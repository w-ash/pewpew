"""The layer stack running: one look's layers rendered and blended into
one frame per slot.

A `Compositor` is a `pewpew.render.Live` source, so the loop, the
crossfader and a rig reload drive it as they would one `Renderer`.
Its layers run bottom to top (`layers[0]` is the bottom). Each is a full
`Renderer` that runs the layer's program bound to the map
(`pewpew.fx.bound_program.BoundProgram`), seeded by `layer_seed` from the
look's seed and its own id. The bound program is named by the layer's
address, each node's knobs by `layers.<layer>.<node>`, so the layer's
errors and refusals name it. Each frame:

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
(pewpew.sinks.sink.sanitize), so a master below 1 dims a clamped stack.
Every layer reads one feature frame per slot (`MemoFeatures`).

Containment: each layer's renderer contains its program's failures, so a
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

A running stack takes a layer in (`insert`), lets one go (`remove`) or
runs one at another place (`move`); each leaves
every other layer's renderer, buffers and seed as they are (ADR-021).

The look's colorways ride along (`colorways`), each less the addresses
that name no whole knob of the stack now, as `front` does: a colorway
left with none is gone. The active colorway (`colorway`) is not stored:
it is the first whose every value equals its knob's own value, so a
route on one of its knobs moves around that value and it stays active.

A colorway lands by `paint`, which glides: each knob's own value is the
new one at once, so the active colorway, a snapshot and a save name it
from the press on, while what its op reads moves there from what it
showed over the glide's seconds of engine time (`Bound.glide`, by the
knob's `Param.mix`): a number on a straight line, a hue the short way
round, a palette mixed per position in OKLab, a choice or a switch at
once. Each frame steps every glide before the signals run, so a route
moves around the gliding value. A paint during a glide glides on from
what shows; a set of a gliding knob, or the end of its time, lands it.

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
from typing import Any

import numpy as np

from pewpew.compose.controls import (
    Controls,
    Knob,
    LayerControls,
    Section,
    layer_address,
)
from pewpew.compose.modulation import Modulation
from pewpew.compose.stack import Colorways, Layer, Look, Route, layer_seed, stack_problems
from pewpew.errors import describe_exception, unknown
from pewpew.features import FakeFeatures, FeatureSource, memo
from pewpew.fx.blend import BLENDS, LIGHTS_BLACK, Blend
from pewpew.fx.bound_program import BoundProgram
from pewpew.fx.compile import label_of
from pewpew.fx.graph import Graph
from pewpew.mapping import dimensions
from pewpew.params.kinds import Parsed
from pewpew.render import Renderer, RenderFailure, error_frame

logger = logging.getLogger(__name__)


class LayerError(Exception):
    """A layer that cannot be built: binding its program raises. The message starts with the layer's address and
    names no path; `layer` is its id and `reason` why. It pickles, so it crosses a process pool."""

    def __init__(self, lid: str, reason: str) -> None:
        super().__init__(f"{layer_address(lid)}: {reason}")
        self.layer = lid
        self.reason = reason

    def __reduce__(self) -> tuple[type[LayerError], tuple[str, str]]:
        return type(self), (self.layer, self.reason)


@dataclass(frozen=True, slots=True, eq=False)
class _Glide:
    """One knob gliding (`Compositor.paint`): the knob, where it started,
    the own value it glides to, and the engine time and seconds it takes."""

    knob: Knob
    start: Any
    end: Any
    t0: float
    seconds: float


@dataclass(frozen=True, slots=True, eq=False)
class LiveLayer:
    """One running layer: its value as built, its renderer, and its live
    mix."""

    layer: Layer
    renderer: Renderer
    mix: LayerControls

    @property
    def id(self) -> str:
        return self.layer.id

    @property
    def bound(self) -> BoundProgram:
        """The program the layer's renderer runs, bound to the map."""
        return self.renderer.bound

    @property
    def masked(self) -> bool:
        """Whether the layer's program masks it (`alpha`)."""
        return self.layer.program.alpha is not None

    def sections(self) -> list[Section]:
        """The layer's knob sets: each node's, then its mix."""
        knobs = [Section(params, self.id, nid) for nid, params in self.bound.node_params.items()]
        return [*knobs, Section(self.mix.params, self.id, "")]

    def nodes(self) -> list[dict[str, Any]]:
        """Each node the layer runs: its id, op, the label it shows, and
        the ids of the nodes it reads (`in`)."""
        return [{"id": n.id, "op": n.op, "label": label_of(n), "in": list(n.inputs)} for n in self.layer.program.graph]

    def snapshot(self) -> Layer:
        """The layer as a value now: its program at the live knob values,
        and its live mix."""
        return replace(self.layer, program=self.bound.snapshot(), **self.mix.params.snapshot())

    def weight(self) -> float | np.ndarray:
        """What the layer's last frame blends in by: its opacity, times its
        mask per pixel when it has one ((N, 1) float32)."""
        alpha, opacity = self.bound.alpha, self.mix.opacity
        if alpha is None:
            return opacity
        return (alpha * np.float32(opacity))[:, None]


class Compositor:
    """One look's layers, rendered and blended per slot (module docstring)."""

    def __init__(
        self,
        layers: Iterable[Layer],
        mapping: np.ndarray,
        *,
        seed: int = 0,
        signals: Graph | None = None,
        routes: Iterable[Route] = (),
        front: Iterable[str] = (),
        colorways: Colorways | None = None,
        features: FeatureSource | None = None,
        bypass: bool = False,
        now: Callable[[], float] | None = None,
        t: float = 0.0,
    ) -> None:
        """Build every layer of `layers` on `mapping`, at engine time `t`,
        with the look's `signals`, `routes` and `front`
        (pewpew.compose.modulation) and its `colorways`, unchecked. `features` is as for `Renderer`; the
        default features are the seeded fake. Raises
        LayerError for a layer that cannot be built, ValueError for no
        layers or a repeated id (`stack_problems`), a signal's value its
        knob refuses, or a route `route_problems` refuses, and TypeError for
        a signal whose op is not a signal op. A `front` path that names no
        whole knob is left out."""
        self._seed = seed
        self._colorways = {name: dict(values) for name, values in (colorways or {}).items()}
        self._modulation = Modulation(signals, tuple(routes), tuple(front), seed)
        self._features = memo(FakeFeatures(seed) if features is None else features)
        self._bypass = bypass
        self._now = now
        self._t = float(t)
        self._unbound: set[str] = set()
        self._timings: Mapping[str, float] = {}
        self._glides: dict[str, _Glide] = {}
        self._live_colorways: Colorways = {}
        # Each live colorway's knobs with their values, and the active
        # colorway as last found, with the own values it was found at.
        self._colorway_knobs: tuple[tuple[str, tuple[tuple[Knob, Any], ...]], ...] = ()
        self._active: tuple[tuple[Any, ...], tuple[Any, ...], str | None] | None = None
        self._bind(mapping)
        self._install(tuple(self._build(layer) for layer in layers), strict=True)

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
    def error(self) -> RenderFailure | None:
        """The first enabled layer's contained failure, bottom up, else a
        signal's (pewpew.compose.modulation), or None."""
        for live in self._layers:
            if live.mix.enabled and (err := live.renderer.error) is not None:
                return err
        return self._modulation.error

    @property
    def colorways(self) -> Colorways:
        """The look's colorways, each less the addresses that name no whole
        knob of the stack now (module docstring)."""
        return self._live_colorways

    def colorway_sets(self, name: object) -> Parsed[list[tuple[str, Knob, Any]]]:
        """Each knob colorway `name` sets, by address, with the value
        parsed as `Controls.parse` parses one (`paint` takes them), or why
        not: a name that is no colorway of the stack, with the closest, or
        a value its knob refuses, named `colorway '<name>'`. Never raises;
        any thread."""
        colorways, controls = self._live_colorways, self._controls
        if not isinstance(name, str) or name not in colorways:
            return None, unknown("colorway", name, colorways, suggest=True)
        sets: list[tuple[str, Knob, Any]] = []
        for path, value in colorways[name].items():
            found, reason = controls.parse(path, value)
            if reason is not None:
                return None, f"colorway {name!r}: {reason}"
            assert found is not None
            sets.append((path, *found))
        return sets, None

    def colorway(self) -> str | None:
        """The active colorway, or None (module docstring). Found again
        only when a knob a colorway sets holds another value object."""
        knobs = self._colorway_knobs
        own = tuple(knob.params[knob.name] for _, pairs in knobs for knob, _ in pairs)
        held = self._active
        if held is not None and held[0] is knobs and all(a is b for a, b in zip(held[1], own, strict=True)):
            return held[2]
        name = next((name for name, pairs in knobs if all(
            knob.params.declarations[knob.name].to_json(knob.params[knob.name]) == value for knob, value in pairs)),
            None)
        self._active = (knobs, own, name)
        return name

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
        the routes that run, the front knobs, the colorways, and the seed."""
        signals, routes, front = self._modulation.snapshot()
        layers = tuple(live.snapshot() for live in self._layers)
        return Look(layers, signals, routes, seed=self._seed, front=front, colorways=self._live_colorways)

    def state(self) -> dict[str, Any]:
        """The stack for a page: each layer's id and nodes (id, op, the label
        it shows, and what it reads), the signals (the same), the routes that run,
        the front knobs, the colorways' names in the look's order and the
        active one, and the mapping's dimensions. JSON-ready, names only."""
        return {
            "layers": [{"id": live.id, "nodes": live.nodes()} for live in self._layers],
            **self._modulation.state(),
            "colorways": list(self._live_colorways),
            "colorway": self.colorway(),
            "dims": self._dims,
        }

    # ---- building (loop thread) -------------------------------------------

    def spawn(self, look: Look) -> Compositor:
        """A new stack of `look`'s layers, seed, signals, routes, front and
        colorways, on this one's mapping, features and `bypass`, at
        its engine time: the incoming side of a recall. Fresh state: a
        recalled look renders the same whatever ran before it. Raises as
        the constructor does, with this stack untouched."""
        return Compositor(
            look.layers, self._mapping, seed=look.seed, signals=look.signals, routes=look.routes, front=look.front,
            colorways=look.colorways, features=self._features, bypass=self._bypass, now=self._now, t=self._t,
        )

    def insert(self, layer: Layer, index: int) -> None:
        """Build `layer` fresh, with its own mix, at this stack's
        engine time, and run it at render index `index` (0: the bottom,
        `len(layers)`: the top). The other layers run on. Raises
        LayerError, or ValueError for an id the stack has, with the stack
        untouched."""
        self._install(self._layers[:index] + (self._build(layer),) + self._layers[index:])

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

    def paint(self, sets: Iterable[tuple[str, Knob, Any]], seconds: float) -> None:
        """Set each knob of `sets`, `(address, knob, value)` as
        `Controls.parse` gives them, gliding over `seconds` of engine time
        (0: at once; module docstring). A knob that no longer runs here is
        passed over, with the reason in the log. Loop thread only."""
        for path, knob, value in sets:
            found = self._controls.find(path)
            if found is None or found.params is not knob.params:
                logger.warning("dropped a colorway's set of %r: the node it was for no longer runs", path)
                continue
            bound, name = knob.params.bound, knob.name
            start = bound.shown(name) if bound is not None else None
            try:
                knob.params.set(name, value)
            except ValueError:
                logger.warning("dropped a colorway's set of %r to %r: the param no longer accepts it", path, value)
                continue
            end = knob.params[name]
            if bound is None or seconds <= 0 or start == end or not knob.params.declarations[name].glides:
                # The set landed it. The binding lets go of its glide too: it knows the
                # base it glides to by identity, and a set of an equal value may store the same object.
                if self._glides.pop(path, None) is not None and bound is not None:
                    bound.unglide(name)
                continue
            self._glides[path] = _Glide(knob, start, end, self._t, float(seconds))
            bound.glide(name, start, 0.0)

    def gliding(self) -> list[str]:
        """The address of each knob that glides now. Loop thread only."""
        return list(self._glides)

    def set_front(self, front: Sequence[str]) -> str | None:
        """Show the knobs `front` names first (`Modulation.set_front`).
        Returns why not, or None. Loop thread only."""
        return self._modulation.set_front(front, self._controls)

    def rebind(self, mapping: np.ndarray) -> None:
        """Rebind every layer to a new mapping. Every layer tries, also after one raises, so each ends bound to
        this stack's mapping or unbound, never on another one. Raises what
        the first failing layer's `Renderer.rebind` raised; the caller binds
        the old mapping again (pewpew.room.live)."""
        self._bind(mapping)
        first: Exception | None = None
        for live in self._layers:
            try:
                live.renderer.rebind(mapping)
            except Exception as exc:  # noqa: BLE001  raised below, once every layer has tried
                first = first or exc
        if first is not None:
            raise first

    def _bind(self, mapping: np.ndarray) -> None:
        self._mapping = mapping
        self._n = len(mapping)
        self._dims = dimensions(mapping)
        self._acc = np.zeros((self._n, 3), dtype=np.float32)
        self._scratch = np.zeros((self._n, 3), dtype=np.float32)
        self._below = self._acc.view()  # what a program's below() reads: the stack blended so far
        self._below.setflags(write=False)

    def _build(self, layer: Layer, mix: LayerControls | None = None) -> LiveLayer:
        """`layer` running, with `mix`, or a new mix from its values."""
        try:
            renderer = Renderer(
                BoundProgram(layer.program, layer_address(layer.id)), self._mapping,
                seed=layer_seed(self._seed, layer.id), features=self._features, t=self._t,
            )
        except Exception as exc:
            raise LayerError(layer.id, describe_exception(exc)) from exc
        return LiveLayer(layer, renderer, LayerControls(layer.id, layer.mix) if mix is None else mix)

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
        whole = {path: knob for values in self._colorways.values() for path in values
                 if (knob := _whole(controls, path)) is not None}
        live = ({path: value for path, value in values.items() if path in whole} for values in self._colorways.values())
        self._live_colorways = {name: values for name, values in zip(self._colorways, live, strict=True) if values}
        self._colorway_knobs = tuple((name, tuple((whole[path], value) for path, value in values.items()))
                                     for name, values in self._live_colorways.items())

    # ---- the frame path ------------------------------------------------------

    def advance_to(self, t: float) -> np.ndarray:
        """Render the frame at engine time `t` (the module docstring)."""
        prev, t = self._t, float(t)
        if t < prev:
            raise ValueError(f"time never goes backwards: advance_to({t!r}) is before the current t={prev!r}")
        self._t = t
        if self._glides:
            self._glide(t)
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

    def _glide(self, t: float) -> None:
        """Move each glide to engine time `t`; land one whose time is up,
        whose knob was set since or no longer runs."""
        for path, glide in list(self._glides.items()):
            knob = glide.knob
            bound, w = knob.params.bound, (t - glide.t0) / glide.seconds
            found = self._controls.find(path)
            if bound is not None and w < 1.0 and found is not None and found.params is knob.params \
                    and knob.params[knob.name] is glide.end:
                bound.glide(knob.name, glide.start, w)
                continue
            del self._glides[path]
            if bound is not None:
                bound.unglide(knob.name)

    def error_frame(self, t: float) -> np.ndarray:
        """The pulsing-red frame at engine time `t`, one row per pixel."""
        return error_frame(self._n, t)

    def _render(self, live: LiveLayer, t: float, timings: dict[str, float]) -> tuple[np.ndarray, bool]:
        """Layer `live`'s frame at `t`, and whether it rendered without failing."""
        start = self._now() if self._now is not None else 0.0
        live.bound.below = self._below
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


def _whole(controls: Controls, path: str) -> Knob | None:
    """The whole knob at `path` among `controls`, or None when `path`
    names none or names a part."""
    knob = controls.find(path)
    return knob if knob is not None and not knob.part else None
