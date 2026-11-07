"""Rainbow — hue by distance from the center, flowing inward. Port of the
studio prototype's tube shader (docs/studio/prototype/golden-tubes-3d.html:336,517).
"""

from __future__ import annotations

import numpy as np

from pewpew import Float, Pattern, hsv


class Rainbow(Pattern):
    warpable = True  # the hue is read from render's coordinates; `hsv` wraps it

    # Arithmetic: Contain's unit is the 3.83 m extent of the golden rings' pixel
    # centers (max of np.ptp over the axes of compile_rig(...).positions_m), and
    # the prototype has one spectrum per meter, so 3.83 spectra per unit.
    bands = Float(3.83, 0.5, 12.0, help="Spectra per unit distance")
    # The prototype moves 1/4 spectrum per second (t / 4000 with t in ms).
    speed = Float(0.25, 0.0, 2.0, "/s", help="Cycles per second, inward")

    def __init__(self):
        self.phase = 0.0

    def before_render(self, dt, features):
        self.phase = (self.phase + dt * self.speed) % 1.0

    def render(self, x, y, z, index):
        d = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2 + (z - 0.5) ** 2)
        # Adding the phase moves a fixed hue toward smaller d, so bands flow inward.
        return hsv(d * self.bands + self.phase, 1.0, 1.0)
