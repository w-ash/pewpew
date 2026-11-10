"""Shared sink helpers: the display gamma/quantize step, the temporal
dither, and the loop as the only clock."""

from __future__ import annotations

import numpy as np
import pytest

from fakes import FLOW, FakeTime, Oversleeper, hosted
from pewpew.mapping import line
from pewpew.pace import PacedLoop
from pewpew.sinks.sink import DITHER_MOTION, Dither, from_display_u8, stride, to_display_u8


def test_display_u8_applies_display_gamma():
    # v ** (1/2.2), then 8-bit: 0.5 -> 186, so mid-greys stay bright on screen.
    frame = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    out = to_display_u8(frame)
    assert out.dtype == np.uint8
    assert out.tolist() == [[0, 186, 255]]


def test_display_u8_clamps_and_survives_nonfinite():
    frame = np.array([[-0.5, 2.0, np.nan], [np.inf, -np.inf, 0.25]], dtype=np.float32)
    out = to_display_u8(frame)
    expected_q = round((0.25 ** (1 / 2.2)) * 255)
    assert out.tolist() == [[0, 255, 0], [255, 0, expected_q]]


def test_display_u8_leaves_the_input_untouched():
    frame = np.full((4, 3), 0.5, dtype=np.float32)
    frame.setflags(write=False)  # as delivered by PacedLoop
    held = frame.copy()
    to_display_u8(frame)
    assert np.array_equal(frame, held)


def test_from_display_u8_undoes_display_gamma_for_every_byte():
    every = np.repeat(np.arange(256, dtype=np.uint8)[:, None], 3, axis=1)
    linear = from_display_u8(every)
    assert linear.dtype == np.float32
    assert np.array_equal(to_display_u8(linear), every)
    assert linear[186, 0] == pytest.approx(0.5, abs=0.002)  # what to_display_u8 makes of 0.5
    assert from_display_u8(every, gamma=1.0)[51, 0] == pytest.approx(0.2)


def grey(levels: np.ndarray) -> np.ndarray:
    """One pixel a frame, grey at each level in 8-bit steps."""
    return np.repeat((np.asarray(levels, np.float32) / 255.0)[:, None, None], 3, axis=2)


def dithered(frames: np.ndarray) -> np.ndarray:
    dither = Dither()
    return np.stack([dither(f) for f in frames]).astype(np.int64)


@pytest.mark.parametrize("start, end", [(2.0, 5.0), (40.3, 36.1), (0.6, 3.9)])
@pytest.mark.parametrize("n", [60, 240])
def test_a_slow_fade_averages_to_its_true_level_within_one_nth_of_a_step(start, end, n):
    levels = np.linspace(start, end, n, dtype=np.float32)
    assert abs(levels[1] - levels[0]) >= DITHER_MOTION  # slow, but moving
    out = dithered(grey(levels))[:, 0, 0]
    assert abs(out.mean() - levels.mean()) <= 1.0 / n


def test_a_dither_steps_between_the_two_nearest_levels_only():
    levels = np.linspace(10.0, 11.0, 90, dtype=np.float32)
    out = dithered(grey(levels))[:, 0, 0]
    assert set(out.tolist()) <= {10, 11}
    assert np.all(np.abs(np.diff(out)) <= 1)


def test_the_dither_is_deterministic():
    rng = np.random.default_rng(7)
    frames = rng.random((50, 64, 3), dtype=np.float32) * 0.1 + np.linspace(0, 0.05, 50, dtype=np.float32)[:, None, None]
    assert np.array_equal(dithered(frames), dithered(frames))


def test_a_held_full_range_color_passes_unchanged_every_frame():
    codes = np.array([[0, 255, 128], [1, 254, 33], [255, 255, 255], [0, 0, 0]], np.float32)
    frame = codes / np.float32(255.0)
    out = dithered(np.stack([frame] * 30))
    assert np.array_equal(out, np.broadcast_to(codes.astype(np.int64), out.shape))


def test_a_held_level_between_steps_is_steady_after_a_fade():
    # A fade that stops at 3.4 steps shows 3 from then on, without shimmer.
    levels = np.concatenate([np.linspace(2.0, 3.4, 40), np.full(30, 3.4)]).astype(np.float32)
    out = dithered(grey(levels))[:, 0, 0]
    assert out[41:].tolist() == [3] * 29


def test_a_jitter_back_and_forth_gets_plain_rounding():
    levels = np.array([5.4, 5.6, 5.4, 5.6, 5.4, 5.6], np.float32)
    out = dithered(grey(levels))[:, 0, 0]
    assert out.tolist() == np.rint(levels).astype(int).tolist()


def test_below_half_a_step_is_black():
    levels = np.linspace(0.45, 0.0, 30, dtype=np.float32)
    assert dithered(grey(levels))[:, 0, 0].tolist() == [0] * 30


def test_the_dither_clamps_and_survives_nonfinite():
    frame = np.array([[-0.5, 2.0, np.nan], [np.inf, -np.inf, 0.5]], dtype=np.float32)
    assert Dither()(frame).tolist() == [[0, 255, 0], [255, 0, 128]]


def test_a_frame_of_a_new_size_starts_the_dither_again():
    dither = Dither()
    dither(np.full((4, 3), 0.1, np.float32))
    assert dither(np.full((2, 3), 0.5, np.float32)).tolist() == [[128] * 3] * 2


@pytest.mark.parametrize("loop, cap, k", [(60, 60, 1), (60, 61, 1), (60, 40, 2), (60, 30, 2), (60, 29, 3),
                                          (50, 30, 2), (30, 60, 1)])
def test_stride_is_the_least_whole_step_that_keeps_under_the_cap(loop, cap, k):
    assert stride(loop, cap) == k
    assert loop / k <= cap or k == 1


def test_stride_refuses_a_rate_of_zero():
    with pytest.raises(ValueError, match="positive"):
        stride(60.0, 0.0)


def record_sends(loop_fps: float, sink_fps: float, ft: FakeTime, frames: int, **kw) -> list[float]:
    """Wall times at which a sink at `sink_fps` gets frames from a loop at
    `loop_fps`, with the sink called on the loop thread."""
    sent: list[float] = []
    k = stride(loop_fps, sink_fps)
    ticks = iter(range(frames))

    def on_frame(t, frame):
        if next(ticks) % k == 0:
            sent.append(ft.now())

    loop = PacedLoop(hosted(FLOW, line(8)), fps=loop_fps, on_frame=[on_frame], now=ft.now, sleep=ft.sleep, **kw)
    loop.run(frames=frames)
    return sent


@pytest.mark.parametrize("loop_fps, sink_fps", [(60, 60), (60, 40), (60, 30), (50, 50)])
def test_a_sink_gets_evenly_spaced_frames_with_no_beat(loop_fps, sink_fps):
    ft = FakeTime()
    sent = record_sends(loop_fps, sink_fps, ft, 120)
    gaps = np.diff(sent)
    period = stride(loop_fps, sink_fps) / loop_fps
    assert np.allclose(gaps, period, atol=1e-9)


def test_an_oversleep_delays_a_frame_but_never_bunches_the_next():
    # A late wake is absorbed by the absolute schedule: every gap stays one
    # period, so a board's gate (more than 15 ms) never sees two close frames.
    ft = Oversleeper(0.003)
    gaps = np.diff(record_sends(60, 60, ft, 60))
    assert np.allclose(gaps, 1 / 60, atol=1e-9)
