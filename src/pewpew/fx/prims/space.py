"""Coordinate ops: pure maps from a `Vec` of points to a new `Vec`.

Each op changes only the axes it names and passes the others through as the
same array, so treat every result as read-only. Ops that turn or fold space
do it about `center`, by default `MID`, the middle of the normalized world.
A point has 2 or 3 axes; a plane or axis must be one the point has.

These ops move the points. A field sampled at the moved points looks moved
the other way: `rotate(p, a)` turns what is sampled next by -a.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from pewpew.fx.prims.vec import (
    AROUND,
    AXES,
    F32,
    MID,
    Axis,
    Center,
    Plane,
    Vec,
    VecLike,
    axis_index,
    per_axis,
    plain,
    plain_center,
    plane_axes,
    vec,
)
from pewpew.kit import TWO_PI


def _with(p: Vec, changes: dict[int, F32]) -> Vec:
    """`p` with the axes in `changes` replaced."""
    return tuple(changes.get(i, c) for i, c in enumerate(p))


def _turn_pair(p: Vec, i: int, j: int, cos: F32 | float, sin: F32 | float, center: Center) -> Vec:
    """Rotate axes i and j of `p` about `center`, from axis i toward axis j."""
    a, b = p[i] - center[i], p[j] - center[j]
    return _with(p, {i: a * cos - b * sin + center[i], j: a * sin + b * cos + center[j]})


def translate(p: VecLike, offset: Sequence[float]) -> Vec:
    """Add `offset` (one value per axis) to the points."""
    q = vec(p)
    return _with(q, {i: c + o for i, (c, o) in enumerate(zip(q, plain(offset))) if o})


def scale(p: VecLike, factor: float | Sequence[float], center: Center = MID) -> Vec:
    """Multiply the points' distance from `center` by `factor` (one value,
    or one per axis). A factor above 1 shrinks what is sampled next."""
    q = vec(p)
    factors = per_axis(factor, len(q))
    return _with(q, {i: (c - m) * f + m for i, (c, f, m) in enumerate(zip(q, factors, plain_center(center))) if f != 1})


def rotate(p: VecLike, angle: float, plane: Plane = "xy", center: Center = MID) -> Vec:
    """Rotate the points by `angle` radians in `plane`, from its first axis
    toward its second. Distances from `center` do not change."""
    q = vec(p)
    i, j = plane_axes(plane, q)
    return _turn_pair(q, i, j, math.cos(angle), math.sin(angle), plain_center(center))


def rotate_about(p: VecLike, angle: float, axis: Sequence[float] = (0.0, 1.0, 0.0), center: Center = MID) -> Vec:
    """Rotate 3-axis points by `angle` radians about the direction `axis`
    through `center`, anticlockwise when the axis points at you (Rodrigues'
    rotation formula)."""
    q = vec(p)
    if len(q) != 3:
        raise ValueError(f"rotate_about takes points of 3 axes, got {len(q)}")
    norm = math.hypot(*axis)
    if norm == 0.0:
        raise ValueError("rotate_about needs a non-zero axis")
    kx, ky, kz = (a / norm for a in plain(axis))
    cos, sin = math.cos(angle), math.sin(angle)
    center = plain_center(center)
    x, y, z = (c - m for c, m in zip(q, center))
    along = (kx * x + ky * y + kz * z) * (1.0 - cos)
    return (
        x * cos + (ky * z - kz * y) * sin + kx * along + center[0],
        y * cos + (kz * x - kx * z) * sin + ky * along + center[1],
        z * cos + (kx * y - ky * x) * sin + kz * along + center[2],
    )


def polar(p: VecLike, plane: Plane = "xy", center: Center = MID) -> Vec:
    """Replace the two axes of `plane` with polar coordinates about
    `center`: the radius, and the turn in [0, 1) from the plane's first
    axis toward its second."""
    q = vec(p)
    i, j = plane_axes(plane, q)
    center = plain_center(center)
    a, b = q[i] - center[i], q[j] - center[j]
    turn = np.arctan2(b, a) * (1.0 / TWO_PI) % 1.0
    # A tiny negative angle rounds up to 1.0 in float32; it is the turn 0.
    return _with(q, {i: np.hypot(a, b), j: np.where(turn < 1.0, turn, np.float32(0.0))})


def cartesian(p: VecLike, plane: Plane = "xy", center: Center = MID) -> Vec:
    """The inverse of `polar`: read the axes of `plane` as (radius, turn)
    about `center` and return them as plain coordinates."""
    q = vec(p)
    i, j = plane_axes(plane, q)
    center = plain_center(center)
    angle = q[j] * TWO_PI
    return _with(q, {i: q[i] * np.cos(angle) + center[i], j: q[i] * np.sin(angle) + center[j]})


def kaleid(p: VecLike, sides: int, plane: Plane = "xy", center: Center = MID) -> Vec:
    """Fold `plane` into `sides` mirrored wedges about `center`: every
    point moves into the first half-wedge at the same radius. A second fold
    changes nothing."""
    if sides < 1:
        raise ValueError(f"kaleid needs 1 or more sides, got {sides}")
    q = polar(p, plane, center)
    j = plane_axes(plane, q)[1]
    wedge = 1.0 / sides
    a = q[j] % wedge
    return cartesian(_with(q, {j: np.minimum(a, wedge - a)}), plane, center)


def mirror(p: VecLike, axes: str = "x", center: Center = MID) -> Vec:
    """Fold each axis in `axes` (for example "xz") onto its high side of
    `center`: c + |x - c|. A second fold changes nothing."""
    q = vec(p)
    center = plain_center(center)
    changes = {}
    for a in axes:
        i = axis_index(a, q)
        changes[i] = np.abs(q[i] - center[i]) + center[i]
    return _with(q, changes)


def twist(p: VecLike, rate: float, axis: Axis = "y", center: Center = MID) -> Vec:
    """Turn the plane around `axis` (as `rotate` turns it) by `rate` radians
    per unit of distance from `center` along the axis, so each slice turns by
    its own angle."""
    q = vec(p)
    k = axis_index(axis, q)
    i, j = plane_axes(AROUND[axis], q)
    center = plain_center(center)
    angle = (q[k] - center[k]) * float(rate)
    return _turn_pair(q, i, j, np.cos(angle), np.sin(angle), center)


def tunnel(p: VecLike, plane: Plane = "xy", center: Center = MID, radius: float = 1e-3) -> Vec:
    """Replace the two axes of `plane` with the demo tunnel's depth 1/r and
    turn about `center` (Inigo Quilez, "Plane Deformations"). A radius below
    `radius` reads as `radius`, so the centre stays finite."""
    q = polar(p, plane, center)
    i, _ = plane_axes(plane, q)
    return _with(q, {i: 1.0 / np.maximum(q[i], np.float32(radius))})


def repeat(p: VecLike, period: float, axes: str | None = None, center: Center = MID) -> Vec:
    """Repeat space every `period` along each axis in `axes` (by default
    every axis of the point): each point moves into the cell of width
    `period` centred on `center` (x - period * round((x - c) / period)). A
    second repeat changes nothing."""
    if period <= 0.0:
        raise ValueError(f"repeat needs a period above 0, got {period}")
    q = vec(p)
    period, center = float(period), plain_center(center)
    changes = {}
    for a in AXES[: len(q)] if axes is None else axes:
        i = axis_index(a, q)
        d = q[i] - center[i]
        changes[i] = d - period * np.round(d * (1.0 / period)) + center[i]
    return _with(q, changes)
