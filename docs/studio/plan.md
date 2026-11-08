# pewpew studio: arrange LED fixtures in 3D, run real effects on them, model the rig, share by link

> Record from 2026-10. Since 2026-11-08 the hosted app is the Gallery and serves the Console's page; the routes and the studio page below are gone. See [README.md](README.md) for the current system.

## Context

The maintainer and an earlier agent session built a three.js prototype: 48 1M LED Pixel Bars in
two golden-ratio rings, with optional 3D-printed points and eyes on the ends. A copy of its files
is in `docs/studio/prototype/`. The maintainer wants pewpew to absorb it, and wants it today.

The fixture record is the maintainer's fixture notes, which are not public. INV-001 is the bar
and INV-002 is the 1.5M 360 LED Tube; the RES- rows are the research.

The maintainer's instructions. The first three came through the earlier session; the rest were
said in this session. The first and fourth are summarized; the others are verbatim.

- pewpew should take what it can from the prototype and integrate it, so that it can map its
  lighting effects onto a 3D model like it, with the 1 m tubes and the needle extension options.
  The maintainer wants to try different arrangements in 3D space, map the effects to them, and
  model the power, wiring and controller needs of each. pewpew should not use Claude artifacts:
  the maintainer wants to host it on fly.io and share possible arrangements by link.

> "the geometry for this arrangement is just one possible arrangement. pewpew should ultimately
> support any arrangement in 3D space." / "not necessarily keep it out of the model, but it would
> be one possible configuration of that model."
>
> "i asked you to do the 3d model now ... i need it today."

- Use the same fly.io setup as the maintainer's other fly.io apps.

> "we're starting by modeling just the 64 pixel, one meter diffused led bars"
>
> "you can serve as orchestrator, have a bunch of specialised subagents do most of the work (with
> appropriately sized models for their tasks) ... our system should be composable, where we can
> add other lights with other power needs, chipsets, etc in the future. before you build
> everything, you should spin up a subagent to design our domain model. again, have subagents
> search the web for inspiration, and make sure we're using state of the art october 2026 best
> practices, libraries, tech, etc"
>
> "we should fully accurately 3d model them, including the fact we need to have the bar and the
> diffusor acurately modeled, so we can see the true orientation of the part of the bar that
> lights up."

The result is a new studio app. A visitor builds any arrangement of fixtures in 3D, runs the real
pewpew engine on it, reads a power, wiring and controller report, and saves it to a share link. It
runs on the laptop and on fly.io.

## Decisions

- **Geometry.** Any arrangement in 3D. The golden rings are one saved arrangement, built from a
  general `ring` preset.
- **Fixtures.** The catalog is composable: fixture types, pixel formats, connectors, cables, PSUs
  and controllers are validated data, not code. The studio ships the 1M LED Pixel Bar. INV-002
  must be expressible as catalog data alone, and a test proves it.
- **Bar geometry.** The bar is modeled as a full assembly: a housing with its T-slot, a diffuser
  with its flat, end caps, pigtail connectors, and LEDs facing into the diffuser. Every dimension
  carries its source and a `measured` flag. Clen's drawing gives a housing 18 mm deep; the maintainer's
  rough figure is about 25 mm (Q-011). Clen gives the round diffuser a 330° beam.
- **Stack.** It matches the maintainer's other fly.io apps, at the October 2026 versions the
  research found:

  | Layer | Choice |
  |---|---|
  | Backend | FastAPI + uvicorn + pydantic 2.14 |
  | Frontend | React 19, @react-three/fiber 9.8, drei 10.7, three r186, zustand 5, Vite 8, TypeScript 7, the control page's styles and controls (one package, `web/`), Vitest, Playwright, pnpm |
  | Type sharing | `scripts/export_openapi.py` → orval |
  | Database | Neon Postgres in production, SQLite locally and in tests |

  - pydantic joins the core for the file format.
  - FastAPI, uvicorn, psycopg and manifold3d 3.5.4 go in a `studio` extra. manifold3d builds the
    bar geometry.
  - The laptop `run --preview` page is unchanged.
- **Rendering.** The engine renders on the server, one aura pipeline per visitor (the one `run` builds, ADR-025), on its own thread.
  Frames reach FastAPI's websocket through `loop.call_soon_threadsafe` into a one-slot,
  newest-wins mailbox. There is no JavaScript copy of the effects
  (backlog story "Keep preview ports honest", `docs/backlog/v0.2.x.md`).
- **Color.** The page draws the display-ready bytes unchanged. It uses a custom `shaderMaterial`
  over an sRGB-tagged RGBA `DataTexture` with `LinearFilter`, one `InstancedMesh` per GLB part,
  and no bloom. The Domain model section explains the choice.
- **Share links.** They are immutable, content-addressed snapshots with 128-bit ids. Opening one lets a visitor edit
  and save a copy. Limits apply per `Fly-Client-IP`. The page stops frames while its tab is
  hidden, because Fly bills egress at $0.02/GB.

## Domain model

The domain-model designer (Plan agent, Opus) wrote the full design, which is appendix A6 and will
be saved as `docs/studio/domain-model.md`. These are its decisions.

- **Three layers.** The split follows GDTF (catalog) and MVR (scene). The electrical layer is new
  design, because no surveyed format models PSUs, feeds or cables.
  - **Catalog.** Hand-written JSON, one file per entity, discriminated by `kind`, in
    `src/pewpew/rig/catalog_entries/<kind>/`. The kinds are `fixture_type`, `attachment_type`, `chipset`,
    `connector`, `cable`, `psu`, `firmware` and `controller`.
  - **Arrangement.** Written by the user or the studio: `fixtures` with poses, preset `groups`
    (`ring`, `array`), `controllers`, `psus`, and `wiring`. Wiring is either explicit chains and
    feeds, or `auto`.
  - **Derived.** Never stored: instances, world matrices, the pixel table, output slices, the
    auto-wiring, and the report.
- **Provenance on every fact.** A catalog value is a literal or `{"v", "status", "src"}`, where
  status is one of `measured | stated | inferred | derived | assumed`. Values are SI floats with
  unit suffixes. A dimension can be an expression over the entity's `dims`, evaluated in Python
  only.
- **The bar as an assembly.** INV-001 is built from Clen's drawing.
  - The housing profile includes its T-slot, cut by CSG.
  - The diffuser is a 30.2 mm circle cut flat 11.9 mm below its axis. The resulting 18.6 mm
    chord matches the 18 mm housing, which is a consistency check.
  - The part list is end caps, strip, LED bodies and diffuser, plus anchors for the in/out
    connectors (male/female, inferred from RES-010), the ends, and the T-slot.
  - Pixels sit on the housing's top face and face +Z.
  - Each part declares `glow`: `pixels` (sampled along the axis, clamped at the ends),
    `pixel_nearest`, or `none`.
- **Frames.** Meters, y-up, right-handed; quaternions stored xyzw with w ≥ 0, never Euler. The
  fixture-local frame has its origin on the diffuser axis at mid-length.
  - +Y runs from data-in to data-out.
  - +Z is the LED facing.
  - Roll turns the lit face; the dark housing sits at −Z.
  - `ring` expansion reproduces the prototype's `makeBasis(side, dir, face)` exactly
    (`docs/studio/prototype/golden-tubes-3d.html:424-430`).
  - MVR import and export convert Z-up mm with a fixed matrix.
- **Point and eye.** These are `attachment_type`s built on the host's own `diffuser_outer` profile,
  so they fit flush. They glow at a gain of 0.25, an assumed value, because the maintainer expects
  the glow "would probably be minimal" (the maintainer's fixture notes).
- **One geometry implementation.** `scripts/build_assemblies.py` (`just assemblies`) builds each
  fixture and attachment type's mesh with `manifold3d` (studio extra) into a deterministic GLB,
  committed as package data in `src/pewpew/rig/assemblies/`. The server serves it at a
  content-hash URL and needs no `manifold3d`. The GLB carries each
  part's `glow` and `gain` and the pixel axis. The browser never expands presets, places pixels,
  wires anything, or does power arithmetic.
- **Compile.** `compile_rig(arrangement, catalog)` is pure: no I/O, no clock, no RNG.
  1. Expand groups into instances.
  2. Wire them.
  3. Index pixels in data order: controller, then output, then chain, then pixel. Pixel `j`
     sits at `−span/2 + (j+0.5)·span/n`.
  4. Contain-normalize to float32 for `Renderer`.
  5. Slice per output and per controller.
  6. Report.
- **Auto-wiring.** Deterministic:
  - The per-output cap is `⌊(1/fps − reset)/t_px⌋`, so 9 bars at 40 fps.
  - A chain breaks where a data hop passes 3 m.
  - Feeds stay at or under 75% of the connector rating (RES-033) and under 10% drop.
  - PSUs fill first-fit to 80%.
- **Validation in three tiers:**
  - errors, such as unknown fields or a fixture in two chains;
  - violations, such as an output over its cap or a feed over its rating, which fail under
    `--strict`;
  - warnings, such as more than 800 px on an output, a drop over 10%, or a result that rests on
    an assumed value.
- **Versioning.** Files carry `format` plus an integer `version`, migrated by pure functions.
  The compile output carries a `catalog_digest`, so an old share link can say when the bar's
  dimensions changed.
- **Composability, proven by data alone.** INV-002 is one fixture file, one chipset file, and one
  `led_types` row in the WLED firmware file. A Dig-Octa controller is one file. A guard test
  fails if a catalog id appears in any `rig/*.py`.

Defaults the design sets, all of which the maintainer can change:

- connectors designed to M12's 4 A at 75% loading;
- PSUs loaded to 80%, following [flexfire's derating guide](https://flexfireleds.com/blog/LED-power-supply-derating);
- 10 cm point and eye, the prototype's placeholder;
- `data_in: "inner"` on rings.

Everything that needs calipers or a bench test is listed in A6 §9 as a measurement. None of it
blocks building.

Where I settled a conflict between reports:

- **Color.** The texture is RGBA u8 tagged `SRGBColorSpace`, and the shader includes
  `colorspace_fragment` with `toneMapped: false`. The diffuser then blends neighboring LEDs in
  linear light, as ADR-001 does (`research/synthesis/decisions/ADR-001-internal-color-pipeline.md`), and the bytes still come out unchanged at texel centers
  ([A2](planning/2026-10-22-a2-threejs-viewer-and-editor.md), managed path). This replaces the raw path.
- **Share ids.** Each id is the first 128 bits of the SHA-256 of the canonical JSON, base64url
  encoded, which follows the design's content addressing. The rows live in Neon, not on a volume.

## How the work runs

I orchestrate. Specialist subagents do the building, each in its own git worktree with a narrow
brief. I review each diff, run the gates and merge.

**Step 0: save the planning record before any building.** This is one commit. A Haiku
`mechanical-edit` agent splits this plan file's appendix into the files below, and I review the
result:

- `docs/studio/planning/2026-10-22-<topic>.md`: each report in the appendix below, verbatim.
  There is one file per report, and each file has a header naming its date, agent role, model and
  brief. Their URLs are not yet in `research/SOURCES.md`; workstream 7 adds the ones the ADRs rely
  on.
- `docs/studio/domain-model.md`: the domain-model design, as approved.
- `docs/studio/plan.md`: this plan, minus the appendix.
- `docs/studio/README.md`: a short index linking all of the above.
- **Link pass, one Sonnet subagent.** Every citation in those files becomes a full link:
  - a full https URL for the web; a bare domain or page title is not enough;
  - a GitHub permalink pinned to a tag or commit, with line anchors, for code;
  - a repo-relative path with line numbers for local files.

  The agent checks that each web link resolves. One that doesn't is marked
  `[link not verified]`, not dropped. Each file ends with a Sources list.

Every agent brief from here on requires sources cited as full links, in the same form. Every
building agent's brief points at `docs/studio/`. Each one records what it did in its backlog
story's Notes, the project's existing convention, so later agents find the outcome where they
already look.

| # | Workstream | Agent and model | Depends on |
|---|---|---|---|
| 1 | Rig core per A6 §6: `src/pewpew/rig/` models, expr, catalog loader and digest, data files (INV-001, INV-002, chipsets, connector, cables, PSU, WLED firmware, the S3 controller), pose, presets, compile, migrate, committed JSON Schemas, plus `run --map file.json` | general-purpose, Opus | the approved design |
| 1b | Geometry: `rig/geometry.py` CSG profiles → manifold3d → deterministic GLB with part `extras` and the pixel axis; the point and eye attachments | general-purpose, Opus | 1's models |
| 2 | Wiring and electrical per A6 §4: auto-wiring, output timing, feeds, fuse windows, drop, PSU packing, Class 2, effect power from the linear frame, BOM, the three validation tiers | general-purpose, Opus | 1 |
| 3 | Backend: FastAPI app, session threads and frame bridge, REST (catalog, arrangements, share), websocket protocol, store (SQLite/Neon), limits, health, SIGTERM drain, OpenAPI export | general-purpose, Sonnet | 1 |
| 4 | Frontend: `web/src/studio/` Vite + React + R3F; orval client; GLB parts drawn as instanced meshes using server matrices; LED `DataTexture` shader reading each part's `glow` and `gain`; editor (select, gizmo with snaps, inspector, duplicate, flip, ring/array tools, undo), report and share panels | general-purpose, Opus for the viewer and shader, Sonnet for the panels | 1b's GLB; 3's OpenAPI |
| 5 | Example looks for the studio: `GET /api/looks` serves `examples/*.look.json`; each passes `verify looks` on the golden-rings mapping | general-purpose, Sonnet | 1 |
| 6 | Deploy: Dockerfile (uv + node + runtime stages), `.dockerignore`, `fly.toml`, `release.yml`, `docs/deployment.md`, copied from another of the maintainer's fly.io apps | general-purpose, Haiku | 3, 4 |
| 7 | Records: ADR-024 (hosted studio, stack, trust model), ADR-007 amendment (format), source fragments + `merge_sources.py`, backlog epic, CHANGELOG | general-purpose, Sonnet | the design |
| 8 | Gates: `uv run pytest`, `pnpm check`/`test`, visual check per `.claude/rules/preview-visual-verify.md` | gate-runner (Haiku) and me | each merge |
| 9 | Independent review per section (the maintainer, 2026-10-22): a `/simplify` pass that applies its cleanups in its own worktree, and a `/code-review high` pass that reports verified findings. Neither reviewer is the author or reads the author's report first. I verify the findings, apply the real ones, re-gate, then merge. Each review's report goes in `docs/studio/reports/reviews/` | general-purpose, Sonnet (simplify), Opus (review) | each workstream |

Workstreams 1b, 2, 3, 5 and 7 run in parallel once 1 lands. Workstream 4 starts on 1's committed
JSON Schema and switches to the orval client when 3's OpenAPI is in.

The maintainer runs, or tells me to run, the outward-facing steps:

1. Create a Neon project.
2. `fly launch --no-deploy`.
3. `fly secrets set DATABASE_URL=...`.
4. The first `fly deploy --ha=false` and `fly scale count 1`.

The uncommitted backlog edits in the working tree are not mine. Every commit leaves them out.

## Verification

- `uv run pytest` stays green and under 30 s. The new tests cover:
  - the compiler: pixel pitch, Contain normalization, and wiring order;
  - golden rings at 30°: 386.6 cm wide without end pieces and about 404 cm with them
    (`docs/studio/prototype/golden-tubes-3d.html:273`);
  - INV-002 compiling from catalog data alone;
  - the report's arithmetic against hand-worked cases;
  - the server: session, edit-rebind with `t` kept, look swap, oversize refusal, save and load;
  - the example looks pass `verify looks`.
- `pnpm check` and `pnpm test` pass in `web/`.
- The visual check uses a headless Playwright screenshot of the golden rings, compared with
  `overview.png`, plus `getImageData` statistics including the low-end glow band. The bar's lit
  face must turn with `roll`.
- Container: `docker build`, then `docker run -p 8080:8000` without `DATABASE_URL`. Save an
  arrangement and open its link in a second browser.
- After the deploy: open the https URL on a phone, confirm frames arrive over `wss`, and confirm
  `fly status` lists one machine.

## Sources

- The maintainer's fixture notes (not public)
- `docs/studio/prototype/golden-tubes-3d.html`, lines 273 and 424-430
- `docs/backlog/v0.2.x.md`, story "Keep preview ports honest"
- `research/synthesis/decisions/ADR-001-internal-color-pipeline.md`
- `planning/2026-10-22-a2-threejs-viewer-and-editor.md`
- https://flexfireleds.com/blog/LED-power-supply-derating
