# Excerpt provenance — S1754 sounddevice's stream callback

- project: python-sounddevice
- license: MIT (upstream LICENSE), © Matthias Geier
- pinned: spatialaudio/python-sounddevice@283f40d6ebdedda2c0d609c41a6a14476c1dc87e
- paths / contents:
  - `src/sounddevice.py` lines 840–850 (fetched at the pin on 2026-11-06): L845 builds the stream's
    callback with `_ffi.callback('PaStreamCallback', ...)`, so a Python callback runs as a cffi callback.
- why excerpted: ADR-009's 2026-11-06 amendment "live input" polls a callback-free stream for this reason.

Licence text: `../LICENSES/MIT.txt`, with the upstream notice "Copyright (c)
2015-2025 Matthias Geier" (`LICENSE` at the pin).
