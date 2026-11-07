"""`ProgramPattern`: an effect program hosted in a normal `Renderer`.

A program is a `Pattern`, so loading, hot reload, `run file.py`, the
goldens and the renderer's containment work for it unchanged:

    from pewpew.fx.expr import noise, osc
    from pewpew.fx.host import ProgramPattern

    class Tide(ProgramPattern):
        program = osc(8, 0.1).kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember")

A look's layer that runs a program of more than one node runs it the same
way, through a class made from the program (`ProgramPattern.of`).

Bind (`setup`): the program is checked against the map (`check`, with the
map's dimension), then each node gets its op and its knobs' values, its
op's `setup`, and the closures are built bottom up, once. Each frame,
`before_render` moves each op's phases and runs each op's `advance`, in
graph order, so `render` stays pure: it evaluates `out` (a scalar field
shows as grey) and the mask `alpha`, if any, at the map's points.

Each node's knobs are a `ParamSet` named by the node's address,
`<renderer name>.<nid>` (`layers.base.fold`), kept by node id for the
host's life: a rebind keeps them, and a hot reload hands each on to the
same node of the new program (ADR-022), so a control holding one keeps
working. A knob takes the new program's literal unless the operator moved
it from the old program's literal, which it keeps if the new declaration
takes it. A node's buffers are the host's (`<nid>__<name>`), so they are
read-only in `render` and carried across a hot reload by name and shape,
and a node's op state (its phases, a pattern node's pattern) is handed on
to the same node with the same op.

Randomness: a node's key is its layer's seed and the CRC-32 of its
layer and node ids (`node_key`), so its draws and its noise are the same
in every process and do not change when another node or layer does.

The compositor sets `below` (the frame of the layers below) before the
layer advances, and reads `alpha` after it renders.

A look runs a pattern file whose class is a `ProgramPattern` as a layer
of one pattern node (`run tide.py`, a pick of it), its knobs its
program's nodes', at `layers.<layer>.<nid>.<arg>`. The pattern node keeps
the file link, so the file's literals stay its content; a knob a look
moves from its literal is the node's arg `<nid>.<arg>` (`starts`), which
the host starts the node at, as if the operator had moved it, and
`moved` gives back.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import partial
from typing import Any, ClassVar

import numpy as np

from pewpew.classinfo import pattern_name
from pewpew.features import FeatureFrame
from pewpew.fx.compile import (
    Built,
    Unrunnable,
    blame_node,
    check,
    closures,
    knob_class,
    node_types,
    require_field,
)
from pewpew.fx.expr import Expr
from pewpew.fx.graph import Buildable, Graph, Program
from pewpew.fx.op import BindCtx, FrameCtx, Op, node_key, node_seed
from pewpew.fx.ops import OPS
from pewpew.fx.prims.vec import Center
from pewpew.fx.types import Coords
from pewpew.mapping import spanned
from pewpew.params import ParamSet, declared_params
from pewpew.pattern import Inheritance, Pattern


@dataclass(slots=True)
class _BoundNode:
    """One bound node: its op and the op's name, the values its knobs
    started from (the program's literal, native), its key, whether its op
    defines `advance`, and once committed the set that holds its knobs and
    the values they bound at."""

    op: Op
    op_name: str
    literal: dict[str, Any]
    key: int
    advances: bool
    params: ParamSet | None = None
    values: dict[str, Any] = field(default_factory=dict)


class ProgramPattern(Pattern):
    """A pattern that runs an effect program (module docstring). A subclass
    sets `program` (a `Program` or a builder expression) and, for its
    pattern nodes, `patterns` (classes by spec); a spec not in `patterns`
    resolves as `run` resolves a pattern (pewpew.load.resolve). `strict`
    checks that every node gives a float32 field (tests)."""

    program: ClassVar[Program | Buildable | None] = None
    patterns: ClassVar[Mapping[str, type]] = {}
    strict: ClassVar[bool] = False
    _program: ClassVar[Program | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        source = cls.__dict__.get("program")
        if source is None:
            return
        cls._program = Program.of(source)  # a builder checks its program here
        if isinstance(source, Expr):
            cls.patterns = {**cls.patterns, **source.patterns()}

    @classmethod
    def of(cls, program: Program, patterns: Mapping[str, type] | None = None) -> type[ProgramPattern]:
        """A class that runs `program`, its pattern nodes' classes in
        `patterns` by spec: how a look's layer runs its program. A bind
        checks the program against the map and raises ValueError, naming
        each problem by its address, for one `check` refuses."""
        return type("Program", (cls,), {"program": program, "patterns": dict(patterns or {})})

    @classmethod
    def resolve(cls, spec: str) -> type | None:
        """The class pattern spec `spec` runs: from `patterns`, else
        resolved once as `run` resolves it and kept in `patterns`."""
        found = cls.patterns.get(spec)
        if found is None:
            from pewpew.load import resolve  # loads the gallery or a file only when a node needs one

            found = resolve(spec).cls
            cls.patterns = {**cls.patterns, spec: found}
        return found

    @classmethod
    def knob_classes(cls) -> dict[str, type]:
        """The class of each node's knobs, by node id, in graph order: what
        a pattern node that runs this class takes as `<nid>.<arg>`."""
        return {node.id: knob_class(node, cls.resolve) for node in cls.runs().graph}

    def __init__(self, starts: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        """`starts`: by node id, the values (native or JSON) a node's knobs
        start at in place of the program's literals, as moved knobs."""
        self._starts = {nid: dict(values) for nid, values in (starts or {}).items()}
        self.tick = 0
        # The frame of the layers below, set by the compositor before each frame.
        self.below: np.ndarray | None = None
        # The mask the last frame gave, or None.
        self.alpha: np.ndarray | None = None
        self._nodes: dict[str, _BoundNode] = {}
        self._staged: dict[str, _BoundNode] = {}
        self._built: Built | None = None
        self._coords: Coords | None = None
        self._black: np.ndarray | None = None
        self.owner = pattern_name(type(self))

    @classmethod
    def runs(cls) -> Program:
        """The program this class runs. Raises TypeError for a class that
        sets none."""
        if cls._program is None:
            raise TypeError(f"{cls.__name__} sets no `program`")
        return cls._program

    @property
    def node_params(self) -> Mapping[str, ParamSet]:
        """Each node's knobs, by node id, in graph order."""
        return {nid: node.params for nid, node in self._nodes.items() if node.params is not None}

    def moved(self) -> dict[str, Any]:
        """Each knob whose live value is not its program's literal, as JSON
        by `<nid>.<arg>`: what a pattern node that runs this class holds
        (module docstring)."""
        out: dict[str, Any] = {}
        for nid, node in self._nodes.items():
            if node.params is None:
                continue
            live, shown = node.params.snapshot(), node.params.snapshot_json()
            out |= {f"{nid}.{name}": shown[name] for name, value in live.items() if value != node.literal.get(name)}
        return out

    def snapshot(self) -> Program:
        """The program at its knobs' live values, as JSON args."""
        program, knobs = self.runs(), self.node_params
        nodes = []
        for node in program.graph:
            params = knobs.get(node.id)
            if params is not None:
                fixed = {k: v for k, v in node.args.items() if k not in OPS[node.op].knob_values(node.args)}
                node = replace(node, args={**fixed, **params.snapshot_json()})
            nodes.append(node)
        return replace(program, graph=Graph(tuple(nodes)))

    # ---- bind ----------------------------------------------------------------------

    def _bind(self, n: int, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray, seed: int,
              params: ParamSet | Mapping[str, Any], inherit: Inheritance | None, name: str | None = None) -> None:
        """`Pattern._bind`, then the nodes' knobs committed: only once the
        whole program bound, so a hot reload whose program fails to bind
        leaves the running nodes' knobs as they were."""
        if name:
            self.owner = name
        super()._bind(n, x, y, z, index, seed, params, inherit, name)
        self._commit()

    def setup(self, n: int, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> None:
        program = self.runs()
        coords = Coords.of(x, y, z, index)
        lo, hi = _extent(x, y, z)
        dims = sum(spanned(b - a for a, b in zip(lo, hi)))
        problems = check(program, where=self.owner, resolve=self.resolve, dims=dims, hosted=True)
        if problems:
            raise Unrunnable("; ".join(problems))
        old = self._inherit.old if self._inherit is not None else None
        handed = old._nodes if isinstance(old, ProgramPattern) else {}
        lid = self.owner.rpartition(".")[2]
        self._black = np.zeros((n, 3), dtype=np.float32)
        self._black.setflags(write=False)
        staged: dict[str, _BoundNode] = {}
        ops: dict[str, Op] = {}
        types = node_types(program)
        for node in program.graph:
            key = node_key(self.seed, lid, node.id)
            cls = OPS[node.op]
            kept = self._nodes.get(node.id) if not handed else None  # a rebind keeps its ops
            prior = handed.get(node.id)
            before = kept or prior
            op = kept.op if kept is not None and kept.op_name == node.op else cls.make(node.args, self.resolve)
            if prior is not None and prior.op_name == node.op:
                op.adopt(prior.op)
            knobs = knob_class(node, self.resolve)
            literal = ParamSet(knobs, cls.knob_values(node.args)).snapshot()
            values = _values(literal, before, type(op.target))
            if before is None and node.id in self._starts:  # a look's moved knobs, at the first bind
                started = {**literal, **self._starts[node.id]}
                values |= ParamSet(knobs, started, name=f"{self.owner}.{node.id}").snapshot()
            for name, value in values.items():
                setattr(op.target, name, value)  # `setup` sees the values the node runs at
            path = f"{self.owner}.{node.id}"
            ctx = BindCtx(
                path=path, values=values, coords=coords, lo=lo, hi=hi, seed=node_seed(key), key=key,
                buffer=partial(self._node_buffer, node.id), below=self._below, prev=self._prev,
                gives=types[node.id],
            )
            try:
                op.setup(ctx)
            except Exception as exc:
                blame_node(exc, path, node.op)
                raise
            ops[node.id] = op
            params = before.params if before is not None else None
            advances = type(op).advance is not Op.advance
            staged[node.id] = _BoundNode(op, node.op, literal, key, advances, params, values)
        self._staged = staged
        self._built = closures(program, ops, self.owner, strict=type(self).strict)
        self._coords = coords

    def _commit(self) -> None:
        """Bind each node's knobs to its op: its own set again (a rebind),
        the set the replaced program's node held (a hot reload), or a new
        set."""
        for nid, node in self._staged.items():
            target, path = node.op.target, f"{self.owner}.{nid}"
            if node.params is None:
                node.params = ParamSet(type(target), node.values, name=path)
                node.params.apply(target)
            elif node.params.bound is not None and node.params.bound.target is target:
                node.params.apply(target)
            else:
                node.params.redeclare(target, node.values)
        self._nodes, self._staged = self._staged, {}

    def _node_buffer(self, nid: str, name: str, shape: int | tuple[int, ...], dtype: Any = np.float32,
                     fill: float = 0.0) -> np.ndarray:
        return self.buffer(f"{nid}__{name}", shape, dtype, fill)

    def _below(self) -> np.ndarray:
        below = self.below
        if below is None:
            assert self._black is not None
            return self._black
        return below

    def _prev(self) -> np.ndarray:
        return self.pixels

    # ---- frames --------------------------------------------------------------------

    def before_render(self, dt: float, features: FeatureFrame) -> None:
        self.tick += 1
        built = self._built
        assert built is not None
        for memo in built.memos:
            memo.reset()  # what a node's advance reads is this frame's
        for node in self.runs().graph:
            bound = self._nodes[node.id]
            bound.op.step(dt)
            if not bound.advances:
                continue
            try:
                bound.op.advance(FrameCtx(dt, features, self.tick, bound.key), built.inputs(node))
            except Exception as exc:
                blame_node(exc, f"{self.owner}.{node.id}", node.op)
                raise

    def render(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> np.ndarray:
        built, coords = self._built, self._coords
        assert built is not None and coords is not None
        if x is not coords.x:
            coords = Coords.of(x, y, z, index)
        for memo in built.memos:
            memo.reset()
        out = built.out(coords)
        alpha = built.alpha(coords) if built.alpha is not None else None
        if alpha is not None:
            require_field(alpha, len(x), mask=True)  # the compositor blends it outside the renderer's containment
        self.alpha = None if alpha is None else np.clip(alpha, 0.0, 1.0)
        if out.ndim == 1:
            return np.repeat(out[:, None], 3, axis=1)
        return out if out.flags.writeable else out.copy()


def split_starts(args: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """A pattern node's knob values (its args but `pattern`) for a
    `ProgramPattern` class, split into the class's own (`speed`) and, by
    node id, its program's nodes' (`waves.freq`; module docstring)."""
    own: dict[str, Any] = {}
    starts: dict[str, dict[str, Any]] = {}
    for key, value in args.items():
        nid, dot, arg = key.partition(".")
        if dot:
            starts.setdefault(nid, {})[arg] = value
        else:
            own[key] = value
    return own, starts


def _extent(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[Center, Center]:
    """The lowest and highest point of the map on each axis, as Python floats."""
    if not len(x):
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    lx, ly, lz = (float(a.min()) for a in (x, y, z))
    hx, hy, hz = (float(a.max()) for a in (x, y, z))
    return (lx, ly, lz), (hx, hy, hz)


def _values(literal: Mapping[str, Any], before: _BoundNode | None, cls: type) -> dict[str, Any]:
    """The values a node's knobs start at: the program's `literal`, except
    a knob the operator moved from the literal of the node it replaces
    (`before`), which keeps its live value where `cls` still takes it."""
    if before is None or before.params is None:
        return dict(literal)
    live = before.params.snapshot()
    declared = declared_params(cls)
    out = dict(literal)
    for name, value in live.items():
        if name in out and value != before.literal.get(name, value) and declared[name].fit(value) is not None:
            out[name] = value
    return out
