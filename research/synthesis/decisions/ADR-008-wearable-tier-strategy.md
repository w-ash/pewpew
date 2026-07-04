# ADR-008: Wearable tier — CircuitPython + ulab, BLE control, baked-frames fallback

Status: Proposed (2026-07-03)

## Context

The wearable tier must render standalone on-body (W-7) at 50–300 px and
≥30 fps (W-1, W-2) on battery, with occasional phone tweaks (W-5). Plain
interpreted Python is 1–2 orders of magnitude too slow per-pixel; the
escape hatches are vectorized ulab, native code emitters, a custom bytecode
VM (Pixelblaze's model), or pre-baked frames. No shipping system runs
host-authored Python patterns live on a wearable MCU — pewpew picks the
shape.

## Decision

- **CircuitPython + ulab on RP2350** (non-radio pieces) **or nRF52840**
  (BLE pieces), running **the same pattern contract as the host** (ADR-005)
  against ulab arrays — ulab deliberately mirrors NumPy, so a disciplined
  pattern subset runs unmodified on both tiers.
- **Device pipeline**: ≥16-bit fixed-point (ADR-001), SmoothLed-style
  interpolate+dither at ≥400 Hz, 5 bytes/channel state (W-3, W-4);
  estimate-and-scale current cap enforced every frame (W-6).
- **Baked-frames fallback** (FSEQ-style playback) for patterns outside the
  ulab subset.
- **Phone control over BLE GATT** (parameter writes + pattern file push via
  FileTransferService); WiFi AP only as an explicit short-session mode.
- **Compile-to-VM is explicitly deferred**: best
  performance-per-flexibility, but a compiler+VM maintenance burden the
  evidence doesn't yet justify.

## Consequences

- One authoring surface spans tiers, but authors must stay inside the ulab
  subset for live on-device patterns — the subset boundary needs docs and a
  lint.
- ~150 px at 60 fps has measured headroom on RP2040-class hardware; the
  RP2350 2× claim and BLE push throughput are prototype items #8–9.
- The nRF52840 branch has the least compute headroom — it leans on the
  dither/interpolate loop being cheap (5 B/channel) and on baked frames.
- **OTA/field-update story.** CircuitPython makes wearable updates a file
  copy, not a flash: patterns and runtime code update via the CIRCUITPY
  USB drive or over BLE FileTransferService [S407][S409] — the same push
  path the phone-control workflow already uses. The CircuitPython core
  itself updates via UF2 bootloader drag-and-drop (the shipped Adafruit
  workflow); a bad pattern file cannot brick the device — worst case is
  factory-reset by re-copying files. Formalizing this (versioned pattern
  bundles, rollback of the last-known-good bundle) is a Phase-3 work item.

## Evidence

- [S400] Measured: 256-px fire at ~40 ms/frame plain Python vs ~4 ms/frame
  ulab-vectorized on RP2040 — the 10× that makes the tier viable (W-1/W-2).
- [S403] ulab is bundled in CircuitPython builds for RP2040/RP2350/
  nRF52840/ESP32-S3; RP2350 ~2× RP2040 [NEEDS-VERIFICATION — prototype #8].
- [S716:src/SmoothLed.h#L63-L79][S019] SmoothLed: value+step+dither in
  5 bytes/channel at ≥400 Hz on ATtiny-class parts — the device pipeline,
  widened to a 16-bit entry point.
- [S411] ESP32 SoftAP draws ~100–130 mA with no modem power-save in AP
  mode — ~10%/hour of a 1200 mAh pack before any LED.
- [S412] nRF52840 measured best-in-class for BLE current (µA-class idle);
  "ESP32s are not suitable for BLE projects with low current consumption."
- [S407][S409] BLE FileTransferService + web editor: pattern push over BLE
  is a solved workflow, though "simple (not fast)".
- [S406][S258] WLED's merged FSEQ-from-SD playback and the xLights
  ecosystem keep the baked-frames format alive — the fallback is
  standard, not bespoke.
- [S405][S404] Pixelblaze's VM renders ~48k px/s on ESP32 — proof the
  deferred VM route works if the ulab subset proves too confining.
- [S413] FastLED's estimate-and-scale power limiting — the algorithm the
  device runtime ports (CircuitPython has no built-in equivalent).

## Rejected alternatives

- **WLED-on-ESP32 as the wearable platform** (Adafruit's 2025 direction
  [S414][S415]) — SoftAP radio floor is wrong for all-day on-body use
  [S411]; right only when a served web UI is the product.
- **Plain-Python per-pixel loops** — ~25 fps at 256 px on RP2040 [S400].
- **Custom bytecode VM now** (Pixelblaze model) — deferred; compiler+VM
  maintenance vs. an unproven need [S404][S405].
- **Hand-ported C++/FastLED firmware per garment** — abandons the shared
  Python pattern contract, the tier's whole point [S008][S402].
- **MicroPython viper/native emitters** — per-function, type-restricted
  integer acceleration; doesn't cover arbitrary pattern code [S402].
