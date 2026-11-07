"""The idiom kit: 0-1 phase/time built-ins and hsv (ADR-005, architecture §3).

Pixelblaze's shapers [S680:README.expressions.md#L19-L23,L151-L163] are the
model: everything is a 0-1 phase, `wave/triangle/square` shape it, `hsv`
colors it, and the kit absorbs the branching an author would write as `if`.

The arithmetic is copied, not tidied, from `bench/authoring/surface.py`, so
the five study ports render bit-identically (tests/test_port_equivalence.py).

`time()` reads a `ContextVar` that the renderer sets around each frame, so
engines on other threads cannot share a time. In this module `time` is the
kit's built-in, not the stdlib module: the engine reads no wall clock (Q-5).
"""

from __future__ import annotations

import contextlib
import math
from collections.abc import Iterator
from contextvars import ContextVar

import numpy as np
from numpy.typing import ArrayLike

TWO_PI = 2.0 * math.pi

# ---- frame context (renderer-managed) --------------------------------------

_NOW: ContextVar[float] = ContextVar("pewpew_frame_time", default=0.0)


@contextlib.contextmanager
def _frame_time(t: float) -> Iterator[None]:
    """Engine-internal: scope `time()` to one frame's t, then restore it."""
    token = _NOW.set(float(t))
    try:
        yield
    finally:
        _NOW.reset(token)


def time(interval: float):
    """Pixelblaze-scaled 0-1 sawtooth: period = interval * 65.536 seconds."""
    if interval == 0:
        # A bare ZeroDivisionError would point at the kit, not the call site.
        raise ValueError("time(interval) needs a non-zero interval; use a constant phase instead")
    return (_NOW.get() / (interval * 65.536)) % 1.0


# ---- 0-1 phase waveform shapers (scalar or array) --------------------------


def wave(p):
    """Sine shaped to 0-1: wave(0)=0.5 rising."""
    return 0.5 + 0.5 * np.sin(TWO_PI * np.asarray(p))


def triangle(p):
    """0 → 1 → 0 over one 0-1 phase."""
    return 1.0 - np.abs(2.0 * (np.asarray(p) % 1.0) - 1.0)


def square(p, duty: float = 0.5):
    """1 for the first `duty` fraction of the phase, else 0."""
    return np.where((np.asarray(p) % 1.0) < duty, 1.0, 0.0)


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


# ---- fade, bins, sample2d, hash01: the study's verdict -----------------------
# (bench/results/authoring-2026-07-16.md). Each copies the expression a study
# pattern wrote by hand; tests/test_kit.py holds the proofs.


def fade(dt: float, tau: float) -> float:
    """Frame-rate-independent decay factor: `v *= fade(dt, tau)` keeps
    exp(-dt/tau), where a per-frame constant (`v *= 0.94`) would depend on
    the frame rate (stumble #2). Returns a Python float, as the study did, so
    no numpy scalar changes a downstream dtype."""
    return math.exp(-dt / tau)


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
    Bit-exact with geq's study code for x in 0..1.
    """
    return _cell(np.asarray(x) * n, n)


def sample2d(field: np.ndarray, x, y) -> np.ndarray:
    """The nearest cell of `field` (H, W) at normalized (x, y), clamped at
    both ends as in `bins`.

    A stencil effect (Fire2012) keeps its state in a field of its own and
    samples it at world coordinates in `render` (stumbles #12, #15).
    Bit-exact with fire's study code for x, y in 0..1.
    """
    if field.ndim != 2:
        raise ValueError(f"sample2d expects a 2D field (H, W), got shape {field.shape}")
    h, w = field.shape
    return field[_cell(np.asarray(y) * (h - 1) + 0.5, h), _cell(np.asarray(x) * (w - 1) + 0.5, w)]


def hash01(x, seed, salt):
    """A stable per-pixel pseudo-random value in [0, 1).

    Computed in float64: float32 flips sparkle pixels near comet's 0.995
    threshold (stumble #6). `seed` and `salt` stay separate and are added in
    this order: a pre-summed value differs by 1 ulp on 46 of comet's 120
    study frames.
    """
    x64 = np.asarray(x).astype(np.float64)
    return (np.sin(12.9898 * x64 + seed + salt) * 43758.5453) % 1.0
