"""State ops: each folds what it reads into state it keeps from frame to
frame, before render, and shows that state (ADR-022).

- `feedback`: the MilkDrop loop on a field over the map (pewpew.fx.field):
  each frame the field moves (zoom, spin, swirl, drift, a noise warp),
  fades, and takes the brighter of itself and what the node reads.
- `trails`: per point, the brighter of what it reads and its own fading
  past.

Both composite by the brighter of the two, never by adding, so a static
input holds the field at the input and never ratchets to white
(docs/authoring.md §9.2): the field is at most the brightest the input
has been.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from pewpew.fx.field import Lattice, Splat, Stencil
from pewpew.fx.op import BindCtx, Cost, FrameCtx, Op
from pewpew.fx.ops.source import DRIFT
from pewpew.fx.prims import noise as prim
from pewpew.fx.prims.sample import sample
from pewpew.fx.prims.vec import F32, Vec, fade
from pewpew.fx.types import SAME, Coords, Fn, Port, Sig
from pewpew.params import Float

# Feedback lattice nodes per point spacing, by the lattice's axes: a field
# moved a little each frame and read back by interpolation blurs at the
# scale of its cells, so they are finer than the points (RA-25 notes: 2 to
# 4 times); a volume takes the low end, as its cells cost the cube.
FINE = {1: 3, 2: 3, 3: 2}
# The warp's noise: features per unit, how fast it changes (lattice units
# a second, looped at DRIFT), how far it moves the field at warp 1, the
# spacing of the coarse lattice it is worked out on (it is smooth at that
# scale) before it is read at every node, and how far apart in the noise
# the axes read, so each axis wobbles on its own.
_WARP_FREQ = 3.0
_WARP_CHANGE = 0.3
_WARP_REACH = 0.5
_WARP_CELL = 0.1
_WARP_APART = 1000.0
# A swirl turns the centre at its full rate and falls off past this share
# of the plane's mean extent.
_SWIRL_CORE = 0.3


class Feedback(Op, op="feedback"):
    """Trails that stream and fade: each frame what it showed moves (zooms,
    spins, swirls, drifts up, wobbles) and fades, and keeps the brighter of
    that and what it reads. On a strip it runs along the strip; spin and
    swirl turn a panel's plane, or a volume about its up axis."""

    sig = Sig.STATE
    inputs = (Port("in"),)
    out = SAME
    stateful = True
    planar = frozenset({"spin", "swirl"})
    decay = Float(1.0, 0.05, 10.0, "s", sweet=(0.3, 3.0), help="How long a trail lasts")
    zoom = Float(1.0, 0.25, 4.0, "×/s", sweet=(0.6, 2.5),
                 help="How much it grows a second: above 1 it streams out of the center, below 1 into it")
    spin = Float(0.0, -180.0, 180.0, "°/s", sweet=(-60.0, 60.0), flash_sensitive=True,
                 help="Which way and how fast it turns about the center; nothing on a strip")
    swirl = Float(0.0, -360.0, 360.0, "°/s", sweet=(-120.0, 120.0),
                  help="Degrees a second the middle turns, falling off outward: a whirlpool; nothing on a strip")
    drift = Float(0.0, -1.0, 1.0, "/s", sweet=(-0.3, 0.3), help="How fast it flows upward (below 0, down)")
    warp = Float(0.0, 0.0, 1.0, help="How much a slow noise wobbles the flow")
    examples = (
        "lissajous(heads=2).feedback(1.5, 1.4, 30, 40, 0.1, 0.3)",
        'shape(0, 0.05).feedback(0.7, 2.2).palette("ember")',
        'voronoi(4, 0.15, edge=0.8).kaleid(6).palette("synthwave").feedback(0.9, 0.7, 20, warp=0.15)',
        "below().feedback(0.6, 0.8, -12)",
    )
    cost = Cost(138.0, 447.0)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        per = FINE[ctx.dims]
        self.lattice = Lattice.over(ctx, per)
        self.field = ctx.buffer("field", self.lattice.shape + ctx.channels)
        self.clock = ctx.buffer("clock", 1, np.float64)  # the warp noise's phase
        self.splat = Splat.of(self.lattice, self.lattice.at(ctx.coords), math.ceil(per / 2))
        self.nodes = self.lattice.grid()
        coarse = self.lattice.coarse(_WARP_CELL)
        self.knots = coarse.grid()
        self.between = Stencil.at(coarse.shape, self.lattice.unit(self.nodes))  # each node among the knots

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        self.clock[0] = (self.clock[0] + _WARP_CHANGE * ctx.dt) % DRIFT
        moved = sample(self.field, self.lattice.unit(self.sources(ctx.dt)))
        fresh = self.splat(inputs[0](self.ctx.coords))
        np.maximum(moved * fade(ctx.dt, self.decay), fresh, out=self.field)

    def sources(self, dt: float) -> Vec:
        """Where each node's value comes from, `dt` seconds back, in world
        units from the centre: the motion of one frame undone."""
        m = self.nodes
        if self.drift:
            m = (*m[:-1], m[-1] - self.drift * dt)  # the last axis is up
        if self.warp:
            m = tuple(axis - shift for axis, shift in zip(m, self.wobble(self.warp * _WARP_REACH * dt)))
        if self.zoom != 1.0:
            m = tuple(axis * (1.0 / self.zoom**dt) for axis in m)
        if len(m) >= 2 and (self.spin or self.swirl):
            m = (*self.turned(m[0], m[1], dt), *m[2:])
        return m

    def wobble(self, reach: float) -> list[F32]:
        """The warp's shift of each node, at most about `reach` units per
        axis: a gradient noise per axis that changes slowly, worked out in
        one call on the coarse lattice and read at each node."""
        d = len(self.knots)
        q = [np.concatenate([axis.ravel() * _WARP_FREQ] * d) for axis in self.knots]
        count = self.knots[0].size
        q[0] = q[0] + np.repeat(np.arange(d, dtype=np.float32) * _WARP_APART, count)
        phase = float(self.clock[0])
        if d < 3:
            q.append(np.full_like(q[0], phase))
        else:
            q[-1] = q[-1] + phase
        period = (*(None,) * (len(q) - 1), DRIFT)
        noise = prim.gradient(q, seed=self.ctx.seed, period=period).reshape(d, *self.knots[0].shape)
        at = self.between.read(np.moveaxis(noise, 0, -1)) * reach
        return [at[..., a] for a in range(d)]

    def turned(self, a: F32, b: F32, dt: float) -> tuple[F32, F32]:
        """`a` and `b` turned back by one frame's spin and swirl."""
        spin = math.radians(self.spin) * dt
        if self.swirl:
            core = _SWIRL_CORE * (self.lattice.span[0] + self.lattice.span[1]) / 2.0
            falloff = 1.0 / (1.0 + (a * a + b * b) * (1.0 / (core * core)))
            angle = spin + math.radians(self.swirl) * dt * falloff
            cos, sin = np.cos(angle), np.sin(angle)
        else:
            cos, sin = math.cos(spin), math.sin(spin)  # Python floats keep the field float32
        return a * cos + b * sin, b * cos - a * sin

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def feedback(c: Coords) -> np.ndarray:
            return self.lattice.sample(self.field, c)

        return feedback


class Trails(Op, op="trails"):
    """A trail behind anything that moves: each light keeps the brighter of
    the pattern and its own fading past. Per point, so cheap on any
    map; it has no value between the points, so no coord op may sit above
    it."""

    sig = Sig.STATE
    inputs = (Port("in"),)
    out = SAME
    stateful = True
    warpable = False
    tail = Float(0.5, 0.02, 10.0, "s", sweet=(0.1, 3.0), help="How long a trail lasts")
    examples = (
        "lissajous(heads=1, width=0.15).trails(0.8)",
        'osc(2, 0.4, axis="u").posterize(4).trails(1.2).palette("aurora")',
    )
    cost = Cost(0.9, 0.4)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.last = ctx.buffer("last", (ctx.n, *ctx.channels))

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        np.maximum(self.last * fade(ctx.dt, self.tail), inputs[0](self.ctx.coords), out=self.last)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: self.last
