# ADR-020: Preview transport — adopt `websockets` (sync server)

Status: Accepted (2026-08-20)

## Context

The Phase-1 preview sink (§8) streams frames to a browser: map positions
once, then compact per-frame color buffers, with an HTML page served from
the same port. Until this decision the engine had a single runtime
dependency (numpy), and §9's ADOPT table named no websocket or HTTP
library — the transport choice was left open. The engine is threaded, not
asyncio: `PacedLoop` owns the loop thread, every sink runs behind a
`SinkDriver` worker (ADR-010), and there is no event loop anywhere to
attach an async server to.

## Decision

Adopt the **`websockets`** library (BSD-3-Clause) as a main runtime
dependency and build `PreviewSink` on **`websockets.sync.server`**, its
thread-per-connection server:

- one port serves both the page (any plain HTTP GET answered from the
  `process_request` hook) and the websocket upgrade;
- each browser connection gets its own handler thread and its own
  `SinkDriver`, so per-client backpressure stays newest-wins and a
  stalled tab cannot touch the render loop or other clients;
- `compression=None` — frames are small, fresh every tick, and latency
  beats wire size on localhost.

## Consequences

- The numpy-only dependency posture ends; the engine's runtime deps are
  now numpy + websockets. The floor stays aligned: websockets 17.x
  requires Python >=3.11, same as pewpew.
- RFC 6455 edge cases (close handshake, fragmentation, ping/pong timing,
  masking validation) are owned by the reference implementation, not by
  us; its C extension covers the hot path.
- The sync server is thread-per-connection: fine for a dev preview's
  handful of tabs, not a design for hundreds of clients. If the preview
  ever needs that, the asyncio implementation in the same package is the
  escape hatch — not a new dependency.
- The hot-reload story's file watcher stays `watchfiles` per §9; this ADR
  adds no HTTP framework, template engine, or frontend build step. The
  served page remains one hand-written zero-dependency HTML file.
  *(Superseded 2026-11-04: the page has a build step, run only when
  building; see that amendment.)*

## Evidence

- [S521] `websockets` 17.0.1 (2026-07-31): the reference Python
  implementation of RFC 6455/7692; `websockets.sync.server` is a
  threading server with a `process_request` HTTP hook; BSD-3-Clause;
  Python >=3.11; C-accelerated. Actively maintained, releases current.
- [S522] RFC 6455: sizes the hand-roll alternative — the server-side
  subset pewpew needs is small, but the close-handshake and fragmentation
  edges are where hand-rolled implementations rot.
- [S508] LedFx's browser pixel streaming (4096-px frontend cap, throttle
  slider): the precedent for the stream-budget shape the sink implements,
  and proof a websocket frame stream to a browser is the working pattern
  in this space.

## Rejected alternatives

- **Hand-rolled stdlib RFC 6455 subset** — ~200 lines buys the handshake
  and unmasked server→client frames, and keeps the numpy-only posture,
  but makes pewpew the maintainer of protocol edge cases the reference
  implementation already owns [S522][S521].
- **aiohttp / an asyncio stack** — drags an event loop into a
  deliberately threaded engine (ADR-010's loop owns its thread; sinks are
  worker threads); the sync server fits the existing model with zero
  impedance [S521].
- **Optional-extra packaging (`pewpew[preview]`)** — the preview is the
  §8 no-hardware dev path, not an optional nicety; an extra would make
  the first-run experience `ImportError` [S508].
- **WLED-style websocket-as-control-channel only** — ADR-004 notes
  Pixelblaze's websocket is a control channel, not a frame transport;
  the preview's job is precisely frame transport, so that shape does not
  apply here.

## Amendment (2026-11-04) — a built page: Vite, React, TypeScript, Ark UI

The page was one hand-written file of about 1,250 lines
(`src/pewpew/sinks/web/index.html`) that drew one range slider per param.
ADR-006's 2026-11-04 amendment gives params five kinds with parts, and the
page must render each pattern's controls from those records, on a phone
and on a desktop. Backlog: `docs/backlog/v0.2.x.md`, story "Typed params
and a schema-driven control page".

Status stays **Accepted**; the transport above is unchanged.

### Decision

- **A build step, run only when building.** The page source lives in
  `web/` (React, TypeScript, Ark UI) and Vite builds it into one inlined
  `src/pewpew/sinks/web/index.html`, which is committed. Vite is a dev
  server plus a build command that bundles with Rolldown and needs Node
  20.19+ or 22.12+ [S1367]; vite-plugin-singlefile inlines all JavaScript
  and CSS into the one HTML file [S1369]. **The runtime is unchanged:** the
  engine serves one file from the package, with no Node, no internet and
  no new Python dependency.
- **The toolchain**: @vitejs/plugin-react with the React Compiler
  (babel-plugin-react-compiler [S1366]) through @rolldown/plugin-babel;
  TypeScript with `isolatedModules`, checked by `tsc --noEmit`; vitest in
  browser mode on Chromium and WebKit through Playwright [S1370]; pnpm.
  `web/package.json` pins each package exactly. On 2026-11-05 each pin was
  MIT or Apache-2.0 by its npm registry record [S1391] (ADR-012); recheck
  the license of a new version.
- **One file, no lazy chunks.** No dynamic `import()` and no `public/`
  folder, since the plugin leaves both outside the HTML [S1369]. System
  fonts only. *(Superseded 2026-11-06: two subset fonts, inlined; see that
  amendment.)*
- **The committed page cannot go stale silently.** `tools/webhash.py`
  hashes the `web/` sources, the lockfile and the config; the build stamps
  the hash into `<meta name="pewpew-build">`, and `tests/test_page_build.py`
  recomputes it. `just web` (install with a frozen lockfile, check, test,
  build) is part of `just check`.
- **Dev proxy.** In development Vite proxies `/ws` (`ws`, `changeOrigin`,
  `rewriteWsOrigin`) and `/plan` to a running engine [S1368]. The dev
  server binds `127.0.0.1` only (`web/vite.config.ts`), so no other
  machine reaches it.
- **Ark UI for every control.** Ark is headless: behavior, ARIA and
  keyboard handling come from the library, the look from pewpew's own CSS
  through `data-scope`, `data-part` and `data-state` [S1363]. It sits on
  the MIT Zag.js state machines [S1364]. It has every control the kinds
  need: Slider and AngleSlider, an inline ColorPicker with an `hsba`
  format, SegmentGroup, Switch, Select, and Field for label, help and
  error; and the layout parts: Accordion with several items open, a
  non-modal Drawer, and Splitter [S1363][S1364]. *(Superseded 2026-11-05:
  native elements replace Select, Switch and Toggle, and the Drawer is
  gone; see that amendment.)*
- **Layers in `web/src`, depending inward.** `domain/` is pure TypeScript
  with no React, DOM or socket: the param record types, one `KindDef`
  per kind (decode, read, normalize, equal, format), the only color math
  (linear HSV to display RGB with the hello's `display_gamma`), and the aura, health
  and room selectors. `infra/` holds the wire protocol, the socket
  (reconnect, per-param set coalescing) and a store read through
  `useSyncExternalStore` [S1365]. `ui/` holds the Ark controls per kind and
  widget, a registry from kind to control, and the panels. `app/` composes
  them. `ui` uses `domain` and `infra`; `domain` imports nothing from
  either. Each kind is defined once in Python (ADR-006) and once in
  `domain/`.
- **One page, two input modes.** The operator and editor views go; effect
  settings are always visible, and layout editing is a separate mode.
  The view flag becomes the unattended-run flag, now `--unattended`
  (keep-awake and the 5 s watchdog). Touch or mouse behavior follows the
  `pointer` and `hover` media queries, which describe the primary input
  [S1380][S1381], not the screen width; a param
  field adapts by a container query [S1382]. The viewport meta adds
  `viewport-fit=cover`, so safe-area insets apply, and
  `interactive-widget=resizes-content` [S1383].
- **Accessibility floors.** Targets are at least 24 px, the WCAG 2.2 AA
  minimum [S1374], and 44 px under `pointer: coarse` [S1375][S1271]. Every
  drag also works by taps or a number input [S1376]. Sliders follow the
  ARIA slider pattern, with `aria-valuetext` where the number alone says
  too little (for example "hold" at 0) [S1377]. No state is shown by color
  alone [S1303].
- **No Wake Lock.** It needs a secure context [S1378], and a phone loading
  `http://<laptop-ip>` is not one [S1379] (inference, as for service
  workers [S1272]). The page asks for Auto-Lock set to Never instead.
- **Serving.** The engine caches the page instead of reading it on each
  request, and gzips it when `Accept-Encoding` allows. The hello drops
  `view` and adds `display_gamma`.

### Consequences

- Building the page needs Node, pnpm and the Playwright browsers; running
  pewpew does not. CI installs them for `just check`.
- The committed page is generated: review its source in `web/`, not its
  diff. The build hash catches a source change without a rebuild.
- The built file carries bundled MIT and Apache-2.0 code, so the build
  keeps those licenses' notices in the output (inference from the license
  terms): Vite's `build.license` lists each bundled package's license, and
  the build moves that list into the page as a comment
  (`web/vite.config.ts`).
- A spike measures the gzipped size first; `tests/test_page_build.py`
  bounds the page at that size plus 15%.
- Zag's AngleSlider clamps values to 0..359 [S1364], while ADR-006's
  `widget="angle"` floats span 0..360 and wrap, so the angle control maps
  360 to 0 itself (`web/src/ui/params/controls/angle.tsx`). *(Since
  2026-11-05 the control turns degrees into dial angles, `(90 − deg) mod
  360`, and the float kind wraps the value that comes back into 0..360,
  `web/src/domain/params/schema.ts`.)*
- The dev proxy weakens the engine's `Origin` check while it runs. Vite
  checks no websocket origin before proxying, and `rewriteWsOrigin` "can
  leave the proxying open to CSRF attacks" [S1368]: any site open in the
  developer's browser can reach `localhost` and drive the engine through
  the proxy. So the proxy refuses an upgrade whose `Origin` is not the dev
  server's own (`web/dev-origin.ts`).

### Evidence

- [S1363][S1364] Ark UI and Zag.js: headless, MIT, and every control and
  layout part the kinds need, with ARIA patterns built in.
- [S1367][S1369] Vite and vite-plugin-singlefile: a build-only toolchain
  whose output is one self-contained HTML file.
- [S1365][S1366] React: an external-store hook for a socket-fed store, and
  a stable compiler for memoization.
- [S1368][S1370] Vite's websocket proxy for development, and browser-mode
  tests on Chromium and WebKit.
- [S1380][S1381][S1382][S1383] Input mode from the primary pointer, layout
  from the container, and safe-area and keyboard-resize viewport settings.
- [S1374][S1375][S1376][S1377][S1271][S1303] WCAG 2.2 and the ARIA slider
  pattern: the target-size, dragging and value-text floors.
- [S1378][S1379][S1272] Wake Lock and service workers need a secure
  context the LAN page does not have.

### Rejected alternatives

- **Keep the hand-written page.** Every control would be hand-built to the
  ARIA patterns [S1377], including an inline color picker, an angle slider,
  drawers and a splitter, which Ark already ships with their keyboard and
  ARIA behavior [S1363]. The old page also had to group colors by a name
  pattern, which ADR-006's 2026-11-04 amendment removes.
- **Web Awesome without a build.** Its color picker opens only as a
  dropdown from a button, and it has no angle slider, knob or dial [S1371].
  Effect settings must stay visible, and `direction` is an angle.
- **React Aria.** Unstyled and thorough, with a full color picker [S1372],
  but `react-aria-components` has no Splitter and no general angle slider
  at the pinned commit [S1372]. Ark has both [S1363].
- **Tweakpane.** A compact parameter pane with number, color and point
  bindings, but its last release is 4.0.5 of 2024-11-03 and its docs say
  nothing about touch [S1373][S1386].

## Amendment (2026-11-05) — native elements where they match Ark

The 2026-11-04 amendment took Ark UI for every control. The page ran its
Drawer with the modal behaviour, focus trap, scroll lock and outside
dismiss all turned off. Code: `web/src/`.

### Decision

- **Ark stays the default.** A native element replaces an Ark part only
  when it gives the same accessibility and behaviour on phone Chromium,
  phone WebKit and desktop, with no hand-written focus, keyboard or
  gesture logic, checked live.
- **Swapped**: Select → `<select>` (`web/src/ui/common/Select.tsx`);
  Switch → `<input type=checkbox role=switch>`, the APG's switch on a
  checkbox [S1393] (`web/src/ui/params/controls/bool.tsx`); Toggle →
  `<button aria-pressed>`, the APG's toggle button [S1394].
- **Removed**: the Drawer. The health panel, and on a phone the layout
  tools, open in the side slot in place of the editor, so no panel covers
  the deck; on a wide screen the layout tools sit beside the canvas
  (`web/src/app/App.tsx`).
- **Kept**: Accordion, since Ark moves focus between headers with the
  arrow keys, Home and End [S1364] and `<details>` has no such keys
  (inference); Dialog, since Ark traps focus and closes on an outside tap
  [S1364] while the native outside close, `<dialog closedby>`, has no
  Safari support [S1395]; Splitter, which has no native element;
  ToggleGroup, for its roving focus [S1364]; and Ark's hotkeys. Slider,
  AngleSlider, ColorPicker, NumberInput, SegmentGroup and Field are
  unchanged.
- **Layout**: the split layout follows `WIDE`, min-width 900px or
  landscape with min-height 300px (`web/src/ui/common/useMedia.ts`), so a
  phone on its side gets it. Target sizes follow the pointer, not `WIDE`
  (`web/src/ui/theme.css`).
- **Single-key shortcuts can be turned off** from the shortcut list, as
  WCAG 2.1.4 requires of a shortcut on a character key [S1392]; the
  choice is kept on the device. Esc is not a character key and stays on
  (`web/src/ui/common/shortcuts.ts`).
- **A two-tap confirm ignores a second tap less than 0.4 s after the
  first**, so a bounce or a double tap cannot black out the room; a
  second tap 0.4–3 s after the first fires (`web/src/ui/common/useArm.ts`).
  The 0.4 s is an engineering choice, not a measured limit.
- **React Compiler runs with `panicThreshold: all_errors`**
  (`web/vite.config.ts`), so a component the compiler cannot optimise
  fails the build.

### Consequences

- A phone opens its own picker for a `<select>` (inference, untested on
  every phone).
- The bottom sheet's swipe to dismiss goes with the Drawer.

### Evidence

- [S1393][S1394] The APG switch and toggle-button patterns: a checkbox
  with role `switch`, and a button with `aria-pressed`, carry the state.
- [S1364] Zag.js at the pin: the accordion's arrow, Home and End keys, the
  dialog's focus trap and outside close, and the toggle group's roving
  focus.
- [S1395] `<dialog closedby>`: no Safari support.
- [S1392] WCAG 2.1.4: a way to turn off character-key shortcuts.

### Rejected alternatives

- **Ark for every control**, as on 2026-11-04: the Drawer carried a modal
  machine with every modal behaviour turned off, and Select, Switch and
  Toggle repeat what the native elements already expose [S1393][S1394].
- **Native elements for every part**: `<details>` loses the accordion's
  arrow keys and a native dialog loses the outside close on Safari
  [S1364][S1395], and no native element splits a panel.

## Amendment (2026-11-05) — capabilities for outside clients, and the look and ack messages

ADR-023 lets an agent apply a look to a running engine over the preview
websocket. An engine built before that change ignores a message type it
does not know: `AuraControl.request` returns nothing for it
(`src/pewpew/aura/control.py`), so a `look` sent to an old engine would
vanish with no answer. Today `refused` echoes the `name` only for a `set`
(`src/pewpew/sinks/preview.py`), so a client cannot match a refusal to
any other request. Backlog: `docs/backlog/v0.3.x.md`.

Status stays **Accepted**; the transport above is unchanged.

### Decision

- **`hello` gains `capabilities`**, a list of names such as `["look"]`.
  **It exists only for clients outside the package** (the MCP server,
  `observe`, `push` and other agents). **The bundled page never branches on
  it**: it ships with the engine, and the wire still changes in place with
  no version negotiation (ADR-006, 2026-11-04 amendment). A client that
  finds a name missing reports that the engine lacks it, as an OSCQuery
  client assumes a feature absent from `HOST_INFO.EXTENSIONS` is
  unsupported [S1350].
- **New inbound `{"type": "look", "id", "look", "fade"}`** applies an
  unsaved layered look (looks v4, ADR-006 amendment "layered paths")
  through the crossfader. The engine accepts it only when started with
  `run --accept-looks`, and refuses that flag with `--unattended`;
  `capabilities` lists `look` only then, which is also the opt-in ADR-018's
  amendment requires before any tier-1 write.
- **No file path crosses the socket inbound either.** A look's pattern may
  be named by path in a looks file (`src/pewpew/aura/book.py`), and a path
  is never sent out. A message that names a pattern (a `look`'s `pattern`
  node, a layer added from the catalog) takes a pick name only; a path is
  refused with the message's `id`, `name` set to the field's address
  (`layers.<lid>.<nid>.pattern`), and a reason that names no file
  (`errors.scrub`).
  *(Since 2026-11-07 no message names a pattern; see ADR-025.)*
- **New outbound `{"type": "ack", "id", "control"}`** answers a message
  that carries an `id` and that the engine ran, and **`refused` always
  carries `name` and `id`**, each null when it does not apply, so a client
  matches each answer to its request on one socket, as a JSON-RPC response
  repeats its request's `id` [S1465]. A message with an `id` and a type
  the engine does not know is refused with that `id`, in
  `errors.unknown`'s wording (`unknown control 'sett'; controls: set,
  pick, ...`): `AuraControl.request` returns None for an accepted message
  and for an unknown type alike, so without this a typo would be acked. A
  message with no `id` is answered as today, and an unknown type without
  one stays silent.
- **`set` takes the paths** of ADR-006's amendment "layered paths", and
  `aura` carries the stack (`aura.stack`, ADR-021).

### Consequences

- `web/src/infra/wire/protocol.ts` and `tests/goldens/wire.json` change in
  the same commit as the engine, as for any wire change; `refused` gains
  `id` and an always-present `name`, so the golden's refusals change.
- An agent learns from the hello whether `push` can work before it sends
  anything, and gets a definite `ack` or `refused` for each look.
- Tests: a message with an `id` and an unknown type is refused with its
  `id`, never acked; an applied look is acked with its `id`; a look whose
  `pattern` is `"/tmp/x.py"` is refused with the field's address and the
  `id`; a bad look is refused with its path and `id`.

### Evidence

- [S1350] OSCQuery: a server lists its optional features in
  `HOST_INFO.EXTENSIONS`, and a client treats an unlisted one as
  unsupported.
- [S1450] MCP 2026-07-28: `server/discover` advertises a server's
  capabilities before any other request.
- [S1465] JSON-RPC 2.0: a response's `id` "MUST be the same as the value of
  the id member in the Request Object".

### Rejected alternatives

- **Version negotiation, or a `protocol` number in the hello.** ADR-006's
  clean-break rule keeps the wire changing in place, and the bundled page
  always matches its engine.
- **Feature detection by trial.** An old engine answers an unknown message
  with nothing, so silence would have to mean "unsupported" after a
  timeout, which is also what a slow engine looks like.
- **The page reading `capabilities`.** It would grow branches for engine
  builds it never meets, the version negotiation the clean-break rule
  removed.
- **Accepting a path in an inbound look.** The port is unauthenticated
  (ADR-006 amendment "trust model"), and loading a pattern file runs it,
  so a path would let any client that reaches the port run a Python file
  from the engine machine's disk; a pick name resolves only to a pattern
  the engine already offers.

## Amendment (2026-11-06) — inline subset fonts: Martian Grotesk and Martian Mono

The 2026-11-04 amendment kept the page to system fonts. The maintainer chose
Martian Grotesk and Martian Mono for the control page (RA-27b, Decisions item 4),
tuned per RA-27c §3.1, whose type roles they fill.

Status stays **Accepted**; the transport above is unchanged.

### Decision

- **Two subset fonts, inlined.** `tools/fonts.py` (`just fonts`) downloads
  Martian Grotesk at evilmartians/grotesk@0b66b31 and Martian Mono v1.1.0,
  checks each file's sha256 and each licence's git blob id against its pin
  [S1700][S1701], and writes `web/src/ui/fonts/`: Grotesk instanced to wght
  400–600 at wdth 100 (13,232 B woff2), Mono to wght 400 at wdth 87.5
  (5,056 B), both unhinted and subset to the characters the page uses, and
  `OFL.txt`. The three files are committed; the tool runs only when the
  fonts change, with fontTools and brotli for that run alone, so pewpew
  gains no dependency. Two runs give byte-identical files.
- **Inline, as everything else is.** `web/src/ui/theme.css` declares the
  faces with `url(./fonts/*.woff2)`, which vite-plugin-singlefile turns into
  data URIs like every other asset [S1369]; the page stays one file with no
  config change. Mono is declared twice: as itself, and as "Martian Figures"
  with a `unicode-range` of digits and value signs, so a live number gets
  fixed-width digits and Grotesk's letters.
- **No render wait.** `font-display: swap`; the fallback stack is the system
  sans. A cold load shifts nothing for the fonts (measured on the build:
  0.0000 for the swap; the desktop's 0.078 comes from the deck mounting when
  the aura message arrives, as before).
- **The licence travels with the page.** `inlineLicenses()`
  (`web/vite.config.ts`) appends `OFL.txt` (both fonts' copyright lines and
  the SIL Open Font License) to the page's licence comment. Neither font
  declares a Reserved Font Name, so the subsets keep their names
  [S1700][S1701].
- **The budget.** `GZIP_BUDGET` in `tests/test_page_build.py` is the real
  build with the fonts, their notice and the icon set (224,888 B gzipped,
  from 199,921 before) plus about 2.5%: 230,500 B, up from 217,855. A test asserts that every
  `url(` in the built page is a data URI.

### Consequences

- The page grows by about 22 KB gzipped for the fonts and their notice.
- Characters neither subset holds fall back to the system sans one glyph at
  a time; the page draws its own signs (✕ ↻ ▾ ▲ ⋯ ● and the rest) as inline
  SVG icons (`web/src/ui/common/Icon.tsx`), and `domain/` returns a sign as
  data, never as a glyph in a string.
- Martian runs wider than the system sans, so on a phone fewer look names
  fit whole (RA-27c §3.1).

### Evidence

- [S1700][S1701] The fonts' repositories at their pins: OFL-1.1, with no
  Reserved Font Name; the variable sources and their axes.
- [S1369] vite-plugin-singlefile: every asset the build emits is inlined.

### Rejected alternatives

- **The engine serves `/fonts/*.woff2`.** It saves about 2 KB a load, but
  breaks "one file, no lazy chunks": the engine answers any GET with the
  page, so it needs a route, package data and a dev proxy, and stopping the
  plugin from inlining [S1369].
- **System fonts only,** as on 2026-11-04: the maintainer chose Martian (RA-27b,
  Decisions item 4).
- **The Grotesk v1.0.0 release binaries:** they carry no licence string and
  point to a commercial EULA; the OFL sources on `main` at the pin do not
  [S1700].
