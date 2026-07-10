# pewpew — agent conventions

Python-first addressable-LED engine, four tiers (host / receivers /
wearables / mesh groups). Currently: provenance-tracked research tree +
test-harness skeleton. Architecture: `research/synthesis/architecture.md`;
requirements IDs (Q/W/P/R/M/T-*): `research/synthesis/requirements.md`;
every major decision has an ADR in `research/synthesis/decisions/`.

## Verify loop (T-1…T-5)

- `uv run pytest` — the L1 suite (golden frames + determinism). Run it
  after any change to `harness/` or future engine code. It must stay green
  and fast (<30 s).
- `uv run pytest --regen-goldens` — ONLY for intentional visual changes;
  review the diff of the regenerated baseline before committing it.
- Iterate at the cheapest level that can falsify your change (pyramid in
  `research/synthesis/test-and-feedback.md`): host tests → fleet twin →
  emulation → bench. Hardware confirms; it is not the iteration loop.
- Determinism is load-bearing: no wall clock, no unseeded RNG in pattern or
  coordination code — inject `FakeClock` and seeds (harness/clock.py,
  harness/pattern.py). Same inputs must give byte-identical output.
- Bench/hardware results are distributions, not point values — report
  pass^k, never hard-gate a session on them (T-5).

## Hardware tiers (T-7)

- Tier 0 (read-only: serial tails, captures, telemetry): free.
- Tier 1 (bench actuation: flash, power-cycle, pattern-push): allowlisted
  verbs only, always `--dry-run` first, actions are audit-logged.
- Tier 2 (deployed fleet): READ-ONLY for agents, no exceptions. Fleet
  writes happen in attended sessions via the gateway.

## Research tree rules (condensed from research/README.md — read it before
editing research/)

- Every non-obvious claim cites a source ID: `... 27 kHz PWM [S102].`
  Unverifiable claims get `[S###][NEEDS-VERIFICATION]`.
- New sources: append entries to `research/sources/_fragments/<name>.md`
  in your allocated S-ID block (block table in research/README.md; never
  reach into another block), then `python3 research/tools/merge_sources.py`.
- ADRs need ≥2 independent evidence sources and cited rejected
  alternatives. `architecture.md` contains no decision without an ADR.
- Code sources are pinned (`owner/repo@full-sha`) with license recorded.

## Repo habits

- Temporary/working files go in the session scratchpad, never the repo.
- Don't create research/clones/ content in commits (gitignored).
- Keep this file lean: must-always-hold rules only; situational knowledge
  lives in the tree and ADRs.
