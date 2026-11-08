# ADR-024: Hosted studio — server-side rendering, FastAPI, public gallery-only trust model

Status: Accepted (2026-10-22)

Numbered ADR-021 in the studio's own history; ADR-021 is layer compositing.

## Context

The maintainer wants to arrange LED fixtures in 3D, run real pewpew effects on the
arrangement, and share arrangements with friends from a public fly.io app,
not a Claude artifact (`docs/studio/plan.md`, "Context"). That adds a
deployment the research tree did not cover. ADR-020 built the laptop preview
on a thread-per-connection `websockets` server and named the asyncio
implementation as its escape hatch. Architecture §5 sets an unauthenticated
trusted-LAN trust model, which does not hold on the public internet. The
studio's data model is in ADR-007 (amended 2026-10-22); its full design is in
`docs/studio/domain-model.md` and `docs/studio/contracts.md`.

## Decision

- **Rendering: per-visitor, server-side, the real engine.** Each session
  owns one `Renderer` on its own thread (30 fps). Frames cross into asyncio
  with `loop.call_soon_threadsafe` into a one-slot mailbox that keeps only
  the newest frame, so a slow client drops frames and never queues them.
  The page draws the display-ready bytes unchanged. There is no JavaScript
  copy of any pattern.
  *(Since 2026-11-07 each session runs the aura's pipeline over a look; see ADR-025.)*
- **Server: FastAPI + uvicorn** for the studio (`python -m pewpew studio`),
  matching the maintainer's other fly.io apps (`docs/studio/plan.md`,
  "Decisions"). This sits beside ADR-020: the sync `websockets` server stays
  for the laptop `run --preview` page, unchanged. ADR-020's asyncio escape
  hatch is used in spirit (an asyncio stack for public traffic) but through
  FastAPI, not the `websockets` asyncio server, because the studio also needs
  request-body REST routes [S769][S770][S768].
- **Trust model: public, unauthenticated, gallery patterns only.**
  - Visitors can run only patterns on a server-side gallery allowlist; no
    user code executes and no hardware sink is reachable.
    *(Superseded 2026-11-07: visitors run JSON looks over the built-in op
    catalog; see ADR-025.)*
  - Limits apply per `Fly-Client-IP` [S763]: websockets per IP, inbound
    message size, saves per minute, and a total storage cap.
    *(Since 2026-11-08 "saves" are shares published.)* The numbers are
    starting values set by the plan (inference, no sourced standard); they
    live in config, not in this ADR.
  - Share links are immutable, content-addressed snapshots. The id is the
    first 128 bits of SHA-256 over the canonical JSON, base64url-encoded
    (22 characters), above the 64-bit minimum for identifiers [S780].
    Opening a link lets a visitor edit and save a copy; nothing is
    overwritten. A link is a capability to public data, not a secret.
    *(Superseded 2026-11-08: a visitor no longer edits or saves a layout;
    a link opens a shared layout read-only, with its looks, in the
    Gallery.)*
  - This amends architecture §5's trust model **for this deployment only**.
    The LAN engine, preview and mesh tiers keep §5 as written. Tier 2 stays
    read-only for agents (CLAUDE.md T-7); the studio has no fleet access.
- **Hosting: fly.io, one machine, with Neon Postgres**, as the sister
  projects deploy. Rows live in Neon, not on a Fly volume or Tigris
  [S781][S773]. SQLite serves local runs and tests. The app must not rely on
  Fly's autostop to end idle sessions, because how an open websocket counts
  as load is undocumented [S782]; the server pauses a session after 10
  minutes without a message and the page stops frames while its tab is
  hidden, because egress is billed per GB [S764].
- **Frontend: React 19 + @react-three/fiber 9 + three r186 with
  `WebGLRenderer`** [S523][S526]. LED colors reach the GPU as an sRGB-tagged
  RGBA `DataTexture` read by a custom `ShaderMaterial` [S525]; streamed
  colors are written imperatively, not through React state.
  *(Since 2026-11-08 the Gallery serves the Console's build, not a studio
  page.)*
- **Geometry: server-built GLB via manifold3d, one implementation.** The
  server builds each fixture type's mesh with `manifold3d` into a
  deterministic GLB served at a content-hash URL; each part node carries
  `glow` and `gain` in `extras` [S775][S527]. The browser never expands
  presets, places pixels, wires, or does power arithmetic.

## Consequences

- The runtime dependency posture grows. pydantic joins the core for the file
  format [S771]. `pewpew[studio]` adds FastAPI, uvicorn, psycopg and
  manifold3d [S769][S770][S772][S775]. psycopg is LGPL-3.0: imported
  unmodified from the optional extra, never vendored (inference, consistent
  with ADR-012).
- CPU is the scaling limit: one render thread per visitor on one machine.
  The per-IP session cap bounds it; there is no horizontal scale plan, and a
  second machine would need a session-affinity decision this ADR does not
  make.
- Egress is the main variable cost, at $0.02/GB in North America and Europe
  [S764]. The plan's figure of about 90 KB at 30 fps per viewer-hour is an
  inference in the A1 report; frame size follows from 3 bytes per pixel.
- A proxy reset cuts a client that stalls for 30 s [S767]. Dropping frames
  rather than queueing is the design response, not an optimization.
- The studio is separable: deleting `src/pewpew/studio/` and `web/` leaves
  the engine and ADR-020 preview untouched.
- Share links store a `catalog_digest`, so an old link can report when a
  fixture's dimensions have since changed.

## Evidence

- [S769][S770] FastAPI provides websocket endpoints and request-body routes
  on an ASGI server; the same stack runs the maintainer's other fly.io apps.
- [S768][S521] The `websockets` docs say "Don't scale with threads. Scale
  only with processes." and call serving HTTP "out of scope". Checked in
  `src/websockets/http11.py` at 17.0.1 and 17.3 (read 2026-10-22): the
  request parser raises on any `Transfer-Encoding` and on a non-zero
  `Content-Length`, so `process_request` cannot receive a POST body.
- [S781][S782][S763][S764][S767] Fly's configuration, autostop, client-IP
  header, pricing and 30 s stalled-stream reset define the hosting
  constraints: one machine, per-IP keys, frame dropping, and an app-level
  idle timeout.
- [S773] Neon is managed Postgres, so share rows survive the machine.
- [S523][S524][S525][S526] three r186, R3F 9.8.2 (peers `react >=19 <19.4`)
  and the color-management rules for passing display-ready bytes through a
  `ShaderMaterial`.
- [S775][S527] manifold3d 3.5.4 (Apache-2.0) does the CSG; GLB `extras`
  carry the per-part glow metadata.
- [S780] OWASP's 64-bit entropy floor for identifiers; the share id has 128
  bits.
- Project precedent: the hand-written JS pattern ports in the old
  `preview/index.html` were retired because mirrors drift, in favour of the
  engine-backed sink (`docs/backlog/v0.2.x.md:193`).

## Rejected alternatives

- **Pyodide in the browser.** It would remove the per-visitor server CPU,
  but Pyodide 314.0.7 needs about 6 MB over the wire for the interpreter and
  standard library alone (3.44 MB brotli wasm, 9.6 MB uncompressed, + 2.55 MB stdlib zip,
  measured 2026-10-22), plus about 2.9 MB for numpy [S779][S776]. The roadmap cites
  4-5 s initialisation and 3x-5x slower than native Python (stale text, a
  rough bound) [S778]. Phone benchmarks were not found. (Inference) the
  engine's threaded pacing and `SinkDriver` workers would need a different
  runtime path there, so the page would not execute the same code the golden
  tests pin. Server rendering keeps one engine [S777].
- **Claude artifacts or static hosting.** The maintainer ruled out artifacts
  (`docs/studio/plan.md`, "Context"). Static hosting cannot run the Python
  engine, save a share link, or enforce limits, which leaves a JS port of
  the patterns (rejected below) or Pyodide (rejected above).
- **The sync `websockets` server for public traffic.** The docs advise
  against scaling it with threads [S768], and it cannot read a POST body,
  so saves would have to ride the socket as messages [S521]. It stays for
  the laptop preview where a handful of tabs is the design (ADR-020).
- **Geometry or patterns mirrored in JavaScript.** Two implementations drift
  silently: the retired playground ports could not express `setup()` or
  `self.buffer()` and differed from NumPy in `%` semantics
  (`docs/backlog/v0.2.x.md:193`). A single server implementation, tested by
  `uv run pytest`, keeps the golden frames meaningful.
- **A Fly volume or Tigris for share storage.** A volume attaches to one
  Machine, is not replicated, and the docs advise at least two [S765].
  Tigris is durable and bills through Fly [S766], but adds a second service
  for write-once rows when Neon, already used by the maintainer's other apps,
  holds them [S773].
- **WebGPURenderer.** The manual calls it experimental and says
  `ShaderMaterial` and `onBeforeCompile()` are unsupported [S524]; the LED
  shader is a `ShaderMaterial`. Phone support is also uneven (the A2
  planning report: Firefox Android lacks it). `WebGLRenderer` is the
  recommended choice for WebGL 2 applications [S524].

## Amendment (2026-11-08) — the Gallery: a shared layout with looks, published from the Console

The hosted studio becomes the **Gallery**. It has no page, editor or save API
of its own. It serves the Console's page, shows a shared layout read-only in
3D, and lets a visitor play with looks for the visit and export them. The
engine's page, the **Console**, publishes. Code names stay (`studio`,
`python -m pewpew studio`). Status stays **Accepted**.

### Decision

- **A share is an envelope.** `{format: "pewpew.share", version: 1,
  arrangement, looks}`: the arrangement with every `controllers[].host`
  removed and no floor plan (v1), and a looks file v4 of the chosen looks,
  each checked with `pewpew.lab.check.ready`, with no `triggers` and no
  `notes`. The id is the content id above, over the canonical envelope.
  `src/pewpew/share.py` holds the canonical JSON, the id and the checks. An
  old stored row is a bare arrangement; it opens as an envelope of that
  arrangement and the example looks.
- **Publish is a top-level form POST from the Console.** The page builds
  `<form method="post" action="{gallery}/api/shares" target="_blank"
  rel="noreferrer">` with one hidden field `envelope` and submits it in the
  user's press. The body is `application/x-www-form-urlencoded`, a simple
  request: no preflight, and the Gallery sends no CORS headers [S784]. The
  Gallery answers `303 See Other` with `Location: /a/{id}`, and the new tab
  loads that page with GET [S786]. `rel="noreferrer"` omits the `Referer`
  header and implies `noopener`, so the Console's LAN address is not sent
  [S787]. Errors answer in plain text: 413, 415, 422 or 429.
- **No fetch crosses between the two origins.** Board hosts are stripped
  before the envelope leaves the Console, and the Console shows "This is
  public: anyone with the link sees this layout and these looks. Board
  addresses are removed." before the press.
- **Internal and public notes.** An arrangement has two free-text fields:
  `notes`, internal, which never leave the machine (stripped from every
  share and export, and again when the Gallery checks one), and
  `public_notes`, which may travel with a share. The arrangement's `name`
  is public. Before the press, Publish shows as plain text everything the
  share makes public (the name, the public notes with a switch to leave
  them out of this share, and the looks' names); what is right to make
  public is the author's call, share by share.
- **The Gallery serves the Console's build** at `/` and `/a/{id}` (title
  `pewpew Gallery`) with the same hashed files, `/parts.json` and prebuilt
  GLBs, and one websocket `/ws?a=<id>` per visitor. The hello's
  `capabilities` gate the page (ADR-020, 2026-11-08 amendment). The routes
  `/api/compile`, `/api/catalog`, `/api/looks`, `/api/assembly/*`,
  `/api/arrangements*` and `/ws/session` are gone.
- **Gallery looks are an in-memory book for the visit.** A visitor saves,
  renames and favorites looks and exports them; the server stores nothing
  of them, and a new session starts from the share's looks with the idle
  cycle off.
- **A session's memory is bounded.** Its book grows to a share's size at
  most (256 KiB of compact JSON, 64 looks); one `export` at a time is on
  its way, at most 10 a minute; its outbox holds 256 messages and 1 MiB of
  text, serialized as queued, and an overflow closes the socket even
  mid-send. A page refused before a hello backs its reconnects off
  exponentially with jitter, to 10 s.

### Consequences

- The web build has one page. The Dockerfile has no Node stage; the image
  serves the committed Console build.
- A link shows the looks its author chose, not only the layout. Board
  addresses and the floor plan do not leave the LAN.
- A visitor cannot change a shared layout; to change one they export the
  looks and use the engine.

### Evidence

- [S784] A POST with Content-Type `application/x-www-form-urlencoded` is a
  CORS simple request, and an HTML `<form>` can already send one to any
  origin, so the server need not opt in.
- [S786] RFC 9110 15.4.4: 303 is "primarily used to allow the output of a
  POST action to redirect the user agent to a different resource".
- [S787] MDN: `rel="noreferrer"` on a `<form>` omits the `Referer` header
  and implies `noopener`.
- [S785] Chrome's Local Network Access asks the user's permission for
  requests from a public site to a local address, covering `fetch()`,
  subresources and subframe navigation in Chrome 138.

### Rejected alternatives

- **A `fetch` POST from the Console with CORS.** A JSON body is not a
  simple request, so the Gallery would answer a preflight and send CORS
  headers, and allow the Console's origin, a LAN address it cannot know
  [S784]. The form needs neither.
- **The Gallery fetching from the LAN engine.** It is a public-to-local
  request, which Chrome gates behind a permission prompt for `fetch()` and
  subresources [S785]; it would also need the engine reachable from the
  internet side and CORS headers on the engine (inference).
- **Keeping a separate studio page.** It duplicated the Console's views and
  wire; serving the Console's build, gated by capabilities, needs one page
  and one client (inference).
