"""Checking a look, and making it ready to render.

`check_look` takes a looks file (version 4; a `.look.json` file is one) or
a single look, as a `Look`, JSON data or JSON text. A file is always a
looks file, as `run --looks` reads it (ADR-006 amendment "layered paths":
there is no second file form for one look). It never raises: what is wrong
comes back as `Problem`s (pewpew.problems), in the words the aura
itself uses. It checks what the aura checks at launch: the file's shape,
each layer's program and the look's signals (the codec, pewpew.fx.codec,
through `pewpew.aura.book.parse_looks`), then each program's patterns and
their params, and each route's knob (`pattern_problems`). A look that
passes comes back normalized: in the looks file's form (`encode_look`),
with every knob of every node and signal at its value, the defaults
written out, as a look saved from the running aura is. A program is
checked against a map only when it renders (`dims_problems`).

A pattern resolves as `python -m pewpew run` resolves one
(pewpew.load.resolve): a gallery name, a `pattern_dir` file by its name,
or a path. Resolving a file runs its code, so check only files you trust.
With a `catalog` (pewpew.load.Catalog), a pattern resolves through it
and by name alone, as for a look sent to a running engine: a path is a
problem, and its file is never read (ADR-020 amendment "capabilities").

`ready` gives one look of the file ready to run (`Ready`), each layer as
the aura builds it (pewpew.aura.deck.ready_layer), and `ready_looks`
every look; each raises `Refused` with the problems.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from pewpew.aura.book import VERSION, LookBook, LookError, parse_looks, pattern_problems
from pewpew.aura.deck import ready_layer
from pewpew.compose import LayerControls, LayerError, Look, Resolved, layer_address, pattern_of
from pewpew.compose.controls import runs
from pewpew.errors import LoadError, describe_exception, did_you_mean, unknown
from pewpew.fx.codec import encode_look
from pewpew.fx.compile import check, is_pattern_program, knob_class
from pewpew.fx.graph import PATTERN, Graph, Node, Program
from pewpew.fx.host import ProgramPattern, split_starts
from pewpew.fx.ops import OPS
from pewpew.jsonfile import TooDeep, nests_deeper, parse_json
from pewpew.load import Catalog, LoadedPattern, is_path, names, resolve
from pewpew.params import ParamSet
from pewpew.problems import Code, Problem, Refused, problem
from pewpew.result import Result

# What check_look and the render family take: a look or a looks file.
LookDoc = Look | Mapping[str, Any] | str | Path

# The name a single look goes by inside the looks file it is checked as.
_SINGLE = "look"
# Why a pattern given as a path does not load through a catalog.
BY_NAME = "a look sent to an engine names its pattern by name, never by file"


@dataclass(frozen=True)
class Check(Result):
    """Whether a look or looks file is ready to run (`ok`), the same
    normalized (None unless ok), and every problem found."""

    ok: bool
    look_normalized: dict[str, Any] | None = None
    problems: tuple[Problem, ...] = ()


@dataclass(frozen=True, slots=True)
class Ready:
    """One look ready to run: the look, its knobs normalized; each layer
    with the class its renderer runs (its one pattern, or a
    `ProgramPattern`) and the name it shows by; the SHA-256 of each layer's
    pattern sources, bottom first (a program's joined by "+", in graph
    order); and the look with only the knobs its document gives
    (`authored`)."""

    look: Look
    layers: tuple[Resolved, ...]
    sources: tuple[str, ...]
    authored: Look


def check_look(doc: LookDoc, *, pattern_dir: Path | None = None, catalog: Catalog | None = None) -> Check:
    """Check `doc`, a looks file or a single look (module docstring).
    `pattern_dir` is `run --pattern-dir`; a `catalog` replaces it. Never
    raises."""
    read = _Read.of(doc, _Patterns(pattern_dir, catalog))
    if read.problems:
        return Check(False, None, read.problems)
    if read.single:
        return Check(True, encode_look(read.looks[_SINGLE].look))
    normalized = replace(read.book, looks={name: ready.look for name, ready in read.looks.items()})
    return Check(True, json.loads(normalized.to_bytes()))


def ready(
    doc: LookDoc, *, name: str | None = None, pattern_dir: Path | None = None, catalog: Catalog | None = None,
) -> Ready:
    """A look of `doc` ready to run: a single look, or the look `name` of a
    looks file, by default its only look or else its `current` one.
    `pattern_dir` and `catalog` are as `check_look` takes them. Raises
    Refused with every problem."""
    read = _Read.of(doc, _Patterns(pattern_dir, catalog))
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


def ready_looks(path: Path, *, pattern_dir: Path | None = None) -> dict[str, Ready]:
    """Every look of the looks file at `path` ready to run, by name.
    Raises Refused with every problem."""
    read = _Read.of(path, _Patterns(pattern_dir))
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
    def of(cls, doc: LookDoc, patterns: _Patterns) -> _Read:
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
            return cls(_localized([problem(text, file) for text in exc.problems], single))
        texts = pattern_problems(book, patterns.declared)
        if texts:
            examples = _examples(book, patterns)
            return cls(_localized([problem(text, file, examples) for text in texts], single))
        labels = patterns.labels()
        try:
            looks = {name: patterns.ready(look, labels) for name, look in book.looks.items()}
        except LayerError as exc:  # checked above, so only a pattern file changed since
            return cls(_localized([problem(str(exc), file)], single))
        return cls((), single, book, looks)


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


class _Patterns:
    """The patterns a document names, each resolved once: as `run`
    resolves a pattern, or through `catalog` by name alone."""

    def __init__(self, pattern_dir: Path | None, catalog: Catalog | None = None) -> None:
        self.pattern_dir = pattern_dir
        self.catalog = catalog
        self._loaded: dict[str, LoadedPattern] = {}

    def labels(self) -> list[str]:
        """The names a pattern goes by on the page."""
        return names(self.pattern_dir) if self.catalog is None else self.catalog.names

    def loaded(self, spec: str) -> LoadedPattern:
        """Pattern `spec` resolved. Raises as `resolve` or the catalog does,
        and LoadError for a path when there is a catalog."""
        if spec not in self._loaded:
            if self.catalog is None:
                self._loaded[spec] = resolve(spec, search_dir=self.pattern_dir)
            elif is_path(spec):
                raise LoadError(BY_NAME)
            else:
                self._loaded[spec] = self.catalog.resolve(spec)
        return self._loaded[spec]

    def declared(self, spec: str) -> type:
        return self.loaded(spec).cls

    def known(self, spec: str) -> type | None:
        """The class of pattern `spec` if it resolved before, else None:
        what is known without loading anything."""
        loaded = self._loaded.get(spec)
        return None if loaded is None else loaded.cls

    def ready(self, look: Look, labels: list[str]) -> Ready:
        """`look`, whose every pattern resolves and takes its params, ready
        to run, its knobs normalized. Raises LayerError as the aura does."""
        layers: list[Resolved] = []
        sources: list[str] = []
        for layer in look.layers:
            program = _normalized(layer.program, self.declared)
            resolved, _ = ready_layer(replace(layer, program=program), self.loaded, labels)
            layers.append(resolved)
            specs = dict.fromkeys(pattern_of(node)[0] for node in program.graph if node.op == PATTERN)
            sources.append("+".join(self.loaded(spec).digest for spec in specs))
        signals = None if look.signals is None else _written(look.signals, self.declared)
        normalized = replace(look, layers=tuple(resolved.layer for resolved in layers), signals=signals)
        return Ready(normalized, tuple(layers), tuple(sources), look)


def _normalized(program: Program, declared: Callable[[str], type]) -> Program:
    """`program` with each node's knobs written out, defaults included."""
    return replace(program, graph=_written(program.graph, declared))


def _written(graph: Graph, declared: Callable[[str], type]) -> Graph:
    """`graph` with each node's knobs written out, defaults included. A
    pattern node that runs a pattern file whose class is a program writes
    its moved knobs (`<nid>.<arg>`) in their JSON form, and no other: the
    file's literals are its content (pewpew.fx.host)."""
    nodes = []
    for node in graph:
        knobs = OPS[node.op].knob_values(node.args)
        fixed = {key: value for key, value in node.args.items() if key not in knobs}
        cls = knob_class(node, declared)
        starts: dict[str, Any] = {}
        if issubclass(cls, ProgramPattern):
            knobs, by_node = split_starts(knobs)
            classes = cls.knob_classes()
            for nid, given in by_node.items():
                shown = ParamSet(classes[nid], given).snapshot_json()
                starts |= {f"{nid}.{arg}": shown[arg] for arg in given}
        values = ParamSet(cls, knobs).snapshot_json()
        nodes.append(Node(node.id, node.op, {**fixed, **values, **starts}, node.inputs))
    return Graph(tuple(nodes))


def dims_problems(staged: Ready, dims: int) -> list[Problem]:
    """What stops each of `staged`'s programs on a map of `dims`
    dimensions (pewpew.fx.compile.check). Never raises."""
    texts: list[str] = []
    for resolved in staged.layers:
        layer, cls = resolved.layer, resolved.cls
        if is_pattern_program(layer.program):
            continue  # one pattern, run directly: any map takes it
        host = cast("type[ProgramPattern]", cls)
        texts += check(layer.program, where=layer_address(layer.id), resolve=host.resolve, dims=dims, hosted=True)
    doc = encode_look(staged.look)
    return [problem(text, doc) for text in texts]


def _examples(book: LookBook, patterns: _Patterns) -> dict[str, Any]:
    """A valid value for each knob of each look whose node classes are
    known, by path: the knob's default."""
    examples: dict[str, Any] = {}
    for name, look in book.looks.items():
        for layer in look.layers:
            sets = [ParamSet(LayerControls, name=layer_address(layer.id))]
            try:
                graph, resolve = runs(layer, patterns.known)  # a pattern file's program, for one whose class is one
            except ValueError:  # its one pattern is not known
                graph, resolve = layer.program.graph, patterns.known
            for node in graph:
                cls = OPS[node.op].knob_class(node.args, resolve) if node.op in OPS else None
                if cls is not None:
                    sets.append(ParamSet(cls, name=layer_address(layer.id, node.id)))
            for params in sets:
                for record in params.describe():
                    examples[f"looks.{name}.{params.owner}.{record['name']}"] = record["default"]
    return examples
