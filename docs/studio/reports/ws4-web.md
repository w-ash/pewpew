# ws4: studio frontend

Built `web/`, a React + three.js app. A visitor arranges fixtures in 3D, watches pewpew's effects
streamed onto them, edits the arrangement with undo, reads the rig report and saves a share link.
It runs against an msw mock (`pnpm dev:mock`) or the backend through Vite's proxy (`pnpm dev`).

I ran it against a scratch backend: branch studio-ws3-server's `src/` with studio-ws1-rig's
`src/pewpew/rig/` laid over it and a stub `geometry.py` that served the mock's GLBs. That run
covered catalog, compile, bind → `bound` → live frames from the real engine, a ring edit that
rebound, and a save that returned a 22-character id. `pnpm check`, `pnpm test` (63 tests) and
`pnpm e2e` (2 tests) pass.

## What is where

| Path in `web/` | Contents |
|---|---|
| `src/api/` | `types.ts` (hand-written, see Deviations 2), `client.ts` (`customFetch`, orval's mutator signature), `endpoints.ts`, `queries.ts` (React Query) |
| `src/session/` | `protocol.ts` (message and frame parsing), `client.ts` (`SessionClient`: reconnect, debounced bind, pause/resume) |
| `src/viewer/` | `Stage.tsx` (Canvas, views, spin, gizmo), `Rig.tsx` (instancing, frame upload), `ledMaterial.ts`, `ledTexture.ts`, `assembly.ts` (GLB → parts), `instances.ts`, `views.ts`, `RigBoundary.tsx` |
| `src/editor/` | `arrangement.ts` (edits), `pose.ts` (quaternion and yaw/pitch/roll), `history.ts` (undo), `Gizmo.tsx` |
| `src/panels/` | Arrangement, Effect, Report, Share |
| `src/store/` | zustand: `doc.ts` (history, selection, share state), `session.ts` |
| `src/mocks/` | msw handlers, a mock compiler, stand-in GLBs, a fake frame stream, a hand-written three-bar rig |
| `src/arrangements/golden-rings.json` | the default arrangement, a copy of ws1's file (Deviations 3) |
| `e2e/` | `smoke.spec.ts` (page against the mock), `color.spec.ts` and `fixtures/color.*` (byte readback) |

## Viewer

- **Instancing.** Each GLB part is one `InstancedMesh` across all instances of its type. The instance
  matrix is the server's column-major `rig.fixtures[].matrix`, or `attachment_matrices[end]` for an
  end piece. Each instance has four attributes:
  - `aRow`: the fixture's texture row;
  - `aAxis`: the host's `y0`, `span` and pixel count;
  - `aAxisY`: maps a part-local vertex to host-local y, so an end piece samples past the span and
    clamps to the end LED;
  - `aSelected`.
- **LED texture.** RGBA u8, `SRGBColorSpace`, `LinearFilter`, `ClampToEdgeWrapping`, no mipmaps,
  `max pixel_count` wide with one row per fixture. Each frame fills it through
  `pixel_start`/`pixel_count`, followed by one `needsUpdate` per rendered frame (newest frame wins).
  A frame is used only if it is exactly 8 + 3n bytes, where n comes from the last `bound`, and n also
  equals the drawn rig's n.
- **Shader.** One `ShaderMaterial` per part, with `toneMapped: false` and `colorspace_fragment`.
  - `pixels`: samples u = (y − y0)/span, clamped to the end texel centers.
  - `pixel_nearest`: `texelFetch` of the fragment's own texel.
  - `none`: a dark albedo times a fixed hemisphere term, computed in the shader rather than with a
    scene light.
  - Lit parts are multiplied by `extras.gain` and dimmed by mix(0.6, 1.0, |n·v|). There is no bloom.
  - `e2e/color.spec.ts` renders four known texels and reads the canvas back. Both `pixel_nearest`
    and `pixels` return the bytes exactly at texel centers, so nothing is encoded twice.
- **The rest.** The Canvas uses `dpr={[1, 2]}`, `flat` and WebGLRenderer. The Angle, Top and Side
  views and their camera tween follow the prototype. Spin uses OrbitControls' `autoRotate` at one
  turn a minute at 60 fps. A GLB that fails to load shows an error in the stage, and the rest of
  the app keeps working.

## Session

- The socket URL is `wss://` over https and `ws://` otherwise.
- Reconnect backoff runs 1 s → 10 s and resets only on `bound`. A server that drops the session on
  every bind is therefore retried ever more slowly.
- `bind` follows each compile the server accepts, debounced 250 ms. On every socket open, the client
  sends the last accepted arrangement and the chosen pattern immediately.
- `pause` is sent when the tab is hidden and `resume` when it is shown, including at open.
- All seven server messages are handled.
- The sliders follow the preview's `makeLevers` (`src/pewpew/sinks/web/index.html:145-185`):
  - range and step come from the engine;
  - a slider under the pointer ignores echoes;
  - a `refused` snaps the slider back and shows the reason for 4 s.

## Editor and panels

- **Selection.** A click on a bar or a list row selects it. Clicking a group member selects its
  group, using the compiled `group` field.
- **Gizmo.** drei `TransformControls` with 1 cm and 1° snaps and a world/local toggle. drei turns
  the default OrbitControls off while dragging (`dragging-changed`, drei v10.7.9 link below).
  - While dragging, the selection's instances move by the gizmo's delta applied to the server
    matrices.
  - On release, the pose commits as `{position_m, quat_xyzw}` with w ≥ 0, and the next compile
    redraws from the server.
- **Inspector.** Position in meters, and yaw, pitch and roll in degrees as three.js Euler order
  `YXZ` (yaw about Y, then pitch about the new X, then roll about the new Z). Zeros are the
  identity. Only quaternions are stored.
- **Edits.** Add (bar, ring, array), duplicate, delete, flip, explode, and a None/Point/Eye control
  per end.
  - Flip on a bar is an exact half turn about local +Z, with the end pieces swapped so they stay in
    place. On a ring it toggles `data_in`; on an array it flips `member`.
  - Explode builds free fixtures from the compiled member matrices.
- **Ring and array editors.** Every field change commits, and runs of the same field merge into one
  undo step. The compile query is keyed on the arrangement, so edits preview live while the last
  good rig stays on screen.
- **Undo and redo.** A hand-written stack of whole-arrangement snapshots, capped at 200. I chose it
  over zundo for three reasons:
  - zundo's last commit is 2025-04-29
    (`docs/studio/planning/2026-10-22-a5-stack-and-libraries.md:20`).
  - The studio needs explicit commit points: drag end, and merged runs of edits to one field.
  - The stack is 60 lines with its own tests.
- **Import and export.** JSON import and export.
- **Report panel.**
  - Errors are solid red, violations orange-tinted with a solid border, and warnings dashed amber.
  - Live watts come from `power`.
  - The report renders as nested lists. A value shaped `{v, status}` shows its status, and
    `assumed` gets a highlighted label; so does a node with `assumed: true` or a non-empty
    `assumptions`, `assumed_from` or `rests_on` list.
- **Share.**
  - `POST /api/arrangements` gives `/a/{id}`, and the URL changes to it.
  - Opening `/a/{id}` loads the arrangement with a read-only banner. The first edit forks it, and
    the URL returns to `/`.
- **Phone.** The stage sits above the panels. Every control is at least 44 px (`min-h-11`).

## Deviations from contracts.md and the plan

1. **Bind timing.** The first `bind` waits for the first successful `POST /api/compile`; on a
   reconnect it is sent as the socket opens. Frames before `bound` are dropped, as ws3 asked.
   Neither changes the protocol.
2. **No orval output yet.** `orval.config.ts` points at `../openapi.json`. A trial run against ws3's
   export produced working functions whose names match `endpoints.ts`. The spec types the catalog
   and compile responses as free-form objects (`GetCatalog200 = { [key: string]: unknown }`), so
   the hand-written `types.ts` stays until ws3 declares response models. It follows ws1's pydantic
   models (Sources).
3. **Default arrangement.** `web/src/arrangements/golden-rings.json` is a byte copy of
   `src/pewpew/rig/examples/golden-rings.json` from studio-ws1-rig, because that file is not on this
   branch. After the merge, import the repo file in `src/store/doc.ts` and add `..` to Vite's
   `server.fs.allow`.
4. **Selection dims the rest.** While something is selected, other fixtures glow at 30%. The bytes
   reach the screen unchanged only when nothing is selected.
5. **Patterns from `hello`.** The pattern list and knobs come from `hello`; `GET /api/patterns` is
   not called.
6. **Attachments use `attachment_matrices`.** This ws1 addition is not in contracts.md. Without it,
   the viewer falls back to a GLB `extras.anchors`, then to the ends of the pixel axis, with end_a
   given a half turn about Z.

## What still needs the real backend

- **ws1b's GLBs.** `assembly.ts` reads `extras.pixel_axis` from the glTF root, the scene or the
  first node that has it, and `glow`/`gain` from each mesh or its nearest ancestor. If ws1b puts
  them elsewhere, that file changes. Nothing has loaded a real GLB yet.
- **ws2's report and power.** The report panel has only seen the mock's invented report; the real
  compile returns `report: null` today. ws2 should mark assumed results in one of the shapes the
  panel detects.
- **A visual check on real geometry against `overview.png`** (workstream 8), on a phone, over
  `wss` on Fly.

## Open issues

- **Unbounded retries.** On ws3's branch without ws1's rig, a `bind` raised `ModuleNotFoundError`,
  which is not a `ValueError`, and the session closed. The client then retries with growing
  backoff.
- **Stale openapi.json.** The `openapi.json` committed on studio-ws3-server is out of date with its
  own `app.py`. Its operationIds (`get_catalog_route`, `compile_route`, …) differ from a fresh
  export (`get_catalog`, `compile_arrangement`, …). Regenerate it before running orval.
- **`aim` poses.** A free fixture placed by `aim` reads its rotation from the compiled matrix and is
  rewritten as a quaternion on its first edit. A group placed by `aim` cannot be moved or flipped;
  the panel says so and offers explode.
- **Gimbal lock.** The inspector's yaw/pitch/roll lock at pitch ±90°. The stored quaternion is
  unaffected.
- **Drag preview after a failed compile.** If the compile after a drag fails, the preview stays
  where the drag left it until undo or the next good compile.
- **Bundle size.** The three.js chunk is 1.04 MB minified, 278 kB gzipped.
- **Mock drift.** The mock's ring expansion and end frames matched ws1's compiler to 5e-10 on the
  golden rings on 2026-10-22. It is a JS copy for dev and tests only, so it can drift.
- **Console warning.** "THREE.Clock: This module has been deprecated" is logged at startup. My
  inference is that it comes from R3F 9.8.2, since `web/src` never uses `Clock`.
- **Playwright browsers.** Playwright 1.64.1 needs `pnpm exec playwright install chromium` (headless
  shell v1248).

## Sources

- Contracts and design: `docs/studio/contracts.md`, `docs/studio/plan.md:79-81` and `:168-172` (color decision),
  `docs/studio/domain-model.md:171-200` (frames and ring formula),
  `docs/studio/domain-model.md:245-273` (glow), and `docs/studio/domain-model.md:476-477` (RGBA
  replaces RGB).
- Prototype: `docs/studio/prototype/golden-tubes-3d.html:8-40` (tokens), `:338` (edge dimming),
  `:354-378` (eye), `:460-468` (views and fit).
- Preview client: `src/pewpew/sinks/web/index.html:145-185` and `:224-241`. Display bytes:
  `src/pewpew/sinks/base.py:82-91`.
- ws3, branch studio-ws3-server:
  - `src/pewpew/studio/app.py:183` and `:210`: 422 `{"issues"}`.
  - `src/pewpew/studio/app.py:334`: bind refusal.
  - `src/pewpew/studio/app.py:301-302`: idle resume.
  - `src/pewpew/studio/session.py:160` and `:246`: `hello` and `bound`.
- ws1, branch studio-ws1-rig:
  - `src/pewpew/rig/models.py:407` (`Pose`), `:458` (`RingGroup`), `:489-516` (`ArrayGroup`,
    `member` at 502), `:680-697` (`FixtureInstance`, `attachment_matrices` at 694).
  - `src/pewpew/rig/catalog.py:223-346` (`Catalog.to_json`).
  - `src/pewpew/rig/pose.py:161-175` (`anchor_frame`).
  - `src/pewpew/rig/examples/golden-rings.json`.
- three r186:
  - sRGB textures must be RGBA u8:
    https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLTextures.js#L2433-L2451
  - `SRGB8_ALPHA8` internal format:
    https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLTextures.js#L234
  - the `instanceMatrix` attribute in the ShaderMaterial prefix:
    https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLProgram.js#L607-L611
  - output encoding:
    https://github.com/mrdoob/three.js/blob/r186/src/renderers/shaders/ShaderChunk/colorspace_fragment.glsl.js#L1-L3
  - tone mapping gated on `toneMapped`:
    https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLPrograms.js#L179
  - ShaderMaterial needs `colorspace_fragment`: https://threejs.org/manual/pages/color-management.html
- drei v10.7.9 turns default controls off while dragging:
  https://github.com/pmndrs/drei/blob/v10.7.9/src/core/TransformControls.tsx#L89-L95
- three-stdlib v2.36.1 autoRotate rate:
  https://github.com/pmndrs/three-stdlib/blob/v2.36.1/src/controls/OrbitControls.ts#L491
- R3F Canvas `flat` and `dpr`: https://r3f.docs.pmnd.rs/api/canvas
- msw WebSocket API: https://mswjs.io/docs/api/ws
- Toolchain matched to the `web/package.json` of another of the maintainer's fly.io apps:
  pnpm 11.20.0, vitest ^4.1.11, msw ^2.15.0, Biome, Tailwind via `@tailwindcss/postcss`. Versions
  installed: three 0.186.1, @react-three/fiber 9.8.2, @react-three/drei 10.7.9, React 19.3.1,
  TypeScript 7.0.2, Vite 8.3.5, zustand 5.0.15, @tanstack/react-query 5.104.5, Playwright 1.64.1.
