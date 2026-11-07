"""The types an effect program passes between its nodes (ADR-022).

A node's output is one of three value types, `Ty`:

    signal   one float per frame (signal ops, from M4)
    scalar   (N,) float32: a field, one value per point, usually 0 to 1
    rgb      (N, 3) float32: linear-light color per point

An op's signature, `Sig`, says what it does with its inputs: a `source`
reads only coordinates; a `coord` op changes the coordinates its input
reads, so it wraps what comes before it (Hydra's rule); a `color` op maps
values to values; a `combine` op mixes two inputs; a `modulate` op lets a
second input warp the first's coordinates; a `state` op folds what it
reads into state it keeps from frame to frame and shows that state (a
feedback field, a trail). A `Port` names one input and
the type it takes: `SAME` takes a scalar or rgb, and an op whose output is
`SAME` gives the type it reads (rgb when either of two inputs is rgb).

`Coords` are what every node evaluates at: the points' x, y, z, the
along-the-strip coordinate `u` and the stable `index`. A coord op changes
x, y, z and u; `index` is never warped (ADR-005 amendment 2026-11-05).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final, Literal

import numpy as np

from pewpew.fx.prims.vec import F32


class Ty(StrEnum):
    SIGNAL = "signal"
    SCALAR = "scalar"
    RGB = "rgb"


class Sig(StrEnum):
    SOURCE = "source"
    COORD = "coord"
    COLOR = "color"
    COMBINE = "combine"
    MODULATE = "modulate"
    STATE = "state"
    SIGNAL = "signal"


SAME: Final = "same"
PortTy = Ty | Literal["same"]

# What a port of each type accepts.
ACCEPTS: dict[PortTy, frozenset[Ty]] = {
    SAME: frozenset({Ty.SCALAR, Ty.RGB}),
    Ty.SCALAR: frozenset({Ty.SCALAR}),
    Ty.RGB: frozenset({Ty.RGB}),
    Ty.SIGNAL: frozenset({Ty.SIGNAL}),
}


@dataclass(frozen=True, slots=True)
class Port:
    """One input of an op: its `name` and the type it takes."""

    name: str
    ty: PortTy = SAME

    @property
    def wording(self) -> str:
        """What the port takes, in words: "rgb or scalar", "scalar"."""
        return "rgb or scalar" if self.ty == SAME else str(self.ty)


@dataclass(frozen=True, slots=True, eq=False)
class Coords:
    """The points a node evaluates at: read-only float32 x, y, z and u,
    each (N,), and the int32 `index` of each point. `u = index / (n - 1)`
    (0 for one point) runs 0 to 1 along a strip in wiring order."""

    x: F32
    y: F32
    z: F32
    u: F32
    index: np.ndarray

    @classmethod
    def of(cls, x: F32, y: F32, z: F32, index: np.ndarray) -> Coords:
        """The coordinates of a binding's points, with `u` from `index`."""
        u = (index / np.float32(max(len(index) - 1, 1))).astype(np.float32)
        u.setflags(write=False)
        return cls(x, y, z, u, index)

    @property
    def xyz(self) -> tuple[F32, F32, F32]:
        return self.x, self.y, self.z

    def moved(self, xyz: tuple[F32, ...]) -> Coords:
        """These coordinates with x, y, z replaced by `xyz`; u and index kept."""
        x, y, z = xyz
        return replace(self, x=x, y=y, z=z)

    def along(self, axis: str) -> F32:
        """The coordinate named `axis`: "x", "y", "z" or "u"."""
        return {"x": self.x, "y": self.y, "z": self.z, "u": self.u}[axis]


# A built node: coordinates in, its field out ((N,) or (N, 3) float32).
Fn = Callable[[Coords], np.ndarray]
