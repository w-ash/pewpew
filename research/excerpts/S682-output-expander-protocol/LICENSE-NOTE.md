# Excerpt provenance

- project: Pixelblaze Output Expander firmware
- source: [S682] simap/pixelblaze_output_expander, v3.x branch
- pinned: simap/pixelblaze_output_expander@7a6295b12056db35be3dfd2629783050020db7ae
- path: firmware/Core/Src/app.c (lines 60-135 protocol comment + structs; lines 375-592 handleIncomming() + loop())
- license: MIT, Copyright (c) 2018 Ben Hencke (firmware; hardware is CC-BY-SA-4.0)
- accessed: 2026-07-03
- why excerpted: the complete "UPXL" serial protocol parser — frame structs,
  magic-resync, CRC-32 validation with zero-on-corrupt policy, color-order
  remap, and APA102 start/end-frame synthesis. This is the reference for a
  pewpew host-side expander driver.
