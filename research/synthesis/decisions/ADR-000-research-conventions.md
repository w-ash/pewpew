# ADR-000: Research provenance conventions

Status: Accepted (2026-07-03)

## Context

pewpew's architecture will be justified by a research pass over the 2026
state of the art. The findings must remain auditable long after the pass:
future devs and agents need to trace any recommendation back to the exact
source — including the exact commit of source code — that produced it.
Sources rot: repos vanish, forum threads disappear, web pages change.

## Decision

Adopt the conventions specified in [`research/README.md`](../../README.md):

1. **Central append-only bibliography** (`SOURCES.md`) with `[S###]` IDs and
   per-area ID blocks so parallel researchers never collide.
2. **Inline citation of every non-obvious claim**; `[NEEDS-VERIFICATION]`
   tags for unsettled claims.
3. **Code cited against pinned SHAs**, with the SHA recorded once per source
   entry and inline cites of the form `[S###:path#Lx-Ly]`.
4. **Load-bearing sources get archived**: archive.org snapshots for web
   pages; for code, verbatim excerpts + license notes are required where an
   ADR cites the code with line anchors (`[S###:path#Lx-Ly]`) — repo-level
   citations (existence, license, maintenance, verdicts) need a `pinned:`
   field but no excerpt (scoped 2026-07-03, Phase 4 verification).
   "Load-bearing" = cited by any ADR.
5. **ADRs carry an Evidence section** mapping S-IDs to what each proves;
   ≥2 independent sources per ADR or an explicit caveat.
6. **ADR Context exemption** (amended 2026-07-03, Phase 4 verification):
   ADR Context sections may restate findings without inline cites ONLY
   where the ADR's own Evidence section carries the citation; all other
   docs cite inline. A Context claim not covered by that ADR's Evidence
   still requires an inline cite.

## Consequences

- Adding a finding costs slightly more (allocate ID, record access date).
- The research tree is greppable end-to-end: claim → `[S###]` → SOURCES.md
  → URL/pin → archive. No claim depends on a live external resource.
- Parallel research agents can work without coordinating beyond their
  assigned ID block.

## Evidence

None — this ADR defines process rather than recording a researched finding.
It is the single permitted evidence-free ADR; all subsequent ADRs must
comply with rule 5.

## Rejected alternatives

- **Per-document bibliographies** — duplicate entries drift apart; a single
  greppable file keeps IDs unique and lookups trivial.
- **Footnote-style numeric citations per doc** — numbers collide across
  docs and break when docs merge during synthesis.
- **Citing code by branch/HEAD** — unpinned references rot within months in
  actively developed repos (FastLED and WLED both ship multiple releases a
  year); SHAs are immutable.
- **No archival** — Fadecandy's own history (author unreachable since
  ~2018, project dormant) shows canonical sources for exactly the
  techniques we care about can go dark.
