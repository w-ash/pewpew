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
    - Notes: XL must be decomposed before scheduling. The v0.2.x preview sink deliberately ships a 2D-canvas page that draws 3D maps as z-slices (matching the ANSI reading); the three.js `Points` view was deferred to here because it means vendoring a library into the served page (§8, [S513]).

- [ ] **Phase 4 — custom hardware tiers**
    - Effort: XXL
    - What: Wearable runtime (ulab subset, device pipeline, BLE GATT, baked-frames fallback, ADR-008) + pewpew receiver firmware (S3: DDP16 ingest, keyframe interp, ≥400 Hz dither, ADR-004).
    - Why: The receiver's device-side dithering is the field's biggest unclaimed quality lever [S600][S054][S251].
    - Dependencies: Phase 2 (16-bit host pipeline)
    - Status: Not Started
    - Notes: Stock WLED and baked frames are the adequate interim carriers until here. **Before committing silicon for this phase, re-run the 2026-08-22 hardware refresh** (ADR-013 § Verification; `research/verification/hardware-refresh-2026-08.md`): the ESP32-S31 (mass production 2026-07-27) supersedes the S3 on paper once devkits + a WLED/FastLED port exist, and **nRF54L15 is already the recorded W-5 default over nRF52840**.

- [ ] **Phase 5 — mesh group tier**
    - Effort: XXL
    - What: ESP-NOW state radio + epoch gossip (ADR-014/015), gateway dongle (ADR-016), coordination simulator in the preview harness, firefly beat layer, wearable BLE bridge.
    - Why: The decentralized-groups product tier (M-* requirements).
    - Dependencies: Phase 4 receiver firmware; §12 items 15–20 gate the fleet buy
    - Status: Not Started
    - Notes: 25–50 nodes at defaults is already inside the evidence; benches gate the buy, not the design. The fleet buy is also the ESP32-S31 re-check point (ADR-013 § Verification).

- [ ] **Port the upgraded fire to Python**
    - Effort: S
    - What: Bring the preview's FireSim recipe (Doom-style randomized advection with wind/gusts, scrolling-noise cooling, wandering hot-spot tongues, additive ember particles) into a Python pattern once the Phase-1 engine and idiom kit exist.
    - Why: It's a far better fire than the study's Fire2012 and it stress-tests exactly the contract questions Phase 1 must settle: internal fields, per-particle state, the stumble-17 private-buffer decision.
    - Dependencies: v0.2.x stories — pure render core, idiom-kit additions, private per-pixel state buffers (#17) — **all cleared 2026-08-20**
    - Status: Not Started
    - Notes: Reference implementation: `preview/fire-reference.js` (extracted verbatim, with the helpers it uses, when the playground was retired 2026-08-20; header records provenance). Technique sources in the CHANGELOG playground entry (Sanglard PSX-Doom fire, FastLED Fire2012WithPalette, 29a.ch, Petrick Fire2018, MatrixFireFast, Pagurek). The ember layer lived in the playground's *renderer* (additive sprite stamps) — decide whether it becomes pattern pixels or stays a preview-side nicety.

- [ ] **Normalize preview layouts per axis for partial-range maps**
    - Effort: S
    - What: Make both preview sinks position pixels by each axis's *observed* range rather than assuming coordinates span 0–1 — `AnsiLayout.from_mapping` (`src/pewpew/sinks/ansi.py`) and `makeLayout` (`src/pewpew/sinks/web/index.html`), changed together.
    - Why: Resolution comes from the count of distinct values per axis, but position comes from `bins()`/`* scale`, which map the value linearly over [0, 1]. A map spanning, say, 0.4–0.6 therefore gets full-width columns and draws into a fifth of them, colliding pixels into shared cells while the rest of the grid stays blank.
    - Dependencies: "Room map file with live 2D simulation" (`v0.2.x.md`, v0.2.6) — as of 2026-10-19 the first source of maps that do not span 0–1, ahead of Phase 3's fixture format and marimapper import
    - Status: Not Started
    - Notes: Surfaced by the 2026-08-21 sink review and deliberately deferred there. Every in-tree mapping (`line`, `grid`, `lattice`) spans 0–1, so nothing fails today; `bins`' own docstring already names imported marimapper CSVs (§6) as where out-of-range coordinates come from. **Both sinks must change in the same pass** — the shared 0–1 assumption is what makes the ANSI and browser previews agree on what the cube looks like (both module docstrings say so), and normalizing one alone would split them. The assumption is documented on `AnsiLayout.from_mapping` until then.
