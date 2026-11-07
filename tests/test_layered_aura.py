"""Layered looks through the aura: the looks file, recall and crossfade,
saving, a pick on one layer, and an unattended run that leaves a failing
layer out."""

from __future__ import annotations

import json

import numpy as np

from fakes import LOOK_CLASSES, LoopThread, Solid, aura_rig, build, look, offered, pattern_looks, rgb
from pewpew.aura.book import LookBook, load_looks, parse_looks, pattern_problems
from pewpew.compose import Layer, Look, pattern_layer, pattern_node, pattern_of
from pewpew.fx.graph import Graph, Node, Program
from pewpew.jsonfile import write_atomic
from pewpew.run import map_hint

RED = {"red": 1.0, "green": 0.0, "blue": 0.0}
BLUE = {"red": 0.0, "green": 0.0, "blue": 1.0}

# Red under blue at half opacity: half red, half blue.
LAYERED = Look((pattern_layer("base", "solid", RED), pattern_layer("top", "solid", BLUE, opacity=0.5)), seed=3)


def make_rig(tmp_path, looks, **kw):
    return aura_rig(Solid, looks=looks, path=tmp_path / "looks.json", **kw)


def test_a_layered_look_round_trips_through_the_file(tmp_path):
    book = LookBook({"duo": LAYERED}, "duo")
    path = tmp_path / "duo.look.json"
    write_atomic(path, book.to_bytes())
    assert load_looks(path) == book
    layers = json.loads(path.read_text())["looks"]["duo"]["layers"]
    assert layers[1] == {
        "id": "top", "opacity": 0.5, "blend": "normal", "enabled": True, "out": "solid",
        "nodes": {"solid": {"op": "pattern", "args": {"pattern": "solid", **BLUE}}},
    }
    # Every key of a layer but its id and nodes has a default.
    terse = {"version": 4, "looks": {"a": {"layers": [{"id": "base", "nodes": {"w": {"op": "pattern",
                                                                                      "args": {"pattern": "wave"}}}}]}}}
    assert parse_looks(json.dumps(terse)).looks["a"] == Look((pattern_layer("base", "wave", node="w"),))


def test_recall_builds_every_layer(tmp_path):
    rig = make_rig(tmp_path, {"duo": LAYERED, "one": look("solid", BLUE, fade=0.0)})
    assert rig.looks.recall("duo", 0.0) is None
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.5, 0.0, 0.5, 4))
    assert [live.id for live in rig.fader.current.layers] == ["base", "top"] and rig.fader.current.seed == 3
    assert rig.looks.recall("one", 0.0) is None
    assert rig.control.state()["stack"]["layers"] == [
        {"id": "base", "nodes": [{"id": "solid", "op": "pattern", "label": "solid", "in": []}]},
    ]


def test_a_layer_runs_an_effect_program_and_its_knobs_are_the_auras(tmp_path):
    """A layer of several nodes runs whole: each node's knobs are the
    aura's, by address, the page sees each node, and a save keeps every
    knob at its live value."""
    glow = Program(Graph((
        pattern_node("solid", "solid", BLUE),
        Node("ramp", "osc", {"freq": 1.0, "sync": 0.0}),
        Node("mix", "mult", {}, ("solid", "ramp")),
    )), "mix")
    rig = make_rig(tmp_path, {"glow": Look((Layer("base", glow),))})
    assert rig.looks.recall("glow", 0.0) is None
    frame = rig.frame(1 / 60)
    ramp = 0.5 + 0.5 * np.sin(np.linspace(0.0, 1.0, 4, dtype=np.float32) * np.float32(2 * np.pi))
    np.testing.assert_allclose(frame[:, 2], ramp, atol=1e-6)
    assert rig.control.state()["stack"]["layers"] == [{"id": "base", "nodes": [
        {"id": "solid", "op": "pattern", "label": "solid", "in": []},
        {"id": "ramp", "op": "osc", "label": "Oscillator", "in": []},
        {"id": "mix", "op": "mult", "label": "Multiply", "in": ["solid", "ramp"]},
    ]}]
    assert rig.control.set("layers.base.solid.green", 1.0) is None
    assert rig.control.set("layers.base.ramp.freq", 2.0) is None
    assert rig.control.set("layers.base.ramp.freq", 99) == "layers.base.ramp.freq must be within 0.5..32.0, got 99.0"
    rig.calls.drain()
    assert rig.looks.save("glow") is None
    saved = load_looks(rig.path).looks["glow"].layers[0].program
    assert saved.graph["ramp"].args["freq"] == 2.0 and saved.graph["solid"].args["green"] == 1.0


def test_a_program_the_map_cannot_run_is_refused_whole(tmp_path, caplog):
    """A fold on a strip is refused with what to use instead, and logged
    with no traceback, which would say nothing more; the running look
    stays."""
    fold = Program(Graph((Node("ramp", "osc"), Node("fold", "kaleid", {}, ("ramp",)))), "fold")
    rig = make_rig(tmp_path, {})
    before = rig.fader.current
    with caplog.at_level("WARNING", logger="pewpew.aura.deck"):
        reason = rig.deck.recall(Look((Layer("base", fold),)))
    assert reason == (
        "layers.base: layers.base.fold: kaleid needs a map of 2 or 3 dimensions, and this map has 1; "
        "a strip has no plane to fold; use mirror along the strip"
    )
    (logged,) = caplog.records
    assert not logged.exc_info and logged.getMessage() == f"cannot start the look: {reason}"
    assert map_hint(reason) == "; run with --map grid:16x16 or --map lattice:8"
    assert map_hint("layers.base.comet.speed must be within 0.0..2.0, got 5.0") == ""
    assert rig.fader.current is before
    sparkle = Program(Graph((pattern_node("sparkle", "sparkle"), Node("dim", "contrast", {}, ("sparkle",)))), "dim")
    book = LookBook({"spark": Look((Layer("base", sparkle),))})
    assert pattern_problems(book, LOOK_CLASSES.get) == [(
        "look 'spark': layers.base.sparkle: pattern 'sparkle' renders once per fixture, not at the program's points; "
        "run it on a layer of its own"
    )]


def test_a_crossfade_between_two_layered_looks(tmp_path):
    other = Look((pattern_layer("base", "solid", BLUE), pattern_layer("glow", "solid", RED, blend="add",
                                                                         opacity=0.5)))
    rig = make_rig(tmp_path, {"duo": LAYERED, "other": other})
    assert rig.looks.recall("duo", 0.0) is None
    rig.frame(1 / 60)
    assert rig.looks.recall("other", 1.0) is None and rig.fader.fading
    # duo is (0.5, 0, 0.5), other (0.5, 0, 1): halfway through the fade, their mean.
    frame = rig.frame(1 / 60 + 0.5)
    np.testing.assert_allclose(frame, rgb(0.5, 0.0, 0.75, 4), atol=1e-6)
    np.testing.assert_array_equal(rig.frame(1.5), rgb(0.5, 0.0, 1.0, 4))
    assert not rig.fader.fading and rig.looks.book.current == "other"


def test_a_layered_save_keeps_every_layer_at_its_live_values(tmp_path):
    rig = make_rig(tmp_path, {"duo": LAYERED})
    assert rig.looks.recall("duo", 0.0) is None
    assert not rig.looks.changed()
    assert rig.control.set("layers.top.solid.green", 1.0) is None
    rig.calls.drain()
    assert rig.looks.changed()
    assert rig.looks.save("duo") is None and not rig.looks.changed()
    saved = load_looks(rig.path).looks["duo"]
    assert saved.seed == 3 and [layer.id for layer in saved.layers] == ["base", "top"]
    assert pattern_of(saved.layers[1].program.output) == ("solid", {"red": 0.0, "green": 1.0, "blue": 1.0})
    assert saved.layers[1].opacity == 0.5


def test_a_pick_runs_on_one_layer_and_the_rest_run_on(tmp_path):
    rig = make_rig(tmp_path, {"duo": LAYERED})
    assert rig.looks.recall("duo", 0.0) is None
    base = rig.renderer("base")
    with LoopThread(rig.calls):
        assert rig.control.pick("pixelramp", "top") is None
        assert rig.control.pick("solid", "nosuch") == "unknown layer 'nosuch'; layers: base, top"
        assert rig.control.pick("solid", 7) == "unknown layer 7; layers: base, top"
        assert rig.control.request({"type": "pick", "name": "pulse", "layer": None}) is None  # the bottom layer
    assert type(rig.renderer("top").pattern).__name__ == "PixelRamp"
    assert rig.fader.current.layer("top").mix.opacity == 0.5  # the layer keeps its mix
    assert type(rig.renderer("base").pattern).__name__ == "Pulse" and rig.renderer("base") is not base
    assert [n["label"] for layer in rig.control.state()["stack"]["layers"] for n in layer["nodes"]] == [
        "pulse", "pixelramp",
    ]
    # A pick on a layer of several edits the look: it stays current, changed until a save keeps it.
    assert rig.looks.book.current == "duo" and rig.looks.changed()


BOOM = '''
from pewpew import Pattern

class Boom(Pattern):
    def render(self, x, y, z, index):
        raise RuntimeError("boom")
'''


def test_run_plays_layered_looks_and_an_unattended_run_leaves_a_failing_layer_out(tmp_path, monkeypatch):
    offered(monkeypatch, boom=BOOM)
    path = tmp_path / "looks.look.json"
    duo = Look((pattern_layer("base", "comet"), pattern_layer("top", "boom", blend="add")))
    write_atomic(path, LookBook({"duo": duo}, "duo").to_bytes())
    argv = ["run", str(path), "--map", "line:300", "--frames", "1"]
    runs = []
    for extra in ([], ["--unattended"]):
        run = build([*argv, *extra])
        assert [layer.id for layer in run.fader.current.layers] == ["base", "top"]
        runs.append(np.stack([run.fader.advance_to(i / 60).copy() for i in range(1, 30)]))
        assert run.fader.error is not None and run.fader.error.pattern == "layers.top.boom"
        if run.watchdog is not None:
            run.watchdog.stop()  # armed as the run was built; it is never served
    dev, unattended = runs
    comet = build(["run", pattern_looks(), "--map", "line:300", "--frames", "1"])
    alone = np.stack([comet.fader.advance_to(i / 60).copy() for i in range(1, 30)])
    assert unattended.tobytes() == alone.tobytes()  # the failing layer is out of the mix
    assert (dev[:, :, 0] >= 0.25).all()  # in dev it pulses red over the room


def test_run_plays_a_look_of_effect_programs_from_its_json(tmp_path):
    path = tmp_path / "tide.look.json"
    path.write_text(json.dumps({"version": 4, "current": "tide", "looks": {"tide": {"seed": 7, "layers": [
        {"id": "base", "out": "tint", "nodes": {
            "waves": {"op": "osc", "args": {"freq": 8.0, "sync": 0.1}},
            "fold": {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
            "tint": {"op": "palette", "in": ["fold"], "args": {"palette": "ember"}}}},
        {"id": "glint", "blend": "screen", "opacity": 0.5, "nodes": {
            "w": {"op": "pattern", "args": {"pattern": "wave"}}, "dim": {"op": "contrast", "in": ["w"]}}}]}}}))
    run = build(["run", str(path), "--map", "grid:8x8", "--frames", "1"])
    frame = run.fader.advance_to(1 / 60)
    assert frame.shape == (64, 3) and run.fader.error is None and frame.max() > 0.0
    values = run.control.values()
    assert values["layers.base.fold.sides"] == 5 and "layers.glint.w.speed" in values
    assert run.deck.current == "program"
