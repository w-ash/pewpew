"""The stateful ops (feedback, trails, the graph sims, particles,
attractors) and what they share (pewpew.fx.field, the graph and the
random arrivals), and the example looks under examples/.

The catalog examples of every op, and the liveness of every arg, are
tests/test_fx_ops.py's; this file holds what only state has: the same
seed gives the same bytes, a hot reload carries the state on mid-run, a
feedback field never climbs past what it reads, the simulations stay
finite and in range at both ends of every knob, on every kind of map,
and over minutes neither climbs to white nor settles."""

from __future__ import annotations

import json
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import fakes
from fakes import Pooled, program_of
from pewpew import grid, lattice, line
from pewpew.fx.compile import check
from pewpew.fx.field import CAPS, Lattice, Splat, lattice_axes
from pewpew.fx.graph import Graph, Node, Program
from pewpew.fx.host import ProgramPattern
from pewpew.fx.op import BindCtx, Op
from pewpew.fx.ops import OPS
from pewpew.fx.ops.sims import arrivals
from pewpew.fx.prims.sample import sample
from pewpew.fx.types import Coords
from pewpew.lab import Verification, verify_looks
from pewpew.lab.geometry import AUTO
from pewpew.params import Float, ParamSet

FPS = 30.0
STATE_OPS = sorted(op for op, cls in OPS.items() if cls.stateful)
RANDOM_OPS = ("attractor", "life", "particles", "reaction", "ripple")
SIMS = ("diffuse", "life", "reaction", "ripple")
EXAMPLES = Path(__file__).parent.parent / "examples"
EXAMPLE_LOOKS = {path.name.removesuffix(".look.json"): path for path in sorted(EXAMPLES.glob("*.look.json"))}


hosted = partial(fakes.hosted, seed=7)
frames = partial(fakes.frames, fps=FPS)


def first_example(op: str) -> Program:
    return program_of(OPS[op].examples[0])


def a_map(program: Program) -> np.ndarray:
    """A small map every op of `program` takes: a panel when it can."""
    return grid(8, 8) if not check(program, dims=2) else lattice(4)


def test_the_new_ops_keep_state_and_say_whether_they_warp() -> None:
    assert {"feedback", "trails", *SIMS, "particles", "attractor"} <= set(STATE_OPS)
    # Grid-backed state reads anywhere; state per point does not.
    assert {op for op in STATE_OPS if OPS[op].warpable} >= {"feedback", "particles", "attractor"}
    assert not any(OPS[op].warpable for op in ("trails", *SIMS))
    assert all(OPS[op].cost.ns_per_point or OPS[op].cost.us_fixed for op in STATE_OPS), "each has a measured cost"


@pytest.mark.parametrize("op", STATE_OPS)
def test_the_same_seed_gives_the_same_bytes(op: str) -> None:
    program = first_example(op)
    mapping = a_map(program)
    once, again = (frames(hosted(program, mapping), 20) for _ in range(2))
    assert once.tobytes() == again.tobytes()
    if op in RANDOM_OPS:
        assert not np.array_equal(once, frames(hosted(program, mapping, seed=8), 20)), "another seed, another stream"


@pytest.mark.parametrize("op", STATE_OPS)
def test_a_hot_reload_carries_the_state_on_mid_run(op: str) -> None:
    """A reload to the same program mid-run continues frame for frame, as
    if nothing had happened: the buffers, phases and tick carry over."""
    program = first_example(op)
    mapping = a_map(program)
    steady = frames(hosted(program, mapping), 30)
    reloaded = hosted(program, mapping)
    before = frames(reloaded, 15)
    report = reloaded.swap(ProgramPattern.of(program)())
    assert report.buffers, "the node buffers are carried"
    np.testing.assert_array_equal(np.concatenate([before, frames(reloaded, 15)]), steady)


@pytest.mark.parametrize("py", [
    'shape(5, 0.3).feedback(10, 4, 180, 360, 1, 1)',
    'shape(5, 0.3).palette("ember").feedback(10, 0.25, -180, -360, -1, 1)',
])
@pytest.mark.parametrize("mapping", [line(40), grid(10, 10), lattice(5)], ids=["strip", "panel", "volume"])
def test_feedback_holds_a_static_input_and_never_climbs_past_it(py: str, mapping: np.ndarray) -> None:
    """The field takes the brighter of itself and its input, so on a static
    input it settles at most at the input's brightest, never at white
    (the ratchet of docs/authoring.md §7.2)."""
    program = program_of(py)
    source = program_of(py.rsplit(".feedback", 1)[0])
    top = frames(hosted(source, mapping), 1).max()
    shown = frames(hosted(program, mapping), 90)
    assert np.isfinite(shown).all() and shown.max() <= top + 1e-6
    assert shown[-1].mean() > 0.0


def sim_cases() -> Iterator[Any]:
    """Each simulation with each float knob at each end of its range."""
    for op in SIMS:
        base = dict(first_example(op).output.args)
        for record in ParamSet(OPS[op]).describe():
            if record["kind"] == "float":
                for end in ("lo", "hi"):
                    yield pytest.param(op, {**base, record["name"]: record[end]}, id=f"{op}-{record['name']}-{end}")


def sim_program(op: str, args: dict[str, Any]) -> Program:
    """`op` on its own, or reading a moving field when it reads one."""
    if not OPS[op].inputs:
        return Program(Graph((Node("sim", op, args),)), "sim")
    return Program(Graph((Node("heads", "lissajous", {"heads": 3, "width": 0.15}), Node("sim", op, args, ("heads",)))),
                   "sim")


@pytest.mark.parametrize("op, args", list(sim_cases()))
def test_a_simulation_stays_finite_and_in_range_at_either_end_of_a_knob(op: str, args: dict[str, Any]) -> None:
    """Each step stays inside its scheme's stable range at every setting,
    even at a slow 10 frames a second."""
    shown = frames(hosted(sim_program(op, args), grid(10, 10)), 40, fps=10.0)
    assert np.isfinite(shown).all() and shown.min() >= 0.0 and shown.max() <= 1.0


@pytest.mark.parametrize("op", SIMS)
def test_a_simulation_runs_steady_at_its_defaults_on_every_kind_of_map(op: str, example: Any) -> None:
    for mapping in (line(48), grid(12, 12), lattice(5), example.mapping):
        renderer = hosted(sim_program(op, {}), mapping)
        shown = frames(renderer, 45)
        assert np.isfinite(shown).all() and 0.0 <= shown.min() and shown.max() <= 1.0
        assert renderer.error is None
        assert np.abs(np.diff(shown, axis=0)).max() > 0.0, f"{op} does not move on {len(mapping)} points"


def two_strips() -> np.ndarray:
    """Two strips a unit apart: each point links only to points of its own
    strip, so the graph falls in two parts."""
    return np.concatenate([line(30), line(30) + np.array([0.0, 1.0, 0.0], np.float32)]).astype(np.float32)


# Ripple ponds, by name: the args, the map, and the parts of its graph.
PONDS: dict[str, tuple[dict[str, Any], np.ndarray, list[slice]]] = {
    "defaults-strip": ({}, line(60), [slice(None)]),
    "volume": ({"speed": 0.2, "damping": 1.0, "drops": 1.0, "size": 0.12}, lattice(6), [slice(None)]),
    "wildest": ({"speed": 2.0, "damping": 0.1, "drops": 4.0, "size": 0.3}, grid(12, 12), [slice(None)]),
    "two-parts": ({"drops": 1.0}, two_strips(), [slice(0, 30), slice(30, 60)]),
}
LIFE_MAPS = {"strip": line(60), "panel": grid(16, 16), "volume": lattice(6)}
LIFE_STATES = (3, 6, 12)


def last_10_s(op: str, args: dict[str, Any], mapping: np.ndarray, seconds: float) -> np.ndarray:
    """The last 10 s of `seconds` of `op` (`sim_program`) on `mapping`, at
    10 frames a second."""
    return frames(hosted(sim_program(op, args), mapping), round(10 * seconds), fps=10.0)[-100:]


# The long runs, each on the suite's process pool (conftest.py): two
# minutes of each pond, and a minute of life on each map at each count of
# states.
LONG_RUNS = {
    **{("pond", name): partial(last_10_s, "ripple", args, mapping, 120.0)
       for name, (args, mapping, _) in PONDS.items()},
    **{("life", name, states): partial(last_10_s, "life", {"states": states}, mapping, 60.0)
       for name, mapping in LIFE_MAPS.items() for states in LIFE_STATES},
}


@pytest.mark.parametrize("pond", PONDS)
def test_a_pond_stays_level_however_long_it_runs(pond: str, pooled: Pooled) -> None:
    """A drop lifts its point as much as it lowers the rest, and the whole
    pond settles at its damping, so two minutes in still water still shows
    0.5 on average, in each part of the graph, and never climbs to white."""
    _, _, parts = PONDS[pond]
    late = pooled["pond", pond][:, :, 0]
    for part in parts:
        assert late[:, part].mean() == pytest.approx(0.5, abs=0.05)
    assert (late >= 0.999).mean() < 0.25


@pytest.mark.parametrize("states", LIFE_STATES)
@pytest.mark.parametrize("map_name", LIFE_MAPS)
def test_life_never_settles(states: int, map_name: str, pooled: Pooled) -> None:
    """On a strip or a small map the automaton's waves die out; its sparks
    start new ones, so a minute in the picture still moves."""
    late = pooled["life", map_name, states]
    assert np.abs(np.diff(late, axis=0)).max() > 0.0


def test_a_clifford_cloud_turns_in_a_panel_s_plane() -> None:
    """Turned about the up axis, a flat cloud would show edge on to a
    panel; it turns in the panel's plane instead, so it spans the panel at
    every angle."""
    mapping = grid(16, 16)
    shown = frames(hosted(program_of('attractor("clifford", 2000, spin=90, trail=0.1)'), mapping), 75)
    columns = [len(np.unique(mapping[frame > 0.25 * frame.max(), 0])) for frame in shown[15:, :, 0]]
    assert min(columns) >= 10, "past a quarter turn, the cloud still spans the panel"


@pytest.mark.parametrize("py", [
    "ripple().feedback(1, 1.2).kaleid(6)",
    "below().feedback(0.6, 0.8).rotate(0.3)",
    "lissajous().trails(0.8).feedback(1, 1.2).scale(2)",
])
def test_a_coord_op_may_warp_feedback_over_anything(py: str) -> None:
    """Feedback reads what is under it at the map's own points, before
    render, and its field reads anywhere: a warp above it moves only where
    the field is read."""
    assert check(program_of(py), where="layers.base", dims=2) == []


def test_a_warp_over_feedback_warps_the_field() -> None:
    warped, plain = (frames(hosted(program_of(py), grid(12, 12)), 30)
                     for py in ("ripple().feedback(1, 1.2).kaleid(6)", "ripple().feedback(1, 1.2)"))
    assert np.isfinite(warped).all() and not np.array_equal(warped, plain)


def test_a_warp_stops_at_the_state_op_it_cannot_read_through() -> None:
    """Trails holds a value per point, so a warp above it is refused, for
    trails alone: what trails reads is read at the map's own points."""
    program = Program(Graph((Node("pond", "ripple", {}), Node("tail", "trails", {}, ("pond",)),
                             Node("fold", "kaleid", {}, ("tail",)))), "fold")
    assert check(program, dims=2) == [(
        "fold: kaleid warps what 'tail' reads, and trails has a value only at the map's own points; "
        "apply kaleid to a source instead"
    )]


def test_planar_names_only_args_of_the_op() -> None:
    with pytest.raises(ValueError, match=r"Turner.planar names \['spinn'\], which are not its args"):
        class Turner(Op):
            planar = frozenset({"spinn"})
            spin = Float(0.0, 0.0, 1.0)

            def build(self, inputs: Any) -> Any:
                return inputs[0]


# ---- what the state ops share --------------------------------------------------------


def bind_ctx(mapping: np.ndarray) -> BindCtx:
    """A bind context for `mapping`, as the host makes one."""
    x, y, z = (np.ascontiguousarray(mapping[:, a]) for a in range(3))
    index = np.arange(len(mapping), dtype=np.int32)
    lo = tuple(float(a.min()) for a in (x, y, z))
    hi = tuple(float(a.max()) for a in (x, y, z))
    return BindCtx("layers.base.n", {}, Coords.of(x, y, z, index), lo, hi, 0, 0,  # type: ignore[arg-type]
                   lambda *a: np.zeros(0), lambda: mapping, lambda: mapping)


def test_a_lattice_runs_along_the_strip_in_the_plane_or_through_the_volume() -> None:
    wall = grid(6, 6)[:, [0, 2, 1]]  # a panel standing in xz
    assert [lattice_axes(bind_ctx(m)) for m in (line(9), wall, lattice(3))] == [("u",), ("x", "z"), ("x", "y", "z")]


def test_a_lattice_has_square_cells_and_stays_under_its_cap() -> None:
    wide = grid(40, 20)
    wide[:, 0] *= 2.0  # twice as wide as it is tall
    cells = Lattice.over(bind_ctx(wide), 3)
    sides = [span / (n - 1) for span, n in zip(cells.span, cells.counts)]
    assert sides[0] == pytest.approx(sides[1], rel=0.05)
    huge = Lattice.over(bind_ctx(lattice(40)), 3)
    assert np.prod(huge.counts) <= CAPS[3]


def test_a_splat_gives_back_what_the_points_hold_and_nothing_far_from_them() -> None:
    mapping = grid(9, 9)
    mapping[:, 0] *= 0.5  # the points fill the left half of a wider map...
    mapping = np.concatenate([mapping, [[1.0, 0.5, 0.0]]]).astype(np.float32)  # ...and one stands far right
    ctx = bind_ctx(mapping)
    cells = Lattice.over(ctx, 3)
    splat = Splat.of(cells, cells.at(ctx.coords), 2)
    field = splat(np.full(len(mapping), 0.7, np.float32))
    np.testing.assert_allclose(cells.sample(field, ctx.coords), 0.7, rtol=1e-5)
    assert field[:, int(cells.counts[0] * 0.75)].max() == 0.0, "no point near, nothing written"
    rgb = splat(np.tile(np.array([0.1, 0.5, 0.9], np.float32), (len(mapping), 1)))
    np.testing.assert_allclose(cells.sample(rgb, ctx.coords), np.tile([0.1, 0.5, 0.9], (len(mapping), 1)), rtol=1e-5)


def test_a_glow_keeps_its_weight_and_peaks_near_it() -> None:
    cells = Lattice.over(bind_ctx(grid(16, 16)), 2)
    at = [np.array([0.5], np.float32), np.array([0.5], np.float32)]
    blob = cells.glow(at, np.array([0.8], np.float32), 0.1)
    assert blob.sum() == pytest.approx(0.8, rel=1e-4)
    assert float(sample(blob, at)[0]) * cells.peak(0.1) == pytest.approx(0.8, rel=0.1)
    assert cells.reach(0.001) == cells.reach(cells.spacing), "never narrower than the points are apart"


def test_arrivals_come_at_their_rate_the_first_on_the_first_frame() -> None:
    def run(rate: float, frames: int, key: int = 1) -> list[int]:
        countdown = np.zeros(1)
        return [arrivals(countdown, rate, 1 / FPS, np.random.Generator(np.random.Philox(key=[key, tick])))
                for tick in range(frames)]

    assert run(2.0, 1) == [1] and sum(run(0.0, 300)) == 0
    over_a_while = run(2.0, 30 * 300)
    assert sum(over_a_while) == pytest.approx(600, rel=0.1) and over_a_while == run(2.0, 30 * 300)
    assert max(run(1e6, 3)) == 32, "a backlog past the most a frame takes is dropped"


# ---- the example looks -------------------------------------------------------------


def test_the_examples_cover_strips_panels_and_volumes() -> None:
    assert len(EXAMPLE_LOOKS) >= 8
    used = {node["op"] for path in EXAMPLE_LOOKS.values()
            for look in json.loads(path.read_text())["looks"].values()
            for layer in look["layers"] for node in layer["nodes"].values()}
    assert {"feedback", "particles", "attractor", "reaction", "ripple", "diffuse"} <= used


def failures(verdict: Verification) -> object:
    failed = {look.name: look.failures for file in verdict.files for look in file.looks if not look.ok}
    return failed or [file.problems for file in verdict.files]


# The map docs/authoring.md names for each look, where it is not the panel
# `verify looks` takes by default: a strip or a volume (`firefly-ink`, for
# any map, on a strip, where it is sparest). A room map renders too slowly
# for this suite.
OWN_MAPS = {
    "copper-tide": "line:120",
    "warp-lane": "line:120",
    "firefly-ink": "line:120",
    "depth-charge": "lattice:6",
    "lorenz-lantern": "lattice:6",
    "ember-fountain": "lattice:6",
}


# The verdict on each example file on the map `verify looks` takes by
# default, over 2 s, and on each look's own map, over 1 s, by (name, map),
# then the long runs. A verdict is the same in any process, so the suite's
# process pool runs them beside the tests in front of them (conftest.py).
JOBS = {
    **{(name, AUTO): partial(verify_looks, [path], map_spec=AUTO, seconds=2.0) for name, path in EXAMPLE_LOOKS.items()},
    **{(name, spec): partial(verify_looks, [EXAMPLE_LOOKS[name]], map_spec=spec, seconds=1.0)
       for name, spec in OWN_MAPS.items()},
    **LONG_RUNS,
}


def test_every_example_look_passes_the_content_gate(pooled: Pooled) -> None:
    """`verify looks examples/`, a file at a time: each checks, renders
    without a raise, flashes at most 3 times a second, is not black, and
    every knob is live."""
    files = tuple(file for name in EXAMPLE_LOOKS for file in pooled[name, AUTO].files)
    verdict = Verification(all(file.ok for file in files), files)
    assert len(files) == len(EXAMPLE_LOOKS)
    assert verdict.ok, failures(verdict)


@pytest.mark.parametrize("name, map_spec", OWN_MAPS.items())
def test_each_example_look_passes_the_content_gate_on_its_own_map(
    name: str, map_spec: str, pooled: Pooled,
) -> None:
    """On a strip, feedback's spin and swirl, a plane or an axis the strip
    does not spread along, and `u` against the strip's own axis cannot
    show, so the gate does not probe them (`Op.shows`); every other knob
    is live there."""
    verdict = pooled[name, map_spec]
    assert verdict.ok, failures(verdict)
