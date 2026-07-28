"""GEQ — 16-band spectrum bars with peak-hold falloff on a 16x16 panel.
Exercises the features frame and band -> segment indexing.
"""

from __future__ import annotations

import numpy as np

from pewpew import Param, Pattern, bins, fade, hsv


class Geq(Pattern):
    name = "geq"
    fall = Param(0.35, 0.05, 2.0, "Fall seconds")

    def setup(self, n, x, y, z, index):
        self.levels = self.buffer("levels", 16)

    def before_render(self, dt, features):
        self.levels = np.maximum(features.bands, self.levels * fade(dt, self.fall))

    def render(self, x, y, z, index):
        band = bins(x, 16)
        level = self.levels[band]  # (16,) per-band state gathered per pixel
        lit = y <= level
        hue = band.astype(np.float32) / 16.0
        return hsv(hue, 1.0, np.where(lit, 1.0, 0.03))
