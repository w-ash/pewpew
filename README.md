# pewpew

A Python-first addressable-LED control system for wearables, portables, and
mid-scale light art (room-sized and up). Quality bar: better than clown mode —
temporal dithering, perceptual color, smooth motion.

## Status: research phase → Phase 1

Before any engine code, we ran a provenance-tracked research pass over the
2026 state of the art; the Phase-1 host engine core is underway
([`docs/backlog/`](docs/backlog/README.md)). Start here:

- [`research/README.md`](research/README.md) — how the research is organized
  and how every claim traces to a source
- [`research/synthesis/architecture.md`](research/synthesis/architecture.md) —
  the recommended system structure (the end deliverable of the research pass)
- [`research/SOURCES.md`](research/SOURCES.md) — the bibliography
- [`docs/authoring.md`](docs/authoring.md) — how patterns are written

## Live preview

Run a gallery pattern against the real engine — no hardware needed:

```sh
uv run python -m pewpew run comet --map line:64 --ansi       # in the terminal
uv run python -m pewpew run fire --map grid:16x16 --preview  # in the browser
```

`--preview` serves http://127.0.0.1:7447/ — positions once over websocket,
then display-ready color frames; `--ansi` renders truecolor half-blocks for
ssh/CI. (The former hand-written JS playground is retired; the extracted
[`preview/fire-reference.js`](preview/fire-reference.js) remains as the
reference for the fire port story.)
