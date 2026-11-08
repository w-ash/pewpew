"""`room_to_arrangement`: a room map migrates to an arrangement that maps, wires and addresses alike."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fakes import LEGACY_ROOM, room_meters
from pewpew.__main__ import main
from pewpew.mapping import contain
from pewpew.rig import RigError, compile_rig, load_arrangement, load_catalog
from pewpew.rig.pose import MVR_C
from pewpew.rig.room_import import RoomError, _parse, room_to_arrangement
from pewpew.rig.runtime import RoomFormatWarning, ddp_targets, load_rig, parse_rig, wled_plan
from pewpew.sinks.ddp import Board, parse_target

ROOT = Path(__file__).resolve().parent.parent
ROOM_FILE = ROOT / "examples" / "room-60-bars.json"
ARRANGEMENT_FILE = ROOT / "examples" / "canopy-60-bars.arrangement.json"
PROFILE = "esp32s3-devkitc1-ahct125"
TYPE = "strip"  # the parametric catalog type; the CLI's default
CATALOG = load_catalog()


def migrate(doc):
    return room_to_arrangement(doc, controller_profile=CATALOG.get(PROFILE, "controller"), fixture_type=TYPE)


def assert_equivalent(doc):
    """The room and its migration give one mapping, order, id set and address table."""
    names, wired, _ = _parse(doc)
    arrangement = migrate(doc)
    rig = compile_rig(load_arrangement(arrangement), CATALOG)
    assert not [i for i in rig.issues if i.level in ("error", "violation")]

    meters = room_meters(doc)
    extent = np.ptp(meters, axis=0)
    assert np.abs(rig.positions_m @ MVR_C.T - meters).max() <= 1e-9 * max(1.0, float(extent.max()))
    expected = contain(meters).mapping
    assert rig.mapping.shape == expected.shape
    assert np.abs(rig.mapping.astype(np.float64) - expected).max() <= 1e-7

    firsts = np.cumsum([0, *(s.pixels for s in wired)])
    assert [(s.id, int(first), s.pixels) for s, first in zip(wired, firsts)] == [
        (f.id, f.pixel_start, f.pixel_count) for f in rig.fixtures
    ]

    # DDP: one target per board, its host and port, its contiguous pixel range.
    expected_boards, start = [], 0
    for name in names:
        count = sum(s.pixels for s in wired if s.board == name)
        host, port = parse_target(doc["boards"][name])
        expected_boards.append(Board(host, start, count, port))
        start += count
    assert ddp_targets(rig) == tuple(expected_boards)

    # WLED's LED settings: each output's start (from its board's pixel 0) and length.
    by_controller = {s.controller: s for s in rig.controller_slices}
    outputs = [o.id for o in CATALOG.get(PROFILE, "controller").outputs]
    per_output: dict[tuple[str, int], int] = {}
    for s in wired:
        per_output[s.board, s.output] = per_output.get((s.board, s.output), 0) + s.pixels
    expected_outputs, board_start = [], {}
    for name in names:
        board_start[name] = 0
    for (board, output), count in per_output.items():
        expected_outputs.append((board, output, board_start[board], count))
        board_start[board] += count
    assert expected_outputs == [
        (s.controller, outputs.index(s.output) + 1, s.start - by_controller[s.controller].start, s.count)
        for s in rig.slices
    ]
    return wired, arrangement, rig


def test_the_example_room_migrates_equivalently():
    doc = json.loads(ROOM_FILE.read_text())
    wired, arrangement, _ = assert_equivalent(doc)
    assert arrangement["name"] == doc["label"] and arrangement["notes"] == doc["notes"]
    assert {t for f in arrangement["fixtures"] for t in f["tags"]} == {"canopy"}
    assert [f["id"] for f in arrangement["fixtures"]] == [s.id for s in wired]
    assert wired[0].id == "row01.1"


WLED_PLAN = """\
ddp 10.0.0.11:4048  pixels 0-1279 (1280)  3 packets/frame  154,800 B/s at 40 fps  board A
  output 1  start 0  length 320  fixtures row01.1..row01.5 (5)
  output 2  start 320  length 320  fixtures row02.1..row02.5 (5)
  output 3  start 640  length 320  fixtures row03.1..row03.5 (5)
  output 4  start 960  length 320  fixtures row04.1..row04.5 (5)
ddp 10.0.0.12:4048  pixels 1280-2559 (1280)  3 packets/frame  154,800 B/s at 40 fps  board B
  output 1  start 0  length 320  fixtures row05.1..row05.5 (5)
  output 2  start 320  length 320  fixtures row06.1..row06.5 (5)
  output 3  start 640  length 320  fixtures row07.1..row07.5 (5)
  output 4  start 960  length 320  fixtures row08.1..row08.5 (5)
ddp 10.0.0.13:4048  pixels 2560-3839 (1280)  3 packets/frame  154,800 B/s at 40 fps  board C
  output 1  start 0  length 320  fixtures row09.1..row09.5 (5)
  output 2  start 320  length 320  fixtures row10.1..row10.5 (5)
  output 3  start 640  length 320  fixtures row11.1..row11.5 (5)
  output 4  start 960  length 320  fixtures row12.1..row12.5 (5)
""".splitlines()


def test_the_canopy_prints_the_plan_the_room_compiler_printed():
    rig, _ = load_rig(ARRANGEMENT_FILE)
    assert wled_plan(rig, 40.0) == WLED_PLAN


def test_the_legacy_room_read_in_place_gives_the_same_rig():
    rig, _ = load_rig(ARRANGEMENT_FILE)
    with pytest.warns(RoomFormatWarning):
        legacy, _ = load_rig(LEGACY_ROOM)
    assert legacy.mapping.tobytes() == rig.mapping.tobytes()
    assert wled_plan(legacy, 40.0) == WLED_PLAN


def test_the_checked_in_example_is_what_the_verb_writes():
    doc = json.loads(ROOM_FILE.read_text())
    assert json.loads(ARRANGEMENT_FILE.read_text()) == json.loads(json.dumps(migrate(doc)))


def test_a_floor_plan_carries_over():
    doc = json.loads(ROOM_FILE.read_text())
    doc["plan"] = {"image": "plan.png", "points": [[10, 20], [110, 20]], "meters": 2.0, "at": [0.5, 0.25]}
    _, arrangement, rig = assert_equivalent(doc)
    assert arrangement["plan"] == doc["plan"]
    assert rig.plan is not None and rig.plan.image == "plan.png"


def test_an_output_the_profile_lacks_is_refused():
    doc = json.loads(ROOM_FILE.read_text())
    doc["fixtures"][0]["output"] = 5
    with pytest.raises(RigError) as exc:
        migrate(doc)
    assert [i.code for i in exc.value.issues] == ["output_missing"]


def test_a_bad_room_is_refused_with_the_rooms_own_message():
    doc = json.loads(ROOM_FILE.read_text())
    del doc["boards"]
    with pytest.raises(RoomError):
        migrate(doc)


# ---- generated rooms -----------------------------------------------------------

tenths = st.integers(-100, 100).map(lambda v: v / 10)


@st.composite
def fixture_entry(draw, serial, board, output, chain):
    """One `fixtures` entry; returns (entry, the chain position after it)."""
    pixels = draw(st.integers(1, 40))
    entry = {
        "id": f"f{serial}",
        "pixels": pixels,
        "input": draw(st.sampled_from(["start", "end"])),
        "board": board,
        "output": output,
        "chain": chain,
    }
    dims = draw(st.sampled_from([2, 3]))  # 3: with a height, vertical strips included
    start = [draw(tenths) for _ in range(dims)]
    entry["start"] = start
    if draw(st.booleans()):
        entry["length"] = draw(st.integers(5, 40)) / 10
        entry["angle"] = draw(st.floats(0, 360, allow_nan=False))
    else:
        delta = draw(st.lists(tenths, min_size=dims, max_size=dims).filter(any))
        entry["end"] = [s + d for s, d in zip(start, delta)]
    if draw(st.booleans()):
        length = _length(entry)
        entry["pitch"] = length / pixels * draw(st.sampled_from([0.5, 0.75, 1.0]))
    instances = draw(st.sampled_from([1, 1, 2, 3]))
    if instances > 1:
        entry["instances"] = instances
        entry["step"] = [draw(tenths), draw(tenths)] + ([draw(tenths)] if draw(st.booleans()) else [])
    if draw(st.booleans()):
        entry["tags"] = draw(st.lists(st.sampled_from(["a", "b", "canopy"]), max_size=2, unique=True))
    return entry, chain + instances


def _length(entry):
    if "length" in entry:
        return entry["length"]
    start, end = np.array([*entry["start"], 0.0][:3]), np.array([*entry["end"], 0.0][:3])
    return float(np.linalg.norm(end - start))


@st.composite
def rooms(draw):
    names = draw(st.sampled_from([["A"], ["A", "B"], ["A", "B", "C"]]))
    hosts = [f"192.0.2.{10 + i}" if draw(st.booleans()) else f"pewpew-{i}.local:4048" for i in range(len(names))]
    fixtures: list[dict] = []
    for board in names:
        for output in sorted(draw(st.sets(st.integers(1, 4), min_size=1))):
            chain = 1
            for _ in range(draw(st.integers(1, 3))):
                entry, chain = draw(fixture_entry(len(fixtures) + 1, board, output, chain))
                fixtures.append(entry)
    doc = {"boards": dict(zip(names, hosts)), "fixtures": draw(st.permutations(fixtures))}
    if draw(st.booleans()):
        doc["label"] = "A generated room"
    if draw(st.booleans()):
        doc["notes"] = "Notes."
    return doc


@given(rooms())
def test_generated_rooms_migrate_equivalently(doc):
    *_, rig = assert_equivalent(doc)
    with pytest.warns(RoomFormatWarning):
        in_place = parse_rig(json.dumps(doc))
    assert in_place.to_json() == rig.to_json()


def test_the_migration_is_deterministic():
    doc = json.loads(ROOM_FILE.read_text())
    assert json.dumps(migrate(doc)) == json.dumps(migrate(doc))


# ---- the verb --------------------------------------------------------------------


def run(*argv):
    return main(["rig", "migrate-room", *map(str, argv)])


def test_the_verb_writes_the_output_file_only(tmp_path):
    room = tmp_path / "room.json"
    room.write_bytes(ROOM_FILE.read_bytes())
    out = tmp_path / "rig.json"
    assert run(room, "-o", out) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["rig.json", "room.json"]
    assert room.read_bytes() == ROOM_FILE.read_bytes()
    assert json.loads(out.read_text()) == json.loads(ARRANGEMENT_FILE.read_text())
    load_arrangement(out)


def test_the_verb_refuses_to_overwrite(tmp_path, capsys):
    out = tmp_path / "rig.json"
    out.write_text("keep")
    with pytest.raises(SystemExit) as exc:
        run(ROOM_FILE, "-o", out)
    assert "already exists" in str(exc.value)
    assert out.read_text() == "keep"
    # The room file itself is never the output.
    with pytest.raises(SystemExit):
        run(ROOM_FILE, "-o", ROOM_FILE)


def test_the_verb_refuses_a_dangling_symlink_as_existing(tmp_path):
    out = tmp_path / "rig.json"
    out.symlink_to(tmp_path / "elsewhere.json")
    with pytest.raises(SystemExit) as exc:
        run(ROOM_FILE, "-o", out)
    assert "already exists" in str(exc.value)
    assert not (tmp_path / "elsewhere.json").exists()


def test_the_verb_exits_with_one_line_when_the_output_directory_is_missing(tmp_path):
    out = tmp_path / "missing" / "rig.json"
    with pytest.raises(SystemExit) as exc:
        run(ROOM_FILE, "-o", out)
    message = str(exc.value)
    assert "\n" not in message
    assert str(out) in message
    assert "No such file or directory" in message
    assert not out.parent.exists()


def test_the_verb_exits_nonzero_and_writes_nothing_when_the_profile_does_not_fit(tmp_path, capsys):
    doc = json.loads(ROOM_FILE.read_text())
    doc["fixtures"][0]["output"] = 5
    room = tmp_path / "room.json"
    room.write_text(json.dumps(doc))
    out = tmp_path / "rig.json"
    assert run(room, "-o", out) == 1
    assert not out.exists()
    assert "output_missing" in capsys.readouterr().err


def test_the_verb_names_a_bad_room_and_writes_nothing(tmp_path):
    room = tmp_path / "room.json"
    room.write_text('{"boards": {}}')
    out = tmp_path / "rig.json"
    with pytest.raises(SystemExit) as exc:
        run(room, "-o", out)
    assert "room.json" in str(exc.value)
    assert not out.exists()


def test_the_verb_refuses_an_unknown_controller_or_type(tmp_path):
    out = tmp_path / "rig.json"
    for flag in ("--controller", "--type"):
        with pytest.raises(SystemExit) as exc:
            run(ROOM_FILE, "-o", out, flag, "nothing-like-this")
        assert flag in str(exc.value)
    assert not out.exists()
