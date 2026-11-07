"""Keep the laptop awake while the aura runs: hold `caffeinate -i -s -w <pid>`.

`-i` stops idle sleep and `-s` stops system sleep on AC power;
`-w <pid>` ends the assertion when pewpew exits, however it exits, so a
watchdog exit or a kill never leaves the laptop held awake. The code
changes no `pmset` setting: those belong to the unattended checklist. Lid-closed
sleep is not stopped by any of this, so the lid stays open on AC.

`check()` starts caffeinate again if it has ended, or failed to start,
while the aura runs; the health monitor calls it every step. A failure
that repeats is logged once. `state()` says whether it is held.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from pewpew.errors import describe_exception

logger = logging.getLogger(__name__)


def _spawn(args: list[str]) -> Any:
    return subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


class KeepAwake:
    """The caffeinate child process and its state."""

    def __init__(
        self,
        *,
        spawn: Callable[[list[str]], Any] | None = None,
        which: Callable[[str], str | None] = shutil.which,
        pid: int | None = None,
    ) -> None:
        self._spawn = spawn
        self._which = which
        self._pid = os.getpid() if pid is None else pid
        self._proc: Any = None
        self._detail: str | None = None
        self._started = False
        self._stopped = False

    @property
    def args(self) -> list[str]:
        return ["caffeinate", "-i", "-s", "-w", str(self._pid)]

    def start(self) -> None:
        self._started = True
        if self._which("caffeinate") is None:
            self._proc = None
            self._failed("caffeinate not found: macOS only")
            return
        try:
            self._proc = (self._spawn or _spawn)(self.args)
            self._detail = None
        except OSError as exc:
            self._proc = None
            self._failed(f"caffeinate did not start: {describe_exception(exc)}")

    def _failed(self, detail: str) -> None:
        if detail != self._detail:
            logger.warning("cannot keep the laptop awake: %s", detail)
        self._detail = detail

    def held(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def check(self) -> None:
        """Start caffeinate again if it ended or did not start. Monitor
        thread."""
        if self._stopped or not self._started or self.held():
            return
        if self._proc is not None:
            logger.warning("caffeinate exited (code %s); starting it again", self._proc.poll())
        self.start()

    def state(self) -> dict:
        held = self.held()
        detail = self._detail
        if not held and detail is None and self._proc is not None:
            detail = f"caffeinate exited ({self._proc.poll()})"
        return {"requested": True, "held": held, "detail": None if held else detail}

    def stop(self) -> None:
        self._stopped = True
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.kill()


__all__ = ["KeepAwake"]
