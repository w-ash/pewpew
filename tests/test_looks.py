"""Saved looks: the file, the two-renderer crossfade, recall, the idle cycle,
and the page's look messages."""

from __future__ import annotations

import json
import os
import threading

import numpy as np
import pytest

import pewpew.run as run_module
from fakes import (
    LOOK_CLASSES,
    FakeTime,
    FixtureRamp,
    LoopThread,
    PixelRamp,
    Raises,
    Solid,
    aura_rig,
    bar,
    build,
    layer_renderer,
    layered,
    look,
    next_of,
    room,
    run_main,
    serving,
    solid,
    spec,
    wait_until,
)
from pewpew import HSV, Renderer, line
from pewpew.aura.book import (
    VERSION,
    CycleConfig,
    LookBook,
    LookError,
    load_looks,
    parse_looks,
    pattern_problems,
)
from pewpew.aura.looks import Looks
from pewpew.compose import DEFAULT_FADE, Look, pattern_layer
from pewpew.crossfade import Crossfader
from pewpew.jsonfile import write_atomic
from pewpew.load import Catalog
from pewpew.pace import PacedLoop
from pewpew.patterns import Comet, Pulse, Sparkle, Wave, canopy
from pewpew.room.map import compile_room
from pewpew.run import geometry

CALM = {"h": 30.0, "s": 1.0, "v": 1.0}


def make_rig(tmp_path, looks, mapping=None, grouping=None, current=None, cycle=None, start="solid"):
    """An aura over a book of test looks, with no loop and no sinks."""
    return aura_rig(LOOK_CLASSES[start], mapping=mapping, grouping=grouping, looks=looks, current=current,
                    cycle=cycle, path=tmp_path / "looks.json")


def looks_file(**fields) -> str:
    """A looks file of this version with `fields`, as text."""
    return json.dumps({"version": VERSION, **fields})


# ---- the file ----------------------------------------------------------------


def test_the_file_round_trips_and_keeps_look_order(tmp_path):
    book = LookBook(
        {"b": solid(1.0, master=0.5, fade=3.0, cycle=True), "a": look("pulse", {"color": CALM}, seed=7)},
        "a", CycleConfig(idle=120.0, each=20.0, rounds=2, end="b"),
    )
    path = tmp_path / "looks.json"
    write_atomic(path, book.to_bytes())
    again = load_looks(path)
    assert again == book and list(again.looks) == ["b", "a"]
    doc = json.loads(path.read_text())
    assert doc["version"] == 4 and "master" not in doc["looks"]["a"] and doc["looks"]["a"]["seed"] == 7
    assert doc["looks"]["a"]["layers"] == [{
        "id": "base", "opacity": 1.0, "blend": "normal", "enabled": True, "out": "pulse",
        "nodes": {"pulse": {"op": "pattern", "args": {"pattern": "pulse", "color": CALM}}},
    }]
    assert doc["looks"]["a"]["fade"] == DEFAULT_FADE
    assert again.in_cycle == ["b"]


BREATH = {"signals": {"breath": {"op": "lfo", "args": {"rate": 0.5}}},
          "routes": [{"source": "breath", "path": "layers.base.solid.red", "depth": 0.25}],
          "front": ["layers.base.solid.red"]}


def test_a_look_holds_its_signals_routes_and_front_and_the_file_keeps_them():
    """The canonical v4 shape (ADR-006 amendment "layered paths"); empty
    or null ones load as none, and a rewrite keeps every one."""
    book = parse_looks(looks_file(looks={"a": layered("solid", **BREATH), "b": layered("solid", signals={},
                                                                                       routes=[], front=None)}))
    a = book.looks["a"]
    assert [node.op for node in a.signals or ()] == ["lfo"] and a.front == ("layers.base.solid.red",)
    assert a.routes[0].depth == 0.25 and book.looks["b"] == look("solid")
    assert parse_looks(book.to_bytes()) == book


def test_a_missing_file_is_an_empty_book_but_a_missing_directory_is_an_error(tmp_path):
    assert load_looks(tmp_path / "new.json") == LookBook()
    with pytest.raises(FileNotFoundError):
        load_looks(tmp_path / "nowhere" / "looks.json")


def test_a_crash_between_write_and_rename_leaves_the_old_file_valid(tmp_path, monkeypatch):
    path = tmp_path / "looks.json"
    old = LookBook({"a": solid(1.0)}, "a")
    write_atomic(path, old.to_bytes())

    def crash(src, dst):
        raise OSError("power cut")

    monkeypatch.setattr(os, "replace", crash)
    with pytest.raises(OSError):
        write_atomic(path, LookBook({"b": solid(0.0, 1.0)}, "b").to_bytes())
    assert load_looks(path) == old
    assert [p.name for p in tmp_path.iterdir()] == ["looks.json"]  # no temp file left


def test_a_failed_write_refuses_the_save_and_changes_nothing(tmp_path, monkeypatch):
    rig = make_rig(tmp_path, {"a": solid(1.0)}, current="a")
    monkeypatch.setattr(os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("disk full")))
    assert rig.looks.save("b") == "cannot write the looks file; nothing was saved"
    assert list(rig.looks.book.looks) == ["a"]


@pytest.mark.parametrize("text, message", [
    ("{", "invalid JSON"),
    ("[]", "a looks file is a JSON object"),
    (looks_file(looks={}, extra=1), "unknown key 'extra'"),
    (looks_file(looks={"../x": layered("solid")}), "bad look name '../x'"),
    (looks_file(looks={"a": layered("solid", master=0.9)}),
     "master must be within 0.0..0.6, got 0.9 (the cap set at launch)"),
    (looks_file(looks={"a": layered("solid", fade=-1)}), "fade must be within 0.0..600.0"),
    (looks_file(looks={"a": layered("solid", cycle="yes")}), "cycle takes true or false"),
    (looks_file(looks={"a": layered("solid", seed=-1)}), "look 'a': 'seed' is a whole number of at least 0, got -1"),
    (looks_file(looks={"a": layered("solid", [1])}), "look 'a': layers.base.solid: 'args' is an object of name: value"),
    (looks_file(looks={"a": {"pattern": "solid"}}),
     "look 'a': unknown key 'pattern'; expected cycle, fade, front, layers, master, routes, seed, signals"),
    (looks_file(looks={"a": layered("solid", routes=[{"source": "breath", "path": "layers.base.opacity",
                                                      "depth": 0.2}])}),
     "look 'a': routes[0]: unknown signal 'breath'; signals: (none)"),
    (looks_file(looks={"a": layered("solid", signals={"breath": {"op": "lfo"}})}),
     "look 'a': signals.breath: nothing reads signal 'breath'; route it to a knob, or remove it"),
    (looks_file(looks={"a": layered("solid", signals={"w": {"op": "osc"}})}),
     ("look 'a': signals.w: osc is not a signal op; a look's signals run band, beat, env, knob, lfo, smooth, walk, "
     "and osc goes in a layer's program")),
    (looks_file(looks={"a": layered("solid", **{**BREATH, "routes": [{"source": "breath", "depth": "deep"}]})}),
     "look 'a': routes[0]: 'path' is missing"),
    (looks_file(looks={"a": layered("solid", front=0)}),
     "look 'a': 'front' is a list of the addresses of the knobs a page shows first"),
    (looks_file(looks={"a": {"layers": []}}), "look 'a': a look has at least one layer"),
    (looks_file(looks={"a": {"layers": {}}}), "look 'a': 'layers' is a list of layers, the bottom one first"),
    (looks_file(looks={"a": {"layers": [{"id": "Base", "nodes": {}}]}}), "look 'a': layers[0]: bad layer id 'Base'"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "opacity": 2, "nodes": {}}]}}),
     "look 'a': layers.b.opacity must be within 0.0..1.0, got 2"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "blend": "glow", "nodes": {}}]}}),
     "look 'a': layers.b.blend takes one of 'normal', 'add', "),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"blend": {"op": "pattern",
                                                                        "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b: bad node id 'blend': alpha, blend, enabled, nodes, opacity, out are reserved"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "glow", "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: unknown op 'glow'"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "osc", "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: unknown param 'pattern'; params: freq, sync, offset, axis"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: 'op' is missing; name the node's op, one of "),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "pattern", "args": {"red": 1}}}}]}}),
     "look 'a': layers.b.w: args: 'pattern' is a pattern name"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "pattern", "pattern": "solid"}}}]}}),
     "look 'a': layers.b.w: unknown key 'pattern'; expected args, in, op"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "out": "x",
                                         "nodes": {"w": {"op": "pattern", "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b: 'out' names 'x', which is not a node"),
    (looks_file(looks={"a": {"layers": [*layered("solid")["layers"], *layered("solid")["layers"]]}}),
     "look 'a': layer id 'base' is used more than once"),
    (looks_file(current="b", looks={"a": layered("solid")}), "'current' names 'b', which is not a look"),
    (looks_file(cycle={"end": "b"}), "'end' names 'b', which is not a look"),
    # Not a name at all, and unhashable: a problem, not a TypeError at launch.
    (looks_file(current=["a"], looks={"a": layered("solid")}), "'current' names ['a'], which is not a look"),
    (looks_file(cycle={"end": {"a": 1}}), "'end' names {'a': 1}, which is not a look"),
    (looks_file(cycle={"idle": 0}), "'idle' is a number of seconds above 0"),
    (looks_file(cycle={"rounds": 1.5}), "'rounds' is a whole number"),
    (looks_file(cycle={"dur": 60}), "cycle: unknown key 'dur'; expected each, end, fresh, idle, rounds, seed"),
    (looks_file(cycle=[1]),  # every key it takes
     "'cycle' is an object with 'each', 'end', 'fresh', 'idle', 'rounds', 'seed', 'weights', 'window'"),
])
def test_a_bad_file_is_refused_naming_the_problem(text, message):
    with pytest.raises(LookError) as err:
        parse_looks(text, cap=0.6)
    assert message in str(err.value)


@pytest.mark.parametrize("doc, start", [
    ({"version": 3, "looks": {"a": {"pattern": "solid"}}}, "looks file is version 3; "),
    ({"version": 2, "attract": {}}, "looks file is version 2; "),
    ({"version": "4"}, "looks file is version '4'; "),
    ({"looks": {}}, "looks file has no version; "),
])
def test_a_file_of_another_version_is_refused_alone(doc, start):
    """A v3 file of single-pattern looks is not read as layers: a clean
    break, with no migration."""
    with pytest.raises(LookError) as err:
        parse_looks(json.dumps(doc))
    fix = "move it aside and save the looks again from the page"
    assert err.value.problems == [f"{start}this pewpew reads version 4: {fix}"]


def test_every_problem_is_reported_at_once():
    text = looks_file(current="zz", looks={"a": layered("solid", cycle=1), "b": layered("solid", fade="slow")})
    with pytest.raises(LookError) as err:
        parse_looks(text)
    assert len(err.value.problems) == 3


def test_pattern_problems_lists_looks_that_no_longer_fit_their_pattern():
    def declared(name):
        if name == "broken":
            raise FileNotFoundError(2, "No such file or directory", "/secret/broken.py")
        return LOOK_CLASSES.get(name)

    book = LookBook({
        "ok": solid(1.0),
        "gone": look("nosuch"),
        "wide": look("solid", {"red": 2.0}),
        "renamed": look("solid", {"tint": 2.0}),
        "broken": look("broken"),
        "top": Look((pattern_layer("base", "solid"), pattern_layer("top", "nosuch"))),
    })
    problems = pattern_problems(book, declared)
    assert problems[0] == "look 'gone': layers.base.nosuch: unknown pattern 'nosuch'"
    assert "look 'wide': layers.base.solid.red must be within 0.0..1.0" in problems[1]
    assert "look 'renamed': layers.base.solid: unknown param 'tint'; params: red, green, blue" in problems[2]
    assert problems[3] == (
        "look 'broken': layers.base.broken: pattern 'broken' does not load: FileNotFoundError: No such file or "
        "directory"
    )
    assert problems[4] == "look 'top': layers.top.nosuch: unknown pattern 'nosuch'"
    assert len(problems) == 5


def test_a_bad_file_fails_the_launch_with_one_line_naming_it(tmp_path):
    path = tmp_path / "looks.json"
    path.write_text(looks_file(looks={"a": layered("solid", fade=-1)}))
    with pytest.raises(SystemExit) as err:
        run_main(["run", "comet", "--map", "line:8", "--frames", "1", "--looks", str(path)])
    assert str(err.value) == f"{path}: look 'a': fade must be within 0.0..600.0, got -1.0"


def test_pattern_drift_warns_at_launch_and_the_aura_starts(tmp_path, caplog, capsys):
    """A restart must not refuse a file whose looks have drifted from their
    patterns: the drifted current look falls back to the command line's
    pattern, and the others are left to their recall."""
    path = tmp_path / "looks.json"
    path.write_text(looks_file(
        current="gone",
        looks={"gone": layered("nosuch"), "wide": layered("pulse", {"color": {"h": 1e9, "s": 1, "v": 1}})},
    ))
    argv = ["run", "comet", "--map", "line:8", "--frames", "1", "--looks", str(path)]
    with caplog.at_level("WARNING", logger="pewpew"):
        assert run_main(argv)[0] == 0
    warned = [r.getMessage() for r in caplog.records if r.name == "pewpew.run"]
    assert f"{path}: look 'gone': layers.base.nosuch: unknown pattern 'nosuch'" in warned
    assert any(m.startswith(f"{path}: look 'wide': layers.base.pulse.color.h must be within") for m in warned)
    assert "starting with comet" in capsys.readouterr().err


def test_the_notes_key_survives_a_rewrite(tmp_path):
    path = tmp_path / "looks.json"
    notes = {"mood": "calm", "todo": ["retune dusk"]}
    path.write_text(looks_file(looks={"a": layered("solid")}, notes=notes))
    book = load_looks(path)
    assert book.notes == notes
    rig = aura_rig(Solid)
    looks = Looks(path, book, rig.deck, rig.master)
    assert looks.save("b") is None and looks.delete("a") is None
    assert json.loads(path.read_text())["notes"] == notes
    assert "notes" not in json.loads(LookBook().to_bytes())


# ---- the crossfade -----------------------------------------------------------


def renderer(cls, mapping=None, **params):
    return Renderer(cls(), line(4) if mapping is None else mapping, params=params)


def test_between_fades_the_crossfader_is_the_renderer():
    plain = renderer(Wave, canopy().mapping)
    fader = Crossfader(renderer(Wave, canopy().mapping))
    for i in range(1, 6):
        assert np.array_equal(fader.advance_to(i / 60), plain.advance_to(i / 60))


def test_the_fade_midpoint_is_the_mean_of_the_two_frames():
    fader = Crossfader(renderer(Solid, red=1.0))
    fader.fade_to(renderer(Solid, red=0.0, blue=1.0), 1.0)
    assert fader.fading
    np.testing.assert_array_equal(fader.advance_to(0.25), [[0.75, 0.0, 0.25]] * 4)
    mid = fader.advance_to(0.5)
    assert mid.dtype == np.float32
    np.testing.assert_array_equal(mid, [[0.5, 0.0, 0.5]] * 4)
    assert fader.progress == 0.5
    np.testing.assert_array_equal(fader.advance_to(1.0), [[0.0, 0.0, 1.0]] * 4)
    assert not fader.fading and fader.progress is None


def test_a_fade_blends_across_units_pixel_for_pixel():
    """A per-pixel look fading into a per-fixture one: each side gathers to
    the pixel frame first, so the blend is of two (N,3) frames."""
    r = compile_room(room(bar("a", pixels=4), bar("b", pixels=4, start=[0, 1], end=[1, 1], chain=2)))
    out = Renderer(PixelRamp(), r.mapping, grouping=r.grouping)
    fader = Crossfader(out)
    fader.fade_to(out.spawn(FixtureRamp()), 2.0)
    assert (out.units, fader.current.units) == ("pixel", "fixture")
    frame = fader.advance_to(0.5)  # a = 0.25
    want = np.zeros((8, 3), dtype=np.float32)
    want[:, 0] = np.arange(8, dtype=np.float32) / 8 * np.float32(0.75)
    want[:4, 2] = np.float32(0.5) * np.float32(0.25)
    want[4:, 2] = np.float32(1.0) * np.float32(0.25)
    np.testing.assert_array_equal(frame, want)


def test_a_raising_side_still_renders_a_frame():
    fader = Crossfader(renderer(Solid, red=0.0, green=1.0))
    fader.fade_to(renderer(Raises), 1.0)
    frame = fader.advance_to(0.5)  # contained: the incoming side is the error frame
    assert frame.shape == (4, 3) and np.all(frame[:, 1] == np.float32(0.5))
    assert fader.error is not None and fader.error.pattern == "raises"


class FourOnly(Solid):
    """Binds a 4-pixel map only: `setup` raises on any other."""

    def setup(self, n, x, y, z, index):
        if n != 4:
            raise RuntimeError("binds 4 pixels only")


def test_an_outgoing_side_that_cannot_render_ends_the_fade_not_the_frame():
    out = renderer(FourOnly)
    fader = Crossfader(out)
    fader.fade_to(renderer(Solid, red=0.0, blue=1.0), 1.0)
    with pytest.raises(RuntimeError, match="binds 4 pixels only"):
        out.rebind(line(6))  # leaves it unbound
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.0, 0.0, 1.0]] * 4)
    assert not fader.fading


def test_a_map_reload_the_outgoing_side_cannot_bind_ends_the_fade():
    fader = Crossfader(renderer(FourOnly))
    fader.fade_to(renderer(Solid, red=0.0, blue=1.0), 1.0)
    fader.rebind(line(6))
    assert not fader.fading
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.0, 0.0, 1.0]] * 6)


def test_a_map_reload_mid_fade_rebinds_both_sides_and_keeps_the_fade():
    out = renderer(Solid, red=1.0)
    fader = Crossfader(out)
    fader.fade_to(renderer(Solid, red=0.0, blue=1.0), 1.0)
    fader.advance_to(0.25)
    fader.rebind(line(6))
    assert fader.fading and out.n == 6 and fader.current.n == 6
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.5, 0.0, 0.5]] * 6)


def test_hot_reload_and_live_sets_reach_the_look_fading_in(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=1.0)})
    out = rig.renderer()
    before = out.pattern
    assert rig.looks.recall("blue") is None and rig.fader.fading
    incoming = rig.renderer()
    rig.reloader()._target.swap(Solid())  # what the layer's reloader does on a save
    assert type(incoming.pattern) is Solid and incoming.pattern is not before and out.pattern is before
    assert rig.control.set("layers.base.solid.green", 1.0) is None
    rig.calls.drain()
    assert incoming.params["green"] == 1.0 and out.params["green"] == 0.0


# ---- recall --------------------------------------------------------------------


def test_recall_with_no_fade_is_an_instant_swap(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=3.0)})
    rig.frame(1 / 60)
    assert rig.looks.recall("blue", 0.0) is None  # the page's override beats the stored 3 s
    assert not rig.fader.fading
    np.testing.assert_array_equal(rig.frame(2 / 60), [[0.0, 0.0, 1.0]] * 4)
    assert rig.deck.current == "solid" and rig.looks.book.current == "blue"
    assert json.loads(rig.path.read_text())["current"] == "blue"  # persisted


def test_recall_uses_the_stored_fade_unless_the_page_overrides_it(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=1.0)})
    rig.looks.recall("blue")
    np.testing.assert_array_equal(rig.frame(0.5), [[0.5, 0.0, 0.5]] * 4)
    state = rig.looks.state()
    assert (state["fading"], state["progress"]) == ("blue", 0.5)


def test_a_recall_during_a_fade_waits_for_it_then_starts(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=1.0), "green": solid(0.0, 1.0, 0.0, fade=1.0)})
    rig.looks.recall("blue")
    rig.frame(0.5)
    assert rig.looks.recall("green") is None
    assert rig.looks.state()["pending"] == "green"
    np.testing.assert_array_equal(rig.frame(0.75), [[0.25, 0.0, 0.75]] * 4)  # still red to blue
    np.testing.assert_array_equal(rig.frame(1.0), [[0.0, 0.0, 1.0]] * 4)  # that fade is done
    # The next frame starts blue to green, from t0 = 1.0.
    np.testing.assert_array_equal(rig.frame(1.5), [[0.0, 0.5, 0.5]] * 4)
    assert rig.looks.state()["fading"] == "green" and rig.looks.state()["pending"] is None
    assert rig.looks.book.current == "green"


def test_deleting_the_look_waiting_for_a_fade_drops_the_wait(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=1.0), "green": solid(0.0, 1.0, 0.0, fade=1.0)})
    rig.looks.recall("blue")
    rig.frame(0.5)
    assert rig.looks.recall("green") is None and rig.looks.delete("green") is None
    assert rig.looks.state()["pending"] is None
    for t in (1.0, 1.5):
        np.testing.assert_array_equal(rig.frame(t), [[0.0, 0.0, 1.0]] * 4)
    assert rig.looks.error is None and rig.looks.book.current == "blue"


def test_a_newer_recall_replaces_the_one_waiting(tmp_path):
    rig = make_rig(tmp_path, {n: solid(fade=1.0) for n in ("a", "b", "c")})
    rig.looks.recall("a")
    rig.looks.recall("b")
    rig.looks.recall("c")
    assert rig.looks.state()["pending"] == "c"


def test_a_look_master_is_set_outside_the_blend(tmp_path):
    rig = make_rig(tmp_path, {"dim": solid(0.0, 0.0, 1.0, master=0.25, fade=1.0)})
    rig.looks.recall("dim")
    assert rig.master.level == 0.25 and rig.fader.fading  # the frame blend has no master in it
    np.testing.assert_array_equal(rig.frame(0.5), [[0.5, 0.0, 0.5]] * 4)


def test_values_that_no_longer_fit_start_at_the_default(tmp_path):
    rig = make_rig(tmp_path, {"old": look("solid", {"red": 0.5, "gone": 3.0})})
    assert rig.looks.recall("old", 0.0) is None
    assert rig.renderer().params.snapshot() == {"red": 0.5, "green": 0.0, "blue": 0.0}


def test_a_look_whose_setup_raises_is_refused_and_the_aura_keeps_running(tmp_path):
    class BadSetup(Solid):
        def setup(self, n, x, y, z, index):
            raise RuntimeError("no fixture")

    LOOK_CLASSES["badsetup"] = BadSetup
    try:
        rig = make_rig(tmp_path, {"bad": look("badsetup")})
        reason = rig.looks.recall("bad")
        assert reason == "cannot recall 'bad': layers.base: RuntimeError: no fixture"
        assert type(rig.renderer().pattern) is Solid and not rig.fader.fading
    finally:
        del LOOK_CLASSES["badsetup"]


def test_restore_comes_back_in_the_current_look_with_no_fade(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=5.0)}, current="blue")
    assert rig.looks.restore() is None
    np.testing.assert_array_equal(rig.frame(1 / 60), [[0.0, 0.0, 1.0]] * 4)


def test_a_start_restores_the_look_the_file_names(tmp_path):
    """The restart path: the command line says comet, the file says pulse."""
    path = tmp_path / "looks.json"
    write_atomic(path, LookBook({"calm": look("pulse", {"color": CALM})}, "calm").to_bytes())
    run = build(["run", "comet", "--frames", "2", "--looks", str(path)])
    assert run.serve() == 0
    assert type(layer_renderer(run).pattern) is Pulse and layer_renderer(run).params["color"] == HSV(30.0, 1.0, 1.0)


def test_the_status_says_which_part_failed_and_which_pattern_raised(tmp_path):
    """A looks error and a render error each reach the preview's status
    with their source. During a fade away from a pattern that raises, the
    status names that pattern, not the one fading in."""
    path = tmp_path / "looks.json"
    write_atomic(path, LookBook({"calm": look("pulse", {"color": CALM}, fade=1.0)}).to_bytes())
    run = build(["run", "comet", "--preview", "--port", "0", "--looks", str(path)])
    status = run.preview._status
    assert status() is None
    run.looks.error = "cannot recall 'x': it was deleted"
    assert status() == ("looks", "cannot recall 'x': it was deleted", None)
    run.looks.error = None
    layer_renderer(run).pattern.render = None  # every frame now raises
    run.fader.advance_to(1 / 60)
    assert status()[0::2] == ("render", "layers.base.comet")
    assert status()[1].startswith("layers.base.comet.render raised")
    assert run.looks.recall("calm") is None
    run.fader.advance_to(2 / 60)
    assert run.fader.fading and run.deck.current == "pulse"
    assert status()[0::2] == ("render", "layers.base.comet")


def test_a_start_after_a_stall_skips_the_restore_once(tmp_path, monkeypatch, capsys):
    """A fresh stall marker: the command line's pattern, not the look whose
    pattern may have hung. The marker is used up, so the next start restores."""
    path = tmp_path / "looks.json"
    write_atomic(path, LookBook({"calm": look("pulse", {"color": CALM})}, "calm").to_bytes())
    marker = tmp_path / "state" / "stalled"
    monkeypatch.setenv("PEWPEW_STALL_MARKER", str(marker))
    argv = ["run", "comet", "--frames", "1", "--looks", str(path)]
    marker.parent.mkdir()
    marker.write_text("5.2\n")
    first = build(argv)
    first.serve()
    assert "the last run stalled" in capsys.readouterr().err and not marker.exists()
    second = build(argv)
    second.serve()
    assert (type(layer_renderer(first).pattern), type(layer_renderer(second).pattern)) == (Comet, Pulse)


def test_the_watchdog_is_armed_before_the_restore(tmp_path, monkeypatch):
    """A restored look whose pattern hangs in `setup`: the first frame never
    comes, and the watchdog fires after its startup allowance. The setup
    waits for the stall, so a watchdog armed too late leaves it hanging and
    the test fails."""
    from pewpew.watchdog import Watchdog

    path = tmp_path / "looks.json"
    write_atomic(path, LookBook({"calm": look("pulse", {"color": CALM})}, "calm").to_bytes())
    monkeypatch.setenv("PEWPEW_STALL_MARKER", str(tmp_path / "stalled"))
    stalls: list[float] = []
    released = threading.Event()

    def fired(stalled: float) -> None:
        stalls.append(stalled)
        released.set()

    monkeypatch.setattr(run_module, "Watchdog", lambda timeout, **kw: Watchdog(
        timeout, **kw, startup=0.02, interval=0.005, on_stall=fired))
    hangs = Pulse.setup
    monkeypatch.setattr(Pulse, "setup", lambda self, *a: (released.wait(5.0), hangs(self, *a)))
    run_main(["run", "comet", "--frames", "1", "--looks", str(path), "--watchdog", "1"])
    assert len(stalls) == 1 and stalls[0] >= 0.02


# ---- saving and the changed marker ---------------------------------------------


def test_save_then_change_then_save_drives_the_changed_marker(tmp_path):
    rig = make_rig(tmp_path, {})
    assert rig.looks.state()["changed"] is False  # no current look
    assert rig.looks.save("warm", fade=4.0) is None
    saved = rig.looks.book.looks["warm"]
    assert saved == solid(1.0, master=1.0, fade=4.0)
    assert rig.looks.state()["current"] == "warm" and rig.looks.state()["changed"] is False
    rig.renderer().params.set("green", 0.5)
    assert rig.looks.state()["changed"] is True
    rig.renderer().params.set("green", 0.0)
    assert rig.looks.state()["changed"] is False
    rig.master.set(0.5)  # the look stores the master
    assert rig.looks.changed()
    assert rig.looks.save("warm") is None  # overwrite keeps the fade and cycle flag
    assert rig.looks.book.looks["warm"].fade == 4.0 and not rig.looks.changed()
    rig.renderer().params.set("green", 0.0)
    assert rig.control.set("layers.base.opacity", 0.5) is None  # a layer's mix is part of the look
    rig.calls.drain()
    assert rig.looks.changed()
    assert rig.control.set("layers.base.opacity", 1.0) is None
    rig.calls.drain()
    assert not rig.looks.changed()
    assert rig.deck.put("base", "pulse") is None  # another pattern, started from outside the looks
    assert rig.looks.changed()


def test_the_front_is_an_edit_a_save_keeps_and_names_whole_knobs_once(tmp_path):
    rig = make_rig(tmp_path, {"warm": solid(1.0)}, current="warm")
    assert rig.looks.restore() is None
    red, green = "layers.base.solid.red", "layers.base.solid.green"
    with LoopThread(rig.calls):
        assert rig.control.front([green, red]) is None
        assert rig.control.front([red, red]).startswith("a look's front lists each knob once")
        assert rig.control.front(["layers.base.solid.nosuch"]).startswith("front[0]: unknown knob")
        assert rig.control.front("red") == "front takes a list of knob addresses, got 'red'"
    assert rig.deck.fader.current.state()["front"] == [green, red] and rig.looks.changed()
    assert rig.looks.save("warm") is None and load_looks(rig.path).looks["warm"].front == (green, red)
    with LoopThread(rig.calls):
        assert rig.control.front([red]) is None
    assert rig.looks.changed()


def test_the_state_holds_each_knobs_saved_value_for_a_page_to_revert_to(tmp_path):
    rig = make_rig(tmp_path, {})
    assert rig.looks.state()["saved"] is None  # no current look
    assert rig.looks.save("warm") is None
    saved = rig.looks.state()["saved"]
    assert saved == rig.control.values() and saved["layers.base.solid.green"] == 0.0
    rig.renderer().params.set("green", 0.5)
    assert rig.looks.state()["saved"]["layers.base.solid.green"] == 0.0  # an edit leaves it
    assert rig.deck.put("base", "pulse") is None and rig.looks.leave() is None
    assert rig.looks.state()["saved"] is None  # no look is current after a pick


def test_a_save_with_no_master_choice_keeps_the_replaced_looks(tmp_path):
    rig = make_rig(tmp_path, {})
    assert rig.looks.save("bare", master=False) is None and rig.looks.book.looks["bare"].master is None
    assert rig.looks.save("bare", master=None) is None and rig.looks.book.looks["bare"].master is None
    assert rig.looks.save("new", master=None) is None and rig.looks.book.looks["new"].master == 1.0


def test_a_new_look_joins_the_idle_cycle_only_when_every_other_look_is_in_it(tmp_path):
    rig = make_rig(tmp_path, {})
    assert rig.looks.save("first") is None and rig.looks.book.looks["first"].cycle is False
    assert rig.looks.set_cycle("first", True) is None
    assert rig.looks.save() is None and rig.looks.book.looks["first 2"].cycle is True
    assert rig.looks.set_cycle("first", False) is None
    assert rig.looks.save("third") is None and rig.looks.book.looks["third"].cycle is False


def test_a_color_drives_the_changed_marker_across_a_hold(tmp_path):
    """Looks store and compare JSON values, so a color compares by its
    parts; a hold is not an edit, and the return brings the live tweak back."""
    rig = make_rig(tmp_path, {"calm": look("pulse", {"color": CALM}, fade=0.0), "cue": look("pulse", fade=0.0)},
              current="calm", start="pulse")
    assert rig.looks.recall("calm") is None
    rig.frame(1 / 60)
    assert not rig.looks.changed()
    rig.renderer().params.set("color", {"h": 90.0, "s": 1.0, "v": 1.0})
    assert rig.looks.changed()
    assert rig.looks.hold("door", "cue", 0.5, 0, rig.fader.t) is None
    rig.frame(2 / 60)
    assert rig.looks.held is not None and not rig.looks.changed()
    rig.frame(1.0)
    assert rig.looks.held is None and rig.renderer().params["color"] == HSV(90.0, 1.0, 1.0)
    assert rig.looks.changed()
    rig.renderer().params.set("color", HSV(30.0, 1.0, 1.0))
    assert not rig.looks.changed()


def test_a_look_without_master_ignores_the_master(tmp_path):
    rig = make_rig(tmp_path, {})
    rig.looks.save("free", master=False)
    assert rig.looks.book.looks["free"].master is None
    rig.master.set(0.2)
    assert not rig.looks.changed()


def test_delete_and_the_cycle_flag_persist(tmp_path):
    rig = make_rig(tmp_path, {"a": solid(), "b": solid()}, current="a",
              cycle=CycleConfig(end="a"))
    assert rig.looks.set_cycle("b", True) is None
    assert load_looks(rig.path).looks["b"].cycle is True
    assert rig.looks.delete("a") is None
    book = load_looks(rig.path)
    assert list(book.looks) == ["b"] and book.current is None and book.cycle.end is None
    assert rig.looks.delete("a").startswith("unknown look 'a'")


def test_a_look_s_own_fade_is_stored_alone_and_edits_stay_unsaved(tmp_path):
    rig = make_rig(tmp_path, {"a": solid(1.0, fade=2.0)}, current="a")
    assert rig.looks.restore() is None
    rig.renderer().params.set("green", 0.5)
    assert rig.looks.set_fade("a", 5.0) is None
    saved = load_looks(rig.path).looks["a"]
    assert saved == solid(1.0, fade=5.0) and rig.looks.changed()
    assert rig.looks.set_fade("a", -1) == "fade must be within 0.0..600.0, got -1.0"
    assert rig.looks.set_fade("b", 1.0).startswith("unknown look 'b'")


def test_a_pattern_dir_file_launched_by_path_saves_by_its_pick_name(tmp_path):
    folder = tmp_path / "patterns"
    folder.mkdir()
    (folder / "mine.py").write_text(MY_WAVE)
    path = tmp_path / "looks.json"
    run = build(["run", str(folder / "mine.py"), "--pattern-dir", str(folder), "--looks", str(path), "--map", "line:4"])
    assert run.deck.current == "mine" and spec(run.deck.snapshot().layers[0]) == "mine"
    assert run.looks.save("x") is None and spec(load_looks(path).looks["x"].layers[0]) == "mine"


def test_a_save_clears_the_last_recall_error(tmp_path):
    rig = make_rig(tmp_path, {"gone": look("nosuch", fade=0.0, cycle=True)}, cycle=CycleConfig(idle=0.1))
    for _ in range(10):
        rig.frame(rig.clock.advance())
    assert rig.looks.error.startswith("cannot recall 'gone': layers.base: unknown pattern 'nosuch'")  # the cycle's
    assert rig.looks.save("fresh") is None
    assert rig.looks.error is None


def test_a_pick_that_cannot_write_the_file_says_a_restart_comes_back_in_the_look(tmp_path, monkeypatch):
    rig = make_rig(tmp_path, {"a": solid(1.0, fade=0.0)}, current="a")
    assert rig.looks.restore() is None
    monkeypatch.setattr(os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("disk full")))
    rig.looks.leave()
    assert rig.looks.book.current is None
    assert rig.looks.error == "cannot write the looks file, so a restart comes back in look 'a'"


MY_WAVE = '''
import numpy as np
from pewpew import Float, Pattern

class Wave(Pattern):
    level = Float(0.3, 0.0, 1.0)

    def render(self, x, y, z, index):
        return np.full((self.n, 3), self.level, dtype=np.float32)
'''


def test_a_pattern_launched_by_path_saves_and_recalls_by_its_path(tmp_path):
    """The author's own `class Wave`, given as a file: the page names it by
    its class, but a look keeps its path, so a recall, a trigger hold's
    return and a restart run that file, never the gallery's Wave."""
    mine = tmp_path / "mywave.py"
    mine.write_text(MY_WAVE)
    path = tmp_path / "looks.json"
    run = build(["run", str(mine), "--looks", str(path), "--map", "line:4"])
    assert run.deck.current == "wave" and spec(run.deck.snapshot().layers[0]) == str(mine)
    assert run.looks.save("mine") is None
    assert spec(load_looks(path).looks["mine"].layers[0]) == str(mine)
    assert run.deck.put("base", "wave") is None  # the gallery's
    assert run.looks.recall("mine", 0.0) is None
    assert type(layer_renderer(run).pattern).__module__ == "pewpew_user.mywave"
    assert layer_renderer(run).params.snapshot_json() == {"level": 0.3}
    assert not run.looks.changed()


# ---- the idle cycle ------------------------------------------------------------


# ---- determinism through the live path -----------------------------------------


def live_frames(tmp_path) -> list[bytes]:
    """Wave on the canopy, then a 0.5 s recall of a sparkle look queued at
    frame 10, through PacedLoop on fake time — the runner's live path."""
    room = canopy()
    rig = make_rig(tmp_path, {"spark": look("sparkle", {"speed": 1.0}, fade=0.5)},
              mapping=room.mapping, grouping=room.grouping, start="wave")
    ft = FakeTime()
    out: list[bytes] = []
    loop = PacedLoop(rig.fader, fps=60.0, before=[rig.looks.before_frame], after=[rig.master.apply],
                     on_frame=[lambda t, f: out.append(f.tobytes())], now=ft.now, sleep=ft.sleep)
    loop.run(frames=10)
    loop.calls.call_soon(lambda: rig.looks.recall("spark"))
    loop.run(frames=50)
    assert rig.looks.book.current == "spark" and not rig.fader.fading
    return out


def test_a_recall_with_fade_through_the_live_loop_is_byte_identical_twice(tmp_path):
    (tmp_path / "1").mkdir()
    (tmp_path / "2").mkdir()
    first, second = live_frames(tmp_path / "1"), live_frames(tmp_path / "2")
    assert len(first) == 60 and first == second
    assert first[15] != first[9] and first[45] != first[15]  # it did change look


# ---- the socket ----------------------------------------------------------------


@pytest.fixture
def served(tmp_path):
    rig = aura_rig(looks={"blue": solid(0.0, 0.0, 1.0)}, path=tmp_path / "looks.json", timeout=2.0)
    with serving(rig.control, rig.calls) as (sink, ws, greeting):
        yield rig, sink, ws, greeting


def test_a_new_client_gets_the_looks(served):
    *_, greeting = served
    looks = greeting["aura"]["looks"]
    assert looks["items"] == [{"name": "blue", "cycle": False, "fade": 2.0}]
    assert (looks["current"], looks["changed"], looks["fading"], looks["cycling"]) == (None, False, None, False)


def test_recall_and_save_over_the_socket_echo_the_new_state(served):
    rig, sink, ws, _ = served
    ws.send(json.dumps({"type": "recall", "name": "blue", "fade": 0}))
    wait_until(lambda: rig.looks.book.current == "blue")
    ws.send(json.dumps({"type": "save", "name": "copy", "fade": None, "master": False}))
    wait_until(lambda: "copy" in rig.looks.book.looks)
    sink.send(0.0, np.zeros((4, 3), np.float32))
    echo = next_of(ws, "aura")  # the recalled look's params come first
    assert echo["looks"]["current"] == "copy"
    assert [item["name"] for item in echo["looks"]["items"]] == ["blue", "copy"]


def test_requests_without_a_looks_file_are_refused():
    control = aura_rig().control
    assert control.recall("a") == "no looks file: start the run with --looks PATH"
    assert control.state()["looks"] is None


# ---- the bare run's default geometry ---------------------------------------------


def test_a_bare_run_of_a_canopy_set_pattern_gets_the_canopy_fixtures():
    mapping, grouping = geometry(None, Sparkle, None)
    assert len(mapping) == 3840 and grouping is not None and len(grouping.centres) == 60
    assert geometry(None, Wave, None)[1] is not None
    assert geometry(None, Solid, None)[1] is None  # no study entry
    assert geometry(line(8), Sparkle, None)[1] is None
    run = build(["run", "sparkle", "--frames", "1"])
    assert layer_renderer(run).units == "fixture" and layer_renderer(run).pattern.n == 60


def test_a_recall_moves_the_reload_watch_and_a_pick_mid_fade_cuts_to_the_pick(tmp_path):
    """Through the aura control: the reloader follows the recalled
    pattern's file, and a pick during the fade cuts to the picked pattern,
    drops the recall waiting behind the fade, and leaves no look current."""
    rig = aura_rig(mapping=line(8), catalog=Catalog(),
                   looks={"calm": look("pulse", fade=1.0), "deep": look("wash", fade=0.0)},
                   path=tmp_path / "looks.json")
    with LoopThread(rig.calls):
        assert rig.control.recall("calm") is None
        assert rig.reloader().loaded.cls is Pulse and rig.control.state()["pattern"] == "pulse"
        assert rig.fader.fading
        assert rig.control.recall("deep") is None  # waits for calm's fade
        assert rig.control.state()["looks"]["pending"] == "deep"
        assert rig.control.pick("comet") is None
    assert type(rig.renderer().pattern) is Comet and not rig.fader.fading
    assert rig.reloader().loaded.cls is Comet
    looks = rig.control.state()["looks"]
    assert (looks["current"], looks["changed"], looks["pending"]) == (None, False, None)
    assert json.loads(rig.path.read_text())["current"] is None  # a restart runs the command line's pattern
    rig.looks.before_frame(rig.fader.t)  # no queued recall replaces the pick
    assert type(rig.renderer().pattern) is Comet
