"""Room map files: compile, wiring checks, live reload, CLI."""

from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from fakes import EXAMPLE_ROOM, FLOW, bar, ddp_sink, hosted, looks_file, room, run_main, source_op
from pewpew.crossfade import Crossfader
from pewpew.pace import Calls
from pewpew.room.blink import Blink
from pewpew.room.live import RoomLive
from pewpew.room.map import MAX_PER_OUTPUT, RoomError, compile_room, load_room, parse_room, rebind_text
from pewpew.sinks.ddp import Board

PITCH = 1.0 / 64
TWO_BARS = room(bar("a"), bar("b", chain=2, start=[0.0, 1.0], end=[1.0, 1.0]))


# ---- compiling the example ---------------------------------------------------


def test_example_compiles_to_three_boards_of_1280_in_wire_order(example):
    assert example.n == 3840 and len(example.fixtures) == 60
    assert [(b.host, b.start, b.count) for b in example.boards] == [
        ("10.0.0.11", 0, 1280), ("10.0.0.12", 1280, 1280), ("10.0.0.13", 2560, 1280),
    ]
    assert [(o.board, o.output, o.start, o.count) for o in example.outputs[:5]] == [
        ("A", 1, 0, 320), ("A", 2, 320, 320), ("A", 3, 640, 320), ("A", 4, 960, 320), ("B", 1, 0, 320),
    ]
    assert [f.id for f in example.fixtures[:6]] == [
        "row01.1", "row01.2", "row01.3", "row01.4", "row01.5", "row02.1",
    ]
    assert [f.first for f in example.fixtures[:3]] == [0, 64, 128]
    assert np.array_equal(example.fixture_of, np.repeat(np.arange(60), 64))


def test_pitch_is_length_over_pixels_with_centres_inset_half_a_pitch(example):
    first = example.meters[:64]
    assert np.allclose(np.diff(first[:, 0]), PITCH)  # 1/64 m, not 1/63
    assert first[0, 0] == pytest.approx(1.1 + PITCH / 2)
    assert first[-1, 0] == pytest.approx(2.1 - PITCH / 2)
    # Board B feeds its rows from the east end: pixel 0 is at the strip's end.
    b0 = example.fixtures[20]
    assert (b0.board, b0.input) == ("B", "end")
    assert example.meters[b0.first, 0] == pytest.approx(2.1 - PITCH / 2)
    assert example.meters[b0.first + 1, 0] < example.meters[b0.first, 0]


def test_contain_keeps_aspect_and_centres_the_short_axis(example):
    m = example.mapping
    assert m.dtype == np.float32 and m.shape == (3840, 3)
    assert m[:, 0].min() == 0.0 and m[:, 0].max() == 1.0
    extent_x, extent_y, _ = example.extent
    assert example.span == (1.0, pytest.approx(extent_y / extent_x), 0.0)
    assert m[:, 1].min() + m[:, 1].max() == pytest.approx(1.0)  # centred
    assert np.ptp(m[:, 1]) == pytest.approx(example.span[1], abs=1e-6)
    assert not m[:, 2].any()  # a flat room's z is 0, as in grid()
    # One scale for both axes: normalized distances keep the metric ratio.
    assert np.ptp(m[:, 1]) / np.ptp(m[:, 0]) == pytest.approx(extent_y / extent_x, rel=1e-6)


def test_compile_is_deterministic_and_read_only():
    a, data = load_room(EXAMPLE_ROOM)
    b = parse_room(data)
    assert np.array_equal(a.mapping, b.mapping) and a.mapping.tobytes() == b.mapping.tobytes()
    with pytest.raises(ValueError):
        a.mapping[0, 0] = 1.0


def test_angle_form_matches_the_end_form_and_pitch_centres_the_pixels():
    by_end = compile_room(room(bar(start=[1.0, 2.0], end=[1.0, 3.0])))
    by_angle = compile_room(room(bar(start=[1.0, 2.0], end=None, angle=90, length=1.0)))
    assert np.allclose(by_end.meters, by_angle.meters)
    short = compile_room(room(bar(pixels=10, pitch=0.05)))  # 0.5 m of pixels on a 1 m strip
    assert short.meters[0, 0] == pytest.approx(0.275) and short.meters[-1, 0] == pytest.approx(0.725)


def test_instances_step_the_fixture_and_its_chain_position():
    r = compile_room(room(bar("wall", instances=3, step=[0.0, 0.5])))
    assert [(f.id, f.chain) for f in r.fixtures] == [("wall.1", 1), ("wall.2", 2), ("wall.3", 3)]
    assert r.meters[64, 1] == pytest.approx(0.5) and r.meters[128, 1] == pytest.approx(1.0)


def test_a_third_coordinate_is_height():
    r = compile_room(room(bar(start=[0.0, 0.0, 0.0], end=[0.0, 0.0, 2.0])))
    assert r.mapping[:, 2].min() == 0.0 and r.mapping[:, 2].max() == 1.0


# ---- wiring checks -----------------------------------------------------------


def _drop(spec, key):
    spec = dict(spec)
    del spec[key]
    return spec


@pytest.mark.parametrize(
    "doc, message",
    [
        (room(bar("long", instances=33, step=[1.0, 0.0])),
         f"board 'A' output 1: 2112 px is over WLED's {MAX_PER_OUTPUT} per output"),
        (room(bar("a"), bar("b", chain=2), bar("c", chain=4)),
         "board 'A' output 1: chain position 3 is empty, so fixture 'c' at 4 has a gap before it"),
        (room(bar("a"), bar("b")), "board 'A' output 1: chain position 1 is claimed by 'a', 'b'"),
        (room(bar("a"), bar("b", board="B"), boards={"A": "10.0.0.11", "B": "10.0.0.11:4048"}),
         "boards 'A' and 'B' both address 10.0.0.11:4048, so their pixel ranges overlap"),
        (room(_drop(bar("west"), "input")),
         """fixture 'west': has no input end; set "input" to "start" or "end\""""),
        (room(bar("west", input="left")), "fixture 'west': input must be"),
        (room(bar("west", board="Z")), "fixture 'west': board 'Z' is not declared"),
        (room(bar("a"), boards={"A": "10.0.0.11", "B": "10.0.0.12"}), "board 'B' has no fixtures"),
        (room(bar("a"), boards={"A": "lights.example.com:4048"}),
         "board 'A': 'lights.example.com' is not an IPv4 address or an mDNS name such as pewpew-1.local"),
        (room(bar("a"), bar("b", board="B"), boards={"A": "pewpew-1.local", "B": "pewpew-1.local:4048"}),
         "boards 'A' and 'B' both address pewpew-1.local:4048"),
        (room(bar("a"), bar("a", chain=2)), "fixture id 'a' is used 2 times"),
        (room(bar("a", chian=2)), "fixture 'a': unknown key 'chian'; expected angle, board, chain,"),
        (room(bar("a", pitch=0.02)), "fixture 'a': 64 px at a 0.02 m pitch need 1.28 m"),
        (room(bar("a", angle=0)), "fixture 'a': give 'end', or 'angle' and 'length', not both"),
        (room(bar("a", output=0)), "fixture 'a': 'output' must be a whole number from 1"),
    ],
)
def test_wiring_check_names_the_fixture(doc, message):
    with pytest.raises(RoomError) as exc:
        compile_room(doc)
    assert message in str(exc.value)
    assert "\n" not in str(exc.value)


def test_every_problem_is_reported_at_once():
    with pytest.raises(RoomError) as exc:
        compile_room(room(_drop(bar("a"), "input"), bar("b", board="Z")))
    assert len(exc.value.problems) == 2


def test_errors_never_name_the_file(tmp_path):
    path = tmp_path / "secret-dir" / "room.json"
    path.parent.mkdir()
    path.write_text('{"boards": {"A": "10.0.0.11"}, "fixtures": [')
    with pytest.raises(RoomError) as exc:
        load_room(path)
    assert str(exc.value).startswith("invalid JSON:")
    assert "secret-dir" not in str(exc.value) and "/" not in str(exc.value)


# ---- floor plan and the preview's description ----------------------------------


def plan(**kw):
    spec = {"image": "plan.png", "points": [[100, 400], [500, 400]], "meters": 2.0, "at": [0.0, 0.0]}
    spec.update(kw)
    return {k: v for k, v in spec.items() if v is not None}


def test_plan_calibration_maps_image_pixels_to_room_meters():
    r = compile_room({**room(bar("a")), "plan": plan()})
    assert r.floor_plan.meters_per_pixel == pytest.approx(2.0 / 400)
    # The first point, 100 px right and 400 px down from the corner, is at
    # [0, 0]: the corner sits 0.5 m left of it and 2 m above it (y up).
    assert r.floor_plan.corner == pytest.approx((-0.5, 2.0))
    d = r.describe()["plan"]
    assert d["corner"] == pytest.approx(r.normalize((-0.5, 2.0)), abs=1e-6)
    assert d["unit"] == pytest.approx(2.0 / 400 * r.scale)
    assert compile_room({**room(bar("a")), "plan": plan(at=None)}).floor_plan.at == (0.0, 0.0)


@pytest.mark.parametrize(
    "spec, message",
    [
        (plan(points=[[10, 10], [10, 10]]), "the two 'points' are the same pixel"),
        (plan(points=[[10, 10]]), "'points' must be two image pixels"),
        (plan(meters=0), "'meters' must be the positive distance"),
        (plan(meters=-2.0), "'meters' must be the positive distance"),
        (plan(meters=True), "'meters' must be the positive distance"),
        (plan(image="../plans/plan.svg"), "'image' must be a .png, .jpg, .jpeg, .webp, .gif file"),
        (plan(image=None), "needs an 'image' file name"),
        (plan(at=[1.0]), "'at' must be [x, y]"),
        (plan(scale=2), "unknown key 'scale'"),
        ("plan.png", "must be an object"),
    ],
)
def test_plan_calibration_is_checked_at_load_without_naming_the_image(spec, message):
    with pytest.raises(RoomError) as exc:
        compile_room({**room(bar("a")), "plan": spec})
    assert [p for p in exc.value.problems if message in p], exc.value.problems
    assert all(p.startswith("plan: ") for p in exc.value.problems)
    assert "plans/" not in str(exc.value)


def test_describe_carries_pitch_in_meters_and_the_meters_to_normalized_scale(example):
    d = example.describe()
    assert d["scale"] == pytest.approx(1.0 / max(example.extent))
    assert len(d["fixtures"]) == 60 and len(d["fixture_of"]) == 3840
    assert {f["pitch"] for f in d["fixtures"]} == {PITCH}
    # A dot sized pitch * scale spans exactly one pixel step in normalized units.
    step = float(np.linalg.norm(example.mapping[1] - example.mapping[0]))
    assert PITCH * d["scale"] == pytest.approx(step, rel=1e-5)
    first = d["fixtures"][0]
    assert first["start"] == pytest.approx(example.normalize(example.fixtures[0].start), abs=1e-6)
    assert first["end"] == pytest.approx(example.normalize(example.fixtures[0].end), abs=1e-6)
    assert d["plan"] is None
    json.dumps(d)  # wire-safe as it stands


# ---- live map reload ---------------------------------------------------------


def ramp(setup=None):
    """A program of a still grey ramp along the pixels, so a frame shows the
    map, with `setup(op, ctx)` as its op's (needs `fake_ops`)."""

    def render(op, c):
        return np.repeat((c.index / np.float32(len(c.index)))[:, None], 3, axis=1).astype(np.float32)

    return source_op("ramp_room_test", render, setup=setup)


def live(tmp_path, program=None, blink=None):
    """A running-aura stand-in: room file, renderer, started DDP sink, and
    the room's live reload the runner builds, whose new maps land in
    `shown`, as the preview's would; `rec` records what the sink sends."""
    path = tmp_path / "room.json"
    doc = copy.deepcopy(TWO_BARS)
    path.write_text(json.dumps(doc))
    r, data = load_room(path)
    renderer = hosted(program or FLOW, r.mapping)
    sink, rec, _ = ddp_sink(r.boards, r.n)
    calls = Calls()
    room_live = RoomLive(path, r, data, renderer, calls.call_soon, ddp=sink, argv=["run"], blink=blink)
    room_live.shown = []  # type: ignore[attr-defined]
    room_live.listeners.append(room_live.shown.append)
    room_live.calls = calls  # type: ignore[attr-defined]
    room_live.rec = rec  # type: ignore[attr-defined]
    return path, doc, renderer, sink, room_live


def test_a_valid_save_rebinds_relays_out_and_resends_positions(tmp_path, audit_log):
    path, doc, renderer, sink, room_live = live(tmp_path)
    renderer.step(1 / 60)
    t = renderer.t
    doc = copy.deepcopy(doc)
    doc["boards"]["B"] = "10.0.0.12"
    doc["fixtures"].append(bar("c", board="B", start=[2.0, 0.0], end=[2.0, 1.0]))
    path.write_text(json.dumps(doc))
    assert room_live.reloader.reload() is True and room_live.error is None
    assert renderer.n == 192 and len(renderer.bound.buffers.pixels) == 192 and renderer.t == t  # time continues
    assert [b.spec for b in sink.boards] == ["10.0.0.11:4048=0+128", "10.0.0.12:4048=128+64"]
    assert [r.n for r in room_live.shown] == [192] and room_live.room is room_live.shown[0]
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["action"] == "ddp-relayout" and len(entry["targets"]) == 2
    sink.send(0.0, renderer.step(1 / 60))
    assert sink.frames_sent == 1


def test_use_for_a_rewrites_the_room_file_and_the_reload_moves_the_stream(tmp_path, audit_log):
    path, _doc, renderer, sink, room_live = live(tmp_path)
    assert room_live.rebind("A", "192.0.2.20") is None
    assert json.loads(path.read_text())["boards"] == {"A": "192.0.2.20"}
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".")] == []  # no temp file left
    room_live.calls.drain()  # the reload runs on the loop thread
    assert room_live.error is None and sink.boards[0].host == "192.0.2.20"
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["action"] == "ddp-relayout" and entry["targets"] == ["192.0.2.20:4048=0+128"]
    sink.send(0.0, renderer.step(1 / 60))
    assert {addr for _, addr in room_live.rec.sent} == {("192.0.2.20", 4048)}


def test_use_for_a_refuses_without_a_path_in_the_reason(tmp_path):
    path, *_, room_live = live(tmp_path)
    assert room_live.rebind("Z", "192.0.2.20") == "board 'Z' is not declared in 'boards'"
    path.unlink()
    assert room_live.rebind("A", "192.0.2.20") == "could not read the room file"


@pytest.mark.usefixtures("fake_ops")
def test_an_invalid_save_keeps_the_last_good_map_and_says_why_without_a_path(tmp_path, audit_log):
    path, doc, renderer, sink, room_live = live(tmp_path, ramp())
    old_boards, old_frame = sink.boards, renderer.step(1 / 60)
    broken = copy.deepcopy(doc)
    del broken["fixtures"][1]["input"]
    path.write_text(json.dumps(broken))
    assert room_live.reloader.reload() is False
    error = room_live.error
    assert error is not None and error.startswith("reload failed, last-good map still running: RoomError:")
    assert "fixture 'b'" in error and str(tmp_path) not in error
    assert sink.boards == old_boards
    assert room_live.shown == [] and not audit_log.exists()
    assert np.array_equal(renderer.step(2 / 60), old_frame)  # the run goes on, on the old map
    path.write_text(json.dumps(doc) + "\n")  # fixed
    assert room_live.reloader.reload() is True and room_live.error is None


@pytest.mark.usefixtures("fake_ops")
def test_a_setup_that_raises_on_the_new_map_keeps_the_old_geometry(tmp_path):
    def picky(op, ctx):
        if ctx.n != 128:
            raise RuntimeError("two bars only")

    path, doc, renderer, sink, room_live = live(tmp_path, ramp(picky))
    doc = copy.deepcopy(doc)
    doc["fixtures"].append(bar("c", chain=3, start=[0.0, 2.0], end=[1.0, 2.0]))
    path.write_text(json.dumps(doc))
    assert room_live.reloader.reload() is False
    assert "two bars only" in (room_live.error or "")
    assert renderer.n == 128 and sink.n_pixels == 128
    assert renderer.step(1 / 60).shape == (128, 3)


@pytest.mark.usefixtures("fake_ops")
def test_a_rollback_that_also_fails_draws_the_error_frame_until_a_good_reload(tmp_path):
    """The new map's setup raises and so does the old map's, so the running
    renderer is left unbound. The run goes on with the error frame and a
    red status, and the next good reload binds it again."""
    bars = [1]

    def needs(op, ctx):
        if bars[0] * 64 > ctx.n:
            raise RuntimeError(f"needs {bars[0]} bars")

    path, doc, renderer, sink, _ = live(tmp_path, ramp(needs))
    fader = Crossfader(renderer)
    r, data = load_room(path)
    room_live = RoomLive(path, r, data, fader, Calls().call_soon, ddp=sink, argv=["run"])
    bars[0] = 5  # no setup runs until the next bind
    path.write_text(json.dumps(room(bar("a"))))
    assert room_live.reloader.reload() is False and "needs 5 bars" in (room_live.error or "")
    frames = [fader.advance_to(t) for t in (1 / 60, 2 / 60)]  # does not raise
    for frame in frames:
        assert frame.shape == (128, 3) and (frame[:, 0] >= 0.25).all() and not frame[:, 1:].any()
    bars[0] = 1
    path.write_text(json.dumps(doc))
    assert room_live.reloader.reload() is True and room_live.error is None
    frame = fader.advance_to(3 / 60)
    assert frame.shape == (128, 3) and frame[:, 1:].any()  # the program again, not the error frame


def test_a_reload_with_a_plan_gives_the_listeners_the_plan_and_its_image_file(tmp_path):
    blink = Blink(compile_room(TWO_BARS))
    path, doc, _renderer, _sink, room_live = live(tmp_path, blink=blink)
    blink.start("a")
    path.write_text(json.dumps({**doc, "plan": plan(image="floor/plan.png")}))
    assert room_live.reloader.reload() is True and room_live.error is None
    [shown] = room_live.shown
    assert shown.plan_file(path) == tmp_path / "floor" / "plan.png"
    assert shown.describe()["plan"]["unit"] == pytest.approx(2.0 / 400 * shown.scale)
    frame = np.zeros((shown.n, 3), dtype=np.float32)
    assert blink.apply(0.0, frame) is frame  # the old map's blink ends with it
    broken = {**doc, "plan": plan(meters=0)}
    path.write_text(json.dumps(broken))
    assert room_live.reloader.reload() is False and "plan: 'meters'" in (room_live.error or "")
    assert len(room_live.shown) == 1


# ---- the CLI -----------------------------------------------------------------


def test_room_dry_run_prints_the_plan_and_sends_nothing(audit_log, recorder, capsys):
    assert run_main(["run", looks_file(), "--room", str(EXAMPLE_ROOM), "--dry-run"])[0] == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "dry run: nothing sent"
    assert out[1] == "ddp 10.0.0.11:4048  pixels 0-1279 (1280)  3 packets/frame  154,800 B/s at 40 fps  board A"
    assert out[2] == "  output 1  start 0  length 320  fixtures row01.1..row01.5 (5)"
    assert len(out) == 1 + 3 * 5
    assert recorder.sent == [] and not audit_log.exists()


def test_room_run_streams_to_the_rooms_boards_and_watches_the_map(audit_log, recorder, capsys):
    watched = []

    def watch(source, stop):
        watched.append(source)
        return iter(())

    argv = ["run", looks_file(), "--room", str(EXAMPLE_ROOM), "--frames", "1"]
    assert run_main(argv, watch=watch)[0] == 0
    assert len(recorder.sent) == 9  # 3 packets to each of 3 boards
    assert {addr for _, addr in recorder.sent} == {(f"10.0.0.1{i}", 4048) for i in (1, 2, 3)}
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["room"] == str(EXAMPLE_ROOM) and len(entry["targets"]) == 3
    assert watched == [EXAMPLE_ROOM]


def test_room_no_ddp_simulates_without_sending(audit_log, recorder, capsys):
    argv = ["run", looks_file(), "--room", str(EXAMPLE_ROOM), "--no-ddp", "--preview", "--port", "0",
            "--frames", "1"]
    assert run_main(argv)[0] == 0
    assert recorder.sent == [] and not audit_log.exists()


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--ddp", "10.0.0.11=0+8"], "drop --ddp"),
        (["--map", "line:8"], "drop --map"),
        (["--ansi"], "--ansi cannot draw a room map"),
        (["--no-ddp"], "add --preview"),
    ],
)
def test_room_rejects_options_it_replaces(extra, message, audit_log, recorder, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--room", str(EXAMPLE_ROOM), "--frames", "1", *extra])
    assert exc.value.code == 2 and message in capsys.readouterr().err  # a usage error
    assert recorder.sent == [] and not audit_log.exists()


def test_no_ddp_needs_a_room(capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--no-ddp", "--frames", "1"])
    assert exc.value.code == 2 and "--no-ddp only applies with --room" in capsys.readouterr().err


def test_a_bad_room_file_is_one_line_naming_the_file(tmp_path):
    path = tmp_path / "room.json"
    path.write_text(json.dumps(room(_drop(bar("west"), "input"))))
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--room", str(path), "--dry-run"])
    assert str(exc.value).startswith(f"{path}: fixture 'west': has no input end")
    path.write_text(json.dumps({**room(_drop(bar("west"), "input")), "lable": "x"}))
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--room", str(path), "--dry-run"])
    assert str(exc.value).splitlines() == [
        f"{path}:",
        "  unknown key 'lable'; expected boards, fixtures, label, notes, plan",
        '  fixture \'west\': has no input end; set "input" to "start" or "end"',
    ]


# ---- rebinding a board ---------------------------------------------------------


HAND_FORMATTED = """{
  "label": "bench",
  "boards": {"A":   "192.0.2.47",
             "B": "192.0.2.48:4049"},
  "fixtures": [
    {"id": "a", "pixels": 64, "start": [0, 0], "end": [1, 0], "input": "start", "board": "A", "output": 1, "chain": 1},
    {"id": "b", "pixels": 64, "start": [0, 1], "end": [1, 1], "input": "start", "board": "B", "output": 1, "chain": 1}
  ]
}
"""


def test_rebind_changes_one_host_and_keeps_the_text_and_the_port():
    new = rebind_text(HAND_FORMATTED.encode(), "B", "192.0.2.20").decode()
    assert new == HAND_FORMATTED.replace('"192.0.2.48:4049"', '"192.0.2.20:4049"')
    new = rebind_text(HAND_FORMATTED.encode(), "A", "pewpew-1.local").decode()
    assert new == HAND_FORMATTED.replace('"192.0.2.47"', '"pewpew-1.local"')
    assert parse_room(new).boards[0].host == "pewpew-1.local"


@pytest.mark.parametrize(
    "text, board, host, message",
    [
        (HAND_FORMATTED, "Z", "192.0.2.20", "board 'Z' is not declared"),
        (HAND_FORMATTED, "A", "lights.example.com", "is not an IPv4 address or an mDNS name"),
        (HAND_FORMATTED.replace('"A":   "192.0.2.47"', '"A": "192.0.2.4\\u0037"'), "A", "192.0.2.20",
         "is not in the file exactly once"),
        ("{", "A", "192.0.2.20", "invalid JSON"),
    ],
)
def test_rebind_refuses_what_it_cannot_change_exactly(text, board, host, message):
    with pytest.raises(RoomError, match=message):
        rebind_text(text.encode(), board, host)


def test_room_names_label_only_the_boards_the_sink_has(tmp_path):
    _path, _doc, _renderer, sink, room_live = live(tmp_path)
    assert room_live.board_names() == ("A",)
    sink.commit(sink.prepare([Board("10.0.0.99", 0, 128)], 128))  # the reload's commit, before `room` is set
    assert room_live.board_names() == ()
