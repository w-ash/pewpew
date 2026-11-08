"""Points as per-axis float32 arrays: the convention every primitive shares.

A `Vec` is a batch of points with one array per axis, in x, y, z order,
like a GLSL `vec` evaluated at all points at once. The arrays broadcast, so
one component can be a scalar (for example time as a third noise axis).
Coordinates are normalized world units (architecture §3), and `MID` is the
middle of the world, the default pivot of every coordinate op.

A field is an array whose leading axes are spatial in reverse order, (H, W)
for x, y and (D, H, W) for x, y, z, as `field[row, col]` reads. Channel
axes, if any, follow the spatial axes.

Angle arguments are radians. An angle that is a coordinate (the `turn` that
`space.polar` gives) is a 0-1 turn, like every other coordinate.

`TWO_PI`, `wave` and `fade` are the scalar and shaping helpers ops share.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

# Float32 at run time (tests hold every primitive to it): NumPy 2 keeps
# float32 times a Python float in float32 (NEP 50), hence the numpy>=2
# floor. A NumPy float64 scalar is not weak, so every scalar argument is
# made a Python float where it enters (`plain`). The type admits any float,
# because NumPy's stubs widen that arithmetic to float64.
F32 = npt.NDArray[np.floating[Any]]

Vec = tuple[F32, ...]
VecLike = Sequence[npt.ArrayLike]

Axis = Literal["x", "y", "z"]
Plane = Literal["xy", "xz", "yz"]
Center = tuple[float, float, float]

MID: Center = (0.5, 0.5, 0.5)

AXES = "xyz"

# The plane around each axis: the plane of the other two.
AROUND: dict[Axis, Plane] = {"x": "yz", "y": "xz", "z": "xy"}


def vec(p: VecLike) -> Vec:
    """Return `p` as float32 arrays. An array that is float32 already is
    not copied. Refuse one array of points: its rows would read as axes."""
    if isinstance(p, np.ndarray):
        raise TypeError(
            f"points must be one array per axis, such as (x, y), got one array of shape {p.shape}; "
            "pass tuple(points.T) for an (N, D) array"
        )
    return tuple(np.asarray(c, dtype=np.float32) for c in p)


def plain(values: Sequence[float]) -> tuple[float, ...]:
    """Return `values` as Python floats. A NumPy float64 scalar (what
    `vec.wave`, `np.sin(t)` and `np.mean` return) would turn float32 math
    into float64; a Python float keeps it float32 (NEP 50)."""
    return tuple(float(v) for v in values)


def plain_center(center: Center) -> Center:
    """Return `center` as three Python floats (`plain`)."""
    x, y, z = center
    return float(x), float(y), float(z)


def per_axis(value: float | Sequence[float], d: int) -> tuple[float, ...]:
    """Return `value` as one Python float per axis of a `d`-axis point: a
    sequence as it is, a single value repeated."""
    return plain(value) if isinstance(value, Sequence) else (float(value),) * d


def axis_index(axis: str, p: Sequence[object]) -> int:
    """Return the index of `axis` ("x", "y" or "z") in `p`. Refuse an axis
    that `p` does not have."""
    i = AXES.find(axis) if len(axis) == 1 else -1
    if not 0 <= i < len(p):
        raise ValueError(f"axis {axis!r} is not one of {AXES[: len(p)]!r} for a {len(p)}-axis point")
    return i


def plane_axes(plane: str, p: Sequence[object]) -> tuple[int, int]:
    """Return the indexes of the two axes of `plane` ("xy", "xz" or "yz")."""
    if len(plane) != 2 or plane[0] == plane[1]:
        raise ValueError(f"plane {plane!r} is not one of 'xy', 'xz', 'yz'")
    return axis_index(plane[0], p), axis_index(plane[1], p)


def length(components: Sequence[F32]) -> F32:
    """Return the Euclidean length of a vector given per axis."""
    total = components[0] * components[0]
    for c in components[1:]:
        total = total + c * c
    return np.sqrt(total)


TWO_PI = 2.0 * math.pi


def wave(p):
    """Sine shaped to 0-1: wave(0)=0.5 rising."""
    return 0.5 + 0.5 * np.sin(TWO_PI * np.asarray(p))


def fade(dt: float, tau: float) -> float:
    """Frame-rate-independent decay factor: `v *= fade(dt, tau)` keeps
    exp(-dt/tau), where a per-frame constant (`v *= 0.94`) would depend on
    the frame rate (stumble #2). Returns a Python float, as the study did, so
    no numpy scalar changes a downstream dtype."""
    return math.exp(-dt / tau)
