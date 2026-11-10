"""The runtime from a compiled rig: room map validation, the live reload and
the board rebind, and `run --map`."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import threading
import warnings
from pathlib import Path

import numpy as np
import pytest

from fakes import (
    EXAMPLE_RIG,
    FLOW,
    LEGACY_ROOM,
    LoopThread,
    UdpRecorder,
    arrangement,
    bar,
    ddp_sink,
    hosted,
    looks_file,
    room,
    run_main,
    source_op,
    wait_until,
)
from pewpew.__main__ import main
from pewpew.crossfade import Crossfader
from pewpew.errors import Refusal
from pewpew.mapping import line
from pewpew.pace import Calls
from pewpew.rig import RigError, load_catalog
from pewpew.rig.models import MAX_FIXTURES
from pewpew.rig.room_import import RoomError, room_to_arrangement
from pewpew.rig.runtime import (
    ROOM_DEPRECATED,
    RoomFormatWarning,
    compile_doc,
    ddp_targets,
    fixture_spans,
    load_rig,
    parse_rig,
    plan_view,
    rebind_host,
    stream_refusals,
)
from pewpew.rig_cli import DEFAULT_CONTROLLER, DEFAULT_TYPE
from pewpew.room.blink import Blink
from pewpew.room.live import CHANGED_ON_DISK, STALE, RigLive
from pewpew.sinks.ddp import Board

TWO_BARS = arrangement(bar("a"), bar("b", chain=2, start=[0.0, 1.0], end=[1.0, 1.0]))


def compiled(doc):
    return compile_doc(doc, load_catalog())


def migrate(doc):
    """The arrangement of the room document `doc`; raises RoomError."""
    profile = load_catalog().get(DEFAULT_CONTROLLER, "controller")
    return room_to_arrangement(doc, controller_profile=profile, fixture_type=DEFAULT_TYPE)


def write(path: Path, doc) -> None:
    path.write_text(json.dumps(doc))


# ---- the example rig -----------------------------------------------------------


def test_example_compiles_to_three_controllers_of_1280_in_wire_order(example):
    assert example.n == 3840 and len(example.fixtures) == 60
    assert [(c.id, c.host) for c in example.controllers] == [
        ("A", "10.0.0.11"), ("B", "10.0.0.12"), ("C", "10.0.0.13"),
    ]
    assert [(s.controller, s.start, s.count) for s in example.controller_slices] == [
        ("A", 0, 1280), ("B", 1280, 1280), ("C", 2560, 1280),
    ]
    assert [f.id for f in example.fixtures[:6]] == [
        "row01.1", "row01.2", "row01.3", "row01.4", "row01.5", "row02.1",
    ]
    assert [s[1:] for s in fixture_spans(example)[:3]] == [(0, 64), (64, 64), (128, 64)]
    assert np.array_equal(example.fixture_of, np.repeat(np.arange(60), 64))


# ---- room map validation (the migration reads the older format) ----------------


def _drop(spec, key):
    spec = dict(spec)
    del spec[key]
    return spec


@pytest.mark.parametrize(
    "doc, message",
    [
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
        migrate(doc)
    assert message in str(exc.value)
    assert "\n" not in str(exc.value)


def test_every_problem_is_reported_at_once():
    with pytest.raises(RoomError) as exc:
        migrate(room(_drop(bar("a"), "input"), bar("b", board="Z")))
    assert len(exc.value.problems) == 2


def plan(**kw):
    spec = {"image": "plan.png", "points": [[100, 400], [500, 400]], "meters": 2.0, "at": [0.0, 0.0]}
    spec.update(kw)
    return {k: v for k, v in spec.items() if v is not None}


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
        migrate({**room(bar("a")), "plan": spec})
    assert [p for p in exc.value.problems if message in p], exc.value.problems
    assert all(p.startswith("plan: ") for p in exc.value.problems)
    assert "plans/" not in str(exc.value)


# ---- pixel caps are the arrangement's ------------------------------------------


def over_cap_doc():
    return arrangement(bar("long", instances=33, step=[1.0, 0.0]))


def test_a_rig_over_a_pixel_cap_gets_an_output_over_cap_issue_and_may_not_stream():
    rig = compiled(over_cap_doc())
    [issue] = [i for i in rig.issues if i.code == "output_over_cap"]
    assert "2112 px" in issue.message
    assert stream_refusals(rig) == [f"{issue.ref}: {issue.message}"]


def test_run_refuses_to_stream_a_rig_over_a_cap(tmp_path, audit_log, recorder):
    path = tmp_path / "over.arrangement.json"
    write(path, over_cap_doc())
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", str(path), "--frames", "1"])
    assert "the boards cannot take this map" in str(exc.value) and "output_over_cap" not in str(exc.value)
    assert recorder.sent == [] and not audit_log.exists()


def test_a_room_file_over_a_pixel_cap_runs_but_streams_nothing(tmp_path, audit_log, recorder, capsys):
    path = tmp_path / "over.json"
    write(path, room(bar("long", instances=33, step=[1.0, 0.0])))
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--room", str(path), "--frames", "1"])
    message = str(exc.value)
    assert "the boards cannot take this map, so nothing streams" in message and "2112 px" in message
    assert recorder.sent == [] and not audit_log.exists()
    rc, out = run_main(["run", looks_file(), "--room", str(path), "--no-ddp", "--ansi", "--frames", "1"])
    assert rc == 0 and "\x1b[38;2;" in out
    assert recorder.sent == [] and not audit_log.exists()


# ---- a room file of more fixtures than the studio takes ------------------------------


def room_of_240():
    """A legacy room of 240 fixtures once its `instances` expand: two boards,
    four outputs each, 30 short bars per output."""
    return room(
        *(
            bar(f"r{b}{o}", pixels=4, start=[0.0, o * 0.1 + (b == "B")], end=[1.0, o * 0.1 + (b == "B")],
                board=b, output=o, instances=30, step=[1.1, 0.0])
            for b in "AB" for o in range(1, 5)
        ),
        boards={"A": "10.0.0.11", "B": "10.0.0.12"},
    )


def test_a_legacy_room_of_240_fixtures_loads_runs_reloads_and_migrates(tmp_path, audit_log, recorder, capsys):
    assert MAX_FIXTURES >= 240
    path = tmp_path / "big.json"
    write(path, room_of_240())
    notices: list[str] = []
    rig, data = load_rig(path, notices=notices)
    assert len(rig.fixtures) == 240 and rig.n == 960 and notices == [ROOM_DEPRECATED]

    assert run_main(["run", looks_file(), "--room", str(path), "--dry-run"])[0] == 0
    out = capsys.readouterr().out
    assert "board A" in out and "board B" in out
    assert recorder.sent == [] and not audit_log.exists()

    rig_live = RigLive(path, rig, data, hosted(FLOW, rig.mapping), Calls(), ddp=None, argv=["run"])
    assert "960 px in 240 fixtures on 2 controller(s)" in rig_live.apply(data)

    out_file = tmp_path / "big.arrangement.json"
    assert main(["rig", "migrate-room", str(path), "-o", str(out_file)]) == 0
    migrated, _ = load_rig(out_file)
    assert migrated.mapping.tobytes() == rig.mapping.tobytes()


# ---- floor plan and the preview's description ----------------------------------


def test_plan_calibration_maps_image_pixels_to_rig_meters():
    r = compiled({**TWO_BARS, "plan": plan()})
    assert r.plan is not None and r.plan.meters_per_pixel == pytest.approx(2.0 / 400)
    view = plan_view(r)["plan"]
    assert view["unit"] == pytest.approx(2.0 / 400 * r.scale)
    assert len(view["corner"]) == 2
    assert plan_view(compiled(TWO_BARS))["plan"] is None


def test_the_plan_draws_a_strip_its_physical_length_not_its_pixels_span():
    """60 px at a 0.02 m pitch span 1.2 m of a 2 m strip: the strip is drawn 2 m long."""
    r = compiled(arrangement(bar("s", pixels=60, end=[2.0, 0.0], pitch=0.02)))
    (f,) = plan_view(r)["fixtures"]
    assert (f["end"][0] - f["start"][0]) / r.scale == pytest.approx(2.0, abs=1e-5)
    assert f["pitch"] == pytest.approx(0.02)
    catalog_bar = compiled(arrangement(bar("t")))  # pitch length / pixels: the span is the length
    (g,) = plan_view(catalog_bar)["fixtures"]
    assert (g["end"][0] - g["start"][0]) / catalog_bar.scale == pytest.approx(1.0, abs=1e-5)


# ---- live map reload ---------------------------------------------------------


def ramp(setup=None):
    """A program of a still grey ramp along the pixels, so a frame shows the
    map, with `setup(op, ctx)` as its op's (needs `fake_ops`)."""

    def render(op, c):
        return np.repeat((c.index / np.float32(len(c.index)))[:, None], 3, axis=1).astype(np.float32)

    return source_op("ramp_room_test", render, setup=setup)


class Harness(RigLive):
    """A `RigLive` that records the rigs its listeners get (`shown`), the loop's
    call queue (`calls`) and what the sink sends (`rec`)."""

    shown: list
    calls: Calls
    rec: UdpRecorder


def live(tmp_path, program=None, blink=None, calls=None, **kw):
    """A running-aura stand-in: rig file, renderer, started DDP sink, and
    the rig's live reload the runner builds, whose new rigs land in
    `shown`, as the preview's would; `rec` records what the sink sends."""
    path = tmp_path / "rig.arrangement.json"
    doc = copy.deepcopy(TWO_BARS)
    write(path, doc)
    r, data = load_rig(path)
    renderer = hosted(program or FLOW, r.mapping)
    sink, rec = ddp_sink(list(ddp_targets(r)), r.n)
    calls = Calls() if calls is None else calls
    rig_live = Harness(path, r, data, renderer, calls, ddp=sink, argv=["run"], blink=blink, **kw)
    rig_live.shown = []
    rig_live.listeners.append(rig_live.shown.append)
    rig_live.calls = calls
    rig_live.rec = rec
    return path, doc, renderer, sink, rig_live


def test_a_valid_save_rebinds_relays_out_and_resends_positions(tmp_path, audit_log):
    path, _doc, renderer, sink, rig_live = live(tmp_path)
    renderer.step(1 / 60)
    t = renderer.t
    new = arrangement(
        bar("a"), bar("b", chain=2, start=[0.0, 1.0], end=[1.0, 1.0]),
        bar("c", board="B", start=[2.0, 0.0], end=[2.0, 1.0]),
        boards={"A": "10.0.0.11", "B": "10.0.0.12"},
    )
    write(path, new)
    assert rig_live.reloader.reload() is True and rig_live.error is None
    assert renderer.n == 192 and len(renderer.bound.buffers.pixels) == 192 and renderer.t == t  # time continues
    assert [b.spec for b in sink.boards] == ["10.0.0.11:4048=0+128", "10.0.0.12:4048=128+64"]
    [shown] = rig_live.shown
    assert shown.n == 192 and rig_live.rig is shown
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["action"] == "ddp-relayout" and len(entry["targets"]) == 2
    sink.send(0.0, renderer.step(1 / 60))
    assert sink.frames_sent == 1


def test_use_for_a_rewrites_the_controller_host_and_the_reload_moves_the_stream(tmp_path, audit_log):
    path, _doc, renderer, sink, rig_live = live(tmp_path)
    assert rig_live.rebind("A", "192.0.2.20") is None
    assert [c["host"] for c in json.loads(path.read_text())["controllers"]] == ["192.0.2.20"]
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".")] == []  # no temp file left
    rig_live.calls.drain()  # the reload runs on the loop thread
    assert rig_live.error is None and sink.boards[0].host == "192.0.2.20"
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["action"] == "ddp-relayout" and entry["targets"] == ["192.0.2.20:4048=0+128"]
    sink.send(0.0, renderer.step(1 / 60))
    assert {addr for _, addr in rig_live.rec.sent} == {("192.0.2.20", 4048)}


def test_use_for_a_refuses_without_a_path_in_the_reason(tmp_path):
    path, *_, rig_live = live(tmp_path)
    reason = rig_live.rebind("Z", "192.0.2.20")
    assert reason is not None and "'Z'" in reason and str(tmp_path) not in reason
    path.unlink()
    assert rig_live.rebind("A", "192.0.2.20") == "could not read the map file"


def legacy_live(tmp_path):
    """A `RigLive` on a copy of the legacy room map file."""
    path = tmp_path / "room.json"
    shutil.copy(LEGACY_ROOM, path)
    data = path.read_bytes()
    with pytest.warns(RoomFormatWarning):
        rig = parse_rig(data)
    renderer = hosted(FLOW, rig.mapping)
    calls = Calls()
    return path, data, renderer, RigLive(path, rig, data, renderer, calls, ddp=None, argv=["run"])


def test_use_for_a_is_refused_on_a_legacy_room_file(tmp_path):
    path, data, *_, rig_live = legacy_live(tmp_path)
    reason = rig_live.rebind("A", "192.0.2.20")
    assert reason is not None and "migrate" in reason and str(tmp_path) not in reason
    assert path.read_bytes() == data


def test_a_legacy_room_file_reloads_and_logs_the_deprecation(tmp_path, caplog, monkeypatch):
    _path, data, renderer, rig_live = legacy_live(tmp_path)
    filters = list(warnings.filters)

    def global_state(*args, **kw):
        raise AssertionError("a reload touched the process-wide warnings state")

    monkeypatch.setattr(warnings, "warn", global_state)
    monkeypatch.setattr(warnings, "catch_warnings", global_state)
    with caplog.at_level("WARNING", logger="pewpew.room.live"):
        status = rig_live.apply(data)
    assert warnings.filters == filters
    assert status.startswith("map reloaded") and "3840 px in 60 fixtures on 3 controller(s)" in status
    assert any("migrate-room" in r.getMessage() for r in caplog.records)
    assert renderer.n == 3840


@pytest.mark.usefixtures("fake_ops")
def test_an_invalid_save_keeps_the_last_good_map_and_says_why_without_a_path(tmp_path, audit_log):
    path, doc, renderer, sink, rig_live = live(tmp_path, ramp())
    old_boards, old_frame = sink.boards, renderer.step(1 / 60)
    broken = copy.deepcopy(doc)
    broken["wiring"]["chains"][0]["fixtures"].append("ghost")
    write(path, broken)
    assert rig_live.reloader.reload() is False
    error = rig_live.error
    assert error is not None and error.startswith("reload failed, last-good map still running: RigError:")
    assert "ghost" in error and str(tmp_path) not in error
    assert sink.boards == old_boards
    assert rig_live.shown == [] and not audit_log.exists()
    assert np.array_equal(renderer.step(2 / 60), old_frame)  # the run goes on, on the old map
    path.write_text(json.dumps(doc) + "\n")  # fixed
    assert rig_live.reloader.reload() is True and rig_live.error is None


@pytest.mark.usefixtures("fake_ops")
def test_a_setup_that_raises_on_the_new_map_keeps_the_old_geometry(tmp_path):
    def picky(op, ctx):
        if ctx.n != 128:
            raise RuntimeError("two bars only")

    path, _doc, renderer, sink, rig_live = live(tmp_path, ramp(picky))
    three = (
        bar("a"), bar("b", chain=2, start=[0.0, 1.0], end=[1.0, 1.0]),
        bar("c", chain=3, start=[0.0, 2.0], end=[1.0, 2.0]),
    )
    write(path, arrangement(*three))
    assert rig_live.reloader.reload() is False
    assert "two bars only" in (rig_live.error or "")
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
    r, data = load_rig(path)
    rig_live = RigLive(path, r, data, fader, Calls(), ddp=sink, argv=["run"])
    bars[0] = 5  # no setup runs until the next bind
    write(path, arrangement(bar("a")))
    assert rig_live.reloader.reload() is False and "needs 5 bars" in (rig_live.error or "")
    frames = [fader.advance_to(t) for t in (1 / 60, 2 / 60)]  # does not raise
    for frame in frames:
        assert frame.shape == (128, 3) and (frame[:, 0] >= 0.25).all() and not frame[:, 1:].any()
    bars[0] = 1
    write(path, doc)
    assert rig_live.reloader.reload() is True and rig_live.error is None
    frame = fader.advance_to(3 / 60)
    assert frame.shape == (128, 3) and frame[:, 1:].any()  # the program again, not the error frame


def test_a_reload_with_a_plan_gives_the_listeners_the_plan_and_its_image_file(tmp_path):
    blink = Blink(fixture_spans(compiled(TWO_BARS)))
    path, doc, _renderer, _sink, rig_live = live(tmp_path, blink=blink)
    blink.start("a")
    write(path, {**doc, "plan": plan(image="floor/plan.png")})
    assert rig_live.reloader.reload() is True and rig_live.error is None
    [shown] = rig_live.shown
    assert shown.plan is not None and shown.plan.image == "floor/plan.png"
    assert plan_view(shown)["plan"]["unit"] == pytest.approx(2.0 / 400 * shown.scale)
    frame = np.zeros((shown.n, 3), dtype=np.float32)
    assert blink.apply(0.0, frame) is frame  # the old map's blink ends with it
    write(path, {**doc, "plan": plan(meters=0)})
    assert rig_live.reloader.reload() is False and "meters" in (rig_live.error or "")
    assert len(rig_live.shown) == 1


# ---- the CLI -----------------------------------------------------------------


def test_rig_dry_run_prints_the_plan_and_sends_nothing(audit_log, recorder, capsys):
    assert run_main(["run", looks_file(), "--map", str(EXAMPLE_RIG), "--dry-run"])[0] == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "dry run: nothing sent"
    assert out[1] == "ddp 10.0.0.11:4048  pixels 0-1279 (1280)  3 packets/frame  232,200 B/s at 60 fps  board A"
    assert out[2] == "  output 1  start 0  length 320  fixtures row01.1..row01.5 (5)"
    assert len(out) == 1 + 3 * 5
    assert recorder.sent == [] and not audit_log.exists()


def test_rig_run_streams_to_the_rigs_boards_and_watches_the_map(audit_log, recorder, capsys):
    watched = []

    def watch(source, stop):
        watched.append(source)
        return iter(())

    argv = ["run", looks_file(), "--map", str(EXAMPLE_RIG), "--frames", "1"]
    assert run_main(argv, watch=watch)[0] == 0
    assert len(recorder.sent) == 9  # 3 packets to each of 3 boards
    assert {addr for _, addr in recorder.sent} == {(f"10.0.0.1{i}", 4048) for i in (1, 2, 3)}
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["map"] == str(EXAMPLE_RIG) and len(entry["targets"]) == 3
    assert watched == [EXAMPLE_RIG]


def test_rig_no_ddp_simulates_without_sending(audit_log, recorder, capsys):
    argv = ["run", looks_file(), "--map", str(EXAMPLE_RIG), "--no-ddp", "--preview", "--port", "0", "--frames", "1"]
    assert run_main(argv)[0] == 0
    assert recorder.sent == [] and not audit_log.exists()


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--no-ddp", "--dry-run"], "--no-ddp"),
        (["--room", str(EXAMPLE_RIG)], "--room is the old name of --map; give --map only"),
    ],
)
def test_run_rejects_options_a_rig_conflicts_with(extra, message, audit_log, recorder, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", str(EXAMPLE_RIG), "--frames", "1", *extra])
    assert exc.value.code == 2 and message in capsys.readouterr().err  # a usage error
    assert recorder.sent == [] and not audit_log.exists()


def test_ddp_with_a_hosted_rig_is_refused_at_launch(audit_log, recorder):
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", str(EXAMPLE_RIG), "--frames", "1", "--ddp", "10.0.0.11=0+8"])
    message = str(exc.value)
    assert "drop --ddp to stream to them" in message and "remove the hosts from the file" in message
    assert "--no-ddp" not in message  # --ddp with --no-ddp is itself refused
    assert recorder.sent == [] and not audit_log.exists()


def test_room_is_always_a_file_path(tmp_path, monkeypatch, audit_log, recorder, capsys):
    shutil.copy(LEGACY_ROOM, tmp_path / "myroom")
    monkeypatch.chdir(tmp_path)
    assert run_main(["run", looks_file(), "--room", "myroom", "--dry-run"])[0] == 0
    assert "board A" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--room", "line:64", "--frames", "1"])
    assert exc.value.code == 2 and "--room takes a file; 'line:64' is a synthetic map" in capsys.readouterr().err
    assert recorder.sent == [] and not audit_log.exists()


def test_an_arrangement_renders_to_the_terminal(audit_log, recorder):
    argv = ["run", looks_file(), "--map", str(EXAMPLE_RIG), "--no-ddp", "--ansi", "--frames", "2", "--fps", "30"]
    rc, out = run_main(argv)
    assert rc == 0 and out.count("\n\n") == 2 and "\x1b[38;2;" in out
    assert recorder.sent == [] and not audit_log.exists()


def test_no_ddp_needs_an_arrangement(capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--no-ddp", "--frames", "1"])
    assert exc.value.code == 2 and "--no-ddp only applies with an arrangement --map" in capsys.readouterr().err


def test_a_bad_map_file_is_one_line_naming_the_file(tmp_path):
    path = tmp_path / "rig.arrangement.json"
    doc = copy.deepcopy(TWO_BARS)
    doc["wiring"]["chains"][0]["fixtures"].append("ghost")
    write(path, doc)
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", str(path), "--dry-run"])
    message = str(exc.value)
    assert message.startswith(f"--map {path}: ") and "ghost" in message and "\n" not in message
    path.write_text("{")
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", str(path), "--dry-run"])
    assert str(exc.value).startswith(f"--map {path}: ") and "\n" not in str(exc.value)


# ---- rebinding a controller ------------------------------------------------------


def hand_formatted() -> str:
    """An arrangement file with two controllers and uneven spacing at their hosts."""
    doc = arrangement(
        bar("a"), bar("b", board="B", start=[0.0, 1.0], end=[1.0, 1.0]),
        boards={"A": "192.0.2.47", "B": "192.0.2.48:4049"},
    )
    text = json.dumps(doc, indent=2)
    return text.replace('"host": "192.0.2.47"', '"host":   "192.0.2.47"') + "\n"


def test_rebind_changes_one_host_and_keeps_the_text_and_the_port():
    text = hand_formatted()
    new = rebind_host(text.encode(), "B", "192.0.2.20").decode()
    assert new == text.replace('"192.0.2.48:4049"', '"192.0.2.20:4049"')
    new = rebind_host(text.encode(), "A", "pewpew-1.local").decode()
    assert new == text.replace('"192.0.2.47"', '"pewpew-1.local"')
    assert [c.host for c in parse_rig(new).controllers] == ["pewpew-1.local", "192.0.2.48"]


@pytest.mark.parametrize(
    "text, controller, host, message",
    [
        (hand_formatted(), "Z", "192.0.2.20", "no controller 'Z' with a host"),
        (hand_formatted(), "A", "lights.example.com", "is not an IPv4 address or an mDNS name"),
        (hand_formatted().replace('"host":   "192.0.2.47"', '"host": "192.0.2.4\\u0037"'), "A", "192.0.2.20",
         "is not in the file exactly once"),
        ("{", "A", "192.0.2.20", "Expecting property name"),
    ],
)
def test_rebind_refuses_what_it_cannot_change_exactly(text, controller, host, message):
    with pytest.raises(RigError, match=message):
        rebind_host(text.encode(), controller, host)


def test_rig_names_label_only_the_boards_the_sink_has(tmp_path):
    _path, _doc, _renderer, sink, rig_live = live(tmp_path)
    assert rig_live.board_names() == ("A",)
    sink.commit(sink.prepare([Board("10.0.0.99", 0, 128)], 128))  # the reload's commit, before `rig` is set
    assert rig_live.board_names() == ()


# ---- the page's layout edit ----------------------------------------------------------


def three_bars_on_two_boards():
    return arrangement(
        bar("a"), bar("b", chain=2, start=[0.0, 1.0], end=[1.0, 1.0]),
        bar("c", board="B", start=[2.0, 0.0], end=[2.0, 1.0]),
        boards={"A": "10.0.0.11", "B": "10.0.0.12"},
    )


def base_of(rig_live: RigLive) -> str | None:
    """The digest an arrange built on the file as it runs names."""
    return rig_live.arrangement()["base"]


def arranged(rig_live: Harness, doc, base=None) -> Refusal | None:
    """`rig_live.arrange(doc, base)` with its loop thread running; `base`
    is the running file's when not given."""
    with LoopThread(rig_live.calls):
        return rig_live.arrange(doc, base_of(rig_live) if base is None else base)


def file_bytes(doc) -> bytes:
    """The bytes an arrange writes for `doc`."""
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode()


class Busy(Calls):
    """A loop that never answers in time: each ask is late, and its step never runs."""

    def ask(self, fn, late, timeout=0.0, *, definite=False):
        return late


def test_arrange_writes_adopts_audits_and_answers_once_the_rig_is_live(tmp_path, audit_log, monkeypatch):
    from pewpew.rig import runtime
    from pewpew.room import live as live_module

    path, _doc, renderer, sink, rig_live = live(tmp_path, edits=True)
    compiles = []
    compile_doc_ = runtime.compile_doc
    monkeypatch.setattr(runtime, "compile_doc", lambda *a, **kw: compiles.append(1) or compile_doc_(*a, **kw))
    steps, at_commit = [], []
    write_atomic = live_module.write_atomic
    monkeypatch.setattr(live_module, "write_atomic",
                        lambda *a, **kw: steps.append(("write", audit_log.exists())) or write_atomic(*a, **kw))
    adopt = rig_live.reloader.adopt
    monkeypatch.setattr(rig_live.reloader, "adopt", lambda d: steps.append(("adopt", audit_log.exists())) or adopt(d))
    commit = sink.commit
    monkeypatch.setattr(sink, "commit", lambda layout: at_commit.append(audit_log.read_text()) or commit(layout))
    new, old_base = three_bars_on_two_boards(), base_of(rig_live)
    assert rig_live.editable and arranged(rig_live, new) is None
    # The answer comes once the rig runs.
    assert renderer.n == 192 and [b.spec for b in sink.boards] == ["10.0.0.11:4048=0+128", "10.0.0.12:4048=128+64"]
    assert steps == [("write", False), ("adopt", False)]  # the audit record follows the write and the adopt
    assert path.read_bytes() == file_bytes(new)
    assert [p.name for p in tmp_path.iterdir() if p.name != path.name] == []  # no temp file left
    assert compiles == [1] and rig_live.error is None
    [shown] = rig_live.shown
    assert rig_live.rig is shown and rig_live.report() == shown.findings()
    digest = hashlib.sha256(file_bytes(new)).hexdigest()
    assert rig_live.arrangement() == {"arrangement": new, "base": digest} and digest != old_base
    actions = [json.loads(line)["action"] for line in at_commit[0].splitlines()]
    assert actions == ["arrange", "ddp-relayout"]  # both audited before the sink takes the new boards


def test_arrange_is_skipped_by_the_watcher_that_sees_its_write(tmp_path, audit_log):
    fired = threading.Event()

    def watch(source, stop):
        while not stop.is_set():
            if fired.wait(0.01):
                fired.clear()
                yield "changed"

    _path, _doc, renderer, _sink, rig_live = live(tmp_path, edits=True, watch=watch)
    rig_live.start()
    try:
        assert arranged(rig_live, three_bars_on_two_boards()) is None
        fired.set()  # the event for our own write
        wait_until(lambda: len(rig_live.calls._queue) == 1)
        rig_live.calls.drain()
    finally:
        rig_live.stop()
    assert len(rig_live.shown) == 1 and renderer.n == 192 and rig_live.error is None


CURRENT = object()


@pytest.mark.parametrize("edits, doc, base, reason", [
    (False, TWO_BARS, CURRENT, "layout edits are off in an unattended run"),
    (True, "rig.arrangement.json", CURRENT, "an arrangement is a JSON object"),
    (True, [TWO_BARS], CURRENT, "an arrangement is a JSON object"),
    (True, TWO_BARS, None, "an arrange names the layout it edits: `base`, from the engine's `arrangement`"),
    (True, TWO_BARS, "0" * 64, "the layout changed; showing the current one"),
])
def test_arrange_refuses_what_it_must_not_write_and_writes_nothing(tmp_path, audit_log, edits, doc, base, reason):
    path, _doc, _renderer, _sink, rig_live = live(tmp_path, edits=edits)
    data = path.read_bytes()
    refused = rig_live.arrange(doc, base_of(rig_live) if base is CURRENT else base)
    assert refused is not None and refused.reason == reason
    # A stale base gets the layout that runs, to show in place of the edit; no other refusal carries one.
    assert refused.current is (rig_live.arrangement() if reason == STALE else None)
    assert path.read_bytes() == data and not rig_live.calls._queue and not audit_log.exists()
    assert rig_live.arrangement()["arrangement"] is (None if not edits else rig_live.doc)


def test_arrange_refuses_an_arrangement_that_does_not_compile_with_every_issue(tmp_path, audit_log):
    path, doc, _renderer, _sink, rig_live = live(tmp_path, edits=True)
    data = path.read_bytes()
    broken = copy.deepcopy(doc)
    broken["wiring"]["chains"][0]["fixtures"] += ["ghost", "phantom"]
    refused = rig_live.arrange(broken, base_of(rig_live))
    assert refused is not None and refused.reason == "the arrangement does not compile: chain A-1: no fixture 'ghost'"
    assert [i["message"] for i in refused.issues] == ["no fixture 'ghost'", "no fixture 'phantom'"]
    assert path.read_bytes() == data and not rig_live.calls._queue and not audit_log.exists()
    assert rig_live.arrangement()["arrangement"] is rig_live.doc and rig_live.doc == doc


def test_arrange_refuses_a_rig_the_boards_cannot_take(tmp_path, audit_log):
    path, _doc, _renderer, _sink, rig_live = live(tmp_path, edits=True)
    data = path.read_bytes()
    refused = rig_live.arrange(over_cap_doc(), base_of(rig_live))
    assert refused is not None and refused.reason.startswith("the boards cannot take this map: ")
    assert "output_over_cap" in {i["code"] for i in refused.issues}
    assert path.read_bytes() == data and not rig_live.calls._queue and not audit_log.exists()


def test_arrange_is_refused_on_a_legacy_room_file(tmp_path):
    path, data, *_, _ = legacy_live(tmp_path)
    rig_live = RigLive(path, parse_rig(data, notices=[]), data, hosted(FLOW, line(4)), Calls(), ddp=None,
                       argv=["run"], edits=True)
    assert not rig_live.editable and rig_live.arrangement() == {"arrangement": None, "base": None}
    refused = rig_live.arrange(TWO_BARS, hashlib.sha256(data).hexdigest())
    assert refused is not None and "migrate" in refused.reason and str(tmp_path) not in refused.reason
    assert path.read_bytes() == data


def test_arrange_without_a_ddp_sink_writes_no_audit_record(tmp_path, audit_log):
    path = tmp_path / "rig.arrangement.json"
    write(path, TWO_BARS)
    r, data = load_rig(path)
    calls = Calls()
    rig_live = RigLive(path, r, data, hosted(FLOW, r.mapping), calls, ddp=None, argv=["run"], edits=True)
    with LoopThread(calls):
        assert rig_live.arrange(three_bars_on_two_boards(), hashlib.sha256(data).hexdigest()) is None
    assert rig_live.rig.n == 192 and not audit_log.exists()


@pytest.mark.usefixtures("fake_ops")
def test_an_arrange_whose_rig_does_not_run_is_refused_and_the_file_put_back(tmp_path, audit_log):
    """A program's setup raises on the new geometry: the refusal says why,
    the file holds its old bytes, the old rig runs, and once the cause is
    gone the same edit applies."""
    bars = [2]

    def needs(op, ctx):
        if ctx.n > bars[0] * 64:
            raise RuntimeError(f"at most {bars[0]} bars")

    path, doc, renderer, sink, rig_live = live(tmp_path, ramp(needs), edits=True)
    data, state, boards = path.read_bytes(), rig_live.arrangement(), list(sink.boards)
    new = three_bars_on_two_boards()
    refused = arranged(rig_live, new)
    assert refused is not None
    assert refused.reason.startswith("the layout did not run, so the map was not changed: RuntimeError: at most 2 bars")
    assert path.read_bytes() == data and renderer.n == 128 and list(sink.boards) == boards
    assert rig_live.arrangement() is state and rig_live.doc == doc and rig_live.shown == []
    assert rig_live.reloader.reload() is False  # the old bytes' digest is adopted again: nothing to reload
    bars[0] = 3
    assert arranged(rig_live, new) is None  # the same edit, sent again
    assert path.read_bytes() == file_bytes(new) and renderer.n == 192 and rig_live.arrangement()["arrangement"] == new


class Raises:
    """A part of the run that raises the `n`th time it takes a new rig, and takes it otherwise."""

    def __init__(self, take, n=1):
        self.take, self.n, self.calls = take, n, 0

    def __call__(self, *a):
        self.calls += 1
        if self.calls == self.n:
            raise RuntimeError("lost the new rig")
        self.take(*a)


def test_an_arrange_whose_blink_fails_after_the_rebind_runs_the_old_rig_everywhere(tmp_path, audit_log, monkeypatch):
    """The renderer and the sink have taken the new rig when the blink raises: both take the old one back,
    the file is put back, and the page is refused."""
    path, _doc, renderer, sink, rig_live = live(tmp_path, blink=Blink([]), edits=True)
    blink = rig_live._blink
    assert blink is not None
    monkeypatch.setattr(blink, "rebind", Raises(blink.rebind))
    data, state, layout = path.read_bytes(), rig_live.arrangement(), sink.layout
    refused = arranged(rig_live, three_bars_on_two_boards())
    assert refused is not None and "RuntimeError: lost the new rig" in refused.reason
    assert renderer.n == 128 and sink.layout is layout and blink._fixtures == tuple(fixture_spans(rig_live.rig))
    assert path.read_bytes() == data and rig_live.arrangement() is state and rig_live.shown == []
    assert rig_live.reloader.reload() is False and rig_live.error is None


def test_a_rollback_step_that_fails_skips_no_other_step_and_the_status_says_which(tmp_path, audit_log, monkeypatch):
    """The blink raises on the new rig and the renderer raises on the old one: the sink and the blink still
    take the old rig, the original error is the refusal, its notes name the renderer, and the revert is
    audited before the sink takes the old layout."""
    path, _doc, _renderer, sink, rig_live = live(tmp_path, blink=Blink([]), edits=True)
    blink, live_ = rig_live._blink, rig_live._live
    assert blink is not None
    monkeypatch.setattr(blink, "rebind", Raises(blink.rebind))
    rebind = live_.rebind
    renderer_calls = []

    def renderer_rebind(mapping):
        renderer_calls.append(mapping)
        if len(renderer_calls) == 2:
            raise OSError("renderer is stuck")
        rebind(mapping)

    monkeypatch.setattr(live_, "rebind", renderer_rebind)
    at_commit, commit = [], sink.commit
    monkeypatch.setattr(sink, "commit", lambda layout: at_commit.append(audit_log.read_text()) or commit(layout))
    data, layout, boards = path.read_bytes(), sink.layout, list(sink.boards)
    refused = arranged(rig_live, three_bars_on_two_boards())
    assert refused is not None and "RuntimeError: lost the new rig" in refused.reason
    assert "rollback failed: the renderer may still run the new map" in refused.reason
    assert sink.layout is layout and list(sink.boards) == boards
    assert blink._fixtures == tuple(fixture_spans(rig_live.rig)) and path.read_bytes() == data
    actions = [json.loads(line)["action"] for line in audit_log.read_text().splitlines()]
    assert actions == ["arrange", "ddp-relayout", "ddp-relayout-reverted"]
    assert [json.loads(line)["action"] for line in at_commit[1].splitlines()][-1] == "ddp-relayout-reverted"
    assert json.loads(audit_log.read_text().splitlines()[-1])["targets"] == [b.spec for b in boards]


def test_an_arrange_whose_listener_fails_once_the_rig_runs_keeps_the_new_file_and_warns(tmp_path, audit_log):
    """The new rig runs everywhere but one listener: the edit is done (the file, the state and the engine
    hold it), and the status line says what did not follow it."""
    path, _doc, renderer, sink, rig_live = live(tmp_path, edits=True)
    rig_live.listeners.insert(0, Raises(lambda rig: None))
    new = three_bars_on_two_boards()
    assert arranged(rig_live, new) is None
    assert renderer.n == 192 and len(sink.boards) == 2 and len(rig_live.shown) == 1  # the later listener ran
    digest = hashlib.sha256(file_bytes(new)).hexdigest()
    assert path.read_bytes() == file_bytes(new) and rig_live.arrangement() == {"arrangement": new, "base": digest}
    error = rig_live.error
    assert error is not None and "the new map runs, but" in error and "lost the new rig" in error
    assert rig_live.reloader.reload() is False  # the new bytes' digest is adopted: nothing to reload
    write(path, TWO_BARS)
    assert rig_live.reloader.reload() is True and rig_live.error is None  # a clean reload clears the warning


def test_an_arrange_the_loop_does_not_answer_in_time_is_refused_and_the_file_put_back(tmp_path, audit_log):
    path, _doc, renderer, _sink, rig_live = live(tmp_path, edits=True, calls=Busy())
    data = path.read_bytes()
    refused = rig_live.arrange(three_bars_on_two_boards(), base_of(rig_live))
    assert refused == Refusal("the engine is busy, so the layout did not change; send it again")
    assert path.read_bytes() == data and renderer.n == 128 and rig_live.reloader.reload() is False


def test_an_arrange_that_cannot_write_the_map_file_adopts_and_audits_nothing(tmp_path, audit_log):
    path, _doc, renderer, _sink, rig_live = live(tmp_path, edits=True)
    data, base, new = path.read_bytes(), base_of(rig_live), three_bars_on_two_boards()
    tmp_path.chmod(0o500)  # no temporary file beside the map
    try:
        refused = rig_live.arrange(new, base)
    finally:
        tmp_path.chmod(0o700)
    assert refused == Refusal("could not write the map file")
    assert path.read_bytes() == data and not audit_log.exists() and renderer.n == 128 and base_of(rig_live) == base
    path.write_bytes(file_bytes(new))  # a save of the same bytes is not skipped: their digest was never adopted
    assert rig_live.reloader.reload() is True and renderer.n == 192


def test_an_arrange_that_cannot_write_its_audit_record_puts_the_file_back(tmp_path, audit_log, monkeypatch):
    from pewpew import audit

    path, _doc, renderer, _sink, rig_live = live(tmp_path, edits=True)
    data = path.read_bytes()

    def unwritable(*a, **kw):
        raise OSError("read-only")

    monkeypatch.setattr(audit, "record", unwritable)
    refused = rig_live.arrange(three_bars_on_two_boards(), base_of(rig_live))
    assert refused == Refusal("could not write the audit log, so the map was not changed")
    assert path.read_bytes() == data and renderer.n == 128 and not rig_live.calls._queue


def test_an_arrange_whose_file_cannot_be_put_back_says_so(tmp_path, audit_log, monkeypatch):
    from pewpew.room import live as live_module

    _path, _doc, _renderer, _sink, rig_live = live(tmp_path, edits=True, calls=Busy())
    writes = []
    write_atomic = live_module.write_atomic

    def once(*a, **kw):
        writes.append(1)
        if len(writes) > 1:
            raise OSError("disk full")
        write_atomic(*a, **kw)

    monkeypatch.setattr(live_module, "write_atomic", once)
    refused = rig_live.arrange(three_bars_on_two_boards(), base_of(rig_live))
    assert refused is not None and refused.reason.endswith("; the map file could not be put back")
    assert rig_live.error is not None and "did not run" in rig_live.error


def test_an_arrange_built_before_a_rebind_is_refused_and_the_new_host_kept(tmp_path, audit_log):
    path, doc, _renderer, sink, rig_live = live(tmp_path, edits=True)
    base = base_of(rig_live)
    edited = copy.deepcopy(doc)
    edited["name"] = "edited before the rebind"
    assert rig_live.rebind("A", "192.0.2.20") is None
    # Before the rebind's reload has run, the file on disk is not the one that runs.
    assert rig_live.arrange(edited, base) == Refusal(CHANGED_ON_DISK, current=rig_live.arrangement())
    rig_live.calls.drain()
    assert base_of(rig_live) != base  # the rebind's file has a digest of its own
    assert rig_live.arrange(edited, base) == Refusal(STALE, current=rig_live.arrangement())
    assert [c["host"] for c in json.loads(path.read_text())["controllers"]] == ["192.0.2.20"]
    assert sink.boards[0].host == "192.0.2.20" and rig_live.doc["controllers"][0]["host"] == "192.0.2.20"


def test_of_two_arranges_on_one_base_the_second_is_refused(tmp_path, audit_log):
    path, doc, renderer, _sink, rig_live = live(tmp_path, edits=True)
    base = base_of(rig_live)
    other = copy.deepcopy(doc)
    other["name"] = "the other tab"
    assert arranged(rig_live, three_bars_on_two_boards(), base) is None
    refused = arranged(rig_live, other, base)
    assert refused == Refusal(STALE, current={"arrangement": three_bars_on_two_boards(), "base": base_of(rig_live)})
    assert path.read_bytes() == file_bytes(three_bars_on_two_boards()) and renderer.n == 192


def test_the_report_is_one_object_per_rig(tmp_path):
    path, doc, _renderer, _sink, rig_live = live(tmp_path, edits=True)
    report = rig_live.report()
    assert report == rig_live.rig.findings() and rig_live.report() is report
    state = rig_live.arrangement()
    assert state["arrangement"] is rig_live.doc and rig_live.doc == doc and rig_live.arrangement() is state
    write(path, three_bars_on_two_boards())
    assert rig_live.reloader.reload() is True
    assert rig_live.report() is not report and rig_live.arrangement()["arrangement"] == three_bars_on_two_boards()
    assert rig_live.arrangement()["base"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_room_file_saved_over_the_arrangement_ends_the_edits(tmp_path):
    path, _doc, _renderer, _sink, rig_live = live(tmp_path, edits=True)
    shutil.copy(LEGACY_ROOM, path)
    assert rig_live.reloader.reload() is True
    assert not rig_live.editable and rig_live.arrangement() == {"arrangement": None, "base": None}
