"""Layer edits as a state machine (Hypothesis): add, remove, move and switch
layers of a look, and undo each edit. After every step the look
round-trips through the looks file and through a running stack, every
layer keeps its id and, unless the edit touched it, its own picture, and
a raising layer is contained. An undo renders, fresh, exactly what the
look rendered before the edit. One stack runs all along, each edit made
to it live (`insert`, `remove`, `move`, a mix set), as a page makes it:
it is always the look, and keeps rendering."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from fakes import PixelRamp, Raises, Solid, spec
from pewpew import line
from pewpew.aura.book import LookBook, parse_looks
from pewpew.compose import MIX, Compositor, Layer, Look, Resolved, layer_address, pattern_layer
from pewpew.fx.blend import Blend
from pewpew.params import ParamSet
from pewpew.patterns import Comet, Sparkle

POOL: dict[str, type] = {"solid": Solid, "pixelramp": PixelRamp, "sparkle": Sparkle, "comet": Comet, "raises": Raises}
MAP = line(8)
MAX_LAYERS = 4


def build(look: Look) -> Compositor:
    return Compositor([Resolved(layer, POOL[spec(layer)], spec(layer)) for layer in look.layers], MAP, seed=look.seed)


class Rendered:
    """A fresh stack of a look after four frames: the frames' bytes, each
    layer's own last frame, and the stack."""

    def __init__(self, look: Look) -> None:
        self.stack = build(look)
        frames = np.stack([self.stack.advance_to(i / 30).copy() for i in range(1, 5)])
        assert frames.dtype == np.float32 and frames.shape == (4, 8, 3) and np.isfinite(frames).all()
        self.frames = frames.tobytes()
        self.own = {live.id: live.renderer.pattern.pixels.tobytes() for live in self.stack.layers}


class LayerEdits(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.look = Look((self._layer("l0", "sparkle"),), seed=7)
        self.made = 1
        self.rendered = Rendered(self.look)
        self.history: list[tuple[Look, bytes]] = []
        self.live = build(self.look)
        self.t = 0.0

    @staticmethod
    def _layer(lid: str, pattern: str, **mix: Any) -> Layer:
        return pattern_layer(lid, pattern, ParamSet(POOL[pattern]).snapshot_json(), **mix)

    def _edit(self, layers: list[Layer]) -> None:
        before, kept = self.rendered, {layer.id: layer for layer in self.look.layers}
        self.history.append((self.look, before.frames))
        self.look = replace(self.look, layers=tuple(layers))
        self.rendered = Rendered(self.look)
        for layer in self.look.layers:
            if kept.get(layer.id) == layer:  # untouched by the edit: its own picture, wherever it now sits
                assert self.rendered.own[layer.id] == before.own[layer.id], layer.id

    def _index(self, data: st.DataObject) -> int:
        return data.draw(st.integers(0, len(self.look.layers) - 1))

    @precondition(lambda self: len(self.look.layers) < MAX_LAYERS)
    @rule(pattern=st.sampled_from(sorted(POOL)), data=st.data(), blend=st.sampled_from(list(Blend)),
          opacity=st.floats(0.0, 1.0))
    def add(self, pattern: str, data: st.DataObject, blend: Blend, opacity: float) -> None:
        layers = list(self.look.layers)
        at = data.draw(st.integers(0, len(layers)))
        layer = self._layer(f"l{self.made}", pattern, blend=blend.value, opacity=opacity)
        layers.insert(at, layer)
        self.live.insert(Resolved(layer, POOL[pattern], pattern), at)
        self.made += 1
        self._edit(layers)

    @precondition(lambda self: len(self.look.layers) > 1)
    @rule(data=st.data())
    def remove(self, data: st.DataObject) -> None:
        layers = list(self.look.layers)
        self.live.remove(layers.pop(self._index(data)).id)
        self._edit(layers)

    @rule(data=st.data())
    def move(self, data: st.DataObject) -> None:
        layers = list(self.look.layers)
        layer = layers.pop(self._index(data))
        to = data.draw(st.integers(0, len(layers)))
        layers.insert(to, layer)
        self.live.move(layer.id, to)
        self._edit(layers)

    @rule(data=st.data(), enabled=st.booleans(), blend=st.sampled_from(list(Blend)))
    def switch(self, data: st.DataObject, enabled: bool, blend: Blend) -> None:
        layers = list(self.look.layers)
        i = self._index(data)
        layers[i] = replace(layers[i], enabled=enabled, blend=blend.value)
        self.live.controls.set(layer_address(layers[i].id, "enabled"), enabled)
        self.live.controls.set(layer_address(layers[i].id, "blend"), blend.value)
        self._edit(layers)

    @precondition(lambda self: self.history)
    @rule()
    def undo(self) -> None:
        self.look, frames = self.history.pop()
        self.rendered = Rendered(self.look)
        assert self.rendered.frames == frames
        self.live = build(self.look)
        self.t = 0.0

    @invariant()
    def round_trips(self) -> None:
        assert parse_looks(LookBook({"x": self.look}).to_bytes()).looks["x"] == self.look
        stack = self.rendered.stack
        assert build(self.look).snapshot() == self.look  # a running stack is the look again
        assert [live.id for live in stack.layers] == [layer.id for layer in self.look.layers]
        paths = stack.controls.snapshot_json()
        for layer in self.look.layers:
            assert {layer_address(layer.id, knob) for knob in MIX} <= paths.keys()

    @invariant()
    def the_live_stack_is_the_look(self) -> None:
        assert self.live.snapshot() == self.look
        self.t += 1 / 30
        frame = self.live.advance_to(self.t)
        assert frame.dtype == np.float32 and frame.shape == (8, 3) and np.isfinite(frame).all()

    @invariant()
    def contains_a_raising_layer(self) -> None:
        raising = [layer.id for layer in self.look.layers if spec(layer) == "raises" and layer.enabled]
        error = self.rendered.stack.error
        if raising:
            assert error is not None and error.pattern == f"layers.{raising[0]}.raises"
        else:
            assert error is None


LayerEdits.TestCase.settings = settings(stateful_step_count=12)  # max_examples: the profile's (conftest.py)
TestLayerEdits = LayerEdits.TestCase
