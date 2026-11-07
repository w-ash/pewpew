"""The catalog: validated, cross-checked entity data with a content digest.

`load_catalog()` reads `catalog_entries/<kind>/<id>.json`, one entity per file
(docs/studio/domain-model.md:25-35). Loading validates every file, resolves
every reference and evaluates every expression, so a catalog that loads is
one `compile_rig` can use without further checks. The result is cached per
root directory.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
from pydantic import ValidationError

from pewpew.jsonfile import TooDeep, loads
from pewpew.rig import expr
from pewpew.rig.models import (
    CATALOG_ENTITY,
    KINDS,
    AttachmentType,
    Cable,
    Chipset,
    Connector,
    Controller,
    Firmware,
    FixtureType,
    Issue,
    LedType,
    Part,
    Profile,
    Psu,
    RigError,
    Sourced,
    status,
    value,
)

DATA_ROOT = Path(__file__).with_name("catalog_entries")
HOST_PREFIX = "host:"

_KIND_ORDER = {kind: i for i, kind in enumerate(KINDS)}


@dataclass(frozen=True)
class FixtureSpec:
    """The numbers of one fixture type that compiling and wiring need."""

    type_id: str
    count: int
    span_m: float
    z_m: float
    facing: tuple[float, float, float] | None
    chipset: str
    channels: str
    color_order: str
    bits_per_channel: int
    bit_s: float
    reset_s: float
    v_nominal: float
    max_w: float

    @property
    def bits_per_px(self) -> int:
        return self.bits_per_channel * len(self.channels)

    @property
    def bytes_per_px(self) -> float:
        return self.bits_per_px / 8

    @property
    def t_px_s(self) -> float:
        """Wire time per pixel: bits per channel × channels × bit time."""
        return self.bits_per_px * self.bit_s

    @property
    def current_a(self) -> float:
        """Worst-case current at the nominal voltage: max_w / v_nominal."""
        return self.max_w / self.v_nominal


class Catalog:
    """Every catalog entity by id. Ids are unique across all kinds."""

    def __init__(self, entities: Iterable[Any]) -> None:
        ordered = sorted(entities, key=lambda e: (_KIND_ORDER[e.kind], e.id))
        issues: list[Issue] = []
        by_id: dict[str, Any] = {}
        for entity in ordered:
            if entity.id in by_id:
                issues.append(Issue.error("duplicate_id", f"id {entity.id!r} is used twice", entity.id))
            by_id[entity.id] = entity
        self._entities = MappingProxyType(by_id)
        self._dims: dict[str, Mapping[str, float]] = {}
        for entity in by_id.values():
            issues.extend(self._check(entity))
        if issues:
            raise RigError(issues)
        self._specs: dict[str, FixtureSpec] = {}

    # ---- lookup -------------------------------------------------------------

    def __contains__(self, entity_id: object) -> bool:
        return entity_id in self._entities

    def __iter__(self) -> Iterator[Any]:
        return iter(self._entities.values())

    def get(self, entity_id: str, kind: str | None = None) -> Any:
        """The entity `entity_id`; KeyError if it is absent or of another kind."""
        entity = self._entities.get(entity_id)
        if entity is None or (kind is not None and entity.kind != kind):
            raise KeyError(f"no {kind or 'catalog entity'} {entity_id!r}")
        return entity

    def has(self, entity_id: str, kind: str) -> bool:
        entity = self._entities.get(entity_id)
        return entity is not None and entity.kind == kind

    def of_kind(self, kind: str) -> Mapping[str, Any]:
        return MappingProxyType({e.id: e for e in self._entities.values() if e.kind == kind})

    @property
    def fixture_types(self) -> Mapping[str, FixtureType]:
        return self.of_kind("fixture_type")

    @property
    def attachment_types(self) -> Mapping[str, AttachmentType]:
        return self.of_kind("attachment_type")

    @property
    def cables(self) -> Mapping[str, Cable]:
        return self.of_kind("cable")

    @property
    def psus(self) -> Mapping[str, Psu]:
        return self.of_kind("psu")

    @property
    def controllers(self) -> Mapping[str, Controller]:
        return self.of_kind("controller")

    # ---- values -------------------------------------------------------------

    def dims(self, entity_id: str) -> Mapping[str, float]:
        """The entity's dims, every expression evaluated."""
        return self._dims.get(entity_id, MappingProxyType({}))

    def num(self, entity_id: str, fact: Any) -> float | None:
        """A numeric fact of `entity_id` as a float; expressions use its dims."""
        raw = value(fact)
        if raw is None:
            return None
        if isinstance(raw, str):
            return expr.evaluate(raw, self.dims(entity_id))
        return float(raw)

    def need(self, entity_id: str, fact: Any) -> float:
        """`num`, for a fact the entity must state."""
        n = self.num(entity_id, fact)
        if n is None:
            raise ValueError(f"{entity_id}: a required numeric fact is missing")
        return n

    def vec(self, entity_id: str, facts: Iterable[Any]) -> np.ndarray:
        return np.array([self.num(entity_id, f) for f in facts], dtype=np.float64)

    def spec(self, type_id: str) -> FixtureSpec:
        """The resolved pixel, timing and power numbers of a fixture type."""
        if type_id not in self._specs:
            ft = self.get(type_id, "fixture_type")
            px = ft.pixels
            chip = self.get(value(px.chipset), "chipset")
            facing = value(px.facing)
            self._specs[type_id] = FixtureSpec(
                type_id=type_id,
                count=int(value(px.count)),
                span_m=self.need(type_id, px.span_m),
                z_m=self.need(type_id, px.z_m),
                facing=None if facing is None else (float(facing[0]), float(facing[1]), float(facing[2])),
                chipset=chip.id,
                channels=value(px.channels),
                color_order=value(px.color_order),
                bits_per_channel=int(value(chip.bits_per_channel)),
                bit_s=self.need(chip.id, chip.bit_s),
                reset_s=self.need(chip.id, chip.reset_s),
                v_nominal=self.need(type_id, ft.power.v_nominal),
                max_w=self.need(type_id, ft.power.max_w),
            )
        return self._specs[type_id]

    def led_type(self, firmware_id: str, chipset: str, channels: str) -> LedType | None:
        """The firmware's LED type for a pixel format, or None if it has none."""
        for led in self.get(firmware_id, "firmware").led_types:
            if led.chipset == chipset and led.channels == channels:
                return led
        return None

    # ---- digests ------------------------------------------------------------

    @cached_property
    def digest(self) -> str:
        """SHA-256 over the canonical JSON of every entity, in kind then id order."""
        return _sha256([e.model_dump(mode="json") for e in self._entities.values()])

    # ---- the catalog as the studio shows it ---------------------------------

    def to_json(self) -> dict[str, Any]:
        """The catalog for `GET /api/catalog`, as plain JSON types.

        Each numeric fact is `{"v", "status", "src"}` with `v` evaluated; an
        expression also keeps its text as `expr`.
        """
        from pewpew.rig.presets import describe_presets

        return {
            "digest": self.digest,
            "fixture_types": [self._fixture_json(ft) for ft in self.fixture_types.values()],
            "attachment_types": [self._attachment_json(a) for a in self.attachment_types.values()],
            "controllers": [self._controller_json(c) for c in self.controllers.values()],
            "psus": [
                {
                    "id": p.id,
                    "name": p.name,
                    "notes": p.notes,
                    "v_out": self._fact(p.id, p.v_out),
                    "i_max_a": self._fact(p.id, p.i_max_a),
                    "connector": p.connector,
                }
                for p in self.psus.values()
            ],
            "cables": [
                {
                    "id": c.id,
                    "name": c.name,
                    "notes": c.notes,
                    "length_m": self._fact(c.id, c.length_m),
                    "ends": list(c.ends),
                    "conductors_mm2": {
                        role: self._fact(c.id, getattr(c.conductors_mm2, role))
                        for role in ("vplus", "gnd", "data", "spare")
                    },
                }
                for c in self.cables.values()
            ],
            "presets": describe_presets(),
        }

    def _fact(self, entity_id: str, fact: Any) -> dict[str, Any] | None:
        raw = value(fact)
        if raw is None:
            return None
        out = self._text(fact)
        if isinstance(raw, (int, float, str)):
            out["v"] = self.num(entity_id, fact)
        if isinstance(raw, str):
            out["expr"] = raw
        return out

    def _text(self, fact: Any) -> dict[str, Any]:
        return {"v": value(fact), "status": status(fact), "src": fact.src if isinstance(fact, Sourced) else None}

    def _fixture_json(self, ft: FixtureType) -> dict[str, Any]:
        spec = self.spec(ft.id)
        px = ft.pixels
        return {
            "id": ft.id,
            "name": ft.name,
            "rev": ft.rev,
            "inventory": ft.inventory,
            "notes": ft.notes,
            "dims": {name: self._fact(ft.id, d) for name, d in ft.dims.items()},
            "anchors": {name: {"accepts": a.accepts, "connector": a.connector} for name, a in ft.anchors.items()},
            "pixels": {
                "count": self._text(px.count),
                "span_m": self._fact(ft.id, px.span_m),
                "leds_per_pixel": self._text(px.leds_per_pixel),
                "facing": self._text(px.facing),
                "beam_deg": self._fact(ft.id, px.beam_deg),
                "chipset": self._text(px.chipset),
                "channels": self._text(px.channels),
                "color_order": self._text(px.color_order),
                "t_px_s": spec.t_px_s,
                "bytes_per_px": spec.bytes_per_px,
            },
            "power": {
                "v_nominal": self._fact(ft.id, ft.power.v_nominal),
                "max_w": self._fact(ft.id, ft.power.max_w),
                "measured_w": self._fact(ft.id, ft.power.measured_w),
                "model": self._text(ft.power.model_fact),
                "current_a": spec.current_a,
            },
        }

    def _attachment_json(self, a: AttachmentType) -> dict[str, Any]:
        return {
            "id": a.id,
            "name": a.name,
            "rev": a.rev,
            "notes": a.notes,
            "fits": a.fits,
            "dims": {name: self._fact(a.id, d) for name, d in a.dims.items()},
        }

    def _controller_json(self, c: Controller) -> dict[str, Any]:
        fw = self.get(c.firmware, "firmware")
        return {
            "id": c.id,
            "name": c.name,
            "notes": c.notes,
            "firmware": {
                "id": fw.id,
                "name": fw.name,
                "max_px_per_output": self._text(fw.max_px_per_output),
                "max_px_total": self._text(fw.max_px_total),
                "warn_px_per_output": self._text(fw.warn_px_per_output),
            },
            "outputs": [o.model_dump(mode="json") for o in c.outputs],
            "groups": {k: g.model_dump(mode="json") for k, g in c.groups.items()},
            "data_out_v": self._fact(c.id, c.data_out_v),
            "lead_max_m": self._fact(c.id, c.lead_max_m),
            "max_px_advised": None if c.max_px_advised is None else self._text(c.max_px_advised),
            "network": list(c.network),
            "power_w": self._fact(c.id, c.power_w),
        }

    # ---- checks -------------------------------------------------------------

    def _check(self, entity: Any) -> list[Issue]:
        ref = f"{entity.kind}/{entity.id}"
        if isinstance(entity, (FixtureType, AttachmentType)):
            return self._check_assembly(entity, ref)
        issues: list[Issue] = []
        issues.extend(self._check_signs(entity, ref, _positive_numbers(entity)))
        if isinstance(entity, Cable):
            for end in entity.ends:
                if end is not None and not self.has(end, "connector"):
                    issues.append(Issue.error("unresolved_ref", f"no connector {end!r}", f"{ref}.ends"))
        elif isinstance(entity, Firmware):
            seen: set[tuple[str, str]] = set()
            for i, led in enumerate(entity.led_types):
                where = f"{ref}.led_types[{i}]"
                if not self.has(led.chipset, "chipset"):
                    issues.append(Issue.error("unresolved_ref", f"no chipset {led.chipset!r}", where))
                if (led.chipset, led.channels) in seen:
                    issues.append(Issue.error("duplicate_id", f"two LED types for {led.chipset} {led.channels}", where))
                seen.add((led.chipset, led.channels))
        elif isinstance(entity, Psu):
            if entity.connector is not None and not self.has(entity.connector, "connector"):
                issues.append(Issue.error("unresolved_ref", f"no connector {entity.connector!r}", f"{ref}.connector"))
        elif isinstance(entity, Controller):
            if not self.has(entity.firmware, "firmware"):
                issues.append(Issue.error("unresolved_ref", f"no firmware {entity.firmware!r}", ref))
            ids = [o.id for o in entity.outputs]
            for dup in sorted({i for i in ids if ids.count(i) > 1}):
                issues.append(Issue.error("duplicate_id", f"output {dup!r} is listed twice", ref))
            for o in entity.outputs:
                if o.group not in entity.groups:
                    issues.append(Issue.error("unresolved_ref", f"output {o.id!r} names no group {o.group!r}", ref))
        issues.extend(self._check_numbers(entity, ref, _plain_numbers(entity)))
        return issues

    def _check_assembly(self, entity: FixtureType | AttachmentType, ref: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            self._dims[entity.id] = MappingProxyType(expr.resolve({k: value(v) for k, v in entity.dims.items()}))
        except expr.ExprError as exc:
            return [Issue.error("bad_expression", str(exc), f"{ref}.dims")]
        host_ok = isinstance(entity, AttachmentType)
        issues.extend(_check_profiles(entity.profiles, ref, host_ok))
        part_ids = [p.id for p in entity.parts]
        for dup in sorted({i for i in part_ids if part_ids.count(i) > 1}):
            issues.append(Issue.error("duplicate_id", f"part {dup!r} is listed twice", ref))
        for part in entity.parts:
            if part.profile is not None and not _profile_known(part.profile, entity.profiles, host_ok):
                issues.append(Issue.error("unresolved_ref", f"part {part.id!r} names no profile {part.profile!r}", ref))
        for name, anchor in entity.anchors.items():
            where = f"{ref}.anchors.{name}"
            if anchor.connector is not None and not self.has(anchor.connector, "connector"):
                issues.append(Issue.error("unresolved_ref", f"no connector {anchor.connector!r}", where))
            if anchor.accepts is not None and anchor.accepts not in entity.profiles:
                issues.append(Issue.error("unresolved_ref", f"accepts no profile {anchor.accepts!r}", where))
            if anchor.accepts is not None and anchor.dir is None:
                issues.append(Issue.error("anchor_dir", "an anchor that accepts attachments needs dir", where))
            if anchor.dir is not None and not any(anchor.dir):
                issues.append(Issue.error("bad_value", "an anchor dir must not be zero", where))
        if isinstance(entity, FixtureType):
            chipset = value(entity.pixels.chipset)
            if not self.has(chipset, "chipset"):
                issues.append(Issue.error("unresolved_ref", f"no chipset {chipset!r}", f"{ref}.pixels"))
            if int(value(entity.pixels.count)) < 1:
                issues.append(Issue.error("bad_value", "pixels.count must be at least 1", f"{ref}.pixels"))
            facing = value(entity.pixels.facing)
            if facing is not None and not any(facing):
                issues.append(Issue.error("bad_value", "pixels.facing must not be zero", f"{ref}.pixels"))
            issues.extend(self._check_signs(entity, ref, _positive_numbers(entity)))
        issues.extend(self._check_numbers(entity, ref, _assembly_numbers(entity)))
        return issues

    def _check_signs(self, entity: Any, ref: str, numbers: Iterable[tuple[str, Any, bool]]) -> list[Issue]:
        """`bad_value` for each given number that is not above 0, or with `zero_ok` below 0."""
        issues = []
        for where, fact, zero_ok in numbers:
            if fact is None:
                continue
            try:
                n = self.num(entity.id, fact)
            except expr.ExprError:
                continue  # _check_numbers reports it
            if n is None:
                continue
            if n < 0 or (n == 0 and not zero_ok):
                rule = "must not be below 0" if zero_ok else "must be above 0"
                issues.append(Issue.error("bad_value", f"{where} {rule}", f"{ref}.{where}"))
        return issues

    def _check_numbers(self, entity: Any, ref: str, numbers: Iterable[tuple[str, Any]]) -> list[Issue]:
        issues = []
        for where, fact in numbers:
            try:
                self.num(entity.id, fact)
            except expr.ExprError as exc:
                issues.append(Issue.error("bad_expression", str(exc), f"{ref}.{where}"))
        return issues


def _sha256(obj: Any) -> str:
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _profile_known(name: str, profiles: Mapping[str, Profile], host_ok: bool) -> bool:
    return name in profiles or (host_ok and name.startswith(HOST_PREFIX))


def _check_profiles(profiles: Mapping[str, Profile], ref: str, host_ok: bool) -> list[Issue]:
    issues: list[Issue] = []

    def refs(p: Profile) -> Iterator[str]:
        if p.ref is not None:
            yield p.ref
        for m in p.minus:
            yield from refs(m)

    for name, profile in profiles.items():
        for target in refs(profile):
            if not _profile_known(target, profiles, host_ok):
                issues.append(Issue.error("unresolved_ref", f"profile {name!r} names no profile {target!r}", ref))
    state: dict[str, int] = {}

    def visit(name: str, path: list[str]) -> None:
        if state.get(name) == 2 or name not in profiles:
            return
        if state.get(name) == 1:
            cycle = " -> ".join(path[path.index(name) :] + [name])
            issues.append(Issue.error("ref_cycle", f"profile cycle: {cycle}", ref))
            return
        state[name] = 1
        for target in refs(profiles[name]):
            visit(target, path + [name])
        state[name] = 2

    for name in profiles:
        visit(name, [])
    return issues


def _profile_numbers(p: Profile, where: str) -> Iterator[tuple[str, Any]]:
    for i, v in enumerate(p.rect or ()):
        yield f"{where}.rect[{i}]", v
    if p.circle is not None:
        yield f"{where}.circle", p.circle
    for i, pt in enumerate(p.polygon or ()):
        for j, v in enumerate(pt):
            yield f"{where}.polygon[{i}][{j}]", v
    for i, v in enumerate(p.at):
        yield f"{where}.at[{i}]", v
    for i, m in enumerate(p.minus):
        yield from _profile_numbers(m, f"{where}.minus[{i}]")


def _part_numbers(part: Part, where: str) -> Iterator[tuple[str, Any]]:
    for name in ("box", "range_m", "at"):
        for i, v in enumerate(getattr(part, name) or ()):
            yield f"{where}.{name}[{i}]", v
    yield f"{where}.gain", part.gain


def _assembly_numbers(entity: FixtureType | AttachmentType) -> Iterator[tuple[str, Any]]:
    for name, profile in entity.profiles.items():
        yield from _profile_numbers(profile, f"profiles.{name}")
    for part in entity.parts:
        yield from _part_numbers(part, f"parts.{part.id}")
    for name, anchor in entity.anchors.items():
        for i, v in enumerate(anchor.at):
            yield f"anchors.{name}.at[{i}]", v
        if anchor.pigtail_m is not None:
            yield f"anchors.{name}.pigtail_m", anchor.pigtail_m
    if isinstance(entity, FixtureType):
        px, power = entity.pixels, entity.power
        yield "pixels.span_m", px.span_m
        yield "pixels.z_m", px.z_m
        yield "pixels.beam_deg", px.beam_deg
        for name in ("v_nominal", "max_w", "measured_w", "passthrough_ohm"):
            yield f"power.{name}", getattr(power, name)


def _positive_numbers(entity: Any) -> Iterator[tuple[str, Any, bool]]:
    """(where, fact, zero_ok) for each number the wiring and power arithmetic divides by or sums.

    A zero conductor area, PSU rating or bit time would divide by zero. A
    board's `power_w` may be 0 but not below it.
    """
    if isinstance(entity, FixtureType):
        yield "pixels.span_m", entity.pixels.span_m, False
        yield "power.v_nominal", entity.power.v_nominal, False
        yield "power.passthrough_ohm", entity.power.passthrough_ohm, True
    elif isinstance(entity, Chipset):
        yield "bit_s", entity.bit_s, False
        yield "bits_per_channel", entity.bits_per_channel, False
    elif isinstance(entity, Connector):
        yield "rated_a", entity.rated_a, False
    elif isinstance(entity, Psu):
        yield "v_out", entity.v_out, False
        yield "i_max_a", entity.i_max_a, False
    elif isinstance(entity, Cable):
        for role in ("vplus", "gnd"):
            yield f"conductors_mm2.{role}", getattr(entity.conductors_mm2, role), False
    elif isinstance(entity, Controller):
        yield "power_w", entity.power_w, True


def _plain_numbers(entity: Any) -> Iterator[tuple[str, Any]]:
    """The numeric facts of a non-assembly entity; they cannot name dims."""
    names = {
        "chipset": ("bit_s", "reset_s"),
        "connector": ("rated_a",),
        "cable": ("length_m",),
        "psu": ("v_out", "i_max_a"),
        "firmware": ("min_frame_interval_s",),
        "controller": ("data_out_v", "lead_max_m", "power_w"),
    }[entity.kind]
    for name in names:
        yield name, getattr(entity, name)
    if isinstance(entity, Cable):
        for role in ("vplus", "gnd", "data", "spare"):
            yield f"conductors_mm2.{role}", getattr(entity.conductors_mm2, role)


def validation_issues(exc: ValidationError, ref: str = "") -> list[Issue]:
    """One error-level issue per pydantic error; `code` is the error type."""
    issues = []
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"])
        where = f"{ref}:{loc}" if ref and loc else (ref or loc or None)
        issues.append(Issue.error(err["type"], err["msg"], where))
    return issues


def read_catalog(root: Path | str) -> Catalog:
    """Read, validate and cross-check the catalog under `root`, uncached."""
    root = Path(root)
    issues: list[Issue] = []
    entities: list[Any] = []
    try:
        kind_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError as exc:
        raise RigError([Issue.error("unreadable_file", f"cannot read the catalog folder: {exc.strerror}")]) from None
    for kind_dir in kind_dirs:
        if kind_dir.name.startswith((".", "_")):
            continue
        if kind_dir.name not in KINDS:
            issues.append(Issue.error("unknown_kind", f"{kind_dir.name!r} is not a catalog kind", kind_dir.name))
            continue
        for path in sorted(kind_dir.glob("*.json")):
            ref = f"{kind_dir.name}/{path.name}"
            try:
                raw = loads(path.read_text(encoding="utf-8"))
            except TooDeep as exc:
                issues.append(Issue.error("too_deep", str(exc), ref))
                continue
            except json.JSONDecodeError as exc:
                issues.append(Issue.error("bad_json", str(exc), ref))
                continue
            except UnicodeDecodeError:
                issues.append(Issue.error("bad_json", "the file is not UTF-8 text", ref))
                continue
            except OSError as exc:
                issues.append(Issue.error("unreadable_file", f"cannot read the file: {exc.strerror}", ref))
                continue
            try:
                entity = CATALOG_ENTITY.validate_python(raw)
            except ValidationError as exc:
                issues.extend(validation_issues(exc, ref))
                continue
            if entity.kind != kind_dir.name:
                issues.append(Issue.error("wrong_kind", f"a {entity.kind} file in {kind_dir.name}/", ref))
            if entity.id != path.stem:
                issues.append(Issue.error("id_mismatch", f"id {entity.id!r} differs from the file name", ref))
            entities.append(entity)
    if issues:
        raise RigError(issues)
    return Catalog(entities)


@cache
def _cached(root: str) -> Catalog:
    return read_catalog(root)


def load_catalog(root: Path | str | None = None) -> Catalog:
    """The catalog under `root` (default: the bundled data), validated and cached."""
    return _cached(str(Path(root or DATA_ROOT).resolve()))
