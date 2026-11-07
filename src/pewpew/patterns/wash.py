"""Wash — a slow color wash: hue rings drift out from the room's center."""

from __future__ import annotations

import numpy as np

from pewpew import Color, Float, Pattern, hsv


class Wash(Pattern):
    warpable = True

    color = Color((0.0, 0.8, 1.0), help="The color at the room's center; the rings turn the hue from there")
    # Hue turns per second at any one point. A turn passes yellow and blue
    # once each, so about one luminance flash per turn.
    speed = Float(0.02, 0.0, 0.1, "/s", help="Hue turns per second at any one point")
    spread = Float(0.5, 0.0, 2.0, help="Times the colors go round the wheel across the room")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        self.phase = (self.phase + dt * self.speed) % 1.0

    def render(self, x, y, z, index):
        r = np.hypot(x - 0.5, y - 0.5)
        c = self.color
        return hsv(c.turn + self.spread * r - self.phase, c.s, c.v)
