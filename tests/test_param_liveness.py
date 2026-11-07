"""Param liveness: every declared param must change what you see.

Render a pattern twice, one param at each value of a probe pair
(pewpew.params.probes), and require the two sequences to differ. Endpoints,
not a nudge, so a range too narrow to change the picture fails too. Neither
the authoring surface nor the goldens can see a param that is semantically
dead. `verify looks` applies the same method to every knob of a look
(pewpew.lab.liveness).
L1 (`research/synthesis/test-and-feedback.md`): seeded and hard-gating.
"""

from __future__ import annotations

import numpy as np
import pytest

from params_zoo import PARAM_CASES
from pewpew import Grouping, Renderer, render_sequence
from pewpew.classinfo import pattern_name
from pewpew.metrics import LIVENESS_RMS, rms
from pewpew.params import ParamSet
from pewpew.params.probes import probes
from pewpew.render import SlotClock

SEED = 42
FPS = 60.0
# Matches tests/test_engine_goldens.py. Half a second is long enough for the
# slowest params here — the fade/decay ones — to separate; a param that needs
# longer than that to show should say so by failing, not pass quietly.
N_FRAMES = 30

# A param that is known dead and deliberately staying that way. `strict=True` is
# load-bearing: if the parameter ever comes alive, this XPASSes and fails the
# suite, so an exemption cannot outlive the bug it documents.
KNOWN_DEAD = {
    ("sdf3d", "spin"): pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
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
    """One case per (pattern, probe), self-extending: a new param on any
    gallery pattern gets checked with no edit here."""
    return [
        pytest.param(
            pattern_cls, mapping, grouping, record["name"], a, b,
            marks=KNOWN_DEAD.get((pattern_name(pattern_cls), probe_id), ()),
            id=f"{pattern_name(pattern_cls)}-{probe_id}",
        )
        for pattern_cls, mapping, grouping in PARAM_CASES
        for record in ParamSet(pattern_cls).describe()
        for probe_id, a, b in probes(record)
    ]


@pytest.mark.parametrize("pattern_cls, mapping, grouping, name, a, b", _cases())
def test_param_changes_the_picture(
    pattern_cls: type, mapping: np.ndarray, grouping: Grouping | None, name: str, a: object, b: object
) -> None:
    low, high = (
        render_sequence(
            pattern_cls, mapping, params={name: value}, seed=SEED, frames=N_FRAMES, fps=FPS,
            grouping=grouping,
        )
        for value in (a, b)
    )
    observed = rms(low, high)
    assert observed > LIVENESS_RMS, (
        f"{pattern_name(pattern_cls)}.{name} is dead. Moving it from {a} to {b} changed the "
        f"{N_FRAMES}-frame sequence by rms {observed:.3g}, under the {LIVENESS_RMS} bar. "
        f"Either nothing reads it in a way that reaches a pixel, or the range is too "
        f"narrow to matter."
    )


def _sequence(renderer: Renderer, frames: int) -> np.ndarray:
    """The next `frames` frames off a live renderer, on the slot schedule
    `render_sequence` uses, continued from wherever the renderer already
    is so successive calls form one run."""
    clock = SlotClock(FPS, start=renderer.t)
    return np.stack([renderer.advance_to(clock.advance()).copy() for _ in range(frames)])


@pytest.mark.parametrize("pattern_cls, mapping, grouping, name, a, b", _cases())
def test_param_set_while_running_changes_the_picture(
    pattern_cls: type, mapping: np.ndarray, grouping: Grouping | None, name: str, a: object, b: object
) -> None:
    """The same bar, for a param set mid-run rather than at bind: it
    catches a control that moves and shows nothing, which the bind-time
    check above cannot see. A pattern that precomputes from a param in
    `setup` fails here."""
    half = N_FRAMES // 2

    held = Renderer(pattern_cls(), mapping, params={name: a}, seed=SEED, grouping=grouping)
    turned = Renderer(pattern_cls(), mapping, params={name: a}, seed=SEED, grouping=grouping)
    before = (_sequence(held, half), _sequence(turned, half))
    assert np.array_equal(*before), "the two runs must be identical until the param moves"

    turned.params.set(name, b)
    observed = rms(_sequence(held, half), _sequence(turned, half))
    assert observed > LIVENESS_RMS, (
        f"{pattern_name(pattern_cls)}.{name} does not respond to a live set. Moving it from "
        f"{a} to {b} after {half} frames changed the next {half} by rms "
        f"{observed:.3g}, under the {LIVENESS_RMS} bar. A param that only takes "
        f"effect at bind cannot be driven from a control surface."
    )
