"""pewpew — the Python-first addressable-LED engine.

This package is the ADR-005 authoring contract made real; it supersedes the
`bench/authoring/surface.py` prototype (kept as frozen study evidence) and
preserves its arithmetic bit-exactly. What a pattern author imports lives
here at the top level:

    from pewpew import Pattern, Param, hsv, wave, time

    class Comet(Pattern):
        name = "comet"
        speed = Param(0.4, 0.0, 2.0, "Rev/s")

        def setup(self, n, x, y, z, index):     # once per binding
            self.heat = self.buffer("heat", n)  # engine-managed state

        def before_render(self, dt, features):  # once per frame; RNG lives here
            self.head = (self.head + dt * self.speed) % 1.0

        def render(self, x, y, z, index):       # pure, over (N,) coord arrays
            return hsv(0.05, 1.0, wave(x - self.head))

Rendering that pattern is `render_sequence(Comet, line(300))` for a
deterministic sequence, or a `Renderer` for a live loop. Determinism is
load-bearing throughout: no wall clock, no unseeded RNG — `time()` resolves
against a renderer-scoped frame time and `self.rng` is seeded at bind.

Layout: `pattern` (contract), `kit` (idioms), `render` (engine), `mapping`
(coordinate fixtures), `features` (the sensor frame patterns see).
"""

from __future__ import annotations

from pewpew.features import FakeFeatures, FeatureFrame
from pewpew.kit import TWO_PI, bins, fade, hash01, hsv, sample2d, square, time, triangle, wave
from pewpew.mapping import grid, lattice, line
from pewpew.pattern import Param, Pattern
from pewpew.render import PatternError, Renderer, render_sequence

__all__ = [
    # authoring contract
    "Pattern",
    "Param",
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
    # engine
    "Renderer",
    "render_sequence",
    "PatternError",
    # fixtures and inputs
    "line",
    "grid",
    "lattice",
    "FeatureFrame",
    "FakeFeatures",
]
