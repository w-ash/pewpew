"""`compile_rig`: an arrangement and a catalog in, a `CompiledRig` out.

Pure: no I/O, no clock, no RNG (docs/studio/domain-model.md:206-215). The
steps are:

1. Expand groups and free fixtures into instances with world matrices.
2. Wire them, from the explicit chains or `wiring.auto`.
3. Index pixels in data order: controllers in file order, then outputs in
   profile order, then the chain on each output, then pixel j. Unwired
   fixtures follow in authoring order.
4. Rotate the positions into the plan frame (x right, y up the plan, z
   height; `MVR_C`) and contain-normalize them into the float32 mapping
   `Renderer` takes. `positions_m` and the matrices stay y-up.
5. Slice per output and per controller.
6. Report power, wiring and controllers (`pewpew.rig.electrical`).

Errors raise `RigError`; violations and warnings come back on `rig.issues`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from pewpew.mapping import contain, pixel_offsets
from pewpew.rig import presets
from pewpew.rig.catalog import HOST_PREFIX, Catalog
from pewpew.rig.electrical import boards_w, build_report, effect_power_model, has_conductors, supplies_of
from pewpew.rig.models import (
    Arrangement,
    Chain,
    CompiledRig,
    ControllerPlacement,
    ControllerSlice,
    FixtureInstance,
    FixtureType,
    Instance,
    Issue,
    OutputSlice,
    PsuPlacement,
    RigError,
    RingGroup,
    WiringPlan,
    capped,
    value,
)
from pewpew.rig.pose import MVR_C, anchor_frame, pose_matrix, to_three
from pewpew.rig.wiring import auto_wire


def compile_rig(arrangement: Arrangement, catalog: Catalog) -> CompiledRig:
    """Compile `arrangement` against `catalog`. Raises RigError on any error."""
    issues: list[Issue] = []
    instances = expand(arrangement, catalog, issues)
    plan = (
        auto_wire(instances, arrangement, catalog)
        if arrangement.wiring.auto is not None
        else _explicit_plan(arrangement, instances)
    )
    issues.extend(plan.issues)
    controllers = [*arrangement.controllers, *plan.controllers]
    psus = [*arrangement.psus, *plan.psus]
    _check_plan(plan, controllers, psus, instances, catalog, issues)
    if any(i.level == "error" for i in issues):
        raise RigError(issues)

    rows, slices, controller_slices = _data_order(plan, controllers, instances, catalog)
    issues.extend(_capacity_issues(controllers, slices, controller_slices, catalog))

    n = sum(catalog.spec(inst.type_id).count for inst, _ in rows)
    positions = np.zeros((n, 3))
    normals = np.zeros((n, 3))
    fixture_of = np.zeros(n, dtype=np.int32)
    pixel_in_fixture = np.zeros(n, dtype=np.int32)
    fixtures = []
    start = 0
    for f, (inst, chain) in enumerate(rows):
        spec = catalog.spec(inst.type_id)
        count = spec.count
        rot, origin = inst.matrix[:3, :3], inst.matrix[:3, 3]
        y = pixel_offsets(count, spec.span_m)
        positions[start : start + count] = origin + y[:, None] * rot[:, 1] + spec.z_m * rot[:, 2]
        if spec.facing is not None:
            normals[start : start + count] = rot @ np.asarray(spec.facing, dtype=np.float64)
        fixture_of[start : start + count] = f
        pixel_in_fixture[start : start + count] = np.arange(count)
        fixtures.append(_fixture_instance(inst, chain, start, count, catalog))
        start += count

    with np.errstate(over="ignore", invalid="ignore"):
        mapping = contain(positions @ MVR_C.T).mapping
    if not np.isfinite(mapping).all():
        raise RigError([*issues, Issue.error("not_finite", "the pixel positions are too far apart to normalize")])
    report, electrical_issues = build_report(plan, arrangement, instances, slices, catalog)
    issues.extend(electrical_issues)
    for array in (positions, normals, fixture_of, pixel_in_fixture):
        array.setflags(write=False)
    return CompiledRig(
        mapping=mapping,
        positions_m=positions,
        normals=normals,
        fixture_of=fixture_of,
        pixel_in_fixture=pixel_in_fixture,
        fixtures=tuple(fixtures),
        slices=tuple(slices),
        controller_slices=tuple(controller_slices),
        issues=capped(issues),
        catalog_digest=catalog.digest,
        report=report,
        feeds=plan.feeds,
        power=effect_power_model(
            fixtures, controllers, catalog, supplies_of(plan), boards_w(psus, controllers, catalog)
        ),
        power_cap=arrangement.power.cap,
    )


# ---- expansion -----------------------------------------------------------------


def expand(arrangement: Arrangement, catalog: Catalog, issues: list[Issue]) -> list[Instance]:
    """Every fixture of `arrangement` in authoring order: groups, then free fixtures.

    Problems are appended to `issues`; a fixture that cannot be placed is left out.
    """
    out: list[Instance] = []
    for gi, group in enumerate(arrangement.groups):
        ref = f"groups[{gi}]"
        ft = _fixture_type(group.type, catalog, issues, ref)
        if ft is None:
            continue
        if isinstance(group, RingGroup):
            end_a, end_b = ft.anchors.get("end_a"), ft.anchors.get("end_b")
            if end_a is None or end_b is None:
                issues.append(Issue.error("ring_needs_ends", f"{ft.id} has no end_a and end_b anchors", ref))
                continue
            a, b = catalog.vec(ft.id, end_a.at), catalog.vec(ft.id, end_b.at)
            members = presets.ring(group, float(np.linalg.norm(b - a)))
        else:
            members = presets.array(group)
        to_world = pose_matrix(group.pose)
        for member in members:
            out.append(
                _instance(member.id, ft, group.id, to_world @ member.matrix, member.attach, catalog, issues, ref)
            )
    for fi, placement in enumerate(arrangement.fixtures):
        ref = f"fixtures[{fi}]"
        ft = _fixture_type(placement.type, catalog, issues, ref)
        if ft is not None:
            out.append(
                _instance(placement.id, ft, None, pose_matrix(placement.pose), placement.attach, catalog, issues, ref)
            )
    _duplicates((i.id for i in out), "fixture", issues)
    return out


def _fixture_type(type_id: str, catalog: Catalog, issues: list[Issue], ref: str) -> FixtureType | None:
    if catalog.has(type_id, "fixture_type"):
        return catalog.get(type_id)
    issues.append(Issue.error("unresolved_ref", f"no fixture type {type_id!r}", ref))
    return None


def _instance(
    inst_id: str,
    ft: FixtureType,
    group: str | None,
    matrix: np.ndarray,
    attach: Mapping[str, str | None],
    catalog: Catalog,
    issues: list[Issue],
    ref: str,
) -> Instance:
    attachments: dict[str, str | None] = {n: None for n, a in ft.anchors.items() if a.accepts is not None}
    for anchor_name, att_id in attach.items():
        if att_id is None:
            continue
        where = f"{ref}.attach.{anchor_name}"
        anchor = ft.anchors.get(anchor_name)
        if anchor is None:
            issues.append(Issue.error("unresolved_ref", f"{ft.id} has no anchor {anchor_name!r}", where))
            continue
        if not catalog.has(att_id, "attachment_type"):
            issues.append(Issue.error("unresolved_ref", f"no attachment type {att_id!r}", where))
            continue
        att = catalog.get(att_id)
        if anchor.accepts is None or att.fits != anchor.accepts:
            issues.append(
                Issue.error(
                    "attach_mismatch",
                    f"{att_id} fits {att.fits!r} but {ft.id}.{anchor_name} accepts {anchor.accepts!r}",
                    where,
                )
            )
            continue
        missing = sorted(p for p in _host_profiles(att) if p not in ft.profiles)
        if missing:
            issues.append(Issue.error("attach_mismatch", f"{ft.id} has no profile {missing[0]!r} for {att_id}", where))
            continue
        attachments[anchor_name] = att_id
    matrix = np.array(matrix, dtype=np.float64)
    if not np.isfinite(matrix).all():
        issues.append(Issue.error("not_finite", "the placement is too far out to compute", ref))
    matrix.setflags(write=False)
    return Instance(id=inst_id, type_id=ft.id, group=group, matrix=matrix, attachments=attachments)


def _host_profiles(att: Any) -> set[str]:
    names = {p.profile for p in att.parts if p.profile}

    def refs(profile: Any) -> Iterable[str]:
        if profile.ref:
            yield profile.ref
        for m in profile.minus:
            yield from refs(m)

    for profile in att.profiles.values():
        names.update(refs(profile))
    return {n[len(HOST_PREFIX) :] for n in names if n.startswith(HOST_PREFIX)}


# ---- wiring checks -------------------------------------------------------------


def _explicit_plan(arrangement: Arrangement, instances: list[Instance]) -> WiringPlan:
    wired = {f for chain in arrangement.wiring.chains for f in chain.fixtures}
    unassigned = tuple(i.id for i in instances if i.id not in wired)
    issues = ()
    if unassigned:
        issues = (
            Issue.of(
                "warning",
                "unwired",
                f"{len(unassigned)} fixtures are in no chain; their pixels follow in authoring order",
            ),
        )
    return WiringPlan(
        chains=tuple(arrangement.wiring.chains),
        feeds=tuple(arrangement.wiring.feeds),
        unassigned=unassigned,
        issues=issues,
    )


def _check_plan(
    plan: WiringPlan,
    placements: list[ControllerPlacement],
    psu_placements: list[PsuPlacement],
    instances: list[Instance],
    catalog: Catalog,
    issues: list[Issue],
) -> None:
    by_id = {i.id: i for i in instances}
    controllers = {}
    for ci, ctrl in enumerate(placements):
        if catalog.has(ctrl.profile, "controller"):
            controllers[ctrl.id] = catalog.get(ctrl.profile)
        else:
            issues.append(
                Issue.error("unresolved_ref", f"no controller profile {ctrl.profile!r}", f"controllers[{ci}]")
            )
    _duplicates((c.id for c in placements), "controller", issues)
    controller_ids = {c.id for c in placements}
    powered: dict[str, str] = {}
    for pi, psu in enumerate(psu_placements):
        if not catalog.has(psu.type, "psu"):
            issues.append(Issue.error("unresolved_ref", f"no PSU type {psu.type!r}", f"psus[{pi}]"))
        for cid in psu.powers:
            if cid not in controller_ids:
                issues.append(Issue.error("unresolved_ref", f"no controller {cid!r}", f"psus[{pi}].powers"))
            elif cid in powered:
                twice = (
                    f"PSU {psu.id!r} lists controller {cid!r} twice"
                    if powered[cid] == psu.id
                    else f"controller {cid!r} is powered by PSU {powered[cid]!r} and PSU {psu.id!r}"
                )
                issues.append(Issue.error("powered_twice", twice, f"psus[{pi}].powers"))
            powered.setdefault(cid, psu.id)
    _duplicates((p.id for p in psu_placements), "PSU", issues)
    _duplicates((c.id for c in plan.chains), "chain", issues)
    _duplicates((f.id for f in plan.feeds), "feed", issues)

    used_outputs: set[tuple[str, str]] = set()
    chained: dict[str, str] = {}
    for chain in plan.chains:
        ref = f"chain {chain.id}"
        profile = controllers.get(chain.controller)
        if profile is None:
            if not any(c.id == chain.controller for c in placements):
                issues.append(Issue.error("unresolved_ref", f"no controller {chain.controller!r}", ref))
        elif chain.output not in {o.id for o in profile.outputs}:
            issues.append(Issue.error("unresolved_ref", f"{profile.id} has no output {chain.output!r}", ref))
        if (chain.controller, chain.output) in used_outputs:
            issues.append(
                Issue.error("output_used_twice", f"output {chain.controller}/{chain.output} has two chains", ref)
            )
        used_outputs.add((chain.controller, chain.output))
        formats = set()
        in_chain: set[str] = set()
        for fid in chain.fixtures:
            inst = by_id.get(fid)
            if inst is None:
                issues.append(Issue.error("unresolved_ref", f"no fixture {fid!r}", ref))
                continue
            if fid in in_chain:
                issues.append(Issue.error("duplicate_in_chain", f"{fid} is listed twice in chain {chain.id}", ref))
            elif fid in chained:
                issues.append(
                    Issue.error("fixture_in_two_chains", f"{fid} is in chain {chained[fid]} and chain {chain.id}", ref)
                )
            in_chain.add(fid)
            chained[fid] = chain.id
            spec = catalog.spec(inst.type_id)
            formats.add((spec.chipset, spec.channels))
        if len(formats) > 1:
            mixed = ", ".join(f"{c} {ch}" for c, ch in sorted(formats))
            issues.append(Issue.error("mixed_pixel_format", f"one chain mixes pixel formats: {mixed}", ref))
        elif formats and profile is not None:
            chipset, channels = formats.pop()
            if catalog.led_type(profile.firmware, chipset, channels) is None:
                issues.append(
                    Issue.error("missing_led_type", f"{profile.firmware} has no LED type for {chipset} {channels}", ref)
                )

    chains = {c.id: c for c in plan.chains}
    psus = {p.id for p in psu_placements}
    for feed in plan.feeds:
        ref = f"feed {feed.id}"
        if feed.psu not in psus:
            issues.append(Issue.error("unresolved_ref", f"no PSU {feed.psu!r}", ref))
        if not catalog.has(feed.cable, "cable"):
            issues.append(Issue.error("unresolved_ref", f"no cable {feed.cable!r}", ref))
        elif not has_conductors(catalog, feed.cable):
            issues.append(Issue.error("no_conductors", f"cable {feed.cable!r} has no V+ or GND conductor", ref))
        chain = chains.get(feed.chain)
        if chain is None:
            issues.append(Issue.error("unresolved_ref", f"no chain {feed.chain!r}", ref))
        elif feed.first + feed.count > len(chain.fixtures):
            issues.append(
                Issue.error(
                    "feed_range",
                    f"fixtures {feed.first}..{feed.first + feed.count - 1} are past the end of "
                    f"chain {chain.id}, which has {len(chain.fixtures)}",
                    ref,
                )
            )
    for fid in plan.unassigned:
        if fid not in by_id:
            issues.append(Issue.error("unresolved_ref", f"no fixture {fid!r}", "wiring"))


def _duplicates(ids: Iterable[str], what: str, issues: list[Issue]) -> None:
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            issues.append(Issue.error("duplicate_id", f"{what} id {i!r} is used twice", i))
        seen.add(i)


# ---- data order and slices -----------------------------------------------------


def _data_order(
    plan: WiringPlan, controllers: list[ControllerPlacement], instances: list[Instance], catalog: Catalog
) -> tuple[list[tuple[Instance, Chain | None]], list[OutputSlice], list[ControllerSlice]]:
    by_id = {i.id: i for i in instances}
    on_output = {(c.controller, c.output): c for c in plan.chains}
    rows: list[tuple[Instance, Chain | None]] = []
    slices: list[OutputSlice] = []
    controller_slices: list[ControllerSlice] = []
    start = 0
    for ctrl in controllers:
        profile = catalog.get(ctrl.profile, "controller")
        ctrl_start = start
        for output in profile.outputs:
            chain = on_output.get((ctrl.id, output.id))
            if chain is None:
                continue
            out_start = start
            for fid in chain.fixtures:
                rows.append((by_id[fid], chain))
                start += catalog.spec(by_id[fid].type_id).count
            spec = catalog.spec(by_id[chain.fixtures[0]].type_id)
            led = catalog.led_type(profile.firmware, spec.chipset, spec.channels)
            slices.append(
                OutputSlice(
                    controller=ctrl.id,
                    output=output.id,
                    chain=chain.id,
                    start=out_start,
                    count=start - out_start,
                    led_type=None if led is None else led.type,
                    color_order=chain.color_order or spec.color_order,
                )
            )
        if start > ctrl_start:
            controller_slices.append(ControllerSlice(controller=ctrl.id, start=ctrl_start, count=start - ctrl_start))
    # Unwired fixtures follow: the plan's order first, then any it left out.
    placed = {inst.id for inst, _ in rows}
    for fid in [*plan.unassigned, *(i.id for i in instances)]:
        if fid not in placed:
            rows.append((by_id[fid], None))
            placed.add(fid)
    return rows, slices, controller_slices


def _capacity_issues(
    controllers: list[ControllerPlacement],
    slices: list[OutputSlice],
    controller_slices: list[ControllerSlice],
    catalog: Catalog,
) -> list[Issue]:
    """Firmware pixel caps per output and per controller, and LED-type groups."""
    issues: list[Issue] = []
    totals = {s.controller: s.count for s in controller_slices}
    for ctrl in controllers:
        profile = catalog.get(ctrl.profile, "controller")
        fw = catalog.get(profile.firmware, "firmware")
        cap_out = int(value(fw.max_px_per_output))
        warn_out = int(value(fw.warn_px_per_output))
        group_of = {o.id: o.group for o in profile.outputs}
        types_in_group: dict[str, set[int | None]] = {}
        for s in (s for s in slices if s.controller == ctrl.id):
            ref = f"{ctrl.id}/{s.output}"
            if s.count > cap_out:
                issues.append(
                    Issue.of(
                        "violation",
                        "output_over_cap",
                        f"{s.count} px on one output; {fw.id} drives at most {cap_out}",
                        ref,
                    )
                )
            elif s.count > warn_out:
                issues.append(
                    Issue.of(
                        "warning",
                        "output_over_warn",
                        f"{s.count} px on one output; {fw.id} warns above {warn_out}",
                        ref,
                    )
                )
            types_in_group.setdefault(group_of[s.output], set()).add(s.led_type)
        total = totals.get(ctrl.id, 0)
        cap_total = int(value(fw.max_px_total))
        if total > cap_total:
            issues.append(
                Issue.of(
                    "violation",
                    "controller_over_cap",
                    f"{total} px on {ctrl.id}; {fw.id} drives at most {cap_total}",
                    ctrl.id,
                )
            )
        advised = None if profile.max_px_advised is None else int(value(profile.max_px_advised))
        if advised is not None and total > advised:
            issues.append(
                Issue.of(
                    "warning",
                    "controller_over_advised",
                    f"{total} px on {ctrl.id}; {profile.id} advises {advised}",
                    ctrl.id,
                )
            )
        for name, types in sorted(types_in_group.items()):
            if profile.groups[name].same_led_type and len(types) > 1:
                issues.append(
                    Issue.of(
                        "violation",
                        "mixed_led_type_group",
                        f"outputs in group {name!r} must share one LED type",
                        ctrl.id,
                    )
                )
    return issues


def _fixture_instance(inst: Instance, chain: Chain | None, start: int, count: int, catalog: Catalog) -> FixtureInstance:
    ft = catalog.get(inst.type_id, "fixture_type")
    frames = {}
    for name, att in inst.attachments.items():
        if att is None:
            frames[name] = None
            continue
        anchor = ft.anchors[name]
        frame = anchor_frame(catalog.vec(ft.id, anchor.at), anchor.dir)
        frames[name] = to_three(inst.matrix @ frame)
    return FixtureInstance(
        id=inst.id,
        type_id=inst.type_id,
        group=inst.group,
        matrix=to_three(inst.matrix),
        attachments=dict(inst.attachments),
        attachment_matrices=frames,
        pixel_start=start,
        pixel_count=count,
        controller=None if chain is None else chain.controller,
        output=None if chain is None else chain.output,
        chain=None if chain is None else chain.id,
    )
