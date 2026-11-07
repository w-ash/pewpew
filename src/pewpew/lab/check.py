"""Checking a look, and making it ready to render.

`check_look` takes a looks file (version 4; a `.look.json` file is one) or
a single look, as a `Look`, JSON data or JSON text. A file is always a
looks file, as `run LOOKS` reads it (ADR-006 amendment "layered paths":
there is no second file form for one look). It never raises: what is wrong
comes back as `Problem`s (pewpew.problems), in the words the aura
itself uses. It checks what the aura checks at launch: the file's shape,
each layer's program and the look's signals (the codec, pewpew.fx.codec,
through `pewpew.aura.book.parse_looks`), then each route's knob
(`route_reasons`). A look that
passes comes back normalized: in the looks file's form (`encode_look`),
with every knob of every node and signal at its value, the defaults
written out, as a look saved from the running aura is. A program is
checked against a map only when it renders (`dims_problems`).

`ready` gives one look of the file ready to run (`Ready`), and
`ready_looks` every look; each raises `Refused` with the problems.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from pewpew.aura.book import VERSION, LookBook, LookError, parse_looks, route_reasons
from pewpew.compose import Layer, LayerControls, Look, layer_address
from pewpew.errors import describe_exception, did_you_mean, unknown
from pewpew.fx.codec import encode_look
from pewpew.fx.compile import check
from pewpew.fx.graph import Graph, Node
from pewpew.fx.ops import OPS
from pewpew.jsonfile import TooDeep, nests_deeper, parse_json
from pewpew.params import ParamSet
from pewpew.problems import Code, Problem, Refused, member, problem
from pewpew.result import Result

# What check_look and the render family take: a look or a looks file.
LookDoc = Look | Mapping[str, Any] | str | Path

# The name a single look goes by inside the looks file it is checked as.
_SINGLE = "look"


@dataclass(frozen=True)
class Check(Result):
    """Whether a look or looks file is ready to run (`ok`), the same
    normalized (None unless ok), and every problem found."""

    ok: bool
    look_normalized: dict[str, Any] | None = None
    problems: tuple[Problem, ...] = ()


@dataclass(frozen=True, slots=True)
class Ready:
    """One look ready to run: the look, its knobs normalized, and the look
    with only the knobs its document gives (`authored`)."""

    look: Look
    authored: Look


def check_look(doc: LookDoc) -> Check:
    """Check `doc`, a looks file or a single look (module docstring).
    Never raises."""
    read = _Read.of(doc)
    if read.problems:
        return Check(False, None, read.problems)
    if read.single:
        return Check(True, encode_look(read.looks[_SINGLE].look))
    normalized = replace(read.book, looks={name: ready.look for name, ready in read.looks.items()})
    return Check(True, json.loads(normalized.to_bytes()))


def ready(doc: LookDoc, *, name: str | None = None) -> Ready:
    """A look of `doc` ready to run: a single look, or the look `name` of a
    looks file, by default its only look or else its `current` one. Raises
    Refused with every problem."""
    read = _Read.of(doc)
    if read.problems:
        raise Refused(read.problems)
    if read.single:
        return read.looks[_SINGLE]
    looks = list(read.looks)
    if name is None:
        name = looks[0] if len(looks) == 1 else read.book.current
    if name is None:
        reason = f"the looks file holds {len(looks)} looks and no 'current'; name the look to render"
        raise Refused([Problem("current", Code.MISSING, reason, valid=tuple(looks))])
    if name not in read.looks:
        reason = unknown("look", name, looks)
        raise Refused([Problem(f"looks.{name}", Code.BAD_REF, reason, did_you_mean(name, looks), tuple(looks))])
    return read.looks[name]


def ready_looks(path: Path) -> dict[str, Ready]:
    """Every look of the looks file at `path` ready to run, by name.
    Raises Refused with every problem."""
    read = _Read.of(path)
    if read.problems:
        raise Refused(read.problems)
    return dict(read.looks)


@dataclass(frozen=True, slots=True)
class _Read:
    """What reading a document found: its problems, or its looks file and
    each look ready to run. A single look is the file's one look, `_SINGLE`."""

    problems: tuple[Problem, ...] = ()
    single: bool = False
    book: LookBook = field(default_factory=LookBook)
    looks: Mapping[str, Ready] = field(default_factory=dict)

    @classmethod
    def of(cls, doc: LookDoc) -> _Read:
        data, problems = _data(doc)
        if problems:
            return cls(tuple(problems))
        if isinstance(data, dict) and "nodes" in data and not ({"layers", "version", "looks"} & data.keys()):
            return cls((_program(data),))
        single = not isinstance(doc, Path) and isinstance(data, dict) and not ({"version", "looks"} & data.keys())
        file = {"version": VERSION, "looks": {_SINGLE: data}} if single else data
        try:
            book = parse_looks(json.dumps(file))
        except LookError as exc:
            return cls(_problems(exc.problems, file, single))
        if texts := route_reasons(book):
            return cls(_problems(texts, file, single))
        return cls((), single, book, {name: _ready(look) for name, look in book.looks.items()})


def _data(doc: LookDoc) -> tuple[Any, list[Problem]]:
    """`doc` as JSON data, or the problems that stop reading it."""
    if isinstance(doc, Look):
        return encode_look(doc), []
    if isinstance(doc, Path):
        try:
            text: bytes | str = doc.read_bytes()
        except OSError as exc:
            return None, [Problem("", Code.MISSING, f"cannot read the look: {describe_exception(exc)}")]
    elif isinstance(doc, str):
        text = doc
    else:
        if nests_deeper(doc):
            return None, [problem(f"invalid JSON: {TooDeep()}")]
        try:
            text = json.dumps(doc)
        except (TypeError, ValueError) as exc:
            return None, [Problem("", Code.NOT_A_LOOK, f"not JSON data: {describe_exception(exc)}")]
    try:
        return parse_json(text, LookError), []
    except LookError as exc:
        return None, [problem(reason) for reason in exc.problems]


def _program(data: dict[str, Any]) -> Problem:
    """The one problem of a layer's program given as a look (a catalog
    example's JSON is one): the look that holds it as its layer."""
    reason = ('this is a layer\'s program ("out" and "nodes"), not a look; a look holds it as a layer: '
              '{"layers": [{"id": "base", ...the program}]}')
    return Problem("", Code.NOT_A_LOOK, reason, example={"layers": [{"id": "base", **data}]})


def _problems(texts: Iterable[str], file: Any, single: bool) -> tuple[Problem, ...]:
    """`texts`, reasons found in the looks file data `file`, as problems
    with a valid example for each knob they name (`_localized`)."""
    examples = _examples(file)
    return _localized([problem(text, file, examples) for text in texts], single)


def _localized(problems: list[Problem], single: bool) -> tuple[Problem, ...]:
    """`problems` with paths and reasons from a single look's view: no
    `looks.look` and no `look 'look':` in front."""
    if not single:
        return tuple(problems)
    head, words = f"looks.{_SINGLE}", f"look {_SINGLE!r}: "
    return tuple(
        replace(
            p,
            path=p.path[len(head) + 1 :] if p.path.startswith(f"{head}.") else "" if p.path == head else p.path,
            reason=p.reason.removeprefix(words),
        )
        for p in problems
    )


def _ready(look: Look) -> Ready:
    """`look` ready to run, its knobs normalized."""
    layers = tuple(replace(layer, program=replace(layer.program, graph=_written(layer.program.graph)))
                   for layer in look.layers)
    signals = None if look.signals is None else _written(look.signals)
    return Ready(replace(look, layers=layers, signals=signals), look)


def _written(graph: Graph) -> Graph:
    """`graph` with each node's knobs written out, defaults included."""
    return Graph(tuple(Node(node.id, node.op, ParamSet(OPS[node.op], node.args).snapshot_json(), node.inputs)
                       for node in graph))


def dims_problems(staged: Ready, dims: int) -> list[Problem]:
    """What stops each of `staged`'s programs on a map of `dims`
    dimensions (`dims_reasons`). Never raises."""
    doc = encode_look(staged.look)
    return [problem(text, doc) for text in dims_reasons(staged.look.layers, dims)]


def dims_reasons(layers: Iterable[Layer], dims: int) -> list[str]:
    """What stops each of `layers`' programs on a map of `dims`
    dimensions (pewpew.fx.compile.check), each named by its address. Never
    raises."""
    return [text for layer in layers for text in check(layer.program, where=layer_address(layer.id), dims=dims)]


def _examples(file: Any) -> dict[str, Any]:
    """A valid value for each knob of each look of `file`, a looks file's
    JSON data, by path: the knob's default. Read off the data, so a look
    that does not decode has them too: a layer's mix knobs, and the knobs
    of each node whose op is known. Never raises."""
    examples: dict[str, Any] = {}
    for name, look in _items(member(file, "looks")):
        layers = member(look, "layers")
        for layer in layers if isinstance(layers, list) else ():
            lid = member(layer, "id")
            if not isinstance(lid, str):
                continue
            sets = [ParamSet(LayerControls, name=layer_address(lid))]
            for nid, node in _items(member(layer, "nodes")):
                op = member(node, "op")
                if isinstance(op, str) and op in OPS:
                    sets.append(ParamSet(OPS[op], name=layer_address(lid, nid)))
            for params in sets:
                for record in params.describe():
                    examples[f"looks.{name}.{params.owner}.{record['name']}"] = record["default"]
    return examples


def _items(data: Any) -> list[tuple[str, Any]]:
    """The entries of `data` when it is an object, else none."""
    return list(data.items()) if isinstance(data, dict) else []
