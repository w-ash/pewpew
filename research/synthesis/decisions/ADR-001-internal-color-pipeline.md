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
