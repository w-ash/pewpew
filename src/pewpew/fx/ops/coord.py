"""Coord ops: each changes the coordinates its input reads, so it wraps
what comes before it (Hydra's rule): `osc(8).rotate(30)` turns the
stripes. The input may be a scalar or rgb, and the op gives the same.

Each pivots on the map's centre (`BindCtx.centre`) in the plane it works
in (`auto`: the two axes the map spreads most along). An op that needs a
plane is refused on a strip, with what to use instead (`fix`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace
from types import MappingProxyType

import numpy as np

from pewpew.fx.op import ALL, BindCtx, Cost, Op, Rate, U, axis_choice, plane_choice
from pewpew.fx.ops.source import DRIFT
from pewpew.fx.prims import space
from pewpew.fx.prims.vec import AXES, Axis, plane_axes
from pewpew.fx.types import SAME, Coords, Fn, Port, Sig
from pewpew.params import Choice, Float, Int

_AXES: dict[str, Axis] = {"x": "x", "y": "y", "z": "z"}


class _Coord(Op):
    """What every coord op shares: one input of either type, the same out,
    and a closure that reads the input at the coordinates `warp` gives."""

    sig = Sig.COORD
    inputs = (Port("in"),)
    out = SAME

    def build(self, inputs: Sequence[Fn]) -> Fn:
        inner = inputs[0]
        return lambda c: inner(self.warp(c))

    def warp(self, c: Coords) -> Coords:
        """The coordinates the input reads at `c`."""
        raise NotImplementedError


class Rotate(_Coord, op="rotate"):
    """Turns a pattern about the center, to an angle and on at a speed. `angle`
    sets how far, `speed` how fast it keeps turning."""

    dims = frozenset({2, 3})
    fix = "a strip has no plane to turn in; use scale or mirror along the strip"
    angle = Float(0.0, 0.0, 360.0, "°", periodic=True, widget="angle", help="Where it starts, before speed turns it on")
    speed = Rate(0.0, -90.0, 90.0, "°/s", period=360.0, flash_sensitive=True,
                 help="Which way and how fast it keeps turning")
    plane = plane_choice()
    examples = ("osc(3).rotate(30)", 'quasicrystal(7).rotate(speed=2).palette("ocean")')
    cost = Cost(1.2, 5.9)

    def warp(self, c: Coords) -> Coords:
        angle = math.radians(self.angle + self.phase("speed"))
        return c.moved(space.rotate(c.xyz, angle, self.ctx.plane(self.plane), self.ctx.centre))


class Scale(_Coord, op="scale"):
    """Zooms a pattern about the center: above 1 enlarges it."""

    amount = Float(1.0, 0.1, 10.0, "×", sweet=(0.5, 4.0), help="Zoom: above 1 enlarges, below 1 shrinks")
    axis = axis_choice(ALL, also=(ALL,), help="The axis it zooms along, or all of them")
    along = MappingProxyType({"amount": "axis"})
    examples = ("noise(3).scale(2)", 'noise(3).scale(0.5, "x").palette("ember")')
    cost = Cost(1.5, 6.9)

    def warp(self, c: Coords) -> Coords:
        factor = 1.0 / self.amount
        if self.axis in (ALL, U):
            c = replace(c, u=(c.u - 0.5) * factor + 0.5)
        if self.axis == U:
            return c
        factors = [factor if self.axis in (ALL, a) else 1.0 for a in AXES]
        return c.moved(space.scale(c.xyz, factors, self.ctx.centre))


class Kaleid(_Coord, op="kaleid"):
    """Folds a pattern into mirrored wedges about the center, as a kaleidoscope
    does. `sides` sets how many."""

    label = "Kaleidoscope"
    dims = frozenset({2, 3})
    fix = "a strip has no plane to fold; use mirror along the strip"
    sides = Int(5, 1, 24, help="More mirror slices")
    plane = plane_choice()
    examples = ("osc(8).kaleid(5)", 'voronoi(4, edge=0.8).kaleid(6).palette("synthwave")')
    cost = Cost(11.0, 10.0)

    def warp(self, c: Coords) -> Coords:
        return c.moved(space.kaleid(c.xyz, self.sides, self.ctx.plane(self.plane), self.ctx.centre))


class Polar(_Coord, op="polar"):
    """Bends a pattern into rings and spokes round the center: stripes along x
    become rings and stripes along y become spokes. In polar coordinates,
    the plane's first axis becomes the radius and its second the turn."""

    dims = frozenset({2, 3})
    fix = "a strip has no plane to wrap round; use mirror along the strip"
    plane = plane_choice()
    examples = ("osc(6).polar()", 'osc(5, axis="y").polar().palette("aurora")')
    cost = Cost(5.1, 6.4)

    def warp(self, c: Coords) -> Coords:
        return c.moved(space.polar(c.xyz, self.ctx.plane(self.plane), self.ctx.centre))


class Mirror(_Coord, op="mirror"):
    """Mirrors one side of a pattern onto the other: folded along one axis, at a
    point you set. `centre` sets where."""

    axis = axis_choice("x", help="The direction it folds across; u folds a strip along its wiring")
    centre = Float(0.5, 0.0, 1.0, label="Center", help="Where the fold sits, from the low end (0) to the high end (1)")
    along = MappingProxyType({"centre": "axis"})
    examples = ('osc(3, 0.15, axis="u").mirror("u")', "noise(4).mirror().palette(\"ocean\")")
    cost = Cost(0.5, 1.7)

    def warp(self, c: Coords) -> Coords:
        if self.axis == U:
            return replace(c, u=np.abs(c.u - self.centre) + self.centre)
        i = AXES.index(self.axis)
        at = self.ctx.lo[i] + self.centre * self.ctx.spans[i]
        x, y, z = (at if a == i else m for a, m in enumerate(self.ctx.centre))
        return c.moved(space.mirror(c.xyz, self.axis, (x, y, z)))


class Twist(_Coord, op="twist"):
    """Twists a volume into a corkscrew: each slice turned a little more than
    the one before it. Each turns about `axis` by `amount` degrees per unit
    along it."""

    dims = frozenset({3})
    fix = "twist turns the slices of a volume; on a panel use rotate, on a strip scale"
    amount = Float(0.0, -360.0, 360.0, "°/unit", sweet=(-180.0, 180.0), help="Degrees of turn per unit along the axis")
    axis = Choice("z", {"x": "x", "y": "y", "z": "z"}, help="The axis the slices turn about")
    examples = ("osc(3).twist(90)", 'metaballs(5).twist(90, "z").palette("ember")')
    cost = Cost(3.2, 5.4)

    def warp(self, c: Coords) -> Coords:
        rate = math.radians(self.amount)
        return c.moved(space.twist(c.xyz, rate, _AXES[self.axis], self.ctx.centre))


class Tunnel(_Coord, op="tunnel"):
    """Rushes a pattern out of the center, as down a tunnel. It reads depth
    (1 / distance from the center) and turn, moving at `speed`."""

    dims = frozenset({2, 3})
    fix = "a strip has no plane to look down; use scale along the strip (u)"
    depth = Float(0.3, 0.05, 2.0, help="How deep the tunnel looks")
    # What the tunnel reads need not repeat along depth, so it jumps once
    # each time the phase wraps: every DRIFT / |speed| s, 34 min at its fastest.
    speed = Rate(0.2, -2.0, 2.0, "/s", period=DRIFT, flash_sensitive=True, help="How fast it flies down the tunnel")
    core = Float(0.08, 0.0, 0.5, help="A still circle at the center, so the middle does not flicker")
    plane = plane_choice()
    examples = ("osc(4).tunnel(0.35, 0.25)", 'voronoi(3, 0.1, edge=0.6).tunnel(0.35, 0.25).palette("aurora")')
    cost = Cost(5.8, 8.3)

    def warp(self, c: Coords) -> Coords:
        plane = self.ctx.plane(self.plane)
        q = list(space.tunnel(c.xyz, plane, self.ctx.centre, radius=max(self.core, 1e-3)))
        i, _ = plane_axes(plane, q)
        q[i] = q[i] * self.depth + self.phase("speed")
        return c.moved(tuple(q))


# The steps of the R4 sequence: 1 / g ** (d + 1) for the root g of
# g ** 5 = g + 1 (Roberts 2018, "The unreasonable effectiveness of
# quasirandom sequences"). Each point steps x, y, z and u by them, so its
# spots spread evenly through its cell.
_G4 = 1.1673039782614187
_R4 = tuple(1.0 / _G4 ** (d + 1) for d in range(4))
# A step along an axis below this share of its span is the same coordinate.
_SAME = 1e-5


def _pitch(values: np.ndarray, span: float, n: int, side: float) -> float:
    """How far apart the points sit along one axis: the median gap of
    their distinct coordinates where points share coordinates (a lattice,
    parallel bars), else `side`, the side of a cell holding one point."""
    distinct = np.unique(np.round(values / max(span * _SAME, 1e-12)))
    if len(distinct) < 2 or len(distinct) > n // 2:
        return side
    return float(np.median(np.diff(distinct))) * span * _SAME


class Dither(_Coord, op="dither"):
    """Breaks hard edges into a sparkle: each light reads the pattern a little
    off its own spot, and jumps to a new spot now and then, on a clock of
    its own. Where the pattern is flat nothing changes; at an edge a light
    twinkles between the colors on each side, as often as the edge covers
    its spot, so a hard edge reads as glitter and an edge that moves
    shimmers across the lights rather than stepping from one to the next.
    `amount` sets how far a light reaches, in the spacing of the lights
    along each axis, and `rate` how often each light jumps."""

    amount = Float(0.5, 0.0, 3.0, "×", sweet=(0.25, 1.5),
                   help="How far each light reaches: 0.5 is halfway to its neighbours; more sparkles wider")
    # A light's spot index is floor(phase + its offset), so it jumps once at
    # each wrap of the phase: every DRIFT / rate s, over 11 min at the fastest.
    rate = Rate(2.0, 0.0, 6.0, "/s", period=DRIFT, flash_sensitive=True,
                help="Jumps a second for each light: more twinkles faster; above about 2 an edge can flash")
    examples = ('osc(5, axis="y").polar().kaleid(5).dither(1).palette("synthwave")',
                'voronoi(4, edge=0.8).dither(1, 1.5).palette("aurora")')
    cost = Cost(2.5, 6.0)

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        n = max(ctx.n, 1)
        spans = [s for s, on in zip(ctx.spans, ctx.spanned, strict=True) if on]
        side = (math.prod(spans) / n) ** (1.0 / len(spans)) if spans else 0.0
        self.pitches = (
            *(_pitch(axis, span, n, side) if on else 0.0
              for axis, span, on in zip(ctx.coords.xyz, ctx.spans, ctx.spanned, strict=True)),
            1.0 / max(n - 1, 1),
        )
        # Each light's start in each axis's sequence (rows 0-3) and its
        # clock's offset (row 4), so neighbours jump at different times.
        self.starts = ctx.rng().random((5, n))

    def warp(self, c: Coords) -> Coords:
        if self.amount == 0.0:
            return c
        starts = self.starts[:, c.index]
        step = np.floor(self.phase("rate") + starts[4])
        moved = []
        for d, (axis, pitch) in enumerate(zip((*c.xyz, c.u), self.pitches, strict=True)):
            if pitch == 0.0:
                moved.append(axis)
                continue
            spot = (starts[d] + step * _R4[d]) % 1.0 - 0.5
            moved.append((axis + (spot * (2.0 * self.amount * pitch)).astype(np.float32)).astype(np.float32))
        x, y, z, u = moved
        return replace(c.moved((x, y, z)), u=u)


class Repeat(_Coord, op="repeat"):
    """Tiles a pattern across the room, each tile showing the whole of it,
    along one axis or all of them. `count` sets how many tiles."""

    count = Int(2, 1, 16, help="Tiles along the axis")
    axis = axis_choice(ALL, also=(ALL,), help="The axis it tiles along, or all of them")
    along = MappingProxyType({"count": "axis"})
    examples = ("noise(2).repeat(3)", "shape(0, 0.3).repeat(3)", 'osc(2, axis="u").repeat(4, "u").palette("candy")')
    cost = Cost(3.7, 15.0)

    def warp(self, c: Coords) -> Coords:
        if self.axis in (ALL, U):
            c = replace(c, u=(c.u * self.count) % 1.0)
        ctx = self.ctx
        tiled = [i for i, a in enumerate(AXES) if self.axis in (ALL, a) and ctx.spanned[i]]
        if not tiled:
            return c
        # Zoom out about the map's low corner, then fold each tile back
        # onto the map: x' = lo + span * frac((x - lo) * count / span).
        q = space.scale(c.xyz, [float(self.count) if i in tiled else 1.0 for i in range(3)], ctx.lo)
        for i in tiled:
            q = space.repeat(q, ctx.spans[i], AXES[i], ctx.centre)
        return c.moved(q)
