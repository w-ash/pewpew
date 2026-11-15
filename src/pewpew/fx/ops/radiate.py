"""Radiating ops: light that leaves a point you set.

- `pulse`: soft shells that swell out of the point at a rate or on the
  beat, and fade as they travel; `jitter` makes each shell its own and
  `wander` gives each a point of its own near the center.
- `branches`: a tree that grows out of the point, trunks forking into
  branches and twigs, with beads of light running along its channels.

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

from pewpew.fx.op import (
    AUTO,
    CENTRE_ALONG,
    BindCtx,
    Cost,
    FrameCtx,
    Op,
    Rate,
    auto_plane,
    centre_args,
    normal_axis,
    stream,
)
from pewpew.fx.prims.vec import AXES, F32, TWO_PI, ease, length, smoothstep
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.mapping import spanned
from pewpew.params import Choice, Float, Int

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
            dark: F32 = np.ones(np.broadcast_shapes(*(axis.shape for axis in c.xyz)), np.result_type(*c.xyz))
            d = None  # the distance from the center, found once a shell starts there
            for shell in self.shells():
                if shell.offset != HOME:
                    point = self.ctx.at([f + o for f, o in zip(fractions, shell.offset, strict=True)])
                    away = length([axis - m for axis, m in zip(c.xyz, point, strict=True)])
                else:
                    if d is None:
                        d = length([axis - m for axis, m in zip(c.xyz, self.ctx.at(fractions), strict=True)])
                    away = d
                band = (away - shell.speed * shell.age) * (1.0 / shell.width)
                dark *= 1.0 - shell.level * np.exp(-(band * band))
            return 1.0 - dark

        return pulse


# ---- branches -------------------------------------------------------------------------

# The most trunks and levels a tree has. Draws are made for all of them, so
# a change of `trunks` or `depth` leaves every other branch as it was.
TRUNKS = 12
LEVELS = 7
# A fork has up to three arms: slots 0 and 1 part either way, slot 2 goes
# on ahead. Arm `slot` of the branch in row `r` of its level's draws is
# row `SLOTS * r + slot` of the next level's.
SLOTS = 3
# The columns of a branch's draws (`_tree_draws`), each in 0..1.
(TURN, RISE, LONG, FORK, LEAN, SPLIT, BOW_SIZE, BOW_TURN, GATE_PHASE, GATE_RATE, SWAY_PHASE, SWAY_RATE) = range(12)
DRAWS = 12
# At `jitter` 1: an arm turns up to SPREAD of `angle` more or less, and a
# fork's arms lean up to LEAN_BY of it to one side; a branch is up to
# LENGTHEN longer or shorter; up to THIRD of the forks grow a third arm
# and up to SINGLE one arm only; the beads move up to UNEVEN of their
# spacing either way, on a still field of WAVES sines whose crests are
# 1 / FINE to 2 / FINE units apart; and a branch's beads stop while a
# slow sine of its own is above GATE_AT.
SPREAD = 0.4
LEAN_BY = 0.4
LENGTHEN = 0.35
THIRD = 0.3
SINGLE = 0.25
UNEVEN = 0.5
WAVES = 4
FINE = 4.0
GATE_AT = 0.4
# An arm grows in from its fork, or shrinks back into it, over this span
# of its draw as `jitter` moves, so it never pops; a gate eases over
# GATE_EASE of its sine.
ARM_EASE = 0.08
GATE_EASE = 0.5
# An arm on its own turns this share of `angle`: it bends rather than splits.
ALONE = 0.35
# The third arm turns this share of `angle` out of the fork's plane.
AHEAD = 0.5
# A branch bows sideways by up to BOW of its length at its middle.
BOW = 0.12
# At `sway` 1 a branch's turn wanders by up to SWAY radians and its bow by
# up to SWAY_BOW of its length, each on a sine of its own whose period is
# SWAY_PERIOD to twice that; a gate's sine has GATE_PERIOD to twice that.
SWAY = 0.3
SWAY_BOW = 0.1
SWAY_PERIOD = 45.0
GATE_PERIOD = 8.0
# Which branches pass near which points is found again every REFRESH
# seconds while the tree sways, for every place the branches reach before
# the next time, with MOTION to spare.
REFRESH = 0.25
MOTION = 1.25
# Pairs of a point and a branch in one block of that search.
BLOCK = 1 << 18
# Each slot's side of its fork: slot 0 turns one way, slot 1 the other,
# slot 2 out of the fork's plane.
SIDES = np.array([1.0, -1.0, 0.0])


@dataclass(frozen=True, slots=True)
class Plan:
    """Which branches a tree has, one row each, parents before children:
    each one's parent's row (-1 for a trunk), its slot at its parent's fork,
    its level (0 for a trunk) and its draws; `arm`, how far it has grown in
    from its fork (an arm eases in or out as `jitter` moves; 1 for slot 0);
    `alone`, the share of `angle` slot 0 turns, less while its fork has no
    slot 1; and `levels`, the rows each level spans."""

    parent: np.ndarray
    slot: np.ndarray
    level: np.ndarray
    draws: np.ndarray
    arm: np.ndarray
    alone: np.ndarray
    levels: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class Tree:
    """A tree's branches as `Plan` lists them, in world units about its
    origin: where each starts, its chord (start to end), its bow (the
    sideways offset of its middle), its length, the path length `s0` from
    the origin to its start, and its glow's radius."""

    plan: Plan
    start: np.ndarray
    chord: np.ndarray
    bow: np.ndarray
    length: np.ndarray
    s0: np.ndarray
    width: np.ndarray

    def __len__(self) -> int:
        return len(self.length)

    @property
    def tips(self) -> float:
        """The longest path from the origin to a tip."""
        return float((self.s0 + self.length).max(initial=0.0))


@dataclass(frozen=True, slots=True)
class _Still:
    """The parts of a tree that do not move as it sways, read-only
    (`Branches.grow_at`): each branch's length, the path length `s0` to its
    start, its turn off its parent, its fork's split, its bow's size and
    its glow's radius; each trunk's turn and rise; and the axes of the
    map's plane, the wider first."""

    length: np.ndarray
    s0: np.ndarray
    turns: np.ndarray
    split: np.ndarray
    size: np.ndarray
    width: np.ndarray
    turn: np.ndarray
    rise: np.ndarray
    axes: tuple[int, ...]


@dataclass(slots=True)
class _Points:
    """The points a tree last lit (`Branches.points`): a copy of them,
    their distance from the origin, and the beads' still field at them,
    made when first read."""

    p: np.ndarray
    distance: np.ndarray
    field: np.ndarray | None = None


@lru_cache(maxsize=16)
def _tree_draws(key: int) -> tuple[np.ndarray, ...]:
    """Each level's draws: TRUNKS * SLOTS**level rows of DRAWS values in
    0..1, from the stream of the node's key and the level
    (pewpew.fx.op.stream). A pure function of the key, so the same seed
    grows the same tree."""
    out = []
    for level in range(LEVELS):
        rows = stream(key, level).random((TRUNKS * SLOTS**level, DRAWS))
        rows.setflags(write=False)
        out.append(rows)
    return tuple(out)


@lru_cache(maxsize=16)
def _uneven(key: int) -> tuple[np.ndarray, np.ndarray]:
    """The still field that moves the beads at `jitter`: WAVES sines, each
    a way (3, WAVES), in radians a unit, and an offset, from the stream of
    the node's key after the levels' (`_tree_draws`)."""
    draw = stream(key, LEVELS)
    way = draw.standard_normal((3, WAVES))
    way *= TWO_PI * FINE * (1.0 + draw.random(WAVES)) / np.sqrt((way * way).sum(0))
    return way, TWO_PI * draw.random(WAVES)


def _unit(v: np.ndarray) -> np.ndarray:
    """Each row of `v` scaled to length 1."""
    return v / np.maximum(np.sqrt((v * v).sum(-1, keepdims=True)), 1e-12)


def _across(d: np.ndarray, normal: int, squash: float, turn: np.ndarray) -> np.ndarray:
    """A unit vector across each direction of `d`, turned by `turn`
    (radians) about it out of the map's plane (`normal` the axis across
    it), but only as far as `squash` lets it out: at 0 it lies in the
    plane."""
    j, k = (normal + 1) % 3, (normal + 2) % 3
    first = np.zeros_like(d)  # the normal crossed with `d`: across it, in the plane
    first[:, k], first[:, j] = d[:, j], -d[:, k]
    size = np.sqrt((first * first).sum(-1))
    lone = size < 1e-9  # `d` along the normal
    first[lone, j], size[lone] = 1.0, 1.0
    first /= size[:, None]
    if not squash:
        return first * np.where(np.cos(turn) < 0.0, -1.0, 1.0)[:, None]
    turn = np.arctan2(squash * np.sin(turn), np.cos(turn))
    return np.cos(turn)[:, None] * first + np.sin(turn)[:, None] * np.cross(d, first)


def _wobble(rows: np.ndarray, clock: float, period: float, phase: int, rate: int, shift: float = 0.0) -> np.ndarray:
    """A slow sine per row of draws at `clock` seconds, its period from
    `period` to twice that and its phase from the row's draws."""
    speed = TWO_PI / (period * (1.0 + rows[:, rate]))
    return np.sin(speed * clock + TWO_PI * rows[:, phase] + shift)


def _near(p: np.ndarray, tree: Tree, reach: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each pair of a point of `p` ((N, 3) float32) and a branch of `tree`
    whose chord passes within that branch's `reach` of it, as the points'
    and the branches' rows, the points' in order."""
    count = len(tree)
    start, chord = tree.start, tree.chord
    # p @ k gives -2 p.a + |a|^2, which with |p|^2 is the squared distance
    # from p to each start a, and p.chord - a.chord.
    k = np.empty((4, 2 * count), np.float32)
    k[:3, :count], k[3, :count] = -2.0 * start.T, (start * start).sum(1)
    k[:3, count:], k[3, count:] = chord.T, -(start * chord).sum(1)
    l2 = (chord * chord).sum(1)
    inv_l2, l2, limit = (1.0 / l2).astype(np.float32), l2.astype(np.float32), (reach * reach).astype(np.float32)
    rows, cols = [], []
    step = max(1, BLOCK // max(count, 1))
    for lo in range(0, len(p) if count else 0, step):
        q = p[lo:lo + step]
        aug = np.ones((len(q), 4), np.float32)
        aug[:, :3] = q
        m = aug @ k
        d2, proj = m[:, :count], m[:, count:]
        d2 += (q * q).sum(1)[:, None]
        t = proj * inv_l2
        np.clip(t, 0.0, 1.0, out=t)
        # |p - a - t chord|^2 = |p - a|^2 - t (2 proj - t |chord|^2)
        part = t * l2
        part -= proj
        part -= proj
        part *= t
        d2 += part
        r, c = np.nonzero(d2 < limit)
        rows.append(r + lo)
        cols.append(c)
    if not rows:
        return np.zeros(0, np.intp), np.zeros(0, np.intp)
    return np.concatenate(rows), np.concatenate(cols)


class Branches(Op, op="branches"):
    """A tree of light that grows out of a point: `trunks` leave it, spread
    round it, each runs `reach` and forks, its arms turning `angle` apart,
    each `shrink` as long and as thin as the branch before, for `depth`
    levels, so the channels grow more and finer away from the point, like
    roots, lightning, a river delta or coral. Each branch bows gently and
    glows softly out to `width` from it at the trunk, never finer than the
    map's points. Beads of light, `beads` apart, run out from the point
    along the channels at `flow` a second (below 0, in), down both arms at
    a fork; between them the channels glow at `floor`. `jitter` makes the
    tree uneven: arms of their own angle and length, some forks in three,
    some not forking, beads that bunch, and paths whose beads stop for a
    while. `sway` lets the branches wander slowly, so the tree re-forms
    over minutes, and `grow` draws it from the point out to that share of
    its reach, with a soft tip. `turn` turns the trunks round the point,
    the first along the map's widest axis at 0. In a volume, `flat` at 1
    (the default) lays the tree into the map's main plane and lights the
    depth across it alike, so a rig spread mostly in one plane shows its
    forks; below 1 the tree leaves the plane too, at 0 spreading every
    way. The look's seed grows the tree: the same seed, the same tree."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    dims = frozenset({2, 3})
    fix = "a strip crosses a tree at a few points only; use pulse"
    trunks = Int(4, 1, TRUNKS, sweet=(2, 8), help="How many trunks leave the point")
    depth = Int(5, 1, LEVELS, sweet=(3, 6), help="How many levels each trunk forks into, the trunk the first")
    angle = Float(30.0, 10.0, 80.0, "°", sweet=(20.0, 50.0), help="How far the arms of a fork turn apart")
    shrink = Float(0.7, 0.5, 0.9, sweet=(0.6, 0.8), help="How long and thick each level is against the one before")
    reach = Float(0.2, 0.03, 0.6, sweet=(0.08, 0.3), help="How long a trunk is, in units")
    width = Float(0.06, 0.01, 0.3, sweet=(0.03, 0.15), help="How far a trunk's glow reaches; each level is thinner")
    jitter = Float(0.4, 0.0, 1.0, sweet=(0.2, 0.7),
                   help="How uneven the tree is: angles, lengths, forks in three or one, beads that bunch and stop")
    flow = Rate(0.3, -2.0, 2.0, "/s", sweet=(0.1, 0.8), flash_sensitive=True,
                help="Beads a second past each point, running out from the point; below 0 they run in")
    beads = Float(0.1, 0.02, 0.5, sweet=(0.05, 0.25), help="How far apart the beads run along a channel, in units")
    floor = Float(0.3, 0.0, 1.0, sweet=(0.1, 0.6), help="How bright the channels are between beads; 1 hides the beads")
    sway = Float(0.0, 0.0, 1.0, sweet=(0.2, 0.8), help="How far the branches wander as the tree slowly re-forms")
    grow = Float(1.0, 0.0, 1.0, sweet=(0.3, 1.0), help="How much of the tree is drawn, from the point out")
    turn = Float(0.0, 0.0, 360.0, "°", periodic=True, help="Turns the trunks round the point")
    flat = Float(1.0, 0.0, 1.0, sweet=(0.6, 1.0),
                 help="In a volume, lays the tree into the map's main plane and lights the depth across it")
    # A tree rooted off the map reaches only its rim, so the point stays on it.
    cx, cy, cz = centre_args(0.0, 1.0)
    along = CENTRE_ALONG
    examples = ("branches(4, 5, jitter=0.5, flow=0.4, flat=0.5)", 'branches(3, 6, angle=25, floor=1).palette("forest")',
                'branches(2, flow=0.6, sway=0.6).palette("ember")',
                'noise(1.5, 0.04).mult(branches(6, jitter=0.6, floor=0.5)).palette("ice")')
    cost = Cost(70.0, 60.0)

    @classmethod
    def shows(cls, name: str, a: Any, b: Any, args: Mapping[str, Any], spans: Sequence[float]) -> bool:
        """As `Op.shows`, but `flat` only in a volume, since on a panel the
        tree lies in its plane already; nor the center across the map's main
        plane while `flat` is 1, since the tree lies in that plane and lights
        the depth across it alike."""
        volume = sum(spanned(spans)) >= 3
        if name == "flat" and not volume:
            return False
        if name in CENTRE_ALONG and volume and args["flat"] >= 1.0 and (
                AXES.index(CENTRE_ALONG[name]) == normal_axis(auto_plane(spans))):
            return False
        return super().shows(name, a, b, args, spans)

    def __init__(self) -> None:
        super().__init__()
        # Seconds the node has run: the clock its slow sines read.
        self.clock = 0.0
        self._planned: tuple[tuple[Any, ...], Plan] | None = None
        self._still: tuple[tuple[Any, ...], _Still] | None = None
        self._grown: tuple[tuple[Any, ...], Tree] | None = None
        # The tree a swaying search grew for the next refresh, by its shape and epoch.
        self._next: tuple[tuple[Any, ...], Tree] | None = None
        # The points last lit, and the parts of their beads that do not move.
        self._points: _Points | None = None
        self._pairs: tuple[tuple[Any, ...], np.ndarray, np.ndarray] | None = None

    def step(self, dt: float) -> None:
        """As `Op.step`, and move the clock on."""
        super().step(dt)
        self.clock += dt

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self._planned = self._still = self._grown = self._next = self._points = self._pairs = None

    def spacing(self) -> float:
        """About how far apart the map's points are as the tree's distance
        reads them: the map's main plane or its volume shared evenly among
        its points, from the plane's at `squash` 0 to the volume's at 1. No
        glow is finer, or it would blink as it moves across the points."""
        spans = sorted(span for span, on in zip(self.ctx.spans, self.ctx.spanned, strict=True) if on)
        n = max(self.ctx.n, 1)
        plane = (math.prod(spans[-2:]) / n) ** (1.0 / max(len(spans[-2:]), 1))
        volume = (math.prod(spans) / n) ** (1.0 / max(len(spans), 1))
        return plane ** (1.0 - self.squash) * volume**self.squash

    @property
    def squash(self) -> float:
        """How far the tree, and the distance to it, reach out of the map's
        main plane: 1 - `flat` in a volume, 0 on a panel."""
        return 1.0 - self.flat if self.ctx.dims >= 3 else 0.0

    @property
    def normal(self) -> int:
        """The axis across the map's main plane."""
        return normal_axis(self.ctx.plane(AUTO))

    def _shape(self) -> tuple[Any, ...]:
        """The args the tree's shape reads."""
        return (self.trunks, self.depth, self.angle, self.shrink, self.reach, self.width, self.jitter, self.sway,
                self.turn, self.flat)

    def plan(self) -> Plan:
        """Which branches the tree has, planned again when `trunks`,
        `depth` or `jitter` moves."""
        key = (self.trunks, self.depth, self.jitter)
        if self._planned is None or self._planned[0] != key:
            self._planned = (key, self._make_plan())
        return self._planned[1]

    def _make_plan(self) -> Plan:
        draws, jitter, n = _tree_draws(self.ctx.key), self.jitter, self.trunks
        ids = np.arange(n)
        parent, slot, rows, arm, alone = [np.full(n, -1)], [np.zeros(n, np.intp)], [draws[0][:n]], [np.ones(n)], [
            np.ones(n)]
        levels = [(0, n)]
        for depth in range(1, self.depth):
            kids = draws[depth][ids[:, None] * SLOTS + np.arange(SLOTS)]  # (parents, slot, draw)
            grown = np.stack([np.ones(len(ids)), 1.0 - smoothstep((SINGLE * jitter - kids[:, 1, FORK]) / ARM_EASE),
                              smoothstep((THIRD * jitter - kids[:, 2, FORK]) / ARM_EASE)], axis=1)
            at, by = np.nonzero((grown > 0.0).T)  # slot, then parent
            parent.append(levels[-1][0] + by)
            slot.append(at)
            rows.append(kids[by, at])
            arm.append(grown[by, at])
            alone.append(np.where(at == 0, ALONE + (1.0 - ALONE) * grown[by, 1], 1.0))
            ids = ids[by] * SLOTS + at
            levels.append((levels[-1][1], levels[-1][1] + len(ids)))
        level = np.repeat(np.arange(len(levels)), [hi - lo for lo, hi in levels])
        return Plan(np.concatenate(parent), np.concatenate(slot), level, np.concatenate(rows), np.concatenate(arm),
                    np.concatenate(alone), tuple(levels))

    def tree(self) -> Tree:
        """The tree now, grown again when an arg its shape reads moves, or
        each frame while it sways."""
        key = (*self._shape(), self.clock if self.sway else 0.0)
        if self._grown is None or self._grown[0] != key:
            self._grown = (key, self.grow_at(self.clock))
        return self._grown[1]

    def still(self) -> _Still:
        """The parts of the tree that do not move as it sways, made again
        when an arg its shape reads moves."""
        key = self._shape()
        if self._still is None or self._still[0] != key:
            self._still = (key, self._make_still())
        return self._still[1]

    def _make_still(self) -> _Still:
        plan, jitter = self.plan(), self.jitter
        draws, parent, slot, levels = plan.draws, plan.parent, plan.slot, plan.levels
        n = levels[0][1]
        # How long each branch is, and how far along the paths it starts.
        lengthen = 1.0 + LENGTHEN * jitter * (2.0 * draws[:, LONG] - 1.0)
        length, s0 = self.reach * lengthen, np.zeros(len(parent))
        for lo, hi in levels[1:]:
            up = parent[lo:hi]
            length[lo:hi] = length[up] * self.shrink * plan.arm[lo:hi] * lengthen[lo:hi]
            s0[lo:hi] = s0[up] + length[up]
        # Which way the trunks leave: evenly round the plane from `turn`
        # along the plane's wider axis, and in a volume each at its own
        # rise out of it, spread evenly from below to above.
        axes = sorted((AXES.index(axis) for axis in self.ctx.plane(AUTO)), key=lambda a: -self.ctx.spans[a])
        rows = draws[:n]
        turn = math.radians(self.turn) + TWO_PI * (np.arange(n) + 0.5 * jitter * (rows[:, TURN] - 0.5)) / n
        rise = (2.0 * np.argsort(np.argsort(rows[:, RISE], kind="stable"), kind="stable") + 1.0) / n - 1.0
        # How far each arm turns off its parent: two part either way, a
        # third goes on ahead out of the fork's plane.
        lean = LEAN_BY * jitter * (2.0 * draws[parent, LEAN] - 1.0)
        share = np.select([slot == 0, slot == 1], [(1.0 - lean) * plan.alone, 1.0 + lean], AHEAD)
        turns = math.radians(self.angle) * share * (1.0 + SPREAD * jitter * (2.0 * draws[:, TURN] - 1.0))
        split = TWO_PI * draws[:, SPLIT]
        size = BOW * (2.0 * draws[:, BOW_SIZE] - 1.0)
        width = np.maximum(self.width * self.shrink**plan.level, self.spacing())
        parts = (length, s0, turns, split, size, width, turn, rise)
        for part in parts:
            part.setflags(write=False)
        return _Still(*parts, tuple(axes))

    def grow_at(self, clock: float) -> Tree:
        """The tree at `clock` seconds: its still parts (`still`), moved
        while it sways."""
        plan, still, sway, squash, normal = self.plan(), self.still(), self.sway, self.squash, self.normal
        draws, parent, slot, levels = plan.draws, plan.parent, plan.slot, plan.levels
        n, axes, length = levels[0][1], still.axes, still.length
        turn, rise, turns, size = still.turn, still.rise, still.turns, still.size
        if sway:
            rows = draws[:n]
            turn = turn + sway * SWAY * _wobble(rows, clock, SWAY_PERIOD, SWAY_PHASE, SWAY_RATE)
            rise = np.clip(rise + sway * SWAY * _wobble(rows, clock, SWAY_PERIOD, SWAY_PHASE, SWAY_RATE, math.pi / 2),
                           -0.95, 0.95)
            turns = turns + sway * SWAY * _wobble(draws, clock, SWAY_PERIOD, SWAY_PHASE, SWAY_RATE)
            size = size + sway * SWAY_BOW * _wobble(draws, clock, SWAY_PERIOD, SWAY_PHASE, SWAY_RATE, math.pi)
        eye = np.eye(3)
        level = np.sqrt(1.0 - rise * rise)
        d = np.empty((len(parent), 3))
        d[:n] = _unit((level * np.cos(turn))[:, None] * eye[axes[0]] + (level * np.sin(turn))[:, None] * eye[axes[1]]
                      + (squash * rise)[:, None] * eye[normal])
        split = still.split
        for (lo, hi), (up_lo, up_hi) in zip(levels[1:], levels, strict=False):
            across = _across(d[up_lo:up_hi], normal, squash, split[up_lo:up_hi])
            up = parent[lo:hi] - up_lo
            way, side = d[up_lo:up_hi][up], across[up] * SIDES[slot[lo:hi]][:, None]
            if squash:
                side += (squash * (slot[lo:hi] == 2))[:, None] * np.cross(way, across[up])
            d[lo:hi] = _unit(np.cos(turns[lo:hi])[:, None] * way + np.sin(turns[lo:hi])[:, None] * side)
        chord = d * length[:, None]
        start = np.zeros((len(parent), 3))
        for lo, hi in levels[1:]:
            up = parent[lo:hi]
            start[lo:hi] = start[up] + chord[up]
        bow = (size * length)[:, None] * _across(d, normal, squash, TWO_PI * draws[:, BOW_TURN])
        return Tree(plan, start, chord, bow, length, still.s0, still.width)

    def gates(self, tree: Tree) -> tuple[np.ndarray, np.ndarray]:
        """How far each branch lets its beads through at its start and its
        end, 0 to 1: its parent's at its end, times its own, which closes
        for a while when its slow sine is high, as far as `jitter`."""
        plan = tree.plan
        start, end = np.ones(len(tree)), np.ones(len(tree))
        if not self.jitter:
            return start, end
        high = _wobble(plan.draws, self.clock, GATE_PERIOD, GATE_PHASE, GATE_RATE)
        end -= self.jitter * smoothstep((high - GATE_AT) / GATE_EASE)
        for lo, hi in plan.levels[1:]:
            start[lo:hi] = end[plan.parent[lo:hi]]
            end[lo:hi] *= start[lo:hi]
        return start, end

    def points(self, p: np.ndarray) -> _Points:
        """Points `p` with their still parts, kept while the points hold
        their values. Points of other values let go of the pairs (`near`)."""
        held = self._points
        if held is None or not np.array_equal(held.p, p):
            q = p.astype(np.float64)
            held = self._points = _Points(p.copy(), np.sqrt((q * q).sum(1)))
            self._pairs = None
        return held

    def near(self, points: _Points) -> tuple[np.ndarray, np.ndarray]:
        """Each pair of a point of `points` and a branch that may light it
        now (`_near`), kept while the points and the tree's shape hold.
        While the tree sways, found again every REFRESH seconds for every
        place each branch reaches until the next time."""
        p, shape = points.p, self._shape()
        epoch = math.floor(self.clock / REFRESH) if self.sway else 0
        key = (*shape, epoch)
        if self._pairs is not None and self._pairs[0] == key:
            return self._pairs[1], self._pairs[2]
        if self.sway:
            # The last search grew the tree at this refresh: the same clock, so the same tree.
            ahead = self._next
            now = ahead[1] if ahead is not None and ahead[0] == key else self.grow_at(epoch * REFRESH)
            then = self.grow_at((epoch + 1) * REFRESH)
            self._next = ((*shape, epoch + 1), then)
            moved = np.maximum(np.sqrt(((then.start - now.start) ** 2).sum(1)),
                               np.sqrt(((then.start + then.chord - now.start - now.chord) ** 2).sum(1)))
            moved += np.sqrt(((then.bow - now.bow) ** 2).sum(1))
            bow = np.maximum(np.sqrt((now.bow * now.bow).sum(1)), np.sqrt((then.bow * then.bow).sum(1)))
            rows, cols = _near(p, now, now.width + bow + MOTION * moved)
        else:
            tree = self.tree()
            rows, cols = _near(p, tree, tree.width + np.sqrt((tree.bow * tree.bow).sum(1)))
        self._pairs = (key, rows, cols)
        return rows, cols

    def light(self, p: np.ndarray) -> np.ndarray:
        """The tree's light at points `p` ((N, 3) float32, about the origin,
        squashed across the plane as the tree is): the brightest of each
        branch's soft glow, times its beads."""
        tree, points = self.tree(), self.points(p)
        rows, cols = self.near(points)
        out = np.zeros(len(p), np.float32)
        reach = self.grow * tree.tips
        drawn = tree.s0[cols] <= reach
        rows, cols = rows[drawn], cols[drawn]
        if not len(rows):
            return out
        gate0, gate1 = self.gates(tree)
        chord, bow = tree.chord[cols], tree.bow[cols]
        away = p[rows].astype(np.float64) - tree.start[cols]
        tmax = np.clip((reach - tree.s0[cols]) / tree.length[cols], 0.0, 1.0)
        t = np.clip((away * chord).sum(1) / (chord * chord).sum(1), 0.0, tmax)
        # The branch bows by `bend` of its bow at `t`, most at its middle.
        bend = 4.0 * t * (1.0 - t)
        off = away - t[:, None] * chord - bend[:, None] * bow
        width = tree.width[cols]
        glow = np.clip(1.0 - (off * off).sum(1) / (width * width), 0.0, 1.0) ** 3
        through = gate0[cols] + (gate1[cols] - gate0[cols]) * t
        bead = self.beads_at(points)[rows]
        np.maximum.at(out, rows, (glow * (self.floor + (1.0 - self.floor) * bead * through)).astype(np.float32))
        return out

    def beads_at(self, points: _Points) -> np.ndarray:
        """The beads' light at `points`, 0 to 1. A bead's place is its
        distance from the origin, nudged by a still, smooth field as far as
        `jitter`, so beads leave the origin down every branch and at a fork
        go on down both arms; and a point sees one train of beads, `flow` a
        second, where glows overlap and while the tree sways."""
        at = points.distance / self.beads
        if self.jitter:
            field = points.field
            if field is None:
                way, offset = _uneven(self.ctx.key)
                field = points.field = np.sin(points.p.astype(np.float64) @ way + offset).mean(1)
            at += self.jitter * UNEVEN * field
        return (0.5 + 0.5 * np.cos(TWO_PI * (at - self.phase("flow")))) ** 2

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def branches(c: Coords) -> np.ndarray:
            x, y, z = np.broadcast_arrays(*c.xyz)
            origin = self.ctx.at((self.cx, self.cy, self.cz))
            p = np.stack([x - origin[0], y - origin[1], z - origin[2]], axis=1).astype(np.float32)
            p[:, self.normal] *= self.squash
            return self.light(p)

        return branches
