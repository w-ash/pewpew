# Excerpt provenance

- project: led-control (jackw01)
- license: MIT
- copyright: Copyright (c) 2022 jackw01
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- source path: ledcontrol/animationcontroller.py (lines 109-165 cache
  computation: palette LUTs, correction word, scaled mappings; lines 330-444
  update_leds frame loop) — two non-contiguous ranges concatenated.
- source ID: [S660]
- why excerpted: the frame loop with everything loop-invariant hoisted out —
  precomputed palette lookup tables with shortest-path hue interpolation,
  packed color-correction word, per-group scaled coordinate mappings, the
  per-pixel user-function list comprehension with prev_state threading, the
  _update_needed idle-suppression logic, and pulsing-red error containment.
