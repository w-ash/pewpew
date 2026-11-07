"""Linear sRGB to and from OKLab, vectorized in float32.

The module is `lab`, not `oklab`, so the `oklab` function that
`pewpew.color` exports does not hide it.

OKLab is Björn Ottosson's perceptual color space
(https://bottosson.github.io/posts/oklab/): a straight line in it keeps
its hue, so a blend from blue to white does not drift purple as one in
HSV or CIELAB does. `L` is lightness from 0 (black) to 1 (white); `a` and
`b` are the green-red and blue-yellow axes, and chroma is the distance
from the `L` axis. The matrices are the post's. pewpew's frames are
linear sRGB (ADR-001), so no transfer function is applied. Each matrix
product is written out as element-wise sums, not `@`: matmul goes through
the BLAS build NumPy ships with (Accelerate on a Mac, OpenBLAS on Linux),
whose kernels round differently, and every product here must be the same
bytes on every machine.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike

# Linear sRGB to cone response (LMS), and cube-rooted LMS to Lab.
_RGB_LMS = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ],
    dtype=np.float32,
)
_LMS_LAB = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ],
    dtype=np.float32,
)
# The inverses, as the post gives them.
_LAB_LMS = np.array(
    [
        [1.0, 0.3963377774, 0.2158037573],
        [1.0, -0.1055613458, -0.0638541728],
        [1.0, -0.0894841775, -1.2914855480],
    ],
    dtype=np.float32,
)
_LMS_RGB = np.array(
    [
        [4.0767416621, -3.3077115913, 0.2309699292],
        [-1.2684380046, 2.6097574011, -0.3413193965],
        [-0.0041960863, -0.7034186147, 1.7076147010],
    ],
    dtype=np.float32,
)


def _mix(matrix: np.ndarray, v: np.ndarray) -> np.ndarray:
    """`v @ matrix.T` for each color of `v`, (..., 3) -> (..., 3), in
    element-wise sums, so no BLAS kernel can change a bit."""
    return v[..., 0:1] * matrix[:, 0] + v[..., 1:2] * matrix[:, 1] + v[..., 2:3] * matrix[:, 2]


def oklab(rgb: ArrayLike) -> np.ndarray:
    """Linear sRGB (..., 3) as OKLab (..., 3) float32. A color outside the
    gamut converts too: its negative cone responses keep their sign."""
    lms = _mix(_RGB_LMS, np.asarray(rgb, dtype=np.float32))
    return _mix(_LMS_LAB, np.cbrt(lms))


def linear_srgb(lab: ArrayLike) -> np.ndarray:
    """OKLab (..., 3) as linear sRGB (..., 3) float32, not clipped: a color
    outside the gamut has a channel below 0 or above 1."""
    lms = _mix(_LAB_LMS, np.asarray(lab, dtype=np.float32))
    return _mix(_LMS_RGB, lms**3)


def turn_hue(rgb: ArrayLike, degrees: float) -> np.ndarray:
    """Linear sRGB (..., 3) with each color's hue turned by `degrees` in
    OKLab, keeping its lightness and chroma, as float32. A color the turn
    takes outside the gamut is clipped per channel to 0..1, which moves
    its hue: cheap per pixel, where `gradient_lut`'s turn is exact."""
    return np.clip(linear_srgb(turned(oklab(rgb), degrees)), 0.0, 1.0)


def turned(lab: np.ndarray, degrees: float) -> np.ndarray:
    """OKLab colors (..., 3) with each hue turned by `degrees`: `a` and `b`
    rotated, lightness and chroma kept. A new float32 array."""
    angle = math.radians(float(degrees))
    cos, sin = np.float32(math.cos(angle)), np.float32(math.sin(angle))
    out = np.array(lab, dtype=np.float32)
    a, b = out[..., 1].copy(), out[..., 2].copy()
    out[..., 1] = a * cos - b * sin
    out[..., 2] = a * sin + b * cos
    return out
