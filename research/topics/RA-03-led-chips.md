# RA-03: LED chips & electrical limits

Last researched: 2026-07-03
Status: draft
S-ID block: S100–S149

## Key questions

- One-wire family (WS2812B incl. revisions, WS2815, SK6812 RGBW, TM1814, WS2814, 2024–2026 newcomers): timing, voltage, PWM rate, reset time, gotchas?
- Data-rate math: at 800 kbps, max refresh rate vs strip length — where is the temporal-dithering ceiling?
- Clocked family (APA102/SK9822/HD107s/HD108/NS108): real PWM numbers, 16-bit availability/pricing/form factors/driver support?
- Electrical practice: level shifting, data integrity over distance, differential extenders, power injection rules of thumb, 5 V vs 12 V per form factor?
- Which chips are ascendant vs waning — what should pewpew design around per form factor?

## Findings

### One-wire (clockless) family

#### WS2812B (WorldSemi) — the default, but a moving target

- 5 V supply, GRB order, 800 kbps one-wire data, 24 bits/pixel [S108].
- **Datasheet revisions materially changed timing.** Classic parts specify a >50 µs reset (latch) time [S108]; the V5 datasheet raises RESET to **>280 µs**, explicitly "to prevent wrong reset during interruption and support lower-frequency, inexpensive MCUs" — old and new parts are mutually incompatible if a driver idles the line between 50 and 280 µs [S105][S104]. WorldSemi only publishes the latest revision, so third-party PDFs (Adafruit, Pololu) still circulate the old timings [S105].
- Bit-cell timing also drifted across revisions (T1L/RES vary; base cell ~208 ns for WS2812B vs ~166 ns for original WS2812) [S104][S107]. Community reverse-engineering (cpldcpu) established the parts are far more tolerant than any single datasheet: what matters is the T0H/T1H threshold and total period, so a single "universal" timing can drive most revisions [S107].
- **PWM (scan) frequency: classic WS2812B ≥400 Hz** [S108]; newer parts (WS2812B-2020, V5 family) refresh at **~2 kHz**, marketed as fixing camera flicker/POV artifacts [S109]. 400 Hz PWM is the single biggest quality liability of legacy WS2812B for wearables/POV [S109].
- Form factors: 5050, 3535, 2020 (WS2812B-2020), and mini 1615 packages; ubiquitous in strips, matrices, rings, PCBs [S109].
- Practical driver note: FastLED/NeoPixelBus both carry timing tweaks tracking these revisions (e.g. FastLED #1311 for V5, NeoPixelBus #795 for WS2815-compatible timing) — chip-revision churn is absorbed at the library layer [S104][S110].
#### WS2815 — 12 V with backup data line

- 12 V supply, WS2812-compatible one-wire protocol at 800 kbps; each pixel remains individually addressable (unlike 12 V WS2811, which groups 3 LEDs per IC) [S111][S112].
- **Backup data input (BI):** each pixel receives data on both DIN and BIN; if DIN sees no signal (e.g. a dead upstream pixel), the pixel switches to BIN, so one failed IC does not kill the rest of the chain [S111][S112]. Wiring gotcha: BI must be tied to GND at the strip head, not left floating [S113].
- Constant-current drive of ~15 mA per pixel at full white regardless of supply sag; 12 V + constant current means far less color shift down long runs and roughly 1/3 the injection current of 5 V strips for the same pixel count [S111][S112].
- Trade-off: at 12 V each pixel burns the full voltage across its regulator, so per-LED efficiency is lower than 5 V WS2812B; power dissipation is in the chip, not the wire [S112][NEEDS-VERIFICATION] (re-checked 2026-07-03: still unsettled — consistent with the constant-current/linear-regulator design in [S112], but needs WS2815 datasheet dissipation figures or a bench measurement to close).
- Timing is WS2812-family; NeoPixelBus unified its ESP32 RMT timing to cover WS2815 [S110].
- Form factor: strips (30/60/144 LED/m) — the de-facto choice for room-scale/architectural runs; not offered in tiny packages, so irrelevant to wearables [S112].

#### SK6812 (Opsco/"SK") — WS2812 clone family, and the default RGBW part

- Protocol-compatible with WS2812 (800 kbps, GRB / GRBW), 5 V [S114].
- **PWM ~1.2 kHz** vs classic WS2812B's 400 Hz — visibly better on camera and for POV; also reputed to have wider timing margins than WS2812B [S115][S114].
- The **RGBW variants (SK6812-RGBW, in NW/CW/WW white temps) are the established 4-channel part**: 32 bits/pixel, true white die. RGBW at 800 kbps costs 33% more data time per pixel than RGB [S114].
- Form factors: 5050, 3535, 2427, 1515 (mini) — widely used in wearables and matrices; supported by every mainstream driver library (FastLED, NeoPixelBus, WLED) [S114][S115].

#### TM1814 (Titan Micro) — 12 V RGBW with settable current

- 4-channel (WRGB order, 32 bits/pixel) 12 V constant-current driver, 800 kbps one-wire [S116][S117].
- **Per-channel constant current is programmable 6.5–38 mA** via a preamble data frame (6-bit current setting) — a real analog brightness control that preserves 8-bit PWM resolution [S116][S117].
- **Protocol gotchas:** requires an inverted data signal relative to WS2812 conventions (many level shifters invert anyway), and expects a periodic settings frame; it is *not* WS2812-timing-compatible at the frame level [S117]. Supported by WLED, Advatek and similar pixel controllers, and by Adafruit's CircuitPython driver [S117][S118].
- Niche verdict inputs: used mostly in 12 V RGBW strip products; less commodity than WS-family [S118].

#### WS2814 — WorldSemi's 12 V/24 V RGBW answer (newer, ascendant in RGBW strips)

- 4-channel RGBW, 12 V or 24 V variants, one-wire 800 kbps, marketed as "similar SK6812 RGBW" and driveable by SK6812-RGBW-capable controllers [S119].
- Datasheet: 4-output-channel driver with 20 V-rated programmable constant-current outputs; data order RGBW, high bit first [S120].
- **Color-order gotcha:** real strips do not match SK6812 GRBW mapping — with a GRBW config, blue input drives the white die and white drives blue; drivers need a distinct WS2814 color-order entry (Pixelblaze added explicit support after user reports) [S121].
- Availability 2024–2026: heavily stocked by BTF-Lighting and peers in 12 V/24 V RGBW/RGBWW/RGBCW strips; effectively the commodity successor for 12 V RGBW [S119].
#### WS2816 — 16-bit one-wire (the notable newcomer)

- WorldSemi's 16-bit-per-channel one-wire RGB part: 48 bits/pixel GRB high-bit-first, 65,536 grayscale levels per color, with **built-in 4-bit gamma correction** and ~**10 kHz refresh** [S122][S123].
- Same one-wire electrical scheme as WS2812 family, so it reuses existing pin/driver hardware, but doubles the data per pixel (halves max pixels per frame at 800 kbps) [S122].
- Driver support: FastLED added WS2816 support with a dedicated controller (from v3.9.x; FastLED applies no software gamma since the chip does it in hardware); NeoPixelBus tracked support in issue #357 [S122][S124].
- Availability is strip/2020-package level (e.g. WS2816B-2020); far less commodity than WS2812B as of 2026 — worth watching, not yet the safe default [S123] (re-checked 2026-07-03: confirmed specialty-level — WS2816 strips on AliExpress, NLED driver modules shipping with more "coming soon" as of 2026-02, World Semi lists the WS2816 family; nowhere near WS2812B ubiquity).

#### Other 2024–2026 currents

- **FCOB/COB addressable strips** (continuous phosphor over dense chips, WS2811-driven, incl. RGBCCT dual-IC variants and 840–960 LED/m densities) are the big form-factor trend for seamless architectural looks [S125].
- Market drift toward **24 V and 48 V pixel systems** for long runs with fewer injection points [S126].

### Data-rate math: the refresh / dithering ceiling

One-wire chips all run a fixed ~800 kbps, 1.25 µs/bit [S108]. Per-pixel wire time: 24-bit RGB = 30 µs; 32-bit RGBW = 40 µs; 48-bit WS2816 = 60 µs. Frame time = N × t_pixel + reset (50 µs legacy, ≥280 µs on current WS2812B-V5 [S105]). Max refresh per data line (RGB, 280 µs reset):

| Pixels/line | Frame time | Max refresh |
|---|---|---|
| 100 | 3.28 ms | ~305 Hz |
| 150 | 4.78 ms | ~209 Hz |
| 300 | 9.28 ms | ~108 Hz |
| 600 | 18.3 ms | ~55 Hz |
| 1000 | 30.3 ms | ~33 Hz |

(RGBW: multiply pixel time by 4/3; WS2816: by 2.)

**The dithering ceiling:** FastLED's temporal dithering fakes extra brightness depth by flipping low-order bits across successive show() calls; its quality is directly proportional to how often the strip can be refreshed — "the more often your code calls FastLED.show() … the higher-quality the dithering will be" [S127]. Community guidance treats a few hundred Hz as the point where dithering is invisible, which by the table above caps a dithered one-wire line at roughly **100–150 RGB pixels**; beyond that, dithering visibly flickers and long strips must either drop dithering, split across parallel output pins (8–16-way parallel on ESP32/Teensy restores the per-line budget), or move to clocked chips [S127][S124]. This ceiling — not raw frame rate — is the binding constraint for high-fidelity low-brightness output on WS281x [S127].

### Clocked (SPI-style) family

Two-wire (data+clock) SPI-style chips have no fixed bit rate: the controller sets the clock, so refresh scales with achievable SPI speed, and there is no reset-time tax. The trade is 4 wires and roughly double the strip cost.

#### APA102 vs SK9822 — same protocol family, different silicon (measured, not marketing)

cpldcpu's photodiode measurements are the authoritative numbers [S128]:
- **APA102: >19 kHz color PWM** (~19.2 kHz), but the 5-bit **global brightness field is a second, slow PWM at ~440 Hz** layered on top — using global brightness on APA102 reintroduces low-frequency flicker [S128].
- **SK9822: 4.7 kHz color PWM** (4× slower than APA102), but **global brightness is a programmable current source, not PWM** — dimming via the 5-bit field is flicker-free and preserves full 8-bit PWM resolution. This is the mechanism FastLED's "pseudo-13-bit" HD gamma mode exploits [S128].
- Update semantics differ: APA102 updates each pixel's registers immediately as data arrives (staggered along the strip); SK9822 latches all pixels simultaneously on a 32-zero-bit reset frame. A unified driver sends: 32×0 start frame, LED frames, 32×0 reset frame, then n/2 clock-bits end frame — compatible with both [S128].
- APA102's clock is regenerated through each pixel with a half-cycle delay, which is why the end frame must supply n/2 extra clocks and why very long strips self-limit the usable clock rate; short strips run at 10–20 MHz+ SPI [S129].
- Genuine APA102 supply has been eclipsed by clones; most "APA102" strips sold since ~2020 are SK9822 or HD107s silicon [S101][NEEDS-VERIFICATION] (re-checked 2026-07-03: still unsettled — remains the FastLED-community consensus and matches vendor listings marketing HD107s as "fast APA102", but no primary supply-chain source found; treat as strong community knowledge).

#### HD107s (Hida/Shenzhen) — the modern APA102 replacement

- APA102 protocol-compatible, same 5050/2020 footprints, **27 kHz color PWM** (highest of the 8-bit clocked parts, excellent for POV/camera), vendor-claimed data clock up to 40 MHz [S101][S102].
- Widely available in strips and 2020 packages from Hida, Newstar, iPixel and the usual strip vendors; this is what "fast APA102" listings actually ship in 2026 [S101][S102].

#### HD108 — 16 bit/channel clocked

- Same footprint as APA102C/HD107s; protocol is APA102-style but with 16 bits per color channel (64-bit pixel frames: 16-bit brightness/marker field + 3×16-bit color), 27 kHz PWM; logic HIGH threshold 3.0 V, so 3.3 V MCUs drive it at 5 V supply without a level shifter [S102][S100].
- **Driver support matured in 2025:** FastLED merged native HD108 support on 2025-10-30 (PR #2119), ending years of "roll your own SPI" (issue #1045 dates to 2021) [S130][S100].
- Availability: strips from Hida (e.g. 48 px/m 16-bit strips) and Newstar; still a specialty item next to WS281x/HD107s — pricing runs well above 8-bit clocked strips and stock is vendor-direct (Hida, Newstar, iPixel/AliExpress) rather than commodity [S131][S132] (re-checked 2026-07-03: confirmed — Hida's hd108-led.com lists 30/48/60/72/84/96/144 px/m HD108 strips and Newstar lists NS108/HD108 strips, all vendor-direct; still no commodity channel).
- Why it matters: native 16-bit kills the need for temporal dithering entirely — the low-brightness fidelity problem WS281x solves in software is solved in silicon [S100][S102].

#### NS108 (Newstar) — second source for 16-bit

- Newstar's NS108 is marketed as HD108-compatible: 16-bit/channel, 27 kHz PWM, same APA102-style clocked protocol; sold as chips and strips [S103][S132].
- FastLED's HD108 discussion treats NS108/HD108 as one chip type; a driver targeting HD108 covers NS108 [S100] (re-checked 2026-07-03: corroborated — Newstar markets itself as the original NS108/HD108 IC developer and vendors list "HD108 NS108" strips as one product family; Hida sells "16bit 65536 HD108 NS108" strips [S131][S132]).

### Electrical practice

#### Level shifting (3.3 V MCU → 5 V data)

- WS281x on a 5 V supply wants VIH ≈ 0.7 × VDD = 3.5 V; a 3.3 V ESP32/RP2040 output is marginal and works only by luck/short wires. The standard fix is a **74AHCT125 / SN74AHCT125N** buffer (5 V-supplied, TTL 3.3 V-friendly input threshold, fast enough for 800 kbps): GPIO → 1A, 1Y → series resistor → DIN, OE tied low [S133][S138].
- Alternatives with trade-offs: the **"sacrificial pixel"** (first LED fed ~4.3 V via a diode drop so its regenerated output swings full 5 V for the rest of the strip) is a $0.20 fix [S134]; generic bidirectional MOSFET I2C shifters are too slow and a known failure source at 800 kHz [S133].
- A series resistor of roughly 62–470 Ω at the strip's data input damps reflections/ringing; built into most commercial controllers [S138][S133].
- Chips with a **3.0 V logic threshold (HD107s/HD108/NS108)** sidestep shifting entirely for 3.3 V hosts [S102].

#### Data integrity over distance

- Single-ended WS281x data is good for only a few meters of wire between controller and first pixel (community practice: ≤2–3 m shifted, less unshifted); each pixel reshapes/regenerates the signal, so pixel-to-pixel distance is the spec, not total strip length [S138][NEEDS-VERIFICATION].
- Ethernet cable is a poor power carrier and mediocre for single-ended pixel data; QuinLED documents why Cat5e/6 should not be used for LED power runs [S139].
- For long controller-to-strip runs the field-standard answer is a **differential (RS485-style) extender pair** — "pixel amplifier"/F-amp style transmit/receive boards over twisted pair — turning the one-wire signal into differential for tens of meters, then back [S135][NEEDS-VERIFICATION] (re-checked 2026-07-03: still unsettled — practice is ubiquitous in vendor stores (F-amp/"pixel amplifier" boards) but needs a citable vendor doc or datasheet; grab QuinLED or Falcon differential-board docs next pass). Clocked chips (APA102 family) tolerate long runs better by slowing the clock, at refresh cost [S129].

#### Power injection and 5 V vs 12 V vs 24 V

- Planning numbers: 5 V WS2812B draws up to ~60 mA/pixel at full white (18 W/m at 60 LED/m theoretical); QuinLED's measured tables show real full-white draw is somewhat lower, but budgets should use measured-per-strip numbers rather than folklore [S136].
- **Voltage-drop rule of thumb: keep drop ≤10% (0.5 V on 5 V)**; on 5 V strips this forces injection roughly every 2.5–5 m (e.g. a 15 m/900-LED run needs front, middle and end injection), with 20 AWG acceptable only for short feeds and 13–14 AWG for long ones [S135].
- 12 V (WS2815/WS2814) cuts current ~3× for the same wattage and the constant-current pixels mask residual droop — injection intervals stretch to roughly 5–10 m [S112][S135][NEEDS-VERIFICATION] (re-checked 2026-07-03: still unsettled — the ~3× current arithmetic is sound, the 5–10 m interval remains community practice without a measured source). The 2026 market is drifting further to 24 V/48 V for architectural runs [S126].
- A hybrid pattern for big 5 V installs: distribute 24 V and buck-convert to 5 V locally at each injection point [S137].
- **Per form factor:** wearables → 5 V (single-cell Li-ion + boost, small packages: SK6812 3535/1515, WS2812B-2020); portable props → 5 V short runs, level-shifted, one or two injection points; room-scale → 12 V WS2815/WS2814 (or 24 V FCOB/WS2814-24V) with fused multi-point injection [S112][S119][S135].

## Verdicts

| Chip | Verdict | Rationale |
|---|---|---|
| WS2812B (V5/2020) | **Stable (dominant)** | Ubiquitous, every library tracks its revisions; 2 kHz PWM on current parts fixes the worst flicker [S104][S109]. Design for it, but never hard-code one datasheet's timing/reset [S105][S107]. |
| WS2811 (external IC, 12 V, 3-LED groups) | **Waning** | Displaced by per-pixel WS2815/WS2814 and FCOB; survives only in bullet pixels [S126][S125]. |
| WS2815 | **Stable** | The room-scale 12 V RGB default: per-pixel, backup data line, relaxed injection [S111][S112]. |
| SK6812 / SK6812-RGBW | **Stable** | The RGBW default at 5 V and the wearable workhorse (small packages, 1.2 kHz PWM) [S114][S115]. |
| TM1814 | **Stable-niche** | Settable current is unique but inverted-signal/settings-frame protocol keeps it niche [S117]. |
| WS2814 | **Ascendant** | Commodity 12/24 V RGBW successor; driver support landed 2023–2025; mind the color-order trap [S119][S121]. |
| WS2816 | **Ascendant (watch)** | 16-bit + hardware gamma + 10 kHz refresh on the existing one-wire ecosystem; FastLED support present, availability still thin [S122][S123]. |
| APA102 (genuine) | **Waning** | 440 Hz global-brightness PWM flicker and clone displacement; buy HD107s instead [S128][S101]. |
| SK9822 | **Stable** | Current-source global brightness enables pseudo-13-bit dimming; the budget clocked choice [S128]. |
| HD107s | **Ascendant** | 27 kHz PWM, 40 MHz clock, 3.3 V-friendly; the de-facto APA102 of 2026 [S101][S102]. |
| HD108 / NS108 | **Ascendant (specialty)** | 16-bit in silicon ends the dithering problem; FastLED support merged 2025-10-30; supply still vendor-direct [S130][S100][S131]. |

**What pewpew should design around:** per form factor — wearable: 5 V SK6812 (RGBW) / WS2812B small packages, with HD107s/HD108 as the POV/high-fidelity option [S114][S102]; portable: same 5 V one-wire plus AHCT125 shifting as a fixed design assumption [S133]; room-scale: 12 V WS2815 (RGB) / WS2814 (RGBW) with multi-point injection [S112][S119][S135]. Architecturally: treat chip timing/color-order/bit-depth as a per-output config (revisions churn), keep the frame pipeline ≥16-bit internally so HD108/WS2816 outputs are lossless, and model the per-line refresh budget (dithering ceiling) as a first-class constraint [S127][S130][S122].

## Code-reading queue

1. **FastLED — HD108 controller (PR #2119: `src/chipsets.h` HD108 path)** [S130]: how 16-bit color + 5/16-bit brightness fields are packed and what API shape 16-bit output takes — informs pewpew's internal pixel format.
2. **FastLED — five-bit HD gamma (`src/fl/five_bit_hd_gamma.cpp`)**: how the SK9822/APA102 5-bit global field is fused with 8-bit PWM into pseudo-13-bit output [S128] — the software model for clocked-chip fidelity.
3. **FastLED — temporal dithering (`src/controller.h` / dither logic)** [S127]: exactly how dither state advances per show(); quantifies the refresh-rate dependence behind the dithering ceiling.
4. **NeoPixelBus — method/feature matrix (`src/internal/methods`, PR #795)** [S110]: how a mature library parameterizes one-wire timing across WS2812 revisions/WS2815/SK6812 — the timing-config surface pewpew should mirror.
5. **WLED — bus manager (`wled00/bus_manager.cpp`) chip/color-order tables** : how WS2814 color-order and TM1814 current-setting quirks are exposed to users [S121][S117].

## Open questions

- Exact WS2812B-V5 T0H/T1H/T0L/T1L min/max from the official PDF — LCSC PDF not machine-readable in this pass; settle by downloading the PDF and transcribing the AC characteristics table [S106].
- Real 2026 street pricing for HD108/NS108 strips vs HD107s/SK9822 (vendor-direct quotes needed; no public price lists found) [S131][S132].
- Whether NS108 is bit-exact HD108-compatible (shared driver) or merely "close" — settle with a hardware test or FastLED issue archaeology [S100][S103].
- Maximum reliable SPI clock for HD107s/HD108 at realistic strip lengths (vendor claims 40 MHz; community measurements needed) [S102].
- WS2815 per-pixel efficiency penalty vs 5 V parts (regulator dissipation) — needs a measured W-vs-lumen comparison [S112].
- WS2816 availability breadth in 2026 (packages beyond 2020? major strip vendors?) [S123].
- Verified maximum single-ended data run lengths (shifted vs unshifted, by cable type) — community numbers are anecdotal; a bench test would settle it [S138].
