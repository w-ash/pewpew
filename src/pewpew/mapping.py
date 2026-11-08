"""Synthetic mappings: (N,3) float32 normalized world coordinates.

A mapping is the coordinate table a program binds to (architecture §3:
normalized 0-1 world units). `line`, `grid` and `lattice` are the
authoring study's fixtures (bench/results/authoring-2026-07-16.md); an
arrangement file (`pewpew.rig`) gives a real one, and `parse_map` reads the
command line's names for the synthetic ones. `dimensions` tells a strip from a panel from a volume, by the axes a
mapping spreads along (`spanned`).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

import numpy as np

# An axis is spanned when its extent is above this share of the longest
# extent, so float noise in a flat room's z leaves the room flat.
_FLAT = 1e-3

# The map `run` and the offline renders use when none is named.
DEFAULT_MAP = "grid:16x16"


class Contained(NamedTuple):
    """A contain-normalized mapping and the transform that made it."""

    mapping: np.ndarray  # (N,3) float32, read-only
    scale: float  # mapping = positions * scale + shift
    shift: tuple[float, float, float]
    span: tuple[float, float, float]  # each axis extent over the longest
    extent: tuple[float, float, float]  # metres, per axis


def contain(positions: np.ndarray) -> Contained:
    """Fit positions in the unit cube, keeping aspect ratio.

    The longest axis spans exactly [0, 1]. Shorter axes are centred on 0.5.
    A flat axis, and a single point, map to 0; an axis is flat when its extent
    is within `_FLAT` of the longest, so libm rounding in a rotated flat rig
    (z about 1e-16 on one platform, exactly 0 on another) gives one mapping.
    No points give an empty mapping.
    """
    p = np.asarray(positions, dtype=np.float64)
    if len(p) == 0:
        empty = np.zeros((0, 3), dtype=np.float32)
        empty.setflags(write=False)
        return Contained(empty, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    lo = p.min(axis=0)
    extent = p.max(axis=0) - lo
    longest = float(extent.max()) or 1.0
    # Division, not a reciprocal multiply, so the longest axis lands on exactly 0 and 1.
    span = extent / longest
    offset = np.where(span > _FLAT, (1.0 - span) / 2.0, 0.0)
    mapping = np.ascontiguousarray((p - lo) / longest + offset, dtype=np.float32)
    mapping.setflags(write=False)
    return Contained(
        mapping,
        1.0 / longest,
        tuple(float(v) for v in offset - lo / longest),  # type: ignore[arg-type]
        tuple(float(v) for v in span),  # type: ignore[arg-type]
        tuple(float(v) for v in extent),  # type: ignore[arg-type]
    )


def pixel_offsets(count: int, span: float) -> np.ndarray:
    """Offsets of `count` pixel centres along a `span`, centred on 0."""
    return (np.arange(count) + 0.5) * span / count - span / 2


def line(n: int) -> np.ndarray:
    """n pixels along x, y=z=0."""
    m = np.zeros((n, 3), dtype=np.float32)
    m[:, 0] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return m


def grid(w: int, h: int) -> np.ndarray:
    """w×h panel in the xy plane, row-major (index = row*w + col), y=0 bottom."""
    xs, ys = np.meshgrid(
        np.linspace(0.0, 1.0, w, dtype=np.float32),
        np.linspace(0.0, 1.0, h, dtype=np.float32),
    )
    m = np.zeros((w * h, 3), dtype=np.float32)
    m[:, 0] = xs.ravel()
    m[:, 1] = ys.ravel()
    return m


def lattice(k: int) -> np.ndarray:
    """k³ cube, index = (iz*k + iy)*k + ix — regular so ANSI z-slices read."""
    axis = np.linspace(0.0, 1.0, k, dtype=np.float32)
    zs, ys, xs = np.meshgrid(axis, axis, axis, indexing="ij")
    m = np.stack([xs.ravel(), ys.ravel(), zs.ravel()], axis=1)
    return np.ascontiguousarray(m, dtype=np.float32)


_SYNTHETIC = {"line": (line, 1), "grid": (grid, 2), "lattice": (lattice, 1)}


def parse_map(spec: str) -> np.ndarray:
    """The synthetic mapping `spec` names: `line:64`, `grid:16x16` or
    `lattice:8`, each size a whole number of at least 1. Raises ValueError
    for any other text."""
    kind, _, arg = spec.partition(":")
    make, count = _SYNTHETIC.get(kind, (None, 0))
    sizes = arg.split("x")
    if make is not None and len(sizes) == count and all(n.isascii() and n.isdigit() and int(n) > 0 for n in sizes):
        return make(*map(int, sizes))
    raise ValueError(f"expected line:64, grid:16x16 or lattice:8, sizes at least 1; got {spec!r}")


def extents(positions: np.ndarray) -> np.ndarray:
    """(3,) float64: the reach of a mapping along x, y and z (max - min).
    All zeros for an empty mapping. Raises ValueError if it is not (N, 3)."""
    p = np.asarray(positions, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError(f"a mapping is an (N, 3) array of x, y, z, got shape {p.shape}")
    return p.max(axis=0) - p.min(axis=0) if len(p) else np.zeros(3)


def spanned(reach: Iterable[float]) -> tuple[bool, ...]:
    """Whether a mapping of `reach` (its `extents`) spans each axis: an
    axis counts when its extent is above 1/1000 of the longest one."""
    spans = [float(r) for r in reach]
    top = max(spans, default=0.0)
    return tuple(span > _FLAT * top for span in spans)


def dimensions(positions: np.ndarray) -> int:
    """How many axes a mapping spans (`spanned`): 0 for one point (or
    none), 1 for a strip, 2 for a panel or a flat room, 3 for a volume. The
    count is per axis, so a diagonal line counts 2.
    """
    return sum(spanned(extents(positions)))
