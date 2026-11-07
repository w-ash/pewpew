"""The JSON form of effect programs and looks: the one codec (ADR-022).

`encode_look`, `encode_layer` and `encode_program` give a value's JSON
form, keys in a fixed order and nodes in graph order. `decode_look` and
`decode_program` read one back and never raise: each returns the value,
or None, and every problem, prefixed by where it is (`look 'dusk':
layers.base.fold: ...`), in the params' own words, with a did-you-mean for
an unknown op, arg or key, and type errors that say how to fix them
(pewpew.fx.compile.check). `to_python` prints a program as the builder
chain that makes it (pewpew.fx.expr). The looks file (pewpew.aura.book)
holds the file's envelope around this codec's looks.

A look (ADR-006 amendment "layered paths"):

    {"seed": 7, "master": 0.6, "fade": 4.0, "cycle": true,
     "layers": [{"id": "base", "opacity": 1.0, "blend": "normal", "enabled": true,
                 "out": "tint", "alpha": null,
                 "nodes": {"waves": {"op": "osc", "args": {"freq": 8.0, "sync": 0.1}},
                           "fold": {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
                           "tint": {"op": "palette", "in": ["fold"], "args": {"palette": "ember"}}}}],
     "signals": {"breath": {"op": "lfo", "args": {"rate": 0.1}}},
     "routes": [{"source": "breath", "path": "layers.base.tint.shift", "depth": 40.0}],
     "front": ["layers.base.waves.freq"]}

Every key of a layer but `id` and `nodes` has a default: the mix's
(`LayerControls`), `out` the last node, `alpha` none. A node's `in` lists
the nodes it reads, in its op's port order, and `args` its args by name;
a node may come before a node it reads, and is put after it. A pattern
node is `{"op": "pattern", "args": {"pattern": name, ...its params}}`. A
look's `master` left out leaves the master alone; `fade` defaults to 2 s,
`cycle` to false and `seed` to 0. Its `signals` are signal nodes by id, in
a layer's node form, each put after the signals it reads and the signals
whose routes drive it; each of its `routes` moves the knob at `path` by
`depth` times its `source` signal, in the knob's units; `front` lists the
knobs a page shows first. Each may be left out or null, and is written
only when it holds something. Which knob a route's path names is checked
against the stack's knobs (pewpew.compose.modulation.route_problems),
once its patterns resolve (pewpew.aura.book.pattern_problems).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from pewpew.compose.controls import LAYERS, MIX, SIGNALS, LayerControls, layer_address, mix_problems
from pewpew.compose.modulation import signal_problems
from pewpew.compose.stack import (
    DEFAULT_FADE,
    Layer,
    Look,
    Route,
    check_on_off,
    is_seed,
    order_signals,
    parse_fade,
    parse_master,
    source_problems,
    stack_problems,
)
from pewpew.errors import typo_hint
from pewpew.fx.compile import check, field_ops, signal_ops
from pewpew.fx.expr import assign_ids, id_base
from pewpew.fx.graph import PATTERN, Graph, Node, Program, check_id, order, post_order
from pewpew.fx.op import Op
from pewpew.fx.ops import OPS
from pewpew.jsonfile import is_number
from pewpew.params import Palette, Param, declared_params

MAX_LAYERS = 16
MAX_NODES = 32
MAX_ROUTES = 64

LOOK_KEYS = ("seed", "master", "fade", "cycle", "layers", "signals", "routes", "front")
LAYER_KEYS = ("id", *MIX, "out", "alpha", "nodes")
NODE_KEYS = ("op", "in", "args")
ROUTE_KEYS = ("source", "path", "depth")

Problems = list[str]


# ---- encoding --------------------------------------------------------------------


def encode_look(look: Look) -> dict[str, Any]:
    """`look` in its JSON form."""
    out: dict[str, Any] = {"seed": look.seed}
    if look.master is not None:
        out["master"] = look.master
    out["fade"] = look.fade
    out["cycle"] = look.cycle
    out["layers"] = [encode_layer(layer) for layer in look.layers]
    if look.signals is not None:
        out["signals"] = {node.id: encode_node(node) for node in look.signals}
    if look.routes:
        out["routes"] = [route.to_json() for route in look.routes]
    if look.front:
        out["front"] = list(look.front)
    return out


def encode_layer(layer: Layer) -> dict[str, Any]:
    """`layer` in its JSON form: its id, its mix and its program."""
    return {"id": layer.id, **layer.mix, **encode_program(layer.program)}


def encode_program(program: Program) -> dict[str, Any]:
    """`program` in its JSON form: `out`, `alpha` when it has one, and its
    nodes by id, in graph order."""
    out: dict[str, Any] = {"out": program.out}
    if program.alpha is not None:
        out["alpha"] = program.alpha
    out["nodes"] = {node.id: encode_node(node) for node in program.graph}
    return out


def encode_node(node: Node) -> dict[str, Any]:
    out: dict[str, Any] = {"op": node.op}
    if node.inputs:
        out["in"] = list(node.inputs)
    out["args"] = dict(node.args)
    return out


# ---- decoding --------------------------------------------------------------------


def decode_look(raw: Any, *, where: str = "look", cap: float = 1.0) -> tuple[Look | None, Problems]:
    """The look `raw` holds, or None, and every problem, each prefixed by
    `where`. `cap` is the launch's master cap: a master above it is
    refused. Never raises."""
    problems: Problems = []
    if not isinstance(raw, dict):
        return None, [f"{where} is an object with 'layers'"]
    problems.extend(_unknown_keys(where, raw, LOOK_KEYS))
    seed = raw.get("seed", 0)
    if not is_seed(seed):
        problems.append(f"{where}: 'seed' is a whole number of at least 0, got {seed!r}")
    master = raw.get("master")
    if master is not None:
        master, reason = parse_master(master, cap)
        if reason is not None:
            problems.append(f"{where}: {reason} (the cap set at launch)")
    fade, reason = parse_fade(raw.get("fade", DEFAULT_FADE))
    if reason is not None:
        problems.append(f"{where}: {reason}")
    cycle = raw.get("cycle", False)
    if (reason := check_on_off("cycle", cycle)) is not None:
        problems.append(f"{where}: {reason}")
    layers = _layers(where, raw.get("layers"), problems)
    before = len(problems)
    routes = _routes(where, _given(raw, "routes", []), problems)
    signals = _signals(where, _given(raw, "signals", {}), routes, problems, routed=len(problems) == before)
    front = _front(where, _given(raw, "front", []), problems)
    if problems:
        return None, problems
    assert fade is not None
    return Look(layers, signals, routes, seed, master, fade, cycle, front), []


def _layers(where: str, raw: Any, problems: Problems) -> tuple[Layer, ...]:
    """A look's layers, bottom first; each problem added, prefixed `where`."""
    if not isinstance(raw, list):
        problems.append(f"{where}: 'layers' is a list of layers, the bottom one first")
        return ()
    if len(raw) > MAX_LAYERS:
        problems.append(f"{where}: {len(raw)} layers; at most {MAX_LAYERS}")
    layers = [layer for i, item in enumerate(raw) if (layer := _layer(where, i, item, problems)) is not None]
    if raw and not layers:
        return ()  # each layer's problem is listed already
    problems.extend(f"{where}: {reason}" for reason in stack_problems([layer.id for layer in layers]))
    return tuple(layers)


def _layer(where: str, i: int, item: Any, problems: Problems) -> Layer | None:
    if not isinstance(item, dict):
        problems.append(f"{where}: layers[{i}] is an object with 'id' and 'nodes'")
        return None
    lid = item.get("id")
    if (reason := check_id(lid, "layer")) is not None:
        problems.append(f"{where}: layers[{i}]: {reason}")
        return None
    assert isinstance(lid, str)  # check_id refuses anything else
    at = layer_address(lid)
    before = len(problems)
    problems.extend(f"{where}: {p}" for p in _unknown_keys(at, item, LAYER_KEYS))
    mix = {key: item[key] for key in MIX if key in item}
    problems.extend(f"{where}: {reason}" for reason in mix_problems(lid, mix))
    program, found = decode_program(item, where=at)
    problems.extend(f"{where}: {reason}" for reason in found)
    if len(problems) > before or program is None:
        return None
    return Layer(lid, program, **mix)


def _given(raw: Mapping[str, Any], key: str, empty: Any) -> Any:
    """`raw[key]`, or `empty` when it is left out or null."""
    value = raw.get(key)
    return empty if value is None else value


def _signals(where: str, raw: Any, routes: tuple[Route, ...], problems: Problems, *, routed: bool) -> Graph | None:
    """A look's signals, each after the signals it reads and the signals
    whose routes drive it, or None for none; each problem added, prefixed
    `where`, a signal's by its address. `routed` says every route was
    read, so a signal no route takes is unread."""
    if not isinstance(raw, dict):
        example = '{"breath": {"op": "lfo", "args": {"rate": 0.1}}}'
        problems.append(f"{where}: 'signals' is an object of signal id: signal, such as {example}")
        return None
    found: Problems = []
    if len(raw) > MAX_NODES:
        found.append(f"{SIGNALS}: {len(raw)} signals; at most {MAX_NODES}")
    nodes = [node for sid, item in raw.items() if (node := _node(SIGNALS, sid, item, found, "signal")) is not None]
    ordered, cycles = order_signals({node.id: node for node in nodes}, routes)
    found += (f"{SIGNALS}: {reason}" for reason in cycles)
    graph = Graph(ordered) if ordered and not found else None
    if not found:
        found += source_problems(graph, routes)
        found += signal_problems(graph, routes if routed and not found else None)
    problems.extend(f"{where}: {reason}" for reason in found)
    return None if found else graph


def _routes(where: str, raw: Any, problems: Problems) -> tuple[Route, ...]:
    """A look's routes, in order; each problem added, prefixed `where` and
    the route's place, `routes[<i>]`."""
    if not isinstance(raw, list):
        problems.append(f"{where}: 'routes' is a list of routes, each {{\"source\", \"path\", \"depth\"}}")
        return ()
    if len(raw) > MAX_ROUTES:
        problems.append(f"{where}: {len(raw)} routes; at most {MAX_ROUTES}")
    routes: list[Route] = []
    for i, item in enumerate(raw):
        at = f"{where}: routes[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{at} is an object with 'source', 'path' and 'depth'")
            continue
        found = [f"{at}: {p}" for p in _unknown_keys("", item, ROUTE_KEYS)]
        found += (f"{at}: {key!r} is missing" for key in ROUTE_KEYS if key not in item)
        source, path, depth = (item.get(key) for key in ROUTE_KEYS)
        if "source" in item and check_id(source, "signal") is not None:
            found.append(f"{at}: 'source' is the id of a signal, got {source!r}")
        if "path" in item and not (isinstance(path, str) and path.partition(".")[0] in (LAYERS, SIGNALS)):
            found.append(f"{at}: 'path' is a knob's address, such as layers.base.osc.freq, got {path!r}")
        if "depth" in item and not is_number(depth):
            found.append(f"{at}: 'depth' is a number, in the knob's own units, got {depth!r}")
        problems.extend(found)
        if not found:
            assert isinstance(source, str) and isinstance(path, str) and is_number(depth)  # each refused above if not
            routes.append(Route(source, path, float(depth)))
    return tuple(routes)


def _front(where: str, raw: Any, problems: Problems) -> tuple[str, ...]:
    """A look's front knobs, by address; each problem added, prefixed `where`."""
    if not isinstance(raw, list) or not all(isinstance(path, str) for path in raw):
        problems.append(f"{where}: 'front' is a list of the addresses of the knobs a page shows first")
        return ()
    problems.extend(f"{where}: front[{i}]: repeats front[{raw.index(path)}]; list each knob once"
                    for i, path in enumerate(raw) if path in raw[:i])
    return tuple(raw)


def decode_program(raw: Any, *, where: str = "program") -> tuple[Program | None, Problems]:
    """The program a layer's `nodes`, `out` and `alpha` in `raw` hold, or
    None, and every problem, each prefixed by `where` (the layer's
    address). Keys of `raw` other than those three are not read. Never
    raises."""
    if not isinstance(raw, dict):
        return None, [f"{where} is an object with 'nodes'"]
    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, dict) or not nodes_raw:
        example = '{"id": {"op": "pattern", "args": {"pattern": name, ...}}}'
        return None, [f"{where}: 'nodes' is an object of node id: node, such as {example}"]
    problems: Problems = []
    if len(nodes_raw) > MAX_NODES:
        problems.append(f"{where}: {len(nodes_raw)} nodes; at most {MAX_NODES}")
    nodes = [node for nid, item in nodes_raw.items() if (node := _node(where, nid, item, problems)) is not None]
    if problems:
        return None, problems
    ordered, found = order({node.id: node for node in nodes})
    problems.extend(f"{where}: {reason}" for reason in found)
    if problems:
        return None, problems
    out, alpha = raw.get("out", ordered[-1].id), raw.get("alpha")
    for role, nid in (("out", out), ("alpha", alpha)):
        if (nid is not None or role == "out") and (not isinstance(nid, str) or nid not in nodes_raw):
            problems.append(f"{where}: {role!r} names {nid!r}, which is not a node")
    if problems:
        return None, problems
    assert isinstance(out, str)  # refused above otherwise
    program = Program(Graph(ordered), out, alpha)
    problems.extend(check(program, where=where))
    return (None, problems) if problems else (program, [])


def _node(where: str, nid: Any, item: Any, problems: Problems, noun: str = "node") -> Node | None:
    """One node of a layer's `nodes` (or a look's signals, `noun`
    "signal"), or None with its problems added."""
    if (reason := check_id(nid, noun)) is not None:
        problems.append(f"{where}: {reason}")
        return None
    at = f"{where}.{nid}"
    if not isinstance(item, dict):
        problems.append(f"{at} is an object with 'op' and 'args'")
        return None
    before = len(problems)
    problems.extend(_unknown_keys(at, item, NODE_KEYS))
    op = item.get("op")
    if not isinstance(op, str) or not op:
        ops = signal_ops() if noun == "signal" else field_ops()
        problems.append(f"{at}: 'op' is missing; name the {noun}'s op, one of {', '.join(ops)}")
    inputs = item.get("in", [])
    if not isinstance(inputs, list) or not all(isinstance(s, str) for s in inputs):
        problems.append(f"{at}: 'in' is a list of the ids of the nodes it reads")
    args = item.get("args", {})
    if not isinstance(args, dict):
        problems.append(f"{at}: 'args' is an object of name: value")
    if len(problems) > before:
        return None
    assert isinstance(op, str)  # refused above otherwise
    return Node(nid, op, args, tuple(inputs))


def _unknown_keys(where: str, raw: Mapping[str, Any], known: tuple[str, ...]) -> Problems:
    """A key of `raw` that is not one of `known`, in the looks file's
    wording, prefixed `where` unless it is empty."""
    expected = ", ".join(sorted(known))
    head = f"{where}: " if where else ""
    return [f"{head}unknown key {key!r}{typo_hint(key, known)}; expected {expected}" for key in raw if key not in known]


# ---- the builder chain ---------------------------------------------------------------


def to_python(value: Program | Look) -> str:
    """`value` as the builder chain that makes it (pewpew.fx.expr): a
    program as one expression, a look as a `look(...)` call over its
    layers, with each route as `signal.to(path, depth=...)` and each field
    left at its default left out. A node read more than once gets a walrus
    name, and `.id()` is written only where the id is not the one the
    builder would give."""
    if isinstance(value, Look):
        return _look_python(value)
    chain = _Chain(value.graph, value.ends)
    out = chain(value.out)
    return out if value.alpha is None else f"{out}.program(alpha={chain(value.alpha)})"


class _Chain:
    """Prints the nodes of `graph` as builder chains, `ends` read in that
    order: the walk the builder makes, so ids it would give go unwritten."""

    def __init__(self, graph: Graph, ends: Sequence[str]) -> None:
        self.graph = graph
        self.reads = Counter([*(source for node in graph for source in node.inputs), *ends])
        walk = post_order(ends, lambda nid: graph[nid].inputs)
        autos = assign_ids([(id_base(graph[nid].op, graph[nid].args), None) for nid in walk])
        self.pinned = {nid for nid, auto in zip(walk, autos) if nid != auto}
        self.named: set[str] = set()

    def __call__(self, nid: str) -> str:
        if nid in self.named:
            return f"{nid}_"
        node = self.graph[nid]
        args = _call_args(node, OPS[node.op])
        if node.inputs:
            head, *others = (self(source) for source in node.inputs)
            text = f"{head}.{node.op}({', '.join([*others, *args])})"
        elif node.op == PATTERN:
            text = f"pattern({', '.join([_py(node.args[PATTERN]), *args])})"
        else:
            text = f"{node.op}({', '.join(args)})"
        if nid in self.pinned:
            text += f".id({_py(nid)})"
        if self.reads[nid] > 1:
            self.named.add(nid)
            text = f"({nid}_ := {text})"
        return text


def _look_python(look: Look) -> str:
    """`look` as a `look(...)` call, one argument a line."""
    args = [_layer_python(layer) for layer in look.layers]
    if look.routes:
        chain = _Chain(look.signals or Graph(()), [route.source for route in look.routes])
        lines = (f"        {chain(r.source)}.to({_py(r.path)}, depth={_py(r.depth)}),\n" for r in look.routes)
        args.append(f"routes=[\n{''.join(lines)}    ]")
    fields = (("seed", look.seed, 0), ("master", look.master, None), ("fade", look.fade, DEFAULT_FADE),
              ("cycle", look.cycle, False), ("front", list(look.front), []))
    args += (f"{name}={_py(value)}" for name, value, default in fields if value != default)
    return "look(\n" + "".join(f"    {arg},\n" for arg in args) + ")"


_MIX_DEFAULTS = {name: param.default for name, param in declared_params(LayerControls).items()}


def _layer_python(layer: Layer) -> str:
    """`layer` as a `layer(...)` call: its id, its program, and each mix
    field off its default."""
    program = layer.program
    chain = _Chain(program.graph, program.ends)
    args = [_py(layer.id), chain(program.out)]
    if program.alpha is not None:
        args.append(f"alpha={chain(program.alpha)}")
    args += (f"{name}={_py(value)}" for name, value in layer.mix.items() if value != _MIX_DEFAULTS[name])
    return f"layer({', '.join(args)})"


def _call_args(node: Node, cls: type[Op]) -> list[str]:
    """`node`'s knobs as call arguments: positional while each follows the
    one before it in declared order from the first, then by name. A
    pattern node's knobs, which only its pattern declares, go by name."""
    knobs = cls.knob_values(node.args)
    if node.op == PATTERN:
        return [f"{name}={_py(value)}" for name, value in knobs.items()]
    out: list[str] = []
    for i, (name, param) in enumerate(declared_params(cls).items()):
        if name in knobs:
            text = _knob(param, knobs[name])
            out.append(text if len(out) == i else f"{name}={text}")
    return out


def _knob(param: Param[Any], value: Any) -> str:
    """A knob's JSON value as Python: a palette that is one of its presets
    by the preset's label."""
    if isinstance(param, Palette):
        for label, preset in param.presets.items():
            if param.to_json(preset) == value:
                return _py(label)
    return _py(value)


def _py(value: Any) -> str:
    """A JSON value as Python source."""
    if isinstance(value, bool) or value is None:
        return repr(value)
    if isinstance(value, dict):
        return "{" + ", ".join(f"{json.dumps(k)}: {_py(v)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_py(v) for v in value) + "]"
    return json.dumps(value) if isinstance(value, str) else repr(value)


__all__ = [
    "LAYER_KEYS", "LOOK_KEYS", "MAX_LAYERS", "MAX_NODES", "MAX_ROUTES", "NODE_KEYS", "ROUTE_KEYS", "decode_look",
    "decode_program", "encode_layer", "encode_look", "encode_node", "encode_program", "to_python",
]
