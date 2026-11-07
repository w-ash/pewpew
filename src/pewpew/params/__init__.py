"""The param domain (ADR-006): what an op declares a user can set.

A param is a typed class attribute of an op. Its kind is one of
`float`, `int`, `bool`, `choice`, `color` or `palette`; a compound kind has
named parts (a color's `h`, `s`, `v`). The id of a param is its attribute
name; `group` is layout only. `ParamSet` holds one class's declarations
and their base values behind one validated write path, and `Bound` links
it to the object that reads them, where a float, an int or a color's part
can be driven by an offset (modulation). `probes` reads a describe record
for two values of a param that must render differently (liveness).

This package depends on nothing else in pewpew but `pewpew.classinfo`,
`pewpew.errors` and `pewpew.kit`.
"""

from __future__ import annotations

from pewpew.params.bound import Bound
from pewpew.params.kinds import Bool, Choice, Color, Float, Int, Palette, Param
from pewpew.params.paramset import ParamSet, declared_params
from pewpew.params.values import HSV, Gradient, Stop

__all__ = [
    "HSV", "Bool", "Bound", "Choice", "Color", "Float", "Gradient", "Int", "Palette", "Param", "ParamSet", "Stop",
    "declared_params",
]
