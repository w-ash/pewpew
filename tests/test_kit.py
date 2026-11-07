"""Tests for the idiom kit (src/pewpew/kit.py).

Two groups: the shapers (`wave`, `triangle`, `square`, `hsv`, `time`), and
the four authoring-surface helpers the 2026-07-16 study made ADR-005
conditional on (bench/results/authoring-2026-07-16.md, "Verdict"):
`fade`, `bins`, `sample2d`, `hash01`.

Every new-helper test inlines the literal expression it replaces, copied
from the frozen study evidence in `bench/authoring/*.py`, as the reference
— and asserts bit-exact (`==` / `np.array_equal`) agreement with it, not
"close enough". Several tests also demonstrate the specific edge or dtype
trap each helper exists to remove (stumble numbers in the inventory).
"""

from __future__ import annotations

import math
import textwrap
from functools import partial

import numpy as np
import pytest

from fakes import run_python
from pewpew import kit
from pewpew.kit import TWO_PI, bins, fade, hash01, hsv, sample2d, square, time, triangle, wave
from pewpew.mapping import grid, line

DT = 1.0 / 60.0  # the engine's fixed study/test frame rate


# ---- the shapers ------------------------------------------------------------


def test_time_is_a_scaled_sawtooth_scoped_by_frame_time():
    # interval=1.0 -> period = 65.536s (Pixelblaze scaling, kit.py docstring).
    with kit._frame_time(0.0):
        assert time(1.0) == 0.0
    with kit._frame_time(65.536 * 0.25):
        assert time(1.0) == pytest.approx(0.25)
    with kit._frame_time(65.536 * 1.5):  # past one period: wraps
        assert time(1.0) == pytest.approx(0.5)


def test_wave_matches_reference_sine_shaping():
    p = np.linspace(-2.0, 2.0, 401, dtype=np.float32)
    expected = 0.5 + 0.5 * np.sin(TWO_PI * np.asarray(p))
    assert np.array_equal(wave(p), expected)
    assert wave(0.0) == 0.5  # rising through the midpoint at phase 0


def test_triangle_matches_reference_and_ranges_0_1():
    p = np.linspace(-2.0, 2.0, 401, dtype=np.float32)
    expected = 1.0 - np.abs(2.0 * (np.asarray(p) % 1.0) - 1.0)
    assert np.array_equal(triangle(p), expected)
    assert triangle(0.0) == 0.0
    assert triangle(0.5) == 1.0


def test_square_matches_reference_and_honours_duty():
    p = np.linspace(0.0, 1.0, 101, dtype=np.float32)
    expected = np.where((np.asarray(p) % 1.0) < 0.5, 1.0, 0.0)
    assert np.array_equal(square(p), expected)
    expected_duty = np.where((np.asarray(p) % 1.0) < 0.2, 1.0, 0.0)
    assert np.array_equal(square(p, duty=0.2), expected_duty)


def test_hsv_matches_reference_and_stays_in_range():
    h = np.linspace(0.0, 1.0, 64, dtype=np.float32)
    out = hsv(h, 1.0, 1.0)
    assert out.dtype == np.float32
    assert out.shape == (64, 3)
    assert np.all((out >= 0.0) & (out <= 1.0))
    assert np.array_equal(out[0], np.array([1.0, 0.0, 0.0], dtype=np.float32))  # h=0 -> red


# ---- fade(dt, tau) — stumble #2 --------------------------------------------


# Comet.tail and Geq.fall, the Param defaults in bench/authoring/.
@pytest.mark.parametrize("tau", [0.25, 0.35], ids=["comet-tail", "geq-fall"])
def test_fade_matches_the_study_expression(tau):
    assert fade(DT, tau) == math.exp(-DT / tau)


def test_fade_returns_a_python_float_not_a_numpy_scalar():
    # A numpy scalar here can silently promote a downstream dtype.
    assert type(fade(DT, 0.25)) is float


# ---- bins(x, n) — stumble #9 (hit) -----------------------------------------


def test_bins_matches_geq_study_expression():
    x = grid(16, 16)[:, 0]  # Geq's actual study fixture
    expected = np.minimum((x * 16.0).astype(np.int32), 15)
    assert np.array_equal(bins(x, 16), expected)


def test_bins_clamps_both_edges():
    # STUMBLE-9: int(x * 16) at x==1.0 (rightmost pixel of an inclusive 0-1
    # mapping) lands in bin 16, one past the array — the study verified this
    # by running the unclamped expression. Confirm the bug is real, then
    # confirm bins() removes it.
    x = np.array([1.0], dtype=np.float32)
    unclamped = (x * 16.0).astype(np.int32)
    assert unclamped[0] == 16
    assert bins(x, 16)[0] == 15
    # Below 0 an index wraps to the far end of the band array and quietly
    # reads another band; imported maps can sit slightly out of range.
    assert bins(np.array([-0.2, -5.0], np.float32), 16).tolist() == [0, 0]


def test_bins_clamps_far_and_infinite_x_the_same_on_every_platform():
    # A warped x can land far outside 0-1. Cast to int32 before the clamp, a
    # value past the int32 range is undefined: arm64 saturates, x86-64 gives
    # INT_MIN (band 0 for a far positive x), and numpy warns.
    x = np.array([np.inf, -np.inf, 3e9, -3e9, 1.4e8], np.float32)
    assert bins(x, 16).tolist() == [15, 0, 15, 0, 15]


def test_a_nan_coordinate_reads_index_0_on_every_platform():
    # NaN cast to int32 gives 0 on arm64 and INT_MIN on x86-64, where a
    # lookup table then raises IndexError. The suite turns numpy's cast
    # warning into an error, so this also proves no NaN reaches the cast.
    nan = np.array([np.nan, 0.5], np.float32)
    assert bins(nan, 16).tolist() == [0, 8]
    field = np.arange(16, dtype=np.float32).reshape(4, 4)
    assert sample2d(field, nan, np.array([0.0, np.nan], np.float32)).tolist() == [0.0, 2.0]
    from pewpew.color import EMBER, gradient_lut, sample

    np.testing.assert_array_equal(sample(gradient_lut(EMBER), nan)[0], gradient_lut(EMBER)[0])


def test_bins_generalizes_n():
    x = np.array([0.0, 0.5, 0.999, 1.0], dtype=np.float32)
    for n in (4, 15, 32):
        expected = np.minimum((x * n).astype(np.int32), n - 1)
        assert np.array_equal(bins(x, n), expected)
        assert bins(x, n).max() <= n - 1


# ---- sample2d(field, x, y) — stumbles #12 (headline hit) / #15 ------------


def test_sample2d_matches_fire_study_expression():
    w, h = 16, 32  # Fire.W, Fire.H, bench/authoring/fire.py
    heat = np.random.default_rng(7).random((h, w), dtype=np.float32)
    coords = grid(w, h)  # Fire's actual study fixture
    x, y = coords[:, 0], coords[:, 1]

    ci = np.minimum((x * (w - 1) + 0.5).astype(np.int32), w - 1)
    ri = np.minimum((y * (h - 1) + 0.5).astype(np.int32), h - 1)
    expected = heat[ri, ci]

    assert np.array_equal(sample2d(heat, x, y), expected)


def test_sample2d_clamps_both_edges():
    # STUMBLE-15: x==1.0 / y==1.0 rounds one cell past the field's last row
    # or column without the edge clamp (the same trap as #9, one dimension
    # richer).
    w, h = 16, 32
    heat = np.arange(h * w, dtype=np.float32).reshape(h, w)
    for at, cell in ((1.0, (h - 1, w - 1)), (1.5, (h - 1, w - 1)), (-0.2, (0, 0))):
        assert sample2d(heat, np.array([at], np.float32), np.array([at], np.float32))[0] == heat[cell], at


def test_sample2d_clamps_far_and_infinite_coordinates_the_same_on_every_platform():
    # As for bins: the clamp comes before the int32 cast.
    w, h = 16, 32
    heat = np.arange(h * w, dtype=np.float32).reshape(h, w)
    for at, cell in ((np.inf, (h - 1, w - 1)), (3e9, (h - 1, w - 1)), (-np.inf, (0, 0)), (-3e9, (0, 0))):
        assert sample2d(heat, np.array([at], np.float32), np.array([at], np.float32))[0] == heat[cell], at


def test_sample2d_rejects_non_2d_field():
    with pytest.raises(ValueError):
        sample2d(np.zeros(4, dtype=np.float32), np.array([0.0]), np.array([0.0]))
    with pytest.raises(ValueError):
        sample2d(np.zeros((2, 2, 2), dtype=np.float32), np.array([0.0]), np.array([0.0]))


# ---- hash01(x, seed, salt) — stumble #6 (hit) ------------------------------

COMET_SEED = 42  # bench_authoring.py SEED, passed to every study pattern's _setup


def test_hash01_matches_comet_study_expression():
    x = line(300)[:, 0]  # Comet's actual study fixture
    for salt in (0, 5, 10, 15):  # spans the comet's real 120-frame salt range
        x64 = x.astype(np.float64)
        expected = (np.sin(12.9898 * x64 + COMET_SEED + salt) * 43758.5453) % 1.0
        assert np.array_equal(hash01(x, COMET_SEED, salt), expected)


def test_hash01_seed_salt_addition_order_is_load_bearing():
    """A single pre-summed `salt` is NOT bit-exact with the study's two-step
    `self.seed + salt`: float addition is not associative, and empirically,
    across the comet's real 120-frame study run (seed=42, x=line(300)), the
    two associations diverge by 1 ulp on 46 of the 120 frames (every frame
    from salt=10 onward). That is why hash01 takes `seed` and `salt` as two
    separate arguments, added in the study's left-to-right order, instead of
    one combined value.
    """
    x = line(300)[:, 0].astype(np.float64)
    seed, salt = 42, 10  # first divergent salt in the study's own run

    two_step = (np.sin(12.9898 * x + seed + salt) * 43758.5453) % 1.0
    presummed = seed + salt
    one_step = (np.sin(12.9898 * x + presummed) * 43758.5453) % 1.0

    assert not np.array_equal(two_step, one_step)  # demonstrates the trap
    assert np.array_equal(hash01(x, seed, salt), two_step)  # hash01 avoids it


def test_hash01_float64_promotion_diverges_from_a_float32_path():
    """STUMBLE-6, reproduced concretely: at frame 0 (seed=42, salt=0) of the
    comet's line(300) study run, pixel 60 (x ~= 0.2006689) sits on opposite
    sides of the 0.995 sparkle threshold depending on dtype — float64 puts
    it just above (sparks), a float32 pipeline puts it well below (silent).
    """
    x = line(300)[:, 0]
    seed, salt = 42, 0
    i = 60

    f64 = hash01(x, seed, salt)
    assert f64.dtype == np.float64
    assert f64[i] > 0.995

    x32 = x.astype(np.float32)
    f32 = (
        np.float32(12.9898) * x32 + np.float32(seed) + np.float32(salt)
    )
    f32 = (np.sin(f32) * np.float32(43758.5453)) % np.float32(1.0)
    assert f32[i] < 0.995  # same pixel, same salt: float32 misses the spark


# ---- wiring -----------------------------------------------------------------


def test_new_helpers_are_exported_from_pewpew_top_level():
    import pewpew

    assert pewpew.fade is fade
    assert pewpew.bins is bins
    assert pewpew.sample2d is sample2d
    assert pewpew.hash01 is hash01


# What a new process loads with `import pewpew`, run on the suite's process
# pool (conftest.py).
JOBS = {"loaded": partial(
    run_python, "import pewpew, sys; print(sorted(m for m in sys.modules if m.startswith(('pewpew', 'websockets'))))")}


def test_importing_pewpew_loads_only_the_authoring_core(pooled):
    """A pattern file's `from pewpew import ...` must not start the engine's
    transports: no loop, no sink, no room compiler, no websocket server."""
    loaded = pooled["loaded"].stdout
    for module in ("pewpew.pace", "pewpew.sinks", "pewpew.room", "pewpew.load", "pewpew.patterns", "websockets"):
        assert f"'{module}" not in loaded, module


def test_the_package_example_renders(tmp_path):
    """The example in `pewpew.__doc__` is the front door: it must load and
    render a moving picture with no contained error."""
    import pewpew
    from pewpew.load import load_file
    from pewpew.render import Renderer

    lines = pewpew.__doc__.splitlines()
    start = lines.index("    from pewpew import Color, Float, Pattern, wave")
    end = next(i for i in range(start, len(lines)) if lines[i] and not lines[i].startswith("    "))
    path = tmp_path / "example.py"
    path.write_text(textwrap.dedent("\n".join(lines[start:end])))
    renderer = Renderer(load_file(path, attr=None).cls(), line(8))
    first, second = renderer.advance_to(0.25).copy(), renderer.advance_to(0.5)
    assert renderer.error is None
    assert not np.array_equal(first, second)
