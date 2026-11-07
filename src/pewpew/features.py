"""The read-only sensor frame patterns see, plus its deterministic stand-in.

Patterns never touch raw audio: features arrive pre-chewed (melbanks, beat,
group scalars) from the feature bus (architecture §7, ADR-009), so
`FeatureFrame` is the whole of what `before_render` gets. A run with
`--audio` reads the analysis of real sound (`pewpew.audio`); every other
renderer reads the seeded `FakeFeatures`, which is faithful in shape.

`events` carries the room events accepted at the frame's tick
(pewpew.aura.triggers); the fake never carries any, and `EventFeatures` adds
them to another source's frames. `FeatureSource` is what a `Renderer`
reads a frame from; `MemoFeatures` lets every layer of a stack read one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Protocol

import numpy as np

from pewpew.kit import TWO_PI

N_BANDS = 16  # the bands of every frame


@dataclass(frozen=True)
class Event:
    """One accepted room event, as a pattern sees it in `features.events`."""

    name: str
    source: str
    value: float | None  # None for an impulse
    priority: str
    t: float  # engine time of the frame it fired on
    tick: int  # frames since the run started


@dataclass(frozen=True)
class FeatureFrame:
    bands: np.ndarray  # (N_BANDS,) float32, read-only
    volume: float
    bass: float
    mid: float
    high: float
    beat_phase: float  # 0-1, 120 BPM
    # Room events accepted at this frame's tick, in the order they fired;
    # empty on every other frame. ADR-009 amendment 2026-11-02.
    events: tuple[Event, ...] = ()


class FeatureSource(Protocol):
    """Where a renderer reads each frame's features."""

    def at(self, t: float) -> FeatureFrame: ...


class FakeFeatures:
    """16 seeded-sinusoid GEQ bands and the group scalars."""

    def __init__(self, seed: int):
        r = np.random.default_rng(seed ^ 0xFEA7)
        self._rates = (0.3 + 2.2 * r.random(N_BANDS)).astype(np.float32)
        self._phases = r.random(N_BANDS).astype(np.float32)

    def at(self, t: float) -> FeatureFrame:
        bands = (0.5 + 0.5 * np.sin(TWO_PI * (self._rates * t + self._phases))).astype(np.float32)
        bands.setflags(write=False)  # §7: the sensor frame is read-only
        return FeatureFrame(
            bands=bands,
            volume=float(bands.mean()),
            bass=float(bands[:4].mean()),
            mid=float(bands[4:10].mean()),
            high=float(bands[10:].mean()),
            beat_phase=(2.0 * t) % 1.0,
        )


class EventFeatures:
    """A feature source that adds each frame's room events to `base`'s
    frame. `post(t, events)` sets the events of the frame at engine time
    `t`, on the loop thread before that frame renders (`Triggers` does);
    a frame with no events is `base`'s own, unchanged."""

    def __init__(self, base: FeatureSource) -> None:
        self._base = base
        self._events: tuple[float, tuple[Event, ...]] = (math.nan, ())

    def post(self, t: float, events: tuple[Event, ...]) -> None:
        self._events = (t, events)

    def at(self, t: float) -> FeatureFrame:
        frame = self._base.at(t)
        stamped, events = self._events
        return replace(frame, events=events) if events and stamped == t else frame


class MemoFeatures:
    """A feature source that asks `base` once per engine time: the frame at
    `t` is kept until a frame at another time is read, so every layer of a
    stack (pewpew.compose) reads the same frame for one call to `base`.
    Loop thread only. A `base` that raises keeps nothing, so each reader
    contains the failure on its own."""

    def __init__(self, base: FeatureSource) -> None:
        self.base = base
        self._last: tuple[float, FeatureFrame] | None = None

    def at(self, t: float) -> FeatureFrame:
        last = self._last
        if last is not None and last[0] == t:
            return last[1]
        frame = self.base.at(t)
        self._last = (t, frame)
        return frame


def memo(source: FeatureSource) -> MemoFeatures:
    """`source` read once per engine time: itself when it already is."""
    return source if isinstance(source, MemoFeatures) else MemoFeatures(source)
