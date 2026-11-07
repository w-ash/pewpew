# pewpew — agent conventions

Python-first addressable-LED engine, four tiers (host / receivers /
wearables / mesh groups). Currently: provenance-tracked research tree,
test harness, and the Phase-1 render core in `src/pewpew/` (ADR-005
authoring contract — author-facing guide in `docs/authoring.md`).
Architecture: `research/synthesis/architecture.md`;
requirements IDs (Q/W/P/R/M/T-*): `research/synthesis/requirements.md`;
every major decision has an ADR in `research/synthesis/decisions/`.

## Verify loop (T-1…T-5)

- `just check` — the gate: ruff, the bibliography check, basedpyright, the
  two pages in `web/`, the control page and the studio (built and tested; needs Node, pnpm
  and the Playwright browsers), and the L1 suite. CI
  (`.github/workflows/ci.yml`) runs the same recipe; run it unpiped before
  every commit. There is no lint or type baseline: suppress a finding only
  inline, with its reason.
- `uv run pytest` (`just test`) — the L1 suite (golden frames +
  determinism). It must stay green and fast (<30 s).
- `just test-thorough` — the L1 suite with more examples a property
  (tests/conftest.py); run it when you change what a property covers.
- `uv run pytest --regen-goldens` — ONLY for intentional visual changes;
  review the diff of the regenerated baseline before committing it.
- Iterate at the cheapest level that can falsify your change (pyramid in
  `research/synthesis/test-and-feedback.md`): host tests → fleet twin →
  emulation → bench. Hardware confirms; it is not the iteration loop.
- Determinism is load-bearing: no wall clock, no unseeded RNG in pattern or
  coordination code — inject the seed and the clock (`Renderer(seed=)`,
  `render_sequence(..., seed=)`; `FakeClock` in src/harness/clock.py).
  Same inputs must give byte-identical output.
- Bench/hardware results are distributions, not point values — report
  pass^k, never hard-gate a session on them (T-5).

## Looks and audio

- Looks: `python -m pewpew fx ...` and `verify looks` check, render and
  compare offline (tier 0, `docs/authoring.md` §11); `mcp` serves them (§12;
  `.mcp.json`: `pewpew`, `pewpew-live` tier 1); `authoring-looks` skill.
- Live audio: `docs/audio.md`. Agents open no input: a privacy act (§7).

## Hardware tiers (T-7)

- Tier 0 (read-only: serial tails, captures, telemetry): free.
- Tier 1 (bench actuation: flash, power-cycle, pattern-push): allowlisted
  verbs only, always `--dry-run` first, actions are audit-logged.
- Tier 2 (deployed fleet): READ-ONLY for agents, no exceptions. Fleet
  writes happen in attended sessions via the gateway.

## Wiring instructions

- When you tell the user what to connect, name each end of every wire by its
  pin name and by the breadboard hole the wire goes into, for example
  "GPIO4 (A a4) → 1A (B a2)". Pin labels can't be read once a board is in a
  breadboard. Holes come from `docs/breadboard-wiring.md`.

## Research tree rules (condensed from research/README.md — read it before
editing research/)

- Every non-obvious claim cites a source ID: `... 27 kHz PWM [S102].`
  Unverifiable claims get `[S###][NEEDS-VERIFICATION]`.
- New sources: append entries to `research/sources/_fragments/<name>.md`
  in your allocated S-ID block (block table in research/README.md; never
  reach into another block), then `python3 research/tools/merge_sources.py
  --merge` (`just check` runs `--check`).
- ADRs need ≥2 independent evidence sources and cited rejected
  alternatives. `architecture.md` contains no decision without an ADR.
- Code sources are pinned (`owner/repo@full-sha`) with license recorded.

## Branches and worktrees

- Before starting a feature, run `just branches`. If an open branch or
  worktree touches the same files, continue it or ask the user; never rebuild it.
- Do feature work on its own branch in its own worktree:
  `git worktree add -b <name> .claude/worktrees/<name> main`. The main
  checkout stays on `main` with no uncommitted work.
- Finish a branch before leaving it: `just ready` green (gate, CHANGELOG
  entry or a `Changelog: none` trailer, open-work report), merge it into
  `main`, then `git worktree remove` and `git branch -d`. Work you pause
  gets committed on its branch and pushed, never left uncommitted.

## Repo habits

- This repo is the public engine. It holds no personal data and says nothing
  about when or where pewpew is used: no names, events, places or dates of
  use, schedules, addresses or device IDs. A credited decision is "the
  maintainer's". The running engine is the aura (`pewpew.aura`), never its
  former name (RA-29).
- Projects live in `projects/<project>/`, each its own private git repo,
  cloned there and ignored by this one. Rooms, looks, wiring and notes for a
  real rig go in its project; commit them with `git -C projects/<project> …`.
  Engine changes a project needs get made here, in general form.
- Temporary/working files go in the session scratchpad, never the repo.
- Don't create research/clones/ content in commits (gitignored).
- Keep this file lean: must-always-hold rules only; situational knowledge
  lives in the tree and ADRs.
