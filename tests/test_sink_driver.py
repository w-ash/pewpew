"""SinkDriver: newest-wins backpressure, bounded at two frames in flight.

Real worker threads, synchronized with Events and Semaphores — never with
sleeps, so the tests are deterministic and cost no wall time beyond thread
scheduling.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest
from conftest import FakeTime

from pewpew import Renderer, line
from pewpew.pace import PacedLoop, SinkDriver
from pewpew.patterns.plasma import Plasma

N_PX = 16


def frame_of(v: float) -> np.ndarray:
    return np.full((N_PX, 3), v, dtype=np.float32)


def test_newest_wins_coalescing():
    gate = threading.Event()
    entered = threading.Event()
    completions = threading.Semaphore(0)
    seen: list[float] = []

    def send(t, frame):
        seen.append(t)
        entered.set()
        gate.wait(timeout=5.0)
        completions.release()

    with SinkDriver(send) as driver:
        driver.submit(1.0, frame_of(1))
        assert entered.wait(timeout=5.0)  # worker is inside send(1)
        for v in (2.0, 3.0, 4.0, 5.0):
            driver.submit(v, frame_of(v))  # coalesce while blocked
        gate.set()
        assert completions.acquire(timeout=5.0)
        assert completions.acquire(timeout=5.0)  # the one pending frame went out
    assert seen == [1.0, 5.0]  # newest won; 2..4 never sent
    assert driver.dropped == 3


def test_at_most_one_pending_regardless_of_submit_count():
    gate = threading.Event()
    entered = threading.Event()

    def send(t, frame):
        entered.set()
        gate.wait(timeout=5.0)

    with SinkDriver(send) as driver:
        driver.submit(1.0, frame_of(1))
        assert entered.wait(timeout=5.0)
        for v in range(2, 50):
            driver.submit(float(v), frame_of(v))
        # One in send, one pending — the Fadecandy MAX_FRAMES_PENDING=2 bound.
        assert driver._pending is not None
        assert driver._pending[0] == 49.0
        assert driver.dropped == 47
        gate.set()


def test_submit_never_blocks():
    wedged = threading.Event()

    def send(t, frame):
        wedged.wait(timeout=30.0)  # effectively forever at test scale

    driver = SinkDriver(send)
    driver.start()
    try:
        for v in range(1000):
            driver.submit(float(v), frame_of(v))  # returns or the test hangs
        assert driver.dropped >= 998  # at most one in-send + one pending kept
    finally:
        wedged.set()
        driver.stop()


def test_loop_never_blocks_on_a_stalled_sink():
    stalled = threading.Event()

    def send(t, frame):
        stalled.wait(timeout=30.0)

    ft = FakeTime()
    renderer = Renderer(Plasma(), line(N_PX), seed=42)
    driver = SinkDriver(send, name="stalled")
    driver.start()
    try:
        loop = PacedLoop(renderer, fps=60.0, on_frame=[driver], now=ft.now, sleep=ft.sleep)
        stats = loop.run(frames=20)
        # Full-rate pacing with a wedged sink: no skips, no blocking.
        assert stats.ticks == 20
        assert stats.skips == 0
        assert ft.t == pytest.approx(20 / 60.0, abs=1e-9)
    finally:
        stalled.set()
        driver.stop()


def test_sink_exception_contained(caplog):
    seen: list[float] = []
    processed = threading.Event()

    def send(t, frame):
        seen.append(t)
        processed.set()
        raise ValueError("wire fell out")

    with caplog.at_level("ERROR"):
        with SinkDriver(send, name="flaky") as driver:
            driver.submit(1.0, frame_of(1))
            assert processed.wait(timeout=5.0)
            processed.clear()
            driver.submit(2.0, frame_of(2))
            assert processed.wait(timeout=5.0)  # worker kept consuming
    assert seen == [1.0, 2.0]
    assert driver.errors == 2
    # First-of-type logged once, not per frame.
    assert sum("flaky" in r.getMessage() for r in caplog.records) == 1


def test_delivered_frame_is_read_only_and_unaliased():
    got: list[np.ndarray] = []
    ft = FakeTime()
    renderer = Renderer(Plasma(), line(N_PX), seed=42)
    loop = PacedLoop(
        renderer,
        fps=60.0,
        on_frame=[lambda t, frame: got.append(frame)],
        now=ft.now,
        sleep=ft.sleep,
    )
    loop.run(frames=2)
    first = got[0]
    with pytest.raises(ValueError):
        first[0, 0] = 1.0  # read-only: a sink cannot corrupt another's frame
    held = first.copy()
    loop.run(frames=3)  # advancing further must not mutate a held frame
    assert np.array_equal(first, held)


def test_stop_reports_worker_exit():
    driver = SinkDriver(lambda t, frame: None)
    driver.start()
    assert driver.stop() is True


def test_submit_before_start_drops_loudly(caplog):
    driver = SinkDriver(lambda t, frame: None, name="unstarted")
    with caplog.at_level("WARNING"):
        for v in range(5):
            driver.submit(float(v), frame_of(v))
    assert driver.dropped == 5
    # One warning for the condition, not one per frame.
    assert sum("unstarted" in r.getMessage() for r in caplog.records) == 1


def test_lifecycle_is_one_shot():
    driver = SinkDriver(lambda t, frame: None)
    assert driver.stop() is True  # stop before start: nothing was running
    with pytest.raises(RuntimeError, match="one-shot"):
        driver.start()  # a stopped driver cannot be (re)started


def test_stop_reports_wedged_worker(caplog):
    wedged = threading.Event()
    entered = threading.Event()

    def send(t, frame):
        entered.set()
        wedged.wait(timeout=30.0)

    driver = SinkDriver(send, name="wedged")
    driver.start()
    driver.submit(1.0, frame_of(1))
    assert entered.wait(timeout=5.0)  # worker is inside send before we stop
    with caplog.at_level("WARNING"):
        assert driver.stop(timeout=0.05) is False  # still mid-send: caller
        # must not tear down the transport yet
    assert any("wedged" in r.getMessage() for r in caplog.records)
    wedged.set()
    assert driver.stop(timeout=5.0) is True  # released: orderly exit


def test_drain_waits_for_the_frame_stop_would_discard():
    """`stop()` checks `_stopping` before `_pending`, so the last submitted
    frame is thrown away — the reason `--frames N` never showed frame N."""
    release = threading.Event()
    entered = threading.Event()
    sent: list[float] = []

    def send(t, frame):
        entered.set()
        release.wait(timeout=5.0)
        sent.append(t)

    driver = SinkDriver(send, name="drainable")
    driver.start()
    driver.submit(1.0, frame_of(1))
    assert entered.wait(timeout=5.0)  # worker is inside send #1
    driver.submit(2.0, frame_of(2))  # queued behind it: stop() would drop this
    release.set()
    assert driver.drain(timeout=5.0) is True
    assert sent == [1.0, 2.0]
    assert driver.dropped == 0
    assert driver.stop() is True


def test_drain_reports_false_when_nothing_will_consume_the_frame():
    driver = SinkDriver(lambda t, frame: None, name="never-started")
    assert driver.drain(timeout=5.0) is True  # empty mailbox, nothing to wait on
    driver.submit(1.0, frame_of(1))  # dropped: no worker
    assert driver.drain(timeout=5.0) is True


def test_drain_times_out_on_a_wedged_worker():
    wedged = threading.Event()
    entered = threading.Event()

    def send(t, frame):
        entered.set()
        wedged.wait(timeout=30.0)

    driver = SinkDriver(send, name="wedged-drain")
    driver.start()
    driver.submit(1.0, frame_of(1))
    assert entered.wait(timeout=5.0)
    assert driver.drain(timeout=0.05) is False  # still sending: bounded, not hung
    wedged.set()
    assert driver.stop(timeout=5.0) is True
