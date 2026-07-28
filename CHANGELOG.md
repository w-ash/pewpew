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

### Changed

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

### Fixed

- Keep preview lattice cell colors attached to their cells through the depth
  sort — colors were being read from pre-sort indices.
- Restore display gamma in the preview, which was crushing low-end glow to
  black.
- Make the preview's sdf3d `spin` parameter visible as an end-over-end
  tumble — spinning about the torus symmetry axis is a mathematical no-op.
