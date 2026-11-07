"""Auto-wiring: which fixtures form which chain, on which output, fed from which PSU.

Workstream 2 owns this module (docs/studio/contracts.md:13). `auto_wire` is
the deterministic rule of docs/studio/domain-model.md:217-226:

1. Split the fixtures, in authoring order, into runs: consecutive members of
   one group, or consecutive free fixtures, that share chipset and channels.
2. Break a run wherever a data hop is longer than `max_hop_m`.
3. Cut each piece into ⌈F/c⌉ chains of near-equal size. The per-output
   fixture cap is `c = ⌊min(output cap, max_px(t_px, reset, fps))/px⌋`,
   and at most `fixtures_per_output`. The output cap is the least of the
   firmware's per-output cap and the board's pixel limit.
4. Put each chain on the first free output that keeps its group's LED type
   and its controller's pixel totals. An empty board takes any chain. When
   no output is free, add a controller of the first declared profile whose
   firmware drives the chain, at that controller's position.
5. Split each chain into feeds greedily, from the first PSU with room. The
   PSUs are the ones whose `v_out` is the chain's `v_nominal`, or all of
   them if none is. A feed grows while its current stays within
   `connector_load_fraction` of the connector rating and within
   `psu_load_fraction` of its PSU, and its drop from that PSU's position
   stays within `max_drop_fraction`. The PSU takes the most the RGB stream
   draws through the boards' auto-white, under the arrangement's power cap,
   as the engine enforces it (`pewpew.power.PowerLimiter`). The connector
   takes that capped current under a cap, else every channel full; the
   drop always takes every channel full. A PSU's output connector limits
   its feeds as a fixture's input connector does. A PSU that powers boards
   (`PsuPlacement.powers`) starts with their load.
6. When no PSU has room, add one of the first of those PSUs' type, at its
   position. A fixture that alone is over a PSU's `psu_load_fraction` goes
   on the first of those PSUs, and the report flags the overload. Each feed
   gets the smallest blade fuse in its window.

Step 2 runs before step 3, so a break never leaves a short tail chain; the
design lists them the other way round.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

from pewpew.rig.catalog import Catalog, FixtureSpec
from pewpew.rig.electrical import (
    EPS,
    ORIGIN,
    Site,
    auto_white_modes,
    board_load_a,
    boards_w,
    cable_ohm_per_m,
    has_conductors,
    least,
    link_m,
    max_px,
    pick_fuse,
    run_m,
)
from pewpew.rig.models import (
    Arrangement,
    AutoWiring,
    Chain,
    Controller,
    ControllerPlacement,
    Feed,
    Firmware,
    Instance,
    Issue,
    PsuPlacement,
    WiringPlan,
    value,
)

# The shortest feed cable: a PSU at the injection point still needs a lead.
_MIN_FEED_M = 1e-3


def auto_wire(instances: Sequence[Instance], arrangement: Arrangement, catalog: Catalog) -> WiringPlan:
    """Wire `instances` (in authoring order) by `arrangement.wiring.auto`."""
    opts = arrangement.wiring.auto or AutoWiring()
    ids = tuple(i.id for i in instances)
    if not ids:
        return WiringPlan()
    if not arrangement.controllers:
        warning = Issue.of(
            "warning",
            "unwired",
            f"{len(ids)} fixtures are not wired: declare a controller, and auto-wiring adds more of its "
            "profile as needed",
        )
        return WiringPlan(unassigned=ids, issues=(warning,))
    if not all(catalog.has(c.profile, "controller") for c in arrangement.controllers):
        return WiringPlan(unassigned=ids)  # compile reports the unresolved profile

    site = Site(instances, catalog)
    pieces = _chain_fixtures(instances, arrangement, opts, site)
    placed, boards, unplaced = _place(pieces, arrangement, site)
    chains = tuple(Chain(id=f"{c}.{o}", controller=c, output=o, fixtures=fx) for c, o, fx in placed)
    modes = auto_white_modes(chains, [b.placement for b in boards], catalog)
    placements = [b.placement for b in boards]
    board_watts = math.fsum(boards_w(arrangement.psus, placements, catalog).values())
    capped = Site(instances, catalog, arrangement.power.cap, modes, board_watts)
    feeds, psus, issues = _feed(chains, arrangement, opts, capped, placements)
    if unplaced:
        issues.append(
            Issue.of(
                "warning",
                "unwired",
                f"{len(unplaced)} fixtures are not wired: no declared controller has an output for their pixel format",
            )
        )
    return WiringPlan(
        chains=chains,
        feeds=feeds,
        unassigned=tuple(unplaced),
        issues=tuple(issues),
        controllers=tuple(b.placement for b in boards if b.derived),
        psus=psus,
    )


# ---- chains ----------------------------------------------------------------------


def _chain_fixtures(
    instances: Sequence[Instance], arrangement: Arrangement, opts: AutoWiring, site: Site
) -> list[list[str]]:
    """Steps 1-3: the fixture ids of each chain, in authoring order."""
    catalog = site.catalog
    output_cap = min(
        min(int(value(_firmware(c, catalog).max_px_per_output)), _board_limit(c, catalog))
        for c in arrangement.controllers
    )
    runs: list[list[Instance]] = []
    key = None
    for inst in instances:
        spec = catalog.spec(inst.type_id)
        k = (inst.group, spec.chipset, spec.channels)
        if runs and k == key:
            runs[-1].append(inst)
        else:
            runs.append([inst])
        key = k

    chains = []
    for run in runs:
        pieces = [[run[0].id]]
        for a, b in pairwise(run):
            if link_m(site.ports(a.id)[1], site.ports(b.id)[0], opts.hop_slack) > opts.max_hop_m + EPS:
                pieces.append([b.id])
            else:
                pieces[-1].append(b.id)
        for piece in pieces:
            chains.extend(_even(piece, fixture_cap(piece, output_cap, opts, site)))
    return chains


def fixture_cap(fids: Sequence[str], output_cap: int, opts: AutoWiring, site: Site) -> int:
    """`⌊min(output cap, max_px(t_px, reset, fps))/px⌋`, at most `fixtures_per_output`, at least 1.

    `px` is the largest pixel count among the fixtures.
    """
    specs = [site.catalog.spec(site.by_id[f].type_id) for f in fids]
    px_cap = min(output_cap, max_px(specs[0].t_px_s, specs[0].reset_s, opts.target_fps))
    cap = max(1, px_cap // max(s.count for s in specs))
    return min(cap, opts.fixtures_per_output) if opts.fixtures_per_output else cap


def _even(items: Sequence[str], cap: int) -> list[list[str]]:
    """`items` cut into ⌈len/cap⌉ runs whose sizes differ by at most one, longer first."""
    k = -(-len(items) // cap)
    q, r = divmod(len(items), k)
    out, start = [], 0
    for j in range(k):
        n = q + (1 if j < r else 0)
        out.append(list(items[start : start + n]))
        start += n
    return out


# ---- outputs ---------------------------------------------------------------------


def _firmware(placement: ControllerPlacement, catalog: Catalog) -> Firmware:
    return catalog.get(catalog.get(placement.profile, "controller").firmware, "firmware")


def _board_limit(placement: ControllerPlacement, catalog: Catalog) -> int:
    """The most pixels the board takes: the firmware's total, or less if the profile advises less."""
    profile = catalog.get(placement.profile, "controller")
    limit = int(value(_firmware(placement, catalog).max_px_total))
    if profile.max_px_advised is not None:
        limit = min(limit, int(value(profile.max_px_advised)))
    return limit


@dataclass
class _Board:
    placement: ControllerPlacement
    profile: Controller
    limit_px: int
    derived: bool
    px: int = 0
    led_types: dict[str, int] = field(default_factory=dict)

    def free_output(self, led_type: int, px: int) -> str | None:
        """The first output that can take a chain of `px` pixels of `led_type`.

        An empty board takes a chain over its pixel limit, as no board can
        take it whole; compile flags it.
        """
        if self.px and self.px + px > self.limit_px:
            return None
        for out in self.profile.outputs:
            if out.id in self.led_types:
                continue
            if self.profile.groups[out.group].same_led_type and any(
                self.led_types.get(o.id, led_type) != led_type for o in self.profile.outputs if o.group == out.group
            ):
                continue
            return out.id
        return None


def _board(placement: ControllerPlacement, catalog: Catalog, derived: bool) -> _Board:
    profile = catalog.get(placement.profile, "controller")
    return _Board(placement, profile, _board_limit(placement, catalog), derived)


def _place(
    chains: Sequence[list[str]], arrangement: Arrangement, site: Site
) -> tuple[list[tuple[str, str, list[str]]], list[_Board], list[str]]:
    """Step 4: (controller, output, fixtures) in data order, the boards, the fixtures left over."""
    catalog = site.catalog
    boards = [_board(c, catalog, derived=False) for c in arrangement.controllers]
    taken = {c.id for c in arrangement.controllers}
    placed: list[tuple[_Board, str, list[str]]] = []
    unplaced: list[str] = []
    for fx in chains:
        spec = catalog.spec(site.by_id[fx[0]].type_id)
        px = sum(catalog.spec(site.by_id[f].type_id).count for f in fx)

        def led_of(board: _Board, spec: FixtureSpec = spec):
            return catalog.led_type(board.profile.firmware, spec.chipset, spec.channels)

        found = None
        for board in boards:
            led = led_of(board)
            out = None if led is None else board.free_output(led.type, px)
            if led is not None and out is not None:
                found = board, led, out
                break
        if found is None:
            template = next((b for b in boards[: len(arrangement.controllers)] if led_of(b) is not None), None)
            board = None
            if template is not None:
                cid = _fresh("c", len(arrangement.controllers), taken)
                source = template.placement
                board = _board(
                    ControllerPlacement(id=cid, profile=source.profile, position_m=source.position_m), catalog, True
                )
            led = None if board is None else led_of(board)
            out = None if board is None or led is None else board.free_output(led.type, px)
            if board is None or led is None or out is None:
                unplaced.extend(fx)
                continue
            taken.add(board.placement.id)
            boards.append(board)
            found = board, led, out
        board, led, out = found
        board.led_types[out] = led.type
        board.px += px
        placed.append((board, out, fx))
    rank = {id(b): i for i, b in enumerate(boards)}
    placed.sort(key=lambda p: (rank[id(p[0])], [o.id for o in p[0].profile.outputs].index(p[1])))
    return [(board.placement.id, out, fx) for board, out, fx in placed], boards, unplaced


def _fresh(prefix: str, declared: int, taken: set[str]) -> str:
    """The first `<prefix><k>` not in `taken`, from k = declared + 1."""
    k = declared + 1
    while f"{prefix}{k}" in taken:
        k += 1
    return f"{prefix}{k}"


# ---- feeds and PSUs --------------------------------------------------------------


def lowest_loss_cable(catalog: Catalog) -> str | None:
    """The catalog cable with the lowest V+ and GND resistance per metre, ties by id."""
    ranked = sorted((cable_ohm_per_m(catalog, c), c) for c in catalog.cables if has_conductors(catalog, c))
    return ranked[0][1] if ranked else None


@dataclass
class _Supply:
    placement: PsuPlacement
    v_out: float
    cap_a: float  # psu_load_fraction × i_max_a
    connector_a: float | None  # the rating of its output connector
    load_a: float = 0.0

    @property
    def room_a(self) -> float:
        return self.cap_a - self.load_a


def _feed(
    chains: Sequence[Chain],
    arrangement: Arrangement,
    opts: AutoWiring,
    site: Site,
    controllers: Sequence[ControllerPlacement],
) -> tuple[tuple[Feed, ...], tuple[PsuPlacement, ...], list[Issue]]:
    """Steps 5 and 6: feeds in data order, the PSUs added, and any issue."""
    catalog = site.catalog
    if not chains or not arrangement.psus or not all(catalog.has(p.type, "psu") for p in arrangement.psus):
        return (), (), []  # the report warns of unfed fixtures; compile reports unresolved types
    cable = opts.feed_cable or lowest_loss_cable(catalog)
    if cable is None:
        return (), (), []
    if not catalog.has(cable, "cable"):
        return (), (), [Issue.error("unresolved_ref", f"no cable {cable!r}", "wiring.auto.feed_cable")]
    if not has_conductors(catalog, cable):
        return (
            (),
            (),
            [Issue.error("no_conductors", f"cable {cable!r} has no V+ or GND conductor", "wiring.auto.feed_cable")],
        )
    per_m = cable_ohm_per_m(catalog, cable)
    profiles = {c.id: c.profile for c in controllers}

    def supply(p: PsuPlacement) -> _Supply:
        psu = catalog.get(p.type, "psu")
        plug = (
            None
            if psu.connector is None
            else catalog.num(psu.connector, catalog.get(psu.connector, "connector").rated_a)
        )
        cap = opts.psu_load_fraction * catalog.need(p.type, psu.i_max_a)
        return _Supply(p, catalog.need(p.type, psu.v_out), cap, plug, board_load_a(p, profiles, catalog))

    def length(at, fid: str) -> float:
        return max(run_m(at or ORIGIN, site.ports(fid)[0].at, opts.hop_slack), _MIN_FEED_M)

    def grow(fx: Sequence[str], i: int, s: _Supply) -> int | None:
        """How many fixtures from `fx[i]` one feed from `s` takes, or None if `s` has no room for them."""
        current, load = site.current_a(fx[i]), site.capped_a(fx[i])
        if load > s.room_a + EPS:
            return None
        rating = least(site.connector_a(fx[i]), s.connector_a)
        r_path = length(s.placement.position_m, fx[i]) * per_m
        drop = current * r_path
        v = site.catalog.spec(site.by_id[fx[i]].type_id).v_nominal
        j = i + 1
        while j < len(fx):
            c = site.current_a(fx[j])
            r_path += site.link_ohm(fx[j - 1], fx[j], per_m, opts.hop_slack)
            nxt_rating = least(rating, site.connector_a(fx[j]))
            nxt_current, nxt_load, nxt_drop = current + c, load + site.capped_a(fx[j]), drop + c * r_path
            nxt_check = nxt_load if site.capping else nxt_current
            if (
                (nxt_rating is not None and nxt_check > opts.connector_load_fraction * nxt_rating + EPS)
                or nxt_drop / v > opts.max_drop_fraction + EPS
                or nxt_load > s.cap_a + EPS
            ):
                break
            if nxt_load > s.room_a + EPS:
                return None  # the feed only grows from here, so it cannot fit
            current, load, drop, rating = nxt_current, nxt_load, nxt_drop, nxt_rating
            j += 1
        return j - i

    supplies = [supply(p) for p in arrangement.psus]
    taken = {p.id for p in arrangement.psus}
    feeds = []
    for chain in chains:
        fx = chain.fixtures
        i = 0
        while i < len(fx):
            v = site.catalog.spec(site.by_id[fx[i]].type_id).v_nominal
            same_v = [s for s in supplies if abs(s.v_out - v) <= 1e-6]
            candidates = same_v or supplies
            chosen = next(((s, n) for s in candidates if (n := grow(fx, i, s)) is not None), None)
            if chosen is None:
                declared = supplies[: len(arrangement.psus)]
                source = next((s for s in declared if s in same_v), declared[0]).placement
                new = supply(
                    PsuPlacement(
                        id=_fresh("p", len(arrangement.psus), taken), type=source.type, position_m=source.position_m
                    )
                )
                n = grow(fx, i, new)
                if n is None:  # one fixture is over a whole PSU: another PSU does not help
                    chosen = candidates[0], 1
                else:
                    taken.add(new.placement.id)
                    supplies.append(new)
                    chosen = new, n
            s, n = chosen
            fids = fx[i : i + n]
            metres = length(s.placement.position_m, fids[0])
            load = site.feed(fids, cable, metres, opts.hop_slack)
            s.load_a += load.capped_a
            feeds.append(
                Feed(
                    id=f"f{len(feeds) + 1}",
                    psu=s.placement.id,
                    chain=chain.id,
                    first=i,
                    count=n,
                    cable=cable,
                    length_m=metres,
                    fuse_a=pick_fuse(
                        site.check_a(load), least(load.connector_a, s.connector_a), opts.connector_load_fraction
                    ),
                )
            )
            i += n
    added = tuple(s.placement for s in supplies[len(arrangement.psus) :])
    return tuple(feeds), added, []
