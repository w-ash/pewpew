# pewpew backlog

## Current

**v0.2.x — Phase 1 host engine core** ([v0.2.x.md](v0.2.x.md)), sequenced
into patches. v0.2.0 (render core + authoring contract), v0.2.1 (paced
clock, ANSI + browser preview sinks, `python -m pewpew run`) and v0.2.2
(typed params, enforced ranges, the param-liveness check) have landed.
**Next up: v0.2.3 — live param controls on the preview page**, plus a
per-pattern default `--map`; then v0.2.4 hot reload and user-file patterns,
v0.2.5 DDP to stock WLED (hardware ordered 2026-08-22; unblocks and may jump
the queue on arrival), v0.2.6 layer compositing.

## Also open

**v0.1.x — Phase 0 long tail** ([v0.1.x.md](v0.1.x.md)). The three de-risk
gates all passed on desktop (throughput 52×, authoring GO, pacing PASS) and
Phase 1 is underway on their strength. Remaining: the Pi-5/deployed-host
reruns (hardware-dependent), the unbought ADR-018 bench core, and the
research-tree-debt stories (archive captures, snapshot refreshes, source
pins, freshness follow-ups). Later phases live in `unscheduled.md` until
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
