"""Fire — Fire2012-style heat simulation on a 16x32 panel. The stress test:
stateful stencil effect, RNG, world-coord sampling of an internal field.
"""

from __future__ import annotations

import math

import numpy as np

from pewpew import Param, Pattern, sample2d


class Fire(Pattern):
    name = "fire"
    cooling = Param(0.9, 0.0, 3.0, "Cooling/s")
    sparking = Param(10.0, 0.0, 30.0, "Sparks/s per column")
    rise = Param(14.0, 1.0, 40.0, "Rise rate")

    W, H = 16, 32  # internal heat-field resolution (columns, rows bottom-up)

    def setup(self, n, x, y, z, index):
        self.heat = self.buffer("heat", (self.H, self.W))

    def before_render(self, dt, features):
        cool = self.rng.random(self.heat.shape, dtype=np.float32) * (self.cooling * dt)
        self.heat = np.maximum(self.heat - cool, 0.0)

        lift = 1.0 - math.exp(-dt * self.rise)
        below = self.heat[:-1]
        up = (below + np.roll(below, 1, axis=1) + np.roll(below, -1, axis=1)) / 3.0
        # Vectorized diffusion reads all pre-frame rows simultaneously, unlike
        # a top-down in-place scalar loop — different (acceptable) diffusion.
        self.heat[1:] = self.heat[1:] * (1.0 - lift) + up * lift

        ignite = self.rng.random(self.W) < (self.sparking * dt)
        sparks = (0.7 + 0.3 * self.rng.random(self.W)).astype(np.float32)
        self.heat[0] = np.where(ignite, np.maximum(self.heat[0], sparks), self.heat[0])

    def render(self, x, y, z, index):
        h = sample2d(self.heat, x, y)
        # Blackbody-ish palette as clip arithmetic: black -> red -> yellow -> white.
        r = np.clip(h * 3.0, 0.0, 1.0)
        g = np.clip(h * 3.0 - 1.0, 0.0, 1.0)
        b = np.clip(h * 3.0 - 2.0, 0.0, 1.0)
        return np.stack([r, g, b], axis=1).astype(np.float32)
