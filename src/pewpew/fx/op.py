"""Ops: what each node of an effect program does (ADR-022).

Each op is a
subclass of `Op` that registers itself by name:

    class Kaleid(Op, op="kaleid"):
        \"\"\"Folds space into mirrored wedges about the map's centre.\"\"\"

        sig = Sig.COORD
        inputs = (Port("in"),)
        out = SAME
        dims = frozenset({2, 3})
        sides = Int(5, 1, 24, help="Wedges in one turn")

        def build(self, inputs):
            inner = inputs[0]
            return lambda c: inner(c.moved(space.kaleid(c.xyz, self.sides, ...)))

Its args are ordinary `pewpew.params` declarations, so `declared_params`
reads them and a node's `ParamSet` (named by the node's address) writes
them onto the op. A closure reads its args when it runs, so a live set
shows on the next frame. An arg may not take the name of a class attribute
the catalog reads (`RESERVED_ARGS`).

A `Rate` arg is a speed whose phase the op keeps (the float rule): each
frame `phase += rate * dt` in a Python float, wrapped into the rate's
period centred on 0. A closure reads
`self.phase(name)`, never `t * rate`.

Hooks: `setup(ctx)` once per bind (`BindCtx`: the points, the map's
extent, the node's seeds, its buffers), which keeps `ctx` as `self.ctx`;
`advance(ctx, inputs)` once per frame before any render, in graph order,
for an op that defines it; and `build(inputs)`, once per bind, which
returns the node's closure.

An op declares the args a map's shape can hide, so liveness does not
probe them there (`Op.shows`): `planar` args act in a plane, so do
nothing on a strip; `along` args act along one axis, fixed or chosen by
an `axis_choice` arg; and an `axis_choice` or `plane_choice` arg acts
along its own value.

A class with the same module and qualified name as a registered one
replaces it, as a reimport of its module gives; a different class under a taken
name is refused.
"""

from __future__ import annotations

import zlib
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar

import numpy as np

from pewpew.features import FeatureFrame
from pewpew.fx.prims.vec import AXES, Center, Plane
from pewpew.fx.types import SAME, Coords, Fn, Port, PortTy, Sig, Ty
from pewpew.mapping import spanned
from pewpew.params import Choice, Float, declared_params

REGISTRY: dict[str, type[Op]] = {}

# The class attributes the catalog, the bound program and `verify looks` read off an
# op; an arg of one of these names would hide it.
CLASS_ATTRS = frozenset({
    "op", "sig", "inputs", "out", "dims", "stateful", "warpable", "planar", "along", "examples", "cost", "label",
    "fix", "range",
})

# The planes an op that works in a plane offers, besides `auto`.
PLANES: tuple[Plane, ...] = ("xy", "xz", "yz")
AUTO = "auto"
U = "u"  # along the strip, in wiring order
ALL = "all"  # every axis, and u


@dataclass(frozen=True, slots=True)
class Cost:
    """What one call of an op costs on this host: `ns_per_point` for each
    point of the map, plus `us_fixed` whatever the map's size."""

    ns_per_point: float
    us_fixed: float

    def to_json(self) -> dict[str, float]:
        return {"ns_per_point": self.ns_per_point, "us_fixed": self.us_fixed}


class Rate(Float):
    """A speed whose phase the op keeps: `Rate(default, lo, hi, unit,
    period=1.0)`. A float param to every surface; the op adds
    `rate * dt` to its phase each frame, wrapped into -period/2 up to
    period/2: a phase that starts at 0 and runs either way wraps only after
    half a period, and stays as small as it can for float32."""

    def __init__(self, default: float, lo: float, hi: float, unit: str = "Hz", *, period: float = 1.0,
                 **meta: Any) -> None:
        if not period > 0.0:
            raise ValueError(f"a Rate's period is above 0, got {period}")
        self.period = float(period)
        super().__init__(default, lo, hi, unit, **meta)


class AxisChoice(Choice):
    """A choice of where on the map an op works: an axis (x, y, z), `u`,
    `all`, or a plane (`auto`, xy, xz, yz). A choice to every surface;
    `Op.shows` reads its options as places (`reach`). Made by
    `axis_choice` and `plane_choice`."""


def plane_choice(**meta: Any) -> AxisChoice:
    """The `plane` arg of an op that works in a plane: `auto` (the two axes
    the map spreads most along) or one of xy, xz, yz."""
    options = {AUTO: "Auto", **{plane: plane for plane in PLANES}}
    return AxisChoice(AUTO, options, help="Which two axes it works across; auto picks the room's", **meta)


def axis_choice(default: str = "x", *, also: Iterable[str] = (), **meta: Any) -> AxisChoice:
    """The `axis` arg of an op along one axis: x, y, z, `u` (along the
    strip, in wiring order) and the `also` choices."""
    keys = (*also, U, *AXES)
    return AxisChoice(default, {key: key for key in keys}, **meta)


def reach(place: str, spans: Sequence[float]) -> frozenset[str]:
    """What an `AxisChoice` option `place` reads on a map of extent
    `spans`: each axis it names that the map spreads along (a plane's two;
    `auto`, those of the plane `auto_plane` takes; `all`, every one), and
    `u` for an option along the strip, which on a strip is the one axis
    the strip spreads along. An option that reaches nothing does nothing
    on that map; two that reach the same read it alike."""
    spread = frozenset(axis for axis, on in zip(AXES, spanned(spans)) if on)
    strip = spread if len(spread) == 1 else frozenset({U})
    if place == U:
        return strip
    if place == ALL:
        return spread | strip
    return spread & set(auto_plane(spans) if place == AUTO else place)


@dataclass(frozen=True, slots=True)
class BindCtx:
    """What a node sees at bind.

    `path` is its address (`layers.<lid>.<nid>`), `values` its knobs'
    values (native, as the op reads them), `coords` the map's points, `lo`
    and `hi` the map's extent per axis, and `dims` how many axes it spans.
    `seed` (32 bits) seeds a hash noise and `key` (64 bits) a node's
    random draws (`rng` at bind, `FrameCtx.rng` each frame).
    `buffer(name, shape, dtype, fill)` declares the node's persistent
    state: at its fill at a bind, read-only while the program renders, so
    write it in place in `advance`. `below()` and `prev()` give the frame
    of the layers below and the layer's own last frame, current when
    called. `gives` is the type the node gives: for a `SAME` output,
    scalar or rgb as it reads (`channels`)."""

    path: str
    values: Mapping[str, Any]
    coords: Coords
    lo: tuple[float, float, float]
    hi: tuple[float, float, float]
    seed: int
    key: int
    buffer: Callable[..., np.ndarray]
    below: Callable[[], np.ndarray]
    prev: Callable[[], np.ndarray]
    gives: Ty = Ty.SCALAR

    @property
    def n(self) -> int:
        return len(self.coords.index)

    @property
    def dims(self) -> int:
        """How many axes the map spreads along: 1 for a strip (or a single
        point), 2 for a panel, 3 for a volume, as `Op.dims` counts them."""
        return max(1, sum(self.spanned))

    @property
    def channels(self) -> tuple[int, ...]:
        """The trailing axis of a field the node gives: (3,) for rgb, ()
        for a scalar. A buffer that holds the node's output takes it."""
        return (3,) if self.gives == Ty.RGB else ()

    def rng(self) -> np.random.Generator:
        """The node's random stream at bind: Philox keyed by the node's
        key, the same at every bind (`FrameCtx.rng` draws each frame's)."""
        return np.random.Generator(np.random.Philox(key=self.key))

    @property
    def centre(self) -> Center:
        """The middle of the map's extent on each axis: where a fold, a
        turn or a shape pivots, on a strip's line or a panel's plane."""
        x, y, z = ((a + b) / 2.0 for a, b in zip(self.lo, self.hi))
        return x, y, z

    @property
    def spans(self) -> tuple[float, float, float]:
        """The map's extent along x, y and z."""
        x, y, z = (b - a for a, b in zip(self.lo, self.hi))
        return x, y, z

    @property
    def spanned(self) -> tuple[bool, bool, bool]:
        """Whether the map spreads along each axis (pewpew.mapping.spanned)."""
        x, y, z = spanned(self.spans)
        return x, y, z

    def plane(self, choice: str) -> Plane:
        """The plane a `plane_choice` names: as chosen, or for `auto` the two
        axes the map spreads most along (xy on a tie)."""
        if choice != AUTO:
            return next(p for p in PLANES if p == choice)
        return auto_plane(self.spans)

    @property
    def time_axis(self) -> int:
        """The axis a field that evolves moves along: the first the map
        does not spread along, else z."""
        return next((a for a, on in enumerate(self.spanned) if not on), 2)


def auto_plane(spans: Sequence[float]) -> Plane:
    """The plane `auto` takes on a map of extent `spans` along x, y and z:
    the two axes it spreads most along, xy on a tie."""
    order = sorted(range(3), key=lambda a: -spans[a])
    i, j = sorted(order[:2])
    return next(p for p in PLANES if p == AXES[i] + AXES[j])


@dataclass(frozen=True, slots=True)
class FrameCtx:
    """What a node sees each frame before render: `dt` in seconds, the
    frame's features, and `tick`, the frames the program has run."""

    dt: float
    features: FeatureFrame
    tick: int
    key: int

    def rng(self) -> np.random.Generator:
        """This node's random stream for this frame (`stream` of the node's
        key and the tick), so each frame draws a stream of its own."""
        return stream(self.key, self.tick)


def stream(key: int, counter: int) -> np.random.Generator:
    """The random stream of `key` at `counter`: Philox keyed by both, so
    each pair draws a stream of its own in every process (ADR-022)."""
    return np.random.Generator(np.random.Philox(key=np.array([key, counter], dtype=np.uint64)))


def node_key(layer_seed: int, lid: str, nid: str) -> int:
    """The 64-bit key of node `nid` of layer `lid`: the layer's seed in
    the high 32 bits and the CRC-32 of `lid/nid` in the low ones, in
    Python ints (ADR-022)."""
    return ((layer_seed & 0xFFFFFFFF) << 32) | zlib.crc32(f"{lid}/{nid}".encode())


def node_seed(key: int) -> int:
    """A 32-bit seed for a hash noise from all 64 bits of `key`."""
    return int(np.random.SeedSequence(key).generate_state(1)[0])


class Op(ABC):
    """The base of every op (module docstring)."""

    op: ClassVar[str]
    sig: ClassVar[Sig]
    inputs: ClassVar[tuple[Port, ...]] = ()
    out: ClassVar[PortTy]
    dims: ClassVar[frozenset[int]] = frozenset({1, 2, 3})
    # Keeps state from frame to frame (a buffer, a feedback field).
    stateful: ClassVar[bool] = False
    # Gives a correct field at points other than the map's own, so a coord
    # op may sit above it. Per-point state (the frame below, the last
    # frame) cannot be read anywhere else.
    warpable: ClassVar[bool] = True
    # Args that act in a plane, so do nothing on a strip.
    planar: ClassVar[frozenset[str]] = frozenset()
    # Args that act along one axis only, so do nothing on a map that does
    # not spread along it: each to its axis (x, y or z), or to the
    # `AxisChoice` arg whose value is its axis. An `AxisChoice` arg acts
    # along its own value.
    along: ClassVar[Mapping[str, str]] = MappingProxyType({})
    examples: ClassVar[tuple[str, ...]] = ()
    cost: ClassVar[Cost] = Cost(0.0, 0.0)
    label: ClassVar[str] = ""
    # What to use instead on a map of a dimension it does not take.
    fix: ClassVar[str] = ""

    _rates: ClassVar[dict[str, Rate]] = {}
    # The bind context `setup` keeps.
    ctx: BindCtx

    def __init_subclass__(cls, *, op: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        params = declared_params(cls)
        for name in sorted(params.keys() & RESERVED_ARGS):  # one message whatever the hash seed
            raise ValueError(
                f"{cls.__name__}.{name}: {name!r} is a class attribute every op has, so it cannot be an arg; "
                "rename the arg"
            )
        cls._rates = {name: p for name, p in params.items() if isinstance(p, Rate)}
        if stray := sorted(cls.planar - params.keys()):
            raise ValueError(f"{cls.__name__}.planar names {stray}, which are not its args")
        for name, axis in sorted(cls.along.items()):
            if name not in params:
                raise ValueError(f"{cls.__name__}.along names {name!r}, which is not one of its args")
            if axis not in AXES and not isinstance(params.get(axis), AxisChoice):
                raise ValueError(
                    f"{cls.__name__}.along[{name!r}] is {axis!r}; give an axis (x, y or z) or an axis_choice arg"
                )
        if op is None:
            return
        prior = REGISTRY.get(op)
        if prior is not None and (prior.__module__, prior.__qualname__) != (cls.__module__, cls.__qualname__):
            raise ValueError(f"op {op!r} is already registered by {prior.__module__}.{prior.__qualname__}")
        cls.op = op
        if not cls.label:
            cls.label = op.capitalize()
        REGISTRY[op] = cls

    def __init__(self) -> None:
        self.phases: dict[str, float] = dict.fromkeys(self._rates, 0.0)

    # ---- the node's knobs ----------------------------------------------------

    @classmethod
    def shows(cls, name: str, a: Any, b: Any, args: Mapping[str, Any], spans: Sequence[float]) -> bool:
        """Whether moving arg `name` of a node of `args` from `a` to `b` can
        change what the node gives on a map of extent `spans`. Not for an
        arg that acts in a plane, on a strip (`planar`), or that acts at
        either end along nothing the map spreads along (`along`, `reach`);
        nor for an `AxisChoice` whose two values read the map alike."""
        if name in cls.planar:
            return sum(spanned(spans)) >= 2
        if isinstance(declared_params(cls).get(name), AxisChoice):
            ends = reach(a, spans), reach(b, spans)
            return all(ends) and ends[0] != ends[1]
        if (axis := cls.along.get(name)) is not None:
            return bool(reach(axis if axis in AXES else args[axis], spans))
        return True

    @classmethod
    def gives(cls, inputs: Sequence[Ty]) -> Ty:
        """The type a node gives from the types it reads: `out`, or for a
        `SAME` output rgb when any input is rgb, else scalar."""
        if cls.out != SAME:
            return Ty(cls.out)
        return Ty.RGB if Ty.RGB in inputs else Ty.SCALAR

    # ---- hooks ----------------------------------------------------------------

    def setup(self, ctx: BindCtx) -> None:
        """Called once per bind, before `build`: keeps `ctx` as `self.ctx`.
        An op that also declares buffers or draws its layout overrides it
        and calls this first."""
        self.ctx = ctx

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        """Called once per frame before any render, in graph order, for an
        op that defines it: the only place state changes or RNG is drawn."""

    @abstractmethod
    def build(self, inputs: Sequence[Fn]) -> Fn:
        """The node's closure over its input closures, built once per bind."""

    # ---- phases ---------------------------------------------------------------

    def step(self, dt: float) -> None:
        """Move each `Rate` arg's phase by `rate * dt` (`Rate`)."""
        for name, rate in self._rates.items():
            half = rate.period / 2.0
            self.phases[name] = (self.phases[name] + getattr(self, name) * dt + half) % rate.period - half

    def phase(self, name: str) -> float:
        """The phase of `Rate` arg `name`, a Python float from -period/2 up
        to period/2."""
        return self.phases[name]


def _public(cls: type) -> set[str]:
    return {name for name in vars(cls) if not name.startswith("_")}


# An arg may not hide a class attribute or a method every op has.
RESERVED_ARGS = CLASS_ATTRS | _public(Op) | {"phases", "ctx"}
