# License note

- project: Falcon Player (FPP), https://github.com/FalconChristmas/fpp
- license: GPL-2.0-or-later: the repo's LICENSE puts every file not listed as LGPL, CC-BY-ND or external under the GPL v2 or later, and `www/` is not listed
- copyright: the Falcon Player developers and contributors
- pinned: FalconChristmas/fpp@49c9591f3ca33c023c804e5a124966aa132c7d12 [S1301]
- excerpted: 2026-11-05
- reuse: Kept verbatim for citation only; under ADR-012 its code is never copied into pewpew.

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `multisync.php` | `www/multisync.php` | 1696-1804 | ADR-004 cites L1696-L1804: a failed poll is counted per address and a system is marked unreachable only after four in a row. |

Licence text: `../LICENSES/GPL-2.0.txt`. GPL v2 or later, per the upstream
`LICENSE`; the GPL v2 text is upstream `LICENSE.GPL`.
