"""The deck: the stack that runs, and the one way to start patterns by name.

A look recall and a pick both start patterns the same way: resolve each
name in the catalog, keep the values that still fit, and build fresh
layers on the crossfader's current geometry. `Deck.recall` does that for a
whole look (a fresh stack, faded or cut to), `Deck.put` for one layer of
the running stack (a pick), and `Deck.add` for a layer new to it; `remove`
and `move` edit the running stack's layers as they run. Each changes
nothing unless every step that can fail has passed, and its refusal names
the layer.

A pattern goes by its name in the catalog: what a look stores, and what
the page, the status line and every refusal call it. A layer that runs an
effect program of more than one node shows as `program`, and each of its
pattern nodes resolves through the catalog too.

Thread discipline as for the crossfader: `recall`, `put`, `add`, `remove`
and `move` belong to the loop thread; `current`, `controls` and `snapshot`
are read by any thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from pewpew.compose import (
    Compositor,
    Controls,
    Layer,
    LayerError,
    Look,
    Resolved,
    pattern_of,
    pattern_program,
)
from pewpew.crossfade import Crossfader
from pewpew.errors import Worded, describe_exception
from pewpew.fx.compile import is_pattern_program
from pewpew.fx.graph import PATTERN, Graph, Node, Program, as_id
from pewpew.fx.host import ProgramPattern, split_starts
from pewpew.load import Catalog
from pewpew.params import ParamSet

logger = logging.getLogger(__name__)


PROGRAM = "program"  # what a layer that runs a program shows as


class Deck:
    """The crossfader over the running stack, and the catalog of names."""

    def __init__(self, fader: Crossfader[Compositor], catalog: Catalog) -> None:
        self.fader = fader
        self.catalog = catalog

    @property
    def current(self) -> str:
        """The bottom layer's pattern, by its name."""
        return self.fader.current.layers[0].label

    @property
    def controls(self) -> Controls:
        """Every knob of the running stack. A recall or a pick installs new
        controls, so read this each time; do not hold it."""
        return self.fader.current.controls

    def snapshot(self) -> Look:
        """The running stack as a look (`Compositor.snapshot`)."""
        return self.fader.current.snapshot()

    def recall(self, look: Look, fade: float = 0.0) -> str | None:
        """Start `look`'s layers and signals fresh, each layer at the values
        its pattern still accepts (the rest at their defaults), fading over
        `fade` seconds or cutting at 0. A running fade ends at its target
        first, as a pick ends it. Returns why not, or None: also a route
        that reaches no knob it can move. Loop thread only."""
        try:
            resolved = [self._resolve(layer) for layer in look.layers]
            incoming = self.fader.current.spawn(resolved, look)
        except (LayerError, ValueError) as exc:  # ValueError: a signal or route the stack cannot run
            # A traceback helps find a pattern that raised; a refusal says all there is.
            refused = not isinstance(exc, LayerError) or isinstance(exc.__cause__, Worded)
            logger.warning("cannot start the look: %s", exc, exc_info=not refused)
            return str(exc)
        if fade:
            if self.fader.fading:
                self.fader.cut(self.fader.current)
            self.fader.fade_to(incoming, fade)
        else:
            self.fader.cut(incoming)
        return None

    def put(self, lid: str, name: str) -> str | None:
        """Run pattern `name` on layer `lid` of the running stack, fresh at
        its defaults; the layer keeps its mix and the other layers run on.
        Ends a running fade, as every pick does. Returns why not, or None.
        Loop thread only."""

        def start(current: Compositor) -> None:
            layer = replace(current.layer(lid).snapshot(), program=pattern_program(as_id(name), name))
            current.put(self._resolve(layer))

        return self._edit(start)

    def add(self, layer: Layer, index: int) -> str | None:
        """Run `layer` in the running stack, fresh, at render index `index`
        (0: the bottom); the other layers run on. Ends a running fade, as a
        pick does. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.insert(self._resolve(layer), index))

    def remove(self, lid: str) -> str | None:
        """Stop layer `lid` of the running stack; the other layers run on.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.remove(lid))

    def move(self, lid: str, index: int) -> str | None:
        """Run layer `lid` of the running stack at render index `index`.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.move(lid, index))

    def _edit(self, edit: Callable[[Compositor], object]) -> str | None:
        """Run `edit` on the running stack, then end a running fade at it.
        Returns the reason of a LayerError or ValueError it raises, with
        the stack untouched, or None."""
        current = self.fader.current
        try:
            edit(current)
        except LayerError as exc:
            logger.warning("cannot run layer %s", exc.layer, exc_info=True)
            return str(exc)
        except ValueError as exc:  # no such layer, a layer of that id, or none left
            return str(exc)
        self.fader.cut(current)
        return None

    def _resolve(self, layer: Layer) -> Resolved:
        return ready_layer(layer, self.catalog.resolve)


def ready_layer(layer: Layer, resolve: Callable[[str], type]) -> Resolved:
    """`layer` ready to build, each pattern `resolve` finds by its name at
    the values it still accepts (`fit`): its one pattern, which shows by
    its name, or a program, which shows as `PROGRAM`. Raises LayerError,
    naming the layer."""
    program = layer.program
    try:
        classes = {spec: resolve(spec) for spec in _specs(program)}
    except Exception as exc:  # LoadError, a gallery module that raised, ...
        raise LayerError(layer.id, describe_exception(exc)) from exc
    program = _fitted(program, classes)
    if is_pattern_program(program):
        spec, _ = pattern_of(program.output)
        return Resolved(replace(layer, program=program), classes[spec], spec)
    return Resolved(replace(layer, program=program), ProgramPattern.of(program, classes), PROGRAM)


def _specs(program: Program) -> list[str]:
    """The pattern spec of each of `program`'s pattern nodes, once each."""
    specs = (pattern_of(node)[0] for node in program.graph if node.op == PATTERN)
    return list(dict.fromkeys(specs))


def _fitted(program: Program, classes: Mapping[str, type]) -> Program:
    """`program` with each pattern node's params at the values its
    pattern (`classes`, by spec) still accepts."""
    nodes = []
    for node in program.graph:
        if node.op == PATTERN:
            spec, values = pattern_of(node)
            node = Node(node.id, PATTERN, {PATTERN: spec, **fit(classes[spec], values)}, node.inputs)
        nodes.append(node)
    return replace(program, graph=Graph(tuple(nodes)))


def fit(cls: type, values: Mapping[str, Any]) -> dict[str, Any]:
    """The values `cls` still accepts. ADR-006's reload policy: a value that
    no longer fits, or a param no longer declared, starts at the pattern's
    default, and the log says which. For a pattern file whose class is a
    program, a moved knob of a node (`<nid>.<arg>`, pewpew.fx.host) is
    kept where that node still takes it."""
    if issubclass(cls, ProgramPattern):
        own, starts = split_starts(values)
        nodes = {nid: ParamSet(knobs) for nid, knobs in cls.knob_classes().items()}
        kept = {k: v for k, v in own.items() if ParamSet(cls).check(k, v) is None}
        kept |= {f"{nid}.{k}": v for nid, args in starts.items() if nid in nodes
                 for k, v in args.items() if nodes[nid].check(k, v) is None}
    else:
        params = ParamSet(cls)
        kept = {k: v for k, v in values.items() if params.check(k, v) is None}
    dropped = sorted(set(values) - set(kept))
    if dropped:
        logger.warning("%s: values %s no longer fit; using the defaults", cls.__name__, dropped)
    return kept
