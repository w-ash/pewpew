"""Room map files: straight fixtures in meters, compiled for render and DDP.

A room map is a JSON file, a subset of ADR-007's fixture format shaped after
Chromatik `.lxf` [S309] (ADR-007 amendment 2026-10-30):

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

Geometry. Coordinates are meters on a plan: x to the right, y up the page,
and an optional third coordinate z for height (right-handed). A fixture is a
straight strip from `start` to `end`, or from `start` for `length` meters at
`angle` degrees counterclockwise from +x. Its `pixels` sit at `pitch`
centre to centre, centred on the strip; `pitch` defaults to length/pixels,
so the end pixels are inset half a pitch from each end of the strip. A
64-pixel bar 1 m long has a 1/64 m pitch, never 1/63 m: a strip is made of
identical segments with one LED each, sold as so many LEDs per meter
[S761][S762].

`instances` repeats a fixture `step` meters apart (an array, `.lxf`
`instances`): copy k of fixture "row" is "row.k", from k = 1, at chain
position chain + k - 1 on the same output.

Wiring. Each fixture names its `board` (declared in `boards` as
HOST[:PORT], HOST an IPv4 address or the board's mDNS name, such as
`pewpew-1.local`), its `output` (1 up) and its `chain` position on that
output (1 up), and the `input` end, "start" or "end", where data enters
it. Wire order is board (in declaration order), then output, then chain;
pixel 0 of a fixture is the one at its input end. Each board takes one
contiguous range of the map, and its outputs follow one another inside
that range.

Normalization is Contain, never Fill [S202]: one scale for every axis, so
the longest axis spans 0-1 and a wave crossing the room keeps its shape.
Each shorter axis is centred, spanning (1 - s)/2 to (1 + s)/2 where s is
its length over the longest, so (0.5, 0.5) is the middle of the room. An
axis with no extent (z in a flat room) is 0, as in `line` and `grid`.
`RoomMap.span` records what each axis spans.

Floor plan. An optional `plan` puts an image under the preview, calibrated
by two points a known distance apart (xLights' two-point ruler [S1279]):

    "plan": {"image": "plan.png", "points": [[120, 840], [1720, 840]],
             "meters": 8.0, "at": [0.0, 0.0]}

`image` is a .png, .jpg, .jpeg, .webp or .gif file, relative to the room
file. `points` are two image pixels (x right, y down, as image editors
show them) `meters` apart; `at` is where the first point sits in the room,
in meters (default [0, 0]). The image is not rotated: its x axis is the
room's x and its y axis runs down the page. Calibration is checked here;
whether the image exists is the preview's concern, so a missing image
never stops the run.

`label`, `notes` and each fixture's `tags` are the file's own: checked,
then not compiled. Compiling is pure and deterministic. Every error names
the fixture or board it concerns and never a path, so the same text can
cross the preview socket as a reload status.

Rebinding. `rebind_text` points one board at a new host by changing that
one string in the file's text, so a hand-formatted file keeps its layout.
It is what the page's "use for A" button writes (pewpew.room.live).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pewpew.jsonfile import ProblemsError, is_number, parse_json
from pewpew.mapping import contain
from pewpew.sinks.ddp import HOST_RULE, Board, board_host, parse_target

# WLED v16.0.1 `MAX_LEDS_PER_BUS` and `MAX_LEDS` (ESP32 and S3), from
# wled00/const.h at the v16.0.1 pin [S1250].
MAX_PER_OUTPUT = 2048
MAX_PER_BOARD = 16384

_TOP_KEYS = {"label", "notes", "boards", "fixtures", "plan"}
_PLAN_KEYS = {"image", "points", "meters", "at"}
_FIXTURE_KEYS = {
    "id", "pixels", "start", "end", "angle", "length", "pitch", "input",
    "board", "output", "chain", "tags", "instances", "step",
}
_EPS = 1e-9

# The floor-plan image types the preview serves, by file suffix. SVG is left
# out: opened as a page, it runs scripts on that origin.
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}


class RoomError(ProblemsError):
    """The room map is malformed or miswired."""


@dataclass(frozen=True)
class Fixture:
    """One compiled strip, in wire order."""

    id: str
    board: str
    output: int
    chain: int
    pixels: int
    first: int  # index of its pixel 0 in the map
    start: tuple[float, float, float]  # meters
    end: tuple[float, float, float]  # meters
    pitch: float  # meters, centre to centre
    input: str  # "start" or "end"


@dataclass(frozen=True)
class Plan:
    """A floor-plan image and its two-point calibration."""

    image: str  # relative to the room file
    points: tuple[tuple[float, float], tuple[float, float]]  # image pixels, y down
    meters: float  # distance between the two points
    at: tuple[float, float]  # room meters of the first point

    @property
    def meters_per_pixel(self) -> float:
        (u1, v1), (u2, v2) = self.points
        return self.meters / math.hypot(u2 - u1, v2 - v1)

    @property
    def corner(self) -> tuple[float, float]:
        """Room meters of the image's top-left corner."""
        (u1, v1), _ = self.points
        m = self.meters_per_pixel
        return (self.at[0] - u1 * m, self.at[1] + v1 * m)


@dataclass(frozen=True)
class OutputRange:
    """One board output's pixels: `start` counts from the board's pixel 0."""

    board: str
    output: int
    start: int
    count: int
    fixtures: tuple[str, ...]


@dataclass(frozen=True)
class RoomMap:
    """A compiled room: the mapping, the pixel-to-fixture table, and the boards."""

    fixtures: tuple[Fixture, ...]
    boards: tuple[Board, ...]  # in declaration order; ranges in wire order
    board_names: tuple[str, ...]
    outputs: tuple[OutputRange, ...]
    meters: np.ndarray  # (N,3) float64 pixel centres
    mapping: np.ndarray  # (N,3) float32, normalized by Contain
    fixture_of: np.ndarray  # (N,) intp, fixture index per pixel
    span: tuple[float, float, float]  # normalized extent per axis
    extent: tuple[float, float, float]  # meters per axis
    scale: float = 1.0  # normalized units per meter: 1 / the longest extent
    shift: tuple[float, float, float] = (0.0, 0.0, 0.0)  # normalized = meters * scale + shift
    floor_plan: Plan | None = None

    @property
    def n(self) -> int:
        return len(self.mapping)

    def plan_file(self, room_path: Path) -> Path | None:
        """The floor-plan image file, relative to the room file at
        `room_path`, or None without a plan."""
        return None if self.floor_plan is None else Path(room_path).parent / self.floor_plan.image

    def normalize(self, point: tuple[float, ...]) -> list[float]:
        """Room meters (x, y) -> the mapping's normalized (x, y)."""
        return [float(point[k]) * self.scale + self.shift[k] for k in range(2)]

    def describe(self) -> dict:
        """What the preview draws beyond the positions, JSON-ready: strip
        ends and plan corner normalized, pitch in meters."""
        plan = None
        if self.floor_plan is not None:
            plan = {
                "corner": [round(v, 6) for v in self.normalize(self.floor_plan.corner)],
                "unit": self.floor_plan.meters_per_pixel * self.scale,
            }
        return {
            "scale": self.scale,
            "fixtures": [
                {
                    "id": f.id, "pitch": f.pitch,
                    "start": [round(v, 6) for v in self.normalize(f.start)],
                    "end": [round(v, 6) for v in self.normalize(f.end)],
                    "input": f.input,
                }
                for f in self.fixtures
            ],
            "fixture_of": self.fixture_of.tolist(),
            "plan": plan,
        }

    def plan(self, fps: float) -> list[str]:
        """Each board's DDP plan line, then one line per output for WLED's LED settings."""
        lines = []
        for name, board in zip(self.board_names, self.boards):
            lines.append(f"{board.describe(fps)}  board {name}")
            for out in self.outputs:
                if out.board == name:
                    lines.append(
                        f"  output {out.output}  start {out.start}  length {out.count}  "
                        f"fixtures {out.fixtures[0]}..{out.fixtures[-1]} ({len(out.fixtures)})"
                    )
        return lines


def load_room(path: Path) -> tuple[RoomMap, bytes]:
    """Read and compile one room file; returns the map and the bytes it came
    from. Raises OSError as the filesystem does, RoomError for the content."""
    data = Path(path).read_bytes()
    return parse_room(data), data


def parse_room(data: bytes | str) -> RoomMap:
    """Compile room-map JSON text. Raises RoomError."""
    return compile_room(parse_json(data, RoomError))


def compile_room(doc: Any) -> RoomMap:
    """Compile a parsed room document. Raises RoomError listing every problem."""
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
    return _compile(specs, boards, plan)


# ---- parsing ----------------------------------------------------------------


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
        )
        for k, name in enumerate(names)
    ]


def _plan(raw: Any, problems: list[str]) -> Plan | None:
    """`plan` -> a Plan. The messages never repeat the image name, which is a path."""
    before = len(problems)

    def bad(message: str) -> None:
        problems.append(f"plan: {message}")

    if not isinstance(raw, dict):
        bad("must be an object with 'image', 'points' and 'meters'")
        return None
    for key in sorted(set(raw) - _PLAN_KEYS):
        bad(f"unknown key {key!r}; expected {', '.join(sorted(_PLAN_KEYS))}")
    image = raw.get("image")
    if not isinstance(image, str) or not image.strip():
        bad("needs an 'image' file name, relative to the room file")
    elif Path(image).suffix.lower() not in IMAGE_TYPES:
        bad(f"'image' must be a {', '.join(IMAGE_TYPES)} file")
    points = raw.get("points")
    pair: list[tuple[float, float]] = []
    if (
        not isinstance(points, list)
        or len(points) != 2
        or not all(isinstance(p, list) and len(p) == 2 and all(is_number(v) for v in p) for p in points)
    ):
        bad("'points' must be two image pixels, [[x, y], [x, y]]")
    else:
        pair = [(float(p[0]), float(p[1])) for p in points]
        if math.hypot(pair[1][0] - pair[0][0], pair[1][1] - pair[0][1]) <= _EPS:
            bad("the two 'points' are the same pixel; pick two points a known distance apart")
    meters = raw.get("meters")
    if not is_number(meters) or meters <= 0:
        bad("'meters' must be the positive distance between the two points")
    at = raw.get("at", [0.0, 0.0])
    if not isinstance(at, list) or len(at) != 2 or not all(is_number(v) for v in at):
        bad("'at' must be [x, y], the room meters of the first point")
    if len(problems) > before:
        return None
    assert isinstance(image, str) and is_number(meters)  # refused above otherwise
    return Plan(image, (pair[0], pair[1]), float(meters), (float(at[0]), float(at[1])))


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
        total = sum(spec.pixels for spec in chain)
        if total > MAX_PER_OUTPUT:
            problems.append(
                f"{where}: {total} px is over WLED's {MAX_PER_OUTPUT} per output "
                f"(fixtures {_names([s.id for s in sorted(chain, key=lambda s: s.chain)])})"
            )

    for name in boards:
        total = sum(spec.pixels for spec in specs if spec.board == name)
        if total == 0:
            problems.append(f"board {name!r} has no fixtures")
        elif total > MAX_PER_BOARD:
            problems.append(f"board {name!r}: {total} px is over WLED's {MAX_PER_BOARD} per board")

    # Two names for one device would send it two pixel ranges that both start
    # at its pixel 0: overlapping ranges on the wire.
    owner: dict[tuple[str, int], str] = {}
    for name, target in boards.items():
        if target in owner:
            problems.append(
                f"boards {owner[target]!r} and {name!r} both address {target[0]}:{target[1]}, "
                "so their pixel ranges overlap on one device"
            )
        else:
            owner[target] = name


def _names(ids: list[str]) -> str:
    return ", ".join(repr(i) for i in ids)


def _ints(values: list[int]) -> str:
    return ", ".join(str(v) for v in values)


# ---- compile -----------------------------------------------------------------


def _compile(specs: list[_Spec], boards: dict[str, tuple[str, int]], plan: Plan | None = None) -> RoomMap:
    order = list(boards)
    wired = sorted(specs, key=lambda s: (order.index(s.board), s.output, s.chain))
    fixtures: list[Fixture] = []
    points: list[np.ndarray] = []
    first = 0
    for spec in wired:
        direction = (spec.end - spec.start) / np.linalg.norm(spec.end - spec.start)
        mid = (spec.start + spec.end) / 2.0
        offsets = (np.arange(spec.pixels, dtype=np.float64) - (spec.pixels - 1) / 2.0) * spec.pitch
        line = mid + offsets[:, None] * direction
        points.append(line if spec.input == "start" else line[::-1])
        fixtures.append(
            Fixture(
                id=spec.id, board=spec.board, output=spec.output, chain=spec.chain,
                pixels=spec.pixels, first=first, start=tuple(spec.start), end=tuple(spec.end),
                pitch=spec.pitch, input=spec.input,
            )
        )
        first += spec.pixels
    meters = np.concatenate(points)
    fixture_of = np.repeat(np.arange(len(fixtures)), [f.pixels for f in fixtures])

    contained = contain(meters)
    for array in (meters, fixture_of):
        array.setflags(write=False)

    ddp_boards: list[Board] = []
    outputs: list[OutputRange] = []
    base = 0
    for name in order:
        mine = [f for f in fixtures if f.board == name]
        count = sum(f.pixels for f in mine)
        host, port = boards[name]
        ddp_boards.append(Board(host, base, count, port))
        for output in sorted({f.output for f in mine}):
            chain = [f for f in mine if f.output == output]
            outputs.append(
                OutputRange(
                    name, output, chain[0].first - base, sum(f.pixels for f in chain),
                    tuple(f.id for f in chain),
                )
            )
        base += count

    return RoomMap(
        fixtures=tuple(fixtures),
        boards=tuple(ddp_boards),
        board_names=tuple(order),
        outputs=tuple(outputs),
        meters=meters,
        mapping=contained.mapping,
        fixture_of=fixture_of,
        span=contained.span,
        extent=contained.extent,
        scale=contained.scale,
        shift=contained.shift,
        floor_plan=plan,
    )


# ---- rebinding -----------------------------------------------------------------


def rebind_text(data: bytes, board: str, host: str) -> bytes:
    """Room file bytes with board `board`'s HOST changed to `host`; its port
    and every other byte of the text are kept. Raises RoomError when the
    file does not compile, the board or the host is not valid, or the
    board's entry cannot be found exactly once in the text."""
    doc = parse_json(data, RoomError)
    compile_room(doc)
    target = doc["boards"].get(board)
    if not isinstance(target, str):
        raise RoomError([f"board {board!r} is not declared in 'boards'"])
    if not board_host(host):
        raise RoomError([f"board {board!r}: {host!r} is not {HOST_RULE}"])
    _, colon, port = target.partition(":")
    new_target = host + colon + port
    text = data.decode("utf-8")
    key = json.dumps(board, ensure_ascii=False)
    entry = re.compile(re.escape(key) + r"(\s*:\s*)" + re.escape(json.dumps(target)))
    found = entry.findall(text)
    if len(found) != 1:
        raise RoomError([
            (f"board {board!r}: its entry {key}: {json.dumps(target)} is not in the file "
             "exactly once; edit the room file by hand")
        ])
    new = entry.sub(lambda m: key + m.group(1) + json.dumps(new_target), text).encode("utf-8")
    # The edit must change that one value and nothing else.
    expected = {**doc, "boards": {**doc["boards"], board: new_target}}
    if parse_json(new, RoomError) != expected:
        why = f"board {board!r}: rewriting the entry changed more than its host; edit the room file by hand"
        raise RoomError([why])
    compile_room(expected)
    return new
