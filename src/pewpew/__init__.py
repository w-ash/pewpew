"""pewpew: the Python-first addressable-LED engine.

The top level is the ADR-005 authoring contract, what a pattern file
imports:

    from pewpew import Color, Float, Pattern, wave

    class Comet(Pattern):
        speed = Float(0.4, 0.0, 2.0, "/s", label="Speed", help="Turns of the strip per second")
        color = Color((20.0, 1.0, 1.0))

        def __init__(self):
            self.head = 0.0                     # plain state; a hot reload keeps it

        def before_render(self, dt, features):  # once per frame; RNG lives here
            self.head = (self.head + dt * self.speed) % 1.0

        def render(self, x, y, z, index):       # pure, over (N,) coord arrays
            return self.color.rgb(wave(x - self.head))

`render_sequence(Comet, line(300))` renders a deterministic sequence and a
`Renderer` runs a live loop. `time()` reads the renderer's frame time and
`self.rng` is seeded at bind, so the frames depend on the inputs only.

docs/authoring.md is the guide, and src/pewpew/patterns/ holds worked
examples. Importing this package loads no loop, sink, room or aura code.
"""

from __future__ import annotations

from pewpew.features import Event, FeatureFrame
from pewpew.kit import TWO_PI, bins, fade, hash01, hsv, sample2d, square, time, triangle, wave
from pewpew.mapping import Grouping, grid, lattice, line
from pewpew.params import HSV, Bool, Choice, Color, Float, Gradient, Int, Palette, Stop
from pewpew.pattern import Pattern
from pewpew.render import Renderer, render_sequence

__all__ = [  # noqa: RUF022  grouped by role
    # authoring contract
    "Pattern",
    # params
    "Float",
    "Int",
    "Bool",
    "Choice",
    "Color",
    "HSV",
    "Palette",
    "Gradient",
    "Stop",
    # idiom kit
    "TWO_PI",
    "time",
    "wave",
    "triangle",
    "square",
    "hsv",
    "fade",
    "bins",
    "sample2d",
    "hash01",
    # rendering
    "Renderer",
    "render_sequence",
    # fixtures and inputs
    "line",
    "grid",
    "lattice",
    "Grouping",
    "FeatureFrame",
    "Event",
]
