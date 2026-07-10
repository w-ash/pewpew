"""The pattern contract the engine will implement (architecture.md §3).

frame = render(t, mapping, params, seed)

- t: seconds (time-parameterized motion, req Q-5)
- mapping: (N, 3) float32 normalized world coords in [0, 1]
- params: flat name -> float dict (typed parameter tree comes later, ADR-006)
- seed: deterministic RNG seed — same inputs must yield the same frame
- returns: (N, 3) float32 linear-light RGB in [0, 1] (quantize-once happens
  at sinks, req Q-1 — goldens compare the float frames)
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


Params = dict[str, float]


class Pattern(Protocol):
    name: str

    def render(
        self,
        t: float,
        mapping: np.ndarray,
        params: Params,
        seed: int,
    ) -> np.ndarray: ...


def line_mapping(n: int) -> np.ndarray:
    """N pixels evenly spaced along x — the trivial test fixture geometry."""
    coords = np.zeros((n, 3), dtype=np.float32)
    coords[:, 0] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return coords
