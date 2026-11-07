"""Fire — flames that rise and flicker. A Fire2012-style heat simulation
on a 16x32 panel, the stress test: stateful stencil effect, RNG,
world-coord sampling of an internal field.
"""

from __future__ import annotations

import math

import numpy as np

from pewpew import Float, Pattern, sample2d


class Fire(Pattern):
    warpable = True  # the heat is a grid sampled at render's coordinates, not per-pixel state

    cooling = Float(0.9, 0.0, 3.0, "/s", help="Heat each cell loses per second, at most")
    sparking = Float(10.0, 0.0, 30.0, "/s", help="Sparks per second in each column")
    rise = Float(14.0, 1.0, 40.0, "/s", help="How fast heat climbs; higher makes taller flames")

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
