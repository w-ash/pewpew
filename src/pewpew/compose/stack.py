"""The layer stack as values: a `Look` is layers bottom to top, each a
`Layer` that runs one program and mixes onto the layers below it.

A layer's mix is its `opacity`, `blend` mode and whether it is `enabled`;
their ranges and refusals are the `LayerControls` params
(pewpew.compose.controls), so a value here and a knob on the page refuse a
bad mix in the same words. A look's `signals` are a graph of signal ops
(pewpew.fx.ops.signal), and each `Route` adds `depth` times one of them to
a knob (ADR-006 amendment "layered paths"); `front` lists the knobs a page
shows first. Which knob a route's path names, and whether it can be
moved, is checked against the stack's knobs
(pewpew.compose.modulation.route_problems).

A look's `colorways` are named sets of knob values, by address, each
value in its knob's JSON form (ADR-006 amendment "colorways"): a press
sets them all at once, so the look takes other colours while its motion
carries on. `parse_colorways` checks them against a stack's knobs, and
`with_colorway` gives the look with one of them set.

A layer's program is an effect program (pewpew.fx): nodes of ops, the
node it shows (`out`) and the node that masks it (`alpha`), so node
`waves`'s arg `freq` is `layers.base.waves.freq` on a layer `base`. A
look's fade and master and a switch's on/off are checked
here (`parse_fade`, `parse_master`, `check_on_off`), in the params' words,
for the look, the codec and the aura's requests alike.

Every layer draws its own random stream, seeded from the look's seed and
the layer's id (`layer_seed`), so adding, removing or moving another layer
never changes its picture. The JSON form is the looks file's
(pewpew.aura.book).
"""

from __future__ import annotations

import math
import re
import zlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

import numpy as np

from pewpew.compose.controls import MIX, LayerControls, layer_address, mix_problems, signal_address, signal_of
from pewpew.errors import typo_hint, unknown
from pewpew.fx.graph import Graph, Node, Program, order, require_id
from pewpew.params import Bool, Float
from pewpew.params.kinds import Parsed
from pewpew.result import Result

if TYPE_CHECKING:
    from pewpew.compose.controls import Controls

DEFAULT_FADE = 2.0
MAX_FADE = 600.0
MAX_NAME = 32  # characters in a look's, a trigger's or a colorway's name
# Letters and digits first, then also space, "_" and "-": short enough for a
# phone button, and nothing that reads as a path.
_NAME = re.compile(rf"[A-Za-z0-9][A-Za-z0-9 _-]{{0,{MAX_NAME - 1}}}")
MAX_COLORWAYS = 12
MAX_COLORWAY_KNOBS = 32  # knobs one colorway sets

# A look's colorways: each colorway's knob values by address, JSON form.
Colorways = Mapping[str, Mapping[str, Any]]


_FADE = Float(DEFAULT_FADE, 0.0, MAX_FADE, "s")
_ON_OFF = Bool(False)


def parse_fade(value: object) -> Parsed[float]:
    """`value` as a fade time in seconds, snapped onto 0 to `MAX_FADE`, or
    why it cannot be one. Never raises."""
    return _FADE.parse("fade", value)


def parse_master(value: object, cap: float = 1.0) -> Parsed[float]:
    """`value` as a look's master level, 0 to `cap` (the launch's cap; a
    look alone takes up to 1), or why it cannot be one. Never raises."""
    return Float(cap, 0.0, cap).parse("master", value)


def check_fade(value: object) -> str | None:
    """Why `value` cannot be a fade time in seconds, or None. Never raises."""
    return parse_fade(value)[1]


def check_on_off(control: str, value: object) -> str | None:
    """Why `value` cannot switch `control` on or off, or None. Never raises."""
    return _ON_OFF.parse(control, value)[1]


def check_name(name: object, noun: str = "look") -> str | None:
    """Why `name` cannot name a look (or a `noun`), or None. Never raises."""
    if not isinstance(name, str):
        return f"a {noun} name is text, got {name!r}"
    if not _NAME.fullmatch(name):
        return (
            f"bad {noun} name {name!r}: 1 to {MAX_NAME} letters, digits, spaces, '_' or '-', "
            "starting with a letter or digit"
        )
    return None


def is_seed(value: object) -> bool:
    """Whether `value` can be a look's seed: a whole number of at least 0."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def layer_seed(seed: int, lid: str) -> int:
    """The seed of layer `lid` in a look seeded `seed`: from NumPy's
    `SeedSequence` over the seed and the CRC-32 of the id, never Python's
    `hash`, so it is the same in every process."""
    return int(np.random.SeedSequence([seed, zlib.crc32(lid.encode())]).generate_state(1)[0])


def stack_problems(ids: Sequence[str]) -> list[str]:
    """Why layers of ids `ids`, bottom first, cannot form one look: none,
    or an id used more than once. Never raises."""
    if not ids:
        return ["a look has at least one layer"]
    counts = Counter(ids)
    return [f"layer id {lid!r} is used more than once" for lid, count in counts.items() if count > 1]


@dataclass(frozen=True, slots=True)
class Layer:
    """One layer of a look: `id`, the `program` it runs, and its mix.
    Raises ValueError for a bad id or a mix the `LayerControls` refuse."""

    id: str
    program: Program
    opacity: float = LayerControls.opacity.default
    blend: str = LayerControls.blend.default
    enabled: bool = LayerControls.enabled.default

    def __post_init__(self) -> None:
        require_id(self.id, "layer")
        problems = mix_problems(self.id, self.mix)
        if problems:
            raise ValueError("; ".join(problems))
        object.__setattr__(self, "opacity", float(self.opacity))

    @property
    def mix(self) -> dict[str, Any]:
        """The mix as `LayerControls` values: opacity, blend and enabled."""
        return {name: getattr(self, name) for name in MIX}


@dataclass(frozen=True, slots=True)
class Route(Result):
    """Signal `source` driving the knob at address `path`: each frame the
    knob reads its own value plus `depth` times the signal, in the knob's
    own units, wrapped if the knob is periodic and clamped if not (ADR-006
    modulation). `to_json` is its form in a look and on the wire."""

    source: str
    path: str
    depth: float

    def __post_init__(self) -> None:
        require_id(self.source, "signal")
        if not isinstance(self.path, str) or not self.path:
            raise ValueError(f"a route's path is a knob's address, got {self.path!r}")
        if not math.isfinite(self.depth):
            raise ValueError(f"a route's depth is a finite number, got {self.depth}")
        object.__setattr__(self, "depth", float(self.depth))


def order_signals(nodes: Mapping[str, Node], routes: Sequence[Route]) -> tuple[tuple[Node, ...], list[str]]:
    """A look's signal `nodes` (by id) in the order they run: each after
    the signals it reads and the signals whose routes drive it, keeping the
    given order where it already is (pewpew.fx.graph.order); and why they
    cannot run: a read of no signal, or signals that read or drive each
    other. Never raises."""
    after: dict[str, list[str]] = {}
    for route in routes:
        if (target := signal_of(route.path)) is not None:
            after.setdefault(target, []).append(route.source)
    return order(nodes, after, noun="signal", cycle=lambda ids: (
        f"{ids} read or drive each other in a cycle; a signal cannot depend on itself"
    ))


def source_problems(signals: Graph | None, routes: Sequence[Route]) -> list[str]:
    """Why `routes` cannot run on `signals`: a source that is not a signal,
    or a route into a signal from one not listed before it, which a
    signal graph in order never has (pewpew.fx.graph.order puts each
    signal after the signals that drive it). Never raises."""
    ids = [node.id for node in signals or ()]
    problems = []
    for i, route in enumerate(routes):
        if route.source not in ids:
            problems.append(f"routes[{i}]: {unknown('signal', route.source, ids, suggest=True)}")
            continue
        target = signal_of(route.path)
        if target in ids and ids.index(target) <= ids.index(route.source):
            problems.append(f"routes[{i}]: signal {target!r} is driven by {route.source!r}, which is not listed "
                            "before it; list each signal after the signals that read or drive it")
    return problems


@dataclass(frozen=True, slots=True)
class Look:
    """A saved state of the aura: its layers bottom to top, the signals and
    routes that drive their knobs, the look's seed, and how it is recalled:
    the master it sets (None: the master stays), its fade in seconds,
    whether the idle cycle plays it, the knobs a page shows first, by
    address, and its colorways (module docstring). Raises ValueError for no
    layers or a repeated layer id (`stack_problems`), a seed that is not a
    whole number of at least 0, a fade, master or cycle its param refuses
    (`parse_fade`, `parse_master`, `check_on_off`), a route
    `source_problems` refuses, a knob listed twice in `front`, or colorways
    of the wrong shape (`colorway_shape`), and TypeError for a layer that is
    not a `Layer` or a route that is not a `Route`. Which knobs a
    colorway's addresses name is `parse_colorways`'s to say."""

    layers: tuple[Layer, ...]
    signals: Graph | None = None
    routes: tuple[Route, ...] = ()
    seed: int = 0
    master: float | None = None
    fade: float = DEFAULT_FADE
    cycle: bool = False
    front: tuple[str, ...] = ()
    colorways: Colorways = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "layers", tuple(self.layers))
        object.__setattr__(self, "routes", tuple(self.routes))
        object.__setattr__(self, "front", tuple(self.front))
        if self.signals is not None and not self.signals:
            object.__setattr__(self, "signals", None)  # one form for no signals, as the file has
        if not all(isinstance(layer, Layer) for layer in self.layers):
            raise TypeError(f"a look's layers are Layer values, got {self.layers!r}")
        if problems := stack_problems([layer.id for layer in self.layers]):
            raise ValueError("; ".join(problems))
        if not is_seed(self.seed):
            raise ValueError(f"a look's seed is a whole number of at least 0, got {self.seed!r}")
        fade, fade_reason = parse_fade(self.fade)
        master, master_reason = (None, None) if self.master is None else parse_master(self.master)
        if reasons := [r for r in (fade_reason, master_reason, check_on_off("cycle", self.cycle)) if r is not None]:
            raise ValueError("; ".join(f"a look's {reason}" for reason in reasons))
        object.__setattr__(self, "fade", fade)
        object.__setattr__(self, "master", master)
        if not all(isinstance(route, Route) for route in self.routes):
            raise TypeError(f"a look's routes are Route values, got {self.routes!r}")
        if problems := source_problems(self.signals, self.routes):
            raise ValueError("; ".join(problems))
        if len(set(self.front)) != len(self.front) or not all(isinstance(path, str) for path in self.front):
            raise ValueError(f"a look's front lists knob addresses, each once, got {self.front!r}")
        if problems := colorway_shape(self.colorways):
            raise ValueError("; ".join(problems))
        object.__setattr__(self, "colorways", {name: dict(values) for name, values in self.colorways.items()})


# ---- colorways ---------------------------------------------------------------------


def colorway_shape(raw: object) -> list[str]:
    """Why `raw` cannot be a look's colorways by its shape alone: not an
    object, too many, a bad name, or a colorway that is not an object of
    1 to `MAX_COLORWAY_KNOBS` knob addresses. Never raises."""
    if not isinstance(raw, Mapping):
        return ["'colorways' is an object of colorway name: {knob address: value}"]
    problems = [f"{len(raw)} colorways; at most {MAX_COLORWAYS}"] if len(raw) > MAX_COLORWAYS else []
    for name, values in raw.items():
        if (reason := check_name(name, "colorway")) is not None:
            problems.append(reason)
        elif not isinstance(values, Mapping) or not values or not all(isinstance(path, str) for path in values):
            problems.append(f"colorway {name!r} is an object of knob address: value, with at least one knob")
        elif len(values) > MAX_COLORWAY_KNOBS:
            problems.append(f"colorway {name!r}: {len(values)} knobs; at most {MAX_COLORWAY_KNOBS}")
    return problems


def parse_colorways(raw: object, controls: Controls) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """`raw` as a look's colorways on a stack of knobs `controls`, each
    value in its knob's JSON form, and why each part is refused: its shape
    (`colorway_shape`), an address that names no whole knob, or a value its
    knob refuses, named `colorway '<name>'`. Never raises."""
    problems = colorway_shape(raw)
    if problems:
        return {}, problems
    assert isinstance(raw, Mapping)  # colorway_shape refuses anything else
    knobs = list(controls.snapshot_json())
    out: dict[str, dict[str, Any]] = {}
    for name, values in raw.items():
        parsed: dict[str, Any] = {}
        for path, value in values.items():
            if controls.find(path) is None:
                found, reason = None, f"unknown key {path!r}{typo_hint(path, knobs)}; expected {', '.join(knobs)}"
            else:
                found, reason = controls.parse(path, value)
            if reason is not None:
                problems.append(f"colorway {name!r}: {reason}")
                continue
            assert found is not None
            knob, native = found
            parsed[path] = knob.params.declarations[knob.name].to_json(native)
        out[name] = parsed
    return (out, []) if not problems else ({}, problems)


def with_colorway(look: Look, name: str) -> Look:
    """`look` with every knob colorway `name` sets at its value there: a
    node's arg, a layer's mix or a signal's arg. An address that names no
    knob of the look is passed over. Raises ValueError for a name that is
    not one of the look's colorways, with the closest."""
    values = look.colorways.get(name)
    if values is None:
        raise ValueError(unknown("colorway", name, look.colorways, suggest=True))
    layers = []
    for layer in look.layers:
        mix = {key: values[path] for key in MIX if (path := layer_address(layer.id, key)) in values}
        graph = Graph(tuple(_painted(node, layer_address(layer.id, node.id), values) for node in layer.program.graph))
        layers.append(replace(layer, program=replace(layer.program, graph=graph), **mix))
    signals = None if look.signals is None else Graph(
        tuple(_painted(node, signal_address(node.id), values) for node in look.signals))
    return replace(look, layers=tuple(layers), signals=signals)


def _painted(node: Node, owner: str, values: Mapping[str, Any]) -> Node:
    """`node`, whose knobs are `<owner>.<arg>`, with each arg `values` sets."""
    head = f"{owner}."
    args = {path[len(head):]: value for path, value in values.items()
            if path.startswith(head) and "." not in path[len(head):]}
    return replace(node, args={**node.args, **args}) if args else node
