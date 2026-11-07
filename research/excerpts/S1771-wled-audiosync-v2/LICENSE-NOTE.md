# Excerpt provenance — S1771 WLED's Audio Sync V2 packet

- project: WLED
- license: "EUPL v. 1.2 or later" (upstream LICENSE L2). Quoted as evidence only; never copied
  (ADR-012 rule 1). A parser is written from a byte-offset table (ADR-012, 2026-11-06 amendment).
- copyright: Christian Schwinne and individual WLED contributors
- pinned: wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c
- paths / contents:
  - `usermods/audioreactive/audio_reactive.cpp` lines 799–812 (fetched at the pin on 2026-11-06):
    the 44-byte V2 struct: levels, a peak flag, 16 GEQ magnitude bytes, magnitude and major peak;
    no timestamp and no phase.
  - `LICENSE` lines 1–2: the copyright and licence line.
- why excerpted: ADR-009's 2026-11-06 amendment "capture nodes": V2 carries no per-bin phase, so it
  cannot feed the beat tracker.

Licence text: `../LICENSES/EUPL-1.2.txt`. The copyright line is in the
`LICENSE` excerpt in this folder.
