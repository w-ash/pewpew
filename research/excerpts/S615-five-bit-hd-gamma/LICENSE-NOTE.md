# Excerpt provenance

- project: FastLED (https://github.com/FastLED/FastLED)
- license: MIT — "The MIT License (MIT), Copyright (c) 2013 FastLED"
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
- source path: src/fl/gfx/five_bit_hd_gamma.cpp.hpp (entire file, 183 lines — the file IS the algorithm)
- excerpted: 2026-07-03, source entry [S615]
- why: the APA102HD pseudo-13-bit pipeline — 16-bit gamma LUT application, joint
  quantization of max component to a ceil-based 5-bit brightness, and rounded
  renormalization of RGB via the BRIGHT_SCALE table. Load-bearing for pewpew's
  high-dynamic-range output on APA102/HD107/SK9822-class chips.
