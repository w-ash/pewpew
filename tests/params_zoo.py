"""A test-only pattern with one param of each kind, every one reaching the
pixels, so each kind's whole path (declaration, describe, parse, bind, live
set) runs in the liveness check and the describe contract."""

from __future__ import annotations

import numpy as np

from pewpew import Bool, Choice, Color, Float, Int, Palette, Pattern, line
from pewpew.color import EMBER, PRESETS, gradient_lut, sample
from pewpew.patterns import STUDY_CASES


class Zoo(Pattern):
    level = Float(0.5, 0.0, 1.0, help="Overall brightness")
    bands = Int(2, 1, 6, help="Ramps across the strip")
    invert = Bool(False, help="Run each ramp the other way")
    shape = Choice("ramp", {"ramp": "Ramp", "steps": "Steps", "flat": "Flat"}, group="Shape")
    color = Color((120.0, 1.0, 1.0), group="Shape")
    palette = Palette(EMBER, presets=PRESETS, group="Shape", help="Colors along each ramp")

    def render(self, x, y, z, index):
        ramp = (x * self.bands) % 1.0
        t = {"ramp": ramp, "steps": np.floor(x * self.bands) / self.bands, "flat": np.full_like(x, 0.5)}[self.shape]
        if self.invert:
            t = 1.0 - t
        shade = self.level * (0.2 + 0.8 * t)
        return 0.5 * (self.color.rgb(shade) + sample(gradient_lut(self.palette), t) * shade[:, None])


_MAPPING = line(64)
_MAPPING.setflags(write=False)
# Every pattern the param tests cover, as `STUDY_CASES` rows: (pattern,
# mapping, grouping).
PARAM_CASES = (*STUDY_CASES, (Zoo, _MAPPING, None))
