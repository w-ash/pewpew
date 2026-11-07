# License note

- project: LedFx, https://github.com/LedFx/LedFx
- license: GPL-3.0 (LICENSE.txt in the repo root)
- copyright: LedFx developers (Austin Hodges et al., per AUTHORS.rst)
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792 [S630]
- excerpted: 2026-11-05
- reuse: Kept verbatim for citation only; under ADR-012 its code is never copied into pewpew.

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `ddp.py` | `ledfx/devices/ddp.py` | 25-36 | ADR-001 cites L25-L36: float64 truncated to uint8 on output. |
| `artnet.py` | `ledfx/devices/artnet.py` | 176-179 | ADR-010 cites L176-L179: LedFx's own comment on its callback-thread pain. |
| `__init__.py` | `ledfx/effects/__init__.py` | 273-340, 479-547 | ADR-005 cites L273-L340 (effect registry and schema boilerplate) and L479-L547 (the persistent `self.pixels` convention). |
| `virtuals.py` | `ledfx/virtuals.py` | 409-495, 746-779, 864-877 | ADR-007 cites L409-L495 (precompiled segment-to-device gathers); ADR-010 cites L746-L779 (thread per virtual) and L864-L877 (the per-virtual loop with compensated sleep). |

Licence text: `../LICENSES/GPL-3.0.txt`.
