# pewpew — hardware buying list

Procurement reference for the pewpew build. Hardware choices trace to the
research tree — chip/board verdicts live in
[`research/synthesis/architecture.md` §10](../research/synthesis/architecture.md)
and [ADR-013](../research/synthesis/decisions/ADR-013-hardware-bets.md); the
bench BOM lives in [ADR-018](../research/synthesis/decisions/ADR-018-agent-driveable-bench.md).

> **Price provenance.** Prices/availability **verified 2026-07-16** via web
> research (multiple vendor pages). They still move — treat as current-ish, not
> quotes. **Amazon blocks automated price reads**, so some Amazon prices are
> marked *not retrieved*; buy those direct from the maker where a price is
> shown. HD108/WS2816 strip prices are quote-based and were *not retrieved*.
> **Confirm the spec (esp. 5V vs 12V) in the listing title before checkout.**
> Grades are this doc's judgement, not a research verdict.

## How to read the grades

Each option gets two grades: **Product** (how good the part is *for this job*)
and **Vendor** (trust / QC / shipping / stock).

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
skew) plus the basic Phase 1 path. **Eyeball-MVP total: ~$95–120** (verified
picks; see the quick-start cart at the bottom).

> Your Mac is the dev host for now — the Pi 5 / wired-gigabit host is a later
> buy (Section 4). Nothing here requires it.

### 1.1 Receivers — 2× ESP32-S3 (with PSRAM)

The S3 is the pewpew receiver target (RMT-DMA + LCD_CAM parallel output). Get a
**PSRAM variant**. Buy genuine silicon — the Amazon clones are a QC lottery on
PSRAM/USB.

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [Espressif DevKitC-1 **N32R8V** — DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/ESP32-S3-DEVKITC-1-N32R8V/26658348) | ~$16 | **In stock** | **A** | **A** | 32MB flash + 8MB octal PSRAM. Authorized, actually stocked, most GPIO. **Recommended.** |
| [Espressif DevKitC-1 **N8R8** — DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/ESP32-S3-DEVKITC-1-N8R8/15295894) | $15.00 | ⚠️ **Backordered ~8wk** | **A** | **B** | 8MB flash + 8MB PSRAM. Great part, but lead time — prefer N32R8V now. |
| [Unexpected Maker **ProS3[D]** — Adafruit #6398](https://www.adafruit.com/product/6398) | ~$26.50 | In stock | **A** | **A** | 8MB PSRAM, dual-antenna, premium build. *Fewer pins* than DevKitC. (Old #5401 discontinued.) |
| [Unexpected Maker **FeatherS3[D]** — Adafruit #6399](https://www.adafruit.com/product/6399) | ~$24.95 | In stock | **A** | **A** | 16MB flash + 8MB PSRAM, Feather ecosystem. (Old #5399 discontinued.) |
| [HiLetgo ESP32-S3-DevKitC N16R8 — Amazon](https://www.amazon.com/HiLetgo-ESP32-S3-ESP32-S3-DevKit-Bluetooth-Development/dp/B0CDWXWXCG) | *not retrieved* (~$10) | Listed | **B** | **C** | Cheapest, Prime. QC varies; verify PSRAM on arrival. |
| ⚠️ [Adafruit ESP32-S3 Feather "8MB"](https://www.adafruit.com/product/5323) | $17.50 | In stock | **C** | **A** | **"8MB" is flash — NO PSRAM.** Use [the 2MB-PSRAM version #5477](https://www.adafruit.com/product/5477) if you want an Adafruit-brand S3. |

> ⚠️ There is **no authorized `-N16R8` DevKitC-1 SKU** — distributors stock N16
> (no PSRAM), N8R8, and N32R8V. Order a `-1-` (PCB antenna) part, not `-1U-`
> (u.FL connector), unless you want an external antenna.

### 1.2 LED strips — 2× SK6812, 5V, 60 px/m

SK6812 8-bit is *deliberately* the MVP target — it forces the host-side
dithering pipeline (the "better than clown mode" claim) to actually work.
**Note: SK6812 from these vendors is RGBW-only (4 bytes/px)** — the plain-RGB
3-byte equivalent is WS2812B, not "SK6812 RGB."

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [Adafruit NeoPixel RGBW 60/m black, 4m #2837](https://www.adafruit.com/product/2837) | $107.80 (4m) | In stock (~87) | **A** | **A** | = SK6812 RGBW. $19.95/m — best US-vendor value per meter. [white PCB #2842](https://www.adafruit.com/product/2842) same. |
| [Adafruit Mini Skinny RGBW 60/m, 1m #4914](https://www.adafruit.com/product/4914) | $21.95 (1m) | In stock | **A** | **A** | 1m each — no 4m reel needed for a 2-light test. Narrow PCB. **Recommended for MVP.** |
| [BTF-LIGHTING SK6812 RGBW 5V 60/m 5m — Amazon](https://www.amazon.com/BTF-LIGHTING-Individually-Addressable-Flexible-Non-Waterproof/dp/B079ZW1265) | *not retrieved* | Listed | **A** | **B** | One reel = both strips. Cheaper if bought [direct at btf-lighting.com](https://www.btf-lighting.com/products/5v-sk6812-rgbw-addressable-led-strip). |
| [Pololu SK6812 60-LED 5V 1m #2529](https://www.pololu.com/product/2529) | $37.53 (1m) | ⚠️ Low/backorder | **A** | **B** | Reputable but priciest per meter and stock-constrained. |

> ⚠️ Confirm **5V** — BTF also sells a [12V SK6812 RGBW](https://www.btf-lighting.com/products/dc12v-sk6812-rgbw-led-strip-individual-addressable) that won't run off the 5V brick below. RGBW means WLED needs RGBW mode + the DDP output must send the W channel.

### 1.3 Level shifter — SN74AHCT125 (3.3V → 5V)

A "fixed assumption" at 5V (§10). One chip shifts up to 4 data lines, so **one
covers both strips.**

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [Adafruit 74AHCT125 breakout #1787](https://www.adafruit.com/product/1787) | $1.50 | In stock | **A** | **A** | The standard part. **Recommended.** |
| [RGB2Go SN74AHCT125 4-pack](https://rgb2go.com/products/level-shifters-sn74ahct125-pack-of-4) | $9.99 | Listed | **A** | **B** | ~$2.50 ea with spares. |

### 1.4 Power — 5V, ~10A

Two 60px strips ≈ 7A worst-case (full white); real patterns far less. **Fuse
every channel** (§10).

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [ALITOVE 5V 10A — direct](https://alitove.com/products/alitove-5v-10a-power-supply) | $21.99 | In stock (71) | **B** | **B** | ~$8 under Adafruit for the same spec. **Recommended value.** ([Amazon listing](https://www.amazon.com/ALITOVE-Converter-100-240V-Transformer-5-5x2-5mm/dp/B0852HL336) price *not retrieved*.) |
| [Adafruit 5V 10A supply #658](https://www.adafruit.com/product/658) | $29.95 | In stock | **A** | **A** | Clean, 2.1mm jack. |

### 1.5 Wiring bits

Generic; nothing spec-critical. Barrel-jack screw-terminal adapter, JST-SM
pigtails, dupont jumpers, inline fuse holders + fuses, a small breadboard, 2×
USB-C cables. **~$15–20** total from any Amazon/AliExpress kit. Product **B** /
Vendor **C** (commodity; per-item pricing not researched).

### Alternative to 1.1–1.5 — QuinLED all-in-one

Skip the shifter + PSU + wiring: QuinLED boards ship fused, level-shifted, WLED
pre-flashed. **Tradeoff: classic ESP32, not the S3 you'll ship on** — great for
proving sync fast, not for benching the receiver firmware.

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [QuinLED Dig-Uno](https://www.drzzs.com/shop/dig-uno-diy-rgb-led-controller-w-wled-preassembled/) | $18–44 (by variant) | Available | **B** | **A** | Two channels, screw terminals. Low end = base board. |
| [QuinLED Dig2go](https://www.drzzs.com/shop/dig2go/) | $30–71 (by bundle) | Available | **B** | **A** | Self-contained, USB-C, mic + WLED built in. Low end = controller only. |

---

## Section 2 — Measurement add-ons (turn eyeball into data)

The eyeball can't confirm "≤1 frame skew" (§12 item 3) or dither bit-gain
(item 5). These are the first bricks of the ADR-018 bench.

| Item | Option | Price | Avail. | Product | Vendor | Notes |
|------|--------|-------|--------|---------|--------|-------|
| Logic analyzer | [SparkFun 24MHz/8-ch](https://www.sparkfun.com/usb-logic-analyzer-24mhz-8-channel.html) | $26.95 | In stock | **B** | **A** | fx2lafw/sigrok-native; reads both data lines. Also at DigiKey (TOL-18627). |
| Logic analyzer | [Generic 24MHz 8-ch — Amazon](https://www.amazon.com/HiLetgo-Analyzer-Device-Ferrite-Channel/dp/B0FRFF6GLP) | ~$8–12 | In stock | **C** | **C** | Same firmware, cheaper, no support. |
| Photodiode | [TSL257-LF — DigiKey](https://www.digikey.com/en/products/detail/ams-osram-usa-inc/TSL257-LF/3095048) | $2.66 | In stock, ships today | **A** | **A** | Light-to-voltage; the §12 photometry rig. |

> The full agent-driveable bench (Saleae Logic 8, Nordic PPK2, powered hub,
> AR9271 monitor-mode adapter) is **Section 4.4** — not needed for the prototype.

---

## Section 3 — Quality-ceiling / fun (16-bit LEDs)

Not for the MVP — buying these first would *mask* whether your dithering works.
Grab once the 8-bit pipeline is proven, to see the top of the ladder (Q-6).
**HD108 is clocked (4-wire: data+clock); WS2816 is one-wire.** Strip prices are
quote-based and were *not retrieved* — request per-meter USD from the vendor.

| Item | Option | Price | Avail. | Product | Vendor | Notes |
|------|--------|-------|--------|---------|--------|-------|
| HD108/NS108 (5V, clocked) | [NEWSTAR NS108/HD108](https://www.addressableledstrip.com/NS108HD108LEDStrip-34.html) | *not retrieved* | Listed | **A** | **B** | Original IC maker. 16-bit, ~27kHz PWM, densities 30–200/m. |
| HD108 | [Hida HD108 catalog](https://www.hd108-led.com/product-category/hd108-led-strip/) | *not retrieved* | Listed | **A** | **B** | Direct manufacturer, multiple densities. |
| HD108 | [SuperLightingLED HD108 5V](https://www.superlightingled.com/hd108-individually-addressable-rgb-pixel-led-flexible-strip-lights-dc5v-full-color-changing-p-4524.html) | *not retrieved* | Listed | **A** | **B** | Closest to a Western storefront. |
| HD108 | [AliExpress HD108](https://www.aliexpress.com/w/wholesale-hd108-led-strip.html) | varies | Listed | **A** | **C** | Cheapest, small qty; slow shipping, clone risk. |
| WS2816 (one-wire) | [AliExpress WS2816 strip](https://www.aliexpress.com/w/wholesale-ws2816-led-strip.html) | *not retrieved* | Listed | **B** | **C** | Reuses AHCT125; ~half refresh (2 B/ch). Often **12V**. §10: "watch availability." |
| WS2816 driver | [NLED WS2816 MOSFET module](https://store.nledshop.com/index.php/nled-ws2816-mosfet-driver-module.html) | $10.00 | In stock (179) | **A** | **B** | Turns plain 12/24V analog strip into 16-bit pixels. |

---

## Section 4 — Beyond the prototype (full-project needs)

Pointers for later phases — not needed to start. Buy against the specific
phase, not up front.

### 4.1 Host (Phase 0–1, R-8)

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| [Raspberry Pi 5, 8GB — Adafruit #5813](https://www.adafruit.com/product/5813) | ~$95 | In stock | **A** | **A** | Throughput-bench target (§12 item 1/13). Also [PiShop](https://www.pishop.us/product/raspberry-pi-5-8gb/), [CanaKit](https://www.canakit.com/raspberry-pi-5-8gb.html). |
| N100-class mini-PC (16GB) | ~$150–190 | Widely stocked | **A** | **B** | More headroom if the NumPy bench is tight. Amazon, many brands. |
| [Raspberry Pi Zero 2 W](https://www.pishop.us/product/raspberry-pi-zero-2-w/) | $15 | In stock | **B** | **A** | Per-prop portable host only (WiFi-only, 512MB). |

### 4.2 More receivers / room backbone (Phase 3)

| Option | Price | Avail. | Product | Vendor | Notes |
|--------|-------|--------|---------|--------|-------|
| More ESP32-S3 | see §1.1 | — | **A** | **A** | Network receivers. |
| [Falcon F16v5 (bare board)](https://pixelcontroller.com/store/featured/88-f16v5.html) | $280 | In stock | **A** | **B** | 16-port, DDP, Ethernet room backbone (~$17.50/port). [RTR pre-built ~$725](https://pixelcontroller.com/store/featured/95-f16v5rtr.html). |
| [QuinLED Dig-Octa / Dig-Uno](https://www.drzzs.com/shop/) | see §1 | — | **A** | **A** | Fused, level-shifted convenience receivers. |
| Advatek (any) | — | — | **D** | — | Fine gear, priced for paid installs — not this project's budget. |

### 4.3 Custom tiers (Phase 4–5)

| Role | Option | Price | Avail. | Product | Vendor | Notes |
|------|--------|-------|--------|---------|--------|-------|
| Mesh fleet (Ph5) | 25–50× ESP32-S3 w/ PSRAM (§1.1) | ~$16 ea | — | **A** | **A** | One SKU, three firmwares. Buy genuine at fleet scale (clone lottery ×50). |
| Wearable core (W-1/2) | [Pimoroni Pico Plus 2 (RP2350)](https://www.pishop.us/product/pimoroni-pico-plus-2/) | $19.95 | In stock | **A** | **A** | 16MB flash + 8MB PSRAM. "W" wireless ~$18. |
| Wearable BLE (W-5) | [Adafruit Feather nRF52840 Express #4062](https://www.adafruit.com/product/4062) | $24.95 | In stock | **A** | **A** | Best-in-class BLE current. |
| Wearable power (W-6) | 1200–2000mAh LiPo + JST-PH | ~$10–15 | Commodity | **B** | **B** | Software current cap. |

> **Avoid** for wearables: any ESP32 holding SoftAP (~100–130mA radio floor);
> SAMD21-class legacy (too slow). **Avoid** as receivers: ESP8266, ESP32-C3/
> S2/C6, ESP32-P4 (no radio; WLED support WIP) — all **F**.

### 4.4 The agent-driveable bench (ADR-018)

Permanently-assembled rig on the Pi 5/N100 runner. **~$190 core:**

| Item | Price | Avail. | Product | Vendor | Notes |
|------|-------|--------|---------|--------|-------|
| 6× ESP32-S3 devkits (§1.1) | ~$96 | In stock | **A** | **A** | Spares double as fleet spares. |
| uhubctl-verified powered USB hub | ~$30 | — | **B** | **B** | Per-port VBUS power-cycling ("most hubs lie" — buy from the verified list). |
| Logic analyzer + TSL257 (Section 2) | ~$30 | In stock | **B** | **A** | $26.95 + $2.66. |
| [Alfa AWUS036NHA (AR9271)](https://www.amazon.com/Alfa-AWUS036NHA-Wireless-USB-Adaptor/dp/B004Y6MIXS) | ~$30–40 | In stock | **B** | **C** | Monitor-mode ESP-NOW PDR sniffing (Phase 5). Also at Rokland. |
| **~$590 add-on tier:** | | | | | |
| [Saleae Logic 8](https://www.saleae.com/products/logic-8) | $499 | In stock | **A** | **A** | 10 MS/s analog collapses protocol + photometry rigs onto one instrument. |
| [Nordic PPK2 — Adafruit #5048](https://www.adafruit.com/product/5048) | ~$89 | In stock | **A** | **A** | Power profiling + source-meter (wearable current, M-9). |

---

## Quick-start cart (just the prototype)

Recommended, **in-stock, verified-price** picks only:

| # | Item | Qty | Price | Link |
|---|------|-----|-------|------|
| 1 | Espressif DevKitC-1 **N32R8V** | 2 | ~$32 | [DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/ESP32-S3-DEVKITC-1-N32R8V/26658348) |
| 2 | Adafruit Mini Skinny NeoPixel RGBW 1m | 2 | $43.90 | [#4914](https://www.adafruit.com/product/4914) |
| 3 | Adafruit 74AHCT125 shifter | 1 | $1.50 | [#1787](https://www.adafruit.com/product/1787) |
| 4 | ALITOVE 5V 10A PSU | 1 | $21.99 | [alitove.com](https://alitove.com/products/alitove-5v-10a-power-supply) |
| 5 | Wiring bits (fuses, pigtails, jumpers, breadboard) | — | ~$15 | any kit |
| | **Total** | | **≈ $114** | |

**Budget path (~$75):** 2× HiLetgo clone S3 (~$20) + 1× BTF SK6812 RGBW 5m reel
cut in two (~$30 direct) + shifter + PSU + wiring — trades QC certainty and
verified pricing for cost.

**Then to *measure* the sync** (§12 item 3), add [SparkFun logic analyzer](https://www.sparkfun.com/usb-logic-analyzer-24mhz-8-channel.html)
$26.95 + [TSL257-LF](https://www.digikey.com/en/products/detail/ams-osram-usa-inc/TSL257-LF/3095048) $2.66.

> **You can start Phase 0 (the NumPy/Numba throughput bench, §12 item 1) with
> zero of this** — it's pure host code. Hardware only becomes the gate at
> item 3.
