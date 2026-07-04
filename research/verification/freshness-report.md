# Freshness re-verification report

- Critic: freshness-verify (Phase 4 verification critic)
- Date: 2026-07-03
- Scope: all `[NEEDS-VERIFICATION]` tags under `research/`; triage to load-bearing
  (cited by / affecting an ADR or `synthesis/architecture.md` decision); re-verify
  those against live sources. Plus 5 rot-prone untagged claims: WLED 16.x release
  status, projectMM/MoonLight activity, Pixelblaze firmware version, FastLED
  latest release, HyperHDR v22 status.

## Status

COMPLETE 2026-07-03. 51 claim tags triaged; 18 load-bearing claims re-verified
against live sources plus 5 rot-prone untagged claims; 20 tags resolved
(removed or replaced with dated citations/answers), 8 load-bearing tags kept
with dated "still unsettled" notes, 23 non-load-bearing tags left untouched
(31 tags remain in the tree, all accounted for).
One VERIFIED-FALSE correction (Pixelblaze firmware "stalled at v3.47")
propagated to 5 files. New sources S750-S753 appended to SOURCES.md.

## 1. Tag inventory & triage

54 `[NEEDS-VERIFICATION]` tags found under `research/` (grep 2026-07-03; the
citation-audit's "80" count predates earlier resolution passes). One is the
convention definition in README.md/ADR-000 (not a claim). Triage rule: a tag is
load-bearing if the claim (or its S-ID) is cited in `synthesis/architecture.md`
or an ADR Evidence/Rejected section, or the brief names it rot-prone.

### Load-bearing (re-verified this pass)

| # | Claim | Where tagged | Why load-bearing |
|---|---|---|---|
| 1 | RP2350 runs CircuitPython/ulab ~2x RP2040 [S403] | requirements.md:34; RA-09:21,35,107 | ADR-008, ADR-013, architecture.md L168/L364/L448; listed as top-risk L518 |
| 2 | nRF54 has not displaced nRF52840 in hobby/CircuitPython ecosystem | RA-09:27,89 | ADR-013 bets on nRF52840 [S412]; "stable" verdict feeds ADR-008 |
| 3 | Sparkle Motion Mini is USB-powered, no LiPo charger [S415] | RA-09:112 | ADR-008 L68 cites S414/S415 (SoftAP radio floor / board fitness) |
| 4 | FPP license is mixed GPL [S022] | comparison-matrix:41; RA-01:109 | ADR-006 cites S022; license claims feed ADR-012 |
| 5 | LedFx ~16 ms audio-to-LED is not a measured figure [S011] | RA-10:35,134 | ADR-009 decision leans on LedFx-shaped host analysis; S011 cited in ADR-009/011/012 |
| 6 | madmom pretrained models carry non-commercial clause [S454] | RA-10:137 | ADR-009 rejects madmom citing S454; license detail feeds ADR-012 exposure |
| 7 | BeatNet sub-50 ms unbenchmarked on Pi [S457] | RA-10:138 | ADR-009 names BeatNet the streaming downbeat option [S457] |
| 8 | Whether LedFx can emit WLED audio-sync V2 packet | RA-10:49 | architecture.md L290 plans emit/consume of V2 packet [S453] |
| 9 | fastled-wasm license MIT (repo) vs BSD-3 (PyPI) conflict [S500][S501] | RA-11:26 | S500 cited in ADRs/architecture; license set feeds ADR-012 |
| 10 | wled-sim young/small — check before depending [S511] | RA-11:65 | architecture.md L341 names wled-sim the preview co-sim |
| 11 | APA102 supply eclipsed by SK9822/HD107s clones [S101] | RA-03:95 | ADR-013 L89 cites S101 for exactly this |
| 12 | WS2816 availability strip/2020-level, not commodity [S123] | RA-03:61 | architecture.md L418 "watch availability [S122][S123]" |
| 13 | HD108 specialty supply (Hida/Newstar, vendor-direct) [S131][S132] | RA-03:106 | architecture.md L417 cites S131 for supply status |
| 14 | NS108/HD108 one chip type for driver purposes [S100] | RA-03:112 | ADR-013 L61 cites S100 |
| 15 | 12 V WS2815 per-LED efficiency lower; dissipation in chip [S112] | RA-03:32,133 | ADR-013 L56 + architecture.md L411 lean on WS2815 12 V bet |
| 16 | Differential (RS485) extender pairs are the long-run field standard [S135] | RA-03:127 | architecture.md L457 cites S135 |
| 17 | FPP VirtualDisplay coordinates preview-only [S308] | RA-07:56,147 | ADR-007 L70 cites S308 for "no coordinates for effects" |
| 18 | led-control output path gamma/dither unknown [S017] | RA-01b:239 | S017 cited ADR-012; feeds ADR-001 "no Python engine does 16-bit" premise |

### Not load-bearing (left as-is, not re-verified)

- RA-01:182 (unsourced leads list), RA-01:219 (Pixelblaze Pico Plus SKU — but see rot-prone #3), RA-01:224 (TouchDesigner tier limits) — no ADR cites these.
- RA-04:133,183 (200-388 ms noisy-WiFi anecdote [S168]) — explicitly kept as color only; not ADR-cited.
- RA-03:125 (single-ended run-length community practice [S138]) — S138 not ADR-cited.
- RA-05:71 (audio-reactive-led-strip fps reports [S212]) — S212 not ADR-cited.
- RA-05:135 (ARTI-FX status inside MoonLight) — not ADR-cited; superseded by rot-prone #2 finding below.
- RA-06:83,143 (FPP MultiSync cadence [S256]) — S256 not ADR-cited; code-reading item.
- RA-07:88,97,149 (zranger1 iOS app [S310]; Pixelblaze map precision) — S310 not ADR-cited.
- RA-08:54,71,101,120 (Kulp/BeagleBone supply [S360][S361], N100 pricing, Falcon F48) — S360/S361 not ADR-cited; ADRs cite Falcon F16v5 [S359], not F48.
- RA-11:35,138 (Pixelblaze compile-in-browser detail [S200]) — S200 not ADR-cited.
- RA-12:33,153,155 (LumenCouture BLINK listing; FPP scheduler; SugarCubes lineage) — explicitly pre-ADR caveats.
- RA-01b:246 (ProjectMM trajectory) — covered by rot-prone #2.

## 2. Load-bearing tag re-verification

Verified 2026-07-03 against live sources (GitHub API, PyPI JSON, vendor pages,
Discourse JSON, GitHub code search).

| # | Claim | Verdict | Evidence (live, 2026-07-03) |
|---|---|---|---|
| 3 | Sparkle Motion Mini USB-only, no LiPo [S415] | **CONFIRMED** | Adafruit Learn overview: "Power via USB Type C for up to 5V 4A input — you can use off-the-shelf USB battery packs"; no LiPo connector/charger. Tag removed. |
| 4 | FPP mixed GPL [S022] | **CONFIRMED** | github.com/FalconChristmas/fpp declares GPL-3.0 + LGPL-2.1 + CC-BY-ND + exception/external license files; latest release 9.5 (2026-01-08). Tags resolved. |
| 5 | LedFx ~16 ms unmeasured [S011] | **STILL UNSETTLED** | No official end-to-end measurement surfaced; tag kept with re-checked note. |
| 6 | madmom model license [S454] | **CONFIRMED (resolved)** | LICENSE at CPJKU/madmom: code BSD-2-Clause; "pickled Processors (i.e. saved models)" under CC BY-NC-SA 4.0, commercial use requires Gerhard Widmer's permission. Repo pushed 2026-03-20 but PyPI still 0.16.1. Tag removed. |
| 7 | BeatNet unbenchmarked on Pi [S457] | **STILL UNSETTLED** | Repo alive (pushed 2026-04-13, license CC-BY-4.0, 499 stars); still no SBC benchmark found. Tag kept with re-checked note. |
| 8 | LedFx emits WLED audio-sync V2? | **RESOLVED: NO** | GitHub code search over LedFx/LedFx: 0 hits for `11988` and `audio_sync` (index validated: `DDPDevice` returns hits). LedFx neither emits nor consumes the V2 packet as of 2026-07-03. Tag replaced with the answer. |
| 9 | fastled-wasm MIT vs BSD-3 conflict [S500][S501] | **CONFIRMED STILL CONFLICTING** | GitHub API: license MIT (pushed 2026-06-25); PyPI `fastled` JSON: license field "BSD 3-Clause License" (latest 2.0.13). Tag kept with re-checked note. |
| 10 | wled-sim young/small [S511] | **CONFIRMED, now also dormant** | Repo created 2025-07-16, last push 2025-08-05 (11 months idle), 6 stars, AGPL-3.0. Caution upgraded; AGPL noted (matters if code is linked rather than co-run). Tag resolved into dated fact. |
| 17 | FPP VirtualDisplay preview-only coords [S308] | **CONFIRMED (existence)** | `src/channeloutput/VirtualDisplay.cpp` (+ VirtualDisplayBase, HTTPVirtualDisplay, HTTPVirtualDisplay3D) exist under channeloutput/ — i.e. output/preview path, not effect input. Tag resolved. |
| 18 | led-control gamma/dither before ws281x? [S017] | **RESOLVED: NO** | `ledcontrol/driver/led_render.h` (master): gamma code commented out and `gamma` param unused; no dithering; 8-bit output via `pack_rgbw()`. Strengthens ADR-001 premise. Repo last push 2023-11-10. Tag replaced with the answer. |

| 1 | RP2350 ~2x RP2040 for CircuitPython [S403] | **CORROBORATED** | Adafruit's own speed test (Python-on-Microcontrollers newsletter 2024-08-26): M33 "'basically' 2x as fast as the M0+ when we speed-tested it"; "real world" MicroPython tests up to 2x. New source [S751]. Tags replaced with [S751] cites; the LED/ulab fire-benchmark remains the named open item (architecture.md risk row unchanged — mitigation still valid). |
| 2 | nRF54 not displacing nRF52840 | **CONFIRMED, nuance added** | CircuitPython's Zephyr port now ships an nRF54L15-DK build; Seeed XIAO nRF54L15 support is an open feature request (#10647, 2025-09); Zephyr-based Arduino core announced 2026-02-17. No mainstream hobby boards; nRF52840 still the shipping wearable platform. New source [S752]; tags replaced. |
| 11 | APA102 eclipsed by SK9822/HD107s clones [S101] | **STILL UNSETTLED** | Remains FastLED-community consensus; vendor listings market HD107s as "fast APA102", but no primary supply-chain source. Tag kept with dated note. |
| 12 | WS2816 specialty-level availability [S123] | **CONFIRMED** | AliExpress WS2816 strips, NLED WS2816 driver modules (more "coming soon" 2026-02-01), World Semi WS2816 family pages — specialty, not commodity. Tag resolved with dated note. |
| 13 | HD108 vendor-direct specialty supply [S131][S132] | **CONFIRMED** | Hida (hd108-led.com) lists 30-144 px/m HD108 strips; Newstar lists NS108/HD108 strips; all vendor-direct. Tag resolved with dated note. |
| 14 | NS108/HD108 one chip type [S100] | **CORROBORATED** | Newstar markets itself as original NS108/HD108 IC developer; vendors sell "HD108 NS108" as one product family. Tag resolved with dated note. |
| 15 | WS2815 12 V regulator efficiency trade-off [S112] | **STILL UNSETTLED** | Consistent with constant-current/linear-regulator design; needs datasheet dissipation figures or bench data. Tag kept with dated note (both at RA-03:32 and the 5-10 m injection-interval claim at RA-03:133). |
| 16 | Differential extender pairs as long-run field standard [S135] | **STILL UNSETTLED** | Ubiquitous vendor practice (F-amp/"pixel amplifier" boards) but no citable vendor doc captured; tag kept with pointer to QuinLED/Falcon differential-board docs. |

## 3. Rot-prone untagged claims

| Claim | Verdict | Evidence (live, 2026-07-03) |
|---|---|---|
| WLED 16.x status | **UPDATED** | v16.0.0 released 2026-05-03 (confirmed); **v16.0.1 tagged 2026-06-30** (was "in progress" in docs); v0.15.5 tagged 2026-04-11 (docs said latest was 0.15.4). Nightlies through 2026-07-02. RA-01 edited. |
| projectMM activity | **CONFIRMED very active** | ewowi/projectMM pushed 2026-07-03 (same day as this audit); not archived. |
| Pixelblaze firmware version | **VERIFIED-FALSE — major correction** | Docs claimed firmware "stalled at v3.47 (2023-07-13)". ElectroMage forum news category (Discourse JSON, cross-checked via search.json): **V3.66 released 2024-12-13** ("Community Patterns... & More LED types", finalizing beta v3.60) and **V3.67 released 2025-11-28** (bugfixes, pb32 + pico32). "Waning/stalled" verdicts corrected in comparison-matrix and RA-01; code-reading/pixelblaze.md corrected. New source [S750] appended. |
| FastLED latest release | **CONFIRMED (nuance)** | Tag `3.10.5` exists, committed 2026-06-23 ("June 2026" claim holds); latest GitHub *release object* is 3.10.4 (2026-06-16). No 4.0 yet — "imminent/unreleased as of 2026-07-03" claims still accurate. No edit needed. |
| HyperHDR v22 status | **CONFIRMED** | Releases: v22.0.0.0beta1 2026-01-06, beta2 2026-05-08 (Infinite Color Engine, adaptive RGBW dithering); no stable v22 yet. Matches [S032]. No edit needed. |

## 2. Load-bearing tag re-verification

(pending)

## 3. Rot-prone untagged claims

(pending)

## Fixes applied

Every in-place edit made this pass (all paths repo-relative to `research/`):

### topics/RA-01-landscape.md
1. L20: WLED — "16.0.1 bugfix milestone in progress" → "16.0.1 shipped 2026-06-30; nightlies through 2026-07-02" [S002][S753]; "latest 0.15.x is 0.15.4" → "0.15.5 (tagged 2026-04-11)".
2. L74 (vendor health): inserted `[VERIFIED-FALSE 2026-07-03: ...]` correction — Pixelblaze firmware did not stall at v3.47; V3.66 (2024-12-13) and V3.67 (2025-11-28) shipped [S750]; reframed v3.47 as last *driver-architecture* release.
3. L109: FPP license tag resolved — enumerated the repo's actual license files (GPL-3.0 + LGPL-2.1 + CC-BY-ND + exception/external) [S022]; tag removed.
4. L220 (open question): resolved YES — V3.66/V3.67 found via Discourse JSON + search.json; tag removed.

### topics/RA-09-hardware-wearable-tier.md
5. L21: RP2350 ~2x — tag replaced with [S751] corroboration note.
6. L27: nRF54 — tag replaced with dated status (CircuitPython Zephyr nRF54L15-DK build; no hobby boards; no displacement) [S752].
7. L35: second RP2350 ~2x tag → [S403][S751].
8. L89 (verdicts): nRF52840 "nRF54 not yet in ecosystem" tag → dated [S752] status.
9. L107 (open question): RP2350 benchmark — updated with [S751] corroboration; fire-benchmark still the settle-with.
10. L112 (open question): Sparkle Motion Mini — resolved: USB-C only ("up to 5V 4A"), no LiPo connector/charger, confirmed against Learn guide [S415]; tag removed.

### synthesis/requirements.md
11. W-2 row: RP2350 tag → [S403][S751] with dated parenthetical.

### synthesis/comparison-matrix.md
12. Pixelblaze maintenance cell: verdict "**Waning** — firmware stalled at v3.47" → "**Stable (slow)**" with inline `[VERIFIED-FALSE 2026-07-03: ...]` correction [S750].
13. xLights/FPP license cell: FPP tag resolved — mixed license enumerated, re-verified 2026-07-03 [S022].

### code-reading/pixelblaze.md
14. §6 ecosystem health: "Firmware: stalled at v3.47" bullet → `[VERIFIED-FALSE 2026-07-03: ...]` with V3.66/V3.67 details [S750].
15. Final open question ("firmware beyond v3.47 shipped silently?") → resolved YES with caveat that driver-pipeline impact of V3.66/V3.67 is unknown.

### topics/RA-10-audio-reactivity.md
16. L35: LedFx ~16 ms — tag KEPT + "(re-checked 2026-07-03: still unsettled...)".
17. L49: WLED audio-sync V2 — tag replaced with the answer: LedFx does NOT implement it (GitHub code search, 0 hits for port 11988/audio_sync, index validated); pewpew must emit the packet itself.
18. L134 (open question 1): re-checked note appended, tag kept.
19. L137 (open question 4): madmom license RESOLVED from LICENSE file — code BSD-2-Clause, models CC BY-NC-SA 4.0 (commercial needs permission); tag removed.
20. L138 (open question 5): BeatNet — tag KEPT + dated note (repo pushed 2026-04-13, CC-BY-4.0; still no SBC benchmark).

### topics/RA-11-dev-ergonomics.md
21. L26: fastled-wasm license conflict — tag KEPT + "(re-checked 2026-07-03: still conflicting — GitHub MIT vs PyPI BSD-3-Clause)".
22. L65: wled-sim — tag resolved into dated facts: dormant since 2025-08-05, 6 stars, AGPL-3.0 (co-run only, don't link); WLED activity refreshed [S753].

### topics/RA-03-led-chips.md
23. L32: WS2815 12 V efficiency — tag KEPT + dated still-unsettled note.
24. L61: WS2816 availability — tag resolved with dated confirmation (AliExpress/NLED/World Semi).
25. L95: APA102 clones — tag KEPT + dated still-unsettled note (community consensus, no primary source).
26. L106: HD108 supply — tag resolved with dated confirmation (Hida/Newstar listings).
27. L112: NS108=HD108 — tag resolved with corroboration (Newstar original-IC-developer marketing; combined product listings) [S131][S132].
28. L127: differential extenders — tag KEPT + dated note (needs QuinLED/Falcon doc).
29. L133: 12 V injection intervals — tag KEPT + dated note.

### topics/RA-01b-python-engine-gap.md
30. Open question (led-control output path): RESOLVED by code read — no gamma (commented out), no dithering, 8-bit `pack_rgbw()` output [S017:ledcontrol/driver/led_render.h @ 8e3fe1d]; tag removed.
31. Open question (ProjectMM/MoonLight trajectory): resolved — MoonLight frozen at v1.0.0, projectMM pushed 2026-07-03; tag removed [S006][S024].

### topics/RA-07-mapping-topology.md
32. L56: FPP VirtualDisplay — tag resolved: file paths confirmed under `src/channeloutput/` (VirtualDisplay/Base/HTTP/HTTP3D) = preview sink, not effect input [S308].
33. L31: Pixelblaze "v3.47 HDR drivers release, 2025" date error → "v3.47 2023-07; V3.66 2024-12; V3.67 2025-11" [S750].
34. L124: verdict line "product active (v3.47, 2025)" → "firmware through V3.67, 2025-11" [S750].

### topics/RA-05-pattern-engines.md
35. L22: "firmware releases continue (v3.47 HDR drivers)" → added V3.66/V3.67 with dates [S750].

### SOURCES.md
36. Appended [S750] (Pixelblaze V3.66/V3.67 forum announcements), [S751] (Adafruit RP2350 speed-test newsletter), [S752] (CircuitPython Zephyr nRF54L15 DK + XIAO feature request), [S753] (WLED releases/tags).
37. [S017]: added `pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6` (set at read time per convention, enabling the path-cite in RA-01b).

### Not edited (verified, no change needed)
- FastLED "3.10.5, June 2026" (tag committed 2026-06-23; latest release *object* 3.10.4 2026-06-16) and "4.0 imminent/unreleased as of 2026-07-03" — both still accurate.
- HyperHDR v22 beta2 2026-05-08 — matches [S032].
- projectMM claims in RA-01 (v2.0.0 2026-06-24, very active) — confirmed by live repo (pushed 2026-07-03).
- architecture.md — no text changes needed: the S403 risk row's mitigation (run fire benchmark) still stands; all other affected claims were corrected at their topic-doc sources. The comparison-matrix Pixelblaze verdict change ("Waning" → "Stable (slow)") does not overturn any ADR: ADR-004 rejects Pixelblaze as receiver on protocol grounds, ADR-005 adopts its authoring *model*, both unaffected by firmware cadence.

### Follow-ups for the RA owners
- comparison-matrix Pixelblaze verdict was corrected by this critic; RA-01 owner should ratify "Stable (slow)" or re-argue.
- S750 needs an archive.org snapshot if any ADR ever cites it (archival rule).
- wled-sim dormancy + AGPL-3.0: architecture.md names it for preview co-sim; fine as a co-run process, but flag if anyone proposes vendoring code.
- fastled-wasm MIT-vs-BSD-3 conflict persists; open an upstream issue before any code reuse (ADR-012 exposure).
