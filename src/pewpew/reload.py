"""Hot reload: re-execute the edited pattern file and swap it in live.

Architecture §8's dev loop: watch the pattern's source, re-import the leaf
module on change, and `Renderer.swap` the new class in while the engine
keeps running — `t`, parameter values, buffers, the RNG stream and plain
scalar state all continue (render.py). Never jurigged-style whole-process
patching: a pattern is one small module with a known interface.

Threading. A daemon thread blocks in the watcher and hands every change
batch to the loop thread through `call_soon`; `reload()` itself runs *on the
loop thread*, executing the file and swapping there, so the renderer keeps a
single owner at the cost of one hitched frame that the paced loop's skip
logic absorbs. `reload()` never raises — an exception out of a queued
closure propagates out of `PacedLoop.run()` and would end the show from a
typo — and a dying watcher thread disables reload, never the show.

A failed reload keeps the last-good pattern running with a visible error
(ADR-005): `error` holds a path-free description (pewpew.load) that the
runner feeds to both sinks' status line, cleared on the next reload that
succeeds. A save that leaves the bytes unchanged is skipped by digest, so a
watcher that fires twice for one write costs nothing.

Only the entry file is watched. Edits to a sibling module it imports, or to
the engine itself, need a restart.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Callable, Iterable

from pewpew.load import LoadedPattern, Source, describe_exception
from pewpew.render import Renderer

logger = logging.getLogger(__name__)

# (directory to watch, stop event) -> one item per change batch. The item is
# never inspected: the reloader re-reads the file and lets the digest decide.
Watch = Callable[[Path, threading.Event], Iterable[object]]

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
    import watchfiles  # third runtime dependency, sanctioned by architecture §9 / ADR-020

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


class Reloader:
    """Supervises one renderer's pattern source.

    `watch` is the seam tests use — it is called with the *source file* and
    the stop event, and each item it yields queues one `reload`. The default
    watches the file's directory through `watchfiles` (`watch_file`).
    """

    def __init__(
        self,
        renderer: Renderer,
        loaded: LoadedPattern,
        call_soon: Callable[[Callable[[], None]], None],
        *,
        watch: Watch | None = None,
    ) -> None:
        self._renderer = renderer
        self._loaded = loaded
        self._call_soon = call_soon
        self._watch = watch_file if watch is None else watch
        self._digest: str | None = loaded.digest
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        # Written on the loop thread, read by sink workers building a status
        # line. A plain attribute store is atomic; readers snapshot it once.
        self.error: str | None = None
        self.reloads = 0  # successful swaps
        self.failures = 0  # reloads that kept the last-good pattern

    @property
    def active(self) -> bool:
        """Whether a watcher thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start watching; a no-op for a pattern with no source file."""
        if self._loaded.source is None or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="pewpew-reload", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self) -> None:
        assert self._loaded.source is not None
        try:
            for _ in self._watch(self._loaded.source, self._stop):
                if self._stop.is_set():
                    break
                self._call_soon(self.reload)
        except Exception:
            logger.exception(
                "the file watcher died; hot reload is off for the rest of this run"
            )

    def reload(self) -> bool:
        """Re-execute the source and swap the pattern in. Loop thread only.

        Never raises. Returns True when a swap happened; False when the file
        was unchanged or the reload failed (see `error`).
        """
        path = self._loaded.source
        if path is None:
            return False
        try:
            source = Source.read(path)
        except OSError:
            # Forgotten digest: when the file comes back, even byte-identical,
            # the next event reloads it and clears this error.
            self._digest = None
            self._fail("source file is gone; keeping the last-good pattern")
            return False
        if source.digest == self._digest:
            return False
        # Recorded before the attempt, so a second event for the same broken
        # bytes is a no-op rather than a second traceback.
        self._digest = source.digest
        try:
            loaded = source.load(self._loaded.attr)
            report = self._renderer.swap(loaded.cls())
        except Exception as exc:  # LoadError, a raising __init__ or setup, ...
            self._fail(describe_exception(exc), exc)
            return False
        self._loaded = loaded
        self.error = None
        self.reloads += 1
        logger.info(
            "reloaded %s (t=%.3f): kept buffers %s, scalars %s; reset params %s; fresh %s",
            loaded.cls.__name__,
            self._renderer.t,
            list(report.buffers),
            list(report.scalars),
            list(report.reset_params),
            list(report.skipped),
        )
        return True

    def _fail(self, message: str, exc: BaseException | None = None) -> None:
        self.failures += 1
        self.error = f"reload failed, last-good pattern still running: {message}"
        logger.error("%s", self.error, exc_info=exc)
