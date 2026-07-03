# Excerpt provenance

- project: led-control (jackw01)
- license: MIT
- copyright: Copyright (c) 2021 jackw01
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- source path: ledcontrol/driver/led_render.h (lines 89-226)
- source ID: [S660]
- why excerpted: the C fast-path color pipeline — FastLED-style "rainbow"
  hue transform, the v*v value gamma, 8-bit-early quantization, RGBW
  desaturation-to-white routing, and scale_8 correction. This is the exact
  per-pixel render function behind the Pi Zero performance claim and the
  reference for what pewpew's pipeline must exceed (no dithering, gamma
  commented out).
