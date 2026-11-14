"""The built-in field ops through their catalog examples: each example
builds, checks and renders float32 at every node on each map its ops
take, and every arg of every op changes the picture when set live (the
method of tests/test_param_liveness.py, over the first example of each
op). Signal ops, whose examples are looks, are tests/test_signals.py's."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import replace
from functools import partial
from types import MappingProxyType
from typing import Any

import numpy as np
import pytest

import fakes
from fakes import op_of, program_of
from pewpew.compose import Look
from pewpew.features import FakeFeatures
from pewpew.fx.catalog import example
from pewpew.fx.compile import check, field_ops
from pewpew.fx.expr import beat, layer, look
from pewpew.fx.graph import Program
from pewpew.fx.op import Op, axis_choice, reach
from pewpew.fx.ops import OPS
from pewpew.fx.ops.source import DRIFT
from pewpew.fx.prims import space
from pewpew.lab.check import ready
from pewpew.lab.geometry import Geometry, parse_geometry
from pewpew.lab.liveness import KnobProbe, dead, probe_knobs
from pewpew.mapping import extents, grid, lattice, line
from pewpew.metrics import FLASH_LIMIT, LIVENESS_RMS, measure, rms
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
        renderer.bound.node_params[nid].set(name, a)
    clock = SlotClock(FPS)
    times = [clock.advance() for _ in range(2 * HALF)]
    before = [np.stack([r.advance_to(t).copy() for t in times[:HALF]]) for r in (held, turned)]
    assert np.array_equal(before[0], before[1]), "the two runs must be identical until the arg moves"
    turned.bound.node_params[nid].set(name, b)
    after = [np.stack([r.advance_to(t).copy() for t in times[HALF:]]) for r in (held, turned)]
    observed = rms(*after)
    assert observed > LIVENESS_RMS, (
        f"{nid}.{name} does not respond to a live set: moving it from {a} to {b} changed the next {HALF} frames "
        f"by rms {observed:.3g}, under the {LIVENESS_RMS} bar"
    )


def every_map_cases(op: str) -> Iterator[Any]:
    """`liveness_cases` for op `op` on each map it takes, not only the richest."""
    cls = OPS[op]
    program = program_of(cls.examples[0])
    node = next(node for node in program.graph if node.op == op)
    for dims in sorted(cls.dims):
        mapping = LIVE_MAPS[dims]
        args, extent = ParamSet(cls, node.args).snapshot(), spans(mapping)
        for record in ParamSet(cls).describe():
            for probe_id, a, b in probes(record):
                if cls.shows(record["name"], a, b, args, extent):
                    yield pytest.param(program, mapping, node.id, record["name"], a, b, id=f"{dims}d-{probe_id}")


@pytest.mark.parametrize("program, mapping, nid, name, a, b", list(every_map_cases("branches")))
def test_every_branches_arg_changes_the_picture_on_each_map_it_takes(
    program: Program, mapping: np.ndarray, nid: str, name: str, a: object, b: object
) -> None:
    test_every_op_arg_set_while_running_changes_the_picture(program, mapping, nid, name, a, b)


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
    op = op_of(renderer, "osc")
    renderer.advance_to(1.0)
    assert op.phase("sync") == pytest.approx(0.25)
    renderer.bound.node_params["osc"].set("sync", 1.0)
    renderer.advance_to(1.5)
    assert op.phase("sync") == pytest.approx(-0.25), "0.75 of a cycle, centred on 0"


def steps(program: Program, frames: int, phase: tuple[str, float] | None = None) -> np.ndarray:
    """The largest change of any pixel from each frame to the next of
    `program` on a 16x16 panel, from `phase` (node id, phase) if given."""
    renderer = hosted(program, grid(16, 16))
    renderer.advance_to(0.0)
    if phase is not None:
        nid, at = phase
        op_of(renderer, nid).phases["speed"] = at
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


def test_a_saw_osc_wraps_within_zero_to_one_and_the_sine_default_is_unchanged() -> None:
    """`shape="saw"` climbs 0 to 1 along the room, then jumps back."""
    saw = run(program_of('osc(2.5, 0.3, shape="saw")'), line(64), 40)
    assert saw.dtype == np.float32
    assert saw.min() >= 0.0 and saw.max() < 1.0
    assert saw.max() > 0.97 and saw.min() < 0.03
    assert (np.diff(saw[0, :, 0]) < 0).sum() in (2, 3), "2.5 stripes wrap two or three times"
    np.testing.assert_array_equal(run(program_of("osc(2.5, 0.3)"), line(64), 4),
                                  run(program_of('osc(2.5, 0.3, shape="sine")'), line(64), 4))


def test_a_saw_osc_keeps_its_phase_across_a_rate_change() -> None:
    """The saw reads the same `sync` phase as the sine, so a new rate moves it on from where it is."""
    renderer = hosted(program_of('osc(1, 0.25, shape="saw")'), line(16))
    op = op_of(renderer, "osc")
    renderer.advance_to(1.0)
    assert op.phase("sync") == pytest.approx(0.25)
    renderer.bound.node_params["osc"].set("sync", 1.0)
    renderer.advance_to(1.5)
    assert op.phase("sync") == pytest.approx(-0.25)


def test_a_saw_osc_wrap_counts_as_a_flash_and_stays_within_the_gate_at_the_top_rate() -> None:
    """A saw's wrap is a hard edge, so a bright-to-dark palette over it counts
    flashes; `sync` tops out at 1 Hz, one wrap a second, inside the limit."""
    def flashes(rate: float) -> float:
        frames = run(program_of(f'osc(1, {rate}, shape="saw").palette("ember")'), line(32), 180)
        return measure(frames, FPS).flash_rate_max

    assert 0.0 < flashes(1.0) <= FLASH_LIMIT


def test_a_dither_sparkles_only_next_to_an_edge() -> None:
    """A light reaches half a spacing at amount 0.5, so only a light beside
    a hard edge ever changes; the flat parts hold still."""
    mapping = line(24)
    still = run(program_of("shape(0, 0.3, 0)"), mapping, 1)[0]
    shown = run(program_of("shape(0, 0.3, 0).dither(0.5, 6)"), mapping, 120)
    changed = np.flatnonzero(np.ptp(shown, axis=0).max(axis=-1) > 1e-6)
    edges = np.flatnonzero(np.abs(np.diff(still, axis=0)).max(axis=-1) > 0.5)
    beside = set(edges) | set(edges + 1)
    assert len(changed) and set(changed) <= beside, (changed, edges)


def test_a_dither_at_rate_0_holds_its_spots() -> None:
    shown = run(program_of("shape(0, 0.3, 0).dither(1, 0)"), line(24), 30)
    assert np.array_equal(shown[0], shown[-1])


def test_a_dither_reaches_by_the_spacing_along_each_axis() -> None:
    """Bars far apart, lights close together along each: the spacing along
    x is the gap between bars, along y the gap between lights."""
    from pewpew.fx.ops.coord import _pitch

    xs = np.repeat(np.array([0.0, 0.15, 0.30, 0.45], np.float32), 64)
    ys = np.tile(np.linspace(0.0, 1.0, 64, dtype=np.float32), 4)
    assert _pitch(xs, 0.45, len(xs), 0.05) == pytest.approx(0.15, rel=1e-3)
    assert _pitch(ys, 1.0, len(ys), 0.05) == pytest.approx(1 / 63, rel=1e-3)
    scattered = np.random.default_rng(0).random(256).astype(np.float32)
    assert _pitch(scattered, 1.0, 256, 0.05) == 0.05


def test_spherical_reads_the_true_distance_from_the_point_it_sets() -> None:
    """`osc(1, 0)` read through `spherical` is a wave of the distance in
    all three axes from the point `cx`, `cy`, `cz` set, a share of the
    map's extent on each axis; so every point at one distance shows one
    value, a shell."""
    renderer = hosted(program_of("osc(1, 0).spherical(cx=0.2, cy=0.7, cz=0.4)"), lattice(5))
    shown = renderer.advance_to(1.0)[:, 0].astype(np.float64)
    ctx = op_of(renderer, "spherical").ctx
    point = [lo + f * span for lo, f, span in zip(ctx.lo, (0.2, 0.7, 0.4), ctx.spans, strict=True)]
    d = np.sqrt(sum((axis.astype(np.float64) - m) ** 2 for axis, m in zip(ctx.coords.xyz, point, strict=True)))
    np.testing.assert_allclose(shown, 0.5 + 0.5 * np.sin(2.0 * np.pi * d), atol=1e-5)
    centred = hosted(program_of("osc(3, 0).spherical()"), lattice(5)).advance_to(1.0)[:, 0]
    xyz = np.stack(op_of(renderer, "spherical").ctx.coords.xyz, axis=-1).astype(np.float64)
    shells = np.round(np.linalg.norm(xyz - xyz.mean(axis=0), axis=-1), 6)
    for r in np.unique(shells):
        assert np.ptp(centred[shells == r]) < 1e-5, r


def test_the_centre_at_one_half_is_the_maps_centre_to_the_bit() -> None:
    """`BindCtx.at` gives `centre` exactly at 0.5 on every axis, so
    `polar` and `shape` at their default center render the same bytes as
    before they had one."""
    rng = np.random.default_rng(3)
    for _ in range(200):
        lo, span = rng.uniform(-3.0, 3.0, 3), rng.uniform(0.0, 5.0, 3) * (rng.random(3) > 0.2)
        ctx = replace(op_of(hosted(program_of("noise(3).polar()"), grid(4, 4)), "polar").ctx,
                      lo=tuple(lo.tolist()), hi=tuple((lo + span).tolist()))
        assert ctx.at((0.5, 0.5, 0.5)) == ctx.centre


def test_polar_at_its_defaults_reads_the_maps_centre_with_straight_spokes() -> None:
    """The default `polar` is the polar map about `BindCtx.centre`, byte for
    byte, on a map whose extent is not 0 to 1."""
    mapping = (lattice(5) * np.float32(0.76) + np.float32(0.12)).astype(np.float32)
    renderer = hosted(program_of("osc(3, 0).polar()"), mapping)
    shown = renderer.advance_to(1.0)
    ctx = op_of(renderer, "polar").ctx
    radius = space.polar(ctx.coords.xyz, ctx.plane("auto"), ctx.centre)[0]
    want = (0.5 + 0.5 * np.sin(2.0 * np.pi * (radius * np.float32(3.0)))).astype(np.float32)
    assert shown[:, 0].tobytes() == want.tobytes()


def test_polar_reads_its_center_along_the_normal_only_through_spiral() -> None:
    """With straight spokes the center's place along the plane's normal
    changes nothing; with `spiral` set, the spokes turn by `spiral` per unit
    from it, so moving it turns them."""
    def frame(args: str) -> np.ndarray:
        return run(program_of(f"noise(3).polar({args})"), lattice(6), 2)

    assert np.array_equal(frame("cz=0.2"), frame("cz=0.8"))
    assert rms(frame("cz=0.2, spiral=2"), frame("cz=0.8, spiral=2")) > 10 * LIVENESS_RMS
    polar = OPS["polar"]
    args, cube, panel = ParamSet(polar).snapshot(), spans(lattice(6)), spans(grid(6, 6))
    assert not polar.shows("cz", 0.0, 1.0, args, cube)
    assert polar.shows("cz", 0.0, 1.0, {**args, "spiral": 2.0}, cube)
    assert polar.shows("spiral", -4.0, 4.0, args, cube) and not polar.shows("spiral", -4.0, 4.0, args, panel)
    assert not polar.shows("cy", 0.0, 1.0, {**args, "plane": "xz"}, cube)


def test_a_round_shape_takes_no_plane_and_a_polygon_no_center_along_its_normal() -> None:
    """A circle is a sphere, the same in every plane, and a polygon is a
    prism along its plane's normal, so the gate does not probe either knob
    where it does nothing."""
    shape, cube = OPS["shape"], spans(lattice(6))
    round_, polygon = ParamSet(shape).snapshot(), {**ParamSet(shape).snapshot(), "sides": 5}
    assert not shape.shows("plane", "auto", "yz", round_, cube) and shape.shows("plane", "auto", "yz", polygon, cube)
    assert shape.shows("cz", 0.0, 1.0, round_, cube) and not shape.shows("cz", 0.0, 1.0, polygon, cube)
    staged = ready(look(layer("base", program_of("shape(0, 0.2, 0.1)")), seed=7))
    paths = [probe.path for probe in probe_knobs(staged, parse_geometry("lattice:6"), 0)]
    assert paths and not any(".plane" in path for path in paths), paths


def test_a_steady_pulse_starts_a_shell_every_one_over_rate_seconds_and_a_new_rate_shows_at_once() -> None:
    renderer = hosted(program_of("pulse(0.5, life=3)"), grid(6, 6))
    pulse = op_of(renderer, "pulse")
    renderer.advance_to(1.0)
    assert pulse.ages() == pytest.approx([1.0])
    renderer.bound.node_params["pulse"].set("rate", 2.0)
    assert pulse.ages() == pytest.approx([0.25 + 0.5 * k for k in range(6)]), "the phase held, the spacing is new"
    renderer.advance_to(1.25)
    assert pulse.ages()[0] == pytest.approx(0.0, abs=1e-9)


def test_pulse_shells_leave_the_point_softly_and_never_pass_full() -> None:
    """Each shell fades in, so the point does not pop when one starts; a
    shell's ring is brightest at `speed` times its age from the point."""
    frames = run(program_of("pulse(1.0, speed=0.3, width=0.1, life=4, cx=0, cy=0)"), grid(16, 16), 120)
    assert frames.min() >= 0.0 and frames.max() <= 1.0
    # The steepest step is the fade-in's middle, 1.5 / rise a second; a pop would be near 1.
    assert np.abs(np.diff(frames, axis=0)).max() < 0.2, "no frame jumps"
    renderer = hosted(program_of("pulse(0.25, speed=0.3, width=0.1, life=8, cx=0, cy=0)"), grid(16, 16))
    shown = renderer.advance_to(2.0)[:, 0]
    xyz = op_of(renderer, "pulse").ctx.coords.xyz
    d = np.hypot(xyz[0] - xyz[0].min(), xyz[1] - xyz[1].min())
    assert abs(float(d[np.argmax(shown)]) - 0.6) < 0.05


class _Beats:
    """Features whose beat comes `per_s` times a second."""

    def __init__(self, per_s: float) -> None:
        self.per_s = per_s
        self.base = FakeFeatures(0)

    def at(self, t: float) -> Any:
        return replace(self.base.at(t), beat_phase=(self.per_s * t) % 1.0)


@pytest.mark.parametrize("per_s, gap", [(2.0, 0.5), (3.0, 2.0 / 3.0)])
def test_a_beat_pulse_starts_a_shell_on_each_beat_but_one_too_close_to_the_last(per_s: float, gap: float) -> None:
    """A beat within 0.4 s of the last starts no shell, so shells start at
    most 2.5 times a second whatever the tempo."""
    renderer = hosted(program_of('pulse(sync="beat", life=8)'), grid(6, 6), features=_Beats(per_s))
    clock = SlotClock(FPS)
    for _ in range(int(4.0 * FPS)):
        renderer.advance_to(clock.advance())
    ages = op_of(renderer, "pulse").ages()
    assert len(ages) >= 3
    np.testing.assert_allclose(np.diff(ages), gap, atol=1e-6)


def test_a_pulse_at_its_top_rate_stays_within_the_flash_limit() -> None:
    """Thin, fast shells two a second pass a point twice a second: under
    WCAG's three flashes."""
    frames = run(program_of('pulse(2.0, speed=2.0, width=0.04, life=8, cx=0).palette("ember")'), line(32), 180)
    assert 0.0 < measure(frames, FPS).flash_rate_max <= FLASH_LIMIT


@pytest.mark.parametrize("chain", ["pulse(1.0, life=4)", 'pulse(sync="beat", speed=0.6, life=2)'])
def test_a_pulse_renders_the_same_bytes_every_time(chain: str) -> None:
    """No wall clock, no unseeded RNG: the same program, map and times give
    the same frames."""
    frames = [run(program_of(chain), lattice(5), 90) for _ in range(2)]
    assert frames[0].tobytes() == frames[1].tobytes()
    assert frames[0].std() > 0


def test_a_pulse_shell_holds_its_level_and_eases_out_over_the_last_fade_of_its_life() -> None:
    """A shell fades in, holds full, and eases out over the last `fade` of
    its life with no kink; a `fade` of 1 eases it out from the start."""
    renderer = hosted(program_of("pulse(0.5, speed=0.12, life=5.5, fade=0.4)"), grid(6, 6))
    pulse = op_of(renderer, "pulse")
    rise, hold = pulse.rise(), 5.5 * 0.6
    ages = np.linspace(0.0, 5.5, 2201)
    levels = np.array([pulse.level(float(a)) for a in ages])
    assert levels[0] == 0.0 and levels[-1] == pytest.approx(0.0, abs=1e-12)
    assert np.all(levels[(ages >= rise) & (ages <= hold)] == 1.0)
    assert np.all(np.diff(levels[ages >= hold]) <= 0.0)
    slopes = np.diff(levels) / np.diff(ages)
    assert np.abs(np.diff(slopes)).max() < 0.01, "the slope never jumps"
    renderer.bound.node_params["pulse"].set("fade", 1.0)
    assert pulse.level(rise) < 1.0 and pulse.level(2.75) == pytest.approx(0.5, abs=0.02)


def test_pulse_jitter_makes_each_shell_its_own_for_its_whole_life() -> None:
    """At `jitter` each shell has its own start, speed, width and peak,
    and some are left out; a shell keeps them as it travels, and the
    youngest's ages are uneven where at 0 they are evenly spaced."""
    renderer = hosted(program_of("pulse(1.0, life=12, jitter=1.0)"), grid(6, 6))
    pulse = op_of(renderer, "pulse")
    clock, seen = SlotClock(FPS), {}
    for _ in range(int(20 * FPS)):
        renderer.advance_to(clock.advance())
        for shell in pulse.shells():
            key = (round(shell.speed, 12), round(shell.width, 12))
            seen.setdefault(key, []).append(shell.level)
    speeds = {speed for speed, _ in seen}
    assert len(speeds) > 10 and min(speeds) >= 0.25 * 0.7 - 1e-9 and max(speeds) <= 0.25 * 1.3 + 1e-9
    ages = pulse.ages()
    assert len(ages) < 12, "some shells are left out"
    assert np.ptp(np.diff(ages)) > 0.3, "uneven"
    even = hosted(program_of("pulse(1.0, life=12)"), grid(6, 6))
    even.advance_to(20.0)
    np.testing.assert_allclose(np.diff(op_of(even, "pulse").ages()), 1.0)


def test_pulse_wander_starts_each_shell_from_its_own_point_near_the_centre() -> None:
    renderer = hosted(program_of("pulse(1.0, life=6, wander=0.3)"), lattice(5))
    renderer.advance_to(1.0)
    offsets = np.array([shell.offset for shell in op_of(renderer, "pulse").shells()])
    assert len(offsets) == 6 and len({tuple(o) for o in offsets.tolist()}) == 6
    assert np.linalg.norm(offsets, axis=1).max() <= 0.3 + 1e-12


@pytest.mark.parametrize("dims", sorted(MAPS))
@pytest.mark.parametrize("name, a, b", [("jitter", 0.0, 1.0), ("wander", 0.0, 0.5)])
def test_pulse_jitter_and_wander_change_the_picture_on_each_map(dims: int, name: str, a: float, b: float) -> None:
    def shown(value: float) -> np.ndarray:
        return run(program_of(f"pulse(1.0, life=4, {name}={value})"), MAPS[dims], 60)

    assert rms(shown(a), shown(b)) > LIVENESS_RMS


def test_an_uneven_pulse_stays_soft_within_full_and_under_the_flash_limit() -> None:
    """Jitter and wander move whole shells, never a step: each shell still
    fades in and out, and a turn of `jitter` fades a shell it leaves out."""
    frames = run(program_of("pulse(1.0, speed=0.3, width=0.1, life=4, jitter=1, wander=0.3)"), grid(16, 16), 240)
    assert frames.min() >= 0.0 and frames.max() <= 1.0
    assert np.abs(np.diff(frames, axis=0)).max() < 0.2
    top = run(program_of('pulse(2.0, speed=2.0, width=0.04, life=8, cx=0, jitter=1).palette("ember")'), line(32), 600)
    assert 0.0 < measure(top, FPS).flash_rate_max <= FLASH_LIMIT
    renderer = hosted(program_of("pulse(1.0, life=8, jitter=0.5)"), grid(8, 8))
    renderer.advance_to(3.0)
    before = renderer.advance_to(3.0 + 1 / FPS).copy()
    renderer.bound.node_params["pulse"].set("jitter", 0.52)
    assert np.abs(renderer.advance_to(3.0 + 2 / FPS) - before).max() < 0.1, "a small turn moves shells a little"


def _hollow() -> np.ndarray:
    """A volume with nothing within 0.22 of its centre, where a pulse starts."""
    points = lattice(9)
    return points[np.linalg.norm(points - 0.5, axis=1) >= 0.22]


def test_a_slow_steady_pulse_is_on_its_way_from_the_first_frame_and_every_knob_shows() -> None:
    """A steady train is as if it had always run: at the first frame the
    shells started before it are out at their range, so a slow pulse on
    a map with nothing near its point shows in the gate's one second."""
    renderer = hosted(program_of("pulse(0.5, speed=0.04, width=0.12, life=12)"), _hollow())
    assert renderer.advance_to(1 / FPS).max() > 0.5
    staged = ready(look(layer("base", program_of("pulse(0.5, speed=0.04, width=0.12, life=12)")), seed=7))
    probed = probe_knobs(staged, Geometry("hollow", _hollow()), 0)
    assert probed and not dead(probed), dead(probed)


def test_a_beat_pulse_starts_with_the_train_the_beat_would_have_sent() -> None:
    """The beat runs whether a pulse watched it or not, so on its second
    frame a beat pulse remembers the beats of the last 20 s at the tempo
    the phase moves at, each at least 0.4 s apart, and every knob shows in
    the gate's one second."""
    renderer = hosted(program_of('pulse(sync="beat", life=8)'), grid(6, 6), features=_Beats(3.0))
    renderer.advance_to(1 / FPS)
    assert op_of(renderer, "pulse").ages() == []
    renderer.advance_to(2 / FPS)
    ages = op_of(renderer, "pulse").ages()
    assert ages[0] == pytest.approx(2 / FPS, abs=1e-9) and ages[-1] > 7.0
    np.testing.assert_allclose(np.diff(ages), 2.0 / 3.0, atol=1e-9)
    chain = 'pulse(sync="beat", speed=0.12, width=0.14, life=5.4, fade=0.3).palette("ember")'
    probed = probe_knobs(ready(look(layer("base", program_of(chain)), seed=7)), Geometry("hollow", _hollow()), 0)
    assert probed and not dead(probed), dead(probed)


def test_a_plane_that_reads_the_input_alike_passes_when_another_plane_shows() -> None:
    """`osc` along x through `spherical` reads only the distance, which
    xy and xz both put on x: xz shows as xy does, yz does not, so `plane`
    is live and xz is `alike`. Stripes along the wiring (u) read no axis
    `spherical` moves, so no plane changes them, and `plane` is dead."""
    def probed(chain: str) -> dict[str, KnobProbe]:
        made = ready(look(layer("base", program_of(chain)), seed=7))
        return {p.path: p for p in probe_knobs(made, parse_geometry("lattice:6"), 0)}

    shells = probed('osc(6).spherical().palette("ice")')
    plane = {path: p for path, p in shells.items() if ".plane=" in path}
    assert {path.rsplit("=", 1)[1]: p.alike for path, p in plane.items()} == {"xz": True, "yz": False}
    assert all(p.live for p in plane.values()) and not dead(shells.values())
    wired = dead(probed('osc(2, axis="u").spherical()').values())
    assert {"layers.base.spherical.plane=xz", "layers.base.spherical.plane=yz"} <= set(wired), wired


def test_a_blend_mode_that_shows_as_normal_passes_when_another_mode_shows() -> None:
    """A noise is never 0, so `stencil` shows as `normal` over it: `alike`,
    not dead, since the other modes change the picture. At `amount` 0 no
    mode shows, and `mode` is dead."""
    def probed(amount: float) -> tuple[KnobProbe, ...]:
        chain = f'noise(3).blend(noise(5, 0.2), "normal", {amount}).palette("ember")'
        return probe_knobs(ready(look(layer("base", program_of(chain)), seed=7)), parse_geometry("lattice:6"), 0)

    mixed = probed(0.5)
    assert [p.path for p in mixed if p.alike] == ["layers.base.blend_.mode=stencil"] and not dead(mixed)
    still = [path for path in dead(probed(0.0)) if ".mode=" in path]
    modes = next(record for record in ParamSet(OPS["blend"]).describe() if record["name"] == "mode")["options"]
    assert len(still) == len(modes) - 1, still


@pytest.mark.parametrize("dims", sorted(MAPS))
@pytest.mark.parametrize("name, a, b", [("gain", 0.3, 0.8), ("lacunarity", 1.75, 3.0), ("ridge", 0.0, 1.0)])
def test_noise_gain_lacunarity_and_ridge_change_the_picture_on_each_map(
    dims: int, name: str, a: float, b: float,
) -> None:
    def shown(value: float) -> np.ndarray:
        return run(program_of(f"noise(3, 0.1, octaves=4, {name}={value})"), MAPS[dims], 20)

    assert rms(shown(a), shown(b)) > LIVENESS_RMS


def test_noise_weighs_and_spaces_finer_layers_only_when_it_has_them() -> None:
    noise, args = OPS["noise"], ParamSet(OPS["noise"]).snapshot()
    cube = spans(lattice(6))
    assert not noise.shows("gain", 0.3, 0.8, args, cube) and not noise.shows("lacunarity", 1.75, 3.0, args, cube)
    assert noise.shows("gain", 0.3, 0.8, {**args, "octaves": 3}, cube) and noise.shows("ridge", 0.0, 1.0, args, cube)


def test_a_ridged_noise_is_dark_with_soft_bright_crests_within_zero_to_one() -> None:
    """Folded, the hills become crests: most of the room dark, the crests
    bright, and no crest a hard line or a kink: with lights twice as dense
    the steepest step between neighbours halves, and the sharpest bend
    falls to a quarter, as for any smooth curve."""
    room = run(program_of("noise(8, 0.1, octaves=4, ridge=1)"), grid(48, 48), 1)[0, :, 0]
    assert 0.0 <= room.min() and room.max() <= 1.0
    assert np.median(room) < 0.4 < np.percentile(room, 95)
    coarse, fine = (run(program_of("noise(8, 0.1, octaves=4, ridge=1)"), line(n), 1)[0, :, 0].astype(np.float64)
                    for n in (2000, 4000))
    assert np.abs(np.diff(fine)).max() < 0.6 * np.abs(np.diff(coarse)).max()
    assert np.abs(np.diff(fine, 2)).max() < 0.35 * np.abs(np.diff(coarse, 2)).max()


def test_a_noise_of_a_quarter_lacunarity_drifts_across_its_wrap_without_a_jump() -> None:
    """A lacunarity in quarters keeps each octave's lattice period whole,
    so the drift wraps with no jump; between quarters it reads the nearest."""
    program = program_of("noise(3, 2.0, octaves=4, lacunarity=2.25)")
    calm = steps(program, 30)
    across = steps(program, 30, ("noise", DRIFT / 2 - 0.4))
    assert across.max() < 1.5 * calm.max()
    np.testing.assert_array_equal(run(program_of("noise(3, 0.1, octaves=3, lacunarity=2.3)"), grid(6, 6), 2),
                                  run(program_of("noise(3, 0.1, octaves=3, lacunarity=2.25)"), grid(6, 6), 2))


def test_a_log_distance_reads_doublings_of_the_distance_over_the_maps_span() -> None:
    """`distance="log"` puts log2(distance / the map's largest span) on the
    distance axis, at least 2^-10 of the span from the point, so each
    doubling of the distance holds as many stripes as the one before."""
    renderer = hosted(program_of('osc(1, 0).spherical(cx=0.2, distance="log")'), lattice(5))
    shown = renderer.advance_to(1.0)[:, 0].astype(np.float64)
    ctx = op_of(renderer, "spherical").ctx
    point = ctx.at((0.2, 0.5, 0.5))
    d = np.sqrt(sum((axis.astype(np.float64) - m) ** 2 for axis, m in zip(ctx.coords.xyz, point, strict=True)))
    logged = np.log2(np.maximum(d / max(ctx.spans), 2.0**-10))
    np.testing.assert_allclose(shown, 0.5 + 0.5 * np.sin(2.0 * np.pi * logged), atol=2e-4)


@pytest.mark.parametrize("mapping", [grid(8, 8), lattice(6)])
def test_a_log_distance_changes_the_picture(mapping: np.ndarray) -> None:
    def shown(distance: str) -> np.ndarray:
        return run(program_of(f'noise(3).spherical(distance="{distance}")'), mapping, 10)

    assert rms(shown("linear"), shown("log")) > LIVENESS_RMS


def test_a_beats_width_shows_only_for_its_pulse() -> None:
    """The phase and the fall do not read `width`, so the gate does not
    probe it there."""
    shown = OPS["beat"].shows
    assert shown("width", 0.05, 0.95, {"shape": "pulse", "width": 0.25}, [1.0, 0.0, 0.0])
    assert not shown("width", 0.05, 0.95, {"shape": "fall", "width": 0.25}, [1.0, 0.0, 0.0])
    made = look(layer("base", program_of('osc(6).palette("ocean")')),
                routes=[beat("fall").to("layers.base.osc.offset", depth=0.25)])
    paths = [probe.path for probe in probe_knobs(ready(made), parse_geometry("line:16"), 0)]
    assert "signals.beat.shape=phase" in paths and not any(path.startswith("signals.beat.width") for path in paths)
