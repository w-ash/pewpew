# Hardware refresh — receiver & wearable silicon (2026-08-22)

Requested by the RA owner: the ESP32-S3 is 2020-vintage silicon — given
2025–26 advances in energy efficiency and radio quality, is it still the
right foundation? Method: two parallel research agents (silicon landscape;
LED-firmware ecosystem), **restricted to sources published in 2025–2026**.
New sources S371–S382 (receiver tier) and S422 (wearable tier); full agent
reports summarized here, verdict recorded as a dated note in ADR-013.

## Verdict

**ESP32-S3 with PSRAM stands as the default receiver buy — but it is now
on a clock.** Espressif shipped its true successor, the **ESP32-S31**, into
mass production on 2026-07-27: WiFi 6 + BT 5.4 + 802.15.4 + GbE MAC,
dual-core RISC-V 320 MHz with SIMD, DDR-PSRAM, parallel LCD bus, ~$4.51
[S371]. It beats the S3 on paper on every axis this system cares about,
and is weeks old: no devkits in distribution, no WLED/FastLED port, no
independent radio or power measurements. **Re-run this comparison Q4 2026 /
Q1 2027, and gate any large fleet buy (Phase 4–5) on it.** The two-board
prototype buy proceeds on S3 regardless — it is disposable at that scale.

## Findings

**The S3's position strengthened through 2025–26, not weakened.**
FastLED's S3 parallel paths (16-way I2S, RMT5-DMA) matured across the 2025
release series [S379]; WLED-MM and MoonLight — the projects actually
pushing 16k–130k LEDs — name S3 (+P4) as their primary targets [S378];
QuinLED's 2026 flagship is still *classic* ESP32, putting an S3 buy ahead
of the commercial curve, not behind it [S382]. Espressif guarantees S3
production to 2033 [S372].

**The successor tier is real but not production-grade anywhere.** WLED's
IDF-5 port merged 2026-07-19 and C6/C5/P4 builds exist for WLED 17,
explicitly "absolutely not suitable for production" (OTA and sync
unstable; P4 needs a C6 hosted-WiFi co-processor) [S377][S375]. FastLED's
P4 16-strip driver is untested on hardware [S379]. MoonLight's P4 driver
was weeks old when the project pivoted to ProjectMM [S378].

**Radio/power advances don't move the receiver tier.** WiFi 6's
station-mode benefit for a 60 fps UDP stream is plausible but unmeasured
in any 2025–26 public benchmark found; C5 active-RX current is
same-order with the S3, and streaming power is LED-dominated anyway
[S373][S374]. ESP-NOW v2.5.x supports all current targets, so S3↔C5/C6
mesh interop is a supported configuration — the mesh tier doesn't pin the
fleet to one generation [S380]. No non-Espressif contender touches the
receiver tier: nothing else combines an ESP-NOW-class connectionless P2P
radio with parallel-LED peripherals and PSRAM (Make's 2026 LED-board
roundup is entirely ESP32/RP2350).

**The wearable tier has a shipping upgrade.** Nordic's nRF54L15 (~2× the
nRF52840's power efficiency, BT 6.0 Channel Sounding for cm-level
node-to-node ranging, $9.90 boards) is in full-volume production — a
design-cycle swap for the W-5 slot, no trigger needed [S422]. The
receiver-tier power story of 2025–26 is this, not WiFi silicon.

## Decision triggers (carried into ADR-013)

1. **S31 devkits/WROOM modules in normal distribution + a WLED/FastLED
   port** → S31 supersedes S3 for the Phase 4–5 fleet buy; check Q4 2026 /
   Q1 2027 [S371].
2. **Observed 2.4 GHz congestion failures at 60 fps in real venues** →
   C5's 5 GHz station mode is the escape hatch, at a peripheral cost
   [S373][S374]. (S31 stays 2.4 GHz and would not help.)
3. **WLED 17 ships P4+hosted-WiFi rated production-stable AND the P4
   parallel drivers get hardware-validated** → P4 (2037 longevity, parlio,
   far more RAM/CPU) becomes the premium receiver target [S377][S375].
4. **Wearables**: adopt nRF54L15 over nRF52840 at the next W-5 design
   decision — already justified, no external trigger [S422].

## Date-constraint caveats

The Espressif longevity page [S372] and C5 datasheet are undated living
documents (both accessed 2026-08-22). The WLED compatible-controllers doc
still carries summer-2023 text and was used only as evidence of
documentation lag. The claimed WiFi-6 jitter benefit over the S3's WiFi 4
is marked [NEEDS-VERIFICATION] in S374 — no rigorous 2025–26 measurement
was found either way.
