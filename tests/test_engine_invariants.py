"""Invariants the engine enforces: without its guard, each case here gives
wrong output or corrupt state silently. Purity (ADR-005) is only real if
the engine enforces it, and a guard without a test comes back off."""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Pattern, Renderer, line, render_sequence


class Flat(Pattern):
    def render(self, x, y, z, index):
        return np.full((index.size, 3), 0.5, dtype=np.float32)


# ---- render purity beyond the buffer registry --------------------------------


def test_render_cannot_write_the_coordinate_arrays() -> None:
    """Coords are views onto the caller's mapping and never enter the
    buffer registry: an in-place `x += 0.5` in `render` would corrupt the
    caller's mapping, and every later frame would render against it with no
    error raised."""

    class Coord(Pattern):
        def render(self, x, y, z, index):
            x += 0.5
            return np.full((index.size, 3), 0.5, dtype=np.float32)

    mapping = line(5)
    original = mapping[:, 0].copy()
    renderer = Renderer(Coord(), mapping)
    renderer.step(1.0 / 60.0)

    assert renderer.error is not None and renderer.error.phase == "render"
    assert np.array_equal(mapping[:, 0], original), "the caller's mapping was mutated"


def test_index_is_read_only_too() -> None:
    class Idx(Pattern):
        def render(self, x, y, z, index):
            index[:] = 0
            return np.full((index.size, 3), 0.5, dtype=np.float32)

    renderer = Renderer(Idx(), line(5))
    renderer.step(1.0 / 60.0)
    assert renderer.error is not None


# ---- the frame the engine accepts back ---------------------------------------


def test_wrong_dtype_frame_is_contained() -> None:
    """`pattern.pixels` is a registered buffer; a float64 frame would make the
    array disagree with its own BufferSpec, which is what hot reload will carry
    state across by."""

    class F64(Pattern):
        def render(self, x, y, z, index):
            return np.full((index.size, 3), np.nan, dtype=np.float64)

    renderer = Renderer(F64(), line(4))
    renderer.step(1.0 / 60.0)

    assert renderer.error is not None and renderer.error.phase == "render"
    assert renderer.pattern.pixels.dtype == np.float32
    assert np.all(np.isfinite(renderer.pattern.pixels))


def test_returned_frame_does_not_alias_pattern_state() -> None:
    """A caller that writes to the returned frame, as a sink applying gamma
    in place would, must not change `pattern.pixels` (the pattern's trail),
    and its array stays writable while the engine locks the buffer during
    the next render."""
    renderer = Renderer(Flat(), line(4))
    frame = renderer.step(1.0 / 60.0)
    frame[:] = 0.0

    assert float(renderer.pattern.pixels.max()) == 0.5
    # ...and the caller's array stays writable across the next frame.
    renderer.step(1.0 / 60.0)
    frame[:] = 1.0


# ---- time only moves forward --------------------------------------------------


def test_time_never_goes_backwards() -> None:
    """Same invariant FakeClock.tick enforces, and for the same reason: a
    negative dt makes `fade` return a factor > 1, so trails amplify to white
    instead of decaying — wrong output rather than an obvious failure."""
    renderer = Renderer(Flat(), line(4))
    renderer.step(1.0 / 60.0)
    with pytest.raises(ValueError, match="never goes backwards"):
        renderer.step(-1.0)
    with pytest.raises(ValueError, match="never goes backwards"):
        renderer.advance_to(0.0)


def test_zero_dt_is_allowed() -> None:
    """Two sinks resolving the same frame is legitimate; only going *back* is not."""
    renderer = Renderer(Flat(), line(4))
    t = renderer.t
    renderer.advance_to(t)
    assert renderer.t == t


# ---- binding -----------------------------------------------------------------


class Half(Pattern):
    """Declares one buffer, then raises in `setup` on a 9-pixel map."""

    def setup(self, n, x, y, z, index):
        self.buffer("a", n)
        if n == 9:
            raise RuntimeError("boom")

    def render(self, x, y, z, index):
        return np.full((index.size, 3), 0.5, dtype=np.float32)


@pytest.mark.parametrize("repair, n", [
    (lambda renderer: renderer.rebind(line(6)), 6),
    (lambda renderer: renderer.swap(Flat()), 9),  # binds on the map the failed rebind left
], ids=["rebind", "swap"])
def test_failed_setup_poisons_the_renderer_until_a_bind_succeeds(repair, n) -> None:
    """Binding is deliberately not contained, but a half-bound pattern must not
    keep rendering as if nothing happened — some buffers reallocated, the ones
    declared after the raise missing."""
    renderer = Renderer(Half(), line(4))
    renderer.step(1.0 / 60.0)

    with pytest.raises(RuntimeError, match="boom"):
        renderer.rebind(line(9))
    with pytest.raises(RuntimeError, match="not bound"):
        renderer.step(1.0 / 60.0)

    repair(renderer)
    assert renderer.step(1.0 / 60.0).shape == (n, 3)


@pytest.mark.parametrize("name", ["render", "setup", "before_render", "_buffers", "speed"])
def test_buffer_cannot_shadow_anything_on_the_class(name: str) -> None:
    """Every class attribute is reserved, not a list of engine names:
    `buffer("render")` would shadow the hook (every later frame dies with
    "'ndarray' is not callable"), and `buffer("_buffers")` would replace the
    registry mid-setup and raise out of binding, past all containment."""

    class Shadow(Pattern):
        speed = 1.0

        def setup(self, n, x, y, z, index):
            self.buffer(name, n)

        def render(self, x, y, z, index):
            return np.full((index.size, 3), 0.5, dtype=np.float32)

    with pytest.raises(ValueError, match="reserved"):
        Renderer(Shadow(), line(4))


def test_a_class_and_an_instance_are_not_interchangeable() -> None:
    """Each entry point says which one it takes, rather than failing deep
    inside with an AttributeError or 'object is not callable'."""
    with pytest.raises(TypeError, match="Renderer takes a Pattern instance, not a class"):
        Renderer(Flat, line(4))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="render_sequence takes a Pattern class, not an instance"):
        render_sequence(Flat(), line(4))  # type: ignore[arg-type]
