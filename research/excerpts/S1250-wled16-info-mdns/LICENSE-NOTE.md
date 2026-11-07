# License note

- project: WLED (tag v16.0.1), https://github.com/wled/WLED
- license: EUPL-1.2
- copyright: WLED contributors
- pinned: wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c [S1250]
- excerpted: 2026-11-05

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `json.cpp` | `wled00/json.cpp` | 762-778, 869, 910 | ADR-004 cites L762-L778, L869 and L910: `/json/info` reports `live`, the realtime mode, the sender's address, `uptime` and `mac`. |
| `wled.cpp` | `wled00/wled.cpp` | 855-860 | ADR-004 cites L855-L860: the mDNS service carrying the MAC. |
| `wled.h` | `wled00/wled.h` | 451 | ADR-004 cites L451: the 2500 ms realtime timeout. |

Licence text: `../LICENSES/EUPL-1.2.txt`, with the upstream notice "Copyright
(c) 2016-present Christian Schwinne and individual WLED contributors"
(`LICENSE` line 1 at the pin).
