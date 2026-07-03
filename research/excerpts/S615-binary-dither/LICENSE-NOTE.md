# Excerpt provenance

- project: FastLED (https://github.com/FastLED/FastLED)
- license: MIT — "The MIT License (MIT), Copyright (c) 2013 FastLED"
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
- source path: src/pixel_controller.h (excerpted line ranges 224-304, 307-363, 396-409, 426-474)
- excerpted: 2026-07-03, source entry [S615]
- why: the complete binary temporal dithering algorithm — virtual-bit budget macros,
  init_binary_dithering() (bit-reversed frame counter, per-channel brightness-inverse
  range), stepDithering() spatial toggle, and the load→dither→scale composite pipeline.
  Load-bearing for pewpew's frame-pipeline precision design.
