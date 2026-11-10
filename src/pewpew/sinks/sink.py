"""The Sink protocol and the shared display-output helpers.

A sink is the engine's edge: it takes each tick's `(N, 3)` float32
linear-light frame to a terminal, a browser or a DDP socket. A sink may
block and raise; the render loop may not, so a sink never runs on the loop
thread:

    PacedLoop(renderer, fps, on_frame=[SinkDriver(sink.send, every=stride(fps, sink.max_fps))])

The loop is the only clock (ADR-010). A sink that takes fewer frames than
the loop renders gets every k-th tick (`stride`), so its frames are evenly
spaced; no sink sleeps to pace itself, since a second clock beats against
the loop's and drops frames unevenly. `SinkDriver` coalesces frames
newest-wins and contains errors.

Fill/latch (ADR-003): `send` fills a frame's packets and sets the latch on
the last one, so `send(t, frame)` is the whole per-frame surface. A latch
synchronized across receivers would be a coordinator above several sinks.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from typing import TYPE_CHECKING, Any, Generic, Protocol, Self, TypeVar

import numpy as np

from pewpew.errors import Refusal

if TYPE_CHECKING:
    from pewpew.aura.control import Exported

logger = logging.getLogger(__name__)

# Display gamma for 8-bit screens (terminal cells, browser canvas): without
# it, low-end glow (trails, soft edges) shows as black. Not the LED
# curve, which is ADR-001's 16-bit LUT.
DISPLAY_GAMMA = 2.2


class Sink(Protocol):
    """What every output implements; see the module docstring for how a
    sink composes with `SinkDriver` and where fill/latch semantics live."""

    max_fps: float
    """The most frames a second it takes; the loop feeds it every
    `stride(loop_fps, max_fps)`-th tick."""

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
        for clients outside the package, and `arrange`, `export` and
        `publish`, which the page reads."""
        ...

    def request(self, message: Mapping[str, object]) -> Refusal | Exported | Future[Refusal | None] | None:
        """Act on one inbound message `{"type": control, ...}`. Returns why
        it was refused, or None when it was accepted, or when it names no
        control and carries no `id`; an `export` returns its file
        (`Exported`). May block until the loop thread has answered. A
        request that takes longer (a look to make) returns a future of
        that answer instead, so the sink reads on."""
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


def sanitize(frame: np.ndarray) -> np.ndarray:
    """A frame as a sink shows it: NaN and -inf -> 0, +inf -> 1, then
    clipped to [0, 1]. Any shape."""
    return np.clip(np.nan_to_num(frame, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _quantize(v: np.ndarray) -> np.ndarray:
    """[0, 1] floats -> uint8, rounded once."""
    return (v * 255.0).round().astype(np.uint8)


# Temporal dither (ADR-002 tier 3, after HyperHDR's adaptive temporal
# error diffusion, research/code-reading/hyperhdr.md §2). Units are 8-bit steps.
DITHER_MOTION = 0.01  # least change of a pixel's fastest channel that carries error
DITHER_LEAK_FLOOR = 0.8  # share of the error a fast change keeps
DITHER_FAST = 50.0  # a change c (full scale = 1) is fast when c**2 * DITHER_FAST >= 1


class Dither:
    """Linear-light float frames -> linear `(N, 3)` uint8 for an 8-bit LED
    wire, with temporal error diffusion per pixel.

    LED duty is linear in light (ADR-001), so there is no curve. Each pixel
    carries its rounding error into its next frame, so a slow fade shows
    the mean of its true level over the frames, not a staircase. Error
    carries only while the pixel's fastest channel moves the same way as
    in the frame before, by at least `DITHER_MOTION` steps: a reversal or
    a jitter gets plain rounding, which does not shimmer. A fast change
    keeps less of the error (down to `DITHER_LEAK_FLOOR`). A pixel equal to
    its last input, or below half a step, gets plain rounding and drops
    its error, so a held color is steady.

    One per output stream: the state is the last frame's. A frame of a new
    size starts it again. Same frames in, same bytes out.
    """

    def __init__(self) -> None:
        self._last: np.ndarray | None = None  # (N, 3) float32, in steps
        self._error = np.zeros((0, 3), np.float32)
        self._flow = np.zeros(0, np.int8)  # sign of each pixel's last change

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        x = sanitize(np.asarray(frame, np.float32)) * np.float32(255.0)
        last = self._last
        self._last = x
        if last is None or last.shape != x.shape:
            self._error = np.zeros_like(x)
            self._flow = np.zeros(len(x), np.int8)
            return np.rint(x).astype(np.uint8)
        diff = x - last
        fastest = diff[np.arange(len(x)), np.abs(diff).argmax(axis=1)]
        flow = np.sign(fastest).astype(np.int8)
        carry = (flow != 0) & (flow == self._flow) & (np.abs(fastest) >= DITHER_MOTION)
        target = x + np.where(carry[:, None], self._error, np.float32(0.0))
        out = np.clip(np.rint(target), 0.0, 255.0)
        fast = np.clip((fastest / np.float32(255.0)) ** 2 * np.float32(DITHER_FAST), 0.0, 1.0)
        leak = np.float32(1.0) - np.float32(1.0 - DITHER_LEAK_FLOOR) * fast
        error = (target - out) * leak[:, None]
        held = (flow == 0) | (x.max(axis=1) < 0.5)
        out[held] = np.rint(x[held])
        error[held] = 0.0
        flow[held] = 0
        self._error = error.astype(np.float32)
        self._flow = flow
        return out.astype(np.uint8)


def stride(loop_fps: float, max_fps: float) -> int:
    """Loop ticks between a sink's frames: the least whole k with
    `loop_fps / k <= max_fps`."""
    if loop_fps <= 0.0 or max_fps <= 0.0:
        raise ValueError(f"rates must be positive, got {loop_fps!r} and {max_fps!r}")
    return max(1, math.ceil(loop_fps / max_fps - 1e-9))


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

    With `every` k, it takes the first submit and every k-th after it and
    ignores the rest, so a slower sink gets evenly spaced loop ticks
    (`stride`).

    One-shot: `start()` once, `stop()` once. Submitting while the worker is
    not running drops the frame with one warning. `drain()` before `stop()`
    is the orderly exit: it waits for the pending frame to be sent, which
    `stop()` does not.
    """

    def __init__(self, send: Callable[[float, P], None], *, name: str = "sink", every: int = 1) -> None:
        if every < 1:
            raise ValueError(f"every must be at least 1, got {every!r}")
        self._send = send
        self.name = name
        self.every = every
        self._ticks = 0  # submits seen, for `every`
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
        """Hand the newest frame to the worker, if this submit is one of
        every `every`; never blocks, never raises."""
        tick, self._ticks = self._ticks, self._ticks + 1
        if tick % self.every:
            return
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
