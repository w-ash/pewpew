"""The Sink protocol and the shared display-output helpers.

A sink is the engine's edge: it takes each tick's `(N, 3)` float32
linear-light frame to a terminal, a browser or a DDP socket. A sink may
block and raise; the render loop may not, so a sink never runs on the loop
thread:

    PacedLoop(renderer, on_frame=[SinkDriver(sink.send)])

`SinkDriver` coalesces frames newest-wins and contains errors, and the sink
paces its own output rate with a `RateGate` inside `send` (ADR-010).

Fill/latch (ADR-003): `send` fills a frame's packets and sets the latch on
the last one, so `send(t, frame)` is the whole per-frame surface. A latch
synchronized across receivers would be a coordinator above several sinks.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from typing import Any, Generic, Protocol, Self, TypeVar

import numpy as np

from pewpew.errors import Refusal

logger = logging.getLogger(__name__)

# Display gamma for 8-bit screens (terminal cells, browser canvas): without
# it, low-end glow (trails, soft edges) shows as black. Not the LED
# curve, which is ADR-001's 16-bit LUT.
DISPLAY_GAMMA = 2.2


class Sink(Protocol):
    """What every output implements; see the module docstring for how a
    sink composes with `SinkDriver` and where fill/latch semantics live."""

    def start(self) -> None:
        """Acquire the transport (open socket, take over the terminal)."""
        ...

    def stop(self) -> None:
        """Release the transport; idempotent, safe after a failed start."""
        ...

    def send(self, t: float, frame: np.ndarray) -> None:
        """Emit one frame. May block and may raise: it runs on a SinkDriver
        worker, which contains both. `frame` is the loop's shared read-only
        copy."""
        ...


class Control(Protocol):
    """What a sink offers a viewer: the params and the aura state to draw,
    and the requests a viewer may make. `pewpew.aura.control.AuraControl`
    implements it.

    Kept to these methods so a sink never imports `Renderer` or
    `PacedLoop`: the object behind it knows the thread discipline. Every
    method runs on a connection or sink thread and never raises, and every
    text and value it returns may cross an unauthenticated socket: names,
    never a source path (ADR-006 amendment; architecture §5 trust model).
    """

    def describe(self) -> list[dict]:
        """Every knob of the running look in display order, each record's
        `name` its address (pewpew.compose.controls)."""
        ...

    def values(self) -> dict:
        """Every knob's value in its JSON form, by address."""
        ...

    def mod(self) -> dict:
        """Each knob a route drives, at its live value (base plus the
        routes' offsets), by address; empty when no route runs."""
        ...

    def state(self) -> dict:
        """The aura state, JSON-ready and names only;
        web/src/wire/protocol.ts types it. Cheap: a sink reads it
        every frame."""
        ...

    def health(self) -> dict | None:
        """The latest health snapshot, replaced whole when it changes, or
        None when the run has no monitor."""
        ...

    def catalog(self) -> dict:
        """What a layer can run and what each blend mode does, for a page's
        "add layer" cards; the same object until it changes."""
        ...

    def arrangement(self) -> dict[str, Any] | None:
        """The run's arrangement as the page edits it and its digest,
        `{"arrangement", "base"}`, both None when it cannot be edited, or
        None without a rig file; the same object until it changes."""
        ...

    def report(self) -> dict | None:
        """The running rig's `issues` and electrical `report`, or None
        without a rig file; the same object until it changes."""
        ...

    @property
    def capabilities(self) -> tuple[str, ...]:
        """The requests this control takes beyond the page's own: `look`,
        for clients outside the package, and `arrange`, which the page reads."""
        ...

    def request(self, message: Mapping[str, object]) -> Refusal | Future[Refusal | None] | None:
        """Act on one inbound message `{"type": control, ...}`. Returns why
        it was refused, or None when it was accepted, or when it names no
        control and carries no `id`. May block until the loop thread has
        answered. A request that takes longer (a look to make) returns a
        future of that answer instead, so the sink reads on."""
        ...


def to_display_u8(frame: np.ndarray) -> np.ndarray:
    """Linear-light float frame -> display-ready `(N, 3)` uint8.

    The quantize-once point (Q-1): sanitize (the render path checks no
    range), apply display gamma and quantize, so no client applies a curve.
    """
    return _quantize(np.power(sanitize(frame), 1.0 / DISPLAY_GAMMA))


def from_display_u8(rgb: np.ndarray, gamma: float = DISPLAY_GAMMA) -> np.ndarray:
    """Display-ready uint8 -> approximate linear-light float32: the inverse
    of `to_display_u8`, less what its quantization lost (the most at the
    dark end). `gamma` is the gamma the bytes carry; a preview's hello
    gives it as `display_gamma`."""
    table = np.power(np.arange(256, dtype=np.float64) / 255.0, gamma).astype(np.float32)
    return table[np.asarray(rgb, dtype=np.uint8)]


def to_linear_u8(frame: np.ndarray) -> np.ndarray:
    """Linear-light float frame -> linear `(N, 3)` uint8 for an LED wire.

    The quantize-once point for 8-bit LED sinks: sanitize and quantize with
    no curve, because LED PWM duty is linear in emitted light.
    """
    return _quantize(sanitize(frame))


def sanitize(frame: np.ndarray) -> np.ndarray:
    """A frame as a sink shows it: NaN and -inf -> 0, +inf -> 1, then
    clipped to [0, 1]. Any shape."""
    return np.clip(np.nan_to_num(frame, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _quantize(v: np.ndarray) -> np.ndarray:
    """[0, 1] floats -> uint8, rounded once."""
    return (v * 255.0).round().astype(np.uint8)


class RateGate:
    """Blocking output-rate limiter for a sink's `send`.

    Call `wait()` at the top of `send`: the first call passes at once, and
    later calls sleep until the next output slot. The SinkDriver mailbox
    coalesces frames while the gate sleeps, so a 30 fps sink under a 60 fps
    engine drops every other frame. Falling behind re-bases the schedule to
    now: a sink has no backlog to clear, only a newest frame.
    """

    def __init__(
        self,
        max_fps: float,
        *,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_fps <= 0.0:
            raise ValueError(f"max_fps must be positive, got {max_fps!r}")
        self._period = 1.0 / float(max_fps)
        self._now = now
        self._sleep = sleep
        self._next_due: float | None = None

    def wait(self) -> None:
        t = self._now()
        if self._next_due is None:
            self._next_due = t + self._period
            return
        slack = self._next_due - t
        if slack > 0.0:
            self._sleep(slack)
            self._next_due += self._period
        else:
            self._next_due = t + self._period


# What a SinkDriver carries: the loop's frame, or a fan-out sink's
# pre-encoded bytes. The driver never looks inside.
P = TypeVar("P")


class SinkDriver(Generic[P]):
    """Newest-wins mailbox and worker thread around a blocking `send`.

    At most two frames are in flight, one being sent and one pending
    (Fadecandy's `MAX_FRAMES_PENDING=2`). `submit()` replaces the pending
    frame and never blocks, so a stalled sink cannot back up the render
    loop; `dropped` counts what newest-wins discarded. Exceptions from
    `send` are contained and counted (`errors`), the first of each type
    logged. A driver is its own `on_frame` callable.

    One-shot: `start()` once, `stop()` once. Submitting while the worker is
    not running drops the frame with one warning. `drain()` before `stop()`
    is the orderly exit: it waits for the pending frame to be sent, which
    `stop()` does not.
    """

    def __init__(self, send: Callable[[float, P], None], *, name: str = "sink") -> None:
        self._send = send
        self.name = name
        self.dropped = 0  # frames coalesced away by newest-wins, or dropped dead
        self.errors = 0  # contained send exceptions
        self._cond = threading.Condition()
        self._pending: tuple[float, P] | None = None
        self._started = False
        self._stopping = False
        self._sending = False  # worker is inside _send; see drain()
        self._warned_dead = False
        self._logged_types: set[type] = set()
        # Daemon so a wedged send never blocks interpreter exit.
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
        """Signal the worker, join, and report whether it exited. A pending
        frame is discarded. False means the worker is still mid-send: do not
        tear down its transport yet."""
        with self._cond:
            self._stopping = True
            self._cond.notify_all()
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

    def drain(self, timeout: float = 1.0) -> bool:
        """Block until the mailbox is empty and the worker is idle, so a
        bounded run (`--frames N`) shows its last frame. False if the sink
        is still busy at `timeout`, or nothing will consume the pending
        frame (never started, or stopping)."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self._pending is not None or self._sending:
                if not self._started or self._stopping:
                    return False  # nothing will ever consume it
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    return False
                self._cond.wait(remaining)
            return True

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def submit(self, t: float, frame: P) -> None:
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
            self._cond.notify_all()

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
                self._sending = True
            try:
                self._send(t, frame)
            except Exception as exc:
                self.errors += 1
                if type(exc) not in self._logged_types:
                    self._logged_types.add(type(exc))
                    logger.exception("sink %r send failed (contained)", self.name)
            finally:
                with self._cond:
                    self._sending = False
                    self._cond.notify_all()
