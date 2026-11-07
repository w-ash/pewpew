# Excerpt provenance — S1759 LedFx's energy beat on the wall clock

- project: LedFx
- license: GPL-3.0. Quoted as evidence only; never copied into pewpew (ADR-012 rule 1).
- pinned: LedFx/LedFx@bf10b599efe74c809a743c6e7c319dcbf77e7dc3
- paths / contents:
  - `ledfx/effects/audio.py` lines 1266–1302 (fetched at the pin on 2026-11-06): `volume_beat_now`,
    L1268–1300, reads `time.time()` for its refractory period.
- why excerpted: ADR-009's 2026-11-06 amendment "live input" puts analysis on the sample clock;
  this is the counter-example.

Licence text: `../LICENSES/GPL-3.0.txt`.
