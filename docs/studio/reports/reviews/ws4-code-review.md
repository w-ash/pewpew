# Code review of the ws4 studio web app (high effort)

- **Reviewer:** an independent agent (Opus), not the author. It ran the `code-review` skill at
  high effort, verified that pass's findings, and read the author's report only after its own
  review.
- **Target:** `git diff studio...studio-ws4-web -- web` at `18a63b8`, on 2026-10-22.
- **Verification:**
  - `pnpm test` (63 tests) and `pnpm e2e` (2 tests) pass.
  - Scratch Vitest cases ran against the real modules: Euler drift, undo after a save, an edit
    while a link loads, the 422 placeholder, the attachment axis, and a malformed import.
  - A Playwright probe measured the running mock app at 390×844, DPR 3.
  - Library behavior was checked in the installed sources and linked upstream.
- **Status:** these are the findings as reported. Two of the skill's findings are dropped: the
  `canExplode` group fallback, because ws1 always sends `group`, and the import-as-fork labeling,
  which is harmless. Its "120.04 shows as 12" example was wrong and is corrected in finding 6.

## Findings, most severe first

**1. A failed compile blanks the 3D view.** CONFIRMED
- **Where:** `web/src/api/queries.ts:29`, `web/src/App.tsx:150`, `:190`.
- **Defect:** `keepPreviousData` applies only while a query is `pending`. After a 422 the query
  is in `error` with `data` undefined, so `rig` becomes null and Stage unmounts the Rig.
  - The condition is `placeholderData !== undefined && data === undefined && status ===
    'pending'`: installed `@tanstack/query-core` 5.104.5 `src/queryObserver.ts:642-646`, and
    https://raw.githubusercontent.com/TanStack/query/main/packages/query-core/src/queryObserver.ts.
- **Scenario:**
  - A scratch QueryObserver test gave `status: error, data: undefined, isPlaceholderData: false`
    after a 422.
  - In the app, a typed intermediate value the server rejects (a ring count over the 200-fixture
    cap, an unresolved ref after Delete or Explode with explicit wiring, a bad import) empties the
    stage. The report panel says "The server sent no report", and the banner's "The view shows the
    last one that did" never renders.
  - The author's report (ws4-web.md:88-89, :156) says the last good rig stays on screen.
- **Fix:** keep the last successful `CompiledRig` in a ref or store, and render it while
  `compiled.isError`. Or drop `placeholderData` and track `lastGood` by hand.

**2. A malformed JSON import crashes the whole page.** CONFIRMED
- **Where:** `web/src/editor/arrangement.ts:335-345`, `web/src/panels/ArrangementPanel.tsx:88-96`,
  `:201-222`.
- **Defect:** `asArrangement` checks only `format` and `version`, so its output is trusted.
  `fixtures`/`groups` that are not arrays, or groups without `counts`, reach render code that
  calls `.map`, `.join` and `.some`. No error boundary sits above `App`.
- **Scenario:** importing `{"format":"pewpew.arrangement","version":1,"groups":[{"id":"g","preset":"array"}]}`
  passes `asArrangement`, then rendering `ArrangementPanel` throws (`g.counts.join`), which was
  reproduced in Vitest. React unmounts the root, so the page goes blank and the unsaved draft and
  undo history are lost. The server never sees the file. `"fixtures": {}` also passes.
- **Fix:** validate the shape before committing: arrays of objects with string `id`/`type`,
  `preset` in ring|array, and the fields each editor reads. Better, ask the server first (`POST
  /api/compile` and refuse on 422) and add a top-level error boundary.

**3. Touch targets are 38.5 px, and every input zooms the page on iOS.** CONFIRMED
- **Where:** `web/src/app.css:52` (`html, body { font-size: 14px }`), `web/src/panels/ui.tsx:39`,
  `:120`, `:148`, and every `min-h-11`/`h-11`.
- **Defect:** Tailwind 4 spacing is rem-based (`--spacing: 0.25rem`,
  `node_modules/tailwindcss/theme.css:325`). With a 14 px root, `min-h-11` is 38.5 px, not
  44 px. `text-sm` and `text-base` inputs render at 12.25 px and 14 px.
- **Scenario:**
  - The Playwright probe measured the tabs at 90×38.5, the buttons at about 53×38.5, and the
    inputs at 38.5 px tall with a 14 px font.
  - iOS Safari zooms the viewport on focus for inputs under 16 px
    (https://css-tricks.com/16px-or-larger-text-prevents-ios-form-zoom/), so every NumberField,
    Select and the name field zoom the phone layout.
  - The author's report (ws4-web.md:107) claims 44 px.
- **Fix:** put the 14 px size on `body` only and leave `html` at 16 px, or use `min-h-[44px]`. Give
  form controls `font-size: 16px` (`text-base` with a 16 px root).

**4. A GLB that fails to load once never retries until a reload.** CONFIRMED
- **Where:** `web/src/viewer/Rig.tsx:56`, `web/src/viewer/Stage.tsx:150-165`, `:216`,
  `web/src/viewer/RigBoundary.tsx:16`.
- **Defect:**
  - `useGLTF` goes through R3F `useLoader` and so through suspend-react. That caches a rejected
    load under `[GLTFLoader, ...urls]` and rethrows it on every later call: installed
    `suspend-react@0.1.3/index.js`, and
    https://raw.githubusercontent.com/pmndrs/suspend-react/main/src/index.ts
    (`.catch((error) => (entry.error = error))`, then `throw entry.error`).
  - Remounting `RigBoundary` by `modelKey` does not clear that cache.
- **Scenario:** one `/api/assembly/*.glb` gets a 502 during a deploy or a phone network blip. The
  stage shows "Fixture models did not load" for the rest of the session for that type set, even
  after the server recovers, and going back to the same set fails again at once.
- **Fix:** in `componentDidCatch`, or behind a Retry button, call `useGLTF.clear(urls)` before
  remounting.

**5. The share link can name content that is no longer on screen.** CONFIRMED
- **Where:** `web/src/store/doc.ts:52-53`, `web/src/panels/SharePanel.tsx:28-29`.
- **Defect:** `undo`/`redo` change the document without `forked()`. `save` sets
  `{mode:"shared", id}` after the await without checking that the document is still the one it
  saved.
- **Scenario:**
  - Edit, then Save (URL `/a/X`), then press ⌘Z. A scratch test confirmed that the share stays
    `shared:X` while `present` reverts.
  - The banner still says "Shared arrangement X, read-only", the URL stays `/a/X`, and Copy link
    hands out X. An edit made while the POST is in flight has the same effect.
- **Fix:** after the await, set `shared` only if `useDoc.getState().history.present ===
  arrangement`, and otherwise `fork` from the id. Apply `forked()` in undo and redo when
  `present` changes.

**6. The report shows wrong numbers for some values of 1000 or more.** CONFIRMED
- **Where:** `web/src/panels/ReportPanel.tsx:108`.
- **Defect:** `toPrecision(4).replace(/\.?0+$/, "")` strips integer zeros when the rounded
  string has no decimal point.
- **Scenario:** Node gives `1000.4 → "1"`, `2500.3 → "25"`, `999.96 → "1"` and
  `15000.2 → "1.500e+4"`. Values such as `120.04 → "120"` are correct. A total near 1 kW or 2.5 kVA
  in the report would read as 1 or 25.
- **Fix:** strip zeros only after a decimal point (`/(\.\d*?)0+$/` → `$1`, then a trailing `.`),
  or use `Intl.NumberFormat` with `maximumSignificantDigits: 4`.

**7. Edits made while a shared link loads are silently discarded.** CONFIRMED
- **Where:** `web/src/store/doc.ts:39-41`, `:54-55`; `web/src/panels/ArrangementPanel.tsx:66`;
  `web/src/App.tsx:63-96`.
- **Defect:** only the gizmo is read-only in `loading` mode. Panel buttons and shortcuts still
  commit, `forked()` leaves `loading` unchanged, and `load()` then replaces the history.
- **Scenario:** open `/a/<id>` on a slow phone connection. The panel lists the default golden
  rings. Tap Add > Ring and the edit commits, but compile is disabled, so nothing visible happens.
  The GET resolves and the edit is gone, which a scratch test reproduced.
- **Fix:** disable the Arrange panel and shortcuts while `share.mode === "loading"`, or show a
  loading state instead of the default arrangement.

**8. After 10 idle minutes the frames freeze while the page still says "live".** CONFIRMED
- **Where:** `web/src/session/client.ts:124-145`, `:172-183`;
  `web/src/viewer/Stage.tsx:350-357`. Server side: `src/pewpew/studio/app.py:34`, `:275`,
  `:301` on `studio-ws3-server`.
- **Defect:** the server pauses a session after 600 s with no inbound message and resumes it on
  the next message. The client sends nothing while someone only watches or orbits, and it has no
  stall detection.
- **Scenario:** someone shows a friend the rig on a phone and leaves it running. After 10 minutes
  the LEDs stop, the status still reads `live · N px` with a frozen `t`, and only an edit, a
  slider move or a tab switch restarts it.
- **Fix:** send `resume` on canvas pointer or keyboard activity once frames have stalled for more
  than about 1 s. Or show "paused, tap to resume" when no frame has arrived in 2 s while
  connected and visible.

**9. Each replaced InstancedMesh is never disposed.** CONFIRMED (missing call); PLAUSIBLE (impact)
- **Where:** `web/src/viewer/Rig.tsx:147-166`.
- **Defect:** every compile builds new meshes, and the cleanup disposes only the geometry.
  - three frees an InstancedMesh's `instanceMatrix` buffer only on the mesh's `dispose` event
    (https://raw.githubusercontent.com/mrdoob/three.js/r186/src/renderers/webgl/WebGLObjects.js,
    `onInstancedMeshDispose`).
  - R3F never disposes `<primitive>` objects
    (https://raw.githubusercontent.com/pmndrs/react-three-fiber/master/packages/fiber/src/core/reconciler.tsx,
    "Never dispose of primitives").
- **Scenario:** one `instanceMatrix` GL buffer per batch×part per edit stays in `WebGLAttributes`
  until JS garbage collection reclaims it (inference), not on change.
- **Fix:** `useEffect(() => () => { mesh.geometry.dispose(); mesh.dispose(); }, [mesh])`.

**10. Every keystroke compiles, and every success rebinds the session.** CONFIRMED (efficiency)
- **Where:** `web/src/panels/ui.tsx:112-118`, `web/src/api/queries.ts:25-34`,
  `web/src/App.tsx:118-121`.
- **Defect:**
  - NumberField and the name input commit each parsable keystroke, and the compile query is keyed
    on the raw arrangement with no debounce.
  - Each successful compile calls `session.bind`, so the server recompiles and rebinds even for a
    name-only change.
  - In-flight compiles are cancelled when the key changes, but completed ones are cached for
    5 minutes.
- **Scenario:**
  - Typing a 20-character name sends up to 20 compiles and up to 20 rebinds (250 ms debounce).
  - Typing "36" into ring count compiles count 3 first.
  - With finding 1, an intermediate the server rejects blanks the stage mid-typing.
- **Fix:** debounce the compile key by about 200 ms, and skip `bind` when only `name` changed.

**11. Copy link reports "Copied" when nothing was copied.** CONFIRMED (code reading)
- **Where:** `web/src/panels/SharePanel.tsx:80`.
- **Defect:** `await navigator.clipboard?.writeText(link)` resolves to `undefined` when the API
  is absent, and a rejection goes unhandled.
- **Scenario:** on a phone testing against `http://<lan-ip>:5173`, which is not a secure context,
  the clipboard API is undefined but the button says "Copied". With permission denied, there is
  no feedback.
- **Fix:** check `navigator.clipboard`, catch the rejection, and fall back to selecting the input.

## Checked and found sound

- **Color.**
  - The texture is an sRGB-tagged RGBA8 `DataTexture`, with Linear min and mag filters,
    clamp-to-edge, no mipmaps, and `needsUpdate` once per new frame.
  - The ShaderMaterial includes `colorspace_fragment`, sets `toneMapped:false`, and the Canvas is
    `flat`, not `linear`, so output is sRGB. Accent and housing colors are linear.
  - `e2e/color.spec.ts` reads the bytes back: exact for `pixel_nearest`, ±1 for `pixels`.
- **Texture rows.**
  - Row f is `rig.fixtures[f]`, filled from `pixel_start`/`pixel_count` (`ledTexture.ts:56-75`),
    and `aRow = f` for hosts and attachments.
  - `u = (y − y0)/span`, with `x = clamp(u·n, 0.5, n − 0.5)` sampled at `x/width` and
    `(row + 0.5)/height`. That puts texel centers at (i+0.5)/n and never bleeds into the padding
    or into neighboring rows. `pixel_axis` matches ws1b's `y0 = −span/2`.
- **`data_in` and attachments.**
  - `data_in` is carried entirely by the server matrix (Rz 180°), so the client needs nothing.
  - An attachment's host-local y is row 1 of `M_fixture⁻¹ · attachment_matrix`. The scratch test
    put an end_a cone at host y −0.5…−0.6, which clamps to texel 0.
  - Free-fixture flip is exactly `q·(0,0,1,0)` with the ends swapped. A ring toggles `data_in`.
- **Matrices.** Server matrices are column-major (`to_three`, ravel order F) and load straight
  into `instanceMatrix` and `Matrix4.fromArray`. The drag preview premultiplies a world-space
  delta.
- **Frame path.**
  - No React state is set per frame: `t` is throttled to 4 Hz, `power` arrives at 2 Hz, and
    status and params go out only on change (ws3 `transport.py`).
  - `parseFrame` drops lengths other than 8 + 3·boundN, and Rig also checks `layout.n`.
  - A new layout key reallocates the texture and its materials and disposes the old texture.
- **Protocol.**
  - Every contracts.md message is parsed and shape-checked.
  - `bind` is sent on open and on reconnect, along with the chosen pattern.
  - `pause` is sent on hidden and on open while hidden; `resume` on shown.
  - A `refused` for a knob snaps its slider back to the accepted value.
  - The URL is `wss` over https, and the backoff goes from 1 s to 10 s.
- **Editor.**
  - quat→YPR→quat drift was at most 2.6e-13 after 100 round trips on 2,000 random rotations,
    always with w ≥ 0.
  - Snaps are 1 cm and 1°, and committed positions round to 0.1 mm.
  - Undo coalesces per field within 800 ms, makes one step per drag, and clears on undo.
  - The browser never expands presets, places pixels, wires or computes power. Explode uses
    server matrices, and the JS ring expansion is mock-only and tree-shaken out of production.
- **Security.** There are no `innerHTML`, `dangerouslySetInnerHTML` or eval sinks. Names,
  patterns and issues render as text, the download filename is sanitized, and share ids are
  regex-checked.
- **Leaks.** Texture, material and geometry clones are disposed; the socket, the
  visibilitychange, keydown and OrbitControls listeners, and the timers are all removed on
  unmount.
- **Mobile.**
  - The Canvas `dpr={[1,2]}` gave a 720 px backing store for a 360 px canvas at DPR 3.
  - drei TransformControls disables the default OrbitControls while dragging, and three's
    pointer-down runs hover first, so a finger can grab an axis. This is not tested on a device.
