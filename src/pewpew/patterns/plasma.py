"""Plasma — soft fields of color that swirl and mix. Stateless nested sin
fields, the happy-path control pattern: written exactly as scalar thinking
dictates, and it vectorizes untouched.
"""

from __future__ import annotations

import numpy as np

from pewpew import TWO_PI, Float, Pattern, hsv


class Plasma(Pattern):
    warpable = True

    speed = Float(0.5, 0.0, 2.0, "/s", help="Cycles of the field per second")
    scale = Float(4.0, 1.0, 10.0, help="How many ripples fit across the map; higher is finer")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        # A wrapped 0-1 phase only stays continuous inside sin() when its
        # cycle multipliers are integers (TWO_PI * k * phase, k in Z).
        self.phase = (self.phase + dt * self.speed) % 1.0

    def field(self, x, y, z):
        """Return the plasma field at each point, in -1..1."""
        u = self.scale * x
        v = self.scale * y
        w = self.scale * z
        a = np.sin(u * 1.7 + TWO_PI * 1.0 * self.phase)
        b = np.sin(v * 2.3 - TWO_PI * 2.0 * self.phase + np.sin(u * 3.1))
        c = np.sin((u + v + w) * 1.9 + TWO_PI * 3.0 * self.phase)
        return (a + b + c) / 3.0

    def render(self, x, y, z, index):
        p = self.field(x, y, z)
        return hsv(0.55 + 0.20 * p, 1.0, 0.35 + 0.65 * (0.5 + 0.5 * np.sin(np.pi * p)))
