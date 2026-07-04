# ADR-010: Frame pipeline — one paced clock, newest-wins backpressure

Status: Proposed (2026-07-03)

## Context

The host engine must render at 60 fps (R-2) and feed sinks with different
rates and stall behaviors without letting a slow sink drag the render loop
or a fast one accumulate latency. LedFx — the closest prior art — runs a
thread per virtual and does DSP in the audio callback, both of which its
own code comments document as pain; its compensated sleep also drifts under
scheduler jitter.

## Decision

- **One paced render clock**, deadline-corrected: measure elapsed, sleep
  the remainder, correct accumulated error (LX's fixed-rate executor is the
  reference). No thread-per-virtual; no DSP in the audio callback
  (ADR-009).
- **Per-sink split with newest-wins backpressure**: each sink paces itself
  at its own output rate from the latest completed frame; if a sink is
  busy, pending frames coalesce — bounded to ~2 in flight, never queued
  deeper.
- **Pattern motion is time-parameterized** (Q-5): dropped or late frames
  slow nothing.
- **Loss policy at receivers**: hold last frame, then revert to local
  effects after a sender-set timeout (P-6, R-6) — inherited from the WLED
  realtime-lock contract and specified for the Phase-4 receiver too.
- Crossfade transitions blend two rendered frames from one engine, never
  two running engines.

## Consequences

- Latency stays bounded at every sink regardless of relative rates; a
  stalled WiFi sink can never back up the renderer.
- Frame skew between sinks of one canvas is bounded by one frame period;
  actual multi-receiver latch skew is transport-level (ADR-003, prototype
  item #3).
- The single clock is the natural place to resolve modulated parameters
  (ADR-006) and audio features (ADR-009) exactly once per frame.

## Evidence

- [S264] LX's fixed-rate engine executor (60 fps default) — the clean
  pacing reference. License posture: LX is source-available under a custom
  non-OSI license; this was a design-pattern read only (recorded per
  ADR-012 rule 3) — pewpew's clock is implemented from this documented
  finding, with no LX code copied or ported.
- [S630:ledfx/virtuals.py#L864-L877] LedFx's per-virtual thread loop with
  compensated sleep that drifts under scheduler jitter — the anti-pattern.
- [S630:ledfx/virtuals.py#L746-L779]
  [S630:ledfx/devices/artnet.py#L176-L179] LedFx's own comments documenting
  thread-per-virtual and callback-thread pain.
- [S600:server/src/fcdevice.cpp#L362-L382] Fadecandy's
  `MAX_FRAMES_PENDING=2` with keyframe coalescing — the bounded
  newest-wins precedent.
- [S700:sources/led-drivers/LedDevice.cpp#L537-L546] HyperHDR's
  latest-wins frame drop at the driver — independent confirmation of the
  same policy.
- [S645:wled00/udp.cpp#L410-L456][S253] WLED's realtime timeout re-armed
  per packet, then fallback to local state — the hold/revert contract
  (P-6).
- [S680:README.expressions.md#L23][S715:docs/architecture.md#L403-L414]
  Pixelblaze's delta-time convention and projectMM's "must animate at
  every tick rate" rule — time-parameterized motion (Q-5).
- [S660:ledcontrol/intervaltimer.py] led-control's compensated timer —
  same approach as LedFx, same missing error accumulation.

## Rejected alternatives

- **Thread-per-virtual** (LedFx) — documented as a pain point in its own
  source [S630:ledfx/virtuals.py#L746-L779].
- **DSP/render work in the audio callback** (LedFx) — priority inversion
  and jitter in the capture path
  [S630:ledfx/effects/audio.py#L1138-L1141].
- **Deep per-sink frame queues** — accumulate latency instead of dropping
  stale frames; both quality references bound at ~2 [S600][S700].
- **Frame-counted animation** — dropped frames change speed; violates Q-5
  [S680][S715].
- **Blocking the render loop on the slowest sink** — one WiFi outlier
  (~25 ms tails measured [S166]) would stall every other output.
