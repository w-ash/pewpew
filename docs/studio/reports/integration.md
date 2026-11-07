# Integration: the studio in its production container

The merged studio runs end to end in `pewpew:local`. The SPA loads the real GLBs, binds the golden
rings, and streams the Rainbow onto all 3072 pixels. Saving and share links work. With ws2 merged,
the session streams live power and the compile returns the electrical report, which the Report
panel shows. The image is 393 MB and runs as uid 1000 `pewpew`.
Without `DATABASE_URL` it writes SQLite to `/app/data/studio.sqlite3`, and its HEALTHCHECK
reports healthy.

Commits on `studio-integration`:
- `3fc4097` feat: run the studio web app on the real backend
- `6ba2e7a` fix: address the ws4 code review (`reviews/ws4-fixes.md`)
- `57aa5f8` fix: word the missing-model notice for several types

On `studio`, ws2 (`studio-ws2-review`) merged without conflicts. `schemas/`, `openapi.json` and
`uv.lock` did not drift, so orval did not rerun.

## What I fixed

1. **OpenAPI and orval.**
   - The committed `openapi.json` already matched the app. I tightened `IssueModel` to
     `level: Literal["error", "violation", "warning"]` and `ref: str | None`
     (`src/pewpew/studio/app.py:73`), then regenerated the spec. The model only documents the 422
     body, because the app builds its responses as dicts.
   - orval now runs with `mock: false`. Its faker mocks import `@faker-js/faker`, which is not
     installed, and the app has its own msw mocks in `web/src/mocks`. The output is committed
     under `web/src/api/generated`, and `endpoints.ts` calls the generated functions.
   - **Types from the spec:** `Issue` (`IssueModel`), `IssueLevel` (`IssueModelLevel`) and
     `SavedArrangement`.
   - **Types still written by hand**, because the spec leaves those bodies free-form:
     - `Arrangement` and its parts: the compile and save bodies are `dict[str, Any]`.
     - `Catalog` and its entries: `/api/catalog`.
     - `CompiledRig` and its parts: the compile response.
     - `ParamSpec`: `PatternInfo.params` is a list of free-form dicts, and `hello` and `declare`
       are websocket messages outside the spec.
   - I removed the hand-written `PatternInfo`, because nothing calls `/api/patterns`.
2. **GLBs.** The viewer already loaded each type's `assembly_url`. The real GLBs work as they are:
   `readAssembly` finds `extras.pixel_axis` on the root node and `glow`/`gain` on each part.
3. **Null `assembly_url`.** `digest` and `assembly_url` are now nullable. `assembliesFor` leaves
   those types out, and `missingAssemblies` names them in a stage notice
   (`web/src/viewer/instances.ts`, `web/src/viewer/Stage.tsx`).
   - Runtime check: I served the container's catalog with every URL nulled. The page made no GLB
     requests, threw no page errors, and showed "This server has no 3D model for
     clen-rgbw-bar-1m, point-v0, eye-v0, so they are not drawn".
4. **Attachment colour.** An attachment instance now samples a constant host y: the centre of
   pixel 0 at `end_a`, or of pixel n−1 at `end_b` (`endPixelY`, `web/src/viewer/instances.ts`).
   Both `pixels` and `pixel_nearest` therefore read that one texel exactly.
   - Before the fix, each plug part sampled the bar's own lit span and mixed in its neighbour
     (pixels 62 and 63 at `end_b`). The plug sits at local y −15…0 mm, inside the diffuser (read
     from the served GLB's accessors).
5. **Default arrangement.** `web/src/store/doc.ts` imports
   `src/pewpew/rig/examples/golden-rings.json`, and the copy in `web/src/arrangements/` is deleted.
   Vite's `server.fs.allow` adds that directory, and the Dockerfile copies
   `src/pewpew/rig/examples/` into the node stage at the same path relative to `web/`.
6. **Image.** The merged Dockerfile and `.dockerignore` built on the first try. The only change is
   the examples `COPY` in item 5.
7. **The ws4 review.** All 11 findings are fixed, plus the accent colour, which had been converted
   to linear twice (`#2561d2` on screen instead of `#6aa6ea`). Details are in
   `reviews/ws4-fixes.md`.

## Smoke test

I ran `docker run --rm -p 8080:8000 pewpew:local` without `DATABASE_URL`, then a scratch script
driven by urllib and websockets 17.0.1. After the ws2 merge it passed all 16 checks.

| Check | Result |
|---|---|
| `/health/live` | 200 `{"ok":true}` |
| `/api/catalog` | all 4 types have an `assembly_url` |
| GLBs | 200 `model/gltf-binary`, `immutable`: bar 81,760 B, tube 57,860 B, eye 36,496 B, point 21,188 B |
| `POST /api/compile`, golden rings | 200, n = 3072, 48 fixtures, 21 ms |
| its `report` | non-null: 2 controllers, 6 outputs (chains), 24 feeds, 5 PSUs, `worst_w` 1,228.8 W (51.2 A), and 7 `rests_on_assumed` warnings |
| `POST /api/compile`, bad body | 422 `{"issues":[…]}` |
| websocket | `hello` (rainbow, 30 fps), then `bound` n = 3072 |
| frames | 301 in 10 s, all 9224 B (8 + 3·3072), 30.1 fps, seq 2→302 |
| `power` messages | 20 in 10 s (2 Hz), 445.8–475.8 W |
| save, then load | 22-character id; GET returns the same JSON; an unknown id gives 404 |
| `/` and `/a/<id>` | 200 `text/html`, the SPA; its JS asset is 200 |

**Report panel.** Headless Chromium against the container showed live watts (about 460 W) and the
report's totals, with no page or console errors (`integration/report-panel.png`). The panel prints
`worst_w` as 1229, because it rounds every number to four significant digits. It renders the whole
report as nested lists, about 36,750 px tall for the golden rings.

## Visual check

**Method.** Headless Chromium (Playwright 1.64.1, SwiftShader) ran against the container at
1200×800, the size of `overview.png`, in dark mode with reduced motion. The canvas was read back
by screenshot, then 2D canvas, then `getImageData`, three samples 0.5 s apart. The counts are:
- **Lit:** max channel > 120 and max − min > 80.
- **Glow:** max − min > 24 and max > background + 16. Both backgrounds are (22, 26, 31).
- **Low band:** glow pixels with max channel < 96.

The prototype figures cover its stage, the region (26, 26, 848×764).

| | lit | lit share | glow | low band (share of glow) | glow bbox w/h |
|---|---|---|---|---|---|
| studio, Angle view | 31,335 | 5.2% | 36,755 | 3,596 (9.8%) | 2.05 |
| `overview.png` | 29,856 | 4.6% | 36,208 | 3,560 (9.8%) | 2.06 |

- **By eye** (`integration/golden-rings.png` against `prototype/overview.png`):
  - It matches: two rings of 24 tilted inner end down, the same framing and footprint.
  - It differs in four ways, all expected:
    1. The prototype's placeholder colours each tube by radius. The studio runs pewpew's
       Rainbow, so the hue changes along each bar.
    2. The studio draws the dark housing under each diffuser.
    3. The end pieces glow faintly, at the data's assumed gain of 0.25. The prototype draws them
       at full brightness.
    4. There are no pivot circles.
- **End pieces.** In the close-ups (`integration/end-eye.png`, `integration/end-point.png`),
  each eye and point takes the hue of its own bar's end LED, dimmed.
- **Low-end glow.** Glow pixels fill every 32-wide band of max channel from 32 up
  (436 / 3,160 / 3,572 / 3,821 / 2,376 / 1,598 / 21,792). The dim band is the prototype's share,
  so the display bytes keep their low end.
- **Roll.** I set `roll_deg` on both rings through the ring editor's Roll field, then deselected.
  The samples varied by less than 0.5% at each setting.

  | roll_deg | Top lit | Angle lit |
  |---|---|---|
  | 0 | 39,280 | 31,335 |
  | 90 | 36,570 | — |
  | 180 | 20,126 (−49%) | 22,026 (−30%) |

  At 180°, the Top view shows the dark housing with only the diffuser's rim lit, and the Angle
  view shows the housing above each diffuser (`canvas-top-roll180.png`,
  `canvas-angle-roll180.png`). The lit face turns with `roll_deg`.
- **Shared link.** `/a/<id>` from a fresh save opened with the read-only banner and went live
  at 3072 px.
- **GLB retry (review finding 4).** With the first GLB request routed to a 502, the stage showed
  the error with Retry. Pressing Retry loaded the models and cleared the alert.
  - R3F 9.8.2 passes `reportError` as the reconciler's `onCaughtError`
    (`web/node_modules/@react-three/fiber/dist/events-*.esm.js`, `logRecoverableError`). So a
    load error the boundary catches still reaches `window.onerror`, which is harmless.
- **Errors.** The visual run raised no page errors and no console errors.

Screenshots are in `docs/studio/reports/integration/`: `report-panel.png`, `golden-rings.png` (the full page),
`canvas-angle-roll0.png`, `canvas-top-roll{0,90,180}.png`, `canvas-angle-roll180.png`,
`end-eye.png` and `end-point.png` (at DPR 3).

## Still open

- Still untested: a real phone, `wss` on Fly, and a GPU browser. The run here was software WebGL.
  `e2e/color.spec.ts` covers byte-exact colour.
- These are unchanged from ws4: the `THREE.Clock` deprecation warning and the 1.04 MB three.js
  chunk.
