# bench/ — Phase-0 host microbenchmarks

One-off L1 host benchmarks (test-and-feedback.md §4), **not** pytest rigs
and not collected by `uv run pytest`. Each run writes a JSON artifact to
`bench/results/`; artifacts are committed (they're the evidence).

## bench_throughput.py — §12 item 1 (R-9, gates ADR-011)

Per-pixel Python loop vs vectorized NumPy vs Numba `@njit` on identical
pattern math + pipeline tail, N ∈ {300, 3k, 30k}. R-9 target: 1.2M
px·frames/s (20k px × 60 fps) on a Pi 5-class host.

```sh
uv run --group bench python bench/bench_throughput.py --label <host>
# ~5s smoke check (N=300 only):
uv run --group bench python bench/bench_throughput.py --quick
```

Numba comes from the `bench` dependency group (PEP 735) — deliberately not
a project dependency (ADR-011 keeps the compiled tier an escape hatch until
this bench settles it). If numba can't resolve on the venv's Python, either
run `uv run --python 3.13 --group bench ...` or just let the script degrade:
it reports the numba column as unavailable and still produces the
loop+NumPy datapoints. Note: numba pins numpy back within the bench env
(e.g. 2.5→2.4); the JSON metadata records the versions actually used.

Methodology (details in the script docstring): agreement gate first (all
impls must match the NumPy reference within RMS 1e-4 / max-abs 1e-3 / 1 LSB
on the quantized frame), deterministic FakeClock timestamps, 2-call warmup,
numba JIT compile timed separately (`jit_compile_s`), frame count
calibrated to ~0.3 s/rep, 5 reps, median-of-rep-means reported, all rep
values kept in the JSON (results are distributions, T-5).

### Status

- [x] Desktop datapoint: `results/throughput-2026-07-15-mac-m5pro.json`
      (Apple M5 Pro). NumPy @ 30k px: 52× the R-9 target — PASS.
- [ ] **Pi 5 rerun** (`--label pi5`) — the host R-9 actually names.
      Only after that datapoint lands does ADR-011 get its verdict
      recorded (promote-or-not the compiled tier) and R-9's
      "no published benchmark" caveat cleared in requirements.md.

## bench_pacing.py — §12 item 13 (gates ADR-010)

Pacing-jitter soak. Item 1 benched *throughput* — how long a frame takes.
This benches *pacing* — whether the next frame starts when it should. They
fail independently: a host with 50× throughput margin can still miss
deadlines, and device-side keyframe interpolation (Phase 4) is hostage to
cadence consistency, not to average speed.

```sh
uv run python bench/bench_pacing.py --label <host>
uv run python bench/bench_pacing.py --quick     # ~60 s smoke run
```

Three pacers run head to head over a 16.67 ms tick:

| Pacer | What it is |
|---|---|
| `deadline` | ADR-010's — absolute schedule, accumulated error corrected |
| `deadline_spin` | same, but sleeps short of the deadline (margin derived from the measured overshoot) and busy-waits the rest |
| `naive` | LedFx / led-control's compensated sleep, no accumulated-error term — ADR-010's rejected alternative [S630][S660] |

The headline metric is **cadence** — the gap between consecutive tick starts,
minus the period. That is what device-side keyframe interpolation depends on:
whether frame k+1 lands one period after frame k, not where either sits in
absolute time.

Phase against an ideal schedule (`t_start + k·period`) is also recorded, but
read it for *slope* only. It catches the naive pacer, which is never late
against its own re-based deadline and just silently runs slow. It is misleading
as a magnitude: when the deadline pacer absorbs a stall by skipping ahead
(ADR-010's newest-wins rule) the phase offset persists for the whole run while
cadence stays tight. Scoring phase reported "every tick is 70 ms late" on a run
whose cadence p99 was under 7 ms.

Load conditions: `idle`, `render` (plasma NumPy at 20k px from `bench/common.py`
— the same kernel `bench_throughput.py` times, imported rather than copied),
and `render+audio` — the last adds a thread waking every 11.6 ms (44.1 kHz /
512-frame blocks) doing an rfft, standing in for the capture thread's GIL
contention. GC stays enabled and every collection is timed via `gc.callbacks`;
the run also probes bare `time.sleep()` overshoot at 1 ms and at the frame
period, which is the floor no pacer can beat and from which the spin pacer's
margin is derived.

Headline run is what item 13 specifies: `deadline` + `render+audio`, 10 min.
It runs **first**, on a cold machine, before the 60 s sweep cells — two of
which pin a core — so thermal state is not confounded with the reported result.
The JSON is rewritten after every cell, so a crash or Ctrl-C keeps whatever
completed. Results are a distribution — percentiles, late-tick counts,
cumulative drift and a histogram go to the JSON (T-5).

### Status

- [x] Desktop datapoint: `results/pacing-2026-07-27-mac-m5pro.{md,json}`
      (Apple M5 Pro). p99 cadence error 3.78 ms over a 10-min soak, 1 of
      35 995 intervals off by a full frame, 59.99 fps — **PASS on this host**.
      The residual jitter is the OS sleep timer (3.82 ms median overshoot at
      this period), not CPython. The `naive` pacer ADR-010 rejects measures
      51.17 fps and 8.8 s of drift per minute.
      A 2026-07-26 run was published and withdrawn — a skip-ahead off-by-one
      and a run order that let the headline inherit thermal state from two
      core-pinning cells. Both fixed; see the report's *Superseded run*.
- [ ] **Pi 5 (or whichever host is chosen) rerun** (`--label pi5`) — R-8 names
      a Pi 5 / N100-class machine; a desktop only bounds it. ADR-010 stays
      Proposed until then: the mechanism is confirmed, the host is not.
- [ ] Re-run once Phase 1 adds the parameter tree, sinks and hot reload. The
      soak saw **zero** GC collections because a pure-NumPy render loop
      allocates arrays, not gc-tracked containers — so ADR-010's GC worry is
      untested, not cleared.

## bench_authoring.py — §12 item 2 (gates ADR-005)

Authoring-surface study: the five canonical patterns (plasma, comet, geq,
fire, sdf3d in `bench/authoring/`) written against a minimal prototype of
the ADR-005 contract (`before_render(dt, features)` + `render(x, y, z,
index)` + persistent `self.pixels` + Pixelblaze-style idiom kit, all in
`bench/authoring/surface.py` — throwaway, superseded by the Phase-1 engine).
Each pattern file is the artifact: author-facing code plus `# STUMBLE-N`
annotations at the exact line of every scalar→array friction point.

```sh
uv run python bench/bench_authoring.py           # validate + JSON artifact
uv run python bench/bench_authoring.py --show    # ANSI eyeball
```

The runner validates output (shape/dtype/finite/[0,1]), gates on
determinism (full 120-frame sequence twice from fresh instances must hash
identically), and emits the mechanical census (np.where + STUMBLE tags per
file). The deliverable is the hand-written inventory, not the runner
output.

### Status

- [x] Study complete: `results/authoring-2026-07-16.md` (inventory +
      verdict) and `results/authoring-2026-07-16.json`. Zero blockers,
      17 stumbles (4 hit / 13 shielded) — **GO conditional on idiom-kit
      additions**, listed in the report.
- [x] ADR-005 status flip (Proposed → Accepted) — signed off 2026-07-26;
      the report's proposed note is now ADR-005 § Verification.

### Caveats on reading the numbers

- The per-pixel loop here is a tight, locals-bound inline loop over Python
  floats — a best case. Framework-style per-pixel engines (function call
  per pixel, HSV conversion) are far slower (led-control's ~22.5k px/s
  [S660]); don't read the loop rows as "CPython passes R-9".
- The numba kernels compute in float64 scalar math (to match the loop spec
  for the agreement gate); NumPy computes float32 SIMD. On the
  transcendental-heavy plasma kernel this makes numba *slower* than NumPy
  at N≥3k on Apple Silicon (scalar libm sin vs vectorized f32 sin). A
  production numba tier would use f32 + fastmath; treat the numba rows as
  a floor, not its ceiling.
