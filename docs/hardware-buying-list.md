# pewpew — hardware buying list

Procurement reference for the pewpew build. Hardware choices trace to the
research tree — chip/board verdicts live in
[`research/synthesis/architecture.md` §10](../research/synthesis/architecture.md)
and [ADR-013](../research/synthesis/decisions/ADR-013-hardware-bets.md); the
bench BOM lives in [ADR-018](../research/synthesis/decisions/ADR-018-agent-driveable-bench.md).

> **Caveats.** Prices are ballpark **as of July 2026** and volatile — treat
> them as order-of-magnitude, not quotes. Retail links are *not* part of the
> cited research sourcing (§10 specifies chip/board *classes*, not SKUs);
> **confirm the spec in the actual listing title before checkout** — sellers
> relabel, and the same product line often has a 12 V variant that won't run
> off a 5 V brick. Grades are this doc's judgement, not a research verdict.

## How to read the grades

Each option gets two grades: **Product** (how good the part is *for this job*)
and **Vendor** (trust / QC / shipping).

| Grade | Meaning |
|-------|---------|
| **A** | Best-in-class for the role. Buy with confidence. |
| **B** | Solid. Minor caveats, no real risk. |
| **C** | Works, but real tradeoffs or a QC lottery. |
| **D** | Fallback only — a known compromise. |
| **F** | Avoid. The research explicitly rejects it, or it's the wrong part. |

---

## Section 1 — Prototype / MVP (two lights in sync)

The smallest kit that proves the core loop: host render engine → DDP over WiFi
→ two independent receivers staying in sync. This is §12 item 3 (DDP Push
skew) plus the basic Phase 1 path. **Eyeball-MVP total: ~$60–90.**

> Your Mac is the dev host for now — the Pi 5 / wired-gigabit host is a later
> buy (see Section 4). Nothing in this section requires it.

### 1.1 Receivers — 2× ESP32-S3 (with PSRAM)

The S3 is the pewpew receiver target (RMT-DMA + LCD_CAM parallel output). Get
a **PSRAM variant** ("R8"). Buy genuine silicon — the Amazon clones are a QC
lottery on PSRAM/USB.

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [Espressif DevKitC-1 **N8R8** — Mouser](https://www.mouser.com/ProductDetail/Espressif-Systems/ESP32-S3-DevKitC-1-N8R8?qs=7D1LtPJG0i2PiuUUKucutQ%3D%3D) | ~$15 ea | **A** | **A** | Official silicon, real PSRAM, most GPIO broken out — best match for the receiver firmware. **Recommended.** |
| [Espressif DevKitC-1 N16 line — DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/ESP32-S3-DEVKITC-1-N16/22320677) | ~$16 ea | **A** | **A** | Same, pick an R8 SKU for PSRAM. |
| [Unexpected Maker **ProS3** — Adafruit](https://www.adafruit.com/product/5401) · [Amazon](https://www.amazon.com/Unexpected-Maker-PROS3-ProS3-ESP32-S3/dp/B09X22YBG7) | $26.50 | **A** | **A** | 8MB PSRAM, premium build, LiPo + low-sleep. Nicer to handle; *fewer pins* than DevKitC. |
| [Unexpected Maker FeatherS3 — Adafruit](https://www.adafruit.com/product/5399) | $24.95 | **A** | **A** | 16MB flash + 8MB PSRAM, Feather ecosystem. |
| [HiLetgo ESP32-S3-DevKitC N16R8 — Amazon](https://www.amazon.com/HiLetgo-ESP32-S3-ESP32-S3-DevKit-Bluetooth-Development/dp/B0CDWXWXCG) | ~$10 ea | **B** | **C** | Cheapest, Prime shipping. QC varies; verify PSRAM on arrival. |
| ⚠️ [Adafruit ESP32-S3 Feather "8MB"](https://www.adafruit.com/product/5323) | $17.50 | **C** | **A** | **"8MB" is flash — NO PSRAM.** Spec says S3 *with* PSRAM; use [the 2MB-PSRAM version](https://www.adafruit.com/product/5477) instead. |

### 1.2 LED strips — 2× SK6812, 5V, 60 px/m

SK6812 8-bit is *deliberately* the MVP target — it forces the host-side
dithering pipeline (the "better than clown mode" claim) to actually work.
RGB = 3 bytes/px (simpler); RGBW = 4 bytes/px (extra channel to drive).

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [BTF-LIGHTING SK6812 **RGBW** 5V 60/m 5m — Amazon](https://www.amazon.com/BTF-LIGHTING-Individually-Addressable-Flexible-Non-Waterproof/dp/B079ZW1265) | ~$30 | **A** | **B** | One reel = both strips (cut every 50cm). Go-to bulk brand. **Recommended.** |
| [BTF-Lighting storefront](https://www.amazon.com/stores/BTF-LIGHTING/page/5C77B767-AD14-4012-8007-E31D2608E529) | — | **A** | **B** | Browse for plain **RGB** SK6812 (simpler for a first test). |
| [Adafruit NeoPixel RGBW 60/m black, 4m](https://www.adafruit.com/product/2837) · [white](https://www.adafruit.com/product/2842) | ~$85/4m | **A** | **A** | Adafruit "NeoPixel RGBW" = SK6812. Premium, pricey per meter. |
| [Adafruit Mini Skinny RGBW 60/m, 1m](https://www.adafruit.com/product/4914) | ~$17 | **A** | **A** | 1m so you're not buying a 4m reel; narrow PCB. |
| [Pololu SK6812 60-LED, 5V, 1m](https://www.pololu.com/product/2529) | ~$26 | **A** | **A** | Well-documented, reputable. |

> ⚠️ Confirm **5V** — BTF also sells a [12V SK6812 RGBW](https://www.btf-lighting.com/products/dc12v-sk6812-rgbw-led-strip-individual-addressable) that won't run off the 5V brick below.

### 1.3 Level shifter — SN74AHCT125 (3.3V → 5V)

A "fixed assumption" at 5V (§10). One chip shifts up to 4 data lines, so **one
covers both strips.**

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [Adafruit 74AHCT125 breakout](https://www.adafruit.com/product/1787) | ~$1.50 | **A** | **A** | The standard part. **Recommended.** |
| [RGB2Go SN74AHCT125 4-pack](https://rgb2go.com/products/level-shifters-sn74ahct125-pack-of-4) | ~$8 | **A** | **B** | LED-hobby vendor; cheaper per unit with spares. |

### 1.4 Power — 5V, ~10A

Two 60px strips ≈ 7A worst-case (full white); real patterns far less. **Fuse
every channel** (§10).

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [Adafruit 5V 10A switching supply](https://www.adafruit.com/product/658) | ~$35 | **A** | **A** | Clean, 2.1mm jack. |
| [ALITOVE 5V 10A — Amazon](https://www.amazon.com/ALITOVE-Converter-100-240V-Transformer-5-5x2-5mm/dp/B0852HL336) | ~$14 | **B** | **B** | Cheaper, explicitly lists SK6812. **Recommended value pick.** |

### 1.5 Wiring bits

Generic; nothing spec-critical. Barrel-jack screw-terminal adapter, JST-SM
pigtails, dupont jumpers, inline fuse holders + fuses, a small breadboard, 2×
USB-C cables to flash. **~$15–20** total from any Amazon/AliExpress kit.
Product **B** / Vendor **C** (commodity).

### Alternative to 1.1–1.5 — QuinLED all-in-one

Skip the shifter + PSU + wiring: QuinLED boards ship fused, level-shifted, WLED
pre-flashed. **Tradeoff: classic ESP32, not the S3 you'll ship on** — great for
proving sync fast, not for benching the receiver firmware.

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [QuinLED Dig2go](https://www.drzzs.com/shop/dig2go/) | ~$35 | **B** | **A** | Self-contained, USB-C powered, mic + WLED built in. Two of these + two strips = whole MVP. |
| [QuinLED Dig-Uno](https://www.drzzs.com/shop/dig-uno-diy-rgb-led-controller-w-wled-preassembled/) | ~$30–40 | **B** | **A** | Two channels per board, screw terminals. |

---

## Section 2 — Measurement add-ons (turn eyeball into data)

The eyeball can't confirm "≤1 frame skew" (§12 item 3) or dither bit-gain
(item 5). These are the first bricks of the ADR-018 bench.

| Item | Option | ~Price | Product | Vendor | Notes |
|------|--------|--------|---------|--------|-------|
| Logic analyzer | [SparkFun USB Logic Analyzer 24MHz/8-ch](https://www.sparkfun.com/usb-logic-analyzer-24mhz-8-channel.html) | ~$15 | **B** | **A** | fx2lafw/sigrok-native; reads both data lines at once. |
| Logic analyzer | [Generic 24MHz 8-ch — Amazon](https://www.amazon.com/Logic-Analyzer-Device-Cable-Channel/dp/B06Y2TTFR1) | ~$10 | **C** | **C** | Same firmware, cheaper, no support. |
| Photodiode | [TSL257-LF — DigiKey](https://www.digikey.com/en/products/detail/ams/TSL257-LF/3095048) | ~$4 | **A** | **A** | Light-to-voltage; the §12 photometry rig. Mouser lists it obsolete — DigiKey has stock. |

> The full agent-driveable bench (Saleae Logic 8, Nordic PPK2, powered
> uhubctl hub, AR9271 monitor-mode adapter) is **Section 4.4** — you don't
> need it for the prototype.

---

## Section 3 — Quality-ceiling / fun (16-bit LEDs)

Not for the MVP — buying these first would *mask* whether your dithering works.
Grab once the 8-bit pipeline is proven, to see the top of the ladder (Q-6).
**HD108 is clocked (4-wire: data+clock); WS2816 is one-wire.**

| Item | Option | ~Price | Product | Vendor | Notes |
|------|--------|--------|---------|--------|-------|
| HD108/NS108 (5V, clocked) | [NEWSTAR NS108/HD108 strip](https://addressableledstrip.com/NS108HD108LEDStrip-34/19.html) | ~$40+ | **A** | **B** | Original IC maker. 16-bit, ~27kHz PWM, APA102-family. |
| HD108 | [Hida HD108 catalog](https://www.hd108-led.com/product-category/hd108-led-strip/) | varies | **A** | **B** | Direct manufacturer, multiple densities. |
| HD108 | [SuperLightingLED HD108 5V](https://www.superlightingled.com/hd108-individually-addressable-rgb-pixel-led-flexible-strip-lights-dc5v-full-color-changing-p-4524.html) | varies | **A** | **B** | Closest to a Western storefront. |
| HD108 | [AliExpress HD108](https://www.aliexpress.com/w/wholesale-hd108-led-strip.html) | cheapest | **A** | **C** | Small quantities; slow shipping, clone risk. |
| WS2816 (one-wire, 16-bit) | [WorldSemi WS2816 family](http://www.world-semi.com/ws2816-family308/) | — | **A** | **B** | Reuses the AHCT125 shifter; ~half the refresh (2 bytes/ch). §10: "watch availability." |
| WS2816 | [AliExpress WS2816 strip](https://www.aliexpress.com/w/wholesale-ws2816-led-strip.html) | ~$20–40 | **B** | **C** | Most common retail; often **12V** — needs a 12V supply. |
| WS2816 driver | [NLED WS2816 MOSFET module](https://store.nledshop.com/index.php/nled-ws2816-mosfet-driver-module.html) | varies | **A** | **B** | Turns plain 12/24V analog strip into 16-bit pixels. |

---

## Section 4 — Beyond the prototype (full-project needs)

Pointers for later phases — not needed to start. Grades are coarser here; buy
these against the specific phase, not up front.

### 4.1 Host (Phase 0–1, R-8)

| Option | ~Price | Product | Vendor | Notes |
|--------|--------|---------|--------|-------|
| [Raspberry Pi 5, 8GB](https://www.raspberrypi.com/products/raspberry-pi-5/) | ~$80 | **A** | **A** | Wired gigabit; the throughput-bench target (§12 item 1/13). Its broken native WS2812 output is irrelevant — receivers do the pixel wiggling. |
| N100-class mini-PC | ~$150–200 | **A** | **B** | More headroom if the NumPy bench (item 1) is tight. |
| [Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) | ~$15 | **B** | **A** | Per-prop portable host only (WiFi-only, 512MB). |

### 4.2 More receivers / room backbone (Phase 3)

- **Network receivers:** more ESP32-S3 (§1.1), or [QuinLED Dig-Octa / Dig-Uno](https://www.drzzs.com/shop/) for fused, level-shifted convenience. Product **A** / Vendor **A**.
- **Room Ethernet backbone:** Falcon F16v5 (16×1,024px, DDP, ~$17.50/port) — buy from [Falcon Christmas store](https://pixelcontroller.com/). Product **A** / Vendor **B**. Advatek is fine gear but priced for paid installs (**D** for this project's budget).
- **Wired satellites:** Olimex ESP32-POE-class boards. Product **A** / Vendor **B**.

### 4.3 Custom tiers (Phase 4–5)

- **Mesh fleet (Phase 5):** 25–50× ESP32-S3 w/ PSRAM — one SKU, three firmwares (node / gateway / bridge). Same options as §1.1; buy genuine at fleet scale to avoid the clone lottery ×50. Prefer clocked chips (HD107s/SK9822) or ≤74px/line one-wire runs so the ≥400Hz dither budget survives (M-6).
- **Wearable non-radio core (W-1/W-2):** RP2350 boards — [Pimoroni](https://shop.pimoroni.com/) / [Adafruit](https://www.adafruit.com/) (~$10–12). Product **A** / Vendor **A**.
- **Wearable BLE tier:** nRF52840 (LED Glasses Driver-class / Feather nRF52840, ~$25). Best-in-class BLE current. Product **A** / Vendor **A**.
- **Wearable power:** 1200–2000mAh LiPo + JST-PH, software current cap (W-6). Product **B** / Vendor **B** (commodity).

> **Avoid** for wearables: any ESP32 that must hold SoftAP (~100–130mA radio
> floor); SAMD21-class legacy boards (too slow). **Avoid** as receivers:
> ESP8266, ESP32-C3/S2/C6, ESP32-P4 (no radio; WLED support WIP) — all **F**.

### 4.4 The agent-driveable bench (ADR-018)

Permanently-assembled rig on the Pi 5/N100 runner. **~$200 core:**

| Item | ~Price | Product | Vendor | Notes |
|------|--------|---------|--------|-------|
| 6× ESP32-S3 devkits | ~$90 | **A** | **A** | See §1.1 — spares double as fleet spares. |
| uhubctl-verified powered USB hub | ~$30 | **B** | **B** | Per-port VBUS power-cycling ("most hubs lie" — buy from the verified list). |
| fx2lafw logic analyzer + TSL257 jigs | ~$20 | **B** | **A** | See Section 2. |
| AR9271 monitor-mode WiFi adapter | ~$15 | **B** | **C** | Mainline monitor mode for ESP-NOW PDR sniffing (Phase 5). |
| **~$500 tier adds:** | | | | |
| [Saleae Logic 8](https://www.saleae.com/) | ~$400 | **A** | **A** | 10 MS/s analog collapses protocol + photometry rigs onto one instrument. |
| [Nordic PPK2](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2) | ~$100 | **A** | **A** | Power profiling + source-meter (wearable current, M-9). |

---

## Quick-start cart (just the prototype)

Minimum to see two lights sync, recommended picks only:

1. **2× [Espressif DevKitC-1 N8R8](https://www.mouser.com/ProductDetail/Espressif-Systems/ESP32-S3-DevKitC-1-N8R8?qs=7D1LtPJG0i2PiuUUKucutQ%3D%3D)** — ~$30
2. **1× [BTF SK6812 RGBW 5V 5m](https://www.amazon.com/BTF-LIGHTING-Individually-Addressable-Flexible-Non-Waterproof/dp/B079ZW1265)** (cut in two) — ~$30
3. **1× [Adafruit 74AHCT125](https://www.adafruit.com/product/1787)** — ~$1.50
4. **1× [ALITOVE 5V 10A PSU](https://www.amazon.com/ALITOVE-Converter-100-240V-Transformer-5-5x2-5mm/dp/B0852HL336)** — ~$14
5. **Wiring bits** (fuses, pigtails, jumpers, breadboard) — ~$15

**≈ $90.** Add the [SparkFun logic analyzer](https://www.sparkfun.com/usb-logic-analyzer-24mhz-8-channel.html) (~$15) + [TSL257](https://www.digikey.com/en/products/detail/ams/TSL257-LF/3095048) (~$4) once it's blinking, to *measure* the sync instead of eyeballing it.

> **You can start Phase 0 (the NumPy/Numba throughput bench, §12 item 1) with
> zero of this** — it's pure host code. Hardware only becomes the gate at
> item 3.
