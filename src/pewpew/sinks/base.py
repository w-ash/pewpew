"""The Sink protocol and the shared display-output helpers.

A sink is the engine's edge: it takes the per-tick `(N, 3)` float32
linear-light frame and puts it somewhere — a terminal, a browser, later a
DDP socket. Sinks are blocking and fallible by design; the render loop is
neither, so a sink never runs on the loop thread directly. The composition
is always:

    PacedLoop(renderer, on_frame=[SinkDriver(sink.send)])

with the `SinkDriver` (pewpew.pace) supplying newest-wins coalescing and
error containment, and the sink pacing its own output rate with a
`RateGate` inside `send` (ADR-010: each sink paces itself at its own
output rate; blocking the driver worker is the throttle — the mailbox
coalesces frames meanwhile).

Fill/latch (ADR-003): the sink API must leave room for DDP's fill-then-
latch shape. It does so by fusing both into `send` — a single-transaction
sink fills its packets and sets the latch/Push flag on the last one inside
one `send` call. A cross-receiver synchronized latch would be a
coordinator sitting *above* several sinks, not a protocol method, so
`send(t, frame)` stays the whole per-frame surface.
"""

from __future__ import annotations

import time
from typing import Callable, Protocol, runtime_checkable

import numpy as np

# Display gamma for 8-bit screen output (terminal cells, browser canvas).
# The preview fix in commit b68b96a exists because omitting this crushed
# low-end glow (comet trails, SDF shell) to black. NOT the perceptual LED
# output curve — that is ADR-001's 16-bit LUT (gamma ~2.6-3.0), a Phase-2
# concern that lives with the LED color pipeline, not here.
DISPLAY_GAMMA = 2.2


@runtime_checkable
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
        """Emit one frame. May block (rate gate, slow client) and may
        raise — it runs on a SinkDriver worker, which contains both.
        `frame` is the loop's shared read-only copy: never mutate it
        (render.py explains why in-place gamma would corrupt patterns)."""
        ...


@runtime_checkable
class Controls(Protocol):
    """The back-channel a sink offers a viewer: read the knobs, turn them.

    Kept to two methods so a sink implementing it never imports `Renderer`
    or `PacedLoop` — the runner supplies the object that knows about thread
    discipline. `set` returns a refusal *reason* rather than raising because
    it is called on a connection thread, and because that reason may cross
    an unauthenticated socket: it must name the knob and the range and
    never a source path (ADR-006 amendment; architecture §5 trust model).
    """

    def describe(self) -> list[dict]:
        """Current declarations and values, in display order."""
        ...

    def set(self, name: str, value: object) -> str | None:
        """Request a value. Returns None if accepted, else why it was not."""
        ...


def to_display_u8(frame: np.ndarray) -> np.ndarray:
    """Linear-light float frame -> display-ready `(N, 3)` uint8.

    The quantize-once point (Q-1): sanitize (range and finiteness are
    deliberately unchecked on the render path), apply display gamma, and
    quantize, so no client downstream ever applies its own curve.
    """
    v = np.clip(np.nan_to_num(frame, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    v = np.power(v, 1.0 / DISPLAY_GAMMA)
    return (v * 255.0).round().astype(np.uint8)


class RateGate:
    """Blocking output-rate limiter for a sink's `send`.

    Call `wait()` at the top of `send`: the first call passes immediately,
    later calls sleep until the next output slot. Sleeping on the
    SinkDriver worker *is* the design — the driver's one-slot mailbox
    coalesces frames while the gate sleeps, so a 30 fps sink under a
    60 fps engine drops every other frame with no further machinery.
    Falling behind re-bases the schedule to now rather than bursting to
    catch up: a sink has no backlog to clear, only a newest frame.

    `now`/`sleep` are injectable for tests, matching `PacedLoop`'s seam.
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
