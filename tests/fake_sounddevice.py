"""A stand-in for the sounddevice module (pewpew[audio]), so no test opens
a real input. A test puts it in `sys.modules["sounddevice"]`.

Like PortAudio, it lists the inputs only when it starts: `plug` and
`unplug` change what is connected, and `query_devices` shows the change
only after `_terminate` and `_lib.Pa_Initialize`. Like sounddevice's,
`_initialize` points stderr at /dev/null while PortAudio starts, which
`calls` records. A stream is in blocking mode, and a test fills it tick by
tick with `push`."""

from __future__ import annotations

import types
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


class PortAudioError(Exception):
    """As sounddevice's: (text, PaErrorCode)."""


UNAVAILABLE = -9985  # paDeviceUnavailable
MIC, LINE = "MacBook Pro Microphone", "Scarlett 2i2 USB"  # the inputs of `laptop`
INVALID = -9996  # paInvalidDevice


@dataclass(frozen=True, slots=True)
class Device:
    name: str
    channels: int = 2
    rate: float = 48000.0
    outputs: int = 0


class FakeStream:
    """A blocking-mode input stream: `read_available` is what was pushed
    and not read yet, and `read` never waits."""

    def __init__(self, device: int, channels: int, samplerate: float, dtype: str, latency: float, **extra) -> None:
        self.device, self.channels, self.samplerate = device, channels, samplerate
        self.dtype, self.latency, self.extra = dtype, latency, extra
        self.started = self.closed = False
        self.overflow = False  # the next read reports an overflow
        self.fail: Exception | None = None  # what the next read raises
        self.reads: list[int] = []
        self._pending = np.zeros((0, channels), np.float32)

    def push(self, samples: np.ndarray) -> None:
        """Samples arrive: mono, copied to every channel, or (n, channels)."""
        samples = np.asarray(samples, np.float32)
        if samples.ndim == 1:
            samples = np.repeat(samples[:, None], self.channels, axis=1)
        self._pending = np.concatenate((self._pending, samples))

    @property
    def read_available(self) -> int:
        if self.fail is not None:
            raise self.fail
        return len(self._pending)

    def read(self, frames: int) -> tuple[np.ndarray, bool]:
        assert self.started and not self.closed
        if self.fail is not None:
            raise self.fail
        assert frames <= len(self._pending), "a read of more than read_available waits"
        data, self._pending = self._pending[:frames], self._pending[frames:]
        self.reads.append(frames)
        overflowed, self.overflow = self.overflow, False
        return data, overflowed

    def start(self) -> None:
        self.started = True

    def close(self) -> None:
        self.closed = True


class FakePortAudio:
    """The PortAudio library as sounddevice's `_lib`: the calls pewpew makes."""

    def __init__(self, sd: FakeSoundDevice) -> None:
        self._sd = sd

    def Pa_Initialize(self) -> int:
        sd = self._sd
        sd.calls.append("initialize")
        sd.listed = list(sd.plugged)
        return 0


class FakeSoundDevice(types.ModuleType):
    """The module: the inputs `devices`, under one host API `api`."""

    PortAudioError = PortAudioError

    def __init__(self, *devices: Device, api: str = "Core Audio") -> None:
        super().__init__("sounddevice")
        self.api = api
        self.plugged = list(devices)  # what is connected
        self.listed = list(devices)  # what PortAudio listed when it last started
        self._lib = FakePortAudio(self)
        self._initialized = 1
        self.streams: list[FakeStream] = []
        self.calls: list[str] = []
        self.refuse: Exception | None = None  # what the next open raises
        self.on_open: Callable[[], None] | None = None

    def query_hostapis(self) -> tuple[dict, ...]:
        return ({"name": self.api, "devices": list(range(len(self.listed)))},)

    def query_devices(self) -> list[dict]:
        if not self._initialized:
            raise PortAudioError("PortAudio not initialized", -10000)
        return [{"name": d.name, "index": k, "hostapi": 0, "max_input_channels": d.channels,
                 "max_output_channels": d.outputs, "default_samplerate": d.rate} for k, d in enumerate(self.listed)]

    def InputStream(self, *, device: int, channels: int, samplerate: float, dtype: str, latency: float,
                    **extra) -> FakeStream:
        self.calls.append(f"open {self.listed[device].name} at {device}")
        if self.on_open is not None:
            self.on_open()
        if self.refuse is not None:
            refused, self.refuse = self.refuse, None
            raise refused
        if self.listed[device] not in self.plugged:
            raise PortAudioError("Error opening InputStream: Invalid device", INVALID)
        stream = FakeStream(device, channels, samplerate, dtype, latency, **extra)
        self.streams.append(stream)
        return stream

    def _terminate(self) -> None:
        self.calls.append(f"terminate with {sum(not s.closed for s in self.streams)} open")
        self._initialized -= 1

    def _initialize(self) -> None:
        self.calls.append("stderr to /dev/null")
        self._check(self._lib.Pa_Initialize(), "Error initializing PortAudio")
        self._initialized += 1

    @staticmethod
    def _check(err: int, msg: str = "") -> int:
        if err < 0:
            raise PortAudioError(f"{msg}: error {err}", err)
        return err

    def unplug(self, name: str) -> None:
        """Disconnect the input: its open streams fail their next read."""
        device = next(d for d in self.plugged if d.name == name)
        self.plugged.remove(device)
        for stream in self.streams:
            if not stream.closed and self.listed[stream.device] == device:
                stream.fail = PortAudioError("Error reading from stream: Unanticipated host error", -9999)

    def plug(self, device: Device) -> None:
        self.plugged.append(device)

    @property
    def stream(self) -> FakeStream:
        """The stream opened last."""
        return self.streams[-1]


def laptop() -> FakeSoundDevice:
    """A laptop's microphone, its speakers, and a two-channel line-in."""
    return FakeSoundDevice(Device(MIC, 1), Device("MacBook Pro Speakers", 0, outputs=2), Device(LINE, 2))
