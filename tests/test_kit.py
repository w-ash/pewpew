"""Tests for the idiom kit (src/pewpew/kit.py).

Two groups: the shapers (`wave`, `hsv`), and the authoring-surface
helpers the 2026-07-16 study made ADR-005 conditional on
(bench/results/authoring-2026-07-16.md, "Verdict"): `fade`, `bins`.

Every helper test inlines the literal expression it replaces, copied
from the frozen study evidence in `bench/authoring/*.py`, as the reference
— and asserts bit-exact (`==` / `np.array_equal`) agreement with it, not
"close enough". Several tests also demonstrate the specific edge or dtype
trap each helper exists to remove (stumble numbers in the inventory).
"""

from __future__ import annotations

import math
from functools import partial

import numpy as np
import pytest

from fakes import run_python
from pewpew.kit import TWO_PI, bins, fade, hsv, wave
from pewpew.mapping import grid

DT = 1.0 / 60.0  # the engine's fixed study/test frame rate


# ---- the shapers ------------------------------------------------------------


def test_wave_matches_reference_sine_shaping():
    p = np.linspace(-2.0, 2.0, 401, dtype=np.float32)
    expected = 0.5 + 0.5 * np.sin(TWO_PI * np.asarray(p))
    assert np.array_equal(wave(p), expected)
    assert wave(0.0) == 0.5  # rising through the midpoint at phase 0


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
    from pewpew.color import EMBER, gradient_lut, sample

    np.testing.assert_array_equal(sample(gradient_lut(EMBER), nan)[0], gradient_lut(EMBER)[0])


def test_bins_generalizes_n():
    x = np.array([0.0, 0.5, 0.999, 1.0], dtype=np.float32)
    for n in (4, 15, 32):
        expected = np.minimum((x * n).astype(np.int32), n - 1)
        assert np.array_equal(bins(x, n), expected)
        assert bins(x, n).max() <= n - 1


# ---- wiring -----------------------------------------------------------------


# What a new process loads with `import pewpew`, run on the suite's process
# pool (conftest.py).
JOBS = {"loaded": partial(
    run_python, "import pewpew, sys; print(sorted(m for m in sys.modules if m.startswith(('pewpew', 'websockets'))))")}


def test_importing_pewpew_loads_no_engine_code(pooled):
    """`import pewpew` must not start the engine's transports: no loop, no
    sink, no room compiler, no aura, no websocket server."""
    loaded = pooled["loaded"].stdout
    for module in ("pewpew.pace", "pewpew.sinks", "pewpew.room", "pewpew.aura", "websockets"):
        assert f"'{module}" not in loaded, module
