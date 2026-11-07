"""Value objects that a param kind holds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from pewpew.kit import hsv


@dataclass(frozen=True, slots=True)
class HSV:
    """A color as hue, saturation and value over linear-light primaries.

    `h` is degrees from 0 to 360; `s` and `v` are 0 to 1. `v` scales
    brightness. `rgb` is the color as a frame; `turn` is the hue in the
    unit `pewpew.hsv` takes.
    """

    h: float
    s: float
    v: float

    @property
    def turn(self) -> float:
        """The hue as a 0-1 turn, the unit `pewpew.hsv` takes."""
        return self.h / 360.0

    def rgb(self, v: np.ndarray) -> np.ndarray:
        """This color as linear RGB with its value scaled by `v`, per pixel:
        `hsv(turn, s, self.v * v)`, (N,3) for an (N,) `v`. A scalar `v`
        gives one (3,) colour, which a frame must broadcast to (N,3)."""
        return hsv(self.turn, self.s, self.v * v)


@dataclass(frozen=True, slots=True)
class Stop:
    """One color of a gradient: `color` at position `at`, from 0 to 1."""

    at: float
    color: HSV


@dataclass(frozen=True, slots=True)
class Gradient:
    """Colors along a line from 0 to 1, as stops in order of `at`.

    The first stop is at 0 and the last at 1; two stops at one position
    make a hard edge. `label` names the gradient (a preset's name) or is
    "". The `Palette` kind checks these rules, and
    `pewpew.color.gradient_lut` samples a gradient that passed it. `rgb`
    is the gradient as a frame, as `HSV.rgb` is a color's.
    """

    stops: tuple[Stop, ...]
    label: str = ""

    def rgb(self, t: ArrayLike) -> np.ndarray:
        """This gradient as linear RGB at positions `t`, from 0 (the first
        stop) to 1 (the last), clamped past either end: (N,3) for an (N,)
        `t`. Reads the cached table (`pewpew.color.gradient_lut`), so it
        costs one lookup per pixel. Pass `t % 1` for a gradient that
        repeats."""
        from pewpew.color import gradient_lut, sample  # pewpew.color imports this module

        return sample(gradient_lut(self), t)
