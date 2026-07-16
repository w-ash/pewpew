# pewpew backlog

## Current

**v0.1.x — Phase 0 de-risk** (build plan: `research/synthesis/architecture.md` §11).
Settle the two riskiest bets — NumPy throughput (R-9/ADR-011) and the vectorized
authoring surface (ADR-005) — and stand up the bench core (ADR-018) before any
engine code hardens. Desktop throughput datapoint landed 2026-07-15: NumPy 52×
the R-9 target on Apple M5 Pro; Pi 5 rerun pending.

## Next

Phase 1 (host engine core, end-to-end on real LEDs) once both Phase 0 gates and
the §12 item 13 pacing-jitter soak clear. Later phases live in
`unscheduled.md` until promoted.

## Version matrix

| Version | Theme | Status | File |
|---|---|---|---|
| v0.1.x | Phase 0 de-risk: benchmarks + bench core | In Progress | [v0.1.x.md](v0.1.x.md) |
