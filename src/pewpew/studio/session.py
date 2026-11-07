"""One visitor's aura: the aura pipeline under a `PacedLoop` on its own thread.

A session builds what `python -m pewpew run` builds (ADR-025,
`pewpew.aura.pipeline`), with no looks file and no boards, and it takes
whole looks (`accept_looks`), and makes at most one look at a time for a
`surprise` or `vary`. It starts in the first of the looks it is given
(the studio gives the example looks, `START` first). Every request a
visitor sends goes to the pipeline's `AuraControl`, which refuses what
needs a looks file or boards; the session adds only `bind`, `pause` and
`resume`.

A bind is coalesced, not queued: one slot, applied by at most one queued
closure on the loop thread, so a paused session holds a bounded amount of
pending work. It rebinds the crossfader to the rig's mapping; engine time
continues. When the running look cannot run on the
new mapping (a strip under a look that folds a plane), the session cuts
to the first of its looks that can, and the `status` message says so
until another look runs; when none can, the bind is refused and the old
mapping stays.

Each frame passes the master, then the bound rig's `PowerLimiter`, an
`after` stage, before it is quantized, so the stream carries the capped
light (architecture §2 stage 3). Beside each frame go the current text of
every per-frame message the preview sends (`pewpew.sinks.preview.StateTexts`):
the status, the knobs, their values, the driven knobs' live values, the
aura state and the catalog. The `mod` values are read at most
`MOD_HZ` times a second of engine time.

The session never touches asyncio. It reports through a `SessionSink`,
whose methods run on the loop thread (or, for an answer, the thread that
asked) and must not block.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from pewpew.aura.book import VERSION, parse_looks
from pewpew.aura.control import AuraControl
from pewpew.aura.pipeline import build_aura_pipeline
from pewpew.compose import Look
from pewpew.mapping import grid
from pewpew.power import PowerLimiter
from pewpew.sinks.base import to_display_u8
from pewpew.sinks.preview import FRAME_HEADER, StateTexts, refusal

logger = logging.getLogger(__name__)

FPS = 30.0
POWER_HZ = 2.0
START = "tide"  # the example look every session starts in


def example_looks(folder: Path) -> dict[str, dict]:
    """The current look of each example looks file in `folder`
    (`*.look.json`), in the looks file's form, by the file's name."""
    looks = {}
    for path in sorted(folder.glob("*.look.json")):
        data = json.loads(path.read_bytes())
        looks[path.name.removesuffix(".look.json")] = data["looks"][data["current"]]
    return looks


def as_look(doc: dict) -> Look:
    """`doc`, one look in the looks file's form, as a `Look`. Raises
    LookError for a look the looks file's loader refuses."""
    return parse_looks(json.dumps({"version": VERSION, "looks": {"look": doc}})).looks["look"]


@dataclass(frozen=True)
class FramePayload:
    """One frame plus the absolute state beside it, as in the preview sink:
    whichever payload survives the one-slot mailbox holds the latest truth.
    `texts` is the current text of each per-frame message, in the
    preview's order (`StateTexts`)."""

    data: bytes
    texts: tuple[str | None, ...]


@dataclass(frozen=True)
class _Bind:
    mapping: np.ndarray
    catalog_digest: str
    issues: list
    limiter: PowerLimiter | None


class SessionSink(Protocol):
    def frame(self, payload: FramePayload) -> None: ...

    def hello(self, message: dict) -> None:
        """The `hello` message: every per-frame message follows it again."""
        ...

    def control(self, message: dict) -> None:
        """A discrete text message."""
        ...

    def power(self, watts: float, uncapped_watts: float) -> None:
        """The estimated draw of the streamed frame, and of the same frame without the cap."""
        ...

    def closed(self) -> None:
        """The loop thread died; the session cannot continue."""
        ...


class Session:
    def __init__(
        self, sink: SessionSink, looks: Mapping[str, Look], *, fps: float = FPS, mapping: np.ndarray | None = None,
        seed: int = 0,
    ) -> None:
        """A session that starts in the first of `looks` on `mapping`
        (default a 16 x 16 grid, which every example look renders on), its
        made looks seeded from `seed`; a bind falls back on `looks` in
        order. Raises as `Compositor` does for a look it cannot start."""
        self._looks = looks
        look = next(iter(looks.values()))
        self._aura = build_aura_pipeline(
            look, grid(16, 16) if mapping is None else mapping, seed=seed, accept_looks=True, max_making=1,
        )
        # The stack a bind cut to, and why, while it runs: the `status` says so.
        self._fallback: tuple[object, str] | None = None
        self._sink = sink
        self._fps = fps
        self._texts = StateTexts(self._aura.control, now=lambda: self._aura.fader.t)
        self._loop = self._aura.loop(fps, after=[self._limit], on_frame=[self._on_frame])
        self._seq = 0
        self._limiter: PowerLimiter | None = None
        # The power reading of the frame `_limit` capped last, when one was due.
        self._reading: tuple[float, float] | None = None
        self._logged: set[type] = set()
        self._power_every = max(1, round(fps / POWER_HZ))
        self._lock = threading.Lock()
        self._next_bind: _Bind | None = None
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

    def hello(self) -> dict[str, Any]:
        """The `hello` message: the pixel count, the frame rate and what a
        client may rely on (the preview's `capabilities`)."""
        return {"type": "hello", "n": self.n, "fps": self._fps,
                "capabilities": ["ack", *self._aura.control.capabilities]}

    def _status(self) -> tuple[str, str, str | None] | None:
        """The render error and the address of the part that raised, else
        the look a bind cut to while it runs, or None."""
        error = self._aura.fader.error
        if error is not None:
            return "render", str(error), error.path
        fallback = self._fallback
        if fallback is not None and fallback[0] is self._aura.fader.current:
            return "bind", fallback[1], None
        return None

    def _limit(self, t: float, frame: np.ndarray) -> np.ndarray:
        """The `after` stage behind the master: the frame under the bound
        rig's cap, keeping the power reading when one is due. An uncapped
        limiter runs only then. Never raises: a frame the limiter refuses
        goes out black, never uncapped."""
        self._reading = None
        limiter = self._limiter
        due = (self._seq + 1) % self._power_every == 0
        if limiter is None or not (limiter.cap.caps or due):
            return frame
        try:
            limited = limiter(frame)
        except Exception as exc:
            if self._first(exc):
                logger.exception("the power limit refused a frame; it goes out black")
            return np.zeros(frame.shape, dtype=np.float32)
        if due and limited.watts is not None and limited.uncapped_watts is not None:
            self._reading = (limited.watts, limited.uncapped_watts)
        return limited.frame

    def _on_frame(self, t: float, frame: np.ndarray) -> None:
        """Loop thread. Must not raise or block: a frame that fails is
        dropped."""
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        try:
            data = FRAME_HEADER.pack(t, self._seq) + to_display_u8(frame).tobytes()
            self._sink.frame(FramePayload(data, self._texts(self._status())))
            if self._reading is not None:
                self._sink.power(*self._reading)
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
        """The aura's controls: every request but `bind`, `pause` and
        `resume` goes here. Its requests may block until the loop thread
        answers, so call them off the event loop."""
        return self._aura.control

    def bind(
        self,
        mapping: np.ndarray,
        *,
        catalog_digest: str,
        issues: list,
        limiter: PowerLimiter | None,
    ) -> None:
        """Ask for a rebind to a compiled rig's mapping; engine time
        continues.

        `limiter` caps the rig's frames and estimates their power; None
        streams them uncapped with no power messages. A later bind replaces
        a pending one."""
        with self._lock:
            queue = self._next_bind is None
            self._next_bind = _Bind(mapping, catalog_digest, issues, limiter)
        if queue:
            self._aura.calls.call_soon(self._apply_bind)

    def _apply_bind(self) -> None:
        """Loop thread. A bind the look cannot run on is refused, and the
        old mapping stays bound."""
        with self._lock:
            bind, self._next_bind = self._next_bind, None
        if bind is None:
            return
        fader = self._aura.fader
        old = fader.current.mapping
        try:
            fader.rebind(bind.mapping)
        except Exception as exc:
            # The stack keeps the new mapping, so a look recalled now starts on it.
            name = self._cut_to_one_that_runs()
            if name is None:
                logger.warning("no look runs on the arrangement", exc_info=True)
                fader.rebind(old)  # if this raises too, the loop ends
                self._sink.control(refusal("bind", "no look could start on this arrangement"))
                return
            self._fallback = (fader.current, f"the look could not run on this arrangement ({exc}), so {name} runs")
        self._limiter = bind.limiter
        self._sink.control({"type": "bound", "n": self.n, "catalog_digest": bind.catalog_digest,
                            "issues": bind.issues})
        self._sink.hello(self.hello())

    def _cut_to_one_that_runs(self) -> str | None:
        """Cut to the first of the session's looks that starts on the
        running stack's mapping, at its master. Returns its name, or None
        when none starts. Loop thread."""
        for name, look in self._looks.items():
            if self._aura.deck.recall(look) is None:
                if look.master is not None:
                    self._aura.master.set(look.master)
                return name
        return None

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
