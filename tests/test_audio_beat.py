"""The beat (pewpew.audio.beat, through pewpew.audio.features): the tracker
finds the tempo of synthetic tracks within 2% and puts the beat on them,
noise gives low confidence, the oscillator never steps back, and the
controls and the modes (tap, hold, auto, resync, nudge; lost, degraded)
do what ADR-009's 2026-11-06 amendment says. The runs over whole tracks
go on the suite's process pool (`JOBS`)."""

from __future__ import annotations

import itertools
import math
from functools import partial

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from audio_signals import RATE, beats, click_times, click_track, clicks, kick_loop, matched, noise, ticks
from pewpew.audio import ArraySource, AudioFeatures, AudioSource, Block
from pewpew.audio.beat import MAX_CORRECTION, NUDGE, TAP_WINDOW, Oscillator, fold, phase_error
from pewpew.audio.features import play


def listening(source: AudioSource) -> AudioFeatures:
    """Features at 60 fps with no lead, so the beats fall at the signal's own times."""
    return AudioFeatures(source, fps=60.0, lead=0.0)


def track(bpm: float, seconds: float = 10.0, rate: int = RATE) -> dict:
    """The tempo, confidence and mode at the end of a click track, and how
    well the beats from 6 s on match its clicks."""
    features = listening(ArraySource(click_track(bpm, seconds, rate, seed=int(bpm)), rate))
    found = beats(features, seconds)
    truth = click_times(bpm, seconds)
    late = found[found > 6.0]
    return {"bpm": features.tracker.bpm, "osc": features.oscillator.bpm, "confidence": features.tracker.confidence,
            "mode": features.mode, "f": matched(late, truth[truth > 5.9]), "lag": float(np.median(
                [x - truth[np.argmin(np.abs(truth - x))] for x in late]))}


def heard(samples: np.ndarray, seconds: float) -> dict:
    features = listening(ArraySource(samples, RATE))
    ticks(features, seconds)
    return {"bpm": features.tracker.bpm, "confidence": features.tracker.confidence, "mode": features.mode}


def tempo_step() -> dict:
    """A kick loop at 120 BPM for 10 s, then at 128 BPM for 12 s."""
    samples = np.concatenate([kick_loop(120.0, 10.0), kick_loop(128.0, 12.0, seed=1)])
    return heard(samples, 22.0)


class Dropping(ArraySource):
    """An array whose every `every`-th hop-sized block never arrives, and
    which goes quiet from `stop` to `resume` seconds."""

    def __init__(self, samples: np.ndarray, *, every: int = 0, stop: float = math.inf,
                 resume: float = math.inf) -> None:
        super().__init__(samples, RATE)
        self.every, self.stop, self.resume, self.n = every, stop, resume, 0

    def take(self, t: float) -> list[Block]:
        out = []
        for block in super().take(t):
            for at in range(0, len(block.samples), 480):
                self.n += 1
                start = block.start + at
                quiet = self.stop * RATE <= start < self.resume * RATE
                if not quiet and not (self.every and self.n % self.every == 0):
                    out.append(Block(start, block.samples[at:at + 480]))
        return out


def degraded() -> dict:
    """A 120 BPM click track that loses one block in 40 from 8 s on."""
    source = Dropping(click_track(120.0, 14.0))
    features = listening(source)
    ticks(features, 8.0)
    before = features.mode
    source.every = 40
    modes = [state["mode"] for _, _, state in play(features, 6.0)]
    return {"before": before, "after": modes[-1], "held": features.tracker.held_share,
            "volume": features.at(14.0).volume}


def lost() -> dict:
    """A 120 BPM click track that goes quiet from 8 s to 11 s."""
    features = listening(Dropping(click_track(120.0, 16.0), stop=8.0, resume=11.0))
    ticks(features, 8.0)
    before = (features.mode, features.oscillator.bpm)
    quiet = [(state["mode"], frame.volume, frame.beat_phase) for _, frame, state in play(features, 3.0)]
    back = [state["mode"] for _, _, state in play(features, 5.0)]
    return {"before": before, "quiet": quiet, "back": back, "beats": features.oscillator.beats}


def tapped(samples: np.ndarray, tap: float, at: float, seconds: float) -> dict:
    """`samples` tapped at `tap` BPM at the tick after `at` s, then heard
    for `seconds` more: the state at the end and the beats after the tap."""
    features = listening(ArraySource(samples, RATE))
    ticks(features, at)
    assert features.control("tap", [60.0 / tap] * 4) is None
    found = beats(features, seconds)
    return {"bpm": features.tracker.bpm, "osc": features.oscillator.bpm, "mode": features.mode,
            "window": features.tracker.window, "beats": found}


def off_beat_track(seconds: float) -> np.ndarray:
    """Quiet clicks on the beats of 120 BPM and loud ones on the off-beats."""
    on = click_times(120.0, seconds)
    return clicks(on, seconds, level=0.1) + clicks(on + 0.25, seconds, seed=1, level=0.6)


def lags(found: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """How far each found beat falls after its nearest true beat."""
    return np.array([x - truth[np.argmin(np.abs(truth - x))] for x in found])


JOBS = {
    **{f"click-{bpm}": partial(track, bpm) for bpm in (90, 120, 150)},
    "click-44k": partial(track, 133, rate=44100),
    "noise": partial(heard, noise(10.0, level=0.2), 10.0),
    "kick-124": partial(heard, kick_loop(124.0, 10.0), 10.0),
    "step": tempo_step,
    "degraded": degraded,
    "lost": lost,
    "tap-near": partial(tapped, click_track(124.0, 12.0), 121.0, 2.0, 10.0),
    "tap-on-beat": partial(tapped, off_beat_track(18.0), 120.0, 10.25, 7.75),  # just after the beat at 10.25 s
    "tap-double": partial(tapped, click_track(172.0, 14.0), 170.0, 4.0, 10.0),
}


@pytest.mark.parametrize("key, bpm", [("click-90", 90), ("click-120", 120), ("click-150", 150), ("click-44k", 133)])
def test_the_tempo_is_within_two_percent_and_the_beat_lands_on_the_clicks(pooled, key: str, bpm: float) -> None:
    result = pooled[key]
    assert result["bpm"] == pytest.approx(bpm, rel=0.02) and result["osc"] == pytest.approx(bpm, rel=0.02)
    assert result["mode"] == "locked" and result["confidence"] > 0.5
    assert result["f"] >= 0.9  # within ±70 ms, mir_eval's window
    assert -0.01 <= result["lag"] <= 0.035  # the analysis's own latency, which the lead absorbs


def test_a_kick_loop_locks_and_noise_free_runs(pooled) -> None:
    assert pooled["kick-124"]["bpm"] == pytest.approx(124, rel=0.02) and pooled["kick-124"]["mode"] == "locked"
    assert pooled["noise"]["confidence"] < 0.3 and pooled["noise"]["mode"] == "free-run"


def test_the_tracker_relocks_after_a_tempo_step(pooled) -> None:
    assert pooled["step"]["bpm"] == pytest.approx(128, rel=0.02) and pooled["step"]["mode"] == "locked"


def test_a_tap_seeds_the_tempo_and_the_tracker_corrects_within_its_window(pooled) -> None:
    result = pooled["tap-near"]
    assert result["mode"] == "tapped" and result["bpm"] == pytest.approx(124, rel=0.01)
    assert result["window"] == pytest.approx((121 * (1 - TAP_WINDOW), 121 * (1 + TAP_WINDOW)))


def test_a_tap_on_the_beats_moves_a_beat_locked_to_the_off_beats(pooled) -> None:
    result = pooled["tap-on-beat"]
    found = result["beats"]
    assert result["mode"] == "tapped" and len(found[found > 13.0]) >= 8
    late = lags(found[found > 13.0], click_times(120.0, 18.0))
    assert ((-0.01 <= late) & (late <= 0.035)).all()  # on the quiet beats, not 0.25 s on


def test_a_tap_outside_the_trackers_octave_is_tracked_at_a_multiple_of_its_tempo(pooled) -> None:
    result = pooled["tap-double"]
    assert result["mode"] == "tapped" and result["bpm"] == pytest.approx(86, rel=0.02)
    assert result["window"] == pytest.approx((85 * (1 - TAP_WINDOW), 85 * (1 + TAP_WINDOW)))
    found = result["beats"]
    assert result["osc"] == pytest.approx(172, rel=0.01) and len(found[found > 9.0]) >= 13
    late = lags(found[found > 9.0], click_times(172.0, 14.0))
    assert ((-0.01 <= late) & (late <= 0.035)).all()  # free-running at 170 BPM drifts about 120 ms by 14 s


def test_held_hops_past_ten_percent_free_run_the_beat_and_keep_the_levels(pooled) -> None:
    result = pooled["degraded"]
    assert result["before"] == "locked" and result["after"] == "free-run"
    assert result["held"] > 0.1 and result["volume"] > 0.0


def test_lost_input_silences_the_levels_and_the_beat_runs_on_at_the_last_tempo(pooled) -> None:
    result = pooled["lost"]
    assert result["before"] == ("locked", 120.0)
    modes = [mode for mode, _, _ in result["quiet"]]
    first_lost = modes.index("lost")
    assert first_lost == pytest.approx(30, abs=2)  # half a second of ticks
    assert all(volume == 0.0 for mode, volume, _ in result["quiet"] if mode == "lost")
    phases = [phase for _, _, phase in result["quiet"]]
    steps = [(b - a) % 1.0 for a, b in itertools.pairwise(phases)]
    assert all(step == pytest.approx(2.0 / 60.0) for step in steps[first_lost:])  # free-running at 120 BPM
    assert "lost" not in result["back"][-60:] and result["back"][-1] in ("searching", "locked")


# ---- the oscillator ---------------------------------------------------------------


@given(st.lists(st.tuples(st.floats(0.0, 0.1), st.floats(60.0, 200.0), st.floats(-0.5, 0.5),
                          st.sampled_from([-1, 0, 1])), min_size=1, max_size=200))
def test_the_oscillator_never_steps_back_and_counts_every_wrap(steps: list[tuple[float, float, float, int]]) -> None:
    osc, t = Oscillator(), 0.0
    osc.advance(t)
    for dt, bpm, error, nudge in steps:
        osc.bpm, osc.bias = bpm, NUDGE * nudge
        osc.steer(error)
        before, beats = osc.phase + osc.beats, osc.beats
        nominal = dt * bpm / 60.0
        t += dt
        osc.advance(t)
        step = osc.phase + osc.beats - before
        assert nominal * (1 - MAX_CORRECTION - NUDGE) - 1e-9 <= step <= nominal * (1 + MAX_CORRECTION + NUDGE) + 1e-9
        assert 0.0 <= osc.phase < 1.0 and osc.beats - beats == math.floor(before - beats + step)


def test_resync_jumps_forward_to_a_beat_once() -> None:
    osc = Oscillator()
    osc.advance(0.0)
    osc.advance(0.15)  # 0.3 of a beat at 120 BPM
    osc.resync()
    assert (osc.phase, osc.beats) == (0.0, 1)
    osc.resync()
    assert (osc.phase, osc.beats) == (0.0, 1)  # already on the beat


def test_the_phase_error_wraps_to_half_a_step_either_way() -> None:
    assert phase_error(0.1, 0.9) == pytest.approx(0.2)
    assert phase_error(0.9, 0.1) == pytest.approx(-0.2)
    assert phase_error(0.5, 0.0) == pytest.approx(-0.5)
    assert phase_error(0.6, 0.05, 0.5) == pytest.approx(0.05)  # the off-beat at 0.1 is nearer than 0.6


def test_a_tempo_folds_into_the_trackers_octave_by_a_power_of_two() -> None:
    assert [fold(bpm) for bpm in (30.0, 60.0, 80.0, 120.0, 160.0, 172.0, 300.0)] == [
        120.0, 120.0, 80.0, 120.0, 160.0, 86.0, 150.0]


# ---- controls on a quiet input ------------------------------------------------------


def quiet(seconds: float = 0.5) -> AudioFeatures:
    features = listening(ArraySource(np.zeros(RATE * 20, np.float32), RATE))
    ticks(features, seconds)
    return features


def test_a_tap_sets_the_tempo_from_the_median_interval_and_the_phase_at_its_tick() -> None:
    features = quiet()
    assert features.control("tap", [0.6, 0.5, 0.5, 0.49, 0.51]) is None  # the last four: median 0.5 s
    before = features.oscillator.beats
    ticks(features, 1.0 / 60.0)
    assert features.oscillator.bpm == pytest.approx(120.0) and features.oscillator.beats == before + 1
    assert features.oscillator.phase == pytest.approx(2.0 / 60.0, abs=1e-9)  # a beat at the tap's tick
    assert features.tracker.window == pytest.approx((115.2, 124.8)) and features.tracker.bpm == 120.0


def test_hold_free_runs_nudge_biases_and_auto_releases() -> None:
    features = quiet()
    for verb, value in (("hold", None), ("nudge", 1)):
        assert features.control(verb, value) is None
    ticks(features, 1.0 / 60.0)
    assert features.mode == "hold" and features.oscillator.rate == pytest.approx(2.0 * (1 + NUDGE))
    features.control("nudge", 0)
    features.control("tap", [0.5])
    features.control("auto")
    ticks(features, 1.0 / 60.0)
    assert features.mode == "searching" and features.tracker.window is None
    assert features.oscillator.rate == pytest.approx(2.0)


def test_sensitivity_moves_the_gate() -> None:
    features = quiet()
    assert features.control("sensitivity", 0.9) is None
    ticks(features, 1.0 / 60.0)
    assert features.analyser.sensitivity == 0.9 and features.state()["sensitivity"] == 0.9


@pytest.mark.parametrize("verb, value, reason", [
    ("tempo", None, "unknown audio control 'tempo'; controls: tap, hold, auto, resync, nudge, sensitivity"),
    ("tap", [], "tap takes the seconds between taps, a list of one or more numbers from 0.2 to 2"),
    ("tap", [0.05], "(30 to 300 BPM), got [0.05]"),
    ("nudge", 2, "nudge takes -1 (slower), 0 (let go) or 1 (faster), got 2"),
    ("nudge", True, "nudge takes -1"),
    ("sensitivity", 1.5, "sensitivity takes a number from 0 to 1, got 1.5"),
    ("hold", 1, "hold takes no value, got 1"),
])
def test_a_malformed_control_is_refused_in_words(verb: str, value: object, reason: str) -> None:
    features = quiet(0.0)
    assert reason in (features.control(verb, value) or "")
    assert features.state()["mode"] == "searching"
