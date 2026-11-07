"""One visitor's renderer: a `Renderer` under a `PacedLoop` on its own thread.

Every change to the renderer runs on the loop thread between frames, through
`PacedLoop.calls`. Changes are coalesced, not queued: one slot for a bind,
one for a pattern and one value per param, applied by at most one queued
closure. A paused session therefore holds a bounded amount of pending work.
A closure that raises would end `run()`, so the apply step contains its own
failures.

A param value is parsed by the running pattern's `ParamSet` on the caller's
thread, so each kind (float, int, bool, choice, color, palette) refuses and
coerces its own values, and set on the loop thread. A pattern change starts
the new pattern fresh, at its defaults, as the preview's pick does
(`pewpew.aura.deck.Deck.put`): the loop's source is a `Crossfader`, cut to
a renderer spawned on the same geometry and engine time. A bind rebinds to the rig's
mapping with one unit per fixture, so a per-fixture pattern lights each bar
as one.

Each frame passes the bound rig's `PowerLimiter` before it is quantized, so
the stream carries the capped light (architecture §2 stage 3). A session has
no master dimmer, so the limiter is its only stage.

The text messages are the preview's own wire text (`pewpew.sinks.preview.message`
and `refusal`).

The session never touches asyncio. It reports through a `SessionSink`, whose
methods run on the loop thread and must not block.
"""

from __future__ import annotations

import logging
import struct
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from pewpew.crossfade import Crossfader
from pewpew.load import gallery
from pewpew.mapping import Grouping, line
from pewpew.pace import PacedLoop
from pewpew.params import ParamSet
from pewpew.power import PowerLimiter
from pewpew.render import Renderer
from pewpew.sinks.base import to_display_u8
from pewpew.sinks.preview import message, refusal, status_state

logger = logging.getLogger(__name__)

FPS = 30.0
POWER_HZ = 2.0
DEFAULT_PATTERNS = ("rainbow", "plasma")


def default_pattern(available: dict[str, type]) -> str:
    for name in DEFAULT_PATTERNS:
        if name in available:
            return name
    return min(available)


@dataclass(frozen=True)
class Echo:
    """The wire text of the `declare` and `params` messages for one moment."""

    declare: str
    params: str


def _echo(declared: list[dict], values: dict) -> Echo:
    return Echo(message("declare", declared), message("params", values))


@dataclass(frozen=True)
class FramePayload:
    """One frame plus the absolute state beside it, as in the preview sink:
    whichever payload survives the one-slot mailbox holds the latest truth.
    `status` is the `status` message's wire text."""

    data: bytes
    status: str
    echo: Echo


@dataclass(frozen=True)
class _Bind:
    mapping: np.ndarray
    grouping: Grouping | None
    catalog_digest: str
    issues: list
    limiter: PowerLimiter | None


class SessionSink(Protocol):
    def frame(self, payload: FramePayload) -> None: ...

    def control(self, message: dict, seen: Echo | None = None) -> None:
        """A discrete text message. `seen` accompanies a `hello`: the echo
        it already carries, so the transport can skip repeating it."""
        ...

    def power(self, watts: float, uncapped_watts: float) -> None:
        """The estimated draw of the streamed frame, and of the same frame without the cap."""
        ...

    def closed(self) -> None:
        """The loop thread died; the session cannot continue."""
        ...


class Session:
    def __init__(
        self,
        sink: SessionSink,
        *,
        pattern: str | None = None,
        fps: float = FPS,
        mapping: np.ndarray | None = None,
    ) -> None:
        self._patterns = gallery()
        self._sink = sink
        self._fps = fps
        name = pattern or default_pattern(self._patterns)
        self._pattern_name = name
        # The bound geometry, kept for a rebind that has to be undone.
        self._mapping = line(64) if mapping is None else mapping
        self._grouping: Grouping | None = None
        self._fader: Crossfader[Renderer] = Crossfader(Renderer(self._patterns[name](), self._mapping))
        self._loop = PacedLoop(self._fader, fps=fps, on_frame=[self._on_frame])
        self._seq = 0
        self._limiter: PowerLimiter | None = None
        self._logged: set[type] = set()
        self._power_every = max(1, round(fps / POWER_HZ))
        self._lock = threading.Lock()
        self._next_bind: _Bind | None = None
        self._next_pattern: str | None = None
        # Each value with the ParamSet it was parsed against.
        self._next_sets: dict[str, tuple[ParamSet, object]] = {}
        self._apply_queued = False
        self._paused_since: float | None = None
        self._want_run = threading.Event()
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="pewpew-session", daemon=True)

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._want_run.set()
        self._thread.start()

    def pause(self) -> None:
        """Stop rendering until `resume`; engine time is kept."""
        if self._paused_since is None:
            self._paused_since = time.monotonic()
        self._want_run.clear()
        self._loop.stop()

    def resume(self) -> None:
        self._paused_since = None
        self._want_run.set()

    @property
    def paused(self) -> bool:
        return not self._want_run.is_set()

    @property
    def paused_since(self) -> float | None:
        """`time.monotonic()` at the start of the current pause, or None.

        Lifecycle only: rendering never reads it."""
        return self._paused_since

    def close(self, join: bool = False, timeout: float = 2.0) -> None:
        self._closed.set()
        self._want_run.set()
        self._loop.stop()
        if join and self._thread.is_alive():
            self._thread.join(timeout)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        try:
            while not self._closed.is_set():
                self._want_run.wait()
                if self._closed.is_set():
                    break
                self._loop.run()
        except Exception:
            logger.exception("session loop ended")
        finally:
            if not self._closed.is_set():
                self._sink.closed()

    # -- messages out ------------------------------------------------------

    def hello(self) -> tuple[dict, Echo]:
        """The `hello` message, with the running pattern's declarations
        (`spec()` each) and values (`snapshot_json()`), and its echo."""
        params = self._fader.current.params
        declared, values = params.describe(), params.snapshot_json()
        return {
            "type": "hello",
            "n": self._fader.current.n,
            "fps": self._fps,
            "patterns": sorted(self._patterns),
            "pattern": self._pattern_name,
            "params": declared,
            "values": values,
        }, _echo(declared, values)

    def echo(self) -> Echo:
        """The current `declare` and `params` wire text."""
        params = self._fader.current.params
        return _echo(params.describe(), params.snapshot_json())

    def status(self) -> str:
        """The current `status` wire text: the render error and the address
        of the part that raised, or none."""
        error = self._fader.error
        return message("status", status_state(None if error is None else ("render", str(error), error.path)))

    def _send_hello(self) -> None:
        hello, seen = self.hello()
        self._sink.control(hello, seen)

    def _on_frame(self, t: float, frame: np.ndarray) -> None:
        """Loop thread. Must not raise or block.

        A frame that fails is dropped and the limiter stays bound, so a
        failure never streams uncapped light. An uncapped limiter runs only
        when a power reading is due.
        """
        try:
            seq = (self._seq + 1) & 0xFFFFFFFF
            due = seq % self._power_every == 0
            limiter = self._limiter
            limited = None
            if limiter is not None and (limiter.cap.caps or due):
                limited = limiter(frame)
                frame = limited.frame
            self._seq = seq
            data = struct.pack("<fI", t, self._seq) + to_display_u8(frame).tobytes()
            self._sink.frame(FramePayload(data, self.status(), self.echo()))
            if due and limited is not None and limited.watts is not None and limited.uncapped_watts is not None:
                self._sink.power(limited.watts, limited.uncapped_watts)
        except Exception as exc:
            if type(exc) not in self._logged:  # the first of each kind; one per frame would flood
                self._logged.add(type(exc))
                logger.exception("dropped a frame")

    # -- messages in (any thread) -------------------------------------------

    def set(self, name: object, value: object) -> str | None:
        """Ask for a param change, native or JSON. Returns the refusal
        reason, or None.

        The param's kind parses the value here, on the caller's thread. A
        later set of the same param replaces a pending one."""
        if not isinstance(name, str):
            return f"set takes a param name, got {name!r}"
        params = self._fader.current.params
        parsed, reason = params.parse(name, value)
        if reason is not None:
            return reason  # network-safe wording; `hint` names a file, so it stays out
        with self._pending():
            self._next_sets[name] = (params, parsed)
        return None

    def pattern(self, name: object) -> str | None:
        """Ask for a gallery pattern, fresh at its defaults. Returns the
        refusal reason, or None.

        Pending sets are dropped: they were checked against the pattern that
        the new one replaces."""
        key = name.lower() if isinstance(name, str) else None
        if key not in self._patterns:
            return f"unknown pattern; available: {', '.join(sorted(self._patterns))}"
        with self._pending():
            self._next_pattern = key
            self._next_sets.clear()
        return None

    def bind(
        self,
        mapping: np.ndarray,
        *,
        grouping: Grouping | None = None,
        catalog_digest: str,
        issues: list,
        limiter: PowerLimiter | None,
    ) -> None:
        """Ask for a rebind to a compiled rig's mapping and its fixture
        grouping; engine time continues.

        `limiter` caps the rig's frames and estimates their power; None
        streams them uncapped with no power messages. A later bind replaces
        a pending one."""
        with self._pending():
            self._next_bind = _Bind(mapping, grouping, catalog_digest, issues, limiter)

    @contextmanager
    def _pending(self) -> Iterator[None]:
        """Change the pending slots under the lock, then queue the apply
        closure unless one is already queued."""
        with self._lock:
            yield
            queue = not self._apply_queued
            self._apply_queued = True
        if queue:
            self._loop.calls.call_soon(self._apply_pending)

    # -- the apply step (loop thread) ----------------------------------------

    def _apply_pending(self) -> None:
        with self._lock:
            bind, pattern, sets = self._next_bind, self._next_pattern, self._next_sets
            self._next_bind, self._next_pattern, self._next_sets = None, None, {}
            self._apply_queued = False
        changed = False
        if bind is not None:
            changed |= self._apply_bind(bind)
        if pattern is not None:
            changed |= self._apply_pattern(pattern)
        for name, (params, value) in sets.items():
            self._apply_set(params, name, value)
        if changed:
            self._send_hello()

    def _apply_set(self, params: ParamSet, name: str, value: object) -> None:
        """Set a value that passed `parse` against `params` on another
        thread. Never raises: a pattern change in between runs other params
        by now, and that must not end the session, so the set is dropped."""
        if params is not self._fader.current.params:
            logger.warning("dropped a live set of %r: the pattern it was for no longer runs", name)
            return
        try:
            params.set(name, value)
        except ValueError:
            logger.warning("dropped a live set of %r to %r: the param no longer accepts it", name, value)

    def _apply_bind(self, bind: _Bind) -> bool:
        try:
            self._fader.rebind(bind.mapping, bind.grouping)
        except Exception:
            logger.exception("rebind failed")
            self._fader.rebind(self._mapping, self._grouping)  # if this raises too, the loop ends
            self._refuse("bind", "the pattern could not start on this arrangement")
            return False
        self._mapping, self._grouping = bind.mapping, bind.grouping
        self._limiter = bind.limiter
        self._sink.control(
            {"type": "bound", "n": self._fader.current.n, "catalog_digest": bind.catalog_digest, "issues": bind.issues}
        )
        return True

    def _apply_pattern(self, key: str) -> bool:
        try:
            self._fader.cut(self._fader.current.spawn(self._patterns[key]()))
        except Exception:
            logger.exception("pattern %s failed to start", key)
            self._refuse("pattern", "that pattern could not start on this arrangement")
            return False
        self._pattern_name = key
        return True

    def _refuse(self, name: str, reason: str) -> None:
        self._sink.control(refusal(name, reason))

    @property
    def renderer(self) -> Renderer:
        """The running renderer. The loop thread owns it: read it from
        another thread, never change it."""
        return self._fader.current

    @property
    def n(self) -> int:
        return self._fader.current.n

    @property
    def t(self) -> float:
        return self._fader.current.t


class SessionRegistry:
    """Live sessions, so shutdown can stop every loop thread and a full
    server can evict the session paused longest."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[Session, tuple[Any, Callable[[], None]]] = {}

    def add(self, session: Session, ticket: Any, evict: Callable[[], None]) -> None:
        """Register `session`. `evict` must close it without blocking;
        `ticket` is its admission slot, which an eviction hands back."""
        with self._lock:
            self._sessions[session] = (ticket, evict)

    def discard(self, session: Session) -> None:
        with self._lock:
            self._sessions.pop(session, None)

    def evict_longest_paused(self) -> Any | None:
        """Close the session paused longest. Returns its ticket, or None when
        no session is paused."""
        with self._lock:
            paused = [s for s in self._sessions if s.paused_since is not None]
            if not paused:
                return None
            victim = min(paused, key=lambda s: s.paused_since)  # type: ignore[arg-type, return-value]
            ticket, evict = self._sessions.pop(victim)
        evict()
        return ticket

    def sessions(self) -> list[Session]:
        with self._lock:
            return list(self._sessions)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def close_all(self, timeout: float = 5.0) -> None:
        """Stop every loop, then join each thread within a shared deadline."""
        with self._lock:
            sessions = list(self._sessions)
        for s in sessions:
            s.close()
        deadline = time.monotonic() + timeout
        for s in sessions:
            s.close(join=True, timeout=max(0.0, deadline - time.monotonic()))
        with self._lock:
            for s in sessions:
                self._sessions.pop(s, None)
