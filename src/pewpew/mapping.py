"""Synthetic mappings: (N,3) float32 normalized world coordinates.

A mapping is the coordinate table the engine hands `setup` and `render`
(architecture §3: normalized 0-1 world units). `line`, `grid` and `lattice`
are the study's fixtures, copied from `bench/authoring/surface.py`; a room
map file (`pewpew.room.map`) gives a real one, and `parse_map` reads the
command line's names for the synthetic ones. `Grouping` groups a mapping's
pixels into fixtures for a pattern that lights a whole fixture as one unit.
`dimensions` tells a strip from a panel from a volume, by the axes a
mapping spreads along (`spanned`).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

# An axis is spanned when its extent is above this share of the longest
# extent, so float noise in a flat room's z leaves the room flat.
_FLAT = 1e-3


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


@dataclass(frozen=True)
class Grouping:
    """Pixels grouped into fixtures: what a per-fixture pattern renders at.

    `centres` is (F,3) float32 in the same normalized units as the pixel
    mapping; `of` is (N,) and gives the fixture index of each pixel. A
    per-fixture frame of F colours becomes the N-pixel frame as `frame[of]`.
    """

    centres: np.ndarray
    of: np.ndarray

    def __post_init__(self) -> None:
        if self.centres.ndim != 2 or self.centres.shape[1] != 3:
            raise ValueError(f"fixture centres must be (F,3), got {self.centres.shape}")
        if self.of.ndim != 1:
            raise ValueError(f"fixture table must be (N,), got {self.of.shape}")
        if len(self.of) and (self.of.min() < 0 or self.of.max() >= len(self.centres)):
            raise ValueError("fixture table names a fixture that has no centre")
