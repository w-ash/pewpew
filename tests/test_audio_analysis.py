"""The analysis on the sample clock (pewpew.audio.analysis) and the live
sample clock's fit (pewpew.audio.clock): levels land in their bands at
both common rates, the gate and the rider behave, onsets are timely, and
the gap and backlog rules hold the hops they say."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from audio_signals import RATE, clicks, noise, sine
from fakes import FakeTime
from pewpew.audio import Analyser, Block
from pewpew.audio.analysis import HOP_S, MAX_HOPS, Hop, band_edges, window_size
from pewpew.audio.clock import READY_S, WINDOW_S, SampleClock
from pewpew.features import N_BANDS
from pewpew.mapping import line
from pewpew.pace import PacedLoop
from pewpew.pattern import Pattern
from pewpew.render import Renderer


def fed(analyser: Analyser, samples: np.ndarray, *, start: int = 0, block: int | None = None) -> list[Hop]:
    """Every hop of `samples` fed in blocks of `block` (a hop's worth by default)."""
    block = block or analyser.hop
    hops: list[Hop] = []
    for at in range(0, len(samples), block):
        hops += analyser.feed([Block(start + at, samples[at:at + block])]).hops
    return hops


def settle(analyser: Analyser, samples: np.ndarray) -> Hop:
    """The last hop of `samples`."""
    return fed(analyser, samples)[-1]


@pytest.mark.parametrize("rate", [44100, 48000])
def test_the_grid_is_ten_ms_hops_over_a_2048_point_window(rate: int) -> None:
    analyser = Analyser(rate)
    assert analyser.hop == round(rate * HOP_S) and analyser.size == window_size(rate) == 2048
    assert analyser.level_size == 1024
    assert window_size(16000) == 512 and window_size(96000) == 4096


@pytest.mark.parametrize("rate", [44100, 48000])
@pytest.mark.parametrize("hz", [60.0, 440.0, 1000.0, 5000.0, 12000.0])
def test_a_sine_lands_in_its_band(rate: int, hz: float) -> None:
    hop = settle(Analyser(rate), sine(hz, 0.5, rate))
    edges = band_edges(rate, 1024) * rate / 1024
    expect = int(np.searchsorted(edges, hz, side="right")) - 1
    assert int(np.argmax(hop.levels.bands)) == expect and hop.levels.bands[expect] > 0.9
    others = np.delete(hop.levels.bands, [expect - 1, expect, expect + 1])
    assert others.max() < hop.levels.bands[expect] - 0.25


@pytest.mark.parametrize("hz, loud", [(100.0, "bass"), (1000.0, "mid"), (6000.0, "high")])
def test_bass_mid_and_high_split_at_250_and_3000_hz(hz: float, loud: str) -> None:
    levels = settle(Analyser(RATE), sine(hz, 0.5)).levels
    split = {name: getattr(levels, name) for name in ("bass", "mid", "high")}
    assert max(split, key=lambda name: split[name]) == loud and split[loud] > 0.9
    assert levels.volume > 0.9


def test_silence_and_a_noise_floor_under_the_gate_read_zero() -> None:
    assert not settle(Analyser(RATE), np.zeros(RATE // 2, np.float32)).levels.bands.any()
    hiss = noise(0.5, level=1e-4)  # about -80 dBFS a sample
    assert settle(Analyser(RATE), hiss).levels.volume == 0.0
    assert settle(Analyser(RATE, sensitivity=1.0), hiss).levels.volume > 0.0  # a lower gate opens


def test_a_dc_offset_is_no_sound_once_the_analysis_has_learnt_it() -> None:
    offset = np.float32(0.003)  # about -50 dBFS
    silent = settle(Analyser(RATE), np.full(3 * RATE, offset, np.float32)).levels
    assert silent.volume == silent.bass == 0.0 and not silent.bands.any()
    tone = settle(Analyser(RATE), sine(100.0, 3.0, level=0.05)).levels
    biased = settle(Analyser(RATE), sine(100.0, 3.0, level=0.05) + offset).levels
    assert biased.bass == pytest.approx(tone.bass, abs=0.01)
    assert biased.bands[0] == pytest.approx(tone.bands[0], abs=0.01)


def test_the_rider_settles_after_a_20_db_step() -> None:
    analyser = Analyser(RATE)
    loud = settle(analyser, sine(1000.0, 3.0, level=0.5)).levels.volume
    quiet = fed(analyser, sine(1000.0, 9.0, level=0.05))
    after = [h.levels.volume for h in quiet]
    assert after[5] < loud - 0.4  # 20 dB down reads low at first
    assert after[-1] == pytest.approx(loud, abs=0.05)  # then the rider comes down to it


def test_an_onset_rises_within_one_hop_of_the_hop_its_click_lands_in() -> None:
    analyser = Analyser(RATE)
    at = [1.0, 1.4037, 1.8111]
    hops = fed(analyser, clicks(np.array(at), 2.2))
    floor = float(np.median([h.onset for h in hops if not h.held]))
    for click in (round(a * RATE) for a in at):
        first = next(h for h in hops if h.end > click and h.onset > 2.0 * floor)
        assert 0 < first.end - click <= 2 * analyser.hop


def test_one_lost_block_holds_seven_hops_of_onset_and_levels() -> None:
    analyser = Analyser(RATE)
    samples = noise(2.0, level=0.3)
    hop = analyser.hop
    hops = fed(analyser, samples[: hop * 100])
    result = analyser.feed([Block(hop * 101, samples[hop * 101:hop * 102])])  # block 100 is lost
    hops = result.hops + fed(analyser, samples[hop * 102:], start=hop * 102)
    held = [h for h in hops if h.held]
    assert result.filled == hop and len(held) == 7
    assert all(h.onset == held[0].onset and h.levels is held[0].levels for h in held)
    assert held[0].end % hop == 0 and held[0].end == hop * 101  # the first hop whose window holds the zeros
    assert not hops[len(held)].held


def test_a_long_gap_restarts_the_grid_with_no_zero_fill() -> None:
    analyser = Analyser(RATE)
    fed(analyser, noise(1.0))
    start = RATE * 31  # 30 s of nothing
    first = analyser.feed([Block(start, noise(0.03))])
    assert first.restarted and first.filled == 0 and first.hops == []  # waiting for a full window
    hops = first.hops + fed(analyser, noise(0.1, seed=1), start=start + int(0.03 * RATE))
    assert hops[0].end == start + 5 * analyser.hop  # the first full 2048-sample window on the grid
    assert [h.held for h in hops[:3]] == [True, True, False]  # two prior frames first


def test_a_backlog_analyses_at_most_twenty_hops_a_feed() -> None:
    analyser = Analyser(RATE)
    fed(analyser, noise(1.0))
    short = analyser.feed([Block(RATE, noise(0.3, seed=1))])  # 30 hops at once
    assert short.skipped == 10 and not short.restarted and len(short.hops) == 30
    assert sum(h.held for h in short.hops) == 12  # 10 skipped, then 2 without fresh frames
    long = analyser.feed([Block(analyser.expected or 0, noise(2.0, seed=2))])  # a 2 s stall
    assert long.restarted and long.skipped == 200 - MAX_HOPS
    assert len(long.hops) == MAX_HOPS and [h.held for h in long.hops[:3]] == [True, True, False]


def test_a_backlog_that_restarts_still_holds_the_hops_a_lost_block_touches() -> None:
    analyser = Analyser(RATE)
    hop = analyser.hop
    fed(analyser, noise(1.0))
    stall = noise(2.0, seed=1)
    blocks = [Block((100 + k) * hop, stall[k * hop:(k + 1) * hop]) for k in range(200) if k != 190]
    result = analyser.feed(blocks)  # a 2 s stall, block 290 lost 50 ms before the newest sample
    assert result.restarted and result.filled == hop
    held = [h.end // hop for h in result.hops if h.held]
    assert held == [281, 282, *range(291, 298)]  # two without prior frames, then the 7 that read the zeros


def test_an_overlap_keeps_the_new_samples_and_a_jump_back_restarts() -> None:
    analyser = Analyser(RATE)
    samples = noise(0.2)
    fed(analyser, samples[:4800])
    again = analyser.feed([Block(4320, samples[4320:5760])])  # 480 samples it has, 960 new
    assert not again.restarted and again.filled == 0 and analyser.expected == 5760
    back = analyser.feed([Block(0, samples[:480])])  # the source counts from 0 again
    assert back.restarted and analyser.expected == 480


# ---- the live sample clock ----------------------------------------------------------


class Stalling(Pattern):
    """Black frames, frame k taking `stalls[k]` seconds of `ft`'s wall time."""

    def __init__(self, ft: FakeTime, stalls: dict[int, float]) -> None:
        self.ft, self.stalls, self.k = ft, stalls, 0

    def render(self, x, y, z, index):
        self.ft.t += self.stalls.get(self.k, 0.0)
        self.k += 1
        return np.zeros((len(x), 3), np.float32)


def arrivals(ppm: float, delay: float, jitter: float, fps: float, seed: int, seconds: float = WINDOW_S + 1,
             block: int = 480, stall: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Blocks of a source `ppm` fast, arriving `delay` plus seeded jitter
    after their last sample, drained by a loop at `fps` that stalls for
    `stall` seconds at the start of each second: (ends, sent, t) with `t`
    the engine time of the tick that drained each."""
    rate = RATE * (1.0 + ppm * 1e-6)
    ends = (np.arange(int(seconds * rate / block)) + 1) * block
    sent = ends / rate
    late = np.random.default_rng(seed).exponential(jitter, len(ends)) if jitter else 0.0
    arrive = np.maximum.accumulate(sent + delay + late)
    drained = np.where(arrive % 1.0 < stall, np.floor(arrive) + stall, arrive)
    return ends, sent, np.ceil(drained * fps) / fps + 1.0 / fps  # tick k runs at k/fps with t = (k+1)/fps


def fitted(ends: np.ndarray, t: np.ndarray, fps: float) -> SampleClock:
    clock = SampleClock(RATE, fps)
    for end, at in zip(ends.tolist(), t.tolist()):
        clock.observe(end, at)
    return clock


@given(ppm=st.floats(-100.0, 100.0), delay=st.floats(0.001, 0.02), jitter=st.floats(0.0, 0.005),
       fps=st.sampled_from([50.0, 60.0, 120.0]), seed=st.integers(0, 2**16), stall=st.sampled_from([0.0, 0.098]))
def test_the_fit_follows_the_arrivals_within_a_slot_and_shrugs_off_an_early_point(
        ppm: float, delay: float, jitter: float, fps: float, seed: int, stall: float) -> None:
    ends, sent, t = arrivals(ppm, delay, jitter, fps, seed, block=960, stall=stall)  # 20 ms blocks keep it quick
    clock = fitted(ends, t, fps)
    window = ends > ends[-1] - WINDOW_S * RATE
    mapped = np.array([clock.time(int(e)) for e in ends[window]]) - sent[window]
    assert np.ptp(mapped) <= 1.0 / fps  # the line follows the samples' own clock to within one slot
    # The earliest stamp is `delay` and two slots after its block was sent
    # (`arrivals`' ticks); a stall makes late stamps, which the line ignores.
    assert delay + 1.5 / fps <= mapped.min() and mapped.max() <= delay + 3.0 / fps + 0.001
    assert abs(clock.drift_ppm or 0.0) <= abs(ppm) + 1e6 / (fps * WINDOW_S)  # drift, to a slot a window
    early = t.copy()
    early[len(t) // 2] -= 1.0 / fps  # one tick that stamped a whole period early
    newest = int(ends[-1])
    assert abs((fitted(ends, early, fps).time(newest) or 0.0) - (clock.time(newest) or 0.0)) < 0.001


def test_each_second_keeps_its_earliest_stamp_against_its_index_not_its_first() -> None:
    clock = SampleClock(RATE, 60.0)
    for second in range(READY_S + 1):
        clock.observe(second * RATE + 4800, second + 0.1 + 0.4)  # sent at 0.1 s into the second, 0.4 s late
        clock.observe(second * RATE + 24000, second + 0.5 + 0.02)  # sent at 0.5 s, 20 ms late
    assert clock.time(RATE + 24000) == pytest.approx(1.5 + 0.02 + clock.slot)


def test_a_stamp_is_at_or_after_its_blocks_arrival_through_a_stall() -> None:
    # The loop's schedule puts the tick of engine time t at wall time t - 1/fps.
    ft, fps = FakeTime(), 60.0
    arrive = [0.004 + 0.01 * k for k in range(1, 400)]  # a 10 ms block 4 ms after its last sample
    stamps: list[tuple[float, float]] = []  # (stamp, arrival), both in engine time

    def drain(t: float) -> None:
        while arrive and arrive[0] <= ft.now():
            stamps.append((t + 1.0 / fps, arrive.pop(0) + 1.0 / fps))

    stalls = {k: 0.098 for k in (30, 95, 160)}  # ADR-010's longest interval, three times
    loop = PacedLoop(Renderer(Stalling(ft, stalls), line(1)), fps, before=[drain], now=ft.now, sleep=ft.sleep)
    assert loop.run(frames=230).skips == 3
    assert len(stamps) > 300 and all(stamp >= at for stamp, at in stamps)


def test_the_fit_maps_nothing_until_it_holds_five_seconds_and_a_restart_forgets() -> None:
    ends, _, t = arrivals(0.0, 0.005, 0.0, 60.0, 0, seconds=READY_S + 1.5)
    clock = SampleClock(RATE, 60.0)
    for end, at in zip(ends.tolist(), t.tolist()):
        clock.observe(end, at)
        assert (clock.time(0) is None) == (end // RATE < READY_S)
    drift = clock.drift_ppm
    assert clock.time(0) is not None and drift is not None and math.isfinite(drift)
    clock.restart()
    assert clock.time(0) is None and clock.drift_ppm is None


def test_band_edges_are_one_bin_wide_at_least_and_empty_past_nyquist() -> None:
    edges = band_edges(16000, 256)
    assert len(edges) == N_BANDS + 1 and (np.diff(edges) >= 0).all()
    assert edges[-1] == 129 and (np.diff(band_edges(RATE, 1024)) >= 1).all()
