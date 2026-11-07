"""Color ops: map each point's value to a new one, at the same point.

`palette` turns a scalar field into colors through a gradient (OKLab
interpolation, pewpew.color); `hue` turns colors' hues; `contrast` and
`posterize` reshape values, a scalar's or each channel of rgb.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from pewpew.color import EMBER, PRESETS, gradient_lut, sample, turn_hue
from pewpew.fx.op import Cost, Op, Rate
from pewpew.fx.types import SAME, Coords, Fn, Port, Sig, Ty
from pewpew.params import Float, Int, Palette

SHIFT_STEP = 0.5  # degrees: a palette's shift turns its table in steps this fine


class PaletteOp(Op, op="palette"):
    """Colors a pattern through a gradient: its lowest values take the first
    color and its highest the last. `shift` turns every color's hue, in
    steps of 0.5°, and a color it turns past what LEDs show gets less
    strong, never a different hue; `cycle` slides the colors along the
    field, wrapping round."""

    sig = Sig.COLOR
    inputs = (Port("in", Ty.SCALAR),)
    out = Ty.RGB
    palette = Palette(EMBER, presets=PRESETS,
                      help="Press a dot to edit its color; the left end colors the low parts, the right the high")
    shift = Float(0.0, 0.0, 360.0, "°", periodic=True, help="Turns every color's hue")
    cycle = Rate(0.0, -1.0, 1.0, "/s", flash_sensitive=True, label="Slide",
                 help="Slides the colors along, round and round; give both ends one color for no seam")
    examples = ('noise(3).palette("ocean")', 'osc(4, 0.1).palette("aurora", shift=40, cycle=0.03)')
    cost = Cost(4.0, 9.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner = inputs[0]

        def palette(c: Coords) -> np.ndarray:
            v, turn = inner(c), self.phase("cycle")
            shift = round(self.shift / SHIFT_STEP) * SHIFT_STEP % 360.0  # a driven shift reuses its tables
            return sample(gradient_lut(self.palette, shift), (v + turn) % 1.0 if turn else v)

        return palette


class Hue(Op, op="hue"):
    """Turns every color's hue round the color wheel, keeping how light and how
    strong it is. `amount` sets how far, in degrees. A color turned past what
    LEDs show is clipped for red, green and blue separately, which moves its
    hue a little; a palette's `shift` turns its colors without that."""

    sig = Sig.COLOR
    inputs = (Port("in", Ty.RGB),)
    out = Ty.RGB
    amount = Float(0.0, 0.0, 360.0, "°", periodic=True, help="Degrees the hues turn")
    examples = ('noise(2).palette("ember").hue(120)', "below().hue(90)")
    cost = Cost(52.0, 11.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner = inputs[0]

        def hue(c: Coords) -> np.ndarray:
            rgb = inner(c)
            return turn_hue(rgb, self.amount) if self.amount else rgb

        return hue


class Contrast(Op, op="contrast"):
    """Pushes colors away from the middle gray for more punch, or toward it
    for less."""

    sig = Sig.COLOR
    inputs = (Port("in"),)
    out = SAME
    amount = Float(1.0, 0.0, 4.0, sweet=(0.5, 2.5), help="Above 1 sharpens, below 1 flattens toward gray")
    examples = ("noise(9).contrast(1.6)", 'voronoi(5).contrast(2).palette("forest")')
    cost = Cost(0.3, 2.9)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner = inputs[0]
        return lambda c: np.clip((inner(c) - 0.5) * self.amount + 0.5, 0.0, 1.0)


class Posterize(Op, op="posterize"):
    """Bands instead of a smooth ramp: values rounded down to a few steps from
    0 to 1. `levels` sets how many. On a fast-changing field the bands flicker."""

    sig = Sig.COLOR
    inputs = (Port("in"),)
    out = SAME
    levels = Int(4, 2, 16, help="Steps from dark to bright")
    examples = ("osc(2).posterize(4)", 'noise(2, 0.05).posterize(5).palette("synthwave")')
    cost = Cost(0.4, 1.9)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner = inputs[0]

        def posterize(c: Coords) -> np.ndarray:
            top = self.levels - 1
            return np.clip(np.floor(inner(c) * self.levels), 0.0, top) * (1.0 / top)

        return posterize
