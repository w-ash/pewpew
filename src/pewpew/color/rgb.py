"""HSV to linear-light RGB, and the index of a 0-1 coordinate in a table."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def hsv(h: ArrayLike, s: ArrayLike, v: ArrayLike) -> np.ndarray:
    """Branch-free HSV -> linear-light RGB (ADR-001), h wrapping mod 1.
    Inputs broadcast; returns (..., 3) float32 in [0, 1]."""
    h6 = (np.asarray(h, dtype=np.float32) % 1.0) * 6.0
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)

    def chan(n: float) -> np.ndarray:
        k = (n + h6) % 6.0
        return v - v * s * np.clip(np.minimum(k, 4.0 - k), 0.0, 1.0)

    r, g, b = np.broadcast_arrays(chan(5.0), chan(3.0), chan(1.0))
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _cell(v, n: int) -> np.ndarray:
    """`v` truncated to an int32 index in [0, n-1].

    The clamp comes before the cast: a float past the int32 range, or NaN,
    casts to a platform-dependent value (arm64 saturates or gives 0, x86-64
    gives INT_MIN), and numpy warns. Clamped first, an infinite or far `v`
    gets the end index and NaN gets index 0 on every platform.
    """
    return np.clip(np.nan_to_num(v, nan=0.0), 0, n - 1).astype(np.int32)


def bins(x, n: int):
    """The bin index of each `x` in 0..1, clamped to [0, n-1] at both ends.

    `int(x * n)` puts x == 1.0 in bin n, one past the end (stumble #9). The
    low clamp keeps a coordinate below 0 from wrapping to the last bin.
    """
    return _cell(np.asarray(x) * n, n)
