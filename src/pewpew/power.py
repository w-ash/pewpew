"""Stage 3's power limit: a brightness ceiling and a watt cap on the linear frame.

Architecture §2 stage 3 and requirement Q-8: estimate what the linear-light
frame draws with a per-chip current model, then scale the frame, as
FastLED's `setMaxPowerInVoltsAndMilliamps` does [S413]. The stage runs
before any sink quantizes. Everything here is pure: no clock, no RNG.

- `PowerCap` is the cap: `max_brightness` and an optional `max_watts`.
- `EffectPower` is the current model of a compiled rig, in rig pixel order.
  `pewpew.rig.electrical.effect_power_model` builds it from the catalog.
- `PowerLimiter` applies a cap to each frame.
- `power_stage` runs a limiter as a `PacedLoop` `after` stage.

The ADR is research/synthesis/decisions/ADR-001-internal-color-pipeline.md
(amendment 2026-10-23).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

import numpy as np

#: The largest watt cap. It keeps the cap finite, and it is far over the
#: full-white draw of any rig the studio compiles.
MAX_CAP_W = 1e6

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PowerCap:
    """A ceiling on light output and on watts. The default caps nothing.

    `max_brightness` (0..1) scales every frame. `max_watts`, when set, then
    holds the estimated draw at or under it.
    """

    max_watts: float | None = None
    max_brightness: float = 1.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.max_brightness) and 0.0 <= self.max_brightness <= 1.0):
            raise ValueError(f"max_brightness must be from 0 to 1, got {self.max_brightness!r}")
        if self.max_watts is not None and not (0.0 < self.max_watts <= MAX_CAP_W):
            raise ValueError(f"max_watts must be over 0 and at most {MAX_CAP_W:g}, got {self.max_watts!r}")

    @property
    def caps(self) -> bool:
        """True if the cap can change a frame."""
        return self.max_watts is not None or self.max_brightness < 1.0

    def scale(self, variable_w: float, flat_w: float = 0.0) -> float:
        """The scale that keeps a full-white frame under the cap.

        The frame draws `flat_w` whatever it shows, plus `variable_w` × the
        scale. A cap under `flat_w` gives 0.
        """
        s = self.max_brightness
        if self.max_watts is not None and variable_w > 0.0:
            s = min(s, max(0.0, (self.max_watts - flat_w) / variable_w))
        return s

    def watts(self, variable_w: float, flat_w: float = 0.0) -> float:
        """The capped worst case: `flat_w + scale × variable_w`."""
        return flat_w + self.scale(variable_w, flat_w) * variable_w


def clean(frame: np.ndarray) -> np.ndarray:
    """A float32 copy of `frame` with NaN at 0 and every value clipped to
    [0, 1], as `pewpew.sinks.sink.to_display_u8` sanitizes it."""
    v = np.nan_to_num(np.asarray(frame, dtype=np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    np.clip(v, 0.0, 1.0, out=v)
    return v


@dataclass(frozen=True, eq=False)
class EffectPower:
    """A per-chip current model: per-pixel power coefficients in rig pixel order.

    `channel_w` is the watts of one full channel of the pixel, or 0 on a
    `flat` fixture. `min_term_w` and `max_term_w` weight min(R, G, B) and
    max(R, G, B), for an RGBW chip whose firmware derives W from RGB.

    `supply_of` gives each pixel's supply group: an index into `flat_w` and
    `worst_w`. A group is the pixels one PSU feeds; the last group is the
    pixels on no feed. `flat_w` is what a group draws whatever the frame
    shows: its `flat` fixtures, and the boards its PSU powers. `worst_w` is the most an RGB frame makes its other
    fixtures draw: the largest value `pixel_watts` reaches.
    """

    channel_w: np.ndarray
    min_term_w: np.ndarray
    max_term_w: np.ndarray
    supply_of: np.ndarray
    flat_w: np.ndarray
    worst_w: np.ndarray

    @property
    def n(self) -> int:
        return len(self.channel_w)

    def pixel_watts(self, v: np.ndarray) -> np.ndarray:
        """The (N,) watts each pixel of the clean (N, 3) frame `v` draws,
        without the `flat` fixtures.

        A pixel draws `channel_w` × its channel sum, equal weights per
        channel as WLED's estimator uses
        (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206,
        https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L285-L289).
        An RGBW pixel sums the channels after its firmware's auto-white.
        """
        if v.shape != (self.n, 3):
            raise ValueError(f"frame shape {v.shape} is not ({self.n}, 3)")
        watts = v.sum(axis=1, dtype=np.float64) * self.channel_w
        if self._min_used:
            watts += v.min(axis=1) * self.min_term_w
        if self._max_used:
            watts += v.max(axis=1) * self.max_term_w
        return watts

    def watts(self, frame_linear: np.ndarray) -> float:
        """The watts drawn to show the (N, 3) linear-light RGB `frame_linear`.

        Values are cleaned as `to_display_u8` cleans them
        (src/pewpew/sinks/sink.py:82-91).
        """
        return float(self.flat_w.sum() + self.pixel_watts(clean(frame_linear)).sum())

    @cached_property
    def _min_used(self) -> bool:
        return bool(self.min_term_w.any())

    @cached_property
    def _max_used(self) -> bool:
        return bool(self.max_term_w.any())


@dataclass(frozen=True)
class Limited:
    """One limited frame.

    `frame` is what the sinks get, `scale` what multiplied the clean frame
    (1 when the cap caps nothing). `watts` and `uncapped_watts` are the
    estimated draw with and without the cap, or None without a model.
    """

    frame: np.ndarray
    scale: float
    watts: float | None
    uncapped_watts: float | None


class PowerLimiter:
    """Scales linear frames so that they keep under a `PowerCap`.

    A frame is cleaned as the sinks clean it and scaled by `s`, at most
    `max_brightness`. With `max_watts` set, `s` also keeps each supply
    group's draw within its share of the cap: its `flat_w` plus `s*` × its
    `worst_w`, where `s*` is the scale that keeps the worst frame of the
    whole rig under the cap. The shares sum to the cap, so the rig keeps
    under it, and a frame that lights only one supply's fixtures cannot put
    the whole cap on that supply. With one group and no flat draw this is
    FastLED's estimate-and-scale [S413], `s = max_watts / estimate`. WLED limits each
    output against its own current limit in the same way
    (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L1447-L1524).

    `s` is never over 1, so the limiter never brightens a frame. A cap that
    caps nothing passes each frame through unchanged. `max_watts` needs a
    model; `max_brightness` alone does not.
    """

    def __init__(self, cap: PowerCap, model: EffectPower | None = None) -> None:
        if cap.max_watts is not None and model is None:
            raise ValueError("max_watts needs a power model: give an arrangement")
        self.cap = cap
        self.model = model
        if model is not None:
            s_worst = cap.scale(float(model.worst_w.sum()), float(model.flat_w.sum()))
            self._budget_w = s_worst * model.worst_w
            self._flat_w = float(model.flat_w.sum())
            self._groups = len(model.worst_w)

    def __call__(self, frame: np.ndarray) -> Limited:
        b = self.cap.max_brightness
        model = self.model
        if model is None:
            if not self.cap.caps:
                return Limited(frame, 1.0, None, None)
            return Limited(clean(frame) * np.float32(b), b, None, None)
        v = clean(frame)
        by_group = np.bincount(model.supply_of, weights=model.pixel_watts(v), minlength=self._groups)
        variable = float(by_group.sum())
        uncapped = self._flat_w + variable
        if not self.cap.caps:
            return Limited(frame, 1.0, uncapped, uncapped)
        s = b
        if self.cap.max_watts is not None:
            lit = by_group > 0.0
            if lit.any():
                s = min(s, float((self._budget_w[lit] / by_group[lit]).min()))
        return Limited(v * np.float32(s), s, self._flat_w + s * variable, uncapped)


def power_stage(limiter: Callable[[np.ndarray], Limited]) -> Callable[[float, np.ndarray], np.ndarray]:
    """A `PacedLoop` `after` stage: each frame under `limiter`'s cap.

    It goes after the master (`pewpew.aura.master.Master.apply`), as
    architecture §2 stage 3 orders them, so the cap holds whatever the
    master is set to. It never raises, as `PacedLoop` requires, and never
    writes into the frame: a frame the limiter refuses goes out black,
    never uncapped.
    """
    logged: set[type] = set()

    def stage(t: float, frame: np.ndarray) -> np.ndarray:
        try:
            return limiter(frame).frame
        except Exception as exc:
            if type(exc) not in logged:
                logged.add(type(exc))
                logger.exception("the power limit refused a frame; it goes out black")
            return np.zeros(frame.shape, dtype=np.float32)

    return stage
