"""A compiled rig as a run uses it: load, check, address and describe.

`load_rig` and `parse_rig` read an arrangement file. A room map file (the
older format, `pewpew.rig.room_import`) is migrated in memory for one more
release, with a deprecation notice that names `python -m pewpew rig
migrate-room`: appended to the caller's `notices` list, or without one a
`RoomFormatWarning`. Every load goes through `compile_doc`, the one checked
compile that the run, the live reload and the studio share.

What a run does with the rig:

- `ddp_targets`: one DDP board per controller with a host and pixels, from
  `controller_slices`.
- `stream_refusals`: why a run must not stream to the rig's controllers (a
  pixel cap broken, a wired controller with no host).
- `wled_plan`: the `--dry-run` lines, each board then each output as WLED's
  LED settings take it.
- `fixture_spans`: (id, first pixel, pixel count) per fixture, for the blink.
- `rebind_host`: the file with one controller's host changed, every other
  byte kept (the page's "use for A"). A room map file is refused: it is
  migrated first.
- `plan_view` and `rig_view`: what the preview draws (`hello` and
  `layout`'s `room` and `rig`).

Every message names a fixture, controller or output, never a path, so the
same text can cross the preview socket as a reload status.
"""

from __future__ import annotations

import warnings
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np

from pewpew.jsonfile import ProblemsError, TooDeep, loads, replace_string
from pewpew.rig import load_arrangement
from pewpew.rig.catalog import Catalog, load_catalog
from pewpew.rig.compile import compile_rig
from pewpew.rig.models import CompiledRig, ControllerSlice, ControllerTarget, Issue, RigError
from pewpew.rig.pose import MVR_C
from pewpew.rig.room_import import RoomError, is_room, room_to_arrangement
from pewpew.rig_cli import DEFAULT_CONTROLLER, DEFAULT_TYPE
from pewpew.sinks.ddp import HOST_RULE, Board, board_host

#: The issue codes of a broken pixel cap: a run streams nothing while one stands.
CAP_CODES = ("output_over_cap", "controller_over_cap")

ROOM_DEPRECATED = (
    "this is a room map, which pewpew reads for one more release; convert it with "
    "`python -m pewpew rig migrate-room ROOM.json -o ROOM.arrangement.json` and run that file"
)


class RoomFormatWarning(FutureWarning):
    """A room map file was read: it is migrated in memory, and the next release refuses it."""


def compile_doc(doc: Any, catalog: Catalog, max_pixels: int | None = None) -> CompiledRig:
    """Load and compile the parsed arrangement `doc` against `catalog`.

    With `max_pixels`, a rig of more pixels is a `too_many_pixels` error.
    Raises RigError with one issue per problem.
    """
    rig = compile_rig(load_arrangement(doc), catalog)
    if max_pixels is not None and rig.n > max_pixels:
        raise RigError([Issue.error("too_many_pixels", f"limit of {max_pixels} pixels per arrangement")])
    return rig


def load_rig(
    path: str | PathLike[str], catalog: Catalog | None = None, *, notices: list[str] | None = None,
) -> tuple[CompiledRig, bytes]:
    """Read and compile the rig file at `path` (`parse_rig`); return the rig
    and the bytes it came from. Raises RigError, also for a file it cannot read."""
    try:
        data = Path(path).read_bytes()
    except (OSError, ValueError) as exc:  # ValueError: a null byte in the path
        reason = (exc.strerror if isinstance(exc, OSError) else str(exc)) or type(exc).__name__
        raise RigError([Issue.error("unreadable_file", f"cannot read the file: {reason.lower()}")]) from None
    return parse_rig(data, catalog, notices=notices), data


def parse_rig(data: bytes | str, catalog: Catalog | None = None, *, notices: list[str] | None = None) -> CompiledRig:
    """Compile rig file text: an arrangement, or a room map. A room map's
    deprecation notice goes on `notices`, or without it is a
    `RoomFormatWarning`. Raises RigError."""
    return compile_doc(_arrangement(read_doc(data), notices), catalog or load_catalog())


def read_doc(data: bytes | str) -> Any:
    """The parsed JSON of rig file text. Raises RigError."""
    try:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
    except UnicodeDecodeError:
        raise RigError([Issue.error("bad_json", "the file is not UTF-8 text")]) from None
    try:
        return loads(text)
    except TooDeep as exc:
        raise RigError([Issue.error("too_deep", str(exc))]) from None
    except ValueError as exc:  # JSONDecodeError, or an integer of too many digits
        raise RigError([Issue.error("bad_json", str(exc))]) from None


def _arrangement(doc: Any, notices: list[str] | None) -> Any:
    """`doc` itself, or for a room map the arrangement it migrates to, with
    its notice on `notices` or, without that list, warned."""
    if not is_room(doc):
        return doc
    if notices is None:
        warnings.warn(ROOM_DEPRECATED, RoomFormatWarning, stacklevel=3)
    else:
        notices.append(ROOM_DEPRECATED)
    catalog = load_catalog()
    try:
        profile = catalog.get(DEFAULT_CONTROLLER, "controller")
        return room_to_arrangement(doc, controller_profile=profile, fixture_type=DEFAULT_TYPE)
    except RoomError as exc:
        raise RigError([Issue.error("bad_room", problem) for problem in exc.problems]) from None


# ---- addressing ------------------------------------------------------------------


def _hosted(rig: CompiledRig) -> list[tuple[ControllerSlice, ControllerTarget]]:
    """Each controller's pixels and its target, for the controllers with a host."""
    targets = {c.id: c for c in rig.controllers}
    return [(s, targets[s.controller]) for s in rig.controller_slices if targets[s.controller].host is not None]


def ddp_targets(rig: CompiledRig) -> tuple[Board, ...]:
    """One DDP board per controller that has a host and pixels, in data order."""
    return tuple(Board(c.host, s.start, s.count, c.port) for s, c in _hosted(rig))  # type: ignore[arg-type]


def target_names(rig: CompiledRig) -> tuple[str, ...]:
    """The controller id of each of `ddp_targets`, in the same order."""
    return tuple(c.id for _, c in _hosted(rig))


def stream_refusals(rig: CompiledRig) -> list[str]:
    """Why a run must not stream to the rig's controllers: each broken pixel
    cap, and each controller with pixels but no host. Empty when it may."""
    reasons = [f"{i.ref}: {i.message}" if i.ref else i.message for i in rig.issues if i.code in CAP_CODES]
    hosted = {c.id for c in rig.controllers if c.host is not None}
    reasons += [
        f"controller {s.controller!r} drives {s.count} px but has no host"
        for s in rig.controller_slices
        if s.controller not in hosted
    ]
    return reasons


def wled_plan(rig: CompiledRig, fps: float, catalog: Catalog | None = None) -> list[str]:
    """Each streamed controller's DDP plan line, then one line per output
    for WLED's LED settings: its number (1 up, in the profile's order), its
    start from the board's pixel 0, its length and its fixtures."""
    catalog = catalog or load_catalog()
    lines: list[str] = []
    for (s, ctrl), board in zip(_hosted(rig), ddp_targets(rig)):
        lines.append(f"{board.describe(fps)}  board {ctrl.id}")
        outputs = [o.id for o in catalog.get(ctrl.profile, "controller").outputs]
        for out in (o for o in rig.slices if o.controller == ctrl.id):
            ids = [f.id for f in rig.fixtures if f.chain == out.chain]
            lines.append(
                f"  output {outputs.index(out.output) + 1}  start {out.start - s.start}  length {out.count}  "
                f"fixtures {ids[0]}..{ids[-1]} ({len(ids)})"
            )
    return lines


def rebind_host(data: bytes, controller: str, host: str, catalog: Catalog | None = None) -> bytes:
    """Arrangement file bytes with controller `controller`'s HOST changed to
    `host`; its port and every other byte are kept. Raises RigError when
    the file is a room map or does not compile, the controller or the host
    is not valid, or the change cannot be made exactly."""
    catalog = catalog or load_catalog()
    doc = read_doc(data)
    if is_room(doc):
        raise RigError([Issue.error("room_format", "the map is a room map file; migrate it first with "
                                    "`python -m pewpew rig migrate-room`, then run the arrangement")])
    compile_doc(doc, catalog)
    entries = doc.get("controllers") or []
    entry = next((c for c in entries if isinstance(c, dict) and c.get("id") == controller), None)
    old = None if entry is None else entry.get("host")
    if not isinstance(old, str):
        raise RigError([Issue.error("unresolved_ref", f"no controller {controller!r} with a host", controller)])
    if not board_host(host):
        raise RigError([Issue.error("bad_host", f"{host!r} is not {HOST_RULE}", controller)])
    _, colon, port = old.partition(":")
    new = host + colon + port
    expected = {**doc, "controllers": [{**c, "host": new} if c is entry else c for c in entries]}
    try:
        out = replace_string(data, old, new, expected)
    except ProblemsError as exc:
        raise RigError([Issue.error("not_rewritten", p, controller) for p in exc.problems]) from None
    compile_doc(expected, catalog)
    return out


def fixture_spans(rig: CompiledRig) -> tuple[tuple[str, int, int], ...]:
    """(id, first pixel, pixel count) of each fixture, in data order."""
    return tuple((f.id, f.pixel_start, f.pixel_count) for f in rig.fixtures)


# ---- what the preview draws -------------------------------------------------------


def _ends(rig: CompiledRig) -> list[tuple[np.ndarray, np.ndarray]]:
    """Each fixture's strip ends in plan-frame meters: its pixel 0 end, then
    the far end. A strip is as long as its `length` dim, which a placement's
    dims set (a variant type); any other type is as long as its pixels' span."""
    lengths = {v.id: v.dims["length"] for v in rig.variants if "length" in v.dims}
    out = []
    for f in rig.fixtures:
        spec = rig.types[f.type_id]
        m = np.asarray(f.matrix, dtype=np.float64).reshape(4, 4, order="F")
        rot, origin = m[:3, :3], m[:3, 3] + spec.z_m * m[:3, 2]
        half = lengths.get(f.type_id, spec.span_m) / 2.0 * rot[:, 1]
        out.append((MVR_C @ (origin - half), MVR_C @ (origin + half)))
    return out


def plan_view(rig: CompiledRig) -> dict[str, Any]:
    """The flat drawing of `rig`, JSON-ready: each fixture's strip ends
    normalized (x, y), its pitch in meters and its input end; each pixel's
    fixture; and the floor plan's corner, normalized, and its normalized
    units per image pixel."""

    def norm(point: np.ndarray | tuple[float, ...]) -> list[float]:
        return [round(float(point[k]) * rig.scale + rig.shift[k], 6) for k in range(2)]

    plan = None
    if rig.plan is not None:
        plan = {"corner": norm(rig.plan.corner), "unit": rig.plan.meters_per_pixel * rig.scale}
    return {
        "scale": rig.scale,
        "fixtures": [
            {
                "id": f.id,
                "pitch": rig.types[f.type_id].span_m / f.pixel_count,
                "start": norm(a),
                "end": norm(b),
                "input": "start",
            }
            for f, (a, b) in zip(rig.fixtures, _ends(rig))
        ],
        "fixture_of": rig.fixture_of.tolist(),
        "plan": plan,
    }


def rig_view(rig: CompiledRig) -> dict[str, Any]:
    """The `rig` of `hello` and `layout`, JSON-ready: what a 3D view needs
    to place each fixture and its pixels. `frame` is C, which takes the
    file's y-up meters to the plan frame the mapping is normalized from
    (`mapping = (C @ p) * scale + shift`). `plan` is the floor plan's
    top-left corner in plan-frame meters and its meters per image pixel."""
    # pixel_start and pixel_count are full resolution, and no index is sent: a 3D view of a
    # decimated hello (n < total) must map them through the same linspace as `pewpew.sinks.preview.View.of`.
    plan = None
    if rig.plan is not None:
        plan = {"corner_m": list(rig.plan.corner), "meters_per_pixel": rig.plan.meters_per_pixel}
    return {
        "catalog_digest": rig.catalog_digest,
        "frame": MVR_C.tolist(),
        "scale": rig.scale,
        "shift": list(rig.shift),
        "plan": plan,
        "fixtures": [
            {
                "id": f.id, "type_id": f.type_id, "base_type_id": f.base_type_id, "group": f.group,
                "matrix": list(f.matrix), "pixel_start": f.pixel_start, "pixel_count": f.pixel_count,
                "controller": f.controller, "output": f.output, "tags": list(f.tags), "dims": dict(f.dims),
            }
            for f in rig.fixtures
        ],
        "types": {
            tid: {
                "count": spec.count, "span_m": spec.span_m, "z_m": spec.z_m,
                "facing": None if spec.facing is None else list(spec.facing),
            }
            for tid, spec in rig.types.items()
        },
        "controllers": [c.model_dump(mode="json") for c in rig.controllers],
        "slices": [s.model_dump(mode="json") for s in rig.slices],
        "controller_slices": [s.model_dump(mode="json") for s in rig.controller_slices],
        "issues": [i.model_dump(mode="json") for i in rig.issues],
    }
