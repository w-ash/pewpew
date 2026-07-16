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
