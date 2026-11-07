"""Frame metrics (src/pewpew/metrics.py) on synthetic signals whose answer
is known."""

from __future__ import annotations

import json
import math
from dataclasses import fields, replace

import numpy as np
import pytest
from numpy.typing import ArrayLike

from pewpew.color import hsv
from pewpew.metrics import FLASH_LIMIT, Metrics, flash_rates, measure

FPS = 60.0


def _still(colours: np.ndarray, frames: int = 30) -> np.ndarray:
    """(F, N, 3): the (N, 3) `colours` held for `frames` frames."""
    return np.repeat(np.asarray(colours, np.float32)[None], frames, axis=0)


def _grey(levels: ArrayLike, pixels: int) -> np.ndarray:
    """(F, N, 3): every pixel grey at `levels[i]` in frame i."""
    column = np.asarray(levels, np.float32)[:, None, None]
    return np.broadcast_to(column, (len(column), pixels, 3)).copy()


def _strobe(rate: float, seconds: float = 3.0, pixels: int = 8, *, low: float = 0.0, high: float = 1.0,
            fps: float = FPS) -> np.ndarray:
    """A full-field grey square wave between `low` and `high` (white on/off
    by default) at `rate` Hz; frame i is at (i + 1) / fps."""
    t = np.arange(1, round(seconds * fps) + 1) / fps
    return _grey(np.where((t * rate) % 1.0 < 0.5, high, low), pixels)


def test_a_5_hz_strobe_reads_5_flashes_a_second_and_is_unsafe():
    m = measure(_strobe(5.0), FPS)
    assert 4.5 <= m.flash_rate_max <= 5.5
    assert not m.flash_safe


@pytest.mark.parametrize(("high", "flashes"), [(0.51, 5.0), (0.5, 5.0), (0.49, 0.0)])
def test_a_flash_is_a_luma_swing_of_a_tenth_or_more(high, flashes):
    """WCAG: opposing changes of 10% or more of full luminance; a swing of
    exactly 0.1 counts, though float32 holds 0.5 - 0.4 as 0.09999999."""
    m = measure(_strobe(5.0, low=0.4, high=high), FPS)
    assert m.flash_rate_max == flashes
    assert m.flash_safe is (flashes <= FLASH_LIMIT)


@pytest.mark.parametrize("fps", [30.0, 60.0])
def test_the_flash_window_is_a_whole_second(fps):
    """3.05 Hz puts a seventh change inside one second of frames; a window
    one frame short would read 3 flashes, and safe."""
    m = measure(_strobe(3.05, fps=fps), fps)
    assert m.flash_rate_max == 3.5 and m.flash_safe is False


def test_a_slow_strobe_is_safe():
    m = measure(_strobe(1.0), FPS)
    assert m.flash_rate_max <= FLASH_LIMIT
    assert m.flash_safe


def test_three_flashes_a_second_is_the_limit_and_still_safe():
    dark = measure(np.zeros((2, 1, 3), np.float32), FPS)
    assert replace(dark, flash_rate_max=FLASH_LIMIT, seconds=1.0).flash_safe
    assert not replace(dark, flash_rate_max=FLASH_LIMIT + 0.5, seconds=1.0).flash_safe


@pytest.mark.parametrize(("hz", "seconds"), [(10.0, 0.25), (6.0, 0.5), (5.0, 0.5)])
def test_under_a_second_flash_safety_is_unknown_never_safe(hz, seconds):
    """A short window counts the flashes of less than a second, so a fast
    strobe would read as safe: 10 Hz over 0.25 s counts 2.5."""
    m = measure(_strobe(hz, seconds), FPS)
    assert m.flash_safe is None and m.flash_rate_max <= FLASH_LIMIT
    assert measure(_strobe(hz, 2.0), FPS).flash_safe is False


def test_all_black_is_all_black_and_still():
    m = measure(np.zeros((30, 16, 3), np.float32), FPS)
    assert m.black_fraction == 1.0
    assert m.mean_luma == m.p95_luma == m.clip_fraction == 0.0
    assert m.palette_spread == 0.0 and m.hue_clusters == 0
    assert m.flash_rate_max == 0.0


def test_a_static_frame_has_no_motion_and_is_frozen():
    colours = np.random.default_rng(1).random((16, 3), dtype=np.float32)
    m = measure(_still(colours), FPS)
    assert m.motion_energy == 0.0
    assert m.frozen_fraction == 1.0


def test_motion_energy_is_luma_change_per_second():
    """White rising by 0.01 a frame at 60 fps is a luma change of 0.6 a second."""
    m = measure(_grey(np.linspace(0.0, 0.29, 30), 4), FPS)
    assert m.motion_energy == pytest.approx(0.6, rel=1e-4)
    assert m.frozen_fraction == 0.0


def test_a_span_under_one_8_bit_level_is_frozen():
    """At 10 fps a span of 0.1 s is one frame step."""
    frames = _still(np.full((4, 3), 0.5), frames=3)
    frames[1] += 2.0 / 255.0  # the first span moves
    frames[2] = frames[1] + 0.5 / 255.0  # the second does not
    assert measure(frames, 10.0).frozen_fraction == 0.5


@pytest.mark.parametrize("fps", [10.0, 30.0, 60.0, 120.0])
def test_frozen_reads_the_same_motion_alike_at_any_fps(fps):
    """A slow fade, 1/255 every 0.08 s, moves in every span of 0.1 s
    however finely it is rendered; per frame step it would read frozen."""
    t = np.arange(round(4 * fps)) / fps
    m = measure(_grey(0.2 + t / 255.0 / 0.08, 4), fps)
    assert m.frozen_fraction == 0.0
    assert measure(_still(np.full((4, 3), 0.5), frames=round(fps)), fps).frozen_fraction == 1.0


def test_clipping_counts_any_channel_at_full_including_overshoot():
    colours = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.5, 0.5, 0.5], [0.0, 0.0, 0.0]])
    assert measure(_still(colours), FPS).clip_fraction == 0.5


def test_nonfinite_values_are_counted_and_drawn_as_a_sink_draws_them():
    colours = np.full((4, 3), 0.25, np.float32)
    colours[0] = np.nan  # shown black
    colours[1, 0] = np.inf  # shown full red
    m = measure(_still(colours, frames=2), FPS)
    assert m.nonfinite == 2 * 4
    assert m.black_fraction == 0.25
    assert m.clip_fraction == 0.25
    assert all(math.isfinite(v) for v in m.to_json().values())


def test_spatial_detail_is_luma_change_between_index_neighbours():
    alternating = np.zeros((8, 3), np.float32)
    alternating[::2] = 1.0
    assert measure(_still(alternating), FPS).spatial_detail == pytest.approx(1.0)
    assert measure(_still(np.full((8, 3), 0.7)), FPS).spatial_detail == 0.0


def test_one_hue_has_no_spread_and_one_cluster():
    m = measure(_still(hsv(np.full(12, 0.6), 1.0, np.linspace(0.2, 1.0, 12))), FPS)
    assert m.palette_spread == pytest.approx(0.0, abs=1e-6)
    assert m.hue_clusters == 1


def test_a_rainbow_spreads_and_two_hues_make_two_clusters():
    rainbow = measure(_still(hsv(np.linspace(0.0, 1.0, 120, endpoint=False), 1.0, 1.0)), FPS)
    pair = measure(_still(hsv(np.repeat([0.0, 0.5], 6), 1.0, 1.0)), FPS)
    assert rainbow.palette_spread > 0.9 and rainbow.hue_clusters >= 8
    assert 0.5 < pair.palette_spread < rainbow.palette_spread
    assert pair.hue_clusters == 2


def test_grey_has_no_spread_whatever_its_float_noise():
    """Grey in OKLab carries chroma of float noise (about 1e-7), whose hue
    is arbitrary: below CHROMA_FLOOR it counts as no colour."""
    ramp = _still(np.repeat(np.linspace(0.0, 1.0, 64, dtype=np.float32)[:, None], 3, axis=1))
    m = measure(ramp, FPS)
    assert (m.palette_spread, m.hue_clusters) == (0.0, 0)
    red = hsv(np.zeros(64), 1.0, 1.0)
    red[:32] = ramp[0, :32]  # half grey: red is still the one hue
    assert measure(_still(red), FPS).palette_spread == pytest.approx(0.0, abs=1e-6)


def test_a_faint_tint_has_no_hue_and_a_few_stray_pixels_add_no_cluster():
    tint = hsv(np.zeros(100), 0.02, 0.5)  # chroma under CHROMA_FLOOR
    assert measure(_still(tint), FPS).hue_clusters == 0
    red = hsv(np.zeros(100), 1.0, 1.0)
    red[:3] = hsv(0.3, 1.0, 1.0)  # 3% green, under MIN_SHARE
    assert measure(_still(red), FPS).hue_clusters == 1


def test_one_hue_near_a_bin_edge_is_one_cluster():
    """sRGB red is OKLab hue 29.2°, 0.8° under a bin edge. Every hue with
    a neighbour 0.01 round the HSV wheel (12.7° in OKLab at most) is one."""
    def clusters(h: float) -> int:
        pair = np.concatenate([hsv(np.full(50, h), 1.0, 1.0), hsv(np.full(50, h + 0.01), 1.0, 1.0)])
        return measure(_still(pair, frames=2), FPS).hue_clusters

    assert clusters(0.0) == 1
    assert [h for h in np.linspace(0.0, 1.0, 48, endpoint=False) if clusters(h) != 1] == []


@pytest.mark.parametrize("fps", [np.float32(FPS), np.int64(FPS), int(FPS)], ids=["float32", "int64", "int"])
def test_a_numpy_or_int_fps_gives_the_same_json_record(fps):
    frames = np.random.default_rng(3).random((20, 4, 3), dtype=np.float32)
    record = measure(frames, fps).to_json()
    assert json.dumps(record, allow_nan=False) == json.dumps(measure(frames, FPS).to_json())


def test_the_record_is_json_with_units_rounded_and_named():
    m = measure(_strobe(2.0, seconds=1.0), FPS)
    record = m.to_json()
    assert list(record) == [f.name for f in fields(Metrics)]
    assert record["frames"] == 60 and record["pixels"] == 8 and record["seconds"] == 1.0
    assert all(round(v, 4) == v for v in record.values())
    json.dumps(record, allow_nan=False)


def test_the_same_frames_give_the_same_record():
    frames = np.random.default_rng(7).random((40, 32, 3), dtype=np.float32)
    assert json.dumps(measure(frames, FPS).to_json()) == json.dumps(measure(frames.copy(), FPS).to_json())


@pytest.mark.parametrize(("frames", "pixels"), [(1, 4), (10, 4), (5, 0), (1, 1)])
def test_short_and_empty_sequences_measure_without_error(frames, pixels):
    m = measure(np.full((frames, pixels, 3), 0.5, np.float32), FPS)
    assert m.frames == frames and m.pixels == pixels
    assert all(math.isfinite(v) for v in m.to_json().values())


def test_the_metrics_do_not_depend_on_the_frames_memory_layout():
    """A fancy-indexed, Fortran-order or transposed view sums in another
    order than a C-contiguous copy of the same pixels; measure reads one
    layout, so the floats agree to the bit."""
    rng = np.random.default_rng(0)
    for _ in range(30):
        frames = rng.random((20, 64, 3), dtype=np.float32)
        views = (frames[:, rng.permutation(64)], np.asfortranarray(frames),
                 np.ascontiguousarray(frames.transpose(1, 0, 2)).transpose(1, 0, 2))
        for view in views:
            assert measure(view, FPS) == measure(np.ascontiguousarray(view), FPS)


def test_a_sequence_under_a_second_counts_as_one_window():
    """6 frames at 60 fps holding two full swings: one flash in the window."""
    assert flash_rates(_grey([0, 1, 1, 0, 0, 0], 1), FPS).tolist() == [1.0]


@pytest.mark.parametrize(
    ("frames", "fps", "says"),
    [
        (np.zeros((0, 4, 3), np.float32), FPS, "F >= 1"),
        (np.zeros((4, 3), np.float32), FPS, "(F, N, 3)"),
        (np.zeros((2, 4, 4), np.float32), FPS, "(2, 4, 4)"),
        (np.zeros((2, 4, 3), np.uint8), FPS, "divided by 255"),
        (np.zeros((2, 4, 3), np.float32), 0.0, "fps must be a positive number"),
        (np.zeros((2, 4, 3), np.float32), math.nan, "fps must be a positive number"),
    ],
)
def test_bad_input_is_refused_with_what_was_wrong(frames, fps, says):
    with pytest.raises(ValueError) as caught:
        measure(frames, fps)
    assert says in str(caught.value)
