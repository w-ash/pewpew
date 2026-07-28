"""Synthetic mapping fixtures — (N,3) float32 normalized world coords.

A mapping is just the coordinate table the engine hands `setup`/`render`
(architecture §3: normalized 0-1 world units, computed at map-load time).
These three are the fixtures the study and the test suite render against;
real fixtures come from map files and marimapper CSV import (§6).

Ported verbatim from `bench/authoring/surface.py`.
"""

from __future__ import annotations

import numpy as np


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
