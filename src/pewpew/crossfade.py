"""Crossfade: two live sources side by side, their linear frames blended.

The live loop drives a `Crossfader` over two `Live` sources: in the aura,
two layer stacks (pewpew.compose.Compositor), one per look. Between fades
it is the current source and adds nothing: `advance_to` returns that
source's frame unchanged. `fade_to(incoming, seconds)` keeps the current
source running as the outgoing side, makes `incoming` the current one, and
returns

    out * (1 - a) + in * a,   a = (t - t0) / seconds

per frame, where `t0` is the engine time of the last frame before the fade.
The first frame at or past `a = 1` is the incoming frame alone, and the
outgoing source is dropped. Progress comes from engine `t` only, so a fade
renders the same bytes every time it is replayed (T-1…T-5).

Each source's frame is the (N,3) linear pixel frame after its fixture
gather (render.py), so two looks with different `units` blend pixel for
pixel. The master is not part of the blend: it is a `PacedLoop` stage after
this.

`current` is the source a live set, a hot reload and a pick act on, which
during a fade is the incoming one: they change the look that is fading in.
A recall builds a fresh source and fades or `cut`s to it; a `cut` ends a
running fade. `rebind` moves both, so a room map reload mid-fade keeps the
fade.

Containment: each source turns its per-frame failures into an error frame,
so a fade blends whatever both sides return and the frame still renders.
The outgoing side is on its way out, so anything its `advance_to` raises (a
source left unbound by a failed rebind) ends the fade at once rather than
the frame. A current source that raises RuntimeError (a renderer left
unbound by a room map reload whose rollback rebind also failed) renders its
error frame until a later reload or rebind binds it again.

Blend frames, never engines: layer compositing within a look is
`pewpew.compose`, and this fades between two of its stacks.

Thread discipline as for `Renderer`: everything here belongs to the loop
thread; reach it through `pewpew.pace.Calls.call_soon`.
"""

from __future__ import annotations

import logging
import math
from typing import Generic, TypeVar

import numpy as np

from pewpew.mapping import Grouping
from pewpew.render import Live, PatternError

logger = logging.getLogger(__name__)

S = TypeVar("S", bound=Live)


class Crossfader(Generic[S]):
    """The current source, and the outgoing one while a fade runs."""

    def __init__(self, source: S) -> None:
        self._current: S = source
        self._outgoing: S | None = None
        self._t0 = 0.0
        self._seconds = 0.0
        self._unbound: S | None = None

    # ---- the fade ------------------------------------------------------

    @property
    def current(self) -> S:
        """The source of the look now running or fading in."""
        return self._current

    @property
    def fading(self) -> bool:
        return self._outgoing is not None

    @property
    def progress(self) -> float | None:
        """Blend weight of the incoming side at the last frame, 0 to 1, or
        None between fades."""
        if self._outgoing is None:
            return None
        return min(1.0, max(0.0, (self.t - self._t0) / self._seconds))

    def cut(self, source: S) -> None:
        """Make `source` current from the next frame on, with no fade. Ends
        a running fade."""
        self._current = source
        self._outgoing = None

    def fade_to(self, source: S, seconds: float) -> None:
        """Fade from the current source to `source` over `seconds` of engine
        time; 0 is `cut`. Raises RuntimeError while a fade runs: the caller
        decides whether a second recall waits or replaces."""
        if not (math.isfinite(seconds) and seconds >= 0.0):
            raise ValueError(f"a fade takes a finite number of seconds, at least 0, got {seconds!r}")
        if self._outgoing is not None:
            raise RuntimeError("a fade is already running")
        if seconds == 0.0:
            self.cut(source)
            return
        self._t0 = self._current.t
        self._seconds = float(seconds)
        self._outgoing = self._current
        self._current = source

    def advance_to(self, t: float) -> np.ndarray:
        """Render frame `t`: the current source's frame, blended with the
        outgoing one's while a fade runs."""
        current = self._current
        try:
            incoming = current.advance_to(t)
        except RuntimeError:
            # Unbound: a `setup` raised on the last rebind. The failed
            # reload keeps the status line red; logged once per source.
            if self._unbound is not current:
                self._unbound = current
                logger.exception("the running look is not bound; showing the error frame")
            return current.error_frame(float(t))
        self._unbound = None
        outgoing = self._outgoing
        if outgoing is None:
            return incoming
        a = (float(t) - self._t0) / self._seconds
        if a >= 1.0:
            self._outgoing = None
            return incoming
        try:
            old = outgoing.advance_to(t)
        except Exception:
            logger.warning("the outgoing look failed mid-fade; the fade ends here", exc_info=True)
            self._outgoing = None
            return incoming
        w = np.float32(a)
        out = old * (np.float32(1.0) - w)
        out += incoming * w
        return out

    # ---- the current source ------------------------------------------------

    @property
    def t(self) -> float:
        return self._current.t

    @property
    def error(self) -> PatternError | None:
        """The current source's contained failure, else the outgoing one's."""
        err = self._current.error
        outgoing = self._outgoing
        if err is None and outgoing is not None:
            err = outgoing.error
        return err

    def error_frame(self, t: float) -> np.ndarray:
        """The current source's error frame at engine time `t`."""
        return self._current.error_frame(t)

    def rebind(self, mapping: np.ndarray, grouping: Grouping | None = None) -> None:
        """Rebind the current source, raising as its `rebind` does; then the
        outgoing one, whose failure ends the fade instead."""
        self._current.rebind(mapping, grouping)
        outgoing = self._outgoing
        if outgoing is None:
            return
        try:
            outgoing.rebind(mapping, grouping)
        except Exception:
            logger.warning("the outgoing look cannot bind the new map; the fade ends here", exc_info=True)
            self._outgoing = None
