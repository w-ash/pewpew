"""PacedLoop: the deadline-corrected clock (ADR-010) under fake time.

Every loop test but `test_real_time_smoke` runs on injected `now`/`sleep`
wall-time fakes (tests/fakes.py). The wall clock decides when a frame runs,
never what it contains, so the engine-time assertions are exact (`==`,
`np.array_equal`) while wall-time assertions use approx: a fake sleep
computes `t + (next_due - t)`, which floats do not guarantee lands
bit-exactly on `next_due`.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from fakes import FLOW, FakeTime, Oversleeper, costed, hosted, source_op, wait_until
from fakes import frames as render_frames
from pewpew.mapping import line
from pewpew.pace import STOPPING, Calls, PacedLoop, PaceStats

PERIOD = 1.0 / 60.0
SEED = 42
N_PX = 32


pytestmark = pytest.mark.usefixtures("fake_ops")


def make_loop(ft, program=None, on_frame=(), fps=60.0, **kw):
    renderer = hosted(program or costed(ft), line(N_PX), seed=SEED)
    return PacedLoop(
        renderer, fps=fps, on_frame=on_frame, now=ft.now, sleep=ft.sleep, **kw
    )


def reference_times(frames: int, fps: float = 60.0) -> list[float]:
    """The SlotClock/FakeClock accumulation, reproduced independently."""
    out, t = [], 0.0
    for _ in range(frames):
        t += 1.0 / fps
        out.append(t)
    return out


def test_frames_go_out_on_the_absolute_schedule_whatever_each_render_costs():
    ft = FakeTime()
    sent: list[float] = []
    loop = make_loop(
        ft,
        program=costed(ft, costs={1: 0.001, 2: 0.012, 3: 0.004, 5: 0.015}, default=0.002),
        on_frame=[lambda t, frame: sent.append(ft.t)],
    )
    stats = loop.run(frames=10)
    assert stats == PaceStats(ticks=10, skips=0, missed_frames=0)
    # Frame k goes out at the end of its slot, (k + 1) periods in.
    acc = 0.0
    for k, wall in enumerate(sent):
        acc += PERIOD
        assert wall == pytest.approx(acc, abs=1e-12), f"frame {k} off schedule"


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
        program=costed(ft, costs={2: 2.5 * PERIOD}),
        on_frame=[lambda t, frame: delivered.append(t)],
    )
    stats = loop.run(frames=6)
    assert stats.ticks == 6
    assert stats.skips == 1
    assert stats.missed_frames == 1
    # Engine time skipped exactly one slot: 4p was never rendered.
    ref = reference_times(8)
    assert delivered == [ref[0], ref[1], ref[2], ref[4], ref[5], ref[6]]


def test_a_stall_short_of_two_periods_loses_no_slot():
    ft = FakeTime()
    delivered: list[float] = []
    # The stall blows the deadline, but the next frame goes out 0.99p late
    # in its own slot and cadence recovers.
    loop = make_loop(
        ft,
        program=costed(ft, costs={3: 1.99 * PERIOD}),
        on_frame=[lambda t, frame: delivered.append(t)],
    )
    stats = loop.run(frames=8)
    assert stats.skips == 1
    assert stats.missed_frames == 0
    assert delivered == reference_times(8)  # contiguous — nothing dropped


def test_engine_time_matches_slot_clock_frames_bitwise():
    count = 60
    expected = render_frames(hosted(FLOW, line(N_PX), seed=SEED), count)

    ft = FakeTime()
    got_t: list[float] = []
    got_frames: list[np.ndarray] = []
    renderer = hosted(FLOW, line(N_PX), seed=SEED)
    loop = PacedLoop(
        renderer,
        fps=60.0,
        on_frame=[lambda t, frame: (got_t.append(t), got_frames.append(frame))],
        now=ft.now,
        sleep=ft.sleep,
    )
    loop.run(frames=count)

    assert got_t == reference_times(count)  # bit-for-bit, no tolerance
    assert np.array_equal(np.stack(got_frames), expected)  # not RMS-tolerant


def test_engine_time_jumps_by_missed_slots():
    ft = FakeTime()
    delivered: list[float] = []
    # 3.5-period stall: two slots lost. The post-stall t must equal the
    # reference accumulation at its slot index bit-for-bit, which only holds
    # if the skip advances t by repeated addition, not `missed * period`.
    loop = make_loop(
        ft,
        program=costed(ft, costs={1: 3.5 * PERIOD}),
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

    def on_frame(t, frame):
        if len(events) == 1:
            loop.calls.call_soon(lambda: events.append("call"))

    loop = make_loop(ft, program=costed(ft, rendered=events), on_frame=[on_frame])
    loop.run(frames=3)
    assert events == ["render0", "call", "render1", "render2"]


def test_poisoned_bind_propagates():
    binds = [0]

    def setup(op, ctx):
        binds[0] += 1
        if binds[0] > 1:
            raise RuntimeError("boom at rebind")

    ft = FakeTime()
    renderer = hosted(source_op("bad_rebind_test", lambda op, c: np.zeros((len(c.index), 3), np.float32),
                                setup=setup), line(N_PX), seed=SEED)

    def failing_supervisor():
        # A supervisor that swallows the bind failure instead of restoring
        # the last-good binding leaves the renderer poisoned...
        try:
            renderer.rebind(line(N_PX))
        except RuntimeError:
            pass

    def on_frame(t, frame):
        loop.calls.call_soon(failing_supervisor)

    loop = PacedLoop(renderer, fps=60.0, on_frame=[on_frame], now=ft.now, sleep=ft.sleep)
    # ...and the next advance_to is loud, straight out of run().
    with pytest.raises(RuntimeError, match="not bound"):
        loop.run(frames=10)


def test_callback_advancing_renderer_time_is_adopted():
    ft = FakeTime()
    delivered: list[float] = []
    renderer = hosted(FLOW, line(N_PX), seed=SEED)

    def probe_frame():
        renderer.step(0.5)  # a supervisor rendering a transition frame

    def on_frame(t, frame):
        delivered.append(t)
        if len(delivered) == 1:
            loop.calls.call_soon(probe_frame)

    loop = PacedLoop(renderer, fps=60.0, on_frame=[on_frame], now=ft.now, sleep=ft.sleep)
    loop.run(frames=3)  # must not die with "time never goes backwards"
    # The loop adopts the advanced time: the run jumps forward, stays
    # monotonic, and keeps stepping one period per tick from there.
    assert delivered == sorted(delivered)
    assert delivered[1] == pytest.approx(delivered[0] + 0.5 + PERIOD, abs=1e-12)


def test_stop_before_run_is_honored_not_erased():
    ft = FakeTime()
    loop = make_loop(ft)
    loop.stop()  # standing request: e.g. a supervisor aborting at startup
    assert loop.run(frames=5).ticks == 0
    # Each run() consumes the request on exit; the next one is normal.
    assert loop.run(frames=3).ticks == 3


def test_rejects_nonpositive_fps():
    ft = FakeTime()
    with pytest.raises(ValueError, match="fps"):
        make_loop(ft, fps=0.0)


def test_real_time_smoke():
    """The one real-clock run: structure only, no timing assertions — bench
    numbers are distributions, never test gates (T-5)."""
    delivered: list[float] = []
    renderer = hosted(FLOW, line(N_PX), seed=SEED)
    loop = PacedLoop(renderer, fps=60.0, on_frame=[lambda t, frame: delivered.append(t)])
    stats = loop.run(frames=3)
    assert stats.ticks == 3
    assert stats.missed_frames >= 0
    assert len(delivered) == 3
    assert delivered == sorted(delivered)


# ---- the frame stages and the call queue -------------------------------------


def test_a_tick_drains_then_runs_the_before_hooks_renders_and_runs_the_after_stages():
    ft = FakeTime()
    events: list[str] = []

    def stage(name):
        def run(t, frame):
            events.append(name)
            return frame + 1.0 if name == "dim" else frame
        return run

    loop = make_loop(
        ft, program=costed(ft, rendered=events), before=[lambda t: events.append(f"before {t:.4f}")],
        after=[stage("blink"), stage("dim")], on_frame=[lambda t, f: events.append(f"sink {f[0, 0]}")],
    )
    loop.calls.call_soon(lambda: events.append("call"))
    loop.run(frames=1)
    assert events == ["call", f"before {1 / 60:.4f}", "render0", "blink", "dim", "sink 1.0"]


def test_a_frame_no_stage_replaced_is_still_a_read_only_copy():
    ft = FakeTime()
    seen: list[np.ndarray] = []
    renderer = hosted(costed(ft), line(N_PX), seed=SEED)
    loop = PacedLoop(renderer, fps=60.0, after=[lambda t, f: f], on_frame=[lambda t, f: seen.append(f)],
                     now=ft.now, sleep=ft.sleep)
    loop.run(frames=1)
    assert not seen[0].flags.writeable and not np.shares_memory(seen[0], renderer.bound.buffers.pixels)


def answer_on_a_thread(calls: Calls, fn, timeout: float = 5.0) -> list:
    out: list = []
    waiter = threading.Thread(target=lambda: out.append(calls.ask(fn, "late", timeout)))
    waiter.start()
    return [out, waiter]


def test_an_ask_waits_for_the_loop_and_contains_what_raises():
    calls = Calls()
    out, waiter = answer_on_a_thread(calls, lambda: "refused")
    wait_until(lambda: calls._queue)
    calls.drain()
    waiter.join(2.0)
    assert out == ["refused"]

    def broken() -> None:
        raise RuntimeError("boom")

    out, waiter = answer_on_a_thread(calls, broken)
    wait_until(lambda: calls._queue)
    calls.drain()  # must not raise: the loop outlives a failed request
    waiter.join(2.0)
    assert out == ["the request failed: RuntimeError: boom"]
    assert calls.ask(lambda: None, "late", timeout=0.01) == "late"


def test_a_late_ask_still_runs_unless_it_is_definite():
    """A definite ask that answers `late` drops its call, and one the loop
    has started is waited for, so `late` always means it never ran."""
    ran: list[str] = []
    calls = Calls()
    assert calls.ask(lambda: ran.append("loose"), "late", timeout=0.01) == "late"
    assert calls.ask(lambda: ran.append("definite"), "late", timeout=0.01, definite=True) == "late"
    calls.drain()
    assert ran == ["loose"]

    started, release = threading.Event(), threading.Event()

    def slow() -> str:
        started.set()
        release.wait(5.0)
        return "refused"

    out: list = []
    waiter = threading.Thread(target=lambda: out.append(calls.ask(slow, "late", timeout=0.05, definite=True)))
    waiter.start()
    wait_until(lambda: calls._queue)
    loop = threading.Thread(target=calls.drain)
    loop.start()
    started.wait(5.0)
    waiter.join(0.2)
    assert out == []  # past its timeout, it waits for the call the loop started
    release.set()
    for thread in (waiter, loop):
        thread.join(2.0)
    assert out == ["refused"]


def test_close_answers_every_waiting_ask_and_every_later_one():
    calls = Calls()
    out, waiter = answer_on_a_thread(calls, lambda: None, timeout=30.0)  # nothing drains
    wait_until(lambda: calls._waiting)
    calls.close()
    waiter.join(2.0)
    assert out == [STOPPING]
    assert calls.ask(lambda: None, "late") == STOPPING


def test_close_racing_a_new_ask_still_answers_it():
    """`close` landing between an ask's check and its registration is the
    window that would leave a waiter hanging until its timeout."""
    calls = Calls()

    class CloseFirst(set):
        def add(self, item):
            calls.close()
            super().add(item)

    calls._waiting = CloseFirst()
    assert calls.ask(lambda: None, "late", timeout=1.0) == STOPPING
    assert not calls._waiting
