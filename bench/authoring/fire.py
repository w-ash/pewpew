"""Fire — Fire2012-style heat simulation on a 16×32 panel. The stress test:
stateful stencil effect, RNG, world-coord sampling of an internal field.
"""

from __future__ import annotations

import math

import numpy as np

from authoring.surface import Param, Pattern


class Fire(Pattern):
    name = "fire"
    cooling = Param(0.9, 0.0, 3.0, "Cooling/s")
    sparking = Param(10.0, 0.0, 30.0, "Sparks/s per column")
    rise = Param(14.0, 1.0, 40.0, "Rise rate")

    W, H = 16, 32  # internal heat-field resolution (columns, rows bottom-up)

    def __init__(self):
        self.heat = np.zeros((self.H, self.W), dtype=np.float32)

    def before_render(self, dt, features):
        # STUMBLE-12 [reduction/scan | hit | friction — HEADLINE]: Fire2012 is
        # a neighbor stencil over a structured grid. self.pixels is an
        # unordered (N,3) point list — the stencil is inexpressible on it.
        # The idiom that unblocks it: the pattern owns an internal field at
        # its own resolution and render() samples the field at world coords.
        # Nothing in the contract documents this; without it fire is a
        # blocker. Proposed mitigation: ship a field/sample2d() kit helper +
        # document the internal-field idiom as first-class.
        cool = self.rng.random(self.heat.shape, dtype=np.float32) * (self.cooling * dt)
        self.heat = np.maximum(self.heat - cool, 0.0)

        lift = 1.0 - math.exp(-dt * self.rise)
        below = self.heat[:-1]
        up = (below + np.roll(below, 1, axis=1) + np.roll(below, -1, axis=1)) / 3.0
        # STUMBLE-13 [mutation/aliasing | shielded | friction]: the classic
        # loop runs top-down IN PLACE (heat[k] reads heat[k-1] already updated
        # this frame); the vectorized slice update is simultaneous — reads all
        # pre-frame values. Different (acceptable) diffusion semantics, but an
        # author porting the loop verbatim gets silently different flames, and
        # the in-place scalar spelling can't be expressed without a Python loop.
        self.heat[1:] = self.heat[1:] * (1.0 - lift) + up * lift

        # STUMBLE-14 [branch->where + RNG discipline | shielded | friction]:
        # per-column `if random() < chance: ignite` → mask + np.where; and all
        # draws must (a) live in before_render, never render (purity), and
        # (b) keep a stable per-frame draw count/order or determinism breaks
        # when any draw is made conditional. RNG placement is an engine rule
        # the author must be taught, not something the surface can infer.
        ignite = self.rng.random(self.W) < (self.sparking * dt)
        sparks = (0.7 + 0.3 * self.rng.random(self.W)).astype(np.float32)
        self.heat[0] = np.where(ignite, np.maximum(self.heat[0], sparks), self.heat[0])

    def render(self, x, y, z, index):
        # STUMBLE-15 [indexing | shielded | friction]: sampling the field at
        # world coords is nearest-cell boilerplate every field pattern
        # repeats: scale, +0.5 round, int cast, edge clamp (x==1.0 again),
        # then a 2D fancy-indexing gather. Prime sample2d() helper candidate.
        ci = np.minimum((x * (self.W - 1) + 0.5).astype(np.int32), self.W - 1)
        ri = np.minimum((y * (self.H - 1) + 0.5).astype(np.int32), self.H - 1)
        h = self.heat[ri, ci]
        # Blackbody-ish palette as clip arithmetic — the scalar if-chain
        # (black→red→yellow→white) absorbed by an idiom, not a stumble.
        r = np.clip(h * 3.0, 0.0, 1.0)
        g = np.clip(h * 3.0 - 1.0, 0.0, 1.0)
        b = np.clip(h * 3.0 - 2.0, 0.0, 1.0)
        return np.stack([r, g, b], axis=1).astype(np.float32)
