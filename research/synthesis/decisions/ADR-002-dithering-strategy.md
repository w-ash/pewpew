# ADR-002: Dithering & precision-spending per tier

Status: Proposed (2026-07-03)

## Context

The float-linear pipeline (ADR-001) preserves precision the wire cannot
carry; each tier must decide where to spend it. Temporal dithering only
works above a refresh floor (~400 Hz for full depth; visible flicker well
below that), which one-wire chip physics ties to line length (Q-3, Q-4).
Meanwhile 16-bit-native chips make dithering unnecessary, and slow network
sinks can't dither at all. One policy per tier is needed.

## Decision

Precision is spent at the **last hop that can afford it**:

1. **16-bit-native sinks (HD108/NS108, WS2816, DDP-16)**: no dithering —
   pass uint16 through losslessly; native depth replaces it (Q-6).
2. **APA102-family clocked sinks (SK9822/HD107s via UPXL/SPI)**: five-bit-HD
   joint quantization (global-brightness field fused with 8-bit PWM,
   `S = ceil(max16·31/65536)`) — pseudo-13-bit with no refresh requirement.
3. **8-bit network sinks (stock WLED, sACN/Art-Net)**: host-side adaptive
   temporal error-diffusion at the sink's output rate (static-scene freeze,
   monotonic-motion gate, leaky accumulator), effective mainly on slow
   fades; fall back to 0.49-LSB hysteresis when the output rate is too low
   to dither.
4. **Device-side tiers (wearable now, pewpew receiver later)**: true
   Fadecandy/SmoothLed-style error-feedback dithering at ≥400 Hz output,
   +2–3 effective bits; dither depth degrades gracefully below 400 Hz
   (configurable mask), and line lengths are sized to the refresh budget
   (Q-4: ~64–85 px/line for ≥400 Hz).

## Consequences

- Stock-WLED installs get real (if modest) fade improvement without
  firmware changes; the full win waits for the Phase-4 receiver.
- The engine must know each sink's achievable output rate — sinks carry a
  rate capability in their config.
- Documented direct-view risk for tier 3: HyperHDR's recipe is proven
  behind a TV, where neighboring-LED correlation doesn't matter — for
  direct-view pewpew fixtures, purely temporal per-LED dithering at
  25–60 Hz may be visibly flickering, and the recipe does not close the
  blue-noise/spatial-distribution question
  (code-reading/hyperhdr.md "What to avoid" [S700]). Prototype item #5
  must therefore test direct-view visibility of the tier-3 recipe, not
  just bit gain vs Hz.
- The exact bits-gained-vs-Hz curve is unmeasured anywhere; prototype item
  #5 (architecture §12) settles the depth-degradation constants.

## Evidence

- [S600:firmware/fc_pixel.cpp#L58-L88][S016] Fadecandy's per-channel
  error-feedback dither at ~400–500 Hz — the reference device-side loop.
- [S615:src/pixel_controller.h#L253-L302][S050] FastLED's dither budget
  assumes ~400 Hz and warns of visible flicker at low refresh; 3 virtual
  bits "only possible with 85 pixels or fewer" per line.
- [S716:src/SmoothLed.h#L13-L15][S019] SmoothLed: interpolate+dither at
  ≥400 Hz with a `ditherMask` depth knob fits 5 bytes/channel (W-3/W-4).
- [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L80-L156][S032]
  HyperHDR's adaptive temporal error-diffusion at output rate (25–200 Hz)
  — the host-side recipe; [S700:sources/led-drivers/LedDevice.cpp#L633-L658]
  the 0.49-LSB hysteresis fallback.
- [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L36-L130][S128] FastLED's
  APA102HD joint quantizer; SK9822's current-source brightness field makes
  it flicker-free.
- [S684][S063] Pixelblaze explicitly rejected temporal dithering in favor
  of HDR (16-bit) chips — validating tier 1.
- [S054][S645:wled00/bus_manager.cpp#L422-L455] WLED has no addressable-LED
  dithering (open request since 2021) — why tier 3 must run host-side.

## Rejected alternatives

- **Dither everywhere regardless of refresh** — below ~200 Hz it is visible
  flicker, worse than banding [S615:src/pixel_controller.h#L253-L302][S127].
- **No dithering, 8-bit only** — WLED's ~5 effective bits at indoor
  brightness [S054][S645:wled00/FX_fcn.cpp#L1781].
- **Dithering instead of 16-bit chips** (treat HD108 as an 8-bit target) —
  wastes the silicon; FastLED's own 8-bit-fed HD108 driver is the
  documented anti-pattern [S615:src/fl/chipsets/hd108.h#L59-L88][S063].
- **Device-side dithering as a day-one requirement** — needs custom
  receiver firmware; stock WLED can't do it, and waiting on it would block
  the whole engine (ADR-004) [S054][S645].
