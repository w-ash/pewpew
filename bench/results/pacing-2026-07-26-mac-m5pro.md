# §12 item 13 — pacing-jitter soak, desktop datapoint

- date: 2026-07-26
- host: Apple M5 Pro (14 cores), macOS, CPython 3.14.3, NumPy 2.5.0
- bench: `bench/bench_pacing.py`; raw data `pacing-2026-07-26-mac-m5pro.json`
- claim under test: *"CPython paces a 16.7 ms tick with low jitter under real
  load"* — ADR-010's silent dependency (GC pauses, GIL contention with the
  capture thread, sleep quantization)

**Verdict: PASS on this host.** CPython holds the tick. The residual jitter is
the OS sleep timer, not the interpreter — and ADR-010's rejected alternative
fails hard enough to be visible without instruments.

**This is a desktop datapoint, not the R-9 host.** R-8 names a Pi 5 or
N100-class machine. Rerun with `--label pi5` before treating any of this as
settled for a deployed host.

## Headline soak — 10 min, deadline pacer, render+audio, 20k px

| Metric | Value |
|---|---|
| Cadence error, p50 / p99 / p99.9 | 1.53 / 6.98 / 7.91 ms |
| Cadence error, max | 81.8 ms |
| Signed interval error, mean ± σ | **+0.004 ± 2.66 ms** |
| Intervals off by ≥ one frame | **2 of 35 991** |
| Achieved rate | 59.98 fps (drift +153 ms over 600 s) |
| GC collections | **0** |
| Audio blocks processed | 51 680 |

Cadence = gap between consecutive tick starts minus the 16.67 ms period. Full
histogram in the JSON; the tail is 23 intervals in the 8–16.7 ms bucket and 2
above 33 ms.

## What the numbers say

**1. The jitter floor is the OS, not CPython.** A bare `time.sleep(16.67 ms)`
overshoots by 3.70 ms median / 4.22 ms p99 on this machine. The deadline
pacer's p99 in the 60 s cells is 3.73–3.90 ms — it lands *on* the floor. There
is no interpreter overhead left to optimize away; the remaining error is timer
granularity.

**2. ADR-010's deadline correction is vindicated, and the margin is not
subtle.** The rejected alternative — LedFx / led-control's compensated sleep
with no accumulated-error term — was rejected on a code read
[S630:ledfx/virtuals.py#L864-L877][S660:ledcontrol/intervaltimer.py]. Measured:

| Pacer | Signed interval error (mean) | Achieved rate | Drift over 60 s |
|---|---|---|---|
| `deadline` (ADR-010) | +0.00 ms | 59.98 fps | +21 ms |
| `naive` (rejected) | **+2.75 ms** | **51.49 fps** | **+8 509 ms** |

The naive pacer is late by 2.75 ms on *every single frame* — it never notices,
because it re-bases its deadline on each wake. The result is a silent 14 % rate
error and 8.5 seconds of drift per minute. Nothing in its own error signal
would ever reveal this; only an external reference does.

**3. GC was a non-issue — for this workload.** Zero collections in 10 minutes.
The NumPy render path allocates arrays, which are not gc-tracked containers, so
gen-0 never filled. ADR-010's GC worry is real in principle but does not bite a
pure-NumPy render loop. **It is not cleared for Phase 1**, which adds a
parameter tree, sink objects and hot-reload machinery — all of which do
allocate tracked containers. Re-run this bench once those exist.

**4. Sub-millisecond cadence is available if it turns out to be needed.**
Sleeping ~6 ms short of the deadline and busy-waiting the remainder
(`deadline_spin`) gives p99 cadence error of 0.009–0.068 ms and exactly 60.00
fps, at the cost of a spinning core. Not the default — but the answer exists if
§12 item 11 (device-side keyframe interpolation) finds ~7 ms of host jitter
visible.

## Method notes and caveats

- **Cadence, not phase.** The first run of this bench scored ticks against an
  absolute schedule (`t_start + k·period`). That is wrong for a pacer that
  deliberately skips ahead: three skips over the soak (150 ms absorbed, ADR-010's
  newest-wins rule) each step phase permanently, so the metric reported "every
  tick is 70 ms late" while the cadence was in fact tight. Phase error is kept in
  the JSON — read it for *slope* (drift), not magnitude. The headline metric is
  the interval between consecutive ticks.
- The audio thread is a **stand-in**, not a device: a thread waking every
  11.6 ms (44.1 kHz / 512-frame blocks) doing an rfft. A real capture device
  would add driver-side jitter that could not be attributed to CPython. This
  isolates the GIL contention ADR-010 actually names.
- Measured on a machine that was otherwise near-idle but not quiesced — no
  attempt was made to pin cores, raise priority, or disable turbo. That is
  deliberate: it is the condition the engine will actually run in.
- Single run, single host. Per T-5 this is a distribution, not a point value,
  and it is one sample of the distribution over hosts.

## Reproduce

```sh
uv run python bench/bench_pacing.py --label mac-m5pro
uv run python bench/bench_pacing.py --quick        # ~40 s smoke run
```

## Open

- [ ] Pi 5 (or whatever host is chosen) rerun — `--label pi5`. Until then
      ADR-010 stays Proposed: the mechanism is confirmed, the host is not.
- [ ] Re-run after Phase 1 lands the parameter tree and sinks, to retest the GC
      finding against a workload that allocates tracked containers.
