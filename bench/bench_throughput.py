"""Phase-0 throughput microbenchmark — §12 item 1 (R-9, gates ADR-011).

Per-pixel Python loop vs vectorized NumPy vs Numba @njit, computing
identical pattern math + a pipeline tail, swept over N ∈ {300, 3000, 30000}.
R-9 target: ≥20k px × 60 fps = 1.2M px·frames/s on a Pi 5-class host.

L1 one-off host microbenchmark (test-and-feedback.md §4) — not a pytest
rig. Run on desktop AND Pi 5; each run drops a JSON in bench/results/.

    uv run --group bench python bench/bench_throughput.py --label <host>

The bench harness times with wall clock (perf_counter); the pattern inputs
themselves stay deterministic (FakeClock timestamps, fixed seed).

Kernel math is specified once per kernel as scalar formulas (see each
*_SPEC docstring); the three implementations transcribe the same formulas.
The agreement gate verifies they match before anything is timed.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from harness.clock import FakeClock

try:
    from numba import njit

    NUMBA_AVAILABLE = True
except ImportError:  # bench still yields loop+NumPy datapoints
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):  # type: ignore[misc]
        def deco(fn):
            return fn

        return deco(args[0]) if args and callable(args[0]) else deco


R9_TARGET_PX_FRAMES_PER_S = 1.2e6
GOLDEN = 0.6180339887498949  # seed→phase hash, same convention as SolidPulse
TWO_PI = 2.0 * math.pi

# Pipeline tail constants (ADR-001 stages-lite: brightness, white point,
# power limit, quantize) — so "evaluation + pipeline" isn't vacuous.
BRIGHTNESS = 0.8
WP_R, WP_G, WP_B = 1.0, 0.95, 0.9
POWER_BUDGET_FRAC = 0.3  # budget = frac * N * 3 in linear-light sum units

SEED = 42
DEFAULT_NS = [300, 3_000, 30_000]
REP_TARGET_S = 0.3
REPS = 5
FRAMES_MIN, FRAMES_MAX = 3, 2000
SLOW_PROBE_S = 2.0  # probe frame slower than this → F=3, R=3, flagged


def make_mapping(n: int, seed: int = 7) -> np.ndarray:
    """Seeded random 3D point cloud in [0,1] — honest 3D coords, no y=z=0."""
    rng = np.random.default_rng(seed)
    return rng.random((n, 3), dtype=np.float32)


# --------------------------------------------------------------------------
# Kernel A — plasma. Transcendental-heavy (~8 sin/exp per pixel): the honest
# representative workload. Scalar spec, per pixel with coords (x, y, z):
#   phase = (seed * GOLDEN) % 1
#   u, v, w = 4x, 4y, 4z
#   a = sin(1.7u + 1.3t)
#   b = sin(2.3v - 0.7t + sin(3.1u + t))
#   c = sin(1.9(u+v+w) + 2.1t + 2π·phase)
#   p = (a + b + c) / 3
#   r, g, b = 0.5 + 0.5·sin(πp + {0, 2π/3, 4π/3})
# --------------------------------------------------------------------------


def plasma_loop(t: float, xs: list, ys: list, zs: list, seed: int) -> list:
    phase = (seed * GOLDEN) % 1.0
    sin = math.sin
    out = []
    for i in range(len(xs)):
        u = 4.0 * xs[i]
        v = 4.0 * ys[i]
        w = 4.0 * zs[i]
        a = sin(u * 1.7 + t * 1.3)
        b = sin(v * 2.3 - t * 0.7 + sin(u * 3.1 + t))
        c = sin((u + v + w) * 1.9 + t * 2.1 + TWO_PI * phase)
        p = (a + b + c) / 3.0
        out.append(
            (
                0.5 + 0.5 * sin(math.pi * p),
                0.5 + 0.5 * sin(math.pi * p + 2.0943951023931953),
                0.5 + 0.5 * sin(math.pi * p + 4.1887902047863905),
            )
        )
    return out


def plasma_numpy(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    phase = (seed * GOLDEN) % 1.0
    u = 4.0 * mapping[:, 0]
    v = 4.0 * mapping[:, 1]
    w = 4.0 * mapping[:, 2]
    a = np.sin(u * 1.7 + t * 1.3)
    b = np.sin(v * 2.3 - t * 0.7 + np.sin(u * 3.1 + t))
    c = np.sin((u + v + w) * 1.9 + t * 2.1 + TWO_PI * phase)
    p = (a + b + c) / 3.0
    frame = np.empty((mapping.shape[0], 3), dtype=np.float32)
    frame[:, 0] = 0.5 + 0.5 * np.sin(np.pi * p)
    frame[:, 1] = 0.5 + 0.5 * np.sin(np.pi * p + 2.0943951023931953)
    frame[:, 2] = 0.5 + 0.5 * np.sin(np.pi * p + 4.1887902047863905)
    return frame


@njit(cache=True)
def plasma_numba(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    n = mapping.shape[0]
    phase = (seed * GOLDEN) % 1.0
    frame = np.empty((n, 3), dtype=np.float32)
    for i in range(n):
        u = 4.0 * mapping[i, 0]
        v = 4.0 * mapping[i, 1]
        w = 4.0 * mapping[i, 2]
        a = math.sin(u * 1.7 + t * 1.3)
        b = math.sin(v * 2.3 - t * 0.7 + math.sin(u * 3.1 + t))
        c = math.sin((u + v + w) * 1.9 + t * 2.1 + TWO_PI * phase)
        p = (a + b + c) / 3.0
        frame[i, 0] = 0.5 + 0.5 * math.sin(math.pi * p)
        frame[i, 1] = 0.5 + 0.5 * math.sin(math.pi * p + 2.0943951023931953)
        frame[i, 2] = 0.5 + 0.5 * math.sin(math.pi * p + 4.1887902047863905)
    return frame


# --------------------------------------------------------------------------
# Kernel B — comet. Branch + decay: probes the `if` vs np.where question
# (ADR-005). Scalar spec, per pixel:
#   phase = (seed * GOLDEN) % 1
#   head = (0.4t + phase) % 1
#   d = |x - head|; d = min(d, 1 - d)          (wrap distance)
#   v = 1.0 if d < 0.02 else exp(-40d)          (branch)
#   spark = frac(sin(12.9898x + seed) · 43758.5453)   (hash, no RNG)
#   v = min(1, v + (0.3 if spark > 0.995 else 0))
#   r, g, b = v, v², v³
# The hash + thresholds are computed in float64 in every impl — float32
# sin() disagrees with float64 near the spark threshold and a 0.3 jump on
# one pixel would (correctly) fail the agreement gate.
# --------------------------------------------------------------------------


def comet_loop(t: float, xs: list, ys: list, zs: list, seed: int) -> list:
    phase = (seed * GOLDEN) % 1.0
    head = (0.4 * t + phase) % 1.0
    sin, exp = math.sin, math.exp
    out = []
    for i in range(len(xs)):
        x = xs[i]
        d = abs(x - head)
        if d > 0.5:
            d = 1.0 - d
        v = 1.0 if d < 0.02 else exp(-40.0 * d)
        spark = (sin(12.9898 * x + seed) * 43758.5453) % 1.0
        if spark > 0.995:
            v = min(1.0, v + 0.3)
        out.append((v, v * v, v * v * v))
    return out


def comet_numpy(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    phase = (seed * GOLDEN) % 1.0
    head = (0.4 * t + phase) % 1.0
    x64 = mapping[:, 0].astype(np.float64)  # hash/thresholds in f64, see spec
    d = np.abs(x64 - head)
    d = np.minimum(d, 1.0 - d)
    v = np.where(d < 0.02, 1.0, np.exp(-40.0 * d))
    spark = (np.sin(12.9898 * x64 + seed) * 43758.5453) % 1.0
    v = np.where(spark > 0.995, np.minimum(1.0, v + 0.3), v)
    frame = np.empty((mapping.shape[0], 3), dtype=np.float32)
    frame[:, 0] = v
    frame[:, 1] = v * v
    frame[:, 2] = v * v * v
    return frame


@njit(cache=True)
def comet_numba(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    n = mapping.shape[0]
    phase = (seed * GOLDEN) % 1.0
    head = (0.4 * t + phase) % 1.0
    frame = np.empty((n, 3), dtype=np.float32)
    for i in range(n):
        x = float(mapping[i, 0])
        d = abs(x - head)
        if d > 0.5:
            d = 1.0 - d
        v = 1.0 if d < 0.02 else math.exp(-40.0 * d)
        spark = (math.sin(12.9898 * x + seed) * 43758.5453) % 1.0
        if spark > 0.995:
            v = min(1.0, v + 0.3)
        frame[i, 0] = v
        frame[i, 1] = v * v
        frame[i, 2] = v * v * v
    return frame


# --------------------------------------------------------------------------
# Kernel C — solid_pulse. The existing reference pattern's math, verbatim
# (harness/patterns/solid_pulse.py, rate_hz=0.5): trivially-broadcast lower
# bound — any real pattern lands between C and A.
# --------------------------------------------------------------------------


def solid_pulse_loop(t: float, xs: list, ys: list, zs: list, seed: int) -> list:
    phase = (seed * GOLDEN) % 1.0
    pulse = 0.5 * (1.0 + math.sin(TWO_PI * (0.5 * t + phase)))
    out = []
    for i in range(len(xs)):
        x = xs[i]
        out.append((pulse * x, pulse * (1.0 - x), 0.25 * pulse))
    return out


def solid_pulse_numpy(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    phase = (seed * GOLDEN) % 1.0
    pulse = 0.5 * (1.0 + np.sin(TWO_PI * (0.5 * t + phase)))
    x = mapping[:, 0]
    frame = np.zeros((mapping.shape[0], 3), dtype=np.float32)
    frame[:, 0] = pulse * x
    frame[:, 1] = pulse * (1.0 - x)
    frame[:, 2] = 0.25 * pulse
    return frame


@njit(cache=True)
def solid_pulse_numba(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    n = mapping.shape[0]
    phase = (seed * GOLDEN) % 1.0
    pulse = 0.5 * (1.0 + math.sin(TWO_PI * (0.5 * t + phase)))
    frame = np.empty((n, 3), dtype=np.float32)
    for i in range(n):
        x = mapping[i, 0]
        frame[i, 0] = pulse * x
        frame[i, 1] = pulse * (1.0 - x)
        frame[i, 2] = 0.25 * pulse
    return frame


# --------------------------------------------------------------------------
# Pipeline tail, per impl style. Scalar spec, per pixel channel c:
#   s = frame[c] · BRIGHTNESS · wp[c]
#   total = Σ s over frame;  k = min(1, budget / max(total, 1e-9))
#   out[c] = floor(clamp(s · k, 0, 1) · 255 + 0.5)  as uint8
# --------------------------------------------------------------------------


def pipeline_loop(frame: list) -> list:
    total = 0.0
    scaled = []
    for r, g, b in frame:
        sr = r * BRIGHTNESS * WP_R
        sg = g * BRIGHTNESS * WP_G
        sb = b * BRIGHTNESS * WP_B
        total += sr + sg + sb
        scaled.append((sr, sg, sb))
    budget = POWER_BUDGET_FRAC * len(frame) * 3.0
    k = min(1.0, budget / max(total, 1e-9))
    out = []
    for sr, sg, sb in scaled:
        vr = min(1.0, max(0.0, sr * k))
        vg = min(1.0, max(0.0, sg * k))
        vb = min(1.0, max(0.0, sb * k))
        out.append((int(vr * 255.0 + 0.5), int(vg * 255.0 + 0.5), int(vb * 255.0 + 0.5)))
    return out


_WP_VEC = np.array([WP_R, WP_G, WP_B], dtype=np.float32)


def pipeline_numpy(frame: np.ndarray) -> np.ndarray:
    scaled = frame * (BRIGHTNESS * _WP_VEC)
    total = float(scaled.sum())
    budget = POWER_BUDGET_FRAC * frame.shape[0] * 3.0
    k = min(1.0, budget / max(total, 1e-9))
    out = np.clip(scaled * k, 0.0, 1.0)
    return (out * 255.0 + 0.5).astype(np.uint8)


@njit(cache=True)
def pipeline_numba(frame: np.ndarray) -> np.ndarray:
    n = frame.shape[0]
    scaled = np.empty((n, 3), dtype=np.float32)
    total = 0.0
    for i in range(n):
        sr = frame[i, 0] * BRIGHTNESS * WP_R
        sg = frame[i, 1] * BRIGHTNESS * WP_G
        sb = frame[i, 2] * BRIGHTNESS * WP_B
        scaled[i, 0] = sr
        scaled[i, 1] = sg
        scaled[i, 2] = sb
        total += sr + sg + sb
    budget = POWER_BUDGET_FRAC * n * 3.0
    k = min(1.0, budget / max(total, 1e-9))
    out = np.empty((n, 3), dtype=np.uint8)
    for i in range(n):
        for c in range(3):
            v = scaled[i, c] * k
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            out[i, c] = np.uint8(v * 255.0 + 0.5)
    return out


# --------------------------------------------------------------------------
# Impl adapters: each yields pattern(t) -> float frame (as f64 ndarray for
# the gate) and run(t) -> uint8 frame (the timed full render+pipeline).
# --------------------------------------------------------------------------

KERNELS = {
    "plasma": (plasma_loop, plasma_numpy, plasma_numba),
    "comet": (comet_loop, comet_numpy, comet_numba),
    "solid_pulse": (solid_pulse_loop, solid_pulse_numpy, solid_pulse_numba),
}


def make_impls(kernel: str, mapping: np.ndarray, seed: int) -> dict:
    loop_fn, numpy_fn, numba_fn = KERNELS[kernel]
    # The loop impl gets python-native lists (its best honest representation
    # of a per-pixel engine); conversion happens once, outside timing.
    xs = mapping[:, 0].astype(np.float64).tolist()
    ys = mapping[:, 1].astype(np.float64).tolist()
    zs = mapping[:, 2].astype(np.float64).tolist()

    impls = {
        "loop": {
            "pattern": lambda t: np.asarray(loop_fn(t, xs, ys, zs, seed), dtype=np.float64),
            "run": lambda t: np.asarray(pipeline_loop(loop_fn(t, xs, ys, zs, seed)), dtype=np.uint8),
        },
        "numpy": {
            "pattern": lambda t: numpy_fn(t, mapping, seed).astype(np.float64),
            "run": lambda t: pipeline_numpy(numpy_fn(t, mapping, seed)),
        },
    }
    if NUMBA_AVAILABLE:
        impls["numba"] = {
            "pattern": lambda t: numba_fn(t, mapping, seed).astype(np.float64),
            "run": lambda t: pipeline_numba(numba_fn(t, mapping, seed)),
        }
    return impls


RMS_TOL = 1e-4
MAXABS_TOL = 1e-3


def agreement_gate(ns: list[int]) -> None:
    """Verify all impls compute the same math before timing anything."""
    t_check = 0.5
    failures = []
    for n in ns:
        mapping = make_mapping(n)
        for kernel in KERNELS:
            impls = make_impls(kernel, mapping, SEED)
            ref_f = impls["numpy"]["pattern"](t_check)
            ref_u8 = impls["numpy"]["run"](t_check).astype(np.int16)
            for name, impl in impls.items():
                if name == "numpy":
                    continue
                f = impl["pattern"](t_check)
                rms = float(np.sqrt(np.mean((f - ref_f) ** 2)))
                maxabs = float(np.max(np.abs(f - ref_f)))
                lsb = int(np.max(np.abs(impl["run"](t_check).astype(np.int16) - ref_u8)))
                if rms > RMS_TOL or maxabs > MAXABS_TOL or lsb > 1:
                    failures.append(
                        f"  {kernel}/{name} @ N={n}: rms={rms:.2e} "
                        f"maxabs={maxabs:.2e} lsb={lsb}"
                    )
    if failures:
        print("AGREEMENT GATE FAILED — implementations disagree:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        sys.exit(1)
    print(f"agreement gate: OK ({len(KERNELS)} kernels × impls × N={ns})")


def time_impl(run, quick: bool) -> dict:
    """Warm up, calibrate frame count, time R reps; return per-rep stats."""
    ts_probe = FakeClock().frames(2, fps=60.0)
    for t in ts_probe:  # warmup (2 calls; numba compile handled by caller)
        run(t)
    t0 = time.perf_counter()
    run(FakeClock(start=1.0).frames(1)[0])
    probe_s = time.perf_counter() - t0

    target = 0.1 if quick else REP_TARGET_S
    reps = 3 if quick else REPS
    flagged_slow = False
    if probe_s > SLOW_PROBE_S:
        frames, reps, flagged_slow = FRAMES_MIN, 3, True
    else:
        frames = max(FRAMES_MIN, min(FRAMES_MAX, int(target / max(probe_s, 1e-7))))

    ts = FakeClock().frames(frames, fps=60.0)  # same deterministic ts each rep
    rep_ms = []
    for _ in range(reps):
        t0 = time.perf_counter()
        for t in ts:
            run(t)
        rep_ms.append((time.perf_counter() - t0) / frames * 1000.0)
    return {
        "frames_per_rep": frames,
        "reps_ms_per_frame": rep_ms,
        "median_ms": statistics.median(rep_ms),
        "min_ms": min(rep_ms),
        "max_ms": max(rep_ms),
        "flagged_slow": flagged_slow,
    }


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

    numba_version = None
    if NUMBA_AVAILABLE:
        import numba

        numba_version = numba.__version__

    return {
        "label": label,
        "date": datetime.date.today().isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "cpu_count": __import__("os").cpu_count(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numba": numba_version,
        "git_sha": try_cmd(["git", "rev-parse", "--short", "HEAD"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default=platform.node() or "unknown-host")
    ap.add_argument("--out", default=None, help="JSON output path")
    ap.add_argument("--quick", action="store_true", help="~5s smoke run, N=300 only")
    args = ap.parse_args()

    ns = [300] if args.quick else DEFAULT_NS
    gate_ns = [300] if args.quick else [300, 3_000]

    if not NUMBA_AVAILABLE:
        print("warning: numba unavailable — loop+NumPy datapoints only", file=sys.stderr)

    agreement_gate(gate_ns)

    meta = gather_meta(args.label)
    results = []
    jit_compile: dict[str, float] = {}

    for kernel in KERNELS:
        for n in ns:
            mapping = make_mapping(n)
            impls = make_impls(kernel, mapping, SEED)
            for name, impl in impls.items():
                if name == "numba" and kernel not in jit_compile:
                    t0 = time.perf_counter()
                    impl["run"](0.0)  # first call = JIT compile, timed separately
                    jit_compile[kernel] = time.perf_counter() - t0
                stats = time_impl(impl["run"], args.quick)
                fps = 1000.0 / stats["median_ms"]
                row = {
                    "kernel": kernel,
                    "impl": name,
                    "n": n,
                    "fps": fps,
                    "px_frames_per_s": n * fps,
                    **stats,
                }
                if name == "numba":
                    row["jit_compile_s"] = jit_compile[kernel]
                results.append(row)
                print(f"  timed {kernel}/{name} @ N={n}: {stats['median_ms']:.4f} ms/frame")

    # speedup vs the per-pixel loop at the same (kernel, N)
    loop_ms = {(r["kernel"], r["n"]): r["median_ms"] for r in results if r["impl"] == "loop"}
    for r in results:
        base = loop_ms.get((r["kernel"], r["n"]))
        r["speedup_vs_loop"] = (base / r["median_ms"]) if base else None
        r["r9_margin"] = r["px_frames_per_s"] / R9_TARGET_PX_FRAMES_PER_S

    print_tables(results)
    print_summary(results, meta)

    out_path = Path(args.out) if args.out else (
        Path(__file__).parent / "results" / f"throughput-{meta['date']}-{meta['label']}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {"meta": meta, "r9_target_px_frames_per_s": R9_TARGET_PX_FRAMES_PER_S, "results": results},
        indent=2,
    ) + "\n")
    print(f"\nresults written to {out_path}")


def print_tables(results: list[dict]) -> None:
    hdr = f"{'impl':<8} {'N':>7} {'ms/frame':>10} {'fps':>10} {'px·f/s':>12} {'vs loop':>9} {'R-9':>7}"
    for kernel in KERNELS:
        rows = [r for r in results if r["kernel"] == kernel]
        if not rows:
            continue
        print(f"\n== {kernel} ==")
        print(hdr)
        for r in rows:
            speedup = f"{r['speedup_vs_loop']:.1f}x" if r["speedup_vs_loop"] else "-"
            verdict = "PASS" if r["r9_margin"] >= 1.0 else "fail"
            flag = " *" if r["flagged_slow"] else ""
            print(
                f"{r['impl']:<8} {r['n']:>7} {r['median_ms']:>10.4f} {1000/r['median_ms']:>10.1f} "
                f"{r['px_frames_per_s']:>12.3g} {speedup:>9} {verdict:>7}{flag}"
            )
    if any(r["flagged_slow"] for r in results):
        print("\n* probe frame >2s — reduced to 3 frames × 3 reps")


def print_summary(results: list[dict], meta: dict) -> None:
    headline = [
        r for r in results
        if r["kernel"] == "plasma" and r["impl"] == "numpy" and r["n"] == max(r2["n"] for r2 in results)
    ]
    if headline:
        h = headline[0]
        verdict = "PASS" if h["r9_margin"] >= 1.0 else "FAIL"
        print(
            f"\nR-9 @ N={h['n']} (plasma, NumPy): {h['median_ms']:.3f} ms/frame → "
            f"{h['px_frames_per_s']:.3g} px·f/s = {h['r9_margin']:.1f}× the 1.2M target — "
            f"{verdict} on this host ({meta['cpu'] or meta['machine']}); Pi 5 pending"
        )


if __name__ == "__main__":
    main()
