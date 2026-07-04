# ADR-012: pewpew's own license — MIT, with a disciplined GPL boundary

Status: Proposed (2026-07-03)

## Context

The field's license landscape directly shaped what exists: Chromatik's
revenue-capped custom license keeps the best parameter/mapping engine out
of most projects; Pixelblaze's closed firmware makes its best-in-class
authoring unstudyable; LedFx's GPL-3.0 couples its excellent plumbing to a
GPL app. The comparison-matrix gap analysis names "genuinely open license +
pip-installable engine-as-library" as one of pewpew's six differentiators.
The license choice also determines which upstream code pewpew may touch.

## Decision

- **pewpew is MIT-licensed** — the norm of the sources pewpew most admires
  and the least-friction choice for an embeddable engine-as-library.
  (Apache-2.0 is the acceptable substitute if contributors want an explicit
  patent grant; the boundary rules below are identical.)
- **GPL/EUPL/LX boundary rules** (already applied throughout this research
  tree):
  1. GPL/EUPL code (LedFx, marimapper, aubio-ledfx, WLED, xLights) is
     never copied, vendored, or imported in-process. Algorithms are
     reimplemented from the documented findings in `research/`.
  2. GPL tools run as **separate processes** whose data output pewpew
     consumes (marimapper CSVs); protocols and file formats are freely
     implemented (DDP, WLED JSON, audio-sync V2, FSEQ, ledmap.json).
  3. LX-licensed code is not read for implementation; formats are
     clean-roomed from public docs (ADR-007).
  4. MIT sources (Fadecandy, FastLED, led-control, pixelblaze-client,
     UPXL firmware) may legally be ported with attribution, but the
     default remains reimplementation; `research/excerpts/` exists for
     verification, not transplanting.

## Consequences

- pewpew can be embedded in closed products, art installations, and
  commercial tooling — the adoption mode GPL app-coupling prevents.
- Real reimplementation cost: melbank/beat math (ADR-009), dithering
  recipes (ADR-002), power limiting (ADR-001) are rewritten, not ported —
  the research docs' cited findings are the spec.
- Contributors must know the boundary rules; a CONTRIBUTING note and a
  dependency-license CI check are needed from the first release.

## Evidence

- [S035] Chromatik/LX's non-commercial revenue cap (not OSI) — the
  cautionary precedent for encumbered engines.
- [S011] LedFx is GPL-3.0 and app-coupled — its plumbing is unavailable to
  permissive projects except by reimplementation.
- [S013] Pixelblaze's firmware is proprietary — closed engines can't be
  built on, only studied via protocol.
- [S017][S660] led-control is MIT but absent from PyPI — permissive
  licensing alone isn't enough; engine-as-library is the paired goal.
- [S008] FastLED (MIT) has the broadest hardware ecosystem in the field —
  the adoption pattern MIT enables.
- [S001][S026][S451][S670:LICENSE#L1-L5] WLED is EUPL-1.2; xLights,
  aubio-ledfx, and marimapper are GPL-3.0 — the specific boundaries rule 1
  and 2 exist for.
- [S600:LICENSE#L1-L3][S682][S552] Fadecandy, the UPXL expander firmware,
  and pixelblaze-client are MIT — the rule-4 set.

## Rejected alternatives

- **GPL-3.0** — would permit importing aubio-ledfx/LedFx code, but blocks
  embedding and repeats the exact coupling the gap analysis identifies
  [S011]; wrong trade for an engine-as-library.
- **EUPL-1.2** (WLED's choice) — copyleft with the same embedding friction
  for downstream products [S001].
- **Custom source-available license** (Chromatik) — the demonstrated way
  to keep good engineering unadopted [S035].
- **Dual licensing** — needless complexity with no current commercial
  entity to serve; revisit only if one appears.
