"""Per-frame exception containment (ADR-005; architecture §3).

"Errors never stop the show": a raising pattern produces a visible error
state and the engine keeps stepping *and keeps calling the pattern*, so a fix
applied by hot reload self-heals with no restart. Precedent is led-control's
pulsing-red frame [S660:ledcontrol/animationcontroller.py#L418-L434] and
Pixelblaze's crash-proof editor [S504].
"""

from __future__ import annotations

import logging

import numpy as np

from pewpew import Pattern, Renderer, line, render_sequence

FPS = 60.0
DT = 1.0 / FPS


class Flaky(Pattern):
    """Renders a flat grey ramp, but raises on the frames in `fail_on`."""

    name = "flaky"
    fail_on: frozenset[int] = frozenset()

    def __init__(self) -> None:
        self.frame = -1

    def before_render(self, dt, features):
        self.frame += 1

    def render(self, x, y, z, index):
        if self.frame in self.fail_on:
            raise ValueError(f"boom in render at frame {self.frame}")
        v = np.full(index.size, 0.25 * (self.frame + 1), dtype=np.float32)
        return np.stack([v, v, v], axis=1)


class AlwaysFails(Flaky):
    name = "always-fails"
    fail_on = frozenset(range(10_000))


class BeforeRenderFails(Flaky):
    name = "before-render-fails"

    def before_render(self, dt, features):
        raise RuntimeError("boom in before_render")


class WrongShape(Flaky):
    name = "wrong-shape"

    def render(self, x, y, z, index):
        return np.zeros((index.size, 4), dtype=np.float32)


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
    frames = render_sequence(AlwaysFails, line(8), frames=30, fps=FPS)

    assert frames.shape == (30, 8, 3) and frames.dtype == np.float32
    assert all(is_error_frame(f) for f in frames)
    # Pulsing, not a static red: the level moves with engine t.
    assert len(np.unique(frames[:, 0, 0])) > 5


def test_before_render_failure_is_contained_too() -> None:
    renderer = Renderer(BeforeRenderFails(), line(8))
    frames = [renderer.step(DT) for _ in range(3)]

    assert all(is_error_frame(f) for f in frames)
    assert renderer.error is not None
    assert renderer.error.phase == "before_render"
    assert renderer.error.pattern == "before-render-fails"
    assert "boom in before_render" in renderer.error.traceback


def test_renderer_keeps_stepping_and_keeps_calling_the_pattern() -> None:
    renderer = Renderer(AlwaysFails(), line(8))
    for _ in range(5):
        renderer.step(DT)

    assert renderer.t == 5 * DT
    # The pattern was still called every frame — that is what lets a hot
    # reload of a fixed pattern recover with no restart.
    assert renderer.pattern.frame == 4
    assert renderer.error is not None
    assert renderer.error.phase == "render"
    assert renderer.error.frame == 4
    assert renderer.error.t == 5 * DT
    assert isinstance(renderer.error.exception, ValueError)


def test_error_is_populated_then_cleared_on_recovery() -> None:
    class FailsOnce(Flaky):
        name = "fails-once"
        fail_on = frozenset({2})

    renderer = Renderer(FailsOnce(), line(4))
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
    class FailsOnce(Flaky):
        name = "fails-once"
        fail_on = frozenset({2})

    renderer = Renderer(FailsOnce(), line(4))
    renderer.step(DT)
    last_good = renderer.step(DT).copy()

    renderer.step(DT)  # the failing frame
    # The trail state a pattern reads next frame is still the last good frame,
    # not the red error frame.
    assert np.array_equal(renderer.pattern.pixels, last_good)


def test_wrong_return_shape_is_contained() -> None:
    renderer = Renderer(WrongShape(), line(4))
    frame = renderer.step(DT)

    assert is_error_frame(frame)
    assert renderer.error is not None and renderer.error.phase == "render"


def test_failing_sequences_stay_deterministic() -> None:
    class FailsOnce(Flaky):
        name = "fails-once"
        fail_on = frozenset({2})

    for factory in (AlwaysFails, BeforeRenderFails, FailsOnce):
        a = render_sequence(factory, line(8), frames=12, fps=FPS)
        b = render_sequence(factory, line(8), frames=12, fps=FPS)
        assert np.array_equal(a, b), factory.name


def test_repeated_failures_log_once(caplog) -> None:
    caplog.set_level(logging.ERROR, logger="pewpew.render")
    renderer = Renderer(AlwaysFails(), line(8))
    for _ in range(30):
        renderer.step(DT)

    records = [r for r in caplog.records if r.name == "pewpew.render"]
    assert len(records) == 1  # 30 failing frames, one log line
