# Excerpt & license-boundary audit

- critic: excerpt-license-audit (Phase 4)
- date: 2026-07-03
- scope: (1) excerpts/ dir completeness + SOURCES.md pin match; (2) license-boundary
  consistency in synthesis/architecture.md + ADRs for LedFx / marimapper / WLED /
  Chromatik-LX; (3) ADR-012 coverage of every copyleft source appearing in a
  code-reading steal-list.

## 1. Excerpt directory audit — PASS

All 19 directories under `research/excerpts/` contain at least one code file plus a
`LICENSE-NOTE.md`. Every note names the project, license, copyright holder, pinned
sha, and original upstream path(s). Every S-ID prefix resolves to a SOURCES.md
entry whose `pinned:` field matches the note's pinned sha exactly:

| dir(s) | S-ID | pinned sha match | license |
|---|---|---|---|
| S600-fadecandy-pixel-pipeline | S600 | PimentNoir/fadecandy@36f6161… ✓ | MIT |
| S615-binary-dither, -compute-adjustment, -five-bit-hd-gamma | S615 | FastLED/FastLED@8df8258… ✓ | MIT |
| S630-beat-osc, -melbank-agc | S630 | LedFx/LedFx@566de0f… ✓ | GPL-3.0 (do-not-copy caution present) |
| S645-abl-power-limiter, -ddp-ingest, -gamma-tables | S645 | wled/WLED@14709dd… ✓ | EUPL-1.2+ |
| S660-frame-loop-hoisting, -hsv2rgb-rainbow-render, -restricted-pattern-compile | S660 | jackw01/led-control@8e3fe1d… ✓ | MIT |
| S670-marimapper | S670 | TheMariday/marimapper@7dc5f79… ✓ | GPL-3.0 (MUST-NOT-copy statement present) |
| S681-ws-compile-upload | S681 | zranger1/pixelblaze-client@9be8470… ✓ | MIT |
| S682-output-expander-protocol | S682 | simap/pixelblaze_output_expander@7a6295b… ✓ | MIT (fw) |
| S683-sensor-board-dsp | S683 | simap/pixelblaze_sensor_board@15b3d27… ✓ | MIT (fw) |
| S700-hyperhdr-infinite-color-engine | S700 | awawa-dev/HyperHDR@6d5fe87… ✓ | MIT |
| S715-projectmm-mapping | S715 | ewowi/projectMM@d5ee07c… ✓ | GPL-3.0 (do-not-copy caution present) |
| S716-smoothled-inner-loop | S716 | mattshepcar/SmoothLed@e09236c… ✓ | MIT |

Notes (non-defects): the S615-* and S681 notes fold the copyright statement into
the `license:` line rather than a separate `copyright:` field; S645-* notes lack an
explicit "reference-only" caution (EUPL) but the boundary is stated in wled.md,
architecture.md §9, and ADR-012. All required information is present; no
LICENSE-NOTE.md required fixing.

## 2. License-boundary check on synthesis — PASS

Grepped every mention of LedFx, marimapper, WLED, and Chromatik/LX in
`synthesis/architecture.md` and all 14 ADRs (206 hits reviewed).

- architecture.md §9 states the master rule: GPL/EUPL/LX systems are "integration
  targets and idea sources only — algorithms are reimplemented from the documented
  findings … their code is never copied or linked in-process", explicitly naming
  LedFx, marimapper, aubio-ledfx, WLED, xLights, Chromatik/LX.
- All other mentions are consistent with that rule: LedFx appears only as
  design precedent / interop peer / anti-pattern; marimapper only as a
  separate-process external tool with CSV import (ADR-007, §6, ADOPT table row
  "GPL, separate process — no obligation"); WLED only as network receiver,
  protocol/format source (DDP, ledmap.json, audio-sync V2, JSON API shape), or
  anti-pattern; Chromatik/LX only as clean-roomed format concepts ("documented
  spec, no LX code", ADR-007) with rule 3 in ADR-012 forbidding reading LX code.
- No synthesis doc proposes copying, vendoring, porting, or in-process linking of
  any GPL/EUPL/LX code. BUILD-list items derived from copyleft sources are all
  marked "reimplemented" (melbank/beat math, ABL-style power limiting, etc.).
- Supporting: marimapper.md carries a dedicated "GPLv3 boundary analysis" section;
  ledfx.md and modern-engines.md steal-lists carry explicit GPL
  reimplement-don't-copy warnings in their "What to avoid" sections.

## 3. ADR-012 coverage of steal-list copyleft sources — 1 VIOLATION

Steal-lists exist in: fadecandy.md, fastled.md, hyperhdr.md, led-control.md,
ledfx.md, marimapper.md, modern-engines.md (§A projectMM, §B SmoothLed),
pixelblaze.md, wled.md. Copyleft sources among them: LedFx (GPL-3.0), WLED
(EUPL-1.2), marimapper (GPL-3.0), projectMM (GPL-3.0, S715).

- LedFx, WLED, marimapper: covered by name in ADR-012 rule 1 and in
  architecture.md §9. OK.
- **VIOLATION (coverage gap): projectMM [S715] is GPL-3.0, has a substantial
  steal-list (code-reading/modern-engines.md §A "What pewpew should steal") and is
  cited as design precedent in architecture.md (lines 68, 117–118) and ADR-001 /
  ADR-005 / ADR-010, but is absent from ADR-012 rule 1's enumerated list
  ("LedFx, marimapper, aubio-ledfx, WLED, xLights") and from architecture.md §9's
  "This applies to …" enumeration.** The local doc (modern-engines.md "What to
  avoid": "GPL-3.0: code cannot be copied into pewpew … excerpts here are for
  study/citation only") and the S715 excerpt LICENSE-NOTE both state the boundary
  correctly, so no doc proposes copying it — but the canonical boundary ADR does
  not name it. Recommend adding projectMM (and, for completeness, the WLED-MM
  fork [S646], EUPL-1.2) to ADR-012 rule 1 and to the architecture.md §9 list.
- Minor (non-violation): wled.md's own steal-list has no local EUPL
  reimplement-only reminder, unlike ledfx.md/modern-engines.md; the boundary is
  stated elsewhere (ADR-012, architecture.md §9). Optional consistency fix.
- All other steal-list sources are MIT (Fadecandy, FastLED, HyperHDR,
  led-control, pixelblaze-client, UPXL/sensor-board firmware, SmoothLed) or
  spec/protocol-level (Pixelblaze closed firmware studied via open docs/protocol
  only); ADR-012 rule 4 covers the MIT set.

## Fixes applied

None. All LICENSE-NOTE.md files were complete and matched SOURCES.md, so no
in-place edits were needed. The ADR-012/architecture.md enumeration gap for
projectMM is reported above but not edited, as ADR edits are outside this
critic's write scope.
