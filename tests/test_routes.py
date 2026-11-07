"""Routes and the modulation seat (ADR-021, ADR-022; ADR-006 amendment
"layered paths"): a look's signals run once a frame before its layers, and
each route moves its knob by depth times its signal, wrapped or clamped in
the knob's own units, while the knob's set keeps the operator's value. The
builder writes routes, the codec round-trips them, the lab checks,
explains and verifies them, and the aura sets a signal's knob like any
other."""

from __future__ import annotations

import json
import math
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fakes import FakeCatalog, LoopThread, Pooled, Solid, aura_rig, frames
from pewpew import grid, line
from pewpew.aura.book import LookBook, pattern_problems
from pewpew.compose import Compositor, Look, Resolved, Route, controls_of, pattern_layer
from pewpew.compose.modulation import signal_problems
from pewpew.fx.catalog import example
from pewpew.fx.codec import decode_look, encode_look, encode_node, to_python
from pewpew.fx.compile import signal_ops
from pewpew.fx.expr import band, beat, knob, layer, lfo, look, noise, osc, pattern, walk
from pewpew.fx.graph import Graph, Node
from pewpew.fx.host import ProgramPattern
from pewpew.fx.ops import OPS
from pewpew.fx.ops.signal import SignalOp
from pewpew.lab import check_look, explain
from pewpew.lab.check import ready
from pewpew.lab.geometry import parse_geometry
from pewpew.lab.rendering import play
from pewpew.lab.verify import Verification, verify_looks
from pewpew.params import Float, Int, declared_params
from pewpew.patterns import Plasma
from pewpew.render import error_frame
from pewpew.run import status_line
from test_fx_codec import value

FREQ = "layers.base.osc.freq"


def running(made: Look, mapping: np.ndarray | None = None) -> Compositor:
    """`made`'s stack, built as a recall builds it, on `mapping` (line(8))."""
    staged = ready(made)
    shown = staged.look
    return Compositor(staged.layers, line(8) if mapping is None else mapping, seed=shown.seed,
                      signals=shown.signals, routes=shown.routes, front=shown.front)


def live(stack: Compositor, path: str) -> Any:
    """What the pattern or op behind the knob at `path` reads now."""
    knob_ = stack.controls.find(path)
    assert knob_ is not None and knob_.params.bound is not None
    read = knob_.params.bound.value(knob_.name)
    return getattr(read, knob_.part) if knob_.part else read


def tint() -> Any:
    return osc(8).palette("ember")


# ---- the seat ------------------------------------------------------------------------


def test_a_route_moves_what_the_op_reads_and_the_set_keeps_the_operators_value() -> None:
    stack = running(look(layer("base", tint()), routes=[knob(1.0).to(FREQ, depth=4)]))
    frames(stack, 1)
    assert live(stack, FREQ) == 12.0
    assert stack.controls.snapshot_json()[FREQ] == 8.0, "a page and a save see the base"
    assert stack.mod() == {FREQ: 12.0}
    assert stack.snapshot().layers[0].program.graph["osc"].args["freq"] == 8.0


def test_at_the_seat_a_periodic_knob_wraps_another_clamps_and_an_int_rounds() -> None:
    made = look(layer("base", osc(30).kaleid(5).palette("ember", shift=300), opacity=0.8), routes=[
        (k := knob(1.0)).to("layers.base.palette.shift", depth=120), k.to("layers.base.opacity", depth=0.5),
        k.to(FREQ, depth=10), k.to("layers.base.kaleid.sides", depth=1.5),
    ])
    stack = running(made, grid(4, 4))
    frames(stack, 1)
    assert live(stack, "layers.base.palette.shift") == pytest.approx(60.0)
    assert (live(stack, "layers.base.opacity"), live(stack, FREQ)) == (1.0, 32.0)
    assert live(stack, "layers.base.kaleid.sides") == 7, "5 + 1.5 rounds half up"
    assert stack.mod()["layers.base.opacity"] == 1.0


def test_routes_into_one_knob_add_up() -> None:
    made = look(layer("base", tint()), routes=[knob(0.5).to(FREQ, depth=4), knob(1.0).to(FREQ, depth=2)])
    stack = running(made)
    frames(stack, 1)
    assert live(stack, FREQ) == 12.0 and [node.id for node in made.signals or ()] == ["knob", "knob2"]


def test_a_route_into_a_signal_moves_it_before_it_samples() -> None:
    """The signals run in graph order, each after the signals that drive
    it, so the knob's route turns the lfo a quarter cycle on the first
    frame, where the sine is at its top."""
    made = look(layer("base", tint()), routes=[
        lfo(0.0).to(FREQ, depth=2), knob(1.0).to("signals.lfo.offset", depth=0.25)])
    assert [node.id for node in made.signals or ()] == ["knob", "lfo"]
    stack = running(made)
    frames(stack, 1)
    assert live(stack, FREQ) == pytest.approx(10.0)


def test_a_raising_signal_holds_its_last_value_while_the_stack_renders_on(monkeypatch: pytest.MonkeyPatch) -> None:
    stack = running(look(layer("base", tint()), routes=[lfo(1.0).id("breath").to(FREQ, depth=2)]))
    frames(stack, 10)
    held = live(stack, FREQ)

    def boom(self: SignalOp, ctx: object, inputs: object) -> float:
        raise ZeroDivisionError("boom")

    with monkeypatch.context() as patch:
        patch.setattr(OPS["lfo"], "sample", boom)
        shown = frames(stack, 3)
        error = stack.error
        assert error is not None and error.path == "signals.breath"
        assert str(error).startswith("signals.breath.sample raised: ZeroDivisionError: boom")
        assert status_line(("render", stack))() == ("render", str(error), "signals.breath")
        assert live(stack, FREQ) == held
        assert not np.array_equal(shown[-1], error_frame(8, stack.t)), "the stack renders on"
        patch.setattr(OPS["lfo"], "sample", lambda self, ctx, inputs: math.nan)
        frames(stack, 1)
        assert "lfo gave nan; a signal gives a finite number each frame" in str(stack.error)
    frames(stack, 1)
    assert stack.error is None and live(stack, FREQ) != held


def test_the_state_gives_each_signal_its_range_a_smooth_its_inputs() -> None:
    """A page shows a route of a signal that swings both ways as ±, of a
    level as its own sign: the range says which."""
    made = look(layer("base", tint()), routes=[
        lfo(1.0).id("wave").smooth(0.5).to(FREQ, depth=2), band("bass").id("bass").smooth(0.5).to(FREQ, depth=-1)])
    ranges = {s["id"]: s["range"] for s in running(made).state()["signals"]}
    assert ranges == {"wave": [-1.0, 1.0], "smooth": [-1.0, 1.0], "bass": [0.0, 1.0], "smooth2": [0.0, 1.0]}


def test_a_route_whose_knob_is_gone_rests_and_the_stack_saves_without_it() -> None:
    """A pick replaces a layer's program: a route into the old program
    rests, a route into the layer's mix runs on, and a snapshot leaves out
    the resting route and the signal only it read, so the look checks. A
    front knob of the old program gives its place to the new one's first."""
    made = look(layer("base", tint()), front=[FREQ, "signals.macro.value"], routes=[
        lfo(1.0).id("breath").to(FREQ, depth=2), knob(1.0).id("macro").to("layers.base.opacity", depth=-0.5)])
    stack = running(made)
    stack.put(Resolved(pattern_layer("base", "plasma"), Plasma, "plasma"))
    frames(stack, 1)
    state = stack.state()
    assert state["routes"] == [{"source": "macro", "path": "layers.base.opacity", "depth": -0.5}]
    assert state["front"] == ["layers.base.plasma.speed", "signals.macro.value"]
    assert [s["id"] for s in state["signals"]] == ["breath", "macro"]
    assert live(stack, "layers.base.opacity") == 0.5 and set(stack.mod()) == {"layers.base.opacity"}
    saved = stack.snapshot()
    assert [node.id for node in saved.signals or ()] == ["macro"]
    assert saved.front == ("layers.base.plasma.speed", "signals.macro.value")
    assert check_look(saved).ok


def test_a_save_leaves_out_the_front_knobs_of_a_signal_it_leaves_out() -> None:
    made = look(layer("base", tint()), front=["signals.breath.rate"], routes=[
        lfo(1.0).id("breath").to(FREQ, depth=2)])
    stack = running(made)
    stack.put(Resolved(pattern_layer("base", "plasma"), Plasma, "plasma"))
    saved = stack.snapshot()
    assert (saved.signals, saved.routes, saved.front) == (None, (), ())
    assert check_look(saved).ok


def test_a_save_leaves_out_a_chain_of_signals_that_drives_only_what_is_gone() -> None:
    """A route into a signal left out goes too, and so does its signal: a
    save prunes until nothing more drops (pewpew.compose.modulation)."""
    made = look(layer("base", tint()), routes=[
        lfo(1.0).id("breath").to(FREQ, depth=2), knob(0.5).id("macro").to("signals.breath.rate", depth=0.5)])
    stack = running(made)
    stack.put(Resolved(pattern_layer("base", "plasma"), Plasma, "plasma"))
    saved = stack.snapshot()
    assert (saved.signals, saved.routes) == (None, ())
    assert check_look(saved).ok


class Narrow(Solid):
    """Solid, its red narrowed by a hot reload."""

    red = Float(0.25, 0.0, 0.5)


def test_a_route_rests_when_a_hot_reload_narrows_its_knob_below_its_depth() -> None:
    """As a set refuses a value past a knob's range, a route rests once its
    depth is past the knob's span, so the knob reads its own value and a
    save holds a look that recalls."""
    red = "layers.base.solid.red"
    stack = Compositor([Resolved(pattern_layer("base", "solid", {"red": 0.25}), Solid, "solid")], line(4),
                       signals=Graph((Node("k", "knob", {"value": 1.0}),)), routes=(Route("k", red, 0.9),))
    frames(stack, 1)
    assert live(stack, red) == pytest.approx(1.0)
    stack.swap("base", Narrow())
    frames(stack, 1)
    assert (stack.state()["routes"], stack.mod(), live(stack, red)) == ([], {}, 0.25)
    saved = stack.snapshot()
    assert (saved.signals, saved.routes) == (None, ())
    Compositor([Resolved(saved.layers[0], Narrow, "solid")], line(4), signals=saved.signals, routes=saved.routes)


def test_a_stack_leaves_out_a_front_path_that_names_no_knob_and_a_look_check_names_it() -> None:
    """`front` is layout only: a stale path never stops a look running,
    while the builder and the checks still teach it."""
    staged = ready(look(layer("base", tint())))
    stack = Compositor(staged.layers, line(8), front=("layers.base.osc.speed", FREQ, "layers.base.palette.hue"))
    assert stack.state()["front"] == [FREQ] and stack.snapshot().front == (FREQ,)
    with pytest.raises(ValueError, match=r"front\[0\]: unknown knob 'layers.base.osc.speed'"):
        look(layer("base", tint()), front=["layers.base.osc.speed"])


def test_a_pattern_file_that_is_a_program_has_its_knobs_where_its_stack_runs_them() -> None:
    """Its renderer is named by the layer, as any program's, so a check, a
    push and a route all name its nodes' knobs `layers.<layer>.<node>`."""
    prog = ProgramPattern.of(tint().program())
    made = Look((pattern_layer("base", "prog"),), Graph((Node("breath", "lfo"),)), (Route("breath", FREQ, 2.0),))
    resolved = Resolved(made.layers[0], prog, "prog")
    stack = Compositor([resolved], line(8), signals=made.signals, routes=made.routes)
    assert list(controls_of([resolved], made.signals).sections) == list(stack.controls.sections)
    assert pattern_problems(LookBook({"tide": made}), lambda spec: prog) == []
    frames(stack, 1)
    assert set(stack.mod()) == {FREQ}


def test_a_stack_refuses_a_route_that_reaches_no_knob_it_can_move() -> None:
    staged = ready(look(layer("base", tint())))
    signals = Graph((Node("breath", "lfo"),))
    for route, reason in [
        (Route("breath", "layers.base.osc.fre", 1.0),
         r"routes\[0\]: unknown knob 'layers.base.osc.fre' \(did you mean 'layers.base.osc.freq'\?\); knobs: "),
        (Route("breath", "layers.base.osc.axis", 1.0), r"routes\[0\]: layers.base.osc.axis cannot be modulated"),
        (Route("breath", FREQ, 40.0), r"routes\[0\]: depth must be within -31.5..31.5, got 40.0; a route moves "),
    ]:
        with pytest.raises(ValueError, match=reason):
            Compositor(staged.layers, line(8), signals=signals, routes=(route,))


def test_the_same_look_and_seed_give_the_same_bytes_and_the_seed_chooses_the_wander() -> None:
    made = look(layer("base", noise(3).palette("ocean", shift=walk(2.0))), routes=[
        band("bass").to("layers.base.noise.scale", depth=4), lfo(0.5).to("layers.base.palette.cycle", depth=0.2)])
    geometry = parse_geometry("grid:6x6")
    first, again = (play(ready(made), geometry, 30, 60.0, 0)[0] for _ in range(2))
    assert first.tobytes() == again.tobytes()
    reseeded = play(ready(Look(made.layers, made.signals, made.routes, seed=1)), geometry, 30, 60.0, 0)[0]
    assert not np.array_equal(first, reseeded)


def test_every_bit_of_the_seed_chooses_the_wander() -> None:
    """Signals key from a seed derived as a layer's is, so seeds 2**32
    apart wander apart, as their layers draw apart."""
    made = look(layer("base", tint()), routes=[walk(2.0).to(FREQ, depth=4)])
    low, high = running(made), running(replace(made, seed=2**32))
    frames(low, 30)
    frames(high, 30)
    assert live(low, FREQ) != live(high, FREQ)


# ---- the builder ---------------------------------------------------------------------


def test_a_signal_given_as_an_arg_sweeps_the_args_sweet_range() -> None:
    """The arg starts where the signal's 0 lands in the sweet range: its
    middle for a swing of -1 to 1, its bottom for a level of 0 to 1."""
    made = look(layer("base", osc(8, sync=lfo(0.1)).add(noise(scale=band().smooth())).palette("ember")))
    nodes = made.layers[0].program.graph
    assert (nodes["osc"].args["sync"], nodes["noise"].args["scale"]) == (0.0, 1.0)
    assert made.routes == (Route("lfo", "layers.base.osc.sync", 1.0), Route("smooth", "layers.base.noise.scale", 9.0))
    assert [node.id for node in made.signals or ()] == ["lfo", "band", "smooth"]


def test_the_builder_refuses_a_signal_where_it_cannot_go() -> None:
    with pytest.raises(ValueError, match=r'osc.sync is driven by a signal, and signals belong to a look: build it'):
        osc(8, sync=lfo(0.1)).program()
    with pytest.raises(TypeError, match="osc gives a field, not a signal; route a signal op"):
        osc(8).to(FREQ, 1.0)
    with pytest.raises(TypeError, match="osc.axis cannot be modulated: it is a choice"):
        osc(8, axis=lfo())  # type: ignore[arg-type]  # on purpose
    with pytest.raises(TypeError, match=r"wave.color cannot be modulated: drive one of the color's parts"):
        pattern("wave", color=lfo())
    with pytest.raises(ValueError, match=r"routes\[0\]: unknown knob 'layers.top.osc.freq'"):
        look(layer("base", tint()), routes=[lfo().to("layers.top.osc.freq", depth=1)])
    with pytest.raises(ValueError, match=r"^osc: unknown param 'synk'; params: freq, sync, offset, axis$"):
        osc(8, synk=lfo(0.1))  # type: ignore[call-arg]  # on purpose
    assert signal_problems(Graph((Node("a", "env"),)), None) == ["signals.a: env reads 1 signal(s) ('gate'), got 0"]


def test_the_builder_and_a_look_refuse_a_fade_master_or_cycle_their_params_refuse() -> None:
    reason = (r"^a look's fade must be within 0.0..600.0, got -5.0; a look's master must be within 0.0..1.0, "
              r"got 7.0; a look's cycle takes true or false, got 'yes'$")
    with pytest.raises(ValueError, match=reason):
        look(layer("base", tint()), fade=-5, master=7.0, cycle="yes")  # type: ignore[arg-type]  # on purpose
    with pytest.raises(ValueError, match=reason):
        Look(look(layer("base", tint())).layers, fade=-5, master=7.0, cycle="yes")  # type: ignore[arg-type]  # on purpose
    made = look(layer("base", tint()), fade=3, master=1)
    assert (made.fade, made.master) == (3.0, 1.0) and decode_look(encode_look(made)) == (made, [])


def test_one_signal_builder_is_one_signal_a_macro() -> None:
    macro = knob(0.5).id("macro")
    made = look(layer("base", tint()), routes=[macro.to(FREQ, depth=8), macro.to("layers.base.opacity", depth=-0.5)])
    assert [node.id for node in made.signals or ()] == ["macro"] and len(made.routes) == 2


# ---- the codec -----------------------------------------------------------------------

SIGNAL_OPS = signal_ops()
TARGETS = {FREQ: declared_params(OPS["osc"])["freq"],
           "layers.base.palette.shift": declared_params(OPS["palette"])["shift"],
           "layers.base.opacity": Float(1.0, 0.0, 1.0)}


def depth(draw: st.DrawFn, param: Float | Int) -> float:
    span = param.hi - param.lo
    return draw(st.floats(-span, span, allow_nan=False))


@st.composite
def looks(draw: st.DrawFn) -> Look:
    """A one-layer look of osc into palette with up to four signals, each
    reading an earlier one where its op reads a signal, each routed to a
    knob of the layer, and maybe driven by an earlier signal's route."""
    nodes: list[Node] = []
    routes: list[Route] = []
    for i in range(draw(st.integers(1, 4))):
        ops = [op for op in SIGNAL_OPS if len(OPS[op].inputs) <= len(nodes)]
        op = draw(st.sampled_from(ops))
        cls = OPS[op]
        inputs = tuple(draw(st.sampled_from([n.id for n in nodes])) for _ in cls.inputs)
        args = {name: draw(value(param)) for name, param in declared_params(cls).items() if draw(st.booleans())}
        nodes.append(Node(f"s{i}", op, args, inputs))
        path = draw(st.sampled_from(sorted(TARGETS)))
        routes.append(Route(f"s{i}", path, depth(draw, TARGETS[path])))
        knobs = {name: param for name, param in declared_params(cls).items() if isinstance(param, Float | Int)}
        if i and knobs and draw(st.booleans()):
            name = draw(st.sampled_from(sorted(knobs)))
            source = draw(st.sampled_from([n.id for n in nodes[:-1]]))
            routes.append(Route(source, f"signals.s{i}.{name}", depth(draw, knobs[name])))
    made = Look((layer_of(),), Graph(()), (), seed=draw(st.integers(0, 2**32)))
    ordered = decode_look({**encode_look(made), "signals": {n.id: encode_node(n) for n in nodes},
                           "routes": [r.to_json() for r in routes]})
    assert ordered[0] is not None, ordered[1]
    return ordered[0]


def layer_of() -> Any:
    return look(layer("base", tint())).layers[0]


@given(looks())
def test_a_look_with_signals_round_trips_through_json_and_the_builder_chain(made: Look) -> None:
    assert decode_look(json.loads(json.dumps(encode_look(made)))) == (made, [])
    assert example(to_python(made)) == made


def test_a_look_prints_as_the_builder_chain_that_makes_it() -> None:
    made = look(layer("base", osc(8, 0.1).palette("ember"), opacity=0.5), front=[FREQ], seed=7, routes=[
        (m := knob(0.5).id("macro")).to(FREQ, depth=4), m.to("layers.base.opacity", depth=-0.25),
        beat().env(0.01, 0.3).to("layers.base.palette.shift", depth=30)])
    assert to_python(made) == """look(
    layer("base", osc(8.0, 0.1).palette("ember"), opacity=0.5),
    routes=[
        (macro_ := knob(0.5).id("macro")).to("layers.base.osc.freq", depth=4.0),
        macro_.to("layers.base.opacity", depth=-0.25),
        beat().env(0.01, 0.3).to("layers.base.palette.shift", depth=30.0),
    ],
    seed=7,
    front=["layers.base.osc.freq"],
)"""
    assert example(to_python(made)) == made


def test_the_codec_puts_each_signal_after_the_signals_that_drive_it() -> None:
    doc = {**encode_look(look(layer("base", tint()))),
           "signals": {"wave": {"op": "lfo"}, "macro": {"op": "knob"}},
           "routes": [{"source": "wave", "path": FREQ, "depth": 2}, {"source": "macro",
                                                                     "path": "signals.wave.rate", "depth": 1}]}
    made, problems = decode_look(doc)
    assert problems == [] and made is not None and [node.id for node in made.signals or ()] == ["macro", "wave"]


# ---- the lab and the aura ----------------------------------------------------------------


def test_check_names_each_bad_route_by_its_path_and_code() -> None:
    doc = encode_look(look(layer("base", tint()), routes=[
        lfo().to(FREQ, depth=1), lfo().to("layers.base.opacity", depth=0.5), lfo().to(FREQ, depth=2)]))
    doc["routes"][0]["path"] = "layers.base.osc.fre"
    doc["routes"][1]["path"] = "layers.base.osc.axis"
    doc["routes"][2]["depth"] = 99
    found = {(p.path, p.code.value, p.did_you_mean, p.valid[:1]) for p in check_look(doc).problems}
    assert found == {
        ("routes[0].path", "bad-ref", FREQ, (FREQ,)), ("routes[1].path", "wrong-kind", None, ()),
        ("routes[2].depth", "out-of-range", None, ("-31.5..31.5",)),
    }
    doc["front"] = [FREQ, FREQ]
    assert [(p.path, p.reason) for p in check_look(doc).problems] == [
        ("front[1]", "front[1]: repeats front[0]; list each knob once")]
    checked = check_look(look(layer("base", tint()), routes=[lfo().to(FREQ, depth=1)]))
    assert checked.ok and checked.look_normalized is not None
    assert checked.look_normalized["signals"]["lfo"]["args"] == {"rate": 0.25, "shape": "sine", "offset": 0.0}


def test_explain_says_what_each_signal_gives_and_how_far_each_route_moves_its_knob() -> None:
    told = explain(look(layer("base", tint()), front=[FREQ], routes=[
        lfo(0.1).id("breath").to(FREQ, depth=2), knob(1.0).to("layers.base.palette.shift", depth=-30)]))
    assert "2 signals move 2 knobs each frame" in told.summary
    assert "A page shows layers.base.osc.freq first" in told.summary
    breath, macro = told.signals
    assert (breath.id, breath.op) == ("breath", "lfo") and breath.about.endswith("It gives -1 to 1.")
    assert breath.knobs[0] == "rate = 0.1 Hz (default 0.25; 0..10): Higher: what it moves swings faster"
    assert breath.routes == ("moves layers.base.osc.freq by up to ±2, either way from its value",)
    assert macro.routes == ("moves layers.base.palette.shift down by up to 30 ° from its value",)


def _verified() -> Verification:
    """`verify looks` of two looks on a 6x6 panel over 2 s: `strobe`, whose
    LFO turns its opacity down and up 8 times a second, and `faint`, whose
    LFO moves its knob too little to see."""
    strobe = look(layer("base", noise(3).palette("ember")), routes=[lfo(8, "square").to("layers.base.opacity",
                                                                                        depth=-1)])
    faint = look(layer("base", noise(3, 0.5).palette("ember")), routes=[
        lfo(0.5).id("faint").to("layers.base.palette.shift", depth=1e-4)])
    looks = {"strobe": encode_look(strobe), "faint": encode_look(faint)}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "mod.look.json"
        path.write_text(json.dumps({"version": 4, "looks": looks}))
        return verify_looks([path], map_spec="grid:6x6", seconds=2.0, fps=30.0)


# The verify run, on the suite's process pool (conftest.py).
JOBS = {"verified": _verified}


def test_verify_catches_a_fast_lfo_on_brightness_and_a_signal_knob_that_moves_nothing(pooled: Pooled) -> None:
    strobed, quiet = pooled["verified"].files[0].looks
    assert not strobed.ok and any("flashes up to" in failure for failure in strobed.failures)
    assert not quiet.ok and "signals.faint.rate" in quiet.dead


def test_the_aura_sets_a_signals_knob_and_reports_the_stack_and_its_live_values(tmp_path: Path) -> None:
    macro = Look((pattern_layer("base", "solid", {"red": 0.0}),), Graph((Node("macro", "knob"),)),
                 (Route("macro", "layers.base.solid.red", 1.0),), front=("signals.macro.value",))
    rig = aura_rig(Solid, catalog=FakeCatalog({"solid": Solid}), looks={"macro": macro}, current="macro",
                   path=tmp_path / "looks.json")
    assert rig.looks.restore() is None
    rig.frame(rig.clock.advance())
    assert rig.control.state()["stack"]["routes"] == [{"source": "macro", "path": "layers.base.solid.red",
                                                       "depth": 1.0}]
    assert rig.control.mod() == {"layers.base.solid.red": 0.0} and not rig.looks.changed()
    with LoopThread(rig.calls):
        assert rig.control.set("signals.macro.value", 0.75) is None
    rig.calls.drain()
    rig.frame(rig.clock.advance())
    assert rig.control.mod() == {"layers.base.solid.red": 0.75} and rig.control.values()["layers.base.solid.red"] == 0
    assert rig.looks.changed(), "a signal's knob is an edit"
    assert rig.control.set("signals.macro.value", 2) == "signals.macro.value must be within 0.0..1.0, got 2.0"
