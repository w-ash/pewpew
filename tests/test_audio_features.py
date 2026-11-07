"""Audio features in a run (pewpew.audio.features, pewpew.run, the `audio`
command): the analysis is deterministic on the sample clock, a feature log
replays byte for byte, `at(t)` never raises, the delay and the log's cap
hold, and the beat, band and env ops read real features unchanged (goldens
on a small committed feature fixture). Nothing
here, or in a run with `--audio`, imports a capture library."""

from __future__ import annotations

import json
import logging
from functools import partial
from pathlib import Path

import numpy as np
import pytest

from audio_signals import RATE, JitterSource, frame_bytes, kick_loop, noise, sine, ticks, write_wav
from fakes import build, looks_file, run_python
from harness.goldens import assert_matches_golden
from pewpew.__main__ import main, parse
from pewpew.audio import ArraySource, AudioFeatures, Block, FeatureLog, ReplayFeatures
from pewpew.audio.analysis import SILENT
from pewpew.audio.beat import phase_error
from pewpew.audio.features import LEAD_S, SILENCE, play, record
from pewpew.audio.inputs import wav_source
from pewpew.fx import expr
from pewpew.fx.op import FrameCtx
from pewpew.fx.ops import OPS
from pewpew.fx.ops.signal import SignalOp
from pewpew.params import ParamSet
from pewpew.render import SlotClock

GOLDENS = Path(__file__).parent / "goldens" / "audio"
# Stripes that stand still unless the bass band moves them: its frames change with the audio alone.
AUDIO_LOOK = expr.look(expr.layer("base", expr.osc(4, offset=expr.band()).palette("ember")))
FIXTURE = GOLDENS / "kick-120.jsonl"


def test_a_wav_analysed_twice_gives_byte_identical_frames(tmp_path: Path) -> None:
    wav = write_wav(tmp_path / "k.wav", kick_loop(124.0, 4.0))
    first, second = ([frame_bytes(f) for _, f in ticks(AudioFeatures(wav_source(wav), fps=60.0), 4.0)]
                     for _ in range(2))
    assert first == second and len(set(first)) > 100


def test_the_frame_is_the_one_stored_for_its_tick_and_keeps_adr_005s_fields() -> None:
    features = AudioFeatures(ArraySource(sine(100.0, 1.0), RATE), fps=60.0)
    assert features.at(0.0) is SILENCE  # before the first tick
    (t, frame), = ticks(features, 1.0 / 60.0)
    assert features.at(t) is frame and features.at(t + 5.0) is frame
    assert frame.events == () and not frame.bands.flags.writeable and frame.bands.dtype == np.float32


class Raising(ArraySource):
    """Noise whose every `take` after the first `after` raises."""

    def __init__(self, after: int) -> None:
        super().__init__(noise(2.0), RATE)
        self.after, self.n = after, 0

    def take(self, t: float) -> list[Block]:
        self.n += 1
        if self.n > self.after:
            raise RuntimeError("the device went away")
        return super().take(t)


def test_before_frame_contains_a_failure_and_at_keeps_the_last_good_frame(caplog) -> None:
    features = AudioFeatures(Raising(after=10), fps=60.0)
    good = ticks(features, 10 / 60.0)[-1][1]
    with caplog.at_level(logging.ERROR, "pewpew.audio.features"):
        later = ticks(features, 5 / 60.0)
    assert all(frame is good for _, frame in later)
    assert features.state()["error"] == "audio analysis failed: RuntimeError: the device went away"
    assert caplog.text.count("the last frame stands") == 1  # logged once per kind of failure


def test_the_delay_holds_the_levels_back_and_the_lead_shrinks() -> None:
    samples = np.concatenate([np.zeros(RATE, np.float32), sine(100.0, 1.0)])
    on_time = [f.volume for _, f in ticks(AudioFeatures(ArraySource(samples, RATE), fps=60.0), 2.0)]
    late = AudioFeatures(ArraySource(samples, RATE), fps=60.0, delay=0.1)
    delayed = [f.volume for _, f in ticks(late, 2.0)]
    rise = next(i for i, v in enumerate(on_time) if v > 0.5)
    assert next(i for i, v in enumerate(delayed) if v > 0.5) == rise + 6  # 0.1 s at 60 fps
    assert late.lead == pytest.approx(LEAD_S - 0.1)


def test_lost_input_reads_silence() -> None:
    features = AudioFeatures(ArraySource(sine(100.0, 0.3), RATE), fps=60.0)
    tail = ticks(features, 1.0)
    assert tail[10][1].volume > 0.5 and tail[-1][1].bands is SILENT.bands and features.mode == "lost"


# ---- the feature log and replay -------------------------------------------------------


def logged(features: AudioFeatures, seconds: float, path: Path) -> list:
    out = path.open("w", encoding="utf-8")
    log = features.log = FeatureLog(out, {"fps": features.fps})
    log.start()
    frames = ticks(features, seconds)
    log.close()
    return frames


def test_a_jittered_live_run_replays_byte_for_byte_at_its_fps_and_at_or_before_t_at_another(tmp_path: Path) -> None:
    path = tmp_path / "f.jsonl"
    live = logged(AudioFeatures(JitterSource(kick_loop(120.0, 3.0), seed=3), fps=60.0), 3.0, path)
    replay = ReplayFeatures(path)
    assert replay.header == {"version": 1, "fps": 60.0}
    assert all(frame_bytes(replay.at(t)) == frame_bytes(frame) for t, frame in live)
    clock = SlotClock(25.0)
    for _ in range(70):
        t = clock.advance()
        before = [frame for at, frame in live if at <= t][-1]
        assert replay.at(t).volume == before.volume
    assert replay.at(0.0) is SILENCE


def test_a_run_logs_its_features_and_a_replay_renders_the_same_bytes(tmp_path: Path) -> None:
    wav = write_wav(tmp_path / "k.wav", kick_loop(120.0, 2.0))
    log = tmp_path / "f.jsonl"
    looks = looks_file(AUDIO_LOOK, "audio")
    live = build(["run", looks, "--audio", str(wav), "--feature-log", str(log), "--ansi"])
    assert isinstance(live.audio, AudioFeatures) and live.audio.source.state()["kind"] == "file"
    live.audio.source = JitterSource(kick_loop(120.0, 2.0), seed=5)  # samples as a device delivers them
    assert live.feature_log is not None
    live.feature_log.start()
    shown = drive(live, 90)
    live.feature_log.close()
    replay = build(["run", looks, "--audio", f"replay:{log}", "--ansi"])
    assert replay.audio is None and replay.loop._before[0] == replay.aura.before_frame
    assert drive(replay, 90) == shown and len(set(shown)) > 20
    header = json.loads(log.read_text().splitlines()[0])["run"]
    assert header == {"version": 1, "seed": 0, "fps": 60.0, "audio": str(wav), "delay_ms": 0.0}


def drive(run, frames: int) -> list[bytes]:
    """`frames` ticks of a built run's stages and stack, as the loop runs them."""
    clock, out = SlotClock(run.args.fps), []
    for _ in range(frames):
        t = clock.advance()
        for hook in run.loop._before:
            hook(t)
        out.append(run.aura.fader.advance_to(t).tobytes())
    return out


def test_the_log_stops_at_its_cap_and_on_a_failed_write_with_one_warning(tmp_path: Path, caplog) -> None:
    path = tmp_path / "f.jsonl"
    log = FeatureLog(path.open("w", encoding="utf-8"), {}, hours=1.0 / 3600.0)  # one second
    log.start()
    for k in range(120):
        log.write(k, k / 60.0, SILENCE, {})
    log.close()
    assert len(path.read_text().splitlines()) == 1 + 61  # the header, then 0 s to 1 s
    assert caplog.text.count("reached its cap of") == 1

    class Full:
        def write(self, text: str) -> int:
            raise OSError(28, "No space left on device")

        def flush(self) -> None: ...

        def close(self) -> None: ...

    caplog.clear()
    failing = FeatureLog(Full(), {})  # type: ignore[arg-type]  # a file that fails every write
    failing.write(0, 0.0, SILENCE, {})
    failing.close()  # never started: written, and failed, on close
    assert caplog.text.count("cannot write the feature log") == 1


# ---- the command line ---------------------------------------------------------------


@pytest.mark.parametrize("argv, problem", [
    (["--feature-log", "f.jsonl"], "--feature-log needs --audio"),
    (["--audio-delay", "40"], "--audio-delay needs --audio"),
    (["--audio", "replay:f.jsonl", "--feature-log", "g.jsonl"], "--feature-log needs an analysed input"),
    (["--audio", "x.wav", "--audio-delay", "20000"], "expected milliseconds from -10000 to 10000"),
    (["--audio-channel", "1"], "--audio-channel needs --audio"),
    (["--audio", "replay:f.jsonl", "--audio-channel", "0"], "--audio-channel needs an analysed input"),
    (["--audio", "x.wav", "--audio-channel", "-1"], "expected a channel, numbered from 0, a whole number of at"),
])
def test_audio_options_that_rule_each_other_out_are_usage_errors(capsys, argv: list[str], problem: str) -> None:
    with pytest.raises(SystemExit) as exit_:
        parse(["run", looks_file(), *argv])
    assert exit_.value.code == 2 and problem in capsys.readouterr().err


def test_an_input_a_run_cannot_open_is_one_exit_line(tmp_path: Path) -> None:
    with pytest.raises(SystemExit,
                       match="--audio net:pewpew-line-1: outside --unattended, a capture node is a bench node"):
        main(["run", looks_file(), "--audio", "net:pewpew-line-1", "--frames", "1"])
    with pytest.raises(SystemExit, match="feature log for appending: No such file or directory"):
        main(["run", looks_file(), "--audio", str(write_wav(tmp_path / "a.wav", noise(0.1))),
              "--feature-log", str(tmp_path / "missing" / "f.jsonl"), "--frames", "1"])


def test_analyse_reports_the_tempo_beats_and_levels(tmp_path: Path, capsys) -> None:
    wav = write_wav(tmp_path / "k.wav", kick_loop(124.0, 10.0))
    log = tmp_path / "f.jsonl"
    assert main(["audio", "analyse", str(wav), "--json", "--feature-log", str(log)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["file"] == "k.wav" and report["rate"] == RATE and report["seconds"] == 10.0
    assert report["bpm"] == pytest.approx(124, rel=0.02) and report["mode"] == "locked"
    assert len(report["tempo"]) == 10 and set(report["modes"]) <= {"searching", "free-run", "locked"}
    gaps = np.diff(report["beats"][-8:])
    assert gaps == pytest.approx(60.0 / 124.0, abs=0.02)
    assert 0.0 < report["levels"]["bass"]["mean"] <= report["levels"]["bass"]["peak"] <= 1.0
    assert len(report["bands"]["mean"]) == 16
    assert ReplayFeatures(log).seconds == pytest.approx(10.0, abs=0.02)
    short = write_wav(tmp_path / "short.wav", kick_loop(124.0, 1.0))
    assert main(["audio", "analyse", str(short)]) == 0
    text = capsys.readouterr().out
    assert text.startswith("short.wav: 1.00 s at 48000 Hz\ntempo 120 BPM, confidence 0.00, ending searching\n")
    assert "\nbeat modes: searching 100%\n1 beat: 0.52\nlevels (mean, 0-1): volume " in text


def test_analyse_takes_a_rate_under_one_frame_a_second(tmp_path: Path, capsys) -> None:
    wav = write_wav(tmp_path / "k.wav", kick_loop(120.0, 3.0))
    assert main(["audio", "analyse", str(wav), "--json", "--fps", "0.4"]) == 0
    assert len(json.loads(capsys.readouterr().out)["tempo"]) == 2  # one a tick: ticks 2.5 s apart


def test_analyse_refuses_a_file_it_cannot_read(tmp_path: Path) -> None:
    (tmp_path / "x.wav").write_bytes(b"not audio")
    with pytest.raises(SystemExit, match=r"x\.wav: not a WAV file"):
        main(["audio", "analyse", str(tmp_path / "x.wav")])


# ---- goldens on a committed feature fixture -------------------------------------------


def fixture_records() -> list[dict]:
    """4 s of a 120 BPM kick loop's features, as a run logs them."""
    features = AudioFeatures(ArraySource(kick_loop(120.0, 4.0), RATE), fps=60.0)
    return [record(k, t, frame, state) for k, (t, frame, state) in enumerate(play(features, 4.0))]


def test_the_fixture_is_what_the_analysis_makes_within_tolerance(regen_goldens: bool) -> None:
    made = fixture_records()
    if regen_goldens or not FIXTURE.exists():
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps({"run": {"version": 1, "fps": 60.0, "audio": "kick_loop(120, 4 s)"}})]
        FIXTURE.write_text("\n".join(lines + [json.dumps(r, separators=(",", ":")) for r in made]) + "\n")
        if not regen_goldens:
            pytest.fail(f"wrote a fresh {FIXTURE.name}; review it, commit it, and re-run")
    stored = [json.loads(line) for line in FIXTURE.read_text().splitlines()[1:]]
    assert [r["t"] for r in stored] == [r["t"] for r in made] and [r["mode"] for r in stored] == [
        r["mode"] for r in made]
    for key in ("bands", "volume", "bass", "mid", "high"):  # FFT output may differ in its last bits by platform
        assert np.allclose([r[key] for r in stored], [r[key] for r in made], atol=1e-4), key
    phases = np.array([[r["beat_phase"] for r in stored], [r["beat_phase"] for r in made]])
    assert (np.abs(phase_error(phases[0], phases[1])) <= 0.02).all()  # a hop, across a wrap too


def signal_traces(features: ReplayFeatures) -> dict[str, np.ndarray]:
    """Each signal op's values over the fixture, at 60 fps, read through the op unchanged."""
    def op(name: str, **args: object) -> SignalOp:
        node = OPS[name]()
        assert isinstance(node, SignalOp)
        ParamSet(OPS[name], args).apply(node)
        return node

    nodes = {"pulse": op("beat"), "phase": op("beat", shape="phase"), "fall": op("beat", shape="fall"),
             "bass": op("band"), "volume": op("band", band="volume"), "env": op("env", attack=0.01, decay=0.2)}
    out: dict[str, list[float]] = {name: [] for name in nodes}
    clock, prev = SlotClock(60.0), 0.0
    for tick in range(240):
        t = clock.advance()
        ctx = FrameCtx(t - prev, features.at(t), tick + 1, 7)
        for name, node in nodes.items():
            node.step(t - prev)
            out[name].append(node.sample(ctx, (out["pulse"][-1],) if name == "env" else ()))
        prev = t
    return {name: np.array(values, np.float64) for name, values in out.items()}


def test_beat_band_and_env_read_real_features_unchanged(regen_goldens: bool) -> None:
    traces = signal_traces(ReplayFeatures(FIXTURE))
    assert traces["pulse"].sum() > 20 and np.ptp(traces["bass"]) > 0.3 and traces["env"].max() > 0.9
    assert_matches_golden(GOLDENS / "signals.npz", traces, regen=regen_goldens)


# ---- no capture library ------------------------------------------------------------------

_NO_CAPTURE = """
import sys, tempfile, pathlib
sys.modules["sounddevice"] = None  # an import of it now raises ImportError
sys.path.insert(0, sys.argv[1])
from audio_signals import kick_loop, write_wav
from pewpew.__main__ import main
from pewpew.aura.book import LookBook
from pewpew.fx import expr
folder = pathlib.Path(tempfile.mkdtemp())
wav = write_wav(folder / "k.wav", kick_loop(120.0, 1.0))
looks = folder / "pulse.look.json"
pulse = expr.look(expr.layer("base", expr.osc(4, offset=expr.band()).palette("ember")))
looks.write_bytes(LookBook({"pulse": pulse}, "pulse").to_bytes())
main(["audio", "analyse", str(wav), "--json"])
main(["run", str(looks), "--audio", str(wav), "--frames", "3", "--ansi"])
print("CAPTURE", sorted(m for m in sys.modules if m.split(".")[0] in {"sounddevice", "_sounddevice", "cffi"}))
"""

JOBS = {"no-capture": partial(run_python, _NO_CAPTURE, str(Path(__file__).parent))}


def test_analysis_and_a_run_with_audio_never_import_a_capture_library(pooled) -> None:
    # The process ran to its end, so nothing imported sounddevice; the one
    # entry is the None the job put there, and cffi never loaded.
    assert "CAPTURE ['sounddevice']" in pooled["no-capture"].stdout
