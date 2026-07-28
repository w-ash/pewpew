# §12 item 13 — pacing-jitter soak, desktop datapoint

- date: 2026-07-27
- host: Apple M5 Pro, 15 logical CPUs, macOS 26.4.1 (arm64)
- toolchain: CPython 3.14.3, NumPy 2.4.6 — read from the run's own JSON meta
- bench: `bench/bench_pacing.py` @ `09c1ff8`; raw data `pacing-2026-07-27-mac-m5pro.json`
- claim under test: *"CPython paces a 16.7 ms tick with low jitter under real
  load"* — ADR-010's silent dependency (GC pauses, GIL contention with the
  capture thread, sleep quantization)

**Verdict: PASS on this host.** CPython holds the tick. The residual jitter is
the OS sleep timer, not the interpreter — and ADR-010's rejected alternative
fails hard enough to be visible without instruments.

**This is a desktop datapoint, not the R-9 host.** R-8 names a Pi 5 or
N100-class machine. Rerun with `--label <host>` before treating any of this as
settled for a deployed host.

> **Supersedes the 2026-07-26 run**, which was withdrawn — see *Superseded run*
> at the end. Two defects in the harness, not the host: an off-by-one in the
> skip-ahead path, and a run order that let the headline inherit thermal state
> from two core-pinning cells. Both are fixed here; the corrected headline p99
> is 3.78 ms against the withdrawn 6.98 ms.

## Headline soak — 10 min, deadline pacer, render+audio, 20k px

| Metric | Value |
|---|---|
| Cadence error, p50 / p99 / p99.9 | 0.92 / 3.78 / 4.05 ms |
| Cadence error, max | 98.4 ms (one interval) |
| Signed interval error, mean ± σ | **+0.002 ± 1.67 ms** |
| Intervals off by ≥ one frame | **1 of 35 995** |
| Intervals > 5 ms off | 19 of 35 995 (0.05 %) |
| Achieved rate | 59.99 fps (drift +86 ms over 600 s) |
| Deadline skips | 2 (83 ms absorbed) |
| GC collections | **0** |
| Audio blocks processed | 51 672 |

Cadence = gap between consecutive tick starts minus the 16.67 ms period. The
histogram tail is 62 intervals in 4–8 ms, 7 in 8–16.7 ms, and a single one
above 33 ms.

## What the numbers say

**1. The jitter floor is the OS, not CPython.** A bare `time.sleep(16.67 ms)`
overshoots by 3.82 ms median / 4.21 ms p99 on this machine. The pacer's
headline p99 is 3.78 ms and its sweep cells are 3.82–3.94 ms — it lands *on*
the floor, and the headline now agrees with the sweep rather than sitting 2×
above it. There is no interpreter overhead left to optimize away.

**2. ADR-010's deadline correction is vindicated, and the margin is not
subtle.** The rejected alternative — LedFx / led-control's compensated sleep
with no accumulated-error term — was rejected on a code read
[S630:ledfx/virtuals.py#L864-L877][S660:ledcontrol/intervaltimer.py]. Measured
over 60 s at matched load:

| Pacer | Signed interval error (mean) | Achieved rate | Drift over 60 s |
|---|---|---|---|
| `deadline` (ADR-010) | +0.00 ms | 60.00 fps | +2.7 ms |
| `naive` (rejected) | **+3.48 ms** | **51.17 fps** | **+8 831 ms** |

The naive pacer is late on *every single frame* — it never notices, because it
re-bases its deadline on each wake. The result is a silent 15 % rate error and
8.8 seconds of drift per minute. Nothing in its own error signal would reveal
this; only an external reference does.

**3. GC was a non-issue — for this workload.** Zero collections in 10 minutes.
The NumPy render path allocates arrays, which are not gc-tracked containers, so
gen-0 never filled. ADR-010's GC worry is real in principle but does not bite a
pure-NumPy render loop. **It is not cleared for Phase 1**, which adds a
parameter tree, sink objects and hot-reload machinery — all of which do
allocate tracked containers. Re-run this bench once those exist.

**4. Sub-millisecond cadence is available if it turns out to be needed.**
Sleeping short of the deadline and busy-waiting the remainder (`deadline_spin`)
gives p99 cadence error of 0.003–0.006 ms and exactly 60.00 fps, at the cost of
a spinning core. The margin is derived from the measured sleep overshoot
(6.32 ms here) rather than hardcoded, so it adapts to a host with a tighter
timer. Not the default — but the answer exists if §12 item 11 (device-side
keyframe interpolation) finds ~4 ms of host jitter visible.

**5. There is a real tail.** One interval of 98 ms and two deadline skips over
10 minutes. Rare — 1 in 36 000 — but not zero, and a 98 ms gap is six frames.
Whatever consumes it (scheduler, page fault, background daemon) is outside the
loop's control, which is exactly why ADR-010 specifies discarding the backlog
rather than chasing it. Worth re-checking on the deployed host, where the tail
may be fatter.

## Method notes and caveats

- **Cadence, not phase.** Ticks are scored on the interval between consecutive
  starts. Phase against an absolute schedule is also recorded but should be
  read for *slope* only: when the pacer absorbs a stall by skipping ahead, the
  phase offset persists for the run while cadence stays tight, so phase
  magnitude reports a single stall as though every later tick were late.
- **Headline runs first, on a cold machine.** The 60 s sweep cells — two of
  which pin a core — run after it. In the withdrawn run the order was reversed
  and the headline read 2× worse than the identical sweep cell.
- The audio thread is a **stand-in**, not a device: a thread waking every
  11.6 ms (44.1 kHz / 512-frame blocks) doing an rfft. It uses the same
  skip-ahead rule as the render pacer, so a stall makes it drop blocks like a
  real capture device rather than bursting rffts back-to-back and manufacturing
  the GIL contention this bench is trying to measure.
- The render kernel is imported from `bench/common.py` — the same function
  `bench_throughput.py` times, not a copy of it.
- Measured on a machine that was otherwise near-idle but not quiesced — no
  core pinning, priority changes, or turbo control. That is deliberate: it is
  the condition the engine will actually run in.
- Single run, single host. Per T-5 this is a distribution, not a point value,
  and it is one sample of the distribution over hosts.

## Superseded run — 2026-07-26 (withdrawn)

The first full run was published and then withdrawn after review found two
defects in the harness. Its artifacts are not in the tree; they are in git
history at `09c1ff8`. Both defects flattered nothing — they made the result
look *worse* — but both invalidated it:

1. **Skip-ahead off-by-one.** `missed = int(-slack // PERIOD_S) + 1` advanced
   the deadline to the next future grid slot, but the following iteration then
   added another full period before testing slack, consuming that slot. Every
   blown deadline therefore dropped one more frame than intended. Reported 3
   skips / 150 ms absorbed; the corrected pacer reports 2 / 83 ms.
2. **Run-order confound.** The headline soak ran *after* nine sweep cells, two
   of which pin a core for 60 s, with no cooldown — so thermal/DVFS state was
   confounded with the headline. It reported p99 6.98 ms while the identical
   60 s cell reported 3.81 ms, and the report drew its "lands on the OS floor"
   conclusion from the sweep while quoting the headline in its verdict. With
   the headline first the two agree.

The withdrawn report also stated the host as "14 cores, NumPy 2.5.0" against
the run's own JSON (`cpu_count: 15`, `numpy: 2.4.6`) — written from memory
rather than from the artifact. This report's host line is copied from the JSON.

## Reproduce

```sh
uv run python bench/bench_pacing.py --label mac-m5pro
uv run python bench/bench_pacing.py --quick        # ~60 s smoke run
```

## Open

- [ ] Rerun on whichever host gets deployed (`--label <host>`). Until then
      ADR-010 stays Proposed: the mechanism is confirmed, the host is not.
- [ ] Re-run after Phase 1 lands the parameter tree and sinks, to retest the GC
      finding against a workload that allocates tracked containers.
