"""pewpew.color: OKLab conversions, gradient tables and the presets.

A gradient blends in OKLab so a blend keeps its hue, and a blend that
leaves the gamut gives up chroma, never hue or lightness. Each stop's color
is the color `pewpew.hsv` gives, so a palette and a color param agree.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from harness.goldens import assert_matches_golden
from pewpew.color import EMBER, LUT_SIZE, OCEAN, PRESETS, gradient_lut, linear_srgb, oklab, sample, turn_hue
from pewpew.kit import hsv
from pewpew.mapping import line
from pewpew.params import HSV, Gradient, Palette, Stop

GOLDENS = Path(__file__).parent / "goldens"


def gradient(*stops: tuple[float, HSV]) -> Gradient:
    return Gradient(tuple(Stop(at, color) for at, color in stops))


def hue(lab: np.ndarray) -> np.ndarray:
    """The OKLab hue of each color, in degrees."""
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))


def chroma(lab: np.ndarray) -> np.ndarray:
    return np.hypot(lab[..., 1], lab[..., 2])


BLUE, WHITE, RED, YELLOW = HSV(240.0, 1.0, 1.0), HSV(0.0, 0.0, 1.0), HSV(0.0, 1.0, 1.0), HSV(60.0, 1.0, 1.0)


# ---- OKLab ------------------------------------------------------------------------


def test_oklab_round_trips_in_float32() -> None:
    rgb = np.random.default_rng(7).random((20_000, 3), dtype=np.float32)
    rgb = np.concatenate([rgb, np.eye(3, dtype=np.float32), np.zeros((1, 3), np.float32), np.ones((1, 3), np.float32)])
    lab = oklab(rgb)
    assert lab.dtype == np.float32 and linear_srgb(lab).dtype == np.float32
    assert np.abs(linear_srgb(lab) - rgb).max() < 1e-5


def test_white_is_lightness_one_and_black_is_zero() -> None:
    np.testing.assert_allclose(oklab([[1.0, 1.0, 1.0], [0.0, 0.0, 0.0]]), [[1, 0, 0], [0, 0, 0]], atol=1e-6)


# ---- gradient tables --------------------------------------------------------------


def test_a_blend_from_blue_to_white_stays_blue() -> None:
    """In HSV or CIELAB the blend drifts purple; in OKLab every entry keeps
    blue's hue while its lightness climbs to white."""
    lab = oklab(gradient_lut(gradient((0.0, BLUE), (1.0, WHITE))))
    tinted = chroma(lab) > 0.02
    assert tinted.sum() > LUT_SIZE // 2
    assert np.abs(hue(lab[tinted]) - hue(oklab(hsv(BLUE.turn, BLUE.s, BLUE.v)))).max() < 0.5
    assert np.all(np.diff(lab[:, 0]) > 0)


@pytest.mark.parametrize(("preset", "shift"), [(EMBER, 180.0), (EMBER, 30.0), (OCEAN, 180.0), (PRESETS[3], 90.0)])
def test_a_turned_gradient_keeps_each_hue_and_gives_up_chroma(preset: Gradient, shift: float) -> None:
    """A palette's `shift` turns its stops, then fits the gamut as any blend
    does: turned, most of these leave the gamut, and none moves its hue,
    where clipping each channel moved hues by up to 19°."""
    plain, turned = oklab(gradient_lut(preset)), oklab(gradient_lut(preset, shift))
    coloured = chroma(turned) > 0.02
    assert coloured.sum() > LUT_SIZE // 2
    error = (hue(turned) - hue(plain) - shift + 180.0) % 360.0 - 180.0
    assert np.abs(error[coloured]).max() < 1.0
    np.testing.assert_allclose(turned[:, 0], plain[:, 0], atol=2e-3)  # lightness kept


def test_a_blend_outside_the_gamut_gives_up_chroma_only() -> None:
    """Red to yellow bulges past the gamut in OKLab. Those entries keep the
    blend's lightness and hue and lose just enough chroma to fit, so one
    channel sits on the gamut's edge; no channel is clamped on its own."""
    lut = gradient_lut(gradient((0.0, RED), (1.0, YELLOW)))
    ends = oklab(np.stack([hsv(c.turn, c.s, c.v) for c in (RED, YELLOW)]))
    x = (np.arange(LUT_SIZE, dtype=np.float32) + 0.5) / LUT_SIZE
    blend = ends[0] + (ends[1] - ends[0]) * x[:, None]
    raw = linear_srgb(blend)
    out = np.any((raw < -1e-5) | (raw > 1 + 1e-5), axis=-1)
    assert out.sum() > LUT_SIZE // 4  # the case the test is for
    assert lut.min() >= 0.0 and lut.max() <= 1.0
    lab = oklab(lut[out])
    np.testing.assert_allclose(lab[:, 0], blend[out, 0], atol=1e-4)
    assert np.abs(hue(lab) - hue(blend[out])).max() < 0.5
    assert np.all(chroma(lab) < chroma(blend[out]))
    edge = np.minimum(lut[out].min(axis=-1), 1.0 - lut[out].max(axis=-1))
    assert edge.max() < 1e-4


def test_a_stop_color_is_the_color_hsv_gives() -> None:
    """One color model: a flat gradient is its stop's `pewpew.hsv` color."""
    teal = HSV(170.0, 0.6, 0.8)
    lut = gradient_lut(gradient((0.0, teal), (1.0, teal)))
    np.testing.assert_allclose(lut, np.broadcast_to(teal.rgb(np.ones(1, np.float32)), lut.shape), atol=1e-5)


def test_two_stops_at_one_position_make_a_hard_edge() -> None:
    lut = gradient_lut(gradient((0.0, RED), (0.5, RED), (0.5, BLUE), (1.0, BLUE)))
    half = LUT_SIZE // 2
    np.testing.assert_allclose(lut[:half], np.broadcast_to(hsv(0.0, 1.0, 1.0), (half, 3)), atol=1e-5)
    np.testing.assert_allclose(lut[half:], np.broadcast_to(hsv(2 / 3, 1.0, 1.0), (half, 3)), atol=1e-5)


@pytest.mark.parametrize("preset", PRESETS, ids=lambda g: g.label)
def test_preset_table_matches_golden(preset: Gradient, regen_goldens: bool) -> None:
    assert_matches_golden(GOLDENS / f"palette_{preset.label}.npz", gradient_lut(preset)[None], regen=regen_goldens)


def test_a_table_is_deterministic_cached_by_value_and_read_only() -> None:
    first = gradient_lut(EMBER)
    copy = Gradient(tuple(Stop(s.at, HSV(s.color.h, s.color.s, s.color.v)) for s in EMBER.stops), EMBER.label)
    assert gradient_lut(copy) is first
    gradient_lut.cache_clear()
    assert gradient_lut(EMBER).tobytes() == first.tobytes()
    with pytest.raises(ValueError, match="read-only"):
        first[0, 0] = 1.0
    assert first.shape == (LUT_SIZE, 3) and first.dtype == np.float32


def test_sample_reads_the_nearest_entry_and_clamps() -> None:
    lut = gradient_lut(OCEAN)
    t = np.array([0.25, 0.0, -0.5, 0.999999, 1.0, 1.5], dtype=np.float32)
    got = sample(lut, t)
    assert got.shape == (6, 3) and got.dtype == np.float32
    np.testing.assert_array_equal(got[0], lut[LUT_SIZE // 4])
    np.testing.assert_array_equal(got[1:3], np.broadcast_to(lut[0], (2, 3)))
    np.testing.assert_array_equal(got[3:], np.broadcast_to(lut[-1], (3, 3)))


def test_a_strip_draws_the_whole_gradient_end_to_end() -> None:
    """A strip's last pixel sits at x = 1, so it shows the last stop."""
    lut = gradient_lut(EMBER)
    got = sample(lut, line(8)[:, 0])
    np.testing.assert_array_equal(got[[0, -1]], lut[[0, -1]])


# ---- presets ----------------------------------------------------------------------


def test_every_preset_is_a_palette_value_with_its_own_label() -> None:
    assert 6 <= len(PRESETS) <= 10
    assert len({p.label for p in PRESETS}) == len(PRESETS)
    palette = Palette(EMBER, presets=PRESETS)
    for preset in PRESETS:
        assert palette.parse("p", palette.to_json(preset)) == (preset, None)
        lut = gradient_lut(preset)
        assert np.isfinite(lut).all() and lut.min() >= 0.0 and lut.max() <= 1.0


def test_a_palette_reads_as_a_frame_as_a_color_does() -> None:
    """`self.palette.rgb(x)` mirrors `self.color.rgb(level)`: the table,
    read per pixel, clamped past either end."""
    x = np.array([-0.5, 0.0, 0.3, 1.0, 1.5], np.float32)
    np.testing.assert_array_equal(EMBER.rgb(x), sample(gradient_lut(EMBER), x))
    assert EMBER.rgb(x).shape == (5, 3) and EMBER.rgb(x).dtype == np.float32


def test_turning_a_hue_keeps_lightness_and_a_whole_turn_is_none() -> None:
    rgb = np.array([[0.8, 0.2, 0.1], [0.1, 0.3, 0.6], [0.5, 0.5, 0.5]], np.float32)
    turned = turn_hue(rgb, 120.0)
    assert turned.dtype == np.float32
    np.testing.assert_allclose(oklab(turned)[:2, 0], oklab(rgb)[:2, 0], atol=2e-3)  # in gamut: L stays
    np.testing.assert_allclose(turned[2], rgb[2], atol=1e-5)  # grey has no hue to turn
    assert np.argmax(turned[0]) != np.argmax(rgb[0])
    np.testing.assert_allclose(turn_hue(rgb, 360.0), rgb, atol=1e-5)
