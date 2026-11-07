# ws7 records report (2026-10-22)

Branch `studio-ws7-records`. `uv run --extra dev pytest`: 240 passed, 2 xfailed.

## Added

- `research/synthesis/decisions/ADR-024-hosted-studio.md`: Accepted (2026-10-22). Covers rendering, server, trust model, hosting, frontend and geometry, plus the six rejected alternatives, each cited.
- `research/synthesis/decisions/ADR-007-mapping-calibration.md`: `## Amendment (2026-10-22)` for the three layers, provenance, frames and xyzw, MVR conversion, Contain normalization with data-order index, and versioning.
- `research/synthesis/architecture.md`: a studio exception under §5's trust model (needed, since ADR-024 amends it); an arrangement-format paragraph in §6; the 3D-view note in §8; five §9 ADOPT rows (pydantic, FastAPI + uvicorn, psycopg, manifold3d, three/R3F).
- `CHANGELOG.md`: two `[Unreleased]` bullets under Added (the studio, and the records).
- `research/SOURCES.md`: 26 entries, merged with `merge_sources.py`.

## S-IDs allocated

| Block | IDs | Contents |
|---|---|---|
| RA-03 (S100-S149) | none | Nothing cited from the power/electrical reports, so no entries. |
| RA-07 (S300-S349) | S316 | GDTF/MVR spec, pinned `mvrdevelopment/spec@098d3791f77f0895bd859adf01864b4826e2006f` |
| RA-11 (S500-S549) | S523-S527 | three r186 (pinned, MIT), WebGPURenderer manual, color-management manual, R3F 9.8.2 (pinned, MIT), glTF 2.0 |
| Synthesis (S750-S799) | S761-S780 | Fly docs (S761-S767), websockets docs (S768), FastAPI (S769), uvicorn (S770), pydantic (S771), psycopg (S772), Neon (S773-S774), manifold (S775), Pyodide (S776-S779), OWASP (S780) |

Code sources are pinned to full SHAs with licenses recorded: FastAPI MIT, uvicorn BSD-3-Clause, pydantic MIT, psycopg LGPL-3.0, manifold Apache-2.0, Pyodide MPL-2.0.

## Checked myself

All source URLs resolved with `curl -sIL` (200) except the bare `uvicorn.org` domain, which I replaced with the GitHub repo. I re-measured the Pyodide 314.0.7 files (wasm 3,438,516 B brotli, stdlib 2,545,637 B). I read `http11.py` at websockets 17.0.1 and 17.3; both reject a request body. I confirmed the WebGPURenderer and "recommended choice" text on the three.js manual page.

## Could not source or left open

- **Archive snapshot missing:** S765 (Fly volumes). Save Page Now returned 429; retry with `research/tools/retry_archives.py`. S316 has no snapshot either, but is pinned by commit.
- **S316 license:** the spec repo has no LICENSE file; recorded as TBD.
- **Backlog line cites:** the brief names `docs/backlog/v0.2.x.md:264` and `:376-382`. In this branch that file has 195 lines, so those lines exist only in the other session's uncommitted edits. I did not edit the backlog. The amendment is written and the backlog can now cite it. ADR-024 cites `docs/backlog/v0.2.x.md:193` (the retired JS pattern mirrors) instead.
- **Not found:** Fly's documentation of how an open websocket counts toward autostop load; phone benchmarks for Pyodide; the per-IP limit numbers (the plan's values, labelled inference in the ADR).
- **Power and wiring:** the electrical findings (A3) are not in any ADR. A later ADR for the report's formulas would need RA-03 sources (QuinLED, Mean Well, WLED const.h, NEC/Class 2).
- **psycopg** is LGPL-3.0. The "import unmodified, never vendor" posture is my inference from ADR-012, not a recorded decision.
- The planning reports' other web sources (not cited by ADR-024 or the amendment) were not added.
