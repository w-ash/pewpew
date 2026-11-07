"""Frame metrics: the numbers an agent reads before it looks at a sheet.

`measure(frames, fps)` reduces a rendered sequence, (F, N, 3) linear light
as an offline render gives it (pewpew.lab.rendering.play), to one `Metrics` record: flashing,
brightness, motion, detail and colour. `Metrics.flash_safe` checks a
record against WCAG's three flashes a second, and gives None for less than
a second of frames, where the count is only a lower bound. `rms` compares
two sequences; `LIVENESS_RMS` is how far an input must move one to count.

Every number except `nonfinite` is taken from the frames as a sink shows
them (`pewpew.sinks.base.sanitize`): NaN to 0, +inf to 1, clipped to
[0, 1]. Luma is WCAG relative luminance, Y = 0.2126 R + 0.7152 G +
0.0722 B, on linear light. A sample is one pixel of one frame. A mean over
no samples (no pixels, or one frame for a per-step number) is 0.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np
from numpy.typing import ArrayLike

from pewpew.color import oklab
from pewpew.render import check_frames
from pewpew.sinks.base import sanitize

# WCAG 2.2 SC 2.3.1: no more than three flashes in any one second.
FLASH_LIMIT = 3.0
FLASH_SWING = 0.1  # a change of relative luminance that counts toward a flash: 10% of full, or more

BLACK = 1.0 / 255.0  # luma below one 8-bit step is black
CLIP = 0.999  # a channel at this or more is clipped
# The RMS an input (a seed, a param) must move a sequence by to count as
# changing the picture: float noise sits below 1e-6, a visible change above.
LIVENESS_RMS = 1e-3
STILL = 1.0 / 255.0  # a span where no channel moves this much is frozen
STILL_SPAN = 0.1  # seconds: the span `frozen_fraction` compares frames across, whatever the fps

# OKLab chroma below this is grey for the hue measures: about a saturated
# colour at 1/500 of full light, or HSV saturation 0.25 at full brightness.
CHROMA_FLOOR = 0.03
HUE_BINS = 12  # `hue_clusters` bins around the OKLab hue circle, 30° each
# A hue bin counts when it holds this share of the coloured samples, so a
# few stray edge pixels do not add a cluster.
MIN_SHARE = 0.05



@dataclass(frozen=True, slots=True)
class Metrics:
    """What `measure` found in one sequence. Luma (Y) is 0-1; a fraction
    is a share of samples (or of frame steps) from 0 to 1."""

    frames: int
    pixels: int
    seconds: float  # frames / fps
    flash_rate_max: float  # flashes per second: the most one pixel makes in any one-second window
    mean_luma: float
    p95_luma: float  # the 95th percentile of Y
    black_fraction: float  # samples with Y < 1/255
    clip_fraction: float  # samples with any channel >= 0.999
    nonfinite: int  # NaN and infinite channel values in the input
    motion_energy: float  # mean |ΔY| of a pixel from frame to frame, per second
    frozen_fraction: float  # spans of 0.1 s (at least one frame) where no channel of any pixel moves 1/255
    spatial_detail: float  # mean |ΔY| between pixel i and pixel i + 1 (index order, see `measure`)
    palette_spread: float  # 0 one hue or none, 1 hues in balance around the wheel (OKLab, chroma-weighted)
    hue_clusters: int  # 30° OKLab hue bins that hold >= 5% of the coloured samples; a hue near a bin edge counts once

    @property
    def flash_safe(self) -> bool | None:
        """Whether no pixel flashes more than WCAG's three times in any
        second; None (unknown) for a sequence under one second, whose
        `flash_rate_max` counts the flashes of a shorter span and so can
        pass a strobe."""
        if self.seconds < 1.0:
            return None
        return self.flash_rate_max <= FLASH_LIMIT

    def to_json(self) -> dict[str, float]:
        """The record as JSON-ready numbers, floats rounded to 4 places."""
        return {f.name: round(getattr(self, f.name), 4) for f in fields(self)}


def measure(frames: np.ndarray, fps: float) -> Metrics:
    """The metrics of `frames`, a sequence rendered at `fps`.

    `spatial_detail` compares neighbours in index order, which is wiring
    order: along a strip or a row-major panel that is spatial detail, but
    on a serpentine panel or across fixtures in a room it also counts the
    step from the end of one run to the start of the next.
    """
    raw = check_frames(frames, fps)
    fps = float(fps)  # a NumPy scalar would make the record's floats NumPy ones, which json cannot write
    shown = sanitize(raw)
    y = luma(shown)
    lab = oklab(shown)
    a, b = lab[..., 1], lab[..., 2]
    coloured = np.hypot(a, b) >= CHROMA_FLOOR  # the samples the hue measures read; the rest are grey
    span = max(1, round(fps * STILL_SPAN))
    return Metrics(
        frames=len(raw),
        pixels=raw.shape[1],
        seconds=len(raw) / fps,
        flash_rate_max=float(flash_rates(shown, fps).max(initial=0.0)),
        mean_luma=_mean(y),
        p95_luma=float(np.percentile(y, 95)) if y.size else 0.0,
        black_fraction=_mean(y < BLACK),
        clip_fraction=_mean((shown >= CLIP).any(axis=-1)),
        nonfinite=int(np.count_nonzero(~np.isfinite(raw))),
        motion_energy=_mean(np.abs(np.diff(y, axis=0))) * fps,
        frozen_fraction=_mean(np.abs(shown[span:] - shown[:-span]).max(axis=(1, 2), initial=0.0) < STILL),
        spatial_detail=_mean(np.abs(np.diff(y, axis=1))),
        palette_spread=_hue_spread(a[coloured], b[coloured]),
        hue_clusters=_hue_clusters(a[coloured], b[coloured]),
    )


def rms(a: np.ndarray, b: np.ndarray) -> float:
    """The root-mean-square difference of two arrays of one shape, in
    float64. Raises ValueError for two shapes."""
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    return float(np.sqrt(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)))


def luma(frames: np.ndarray) -> np.ndarray:
    """WCAG relative luminance of linear-light colours: (..., 3) -> (...)."""
    return frames[..., 0] * 0.2126 + frames[..., 1] * 0.7152 + frames[..., 2] * 0.0722


def flash_rates(frames: np.ndarray, fps: float) -> np.ndarray:
    """Most flashes each pixel makes in any one-second window.

    A flash is "a pair of opposing changes in relative luminance of 10% or
    more of the maximum relative luminance (1.0)" (WCAG 2.2, definition of
    "general flash and red flash thresholds"). Relative luminance is
    `luma`; the frames are already linear light, so no gamma expansion is
    applied.

    A change is counted when luminance moves 0.1 or more away from the last
    extreme in the direction opposite to the previous change (a zigzag with
    0.1 hysteresis); flashes are changes / 2. This is stricter than WCAG in
    two ways: it counts every pixel alone, where WCAG exempts flashing over
    less than 25% of a 10-degree visual field, and it drops WCAG's exemption
    for changes whose darker side is above 0.80. Red flashes (saturated red
    transitions) are not measured separately. A sequence shorter than one
    second is one window.
    """
    lum = luma(frames)
    delta = FLASH_SWING - 1e-6  # "or more": float32 holds a swing of 0.1, such as 0.5 - 0.4, a hair under it
    direction = np.zeros(lum.shape[1], np.int8)  # +1 rising, -1 falling, 0 not yet moved
    high = lum[0].astype(np.float64)
    low = high.copy()
    changes = np.zeros(lum.shape, bool)
    for i in range(1, len(lum)):
        v = lum[i]
        high = np.where(direction >= 0, np.maximum(high, v), high)
        low = np.where(direction <= 0, np.minimum(low, v), low)
        rise = (direction <= 0) & (v - low >= delta)
        fall = (direction >= 0) & (high - v >= delta) & ~rise
        changes[i] = rise | fall
        direction = np.where(rise, 1, np.where(fall, -1, direction)).astype(np.int8)
        high = np.where(rise, v, high)
        low = np.where(fall, v, low)
    window = max(1, min(round(fps), len(lum)))
    count = np.concatenate([np.zeros((1, lum.shape[1])), np.cumsum(changes, axis=0)])
    per_window = count[window:] - count[:-window]
    return per_window.max(axis=0) / 2.0


def _hue_spread(a: np.ndarray, b: np.ndarray) -> float:
    """1 - |Σ (a + ib)| / Σ chroma over the coloured samples' OKLab `a`
    and `b`: the circular variance of hue, each sample weighted by its
    chroma, since a + ib is chroma times the unit hue vector. 0 when
    nothing has colour."""
    chroma = float(np.hypot(a, b).sum(dtype=np.float64))
    if chroma <= 0.0:
        return 0.0
    resultant = float(np.hypot(a.sum(dtype=np.float64), b.sum(dtype=np.float64)))
    return max(0.0, 1.0 - resultant / chroma)


def _hue_clusters(a: np.ndarray, b: np.ndarray) -> int:
    """How many of the HUE_BINS hue bins hold MIN_SHARE or more of the
    coloured samples (OKLab `a` and `b` of the samples whose chroma is
    CHROMA_FLOOR or more): the fewer of two bin sets half a bin apart. Hues
    that all fit in half a bin (15°) fall in one bin of one set, so one hue
    near a bin edge counts once."""
    if not a.size:
        return 0
    position = np.arctan2(b, a) / (2.0 * np.pi) % 1.0 * HUE_BINS
    least = MIN_SHARE * a.size
    return min(_full_bins(position + shift, least) for shift in (0.0, 0.5))


def _full_bins(position: np.ndarray, least: float) -> int:
    """How many hue bins hold `least` samples or more; `position` is in bins."""
    bins = position.astype(np.int64) % HUE_BINS  # positions at or past the top bin wrap to bin 0
    return int(np.count_nonzero(np.bincount(bins, minlength=HUE_BINS) >= least))


def _mean(values: ArrayLike) -> float:
    array = np.asarray(values)
    return float(array.mean(dtype=np.float64)) if array.size else 0.0
