"""Color math past `pewpew.hsv`: OKLab and gradients.

ADR-001 keeps linear RGB as the working space and allows OKLab as a
blending helper that converts back to it. A `Palette` param's value is a
`Gradient`; `gradient_lut` turns it into a table once (it is cached), and
`sample` reads the table per pixel, which `Gradient.rgb` does in one call:

    from pewpew import Palette, Pattern
    from pewpew.color import EMBER, PRESETS

    class Glow(Pattern):
        palette = Palette(EMBER, presets=PRESETS)

        def render(self, x, y, z, index):
            return self.palette.rgb(x)
"""

from __future__ import annotations

from pewpew.color.gradient import (
    AURORA,
    CANDY,
    EMBER,
    FOREST,
    ICE,
    LUT_SIZE,
    MONO,
    OCEAN,
    PRESETS,
    SYNTHWAVE,
    gradient_lut,
    sample,
)
from pewpew.color.lab import linear_srgb, oklab, turn_hue

__all__ = [
    "AURORA",
    "CANDY",
    "EMBER",
    "FOREST",
    "ICE",
    "LUT_SIZE",
    "MONO",
    "OCEAN",
    "PRESETS",
    "SYNTHWAVE",
    "gradient_lut",
    "linear_srgb",
    "oklab",
    "sample",
    "turn_hue",
]
