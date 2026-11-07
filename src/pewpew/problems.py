"""Problems with a look, each with a stable code an agent can act on
(ADR-023): the aura refuses a look with them, the lab checks one, and
the CLI and MCP server teach the fix from them.

The looks loader (pewpew.aura.book), the effect-program codec and checker
(pewpew.fx.codec, pewpew.fx.compile) and the param kinds (`ParamSet.parse`)
word every refusal once. `problem` reads one refusal and gives it a stable
`Code`, the path of what it refuses, the valid values its wording lists, a
did-you-mean among them (pewpew.errors.did_you_mean), and an example of a
valid value where one is known. The reason stays the refusal's own words, scrubbed of paths
(pewpew.errors.scrub).

A path is dotted: `looks.<name>` for a look of a book, then a knob's
address (ADR-006: `layers.<layer>.<node>.<arg>`, `layers.<layer>.opacity`,
`signals.<signal>.<arg>`), a node's or signal's own part
(`layers.<layer>.<node>.op`, `.in`, `.pattern`), a route's or front
knob's place and key (`routes[<index>].path`, `front[<index>]`), or the
key refused, such as `looks.dusk.master` or `cycle.end`. A layer
that has no usable id yet is `layers[<index>]`. The path of a problem with
a single look starts at the look, with no `looks.<name>`.

`Refused` carries the problems of a look that cannot run.
"""

from __future__ import annotations

import ast
import json
import re
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pewpew.errors import did_you_mean, scrub
from pewpew.result import Result


class Code(StrEnum):
    """What kind of fix a problem needs. The values never change."""

    UNKNOWN_OP = "unknown-op"  # a node runs an op that does not exist
    UNKNOWN_KEY = "unknown-key"  # a key, or a param, that the thing does not have
    WRONG_KIND = "wrong-kind"  # a value of the wrong type or shape, or a node that cannot read what it reads
    OUT_OF_RANGE = "out-of-range"  # a value outside its range or options, or too many of a thing
    MISSING = "missing"  # a required key, a file or a choice is not there
    BAD_REF = "bad-ref"  # a name that refers to nothing, an id used more than once, or a node nothing reads
    CYCLE = "cycle"  # nodes that read each other
    WRONG_DIMS = "wrong-dims"  # an op that the mapping's dimensions do not support
    WRONG_VERSION = "wrong-version"  # a looks file of another version
    NOT_A_LOOK = "not-a-look"  # not JSON, or not a look or a looks file


# A look an agent can start from: one layer running one gallery pattern.
EXAMPLE_LOOK: dict[str, Any] = {
    "layers": [{"id": "base", "nodes": {"comet": {"op": "pattern", "args": {"pattern": "comet", "speed": 0.4}}}}],
}
# Examples of a key that is missing, by key.
_MISSING_EXAMPLES: dict[str, Any] = {
    "layers": EXAMPLE_LOOK["layers"],
    "nodes": EXAMPLE_LOOK["layers"][0]["nodes"],
    "op": "pattern",
    "pattern": "comet",
}


@dataclass(frozen=True, slots=True)
class Problem(Result):
    """One problem: where (`path`), what kind (`code`), why (`reason`, the
    refusal's own words), the name it is closest to, the valid values, an
    example of a valid value at `path` or None, and the edit that fixes it
    in words (`fix`, made from the rest; None when only its reason can
    say)."""

    path: str
    code: Code
    reason: str
    did_you_mean: str | None = None
    valid: tuple[str, ...] = ()
    example: Any = None
    fix: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fix", self._fix())

    def __str__(self) -> str:
        """The reason, which names its place itself, and the did-you-mean
        when the reason does not give it already."""
        guess = "" if self.did_you_mean is None else f" (did you mean {self.did_you_mean!r}?)"
        return self.reason if guess in self.reason else self.reason + guess

    def _fix(self) -> str | None:
        """The edit that fixes it, from its did-you-mean, example or valid
        values; a list its reason gives already is not given again."""
        where = self.path or "the look"
        key = self.path.rpartition(".")[2]
        listed = len(self.valid) > 2 and ", ".join(self.valid) in self.reason
        if self.code == Code.UNKNOWN_KEY:
            if self.did_you_mean is not None:
                return f"rename {key!r} to {self.did_you_mean!r}"
            if listed or not self.valid:
                return f"remove {key!r}"
            return f"remove {key!r}; the keys there are {', '.join(self.valid)}"
        if self.code == Code.WRONG_DIMS:
            return f"render on a map of {' or '.join(self.valid)} dimensions"
        if self.did_you_mean is not None:
            return f"set {where} to {self.did_you_mean!r}"
        such = "" if self.example is None else f", such as {json.dumps(self.example)}"
        if len(self.valid) == 1 and ".." in self.valid[0]:
            return f"set {where} within {self.valid[0]}{such}"
        if len(self.valid) < 3 and self.valid:
            return f"set {where} to {' or '.join(self.valid)}"
        if listed:
            return f"set {where} to one of the {len(self.valid)} its reason lists"
        if self.valid:
            return f"set {where} to one of {', '.join(self.valid)}"
        return None if self.example is None else f"set {where} to {json.dumps(self.example)}"


class Refused(Exception):
    """A look that cannot run: `problems` says why."""

    def __init__(self, problems: Sequence[Problem]) -> None:
        self.problems = tuple(problems)
        super().__init__("; ".join(str(p) for p in self.problems))


# ---- reading a refusal ------------------------------------------------------

_ID = r"[a-z][a-z0-9_]{0,23}"
_REPR = r"""'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*\""""
_END = r"(?:: | (?=is |holds ))"  # a location ends at ": ", or before a reason about itself
_LOOK = re.compile(rf"look ({_REPR}){_END}")
_TRIGGER = re.compile(rf"trigger ({_REPR}){_END}")
_CYCLE = re.compile(r"cycle: ")
_INDEX = re.compile(rf"layers\[(\d+)\]{_END}")
_ITEM = re.compile(rf"(routes|front)\[(\d+)\]{_END}")
_PLACE = re.compile(rf"(layers(?:\.{_ID})+|signals(?:\.{_ID})*){_END}")  # a layer, node or signal, or a knob
_ADDRESSES = ("layers", "signals")  # the heads of a knob's address
# A knob or a part of its value: `layers.base.t.palette.stops[0].s`.
_SUBJECT = re.compile(r"([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*|\[\d+\])*) (must|takes) (.*)", re.DOTALL)
_HINT = rf"(?: \(did you mean (?:{_REPR})\?\))?"  # pewpew.errors.typo_hint


def problem(text: str, doc: Any = None, examples: Mapping[str, Any] | None = None) -> Problem:
    """`text`, one refusal of the looks loader or of a `ParamSet`, as a
    Problem. `doc` is the looks file refused, as JSON data: it tells a
    missing key from a wrong one. `examples` maps a path to an example of a
    valid value there, such as a knob's default. Never raises."""
    reason = scrub(text)
    path, node, look, rest = _locate(reason, doc)
    code, parts, valid, guess, example = _classify(rest, node)
    if parts and parts[0] in _ADDRESSES and look is not None:
        path = [*look, *parts]  # an address names the knob from the look down
    else:
        path = [*path, *parts]
    where = ".".join(path)
    if example is None and examples is not None and code in (Code.OUT_OF_RANGE, Code.WRONG_KIND, Code.MISSING):
        example = examples.get(where)
    hinted = re.search(rf"\(did you mean ({_REPR})\?\)", reason)  # the refusal's own guess, by any route
    if hinted is not None and _unrepr(hinted[1]) in valid:
        guessed: str | None = _unrepr(hinted[1])
    else:
        guessed = None if guess is None or guess in valid else did_you_mean(guess, valid)
    return Problem(where, code, reason, guessed, valid, example)


def _locate(text: str, doc: Any) -> tuple[list[str], Any, list[str] | None, str]:
    """The location prefixes of `text` read off: the path they name, the
    part of `doc` there (or None), the path of the look they are in, and
    the rest of the text."""
    path: list[str] = []
    node, look, rest = doc, None, text
    while True:
        if m := _LOOK.match(rest):
            name = _unrepr(m[1])
            path, node = ["looks", name], _child(_child(doc, "looks"), name)
            look = list(path)
        elif m := _TRIGGER.match(rest):
            name = _unrepr(m[1])
            path, node = ["triggers", name], _child(_child(doc, "triggers"), name)
        elif m := _CYCLE.match(rest):
            path, node = ["cycle"], _child(doc, "cycle")
        elif m := _INDEX.match(rest):
            i = int(m[1])
            layers = _child(node, "layers")
            path, node = [*path, f"layers[{i}]"], layers[i] if isinstance(layers, list) and i < len(layers) else None
        elif m := _ITEM.match(rest):
            key, i = m[1], int(m[2])
            items = _child(node, key)
            path, node = [*path, f"{key}[{i}]"], items[i] if isinstance(items, list) and i < len(items) else None
        elif m := _PLACE.match(rest):
            head, *ids = m[1].split(".")
            if head == "signals":
                node = _child(node, "signals")
                node = _child(node, ids[0]) if ids else node
            else:
                node = _layer(node, ids[0])
                if len(ids) > 1:
                    node = _child(_child(node, "nodes"), ids[1])
            path = [*path, *m[1].split(".")]
        else:
            return path, node, look, rest
        rest = rest[m.end() :]


def _classify(rest: str, node: Any) -> tuple[Code, list[str], tuple[str, ...], str | None, Any]:
    """The code of a refusal's reason, the path parts it adds, the valid
    values it lists, the word to find a did-you-mean for, and an example."""
    if m := re.fullmatch(rf"unknown key ({_REPR}){_HINT}; expected (.*)", rest, re.DOTALL):
        key = _unrepr(m[1])
        return Code.UNKNOWN_KEY, [key], _listed(m[2]), key, None
    if m := re.search(rf"unknown (\w+) ({_REPR}){_HINT}; \1e?s: (.*)$", rest, re.DOTALL):  # pewpew.errors.unknown
        noun, name = m[1], _unrepr(m[2])
        code = {"param": Code.UNKNOWN_KEY, "op": Code.UNKNOWN_OP, "preset": Code.OUT_OF_RANGE}.get(noun, Code.BAD_REF)
        knob = ["path"] if isinstance(node, dict) else []  # a route's path, or a front knob itself
        parts = {"param": [name], "op": ["op"], "pattern": _pattern_at(node), "signal": ["source"],
                 "knob": knob}.get(noun, [])
        return code, parts, _listed(m[3]), name, None
    if re.match(r"\S+ cannot be modulated: ", rest):  # pewpew.params.bound.drive_range, for a route
        return Code.WRONG_KIND, ["path"], (), None, None
    if re.match(r"\S+ is a part of \S+; list ", rest):  # a front knob
        return Code.WRONG_KIND, [], (), None, None
    if re.match(r"repeats (?:routes|front)\[\d+\]", rest):  # one route or front knob listed twice
        return Code.BAD_REF, [], (), None, None
    if re.match(r"\w+ is (?:not a signal op|a signal, one number a frame)", rest):  # one in the wrong graph
        return Code.WRONG_KIND, ["op"], (), None, None
    if re.match(rf"nothing reads signal (?:{_REPR})", rest):
        return Code.BAD_REF, [], (), None, None
    if m := re.match(rf"signal ({_REPR}) reads (?:{_REPR}), which is not a signal", rest):
        return Code.BAD_REF, [_unrepr(m[1]), "in"], (), None, None
    if re.match(r".* read or drive each other in a cycle", rest, re.DOTALL):
        return Code.CYCLE, [], (), None, None
    if re.match(rf"pattern (?:{_REPR}) (?:is a program|renders once per fixture)", rest):
        return Code.WRONG_KIND, _pattern_at(node), (), None, None
    if re.match(rf"(?:unknown pattern|pattern) (?:{_REPR})", rest):
        return Code.BAD_REF, _pattern_at(node), (), None, None
    if m := re.match(r"\w+ needs a map of ([\d ]+(?:or [\d ]+)?)dimensions", rest):
        return Code.WRONG_DIMS, [], tuple(m[1].replace("or", "").split()), None, None
    if re.match(r"\w+ reads \d+ node\(s\)", rest):
        return Code.WRONG_KIND, ["in"], (), None, None
    if re.match(rf"\w+ takes [\w ]+ on (?:{_REPR}); ", rest):  # a port that does not take the type it reads
        return Code.WRONG_KIND, ["in"], (), None, None
    if re.match(rf"\w+ warps what (?:{_REPR}) reads", rest):
        return Code.WRONG_KIND, [], (), None, None
    if m := re.match(rf"node ({_REPR}) reads (?:{_REPR}), which is not a node", rest):
        return Code.BAD_REF, [_unrepr(m[1]), "in"], (), None, None
    if re.match(rf"nothing reads node (?:{_REPR})", rest):
        return Code.BAD_REF, [], (), None, None
    if re.match(r"nodes .* read each other in a cycle", rest, re.DOTALL):
        return Code.CYCLE, [], (), None, None
    if m := _SUBJECT.match(rest):
        return _param(m[1].split("."), m[2], m[3])
    if m := re.match(rf"({_REPR}) names ({_REPR}), which is not a", rest):
        return Code.BAD_REF, [_unrepr(m[1])], (), None, None
    if rest.startswith("a look has at least one layer"):  # pewpew.compose.stack_problems
        return Code.WRONG_KIND, ["layers"], (), None, EXAMPLE_LOOK["layers"]
    if m := re.match(rf"layer id ({_REPR}) is used more than once", rest):
        return Code.BAD_REF, ["layers", _unrepr(m[1])], (), None, None
    if m := re.match(r"looks file (?:has no version|is version (.*)); this pewpew reads version (\d+)", rest):
        version = int(m[2])  # pewpew.aura.book.VERSION, as the refusal names it
        if m[1] is not None:
            return Code.WRONG_VERSION, ["version"], (str(version),), None, version
        if isinstance(node, dict) and "layers" in node:  # a single look in a file: the file that holds it
            return Code.MISSING, [], (), None, {"version": version, "current": "look", "looks": {"look": node}}
        return Code.MISSING, ["version"], (str(version),), None, version
    if rest.startswith(("a looks file is a JSON object", "invalid JSON")):
        return Code.NOT_A_LOOK, [], (), None, EXAMPLE_LOOK
    if re.match(rf"duplicate key (?:{_REPR}): ", rest):  # pewpew.jsonfile.parse_json
        return Code.BAD_REF, [], (), None, None
    if m := re.match(r"\d+ (\w+); at most \d+", rest):  # too many of a thing: `17 layers; at most 16`
        return Code.OUT_OF_RANGE, [m[1]], (), None, None
    if m := re.match(rf"args: ({_REPR}) is ", rest):  # a node's arg, addressed as a knob is
        key = _unrepr(m[1])
        args = _child(node, "args")
        if isinstance(node, dict) and not (isinstance(args, dict) and key in args):
            return Code.MISSING, [key], (), None, _MISSING_EXAMPLES.get(key)
        return Code.WRONG_KIND, [key], (), None, None
    if m := re.match(rf"({_REPR}) is a (?:whole )?number (?:of at least|above) \S+?,? got -?[\d.]", rest):
        return Code.OUT_OF_RANGE, [_unrepr(m[1])], (), None, None  # a number, past its bound
    if m := re.match(rf"({_REPR}) takes ", rest):  # a layer's key that names a node of the wrong kind
        return Code.WRONG_KIND, [_unrepr(m[1])], (), None, None
    if m := re.match(rf"({_REPR}) is one of (.*); got (.*)$", rest, re.DOTALL):
        got = m[3]
        guess = _unrepr(got) if re.fullmatch(_REPR, got) else None
        return Code.OUT_OF_RANGE, [_unrepr(m[1])], _listed(m[2]), guess, None
    if m := re.match(rf"({_REPR}) (?:is|holds) ", rest):
        key = _unrepr(m[1])
        if isinstance(node, dict) and key not in node:
            return Code.MISSING, [key], (), None, _MISSING_EXAMPLES.get(key)
        return Code.WRONG_KIND, [key], (), None, None
    if m := re.match(rf"bad (\w+) name ({_REPR})", rest):
        return Code.WRONG_KIND, [f"{m[1]}s", _unrepr(m[2])], (), None, None
    if m := re.match(r"bad (\w+) id ", rest):
        return Code.WRONG_KIND, ["id"] if m[1] == "layer" else [], (), None, None
    return Code.WRONG_KIND, [], (), None, None


def _param(subject: list[str], verb: str, rest: str) -> tuple[Code, list[str], tuple[str, ...], str | None, Any]:
    """A refusal in the param kinds' words: `<subject> must ...` or
    `<subject> takes ...`."""
    if verb == "must":
        m = re.match(r"be within (\S+?)\.\.(\S+?),? got ", rest)
        return Code.OUT_OF_RANGE, subject, (f"{m[1]}..{m[2]}",) if m else (), None, None
    if m := re.match(r"one of (.*), got (.*)$", rest, re.DOTALL):
        got = m[2]
        return Code.OUT_OF_RANGE, subject, _listed(m[1]), _unrepr(got) if re.fullmatch(_REPR, got) else None, None
    if rest.startswith("true or false"):
        return Code.WRONG_KIND, subject, ("true", "false"), None, None
    return Code.WRONG_KIND, subject, (), None, None


def _unrepr(text: str) -> str:
    """The text a Python string repr stands for; `text` itself if it is not one."""
    if not re.fullmatch(_REPR, text):
        return text  # so literal_eval reads one string literal and nothing that builds a dict or set
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # an escape Python does not know warns before it fails
            value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text
    return value if isinstance(value, str) else text


def _listed(text: str) -> tuple[str, ...]:
    """The names in a refusal's list, "a, b" or "'a', 'b'"; none for "(none)"."""
    text = text.strip()
    if not text or text == "(none)":
        return ()
    return tuple(_unrepr(item.strip()) for item in text.split(", "))


def _pattern_at(node: Any) -> list[str]:
    """The path parts from `node` to its pattern: from a pattern node, or
    from a layer of one node."""
    if isinstance(node, dict) and "op" in node:
        return ["pattern"]
    nodes = _child(node, "nodes")
    return [next(iter(nodes)), "pattern"] if isinstance(nodes, dict) and len(nodes) == 1 else []


def _child(node: Any, key: str) -> Any:
    return node.get(key) if isinstance(node, dict) else None


def _layer(look: Any, lid: str) -> Any:
    """The layer of `look` whose id is `lid`, or None."""
    layers = _child(look, "layers")
    if not isinstance(layers, list):
        return None
    return next((item for item in layers if isinstance(item, dict) and item.get("id") == lid), None)
