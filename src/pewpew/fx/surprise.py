"""Surprise: endless looks from a seed, and looks like a given one
(ADR-022 "Generation is a grammar over the catalog").

`generate(seed, mapping)` makes a look from nothing; `mutate(look, seed,
mapping, strength=...)` makes one like `look`. Each takes the mapping it
is for, because the ops a look may use depend on the mapping's dimensions
and each candidate is rendered on it and judged. Each is byte-deterministic
for its arguments: the same seed and mapping give the same look.

The grammar. A look has one to three layers (`LAYERS`). Each layer is one
of four kinds of program, built from the built-in ops by role (`role`), so
a new built-in op joins the grammar when its module is added to
pewpew.fx.ops. An op a pattern file defines never does: the same seed
would make another look in a process that ran the file.

    field   a source, then 1 to 3 warps (coord or modulate ops), maybe a tone op, then a palette
    trail   a source and maybe one warp, then a state op before or after the palette
    sim     a stateful source, maybe a state op and a tone op, then a palette
    echo    below() and a state op (an upper layer only), with no palette

An upper layer mixes onto the layers below with screen, add or max
(`BLENDS`) at part opacity. Each layer's palette starts dark, as LEDs
show black for free: a preset in colour that does (`GROUNDED`) turned to
the layer's hue, or a harmony of up to three hues about it (`RAMP`); the
layers' hues step by the golden angle. A modulate warps by a smooth field
(`MODULATORS`). Half the palettes cycle: each is then looped, so its
ends meet, and the layers' cycle rates step by the golden ratio, so they
never line up. Up to two routes (`ROUTES`) move float knobs, each with
its own slow signal: a `walk`, or an `lfo`
that starts near its crest (a saw on a periodic knob turns it round
seamlessly); with `audio`, also a `band`. Their rates step down by the
golden ratio. A look stays within `budget` microseconds a frame, summed
from the catalog's `cost` at the mapping's size (`look_cost`).

A knob is drawn from its describe record alone (pewpew.params `spec()`):
inside its `sweet` range, eased toward its default (log-spaced across a
wide positive range, uniform round a periodic one). Slow beats fast: a
speed (a knob in a unit per second) or a `flash_sensitive` knob stays
within a factor of `STEADY` of its default (`steady`), and a route never
moves either but a layer's opacity, and that one shallowly. A signal's
rate is from the slow end of its rate's sweet range. A choice never names
an axis the mapping does not span.

`mutate` nudges each knob it does not hold with a chance that grows with
`strength` (above 0, at most 1), within its sweet range (widened to take
a value set outside it), and more rarely draws a choice again, repaints
a palette, changes a blend, swaps an op for another of its role, adds or
drops a route, or reseeds the look; a swap or a new route stays within
`budget`. `keep` holds addresses (`Held`): a knob, a node, a layer or a
signal, and all under it, never change, and no route is added into them
or dropped from them, nor a node swapped that a held route moves. A held
layer, node or signal holds the look's seed too, as its random stream
comes from it.

The judge (`judge`). Each candidate is checked and rendered through
pewpew.lab on the mapping, thinned to `PREVIEW_POINTS`, for `PREVIEW_S`
at `PREVIEW_FPS` with the stand-in features seeded 0, and measured
(pewpew.metrics). It must pass the content gate of `verify looks`: it
checks, no layer raises, it flashes at most 3 times a second, it is not
black, and every knob changes the picture (pewpew.lab.liveness), here by
`LIVE_MARGIN` times the threshold, so it passes with room. It should pass
the taste gates (`taste`): not too dark, not washed out, not dying out,
not frozen, not noise, and in colour when its palettes are. It must also
keep its flashes to `SAFE_FLASH` a second, so a longer run stays under
WCAG's 3. Of at most `TRIES` candidates the first that passes both is the
result; else the one that passes the content gate and fails fewest taste
gates; else each raises `NoLook`. Each takes about a second: the
liveness probe renders the look twice for each knob.

Determinism: each candidate draws from a counter-based stream
(pewpew.fx.op.stream) keyed by what is made, the seed and the attempt;
ops and records are read in a fixed order; numbers are rounded to three
significant figures, so the JSON reads well and stays stable. No wall
clock, no `hash()`.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import Any, TypeVar

import numpy as np

from pewpew.color import PRESETS
from pewpew.compose.controls import Controls, LayerControls, layer_address, look_controls, signal_address, signal_of
from pewpew.compose.modulation import route_problems
from pewpew.compose.stack import Look, Route, is_seed
from pewpew.errors import did_you_mean, typo_hint
from pewpew.fx.compile import check, knob_class
from pewpew.fx.expr import Expr, Routed, layer, look, namespace
from pewpew.fx.graph import PATTERN, Graph, Node, Program, as_id, free_id
from pewpew.fx.op import Op, stream
from pewpew.fx.ops import OPS
from pewpew.fx.ops.color import PaletteOp
from pewpew.fx.prims.vec import AXES
from pewpew.fx.types import SAME, Sig, Ty
from pewpew.jsonfile import is_number
from pewpew.lab.check import Ready, ready
from pewpew.lab.geometry import Geometry
from pewpew.lab.liveness import each_probe
from pewpew.lab.rendering import limits, play
from pewpew.load import Catalog
from pewpew.mapping import Grouping, extents, spanned
from pewpew.metrics import FLASH_LIMIT, LIVENESS_RMS, Metrics, measure
from pewpew.params import HSV, Gradient, Palette, ParamSet, Stop
from pewpew.problems import Code, Problem, Refused

T = TypeVar("T")
Record = Mapping[str, Any]
# The class of a node's knobs, by its layer's id and the node.
KnobClass = Callable[[str, Node], type]

PHI = (1.0 + 5.0**0.5) / 2.0
GOLDEN_ANGLE = 360.0 * (2.0 - PHI)  # degrees: the hue step between layers

BUDGET_US = 4000.0  # a quarter of a 60 fps frame
STRENGTH = 0.3  # how far mutate moves a look by default: above 0, at most 1
TRIES = 16
PREVIEW_S = 4.0  # as long as `verify looks` renders by default
PREVIEW_FPS = 30.0
PREVIEW_POINTS = 256
LIVE_MARGIN = 2.0
SAFE_FLASH = 2.5  # flashes a second a made look keeps to: WCAG's 3, with room

# The grammar's weights: each choice and how often it is drawn.
LAYERS = {1: 0.5, 2: 0.38, 3: 0.12}
BOTTOM = {"field": 0.55, "trail": 0.25, "sim": 0.2}
UPPER = {"field": 0.45, "trail": 0.15, "sim": 0.15, "echo": 0.25}
WARPS = {1: 0.6, 2: 0.3, 3: 0.1}
MODULATE = 0.3  # a warp that is a modulate rather than a coord op
# What a modulate warps by: a smooth field, as the examples' noise; a
# sharp-edged one (voronoi, metaballs) makes the warp jump.
MODULATORS = {"noise": 0.75, "osc": 0.25}
TONE = 0.25  # a field or sim that a tone op shapes before its palette
SIM_STATE = 0.25  # a sim whose source a state op smooths
STATE_FIRST = 0.8  # a trail that keeps its state before the palette: a blur after it greys the colors
BLENDS = {"screen": 0.5, "add": 0.25, "max": 0.25}
OPACITY = {"field": (0.3, 0.6), "trail": (0.3, 0.6), "sim": (0.3, 0.6), "echo": (0.2, 0.45)}
CYCLES = 0.5  # a palette that cycles
HARMONY = 0.35  # a palette made about a hue, rather than a preset turned to it
SCHEMES = {(0.0, 25.0, 50.0): 0.6, (0.0, 150.0, 210.0): 0.4}  # analogous, split complementary
# A harmony's stops: where, which of its scheme's hues, saturation and
# value; dark for its first third, and pale only at its top.
RAMP = ((0.0, 0, 0.9, 0.0), (0.35, 0, 0.9, 0.12), (0.65, 1, 0.85, 0.5), (0.88, 2, 0.6, 0.85), (1.0, 2, 0.4, 1.0))
DARK_START = 0.1  # a palette starts dark: its first stop's value at most this
ROUTES = {0: 0.2, 1: 0.5, 2: 0.3}
SIGNALS = {"walk": 0.45, "lfo": 0.55}
# What a made look calls each signal it adds, in the page's plain words
# rather than the op's synth name.
SIGNAL_NAMES = {"lfo": "sway", "walk": "drift", "band": "music"}
BAND = 0.3  # with audio: a route's signal that is a band
WAVES = {"sine": 0.7, "triangle": 0.3}
LFO_START = 0.375  # the part of its cycle an lfo starts at: near its crest, where its shapes differ most
DEPTH = (0.15, 0.5)  # a route's depth, as a share of its knob's sweet range
FLASH_DEPTH = 0.3  # the deepest route into a flash-sensitive knob, as a share of its range
SLOW = 0.125  # a rate is from this slowest share of its sweet range...
PACE = (0.2, 1.0)  # ...this far across it
FADE = (2.0, 6.0)  # seconds a made look fades in over
FRONT = 3  # knobs a made look shows first

# How a knob is drawn: eased toward its default by this power of a uniform
# draw, log-spaced across a sweet range that spans this ratio.
EASE = 2.0
WIDE = 10.0
STEADY = PHI**2  # how far a speed strays from its default, as a factor either way
KEEP_CHOICE = 0.6  # a choice that keeps its default
KEEP_BOOL = 0.8

# How mutate changes a look at strength s: each knob is nudged with chance
# NUDGE[0] + NUDGE[1] s, by a normal step of NUDGE_STEP s of its range.
NUDGE = (0.35, 0.5)
NUDGE_STEP = 0.15
RECHOOSE = 0.25  # a choice or switch drawn again, times s
REPAINT = 0.3  # a palette made again, times s
REBLEND = 0.3  # an upper layer's blend drawn again, times s
SWAP = 0.5  # an op swapped for another of its role, times s squared
REROUTE = 0.3  # a route added or dropped, times s
RESEED = 0.5  # the look's seed drawn again, times s

# The taste gates' thresholds (calibrated on examples/: each passes there).
DARK_BLACK = 0.8  # most samples black...
DARK_P95 = 0.05  # ...or even the brightest few dim
WASHED = 0.4  # mean luma above this: no dark ground, which LEDs give for free
DEAD_TAIL = 0.95  # black in the last second: a sim that died out
STILL_MOTION = 0.01  # mean |ΔY| a second below this, or...
STILL_FROZEN = 0.5  # ...frozen this share of the frame steps
NOISE_MOTION = 0.25  # fast and...
NOISE_DETAIL = 0.5  # ...fine at once reads as static
COLOURFUL_S = 0.2  # a palette with a stop at least this saturated means colour


class NoLook(ValueError):
    """No candidate passed the content gate in `TRIES` attempts."""


def generate(
    seed: int,
    mapping: np.ndarray,
    *,
    grouping: Grouping | None = None,
    audio: bool = False,
    budget: float = BUDGET_US,
) -> Look:
    """A look made from `seed` for `mapping` (module docstring): within
    `budget` microseconds a frame, with an audio-driven route only when
    `audio`. Raises NoLook when no candidate passes the content gate, and
    ValueError for a negative seed, a map no look runs on (`Space.of`) or
    a budget no look fits."""
    space = Space.of(mapping, grouping, budget)
    return best(space, (_drawn(Draw("surprise", seed, k), space, audio) for k in range(TRIES)), seed)


def mutate(
    look: Look,
    seed: int,
    mapping: np.ndarray,
    *,
    strength: float = STRENGTH,
    keep: Iterable[str] = (),
    grouping: Grouping | None = None,
    audio: bool = False,
    budget: float = BUDGET_US,
    pattern_dir: Path | None = None,
    catalog: Catalog | None = None,
) -> Look:
    """A look like `look`, changed by `strength` (above 0, at most 1) from
    `seed`, for `mapping` (module docstring), holding each address of
    `keep` and all under it; never `look` itself. Its patterns resolve as
    pewpew.lab.check `ready` resolves them, from `pattern_dir` or through
    `catalog`. Raises NoLook when no change passes the content gate,
    Refused for a look that does not check or a `keep` address that names
    nothing in it, and ValueError for a bad strength (`check_strength`), a
    negative seed or a map no look runs on (`Space.of`)."""
    s = require_strength(strength)
    require_seed(seed)
    space = Space.of(mapping, grouping, budget, pattern_dir=pattern_dir, catalog=catalog)
    staged = ready(look, pattern_dir=pattern_dir, catalog=catalog)
    held = Held.of(keep, staged)
    drawn = (_mutated(Draw("mutate", seed, k), staged, space, s, held, audio) for k in range(TRIES))
    try:
        return best(space, (made for made in drawn if made != staged.look), seed)
    except NoLook:
        raise NoLook(f"no change of the look made from seed {seed} passed the content gate in {TRIES} tries; "
                     "try another seed, or keep less") from None


# ---- where a look is made for ---------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class Space:
    """Where a made look runs: how many points, how many axes they span and
    which, the cost budget in microseconds a frame, the geometry the judge
    renders on, and where a look's patterns resolve (pewpew.lab.check
    `ready`): from `pattern_dir`, or through `catalog`."""

    points: int
    dims: int
    axes: frozenset[str]
    budget: float
    preview: Geometry
    pattern_dir: Path | None = None
    catalog: Catalog | None = None

    @classmethod
    def of(cls, mapping: np.ndarray, grouping: Grouping | None, budget: float, *,
           pattern_dir: Path | None = None, catalog: Catalog | None = None) -> Space:
        """The space of `mapping`. Raises ValueError for a mapping that is
        not (N, 3) points, one whose points all sit at one place (every op
        needs an axis to run along), or a budget that is not above 0."""
        mapping = np.asarray(mapping, dtype=np.float32)
        if mapping.ndim != 2 or mapping.shape[1] != 3 or not len(mapping):
            raise ValueError(f"a mapping is (N, 3) points, N at least 1; got shape {mapping.shape}")
        if not budget > 0:
            raise ValueError(f"a budget is a number of microseconds above 0, got {budget!r}")
        axes = frozenset(axis for axis, on in zip(AXES, spanned(extents(mapping))) if on)
        if not axes:
            raise ValueError(f"no look is made for a map whose {len(mapping)} point(s) sit at one place: "
                             "every op runs along an axis, so give a map that spans one")
        return cls(len(mapping), len(axes), axes, float(budget), _preview(mapping, grouping), pattern_dir, catalog)

    def takes(self, cls: type[Op]) -> bool:
        """Whether op `cls` runs on this mapping."""
        return self.dims in cls.dims

    def cost(self, op: str) -> float:
        """Microseconds a frame one node of `op` costs at this mapping's size."""
        return node_cost(op, self.points)


def _preview(mapping: np.ndarray, grouping: Grouping | None) -> Geometry:
    """The geometry the judge renders on: the mapping, or past
    PREVIEW_POINTS points, that many spread evenly along it, each in the
    fixture it was in."""
    if len(mapping) <= PREVIEW_POINTS:
        return Geometry("surprise", mapping, grouping)
    keep = np.linspace(0, len(mapping) - 1, PREVIEW_POINTS).round().astype(np.intp)
    thinned = None if grouping is None else Grouping(grouping.centres, grouping.of[keep])
    return Geometry("surprise", mapping[keep], thinned)


def node_cost(op: str, points: int) -> float:
    """Microseconds a frame one node of `op` costs at `points` points, from
    the catalog's `cost`."""
    price = OPS[op].cost
    return price.ns_per_point * points / 1000.0 + price.us_fixed


def look_cost(look: Look, points: int) -> float:
    """Microseconds a frame `look` costs at `points` points: the cost of
    each node of each layer and of each signal."""
    return _cost((item.program for item in look.layers), look.signals or (), points)


def _cost(programs: Iterable[Program], signals: Iterable[Node], points: int) -> float:
    """Microseconds a frame the nodes of `programs` and `signals` cost at
    `points` points."""
    nodes = [*(node for program in programs for node in program.graph), *signals]
    return sum(node_cost(node.op, points) for node in nodes)


# ---- draws -----------------------------------------------------------------------------


def check_seed(seed: object) -> str | None:
    """Why `seed` cannot seed a made look, or None. Never raises."""
    return None if is_seed(seed) else f"a seed is a whole number of at least 0, got {seed!r}"


def require_seed(seed: object) -> int:
    """`seed` as a seed. Raises ValueError, in `check_seed`'s words, for
    anything but a whole number of at least 0."""
    if (reason := check_seed(seed)) is not None:
        raise ValueError(reason)
    assert isinstance(seed, int)
    return seed


def sub_seed(seed: int, i: int) -> int:
    """The seed of look `i` of a series made from `seed`."""
    return zlib.crc32(f"{seed}/{i}".encode())


def check_strength(strength: object) -> str | None:
    """Why `strength` cannot move a look (`mutate`): it is a number above 0
    and at most 1. Returns the reason, or None. Never raises."""
    if is_number(strength) and 0.0 < strength <= 1.0:
        return None
    return f"a strength is a number above 0 and at most 1 (at 0 a look does not change), got {strength!r}"


def require_strength(strength: object) -> float:
    """`strength` as a strength. Raises ValueError, in `check_strength`'s
    words, for anything else."""
    if (reason := check_strength(strength)) is not None:
        raise ValueError(reason)
    assert isinstance(strength, (int, float))
    return float(strength)


class Draw:
    """The random draws of one candidate: a counter-based stream keyed by
    what is made (`kind`), the seed and the attempt. Raises ValueError for
    a bad seed (`require_seed`)."""

    def __init__(self, kind: str, seed: int, attempt: int) -> None:
        key = np.random.SeedSequence([zlib.crc32(kind.encode()), require_seed(seed)]).generate_state(1, np.uint64)[0]
        self._rng = stream(int(key), attempt)

    def random(self) -> float:
        return float(self._rng.random())

    def normal(self) -> float:
        return float(self._rng.normal())

    def chance(self, p: float) -> bool:
        return self.random() < p

    def uniform(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.random()

    def sign(self) -> int:
        return 1 if self.chance(0.5) else -1

    def pick(self, weights: Mapping[T, float]) -> T:
        """One key of `weights`, each as likely as its weight, read in the
        mapping's order."""
        keys = [key for key, w in weights.items() if w > 0]
        if not keys:
            raise ValueError("nothing to pick from")
        at = self.random() * sum(weights[key] for key in keys)
        for key in keys:
            at -= weights[key]
            if at < 0:
                return key
        return keys[-1]

    def choice(self, items: Sequence[T]) -> T:
        if not items:
            raise ValueError("nothing to choose from")
        return items[min(int(self.random() * len(items)), len(items) - 1)]

    def seed(self) -> int:
        return int(self._rng.integers(2**31))


# ---- knobs -----------------------------------------------------------------------------


@cache
def records(cls: type) -> tuple[Record, ...]:
    """The describe records of the knobs of op or pattern class `cls`."""
    return tuple(ParamSet(cls).describe())


def record_of(cls: type, name: str) -> Record:
    """The describe record of knob `name` of class `cls`."""
    return next(record for record in records(cls) if record["name"] == name)


def value(draw: Draw, record: Record, axes: frozenset[str] = frozenset(AXES)) -> Any:
    """A value of the knob `record` describes (module docstring); a
    palette's or a color's is its default, which the grammar paints over."""
    kind = record["kind"]
    if kind in ("float", "int"):
        return number(draw, record)
    if kind == "choice":
        options = choices(record, axes)
        if record["default"] in options and draw.chance(KEEP_CHOICE):
            return record["default"]
        return draw.choice(options)
    if kind == "bool":
        return record["default"] if draw.chance(KEEP_BOOL) else not record["default"]
    return record["default"]


def drawn_args(draw: Draw, cls: type, axes: frozenset[str] = frozenset(AXES)) -> dict[str, Any]:
    """A value (`value`) of each knob of op `cls`, by name, in declared order."""
    return {record["name"]: value(draw, record, axes) for record in records(cls)}


def choices(record: Record, axes: frozenset[str]) -> list[str]:
    """The options of a choice that make sense on a mapping spanning
    `axes`: none that names an axis it does not span, or a plane through
    one."""
    options = [o["value"] for o in record["options"]]
    fit = [o for o in options if not set(o) <= set(AXES) or set(o) <= axes]
    return fit or [record["default"]]


def number(draw: Draw, record: Record) -> float | int:
    """A number inside the record's sweet range: uniform round a periodic
    knob; near its default for a speed or a flash-sensitive knob
    (`steady`); else eased toward its default, to one end or the other as
    far as each lies from it, in log space across a wide positive range."""
    lo, hi = record["sweet"]
    if record["periodic"]:
        return tidy(draw.uniform(lo, hi), record)
    if record["flash_sensitive"] or is_speed(record):
        return tidy(steady(draw, record), record)
    log = _log_spaced(lo, hi)
    a, b, mid = (_to(x, log) for x in (lo, hi, min(max(record["default"], lo), hi)))
    end = b if draw.uniform(a, b) >= mid else a
    return tidy(_from(mid + (end - mid) * draw.random() ** EASE, log), record)


def is_speed(record: Record) -> bool:
    """Whether a knob is a speed: its unit is per second ("Hz", "/s", "°/s")."""
    unit = record.get("unit", "")
    return unit == "Hz" or unit.endswith("/s")


def steady(draw: Draw, record: Record) -> float:
    """A speed slow beats fast: within a factor of STEADY either way of its
    default, log-spaced; for a default of 0, across the slow share of its
    range (`slow`). Its sign flips half the time when its range runs both
    ways."""
    sign = draw.sign() if record["sweet"][0] < 0 else 1
    default = abs(record["default"])
    if not default:
        return sign * slow(record, draw.uniform(*PACE))
    return sign * default * STEADY ** draw.uniform(-1.0, 1.0)


def slow(record: Record, pace: float) -> float:
    """A rate `pace` (0 to 1) across the slowest `SLOW` share of the
    record's sweet range, from its low end, or from 0 for a range round 0."""
    lo, hi = record["sweet"]
    start = max(lo, 0.0)
    return float(tidy(start + (hi - start) * SLOW * pace, record))


def nudge(draw: Draw, record: Record, now: Any, s: float, axes: frozenset[str] = frozenset(AXES)) -> Any:
    """`now`, the value of the knob `record` describes, moved at strength
    `s`: a number by a normal step within its sweet range widened to take
    `now` (reflected at the ends; wrapped round when periodic); a choice
    drawn again now and then, as `value` draws one for a mapping spanning
    `axes` (`choices`), or a switch flipped; a color by each part. Any
    other kind keeps its value."""
    kind = record["kind"]
    if kind in ("float", "int"):
        if record["periodic"]:
            lo, hi = record["lo"], record["hi"]
            moved = now + draw.normal() * NUDGE_STEP * s * (hi - lo)
            return tidy(lo + (moved - lo) % (hi - lo), {**record, "sweet": (lo, hi)})
        lo, hi = min(record["sweet"][0], now), max(record["sweet"][1], now)
        log = _log_spaced(lo, hi)
        a, b = _to(lo, log), _to(hi, log)
        moved = _reflect(_to(now, log) + draw.normal() * NUDGE_STEP * s * (b - a), a, b)
        return tidy(_from(moved, log), {**record, "sweet": (lo, hi)})
    if kind in ("choice", "bool"):
        if not draw.chance(RECHOOSE * s):
            return now
        return draw.choice(choices(record, axes)) if kind == "choice" else not now
    if kind == "color":
        return {name: nudge(draw, {**part, "kind": "float", "sweet": (part["lo"], part["hi"])}, now[name], s)
                for name, part in record["parts"].items()}
    return now


def tidy(x: float, record: Record) -> float | int:
    """`x` as the knob `record` describes takes it, within its sweet range
    (wrapped back to its low end at a periodic top): an int rounded half
    up, a float to three significant figures."""
    lo, hi = record["sweet"]
    if record["kind"] == "int":
        return int(min(max(math.floor(x + 0.5), lo), hi))
    rounded = min(max(float(f"{x:.3g}"), lo), hi)
    return float(lo) if record["periodic"] and rounded >= record["hi"] else rounded


def _log_spaced(lo: float, hi: float) -> bool:
    return lo > 0 and hi / lo >= WIDE


def _to(x: float, log: bool) -> float:
    return math.log(x) if log else float(x)


def _from(x: float, log: bool) -> float:
    return math.exp(x) if log else x


def _reflect(x: float, a: float, b: float) -> float:
    """`x` folded back into `a`..`b` at each end."""
    if b <= a:
        return a
    period = 2.0 * (b - a)
    x = (x - a) % period
    return a + (period - x if x > b - a else x)


# ---- palettes ----------------------------------------------------------------------------


def colourful(gradient: Gradient) -> bool:
    """Whether `gradient` has colour: a stop of saturation COLOURFUL_S or more."""
    return max(stop.color.s for stop in gradient.stops) >= COLOURFUL_S


# The presets a made look paints with: in colour, and starting dark.
GROUNDED = tuple(preset for preset in PRESETS if colourful(preset) and preset.stops[0].color.v <= DARK_START)


def palette(draw: Draw, hue: float) -> tuple[Gradient, float]:
    """A gradient about `hue` (degrees) and the shift that turns it there:
    a preset in colour that starts dark (`GROUNDED`), turned so its last
    stop takes the hue, or a harmony of hues about it (`RAMP`), which needs
    no shift."""
    if draw.chance(HARMONY):
        turns = draw.pick(SCHEMES)
        stops = tuple(Stop(at, HSV(round((hue + turns[k]) % 360.0, 1), s, v)) for at, k, s, v in RAMP)
        return Gradient(stops, "harmony"), 0.0
    preset = draw.choice(GROUNDED)
    return preset, round((hue - preset.stops[-1].color.h) % 360.0, 1) % 360.0


def looped(gradient: Gradient) -> Gradient:
    """`gradient` there and back: its stops at half their places, then the
    same in reverse up to 1, so its two ends meet and it can cycle."""
    there = [Stop(stop.at / 2.0, stop.color) for stop in gradient.stops]
    back = [Stop(1.0 - stop.at / 2.0, stop.color) for stop in reversed(gradient.stops[:-1])]
    return Gradient((*there, *back), f"{gradient.label} loop".strip()[: Palette.max_label])


# ---- the grammar -------------------------------------------------------------------------


def role(cls: type[Op]) -> str | None:
    """What the grammar uses op `cls` for, from its catalog record: a
    `field` or `sim` source (a scalar one, stateless or not), a `warp`
    (coord or modulate), a `tone` (a color op that keeps its type) or a
    `state` op; None for what the grammar places itself (the palette,
    below) or never makes (patterns, combines, signals)."""
    if cls.op == PATTERN:
        return None
    if cls.sig == Sig.SOURCE:
        return None if cls.out != Ty.SCALAR else "sim" if cls.stateful else "field"
    if cls.sig in (Sig.COORD, Sig.MODULATE):
        return "warp"
    if cls.sig == Sig.COLOR and cls.out == SAME:
        return "tone"
    return "state" if cls.sig == Sig.STATE else None


BUILT_IN = "pewpew.fx.ops."  # the package of the built-in ops, which pewpew.fx.ops imports whole


@cache
def _roles() -> dict[str, tuple[type[Op], ...]]:
    """The built-in ops by role, by name (module docstring): read once,
    since importing pewpew.fx.ops registered every one."""
    found: dict[str, list[type[Op]]] = {}
    for name in sorted(OPS):
        cls = OPS[name]
        if cls.__module__.startswith(BUILT_IN) and (kind := role(cls)) is not None:
            found.setdefault(kind, []).append(cls)
    return {kind: tuple(classes) for kind, classes in found.items()}


def ops(space: Space, kind: str) -> tuple[type[Op], ...]:
    """The ops of role `kind` that run on `space`, by name."""
    return tuple(cls for cls in _roles().get(kind, ()) if space.takes(cls))


class _Purse:
    """What a look being made may still spend, in microseconds a frame.
    A node is spent for before it joins the look, and only when the purse
    affords it, so the look never costs more than the budget."""

    def __init__(self, space: Space, spent: float = 0.0) -> None:
        self.space = space
        self.left = space.budget - spent

    def afford(self, *ops: str) -> bool:
        """Whether one node of each of `ops` fits."""
        return sum(self.space.cost(op) for op in ops) <= self.left

    def spend(self, op: str) -> None:
        self.left -= self.space.cost(op)


def _drawn(draw: Draw, space: Space, audio: bool) -> Look:
    """One candidate look from `draw` (module docstring). Raises ValueError
    when not even one layer fits the budget."""
    purse = _Purse(space)
    hue = draw.uniform(0.0, 360.0)
    spin = slow(record_of(PaletteOp, "cycle"), draw.uniform(*PACE))
    programs: dict[str, Program] = {}
    mixes: dict[str, dict[str, Any]] = {}
    for i in range(draw.pick(LAYERS)):
        kind = draw.pick(BOTTOM if i == 0 else UPPER)
        cycle = spin * PHI**i * draw.sign() if draw.chance(CYCLES) else 0.0
        made = _program(draw, space, purse, kind, (hue + i * GOLDEN_ANGLE) % 360.0, cycle)
        if made is None:
            continue
        lid = "base" if not programs else free_id(as_id(kind), set(programs))
        programs[lid] = made.program()
        if len(programs) > 1:
            mixes[lid] = {"blend": draw.pick(BLENDS), "opacity": round(draw.uniform(*OPACITY[kind]), 2)}
    if not programs:
        raise ValueError(f"no look fits a budget of {space.budget:g} µs a frame on {space.points} points")
    routes = _routes(draw, programs, mixes, purse, audio)
    layers = [layer(lid, program, **mixes.get(lid, {})) for lid, program in programs.items()]
    return look(*layers, routes=routes, seed=draw.seed(), fade=round(draw.uniform(*FADE), 1),
                front=_front(programs, routes))


def _program(draw: Draw, space: Space, purse: _Purse, kind: str, hue: float, cycle: float) -> Expr | None:
    """One layer's program of `kind` (module docstring), its palette about
    `hue` cycling at `cycle`; None when its source does not fit the budget."""
    if kind == "echo":
        if not purse.afford("below"):
            return None
        purse.spend("below")
        return _then(draw, space, purse, "state", namespace()["below"]())
    chain = _source(draw, space, purse, "sim" if kind == "sim" else "field")
    if chain is None:
        return None
    if kind == "sim" and draw.chance(SIM_STATE):
        chain = _then(draw, space, purse, "state", chain)
    for _ in range(draw.pick(WARPS) if kind == "field" else int(kind == "trail" and draw.chance(0.5))):
        chain = _warp(draw, space, purse, chain)
    if kind != "trail":
        if draw.chance(TONE):
            chain = _then(draw, space, purse, "tone", chain)
        return _tint(draw, chain, hue, cycle)
    if draw.chance(STATE_FIRST):
        return _tint(draw, _then(draw, space, purse, "state", chain), hue, cycle)
    return _then(draw, space, purse, "state", _tint(draw, chain, hue, cycle))


def _source(draw: Draw, space: Space, purse: _Purse, kind: str) -> Expr | None:
    """A source of role `kind` the purse affords with a palette after it,
    both spent for, or None."""
    found = [cls for cls in ops(space, kind) if purse.afford(cls.op, "palette")]
    if not found:
        return None
    purse.spend("palette")  # the palette that ends the layer (`_tint`)
    return _node(draw, space, purse, draw.choice(found), None)


def _then(draw: Draw, space: Space, purse: _Purse, kind: str, chain: Expr) -> Expr:
    """`chain` read by a one-input op of role `kind` the purse affords; or
    `chain` as it is when none fits, or the program cannot take it."""
    found = [cls for cls in ops(space, kind) if len(cls.inputs) == 1 and purse.afford(cls.op)]
    return _checked(chain, _node(draw, space, purse, draw.choice(found), chain)) if found else chain


def _warp(draw: Draw, space: Space, purse: _Purse, chain: Expr) -> Expr:
    """`chain` warped: by a modulate whose second input is a smooth field
    (`MODULATORS`), or by a coord op; left as it is when the program
    cannot take the warp (above a node read only at the map's points) or
    none fits the budget."""
    warps = [cls for cls in ops(space, "warp") if purse.afford(cls.op)]
    coords = [cls for cls in warps if len(cls.inputs) == 1]
    smooth = {op: w for op, w in MODULATORS.items() if op in OPS and space.takes(OPS[op])}

    def fits(cls: type[Op]) -> dict[str, float]:
        """The smooth fields the purse affords with modulate `cls`."""
        return {op: w for op, w in smooth.items() if purse.afford(cls.op, op)}

    modulates = [cls for cls in warps if len(cls.inputs) == 2 and fits(cls)]
    if modulates and (not coords or draw.chance(MODULATE)):
        cls = draw.choice(modulates)
        by = _node(draw, space, purse, OPS[draw.pick(fits(cls))], None)
        return _checked(chain, _node(draw, space, purse, cls, chain, by))
    return _checked(chain, _node(draw, space, purse, draw.choice(coords), chain)) if coords else chain


def _checked(chain: Expr, made: Expr) -> Expr:
    """`made` when its program checks, else `chain`, which it extends."""
    try:
        made.program()
    except ValueError:
        return chain
    return made


def _node(draw: Draw, space: Space, purse: _Purse, cls: type[Op], chain: Expr | None, *more: Expr) -> Expr:
    """A node of op `cls` reading `chain` and `more`, each knob drawn."""
    purse.spend(cls.op)
    args = drawn_args(draw, cls, space.axes)
    if chain is None:
        return namespace()[cls.op](*more, **args)
    return getattr(chain, cls.op)(*more, **args)


def _tint(draw: Draw, chain: Expr, hue: float, cycle: float) -> Expr:
    """`chain` through a palette about `hue`, looped when it cycles; its
    layer's source spent for it."""
    gradient, shift = palette(draw, hue)
    if cycle:
        gradient = looped(gradient)
    return chain.palette(gradient, shift=shift, cycle=tidy(cycle, record_of(PaletteOp, "cycle")))


# ---- routes ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Target:
    """A knob a route may move: its address, its describe record, and its
    value now."""

    path: str
    record: Record
    now: float


_OPACITY: Record = LayerControls.opacity.spec()


def targets(programs: Mapping[str, Program], mixes: Mapping[str, Mapping[str, Any]],
            classes: KnobClass) -> list[Target]:
    """Every knob of `programs` (by layer id) a route may move: each float
    knob that is neither flash-sensitive nor a speed (a route into a speed
    speeds the look up), and each opacity `mixes` holds (an upper
    layer's). `classes(lid, node)` gives the class of a node's knobs."""
    found = []
    for lid, program in programs.items():
        for node in program.graph:
            found += (Target(layer_address(lid, node.id, r["name"]), r, float(node.args.get(r["name"], r["default"])))
                      for r in records(classes(lid, node)) if r["kind"] == "float" and not r["flash_sensitive"]
                      and not is_speed(r))
        if lid in mixes:
            found.append(Target(layer_address(lid, "opacity"), _OPACITY, float(mixes[lid].get("opacity", 1.0))))
    return found


def _op_class(lid: str, node: Node) -> type:
    return OPS[node.op]


def _routes(draw: Draw, programs: dict[str, Program], mixes: dict[str, dict[str, Any]], purse: _Purse,
            audio: bool) -> list[Routed]:
    """Up to two routes (`ROUTES`) into knobs of `programs`, each with its
    own signal, their rates a golden ratio apart; each knob moved is
    re-centred in `programs` or `mixes` so its swing stays in range."""
    out: list[Routed] = []
    pace = draw.uniform(*PACE)
    for j in range(draw.pick(ROUTES)):
        found = [t for t in targets(programs, mixes, _op_class) if t.path not in {r.path for r in out}]
        if not found:
            break
        target = found[draw.pick({i: 3.0 if t.record["periodic"] else 1.0 for i, t in enumerate(found)})]
        signal, depth, base = signal_for(draw, target, pace * PHI**-j, audio)
        if not purse.afford(signal.op):
            break
        purse.spend(signal.op)
        place(programs, mixes, target.path, base)
        sid = free_id(as_id(SIGNAL_NAMES.get(signal.op, signal.op)), {r.signal.pinned or "" for r in out})
        out.append(signal.id(sid).to(target.path, depth))
    return out


def signal_for(draw: Draw, target: Target, pace: float, audio: bool) -> tuple[Expr, float, float]:
    """A slow signal for `target`, its rate `pace` (0 to 1) across the slow
    share of its rate's sweet range; the route's depth; and the knob's
    value that keeps what the route adds within its sweet range (module
    docstring)."""
    record = target.record
    lo, hi = record["sweet"]
    kind = "band" if audio and draw.chance(BAND) else draw.pick(SIGNALS)
    cls = OPS[kind]
    args = drawn_args(draw, cls)
    if "rate" in args:
        args["rate"] = slow(record_of(cls, "rate"), pace)
    depth = (hi - lo) * draw.uniform(*DEPTH)
    if record["flash_sensitive"]:
        depth = min(depth, FLASH_DEPTH * (record["hi"] - record["lo"]))
    seamless = kind == "lfo" and record["periodic"]
    if kind == "lfo":
        args |= {"shape": "saw" if seamless else draw.pick(WAVES), "offset": LFO_START}
    depth = (hi - lo) / 2.0 if seamless else float(f"{depth:.3g}") * (draw.sign() if kind != "band" else 1)
    if record["periodic"]:
        return namespace()[kind](**args), depth, target.now
    # A swing (lfo, walk) moves the knob both ways, a level (band) one way.
    below, above = (abs(depth), abs(depth)) if kind != "band" else (0.0, depth)
    whole = {**record, "sweet": (record["lo"], record["hi"])}
    return namespace()[kind](**args), depth, tidy(min(max(target.now, lo + below), hi - above), whole)


def place(programs: dict[str, Program], mixes: dict[str, dict[str, Any]], path: str, base: float) -> None:
    """Set the knob at address `path` (`layers.<lid>.<nid>.<arg>`, or a
    layer's opacity) to `base` in `programs` or `mixes`."""
    _, lid, *rest = path.split(".")
    if rest == ["opacity"]:
        mixes[lid] = {**mixes.get(lid, {}), "opacity": base}
        return
    nid, name = rest
    program = programs[lid]
    nodes = tuple(replace(n, args={**n.args, name: base}) if n.id == nid else n for n in program.graph)
    programs[lid] = replace(program, graph=Graph(nodes))


def _front(programs: Mapping[str, Program], routes: Sequence[Routed]) -> list[str]:
    """The knobs a page shows first: those the routes move, then each
    layer's first knob, the bottom layer's first. A layer's opacity is never
    one: its row shows it."""
    paths = [route.path for route in routes]
    for lid, program in programs.items():
        first = program.graph.nodes[0]
        paths += [layer_address(lid, first.id, r["name"]) for r in records(OPS[first.op])[:1]]
    return list(dict.fromkeys(paths))[:FRONT]


# ---- the judge ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class Verdict:
    """What the judge found in one candidate before its liveness: why it
    fails the content gate (`unsafe`, empty when it passes), why it fails
    the taste gates, the look ready to run (None when it does not check),
    and the metrics of its preview (None when it did not render)."""

    unsafe: tuple[str, ...]
    taste: tuple[str, ...] = ()
    staged: Ready | None = None
    metrics: Metrics | None = None


def judge(candidate: Look, space: Space) -> Verdict:
    """`candidate` checked, rendered on `space`'s preview and measured
    (module docstring), without its liveness (`dead_knob`). Never raises."""
    try:
        staged = ready(candidate, pattern_dir=space.pattern_dir, catalog=space.catalog)
        frames, errors = play(staged, space.preview, round(PREVIEW_S * PREVIEW_FPS), PREVIEW_FPS, 0)
    except Refused as exc:
        return Verdict((f"it does not check: {exc}",))
    metrics = measure(frames, PREVIEW_FPS)
    near = FLASH_LIMIT >= metrics.flash_rate_max > SAFE_FLASH
    unsafe = (
        *errors, *limits(metrics),
        *((f"flashes {metrics.flash_rate_max:g} times a second; a made look keeps to {SAFE_FLASH:g}",) if near else ()),
        *(("it gives values that are not numbers",) if metrics.nonfinite else ()),
    )
    tail = measure(frames[-round(PREVIEW_FPS):], PREVIEW_FPS)
    return Verdict(unsafe, taste(metrics, tail, wants_colour(candidate)), staged, metrics)


def taste(metrics: Metrics, tail: Metrics, colour: bool) -> tuple[str, ...]:
    """The taste gates `metrics` fails (module docstring); `tail` is the
    last second's, and `colour` says the look's palettes have colour."""
    gates = {
        "too dark": metrics.black_fraction > DARK_BLACK or metrics.p95_luma < DARK_P95,
        "washed out": metrics.mean_luma > WASHED,
        "dies out": tail.black_fraction > DEAD_TAIL,
        "frozen": metrics.motion_energy < STILL_MOTION or metrics.frozen_fraction > STILL_FROZEN,
        "noise": metrics.motion_energy > NOISE_MOTION and metrics.spatial_detail > NOISE_DETAIL,
        "grey": colour and metrics.hue_clusters == 0,
    }
    return tuple(name for name, failed in gates.items() if failed)


def wants_colour(candidate: Look) -> bool:
    """Whether `candidate` means colour: a palette node with a colourful
    gradient in an enabled layer."""
    return any(
        colourful(_gradient(node.args["palette"]))
        for item in candidate.layers if item.enabled for node in item.program.graph
        if node.op == "palette" and "palette" in node.args
    )


_PALETTE = PaletteOp.palette  # the palette op's own param: it parses and writes a gradient


def _gradient(raw: Any) -> Gradient:
    parsed, _ = _PALETTE.parse("palette", raw)
    return parsed if parsed is not None else PRESETS[0]


def dead_knob(staged: Ready, space: Space) -> str | None:
    """The first knob of `staged` that does not change its preview by
    `LIVE_MARGIN` times the liveness threshold, or cannot be probed, as
    "<path>" or "<path>: <why>"; None when every knob does. Stops at the
    first, as each probe renders the look twice."""
    for probe in each_probe(staged, space.preview, 0):
        if probe.error is not None:
            return f"{probe.path}: {probe.error}"
        if probe.rms is None or probe.rms <= LIVE_MARGIN * LIVENESS_RMS:
            return probe.path
    return None


def best(space: Space, candidates: Iterable[Look], seed: int) -> Look:
    """The first of `candidates` that passes the content gate and the taste
    gates, else the one that passes the content gate and fails fewest
    taste gates (module docstring). A candidate is probed for liveness, the
    costly part, only when it could be the answer. Raises NoLook when none
    passes the content gate."""
    found: tuple[int, Look] | None = None
    for candidate in candidates:
        verdict = judge(candidate, space)
        if verdict.unsafe or (found is not None and len(verdict.taste) >= found[0]):
            continue
        assert verdict.staged is not None  # it checked: nothing unsafe
        if dead_knob(verdict.staged, space) is not None:
            continue
        if not verdict.taste:
            return candidate
        found = (len(verdict.taste), candidate)
    if found is None:
        raise NoLook(f"nothing made from seed {seed} passed the content gate in {TRIES} tries; try another seed")
    return found[1]


# ---- mutation --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Held:
    """The addresses `mutate` keeps: each, and all under it; and whether
    the look's seed is kept (`seed`), as it is with a layer, node or
    signal, whose random stream comes from the seed
    (pewpew.compose.stack.layer_seed)."""

    paths: tuple[str, ...] = ()
    seed: bool = False

    @classmethod
    def of(cls, keep: Iterable[str], staged: Ready) -> Held:
        """`keep` held in `staged`'s look. Raises Refused for an address
        that names no knob of it, nor a layer, node or signal above one,
        at `keep[<index>]`."""
        given = list(keep)
        knobs = list(_controls(staged).snapshot_json())
        known = {prefix for path in knobs for prefix in _prefixes(path)}
        above = sorted(known)  # a knob, or a layer, node or signal above one
        refused = [
            Problem(f"keep[{i}]", Code.BAD_REF, f"keep[{i}]: unknown address {path!r}{typo_hint(path, above)}; "
                    f"keep takes a knob's address, or a layer, node or signal above one: {', '.join(knobs)}",
                    did_you_mean(path, above), tuple(knobs))
            for i, path in enumerate(given) if path not in known
        ]
        if refused:
            raise Refused(refused)
        paths = tuple(dict.fromkeys(given))
        return cls(paths, seed=not set(paths) <= set(knobs))

    def holds(self, path: str) -> bool:
        """Whether `path` is held: it or an address above it is kept."""
        return any(path == k or path.startswith(f"{k}.") for k in self.paths)

    def touches(self, path: str) -> bool:
        """Whether `path` is held, or holds a kept address under it."""
        return self.holds(path) or any(k.startswith(f"{path}.") for k in self.paths)

    def holds_route(self, route: Route) -> bool:
        """Whether `route` is held: the knob it moves is, or its signal."""
        return self.holds(route.path) or self.holds(signal_address(route.source))


def _prefixes(path: str) -> Iterator[str]:
    parts = path.split(".")
    return (".".join(parts[:k]) for k in range(1, len(parts) + 1))


def _controls(staged: Ready, candidate: Look | None = None) -> Controls:
    """The knobs of `candidate` (default `staged`'s look), its patterns as
    `staged` resolved them."""
    known: dict[str, type] = {}
    for resolved in staged.layers:
        for node in resolved.layer.program.graph:
            if node.op == PATTERN:
                known[node.args[PATTERN]] = knob_class(node, resolved.resolve)
    return look_controls(candidate or staged.look, known.get)


def _mutated(draw: Draw, staged: Ready, space: Space, s: float, held: Held, audio: bool) -> Look:
    """One candidate like `staged`'s look at strength `s` (module
    docstring), holding `held`."""
    base = staged.look
    by_id = {resolved.layer.id: resolved for resolved in staged.layers}

    def classes(lid: str, node: Node) -> type:
        return knob_class(node, by_id[lid].resolve)

    programs: dict[str, Program] = {}
    mixes: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(base.layers):
        lid = item.id
        programs[lid] = _nudged(draw, item.program, lid, classes, s, held, space.axes)
        mix = dict(item.mix)
        if i and not held.holds(layer_address(lid, "blend")) and draw.chance(REBLEND * s):
            mix["blend"] = draw.pick(BLENDS)
        if i and not held.holds(layer_address(lid, "opacity")) and _nudges(draw, s):
            mix["opacity"] = nudge(draw, _OPACITY, item.opacity, s)
        mixes[lid] = mix
    routes = list(base.routes)
    if draw.chance(SWAP * s * s):
        _swap(draw, programs, routes, space, held, look_cost(base, space.points))
    signals = [replace(n, args=_nudged_args(draw, n, OPS[n.op], signal_address(n.id), s, held, space.axes))
               for n in base.signals or ()]
    if draw.chance(REROUTE * s):
        _reroute(draw, programs, mixes, signals, routes, classes, held, space, audio)
    layers = tuple(replace(item, program=programs[item.id], **mixes[item.id]) for item in base.layers)
    reseed = not held.seed and draw.chance(RESEED * s)
    made = replace(base, layers=layers, seed=draw.seed() if reseed else base.seed)
    return _pruned(made, signals, routes, staged)


def _nudged(draw: Draw, program: Program, lid: str, classes: KnobClass, s: float, held: Held,
            axes: frozenset[str]) -> Program:
    """`program`, layer `lid`'s, with each knob of each node nudged
    (`nudge`, on a mapping spanning `axes`) and each palette now and then
    repainted, but what `held` holds."""
    nodes = []
    for node in program.graph:
        where = layer_address(lid, node.id)
        args = _nudged_args(draw, node, classes(lid, node), where, s, held, axes)
        if node.op == "palette" and not held.holds(f"{where}.palette") and draw.chance(REPAINT * s):
            gradient, _ = palette(draw, draw.uniform(0.0, 360.0))
            cycling = bool(args.get("cycle"))
            args["palette"] = _PALETTE.to_json(looped(gradient) if cycling else gradient)
        nodes.append(replace(node, args=args))
    return replace(program, graph=Graph(tuple(nodes)))


def _nudged_args(draw: Draw, node: Node, cls: type, where: str, s: float, held: Held,
                 axes: frozenset[str]) -> dict[str, Any]:
    """`node`'s args, each knob of class `cls` at address `<where>.<name>`
    that `held` does not hold nudged now and then (`_nudges`) on a mapping
    spanning `axes`."""
    args = dict(node.args)
    for record in records(cls):
        name = record["name"]
        if name in args and not held.holds(f"{where}.{name}") and _nudges(draw, s):
            args[name] = nudge(draw, record, args[name], s, axes)
    return args


def _nudges(draw: Draw, s: float) -> bool:
    """Whether a knob moves at strength `s`: with chance NUDGE[0] + NUDGE[1] s."""
    return draw.chance(NUDGE[0] + NUDGE[1] * s)


def _swap(draw: Draw, programs: dict[str, Program], routes: Sequence[Route], space: Space, held: Held,
          spent: float) -> None:
    """Swap one node of `programs` that `held` does not touch, and no held
    route moves, for a node of another op of its role and inputs that
    runs on `space`, fits the budget (`spent` so far) and leaves its
    program checking; its knobs drawn anew and its id from its op."""
    driven = [route.path for route in routes if held.holds_route(route)]

    def free(lid: str, node: Node) -> bool:
        where = layer_address(lid, node.id)
        return not held.touches(where) and not any(path.startswith(f"{where}.") for path in driven)

    found = [(lid, node) for lid, program in programs.items() for node in program.graph
             if node.op in OPS and role(OPS[node.op]) is not None and free(lid, node)]
    if not found:
        return
    lid, node = draw.choice(found)
    old = OPS[node.op]
    purse = _Purse(space, spent - space.cost(node.op))
    others = [cls for cls in ops(space, role(old) or "") if cls is not old
              and len(cls.inputs) == len(old.inputs) and purse.afford(cls.op)]
    if not others:
        return
    cls = draw.choice(others)
    program = programs[lid]
    nid = free_id(as_id(cls.op), {n.id for n in program.graph})
    args = drawn_args(draw, cls, space.axes)
    rename = {node.id: nid}
    nodes = tuple(
        Node(nid, cls.op, args, n.inputs) if n.id == node.id
        else replace(n, inputs=tuple(rename.get(i, i) for i in n.inputs))
        for n in program.graph
    )
    swapped = Program(Graph(nodes), rename.get(program.out, program.out),
                      None if program.alpha is None else rename.get(program.alpha, program.alpha))
    if not check(swapped, dims=space.dims, hosted=True):
        programs[lid] = swapped


def _reroute(draw: Draw, programs: dict[str, Program], mixes: dict[str, dict[str, Any]], signals: list[Node],
             routes: list[Route], classes: KnobClass, held: Held, space: Space, audio: bool) -> None:
    """Drop one route that `held` does not hold, or add one into a knob it
    does not hold, with a signal of its own that fits the budget."""
    free = [route for route in routes if not held.holds_route(route)]
    if free and (len(routes) >= max(ROUTES) or draw.chance(0.5)):
        routes.remove(draw.choice(free))
        return
    taken = {route.path for route in routes}
    upper = dict(list(mixes.items())[1:])  # a route moves an upper layer's opacity only
    found = [t for t in targets(programs, upper, classes) if t.path not in taken and not held.holds(t.path)]
    if not found:
        return
    target = draw.choice(found)
    signal, depth, base = signal_for(draw, target, draw.uniform(*PACE), audio)
    if not _Purse(space, _cost(programs.values(), signals, space.points)).afford(signal.op):
        return
    sid = free_id(as_id(SIGNAL_NAMES.get(signal.op, signal.op)), {n.id for n in signals})
    place(programs, mixes, target.path, base)
    signals.append(Node(sid, signal.op, signal.args))
    routes.append(Route(sid, target.path, depth))


def _pruned(made: Look, signals: Sequence[Node], routes: Sequence[Route], staged: Ready) -> Look:
    """`made` with `signals` and `routes`, less each route that cannot move
    its knob any more (pewpew.compose.modulation.route_problems), each
    signal nothing reads, with the routes into its knobs, and each front
    knob that is gone."""
    controls = _controls(staged, replace(made, signals=Graph(tuple(signals)) if signals else None, routes=(),
                                         front=()))
    kept = [route for route in routes if not route_problems([route], (), controls)]
    left = list(signals)
    while True:
        ids = {node.id for node in left}
        kept = [r for r in kept if r.source in ids and (signal_of(r.path) is None or signal_of(r.path) in ids)]
        read = {route.source for route in kept} | {source for node in left for source in node.inputs}
        if all(node.id in read for node in left):
            break
        left = [node for node in left if node.id in read]
    gone = {node.id for node in signals} - {node.id for node in left}
    front = tuple(path for path in made.front
                  if signal_of(path) not in gone and not route_problems((), (path,), controls))
    return replace(made, signals=Graph(tuple(left)) if left else None, routes=tuple(kept), front=front)
