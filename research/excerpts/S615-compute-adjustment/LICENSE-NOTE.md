# Excerpt provenance

- project: FastLED (https://github.com/FastLED/FastLED)
- license: MIT — "The MIT License (MIT), Copyright (c) 2013 FastLED"
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
- source paths:
  - crgb.cpp.hpp — src/crgb.cpp.hpp lines 29-52 (CRGB::computeAdjustment)
  - scale8.h — src/platforms/shared/scale8.h lines 25-42 (scale8, scale8_constexpr, scale8_video)
- excerpted: 2026-07-03, source entry [S615]
- why: the per-frame premixed color-adjustment math ((cc+1)(ct+1)*scale/0x10000) and the
  fixed-point scale8 family it feeds — including the video variant's low-end blackout guard.
  Load-bearing for pewpew's brightness/correction pipeline design.
