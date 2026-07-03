# Excerpt provenance

- project: HyperHDR (https://github.com/awawa-dev/HyperHDR)
- license: MIT
- copyright: Copyright (c) 2020-2026 awawa-dev
- pinned: awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584
- source id: [S700]
- accessed: 2026-07-03

## Files

- `InfiniteColorEngineRgbw.cpp` — verbatim copy of
  `sources/led-drivers/InfiniteColorEngineRgbw.cpp`. Why: the adaptive
  temporal dithering + RGBW white-mixing encoder (`encodeRgbwFrame`) is the
  single most load-bearing algorithm for pewpew's dither design — leaky
  per-LED error accumulator, static-scene stabilization, monotonic-motion
  gate, interval-normalized motion threshold.
- `InfiniteColorEngineRgbw.h` — verbatim copy of
  `include/led-drivers/InfiniteColorEngineRgbw.h`. Why: defines the per-LED
  dither state struct (error, last_input, last_sent_bytes, flow_control).
- `InfiniteHybridInterpolator.cpp` — copy of
  `sources/infinite-color-engine/InfiniteHybridInterpolator.cpp` lines 1-208
  (the `test()` harness at lines 210-323 omitted). Why: the spring-damper
  YUV smoothing with per-frame luminance rate limiting and exact-target
  snap-on-completion is the reference for pewpew's temporal smoothing.
