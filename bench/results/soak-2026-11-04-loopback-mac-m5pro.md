# Aura rig soak — 2026-11-04, loopback-mac-m5pro

- bench: `bench/bench_soak.py` @ `4575cf4`; raw data `soak-2026-11-04-loopback-mac-m5pro.json`
- host: Apple M5 Pro, macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, GC thresholds (2000, 10, 10)
- rig: `python -m pewpew run soakwave --patterns /var/folders/7m/hk3_xjvj07xbnc25l_rw78dh0000gn/T/pewpew-soak-82u_26q3/patterns --room /var/folders/7m/hk3_xjvj07xbnc25l_rw78dh0000gn/T/pewpew-soak-82u_26q3/room/room.json --fps 60 --ddp-fps 40 --preview 58560 --looks /var/folders/7m/hk3_xjvj07xbnc25l_rw78dh0000gn/T/pewpew-soak-82u_26q3/looks/looks.json --trigger-log /var/folders/7m/hk3_xjvj07xbnc25l_rw78dh0000gn/T/pewpew-soak-82u_26q3/triggers.jsonl --armed --keep-awake --max-brightness 1`
- mode: loopback (local UDP listeners); room `room-60-bars.json`, boards A, B, C; render 60 fps, DDP 40 fps
- run: 19.9 min of 20.0 planned; seed 1; note: loopback on the dev laptop, mains power; other agent sessions may have been running
- A measurement, not a gate (T-5): distributions below, no pass/fail.

**Loopback run: no Wi-Fi, no WLED.** Every board in the room was moved to a
UDP listener on 127.0.0.1 in the driver process, which counts packets and
PUSH frames. What this answers for ADR-010: how often the collector runs
and how long it pauses with the real rig's allocations in play (DDP sink,
preview fan-out with client churn, slider sets through `call_soon`, look
recalls with crossfades, triggers, hot reloads), whether those pauses
reach the frame cadence, and whether memory, threads or modules grow over
the run. What it does not answer: Wi-Fi loss and latency, what each board
actually shows (`leds.fps`), board-side drift over hours (wled/WLED#4320),
or the router. The health poller ran but polled 127.0.0.1, where no WLED
answers, so its board data here is failures by construction. ADR-010's
other open caveat, the R-8 host (Pi 5 / N100), is not touched either.
The real-rig run of this bench answers the board side.

## Scripted actions

- look recalls sent: 15; trigger fires sent: 12; pattern edits: 5, rig logged 5 successful reloads
- churn client: 29 connects, 29 disconnects, 2900 slider sets, 0 refused, 0 errors

## Frame pacing

Interval between consecutive frames handed to the sinks, from 5 s on; period 16.67 ms. The first 300 intervals (startup) are left out; the longest was 24.8 ms.

| metric | n | min | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| interval ms | 71699 | 0.16 | 16.49 | 21.26 | 24.19 | 34.07 |
| abs error ms | 71699 | 0.00 | 2.21 | 5.38 | 7.61 | 17.40 |

- 60.00 fps over 71700 frames; 9347 intervals off by more than 5 ms, 2 by more than a frame (0 of them with a GC pause inside)
- deadline skips: 4 events, 0 schedule slots skipped; gaps over 5 s (the unattended run's watchdog timeout): 0
- sink drivers at the end (dropped = coalesced by newest-wins, expected when a sink's rate is below the loop's): PreviewSink dropped 35998, errors 0; DdpSink dropped 23998, errors 0, frames sent 48000

## GC

5 collections, 4.0 ms in total; 0 longer than one frame period. Counts by generation from the callback: [5, 0, 0].

| generation | n | min ms | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| 0 | 5 | 0.146 | 0.266 | 1.732 | 1.857 | 1.871 |
| all | 5 | 0.146 | 0.266 | 1.732 | 1.857 | 1.871 |

## Per-board delivery

Counted at the listener per 10 s window; the DDP sink sent 48000 frames to each board.

| board | windows | min fps | p50 | p90 | p99 | max | frames | incomplete |
|---|---|---|---|---|---|---|---|---|
| A | 119 | 39.90 | 40.00 | 40.02 | 40.09 | 40.09 | 48001 | 0 |
| B | 119 | 39.90 | 40.00 | 40.02 | 40.09 | 40.09 | 48001 | 0 |
| C | 119 | 39.90 | 40.00 | 40.02 | 40.09 | 40.09 | 48001 | 0 |

## Process

Sampled every 10 s; slope fitted after the first 120 s.

| series | first | last | min | max | slope |
|---|---|---|---|---|---|
| RSS KB | 48000 | 37744 | 34864 | 48000 | +3623.7 KB/h |
| threads | 12 | 12 | 12 | 16 | +0.1 threads/h |
| modules | 442 | 442 | 442 | 442 | +0.0 modules/h |

Thread groups that changed first→last sample: none.

## Largest intervals over one frame of error (top 2)

| t s | interval ms | GC ms inside | gens | nearest rig log line (±2 s) |
|---|---|---|---|---|
| 689.5 | 34.1 | 0.00 | - | - |
| 674.4 | 33.6 | 0.00 | - | recalled look soak-b |

## Reading (written 2026-11-04, after the run)

- **GC, ADR-010's open caveat.** The rig ran with all three things ADR-010
  named (sinks, the param tree under 2,900 slider sets, 5 hot reloads) plus
  15 look recalls, 12 trigger fires and 29 client connects. The collector
  ran 5 times in 20 minutes, all generation 0, the longest 1.87 ms (11% of
  a frame period). Generations 1 and 2 never ran. No interval that lost a
  frame of cadence had a GC pause inside it. On this host and Python
  (3.14.7, thresholds 2000/10/10), GC is not a pacing risk for this rig.
  Inference: the rig allocates few gc-tracked containers per frame, and
  the cyclic garbage that reloads and recalls leave (`gc.get_stats()`
  counts about 3,700 objects collected over the run) is cleared by those
  few young collections.
- **Pacing.** p99 cadence error 7.61 ms, max interval 34.1 ms, 2 intervals
  more than a frame off, 4 deadline skips with no slot lost. The
  2026-07-27 pacing soak on the same host measured p99 3.78 ms, but it
  timed the start of each tick; this bench times the hand-off to the sinks,
  after the render, so render-time variation is inside these intervals.
  Not measured here, an inference: the rest of the difference is the sink
  worker threads sharing the GIL with the loop (switch interval 5 ms).
  GC is ruled out as the cause by the row above.
- **Leaks.** Threads: 12 at rest, 16 while the churn client is connected,
  back to 12 after each of the 29 disconnects. Modules: 442 throughout, so
  reloads and recalls do not pile up modules. RSS moved between 35 and
  43 MB with no visible trend: median 37.1 MB in minutes 2-10 and 38.2 MB
  in minutes 10-20, max 43.1 and 43.0 MB. The fitted +3.6 MB/h is inside
  that noise over 18 minutes; the hours-long run settles it.
- **Delivery.** Every frame the DDP sink sent reached its listener whole
  (0 incomplete). The listener counts 48,001 frames against the sink's
  48,000 because the sink's count is from the last sample row and the
  listener's from the end of the run.

**Addendum 2026-11-06.** Wording only: names in this report follow the
RA-29 rename. The measurements and their source commit are unchanged.
