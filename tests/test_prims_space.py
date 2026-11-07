"""Tests for the coordinate ops (src/pewpew/fx/prims/space.py): what each
op keeps (distances, idempotence, round trips) and what it passes through."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pewpew.fx.prims import space
from pewpew.fx.prims.vec import MID
from prim_points import points, radius

angle = st.floats(-10.0, 10.0)
planes = st.sampled_from(["xy", "xz", "yz"])

ATOL = 2e-6


def _close(a, b, atol: float = ATOL) -> bool:
    return all(np.allclose(x, y, atol=atol, rtol=0) for x, y in zip(a, b))


def _float32(p) -> bool:
    return all(c.dtype == np.float32 for c in p)


@given(points, angle, planes)
def test_rotate_keeps_distances_and_undoes(p, a: float, plane) -> None:
    turned = space.rotate(p, a, plane)
    assert _float32(turned)
    assert np.allclose(radius(turned), radius(p), atol=ATOL)
    assert _close(space.rotate(turned, -a, plane), p, atol=4 * ATOL)


@given(points, angle, st.tuples(*(st.floats(-1, 1) for _ in range(3))).filter(lambda v: math.hypot(*v) > 0.1))
def test_rotate_about_keeps_distances(p, a: float, axis) -> None:
    turned = space.rotate_about(p, a, axis)
    assert _float32(turned)
    assert np.allclose(radius(turned), radius(p), atol=4 * ATOL)


@given(points, angle)
def test_rotate_about_z_is_rotate_in_xy(p, a: float) -> None:
    assert _close(space.rotate_about(p, a, (0.0, 0.0, 1.0)), space.rotate(p, a, "xy"), atol=4 * ATOL)


@given(points, planes)
def test_polar_round_trips_and_turns_are_in_0_1(p, plane) -> None:
    q = space.polar(p, plane)
    i, j = "xyz".index(plane[0]), "xyz".index(plane[1])
    assert np.all((q[j] >= 0.0) & (q[j] < 1.0))
    assert np.all(q[i] >= 0.0)
    assert _close(space.cartesian(q, plane), p, atol=4 * ATOL)


@given(points, st.integers(1, 12), planes)
def test_kaleid_keeps_radius_lands_in_the_wedge_and_folds_once(p, sides: int, plane) -> None:
    folded = space.kaleid(p, sides, plane)
    assert _float32(folded)
    assert np.allclose(radius(folded, plane), radius(p, plane), atol=4 * ATOL)
    q = space.polar(folded, plane)
    r, turn = q["xyz".index(plane[0])], q["xyz".index(plane[1])]
    # Turns wrap at 1, so a point on the wedge's first edge may read just below 1.
    in_wedge = (turn <= 0.5 / sides + 1e-5) | (turn > 1 - 1e-5) | (r < 1e-4)
    assert np.all(in_wedge)
    assert _close(space.kaleid(folded, sides, plane), folded, atol=8 * ATOL)


@given(points, st.sampled_from(["x", "y", "z", "xz", "xyz"]))
def test_mirror_folds_once(p, axes: str) -> None:
    once = space.mirror(p, axes)
    assert all(a.tobytes() == b.tobytes() for a, b in zip(space.mirror(once, axes), once))
    for a in axes:
        assert np.all(once["xyz".index(a)] >= np.float32(0.5))


@given(points, st.floats(0.05, 2.0))
def test_repeat_folds_once_into_one_cell(p, period: float) -> None:
    """A second repeat moves no point, except that a point on the cell's
    edge may hop to the opposite edge, one period away: the same place."""
    once = space.repeat(p, period)
    for c, m in zip(once, MID):
        assert np.all(np.abs(c - np.float32(m)) <= period / 2 + 1e-6)
    for again, before in zip(space.repeat(once, period), once):
        gap = np.abs(again.astype(np.float64) - before) % period
        assert np.all(np.minimum(gap, period - gap) <= 4 * ATOL)


@given(points, st.floats(-20, 20), st.sampled_from(["x", "y", "z"]))
def test_twist_keeps_the_axis_coordinate_and_the_distance_from_it(p, rate: float, axis) -> None:
    twisted = space.twist(p, rate, axis)
    assert twisted["xyz".index(axis)] is p["xyz".index(axis)]
    around = "xyz".replace(axis, "")
    assert np.allclose(radius(twisted, around), radius(p, around), atol=4 * ATOL)


@given(points)
def test_tunnel_depth_is_one_over_the_radius(p) -> None:
    depth = space.tunnel(p, "xy")[0]
    r = np.maximum(np.hypot(p[0].astype(np.float64) - 0.5, p[1].astype(np.float64) - 0.5), 1e-3)
    assert np.allclose(depth, 1.0 / r, rtol=1e-5)


@given(points, st.floats(0.25, 4.0), st.tuples(*(st.floats(-1, 1) for _ in range(3))))
def test_scale_and_translate_undo(p, factor: float, offset) -> None:
    assert _close(space.scale(space.scale(p, factor), 1.0 / factor), p, atol=8 * ATOL)
    back = tuple(-o for o in offset)
    assert _close(space.translate(space.translate(p, offset), back), p, atol=4 * ATOL)


def test_untouched_axes_pass_through_as_the_same_array() -> None:
    p = tuple(np.linspace(0, 1, 5, dtype=np.float32) for _ in range(3))
    assert space.rotate(p, 0.3, "xy")[2] is p[2]
    assert space.mirror(p, "y")[0] is p[0]
    assert space.translate(p, (0.1, 0.0, 0.0))[1] is p[1]
    assert space.scale(p, (2.0, 1.0, 1.0))[2] is p[2]


def test_ops_work_on_two_axis_points() -> None:
    p = (np.linspace(0, 1, 5, dtype=np.float32), np.zeros(5, np.float32))
    assert len(space.kaleid(p, 4)) == 2
    assert len(space.rotate(p, 1.0)) == 2
    assert all(a.tobytes() == b.tobytes() for a, b in zip(space.repeat(p, 0.25), space.repeat(p, 0.25, "xy")))


def test_refusals_name_the_fix() -> None:
    p2 = (np.zeros(3, np.float32), np.zeros(3, np.float32))
    with pytest.raises(ValueError, match="axis 'z' is not one of 'xy' for a 2-axis point"):
        space.rotate(p2, 1.0, "xz")
    with pytest.raises(ValueError, match="plane 'xx' is not one of 'xy', 'xz', 'yz'"):
        space.rotate(p2, 1.0, "xx")  # type: ignore[arg-type]  # on purpose
    with pytest.raises(ValueError, match="axis 'z' is not one of 'xy' for a 2-axis point"):
        space.twist(p2, 1.0, "x")
    with pytest.raises(ValueError, match="kaleid needs 1 or more sides, got 0"):
        space.kaleid(p2, 0)
    with pytest.raises(ValueError, match="repeat needs a period above 0"):
        space.repeat(p2, 0.0, "x")
    with pytest.raises(ValueError, match="rotate_about takes points of 3 axes"):
        space.rotate_about(p2, 1.0)
