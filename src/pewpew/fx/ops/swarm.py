"""Swarm ops: many moving points drawn as glow on a field over the map
(pewpew.fx.field), so drawing them costs one pass over the points, not
one per pixel, and the field reads anywhere (a coord op may sit above).

- `particles`: emitters, gravity and a curl-noise breeze; sparks, snow
  and fireflies are settings of one op.
- `attractor`: a Lorenz butterfly or a morphing Clifford cloud, its glow
  built up and faded over a trail.

On a strip the points move along it; on a panel in its plane; in a
volume in x, y and z, with the lattice's last axis up.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from pewpew.fx.field import Lattice
from pewpew.fx.op import BindCtx, Cost, FrameCtx, Op, Rate
from pewpew.fx.ops.sims import arrivals
from pewpew.fx.ops.source import DRIFT
from pewpew.fx.prims import noise as prim
from pewpew.fx.prims.vec import TWO_PI, fade
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.params import Choice, Float, Int

# Lattice nodes per point spacing for a glow: a blob a point wide still
# spans a few cells, so it moves smoothly between the points.
GLOW = 2


def _smoothstep(lo: float, hi: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - lo) * (1.0 / (hi - lo)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Particles(Op, op="particles"):
    """Sparks that drift, rise and fade: up to 256 at once, each born where
    the emit choice says, setting off in a random direction, falling or
    rising, drifting on a breeze and fading in and out. `rate` are born a
    second, each sets off at `speed`, falls or rises under `gravity`,
    drifts on a curl-noise breeze (`swirl`), and fades over its `life`.
    Sparks fly fast from the center and fall; snow drifts down from the
    top; fireflies hang anywhere and wander."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    stateful = True
    rate = Float(20.0, 0.0, 120.0, "/s", sweet=(2.0, 60.0), help="More sparks at once")
    life = Float(2.0, 0.1, 10.0, "s", sweet=(0.3, 6.0), help="Seconds each lives, fading in and out")
    speed = Float(0.2, 0.0, 2.0, "/s", sweet=(0.0, 1.0), help="How fast each spark sets off, in a random direction")
    gravity = Float(0.0, -2.0, 2.0, "/s²", sweet=(-1.0, 1.0), help="Pull upward: above 0 up, below 0 down")
    swirl = Float(0.0, 0.0, 1.0, "/s", help="How fast the breeze they drift on swirls")
    emit = Choice("centre", {"centre": "Center", "bottom": "Bottom", "top": "Top", "anywhere": "Anywhere"},
                  help="Where they are born: the center, along the bottom or top edge, or anywhere")
    size = Float(0.06, 0.02, 0.3, sweet=(0.03, 0.15), help="Radius of each particle's glow")
    examples = (
        'particles(30, 1.2, 0.8, -1, emit="centre")',
        'particles(12, 6, 0.05, -0.1, 0.3, "top").palette("ice")',
        'particles(8, 3, 0, 0, 0.3, "anywhere", 0.05).palette("forest")',
    )
    cost = Cost(69.0, 109.0)
    CAPACITY = 256
    _BREEZE_FREQ = 2.0  # breeze features per unit
    _BREEZE_CHANGE = 0.25  # how fast it changes, lattice units a second

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.lattice = Lattice.over(ctx, GLOW)
        self.half = np.array(self.lattice.span, np.float32) * 0.5  # the lattice's half-extent
        d = self.lattice.d
        self.pos = ctx.buffer("pos", (self.CAPACITY, d))  # world units from the centre
        self.vel = ctx.buffer("vel", (self.CAPACITY, d))
        self.age = ctx.buffer("age", self.CAPACITY, fill=1.0)  # a share of its life: 1 or more is dead
        self.lifetime = ctx.buffer("lifetime", self.CAPACITY, fill=1.0)  # its life, in seconds
        self.countdown = ctx.buffer("countdown", 1, np.float64)  # births still due (`arrivals`)
        self.clock = ctx.buffer("clock", 1, np.float64)  # the breeze's phase
        self.shown = np.zeros(self.lattice.shape, np.float32)

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        rng = ctx.rng()
        dt, d = ctx.dt, self.lattice.d
        self.clock[0] = (self.clock[0] + self._BREEZE_CHANGE * dt) % DRIFT
        born = np.flatnonzero(self.age >= 1.0)[: arrivals(self.countdown, self.rate, dt, rng, self.CAPACITY)]
        if len(born):
            self.pos[born] = self.births(len(born), rng)
            heading = rng.normal(size=(len(born), d))
            heading /= np.maximum(np.linalg.norm(heading, axis=1, keepdims=True), 1e-9)
            self.vel[born] = heading * self.speed
            self.age[born] = 0.0
            self.lifetime[born] = self.life * (0.75 + 0.5 * rng.random(len(born)))
        live = np.flatnonzero(self.age < 1.0)
        if len(live):
            self.vel[live, d - 1] += self.gravity * dt
            move = self.vel[live]
            if self.swirl:
                move = move + self.breeze(self.pos[live]) * self.swirl
            self.pos[live] += move * dt
            self.age[live] += dt / self.lifetime[live]
            self.age[live[(np.abs(self.pos[live]) > self.half + self.size).any(axis=1)]] = 1.0
        live = np.flatnonzero(self.age < 1.0)
        x = self.age[live]
        brightness = _smoothstep(0.0, 0.2, x) * (1.0 - _smoothstep(0.4, 1.0, x))
        at = self.lattice.unit(list(self.pos[live].T))
        glow = self.lattice.glow(at, brightness, self.size) * self.lattice.peak(self.size)
        self.shown = np.minimum(glow, 1.0)

    def births(self, count: int, rng: np.random.Generator) -> np.ndarray:
        """Where `count` new particles start, in world units from the centre."""
        d = self.lattice.d
        if self.emit == "centre":
            return np.zeros((count, d), np.float32)
        out = ((rng.random((count, d)) * 2.0 - 1.0) * self.half).astype(np.float32)
        if self.emit != "anywhere":
            out[:, -1] = self.half[-1] if self.emit == "top" else -self.half[-1]
        return out

    def breeze(self, pos: np.ndarray) -> np.ndarray:
        """The breeze at `pos` (world units from the centre), about 1 unit a
        second: curl noise in a plane or a volume, a noise along a strip."""
        q = [pos[:, a] * self._BREEZE_FREQ for a in range(pos.shape[1])]
        phase = float(self.clock[0])
        seed = self.ctx.seed
        if len(q) == 1:
            return prim.gradient([q[0], np.full_like(q[0], phase)], seed=seed)[:, None]
        if len(q) == 2:
            flow = prim.curl2(prim.gradient, [*q, np.full_like(q[0], phase)], seed=seed)
        else:
            flow = prim.curl3(prim.gradient, [q[0], q[1], q[2] + phase], seed=seed)
        return np.stack(flow, axis=1)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def particles(c: Coords) -> np.ndarray:
            return self.lattice.sample(self.shown, c)

        return particles


# Lorenz's system (Lorenz, "Deterministic Nonperiodic Flow", 1963) and the
# scale that puts its butterfly in -1..1 (x, y) and its wings upright (z).
_SIGMA, _RHO, _BETA = 10.0, 28.0, 8.0 / 3.0
_LORENZ_SCALE = np.array([1 / 20, 1 / 27, 1 / 24])
_LORENZ_MID = np.array([0.0, 0.0, 24.0])
_LORENZ_STEP = 0.01  # the longest step, in Lorenz time
_LORENZ_MOST = 64  # the most steps a frame
# Clifford's map (Pickover, "Chaos in Wonderland", 1994) about a classic
# setting, its a and b swung round as it morphs.
_CLIFFORD = (-1.4, 1.6, 1.0, 0.7)
_SWING = 0.25


def _lorenz(p: np.ndarray) -> np.ndarray:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return np.stack([_SIGMA * (y - x), x * (_RHO - z) - y, x * y - _BETA * z], axis=1)


class Attractor(Op, op="attractor"):
    """Glowing trails that fly round a looping butterfly or cloud, a strange
    attractor: points fly along a Lorenz
    butterfly, or hop across a Clifford cloud of filaments that slowly
    morphs, and their glow builds up and fades as the figure turns about
    the upright axis. `count` points glow for `trail` and turn at `spin`. On a panel the
    butterfly faces front, wings upright, and the flat Clifford cloud lies
    in the panel's plane and turns in it. Brightness is the glow against
    its mean over the lit cells, so a few heads and a dense cloud read
    alike."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    stateful = True
    dims = frozenset({2, 3})
    fix = "a strip shows only a line through it; use lissajous or particles"
    CAPACITY = 2000
    kind = Choice("lorenz", {"lorenz": "Lorenz", "clifford": "Clifford"},
                  help="Lorenz: a butterfly ribbon in 3D; Clifford: a flat cloud of filaments")
    count = Int(24, 1, CAPACITY, help="Points it draws: a few ribbons, or a dense cloud")
    speed = Rate(0.3, 0.0, 1.0, "Hz", help="How fast it moves: Lorenz points fly, a Clifford cloud morphs")
    spin = Rate(10.0, -90.0, 90.0, "°/s", period=360.0, sweet=(-30.0, 30.0), flash_sensitive=True,
                help="How fast the figure turns")
    size = Float(0.04, 0.02, 0.3, sweet=(0.03, 0.12), help="Radius of each point's glow")
    trail = Float(1.0, 0.1, 10.0, "s", sweet=(0.3, 4.0), help="How long its glow lasts")
    examples = ('attractor("lorenz", 24, 0.3, 10)', 'attractor("clifford", 2000, 0.05, 0, 0.04, 2).palette("ember")')
    cost = Cost(72.0, 84.0)
    _KINDS = tuple(kind.options)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.lattice = Lattice.over(ctx, GLOW)
        self.points = ctx.buffer("points", (self.CAPACITY, 3), np.float64)
        self.field = ctx.buffer("field", self.lattice.shape)
        self.drawing = ctx.buffer("drawing", 1, np.float64)  # 1 + the kind its points follow; 0 when new
        self.level = 1.0
        self.start()

    def start(self) -> None:
        """Put the points on the attractor of `kind`, unless they are."""
        which = self._KINDS.index(self.kind) + 1.0
        if self.drawing[0] == which:
            return
        rng = self.ctx.rng()
        if self.kind == "lorenz":
            p = rng.random((self.CAPACITY, 3)) * [30.0, 30.0, 40.0] + [-15.0, -15.0, 5.0]
            for _ in range(100):  # 2 time units: onto the butterfly
                p = p + 0.02 * _lorenz(p + 0.01 * _lorenz(p))
        else:
            p = np.zeros((self.CAPACITY, 3))
            p[:, :2] = rng.random((self.CAPACITY, 2)) * 2.0 - 1.0
            for _ in range(20):
                p = self.hop(p)
        self.points[...] = p
        self.drawing[0] = which

    def hop(self, p: np.ndarray) -> np.ndarray:
        """One step of Clifford's map, its shape at the speed's phase."""
        turn = TWO_PI * self.phase("speed")
        a0, b0, c, d = _CLIFFORD
        a, b = a0 + _SWING * math.sin(turn), b0 + _SWING * math.cos(turn)
        x, y = p[:, 0], p[:, 1]
        out = np.zeros_like(p)
        out[:, 0] = np.sin(a * y) + c * np.cos(a * x)
        out[:, 1] = np.sin(b * x) + d * np.cos(b * y)
        return out

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        self.start()
        p = self.points[: self.count]
        if self.kind == "lorenz":
            time = self.speed * ctx.dt  # Lorenz time: 1 a second at speed 1
            steps = min(math.ceil(time / _LORENZ_STEP), _LORENZ_MOST)
            for _ in range(steps):
                h = time / steps
                p = p + h * _lorenz(p + 0.5 * h * _lorenz(p))
            frame = (p - _LORENZ_MID) * _LORENZ_SCALE
        else:
            p = self.hop(p)
            _, _, c, d = _CLIFFORD
            frame = np.stack([p[:, 0] / (1.0 + c), np.zeros(len(p)), p[:, 1] / (1.0 + d)], axis=1)
        self.points[: self.count] = p
        glow = self.lattice.glow(self.placed(frame), np.ones(len(p), np.float32), self.size)
        keep = fade(ctx.dt, self.trail)
        self.field[...] = self.field * keep + glow * (1.0 - keep)
        lit = self.field[self.field > self.field.max(initial=0.0) * 1e-3]
        self.level = float(lit.mean()) if len(lit) else 1.0

    def placed(self, frame: np.ndarray) -> list[np.ndarray]:
        """Points in the attractor's frame (about -1..1, z up), turned by
        the spin, in lattice units: x, y, z in a volume, x and z (up) on a
        panel. The spin turns x into y about the up axis, so on a panel,
        which shows x and z, it turns a Clifford cloud (flat in x and z)
        x into z instead: about the up axis it would turn edge on."""
        turn = math.radians(self.phase("spin"))
        cos, sin = math.cos(turn), math.sin(turn)
        x, y, z = frame[:, 0], frame[:, 1], frame[:, 2]
        if self.lattice.d == 2 and self.kind == "clifford":
            axes = (x * cos - z * sin, x * sin + z * cos)
        else:
            x, y = x * cos - y * sin, x * sin + y * cos
            axes = (x, y, z) if self.lattice.d == 3 else (x, z)
        return [(0.5 + 0.45 * a).astype(np.float32) for a in axes]

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def attractor(c: Coords) -> np.ndarray:
            return 1.0 - np.exp(self.lattice.sample(self.field, c) * (-1.0 / self.level))

        return attractor
