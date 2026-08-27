"""Golden-frame loop, exercised end to end on the reference pattern.

This is the shape every engine pattern test will take: fixed seed + fake
clock -> N frames -> perceptual comparison against a committed baseline
(architecture.md §8 item 4; no surveyed project does this [S516][S517]).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from harness.clock import FakeClock
from harness.goldens import LIVENESS_RMS, assert_matches_golden, rms
from harness.pattern import line_mapping
from harness.patterns.solid_pulse import SolidPulse

GOLDENS = Path(__file__).parent / "goldens"

N_PIXELS = 64
N_FRAMES = 30
SEED = 1234


def render_frames() -> np.ndarray:
    pattern = SolidPulse()
    mapping = line_mapping(N_PIXELS)
    clock = FakeClock()
    frames = [
        pattern.render(t, mapping, {"rate_hz": 0.5}, SEED)
        for t in clock.frames(N_FRAMES, fps=60.0)
    ]
    return np.stack(frames)


def test_solid_pulse_matches_golden(regen_goldens: bool) -> None:
    assert_matches_golden(
        GOLDENS / "solid_pulse.npz",
        render_frames(),
        regen=regen_goldens,
    )


def test_render_is_deterministic() -> None:
    a, b = render_frames(), render_frames()
    assert rms(a, b) == 0.0


def test_seed_changes_output() -> None:
    pattern = SolidPulse()
    mapping = line_mapping(N_PIXELS)
    a = pattern.render(0.5, mapping, {}, seed=1)
    b = pattern.render(0.5, mapping, {}, seed=2)
    # Same bar tests/test_param_liveness.py holds parameters to: an input that
    # does not change the picture is not an input.
    assert rms(a, b) > LIVENESS_RMS
