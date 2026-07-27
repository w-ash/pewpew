# pewpew backlog

## Current

**v0.1.x — Phase 0 de-risk** (build plan: `research/synthesis/architecture.md` §11).
Settle the two riskiest bets — NumPy throughput (R-9/ADR-011) and the vectorized
authoring surface (ADR-005) — and stand up the bench core (ADR-018) before any
engine code hardens. Desktop throughput datapoint landed 2026-07-15: NumPy 52×
the R-9 target on Apple M5 Pro; Pi 5 rerun pending.

## Next

**v0.2.x — Phase 1 host engine core**, decomposed and ready ([v0.2.x.md](v0.2.x.md)),
gated on the Phase 0 benchmarks and the §12 item 13 pacing-jitter soak. Two of
its stories carry their own hardware blocks (paced clock waits on item 13; the
DDP sink waits on a receiver + strip). Later phases live in `unscheduled.md`
until promoted.

## Version matrix

| Version | Theme | Status | File |
|---|---|---|---|
| v0.1.x | Phase 0 de-risk: benchmarks + bench core | In Progress | [v0.1.x.md](v0.1.x.md) |
| v0.2.x | Phase 1: host engine core, end-to-end on real LEDs | Not Started | [v0.2.x.md](v0.2.x.md) |

## Changelog mode

`batch` — work accumulates under `## [Unreleased]` in the root
[`CHANGELOG.md`](../../CHANGELOG.md) and rolls into a dated version section at
the release ritual. The project is pre-release; no series has shipped yet.
