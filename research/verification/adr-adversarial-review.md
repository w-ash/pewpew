# ADR Adversarial Review

- Critic: adr-adversarial (Phase 4 verification)
- Date: 2026-07-03
- Scope: ADR-001..ADR-013 in `research/synthesis/decisions/`. Method: for each ADR, read the ADR; pulled every load-bearing S-ID from `SOURCES.md`; cross-checked line-level code cites against `research/excerpts/` and `research/code-reading/*.md`; cross-checked numeric/quoted claims against `topics/RA-*.md`; grepped every code-reading "What to avoid" list against ADR consequences; checked cross-ADR and ADR-vs-architecture.md/requirements.md consistency.

Verification depth: ~40 line-level citations were re-resolved (excerpts: S600 fc_pixel.cpp, S645 e131.cpp DDP ingest, S615 five_bit_hd_gamma, S716 SmoothLed, S700 InfiniteColorEngineRgbw; code-reading docs for the rest). None was found to say the opposite of what an ADR claims. The findings below are misattributions, over-generalizations, ignored documented costs, duplicate-source corroboration, and cross-document inconsistencies — no decision was refuted outright.

## Verdict summary

| ADR | Rating | Worst issue |
|---|---|---|
| ADR-001 | SOUND-WITH-NITS | "quantize exactly once" wording vs the two-step 8-bit path |
| ADR-002 | SOUND-WITH-NITS | tier-3 low-rate dithering vs its own rejected-alt flicker rationale; direct-view visibility cost from hyperhdr.md avoid-list not carried |
| ADR-003 | SOUND-WITH-NITS | broadcast-Push shares the unacked-WiFi physics used to reject multicast; S165 over-attribution |
| ADR-004 | SOUND-WITH-NITS | [S253][S162] are the same document, generalized to "field standard" |
| ADR-005 | SOUND-WITH-NITS | [S400][S211] are the same article; 22.5k px/s "ceiling" drops the small-hardware qualifier |
| ADR-006 | SOUND-WITH-NITS | quotation marks around a research-doc paraphrase ("patched onto any knob") |
| ADR-007 | SOUND-WITH-NITS | LedFx "13×" is a code-comment claim flagged unverified in ledfx.md; no flag in the ADR |
| ADR-008 | SOUND | (archival nit only: SmoothLed.h lines cited but not excerpted) |
| ADR-009 | SOUND-WITH-NITS | 45 ms budget cited to (P-4, R-4) but P-4 says ≤50 ms |
| ADR-010 | SOUND-WITH-NITS | S264 = line-level LX code read used as implementation reference (see cross-ADR #1) |
| ADR-011 | SOUND-WITH-NITS | "host CPUs gain 1–2 orders" attributed to an RP2040-only measurement; C++/Rust rejected-alt partially strawmanned |
| ADR-012 | SOUND-WITH-NITS | rule 3 ("LX code is not read") contradicted in spirit by S264/RA-06/ADR-010 |
| ADR-013 | SOUND-WITH-NITS | 3.0 V logic threshold attributed to HD107s; sources document it for HD108 |

No ADR is DEFECTIVE. All 13 have ≥2 genuinely independent evidence sources at ADR level (ADR-011, the thinnest, has three independent performance sources plus the strongest explicit caveat in the set).

## Findings (most severe first)

### F1. Cross-ADR: ADR-012 rule 3 vs ADR-010's use of LX source (ADR-010, ADR-012)
ADR-012 rule 3: "LX-licensed code is not read for implementation; formats are clean-roomed from public docs (ADR-007)" and claims the boundary rules are "already applied throughout this research tree." But [S264] is a **pinned, line-cited read of `heronarts/LX LXEngine.java`** (SOURCES.md records the custom non-OSI license with "read terms before any reuse"); RA-06 cites it at line level (`#L109-L110`, and queued a deeper read of the Frame double-buffering "around L1283+"), and **ADR-010 adopts it as "the clean pacing reference"** for pewpew's render clock. A design-only read for a generic technique (fixed-rate executor with error correction) is likely fine legally, and S035's own relevance line says "worth a design-only read" — but ADR-012's blanket wording does not match what the research tree actually did, and ADR-010 blurs "design-only" into "reference for implementation." Fix: qualify ADR-012 rule 3 (e.g. "not ported or paraphrased at code level; design-pattern reads permitted and recorded") and/or note in ADR-010 that the LX reference is a design-pattern observation, not a code source.

### F2. Cross-doc: audio-to-photon budget is 45 ms in ADR-009/architecture but 50 ms in P-4 (ADR-009, requirements.md)
ADR-009 decision: "≤45 ms budget" citing "(P-4, R-4)". requirements.md R-4 says ≤45 ms, but **P-4 says "≤50 ms audio-to-photon."** architecture.md §7 also says ≤45 ms "req P-4/R-4". A 5 ms discrepancy across the three documents, with the ADR citing a requirement that states a different number. One of P-4 or the ADR/architecture should change.

### F3. ADR-002: tier-3 policy vs its own rejected-alternative rationale; ignored avoid-list cost (ADR-002)
Rejected alternative: "Dither everywhere regardless of refresh — below ~200 Hz it is visible flicker, worse than banding [S615][S127]." Yet tier 3 adopts host-side temporal error-diffusion "at the sink's output rate," whose evidence base (HyperHDR) runs at **25–200 Hz** — below the ADR's own flicker floor. The implicit reconciliation (adaptive error-diffusion with static-freeze/motion gates is not free-running binary dither, so it de-bands slow fades without steady-state flicker) is never stated. Worse, `code-reading/hyperhdr.md` "What to avoid" explicitly warns: HyperHDR's LEDs sit behind a TV; "for direct-view pewpew fixtures, purely temporal per-LED dithering at 25-60 Hz may be visible; don't assume this closes the question." ADR-002's consequences say "effective mainly on slow fades" but do not carry the direct-view visibility risk, and prototype item #5 measures bit-gain-vs-Hz, not direct-view visibility of the tier-3 recipe. Fix: one sentence in Consequences acknowledging the direct-view visibility risk and folding it into the prototype-5 bench.

### F4. Systemic: duplicate S-IDs co-cited as if they corroborate (ADR-002, -004, -005, -007, -011, -013)
The per-area ID blocks caused the same document to be entered twice under different IDs, and several ADRs co-cite both halves of a pair for a single claim, inflating apparent corroboration:
- **S400 ≡ S211** (todbot ulab article): co-cited in ADR-005 ("[S400][S211] Vectorization buys ~10×") and ADR-011. One author, one measurement.
- **S253 ≡ S162** (WLED UDP-realtime doc): co-cited in ADR-004 ("[S253][S162] ... the documented field standard") and ADR-010. One document, one project.
- **S050 ≡ S127** (FastLED dithering wiki): both used inside ADR-002 (evidence and rejected-alts).
- **S135 ≡ S369** (QuinLED injection guide): both inside ADR-013's "[S133][S135][S369][S370]" bracket.
- **S304 ≡ S680:README.mapper.md** (same file; seed vs repo pin): co-cited in ADR-005 and ADR-007.
- Also same-repo seed/pin pairs co-cited: **S011/S630** (ADR-011), **S016/S600**, **S019/S716**, **S251 ≡ S684** (used in different ADRs — acceptable).
No ADR drops below 2 independent sources when the pairs are collapsed, but claim-level corroboration is weaker than the citation lists suggest. Fix: annotate duplicate pairs in SOURCES.md ("duplicate of S###") and avoid co-citing both IDs for one claim.

### F5. ADR-011: host-CPU gain attributed beyond what the source measured (ADR-011)
Evidence line: "[S400][S211] Vectorization measured at ~10× even on an RP2040 ...; **host CPUs gain 1–2 orders of magnitude**." The source measured RP2040 only. RA-05 states the host-CPU extrapolation with an explicit **[NEEDS-VERIFICATION]** tag (line 73) that the ADR drops from that sentence. Partially remediated: the ADR's fourth evidence bullet and Decision do carry the R-9/benchmark-gap caveat prominently, and Phase 0 gates on it. Fix: move the caveat into the same sentence or tag the host-CPU figure.

### F6. ADR-003: broadcast-Push inherits the physics used to reject multicast (ADR-003)
The ADR rejects multicast because "WiFi multicast loss ≈ raw PER (~5%) vs <0.1% for unicast [S150]" — but 802.11 **broadcast frames are equally unacknowledged**, and the decision adopts "Broadcast DDP Push as the cross-receiver frame-latch signal." The DDP spec's own qualifier ("usable when ... latency is minimal", single broadcast-supporting network) and RA-04's single-source caveat (line 167) cover skew, and the ADR carries skew as prototype item #3 — but neither the ADR nor its consequences note that ~5% of broadcast latch packets can simply vanish on WiFi segments (receivers then latch on their own unicast Push, restoring per-receiver timing but defeating the cross-receiver alignment the broadcast exists for). Mitigations exist (room backbone is wired per R-5), but WiFi receivers in a multi-receiver canvas are the unaddressed case. Fix: extend prototype item #3 to measure broadcast-Push *loss*, not just skew.

### F7. ADR-003: [S165] over-attribution (ADR-003)
Evidence: "WLED's own docs recommend DDP **because per-packet processing, not bandwidth, saturates ESP32 receivers**." Per RA-04 (line 135), the WLED FAQ's actual rationale is "the reduced overhead" improving "the fluidity of your animations"; the per-packet-vs-bandwidth framing is RA-04's own (well-supported) analysis built on S150+S152. The conclusion stands; the attribution puts the research tree's inference in WLED's mouth. Fix: split the cite ("WLED's docs recommend DDP for reduced overhead [S165]; per-packet processing is the binding constraint [S150][S152]").

### F8. ADR-004: single project's docs generalized to "the documented field standard" (ADR-004)
"[S253][S162] The realtime-lock/hold-then-revert policy is the documented field standard for stream loss." Both IDs are the same WLED doc page (see F4), so the claim rests on one project's documentation. The behavior *is* corroborated elsewhere in the tree (sACN's 2.5 s data-loss timeout [S157], ArtSync's 4 s fallback [S159]) — but those aren't cited here. Fix: cite S157/S159 for "field standard," or soften to "WLED's documented contract."

### F9. ADR-006: paraphrase presented as quotation (ADR-006)
Evidence: 'runtime modulation "patched onto any knob"' attributed to [S216]. The quoted words are RA-05's paraphrase (line 91: "i.e. LFOs/audio modulators can be *patched onto any knob* at runtime"); S216's actual language is "the ability to be easily mapped to UI components, MIDI controllers, or OSC messages" / "opens up interesting modulation possibilities." Semantics match; the quotation marks violate the README's direct-quote rule. Fix: drop the quote marks.

### F10. ADR-007: unverified "13×" carried without its flag (ADR-007)
"LedFx's precompiled segment→device gathers ('up to 13× faster')" — `code-reading/ledfx.md` Open questions explicitly notes the 13× is asserted **only in a code comment** (virtuals.py#L1130), with no benchmark in-repo, "Unverified." architecture.md hedges ("claimed up to 13×"); ADR-007 does not. It is supporting evidence for a design direction (compiled gathers), not a load-bearing constant, so a nit. Fix: add "claimed" or the NEEDS-VERIFICATION tag.

### F11. ADR-005/ADR-011: "22.5k px/s ceiling" drops its hardware qualifier (ADR-005, ADR-011)
The figure is 150 fps × 150 px **on a Pi Zero** (led-control README claim, itself un-benchmarked per led-control.md's open questions). RA-05 consistently qualifies it ("on small hardware"); ADR-005's rejected-alts and ADR-011's evidence state it as an absolute ceiling of the approach. A desktop-class host would do better per-pixel — though still far below R-9's 1.2 M px·frames/s, so the conclusion survives. Fix: add "on Pi-class hardware; orders of magnitude short of R-9 on any host."

### F12. ADR-011: C++/Rust-core rejected alternative is partially strawmanned (ADR-011)
"C++/Rust engine core with Python bindings — forfeits live authoring simplicity and pip-installability." Neither is actually forfeited: compiled cores ship as pip wheels routinely (NumPy itself — the adopted substrate — is a compiled core), and live Python pattern authoring is unaffected by the core's language. The honest costs are build/maintenance burden and contributor accessibility (which the Consequences do state: "contributors write Python only"). The escape-hatch design and Phase-0 gate keep the decision sound regardless. Fix: restate the rejection rationale as maintenance/contributor cost, not installability.

### F13. ADR-001: "quantize exactly once" overstates the 8-bit path (ADR-001)
Decision says "Quantize exactly once, at the sink," but per architecture §2 the perceptual curve quantizes float32→uint16 at stage 4 (per sink group), and 8-bit sinks then quantize uint16→uint8(+dither) at stage 6 — two lossy steps on the volume path (the second mitigated by dithering per ADR-002). The intended meaning — no mid-pipeline 8-bit round-trips, one quantization *pathway* — is sound and matches Q-1; the slogan is imprecise. Fix: "quantize once per sink, never mid-pipeline" or note the uint16 intermediate explicitly.

### F14. ADR-013: HD107s/HD108 spec conflation (ADR-013)
Evidence: "HD107s does 27 kHz PWM **at 3.0 V logic**." RA-03 documents 27 kHz for HD107s [S101][S102] but attributes the 3.0 V logic-HIGH threshold to **HD108** (line 104; HD107s is described as "3.3 V-friendly," line 150). The S102 vendor page covers the family, so the claim may be true of both, but the tree's own record pins 3.0 V to HD108. requirements.md W-9 repeats the conflation ("HD107s/HD108 have ... 3.0 V logic thresholds"). Fix: verify HD107s's threshold on the vendor page or scope the 3.0 V claim to HD108.

### F15. ADR-004/architecture: universal negative slightly over-broad (ADR-004)
"Device-side interpolate+dither ... absent from **every current receiver**" (also architecture §4b "the single biggest unclaimed quality lever in the field"). Supported for WLED [S054], Pixelblaze expander [S251], and the surveyed set; as a universal it is survey-bounded (Falcon/Kulp/HinksPix firmware was not read). Low risk; a "no surveyed receiver" phrasing would be exact.

### F16. Archival gap: SmoothLed.h cited, not excerpted (ADR-002, ADR-008, requirements W-3/W-4)
ADR-002 cites [S716:src/SmoothLed.h#L13-L15], ADR-008 and W-4 cite [S716:src/SmoothLed.h#L63-L79], but `excerpts/S716-smoothled-inner-loop/` contains only SmoothLed.cpp, SmoothLedMultiply.h, SmoothLedUpdate.S. Per README's archival rule, load-bearing code cites need verbatim excerpts. The claims themselves are corroborated by modern-engines.md §B (5 B/channel, ≥400 Hz, ditherMask) — this is an archival-completeness gap, not an evidence failure.

## What was attacked and held

- **ADR-001**: S063 quote ("All 16 bit per element throughout") verified verbatim in RA-02; fc_pixel.cpp L25-88 verified against the excerpt (interpolate→16-bit→LUT→dither); whitepoint-before-gamma verified (fcdevice.cpp / fadecandy.md); S058 "first ~16 codes → 0 or 1" verified in RA-02 and independently arithmetic-checked (γ2.8: inputs ≤27 map to 0/1); LedFx ddp.py uint8-truncation verified in ledfx.md; projectMM deliberate-8-bit verified at modern-engines.md L184-199. OKLab rejection is an honest negative result [S068]. The avoid-lists' power-limiter-on-linear lesson (hyperhdr.md) is *adopted*, not ignored.
- **ADR-002**: FastLED "only possible with 85 pixels or fewer" quote verified (fastled.md L31, header comment); 3-virtual-bits derivation verified; `S = ceil(max16·31/65536)` verified (fastled.md L101/L340); HyperHDR static-freeze/monotonic-motion/leaky-accumulator recipe verified (hyperhdr.md L145-164); 0.49-LSB hysteresis verified; Hencke's on-record dithering rejection verified [S684]. Q-4's 64–85 px/400 Hz arithmetic checks (30 µs/px + 280 µs reset).
- **ADR-003**: 94.9/72.7/85.9% and 2.8× verified as the DDP spec's own math reproduced in RA-04 (arithmetic checks out independently); multicast ~5%-vs-<0.1% verified as the spec quoting Cisco; WLED timecode-flag ignore verified **in the excerpt itself** (e131.cpp L63); render-on-push-or-per-packet verified (e131.cpp L87-88); UPXL 66k px/s arithmetic verified (pixelblaze.md L337).
- **ADR-004**: realtimeLock/timeout/fallback verified (wled.md L162-171, udp.cpp cite); the brightness/gamma sender caveat verified as a *resolved review finding* in wled.md (L480-486: gamma NOT reapplied by default, master brightness IS) — the ADR states exactly this, correctly.
- **ADR-005**: ARTI-FX as second independent reimplementation verified (RA-05 L40/L99); projectMM auto-clear-breaks-trails verified; led-control pulsing-red error frame and RestrictedPython-can't-stop-loops verified (led-control.md avoid #5).
- **ADR-006**: WLED single-vocabulary/push fan-out and "dozens of third-party apps" verified (RA-12 L77); MQTT-as-fallback rationale traced to RA-12 (L107/L129/L139) — loosely cited but not invented.
- **ADR-007**: Chromatik tags/views-as-masks verified (RA-07 L105); marimapper v3.4.2 / 2026-03 verified (marimapper.md pin line); CSV schema and GPL boundary verified; the Pixelblaze aspect-distortion avoid-list item is *fixed* by the ADR's Fill/Contain policy, not ignored; marimapper.md's provenance-marking avoid item is carried as the importer's error-column requirement.
- **ADR-008**: S412 quote "ESP32s are not suitable for BLE projects with low current consumption" verified verbatim (RA-09 L23); ~10%/hour arithmetic verified (RA-09 L59); ulab 40→4 ms measurement verified; RP2350 2× correctly carries NEEDS-VERIFICATION *inside the ADR*; 5 B/channel state verified. Viper rejection matches S402's documented restrictions.
- **ADR-009**: 44-byte/port-11988/~43 Hz verified (RA-10 L41/L49); ITU +45 ms detectability verified (S459, correct directionality for lagging light); DSP-in-callback flaw verified (ledfx.md L296+); <0.2 ms/hop is RA-10's own measurement ("this doc") — used as context, acceptably.
- **ADR-010**: MAX_FRAMES_PENDING=2 verified (fadecandy.md L266/L348); HyperHDR latest-wins verified (hyperhdr.md L290); LedFx no-error-accumulation drift verified (ledfx.md L78-84); "must animate at every tick rate" verified (modern-engines.md L177); S166 ~25 ms tails verified. The ledfx.md avoid-list maps 1:1 onto this ADR's rejections — costs were mined, not ignored.
- **ADR-011**: carries the single most prominent honesty caveat in the set (R-9 unverified, Phase-0 gate, promotion path defined). The measurement gap is documented in RA-05 open questions exactly as cited.
- **ADR-012**: all seven license assertions re-verified against SOURCES.md entries (EUPL-1.2 WLED, GPL-3.0 LedFx/xLights/aubio-ledfx/marimapper, LX custom cap, MIT set); led-control never-on-PyPI verified (RA-01b L127/L201); GPL separate-process reasoning grounded in S672 (GNU FAQ).
- **ADR-013**: WS2812B-2020 2 kHz [S109], SK6812 1.2 kHz [S114], HD108 merge 2025-10-30 [S130], ESP8266 "should not be used for any new installations" quote (RA-08 L38), P4 no-radio [S353], F16v5 $280/16 = $17.50/port [S359], SoftAP-no-power-save [S411] — all verified. Hardware-verdict dating caveat present in Consequences.

## Cross-ADR consistency

Checked pairwise against each other and architecture.md/requirements.md:
- **Contradictions found**: F1 (ADR-012 rule 3 vs ADR-010/S264), F2 (P-4 50 ms vs ADR-009/R-4/architecture 45 ms), F3 (internal to ADR-002), F13 (ADR-001 slogan vs architecture stage table).
- **Consistent**: ADR-001↔002 (precision spending), ADR-002↔004 (tier 3 until Phase 4), ADR-003↔004↔013 (DDP/WLED/Falcon/S3 receiver story), ADR-005↔008↔011 (one contract, ulab subset, vectorized execution), ADR-006↔009↔010 (once-per-frame resolution of modulation and features on the single clock), ADR-007↔012 (marimapper GPL boundary), ADR-008↔013 (RP2350/nRF52840, SoftAP avoid). architecture.md contains no decision lacking an ADR that I could find; every §-level decision links one.
- Minor unflagged tension: ADR-009 emits WLED audio-sync V2 (a broadcast/multicast-style LAN packet per the WLED-MM convention) while ADR-003 bans multicast on WiFi — defensible because features are small, repeated at ~43 Hz, and loss-tolerant, unlike pixel data; worth one clause in ADR-009 if revised.

## Fixes applied

None. The brief grants this critic no edit authority over ADRs, topic docs, or SOURCES.md; all fixes above are recommendations, keyed F1–F16, left for the synthesis owner. The only file written is this report.
