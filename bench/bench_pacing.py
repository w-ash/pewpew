"""Phase-0 pacing-jitter soak — §12 item 13 (gates ADR-010).

ADR-010 says: one paced render clock, deadline-corrected — measure elapsed,
sleep the remainder, correct accumulated error. Its silent dependency is that
CPython can actually hold a 16.7 ms tick under real load: GC pauses, GIL
contention with the audio capture thread, and OS sleep quantization all land
on the render cadence, and device-side keyframe interpolation is hostage to
that cadence being consistent (§12 item 13, [RA-06]).

Item 1 benched throughput — how long a frame takes. This benches *pacing* —
whether the next frame starts when it should. They are different failures: a
host with 50x throughput margin can still miss deadlines.

Three pacers run head to head:
  deadline       ADR-010's — the next deadline advances by exactly one period,
                 so a late tick is absorbed rather than pushed downstream.
  deadline_spin  same schedule, but sleeps short of the deadline and busy-waits
                 the remainder — buys sub-timer accuracy for a core.
  naive          LedFx / led-control's compensated sleep: sleep(period -
                 elapsed) with no accumulated-error term. ADR-010 names this a
                 rejected alternative on the strength of a code read
                 [S630:ledfx/virtuals.py#L864-L877][S660:ledcontrol/intervaltimer.py];
                 running it here turns that read into a measurement.

Headline metric is **cadence** (gap between consecutive ticks), not phase
against an absolute schedule — see run_soak's docstring for why the two differ
and why only the first answers item 13.

L1 one-off host benchmark (test-and-feedback.md §4) — not a pytest rig.
Results are a distribution, never a point value (T-5).

    uv run python bench/bench_pacing.py --label <host>
    uv run python bench/bench_pacing.py --quick        # ~40 s smoke run

The bench measures with the wall clock (perf_counter) — that is the subject.
Render inputs stay deterministic: FakeClock timestamps, fixed seed.
"""

from __future__ import annotations

import argparse
import datetime
import gc
import json
import platform
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

from harness.clock import FakeClock

TARGET_FPS = 60.0
PERIOD_S = 1.0 / TARGET_FPS  # 16.667 ms
SEED = 42
DEFAULT_PX = 20_000  # the pixel count R-9 names
SOAK_S = 600.0  # §12 item 13: "10-min soak"
SWEEP_S = 60.0

# Audio capture cadence: 44.1 kHz / 512-frame blocks = 11.6 ms, the rate a
# sounddevice callback would fire at (ADR-009 keeps DSP out of the callback,
# but the callback thread still exists and still contends for the GIL).
AUDIO_BLOCK = 512
AUDIO_RATE = 44_100.0
AUDIO_PERIOD_S = AUDIO_BLOCK / AUDIO_RATE

# How far short of the deadline the spin pacer stops sleeping. Must exceed the
# sleep overshoot at this period (measured, ~4 ms on macOS) or the sleep lands
# past the deadline and the spin never runs.
SPIN_MARGIN_S = 0.006

# Tick-error histogram edges in ms. Open-ended above the last edge.
HIST_EDGES_MS = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.667, 33.3]


def make_mapping(n: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((n, 3), dtype=np.float32)


def plasma_numpy(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    """Same kernel as bench_throughput's plasma — the representative load."""
    phase = (seed * 0.6180339887498949) % 1.0
    u = 4.0 * mapping[:, 0]
    v = 4.0 * mapping[:, 1]
    w = 4.0 * mapping[:, 2]
    a = np.sin(u * 1.7 + t * 1.3)
    b = np.sin(v * 2.3 - t * 0.7 + np.sin(u * 3.1 + t))
    c = np.sin((u + v + w) * 1.9 + t * 2.1 + 2.0 * np.pi * phase)
    p = (a + b + c) / 3.0
    frame = np.empty((mapping.shape[0], 3), dtype=np.float32)
    frame[:, 0] = 0.5 + 0.5 * np.sin(np.pi * p)
    frame[:, 1] = 0.5 + 0.5 * np.sin(np.pi * p + 2.0943951023931953)
    frame[:, 2] = 0.5 + 0.5 * np.sin(np.pi * p + 4.1887902047863905)
    return frame


class AudioThread:
    """Stand-in for the capture thread: wakes every ~11.6 ms and does an rfft.

    Not a real device — a real one would add driver-side jitter we cannot
    attribute. This isolates what ADR-010 actually worries about: a second
    thread waking on its own cadence and taking the GIL mid-render.
    """

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="audio-capture")
        self.blocks = 0
        rng = np.random.default_rng(SEED)
        self._buf = rng.standard_normal(AUDIO_BLOCK).astype(np.float32)
        self._window = np.hanning(AUDIO_BLOCK).astype(np.float32)

    def _run(self) -> None:
        next_at = time.perf_counter()
        while not self._stop.is_set():
            next_at += AUDIO_PERIOD_S
            slack = next_at - time.perf_counter()
            if slack > 0:
                time.sleep(slack)
            spec = np.abs(np.fft.rfft(self._buf * self._window))
            self._buf[0] = float(spec[1]) * 1e-9  # keep the result live
            self.blocks += 1

    def __enter__(self) -> AudioThread:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)


class GCRecorder:
    """Record every gc collection and its wall duration via gc.callbacks."""

    def __init__(self) -> None:
        self.pauses_ms: list[float] = []
        self._t0: float | None = None

    def _cb(self, phase: str, info: dict) -> None:
        if phase == "start":
            self._t0 = time.perf_counter()
        elif self._t0 is not None:
            self.pauses_ms.append((time.perf_counter() - self._t0) * 1000.0)
            self._t0 = None

    def __enter__(self) -> GCRecorder:
        gc.callbacks.append(self._cb)
        return self

    def __exit__(self, *exc) -> None:
        gc.callbacks.remove(self._cb)


def sleep_quantization_ms(samples: int = 200) -> list[dict]:
    """Floor check: how late does a bare time.sleep() actually return?

    No pacer can beat this. Probed at 1 ms and at the frame period itself,
    because the overshoot is not constant in the requested duration — the
    period row is the one comparable to the pacer results.
    """
    rows = []
    for req in (0.001, PERIOD_S):
        overshoot = []
        for _ in range(samples):
            t0 = time.perf_counter()
            time.sleep(req)
            overshoot.append(((time.perf_counter() - t0) - req) * 1000.0)
        rows.append({
            "requested_ms": req * 1000.0,
            "median_overshoot_ms": statistics.median(overshoot),
            "p99_overshoot_ms": percentile(overshoot, 99),
            "max_overshoot_ms": max(overshoot),
        })
    return rows


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def histogram(values: list[float]) -> list[dict]:
    buckets = []
    for i, lo in enumerate(HIST_EDGES_MS):
        hi = HIST_EDGES_MS[i + 1] if i + 1 < len(HIST_EDGES_MS) else None
        n = sum(1 for v in values if v >= lo and (hi is None or v < hi))
        buckets.append({"lo_ms": lo, "hi_ms": hi, "count": n})
    return buckets


def run_soak(pacer: str, load: str, duration_s: float, px: int) -> dict:
    """Run one paced loop; return its timing distributions.

    Two different things are measured, because they answer different questions
    and the first run of this bench conflated them:

    interval error — actual gap between consecutive tick starts, minus the
        16.67 ms period. **This is the cadence metric item 13 is about.**
        Device-side keyframe interpolation cares whether frame k+1 lands one
        period after frame k, not where either sits in absolute time.

    phase error — tick start minus a perfect 60 fps schedule (t_start +
        k*period). Catches cumulative drift, which is how the naive pacer
        fails: measured against its own re-based deadline it is never late,
        it just silently runs slow. But a *constant* phase offset is not
        jitter — when the deadline pacer absorbs a stall by skipping ahead
        (ADR-010's newest-wins rule) the offset persists for the whole run
        while the cadence stays perfect. Read phase error for slope, not
        magnitude; `deadline_skips` records the skips that caused the steps.
    """
    mapping = make_mapping(px) if load != "idle" else None
    clock = FakeClock()  # pattern time stays deterministic; only pacing is real

    phase_ms: list[float] = []
    interval_err_ms: list[float] = []
    n_ticks = 0
    skips = 0
    skipped_ms = 0.0
    prev_start: float | None = None
    audio = AudioThread() if load == "render+audio" else None

    gc.collect()  # start from a known heap state, then leave GC on — it is the subject
    with GCRecorder() as gcrec:
        ctx = audio if audio else _null_ctx()
        with ctx:
            t_start = time.perf_counter()
            next_due = t_start
            while True:
                now = time.perf_counter()
                if now - t_start >= duration_s:
                    break
                phase_ms.append((now - (t_start + n_ticks * PERIOD_S)) * 1000.0)
                if prev_start is not None:
                    interval_err_ms.append((now - prev_start - PERIOD_S) * 1000.0)
                prev_start = now
                n_ticks += 1

                if mapping is not None:
                    plasma_numpy(clock.tick(PERIOD_S), mapping, SEED)

                if pacer in ("deadline", "deadline_spin"):
                    # ADR-010: absolute schedule, accumulated error corrected.
                    next_due += PERIOD_S
                    slack = next_due - time.perf_counter()
                    if slack > 0:
                        if pacer == "deadline_spin":
                            # Sleep short of the deadline, then busy-wait the
                            # remainder — trades CPU for sub-timer accuracy.
                            if slack > SPIN_MARGIN_S:
                                time.sleep(slack - SPIN_MARGIN_S)
                            while time.perf_counter() < next_due:
                                pass
                        else:
                            time.sleep(slack)
                    else:
                        # Deadline already blown: skip ahead so we never chase a
                        # backlog (newest-wins, never queue deeper).
                        missed = int(-slack // PERIOD_S) + 1
                        next_due += missed * PERIOD_S
                        skips += 1
                        skipped_ms += missed * PERIOD_S * 1000.0
                else:
                    # LedFx / led-control: sleep the remainder of this frame's
                    # budget, measured from wake. No accumulated-error term.
                    elapsed = time.perf_counter() - now
                    slack = PERIOD_S - elapsed
                    if slack > 0:
                        time.sleep(slack)
                    next_due = time.perf_counter()
            wall_s = time.perf_counter() - t_start

    # Drift: where the loop ended up vs where 60 fps says it should have.
    expected_s = n_ticks * PERIOD_S
    drift_ms = (wall_s - expected_s) * 1000.0

    def dist(values: list[float]) -> dict:
        if not values:
            return {k: float("nan") for k in ("mean", "median", "stdev", "min", "p90", "p99", "p99_9", "max")}
        return {
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "p90": percentile(values, 90),
            "p99": percentile(values, 99),
            "p99_9": percentile(values, 99.9),
            "max": max(values),
        }

    abs_interval = [abs(e) for e in interval_err_ms]
    return {
        "pacer": pacer,
        "load": load,
        "duration_s": round(wall_s, 3),
        "px": px if mapping is not None else 0,
        "ticks": n_ticks,
        "achieved_fps": n_ticks / wall_s if wall_s else 0.0,
        # The cadence metric — signed, and absolute for the percentile headline.
        "interval_error_ms": dist(interval_err_ms),
        "abs_interval_error_ms": dist(abs_interval),
        # Phase vs an ideal 60 fps schedule: read for slope (drift), not magnitude.
        "phase_error_ms": dist(phase_ms),
        "late_ticks": {
            "over_1ms": sum(1 for e in abs_interval if e > 1.0),
            "over_5ms": sum(1 for e in abs_interval if e > 5.0),
            "over_one_frame": sum(1 for e in abs_interval if e > PERIOD_S * 1000.0),
        },
        "deadline_skips": {"count": skips, "skipped_ms": skipped_ms},
        "cumulative_drift_ms": drift_ms,
        "drift_ppm": (drift_ms / 1000.0) / wall_s * 1e6 if wall_s else 0.0,
        "gc": {
            "collections": len(gcrec.pauses_ms),
            "total_pause_ms": sum(gcrec.pauses_ms),
            "max_pause_ms": max(gcrec.pauses_ms) if gcrec.pauses_ms else 0.0,
            "p99_pause_ms": percentile(gcrec.pauses_ms, 99) if gcrec.pauses_ms else 0.0,
        },
        "audio_blocks": audio.blocks if audio else 0,
        "histogram_abs_interval_ms": histogram(abs_interval),
    }


class _null_ctx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gather_meta(label: str) -> dict:
    def try_cmd(cmd: list[str]) -> str | None:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip() or None
        except Exception:
            return None

    cpu = None
    if sys.platform == "darwin":
        cpu = try_cmd(["sysctl", "-n", "machdep.cpu.brand_string"])
    elif sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith(("model name", "model")):
                    cpu = line.split(":", 1)[1].strip()
                    break
        except Exception:
            pass

    return {
        "label": label,
        "date": datetime.date.today().isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "cpu_count": __import__("os").cpu_count(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "gc_enabled": gc.isenabled(),
        "gc_thresholds": gc.get_threshold(),
        "git_sha": try_cmd(["git", "rev-parse", "--short", "HEAD"]),
    }


def print_row(r: dict) -> None:
    e = r["abs_interval_error_ms"]
    print(
        f"{r['pacer']:<14} {r['load']:<13} {r['duration_s']:>6.0f}s "
        f"{e['median']:>8.3f} {e['p99']:>8.3f} {e['p99_9']:>9.3f} {e['max']:>9.3f} "
        f"{r['late_ticks']['over_one_frame']:>7} {r['deadline_skips']['count']:>6} "
        f"{r['cumulative_drift_ms']:>11.1f} {r['achieved_fps']:>7.2f}"
    )


def print_header() -> None:
    print(
        f"\n{'pacer':<14} {'load':<13} {'dur':>7} "
        f"{'|Δint| p50':>10} {'p99':>8} {'p99.9':>9} {'max':>9} "
        f"{'>frame':>7} {'skips':>6} {'drift ms':>11} {'fps':>7}"
    )
    print(f"{'':<14} {'':<13} {'':>7} {'cadence error vs 16.67 ms period (ms)':>39}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default=platform.node() or "unknown-host")
    ap.add_argument("--out", default=None, help="JSON output path")
    ap.add_argument("--px", type=int, default=DEFAULT_PX, help=f"render load in pixels (default {DEFAULT_PX})")
    ap.add_argument("--duration", type=float, default=SOAK_S, help=f"headline soak seconds (default {SOAK_S:.0f})")
    ap.add_argument("--sweep-duration", type=float, default=SWEEP_S, help=f"per-cell comparison seconds (default {SWEEP_S:.0f})")
    ap.add_argument("--quick", action="store_true", help="~40 s smoke run")
    args = ap.parse_args()

    soak_s = 10.0 if args.quick else args.duration
    sweep_s = 5.0 if args.quick else args.sweep_duration

    meta = gather_meta(args.label)
    print(f"host: {meta['cpu'] or meta['machine']} | python {meta['python']} | "
          f"gc={'on' if meta['gc_enabled'] else 'OFF'} | {args.px} px @ {TARGET_FPS:.0f} fps")

    quant = sleep_quantization_ms()
    for q in quant:
        print(f"sleep({q['requested_ms']:.2f} ms) overshoot: median {q['median_overshoot_ms']:.3f} ms, "
              f"p99 {q['p99_overshoot_ms']:.3f} ms, max {q['max_overshoot_ms']:.3f} ms")
    print("  ^ the floor under any pacer — the frame-period row is the comparable one")

    results = []
    print_header()

    # Comparison sweep: each pacer, increasing load.
    for load in ("idle", "render", "render+audio"):
        for pacer in ("deadline", "deadline_spin", "naive"):
            r = run_soak(pacer, load, sweep_s, args.px)
            r["role"] = "sweep"
            results.append(r)
            print_row(r)

    # Headline: what §12 item 13 actually specifies.
    print(f"\n-- headline soak: deadline pacer, render+audio, {soak_s:.0f}s --")
    print_header()
    headline = run_soak("deadline", "render+audio", soak_s, args.px)
    headline["role"] = "headline"
    results.append(headline)
    print_row(headline)

    print_summary(headline, results, meta, quant)

    out_path = Path(args.out) if args.out else (
        Path(__file__).parent / "results" / f"pacing-{meta['date']}-{meta['label']}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "meta": meta,
        "target_fps": TARGET_FPS,
        "period_ms": PERIOD_S * 1000.0,
        "sleep_quantization": quant,
        "results": results,
    }, indent=2) + "\n")
    print(f"\nresults written to {out_path}")


def print_summary(h: dict, results: list[dict], meta: dict, quant: list[dict]) -> None:
    e = h["abs_interval_error_ms"]
    frame_ms = PERIOD_S * 1000.0
    p99_frac = e["p99"] / frame_ms
    floor = quant[-1]["median_overshoot_ms"]
    print(
        f"\n§12 item 13 — p99 cadence error {e['p99']:.3f} ms "
        f"({p99_frac * 100:.1f}% of the {frame_ms:.2f} ms period), "
        f"max {e['max']:.3f} ms, {h['late_ticks']['over_one_frame']} intervals off by a full frame "
        f"over {h['ticks']} ticks on {meta['cpu'] or meta['machine']}."
    )
    print(
        f"  Sleep-quantization floor at this period: {floor:.3f} ms median — "
        f"{'most of' if e['median'] <= floor * 1.5 else 'part of'} the observed error is the OS timer, not CPython."
    )
    skips = h["deadline_skips"]["count"]
    if skips:
        print(
            f"  Deadline skips: {skips} ({h['deadline_skips']['skipped_ms']:.0f} ms absorbed) — "
            f"ADR-010's newest-wins rule discarding a backlog rather than chasing it. Each one "
            f"steps phase permanently without disturbing cadence, which is why phase p50 reads "
            f"{h['phase_error_ms']['median']:.1f} ms while cadence stays tight."
        )
    else:
        print(f"  Deadline skips: 0 — no deadline was blown badly enough to drop a frame.")
    print(
        f"  GC: {h['gc']['collections']} collections, max pause {h['gc']['max_pause_ms']:.3f} ms "
        f"— {'below' if h['gc']['max_pause_ms'] < frame_ms else 'ABOVE'} one frame period."
    )
    sweep = {(r["pacer"], r["load"]): r for r in results if r["role"] == "sweep"}
    d = sweep.get(("deadline", "render+audio"))
    n = sweep.get(("naive", "render+audio"))
    s = sweep.get(("deadline_spin", "render+audio"))
    if d and n:
        print(
            f"  ADR-010 pacer choice: deadline drift {d['cumulative_drift_ms']:+.1f} ms "
            f"({d['achieved_fps']:.2f} fps) vs naive {n['cumulative_drift_ms']:+.1f} ms "
            f"({n['achieved_fps']:.2f} fps) over {d['duration_s']:.0f}s."
        )
    if s and d:
        gain = d["abs_interval_error_ms"]["p99"] - s["abs_interval_error_ms"]["p99"]
        print(
            f"  Spin variant: p99 cadence {s['abs_interval_error_ms']['p99']:.3f} ms vs {d['abs_interval_error_ms']['p99']:.3f} ms "
            f"({gain:+.3f} ms) — only worth its CPU if a sub-timer tick is actually needed."
        )
    print("  Distribution, not a point value (T-5) — full percentiles and histogram in the JSON.")
    print("  Pi 5 datapoint pending: rerun with --label pi5.")


if __name__ == "__main__":
    main()
