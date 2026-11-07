"""The fluent builder: effect programs written as Python chains (ADR-022).

    from pewpew.fx.expr import noise, osc

    osc(8, 0.1).kaleid(5).modulate(noise(3), 0.2).palette("ember")

A source op is a function (`osc(...)`, `pattern("plasma")`); every other op
is a method of what it reads (`.kaleid(5)`): the receiver is its first
input, and a combine or modulate op takes its second input first
(`a.add(b, 0.5)`). Positional args follow the op's declared order and
keywords name them. Each literal is parsed when written, in the params'
own words, so a bad value fails at once (`kaleid.sides must be within
1..24, got 40`). An arg is a value, never a function.

`Program.of(expr)` (or `expr.program()`) gives the program. A node's id is
the one `.id("waves")` pins, or the op's name with an ordinal past the
first of that op (`osc`, `osc2`), counted in the order Python evaluates
the chain: inputs before the node, the receiver before the args. One
builder used twice is one node: `w = osc(8); w.add(w.kaleid(5))`.

A signal op (`lfo`, `walk`, `knob`, ...; pewpew.fx.ops.signal) builds the
same way and gives one number a frame. `signal.to(path, depth=...)`
routes it to the knob at an address; a signal given as an arg of a float
or int knob is a route too, which sweeps the knob's sweet range: the arg
starts where the signal's 0 puts it in that range, and the route's depth
spreads the signal's range over it. Signals and routes belong to a look,
not a program, so a look is built with `look(layer("base", ...), ...,
routes=[...])`:

    look(layer("base", noise(3).palette("ember", shift=lfo(0.05))),
         routes=[knob(0.5).id("macro").to("layers.base.noise.scale", depth=4)])

A signal's id comes from its op's name, as a node's does, counted over
the whole look in the order of its routes; one signal builder used twice
is one signal (a macro: one `knob` with several routes).

The stub beside this module (`expr.pyi`) is generated from the catalog
(pewpew.fx.catalog.stub) for editors and type checkers.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import partial
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pewpew.classinfo import pattern_name
from pewpew.errors import unknown
from pewpew.fx.compile import check
from pewpew.fx.graph import PATTERN, Graph, Node, Program, as_id, auto_id, post_order, require_id
from pewpew.fx.op import Op
from pewpew.fx.ops import OPS, labels
from pewpew.fx.ops.signal import Range, SignalOp
from pewpew.fx.types import Sig
from pewpew.params import Param, ParamSet, declared_params
from pewpew.params.bound import drive_range

if TYPE_CHECKING:
    from pewpew.compose.stack import Look


@dataclass(frozen=True, slots=True, eq=False)
class Expr:
    """One node being written: its op, its args (JSON values, the ones
    given), the builders it reads, the id `.id` pinned, for a pattern node
    the pattern's class, and the route of each arg a signal drives, its
    path the arg's name. Compared by identity: one builder, one node."""

    op: str
    args: Mapping[str, Any]
    inputs: tuple[Expr, ...] = ()
    pinned: str | None = None
    pattern_cls: type | None = field(default=None, repr=False)
    driven: tuple[Routed, ...] = field(default=(), repr=False)

    def id(self, nid: str) -> Expr:
        """This node with id `nid`. Raises ValueError for an id the
        address grammar refuses."""
        return replace(self, pinned=require_id(nid))

    @property
    def signal(self) -> bool:
        """Whether this is a signal: one number a frame, not a field."""
        return OPS[self.op].sig == Sig.SIGNAL

    def to(self, path: str, depth: float) -> Routed:
        """This signal routed to the knob at address `path`, moving it by
        `depth` times the signal, in the knob's units: for `look(routes=...)`.
        Raises TypeError for a node that is not a signal."""
        if not self.signal:
            raise TypeError(f"{self.op} gives a field, not a signal; route a signal op, such as lfo(0.1).to(...)")
        return Routed(self, path, float(depth))

    def __getattr__(self, name: str) -> Callable[..., Expr]:
        if name.startswith("_"):
            raise AttributeError(name)
        cls = OPS.get(name)
        if cls is None:
            ops = sorted(op for op, c in OPS.items() if c.inputs)
            raise AttributeError(unknown("op", name, ops, suggest=True, aliases=labels(ops)))
        if not cls.inputs:
            raise AttributeError(
                f"{name} is a source and reads no node; call {name}(...) and combine it, "
                f"as .add({name}(...)) or .modulate({name}(...))"
            )
        return partial(_node, cls, self)

    def program(self, alpha: Expr | None = None) -> Program:
        """The program this expression ends in, masked by `alpha`. Raises
        ValueError for an id used twice, a program `check` refuses, or an
        arg a signal drives, which only a look holds."""
        program, driven = self.built(alpha)
        if driven:
            raise ValueError(f"{driven[0].path} is driven by a signal, and signals belong to a look: build it with "
                             f'look(layer("base", ...))')
        return program

    def built(self, alpha: Expr | None = None) -> tuple[Program, list[Routed]]:
        """The program this expression ends in, masked by `alpha`, and the
        route of each arg a signal drives, its path `<node>.<arg>`. Raises
        ValueError for an id used twice or a program `check` refuses."""
        order = post_order([self] if alpha is None else [self, alpha], lambda e: e.inputs)
        ids = assign_ids([(id_base(e.op, e.args), e.pinned) for e in order])
        by_expr = dict(zip(order, ids))  # an Expr hashes by identity
        nodes = tuple(Node(by_expr[e], e.op, e.args, tuple(by_expr[s] for s in e.inputs)) for e in order)
        program = Program(Graph(nodes), by_expr[self], None if alpha is None else by_expr[alpha])
        patterns = self.patterns() | (alpha.patterns() if alpha is not None else {})
        if problems := check(program, resolve=patterns.get):
            raise ValueError("; ".join(problems))
        return program, [replace(wire, path=f"{by_expr[e]}.{wire.path}") for e in order for wire in e.driven]

    def patterns(self) -> dict[str, type]:
        """The class of each pattern node's pattern, by spec."""
        found: dict[str, type] = {}
        stack: list[Expr] = [self]
        while stack:
            e = stack.pop()
            if e.pattern_cls is not None:
                found[str(e.args[PATTERN])] = e.pattern_cls
            stack.extend(e.inputs)
        return found


def id_base(op: str, args: Mapping[str, Any]) -> str:
    """What a node's id is made from when none is pinned: its op's name,
    or for a pattern node its pattern's name."""
    spec = args.get(PATTERN) if op == PATTERN else None
    return as_id(spec) if isinstance(spec, str) and spec else as_id(op)


def assign_ids(nodes: list[tuple[str, str | None]]) -> list[str]:
    """The ids of nodes given as (`id_base`, pinned id or None) in
    evaluation order: the pinned one, or the base with an ordinal past its
    first (`osc`, `osc2`). Raises ValueError for an id used twice."""
    counts: Counter[str] = Counter()
    ids = []
    for base, pinned in nodes:
        counts[base] += 1
        ids.append(pinned if pinned is not None else auto_id(base, counts[base]))
    twice = sorted(nid for nid, k in Counter(ids).items() if k > 1)
    if twice:
        raise ValueError(f"ids {', '.join(map(repr, twice))} are used by more than one node; pin others with .id()")
    return ids


def _node(cls: type[Op], receiver: Expr | None, *args: Any, **kwargs: Any) -> Expr:
    """A node of op `cls` reading `receiver` (None for a source) and the
    inputs at the front of `args`, at the rest of `args` and `kwargs`."""
    rest = list(args)
    inputs = [] if receiver is None else [receiver]
    for port in cls.inputs[len(inputs):]:
        if not rest or not isinstance(rest[0], Expr):
            got = "nothing" if not rest else repr(rest[0])
            raise TypeError(f"{cls.op} reads {len(cls.inputs)} nodes; pass the node it reads on {port.name!r} "
                            f"first, got {got}")
        inputs.append(rest.pop(0))
    return _with_args(cls.op, tuple(inputs), cls, rest, kwargs)


def _with_args(op: str, inputs: tuple[Expr, ...], knobs: type, args: list[Any], kwargs: Mapping[str, Any],
               fixed: Mapping[str, Any] | None = None, pattern_cls: type | None = None) -> Expr:
    """An `Expr` of `op` whose knobs (the params of `knobs`) are `args` in
    declared order and `kwargs`, each parsed now, a signal given for one
    driving it (`swept`); a refusal names the op, or a pattern node's
    pattern."""
    names = list(declared_params(knobs))
    if len(args) > len(names):
        raise TypeError(f"{op} takes {len(names)} args ({', '.join(names) or 'none'}), got {len(args)}")
    values = dict(zip(names, args))
    for name in kwargs.keys() & values.keys():
        raise TypeError(f"{op} got {name!r} twice, by position and by name")
    values.update(kwargs)
    params = ParamSet(knobs, name=op if pattern_cls is None else pattern_name(pattern_cls))
    out: dict[str, Any] = dict(fixed or {})
    driven: list[Routed] = []
    for name, given in values.items():
        param, value = params.declarations.get(name), given
        if param is None:
            pass  # `parse` names the unknown param, whatever was given for it
        elif isinstance(given, Expr) and given.signal:
            value, depth = swept(param, f"{params.owner}.{name}", signal_range(given))
            driven.append(Routed(given, name, depth))
        elif callable(given) or isinstance(given, Expr):
            raise TypeError(
                f"{op}.{name} takes a value or a signal, not {'a node' if isinstance(given, Expr) else 'a function'}: "
                "to let one field move another, use modulate"
            )
        parsed, reason = params.parse(name, value)
        if reason is not None:
            raise ValueError(reason)
        out[name] = params.declarations[name].to_json(parsed)
    return Expr(op, MappingProxyType(out), inputs, pattern_cls=pattern_cls, driven=tuple(driven))


def swept(param: Param[Any], where: str, span: Range) -> tuple[Any, float]:
    """The value and route depth that make a signal of range `span` sweep
    `param`'s sweet range: the value where the signal's 0 lands, and the
    depth that spreads the signal's range over the sweet range. Raises
    TypeError for a param a route cannot move."""
    moved, reason = drive_range(param, where)
    if moved is None:
        raise TypeError(f"{reason}; route a signal to a part with signal.to(path, depth)")
    lo, hi = moved.sweet
    depth = (hi - lo) / (span[1] - span[0])
    return moved.modulate(lo, -span[0] * depth), depth


def signal_range(signal: Expr) -> Range:
    """The values signal builder `signal` gives (`SignalOp.range_of`)."""
    cls = OPS[signal.op]
    assert issubclass(cls, SignalOp)  # `Expr.signal` says so
    return cls.range_of([signal_range(source) for source in signal.inputs])


def pattern(spec: str | type, *args: Any, **params: Any) -> Expr:
    """A pattern node: `spec` a gallery name or a pattern file's spec, as
    `run` takes one (or the pattern's class), at `params`."""
    if isinstance(spec, type):
        cls, spec = spec, pattern_name(spec)
    else:
        from pewpew.load import resolve  # loads the gallery or a file only when a node needs one

        cls = resolve(spec).cls
    return _with_args(PATTERN, (), cls, list(args), params, {PATTERN: spec}, cls)


def _sources() -> dict[str, type[Op]]:
    """The ops a builder calls as functions, which read no node: the
    sources and the signal sources; `pattern` has its own."""
    return {op: cls for op, cls in OPS.items() if not cls.inputs and op != PATTERN}


def namespace() -> dict[str, Any]:
    """The names a builder chain may use: `look`, `layer`, `pattern` and
    each op that reads no node."""
    return {"look": look, "layer": layer, PATTERN: pattern,
            **{op: partial(_node, cls, None) for op, cls in _sources().items()}}


# ---- looks ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class Routed:
    """A signal builder routed to the knob at `path` by `depth`: what
    `signal.to(path, depth)` gives. Inside a builder, a route of a signal
    given as an arg has a path relative to its node."""

    signal: Expr
    path: str
    depth: float


@dataclass(frozen=True, slots=True, eq=False)
class LayerExpr:
    """A layer being written: its id, what it runs (a builder or a
    program), its mask, and its mix by name: what `layer(...)` gives."""

    id: str
    source: Expr | Program
    alpha: Expr | None
    mix: Mapping[str, Any]


def layer(lid: str, source: Expr | Program, *, alpha: Expr | None = None, **mix: Any) -> LayerExpr:
    """Layer `lid` running `source` (a builder or a program), masked by
    `alpha`, at its `mix` (opacity, blend, enabled): for `look(...)`.
    Raises ValueError for an id the address grammar refuses."""
    return LayerExpr(require_id(lid, "layer"), source, alpha, MappingProxyType(mix))


def look(
    *layers: LayerExpr,
    routes: Iterable[Routed] = (),
    seed: int = 0,
    master: float | None = None,
    fade: float | None = None,
    cycle: bool = False,
    front: Sequence[str] = (),
) -> Look:
    """The look of `layers`, bottom first, with `routes` and the routes of
    signals given as args, and the look's own fields (pewpew.compose.stack
    .Look; `fade` None is its default). Its signals are the ones its routes
    take, and the ones they read. Raises ValueError for a look that its
    programs, its signals, its routes or its own fields refuse, each
    problem by its path."""
    # The compose package imports this module, so it is imported here.
    from pewpew.compose.controls import layer_address, look_controls, signal_address
    from pewpew.compose.modulation import route_problems, signal_problems
    from pewpew.compose.stack import DEFAULT_FADE, Layer, Look, Route, order_signals
    from pewpew.load import resolve

    built: list[Layer] = []
    wires: list[Routed] = []
    patterns: dict[str, type] = {}
    for part in layers:
        if isinstance(part.source, Program):
            program, driven = part.source, []
        else:
            program, driven = part.source.built(part.alpha)
            patterns |= part.source.patterns() | (part.alpha.patterns() if part.alpha is not None else {})
        built.append(Layer(part.id, program, **part.mix))
        wires += (replace(wire, path=layer_address(part.id, wire.path)) for wire in driven)
    wires += routes
    order = post_order([wire.signal for wire in wires], lambda e: [*e.inputs, *(wire.signal for wire in e.driven)])
    sids = dict(zip(order, assign_ids([(id_base(e.op, e.args), e.pinned) for e in order])))
    wires += (replace(wire, path=signal_address(sids[e], wire.path)) for e in order for wire in e.driven)
    made = tuple(Route(sids[wire.signal], wire.path, wire.depth) for wire in wires)
    nodes, problems = order_signals(
        {sids[e]: Node(sids[e], e.op, e.args, tuple(sids[s] for s in e.inputs)) for e in order}, made)
    if problems:
        raise ValueError("; ".join(problems))
    result = Look(tuple(built), Graph(nodes) if nodes else None, made, seed, master,
                  DEFAULT_FADE if fade is None else fade, cycle, tuple(front))
    problems = signal_problems(result.signals, result.routes) or route_problems(
        result.routes, result.front, look_controls(result, lambda spec: patterns.get(spec) or resolve(spec).cls))
    if problems:
        raise ValueError("; ".join(problems))
    return result


def __getattr__(name: str) -> Callable[..., Expr]:
    """A source op as a function: `osc(8, 0.1)`."""
    sources = _sources()
    if name not in sources:
        known = sorted([*sources, PATTERN])
        raise AttributeError(f"module {__name__!r} has no {name!r}; {unknown('source', name, known, suggest=True)}")
    return partial(_node, sources[name], None)
