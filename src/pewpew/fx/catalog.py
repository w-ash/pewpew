"""The catalog: the one description of everything a look is made of
(ADR-022). The page, the command line (`python -m pewpew fx catalog`,
`fx show`), the agent service, the generated reference
(docs/reference/catalog.md) and the builder's stub (`expr.pyi`) all read
it; nothing describes an op twice.

`catalog()` is a JSON-ready dict of five sections, and `page`, `markdown`
and `stub` give it as the control page, the reference page and the
builder's stub read it:

- `ops`: one record per op: `op`, `sig`, `label`, `doc` (its docstring),
  `inputs` (`{name, ty}`), `out`, `dims`, `stateful`, `warpable`, `fix`
  (what to use on a map of another dimension), `params` (the params'
  describe records, the same as the page's), `cost` and `examples`, each
  as the builder chain (`py`) and as the program it makes (`json`); a
  signal op's examples are looks, which hold signals and routes.
- `patterns`: each gallery pattern's name, doc, `units`, `warpable` and
  params.
- `blends`: each blend mode, what it does, and whether it shows black
  over nothing (`black`: on the bottom layer it hides the layer).
- `palettes`: each preset gradient, as a `palette` param's value.
- `kinds`: each param kind and what it holds.

`cost` is `{ns_per_point, us_fixed}`: the median time of 40 renders of
the op's first example on the author's laptop (Apple silicon, NumPy 2.4),
minus the same for each program it reads, at about 300, 1,000 and 5,000
points (a 17², 32² and 71² grid; a 7³, 10³ and 17³ lattice for a
volume-only op), with a straight line fitted through the three. A
stateful op is timed over whole frames, its `advance` and its render,
less the same for what it reads, or for a source less a frame of
`osc(1)`; its `us_fixed` holds the work on its own grid or particles,
which grows with the map only up to the grid's cap. Where that
difference is lost in timing noise (a cheap combine) the figure is an
estimate of the same order, and `below`, `prev` and `pattern` are
estimates (a copy; the wrapped pattern's own cost). A signal op costs a
few float operations a frame whatever the map, an estimate in
`us_fixed`. The suite never times anything; measure a new op the same
way.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pewpew.classinfo import first_sentence
from pewpew.color import PRESETS
from pewpew.compose.stack import Look, pattern_program
from pewpew.fx.blend import ABOUT, LABELS, LIGHTS_BLACK, Blend
from pewpew.fx.codec import encode_look, encode_program, to_python
from pewpew.fx.expr import Expr, namespace
from pewpew.fx.graph import PATTERN, Program, as_id
from pewpew.fx.op import Op
from pewpew.fx.ops import OPS
from pewpew.fx.types import Sig
from pewpew.params import Bool, Choice, Color, Float, Int, Palette, ParamSet

SECTIONS = ("ops", "patterns", "blends", "palettes", "kinds")
# The kind of each section's records: the section's one-item name.
RECORD_KINDS = tuple(section.removesuffix("s") for section in SECTIONS)
# What `--kind` takes: a record kind, or an op signature.
KINDS = (*RECORD_KINDS, *(sig.value for sig in Sig))
_PALETTE = Palette(PRESETS[0], presets=PRESETS)


def doc(obj: object) -> str:
    """`obj`'s docstring as one paragraph."""
    return " ".join((inspect.getdoc(obj) or "").split())


def example(py: str) -> Program | Look:
    """The program or look a builder chain makes: an op's example, or
    what `to_python` prints (pewpew.fx.codec), which may end in
    `.program(...)` or be a `look(...)`."""
    # Trusted text only: an op's examples are source in its own class, as
    # trusted as its code. They run with the builder's names only.
    made = eval(py, {"__builtins__": {}}, namespace())
    if not isinstance(made, Expr | Program | Look):
        raise TypeError(f"example {py!r} gives a {type(made).__name__}, not a builder")
    return made if isinstance(made, Look) else Program.of(made)


def encode_example(made: Program | Look) -> dict[str, Any]:
    """An example's JSON form: a look's, or a program's."""
    return encode_look(made) if isinstance(made, Look) else encode_program(made)


def op_record(cls: type[Op]) -> dict[str, Any]:
    """The catalog record of op `cls`."""
    return {
        "op": cls.op,
        "sig": cls.sig.value,
        "label": cls.label,
        "doc": doc(cls),
        "inputs": [{"name": port.name, "ty": str(port.ty)} for port in cls.inputs],
        "out": str(cls.out),
        "dims": sorted(cls.dims),
        "stateful": cls.stateful,
        "warpable": cls.warpable,
        "fix": cls.fix,
        "params": [] if cls.op == PATTERN else ParamSet(cls).describe(),
        "cost": cls.cost.to_json(),
        "examples": [{"py": py, "json": encode_example(example(py))} for py in cls.examples],
    }


def pattern_record(name: str, cls: type) -> dict[str, Any]:
    """The catalog record of gallery pattern `cls`, named `name`."""
    return {
        "name": name,
        "doc": doc(inspect.getmodule(cls)) or doc(cls),
        "units": cls.units,
        "warpable": bool(cls.warpable),
        "params": ParamSet(cls).describe(),
    }


def catalog() -> dict[str, list[dict[str, Any]]]:
    """Every op (in signature order, then by name), gallery pattern, blend
    mode, palette preset and param kind (module docstring)."""
    from pewpew.load import gallery  # the gallery loads every pattern

    order = list(Sig)
    ops = sorted(OPS.values(), key=lambda cls: (order.index(cls.sig), cls.op))
    return {
        "ops": [op_record(cls) for cls in ops],
        "patterns": [pattern_record(name, cls) for name, cls in gallery().items()],
        "blends": [{"name": mode.value, "label": LABELS[mode], "doc": ABOUT[mode],
                    "black": mode not in LIGHTS_BLACK} for mode in Blend],
        "palettes": [{"name": preset.label, "value": _PALETTE.to_json(preset)} for preset in PRESETS],
        "kinds": [{"kind": kind.kind, "doc": doc(kind).split(": ")[0]} for kind in (Float, Int, Bool, Choice,
                                                                                    Color, Palette)],
    }


def entries(book: Mapping[str, list[dict[str, Any]]], kind: str | None = None, query: str | None = None
            ) -> list[tuple[str, dict[str, Any]]]:
    """The records of `book` (a `catalog()`) of `kind` (`KINDS`; None for
    every section) whose name, label or doc holds every word of `query`,
    ignoring case, each after its record kind (`RECORD_KINDS`)."""
    picked: Iterable[tuple[str, dict[str, Any]]] = (
        (k, record) for k, section in zip(RECORD_KINDS, SECTIONS) for record in book[section]
    )
    if kind is not None:
        picked = ((k, r) for k, r in picked if k == kind or (k == "op" and r["sig"] == kind))
    words = (query or "").lower().split()
    return [(k, record) for k, record in picked if all(w in _text(record) for w in words)]


def items(book: Mapping[str, list[dict[str, Any]]], kind: str | None = None, query: str | None = None
          ) -> list[dict[str, Any]]:
    """The records `entries` finds, without their kinds."""
    return [record for _, record in entries(book, kind, query)]


def name_of(record: Mapping[str, Any]) -> str:
    """A catalog record's name: an op's `op`, a kind's `kind`, else `name`."""
    return str(record.get("op") or record.get("kind") or record.get("name"))


def _text(record: Mapping[str, Any]) -> str:
    """What a query searches in a record: its name, label and doc, lowercased."""
    return " ".join((name_of(record), str(record.get("label", "")), str(record.get("doc", "")))).lower()


# ---- the control page's cards ----------------------------------------------------------


def page(book: Mapping[str, list[dict[str, Any]]], patterns: Sequence[str]) -> dict[str, Any]:
    """`book` as the control page reads it (the preview's `catalog`
    message): a card for each pattern of `patterns` (the aura's pick names)
    and each op that draws (every signature but `signal`), and the blend
    modes as `book` has them. A card is its record's `item`, with the map
    dimensions its op takes (`dims`; None: any), what to use on another
    map (`fix`), and its `examples`: each a program a layer runs, as the
    builder chain (`py`), in the looks file's form (`json`), and with the
    map dimensions it runs on (`dims`: those each of its ops takes). A
    pattern's one example runs it alone."""
    gallery = {record["name"]: record for record in book["patterns"]}
    takes = {record["op"]: set(record["dims"]) for record in book["ops"]}

    def runs_on(example: dict[str, Any]) -> dict[str, Any]:
        ops = {node["op"] for node in example["json"]["nodes"].values()}
        return {**example, "dims": sorted(set.intersection(*(takes[op] for op in ops)))}

    cards = [{**item("pattern", gallery.get(name, {"name": name})), "dims": None, "fix": "",
              "examples": [runs_on(_pattern_example(name))]} for name in patterns]
    cards += [{**item("op", r), "dims": r["dims"], "fix": r["fix"], "examples": [runs_on(e) for e in r["examples"]]}
              for r in book["ops"] if r["sig"] != Sig.SIGNAL]
    return {"cards": cards, "blends": book["blends"]}


def item(kind: str, record: Mapping[str, Any]) -> dict[str, Any]:
    """Record `record`, of record kind `kind` (`RECORD_KINDS`), in short,
    as a search lists it (pewpew.lab.search) and a page's card names it:
    `kind`, `name`, `label` (a pattern's the title its doc starts with;
    the name when it has none), `summary` (its doc's first sentence, a
    pattern's without its title) and `sig` (an op's signature, else
    None)."""
    name = name_of(record)
    text = str(record.get("doc", ""))
    summary = first_sentence(_untitled(text) if kind == "pattern" else text)
    title = _title(text) if kind == "pattern" else ""
    return {"kind": kind, "name": name, "label": str(record.get("label") or title or name), "summary": summary,
            "sig": record.get("sig")}


def _title(doc: str) -> str:
    """The title a pattern's doc starts with (`Color plasma` of `Color
    plasma — the plasma field...`), or ""."""
    title, dash, _ = doc.partition(" — ")
    return title.strip() if dash and "\n" not in title else ""


def _untitled(doc: str) -> str:
    """A pattern's doc without the title its module's starts with (`Wave —
    bands of light...`): the item names it already."""
    _, dash, rest = doc.partition(" — ")
    return rest[:1].upper() + rest[1:] if dash else doc


def _pattern_example(name: str) -> dict[str, Any]:
    """The example of pattern `name`'s card: a program of it alone."""
    program = pattern_program(as_id(name), name)
    return {"py": to_python(program), "json": encode_program(program)}


# ---- the reference page and the builder's stub ------------------------------------------


def markdown(book: Mapping[str, list[dict[str, Any]]]) -> str:
    """`book` as the reference page, docs/reference/catalog.md."""
    lines = [
        "# Effects catalog",
        "",
        "Generated from `pewpew.fx.catalog` by `python -m pewpew fx catalog --format markdown`;",
        "a test fails when it drifts. Do not edit it by hand.",
        "",
        "An op's args are params: `default lo..hi unit`. A source op is a function (`osc(8)`); every",
        "other op is a method of what it reads (`.kaleid(5)`). Coord ops change the coordinates their",
        "input reads, so they wrap what comes before them. A signal op gives one number a frame, which",
        "a look's route adds to a knob (`lfo(0.1).to(\"layers.base.osc.freq\", depth=2)`), or which sweeps",
        "the knob's sweet range when given as its arg (`osc(8, sync=lfo(0.1))`).",
    ]
    for sig in Sig:
        ops = [r for r in book["ops"] if r["sig"] == sig.value]
        if not ops:
            continue
        lines += ["", f"## {sig.value.capitalize()} ops"]
        for record in ops:
            lines += ["", f"### `{record['op']}` — {record['label']}", "", record["doc"], ""]
            ports = ", ".join(f"`{p['name']}` ({p['ty']})" for p in record["inputs"]) or "none"
            lines.append(f"Reads {ports}; gives {record['out']}. Dimensions: "
                         f"{', '.join(map(str, record['dims']))}.{' ' + record['fix'] if record['fix'] else ''}")
            if record["params"]:
                lines += ["", *(f"- `{p['name']}`: {_param(p)}" for p in record["params"])]
            lines += ["", *(f"    {e['py']}" for e in record["examples"])]
    lines += ["", "## Patterns", ""]
    lines += [f"- `{r['name']}` ({r['units']}{', warpable' if r['warpable'] else ''}): {r['doc']}"
              for r in book["patterns"]]
    lines += ["", "## Blend modes", ""] + [f"- `{r['name']}`: {r['doc']}" for r in book["blends"]]
    lines += ["", "## Palettes", ""] + [f"- `{r['name']}`" for r in book["palettes"]]
    lines += ["", "## Param kinds", ""] + [f"- `{r['kind']}`: {r['doc']}" for r in book["kinds"]]
    return "\n".join(lines) + "\n"


def _param(record: Mapping[str, Any]) -> str:
    """A param record in one line: its default, range or options, and help."""
    kind = record["kind"]
    if kind in ("float", "int"):
        unit = f" {record['unit']}" if record["unit"] else ""
        shape = f"{record['default']} {record['lo']}..{record['hi']}{unit}"
    elif kind == "choice":
        shape = f"{record['default']!r} of {', '.join(o['value'] for o in record['options'])}"
    elif kind == "palette":
        shape = f"palette, default {record['default']['label'] or 'custom'}"
    else:
        shape = f"{kind}, default {record['default']}"
    return f"{shape}. {record['help']}".rstrip(". ") + "."


def stub(book: Mapping[str, list[dict[str, Any]]]) -> str:
    """The builder's type stub (`src/pewpew/fx/expr.pyi`): each op that
    reads no node a function, each other op a method, args typed by kind
    (a float or int arg may be a signal), and the look builder."""
    sources = [r for r in book["ops"] if not r["inputs"] and r["op"] != PATTERN]
    methods = [r for r in book["ops"] if r["inputs"]]
    lines = [
        '"""Generated from the catalog (pewpew.fx.catalog.stub); a test fails when it drifts."""',
        "",
        "from collections.abc import Callable, Iterable, Mapping, Sequence",
        "from typing import Any",
        "",
        "from pewpew.compose.stack import Look",
        "from pewpew.fx.graph import Program",
        "from pewpew.fx.ops.signal import Range",
        "from pewpew.params import Param",
        "",
        "class Expr:",
        "    op: str",
        "    args: Mapping[str, Any]",
        "    inputs: tuple[Expr, ...]",
        "    pinned: str | None",
        "    pattern_cls: type | None",
        "    driven: tuple[Routed, ...]",
        "    def id(self, nid: str) -> Expr: ...",
        "    @property",
        "    def signal(self) -> bool: ...",
        "    def to(self, path: str, depth: float) -> Routed: ...",
        "    def program(self, alpha: Expr | None = None) -> Program: ...",
        "    def built(self, alpha: Expr | None = None) -> tuple[Program, list[Routed]]: ...",
        "    def patterns(self) -> dict[str, type]: ...",
    ]
    for record in methods:
        ports = [f"{p['name']}: Expr" for p in record["inputs"][1:]]
        lines.append(_def(record["op"], ["self", *ports, *_args(record)], "    "))
    lines += [
        "    def __getattr__(self, name: str) -> Callable[..., Expr]: ...",
        "",
        "class Routed:",
        "    signal: Expr",
        "    path: str",
        "    depth: float",
        "",
        "class LayerExpr:",
        "    id: str",
        "    source: Expr | Program",
        "    alpha: Expr | None",
        "    mix: Mapping[str, Any]",
        "",
        "def id_base(op: str, args: Mapping[str, Any]) -> str: ...",
        "def assign_ids(nodes: list[tuple[str, str | None]]) -> list[str]: ...",
        "def auto_id(base: str, ordinal: int) -> str: ...",
        "def swept(param: Param[Any], where: str, span: Range) -> tuple[Any, float]: ...",
        "def signal_range(signal: Expr) -> Range: ...",
        "def namespace() -> dict[str, Any]: ...",
        "def layer(lid: str, source: Expr | Program, *, alpha: Expr | None = None, **mix: Any) -> LayerExpr: ...",
        _def("look", ["*layers: LayerExpr", "routes: Iterable[Routed] = ()", "seed: int = 0",
                      "master: float | None = None", "fade: float | None = None", "cycle: bool = False",
                      "front: Sequence[str] = ()"], "", "Look"),
        "def pattern(spec: str | type, *args: Any, **params: Any) -> Expr: ...",
    ]
    lines += [_def(r["op"], _args(r), "") for r in sources]
    lines.append("def __getattr__(name: str) -> Callable[..., Expr]: ...")
    return "\n".join(lines) + "\n"


_PY_TYPES = {"float": "float | Expr", "int": "int | Expr", "bool": "bool", "choice": "str", "color": "Any",
             "palette": "Any"}


def _def(name: str, args: list[str], indent: str, returns: str = "Expr") -> str:
    """A stub's `def` line, its args one per line when it would pass 120 characters."""
    line = f"{indent}def {name}({', '.join(args)}) -> {returns}: ..."
    if len(line) <= 120:
        return line
    inner = "".join(f"\n{indent}    {arg}," for arg in args)
    return f"{indent}def {name}({inner}\n{indent}) -> {returns}: ..."


def _args(record: Mapping[str, Any]) -> list[str]:
    return [f"{p['name']}: {_PY_TYPES[p['kind']]} = ..." for p in record["params"]]
