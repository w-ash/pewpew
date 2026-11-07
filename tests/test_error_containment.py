"""Per-frame exception containment (ADR-005; architecture §3).

"Errors never stop rendering": a raising program produces a visible error
state and the engine keeps stepping *and keeps calling the program*, so a
program whose failure passes recovers with no restart. Precedent is led-control's
pulsing-red frame [S660:ledcontrol/animationcontroller.py#L418-L434] and
Pixelblaze's crash-proof editor [S504].
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pytest

from fakes import frames as render_frames
from fakes import hosted, source_op
from pewpew.mapping import line
from pewpew.render import Renderer

pytestmark = pytest.mark.usefixtures("fake_ops")

FPS = 60.0
DT = 1.0 / FPS
NID = "flaky_test"


def flaky(fail_on=frozenset(), *, advance_fails: bool = False):
    """A program that renders flat grey, brighter each frame, but raises
    in render on the frames in `fail_on`, or in every advance."""

    def setup(op, ctx):
        op.frame = -1

    def advance(op, ctx):
        if advance_fails:
            raise RuntimeError("boom in advance")
        op.frame += 1

    def render(op, c):
        if op.frame in fail_on:
            raise ValueError(f"boom in render at frame {op.frame}")
        return np.full((len(c.index), 3), 0.25 * (op.frame + 1), dtype=np.float32)

    return source_op(NID, render, setup=setup, advance=advance)


def op_of(renderer: Renderer) -> Any:
    """The op of the program's one node."""
    return renderer.bound._nodes[NID].op


def always_fails():
    return flaky(frozenset(range(10_000)))


def fails_once():
    return flaky(frozenset({2}))


def advance_fails():
    return flaky(advance_fails=True)


def is_error_frame(frame: np.ndarray) -> bool:
    """Red channel lit, green and blue dark, all in range."""
    return bool(
        frame.dtype == np.float32
        and np.all(frame[:, 0] > 0.0)
        and not frame[:, 1:].any()
        and frame.min() >= 0.0
        and frame.max() <= 1.0
    )


def test_render_failure_yields_pulsing_red_frames() -> None:
    frames = render_frames(hosted(always_fails(), line(8)), 30, FPS)

    assert frames.shape == (30, 8, 3) and frames.dtype == np.float32
    assert all(is_error_frame(f) for f in frames)
    # Pulsing, not a static red: the level moves with engine t.
    assert len(np.unique(frames[:, 0, 0])) > 5


def test_advance_failure_is_contained_too() -> None:
    renderer = hosted(advance_fails(), line(8))
    frames = [renderer.step(DT) for _ in range(3)]

    assert all(is_error_frame(f) for f in frames)
    assert renderer.error is not None
    assert renderer.error.phase == "advance"
    assert renderer.error.pattern == "layers.base" and renderer.error.path == f"layers.base.{NID}"
    assert "boom in advance" in renderer.error.traceback


def test_renderer_keeps_stepping_and_keeps_calling_the_program() -> None:
    renderer = hosted(always_fails(), line(8))
    for _ in range(5):
        renderer.step(DT)

    assert renderer.t == 5 * DT
    # The program was still called every frame — that is what lets a
    # program whose failure passes recover with no restart.
    assert op_of(renderer).frame == 4
    assert renderer.error is not None
    assert renderer.error.phase == "render"
    assert renderer.error.frame == 4
    assert renderer.error.t == 5 * DT
    assert isinstance(renderer.error.exception, ValueError)


def test_error_is_populated_then_cleared_on_recovery() -> None:
    renderer = hosted(fails_once(), line(4))
    good_a = renderer.step(DT)
    good_b = renderer.step(DT)
    assert renderer.error is None
    assert not is_error_frame(good_a) and not is_error_frame(good_b)

    bad = renderer.step(DT)
    assert is_error_frame(bad)
    assert renderer.error is not None and renderer.error.frame == 2

    recovered = renderer.step(DT)
    assert renderer.error is None
    assert np.allclose(recovered, 1.0)


def test_failed_frame_does_not_corrupt_pixels() -> None:
    renderer = hosted(fails_once(), line(4))
    renderer.step(DT)
    last_good = renderer.step(DT).copy()

    renderer.step(DT)  # the failing frame
    # The last frame a program reads next frame (`prev()`) is still the
    # last good frame, not the red error frame.
    assert np.array_equal(renderer.bound.buffers.pixels, last_good)


def test_wrong_return_shape_is_contained() -> None:
    renderer = hosted(fails_once(), line(4))
    renderer.bound.render = lambda: np.zeros((4, 4), dtype=np.float32)
    frame = renderer.step(DT)

    assert is_error_frame(frame)
    assert renderer.error is not None and renderer.error.phase == "render"


def test_failing_sequences_stay_deterministic() -> None:
    for factory in (always_fails, advance_fails, fails_once):
        a = render_frames(hosted(factory(), line(8)), 12, FPS)
        b = render_frames(hosted(factory(), line(8)), 12, FPS)
        assert np.array_equal(a, b), factory.__name__


def test_repeated_failures_log_once(caplog) -> None:
    caplog.set_level(logging.ERROR, logger="pewpew.render")
    renderer = hosted(always_fails(), line(8))
    for _ in range(30):
        renderer.step(DT)

    records = [r for r in caplog.records if r.name == "pewpew.render"]
    assert len(records) == 1  # 30 failing frames, one log line
    assert "(frame 0, t=0.016667)" in records[0].getMessage()


def test_a_program_that_fails_every_frame_keeps_one_status_text() -> None:
    """The status line is the error's text: it names no frame or time, so
    the preview sends it once, not once per frame."""

    def render(op, c):
        raise ValueError("boom")

    renderer = hosted(source_op("steady_test", render), line(8), name="mine")
    texts = set()
    for _ in range(30):
        renderer.step(DT)
        texts.add(str(renderer.error))
    assert texts == {"mine.render raised: ValueError: boom (in node mine.steady_test (steady_test))"}
