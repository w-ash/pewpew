"""Tests for the neighbour graph and its steps (src/pewpew/fx/prims/knn.py):
the grid-hash search equals brute force on every layout, and the steps
conserve what they should and stay stable."""

from __future__ import annotations

import math
import time

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from pewpew.fx.prims.knn import Neighbors, diffuse, gray_scott_step, laplacian, neighbors, wave_step
from pewpew.mapping import grid, lattice, line


def brute(points: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Every pair's distance, sorted by distance then index, self excluded
    and spare slots padded with self at inf."""
    pts = np.asarray(points, np.float32).reshape(len(points), -1)
    n = len(pts)
    d2 = np.zeros((n, n), np.float32)
    for a in range(pts.shape[1]):
        delta = pts[:, a][:, None] - pts[:, a][None]
        d2 += delta * delta
    np.fill_diagonal(d2, np.inf)
    d2 = np.hstack([d2, np.full((n, k), np.inf, np.float32)])
    order = np.lexsort((np.broadcast_to(np.arange(n + k), d2.shape), d2), axis=1)[:, :k]
    dk = np.take_along_axis(d2, order, axis=1)
    return np.where(np.isinf(dk), np.arange(n)[:, None], order), np.sqrt(dk)


def assert_brute(points: np.ndarray, k: int) -> Neighbors:
    nbrs = neighbors(points, k)
    idx, dist = brute(points, k)
    assert nbrs.idx.dtype == np.int32 and nbrs.dist.dtype == np.float32
    assert np.array_equal(nbrs.idx, idx)
    assert np.array_equal(nbrs.dist, dist)
    return nbrs


@st.composite
def clouds(draw):
    """1 to 60 points of 1 to 3 axes, some of them duplicates, some axes flat."""
    n, d = draw(st.integers(1, 60)), draw(st.integers(1, 3))
    pool = draw(arrays(np.float32, (draw(st.integers(1, n)), d), elements=st.floats(0, 1, width=32)))
    picks = draw(arrays(np.int64, n, elements=st.integers(0, len(pool) - 1)))
    pts = pool[picks]
    flat = draw(st.lists(st.booleans(), min_size=d, max_size=d))
    pts[:, flat] = 0.25
    return pts


@given(clouds(), st.integers(1, 8))
def test_knn_equals_brute_force(points, k: int) -> None:
    assert_brute(points, k)


@pytest.mark.parametrize(
    "points",
    [line(200), grid(12, 9), lattice(6), np.zeros((7, 3), np.float32)],
    ids=["strip", "panel", "lattice", "one-spot"],
)
@pytest.mark.parametrize("k", [1, 2, 6, 12])
def test_knn_equals_brute_force_on_regular_layouts(points, k: int) -> None:
    """Regular layouts tie at equal distances; ties go to the lower index."""
    assert_brute(points, k)


def test_knn_finds_a_far_outlier() -> None:
    rng = np.random.default_rng(0)
    cluster = rng.random((300, 3), dtype=np.float32) * 0.02
    assert_brute(np.vstack([cluster, [[1.0, 1.0, 1.0]]]).astype(np.float32), 6)


def test_knn_on_a_curve_through_a_box() -> None:
    t = np.linspace(0, 30, 900)
    helix = np.stack([np.cos(t), np.sin(t), t / 30], axis=1).astype(np.float32)
    assert_brute(helix, 6)


def test_a_strip_links_each_pixel_to_its_wiring_neighbours() -> None:
    nbrs = neighbors(line(10), 2)
    assert nbrs.idx[0].tolist() == [1, 2]
    assert sorted(nbrs.idx[5].tolist()) == [4, 6]  # float32 spacing breaks the tie


def test_too_few_points_pad_with_self_at_inf() -> None:
    nbrs = neighbors(np.array([[0.0, 0, 0], [1.0, 0, 0]], np.float32), 3)
    assert nbrs.idx.tolist() == [[1, 0, 0], [0, 1, 1]]
    assert nbrs.dist[:, 0].tolist() == [1.0, 1.0]
    assert np.all(np.isinf(nbrs.dist[:, 1:]))
    assert np.all(nbrs.weight[:, 1:] == 0)
    assert neighbors(np.zeros((0, 3), np.float32), 4).idx.shape == (0, 4)


def test_duplicates_are_neighbours_at_distance_zero() -> None:
    nbrs = neighbors(np.array([[0.5, 0.5, 0.5]] * 3 + [[0.9, 0.5, 0.5]], np.float32), 2)
    assert nbrs.idx[0].tolist() == [1, 2]
    assert nbrs.dist[0].tolist() == [0.0, 0.0]


def test_knn_on_a_crowded_spot() -> None:
    """Hundreds of points at one spot crowd one cell, which halving the
    cells cannot split."""
    points = np.random.default_rng(3).random((900, 3), dtype=np.float32)
    points[:300] = points[0]
    points[300:340] = points[400]
    for k in (1, 6, 40):
        assert_brute(points, k)


@pytest.mark.parametrize("crowd", [0, 1000], ids=["uniform", "1000-at-one-spot"])
def test_building_5000_points_is_far_below_brute_force(crowd: int) -> None:
    """Brute force took 392 ms at N = 5000 (research note 03, §2). The grid
    hash measures about 10 ms uniform and 20 ms with a crowded spot; the bar
    is half the brute-force time, best of three, so a loaded machine does not
    fail it."""
    points = np.random.default_rng(1).random((5000, 3), dtype=np.float32)
    points[:crowd] = 0.37
    best = np.inf
    for _ in range(3):
        start = time.perf_counter()
        neighbors(points, 6)
        best = min(best, time.perf_counter() - start)
    assert best < 0.196


def test_neighbors_are_read_only_values() -> None:
    idx = np.array([[1], [0]], np.int32)
    nbrs = Neighbors(idx, np.ones((2, 1), np.float32))
    assert nbrs.k == 1
    assert not nbrs.idx.flags.writeable and not nbrs.weight.flags.writeable
    assert idx.flags.writeable  # the caller's array is copied, not frozen


def test_neighbors_refusals_name_the_fix() -> None:
    with pytest.raises(ValueError, match=r"idx and dist must both be \(N, k\)"):
        Neighbors(np.zeros((3, 2), np.int32), np.zeros((3, 1), np.float32))
    with pytest.raises(ValueError, match="idx must index the 2 points, got values from 0 to 5"):
        Neighbors(np.array([[5], [0]], np.int32), np.zeros((2, 1), np.float32))
    with pytest.raises(ValueError, match="k must be 1 or more, got 0"):
        neighbors(line(4), 0)
    with pytest.raises(ValueError, match=r"u must be \(4,\) for this graph, got \(3,\)"):
        laplacian(np.zeros(3), neighbors(line(4), 1))


def test_steps_refuse_settings_past_their_stable_limit() -> None:
    nbrs = neighbors(line(8), 2)
    u = np.zeros(8, np.float32)
    with pytest.raises(ValueError, match=r"diffuse needs a rate in \[0, 1\] to stay stable, got 1.5; take more steps"):
        diffuse(u, nbrs, 1.5)
    with pytest.raises(ValueError, match=r"wave_step needs a damping in \[0, 1\], got -0.1"):
        wave_step(u, u, nbrs, 1.0, damping=-0.1)
    with pytest.raises(ValueError, match="wave_step needs c below 1.396 at damping 0.05 to stay stable, got c=1.4"):
        wave_step(u, u, nbrs, 1.4, damping=0.05)
    with pytest.raises(ValueError, match="gray_scott_step needs dt at most 0.9735 at these rates to stay stable, got"):
        gray_scott_step(u + 1.0, u, nbrs, dt=1.0)


graphs = st.tuples(clouds(), st.integers(1, 6)).map(lambda c: neighbors(*c))


@st.composite
def graph_and_values(draw):
    nbrs = draw(graphs)
    u = draw(arrays(np.float32, len(nbrs.idx), elements=st.floats(-1, 1, width=32)))
    return nbrs, u


@given(graph_and_values(), st.floats(0, 1))
def test_diffusion_conserves_the_total_and_stays_in_range(case, rate: float) -> None:
    nbrs, u = case
    out = diffuse(u, nbrs, rate)
    assert out.dtype == np.float32
    assert float(out.sum(dtype=np.float64)) == pytest.approx(float(u.sum(dtype=np.float64)), abs=1e-4)
    assert out.min() >= u.min() - 1e-6 and out.max() <= u.max() + 1e-6


@given(graph_and_values())
def test_laplacian_sums_to_zero_and_ignores_a_constant(case) -> None:
    nbrs, u = case
    assert abs(float(laplacian(u, nbrs).sum(dtype=np.float64))) < 1e-4
    assert np.all(laplacian(np.full(len(u), 0.7, np.float32), nbrs) == 0)


# A strip and a 4-neighbour panel bring L's eigenvalues closest to -2: the
# graphs on which an explicit step diverges first.
WORST = [pytest.param(line(200), 2, id="strip"), pytest.param(grid(16, 16), 4, id="panel")]


@pytest.mark.parametrize("points, k", WORST)
@pytest.mark.parametrize("damping", [0.0, 0.2, 0.5, 1.0])
def test_wave_stays_bounded_just_below_the_limit(points, k: int, damping: float) -> None:
    nbrs = neighbors(points, k)
    u = np.zeros(len(points), np.float32)
    u[len(points) // 2] = 1.0
    prev = u.copy()
    c = 0.999 * math.sqrt(2.0 - damping)
    for _ in range(2000):
        u, prev = wave_step(u, prev, nbrs, c, damping), u
    assert u.dtype == np.float32
    assert np.abs(u).max() < 2.0
    # Undamped, the total's float32 rounding error grows with the square of the step count.
    assert float(u.sum(dtype=np.float64)) == pytest.approx(1.0, abs=1e-3 if damping else 0.05)


def test_damping_calms_the_wave() -> None:
    nbrs = neighbors(grid(10, 10), 4)
    u = np.zeros(100, np.float32)
    u[55] = 1.0
    prev = u.copy()
    for _ in range(300):
        u, prev = wave_step(u, prev, nbrs, 1.0, damping=0.05), u
    assert np.abs(u - u.mean()).max() < 1e-3


def test_gray_scott_rest_state_is_fixed_and_spots_grow() -> None:
    nbrs = neighbors(grid(24, 24), 8)
    a, b = np.ones(576, np.float32), np.zeros(576, np.float32)
    a2, b2 = gray_scott_step(a, b, nbrs)
    assert a2.dtype == b2.dtype == np.float32
    assert np.array_equal(a2, a) and np.array_equal(b2, b)
    b[[300, 301, 324, 325]] = 1.0
    for _ in range(200):
        a, b = gray_scott_step(a, b, nbrs)
    assert np.isfinite(b).all() and (b > 0.1).sum() > 4


@pytest.mark.parametrize("points, k", [*WORST, pytest.param(lattice(10), 6, id="lattice")])
def test_gray_scott_defaults_stay_bounded(points, k: int) -> None:
    """Sims' dt = 1 diverged here within 200 steps from a one-pixel seed."""
    nbrs = neighbors(points, k)
    a, b = np.ones(len(points), np.float32), np.zeros(len(points), np.float32)
    b[len(points) // 2] = 1.0
    for _ in range(600):
        a, b = gray_scott_step(a, b, nbrs)
    assert np.all((a >= 0) & (a <= 1.0)) and np.all((b >= 0) & (b <= 1.0))


def test_a_wiring_graph_works_like_a_built_one() -> None:
    """Any (idx, dist) is a graph: a strip's wiring, each pixel to the next."""
    n = 6
    idx = np.array([[min(i + 1, n - 1)] for i in range(n)], np.int32)
    wiring = Neighbors(idx, np.where(idx[:, :1] == np.arange(n)[:, None], np.inf, 1.0))
    u = np.zeros(n, np.float32)
    u[0] = 1.0
    out = diffuse(u, wiring, 1.0)
    assert out.sum() == pytest.approx(1.0)
    assert out[1] > 0
