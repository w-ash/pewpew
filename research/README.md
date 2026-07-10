# pewpew research

Provenance-tracked research into addressable-LED control systems (2026 state of
the art), feeding the recommended architecture in
[`synthesis/architecture.md`](synthesis/architecture.md).

Read this file first. It defines the conventions that make every claim in this
tree traceable to a source by any future dev or agent — human or AI.

## Layout

```
research/
  README.md            this file — conventions
  SOURCES.md           THE bibliography. Single file, append-only, greppable
  topics/              one doc per research area (RA-01 … RA-12)
    _TEMPLATE.md       copy this to start a topic doc
  code-reading/        one doc per repository read, pinned to a commit SHA
  excerpts/            verbatim load-bearing code excerpts (survive upstream deletion)
  synthesis/
    requirements.md    form factors → numeric requirements, cited
    comparison-matrix.md
    architecture.md    THE deliverable — recommended system structure
    decisions/         ADRs; every major choice gets one
```

## Citation conventions

### Source IDs

Every source gets an ID like `[S014]` — zero-padded, append-only, never reused.
The full record lives in [`SOURCES.md`](SOURCES.md); retrieve it with:

```
grep -A10 '\[S014\]' research/SOURCES.md
```

Entry format (one `###` heading per source):

```markdown
### [S014] Short descriptive title
- type: code | spec | docs | article | forum | video | datasheet | product
- url: https://...
- pinned: owner/repo@<full-sha>        # code sources only, set at read time
- author: ...
- license: ...                          # code sources; "TBD" until verified
- published: YYYY-MM-DD                 # if known
- accessed: YYYY-MM-DD                  # required
- archive: https://web.archive.org/...  # required iff load-bearing (see below)
- relevance: one line on why this source matters to pewpew
```

### Citing prose

Every non-obvious claim ends with its source ID: `... at 27 kHz PWM [S102].`
A paragraph containing factual claims must carry at least one cite.
Direct quotes are quoted and cited. Claims we could not verify are tagged
`[S###][NEEDS-VERIFICATION]` so they are greppable.

### Citing source code

Pin the commit SHA **once**, in the source entry's `pinned:` field. Inline
cites then reference path and lines against that pin:

```
[S014:src/fl/five_bit_hd_gamma.cpp#L40-L88]
```

Resolution: ID → `pinned: owner/repo@sha` → GitHub permalink
`https://github.com/owner/repo/blob/<sha>/<path>#L40-L88`.

### Archival rule — "load-bearing" sources

A source is **load-bearing** once any ADR cites it as evidence. Load-bearing
sources MUST have:
- web pages → an `archive:` field with an archive.org snapshot
- code cited with line anchors (`[S###:path#Lx-Ly]`) in an ADR → a verbatim
  excerpt of the cited code in `excerpts/S###-name/` alongside a
  `LICENSE-NOTE.md` recording the original license and attribution
- code cited only at repo level (existence, license, maintenance status,
  verdicts) → a `pinned:` field in SOURCES.md; no excerpt required
  (scoped 2026-07-03, Phase 4 verification)

### S-ID block allocation

Blocks are pre-allocated per research area so parallel researchers never
collide. Allocate the next free ID inside your block; never reach into
another block.

| Block | Area |
|---|---|
| S001–S049 | RA-01 Landscape (S030–S049 reserved: Python-engine gap check) |
| S050–S099 | RA-02 Color science & high-fidelity output |
| S100–S149 | RA-03 LED chips & electrical limits |
| S150–S199 | RA-04 Protocols & transport |
| S200–S249 | RA-05 Pattern-engine design |
| S250–S299 | RA-06 Frame pipeline & motion quality |
| S300–S349 | RA-07 Mapping & topology |
| S350–S399 | RA-08 Hardware: host-driven tier |
| S400–S449 | RA-09 Hardware: wearable tier |
| S450–S499 | RA-10 Audio reactivity |
| S500–S549 | RA-11 Simulation, preview & dev ergonomics |
| S550–S599 | RA-12 Prior art & control plane |
| S600–S699 | Code-reading deep dives |
| S700–S749 | Code-reading deep dives (added from Phase 1 queues) |
| S750–S799 | Synthesis & later additions |
| S800–S849 | RA-13 ESP-NOW & fleet scaling |
| S850–S899 | RA-14 Mesh transport alternatives |
| S900–S949 | RA-15 Decentralized coordination & sync |
| S950–S999 | RA-16 ESP32-S3 render+radio coexistence |
| S1000–S1049 | RA-17 Fleet ops & mesh gateway |
| S1050–S1099 | RA-18 Wearable bridging |

## Topic docs

Copy [`topics/_TEMPLATE.md`](topics/_TEMPLATE.md). Every topic doc records,
for each system/technique it covers:
- **license** (reuse constraints differ: EUPL vs GPLv3 vs MIT)
- **maintenance status with dates** (last release/commit as of research date)
- **form-factor applicability** (wearable / portable / room-scale)
- an **ascendant / stable / waning verdict** — we do not build around tech on
  the wane
- a ranked **code-reading queue** feeding Phase 2

## ADRs

Format: Status / Context / Decision / Consequences / Evidence / Rejected
alternatives. The Evidence section lists S-IDs, each with a one-line statement
of what that source proves. Rejected alternatives are cited too. An ADR needs
≥2 independent evidence sources, or an explicit single-source caveat.
`synthesis/architecture.md` contains no decision that lacks an ADR.

ADR Context sections may restate findings without inline cites ONLY where the
ADR's own Evidence section carries the citation; all other docs cite inline
(ADR-000 rule 6).
