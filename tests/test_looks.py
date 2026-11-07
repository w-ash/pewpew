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
    FLOW,
    FLOW_LOOK,
    FakeTime,
    LoopThread,
    aura_rig,
    build,
    hosted,
    layer_renderer,
    layered,
    look,
    next_of,
    one_node,
    program_of,
    restore,
    run_main,
    serving,
    solid,
    wait_until,
)
from pewpew.aura.book import (
    VERSION,
    CycleConfig,
    LookBook,
    LookError,
    load_looks,
    parse_looks,
    route_reasons,
)
from pewpew.aura.looks import Looks
from pewpew.compose import DEFAULT_FADE, Layer, Look, Route
from pewpew.crossfade import Crossfader
from pewpew.fx import expr
from pewpew.fx.graph import Graph, Node, Program
from pewpew.fx.host import ProgramPattern
from pewpew.jsonfile import write_atomic
from pewpew.mapping import grid, line
from pewpew.pace import PacedLoop
from pewpew.params import HSV, ParamSet
from pewpew.pattern import Pattern
from pewpew.render import Renderer

pytestmark = pytest.mark.usefixtures("fake_ops")

CALM = {"h": 30.0, "s": 1.0, "v": 1.0}
# A look of one zoo_test node at the calm color: a color knob to edit.
CALM_LOOK = look("zoo_test", {"color": CALM})


def make_rig(tmp_path, looks, mapping=None, current=None, cycle=None, start=None):
    """An aura over a book of test looks, with no loop and no sinks."""
    return aura_rig(start, mapping=mapping, looks=looks, current=current, cycle=cycle, path=tmp_path / "looks.json")


def knobs(source, nid: str = "solid") -> ParamSet:
    """The knobs of node `nid` of the program `source` runs: a renderer,
    or a rig's layer `base`."""
    pattern = (source if isinstance(source, Renderer) else source.renderer()).pattern
    assert isinstance(pattern, ProgramPattern)
    return pattern.node_params[nid]


def program_running(run) -> Program:
    """The program a run's layer `base` runs now."""
    return run.aura.fader.current.layer("base").layer.program


def looks_file(**fields) -> str:
    """A looks file of this version with `fields`, as text."""
    return json.dumps({"version": VERSION, **fields})


# ---- the file ----------------------------------------------------------------


def test_the_file_round_trips_and_keeps_look_order(tmp_path):
    book = LookBook(
        {"b": solid(1.0, master=0.5, fade=3.0, cycle=True), "a": look("zoo_test", {"color": CALM}, seed=7)},
        "a", CycleConfig(idle=120.0, each=20.0, rounds=2, end="b"),
    )
    path = tmp_path / "looks.json"
    write_atomic(path, book.to_bytes())
    again = load_looks(path)
    assert again == book and list(again.looks) == ["b", "a"]
    doc = json.loads(path.read_text())
    assert doc["version"] == 4 and "master" not in doc["looks"]["a"] and doc["looks"]["a"]["seed"] == 7
    assert doc["looks"]["a"]["layers"] == [{
        "id": "base", "opacity": 1.0, "blend": "normal", "enabled": True, "out": "zoo_test",
        "nodes": {"zoo_test": {"op": "zoo_test", "args": {"color": CALM}}},
    }]
    assert doc["looks"]["a"]["fade"] == DEFAULT_FADE
    assert again.in_cycle == ["b"]


BREATH = {"signals": {"breath": {"op": "lfo", "args": {"rate": 0.5}}},
          "routes": [{"source": "breath", "path": "layers.base.solid.red", "depth": 0.25}],
          "front": ["layers.base.solid.red"]}


def test_a_look_holds_its_signals_routes_and_front_and_the_file_keeps_them():
    """The canonical v4 shape (ADR-006 amendment "layered paths"); empty
    or null ones load as none, and a rewrite keeps every one."""
    book = parse_looks(looks_file(looks={"a": layered("solid_test", **BREATH),
                                         "b": layered("solid_test", signals={}, routes=[], front=None)}))
    a = book.looks["a"]
    assert [node.op for node in a.signals or ()] == ["lfo"] and a.front == ("layers.base.solid.red",)
    assert a.routes[0].depth == 0.25 and book.looks["b"] == look("solid_test")
    assert parse_looks(book.to_bytes()) == book


def test_a_missing_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_looks(tmp_path / "new.json")


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
    (looks_file(looks={"../x": layered("solid_test")}), "bad look name '../x'"),
    (looks_file(looks={"a": layered("solid_test", master=0.9)}),
     "master must be within 0.0..0.6, got 0.9 (the cap set at launch)"),
    (looks_file(looks={"a": layered("solid_test", fade=-1)}), "fade must be within 0.0..600.0"),
    (looks_file(looks={"a": layered("solid_test", cycle="yes")}), "cycle takes true or false"),
    (looks_file(looks={"a": layered("solid_test", seed=-1)}),
     "look 'a': 'seed' is a whole number of at least 0, got -1"),
    (looks_file(looks={"a": layered("solid_test", [1])}),
     "look 'a': layers.base.solid: 'args' is an object of name: value"),
    (looks_file(looks={"a": {"pattern": "solid"}}),
     "look 'a': unknown key 'pattern'; expected cycle, fade, front, layers, master, routes, seed, signals"),
    (looks_file(looks={"a": layered("solid_test", routes=[{"source": "breath", "path": "layers.base.opacity",
                                                      "depth": 0.2}])}),
     "look 'a': routes[0]: unknown signal 'breath'; signals: (none)"),
    (looks_file(looks={"a": layered("solid_test", signals={"breath": {"op": "lfo"}})}),
     "look 'a': signals.breath: nothing reads signal 'breath'; route it to a knob, or remove it"),
    (looks_file(looks={"a": layered("solid_test", signals={"w": {"op": "osc"}})}),
     ("look 'a': signals.w: osc is not a signal op; a look's signals run band, beat, env, knob, lfo, smooth, walk, "
     "and osc goes in a layer's program")),
    (looks_file(looks={"a": layered("solid_test", **{**BREATH, "routes": [{"source": "breath", "depth": "deep"}]})}),
     "look 'a': routes[0]: 'path' is missing"),
    (looks_file(looks={"a": layered("solid_test", front=0)}),
     "look 'a': 'front' is a list of the addresses of the knobs a page shows first"),
    (looks_file(looks={"a": {"layers": []}}), "look 'a': a look has at least one layer"),
    (looks_file(looks={"a": {"layers": {}}}), "look 'a': 'layers' is a list of layers, the bottom one first"),
    (looks_file(looks={"a": {"layers": [{"id": "Base", "nodes": {}}]}}), "look 'a': layers[0]: bad layer id 'Base'"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "opacity": 2, "nodes": {}}]}}),
     "look 'a': layers.b.opacity must be within 0.0..1.0, got 2"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "blend": "glow", "nodes": {}}]}}),
     "look 'a': layers.b.blend takes one of 'normal', 'add', "),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"blend": {"op": "osc"}}}]}}),
     "look 'a': layers.b: bad node id 'blend': alpha, blend, enabled, nodes, opacity, out are reserved"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "glow", "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: unknown op 'glow'"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "osc", "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: unknown param 'pattern'; params: freq, sync, offset, axis"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: 'op' is missing; name the node's op, one of "),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "pattern",
                                                                    "args": {"pattern": "solid"}}}}]}}),
     "look 'a': layers.b.w: unknown op 'pattern'"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "nodes": {"w": {"op": "osc", "pattern": "solid"}}}]}}),
     "look 'a': layers.b.w: unknown key 'pattern'; expected args, in, op"),
    (looks_file(looks={"a": {"layers": [{"id": "b", "out": "x", "nodes": {"w": {"op": "osc"}}}]}}),
     "look 'a': layers.b: 'out' names 'x', which is not a node"),
    (looks_file(looks={"a": {"layers": [*layered("solid_test")["layers"], *layered("solid_test")["layers"]]}}),
     "look 'a': layer id 'base' is used more than once"),
    (looks_file(current="b", looks={"a": layered("solid_test")}), "'current' names 'b', which is not a look"),
    (looks_file(cycle={"end": "b"}), "'end' names 'b', which is not a look"),
    # Not a name at all, and unhashable: a problem, not a TypeError at launch.
    (looks_file(current=["a"], looks={"a": layered("solid_test")}), "'current' names ['a'], which is not a look"),
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
    text = looks_file(current="zz", looks={"a": layered("solid_test", cycle=1),
                                           "b": layered("solid_test", fade="slow")})
    with pytest.raises(LookError) as err:
        parse_looks(text)
    assert len(err.value.problems) == 3


BREATHING = Graph((Node("breath", "lfo", {"rate": 0.5}),))


def test_route_reasons_lists_looks_whose_routes_or_front_reach_no_knob():
    book = LookBook({
        "ok": solid(1.0),
        "tint": look("solid_test", signals=BREATHING, routes=(Route("breath", "layers.base.solid.tint", 0.2),)),
        "front": look("solid_test", front=("layers.base.nosuch.red",)),
    })
    knobs = "layers.base.solid.red, layers.base.solid.green, layers.base.solid.blue, layers.base.opacity, "
    assert route_reasons(book) == [
        ("look 'tint': routes[0]: unknown knob 'layers.base.solid.tint' (did you mean 'layers.base.solid.green'?); "
         f"knobs: {knobs}signals.breath.rate, signals.breath.offset"),
        ("look 'front': front[0]: unknown knob 'layers.base.nosuch.red' (did you mean 'layers.base.solid.red'?); "
         f"knobs: {knobs}layers.base.blend, layers.base.enabled"),
    ]


def test_a_bad_file_fails_the_launch_with_one_line_naming_it(tmp_path):
    path = tmp_path / "looks.json"
    path.write_text(looks_file(looks={"a": layered("solid_test", fade=-1)}))
    with pytest.raises(SystemExit) as err:
        run_main(["run", str(path), "--map", "line:8", "--frames", "1"])
    assert str(err.value) == f"{path}: look 'a': fade must be within 0.0..600.0, got -1.0"


def test_a_route_to_no_knob_warns_at_launch_and_the_aura_starts(tmp_path, caplog):
    """A restart must not refuse a file whose routes reach no knob: the
    launch names each, and the look is left to its recall."""
    path = tmp_path / "looks.json"
    tint = [{"source": "breath", "path": "layers.base.solid.tint", "depth": 0.2}]
    path.write_text(looks_file(current="calm", looks={
        "tint": layered("solid_test", signals={"breath": {"op": "lfo"}}, routes=tint), "calm": layered("osc"),
    }))
    with caplog.at_level("WARNING", logger="pewpew"):
        run = build(["run", str(path), "--map", "line:8", "--frames", "1"])
        assert run.serve() == 0
    warned = [r.getMessage() for r in caplog.records if r.name == "pewpew.run"]
    assert any(m.startswith(f"{path}: look 'tint': routes[0]: unknown knob 'layers.base.solid.tint'") for m in warned)
    assert run.looks.book.current == "calm"


def test_the_notes_key_survives_a_rewrite(tmp_path):
    path = tmp_path / "looks.json"
    notes = {"mood": "calm", "todo": ["retune dusk"]}
    path.write_text(looks_file(looks={"a": layered("solid_test")}, notes=notes))
    book = load_looks(path)
    assert book.notes == notes
    rig = aura_rig()
    looks = Looks(path, book, rig.deck, rig.master)
    assert looks.save("b") is None and looks.delete("a") is None
    assert json.loads(path.read_text())["notes"] == notes
    assert "notes" not in json.loads(LookBook().to_bytes())


# ---- the crossfade -----------------------------------------------------------


def renderer(op: str = "solid_test", mapping=None, **args):
    """A renderer, named `layers.base`, of one node of `op` at `args`."""
    return Renderer(ProgramPattern.of(one_node(op, args))(), line(4) if mapping is None else mapping,
                    name="layers.base")


def test_between_fades_the_crossfader_is_the_renderer():
    plain = hosted(FLOW, grid(8, 8))
    fader = Crossfader(hosted(FLOW, grid(8, 8)))
    for i in range(1, 6):
        assert np.array_equal(fader.advance_to(i / 60), plain.advance_to(i / 60))


def test_the_fade_midpoint_is_the_mean_of_the_two_frames():
    fader = Crossfader(renderer(red=1.0))
    fader.fade_to(renderer(red=0.0, blue=1.0), 1.0)
    assert fader.fading
    np.testing.assert_array_equal(fader.advance_to(0.25), [[0.75, 0.0, 0.25]] * 4)
    mid = fader.advance_to(0.5)
    assert mid.dtype == np.float32
    np.testing.assert_array_equal(mid, [[0.5, 0.0, 0.5]] * 4)
    assert fader.progress == 0.5
    np.testing.assert_array_equal(fader.advance_to(1.0), [[0.0, 0.0, 1.0]] * 4)
    assert not fader.fading and fader.progress is None


def test_a_raising_side_still_renders_a_frame():
    fader = Crossfader(renderer(red=0.0, green=1.0))
    fader.fade_to(renderer("raises_test"), 1.0)
    frame = fader.advance_to(0.5)  # contained: the incoming side is the error frame
    assert frame.shape == (4, 3) and np.all(frame[:, 1] == np.float32(0.5))
    assert fader.error is not None and fader.error.pattern == "layers.base"


class FourOnly(Pattern):
    """Red that binds a 4-pixel map only: `setup` raises on any other."""

    def setup(self, n, x, y, z, index):
        if n != 4:
            raise RuntimeError("binds 4 pixels only")

    def render(self, x, y, z, index):
        return np.tile(np.array([1.0, 0.0, 0.0], np.float32), (self.n, 1))


def test_an_outgoing_side_that_cannot_render_ends_the_fade_not_the_frame():
    out = Renderer(FourOnly(), line(4))
    fader = Crossfader(out)
    fader.fade_to(renderer(red=0.0, blue=1.0), 1.0)
    with pytest.raises(RuntimeError, match="binds 4 pixels only"):
        out.rebind(line(6))  # leaves it unbound
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.0, 0.0, 1.0]] * 4)
    assert not fader.fading


def test_a_map_reload_the_outgoing_side_cannot_bind_ends_the_fade():
    fader = Crossfader(Renderer(FourOnly(), line(4)))
    fader.fade_to(renderer(red=0.0, blue=1.0), 1.0)
    fader.rebind(line(6))
    assert not fader.fading
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.0, 0.0, 1.0]] * 6)


def test_a_map_reload_mid_fade_rebinds_both_sides_and_keeps_the_fade():
    out = renderer(red=1.0)
    fader = Crossfader(out)
    fader.fade_to(renderer(red=0.0, blue=1.0), 1.0)
    fader.advance_to(0.25)
    fader.rebind(line(6))
    assert fader.fading and out.n == 6 and fader.current.n == 6
    np.testing.assert_array_equal(fader.advance_to(0.5), [[0.5, 0.0, 0.5]] * 6)


def test_live_sets_reach_the_look_fading_in(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=1.0)})
    out = rig.renderer()
    assert rig.looks.recall("blue") is None and rig.fader.fading
    incoming = rig.renderer()
    assert incoming is not out
    assert rig.control.set("layers.base.solid.green", 1.0) is None
    rig.calls.drain()
    assert knobs(incoming)["green"] == 1.0 and knobs(out)["green"] == 0.0


# ---- recall --------------------------------------------------------------------


def test_recall_with_no_fade_is_an_instant_swap(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=3.0)})
    rig.frame(1 / 60)
    assert rig.looks.recall("blue", 0.0) is None  # the page's override beats the stored 3 s
    assert not rig.fader.fading
    np.testing.assert_array_equal(rig.frame(2 / 60), [[0.0, 0.0, 1.0]] * 4)
    assert rig.looks.book.current == "blue"
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


def test_a_look_that_cannot_bind_is_refused_and_the_aura_keeps_running(tmp_path):
    fold = Look((Layer("base", program_of("osc(8).kaleid(5)")),))  # a fold, which a strip cannot run
    rig = make_rig(tmp_path, {"bad": fold})
    before = rig.renderer()
    reason = rig.looks.recall("bad")
    assert reason is not None and reason.startswith(
        "cannot recall 'bad': layers.base: layers.base.kaleid: kaleid needs a map of 2 or 3 dimensions")
    assert rig.renderer() is before and not rig.fader.fading


def test_restore_comes_back_in_the_current_look_with_no_fade(tmp_path):
    rig = make_rig(tmp_path, {"blue": solid(0.0, 0.0, 1.0, fade=5.0)}, current="blue")
    assert restore(rig) is None
    np.testing.assert_array_equal(rig.frame(1 / 60), [[0.0, 0.0, 1.0]] * 4)


def test_a_run_starts_in_the_look_the_file_names_and_writes_nothing(tmp_path):
    path = tmp_path / "looks.json"
    data = LookBook({"flow": FLOW_LOOK, "calm": CALM_LOOK}, "calm").to_bytes()
    path.write_bytes(data.replace(b"\n", b"\n\n"))  # spaced as no save writes it
    run = build(["run", str(path), "--frames", "2"])
    assert run.serve() == 0
    assert knobs(layer_renderer(run.aura), "zoo_test")["color"] == HSV(30.0, 1.0, 1.0)
    assert run.looks.book.current == "calm" and not run.looks.changed()
    assert path.read_bytes() == data.replace(b"\n", b"\n\n")


def test_the_status_says_which_part_failed_and_which_layer_raised(tmp_path):
    """A looks error and a render error each reach the preview's status
    with their source. During a fade away from a layer that raises, the
    status names that layer, not the look fading in."""
    path = tmp_path / "looks.json"
    book = LookBook({"flow": FLOW_LOOK, "calm": look("zoo_test", {"color": CALM}, fade=1.0)}, "flow")
    write_atomic(path, book.to_bytes())
    run = build(["run", str(path), "--preview", "--port", "0"])
    status = run.preview._status
    assert status() is None
    run.looks.error = "cannot recall 'x': it was deleted"
    assert status() == ("looks", "cannot recall 'x': it was deleted", None)
    run.looks.error = None
    # Every frame now raises: the test breaks the layer on purpose.
    layer_renderer(run.aura).pattern.render = None  # pyright: ignore[reportAttributeAccessIssue]
    run.aura.fader.advance_to(1 / 60)
    assert status()[0::2] == ("render", "layers.base")
    assert status()[1].startswith("layers.base.render raised")
    assert run.looks.recall("calm") is None
    run.aura.fader.advance_to(2 / 60)
    assert run.aura.fader.fading and run.looks.state()["fading"] == "calm"
    assert status()[0::2] == ("render", "layers.base")


def stalled_runs(tmp_path, monkeypatch, book: LookBook, *flags: str, marked: str = "5.2\n") -> tuple:
    """Two runs of `book` on a line, the first after a fresh stall marker
    with the text `marked` (by default the older shape): each run, and the
    looks file's bytes after the first."""
    path = tmp_path / "looks.json"
    write_atomic(path, book.to_bytes())
    marker = tmp_path / "state" / "stalled"
    monkeypatch.setenv("PEWPEW_STALL_MARKER", str(marker))
    argv = ["run", str(path), "--frames", "1", "--map", "line:8", *flags]
    marker.parent.mkdir()
    marker.write_text(marked)
    first = build(argv)
    first.serve()
    after = path.read_bytes()
    assert not marker.exists()  # used up
    second = build(argv)
    second.serve()
    return first, second, after


def test_a_start_after_a_stall_runs_the_next_look_of_the_cycle_and_says_so(tmp_path, monkeypatch, capsys):
    """A fresh stall marker: the run does not start in the look that
    stalled, but in the next of the idle cycle's order that can start
    (`fold` folds a plane, which a line has not), says so, and leaves the
    file naming the operator's look. The next start is the operator's look."""
    fold = Look((Layer("base", Program.of(expr.osc(2).kaleid(5).palette("ember"))),), cycle=True)
    book = LookBook({"calm": look("zoo_test", {"color": CALM}, cycle=True), "out": FLOW_LOOK, "fold": fold,
                     "wave": look("osc", {"freq": 3.0}, cycle=True)}, "calm")
    first, second, after = stalled_runs(tmp_path, monkeypatch, book)
    said = "the last run stalled in 'calm', so 'wave' runs"
    assert capsys.readouterr().err.strip() == said and first.looks.error == said
    wave, calm = (book.looks[name].layers[0].program for name in ("wave", "calm"))
    assert first.looks.book.current is None and program_running(first) == wave  # run as no saved look
    assert after == book.to_bytes()  # the file still names calm
    assert second.looks.error is None and program_running(second) == calm
    assert book.after("calm") == ["fold", "wave", "out"] and book.after("wave") == ["calm", "fold", "out"]
    assert first.looks.set_cycle("out", True) is None  # an unrelated write after the fallback
    assert load_looks(tmp_path / "looks.json").current == "calm"


def test_a_start_after_a_stall_of_the_only_look_runs_it_again_and_says_so(tmp_path, monkeypatch, capsys):
    book = LookBook({"calm": CALM_LOOK}, "calm")
    first, second, _ = stalled_runs(tmp_path, monkeypatch, book)
    said = "the last run stalled in 'calm', the only look that starts, so it runs again"
    assert capsys.readouterr().err.strip() == said and first.looks.error == said
    assert program_running(first) == program_running(second) == CALM_LOOK.layers[0].program


def marker_naming(*names: str) -> str:
    return json.dumps({"stalled": 5.2, "looks": list(names)})


def test_two_looks_that_both_stall_do_not_alternate_and_a_third_runs(tmp_path, monkeypatch, capsys):
    """The marker names the looks that stalled: with 'calm' and 'wave' named,
    the run starts in 'out', not back in either."""
    book = LookBook({"calm": CALM_LOOK, "wave": look("osc", {"freq": 3.0}, cycle=True), "out": FLOW_LOOK}, "calm")
    first, _, _ = stalled_runs(tmp_path, monkeypatch, book, marked=marker_naming("calm", "wave"))
    said = "the last run stalled in 'calm', 'wave', so 'out' runs"
    assert capsys.readouterr().err.strip() == said and first.looks.error == said
    assert program_running(first) == FLOW_LOOK.layers[0].program


def test_a_marker_that_names_other_looks_leaves_the_current_one_running(tmp_path, monkeypatch):
    book = LookBook({"calm": CALM_LOOK, "wave": look("osc", {"freq": 3.0}, cycle=True)}, "calm")
    first, _, _ = stalled_runs(tmp_path, monkeypatch, book, marked=marker_naming("wave"))
    assert program_running(first) == CALM_LOOK.layers[0].program and first.looks.book.current == "calm"


def test_a_start_after_every_look_stalled_runs_the_current_one_again_and_says_so(tmp_path, monkeypatch, capsys):
    book = LookBook({"calm": CALM_LOOK, "wave": look("osc", {"freq": 3.0}, cycle=True)}, "calm")
    first, _, _ = stalled_runs(tmp_path, monkeypatch, book, marked=marker_naming("wave", "calm"))
    said = "the last run stalled in 'wave', 'calm', no other look starts, so 'calm' runs again"
    assert capsys.readouterr().err.strip() == said and first.looks.error == said
    assert program_running(first) == CALM_LOOK.layers[0].program


def test_the_watchdog_is_armed_before_the_stack_is_built(tmp_path, monkeypatch):
    """A look whose program hangs in `setup` as the run builds it: the
    first frame never comes, and the watchdog fires after its startup
    allowance. The setup waits for the stall, so a watchdog armed too late
    leaves it hanging and the test fails."""
    from pewpew.watchdog import Watchdog

    path = tmp_path / "looks.json"
    write_atomic(path, LookBook({"calm": CALM_LOOK}, "calm").to_bytes())
    monkeypatch.setenv("PEWPEW_STALL_MARKER", str(tmp_path / "stalled"))
    stalls: list[float] = []
    released = threading.Event()

    def fired(stalled: float) -> None:
        stalls.append(stalled)
        released.set()

    monkeypatch.setattr(run_module, "Watchdog", lambda timeout, **kw: Watchdog(
        timeout, **kw, startup=0.02, interval=0.005, on_stall=fired))
    hangs = ProgramPattern.setup
    monkeypatch.setattr(ProgramPattern, "setup", lambda self, *a: (released.wait(5.0), hangs(self, *a)))
    run_main(["run", str(path), "--frames", "1", "--watchdog", "1"])
    assert len(stalls) == 1 and stalls[0] >= 0.02


# ---- saving and the changed marker ---------------------------------------------


def test_save_then_change_then_save_drives_the_changed_marker(tmp_path):
    rig = make_rig(tmp_path, {})
    assert rig.looks.state()["changed"] is False  # no current look
    assert rig.looks.save("warm", fade=4.0) is None
    saved = rig.looks.book.looks["warm"]
    assert saved == solid(1.0, master=1.0, fade=4.0)
    assert rig.looks.state()["current"] == "warm" and rig.looks.state()["changed"] is False
    knobs(rig).set("green", 0.5)
    assert rig.looks.state()["changed"] is True
    knobs(rig).set("green", 0.0)
    assert rig.looks.state()["changed"] is False
    rig.master.set(0.5)  # the look stores the master
    assert rig.looks.changed()
    assert rig.looks.save("warm") is None  # overwrite keeps the fade and cycle flag
    assert rig.looks.book.looks["warm"].fade == 4.0 and not rig.looks.changed()
    knobs(rig).set("green", 0.0)
    assert rig.control.set("layers.base.opacity", 0.5) is None  # a layer's mix is part of the look
    rig.calls.drain()
    assert rig.looks.changed()
    assert rig.control.set("layers.base.opacity", 1.0) is None
    rig.calls.drain()
    assert not rig.looks.changed()
    assert rig.deck.recall(FLOW_LOOK) is None  # another look, started from outside the looks
    assert rig.looks.changed()


def test_the_front_is_an_edit_a_save_keeps_and_names_whole_knobs_once(tmp_path):
    rig = make_rig(tmp_path, {"warm": solid(1.0)}, current="warm")
    assert restore(rig) is None
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
    knobs(rig).set("green", 0.5)
    assert rig.looks.state()["saved"]["layers.base.solid.green"] == 0.0  # an edit leaves it
    assert rig.deck.recall(FLOW_LOOK) is None and rig.looks.leave() is None
    assert rig.looks.state()["saved"] is None  # no look is current after a leave


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
    rig = make_rig(tmp_path, {"calm": look("zoo_test", {"color": CALM}, fade=0.0), "cue": look("zoo_test", fade=0.0)},
                   current="calm")
    assert rig.looks.recall("calm") is None
    rig.frame(1 / 60)
    assert not rig.looks.changed()
    knobs(rig, "zoo_test").set("color", {"h": 90.0, "s": 1.0, "v": 1.0})
    assert rig.looks.changed()
    assert rig.looks.hold("door", "cue", 0.5, 0, rig.fader.t) is None
    rig.frame(2 / 60)
    assert rig.looks.held is not None and not rig.looks.changed()
    rig.frame(1.0)
    assert rig.looks.held is None and knobs(rig, "zoo_test")["color"] == HSV(90.0, 1.0, 1.0)
    assert rig.looks.changed()
    knobs(rig, "zoo_test").set("color", HSV(30.0, 1.0, 1.0))
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
    assert restore(rig) is None
    knobs(rig).set("green", 0.5)
    assert rig.looks.set_fade("a", 5.0) is None
    saved = load_looks(rig.path).looks["a"]
    assert saved == solid(1.0, fade=5.0) and rig.looks.changed()
    assert rig.looks.set_fade("a", -1) == "fade must be within 0.0..600.0, got -1.0"
    assert rig.looks.set_fade("b", 1.0).startswith("unknown look 'b'")


def test_a_save_clears_the_last_recall_error(tmp_path):
    rig = make_rig(tmp_path, {"gone": look("nosuch", fade=0.0, cycle=True)}, cycle=CycleConfig(idle=0.1))
    for _ in range(10):
        rig.frame(rig.clock.advance())
    assert rig.looks.error.startswith("cannot recall 'gone': layers.base: layers.base.nosuch: unknown op 'nosuch'")
    assert rig.looks.save("fresh") is None
    assert rig.looks.error is None


def test_after_a_leave_no_look_is_current_and_the_file_keeps_naming_the_last(tmp_path):
    """A restart comes back in the look the file names: a leave, and every
    write while no look is current, leave it there."""
    rig = make_rig(tmp_path, {"a": solid(1.0, fade=0.0), "b": solid()}, current="a")
    assert restore(rig) is None
    rig.looks.leave()
    assert rig.looks.book.current is None and rig.looks.state()["current"] is None
    assert rig.looks.set_cycle("b", True) is None and rig.looks.delete("b") is None
    assert load_looks(rig.path).current == "a"
    assert rig.looks.delete("a") is None and load_looks(rig.path).current is None  # gone with its look


# ---- the idle cycle ------------------------------------------------------------


# ---- determinism through the live path -----------------------------------------


def live_frames(tmp_path) -> list[bytes]:
    """A moving field on a grid, then a 0.5 s recall of a stripes look
    queued at frame 10, through PacedLoop on fake time — the runner's live
    path."""
    stripes = Look((Layer("base", program_of('osc(6, 0.3).palette("ember")')),), fade=0.5)
    rig = make_rig(tmp_path, {"stripes": stripes}, mapping=grid(8, 8), start=FLOW_LOOK)
    ft = FakeTime()
    out: list[bytes] = []
    loop = PacedLoop(rig.fader, fps=60.0, before=[rig.looks.before_frame], after=[rig.master.apply],
                     on_frame=[lambda t, f: out.append(f.tobytes())], now=ft.now, sleep=ft.sleep)
    loop.run(frames=10)
    loop.calls.call_soon(lambda: rig.looks.recall("stripes"))
    loop.run(frames=50)
    assert rig.looks.book.current == "stripes" and not rig.fader.fading
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
    assert control.recall("a") == "no looks file: this aura saves no looks"
    assert control.state()["looks"] is None
