"""Room map to arrangement: a pure migration of a room file's meaning.

A room map is the older rig file. It is read for one more release
(`pewpew.rig.runtime.parse_rig` migrates one in memory, with a warning) and
converted for good by `python -m pewpew rig migrate-room`. Its format:

    {
      "label": "Example room",
      "boards": {"A": "10.0.0.11", "B": "pewpew-2.local:4048"},
      "fixtures": [
        {"id": "west", "pixels": 64, "start": [0.2, 1.0], "end": [0.2, 2.0],
         "input": "start", "board": "A", "output": 1, "chain": 1},
        {"id": "row", "pixels": 64, "length": 1.0, "start": [1.1, 0.8], "angle": 0,
         "input": "end", "board": "B", "output": 1, "chain": 1,
         "instances": 5, "step": [1.2, 0.0], "tags": ["canopy"]}
      ]
    }

Coordinates are meters on a plan: x right, y up the page, an optional z for
height. A fixture is a straight strip from `start` to `end`, or from
`start` for `length` meters at `angle` degrees counterclockwise from +x.
Its `pixels` sit at `pitch` centre to centre, centred on the strip; `pitch`
defaults to length/pixels [S761][S762]. `instances` repeats a fixture `step`
meters apart: copy k of "row" is "row.k", from k = 1, at chain position
chain + k - 1. Each fixture names its `board` (HOST[:PORT] in `boards`),
its `output` (1 up), its `chain` position (1 up) and the `input` end where
data enters it. An optional `plan` is a floor plan (`pewpew.floorplan`).

`room_to_arrangement` returns an arrangement dict that `compile_rig`
compiles to the same mapping, pixel order, fixture ids and DDP ranges:

- A board becomes a controller with its `host`. Output n becomes the
  profile's n-th output, and each (board, output) a chain `BOARD-N`.
- Every fixture, `instances` copies included, becomes a free fixture with
  the room's id (`row.3`), its tags, and `dims` for its pixels, length and
  pitch.
- A free fixture's pixel 0 sits at local -y. The pose is the strip midpoint
  with `aim` along the strip from its input end to its far end, so the
  room's `input` end is in the pose and no field carries it.
- The room's plan frame (x right, y up the plan, z height) goes to the
  arrangement's y-up frame by C^T, where C is `MVR_C`.
- `label` becomes `name`; `notes` and `plan` carry over.

The room's own checks run first, and a room that fails them raises
`RoomError`; every message names the fixture or board and never a path.
The pixel caps are the arrangement's (`output_over_cap`,
`controller_over_cap`). Nothing is guessed: an output the profile lacks
raises `RigError`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from pewpew.floorplan import Plan, parse_plan
from pewpew.jsonfile import ProblemsError, is_number
from pewpew.rig.models import Controller, Issue, RigError
from pewpew.rig.pose import MVR_C
from pewpew.sinks.ddp import parse_target, shared_targets

_TOP_KEYS = {"label", "notes", "boards", "fixtures", "plan"}
_FIXTURE_KEYS = {
    "id", "pixels", "start", "end", "angle", "length", "pitch", "input",
    "board", "output", "chain", "tags", "instances", "step",
}
_EPS = 1e-9


class RoomError(ProblemsError):
    """The room map is malformed or miswired."""


def is_room(doc: Any) -> bool:
    """Whether the parsed document `doc` is a room map: an object with
    `boards` and no `format`, which every arrangement has."""
    return isinstance(doc, dict) and "format" not in doc and "boards" in doc


def room_to_arrangement(doc: Any, *, controller_profile: Controller, fixture_type: str) -> dict[str, Any]:
    """The arrangement dict for the parsed room document `doc`.

    `controller_profile` is the catalog controller every board becomes and
    `fixture_type` the parametric catalog type every strip becomes; it takes
    the dims `pixels`, `length` and `pitch`. Raises `RoomError` for a room
    that does not parse and `RigError` for an output the profile lacks.
    Numbers are kept to 12 significant digits. The result is not yet
    validated; load it with `load_arrangement`.
    """
    boards, wired, plan = _parse(doc)
    outputs = [o.id for o in controller_profile.outputs]
    missing = sorted({s.output for s in wired if s.output > len(outputs)})
    if missing:
        raise RigError([
            Issue.error(
                "output_missing",
                f"output {n} does not exist on {controller_profile.id!r}, which has {len(outputs)} outputs",
            )
            for n in missing
        ])
    chains: dict[tuple[str, int], list[_Spec]] = {}
    for spec in wired:
        chains.setdefault((spec.board, spec.output), []).append(spec)
    out: dict[str, Any] = {"format": "pewpew.arrangement", "version": 1}
    if doc.get("label"):
        out["name"] = doc["label"]
    if doc.get("notes"):
        out["notes"] = doc["notes"]
    out["controllers"] = [
        {"id": name, "profile": controller_profile.id, "host": doc["boards"][name]} for name in boards
    ]
    out["fixtures"] = [_placement(s, fixture_type) for s in wired]
    out["wiring"] = {
        "chains": [
            {
                "id": f"{board}-{output}",
                "controller": board,
                "output": outputs[output - 1],
                "fixtures": [s.id for s in chain],
            }
            for (board, output), chain in chains.items()
        ]
    }
    if plan is not None:
        out["plan"] = plan.to_json()
    return out


def _parse(doc: Any) -> tuple[list[str], list[_Spec], Plan | None]:
    """The board names in declaration order, the fixtures in wire order
    (board, then output, then chain) and the plan of the room document
    `doc`. Raises RoomError listing every problem."""
    problems: list[str] = []
    if not isinstance(doc, dict):
        raise RoomError(["a room map is a JSON object with 'boards' and 'fixtures'"])
    for key in sorted(set(doc) - _TOP_KEYS):
        problems.append(f"unknown key {key!r}; expected {', '.join(sorted(_TOP_KEYS))}")
    if not isinstance(doc.get("label", ""), str):
        problems.append("'label' must be a string")
    boards = _boards(doc.get("boards"), problems)
    raw = doc.get("fixtures")
    if not isinstance(raw, list) or not raw:
        problems.append("'fixtures' must be a non-empty list")
        raw = []
    specs: list[_Spec] = []
    for i, item in enumerate(raw):
        specs.extend(_fixture(item, i, boards, problems))
    plan = _plan(doc["plan"], problems) if "plan" in doc else None
    if problems:
        raise RoomError(problems)
    _check_wiring(specs, boards, problems)
    if problems:
        raise RoomError(problems)
    order = list(boards)
    return order, sorted(specs, key=lambda s: (order.index(s.board), s.output, s.chain)), plan


def _placement(spec: _Spec, fixture_type: str) -> dict[str, Any]:
    near, far = (spec.start, spec.end) if spec.input == "start" else (spec.end, spec.start)
    length = float(np.linalg.norm(spec.end - spec.start))
    placement: dict[str, Any] = {
        "id": spec.id,
        "type": fixture_type,
        "pose": {
            "position_m": _vec(MVR_C.T @ ((spec.start + spec.end) / 2.0)),
            "aim": {"axis": _vec(MVR_C.T @ (far - near))},
        },
        "dims": {"pixels": spec.pixels, "length": _clean(length), "pitch": _clean(spec.pitch)},
    }
    if spec.tags:
        placement["tags"] = list(spec.tags)
    return placement


def _vec(v: np.ndarray) -> list[float]:
    return [_clean(float(c)) for c in v]


def _clean(x: float) -> float:
    """`x` to 12 significant digits, so a sum such as 1.1 + 3 * 1.2 reads 5.2;
    the error is far below the mapping's float32 steps."""
    return float(f"{x:.12g}") + 0.0  # + 0.0 turns -0.0 into 0.0


# ---- parsing -----------------------------------------------------------------


@dataclass(frozen=True)
class _Spec:
    id: str
    pixels: int
    start: np.ndarray  # (3,) float64
    end: np.ndarray
    pitch: float
    input: str
    board: str
    output: int
    chain: int
    tags: tuple[str, ...] = ()


def _boards(raw: Any, problems: list[str]) -> dict[str, tuple[str, int]]:
    """`boards` -> {name: (host, port)}, in declaration order, each per
    `pewpew.sinks.ddp.parse_target`. Compiling looks no name up:
    `pewpew.health.HealthMonitor` does, off the loop."""
    if not isinstance(raw, dict) or not raw:
        problems.append("'boards' must map each board name to HOST or HOST:PORT")
        return {}
    out: dict[str, tuple[str, int]] = {}
    for name, target in raw.items():
        try:
            out[name] = parse_target(target if isinstance(target, str) else "")  # a non-string as no host
        except ValueError as exc:
            problems.append(f"board {name!r}: {exc}")
    return out


def _fixture(item: Any, i: int, boards: dict, problems: list[str]) -> list[_Spec]:
    """One `fixtures` entry, expanded to its instances."""
    if not isinstance(item, dict):
        problems.append(f"fixtures[{i}] must be an object")
        return []
    fid = item.get("id")
    if not isinstance(fid, str) or not fid:
        problems.append(f"fixtures[{i}] needs an 'id' string")
        return []
    before = len(problems)

    def bad(message: str) -> None:
        problems.append(f"fixture {fid!r}: {message}")

    for key in sorted(set(item) - _FIXTURE_KEYS):
        bad(f"unknown key {key!r}; expected {', '.join(sorted(_FIXTURE_KEYS))}")
    pixels = _count(item, "pixels", bad)
    output = _count(item, "output", bad)
    chain = _count(item, "chain", bad)
    instances = _count(item, "instances", bad, default=1)
    board = item.get("board")
    if not isinstance(board, str):
        bad("needs a 'board' name")
    elif boards and board not in boards:
        bad(f"board {board!r} is not declared in 'boards'")
    end_name = item.get("input")
    if end_name is None:
        bad('has no input end; set "input" to "start" or "end"')
    elif end_name not in ("start", "end"):
        bad(f'input must be "start" or "end", got {end_name!r}')
    tags = item.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        bad("'tags' must be a list of strings")

    start = _point(item, "start", bad)
    end = None
    if "end" in item:
        if "angle" in item or "length" in item:
            bad("give 'end', or 'angle' and 'length', not both")
        end = _point(item, "end", bad)
    elif "angle" in item:
        angle, length = item.get("angle"), item.get("length")
        if not is_number(angle):
            bad("'angle' must be a number of degrees")
        elif not is_number(length) or length <= 0:
            bad("'angle' needs a positive 'length' in meters")
        elif start is not None:
            rad = math.radians(angle)
            end = start + length * np.array([math.cos(rad), math.sin(rad), 0.0])
    else:
        bad("give 'end', or 'angle' and 'length'")
    length_m = float(np.linalg.norm(end - start)) if start is not None and end is not None else 0.0
    if start is not None and end is not None and length_m <= 0.0:
        bad("'start' and 'end' are the same point")

    pitch = None
    if "pitch" in item:
        pitch = item["pitch"]
        if not is_number(pitch) or pitch <= 0:
            bad("'pitch' must be a positive number of meters")
            pitch = None
        elif pixels and length_m > 0 and pixels * pitch > length_m + _EPS:
            bad(f"{pixels} px at a {pitch:g} m pitch need {pixels * pitch:g} m; the strip is {length_m:g} m")
    step = np.zeros(3)
    if instances and instances > 1:
        step_pt = _point(item, "step", bad)
        if step_pt is not None:
            step = step_pt
    elif "step" in item:
        bad("'step' needs 'instances' above 1")

    if len(problems) > before:
        return []
    assert start is not None and end is not None and pixels and output and chain and instances
    if pitch is None:
        pitch = length_m / pixels
    names = [fid] if instances == 1 else [f"{fid}.{k}" for k in range(1, instances + 1)]
    return [
        _Spec(
            id=name,
            pixels=pixels,
            start=start + k * step,
            end=end + k * step,
            pitch=float(pitch),
            input=end_name,  # type: ignore[arg-type]
            board=board,  # type: ignore[arg-type]
            output=output,
            chain=chain + k,
            tags=tuple(tags),
        )
        for k, name in enumerate(names)
    ]


def _plan(raw: Any, problems: list[str]) -> Plan | None:
    plan, found = parse_plan(raw)
    problems.extend(f"plan: {p}" for p in found)
    return plan


def _count(item: dict, key: str, bad, default: int | None = None) -> int | None:
    value = item.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        bad(f"{key!r} must be a whole number from 1")
        return None
    return value


def _point(item: dict, key: str, bad) -> np.ndarray | None:
    value = item.get(key)
    if (
        not isinstance(value, list)
        or len(value) not in (2, 3)
        or not all(is_number(v) for v in value)
    ):
        bad(f"{key!r} must be [x, y] or [x, y, z] in meters")
        return None
    return np.array([*value, 0.0][:3], dtype=np.float64)


# ---- wiring checks (after xLights' model chains and controller visualizer) ---


def _check_wiring(specs: list[_Spec], boards: dict, problems: list[str]) -> None:
    seen: dict[str, int] = {}
    for spec in specs:
        seen[spec.id] = seen.get(spec.id, 0) + 1
    for fid, count in seen.items():
        if count > 1:
            problems.append(f"fixture id {fid!r} is used {count} times")

    by_output: dict[tuple[str, int], list[_Spec]] = {}
    for spec in specs:
        by_output.setdefault((spec.board, spec.output), []).append(spec)
    for (board, output), chain in sorted(by_output.items(), key=lambda kv: (list(boards).index(kv[0][0]), kv[0][1])):
        where = f"board {board!r} output {output}"
        positions: dict[int, list[str]] = {}
        for spec in chain:
            positions.setdefault(spec.chain, []).append(spec.id)
        for pos, ids in sorted(positions.items()):
            if len(ids) > 1:
                problems.append(f"{where}: chain position {pos} is claimed by {_names(ids)}")
        expected = set(range(1, max(positions) + 1))
        missing = sorted(expected - set(positions))
        if missing:
            first_after = min(p for p in positions if p > missing[0])
            problems.append(
                f"{where}: chain position {_ints(missing)} is empty, "
                f"so fixture {positions[first_after][0]!r} at {first_after} has a gap before it"
            )

    for name in boards:
        if not any(spec.board == name for spec in specs):
            problems.append(f"board {name!r} has no fixtures")

    for first, name, (host, port) in shared_targets(boards.items()):
        problems.append(
            f"boards {first!r} and {name!r} both address {host}:{port}, so their pixel ranges overlap on one device"
        )


def _names(ids: list[str]) -> str:
    return ", ".join(repr(i) for i in ids)


def _ints(values: list[int]) -> str:
    return ", ".join(str(v) for v in values)
