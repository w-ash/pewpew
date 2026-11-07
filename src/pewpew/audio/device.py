"""Live capture from this computer's inputs, a line-in or a microphone,
through the optional extra `pewpew[audio]` (sounddevice on PortAudio).

Nothing imports sounddevice until an input is listed or opened
(`portaudio`), so `import pewpew`, a run without a device and the L1
suite never load it. Without the extra, or without PortAudio, the refusal
says how to install it.

`choose` finds the input a spec names: its exact name, its index, or a
part of one input's name in any case. It refuses a blank spec, `default`
(on a laptop, the built-in microphone), a part that fits more than one
input, and any spec that fits an input whose name another input has too,
since a reopen goes by the name. A spec that fits no input names an input
to wait for, by that exact name. `DeviceSource` is that input as an
`AudioSource`. Each stream opens at the input's own rate, with no
resampling: when a reopen finds another rate, the source's `rate` changes
as the loop takes the stream, and the analysis starts again at it
(pewpew.audio.features). An input absent at launch has `DEFAULT_RATE`
until it opens.

Threads. The stream has no Python callback: sounddevice runs one as a cffi
callback, and cffi takes the GIL to run it, so PortAudio's real-time
thread would wait on the render loop (ADR-009, 2026-11-06 amendment "live
input"). Instead:

- the supervisor thread `pewpew-audio` opens the stream and offers it;
- the loop thread takes it at its next tick and owns it from then on:
  each `take(t)` reads what is available, without waiting, and stamps it
  through a `SampleClock`;
- when the input is lost (a read fails, or no samples come for `LOST_S`)
  the loop releases the stream. The supervisor closes it, then lists the
  inputs again and opens the one of the same exact name, at most once
  every `RETRY_S`. PortAudio has no hotplug, and its last `Pa_Terminate`
  closes every open stream, so it lists the inputs again only while no
  stream is open, through sounddevice's private `_terminate` and its
  `_lib.Pa_Initialize` (pinned to 0.5.6). It does not call sounddevice's
  `_initialize`: that points file descriptor 2 at /dev/null while
  PortAudio starts, which drops what the other threads log meanwhile.

A read that reports an overflow lost a number of samples nobody knows,
and a new stream starts a new count: each begins a new epoch. The sample
index then jumps by `LOST_S` of samples, so the analysis restarts its hop
grid, and the clock forgets its fit.

Privacy: samples stay in memory. PortAudio's buffer holds a few times
`latency` of them, the analysis keeps one window (43 ms at 48 kHz), and
none go to disk. Opening an input is a privacy act, so a run calls
`DeviceSource.audit`, which appends an `audio-input` audit record, before
it starts the supervisor (pewpew.run).
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pewpew import audit
from pewpew.audio.analysis import LOST_S, restart_gap
from pewpew.audio.clock import SampleClock
from pewpew.audio.source import MIN_RATE, Block, mono
from pewpew.errors import Worded, describe_exception

if TYPE_CHECKING:
    from sounddevice import InputStream

logger = logging.getLogger(__name__)

DEFAULT_RATE = 48000  # an input absent at launch, until it opens; an input listed below MIN_RATE [inf]
RETRY_S = 5.0  # the supervisor opens an input at most this often
LATENCY_S = {"Core Audio": 0.02}  # PortAudio's latency, by host API [inf: RA-28 §1; M4 measures]
OTHER_LATENCY_S = 0.04  # ALSA's `hw:` devices and any other host API [inf]
UNAVAILABLE = -9985  # PortAudio's paDeviceUnavailable: another program holds the input
INSTALL = "live capture needs the audio extra: install pewpew[audio] (in this repo, `uv sync --extra audio`)"
NO_PORTAUDIO = ("sounddevice cannot find the PortAudio library; on Linux, install it "
                "(`sudo apt install libportaudio2`)")
LIST = "`python -m pewpew audio list` shows them"
PRIVACY = ("samples stay in memory, under a second of them, and never go to disk; a feature log of a "
           "microphone is close to a recording of speech")
# The modules the extra brings: a missing one is the extra missing, not a bug.
_EXTRA = {"sounddevice", "_sounddevice", "_sounddevice_data", "cffi", "_cffi_backend", "pycparser"}


def portaudio():
    """The sounddevice module, imported here on first use; its return type
    is left to the checker, so callers keep sounddevice's own types.
    Raises `Worded`, saying what to install, when the extra or PortAudio is
    missing."""
    try:
        import sounddevice  # here, so nothing else loads it
    except ModuleNotFoundError as exc:
        if (exc.name or "").partition(".")[0] not in _EXTRA:
            raise
        raise Worded(INSTALL) from None
    except OSError:  # sounddevice raises it when no PortAudio library loads
        raise Worded(NO_PORTAUDIO) from None
    return sounddevice


@dataclass(frozen=True, slots=True)
class Input:
    """One of this computer's inputs, as PortAudio lists it: `rate` is its
    own sample rate, and `api` its host API, such as "Core Audio"."""

    index: int
    name: str
    channels: int
    rate: int
    api: str

    @property
    def latency(self) -> float:
        """The latency the stream asks PortAudio for: its headroom, and the
        size of the chunks the samples arrive in."""
        return LATENCY_S.get(self.api, OTHER_LATENCY_S)

    @property
    def stream_rate(self) -> int:
        """The rate a stream of it opens at: its own, or `DEFAULT_RATE`
        when its own is below what the analysis supports."""
        return self.rate if self.rate >= MIN_RATE else DEFAULT_RATE


def inputs() -> list[Input]:
    """This computer's inputs, as PortAudio last listed them."""
    sd = portaudio()
    apis = [api["name"] for api in sd.query_hostapis()]
    return [
        Input(d["index"], d["name"], d["max_input_channels"], round(d["default_samplerate"]), apis[d["hostapi"]])
        for d in sd.query_devices() if d["max_input_channels"] > 0
    ]


def choose(spec: str, found: Sequence[Input]) -> Input | None:
    """The input in `found` that `spec` names (module docstring), or None
    when it names none: the run then waits for an input of exactly that
    name. Raises ValueError, naming the cause, for a blank spec, `default`,
    a part of a name that fits more than one input, an index of no input,
    or an input whose name another input has too."""
    _check_spec(spec)
    if (named := _named(spec, found)) is not None:
        return named
    if spec.isdigit():
        picked = next((i for i in found if i.index == int(spec)), None)
        if picked is None:
            raise ValueError(f"no input has the index {spec}; {LIST}")
        return _named(picked.name, found)  # a reopen goes by the name, so it must be one input's
    near = [i for i in found if spec.casefold() in i.name.casefold()]
    if len(near) > 1:
        names = ", ".join(repr(i.name) for i in near)
        raise ValueError(f"{spec!r} fits {len(near)} inputs ({names}); give one's exact name")
    return near[0] if near else None


def _check_spec(spec: str) -> None:
    """Raise ValueError for a spec that names no input in particular: a
    blank one, which is part of every name, or `default`."""
    word = spec.strip()
    if not word:
        raise ValueError(f"a blank name names no input; name one ({LIST})")
    if word.casefold() == "default":
        raise ValueError("pewpew never opens the default input, which on a laptop is the built-in microphone; "
                         f"name the input ({LIST})")


def _named(name: str, found: Sequence[Input]) -> Input | None:
    """The input in `found` named `name` exactly, or None. Raises `Worded`
    for a name of more than one input."""
    exact = [i for i in found if i.name == name]
    if len(exact) > 1:
        raise Worded(f"{len(exact)} inputs are named {name!r}, so pewpew could not tell them apart when it "
                     "opens one again; rename one (on a Mac, in Audio MIDI Setup)")
    return exact[0] if exact else None


def _check_channel(found: Input, channel: int | None) -> None:
    """Raise `Worded` when `found` has no channel `channel`."""
    if channel is not None and channel >= found.channels:
        raise Worded(f"{found.name!r} has {found.channels} channel(s), numbered from 0; channel {channel} is not one")


class DeviceSource:
    """One of this computer's inputs as an `AudioSource` (module docstring).

    `name` is the input's exact name, `rate` the rate of the stream the
    loop reads (the input's own at launch, or `DEFAULT_RATE` while an input
    absent at launch has not opened), and `channel` the one channel it
    reads, numbered from 0, or None for the mean of them all. `found` is
    the input as listed at launch, or None when it was absent, and `now`
    is the supervisor's clock. Call `start` once `audit` has written the
    record, and `stop` once the loop has stopped."""

    kind = "device"

    def __init__(
        self, name: str, *, rate: int, fps: float, channel: int | None = None, found: Input | None = None,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.rate = int(rate)  # the loop thread writes it, under the lock
        self.channel = channel
        self.found = found
        self.clock = SampleClock(self.rate, fps)
        self._fps = fps
        self._now = now
        # The loop thread's own.
        self._stream: InputStream | None = None
        self._index = 0  # the index the next sample read gets
        self._heard = 0.0  # engine time of the last tick that read samples
        # Shared, under the lock.
        self._lock = threading.Lock()
        self._offered: tuple[InputStream, int] | None = None  # a stream and its rate
        self._released: InputStream | None = None
        self._status = "opening"
        self._reason: str | None = None
        self._busy = False
        self._overflows = 0
        self._opens = 0
        # The supervisor's own, and `stop`'s once it has stopped. `_open` is
        # the one stream open anywhere: offered, held by the loop or
        # released, until the supervisor closes it.
        self._open: InputStream | None = None
        self._listed = True  # PortAudio's list is fresh: the first open lists nothing again
        self._next_open = -math.inf
        self._logged: str | None = None
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- any thread ------------------------------------------------------

    def state(self) -> dict:
        """JSON-ready: the input's name, kind, rate and channel; its
        `status` (opening, listening or lost) and why it is lost; whether
        another program holds it; and its overflows and opens."""
        with self._lock:
            return {
                "name": self.name, "kind": self.kind, "rate": self.rate, "channel": self.channel,
                "status": self._status, "reason": self._reason, "busy": self._busy,
                "overflows": self._overflows, "opens": self._opens,
            }

    def describe(self) -> str:
        """One line on the input as found at launch, for `run --dry-run`."""
        found = self.found
        if found is None:
            return (f"audio: no input is named {self.name!r} now; the run starts lost and opens it by that "
                    "exact name once it appears, at its own rate")
        if self.channel is not None:
            channels = f"channel {self.channel} of {found.channels}"
        else:
            channels = f"the mean of {found.channels} channels" if found.channels > 1 else "its one channel"
        return (f"audio: {found.name!r} ({found.api}), {channels} at {self.rate} Hz, "
                f"latency {found.latency:g} s; opened only after its audit record")

    def time(self, index: float) -> float | None:
        return self.clock.time(index)

    def audit(self, argv: list[str], *, feature_log: Path | None = None, **fields: object) -> Path:
        """Append the `audio-input` audit record, with the privacy note,
        before the first open; returns the log's path. Its `rate` is None
        for an input absent at launch, whose rate is not known yet. Raises
        OSError when the record cannot be written: then nothing may open
        the input."""
        rate = self.rate if self.found is not None else None
        return audit.record(
            "audio-input", argv=argv, input=self.name, kind=self.kind, rate=rate, channel=self.channel,
            feature_log=None if feature_log is None else str(feature_log), privacy=PRIVACY, **fields,
        )

    def start(self) -> None:
        """Start the supervisor, which opens the input at once."""
        self._thread = threading.Thread(target=self._run, name="pewpew-audio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the supervisor and close every stream. After the loop has stopped."""
        self._stopping.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=RETRY_S)
        self._stream = None
        stream, self._open = self._open, None
        with self._lock:
            self._offered = self._released = None
        if stream is not None:
            self._close(stream)

    # ---- loop thread -----------------------------------------------------

    def take(self, t: float) -> list[Block]:
        """What the input has delivered since the last tick, read without
        waiting, as at most one block."""
        stream = self._stream if self._stream is not None else self._adopt(t)
        if stream is None:
            return []
        try:
            available = stream.read_available
            data, overflowed = stream.read(available) if available else (None, False)
        except Exception as exc:  # noqa: BLE001  an unplugged input raises PortAudioError; any failure loses it
            self._release(f"the input stopped: {describe_exception(exc)}")
            return []
        if data is None:
            if t - self._heard >= LOST_S:
                self._release(f"no samples for {LOST_S:g} s")
            return []
        if overflowed:
            with self._lock:
                self._overflows += 1
            self._new_epoch()
        samples = mono(data, self.channel)
        samples.setflags(write=False)
        block = Block(self._index, samples)
        self._index = block.end
        self.clock.observe(block.end, t)
        self._heard = t
        return [block]

    def _adopt(self, t: float) -> InputStream | None:
        """The stream the supervisor offers, now the loop's, at its rate;
        or None."""
        with self._lock:
            offered, self._offered = self._offered, None
            if offered is None:
                return None
            stream, self.rate = offered
            self._status, self._reason, self._busy = "listening", None, False
        if self.clock.rate != self.rate:
            self.clock = SampleClock(self.rate, self._fps)
        self._stream = stream
        self._heard = t
        self._new_epoch()
        return stream

    def _new_epoch(self) -> None:
        self._index += restart_gap(self.rate)
        self.clock.restart()

    def _release(self, reason: str) -> None:
        """Give the stream back to the supervisor to close."""
        stream, self._stream = self._stream, None
        with self._lock:
            self._released = stream
            self._status, self._reason = "lost", reason
        self._wake.set()
        logger.warning("audio input %r lost: %s; pewpew opens it again by its name", self.name, reason)

    # ---- the supervisor --------------------------------------------------

    def step(self) -> None:
        """One pass of the supervisor: close the stream the loop released,
        then open the input when no stream is open and an open is due."""
        with self._lock:
            released, self._released = self._released, None
        if released is not None:
            self._close(released)
            self._open = None
        if self._open is not None:
            return
        now = self._now()
        if now >= self._next_open:
            self._next_open = now + RETRY_S
            self._open_input()

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                self.step()
            except Exception:  # the supervisor must outlive anything PortAudio raises
                logger.exception("audio supervisor step failed (contained)")
            self._wake.wait(None if self._open is not None else max(0.0, self._next_open - self._now()))
            self._wake.clear()

    def _open_input(self) -> None:
        """List the inputs again unless the list is fresh, then open the
        one named `name` and offer it to the loop. A failure leaves the
        input lost, with the reason."""
        sd, busy = portaudio(), False
        try:
            if not self._listed:
                _list_again()
            self._listed = False
            found = _named(self.name, inputs())
            if found is None:
                raise Worded(f"no input is named {self.name!r}")
            _check_channel(found, self.channel)
            channels = self.channel + 1 if self.channel is not None else found.channels
            rate = found.stream_rate
            stream = sd.InputStream(device=found.index, channels=channels, samplerate=rate,
                                    dtype="float32", latency=found.latency)
            try:
                stream.start()
            except Exception:
                stream.close()
                raise
        except Worded as exc:
            reason = describe_exception(exc)
        except Exception as exc:  # noqa: BLE001  PortAudio refused the open or the list: the input stays lost
            busy = isinstance(exc, sd.PortAudioError) and len(exc.args) > 1 and exc.args[1] == UNAVAILABLE
            reason = f"cannot open it: {describe_exception(exc)}"
        else:
            self._open = stream
            with self._lock:
                self._offered = (stream, rate)
                self._opens += 1
            self._logged = None
            logger.info("audio input %r open: %d channel(s) at %d Hz, latency %g s (%s)",
                        self.name, channels, rate, found.latency, found.api)
            return
        with self._lock:
            self._status, self._reason, self._busy = "lost", reason, busy
        if reason != self._logged:
            self._logged = reason
            logger.warning("audio input %r: %s; pewpew tries again every %g s", self.name, reason, RETRY_S)

    def _close(self, stream: InputStream) -> None:
        try:
            stream.close()
        except Exception:  # a stream of an unplugged input may fail to close; it is gone either way
            logger.warning("cannot close the stream of audio input %r", self.name, exc_info=True)


def _list_again() -> None:
    """Have PortAudio list the inputs again: it lists them only when it
    starts. Only while no stream is open, and with stderr left as it is
    (module docstring). Keeps sounddevice's count of starts, which its
    exit handler reads."""
    sd = portaudio()
    if sd._initialized:
        sd._terminate()
    sd._check(sd._lib.Pa_Initialize(), "Error initializing PortAudio")
    sd._initialized += 1


def device_source(
    spec: str, *, fps: float, channel: int | None = None, now: Callable[[], float] = time.monotonic,
) -> DeviceSource:
    """The input `spec` names (`choose`) as a source, not yet started, its
    supervisor on the clock `now`. Raises ValueError naming the cause: a
    blank spec or `default`, a missing extra or PortAudio, a name that fits
    several inputs, an index of no input, or a channel the input does not
    have."""
    _check_spec(spec)  # before the list, so neither refusal needs the extra
    found = choose(spec, inputs())
    if found is None:
        return DeviceSource(spec, rate=DEFAULT_RATE, fps=fps, channel=channel, now=now)
    _check_channel(found, channel)
    return DeviceSource(found.name, rate=found.stream_rate, fps=fps, channel=channel, found=found, now=now)


__all__ = [
    "DEFAULT_RATE", "INSTALL", "NO_PORTAUDIO", "PRIVACY", "RETRY_S", "DeviceSource", "Input", "choose",
    "device_source", "inputs", "portaudio",
]
