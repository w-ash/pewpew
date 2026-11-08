---
paths:
  - "src/pewpew/sinks/**"
  - "web/**"
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
(`src/pewpew/sinks/web/index.html` and the hashed files `files.json`
lists, which the engine serves), built from `web/` by Vite (React + Ark UI;
the 3D view, three.js, loads on demand). Edit `web/`, never the build. Run an engine in the
background, `uv run python -m pewpew run <looks.json> --map <spec> --preview --port 0`,
and read the port from its `preview at http://127.0.0.1:PORT/` line (7447
is often a live unattended run). Iterate with the Vite dev server against it:
`PEWPEW_ENGINE=http://127.0.0.1:PORT pnpm -C web dev` (`web/vite.config.ts`).
Open it on 127.0.0.1 or localhost: it refuses a websocket upgrade with any
other Host or Origin (`web/dev-origin.ts`).

Before committing, run `just web` and commit the rebuilt page and files
with their source: `tests/test_page_build.py` fails on a source change without a
rebuild, and CI fails when the committed page is not the build. The engine
reads the page once per process, so restart it, then verify the built
page: drive headless Playwright there, and sample the canvas with
`getImageData` — lit-pixel counts, brightness bands, and especially the
low-end-glow band the display gamma exists for (a canvas showing only
bright pixels means gamma regressed, commit `b68b96a`). Dots are added onto the background `#0b0b0e`, so a dot's core
is `min(255, LED + (11, 11, 14))`: compare the most common lit color with
the frame's bytes, not the nearest pixel, which an anti-aliased edge
matches even when every core is white. Playwright's WebKit has no canvas
`filter`, so it draws no glow; check the glow band on Chromium. The ANSI
sink is the exact-string surface: its layout goldens
(`tests/goldens/ansi_*.txt`) are the stats half for terminal output.

Board rows in the health panel need DDP on. Stream to a fake board on this
Mac, never a real one (T-7): a room whose board is this Mac's LAN address,
a small HTTP server answering `/json/info` on port 80 (macOS lets a normal
user bind port 80 only on all interfaces), and a UDP listener on 4048 that
reports `live` and `lip` while packets arrive. Stop it to see a board go
bad; restarted, it reads as rebooted (warn). Find boards skips this Mac's
own address, so it never lists the fake board. Set `PEWPEW_AUDIT_LOG` to a
scratch file so the run stays out of the real audit log.
