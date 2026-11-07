# bench/ — Phase-0 host microbenchmarks

One-off L1 host benchmarks (test-and-feedback.md §4), **not** pytest rigs
and not collected by `uv run pytest`. Each run writes a JSON artifact to
`bench/results/`; artifacts are committed (they're the evidence).

## bench_throughput.py — §12 item 1 (R-9, gates ADR-011)

Per-pixel Python loop vs vectorized NumPy vs Numba `@njit` on identical
pattern math + pipeline tail, N ∈ {300, 3k, 30k}. R-9 target: 1.2M
px·frames/s (20k px × 60 fps) on a Pi 5-class host.

```sh
uv run --group bench python -m bench.bench_throughput --label <host>
# ~5s smoke check (N=300 only):
uv run --group bench python -m bench.bench_throughput --quick
```

Numba comes from the `bench` dependency group (PEP 735) — deliberately not
a project dependency (ADR-011 keeps the compiled tier an escape hatch until
this bench settles it). If numba can't resolve on the venv's Python, the
script reports the numba column as unavailable and still produces the
loop+NumPy datapoints.

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
uv run python -m bench.bench_pacing --label <host>
uv run python -m bench.bench_pacing --quick     # ~60 s smoke run
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
      untested, not cleared. First retest: `bench_soak.py`'s loopback run
      (`results/soak-2026-11-04-loopback-mac-m5pro.md`) saw 5 generation-0
      collections in 20 min of the full rig, max pause 1.87 ms.

## bench_wifi.py — §12 item 14 for a real rig

Wi-Fi ingest on the real rig: DDP through `DdpSink` to every board at once
(default 1,280 px per board) at 40, 50 and 60 fps, k trials per rate, while a
separate thread polls each board's `/json/info` (never the full `/json`) one
board at a time. Per board per rate it reports `leds.fps` against the sent
rate as min/p10/median/p90, the RSSI range, trials with a reboot and pass^k
— a distribution, never a gate (T-5).

```sh
uv run python -m bench.bench_wifi IP1 IP2 IP3 --dry-run   # plan only
uv run python -m bench.bench_wifi IP1 IP2 IP3 --label <rig> --note "<router settings>"
```

Streaming is tier-1 bench actuation: `--dry-run` first, and a real run
appends an audit record (`pewpew.audit`, `$PEWPEW_AUDIT_LOG`). A run writes
`results/wifi-<date>-<label>.{json,md}` and refuses to overwrite either.

### Status

- [ ] First run on a real rig (three ESP32-S3 boards, WLED v16.0.1), then
      v0.15.4 for comparison (wled/WLED#5575).

## bench_soak.py — the live rig soak and ADR-010's GC retest

Runs the whole live rig as `python -m pewpew run` wires it, for hours: the
60-bar example room (or `--room`), DDP to its boards (or `--loopback`, a
local UDP listener per board), the preview with a control client and a
churn client that connects, drags a slider and disconnects, look recalls
with fades, armed trigger fires, and several hot reloads of a pattern copy
it edits. All schedules come from `--seed`. It records GC collections per
generation and their pauses (`gc.callbacks`), frame intervals and their
outliers (each with the GC time inside it), skipped slots, per-board
delivered fps (listener counts, or the health poller's `leds.fps` and
`uptime` on real boards), and RSS, threads and modules over time. The
clients, listeners, edits and RSS sampling run in a child process, so
their allocations stay out of the GC counts.

```sh
uv run python -m bench.bench_soak --loopback --duration 1200 --label loopback-<host>
uv run python -m bench.bench_soak --dry-run                  # plan only
uv run python -m bench.bench_soak --label <rig> --note "<router settings>"   # real boards, 4 h
```

Real boards are tier-1 bench actuation: `--dry-run` first; a real run
appends a `bench-soak` audit record before the rig starts. A run writes
`results/soak-<date>-<label>.{json,md}`, refuses to overwrite either, and
rewrites the JSON every minute so a killed run keeps its data. A
distribution, never a gate (T-5).

### Status

- [x] Loopback datapoint: `results/soak-2026-11-04-loopback-mac-m5pro.{md,json}`
      (20 min). No Wi-Fi and no WLED: it answers the GC and leak side only.
- [ ] Real-rig run on WLED boards (hours), for `leds.fps` drift and the
      network side.

## Authoring study — §12 item 2 (gated ADR-005)

The authoring-surface study wrote five canonical patterns against a
prototype of the ADR-005 contract. The pattern contract is gone (ADR-025)
and its prototype with it; the report stays as history.

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

## bench_critic.py — taste of made looks (evidence, never a gate)

Makes K looks from a seed (`pewpew.fx.surprise`), renders them, and writes
`bench/results/critic-<label>/`: the looks, one numbered sheet of all of
them, and an A/B sheet of every pair both ways round, with a manifest. A
person or the `look-critic` subagent judges each pair in both orders and
writes the verdicts into the manifest; `--tally` counts each look's wins,
leaving out a pair whose two orders disagree. The script's docstring has
the procedure.

```sh
uv run python -m bench.bench_critic --label mac --k 6 --seed 1 --map grid:16x16
uv run python -m bench.bench_critic --tally bench/results/critic-mac/manifest.json
```

## bench_audio.py — RA-28 M2's attended replug test (tier 1)

Opens one live input as an unattended run does and asks the person at the
bench to unplug and replug it `--trials` times; each trial passes when the input
reads lost within 30 s and listens again within 60 s. pass^k, never a gate
(T-5). A person runs it, never an agent: opening an input is a privacy act, so `--dry-run`
comes first and a real run writes an `audio-input` audit record before the
first open. The procedure is `docs/audio.md` §7.

```sh
uv run python -m bench.bench_audio "Scarlett 2i2 USB" --dry-run
uv run python -m bench.bench_audio "Scarlett 2i2 USB" --trials 5 --label mac
```

### Status

- [ ] First attended run on the Mac (`results/audio-replug-<date>-mac.json`).
