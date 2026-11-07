"""Graph ops: simulations on the map's own points, each linked to its
nearest neighbours (pewpew.fx.prims.knn), so heat, waves, reaction and
automata follow the layout: along a strip, across a panel, through a
volume, never across a gap with no points.

- `diffuse`: what it reads glows and bleeds to the next points, fading.
- `ripple`: a pond; drops fall at random and rings spread and bounce.
- `reaction`: Gray-Scott reaction-diffusion grown from a few seeds.
- `life`: a cyclic cellular automaton, whose noise turns into spirals,
  kept going by random sparks.

The graph is built once per map (`graph`) and kept for the next bind. Each
simulation keeps one value per point, so no coord op may sit above it.
Every step stays inside its explicit scheme's stable range at every
setting: an op takes as many steps a frame as its speed needs (up to
`MOST`), each one small enough, so a knob never makes it blow up.
Random events (drops, seeds, sparks) arrive as a Poisson process drawn
from the node's stream (`arrivals`), the first one on the first frame.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from functools import lru_cache

import numpy as np

from pewpew.fx.op import BindCtx, Cost, FrameCtx, Op
from pewpew.fx.prims import knn
from pewpew.fx.prims.knn import Neighbors
from pewpew.fx.prims.vec import F32, fade
from pewpew.fx.types import SAME, Coords, Fn, Port, Sig, Ty
from pewpew.params import Choice, Float, Int

# Neighbours per point by the map's dimension: on a strip, a grid or a
# lattice exactly the points next to it along each axis.
NEIGHBOURS = {1: 2, 2: 4, 3: 6}
# The most steps a simulation takes in one frame.
MOST = 32
# The most graphs kept for later binds.
_KEEP = 8


def _points(ctx: BindCtx) -> np.ndarray:
    """The map's points as (N, 3) float32."""
    return np.stack(ctx.coords.xyz, axis=1).astype(np.float32)


def graph(ctx: BindCtx) -> Neighbors:
    """The nearest-neighbour graph of `ctx`'s points (`NEIGHBOURS` each),
    built once per map: a later bind on the same points reuses it."""
    return _graph(_points(ctx).tobytes(), NEIGHBOURS[ctx.dims])


@lru_cache(maxsize=_KEEP)
def _graph(points: bytes, k: int) -> Neighbors:
    return knn.neighbors(np.frombuffer(points, np.float32).reshape(-1, 3), k)


def spacing(nbrs: Neighbors) -> float:
    """How far apart neighbouring points are: the median distance to each
    point's nearest neighbour (1 with no neighbours)."""
    near = nbrs.dist[:, 0] if nbrs.k else np.zeros(0, np.float32)
    near = near[np.isfinite(near) & (near > 0)]
    return float(np.median(near)) if len(near) else 1.0


def arrivals(countdown: np.ndarray, rate: float, dt: float, rng: np.random.Generator, most: int = MOST) -> int:
    """How many events of a Poisson process of `rate` a second fall in the
    next `dt` seconds (at most `most`). `countdown[0]`, a node buffer,
    holds the events still due before the next one, so the process runs
    on across frames; at 0, the first frame with a rate
    above 0 has one."""
    countdown[0] -= rate * dt
    count = 0
    while countdown[0] < 0.0 and count < most:
        countdown[0] += rng.exponential()
        count += 1
    if count == most:
        countdown[0] = max(countdown[0], 0.0)  # a backlog past `most` is dropped
    return count


def _landings(countdown: np.ndarray, rate: float, dt: float, rng: np.random.Generator, n: int) -> list[int]:
    """The points, of `n`, that the events of `rate` a second in the next
    `dt` seconds land on (`arrivals`), drawn from `rng`."""
    if not n:
        return []
    return [int(rng.integers(n)) for _ in range(arrivals(countdown, rate, dt, rng))]


def _bump(points: np.ndarray, at: np.ndarray, radius: float) -> F32:
    """A smooth bump of height 1 at `at`, `radius` wide, at each point."""
    d2 = ((points - at) ** 2).sum(axis=1)
    return np.exp(d2 * (-1.0 / (radius * radius))).astype(np.float32)


def _per_channel(step: Callable[[np.ndarray], np.ndarray], u: np.ndarray) -> np.ndarray:
    """`step` applied to a scalar field, or to each channel of rgb."""
    return step(u) if u.ndim == 1 else np.stack([step(u[:, k]) for k in range(u.shape[1])], axis=1)


class _GraphSim(Op):
    """What every graph op shares: per-point state, so not warpable, and
    the graph of the map's points."""

    stateful = True
    warpable = False

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.nbrs = graph(ctx)
        self.spacing = spacing(self.nbrs)


class Diffuse(_GraphSim, op="diffuse"):
    """Heat that bleeds from light to light: what it reads glows, spreads to
    the lights next to it (never across a gap with none) and fades."""

    sig = Sig.STATE
    inputs = (Port("in"),)
    out = SAME
    bleed = Float(6.0, 0.0, 40.0, "/s", sweet=(1.0, 20.0), help="How fast the glow spreads to the next points")
    decay = Float(2.0, 0.05, 20.0, "s", sweet=(0.5, 6.0), help="How long the glow lasts")
    examples = ("lissajous(3, 4, 5, 0.07, 3, 0.05).diffuse(6, 2.5)", 'shape(0, 0.1).diffuse(20, 1).palette("ice")')
    cost = Cost(17.0, 7.3)
    # Each step moves at most this share of the gap between neighbours
    # (the scheme holds up to 1).
    _MOST_RATE = 0.5

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.heat = ctx.buffer("heat", (ctx.n, *ctx.channels))

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        amount = self.bleed * ctx.dt
        steps = min(math.ceil(amount / self._MOST_RATE), MOST)
        u = self.heat
        for _ in range(steps):
            u = _per_channel(lambda v: knn.diffuse(v, self.nbrs, min(amount / steps, 1.0)), u)
        np.maximum(u * fade(ctx.dt, self.decay), inputs[0](self.ctx.coords), out=self.heat)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: self.heat


class Ripple(_GraphSim, op="ripple"):
    """A pond across the lights: drops fall at random points, and
    rings spread from each along the points, bounce off the ends and die
    away. Still water is 0.5; a crest is brighter, a trough darker. A
    drop lifts its point as much as it lowers the rest, and the whole
    pond settles at `damping`, so the water stays level however long it
    runs."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    speed = Float(0.5, 0.05, 2.0, "/s", sweet=(0.2, 1.0), flash_sensitive=True, help="How fast the rings spread")
    damping = Float(0.5, 0.1, 5.0, "/s", sweet=(0.2, 2.0),
                    help="How quickly ripples fade")
    drops = Float(0.5, 0.0, 4.0, "/s", sweet=(0.1, 1.5), flash_sensitive=True,
                  help="How often a drop falls, each at a random point")
    size = Float(0.08, 0.02, 0.3, sweet=(0.04, 0.15), help="Bigger splashes")
    examples = ("ripple(0.6, 0.8, 4, 0.1)", 'ripple(drops=1).palette("ice")')
    cost = Cost(91.0, 0.0)
    # The largest wave speed c a step takes: the undamped leapfrog scheme
    # holds c^2 < 2.
    _MOST_C = 0.7
    _HEIGHT = 0.6

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.points = _points(ctx)
        self.u = ctx.buffer("u", ctx.n)
        self.was = ctx.buffer("was", ctx.n)
        self.countdown = ctx.buffer("countdown", 1, np.float64)

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        for i in _landings(self.countdown, self.drops, ctx.dt, ctx.rng(), self.ctx.n):
            bump = _bump(self.points, self.points[i], self.size) * self._HEIGHT
            bump -= bump.mean()  # the water a drop lifts comes from the rest of the pond
            self.u += bump
            self.was += bump
        # A ring crosses about c / sqrt(k) gaps a step (the graph Laplacian
        # is about h^2 / k times the continuous one).
        travel = self.speed * ctx.dt * math.sqrt(self.nbrs.k) / self.spacing
        steps = min(math.ceil(travel / self._MOST_C), MOST)
        if not steps:
            return
        c = min(travel / steps, self._MOST_C)
        # Each step fades the whole pond, rings and level alike, so every
        # part of it settles at `damping`: on a map whose points fall in
        # groups the graph does not link, each group's level too.
        settle = math.exp(-self.damping * ctx.dt / steps)
        u, was = self.u.copy(), self.was
        for _ in range(steps):
            u, was = knn.wave_step(u, was, self.nbrs, c) * settle, u * settle
        self.u[...] = u
        self.was[...] = was

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: np.clip(0.5 + self.u, 0.0, 1.0)


# Gray-Scott feed and kill rates per regime, for diffusion 1 : 0.5 on a
# mean-of-neighbours Laplacian (Karl Sims, karlsims.com/rd.html; Pearson,
# "Complex Patterns in a Simple System", 1993).
REGIMES = {
    "coral": (0.0545, 0.062),
    "mitosis": (0.0367, 0.0649),
    "spots": (0.03, 0.062),
    "maze": (0.029, 0.057),
}


class Reaction(_GraphSim, op="reaction"):
    """Coral, dividing cells, spots or a maze that grow across the lights from
    a few seeds: two chemicals that feed, react and spread. Brighter is
    more of the second chemical."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    kind = Choice("coral", {name: name.capitalize() for name in REGIMES}, help="Coral, mitosis, spots or maze")
    size = Float(0.4, 0.15, 0.8, sweet=(0.25, 0.6), help="How big its shapes grow")
    speed = Float(60.0, 5.0, 240.0, "/s", sweet=(20.0, 120.0), help="How fast it grows")
    seeds = Float(0.2, 0.0, 4.0, "/s", sweet=(0.0, 1.0), help="New seeds a second at random points")
    examples = ('reaction("coral", 0.4, 120, 1)', 'reaction("maze", speed=90).contrast(1.6).palette("forest")')
    cost = Cost(133.0, 41.0)
    _GAIN = 3.0  # the second chemical tops out near 1 / _GAIN

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.points = _points(ctx)
        self.a = ctx.buffer("a", ctx.n, fill=1.0)
        self.b = ctx.buffer("b", ctx.n)
        self.countdown = ctx.buffer("countdown", 1, np.float64)
        if ctx.n and not self.b.any():  # new, not carried: seed it
            rng = ctx.rng()
            for _ in range(max(2, ctx.n // 150)):
                self.seed_at(int(rng.integers(ctx.n)))

    def seed_at(self, i: int) -> None:
        """A seed of the second chemical at point `i` and the points
        around it."""
        near = _bump(self.points, self.points[i], 3.0 * self.spacing) > 0.3
        self.a[near] = 0.25
        self.b[near] = 0.5

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        for i in _landings(self.countdown, self.seeds, ctx.dt, ctx.rng(), self.ctx.n):
            self.seed_at(i)
        feed, kill = REGIMES[self.kind]
        da, db = self.size, self.size / 2.0
        longest = 1.0 / max(2.0 * da + feed, 2.0 * db + feed + kill)  # half the scheme's limit
        time = self.speed * ctx.dt
        steps = min(math.ceil(time / longest), MOST)
        a, b = self.a, self.b
        for _ in range(steps):
            a, b = knn.gray_scott_step(a, b, self.nbrs, feed, kill, da, db, min(time / steps, longest))
        self.a[...] = a
        self.b[...] = b

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: np.clip(self.b * self._GAIN, 0.0, 1.0)


class Life(_GraphSim, op="life"):
    """Waves of color that chase round and round across the lights: a cyclic
    cellular automaton, each point counting round its steps and moving on a
    step when a neighbor is one step ahead. `states` sets how many steps. From noise, waves and
    turning spirals form. On a strip or a small map the waves die out and
    the points settle, so `sparks` move points on at random, and each starts
    a new wave. It shows each point's step as a share of the cycle, so give
    it a palette whose ends match."""

    label = "Chase"
    sig = Sig.SOURCE
    out = Ty.SCALAR
    states = Int(6, 3, 12, help="Steps in one cycle: more give wider bands, which settle sooner")
    speed = Float(6.0, 0.5, 20.0, "/s", sweet=(2.0, 10.0), flash_sensitive=True, help="How fast the waves chase")
    sparks = Float(2.0, 0.0, 20.0, "/s", sweet=(0.5, 8.0),
                   help="Points a second that move on by themselves, each starting a wave; at 0 a strip settles")
    examples = ("life(6, 20, 4)", 'life(5, speed=4).palette("synthwave", cycle=0.02)')
    cost = Cost(20.0, 4.5)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.state = ctx.buffer("state", ctx.n)
        self.last = ctx.buffer("last", ctx.n)
        self.progress = ctx.buffer("progress", 1, np.float64)
        self.countdown = ctx.buffer("countdown", 1, np.float64)
        if ctx.n and not self.state.any():  # new, not carried: start from noise
            self.state[...] = ctx.rng().integers(self.states, size=ctx.n)
            self.last[...] = self.state

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        cycle = float(self.states)
        np.remainder(self.state, cycle, out=self.state)
        np.remainder(self.last, cycle, out=self.last)
        self.progress[0] += self.speed * ctx.dt
        steps = min(int(self.progress[0]), MOST)
        self.progress[0] = min(self.progress[0] - steps, 1.0)
        rng = ctx.rng()
        for _ in range(steps):
            ahead = (self.state + 1.0) % cycle
            moves = (self.state[self.nbrs.idx] == ahead[:, None]).any(axis=1)
            moves[_landings(self.countdown, self.sparks, 1.0 / self.speed, rng, self.ctx.n)] = True
            self.last[...] = self.state
            self.state[...] = np.where(moves, ahead, self.state)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def life(c: Coords) -> np.ndarray:
            cycle = float(self.states)
            moved = (self.state != self.last).astype(np.float32)
            return ((self.last + moved * float(self.progress[0])) * (1.0 / cycle)) % 1.0

        return life
