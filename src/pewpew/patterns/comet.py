"""Comet — moving head with a decaying trail. Exercises self.pixels
persistence and the float64 hash threshold that flips sparkle pixels near
its 0.995 cutoff.
"""

from __future__ import annotations

import math

import numpy as np

from pewpew import Param, Pattern, fade, hash01


class Comet(Pattern):
    name = "comet"
    speed = Param(0.4, 0.0, 2.0, "Rev/s")
    tail = Param(0.25, 0.01, 2.0, "Tail seconds")

    def __init__(self):
        self.head = 0.0
        self.keep = 1.0
        self.t = 0.0

    def before_render(self, dt, features):
        self.t += dt
        self.head = (self.head + dt * self.speed) % 1.0
        self.keep = fade(dt, self.tail)

    def render(self, x, y, z, index):
        d = np.abs(x - self.head)
        d = np.minimum(d, 1.0 - d)  # wrap-around distance
        core = np.where(d < 0.02, 1.0, np.exp(-40.0 * d))
        v = np.maximum(self.pixels[:, 0] * self.keep, core)  # trail: prev frame, decayed
        # Re-salted every 125ms so sparks twinkle and decay instead of
        # accumulating — self.pixels feeds this back next frame, so a static
        # hash would ratchet every sparked pixel to permanent white.
        salt = math.floor(self.t * 8.0)
        spark = hash01(x, self.seed, salt)
        v = np.where(spark > 0.995, np.minimum(1.0, v + 0.3), v)
        return np.stack([v, v * v, v**3], axis=1).astype(np.float32)
