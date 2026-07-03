# RA-08: Hardware — host-driven tier

Last researched: 2026-07-03
Status: draft
S-ID block: S350–S399

## Key questions

- Which ESP32 variant should new network receivers be (original / S3 / C3 / P4)? Which do WLED and MoonLight target? What is the P4's WiFi story?
- Is the ESP8266 dead as a WLED receiver in 2026?
- QuinLED board lineup: which boards, per-port limits, Ethernet options?
- Dedicated pixel controllers (Falcon F16v5/F48, Advatek, Kulp, ESPixelStick, HinksPix): per-port pixel limits at target fps, Ethernet vs WiFi, price per port.
- Pixelblaze output expander: capabilities, role in a network architecture.
- Render hosts: Pi 5 vs Pi Zero 2 vs mini-PC — does Pi 5's poor native WS2812 output matter when output goes over the network?
- Power practice at room scale: 5 V vs 12 V, injection, fusing, connectors (xConnect).
- Cost per pixel-port across receiver classes.
- Buy/avoid verdicts for portable and room tiers.

## Findings

### ESP32 variants as receivers (WLED / MoonLight targets)

**WLED (upstream, 0.15/0.16 era).** The classic dual-core ESP32 remains the platform WLED recommends for production; the official compatible-controllers page still says of the newer chips: "Some of the newer types like ESP32-C3, ESP32-S2 and ESP32-S3 are experimentally supported, but productive use is not recommended yet because some bugs are suspected" [S351]. ESP32-C3 has two extra strikes: it is single-core, causing "small stutter during Wifi communication", and some "C3 mini V1.0.0" boards on the market have broken WLAN [S351]. ESP32-P4 in upstream WLED is "in a very early experimental stage" [S351]. Classic-ESP32 Ethernet boards (Olimex ESP32-POE, WT32-ETH01) are supported and are the documented answer to WiFi realtime-stream jitter [S351][S165].

**MoonLight (MoonModules, v1.0.0 released 2026-05-06).** MoonLight is "ESP32-only, no legacy baggage" [S352][S006]. Its release notes invert WLED's ranking: "MoonLight v0.6.0 works best on ESP32-S3 and ESP32-P4"; classic ESP32 (d0) and C3 are the constrained tier (~1,024 LEDs), non-PSRAM boards pre-allocate 4,096 LEDs, and PSRAM boards scale to ~130K LEDs [S352]. MoonLight ships a parallel LED driver using the P4's PARLIO peripheral and explicitly supports boards including the ESP32-P4-Nano, QuinLED Dig-Next-2, and M5Stack Atom S3R [S352]. So: for a MoonLight-first architecture buy S3-with-PSRAM today; for a WLED-first architecture buy classic ESP32.

**ESP32-P4 WiFi story.** The P4 has **no built-in radio at all**; WiFi/BLE is delegated to a companion chip — typically an ESP32-C6 — over SDIO/SPI using Espressif's ESP-Hosted (or ESP-AT/ESP-Extconn) stack [S353]. Newer "P4-M3"-style modules integrate the C6 die into the same module package [S354]. The hosted-WiFi path is not yet boring: ESPHome's esp32_hosted integration on a Waveshare P4+C6 board shows unstable WiFi association as of early 2026 [S355][NEEDS-VERIFICATION as to whether this affects MoonLight's stack]. Ethernet on P4 dev boards (e.g. ESP32-P4-Nano, Function-EV) sidesteps the radio question entirely and is the sane way to use a P4 receiver in 2026 [S353].

**Practical variant guidance (receivers).**
- Classic ESP32 (WROOM/WROVER): stable everywhere, cheapest, both firmwares run it; WROVER (PSRAM) preferred for MoonLight [S351][S352].
- ESP32-S3 with PSRAM: MoonLight's sweet spot; WLED upstream still calls it experimental (bugs suspected) but it is widely used in practice [S351][S352].
- ESP32-C3: avoid for LED receivers — single-core stutter, low pin count, known bad-WLAN board revisions [S351].
- ESP32-S2: no reason to buy; same experimental status as S3 with a weaker CPU and no second core [S351].
- ESP32-P4: highest ceiling (PARLIO parallel output, 130K-LED class with PSRAM under MoonLight) but WiFi requires a hosted companion chip and upstream WLED support is embryonic — Ethernet-only early-adopter territory [S352][S353][S351].

### ESP8266 status

Dead for new purchases. WLED's own hardware page: "ESP8266 should not be used for any new installations" [S351]. The 0.16 release cycle still ships ESP8266 binaries, but the platform is squeezed out in practice: 4 MB flash no longer fits full builds for OTA (users need 2-step `_min`-build updates, issues #5576, #5363) [S356], and MoonLight/WLED-MM dropped it entirely as "legacy baggage" [S352][S006]. Existing ESP8266 units are fine as low-count legacy receivers; buy nothing new.

### QuinLED boards

QuinLED (Quindor) is the reference open-hardware ESP32 controller line, sold pre-assembled via drzzs.com and documented at quinled.info [S350].
- **Dig-Uno / Dig-Quad**: the classic 1–2 output and 4-output WLED boards, classic ESP32 (pluggable "QuinLED-ESP32" module available with onboard, external-antenna, or **wired Ethernet** variants), 5–24 V, per-channel fusing [S350].
- **Dig-Next-2** (current-generation small board): dual-core ESP32 with 8 MB flash + 2 MB PSRAM, 2.4 GHz WiFi with external antenna (no Ethernet), 2 level-shifted data outputs, 3 fused power outputs (2×5 A + 1×10 A) with per-channel relay control, 5–48 V input auto-detection, USB-C secondary power, onboard microphone, I2C/Stemma-QT expansion; suggested ~1,200 LEDs total (~600/port) under WLED; "100% compatible with WLED, ESPhome, FastLED, Moonlight" [S357]. MoonLight lists Dig-Next-2 as an explicitly supported board [S352].
- **Dig-Octa**: the room/stage-scale modular system — brainboard with 8 LED channels + Ethernet, stacked on powerboards fused for 30–100 A, 5–48 V, speaking E1.31/Art-Net/DDP over wired Ethernet [S358].

Form-factor fit: Dig-Next-2/Dig-Quad = portable-to-room; Dig-Octa = room-scale with serious power. QuinLED is the natural "buy" for the user's existing WLED/MoonLight ecosystem.

### Dedicated pixel controllers (Falcon, Advatek, Kulp, HinksPix, ESPixelStick)

**Per-port physics first**: WS281x data is ~800 kbit/s ≈ 30 µs/pixel, so one port carries ~800 pixels at 40 fps and ~1,500–1,600 at 20 fps regardless of vendor; Kulp states exactly this ("16 local ports that can each drive 800 pixels ... at 40FPS (1500 at 20fps)") [S360]. Vendor "max pixels per port" numbers above ~800 imply sub-40 fps refresh on full ports.

- **Falcon F16v5** (pixelcontroller.com, USD $280 bare): 16 local outputs + 4 SmartReceiver ports, expandable to 32 strings; 1,024 pixels per output; receives 192 universes of E1.31/Art-Net/**DDP**; 2-port Ethernet switch for daisy-chaining; e-fuses on all outputs with web-UI status; 5–13 V board power; microSD standalone playback with FPP sync [S359]. An F48 variant trades local ports for 48 strings via differential receivers (long-range architecture) [S359][NEEDS-VERIFICATION on current F48 availability/version].
- **Kulp** (kulplights.com): capes for BeagleBone/PocketBeagle running **FPP natively on the controller** — K16A-B: 16 local ports at 800 px/port @40 fps, +4 differential RJ45 ports (16 more strings), audio DAC, optional FM transmitter [S360]. K40D-PB: 10 RJ45 differential ports driving 40 strings from a PocketBeagle [S361]. Kulp = the "controller is also the render host" option since FPP runs on it. Caveat: BeagleBone supply has been shaky for years; watch availability [NEEDS-VERIFICATION].
- **Advatek PixLite Mk3** (advateklighting.com): the professional/architectural tier. A4-S Mk3 drives up to 4,080 RGB pixels over 4 outputs (~1,020/port); E4-S is the Ethernet variant; T8-S is the long-range 8-port model [S362]. Polished, supported, and priced accordingly — overkill for a hobby room but the safe answer for installs that must not fail.
- **HinksPix Pro V3** (HolidayCoro): high-density xLights-show controller; V3 CPU + expansion boards scale to 16,320 pixels, sold in 80-port long-range configurations [S363]. Windows-centric configuration tooling and a holiday-show focus make it a poor match for a Linux/DIY room architecture [S363].
- **ESPixelStick V4** (forkineye): open firmware + small ESP8266/ESP32 pixel stick. V4 firmware has sat in beta since ~2023 (v4.0-beta4, 2023-11), with current development happening in a co-developer's fork and CI artifacts rather than releases; issues still active through 2025 [S364]. Functional but drifting — WLED has effectively won this niche; do not buy new [S364].

**Ethernet vs WiFi**: every controller in this class above the ESP tier is Ethernet-first (Falcon, Kulp, Advatek E-series, HinksPix, Dig-Octa); WiFi at room scale is only defensible for low-count ESP receivers, and even there WLED's own docs steer realtime streaming toward Ethernet [S351][S165].

### Pixelblaze + output expander

The Pixelblaze Output Expander is a serial-to-8-channel WS2812/APA102 driver: it takes a documented 2 Mbps framed serial protocol (magic bytes, channel ID, command, CRC32) and buffers up to 240 RGB / 180 RGBW pixels per channel on the standard board, with level-shifted 5 V outputs; up to 8 boards can share one serial line via address switches (64 channels total) [S365]. The 2 Mbps line supports ~66K pixels/sec — about 2x one WS2812 line — so the expander is a fan-out/level-shift device, not a bandwidth multiplier [S365]. The Pro variant raises buffering to 600–800 pixels per channel [S366]. Crucially the protocol is open (MIT firmware, spec in repo) and host-agnostic — it works from "Pixelblaze or an Arduino/Pi", and Pi4J even documents driving it from a Pi serial port [S365][S366]. That makes the user's existing expanders reusable as dumb output hardware for *any* render host, not just Pixelblaze. Form factor: portable and small-room tiers.

### Render hosts (Pi 5, Pi Zero 2, mini-PCs)

**Does the Pi 5's poor native WS2812 story matter? No — in a network architecture the render host never bit-bangs pixels.** For the record: the Pi 5's RP1 I/O chip broke every legacy GPIO LED library; jgarff/rpi_ws281x now needs a custom `rp1_ws281x_pwm` kernel module, and alternatives use SPI or the RP1's PIO block [S367]. This is exactly why the architecture should keep pixel wiggling on receivers (ESP32/controller hardware) and let hosts emit DDP/E1.31/Art-Net over the network — at which point the Pi 5 is simply a fast, cheap Linux box with gigabit Ethernet.

- **Pi 5**: strong render host — FPP 9.x images officially support "Pi B ... Pi 4, Pi 5, and all Pi Zeros" [S368]; ample CPU for LedFx/FPP/custom Python engines at room scale. Buy if a new SBC host is needed.
- **Pi Zero 2 W**: supported by FPP [S368]; quad-core but 512 MB RAM and **WiFi-only** — fine as a portable render host or FPP remote for a few hundred–few thousand pixels, wrong for a room backbone (no Ethernet without a hat/adapter).
- **Mini-PCs (N100/N150 class)**: for xLights sequencing plus playback, or heavy Python/shader rendering, a ~$150 N100 mini-PC outclasses a Pi 5 with case/PSU/SSD at similar total cost; x86 also simplifies running xLights natively. General market knowledge — no single citation; treat as [NEEDS-VERIFICATION] on 2026 pricing specifics.
- The user's existing Pis are sufficient; buying new render-host hardware is only justified for a dedicated always-on room installation.

### Power: PSUs, injection, fusing, connectors

The QuinLED guides are the de-facto community reference for room-scale power practice [S350][S369]:
- **Injection rule of thumb**: size injection wires for ≤10% voltage drop at calculated current. 12 V tolerates far more drop (1.2 V budget vs 0.5 V) — 10 m runs are workable at 12 V, while dense 5 V strip (144/m) may need injection **every meter** [S369]. This is the core argument for 12 V (WS2815/WS2811) at room scale and 5 V only for short/portable runs.
- **Wire gauge**: 18 AWG is the practical strip-soldering gauge, good for 1–2 m feeds even at 5 V; heavier feeds (12 AWG class) into the controller's screw terminals [S369][S357].
- **Fusing**: fuse every power channel; edge injection points feed LEDs on only one side so they may need different fuse ratings than mid-run injections (QuinLED ships per-channel replaceable blade fuses, e.g. 2×5 A + 1×10 A on Dig-Next-2) [S369][S357]. Commercial controllers use e-fuses with software status instead (Falcon F16v5) [S359].
- **Connectors**: **xConnect** has won the pixel-pigtail war — Ray Wu and xConnect are electrically and mechanically near-identical 3-pin waterproof connectors (nut on opposite genders), but xConnect has one consistent wiring configuration and is stocked by every major pixel store, so it is the standard to buy into for new gear [S370]. Existing Ray Wu stock is fine; just don't mix genders mid-system.

### Cost per pixel-port

Approximate 2026 street prices, per usable WS281x output port (data only, excluding PSU):
- ESP32 devboard + level shifter (DIY): $6–12 for 1–4 usable ports → **$3–8/port**, WiFi only.
- QuinLED Dig-Next-2 (assembled): ~$30–40 for 2 fused, level-shifted ports → **~$15–20/port** with power distribution included [S357][NEEDS-VERIFICATION on current price].
- Falcon F16v5: $280 / 16 local ports → **~$17.50/port**, with Ethernet, e-fuses, DDP, and expansion to 32 [S359].
- Kulp K16A-B class: similar per-port economics to Falcon with FPP running on-board [S360][NEEDS-VERIFICATION on 2026 pricing/stock].
- Advatek PixLite Mk3: several times higher per port — professional support/warranty tier [S362].
- Pixelblaze Output Expander: ~$20–30 for 8 channels of 240-px fan-out → cheap per port but per-channel pixel-count capped [S365][S366].

## Verdicts

- **ESP8266**: **dead** for new installations — WLED's own docs say not to use it for new installs; full builds no longer fit for single-step OTA [S351][S356]. Keep existing units on ≤300-pixel legacy duty.
- **Classic ESP32**: **stable** — still WLED's only "production-recommended" chip in 2026 [S351]. Fine to keep buying while WLED-upstream is the target firmware; expect it to cede to S3 over the next cycle.
- **ESP32-S3 (with PSRAM)**: **ascendant** — MoonLight's primary target ("works best on ESP32-S3 and ESP32-P4"), huge LED ceilings with PSRAM [S352]. The default new-receiver buy.
- **ESP32-C3 / S2**: **avoid** — single-core stutter, bad board revisions, no advantage for LED duty [S351].
- **ESP32-P4**: **premature for WiFi receivers, promising for Ethernet** — no onboard radio (hosted C6 WiFi still flaky in early 2026), upstream WLED "very early experimental", but MoonLight already ships a PARLIO driver and 100K-LED-class capability [S351][S352][S353][S355]. Early-adopter buy only, Ethernet-attached.
- **QuinLED**: **ascendant/stable** — actively developed (Dig-Next-2 generation, MoonLight-supported), the natural fit for the user's WLED fleet [S350][S357][S352]. Recommended buy for portable and room tiers.
- **Falcon F16v5**: **stable** — the DIY-community workhorse for dense room/holiday scale; Ethernet+DDP+e-fuses at ~$17.50/port [S359]. Recommended room-tier backbone if port count exceeds what ESP receivers handle cleanly.
- **Kulp/FPP capes**: **stable but supply-constrained** (BeagleBone dependency) [S360][S361][NEEDS-VERIFICATION]. Only buy if the FPP-on-controller model specifically appeals.
- **Advatek**: **stable, professional tier** — buy for paid installs, not for this project [S362].
- **HinksPix**: **stable but ecosystem-mismatched** (Windows/holiday-show oriented) — avoid for this architecture [S363].
- **ESPixelStick**: **waning** — V4 in beta since 2023, development scattered into forks; WLED owns this niche [S364]. Avoid.
- **Pixelblaze Output Expander**: **stable** — open MIT protocol, host-agnostic; keep and reuse, no need to buy more unless expanding a Pixelblaze rig [S365].
- **Pi 5 as render host**: **recommended** — its native-pixel-output weakness is irrelevant in a network architecture; FPP 9.x supports it [S367][S368].

**Recommended receiver picks**: portable tier → QuinLED Dig-Next-2 or any ESP32-S3-PSRAM board (MoonLight) / classic ESP32 (WLED) [S351][S352][S357]. Room tier → Ethernet-attached receivers: Dig-Octa or Falcon F16v5 backbone, ESP32+Ethernet (Olimex ESP32-POE) for satellite clusters [S358][S359][S351].

## Code-reading queue

1. **MoonModules/MoonLight — parallel LED driver** (`src/` LED driver module, PARLIO/I2S paths): how per-variant output (S3 LCD/I2S vs P4 PARLIO) is abstracted; what per-pin pixel limits and fps assumptions are baked in [S352]. Answers: which receiver chip maximizes pixels/port at 40+ fps.
2. **simap/pixelblaze_output_expander — protocol + firmware** (`README.md` protocol spec, STM32 firmware): exact framing, CRC, draw-all semantics, and per-channel buffer limits — feeds a possible "render host drives expander directly over USB-serial" portable design [S365].
3. **jgarff/rpi_ws281x — rp1_ws281x_pwm kernel module**: confirm Pi 5 output constraints (channel count, DMA) to close the "could the Pi drive pixels directly?" question definitively [S367].
4. **FalconChristmas/fpp — channel output code** (`src/channeloutput/`, DDP/E1.31 senders): how FPP paces multi-controller output; reference implementation for a room-scale sender [S368].
5. **WLED upstream — bus manager / NeoPixelBus integration**: what per-variant output methods (RMT vs I2S vs parallel) upstream uses, to quantify classic-ESP32 vs S3 receiver headroom [S351].

## Open questions

- **Falcon F48v-series current status**: search coverage of F48 v5-era availability/specs was thin; settle via pixelcontroller.com store crawl or Falcon forum. [S359][NEEDS-VERIFICATION]
- **MoonLight on P4 over hosted WiFi**: does MoonLight's ESP-Hosted integration (if any) work reliably, or is P4 Ethernet-only in practice? Settle by reading MoonLight's platformio env for P4 and testing on an ESP32-P4-Nano [S352][S355].
- **Kulp/BeagleBone supply in 2026**: BeagleBone Black availability and whether Kulp has moved to newer SoCs; settle via kulplights.com stock check / forum ask.
- **WLED 0.16 final ESP8266 stance**: 0.16 still ships 8266 binaries; whether 0.17 drops them is unconfirmed. Watch wled/WLED release notes [S002][S356].
- **Exact 2026 prices** for Dig-Next-2, Kulp K16A-B, and mini-PC render hosts — spot-check at purchase time; per-port figures above are directional.
- **Per-port limits at 40 fps for Advatek Mk3** — datasheet PDF not fetched; the 4,080-px A4-S figure's fps assumption is unstated [S362].
