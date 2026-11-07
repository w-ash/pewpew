"""Interpolated reads of a field at points, semi-Lagrangian advection, and
projections that give 3D points 2D texture coordinates.

`sample` is linear interpolation in as many dimensions as the point has
axes: bilinear for (x, y) on an (H, W) field, trilinear for (x, y, z) on a
(D, H, W) field. Channel axes after the spatial ones (an (H, W, 3) colour
field) come back per point.

Each axis has an edge mode:
- "clamp": the field spans 0 to 1 with a node at each end (node j at
  j / (n - 1)), and points outside read the edge.
- "wrap": the field is periodic with period 1 (node j at j / n), so
  1.0 reads the same as 0.0.
"""

from __future__ import annotations

import math
import operator
from collections.abc import Sequence
from functools import lru_cache, reduce
from typing import Literal, get_args

import numpy as np
import numpy.typing as npt

from pewpew.fx.prims.space import polar
from pewpew.fx.prims.vec import (
    AROUND,
    F32,
    MID,
    Axis,
    Center,
    Plane,
    Vec,
    VecLike,
    axis_index,
    length,
    plain_center,
    plane_axes,
    vec,
)

Edge = Literal["clamp", "wrap"]
EDGES: tuple[Edge, ...] = get_args(Edge)

Index = npt.NDArray[np.intp]


def _modes(edge: Edge | Sequence[Edge], d: int) -> tuple[Edge, ...]:
    modes = (edge,) * d if isinstance(edge, str) else tuple(edge)
    if len(modes) != d or any(m not in EDGES for m in modes):
        raise ValueError(f"edge must be 'clamp', 'wrap' or one of them per axis ({d} axes), got {edge!r}")
    return modes


def _axis(c: F32, n: int, mode: Edge) -> tuple[Index, Index, F32]:
    """The two nodes around each coordinate on an axis of `n` nodes, and
    the fraction of the way from the first to the second. A NaN coordinate
    reads as 0, since NaN cast to an index differs by platform (arm64 gives
    0, x86-64 the lowest integer, which indexes out of range)."""
    c = np.where(np.isnan(c), np.float32(0.0), c)
    if mode == "wrap":
        s = c * np.float32(n)
        cell = np.floor(s)
        i0 = cell.astype(np.intp) % n
        return i0, (i0 + 1) % n, s - cell
    if n == 1:
        zero = np.zeros(c.shape, dtype=np.intp)
        return zero, zero, np.zeros(c.shape, dtype=np.float32)
    s = np.clip(c, 0.0, 1.0) * np.float32(n - 1)
    cell = np.minimum(np.floor(s), np.float32(n - 2))
    i0 = cell.astype(np.intp)
    return i0, i0 + 1, s - cell


def stencil(shape: Sequence[int], p: VecLike, edge: Edge | Sequence[Edge] = "clamp") -> list[tuple[Index, F32]]:
    """The 2^d nodes around each point and their linear weights, as one
    (flat node index, weight) pair per corner. `shape` is the field's
    spatial shape, reversed from the axes of `p`. The weights of a point
    sum to 1. `sample` gathers through the stencil and `grid.deposit`
    scatters through it, so the two are adjoint."""
    q = vec(p)
    if len(shape) != len(q):
        raise ValueError(f"a field of spatial shape {tuple(shape)} needs points of {len(shape)} axes, got {len(q)}")
    corners: list[tuple[Index | int, F32 | float]] = [(0, 1.0)]
    stride = 1
    for c, n, mode in zip(q, reversed(shape), _modes(edge, len(q))):
        i0, i1, f = _axis(c, n, mode)
        sides = ((i0 * stride, 1.0 - f), (i1 * stride, f))
        corners = [(i + si, w * sw) for i, w in corners for si, sw in sides]
        stride *= n
    return [(np.asarray(i, dtype=np.intp), np.asarray(w, dtype=np.float32)) for i, w in corners]


def sample(field: npt.ArrayLike, p: VecLike, edge: Edge | Sequence[Edge] = "clamp") -> F32:
    """Read `field` at each point by linear interpolation of the nodes
    around it. The result has the points' shape, then the field's channel
    axes."""
    q = vec(p)
    f = np.asarray(field, dtype=np.float32)
    return gather(f, stencil(f.shape[: len(q)], q, edge), len(q))


def gather(field: npt.ArrayLike, corners: Sequence[tuple[Index, F32]], d: int) -> F32:
    """Read `field`, whose first `d` axes are spatial, through `corners`,
    a `stencil` of its spatial shape: `sample` once the stencil is known,
    so points read every frame work theirs out once. The result has the
    points' shape, then the field's channel axes."""
    f = np.asarray(field, dtype=np.float32)
    channels = f.shape[d:]
    flat = f.reshape(-1, *channels)
    per_channel = (1,) * len(channels)
    return reduce(operator.add, (flat[i] * w.reshape(w.shape + per_channel) for i, w in corners))


@lru_cache(maxsize=64)
def _nodes(shape: tuple[int, ...], modes: tuple[Edge, ...]) -> Vec:
    """The coordinates of a field's nodes per axis, shaped to broadcast
    along the field's own axes."""
    d = len(shape)
    out = []
    for a, (n, mode) in enumerate(zip(reversed(shape), modes)):
        step = 1.0 / n if mode == "wrap" else 1.0 / max(n - 1, 1)
        c = (np.arange(n, dtype=np.float32) * np.float32(step)).reshape([n if k == d - 1 - a else 1 for k in range(d)])
        c.flags.writeable = False
        out.append(c)
    return tuple(out)


def advect(field: npt.ArrayLike, v: VecLike, dt: float, edge: Edge | Sequence[Edge] = "clamp") -> F32:
    """Move `field` along the velocity `v` (one field or scalar per axis, in
    normalized units per second) for `dt` seconds: each node reads the field
    where its value came from (semi-Lagrangian advection; Stam, "Stable
    Fluids", 1999). The result has the field's shape."""
    vel = vec(v)
    f = np.asarray(field, dtype=np.float32)
    nodes = _nodes(f.shape[: len(vel)], _modes(edge, len(vel)))
    return sample(f, [n - u * np.float32(dt) for n, u in zip(nodes, vel)], edge)


def planar(p: VecLike, plane: Plane = "xy") -> Vec:
    """The two axes of `plane` as texture coordinates (u, v)."""
    q = vec(p)
    i, j = plane_axes(plane, q)
    return q[i], q[j]


def cylindrical(p: VecLike, axis: Axis = "y", center: Center = MID) -> Vec:
    """Texture coordinates on a cylinder about `axis` through `center`: u is
    the turn around the axis in [0, 1) (sample it with "wrap"), v is the
    coordinate along the axis."""
    q = vec(p)
    k = axis_index(axis, q)
    plane = AROUND[axis]
    return polar(q, plane, center)[plane_axes(plane, q)[1]], q[k]


def spherical(p: VecLike, center: Center = MID) -> Vec:
    """Texture coordinates on a sphere about `center`, with y up: u is the
    turn around the y axis in [0, 1) (sample it with "wrap"), v is the
    elevation from 0 at the bottom pole to 1 at the top."""
    q = vec(p)
    if len(q) != 3:
        raise ValueError(f"spherical takes points of 3 axes, got {len(q)}")
    center = plain_center(center)
    u = polar(q, "xz", center)[2]
    r = length([c - m for c, m in zip(q, center)])
    up = (q[1] - center[1]) / np.maximum(r, np.float32(1e-12))
    return u, 1.0 - np.arccos(np.clip(up, -1.0, 1.0)) * np.float32(1.0 / math.pi)
