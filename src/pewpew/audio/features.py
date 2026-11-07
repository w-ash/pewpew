"""The feature sources a run reads from audio: `AudioFeatures` analyses a
source, `ReplayFeatures` plays a feature log back, and `FeatureLog`
writes one.

`AudioFeatures` is a `FeatureSource` (pewpew.features). Its
`before_frame(t)` is a `before` stage of the paced loop, ahead of the
triggers (ADR-010's seat): it applies the controls queued since the last
tick, drains the source, analyses every complete hop, steers the beat
oscillator, and stores the frame for `t`. It contains its own exceptions,
and `at(t)` returns the stored frame, or the last good one, so a reader
never sees an error. The frame keeps ADR-005's fields: `bands`, `volume`,
`bass`, `mid`, `high` and `beat_phase` take their live meanings, and no
field is added (ADR-009, 2026-11-06 amendment "live input"). When the
source's `rate` changes (a live input opened again at another rate), the
analysis starts again at the new rate, as at any new epoch, and the
tracker keeps its tempo and its tap.

Each tick the beat is in one mode:

- `lost`: no samples for `LOST_S`, or a gap that long. Levels go to
  silence and the beat free-runs at the last tempo (the maintainer, 2026-11-06).
- `hold`: the operator holds the tempo; the beat free-runs.
- `searching`: the tracker has no tempo this epoch, or the source cannot
  map samples to engine time yet; the beat free-runs.
- `free-run`: confidence under `FREE_RUN_BELOW`, or the held hops pass
  `DEGRADED_ABOVE` of the tempo window; the beat free-runs at the last
  confident tempo while the levels go on.
- `tapped`, `locked`: the tracker steers the oscillator, within the tap's
  window or freely.

Controls (`control(verb, value)`, any thread) are applied at the next
tick, stamped with its `t`, as triggers are: `tap`, `hold`, `auto`
(release the hold and the tap), `resync` (a beat now), `nudge` (-1, 0 or
1: bias the rate while held) and `sensitivity` (0 to 1, the gate and the
rider).

`tap` takes the intervals between taps, in seconds: the median of the last
four sets the tempo and the tick the phase. The tracker takes the tempo
folded into its octave and corrects it within `TAP_WINDOW`, and the beat
keeps the tapped multiple of it: 172 BPM is twice a tracker at 86. Until
`auto`, the beat keeps to the nearest of the tracker's beats and
off-beats, so a tap moves a beat that locked half a beat off.

`lead` runs the beat ahead of the analysis by the pipeline's latency, and
`delay` (the signed `--audio-delay`) delays the levels by `max(0, delay)`
and shrinks the lead by `delay`.
"""

from __future__ import annotations

import json
import logging
import math
import queue
import statistics
import threading
from bisect import bisect_right
from collections import deque
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO

import numpy as np

from pewpew.audio.analysis import LOST_S, SILENT, Analyser, Levels
from pewpew.audio.beat import FREE_RUN_BELOW, NUDGE, Oscillator, Tracker, fold, phase_error
from pewpew.audio.source import AudioSource
from pewpew.errors import describe_exception
from pewpew.features import N_BANDS, FeatureFrame
from pewpew.jsonfile import is_number, read_run
from pewpew.render import SlotClock

logger = logging.getLogger(__name__)

LEAD_S = 0.035  # the default lead: the pipeline from sound to light [inf: RA-28 §8; M4 measures]
TAP_INTERVALS = 4  # a tap's tempo is the median of this many intervals
TAP_SECONDS = (60.0 / 300.0, 60.0 / 30.0)  # an interval between taps: 30 to 300 BPM
MODES = ("lost", "hold", "searching", "free-run", "tapped", "locked")
VERBS = ("tap", "hold", "auto", "resync", "nudge", "sensitivity")
LOG_VERSION = 1
LEVELS = ("volume", "bass", "mid", "high")  # a frame's levels besides its bands
SCALARS = (*LEVELS, "beat_phase")  # a frame's numbers besides its bands, in field order
_SLACK = 1e-9  # seconds: a delay of whole ticks lands on its tick despite float rounding


def frame_of(levels: Levels, beat_phase: float) -> FeatureFrame:
    """The frame a pattern reads, from levels and a phase."""
    return FeatureFrame(levels.bands, levels.volume, levels.bass, levels.mid, levels.high, beat_phase)


SILENCE = frame_of(SILENT, 0.0)


class AudioFeatures:
    """Features analysed from `source` (module docstring). `fps` is the
    loop's rate; `log`, when given, gets every frame."""

    def __init__(
        self, source: AudioSource, *, fps: float, lead: float = LEAD_S, delay: float = 0.0,
        sensitivity: float = 0.5, log: FeatureLog | None = None,
    ) -> None:
        self.source = source
        self.fps = float(fps)
        self.lead = lead - delay
        self.delay = max(0.0, delay)
        self.analyser = Analyser(source.rate, sensitivity=sensitivity)
        self.tracker = Tracker(self.analyser.hop, source.rate)
        self.oscillator = Oscillator()
        self.log = log
        self.mode = "searching"
        self.t = 0.0  # the engine time of the last tick
        self.error: str | None = None
        self._controls: deque[tuple[str, Any]] = deque()
        self._lock = threading.Lock()
        self._held = False
        self._level = 1.0  # oscillator beats a tracker beat: the power of two a tap sets
        self._heard: float | None = None  # engine time of the last tick with samples
        self._levels: deque[tuple[float, Levels]] = deque()  # (tick, levels), for `delay`
        self._peaks: deque[tuple[float, float]] = deque()  # (tick, peak), the last second
        self._zeros_since: float | None = None  # the first tick of the reads that held only exact zeros
        self._zeros_s = 0.0
        self._frame = SILENCE
        self._tick = 0
        self._counts = {"skipped": 0, "filled": 0, "restarts": 0}
        self._failed: set[str] = set()
        self._state: dict = self._snapshot()

    # ---- any thread ------------------------------------------------------

    def control(self, verb: str, value: object = None) -> str | None:
        """Queue a control for the next tick. Returns why it was refused,
        else None."""
        reason = _check(verb, value)
        if reason is None:
            with self._lock:
                self._controls.append((verb, value))
        return reason

    def state(self) -> dict:
        """The input's view for health and the page; JSON-ready. `zeros_s`
        is how long, in engine seconds, the input has read only exact zeros,
        which a quiet room never gives."""
        return self._state

    # ---- loop thread -----------------------------------------------------

    def at(self, t: float) -> FeatureFrame:
        """The last tick's frame, which `before_frame(t)` stored for `t`;
        silence before the first. Never raises."""
        return self._frame

    def before_frame(self, t: float) -> None:
        """Analyse up to engine time `t` and store its frame. Never raises."""
        try:
            self._advance(float(t))
        except Exception as exc:  # the aura runs on with the last good frame
            key = type(exc).__name__
            self.error = f"audio analysis failed: {describe_exception(exc)}"
            self._state = {**self._state, "error": self.error}
            if key not in self._failed:
                self._failed.add(key)
                logger.exception("audio analysis at t=%s failed; the last frame stands", t)
        self.t = float(t)
        self._tick += 1

    def _advance(self, t: float) -> None:
        self._apply_controls(t)
        blocks = self.source.take(t)
        if self.source.rate != self.analyser.rate:  # a live input opened again at another rate
            self.analyser = Analyser(self.source.rate, sensitivity=self.analyser.sensitivity)
            self.tracker = self.tracker.at_rate(self.analyser.hop, self.source.rate)
        if blocks:
            self._heard = t
            peak = max(float(np.abs(b.samples).max(initial=0.0)) for b in blocks)
            self._peaks.append((t, peak))
            if peak > 0.0:
                self._zeros_since = None
            elif self._zeros_since is None:
                self._zeros_since = t
            self._zeros_s = 0.0 if self._zeros_since is None else t - self._zeros_since
        elif self._heard is None:
            self._heard = t
        while self._peaks and self._peaks[0][0] <= t - 1.0:
            self._peaks.popleft()
        fed = self.analyser.feed(blocks)
        self._counts["skipped"] += fed.skipped
        self._counts["filled"] += fed.filled
        if fed.restarted:
            self._counts["restarts"] += 1
            self.tracker.restart()
        for hop in fed.hops:
            self.tracker.push(hop)
        lost = fed.restarted or t - self._heard >= LOST_S
        self.oscillator.advance(t)
        self.mode = self._steer(t, lost, bool(fed.hops))
        if lost:
            self._levels.clear()
            levels = SILENT
        else:
            if fed.hops:
                self._levels.append((t, fed.hops[-1].levels))
            levels = self._delayed(t)
        frame = self._frame = frame_of(levels, self.oscillator.phase)
        self.error = None
        self._state = self._snapshot()
        if self.log is not None:
            self.log.write(self._tick, t, frame, self._state)

    def _steer(self, t: float, lost: bool, hopped: bool) -> str:
        """The beat's mode this tick, steering the oscillator when the
        tracker leads it."""
        osc, tracker = self.oscillator, self.tracker
        grid = tracker.grid()
        mapped = None if grid is None else self._grid_times(*grid)
        if lost:
            mode = "lost"
        elif self._held:
            mode = "hold"
        elif mapped is None:
            mode = "searching"
        elif tracker.degraded or tracker.confidence < FREE_RUN_BELOW or not tracker.within_window:
            mode = "free-run"
        else:
            mode = "tapped" if tracker.window is not None else "locked"
        if mode not in ("tapped", "locked") or mapped is None:
            osc.correction = 0.0
            return mode
        if hopped:
            anchor, period = mapped
            beat = period / self._level
            osc.bpm = 60.0 / beat
            target = ((t + self.lead - anchor) / beat) % 1.0
            step = min(self._level / 2.0, 1.0) if mode == "tapped" else 1.0  # the tracker's half beats
            osc.steer(phase_error(target, osc.phase, step))
        return mode

    def _grid_times(self, anchor: float, period: float) -> tuple[float, float] | None:
        """The tracker's grid in engine time: (the anchor beat's time, the
        seconds per beat), or None while the source cannot map samples."""
        a, b = self.source.time(anchor), self.source.time(anchor + period)
        if a is None or b is None or b <= a:
            return None
        return a, b - a

    def _delayed(self, t: float) -> Levels:
        """The newest levels at least `delay` old."""
        levels, due = self._levels, t - self.delay + _SLACK
        while len(levels) > 1 and levels[1][0] <= due:
            levels.popleft()
        return levels[0][1] if levels and levels[0][0] <= due else SILENT

    def _apply_controls(self, t: float) -> None:
        with self._lock:
            controls = list(self._controls)
            self._controls.clear()
        for verb, value in controls:
            if verb == "tap":
                intervals = [float(v) for v in value][-TAP_INTERVALS:]
                bpm = 60.0 / statistics.median(intervals)
                self.oscillator.bpm = bpm
                self.oscillator.correction = 0.0
                self.oscillator.resync()
                self.tracker.tap(bpm)
                self._level = bpm / fold(bpm)
            elif verb == "hold":
                self._held = True
            elif verb == "auto":
                self._held = False
                self._level = 1.0
                self.tracker.auto()
            elif verb == "resync":
                self.oscillator.resync()
            elif verb == "nudge":
                self.oscillator.bias = NUDGE * float(value)
            else:
                self.analyser.sensitivity = float(value)
            logger.info("audio %s%s at t=%.3f", verb, "" if value is None else f" {value}", t)

    def _snapshot(self) -> dict:
        peak = max((p for _, p in self._peaks), default=0.0)
        tracker = self.tracker
        return {
            "input": self.source.state(),
            "mode": self.mode,
            "bpm": round(self.oscillator.bpm, 2),
            "confidence": round(tracker.confidence, 3),
            "peak_db": round(20.0 * math.log10(peak), 1) if peak > 0.0 else None,
            "held": round(tracker.held_share, 3),
            "zeros_s": round(self._zeros_s, 3),
            **self._counts,
            "sensitivity": self.analyser.sensitivity,
            "error": self.error,
        }


def play(features: AudioFeatures, seconds: float) -> Iterator[tuple[float, FeatureFrame, dict]]:
    """Each tick's engine time, frame and state for the next `seconds` of
    engine time at the features' fps, as the paced loop runs it
    (pewpew.pace)."""
    clock = SlotClock(features.fps, start=features.t)
    for _ in range(math.ceil(seconds * features.fps)):
        t = clock.advance()
        features.before_frame(t)
        yield t, features.at(t), features.state()


def beat_times(ticks: Iterable[tuple[float, FeatureFrame]]) -> list[float]:
    """The engine times the beat phase wrapped, between ticks, found by
    the phase's rate over the tick it wrapped in."""
    out: list[float] = []
    last: tuple[float, float] | None = None
    for t, frame in ticks:
        phase = frame.beat_phase
        if last is not None and phase < last[1]:
            t0, p0 = last
            out.append(t0 + (1.0 - p0) / (phase + 1.0 - p0) * (t - t0))
        last = (t, phase)
    return out


def _check(verb: object, value: object) -> str | None:
    """Why a control is malformed, or None."""
    if verb not in VERBS:
        return f"unknown audio control {verb!r}; controls: {', '.join(VERBS)}"
    if verb == "tap":
        lo, hi = TAP_SECONDS
        if not isinstance(value, (list, tuple)) or not value or not all(
                is_number(v) and lo <= v <= hi for v in value):
            return (f"tap takes the seconds between taps, a list of one or more numbers from {lo:g} to {hi:g} "
                    f"(30 to 300 BPM), got {value!r}")
    elif verb == "nudge":
        if value not in (-1, 0, 1) or isinstance(value, bool):
            return f"nudge takes -1 (slower), 0 (let go) or 1 (faster), got {value!r}"
    elif verb == "sensitivity":
        if not is_number(value) or not 0.0 <= value <= 1.0:
            return f"sensitivity takes a number from 0 to 1, got {value!r}"
    elif value is not None:
        return f"{verb} takes no value, got {value!r}"
    return None


# ---- the feature log ------------------------------------------------------


class FeatureLog:
    """Each frame as one JSON line, written by a thread of its own from
    `start` to `close`, so the loop never waits on the disk. The first
    line is the run's header. `hours` caps the log in engine time; a write
    that fails, or one past the cap, ends the log with one warning, never
    the run."""

    def __init__(self, file: TextIO, header: Mapping[str, Any], *, hours: float = 1.0) -> None:
        self._file = file
        self._cap = hours * 3600.0
        self._first: float | None = None
        self._queue: queue.SimpleQueue[str | None] = queue.SimpleQueue()
        self._open = True
        self._thread = threading.Thread(target=self._drain, name="pewpew-feature-log", daemon=True)
        self._queue.put(json.dumps({"run": {"version": LOG_VERSION, **header}}) + "\n")

    def start(self) -> None:
        """Start the writer thread."""
        self._thread.start()

    def write(self, tick: int, t: float, frame: FeatureFrame, state: Mapping[str, Any]) -> None:
        """Queue the frame at engine time `t`. Loop thread."""
        if not self._open:
            return
        if self._first is None:
            self._first = t
        if t - self._first > self._cap:
            logger.warning("the feature log reached its cap of %g hours; it stops here", self._cap / 3600.0)
            self._open = False
            return
        self._queue.put(json.dumps(record(tick, t, frame, state), separators=(",", ":")) + "\n")

    def close(self) -> None:
        """Write what is queued, then close the file."""
        self._open = False
        self._queue.put(None)
        if self._thread.ident is None:
            self._drain()  # never started: write the queue here
        else:
            self._thread.join()

    def _drain(self) -> None:
        failed = False
        while (line := self._queue.get()) is not None:
            if failed:
                continue
            try:
                self._file.write(line)
                if self._queue.empty():
                    self._file.flush()
            except (OSError, ValueError):  # ValueError: the file was closed
                logger.warning("cannot write the feature log; it stops here", exc_info=True)
                failed = True
        try:
            self._file.close()
        except OSError:
            logger.warning("cannot close the feature log", exc_info=True)


def record(tick: int, t: float, frame: FeatureFrame, state: Mapping[str, Any]) -> dict:
    """One frame as a log record: exact floats, so a replay is byte-identical."""
    return {
        "tick": tick, "t": t, "bands": frame.bands.tolist(), **{name: getattr(frame, name) for name in SCALARS},
        "mode": state.get("mode"), "bpm": state.get("bpm"), "confidence": state.get("confidence"),
    }


class ReplayFeatures:
    """A feature log played back: `at(t)` is the frame of the last record
    at or before `t`, so another fps or a skipped slot still gets a frame,
    and before the first record it is silence. Reads the log's last run."""

    def __init__(self, path: Path) -> None:
        records = read_run(path)
        if not records or not isinstance(records[0], dict) or not isinstance(records[0].get("run"), dict):
            raise ValueError('a feature log starts with its run header, {"run": {...}}; this one does not')
        self.header: dict = records[0]["run"]
        times: list[float] = []
        frames: list[FeatureFrame] = []
        for n, rec in enumerate(records[1:], start=2):
            frame = _replayed(rec, n)
            if times and rec["t"] < times[-1]:
                raise ValueError(f"record {n}: t goes back from {times[-1]} to {rec['t']}")
            times.append(rec["t"])
            frames.append(frame)
        if not frames:
            raise ValueError("the feature log holds no frames")
        self._times, self._frames = times, frames

    @property
    def seconds(self) -> float:
        return self._times[-1]

    def at(self, t: float) -> FeatureFrame:
        i = bisect_right(self._times, t) - 1
        return self._frames[i] if i >= 0 else SILENCE


def _replayed(rec: object, n: int) -> FeatureFrame:
    """A log record's frame; ValueError naming the record when it is malformed."""
    if not isinstance(rec, dict) or not is_number(rec.get("t")) or not all(is_number(rec.get(f)) for f in SCALARS):
        raise ValueError(f"record {n} is not a frame: it needs t, bands, {', '.join(SCALARS)} as numbers")
    bands = rec.get("bands")
    if not isinstance(bands, list) or len(bands) != N_BANDS or not all(is_number(b) for b in bands):
        raise ValueError(f"record {n}: bands is a list of {N_BANDS} numbers")
    array = np.array(bands, np.float32)
    array.setflags(write=False)
    volume, bass, mid, high, beat_phase = (float(rec[f]) for f in SCALARS)
    return FeatureFrame(array, volume, bass, mid, high, beat_phase)


__all__ = [
    "LEAD_S", "LEVELS", "MODES", "SCALARS", "SILENCE", "VERBS", "AudioFeatures", "FeatureLog", "ReplayFeatures",
    "beat_times", "frame_of", "play", "record",
]
