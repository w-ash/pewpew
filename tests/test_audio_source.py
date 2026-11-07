"""Audio sources (pewpew.audio.source, pewpew.audio.inputs): WAV files
read to mono float32 with named refusals, an array played on engine time,
and the `--audio` specs a run accepts."""

from __future__ import annotations

import struct
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

from audio_signals import RATE, sine, write_wav
from pewpew.audio import ArraySource, ReplayFeatures, read_wav
from pewpew.audio.inputs import read_input


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_a_wav_reads_as_float32_in_minus_one_to_one(tmp_path: Path, width: int) -> None:
    tone = sine(440.0, 0.1, level=0.5)
    samples, rate = read_wav(write_wav(tmp_path / "a.wav", tone, width=width))
    assert rate == RATE and samples.dtype == np.float32 and len(samples) == len(tone)
    assert np.abs(samples - tone).max() < 2.0 / 2 ** (8 * width - 1) + 1e-6


def test_channels_mix_or_one_is_picked(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "s.wav", sine(440.0, 0.05), channels=2)
    mixed, _ = read_wav(path)
    left, _ = read_wav(path, channel=0)
    assert np.array_equal(mixed, left)
    with pytest.raises(ValueError, match="the file has 2 channel"):
        read_wav(path, channel=2)


def _header(tag: int, bits: int = 0) -> bytes:
    """A mono WAV header of format `tag` and `bits` a sample, with no samples."""
    body = b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, tag, 1, RATE, 0, 0, bits) + b"data" + bytes(4)
    return b"RIFF" + struct.pack("<I", len(body)) + body


@pytest.mark.parametrize("data, reason", [
    (b"ID3\x04 an mp3", "not a WAV file"),
    (_header(0x55), "format tag is 0x0055, not PCM"),
    (_header(1, bits=64), "this WAV holds 64-bit samples; pewpew reads 8-, 16-, 24- and 32-bit PCM"),
    *([(_header(3), "IEEE float samples, which Python's wave module reads from 3.15")]
      if sys.version_info < (3, 15) else []),
    *([(_header(0xFFFE), "extensible header, which Python's wave module reads from 3.12")]
      if sys.version_info < (3, 12) else []),
])
def test_a_file_wave_cannot_read_is_refused_by_its_cause(tmp_path: Path, data: bytes, reason: str) -> None:
    path = tmp_path / "x.wav"
    path.write_bytes(data)
    with pytest.raises(ValueError, match=reason):
        read_wav(path)


def test_an_empty_or_slow_wav_is_refused(tmp_path: Path) -> None:
    with wave.open(str(tmp_path / "empty.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
    with pytest.raises(ValueError, match="holds no samples"):
        read_wav(tmp_path / "empty.wav")
    with pytest.raises(ValueError, match="the sample rate is 4000 Hz; the analysis needs at least 8000 Hz"):
        read_wav(write_wav(tmp_path / "slow.wav", sine(100.0, 0.1, 4000), 4000))


def test_an_array_plays_up_to_floor_t_rate_in_one_block_a_tick() -> None:
    source = ArraySource(np.arange(800, dtype=np.float32), 8000)
    first, second = source.take(0.0333), source.take(0.0666)
    assert [(b.start, len(b.samples)) for b in first + second] == [(0, 266), (266, 266)]
    assert source.take(0.0666) == []  # nothing new
    assert sum(len(b.samples) for b in source.take(1.0)) == 268 and source.take(2.0) == []  # it ends
    assert source.time(480) == 0.06 and not first[0].samples.flags.writeable


def test_a_looping_array_never_ends_and_never_gaps() -> None:
    source = ArraySource(np.arange(10, dtype=np.float32), 8000, loop=True)
    blocks = [b for t in (0.00075, 0.001875, 0.003375) for b in source.take(t)]
    assert [b.start for b in blocks] == [0, 6, 15] and blocks[-1].end == 27
    assert blocks[1].samples.tolist() == [6, 7, 8, 9, 0, 1, 2, 3, 4]


def test_an_array_source_keeps_its_own_copy_of_the_samples() -> None:
    samples = np.zeros(RATE, np.float32)
    source = ArraySource(samples, RATE)
    samples[0] = 1.0  # the caller's array stays writable
    assert source.samples[0] == 0.0 and not source.samples.flags.writeable


@pytest.mark.parametrize("samples, rate, reason", [
    (np.zeros((2, 2)), RATE, "1-D array"), (np.zeros(0), RATE, "non-empty"),
    (np.array([np.nan]), RATE, "finite"), (np.zeros(4), 100, "at least 8000 Hz"),
])
def test_an_array_source_refuses_what_it_cannot_play(samples: np.ndarray, rate: int, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        ArraySource(samples, rate)


def test_audio_specs_name_a_wav_file_or_a_feature_log(tmp_path: Path) -> None:
    wav = write_wav(tmp_path / "Song.WAV", sine(440.0, 0.1), channels=2)
    source = read_input(str(wav), fps=60.0)
    assert isinstance(source, ArraySource) and source.loop and source.state()["name"] == "Song.WAV"
    assert isinstance(read_input(str(wav), fps=60.0, channel=1), ArraySource)
    with pytest.raises(ValueError, match="the file has 2 channel"):  # `--audio-channel` reaches the file
        read_input(str(wav), fps=60.0, channel=2)
    log = tmp_path / "f.jsonl"
    log.write_text('{"run": {"version": 1}}\n{"t": 0.1, "bands": ' + str([0.0] * 16)
                   + ', "volume": 0, "bass": 0, "mid": 0, "high": 0, "beat_phase": 0.5}\n')
    assert isinstance(read_input(f"replay:{log}", fps=60.0), ReplayFeatures)


@pytest.mark.parametrize("spec, reason", [
    ("missing.wav", "cannot read the WAV file: No such file or directory"),
    # A path separator names a file, never an input to wait for (nor the extra to install).
    ("sets/friday.aiff", "cannot read the WAV file: No such file or directory"),
    ("/no/such/folder/friday.aiff", "cannot read the WAV file: No such file or directory"),
    ("net:pewpew-line-1", "outside --unattended, a capture node is a bench node: name its IPv4 address"),
    ("replay:missing.jsonl", "cannot read the feature log: No such file or directory"),
])
def test_an_audio_spec_a_run_cannot_play_is_refused_by_its_cause(spec: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        read_input(spec, fps=60.0)


@pytest.mark.parametrize("text, reason", [
    ("", "not a feature log: a feature log starts with its run header"),
    ('{"t": 1}\n', "starts with its run header"),
    ('{"run": {}}\n', "holds no frames"),
    ('{"run": {}}\n{"t": 1, "volume": 0}\n', "record 2 is not a frame"),
    ('{"run": {}}\n{"t": 1, "bands": [1], "volume": 0, "bass": 0, "mid": 0, "high": 0, "beat_phase": 0}\n',
     "record 2: bands is a list of 16 numbers"),
    ("not json\n", "not a feature log: Expecting value"),
    ("null\n", "not a feature log: line 1 is not a JSON object"),
    ('{"run": {}}\n\n["run"]\n', "not a feature log: line 3 is not a JSON object"),
])
def test_a_malformed_feature_log_is_refused_by_its_record(tmp_path: Path, text: str, reason: str) -> None:
    (tmp_path / "f.jsonl").write_text(text)
    with pytest.raises(ValueError, match=reason):
        read_input(f"replay:{tmp_path / 'f.jsonl'}", fps=60.0)
