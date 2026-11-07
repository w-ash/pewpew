# ADR-001: Internal color pipeline — float32 linear-light, quantize once

Status: Proposed (2026-07-03)

## Context

Every surveyed system that is praised for output quality carries wide,
linear color internally and quantizes late; every system criticized for
banding quantizes early or repeatedly. WLED's 8-bit-everywhere pipeline
leaves ~5 effective bits at typical indoor brightness and applies gamma as a
lossy 8→8 table; LedFx computes in float64 but truncates to uint8 at every
network driver with no gamma. pewpew's differentiator (comparison-matrix §2)
is bringing the proven C++ high-fidelity pipeline to Python. Requirements
Q-1, Q-2, Q-7, Q-8.

## Decision

- Working space: **float32 linear-light RGB (N,3), 0–1**, from pattern
  evaluation through compositing, color ops, and power limiting.
- **Quantize exactly once, at the sink** — sinks self-quantize to the best
  their wire supports (uint16 for DDP-16/HD108, uint8+dither for 8-bit
  wires; see ADR-002/ADR-003).
- Perceptual curve (inverse-CIE-L\*/configurable γ≈2.6–3.0 with a linear
  toe) is the **last lossy step**, applied float→uint16 via a 16-bit LUT.
- White-point/batch trim multiplies in linear space **before** the curve;
  power limiting is estimate-and-scale on linear values (per-chip current
  models) before quantization.
- MCU tiers use ≥16-bit linear fixed point in place of float32 (ADR-008).

## Consequences

- Slow fades and low-brightness scenes stop banding at the engine level;
  the remaining fidelity is decided per-tier by ADR-002.
- Memory/CPU: 12 bytes/px working state; NumPy-friendly (float32 is the
  vectorization sweet spot).
- Every sink needs an explicit quantization contract; no stage may cache
  gamma-encoded values.
- 16-bit-native chips (HD108/WS2816) receive all 16 bits losslessly (Q-6).

## Evidence

- [S063] Pixelblaze v3.47 is "all 16 bit per element throughout" — the
  quality rewrite converged on wide-internal.
- [S600:firmware/fc_pixel.cpp#L25-L88] Fadecandy interpolates 8-bit input
  into 16-bit, applies a 257-entry 16-bit LUT, dithers at the very end.
- [S600:server/src/fcdevice.cpp#L235-L360] Fadecandy multiplies whitepoint
  "prior to gamma correction," baked into the 16-bit LUT — the ordering we
  adopt.
- [S700:sources/led-drivers/LedDevice.cpp#L625-L678] HyperHDR carries float
  color into the drivers, which self-quantize — the sink-self-quantize
  pattern.
- [S645:wled00/FX_fcn.cpp#L1781][S054] The counterexample: WLED's 8-bit
  pipeline and open-since-2021 dithering request.
- [S058] An 8→8 γ=2.8 table maps the first ~16 input codes to 0 or 1 —
  why the curve must come from the wide space.
- [S059][S061] Inverse-L\* is the perceptually correct linearization,
  steeper than γ2.2 near black.
- [S630:ledfx/devices/ddp.py#L25-L36] LedFx truncates float64 to uint8 with
  no gamma — wide math without quantize-once discipline buys nothing.

## Rejected alternatives

- **8-bit integer end-to-end** (WLED [S645:wled00/FX_fcn.cpp#L1781][S054];
  projectMM deliberately, trading depth for scale
  [S715:docs/architecture.md#L202]) — the exact quality ceiling pewpew
  exists to break.
- **Float64 working space** (LedFx [S630]) — double the memory bandwidth
  for precision the LEDs cannot express; float32 already exceeds 16-bit
  output depth.
- **Gamma as an 8→8 LUT** (WLED default-off gamma [S054][S058]) —
  destroys the bottom of the curve regardless of internal width.
- **OKLab as the working space** — no LED system uses it [S055][S068];
  adopted only as optional blending helpers that convert back to linear RGB
  (architecture §2 stage 1).

## Amendment (2026-10-23) — the stage-3 power limit, pulled forward from Phase 2

The studio sizes power supplies, and a rig that never runs at full
brightness should not be bought supplies for full white. So the power
limit of architecture §2 stage 3, planned for Phase 2 (§11), lands now as
`src/pewpew/power.py`. The original decision stands: estimate-and-scale on
linear values, with per-chip current models, before quantization (Q-8).
The rest of stage 3 (white-point trim, colorimetric W derivation) stays in
Phase 2.

- **Where.** `PowerLimiter` runs on the renderer's linear float frame
  before any sink quantizes. The studio session applies it to every
  streamed frame, so the preview shows the capped light, and
  `python -m pewpew run --map rig.json` puts it in front of every sink.
  `--max-watts` and `--max-brightness` replace the arrangement's values.
- **Two limits, stored in the arrangement.** An optional `power` block,
  `{"max_watts": float | null, "max_brightness": float}`, caps nothing by
  default. `max_brightness` (0–1) scales the frame linearly: a ceiling on
  light output. `max_watts` then scales the variable part of the estimate,
  `(max_watts − flat draw) / variable draw` at most, by supply group as the
  next item says: FastLED's estimate-and-scale [S413], with the per-chip estimate of
  `pewpew.rig.electrical`: the channel sum after the firmware's auto-white
  derivation of W, as WLED estimates it [S645:wled00/bus_manager.cpp#L275-L288].
- **Per-supply shares.** One global scale lets a frame that lights only
  one supply's fixtures put the whole cap on that supply. On the golden
  rings at 500 W, red and green full on the 26 bars of one supply ask for
  26 × 2 × 6.4 W = 332.8 W, under the cap, on a supply sized for 270.8 W
  (arithmetic). The limiter therefore splits `max_watts`
  across the supply groups in proportion to each group's worst-case draw
  and keeps every group within its share. The shares sum to the cap, so the
  rig keeps under it, and with one supply the rule is FastLED's exactly.
  WLED's ABL also limits each bus against its own current limit
  [S645:wled00/bus_manager.cpp#L208-L225].
- **The worst case follows the firmware's auto-white.** pewpew sends RGB,
  and the board's WLED derives W from it [S645:wled00/bus_manager.cpp#L275-L288].
  The estimate is linear wherever the order of R, G and B is fixed, so its
  largest value is at a corner of the RGB cube. In Accurate mode an RGB
  frame reaches at most 2 of an RGBW pixel's 4 channels (yellow: W = 0);
  with no auto-white it reaches 3 (arithmetic). A fixture's worst case is
  `max_w × reach / channels`, which assumes that `max_w` is every channel
  full and splits evenly across them. One bar's per-channel watts are not
  measured (Q-004), so the report marks that split, and the board setting it
  rests on, as assumed.
- **Sizing.** The report sizes PSUs for the capped worst case,
  `min(auto-white worst case × max_brightness, max_watts)` when no fixture
  draws a flat load. Auto-wiring packs feeds into PSUs by that current. A
  fallback preset that drives every channel can exceed it, so the report
  warns when a PSU's every-channel load is over its rating.
- **Feeds under a cap.** The cap is software: a fallback preset or a bug
  can exceed it, and WLED's own limiter warns that it is "NOT guaranteed to
  stay within the ablMilliampsMax margin" [S645:wled00/bus_manager.cpp#L183-L187].
  So a fuse at each feed head, within the connector's rating, is the
  hardware backstop. Under a cap, the feed current, the connector check and
  the fuse window take the capped current, and a capped feed with no fuse is
  a violation. A feed whose every-channel current is over its connector's
  rating gets a warning that names those amps and the fuse. Without a cap
  the feeds are checked with every channel full, as before. Voltage drop is
  always computed with every channel full.
- **Determinism.** The limiter is pure, with one vectorized estimate per
  frame. An uncapped arrangement passes each frame through unchanged, so
  the golden frames hold.

Consequence: PSU sizing holds only as far as each fixture's draw follows
the frame and splits evenly across its channels, and only while every board
runs Accurate auto-white. The bar's `linear` model, its channel split and
the board setting are assumed, so the report flags every PSU size as
resting on them until a bench measurement (Q-004) settles the first two.

Evidence: [S413] (FastLED: estimate a frame's power, scale its brightness)
and [S645] (WLED's ABL: a per-bus limit that rescales the frame, and the
disclaimer), with [S418] (WLED's ABL as shipped, a cap set to the supply's
rating). No new source is added.

Rejected alternatives:

- **WLED's ABL on the receiver.** It rewrites the already-quantized 8-bit
  buffer [S645:wled00/bus_manager.cpp#L183-L253], which Q-8 rules out, and
  the studio preview would never show the capped light.
- **One global scale** (FastLED's form [S413]). Sizing each PSU for its own
  worst case under it is safe, but gives the golden rings at 500 W the same
  3 PSUs as uncapped; sizing them for the cap alone loads a supply past its
  derating on a frame that lights only its fixtures.
- **Feeds checked with every channel full under a cap.** This is safe, but
  it refuses any feed whose every-channel current is over its connector
  even when the cap keeps it well inside, so a cap could never shorten the
  wiring. The fuse at the connector's rating gives the same protection when
  the cap fails [S645:wled00/bus_manager.cpp#L183-L187].
- **A cap with no fuse.** Nothing then stops a failed cap from overloading
  the connector, so the report refuses it.
