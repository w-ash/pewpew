"""Tests for the shared scalar helpers in pewpew.fx.prims.vec: `wave`, `fade`.

Each test inlines the literal expression the helper replaces (from the
authoring study, bench/results/authoring-2026-07-16.md) and asserts
bit-exact agreement with it.
"""

from __future__ import annotations

import math
from functools import partial

import numpy as np
import pytest

from fakes import run_python
from pewpew.fx.prims.vec import TWO_PI, fade, wave

DT = 1.0 / 60.0  # the engine's fixed study/test frame rate


def test_wave_matches_reference_sine_shaping():
    p = np.linspace(-2.0, 2.0, 401, dtype=np.float32)
    expected = 0.5 + 0.5 * np.sin(TWO_PI * np.asarray(p))
    assert np.array_equal(wave(p), expected)
    assert wave(0.0) == 0.5  # rising through the midpoint at phase 0


# ---- fade(dt, tau) — stumble #2 --------------------------------------------


# Comet.tail and Geq.fall, the study's Param defaults.
@pytest.mark.parametrize("tau", [0.25, 0.35], ids=["comet-tail", "geq-fall"])
def test_fade_matches_the_study_expression(tau):
    assert fade(DT, tau) == math.exp(-DT / tau)


def test_fade_returns_a_python_float_not_a_numpy_scalar():
    # A numpy scalar here can silently promote a downstream dtype.
    assert type(fade(DT, 0.25)) is float


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
