"""Rotations, placements and frame conversion, in NumPy only.

World frame: meters, y up, right-handed, the same as glTF
(https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units).
Quaternions are xyzw, the order of three.js `Quaternion.toJSON()`
(https://threejs.org/docs/pages/Quaternion.html), stored with w >= 0.
Matrices leave as 16 floats in column-major order, the order of three.js
`Matrix4.elements` (https://threejs.org/docs/pages/Matrix4.html).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from pewpew.rig.models import Quat, canonical_quat

#: Rz(180°), exact. It turns a fixture end for end and keeps its facing.
FLIP_Z = np.diag([-1.0, -1.0, 1.0])

#: World (y up) to MVR (z up): C·(x, y, z) = (x, -z, y); det C = +1.
MVR_C = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
MVR_MM_PER_M = 1000.0

# Above this |y·Y|, `aim` takes world +Z as its reference instead of +Y.
_AIM_PARALLEL = 0.999


def rot_x(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rot_y(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rot_z(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def quat_to_matrix(q: Sequence[float]) -> np.ndarray:
    """The 3x3 rotation of a unit quaternion (x, y, z, w)."""
    x, y, z, w = canonical_quat(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def matrix_to_quat(r: np.ndarray) -> Quat:
    """The canonical quaternion (x, y, z, w) of a 3x3 rotation matrix.

    The branch structure follows three.js `Quaternion.setFromRotationMatrix`
    (https://threejs.org/docs/pages/Quaternion.html).
    """
    m = np.asarray(r, dtype=np.float64)
    m11, m12, m13 = m[0]
    m21, m22, m23 = m[1]
    m31, m32, m33 = m[2]
    trace = m11 + m22 + m33
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        q = ((m32 - m23) * s, (m13 - m31) * s, (m21 - m12) * s, 0.25 / s)
    elif m11 > m22 and m11 > m33:
        s = 2.0 * math.sqrt(1.0 + m11 - m22 - m33)
        q = (0.25 * s, (m12 + m21) / s, (m13 + m31) / s, (m32 - m23) / s)
    elif m22 > m33:
        s = 2.0 * math.sqrt(1.0 + m22 - m11 - m33)
        q = ((m12 + m21) / s, 0.25 * s, (m23 + m32) / s, (m13 - m31) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + m33 - m11 - m22)
        q = ((m13 + m31) / s, (m23 + m32) / s, 0.25 * s, (m21 - m12) / s)
    norm = math.sqrt(sum(c * c for c in q))
    return canonical_quat(c / norm for c in q)


def unit(v: ArrayLike) -> np.ndarray:
    """`v` at length 1; raises ValueError if `v` is zero or not finite.

    `v` is first divided by its largest |component|, so the norm cannot
    underflow or overflow.
    """
    arr = np.asarray(v, dtype=np.float64)
    big = float(np.abs(arr).max())
    if not (0.0 < big < math.inf):
        raise ValueError("a direction must be nonzero and finite")
    arr = arr / big
    return arr / np.linalg.norm(arr)


def aim(axis: ArrayLike, roll_deg: float = 0.0) -> np.ndarray:
    """The rotation whose +y is `axis`, rolled by `roll_deg` about it.

    +z is the reference direction (world +Y, or world +Z when the axis is
    within about 2.6° of vertical) with its component along +y removed, and
    +x = +y × +z (docs/studio/domain-model.md:185-189).
    """
    y = unit(axis)
    ref = np.array([0.0, 1.0, 0.0])
    if abs(float(y @ ref)) > _AIM_PARALLEL:
        ref = np.array([0.0, 0.0, 1.0])
    z = ref - (ref @ y) * y
    z = z / np.linalg.norm(z)
    x = np.cross(y, z)
    return np.column_stack([x, y, z]) @ rot_y(roll_deg)


def rotation(pose: Any) -> np.ndarray:
    """The 3x3 rotation of a `Pose`: from its quaternion, its aim, or identity."""
    if pose.quat_xyzw is not None:
        return quat_to_matrix(pose.quat_xyzw)
    if pose.aim is not None:
        return aim(pose.aim.axis, pose.aim.roll_deg)
    return np.eye(3)


def compose(position: ArrayLike, r: np.ndarray) -> np.ndarray:
    """The 4x4 matrix T(position) · R."""
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = np.asarray(position, dtype=np.float64)
    return m


def pose_matrix(pose: Any) -> np.ndarray:
    """The 4x4 matrix of a `Pose`."""
    return compose(pose.position_m, rotation(pose))


def to_three(m: np.ndarray) -> tuple[float, ...]:
    """A 4x4 matrix as 16 floats in three.js `Matrix4.elements` order."""
    return tuple(float(v) + 0.0 for v in np.asarray(m, dtype=np.float64).ravel(order="F"))


def from_three(elements: Sequence[float]) -> np.ndarray:
    """The 4x4 matrix of 16 floats in three.js `Matrix4.elements` order."""
    return np.asarray(elements, dtype=np.float64).reshape(4, 4, order="F")


def to_mvr(m: np.ndarray) -> tuple[tuple[float, float, float], ...]:
    """A world matrix as an MVR `Matrix`: rows u, v, w, o; z up, millimeters.

    MVR is right-handed, z up, 1 unit = 1 mm, with a 4x3 matrix written
    u1,u2,u3 / v1,v2,v3 / w1,w2,w3 / o1,o2,o3
    (https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L805-L823).
    u, v and w are taken as the columns of the rotation and o as the offset;
    the spec gives only the order, so the column reading is an inference.
    """
    m = np.asarray(m, dtype=np.float64)
    r = MVR_C @ m[:3, :3] @ MVR_C.T
    o = MVR_MM_PER_M * (MVR_C @ m[:3, 3])
    rows = (r[:, 0], r[:, 1], r[:, 2], o)
    return tuple(tuple(float(c) + 0.0 for c in row) for row in rows)  # type: ignore[return-value]


def from_mvr(uvwo: Sequence[Sequence[float]]) -> np.ndarray:
    """The world matrix of an MVR `Matrix` (rows u, v, w, o); the inverse of `to_mvr`."""
    u, v, w, o = (np.asarray(row, dtype=np.float64) for row in uvwo)
    r = MVR_C.T @ np.column_stack([u, v, w]) @ MVR_C
    return compose(MVR_C.T @ o / MVR_MM_PER_M, r)


def anchor_frame(at: ArrayLike, direction: ArrayLike) -> np.ndarray:
    """The 4x4 frame of an attachment on an anchor, in the host's frame.

    The origin is the anchor point, +y points along `direction`, and +z is the
    host's +z with its component along +y removed (host +x when the anchor
    points along z). +x = +y × +z.
    """
    y = unit(direction)
    ref = np.array([0.0, 0.0, 1.0])
    if abs(float(y @ ref)) > _AIM_PARALLEL:
        ref = np.array([1.0, 0.0, 0.0])
    z = ref - (ref @ y) * y
    z = z / np.linalg.norm(z)
    return compose(at, np.column_stack([np.cross(y, z), y, z]))
