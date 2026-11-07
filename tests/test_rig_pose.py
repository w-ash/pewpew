"""Quaternions, matrices and frame conversion (pewpew.rig.pose)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pewpew.rig.models import canonical_quat
from pewpew.rig.pose import (
    aim,
    anchor_frame,
    compose,
    from_mvr,
    from_three,
    matrix_to_quat,
    quat_to_matrix,
    rot_x,
    rot_y,
    rot_z,
    to_mvr,
    to_three,
)


def random_rotations(k: int) -> list[np.ndarray]:
    rng = np.random.default_rng(7)
    out = []
    for q in rng.normal(size=(k, 4)):
        out.append(quat_to_matrix(q / np.linalg.norm(q)))
    return out


def test_matrix_quat_round_trip_with_w_nonnegative():
    special = [np.eye(3), rot_x(180), rot_y(180), rot_z(180), rot_x(90) @ rot_z(180)]
    for r in special + random_rotations(200):
        q = matrix_to_quat(r)
        assert q[3] >= 0.0
        assert abs(math.sqrt(sum(c * c for c in q)) - 1.0) < 1e-12
        np.testing.assert_allclose(quat_to_matrix(q), r, atol=1e-12)


def test_canonical_quat_flips_sign_and_checks_the_norm():
    assert canonical_quat((0, 0, 0, -1)) == (0.0, 0.0, 0.0, 1.0)
    assert canonical_quat((0, -1, 0, 0)) == (0.0, 1.0, 0.0, 0.0)
    assert canonical_quat((0, 0, 0.7071068, 0.7071068))[2] == pytest.approx(math.sqrt(0.5), abs=1e-15)
    with pytest.raises(ValueError, match="not within"):
        canonical_quat((0, 0, 0, 1.01))


def test_aim_at_theta_zero_gives_the_ring_basis():
    # docs/studio/domain-model.md:200: at θ = 0 the aim rule gives the ring basis.
    a = math.radians(30)
    x = np.array([0.0, 0.0, 1.0])
    y = np.array([math.cos(a), math.sin(a), 0.0])
    np.testing.assert_allclose(aim(y), np.column_stack([x, y, np.cross(x, y)]), atol=1e-15)


def test_aim_is_orthonormal_right_handed_and_handles_vertical():
    for axis in ([0, 1, 0], [0, -1, 0], [1, 2, 3], [0, 0, 1], [0.0005, 1, 0]):
        r = aim(axis, roll_deg=20)
        np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-12)
        assert np.linalg.det(r) == pytest.approx(1.0)
        np.testing.assert_allclose(r[:, 1], np.asarray(axis) / np.linalg.norm(axis), atol=1e-12)
    with pytest.raises(ValueError):
        aim([0, 0, 0])


def test_three_order_is_column_major():
    m = compose((1.0, 2.0, 3.0), rot_z(90))
    e = to_three(m)
    assert e[12:15] == (1.0, 2.0, 3.0)
    assert e[15] == 1.0
    np.testing.assert_array_equal(from_three(e), m)


def test_mvr_is_z_up_millimeters_and_round_trips():
    m = compose((1.0, 2.0, 3.0), aim([1, 1, 0], 15))
    u, v, w, o = to_mvr(m)
    assert o == pytest.approx((1000.0, -3000.0, 2000.0))
    r = np.column_stack([u, v, w])
    assert np.linalg.det(r) == pytest.approx(1.0)
    up = compose((0, 0, 0), np.eye(3))
    assert to_mvr(up)[:3] == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    # C converts the fixture frame too, so its +y is MVR's w row. Aimed at world
    # +z (toward the viewer), +y lands on MVR -y.
    assert to_mvr(compose((0, 0, 0), aim([0, 0, 1])))[2] == pytest.approx((0.0, -1.0, 0.0))
    np.testing.assert_allclose(from_mvr(to_mvr(m)), m, atol=1e-12)


def test_anchor_frame_turns_end_a_end_for_end():
    np.testing.assert_array_equal(anchor_frame((0, 0.5, 0), (0, 1, 0))[:3, :3], np.eye(3))
    np.testing.assert_array_equal(anchor_frame((0, -0.5, 0), (0, -1, 0))[:3, :3], np.diag([-1.0, -1.0, 1.0]))
