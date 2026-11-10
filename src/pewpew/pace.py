"""The paced render loop: ADR-010's deadline-corrected clock, the frame
stages around each render, and the loop thread's call queue.

`PacedLoop` is the live form of an offline render: one `advance_to(t)` per
schedule slot of its `FrameSource`, paced against an absolute deadline
schedule. The wall clock decides when a frame runs, never what it holds:
engine time comes from `render.SlotClock`, so a live run renders the same
bytes as an offline render at the same slot, skips or not (ADR-010 and its
2026-08-20 amendment).

One tick, in order, on the loop thread:

1. `calls` drains: every closure queued with `call_soon` or `ask` runs.
2. Each `before` hook runs with the engine time `t` of the frame about to
   render: per-frame aura control (triggers, looks), so what it starts is
   in this frame.
3. The source renders frame `t`.
4. Each `after` stage takes `(t, frame)` and returns the frame or a new
   array, never writing into it (blink, then the master). The loop copies
   the frame when no stage replaced it and makes the result read-only.
5. The loop sleeps to the end of the frame's slot, then every `on_frame`
   callable gets that one shared copy. Frames go out on the slot schedule,
   one period after their slot starts, whatever each render costs, so a
   sink sees them evenly spaced (a board that drops frames closer than
   its gate needs this, `pewpew.sinks.ddp`).

Step 4 and the hand-off in step 5 run only when there is an `on_frame`
callable. A hook or a stage must not raise: an exception from one ends
`run()`.

Threading: `run()` blocks its calling thread, which becomes the loop
thread and the sole owner of the source. Mutate the source only from a
closure queued on `calls`, or between `run()` calls. A closure that
advances the source's time makes the run jump forward. `stop()` is
thread-safe and takes effect at the tick boundary.

An `on_frame(t, frame)` callable must never block or raise (ADR-010): wrap
a blocking `send` in a `pewpew.sinks.sink.SinkDriver`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from concurrent.futures import Future, InvalidStateError
from dataclasses import dataclass
from typing import TypeVar

import numpy as np

from pewpew.errors import describe_exception
from pewpew.render import FrameSource, SlotClock

logger = logging.getLogger(__name__)

ASK_TIMEOUT_S = 5.0
STOPPING = "the aura is stopping"

R = TypeVar("R")  # what an `ask` closure refuses with

# A stage after the render: `(t, frame) -> frame`, never writing into `frame`.
Stage = Callable[[float, np.ndarray], np.ndarray]


@dataclass
class PaceStats:
    """Counters, bounded for a run of any length. Distributions belong in
    `bench/bench_pacing.py` (T-5)."""

    ticks: int = 0  # frames actually rendered
    skips: int = 0  # blown-deadline events (slack <= 0 at the pace point)
    missed_frames: int = 0  # schedule slots skipped past, summed over skips


class Calls:
    """The loop thread's queue: closures that run at the top of the next tick.

    `call_soon(fn)` is for the engine: an exception from `fn` propagates
    out of `PacedLoop.run()`, so bind failures stay loud (render.py).
    `ask(fn, late)` is for a request from another thread that needs the
    loop's answer: it queues `fn`, waits for the refusal (a reason, or a
    value that says more) or None that `fn` returns, and turns an
    exception from `fn` into a reason, because one
    out of a queued closure would end the run. A `definite` ask never
    answers `late` for an `fn` that then runs. `close()` answers every
    waiting ask with `STOPPING` once the loop runs no more closures, so no
    caller holds up a teardown; an ask after it gets `STOPPING` at once.
    """

    def __init__(self) -> None:
        self._queue: deque[Callable[[], object]] = deque()
        self._waiting: set[Future] = set()
        self._closed = False

    def call_soon(self, fn: Callable[[], object]) -> None:
        """Run `fn` on the loop thread at the top of the next tick. Any thread."""
        self._queue.append(fn)

    def ask(
        self, fn: Callable[[], R | None], late: str, timeout: float = ASK_TIMEOUT_S, *, definite: bool = False,
    ) -> R | str | None:
        """Run `fn` on the loop thread and return its answer, a refusal or
        None; `late` when the loop has not answered within `timeout`
        seconds, and `fn` still runs after that. When `definite`, a late
        `fn` that the loop has not started is dropped, so `late` means it
        never runs, and one it has started is waited for. Any thread but
        the loop's, which would wait for itself."""
        answer: Future = Future()
        # Taken once: by the loop to run `fn`, or by a late definite ask to drop it.
        claim = threading.Lock()
        # Registered before `_closed` is read, so a `close` on another
        # thread either sees this request and answers it, or this sees
        # `_closed` set.
        self._waiting.add(answer)
        if self._closed:
            self._waiting.discard(answer)
            return STOPPING

        def run() -> None:
            if claim.acquire(blocking=False):
                _settle(answer, _contained(fn))

        self._queue.append(run)
        try:
            return answer.result(timeout=timeout)
        except TimeoutError:
            if not definite or claim.acquire(blocking=False):
                return late
            return answer.result()  # running on the loop; `close` answers it at a teardown
        finally:
            self._waiting.discard(answer)

    def drain(self) -> None:
        """Run every queued closure, in order, including ones queued while
        it runs. Loop thread only."""
        while self._queue:
            self._queue.popleft()()

    def close(self) -> None:
        """Answer every waiting ask, and every later one, with `STOPPING`."""
        self._closed = True
        for answer in list(self._waiting):
            _settle(answer, STOPPING)


def _contained(fn: Callable[[], R | None]) -> R | str | None:
    try:
        return fn()
    except Exception as exc:
        logger.warning("a request failed", exc_info=True)
        return f"the request failed: {describe_exception(exc)}"


def _settle(answer: Future, reason: object) -> None:
    # `close` may have answered first; a second answer must not raise out
    # of the loop.
    try:
        answer.set_result(reason)
    except InvalidStateError:
        pass


class PacedLoop:
    """One deadline-corrected render loop over a `FrameSource`.

    `calls` and `stats` may be built first and passed in, so the parts
    that queue onto the loop or read its counters can be built before it.
    `now`/`sleep` are injectable so tests pace against fake time; defaults
    are the real monotonic clock.
    """

    def __init__(
        self,
        source: FrameSource,
        fps: float = 60.0,
        *,
        before: Sequence[Callable[[float], None]] = (),
        after: Sequence[Stage] = (),
        on_frame: Sequence[Callable[[float, np.ndarray], None]] = (),
        calls: Calls | None = None,
        stats: PaceStats | None = None,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if fps <= 0.0:
            raise ValueError(f"fps must be positive, got {fps!r}")
        self._source = source
        self._fps = float(fps)
        self._before = tuple(before)
        self._after = tuple(after)
        self._on_frame = tuple(on_frame)
        self.calls = Calls() if calls is None else calls
        self._stats = PaceStats() if stats is None else stats
        self._now = now
        self._sleep = sleep
        self._stop = threading.Event()
        self._running = False

    @property
    def stats(self) -> PaceStats:
        return self._stats

    def stop(self) -> None:
        """Ask the loop to exit; thread-safe; effective at the tick boundary.

        A standing request: issued while the loop is not running, it makes
        the next `run()` return immediately (each `run()` consumes it on
        exit), so a stop racing `run()` startup is honored, never lost.
        """
        self._stop.set()

    def run(self, frames: int | None = None) -> PaceStats:
        """Pace the source; blocks until `frames` ticks or `stop()`.

        Resume-safe: engine time continues from `source.t`, so a second
        `run()` never steps time backwards.
        """
        if self._running:
            raise RuntimeError("PacedLoop.run() is not re-entrant — the loop is already running")
        self._running = True
        try:
            clock = SlotClock(self._fps, start=self._source.t)
            next_due = self._now()  # absolute schedule, seeded once — never re-based
            done = 0
            while not self._stop.is_set() and (frames is None or done < frames):
                self.calls.drain()
                # A callback may have advanced the source; adopt the later
                # time. Exact in the normal path — after our own advance_to,
                # source.t == clock.t, and during skip catch-up clock.t is
                # ahead — so max() never perturbs the accumulation.
                clock.t = max(clock.t, self._source.t)
                t = clock.advance()
                for hook in self._before:
                    hook(t)
                frame = self._source.advance_to(t)
                self._stats.ticks += 1
                done += 1
                out = None
                if self._on_frame:
                    # One immutable copy shared by every sink: the source's
                    # live frame must not be held across frames (render.py),
                    # and read-only makes cross-sink corruption impossible.
                    out = frame
                    for stage in self._after:
                        out = stage(t, out)
                    if out is frame:
                        out = frame.copy()
                    out.setflags(write=False)
                next_due += clock.period  # deadline-corrected: error accumulates here
                slack = next_due - self._now()
                if slack > 0:
                    self._sleep(slack)
                else:
                    # Deadline blown: skip to the last past slot and render
                    # now, late. No +1: the next tick adds one period before
                    # testing slack, so it lands on the first future slot;
                    # +1 would drop one more frame per skip.
                    missed = int(-slack // clock.period)
                    next_due += missed * clock.period
                    clock.advance(missed)  # engine time stays locked to slots
                    self._stats.skips += 1
                    self._stats.missed_frames += missed
                if out is not None:
                    for cb in self._on_frame:
                        cb(t, out)
            return self._stats
        finally:
            self._stop.clear()
            self._running = False
