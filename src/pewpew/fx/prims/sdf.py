"""Signed distance functions and the operators that combine them, after
Inigo Quilez's catalog (iquilezles.org/articles/distfunctions).

A distance is negative inside a shape, zero on its surface and positive
outside. Shapes sit at `center`, by default `MID`. To move, turn or repeat a
shape, move the points first with `pewpew.fx.prims.space`. The smooth
operators keep the sign right but not the exact distance, so use their
result for shading, not for ray marching.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import reduce

import numpy as np
import numpy.typing as npt

from pewpew.fx.prims.vec import F32, MID, Center, Plane, VecLike, length, per_axis, plain, plain_center, plane_axes, vec

_TINY = float(np.finfo(np.float32).tiny)


def sphere(p: VecLike, radius: float, center: Center = MID) -> F32:
    """A sphere (a circle for 2-axis points): |p - c| - r."""
    q = vec(p)
    return length([c - m for c, m in zip(q, plain_center(center))]) - np.float32(radius)


def box(p: VecLike, half: float | Sequence[float], center: Center = MID) -> F32:
    """An axis-aligned box with half-size `half` (one value, or one per
    axis): the exact distance, inside and out."""
    q = vec(p)
    d = [np.abs(c - m) - np.float32(h) for c, m, h in zip(q, plain_center(center), per_axis(half, len(q)))]
    outside = length([np.maximum(e, 0.0) for e in d])
    inside = np.minimum(reduce(np.maximum, d), 0.0)
    return outside + inside


def torus(p: VecLike, major: float, minor: float, plane: Plane = "xz", center: Center = MID) -> F32:
    """A torus whose ring of radius `major` lies in `plane`, with a tube of
    radius `minor`."""
    q = vec(p)
    if len(q) != 3:
        raise ValueError(f"torus takes points of 3 axes, got {len(q)}")
    i, j = plane_axes(plane, q)
    k = 3 - i - j
    center = plain_center(center)
    ring = length([q[i] - center[i], q[j] - center[j]]) - np.float32(major)
    return length([ring, q[k] - center[k]]) - np.float32(minor)


def capsule(p: VecLike, a: Sequence[float], b: Sequence[float], radius: float) -> F32:
    """A capsule: the points within `radius` of the segment from `a` to
    `b`."""
    q = vec(p)
    a, b = plain(a), plain(b)
    ab = [hi - lo for lo, hi in zip(a, b)]
    pa = [c - lo for c, lo in zip(q, a)]
    span = sum(e * e for e in ab)
    if span == 0.0:
        return length(pa) - np.float32(radius)
    along = np.clip(sum(x * e for x, e in zip(pa, ab)) * np.float32(1.0 / span), 0.0, 1.0)
    return length([x - along * np.float32(e) for x, e in zip(pa, ab)]) - np.float32(radius)


def polygon(p: VecLike, sides: int, radius: float, plane: Plane = "xy", center: Center = MID) -> F32:
    """A regular polygon of `sides` corners on a circle of `radius` in
    `plane`, a corner on the plane's first axis (a prism through 3-axis
    points): the distance along the nearest edge's normal, exact on the
    edges and inside, a little short past a corner."""
    if sides < 3:
        raise ValueError(f"a polygon has 3 or more sides, got {sides}")
    q = vec(p)
    i, j = plane_axes(plane, q)
    center = plain_center(center)
    a, b = q[i] - center[i], q[j] - center[j]
    sector = 2.0 * math.pi / sides
    angle = np.arctan2(b, a) % sector - sector * 0.5
    return np.hypot(a, b) * np.cos(angle) - np.float32(radius * math.cos(math.pi / sides))


def coverage(d: npt.ArrayLike, soft: float) -> F32:
    """How much of each point a shape of distance `d` covers: 1 inside, 0
    outside, with a smooth step `soft` wide on each side of the surface
    (a hard edge for a `soft` of 0)."""
    d32 = np.asarray(d, dtype=np.float32)
    if soft < _TINY:
        return (d32 <= 0.0).astype(np.float32)
    t = np.clip(d32 * np.float32(-0.5 / soft) + np.float32(0.5), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def halfspace(p: VecLike, normal: Sequence[float], center: Center = MID) -> F32:
    """The side of a plane through `center` away from `normal`: the
    distance along the unit normal, negative behind the plane."""
    q = vec(p)
    norm = math.hypot(*normal)
    if norm == 0.0:
        raise ValueError("halfspace needs a non-zero normal")
    terms = [(c - m) * np.float32(n / norm) for c, m, n in zip(q, plain_center(center), normal)]
    return sum(terms[1:], terms[0])


def _smin(a: F32, b: F32, k: float) -> F32:
    """Quadratic smooth minimum with blend width k; the plain minimum for a
    k of 0 or below float32's smallest normal (Inigo Quilez, "Smooth
    Minimum")."""
    if k < _TINY:
        return np.minimum(a, b)
    h = np.maximum(np.float32(k) - np.abs(a - b), 0.0) * np.float32(1.0 / k)
    return np.minimum(a, b) - h * h * np.float32(k * 0.25)


def union(a: npt.ArrayLike, b: npt.ArrayLike, k: float = 0.0) -> F32:
    """The shapes together, blended over a width `k` where they meet."""
    a32, b32 = vec((a, b))
    return _smin(a32, b32, k)


def intersect(a: npt.ArrayLike, b: npt.ArrayLike, k: float = 0.0) -> F32:
    """Where both shapes are, with the crease rounded over a width `k`."""
    a32, b32 = vec((a, b))
    return -_smin(-a32, -b32, k)


def subtract(a: npt.ArrayLike, b: npt.ArrayLike, k: float = 0.0) -> F32:
    """Shape `a` with shape `b` cut out of it, the cut rounded over `k`."""
    a32, b32 = vec((a, b))
    return -_smin(-a32, b32, k)


def rounded(d: npt.ArrayLike, radius: float) -> F32:
    """The shape grown by `radius`, with its edges rounded."""
    return np.asarray(d, dtype=np.float32) - np.float32(radius)


def onion(d: npt.ArrayLike, thickness: float) -> F32:
    """A shell of `thickness` on each side of the shape's surface."""
    return np.abs(np.asarray(d, dtype=np.float32)) - np.float32(thickness)
