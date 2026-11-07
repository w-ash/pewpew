"""Fields: the state an op keeps on a grid over the map (ADR-022).

An op whose state must be read between the map's points (a feedback
field, the glow of particles or of an attractor's orbits) keeps it on a
`Lattice`: a grid over the map's extent along the axes the map spreads
along. On a strip that is one axis, `u` (along the strip in wiring order,
0 to 1, so distances on a strip are shares of its length); on a panel the
two axes of its plane; in a volume x, y and z. The last axis is "up": `u`
on a strip, the plane's second axis on a panel, z in a volume. Cells are
square in world units, so a turn stays round on a 16x32 panel.

A field is an array of the lattice's `shape` (its last axis first, as
pewpew.fx.prims.sample reads one), with a trailing channel axis for rgb.
`Lattice.sample` reads it at points by linear interpolation, so a coord op
may sit above an op that keeps its state here. `Stencil` is a read at
fixed points worked out once; `Splat` writes values known only at the
map's points into a field; `Lattice.glow` draws moving points as soft
blobs.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
import numpy.typing as npt

from pewpew.fx.op import AUTO, BindCtx
from pewpew.fx.prims.grid import deposit, spread
from pewpew.fx.prims.sample import Index, gather, sample, stencil
from pewpew.fx.prims.vec import AXES, F32, Vec
from pewpew.fx.types import Coords

# The most nodes a lattice of 1, 2 or 3 axes holds: a field step stays
# under a few milliseconds at the cap.
CAPS = {1: 4096, 2: 128 * 128, 3: 32**3}
# The fewest nodes along an axis.
_FEWEST = 2


@dataclass(frozen=True, slots=True)
class Lattice:
    """A grid over the map (module docstring): its `axes` ("u", or x, y, z
    names), the low end and extent of each in world units (`lo`, `span`),
    the nodes along each (`counts`), in `axes` order, and about how far
    apart the map's points are (`spacing`). Node j of an axis sits at
    lo + span * j / (count - 1)."""

    axes: tuple[str, ...]
    lo: tuple[float, ...]
    span: tuple[float, ...]
    counts: tuple[int, ...]
    spacing: float

    @classmethod
    def over(cls, ctx: BindCtx, per: float) -> Lattice:
        """The lattice over `ctx`'s map with about `per` nodes per point
        spacing along each axis, cells square in world units, at most
        `CAPS` nodes."""
        axes = lattice_axes(ctx)
        if axes == ("u",):
            lo, span = (0.0,), (1.0,)
        else:
            picked = [AXES.index(a) for a in axes]
            lo = tuple(ctx.lo[i] for i in picked)
            span = tuple(max(ctx.spans[i], 1e-6) for i in picked)
        spacing = _point_spacing(ctx, span)
        cell = spacing / per
        counts = _counts(span, cell)
        while math.prod(counts) > CAPS[len(axes)]:
            cell *= (math.prod(counts) / CAPS[len(axes)]) ** (1.0 / len(axes)) * 1.001
            counts = _counts(span, cell)
        return cls(axes, lo, span, counts, spacing)

    @property
    def d(self) -> int:
        return len(self.axes)

    @property
    def shape(self) -> tuple[int, ...]:
        """A field's spatial shape: the last axis first."""
        return tuple(reversed(self.counts))

    @property
    def cell(self) -> float:
        """The world size of a cell (the mean over the axes)."""
        return sum(s / (n - 1) for s, n in zip(self.span, self.counts)) / self.d

    def coarse(self, cell: float) -> Lattice:
        """This lattice's extent with nodes about `cell` world units apart,
        never more than its own."""
        return replace(self, counts=tuple(min(n, c) for n, c in zip(self.counts, _counts(self.span, cell))))

    def at(self, c: Coords) -> Vec:
        """Each point of `c` in lattice units, 0 to 1 along each axis."""
        return tuple((c.along(a) - lo) * (1.0 / span) for a, lo, span in zip(self.axes, self.lo, self.span))

    def sample(self, field: npt.ArrayLike, c: Coords) -> F32:
        """`field` read at the points of `c` by linear interpolation, edges
        clamped: (N,) for a scalar field, (N, 3) for rgb."""
        return sample(field, self.at(c))

    def grid(self) -> Vec:
        """Each node's position in world units from the lattice's centre,
        one array of `shape` per axis."""
        out = []
        for a, (n, span) in enumerate(zip(self.counts, self.span)):
            line = (np.linspace(-0.5, 0.5, n) * span).astype(np.float32)
            line = line.reshape([n if k == self.d - 1 - a else 1 for k in range(self.d)])
            out.append(np.broadcast_to(line, self.shape).copy())
        return tuple(out)

    def unit(self, offsets: Sequence[F32]) -> Vec:
        """Positions given in world units from the centre (`grid`), in
        lattice units."""
        return tuple(m * (1.0 / span) + 0.5 for m, span in zip(offsets, self.span))

    def reach(self, radius: float) -> int:
        """The box `blur` takes for a tent of about `radius` (world units),
        or of the points' spacing when that is wider, so a blob never
        slips between two points: two passes of a box `2 * reach + 1`
        cells wide reach `2 * reach` cells. At least 1."""
        return max(1, round(max(radius, self.spacing) / (2.0 * self.cell)))

    def glow(self, points: Sequence[npt.ArrayLike], weights: npt.ArrayLike, radius: float) -> F32:
        """Points (in lattice units, one array per axis) drawn as soft
        blobs of about `radius` (`reach`): each point's weight spread over
        the cells about it, so the field's total is the weights' total."""
        return blur(deposit(points, weights, self.shape), self.reach(radius))

    def peak(self, radius: float) -> float:
        """What makes a blob of `glow` peak at its weight."""
        return float((2 * self.reach(radius) + 1) ** self.d)


def lattice_axes(ctx: BindCtx) -> tuple[str, ...]:
    """The axes a lattice over `ctx`'s map has (module docstring)."""
    if ctx.dims == 1:
        return ("u",)
    if ctx.dims == 2:
        return tuple(ctx.plane(AUTO))
    return tuple(AXES)


def _point_spacing(ctx: BindCtx, span: Sequence[float]) -> float:
    """About how far apart the map's points are along a lattice of extent
    `span`: on a strip a share of its length, else the side of a cube (or
    square) holding one point."""
    n = max(ctx.n, 1)
    if len(span) == 1:
        return 1.0 / max(n - 1, 1)
    return (math.prod(span) / n) ** (1.0 / len(span))


def _counts(span: Sequence[float], cell: float) -> tuple[int, ...]:
    return tuple(max(_FEWEST, math.ceil(s / cell) + 1) for s in span)


def blur(field: np.ndarray, reach: int, passes: int = 2, axes: int | None = None) -> F32:
    """`field` blurred `passes` times by a box `2 * reach + 1` cells wide
    along each of its first `axes` axes (all by default; leave a channel
    axis out), a tent for two passes, its edges held: the total is kept
    but for what the held edges add."""
    out = np.asarray(field, dtype=np.float32)
    for _ in range(passes):
        for axis in range(out.ndim if axes is None else axes):
            out = _box(out, reach, axis)
    return out


def _box(field: np.ndarray, reach: int, axis: int) -> F32:
    """One box pass along `axis`, by running sums."""
    f = np.moveaxis(field, axis, 0)
    n = f.shape[0]
    padded = np.concatenate([np.repeat(f[:1], reach + 1, axis=0), f, np.repeat(f[-1:], reach, axis=0)])
    sums = np.cumsum(padded, axis=0, dtype=np.float64)
    width = 2 * reach + 1
    out = ((sums[width : width + n] - sums[:n]) * (1.0 / width)).astype(np.float32)
    return np.moveaxis(out, 0, axis)


@dataclass(frozen=True, slots=True, eq=False)
class Stencil:
    """A linear read of a field of spatial `shape` at fixed points, worked
    out once: the nodes about each point and their weights
    (pewpew.fx.prims.sample.stencil). `read` gathers through it, as
    `sample` would; `scatter` spreads values back through it, as
    `grid.deposit` would."""

    shape: tuple[int, ...]
    corners: tuple[tuple[Index, F32], ...]

    @classmethod
    def at(cls, shape: Sequence[int], points: Sequence[npt.ArrayLike]) -> Stencil:
        """The read of a field of spatial `shape` at `points` (lattice
        units, one array per axis)."""
        return cls(tuple(shape), tuple(stencil(shape, points)))

    def read(self, field: np.ndarray) -> F32:
        """`field` at the points, with its channel axes after theirs."""
        return gather(field, self.corners, len(self.shape))

    def scatter(self, values: np.ndarray) -> F32:
        """A field of `shape` that holds each point's value (an (N,) or
        (N, 3) array) spread over the nodes about it, with the values'
        channel axis last."""
        return spread(self.corners, values, self.shape)


@dataclass(frozen=True, slots=True, eq=False)
class Splat:
    """Writes values known only at fixed points (the map's) into a
    lattice's field: the weighted values and the weights are spread on the
    nodes about each point and blurred alike over the gaps between points,
    then divided (normalized convolution), so a node near points takes
    their blend and a node far from every point takes 0. Built once per
    bind (`of`)."""

    stencil: Stencil
    inverse: F32
    reach: int

    @classmethod
    def of(cls, lattice: Lattice, points: Sequence[npt.ArrayLike], reach: int) -> Splat:
        """The splat of `points` (lattice units, one array per axis) onto
        `lattice`, blurred `reach` cells wide."""
        at = Stencil.at(lattice.shape, points)
        cover = blur(at.scatter(np.ones(len(np.asarray(points[0])), np.float32)), reach, passes=1)
        inverse = np.where(cover > 1e-6, 1.0 / np.maximum(cover, 1e-6), 0.0).astype(np.float32)
        return cls(at, inverse, reach)

    def __call__(self, values: np.ndarray) -> F32:
        """A field of `values` ((N,) or (N, 3), one per point)."""
        smeared = blur(self.stencil.scatter(values), self.reach, passes=1, axes=len(self.stencil.shape))
        return smeared * (self.inverse if values.ndim == 1 else self.inverse[..., None])
