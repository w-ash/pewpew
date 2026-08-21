"""The paced render loop: ADR-010's deadline-corrected clock and the
per-sink newest-wins backpressure seam.

`PacedLoop` is the live form of `render_sequence`: one
`Renderer.advance_to(t)` per schedule slot, paced against an absolute
deadline schedule — measure elapsed, sleep the remainder, correct
accumulated error. The wall clock decides *when* a frame runs; it never
decides *what* the frame contains: engine time comes from
`render.SlotClock`, so a live show renders bit-identically to
`render_sequence` at the same slot, skips or not. Rationale, precedents,
and the soak evidence live in ADR-010 and its 2026-08-20 amendment.

Threading contract: `run()` blocks its calling thread, which becomes the
loop thread and the sole owner of the Renderer. Mutate the renderer only
from `call_soon(fn)` (drained on the loop thread at the top of each tick)
or between `run()` calls. `stop()` is thread-safe and takes effect at the
tick boundary, so stop latency is bounded by one period plus one render.

Sink contract: `on_frame(t, frame)` callables receive one shared read-only
copy per tick and must never block or raise — the render loop must outlive
any sink (ADR-010 rejects blocking the loop on the slowest sink). Wrap a
blocking or fallible `send` in a `SinkDriver`: a per-sink worker thread
with a one-slot latest-frame mailbox, giving newest-wins coalescing with
at most two frames in flight (one sending, one pending — Fadecandy's
`MAX_FRAMES_PENDING=2` shape, HyperHDR's latest-wins drop).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from pewpew.render import Renderer, SlotClock

logger = logging.getLogger(__name__)


@dataclass
class PaceStats:
    """Counters, deliberately not distributions — those belong in the bench
    (`bench/bench_pacing.py`), and T-5 says bench numbers are evidence, not
    gates. Counters are bounded for a show of any length."""

    ticks: int = 0  # frames actually rendered
    skips: int = 0  # blown-deadline events (slack <= 0 at the pace point)
    missed_frames: int = 0  # schedule slots skipped past, summed over skips


class PacedLoop:
    """One deadline-corrected render loop over a bound `Renderer`.

    `now`/`sleep` are injectable so tests pace against fake time; defaults
    are the real monotonic clock. An injected `now` must advance (the spin
    variant polls it). `spin_margin=None` is the plain sleeper; a float
    enables the spin variant — sleep short of the deadline by the margin,
    then busy-wait — the escape hatch if device-side interpolation ever
    finds the sleep-timer jitter visible (§12 item 11). Measure the margin
    with `measure_spin_margin` at startup; the loop never probes.
    """

    def __init__(
        self,
        renderer: Renderer,
        fps: float = 60.0,
        on_frame: Sequence[Callable[[float, np.ndarray], None]] = (),
        *,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
        spin_margin: float | None = None,
    ) -> None:
        if fps <= 0.0:
            raise ValueError(f"fps must be positive, got {fps!r}")
        self._renderer = renderer
        self._fps = float(fps)
        self._on_frame = tuple(on_frame)
        self._now = now
        self._sleep = sleep
        self._spin_margin = spin_margin
        self._stop = threading.Event()
        self._calls: deque[Callable[[], None]] = deque()
        self._stats = PaceStats()
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

    def call_soon(self, fn: Callable[[], None]) -> None:
        """Run `fn` on the loop thread at the top of the next tick.

        The seam for mid-show renderer mutation (rebind, pattern swap — the
        hot-reload story's supervisor). A callback that advances the
        renderer's own time (a probe frame via `step()`) is tolerated: the
        loop adopts the later time and the show jumps forward, never dies.
        An exception from `fn` propagates out of `run()`: bind failures are
        loud (render.py), and it is the caller's job to catch what it wants
        survived.
        """
        self._calls.append(fn)

    def run(self, frames: int | None = None) -> PaceStats:
        """Pace the renderer; blocks until `frames` ticks or `stop()`.

        Resume-safe: engine time continues from `renderer.t`, so a second
        `run()` never steps time backwards.
        """
        if self._running:
            raise RuntimeError("PacedLoop.run() is not re-entrant — the loop is already running")
        self._running = True
        try:
            clock = SlotClock(self._fps, start=self._renderer.t)
            next_due = self._now()  # absolute schedule, seeded once — never re-based
            done = 0
            while not self._stop.is_set() and (frames is None or done < frames):
                while self._calls:
                    self._calls.popleft()()
                # A callback may have advanced the renderer; adopt the later
                # time. Exact in the normal path — after our own advance_to,
                # renderer.t == clock.t, and during skip catch-up clock.t is
                # ahead — so max() never perturbs the accumulation.
                clock.t = max(clock.t, self._renderer.t)
                frame = self._renderer.advance_to(clock.advance())
                self._stats.ticks += 1
                done += 1
                if self._on_frame:
                    # One immutable copy shared by every sink: the renderer's
                    # live frame must not be held across frames (render.py),
                    # and read-only makes cross-sink corruption impossible.
                    out = frame.copy()
                    out.setflags(write=False)
                    for cb in self._on_frame:
                        cb(clock.t, out)
                next_due += clock.period  # deadline-corrected: error accumulates here
                slack = next_due - self._now()
                if slack > 0:
                    if self._spin_margin is not None:
                        if slack > self._spin_margin:
                            self._sleep(slack - self._spin_margin)
                        while self._now() < next_due and not self._stop.is_set():
                            pass
                    else:
                        self._sleep(slack)
                else:
                    # Deadline already blown: skip ahead so we never chase a
                    # backlog (newest-wins, never queue deeper).
                    #
                    # No +1 here. The next iteration adds one period of its
                    # own before testing slack, so landing next_due on the
                    # last *past* slot makes that addition arrive on the
                    # first future one. Adding 1 here consumed an extra slot
                    # and silently dropped one more frame per skip (the bench
                    # review's off-by-one). The next frame renders
                    # immediately — late, in the last past slot — rather
                    # than idling until the schedule comes around.
                    missed = int(-slack // clock.period)
                    next_due += missed * clock.period
                    clock.advance(missed)  # engine time stays locked to slots
                    self._stats.skips += 1
                    self._stats.missed_frames += missed
            return self._stats
        finally:
            self._stop.clear()
            self._running = False


class SinkDriver:
    """Newest-wins mailbox and worker thread around a blocking `send`.

    At most two frames are in flight: one being sent, one pending.
    `submit()` replaces the pending frame and never blocks, so a stalled
    sink can never back up the render loop — pending frames coalesce and
    `dropped` counts what newest-wins discarded. Exceptions from `send`
    are contained and counted (`errors`), first of each type logged; the
    worker keeps consuming. Instances are callables so they plug into
    `PacedLoop(on_frame=[driver])` directly.

    The lifecycle is one-shot: `start()` once, `stop()` once, then create
    a new driver. Submitting while the worker is not running drops the
    frame with a single warning rather than raising — a sink must never
    take the show down.
    """

    def __init__(self, send: Callable[[float, np.ndarray], None], *, name: str = "sink") -> None:
        self._send = send
        self.name = name
        self.dropped = 0  # frames coalesced away by newest-wins, or dropped dead
        self.errors = 0  # contained send exceptions
        self._cond = threading.Condition()
        self._pending: tuple[float, np.ndarray] | None = None
        self._started = False
        self._stopping = False
        self._warned_dead = False
        self._logged_types: set[type] = set()
        # Daemon so a wedged send never blocks interpreter exit; stop()
        # still joins for the orderly path (bench AudioThread precedent).
        self._worker = threading.Thread(target=self._run, name=f"pewpew-sink-{name}", daemon=True)

    def start(self) -> None:
        if self._started or self._stopping:
            raise RuntimeError(
                f"SinkDriver {self.name!r} is one-shot and was already "
                f"{'stopped' if self._stopping else 'started'} — create a new driver"
            )
        self._worker.start()
        self._started = True

    def stop(self, timeout: float = 1.0) -> bool:
        """Signal the worker, join, and report whether it actually exited.

        A pending frame is discarded, not drained — stopping a sink must
        not wait on its backlog. False means the worker is still mid-send;
        do not tear down its transport yet.
        """
        with self._cond:
            self._stopping = True
            self._cond.notify()
        if not self._started:
            return True
        self._worker.join(timeout)
        if self._worker.is_alive():
            logger.warning(
                "sink %r worker still mid-send after stop(timeout=%s) — "
                "its transport is still in use",
                self.name,
                timeout,
            )
            return False
        return True

    def __enter__(self) -> "SinkDriver":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def submit(self, t: float, frame: np.ndarray) -> None:
        """Hand the newest frame to the worker; never blocks, never raises."""
        if not self._worker.is_alive():
            self.dropped += 1
            if not self._warned_dead:
                self._warned_dead = True
                logger.warning(
                    "sink %r worker is not running (%s); frames are being dropped",
                    self.name,
                    "stopped" if self._stopping else "never started",
                )
            return
        with self._cond:
            if self._pending is not None:
                self.dropped += 1
            self._pending = (t, frame)
            self._cond.notify()

    # A driver is its own on_frame callable.
    __call__ = submit

    def _run(self) -> None:
        while True:
            with self._cond:
                while self._pending is None and not self._stopping:
                    self._cond.wait()
                if self._stopping:
                    return
                t, frame = self._pending  # type: ignore[misc]
                self._pending = None
            try:
                self._send(t, frame)
            except Exception as exc:
                self.errors += 1
                if type(exc) not in self._logged_types:
                    self._logged_types.add(type(exc))
                    logger.exception("sink %r send failed (contained)", self.name)


def measure_spin_margin(
    now: Callable[[], float] = time.perf_counter,
    sleep: Callable[[float], None] = time.sleep,
    *,
    period: float = 1.0 / 60.0,
    samples: int = 200,
    floor: float = 0.0005,
    safety: float = 1.5,
) -> float:
    """Measure how far `sleep(period)` overshoots on this host and return
    the spin margin: p99 overshoot × `safety`, floored at `floor`.

    Port of the bench's `sleep_quantization_ms` + `spin_margin_s`: macOS
    overshoots ~4 ms at the frame period, Linux typically <0.2 ms — a
    constant cannot serve both, and probing inside the loop would be
    nondeterministic, so the caller measures once at startup. Costs
    `samples × period` of wall time (~3.3 s at defaults).
    """
    overshoots = []
    for _ in range(samples):
        before = now()
        sleep(period)
        overshoots.append(now() - before - period)
    overshoots.sort()
    p99 = overshoots[int(0.99 * (samples - 1))]
    return max(floor, p99 * safety)
