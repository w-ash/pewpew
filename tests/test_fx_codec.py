"""The one codec: programs and looks to JSON and back, the builder chain a
program prints as, and the problems a bad program is refused with (a
golden of teaching wordings, tests/goldens/fx_problems.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from fakes import LOOK_CLASSES, program_of
from pewpew.compose import Layer, Look, pattern_layer
from pewpew.compose.controls import look_controls
from pewpew.compose.modulation import route_problems
from pewpew.fx.codec import decode_look, decode_program, encode_look, encode_program, to_python
from pewpew.fx.compile import check, field_ops, upstream
from pewpew.fx.expr import Expr, noise, osc
from pewpew.fx.graph import PATTERN, Graph, Node, Program
from pewpew.fx.host import ProgramPattern
from pewpew.fx.ops import OPS
from pewpew.fx.types import ACCEPTS, Ty
from pewpew.params import Bool, Choice, Float, Int, Palette, Param, declared_params

GOLDEN = Path(__file__).parent / "goldens" / "fx_problems.json"


def round_trip(program: Program) -> tuple[Program | None, list[str]]:
    return decode_program(json.loads(json.dumps(encode_program(program))), where="layers.base")


def from_python(program: Program) -> Program:
    return program_of(to_python(program))


def nodes_of(program: Program) -> dict[str, tuple[str, dict[str, Any], tuple[str, ...]]]:
    return {node.id: (node.op, dict(node.args), node.inputs) for node in program.graph}


# ---- generated programs ------------------------------------------------------------


def value(param: Param[Any]) -> st.SearchStrategy[Any]:
    """A value `param` takes, in its JSON form."""
    if isinstance(param, Float):
        return st.floats(param.lo, param.hi, allow_nan=False)
    if isinstance(param, Int):
        return st.integers(param.lo, param.hi)
    if isinstance(param, Bool):
        return st.booleans()
    if isinstance(param, Choice):
        return st.sampled_from(sorted(param.options))
    assert isinstance(param, Palette)
    return st.sampled_from([param.to_json(preset) for preset in param.presets.values()])


@st.composite
def programs(draw: st.DrawFn) -> Program:
    """A program of up to six nodes of the built-in ops (no pattern
    nodes), each reading earlier nodes of a type its ports take, ending in
    its last node."""
    nodes: list[Node] = []
    types: dict[str, Ty] = {}
    for i in range(draw(st.integers(1, 6))):
        ops = [op for op in field_ops() if op != PATTERN
               and all(any(t in ACCEPTS[port.ty] for t in types.values()) for port in OPS[op].inputs)]
        op = draw(st.sampled_from(ops))
        cls = OPS[op]
        inputs = tuple(draw(st.sampled_from([nid for nid, t in types.items() if t in ACCEPTS[port.ty]]))
                       for port in cls.inputs)
        args = {name: draw(value(param)) for name, param in declared_params(cls).items() if draw(st.booleans())}
        nodes.append(Node(f"n{i}", op, args, inputs))
        types[f"n{i}"] = cls.gives([types[s] for s in inputs])
    out = nodes[-1].id
    graph = Graph(tuple(nodes))
    keep = upstream(Program(graph, out), [out])
    return Program(Graph(tuple(n for n in nodes if n.id in keep)), out)


@given(programs())
def test_a_program_round_trips_through_json_and_through_the_builder_chain(program: Program) -> None:
    assume(not check(program, where="layers.base"))  # a coord op over below() is refused, rightly
    assert round_trip(program) == (program, [])
    assert nodes_of(from_python(program)) == nodes_of(program)


def json_values() -> st.SearchStrategy[Any]:
    leaves = st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=8)
    return st.recursive(leaves, lambda inner: st.lists(inner, max_size=4)
                        | st.dictionaries(st.text(max_size=8), inner, max_size=4), max_leaves=12)


KEYS = ["layers", "nodes", "op", "args", "in", "out", "alpha", "id", "pattern", "sides", "freq"]


def layer_docs() -> list[dict[str, Any]]:
    """Valid layers to graft junk into: a program, and one pattern node,
    whose own `out` is the only node it can name."""
    return [
        {"id": "base", "out": "tint", "nodes": {
            "waves": {"op": "osc", "args": {"freq": 8.0}},
            "fold": {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
            "tint": {"op": "palette", "in": ["fold"], "args": {}}}},
        {"id": "base", "nodes": {"p": {"op": "pattern", "args": {"pattern": "solid"}}}},
    ]


@given(json_values(), st.integers(0, 1), st.lists(st.sampled_from(KEYS), max_size=4), json_values())
def test_decode_never_raises(junk: Any, which: int, path: list[str], graft: Any) -> None:
    """Junk, and a valid look with junk grafted in somewhere."""
    look: Any = {"layers": [layer_docs()[which]]}
    where: Any = look
    for key in path:
        where = where[0] if isinstance(where, list) and where else where
        if isinstance(where, dict):
            if key not in where or not isinstance(where[key], dict | list):
                where[key] = graft
                break
            where = where[key]
    for doc in (junk, look):
        result, problems = decode_look(doc)
        assert (result is None) == bool(problems)


# ---- the JSON form ---------------------------------------------------------------------


def test_a_look_encodes_in_a_fixed_order_and_omits_what_is_default() -> None:
    program = osc(8, 0.1).id("waves").kaleid(5).id("fold").palette("ember").id("tint").program()
    look = Look((Layer("base", program, opacity=0.5), pattern_layer("top", "solid")), seed=7, master=0.6)
    doc = encode_look(look)
    assert list(doc) == ["seed", "master", "fade", "cycle", "layers"]
    assert list(doc["layers"][0]) == ["id", "opacity", "blend", "enabled", "out", "nodes"]
    assert doc["layers"][0]["nodes"]["fold"] == {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}}
    assert decode_look(json.loads(json.dumps(doc))) == (look, [])


@pytest.mark.parametrize("layer", layer_docs(), ids=["program", "pattern"])
@pytest.mark.parametrize("end", [None, 3, "nope"])
def test_an_out_that_names_no_node_is_a_problem_not_an_exception(layer: dict[str, Any], end: Any) -> None:
    look, problems = decode_look({"layers": [{**layer, "out": end}]})
    assert look is None and problems == [f"look: layers.base: 'out' names {end!r}, which is not a node"]


def test_nodes_may_come_in_any_order_and_are_put_after_what_they_read() -> None:
    raw = {"out": "tint", "nodes": {"tint": {"op": "palette", "in": ["waves"]}, "waves": {"op": "osc"}}}
    program, problems = decode_program(raw, where="layers.base")
    assert problems == [] and program is not None
    assert [node.id for node in program.graph] == ["waves", "tint"]
    terse, _ = decode_program({"nodes": {"waves": {"op": "osc"}, "tint": {"op": "palette", "in": ["waves"]}}})
    assert terse is not None and terse.out == "tint", "out defaults to the last node"


def test_the_builder_chain_of_a_program_is_short_and_runs_again() -> None:
    chain = osc(8, 0.1).kaleid(5).modulate(noise(3), 0.2).palette("ember")
    assert to_python(chain.program()) == 'osc(8.0, 0.1).kaleid(5).modulate(noise(3.0), 0.2).palette("ember")'
    w = osc(8).id("waves")
    shared = w.add(w.kaleid(5), amount=0.5).program()
    assert to_python(shared) == '(waves_ := osc(8.0).id("waves")).add(waves_.kaleid(5), 0.5)'
    assert from_python(shared) == shared
    masked = osc(8).palette("ocean").program(alpha=osc(2, offset=0.25))
    assert to_python(masked) == 'osc(8.0).palette("ocean").program(alpha=osc(2.0, offset=0.25))'
    assert from_python(masked) == masked


# ---- the problems a bad program is refused with ---------------------------------------------


def _problems() -> dict[str, list[str]]:
    """Each case's problems: a layer's nodes decoded, or a program checked
    against a map's dimension or with its patterns resolved."""

    class Nested(ProgramPattern):
        program = osc(2)

    classes = {**LOOK_CLASSES, "nested": Nested}

    def nodes(**raw: Any) -> list[str]:
        return decode_program({"nodes": raw}, where="layers.base")[1]

    def checked(source: Expr | Program, dims: int | None = None) -> list[str]:
        return check(Program.of(source), where="layers.base", resolve=classes.get, dims=dims)

    def unchecked(*nodes: Node) -> Program:
        return Program(Graph(nodes), nodes[-1].id)

    waves = {"layers": [{"id": "base", "nodes": {"waves": {"op": "osc"}, "tint": {"op": "palette", "in": ["waves"]}}}]}
    breath = {"breath": {"op": "lfo"}}

    def route(source: str = "breath", path: str = "layers.base.waves.freq", depth: float = 1.0) -> dict[str, Any]:
        return {"source": source, "path": path, "depth": depth}

    def wired(signals: dict[str, Any], *routes: dict[str, Any], front: tuple[str, ...] = ()) -> list[str]:
        """A look's problems: decoded, then each route and front knob
        checked against the stack's knobs, as `pattern_problems` does."""
        look, found = decode_look({**waves, "signals": signals, "routes": list(routes), "front": list(front)})
        if look is None:
            return found
        return route_problems(look.routes, look.front, look_controls(look, classes.get))

    return {
        "unknown op": nodes(fold={"op": "kaleidd"}),
        "unknown param": nodes(waves={"op": "osc", "args": {"freqq": 3}}),
        "out of range": nodes(waves={"op": "osc"}, fold={"op": "kaleid", "in": ["waves"], "args": {"sides": 40}}),
        "a value of the wrong kind": nodes(waves={"op": "osc", "args": {"axis": "w", "freq": "fast"}}),
        "reads too few": nodes(fold={"op": "kaleid"}),
        "reads a node that is not there": nodes(fold={"op": "kaleid", "in": ["waves"]}),
        "a cycle": nodes(a={"op": "add", "in": ["b", "b"]}, b={"op": "hue", "in": ["a"]}),
        "hue on a scalar": nodes(waves={"op": "osc"}, tint={"op": "hue", "in": ["waves"]}),
        "palette on rgb": nodes(waves={"op": "osc"}, a={"op": "palette", "in": ["waves"]},
                                b={"op": "palette", "in": ["a"]}),
        "nothing reads a node": nodes(waves={"op": "osc"}, drift={"op": "noise"},
                                      tint={"op": "palette", "in": ["waves"]}),
        "a bad node id": nodes(Fold={"op": "osc"}),
        "a reserved node id": nodes(blend={"op": "osc"}),
        "an unknown key": nodes(waves={"op": "osc", "arg": {}}),
        "a mask of rgb": decode_program({"alpha": "tint", "nodes": {"waves": {"op": "osc"},
                                                                   "tint": {"op": "palette", "in": ["waves"]}}},
                                        where="layers.base")[1],
        "kaleid on a strip": checked(osc(8).kaleid(5), dims=1),
        "twist on a panel": checked(osc(8).twist(90), dims=2),
        "a fixture pattern in a program": checked(unchecked(Node("p", PATTERN, {PATTERN: "fixtureramp"}),
                                                            Node("dim", "contrast", {}, ("p",)))),
        "a coord op over a pattern that is not warpable": checked(unchecked(
            Node("p", PATTERN, {PATTERN: "solid"}), Node("fold", "mirror", {}, ("p",)))),
        "a coord op over below": checked(unchecked(Node("b", "below"), Node("fold", "mirror", {}, ("b",)))),
        "a coord op over state per point": checked(unchecked(Node("pond", "ripple"),
                                                             Node("turn", "rotate", {}, ("pond",)))),
        "an attractor on a strip": checked(unchecked(Node("moth", "attractor")), dims=1),
        "a program in a program": checked(unchecked(Node("p", PATTERN, {PATTERN: "nested"}),
                                                    Node("dim", "contrast", {}, ("p",)))),
        "an unknown pattern": checked(unchecked(Node("p", PATTERN, {PATTERN: "plasmo"}),
                                                Node("dim", "contrast", {}, ("p",)))),
        "a pattern's param": checked(unchecked(Node("p", PATTERN, {PATTERN: "solid", "rde": 0.5}),
                                               Node("dim", "contrast", {}, ("p",)))),
        "a signal op in a layer": nodes(w={"op": "lfo"}),
        "a field op in the signals": wired({"w": {"op": "osc"}}, route("w")),
        "an unknown signal op": wired({"b": {"op": "lfoo"}}, route("b")),
        "a signal's arg": wired({"breath": {"op": "lfo", "args": {"rate": 99}}}, route()),
        "signals that drive each other": wired({"a": {"op": "lfo"}, "b": {"op": "lfo"}},
                                               route("a", "signals.b.rate"), route("b", "signals.a.rate")),
        "a signal nothing reads": wired(breath),
        "a route from no signal": wired(breath, route("breth")),
        "a route with no path": wired(breath, {"source": "breath", "depth": 1.0}),
        "a route to no knob": wired(breath, route(path="layers.base.waves.fre")),
        "a route to a knob that cannot move": wired(breath, route(path="layers.base.waves.axis")),
        "a route past its knob's span": wired(breath, route(depth=40.0)),
        "a front knob that is not there": wired(breath, route(), front=("layers.base.waves.fre",)),
    }


def test_each_bad_program_is_refused_in_words_that_teach_the_fix(regen_goldens: bool) -> None:
    live = _problems()
    for case, problems in live.items():
        assert problems, f"{case}: no problem found"
    if regen_goldens:
        GOLDEN.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n")
    assert json.loads(GOLDEN.read_text()) == live, "run `uv run pytest --regen-goldens` and review the diff"


def test_the_builder_refuses_what_the_codec_refuses_in_the_same_words() -> None:
    with pytest.raises(ValueError) as built:
        osc(8).hue(30).program()
    decoded = decode_program({"nodes": {"osc": {"op": "osc", "args": {"freq": 8.0}},
                                        "hue": {"op": "hue", "in": ["osc"], "args": {"amount": 30.0}}}},
                             where="layers.base")[1]
    assert decoded == [f"layers.base.{built.value}"]


OSC = {"op": "osc"}
BASE = {"id": "base", "nodes": {"o": OSC}}


@pytest.mark.parametrize("key, doc, refusal", [
    ("layers", {"layers": [{"id": f"l{i}", "nodes": {"o": OSC}} for i in range(17)]}, "17 layers; at most 16"),
    ("nodes", {"layers": [{"id": "base", "nodes": {f"n{i}": OSC for i in range(33)}}]}, "33 nodes; at most 32"),
    ("signals", {"layers": [BASE], "signals": {f"s{i}": {"op": "lfo"} for i in range(33)}}, "33 signals; at most 32"),
    ("routes", {"layers": [BASE], "signals": {"s": {"op": "lfo"}},
                "routes": [{"source": "s", "path": "layers.base.o.freq", "depth": 1.0}] * 65}, "65 routes; at most 64"),
])
def test_a_look_past_a_size_cap_is_refused(key: str, doc: dict[str, Any], refusal: str) -> None:
    """The caps bound a look a page or an agent sends (ADR-022)."""
    look, problems = decode_look(doc)
    assert look is None and any(refusal in problem for problem in problems), problems
