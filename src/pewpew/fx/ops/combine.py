"""Combine ops: two inputs mixed into one, through the blend table that
mixes layers too (pewpew.fx.blend), and `modulate`, where a second input
warps the first's coordinates.

A combine reads `a` and `b` at the same points and blends `b` onto `a` by
`amount`. Two scalars give a scalar; with any rgb input the result is rgb,
a scalar read as grey. Nothing is clamped (as in a layer stack, the sinks
clip the frame).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import ClassVar

import numpy as np

from pewpew.fx.blend import BLENDS, Blend, blend_choice
from pewpew.fx.op import Cost, Op
from pewpew.fx.types import SAME, Coords, Fn, Port, Sig, Ty
from pewpew.params import Float


def _rows(v: np.ndarray, channels: int) -> np.ndarray:
    """`v` as an (N, channels) array: a scalar field as one column, or
    repeated as grey."""
    if v.ndim == 2:
        return v
    return np.repeat(v[:, None], channels, axis=1)


def _amount() -> Float:
    return Float(1.0, 0.0, 1.0, help="How much of the second pattern shows over the first")


class _Combine(Op):
    """What the combine ops share: inputs `a` and `b`, the `amount` of `b`
    blended on (each op declares it, after its other args), and the blend
    mode (`how`): `fixed`, or the op's own arg."""

    sig = Sig.COMBINE
    inputs = (Port("a"), Port("b"))
    out = SAME
    fixed: ClassVar[str] = Blend.NORMAL
    amount: Float  # declared by each op, after its other args

    def how(self) -> str:
        return self.fixed

    def build(self, inputs: Sequence[Fn]) -> Fn:
        first, second = inputs

        def combine(c: Coords) -> np.ndarray:
            a, b = first(c), second(c)
            channels = 3 if a.ndim == 2 or b.ndim == 2 else 1  # rgb when either is
            acc = _rows(a, channels).copy()
            BLENDS[self.how()](acc, _rows(b, channels), self.amount, np.empty_like(acc))
            return acc if channels == 3 else acc[:, 0]

        return combine


class Add(_Combine, op="add"):
    """Adds two patterns, light on light. `b` goes onto `a`."""

    fixed = Blend.ADD
    amount = _amount()
    examples = ("osc(4).add(noise(3), 0.5)", 'shape(0, 0.2).add(osc(10), 0.3).palette("ember")')
    cost = Cost(1.0, 4.0)


class Mult(_Combine, op="mult"):
    """One pattern masks another: dark where the mask is dark. `a` is
    multiplied by `b`."""

    label = "Multiply"
    fixed = Blend.MULTIPLY
    amount = _amount()
    examples = ("osc(4).mult(shape(0, 0.4))", 'noise(3).palette("ember").mult(osc(2, axis="y"))')
    cost = Cost(0.5, 2.0)


class Diff(_Combine, op="diff"):
    """Bright where two patterns disagree. It is the difference of `a` and `b`,
    for red, green and blue separately."""

    label = "Difference"
    fixed = Blend.DIFFERENCE
    amount = _amount()
    examples = ("osc(4).diff(osc(5, -0.1))", 'noise(3).diff(voronoi(4)).palette("synthwave")')
    cost = Cost(0.3, 1.9)


class BlendOp(_Combine, op="blend"):
    """Lays one pattern onto another, mixed as layers mix: the second onto
    the first. `b` goes onto `a`."""

    mode = blend_choice("How the second pattern mixes into the first")
    amount = _amount()
    examples = ('noise(2).palette("ember").blend(osc(3).posterize(2), "multiply", 0.6)',)
    cost = Cost(3.4, 4.0)

    def how(self) -> str:
        return self.mode


class Modulate(Op, op="modulate"):
    """Ripples one pattern with another: each point moves as far as the second
    says there. Each point of `in` moves by `amount` times `mod`. A color's red, green and blue move x, y and z."""

    label = "Ripple"  # not "Modulate", which a page would read as a modulator (a look's signal)
    sig = Sig.MODULATE
    inputs = (Port("in"), Port("mod"))
    out = SAME
    amount = Float(0.1, 0.0, 1.0, sweet=(0.02, 0.4), help="How strongly the second pattern warps the first")
    examples = ("osc(8).modulate(noise(3), 0.2)", 'osc(3, axis="u").modulate(noise(2, 0.07), 0.12).palette("ember")')
    cost = Cost(1.0, 2.6)

    @classmethod
    def gives(cls, inputs: Sequence[Ty]) -> Ty:
        return inputs[0]

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner, mod = inputs

        def modulate(c: Coords) -> np.ndarray:
            m = (mod(c) - 0.5) * self.amount
            dx, dy, dz = (m[:, 0], m[:, 1], m[:, 2]) if m.ndim == 2 else (m, m, m)
            return inner(replace(c, x=c.x + dx, y=c.y + dy, z=c.z + dz, u=c.u + dx))

        return modulate
