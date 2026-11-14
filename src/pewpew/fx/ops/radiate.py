"""Radiating ops: light that leaves a point you set.

- `pulse`: soft shells that swell out of the point at a rate or on the
  beat, and fade as they travel; `jitter` makes each shell its own and
  `wander` gives each a point of its own near the center.

The point is a share of the map's extent on each axis (`cx`, `cy`, `cz`;
`BindCtx.at`), and distance is true distance in world units, so a shell
is a sphere in a volume, a circle on a panel and two travelling glows on a
strip.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from pewpew.fx.op import CENTRE_ALONG, BindCtx, Cost, FrameCtx, Op, Rate, centre_args, stream
from pewpew.fx.prims.vec import F32, ease, length
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.params import Choice, Float

# The least time a shell takes to fade in from nothing, in seconds. It
# takes as long as it needs to swell its own width off the point (`Pulse.rise`).
FADE_IN = 0.15
# A beat closer than this to the last one starts no shell (2.5 a second at most).
BEAT_GAP = 0.4
# The beats a node remembers: more than live at once at BEAT_GAP and the longest life.
BEATS = 64
# The age of a slot that holds no beat, in seconds: past any life.
NO_BEAT = 1.0e6
# How far back a beat pulse fills its history when it starts: the longest life.
HISTORY = 20.0
# A beat slower than this, in seconds, fills no history: under 30 a minute is no tempo.
SLOWEST_BEAT = 2.0

# At `jitter` 1, a shell's start moves by up to this share of the spacing
# either way, its speed and width by up to these shares either way, and its
# peak falls by up to PEAK of full. SKIP of the shells are left out, and
# SKIP_EASE more fade out on the way, so a turn of `jitter` never pops one.
START = 0.4
SPEED = 0.3
WIDTH = 0.3
PEAK = 0.6
SKIP = 0.25
SKIP_EASE = 0.1
HOME = (0.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class Shell:
    """One shell this frame: its age in seconds, its speed and width, its
    level now (0 to 1), and where its point sits off the center args, as
    shares of the map's extent on each axis."""

    age: float
    speed: float
    width: float
    level: float
    offset: tuple[float, float, float] = HOME


@lru_cache(maxsize=1024)
def _draws(key: int, n: int) -> tuple[float, ...]:
    """Shell `n`'s own draws from the stream of the node's key and `n`
    (pewpew.fx.op.stream): five in 0..1 (its start, speed, width, peak and
    whether it is left out) and a point in the unit ball. A pure function
    of both, so a shell keeps its draws for its whole life and a steady
    pulse keeps no state for them."""
    draw = stream(key, n % 2**64)
    each = draw.random(5)
    way, reach = draw.standard_normal(3), draw.random() ** (1.0 / 3.0)
    norm = float(np.sqrt((way * way).sum())) or 1.0
    return (*each.tolist(), *(way * (reach / norm)).tolist())


class Pulse(Op, op="pulse"):
    """Soft shells of light that swell out of a point and fade at the end of
    their travel: one `rate` times a second, or one on each beat. Each shell
    is a soft band `width` wide that grows at `speed`. It fades in as it
    swells off the point, holds its full level, and eases out over the last
    `fade` of its `life`; where shells overlap they add as light does,
    never past full. `cx`, `cy` and `cz` set the point. `jitter` makes
    each shell its own: its start, speed, width and strength, and some
    shells left out, so the train is uneven; `wander` starts each from a
    point of its own, up to that share of the room from the center. A shell
    keeps its own for its whole life, and the look's seed chooses them.
    Shells are on their way from the first frame: a steady train as if it
    had always run, a beat train as if the beat had (one frame in, once
    the tempo is known)."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    stateful = True
    rate = Rate(0.5, 0.05, 2.0, "/s", sweet=(0.1, 1.0), flash_sensitive=True,
                help="Shells a second when steady: more is busier")
    sync = Choice("steady", {"steady": "Steady", "beat": "Beat"},
                  help="Steady starts shells at the rate; beat starts one on each beat")
    speed = Float(0.25, 0.02, 2.0, "/s", sweet=(0.05, 0.8), help="How fast each shell swells, in units a second")
    width = Float(0.15, 0.04, 0.6, sweet=(0.08, 0.4), help="How thick each shell is; more is softer")
    life = Float(3.0, 0.3, 20.0, "s", sweet=(1.0, 10.0), help="Seconds each shell lasts, start to end")
    fade = Float(0.4, 0.05, 1.0, sweet=(0.2, 0.8),
                 help="The share of its life a shell spends fading out at the end: 1 fades it from the start")
    # Off the map, a shell's reach (speed times life) may not touch it, so the center stays on it.
    cx, cy, cz = centre_args(0.0, 1.0)
    jitter = Float(0.0, 0.0, 1.0, sweet=(0.2, 0.8),
                   help="How uneven the shells are: each its own start, speed, width and strength, some left out")
    wander = Float(0.0, 0.0, 0.5, sweet=(0.05, 0.3),
                   help="How far each shell's own point strays from the center, as a share of the room")
    along = CENTRE_ALONG
    examples = ("pulse(1.0, life=4)", 'pulse(0.4, speed=0.15, width=0.3, life=6).palette("ice")',
                'pulse(sync="beat", speed=0.6, life=2).palette("ember")',
                'pulse(0.5, speed=0.12, life=6, jitter=0.8, wander=0.2).palette("ocean")')
    cost = Cost(5.4, 14.0)

    @classmethod
    def shows(cls, name: str, a: Any, b: Any, args: Mapping[str, Any], spans: Sequence[float]) -> bool:
        """As `Op.shows`, but `rate` only when steady: the beat sets when
        shells start."""
        if name == "rate" and args["sync"] == "beat":
            return False
        return super().shows(name, a, b, args, spans)

    def __init__(self) -> None:
        super().__init__()
        # The rate's phase, unwrapped: which shell the phase started last.
        self.born = 0.0

    def step(self, dt: float) -> None:
        """As `Op.step`, and count the shells the phase starts."""
        super().step(dt)
        self.born += self.rate * dt

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        # Seconds since each remembered beat and its number (filled history
        # counts down from -1), the beats counted, the beat's phase last
        # frame (-1: none yet), and whether the history is filled.
        self.beats = ctx.buffer("beats", BEATS, np.float64, fill=NO_BEAT)
        self.ids = ctx.buffer("ids", BEATS, np.float64, fill=0.0)
        self.count = ctx.buffer("count", 1, np.float64, fill=0.0)
        self.last = ctx.buffer("last", 1, np.float64, fill=-1.0)
        self.filled = ctx.buffer("filled", 1, np.float64, fill=0.0)

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        """Age the remembered beats, and remember a beat whose phase
        wrapped since last frame, at the moment in the frame it wrapped. On
        the second frame, once the tempo is known, fill the history
        (`fill`)."""
        np.minimum(self.beats + ctx.dt, NO_BEAT, out=self.beats)
        phase, last = float(ctx.features.beat_phase) % 1.0, float(self.last[0])
        self.last[0] = phase
        if last < 0.0:
            return
        if not self.filled[0]:
            self.filled[0] = 1.0
            if self.fill(phase, last, ctx.dt):
                return
        if phase >= last:
            return
        since = ctx.dt * phase / (phase + 1.0 - last)
        if self.beats.min() < BEAT_GAP:
            return
        slot = int(np.argmax(self.beats))
        self.beats[slot], self.ids[slot] = since, self.count[0]
        self.count[0] += 1.0

    def fill(self, phase: float, last: float, dt: float) -> bool:
        """Remember the beats of the last HISTORY seconds as if they had
        come at the tempo the phase moved at over `dt`, each BEAT_GAP or
        more after the one before, the last where the phase last wrapped:
        the beat runs on whether or not the pulse watched (pewpew.audio.beat
        free-runs at its last tempo), so a beat pulse starts with its train
        on its way as a steady one does. False, and nothing remembered,
        when the phase did not move or moves slower than SLOWEST_BEAT."""
        moved = (phase - last) % 1.0
        if dt <= 0.0 or moved <= 0.0 or dt / moved > SLOWEST_BEAT:
            return False
        period = dt / moved
        spacing = period * math.ceil(BEAT_GAP / period - 1e-9)
        ages = np.arange(phase * period, HISTORY, spacing)[:BEATS]
        self.beats[: len(ages)] = ages
        self.ids[: len(ages)] = -1.0 - np.arange(len(ages))
        return True

    def shells(self) -> list[Shell]:
        """Each shell alive this frame."""
        if self.sync == "beat":
            pairs = sorted(zip(self.beats.tolist(), self.ids.tolist(), strict=True))
            made = (self.shell(int(n), age) for age, n in pairs if age < self.life)
            return [shell for shell in made if shell is not None]
        # Steady shells start each time the phase passes a whole number, so
        # the k-th youngest started (frac + k) / rate ago: no state, and a new
        # rate shows at once. `jitter` moves each start by up to START of the
        # spacing, so the one the phase starts next may already be out.
        start = self.phase("rate") % 1.0
        newest = round(self.born - start)
        early = START * self.jitter
        out = []
        k = -1 if early else 0
        while (start + k - early) / self.rate < self.life:
            n = newest - k
            shift = early * (2.0 * _draws(self.ctx.key, n)[0] - 1.0) if early else 0.0
            age = (start + k - shift) / self.rate
            k += 1
            if 0.0 <= age < self.life and (shell := self.shell(n, age)) is not None:
                out.append(shell)
        return out

    def shell(self, n: int, age: float) -> Shell | None:
        """Shell number `n` at `age` seconds, or None when `jitter` leaves
        it out: its own speed, width and peak at `jitter`, its own point at
        `wander`, each drawn once for it (`_draws`)."""
        jitter, wander = self.jitter, self.wander
        if not jitter and not wander:
            return Shell(age, self.speed, self.width, self.level(age))
        draws = _draws(self.ctx.key, n)
        speed = self.speed * (1.0 + SPEED * jitter * (2.0 * draws[1] - 1.0))
        width = self.width * (1.0 + WIDTH * jitter * (2.0 * draws[2] - 1.0))
        peak = 1.0 - PEAK * jitter * draws[3]
        if jitter:
            peak *= ease((draws[4] - SKIP * jitter) / (SKIP_EASE * jitter))
        if peak <= 0.0:
            return None
        x, y, z = (wander * v for v in draws[5:8])
        return Shell(age, speed, width, peak * self.level(age, width, speed), (x, y, z))

    def ages(self) -> list[float]:
        """The age in seconds of each shell alive this frame, youngest first."""
        return sorted(shell.age for shell in self.shells())

    def rise(self, width: float | None = None, speed: float | None = None) -> float:
        """Seconds a shell takes to fade in: as long as it takes to move its
        own width off the point, so the point brightens as the shell swells
        rather than switching on; at least FADE_IN and at most half its life.
        A shell of its own `width` and `speed`, or the node's."""
        width = self.width if width is None else width
        speed = self.speed if speed is None else speed
        return min(max(width / speed, FADE_IN), self.life / 2.0)

    def level(self, age: float, width: float | None = None, speed: float | None = None) -> float:
        """How bright a shell `age` seconds old is, 0 to 1: up over `rise`,
        full, then down over the last `fade` of its life, each a smoothstep,
        so it has no kink."""
        fading = self.fade * self.life
        return ease(age / self.rise(width, speed)) * (1.0 - ease((age - (self.life - fading)) / fading))

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def pulse(c: Coords) -> np.ndarray:
            fractions = (self.cx, self.cy, self.cz)
            centre = self.ctx.at(fractions)
            d = length([axis - m for axis, m in zip(c.xyz, centre, strict=True)])
            dark: F32 = np.ones_like(d)
            for shell in self.shells():
                away = d
                if shell.offset != HOME:
                    point = self.ctx.at([f + o for f, o in zip(fractions, shell.offset, strict=True)])
                    away = length([axis - m for axis, m in zip(c.xyz, point, strict=True)])
                band = (away - shell.speed * shell.age) * (1.0 / shell.width)
                dark = dark * (1.0 - shell.level * np.exp(-(band * band)))
            return 1.0 - dark

        return pulse
