# License note

- project: Fadecandy fcserver, https://github.com/PimentNoir/fadecandy
- license: MIT
- copyright: Copyright (c) 2013 Micah Elizabeth Scott
- pinned: PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d [S600]
- excerpted: 2026-11-05

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `fcdevice.cpp` | `server/src/fcdevice.cpp` | 235-360, 362-382 | ADR-001 cites L235-L360 (white point multiplied in before gamma, baked into the 16-bit LUT); ADR-010 cites L362-L382 (`MAX_FRAMES_PENDING` with frame coalescing). |
| `LICENSE` | `LICENSE` | 1-3 | ADR-012 cites L1-L3 for the MIT license. |

Licence text: `../LICENSES/MIT.txt`, with the upstream notice "Copyright (c)
2013 Micah Elizabeth Scott" (`LICENSE` at the pin).
