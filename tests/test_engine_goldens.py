"""Golden-frame regression for the five built-in gallery patterns
(src/pewpew/patterns/), following the idiom in test_golden_frames.py: fixed
seed -> the engine's own deterministic timeline -> N frames -> perceptual
comparison against a committed baseline.

30 frames rather than the study's 120 — this is a regression tripwire, not
the equivalence proof (that's test_port_equivalence.py, which is exact and
uses the full 120). The engine's own timeline is `render_sequence`'s
internal `t += 1/fps` accumulation, not `harness.clock.FakeClock` — the
engine does not depend on the harness (render.py docstring).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from harness.goldens import assert_matches_golden, rms
from pewpew import grid, lattice, line, render_sequence
from pewpew.patterns import Comet, Fire, Geq, Plasma, Sdf3d

GOLDENS = Path(__file__).parent / "goldens"

SEED = 42
FPS = 60.0
N_FRAMES = 30

CASES = [
    pytest.param(Plasma, line(300), id="plasma"),
    pytest.param(Comet, line(300), id="comet"),
    pytest.param(Geq, grid(16, 16), id="geq"),
    pytest.param(Fire, grid(16, 32), id="fire"),
    pytest.param(Sdf3d, lattice(10), id="sdf3d"),
]


def _render(pattern_cls, mapping: np.ndarray) -> np.ndarray:
    return render_sequence(pattern_cls, mapping, seed=SEED, frames=N_FRAMES, fps=FPS)


@pytest.mark.parametrize("pattern_cls, mapping", CASES)
def test_pattern_matches_golden(pattern_cls, mapping: np.ndarray, regen_goldens: bool) -> None:
    assert_matches_golden(
        GOLDENS / f"{pattern_cls.name}.npz",
        _render(pattern_cls, mapping),
        regen=regen_goldens,
    )


@pytest.mark.parametrize("pattern_cls, mapping", CASES)
def test_pattern_is_deterministic(pattern_cls, mapping: np.ndarray) -> None:
    a, b = _render(pattern_cls, mapping), _render(pattern_cls, mapping)
    assert rms(a, b) == 0.0
