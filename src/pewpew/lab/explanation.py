"""A look in words: what each layer runs, how it mixes, every knob, and
what moves the knobs.

`explain` writes the same text for the same look, from the look and the
describe records of its knobs (`ParamSet.describe`), with no model in the
loop: a summary of the stack, then one note per layer, bottom first, each
knob as `name = value unit (default, range): help`, then one note per
signal. A layer that runs a program names each node, its op and what the
op does, and each knob by its node, as `node.name = ...`. A signal's note
says what it gives, lists its knobs, and says how far each of its routes
moves its knob: either way for a signal that swings from -1 to 1, one
way for a level from 0 to 1. A knob a route moves renders its own value
plus the route's offset, so its `value` is where it rests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pewpew.classinfo import pattern_summary
from pewpew.compose import Controls, Resolved, Route, controls_of, pattern_of
from pewpew.compose.controls import runs
from pewpew.fx.compile import is_pattern_program, knob_class, label_of
from pewpew.fx.graph import PATTERN, Node
from pewpew.fx.op import Resolve
from pewpew.fx.ops import OPS
from pewpew.fx.ops.signal import Range, ranges
from pewpew.lab.check import LookDoc, ready
from pewpew.params import ParamSet
from pewpew.result import Result


@dataclass(frozen=True, slots=True)
class LayerNote(Result):
    """One layer in words: its id, the pattern it runs (or "program") and
    what it does (for a program, each node and its op), its mix, and one
    line per knob."""

    id: str
    pattern: str
    about: str
    mix: str
    knobs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SignalNote(Result):
    """One signal in words: its id, its op, what it gives, one line per
    knob, and one line per route it drives."""

    id: str
    op: str
    about: str
    knobs: tuple[str, ...]
    routes: tuple[str, ...]


@dataclass(frozen=True)
class Explanation(Result):
    """A look in words: one summary, then each layer, bottom first, then
    each signal, in the order they run."""

    summary: str
    layers: tuple[LayerNote, ...]
    signals: tuple[SignalNote, ...] = ()

    def text(self) -> str:
        """The look in lines of words: the summary, then each layer and its
        knobs, then each signal, its knobs and its routes, one a line."""
        lines = [self.summary]
        for note in self.layers:
            lines.append(f"{note.id}: {note.pattern}, {note.mix}" + (f". {note.about}" if note.about else ""))
            lines += [f"  {knob}" for knob in note.knobs]
        for signal in self.signals:
            lines.append(f"signals.{signal.id}: {signal.op}. {signal.about}")
            lines += [f"  {knob}" for knob in signal.knobs]
            lines += [f"  {route}" for route in signal.routes]
        return "\n".join(lines)


def explain(look: LookDoc, *, name: str | None = None) -> Explanation:
    """`look` (a look, or the look `name` of a looks file) in words.
    Raises Refused for a look with problems."""
    staged = ready(look, name=name)
    shown = staged.look
    stack = ", then ".join(f"{r.label} ({_mix(r)})" for r in staged.layers)
    count = len(staged.layers)
    master = "leaves the master alone" if shown.master is None else f"sets the master to {shown.master:g}"
    cycle = "plays in the idle cycle" if shown.cycle else "stays out of the idle cycle"
    summary = (
        f"{count} layer{'s' if count != 1 else ''}, bottom first: {stack}. Seed {shown.seed}; the look {master}, "
        f"fades in over {shown.fade:g} s and {cycle}."
    )
    signals = tuple(shown.signals or ())
    if signals:
        driven = len({route.path for route in shown.routes})
        summary += (f" {len(signals)} signal{'s' if len(signals) != 1 else ''} move{'s' if len(signals) == 1 else ''} "
                    f"{driven} knob{'s' if driven != 1 else ''} each frame (each signal's note says how far).")
    if shown.front:
        summary += f" A page shows {', '.join(shown.front)} first."
    knobs = controls_of(staged.layers, shown.signals)
    spans = ranges(signals)
    notes = tuple(_signal(node, spans[node.id], shown.routes, knobs) for node in signals)
    return Explanation(summary, tuple(_note(r) for r in staged.layers), notes)


def _signal(node: Node, span: Range, routes: Sequence[Route], knobs: Controls) -> SignalNote:
    """Signal `node`, which gives `span`, in words, with the routes it drives."""
    cls = OPS[node.op]
    lo, hi = span
    about = f"{pattern_summary(cls)} It gives {lo:g} to {hi:g}."
    lines = tuple(_knob(record, node.args[record["name"]]) for record in ParamSet(cls).describe())
    return SignalNote(node.id, node.op, about, lines, tuple(
        _route(route, lo < 0, knobs) for route in routes if route.source == node.id
    ))


def _route(route: Route, swings: bool, knobs: Controls) -> str:
    """How far `route` moves its knob, in the knob's unit: either way when
    its signal `swings` below 0, else one way."""
    knob = knobs.find(route.path)
    moved = knob.drive_range()[0] if knob is not None else None
    unit = f" {moved.unit}" if moved is not None and moved.unit else ""
    if swings:
        return f"moves {route.path} by up to ±{abs(route.depth):g}{unit}, either way from its value"
    way = "up" if route.depth >= 0 else "down"
    return f"moves {route.path} {way} by up to {abs(route.depth):g}{unit} from its value"


def _note(resolved: Resolved) -> LayerNote:
    layer = resolved.layer
    program = layer.program
    graph, resolve = runs(layer, resolved.resolve)  # a pattern file's program, for one whose class is one
    if is_pattern_program(program) and graph is program.graph:
        _, values = pattern_of(program.output)  # every param, written out by `ready`
        knobs = tuple(_knob(record, values[record["name"]]) for record in ParamSet(resolved.cls).describe())
        return LayerNote(layer.id, resolved.label, pattern_summary(resolved.cls), _mix(resolved), knobs)
    about = "; ".join(_node(node, resolve) for node in graph) + "."
    lines: list[str] = []
    for node in graph:
        defaults = ParamSet(knob_class(node, resolve), OPS[node.op].knob_values(node.args)).snapshot_json()
        records = ParamSet(knob_class(node, resolve)).describe()
        lines += (f"{node.id}.{_knob(record, defaults[record['name']])}" for record in records)
    count = len(graph)
    return LayerNote(layer.id, resolved.label, f"{count} node{'s' if count != 1 else ''}: {about}", _mix(resolved),
                     tuple(lines))


def _node(node: Node, resolve: Resolve) -> str:
    """A node in words: `id (op, label): what it does`, with no full stop."""
    cls = knob_class(node, resolve) if node.op == PATTERN else OPS[node.op]
    summary = pattern_summary(cls).rstrip(".")
    head = f"{node.id} ({node.op}, {label_of(node, resolve)})"
    return f"{head}: {summary}" if summary else head


def _mix(resolved: Resolved) -> str:
    layer = resolved.layer
    mix = f"{layer.blend} blend at opacity {layer.opacity:g}"
    return mix if layer.enabled else f"{mix}, switched off"


def _knob(record: Mapping[str, Any], value: Any) -> str:
    """One knob as `name = value unit (default ..., range): help`."""
    unit = f" {record['unit']}" if record.get("unit") else ""
    default = record["default"]
    notes = [] if value == default else [f"default {_value(record, default)}"]
    if "lo" in record:
        notes.append(f"{_value(record, record['lo'])}..{_value(record, record['hi'])}")
    elif "options" in record:
        notes.append("one of " + ", ".join(str(option["value"]) for option in record["options"]))
    about = record.get("help") or record.get("label") or ""
    tail = f" ({'; '.join(notes)})" if notes else ""
    return f"{record['name']} = {_value(record, value)}{unit}{tail}" + (f": {about}" if about else "")


def _value(record: Mapping[str, Any], value: Any) -> str:
    """A knob's JSON value as text."""
    kind = record["kind"]
    if kind == "color":
        return ", ".join(f"{part} {value[part]:g}" for part in ("h", "s", "v"))
    if kind == "palette":
        stops = value["stops"]
        return f"{value.get('label') or 'custom'} ({len(stops)} stops)"
    if kind == "bool":
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
