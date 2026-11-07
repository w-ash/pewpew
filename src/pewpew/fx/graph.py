"""Effect programs as values: nodes, the graph they form, and the program
a layer runs.

A `Node` is one op with its args (JSON values) and the ids of the nodes it
reads. A `Graph` holds its nodes in topological order: each node comes
after every node it reads, so a cycle cannot be written down, and the order
of evaluation follows from the value alone. Feedback is never a cycle: it
comes from ops that read a layer's last frame. A `Program` names the node
whose output the layer shows (`out`) and, optionally, the node whose output
masks it (`alpha`).

Ids never change once given: a knob's address,
`layers.<layer>.<node>.<arg>`, names it for a look's whole life. A node id
cannot be one of the words a layer's own address uses (`RESERVED`).

These are values only; evaluating them is the ops' work (pewpew.fx.op,
pewpew.fx.host), and pewpew.fx.codec is their JSON form. A pattern node
has op `pattern` and names its pattern by its `pattern` arg.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import count
from types import MappingProxyType
from typing import Any, Protocol, TypeVar

# A node, layer or signal id: short, lowercase, and safe in a dotted address.
ID = re.compile(r"[a-z][a-z0-9_]{0,23}")
# The words after `layers.<layer>.` that are not node ids: a layer's mix
# knobs and the keys of a layer in a looks file.
RESERVED = frozenset({"opacity", "blend", "enabled", "nodes", "out", "alpha"})
# The heads of an address, which no layer is named: a look's signals draw
# their random streams as a layer named `signals` would (pewpew.compose.modulation).
HEADS = frozenset({"layers", "signals"})
PATTERN = "pattern"  # a pattern node's op, and the arg that names its pattern

T = TypeVar("T")


def check_id(value: object, noun: str = "node") -> str | None:
    """Why `value` cannot be the id of a `noun` (node, layer, signal), or
    None. A node's and a signal's id have reserved words, as a signal is a
    node of the look's signal graph, and a layer's id is never an
    address's head (`HEADS`). Never raises."""
    if not isinstance(value, str) or not ID.fullmatch(value):
        return (
            f"bad {noun} id {value!r}: a lowercase letter, then up to 23 lowercase letters, digits or '_'"
        )
    if noun in ("node", "signal") and value in RESERVED:
        return (f"bad {noun} id {value!r}: {', '.join(sorted(RESERVED))} are reserved for a layer's own keys; "
                f"name the {noun} for its role, such as 'mix'")
    if noun == "layer" and value in HEADS:
        return f"bad layer id {value!r}: {' and '.join(sorted(HEADS))} are reserved, as the heads of an address"
    return None


def as_id(name: str) -> str:
    """`name` (a pattern's name) made into a node id: lowercased, any other
    character as '_', a leading 'p' when it does not start with a letter,
    at most 24 characters, and '_' after a reserved word."""
    text = re.sub(r"[^a-z0-9_]", "_", name.lower())
    if not text[:1].isalpha():
        text = f"p{text}"
    text = text[:24]
    return f"{text}_" if text in RESERVED else text


def auto_id(base: str, ordinal: int) -> str:
    """The id of the `ordinal`-th node (or layer) of id base `base`: the
    base, then `base2`, `base3`, ..., cut to fit 24 characters."""
    suffix = "" if ordinal == 1 else str(ordinal)
    return base[: 24 - len(suffix)] + suffix


def free_id(base: str, taken: Collection[str]) -> str:
    """The first id of base `base` (`auto_id`) that `taken` does not hold."""
    return next(nid for ordinal in count(1) if (nid := auto_id(base, ordinal)) not in taken)


def require_id(value: object, noun: str = "node") -> str:
    """`value` as the id of a `noun`. Raises ValueError, in `check_id`'s
    words, for an id it refuses."""
    if (reason := check_id(value, noun)) is not None:
        raise ValueError(reason)
    assert isinstance(value, str)  # check_id refuses anything else
    return value


@dataclass(frozen=True, slots=True)
class Node:
    """One op of a program: `op` with `args` (JSON values, by arg name),
    reading the outputs of the nodes `inputs` names. `args` is read-only."""

    id: str
    op: str
    args: Mapping[str, Any] = field(default_factory=dict)
    inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_id(self.id)
        if not isinstance(self.op, str) or not self.op:
            raise ValueError(f"node {self.id!r}: op is a name, got {self.op!r}")
        object.__setattr__(self, "args", MappingProxyType(dict(self.args)))
        object.__setattr__(self, "inputs", tuple(self.inputs))


def _layer_cycle(ids: str) -> str:
    return f"nodes {ids} read each other in a cycle; a layer's last frame comes from prev(), never a cycle"


def order(
    nodes: Mapping[str, Node],
    after: Mapping[str, Iterable[str]] | None = None,
    *,
    noun: str = "node",
    cycle: Callable[[str], str] = _layer_cycle,
) -> tuple[tuple[Node, ...], list[str]]:
    """`nodes` (by id) in an order where each comes after every node it
    reads and every node `after` lists for it, keeping the given order
    wherever it already is, and why they cannot form a graph: a read of no
    node, or nodes that read each other, worded by `cycle` from their ids.
    `noun` is what a node is called (a signal, in a look's signals). Never
    raises."""
    problems = [
        f"{noun} {node.id!r} reads {source!r}, which is not a {noun}"
        for node in nodes.values() for source in node.inputs if source not in nodes
    ]
    needs = {nid: [*node.inputs, *(after or {}).get(nid, ())] for nid, node in nodes.items()}
    placed: dict[str, Node] = {}
    waiting = list(nodes.values())
    while waiting:
        ready = next((n for n in waiting if all(s in placed or s not in nodes for s in needs[n.id])), None)
        if ready is None:
            problems.append(cycle(", ".join(repr(n.id) for n in waiting)))
            break
        placed[ready.id] = ready
        waiting.remove(ready)
    return tuple(placed.values()) if not problems else tuple(nodes.values()), problems


def post_order(roots: Iterable[T], reads: Callable[[T], Iterable[T]]) -> list[T]:
    """`roots` and every node they read (`reads(node)`, in port order),
    each once and after the nodes it reads: the order Python evaluates a
    builder chain in (pewpew.fx.expr), which `to_python` follows too."""
    order: list[T] = []
    seen: set[T] = set()

    def visit(node: T) -> None:
        if node not in seen:
            seen.add(node)
            for source in reads(node):
                visit(source)
            order.append(node)

    for root in roots:
        visit(root)
    return order


@dataclass(frozen=True, slots=True)
class Graph:
    """Nodes in topological order: each reads only nodes listed before it.
    Ids are unique. Raises ValueError, naming every problem, otherwise."""

    nodes: tuple[Node, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        problems: list[str] = []
        seen: set[str] = set()
        ids = {node.id for node in self.nodes}
        for node in self.nodes:
            if node.id in seen:
                problems.append(f"node {node.id!r} is listed twice")
            for source in node.inputs:
                if source not in ids:
                    problems.append(f"node {node.id!r} reads {source!r}, which is not a node")
                elif source not in seen:
                    problems.append(
                        f"node {node.id!r} reads {source!r}, which is not listed before it; "
                        "list each node after the nodes it reads (a graph has no cycles)"
                    )
            seen.add(node.id)
        if problems:
            raise ValueError("; ".join(problems))

    def __getitem__(self, nid: str) -> Node:
        for node in self.nodes:
            if node.id == nid:
                return node
        raise KeyError(nid)

    def __contains__(self, nid: object) -> bool:
        return any(node.id == nid for node in self.nodes)

    def __iter__(self) -> Iterator[Node]:
        return iter(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)


class Buildable(Protocol):
    """A builder expression (pewpew.fx.expr.Expr): it gives a program."""

    def program(self) -> Program: ...


@dataclass(frozen=True, slots=True)
class Program:
    """What a layer runs: `graph`, the node whose output it shows (`out`),
    and the node whose output masks it (`alpha`), or None for no mask."""

    graph: Graph
    out: str
    alpha: str | None = None

    @classmethod
    def of(cls, source: Program | Buildable) -> Program:
        """`source` as a program: a program as it is, or the program a
        builder expression gives (`osc(8).kaleid(5)`)."""
        return source if isinstance(source, Program) else source.program()

    def __post_init__(self) -> None:
        for role, nid in (("out", self.out), ("alpha", self.alpha)):
            if nid is not None and nid not in self.graph:
                raise ValueError(f"{role} names {nid!r}, which is not a node")

    @property
    def output(self) -> Node:
        """The node whose output the layer shows."""
        return self.graph[self.out]

    @property
    def ends(self) -> tuple[str, ...]:
        """The ids of `out` and, when there is one, `alpha`."""
        return (self.out,) if self.alpha is None else (self.out, self.alpha)

    def reads(self) -> Counter[str]:
        """How many times each node is read: by other nodes, and as `out`
        or `alpha`."""
        return Counter([*(source for node in self.graph for source in node.inputs), *self.ends])
