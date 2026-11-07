"""Param liveness: every declared param kind must change what you see.

Render a program twice, one knob at each value of a probe pair
(pewpew.params.probes), and require the two sequences to differ. Endpoints,
not a nudge, so a range too narrow to change the picture fails too. Neither
the authoring surface nor the goldens can see a param that is semantically
dead. The op is the params zoo (tests/params_zoo.py), one knob of each kind,
so each kind's whole path runs; tests/test_fx_ops.py applies the same method
to every built-in op, and `verify looks` to every knob of a look
(pewpew.lab.liveness).
L1 (`research/synthesis/test-and-feedback.md`): seeded and hard-gating.
"""

from __future__ import annotations

import numpy as np
import pytest

from fakes import frames, hosted, one_node, with_test_ops
from params_zoo import ZOO
from pewpew.fx.ops import OPS
from pewpew.mapping import line
from pewpew.metrics import LIVENESS_RMS, rms
from pewpew.params import ParamSet
from pewpew.params.probes import probes
from pewpew.render import Renderer

pytestmark = pytest.mark.usefixtures("fake_ops")

SEED = 42
FPS = 60.0
# Half a second is long enough for a param to separate; a param that needs
# longer than that to show should say so by failing, not pass quietly.
N_FRAMES = 30
MAPPING = line(64)
NODE = "zoo"


def _cases() -> list[pytest.ParameterSet]:
    """One case per probe of each zoo knob, self-extending: a new knob on
    the zoo gets checked with no edit here."""
    with with_test_ops():
        records = ParamSet(OPS[ZOO]).describe()
    return [pytest.param(record["name"], a, b, id=f"{ZOO}-{probe_id}")
            for record in records for probe_id, a, b in probes(record)]


def zoo(args: dict[str, object]) -> Renderer:
    """A renderer of one zoo node at `args`."""
    return hosted(one_node(ZOO, args, node=NODE), MAPPING, seed=SEED)


@pytest.mark.parametrize("name, a, b", _cases())
def test_param_changes_the_picture(name: str, a: object, b: object) -> None:
    low, high = (frames(zoo({name: value}), N_FRAMES, FPS) for value in (a, b))
    observed = rms(low, high)
    assert observed > LIVENESS_RMS, (
        f"{ZOO}.{name} is dead. Moving it from {a} to {b} changed the "
        f"{N_FRAMES}-frame sequence by rms {observed:.3g}, under the {LIVENESS_RMS} bar. "
        f"Either nothing reads it in a way that reaches a pixel, or the range is too "
        f"narrow to matter."
    )


@pytest.mark.parametrize("name, a, b", _cases())
def test_param_set_while_running_changes_the_picture(name: str, a: object, b: object) -> None:
    """The same bar, for a knob set mid-run rather than at bind: it catches
    a control that moves and shows nothing, which the bind-time check above
    cannot see. An op that precomputes from a knob in `setup` fails here."""
    half = N_FRAMES // 2
    held, turned = zoo({name: a}), zoo({name: a})
    before = (frames(held, half, FPS), frames(turned, half, FPS))
    assert np.array_equal(*before), "the two runs must be identical until the param moves"

    turned.pattern.node_params[NODE].set(name, b)  # type: ignore[attr-defined]  # a ProgramPattern
    observed = rms(frames(held, half, FPS), frames(turned, half, FPS))
    assert observed > LIVENESS_RMS, (
        f"{ZOO}.{name} does not respond to a live set. Moving it from "
        f"{a} to {b} after {half} frames changed the next {half} by rms "
        f"{observed:.3g}, under the {LIVENESS_RMS} bar. A param that only takes "
        f"effect at bind cannot be driven from a control surface."
    )
