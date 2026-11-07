"""Blend modes: how one frame combines onto another, in linear light.

`BLENDS[mode](acc, src, weight, scratch)` blends `src` onto `acc` in
place. `acc`, `src` and `scratch` are (N, C) float32 arrays the caller
owns (C is 3 for colors, 1 for a scalar field); `scratch` is working
space whose contents are lost. `weight` (a layer's opacity, or an (N, 1)
array of it times its mask) is coerced to float32 first, so a float64
weight cannot change the bytes. Each mode computes a
result `r` and moves `acc` toward it by `weight`, `acc + (r - acc) * weight`,
except add, subtract and highlight, which scale what they add.

    normal      r = src
    add         acc + src
    screen      1 - (1 - acc)(1 - src): add without washing out to white
    multiply    acc * src
    max, min    the brighter or darker of the two, per channel
    difference  |acc - src|
    subtract    acc - src
    stencil     src where it has any color, acc where src is black
    highlight   acc + acc * src: src lights only what acc already lights

Only screen clamps: its formula assumes a white ceiling of 1 and darkens
above it (1.6 over 1.6 gives 0.64), so it reads both inputs clipped to
[0, 1] (ADR-021). A stack clamps once, after its last layer
(pewpew.compose); a frame that skips the blend goes out unclamped, and the
sinks clip every frame to 0-1 (pewpew.sinks.base.sanitize).

`LIGHTS_BLACK` holds the modes that show something over black: over an
empty accumulator, multiply, min, subtract and highlight stay black.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np

from pewpew.params import Choice

# A weight: one number, or one per row, (N, 1).
Weight = float | np.ndarray
# A weight as a kernel gets it, coerced to float32.
Coerced = np.floating | np.ndarray
# acc, src, weight, scratch
BlendFn = Callable[[np.ndarray, np.ndarray, Weight, np.ndarray], None]


class Blend(StrEnum):
    NORMAL = "normal"
    ADD = "add"
    SCREEN = "screen"
    MULTIPLY = "multiply"
    MAX = "max"
    MIN = "min"
    DIFFERENCE = "difference"
    SUBTRACT = "subtract"
    STENCIL = "stencil"
    HIGHLIGHT = "highlight"


# Each mode's label, by name: what a page and the catalog show for it. Max
# and min read as lighter and darker, as a person says it (RA-27 §8).
LABELS = MappingProxyType({mode.value: mode.value.capitalize() for mode in Blend} | {
    Blend.MAX.value: "Lighter", Blend.MIN.value: "Darker"})


def blend_choice(help: str, **meta: Any) -> Choice:
    """A param that picks a blend mode, normal by default: a layer's
    `blend` and the blend op's `mode` alike."""
    return Choice(Blend.NORMAL.value, dict(LABELS), help=help, **meta)


def _toward(acc: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    """Move `acc` toward the result held in `scratch` by `w`."""
    scratch -= acc
    scratch *= w
    acc += scratch


def _normal(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.copyto(scratch, src)
    _toward(acc, w, scratch)


def _add(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.multiply(src, w, out=scratch)
    acc += scratch


def _screen(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    # With a and b the inputs clipped to [0, 1], screen is a + b(1 - a), so
    # acc + (screen - acc) * w = acc + ((a - acc) + b(1 - a)) * w. In range
    # a - acc is 0 and this is acc + src(1 - acc) * w.
    a = np.clip(acc, 0.0, 1.0)
    np.clip(src, 0.0, 1.0, out=scratch)
    scratch *= 1.0 - a
    a -= acc
    scratch += a
    scratch *= w
    acc += scratch


def _multiply(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.multiply(acc, src, out=scratch)
    _toward(acc, w, scratch)


def _max(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.maximum(acc, src, out=scratch)
    _toward(acc, w, scratch)


def _min(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.minimum(acc, src, out=scratch)
    _toward(acc, w, scratch)


def _difference(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.subtract(acc, src, out=scratch)
    np.abs(scratch, out=scratch)
    _toward(acc, w, scratch)


def _subtract(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.multiply(src, w, out=scratch)
    acc -= scratch


def _stencil(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.subtract(src, acc, out=scratch)
    scratch *= w
    scratch *= src.max(axis=1, keepdims=True) > 0.0  # rows where src is black move nothing
    acc += scratch


def _highlight(acc: np.ndarray, src: np.ndarray, w: Coerced, scratch: np.ndarray) -> None:
    np.multiply(acc, src, out=scratch)
    scratch *= w
    acc += scratch


def _weighted(kernel: Callable[[np.ndarray, np.ndarray, Coerced, np.ndarray], None]) -> BlendFn:
    """`kernel` with its weight coerced to float32."""

    def blend(acc: np.ndarray, src: np.ndarray, weight: Weight, scratch: np.ndarray) -> None:
        kernel(acc, src, np.asarray(weight, dtype=np.float32) if isinstance(weight, np.ndarray) else np.float32(weight),
               scratch)

    return blend


BLENDS: Mapping[str, BlendFn] = MappingProxyType({
    Blend.NORMAL: _weighted(_normal),
    Blend.ADD: _weighted(_add),
    Blend.SCREEN: _weighted(_screen),
    Blend.MULTIPLY: _weighted(_multiply),
    Blend.MAX: _weighted(_max),
    Blend.MIN: _weighted(_min),
    Blend.DIFFERENCE: _weighted(_difference),
    Blend.SUBTRACT: _weighted(_subtract),
    Blend.STENCIL: _weighted(_stencil),
    Blend.HIGHLIGHT: _weighted(_highlight),
})

# What each mode does, in a line: the catalog's and the page's words.
ABOUT: Mapping[str, str] = MappingProxyType({
    Blend.NORMAL: "Shows the layer over what is below",
    Blend.ADD: "Adds the layer's light to what is below",
    Blend.SCREEN: "Adds light without washing out to white",
    Blend.MULTIPLY: "Darkens what is below where the layer is dark",
    Blend.MAX: "The brighter of the two, for red, green and blue separately",
    Blend.MIN: "The darker of the two, for red, green and blue separately",
    Blend.DIFFERENCE: "Bright where the two differ",
    Blend.SUBTRACT: "Takes the layer's light away from what is below",
    Blend.STENCIL: "Shows the layer where it has any color, what is below where it is black",
    Blend.HIGHLIGHT: "Lights only where what is below is already lit",
})

LIGHTS_BLACK = frozenset({Blend.NORMAL, Blend.ADD, Blend.SCREEN, Blend.MAX, Blend.DIFFERENCE, Blend.STENCIL})
