# Citation audit

- critic: citation-audit (Phase 4 verification)
- date: 2026-07-03
- scope: topics/, code-reading/, synthesis/ (incl. decisions/), SOURCES.md, plus S-ID references in README.md/excerpts/tools

Corpus stats: 280 `### [S###]` entries in SOURCES.md; 280 distinct S-IDs cited across the docs; 80 `[NEEDS-VERIFICATION]` tags present.

## 1. Uncited factual paragraphs

Method: paragraph-level scan (blank-line separated) for prose lacking any `[S###]`, then manual verification against the text. Headings, tables whose cells cite, lead-in sentences immediately substantiated by cited bullets in the same section, and pure synthesis/decision prose were not flagged.

Confirmed (non-obvious factual claim, no cite in the paragraph):

- code-reading/wled.md:250 — direct quote ("It is NOT a measurement and NOT guaranteed to stay within the ablMilliampsMax margin") plus claims about what the estimate ignores, with no cite. README requires direct quotes to be quoted AND cited (nearest cite is [S645:wled00/bus_manager.cpp#L183-L253] two paragraphs up).
- topics/RA-02-color-science.md:305 — "Addressable LEDs ship uncalibrated; different chip generations, vendors and bins have visibly different primaries and white points" — non-obvious factual lead claim, no cite.
- topics/RA-03-led-chips.md:86 — clocked-chip paragraph ends with "The trade is 4 wires and roughly double the strip cost" — pricing claim, no cite.
- topics/RA-10-audio-reactivity.md:57 — "~74 µs/call ... ~3 µs" FFT/mel microbenchmark: self-measured, attributed only to "bench script, this repo's research run, 2026-07-03"; no S-ID and the bench script is not in the tree — untraceable per the conventions (should get a source entry or a NEEDS-VERIFICATION tag).

Systematic:

- synthesis/decisions/ADR-001 … ADR-013: every Context section makes non-obvious factual claims (e.g. ADR-001:7 "WLED's 8-bit-everywhere pipeline leaves ~5 effective bits... LedFx computes in float64 but truncates to uint8 at every network driver") with zero inline cites. The evidence lives in each ADR's Evidence section, so this may be accepted ADR style — but as written it violates "a paragraph containing factual claims must carry at least one cite." 13 files (ADR-000 is the permitted evidence-free ADR). Recommend either citing Contexts inline or amending README/ADR-000 to exempt Context sections explicitly.

Minor / borderline (lead-ins or doc-header-covered; listed for completeness, low priority):

- topics/RA-02-color-science.md:24 (lightness-perception lead-in; following paragraphs cite)
- topics/RA-02-color-science.md:63 ("Principle." temporal-dithering explainer; section that follows cites)
- topics/RA-09-hardware-wearable-tier.md:41 ("no shipping system today runs host-authored Python patterns live on a wearable MCU" — negative sweep claim; following strategy bullets cite)
- code-reading/fadecandy.md:16 (firmware toolchain facts; covered by the doc-level S600 pin block directly above, no inline cite)
- code-reading/hyperhdr.md:179 (refresh-rate paragraph; only cite is a relative `[#L63-L65]`, see section on relative cites)

## 2. Dangling [S###] cites

None. All 280 distinct S-IDs cited in topics/, code-reading/, synthesis/ (and in README.md/excerpts/tools) resolve to a `### [S###]` entry in SOURCES.md. Cited-set and defined-set are exactly equal (no dangling cites, no orphan sources).

## 3. SOURCES.md entries missing url / accessed

None. 280 entries, 280 `- url:` lines, 280 `- accessed:` lines; per-entry scan confirms every entry carries both, none empty/TBD. No duplicate `### [S###]` headings.

## 4. Code cites `[S###:path#L...]` vs `pinned:` fields

26 distinct S-IDs are used in code-cite form. Two lack a `pinned:` field in SOURCES.md, so their line-anchored cites cannot resolve to permalinks:

- S008 (FastLED repository) — cited as e.g. [S008:src/fl/gfx/rgbw.h], [S008:src/color.h#L11-L26] in topics/RA-02-color-science.md:283,291,296,311,314,330 and synthesis/architecture.md:69. Entry has no `pinned:`.
- S011 (LedFx repository) — cited as [S011:ledfx/effects/audio.py#L...] etc. throughout topics/RA-10-audio-reactivity.md:23-31,93 and synthesis/requirements.md:62. Entry has no `pinned:`.

The other 24 (S014, S062, S156, S200, S250-S264 range, S600, S615, S630, S645, S660, S670, S681-S683, S700, S715, S716...) all carry pins.

Related: code-reading/hyperhdr.md uses bare relative line cites `[#L63-L65]`-style with no S-ID at lines 147, 155, 173, 185, 233, 246, 248, 250, 250. These resolve only by reading the surrounding prose to infer the file; they break the documented ID → pinned → permalink chain. Not normalized in place because expanding them requires inferring the intended file (judgment, not syntax). Recommend expanding each to full `[S700:path#L...]` form.

Nonstandard bracket usage (resolvable, but not per convention):

- topics/RA-01b-python-engine-gap.md:242 — `[S040 covers HN only]` (annotation inside cite brackets)
- topics/RA-04-protocols-transport.md:171 — `[S156, pinned 566de0f]` (pin repeated in prose; SOURCES entry does carry the matching `pinned:`, so this is redundant but consistent)

## 5. S-ID block discipline

Clean. SOURCES.md is organized into `## Block` sections matching README's table; every entry's numeric ID falls inside its section's declared range (checked mechanically, 0 violations). Cited IDs span S001–S716; no ID outside a documented block; the RA-01b reserved sub-block (S030–S049) is used only by RA-01b (S030–S040). No reused/duplicate IDs.

## Fixes applied

None. No malformed citation syntax of the normalizable kind (e.g. `[S 042]`, lowercase, wrong padding) was found anywhere in the tree; all other findings above require judgment and are reported, not fixed.
