# License note

- project: WLED, https://github.com/wled/WLED
- license: EUPL v1.2 or later
- copyright: Copyright (c) 2016 Harm Aldick; (c) 2016-present Christian Schwinne and individual WLED contributors
- pinned: wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63 [S645]
- excerpted: 2026-11-05

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `udp.cpp` | `wled00/udp.cpp` | 410-456 | ADR-004 and ADR-010 cite L410-L456: realtime UDP ingest and its timeout, re-armed per packet. |
| `wled.h` | `wled00/wled.h` | 453-454 | ADR-004 cites L453-L454: master brightness still applies to realtime data. |

Licence text: `../LICENSES/EUPL-1.2.txt`, with the upstream notice "Copyright
(c) 2016-present Christian Schwinne and individual WLED contributors"
(`LICENSE` line 1 at the pin).
