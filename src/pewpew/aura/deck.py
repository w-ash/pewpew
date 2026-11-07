"""The deck: the stack that runs, and the one way to start patterns by name.

A look recall and a pick both start patterns the same way: resolve each
name in the catalog, keep the values that still fit, build fresh layers on
the crossfader's current geometry, and point each layer's reloader at its
pattern's file. `Deck.recall` does that for a whole look (a fresh stack,
faded or cut to), `Deck.put` for one layer of the running stack (a
pick), and `Deck.add` for a layer new to it; `remove` and `move` edit
the running stack's layers as they run. Each changes nothing unless every
step that can fail has passed, and its refusal names the layer, never a
path.

A pattern has two names. Its spec is what a look stores to run it again:
its pick name, or the command line's spec for a launch pattern off the
pick list (which may be a path), so a look saved from it recalls that
file. Its label is what the page, the status line and every refusal call
it: its pick name, or its class's name (`pattern_label`), never a path. A
layer that runs an effect program of more than one node shows as
`program`, and each of its pattern nodes resolves through the catalog
too.

Hot reload: one `Reloader` per layer follows the file of the pattern that
layer runs, and swaps a saved file into that layer alone. Two layers that
run one file each reload it. A layer that runs a program follows no file:
a pattern node inside a program does not reload.

Thread discipline as for the crossfader: `recall`, `put`, `add`,
`remove`, `move`, `watch` and `unwatch` belong to the loop thread;
`current`, `controls`, `reloaders`, `error` and `snapshot` are read by any
thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from pewpew.classinfo import pattern_name
from pewpew.compose import (
    Compositor,
    Controls,
    Layer,
    LayerError,
    Look,
    Resolved,
    layer_address,
    pattern_of,
    pattern_program,
)
from pewpew.crossfade import Crossfader
from pewpew.errors import Worded, describe_exception
from pewpew.fx.compile import is_pattern_program
from pewpew.fx.graph import PATTERN, Graph, Node, Program, as_id
from pewpew.fx.host import ProgramPattern, split_starts
from pewpew.load import Catalog, LoadedPattern
from pewpew.params import ParamSet
from pewpew.pattern import Pattern
from pewpew.reload import CallSoon, Reloader, Watch
from pewpew.render import SwapReport

logger = logging.getLogger(__name__)


PROGRAM = "program"  # what a layer that runs a program shows as


def pattern_label(spec: str, cls: type, names: Sequence[str]) -> str:
    """The label of the pattern `spec` starts: `spec` when it is a
    pick name, else the name of its class `cls`."""
    return spec if spec in names else pattern_name(cls)


class _LayerSwap:
    """Layer `lid` of the stack now running, as a reloader's swap target.
    During a fade that is the incoming stack."""

    def __init__(self, fader: Crossfader[Compositor], lid: str) -> None:
        self._fader = fader
        self._lid = lid

    @property
    def t(self) -> float:
        return self._fader.t

    def swap(self, pattern: Pattern) -> SwapReport:
        return self._fader.current.swap(self._lid, pattern)


class Deck:
    """The crossfader over the running stack, the catalog of names, and one
    reloader per layer."""

    def __init__(
        self,
        fader: Crossfader[Compositor],
        catalog: Catalog,
        call_soon: CallSoon,
        loaded: Mapping[str, LoadedPattern],
        *,
        watch: Watch | None = None,
    ) -> None:
        """`loaded` is the pattern each layer of the running stack runs, by
        layer id, as the launch resolved it."""
        self.fader = fader
        self.catalog = catalog
        self._call_soon = call_soon
        self._watch = watch
        self._watching = False
        # Replaced whole on the loop thread, read by sink workers.
        self._reloaders: Mapping[str, Reloader] = MappingProxyType({})
        self._follow(loaded)

    @property
    def current(self) -> str:
        """The bottom layer's pattern, by its label: never a path."""
        return self.fader.current.layers[0].label

    @property
    def controls(self) -> Controls:
        """Every knob of the running stack. A recall or a pick installs new
        controls, so read this each time; do not hold it."""
        return self.fader.current.controls

    @property
    def reloaders(self) -> Mapping[str, Reloader]:
        """The reloader of each layer of the running stack, by layer id."""
        return self._reloaders

    @property
    def error(self) -> str | None:
        """The first layer's failed reload, bottom up, prefixed by its
        address, or None: a status line source."""
        for lid, reloader in self._reloaders.items():
            if (error := reloader.error) is not None:
                return f"{layer_address(lid)}: {error}"
        return None

    def snapshot(self) -> Look:
        """The running stack as a look (`Compositor.snapshot`)."""
        return self.fader.current.snapshot()

    def watch(self) -> None:
        """Start watching every layer's pattern file, and each new layer's."""
        self._watching = True
        for reloader in self._reloaders.values():
            reloader.start()

    def unwatch(self) -> None:
        """Stop every watch, waiting for each watcher to end."""
        self._watching = False
        for reloader in self._reloaders.values():
            reloader.stop()

    def recall(self, look: Look, fade: float = 0.0) -> str | None:
        """Start `look`'s layers and signals fresh, each layer at the values
        its pattern still accepts (the rest at their defaults), fading over
        `fade` seconds or cutting at 0. A running fade ends at its target
        first, as a pick ends it. Returns why not, or None: also a route
        that reaches no knob it can move. Loop thread only."""
        try:
            resolved = [self._resolve(layer) for layer in look.layers]
            incoming = self.fader.current.spawn((r for r, _ in resolved), look)
        except (LayerError, ValueError) as exc:  # ValueError: a signal or route the stack cannot run
            # A traceback helps the author of pattern code that raised; a refusal says all there is.
            refused = not isinstance(exc, LayerError) or isinstance(exc.__cause__, Worded)
            logger.warning("cannot start the look: %s", exc, exc_info=not refused)
            return str(exc)
        if fade:
            if self.fader.fading:
                self.fader.cut(self.fader.current)
            self.fader.fade_to(incoming, fade)
        else:
            self.fader.cut(incoming)
        self._follow({r.layer.id: loaded for r, loaded in resolved})
        return None

    def put(self, lid: str, name: str) -> str | None:
        """Run pattern `name` on layer `lid` of the running stack, fresh at
        its defaults; the layer keeps its mix and the other layers run on.
        Ends a running fade, as every pick does. Returns why not, or None.
        Loop thread only."""

        def start(current: Compositor) -> dict[str, LoadedPattern]:
            layer = replace(current.layer(lid).snapshot(), program=pattern_program(as_id(name), name))
            resolved, loaded = self._resolve(layer)
            current.put(resolved)
            return {lid: loaded}

        return self._edit(start)

    def add(self, layer: Layer, index: int) -> str | None:
        """Run `layer` in the running stack, fresh, at render index `index`
        (0: the bottom); the other layers run on. Ends a running fade, as a
        pick does. Returns why not, or None. Loop thread only."""

        def start(current: Compositor) -> dict[str, LoadedPattern]:
            resolved, loaded = self._resolve(layer)
            current.insert(resolved, index)
            return {layer.id: loaded}

        return self._edit(start)

    def remove(self, lid: str) -> str | None:
        """Stop layer `lid` of the running stack; the other layers run on.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.remove(lid))

    def move(self, lid: str, index: int) -> str | None:
        """Run layer `lid` of the running stack at render index `index`.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.move(lid, index))

    def _edit(self, edit: Callable[[Compositor], Mapping[str, LoadedPattern] | None]) -> str | None:
        """Run `edit` on the running stack, then end a running fade at it
        and point the reloaders at its layers (`_follow`). `edit` returns
        the pattern each layer it starts runs, by layer id, or None when it
        starts none. Returns the reason of a LayerError or ValueError it
        raises, with the stack untouched, or None."""
        current = self.fader.current
        try:
            loaded = edit(current)
        except LayerError as exc:
            logger.warning("cannot run layer %s", exc.layer, exc_info=True)
            return str(exc)
        except ValueError as exc:  # no such layer, a layer of that id, or none left
            return str(exc)
        self.fader.cut(current)
        self._follow(loaded or {})
        return None

    def _resolve(self, layer: Layer) -> tuple[Resolved, LoadedPattern]:
        return ready_layer(layer, self.catalog.resolve, self.catalog.names)

    def _follow(self, loaded: Mapping[str, LoadedPattern]) -> None:
        """Point the reloader of each layer in `loaded` at the file of the
        pattern it now runs, a new layer getting one; keep every other
        running layer's as it is; and stop the reloader of each layer the
        running stack no longer has."""
        reloaders: dict[str, Reloader] = {}
        for live in self.fader.current.layers:
            lid, reloader = live.id, self._reloaders.get(live.id)
            if lid in loaded:
                if reloader is None:
                    reloader = Reloader(_LayerSwap(self.fader, lid), loaded[lid], self._call_soon, watch=self._watch)
                    if self._watching:
                        reloader.start()
                else:
                    reloader.follow(loaded[lid])
            if reloader is not None:
                reloaders[lid] = reloader
        for lid, reloader in self._reloaders.items():
            if lid not in reloaders:
                reloader.stop(timeout=0.0)  # told to stop, not waited for: this is the loop thread
        self._reloaders = MappingProxyType(reloaders)


def ready_layer(
    layer: Layer, resolve: Callable[[str], LoadedPattern], names: Sequence[str]
) -> tuple[Resolved, LoadedPattern]:
    """`layer` ready to build, each pattern `resolve` finds by its spec at
    the values it still accepts (`fit`), and what its reloader follows: its
    one pattern as loaded, or for a program (shown as `PROGRAM`), no file.
    `names` are the pick names a pattern shows by (`pattern_label`). Raises
    LayerError, naming the layer and no path."""
    program = layer.program
    try:
        loaded = {spec: resolve(spec) for spec in _specs(program)}
    except OSError as exc:
        raise LayerError(layer.id, "cannot read its pattern file") from exc
    except Exception as exc:  # LoadError, a raising module body, ...
        raise LayerError(layer.id, describe_exception(exc)) from exc
    classes = {spec: found.cls for spec, found in loaded.items()}
    program = _fitted(program, classes)
    if is_pattern_program(program):
        spec, _ = pattern_of(program.output)
        label = pattern_label(spec, classes[spec], names)
        return Resolved(replace(layer, program=program), classes[spec], label), loaded[spec]
    cls = ProgramPattern.of(program, classes)
    follows = LoadedPattern(cls=cls, source=None, attr=None, digest="")
    return Resolved(replace(layer, program=program), cls, PROGRAM), follows


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
