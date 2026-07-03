# Excerpt provenance

- project: Pixelblaze Sensor Expansion Board firmware
- source: [S683] simap/pixelblaze_sensor_board
- pinned: simap/pixelblaze_sensor_board@15b3d271e0d6535965a68b15f057bac58a3154d7
- path: src/output.c (entire file, 151 lines — it is one cohesive unit: band maps, fftRealWindowedMagnitude(), processSensorData())
- license: MIT, Copyright (c) 2018 Ben Hencke (firmware; hardware CC-BY-SA-4.0)
- accessed: 2026-07-03
- why excerpted: the dual-rate FFT audio analysis (20 kHz/512-pt + 400 Hz/32-pt
  decimated bass FFT) merged into 32 log-spaced max-of-bins bands, plus the
  exact "SB1.0…END" serial frame serialization — reference for pewpew audio
  reactivity and for consuming sensor boards directly.
