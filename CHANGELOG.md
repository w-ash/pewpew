# Changelog

All notable changes to pewpew are documented here, per
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). The project
is pre-release; work accumulates under Unreleased until the first shipped
series (batch mode).

## [Unreleased]

### Added

- Add a `shape` arg to `osc`: `saw` climbs from 0 to 1 and jumps back, so a palette
  over it wraps round (a rainbow that restarts at red) where the default `sine`
  plays it up and back. The sine renders as before.
- Lint the front end for bugs with oxlint and its type-aware rules (`pnpm -C web lint`,
  in `just web`, so `just check` and CI): `correctness`, the React hooks and React
  Compiler rules, the promise rules and `no-param-reassign`. No style rules. It
  found a null fixture attachment in the model-reload key, and a few promises the
  tests left unawaited.
- Record one effect system (ADR-025, Proposed): a look over the op catalog is
  the only effect. The gallery, the `pattern` op, hand-written Python
  patterns and fixture units are to go, `run LOOKS` replaces `run PATTERN`,
  and the studio is to run the aura. The bullets it supersedes in ADR-005,
  -006, -007 and -020 to -024 say so.
- License pewpew under Apache-2.0 (`LICENSE`, `NOTICE`, ADR-012 Accepted),
  the capture-node firmware included. The third-party excerpts in
  `research/excerpts/` keep their own licences, with the full texts in
  `research/excerpts/LICENSES/`.
- Keep projects in `projects/<project>/`, each its own git repo cloned there
  and ignored by the engine; `just branches` reports their open work.
- Hear a mixer from a capture node (RA-28 M2b,
  `firmware/audio-node`, `pewpew.audio.net`). The node is an
  ESP32-S3-DevKitC-1 with a PCM1808 on its line in, running a small
  Apache-2.0 ESP-IDF v6.1 firmware: it sends 48 kHz mono audio in 10 ms UDP packets,
  each with its first sample's index, to the one host that signed its
  subscription with the node's own key; the holder keeps the stream while
  it renews. Its HTTP is read-only (`/json/info`, with `brand` "pewpew"),
  a task watchdog and a send-stall supervisor reboot it, and the RGB LED
  shows when it streams. `just firmware` builds it in the pinned ESP-IDF
  image, and a CI job does on every firmware change. `run --audio
  net:pewpew-line-1` subscribes; outside `--unattended` it needs `--allow-host`
  with the node's address, and audits before the first subscription and
  each new address. A run streams only from the node it first subscribed
  to: another node at its address (DHCP moved them) is the reason the
  input is lost, and a packet of a boot nonce the run did not sign for is
  dropped, never taken as a reboot. Late, repeated and far-future packets
  are dropped, and after 0.5 s of only those the stream is followed again;
  a lost packet holds its hops, a reboot starts a new epoch, the drift is
  measured, and no packet for 0.5 s reads as lost with the last tempo kept.
  A refusal stays the input's reason until the node answers again, and the
  10 s loss share counts only what of an outage that window holds.
  Provisioning a node that already has Wi-Fi settings reports a refused
  change instead of rebooting it. `audio list` lists the nodes, without
  the audio extra too, `boards scan` shows them as nodes and the
  page's board scan never offers one, `audio key MAC` makes a node's key
  and its flash image (tier 1), and `wifi --name` names a node over
  Improv. The health row gains the node's numbers and checks. A packet
  trace (headers and ticks, never samples) replays a node's run
  deterministically over a seeded signal; `bench/bench_node.py` records
  one at the bench, and `docs/audio.md` §8–9 has the attended build,
  flash, provisioning and bench steps. The wiring and parts are in
  `docs/breadboard-wiring.md` and `docs/hardware-buying-list.md` §4.5.
- Hear the room live from a line-in or a microphone (RA-28 M2,
  `pewpew.audio.device`). `run --audio "Scarlett 2i2 USB"` opens one of
  this computer's inputs at its own rate through the new optional extra
  `pewpew[audio]` (sounddevice 0.5.6), and `--audio-channel N` reads one
  channel. `audio list [--json]` names the inputs by the exact names
  `--audio` takes and opens none; an index or a part of a name works while
  the input is plugged in. A blank name and `default`, the laptop's
  built-in microphone, are refused, as is a name two inputs share, and a
  spec with a `/` is a file. The loop reads the stream each tick with no
  Python callback. An unplugged input reads as lost (silent levels, the
  beat at its last tempo), and pewpew opens it again by its exact name
  once it is back, listing the inputs only while no stream is open. An
  input absent at launch never stops the aura: the run starts lost, and
  the input opens at its own rate once it appears. The first open writes
  an `audio-input` audit record, and the health state gains an `audio`
  row with a fix sentence for lost, busy, exact zeros (macOS may deny a
  LaunchAgent the microphone), dropped samples, clipping and overflows;
  the page's chip leaves it out until the page draws it. `docs/audio.md`
  covers the input, privacy, the
  LaunchAgent's microphone check and the attended replug test
  (`bench/bench_audio.py`). Without the extra, the refusal says how to
  install it; `import pewpew` and every other command still load no
  capture library.
- Hear real sound from a file (RA-28 M1, `pewpew.audio`). `run --audio
  FILE.wav` analyses a WAV file on a loop, frame by frame as a live input
  will be: a 10 ms hop counted in samples, 16 mel bands with volume, bass,
  mid and high from a 1024-point window behind one gain rider and gate,
  and Stark, Davies & Plumbley's beat tracker over 80–160 BPM steering an
  engine-time oscillator, so `beat_phase` never steps back. A DC offset
  reads as silence. Gaps hold the hops they touch, lost input keeps the
  last tempo with silent levels, and tap, hold, auto, resync, nudge and
  sensitivity are controls for the page to come: a tap sets the tempo and
  the phase, can move a beat that locked onto the off-beats, and is
  followed at a multiple of the tracker's tempo outside 80–160 BPM. `--feature-log PATH` writes each frame, `--audio replay:PATH`
  plays it back byte for byte, and `--audio-delay MS` delays the levels
  for late speakers. `audio analyse FILE [--json]` reports the tempo,
  confidence, beat times and levels an agent or a person needs. Patterns
  and the `beat`, `band` and `env` ops read the same fields unchanged, no
  dependency is added, and nothing imports a capture library; without
  `--audio`, every run reads the simulated features as before.
- Record how pewpew hears live sound (RA-28, sources S1750–S1797).
  ADR-009 gains two amendments. "Live input": polled capture with no
  Python callback, analysis on the sample clock at the native rate,
  Stark, Davies & Plumbley's tracker over 80–160 BPM with confidence and
  free-run, an engine-time beat oscillator, tap, hold and resync, and a
  feature log that is off unless asked. "Capture nodes": an ESP32 node may
  send raw audio to its one subscribed host, under the private-router trust
  model with a signed subscription and no per-packet tag. ADR-012 gains
  the legal basis for implementing protocols such as WLED's Audio Sync V2.
  BeatNet, which ADR-009 named, cannot install on Python 3.11 or later.
- Build a provenance-tracked research tree: 512-source bibliography across
  eight research batches (landscape through fleet resilience), topic docs,
  and code dives into WLED, FastLED, LedFx, Pixelblaze, HyperHDR, fadecandy,
  led-control, and marimapper.
- Synthesize the architecture: `research/synthesis/architecture.md` §1–13,
  requirements catalog (Q/W/P/R/M/T IDs), comparison matrix, and 20 ADRs
  (ADR-000..019) covering color pipeline, transport, receivers, authoring
  model, mesh tier, and test/feedback/resilience strategy.
- Verify the research pass: six critic reports, 18 findings resolved, and
  archive snapshots recorded for load-bearing sources.
- Land the test-harness skeleton: golden-frame regression loop
  (`uv run pytest`, `--regen-goldens`), deterministic `FakeClock`, pattern
  contract, and fleet-sim interfaces.
- Add a committed verification harness for the playground (`preview/verify.js`,
  Playwright): animation, lever-effect, pause, and spin checks with the
  measurement rules that keep them deterministic.
- Add a live pattern playground (`preview/index.html`): browser-rendered JS
  ports of the five authoring patterns with parameter levers, tempo-driven
  fake audio, and a particle-upgraded fire (Doom-style advection, wind and
  gusts, noise cooling, wandering tongues, additive embers). Dark-mode-only,
  single file, opens locally.
- Add the Phase-0 authoring-surface prototype (`bench/authoring/` +
  `bench/bench_authoring.py`): five canonical patterns (plasma, comet, geq,
  fire, 3D SDF) written against the ADR-005 contract with a per-line stumble
  inventory in `bench/results/authoring-2026-07-16.md` — zero blockers,
  verdict GO conditional on idiom-kit additions.
- Add the Phase-0 throughput microbenchmark (`bench/bench_throughput.py`):
  per-pixel loop vs NumPy vs Numba at 300/3k/30k px with agreement gate and
  committed JSON artifacts; desktop datapoint clears the R-9 target 52× on
  Apple M5 Pro (Pi 5 rerun pending).
- Add the Phase-0 pacing-jitter soak (`bench/bench_pacing.py`): three pacers
  over a 16.67 ms tick under render + capture-thread load, reporting cadence
  distribution, drift and GC pauses. Desktop datapoint passes — p99 cadence
  error 3.78 ms over 10 minutes, 1 of 35 995 intervals off by a frame — and
  measures ADR-010's rejected compensated-sleep pacer at 51.17 fps.
- Add `research/tools/retry_archives.py`: resumable archive.org snapshot
  retries for `SOURCES.md` entries left marked pending by earlier passes —
  availability API first, Save-Page-Now fallback, journalled per entry.
- Decompose Phase 1 into a scheduled `docs/backlog/v0.2.x.md` series, with
  the Phase-0 study's conditional obligations as first-class stories.
- Land the Phase-1 render core (`src/pewpew/`): the ADR-005 authoring
  contract as `setup`/`before_render`/`render` over coordinate arrays, the
  pure `render_sequence()`, frame-scoped `time()`, and per-frame exception
  containment that shows a pulsing-red error frame and keeps the aura
  running. Ships the five study patterns as the built-in gallery, rendering
  bit-identically to the prototype they replace.
- Sanction private per-pixel state (ADR-005 amendment): a `setup(n, x, y, z,
  index)` hook hands patterns their coordinates, and buffers declared there
  with `self.buffer(name, shape)` are engine-managed and read-only inside
  `render` — so stateful effects no longer launder per-pixel state through
  the output buffer, which is what ratcheted additive overlays to white.
- Add the four idiom-kit helpers the Phase-0 verdict made the GO conditional
  on — `fade`, `bins`, `sample2d`, `hash01` — each a bit-exact substitute for
  the study expression it replaces.
- Add `docs/authoring.md`, covering the six friction points the authoring
  study measured, each traced to the pattern line that produced it.
- Land the paced render loop (`src/pewpew/pace.py`, `PacedLoop`): ADR-010's
  deadline-corrected clock, ported from the pacer the Phase-0 soak validated
  — absolute schedule, accumulated-error correction, skip-ahead on blown
  deadlines, and an opt-in spin variant with a host-measured margin. Engine
  time is nominal schedule time (ADR-010 amendment), so a live run renders
  bit-identically to `render_sequence` at the same slot.
- Add `SinkDriver`: per-sink newest-wins backpressure — a worker thread and
  one-slot mailbox bounding frames in flight at two, so a stalled or raising
  sink drops stale frames instead of ever backing up the render loop.
- Land the sink layer (`src/pewpew/sinks/`): the `Sink` protocol
  (`send(t, frame)` + lifecycle, with DDP's fill/latch fused into `send` per
  ADR-003), a shared display-gamma + quantize-once helper (`to_display_u8`),
  and `RateGate` self-pacing that lets each sink run at its own output rate
  by blocking its own driver worker.
- Add the ANSI terminal sink: truecolor half-block rendering laid out from
  the mapping — 1D strips as a row, 2D grids with y=0 at the bottom, 3D
  lattices as z-slices left to right — with linear-light cell averaging
  before gamma, TTY cursor-overwrite vs frame-per-block pipe mode, and an
  exact-string golden test.
- Add the browser preview sink (ADR-020: `websockets` sync server becomes
  the second runtime dependency): one port serves a zero-dependency canvas
  page and the websocket, positions cross the wire once, frames stream as
  display-ready uint8 after server-side gamma, mappings decimate at 4096 px,
  and every connected tab gets its own newest-wins driver so a dead client
  is contained.
- Surface the renderer's error state through both sinks as text — a red
  status line under the ANSI grid, a banner on the preview page — beside the
  pulsing-red error frame that already flows as pixels.
- Add the `python -m pewpew run <pattern>` entry point wiring renderer,
  paced loop, and driver-wrapped sinks: `--map line:64|grid:16x16|lattice:8`,
  `--ansi`, `--preview [PORT]`, `--param k=v`, `--frames N`.
- Make typed params real (ADR-006 amendment): `Param` declarations now
  outlive bind as a `ParamSet` that reports what knobs a pattern has, their
  ranges, units and current values. Declared `lo`/`hi` are enforced rather
  than decorative — an out-of-range value is refused with the range and the
  file to widen, never clamped — and validation (`check`) is separable from
  mutation (`set`) so a control surface can reject a bad value on its own
  thread instead of killing the render loop.
- Add the param-liveness check (`tests/test_param_liveness.py`): every
  declared knob is moved across its full range and must change the rendered
  sequence. Catches the class of bug that shipped `sdf3d`'s `spin`, a
  parameter that was a mathematical no-op nothing caught — it now fails at
  rms 2.65e-08 against a 1e-3 bar, and is carried as a strict `xfail` so the
  exemption cannot outlive the bug.
- Re-verify the receiver and wearable silicon bets against 2025–26 sources
  (`research/verification/hardware-refresh-2026-08.md`; new sources S371–S382
  and S422): the ESP32-S3-with-PSRAM receiver bet stands and strengthened, and
  three dated triggers that would overturn it are now named. Chief among them
  is the ESP32-S31, in mass production since 2026-07-27 and superseding the S3
  on paper once devkits and a WLED/FastLED port exist — re-check it before any
  fleet-scale buy. Recorded as `## Verification` in ADR-013, which also makes
  nRF54L15 the W-5 wearable default in place of nRF52840.
- Default `--map` to the fixture a pattern was authored against, from
  `STUDY_CASES`. `grid:16x16` fits geq and fire and nothing else — comet and
  plasma were written for `line(300)`, sdf3d for `lattice(10)` — so the
  no-argument run, the first thing anyone types, showed three of five patterns
  on geometry they were never designed against. An explicit `--map` still wins,
  and a pattern outside the table keeps the old default.
- Add live parameter sliders to the preview page: one per declared `Param`,
  bounded by its range and stepped by the engine's own quantization, driving
  the running pattern over the existing websocket. The retired playground's
  sliders drove JS reimplementations, so what a knob showed was not what
  rendered — these drive the real engine. Every open tab follows whichever
  one moved last, and a refused value snaps back with the reason.
- Add the live-set half of the param-liveness check: each knob is turned
  mid-sequence and the frames after it must diverge. The bind-time check
  cannot see a knob that only takes effect at bind — a pattern precomputing
  from one in `setup` passes that bar at rms 0.37 and fails this one at 0.
- Run a pattern from your own file: `python -m pewpew run effects/mine.py`,
  `mine.py:ClassName` when the file defines several, or a bare name resolved
  through `--patterns DIR` before the gallery. The ADR-005 contract was
  already the extension point — `Renderer` takes any subclass — but the tool
  could only name the five built-ins, so a custom effect was a library call
  and not a command. A bare name is never the working directory, and a load
  error names the line but never leaks a path past the CLI.
- Hot reload with the run's state kept: while `run` is up, a save re-executes
  the pattern file and swaps the new class in between two frames (`--no-reload`
  opts out; gallery files reload too). Engine time, parameter values (kept when
  they still fit, else reset to the new default per ADR-006), `self.pixels` and
  every `self.buffer` with a matching name and shape, the RNG stream, and plain
  scalar state of the same name and type all continue — a swap to the same
  source is bit-identical to no swap for all five gallery patterns. A save that
  does not load keeps the last-good pattern running and shows why on the
  terminal status line and the preview banner; fixing it clears the banner. The
  preview page rebuilds its sliders when a reload changes the knobs.
  `watchfiles` becomes the third runtime dependency (architecture §9,
  ADR-020).
- Add the pewpew studio: arrange LED fixtures in 3D, run the real engine on
  the arrangement, read a power, wiring and controller report, and share it by
  link. A catalog of fixture types, chipsets, connectors, cables, PSUs and
  controllers is validated JSON, with a provenance status on every value; the
  1M LED Pixel Bar ships as a full assembly (housing with T-slot, end caps,
  strip and LEDs, flat-cut diffuser), beside the 360 tube and the point and
  eye end pieces. An arrangement places free fixtures or `ring` and `array`
  groups and compiles to a pixel mapping in data order, which
  `run --map file.json` also takes. Auto-wiring cuts chains to the frame-rate
  target and the board limits, sizes power feeds to the connector rating and
  the voltage drop, fuses each feed, and adds boards and supplies of the
  declared types until everything fits; the report lists every chain, hop,
  feed and PSU with a bill of materials, and flags each result that rests on an
  assumed value. The golden rings come to 2 boards, 6 chains, 24 feeds, 3 PSUs
  and 1,228.8 W with every channel full. The server runs one `Renderer` per visitor and
  streams its frames and a live power estimate over a websocket, builds
  deterministic fixture GLBs with manifold3d, and serves a React +
  react-three-fiber page with a transform gizmo, ring and array editors, undo,
  JSON import and export, and a phone layout. Share links are immutable
  content-addressed snapshots in Neon Postgres, with SQLite locally, and
  per-address limits on sessions, compiles and saves keep one visitor from
  starving the rest. `python -m pewpew studio` runs it on the laptop; a `v*`
  tag is tested, released, and deployed as one container to one fly.io
  machine.
  `pydantic` joins the core dependencies; FastAPI, uvicorn, psycopg and
  manifold3d form the `studio` extra (architecture §9, ADR-024). The laptop
  `run --preview` page is unchanged.
- Add Rainbow to the gallery and make it the studio's default effect: hue
  bands that flow inward from the rig's centre, ported from the studio
  prototype. `run rainbow` defaults its map to the 60-bar canopy.
- Cap a rig's power: an arrangement's optional `power` block sets a brightness
  ceiling and a watt cap, which the engine applies to every frame before any
  sink quantizes, split across the supplies so no PSU carries more than its
  share. The studio preview shows the capped light, the Report panel edits the
  cap, and `run --max-watts --max-brightness` caps a laptop run. PSUs are
  sized for the most the RGB stream draws through WLED's Accurate auto-white,
  under the cap: the golden rings take 3 PSUs uncapped (614.4 W) and 1 at
  18.4% brightness (113.0 W). Under a cap, feeds are checked at the capped
  current and each needs a fuse at its head (ADR-001 amendment).
- Add the BTF-LIGHTING 24 V 5 A brick and its 5.5 × 2.1 mm barrel to the
  catalog, and two examples that run the golden rings on four bricks: 12
  chains of 4 at 62.5% brightness, and 4 head-fed chains of 12 at 46.9%.
- Count a board's own draw against the PSU that powers it: a controller
  profile's optional `power_w` (0.6 W for the DevKitC-1, from WLED's 120 mA),
  a PSU's `powers` list, and a buck efficiency (70%, assumed). Add the golden
  rings in 4 self-contained sets, one brick, buck and board per quadrant, at
  61.94% brightness, with its wiring diagrams and shopping list.
- Hang a chain on a T trunk: a chain's optional `tee` runs its links from
  one fixture's input to the next along the trunk, and leaves the fixtures'
  pass-through out of the drop. Add the golden rings on six Clen T trunks,
  2 boards and 3 bricks at 46.45% brightness, with its wiring diagrams and
  shopping list. It rests on a T pin map that no source gives.
- Run the 3D studio on the current engine: every gallery effect plays on a
  studio rig, and the Effect panel draws each param by its kind (a slider
  for a float or an int, a switch for a bool, a menu for a choice, a color
  picker for a color) and sends values the engine checks by kind. Bars light
  as one unit for per-fixture effects such as Pulse and Sparkle, a pattern
  change starts the new effect at its defaults, and the session speaks the
  preview's `status`, `declare`, `params` and `refused` messages.
  `run --map <arrangement>.json` renders per fixture too, and its power
  limit runs after the master dimmer. The gate (`just check`, CI) now builds
  and tests `studio-web/` beside `web/`.
- Run the 3D studio on the layered engine, beside the compositor, effect
  programs and live audio: a studio session, `run --map <arrangement>.json`,
  `--max-watts` and `--max-brightness` work as before, and `studio` adds its
  own subcommand. The Effect panel decodes every param kind the engine
  declares, and sets a palette from its presets and draws its gradient. The
  session's `status` names the part that raised by its `path`, and its
  refusals carry `name` and `id` as the preview's do. Rainbow is warpable
  and is listed in the effects catalog.
- Record the studio decisions: ADR-024 (hosted studio: server-side rendering,
  FastAPI beside the sync preview server, public gallery-only trust model,
  fly.io + Neon, React 19 + R3F + three r186, server-built GLB), an ADR-007
  amendment for the arrangement and catalog format, and 26 new sources
  (S316, S523-S527, S763-S782) in `research/SOURCES.md`.
- Stream to stock WLED boards over DDP: `run --ddp HOST=START+COUNT` (one per
  board) sends each board its pixel range as 8-bit RGB at `--ddp-fps`
  (default 40), with PUSH on each board's last packet. `--dry-run` prints the
  per-board plan and sends nothing; every real start appends a line to an
  audit log outside the repo (`PEWPEW_AUDIT_LOG`).
- Add the Wi-Fi ingest bench (`bench/bench_wifi.py`): streams to all boards
  at 40, 50 and 60 fps for k trials while polling each board's `/json/info`,
  and writes per-board distributions of delivered fps, signal and reboots.
- Describe a room in one JSON file (`run --room PATH`): bars and tubes as
  strips in meters, arrays for rows, boards, outputs and chain order. It
  compiles to the mapping and each board's DDP range, checks the wiring at
  load, and reloads live on save. A pattern can set `units = "fixture"` to
  light each bar as one unit. `examples/room-60-bars.json` is a 60-bar canopy.
- Make the preview page the aura's control surface: reachable from a phone
  (`--host`), a pattern picker, a master dimmer under a launch-time cap
  (`--master-cap`), two-step blackout, and `--unattended` for an unattended
  run (keep-awake and the watchdog).
- Save and recall looks (`--looks PATH`, a version-3 file): pattern, params
  and optionally the master, recalled with a crossfade on engine time, restored on restart, and
  cycled when idle.
- Show the room as it is: dots sized from each fixture's pixel pitch, drawn
  additively over a dimmable, two-point-calibrated floor plan, with
  input-end markers and blink-to-identify for setup.
- Add the canopy set, four patterns: `pulse`, `wave`, `wash` and
  `sparkle`, each with a color and a speed, all held under 3 flashes per second by a test.
- Set up a new WLED board from the laptop (`python -m pewpew wifi PORT`):
  sends the Wi-Fi settings over USB serial (Improv), prints the IP the board
  reports, and with `--name` sets its display and mDNS name and reboots it.
  The password comes from a hidden prompt or, with `--ssid NAME --keychain`,
  from the macOS Keychain, and never reaches argv or the audit log. `pyserial` becomes the fourth runtime dependency.
- Add the standard breadboard layout (`docs/breadboard-wiring.md`): a
  hole-by-hole map for one DevKitC-1 and one 74AHCT125 on two half-size
  breadboards, with four outputs on GPIO 4–7.
- Add `colorplasma`: plasma painted with a three-color palette. Each color
  is its own `color` param with a hue cycle (seconds per turn, 0 holds).
- Declare typed params: `Float`, `Int`, `Bool`, `Choice` and `Color` (one
  HSV param with parts `h`, `s`, `v`), each with a unit, help text, a layout
  group and an optional widget. The page renders each kind with its own
  control, from the engine's declaration.
- Rebuild the control page in React and Ark UI from `web/`, built into one
  committed file the laptop serves gzipped: a control per param kind (slider,
  angle dial, switch, segmented choice, inline color picker, typed entry),
  collapsible groups, a reset dot per param and reset all, phone and desktop
  layouts, and desktop keyboard shortcuts (`?` lists them; they can be
  turned off).
- Add a Layout mode to the page for input-end markers, fixture blink and
  board rebind; effect settings stay visible in every mode.
- Show a red "Not connected" banner and dim the controls while the page has
  lost the engine, so no tap is silently dropped.
- Name the failing pattern and the part that failed (render, reload or
  looks) on the status line, once per distinct error.
- Give every health row a fix sentence, the render loop and sleep rows
  included.
- Reload a page tab that was built for another engine build.
- Let room events drive the lighting: a page "fire cue" button and arm
  switch submit tick-stamped events that recall a look for a set hold and
  then return, or reach the pattern as `features.events`. Debounce,
  cooldown, priority and a rate limit run on engine time; `--trigger-log`
  records a JSONL log that replays byte-identically; `--armed` starts armed.
- Keep a multi-day unattended run healthy: a per-board health panel from WLED's
  `/json/info`, a render-loop watchdog that exits so launchd restarts the
  aura (`deploy/launchd/pewpew-aura.plist`), a sleep assertion, and
  `python -m pewpew boards backup|restore` for each board's WLED config.
- Add the live-rig soak bench (`bench/bench_soak.py`) and a 20-minute
  loopback run, and the unattended checklist (`docs/unattended-checklist.md`).
- Fold the 2026-10-19 research on stock-WLED DDP over a private router
  into the tree (`research/verification/wled-ddp-private-router-2026-10.md`,
  sources S1250–S1299).
- Say what to do about each board in the health panel: one fix sentence per
  board, its room name, address and MAC, a link to its WLED page, a banner
  while a board is bad, and a check that the MAC answering is the board's.
- Add "find boards" to the health panel and `python -m pewpew boards scan`:
  both list the WLED boards on the laptop's network, and the panel's "use
  for A" rewrites that board's address in the room file.
- Let an agent see rendered output: `pewpew.sheet` draws a sequence as one
  labeled PNG contact sheet (a space-time strip for a strip, time-stamped
  tiles for a panel, top-down dots for a volume or a room, and an A/B
  compare sheet), sized for a vision model. `pewpew.metrics` measures
  flashing against WCAG's 3 per second, brightness, black and clipping,
  motion, frozen frames, detail and palette spread. `pewpew.png` encodes
  the sheets with the standard library, the same pixels always giving the
  same bytes.
- Add the `palette` param kind: a gradient of 2 to 16 color stops, with
  named presets (`pewpew.color.PRESETS`: ember, ocean, aurora, synthwave,
  forest, ice, candy, mono) that `--param palette=ocean` and the page's
  picker choose. The page's palette control draws the gradient as the LEDs
  show it and edits each stop with the color control and a position slider.
- Add `pewpew.color`: OKLab conversions and `gradient_lut`, a cached table
  that blends a palette's stops in OKLab, so blue to white stays blue, and
  moves a color outside the gamut in by chroma, never by clamping a channel.
  `sample` reads the table from 0 (the first stop) to 1 (the last), so a
  strip's last pixel shows the gradient's end.
- Add modulation to the param domain: a float, an int or a color's part can
  be driven by an offset (`Bound.drive`), wrapped when periodic and clamped
  otherwise, while sliders and saved looks keep the operator's value. A new
  room map keeps the drives; after a swap the old binding refuses.
- Add the effect primitives (`pewpew.fx.prims`) that layered effects build
  on, in plain NumPy with no new runtime dependency: seeded value and
  gradient noise in 1 to 3 dimensions with fBm, ridged, turbulence, curl and
  domain warping; coordinate ops (rotate, polar, kaleidoscope, mirror,
  twist, tunnel, repeat); signed distance functions with smooth union,
  subtract and intersect; bilinear and trilinear field reads with clamp or
  wrap edges, advection, and cylindrical and spherical projections; deposit
  of points into a field; and an exact nearest-neighbour graph from a grid
  hash, with diffusion, wave and Gray-Scott steps that run on any layout
  and refuse settings that would diverge on one.
- Let a pattern declare `warpable = True`: its `render` then gives a correct
  frame at any finite coordinates other than the ones `setup` saw, far
  outside 0–1 too, with `index` as the identity that no warp moves (ADR-005
  amendment 2026-11-05). Every gallery pattern declares it, and `warpable` cannot be a
  param name. Comet's sparks now hash the coordinates `setup` saw and its
  head's distance wraps at 1, so a moving warp no longer makes the sparks
  crawl. Unwarped, its frames are byte-identical to before.
- Let an agent watch a running engine: `python -m pewpew observe URL`
  reads the preview's aura state, status, params and health and the frames
  it streams for `--seconds` of engine time, then reports `pewpew.metrics`
  over them and, with `--sheet PATH`, a contact sheet. It sends the engine
  nothing (tier 0). The numbers are flagged approximate: the frames are
  8-bit display gamma (`from_display_u8` undoes it) and a large map is
  decimated. `--json` prints one document, even when the sheet cannot be
  written; a capture without metrics or the sheet asked for exits 1, and
  an engine that does not answer exits 3 with what to try.
  `pewpew.remote.client` is the wire client under it, and the soak
  bench's client now uses it.
- Record the decisions for layered effects and agent connectivity:
  ADR-021 (a stack of renderers blended once in linear light, the
  compositor as the modulation seat), ADR-022 (effect programs: typed node
  graphs of ops declared with params, one op catalog and one JSON codec)
  and ADR-023 (the `pewpew.lab` service, the `fx` CLI verbs and MCP as an
  optional adapter), with 2026-11-05 amendments to ADR-005, ADR-006,
  ADR-018 and ADR-020, sources S1400–S1469 (RA-25 and RA-26), and the
  v0.3.x backlog that builds them. The records match the params,
  primitives, sheets, warpable patterns and observe as built, and the MCP
  SDK as observed in `mcp` 2.3.0.
- Stack patterns in layers (`pewpew.compose`): a look is layers bottom to
  top, each running a program with its own opacity, blend mode and on
  switch, blended in linear light and clamped once. The blend modes
  (`pewpew.fx.blend`) are normal, add, screen, multiply, max, min,
  difference, subtract, stencil and highlight. Each layer draws its own
  random stream from the look's seed and its id, so adding, removing or
  moving a layer never changes another's picture. A one-layer stack renders
  exactly what its pattern alone renders.
- Address every knob by its path: `layers.<layer>.<pattern>.<param>`, and
  `layers.<layer>.opacity`, `.blend` and `.enabled` for a layer's mix. A
  refusal names the path, and the page's knobs, `set` and the status line
  use it.
- Hot-reload each layer's pattern on its own: a saved file reloads into
  every layer that runs it.
- Send the running look's layers to the page (`aura.stack`), and let a pick
  name the layer it runs on (`pick.layer`; null is the bottom layer).
- Read a palette param as a frame with `self.palette.rgb(x)`, as a color
  param reads with `self.color.rgb(level)`.
- Document layered looks in `docs/authoring.md` §9: a two-layer looks
  file, the knob addresses and the blends.
- Leave a failing layer out of the mix in an `--unattended` run while another
  layer still renders; the status line still names it. With more than one
  layer, the page's status line names the failing layer and says to pick
  another pattern (bottom layer) or recall another look (any other). A
  room map reload that a layer cannot bind leaves that layer failing and
  the others running.
- Check, render, measure and compare looks offline, for people and agents
  alike (`pewpew.lab`, ADR-023): `python -m pewpew fx check|render|sheet|
  metrics|compare|explain` and `verify looks FILE|DIR`. A check lists each
  problem with a stable code, its path (`layers.base.comet.speed`), the
  aura's own words and a did-you-mean, or prints the look normalized. A
  render runs the aura's own layer stack and master, so its frames are what
  `run --looks` shows, and answers with a content-addressed handle
  (`r1-...`) whose frames wait in a size-capped cache under
  `$PEWPEW_CACHE`. `verify looks` fails a look that does not check, has a
  layer that raises, flashes more than 3 times a second, is all black, or
  has a knob that changes nothing or cannot be probed; it also fails a
  file or folder with no look. A look's effect programs go through every
  verb node by node: a problem names its node, a render refuses a program
  its map does not support (`wrong-dims`), and liveness probes each
  node's knobs. Every verb takes `--json` and prints one document; exit
  codes are 0 ok, 1 problems, 2 usage, 3 an expired handle.
- Let an agent change the look of an engine on this machine (tier 1):
  `python -m pewpew push URL LOOK [--fade S] [--set PATH=VALUE ...]`
  sends a whole look, then knob values, and waits for the engine's answer
  to each. It writes only to a loopback engine unless `--allow-host IP`
  names a bench machine, connects to the address it checked, checks the
  look first as the engine will (a pattern goes by name, never by file)
  and each `--set` against the look's knobs, stops there with the plan
  under `--dry-run` without opening a socket, and appends an audit record
  before it sends; a write it cannot record is not sent. The look goes out
  as written, so the engine fills in its own defaults. Exit codes are 0
  ok, 1 problems with the look or a set, 3 unreachable, 4 refused (also an
  audit record that cannot be written). `pewpew.remote.control` (`push`,
  `set_value`) is the service under it.
- Take a whole look over the preview socket in a run started with
  `--preview --accept-looks` (refused with `--unattended`): the inbound `look`
  message fades to it unsaved, as a pick runs a pattern, until a save
  keeps it, and ends a running fade. A pattern named by a file is refused
  with the part of the look that names it, and a look the loop cannot
  take within the request timeout is refused and never starts. Any
  message may carry an `id`; the engine then answers it with `ack` or with
  `refused`, which now always carries `name` (the knob or the part of the
  look refused) and `id`, null when they do not apply, and a message with
  an `id` and an unknown or missing type is refused (`control` null when
  the type is not text). The `blink` message names its fixture in
  `fixture`, no longer `id`. The hello lists `capabilities` (`ack`, and `look` when the run
  takes looks) for clients outside the package; the page never reads it.
  Messages without an `id` are answered as before (ADR-020 amendment
  "capabilities").
- Run effect programs on a layer (`pewpew.fx`, ADR-022): a graph of ops
  written as a chain, `osc(8, 0.1).kaleid(5).modulate(noise(3), 0.2)
  .palette("ember")`, in a pattern file (`class Tide(ProgramPattern)`) or
  as a looks file's `nodes`. 27 ops: sources (osc, noise, voronoi, shape,
  quasicrystal, metaballs, lissajous, a pattern, the layers below, the
  layer's last frame), coordinate ops that wrap what they read (rotate,
  scale, kaleid, polar, mirror, twist, tunnel, repeat), color ops
  (palette, hue, contrast, posterize), combines through the layer blend
  table (add, mult, diff, blend) and modulate. Every op arg is a param
  with an address, `layers.<layer>.<node>.<arg>`, that the page, `set` and
  a saved look use; a hot reload keeps each node's knobs, buffers and
  phases, and a knob you moved keeps your value. A program is checked
  against the map before it runs, with refusals that say what to use
  instead (`kaleid` on a strip: use `mirror` on u). A program's `alpha`
  node masks its layer. A drifting noise moves smoothly for as long as the
  aura runs, either way: its lattice loops where its phase wraps (the noise
  primitives take a `period` per axis).
- Describe every op once, in a catalog (`pewpew.fx.catalog`) that the
  `fx` command group prints (`python -m pewpew fx catalog`, `fx show OP`),
  that generates docs/reference/catalog.md and the builder's type stub,
  and that a golden holds. Each record has the op's inputs, output,
  dimensions, params, measured cost and runnable examples.
- Read and write looks through one codec (`pewpew.fx.codec`): a bad look
  is refused with every problem at its address, a did-you-mean for a
  misspelt op, param or key, and type errors that teach the fix; a
  program prints back as the builder chain that makes it.
- Give `float` and `int` params two generation hints, `sweet` and
  `flash_sensitive`, in every describe record, so a look generator can
  sample where a knob looks best and keep fast routes off knobs that
  strobe (ADR-022 amendment); layer opacity is flash-sensitive.
- Serve pewpew to AI agents over MCP (ADR-023): `python -m pewpew mcp`
  runs a stdio server on the optional `agent` extra (`mcp>=2,<3`; `import
  pewpew` never loads it, and without it the command says how to install
  it). Its tools, in a fixed order, are thin over the lab and answer with
  the JSON the matching verb prints with `--json`: `catalog_search` (a
  page of the catalog, concise or detailed, with a cursor), `look_check`
  (with each look in words on request), `look_render` (a handle, metrics,
  warnings and a contact sheet image), `look_compare` (an A/B sheet),
  `engine_observe` and `fleet_status`, all read-only; `--tier 1` adds
  `engine_apply` and `engine_set` over `push`, each a dry run unless asked
  to send. A look's patterns go by name only, so no tool runs a file. A
  refused look, kind or cursor comes back as an error that lists each
  problem's code, path, reason and fix, with the corrected call when the
  fix is an argument, then the problems as JSON text; an error carries no
  structured content, which a client such as the TypeScript SDK would
  check against the tool's output schema. An argument a tool does not
  take is refused with a did-you-mean. Resources serve the catalog, the
  example looks (one added while the server runs reads too), the
  authoring guide, the catalog reference and render sheets; prompts
  `design-look` and `critique-pair` start the loop. `.mcp.json` registers
  `pewpew` (tier 0) and `pewpew-live` (tier 1), and a golden holds the
  tool list.
- Teach agents the look loop: the `authoring-looks` skill (catalog,
  check, render, metrics before the image, compare one change at a time,
  the critic, the gate) with references on the metrics and on look shapes
  that check, the `look-critic` subagent (renders, compares and reads
  only; judges in both orders; a verdict is evidence, never a gate), a
  rule for `examples/` and the compositor, and three example looks,
  `examples/mcp-tide`, `mcp-ember` and `mcp-prism`, that pass `verify
  looks`. docs/authoring.md §12 covers the server.
- Search the catalog a page at a time from the lab (`pewpew.lab.catalog`,
  `describe`), for every word of a query in any order (`fx catalog
  --query` too), and give each problem the edit that fixes it
  (`Problem.fix`). `python -m pewpew boards scan --json` prints each board
  it finds with its health (`pewpew.boards.survey`).
- Modulate any float, int or color part of a look (ADR-021, ADR-022): a
  look's `signals` are signal ops that give one number a frame (lfo, env,
  band, beat, walk, knob, smooth), and each of its `routes` moves a knob by
  `depth` times a signal, in the knob's units, wrapped or clamped. The
  stack runs every signal once a frame before its layers; a knob's own
  value stays what the page shows and a save stores. A macro is a `knob`
  with several routes, and a route may drive another signal's knob. Write
  one as `lfo(0.1).to("layers.base.osc.freq", depth=2)`, or pass a signal
  as an arg (`osc(8, sync=lfo(0.1))`) to sweep its sweet range, inside
  `look(layer("base", ...), routes=[...])`; a look prints back as that
  call. A signal that raises holds its last value and names
  `signals.<id>` on the status line while the aura renders on. A route
  that reaches no knob it can move, by more than its span, or in a cycle
  is refused with its place (`routes[0].path`) and a did-you-mean; when a
  pattern edit or a pick takes its knob away or narrows it below its
  depth, the route rests and a save leaves it out. A `front` path that
  names no knob is refused by the checks and left out at recall. The
  page lists a look's `front` knobs first and marks where a route moves a
  knob now, from a `mod` message sent at most ten times a second; `fx
  explain` says how far each route moves its knob, and `verify looks`
  probes each signal's knobs and counts the flashes a fast route makes.
- Add ops that keep state from frame to frame (ADR-022 amendment
  "stateful ops"). `feedback` is the MilkDrop loop: a field finer than the
  points that zooms, spins, swirls, drifts and wobbles each frame, fades
  over `decay`, and takes the brighter of itself and what it reads, so a
  still input never ratchets to white; it works along a strip, in a
  panel's plane and through a volume. `trails` does the same per point
  with no motion. `diffuse`, `ripple`, `reaction` (Gray-Scott: coral,
  mitosis, spots, maze) and `life` (a cyclic automaton) run on the map's
  own points linked to their nearest neighbours, so they follow the wiring
  and never jump a gap, and take as many small steps a frame as their
  speed needs, so no knob makes them blow up. Over minutes a ripple pond
  stays level, since a drop adds as much water as it takes and `damping`
  fades the whole pond, and `life` never settles, since `sparks` start new
  waves where the old ones die out. `particles` (sparks, snow, fireflies)
  and `attractor` (Lorenz, and a Clifford cloud that turns in a panel's
  plane) draw moving points as glow. State lives in node buffers, so a hot
  reload carries it on, and random draws come from each node's own
  stream, so a look renders the same bytes every time. A new op
  signature, `state`, lists the ones that read an input (`fx catalog
  --kind state`); a state op reads its input at the map's own points, so
  a coord op may sit above `feedback` whatever it reads.
- Add ten example looks in `examples/` (strips, panels, volumes and the
  canopy; feedback, graph sims, particles, an attractor, and palettes
  cycling a golden ratio apart), each passing `verify looks examples/`
  and `verify looks --map` on the maps it is for.
- Move knobs in the ten stateful example looks with signals, and list the
  knobs to turn first in each one's `front`: slow walks and LFOs drift
  hues, warps and sizes, the beat and a sound band pulse `warp-lane`,
  `depth-charge` and `ember-fountain`, and `milk-bloom`'s `trip` knob is a
  macro that speeds and stretches its feedback swirl.
- Render each value of a knob once in `verify looks` liveness, shared by
  the probes that start from it (a palette's default, a choice's first
  option): about a quarter fewer renders.
- Skip in `verify looks` liveness a probe the map's shape cannot show, as
  each op declares it (`Op.shows`): an op's `planar` args on a strip
  (feedback's spin and swirl); an arg that acts along an axis the map does
  not spread along (`along`: lissajous's `b` and `c` on a strip, or
  mirror's `centre`, scale's `amount`, repeat's `count` and osc's `freq`
  along a flat axis), or a choice of such an axis; and two choices of axis
  or plane that read the map alike (`u` against the axis a strip runs
  along). A strip look with feedback or a Lissajous knot can pass the gate
  on a strip, and made looks may use mirror, repeat and scale on strips
  and panels; a variation draws a choice again only among the axes and
  planes its map spans, as a made look draws one.
- Probe each knob in `verify looks` liveness after a warm-up: each render
  runs 1 s at 30 fps and compares its last 0.5 s, so a knob that shows
  once a trail, a feedback field or a simulation has filled, or once a
  slow signal has moved off its start, is live. It renders as many frames
  as the cold half second at 60 fps it replaces.
- Build layered looks on the control page. `+ layer` opens the catalog in
  the side slot: patterns, then ops on shelves by what they do, each card
  a line on what it does (the same line `fx catalog` search gives), an
  op's other examples the map runs as builder chains, and a card whose
  example the map cannot run saying what to use instead. A card adds its
  example screened over the running layers at 0.7 (an effect that reads
  the layers under it at normal), and its row opens with focus. With two
  layers or more the page lists them top first, each row with an on
  switch; the picked row opens to its pattern, opacity, blend (`?` says
  what the mode does), ▲ ▼ or Alt+↑ ↓, and remove in two taps, and the
  panel under the list shows that layer's knobs, a node's section each in
  a program. A look's `front` knobs come first, each drawn once, and the
  rest wait under "more". A lone layer's page stays as it was, with a
  quiet `+ layer`, and shows the layer's mix only while it is off its
  defaults. The engine takes `add_layer` (a layer in the looks file's
  form, its patterns by name only, a free id made from its `out` node when
  it has none, under the layer `below` names or on top), `remove_layer`
  and `move_layer` through `AuraControl.request`, each editing the running
  look, which a save keeps, and ending a trigger's hold and a recall that
  waits for the fade, with an `ack` or a `refused` that names the part for
  a client that sends an `id`. The preview sends the catalog's cards and
  blend notes as a `catalog` message in the greeting, and again when an op
  file loads or a pattern file appears; an op whose example does not
  build leaves the page its last cards, and the log says why.
- Make looks from a seed (`pewpew.fx.surprise`, ADR-022): `generate(seed,
  map)` draws a look from a grammar over the catalog (a source, warps, a
  palette that starts dark, up to two more layers screened or added on
  top, up to two slow routes a golden ratio apart), each knob inside its
  `sweet` range and each speed near its default, never past a cost
  budget at the map's size; `mutate(look, seed, map, strength=, keep=)`
  makes one like a look, at a strength above 0 and at most 1 (any other
  is refused, never clamped), holding the addresses in `keep` (a held
  layer, node or signal keeps the look's seed and every route it is
  part of). A map whose points sit at one place is refused. Each
  candidate is judged on the map before it is given: it passes `verify
  looks` with room on every knob's probe, and is not too dark, washed
  out, dying out, frozen, noise or grey when one of its tries manages
  that, else it fails the fewest of those. The same seed and map give the
  same look, in any process.
- Explore looks from the lab, the command line and MCP: `lab.vary`, `fx
  vary [FILE] --seed --n --strength --keep PATH --out rows.png`, and the
  `look_vary` tool (up to 8 candidates, each with its seed, look, render
  handle and metrics, and one sheet of them in rows numbered 1 to n;
  `pewpew.sheet.rows_sheet`).
- Let a running aura make looks: `surprise` (a look made for its own map)
  and `vary` (one like the running look, also one launched from a
  pattern file) fade in unsaved, as a pick does, answered `ack` or
  `refused` with the request's `id` once the look starts; `keep` saves
  the running look under the name a made look offers (`surprise 7`), or
  the next free one, and is refused while a trigger holds a look. A look
  is made on a thread of its own, so a blackout, a master move or any
  other request sent after it runs at once, and a look recalled, picked,
  edited or sent while one is made wins over it (`OVERTAKEN`). The looks
  state names the made look that plays unsaved (`made`).
- Make, vary and keep looks from the control page: `surprise`, `like
  this` and `keep` under the saved looks (keys `s`, `m`, `k`). The button
  pressed shows the engine is busy and the three wait for its answer (the
  page gives these requests an `id`; `Sender.ask`), a refusal goes to the
  status bar, the top bar names the made look, and a kept look shows in
  the look box to rename. Like this needs a look playing, and keep
  something unsaved and no trigger holding a look; the `?` says what
  each does and why one is off.
- Run the idle cycle with a seeded director (`pewpew.aura.director`): a
  random order among the cycle looks, weighted (`weights`), with no look
  again within `window` slots, a dwell drawn from `each` (now a number or
  a `[min, max]` range), and every `fresh`th slot a made look, made a
  slot ahead; `seed` makes the order and each slot's start the same on
  every run, on engine time alone. The loop never waits for a make: a
  fresh slot whose look is not made by its start plays the cycle look
  drawn for it instead, logged, and the next fresh slot plays the fresh
  look; a make that fails says so on the status line. A run makes each
  on a thread of its own, so only whether a make is done by its slot's
  start is up to the wall clock; a caller that steps frames on engine
  time alone makes each at once (`pewpew.aura.variety.at_once`).
- Add a bench script for pairwise taste checks of made looks
  (`bench/bench_critic.py`): it makes K looks, renders them and their
  pairs both ways, and writes the sheets and a manifest for the
  `look-critic` subagent or a person to judge. Evidence only, never a gate.

### Changed

- Dependencies: websockets 17.4 (the wire client opens its socket with
  `legacy=True`, as 17.1 asks of a caller that closes it), pytest 9.2,
  numba 0.68.1, watchfiles 1.3, msw 3 for the studio's mock mode, and
  @types/node 26.
- Name things for the domain. `PatternError` is `RenderFailure` and its
  `pattern` field is `layer`; `pewpew.kit` is gone (`hsv` and `bins` are in
  `pewpew.color`, `TWO_PI`, `wave` and `fade` in `pewpew.fx.prims.vec`);
  `pewpew.classinfo` is gone; comments and docs no longer call a layer or
  program a pattern. No wire field or golden changes. A look that hangs
  while it is built at launch is named in the stall marker (tested).
- Modules take precise names: `harness` is `pewpew.testing`, `sinks/base.py`
  is `sinks/sink.py`, `agent.py` is `mcp_cli.py`, `command.py` is
  `cli_args.py`, and the rig catalog's JSON lives in `rig/catalog_entries/`.
- `run LOOKS` plays a looks file (ADR-025): a version-4 book, a
  `.look.json` included, which it starts in at its `current` look (else
  its first) and saves to. It replaces `run PATTERN --looks FILE`. Without
  `--map` or `--room` the map is `grid:16x16`, and `fx render`, `compare`,
  `vary`, `verify looks` and the MCP tools default to it too. `--seed`
  seeds the stand-in features and the made looks; each look's own seed
  seeds its layers. After a pick no look is current, and the file keeps
  naming the last one, so a restart comes back in it. After a watchdog
  stall a restart starts in the next look of the idle cycle's order that
  can start, not the one that stalled, playing it as a pick so the file
  keeps naming the operator's look, and says so on the status line; the
  watchdog is armed before the look is built. The LaunchAgent template
  runs `run __LOOKS__ --room __ROOM__`.
- One front-end package, `web/`, builds both pages: the control page into
  `src/pewpew/sinks/web/index.html` and the studio (`web/src/studio/`)
  into `web/dist/studio` (`vite build --mode studio`; `--mode mock` serves
  it against mocks). One toolchain: TypeScript at the page's strictness,
  Vitest browser mode in Chromium and WebKit for both pages' unit tests,
  and the React Compiler on the studio too. `studio-web/`, Biome, jsdom and
  Testing Library are gone, and `just studio` is folded into `just web`.
- The studio runs the aura (ADR-025): each session builds the pipeline
  `run` builds (`pewpew.aura.pipeline.build_aura_pipeline`), starts in
  `examples/tide.look.json`'s look, takes every aura request
  (`set` by knob address, `look`, `surprise`, ...) with the preview's
  `ack` and `refused` answers, and streams the preview's per-frame
  messages (`declare`, `params`, `mod`, `aura`, `catalog`). `bind`, `pause`
  and `resume` stay; the `pattern` message and `GET /api/patterns` are
  gone, and `GET /api/looks` lists the example looks.
- The studio's Effect tab is the control page's look editor: the example
  looks, surprise me and vary this, the main knobs, the layers with their
  knobs, "+ layer" cards and the modulators, on the control page's socket
  and wire store (`@pewpew/page/wire`, `/params`, `/stack`, `/deck`). Its
  own pattern picker, params decoder and session protocol are gone; only
  `bind`, `pause`, `resume`, `bound` and `power` are the studio's. Its forms
  use the page's parts too (`Block`, `Field`, `Segments`, `NumberField`):
  a number is typed with the knobs' entry, and the watt cap is a switch.
- The studio uses the control page's styles and controls (`@pewpew/page`), with
  Tailwind gone, so the two pages share one design system; the studio is dark
  only, as the control page is. `web/` and `studio-web/` are one pnpm workspace
  with one lockfile at the repo root, and `web/src` is laid out by feature
  (`wire/`, `params/`, `stack/`, `design/`, ...), not by layer.
- `examples/tide.look.json` and `examples/mcp-ember.look.json` draw their
  sparks with `particles` and an `ember` palette, not the `sparkle` pattern.
- The engine package is now `pewpew.aura`, and `run --unattended` replaces
  the old unattended-run flag. The page's wire message is `aura`, and
  `observe` and the MCP `engine_observe` tool report the aura state under
  `aura`. The LaunchAgent template is `deploy/launchd/pewpew-aura.plist`,
  label `local.pewpew.aura`. A LaunchAgent installed from the old template
  passes a flag `run` no longer accepts, so boot it out and reinstall it from
  the new one (`docs/unattended-checklist.md` §1).
- Redraw the control page on RA-27c's visual foundations. Text is set in
  Martian Grotesk, with Martian Mono for keys and addresses and Mono's
  digits for live values, as two subset fonts inlined into the page
  (`just fonts` builds them from pinned sources; ADR-020 amendment). One
  token set (`web/src/ui/theme.css`) gives seven type roles, five space
  steps, four surfaces and one meaning per colour: amber only for what the
  room is shown, red for what darkens or removes, neutral focus and
  selection. The deck and the editor are region cards, and headings are
  never smaller than what they head. Every action is a shared `Button`
  (primary, secondary or tertiary, with confirm, busy and an off-with-a-reason
  state that opens a note), `IconButton` or `ToggleButton`; saved looks and
  pattern picks are `Tile`s, modes are `Badge`s, and each `?` is a
  one-at-a-time disclosure under its row. A second press now reads "again
  to …", a changed knob shows ↺ at rest and a changed look "· changed", and
  signs the fonts lack are inline SVG icons. Modulators read by RA-27's
  names: LFO, random, beat, envelope, audio follower, macro and smooth.
  The page grows to about
  225 KB gzipped, under a budget of 230,500 B.
- Reorganize the control page around what each thing is (RA-27b phase 1).
  Saved looks are tiles under a quiet "looks" caption, the first nine, on
  keys 1–9 in file order; past nine, "all N ›" lists every look in the side
  slot. "surprise me" and "vary this" are secondary buttons with signs on a
  row of their own. One save, the header's only primary, shows only while
  there is something to save: one press saves the edits into the look, or
  keeps a made look (a draft, badged ✦ draft, named by its label) under the
  name it offers, and `k` presses it or says why it is off, as it does at
  64 looks. Its ▾ opens "save as new…", which closes once the engine has
  saved; revert, delete, the look's own fade and its place in shuffle are
  behind the look's ⋯. The look's header names a long name whole, on more
  lines. A look of one layer shows no layer chrome but a quiet "+ layer",
  and its on switch, opacity and blend while they are off their defaults;
  the open layer of several is a raised card with its knobs inside it, and a
  main knob names its owner (`decay · fb · base`). The page uses the
  glossary's words: brightness and max, shuffle, cues on, modulators,
  `modulated by ‘breath’ ±0.2 Hz` (+ or − for a modulator that gives a
  level), fade "as saved" or "instant". The top bar is status only, and on
  touch blackout has a row of its own under a brightness slider that takes
  the row's width.
- Tune the control page's type and spacing (RA-27c, tuned 2026-11-06). Text
  is a step smaller for Martian's tall, wide letters: 13 px body, 11 px
  captions and an 18 px look name with a mouse (15, 12 and 20 on a phone),
  each with a whole-pixel line height, and every typed field is 16 px under
  a finger. Spacing comes from what holds a thing, not the thing: knobs are
  12 apart, groups 24, a heading 8 over what it heads, and the wide deck's
  rows 16. Wide with a mouse, "all N ›" and ⋯ end the looks caption's line
  and the tiles fill the card in equal columns; the live look's ● is a pip
  in its tile's corner. On a phone a knob's name has its own line and its
  entry sits beside its slider, controls are drawn 40 px with 44 px
  targets, the looks strip stops on a tile, and the top bar is 44 px tall.
  The brightness's steps, blackout and every knob's entry share one width
  and both edges, each one well with its value at the right. Rows of a list
  share one edge rule, disclosure rows are one height with names at weight
  600 only while picked or open, the look's ⋯ reads as rows ending at the
  column's edge, the colour control drops its well, the deck's ⋯ floats
  over the editor, and the shortcuts button shows ⌘.
- Polish the control page to the pixel (RA-27c, second pass 2026-11-06).
  Every number's digits end on one line, units in a fixed slot on the
  digits' baseline, the brightness's too. A heading sits 8 over what it heads
  whatever is beside it, a phone knob's name 4 over its control, and the
  slot's heads start their text at one depth, a lone layer's path as a
  title. ⋯, ✕ and ? end on the column's edge with the words, and the look
  menu's ? follows its words so its switch ends there too. The deck's ⋯
  opens in the deck, under its row, with a shorter shuffle line; the deck's
  "looks" is a heading; the make buttons take the tiles' columns; secondary
  buttons have a quiet edge, fields keep the strong one; "+ layer" is a word
  in both runs. The open layer drops its card for one indent; a colour's
  parts sit 4 apart; on a phone the looks strip stops flush on the live tile,
  layer rows centre their mix and switch, and the editor's foot fades under
  the deck. Icons draw at 16 px, the live ● at 12, and the side column and
  phone canvas land on whole pixels.
- Make a `save` with a null name keep the running look under the name it
  offers, with a made look's fade, as `keep` did; `keep` is now that save,
  kept for clients outside the package, and the page no longer sends it.
  The aura state's looks carry `offered`, the name such a save gives, and
  each signal its `range`, so a page signs a route's depth.
- Rename engine labels to the glossary's words, ids unchanged: the signal
  ops `walk`, `band` and `knob` read Random, Audio follower and Macro; the
  `modulate` op reads Ripple, so it never reads as a modulator; osc's
  `freq` reads Stripes, band's `gain` Boost, and an envelope's or band's
  `attack` Rise; the blend modes max and min read Lighter and Darker; an
  envelope's help says "pulse" in place of "trigger".
- Run the L1 suite in about 18 s, down from about 27 s on the same machine.
  A test's state files go to a folder that is made only when one is written;
  the render gates, the long simulation runs and the tests' other processes
  run on one process pool beside the tests; and a property draws 50 examples.
  `just test-thorough` draws Hypothesis's default 100.
- Require NumPy 2 or later. The goldens, the port-equivalence proof and the
  effect primitives' float32 output depend on its type promotion rules
  (NEP 50); under NumPy 1, a float32 scalar times a Python float came back
  as float64.
- Name a look's pattern problems by the node they are about
  (`layers.base.nosuch: unknown pattern 'nosuch'`), and a render error's
  status path by the program node that raised (`layers.base.fold`).
- Place the 1M LED Pixel Bar's pigtails where the maintainer measured them on
  2026-11-05: each one leaves the underside 0.15 m in from its end and is
  0.20 m long. The ports were at the bar's ends with an assumed 0.30 m, so
  every data hop, lead and drop the rig report gives for the bar is shorter.
- Keep the aura running when the preview cannot listen, and try the port
  again every 5 s.
- Save and recall a look for a pattern launched by path, by that path.
- Clear the current look when a pattern is picked.
- Ignore a second tap less than 0.4 s after the first on every two-tap
  confirm, so a double tap cannot black out the room.
- Import `pewpew` without loading the sinks or the websocket server.
- Accept a board's mDNS name (`pewpew-1.local`) in a room file and in
  `--ddp`, alongside an IPv4 address. pewpew looks the name up off the
  render loop and again whenever the board stops answering, so a board that
  comes back on a new DHCP address keeps getting frames.
- Refuse pattern parameter values outside their declared range. Previously
  `lo`/`hi` were read by nothing and `{"speed": 1e9}` bound silently, so a
  control surface could never trust that a knob's endpoints bounded what the
  engine rendered.
- Let a `Param` declaration win over an `__init__` assignment to the same
  name. The prototype's materialization loop skipped any attribute already
  holding a float, so a pattern could shadow its own declared default and no
  surface would know.
- Share one canonical (pattern, fixture) table from `pewpew.patterns`, which
  the golden, port-equivalence and liveness tests had each been re-deriving
  from the study runner by hand.
- Keep a refusal free of source paths when it crosses the preview socket.
  `ParamSet.check` supplies the reason (the knob and its range) and `hint`,
  which names the file to widen, stays on the command line — the preview port
  is unauthenticated by design and must not serve the layout of the disk.
- Stop the preview server thread from raising when `stop()` closes the
  listener before `serve_forever` has finished starting. Harmless but noisy,
  and it surfaced as an intermittent unhandled thread exception once the
  socket tests grew.
- Move the preview page's readout out of a viewport-fixed position, where the
  new lever row overprinted it, into the footer row itself.
- Re-verify sections 1–2 and the quick-start cart of the hardware buying list
  against live listings, and add a vendor policy naming which suppliers to buy
  from. The N32R8V devkit and the TSL257-LF photodiode are obsolete, DigiKey's
  N8R8 backorder slipped to 2027-03, and three Adafruit parts went out of stock.
- Accept ADR-005 (pattern authoring model) — the Phase-0 item-2 study
  confirmed the vectorized-authoring bet, conditional on idiom-kit additions.
- Pin every ADR-cited code source to the commit that was actually read, so
  ADR evidence resolves to a fixed tree rather than a moving branch.
- Snapshot 40 of the 53 sources left unarchived by earlier passes; 6 are
  refused by Save Page Now at the domain level and 7 resolve only to snapshots
  predating the read, now annotated as such.
- Require an archive snapshot to be at or after the date its source was read.
  Accepting anything older produced `archive:` fields that satisfied the
  archival rule and evidenced nothing.
- Move the packages to a `src/` layout (`src/pewpew`, `src/harness`) so the
  installed copy is what gets imported; import paths are unchanged.
- Refuse a pattern parameter override that names an undeclared `Param`
  instead of silently creating an attribute nothing reads.
- Retire the JS pattern playground (`preview/index.html` + `verify.js`): the
  engine-backed preview sink renders the real contract, which the
  hand-written mirrors could not express (`setup`/`self.buffer`, both-end
  `bins` clamping, NumPy floor-mod hashing). The upgraded FireSim — an
  original, not a port — is preserved verbatim in `preview/fire-reference.js`
  as the reference for its future Python port.
- Check each file an ADR cites by line, not only its source: `just
  sources` now fails unless an excerpt directory of that source holds a
  file of that name and its LICENSE-NOTE.md names the cited upstream path,
  so another upstream file of the same name does not count. The 23 cited
  files that had none now have excerpts of their cited lines (from WLED,
  FastLED, LedFx, Fadecandy, led-control, marimapper, HyperHDR, projectMM,
  the UPXL expander, Home Assistant and FPP), so the known evidence gaps
  fall from 32 to 29, all archive snapshots and pins.
- Save looks as layered looks, looks file version 4, and refuse a version 3
  file: move it aside and save the looks again. A look is its layers, each
  with its pattern node, mix and id, plus its own seed. A pattern node names
  its pattern in its `args`, beside the pattern's params
  (`{"op": "pattern", "args": {"pattern": "wash", "speed": 0.01}}`); a file
  from an earlier `fx` build that put `pattern` beside `op` is refused with
  that key named. Its `signals`, `routes` and `front` load only when empty,
  until signals arrive.
- Report flash safety as unknown (`Metrics.flash_safe` None) for less than
  a second of frames, where the count could pass a fast strobe; `observe`
  prints `flash_safe: unknown` and warns.
- Name `observe`'s engine time from the first frame to the last `span`
  (it was `seconds`, beside a different `metrics.seconds`), and list the
  running look's layers with their blend, opacity and switch.
- Take a knob's address in `run --param` (`layers.base.plasma.speed=1`),
  as `observe --json` and the page name it, and name a refused value by its
  address there too, as the socket does.
- Name the part that raised a render error by its path on the wire:
  `status.path` (`layers.base.comet`) replaces `status.pattern`. A layer's
  own opacity, blend and enabled records carry `node: ""`, not null.
- Name the failing pattern by its name in the page's status line
  ("The room is pulsing red: wave failed", "Layer top (sparkle) failed").
- Hide a lone layer's opacity, blend and enabled on the page, where they
  only repeat the master and the blackout or black the room; with more than
  one layer, show each layer's knobs under its id. Reset all still resets
  them.
- Answer a `set` of an address that names no knob, such as
  `layers.base.speed`, with every address, so the right one
  (`layers.base.comet.speed`) is in the reply. A color part's address
  (`layers.base.wave.color.h`) is found for a route, and a `set` of one says
  to set the whole color.
- Run the command line's pattern as a stack of one layer, `base`. Its seed
  comes from `--seed` and the layer id, so comet, fire and sparkle draw a
  different random stream under `run` than before, the same on every run.
- Reserve `pattern` as a param name: a look's pattern node uses it to name
  its pattern.
- Rework the control page's editor into three blocks. The look comes first:
  its name, a dot while it is changed, `revert` (two presses), `save…`
  (the name box, save or overwrite, delete, and boxes for `include master`
  and `in idle cycle`, the name checked as it is typed, and save and delete
  off with the reason while a trigger holds a look), then its front knobs
  and its signals, folded. Then `layers`: a lone pattern as its pick (`[`
  and `]` step it, but not over unsaved edits), else a row per layer, a
  lone program's too, with what it runs in a few words (`custom · 5
  steps`), its blend and opacity at a glance, the chevron first, the full
  chain inside, and a program's pattern pick behind `replace with
  pattern…`. Then the picked layer's knobs under `layer <id>`, a section
  per node by its id and op (`bars · Oscillator`), with a reset all of its
  own. A front knob names only its layer, or its signal; its node too only
  where two would read alike.
- Make the page quieter and steadier. A knob's help shows while it has
  focus, over what follows it, and describes it always; a moved knob reads
  `now 0.48` and `moves with swell, ±0.15`. Every entry ends at one edge
  (the unit keeps its column), the dial's too. Opacity, and a color's
  saturation and brightness, read as percents. On touch a slider moves by
  its thumb alone, so a swipe that starts on its track scrolls; its label
  and entry share a line over a full-width slider. Controls' edges hold
  3:1, a focused slider thumb is ringed, segments are a touch wide, labels
  are lowercase, and the editor's blocks are spaced and headed.
- On the deck, `surprise` leads; over unsaved edits it and `like this`
  take two presses; the three keep focus while the engine works, and one
  that is off says why when pressed. The deck's `?` also says what ↻,
  dashed and the dot mean; ↻ shows only when some looks are out of the
  idle cycle, and the saved looks are one tab stop (arrow keys move). The
  fade reads `fade: 2 s` and ends the made looks' row (by the look's name
  on a phone). The top bar keeps the master whole and lets the name give
  way, and its `IDLE CYCLE` and `ARMED` tags say what they mean when
  pressed. A render error turns the health chip bad, sits on a panel with
  a red rule (its engine text under `details` on touch), and a lost
  connection's banner lies over the stage instead of pushing it down.
  Esc closes a panel, and `+ layer` says why it is off at 16 layers. Every
  group on the page has a name, and a color's hidden input and strips'
  tracks are out of the accessibility tree.
- Show the add-layer catalog's cards as a label and the gist of what each
  does, the rest behind its `?` and an op's other examples behind `more`;
  the op shelves sit under `effects (advanced)`, and `mix` is `combine two
  fields`. Give the gallery patterns, `feedback` and `modulate` first
  sentences that say what they look like, and spell `color` alike.
- Draw a room's LEDs on the page at least 1.5 css px across, with a glow
  that reaches a quarter of the way to each fixture's nearest neighbour (at
  most 8 css px), so a bar reads as a bar of light, not a dotted hairline.
- Caption the oscillator's `sync` "Drift", and say in plain words what it,
  the palette's `cycle` and modulate's `amount` do.
- Name made looks by their count in the run (`surprise 3`, `variation 2`),
  not their seed, which the look keeps; a keep under a taken name counts on
  past it (`surprise 4`). A pick on one layer of several edits the running
  look, which stays current and changed, instead of leaving it.
- Rework the page after the second UI review. A knob's dot now means
  changed since the look was saved, and its ↺ (shown under a pointer or
  with focus) puts back the saved value, then the default; `reset all` is
  `defaults`. A changed look saves back into itself from its header (`save`,
  two presses) beside `revert`; `save as…` names a copy, keeps the look's own
  fade unless changed there, and the deck's fade sets recalls only. `keep`
  keeps made looks; a variation is named after its look (`tide variation 1`).
  The open layer row holds its knobs; a lone layer shows no order or remove;
  the bottom layer marks blends that show black. A layer reads what it makes
  (`Oscillator · Palette`) and its chain follows its wiring; a signal's
  section names its kind and what it moves. Cues are one noun (`arm cues`;
  cue buttons only while armed). The add-layer catalog groups effects on the
  layers below apart from parts, sets an arg's name as a token, drops `more`,
  and shows `?` only when it adds something. Two-press buttons keep their
  width armed and read `REPLACE?`-style; armed is always red. The deck's `?`
  lies over the editor; a phone's knob keeps its label and its − clear of
  the reset, and a tap on its label tells its help; a phone on its side
  scrolls deck and editor as one. Focus survives moves, reverts, panels and
  a lost connection; number keys recall nothing over unsaved edits. A strip
  draws as a band of bars. Help, gists and health say what they mean in
  plain words; the oscillator's `sync` reads `Travel`.
- Rework the page after the third UI review. The deck groups its rows
  (the saved looks, the made looks, the cues, then the master with the
  recall fade and blackout) and ends each with its `?`; on a phone the
  master is laid out as a knob is and nothing slides the deck sideways. A
  look's chip or number key recalls over unsaved edits only on a second
  press, as surprise and like this do (`DROP EDITS?`), and the deck's note
  closes on Esc or a press outside it. `arm cues` keeps its name and shows
  its state pressed. A new look joins the idle cycle when every other look
  is in it. A knob's value and unit share one box, so every entry ends at
  the column's edge; its help is behind a `?` on both pointers; − and +
  from a value between steps go to the nearest step. A color's parts are
  laid out as knobs, their strips as long as the sliders', and a chosen
  option is a neutral fill: amber marks what plays. A look of one layer
  opens with it; of more, the rows start closed so the stack reads at a
  glance. An open row leads with ▲ ▼ and remove, then its mix, then what
  it runs (its wiring only when that says more than the row) and its node
  sections, folded and in wiring order; a palette's stop editor waits for
  a marker. A moved row stays where it was in the slot, and a row opened
  by hand scrolls into view. Sections name their node or signal first,
  then its kind, what it reads (`splash · envelope ← kick`) and what it
  drives (`hiss · sound → shift · pond`); `moved by` names the signal's
  kind; a knob whose caption another node shares names its node, and the
  look's own knob is called by its name with what it drives. The look's
  header stays at the slot's top; `save as…` offers a name no look has
  and saves a copy, while a taken name overwrites; the look's own fade
  (`own fade: 4 s`), its place in the idle cycle and delete sit behind
  its `⋯`. While a cue holds a look the editor says so and waits, inert.
  A render error just after a knob was set names the knob and offers its
  value back. A panel takes focus to its title, so Esc closes it. Stage
  alerts are drawn alike, amber while retrying. The catalog puts each
  card on one shelf, adds `trails and glow`, and leaves out below, prev
  and pattern; twist names the op to use on each map; layout tools say
  how to blink a bar. Help and gists drop their jargon; sparkle's speed
  reads `Sparks` and the palette's cycle `Slide`.
- Rework the page after the fourth UI review. On a phone the deck is three
  rows (the looks; surprise and like this; blackout and the master's
  steps, no slider) and the editor keeps a floor while the stage gives
  way: at 390×844 the editor has 366 px, not 209. Arming the cues, the
  fade a look takes (`fade: each look's own`) and what each row does wait
  behind the deck's one `⋯`; cue buttons show while armed and keep their
  width counting down, the last outcome on their line, and the top bar
  keeps the master beside a short `ARMED`. `keep` moves to the look's
  header, the one-press save while a made look plays, as `save` (now
  drawn as a button) is while a look is changed; on touch `revert` and
  `save as…` wait behind the header's `⋯`, so it stays one line. A
  knob's `?` never moves under a finger: the reset shows before it, only
  once the knob has focus. Its help opens under its line, by the `?`. A
  touch steps − and + on a tap alone, so a swipe that starts on one
  scrolls and changes nothing. Every entry is one width, so sliders end
  together, and a step at its limit dims its glyph, not its frame. A look
  that lists no front knobs shows the ones the engine picks for a made
  look. A row opened by hand scrolls into view once its body has height.
  Focus that a cue's hold, a recall or a reconnect takes away goes to the
  hold's note or the look's heading, and back to the knob when it can;
  `put back` takes it to the knob. A phone on its side scrolls the side
  panel again. An open row's head stays under the look's header, a layer
  of one section shows its knobs loose, and a switched-off layer's knobs
  in front dim and say so. A switch puts its words first and drops
  `on`/`off` (`recalling it sets the master too`). Catalog cards are
  raised chips (`+ oscillator`) and a parts card says what it acts on
  (`on a new oscillator`). Health leads each row with its status and
  folds its figures, a phone's own row first. `defaults` reads `reset to
  defaults`, `params` reads `knobs`, and Tab into the patterns lands on
  the one playing.
- Rework the page after the fifth UI review. On a phone a knob's label is
  its name over what it belongs to, and its `?` keeps one column in every
  kind of row; every entry has one unit slot, so a column's digits end
  together. A stepper at its limit keeps a whole frame. The deck's `⋯`
  follows blackout in every run, so the master's steps end at the column's
  edge; on a narrow side panel blackout keeps its width; on a phone on its
  side blackout moves to the top bar. The top bar's tags are one height,
  `BLACKOUT` takes the others' place on a phone, and a tag's note lies over
  the stage and closes on Esc or a press elsewhere. On a phone a render
  error's bar is one line (`boomer failed · put back`), and health marks
  the render loop bad while a layer fails. A pattern file's chip reads as
  chosen (`your own file, not in the gallery`). Layer ids share a left
  edge, a row's summary keeps to one line, an id is amber only while its
  row is open, and an open row's head pins under the look's header however
  tall, drawn over the knobs, with focus never under either. A color's or
  a stop's parts sit on an inset; catalog names share a column; panel heads
  pin. A dial marks where a route moves it. The look's signals sit under
  `moves on its own`; a blend's `?` says what every mode does. Saving,
  keeping and deleting a look are announced; a made look has no dot until
  kept; a recall that waits over a cue's hold shows no edits; the phone's
  `⋯` opens its forms in view, the copy apart from the look's settings
  (`keep master 60% with it`); Esc closes save as…, the settings, a knob's
  help and a typed number; a run without a looks file says a look of
  layers is not kept; a lost laptop says how to recover. Controls in notes
  keep the controls' face; an off select looks off; health prose is
  prose; the pattern row is toggle buttons; knob names read in lower case,
  sections are named, and a knob shown twice says `also above`. Help,
  gists and refusals say what a person sees: `pattern`, not field; `the
  aura`, not the engine; `how long a trail lasts`; `upward`; `along the
  strip (u)`; one spelling (`center`, `gray`, `neighbor`); `play`, not
  recall. A gist names no args, and a knob's help no longer repeats its
  unit; the palette's help says to press a dot.
- Rework the page after the sixth UI review. On a phone `BLACKOUT` never
  shrinks below its word: the master's readout drops its word first. A
  phone's knob keeps its label's whole line, so the reset never cuts the
  name, and its slider and entry share the line under it; an angle knob
  lays out as a number knob, with a track where the row has room. An edit
  to a made look gets the dot and guards surprise, `more like this` (was
  `like this`, armed `VARY EDITS?`) and the looks, and the deck's note
  follows whichever press is armed; the made look's form keeps it (`keep
  as`); `save master 70% with it`. The catalog leads with `ready to play`
  (patterns, sources, effects), card buttons share one width, and while a
  cue holds a look its cards wait. Every slot panel heads like the look; a
  held look's chip, the lead button and section titles read plainly; the
  ↻ marks the fewer looks; the idle cycle is a `↻` on touch and says when
  it starts, how long each look plays and how to take over; each cue says
  what it fires, and a signal-only one reads `sent`. A blend's `?` leads
  with the chosen mode, the rest behind `all modes`; the chain line names
  steps by what they do; what moves the knobs comes after the layers.
  Health leads with why and what to do, figures under `details`. − and +
  step on assistive tech's click; an armed button, a revert and a layer's
  move are announced; Esc in the deck's `⋯` returns focus to it; the `?`
  list names the arrow, Alt and Backspace keys. Made looks call their
  signals `sway`, `drift` and `music`, and help says `center`.
- Rework the page after the seventh UI review. The idle cycle waits while
  the look has unsaved edits, and a look's own fade is stored alone
  (`fade`), so edits never block it. The master is one control laid out as
  a knob, with its own `?`; on a phone blackout and its steps share the row
  half and half, as surprise and `more like this` do, and `⋯` ends the
  looks' row. While a cue can hold a look every chip keeps room for `↩`, so
  a hold moves nothing; wide, the looks scroll inside three rows. A fade is
  a bar along the chip's foot, a held look is filled, the look it returns
  to has a muted edge, and a look left out of the idle cycle is a slashed
  `↻`. The `⋯` holds arm cues and the fade, and names only the marks shown;
  the cue row says what each cue does (`tells the pattern, no look
  change`). What moves a knob waits behind its `?`, its depth in the knob's
  unit; the `?` also shows a knob above (`front`) or takes it off, and a
  replaced node's front knob gives way to the new one's first. `↺` only
  reverts to the saved value. A changed layer row and node section get the
  dot; each row has its own opacity slider. An angle is a slider with a
  compass. On a phone every slider spans the column, and a swipe that
  starts on a thumb and goes up scrolls. The editor gives way before the
  stage; the room fits under a banner; the deck's note dims the editor.
  Palette stops remove in two presses and say why at their limits; a step
  says where it left a value; focus returns to its knob after a reconnect;
  a tap picks a bar in layout mode and a second blinks it. Help and gists
  name what a person sees (`new stripes → mirrors…`, `Chase`, the
  lissajous's `loops across`), and made looks name their signals plainly.
- Rework the page after the eighth UI review. `save as…` takes focus to
  the name box, its text selected, and keys typed in a look's form never
  reach the shortcuts. A layer's opacity has one home: with a mouse its
  row's slider, the rows' sliders and readouts in shared columns; on touch
  its open row, each row's summary on a line under its id. Made looks and
  looks without a front no longer show a layer's opacity in front. A
  knob's pin (`⤒`) shows it above in one press, takes it off in two, and
  says so. `↩` sits in the chip's corner, so arming cues moves no chip;
  the looks grid grows to a fifth of the screen with a scrollbar. The cue
  row keeps what each cue does and shows an outcome for a few seconds (on
  touch the descriptions wait behind a `?`). A recall that waits for a fade
  makes the editor wait, inert, and says which look is next. Delete is off
  for a look a cue plays and says why; settings refusals are alerts; save
  arms as `SAVE FAILING?` while a layer fails. A card is one borderless
  button with its gist, a press while an add waits does nothing, and a
  layer adds above the picked one (`add above base`). Patterns go by their
  doc's title (`color plasma`, `sound bars`, `spinning ring`). A run with
  nothing behind the deck's `⋯` has none, and on touch the master has its
  own `?`. A narrow window with a mouse stacks, and a 320 px phone puts a
  knob's label on its own line. Every `details` has a chevron; headings
  step title, block, row; prose is at least 12.5 px; a hue shift has no
  compass and an angle's is a dial; signals are `sway` and `swell`, a
  signal `on` its trigger. Blackout, restore and a removed layer are
  announced; the look is one region, its blocks `h3`, its rows `h4`.
  Help says what a person sees (`fall back`, `which way the bands cross`),
  freq has no `/unit`, and strip refusals drop `(u)`.

### Removed

- Remove hand-written Python patterns (ADR-025): `run file.py`,
  `file.py:Class`, `--pattern-dir` (on `run`, the `fx` verbs, `verify
  looks` and `push`), pattern-file hot reload (`Reloader`), op
  registration from a loaded file, and the control page's rescan of a
  patterns folder. A pattern goes by its gallery name alone
  (`pewpew.load`).
- Remove the pattern gallery and every way to run it (ADR-025): the eleven
  patterns of `pewpew.patterns`, `pewpew.load`, the `pattern` op and
  builder, a layer that runs one pattern directly, the aura's `pick`
  request with the page's pattern picker and "replace with pattern", the
  `pattern` and `patterns` fields of the `aura` state, the catalog's
  `patterns` section, fixture units (`Pattern.units` and the per-fixture
  gather), `render_sequence`, and the top-level `pewpew` exports. A look
  that names op `pattern` is refused as any unknown op is.
- Remove `run`'s launch pattern and its flags: the `PATTERN` positional,
  `--param`, `--units`, `--no-reload`, `--looks` and `--map auto` (the
  pattern's study fixture), with `auto` from the `fx` verbs and the MCP
  tools.
- Remove the page's operator and editor views; Layout mode replaces them.
- Remove the pre-engine harness pattern contract and the fleet-simulation
  stub from `src/harness/`.
- Remove `Pattern` (ADR-025 amendment). A layer's `Renderer` runs a
  `BoundProgram`, one program bound to the map, whose `Buffers` hold its
  ops' state and the last frame and lock them read-only while it renders.
  Gone with it: one class made per program, the renderer's own param set
  (`Renderer.params`, `params=`, `name=`), the class checks on buffer and
  param names, `ParamSet.hint` (a refusal no longer points at a source
  file) and `Param.owner`. A contained failure in an op's `advance` names
  the phase `advance`.
- Remove the authoring study's prototype (`bench/bench_authoring.py`,
  `bench/authoring/`); its report stays in `bench/results/`.

### Fixed

- `observe` and `push` give the websocket handshake its own bound
  (`OPEN_TIMEOUT_S`, 5 s) in the shared client, apart from the read timeout. A
  short timeout, or a slow network, no longer reports a working engine as
  unreachable.
- A restart after a watchdog stall no longer alternates between two looks that
  both hang: the stall marker names the looks that stalled, the restart
  skips every one of them, and it starts the current look again only when
  all have stalled.
- Name a layer added without an id by its `out` node also when one of its
  args is refused, so the refusal names `layers.<out>…`, not `layers.layer…`.
- Give an out-of-range op knob or layer mix knob in a look that does not
  decode its default as the problem's `example`, as a route's knob had.
- Let a `LayerError` cross a process pool: it unpickles with its layer and
  reason.
- Point the control page's "not saved" note at `run LOOKS`, not `--looks`.
- A number entry's − and + answer a finger over the full 44 px, as a
  bordered button does; they were 2 px short.
- A bordered button or tile answers a finger over the full 44 px, not 42.
- Refuse JSON that nests arrays and objects more than 64 deep on every
  platform (`pewpew.jsonfile.MAX_DEPTH`), before the parser runs. Python's
  parser stops only when the machine stack runs out, so before, the same
  catalog file, arrangement or studio body was refused on macOS and read on
  Linux. The studio answers such a body with a 422 of code `too_deep`, and
  a catalog file or arrangement gives the `too_deep` issue.
- Name the knobs of a pattern file whose class is a program (`class
  Tide(ProgramPattern)`) `layers.<layer>.<node>.<arg>` in a look's checks,
  a push's checks and `fx explain`, as the running aura names them, so a
  set or route at an address the page shows is no longer refused.
- Refuse a look's fade, master or cycle that its param refuses when the
  look is made (`look(...)`, `Look`), not first at the codec or at recall.
- Start a layer that is enabled again with one frame's time step, not the
  whole time it was off, so a sparkle or fire layer no longer lights every
  pixel on its first frame back.
- Clip both inputs of the `screen` blend to 0–1, so two layers above 1 no
  longer darken each other.
- Keep the control page's document from scrolling under its fixed frame: a
  color's hidden input far down the editor made a wheel or a swipe over the
  canvas or the deck slide the whole page up into a black void.
- Say `"x" is not a number` when a number entry turns away a typed letter,
  instead of nothing, and send nothing for it.
- Word the `highlight` blend's line: "Lights only where what is below is
  already lit".
- Show the error frame under `--unattended` when the failing layer is
  left out and the layers still running only blend over it (multiply, min,
  subtract or highlight) or have their opacity at 0, instead of a black
  room.
- Contain a program's mask of the wrong shape, such as one number from an
  op a pattern file defines, as its layer's error frame; it raised out of
  the frame loop and ended the run.
- Zero a pattern node's last frame when a room map reload rebinds its
  layer, so a program around a trail pattern renders on a map of another
  size instead of failing every frame, and its trail starts again.
- Put the op registry back when a pattern file fails to load, so a room
  map reload still binds the layers that run the last good version's ops.
- Refuse `layers` and `signals` as a layer's id: a layer named `signals`
  drew the same random streams as the look's signals of the same ids.
- Measure `frozen_fraction` over spans of 0.1 s whatever the fps, so a
  slow wash rendered at 30 or 60 fps no longer reads as frozen, and `vary`
  no longer drops a slow look as frozen.
- Count grey as no colour in `palette_spread`, as `hue_clusters` does: a
  look with no palette read as hues in balance.
- Count a luma swing of exactly 0.1 toward a flash, as WCAG's "or more"
  says; float32 read it a hair under.
- Name signals, routes and the front list in a look diff (`fx compare`,
  `look_compare`): a change to modulation read as no knob moved.
- Give one mistake one problem code wherever it is written (ADR-023): a
  knob address that names nothing is `bad-ref` in a set as in a route or
  a front list, and a seed below 0 is `out-of-range`. A palette's preset
  or stop, too many layers, nodes, signals or routes, a repeated front
  knob, and a layer's `alpha` on a colour node are each named at their
  own path, so the fix names the knob, not the whole look.
- Give each problem's `fix` in `fx check --json`, `look_check`'s
  structured content and the command line's text, not only in the MCP
  error text; a fix no longer repeats a list its reason gives.
- Find an op by its label in a did-you-mean (`oscillator`, `kaleidoscope`,
  `multiply`), and in `fx show`.
- Refuse a JSON object that names a key twice, such as a copied node,
  which replaced the first without a word.
- Refuse a layer's program checked as a look (a catalog example's JSON),
  with the look that holds it as a layer.
- Read a `.look.json` file as a looks file in `fx check`, `fx render`,
  `verify looks` and `push`, as `run --looks` does: a single look in a
  file passed the gate and the aura refused it. Both now say how a looks
  file wraps it.
- Report a crossfade in the aura state (`fading`, `progress`) and in
  `observe` (`faded`, with a warning), and name the fade a pushed look
  runs, so frames measured during a fade are not read as the look's.
- Check a set's address form in a dry run (`engine_set`), and say what a
  dry run of `push`, `engine_apply` and `engine_set` checks.
- Refuse a `keep` address that names nothing as a problem with a path,
  code and did-you-mean.
- Give each candidate of `fx vary` and `look_vary` the taste gates it
  fails (`taste`), and never give the varied look back unchanged: a seed
  whose changes all fail the content gate gives no candidate.
- Serve each section of the authoring guide alone over MCP
  (`pewpew://docs/authoring/9`), and point agents at sections 9 and 10.
- Name the presets a palette takes in its shape refusal, every key in
  the idle cycle's, and every verb and exit code in `fx --help`.
- Save a knob moved in a pattern file whose class is a program (`class
  Tide(ProgramPattern)`) on its layer's pattern node, as `"waves.freq":
  9.0`, and start it there on recall: a save, the page's "changed" and
  "like this" lost it. `verify looks` probes that program's knobs and
  `fx explain` lists them; both skipped every one.
- Keep each color's hue when a palette's `shift` turns it past what LEDs
  show: it gives up chroma, as the gradient's own colors do, where
  clipping each channel moved hues by up to 19°. The shift turns in
  steps of 0.5°.
- Make the same surprise from the same seed in every process: an op a
  pattern file defines no longer joins the grammar, and one registered
  after the first look no longer leaves the grammar stale.
- Say which `--map` to run with when the looks file's current look cannot
  run on the map `run` takes from its pattern (`run comet --looks
  tide.look.json`), and log a look the stack refuses without a traceback.
- Keep a layer's opacity, blend and enabled switch through a pick on it, so
  a mix change sent while the pick loads still applies.
- Read a NaN coordinate as 0 in `bins`, `sample2d`, `pewpew.color.sample`
  and the `sample` and `deposit` primitives on every platform. On x86-64 a
  NaN cast to an index raised IndexError, so a pattern that divided 0 by 0
  showed the error frame there and not on a Mac.
- Keep the effect primitives' output float32 when an argument is a NumPy
  float64 scalar, such as `kit.wave(...)` or `np.sin(t)`: a moving sphere
  centre no longer turns the frame float64 and the room red.
- Convert to and from OKLab with element-wise sums instead of matrix
  products, so a palette's table is the same bytes whichever BLAS NumPy
  uses. The OKLab module is now `pewpew.color.lab`, so the `oklab` function
  no longer hides it; `pewpew.color.oklab` is the function, as before.
  `pewpew.metrics` uses it instead of a copy of its own.
- Give the same metrics for the same pixels whatever the memory layout of
  the frames passed to `measure`.
- Name the same reserved param in every process when a pattern declares
  several.
- Fail a golden comparison on a NaN output or baseline; NaN passed every
  check.
- Refuse a looks file whose cycle `idle` or `each` is an integer past
  float range, or whose JSON holds a number past Python's digit limit,
  with a problem instead of a traceback (`run --looks`, `fx check`).
- Clamp `bins` and `sample2d` before the `int32` cast, so a far or
  infinite coordinate gets the edge index on every platform instead of an
  undefined cast. Inside 0–1 the result is unchanged.
- Keep file paths out of every error text that reaches the page.
- Keep the test suite out of the real audit log.
- Apply `ParamSet.set` to the running pattern.
- Refuse a param value at the REPL with the refusal text instead of
  `OSError`.
- Reset a param to its exact default, and leave a color's other parts alone
  when one part changes.
- Fit the page to a phone in landscape and inside the safe area, and raise
  the armed and muted text to WCAG AA contrast.
- Keep digit and bracket shortcuts from firing while a control has focus.
- Answer a repeated `Host` or `Origin` header with 403 instead of a
  traceback, and keep one malformed board reply from freezing health.
- Collect the Wi-Fi bench tests in a fresh checkout: pytest now puts the
  repo root on the path, so `tests/test_bench_wifi.py` can import `bench`.
- Make the coordinate arrays read-only inside `render`. Locking the buffer
  registry alone left them writable, so an in-place write corrupted the
  caller's mapping permanently instead of failing.
- Return a frame that does not alias the pattern's previous-frame buffer, so
  a sink working in place cannot destroy every trail pattern's state.
- Clamp `bins` and `sample2d` at the lower edge, not just the upper. A
  negative coordinate produced a negative index that wrapped to the far end
  of the array and returned another band's or cell's value silently.
- Refuse a buffer name that already exists on the pattern class. Declaring
  `buffer("render", n)` shadowed the hook, and `buffer("_buffers", n)`
  replaced the registry mid-bind and escaped containment.
- Reject a frame whose dtype is not float32, which otherwise left
  `pattern.pixels` disagreeing with the spec the registry tracks it by.
- Refuse time moving backwards, matching `FakeClock`. A negative dt made
  `fade` return a factor above 1, so trails amplified to white.
- Stop rendering from a pattern whose `setup` raised, instead of continuing
  from half-initialized buffers as though the bind had succeeded.
- Keep preview lattice cell colors attached to their cells through the depth
  sort — colors were being read from pre-sort indices.
- Restore display gamma in the preview, which was crushing low-end glow to
  black.
- Make the preview's sdf3d `spin` parameter visible as an end-over-end
  tumble — spinning about the torus symmetry axis is a mathematical no-op.
- Print the browser preview's URL. It was only ever logged at INFO, and the
  runner configures no handler, so `--preview` told the user to open a page
  and never said where.
- Keep the engine's own log output off the terminal while the ANSI sink owns
  it. A pattern that raised logged a traceback straight through the sink's
  cursor-rewind block, permanently desyncing it so every later frame
  overwrote the wrong rows. Records are held and replayed on exit.
- Stop the error status line from reading `None`. It tested
  `renderer.error` and then formatted it as a second read, so a pattern that
  recovered in between rendered the string "None" in red.
- Reserve the status line's row in the ANSI height budget. A tall map filled
  the terminal and the extra line scrolled the block one row per frame,
  walking the display up over the scrollback.
- Deliver the last frame of a bounded `--frames N` run. Teardown discarded
  whatever was still in the sink's mailbox, which was usually frame N.
- Drop the previous connection's frame buffer when the preview page
  reconnects. Against a larger mapping the redraw read past the end of it
  and left dots frozen at their old color.
- Give each thread its own temporary file in `write_atomic` and the
  render cache, so two MCP tool calls that render or draw the same look
  at once no longer lose a write or warn that the frames are not cached.
- Render a look on side A of `fx compare` and `look_compare` as the render
  on side B was, when B alone is a render. It rendered with the default
  map and seconds, so the two sides did not compare.
