"""One Gallery visitor's aura: the aura pipeline under a `PacedLoop` on its own thread.

A session builds what `python -m pewpew run` builds (ADR-025,
`pewpew.aura.pipeline`) on one share (`Shared`): its compiled rig's
mapping and power limit, and its looks book, kept in memory (`Looks` with
no file) and held to `max_book_bytes`, so a save, a rename or a favorite
lasts for the visit and an `export` hands back a looks file. The idle cycle
is off (`idle` null): a visit plays what the visitor picks. It has no boards and no rig file, takes
whole looks (`accept_looks`), and makes at most one look at a time for a
`surprise` or a `vary`. It starts in the book's current look, else in the
first that starts on the mapping; with none, it is refused (`NoLook`).
Every request a visitor sends goes to the pipeline's `AuraControl`, which
refuses what needs boards or a rig file; the session adds only `pause`
and `resume`.

Each frame passes the master, then the rig's `PowerLimiter` (a
`pewpew.power.PowerMeter`, an `after` stage), before it is quantized, so
the stream carries the capped light (architecture §2 stage 3). Beside each
frame go the current text of every per-frame message the preview sends
(`pewpew.sinks.preview.StateTexts`): the status, the knobs, their values,
the driven knobs' live values, the aura state with the looks, the catalog
and the `power` reading. The `mod` values are read at most `MOD_HZ` times
a second of engine time. The session speaks the engine's wire: its `View`
(`pewpew.sinks.preview`) gives the `hello`, with the rig's flat drawing
(`room`) and 3D view (`rig`), the packaged page's build stamp and the
capabilities `ack`, the control's own (`look`, `export`), `pause` and
`gallery`; `pack_frame` gives the frames.

The session never touches asyncio. It reports through a `SessionSink`,
whose methods run on the loop thread (or, for an answer, the thread that
asked) and must not block.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol

import numpy as np

from pewpew.aura.book import LookBook
from pewpew.aura.control import AuraControl
from pewpew.aura.pipeline import AuraPipeline, build_aura_pipeline
from pewpew.compose import LayerError
from pewpew.power import PowerLimiter, PowerMeter
from pewpew.sinks.preview import StateTexts, View, pack_frame, page_build
from pewpew.studio.limits import MAX_BODY_BYTES, MAX_PIXELS

logger = logging.getLogger(__name__)

FPS = 30.0
GALLERY_CAPABILITIES = ("pause", "gallery")  # what a Gallery session adds to the control's


class NoLook(Exception):
    """No look of the share's book starts on its layout."""


@dataclass(frozen=True, eq=False)
class Shared:
    """A share compiled once, which every session on it reads: the rig's
    `mapping`, its flat drawing `room` (`plan_view`) and 3D view `rig`
    (`rig_view`), a `limiter` factory for its power limit (None: uncapped,
    with no power reading) and the looks `book`."""

    mapping: np.ndarray
    room: dict[str, Any] | None
    rig: dict[str, Any] | None
    limiter: Callable[[], PowerLimiter] | None
    book: LookBook


@dataclass(frozen=True)
class FramePayload:
    """One frame plus the absolute state beside it, as in the preview sink:
    whichever payload survives the one-slot mailbox holds the latest truth.
    `texts` is the current text of each per-frame message, in the
    preview's order (`StateTexts`)."""

    data: bytes
    texts: tuple[str | None, ...]


class SessionSink(Protocol):
    def frame(self, payload: FramePayload) -> None: ...

    def control(self, message: dict | str) -> None:
        """A discrete text message: a dict to serialize, or its text."""
        ...

    def closed(self) -> None:
        """The loop thread died; the session cannot continue."""
        ...


def _start(shared: Shared, **kw: Any) -> AuraPipeline:
    """The aura of `shared` in the book's current look, else the first
    that starts on the mapping, with the idle cycle off. Raises NoLook
    when none starts."""
    book = replace(shared.book, cycle=replace(shared.book.cycle, idle=None))
    names = [*([book.current] if book.current is not None else []), *(n for n in book.looks if n != book.current)]
    for name in names:
        try:
            aura = build_aura_pipeline(book.looks[name], shared.mapping, book=book, **kw)
        except (LayerError, ValueError):  # ValueError: a signal or route the stack cannot run
            logger.debug("look %r does not start on the share", name, exc_info=True)
            continue
        if name != book.current:
            assert aura.looks is not None
            aura.looks.leave()  # runs as a sent look does: no look is current
        return aura
    raise NoLook("no look of this share can start on its layout")


class Session:
    def __init__(
        self,
        sink: SessionSink,
        shared: Shared,
        *,
        fps: float = FPS,
        seed: int = 0,
        max_pixels: int = MAX_PIXELS,
        max_book_bytes: int = MAX_BODY_BYTES,
    ) -> None:
        """A session on `shared`, its made looks seeded from `seed`. A rig
        over `max_pixels` is decimated evenly in the stream, as in the
        preview; the book grows to `max_book_bytes` at most
        (`LookBook.size`). Raises NoLook when no look of the book starts."""
        self._aura = _start(shared, seed=seed, accept_looks=True, max_making=1, max_book_bytes=max_book_bytes)
        self._sink = sink
        self._texts = StateTexts(self._aura.control, now=lambda: self._aura.fader.t)
        self._view = View.of(
            shared.mapping, max_pixels, 0, room=shared.room, rig=shared.rig, build=page_build(),
            capabilities=("ack", *self._aura.control.capabilities, *GALLERY_CAPABILITIES),
        )
        # The rig's cap and its power reading: the `power` state.
        self._meter = PowerMeter(fps, shared.limiter() if shared.limiter is not None else None)
        self._loop = self._aura.loop(fps, after=[self._meter], on_frame=[self._on_frame])
        self._seq = 0
        self._logged: set[type] = set()
        self._paused_since: float | None = None
        self._want_run = threading.Event()
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="pewpew-session", daemon=True)

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._want_run.set()
        self._thread.start()

    def pause(self) -> None:
        """Stop rendering until `resume`; engine time is kept. A request
        that waits for the loop thread waits until it resumes, or is
        answered late."""
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
        """Stop the loop for good, and answer every request that waits for it."""
        self._closed.set()
        self._want_run.set()
        self._loop.stop()
        self._aura.calls.close()
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

    def hello(self) -> str:
        """The `hello` message text, as the preview sends it (the module docstring)."""
        return self._view.hello

    def _status(self) -> tuple[str, str, str | None] | None:
        """The render error and the address of the part that raised, else
        a failed look recall, or None."""
        error = self._aura.fader.error
        if error is not None:
            return "render", str(error), error.path
        looks = self._aura.looks
        failed = looks.error if looks is not None else None
        return ("looks", failed, None) if failed else None

    def _on_frame(self, t: float, frame: np.ndarray) -> None:
        """Loop thread. Must not raise or block: a frame that fails is
        dropped."""
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        try:
            view = self._view
            data = pack_frame(t, self._seq, frame if view.idx is None else frame[view.idx])
            self._sink.frame(FramePayload(data, self._texts(self._status(), self._meter.reading)))
        except Exception as exc:
            if self._first(exc):
                logger.exception("dropped a frame")

    def _first(self, exc: Exception) -> bool:
        """Whether `exc` is the first of its kind, the only one logged: one
        a frame would flood the log."""
        first = type(exc) not in self._logged
        self._logged.add(type(exc))
        return first

    # -- messages in (any thread) -------------------------------------------

    @property
    def control(self) -> AuraControl:
        """The aura's controls: every request but `pause` and `resume`
        goes here. Its requests may block until the loop thread answers,
        so call them off the event loop."""
        return self._aura.control

    @property
    def n(self) -> int:
        return len(self._aura.fader.current.mapping)

    @property
    def t(self) -> float:
        return self._aura.fader.t


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
