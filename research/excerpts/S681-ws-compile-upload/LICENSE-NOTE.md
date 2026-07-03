# Excerpt provenance

- project: pixelblaze-client (Python library for the Pixelblaze WebSocket API)
- source: [S681] zranger1/pixelblaze-client
- pinned: zranger1/pixelblaze-client@9be84700248fa17f0123c702a2939213ba69800a
- path: pixelblaze/pixelblaze.py (lines 460-479 messageTypes/frameTypes enums; lines 1314-1565 compilePattern(), makeId(), LZString helpers, sendPatternToRenderer())
- license: MIT, Copyright (c) 2020-2025 ZRanger1
- accessed: 2026-07-03
- why excerpted: only public documentation of (a) the Pixelblaze binary
  WebSocket message types, (b) the device bytecode blob layout (opcode/export
  section sizes, 32-bit opcodes, name->address export table), and (c) the
  technique of extracting the closed JS compiler from the device's /index.html.gz
  and running it in V8 to compile patterns off-device.
