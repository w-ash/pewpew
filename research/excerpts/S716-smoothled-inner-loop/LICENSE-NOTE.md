# Excerpt provenance — S716 SmoothLed interpolation + dithering inner loop

- project: SmoothLed
- license: MIT (upstream LICENSE, © 2020 Matt Shepcar) — MIT-compatible for reuse
  with attribution.
- copyright: Matt Shepcar
- pinned: mattshepcar/SmoothLed@e09236cfc63a96c565d97ef316073452a38cf86d
- paths / contents:
  - `SmoothLed.cpp` — extracted fragments (lines 10–17, 51–71, 122–131 of the
    original): the inverted 32-entry gamma-2.5 LUT, the fade-clock
    `beginFade`/`updateTime` coefficient scheme, and `Interpolator::update`
    (fmac fade advance → clamp → LUT lerp gamma → error-feedback dither).
  - `SmoothLedMultiply.h` — complete file: the AVR `fmul/fmulsu` fixed-point
    primitives (`mac`, `fmac`, `fmul`, `lerp`) with cycle counts.
  - `SmoothLedUpdate.S` — the `SmoothLedUpdate8cpb` routine (lines 1–96): the
    cycle-annotated 64-cycles-per-channel (8-cycles-per-bit) streaming loop,
    the primary evidence for the cycles-per-LED claim.
- why excerpted: this is the existence proof for pewpew's wearable-tier quality
  layer — Fadecandy-class interpolation + gamma + temporal dithering in 5 bytes
  of RAM per channel and 64 cycles per channel on an ATtiny. Cited in
  research/code-reading/modern-engines.md §B.
