# Unscheduled ideas

Unversioned; promotion into a version series file is a deliberate planning act.
The Phase 1–5 entries mirror the build plan (`research/synthesis/architecture.md`
§11) — they're staged here so the backlog only versions what's actually next.

- [ ] **Phase 1 — host engine core**
    - Effort: XL
    - What: Pure render core, pattern contract (§3), typed params, preview + ANSI sinks, hot reload, paced clock (ADR-010), DDP 8-bit to stock WLED (ADR-003/004), golden-frame tests from day one.
    - Why: First end-to-end light on real LEDs; everything later builds on it.
    - Dependencies: v0.1.x Phase 0 gates (throughput, authoring surface, pacing jitter)
    - Status: Not Started
    - Notes: Break into a v0.2.x series when promoted — XL must be decomposed before scheduling. Idiom-kit additions mandated by the §12 item 2 verdict (`bench/results/authoring-2026-07-16.md`): `fade(dt, tau)`, `bins(x, n)`, `sample2d(field, x, y)`, `hash01(x, salt)`; docs for the internal-field idiom, np.where-evaluates-both-branches, and RNG placement; decide whether private per-pixel state buffers become sanctioned alongside `self.pixels` (stumble #17). Add a param-liveness check to the L1 harness: wiggle each declared `Param` across its range and assert the frame sequence changes — motivated by the sdf3d dead-spin discovery (report addendum): neither the authoring surface nor goldens catch a semantically dead parameter when other motion masks it.

- [ ] **Phase 2 — quality pipeline**
    - Effort: XL
    - What: Float32-linear stages 1–6 of §2 (LUT, white point, power limiter, adaptive dither, DDP 16-bit, five-bit-HD via UPXL) + photodiode bench rig.
    - Why: The quality lever the research identifies as the field's biggest gap (ADR-001/002).
    - Dependencies: Phase 1
    - Status: Not Started
    - Notes: Photodiode rig settles §12 items 3, 5, 6.

- [ ] **Phase 3 — control plane, audio, mapping**
    - Effort: XL
    - What: HTTP+WS JSON tree, presets/playlists, OSC + MIDI-learn, mDNS/HA, feature bus + WLED sync out, fixture format + map compiler + marimapper import, three.js preview.
    - Why: Makes the engine drivable and mappable (§5–7, ADR-007/009).
    - Dependencies: Phase 1
    - Status: Not Started
    - Notes: —

- [ ] **Phase 4 — custom hardware tiers**
    - Effort: XXL
    - What: Wearable runtime (ulab subset, device pipeline, BLE GATT, baked-frames fallback, ADR-008) + pewpew receiver firmware (S3: DDP16 ingest, keyframe interp, ≥400 Hz dither, ADR-004).
    - Why: The receiver's device-side dithering is the field's biggest unclaimed quality lever [S600][S054][S251].
    - Dependencies: Phase 2 (16-bit host pipeline)
    - Status: Not Started
    - Notes: Stock WLED and baked frames are the adequate interim carriers until here.

- [ ] **Phase 5 — mesh group tier**
    - Effort: XXL
    - What: ESP-NOW state radio + epoch gossip (ADR-014/015), gateway dongle (ADR-016), coordination simulator in the preview harness, firefly beat layer, wearable BLE bridge.
    - Why: The decentralized-groups product tier (M-* requirements).
    - Dependencies: Phase 4 receiver firmware; §12 items 15–20 gate the fleet buy
    - Status: Not Started
    - Notes: 25–50 nodes at defaults is already inside the evidence; benches gate the buy, not the design.

- [ ] **Keep preview ports honest**
    - Effort: XS
    - What: `preview/index.html` carries hand-ported JS mirrors of the `bench/authoring/` patterns; re-port (or retire the page) when the Phase-1 engine or idiom kit changes the contract.
    - Why: Unmaintained mirrors drift silently; the page is a playground, not evidence, and must not masquerade as either.
    - Dependencies: None
    - Status: Not Started
    - Notes: Sanctioned divergences from the study patterns: fire (Doom advection + embers, sourced in the CHANGELOG entry) and sdf3d spin (end-over-end tumble — the study pattern's spin is a proven no-op, see the report addendum). Port-introduced bugs to date were both renderer-side (lattice color/position desync after sort; missing display gamma crushing low-end glow) — any future preview sink inherits the display-gamma requirement. Verify changes with `cd preview && npm install && node verify.js` (the committed Playwright harness).

- [ ] **Port the upgraded fire to Python**
    - Effort: S
    - What: Bring the preview's FireSim recipe (Doom-style randomized advection with wind/gusts, scrolling-noise cooling, wandering hot-spot tongues, additive ember particles) into a Python pattern once the Phase-1 engine and idiom kit exist.
    - Why: It's a far better fire than the study's Fire2012 and it stress-tests exactly the contract questions Phase 1 must settle: internal fields, per-particle state, the stumble-17 private-buffer decision.
    - Dependencies: Phase 1 engine + idiom-kit additions
    - Status: Not Started
    - Notes: Reference implementation: `FireSim` in `preview/index.html`; technique sources in the CHANGELOG playground entry (Sanglard PSX-Doom fire, FastLED Fire2012WithPalette, 29a.ch, Petrick Fire2018, MatrixFireFast, Pagurek).

- [ ] **Retry 51 pending archive snapshots**
    - Effort: S
    - What: Re-run the archive pass for the SOURCES.md entries marked `archive: pending` (Save Page Now outage during the ADR-014..019 pass).
    - Why: Load-bearing sources aren't link-rot-proof until snapshotted.
    - Dependencies: None
    - Status: Not Started
    - Notes: `grep 'archive: pending' research/SOURCES.md`; procedure + failure details in `research/verification/archive-report.md`. S027/S123 need a real-browser retry.
