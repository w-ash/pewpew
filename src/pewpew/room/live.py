"""The rig file while the aura runs: a save reloads it, the page's "use
for A" rewrites one controller's host in the file, and the page's layout
edit writes a whole new arrangement to it.

`_commit` is the one apply step, on the loop thread, for a reload and for
a layout edit. It checks everything that can fail before it changes
anything: the rig may stream (`pewpew.rig.runtime.stream_refusals`), the
DDP sink accepts the new boards, and the audit record of a changed board
set is written (no packet goes to a target without one). Then the running
look, the DDP sink and the blink take the new rig; if any of them raises
(a program's `setup` on the new geometry), each one that took it takes the
last good rig again and the step fails: the new rig never ran. Once all
three have it, the new rig runs and nothing puts the old one back: the
state and each listener take it, and a listener that raises leaves a
warning in `error` (`_commit`'s second value) while the new rig runs. A
reload (`apply`) first compiles the file; a room map file reloads too,
with its deprecation logged as a warning.

`rebind` runs on a connection thread: it rewrites the controller's host
(`pewpew.rig.runtime.rebind_host`) atomically, then queues a reload, where
`_commit` audits the new board set as a relayout before any frame goes
there. It works in an `--unattended` run too, audited the same way.

`arrange` runs on a connection thread and answers only once the edit is
live or refused. It takes the arrangement and its `base`: the digest of
the file the page edited (`arrangement`). Under one lock, in this order,
it refuses a stale `base` or a file that changed on disk since it last
loaded, compiles the arrangement once, checks that the boards can take
it, writes the file atomically, adopts the new digest in the reloader (so
the watcher's event for the write applies nothing), writes an `arrange`
audit record when the run streams DDP, then waits for `_commit` on the
loop thread. A refusal at any step after the write puts the old bytes
back atomically and adopts their digest again, so the file, the running
rig and the page agree: the edit did not happen. Once the new rig runs,
the edit is answered as done even when a listener failed (the warning is
the status line's), since the file and the engine both hold it. A refusal
for a stale `base` or a changed file carries the engine's current
`arrangement` state, so the page shows it without waiting for the next
broadcast. It is off unless the run allows edits (`edits`; an unattended
run does not).

Both rewrites are refused on a room map file, and every refusal names no
path. `arrangement` and `report` are what the page draws of the file and
of the running rig. A file's digest is the sha256 of its bytes; a reload,
a rebind and an arrange each change it, so an arrange built on an older
file is refused.

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
from pewpew.errors import Refusal, describe_exception, scrub
from pewpew.jsonfile import write_atomic
from pewpew.pace import Calls
from pewpew.reload import FileReloader, Watch
from pewpew.render import Live
from pewpew.room.blink import Blink
from pewpew.sinks.ddp import Board, DdpSink, Layout

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

logger = logging.getLogger(__name__)

NO_EDITS = "layout edits are off in an unattended run"
NOT_AN_OBJECT = "an arrangement is a JSON object"
NO_BASE = "an arrange names the layout it edits: `base`, from the engine's `arrangement`"
STALE = "the layout changed; showing the current one"
CHANGED_ON_DISK = "the map file changed since it last loaded, so it was not overwritten"
LATE = "the engine is busy, so the layout did not change; send it again"


class RigLive:
    """One rig file, its compiled rig, and its watch.

    With `follow`, the DDP sink streams to the rig's controllers and takes
    each reload's (`ddp_targets`); without it, the sink keeps its own
    boards (`run --ddp`). With `edits`, `arrange` may write the file.

    `doc` is the file's parsed JSON as the last reload or `arrange`
    applied it; None for a room map file.
    """

    def __init__(
        self,
        path: Path,
        rig: CompiledRig,
        data: bytes,
        live: Live,
        calls: Calls,
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
        # The digest of the bytes `doc` came from.
        self._digest = hashlib.sha256(data).hexdigest()
        # Called with each new rig once it is live, on the loop thread.
        self.listeners: list[Callable[[CompiledRig], None]] = []
        self._live = live
        self._calls = calls
        self._ddp = ddp
        self._follow = follow
        self._edits = edits
        self._targets: tuple[tuple[str, ...], tuple[Board, ...]] = ((), ())
        self._report: dict[str, Any] = {}
        self._arrangement: dict[str, Any] = {}
        # What failed after the last new rig ran (a listener), or None.
        self._warning: str | None = None
        self._take(*self._taking(rig))
        self._publish()
        self._argv = argv
        self._blink = blink
        self._lock = threading.Lock()
        self.reloader = FileReloader(self.path, self._digest, calls.call_soon, self.apply, noun="map", watch=watch)

    @property
    def error(self) -> str | None:
        """Why the last reload failed, or what failed once its rig ran, or
        None (a status line source)."""
        return self.reloader.error or self._warning

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

    def arrangement(self) -> dict[str, Any]:
        """`{"arrangement", "base"}`: the file's arrangement (`doc`) and the
        digest an `arrange` built on it names, both None while the file is
        not `editable`. The same object until it changes. Any thread."""
        return self._arrangement

    def _publish(self) -> None:
        """Make the `arrangement` state of `doc` and its digest."""
        editable = self.editable
        self._arrangement = {"arrangement": self.doc if editable else None,
                             "base": self._digest if editable else None}

    def report(self) -> dict[str, Any]:
        """The running rig's `issues` and electrical `report` as JSON
        (`CompiledRig.findings`). The same object until the rig changes.
        Any thread."""
        return self._report

    def _taking(self, rig: CompiledRig) -> tuple[CompiledRig, dict[str, Any], tuple | None]:
        """What `_take` holds of `rig`: it, its findings and, with `follow`,
        the names and boards it streams to. Changes nothing."""
        from pewpew.rig.runtime import ddp_targets, target_names

        return rig, rig.findings(), (target_names(rig), ddp_targets(rig)) if self._follow else None

    def _take(self, rig: CompiledRig, report: dict[str, Any], targets: tuple | None) -> None:
        """Hold what `_taking` made of `rig`. Never raises."""
        self._report = report
        self.rig = rig
        if targets is not None:
            self._targets = targets

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
        summary, _warning = self._commit(rig, None if is_room(doc) else doc, hashlib.sha256(data).hexdigest())
        return summary

    def _commit(self, rig: CompiledRig, doc: Any, digest: str) -> tuple[str, str | None]:
        """Make `rig`, compiled from the file's `doc` whose bytes have
        `digest`, live (the module docstring). Loop thread only. Raises
        what a failed step raises, with no path in it, only when the old rig
        still runs; returns the summary and, when a listener failed once
        the new rig ran, the warning `error` then gives."""
        from pewpew.rig.runtime import fixture_spans

        old = self.rig
        boards, layout = self._boards(rig)
        taken = self._taking(rig)
        old_boards = tuple(self._ddp.boards) if self._ddp is not None else ()
        relaid = self._ddp is not None and boards != old_boards
        if relaid:
            assert self._ddp is not None
            audit.record(
                "ddp-relayout", argv=self._argv, targets=[b.spec for b in boards], fps=self._ddp.max_fps,
            )
        old_layout = self._ddp.layout if self._ddp is not None else None
        try:
            self._live.rebind(rig.mapping)
            if self._ddp is not None and layout is not None:
                self._ddp.commit(layout)
            if self._blink is not None:
                self._blink.rebind(fixture_spans(rig))
        except Exception as exc:
            # Each part takes the old rig again, last applied first, each in its own try, so one that
            # fails neither skips the others nor hides `exc`.
            for note in self._roll_back(old, old_layout, old_boards, relaid):
                exc.add_note(note)
            raise
        # The new rig runs: from here on, nothing puts the old one back.
        self._take(*taken)
        self.doc = doc
        self._digest = digest
        self._publish()
        failed: list[str] = []
        for listener in self.listeners:
            try:
                listener(rig)
            except Exception as exc:  # the rig runs; the warning says what did not follow it
                logger.warning("a part of the run did not take the new map", exc_info=True)
                failed.append(describe_exception(exc))
        self._warning = None if not failed else (
            f"the new map runs, but a part of the run did not take it: {'; '.join(failed)}"
        )
        summary = (
            f"map reloaded (t={self._live.t:.3f}): {rig.n} px in "
            f"{len(rig.fixtures)} fixtures on {len(rig.controllers)} controller(s)"
        )
        return summary, self._warning

    def _roll_back(
        self, old: CompiledRig, old_layout: Layout | None, old_boards: tuple[Board, ...], relaid: bool,
    ) -> list[str]:
        """Put the blink, the DDP sink and the renderer back on `old`, in
        that order; the note for each that failed, naming the rig it may
        still run. Loop thread only; never raises. The revert is audited
        before the sink takes the old layout, so before any frame can go to
        the old boards (the sink sends nothing itself)."""
        from pewpew.rig.runtime import fixture_spans

        notes: list[str] = []

        def attempt(part: str, new_rig: str, step: Callable[[], object]) -> None:
            try:
                step()
            except Exception as exc:
                logger.warning("rolling back %s failed", part, exc_info=True)
                notes.append(
                    f"rollback failed: {part} may still run {new_rig}" if new_rig != "no record"
                    else f"rollback failed: {part} is missing from the audit log"
                )
                notes[-1] += f" ({describe_exception(exc)})"

        if self._blink is not None:
            blink = self._blink
            attempt("the blink", "the new map", lambda: blink.rebind(fixture_spans(old)))
        if self._ddp is not None and old_layout is not None:
            ddp = self._ddp

            if relaid:
                attempt("the audit record of the revert", "no record", lambda: audit.record(
                    "ddp-relayout-reverted", argv=self._argv, targets=[b.spec for b in old_boards], fps=ddp.max_fps,
                ))
            attempt("the DDP sink", "the new boards", lambda: ddp.commit(old_layout))
        live = self._live
        attempt("the renderer", "the new map", lambda: live.rebind(old.mapping))
        return notes

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
        self._calls.call_soon(self.reloader.reload)
        return None

    def arrange(self, doc: object, base: object) -> Refusal | None:
        """Write the arrangement `doc`, built on the file whose digest is
        `base`, and make it live (the module docstring). Any thread but the
        loop's, which it waits for; returns a refusal that names no path, or
        None once the edit is live. After a refusal the file holds the bytes
        it held before."""
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
            if not isinstance(base, str):
                return Refusal(NO_BASE)
            if base != self._digest:
                return Refusal(STALE, current=self._arrangement)
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
            try:
                old = self.path.read_bytes()
            except OSError:
                return Refusal("could not read the map file")
            if hashlib.sha256(old).hexdigest() != base:
                return Refusal(CHANGED_ON_DISK, current=self._arrangement)
            try:
                write_atomic(self.path, data)  # a watcher and a reader never see half a file
            except OSError:
                return Refusal("could not write the map file")
            digest = hashlib.sha256(data).hexdigest()
            self.reloader.adopt(digest)  # the watcher's event for the write applies nothing
            if self._ddp is not None:
                try:
                    audit.record("arrange", argv=self._argv, map=str(self.path), pixels=rig.n,
                                 fixtures=len(rig.fixtures))
                except OSError:
                    return self._put_back(old, base, "could not write the audit log, so the map was not changed")
            reason = self._calls.ask(lambda: self._arranged(rig, doc, digest), LATE, definite=True)
            if reason is not None:
                return self._put_back(old, base, reason)
        logger.info("map file rewritten from the page: %d px in %d fixtures", rig.n, len(rig.fixtures))
        return None

    def _arranged(self, rig: CompiledRig, doc: Any, digest: str) -> str | None:
        """`_commit` an arrangement the page wrote; why it did not run, or
        None once it runs, even with a warning. Loop thread only; never
        raises."""
        try:
            summary, _warning = self._commit(rig, doc, digest)
        except Exception as exc:  # a raising setup, a sink that cannot take the layout, ...
            logger.warning("the layout from the page did not run", exc_info=True)
            return f"the layout did not run, so the map was not changed: {describe_exception(exc)}"
        self.reloader.error = None
        logger.info("%s", summary)
        return None

    def _put_back(self, old: bytes, digest: str, reason: str) -> Refusal:
        """Write `old`, the file's bytes before an arrange, back and adopt
        their `digest` again; the refusal for `reason`. Under the lock."""
        try:
            write_atomic(self.path, old)
        except OSError:
            self.reloader.error = "the map file holds a layout that did not run: undo the edit or save the file again"
            reason = f"{reason}; the map file could not be put back"
        self.reloader.adopt(digest)
        return Refusal(scrub(reason))


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
