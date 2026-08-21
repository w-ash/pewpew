---
paths:
  - "preview/**"
  - "src/pewpew/sinks/**"
---

# Measurable ≠ visible

Changes to visual surfaces are verified BOTH ways before committing:

- **Eyeball a screenshot** (headless Playwright; binaries are cached under
  `~/Library/Caches/ms-playwright`). Metrics have passed while the render
  was scrambled (the lattice color/position desync) or imperceptible (torus
  precession at 10³ cells — motion must read to a human, not just to a diff).
- **Statistics on the actual pixel/state data** — eyes have missed what
  stats caught (comet sparkle ratcheting to permanent white).

The visual surface is the preview sink's served page
(`src/pewpew/sinks/web/index.html`; the old `preview/index.html`
playground was retired 2026-08-20). Verify against a live engine: run
`uv run python -m pewpew run <pattern> --map <spec> --preview` in the
background, drive headless Playwright at `http://127.0.0.1:7447/`, and
sample the canvas with `getImageData` — lit-pixel counts, brightness
bands, and especially the low-end-glow band the display gamma exists for
(a canvas showing only bright pixels means gamma regressed, commit
`b68b96a`). The ANSI sink is the exact-string surface: its layout goldens
(`tests/goldens/ansi_*.txt`) are the stats half for terminal output.
