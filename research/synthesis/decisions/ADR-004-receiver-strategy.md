# ADR-004: Receiver strategy — stock WLED first, custom firmware later

Status: Proposed (2026-07-03)

## Context

Portable/room tiers need network receivers that turn DDP frames into pixel
waveforms (P-6, R-1). Options: adopt stock firmware (WLED), commercial
Ethernet controllers, or write pewpew receiver firmware. Custom firmware
would unlock device-side interpolation+dithering (ADR-002 tier 4) but is a
whole embedded project; the engine must not block on it.

## Decision

- **Day one: stock WLED as the dumb receiver.** It already implements the
  needed contract: DDP ingest with offset + Push render flag, realtime
  preemption of local effects, timeout fallback to local state (P-6).
- **Room backbone: Ethernet pixel controllers** (Falcon F16v5 /
  QuinLED-Octa class) fed DDP/sACN (ADR-013).
- **Existing Pixelblaze output expanders reused** as host-driven serial
  sinks (UPXL, open/MIT).
- **Phase 4: pewpew receiver firmware (ESP32-S3)** adding what stock WLED
  cannot: keyframe interpolation + ≥400 Hz temporal dithering device-side.
- Sender-side caveats codified in the WLED sink: pin receiver brightness to
  255 or compensate for its scaling (WLED applies master brightness to
  realtime data; its gamma is off by default), and don't rely on the DDP
  timecode flag.

## Consequences

- pewpew is useful on the user's existing fleet immediately; receiver
  quality improves later without engine changes (sinks abstract it).
- Until Phase 4, 8-bit sinks get only host-side dithering (ADR-002 tier 3)
  — effective on slow fades, not full depth.
- Local-effect fallback behavior (hold last frame, revert after timeout)
  is inherited from WLED's realtime-lock contract and becomes the spec for
  the custom receiver too.

## Evidence

- [S645:wled00/e131.cpp#L20-L93][S645:wled00/udp.cpp#L410-L456] WLED's DDP
  ingest honors offset+Push and re-arms a realtime timeout on every packet,
  then falls back to local state — the exact preempt/hold/revert contract
  (P-6).
- [S253][S162] The realtime-lock/hold-then-revert policy is the documented
  field standard for stream loss.
- [S645:wled00/wled.h#L453-L454] WLED still applies master brightness to
  realtime data (gamma off by default) — the sender-side caveat.
- [S682:README.md#L13-L78][S365] UPXL protocol is open (MIT), CRC-framed,
  DRAW_ALL latch — the expanders are reusable dumb sinks from any host.
- [S359] Falcon F16v5: 16×1,024 px over Ethernet+DDP with e-fuses — the
  backbone class exists off the shelf.
- [S600][S054][S251] Device-side interpolate+dither below the engine is
  proven (Fadecandy) and absent from every current receiver — the Phase-4
  lever.

## Rejected alternatives

- **Custom receiver firmware first** — months of embedded work before any
  light; stock WLED already implements the streaming contract
  [S645:wled00/udp.cpp#L410-L456].
- **Pixelblaze as a network receiver** — no standard pixel-stream input;
  its websocket is a control channel, not a frame transport [S681][S682].
- **ESPixelStick** — V4 in beta since 2023, development scattered; niche
  lost to WLED [S364].
- **Host bit-bangs pixels directly** (Pi GPIO) — Pi 5's RP1 broke legacy
  pixel output, and a network architecture makes it moot (R-8)
  [S367][S368].
