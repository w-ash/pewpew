"""Modulation: a look's signals running, and its routes moving the knobs
of its stack (ADR-021's modulation seat; ADR-006 amendment "layered
paths").

A `Compositor` runs its `Modulation` once a frame, before any layer
advances. Each signal, in graph order (after the signals it reads and the
signals whose routes drive it), first has its own knobs moved by the
routes into them, then steps its phases and samples its value
(pewpew.fx.ops.signal), kept within its range. Then each route into a
layer's knob moves it. A knob several routes reach moves by the sum of
`depth` times each signal. A route moves a knob through its set's binding
(`Bound.drive`): what the op reads moves, while the set keeps
the operator's value, so a page shows it and a saved look stores it. Only
route targets are driven, so a knob no route reaches costs nothing.

A route finds its knob by address through the stack's `Controls`
(`bind`), again whenever the stack's knobs change (a layer edit):
a route that cannot move its knob any more (the knob is gone, or its span
is now less than the route's depth) rests, and a knob no route reaches any
more reads its own value again. When the stack is built every route must
reach a knob it can move, by at most the knob's span (`route_problems`);
`signal_problems` judges the signal graph itself. `front` is layout only:
a path that names no whole knob is left out, never refused, so a look
whose program changed still recalls; one whose node is gone gives its
place to the first knob of what runs on its layer now. A look's checks
refuse such a path (`route_problems`). An operator sets the front whole
(`set_front`).

Randomness: a signal's key is the key a node of the same id would have
on a layer `signals` (pewpew.fx.op.node_key over `layer_seed`), so its
draws come from the whole look seed and its own id.

Containment: signals run outside every layer's renderer. A signal that
raises, or gives anything but a finite number, holds its last value and
becomes `error`, a `RenderFailure` whose path is `signals.<sid>`, and the
stack renders on; a route that cannot move its knob is its signal's
error. Each failure site is logged once; a frame with no failure clears
the error.

`values` is each driven knob's live value, by address, rounded to the
knob's decimals: the page's read-only readout (the `mod` message). It is
made on the loop thread each frame; `values`, `state`, `error` and
`snapshot` may be read from any thread.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from pewpew.compose.controls import LAYERS, SIGNALS, Controls, Knob, Section, signal_address, signal_of
from pewpew.compose.stack import Route, layer_seed, source_problems
from pewpew.errors import blame, unknown
from pewpew.features import FeatureSource
from pewpew.fx.compile import check_signals
from pewpew.fx.graph import Graph, Node
from pewpew.fx.op import FrameCtx, node_key
from pewpew.fx.ops import OPS
from pewpew.fx.ops.signal import Range, SignalOp, ranges
from pewpew.params import Float, ParamSet
from pewpew.params.kinds import Parsed, Ranged
from pewpew.render import RenderFailure, contain


def signal_problems(signals: Graph | None, routes: Sequence[Route] | None) -> list[str]:
    """Every problem with a look's signal graph (pewpew.fx.compile
    .check_signals), and with its `routes` (None: not known), each signal
    nothing reads: no route takes it and no signal reads it. Never
    raises."""
    if signals is None:
        return []
    problems = check_signals(signals, where=SIGNALS)
    if routes is not None:
        read = {route.source for route in routes} | {source for node in signals for source in node.inputs}
        problems += (f"{signal_address(node.id)}: nothing reads signal {node.id!r}; route it to a knob, or remove it"
                     for node in signals if node.id not in read)
    return problems


def route_problems(routes: Sequence[Route], front: Sequence[str], controls: Controls) -> list[str]:
    """Why each of `routes` cannot move its knob among `controls`
    (`_knob_of`), and why each path of `front` names no whole knob. Never
    raises."""
    problems = [f"routes[{i}]: {reason}" for i, route in enumerate(routes)
                if (reason := _knob_of(route, controls)[1]) is not None]
    problems += (f"front[{i}]: {reason}" for i, path in enumerate(front)
                 if (reason := _front_problem(path, controls)) is not None)
    return problems


def _knob_of(route: Route, controls: Controls) -> Parsed[tuple[Knob, Ranged[Any]]]:
    """The knob among `controls` that `route` moves, with what it moves on
    it, or why it cannot: no knob at its path (with a did-you-mean among
    the knobs a route can move), a knob that cannot be modulated, or a
    depth past the knob's span. Never raises."""
    knob = controls.find(route.path)
    if knob is None:
        return None, unknown("knob", route.path, controls.modulatable(), suggest=True)
    moved, reason = knob.drive_range()
    if reason is not None:
        return None, reason
    assert moved is not None  # `Parsed`: no reason, so a value
    span = moved.hi - moved.lo
    if (reason := Float(0.0, -span, span).parse("depth", route.depth)[1]) is not None:
        return None, f"{reason}; a route moves {route.path} by at most its span, {span:g}"
    return (knob, moved), None


def _shown(front: Sequence[str], controls: Controls) -> tuple[str, ...]:
    """The paths of `front` that name a whole knob among `controls`, in
    order; one whose node is gone from a layer that still runs gives its
    place to that layer's first node knob, once."""
    shown: list[str] = []
    for path in front:
        if _front_problem(path, controls) is None:
            shown.append(path)
        elif (first := _in_place(path, controls)) is not None:
            shown.append(first)
    return tuple(dict.fromkeys(shown))


def _in_place(path: str, controls: Controls) -> str | None:
    """The knob that takes the place of node knob `path`
    (`layers.<lid>.<node>.<knob>`) when its node no longer runs: its
    layer's first node's first knob; None while the node runs, or with no
    such layer."""
    head, lid, node, *_ = [*path.split("."), "", ""]
    if head != LAYERS or not lid or not node or f"{LAYERS}.{lid}.{node}" in controls.sections:
        return None
    for owner, section in controls.sections.items():
        if section.layer == lid and section.node and section.params.declarations:
            return f"{owner}.{next(iter(section.params.declarations))}"
    return None


def _front_problem(path: str, controls: Controls) -> str | None:
    """Why `path` names no whole knob among `controls`, or None."""
    knob = controls.find(path)
    if knob is None:
        return unknown("knob", path, controls.snapshot_json(), suggest=True)
    if knob.part:
        whole = path.rpartition(".")[0]
        return f"{path} is a part of {whole}; list {whole}, the whole knob"
    return None


@dataclass(frozen=True, slots=True, eq=False)
class _Target:
    """One knob the routes move: the knob, its address, what a route moves
    on it (for its decimals), and each route's signal index and depth."""

    knob: Knob
    path: str
    moved: Ranged[Any]
    sources: tuple[tuple[int, float], ...]


@dataclass(slots=True, eq=False)
class _Signal:
    """One running signal: its node, op and knobs, its key, its range, the
    indices of the signals it reads, and the targets of the routes into
    its own knobs."""

    node: Node
    op: SignalOp
    params: ParamSet
    key: int
    range: Range
    reads: tuple[int, ...]
    into: tuple[_Target, ...] = ()


class Modulation:
    """A look's signals and routes, running (module docstring)."""

    def __init__(self, signals: Graph | None, routes: Sequence[Route], front: Sequence[str], seed: int) -> None:
        """Make each signal of `signals`, keyed by the look's `seed` and its
        id (module docstring), its knobs at its node's args. Raises
        TypeError for an op that is not a signal op, and ValueError for an
        arg its knob refuses or a route `source_problems` refuses."""
        self.routes = tuple(routes)
        self.front = tuple(front)
        nodes = tuple(signals or ())
        for node in nodes:
            if not issubclass(OPS.get(node.op, object), SignalOp):
                raise TypeError(f"{signal_address(node.id)}: {node.op!r} is not a signal op")
        if problems := source_problems(signals, self.routes):
            raise ValueError("; ".join(problems))
        self._index = {node.id: i for i, node in enumerate(nodes)}
        spans = ranges(nodes)
        derived = layer_seed(seed, SIGNALS)
        self._signals = tuple(self._make(node, spans[node.id], derived) for node in nodes)
        self._values = [0.0] * len(nodes)
        self._layers: tuple[_Target, ...] = ()
        self._active: tuple[Route, ...] = ()
        self._shown: tuple[str, ...] = ()
        self._live: Mapping[str, float] = MappingProxyType({})
        self._tick = 0
        self._error: RenderFailure | None = None
        self._logged: set[tuple] = set()

    def _make(self, node: Node, span: Range, seed: int) -> _Signal:
        """Signal `node`, which gives `span`, running: its op bound to its
        knobs, keyed by the signals' derived `seed` and its id."""
        cls = OPS[node.op]
        op = cls()
        assert isinstance(op, SignalOp)  # checked by the constructor
        params = ParamSet(cls, node.args, name=signal_address(node.id))
        params.apply(op)
        reads = tuple(self._index[source] for source in node.inputs)
        return _Signal(node, op, params, node_key(seed, SIGNALS, node.id), span, reads)

    # ---- state (any thread) ---------------------------------------------

    @property
    def error(self) -> RenderFailure | None:
        """The current contained failure of a signal or a route, or None."""
        return self._error

    def sections(self) -> list[Section]:
        """Each signal's knob set, in graph order: its address
        `signals.<sid>`, no layer, and the signal's id as its node."""
        return [Section(signal.params, "", signal.node.id) for signal in self._signals]

    def values(self) -> Mapping[str, float]:
        """Each driven knob's value as of the last frame, by address,
        rounded to its decimals (module docstring)."""
        return self._live

    def state(self) -> dict[str, list[Any]]:
        """The signals (id, op, label, the ids of the signals each reads,
        and the range of what it gives: a page shows a route that swings
        both ways as ±), the routes that run and the front knobs that
        exist, for a page. JSON-ready, names only."""
        return {
            "signals": [{"id": s.node.id, "op": s.node.op, "label": s.op.label, "in": list(s.node.inputs),
                         "range": list(s.range)} for s in self._signals],
            "routes": [route.to_json() for route in self._active],
            "front": list(self._shown),
        }

    def snapshot(self) -> tuple[Graph | None, tuple[Route, ...], tuple[str, ...]]:
        """What runs, as a look holds it: the signals at their knobs' live
        values, the routes that run, and the front knobs that exist. A
        signal nothing reads any more (its routes rest) is left out, with
        the routes into its knobs and its front knobs, so the look checks
        again."""
        routes = list(self._active)
        nodes = {s.node.id: s.node for s in self._signals}
        while True:
            kept = _reached([route.source for route in routes], nodes)
            pruned = [route for route in routes if _kept(route.path, kept)]
            if len(pruned) == len(routes):
                break
            routes = pruned
        signals = tuple(replace(s.node, args=s.params.snapshot_json()) for s in self._signals if s.node.id in kept)
        front = tuple(path for path in self._shown if _kept(path, kept))
        return (Graph(signals) if signals else None), tuple(routes), front

    # ---- the loop thread --------------------------------------------------

    def bind(self, controls: Controls, *, strict: bool = False) -> None:
        """Find each route's knob among `controls`, the stack's knobs now
        (module docstring). A route `route_problems` refuses rests; with
        `strict`, raises ValueError naming each such route instead, with
        nothing changed. A front path that names no whole knob is left out.
        A knob the last binding drove and this one does not reads its own
        value again."""
        if strict and (problems := route_problems(self.routes, (), controls)):
            raise ValueError("; ".join(problems))
        found: dict[str, tuple[Knob, Ranged[Any], list[tuple[int, float]]]] = {}
        active: list[Route] = []
        for route in self.routes:
            reached, _ = _knob_of(route, controls)
            if reached is None:
                continue
            knob, moved = reached
            found.setdefault(route.path, (knob, moved, []))[2].append((self._index[route.source], route.depth))
            active.append(route)
        targets = [_Target(knob, path, moved, tuple(sources)) for path, (knob, moved, sources) in found.items()]
        for old in self._targets():
            if old.path not in found and (bound := old.knob.params.bound) is not None:
                bound.undrive(old.knob.path)
        for signal in self._signals:
            signal.into = tuple(t for t in targets if signal_of(t.path) == signal.node.id)
        self._layers = tuple(t for t in targets if signal_of(t.path) is None)
        self._active = tuple(active)
        self._shown = _shown(self.front, controls)

    def set_front(self, front: Sequence[str], controls: Controls) -> str | None:
        """Show the knobs `front` names first, in its order, each once: an
        operator's edit of the look, which a save keeps. Returns why not,
        naming each path that names no whole knob among `controls`, or
        None."""
        front = tuple(front)
        if len(set(front)) != len(front):
            return f"a look's front lists each knob once, got {list(front)!r}"
        problems = [f"front[{i}]: {reason}" for i, path in enumerate(front)
                    if (reason := _front_problem(path, controls)) is not None]
        if problems:
            return "; ".join(problems)
        self.front = front
        self._shown = front
        return None

    def advance(self, t: float, dt: float, features: FeatureSource) -> None:
        """Run the frame at engine time `t`, `dt` after the last one:
        every signal, then every route into a layer (module docstring).
        Never raises."""
        if not self._signals:
            return
        self._tick += 1
        failed: tuple[int, Exception] | None = None
        try:
            frame = features.at(t)
        except Exception as exc:  # noqa: BLE001  contained: every signal holds
            self._fail(0, exc, t)
            return
        values = self._values
        for i, signal in enumerate(self._signals):
            drove = self._drive(signal.into)
            failed = failed or drove
            try:
                signal.op.step(dt)
                value = signal.op.sample(FrameCtx(dt, frame, self._tick, signal.key), [values[j] for j in signal.reads])
                if not (isinstance(value, int | float) and math.isfinite(value)):
                    raise ValueError(f"{signal.node.op} gave {value!r}; a signal gives a finite number each frame")
            except Exception as exc:  # noqa: BLE001  contained: the signal holds its last value
                failed = failed or (i, exc)
                continue
            lo, hi = signal.range
            values[i] = min(max(float(value), lo), hi)
        drove = self._drive(self._layers)
        failed = failed or drove
        self._live = MappingProxyType(self._read())
        if failed is not None:
            self._fail(*failed, t)
        else:
            self._error = None

    def _targets(self) -> Iterable[_Target]:
        for signal in self._signals:
            yield from signal.into
        yield from self._layers

    def _drive(self, targets: Iterable[_Target]) -> tuple[int, Exception] | None:
        """Move each of `targets` by its routes' offsets; the first failure,
        by the index of the signal of its first route."""
        failed = None
        for target in targets:
            bound = target.knob.params.bound
            if bound is None:
                continue
            try:
                bound.drive(target.knob.path, sum(depth * self._values[i] for i, depth in target.sources))
            except Exception as exc:  # noqa: BLE001  contained: the knob keeps its last offset
                failed = failed or (target.sources[0][0], exc)
        return failed

    def _read(self) -> dict[str, float]:
        """Each driven knob's value now, rounded to its decimals."""
        out = {}
        for target in self._targets():
            bound = target.knob.params.bound
            if bound is None:
                continue
            value = bound.value(target.knob.name)
            part = target.knob.part
            out[target.path] = round(getattr(value, part) if part else value, target.moved.decimals)
        return out

    def _fail(self, i: int, exc: Exception, t: float) -> None:
        """Make the failure of signal `i` the error, logged once per site
        (pewpew.render.contain)."""
        node = self._signals[i].node
        path = signal_address(node.id)
        blame(exc, path, f"in signal {path} ({node.op})")
        self._error = contain(path, "sample", exc, self._tick, t, self._logged, outcome="; it holds its last value")


def _kept(path: str, kept: set[str]) -> bool:
    """Whether knob address `path` is a layer's, or a signal's in `kept`."""
    return (sid := signal_of(path)) is None or sid in kept


def _reached(sources: Iterable[str], nodes: Mapping[str, Node]) -> set[str]:
    """The ids of `sources` and every signal they read, directly or not."""
    seen: set[str] = set()
    stack = [sid for sid in sources if sid in nodes]
    while stack:
        sid = stack.pop()
        if sid not in seen:
            seen.add(sid)
            stack.extend(nodes[sid].inputs)
    return seen
