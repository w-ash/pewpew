"""Minimal prototype of the ADR-005 authoring surface.

This is the contract under study (§12 item 2), NOT the Phase-1 engine:
patterns are classes with `before_render(dt, features)` (per-frame state
advance; the only place RNG may be drawn) and `render(x, y, z, index)` — a
pure function over (N,) coordinate arrays in normalized 0-1 world units
returning (N,3) float32 linear RGB. `self.pixels` holds the previous
frame's output (assigned by the runner after each render; read-only inside
render). Idiom kit follows Pixelblaze [S680]: 0-1 phases + wave/triangle/
square shapers, hsv().

Prototype hacks, flagged for Phase 1: `time()` reads a module-level
current-t set by the runner each frame (a real engine will scope this);
`Param` materializes to a plain float at setup (full typed tree is ADR-006).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TWO_PI = 2.0 * math.pi

# ---- frame context (runner-managed) ---------------------------------------

_now = 0.0


def set_now(t: float) -> None:
    """Runner hook: set the current frame's time before before_render()."""
    global _now
    _now = float(t)


def time(interval: float):
    """Pixelblaze-scaled 0-1 sawtooth: period = interval * 65.536 seconds."""
    return (_now / (interval * 65.536)) % 1.0


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

    Output is treated as linear-light RGB for the prototype (a real engine
    would be explicit about the colorspace, ADR-001). Inputs broadcast;
    returns (..., 3) float32 in [0,1]. The classic if-chain lives here as
    clip arithmetic — the kit absorbing branching on the authors' behalf.
    """
    h6 = (np.asarray(h, dtype=np.float32) % 1.0) * 6.0
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)

    def chan(n: float) -> np.ndarray:
        k = (n + h6) % 6.0
        return v - v * s * np.clip(np.minimum(k, 4.0 - k), 0.0, 1.0)

    r, g, b = np.broadcast_arrays(chan(5.0), chan(3.0), chan(1.0))
    return np.stack([r, g, b], axis=-1).astype(np.float32)


# ---- typed params (ADR-006 semantics, prototype-minimal) --------------------


class Param:
    """One-line typed knob: Param(default, lo, hi, label).

    At _setup the instance attribute becomes plain float(default), so
    pattern code reads `self.speed` as a number. UI/OSC/modulation wiring
    is the real engine's job (ADR-006).
    """

    def __init__(self, default: float, lo: float = 0.0, hi: float = 1.0, label: str = ""):
        self.default, self.lo, self.hi, self.label = default, lo, hi, label


# ---- the pattern base -------------------------------------------------------


class Pattern:
    name = "pattern"

    def _setup(self, n: int, seed: int) -> None:
        """Engine-side init: called once before the first frame."""
        self.pixels = np.zeros((n, 3), dtype=np.float32)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        for cls in type(self).__mro__:
            for k, val in vars(cls).items():
                if isinstance(val, Param) and not isinstance(getattr(self, k), float):
                    setattr(self, k, float(val.default))

    def before_render(self, dt: float, features: "FeatureFrame") -> None:
        """Advance state once per frame. The only place RNG may be drawn."""

    def render(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> np.ndarray:
        """Pure over coordinate arrays; returns (N,3) float32 in [0,1]."""
        raise NotImplementedError


# ---- fake sensor frame (architecture §7, deterministic) ---------------------


@dataclass(frozen=True)
class FeatureFrame:
    bands: np.ndarray  # (16,) float32, read-only
    volume: float
    bass: float
    mid: float
    high: float
    beat_phase: float  # 0-1, 120 BPM


class FakeFeatures:
    """Deterministic stand-in for the read-only sensor frame patterns see.

    16 seeded-sinusoid GEQ bands + group scalars; real features arrive
    pre-chewed from the feature bus (§7, ADR-009) — patterns never touch
    raw audio, so a fake at this interface is faithful in shape.
    """

    N_BANDS = 16

    def __init__(self, seed: int):
        r = np.random.default_rng(seed ^ 0xFEA7)
        self._rates = (0.3 + 2.2 * r.random(self.N_BANDS)).astype(np.float32)
        self._phases = r.random(self.N_BANDS).astype(np.float32)

    def at(self, t: float) -> FeatureFrame:
        bands = (0.5 + 0.5 * np.sin(TWO_PI * (self._rates * t + self._phases))).astype(np.float32)
        bands.setflags(write=False)  # §7: the sensor frame is read-only
        return FeatureFrame(
            bands=bands,
            volume=float(bands.mean()),
            bass=float(bands[:4].mean()),
            mid=float(bands[4:10].mean()),
            high=float(bands[10:].mean()),
            beat_phase=(2.0 * t) % 1.0,
        )


# ---- mapping fixtures --------------------------------------------------------


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
