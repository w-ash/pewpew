"""Running effect programs: the op registry, a program bound to a map in a
`Renderer` (binding, the nodes' knobs and buffers, errors), and programs
in the layer stack (below, masks, controls by address)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np
import pytest

from fakes import frames, hosted, one_node, program_layer, stack
from pewpew.compose import Layer, layer_seed
from pewpew.errors import blamed
from pewpew.fx.bound_program import BoundProgram
from pewpew.fx.expr import noise, osc
from pewpew.fx.graph import Graph, Node, Program
from pewpew.fx.op import REGISTRY, RESERVED_ARGS, BindCtx, FrameCtx, Op, node_key, node_seed
from pewpew.fx.types import Coords, Fn, Port, Sig, Ty
from pewpew.mapping import grid, line
from pewpew.params import Float
from pewpew.render import Renderer

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

    first, second = make(), make()  # a module imported again: the same module and qualified name
    assert REGISTRY["again_test"] is second and first is not second
    with pytest.raises(ValueError, match="op 'again_test' is already registered by"):
        type("Other", (Op,), {"build": lambda self, inputs: None}, op="again_test")


# ---- a program in a renderer -------------------------------------------------------------


def test_a_bound_program_renders_and_names_its_knobs_by_address() -> None:
    program = Program.of(osc(8, 0.1).id("waves").modulate(noise(3, 0.1), 0.2).palette("ember").id("tint"))
    renderer = Renderer(BoundProgram(program, "layers.base"), grid(6, 6))
    assert frames(renderer, 3).dtype == np.float32
    assert [p.owner for p in renderer.bound.node_params.values()] == [
        "layers.base.waves", "layers.base.noise", "layers.base.modulate", "layers.base.tint",
    ]
    assert frames(hosted(program, grid(6, 6), seed=1), 3).shape == (3, 36, 3)


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
    monkeypatch.setattr(BoundProgram, "strict", True)
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


# ---- in the layer stack -------------------------------------------------------------------


@pytest.mark.usefixtures("fake_ops")
def test_a_program_reads_the_layers_below_it() -> None:
    from pewpew.fx.expr import below

    comp = stack(Layer("base", one_node("solid_test")), program_layer("tint", below().hue(120)))
    frame = comp.advance_to(1 / FPS)
    assert frame[0, 1] > frame[0, 0], "red turned toward green"
    assert stack(program_layer("alone", below().hue(120))).advance_to(1 / FPS).max() == 0.0, "nothing is below"


def masked(alpha: tuple[Node, ...], red: float = 1.0) -> Program:
    """A red `solid_test` node, `solid`, masked by the last of `alpha`."""
    return Program(Graph((Node("solid", "solid_test", {"red": red}), *alpha)), "solid", alpha[-1].id)


RAMP = Node("ramp", "osc", {"freq": 1.0, "sync": 0.0})


@pytest.mark.usefixtures("fake_ops")
def test_a_programs_mask_weights_its_layer_per_pixel() -> None:
    comp = stack(program_layer("base", masked((RAMP,))))  # red shows as much as the ramp lets it
    frame = comp.advance_to(1 / FPS)
    expected = 0.5 + 0.5 * np.sin(np.linspace(0.0, 1.0, 8, dtype=np.float32) * np.float32(2 * np.pi))
    np.testing.assert_allclose(frame[:, 0], expected, atol=1e-6)
    assert comp.layer("base").masked


@pytest.mark.usefixtures("fake_ops")
def test_a_mask_is_clipped_so_it_never_brightens_its_layer() -> None:
    raw = (RAMP, Node("again", "osc", {"freq": 1.0, "sync": 0.0}), Node("sum", "add", {}, ("ramp", "again")))  # 0 to 2
    frame = stack(program_layer("base", masked(raw, red=0.5))).advance_to(1 / FPS)
    wave = 0.5 + 0.5 * np.sin(np.linspace(0.0, 1.0, 8, dtype=np.float32) * np.float32(2 * np.pi))
    np.testing.assert_allclose(frame[:, 0], 0.5 * np.minimum(2 * wave, 1.0), atol=1e-6)


@pytest.mark.parametrize("gives", [lambda n: np.float32(0.5), lambda n: np.full(n - 1, 0.5, np.float32)])
def test_a_mask_of_the_wrong_shape_is_the_layers_error_not_the_auras(gives, monkeypatch: pytest.MonkeyPatch,
                                                                    fake_ops: None) -> None:
    """The compositor blends a mask after the renderer's containment, so the
    bound program refuses a wrong one inside it, as the aura runs: without the tests'
    check of every node."""
    monkeypatch.setattr(BoundProgram, "strict", False)

    class Flat(Op, op="flatmask_test"):
        """A mask of the wrong shape."""

        sig = Sig.SOURCE
        out = Ty.SCALAR

        def build(self, inputs: Sequence[Fn]) -> Fn:
            return lambda c: gives(len(c.index))

    comp = stack(program_layer("base", masked((Node("m", "flatmask_test"),))))
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


def test_a_masked_layer_that_fails_draws_its_whole_error_frame(counter: type[Op], monkeypatch: pytest.MonkeyPatch,
                                                               fake_ops: None) -> None:
    monkeypatch.setattr(counter, "build", lambda self, inputs: lambda c: 1 / 0)
    comp = stack(program_layer("base", masked((Node("n", "count_test"),))))
    assert comp.layer("base").masked
    np.testing.assert_array_equal(comp.advance_to(1 / FPS), comp.error_frame(1 / FPS))
