"""Checking an effect program, and building its closures.

`check` is the one judge of a program, shared by the builder
(pewpew.fx.expr), the codec (pewpew.fx.codec) and the host
(pewpew.fx.host). It never raises: it returns every problem, each
prefixed by the address of the node it is about, worded to say how to
fix it:

- an op that does not exist (with a did-you-mean), or a signal op, which
  belongs in the look's signals (`check_signals` judges those);
- an arg the op does not declare, or a value its param refuses (in the
  params' own words);
- a node that reads the wrong number of nodes, or a type its port does
  not take (`hue` reads rgb; color a scalar with `palette` first);
- a node nothing reads;
- with `dims`, an op that a map of that dimension does not support, and
  what to use instead;
- with `resolve`, a pattern node's pattern and params, and the pattern
  rules of a program (ADR-022): inside a program a pattern renders at the
  program's points, so it must be a pixel-unit pattern, and a coord op may
  warp only what can be read at other points (a warpable pattern, not the
  frame below or the layer's last frame). A state op reads its input at
  the map's own points, so a coord op above it warps nothing below it.

`closures` builds a checked program's closures bottom up, once per bind.
A node read by more than one other shares one result per frame (a memo the
host resets each frame); every node's exception names the node.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np

from pewpew.classinfo import pattern_name
from pewpew.errors import Worded, blame, describe_exception, unknown
from pewpew.fx.graph import PATTERN, Graph, Node, Program
from pewpew.fx.op import Op, Resolve
from pewpew.fx.ops import OPS, labels
from pewpew.fx.types import ACCEPTS, Coords, Fn, Port, PortTy, Sig, Ty
from pewpew.params import ParamSet

# How to fix a port that got the wrong type, by (what it takes, what it got).
_ADVICE: dict[tuple[PortTy, Ty], str] = {
    (Ty.SCALAR, Ty.RGB): "it colors a scalar field; read a source such as osc or noise, not a color",
    (Ty.RGB, Ty.SCALAR): "color the field first, with palette",
}
_SIGNAL = "route it to a param instead"


class Unrunnable(Worded):
    """A program `check` refuses where it binds: its message is every
    problem, each naming its node."""


def is_pattern_program(program: Program) -> bool:
    """Whether `program` is one pattern node and no mask: a layer that runs
    its pattern directly, in the layer's own renderer."""
    return len(program.graph) == 1 and program.output.op == PATTERN and program.alpha is None


def check(
    program: Program,
    *,
    where: str = "",
    resolve: Resolve | None = None,
    dims: int | None = None,
    hosted: bool = False,
) -> list[str]:
    """Every problem with `program` (module docstring), each prefixed by
    its node's address `<where>.<nid>`. `resolve(spec)` gives a pattern
    node's class, or None for a name nothing offers. `hosted` says the
    program runs in a `ProgramPattern` even when it is one pattern node, so
    that node renders at the program's points too. Never raises."""
    at = (lambda nid: f"{where}.{nid}") if where else (lambda nid: nid)
    problems: list[str] = []
    types = node_types(program)
    direct = not hosted and is_pattern_program(program)
    for node in program.graph:
        cls = OPS.get(node.op)
        if cls is None:
            ops = field_ops()
            problems.append(f"{at(node.id)}: {unknown('op', node.op, ops, suggest=True, aliases=labels(ops))}")
            continue
        if cls.sig == Sig.SIGNAL:
            problems.append(f"{at(node.id)}: {node.op} is a signal, one number a frame, not a field; "
                            "put it in the look's signals and route it to a knob")
            continue
        problems.extend(_args(node, cls, at(node.id), resolve, hosted=not direct))
        problems.extend(_ports(node, cls, at(node.id), types))
        if dims is not None and max(dims, 1) not in cls.dims:
            problems.append(_dims(cls, at(node.id), max(dims, 1)))
    problems.extend(_ends(program, where, types))
    problems.extend(_unread(program, at))
    if not direct:
        problems.extend(_warps(program, at, resolve))
    return problems


def field_ops() -> list[str]:
    """The ops a layer's program may run, by name: every op but the signal ops."""
    return sorted(op for op, cls in OPS.items() if cls.sig != Sig.SIGNAL)


def signal_ops() -> list[str]:
    """The ops a look's signals may run, by name."""
    return sorted(op for op, cls in OPS.items() if cls.sig == Sig.SIGNAL)


def check_signals(graph: Graph, *, where: str = "signals") -> list[str]:
    """Every problem with a look's signal graph, each prefixed by its
    signal's address `<where>.<sid>`: an op that is not a signal op (with a
    did-you-mean), an arg its param refuses, or a signal that reads the
    wrong number of signals. Never raises."""
    problems: list[str] = []
    types = dict.fromkeys((node.id for node in graph), Ty.SIGNAL)
    for node in graph:
        at = f"{where}.{node.id}"
        cls = OPS.get(node.op)
        if cls is None:
            ops = signal_ops()
            problems.append(f"{at}: {unknown('op', node.op, ops, suggest=True, aliases=labels(ops))}")
        elif cls.sig != Sig.SIGNAL:
            problems.append(f"{at}: {node.op} is not a signal op; a look's signals run {', '.join(signal_ops())}, "
                            f"and {node.op} goes in a layer's program")
        else:
            problems += [*_args(node, cls, at, None, hosted=False), *_ports(node, cls, at, types, noun="signal")]
    return problems


def node_types(program: Program) -> dict[str, Ty]:
    """The type each node of `program` gives (`Op.gives`). A node of an
    unknown op or a signal op (refused in a program on its own), or one
    that reads the wrong number of nodes, has none, and a node that reads
    it takes it as a scalar."""
    types: dict[str, Ty] = {}
    for node in program.graph:
        cls = OPS.get(node.op)
        if cls is not None and cls.sig != Sig.SIGNAL and len(node.inputs) == len(cls.inputs):
            types[node.id] = cls.gives([types.get(source, Ty.SCALAR) for source in node.inputs])
    return types


def _args(node: Node, cls: type[Op], where: str, resolve: Resolve | None, *, hosted: bool) -> list[str]:
    """Why each of `node`'s args is refused."""
    if node.op == PATTERN:
        spec = node.args.get(PATTERN)
        if not isinstance(spec, str) or not spec:
            return [f"{where}: args: {PATTERN!r} is a pattern name"]
        try:
            knobs = cls.knob_class(node.args, resolve)
        except Exception as exc:  # noqa: BLE001  a pattern file that does not load
            return [f"{where}: pattern {spec!r} does not load: {describe_exception(exc)}"]
        if knobs is None:
            return [] if resolve is None else [f"{where}: unknown pattern {spec!r}"]
        if hosted and (reason := _hosted(spec, knobs)) is not None:
            return [f"{where}: {reason}"]
    else:
        knobs = cls.knob_class(node.args, resolve)
        assert knobs is not None  # an op's knobs are its own params
    values = cls.knob_values(node.args)
    out: list[str] = []
    if node.op == PATTERN:
        from pewpew.fx.host import ProgramPattern, split_starts  # the host imports this module

        if issubclass(knobs, ProgramPattern):
            values, starts = split_starts(values)
            out += _starts(starts, knobs.knob_classes(), where)
    return out + _knobs(values, ParamSet(knobs, name=where), where)


def _knobs(values: Mapping[str, Any], params: ParamSet, where: str) -> list[str]:
    """Why each of `values` cannot be a knob of `params`, at `where`."""
    out = []
    for name, value in values.items():
        if name not in params.declarations:
            out.append(f"{where}: {unknown('param', name, params.declarations, suggest=True)}")
        elif (reason := params.check(name, value)) is not None:
            out.append(reason)
    return out


def _starts(starts: Mapping[str, Mapping[str, Any]], classes: Mapping[str, type], where: str) -> list[str]:
    """Why each start of a pattern node at `where` that runs a program file
    (`<nid>.<arg>`, pewpew.fx.host) is refused, each knob named by its
    address, `<layer>.<nid>.<arg>`, as the stack names it."""
    layer = where.rpartition(".")[0]
    out = []
    for nid, values in starts.items():
        if nid not in classes:
            out.append(f"{where}: {unknown('node', nid, classes, suggest=True)}")
            continue
        at = f"{layer}.{nid}" if layer else nid
        out += _knobs(values, ParamSet(classes[nid], name=at), at)
    return out



def _hosted(spec: str, cls: type) -> str | None:
    """Why pattern `spec` (class `cls`) cannot run inside a program, or None."""
    from pewpew.fx.host import ProgramPattern  # the host imports this module

    if issubclass(cls, ProgramPattern):
        return f"pattern {spec!r} is a program; run it on a layer of its own"
    if getattr(cls, "units", "pixel") != "pixel":
        return (
            f"pattern {spec!r} renders once per fixture, not at the program's points; "
            "run it on a layer of its own"
        )
    return None


def _ports(node: Node, cls: type[Op], where: str, types: Mapping[str, Ty], *, noun: str = "node") -> list[str]:
    """Why `node` cannot read the nodes it reads, each a `noun`."""
    if len(node.inputs) != len(cls.inputs):
        names = ", ".join(repr(port.name) for port in cls.inputs) or "none"
        return [f"{where}: {cls.op} reads {len(cls.inputs)} {noun}(s) ({names}), got {len(node.inputs)}"]
    out = []
    for port, source in zip(cls.inputs, node.inputs):
        got = types.get(source)
        if got is not None and got not in ACCEPTS[port.ty]:
            out.append(_wrong_type(where, cls, port, source, got))
    return out


def _wrong_type(where: str, cls: type[Op], port: Port, source: str, got: Ty) -> str:
    advice = _SIGNAL if got == Ty.SIGNAL else _ADVICE.get((port.ty, got), "")
    tail = f" — {advice}" if advice else ""
    return f"{where}: {cls.op} takes {port.wording} on {port.name!r}; {source!r} is {got}{tail}"


def _dims(cls: type[Op], where: str, dims: int) -> str:
    takes = " or ".join(str(d) for d in sorted(cls.dims))
    fix = f"; {cls.fix}" if cls.fix else ""
    return f"{where}: {cls.op} needs a map of {takes} dimensions, and this map has {dims}{fix}"


def _ends(program: Program, where: str, types: Mapping[str, Ty]) -> list[str]:
    """Why the program's out or alpha node cannot be one, each prefixed by
    the layer's address `where`, since `out` and `alpha` are its keys."""
    at = f"{where}: " if where else ""
    out = []
    if types.get(program.out) == Ty.SIGNAL:
        out.append(f"{at}'out' is a signal; a layer shows a field, so end with a source or a color op")
    if program.alpha is not None and types.get(program.alpha) not in (None, Ty.SCALAR):
        got = types[program.alpha]
        out.append(f"{at}'alpha' takes a scalar field, and {program.alpha!r} gives {got}; mask with a source "
                   "such as shape or noise, before any palette")
    return out


def _unread(program: Program, at: Callable[[str], str]) -> list[str]:
    """A node that neither `out`, `alpha` nor any node they read reads."""
    reached = upstream(program, program.ends)
    return [
        f"{at(node.id)}: nothing reads node {node.id!r}; read it from another node, or remove it"
        for node in program.graph if node.id not in reached
    ]


def upstream(program: Program, roots: Sequence[str], past: Callable[[Node], bool] = lambda node: True) -> set[str]:
    """The ids of `roots` and every node they read, directly or not; the
    walk goes on past a node only where `past(node)`."""
    seen: set[str] = set()
    stack = [nid for nid in roots if nid in program.graph]
    while stack:
        nid = stack.pop()
        if nid not in seen:
            seen.add(nid)
            node = program.graph[nid]
            if past(node):
                stack.extend(source for source in node.inputs if source in program.graph)
    return seen


def _warps(program: Program, at: Callable[[str], str], resolve: Resolve | None) -> list[str]:
    """A coord op, or a modulate's `in`, above a node that cannot be read
    at other points. A state op reads its inputs at the map's own points
    before render, so a warp above it moves only where its state is read:
    the walk stops there."""
    out = []
    for node in program.graph:
        cls = OPS.get(node.op)
        if cls is None or cls.sig not in (Sig.COORD, Sig.MODULATE) or not node.inputs:
            continue
        for nid in sorted(upstream(program, node.inputs[:1], _warps_through)):
            reader = program.graph[nid]
            source = OPS.get(reader.op)
            if source is None or _readable(source, reader.args, resolve):
                continue
            if reader.op == PATTERN:
                why = (f"pattern {reader.args.get(PATTERN)!r} is not warpable; apply {node.op} to another source, "
                       f"or run {nid!r} on a layer of its own")
            else:
                why = f"{reader.op} has a value only at the map's own points; apply {node.op} to a source instead"
            out.append(f"{at(node.id)}: {node.op} warps what {nid!r} reads, and {why}")
    return out


def _warps_through(node: Node) -> bool:
    """Whether a warp above `node` moves where `node` reads its inputs:
    not for a state op (`_warps`)."""
    cls = OPS.get(node.op)
    return cls is None or cls.sig != Sig.STATE


def _readable(cls: type[Op], args: Mapping[str, Any], resolve: Resolve | None) -> bool:
    try:
        return cls.warps(args, resolve)
    except Exception:  # noqa: BLE001  a pattern that does not load is reported by _args
        return True


# ---- closures ------------------------------------------------------------------


class Memo:
    """A node's closure that computes once per set of coordinates: the
    second read of a node read twice at the same points reuses the first.
    `reset` before each frame."""

    __slots__ = ("c", "fn", "value")

    def __init__(self, fn: Fn) -> None:
        self.fn = fn
        self.c: Coords | None = None
        self.value: np.ndarray | None = None

    def __call__(self, c: Coords) -> np.ndarray:
        if c is not self.c or self.value is None:
            self.value, self.c = self.fn(c), c
        return self.value

    def reset(self) -> None:
        self.c = self.value = None


@dataclass(frozen=True, slots=True)
class Built:
    """A program's closures: each node's by id, what `out` and `alpha` (or
    None) give, and the memos to reset before each frame."""

    fns: Mapping[str, Fn]
    out: Fn
    alpha: Fn | None
    memos: tuple[Memo, ...]

    def inputs(self, node: Node) -> list[Fn]:
        """The closures of the nodes `node` reads, in port order."""
        return [self.fns[source] for source in node.inputs]


def closures(program: Program, ops: Mapping[str, Op], where: str, *, strict: bool = False) -> Built:
    """`program`'s closures over its bound `ops` (by node id), bottom up.
    With `strict`, every node's output is checked to be a float32 field of
    the right shape."""
    reads = program.reads()
    fns: dict[str, Fn] = {}
    memos: list[Memo] = []
    for node in program.graph:
        path = f"{where}.{node.id}"
        try:
            built = ops[node.id].build([fns[source] for source in node.inputs])
        except Exception as exc:
            blame_node(exc, path, node.op)
            raise
        fn = _guarded(built, path, node.op, strict)
        if reads[node.id] > 1:
            fn = Memo(fn)
            memos.append(fn)
        fns[node.id] = fn
    return Built(MappingProxyType(fns), fns[program.out], fns[program.alpha] if program.alpha else None, tuple(memos))


def blame_node(exc: BaseException, path: str, op: str) -> None:
    """Mark `exc` as raised by node `path` of op `op` (pewpew.errors.blame)."""
    blame(exc, path, f"in node {path} ({op})")


def _guarded(fn: Fn, path: str, op: str, strict: bool) -> Fn:
    """`fn`, its exceptions naming node `path` (`blame_node`)."""

    def node(c: Coords) -> np.ndarray:
        try:
            value = fn(c)
            if strict:
                require_field(value, len(c.index))
        except Exception as exc:
            blame_node(exc, path, op)
            raise
        return value

    return node


def require_field(value: object, n: int, *, mask: bool = False) -> None:
    """Raise TypeError unless `value` is an (n,) or (n, 3) float32 array:
    only (n,) for a `mask`, one weight a point."""
    shapes = ((n,),) if mask else ((n,), (n, 3))
    if not isinstance(value, np.ndarray) or value.dtype != np.float32 or value.shape not in shapes:
        got = f"{value.dtype} {value.shape}" if isinstance(value, np.ndarray) else type(value).__name__
        want = f"a mask is an ({n},)" if mask else f"a node gives an ({n},) or ({n}, 3)"
        raise TypeError(f"{want} float32 field, got {got}")


def knob_class(node: Node, resolve: Resolve | None) -> type:
    """The class whose params `node`'s knobs are. Raises ValueError when it
    cannot be known (a pattern nothing resolves)."""
    found = OPS[node.op].knob_class(node.args, resolve)
    if found is None:
        raise ValueError(f"no pattern {node.args.get(PATTERN)!r} to run")
    return found


def label_of(node: Node, resolve: Resolve | None) -> str:
    """What a page shows for `node`: its pattern's name for a pattern node,
    else its op's label."""
    if node.op == PATTERN:
        found = OPS[PATTERN].knob_class(node.args, resolve)
        return pattern_name(found) if found is not None else str(node.args.get(PATTERN))
    cls = OPS.get(node.op)
    return cls.label if cls is not None else node.op
