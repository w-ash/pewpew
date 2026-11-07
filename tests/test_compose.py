"""The layer stack: program values, blend modes, the stack's knobs, and the
compositor that renders a look's layers into one frame."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from fakes import build, frames, one_node, program_layer, rgb, stack
from pewpew.aura.book import LookBook
from pewpew.compose import Compositor, Controls, Layer, LayerControls, LayerError, Look, Route, layer_seed
from pewpew.crossfade import Crossfader
from pewpew.features import FakeFeatures, FeatureFrame, MemoFeatures
from pewpew.fx import expr
from pewpew.fx.blend import BLENDS, LIGHTS_BLACK, Blend
from pewpew.fx.expr import noise, osc, particles, ripple
from pewpew.fx.graph import RESERVED, Graph, Node, Program, as_id, check_id
from pewpew.fx.host import ProgramPattern
from pewpew.fx.op import BindCtx, Op
from pewpew.fx.types import Fn, Sig, Ty
from pewpew.mapping import grid, line
from pewpew.params import Int, declared_params
from pewpew.render import Renderer, SlotClock
from pewpew.testing.goldens import assert_matches_golden

GOLDEN = Path(__file__).parent / "goldens" / "compose.npz"

pytestmark = pytest.mark.usefixtures("fake_ops")


def solid(lid: str, args: dict | None = None, **mix: object) -> Layer:
    """A layer `lid` of one `solid_test` node, `solid`."""
    return Layer(lid, one_node("solid_test", args), **mix)  # type: ignore[arg-type]


def stepped(dts: list[float]) -> type[Op]:
    """Op `steps_test` (registered while `fake_ops` runs): black, and
    appends the dt of each frame it steps to `dts`."""

    class StepsTest(Op, op="steps_test"):
        sig = Sig.SOURCE
        out = Ty.RGB

        def step(self, dt: float) -> None:
            dts.append(dt)

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: np.zeros((len(c.index), 3), np.float32)

    return StepsTest


def needs() -> type[Op]:
    """Op `needs_test` (registered while `fake_ops` runs): `solid_test`
    whose bind raises on a map of other than `need` points (0: any)."""
    from pewpew.fx.ops import OPS

    class NeedsTest(OPS["solid_test"], op="needs_test"):
        need = Int(0, 0, 64)

        def setup(self, ctx: BindCtx) -> None:
            super().setup(ctx)
            if self.need and ctx.n != self.need:
                raise RuntimeError(f"binds {self.need} pixels only")

    return NeedsTest


# ---- program values ----------------------------------------------------------------


@pytest.mark.parametrize("value, problem", [
    ("comet", None),
    ("a" * 24, None),
    ("a" * 25, "bad node id"),
    ("Comet", "bad node id 'Comet': a lowercase letter"),
    ("2d", "bad node id '2d'"),
    ("my-wave", "bad node id"),
    (7, "bad node id 7"),
    ("blend", "bad node id 'blend': alpha, blend, enabled, nodes, opacity, out are reserved"),
])
def test_a_node_id_is_short_lowercase_and_not_a_layer_word(value, problem):
    reason = check_id(value)
    assert reason is None if problem is None else reason is not None and reason.startswith(problem)


def test_a_layer_id_may_be_a_word_a_node_id_may_not():
    """`layers.<layer>.opacity` is a mix knob, so no node may be named `opacity`."""
    assert check_id("out", "layer") is None and check_id("out") is not None
    assert declared_params(LayerControls).keys() <= RESERVED


def test_a_layers_blend_and_the_blend_ops_mode_are_one_choice():
    """One declaration of the blend modes and their labels (pewpew.fx.blend)."""
    from pewpew.fx.catalog import catalog
    from pewpew.fx.ops import OPS

    layer, op = LayerControls.blend.spec(), declared_params(OPS["blend"])["mode"].spec()
    assert layer["options"] == op["options"] == [{"value": b["name"], "label": b["label"]} for b in catalog()["blends"]]
    assert layer["default"] == op["default"] == Blend.NORMAL


@pytest.mark.parametrize("head", ["signals", "layers"])
def test_a_layer_is_never_named_for_an_addresss_head(head):
    """A look's signals draw their random streams as a layer named `signals`
    would (pewpew.compose.modulation), so no layer takes that name."""
    reason = check_id(head, "layer")
    assert reason == f"bad layer id {head!r}: layers and signals are reserved, as the heads of an address"
    assert check_id(head, "node") is None


@pytest.mark.parametrize("name, nid", [
    ("comet", "comet"), ("MyWave", "mywave"), ("my-wave.py", "my_wave_py"), ("2d", "p2d"), ("", "p"),
    ("blend", "blend_"), ("x" * 30, "x" * 24),
])
def test_a_name_becomes_a_node_id(name, nid):
    assert as_id(name) == nid and check_id(nid) is None


def test_a_graph_lists_each_node_after_the_nodes_it_reads():
    a, b = Node("a", "osc"), Node("b", "kaleid", {"sides": 5}, ("a",))
    graph = Graph((a, b))
    assert graph["b"] is b and "a" in graph and list(graph) == [a, b]
    with pytest.raises(ValueError, match="node 'b' reads 'a', which is not listed before it"):
        Graph((b, a))
    with pytest.raises(ValueError, match="node 'a' reads 'a', which is not listed before it"):
        Graph((Node("a", "fb", inputs=("a",)),))  # a cycle cannot be written down
    with pytest.raises(ValueError, match="node 'b' reads 'zz', which is not a node"):
        Graph((Node("b", "x", inputs=("zz",)),))
    with pytest.raises(ValueError, match="node 'a' is listed twice"):
        Graph((a, a))


def test_a_program_names_nodes_of_its_graph_and_its_args_are_read_only():
    node = Node("wave", "osc", {"speed": 1.0})
    program = Program(Graph((node,)), "wave")
    assert program.output is node and node.args == {"speed": 1.0}
    with pytest.raises(TypeError):
        node.args["speed"] = 2.0  # type: ignore[index]
    with pytest.raises(ValueError, match="out names 'x', which is not a node"):
        Program(Graph((node,)), "x")
    with pytest.raises(ValueError, match="alpha names 'm', which is not a node"):
        Program(Graph((node,)), "wave", "m")


def test_layer_and_look_values_refuse_what_cannot_run():
    wave = Program.of(osc())
    with pytest.raises(ValueError, match=r"layers.base.opacity must be within 0.0..1.0, got 1.5"):
        Layer("base", wave, opacity=1.5)
    with pytest.raises(ValueError, match=r"layers.base.blend takes one of 'normal', 'add', "):
        Layer("base", wave, blend="glow")
    with pytest.raises(ValueError, match="bad layer id 'Base'"):
        Layer("Base", wave)
    with pytest.raises(ValueError, match="a look has at least one layer"):
        Look(())
    with pytest.raises(ValueError, match="layer id 'a' is used more than once"):
        Look((Layer("a", wave), Layer("a", Program.of(noise()))))
    with pytest.raises(ValueError, match="a look's seed is a whole number of at least 0"):
        Look((Layer("a", wave),), seed=-1)
    with pytest.raises(ValueError, match="bad signal id"):
        Route("Breath", "layers.base.opacity", 0.2)
    with pytest.raises(ValueError, match="a route's depth is a finite number"):
        Route("breath", "layers.base.opacity", math.inf)
    base = (Layer("base", wave),)
    breath = Graph((Node("breath", "lfo"),))
    with pytest.raises(ValueError, match=r"routes\[0\]: unknown signal 'breth' \(did you mean 'breath'\?\)"):
        Look(base, breath, (Route("breth", "layers.base.opacity", 0.2),))
    with pytest.raises(ValueError, match="a look's front lists knob addresses, each once"):
        Look(base, front=("layers.base.opacity", "layers.base.opacity"))
    assert Look(base, signals=Graph(()), routes=[], front=[]) == Look(base)  # type: ignore[arg-type]  # lists too
    assert Layer("base", wave, opacity=1).opacity == 1.0 and type(Layer("b", wave).opacity) is float


def test_a_layer_seed_comes_from_the_look_seed_and_the_layer_id_alone():
    """SeedSequence over (seed, crc32(id)): stable across processes, apart
    per layer, never Python's hash()."""
    assert layer_seed(0, "base") == 3889957496
    assert len({layer_seed(s, lid) for s in (0, 1) for lid in ("base", "top")}) == 4


# ---- blend modes ---------------------------------------------------------------------

ACC = np.linspace(0.0, 1.0, 48, dtype=np.float32).reshape(16, 3)
SRC = np.abs(np.sin(np.arange(48, dtype=np.float32))).reshape(16, 3)
SRC[3] = 0.0  # a black pixel, for stencil


def blended(mode: str, weight: float, acc: np.ndarray = ACC) -> np.ndarray:
    out = acc.copy()
    BLENDS[mode](out, SRC, weight, np.empty_like(out))
    return out


def test_every_blend_matches_its_golden(regen_goldens):
    arrays = {f"{mode}_{w}": blended(mode, w) for mode in Blend for w in (1.0, 0.5, 0.25)}
    assert_matches_golden(GOLDEN, {**arrays, "stack": three_layer_frames()}, regen=regen_goldens)


@pytest.mark.parametrize("mode, want", [
    ("normal", SRC),
    ("add", ACC + SRC),
    ("screen", 1 - (1 - ACC) * (1 - SRC)),
    ("multiply", ACC * SRC),
    ("max", np.maximum(ACC, SRC)),
    ("min", np.minimum(ACC, SRC)),
    ("difference", np.abs(ACC - SRC)),
    ("subtract", ACC - SRC),
    ("stencil", np.where(SRC.max(axis=1, keepdims=True) > 0, SRC, ACC)),
    ("highlight", ACC + ACC * SRC),
])
def test_each_blend_at_full_weight_is_its_formula(mode, want):
    np.testing.assert_allclose(blended(mode, 1.0), want, atol=1e-6)


@pytest.mark.parametrize("weight", [1.0, 0.5])
def test_screen_reads_its_inputs_clipped_so_it_never_darkens(weight):
    """1 - (1 - a)(1 - b) darkens above 1: 1.6 over 1.6 would give 0.64 (ADR-021)."""
    over = np.full((4, 3), 1.6, dtype=np.float32)
    out = over.copy()
    BLENDS["screen"](out, over, weight, np.empty_like(out))
    np.testing.assert_array_equal(out, np.ones((4, 3), np.float32) + np.float32(0.6) * np.float32(1 - weight))
    below = np.full((4, 3), -0.5, dtype=np.float32)
    out = below.copy()
    BLENDS["screen"](out, below, weight, np.empty_like(out))
    np.testing.assert_array_equal(out, below * np.float32(1 - weight))  # moves toward 0, the clipped screen


@pytest.mark.parametrize("mode", list(Blend))
def test_a_blend_at_weight_0_leaves_the_frame_and_a_float64_weight_stays_float32(mode):
    np.testing.assert_array_equal(blended(mode, 0.0), ACC)
    for weight in (np.float64(0.3), 0.3, np.float32(0.3)):
        out = blended(mode, weight)  # type: ignore[arg-type]
        assert out.dtype == np.float32
        assert out.tobytes() == blended(mode, np.float32(0.3)).tobytes()  # type: ignore[arg-type]


# ---- the stack's knobs -------------------------------------------------------------------


def two_layers(**kw) -> Compositor:
    return stack(program_layer("base", noise(speed=0.5)), solid("top", blend="screen", opacity=0.5), **kw)


def test_the_knobs_are_named_by_address_in_display_order():
    controls = two_layers().controls
    names = [record["name"] for record in controls.describe()]
    assert names == [
        "layers.base.noise.scale", "layers.base.noise.speed", "layers.base.noise.octaves", "layers.base.noise.kind",
        "layers.base.opacity", "layers.base.blend", "layers.base.enabled",
        "layers.top.solid.red", "layers.top.solid.green", "layers.top.solid.blue",
        "layers.top.opacity", "layers.top.blend", "layers.top.enabled",
    ]
    where = {record["name"]: (record["layer"], record["node"]) for record in controls.describe()}
    assert where["layers.base.noise.speed"] == ("base", "noise") and where["layers.top.blend"] == ("top", "")
    records = {record["name"]: record for record in controls.describe()}
    assert records["layers.top.blend"]["kind"] == "choice" and "value" not in records["layers.top.blend"]
    values = controls.snapshot_json()
    assert values["layers.base.noise.speed"] == 0.5 and values["layers.top.blend"] == "screen"
    assert list(values) == names


def test_a_knob_is_parsed_and_set_through_its_set_and_refused_in_its_words():
    comp = two_layers()
    controls = comp.controls
    assert controls.parse("layers.base.noise.speed", 5.0) == (
        None, "layers.base.noise.speed must be within 0.0..2.0, got 5.0")
    for wrong in ("layers.base.noise.nosuch", "speed", "layers.base.speed", "layers.nosuch.noise.speed"):
        # Every address that names no knob gets every address, so the fix is in the list.
        reason = controls.parse(wrong, 1)[1]
        assert reason is not None and reason.startswith(f"unknown knob {wrong!r}")  # in a route's words
        assert "; knobs: layers.base.noise.scale, " in reason
    found, reason = controls.parse("layers.top.opacity", 0.25)
    assert reason is None and found is not None and found[0].params is comp.layer("top").mix.params
    assert controls.set("layers.top.opacity", 0.25) is True
    assert comp.layer("top").mix.opacity == 0.25
    assert controls.set("layers.base.noise.speed", 1.5)
    assert comp.layer("base").renderer.pattern.node_params["noise"]["speed"] == 1.5  # type: ignore[attr-defined]
    assert controls.find("layers.top.solid.red") == (comp.layer("top").host.node_params["solid"], "red", "")
    assert controls.find("layers.top.solid") is None
    with pytest.raises(ValueError, match="layers.top.blend takes one of"):
        controls.set("layers.top.blend", "glow")


def test_a_part_address_names_the_part_a_route_drives():
    """`layers.<lid>.<nid>.<arg>.<part>` (ADR-006) finds the color and its
    part, as `Bound.drive` takes it; a set takes the whole color."""
    comp = stack(Layer("base", one_node("zoo_test", node="zoo")))
    controls, params = comp.controls, comp.layer("base").host.node_params["zoo"]
    assert controls.find("layers.base.zoo.color.h") == (params, "color", "h")
    assert controls.find("layers.base.zoo.color.x") is None and controls.find("layers.base.zoo.level.h") is None
    assert controls.parse("layers.base.zoo.color.h", 10.0)[1] == (
        "layers.base.zoo.color.h is a part of layers.base.zoo.color; set layers.base.zoo.color as a whole")
    knob = controls.find("layers.base.zoo.color.h")
    assert knob is not None
    assert knob.params.bound is not None
    knob.params.bound.drive(f"{knob.name}.{knob.part}", 10.0)
    color = params["color"]
    hsv = {"h": color.h + 10.0, "s": color.s, "v": color.v}
    turned = stack(Layer("base", one_node("zoo_test", {"color": hsv}, node="zoo")))
    plain = stack(Layer("base", one_node("zoo_test", node="zoo")))
    assert comp.advance_to(1 / 60).tobytes() == turned.advance_to(1 / 60).tobytes()
    assert comp.advance_to(2 / 60).tobytes() != plain.advance_to(2 / 60).tobytes()


def test_layer_controls_drive_like_any_knob():
    """The mix is ordinary params, so modulation (ADR-006) reaches opacity."""
    mix = LayerControls("base", {"opacity": 0.5})
    mix.params.bound.drive("opacity", 0.75)  # type: ignore[union-attr]
    assert mix.opacity == 1.0 and mix.params["opacity"] == 0.5
    with pytest.raises(TypeError, match="cannot be modulated: it is a choice"):
        mix.params.bound.drive("blend", 1.0)  # type: ignore[union-attr]


# ---- the compositor -------------------------------------------------------------------------

IDENTITY = [
    ("particles", particles(), line(300), None), ("noise", noise(3).palette("ember"), line(64), None),
    ("ripple", ripple(), grid(8, 8), None), ("osc", osc(8, 0.2).palette("ocean"), None, "canopy"),
    ("particles", particles(), None, "canopy"),
]


@pytest.mark.parametrize("source, mapping, where", [row[1:] for row in IDENTITY],
                         ids=[f"{row[0]}-{row[3] or len(row[2])}" for row in IDENTITY])
def test_a_one_layer_stack_is_its_renderer_byte_for_byte(source, mapping, where, example):
    """The identity path: the layer's frame untouched, its seed derived."""
    if where == "canopy":
        mapping = example.mapping
    lid = "base"
    program = Program.of(source)
    comp = Compositor([Layer(lid, program)], mapping, seed=5, features=FakeFeatures(5))
    alone = Renderer(ProgramPattern.of(program)(), mapping, seed=layer_seed(5, lid), features=FakeFeatures(5),
                     name=f"layers.{lid}")
    assert frames(comp).tobytes() == frames(alone).tobytes()


def test_the_seed_a_layer_draws_is_its_own_whatever_else_runs():
    """Adding a layer above never changes the picture of the one below."""
    alone = stack(program_layer("base", particles()), mapping=line(64), seed=3)
    under = stack(program_layer("base", particles()), program_layer("top", particles(), opacity=0.0),
                  mapping=line(64), seed=3)
    renders = [frames(alone, 20), frames(under, 20)]
    assert renders[0].tobytes() == renders[1].tobytes()
    other = stack(program_layer("other", particles()), mapping=line(64), seed=3)
    assert frames(other, 20).tobytes() != renders[0].tobytes()


def test_a_stack_clamps_once_and_the_identity_path_never():
    class BrightTest(Op, op="bright_test"):
        """Above 1 everywhere: what an unclamped frame looks like."""

        sig = Sig.SOURCE
        out = Ty.RGB

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: np.full((len(c.index), 3), 1.6, dtype=np.float32)

    one = stack(Layer("base", one_node(BrightTest.op)))
    assert np.all(one.advance_to(1 / 60) == np.float32(1.6))  # the sinks clip it
    added = stack(solid("base", {"red": 0.8}), solid("top", {"red": 0.8}, blend="add"))
    np.testing.assert_array_equal(added.advance_to(1 / 60), [[1.0, 0.0, 0.0]] * 8)
    half = stack(Layer("base", one_node(BrightTest.op), opacity=0.5))  # not the identity: blended, clamped
    np.testing.assert_array_equal(half.advance_to(1 / 60), np.full((8, 3), 0.8, np.float32))


def test_a_disabled_layer_is_not_advanced_and_opacity_0_draws_nothing():
    comp = stack(solid("base", {"red": 0.2}), Layer("top", one_node("ramp_test"), enabled=False))
    np.testing.assert_array_equal(comp.advance_to(1 / 60), rgb(0.2, 0.0, 0.0, 8))
    assert comp.layer("top").renderer.t == 0.0 and comp.t == 1 / 60
    comp.controls.set("layers.top.enabled", True)
    comp.controls.set("layers.top.opacity", 0.0)
    np.testing.assert_array_equal(comp.advance_to(2 / 60), rgb(0.2, 0.0, 0.0, 8))
    assert comp.layer("top").renderer.t == 2 / 60
    comp.controls.set("layers.base.enabled", False)
    comp.controls.set("layers.top.enabled", False)
    assert not comp.advance_to(3 / 60).any()  # nothing on: black


def test_a_layer_enabled_again_takes_one_slot_as_its_first_dt():
    """The time it was off, given as one dt, would ignite every pixel of sparkle (ADR-021)."""
    steps: list[float] = []
    stepped(steps)
    comp = stack(solid("base"), Layer("top", one_node("steps_test"), blend="add"))
    clock = SlotClock(60.0)
    for _ in range(4):
        comp.advance_to(clock.advance())
    comp.controls.set("layers.top.enabled", False)
    for _ in range(595):
        comp.advance_to(clock.advance())
    comp.controls.set("layers.top.enabled", True)
    comp.advance_to(clock.advance())
    top = comp.layer("top").renderer
    assert steps[-1] == pytest.approx(1 / 60) and top.t == comp.t
    steps.clear()
    spawned = Compositor([Layer("top", one_node("steps_test"), enabled=False)], line(8), t=1.0)
    spawned.advance_to(2.0)
    spawned.controls.set("layers.top.enabled", True)
    spawned.advance_to(2.5)
    assert steps == [0.5]  # spawned off: one slot too
    with pytest.raises(ValueError, match="time never goes backwards"):
        top.resume_at(0.0)


def lit(frame: np.ndarray) -> float:
    return float((frame.max(axis=1) > 0.5).mean())


def test_particles_enabled_again_light_their_usual_share():
    """The backlog's acceptance: sparks on line(300), off for 10 s, light about their usual share."""
    dark = solid("base", {"red": 0.0})
    sparks = program_layer("sparks", particles(), blend="screen")
    comp, fresh = stack(dark, sparks, mapping=line(300)), stack(dark, sparks, mapping=line(300))
    clock = SlotClock(60.0)
    usual = [lit(fresh.advance_to(clock.advance())) for _ in range(60)][-1]
    clock = SlotClock(60.0)
    comp.advance_to(clock.advance())
    comp.controls.set("layers.sparks.enabled", False)
    for _ in range(600):
        comp.advance_to(clock.advance())
    comp.controls.set("layers.sparks.enabled", True)
    back = lit(comp.advance_to(clock.advance()))
    assert back < 0.5 and back <= usual + 0.1


def test_each_layer_reads_one_feature_frame_per_slot():
    calls: list[float] = []

    class Counted(FakeFeatures):
        def at(self, t: float) -> FeatureFrame:
            calls.append(t)
            return super().at(t)

    comp = stack(*(program_layer(lid, osc(4, 0.2), blend="add") for lid in ("a", "b", "c")),
                 features=Counted(0))
    frames(comp, 5)
    assert len(calls) == len(set(calls)) == 5
    memo = MemoFeatures(Counted(0))
    assert memo.at(0.5) is memo.at(0.5) and memo.at(0.6) is not memo.at(0.5)


GREEN = {"red": 0.0, "green": 1.0}


def test_a_raising_layer_draws_its_error_frame_in_its_place():
    comp = stack(solid("base", GREEN), Layer("top", one_node("raises_test"), blend="add"))
    frame = comp.advance_to(0.3)
    np.testing.assert_array_equal(frame, comp.error_frame(0.3) + np.array([0.0, 1.0, 0.0], np.float32))
    assert comp.error is not None and comp.error.pattern == "layers.top"
    assert str(comp.error).startswith(
        "layers.top.render raised: RuntimeError: broken render (in node layers.top.raises (raises_test))")
    comp.controls.set("layers.top.enabled", False)
    assert comp.error is None  # a layer that is off reports nothing


def test_an_unattended_run_leaves_a_failing_layer_out_until_none_is_left():
    comp = stack(solid("base", GREEN), Layer("top", one_node("raises_test"), blend="add"), bypass=True)
    np.testing.assert_array_equal(comp.advance_to(0.25), [[0.0, 1.0, 0.0]] * 8)
    assert comp.error is not None and comp.error.pattern == "layers.top"  # the status still names it
    comp.controls.set("layers.base.enabled", False)
    np.testing.assert_array_equal(comp.advance_to(0.5), comp.error_frame(0.5))  # the failure, not black
    alone = stack(Layer("base", one_node("raises_test")), bypass=True)
    np.testing.assert_array_equal(alone.advance_to(0.25), alone.error_frame(0.25))


@pytest.mark.parametrize("mode", sorted(set(Blend) - LIGHTS_BLACK))
def test_an_unattended_run_draws_the_failure_when_only_a_blend_that_stays_dark_is_left(mode):
    """A healthy multiply over a bypassed base is black: a dark look, not a failure (ADR-021)."""
    comp = stack(Layer("base", one_node("raises_test")),
                 solid("top", {"red": 1.0, "green": 1.0, "blue": 1.0}, blend=mode), bypass=True)
    np.testing.assert_array_equal(comp.advance_to(0.25), comp.error_frame(0.25))
    alone = stack(solid("base", blend=mode), bypass=True)
    assert not alone.advance_to(0.25).any()  # nothing failed: black, the look as written


def test_an_unattended_run_draws_the_failure_when_the_only_layer_left_is_at_opacity_0():
    """A layer at opacity 0 lights nothing, so it leaves the room dark (ADR-021)."""
    white = {"red": 1.0, "green": 1.0, "blue": 1.0}
    comp = stack(Layer("base", one_node("raises_test")), solid("top", white, blend="add", opacity=0.0), bypass=True)
    np.testing.assert_array_equal(comp.advance_to(0.25), comp.error_frame(0.25))
    comp.controls.set("layers.top.opacity", 0.5)
    np.testing.assert_array_equal(comp.advance_to(0.5), [[0.5, 0.5, 0.5]] * 8)  # the survivor lights the room


@pytest.mark.parametrize("mode", sorted(LIGHTS_BLACK))
def test_a_blend_that_lights_black_draws_over_nothing(mode):
    out = np.zeros_like(SRC)
    BLENDS[mode](out, SRC, 1.0, np.empty_like(out))
    assert out.any()


def test_a_layer_left_unbound_draws_its_error_frame_and_logs_once(caplog):
    needs()
    comp = stack(solid("base", GREEN), Layer("top", one_node("needs_test", {"need": 8}), blend="add"))
    with pytest.raises(RuntimeError, match="binds 8 pixels only"):
        comp.rebind(line(6))
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        for t in (0.25, 0.5):
            frame = comp.advance_to(t)
    assert frame.shape == (6, 3) and caplog.text.count("layer top is not bound") == 1
    comp.rebind(line(8))
    np.testing.assert_array_equal(comp.advance_to(0.75), [[1.0, 1.0, 0.0]] * 8)  # solid red on green


def test_a_rebind_whose_rollback_fails_too_leaves_no_layer_on_another_map():
    """A room reload (pewpew.room.live) binds the new map, and on a failure
    the old one again. Every layer tries both, so each ends on the old map
    or unbound, and the blend still renders."""
    needs()
    comp = stack(Layer("a", one_node("needs_test", node="needs")),
                 solid("m", {"red": 0.0, "blue": 1.0}, blend="add"),
                 Layer("b", one_node("needs_test", GREEN, node="needs"), blend="add"))
    comp.controls.set("layers.a.needs.need", 6)  # a live set runs no setup
    comp.controls.set("layers.b.needs.need", 8)
    with pytest.raises(RuntimeError, match="binds 8 pixels only"):
        comp.rebind(line(6))
    with pytest.raises(RuntimeError, match="binds 6 pixels only"):
        comp.rebind(line(8))  # the rollback
    frame = Crossfader(comp).advance_to(0.25)
    np.testing.assert_array_equal(frame, comp.error_frame(0.25) + np.array([0.0, 1.0, 1.0], np.float32))


def test_a_layer_that_cannot_be_built_is_named():
    needs()
    with pytest.raises(LayerError, match=r"^layers.top: RuntimeError: binds 4 pixels only") as err:
        stack(solid("base"), Layer("top", one_node("needs_test", {"need": 4})))
    assert err.value.layer == "top"


def test_the_stack_is_a_look_again_at_its_live_values():
    look = Look((program_layer("base", noise(speed=0.5)), solid("top", blend="screen")), seed=4)
    comp = stack(*look.layers, seed=look.seed)
    comp.controls.set("layers.top.solid.red", 0.25)
    comp.controls.set("layers.top.opacity", 0.75)
    snap = comp.snapshot()
    assert snap.seed == 4 and [layer.id for layer in snap.layers] == ["base", "top"]
    top = snap.layers[1].program.output
    assert (top.op, top.args) == ("solid_test", {"red": 0.25, "green": 0.0, "blue": 0.0})
    assert (snap.layers[1].opacity, snap.layers[1].blend) == (0.75, "screen")
    assert comp.state() == {
        "layers": [{"id": "base", "nodes": [{"id": "noise", "op": "noise", "label": "Noise", "in": []}]},
                   {"id": "top", "nodes": [{"id": "solid", "op": "solid_test", "label": "Solid_test", "in": []}]}],
        "signals": [], "routes": [], "front": [], "dims": 1,
    }


def test_layer_timings_come_from_the_injected_clock_and_never_reach_a_frame():
    ticks = iter(range(100))
    timed = two_layers(now=lambda: float(next(ticks)))
    plain = two_layers()
    assert frames(timed, 3).tobytes() == frames(plain, 3).tobytes()
    assert timed.timings == {"base": 1.0, "top": 1.0} and plain.timings == {}


def test_a_crossfade_between_two_layered_looks_is_the_mean_at_its_midpoint():
    first = stack(solid("base", {"red": 1.0}), solid("top", {"red": 0.0, "blue": 1.0}, opacity=0.5))
    fader: Crossfader[Compositor] = Crossfader(first)
    second = first.spawn(Look((solid("x", {"red": 0.0, "green": 1.0}),), seed=1))
    fader.fade_to(second, 1.0)
    mid = fader.advance_to(0.5)
    np.testing.assert_array_equal(mid, [[0.25, 0.5, 0.25]] * 8)
    assert mid.dtype == np.float32
    np.testing.assert_array_equal(fader.advance_to(1.0), [[0.0, 1.0, 0.0]] * 8)
    assert not fader.fading and fader.current is second


def three_layer_frames() -> np.ndarray:
    """Noise under sparks (screen) and stripes (add, half): the stack golden."""
    comp = stack(program_layer("base", noise(3, 0.3).palette("ember")),
                 program_layer("trail", particles(), blend="screen", opacity=0.6),
                 program_layer("swell", osc(4, 0.2).palette("ocean"), blend="add", opacity=0.5),
                 mapping=line(32), seed=11)
    return frames(comp, 24)


def test_a_layered_render_is_byte_identical_twice():
    assert three_layer_frames().tobytes() == three_layer_frames().tobytes()


def test_run_runs_a_layer_with_a_seed_derived_from_its_id(tmp_path):
    """The visible change: a look's sparks under `run` draw the base layer's
    stream, not seed 0's."""
    path = tmp_path / "sparks.look.json"
    path.write_bytes(LookBook({"sparks": expr.look(expr.layer("base", particles()))}, "sparks").to_bytes())
    run = build(["run", str(path), "--map", "line:300", "--seed", "0"])
    live = run.fader.current
    assert [layer.id for layer in live.layers] == ["base"] and live.layer("base").renderer.seed == layer_seed(0, "base")
    got = frames(run.fader, 60)
    cls = ProgramPattern.of(Program.of(particles()))
    want = frames(Renderer(cls(), line(300), seed=layer_seed(0, "base"), name="layers.base"), 60)
    assert got.tobytes() == want.tobytes()
    assert want.tobytes() != frames(Renderer(cls(), line(300), seed=0, name="layers.base"), 60).tobytes()


def test_controls_are_one_value_replaced_whole():
    comp = two_layers()
    before = comp.controls
    comp.remove("top")
    comp.insert(solid("top"), 1)
    assert isinstance(comp.controls, Controls) and comp.controls is not before
    assert before.sections["layers.top.solid"].params is not comp.controls.sections["layers.top.solid"].params
