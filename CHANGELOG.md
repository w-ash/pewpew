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
