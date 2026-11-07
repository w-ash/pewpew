"""Signal ops (pewpew.fx.ops.signal): each gives one finite number a frame
within its range, keeps its phase and levels from frame to frame so a
changed rate never jumps, draws the same wander for the same key, and
changes what it gives when any of its args moves (liveness). Each op's
examples are looks that check and render."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Sequence
from dataclasses import replace
from typing import Any, cast

import numpy as np
import pytest

from pewpew.compose import Look
from pewpew.features import FakeFeatures, FeatureFrame, FeatureSource
from pewpew.fx.catalog import example
from pewpew.fx.compile import signal_ops
from pewpew.fx.op import FrameCtx
from pewpew.fx.ops import OPS
from pewpew.fx.ops.signal import LEVEL, SWING, WALK_PERIOD, Band, SignalOp
from pewpew.lab import check_look
from pewpew.lab.check import ready
from pewpew.lab.geometry import parse_geometry
from pewpew.lab.rendering import play
from pewpew.params import ParamSet
from pewpew.params.probes import probes
from pewpew.render import SlotClock

FPS = 60.0
SIGNALS = {op: cast("type[SignalOp]", OPS[op]) for op in signal_ops()}
Inputs = Callable[[int], Sequence[float]]


def square(i: int) -> tuple[float]:
    """A gate that is on for a quarter second, then off for one, at 60 fps."""
    return (1.0 if (i // 15) % 2 == 0 else 0.0,)


def made(op: str, **args: object) -> tuple[SignalOp, ParamSet]:
    """A signal op at `args`, the rest at their defaults, and its knobs."""
    cls = OPS[op]
    signal = cls()
    assert isinstance(signal, SignalOp)
    params = ParamSet(cls, args)
    params.apply(signal)
    return signal, params


def run(signal: SignalOp, frames: int, inputs: Inputs = square, *, key: int = 7,
        features: FeatureSource | None = None, start: float = 0.0) -> list[float]:
    """`frames` values of `signal` at 60 fps from engine time `start`, as
    the seat runs it: step, then sample."""
    source = features if features is not None else FakeFeatures(0)
    clock, prev, out = SlotClock(FPS, start), start, []
    for i in range(frames):
        t = clock.advance()
        signal.step(t - prev)
        out.append(signal.sample(FrameCtx(t - prev, source.at(t), i + 1, key), inputs(i)))
        prev = t
    return out


class Level:
    """Features whose `field` is `value(t)`, and the fake's otherwise."""

    def __init__(self, field: str, value: Callable[[float], float]) -> None:
        self.field, self.value, self.base = field, value, FakeFeatures(0)

    def at(self, t: float) -> FeatureFrame:
        return replace(self.base.at(t), **{self.field: self.value(t)})


# ---- every op -------------------------------------------------------------------------


@pytest.mark.parametrize("op", SIGNALS)
def test_each_signal_gives_a_finite_float_within_its_range(op: str) -> None:
    signal, _ = made(op)
    lo, hi = type(signal).range_of([SWING] * len(type(signal).inputs))
    values = run(signal, 240)
    assert all(type(v) is float and math.isfinite(v) and lo <= v <= hi for v in values), values


def test_a_signal_is_not_a_field_and_says_where_it_goes() -> None:
    signal, _ = made("lfo")
    with pytest.raises(TypeError, match="lfo gives a signal, one number a frame, not a field; route it to a knob"):
        signal.build([])
    assert {op: cls.range for op, cls in SIGNALS.items()} == {
        "band": LEVEL, "beat": LEVEL, "env": LEVEL, "knob": LEVEL, "lfo": SWING, "smooth": SWING, "walk": SWING,
    }


def liveness_cases() -> Iterator[Any]:
    for op, cls in SIGNALS.items():
        for record in ParamSet(cls).describe():
            for probe, a, b in probes(record):
                yield pytest.param(op, record["name"], a, b, id=f"{op}-{probe}")


@pytest.mark.parametrize("op, name, a, b", list(liveness_cases()))
def test_every_signal_arg_changes_what_it_gives(op: str, name: str, a: object, b: object) -> None:
    """Liveness for signal ops: each probe pair of each arg (pewpew.params
    .probes) gives another second of values, with a gate or input that
    switches every quarter second."""
    low, high = (run(made(op, **{name: end})[0], 60) for end in (a, b))
    assert max(abs(x - y) for x, y in zip(low, high)) > 1e-3, f"{op}.{name} from {a} to {b} changed nothing"


@pytest.mark.parametrize("op, py", [(op, py) for op, cls in SIGNALS.items() for py in cls.examples])
def test_each_example_is_a_look_that_checks_and_renders(op: str, py: str) -> None:
    made_ = example(py)
    assert isinstance(made_, Look) and any(node.op == op for node in made_.signals or ())
    assert check_look(made_).ok
    frames, errors = play(ready(made_), parse_geometry("grid:6x6"), 20, FPS, 0)
    assert errors == () and frames.dtype == np.float32 and np.isfinite(frames).all()


# ---- phases --------------------------------------------------------------------------


@pytest.mark.parametrize("shape, offset, value", [
    ("sine", 0.0, 0.0), ("sine", 0.25, 1.0), ("triangle", 0.0, 0.0), ("triangle", 0.25, 1.0),
    ("triangle", 0.75, -1.0), ("square", 0.0, 1.0), ("square", 0.5, -1.0), ("saw", 0.0, 1.0), ("ramp", 0.0, -1.0),
])
def test_each_lfo_shape_starts_where_its_doc_says(shape: str, offset: float, value: float) -> None:
    signal, _ = made("lfo", rate=0.0, shape=shape, offset=offset)
    assert run(signal, 1)[0] == pytest.approx(value, abs=1e-12)


def test_a_rate_changed_mid_run_moves_the_wave_on_without_a_jump() -> None:
    """The float rule (ADR-022): the phase adds `rate * dt` each frame, so
    a new rate, by hand or by a route, bends the wave where it is; an hour
    into the run a frame moves it as far as at the start."""
    signal, params = made("lfo", rate=0.2)
    before = run(signal, 60)
    params.set("rate", 5.0)
    after = run(signal, 60, start=1.0)
    steps = np.abs(np.diff([*before, *after]))
    assert steps.max() <= math.tau * 5.0 / FPS + 1e-9  # the steepest a 5 Hz sine moves in one frame
    early, late = (np.diff(run(made("lfo", rate=5.0)[0], 30, start=start)) for start in (0.0, 3600.0))
    np.testing.assert_allclose(early, late, atol=1e-9)


def test_a_walk_eases_within_its_range_and_one_key_wanders_one_way() -> None:
    signal, _ = made("walk", rate=1.0)
    values = run(signal, 300)
    assert max(abs(v) for v in values) <= 1.0 and len({round(v, 3) for v in values}) > 100
    assert np.abs(np.diff(values)).max() < 0.06, "eased, never a jump"
    assert run(made("walk", rate=1.0)[0], 300) == values, "a key gives the same wander in every run"
    assert run(made("walk", rate=1.0)[0], 300, key=8) != values


def test_a_walk_crosses_the_wrap_of_its_phase_without_a_jump() -> None:
    signal, _ = made("walk", rate=4.0)
    signal.phases["rate"] = WALK_PERIOD / 2 - 0.5  # the wrap comes about 8 frames in
    values = run(signal, 30)
    assert np.abs(np.diff(values)).max() < 0.25


# ---- levels ---------------------------------------------------------------------------


def test_an_envelope_plays_attack_decay_sustain_and_release_from_its_gate() -> None:
    signal, _ = made("env", attack=0.1, decay=0.1, sustain=0.5, release=0.2)
    gate: Inputs = lambda i: (1.0 if i < 30 else 0.0,)  # on for half a second
    values = run(signal, 60, gate)
    assert values[2] == pytest.approx(0.5), "half way up after 3 of 6 frames of attack"
    assert values[6] == 1.0, "at the top it turns to decay"
    assert values[12] == pytest.approx(0.5), "the decay falls to the sustain in 6 frames"
    assert values[29] == 0.5, "it holds the sustain while the gate stays on"
    assert values[35] == pytest.approx(0.0, abs=0.01), "0.5 of release falls in 0.1 s"
    again = run(signal, 6, lambda i: (1.0,))
    assert again[-1] == pytest.approx(1.0), "a new gate plays it again"


def test_a_band_rises_over_its_attack_and_falls_over_its_release() -> None:
    """One-pole smoothing (FastLED's audio levels): after one time constant
    a step is about 63% followed."""
    loud = Level("bass", lambda t: 1.0 if t < 0.5 else 0.0)
    signal, _ = made("band", attack=0.05, release=0.2)
    assert isinstance(signal, Band)
    signal.level = 0.0
    values = run(signal, 60, features=loud)
    assert values[2] == pytest.approx(1 - math.exp(-1), abs=0.01)  # 3 frames = 0.05 s
    assert values[29 + 12] == pytest.approx(values[29] * math.exp(-1), abs=0.01)  # 12 frames = 0.2 s
    assert run(made("band", gain=4.0)[0], 10, features=Level("bass", lambda t: 0.5)) == [1.0] * 10


@pytest.mark.parametrize("shape, values", [
    ("pulse", [1.0, 1.0, 0.0, 0.0]), ("phase", [0.0, 0.25, 0.5, 0.75]), ("fall", [1.0, 0.75, 0.5, 0.25]),
])
def test_a_beat_gives_a_pulse_its_phase_or_a_fall(shape: str, values: list[float]) -> None:
    beats = Level("beat_phase", lambda t: (t - 1 / FPS) % 1.0)
    signal, _ = made("beat", shape=shape, width=0.3)
    assert run(signal, 60, features=beats)[::15] == pytest.approx(values)


def test_smooth_follows_its_input_with_its_lag_and_a_knob_gives_its_value() -> None:
    signal, _ = made("smooth", time=0.25)
    values = run(signal, 30, lambda i: (0.0 if i == 0 else 1.0,))
    assert values[0] == 0.0 and values[15] == pytest.approx(1 - math.exp(-1), abs=0.01)
    assert SIGNALS["smooth"].range_of([LEVEL]) == LEVEL, "it gives what its input gives"
    assert run(made("knob", value=0.3)[0], 3) == [0.3] * 3
