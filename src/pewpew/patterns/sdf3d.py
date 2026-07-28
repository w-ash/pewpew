"""3D SDF — a spinning torus distance field, radius pulsing on the beat.
The counterweight datapoint: volumetric math is where arrays shine.
"""

from __future__ import annotations

import math

import numpy as np

from pewpew import TWO_PI, Param, Pattern, hsv, time, wave


class Sdf3d(Pattern):
    name = "sdf3d"
    # Known no-op: the torus is centered on the y-axis and render() rotates
    # about that same axis, an invariance the SDF has by construction
    # (2026-07-16 addendum). Ported as-is; a param-liveness check is the
    # intended way to catch this class of bug, not a fix here.
    spin = Param(0.15, 0.0, 1.0, "Rev/s")

    def __init__(self):
        self.angle = 0.0
        self.r = 0.1

    def before_render(self, dt, features):
        self.angle = (self.angle + dt * self.spin * TWO_PI) % TWO_PI
        self.r = 0.09 + 0.05 * wave(features.beat_phase)  # minor radius on the beat

    def render(self, x, y, z, index):
        px, py, pz = x - 0.5, y - 0.5, z - 0.5
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        rx = ca * px + sa * pz
        rz = ca * pz - sa * px
        ring = np.sqrt(rx * rx + rz * rz) - 0.30  # major radius
        d = np.sqrt(ring * ring + py * py) - self.r  # torus SDF
        v = np.where(d < 0.0, 1.0, 0.6 * np.exp(-np.abs(d) * 18.0))
        hue = 0.55 + d * 1.5 + 0.1 * wave(time(0.01))
        return hsv(hue, 0.8, v)
