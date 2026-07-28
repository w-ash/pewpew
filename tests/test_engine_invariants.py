"""Invariants the engine enforces, each one a defect found in review.

These are not feature tests — every case here is a scenario that silently
produced wrong output or corrupted state before the guard existed. Purity
(ADR-005) is only real if the engine enforces it; a guard that exists but is
untested is a guard that comes back off.
"""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Pattern, Renderer, bins, line, sample2d


class Flat(Pattern):
    name = "flat"

    def render(self, x, y, z, index):
        return np.full((index.size, 3), 0.5, dtype=np.float32)


# ---- render purity beyond the buffer registry --------------------------------


def test_render_cannot_write_the_coordinate_arrays() -> None:
    """Coords are views onto the caller's mapping and never enter the registry.

    Locking buffers alone left this hole: an in-place `x += 0.5` in `render`
    corrupted the caller's own mapping permanently, and every later frame
    rendered against the damaged coordinates with no error raised.
    """

    class Coord(Pattern):
        name = "coord"

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
        name = "idx"

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
        name = "f64"

        def render(self, x, y, z, index):
            return np.full((index.size, 3), np.nan, dtype=np.float64)

    renderer = Renderer(F64(), line(4))
    renderer.step(1.0 / 60.0)

    assert renderer.error is not None and renderer.error.phase == "render"
    assert renderer.pattern.pixels.dtype == np.float32
    assert np.all(np.isfinite(renderer.pattern.pixels))


def test_returned_frame_does_not_alias_pattern_state() -> None:
    """A sink applying gamma in place must not destroy the pattern's trail.

    The returned frame and `pattern.pixels` were the same object, so a caller
    writing to what it was handed silently rewrote the previous-frame buffer —
    and the engine then flipped that array read-only during the next render,
    handing the consumer a ValueError from an object it owned.
    """
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


def test_failed_setup_poisons_the_renderer() -> None:
    """Binding is deliberately not contained, but a half-bound pattern must not
    keep rendering as if nothing happened — some buffers reallocated, the ones
    declared after the raise missing."""

    class Half(Pattern):
        name = "half"

        def setup(self, n, x, y, z, index):
            self.buffer("a", n)
            if n == 9:
                raise RuntimeError("boom")

        def render(self, x, y, z, index):
            return np.full((index.size, 3), 0.5, dtype=np.float32)

    renderer = Renderer(Half(), line(4))
    renderer.step(1.0 / 60.0)

    with pytest.raises(RuntimeError, match="boom"):
        renderer.rebind(line(9))
    with pytest.raises(RuntimeError, match="not bound"):
        renderer.step(1.0 / 60.0)

    renderer.rebind(line(6))  # a good rebind clears it
    assert renderer.step(1.0 / 60.0).shape == (6, 3)


@pytest.mark.parametrize("name", ["render", "setup", "before_render", "_buffers", "speed"])
def test_buffer_cannot_shadow_anything_on_the_class(name: str) -> None:
    """A denylist of engine attribute names was not enough: `buffer("render")`
    shadowed the hook (every later frame died with "'ndarray' is not callable")
    and `buffer("_buffers")` replaced the registry mid-setup and raised out of
    binding, past all containment."""

    class Shadow(Pattern):
        name = "shadow"
        speed = 1.0

        def setup(self, n, x, y, z, index):
            self.buffer(name, n)

        def render(self, x, y, z, index):
            return np.full((index.size, 3), 0.5, dtype=np.float32)

    with pytest.raises(ValueError, match="reserved"):
        Renderer(Shadow(), line(4))


# ---- kit helpers clamp at both ends ------------------------------------------


def test_bins_clamps_the_lower_edge() -> None:
    """A negative index does not raise — it wraps to the far end of the band
    array and quietly returns another band's value. Imported maps are where
    slightly-out-of-range coordinates come from."""
    assert bins(np.float32([-0.2]), 16)[0] == 0
    assert bins(np.float32([-5.0]), 16)[0] == 0
    assert bins(np.float32([1.0]), 16)[0] == 15  # the edge the study measured


def test_sample2d_clamps_the_lower_edge() -> None:
    field = np.arange(512, dtype=np.float32).reshape(32, 16)
    below = sample2d(field, np.float32([-0.2]), np.float32([-0.2]))
    assert below[0] == field[0, 0]
    above = sample2d(field, np.float32([1.5]), np.float32([1.5]))
    assert above[0] == field[31, 15]
