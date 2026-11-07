"""Plasma — stateless nested sin fields. The happy-path control pattern:
written exactly as scalar thinking dictates, expected to vectorize untouched.
"""

from __future__ import annotations

import numpy as np

from authoring.surface import TWO_PI, Param, Pattern, hsv


class Plasma(Pattern):
    name = "plasma"
    speed = Param(0.5, 0.0, 2.0, "Speed")
    scale = Param(4.0, 1.0, 10.0, "Scale")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        # STUMBLE-1 [time-parameterization | shielded | papercut]: a wrapped
        # 0-1 phase only stays continuous inside sin() when its cycle
        # multipliers are integers (TWO_PI * k * phase, k ∈ ℤ) — the first
        # draft used the throughput kernel's non-integer time rates and
        # popped at every wrap. Generic animation math, not array-specific,
        # but the 0-1 phase idiom makes it easy to hit.
        self.phase = (self.phase + dt * self.speed) % 1.0

    def render(self, x, y, z, index):
        u = self.scale * x
        v = self.scale * y
        w = self.scale * z
        a = np.sin(u * 1.7 + TWO_PI * 1.0 * self.phase)
        b = np.sin(v * 2.3 - TWO_PI * 2.0 * self.phase + np.sin(u * 3.1))
        c = np.sin((u + v + w) * 1.9 + TWO_PI * 3.0 * self.phase)
        p = (a + b + c) / 3.0
        return hsv(0.55 + 0.20 * p, 1.0, 0.35 + 0.65 * (0.5 + 0.5 * np.sin(np.pi * p)))
