"""Sparkle — random bars flare and fade."""

from __future__ import annotations

import numpy as np

from pewpew import Color, Float, Pattern, fade


class Sparkle(Pattern):
    # A whole bar flaring is the look; per pixel it is fine glitter.
    units = "fixture"
    warpable = True  # its state is per index, which no warp moves
    color = Color((40.0, 1.0, 1.0), help="The color of a spark")
    speed = Float(0.3, 0.0, 1.0, "/s", label="Sparks", help="How many sparks light a second on each fixture")
    tail = Float(0.6, 0.1, 2.0, "s", help="How long a spark lasts")

    # Seconds a unit waits after a spark before it can spark again. Each spark
    # is at most one flash, so no unit flashes more than twice in any second,
    # whatever the speed and the RNG draw.
    GAP = 0.6

    def setup(self, n, x, y, z, index):
        self.level = self.buffer("level", n)
        self.age = self.buffer("age", n, fill=self.GAP)

    def before_render(self, dt, features):
        self.level *= fade(dt, self.tail)
        np.minimum(self.age + dt, self.GAP, out=self.age)
        # Drawn every frame at the same shape, so the stream stays in step.
        roll = self.rng.random(self.n)
        ignite = (roll < self.speed * dt) & (self.age >= self.GAP)
        self.level[ignite] = 1.0
        self.age[ignite] = 0.0

    def render(self, x, y, z, index):
        return self.color.rgb(self.level)
