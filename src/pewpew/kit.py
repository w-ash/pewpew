"""The idiom kit: 0-1 phase/time built-ins and hsv (ADR-005, architecture §3).

Pixelblaze's shapers [S680:README.expressions.md#L19-L23,L151-L163] are the
model — everything is a 0-1 phase, `wave/triangle/square` shape it, `hsv`
colors it, and the kit absorbs the branching authors would otherwise write as
`if` (the `np.where` translation that the 2026-07-16 study measured).

Arithmetic here is ported **verbatim** from `bench/authoring/surface.py`: the
five study patterns are frozen evidence and their ported forms must render
bit-identically, so these expressions are copied rather than tidied.

`time()` is the one thing that changed. The prototype kept the current frame
time in a module global (`surface._now`, flagged there as a Phase-1 hack);
here it lives in a `contextvars.ContextVar` that the renderer scopes around
each frame, so concurrent engines, threads and async tasks cannot bleed each
other's time. The author-facing spelling stays the free function `time()` —
that spelling is the ADR-005 contract.

Note for engine code: `time` in this module is the kit's phase built-in, not
the stdlib module. The engine never reads a wall clock (determinism is
load-bearing, req Q-5), so `import time` must not appear anywhere in it.
"""

from __future__ import annotations

import contextlib
import math
from contextvars import ContextVar
from typing import Iterator

import numpy as np

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
        # 0 is the natural spelling for "don't animate", and the bare
        # ZeroDivisionError points at the kit rather than at the call site.
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


def hsv(h, s, v) -> np.ndarray:
    """Vectorized branch-free HSV -> RGB, h wrapping mod 1.

    Output is linear-light RGB (ADR-001). Inputs broadcast; returns (..., 3)
    float32 in [0,1]. The classic if-chain lives here as clip arithmetic — the
    kit absorbing branching on the authors' behalf.
    """
    h6 = (np.asarray(h, dtype=np.float32) % 1.0) * 6.0
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)

    def chan(n: float) -> np.ndarray:
        k = (n + h6) % 6.0
        return v - v * s * np.clip(np.minimum(k, 4.0 - k), 0.0, 1.0)

    r, g, b = np.broadcast_arrays(chan(5.0), chan(3.0), chan(1.0))
    return np.stack([r, g, b], axis=-1).astype(np.float32)


# ---- the four kit additions the study made ADR-005 conditional on ----------
#
# Ported verbatim from the inline expressions the five study patterns each
# wrote by hand (bench/authoring/*.py, frozen evidence) — see
# bench/results/authoring-2026-07-16.md, "Verdict", and the Authoring-surface
# epic of docs/backlog/v0.2.x.md.


def fade(dt: float, tau: float) -> float:
    """Frame-rate-independent decay keep-factor: `v *= fade(dt, tau)`.

    Ported verbatim from comet.py/geq.py::before_render: `math.exp(-dt /
    self.tail)` / `math.exp(-dt / self.fall)`. Stumble #2: every classic
    trail/falloff effect ships a per-frame constant (`v *= 0.94`,
    `fadeToBlackBy`) that is silently frame-rate dependent; req Q-5 makes
    patterns pure functions of dt, so the decay must be `exp(-dt/tau)`
    instead — right thing to do, porting trap otherwise.

    Scalar in, scalar out, deliberately not vectorized (dt and tau are
    per-frame/per-pattern scalars, not per-pixel arrays). Returns a Python
    float via `math.exp`, not a numpy scalar — matching the study's types
    exactly, since a numpy scalar here can perturb a downstream dtype.
    """
    return math.exp(-dt / tau)


def bins(x, n: int):
    """Coordinate to integer bin index, edge-clamped to `[0, n-1]`.

    Ported verbatim from geq.py::render (n=16): `np.minimum((x *
    16.0).astype(np.int32), 15)`. Stumble #9 — a *hit* even for a
    NumPy-fluent author: scalar-thinking `int(x * n)` bins `x == 1.0` (the
    last pixel of an inclusive 0-1 mapping) into bin `n`, one past the end,
    and every segment/band lookup IndexErrors. Nothing warns you until the
    rightmost pixel.

    Clamped at *both* ends. The study spelling clamped only the top, which is
    invisible while coordinates are exactly 0-1 but silently wrong the moment
    they are not: a negative index does not raise, it wraps to the far end of
    the band array and quietly returns another band's value. Imported maps
    (marimapper CSVs, §6) are exactly where slightly-out-of-range coordinates
    come from. The 0-1 case is unaffected, so this stays bit-exact with the
    study.
    """
    return np.clip((np.asarray(x) * n).astype(np.int32), 0, n - 1)


def sample2d(field: np.ndarray, x, y) -> np.ndarray:
    """Sample a 2D field at normalized (x, y) world coordinates: nearest
    cell, edge-clamped.

    Ported verbatim from fire.py::render (field = self.heat, shape (H, W)):
        ci = np.minimum((x * (self.W - 1) + 0.5).astype(np.int32), self.W - 1)
        ri = np.minimum((y * (self.H - 1) + 0.5).astype(np.int32), self.H - 1)
        h = self.heat[ri, ci]
    generalized from Fire's fixed W=16/H=32 to `field.shape`. Stumble #12 —
    the study's HEADLINE finding, a *hit*: Fire2012's neighbor stencil is
    inexpressible over the unordered `self.pixels` point list; the
    unblocking idiom is a pattern-owned internal field sampled at world
    coords in `render`. Every field pattern then repeats this exact
    scale/round/cast/clamp/gather boilerplate (stumble #15).

    Clamped at *both* ends, for the reason spelled out in `bins`: the study
    spelling clamped only the top, so a coordinate below 0 indexed the field
    from its opposite edge instead of its nearest cell — for fire, sampling
    the top of the flame for a pixel below the panel origin. Coordinates in
    0-1 are unaffected, so this stays bit-exact with the study.
    """
    if field.ndim != 2:
        raise ValueError(f"sample2d expects a 2D field (H, W), got shape {field.shape}")
    h, w = field.shape
    ci = np.clip((np.asarray(x) * (w - 1) + 0.5).astype(np.int32), 0, w - 1)
    ri = np.clip((np.asarray(y) * (h - 1) + 0.5).astype(np.int32), 0, h - 1)
    return field[ri, ci]


def hash01(x, seed, salt):
    """Stable per-pixel pseudo-random value in `[0, 1)`.

    Ported verbatim from comet.py::render:
        x64 = x.astype(np.float64)
        spark = (np.sin(12.9898 * x64 + self.seed + salt) * 43758.5453) % 1.0
    Stumble #6 — a *hit*, carried from the throughput bench: computed in
    float32 this disagrees with float64 near the 0.995 threshold and flips
    sparkle pixels, so the float64 promotion of `x` is unconditional here,
    not incidental — do not let a caller downcast around it.

    `seed` and `salt` are kept as two separate arguments, not one
    pre-summed value, and that is load-bearing, not stylistic. The study
    expression is `12.9898 * x64 + self.seed + salt`, which Python
    evaluates left-to-right as `(12.9898 * x64 + self.seed) + salt`; float
    addition is not associative, so a single `seed + salt` argument
    computed *before* the array op is not guaranteed to reproduce that
    bit-for-bit. It doesn't: checked empirically against the comet's actual
    120-frame study run (seed=42, x=line(300)), the pre-summed and
    two-step forms diverge by 1 ulp on 46 of the 120 frames (every frame
    from salt=10 onward) — the same class of last-bit sensitivity stumble
    #6 exists to catch, just one step upstream of the float32/float64 one.
    Keeping `seed` and `salt` as separate addends, added in the study's
    order, reproduces the study bit-exactly by construction rather than by
    coincidence.
    """
    x64 = np.asarray(x).astype(np.float64)
    return (np.sin(12.9898 * x64 + seed + salt) * 43758.5453) % 1.0
