# Changelog

All notable changes to pewpew are documented here, per
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). The project
is pre-release; work accumulates under Unreleased until the first shipped
series (batch mode).

## [Unreleased]

### Added

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
  containment that shows a pulsing-red error frame and keeps the show
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
  time is nominal schedule time (ADR-010 amendment), so a live show renders
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

### Changed

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

### Fixed

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
