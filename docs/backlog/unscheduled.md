# Unscheduled ideas

**Optional only.** Anything the project actually owes — obligations, debt,
follow-ups — belongs in a version series file in its proper sequence, not here.
This file holds genuinely nice-to-have ideas plus the staged phase queue.

The remaining Phase 2–5 entries mirror the build plan
(`research/synthesis/architecture.md` §11). They are sequenced, not optional —
they sit here only because XL/XXL scope must be decomposed before it can be
scheduled, and each is promoted to its own series when its dependencies clear.

> **Phase 1 was promoted** to [`v0.2.x.md`](v0.2.x.md) on 2026-07-26 and is no
> longer listed here. Its XL scope is now ten stories; the idiom-kit, docs,
> private-state-buffer and param-liveness obligations it carried live in that
> series' Authoring-surface epic.

- [ ] **Phase 2 — quality pipeline**
    - Effort: XL
    - What: Float32-linear stages 1–6 of §2 (LUT, white point, power limiter, adaptive dither, DDP 16-bit, five-bit-HD via UPXL) + photodiode bench rig.
    - Why: The quality lever the research identifies as the field's biggest gap (ADR-001/002).
    - Dependencies: v0.2.x (Phase 1)
    - Status: Not Started
    - Notes: Photodiode rig settles §12 items 3, 5, 6. Break into a v0.3.x series when promoted — XL must be decomposed before scheduling.

- [ ] **Phase 3 — control plane, audio, mapping**
    - Effort: XL
    - What: HTTP+WS JSON tree, presets/playlists, OSC + MIDI-learn, mDNS/HA, feature bus + WLED sync out, fixture format + map compiler + marimapper import, three.js preview.
    - Why: Makes the engine drivable and mappable (§5–7, ADR-007/009).
    - Dependencies: v0.2.x (Phase 1)
    - Status: Not Started
    - Notes: XL must be decomposed before scheduling.

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

- [ ] **Port the upgraded fire to Python**
    - Effort: S
    - What: Bring the preview's FireSim recipe (Doom-style randomized advection with wind/gusts, scrolling-noise cooling, wandering hot-spot tongues, additive ember particles) into a Python pattern once the Phase-1 engine and idiom kit exist.
    - Why: It's a far better fire than the study's Fire2012 and it stress-tests exactly the contract questions Phase 1 must settle: internal fields, per-particle state, the stumble-17 private-buffer decision.
    - Dependencies: v0.2.x stories — pure render core, idiom-kit additions, private per-pixel state buffers (#17)
    - Status: Not Started
    - Notes: Reference implementation: `FireSim` in `preview/index.html`; technique sources in the CHANGELOG playground entry (Sanglard PSX-Doom fire, FastLED Fire2012WithPalette, 29a.ch, Petrick Fire2018, MatrixFireFast, Pagurek).
