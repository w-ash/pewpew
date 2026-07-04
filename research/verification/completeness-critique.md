# Completeness critique — Phase 4 verification

- critic: completeness-critic
- date: 2026-07-03
- scope: whole research pass — 13 topic docs (RA-01 … RA-12 + RA-01b: headers,
  verdicts, open questions), architecture.md §5–12, ADR-000 … ADR-013,
  SOURCES.md modality mix, plus three targeted 2025–2026 web currency sweeps.
- question asked: what would make a future dev distrust this research?

## Overall assessment

The pass is trustworthy at its core: research is dated same-day (2026-07-03),
verdicts carry dates, 76 `NEEDS-VERIFICATION` tags are honestly placed, every
topic doc ends with open questions, and §12 exists precisely to catch
unverifiable claims. The defects found are (a) two empirical assumptions ADRs
lean on that never made it into §12, (b) four subsystems pewpew will need that
no RA covers, and (c) a small number of currency and modality soft spots. None
invalidates an ADR; two should become bench items before Phase 1/2 hardens.

## 1. Topic gaps (subsystems no RA covered)

- **OTA/field-update story for the custom tiers.** Phase 4 (§11) commits to
  pewpew receiver firmware (ESP32-S3) and a CircuitPython wearable runtime;
  ADR-004 and ADR-008 contain zero mention of how deployed units get updated,
  rolled back, or recovered from a bad flash (grep: no `OTA`/update hits in
  either ADR). RA-08 shows the pass knew updates matter (ESP8266 two-step
  `_min` OTA pain [S356]). Sweep 3 (below) confirms this is well-trodden
  ground (WLED integrated OTA + multi-device update scripts since 0.13;
  esp-web-tools powers WLED/Tasmota one-click installers; esp-idf dual
  OTA partitions), so no new RA is needed — but the dependency should be
  written down.
- **Control-plane security/auth posture + multi-user conflict semantics.**
  §5 exposes HTTP+WS JSON tree, OSC, MIDI-learn, and mDNS with no auth
  discussion anywhere in the tree (grep confirms; "auth" hits are all
  "author"). Likewise §5's WLED-style server-push-merged-state implies
  last-write-wins between concurrent controllers/editors but never says so.
  Field norm is unauthenticated-LAN (WLED default), which is defensible — but
  it is currently an undocumented non-decision rather than a decision.
- **Show/project persistence & pattern-file versioning.** Presets/playlists
  and live-vs-persisted split are covered (§5, RA-12), and patterns are
  "portable, self-describing documents" (ISF-style, ADR-006) — but what a
  pewpew *project* on disk is (patterns + fixtures + calibration CSVs +
  presets, versioned and migratable across engine versions) is nowhere
  addressed.
- **Thermal practice.** RA-03 covers the electrical half (injection, fusing,
  level shifting) but no doc mentions heat at all (grep: zero
  thermal/derating hits in RA-03/RA-08): strip derating at sustained full
  white, PSU thermal headroom, enclosed-channel diffuser heat. Wearable
  durability, by contrast, IS covered (RA-09 has a real
  connectors/strain-relief/wash section) — the gap is portable/room tiers.
- **Palette/gradient subsystem.** Palettes are a first-class creative
  primitive in every surveyed system (WLED's 800+ palette editor [S002],
  FastLED gradient palettes, RA-12's Angus finding names palettes "the unit
  of visual taste") — yet no ADR decides pewpew's palette model, and
  architecture mentions palettes only as enumerable entities in §5.
- **CI for golden-frame tests** — checked, NOT a gap: §8 mandates
  golden-frame tests from day one with the pytest-mpl baseline+RMS model
  [S518] and routes the ANSI sink through ssh/CI; the pure render core makes
  headless CI trivial. Nothing to add.

## 2. Evidence-modality gaps

Modality mix in SOURCES.md is healthy (88 code, 79 docs, 41 forum, 33
article, 21 product, 9 spec, 8 datasheet, 1 video), and most forum sources
are issue trackers (primary evidence, not hearsay). Residual soft spots:

- **[S412] (Seeed forum, single hobbyist's BLE-current measurement) is
  load-bearing for the wearable radio bet** (ADR-013 / §10: "measured
  best-in-class BLE current [S412][S416]"). One careful measurement, but one
  person's rig; Nordic/Espressif datasheet sleep/RX currents or a vendor
  power-profiler citation would corroborate it cheaply. The direction of the
  conclusion (nRF52840 ≪ ESP32 for BLE idle) is not really in doubt.
- **WLED-MM performance claims ("50–60% faster than upstream, 25–45 fps on
  complex 2D") are fork self-description** [S004][S005] — vendor-marketing
  modality. Not ADR-load-bearing (colors RA-01 verdicts only); acceptable,
  but should not be promoted into synthesis without a benchmark.
- **HD107s 27 kHz PWM / 40 MHz clock figures are vendor datasheet/product
  claims** feeding the ADR-013 buy list [S101][S102]; RA-03's open questions
  already ask for community measurements — the honesty is there, but the buy
  decision should carry that caveat forward (it currently reads as settled in
  §10).
- **Pixelblaze protocol/editor internals rest on the MIT client
  implementation and secondary docs** because electromage.com/docs is an
  unfetchable JS SPA — flagged independently in RA-05, RA-11, and RA-12. A
  five-minute human browser read would upgrade three docs' worth of
  [NEEDS-VERIFICATION]s; the cheapest single modality fix available.
- **CIE-L\* linearization correctness cites maker blogs** [S059][S060][S061]
  where primary literature (CIE publications, Poynton) exists. Claim is
  uncontroversial; upgrade is optional polish.

## 3. 2025–2026 currency sweeps (3 run, targeting identified gaps)

- **Sweep 1 — ESP32-C5 as receiver.** RA-08's variant guidance covers
  classic/S3/C3/S2/P4 but never mentions the C5 (dual-band 2.4/5 GHz
  WiFi 6), which is in mass production and requested in WLED (issue #5020,
  open since 2025-10, no support landed). Not a buy-list change today — no
  firmware runs on it — but 5 GHz receivers would directly attack the pass's
  own biggest WiFi worries (§12 item 10 AP capacity; RA-04 jitter findings).
  Deserves a watch-item line in RA-08.
- **Sweep 2 — Matter/Thread.** Zero mentions of Matter anywhere in the tree.
  State of the world: no native WLED Matter (issue #4252 open discussion);
  bridge projects exist (zackelia/wled-matter-bridge; TLED, a Matter-over-
  Thread addressable controller on ESP32-C6); Matter 1.6 is current
  (2026-06). pewpew's HA-first mDNS/push stance (§5) already captures most
  user value, and Matter's light model (on/color/level, no addressable
  effects) can't carry pewpew's surface — so absence is defensible, but the
  control-plane RA should say why it was excluded rather than be silent.
- **Sweep 3 — OTA/fleet tooling.** Confirms the OTA gap is
  documentation-shaped, not research-shaped: WLED ships integrated OTA plus
  multi-device update scripts (since 0.13), esp-web-tools/Improv is the
  ecosystem-standard installer path, esp-idf provides dual-partition
  rollback. Nothing exotic to research; ADR-004/008 just need to state the
  plan.

Sources: [WLED issue #5020](https://github.com/wled/WLED/issues/5020),
[WLED issue #4252](https://github.com/wled/WLED/issues/4252),
[wled-matter-bridge](https://github.com/zackelia/wled-matter-bridge),
[TLED](https://github.com/maui1911/TLED),
[ESP Web Tools](https://esphome.github.io/esp-web-tools/),
[WLED getting started / OTA](https://kno.wled.ge/basics/getting-started/),
[WLED compatible controllers](https://kno.wled.ge/basics/compatible-controllers/).

## 4. Prototype-to-verify list (§12) vs silent ADR dependencies

§12 is strong (12 items, each mapped to requirement IDs and a bench design).
Two ADR assumptions are missing from it:

- **ADR-010 silently assumes CPython can pace a 16.7 ms tick with low jitter**
  (GC pauses, GIL contention with capture threads, sleep quantization on
  Linux). §12 item 1 benches *throughput*, not *pacing jitter* — yet the
  pass's own motion-quality thesis says cadence consistency is what device
  interpolation is hostage to (RA-06, Fadecandy finding), and ADR-010's
  context critiques LedFx's compensated sleep for exactly this drift.
  This is the most consequential missing bench item.
- **ADR-004 silently assumes one stock WLED node sustains 60 fps DDP ingest
  at its assigned pixel count.** Item 3 benches Push skew, item 4 16-bit
  handling, item 10 AP-level capacity — none benches sustained per-receiver
  frame rate/drop behavior on real firmware, which is the day-one Phase 1
  path.
- Minor (note, don't bench): power-limiter current-model accuracy vs an
  ammeter (FastLED constants reimplemented [S413]); BLE parameter-tweak
  latency (item 9 covers file push only); OTA story (see §1).

## Ranked gap list with recommended actions

| # | Gap | Severity | Recommended action |
|---|---|---|---|
| 1 | CPython frame-pacing jitter unbenched (ADR-010 silent dependency) | High | **Benchmark** — add §12 item 13: 10-min soak of the paced loop on Pi 5, record tick-error histogram (p99 vs 16.7 ms) with GC active + audio thread running; gates Phase 1 |
| 2 | Per-receiver sustained DDP ingest on stock WLED unbenched (ADR-004) | High | **Benchmark** — add §12 item 14 (or widen item 10's soak): one ESP32/S3 WLED node, 60 fps unicast DDP at 300/800/2000 px, measure delivered fps/drops |
| 3 | OTA/field-update story absent for custom receiver + wearable tiers | Medium | **Accept-and-note** — one consequences paragraph each in ADR-004 and ADR-008 (esp-idf dual-partition OTA / esp-web-tools for receivers; CIRCUITPY/BLE file drop for wearables); no new RA |
| 4 | Control-plane security posture + concurrent-writer semantics undocumented | Medium | **Accept-and-note** — short "trust model" subsection in architecture §5 (unauthenticated trusted LAN, WLED-style opt-in PIN later; last-write-wins + server-push merge) |
| 5 | Matter/Thread never mentioned in control-plane survey | Medium-low | **Accept-and-note** — 1-paragraph RA-12 addendum: excluded because Matter's light model can't express addressable effects; bridges (wled-matter-bridge, TLED) exist; revisit if native WLED Matter lands (#4252) |
| 6 | ESP32-C5 absent from RA-08 variant guidance | Low | **Accept-and-note** — RA-08 open-questions line: no WLED support yet (#5020); dual-band 5 GHz would relieve AP-capacity ceiling (§12 item 10) — watch |
| 7 | Project/show persistence & pattern-file versioning undefined | Low | **Accept-and-note** — ADR-006 consequence: define project-dir layout + schema-version field when Phase 3 starts |
| 8 | Thermal practice (strip derating, PSU headroom) uncovered | Low | **Accept-and-note** — 3–4 cited lines in RA-03's electrical-practice section next touch; power limiter (req Q-8) already bounds worst case |
| 9 | Palette model undecided | Low | **Accept-and-note** — fold into ADR-005/006 at Phase 1 (palettes as gradient assets addressable in the param tree); RA-12 already carries the taste evidence |
| 10 | Modality soft spots: S412 single-measurement radio bet; HD107s vendor figures; Pixelblaze docs-via-client | Low | **Accept-and-note** — add corroborating datasheet cite for BLE currents; carry HD107s measurement caveat into §10; one human browser read of electromage.com/docs clears three docs' flags |

## Fixes applied

None. This critic's brief permits editing only this report; all recommended
edits above are left to the doc owners. No topic docs, synthesis docs, or
ADRs were modified.
