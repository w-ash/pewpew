"""Render-loop watchdog: exit the process when no frame completes for a
while, so launchd starts pewpew again into the last look.

launchd restarts a job only when it exits (launchd.plist(5)), so a loop
that hangs must end the process itself. `beat` is a `PacedLoop` `on_frame`
callable: it stores the time of each completed frame and nothing else, so
it cannot block or raise. A separate thread checks the age of the last
beat every `interval` and, past `timeout` seconds, writes the stall marker,
writes one line straight to the process's stderr, and calls
`os._exit(EXIT_STALL)`: a non-zero code, which `KeepAlive
{SuccessfulExit=false}` restarts. `os._exit` skips the teardown on purpose,
because a hung loop thread can hold up an orderly exit forever. The line
bypasses logging because the runner defers log records while the terminal
sink owns the terminal, and `os._exit` would drop them; on a terminal it
also shows the cursor again.

The stall marker (`marker_path()`: `$PEWPEW_STALL_MARKER`, else
`~/.local/state/pewpew/stalled`, beside the audit log) tells the next start
that the last run stalled. It is one JSON object: `stalled`, the seconds
without a frame, and `looks`, the names of the looks that stalled within
the freshness window, each once. The runner takes it at start
(`take_marker`): a marker younger than `MARKER_FRESH_S` makes it start in
the first look of the idle cycle's order that the marker does not name,
instead of the file's current one, and say so on the status line, which
breaks a restart loop on looks that hang (pewpew.run.after_stall). The
run carries the names it took into its own marker, for as long as they
stay fresh. A marker of the older shape (the seconds alone) names no
look. The marker's age is wall-clock time, because it has to survive the
process.

Until the first beat the limit is `startup` (default
`max(3 * timeout, STARTUP_S)`), which covers building the look, the sinks
starting and the first render; a look that hangs there also ends the
process. Then the
limit is `timeout`, well over a normal hitch (a look recall or a room map
reload runs one `setup` between two frames). `time.monotonic` is the clock, so a
wall-clock step cannot fire it.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from pewpew.audit import state_file

logger = logging.getLogger(__name__)

TIMEOUT_S = 5.0
STARTUP_S = 15.0
EXIT_STALL = 70  # EX_SOFTWARE in sysexits(3)
MARKER_ENV = "PEWPEW_STALL_MARKER"
MARKER_FRESH_S = 600.0


def _exit(code: int) -> None:
    os._exit(code)


def marker_path() -> Path:
    """Where the stall marker goes: `$PEWPEW_STALL_MARKER`, else the
    per-user state dir."""
    return state_file(MARKER_ENV, "stalled")


class Stall(NamedTuple):
    """A fresh stall marker: its age in seconds and the looks it names."""

    age: float
    looks: tuple[str, ...]


def take_marker(path: Path, *, now: Callable[[], float] = time.time,
                fresh: float = MARKER_FRESH_S) -> Stall | None:
    """Remove the stall marker at `path`. Returns it when it is younger
    than `fresh`, else None (also when there is none). A marker that names
    no look, as one of the older shape, gives no `looks`. Never raises."""
    try:
        age = now() - Path(path).stat().st_mtime
        text = Path(path).read_text(encoding="utf-8")
        Path(path).unlink()
    except (OSError, UnicodeDecodeError):
        return None
    if age >= fresh:
        return None
    try:
        named = json.loads(text).get("looks")
    except (ValueError, AttributeError):
        named = None
    looks = tuple(dict.fromkeys(n for n in named if isinstance(n, str))) if isinstance(named, list) else ()
    return Stall(age, looks)


def _last_words(line: str) -> None:
    """Write `line` to the process's own stderr and flush it; on a
    terminal, show the cursor and start a fresh line first."""
    stream = sys.__stderr__
    if stream is None:
        return
    try:
        if stream.isatty():
            stream.write("\x1b[?25h\n")
        stream.write(line + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


class Watchdog:
    """Fires `on_stall(seconds)` once when no `beat` arrives for `timeout`
    seconds after the first one, or when the first one does not arrive
    within `startup` seconds of `start`. Without `on_stall` it writes the
    stall marker to `marker` (None: no marker), writes its line to stderr,
    and exits the process. The marker names `playing()` (any thread) and
    the looks of the `earlier` stall that this run took, while they are
    still fresh."""

    def __init__(
        self,
        timeout: float = TIMEOUT_S,
        *,
        interval: float | None = None,
        startup: float | None = None,
        on_stall: Callable[[float], None] | None = None,
        marker: Path | None = None,
        playing: Callable[[], str | None] | None = None,
        earlier: Stall | None = None,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if timeout <= 0.0:
            raise ValueError(f"timeout must be positive, got {timeout!r}")
        self.timeout = float(timeout)
        self.startup = float(startup) if startup is not None else max(3.0 * self.timeout, STARTUP_S)
        if self.startup <= 0.0:
            raise ValueError(f"startup must be positive, got {startup!r}")
        self._interval = interval if interval is not None else min(1.0, timeout / 4)
        self._on_stall = on_stall
        self._marker = marker
        self._playing = playing
        self._earlier = earlier
        self._now = now
        self._armed: float | None = None
        self._last: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.fired = False

    def beat(self, t: float = 0.0, frame: Any = None) -> None:
        """A frame completed. The `on_frame` signature; both arguments unused."""
        self._last = self._now()

    def check(self) -> float | None:
        """The stall in seconds when it has reached its limit, else None:
        `startup` from `start` until the first beat, then `timeout` from
        the last beat. None before `start`."""
        last = self._last
        if last is not None:
            age = self._now() - last
            return age if age >= self.timeout else None
        armed = self._armed
        if armed is None:
            return None
        age = self._now() - armed
        return age if age >= self.startup else None

    def start(self) -> None:
        """Arm the check and start the thread."""
        self._armed = self._now()
        self._thread = threading.Thread(target=self._run, name="pewpew-watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop checking; call it before an orderly teardown."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1.0)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            stalled = self.check()
            if stalled is not None:
                self._fire(stalled)
                return

    def _stalled_looks(self) -> list[str]:
        """The looks the marker names: those of `earlier` while the window
        that began at its stall still holds, then the one playing."""
        earlier = self._earlier
        names: list[str] = []
        if earlier is not None and self._armed is not None and (
            earlier.age + (self._now() - self._armed) < MARKER_FRESH_S
        ):
            names.extend(earlier.looks)
        playing = self._playing() if self._playing is not None else None
        if playing is not None:
            names.append(playing)
        return list(dict.fromkeys(names))

    def _fire(self, stalled: float) -> None:
        self.fired = True
        message = f"render loop stalled: no frame for {stalled:.1f} s; exiting {EXIT_STALL} so launchd restarts pewpew"
        if self._on_stall is not None:
            logger.critical(message)
            self._on_stall(stalled)
            return
        if self._marker is not None:
            try:
                self._marker.parent.mkdir(parents=True, exist_ok=True)
                record = {"stalled": round(stalled, 1), "looks": self._stalled_looks()}
                self._marker.write_text(json.dumps(record) + "\n", encoding="utf-8")
            except OSError:
                pass  # the exit matters more than the marker
        _last_words(f"CRITICAL {__name__}: {message}")
        _exit(EXIT_STALL)


__all__ = ["EXIT_STALL", "MARKER_FRESH_S", "STARTUP_S", "TIMEOUT_S", "Stall", "Watchdog", "marker_path", "take_marker"]
