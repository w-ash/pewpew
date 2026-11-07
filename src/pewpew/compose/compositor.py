"""The layer stack running: one look's layers rendered and blended into
one frame per slot.

A `Compositor` is a `pewpew.render.Live` source, so the loop, the
crossfader and a room map reload drive it as they would one `Renderer`.
Its layers run bottom to top (`layers[0]` is the bottom). Each is a full
`Renderer`, seeded by `layer_seed` from the look's seed and its own id. A
layer of one pattern node runs that pattern directly, its renderer named
by the node's address (`layers.<layer>.<node>`); any other program runs in
a `pewpew.fx.host.ProgramPattern`, its renderer named by the layer's
address, each node's knobs by `layers.<layer>.<node>`. A pattern that is
a program (a `ProgramPattern` file) is named as a program is, so its
nodes' knobs are the layer's. Either way the layer's errors and refusals
name it. Each frame:

1. The look's signals run, and its routes move their knobs
   (pewpew.compose.modulation): the modulation seat, before any layer.
2. Each enabled layer advances, reading the accumulator so far as the
   frame below it (a program's `below()`), then blends into the
   compositor's own accumulator with its blend mode and its opacity, times
   its program's mask where it has one (pewpew.fx.blend). A layer's frame
   is never written. A disabled layer is not advanced; when it is enabled
   again, its renderer resumes at the previous frame's time, so its first
   dt is one slot, not the time it was off (ADR-021).
3. The accumulator is clamped to 0..1, once.

One enabled layer at normal blend, opacity 1 and no mask is the identity:
its frame is returned as its renderer gave it, unclamped, so a one-layer
stack is byte for byte its renderer. The sinks clip every frame
(pewpew.sinks.base.sanitize), so a master below 1 dims a clamped stack.
Every layer reads one feature frame per slot (`MemoFeatures`).

Containment: each layer's renderer contains its pattern's failures, so a
raising layer shows its pulsing-red frame in its place (a layer left
unbound by a failed map reload shows it too). With `bypass` (an unattended run),
a failing layer is left out of the blend instead, while another layer
still lights the room; `error` still names it for the status line. When
the bypass leaves no layer whose blend lights black (`LIGHTS_BLACK`: a
multiply over nothing is black too) at an opacity above 0, the frame is
the error frame, never a dark room. The opacity read is the knob's own
value, never a route's, so a route never switches the error frame on and
off. Building a layer is loud: `LayerError` names the layer. A
signal that raises holds its last value and is the stack's `error` after
its layers' (named `signals.<sid>`), while the stack renders on.

A running stack takes a layer in (`insert`), lets one go (`remove`), runs
one at another place (`move`) or swaps one's program (`put`); each leaves
every other layer's renderer, buffers and seed as they are (ADR-021).

`now` (a clock, injected as `pewpew.pace.PacedLoop` takes it) times each
layer's frame into `timings`. Timing never reaches a frame.

The frame `advance_to` returns is valid until the next call, as a
renderer's is: a caller that keeps frames copies them. Thread discipline as
for `Renderer`; `layers`, `controls`, `error`, `state`, `mod` and
`snapshot` may be read from any thread, and each is replaced whole, never
changed in place.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, NamedTuple, cast

import numpy as np

from pewpew.compose.controls import (
    Controls,
    LayerControls,
    Section,
    layer_address,
    layer_sections,
    signal_sections,
)
from pewpew.compose.modulation import Modulation
from pewpew.compose.stack import Layer, Look, Route, layer_seed, pattern_of, pattern_program, stack_problems
from pewpew.errors import describe_exception, unknown
from pewpew.features import FakeFeatures, FeatureSource, memo
from pewpew.fx.blend import BLENDS, LIGHTS_BLACK, Blend
from pewpew.fx.compile import is_pattern_program, label_of
from pewpew.fx.graph import Graph
from pewpew.fx.host import ProgramPattern, split_starts
from pewpew.fx.op import Resolve
from pewpew.mapping import Grouping, dimensions
from pewpew.pattern import Pattern
from pewpew.render import PatternError, Renderer, SwapReport, error_frame

logger = logging.getLogger(__name__)


class LayerError(Exception):
    """A layer that cannot be built: its pattern does not resolve or load,
    or binding it raises. The message starts with the layer's address and
    names no path; `layer` is its id."""

    def __init__(self, lid: str, reason: str) -> None:
        super().__init__(f"{layer_address(lid)}: {reason}")
        self.layer = lid


class Resolved(NamedTuple):
    """A layer ready to build: its value, the class its renderer runs (its
    one pattern node's, or a `ProgramPattern` of its program), and the name
    the page shows for it, never a path."""

    layer: Layer
    cls: type[Pattern]
    label: str

    @property
    def resolve(self) -> Resolve:
        """The class each pattern node of the layer runs, by spec: its one
        pattern's, or what its program's class resolves."""
        if is_pattern_program(self.layer.program):
            return lambda spec: self.cls
        return cast("type[ProgramPattern]", self.cls).resolve


def controls_of(layers: Iterable[Resolved], signals: Graph | None = None) -> Controls:
    """The knobs of a stack of `layers` and `signals`, as a stack built
    from them holds them, at their defaults but the signals', with nothing
    built: to check an address or a value before the stack runs, never to
    read one (pewpew.compose.controls.layer_sections). Raises ValueError
    for a signal's value its knob refuses."""
    sections = [section for resolved in layers for section in layer_sections(resolved.layer, resolved.resolve)]
    return Controls.of([*sections, *signal_sections(signals)])


@dataclass(frozen=True, slots=True, eq=False)
class LiveLayer:
    """One running layer: its value as built, the name it shows by, its
    renderer, and its live mix."""

    layer: Layer
    label: str
    renderer: Renderer
    mix: LayerControls

    @property
    def id(self) -> str:
        return self.layer.id

    @property
    def host(self) -> ProgramPattern | None:
        """The program the layer's renderer runs, or None for a pattern."""
        pattern = self.renderer.pattern
        return pattern if isinstance(pattern, ProgramPattern) else None

    @property
    def masked(self) -> bool:
        """Whether the layer's program masks it (`alpha`)."""
        host = self.host
        return host is not None and host.runs().alpha is not None

    def sections(self) -> list[Section]:
        """The layer's knob sets: each node's, then its mix."""
        host = self.host
        if host is None:
            knobs = [Section(self.renderer.params, self.id, self.layer.program.out)]
        else:
            knobs = [Section(params, self.id, nid) for nid, params in host.node_params.items()]
        return [*knobs, Section(self.mix.params, self.id, "")]

    def nodes(self) -> list[dict[str, Any]]:
        """Each node the layer runs: its id, op, the label it shows, and
        the ids of the nodes it reads (`in`)."""
        host = self.host
        if host is None:
            node = self.layer.program.output
            return [{"id": node.id, "op": node.op, "label": self.label, "in": []}]
        return [{"id": n.id, "op": n.op, "label": label_of(n, host.resolve), "in": list(n.inputs)}
                for n in host.runs().graph]

    def snapshot(self) -> Layer:
        """The layer as a value now: its program at the live knob values,
        and its live mix. A layer that runs a pattern file whose class is a
        program keeps its pattern node, the file's literals its content,
        with each knob moved from its literal as `<nid>.<arg>`
        (pewpew.fx.host)."""
        program, host = self.layer.program, self.host
        if not is_pattern_program(program):
            assert host is not None  # a program of more than one node runs hosted
            program = host.snapshot()
        else:
            spec, _ = pattern_of(program.output)
            moved = host.moved() if host is not None else {}
            program = pattern_program(program.out, spec, {**self.renderer.params.snapshot_json(), **moved})
        return replace(self.layer, program=program, **self.mix.params.snapshot())

    def weight(self) -> float | np.ndarray:
        """What the layer's last frame blends in by: its opacity, times its
        mask per pixel when it has one ((N, 1) float32)."""
        host, opacity = self.host, self.mix.opacity
        alpha = host.alpha if host is not None else None
        if alpha is None:
            return opacity
        if self.renderer.units == "fixture":
            alpha = alpha[self.renderer.gather]
        return (alpha * np.float32(opacity))[:, None]


class Compositor:
    """One look's layers, rendered and blended per slot (module docstring)."""

    def __init__(
        self,
        layers: Iterable[Resolved],
        mapping: np.ndarray,
        *,
        seed: int = 0,
        signals: Graph | None = None,
        routes: Iterable[Route] = (),
        front: Iterable[str] = (),
        features: FeatureSource | None = None,
        grouping: Grouping | None = None,
        units: str | None = None,
        bypass: bool = False,
        now: Callable[[], float] | None = None,
        t: float = 0.0,
    ) -> None:
        """Build every layer of `layers` on `mapping`, at engine time `t`,
        with the look's `signals`, `routes` and `front`
        (pewpew.compose.modulation). `features`, `grouping` and `units` are
        as for `Renderer`; the default features are the seeded fake. Raises
        LayerError for a layer that cannot be built, ValueError for no
        layers or a repeated id (`stack_problems`), a signal's value its
        knob refuses, or a route `route_problems` refuses, and TypeError for
        a signal whose op is not a signal op. A `front` path that names no
        whole knob is left out."""
        self._seed = seed
        self._modulation = Modulation(signals, tuple(routes), tuple(front), seed)
        self._features = memo(FakeFeatures(seed) if features is None else features)
        self._units = units
        self._bypass = bypass
        self._now = now
        self._t = float(t)
        self._unbound: set[str] = set()
        self._timings: Mapping[str, float] = {}
        self._bind(mapping, grouping)
        self._install(tuple(self._build(resolved) for resolved in layers), strict=True)

    # ---- state (any thread) ---------------------------------------------

    @property
    def t(self) -> float:
        """Engine time of the most recent frame, in seconds."""
        return self._t

    @property
    def seed(self) -> int:
        """The look's seed, which each layer's is derived from."""
        return self._seed

    @property
    def dims(self) -> int:
        """How many axes the mapping spans (pewpew.mapping.dimensions)."""
        return self._dims

    @property
    def mapping(self) -> np.ndarray:
        """The points the stack renders at, (N, 3)."""
        return self._mapping

    @property
    def grouping(self) -> Grouping | None:
        """The points' fixture grouping, or None."""
        return self._grouping

    @property
    def layers(self) -> tuple[LiveLayer, ...]:
        """The running layers, bottom to top."""
        return self._layers

    @property
    def controls(self) -> Controls:
        """Every knob of the stack, by address. Replaced when a layer is."""
        return self._controls

    @property
    def timings(self) -> Mapping[str, float]:
        """Seconds each layer's last frame took, by layer id; empty without
        a `now` clock."""
        return self._timings

    @property
    def error(self) -> PatternError | None:
        """The first enabled layer's contained failure, bottom up, else a
        signal's (pewpew.compose.modulation), or None."""
        for live in self._layers:
            if live.mix.enabled and (err := live.renderer.error) is not None:
                return err
        return self._modulation.error

    def mod(self) -> Mapping[str, float]:
        """Each knob a route drives, at its value as of the last frame, by
        address: the page's live readout."""
        return self._modulation.values()

    def layer(self, lid: str) -> LiveLayer:
        """The running layer `lid`. Raises ValueError for another id."""
        for live in self._layers:
            if live.id == lid:
                return live
        raise ValueError(unknown("layer", lid, [live.id for live in self._layers]))

    def snapshot(self) -> Look:
        """The stack as a look: each layer and signal at its live values,
        the routes that run, the front knobs, and the seed."""
        signals, routes, front = self._modulation.snapshot()
        layers = tuple(live.snapshot() for live in self._layers)
        return Look(layers, signals, routes, seed=self._seed, front=front)

    def state(self) -> dict[str, Any]:
        """The stack for a page: each layer's id and nodes (id, op, the label
        it shows, and what it reads), the signals (the same), the routes that run,
        the front knobs, and the mapping's dimensions. JSON-ready, names
        only."""
        return {
            "layers": [{"id": live.id, "nodes": live.nodes()} for live in self._layers],
            **self._modulation.state(),
            "dims": self._dims,
        }

    # ---- building (loop thread) -------------------------------------------

    def spawn(self, layers: Iterable[Resolved], look: Look) -> Compositor:
        """A new stack of `layers` with `look`'s seed, signals, routes and
        front, on this one's mapping, features, `units` and `bypass`, at
        its engine time: the incoming side of a recall. Fresh state: a
        recalled look renders the same whatever ran before it. Raises as
        the constructor does, with this stack untouched."""
        return Compositor(
            layers, self._mapping, seed=look.seed, signals=look.signals, routes=look.routes, front=look.front,
            features=self._features, grouping=self._grouping, units=self._units, bypass=self._bypass,
            now=self._now, t=self._t,
        )

    def put(self, resolved: Resolved) -> None:
        """Replace the program of layer `resolved.layer.id` with a fresh
        build of it, at this stack's engine time. The layer keeps its
        running mix, the same `LayerControls`, so a set queued for it still
        lands; `resolved.layer`'s own mix is not read. The other layers run
        on, and a route into a knob the new program lacks rests. Raises
        LayerError, or ValueError for an id the stack has not, with the
        stack untouched."""
        old = self.layer(resolved.layer.id)
        index = self._layers.index(old)
        live = self._build(resolved, old.mix)
        self._install(self._layers[:index] + (live,) + self._layers[index + 1:])

    def insert(self, resolved: Resolved, index: int) -> None:
        """Build layer `resolved` fresh, with its own mix, at this stack's
        engine time, and run it at render index `index` (0: the bottom,
        `len(layers)`: the top). The other layers run on. Raises
        LayerError, or ValueError for an id the stack has, with the stack
        untouched."""
        self._install(self._layers[:index] + (self._build(resolved),) + self._layers[index:])

    def remove(self, lid: str) -> None:
        """Stop running layer `lid`. The other layers run on, and a route
        into its knobs rests. Raises ValueError for an id the stack has
        not, or for its last layer, with the stack untouched."""
        gone = self.layer(lid)
        self._install(tuple(live for live in self._layers if live is not gone))
        self._unbound.discard(lid)

    def move(self, lid: str, index: int) -> None:
        """Run layer `lid`, as it runs, at render index `index` among the
        layers (0: the bottom). Raises ValueError for an id the stack has
        not."""
        moved = self.layer(lid)
        rest = tuple(live for live in self._layers if live is not moved)
        self._install(rest[:index] + (moved,) + rest[index:])

    def set_front(self, front: Sequence[str]) -> str | None:
        """Show the knobs `front` names first (`Modulation.set_front`).
        Returns why not, or None. Loop thread only."""
        return self._modulation.set_front(front, self._controls)

    def swap(self, lid: str, pattern: Pattern) -> SwapReport:
        """Hot-reload layer `lid`'s pattern (`Renderer.swap`), and find each
        route's knob anew: a pattern keeps its set, whose declarations may
        change; a program's nodes may change, so its knobs are installed
        again. Raises ValueError, with the layer untouched, for a pattern
        that becomes a program or a program that becomes a pattern: its
        knobs would change address, so that takes a restart."""
        live = self.layer(lid)
        if isinstance(pattern, ProgramPattern) != (live.host is not None):
            raise ValueError("a pattern file that turns into a program, or back, takes a restart")
        self._check_units(type(pattern))
        report = live.renderer.swap(pattern)
        if live.host is not None:
            self._install(self._layers)
        else:
            self._modulation.bind(self._controls)
        return report

    def rebind(self, mapping: np.ndarray, grouping: Grouping | None = None) -> None:
        """Rebind every layer to a new mapping and its fixture grouping.
        Every layer tries, also after one raises, so each ends bound to
        this stack's mapping or unbound, never on another one. Raises what
        the first failing layer's `Renderer.rebind` raised; the caller binds
        the old mapping again (pewpew.room.live)."""
        self._bind(mapping, grouping)
        first: Exception | None = None
        for live in self._layers:
            try:
                live.renderer.rebind(mapping, grouping)
            except Exception as exc:  # noqa: BLE001  raised below, once every layer has tried
                first = first or exc
        if first is not None:
            raise first

    def _bind(self, mapping: np.ndarray, grouping: Grouping | None) -> None:
        self._mapping = mapping
        self._grouping = grouping
        self._n = len(mapping)
        self._dims = dimensions(mapping)
        self._acc = np.zeros((self._n, 3), dtype=np.float32)
        self._scratch = np.zeros((self._n, 3), dtype=np.float32)
        self._below = self._acc.view()  # what a program's below() reads: the stack blended so far
        self._below.setflags(write=False)

    def _build(self, resolved: Resolved, mix: LayerControls | None = None) -> LiveLayer:
        """`resolved` running, with `mix`, or a new mix from its layer's values."""
        layer, cls = resolved.layer, resolved.cls
        try:
            program = layer.program
            direct = is_pattern_program(program)
            hosted = issubclass(cls, ProgramPattern)
            if not direct and not hosted:
                raise ValueError("a program other than one pattern node runs in its own class, "
                                 "pewpew.fx.host.ProgramPattern.of(program)")
            self._check_units(cls)
            params, pattern = None, None
            if direct and hosted:  # a pattern file whose class is a program: the look's moved knobs start it
                params, starts = split_starts(pattern_of(program.output)[1])
                pattern = cast("type[ProgramPattern]", cls)(starts)
            elif direct:
                params = pattern_of(program.output)[1]
            renderer = Renderer(
                pattern or cls(), self._mapping, params=params, seed=layer_seed(self._seed, layer.id),
                features=self._features, grouping=self._grouping, units=self._units,
                name=layer_address(layer.id) if hosted else layer_address(layer.id, program.out), t=self._t,
            )
        except Exception as exc:
            raise LayerError(layer.id, describe_exception(exc)) from exc
        return LiveLayer(layer, resolved.label, renderer, LayerControls(layer.id, layer.mix) if mix is None else mix)

    def _check_units(self, cls: type[Pattern]) -> None:
        """Raise ValueError for a program that reads below() set to render
        per fixture: the frame below has one row per pixel."""
        if self._units == "fixture" and issubclass(cls, ProgramPattern) and any(
            node.op == "below" for node in cls.runs().graph
        ):
            raise ValueError("a program that reads below() runs per pixel, never per fixture")

    def _install(self, layers: tuple[LiveLayer, ...], *, strict: bool = False) -> None:
        """Run `layers`, their knobs and the signals' as the stack's
        controls, each route bound to its knob (`Modulation.bind`; with
        `strict`, a route that cannot bind raises ValueError first). Raises
        ValueError, with the stack untouched, for no layers or a repeated id
        (`stack_problems`)."""
        if problems := stack_problems([live.id for live in layers]):
            raise ValueError("; ".join(problems))
        controls = Controls.of([*(section for live in layers for section in live.sections()),
                                *self._modulation.sections()])
        self._modulation.bind(controls, strict=strict)
        self._layers = layers
        self._controls = controls

    # ---- the frame path ------------------------------------------------------

    def advance_to(self, t: float) -> np.ndarray:
        """Render the frame at engine time `t` (the module docstring)."""
        prev, t = self._t, float(t)
        if t < prev:
            raise ValueError(f"time never goes backwards: advance_to({t!r}) is before the current t={prev!r}")
        self._t = t
        self._modulation.advance(t, t - prev, self._features)
        on = [live for live in self._layers if live.mix.enabled]
        for live in on:
            if live.renderer.t < prev:  # enabled again since its last frame
                live.renderer.resume_at(prev)
        timings: dict[str, float] = {}
        acc, scratch = self._acc, self._scratch
        acc.fill(0.0)  # the bottom layer's below() is black
        try:
            if len(on) == 1 and on[0].mix.blend == Blend.NORMAL and on[0].mix.opacity == 1.0 and not on[0].masked:
                return self._render(on[0], t, timings)[0]
            bypassed = lit = False
            for live in on:
                frame, ok = self._render(live, t, timings)
                if ok or not self._bypass:
                    weight = live.weight() if ok else live.mix.opacity  # a failing layer's mask is stale
                    BLENDS[live.mix.blend](acc, frame, weight, scratch)
                    lit = lit or (live.mix.blend in LIGHTS_BLACK and live.mix.params["opacity"] > 0)
                else:
                    bypassed = True
            if bypassed and not lit:
                return error_frame(self._n, t)  # the bypass left the room dark: show the failure
            np.clip(acc, 0.0, 1.0, out=acc)
            return acc
        finally:
            if self._now is not None:
                self._timings = timings

    def error_frame(self, t: float) -> np.ndarray:
        """The pulsing-red frame at engine time `t`, one row per pixel."""
        return error_frame(self._n, t)

    def _render(self, live: LiveLayer, t: float, timings: dict[str, float]) -> tuple[np.ndarray, bool]:
        """Layer `live`'s frame at `t`, and whether it rendered without failing."""
        start = self._now() if self._now is not None else 0.0
        if (host := live.host) is not None:
            host.below = self._below
        try:
            frame = live.renderer.advance_to(t)
        except RuntimeError:
            # Unbound: its setup raised on the last rebind. The failed map
            # reload keeps the status line red; logged once per layer.
            if live.id not in self._unbound:
                self._unbound.add(live.id)
                logger.exception("layer %s is not bound; showing its error frame", live.id)
            return error_frame(self._n, t), False
        finally:
            if self._now is not None:
                timings[live.id] = self._now() - start
        self._unbound.discard(live.id)
        return frame, live.renderer.error is None
