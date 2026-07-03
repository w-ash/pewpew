# RA-09: Hardware — wearable/standalone tier

Last researched: 2026-07-03
Status: draft
S-ID block: S400–S449

## Key questions

1. Which MCUs (2024–2026) best serve standalone on-body LED wearables: RP2040/RP2350 (PIO), nRF52840 (BLE/power), ESP32-S3/C3 (WiFi AP, battery draw), anything newer?
2. What LED frame rates are realistically achievable in CircuitPython/MicroPython, with and without ulab? Where does interpreted Python hit the wall?
3. How do Python-authored patterns reach a standalone wearable device? (bake/export to data, transpile, embedded interpreter, tiny shared-semantics engine)
4. Phone control: BLE GATT (Bluefruit model) vs WiFi AP + web UI (WLED/Pixelblaze model) — battery cost of each?
5. Power: LiPo sizing for realistic pixel counts, brightness limiting, charging, brownout behavior.
6. What does the Adafruit wearable lineup look like in 2026 (Sparkle Motion etc.)?
7. Durability: connectors, strain relief, wash/wear survival.

## Findings

### MCU landscape for wearables (2024–2026)

**RP2040 / RP2350.** RP2350 (published August 2024) is the current default "compute per milliamp with deterministic LED output" pick: dual Cortex-M33 (or RISC-V Hazard3) at 150 MHz, three PIO blocks / 12 state machines, 32-instruction PIO programs (up from 2 blocks / 8 SMs / 32-instr on RP2040 at 133 MHz) [S410]. PIO generates WS2812 waveforms with essentially zero CPU cost and no interrupt-latency glitching — the property that lets an interpreted-Python frame loop coexist with clean LED output. No radio on-chip: wireless RP2350 boards add a CYW43 (Pico 2 W) or similar, which erodes the power story [S410]. CircuitPython support is first-class; RP2350 runs the same code roughly 2x faster than RP2040 [S403][NEEDS-VERIFICATION].

**nRF52840.** The battery/BLE champion: ~1.5 µA deep sleep vs 10–20 µA for ESP32-S3, with a purpose-built BLE 5.0 radio [S412]. A January 2025 measured comparison of BLE advertising current across ESP32-C3/C6/S3, EFR32MG24 and nRF52840 concluded "nRF52840 is by far the best for low current consumption BLE applications" and "ESP32s are not suitable for BLE projects with low current consumption" [S412]. No WiFi, and only 64 MHz Cortex-M4F — the least compute headroom of the three families, so it leans hardest on offload (e.g. the LED Glasses pair it with an IS31FL3741 I2C matrix driver that does all PWM in hardware) [S416]. Adafruit's LED Glasses Driver (nRF52840 + LIS3DH accelerometer + PDM mic + LiPo support, CircuitPython-native) is the canonical wearable reference design for this chip [S416].

**ESP32-S3 / C3 / classic ESP32.** The WiFi family: S3 is dual-core 240 MHz LX7 with WiFi+BLE and vector instructions; C3 is a cheaper single-core 160 MHz RISC-V with WiFi+BLE. This is the WLED substrate and what Adafruit's 2025 Sparkle Motion boards use (classic ESP32 mini module, 240 MHz dual-core) [S414]. The cost is radio power draw: ~130 mA average with 0.6 A spikes while WiFi is active, and WiFi modem power-save (`esp_wifi_set_ps`) works only in station mode — not in the SoftAP mode a standalone wearable would run for phone control [S411]. Deep-sleep currents (10–20 µA) are fine, but a wearable that keeps WiFi up all day pays ~100+ mA continuously [S411][S412].

**Anything newer (2024–2026).** ESP32-C6 adds WiFi 6 + BLE + 802.15.4 but measured no better than other ESP32s for BLE advertising current [S412]. Nordic's nRF54 series began sampling in this window but has not displaced nRF52840 in the hobby/CircuitPython ecosystem as of mid-2026 [NEEDS-VERIFICATION]. No new MCU family has changed the basic triangle: RP2350 = deterministic output + best interpreted-Python throughput per dollar; nRF52840 = battery + BLE; ESP32-x = WiFi + the WLED ecosystem.

### CircuitPython/MicroPython: achievable frame rates and the ulab escape hatch

**Baseline numbers.** todbot's canonical benchmark: a fire animation over 256 LEDs on RP2040 CircuitPython takes ~40 ms/frame (~25 fps) written as plain Python for-loops, and ~4 ms/frame (~250 fps of compute) when the per-pixel math is vectorized through ulab numpy arrays — a 10x speedup [S400]. The technique is "keep a working copy of the LED data in a ulab array, mutate it with vectorized ops (e.g. `np.clip(leds_np,0,255)`), and copy into the real pixel object at the last moment" [S400]. His stated rule of thumb: "any time you're doing a for-loop on a large list in Python, you're probably doing it wrong" [S400]. His `circuitpython_led_effects` repo carries the benchmark code and further effects [S408].

**MicroPython's equivalent escape hatch** is the `@micropython.viper`/`@micropython.native` code emitters, which compile a function to native machine code; a Core Electronics tutorial on a GlowBit WS2812 matrix measured frame rate roughly doubling (10 → ~22-23 fps) just by decorating the hot animation functions, with the usual viper restrictions (max 4 typed args, no default values) [S402]. Viper is strong on integer/bit math but is per-function and type-restricted — it accelerates a hand-tuned inner loop, not arbitrary user pattern code [S402].

**Where interpreted Python hits the wall.** Both escape hatches share the same shape: the interpreter is ~1-2 orders of magnitude too slow for per-pixel per-frame math at wearable pixel counts (100-500 px) and 30-60 fps, so viable Python-on-device architectures push the per-pixel work into vectorized C (ulab) or native-emitted functions and keep the interpreted layer to per-frame orchestration [S400][S402]. Practical implication for pewpew: a pattern authored as arbitrary per-pixel Python cannot run as-is on-device at speed; it must either be expressed against a vectorized array API (ulab semantics, which conveniently mirror host-side numpy) or be compiled/baked (see portability section). On RP2350 the same CircuitPython code runs roughly 2x faster than RP2040, which relaxes but does not remove the wall [S403][NEEDS-VERIFICATION].

Maintenance status: ulab is bundled in CircuitPython builds for the boards relevant here (RP2040/RP2350/nRF52840/ESP32-S3) as of CircuitPython 9.x/10.x (2025-2026) [S403]. The Adafruit LED Animation library (MIT) remains the standard high-level wearable animation API but is plain-Python and inherits the for-loop performance ceiling [S401].

### Pattern portability: how Python-authored patterns reach the device

Four strategies are visible in the wild; no shipping system today runs host-authored *Python* patterns live on a wearable MCU, so pewpew would be choosing among these shapes:

**1. Ship the source, run an interpreter (CircuitPython model).** CircuitPython devices expose their filesystem as a USB drive, and on nRF52840-class boards also over BLE via the FileTransferService (service UUID 0xfebb, simple CRUD protocol, explicitly "simple (not fast)") [S407]. Adafruit's web Code Editor edits files on a BLE device from Chrome with no installed software — proof that "push new Python pattern over BLE from a phone/laptop" is a solved workflow on nRF52840 [S409]. The cost is the interpreter performance wall (previous section): source-level portability only works if the pattern API is vectorized (ulab) or the pixel count is small (~<100 px for pure-Python at 30 fps on RP2040-class hardware, extrapolating from the 256-px/40-ms benchmark) [S400].

**2. Compile off-device to bytecode for a tiny on-device VM (Pixelblaze model).** Pixelblaze patterns are written in a JS-like expression language in a web editor; they are "compiled into high level rendering instructions that are then executed on the ESP32," recompiled and re-sent live on every edit [S404]. The compiled binaries are bytecode and are slightly platform-dependent (a v3 binary differs from the same pattern on v2) [S405]. The optimized expression engine renders ~48k pixels/sec on ESP32 (V3) — e.g. 300 px at 160 fps or 1500 px at 32 fps — which is the existence proof that an expression-VM approach comfortably clears wearable pixel counts on 240 MHz-class silicon [S405]. This is the closest architectural precedent for "author in a host language, execute on-device with shared semantics": the compiler lives off-device (in the browser), the device runs only a small fixed VM.

**3. Bake to frames and play back (xLights/FSEQ model).** Patterns are rendered ahead of time to an FSEQ frame stream and played from SD/flash; WLED merged FSEQ-from-SD playback support (PR #4570, merged 2025) with a file manager for upload/delete/play [S406]. Adafruit's older LIGHTSHIP guide shows the same idea at wearable scale (SD-card frame playback on a wearable-class controller) [S421]. Baking is trivially portable (host Python renders frames, device just streams them) and has zero on-device compute cost, but loses interactivity/parametrization and costs storage: raw RGB at 150 px x 30 fps ≈ 13.5 KB/s, ~810 KB/min — fine on SD, tight on a 4 MB-flash MCU without SD.

**4. Transpile/regenerate to native.** No maintained Python→MCU-C transpiler for LED patterns surfaced in the wild; the closest patterns are hand-porting to FastLED/WLED usermods or viper-decorating MicroPython hot loops [S402]. This path exists but is a per-pattern manual effort, not a pipeline. [NEEDS-VERIFICATION — a deeper repo trawl could still surface a niche transpiler.]

**Synthesis for pewpew.** The workable hybrid seen across these precedents: define the pattern API against array semantics that exist on both sides (host numpy ↔ device ulab, which deliberately mirrors numpy's API [S400]), so a subset of host patterns runs unmodified under CircuitPython; for patterns outside that subset, bake to FSEQ-style frame data. The Pixelblaze route (custom bytecode + VM) yields the best on-device performance-per-flexibility but means building and maintaining a compiler+VM pair [S404][S405].

### Phone control: BLE GATT vs WiFi AP + web UI

**BLE GATT (Bluefruit/Adafruit model).** Phone app (Bluefruit Connect or web-Bluetooth page in Chrome) speaks custom GATT services: Adafruit ships UART, color-picker, control-pad services, plus the FileTransferService for pushing whole files [S407][S409]. Fits the wearable duty cycle: advertise at low rate, connect only during the "occasional phone tweak," radio nearly free the rest of the time — the regime where nRF52840 draws µA-to-low-mA [S412]. Constraints: low throughput (file push is explicitly "simple (not fast)" [S407]), and the UI must live in an app or web-Bluetooth page rather than being served by the device.

**WiFi AP + web UI (WLED/Pixelblaze model).** Device runs SoftAP and serves its own full web app; any phone browser works with zero installed software, and the UI can be rich (WLED's full control surface, Pixelblaze's live pattern editor) [S404][S414]. Battery cost is the problem: ~130 mA average radio draw while the AP is up, with no modem power-save available in SoftAP mode [S411]. WLED-based wearables in practice either accept a few hours of runtime, add a "turn WiFi off after config" behavior, or are used with larger packs; the Sparkle Motion guides target sound-reactive hats and props powered by USB battery banks rather than small LiPos [S414][S415].

**Battery comparison, concretely.** Take a 1200 mAh LiPo: ESP32 SoftAP idle (~100-130 mA) burns ~10% of the pack per hour before lighting a single LED; nRF52840 with occasional BLE connection contributes ~1% or less per hour [S411][S412]. For "standalone on-body with occasional tweaks," BLE is the architecture-correct radio; WiFi AP is only defensible when the device's UI *is* the product (live pattern editing) or runtime is short/pack is big. A hybrid seen in the wild: ESP32 boots with WiFi on for N minutes then drops the radio [NEEDS-VERIFICATION — common forum advice, no canonical implementation cited].

### Power: LiPo sizing, brightness limiting, charging, brownout

**Per-pixel budget.** The planning constant is 60 mA/pixel worst case (RGB full white); Adafruit is explicit that this is "a rule of thumb, not hard science," and real animated patterns at wearable brightness average far less (measured example: 12 WS2812B at 50% brightness all-on drew 78 mA total, ~6.5 mA/px) [S417]. LiPo cells at 3.7 V can drive "5 V" NeoPixels directly (they run fine at 3.7 V, and a 3.3 V data signal is then within spec), avoiding boost-converter losses at the cost of slightly dimmer/warmer output [S417].

**Sizing math.** Runtime(h) ≈ pack mAh / (MCU mA + pixels x avg mA/px). Worked wearable example: 150 px costume, animated pattern limited to ~15% average duty ≈ 150 x 9 mA = 1.35 A ... which is already too much for a small pack; this is why every real wearable ships with a brightness limiter. With WLED's Automatic Brightness Limiter at its 850 mA default (tunable to the pack's rating), a 2000 mAh LiPo yields roughly 2 h worst-case at the cap, plus radio overhead (~130 mA if WiFi stays up [S411]) [S418]. On the C++ side the same pattern is `FastLED.setMaxPowerInVoltsAndMilliamps(5, 1000)`: FastLED estimates frame power and scales global brightness so draw never exceeds the cap; `show()`/`delay()` apply it automatically [S413]. CircuitPython has no built-in equivalent — a pewpew device runtime would need to implement the estimate-and-scale loop itself (the math is simple: sum of channel values x per-channel mA) [S413][S401].

**Brownout.** Two distinct failure modes: (a) pixel-logic brownout — mitigated by the classic 1000 µF reservoir cap and per-pixel 0.1 µF decoupling [S417]; (b) MCU brownout — ESP32s reset when WiFi TX spikes (0.6 A [S411]) sag a soft supply; shared LiPo + boost designs must budget for radio spikes on top of LED draw. Brightness limiting doubles as brownout protection by keeping the pack inside its C-rating [S418][S413].

**Charging.** Standard wearable pattern is an onboard LiPo charger charging over USB while the device runs (Adafruit LED Glasses Driver and most Feathers include this) [S416].

### Adafruit wearable lineup 2026

The 2025-2026 lineup splits into a WLED-first family and a CircuitPython-first family:

- **Sparkle Motion** (Jan 2025, #6100): "all-in-one WLED and xLights board" — classic ESP32 mini (240 MHz dual-core, 4 MB flash), 4 LED outputs, USB-C PD selectable 5/12/20 V up to 100 W, onboard IR receiver and I2S mic for sound reactivity; 33x45 mm, wearable-compatible but aimed at props/installs; also runs Arduino/ESP-IDF/MicroPython/CircuitPython [S414]. A wFL-external-antenna variant exists (#6167) [S414].
- **Sparkle Motion Mini** (2025): 31.6x19.8 mm, 2 outputs, USB-C powered — the variant Adafruit positions for "wearables and portable LED setups" [S415].
- **LED Glasses Driver nRF52840** (#5217) + EyeLights glasses: the BLE/CircuitPython wearable reference — thin nRF52840 board with LiPo charging, LIS3DH accelerometer, PDM mic, driving 116 RGB LEDs through an IS31FL3741 I2C constant-current driver so the MCU never bit-bangs pixels [S416].
- Legacy wearables (Gemma M0, Circuit Playground, Flora) remain sold but are SAMD21-class — too slow for the pattern-engine ambitions here and effectively frozen [S416][NEEDS-VERIFICATION as to formal EOL status].

Notable read: Adafruit's own 2025 direction for wearable LED control is *WLED firmware on ESP32*, not CircuitPython — the Sparkle Motion guides configure WLED rather than shipping Python animation code [S414][S415]. Battery-first BLE wearables remain on nRF52840+CircuitPython.

### Durability: connectors, strain relief

Adafruit's wearable guidance: repeated flexing cracks solder joints and strip traces, so either mount short strip segments on a semi-rigid base or use individually sewable pixels for garments that flex [S417]. Standard practice from the Überguide: JST-SM 3-pin pigtails as the strip-to-controller disconnect, heat-shrink over solder joints, hot-glue or epoxy strain-relief blobs where wires exit strips, and silicone-sleeved strips for anything that touches skin or weather [S417]. Battery leads are the most common failure point — JST-PH 2-pin with the connector body anchored (not dangling from the pigtail) is the norm on Adafruit boards [S416][S417].

## Verdicts

- **RP2350 (+ CircuitPython)** — **ascendant.** Released Aug 2024, rapidly adopted across vendor boards (Feather RP2350, Plasma 2350, XIAO RP2350 all shipping CircuitPython builds by 2025) [S403][S410]. Best deterministic-output + Python-throughput combination for a non-radio wearable core.
- **nRF52840** — **stable.** 2018-era silicon but still the measured best-in-class for BLE current (Jan 2025 comparison) [S412] and still Adafruit's BLE-wearable platform [S416]; nRF54 successors not yet in the hobby ecosystem [NEEDS-VERIFICATION]. Safe to build on for the BLE wearable tier.
- **ESP32 classic / S3 for wearables** — **stable, with a battery asterisk.** Adafruit doubled down in 2025 with Sparkle Motion/Mini [S414][S415], but SoftAP power draw (~130 mA, no power-save in AP mode [S411]) makes it the wrong radio for all-day on-body use; right choice when a served web UI or WLED ecosystem is the requirement.
- **CircuitPython** — **ascendant/stable.** Major release cadence healthy: 10.0.0 Oct 2025, 10.2.1 May 2026 [S419]; ulab bundled on all relevant ports [S403]. The plain-Python per-pixel loop remains too slow; the ulab-vectorized style is mandatory at >100 px [S400].
- **Adafruit LED Animation library** — **stable/waning as an architecture model.** Maintained (MIT) but plain-Python and performance-capped; fine prior art for API shape, not for engine internals [S401][S400].
- **Pixelblaze** — **stable but single-vendor-fragile.** V3 shipping (Adafruit distributes it [S405][S420]); V2+ retired, Tindie storefront paused until 2027, no V4 roadmap visible on the forum as of 2025 [S420]. Its architecture (off-device compiler → on-device expression VM) is the strongest design precedent even if the product's momentum is flat.
- **Bake-to-FSEQ playback** — **ascendant** as a portability floor: WLED merged SD FSEQ playback in 2025 [S406]; xLights ecosystem keeps the format alive at scale.

## Code-reading queue

1. **todbot/circuitpython_led_effects** — the ulab fire benchmark files (`fire_no_ulab.py`, `fire_with_ulab.py`): exactly which operations vectorize and what the residual per-frame Python overhead is; answers "what must pewpew's device-side pattern API look like to be fast under ulab" [S408].
2. **adafruit/Adafruit_CircuitPython_BLE_File_Transfer** — protocol (`adafruit_ble_file_transfer.py`) + stub server: measure/estimate real KB/s and see whether the CRUD protocol suffices for pattern push + parameter tweak, or whether pewpew needs its own GATT service [S407].
3. **wled/WLED PR #4570** (fseq playback, `usermods`/`FX` integration): how a streaming frame player coexists with an effect engine — the model for pewpew's "baked pattern" fallback path [S406].
4. **Adafruit_CircuitPython_LED_Animation** — `animation/__init__.py` base class: API prior art for time-based (not frame-counted) animation stepping and layered/grouped pixels [S401].
5. **Pixelblaze pattern binary format** (community reverse-engineering, e.g. pixelblaze-client Python lib and forum posts): how small a pattern VM's instruction set can be while covering the observed pattern corpus [S404][S405].
6. **FastLED `power_mgt.cpp`** — the power-estimation constants and scaling algorithm, to port estimate-and-scale brightness limiting into a Python device runtime [S413].

## Open questions

- **Measured CircuitPython-on-RP2350 LED frame rates.** The "~2x over RP2040" figure is inferred from vendor/board pages, not a benchmark run [S403][NEEDS-VERIFICATION]. Settle with: run todbot's fire benchmark on a Feather RP2350.
- **BLE file-transfer throughput in practice.** "Simple (not fast)" [S407] — but is it 1 KB/s or 20 KB/s? Determines whether pushing a baked 100 KB pattern over BLE is seconds or minutes. Settle with a bench test or forum ask.
- **ESP32 SoftAP with radio duty-cycling.** Is there a maintained "AP up for N minutes then off" implementation in WLED or elsewhere, and what does average current become? No canonical source found.
- **nRF54 / newer Nordic parts in CircuitPython.** Whether a supported successor to nRF52840 lands in the ecosystem before pewpew's device tier ships.
- **Python→MCU transpilers for pattern code.** None found in the wild; a deeper trawl (GitHub topic search, MicroPython forums) could still surface one before concluding the only options are ulab-subset, bytecode-VM, or bake.
- **Sparkle Motion Mini battery behavior.** It is USB-powered; no LiPo charger onboard [S415][NEEDS-VERIFICATION] — confirms/denies its fitness as a true on-body board versus battery-bank-in-pocket.
