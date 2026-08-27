"""Param-liveness: every declared knob must change what you see.

The sdf3d `spin` parameter is a mathematical no-op — the torus is centered on
the y-axis and `render` rotates about that same axis, an invariance the SDF has
by construction — and nothing caught it. Not the authoring surface, which
cannot see that a parameter is *semantically* dead, and not golden frames,
because a beat pulse and a hue shimmer masked it
(`bench/results/authoring-2026-07-16.md`, addendum 2026-07-16). This is the
check that would have.

Method: render one pattern twice, identical in every respect except that a
single knob is held at `lo` in the first run and `hi` in the second, and
require the two sequences to differ. Endpoints rather than a nudge, because
that puts the declared range under test as well: a range too narrow to change
the picture is as dead as a parameter nothing reads.

This is an L1 check (`research/synthesis/test-and-feedback.md`) — seeded,
reproducible, and hard-gating, which is the whole point. A dead knob is
supposed to fail the build, not earn a note in a report.
"""

from __future__ import annotations

import numpy as np
import pytest

from harness.goldens import LIVENESS_RMS, rms
from pewpew import declared_params, render_sequence
from pewpew.patterns import STUDY_CASES

SEED = 42
FPS = 60.0
# Matches tests/test_engine_goldens.py. Half a second is long enough for the
# slowest knobs here — the fade/decay ones — to separate; a knob that needs
# longer than that to show should say so by failing, not pass quietly.
N_FRAMES = 30

# A knob that is known dead and deliberately staying that way. `strict=True` is
# load-bearing: if the parameter ever comes alive, this XPASSes and fails the
# suite, so an exemption cannot outlive the bug it documents.
KNOWN_DEAD = {
    ("sdf3d", "spin"): pytest.mark.xfail(
        strict=True,
        reason=(
            "Known dead: the torus is centered on the y-axis and render() rotates "
            "about that same axis, an invariance the SDF has by construction "
            "(bench/results/authoring-2026-07-16.md, addendum). sdf3d is frozen "
            "study evidence — test_port_equivalence.py holds it bit-identical to "
            "the prototype — so the bug stays put and this check proves itself "
            "against it. If this XPASSes, spin came alive: delete this entry."
        ),
    ),
}


def _cases() -> list[pytest.ParameterSet]:
    """One case per (pattern, declared knob) — nine today, and self-extending:
    a new `Param` on any gallery pattern gets checked with no edit here."""
    return [
        pytest.param(
            pattern_cls,
            mapping,
            name,
            marks=KNOWN_DEAD.get((pattern_cls.name, name), ()),
            id=f"{pattern_cls.name}-{name}",
        )
        for pattern_cls, mapping in STUDY_CASES
        for name in declared_params(pattern_cls)
    ]


@pytest.mark.parametrize("pattern_cls, mapping, name", _cases())
def test_param_changes_the_picture(
    pattern_cls: type, mapping: np.ndarray, name: str
) -> None:
    param = declared_params(pattern_cls)[name]
    low, high = (
        render_sequence(
            pattern_cls, mapping, {name: value}, seed=SEED, frames=N_FRAMES, fps=FPS
        )
        for value in (param.lo, param.hi)
    )
    observed = rms(low, high)
    assert observed > LIVENESS_RMS, (
        f"{pattern_cls.name}.{name} is dead. Moving it across its entire declared "
        f"range ({param.lo} -> {param.hi}) changed the {N_FRAMES}-frame sequence by "
        f"rms {observed:.3g}, under the {LIVENESS_RMS} bar. Either nothing reads it "
        f"in a way that reaches a pixel, or the range is too narrow to matter."
    )
