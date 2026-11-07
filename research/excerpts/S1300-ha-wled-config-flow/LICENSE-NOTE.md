# License note

- project: Home Assistant core (WLED integration), https://github.com/home-assistant/core
- license: Apache-2.0
- copyright: Home Assistant contributors
- pinned: home-assistant/core@db50c01e164020f0179e679c9923138bf4172e9c [S1300]
- excerpted: 2026-11-05

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `config_flow.py` | `homeassistant/components/wled/config_flow.py` | 77-91 | ADR-004 cites L77-L91: a board is identified by MAC, and its host follows it to a new address. |

Licence text: `../LICENSES/Apache-2.0.txt`. The upstream repo has no NOTICE
file at the pin, and its `LICENSE.md` carries no copyright line.
