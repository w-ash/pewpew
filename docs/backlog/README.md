# pewpew backlog

## Current

**v0.2.x — Phase 1 host engine core** ([v0.2.x.md](v0.2.x.md)), sequenced
into patches. v0.2.0 (render core + authoring contract), v0.2.1 (paced
clock, ANSI + browser preview sinks, `python -m pewpew run`), v0.2.2 (typed
params, enforced ranges, the param-liveness check), v0.2.3 (live param
sliders on the preview page, per-pattern default `--map`) and v0.2.4 (run a
pattern from any file; hot reload with `t`, params, buffers and scalar state
kept across the swap) have landed. **The series now carries the first
installation** (re-planned 2026-10-19): one hotel room, build check-in
2026-11-10, show 2026-11-13 to 16. v0.2.5 (2026-10-26) landed the DDP sink
to stock WLED boards and the Wi-Fi bench script; the Wi-Fi test run waits
for the rig to be flashed and wired. **Next up: v0.2.6** (room map with 2D
simulation, on-site control page,
saved looks, show patterns), then v0.2.7 (room-event triggers, show health
and restart safety, the soak that now includes the ADR-010 GC retest, a show
checklist), all before check-in. Drag-to-arrange is v0.2.8; layer
compositing moves to v0.2.9, after the show.

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
