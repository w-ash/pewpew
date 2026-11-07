"""Hosting effect programs: the op registry, a program in a `Renderer`
(binding, hot reload, the nodes' knobs and buffers, errors), pattern nodes,
and programs in the layer stack (below, masks, controls by address)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np
import pytest

from fakes import Solid, frames, hosted, stack
from pewpew import Float, Pattern, Renderer, grid, line, render_sequence
from pewpew.classinfo import pattern_name
from pewpew.compose import (
    Compositor,
    Layer,
    LayerError,
    Resolved,
    layer_seed,
    pattern_layer,
    pattern_node,
    pattern_program,
)
from pewpew.errors import blamed
from pewpew.features import FakeFeatures
from pewpew.fx.expr import noise, osc, pattern, shape
from pewpew.fx.graph import Graph, Node, Program
from pewpew.fx.host import ProgramPattern
from pewpew.fx.op import REGISTRY, RESERVED_ARGS, BindCtx, FrameCtx, Op, node_key, node_seed
from pewpew.fx.types import Coords, Fn, Port, Sig, Ty
from pewpew.mapping import Grouping
from pewpew.patterns import Comet, Fire, Geq, Plasma, Sdf3d, Wash, Wave

FPS = 60.0




@pytest.fixture(autouse=True)
def registry() -> Iterator[None]:
    """An op a test defines leaves the registry when the test ends."""
    before = dict(REGISTRY)
    yield
    REGISTRY.clear()
    REGISTRY.update(before)


@pytest.fixture
def counter() -> type[Op]:
    """A test op with state: it counts frames in a buffer, one per point."""

    class Count(Op, op="count_test"):
        """Counts the frames it has run, at every point."""

        sig = Sig.SOURCE
        out = Ty.SCALAR
        stateful = True
        warpable = False
        step_ = Float(1.0, 0.0, 10.0)

        def setup(self, ctx: BindCtx) -> None:
            self.frames = ctx.buffer("frames", ctx.n)

        def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
            self.frames += np.float32(self.step_)

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: self.frames * np.float32(0.01)

    return Count


# ---- the registry ------------------------------------------------------------------


@pytest.mark.parametrize("name", ["out", "cost", "dims", "inputs", "examples", "build", "phases", "ctx"])
def test_an_arg_named_after_what_every_op_has_is_refused(name: str) -> None:
    body: dict[str, object] = {"build": lambda self, inputs: None}
    body[name] = Float(0.5, 0.0, 1.0)
    with pytest.raises(ValueError, match=f"{name!r} is a class attribute every op has"):
        type("Bad", (Op,), body)
    assert {"op", "sig", "out", "cost", "dims", "stateful", "warpable", "examples"} <= RESERVED_ARGS


def test_one_class_re_registers_and_another_under_its_name_is_refused() -> None:
    def make() -> type[Op]:
        class Again(Op, op="again_test"):
            sig = Sig.SOURCE
            out = Ty.SCALAR

            def build(self, inputs: Sequence[Fn]) -> Fn:
                return lambda c: c.x

        return Again

    first, second = make(), make()  # a hot reload: the same module and qualified name
    assert REGISTRY["again_test"] is second and first is not second
    with pytest.raises(ValueError, match="op 'again_test' is already registered by"):
        type("Other", (Op,), {"build": lambda self, inputs: None}, op="again_test")


# ---- a program in a renderer -------------------------------------------------------------


def test_a_program_class_renders_and_names_its_knobs_by_address() -> None:
    class Tide(ProgramPattern):
        program = osc(8, 0.1).id("waves").modulate(noise(3, 0.1), 0.2).palette("ember").id("tint")

    renderer = Renderer(Tide(), grid(6, 6), name="layers.base")
    assert frames(renderer, 3).dtype == np.float32
    assert [p.owner for p in renderer.pattern.node_params.values()] == [  # type: ignore[attr-defined]
        "layers.base.waves", "layers.base.noise", "layers.base.modulate", "layers.base.tint",
    ]
    bare = Renderer(Tide(), grid(6, 6))
    assert bare.pattern.node_params["waves"].owner == "tide.waves"  # type: ignore[attr-defined]
    assert render_sequence(Tide, grid(6, 6), frames=3).shape == (3, 36, 3)


def test_a_node_that_raises_is_named_on_the_status_line(counter: type[Op],
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(self: Op, inputs: Sequence[Fn]) -> Fn:
        def node(c: Coords) -> np.ndarray:
            raise ZeroDivisionError("bad step")

        return node

    monkeypatch.setattr(counter, "build", broken)
    renderer = hosted(Program(Graph((Node("n", "count_test"), Node("tint", "palette", {}, ("n",)))), "tint"))
    frame = renderer.advance_to(1 / FPS)
    error = renderer.error
    assert error is not None and frame[:, 0].min() > 0.0  # the pulsing-red frame
    assert error.path == "layers.base.n" and error.pattern == "layers.base"
    assert str(error) == "layers.base.render raised: ZeroDivisionError: bad step (in node layers.base.n (count_test))"


def test_a_program_the_map_cannot_take_does_not_bind() -> None:
    with pytest.raises(ValueError, match="kaleid needs a map of 2 or 3 dimensions, and this map has 1"):
        hosted(osc(8).kaleid(5).program(), line(8))


def test_a_node_whose_build_raises_is_named(counter: type[Op], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(self: Op, inputs: Sequence[Fn]) -> Fn:
        raise KeyError("x")

    monkeypatch.setattr(counter, "build", broken)
    program = Program(Graph((Node("n", "count_test"), Node("tint", "palette", {}, ("n",)))), "tint")
    with pytest.raises(KeyError) as raised:
        hosted(program)
    assert blamed(raised.value) == "layers.base.n"
    assert raised.value.__notes__ == ["in node layers.base.n (count_test)"]


def test_strict_mode_names_a_node_that_gives_float64(counter: type[Op], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ProgramPattern, "strict", True)
    monkeypatch.setattr(counter, "build", lambda self, inputs: lambda c: self.frames.astype(np.float64))
    renderer = hosted(Program(Graph((Node("n", "count_test"),)), "n"))
    renderer.advance_to(1 / FPS)
    assert renderer.error is not None and renderer.error.path == "layers.base.n"
    assert "float32 field, got float64" in str(renderer.error)


def test_each_node_draws_its_own_stream_per_tick_with_the_seed_in_its_key() -> None:
    key = node_key(layer_seed(7, "base"), "base", "fx")
    assert key >> 32 == layer_seed(7, "base") and key & 0xFFFFFFFF != 0
    assert node_key(layer_seed(8, "base"), "base", "fx") != key
    ctx = lambda tick: FrameCtx(1 / FPS, None, tick, key)  # type: ignore[arg-type]
    a, b = (ctx(tick).rng().random(64) for tick in (5, 6))
    assert np.array_equal(ctx(5).rng().random(64), a)
    for shift in range(1, 16):  # a stream that slid by whole blocks would repeat here
        assert not np.array_equal(a[shift:], b[: 64 - shift])
    assert node_seed(key) != node_seed(node_key(layer_seed(7, "base"), "base", "fy"))


def test_a_stateful_node_folds_what_it_reads_into_its_state_before_render() -> None:
    """`advance` gets the closures of the nodes it reads, so state such as
    a feedback field advances before render, which stays pure."""

    class Hold(Op, op="hold_test"):
        """Keeps the brightest value it has read at each point."""

        sig = Sig.SOURCE
        inputs = (Port("in", Ty.SCALAR),)
        out = Ty.SCALAR
        stateful = True
        warpable = False

        def setup(self, ctx: BindCtx) -> None:
            self.coords = ctx.coords
            self.peak = ctx.buffer("peak", ctx.n)

        def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
            np.maximum(self.peak, inputs[0](self.coords), out=self.peak)

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: self.peak

    renderer = hosted(Program(Graph((Node("waves", "osc", {"freq": 1.0, "sync": 1.0}),
                                     Node("peak", "hold_test", {}, ("waves",)))), "peak"))
    out = frames(renderer, 70)  # past one whole turn of the stripes
    assert np.all(np.diff(out[:, :, 0], axis=0) >= 0.0) and out[-1].min() > 0.99


# ---- hot reload ------------------------------------------------------------------------


def test_a_hot_reload_keeps_each_nodes_knobs_buffers_and_phases(counter: type[Op]) -> None:
    def program(freq: float) -> Program:
        return Program(Graph((Node("n", "count_test"), Node("waves", "osc", {"freq": freq, "sync": 0.5}),
                              Node("mix", "add", {}, ("n", "waves")))), "mix")

    old = hosted(program(8.0))
    knobs = old.pattern.node_params  # type: ignore[attr-defined]
    waves, count = knobs["waves"], knobs["n"]
    count.set("step_", 2.0)
    frames(old, 3)
    phase = old.pattern._nodes["waves"].op.phase("sync")  # type: ignore[attr-defined]
    report = old.swap(ProgramPattern.of(program(12.0))())
    assert "n__frames" in report.buffers and "tick" in report.scalars
    new = old.pattern
    assert new.node_params["waves"] is waves and new.node_params["n"] is count  # type: ignore[attr-defined]
    assert waves["freq"] == 12.0, "a literal the operator did not move takes the new program's"
    assert count["step_"] == 2.0, "a value the operator moved stays"
    assert new._nodes["waves"].op.phase("sync") == phase  # type: ignore[attr-defined]
    np.testing.assert_array_equal(new.n__frames, np.full(16, 6.0, np.float32))  # type: ignore[attr-defined]
    count.set("step_", 3.0)  # the set still reaches the running op
    frames(old, 1)
    np.testing.assert_array_equal(new.n__frames, np.full(16, 9.0, np.float32))  # type: ignore[attr-defined]


def test_a_reload_whose_program_does_not_bind_leaves_the_running_one(counter: type[Op]) -> None:
    good = Program(Graph((Node("n", "count_test"),)), "n")
    renderer = hosted(good)
    count = renderer.pattern.node_params["n"]  # type: ignore[attr-defined]
    running = renderer.pattern
    with pytest.raises(ValueError, match="kaleid needs a map"):
        renderer.swap(ProgramPattern.of(Program(Graph((Node("n", "count_test"), Node("k", "kaleid", {}, ("n",)))),
                                                "k"))())
    assert renderer.pattern is running and count.bound.target is running._nodes["n"].op  # type: ignore[attr-defined]
    count.set("step_", 4.0)
    frames(renderer, 1)
    np.testing.assert_array_equal(running.n__frames, np.full(16, 4.0, np.float32))  # type: ignore[attr-defined]


def test_set_reload_set_through_the_stack_keeps_the_knob_and_its_value() -> None:
    """ADR-022: a control holds a node's knobs across a hot reload, so the
    aura's identity check lets the second set through."""

    class Tide(ProgramPattern):
        program = osc(8).id("waves").palette("ember").id("tint")

    comp = Compositor([Resolved(pattern_layer("base", "tide.py", node="tide"), Tide, "tide")], grid(4, 4))
    controls = comp.controls
    knob = controls.find("layers.base.waves.freq")
    assert knob is not None and controls.set("layers.base.waves.freq", 9.0)
    comp.advance_to(1 / FPS)

    class Tide2(ProgramPattern):  # the saved file: one more node
        program = osc(8).id("waves").kaleid(5).id("fold").palette("ember").id("tint")

    comp.swap("base", Tide2())
    again = comp.controls.find("layers.base.waves.freq")
    assert again is not None and again.params is knob.params
    assert comp.controls.snapshot_json()["layers.base.waves.freq"] == 9.0
    assert comp.controls.set("layers.base.fold.sides", 7)
    assert comp.controls.set("layers.base.waves.freq", 10.0)
    with pytest.raises(ValueError, match="takes a restart"):
        comp.swap("base", Solid())


# ---- pattern nodes ----------------------------------------------------------------------


@pytest.mark.parametrize("cls, mapping", [(Plasma, line(32)), (Comet, line(32)), (Geq, grid(8, 8)),
                                          (Fire, grid(8, 8)), (Wave, grid(8, 8)), (Wash, grid(8, 8)),
                                          (Sdf3d, grid(6, 6))])
def test_a_pattern_node_renders_its_pattern_byte_for_byte(cls: type[Pattern], mapping: np.ndarray) -> None:
    """A program of one pattern node is the pattern, seeded by the node's
    own key, whatever hosts it."""
    seed = layer_seed(3, "base")
    name = pattern_name(cls)
    program = ProgramPattern.of(pattern_program(name, name), {name: cls})
    alone = render_sequence(cls, mapping, seed=node_seed(node_key(seed, "base", name)), frames=20,
                            features=FakeFeatures(seed))
    np.testing.assert_array_equal(frames(Renderer(program(), mapping, seed=seed, name="layers.base"), 20), alone)


def test_a_pattern_node_takes_its_patterns_knobs_and_warps_when_warpable() -> None:
    renderer = hosted(pattern("plasma", speed=0.3).id("p").kaleid(5), grid(6, 6))
    knobs = renderer.pattern.node_params["p"]  # type: ignore[attr-defined]
    assert knobs.owner == "layers.base.p" and knobs["speed"] == 0.3
    assert type(knobs.bound.target) is Plasma
    assert frames(renderer, 3).dtype == np.float32


@pytest.mark.parametrize("n", [16, 24])
def test_a_rebind_starts_a_pattern_node_from_zeroed_pixels(n: int) -> None:
    """A pattern node's last frame is a buffer like any other: a rebind,
    to any number of pixels, zeroes it (pewpew.render)."""
    renderer = hosted(pattern("comet").id("c").hue(30))
    frames(renderer, 10)
    renderer.rebind(line(n))
    op = renderer.pattern._nodes["c"].op  # type: ignore[attr-defined]
    assert op.last is None and not op.inner.pixels.any()
    assert frames(renderer, 2).shape == (2, n, 3) and renderer.error is None


def test_the_pattern_rules_of_a_program() -> None:
    with pytest.raises(ValueError, match="pattern 'solid' is not warpable; apply mirror to another source"):
        pattern(Solid).mirror().program()
    assert pattern(Solid).mult(shape(0, 0.3)).program() is not None  # no warp, no rule
    with pytest.raises(ValueError, match="renders once per fixture, not at the program's points"):
        pattern("pulse").mult(osc(2)).program()

    class Inner(ProgramPattern):
        program = osc(2)

    with pytest.raises(ValueError, match="is a program; run it on a layer of its own"):
        pattern(Inner).mult(osc(2)).program()


def test_a_program_class_of_one_pattern_node_renders_it_at_the_programs_points() -> None:
    """A pattern-only layer runs its pattern in the layer's own renderer, at
    its own units; a program class hosts it at the program's points, so the
    rule of a pattern inside a program holds for one node too."""

    class Pulsing(ProgramPattern):
        program = pattern("pulse")

    with pytest.raises(ValueError, match="pattern 'pulse' renders once per fixture, not at the program's points"):
        hosted(Pulsing, grid(4, 4))


# ---- in the layer stack -------------------------------------------------------------------


def program_layer(lid: str, source: object, **mix: object) -> tuple[Layer, type[Pattern]]:
    program = Program.of(source)  # type: ignore[arg-type]
    return Layer(lid, program, **mix), ProgramPattern.of(program, {"solid": Solid})  # type: ignore[arg-type]


def test_a_program_reads_the_layers_below_it() -> None:
    from pewpew.fx.expr import below

    red = (pattern_layer("base", "solid"), Solid)
    comp = stack(red, program_layer("tint", below().hue(120)))
    frame = comp.advance_to(1 / FPS)
    assert frame[0, 1] > frame[0, 0], "red turned toward green"
    assert stack(program_layer("alone", below().hue(120))).advance_to(1 / FPS).max() == 0.0, "nothing is below"


def test_a_program_that_reads_below_is_refused_per_fixture_at_build_and_at_reload() -> None:
    """The frame below has one row per pixel, so a program that reads it
    cannot render per fixture: a build refuses it, and so does a hot reload
    that adds below(), with the running program kept."""
    from pewpew.fx.expr import below

    mapping = grid(4, 4)
    grouping = Grouping(np.asarray(grid(2, 2), np.float32), np.repeat(np.arange(4), 4))

    def fixture_stack(source: object) -> Compositor:
        layer, cls = program_layer("base", source)
        return Compositor([Resolved(layer, cls, "base")], mapping, grouping=grouping, units="fixture")

    with pytest.raises(LayerError, match="a program that reads below\\(\\) runs per pixel"):
        fixture_stack(below().hue(30))
    comp = fixture_stack(osc(3).palette("ember"))
    reads_below = ProgramPattern.of(Program.of(below().hue(30)))
    with pytest.raises(ValueError, match="a program that reads below\\(\\) runs per pixel"):
        comp.swap("base", reads_below())
    comp.advance_to(1 / FPS)
    assert comp.error is None


def test_a_programs_mask_weights_its_layer_per_pixel() -> None:
    ramp = osc(1, 0.0).id("ramp")  # red Solid shows as much as the ramp lets it
    masked = pattern(Solid).id("solid").program(alpha=ramp)
    comp = stack(program_layer("base", masked))
    frame = comp.advance_to(1 / FPS)
    expected = 0.5 + 0.5 * np.sin(np.linspace(0.0, 1.0, 8, dtype=np.float32) * np.float32(2 * np.pi))
    np.testing.assert_allclose(frame[:, 0], expected, atol=1e-6)
    assert comp.layer("base").masked


def test_a_mask_is_clipped_so_it_never_brightens_its_layer() -> None:
    raw = osc(1, 0.0).add(osc(1, 0.0))  # 0 to 2
    frame = stack(program_layer("base", pattern(Solid, red=0.5).program(alpha=raw))).advance_to(1 / FPS)
    wave = 0.5 + 0.5 * np.sin(np.linspace(0.0, 1.0, 8, dtype=np.float32) * np.float32(2 * np.pi))
    np.testing.assert_allclose(frame[:, 0], 0.5 * np.minimum(2 * wave, 1.0), atol=1e-6)


def test_a_mask_per_fixture_is_gathered_to_its_pixels() -> None:
    grouping = Grouping(np.asarray(grid(2, 2), np.float32), np.repeat(np.arange(4), 4))
    layer, cls = program_layer("base", pattern(Solid).program(alpha=noise(3, 0.0)))
    comp = Compositor([Resolved(layer, cls, "base")], grid(4, 4), grouping=grouping, units="fixture")
    red = comp.advance_to(1 / FPS)[:, 0].reshape(4, 4)  # a row per fixture
    assert comp.error is None
    np.testing.assert_array_equal(red, np.repeat(red[:, :1], 4, axis=1))  # one weight per fixture
    assert len(set(red[:, 0].tolist())) == 4


@pytest.mark.parametrize("gives", [lambda n: np.float32(0.5), lambda n: np.full(n - 1, 0.5, np.float32)])
def test_a_mask_of_the_wrong_shape_is_the_layers_error_not_the_auras(gives, monkeypatch: pytest.MonkeyPatch) -> None:
    """The compositor blends a mask after the renderer's containment, so the
    host refuses a wrong one inside it, as the aura runs: without the tests'
    check of every node."""
    monkeypatch.setattr(ProgramPattern, "strict", False)

    class Flat(Op, op="flatmask_test"):
        """A mask of the wrong shape."""

        sig = Sig.SOURCE
        out = Ty.SCALAR

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: gives(len(c.index))

    masked = Program(Graph((pattern_node("solid", "solid"), Node("m", "flatmask_test"))), "solid", "m")
    comp = stack(program_layer("base", masked))
    np.testing.assert_array_equal(comp.advance_to(1 / FPS), comp.error_frame(1 / FPS))
    assert comp.error is not None and "a mask is an (8,) float32 field" in str(comp.error)


def test_a_program_layers_state_and_snapshot_name_every_node() -> None:
    comp = stack(program_layer("base", osc(8).id("waves").palette("ember").id("tint")))
    assert comp.state()["layers"] == [{"id": "base", "nodes": [
        {"id": "waves", "op": "osc", "label": "Oscillator", "in": []},
        {"id": "tint", "op": "palette", "label": "Palette", "in": ["waves"]},
    ]}]
    comp.controls.set("layers.base.waves.freq", 3.0)
    snap = comp.snapshot().layers[0].program
    assert snap.graph["waves"].args["freq"] == 3.0 and snap.out == "tint"
    records = comp.controls.describe()
    assert [(r["name"], r["node"]) for r in records][:2] == [("layers.base.waves.freq", "waves"),
                                                             ("layers.base.waves.sync", "waves")]


def test_a_masked_layer_that_fails_draws_its_whole_error_frame(counter: type[Op],
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(counter, "build", lambda self, inputs: lambda c: 1 / 0)
    masked = Program(Graph((pattern_node("solid", "solid"), Node("n", "count_test"))), "solid", "n")
    comp = stack(program_layer("base", masked))
    assert comp.layer("base").masked
    np.testing.assert_array_equal(comp.advance_to(1 / FPS), comp.error_frame(1 / FPS))
