"""Every knob of a layer stack, by address.

An address is a knob's full path (ADR-006):

    layers.<layer>.(opacity|blend|enabled)   a layer's mix (`LayerControls`)
    layers.<layer>.<node>.<arg>[.<part>]     an arg of one of its nodes
    signals.<signal>.<arg>[.<part>]          an arg of one of the look's signals

Each `ParamSet` in a stack is named by the address before its knobs (its
`owner`), so a refusal names the full path with the params' own wording:
`layers.base.comet.speed must be within 0.0..2.0, got 5.0`. `Controls`
holds a stack's sets by owner, in display order: per layer, bottom to top,
each of its nodes' args in graph order, then its mix; then each signal's
args. An address is read against the longest owner it starts with; a node
id is never a mix knob's name (pewpew.fx.graph `RESERVED`), so the two
never overlap. A part (`color.h`) names a knob a route can drive
(`pewpew.params.Bound`); a set takes the whole value.

`Controls` is one immutable value, replaced whole when the stack changes,
so a reader on another thread takes it once and never sees half a change.
It holds `ParamSet`s, never their `Bound`s: a hot reload keeps a set and
rebinds it, and every write goes through the set (`ParamSet.bound` gives
the current binding). The same rules as `ParamSet` apply: `parse`,
`describe` and `snapshot_json` from any thread, `set` on the loop thread.

`look_controls` gives a look's knobs before it runs, its layers' at their
defaults (`layer_sections`) and its signals' at their values
(`signal_sections`), to check an address against them: a route's path, or
a set before it is sent.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, NamedTuple

from pewpew.errors import unknown
from pewpew.fx.blend import blend_choice
from pewpew.fx.compile import is_pattern_program, knob_class
from pewpew.fx.graph import ID, PATTERN, Graph, Node
from pewpew.fx.host import ProgramPattern, split_starts
from pewpew.fx.op import Resolve
from pewpew.fx.ops import OPS
from pewpew.params import Bool, Float, ParamSet, declared_params
from pewpew.params.bound import drive_range
from pewpew.params.kinds import Color, Parsed, Ranged

if TYPE_CHECKING:
    from pewpew.compose.stack import Layer, Look


LAYERS = "layers"
SIGNALS = "signals"


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"  # an arg's or a part's name
_ADDRESS = re.compile(
    rf"{LAYERS}\.{ID.pattern}\.(?:opacity|blend|enabled)"
    rf"|{LAYERS}\.{ID.pattern}\.{ID.pattern}\.{_NAME}(?:\.{_NAME})?"
    rf"|{SIGNALS}\.{ID.pattern}\.{_NAME}(?:\.{_NAME})?"
)


def address_problem(path: object) -> str | None:
    """Why `path` does not have a knob address's form (module docstring),
    or None. Which knobs a stack has is `Controls.parse`'s to say."""
    if isinstance(path, str) and _ADDRESS.fullmatch(path):
        return None
    return (f"{path!r} is not a knob's address: layers.<layer>.(opacity|blend|enabled), "
            "layers.<layer>.<node>.<arg> or signals.<signal>.<arg>")


def layer_address(lid: str, *parts: str) -> str:
    """The address of layer `lid`, or of the node or knob `parts` names
    under it: `layers.<lid>[.<part>...]`."""
    return ".".join((LAYERS, lid, *parts))


def signal_address(sid: str, *parts: str) -> str:
    """The address of signal `sid`, or of the knob `parts` names under it:
    `signals.<sid>[.<part>...]`."""
    return ".".join((SIGNALS, sid, *parts))


def signal_of(path: str) -> str | None:
    """The signal whose knob address `path` names, or None for a layer's."""
    head, _, rest = path.partition(".")
    if head != SIGNALS:
        return None
    return rest.partition(".")[0] or None


class LayerControls:
    """A layer's mix: how much of it shows, how it combines with the layers
    below it, and whether it runs. Declared as params, so a page sets them
    by address like any knob, and a signal can drive `opacity`. An instance
    is its own params' target: the compositor reads its attributes each
    frame."""

    opacity = Float(1.0, 0.0, 1.0, help="How much of the layer shows; the master dims the room after this",
                    group="Layer", flash_sensitive=True)
    blend = blend_choice("How the layer combines with the layers below it", group="Layer")
    enabled = Bool(True, help="Whether the layer runs and shows", group="Layer")

    def __init__(self, lid: str, values: Mapping[str, Any] | None = None) -> None:
        """Layer `lid`'s mix at `values` (native or JSON, by name), the
        rest at their defaults. Raises ValueError for a value refused."""
        self.params = ParamSet(LayerControls, values, name=layer_address(lid))
        self.params.apply(self)


# The mix knobs' names, in display order: also the mix fields of a `Layer`
# and the mix keys of a layer in a looks file.
MIX = tuple(declared_params(LayerControls))


def mix_problems(lid: str, values: Mapping[str, Any]) -> list[str]:
    """Why each of `values` cannot be layer `lid`'s mix. Never raises."""
    params = ParamSet(LayerControls, name=layer_address(lid))
    return [reason for name, value in values.items() if (reason := params.check(name, value)) is not None]


class Section(NamedTuple):
    """The knobs of one set in a stack: a layer's mix (`node` ""), the args
    of one of its nodes, or a signal's args (`layer` "", `node` the
    signal's id)."""

    params: ParamSet
    layer: str
    node: str


class Knob(NamedTuple):
    """One knob: the set that holds it, its name there, and the part of
    its value the address names ("" for the whole value)."""

    params: ParamSet
    name: str
    part: str = ""

    @property
    def path(self) -> str:
        """The knob's path in its set: `name`, or `name.part`."""
        return f"{self.name}.{self.part}" if self.part else self.name

    def drive_range(self) -> Parsed[Ranged[Any]]:
        """The ranged declaration a route moves on this knob, or why it
        cannot be modulated (pewpew.params.bound.drive_range). Never raises."""
        return drive_range(self.params.declarations[self.name], f"{self.params.owner}.{self.name}", self.part)


class Controls(NamedTuple):
    """A stack's knob sets, by owner address, in display order."""

    sections: Mapping[str, Section]

    @classmethod
    def of(cls, sections: Iterable[Section]) -> Controls:
        return cls(MappingProxyType({section.params.owner: section for section in sections}))

    def find(self, path: str) -> Knob | None:
        """The knob at address `path`, a part of one included, or None."""
        section, name, part = self._locate(path)
        if section is None:
            return None
        param = section.params.declarations.get(name)
        if param is None or (part and not (isinstance(param, Color) and part in param.parts)):
            return None
        return Knob(section.params, name, part)

    def parse(self, path: str, value: object) -> Parsed[tuple[Knob, Any]]:
        """`value` (native or JSON) as the knob at `path` takes it, with the
        knob, or why it is refused: an address that names no knob gets
        every address and the closest, in a route's words. Never raises."""
        knob = self.find(path)
        if knob is None:
            return None, unknown("knob", path, self.snapshot_json(), suggest=True)
        if knob.part:
            owner = f"{knob.params.owner}.{knob.name}"
            return None, f"{path} is a part of {owner}; set {owner} as a whole"
        parsed, reason = knob.params.parse(knob.name, value)
        if reason is not None:
            return None, reason
        return (knob, parsed), None

    def set(self, path: str, value: object) -> bool:
        """Set the knob at `path`; returns whether its value changed. Raises
        ValueError if refused. Loop thread only."""
        found, reason = self.parse(path, value)
        if reason is not None:
            raise ValueError(reason)
        assert found is not None
        knob, parsed = found
        return knob.params.set(knob.name, parsed)

    def describe(self) -> list[dict[str, Any]]:
        """Each knob's declaration record (`Param.spec`) in display order,
        its `name` the knob's address, with the `layer` and `node` it
        belongs to (`node` "" for a layer's mix, `layer` "" for a signal's
        knob: ADR-006's one empty form)."""
        return [
            {**record, "name": f"{owner}.{record['name']}", "layer": section.layer, "node": section.node}
            for owner, section in self.sections.items()
            for record in section.params.describe()
        ]

    def modulatable(self) -> list[str]:
        """The address of every knob a route can move, in display order:
        each float and int, and each part of each color."""
        return [
            f"{owner}.{name}{f'.{part}' if part else ''}"
            for owner, section in self.sections.items()
            for name, param in section.params.declarations.items()
            for part in (param.parts if isinstance(param, Color) else ("",) if isinstance(param, Ranged) else ())
        ]

    def snapshot_json(self) -> dict[str, Any]:
        """Each knob's value in its JSON form, by address."""
        return {
            f"{owner}.{name}": value
            for owner, section in self.sections.items()
            for name, value in section.params.snapshot_json().items()
        }

    def _locate(self, path: str) -> tuple[Section | None, str, str]:
        """The section of the longest owner that address `path` starts
        with, if any, and the rest of the path as the knob's name and part."""
        owners = [owner for owner in self.sections if path.startswith(f"{owner}.")]
        if not owners:
            return None, "", ""
        owner = max(owners, key=len)
        name, _, part = path[len(owner) + 1:].partition(".")
        return self.sections[owner], name, part


# ---- the knobs of a stack before it runs ------------------------------------------------


def runs(layer: Layer, resolve: Resolve) -> tuple[Graph, Resolve]:
    """The nodes `layer` runs, and what resolves their patterns: its own
    program's; or for a layer of one pattern node whose pattern is a
    program (a `ProgramPattern` file), that program's, so the layer has
    their knobs at `layers.<layer>.<node>` as any program's
    (pewpew.compose.compositor), each node's args with the look's moved
    knobs in (`<nid>.<arg>`, pewpew.fx.host). Raises ValueError for a
    pattern `resolve` does not find."""
    program = layer.program
    if is_pattern_program(program) and issubclass(cls := knob_class(program.output, resolve), ProgramPattern):
        _, starts = split_starts(OPS[PATTERN].knob_values(program.output.args))
        nodes = (Node(n.id, n.op, {**n.args, **starts.get(n.id, {})}, n.inputs) for n in cls.runs().graph)
        return Graph(tuple(nodes)), cls.resolve
    return program.graph, resolve


def layer_sections(layer: Layer, resolve: Resolve) -> list[Section]:
    """The knob sets of `layer` as a stack built from it names them, at
    their defaults, each pattern node's class from `resolve`: each node's
    args in graph order (`runs`), then the mix. Raises ValueError for a
    pattern `resolve` does not find."""
    graph, resolve = runs(layer, resolve)
    sections = [Section(ParamSet(knob_class(node, resolve), name=layer_address(layer.id, node.id)), layer.id, node.id)
                for node in graph]
    sections.append(Section(ParamSet(LayerControls, name=layer_address(layer.id)), layer.id, ""))
    return sections


def signal_sections(signals: Graph | None) -> list[Section]:
    """The knob sets of a look's `signals`, at the values their nodes
    give, in graph order. Raises ValueError for a value a knob refuses."""
    return [
        Section(ParamSet(OPS[node.op], node.args, name=signal_address(node.id)), "", node.id)
        for node in signals or ()
    ]


def look_controls(look: Look, resolve: Resolve) -> Controls:
    """Every knob of `look`, as a stack built from it holds them, with
    nothing built: to check an address before the look runs. Raises
    ValueError as `layer_sections` and `signal_sections` do."""
    layers = [section for layer in look.layers for section in layer_sections(layer, resolve)]
    return Controls.of([*layers, *signal_sections(look.signals)])
