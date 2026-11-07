# ADR-012: pewpew's own license — Apache-2.0, with a disciplined GPL boundary

Status: Accepted (2026-11-06)

## Context

The field's license landscape directly shaped what exists: Chromatik's
revenue-capped custom license keeps the best parameter/mapping engine out
of most projects; Pixelblaze's closed firmware makes its best-in-class
authoring unstudyable; LedFx's GPL-3.0 couples its excellent plumbing to a
GPL app. The comparison-matrix gap analysis names "genuinely open license +
pip-installable engine-as-library" as one of pewpew's six differentiators.
The license choice also determines which upstream code pewpew may touch.

This ADR was Proposed on 2026-07-03 choosing MIT, with Apache-2.0 as the
substitute if contributors wanted an explicit patent grant. For the public
release the maintainer chose Apache-2.0 over MIT on 2026-11-06. Both are
permissive, so the embedding argument and the boundary rules are
unchanged; what differs is the patent grant, its termination, and GPL-2.0
compatibility.

## Decision

- **pewpew is Apache-2.0-licensed.** The root `LICENSE` is the unmodified
  Apache License 2.0 text; `NOTICE` carries "Copyright 2026 the pewpew
  contributors"; `pyproject.toml` declares `license = "Apache-2.0"` with
  `license-files = ["LICENSE", "NOTICE"]`. Contributions come in under the
  same licence (Apache-2.0 §5); no contributor agreement is needed.
- **GPL/EUPL/LX boundary rules** (already applied throughout this research
  tree):
  1. GPL/EUPL code (LedFx, marimapper, aubio-ledfx, WLED, xLights,
     projectMM [S715] (GPL-3.0), WLED-MM [S646] (EUPL-1.2)) is
     never copied, vendored, or imported in-process. Algorithms are
     reimplemented from the documented findings in `research/`.
  2. GPL tools run as **separate processes** whose data output pewpew
     consumes (marimapper CSVs); protocols and file formats are freely
     implemented (DDP, WLED JSON, audio-sync V2, FSEQ, ledmap.json).
  3. LX-licensed code: this research DID make a recorded, line-level
     design read of `LXEngine.java` [S264] (frame-clock pacing, used by
     ADR-010) — the earlier wording "not read" was inaccurate. The binding
     rule going forward: read-for-understanding is permitted and must be
     recorded in `research/`; LX code is never copied or ported
     line-by-line, and implementations are written from our documented
     findings. File formats are clean-roomed from public docs (ADR-007).
  4. MIT sources (Fadecandy, FastLED, led-control, pixelblaze-client,
     UPXL firmware) may legally be ported with attribution, but the
     default remains reimplementation; `research/excerpts/` exists for
     verification, not transplanting.
- **The excerpts in `research/excerpts/` are not under Apache-2.0.** Each
  folder stays under its upstream licence, named with its copyright line
  in its `LICENSE-NOTE.md`; the full text of each licence (Apache-2.0,
  EUPL-1.2, GPL-2.0, GPL-3.0, MIT) is in `research/excerpts/LICENSES/`,
  and `research/excerpts/README.md` says so. The Pixelblaze docs [S680]
  have no licence, so their folder keeps only brief, attributed
  quotations of the lines the research cites, not copies.

## Consequences

- pewpew can be embedded in closed products, art installations, and
  commercial tooling — the adoption mode GPL app-coupling prevents.
- Users get each contributor's patent licence, and anyone who sues over
  the work's patents loses theirs; MIT gives neither.
- Redistributors carry the licence, the `NOTICE` file, and a notice on
  each file they change — a little more than MIT asks.
- pewpew code can go into GPL-3.0 projects but not GPL-2.0-only ones.
  Under rule 1 pewpew takes in no GPL code, so this limits only
  downstream mixing.
- Real reimplementation cost: melbank/beat math (ADR-009), dithering
  recipes (ADR-002), power limiting (ADR-001) are rewritten, not ported —
  the research docs' cited findings are the spec.
- Contributors must know the boundary rules; a CONTRIBUTING note and a
  dependency-license CI check are needed from the first release.

## Evidence

- [S1850] Apache-2.0 §3: each contributor's patent licence, ended for a
  licensee who sues over the work's patents; §4: the redistribution
  conditions; §5: contributions under the same licence.
- [S1851][S1852] choosealicense.com lists "Patent use" among Apache-2.0's
  permissions and not among MIT's; both are permissive and keep only
  notice conditions.
- [S1853] The FSF calls Apache-2.0 compatible with GPLv3, not with GPLv2,
  and recommends it over other permissive licences for substantial
  programs for its patent termination.
- [S1854] Apache-2.0 is OSI-approved, SPDX `Apache-2.0` — a genuinely
  open licence in the comparison-matrix sense.
- [S035] Chromatik/LX's non-commercial revenue cap (not OSI) — the
  cautionary precedent for encumbered engines.
- [S011] LedFx is GPL-3.0 and app-coupled — its plumbing is unavailable to
  permissive projects except by reimplementation.
- [S013] Pixelblaze's firmware is proprietary — closed engines can't be
  built on, only studied via protocol.
- [S017][S660] led-control is MIT but absent from PyPI — permissive
  licensing alone isn't enough; engine-as-library is the paired goal.
- [S008] FastLED (MIT) has the broadest hardware ecosystem in the field —
  the adoption pattern a permissive licence enables.
- [S001][S026][S451][S670:LICENSE#L1-L5] WLED is EUPL-1.2; xLights,
  aubio-ledfx, and marimapper are GPL-3.0 — the specific boundaries rule 1
  and 2 exist for.
- [S600:LICENSE#L1-L3][S682][S552] Fadecandy, the UPXL expander firmware,
  and pixelblaze-client are MIT — the rule-4 set.
- [S1855][S1856][S1780][S1852] GPL-3.0 §4, GPL-2.0 §1, EUPL-1.2 Art. 5
  and MIT each let a verbatim copy travel with its notices and the
  licence text — what `research/excerpts/LICENSES/` supplies.
- [S1857][S680] 17 USC §107 allows fair use for research and comment,
  weighed by the amount used; the Pixelblaze docs repo has no licence.

## Rejected alternatives

- **MIT** (this ADR's 2026-07-03 choice) — as permissive and shorter, but
  it grants no patent rights [S1852] and has no patent termination, which
  the FSF names as Apache-2.0's advantage [S1853]; its one gain, GPL-2.0
  compatibility [S1853], matters little to a project that takes in no GPL
  code (rule 1).
- **GPL-3.0** — would permit importing aubio-ledfx/LedFx code, but blocks
  embedding and repeats the exact coupling the gap analysis identifies
  [S011]; wrong trade for an engine-as-library.
- **EUPL-1.2** (WLED's choice) — copyleft with the same embedding friction
  for downstream products [S001].
- **Custom source-available license** (Chromatik) — the demonstrated way
  to keep good engineering unadopted [S035].
- **Dual licensing** — needless complexity with no current commercial
  entity to serve; revisit only if one appears.

## Amendment (2026-11-06) — protocol interop

Records the legal basis of rule 2's "protocols and file formats are freely
implemented", for RA-28's receipt of WLED's Audio Sync V2 and any later
format pewpew reads from EUPL or GPL software
(`research/topics/RA-28-audio-input.md` §10).

### Decision

- **Receiving or emitting a protocol creates no obligation**, on this
  basis: EUPL-1.2's copyleft binds a licensee who distributes or
  communicates copies of the work or a derivative (Art. 5), and leaves
  what is a derivative to copyright law (Art. 1); EU law protects no idea
  or principle behind an interface (Directive 2009/24/EC Art. 1(2),
  Recital 11); data file formats are not protected expression (CJEU
  C-406/10); and US copyright never covers a method of operation
  (17 USC §102(b)).
- **The condition:** a parser or writer is written from a byte-offset
  table in `research/`, never by copying a struct's text, comments or
  names.
- **No WLED binary ships with pewpew.** WLED is "EUPL v. 1.2 or later" and
  its audioreactive usermod builds with the GPL-3.0 ArduinoFFT by default,
  so a capture node runs pewpew's own firmware.

### Consequences

- RA-28's later V2 receiver and any WLED wire format are written from
  offset tables; a reviewer can check the condition against the excerpts.

### Evidence

- [S1780] EUPL-1.2 Arts. 1 and 5: what binds a licensee, and who decides
  what a derivative is.
- [S1781] Directive 2009/24/EC Art. 1(2) and Recital 11: interfaces'
  ideas and principles are unprotected.
- [S1782] C-406/10, ruling 1, paras 39 and 46: data file formats are not
  protected expression.
- [S1783] 17 USC §102(b): no copyright in a method of operation.
- [S1771] WLED's licence line and its V2 struct; [S1784] ArduinoFFT is
  GPL-3.0.

### Rejected alternatives

- **Linking or flashing WLED's audio build on a capture node** — EUPL and
  GPL code in a binary pewpew would distribute [S1771][S1784].
- **Copying the V2 struct definition** — the text is EUPL-licensed
  expression; the byte layout is not [S1782].
