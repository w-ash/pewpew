"""Comet — moving head with a decaying trail. Exercises self.pixels
persistence and carries the float64 hash-threshold datapoint discovered in
bench_throughput.py kernel B.
"""

from __future__ import annotations

import math

import numpy as np

from authoring.surface import Param, Pattern


class Comet(Pattern):
    name = "comet"
    speed = Param(0.4, 0.0, 2.0, "Rev/s")
    tail = Param(0.25, 0.01, 2.0, "Tail seconds")

    def __init__(self):
        self.head = 0.0
        self.keep = 1.0
        self.t = 0.0

    def before_render(self, dt, features):
        self.t += dt
        self.head = (self.head + dt * self.speed) % 1.0
        # STUMBLE-2 [time-parameterization | shielded | friction]: every
        # classic trail effect ships a per-frame decay factor (`v *= 0.94`,
        # FastLED fadeToBlackBy) that is silently frame-rate-dependent; the
        # contract's dt-parameterization forces exp(-dt/tau). Right thing,
        # but a porting trap for every effect an author brings over.
        self.keep = math.exp(-dt / self.tail)

    def render(self, x, y, z, index):
        d = np.abs(x - self.head)
        # STUMBLE-3 [branch->where | shielded | papercut]: wrap-around
        # distance is min(d, 1-d) — scalar min() → np.minimum.
        d = np.minimum(d, 1.0 - d)
        # STUMBLE-4 [branch->where | shielded | papercut]: scalar
        # `1.0 if d < 0.02 else exp(-40d)` → np.where.
        # STUMBLE-5 [branch->where | shielded | friction]: np.where evaluates
        # BOTH branches — the exp runs on every pixel and is discarded under
        # the mask. Benign here; a NaN/domain-error trap in general (sqrt,
        # log, division) that scalar-thinking authors won't anticipate.
        core = np.where(d < 0.02, 1.0, np.exp(-40.0 * d))
        v = np.maximum(self.pixels[:, 0] * self.keep, core)  # trail: prev frame, decayed
        # STUMBLE-6 [dtype/threshold | hit | friction]: carried datapoint from
        # bench_throughput.py (kernel B): the sin-fract hash computed in
        # float32 disagrees with float64 near the 0.995 threshold and flips
        # sparkle pixels — the hash must run in float64. Discontinuities +
        # f32 coords make thresholds dtype-sensitive.
        # STUMBLE-17 [state-feedback | hit | friction]: the first draft used a
        # static per-pixel spark hash — and every spark pixel ratcheted to
        # permanent white, because self.pixels feeds the +0.3 back next frame
        # (fixed point of min(1, keep·v + 0.3) is 1.0). The contract's only
        # per-pixel state is the output buffer itself (render must stay pure,
        # before_render never sees coords), so any additive overlay MUST be
        # transient — here the hash is re-salted every 125 ms so sparks
        # twinkle and decay instead of accumulating. Caught by the runner's
        # statistics, not by eye. Engine mitigation candidate: sanctioned
        # private per-pixel state buffers alongside self.pixels.
        x64 = x.astype(np.float64)
        salt = math.floor(self.t * 8.0)
        spark = (np.sin(12.9898 * x64 + self.seed + salt) * 43758.5453) % 1.0
        v = np.where(spark > 0.995, np.minimum(1.0, v + 0.3), v)
        # STUMBLE-7 [shape assembly | shielded | papercut]: scalar authors
        # return a tuple (r,g,b); arrays need the (N,)→(N,3) stack + a final
        # astype because the f64 spark branch promoted the whole expression.
        return np.stack([v, v * v, v**3], axis=1).astype(np.float32)
