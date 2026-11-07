"""The master dimmer: one scalar on the linear frame, under a launch-time cap.

Architecture §2 stage 3's master brightness. `apply` is the paced loop's
last `after` stage, so every sink quantizes the dimmed frame and the
preview shows what the room sees. The scale multiplies the linear-light
values, so 0.5 is half the light, and it involves no time: the same frame
and the same state give the same output.

The cap is set at launch (`run --master-cap`) and never changes while
the aura runs. A level above it is refused, not clamped, as `ParamSet`
refuses an out-of-range param: a clamp would quietly run a value nobody
chose, and a refusal tells the operator the cap is there. The page's slider
ends at the cap, so only a stale or hand-made message meets the refusal.

Blackout forces the output to 0 and keeps the level, so a restore returns
to the same brightness.

Thread discipline as for the renderer: `check` runs anywhere; `set` and
`set_blackout` belong to the loop thread (reach them through
`pewpew.pace.Calls.call_soon`), so a change lands between whole frames.
"""

from __future__ import annotations

import numpy as np

from pewpew.params import Float


class Master:
    """Master level, blackout and the cap; `apply` dims one frame."""

    def __init__(self, cap: float = 1.0) -> None:
        if isinstance(cap, bool) or not (isinstance(cap, (int, float)) and 0.0 < cap <= 1.0):
            raise ValueError(f"the brightness cap must be above 0 and at most 1, got {cap!r}")
        self.cap = float(cap)
        self._range = Float(self.cap, 0.0, self.cap)
        # Starts at the cap: the operator dims down from the most the launch allows.
        self.level = self.cap
        self.blackout = False

    @property
    def scale(self) -> float:
        """The factor `apply` uses: 0 in blackout, else the level."""
        return 0.0 if self.blackout else self.level

    def check(self, value: object) -> str | None:
        """Why `value` would be refused as the level, or None. Never raises.

        The wording is the param kinds' own, with the cap as the range's top,
        and never a path: it crosses the preview socket.
        """
        return self._range.parse("master", value)[1]

    def set(self, value: float) -> None:
        """Set the level, snapped onto 0 to the cap. Loop thread only; raises
        ValueError for a value `check` refuses."""
        level, reason = self._range.parse("master", value)
        if reason is not None:
            raise ValueError(reason)
        assert level is not None
        self.level = level

    def set_blackout(self, on: bool) -> None:
        """Force the output to 0, or restore it to the level. Loop thread only."""
        self.blackout = bool(on)

    def apply(self, t: float, frame: np.ndarray) -> np.ndarray:
        """`frame` at engine time `t` times the scale, as a new float32
        array; `frame` is not changed. The loop's frame is shared with the
        renderer's state (render.py), so the product must never be written
        into it. `t` is unused: the master involves no time."""
        return np.multiply(frame, np.float32(self.scale), dtype=np.float32)
