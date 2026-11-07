"""Wave — bands of light cross the room in one direction.

Direction is measured on the plan in real x/y: the room map's Contain
normalization uses one scale for both axes, so 45 degrees is a true diagonal.
"""

from __future__ import annotations

import math

from pewpew import Color, Float, Pattern, wave


class Wave(Pattern):
    warpable = True

    color = Color((200.0, 1.0, 1.0), help="The color of the crests")
    # Crests passing any one point per second. This is the flash rate at
    # every point whatever the width, so the 1/s cap bounds it alone.
    speed = Float(0.25, 0.0, 1.0, "/s", help="Crests passing any one point per second")
    direction = Float(
        0.0, 0.0, 360.0, "°", periodic=True, widget="angle",
        help="Which way the bands cross the room, as the plan shows it",
    )
    width = Float(0.5, 0.1, 2.0, help="Room lengths from one crest to the next")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        self.phase = (self.phase + dt * self.speed) % 1.0

    def render(self, x, y, z, index):
        a = math.radians(self.direction)
        along = (x - 0.5) * math.cos(a) + (y - 0.5) * math.sin(a)
        v = wave(along / self.width - self.phase) ** 2  # narrower crests, darker troughs
        return self.color.rgb(v)
