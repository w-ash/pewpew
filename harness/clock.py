"""Deterministic time source for tests.

Patterns are functions of t (req Q-5); tests inject this instead of wall
clock so every run of a pattern is bit-reproducible.
"""

from __future__ import annotations


class FakeClock:
    """Monotonic fake clock advanced explicitly by the test."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = float(start)

    @property
    def t(self) -> float:
        return self._t

    def tick(self, dt: float) -> float:
        if dt < 0:
            raise ValueError("clock never goes backwards")
        self._t += dt
        return self._t

    def frames(self, n: int, fps: float = 60.0) -> list[float]:
        """Timestamps for n successive frames at a fixed fps."""
        return [self.tick(1.0 / fps) for _ in range(n)]
