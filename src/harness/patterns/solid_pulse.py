"""Reference pattern: a spatially graded pulse.

Exists to exercise the contract (t-parameterized, mapping-aware, seeded),
not to look good. Deterministic: same (t, mapping, params, seed) -> same
frame, always.
"""

from __future__ import annotations

import numpy as np

from harness.pattern import Params


class SolidPulse:
    name = "solid_pulse"

    def render(
        self,
        t: float,
        mapping: np.ndarray,
        params: Params,
        seed: int,
    ) -> np.ndarray:
        rate_hz = params.get("rate_hz", 0.5)
        # Phase offset from the seed so distinct seeds are distinguishable
        # in golden tests without any RNG in the hot path. Golden-ratio hash
        # spreads consecutive seeds far apart on the phase circle.
        phase = (seed * 0.6180339887498949) % 1.0
        pulse = 0.5 * (1.0 + np.sin(2.0 * np.pi * (rate_hz * t + phase)))
        x = mapping[:, 0]
        frame = np.zeros((mapping.shape[0], 3), dtype=np.float32)
        frame[:, 0] = pulse * x          # red ramps along the strip
        frame[:, 1] = pulse * (1.0 - x)  # green ramps the other way
        frame[:, 2] = 0.25 * pulse       # constant dim blue floor
        return frame
