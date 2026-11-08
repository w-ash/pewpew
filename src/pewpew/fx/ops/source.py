"""Source ops: fields made from the coordinates alone, and the two frames
a layer can read (the layers below it, its own last frame).

A scalar source gives values from 0 to 1. Each pivots on the map's centre
(`BindCtx.centre`), and a source that evolves moves along the map's flat
axis, so it changes in place on a strip or a panel.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from types import MappingProxyType

import numpy as np

from pewpew.fx.op import BindCtx, Cost, Op, Rate, plane_choice
from pewpew.fx.op import axis_choice as _axis_choice
from pewpew.fx.prims import noise as prim
from pewpew.fx.prims import sdf
from pewpew.fx.prims.vec import F32, TWO_PI, plane_axes, wave
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.params import Choice, Float, Int

# The period of a drift phase, in lattice units. A noise that drifts loops
# its lattice along the drift axis at this period, so the phase wraps with
# no jump; the field repeats every DRIFT / speed seconds (34 min at speed
# 2). A drift phase stays within +-DRIFT / 2, where a float32 step is at
# most 0.00024 lattice units: under a third of a frame's step at speed 0.05.
DRIFT = 4096
_BELOW_ONE = np.nextafter(np.float32(1.0), np.float32(0.0))
_NOISES = {"gradient": prim.gradient, "value": prim.value}


def _drifting(c: Coords, ctx: BindCtx, scale: float, phase: float) -> list[F32]:
    """The points scaled by `scale`, moved by `phase` along the map's flat
    axis, so a noise sampled there changes in place."""
    p = [axis * scale for axis in c.xyz]
    p[ctx.time_axis] = p[ctx.time_axis] + phase
    return p


def _looped(ctx: BindCtx) -> tuple[int | None, ...]:
    """The lattice period of a drifting noise: DRIFT along the axis it
    drifts on (`_drifting`), none along the others."""
    return tuple(DRIFT if axis == ctx.time_axis else None for axis in range(3))


class Osc(Op, op="osc"):
    """Stripes along one axis that travel across the room."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    label = "Oscillator"
    freq = Float(4.0, 0.5, 32.0, sweet=(1.0, 12.0), label="Stripes", help="More stripes across the room")
    sync = Rate(0.1, -1.0, 1.0, "Hz", flash_sensitive=True, label="Travel",
                help="How fast the stripes travel: crests a second past each point; below 0 they run back")
    offset = Float(0.0, 0.0, 1.0, periodic=True, help="Moves the stripes along by part of a crest")
    axis = _axis_choice("x", help="Which way the stripes run; u runs along a strip from its first light")
    shape = Choice("sine", {"sine": "Sine", "saw": "Saw"},
                   help="Sine rises and falls; saw climbs from 0 to 1, then jumps back to 0, so a palette wraps round")
    along = MappingProxyType({"freq": "axis"})
    examples = ("osc(8, 0.1)", 'osc(3, 0.15, axis="u").palette("ocean")',
                'osc(0.8, 0.1, shape="saw").palette("candy", cycle=0.03)')
    cost = Cost(2.5, 2.4)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def osc(c: Coords) -> np.ndarray:
            turns = c.along(self.axis) * self.freq - (self.phase("sync") - self.offset)
            if self.shape == "saw":
                # x - floor(x) can round up to 1.0 for a tiny negative x in float32.
                return np.minimum(turns - np.floor(turns), _BELOW_ONE)
            return wave(turns)

        return osc


class Noise(Op, op="noise"):
    """Smooth random hills that slowly change, finer ones on top. `octaves`
    sets how many finer layers, and `speed` how fast they change."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    scale = Float(3.0, 0.1, 40.0, sweet=(1.0, 10.0), help="How many hills fit across; more is finer")
    speed = Rate(0.1, 0.0, 2.0, "/s", period=DRIFT, help="How fast the hills change")
    octaves = Int(1, 1, 6, help="Finer detail on top of the hills")
    kind = Choice("gradient", {"gradient": "Gradient", "value": "Value"},
                  help="Gradient noise is smoother; value noise is blockier")
    examples = ("noise(3, 0.1)", 'noise(2, 0.07, octaves=3).palette("aurora")')
    cost = Cost(37.0, 59.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def noise(c: Coords) -> np.ndarray:
            p = _drifting(c, self.ctx, self.scale, self.phase("speed"))
            v = prim.fbm(_NOISES[self.kind], p, octaves=self.octaves, seed=self.ctx.seed, period=_looped(self.ctx))
            return 0.5 + 0.5 * v

        return noise


class Voronoi(Op, op="voronoi"):
    """Cells around scattered points: bright at each point fading to its
    cell's rim, or bright rims between the cells. `edge` draws the rims."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    scale = Float(5.0, 1.0, 32.0, sweet=(2.0, 10.0), help="Cells across the room; more is smaller")
    speed = Rate(0.2, 0.0, 2.0, "/s", period=DRIFT, help="How fast the cells move")
    edge = Float(0.0, 0.0, 1.0, help="0 lights each cell's middle; 1 lights the borders between cells")
    examples = ("voronoi(4, 0.15, edge=0.8)", 'voronoi(6).palette("forest")')
    cost = Cost(220.0, 44.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def voronoi(c: Coords) -> np.ndarray:
            p = _drifting(c, self.ctx, self.scale, self.phase("speed"))
            f1, f2 = prim.cellular(p, seed=self.ctx.seed, period=_looped(self.ctx))
            middle = np.maximum(1.0 - f1, 0.0)
            rim = sdf.coverage(f2 - f1, 0.08) if self.edge else middle
            return middle + (rim - middle) * self.edge

        return voronoi


class Shape(Op, op="shape"):
    """A filled circle or regular polygon at the room's center: a sphere in
    a volume, a segment on a strip."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    sides = Int(0, 0, 12, text={0: "round"}, help="Corners; fewer than 3 draws a circle")
    radius = Float(0.3, 0.0, 1.0, sweet=(0.05, 0.5), help="Size from the center to the rim or a corner")
    smooth = Float(0.05, 0.0, 0.5, help="Softness of the edge")
    plane = plane_choice()
    examples = ("shape(5, 0.3)", 'shape(0, 0.2, 0.1).palette("ember")')
    cost = Cost(9.1, 7.3)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def shape(c: Coords) -> np.ndarray:
            centre = self.ctx.centre
            if self.sides < 3:
                d = sdf.sphere(c.xyz, self.radius, centre)
            else:
                d = sdf.polygon(c.xyz, self.sides, self.radius, self.ctx.plane(self.plane), centre)
            return sdf.coverage(d, self.smooth)

        return shape


class Quasicrystal(Op, op="quasicrystal"):
    """Patterns with many-fold symmetry that never repeat: waves from several
    evenly turned directions, summed. `waves` sets how many directions."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    dims = frozenset({2, 3})
    fix = "a strip shows only swelling stripes; use oscillator"
    waves = Int(7, 3, 12, help="Directions of the waves; 5 and 7 never repeat")
    scale = Float(8.0, 1.0, 40.0, sweet=(3.0, 15.0), help="Higher: more, smaller waves")
    speed = Rate(0.1, -1.0, 1.0, "Hz", flash_sensitive=True, help="How fast the waves move")
    plane = plane_choice()
    examples = ("quasicrystal(7, 7, 0.12)", 'quasicrystal(5, 4.5).palette("synthwave")')
    cost = Cost(10.0, 16.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def quasicrystal(c: Coords) -> np.ndarray:
            i, j = plane_axes(self.ctx.plane(self.plane), c.xyz)
            centre = self.ctx.centre
            a, b = c.xyz[i] - centre[i], c.xyz[j] - centre[j]
            total = np.zeros_like(a)
            for k in range(self.waves):
                turn = math.pi * k / self.waves
                along = a * (self.scale * math.cos(turn)) + b * (self.scale * math.sin(turn))
                total = total + np.cos((along + self.phase("speed")) * TWO_PI)
            return 0.5 + total * (0.5 / self.waves)

        return quasicrystal


def _paths(ctx: BindCtx, count: int) -> np.ndarray:
    """(count, 3, 2) float64: for each moving point, per axis, a whole
    number of turns per cycle (1 to 3) and a start in 0..1, from the
    node's seed."""
    rng = ctx.rng()
    turns = rng.integers(1, 4, size=(count, 3)).astype(np.float64)
    starts = rng.random((count, 3))
    return np.stack([turns, starts], axis=-1)


def _orbit(ctx: BindCtx, paths: np.ndarray, phase: float, reach: float) -> list[tuple[float, float, float]]:
    """Where each moving point is at `phase` (0..1 of a cycle): on each
    axis the map spreads along, a sine about the centre `reach` of the
    half-extent; on a flat axis, the centre."""
    out = []
    for turns, starts in zip(paths[:, :, 0], paths[:, :, 1]):
        x, y, z = (
            m + (0.5 * span * reach * math.sin(TWO_PI * (n * phase + s)) if on else 0.0)
            for m, span, on, n, s in zip(ctx.centre, ctx.spans, ctx.spanned, turns, starts)
        )
        out.append((x, y, z))
    return out


class Metaballs(Op, op="metaballs"):
    """Soft blobs that wander the room and melt together where they meet."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    count = Int(5, 1, 16, help="How many blobs")
    radius = Float(0.15, 0.02, 0.5, help="Size of each blob")
    smooth = Float(0.1, 0.0, 0.5, help="How far apart blobs start to melt together")
    speed = Rate(0.1, 0.0, 1.0, "Hz", help="How fast the blobs wander")
    glow = Float(0.1, 0.01, 0.5, help="Softness of the blobs' edges")
    examples = ("metaballs(5, 0.16, 0.12, 0.08)", 'metaballs(3).palette("candy")')
    cost = Cost(12.0, 38.0)
    _MAX = 16

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        self.paths = _paths(ctx, self._MAX)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def metaballs(c: Coords) -> np.ndarray:
            centres = _orbit(self.ctx, self.paths[: self.count], self.phase("speed"), 0.7)
            d = sdf.sphere(c.xyz, self.radius, centres[0])
            for centre in centres[1:]:
                d = sdf.union(d, sdf.sphere(c.xyz, self.radius, centre), self.smooth)
            return sdf.coverage(d, self.glow)

        return metaballs


class Lissajous(Op, op="lissajous"):
    """Glowing heads that trace a looping knot through the room: a Lissajous
    figure, its own number of loops along each axis. `a`, `b` and `c` are
    the loops a cycle along x, y and z."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    a = Int(3, 1, 9, label="Loops across", help="How many times the knot crosses the room side to side")
    b = Int(4, 1, 9, label="Loops up", help="How many times the knot rises and falls")
    c = Int(5, 1, 9, label="Loops deep", help="How many times the knot comes near and goes far")
    speed = Rate(0.1, 0.0, 1.0, "Hz", help="How fast the heads run round the knot")
    heads = Int(3, 1, 8, help="Heads spaced evenly along the knot")
    width = Float(0.06, 0.01, 0.3, help="Size of each head's glow")
    along = MappingProxyType({"a": "x", "b": "y", "c": "z"})
    examples = ("lissajous(3, 4, 5, 0.1, 3, 0.15)", 'lissajous(heads=5).palette("ice")')
    cost = Cost(9.2, 18.0)

    def head(self, at: float) -> tuple[float, float, float]:
        """Where a head `at` (0..1 of a cycle) is: on each axis the map
        spreads along, a sine about the centre; on a flat axis, the centre."""
        ctx, loops = self.ctx, (self.a, self.b, self.c)
        x, y, z = (
            m + (0.45 * span * math.sin(TWO_PI * (n * at + 0.25 * i)) if on else 0.0)
            for i, (m, span, on, n) in enumerate(zip(ctx.centre, ctx.spans, ctx.spanned, loops))
        )
        return x, y, z

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def lissajous(p: Coords) -> np.ndarray:
            out = np.zeros_like(p.x)
            for k in range(self.heads):
                d = sdf.sphere(p.xyz, 0.0, self.head(self.phase("speed") + k / self.heads))
                out = np.maximum(out, np.exp(-((d * (1.0 / self.width)) ** 2)))
            return out

        return lissajous


class Below(Op, op="below"):
    """The frame of the layers below this one, as blended so far: a layer
    whose program starts here is an effect on the stack below it."""

    sig = Sig.SOURCE
    out = Ty.RGB
    warpable = False
    examples = ("below().hue(90)",)
    cost = Cost(1.0, 1.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: self.ctx.below()


class Prev(Op, op="prev"):
    """The layer's own last frame: with a fade or a color op after it, a
    trail (feedback with no warp)."""

    sig = Sig.SOURCE
    out = Ty.RGB
    warpable = False
    examples = ('lissajous(heads=1).blend(prev(), "max", 0.9)',)
    cost = Cost(1.0, 1.0)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        return lambda c: self.ctx.prev()
