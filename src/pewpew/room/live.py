"""The rig file while the aura runs: a save reloads it, and the page's
"use for A" rewrites one controller's host in the file.

`RigLive.apply` is the reload's apply step, on the loop thread. It
checks everything that can fail before it changes anything: the file
compiles, the rig may stream (`pewpew.rig.runtime.stream_refusals`), the
DDP sink accepts the new boards, and the audit record of a changed board
set is written (no packet goes to a target without one). Then the running
look is rebound; if a program's `setup` raises on the new geometry, the
last good geometry is bound again and the reload fails. Only then do the
sinks, the blink and each listener take the new rig. A room map file
reloads too, with its deprecation logged as a warning.

`rebind` runs on a connection thread: it rewrites the controller's host
(`pewpew.rig.runtime.rebind_host`) atomically, then queues a reload, where
`apply` audits the new board set as a relayout before any frame goes
there. It works in an `--unattended` run too, audited the same way. It
is refused on a room map file. Refusals name no path.

The rig stack is imported only when a rig file is reloaded or rebound, so
a run on a synthetic map never loads it.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pewpew import audit
from pewpew.errors import scrub
from pewpew.jsonfile import write_atomic
from pewpew.reload import CallSoon, FileReloader, Watch
from pewpew.render import Live
from pewpew.room.blink import Blink
from pewpew.sinks.ddp import Board, DdpSink

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

logger = logging.getLogger(__name__)


class RigLive:
    """One rig file, its compiled rig, and its watch.

    With `follow`, the DDP sink streams to the rig's controllers and takes
    each reload's (`ddp_targets`); without it, the sink keeps its own
    boards (`run --ddp`).
    """

    def __init__(
        self,
        path: Path,
        rig: CompiledRig,
        data: bytes,
        live: Live,
        call_soon: CallSoon,
        *,
        ddp: DdpSink | None,
        argv: list[str],
        blink: Blink | None = None,
        watch: Watch | None = None,
        follow: bool = True,
    ) -> None:
        self.path = Path(path)
        self.rig = rig
        # Called with each new rig once it is live, on the loop thread.
        self.listeners: list[Callable[[CompiledRig], None]] = []
        self._live = live
        self._call_soon = call_soon
        self._ddp = ddp
        self._follow = follow
        self._targets: tuple[tuple[str, ...], tuple[Board, ...]] = ((), ())
        self._take(rig)
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
        """The controller id of each of the sink's boards, or none while
        the sink has other boards (`run --ddp`, or between a reload's checks
        and its commit): a name must never label another board."""
        names, boards = self._targets
        return names if self._ddp is not None and boards == tuple(self._ddp.boards) else ()

    def _take(self, rig: CompiledRig) -> None:
        """Hold `rig` and, with `follow`, the names and boards it streams to."""
        from pewpew.rig.runtime import ddp_targets, target_names

        self.rig = rig
        if self._follow:
            self._targets = (target_names(rig), ddp_targets(rig))

    def apply(self, data: bytes) -> str:
        """The reload's apply step (the module docstring). Loop thread only;
        raises what a failed step raises, with no path in it."""
        from pewpew.rig.runtime import ddp_targets, fixture_spans, parse_rig, stream_refusals

        notices: list[str] = []
        rig = parse_rig(data, notices=notices)
        for notice in notices:
            logger.warning("%s", notice)
        old = self.rig
        layout = None
        boards: tuple[Board, ...] = ()
        if self._ddp is not None:
            if self._follow:
                if reasons := stream_refusals(rig):
                    raise ValueError("the boards cannot take this map: " + "; ".join(reasons))
                boards = ddp_targets(rig)
            else:
                boards = tuple(self._ddp.boards)
            layout = self._ddp.prepare(boards, rig.n)
            if boards != tuple(self._ddp.boards):
                audit.record(
                    "ddp-relayout", argv=self._argv, targets=[b.spec for b in boards], fps=self._ddp.max_fps,
                )
        try:
            self._live.rebind(rig.mapping)
        except Exception:
            self._live.rebind(old.mapping)
            raise
        if self._ddp is not None and layout is not None:
            self._ddp.commit(layout)
        if self._blink is not None:
            self._blink.rebind(fixture_spans(rig))
        self._take(rig)
        for listener in self.listeners:
            listener(rig)
        return (
            f"map reloaded (t={self._live.t:.3f}): {rig.n} px in "
            f"{len(rig.fixtures)} fixtures on {len(rig.controllers)} controller(s)"
        )

    def rebind(self, controller: str, address: str) -> str | None:
        """Point controller `controller` at `address` by rewriting its host
        in the file, then reload it on the loop thread.
        Any thread; returns a refusal that names no path, or None."""
        from pewpew.rig import RigError
        from pewpew.rig.runtime import rebind_host

        with self._lock:
            try:
                data = self.path.read_bytes()
            except OSError:
                return "could not read the map file"
            try:
                new = rebind_host(data, controller, address)
            except RigError as exc:
                return scrub(str(exc))
            try:
                write_atomic(self.path, new)  # a watcher and a reader never see half a file
            except OSError:
                return "could not write the map file"
        logger.info("controller %s: map file now gives %s", controller, address)
        self._call_soon(self.reloader.reload)
        return None
