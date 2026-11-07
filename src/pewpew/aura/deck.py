"""The deck: the stack that runs, and the one way to start layers.

A look recall and a layer edit both build fresh layers on the
crossfader's current geometry. `Deck.recall` does that for a whole look
(a fresh stack, faded or cut to), and `Deck.add` for a layer new to the
running stack; `remove` and `move` edit the running stack's layers as they
run. Each changes nothing unless every step that can fail has passed, and
its refusal names the layer.

Thread discipline as for the crossfader: `recall`, `add`, `remove` and
`move` belong to the loop thread; `controls` and `snapshot` are read by
any thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from pewpew.compose import Compositor, Controls, Layer, LayerError, Look
from pewpew.crossfade import Crossfader
from pewpew.errors import Worded

logger = logging.getLogger(__name__)


class Deck:
    """The crossfader over the running stack."""

    def __init__(self, fader: Crossfader[Compositor]) -> None:
        self.fader = fader

    @property
    def controls(self) -> Controls:
        """Every knob of the running stack. A recall or a layer edit
        installs new controls, so read this each time; do not hold it."""
        return self.fader.current.controls

    def snapshot(self) -> Look:
        """The running stack as a look (`Compositor.snapshot`)."""
        return self.fader.current.snapshot()

    def recall(self, look: Look, fade: float = 0.0) -> str | None:
        """Start `look`'s layers and signals fresh, fading over `fade`
        seconds or cutting at 0. A running fade ends at its target first,
        as a layer edit ends it. Returns why not, or None: also a route
        that reaches no knob it can move. Loop thread only."""
        try:
            incoming = self.fader.current.spawn(look)
        except (LayerError, ValueError) as exc:  # ValueError: a signal or route the stack cannot run
            # A traceback helps find an op that raised; a refusal says all there is.
            refused = not isinstance(exc, LayerError) or isinstance(exc.__cause__, Worded)
            logger.warning("cannot start the look: %s", exc, exc_info=not refused)
            return str(exc)
        if fade:
            if self.fader.fading:
                self.fader.cut(self.fader.current)
            self.fader.fade_to(incoming, fade)
        else:
            self.fader.cut(incoming)
        return None

    def add(self, layer: Layer, index: int) -> str | None:
        """Run `layer` in the running stack, fresh, at render index `index`
        (0: the bottom); the other layers run on. Ends a running fade.
        Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.insert(layer, index))

    def remove(self, lid: str) -> str | None:
        """Stop layer `lid` of the running stack; the other layers run on.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.remove(lid))

    def move(self, lid: str, index: int) -> str | None:
        """Run layer `lid` of the running stack at render index `index`.
        Ends a running fade. Returns why not, or None. Loop thread only."""
        return self._edit(lambda current: current.move(lid, index))

    def _edit(self, edit: Callable[[Compositor], object]) -> str | None:
        """Run `edit` on the running stack, then end a running fade at it.
        Returns the reason of a LayerError or ValueError it raises, with
        the stack untouched, or None."""
        current = self.fader.current
        try:
            edit(current)
        except LayerError as exc:
            logger.warning("cannot run layer %s", exc.layer, exc_info=True)
            return str(exc)
        except ValueError as exc:  # no such layer, a layer of that id, or none left
            return str(exc)
        self.fader.cut(current)
        return None
