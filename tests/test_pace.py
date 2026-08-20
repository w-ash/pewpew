"""PacedLoop: the deadline-corrected clock (ADR-010) under fake time.

Every test but the last runs on injected `now`/`sleep` fakes — the pacing
counterpart of FakeClock (which stays a *pattern-time* fake in the harness;
these are wall-time fakes and live here). The wall clock decides when a
frame runs, never what it contains, so the engine-time assertions are exact
(`==`, `np.array_equal`) while wall-time assertions use approx: a fake
sleep computes `t + (next_due - t)`, which floats do not guarantee lands
bit-exactly on `next_due`.
"""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Pattern, Renderer, line, render_sequence
from pewpew.pace import PacedLoop, PaceStats
from pewpew.patterns.plasma import Plasma

PERIOD = 1.0 / 60.0
SEED = 42
N_PX = 32


class FakeTime:
    """Perfect sleeper: sleep(s) advances the clock by exactly s."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = float(start)
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


class Oversleeper(FakeTime):
    """macOS-shaped sleeper: every sleep lands `overshoot` seconds late."""

    def __init__(self, overshoot: float, start: float = 0.0) -> None:
        super().__init__(start)
        self.overshoot = overshoot

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s + self.overshoot


class Costed(Pattern):
    """Render cost injected as fake wall time: `costs[frame_index]` seconds,
    else `default`. Deterministic stand-in for a slow or stalling frame."""

    name = "costed"

    def __init__(self, ft: FakeTime, costs: dict[int, float] | None = None, default: float = 0.0):
        self.ft = ft
        self.costs = costs or {}
        self.default = default
        self.i = 0

    def render(self, x, y, z, index):
        self.ft.t += self.costs.get(self.i, self.default)
        self.i += 1
        return np.zeros((x.shape[0], 3), dtype=np.float32)


def make_loop(ft, pattern=None, on_frame=(), fps=60.0, **kw):
    renderer = Renderer(pattern or Costed(ft), line(N_PX), seed=SEED)
    return PacedLoop(
        renderer, fps=fps, on_frame=on_frame, now=ft.now, sleep=ft.sleep, **kw
    )


def reference_times(frames: int, fps: float = 60.0) -> list[float]:
    """The render_sequence/FakeClock accumulation, reproduced independently."""
    out, t = [], 0.0
    for _ in range(frames):
        t += 1.0 / fps
        out.append(t)
    return out


def test_ticks_land_on_the_absolute_schedule():
    ft = FakeTime()
    starts: list[float] = []
    cost = 0.004
    loop = make_loop(
        ft,
        pattern=Costed(ft, default=cost),
        on_frame=[lambda t, frame: starts.append(ft.t)],
    )
    stats = loop.run(frames=10)
    assert stats == PaceStats(ticks=10, skips=0, missed_frames=0)
    # Delivery happens right after render, so tick k started at starts[k]-cost.
    acc = 0.0
    for k, wall in enumerate(starts):
        assert wall - cost == pytest.approx(acc, abs=1e-12), f"tick {k} off schedule"
        acc += PERIOD


def test_oversleep_is_absorbed_not_accumulated():
    overshoot = 0.004
    ft = Oversleeper(overshoot)
    loop = make_loop(ft)
    n = 8
    loop.run(frames=n)
    # The naive pacer would end n * overshoot late (a 15% rate error at 60
    # fps); deadline correction bounds the drift at a single overshoot.
    assert ft.t == pytest.approx(n * PERIOD + overshoot, abs=1e-9)
    # It compensates by requesting shorter sleeps, not by sleeping the period.
    assert ft.sleeps[0] == pytest.approx(PERIOD, abs=1e-12)
    for s in ft.sleeps[1:]:
        assert s == pytest.approx(PERIOD - overshoot, abs=1e-9)


def test_blown_deadline_skips_ahead():
    ft = FakeTime()
    delivered: list[float] = []
    # Frame 2 stalls 2.5 periods: slots at wall 3p is unrecoverable, slot 4p
    # is rendered late-immediately (newest-wins: never idle waiting for the
    # schedule to come around).
    loop = make_loop(
        ft,
        pattern=Costed(ft, costs={2: 2.5 * PERIOD}),
        on_frame=[lambda t, frame: delivered.append(t)],
    )
    stats = loop.run(frames=6)
    assert stats.ticks == 6
    assert stats.skips == 1
    assert stats.missed_frames == 1
    # Engine time skipped exactly one slot: 4p was never rendered.
    ref = reference_times(8)
    assert delivered == [ref[0], ref[1], ref[2], ref[4], ref[5], ref[6]]


def test_skip_rule_has_no_plus_one():
    ft = FakeTime()
    delivered: list[float] = []
    # A stall short of two periods blows the deadline but loses no slot: the
    # next frame goes out 0.99p late in its own slot and cadence recovers.
    # The bench's off-by-one (+1) dropped a frame here for nothing.
    loop = make_loop(
        ft,
        pattern=Costed(ft, costs={3: 1.99 * PERIOD}),
        on_frame=[lambda t, frame: delivered.append(t)],
    )
    stats = loop.run(frames=8)
    assert stats.skips == 1
    assert stats.missed_frames == 0
    assert delivered == reference_times(8)  # contiguous — nothing dropped


def test_engine_time_matches_render_sequence_bitwise():
    frames = 60
    expected = render_sequence(Plasma, line(N_PX), seed=SEED, frames=frames)

    ft = FakeTime()
    got_t: list[float] = []
    got_frames: list[np.ndarray] = []
    renderer = Renderer(Plasma(), line(N_PX), seed=SEED)
    loop = PacedLoop(
        renderer,
        fps=60.0,
        on_frame=[lambda t, frame: (got_t.append(t), got_frames.append(frame))],
        now=ft.now,
        sleep=ft.sleep,
    )
    loop.run(frames=frames)

    assert got_t == reference_times(frames)  # bit-for-bit, no tolerance
    assert np.array_equal(np.stack(got_frames), expected)  # not RMS-tolerant


def test_engine_time_jumps_by_missed_slots():
    ft = FakeTime()
    delivered: list[float] = []
    # 3.5-period stall: two slots lost. The post-stall t must equal the
    # reference accumulation at its slot index bit-for-bit, which only holds
    # if the skip advances t by repeated addition, not `missed * period`.
    loop = make_loop(
        ft,
        pattern=Costed(ft, costs={1: 3.5 * PERIOD}),
        on_frame=[lambda t, frame: delivered.append(t)],
    )
    stats = loop.run(frames=4)
    assert stats.missed_frames == 2
    ref = reference_times(8)
    assert delivered == [ref[0], ref[1], ref[4], ref[5]]


def test_run_frames_limit_and_resume():
    ft = FakeTime()
    loop = make_loop(ft)
    stats = loop.run(frames=10)
    assert stats.ticks == 10
    # A second run resumes engine time from renderer.t — no backwards-time
    # ValueError, and the frame budget is per-call, not cumulative.
    stats = loop.run(frames=5)
    assert stats.ticks == 15


def test_stop_is_tick_boundary_and_run_is_not_reentrant():
    ft = FakeTime()
    reentrant: list[BaseException] = []

    def on_frame(t, frame):
        if loop.stats.ticks == 3:
            try:
                loop.run(frames=1)
            except RuntimeError as exc:
                reentrant.append(exc)
            loop.stop()

    loop = make_loop(ft, on_frame=[on_frame])
    stats = loop.run(frames=100)
    assert stats.ticks == 3  # stop lands at the tick boundary, not mid-run
    assert len(reentrant) == 1 and "not re-entrant" in str(reentrant[0])
    # After a stop, run() works again.
    assert loop.run(frames=2).ticks == 5


def test_call_soon_runs_on_loop_thread_before_the_tick():
    ft = FakeTime()
    events: list[str] = []

    class Recording(Costed):
        def render(self, x, y, z, index):
            events.append(f"render{self.i}")
            return super().render(x, y, z, index)

    def on_frame(t, frame):
        if len(events) == 1:
            loop.call_soon(lambda: events.append("call"))

    loop = make_loop(ft, pattern=Recording(ft), on_frame=[on_frame])
    loop.run(frames=3)
    assert events == ["render0", "call", "render1", "render2"]


def test_spin_variant_sleeps_short_then_polls():
    margin = 0.002

    class TickingTime(FakeTime):
        """now() itself advances 50 µs per read, so the busy-wait terminates."""

        def now(self) -> float:
            self.t += 5e-5
            return self.t

    ft = TickingTime()
    loop = make_loop(ft, spin_margin=margin)
    stats = loop.run(frames=3)
    assert stats.ticks == 3
    assert len(ft.sleeps) == 3
    for s in ft.sleeps:
        # Sleeps stop short of the deadline by the margin; the poll covers it.
        assert s <= PERIOD - margin + 1e-9


def test_poisoned_bind_propagates():
    class BadRebind(Pattern):
        name = "badrebind"

        def __init__(self):
            self.binds = 0

        def setup(self, n, x, y, z, index):
            self.binds += 1
            if self.binds > 1:
                raise RuntimeError("boom at rebind")

        def render(self, x, y, z, index):
            return np.zeros((x.shape[0], 3), dtype=np.float32)

    ft = FakeTime()
    renderer = Renderer(BadRebind(), line(N_PX), seed=SEED)

    def failing_supervisor():
        # A supervisor that swallows the bind failure instead of restoring
        # the last-good binding leaves the renderer poisoned...
        try:
            renderer.rebind(line(N_PX))
        except RuntimeError:
            pass

    def on_frame(t, frame):
        loop.call_soon(failing_supervisor)

    loop = PacedLoop(renderer, fps=60.0, on_frame=[on_frame], now=ft.now, sleep=ft.sleep)
    # ...and the next advance_to is loud, straight out of run().
    with pytest.raises(RuntimeError, match="not bound"):
        loop.run(frames=10)


def test_rejects_nonpositive_fps():
    ft = FakeTime()
    with pytest.raises(ValueError, match="fps"):
        make_loop(ft, fps=0.0)


def test_real_time_smoke():
    """The one real-clock run: structure only, no timing assertions — bench
    numbers are distributions, never test gates (T-5)."""
    delivered: list[float] = []
    renderer = Renderer(Plasma(), line(N_PX), seed=SEED)
    loop = PacedLoop(renderer, fps=60.0, on_frame=[lambda t, frame: delivered.append(t)])
    stats = loop.run(frames=12)
    assert stats.ticks == 12
    assert stats.missed_frames >= 0
    assert len(delivered) == 12
    assert delivered == sorted(delivered)
