"""The beat: Stark, Davies & Plumbley's causal tracker on the onset of each
hop, and the engine-time oscillator that `beat_phase` reads.

`Tracker` implements Stark et al. [S1750] §2 as written, from the papers
and never from GPL code (ADR-012 rule 1):

- a cumulative score `C(m) = (1 - α) Γ(m) + α max_v W1(v) C(m + v)` over
  the past `v` from -2τ to -τ/2, with a log-Gaussian `W1` of tightness η
  (eqs. 2–3, α 0.9 and η 5);
- half a beat after each beat, the next beat predicted as the peak of the
  score carried one beat ahead with α = 1, weighted by a Gaussian `W2`
  centred half a beat on (eqs. 4–5);
- once each predicted beat has passed, the tempo from the last `TEMPO_S`
  seconds of onsets: a moving-mean threshold over 16 samples, an
  autocorrelation normalised for its lag, a comb filterbank of four
  elements with Rayleigh weighting (Davies & Plumbley [S1751] eqs. 3–8)
  over 80–160 BPM, and a one-step "Viterbi-like" update with σ = 10 BPM
  (eqs. 6–12).

`confidence` is the salience of the comb's peak: 1 minus the ratio of
its mean to its maximum over the tempo range [inf: RA-28 §2; tuned in
M4]. Below `FREE_RUN_BELOW` the beat free-runs at the last confident
tempo.

`Oscillator` gives `beat_phase` on engine time:
`phase += dt * bpm / 60 * (1 + c)`. A phase-locked loop sets `c`, at most
`MAX_CORRECTION` either way, from the phase error against the tracker's
beats, so the phase never steps back and a wrap is a beat. Arrival jitter
moves `c`, never the phase.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from pewpew.audio.analysis import Hop

TEMPO_BPM = (80, 160)  # one tempo octave (Stark §2.3)
ALPHA = 0.9
ETA = 5.0
TEMPO_S = 6.0
THRESHOLD_Q = 16  # the moving mean's span, in onset samples (Davies & Plumbley eq. 3)
COMB_ELEMENTS = 4
DEFAULT_BPM = 120.0
FREE_RUN_BELOW = 0.3  # confidence under which the beat free-runs [inf]
DEGRADED_ABOVE = 0.1  # held share of the tempo window over which tempo and phase stop [inf]
TAP_WINDOW = 0.04  # a tap keeps the tracker within this share of the tapped tempo [inf]
MAX_CORRECTION = 0.1  # the PLL's largest rate correction [inf]
NUDGE = 0.02  # the rate a held nudge adds or takes away
PLL_GAIN = 1.0  # rate correction per beat of phase error [inf]


class Tracker:
    """The beat tracker (module docstring), fed one `Hop` of `hop`
    samples at `rate` samples a second at a time. `grid` is where it puts
    the beats: a beat at sample `anchor` and one every `period` samples.
    Loop thread."""

    def __init__(self, hop: int, rate: int) -> None:
        self.hop = hop
        self.onset_s = onset_s = hop / rate  # seconds per onset sample
        self.frame = round(TEMPO_S / onset_s)
        lo, hi = TEMPO_BPM
        self.tempi = np.arange(lo, hi + 1, dtype=np.float64)
        sigma = (hi - lo) / 8.0
        spread = self.tempi[:, None] - self.tempi[None, :]
        self._transition = np.exp(-(spread**2) / (2.0 * sigma**2))
        periods = 60.0 / (onset_s * self.tempi)  # each tempo's beat period, in onset samples
        beta = 60.0 / (onset_s * DEFAULT_BPM)  # the Rayleigh peak at 120 BPM (Davies & Plumbley eq. 8)
        self._rayleigh = periods / beta**2 * np.exp(-(periods**2) / (2.0 * beta**2))
        lags, weights = [], []
        for p in range(1, COMB_ELEMENTS + 1):
            for v in range(1 - p, p):
                lags.append(periods * p + v)
                weights.append(np.full_like(periods, 1.0 / (2 * p - 1)))
        self._comb_lags = np.stack(lags, axis=1)
        self._comb_weights = np.stack(weights, axis=1)
        self._delta = np.full(len(self.tempi), 1.0 / len(self.tempi))
        self.bpm = DEFAULT_BPM
        self.confidence = 0.0
        self.ready = False  # a tempo has been measured this epoch
        self.window: tuple[float, float] | None = None
        self._held: deque[bool] = deque(maxlen=self.frame)
        self.restart()

    # ---- state -----------------------------------------------------------

    def restart(self) -> None:
        """Begin a new epoch: forget the onsets, keep the tempo."""
        size = 2 * self.frame
        self._onsets = np.zeros(size)
        self._scores = np.zeros(size)
        self._count = 0  # values in the buffers
        self.m = -1  # the index of the newest onset this epoch
        self._origin = 0  # the sample index of onset 0's window centre
        self._last_beat = 0
        self._next_beat: int | None = None
        self._held.clear()
        self.ready = False
        self._retune(self.bpm)

    @property
    def held_share(self) -> float:
        """The share of the tempo window's hops that were held."""
        return sum(self._held) / self.frame

    @property
    def degraded(self) -> bool:
        return self.held_share > DEGRADED_ABOVE

    @property
    def within_window(self) -> bool:
        """Whether the tempo is inside the tap window, or there is none."""
        return self.window is None or self.window[0] <= self.bpm <= self.window[1]

    def grid(self) -> tuple[float, float] | None:
        """(anchor, period) in samples: the latest beat, and the samples
        per beat; None before the first tempo of the epoch."""
        if not self.ready:
            return None
        beat = self._next_beat if self._next_beat is not None else self._last_beat
        return self._origin + beat * self.hop, 60.0 / (self.onset_s * self.bpm) * self.hop

    def tap(self, bpm: float) -> None:
        """Seed the tempo at `bpm`, folded into the tracker's octave, and
        keep it within `TAP_WINDOW` of that until `auto`."""
        bpm = fold(bpm)
        self.window = (bpm * (1.0 - TAP_WINDOW), bpm * (1.0 + TAP_WINDOW))
        inside = self._inside()
        if inside.any():
            nearest = int(np.argmin(np.where(inside, np.abs(self.tempi - bpm), np.inf)))
            self._delta = np.zeros_like(self._delta)
            self._delta[nearest] = 1.0
            self.bpm = float(self.tempi[nearest])
            self._retune(self.bpm)

    def auto(self) -> None:
        """Release the tap window."""
        self.window = None

    def at_rate(self, hop: int, rate: int) -> Tracker:
        """A tracker for hops of `hop` samples at `rate`, at the start of an
        epoch, that keeps this one's tempo, confidence and tap window."""
        tracker = Tracker(hop, rate)
        tracker.bpm, tracker.confidence, tracker.window = self.bpm, self.confidence, self.window
        tracker._delta = self._delta.copy()  # one weight per tempo of TEMPO_BPM, at any rate
        tracker.restart()
        return tracker

    # ---- per hop ---------------------------------------------------------

    def push(self, hop: Hop) -> None:
        """Score one hop's onset, predict the next beat half a beat after
        the last, and measure the tempo once a predicted beat has passed."""
        if self.m < 0:
            self._origin = hop.centre
        self.m += 1
        self._held.append(hop.held)
        past = self._past(self._scores, self._count)
        score = (1.0 - ALPHA) * hop.onset + (ALPHA * float(past.max()) if past is not None else 0.0)
        self._store(hop.onset, score)
        if self._next_beat is None and self.m >= self._last_beat + round(self._tau / 2):
            self._next_beat = self._predict()
        elif self._next_beat is not None and self.m >= self._next_beat:
            self._last_beat, self._next_beat = self._next_beat, None
            self._measure_tempo()

    def _store(self, onset: float, score: float) -> None:
        if self._count == len(self._onsets):
            keep = self.frame
            self._onsets[:keep] = self._onsets[-keep:]
            self._scores[:keep] = self._scores[-keep:]
            self._count = keep
        self._onsets[self._count] = onset
        self._scores[self._count] = score
        self._count += 1

    def _past(self, scores: np.ndarray, end: int) -> np.ndarray | None:
        """`W1(v) C(m + v)` for the past window before `end`, or None
        before there is any."""
        lo, hi = self._reach
        start = end - lo
        if end - hi < 0:
            return None
        window = scores[max(start, 0):end - hi + 1]
        return window * self._w1[len(self._w1) - len(window):]

    def _predict(self) -> int:
        """The next beat, as an onset index (Stark eqs. 4–5)."""
        tau = self._tau
        ahead = np.concatenate((self._scores[:self._count], np.zeros(tau)))
        for v in range(tau):
            past = self._past(ahead, self._count + v)
            ahead[self._count + v] = float(past.max()) if past is not None else 0.0
        future = ahead[self._count:] * self._w2
        return self.m + 1 + int(np.argmax(future))

    def _measure_tempo(self) -> None:
        n = min(self._count, self.frame)
        if n < self.frame // 2:
            return
        onsets = self._onsets[self._count - n:self._count]
        kernel = np.ones(THRESHOLD_Q + 1)
        mean = np.convolve(onsets, kernel, "same") / np.convolve(np.ones(n), kernel, "same")
        peaks = np.maximum(onsets - mean, 0.0)
        acf = np.correlate(peaks, peaks, "full")[n - 1:] / (n - np.arange(n))
        comb = (np.interp(self._comb_lags, np.arange(n), acf, right=0.0) * self._comb_weights).sum(axis=1)
        strength = comb * self._rayleigh
        top = float(strength.max())
        self.confidence = 0.0 if top <= 0.0 else 1.0 - float(strength.mean()) / top
        if self.window is not None:
            strength = strength * self._inside()
        delta = (self._transition * self._delta[:, None]).max(axis=0) * strength
        total = float(delta.sum())
        if total > 0.0 and math.isfinite(total):
            self._delta = delta / total
            self.bpm = float(self.tempi[int(np.argmax(self._delta))])
            self._retune(self.bpm)
            self.ready = True

    def _inside(self) -> np.ndarray:
        assert self.window is not None
        lo, hi = self.window
        return (self.tempi >= lo) & (self.tempi <= hi)

    def _retune(self, bpm: float) -> None:
        """The score's windows for a beat period of `bpm`."""
        tau = max(2, round(60.0 / (self.onset_s * bpm)))
        self._tau = tau
        lo, hi = round(2 * tau), max(1, round(tau / 2))
        self._reach = (lo, hi)
        v = -np.arange(lo, hi - 1, -1, dtype=np.float64)  # -lo … -hi, oldest first
        self._w1 = np.exp(-((ETA * np.log(-v / tau)) ** 2) / 2.0)
        ahead = np.arange(1, tau + 1, dtype=np.float64)
        self._w2 = np.exp(-((ahead - tau / 2.0) ** 2) / (2.0 * (tau / 2.0) ** 2))


class Oscillator:
    """`beat_phase` on engine time (module docstring)."""

    def __init__(self, bpm: float = DEFAULT_BPM) -> None:
        self.phase = 0.0
        self.bpm = bpm
        self.correction = 0.0  # the PLL's, within ±MAX_CORRECTION
        self.bias = 0.0  # a held nudge's
        self.beats = 0
        self._t: float | None = None

    @property
    def rate(self) -> float:
        """Beats a second, with the correction and the nudge."""
        return self.bpm / 60.0 * (1.0 + self.correction + self.bias)

    def advance(self, t: float) -> None:
        """Move the phase on to engine time `t`; never back."""
        dt = 0.0 if self._t is None else max(t - self._t, 0.0)
        self._t = t if self._t is None else max(t, self._t)
        self.phase += dt * self.rate
        wraps = math.floor(self.phase)
        self.phase -= wraps
        self.beats += wraps

    def steer(self, error: float) -> None:
        """Correct the rate toward a phase `error`, in beats, ahead."""
        self.correction = min(max(PLL_GAIN * error, -MAX_CORRECTION), MAX_CORRECTION)

    def resync(self) -> None:
        """Jump forward to the wrap: a beat now."""
        if self.phase > 0.0:
            self.phase = 0.0
            self.beats += 1


def fold(bpm: float) -> float:
    """`bpm` times the power of two that puts it in the tracker's octave, `TEMPO_BPM`."""
    lo, hi = TEMPO_BPM
    while bpm > hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def phase_error(target: float, phase: float, step: float = 1.0) -> float:
    """How far the nearest of the points `step` beats apart from `target`
    is ahead of `phase`, in beats, from -step/2 to step/2."""
    return (target - phase + step / 2.0) % step - step / 2.0


__all__ = [
    "DEFAULT_BPM", "FREE_RUN_BELOW", "MAX_CORRECTION", "NUDGE", "TAP_WINDOW", "TEMPO_BPM", "Oscillator", "Tracker",
    "fold", "phase_error",
]
