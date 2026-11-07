"""Golden-frame regression for the built-in gallery patterns
(src/pewpew/patterns/): fixed seed -> the engine's own deterministic
timeline -> N frames -> perceptual comparison against a committed baseline
(architecture.md §8 item 4).

30 frames rather than the study's 120 — this is a regression tripwire, not
the equivalence proof (that's test_port_equivalence.py, which is exact and
uses the full 120). The engine's own timeline is `render_sequence`'s
internal `t += 1/fps` accumulation, not `harness.clock.FakeClock` — the
engine does not depend on the harness (render.py docstring).

The canopy set renders on the 3,840-px canopy through its grouping. Its
baselines keep every 16th pixel (four per bar, every frame), which keeps each
file small; the determinism check compares every pixel.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from harness.goldens import assert_matches_golden
from pewpew import Grouping, render_sequence
from pewpew.classinfo import pattern_name
from pewpew.metrics import LIVENESS_RMS, rms
from pewpew.patterns import STUDY_CASES, Comet, Fire, Sparkle

GOLDENS = Path(__file__).parent / "goldens"

SEED = 42
FPS = 60.0
N_FRAMES = 30
ROOM_STRIDE = 16

# Each pattern on the fixture it was written for; the frame count above is
# this file's own (the study ran 120).
CASES = [
    pytest.param(cls, mapping, grouping, id=pattern_name(cls)) for cls, mapping, grouping in STUDY_CASES
]


def _render(pattern_cls, mapping: np.ndarray, grouping: Grouping | None) -> np.ndarray:
    return render_sequence(
        pattern_cls, mapping, seed=SEED, frames=N_FRAMES, fps=FPS, grouping=grouping
    )


@pytest.mark.parametrize("pattern_cls, mapping, grouping", CASES)
def test_pattern_matches_golden(
    pattern_cls, mapping: np.ndarray, grouping: Grouping | None, regen_goldens: bool
) -> None:
    frames = _render(pattern_cls, mapping, grouping)
    assert_matches_golden(
        GOLDENS / f"{pattern_name(pattern_cls)}.npz",
        frames if grouping is None else frames[:, ::ROOM_STRIDE],
        regen=regen_goldens,
    )


@pytest.mark.parametrize("pattern_cls, mapping, grouping", CASES)
def test_pattern_is_deterministic(
    pattern_cls, mapping: np.ndarray, grouping: Grouping | None
) -> None:
    a, b = _render(pattern_cls, mapping, grouping), _render(pattern_cls, mapping, grouping)
    assert a.tobytes() == b.tobytes()


SEEDED = [case for case in CASES if case.values[0] in (Comet, Fire, Sparkle)]  # the seed's readers


@pytest.mark.parametrize("pattern_cls, mapping, grouping", SEEDED)
def test_the_seed_changes_the_picture(pattern_cls, mapping: np.ndarray, grouping: Grouping | None) -> None:
    """The goldens pin one seed; a renderer that ignored it would pass them.
    Same bar the liveness check holds params to: an input that does not
    change the picture is not an input."""
    one, two = (
        render_sequence(pattern_cls, mapping, seed=seed, frames=N_FRAMES, fps=FPS, grouping=grouping)
        for seed in (1, 2)
    )
    assert rms(one, two) > LIVENESS_RMS
