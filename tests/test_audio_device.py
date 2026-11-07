"""Live capture (pewpew.audio.device, `audio list`, `run --audio NAME`) on
a fake sounddevice module, never the real one: the extra's teaching
refusals, the name rule, a callback-free stream read once a tick, epochs
on overflow and reopen, the supervisor that closes a lost stream and opens
the input again by its exact name while no stream is open, the lost rule,
the audit record before the first open, and the health row."""

from __future__ import annotations

import importlib.machinery
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

from audio_signals import RATE, frame_bytes, kick_loop, sine
from fake_sounddevice import LINE, MIC, UNAVAILABLE, Device, FakeSoundDevice, PortAudioError
from fakes import FakeTime, build, wait_until
from pewpew import audit
from pewpew.__main__ import main
from pewpew.audio import AudioFeatures, DeviceSource
from pewpew.audio.analysis import LOST_S, SILENT
from pewpew.audio.device import (
    DEFAULT_RATE,
    INSTALL,
    NO_PORTAUDIO,
    PRIVACY,
    RETRY_S,
    Input,
    choose,
    device_source,
    portaudio,
)
from pewpew.audio.features import beat_times
from pewpew.errors import Worded
from pewpew.health import OVERFLOW_WARN_S, ZEROS_S, AudioHealth, HealthMonitor
from pewpew.render import SlotClock

FPS = 60.0
TICK = RATE // 60  # the samples one tick at 60 fps brings


def opened(spec: str = LINE, **kw) -> tuple[DeviceSource, FakeTime]:
    """The source `spec` names, on the fake (the `sd` fixture), with its first
    stream open and offered, and its supervisor on a fake clock."""
    ft = FakeTime()
    source = device_source(spec, fps=FPS, now=ft.now, **kw)
    source.step()
    return source, ft


# ---- the extra ---------------------------------------------------------------------


def test_without_the_extra_listing_and_running_say_how_to_install_it(capsys) -> None:
    # conftest puts None in sys.modules["sounddevice"]: the extra is missing.
    with pytest.raises(Worded, match=re.escape(INSTALL)):
        portaudio()
    assert main(["audio", "list"]) == 1  # it still lists the capture nodes (test_audio_node.py)
    assert f"audio list: {INSTALL}" in capsys.readouterr().err
    with pytest.raises(SystemExit, match=re.escape(f"--audio {LINE}: {INSTALL}")):
        main(["run", "pulse", "--audio", LINE, "--frames", "1"])


def test_without_portaudio_the_refusal_names_the_library(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The Linux wheel has no PortAudio: sounddevice's import raises OSError.
    (tmp_path / "sounddevice.py").write_text("raise OSError('PortAudio library not found')\n")
    monkeypatch.delitem(sys.modules, "sounddevice")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(Worded, match=re.escape(NO_PORTAUDIO)):
        portaudio()
    assert "sounddevice" not in sys.modules


def test_the_pinned_sounddevice_has_the_private_calls_the_supervisor_makes() -> None:
    # Read from its source, never imported: CI has no PortAudio.
    spec = importlib.machinery.PathFinder.find_spec("sounddevice")
    assert spec is not None and spec.origin is not None
    text = Path(spec.origin).read_text()
    assert "__version__ = '0.5.6'" in text
    for name in ("def _terminate():", "_initialized -= 1", "def _check(err, msg=''):",
                 "_check(_lib.Pa_Initialize(), 'Error initializing PortAudio')", "_initialized += 1",
                 "def read_available(self):"):
        assert name in text
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    assert pyproject.count('"sounddevice==0.5.6"') == 2  # the extra and the dev group


# ---- naming an input ---------------------------------------------------------------


FOUND = [Input(0, MIC, 1, 48000, "Core Audio"), Input(2, LINE, 2, 44100, "Core Audio"),
         Input(3, "BlackHole 2ch", 2, 48000, "Core Audio")]


@pytest.mark.parametrize("spec, name", [
    (LINE, LINE), ("2", LINE), ("scarlett", LINE), ("blackhole", "BlackHole 2ch"), ("Behringer", None),
])
def test_an_input_is_named_exactly_by_index_or_by_a_part_of_one_name(spec: str, name: str | None) -> None:
    found = choose(spec, FOUND)
    assert (found.name if found is not None else None) == name


TWINS = [Input(0, "USB Audio CODEC", 2, 48000, "ALSA"), Input(1, "USB Audio CODEC", 2, 48000, "ALSA")]


@pytest.mark.parametrize("spec, found, reason", [
    ("default", FOUND, "pewpew never opens the default input, which on a laptop is the built-in microphone"),
    (" Default ", FOUND, "never opens the default input"),
    ("", FOUND[:1], "a blank name names no input; name one (`python -m pewpew audio list` shows them)"),
    ("  ", FOUND[:1], "a blank name names no input"),  # a part of every name, so of the one input here
    ("2ch", FOUND + [Input(4, "Loopback 2ch", 2, 48000, "Core Audio")], "'2ch' fits 2 inputs"),
    (LINE, FOUND + [Input(5, LINE, 2, 48000, "Core Audio")], "2 inputs are named 'Scarlett 2i2 USB'"),
    ("1", TWINS, "2 inputs are named 'USB Audio CODEC'"),  # a reopen by that name could not tell them apart
    ("7", FOUND, "no input has the index 7; `python -m pewpew audio list` shows them"),
])
def test_a_blank_spec_default_a_name_of_several_inputs_and_an_index_of_none_are_refused(
        spec: str, found: list[Input], reason: str) -> None:
    with pytest.raises(ValueError, match=re.escape(reason)):
        choose(spec, found)


@pytest.mark.parametrize("spec, reason", [("", "a blank name names no input"),
                                          ("default", "never opens the default input")])
def test_a_blank_spec_and_default_are_refused_without_the_extra(spec: str, reason: str) -> None:
    # conftest's sounddevice is missing: these refusals come before the list.
    with pytest.raises(SystemExit, match=re.escape(f"--audio {spec}: ") + ".*" + re.escape(reason)):
        main(["run", "pulse", "--audio", spec, "--frames", "1"])


def test_audio_list_names_the_inputs_and_leaves_out_outputs(sd: FakeSoundDevice, capsys) -> None:
    assert main(["audio", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"devices": [
        {"index": 0, "name": MIC, "channels": 1, "rate": 48000, "api": "Core Audio"},
        {"index": 2, "name": LINE, "channels": 2, "rate": 48000, "api": "Core Audio"},
    ], "error": None, "nodes": []}  # conftest: no address to look for nodes from
    assert main(["audio", "list"]) == 0
    text = capsys.readouterr().out
    assert MIC in text and LINE in text and "Speakers" not in text and "never\nopens the default input" in text
    assert sd.streams == []  # listing opens nothing


def test_a_dry_run_names_the_input_and_opens_nothing(sd: FakeSoundDevice, capsys) -> None:
    base = ["run", "pulse", "--ddp", "127.0.0.1=0+10", "--dry-run", "--audio"]
    assert main([*base, "scarlett", "--audio-channel", "1"]) == 0
    assert ("audio: 'Scarlett 2i2 USB' (Core Audio), channel 1 of 2 at 48000 Hz, latency 0.02 s"
            in capsys.readouterr().out)
    assert main([*base, "Behringer UMC22"]) == 0  # not plugged in: not refused
    assert "no input is named 'Behringer UMC22' now; the run starts lost" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="'MacBook Pro Microphone' has 1 channel"):
        main([*base, MIC, "--audio-channel", "1"])
    assert sd.streams == []


# ---- the stream ----------------------------------------------------------------------


@pytest.mark.parametrize("api, latency", [("Core Audio", 0.02), ("ALSA", 0.04)])
def test_the_stream_has_no_callback_and_opens_at_the_inputs_rate(
        sd: FakeSoundDevice, api: str, latency: float) -> None:
    sd.api = api
    source, _ = opened()
    stream = sd.stream
    assert (stream.device, stream.channels, stream.samplerate, stream.dtype, stream.latency) == (
        2, 2, 48000, "float32", latency)
    assert stream.extra == {} and stream.started  # no callback: blocking mode
    assert source.state()["status"] == "opening"  # offered, until the loop takes it


def test_each_tick_reads_what_is_available_without_waiting(sd: FakeSoundDevice) -> None:
    source, _ = opened()
    assert source.take(0.0) == []  # the loop takes the stream; nothing has arrived
    stream = sd.stream
    left, right = sine(440.0, 0.02), sine(440.0, 0.02, level=0.1)
    stream.push(np.stack((left, right), axis=1))
    (block,) = source.take(1 / FPS)
    assert block.start == math.ceil(LOST_S * RATE) and not block.samples.flags.writeable
    np.testing.assert_allclose(block.samples, (left + right) / 2, atol=1e-7)
    assert source.take(2 / FPS) == [] and stream.reads == [len(left)]  # nothing new: no read
    stream.push(np.zeros(TICK))
    assert source.take(3 / FPS)[0].start == block.end and source.state()["status"] == "listening"


def test_one_channel_is_read_alone(sd: FakeSoundDevice) -> None:
    source, _ = opened(channel=1)
    source.take(0.0)
    sd.stream.push(np.stack((np.ones(TICK), np.full(TICK, 0.25)), axis=1))
    assert np.all(source.take(1 / FPS)[0].samples == 0.25)


def test_an_overflow_starts_a_new_epoch_and_the_analysis_restarts_its_grid(sd: FakeSoundDevice) -> None:
    source, _ = opened()
    features = AudioFeatures(source, fps=FPS)
    clock = SlotClock(FPS)
    for k in range(400):  # past the clock's first fit
        sd.stream.overflow = k == 380
        sd.stream.push(sine(100.0, TICK / RATE))
        features.before_frame(clock.advance())
        if k == 379:
            assert source.time(0.0) is not None
    state = features.state()
    assert state["input"]["overflows"] == 1 and state["restarts"] == 1 and source.time(0.0) is None


# ---- lost and reopened ---------------------------------------------------------------


def test_a_lost_input_is_closed_and_opened_again_by_its_exact_name(sd: FakeSoundDevice, caplog) -> None:
    source, ft = opened()
    source.take(0.0)
    first = sd.stream
    source.step()  # a stream is open: the supervisor waits
    assert sd.calls == ["open Scarlett 2i2 USB at 2"]
    sd.unplug(LINE)
    assert source.take(1 / FPS) == []
    state = source.state()
    assert state["status"] == "lost" and state["reason"].startswith("the input stopped: PortAudioError")
    ft.t = 1.0
    source.step()  # closes the released stream; an open is not due until RETRY_S after the last
    assert first.closed and len(sd.calls) == 1
    ft.t = RETRY_S
    source.step()  # lists the inputs again, with no stream open; the input is not back
    assert source.state()["reason"] == "no input is named 'Scarlett 2i2 USB'"
    sd.plug(Device("Scarlett 2i2 USB (2)", 2))
    sd.plug(Device(LINE, 2))  # back, after another
    ft.t = 2 * RETRY_S
    source.step()
    # By its exact name, at its new index; and never through sounddevice's `_initialize`, which points
    # stderr at /dev/null while PortAudio starts, so a record another thread logs then is lost.
    assert sd.calls[1:] == ["terminate with 0 open", "initialize", "terminate with 0 open", "initialize",
                            "open Scarlett 2i2 USB at 3"]
    assert sd._initialized == 1  # sounddevice's count of starts, which its exit handler unwinds
    sd.stream.push(np.zeros(TICK))
    assert source.take(2.0) and source.state()["status"] == "listening" and source.state()["opens"] == 2
    assert caplog.text.count("audio input 'Scarlett 2i2 USB' lost") == 1


def test_a_reopen_refuses_a_name_that_fits_two_inputs_as_the_launch_does(sd: FakeSoundDevice) -> None:
    source, ft = opened()
    source.take(0.0)
    sd.unplug(LINE)
    source.take(1 / FPS)
    sd.plug(Device(LINE, 2))
    sd.plug(Device(LINE, 2))
    ft.t = RETRY_S
    source.step()
    with pytest.raises(ValueError) as launch:
        choose(LINE, [Input(0, LINE, 2, 48000, "Core Audio")] * 2)
    assert source.state()["status"] == "lost" and source.state()["reason"] == str(launch.value)
    assert len(sd.streams) == 1


def test_an_input_that_stops_sending_is_lost_after_half_a_second(sd: FakeSoundDevice) -> None:
    source, _ = opened()
    source.take(0.0)
    sd.stream.push(np.zeros(TICK))
    assert source.take(0.1)
    assert source.take(0.1 + LOST_S - 0.01) == [] and source.state()["status"] == "listening"
    assert source.take(0.1 + LOST_S) == []
    assert source.state()["status"] == "lost" and source.state()["reason"] == "no samples for 0.5 s"


def test_an_input_absent_at_launch_starts_lost_and_opens_at_its_own_rate_once_it_appears(
        sd: FakeSoundDevice, audit_log: Path) -> None:
    source, ft = opened("Behringer UMC22", channel=1)
    assert source.found is None and source.rate == DEFAULT_RATE
    source.audit(["run"])
    assert json.loads(audit_log.read_text())["rate"] is None  # not known until it opens
    assert source.state()["status"] == "lost" and source.state()["reason"] == "no input is named 'Behringer UMC22'"
    features = AudioFeatures(source, fps=FPS)
    assert features.analyser.rate == DEFAULT_RATE and features.control("tap", [0.5] * 4) is None
    clock = SlotClock(FPS)
    features.before_frame(clock.advance())
    sd.plug(Device("Behringer UMC22", 1, rate=44100.0))
    ft.t = RETRY_S
    source.step()
    assert source.state()["reason"] == "'Behringer UMC22' has 1 channel(s), numbered from 0; channel 1 is not one"
    sd.unplug("Behringer UMC22")
    sd.plug(Device("Behringer UMC22", 2, rate=44100.0))
    ft.t = 2 * RETRY_S
    source.step()
    assert (sd.stream.samplerate, sd.stream.channels) == (44100, 2)  # its own rate: no resampling
    tone = sine(100.0, 1.0, rate=44100)
    for k in range(60):
        sd.stream.push(tone[k * 735:(k + 1) * 735])  # one tick of samples at 44.1 kHz
        features.before_frame(clock.advance())
    assert source.rate == source.clock.rate == source.state()["rate"] == 44100
    assert (features.analyser.rate, features.tracker.hop) == (44100, 441)  # the analysis starts again at it
    assert features.tracker.window is not None and features.tracker.bpm == 120.0  # the tap holds
    assert features.at(clock.t).volume > 0.5


def test_a_lost_reason_names_no_path(sd: FakeSoundDevice) -> None:
    # Only a direct caller can name one: `run --audio` takes a spec with a path separator for a file.
    source, _ = opened(str(Path.home() / "sets" / "friday.aiff"))
    assert source.state()["reason"] == "no input is named '…'"


def test_a_busy_input_is_lost_and_says_another_program_holds_it(sd: FakeSoundDevice) -> None:
    sd.refuse = PortAudioError("Error opening InputStream: Device unavailable", UNAVAILABLE)
    source, _ = opened()
    state = source.state()
    assert state["status"] == "lost" and state["busy"] and "Device unavailable" in state["reason"]
    row = AudioHealth().assess({**AudioFeatures(source, fps=FPS).state(), "input": state}, 0.0)
    assert row["level"] == "bad" and "Another program holds it" in row["fix"]


def test_lost_input_silences_the_levels_and_the_beat_keeps_the_last_tempo(sd: FakeSoundDevice) -> None:
    source, ft = opened()
    features = AudioFeatures(source, fps=FPS)
    assert features.control("tap", [0.5] * 4) is None  # 120 BPM
    clock, frames = SlotClock(FPS), []
    tone = sine(100.0, 1.0)
    for k in range(180):
        t = clock.advance()
        if k < 60:
            sd.stream.push(tone[k * TICK:(k + 1) * TICK])
        elif k == 60:
            sd.unplug(LINE)
        features.before_frame(t)
        frames.append((t, features.at(t)))
    assert frames[50][1].volume > 0.5
    assert features.mode == "lost" and frames[-1][1].bands is SILENT.bands and frames[-1][1].volume == 0.0
    beats = beat_times(frames[60:])
    assert len(beats) >= 3 and np.allclose(np.diff(beats), 0.5, atol=1e-6)
    ft.t = RETRY_S
    source.step()  # still unplugged: the beat runs on, and nothing falls back to another input
    assert sd.calls[-1] == "initialize" and source.state()["status"] == "lost"


# ---- in a run ------------------------------------------------------------------------


def live_frames(sd: FakeSoundDevice, frames: int) -> list[bytes]:
    """A built run with `--audio LINE`, its supervisor stepped once, fed a
    kick loop as the input delivers it, tick by tick."""
    run = build(["run", "geq", "--audio", LINE, "--ansi"])
    assert run.capture is not None and run.capture is run.launch.audio
    assert run.audio is not None and run.audio.source is run.capture
    assert run.loop._before[0] == run.audio.before_frame
    run.capture.step()
    kick, clock, out = kick_loop(120.0, frames / FPS + 1.0), SlotClock(FPS), []
    for k in range(frames):
        t = clock.advance()
        if k:
            sd.stream.push(kick[(k - 1) * TICK:k * TICK])
        for hook in run.loop._before:
            hook(t)
        out.append(run.fader.advance_to(t).tobytes() + frame_bytes(run.audio.at(t)))
    return out


def test_a_run_renders_its_input_the_same_for_the_same_samples(sd: FakeSoundDevice) -> None:
    first = live_frames(sd, 150)
    assert live_frames(sd, 150) == first and len(set(first)) > 30


def test_a_run_writes_its_audit_record_before_it_opens_the_input(
        sd: FakeSoundDevice, audit_log: Path, tmp_path: Path) -> None:
    seen: list[bool] = []
    sd.on_open = lambda: seen.append(audit_log.exists() and "audio-input" in audit_log.read_text())
    log = tmp_path / "f.jsonl"
    run = build(["run", "pulse", "--audio", "scarlett", "--feature-log", str(log), "--ansi"])
    assert run.capture is not None
    run._start_capture()
    wait_until(lambda: sd.streams)
    run.capture.stop()
    assert seen == [True] and sd.stream.closed
    (entry,) = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert {k: v for k, v in entry.items() if k not in ("utc", "argv")} == {
        "action": "audio-input", "input": LINE, "kind": "device", "rate": 48000, "channel": None,
        "feature_log": str(log), "privacy": PRIVACY,
    }
    assert run.feature_log is not None
    run.feature_log.close()


def test_no_input_opens_when_its_audit_record_cannot_be_written(
        sd: FakeSoundDevice, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(audit.ENV_VAR, str(tmp_path))  # a directory: the append fails
    run = build(["run", "pulse", "--audio", LINE, "--ansi"])
    with pytest.raises(SystemExit, match="audio: "):
        run._start_capture()
    assert sd.calls == []


def test_the_analysis_keeps_under_a_second_of_samples_after_a_backlog(sd: FakeSoundDevice) -> None:
    source, _ = opened()
    features = AudioFeatures(source, fps=FPS)
    features.before_frame(0.0)
    sd.stream.push(sine(100.0, 3.0))  # a 3 s stall's worth at once
    features.before_frame(3.0)
    assert len(features.analyser._samples) < RATE


# ---- health --------------------------------------------------------------------------


def test_an_input_reading_only_zeros_warns_that_macos_may_deny_the_microphone(sd: FakeSoundDevice) -> None:
    source, _ = opened()
    features = AudioFeatures(source, fps=FPS)
    clock = SlotClock(FPS)
    for _ in range(int((ZEROS_S + 0.5) * FPS)):
        sd.stream.push(np.zeros(TICK))
        features.before_frame(clock.advance())
    row = AudioHealth().assess(features.state(), 0.0)
    assert row["level"] == "warn" and row["reasons"] == ["only exact zeros for 5 s"]
    assert "Privacy & Security → Microphone" in row["fix"]


def _state(mode: str = "locked", **input_state) -> dict:
    """The features' state of a listening device, with overrides."""
    return {"input": {"name": LINE, "kind": "device", "status": "listening", "overflows": 0, **input_state},
            "mode": mode, "bpm": 124.0, "confidence": 0.6, "peak_db": -12.0, "held": 0.0, "zeros_s": 0.0,
            "error": None}


@pytest.mark.parametrize("state, level, reason", [
    (_state(), "ok", None),
    (_state(status="opening"), "pending", None),
    (_state("lost", status="lost", reason="no samples for 0.5 s"), "bad", "lost: no samples for 0.5 s"),
    ({**_state(), "held": 0.2}, "warn", "20% of the tempo window's hops held"),
    ({**_state(), "peak_db": 0.0}, "warn", "clipping: peak 0 dBFS"),
    ({**_state(), "error": "audio analysis failed: ValueError: x"}, "bad", "audio analysis failed: ValueError: x"),
    ({**_state("lost"), "input": {"name": "k.wav", "kind": "file"}}, "bad", "lost: no samples"),
])
def test_the_audio_row_judges_the_input(state: dict, level: str, reason: str | None) -> None:
    row = AudioHealth().assess(state, 0.0)
    assert row["level"] == level and row["reasons"] == ([] if reason is None else [reason])
    assert (row["fix"] is None) == (reason is None)
    assert row["lost"] == (reason is not None and reason.startswith("lost"))


def test_an_overflow_warns_for_a_minute() -> None:
    health = AudioHealth()
    assert health.assess(_state(overflows=0), 0.0)["level"] == "ok"
    assert health.assess(_state(overflows=2), 1.0)["reasons"] == ["2 overflows"]
    assert health.assess(_state(overflows=2), OVERFLOW_WARN_S)["level"] == "warn"
    assert health.assess(_state(overflows=2), 1.0 + OVERFLOW_WARN_S)["level"] == "ok"


def test_the_monitor_reports_the_audio_row_and_logs_its_changes(caplog) -> None:
    states = iter([_state(status="opening"), _state(), _state("lost", status="lost", reason="no samples")])
    ft = FakeTime()
    monitor = HealthMonitor(now=ft.now, audio=lambda: next(states))
    assert monitor.state()["audio"]["level"] == "pending"
    monitor.step()
    assert monitor.state()["audio"]["level"] == "ok" and monitor.state()["level"] == "ok"
    monitor.step()
    snapshot = monitor.state()
    # The page's chip shows `level`, and the page draws no audio row: a bad chip there would explain nothing.
    assert snapshot["audio"]["lost"] and snapshot["audio"]["level"] == "bad" and snapshot["level"] == "ok"
    assert "audio input 'Scarlett 2i2 USB' ok -> bad: lost: no samples" in caplog.text
    assert "audio" not in HealthMonitor(now=ft.now).state()  # no input, no row
