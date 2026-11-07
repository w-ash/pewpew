"""`BoundProgram`: an effect program bound to a map, which a `Renderer`
runs (pewpew.render). Each layer of a stack runs one:

    from pewpew.fx.bound_program import BoundProgram
    from pewpew.fx.expr import noise, osc
    from pewpew.fx.graph import Program
    from pewpew.mapping import grid
    from pewpew.render import Renderer

    program = Program.of(osc(8, 0.1).kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember"))
    renderer = Renderer(BoundProgram(program, "layers.base"), grid(16, 16))

Bind (`bind`): the program is checked against the map (`check`, with the
map's dimension), then each node gets its op and its knobs' values, its
op's `setup`, and the closures are built bottom up, once. Each frame,
`advance` moves each op's phases and runs each op's `advance`, in graph
order, so `render` stays pure: it evaluates `out` (a scalar field shows
as grey) and the mask `alpha`, if any, at the map's points.

Each node's knobs are a `ParamSet` named by the node's address,
`<name>.<nid>` (`layers.base.fold`), kept by node id for the bound
program's life: a rebind keeps them and each node's op, so a control
holding one keeps working. A node's buffers are the bind's `Buffers`
(`<nid>.<name>`), so they are read-only in `render`, and `pixels`, the
last frame, is what `prev()` reads.

Randomness: a node's key is the bind's seed and the CRC-32 of its layer
and node ids (`node_key`), so its draws and its noise are the same in
every process and do not change when another node or layer does.

The compositor sets `below` (the frame of the layers below) before the
layer advances, and reads `alpha` after it renders.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import partial
from typing import Any, ClassVar

import numpy as np

from pewpew.features import FeatureFrame
from pewpew.fx.buffers import Buffers
from pewpew.fx.compile import (
    Built,
    Unrunnable,
    blame_node,
    check,
    closures,
    node_types,
    require_field,
)
from pewpew.fx.graph import Graph, Program
from pewpew.fx.op import BindCtx, FrameCtx, Op, node_key, node_seed
from pewpew.fx.ops import OPS
from pewpew.fx.prims.vec import Center
from pewpew.fx.types import Coords
from pewpew.mapping import spanned
from pewpew.params import ParamSet


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


class BoundProgram:
    """`program` bound to a map (module docstring). `name` is its address
    (`layers.<lid>`), which its errors, refusals and node knobs name; its
    last part is the layer id in each node's key."""

    # Whether every node is checked to give a float32 field (tests).
    strict: ClassVar[bool] = False

    def __init__(self, program: Program, name: str) -> None:
        self.program = program
        self.name = name
        self.tick = 0
        # The frame of the layers below, set by the compositor before each frame.
        self.below: np.ndarray | None = None
        # The mask the last frame gave, or None.
        self.alpha: np.ndarray | None = None
        self.buffers = Buffers(0)
        self._nodes: dict[str, _BoundNode] = {}
        self._built: Built | None = None
        self._coords: Coords | None = None
        self._black = np.zeros((0, 3), dtype=np.float32)

    @property
    def node_params(self) -> Mapping[str, ParamSet]:
        """Each node's knobs, by node id, in graph order."""
        return {nid: node.params for nid, node in self._nodes.items() if node.params is not None}

    def snapshot(self) -> Program:
        """The program at its knobs' live values, as JSON args."""
        knobs = self.node_params
        nodes = []
        for node in self.program.graph:
            params = knobs.get(node.id)
            if params is not None:
                node = replace(node, args=params.snapshot_json())
            nodes.append(node)
        return replace(self.program, graph=Graph(tuple(nodes)))

    # ---- bind ----------------------------------------------------------------------

    def bind(self, coords: Coords, seed: int) -> None:
        """Bind the program to the points `coords`, its nodes keyed from
        `seed`: new buffers at their fill, each op's `setup`, the closures.
        The nodes' knobs change only once the whole program binds, so a
        rebind that raises leaves the running nodes' knobs as they were.
        Raises Unrunnable for a program `check` refuses on this map, and
        what an op's `setup` raises, naming its node."""
        program, n = self.program, len(coords.index)
        lo, hi = _extent(coords)
        dims = sum(spanned(b - a for a, b in zip(lo, hi)))
        if problems := check(program, where=self.name, dims=dims):
            raise Unrunnable("; ".join(problems))
        lid = self.name.rpartition(".")[2]
        self.buffers = buffers = Buffers(n)
        self._black = np.zeros((n, 3), dtype=np.float32)
        self._black.setflags(write=False)
        staged: dict[str, _BoundNode] = {}
        ops: dict[str, Op] = {}
        types = node_types(program)
        for node in program.graph:
            key = node_key(seed, lid, node.id)
            kept = self._nodes.get(node.id)  # a rebind keeps each node's op and knobs
            op = kept.op if kept is not None else OPS[node.op]()
            params = kept.params if kept is not None else None
            values = params.snapshot() if params is not None else ParamSet(OPS[node.op], node.args).snapshot()
            for name, value in values.items():
                setattr(op, name, value)  # `setup` sees the values the node runs at
            path = f"{self.name}.{node.id}"
            ctx = BindCtx(
                path=path, values=values, coords=coords, lo=lo, hi=hi, seed=node_seed(key), key=key,
                buffer=partial(_node_buffer, buffers, node.id), below=self._below, prev=self._prev,
                gives=types[node.id],
            )
            try:
                op.setup(ctx)
            except Exception as exc:
                blame_node(exc, path, node.op)
                raise
            ops[node.id] = op
            staged[node.id] = _BoundNode(op, key, type(op).advance is not Op.advance, values, params)
        self._built = closures(program, ops, self.name, strict=type(self).strict)
        self._coords = coords
        for nid, node in staged.items():
            if node.params is None:
                node.params = ParamSet(type(node.op), node.values, name=f"{self.name}.{nid}")
            node.params.apply(node.op)
        self._nodes = staged

    def _below(self) -> np.ndarray:
        return self._black if self.below is None else self.below

    def _prev(self) -> np.ndarray:
        return self.buffers.pixels

    # ---- frames --------------------------------------------------------------------

    def advance(self, dt: float, features: FeatureFrame) -> None:
        """Move the program on by `dt` seconds: each op's phases, then each
        stateful op's `advance`, in graph order."""
        self.tick += 1
        built = self._built
        assert built is not None
        for memo in built.memos:
            memo.reset()  # what a node's advance reads is this frame's
        for node in self.program.graph:
            bound = self._nodes[node.id]
            bound.op.step(dt)
            if not bound.advances:
                continue
            try:
                bound.op.advance(FrameCtx(dt, features, self.tick, bound.key), built.inputs(node))
            except Exception as exc:
                blame_node(exc, f"{self.name}.{node.id}", node.op)
                raise

    def render(self) -> np.ndarray:
        """This frame at the bound points: `out` as (n, 3), a scalar as
        grey, with the mask in `alpha`. Reads state, never writes it."""
        built, coords = self._built, self._coords
        assert built is not None and coords is not None
        for memo in built.memos:
            memo.reset()
        out = built.out(coords)
        alpha = built.alpha(coords) if built.alpha is not None else None
        if alpha is not None:
            # The compositor blends the mask outside the renderer's containment.
            require_field(alpha, len(coords.index), mask=True)
        self.alpha = None if alpha is None else np.clip(alpha, 0.0, 1.0)
        if out.ndim == 1:
            return np.repeat(out[:, None], 3, axis=1)
        return out if out.flags.writeable else out.copy()


def _node_buffer(buffers: Buffers, nid: str, name: str, shape: int | tuple[int, ...], dtype: Any = np.float32,
                 fill: float = 0.0) -> np.ndarray:
    """`BindCtx.buffer` for node `nid`: an array of `buffers` named `<nid>.<name>`."""
    return buffers.declare(f"{nid}.{name}", shape, dtype, fill)


def _extent(coords: Coords) -> tuple[Center, Center]:
    """The lowest and highest point of the map on each axis, as Python floats."""
    if not len(coords.index):
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    lx, ly, lz = (float(a.min()) for a in coords.xyz)
    hx, hy, hz = (float(a.max()) for a in coords.xyz)
    return (lx, ly, lz), (hx, hy, hz)
