# License note

- project: HyperHDR, https://github.com/awawa-dev/HyperHDR
- license: MIT
- copyright: Copyright (c) 2020-2026 awawa-dev
- pinned: awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584 [S700]
- excerpted: 2026-11-05

Each file holds the lines an ADR cites, verbatim, under a provenance
header; the research archival rule (research/README.md) asks for them
so the cite survives an upstream change or deletion.

| file | upstream path | lines | why |
|---|---|---|---|
| `LedDevice.cpp` | `sources/led-drivers/LedDevice.cpp` | 537-546, 625-678 | ADR-010 cites L537-L546 (latest-wins frame drop at the driver); ADR-001 cites L625-L678 (float color carried into the output stage) and ADR-002 L633-L658 within it (the 0.49-LSB hysteresis fallback). |

Licence text: `../LICENSES/MIT.txt`, with the upstream notice "Copyright (c)
2020-2026 awawa-dev" (`LICENSE` at the pin).
