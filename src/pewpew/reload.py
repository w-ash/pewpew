"""Hot reload of a watched file: apply each saved version live.

`FileReloader` watches one file, skips unchanged bytes, applies new bytes
on the loop thread, and keeps the last good version on failure.
`pewpew.room.live` builds on it for a rig file (an arrangement `--map`),
whose apply step rebinds the renderer and relays out the sinks.

Threading. A daemon thread blocks in the watcher and hands every change
batch to the loop thread through `call_soon`. `reload()` runs on the loop
thread, so what it applies keeps one owner at the cost of one hitched
frame. `reload()` never raises (a queued closure that raises ends the run,
see `pewpew.pace.Calls`), and a dying watcher thread disables reload,
never the run.

A failed reload keeps the last good version running with a visible error:
`error` holds a path-free description that the runner feeds to the sinks'
status line, cleared on the next reload that succeeds. A save that leaves
the bytes unchanged is skipped by digest, so a watcher that fires twice
for one write costs nothing.

The file's owner can write it too (the page's layout edit): it gives the
digest of what it writes to `adopt` before the write, so the watcher's
event for that write is skipped, and applies its own step through `run`,
which reports as a reload does.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from collections.abc import Callable, Iterable
from pathlib import Path

from pewpew.errors import describe_exception

logger = logging.getLogger(__name__)

# (directory to watch, stop event) -> one item per change batch. The item is
# never inspected: the reloader re-reads the file and lets the digest decide.
Watch = Callable[[Path, threading.Event], Iterable[object]]

# How a part queues a closure onto the loop thread (`pewpew.pace.Calls.call_soon`).
CallSoon = Callable[[Callable[[], object]], None]

# Far below watchfiles' 1600 ms default, which is tuned for restarting a
# server process: the Pixelblaze bar is "save, look up, see it". Duplicate
# fires are free (digest), so the debounce only has to swallow one editor's
# burst of events for a single save.
_DEBOUNCE_MS = 100
_STEP_MS = 50


def watch_file(source: Path, stop: threading.Event) -> Iterable[object]:
    """The default watcher: `watchfiles` on the parent directory, filtered to
    `source`. The *directory* is watched, non-recursively, because an editor's
    atomic save (write a temp file, rename it over the original) replaces the
    inode; a watch on the file itself follows the old inode on inotify and goes
    silent after the first save. Every change kind is accepted — that rename
    arrives as `added`, not `modified`. Imported lazily so nothing else in the
    engine, and no test, needs the package loaded."""
    import watchfiles  # runtime dependency (architecture §9, ADR-020)

    target = source.resolve()
    # Cheap name test first: every event in the directory (editor temp files,
    # swap files, git churn) reaches this filter, and `resolve()` is a syscall
    # chain per call.
    return watchfiles.watch(
        source.parent,
        watch_filter=lambda change, path: (
            os.path.basename(path) == target.name and Path(path).resolve() == target
        ),
        recursive=False,
        debounce=_DEBOUNCE_MS,
        step=_STEP_MS,
        stop_event=stop,
        # A watcher that is interrupted must not raise into its own thread.
        raise_interrupt=False,
    )


class FileReloader:
    """Watch one file and apply each new version of it on the loop thread.

    `apply(data)` runs on the loop thread with the file's new bytes and
    returns a line for the log; if it raises, the last good version keeps
    running and `error` says why. Its exceptions must carry no path: the
    text reaches the status line and the preview socket. `noun` names what
    the file holds in those messages ("map").

    `watch` is the seam tests use — it is called with the file and the stop
    event, and each item it yields queues one `reload`. The default watches
    the file's directory through `watchfiles` (`watch_file`).
    """

    def __init__(
        self,
        source: Path,
        digest: str | None,
        call_soon: CallSoon,
        apply: Callable[[bytes], str],
        *,
        noun: str,
        watch: Watch | None = None,
    ) -> None:
        self._source = source
        self._digest = digest
        self._call_soon = call_soon
        self._apply = apply
        self._noun = noun
        self._watch = watch_file if watch is None else watch
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # Written on the loop thread, read by sink workers building a status
        # line. A plain attribute store is atomic; readers snapshot it once.
        self.error: str | None = None

    @property
    def active(self) -> bool:
        """Whether a watcher thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start watching; a no-op once started."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, args=(self._source, self._stop),
            name=f"pewpew-reload-{self._noun}", daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self, source: Path, stop: threading.Event) -> None:
        try:
            for _ in self._watch(source, stop):
                if stop.is_set():
                    break
                self._call_soon(self.reload)
        except Exception:
            logger.exception(
                "the file watcher died; hot reload is off for the rest of this run"
            )

    def adopt(self, digest: str) -> None:
        """Take `digest` as the version now current, so a reload of a file
        with those bytes is skipped. Any thread: one attribute store."""
        self._digest = digest

    def run(self, step: Callable[[], str]) -> bool:
        """Run the apply step `step` as `reload` runs its own: on success
        clear `error` and log the line `step` returns; on an exception keep
        the last good version and set `error`. Loop thread only.

        Never raises. Returns True when `step` succeeded.
        """
        try:
            summary = step()
        except Exception as exc:  # noqa: BLE001  RoomError, a raising setup, ...
            self._fail(describe_exception(exc), exc)
            return False
        self.error = None
        logger.info("%s", summary)
        return True

    def reload(self) -> bool:
        """Read the file and apply it if its bytes changed. Loop thread only.

        Never raises. Returns True when the new version was applied; False
        when the file was unchanged or the reload failed (see `error`).
        """
        try:
            data = self._source.read_bytes()
        except OSError:
            # Forgotten digest: when the file comes back, even byte-identical,
            # the next event reloads it and clears this error.
            self._digest = None
            self._fail(f"{self._noun} file is gone; keeping the last-good {self._noun}")
            return False
        digest = hashlib.sha256(data).hexdigest()
        if digest == self._digest:
            return False
        # Recorded before the attempt, so a second event for the same broken
        # bytes is a no-op rather than a second traceback.
        self._digest = digest
        return self.run(lambda: self._apply(data))

    def _fail(self, message: str, exc: BaseException | None = None) -> None:
        self.error = f"reload failed, last-good {self._noun} still running: {message}"
        logger.error("%s", self.error, exc_info=exc)

