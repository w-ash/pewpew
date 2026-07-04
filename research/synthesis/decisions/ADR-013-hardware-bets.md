# ADR-013: Hardware bets — chips, receivers, hosts, wearable MCUs

Status: Proposed (2026-07-03)

## Context

pewpew's software choices assume specific hardware trajectories: 16-bit
chips exist and are driver-supported (Q-6), receivers are ESP32-class over
DDP (ADR-003/004), hosts never bit-bang pixels (R-8), and the wearable tier
runs on µA-class radios (W-5). Buying against a waning trajectory
(ESP8266, genuine APA102) would strand work. Full buy/avoid detail:
architecture §10; verdict tables in RA-03/RA-08/RA-09.

## Decision

Design around, and buy:

- **Chips**: SK6812/SK6812-RGBW and current-revision WS2812B (5 V tiers);
  WS2815/WS2814 (12 V room tier); HD107s/SK9822 (clocked 8-bit);
  **HD108/NS108 and WS2816 as the 16-bit endgame** the pipeline is built
  for. Chip timing/color-order/bit-depth are per-output config, never
  hardcoded (revisions churn).
- **Receivers**: classic ESP32 for WLED duty today; **ESP32-S3 with PSRAM
  as the default new buy** and the Phase-4 pewpew-receiver target; QuinLED
  boards portable/room; Falcon F16v5-class Ethernet controllers as the
  room backbone; keep existing Pixelblaze output expanders as serial
  sinks.
- **Hosts**: Pi 5 or N100-class mini-PC on wired gigabit (R-8).
- **Wearables**: RP2350 (non-radio) and nRF52840 (BLE); LiPo packs with a
  software current cap (W-6).
- **Fixed practice**: AHCT125-class level shifting at 5 V, ≤10%-drop
  injection sizing, per-channel fusing, xConnect pigtails.

Avoid: ESP8266, ESP32-C3/S2, ESP32-P4 (except Ethernet-attached
experiments), genuine APA102, legacy-revision WS2812B, WS2811 group
strips, ESPixelStick, HinksPix, SAMD21-class wearables, all-day SoftAP
wearables.

## Consequences

- The 16-bit pipeline has real silicon to land on, but HD108/WS2816 supply
  is specialty-tier — 8-bit+dither (ADR-002) stays the volume path for
  now.
- Receiver firmware (Phase 4) targets one chip family (ESP32-S3),
  simplifying the embedded scope.
- Hardware verdicts are dated 2026-07; re-verify supply/pricing at
  purchase time (RA-03/RA-08 open questions).

## Evidence

- [S109][S105] Current WS2812B revisions fix the 400 Hz PWM flicker
  (~2 kHz) and changed reset timing — buy current stock, config per
  output.
- [S114][S115] SK6812: 1.2 kHz PWM, small packages, the RGBW default —
  the wearable workhorse (W-9).
- [S111][S112][S119] WS2815 (backup data line, per-pixel 12 V) and WS2814
  (ascendant commodity 12/24 V RGBW) — the room-tier parts (R-7).
- [S128][S101][S102] Measured: APA102's global brightness is ~440 Hz PWM
  (flicker) while SK9822's is a current source; HD107s does 27 kHz PWM.
  The 3.0 V logic-HIGH threshold is documented for HD108, not HD107s
  (HD107s is vendor-described as 3.3 V-friendly without a stated threshold
  figure — RA-03) — the clocked-family ranking.
- [S130][S100][S122] FastLED merged HD108 support 2025-10-30; WS2816 is
  16-bit on the one-wire ecosystem — the 16-bit bet has driver momentum
  (Q-6).
- [S351][S356] WLED: ESP8266 "should not be used for any new
  installations"; C3/S2 experimental with known bad revisions; classic
  ESP32 the only production-recommended chip.
- [S352] MoonLight targets ESP32-S3/P4, ~130k LEDs with PSRAM — the S3
  trajectory.
- [S353][S355] ESP32-P4 has no onboard radio; hosted WiFi still flaky in
  early 2026 — Ethernet-only early-adopter territory.
- [S357][S358][S359] QuinLED Dig-Next-2/Octa and Falcon F16v5 (16×1,024 px,
  Ethernet+DDP, ~$17.50/port) — the receiver/backbone buys.
- [S367][S368] Pi 5's native pixel output is broken by RP1 and irrelevant
  in a network architecture; FPP 9.x supports Pi 5 as a host (R-8).
- [S410][S412][S403] RP2350 (PIO + best Python throughput) and nRF52840
  (measured best BLE current) — the wearable pair (W-5).
- [S411] ESP32 SoftAP ~100–130 mA with no AP-mode power save — the
  all-day-wearable disqualifier.
- [S133][S135][S369][S370] AHCT125 shifting, ≤10%-drop injection, fusing,
  and xConnect — the fixed electrical practice (P-5, R-7). (Note: S135 and
  S369 are the same QuinLED guide — three independent sources here, not
  four.)

## Rejected alternatives

- **ESP8266 receivers** — deprecated by WLED's own docs; OTA no longer
  fits [S351][S356].
- **ESP32-C3/S2** — single-core stutter, bad board revisions, no LED-duty
  advantage [S351].
- **Genuine APA102** — 440 Hz brightness-field flicker; displaced by
  clones/HD107s [S128][S101].
- **ESPixelStick / HinksPix** — waning firmware and ecosystem mismatch
  respectively [S364][S363].
- **Advatek for this project** — professional pricing for paid installs,
  not a hobby room [S362].
- **Hosts driving pixels directly** — Pi 5 GPIO regression proves the
  fragility; the architecture never needs it [S367].
