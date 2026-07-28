"""Typed-param declaration and override semantics (ADR-005 §5 / ADR-006).

The full typed tree is ADR-006's job; what is contractual today is that
declared `Param`s materialize to plain floats before `setup` runs, that a
flat override dict can drive them, and that an override naming something
undeclared is refused rather than silently landing on a dead attribute.
"""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Param, Pattern, Renderer, line


class Knobs(Pattern):
    name = "knobs"
    speed = Param(0.4, 0.0, 2.0, "Rev/s")
    tail = Param(0.25, 0.01, 2.0, "Tail seconds")

    def render(self, x, y, z, index):
        return np.zeros((index.size, 3), dtype=np.float32)


def test_params_materialize_to_floats_before_setup() -> None:
    seen: dict[str, object] = {}

    class Probe(Knobs):
        def setup(self, n, x, y, z, index):
            seen["speed"] = self.speed

    Renderer(Probe(), line(4))
    # setup must see a number, not the Param declaration object.
    assert seen["speed"] == 0.4
    assert isinstance(seen["speed"], float)


def test_override_drives_a_declared_param() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 1.5})
    assert renderer.pattern.speed == 1.5
    assert renderer.pattern.tail == 0.25  # untouched declarations keep defaults


def test_override_coerces_to_float() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 2})
    assert isinstance(renderer.pattern.speed, float)


def test_undeclared_override_is_refused() -> None:
    """A dead knob must not be creatable.

    The sdf3d `spin` addendum in bench/results/authoring-2026-07-16.md is the
    motivating evidence: a parameter that appears to work and provably does
    nothing, which neither the authoring surface nor golden frames caught. An
    override landing on an undeclared name is the same failure one step
    earlier, and here it is cheap to refuse outright.
    """
    with pytest.raises(ValueError, match="no Param named 'sped'"):
        Renderer(Knobs(), line(4), params={"sped": 1.5})


def test_refusal_names_the_declared_params() -> None:
    with pytest.raises(ValueError, match="speed, tail"):
        Renderer(Knobs(), line(4), params={"nope": 1.0})


def test_params_survive_rebind() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 1.5})
    renderer.rebind(line(9))
    assert renderer.pattern.speed == 1.5
    assert renderer.n == 9
