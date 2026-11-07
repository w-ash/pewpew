# Fixes applied — Phase 4 fixer

- fixer: phase-4-fixer
- date: 2026-07-03
- input reports: citation-audit.md, archive-report.md, excerpt-license-audit.md,
  adr-adversarial-review.md (F1–F16), completeness-critique.md (ranked #1–#10)
- scope: judgment fixes 1–18 per fixer brief (mechanical archive/freshness fixes
  were applied earlier by the critics themselves)

## Log

<!-- one entry per fix, appended as applied -->

### Fix 1 — pinned: fields for S008 and S011 (citation-audit §4)
- SOURCES.md [S008]: added `pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e` (copied from deep-dive pin [S615], same repo).
- SOURCES.md [S011]: added `pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792` (copied from deep-dive pin [S630], same repo).

### Fix 2 — hyperhdr.md bare relative cites expanded to full [S700:path#L...] form (citation-audit §4)
Nine bare anchors expanded; each intended file inferred from surrounding prose and
VERIFIED by fetching the file at the S700 pin
(awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584) via raw.githubusercontent.com
and confirming the cited lines contain the described code:
- `#L63-L65`, `#L97-L101`, `#L121-L127`, `#L104-L117`, `#L63-L65` (x2 occurrences) →
  `sources/led-drivers/InfiniteColorEngineRgbw.cpp` (motion threshold + interval scaling,
  flow gate, leak lerp, white mixing — all confirmed at those lines).
- `#L220-L283` → `sources/infinite-color-engine/InfiniteSmoothing.cpp` (incomingColors →
  updateLeds flow; L220 is `incomingColors`, confirmed).
- `#L151-L157`, `#L133-L142`, `#L187-L208` →
  `sources/infinite-color-engine/InfiniteHybridInterpolator.cpp` (y_limit scale, completion
  test constants, getCurrentColors — confirmed).

### Fix 3 — wled.md uncited direct quote (citation-audit §1)
- code-reading/wled.md:250 — the direct quote "It is NOT a measurement and NOT guaranteed
  to stay within the ablMilliampsMax margin" is a WLED source comment. Verified at the S645
  pin: wled00/bus_manager.cpp line 185 (comment block L183-L186), also present in
  excerpts/S645-abl-power-limiter/bus_manager.cpp line 3. Added inline cite
  `[S645:wled00/bus_manager.cpp#L183-L186]` after the quote; kept as a quote (it is verbatim).

### Fix 4 — topic-doc uncited paragraphs (citation-audit §1)
- topics/RA-02-color-science.md ~L305 (batch calibration lead): grounded the "ship
  uncalibrated" half in FastLED's TypicalLEDStrip correction [S008:src/color.h#L11-L26]
  (S008 now pinned per Fix 1); tagged the vendor/bin-variance half [NEEDS-VERIFICATION]
  (no measured source in SOURCES.md covers it).
- topics/RA-03-led-chips.md ~L86 ("roughly double the strip cost"): no priced source
  exists in the tree; reworded to state it is an observed retail delta and tagged
  [NEEDS-VERIFICATION].
- topics/RA-10-audio-reactivity.md ~L57 (self-measured FFT/mel microbenchmark): marked
  explicitly as a local measurement whose bench script was NOT preserved (not reproducible
  from the repo, re-bench before relying on it) and tagged [NEEDS-VERIFICATION].

### Fix 5 — ADR Context citation convention (citation-audit §1 systematic finding)
- ADR-000 Decision: added rule 6 — ADR Context sections may restate findings without
  inline cites ONLY where the ADR's own Evidence section carries the citation; all other
  docs cite inline.
- README.md ADRs section: added the same convention (pointer to ADR-000 rule 6).
- Spot-check ADR-001 Context: every factual claim (WLED 8-bit pipeline / ~5 effective
  bits / lossy 8→8 gamma; LedFx float64→uint8 truncation) is covered by that ADR's own
  Evidence ([S645:wled00/FX_fcn.cpp#L1781][S054][S058]; [S630:ledfx/devices/ddp.py#L25-L36]).
  No inline cite needed.
- Spot-check ADR-002 Context: refresh floor ~400 Hz / flicker below → Evidence bullet 2
  ([S615:src/pixel_controller.h#L253-L302][S050]); line-length tie → same bullet;
  16-bit-native chips make dithering unnecessary → [S684][S063]. No inline cite needed.

### Fix 6 — archival rule scoping + excerpt backfill (archive-report 27-source list, F16)
- README.md archival rule: scoped — excerpts required for code cited with line anchors
  ([S###:path#Lx-Ly]) in ADRs; repo-level citations (existence, license, maintenance,
  verdicts) need `pinned:` but no excerpt.
- ADR-000 rule 4: same scoping added.
- Checked all 27 sources from archive-report against the scoped rule by grepping
  decisions/*.md for `[S###:` forms: NONE of the 27 is line-anchored in any ADR — all are
  repo-level ADR cites, so none requires an excerpt under the scoped rule. S017's
  line-anchored cite ([S017:ledcontrol/driver/led_render.h]) is in topics/RA-01b, not an
  ADR, and S017 already carries `pinned:` — no excerpt created.
- The full set of S-IDs line-anchored in ADRs is: S600 S615 S630 S645 S660 S670 S680 S681
  S682 S700 S715 S716. Two gaps found and closed:
  - S716 (F16): `src/SmoothLed.h` cited by ADR-002 #L13-L15 and ADR-008/W-3/W-4 #L63-L79
    but absent from excerpts/S716-smoothled-inner-loop/. Fetched the complete file (168
    lines) at pin mattshepcar/SmoothLed@e09236cfc63a96c565d97ef316073452a38cf86d, verified
    both cited ranges (DitherBits enum; Interpolator struct = 5 B/channel), added to the
    excerpt dir and recorded in its LICENSE-NOTE.md.
  - S680: line-anchored in ADR-005/007/010 (README.expressions.md, README.mapper.md) with
    no excerpt dir; its archive: snapshot (repo tree page) does not capture those files.
    Created excerpts/S680-pixelblaze-docs/ with both complete files fetched at pin
    simap/pixelblaze@20d169f30f7912b2245c57ab9bd721436324bf04, cited ranges verified;
    LICENSE-NOTE.md records the no-license status (verbatim retention for citation
    permanence only, no reuse).
- Residual (out of fixer scope, already recorded in archive-report): ~25 repo-level code
  sources still lack `pinned:` fields; under the scoped rule they need pins but not
  excerpts. S008/S011 were pinned in Fix 1.

### Fix 7 — copyleft boundary lists gain projectMM and WLED-MM (excerpt-license-audit §3)
- ADR-012 rule 1: enumerated list now includes projectMM [S715] (GPL-3.0) and WLED-MM
  [S646] (EUPL-1.2).
- architecture.md §9 "This applies to ..." enumeration: added WLED-MM (EUPL-1.2 [S646])
  and projectMM (GPL-3.0 [S715]).

### Fix 8 — ADR-012 rule 3 vs ADR-010 LX-read contradiction (adversarial F1)
- ADR-012 rule 3 rewritten to reflect reality: the research DID make a recorded
  line-level design read of LXEngine.java [S264] (used by ADR-010); binding rule going
  forward is read-for-understanding permitted and recorded, no LX code copied or ported
  line-by-line, implementations written from documented findings; formats still
  clean-roomed from public docs.
- ADR-010 Evidence [S264] bullet: added license-posture sentence (custom non-OSI
  source-available; design-pattern read only; no code copied/ported).
- Checked remaining "no LX code"/"clean-roomed" mentions (architecture.md L227/L398,
  ADR-007): all format-scoped and consistent with the amended rule — left unchanged.

### Fix 9 — 45/50 ms audio budget alignment (adversarial F2)
- requirements.md P-4: now "≤50 ms audio-to-photon hard ceiling; ≤45 ms engine design
  budget (R-4)"; rationale explains the 5 ms ceiling slack for transport tails.
- ADR-009 Context: budget stated as ≤50 ms hard ceiling (P-4) / ≤45 ms engine design
  budget (R-4).
- ADR-009 Decision Latency bullet: "≤45 ms engine design budget within the ≤50 ms hard
  ceiling (P-4/R-4)".
- architecture.md §7 Latency & sync: references both numbers (design budget inside hard
  ceiling). §12 item 6 ("≤45 ms ... is met") left as-is — it benches the design budget.

### Fix 10 — ADR-002 direct-view flicker warning carried into Consequences (adversarial F3)
- ADR-002 Consequences: added the documented hyperhdr.md "What to avoid" warning — tier-3
  recipe proven only behind a TV; direct-view purely-temporal dithering at 25–60 Hz may be
  visible; spatial/blue-noise question not closed [S700] — and folded direct-view
  visibility into prototype item #5's mandate.

### Fix 11 — duplicate S-ID pairs annotated (adversarial F4)
SOURCES.md: added "- note: same underlying source as [S###] — do not co-cite the pair as
independent corroboration" to BOTH entries of each pair: S050=S127 (FastLED dithering
wiki), S162=S253 (WLED UDP-realtime doc), S211=S400 (todbot ulab article), S135=S369
(QuinLED injection guide), S304≈S680 (Pixelblaze mapper doc, seed URL vs pinned repo copy).
Claim-level caveats added where an ADR co-cites a pair for one claim:
- ADR-004 Evidence: [S253][S162] "documented field standard" reworded to "WLED's
  documented contract" + explicit single-source caveat + independent corroboration cites
  added ([S157] sACN 2.5 s data-loss timeout, [S159] ArtSync 4 s fallback) — also
  resolves adversarial F8.
- ADR-005 Evidence: [S400][S211] single-source caveat; [S304][S680] same-document note.
- ADR-007 Evidence: [S304][S680] same-document note.
- ADR-011 Evidence: [S400][S211] single-source caveat (merged with Fix 13's F5 edit).
- ADR-013 Evidence: [S133][S135][S369][S370] bracket noted as three independent sources,
  not four.
- ADR-002 (S050/S127): NOT co-cited for a single claim (each appears in a different
  bracket alongside the independent S615 code cite) — SOURCES.md notes suffice, no ADR
  edit.

### Fix 12 — ADR-003 broadcast-Push loss physics (adversarial F6)
- ADR-003 Consequences: added paragraph — broadcast DDP Push shares the unacked-WiFi
  ~5% loss physics [S150] of the rejected multicast option; lost broadcast latch degrades
  to per-receiver unicast-Push timing (defeats cross-receiver alignment); prototype item
  #3 gates it and must measure broadcast-Push LOSS as well as skew; wired backbone (R-5)
  unaffected.

### Fix 13 — remaining adversarial nits (F9, F10, F5, F12, F14)
- ADR-006 (F9): "patched onto any knob" de-quoted — now explicitly a paraphrase, with
  S216's actual verified language quoted instead.
- ADR-007 (F10): "up to 13× faster" now attributed as a code-comment claim, unbenchmarked
  in-repo (per ledfx.md open questions); evidence scoped to the design direction, not the
  constant.
- ADR-011 (F5): "host CPUs gain 1–2 orders of magnitude" now explicitly marked as RA-05's
  extrapolation from an RP2040-only measurement, [NEEDS-VERIFICATION]-flagged at RA-05 and
  gated on the Phase-0 benchmark.
- ADR-011 (F12): C++/Rust rejected-alternative reworded to the honest costs
  (build/maintenance burden, contributor accessibility) — installability/live-authoring
  strawman removed (compiled cores ship as pip wheels; NumPy itself is one).
- ADR-013 + requirements.md W-9 + topics/RA-03 L121 (F14): 3.0 V logic-HIGH threshold
  scoped to HD108 (where RA-03 L104 documents it [S102][S100]); HD107s/NS108 described as
  vendor-"3.3 V-friendly" with no captured threshold figure.

### Fix 14 — architecture.md §12 bench items 13 & 14 (completeness #1, #2)
- Item 13: CPython frame-pacing jitter soak (10-min paced loop on Pi 5, tick-error
  histogram p99 vs 16.7 ms, GC active + audio thread) — gates ADR-010 / Phase 1.
- Item 14: per-receiver sustained DDP ingest on stock WLED (one ESP32 + one S3 node,
  60 fps unicast at 300/800/2000 px, delivered fps/drops) — gates ADR-004 / Phase 2/3.
- Gating sentence updated to include both items.

### Fix 15 — OTA/field-update consequences (completeness #3) + new sources
- SOURCES.md: added [S754] WLED getting-started/OTA docs, [S755] ESP Web Tools,
  [S756] ESP-IDF OTA docs (all liveness-checked 2026-07-03; existing wayback snapshots
  ≥2026-03 recorded in archive: fields since S754–S756 are now ADR-cited/load-bearing).
- ADR-004 Consequences: OTA paragraph — stock WLED's own path [S754]; Phase-4 receiver
  adopts esp-idf dual-partition OTA + rollback [S756] and esp-web-tools install/recovery
  [S755].
- ADR-008 Consequences: wearable update paragraph — CIRCUITPY USB / BLE
  FileTransferService file drop [S407][S409], UF2 bootloader for the core, no-brick
  worst case; versioned bundles + rollback deferred to Phase 3.

### Fix 16 — architecture.md §5 "Trust model" subsection (completeness #4)
- Added an explicit-decision subsection: unauthenticated trusted LAN by design (WLED
  field norm [S550]); opt-in PIN/token gate as planned later hardening; TLS/accounts out
  of scope; concurrent writers resolved last-write-wins with server-push merge of partial
  updates [S550][S551].

### Fix 17 — Matter/Thread exclusion + ESP32-C5 watch item (completeness #5, #6)
- topics/RA-12: addendum paragraph — Matter's light model (on/off/level/color) cannot
  express addressable effects; state of the world is bridges (wled-matter-bridge [S758],
  TLED [S759]) and an open, unlanded WLED discussion [S757]; revisit if native support
  lands. New sources [S757][S758][S759] added to SOURCES.md (liveness-checked; snapshot
  recorded where one existed).
- topics/RA-08 open questions: ESP32-C5 watch line — WLED #5020 open since 2025-10, no
  support landed [S760]; dual-band 5 GHz would relieve the AP-capacity ceiling (§12 item
  10). New source [S760] added.

### Fix 18 — small deferrals and caveats (completeness #7, #8, #9, #10)
- ADR-006 Consequences: project-on-disk layout + schema-version field deliberately
  undefined, to be defined at build Phase 3 (completeness #7).
- ADR-006 Consequences: palette model deferred to build Phase 1 — palettes as gradient
  assets addressable in the param tree; RA-12 carries the taste evidence (completeness
  #9; placed in ADR-006 because the param tree is where palettes mount).
- topics/RA-03 open questions: thermal practice (strip derating, PSU headroom, enclosed
  channels) added as an explicitly uncovered area — no existing source in the tree could
  cite it, so it went to open questions rather than the body (completeness #8).
- architecture.md §10: HD107s 27 kHz/40 MHz marked vendor-claimed pending community
  measurement (RA-03 open questions), and the 3.0 V threshold clause scoped to HD108
  (consistent with Fix 13/F14); S412 noted as a single hobbyist measurement pending
  datasheet corroboration, direction not in doubt (completeness #10).

## Summary

- All 18 fixes from the fixer brief applied; none skipped.
- New SOURCES.md entries: S754–S760 (7). New excerpt dirs: S680-pixelblaze-docs;
  S716-smoothled-inner-loop gained SmoothLed.h.
- Post-fix checks: zero bare `[#L...]` cites remain; every S754–S760 cite resolves to a
  SOURCES.md entry; every S-ID line-anchored in an ADR (S600 S615 S630 S645 S660 S670
  S680 S681 S682 S700 S715 S716) now has an excerpt dir; 38 `pinned:` fields in
  SOURCES.md.
- NEEDS-VERIFICATION count after fixes: 79 tag lines across research/ (grep -rc sum;
  includes 13 mentions inside verification reports and 2 in convention text — 64 in
  content docs). Fixes 4 added three new tags (RA-02 bin-variance, RA-03 strip cost,
  RA-10 unpreserved bench).
- Known residuals (recorded, not fixed — outside brief): ~25 repo-level code sources
  still lack `pinned:` (archive-report secondary observation); S027/S123 archive:
  pending; adversarial F7/F11/F13/F15 nits not in the fixer brief's enumerated list.
