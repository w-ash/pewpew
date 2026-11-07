"""A test-only op with one knob of each param kind, every one reaching the
pixels, so each kind's whole path (declaration, describe, parse, bind, live
set) runs in the liveness check and the describe contract. No built-in op
has a bool or a color knob."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from pewpew.color import EMBER, PRESETS, gradient_lut, sample
from pewpew.fx.op import Op
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.params import Bool, Choice, Color, Float, Int, Palette

ZOO = "zoo_test"


def define_zoo() -> type[Op]:
    """Define (and so register) op `ZOO` (fakes.with_test_ops)."""

    class ZooTest(Op, op=ZOO):
        """One knob of each kind, each shading ramps across the map."""

        label = "Zoo"

        sig = Sig.SOURCE
        out = Ty.RGB
        level = Float(0.5, 0.0, 1.0, help="Overall brightness")
        bands = Int(2, 1, 6, help="Ramps across the strip")
        invert = Bool(False, help="Run each ramp the other way")
        shape = Choice("ramp", {"ramp": "Ramp", "steps": "Steps", "flat": "Flat"}, group="Shape")
        color = Color((120.0, 1.0, 1.0), group="Shape")
        palette = Palette(EMBER, presets=PRESETS, group="Shape", help="Colors along each ramp")

        def build(self, inputs: Sequence[Fn]) -> Fn:
            def zoo(c: Coords) -> np.ndarray:
                x = c.x
                ramp = (x * self.bands) % 1.0
                t = {"ramp": ramp, "steps": np.floor(x * self.bands) / self.bands,
                     "flat": np.full_like(x, 0.5)}[self.shape]
                if self.invert:
                    t = 1.0 - t
                shade = self.level * (0.2 + 0.8 * t)
                frame = 0.5 * (self.color.rgb(shade) + sample(gradient_lut(self.palette), t) * shade[:, None])
                return frame.astype(np.float32, copy=False)

            return zoo

    return ZooTest
