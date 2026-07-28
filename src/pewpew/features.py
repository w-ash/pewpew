"""The read-only sensor frame patterns see, plus its deterministic stand-in.

Patterns never touch raw audio: features arrive pre-chewed (melbanks, beat,
group scalars) from the feature bus (architecture §7), so `FeatureFrame` is
the whole of what `before_render` gets. `FakeFeatures` is the deterministic
stand-in used by tests, goldens and the bench until the real bus lands with
ADR-009; a fake at this interface is faithful in shape, and being seeded it
keeps whole sequences bit-reproducible.

Ported verbatim from `bench/authoring/surface.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pewpew.kit import TWO_PI


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
