"""GEQ — 16-band spectrum bars with peak-hold falloff on a 16×16 panel.
Exercises the features frame and band→segment indexing.
"""

from __future__ import annotations

import math

import numpy as np

from authoring.surface import Param, Pattern, hsv


class Geq(Pattern):
    name = "geq"
    fall = Param(0.35, 0.05, 2.0, "Fall seconds")

    def __init__(self):
        self.levels = np.zeros(16, dtype=np.float32)

    def before_render(self, dt, features):
        # STUMBLE-8 [branch->where | shielded | papercut]: per-band peak-hold
        # (`if band > level: level = band`) → np.maximum over the band array.
        self.levels = np.maximum(features.bands, self.levels * math.exp(-dt / self.fall))

    def render(self, x, y, z, index):
        # STUMBLE-9 [indexing | hit | friction]: binning pixels into bands is
        # `int(x * 16)` in scalar thinking — but x == 1.0 (the last pixel of
        # a 0-1 inclusive mapping) yields bin 16 and an IndexError. Verified
        # by running without the clamp. Every segment/bin pattern needs the
        # edge clamp, and nothing warns you until the rightmost pixel.
        band = np.minimum((x * 16.0).astype(np.int32), 15)
        # STUMBLE-10 [indexing | shielded | papercut]: reading per-band state
        # per pixel is fancy-indexing gather ((16,) → (N,)). The scalar
        # spelling `self.levels[band]` happens to BE the vectorized spelling
        # — it works, but the author has no idea they just did a gather.
        level = self.levels[band]
        lit = y <= level
        # STUMBLE-11 [dtype | shielded | papercut]: hue from the int32 band
        # array needs an explicit float cast; int/float promotion quietly
        # lands everything in float64 otherwise.
        hue = band.astype(np.float32) / 16.0
        return hsv(hue, 1.0, np.where(lit, 1.0, 0.03))
