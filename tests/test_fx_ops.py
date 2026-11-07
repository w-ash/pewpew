"""The built-in field ops through their catalog examples: each example
builds, checks and renders float32 at every node on each map its ops
take, and every arg of every op changes the picture when set live (the
method of tests/test_param_liveness.py, over the first example of each
op). Signal ops, whose examples are looks, are tests/test_signals.py's."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from functools import partial
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest

import fakes
from fakes import program_of
from pewpew import grid, lattice, line
from pewpew.compose import Look
from pewpew.fx.catalog import example
from pewpew.fx.compile import check, field_ops
from pewpew.fx.graph import PATTERN, Program
from pewpew.fx.op import Op, axis_choice, reach
from pewpew.fx.ops import OPS
from pewpew.fx.ops.source import DRIFT
from pewpew.mapping import extents
from pewpew.metrics import LIVENESS_RMS, rms
from pewpew.params import Float, ParamSet
from pewpew.params.probes import probes
from pewpew.render import SlotClock

FPS = 60.0
SEED = 42
MAPS = {1: line(24), 2: grid(6, 6), 3: lattice(4)}
# Liveness renders on the richest map an op takes: a volume spans every axis.
LIVE_MAPS = {3: lattice(6), 2: grid(8, 8), 1: line(32)}
HALF = 10
FIELD_OPS = {op: OPS[op] for op in field_ops()}


def dims_of(program: Program) -> set[int]:
    """The map dimensions every op of `program` takes."""
    return set.intersection(*(set(OPS[node.op].dims) for node in program.graph))


hosted = partial(fakes.hosted, seed=SEED)


def run(program: Program, mapping: np.ndarray, frames: int, start: float = 0.0) -> np.ndarray:
    renderer = hosted(program, mapping)
    clock = SlotClock(FPS, start=start)
    return np.stack([renderer.advance_to(clock.advance()).copy() for _ in range(frames)])


def examples() -> Iterator[Any]:
    for op, cls in FIELD_OPS.items():
        for i, py in enumerate(cls.examples):
            yield pytest.param(py, id=f"{op}-{i}")


def test_every_op_has_an_example_a_label_and_a_doc() -> None:
    for op, cls in OPS.items():
        assert cls.examples and cls.label and cls.__doc__, op
        made = example(cls.examples[0])
        nodes = made.signals if isinstance(made, Look) else made.graph
        assert any(node.op == op for node in nodes or ()), op


@pytest.mark.parametrize("py", list(examples()))
def test_each_example_renders_float32_at_every_node_on_each_map_it_takes(py: str) -> None:
    program = program_of(py)
    takes = dims_of(program)
    for dims, mapping in MAPS.items():
        problems = check(program, where="layers.base", dims=dims)
        assert (dims in takes) == (not problems), problems
        if dims in takes:
            frames = run(program, mapping, 3)
            assert frames.dtype == np.float32 and np.isfinite(frames).all(), (py, dims)


def spans(mapping: np.ndarray) -> list[float]:
    """The extent of `mapping` along x, y and z, as `Op.shows` reads it."""
    return extents(mapping).tolist()


def liveness_cases() -> Iterator[Any]:
    """One case per (op, probe) over the op's first example, on the
    richest map the example takes, but a probe that map cannot show
    (`Op.shows`): a `plane` probe of `auto` against the plane auto picks
    there is the same plane."""
    for op, cls in FIELD_OPS.items():
        if op == PATTERN:
            continue  # its knobs are its pattern's, which tests/test_param_liveness.py covers
        program = program_of(cls.examples[0])
        node = next(node for node in program.graph if node.op == op)
        mapping = next(m for d, m in LIVE_MAPS.items() if d in dims_of(program))
        args, extent = ParamSet(cls, node.args).snapshot(), spans(mapping)
        for record in ParamSet(cls).describe():
            for probe_id, a, b in probes(record):
                if cls.shows(record["name"], a, b, args, extent):
                    yield pytest.param(program, mapping, node.id, record["name"], a, b, id=f"{op}-{probe_id}")


@pytest.mark.parametrize("program, mapping, nid, name, a, b", list(liveness_cases()))
def test_every_op_arg_set_while_running_changes_the_picture(
    program: Program, mapping: np.ndarray, nid: str, name: str, a: object, b: object
) -> None:
    held, turned = hosted(program, mapping), hosted(program, mapping)
    for renderer in (held, turned):
        renderer.pattern.node_params[nid].set(name, a)  # type: ignore[attr-defined]  # a ProgramPattern
    clock = SlotClock(FPS)
    times = [clock.advance() for _ in range(2 * HALF)]
    before = [np.stack([r.advance_to(t).copy() for t in times[:HALF]]) for r in (held, turned)]
    assert np.array_equal(before[0], before[1]), "the two runs must be identical until the arg moves"
    turned.pattern.node_params[nid].set(name, b)  # type: ignore[attr-defined]
    after = [np.stack([r.advance_to(t).copy() for t in times[HALF:]]) for r in (held, turned)]
    observed = rms(*after)
    assert observed > LIVENESS_RMS, (
        f"{nid}.{name} does not respond to a live set: moving it from {a} to {b} changed the next {HALF} frames "
        f"by rms {observed:.3g}, under the {LIVENESS_RMS} bar"
    )


@pytest.mark.parametrize("place, mapping, reached", [
    ("u", line(8), {"x"}), ("all", line(8), {"x"}), ("x", line(8), {"x"}), ("y", line(8), set()),
    ("u", grid(4, 4), {"u"}), ("all", grid(4, 4), {"u", "x", "y"}), ("z", grid(4, 4), set()),
    ("auto", grid(4, 4), {"x", "y"}), ("xz", grid(4, 4), {"x"}), ("xz", lattice(3), {"x", "z"}),
])
def test_an_axis_or_a_plane_reaches_the_axes_the_map_spreads_along(
    place: str, mapping: np.ndarray, reached: set[str],
) -> None:
    """`u` runs along a strip's own axis, so on a strip it reaches that one."""
    assert reach(place, spans(mapping)) == reached


def test_an_arg_along_an_axis_the_map_does_not_spread_along_changes_nothing_there() -> None:
    """What liveness leaves unprobed, as each op declares it: lissajous's
    loops along a flat axis, a fold, zoom or tiling along one, a choice of
    one, two choices that read the map alike, and spin on a strip."""
    strip, panel = spans(line(8)), spans(grid(4, 4))
    knot, fold, zoom, flow = (OPS[op] for op in ("lissajous", "mirror", "scale", "feedback"))
    loops = ParamSet(knot).snapshot()
    assert [n for n in "abc" if knot.shows(n, 1, 9, loops, strip)] == ["a"]
    assert [n for n in "abc" if knot.shows(n, 1, 9, loops, panel)] == ["a", "b"]
    on_z = {**ParamSet(fold).snapshot(), "axis": "z"}
    assert not fold.shows("centre", 0.0, 1.0, on_z, panel)
    assert fold.shows("centre", 0.0, 1.0, {**on_z, "axis": "y"}, panel)
    assert [b for b in "xyz" if fold.shows("axis", "u", b, on_z, panel)] == ["x", "y"]
    assert [b for b in "xyz" if fold.shows("axis", "u", b, on_z, strip)] == []  # u is x there; y and z are flat
    zoomed = ParamSet(zoom).snapshot()
    assert not zoom.shows("axis", "all", "x", zoomed, strip) and zoom.shows("axis", "all", "x", zoomed, panel)
    assert flow.shows("spin", -180.0, 180.0, {}, panel) and not flow.shows("spin", -180.0, 180.0, {}, strip)


@pytest.mark.parametrize("declared, message", [
    ({"spinn": "x"}, "Turner.along names 'spinn', which is not one of its args"),
    ({"spin": "w"}, "Turner.along['spin'] is 'w'; give an axis (x, y or z) or an axis_choice arg"),
    ({"spin": "level"}, "Turner.along['spin'] is 'level'; give an axis (x, y or z) or an axis_choice arg"),
])
def test_along_names_args_of_the_op_each_to_an_axis_or_an_axis_choice(
    declared: Mapping[str, str], message: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        class Turner(Op):
            along = MappingProxyType(declared)
            spin = Float(0.0, 0.0, 1.0)
            level = Float(0.0, 0.0, 1.0)
            axis = axis_choice()

            def build(self, inputs: Any) -> Any:
                return inputs[0]


@pytest.mark.parametrize("py, dims, fix", [
    ("osc(8).kaleid(5)", 1, "use mirror along the strip"),
    ("osc(6).twist(90)", 2, "on a panel use rotate, on a strip scale"),
    ("quasicrystal(7)", 1, "use oscillator"),
])
def test_an_op_the_map_cannot_take_is_refused_with_what_to_use(py: str, dims: int, fix: str) -> None:
    (problem,) = check(program_of(py), where="layers.base", dims=dims)
    assert f"this map has {dims}" in problem and problem.endswith(fix)


def test_a_rate_keeps_its_phase_so_a_change_never_jumps_and_an_hour_runs_as_a_second() -> None:
    """The float rule (ADR-022): a rate adds `rate * dt` to a phase each
    frame, so its phase moves the same per frame at t = 3600 as at t = 0,
    and a new rate moves it on from where it is."""
    early, late = (run(program_of("osc(8, 0.25)"), line(16), 2, start=start) for start in (0.0, 3600.0))
    np.testing.assert_array_equal(early, late)
    renderer = hosted(program_of("osc(8, 0.25)"), line(16))
    op = renderer.pattern._nodes["osc"].op  # type: ignore[attr-defined]  # a ProgramPattern
    renderer.advance_to(1.0)
    assert op.phase("sync") == pytest.approx(0.25)
    renderer.pattern.node_params["osc"].set("sync", 1.0)  # type: ignore[attr-defined]
    renderer.advance_to(1.5)
    assert op.phase("sync") == pytest.approx(-0.25), "0.75 of a cycle, centred on 0"


def steps(program: Program, frames: int, phase: tuple[str, float] | None = None) -> np.ndarray:
    """The largest change of any pixel from each frame to the next of
    `program` on a 16x16 panel, from `phase` (node id, phase) if given."""
    renderer = hosted(program, grid(16, 16))
    renderer.advance_to(0.0)
    if phase is not None:
        nid, at = phase
        renderer.pattern._nodes[nid].op.phases["speed"] = at  # type: ignore[attr-defined]  # a ProgramPattern
    clock = SlotClock(FPS)
    shown = np.stack([renderer.advance_to(clock.advance()).copy() for _ in range(frames)])
    return np.abs(np.diff(shown, axis=0)).max(axis=(1, 2))


def test_a_drift_that_runs_backward_starts_without_a_jump() -> None:
    """A phase starts at 0 in the middle of its period, so a negative speed
    moves it on smoothly, as a positive one does."""
    back, ahead = (steps(program_of(f"noise(3).tunnel(0.35, {speed})"), 8) for speed in (-0.05, 0.05))
    assert back.max() < 2 * ahead.max() + 1e-3


@pytest.mark.parametrize("py, nid", [("noise(3, 2.0, octaves=3)", "noise"), ("voronoi(4, 2.0)", "voronoi")])
def test_a_noise_drifts_across_its_wrap_without_a_jump(py: str, nid: str) -> None:
    """A drifting noise loops its lattice where its phase wraps (DRIFT), so
    the frames across the wrap move as much as any others."""
    program = program_of(py)
    calm = steps(program, 30)
    across = steps(program, 30, (nid, DRIFT / 2 - 0.4))  # the wrap comes about 12 frames in
    assert across.max() < 1.5 * calm.max()
