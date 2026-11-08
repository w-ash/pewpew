"""Test signals, made in the test from a seed: no audio file is committed
(RA-28 §5). Each gives mono float32 samples at `rate`."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

from pewpew.audio import ArraySource, AudioFeatures, Block
from pewpew.audio.clock import SampleClock
from pewpew.audio.features import SCALARS, beat_times, play
from pewpew.features import FeatureFrame

RATE = 48000


def click_times(bpm: float, seconds: float, start: float = 0.25) -> np.ndarray:
    """The times of a click track's beats."""
    return np.arange(start, seconds, 60.0 / bpm)


def clicks(times: np.ndarray, seconds: float, rate: int = RATE, *, seed: int = 0, noise: float = 0.01,
           level: float = 0.5) -> np.ndarray:
    """A short decaying 2 kHz burst at each of `times`, over seeded noise."""
    out = np.random.default_rng(seed).normal(0.0, noise, int(seconds * rate))
    n = int(0.03 * rate)
    k = np.arange(n) / rate
    burst = level * np.sin(2 * math.pi * 2000.0 * k) * np.exp(-k / 0.006)
    for at in times:
        i = round(at * rate)
        out[i:i + n] += burst[: len(out) - i]
    return out.astype(np.float32)


def click_track(bpm: float, seconds: float, rate: int = RATE, *, seed: int = 0) -> np.ndarray:
    return clicks(click_times(bpm, seconds), seconds, rate, seed=seed)


def kick_loop(bpm: float, seconds: float, rate: int = RATE, *, seed: int = 0) -> np.ndarray:
    """A kick on every beat and a hat on every off-beat, over seeded noise."""
    rng = np.random.default_rng(seed)
    out = rng.normal(0.0, 0.005, int(seconds * rate))
    beat = 60.0 / bpm
    kn, hn = int(0.15 * rate), int(0.04 * rate)
    k = np.arange(kn) / rate
    kick = 0.8 * np.sin(2 * math.pi * (50.0 * k + 60.0 * (1 - np.exp(-k / 0.02)))) * np.exp(-k / 0.08)
    hat = 0.15 * rng.normal(0.0, 1.0, hn) * np.exp(-np.arange(hn) / rate / 0.01)
    for at in np.arange(0.25, seconds, beat):
        for sound, when in ((kick, at), (hat, at + beat / 2)):
            i = round(when * rate)
            if i < len(out):
                out[i:i + len(sound)] += sound[: len(out) - i]
    return out.astype(np.float32)


def sine(hz: float, seconds: float, rate: int = RATE, level: float = 0.5) -> np.ndarray:
    return (level * np.sin(2 * math.pi * hz * np.arange(int(seconds * rate)) / rate)).astype(np.float32)


def noise(seconds: float, rate: int = RATE, *, seed: int = 0, level: float = 0.2) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, level, int(seconds * rate)).astype(np.float32)


def write_wav(path: Path, samples: np.ndarray, rate: int = RATE, *, width: int = 2, channels: int = 1) -> Path:
    """`samples` as a PCM WAV of `width` bytes a sample, the same on every channel."""
    scaled = np.clip(samples, -1.0, 1.0)
    if width == 1:
        data = np.round(scaled * 127.0 + 128.0).astype(np.uint8).tobytes()
    else:
        ints = np.round(scaled * (2 ** (8 * width - 1) - 1)).astype(np.int64)
        data = b"".join(int(v).to_bytes(width, "little", signed=True) for v in ints) if width == 3 else (
            ints.astype({2: "<i2", 4: "<i4"}[width]).tobytes())
    if channels > 1:
        frame = np.frombuffer(data, np.uint8).reshape(-1, width)
        data = np.repeat(frame, channels, axis=0).tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(data)
    return path


def ticks(features: AudioFeatures, seconds: float) -> list[tuple[float, FeatureFrame]]:
    """Each tick's (t, frame) for `seconds` of engine time, as the loop runs it."""
    return [(t, frame) for t, frame, _ in play(features, seconds)]


def beats(features: AudioFeatures, seconds: float) -> np.ndarray:
    """The beat times a program sees over `seconds`."""
    return np.array(beat_times(ticks(features, seconds)))


def frame_bytes(frame: FeatureFrame) -> bytes:
    """A frame's bands and numbers as bytes, to compare frames byte for byte."""
    return frame.bands.tobytes() + np.array([getattr(frame, name) for name in SCALARS]).tobytes()


def matched(found: np.ndarray, truth: np.ndarray, window: float = 0.07) -> float:
    """The F-measure of `found` beats against `truth` within `window` seconds, each true beat matched once."""
    if not len(found) or not len(truth):
        return 0.0
    used, hits = set(), 0
    for x in found:
        k = int(np.argmin(np.abs(truth - x)))
        if abs(truth[k] - x) <= window and k not in used:
            used.add(k)
            hits += 1
    precision, recall = hits / len(found), hits / len(truth)
    return 0.0 if not hits else 2 * precision * recall / (precision + recall)


class JitterSource(ArraySource):
    """`samples` delivered as a live input would be: in blocks of `block`
    samples that arrive after a seeded delay, mapped to engine time by a
    `SampleClock`. Deterministic for one seed."""

    def __init__(self, samples: np.ndarray, rate: int = RATE, *, fps: float = 60.0, block: int = 480,
                 seed: int = 0, delay: float = 0.004, jitter: float = 0.003) -> None:
        super().__init__(samples, rate, name="jitter", kind="test")
        self.clock = SampleClock(rate, fps)
        self._block = block
        self._rng = np.random.default_rng(seed)
        self._delay, self._jitter = delay, jitter
        self._waiting: list[Block] = []
        self._arrive: list[float] = []

    def take(self, t: float) -> list[Block]:
        for b in super().take(t - self._delay):
            for start in range(0, len(b.samples), self._block):
                self._waiting.append(Block(b.start + start, b.samples[start:start + self._block]))
                # In order, as a USB device delivers: never before the block ahead of it.
                last = self._arrive[-1] if self._arrive else -np.inf
                self._arrive.append(max(last, t + float(self._rng.exponential(self._jitter))))
        ready = [b for b, at in zip(self._waiting, self._arrive) if at <= t]
        keep = [(b, at) for b, at in zip(self._waiting, self._arrive) if at > t]
        self._waiting, self._arrive = [b for b, _ in keep], [at for _, at in keep]
        for b in ready:
            self.clock.observe(b.end, t)
        return sorted(ready, key=lambda b: b.start)

    def time(self, index: float) -> float | None:
        return self.clock.time(index)
