"""Tests for the distance functions and operators (src/pewpew/fx/prims/
sdf.py): exact distances where the shape has one, and the bounds the smooth
operators keep."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from pewpew.fx.prims import sdf
from prim_points import points, radius

dists = st.integers(1, 30).flatmap(
    lambda n: st.tuples(*(arrays(np.float32, n, elements=st.floats(-2, 2, width=32)) for _ in range(2)))
)


@given(points, st.floats(0.0, 1.0))
def test_sphere_is_the_exact_distance(p, r: float) -> None:
    d = sdf.sphere(p, r)
    assert d.dtype == np.float32
    assert np.allclose(d, radius(p) - r, atol=1e-6)


def test_box_distance_inside_on_and_outside() -> None:
    x = np.array([0.5, 0.7, 0.9, 1.0], np.float32)
    mid = np.full(4, 0.5, np.float32)
    assert sdf.box((x, mid, mid), 0.2).tolist() == pytest.approx([-0.2, 0.0, 0.2, 0.3], abs=1e-6)
    corner = np.array([1.0], np.float32)
    assert sdf.box((corner, corner, corner), 0.2)[0] == pytest.approx(np.sqrt(3) * 0.3, abs=1e-6)


def test_box_takes_a_half_size_per_axis() -> None:
    mid = np.full(1, 0.5, np.float32)
    up = np.full(1, 0.9, np.float32)
    assert sdf.box((mid, up, mid), (0.1, 0.3, 0.1))[0] == pytest.approx(0.1, abs=1e-6)


def test_torus_is_hollow_along_its_ring() -> None:
    on_ring = (np.array([0.8], np.float32), np.array([0.5], np.float32), np.array([0.5], np.float32))
    assert sdf.torus(on_ring, 0.3, 0.1)[0] == pytest.approx(-0.1, abs=1e-6)
    centre = tuple(np.array([0.5], np.float32) for _ in range(3))
    assert sdf.torus(centre, 0.3, 0.1)[0] == pytest.approx(0.2, abs=1e-6)


@given(points)
def test_capsule_with_equal_ends_is_a_sphere(p) -> None:
    c = (0.5, 0.5, 0.5)
    assert np.allclose(sdf.capsule(p, c, c, 0.2), sdf.sphere(p, 0.2), atol=1e-6)


def test_capsule_measures_to_the_segment() -> None:
    p = (np.array([0.5, 0.5], np.float32), np.array([0.5, 1.5], np.float32), np.array([0.3, 0.0], np.float32))
    d = sdf.capsule(p, (0.5, 0.0, 0.0), (0.5, 1.0, 0.0), 0.1)
    assert d.tolist() == pytest.approx([0.2, 0.4], abs=1e-6)


def test_halfspace_is_negative_behind_the_plane() -> None:
    y = np.array([0.2, 0.5, 0.9], np.float32)
    zero = np.zeros(3, np.float32)
    assert sdf.halfspace((zero, y, zero), (0, 2, 0)).tolist() == pytest.approx([-0.3, 0.0, 0.4], abs=1e-6)


@given(dists, st.floats(0.0, 1.0))
def test_smooth_operators_stay_near_the_hard_ones(ab, k: float) -> None:
    a, b = ab
    u = sdf.union(a, b, k)
    assert u.dtype == np.float32
    assert np.all(u <= np.minimum(a, b) + 1e-6)
    assert np.all(u >= np.minimum(a, b) - k / 4 - 1e-6)
    i = sdf.intersect(a, b, k)
    assert np.all(i >= np.maximum(a, b) - 1e-6) and np.all(i <= np.maximum(a, b) + k / 4 + 1e-6)
    assert np.array_equal(sdf.subtract(a, b, k), sdf.intersect(a, -b, k))


@given(dists)
def test_zero_blend_is_the_hard_operator(ab) -> None:
    a, b = ab
    assert np.array_equal(sdf.union(a, b), np.minimum(a, b))
    assert np.array_equal(sdf.intersect(a, b), np.maximum(a, b))


def test_rounded_and_onion() -> None:
    d = np.array([-0.3, 0.0, 0.3], np.float32)
    assert sdf.rounded(d, 0.1).tolist() == pytest.approx([-0.4, -0.1, 0.2])
    assert sdf.onion(d, 0.1).tolist() == pytest.approx([0.2, -0.1, 0.2])


def test_refusals_name_the_fix() -> None:
    one = np.zeros(1, np.float32)
    with pytest.raises(ValueError, match="halfspace needs a non-zero normal"):
        sdf.halfspace((one, one), (0, 0))
    with pytest.raises(ValueError, match="torus takes points of 3 axes, got 2"):
        sdf.torus((one, one), 0.3, 0.1)


def test_a_polygon_touches_its_circle_at_the_corners_and_its_apothem_at_the_edges() -> None:
    a = np.array([0.0, np.pi / 5], np.float32)  # a corner, then the middle of an edge, of a pentagon
    p = (0.5 + 0.3 * np.cos(a), 0.5 + 0.3 * np.sin(a))
    d = sdf.polygon(p, 5, 0.3, "xy")
    assert d.dtype == np.float32
    np.testing.assert_allclose(d, [0.0, 0.3 - 0.3 * np.cos(np.pi / 5)], atol=1e-6)
    with pytest.raises(ValueError, match="3 or more sides"):
        sdf.polygon(p, 2, 0.3)


def test_coverage_is_one_inside_zero_outside_and_soft_between() -> None:
    d = np.array([-1.0, -0.1, 0.0, 0.1, 1.0], np.float32)
    np.testing.assert_array_equal(sdf.coverage(d, 0.0), [1, 1, 1, 0, 0])
    soft = sdf.coverage(d, 0.1)
    assert soft.dtype == np.float32 and soft[0] == 1.0 and soft[-1] == 0.0 and soft[2] == 0.5
    assert np.all(np.diff(soft) <= 0.0)
