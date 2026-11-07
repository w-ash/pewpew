"""Nearest-neighbour graphs over a point cloud, and diffusion, wave and
reaction-diffusion steps on them.

A graph over the mapping's own points lets a simulation run on any layout
(a strip, a panel, a cloud or a mix) without an internal grid: heat
spreads, waves travel and Gray-Scott spots grow along the points
themselves. Build the graph once at bind with `neighbors`, then step it
each frame. Each step returns new arrays and keeps its inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import product

import numpy as np
import numpy.typing as npt

from pewpew.fx.prims.vec import F32

I32 = npt.NDArray[np.int32]
I64 = npt.NDArray[np.int64]

# Elements per candidate block; it bounds the memory of one search pass.
_BLOCK = 1 << 20
# Cells per axis the grid may grow to while it adapts to the points.
_MAX_CELLS = 1 << 20
# The typical distance of the k-th neighbour, in cells. Measured fastest
# for 5000-point clouds, panels and grids.
_REACH = 0.8


@dataclass(frozen=True, slots=True, eq=False)
class Neighbors:
    """The k nearest other points of each point, nearest first, ties by
    index: `idx` is (N, k) int32 and `dist` is (N, k) float32.

    A point with fewer than k others lists itself at distance inf in its
    spare slots, which every step ignores. Any (idx, dist) pair makes a
    graph, for example a strip's wiring order.

    `weight` (N, k) is the weight of each listed edge in the graph
    Laplacian: 1 / the larger degree of its two ends, where a degree counts
    every listed edge at both of its ends. These weights make the Laplacian
    conserve the total and keep `diffuse` stable for a rate up to 1. The
    arrays are read-only copies.
    """

    idx: I32
    dist: F32
    weight: F32 = field(init=False, repr=False)

    def __post_init__(self) -> None:
        idx, dist = np.array(self.idx, dtype=np.int32), np.array(self.dist, dtype=np.float32)
        if idx.ndim != 2 or idx.shape != dist.shape:
            raise ValueError(f"idx and dist must both be (N, k), got {idx.shape} and {dist.shape}")
        n = len(idx)
        if idx.size and (idx.min() < 0 or idx.max() >= n):
            raise ValueError(f"idx must index the {n} points, got values from {idx.min()} to {idx.max()}")
        real = idx != np.arange(n, dtype=np.int32)[:, None]
        degree = real.sum(axis=1) + np.bincount(idx[real], minlength=n)
        ends = np.maximum(degree[:, None], degree[idx])
        weight = np.where(real, 1.0 / np.maximum(ends, 1), 0.0).astype(np.float32)
        for name, a in (("idx", idx), ("dist", dist), ("weight", weight)):
            a.flags.writeable = False
            object.__setattr__(self, name, a)

    @property
    def k(self) -> int:
        """The number of neighbours each point lists."""
        return self.idx.shape[1]


# ---- the exact kNN search ----------------------------------------------------


def _pack(d2: F32, ids: I64) -> I64:
    """Sort keys: the squared distance's float32 bits, then the index.
    Non-negative float32 bits order as their values, so one integer sort
    orders by distance, then by index."""
    return (d2.view(np.uint32).astype(np.int64) << 32) | ids


def _d2(keys: I64) -> F32:
    """The squared distances that sort keys hold."""
    return (keys >> 32).astype(np.uint32).view(np.float32)


def _keys(pts: F32, ids: I64, rows: I64, valid: npt.NDArray[np.bool_]) -> I64:
    """Sort keys for the candidates `ids` (B, ...) of the points `rows`
    (B,). An invalid candidate or the point itself is at inf."""
    shape = (len(rows),) + (1,) * (ids.ndim - 1)
    d2 = np.zeros(np.broadcast_shapes(ids.shape, shape), dtype=np.float32)
    for a in range(pts.shape[1]):
        delta = pts[ids, a] - pts[rows, a].reshape(shape)
        d2 += delta * delta
    return _pack(np.where(valid & (ids != rows.reshape(shape)), d2, np.float32(np.inf)), ids)


def _merge(best: I64, rows: I64, keys: I64) -> None:
    """Keep the k smallest of each row's current best and its new keys."""
    k = best.shape[1]
    both = np.concatenate([best[rows], keys.reshape(len(rows), -1)], axis=1)
    best[rows] = np.partition(both, k - 1, axis=1)[:, :k]


class _Grid:
    """A uniform grid hash over the axes along which the points spread:
    the points sorted by cell, and the run of each occupied cell."""

    def __init__(self, pts: F32, k: int) -> None:
        n = len(pts)
        lo = pts.min(axis=0)
        extent = (pts.max(axis=0) - lo).astype(np.float64)
        active = np.flatnonzero(extent > 0)
        self.coords = (pts[:, active] - lo[active]).astype(np.float64)
        m = len(active)
        h = math.inf
        if m:
            # Size a cell so that k + 1 points fill a ball of radius _REACH cells.
            ball = math.pi ** (m / 2) / math.gamma(m / 2 + 1)
            per_cell = (k + 1) / (ball * _REACH**m)
            finest = float(extent.max()) / _MAX_CELLS
            h = max(float(np.prod(extent[active]) * per_cell / n) ** (1.0 / m), finest)
            self._place(h)
            # Points on curves or sheets inside the box crowd fewer cells:
            # halve the cells until the occupied ones are not crowded, or
            # until halving stops helping (duplicate points).
            crowd = n / len(self.uniq)
            while crowd > 4 * per_cell and h / 2 > finest:
                h /= 2
                self._place(h)
                crowd, before = n / len(self.uniq), crowd
                if crowd > before / 1.5:
                    break
        else:
            self._place(h)
        self.h = h

    def _place(self, h: float) -> None:
        cells = np.floor(self.coords / h).astype(np.int64)
        self.size = cells.max(axis=0, initial=0) + 1
        cell_id = self._linear(cells)
        self.order = np.argsort(cell_id, kind="stable")
        self.uniq, self.start, self.count = np.unique(cell_id[self.order], return_index=True, return_counts=True)
        self.home = cells[self.order[self.start]]
        self.which = np.searchsorted(self.uniq, cell_id)

    def _linear(self, cells: I64) -> I64:
        flat = np.zeros(cells.shape[:-1], dtype=np.int64)
        for a in range(cells.shape[-1]):
            flat = flat * self.size[a] + cells[..., a]
        return flat

    @property
    def span(self) -> int:
        """The most cells along any axis."""
        return int(self.size.max(initial=1))

    def ring(self, r: int) -> I64:
        """The cell offsets at Chebyshev distance `r` (all within 1 for
        r = 1), as (O, m)."""
        steps = [s for s in product(range(-r, r + 1), repeat=len(self.size)) if r == 1 or max(map(abs, s)) == r]
        return np.array(steps, dtype=np.int64).reshape(len(steps), len(self.size))

    def search(self, pts: F32, best: I64, rows: I64, offsets: I64) -> None:
        """Merge every point in the cells at `offsets` from each row's cell
        into that row's best keys."""
        home, line = np.unique(self.which[rows], return_inverse=True)
        near = self.home[home][:, None, :] + offsets[None]
        inside = ((near >= 0) & (near < self.size)).all(axis=-1)
        cell_id = self._linear(near)
        pos = np.minimum(np.searchsorted(self.uniq, cell_id), len(self.uniq) - 1)
        count = np.where(inside & (self.uniq[pos] == cell_id), self.count[pos], 0).ravel()
        # Each home cell's candidates: the runs of its cells at `offsets`, end to end.
        run = np.repeat(np.arange(count.size), count)
        step = np.arange(run.size) - np.repeat(np.cumsum(count) - count, count)
        candidates = self.order[self.start[pos].ravel()[run] + step]
        size = count.reshape(len(home), -1).sum(axis=1)
        first = np.cumsum(size) - size
        # Rows go in groups whose candidate counts are within a factor of 2,
        # so a crowded cell pads only the rows that search it.
        width = size[line]
        group = np.frexp(width.astype(np.float64))[1]
        for g in np.unique(group[width > 0]):
            members = np.flatnonzero(group == g)
            slot = np.arange(width[members].max())
            chunk = max(1, _BLOCK // len(slot))
            for lo in range(0, len(members), chunk):
                part = members[lo : lo + chunk]
                valid = slot < width[part, None]
                at = candidates[np.where(valid, first[line[part], None] + slot, 0)]
                _merge(best, rows[part], _keys(pts, at, rows[part], valid))


def neighbors(points: npt.ArrayLike, k: int) -> Neighbors:
    """The exact k nearest other points of each of the (N, D) `points`.

    The points go into a uniform grid hash sized to their density, over the
    axes along which they spread (one for a strip, two for a panel). Each
    point searches the cells around its own, then the next ring of cells.
    A point whose k-th neighbour may still lie outside the cells searched is
    checked against every point. Duplicate points are neighbours at
    distance 0.
    """
    pts = np.asarray(points, dtype=np.float32)
    pts = pts[:, None] if pts.ndim == 1 else pts
    if pts.ndim != 2:
        raise ValueError(f"points must be (N, D), got shape {pts.shape}")
    if k < 1:
        raise ValueError(f"k must be 1 or more, got {k}")
    n = len(pts)
    own = np.arange(n, dtype=np.int64)
    empty = _pack(np.full((n, k), np.inf, dtype=np.float32), own[:, None])
    best = empty.copy()
    if n > 1:
        grid = _Grid(pts, k)
        rows = own
        for r in (1, 2):
            grid.search(pts, best, rows, grid.ring(r))
            if r >= grid.span - 1:  # the cells searched cover the grid
                rows = rows[:0]
                break
            reach = np.float32(r * grid.h * (1.0 - 1e-4)) ** 2
            rows = rows[_d2(best[rows, -1]) > reach]
            if not len(rows):
                break
        # The rest start over against every point, so no candidate is seen twice.
        best[rows] = empty[rows]
        everyone, all_valid = own[None, :], np.ones((1, n), dtype=np.bool_)
        chunk = max(1, _BLOCK // n)
        for lo in range(0, len(rows), chunk):
            part = rows[lo : lo + chunk]
            _merge(best, part, _keys(pts, everyone, part, all_valid))
    best.sort(axis=1)
    d2 = _d2(best)
    idx = np.where(np.isinf(d2), own[:, None], best & 0xFFFFFFFF).astype(np.int32)
    return Neighbors(idx, np.sqrt(d2))


# ---- steps on the graph --------------------------------------------------------


def laplacian(u: npt.ArrayLike, nbrs: Neighbors) -> F32:
    """The graph Laplacian L u: sum of w (u_j - u_i) over each point's
    edges in both directions, the net flow into each point. It sums to 0
    over all points.

    The eigenvalues of L lie in [-2, 0] on every graph, and come close to
    -2 on a strip, a ring or a 4-neighbour panel. So each explicit step
    below is stable only up to a limit that holds on every graph, and
    refuses settings past it."""
    v = np.asarray(u, dtype=np.float32)
    if v.shape != (len(nbrs.idx),):
        raise ValueError(f"u must be ({len(nbrs.idx)},) for this graph, got {v.shape}")
    flow = nbrs.weight * (v[nbrs.idx] - v[:, None])
    back = np.bincount(nbrs.idx.ravel(), weights=flow.ravel(), minlength=len(v))
    return (flow.sum(axis=1) - back).astype(np.float32)


def diffuse(u: npt.ArrayLike, nbrs: Neighbors, rate: float) -> F32:
    """One explicit heat-diffusion step, u + rate * L u, for a rate in
    [0, 1]. The total does not change, and no value leaves the range of its
    neighbours'."""
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"diffuse needs a rate in [0, 1] to stay stable, got {rate}; take more steps instead")
    v = np.asarray(u, dtype=np.float32)
    return v + np.float32(rate) * laplacian(v, nbrs)


def wave_step(u: npt.ArrayLike, u_prev: npt.ArrayLike, nbrs: Neighbors, c: float, damping: float = 0.0) -> F32:
    """One leapfrog step of the damped wave equation: u + (1 - damping)
    (u - u_prev) + c^2 L u. Returns the next u; the current u becomes the
    next u_prev. Damping is in [0, 1], and c^2 must stay below 2 - damping
    (c^2 times L's eigenvalues must stay above 2 damping - 4): c below 1.41
    undamped, 1.22 at damping 0.5."""
    if not 0.0 <= damping <= 1.0:
        raise ValueError(f"wave_step needs a damping in [0, 1], got {damping}")
    if c * c >= 2.0 - damping:
        raise ValueError(
            f"wave_step needs c below {math.sqrt(2.0 - damping):.4g} at damping {damping} to stay stable, "
            f"got c={c}; take more steps with a smaller c"
        )
    v = np.asarray(u, dtype=np.float32)
    w = np.asarray(u_prev, dtype=np.float32)
    return v + np.float32(1.0 - damping) * (v - w) + np.float32(c * c) * laplacian(v, nbrs)


def gray_scott_step(
    a: npt.ArrayLike,
    b: npt.ArrayLike,
    nbrs: Neighbors,
    feed: float = 0.0545,
    kill: float = 0.062,
    da: float = 1.0,
    db: float = 0.5,
    dt: float = 0.5,
) -> tuple[F32, F32]:
    """One explicit step of Gray-Scott reaction-diffusion on the graph:
    a' = a + dt (da L a - a b^2 + feed (1 - a)) and
    b' = b + dt (db L b + a b^2 - (feed + kill) b) (Pearson, "Complex
    Patterns in a Simple System", 1993). The default rates are Karl Sims'
    coral (karlsims.com/rd.html).

    The rest state (a = 1, b = 0) is stable on every graph only while
    dt (2 da + feed) and dt (2 db + feed + kill) are at most 2, so a larger
    dt is refused. Sims' dt = 1 is past that limit (0.97 at his rates); it
    suits his 3x3 kernel, whose eigenvalues stop at -1.6. Inside spots the
    reaction lowers the limit, so the default dt = 0.5 keeps a wide margin."""
    reach = max(2.0 * da + feed, 2.0 * db + feed + kill)
    if dt * reach > 2.0:
        raise ValueError(
            f"gray_scott_step needs dt at most {2.0 / reach:.4g} at these rates to stay stable, got dt={dt}; "
            "take more steps with a smaller dt"
        )
    a32, b32 = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    react = a32 * b32 * b32
    step = np.float32(dt)
    a_next = a32 + step * (np.float32(da) * laplacian(a32, nbrs) - react + np.float32(feed) * (1.0 - a32))
    b_next = b32 + step * (np.float32(db) * laplacian(b32, nbrs) + react - np.float32(feed + kill) * b32)
    return a_next, b_next
