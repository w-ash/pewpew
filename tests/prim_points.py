"""Hypothesis strategies and a distance oracle for the point-taking fx
primitive tests (tests/test_prims_*.py)."""

from __future__ import annotations

import numpy as np
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from pewpew.fx.prims.vec import MID

# A coordinate around the unit world, including a little outside it.
coord = st.floats(-0.5, 1.5, width=32)
# 1 to 40 three-axis points, as per-axis float32 arrays.
points = st.integers(1, 40).flatmap(lambda n: st.tuples(*(arrays(np.float32, n, elements=coord) for _ in range(3))))


def radius(p, axes: str = "xyz") -> np.ndarray:
    """The float64 distance of each point from `MID`, over the axes in
    `axes`."""
    return np.sqrt(sum((p[i].astype(np.float64) - MID[i]) ** 2 for i in map("xyz".index, axes)))
