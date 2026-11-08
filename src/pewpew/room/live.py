"""The rig file while the aura runs: a save reloads it, the page's "use
for A" rewrites one controller's host in the file, and the page's layout
edit writes a whole new arrangement to it.

`_commit` is the one apply step, on the loop thread, for a reload and for
a layout edit. It checks everything that can fail before it changes
anything: the rig may stream (`pewpew.rig.runtime.stream_refusals`), the
DDP sink accepts the new boards, and the audit record of a changed board
set is written (no packet goes to a target without one). Then the running
look is rebound; if a program's `setup` raises on the new geometry, the
last good geometry is bound again and the step fails. Only then do the
sinks, the blink and each listener take the new rig. A reload (`apply`)
first compiles the file; a room map file reloads too, with its deprecation
logged as a warning.

`rebind` runs on a connection thread: it rewrites the controller's host
(`pewpew.rig.runtime.rebind_host`) atomically, then queues a reload, where
`_commit` audits the new board set as a relayout before any frame goes
there. It works in an `--unattended` run too, audited the same way.

`arrange` runs on a connection thread: it compiles the new arrangement
once, checks that the boards can take it, writes an `arrange` audit
record when the run streams DDP, writes the file atomically, then queues
`_commit` with the rig it compiled. The reloader adopts the new file's
digest before the write, so the watcher's event for it applies nothing.
It is off unless the run allows edits (`edits`; an unattended run does
not).

Both rewrites are refused on a room map file, and every refusal names no
path. `arrangement` and `report` are what the page draws of the file and
of the running rig.

The rig stack is imported only when a rig file is reloaded or rebound, so
a run on a synthetic map never loads it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pewpew import audit
from pewpew.errors import Refusal, scrub
from pewpew.jsonfile import write_atomic
from pewpew.reload import CallSoon, FileReloader, Watch
from pewpew.render import Live
from pewpew.room.blink import Blink
from pewpew.sinks.ddp import Board, DdpSink, Layout

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

logger = logging.getLogger(__name__)

NO_EDITS = "layout edits are off in an unattended run"
NOT_AN_OBJECT = "an arrangement is a JSON object"


class RigLive:
    """One rig file, its compiled rig, and its watch.

    With `follow`, the DDP sink streams to the rig's controllers and takes
    each reload's (`ddp_targets`); without it, the sink keeps its own
    boards (`run --ddp`). With `edits`, `arrange` may write the file.

    `doc` is the file's parsed JSON as the last reload applied it or
    `arrange` wrote it; None for a room map file.
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
        edits: bool = False,
    ) -> None:
        from pewpew.rig.room_import import is_room
        from pewpew.rig.runtime import read_doc

        self.path = Path(path)
        self.rig = rig
        doc = read_doc(data)
        self.doc: Any = None if is_room(doc) else doc
        # Called with each new rig once it is live, on the loop thread.
        self.listeners: list[Callable[[CompiledRig], None]] = []
        self._live = live
        self._call_soon = call_soon
        self._ddp = ddp
        self._follow = follow
        self._edits = edits
        self._targets: tuple[tuple[str, ...], tuple[Board, ...]] = ((), ())
        self._report: dict[str, Any] = {}
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

    @property
    def editable(self) -> bool:
        """Whether `arrange` may write the file: the run allows edits and
        the file is an arrangement."""
        return self._edits and self.doc is not None

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

    def arrangement(self) -> Any:
        """The file's arrangement (`doc`) while `editable`, else None. The
        same object until it changes. Any thread."""
        return self.doc if self.editable else None

    def report(self) -> dict[str, Any]:
        """The running rig's `issues` and electrical `report` as JSON
        (`CompiledRig.findings`). The same object until the rig changes.
        Any thread."""
        return self._report

    def _take(self, rig: CompiledRig) -> None:
        """Hold `rig`, its findings and, with `follow`, the names and boards it streams to."""
        from pewpew.rig.runtime import ddp_targets, target_names

        self._report = rig.findings()
        self.rig = rig
        if self._follow:
            self._targets = (target_names(rig), ddp_targets(rig))

    def _boards(self, rig: CompiledRig) -> tuple[tuple[Board, ...], Layout | None]:
        """The boards the DDP sink takes for `rig` and its checked layout,
        or no layout without a sink. Changes nothing; raises ValueError
        when the boards cannot take `rig`."""
        from pewpew.rig.runtime import ddp_targets, stream_refusals

        if self._ddp is None:
            return (), None
        if self._follow:
            if reasons := stream_refusals(rig):
                raise ValueError("the boards cannot take this map: " + "; ".join(reasons))
            boards = ddp_targets(rig)
        else:
            boards = tuple(self._ddp.boards)
        return boards, self._ddp.prepare(boards, rig.n)

    def apply(self, data: bytes) -> str:
        """The reload's apply step: compile the file's bytes, then
        `_commit` them. Loop thread only; raises what a failed step raises,
        with no path in it."""
        from pewpew.rig.room_import import is_room
        from pewpew.rig.runtime import read_doc, rig_of

        notices: list[str] = []
        doc = read_doc(data)
        rig = rig_of(doc, notices=notices)
        for notice in notices:
            logger.warning("%s", notice)
        return self._commit(rig, None if is_room(doc) else doc)

    def _commit(self, rig: CompiledRig, doc: Any) -> str:
        """Make `rig`, compiled from the file's `doc`, live (the module
        docstring). Loop thread only; raises what a failed step raises,
        with no path in it."""
        from pewpew.rig.runtime import fixture_spans

        old = self.rig
        boards, layout = self._boards(rig)
        if self._ddp is not None and boards != tuple(self._ddp.boards):
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
        self.doc = doc
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

    def arrange(self, doc: object) -> Refusal | None:
        """Write the arrangement `doc` to the file and make it live on the
        loop thread (the module docstring). Any thread; returns a refusal
        that names no path, or None. A refusal writes nothing."""
        from pewpew.rig import RigError, load_catalog
        from pewpew.rig.models import Issue
        from pewpew.rig.runtime import ROOM_REWRITE, compile_doc

        with self._lock:
            if not self._edits:
                return Refusal(NO_EDITS)
            if self.doc is None:
                return Refusal(ROOM_REWRITE)
            if not isinstance(doc, dict):
                return Refusal(NOT_AN_OBJECT)  # only a dict reaches the compiler: a string is never a path
            try:
                rig = compile_doc(doc, load_catalog())
            except (ValueError, OverflowError) as exc:  # RigError and ValidationError are ValueErrors
                issues = exc.issues if isinstance(exc, RigError) else ()
                return _refused(issues or (Issue.error("invalid", _unreadable(exc)),))
            try:
                self._boards(rig)
            except ValueError as exc:
                return Refusal(scrub(str(exc)), issues=tuple(i.model_dump(mode="json") for i in rig.issues))
            try:
                data = (json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
            except (TypeError, ValueError):
                return Refusal("the arrangement is not plain JSON")
            if self._ddp is not None:
                try:
                    audit.record("arrange", argv=self._argv, map=str(self.path), pixels=rig.n,
                                 fixtures=len(rig.fixtures))
                except OSError:
                    return Refusal("could not write the audit log, so the map was not changed")
            # Before the write, so the watcher's event for it applies nothing.
            self.reloader.adopt(hashlib.sha256(data).hexdigest())
            try:
                write_atomic(self.path, data)  # a watcher and a reader never see half a file
            except OSError:
                return Refusal("could not write the map file")
            self.doc = doc
            # Under the lock, so the commits run in the order of the writes.
            self._call_soon(lambda: self.reloader.run(lambda: self._commit(rig, doc)))
        logger.info("map file rewritten from the page: %d px in %d fixtures", rig.n, len(rig.fixtures))
        return None


def _refused(issues: tuple[Any, ...]) -> Refusal:
    """The refusal of an arrangement whose compile found `issues`: its
    reason the first error, and every issue as JSON."""
    first = next((i for i in issues if i.level == "error"), issues[0])
    where = f"{first.ref}: " if first.ref else ""
    return Refusal(
        scrub(f"the arrangement does not compile: {where}{first.message}"),
        issues=tuple(i.model_dump(mode="json") for i in issues),
    )


def _unreadable(exc: BaseException) -> str:
    """What a compile error without issues says, with no path."""
    if isinstance(exc, OverflowError):
        return "a number in the JSON is too large"
    return scrub(str(exc))[:300] or "invalid arrangement"
