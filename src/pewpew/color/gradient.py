"""Gradients as tables of linear RGB: `gradient_lut` builds one, `sample`
reads it per pixel, and the named presets a `Palette` param can offer."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from numpy.typing import ArrayLike

from pewpew.color.lab import linear_srgb, oklab, turned
from pewpew.kit import bins, hsv
from pewpew.params.values import HSV, Gradient, Stop

LUT_SIZE = 256
# How far a channel may sit outside 0..1 and still count as in the gamut:
# the OKLab round trip moves a color by about 2e-6.
_GAMUT_TOL = 1e-5
# Halvings of the chroma scale when a color is moved into the gamut:
# 2**-14 of the chroma puts a channel within 1e-4 of the gamut's edge, at
# two thirds of the cost of float32's full resolution; a driven `shift`
# may build a table every frame.
_HALVINGS = 14


@lru_cache(maxsize=256)
def gradient_lut(gradient: Gradient, shift: float = 0.0) -> np.ndarray:
    """`gradient` as a (LUT_SIZE, 3) float32 table of linear RGB, read-only,
    each stop's hue turned by `shift` degrees in OKLab first.

    Entry `i` is the color at the middle of `i/LUT_SIZE` to
    `(i+1)/LUT_SIZE`, the positions `sample` reads it for. Each stop's
    color converts from HSV as `pewpew.hsv` does; between two stops the
    color moves in a straight line in OKLab, so a blend keeps its hue. A
    color outside the gamut, a turned one too, keeps its lightness and hue
    and loses chroma until it fits: no channel is clamped on its own.
    Cached by value, and the cache shares each table, so it is read-only.
    """
    stops = gradient.stops
    at = np.array([stop.at for stop in stops], dtype=np.float32)
    lab = oklab(hsv([s.color.turn for s in stops], [s.color.s for s in stops], [s.color.v for s in stops]))
    if shift:
        lab = turned(lab, shift)
    x = (np.arange(LUT_SIZE, dtype=np.float32) + np.float32(0.5)) / np.float32(LUT_SIZE)
    # The stop each entry follows; at a hard edge (two stops at one
    # position), the later of the two.
    j = np.clip(np.searchsorted(at, x, side="right") - 1, 0, len(stops) - 2)
    width = at[j + 1] - at[j]
    w = np.divide(x - at[j], width, out=np.ones_like(x), where=width > 0)
    lut = _into_gamut(lab[j] + (lab[j + 1] - lab[j]) * w[:, None])
    lut.setflags(write=False)
    return lut


def sample(lut: np.ndarray, t: ArrayLike) -> np.ndarray:
    """The nearest entries of `lut` at positions `t`, from 0 (the first
    stop) to 1 (the last), clamped at both ends as `bins` is. Pass `t % 1`
    for a gradient that repeats. (N,3) float32 for an (N,) `t`."""
    return lut[bins(np.asarray(t, dtype=np.float32), len(lut))]


def _into_gamut(lab: np.ndarray) -> np.ndarray:
    """Linear RGB for each OKLab color in `lab` (M,3). A color outside the
    gamut first moves toward the `L` axis, keeping its lightness and hue,
    to the most chroma that fits: a gray between black and white always
    fits, and a scale that fits is found by halving."""
    rgb = linear_srgb(lab)
    out = _outside(rgb)
    if out.any():
        far = lab[out]
        lo = np.zeros(len(far), dtype=np.float32)
        hi = np.ones(len(far), dtype=np.float32)
        for _ in range(_HALVINGS):
            mid = (lo + hi) * np.float32(0.5)
            fits = ~_outside(linear_srgb(_with_chroma(far, mid)))
            lo, hi = np.where(fits, mid, lo), np.where(fits, hi, mid)
        rgb[out] = linear_srgb(_with_chroma(far, lo))
    return np.clip(rgb, 0.0, 1.0)  # float noise only: every color is now within _GAMUT_TOL


def _outside(rgb: np.ndarray) -> np.ndarray:
    """Whether each color (M,3) has a channel outside 0..1, past float noise."""
    return np.any((rgb < -_GAMUT_TOL) | (rgb > 1.0 + _GAMUT_TOL), axis=-1)


def _with_chroma(lab: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """`lab` with each color's chroma (its `a` and `b`) scaled by `scale`."""
    out = lab.copy()
    out[:, 1:] *= scale[:, None]
    return out


def _preset(label: str, *stops: tuple[float, float, float, float]) -> Gradient:
    """A gradient named `label` from `(at, h, s, v)` stops, each held as a float."""
    return Gradient(tuple(Stop(float(at), HSV(float(h), float(s), float(v))) for at, h, s, v in stops), label)


# Each preset keeps to two or three neighbouring hues, and most start dark:
# black costs nothing on LEDs, and saturated primaries read harsh.
EMBER = _preset("ember", (0, 0, 1, 0), (0.35, 5, 1, 0.35), (0.7, 22, 1, 0.9), (1, 42, 0.7, 1))
OCEAN = _preset("ocean", (0, 225, 1, 0.05), (0.45, 210, 0.95, 0.4), (0.8, 190, 0.8, 0.85), (1, 175, 0.35, 1))
AURORA = _preset("aurora", (0, 150, 1, 0.1), (0.4, 140, 0.85, 0.7), (0.7, 185, 0.7, 0.8), (1, 285, 0.65, 0.7))
SYNTHWAVE = _preset("synthwave", (0, 275, 1, 0.25), (0.5, 315, 0.9, 0.9), (1, 190, 0.85, 1))
FOREST = _preset("forest", (0, 120, 1, 0.08), (0.5, 105, 0.85, 0.45), (1, 65, 0.7, 0.9))
ICE = _preset("ice", (0, 220, 1, 0.25), (0.6, 200, 0.55, 0.75), (1, 195, 0.08, 1))
CANDY = _preset("candy", (0, 330, 0.55, 1), (0.5, 275, 0.4, 1), (1, 160, 0.45, 1))
MONO = _preset("mono", (0, 0, 0, 0), (1, 0, 0, 1))

PRESETS: tuple[Gradient, ...] = (EMBER, OCEAN, AURORA, SYNTHWAVE, FOREST, ICE, CANDY, MONO)
