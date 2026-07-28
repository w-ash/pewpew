"""Engine-managed private state buffers (ADR-005 amendment 2026-07-27).

The properties under test are the ones the amendment makes the engine
responsible for: declare-in-`setup` only, zero on bind, reallocate and
re-zero on mapping change, track a buffer by name (not by array identity) so
the rebinding idiom keeps working, and hand `render` read-only views so it
stays pure — the property golden frames and determinism rest on (§8).
"""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Param, Pattern, Renderer, line


class Buffered(Pattern):
    """Declares both buffer flavours: per-pixel (N,) and an internal field."""

    name = "buffered"
    decay = Param(0.1, 0.0, 1.0, "Decay")

    def setup(self, n, x, y, z, index):
        self.trail = self.buffer("trail", n)
        self.field = self.buffer("field", (4, 3))
        # Probes; plain instance state, deliberately not buffers.
        self.first_trail = self.trail
        self.writeable_in_before: list[tuple[bool, bool]] = []
        self.writeable_in_render: list[tuple[bool, bool]] = []
        self.rebound_in_render: list[bool] = []

    def before_render(self, dt, features):
        self.writeable_in_before.append((self.trail.flags.writeable, self.pixels.flags.writeable))
        # The fire/geq idiom: rebind to a brand-new array rather than mutate.
        self.trail = np.clip(self.trail - self.decay, 0.0, 1.0) + 0.25
        self.field[0, 0] += 1.0  # in-place is equally fine here

    def render(self, x, y, z, index):
        self.writeable_in_render.append((self.trail.flags.writeable, self.pixels.flags.writeable))
        self.rebound_in_render.append(self.trail is not self.first_trail)
        v = np.clip(self.trail, 0.0, 1.0).astype(np.float32)
        return np.stack([v, v, v], axis=1).astype(np.float32)


def test_buffers_are_declared_zeroed_and_reachable() -> None:
    pattern = Buffered()
    Renderer(pattern, line(6))

    assert pattern.trail.shape == (6,) and pattern.trail.dtype == np.float32
    assert pattern.field.shape == (4, 3)
    assert not pattern.trail.any() and not pattern.field.any()
    # self.pixels is just the engine's own entry in the same registry.
    assert pattern.pixels.shape == (6, 3) and not pattern.pixels.any()


def test_buffer_honours_dtype_and_fill() -> None:
    class Typed(Pattern):
        name = "typed"

        def setup(self, n, x, y, z, index):
            self.hits = self.buffer("hits", n, dtype=np.int32)
            self.warm = self.buffer("warm", (2, 2), fill=0.5)

        def render(self, x, y, z, index):
            return np.zeros((index.size, 3), dtype=np.float32)

    pattern = Typed()
    Renderer(pattern, line(3))
    assert pattern.hits.dtype == np.int32 and not pattern.hits.any()
    assert np.all(pattern.warm == 0.5)


def test_rebind_reallocates_and_rezeros() -> None:
    renderer = Renderer(Buffered(), line(6))
    renderer.step(1.0 / 60.0)
    pattern = renderer.pattern
    assert pattern.trail.any() and pattern.field.any()  # state accumulated

    renderer.rebind(line(11))

    assert pattern.trail.shape == (11,) and not pattern.trail.any()
    assert pattern.pixels.shape == (11, 3) and not pattern.pixels.any()
    # A mapping-independent buffer is re-zeroed too: rebind is a fresh start,
    # and no resampling semantics are invented [S219].
    assert pattern.field.shape == (4, 3) and not pattern.field.any()


def test_rebound_buffer_is_still_tracked() -> None:
    """The registry maps name -> spec, so re-reading picks up the new array."""
    renderer = Renderer(Buffered(), line(6))
    for _ in range(3):
        renderer.step(1.0 / 60.0)
    pattern = renderer.pattern

    # before_render rebinds before the first render, so every rendered frame
    # sees an array the registry never saw allocated — and it is locked all
    # the same, which identity tracking would have missed.
    assert pattern.rebound_in_render == [True, True, True]
    assert pattern.trail is not pattern.first_trail
    assert pattern.writeable_in_render == [(False, False)] * 3


def test_buffers_are_readonly_in_render_and_writable_again_next_frame() -> None:
    renderer = Renderer(Buffered(), line(6))
    for _ in range(3):
        renderer.step(1.0 / 60.0)
    pattern = renderer.pattern

    assert pattern.writeable_in_render == [(False, False)] * 3
    assert pattern.writeable_in_before == [(True, True)] * 3
    # ...and still writable once the sequence is over.
    assert pattern.trail.flags.writeable and pattern.pixels.flags.writeable


def test_render_cannot_write_a_buffer() -> None:
    class Impure(Pattern):
        name = "impure"

        def setup(self, n, x, y, z, index):
            self.state = self.buffer("state", n)

        def render(self, x, y, z, index):
            self.state += 1.0  # in-place: refused while locked
            return np.zeros((index.size, 3), dtype=np.float32)

    renderer = Renderer(Impure(), line(4))
    renderer.step(1.0 / 60.0)
    # Contained, not raised — and the buffer is untouched.
    assert renderer.error is not None and renderer.error.phase == "render"
    assert isinstance(renderer.error.exception, ValueError)
    assert not renderer.pattern.state.any()


def test_buffer_outside_setup_raises() -> None:
    unbound = Buffered()
    with pytest.raises(RuntimeError, match="setup"):
        unbound.buffer("early", 4)

    pattern = Buffered()
    Renderer(pattern, line(4))
    with pytest.raises(RuntimeError, match="setup"):
        pattern.buffer("late", 4)

    # The class-level registry default must never be written through.
    assert Pattern._buffers == {}


def test_reserved_and_duplicate_names_are_refused() -> None:
    class Clashing(Pattern):
        name = "clashing"
        declare = "pixels"

        def setup(self, n, x, y, z, index):
            self.buffer(self.declare, n)

        def render(self, x, y, z, index):
            return np.zeros((index.size, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="reserved"):
        Renderer(Clashing(), line(4))

    class Twice(Clashing):
        name = "twice"

        def setup(self, n, x, y, z, index):
            self.buffer("dup", n)
            self.buffer("dup", n)

    with pytest.raises(ValueError, match="already declared"):
        Renderer(Twice(), line(4))


def test_unlockable_buffer_is_diagnosed_once_not_fatal() -> None:
    """Purity enforcement is best-effort: a policy check never kills a frame."""

    class Sloppy(Pattern):
        name = "sloppy"

        def setup(self, n, x, y, z, index):
            self.state = self.buffer("state", n)

        def before_render(self, dt, features):
            self.state = 0.5  # rebound to something that has no write flag

        def render(self, x, y, z, index):
            return np.zeros((index.size, 3), dtype=np.float32)

    renderer = Renderer(Sloppy(), line(4))
    for _ in range(5):
        renderer.step(1.0 / 60.0)

    assert renderer.error is None  # frames kept rendering
    assert len(renderer.diagnostics) == 1
    assert "state" in renderer.diagnostics[0]
