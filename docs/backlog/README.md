# pewpew backlog

## Current

**v0.2.x — Phase 1 host engine core** ([v0.2.x.md](v0.2.x.md); its patch
table holds each patch's status). Now: v0.2.8, typed params and a
schema-driven control page, then drag to arrange; the Wi-Fi ingest test and
the real-rig soak wait on the rig.

**Next: v0.3.x — layered effects, effect programs and agent connectivity**
([v0.3.x.md](v0.3.x.md)). Built on the integration branch `fx`, which
is merged into `main` (e37aa7d): the effects
engine, agent connectivity, the director, control page redesign phase 1
with its polish, and live audio from a laptop input.
In progress: the ESP32 line-in node (`fx-audio-node`). Not started:
redesign phases 2 and 3, audio on the page, the audio bench and the
attended audio checks. The file's "Open decisions for the maintainer"
lists what waits on the maintainer. Layer compositing, planned as v0.2.9, is its layer-stack
story.

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
| v0.3.x | Layered effects, effect programs and agent connectivity | In Progress | [v0.3.x.md](v0.3.x.md) |

## Changelog mode

`batch` — work accumulates under `## [Unreleased]` in the root
[`CHANGELOG.md`](../../CHANGELOG.md) and rolls into a dated version section at
the release ritual. The project is pre-release; no series has shipped yet.
