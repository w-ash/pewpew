# pewpew backlog

## Current

**v0.1.x — Phase 0 de-risk** (build plan: `research/synthesis/architecture.md` §11).
Settle the riskiest bets — NumPy throughput (R-9/ADR-011), the vectorized
authoring surface (ADR-005), and host pacing (ADR-010) — and stand up the bench
core (ADR-018) before any engine code hardens. All three benchmarks have
desktop verdicts on Apple M5 Pro: throughput 52× the R-9 target (2026-07-15),
authoring GO conditional on idiom-kit additions (2026-07-16), pacing PASS with
p99 cadence error 3.78 ms (2026-07-27). Each wants a rerun on the deployed
host; the bench core is unbought.

## Next

**v0.2.x — Phase 1 host engine core**, in progress ([v0.2.x.md](v0.2.x.md)).
All three Phase-0 gates now have desktop verdicts (item 2 GO, item 1 PASS at
52×, item 13 PASS) — each wants a rerun on whichever host gets deployed, but
none blocks the work. The Authoring-surface epic is complete as of 2026-07-27:
the render core, idiom kit, authoring docs, and the stumble-#17 contract
decision all landed, so item 2's GO is no longer conditional. Remaining: paced
clock, sinks, hot reload, DDP, param-liveness. Only the DDP-sink story is hard
blocked, on a receiver + strip. Later phases live in `unscheduled.md` until
promoted.

## Version matrix

| Version | Theme | Status | File |
|---|---|---|---|
| v0.1.x | Phase 0 de-risk: benchmarks + bench core | In Progress | [v0.1.x.md](v0.1.x.md) |
| v0.2.x | Phase 1: host engine core, end-to-end on real LEDs | In Progress | [v0.2.x.md](v0.2.x.md) |

## Changelog mode

`batch` — work accumulates under `## [Unreleased]` in the root
[`CHANGELOG.md`](../../CHANGELOG.md) and rolls into a dated version section at
the release ritual. The project is pre-release; no series has shipped yet.
