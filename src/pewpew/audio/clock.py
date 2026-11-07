"""The sample clock of a live input: a line from sample index to engine
time, fitted to when the samples arrived.

A live source's samples arrive in blocks, and a tick drains each block
with no timestamp but the tick's own. `SampleClock.observe(end, t)`
stamps a block, whose last sample is `end - 1`, with `t + 1/fps`, the end
of its slot: the loop can run a tick late with a `t` up to one period
behind (pewpew.pace), so the end of the slot is at or after the arrival.

The fit keeps, for each second of samples, the stamp that sits earliest
against its index, over the last `WINDOW_S` seconds. Its slope `b` is the
median of the pairwise slopes of those points and its offset `a` the
median residual, so one early point moves the line by little, where a line
under every point (Moon, Skelly & Towsley [S1753]) would follow it until
it left the window. `b * rate` is the source's rate against engine time,
so `drift_ppm` reports the drift it measures, and judges none.

`time(index)` is None until the points span `READY_S` seconds: the beat
oscillator does not steer until then (ADR-009, 2026-11-06 amendment
"live input").
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np

WINDOW_S = 60  # seconds of per-second points the fit keeps
READY_S = 5  # seconds of points before the fit maps an index


class SampleClock:
    """Sample index to engine time for a live source at `rate` samples a
    second, drained by a loop at `fps`. Loop thread."""

    def __init__(self, rate: int, fps: float) -> None:
        self.rate = int(rate)
        self.slot = 1.0 / float(fps)
        self._earliest: OrderedDict[int, tuple[float, float]] = OrderedDict()  # second -> (end, stamp)
        self._line: tuple[float, float] | None = None  # (a, b): t = a + b * index

    def observe(self, end: int, t: float) -> None:
        """A block ending before sample `end` was drained at the tick of engine time `t`."""
        stamp = t + self.slot
        second = end // self.rate
        kept = self._earliest.get(second)
        if kept is None or stamp - end / self.rate < kept[1] - kept[0] / self.rate:
            self._earliest[second] = (float(end), stamp)
            self._earliest.move_to_end(second)
            while next(iter(self._earliest)) <= second - WINDOW_S:
                self._earliest.popitem(last=False)
            self._line = None

    def restart(self) -> None:
        """Forget every point: the source restarted its sample count."""
        self._earliest.clear()
        self._line = None

    def time(self, index: float) -> float | None:
        line = self.line()
        return None if line is None else line[0] + line[1] * index

    def line(self) -> tuple[float, float] | None:
        """The fitted (a, b) of `t = a + b * index`, or None before `READY_S`."""
        if self._line is None and self._earliest:
            seconds = list(self._earliest)
            if seconds[-1] - seconds[0] >= READY_S:
                self._line = _fit(np.array(list(self._earliest.values())))
        return self._line

    @property
    def drift_ppm(self) -> float | None:
        """How fast the source runs against engine time, in parts per
        million; None before the fit."""
        line = self.line()
        return None if line is None else (1.0 / (line[1] * self.rate) - 1.0) * 1e6


def _fit(points: np.ndarray) -> tuple[float, float]:
    """The median-of-slopes line through `points`, rows of (index, t)."""
    x0 = points[0, 0]
    x, y = points[:, 0] - x0, points[:, 1]
    i, j = np.triu_indices(len(x), k=1)
    b = float(np.median((y[j] - y[i]) / (x[j] - x[i])))
    a = float(np.median(y - b * x))
    return a - b * x0, b


__all__ = ["READY_S", "WINDOW_S", "SampleClock"]
