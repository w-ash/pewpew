"""Engine-managed private state buffers (ADR-005 amendment 2026-07-27).

The properties under test are the ones the amendment makes the engine
responsible for: an op declares its state through `ctx.buffer` at bind,
at its fill on bind, reallocated and refilled on a mapping change, and
read-only while the program renders, so the render stays pure — the
property golden frames and determinism rest on (§8).
"""

from __future__ import annotations

import numpy as np
import pytest

from fakes import hosted, op_of, source_op
from pewpew.fx.buffers import Buffers
from pewpew.mapping import line

pytestmark = pytest.mark.usefixtures("fake_ops")

NID = "buffered_test"


def buffered():
    """A program of one op that declares both buffer flavours, per-pixel
    (N,) and an internal field, and records whether they and `pixels` are
    writable as it advances and as it renders."""

    def setup(op, ctx):
        op.trail = ctx.buffer("trail", ctx.n)
        op.field = ctx.buffer("field", (4, 3))
        op.in_advance, op.in_render = [], []
        op.prev = ctx.prev

    def advance(op, ctx):
        op.in_advance.append((op.trail.flags.writeable, op.prev().flags.writeable))
        np.clip(op.trail - 0.1, 0.0, 1.0, out=op.trail)
        op.trail += 0.25
        op.field[0, 0] += 1.0

    def render(op, c):
        op.in_render.append((op.trail.flags.writeable, op.prev().flags.writeable))
        v = np.clip(op.trail, 0.0, 1.0).astype(np.float32)
        return np.stack([v, v, v], axis=1)

    return source_op(NID, render, setup=setup, advance=advance)


def test_buffers_are_declared_at_their_fill_and_reachable() -> None:
    renderer = hosted(buffered(), line(6))
    buffers = renderer.bound.buffers

    assert list(buffers) == [f"{NID}.trail", f"{NID}.field"]
    trail, field = buffers[f"{NID}.trail"], buffers[f"{NID}.field"]
    assert trail.shape == (6,) and trail.dtype == np.float32 and not trail.any()
    assert field.shape == (4, 3) and not field.any()
    assert op_of(renderer, NID).trail is trail
    assert buffers.pixels.shape == (6, 3) and not buffers.pixels.any()


def test_buffer_honours_dtype_and_fill() -> None:
    buffers = Buffers(3)
    assert buffers.declare("hits", 3, dtype=np.int32).dtype == np.int32
    assert np.all(buffers.declare("warm", (2, 2), fill=0.5) == 0.5)


def test_rebind_reallocates_and_refills() -> None:
    renderer = hosted(buffered(), line(6))
    renderer.step(1.0 / 60.0)
    op = op_of(renderer, NID)
    assert op.trail.any() and op.field.any()  # state accumulated

    renderer.rebind(line(11))

    assert op_of(renderer, NID) is op  # a rebind keeps the op
    assert op.trail.shape == (11,) and not op.trail.any()
    assert renderer.bound.buffers.pixels.shape == (11, 3) and not renderer.bound.buffers.pixels.any()
    # A mapping-independent buffer is refilled too: rebind is a fresh start,
    # and no resampling semantics are invented [S219].
    assert op.field.shape == (4, 3) and not op.field.any()


def test_buffers_are_read_only_in_render_and_writable_again_next_frame() -> None:
    renderer = hosted(buffered(), line(6))
    for _ in range(3):
        renderer.step(1.0 / 60.0)
    op = op_of(renderer, NID)

    assert op.in_render == [(False, False)] * 3
    assert op.in_advance == [(True, True)] * 3
    # ...and still writable once the sequence is over.
    assert op.trail.flags.writeable and renderer.bound.buffers.pixels.flags.writeable


def test_render_cannot_write_a_buffer() -> None:
    def setup(op, ctx):
        op.state = ctx.buffer("state", ctx.n)

    def render(op, c):
        op.state += 1.0  # in place: refused while locked
        return np.zeros((len(c.index), 3), dtype=np.float32)

    renderer = hosted(source_op("impure_test", render, setup=setup), line(4))
    renderer.step(1.0 / 60.0)
    # Contained, not raised — and the buffer is untouched.
    assert renderer.error is not None and renderer.error.phase == "render"
    assert isinstance(renderer.error.exception, ValueError)
    assert not renderer.bound.buffers["impure_test.state"].any()


def test_a_name_declared_twice_is_refused() -> None:
    buffers = Buffers(4)
    buffers.declare("dup", 4)
    with pytest.raises(ValueError, match="already declared"):
        buffers.declare("dup", 4)
