"""Where audio samples come from: the `AudioSource` protocol, `ArraySource`
for an array or a WAV file, `read_wav`, and `mono`, the mixdown of a file
and of a live input.

A source gives mono float32 samples at its native rate, with no
resampling. `take(t)` drains the samples due by engine time `t` as
`Block`s, each with the index of its first sample; a jump in that index
is a gap. `time(index)` maps a sample index to engine time, so the beat
oscillator can compare the tracker's beats with engine time: exactly for
a file, by a fitted line (`pewpew.audio.clock.SampleClock`) for a live
input. `state()` is the input's part of the health and page view.

`ArraySource` is deterministic: the samples due at `t` are those up to
`floor(t * rate)`, so the same samples and the same ticks give the same
blocks. A live device and a capture node implement the same protocol
(ADR-009, 2026-11-06 amendments), and `LiveSource` too: a run audits one
before it starts its supervisor, and stops it after the loop.
"""

from __future__ import annotations

import math
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

# The lowest rate the analysis supports: its 16 bands reach 16 kHz only at
# 32 kHz and above, and a lower rate leaves the top bands empty.
MIN_RATE = 8000
_TAGS = (1, 3, 0xFFFE)  # PCM, IEEE float and the extensible header: what `wave` may read
_WIDTHS = (1, 2, 3, 4)  # the sample widths, in bytes, that `_pcm` reads


@dataclass(frozen=True, slots=True)
class Block:
    """Samples drained at one tick: `samples` (mono float32, read-only)
    start at sample index `start`."""

    start: int
    samples: np.ndarray

    @property
    def end(self) -> int:
        """The index one past the last sample."""
        return self.start + len(self.samples)


class AudioSource(Protocol):
    """Mono float32 samples at the native `rate`; no resampling. A live
    input that opens again at another rate changes `rate` in the `take`
    that gives its first block, which starts a new epoch."""

    rate: int

    def take(self, t: float) -> list[Block]:
        """The blocks due by engine time `t`, in index order. Loop thread."""
        ...

    def time(self, index: float) -> float | None:
        """The engine time of sample `index`, or None while the source
        cannot map it yet."""
        ...

    def state(self) -> dict:
        """JSON-ready: at least `name` and `kind`. Any thread."""
        ...


@runtime_checkable
class LiveSource(AudioSource, Protocol):
    """A live input: one of this computer's inputs or a capture node. Its
    supervisor thread opens it; opening it is a privacy act, so a run calls
    `audit` first, then `start`, and `stop` once the loop has stopped."""

    name: str
    kind: str

    def describe(self) -> str:
        """One line on what the run would open, for `run --dry-run`."""
        ...

    def audit(self, argv: list[str], *, feature_log: Path | None = None) -> Path:
        """Append the `audio-input` audit record; returns the log's path.
        Raises OSError when it cannot be written: then nothing opens."""
        ...

    def start(self) -> None:
        """Start the supervisor thread, which runs `step` until `stop`."""
        ...

    def step(self) -> None:
        """One pass of the supervisor; tests and the bench call it directly."""
        ...

    def stop(self) -> None: ...


class ArraySource:
    """A read-only copy of `samples` played on engine time: sample i is
    due at `i / rate`. With `loop`, the samples repeat without end;
    without it, the source gives nothing after its last sample."""

    def __init__(self, samples: np.ndarray, rate: int, *, name: str = "array", kind: str = "array",
                 loop: bool = False) -> None:
        samples = np.array(samples, dtype=np.float32)
        if samples.ndim != 1 or not len(samples):
            raise ValueError(f"an audio source needs a non-empty 1-D array of samples, got shape {samples.shape}")
        if not np.isfinite(samples).all():
            raise ValueError("audio samples must be finite")
        if rate < MIN_RATE:
            raise ValueError(f"the sample rate must be at least {MIN_RATE} Hz, got {rate}")
        self.samples = samples
        self.samples.setflags(write=False)
        self.rate = int(rate)
        self.name = name
        self.kind = kind
        self.loop = loop
        self._next = 0

    @property
    def seconds(self) -> float:
        """The length of one play of the samples."""
        return len(self.samples) / self.rate

    def take(self, t: float) -> list[Block]:
        due = max(self._next, math.floor(t * self.rate))
        if not self.loop:
            due = min(due, len(self.samples))
        if due <= self._next:
            return []
        start, self._next = self._next, due
        return [Block(start, self._slice(start, due))]

    def time(self, index: float) -> float | None:
        return index / self.rate

    def state(self) -> dict:
        return {"name": self.name, "kind": self.kind, "rate": self.rate}

    def _slice(self, start: int, end: int) -> np.ndarray:
        n = len(self.samples)
        if end <= n:
            return self.samples[start:end]
        picks = np.arange(start, end) % n
        out = self.samples[picks]
        out.setflags(write=False)
        return out


def read_wav(path: Path, channel: int | None = None) -> tuple[np.ndarray, int]:
    """The samples of a WAV file as mono float32 in -1 to 1, and its rate:
    one `channel`, or the mean of all. Raises ValueError, in words that
    name the cause, for a file `wave` cannot read; OSError when the file
    cannot be opened."""
    with open(path, "rb") as f:
        head = f.read(36)
    if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        raise ValueError("not a WAV file (it has no RIFF/WAVE header)")
    try:
        with wave.open(str(path), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            data = w.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise ValueError(_wave_refusal(head, exc)) from None
    if width not in _WIDTHS:
        raise ValueError(f"this WAV holds {8 * width}-bit samples; pewpew reads 8-, 16-, 24- and 32-bit PCM")
    if rate < MIN_RATE:
        raise ValueError(f"the sample rate is {rate} Hz; the analysis needs at least {MIN_RATE} Hz")
    if not frames:
        raise ValueError("the file holds no samples")
    if channel is not None and not 0 <= channel < channels:
        raise ValueError(f"the file has {channels} channel(s), numbered from 0; channel {channel} is not one")
    frames = len(data) // (width * channels)  # a truncated file reads short
    return mono(_pcm(data[: frames * width * channels], width).reshape(frames, channels), channel), rate


def mono(frames: np.ndarray, channel: int | None = None) -> np.ndarray:
    """The (n, channels) `frames` as n contiguous float32 samples: one
    `channel`, or the mean of all."""
    picked = frames[:, channel] if channel is not None else frames.mean(axis=1, dtype=np.float64)
    return np.ascontiguousarray(picked, dtype=np.float32)


def _pcm(data: bytes, width: int) -> np.ndarray:
    """Little-endian PCM of `width` bytes a sample, scaled to -1 to 1."""
    if width == 1:  # 8-bit WAV is unsigned
        return (np.frombuffer(data, np.uint8).astype(np.float64) - 128.0) / 128.0
    if width == 3:
        raw = np.frombuffer(data, np.uint8).reshape(-1, 3).astype(np.int32)
        ints = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        ints = np.where(ints >= 1 << 23, ints - (1 << 24), ints)
        return ints / float(1 << 23)
    dtype = {2: "<i2", 4: "<i4"}[width]
    return np.frombuffer(data, dtype).astype(np.float64) / float(1 << (8 * width - 1))


def _wave_refusal(head: bytes, exc: Exception) -> str:
    """Why `wave` refused a RIFF/WAVE file, naming the format when the
    header gives it."""
    tag = int.from_bytes(head[20:22], "little") if head[12:16] == b"fmt " and len(head) >= 22 else None
    if tag == 3 and sys.version_info < (3, 15):
        return "this WAV holds IEEE float samples, which Python's wave module reads from 3.15; save it as PCM"
    if tag == 0xFFFE and sys.version_info < (3, 12):
        return "this WAV uses the extensible header, which Python's wave module reads from 3.12; save it as plain PCM"
    if tag is not None and tag not in _TAGS:
        return f"this WAV's format tag is {tag:#06x}, not PCM; save it as PCM"
    return f"cannot read this WAV: {exc}"
