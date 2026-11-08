"""Signal ops: one number a frame, which a route adds to a knob
(ADR-022, ADR-021's modulation seat).

A look's signals are a graph of these ops, apart from its layers, run
once a frame before any layer (pewpew.compose.modulation). A signal op
gives a Python float in its `range`: -1 to 1 for one that swings both
ways (`lfo`, `walk`), 0 to 1 for a level (`env`, `band`, `beat`, `knob`);
`smooth` gives its input's range. A route moves its knob by `depth` times
the signal, in the knob's own units, so a swing of -1 to 1 moves it
either way and a level only one way. A signal may read other signals
(`smooth`, `env`), and a route may drive another signal's knob.

    look(layer("base", noise(3).palette("ember")),
         routes=[lfo(0.1).to("layers.base.palette.shift", depth=40)])

Each frame the seat calls `step(dt)`, which moves each `Rate` arg's
phase, then `sample(ctx, inputs)` with this frame's values of the signals
it reads. Phases, levels and envelopes are Python floats kept from frame
to frame, so a rate changed by hand or by a route moves the signal on from
where it is and never jumps (the float rule). `walk` draws its levels from
a counter-based stream keyed by the signal's key and the step, so a seed
gives the same wander in every process.
"""

from __future__ import annotations

import math
from abc import abstractmethod
from collections.abc import Callable, Iterable, Sequence
from functools import lru_cache
from typing import ClassVar

from pewpew.fx.graph import Node
from pewpew.fx.op import REGISTRY, Cost, FrameCtx, Op, Rate, stream
from pewpew.fx.prims.vec import TWO_PI
from pewpew.fx.types import Fn, Port, Sig, Ty
from pewpew.params import Choice, Float

Range = tuple[float, float]
LEVEL: Range = (0.0, 1.0)
SWING: Range = (-1.0, 1.0)

# A walk's phase, in steps, wraps at this period, where its levels repeat:
# 49 days at 4 steps a second.
WALK_PERIOD = 2**24


class SignalOp(Op):
    """The base of every signal op (module docstring): `sample` gives the
    frame's value, within `range`. A signal is not a field, so it never
    builds a closure."""

    sig = Sig.SIGNAL
    out = Ty.SIGNAL
    range: ClassVar[Range] = LEVEL

    @classmethod
    def range_of(cls, inputs: Sequence[Range]) -> Range:
        """The values a node of this op gives, from the ranges of the
        signals it reads: `range`, for most ops."""
        return cls.range

    @abstractmethod
    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        """This frame's value, from this frame's values of the signals the
        node reads, after `step(dt)`. Called once a frame, in signal order."""

    def build(self, inputs: Sequence[Fn]) -> Fn:
        raise TypeError(f"{self.op} gives a signal, one number a frame, not a field; route it to a knob")


def ranges(nodes: Iterable[Node]) -> dict[str, Range]:
    """The values each signal of `nodes` gives, by id; `nodes` in graph
    order, each after the signals it reads, all of signal ops."""
    out: dict[str, Range] = {}
    for node in nodes:
        cls = REGISTRY[node.op]
        assert issubclass(cls, SignalOp), node.op  # a look's signals are checked to be
        out[node.id] = cls.range_of([out[source] for source in node.inputs])
    return out


def _toward(level: float, target: float, dt: float, seconds: float) -> float:
    """`level` moved toward `target` by `dt / seconds`, never past it: a
    ramp that crosses one unit in `seconds`, or a jump for 0 seconds."""
    if seconds <= 0.0:
        return target
    step = dt / seconds
    return min(level + step, target) if level < target else max(level - step, target)


def _follow(level: float, target: float, dt: float, tau: float) -> float:
    """`level` moved toward `target` by a one-pole filter of time constant
    `tau` seconds, or onto it for 0 seconds."""
    if tau <= 0.0:
        return target
    return target + (level - target) * math.exp(-dt / tau)


_SHAPES: dict[str, Callable[[float], float]] = {
    "sine": lambda q: math.sin(TWO_PI * q),
    "triangle": lambda q: 1.0 - 4.0 * abs((q + 0.25) % 1.0 - 0.5),
    "square": lambda q: 1.0 if q < 0.5 else -1.0,
    "saw": lambda q: 1.0 - 2.0 * q,
    "ramp": lambda q: 2.0 * q - 1.0,
}


class Lfo(SignalOp, op="lfo"):
    """A wave that swings from -1 to 1 `rate` times a second: a sine, a
    triangle, a square, a saw that falls or a ramp that rises. Each starts
    at 0 rising, but the square and the saw, which start at the top, and
    the ramp, at the bottom."""

    label = "LFO"
    range = SWING
    rate = Rate(0.25, 0.0, 10.0, "Hz", sweet=(0.02, 1.0), flash_sensitive=True,
                help="Higher: what it moves swings faster")
    shape = Choice("sine", {"sine": "Sine", "triangle": "Triangle", "square": "Square", "saw": "Saw down",
                            "ramp": "Ramp up"},
                   help="Sine glides; square jumps; saw and ramp climb or fall, then jump back")
    offset = Float(0.0, 0.0, 1.0, periodic=True, help="Moves the wave along by part of a cycle")
    examples = (
        'look(layer("base", noise(3).palette("ember", shift=lfo(0.05))))',
        ('look(layer("base", osc(8).palette("ocean")), routes=[lfo(0.25, "triangle").to("layers.base.osc.freq", '
        'depth=4)])'),
    )
    cost = Cost(0.0, 1.0)

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        return _SHAPES[self.shape]((self.phase("rate") + self.offset) % 1.0)


class Env(SignalOp, op="env"):
    """An envelope its `gate` signal plays, 0 to 1: when the gate turns on
    (0.5 or more) it rises to 1 over `attack`, falls to `sustain` over
    `decay` and holds there; when the gate turns off it falls to 0 over
    `release`. On the beat: `beat().env(...)`."""

    label = "Envelope"
    inputs = (Port("gate", Ty.SIGNAL),)
    attack = Float(0.01, 0.0, 5.0, "s", sweet=(0.0, 0.5), label="Rise", help="Seconds to rise from 0 to 1")
    decay = Float(0.3, 0.0, 5.0, "s", sweet=(0.05, 1.0), help="Seconds to fall from 1 to the sustain level")
    sustain = Float(0.0, 0.0, 1.0, help="The level it holds while the pulse lasts")
    release = Float(0.3, 0.0, 10.0, "s", sweet=(0.05, 2.0), help="Seconds to fall to nothing after the pulse ends")
    examples = (
        ('look(layer("base", shape(0, 0.3).palette("ember")), routes=[beat().env(0.01, 0.3).to('
        '"layers.base.shape.radius", depth=0.2)])'),
    )
    cost = Cost(0.0, 1.0)

    def __init__(self) -> None:
        super().__init__()
        self.level = 0.0
        self.stage = "release"
        self.gate = False

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        on = inputs[0] >= 0.5
        if on != self.gate:
            self.stage = "attack" if on else "release"
            self.gate = on
        if self.stage == "attack":
            self.level = _toward(self.level, 1.0, ctx.dt, self.attack)
            if self.level >= 1.0:
                self.stage = "decay"
        elif self.stage == "decay":
            fall = 1.0 - self.sustain
            self.level = _toward(self.level, self.sustain, ctx.dt, self.decay / fall if fall else 0.0)
        else:
            self.level = _toward(self.level, 0.0, ctx.dt, self.release)
        return self.level


class Band(SignalOp, op="band"):
    """How loud a part of the sound is, 0 to 1: the volume, or the bass,
    mid or high bands, times `gain`. It rises with time constant `attack`
    and falls with `release`, as an audio-reactive light smooths its
    levels (about 50 ms up and 200 ms down)."""

    label = "Audio follower"
    band = Choice("bass", {"volume": "Volume", "bass": "Bass", "mid": "Mid", "high": "High"},
                  help="The part of the sound it follows")
    gain = Float(1.0, 0.0, 4.0, "×", sweet=(0.5, 2.0), label="Boost",
                 help="Turns the level up; it never goes past full")
    attack = Float(0.05, 0.0, 2.0, "s", sweet=(0.0, 0.2), label="Rise", help="How soon it follows the sound up")
    release = Float(0.2, 0.0, 5.0, "s", sweet=(0.05, 1.0), help="How slowly it lets go as the sound falls")
    examples = (
        ('look(layer("base", shape(0, 0.2).palette("ember")), routes=[band("bass").to("layers.base.shape.radius", '
        'depth=0.3)])'),
    )
    cost = Cost(0.0, 1.0)

    def __init__(self) -> None:
        super().__init__()
        self.level: float | None = None

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        heard = min(float(getattr(ctx.features, self.band)) * self.gain, 1.0)
        level = heard if self.level is None else self.level
        self.level = _follow(level, heard, ctx.dt, self.attack if heard > level else self.release)
        return self.level


class Beat(SignalOp, op="beat"):
    """The beat, 0 to 1: a `pulse` on for the first `width` of each beat,
    the beat's `phase` rising from 0 to 1, or a `fall` from 1 at each beat
    to 0 at the next."""

    shape = Choice("pulse", {"pulse": "Pulse", "phase": "Phase", "fall": "Fall"},
                   help="Pulse flashes on each beat; phase climbs through the beat; fall drops from each beat")
    width = Float(0.25, 0.05, 0.95, help="How much of each beat the pulse is on")
    examples = (
        ('look(layer("base", osc(6).palette("ocean")), routes=[beat("fall").to("layers.base.osc.offset", '
        'depth=0.25)])'),
    )
    cost = Cost(0.0, 1.0)

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        phase = float(ctx.features.beat_phase) % 1.0
        if self.shape == "phase":
            return phase
        if self.shape == "fall":
            return 1.0 - phase
        return 1.0 if phase < self.width else 0.0


@lru_cache(maxsize=256)
def _level(key: int, step: int) -> float:
    """The level, -1 to 1, a walk keyed `key` reaches at `step`: a draw
    from the stream of both (pewpew.fx.op.stream)."""
    return float(stream(key, step).random()) * 2.0 - 1.0


class Walk(SignalOp, op="walk"):
    """A smooth random wander from -1 to 1: it eases to a new random level
    `rate` times a second. The look's seed and the signal's id choose the
    levels, so a look wanders the same way on every run."""

    label = "Random"
    range = SWING
    rate = Rate(0.25, 0.0, 4.0, "Hz", period=WALK_PERIOD, sweet=(0.05, 1.0), flash_sensitive=True,
                help="How often it wanders somewhere new")
    examples = (
        ('look(layer("base", voronoi(5).palette("forest")), routes=[walk(0.3).to("layers.base.palette.shift", '
        'depth=90)])'),
    )
    cost = Cost(0.0, 2.0)

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        at = self.phase("rate")
        step = math.floor(at)
        f = at - step
        a, b = (_level(ctx.key, (step + k) % WALK_PERIOD) for k in (0, 1))
        return a + (b - a) * f * f * (3.0 - 2.0 * f)


class KnobOp(SignalOp, op="knob"):
    """A value a person sets, 0 to 1. With several routes it is a macro:
    at 0 each knob it drives sits at its own value, and at 1 each has moved
    by its route's depth."""

    label = "Macro"
    value = Float(0.0, 0.0, 1.0, help="A knob of the look's own: turn it to move what it drives")
    examples = (
        ('look(layer("base", osc(8).kaleid(5).palette("ember")), routes=[(macro_ := knob(0.5).id("macro")).to('
        '"layers.base.osc.freq", depth=8), macro_.to("layers.base.kaleid.sides", depth=6)])'),
    )
    cost = Cost(0.0, 0.5)

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        return self.value


class Smooth(SignalOp, op="smooth"):
    """Another signal, smoothed: it follows its input with a lag of `time`
    seconds (a one-pole filter), so a jump becomes a glide. Gives what its
    input gives."""

    inputs = (Port("in", Ty.SIGNAL),)
    range = SWING
    time = Float(0.2, 0.0, 10.0, "s", sweet=(0.05, 2.0), help="How long it takes to catch up")
    examples = (
        ('look(layer("base", osc(8).palette("ember")), routes=[band("bass").smooth(0.5).to('
        '"layers.base.palette.shift", depth=90)])'),
    )
    cost = Cost(0.0, 1.0)

    def __init__(self) -> None:
        super().__init__()
        self.level: float | None = None

    @classmethod
    def range_of(cls, inputs: Sequence[Range]) -> Range:
        return inputs[0] if inputs else cls.range

    def sample(self, ctx: FrameCtx, inputs: Sequence[float]) -> float:
        heard = inputs[0]
        self.level = _follow(heard if self.level is None else self.level, heard, ctx.dt, self.time)
        return self.level
