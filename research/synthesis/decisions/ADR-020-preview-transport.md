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
