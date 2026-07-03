# Excerpt provenance

- project: led-control (jackw01)
- license: MIT
- copyright: Copyright (c) 2022 jackw01
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- source path: ledcontrol/animationcontroller.py (lines 226-283,
  set_pattern_function)
- source ID: [S660]
- why excerpted: the compile-once RestrictedPython sandbox — curated injected
  globals (math, palette, C wave/noise primitives), guard functions,
  compile-time used-names checking returned as editor warnings, and storage
  of the compiled `pattern` callable. The blueprint for pewpew's safe
  user-Python shader compilation.
