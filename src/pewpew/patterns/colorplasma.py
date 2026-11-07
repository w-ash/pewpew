"""Color plasma — the plasma field painted with a three-color palette.

Each color has its own hue cycle. The field runs from the low color through
the middle color to the high color. The brightness shaping is plasma's own,
scaled by each color's brightness.
"""

from __future__ import annotations

import numpy as np

from pewpew import Color, Float, hsv
from pewpew.patterns.plasma import Plasma

SPREAD = 2.0


def _turn(turn: float, dt: float, period: float) -> float:
    """Advance a 0-1 hue turn by `dt` for a cycle of `period` seconds. A period of 0 holds."""
    return (turn + dt / period) % 1.0 if period > 0.0 else turn


def _cycle(group: str) -> Float:
    return Float(0.0, 0.0, 60.0, "s", text={0: "hold"}, label="Cycle", group=group,
                 help="Seconds for the hue to turn once round the wheel; 0 holds it")


class ColorPlasma(Plasma):
    # The defaults span plasma's own hues: 126 (low) to 198 (middle) to 270 (high).
    color_a = Color((126.0, 1.0, 1.0), label="Color", group="Low")
    cycle_a = _cycle("Low")
    color_b = Color((198.0, 1.0, 1.0), label="Color", group="Middle")
    cycle_b = _cycle("Middle")
    color_c = Color((270.0, 1.0, 1.0), label="Color", group="High")
    cycle_c = _cycle("High")

    def __init__(self):
        super().__init__()
        self.turn_a = self.turn_b = self.turn_c = 0.0

    def before_render(self, dt, features):
        super().before_render(dt, features)
        self.turn_a = _turn(self.turn_a, dt, self.cycle_a)
        self.turn_b = _turn(self.turn_b, dt, self.cycle_b)
        self.turn_c = _turn(self.turn_c, dt, self.cycle_c)

    def render(self, x, y, z, index):
        p = self.field(x, y, z)
        colors = (self.color_a, self.color_b, self.color_c)
        hues = np.array([c.turn for c in colors])
        turns = np.array([self.turn_a, self.turn_b, self.turn_c])
        palette = hsv(hues + turns, [c.s for c in colors], [c.v for c in colors])  # (3, 3): one RGB row per color
        # RGB blend, not a hue blend: a hue blend jumps when two cycling hues
        # pass 180 degrees apart.
        # The field sits near 0 (std 0.41 on line(300) and the canopy), so it is
        # stretched x2: each end color then holds about a quarter of the points.
        t = 0.5 + 0.5 * np.clip(SPREAD * p, -1.0, 1.0)
        rgb = np.stack([np.interp(t, (0.0, 0.5, 1.0), palette[:, k]) for k in range(3)], axis=-1)
        v = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(np.pi * p))
        return (rgb * v[:, None]).astype(np.float32)
