"""The analysis on the sample clock: hops, levels and the onset detection
function, with the gap and backlog rules.

Hop n of an epoch starts at sample `start + n * hop`, where `hop` is
`HOP_S` seconds of samples (480 at 48 kHz, 441 at 44.1 kHz); the first hop
analysed is the first whose window is full. The analysis
counts samples, never wall time, so the same samples give the same hops
(RA-28 §4). Each hop gives:

- **levels** from the newest `size // 2` samples (1024 at 48 kHz, the maintainer's
  latency lever): 16 bands on the mel scale from 40 Hz to 16 kHz, the
  volume, and bass, mid and high split at 250 and 3000 Hz (ADR-009's
  edges). One gain rider and one noise gate stand behind one
  `sensitivity` knob: a level is 1 at the rider and 0 `RANGE_DB` below
  it, and every level is 0 while the gate is shut. The levels leave out
  the input's DC offset, the mean of the hops' new samples over about
  `DC_S`: a 10 ms hop holds whole cycles of 100 Hz and its multiples, so
  bass averages out of it, and an offset is no sound.
- **onset**, the complex spectral difference of the `size`-sample window
  (2048 at 48 kHz), the detection function of Stark et al. [S1750] §2.1:
  the distance of each bin from the bin its two previous frames predict
  (Bello et al. [S1752] §II-B.3).

Gaps and backlog (ADR-009, 2026-11-06 amendment "live input"):

- A gap under `LOST_S` is filled with counted zeros, and every hop whose
  onset reads a window that touches the gap holds its onset and its
  levels: with a 2048-sample window and a 480-sample hop, one lost 10 ms
  block holds 7 hops.
- A gap of `LOST_S` or more restarts the epoch at the next sample, with no
  zero-fill: the grid waits for a full window, and the first two hops hold
  until two prior frames exist.
- One `feed` analyses at most `MAX_HOPS` hops. Older due hops are skipped
  and counted: under `LOST_S` of them hold, more restart the epoch.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

from pewpew.audio.source import Block
from pewpew.features import N_BANDS
from pewpew.kit import fade

HOP_S = 0.01
LOST_S = 0.5
MAX_HOPS = 20
BAND_HZ = (40.0, 16000.0)
BASS_HZ = 250.0
HIGH_HZ = 3000.0
RANGE_DB = 36.0  # a level runs from 0, this far below the rider, to 1 at it
GATE_DB = -60.0  # the gate opens above this broadband level at sensitivity 0.5
GATE_SPAN_DB = 40.0  # sensitivity 0 to 1 moves the gate this far, down
HYSTERESIS_DB = 3.0  # the gate shuts this far below where it opens
RIDER_ATTACK_S = 0.3  # the rider's time constant rising to a louder level
RIDER_FALL_DB_S = 3.0  # how fast the rider falls toward a quieter level
RIDER_HEADROOM_DB = 20.0  # the rider never falls below the gate plus this
DC_S = 1.0  # the time constant of the input's DC offset, which the levels take away [inf]
_FLOOR = 1e-12  # power floor, so silence has a finite level


@dataclass(frozen=True, slots=True)
class Levels:
    """The levels a frame shows: 0 to 1."""

    bands: np.ndarray  # (N_BANDS,) float32, read-only
    volume: float
    bass: float
    mid: float
    high: float


def _silent() -> Levels:
    bands = np.zeros(N_BANDS, np.float32)
    bands.setflags(write=False)
    return Levels(bands, 0.0, 0.0, 0.0, 0.0)


SILENT = _silent()


@dataclass(frozen=True, slots=True)
class Hop:
    """One hop of the analysis. `end` is one past its newest sample;
    `centre` is the middle of its onset window, the sample its onset is
    timed at."""

    end: int
    centre: int
    onset: float
    levels: Levels
    held: bool


@dataclass(frozen=True, slots=True)
class Fed:
    """What one `feed` gave: its hops in order, whether the epoch
    restarted before the first of them, and the hops skipped and samples
    zero-filled."""

    hops: list[Hop] = field(default_factory=list)
    restarted: bool = False
    skipped: int = 0
    filled: int = 0


def restart_gap(rate: int) -> int:
    """The jump in a source's sample index that makes the analysis restart
    its grid: `LOST_S` of samples. A live source adds it at a new epoch (an
    overflow, a reopen, a node's reboot), whose samples it cannot place."""
    return math.ceil(LOST_S * rate)


def window_size(rate: int) -> int:
    """The onset window: the power of two nearest 2048 samples at 48 kHz."""
    return 1 << round(math.log2(rate * 2048 / 48000))


def band_edges(rate: int, size: int) -> np.ndarray:
    """The rfft bin where each of the `N_BANDS` mel bands starts, and one
    past the last: each band at least one bin wide below the Nyquist
    frequency, and empty above it."""
    lo, hi = (2595.0 * math.log10(1.0 + f / 700.0) for f in BAND_HZ)
    hz = 700.0 * (10.0 ** (np.linspace(lo, hi, N_BANDS + 1) / 2595.0) - 1.0)
    edges = np.round(hz * size / rate).astype(int)
    for k in range(1, len(edges)):  # each band at least one bin
        edges[k] = max(edges[k], edges[k - 1] + 1)
    return np.minimum(edges, size // 2 + 1)  # a band past the Nyquist frequency is empty


class Analyser:
    """Blocks in, hops out (the module docstring). Loop thread."""

    def __init__(self, rate: int, *, sensitivity: float = 0.5) -> None:
        self.rate = int(rate)
        self.hop = round(rate * HOP_S)
        self.size = window_size(rate)
        self.level_size = self.size // 2
        self.sensitivity = sensitivity
        self._onset_window = np.hanning(self.size)
        self._level_window = np.hanning(self.level_size)
        # Power of a full-scale sine's peak bin, so a level reads in dBFS.
        self._ref = (self.level_size * self._level_window.mean() / 2.0) ** 2
        self._edges = band_edges(rate, self.level_size)
        freqs = np.fft.rfftfreq(self.level_size, 1.0 / rate)
        self._splits = [freqs < BASS_HZ, (freqs >= BASS_HZ) & (freqs < HIGH_HZ), freqs >= HIGH_HZ]
        self._samples = np.zeros(0, np.float32)
        self._base = 0  # the index of `_samples[0]`
        self._next_end: int | None = None  # the end of the next hop; None before the first block
        self._frames: list[np.ndarray] = []  # the last two onset spectra
        self._held_spans: list[tuple[int, int]] = []  # zero-filled [start, end) spans
        self._onset = 0.0
        self._levels = SILENT
        self._rider: float | None = None
        self._open = False
        self._dc = 0.0  # the mean of the analysed hops' new samples over about `DC_S`

    @property
    def expected(self) -> int | None:
        """The index the next block should start at, or None before the first."""
        return None if self._next_end is None else self._base + len(self._samples)

    def feed(self, blocks: Iterable[Block]) -> Fed:
        """Analyse every hop the blocks complete, by the gap and backlog rules."""
        restarted, filled = False, 0
        for block in blocks:
            expected = self.expected
            if expected is None or block.start >= expected + LOST_S * self.rate or block.end <= self._base:
                restarted |= expected is not None
                self._restart(block.start)
            elif block.start > expected:
                gap = block.start - expected
                self._append(np.zeros(gap, np.float32))
                self._held_spans.append((expected, block.start))
                filled += gap
            elif block.start < expected:  # an overlap: keep only the new samples
                block = Block(expected, block.samples[expected - block.start:])
            self._append(block.samples)
        return self._run(restarted, filled)

    def _restart(self, start: int) -> None:
        self._samples = np.zeros(0, np.float32)
        self._base = start
        self._next_end = start + -(-self.size // self.hop) * self.hop  # the first full window on the grid
        self._frames.clear()
        self._held_spans.clear()

    def _append(self, samples: np.ndarray) -> None:
        self._samples = np.concatenate((self._samples, samples)) if len(self._samples) else samples

    def _run(self, restarted: bool, filled: int) -> Fed:
        if self._next_end is None:  # no block yet
            return Fed(restarted=restarted, filled=filled)
        have = self._base + len(self._samples)
        due = (have - self._next_end) // self.hop + 1 if have >= self._next_end else 0
        hops: list[Hop] = []
        skipped = max(0, due - MAX_HOPS)
        if skipped:
            if skipped * self.hop >= LOST_S * self.rate:
                restarted = True  # the samples stay contiguous, so a zero-filled span still holds its hops
                self._frames.clear()
            else:
                hops += [self._hold(self._next_end + k * self.hop) for k in range(skipped)]
                self._frames.clear()  # the next frames have no fresh predecessors
            self._next_end += skipped * self.hop
        for _ in range(due - skipped):
            hops.append(self._analyse(self._next_end))
            self._next_end += self.hop
        keep = self._next_end - self.size  # the oldest sample the next window reads
        if keep > self._base:
            self._samples = self._samples[keep - self._base:]
            self._base = keep
        return Fed(hops, restarted, skipped, filled)

    def _hold(self, end: int) -> Hop:
        return Hop(end, end - self.size // 2, self._onset, self._levels, True)

    def _analyse(self, end: int) -> Hop:
        window = self._samples[end - self.size - self._base:end - self._base].astype(np.float64)
        spectrum = np.fft.rfft(window * self._onset_window)
        frames = self._frames
        onset = None
        if len(frames) == 2:
            prev, older = frames
            predicted = np.abs(prev) * np.exp(1j * (2.0 * np.angle(prev) - np.angle(older)))
            onset = float(np.abs(spectrum - predicted).sum())
        frames.append(spectrum)
        if len(frames) > 2:
            del frames[0]
        if onset is None or self._touches_gap(end):
            return self._hold(end)
        self._onset = onset
        self._levels = self._measure(window[-self.level_size:])
        return Hop(end, end - self.size // 2, onset, self._levels, False)

    def _touches_gap(self, end: int) -> bool:
        """Whether hop `end`'s onset reads a window, its own or one of the
        two before, that touches a zero-filled span."""
        reach = self.size + 2 * self.hop
        self._held_spans = [(a, b) for a, b in self._held_spans if end - reach < b]
        return any(a < end for a, _ in self._held_spans)

    def _measure(self, samples: np.ndarray) -> Levels:
        """The levels of the newest samples, through the rider and the gate."""
        self._dc += (float(samples[-self.hop:].mean()) - self._dc) * (1.0 - fade(HOP_S, DC_S))
        power = np.abs(np.fft.rfft((samples - self._dc) * self._level_window)) ** 2 / self._ref
        total = float(power.sum())
        volume_db = _db(total)
        gate = GATE_DB - GATE_SPAN_DB * (self.sensitivity - 0.5)
        self._open = volume_db > (gate - HYSTERESIS_DB if self._open else gate)
        floor = gate + RIDER_HEADROOM_DB
        rider = max(volume_db, floor) if self._rider is None else self._rider
        if volume_db > rider:
            rider += (volume_db - rider) * (1.0 - fade(HOP_S, RIDER_ATTACK_S))
        else:
            rider = max(rider - RIDER_FALL_DB_S * HOP_S, volume_db)
        self._rider = rider = max(rider, floor)
        if not self._open:
            return SILENT
        running = np.concatenate(([0.0], np.cumsum(power)))
        sums = running[self._edges[1:]] - running[self._edges[:-1]]

        def level(p: float) -> float:
            return min(max(1.0 + (_db(p) - rider) / RANGE_DB, 0.0), 1.0)

        bands = np.array([level(p) for p in sums], np.float32)
        bands.setflags(write=False)
        bass, mid, high = (level(float(power[split].sum())) for split in self._splits)
        return Levels(bands, level(total), bass, mid, high)


def _db(power: float) -> float:
    return 10.0 * math.log10(max(power, _FLOOR))


__all__ = [
    "HOP_S", "LOST_S", "MAX_HOPS", "SILENT", "Analyser", "Fed", "Hop", "Levels", "band_edges", "restart_gap",
    "window_size",
]
