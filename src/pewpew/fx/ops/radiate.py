"""Radiating ops: light that leaves a point you set.

- `pulse`: soft shells that swell out of the point at a rate or on the
  beat, and fade as they travel.

The point is a share of the map's extent on each axis (`cx`, `cy`, `cz`;
`BindCtx.at`), and distance is true distance in world units, so a shell
is a sphere in a volume, a circle on a panel and two travelling glows on a
strip.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pewpew.fx.op import CENTRE_ALONG, BindCtx, Cost, FrameCtx, Op, Rate, centre_args
from pewpew.fx.prims.vec import F32, length
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.params import Choice, Float

# The least time a shell takes to fade in from nothing, in seconds. It
# takes as long as it needs to swell its own width off the point (`Pulse.rise`).
FADE_IN = 0.15
# A beat closer than this to the last one starts no shell (2.5 a second at most).
BEAT_GAP = 0.4
# The beats a node remembers: more than live at once at BEAT_GAP and the longest life.
BEATS = 24
# The age of a slot that holds no beat, in seconds: past any life.
NO_BEAT = 1.0e6


class Pulse(Op, op="pulse"):
    """Soft shells of light that swell out of a point and fade as they
    travel: one `rate` times a second, or one on each beat. Each shell is a
    soft band `width` wide that grows at `speed`, fades in as it swells
    off the point and out over its `life`; where shells overlap they add as light
    does, never past full. `cx`, `cy` and `cz` set the point."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    stateful = True
    rate = Rate(0.5, 0.05, 2.0, "/s", sweet=(0.1, 1.0), flash_sensitive=True,
                help="Shells a second when steady: more is busier")
    sync = Choice("steady", {"steady": "Steady", "beat": "Beat"},
                  help="Steady starts shells at the rate; beat starts one on each beat")
    speed = Float(0.25, 0.02, 2.0, "/s", sweet=(0.05, 0.8), help="How fast each shell swells, in units a second")
    width = Float(0.15, 0.04, 0.6, sweet=(0.08, 0.4), help="How thick each shell is; more is softer")
    life = Float(3.0, 0.3, 8.0, "s", sweet=(1.0, 6.0), help="Seconds each shell lasts, fading as it goes")
    cx, cy, cz = centre_args()
    along = CENTRE_ALONG
    examples = ("pulse(1.0, life=4)", 'pulse(0.4, speed=0.15, width=0.3, life=6).palette("ice")',
                'pulse(sync="beat", speed=0.6, life=2).palette("ember")')
    cost = Cost(5.4, 14.0)

    @classmethod
    def shows(cls, name: str, a: Any, b: Any, args: Mapping[str, Any], spans: Sequence[float]) -> bool:
        """As `Op.shows`, but `rate` only when steady: the beat sets when
        shells start."""
        if name == "rate" and args["sync"] == "beat":
            return False
        return super().shows(name, a, b, args, spans)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        # Seconds since each remembered beat, and the beat's phase last frame (-1: none yet).
        self.beats = ctx.buffer("beats", BEATS, np.float64, fill=NO_BEAT)
        self.last = ctx.buffer("last", 1, np.float64, fill=-1.0)

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        """Age the remembered beats, and remember a beat whose phase
        wrapped since last frame, at the moment in the frame it wrapped."""
        np.minimum(self.beats + ctx.dt, NO_BEAT, out=self.beats)
        phase, last = float(ctx.features.beat_phase) % 1.0, float(self.last[0])
        self.last[0] = phase
        if last < 0.0 or phase >= last:
            return
        since = ctx.dt * phase / (phase + 1.0 - last)
        if self.beats.min() < BEAT_GAP:
            return
        self.beats[int(np.argmax(self.beats))] = since

    def ages(self) -> list[float]:
        """The age in seconds of each shell still alive this frame."""
        if self.sync == "beat":
            return sorted(float(a) for a in self.beats if a < self.life)
        # Steady shells start each time the phase passes a whole number, so
        # the k-th youngest is (frac + k) / rate old: no state, and a new
        # rate shows at once.
        start = self.phase("rate") % 1.0
        out = []
        while (age := (start + len(out)) / self.rate) < self.life:
            out.append(age)
        return out

    def rise(self) -> float:
        """Seconds a shell takes to fade in: as long as it takes to move its
        own width off the point, so the point brightens as the shell swells
        rather than switching on; at least FADE_IN and at most half its life."""
        return min(max(self.width / self.speed, FADE_IN), self.life / 2.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def pulse(c: Coords) -> np.ndarray:
            centre = self.ctx.at((self.cx, self.cy, self.cz))
            d = length([axis - m for axis, m in zip(c.xyz, centre, strict=True)])
            dark: F32 = np.ones_like(d)
            rise = self.rise()
            for age in self.ages():
                up = min(age / rise, 1.0)
                level = up * up * (3.0 - 2.0 * up) * (1.0 - age / self.life) ** 2
                band = (d - self.speed * age) * (1.0 / self.width)
                dark = dark * (1.0 - level * np.exp(-(band * band)))
            return 1.0 - dark

        return pulse
