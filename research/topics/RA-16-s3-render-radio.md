# RA-16: ESP32-S3 as simultaneous renderer + radio node

Last researched: 2026-07-09
Status: draft
S-ID block: S950–S999

## Key questions

- Which S3 LED-output peripheral (RMT / I2S / LCD-parallel / SPI-DMA) is glitch-free
  while WiFi/ESP-NOW is active? What is the current (2026) status of the classic
  WiFi-interrupt→RMT-glitch problem under the IDF 5 RMT driver, and does the S3's
  RMT DMA change the answer?
- What is the right dual-core task layout: render loop vs radio callbacks, where does
  the ESP-NOW recv callback run, FreeRTOS priorities, watchdog interplay?
- CPU/memory budget: does a 16-bit-per-channel pipeline + temporal dithering at
  ≥400 Hz output fit on one S3 core for 50–500 px with the radio on? What do FastLED's
  5-bit HD gamma + binary dithering cost? Is PSRAM usable for hot-path framebuffers?
- 400+ Hz dither feasibility: what output rate does 800 kHz one-wire physics allow per
  strip length, and do clocked chips (HD107s/SK9822 at MHz SPI) escape the ceiling?
- Framework for custom receiver firmware in 2026: ESP-IDF 5.x vs Arduino-ESP32 3.x vs
  PlatformIO (espressif32 stagnation, pioarduino fork)?
- NeoPixelBus vs FastLED on the S3 specifically: driver methods, 16-bit-ish support,
  maintenance status?
- OTA dual-partition implications for firmware size (brief).

## Findings

### The WiFi-vs-LED-glitch problem: mechanism and history

One-wire (WS281x/SK6812) output on ESP32-class chips is timing-critical at the
~hundreds-of-nanoseconds level, and every interrupt-driven driver shares one failure
mode: the CPU must refill the peripheral's small symbol buffer mid-frame, and if that
refill interrupt is delayed — canonically by WiFi/Bluetooth interrupts on the same
core — the transmitter reads stale or missing data. Espressif's own led_strip
documentation states it plainly: without DMA "the driver will going into interrupt
very frequently, thus result in a high CPU usage", and if a WiFi interrupt lands on
the same core "the RMT transaction will be corrupted and the LEDs will display
incorrect colors" [S964]. The official FAQ answer to "RMT + WS2812 + WiFi = data
frame exceptions" offers four escapes: more RMT memory blocks, pinning the RMT
interrupt to the non-WiFi core, switching to SPI-DMA output, or — at chip-selection
time — "ESP32-S3 is recommended because it is currently the only chip with RMT DMA
support. This ensures RMT is not interfered by interrupts caused by Wi-Fi, Bluetooth,
and other peripherals" [S963]. The ESP-IDF RMT driver docs carry the same mitigation
list for transmission glitches: increase `mem_block_symbols` in steps of 48, put the
encoder in IRAM, "Enable the `rmt_tx_channel_config_t::with_dma` if DMA is
available", and install the RMT driver from a task pinned to a core away from
WiFi/BT [S950].

FastLED's history quantifies the problem. Its maintainer measured 40–50 µs of ISR
jitter under *light* WiFi activity against a ~35 µs refill deadline — enough to
starve one-wire timing by itself [S951]. The old RMT4 backend survived this better
because FastLED hand-managed a ping-pong double buffer and could recover from
transient ISR delay; the IDF 5 RMT driver (used via Espressif's led_strip component)
centralizes refill, so "you can enlarge the buffer but can't explicitly schedule
half-buffer refills at precise boundary interrupts", and the driver caps its
interrupt priority at level 3 [S951]. FastLED 3.9.0's release notes claimed "Flicker
with WIFI *should* be solved. The new RMT 5.1 driver features large DMA buffers and
deep transaction queues" [S009], but the 2025 issue record (below) shows the story
was still being finished through 3.9.x/3.10.x.

WLED provides the production-scale control group: WLED 0.15 made DMA-fed I2S the
default first bus and immediately collected "LEDs are flickering" reports — but from
a *different* mechanism: the I2S/LCD 3-step encoding has fixed T0H ≈ 417 ns versus
RMT's ~320–400 ns, marginal against some strips' datasheet limits. The proposed fix
is RMT-by-default with DMA parallel output as opt-in [S956]. Lesson for pewpew: the
DMA drivers solve *radio-induced* glitches but bake in a single rigid bit cadence;
chip-timing compatibility must be verified per LED family.

### RMT on the S3 under IDF 5: the DMA escape hatch — with one big constraint

The S3 has 4 RMT TX channels (48 symbol-words of channel memory each) [S953][S967].
Under IDF 5's driver, enabling `with_dma` turns the channel into a GDMA-fed
transmitter whose internal buffer can be set large (e.g. 1024 symbols), removing the
per-48-symbol refill interrupt entirely [S950]. This is Espressif's recommended
cure for WiFi corruption [S963][S964].

The constraint the marketing line omits: **only one RMT TX channel per group can use
DMA**. The driver source is explicit — "Only the last channel has the DMA
capability" (channel scan starts at the last TX channel when `with_dma` is set)
[S973:components/esp_driver_rmt/src/rmt_tx.c#L124-L128]. So RMT-DMA buys exactly
*one* radio-immune one-wire line per S3; the other three RMT channels remain
interrupt-refilled and jitter-exposed. FastLED users hitting "no free tx channels"
when configuring a second DMA strip found this the hard way [S951][S975].

The RMT-DMA path also still has 2025–2026-era rough edges: Espressif's own led_strip
DMA mode fails outright on some S3 boards (Xiao ESP32-S3, possibly others — open
issue) [S965], and FastLED's computed DMA `mem_block_symbols` failed IDF validation
on S3 until it was pinned to a fixed 1024 [S966]. DMA mode additionally requires the
GDMA ISR/control functions in IRAM for cache-safe operation
[S973:components/esp_driver_rmt/src/rmt_tx.c#L264-L272] — which matters because
during flash writes (NVS commits, OTA) the cache is disabled and anything not in
IRAM stalls, another classic glitch source [S962][S950].

### I2S/LCD parallel on the S3 — the multi-line answer

The S3 lost the classic ESP32's LED-abusable I2S parallel mode ("ESP32S3/ESP32C3
... do not support I2S at this time" for NeoPixelBus's I2S methods [S953]) but
gained a dedicated LCD_CAM peripheral that does the same job better: a GDMA-fed
8/16-lane parallel bus with no mid-frame CPU involvement. Implementations, 2026
status:

- **FastLED**: 3.9.9 vendored Yves Bazin's S3 driver ("Yves's amazing I2S driver for
  ESP32S3 ... 12 way parallel, I2S/LCD protocol", PSRAM required) [S009]; by 3.10.4
  the LCD_I80 driver advertises "Up to 16 parallel WS28xx LED strips with automatic
  chipset timing optimization" [S009]. Selected with `FASTLED_ESP32_LCD_DRIVER`;
  the vendored Yves driver requires PSRAM because its expanded transposition buffers
  live there [S970]. Upstream hpwit repo is dormant (last commit 2024-11-15, no
  license file) — the maintained copy is FastLED's [S970][S008].
- **NeoPixelBus**: ships an S3-only `NeoEsp32LcdXMethod` (LCD_CAM + GDMA, X8 mux,
  3-step cadence, buffers in internal RAM)
  [S954:src/internal/methods/NeoEsp32LcdXMethod.h] alongside 4 RMT channels [S953].
- **WLED (production evidence)**: PR #4484 (merged 2025-02-13, backported to 0.15.1)
  raised S3 outputs from 4 to 12 using parallel I2S/LCD output — thousands of
  WLED-on-S3 installs now run LCD-parallel output under a live WiFi stack [S955].
  On S3 "the LCD driver has the exact same timings as I2S" — i.e. the fixed-cadence
  T0H caveat above applies [S956].

Because the LCD path is DMA-from-start-to-finish, radio interrupts cannot corrupt an
in-flight frame the way they corrupt interrupt-refilled RMT; the residual risks are
(a) the fixed 3-step cadence vs marginal strips [S956] and (b) buffer placement —
DMA bandwidth to PSRAM "is very limited, especially when the core is trying to
access the external RAM at the same time" [S962], so at pewpew's 50–500 px scale the
DMA buffers should sit in internal SRAM (NeoPixelBus's LcdX8 does; FastLED's Yves
driver deliberately uses PSRAM to reach thousands of pixels) [S954][S970][S962].

### SPI-DMA for clocked chips: structurally immune, driver-dependent in practice

HD107s/SK9822-class chips carry their own clock line, so there is no
hundreds-of-ns timing contract to violate: if the SPI DMA stream stalls, the strip
simply waits. A single-transaction SPI-DMA transfer removes even that stall. This is
why Espressif's FAQ lists "SPI DMA" as a WS2812 workaround at all [S963], and the
led_strip component offers an SPI backend (with the caveat that it monopolizes the
host — "the led_strip doesn't have the concept of 'Chip Select'") [S964]. On the S3,
NeoPixelBus provides `DotStarEsp32DmaSpiMethod` for exactly this
[S954:src/internal/methods/DotStarEsp32DmaSpiMethod.h], and FastLED documents
hardware multi-lane (1/2/4-lane) SPI with DMA for APA102/SK9822/HD107S [S952].

The practical caveat is driver quality, not physics: FastLED's ESP32 SPI path was
measured sending a 30-px APA102 frame in ~422 µs at 5 MHz and ~244 µs at 20 MHz,
with ~1.7 µs dead gaps between bytes — i.e. raising the clock 4× bought only 1.7×,
because per-byte overhead dominates; the issue remains open [S971]. At those
effective rates a 500-px strip lands near 4 ms/frame (~250 Hz) instead of the
protocol-limited ~0.8 ms (1.2 kHz at 20 MHz). A single queued IDF `spi_master` DMA
transaction (or NeoPixelBus's DMA method) avoids the per-byte gap [S954][S964].

### The 2026 recommendation for glitch-free output under an active radio

Ranked for a pewpew S3 node (50–500 px, ESP-NOW always on, WiFi STA on gateway
nodes):

1. **Clocked chips via one-shot SPI-DMA** — categorically immune to radio jitter;
   also the only path to 400+ Hz at 500 px (math below) [S963][S964][S971].
2. **One-wire via LCD_CAM parallel (X8)** — DMA end-to-end, proven at scale by
   WLED-on-S3; verify strip timing tolerance against the 3-step cadence
   [S955][S956][S954].
3. **One-wire via RMT + DMA** — radio-immune per Espressif, but only ONE line per
   chip and still shaking out board-specific bugs [S963][S973][S965][S966].
4. **One-wire via plain RMT (no DMA)** — acceptable only with the full mitigation
   stack (interrupts + encoder pinned to core 1, IRAM, enlarged mem blocks), and
   never guaranteed under worst-case jitter [S950][S951][S964].

### Dual-core task layout

ESP-IDF's stock layout: the WiFi driver task runs at priority 23 pinned to core 0 by
default (`CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE`); lwIP runs at 18 unpinned; `app_main`
starts at priority 1 on core 0 [S957]. Espressif's optimization guide says to place
latency-sensitive interrupts "on a CPU where built-in Wi-Fi/Bluetooth tasks are not
configured to run, which means assigning the interrupt on Core 1 by default" [S957].

ESP-NOW callbacks run inside the radio's context, not the app's: "The receiving
callback function also runs from the Wi-Fi task. So, do not do lengthy operations in
the callback function. Instead, post the necessary data to a queue and handle it from
a lower priority task" (same for the send callback, which "runs from a high-priority
Wi-Fi task") [S800]. Implications for pewpew: the recv callback must only timestamp +
copy the ≤250 B (v1) payload into a FreeRTOS queue; any beat/param processing happens
in an app task, or it delays the radio itself. At ~10 Hz broadcast rate the queue
depth needed is trivial.

Watchdog interplay: the task watchdog subscribes both cores' idle tasks by default
(`CONFIG_ESP_TASK_WDT_CHECK_IDLE_TASK_CPU0/CPU1`) [S972], and a render/output loop
pinned to core 1 that never blocks will starve idle1 and trip it — ESP-IDF's guide
is explicit that tasks must yield "in order to not starve lower-priority tasks and
cause problems for the overall system" [S957]. A 400 Hz output task naturally blocks
on a DMA-done notification each cycle, which both feeds the watchdog and paces the
loop; the alternative (unsubscribing idle1) sacrifices hang detection [S972].

Resulting layout (sketch, see Verdicts):

- **Core 0**: WiFi/ESP-NOW stack (prio 23, built-in), lwIP (18), control task
  (~prio 5) draining the ESP-NOW queue, NVS/OTA/housekeeping at low prio
  [S957][S800].
- **Core 1**: output/dither task (highest app prio, e.g. 10–15; wakes per output
  period, re-quantizes the 16-bit frame with the dither state, queues the DMA
  transaction, blocks on completion), render task (~prio 5, produces float/16-bit
  frames at ~60 fps), LED peripheral interrupts allocated on core 1 [S957][S950].

### CPU and memory budget

**The silicon.** Dual Xtensa LX7 at 240 MHz with a single-precision FPU, 512 KB
internal SRAM, GDMA, and the PIE extension: 8× 128-bit SIMD registers with 8/16/32-bit
vector ops and MAC — shared with the P4 and used by Espressif's esp-dsp library
(assembly-optimized dot/matrix/FFT; active, last commit 2026-05-11, Apache-2.0)
[S967][S968][S969]. Float render code costs roughly one FLOP/cycle on the FPU;
bulk 16-bit pixel arithmetic can additionally be vectorized via PIE/esp-dsp — the
S3 does not force a fixed-point-vs-float choice for a 500-px pipeline [S967][S968].

**Memory.** A 500-px RGBW uint16 framebuffer is 4 KB; double-buffered plus dither
error state ≈ 12 KB. Driver overhead: RMT needs a hardware-read buffer equal to the
pixel buffer, classic I2S needed 4×, and the LcdX8 DMA buffer is 3 DMA-bits per
pixel-bit across the 8-lane mux (≈ 4.5 KB for 8×63 px RGB)
[S953][S954:src/internal/methods/NeoEsp32LcdXMethod.h]. Total worst case is tens of
KB against 512 KB SRAM — **PSRAM is unnecessary at pewpew's node scale and should be
kept out of the hot path**: DMA descriptors cannot live in PSRAM, DMA-to-PSRAM
bandwidth is "very limited" under concurrent core access, and PSRAM becomes
*inaccessible* whenever the flash cache is disabled (NVS writes, OTA) — a latent
glitch/crash source for radio-connected nodes that periodically persist state
[S962]. PSRAM's role on a pewpew node is cold data (palettes, presets, OTA
buffers), not framebuffers [S962].

**CPU arithmetic (estimate, uncited — prototype must measure).** A dither/re-quantize
pass touching 500 px × 4 ch at ~40 cycles/channel costs ≈ 80 k cycles per tick; at
400 Hz that is 32 M cycles/s ≈ 13% of one 240 MHz core (at 100 px, ~3%). A 60 fps render pass then has ≈ 200 M − 32 M ≈ 170 M cycles/s available on
core 1 alone — ~5,600 cycles/px/frame at 500 px, comfortable for float-linear effects
with FPU + optional PIE. Nothing published measures FastLED's binary-dither or
5-bit-HD-gamma per-pixel cost on S3 (searched 2026-07-09; no benchmark found) — the
5-bit HD path was rewritten with "a closed-form mathematical solution" in 3.10.2
[S009], and its cost must be measured in the prototype, not assumed. FastLED's own
dither model also assumes the *driver* can physically reach ~400 Hz — its docs tie
dither quality directly to show() rate [S050][S127].

**Radio load.** ESP-NOW at ~10 Hz beacon rates is negligible airtime; the budget
question is interrupt *jitter*, not throughput — which the DMA output paths above
absorb [S951][S963]. A gateway node additionally running WiFi STA sees the full
WLED-class interrupt environment, which is exactly what WLED's S3 parallel output
already survives in production [S955].

### Output-rate math: one-wire ceiling vs clocked escape

**One-wire (WS2812/SK6812 class).** The line rate is fixed at 800 kbit/s — 1.25 µs
per bit, 30 µs per 24-bit RGB pixel (40 µs per 32-bit RGBW), plus a latch: ≥80 µs
(SK6812) to ≥280 µs (current WS2812B-V5) [S114][S106][S105]. Maximum output rate for
one line, RGB with 280 µs latch (`1 / (n×30µs + 280µs)`):

| px/line | frame time | max output rate |
|---|---|---|
| 50 | 1.78 ms | ~560 Hz |
| **74** | **2.50 ms** | **400 Hz — the ≥400 Hz ceiling** |
| 100 | 3.28 ms | ~305 Hz |
| 150 | 4.78 ms | ~209 Hz |
| 300 | 9.28 ms | ~108 Hz |
| 500 | 15.28 ms | ~65 Hz |

(RGBW at 40 µs/px crosses 400 Hz at ~60 px/line.) This confirms ADR-002's
~64–85 px/line sizing rule and RA-03's dithering-ceiling finding [S127][S106][S114].
**The escape for one-wire is parallelism, not speed**: the S3's LCD X8 path splits
500 px into 8 lines of ≤63 px → 63×30 µs + 280 µs ≈ 2.17 ms ≈ 460 Hz, so a 500-px
one-wire node *can* dither at ≥400 Hz if physically wired as 8 short lines
[S954][S955][S106].

**Clocked (HD107s/SK9822 class).** No latch, no fixed bit rate: frame = 32-bit start
+ 32 bits/px + n/2 end-clocks, at whatever SPI clock the wiring sustains — vendor
claims up to 40 MHz for HD107s; 10–20 MHz is realistic on short strips, and the clock
regenerates through each pixel with a half-cycle delay (why long strips self-limit)
[S101][S102][S129]. At 10 MHz: 500 px = 16,282 bits ≈ 1.63 ms ≈ **610 Hz**; 100 px ≈
3 kHz; at 20 MHz, 500 px ≈ 1.2 kHz. Meeting 400 Hz at 500 px needs only ≥6.6 MHz —
trivial — **provided the driver doesn't fritter the clock away in per-byte gaps**
(FastLED's measured 1.7 µs/byte gap would drag 500 px at 20 MHz down to ~240 Hz;
use a single-transaction DMA driver) [S971][S954][S964].

### Framework choice for custom receiver/mesh firmware, 2026

- **ESP-IDF 5.x (native)**: the substrate everything else wraps. 5.5.x is the
  current maintenance line (5.5.4 shipping inside Arduino 3.3.10, 2026-06-05); IDF
  6.0/6.0.1 is out and already supported by PlatformIO's official platform (v7.0.0
  2026-04-30, v7.0.1 2026-05-12) [S958][S961]. All the peripherals this document
  depends on (RMT-DMA, LCD_CAM, GDMA SPI, ESP-NOW v2) are IDF APIs [S950][S800].
- **Arduino-ESP32 3.x**: a tracked wrapper over IDF 5 — 3.0.0 = IDF 5.1.4
  (2024-05-27), 3.1.0 = 5.3.2 (2024-12-16), 3.2.0 = 5.4.1 (2025-03-28), 3.3.0 =
  5.5.0 (2025-07-23), 3.3.10 = 5.5.4 (2026-06-05); roughly monthly patch cadence
  [S958]. It can be consumed *as an ESP-IDF component* ("use the Arduino framework
  as an ESP-IDF component ... with the full flexibility of the ESP-IDF") — the
  pragmatic way to get IDF-level task/peripheral control plus the Arduino LED
  library ecosystem in one firmware [S976].
- **PlatformIO**: bifurcated. The official `platform-espressif32` is alive for
  *pure IDF* (v7.0.1 adds IDF 6.0.1, 2026-05-12) but never adopted Arduino core 3.x
  [S961][S959]. The community **pioarduino** fork (Jason2866, created 2024 after
  PlatformIO declined core-3.x support) carries Arduino 3.x on PlatformIO and tracks
  upstream within days (release 55.03.39 = Arduino 3.3.9/IDF 5.5.4, 2026-06-04)
  [S959][S960]. Anyone building Arduino-flavored S3 firmware under PlatformIO in
  2026 uses pioarduino; WLED-ecosystem projects already migrated [S959][S960].

### NeoPixelBus vs FastLED on the S3

| | NeoPixelBus | FastLED |
|---|---|---|
| License | LGPL-3.0 [S954] | MIT [S008] |
| Latest release | 2.8.4, 2025-05-02; master active 2026-02 [S954] | 3.10.4, 2026-06-16; near-daily master activity [S008][S009] |
| S3 one-wire drivers | RMT ×4; LcdX8 parallel (LCD_CAM+GDMA, internal-RAM buffers); no I2S on S3 [S953][S954] | RMT5 (DMA-capable, 1 DMA ch); I2S/LCD 16-way parallel (PSRAM for Yves path); LCD_I80 driver [S952][S009][S970] |
| S3 clocked drivers | DotStar SPI-DMA method [S954] | 1/2/4-lane hardware SPI w/ DMA (per-byte-gap issue open) [S952][S971] |
| 16-bit-ish output | HD108 16-bit generic method in tree [S954:src/internal/methods/Hd108GenericMethod.h] | APA102HD 5-bit-HD joint quantization ("pseudo 13 bit", rewritten 3.10.2), HD108 chipset, built-in temporal dithering [S009][S051][S050] |
| Radio-coexistence posture | driver choice per method; WLED's production base [S955][S956] | RMT5 DMA + LCD driver, explicit WiFi-flicker workstream [S951][S009] |

FastLED is where the precision features live (HD gamma, dithering, HD108) and is the
faster-moving project; NeoPixelBus is the steadier, WLED-proven plumbing with the
cleanest internal-RAM LCD parallel method. LGPL-3.0 on NeoPixelBus is a linking
consideration for distributed firmware; FastLED's MIT is unconstrained [S954][S008].

### OTA + dual-partition sizing (brief)

IDF OTA requires two app partitions plus otadata; rollback/anti-rollback come free
with it [S756]. On stock 4 MB Arduino layout that means two 1.25 MiB (0x140000)
slots [S974:tools/partitions/default.csv] — enough for an IDF 5 + WiFi + ESP-NOW +
FastLED/NeoPixelBus receiver, but tight if web assets or big tables creep in; S3
modules commonly ship 8–16 MB flash, which dissolves the constraint. Two
radio-node-specific cautions: during OTA flash writes the cache goes down, so
(a) output-path code/ISRs must be IRAM-resident and (b) PSRAM is unreachable —
another reason framebuffers stay in internal SRAM [S756][S962][S950].

## Verdicts

- **ESP32-S3 as combined renderer+radio node**: **ascendant** — the only ESP32 with
  RMT DMA (Espressif's own coexistence recommendation), plus LCD_CAM parallel and a
  free second core for rendering; WLED already runs 12-output DMA parallel on it in
  production [S963][S955][S967].
- **RMT+DMA on S3 (one-wire)**: **ascendant but single-lane** — radio-immune by
  design, capped at one DMA channel per chip, with open board-specific bugs
  [S963][S973][S965][S966].
- **LCD_CAM/I2S parallel on S3 (one-wire)**: **ascendant** — DMA end-to-end, 8–16
  lanes, production-proven via WLED 0.15.1+; fixed cadence needs per-chip timing
  check [S955][S956][S009][S954].
- **Interrupt-driven RMT (no DMA) under radio**: **waning** — a decade of glitch
  reports; every vendor doc now routes around it [S964][S963][S951].
- **SPI-DMA clocked output (HD107s/SK9822)**: **stable/ascendant** — structurally
  radio-immune and the only ≥400 Hz path at 500 px; pick a single-transaction DMA
  driver [S963][S971][S954].
- **ESP-IDF 5.x**: **stable** (5.5.x maintenance line; 6.0 arriving) [S958][S961].
- **Arduino-ESP32 3.x**: **stable** — monthly cadence on IDF 5.5.x; usable as an
  IDF component [S958][S976].
- **PlatformIO official espressif32 (for Arduino)**: **waning** — no Arduino 3.x,
  by decision [S959][S961]. For pure IDF: stable [S961].
- **pioarduino**: **ascendant** — the de-facto Arduino-3.x-on-PlatformIO platform,
  tracking upstream within days [S960][S959].
- **FastLED on S3**: **ascendant** — very active (3.10.4, 2026-06-16), owns the
  16-bit-ish/dither feature set; SPI path still inefficient (open issue)
  [S008][S009][S971].
- **NeoPixelBus on S3**: **stable** — slower cadence (2.8.4, 2025-05-02), clean
  LCD/SPI-DMA methods, WLED-proven; LGPL-3.0 [S954][S953][S955].

### Recommended S3 node software stack + task layout

**Stack**: ESP-IDF 5.5.x as base (directly, or via Arduino-ESP32 3.3.x as an IDF
component when Arduino-ecosystem code is wanted) [S958][S976]; pioarduino if the
build system is PlatformIO [S960]. LED output: clocked chips → one-shot `spi_master`
DMA transactions (or NeoPixelBus DotStar DMA method) [S964][S954]; one-wire →
NeoPixelBus LcdX8 / FastLED LCD driver for multi-line, RMT+DMA for a single line
[S954][S952][S963]. Pixel math: float-linear render on the LX7 FPU, PIE/esp-dsp for
bulk 16-bit ops where profiling justifies it [S967][S969]. Framebuffers and DMA
buffers in internal SRAM; PSRAM for cold assets only [S962].

**Task layout**:
- Core 0 — WiFi/ESP-NOW stack (built-in, prio 23), lwIP (18); ESP-NOW recv callback
  does copy+enqueue only [S957][S800]; control task (prio ~5) applies received
  beat/params atomically to a shared param block; housekeeping/NVS/OTA at low prio.
- Core 1 — output task (prio ~12): every output period (≥400 Hz clocked / per-length
  one-wire), quantize the current 16-bit frame once with dither error state, queue
  DMA, block on completion (feeds TWDT); render task (prio ~5): produce float→16-bit
  frames at ~60 fps into a double buffer; LED peripheral interrupts allocated on
  core 1 [S957][S950][S972].

### Feasibility verdicts

- **(a) Glitch-free LED output with the radio on: YES, conditional on peripheral
  choice.** SPI-DMA clocked output and LCD_CAM parallel are DMA end-to-end and
  radio-immune; RMT is radio-immune only on its single DMA channel. Plain
  interrupt-refilled RMT cannot be certified glitch-free under WiFi and should not
  ship in a quality-bar pewpew node [S963][S964][S973][S955].
- **(b) ≥400 Hz dither on clocked chips: YES, with margin.** 500 px HD107s needs only
  ≥6.6 MHz SPI; 10 MHz yields ~610 Hz, 20 MHz ~1.2 kHz. The risk is driver overhead,
  not physics — require single-transaction DMA output [S101][S129][S971].
- **(c) One-wire dither/output rate is strip-length-bound.** Per line: ~560 Hz at
  50 px, 400 Hz at 74 px (RGB; ~60 px RGBW), ~305 Hz at 100 px, ~108 Hz at 300 px,
  ~65 Hz at 500 px [S106][S114][S105]. A 500-px node reaches ≥400 Hz only by wiring
  as ≥8 parallel lines on the LCD_CAM path (8×63 px ≈ 460 Hz); otherwise dither
  depth must degrade with length per ADR-002's mask policy [S954][S955][S127].

## Code-reading queue

1. **espressif/esp-idf — `components/esp_driver_rmt/src/rmt_tx.c` + led_strip RMT
   backend** [S973][S964]: exact DMA-channel allocation, encoder-callback timing,
   what `mem_block_symbols` buys without DMA — settles how far the 3 non-DMA RMT
   channels can be hardened.
2. **Makuna/NeoPixelBus — `NeoEsp32LcdXMethod.h` + `DotStarEsp32DmaSpiMethod.h`**
   [S954]: DMA buffer sizing/placement, cadence timing constants vs SK6812/WS2812
   datasheet windows, whether the SPI method issues one transaction per frame —
   feeds the output-driver decision directly.
3. **FastLED — `third_party/yves` S3 driver + LCD_I80 driver + RMT5 worker pool**
   [S008][S970][S952]: PSRAM buffer strategy vs internal RAM, per-frame CPU cost of
   the transposition/encode step, current state of the #2082 jitter-hardening work.
4. **FastLED — `fl/five_bit_hd_gamma` + binary dither path on S3** [S008][S009]:
   cycle-count the 3.10.2 closed-form HD gamma and per-show dither overhead —
   fills the budget table's biggest unknown.
5. **espressif/esp-dsp — PIE kernels** [S969]: which 16-bit vector primitives map
   onto gamma/scale/dither loops; decides whether SIMD is worth the assembly.
6. **WLED — S3 bus manager after PR #4484** [S955]: how production firmware
   allocates RMT vs parallel buses per chip type and what limits it hit.

## Open questions

- **Is S3 RMT-DMA actually reliable in mid-2026?** Espressif recommends it
  [S963], but led_strip DMA fails on some S3 boards (open issue #466) [S965] and
  FastLED needed a hardcoded 1024-symbol workaround [S966]. Settle with a 2-week
  soak test: RMT-DMA + ESP-NOW 10 Hz + STA traffic, logic analyzer on the data line.
- **LCD X8 cadence vs pewpew's chip set**: WLED reports T0H ≈ 417 ns is marginal
  for some WS281x variants [S956]. Verify against SK6812's datasheet window
  [S114] on real strips before standardizing on LCD parallel.
- **FastLED SPI throughput today**: issue #1609's per-byte gaps were measured
  pre-3.10; whether the current multi-lane SPI path batches transactions is
  unverified [S971][S952][NEEDS-VERIFICATION]. A scope trace answers it in an hour.
- **Measured CPU cost of 16-bit + dither on S3**: no published benchmark of
  FastLED's 5-bit HD gamma or binary dithering cost on any ESP32 was found
  (searched 2026-07-09); the ~13%-of-core estimate above is arithmetic, not data.
  Needs the prototype cycle-count (code-reading item 4).
- **ESP-NOW-only nodes vs STA nodes**: does a node running only ESP-NOW (no STA
  association, no lwIP traffic) see materially less interrupt jitter than a
  WiFi-associated one? Plausible but unmeasured; affects whether non-gateway nodes
  could tolerate cheaper output paths. Measure ISR-to-ISR jitter both ways.
- **Yves/FastLED PSRAM-resident DMA buffers under radio load**: S962 warns
  DMA-to-PSRAM bandwidth degrades under concurrent core access [S962]; the driver
  works in the field at thousands of px [S009] — where is the cliff at pewpew's
  frame rates? Only matters if a node ever exceeds internal-SRAM scale.
- **hpwit S3 driver licensing**: upstream repo has no license file while FastLED
  vendors it under MIT overall [S970][S008] — check FastLED's third_party
  attribution before shipping derived code.
