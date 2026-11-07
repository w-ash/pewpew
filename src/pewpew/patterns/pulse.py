"""Pulse — the whole room breathes in one color."""

from __future__ import annotations

import numpy as np

from pewpew import Color, Float, Pattern, wave


class Pulse(Pattern):
    # Every unit shows the same colour, so one evaluation per bar is enough.
    units = "fixture"
    warpable = True
    color = Color((200.0, 1.0, 1.0), help="The color at the top of each breath")
    # One breath is one flash; 1/s keeps it well under the 3 Hz limit.
    speed = Float(0.2, 0.0, 1.0, "/s", help="Breaths per second")
    depth = Float(0.8, 0.0, 1.0, help="How far each breath dims, from 0 (not at all) to 1 (to black)")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        # Accumulated, not t * speed, so a live speed change does not jump.
        self.phase = (self.phase + dt * self.speed) % 1.0

    def render(self, x, y, z, index):
        v = 1.0 - self.depth * (1.0 - wave(self.phase))
        return self.color.rgb(np.full(x.shape, v))
