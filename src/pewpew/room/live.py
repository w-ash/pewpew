"""The room map while the aura runs: a save reloads it, and the page's
"use for A" rewrites one board's host in the file.

`RoomLive.apply` is the reload's apply step, on the loop thread. It
checks everything that can fail before it changes anything: the map
compiles, the DDP sink accepts the new boards, and the audit record of a
changed board set is written (no packet goes to a target without one).
Then the running look is rebound; if a program's `setup` raises on the new
geometry, the last good geometry is bound again and the reload fails. Only
then do the sinks, the blink and each listener take the new map.

`rebind` runs on a connection thread: it rewrites the board's entry
(`pewpew.room.map.rebind_text`) atomically, then queues a reload, where
`apply` audits the new board set as a relayout before any frame goes
there. Refusals name no path.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path

from pewpew import audit
from pewpew.errors import scrub
from pewpew.jsonfile import write_atomic
from pewpew.reload import CallSoon, FileReloader, Watch
from pewpew.render import Live
from pewpew.room.blink import Blink
from pewpew.room.map import RoomError, RoomMap, parse_room, rebind_text
from pewpew.sinks.ddp import DdpSink

logger = logging.getLogger(__name__)


class RoomLive:
    """One room file, its compiled map, and its watch."""

    def __init__(
        self,
        path: Path,
        room: RoomMap,
        data: bytes,
        live: Live,
        call_soon: CallSoon,
        *,
        ddp: DdpSink | None,
        argv: list[str],
        blink: Blink | None = None,
        watch: Watch | None = None,
    ) -> None:
        self.path = Path(path)
        self.room = room
        # Called with each new map once it is live, on the loop thread.
        self.listeners: list[Callable[[RoomMap], None]] = []
        self._live = live
        self._call_soon = call_soon
        self._ddp = ddp
        self._argv = argv
        self._blink = blink
        self._lock = threading.Lock()
        self.reloader = FileReloader(
            self.path, hashlib.sha256(data).hexdigest(), call_soon, self.apply, noun="map", watch=watch,
        )

    @property
    def error(self) -> str | None:
        """Why the last reload failed, or None (a status line source)."""
        return self.reloader.error

    def start(self) -> None:
        self.reloader.start()

    def stop(self) -> None:
        self.reloader.stop()

    def board_names(self) -> tuple[str, ...]:
        """The room's board names, or none while a reload has given the
        sink boards the room does not have yet: a name must never label
        another board."""
        room = self.room
        return room.board_names if self._ddp is not None and room.boards == self._ddp.boards else ()

    def apply(self, data: bytes) -> str:
        """The reload's apply step (the module docstring). Loop thread only;
        raises what a failed step raises, with no path in it."""
        room = parse_room(data)
        old = self.room
        layout = None
        if self._ddp is not None:
            layout = self._ddp.prepare(room.boards, room.n)
            if room.boards != old.boards:
                audit.record(
                    "ddp-relayout", argv=self._argv, targets=[b.spec for b in room.boards], fps=self._ddp.max_fps,
                )
        try:
            self._live.rebind(room.mapping)
        except Exception:
            self._live.rebind(old.mapping)
            raise
        if self._ddp is not None and layout is not None:
            self._ddp.commit(layout)
        if self._blink is not None:
            self._blink.rebind(room)
        self.room = room
        for listener in self.listeners:
            listener(room)
        return (
            f"room map reloaded (t={self._live.t:.3f}): {room.n} px in "
            f"{len(room.fixtures)} fixtures on {len(room.boards)} board(s)"
        )

    def rebind(self, board: str, address: str) -> str | None:
        """Point room board `board` at `address` by rewriting its entry in
        the file, then reload it on the loop thread.
        Any thread; returns a refusal that names no path, or None."""
        with self._lock:
            try:
                data = self.path.read_bytes()
            except OSError:
                return "could not read the room file"
            try:
                new = rebind_text(data, board, address)
            except RoomError as exc:
                return scrub(str(exc))
            try:
                write_atomic(self.path, new)  # a watcher and a reader never see half a file
            except OSError:
                return "could not write the room file"
        logger.info("board %s: room file now gives %s", board, address)
        self._call_soon(self.reloader.reload)
        return None
