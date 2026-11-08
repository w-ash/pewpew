"""Blink one fixture to find it on build day.

The operator names a fixture on the preview page and its pixels flash white
and off, so the bar on the ceiling that blinks is the one the map calls by
that name. `apply` is a paced-loop `after` stage, before the master and
every sink, so a blink drives the real boards: tier-1 bench actuation (CLAUDE.md
T-7).

The flashes are keyed on engine `t`. A blink starts on the first frame
after the request and runs for `DURATION` seconds at `RATE` Hz, on for the
first half of each period: under the 3 Hz flash limit (Epilepsy Society,
2023; WCAG 2.2 SC 2.3.1).

The master still applies, so blackout hides a blink and a low master dims
it. The rest of the frame keeps the look.

Thread discipline as for `Master`: `check` runs anywhere; `start`, `stop`,
`rebind` and `apply` belong to the loop thread (reach them through
`pewpew.pace.Calls.call_soon`).

The fixtures are (id, first pixel, pixel count) triples
(`pewpew.rig.runtime.fixture_spans`), so this module, which the aura
imports at start, never loads the rig stack.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from pewpew.errors import unknown

Span = tuple[str, int, int]  # a fixture's id, first pixel and pixel count

RATE = 2.0  # flashes per second
DURATION = 4.0  # seconds


class Blink:
    """At most one fixture blinking at a time; `apply` overrides one frame."""

    def __init__(self, fixtures: Sequence[Span]) -> None:
        self._fixtures = tuple(fixtures)
        self._span: tuple[int, int] | None = None  # (first, count) of the blinking fixture
        self._t0: float | None = None  # engine time of its first frame

    def check(self, fixture: object) -> str | None:
        """Why a blink of `fixture` would be refused, or None. Never raises.

        The wording names the fixture and never a path: it crosses the
        preview socket.
        """
        if not isinstance(fixture, str):
            return f"blink takes a fixture id, got {fixture!r}"
        ids = [fid for fid, _, _ in self._fixtures]
        if fixture not in ids:
            return unknown("fixture", fixture, ids)
        return None

    def start(self, fixture: str) -> None:
        """Blink `fixture` from the next frame, replacing any blink running.
        Loop thread only; a fixture a reload removed is ignored."""
        for fid, first, count in self._fixtures:
            if fid == fixture:
                self._span = (first, count)
                self._t0 = None
                return

    def stop(self) -> None:
        self._span = None
        self._t0 = None

    def rebind(self, fixtures: Sequence[Span]) -> None:
        """Take a reloaded map's fixtures. A blink in progress ends: its
        pixel range belongs to the old map."""
        self._fixtures = tuple(fixtures)
        self.stop()

    def apply(self, t: float, frame: np.ndarray) -> np.ndarray:
        """`frame` with the blinking fixture's pixels white or off at engine
        time `t`, as a new array; `frame` itself when nothing blinks.
        `frame` is never written: it is the renderer's live frame."""
        if self._span is None:
            return frame
        if self._t0 is None:
            self._t0 = t
        elapsed = t - self._t0
        if elapsed >= DURATION:
            self.stop()
            return frame
        first, count = self._span
        if first + count > len(frame):
            self.stop()
            return frame
        out = frame.copy()
        on = math.floor(elapsed * RATE * 2.0) % 2 == 0
        out[first : first + count] = 1.0 if on else 0.0
        return out
