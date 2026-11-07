"""Deposit values carried by points (particles, attractor orbits) into a
field: the cheap way to draw many points, which costs one pass over them,
not one per pixel. `sample.sample` then reads the field at the mapping's
points. `spread` deposits through a stencil worked out once, for points
that stay put (the mapping's own).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from pewpew.fx.prims.sample import Edge, Index, stencil
from pewpew.fx.prims.vec import F32, VecLike, vec


def deposit(p: VecLike, weights: npt.ArrayLike, shape: Sequence[int], edge: Edge | Sequence[Edge] = "clamp") -> F32:
    """Spread each point's weight over the 2^d nodes around it, in the
    proportions `sample` reads them with (cloud-in-cell), into a new field
    of spatial `shape`. The field's total equals the total weight. For an
    (M, 3) array of points, pass `tuple(points.T)`."""
    return spread(stencil(shape, vec(p), edge), weights, shape)


def spread(corners: Sequence[tuple[Index, F32]], values: npt.ArrayLike, shape: Sequence[int]) -> F32:
    """Spread each point's value through `corners`, a `stencil` of spatial
    `shape`, summed per node: `deposit` once the stencil is known. A value
    per point (or one broadcast to every point) gives a field of `shape`;
    values with one more axis than the points (an (N, 3) colour per point)
    give a field with that axis last."""
    v = np.asarray(values, dtype=np.float32)
    size = int(np.prod(shape))
    channels = v.ndim > corners[0][1].ndim if corners else False
    fields = []
    for column in ([v[..., k] for k in range(v.shape[-1])] if channels else [v]):
        total = np.zeros(size, dtype=np.float64)
        for index, part in corners:
            index, part = np.broadcast_arrays(index, part * column)
            total += np.bincount(index.ravel(), weights=part.ravel(), minlength=size)
        fields.append(total.astype(np.float32).reshape(tuple(shape)))
    return np.stack(fields, axis=-1) if channels else fields[0]
