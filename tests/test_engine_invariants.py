"""Invariants the engine enforces: without its guard, each case here gives
wrong output or corrupt state silently. Purity (ADR-005) is only real if
the engine enforces it, and a guard without a test comes back off."""

from __future__ import annotations

import numpy as np
import pytest

from fakes import hosted, one_node, source_op
from pewpew.mapping import line

pytestmark = pytest.mark.usefixtures("fake_ops")

GREY = one_node("solid_test", {"red": 0.5, "green": 0.5, "blue": 0.5})


def grey(n: int) -> np.ndarray:
    return np.full((n, 3), 0.5, dtype=np.float32)


# ---- render purity beyond the buffers ----------------------------------------


def test_render_cannot_write_the_coordinate_arrays() -> None:
    """Coords are views onto the caller's mapping and never enter the
    buffers: an in-place `x += 0.5` in a render would corrupt the
    caller's mapping, and every later frame would render against it with no
    error raised."""

    def shift(op, c):
        c.x[:] += 0.5
        return grey(len(c.index))

    mapping = line(5)
    original = mapping[:, 0].copy()
    renderer = hosted(source_op("coord_test", shift), mapping)
    renderer.step(1.0 / 60.0)

    assert renderer.error is not None and renderer.error.phase == "render"
    assert np.array_equal(mapping[:, 0], original), "the caller's mapping was mutated"


def test_index_is_read_only_too() -> None:
    def zero(op, c):
        c.index[:] = 0
        return grey(len(c.index))

    renderer = hosted(source_op("index_test", zero), line(5))
    renderer.step(1.0 / 60.0)
    assert renderer.error is not None


# ---- the frame the engine accepts back ---------------------------------------


def test_wrong_dtype_frame_is_contained() -> None:
    """`pixels` is the program's state; a float64 frame would make it
    float64."""
    renderer = hosted(GREY, line(4))
    renderer.bound.render = lambda: np.full((4, 3), np.nan, dtype=np.float64)
    renderer.step(1.0 / 60.0)

    assert renderer.error is not None and renderer.error.phase == "render"
    assert renderer.bound.buffers.pixels.dtype == np.float32
    assert np.all(np.isfinite(renderer.bound.buffers.pixels))


def test_returned_frame_does_not_alias_program_state() -> None:
    """A caller that writes to the returned frame, as a sink applying gamma
    in place would, must not change `pixels` (what `prev()` reads), and its
    array stays writable while the engine locks the buffers during the
    next render."""
    renderer = hosted(GREY, line(4))
    frame = renderer.step(1.0 / 60.0)
    frame[:] = 0.0

    assert float(renderer.bound.buffers.pixels.max()) == 0.5
    # ...and the caller's array stays writable across the next frame.
    renderer.step(1.0 / 60.0)
    frame[:] = 1.0


# ---- time only moves forward --------------------------------------------------


def test_time_never_goes_backwards() -> None:
    """Same invariant FakeClock.tick enforces, and for the same reason: a
    negative dt makes `fade` return a factor > 1, so trails amplify to white
    instead of decaying — wrong output rather than an obvious failure."""
    renderer = hosted(GREY, line(4))
    renderer.step(1.0 / 60.0)
    with pytest.raises(ValueError, match="never goes backwards"):
        renderer.step(-1.0)
    with pytest.raises(ValueError, match="never goes backwards"):
        renderer.advance_to(0.0)


def test_zero_dt_is_allowed() -> None:
    """Two sinks resolving the same frame is legitimate; only going *back* is not."""
    renderer = hosted(GREY, line(4))
    t = renderer.t
    renderer.advance_to(t)
    assert renderer.t == t


# ---- binding -----------------------------------------------------------------


def test_failed_setup_poisons_the_renderer_until_a_bind_succeeds() -> None:
    """Binding is deliberately not contained, but a half-bound program must
    not keep rendering as if nothing happened — some buffers reallocated,
    the ones declared after the raise missing."""

    def half(op, ctx):
        ctx.buffer("a", ctx.n)
        if ctx.n == 9:
            raise RuntimeError("boom")

    renderer = hosted(source_op("half_test", lambda op, c: grey(len(c.index)), setup=half), line(4))
    renderer.step(1.0 / 60.0)

    with pytest.raises(RuntimeError, match="boom"):
        renderer.rebind(line(9))
    with pytest.raises(RuntimeError, match="not bound"):
        renderer.step(1.0 / 60.0)

    renderer.rebind(line(6))
    assert renderer.step(1.0 / 60.0).shape == (6, 3)
