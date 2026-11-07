"""Tests for field sampling, advection, projections (src/pewpew/fx/prims/
sample.py) and deposit (grid.py): interpolation reads the nodes, stays
between them and is exact on linear fields; deposit is its adjoint."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from pewpew.fx.prims import grid, sample
from pewpew.fx.prims.sample import advect, stencil
from prim_points import coord, points

value = st.floats(-4.0, 4.0, width=32)
shapes = st.lists(st.integers(1, 7), min_size=1, max_size=3).map(tuple)
modes = st.sampled_from(["clamp", "wrap"])


@st.composite
def field_and_points(draw, n_points: int = 20):
    """A field of 1 to 3 spatial axes, points for it, and an edge mode per axis."""
    shape = draw(shapes)
    field = draw(arrays(np.float32, shape, elements=value))
    p = tuple(draw(arrays(np.float32, n_points, elements=coord)) for _ in shape)
    edge = tuple(draw(modes) for _ in shape)
    return field, p, edge


def _node_coords(shape, edge, index):
    """The coordinates, in x, y, z order, of the node at field `index`."""
    return tuple(
        np.float32(i / n if mode == "wrap" else i / max(n - 1, 1))
        for i, n, mode in zip(reversed(index), reversed(shape), edge)
    )


@pytest.mark.parametrize("edge", ["clamp", "wrap"])
def test_a_nan_point_reads_as_0_on_every_platform(edge) -> None:
    """NaN cast to an index is 0 on arm64 and the lowest integer on x86-64,
    which indexes out of range; the suite's warnings-as-errors also catches
    a NaN that reaches the cast."""
    field = np.arange(16, dtype=np.float32).reshape(4, 4)
    nan, zero = np.array([np.nan], np.float32), np.array([0.0], np.float32)
    assert sample.sample(field, (nan, nan), edge).tolist() == sample.sample(field, (zero, zero), edge).tolist()
    assert grid.deposit((nan, nan), np.ones(1, np.float32), (4, 4), edge)[0, 0] == 1.0


@given(field_and_points(), st.data())
def test_sample_at_a_node_reads_the_node(case, data) -> None:
    field, _, edge = case
    index = tuple(data.draw(st.integers(0, n - 1)) for n in field.shape)
    p = tuple(np.array([c]) for c in _node_coords(field.shape, edge, index))
    assert sample.sample(field, p, edge)[0] == pytest.approx(field[index], abs=1e-5)


@given(field_and_points())
def test_sample_stays_within_the_field(case) -> None:
    field, p, edge = case
    out = sample.sample(field, p, edge)
    assert out.dtype == np.float32
    assert out.shape == p[0].shape
    assert np.all(out >= field.min() - 1e-5) and np.all(out <= field.max() + 1e-5)


@given(field_and_points())
def test_stencil_weights_sum_to_one(case) -> None:
    field, p, edge = case
    total = sum(w for _, w in stencil(field.shape, p, edge))
    assert np.allclose(total, 1.0, atol=1e-6)


@given(field_and_points())
def test_wrap_has_period_one(case) -> None:
    field, p, _ = case
    edge = ("wrap",) * len(p)
    shifted = tuple(c + np.float32(1.0) for c in p)
    assert np.allclose(sample.sample(field, shifted, edge), sample.sample(field, p, edge), atol=2e-5)


@given(arrays(np.float32, 30, elements=st.floats(0, 1, width=32)), st.tuples(value, value, value, value))
def test_trilinear_is_exact_on_a_linear_field(x, coef) -> None:
    a, b, c, d = coef
    axis = [np.linspace(0, 1, n) for n in (3, 4, 5)]  # z, y, x node coordinates
    zs, ys, xs = np.meshgrid(*axis, indexing="ij")
    field = (a * xs + b * ys + c * zs + d).astype(np.float32)
    y, z = np.roll(x, 7), np.roll(x, 13)
    expected = a * x.astype(np.float64) + b * y + c * z + d
    assert np.allclose(sample.sample(field, (x, y, z)), expected, atol=1e-4)


def test_clamp_reads_the_edge_outside_the_world() -> None:
    field = np.arange(12, dtype=np.float32).reshape(3, 4)
    out = sample.sample(field, (np.array([-1.0, 2.0], np.float32), np.array([-1.0, 2.0], np.float32)))
    assert out.tolist() == [field[0, 0], field[-1, -1]]


def test_channels_sample_per_channel() -> None:
    rng = np.random.default_rng(0)
    field = rng.random((5, 6, 3), dtype=np.float32)
    p = tuple(rng.random(9, dtype=np.float32) for _ in range(2))
    rgb = sample.sample(field, p)
    assert rgb.shape == (9, 3)
    for ch in range(3):
        assert np.array_equal(rgb[:, ch], sample.sample(field[..., ch], p))


def test_advect_with_no_flow_keeps_the_field() -> None:
    field = np.random.default_rng(1).random((6, 7), dtype=np.float32)
    for edge in ("clamp", "wrap"):
        assert np.allclose(advect(field, (0.0, 0.0), 1.0, edge), field, atol=1e-6)


def test_advect_one_cell_per_step_rolls_a_wrapped_field() -> None:
    field = np.random.default_rng(2).random((4, 8), dtype=np.float32)
    moved = advect(field, (1.0 / 8, 0.0), 1.0, "wrap")
    assert moved.shape == field.shape and moved.dtype == np.float32
    assert np.allclose(moved, np.roll(field, 1, axis=1), atol=1e-5)


def test_advect_takes_a_velocity_field() -> None:
    field = np.random.default_rng(3).random((5, 5), dtype=np.float32)
    vx = np.full((5, 5), 0.25, np.float32)
    assert np.allclose(advect(field, (vx, 0.0), 1.0), advect(field, (0.25, 0.0), 1.0))


@given(field_and_points(), st.data())
def test_deposit_is_the_adjoint_of_sample(case, data) -> None:
    """<deposit(w), f> == <w, sample(f)> for every field f and weights w:
    the two share one stencil."""
    field, p, edge = case
    w = data.draw(arrays(np.float32, len(p[0]), elements=st.floats(0, 2, width=32)))
    dep = grid.deposit(p, w, field.shape, edge)
    assert dep.dtype == np.float32 and dep.shape == field.shape
    lhs = float((dep.astype(np.float64) * field).sum())
    rhs = float((w.astype(np.float64) * sample.sample(field, p, edge)).sum())
    assert lhs == pytest.approx(rhs, rel=1e-4, abs=1e-3)
    assert float(dep.sum()) == pytest.approx(float(w.sum()), rel=1e-5, abs=1e-5)


def test_deposit_of_an_m_by_3_array() -> None:
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.5, 0.5]], np.float32)
    dep = grid.deposit(tuple(pts.T), [1.0, 2.0, 4.0], (3, 3, 3))
    assert dep[0, 0, 0] == 1.0 and dep[2, 2, 2] == 2.0 and dep[1, 1, 1] == 4.0


def test_one_array_of_points_is_refused() -> None:
    """Its rows would read as axes: three points at (0, 0, 1) would land on
    two wrong corners."""
    pts = np.array([[0.0, 0.0, 1.0]] * 3, np.float32)
    with pytest.raises(TypeError, match=r"one array per axis, such as \(x, y\), got one array of shape \(3, 3\); "):
        grid.deposit(pts, [1.0, 1.0, 1.0], (2, 2, 2))  # type: ignore[arg-type]  # on purpose
    with pytest.raises(TypeError, match=r"pass tuple\(points.T\) for an \(N, D\) array"):
        sample.sample(np.zeros((2, 2), np.float32), np.zeros(2, np.float32))  # type: ignore[arg-type]  # on purpose


@given(points, st.sampled_from(["x", "y", "z"]))
def test_projections_give_texture_coordinates(p, axis) -> None:
    u, v = sample.cylindrical(p, axis)
    assert np.all((u >= 0) & (u < 1))
    assert v is p["xyz".index(axis)]
    u, v = sample.spherical(p)
    assert u.dtype == v.dtype == np.float32
    assert np.all((u >= 0) & (u < 1)) and np.all((v >= 0) & (v <= 1))
    assert sample.planar(p, "xz") == (p[0], p[2])


def test_spherical_v_runs_from_the_bottom_pole_to_the_top() -> None:
    p = (np.full(3, 0.5, np.float32), np.array([0.0, 0.5, 1.0], np.float32), np.full(3, 0.5, np.float32))
    assert sample.spherical(p)[1].tolist() == pytest.approx([0.0, 0.5, 1.0], abs=1e-6)


def test_refusals_name_the_fix() -> None:
    field = np.zeros((3, 4), np.float32)
    one = np.zeros(1, np.float32)
    with pytest.raises(ValueError, match=r"spatial shape \(3, 4\) needs points of 2 axes, got 3"):
        stencil(field.shape, (one, one, one))
    with pytest.raises(ValueError, match="edge must be 'clamp', 'wrap' or one of them per axis"):
        sample.sample(field, (one, one), "mirror")  # type: ignore[arg-type]  # on purpose
    with pytest.raises(ValueError, match="edge must be"):
        sample.sample(field, (one, one), ("wrap",))
