"""`ProgramPattern`: an effect program hosted in a normal `Renderer`.

A program runs as a `Pattern`, so the renderer's containment works for it
unchanged:

    from pewpew.fx.expr import noise, osc
    from pewpew.fx.host import ProgramPattern

    class Tide(ProgramPattern):
        program = osc(8, 0.1).kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember")

A look's layer runs its program the same way, through a class made from
the program (`ProgramPattern.of`).

Bind (`setup`): the program is checked against the map (`check`, with the
map's dimension), then each node gets its op and its knobs' values, its
op's `setup`, and the closures are built bottom up, once. Each frame,
`before_render` moves each op's phases and runs each op's `advance`, in
graph order, so `render` stays pure: it evaluates `out` (a scalar field
shows as grey) and the mask `alpha`, if any, at the map's points.

Each node's knobs are a `ParamSet` named by the node's address,
`<renderer name>.<nid>` (`layers.base.fold`), kept by node id for the
host's life: a rebind keeps them and each node's op, so a control holding
one keeps working. A node's buffers are the host's (`<nid>__<name>`), so
they are read-only in `render`.

Randomness: a node's key is its layer's seed and the CRC-32 of its
layer and node ids (`node_key`), so its draws and its noise are the same
in every process and do not change when another node or layer does.

The compositor sets `below` (the frame of the layers below) before the
layer advances, and reads `alpha` after it renders.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
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
    node_types,
    require_field,
)
from pewpew.fx.graph import Buildable, Graph, Program
from pewpew.fx.op import BindCtx, FrameCtx, Op, node_key, node_seed
from pewpew.fx.ops import OPS
from pewpew.fx.prims.vec import Center
from pewpew.fx.types import Coords
from pewpew.mapping import spanned
from pewpew.params import ParamSet
from pewpew.pattern import Pattern


@dataclass(slots=True)
class _BoundNode:
    """One bound node: its op, its key, whether its op defines `advance`,
    the values its knobs bind at (the program's literal, native), and once
    committed the set that holds its knobs."""

    op: Op
    key: int
    advances: bool
    values: dict[str, Any]
    params: ParamSet | None = None


class ProgramPattern(Pattern):
    """A pattern that runs an effect program (module docstring). A subclass
    sets `program` (a `Program` or a builder expression). `strict` checks
    that every node gives a float32 field (tests)."""

    program: ClassVar[Program | Buildable | None] = None
    strict: ClassVar[bool] = False
    _program: ClassVar[Program | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        source = cls.__dict__.get("program")
        if source is None:
            return
        cls._program = Program.of(source)  # a builder checks its program here

    @classmethod
    def of(cls, program: Program) -> type[ProgramPattern]:
        """A class that runs `program`: how a look's layer runs its
        program. A bind checks the program against the map and raises
        ValueError, naming each problem by its address, for one `check`
        refuses."""
        return type("Program", (cls,), {"program": program})

    def __init__(self) -> None:
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

    def snapshot(self) -> Program:
        """The program at its knobs' live values, as JSON args."""
        program, knobs = self.runs(), self.node_params
        nodes = []
        for node in program.graph:
            params = knobs.get(node.id)
            if params is not None:
                node = replace(node, args=params.snapshot_json())
            nodes.append(node)
        return replace(program, graph=Graph(tuple(nodes)))

    # ---- bind ----------------------------------------------------------------------

    def _bind(self, n: int, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray, seed: int,
              params: ParamSet | Mapping[str, Any], name: str | None = None) -> None:
        """`Pattern._bind`, then the nodes' knobs committed: only once the
        whole program bound, so a rebind whose program fails to bind leaves
        the running nodes' knobs as they were."""
        if name:
            self.owner = name
        super()._bind(n, x, y, z, index, seed, params, name)
        self._commit()

    def setup(self, n: int, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> None:
        program = self.runs()
        coords = Coords.of(x, y, z, index)
        lo, hi = _extent(x, y, z)
        dims = sum(spanned(b - a for a, b in zip(lo, hi)))
        problems = check(program, where=self.owner, dims=dims)
        if problems:
            raise Unrunnable("; ".join(problems))
        lid = self.owner.rpartition(".")[2]
        self._black = np.zeros((n, 3), dtype=np.float32)
        self._black.setflags(write=False)
        staged: dict[str, _BoundNode] = {}
        ops: dict[str, Op] = {}
        types = node_types(program)
        for node in program.graph:
            key = node_key(self.seed, lid, node.id)
            kept = self._nodes.get(node.id)  # a rebind keeps each node's op and knobs
            op = kept.op if kept is not None else OPS[node.op]()
            params = kept.params if kept is not None else None
            values = params.snapshot() if params is not None else ParamSet(OPS[node.op], node.args).snapshot()
            for name, value in values.items():
                setattr(op, name, value)  # `setup` sees the values the node runs at
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
            staged[node.id] = _BoundNode(op, key, type(op).advance is not Op.advance, values, params)
        self._staged = staged
        self._built = closures(program, ops, self.owner, strict=type(self).strict)
        self._coords = coords

    def _commit(self) -> None:
        """Bind each node's knobs to its op: its own set again (a rebind),
        or a new set."""
        for nid, node in self._staged.items():
            if node.params is None:
                node.params = ParamSet(type(node.op), node.values, name=f"{self.owner}.{nid}")
            node.params.apply(node.op)
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


def _extent(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[Center, Center]:
    """The lowest and highest point of the map on each axis, as Python floats."""
    if not len(x):
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    lx, ly, lz = (float(a.min()) for a in (x, y, z))
    hx, hy, hz = (float(a.max()) for a in (x, y, z))
    return (lx, ly, lz), (hx, hy, hz)
