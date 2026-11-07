# Code deep-dive: modern engines — projectMM & SmoothLed

Two smaller reads in one dive (Phase 1 queue additions, RA-01/RA-09):

- **Section A — projectMM** (`ewowi/projectMM`, redirects to `MoonModules/projectMM`):
  the 2026 clean-slate successor to MoonLight by the WLED-MM/MoonModules authors.
  Pipeline architecture, cross-platform layer, effect model, and the postmortem of
  abandoned MoonLight/WLED decisions.
- **Section B — SmoothLed** (`mattshepcar/SmoothLed`): Fadecandy-style
  interpolation + temporal dithering on an ATtiny — existence proof for
  pewpew's wearable-tier quality layer.

---

## Section A — projectMM

- repo: https://github.com/ewowi/projectMM (now MoonModules/projectMM)
- pinned: ewowi/projectMM@d5ee07ce3d6c590019cbbde670de8c532b2df511 [S715]
- license: GPL-3.0 (LICENSE file verified)
- accessed: 2026-07-03 (HEAD commit dated 2026-07-03 — actively developed, same-day commits)
- Context: this is "v3" of the MoonModules line — MoonLight (a WLED-MM-era fork
  built on ESP32-SvelteKit, see [S004]) → projectMM v1 → v2 → v3 (this repo,
  released v1.0.0/v2.0.0 under the new tree). Pure ESP-IDF v6.x, **no Arduino, no
  FastLED, no ArduinoJson, no ESPAsyncWebServer** — all in-tree
  [S715:README.md#L41-L43]. Docs are unusually good: `docs/architecture.md` is a
  571-line binding "architecture contract" and `docs/history/decisions.md` is an
  818-line explicit postmortem of all four iterations.

### Architecture: Layouts → Layers → Drivers pipeline

The whole system is two strata: a domain-neutral **core** (module base, controls,
scheduler, persistence, platform abstraction, HTTP/WS) and the **light domain**
built on it [S715:docs/architecture.md#L63-L70]. The light pipeline
[S715:docs/architecture.md#L285-L318]:

```
Layouts (shared physical topology, coordinate iterators)
   → Layers (each Layer: own logical buffer + own mapping LUT + ordered Effects + ordered Modifiers)
      → Blend+Map (composite layers bottom→top into physical buffer)
         → Drivers (RMT / LCD_CAM i80 / Parlio WS2812, ArtNet/E1.31/DDP, Preview-WebSocket)
            each applying a shared Correction (brightness LUT + channel reorder + white derive)
```

Key structural decisions, each a deliberate break from WLED's segment model:

- **A layout is a coordinate iterator, not a data structure.** Each layout yields
  `(physicalIndex, x, y, z)` algorithmically; positions are computed, never stored
  [S715:docs/architecture.md#L331-L341]. One Layouts container is shared by every
  Layer; "light" covers both addressable LEDs and DMX fixtures (a moving head is
  one point in 3D).
- **Each Layer owns a logical buffer + a mapping LUT** built by folding the shared
  physical coordinates through the layer's chain of static modifiers
  [S715:docs/architecture.md#L343-L360]. Effects write only logical space and know
  nothing about hardware or mapping [S715:docs/architecture.md#L362-L368].
- **Modifiers are a first-class concept WLED lacks.** A modifier is a coordinate
  transform: *static* modifiers (mirror, tile, crop, mask, transpose) are folded
  into the LUT at build time and cost **zero per frame**; *live* modifiers
  (rotation) run a per-frame remap pass only when present
  [S715:docs/architecture.md#L430-L439]. The binding rule: "an effect renders a
  pattern; it does not transform geometry" — anything that remaps *where* pixels
  land is stripped out of ported effects and made a modifier
  [S715:docs/architecture.md#L416].
- **Four mapping types** in one LUT abstraction: 1:1 identity (no table at all —
  `hasLUT()==false` fast path), 1:1 shuffled (serpentine), 1:0 unmapped (sparse
  layouts), 1:N multimap (mirror/clone), stored CSR (offsets + destinations
  arrays) [S715:src/light/layers/MappingLUT.h#L10-L18]. On a fragmented no-PSRAM
  heap the destinations array falls back to 4096-entry power-of-two **pages**
  (shift/mask indexing — Xtensa has no hardware divide)
  [S715:src/light/layers/MappingLUT.h#L27-L35,L166-L208].
- **The LUT build is a textbook counting-sort CSR build** run physical→logical:
  pass A counts destinations per logical cell, prefix-sum to offsets, pass B
  scatters driver indices, then replay through `setMapping` in order
  [S715:src/light/layers/Layer.h#L410-L507] (excerpted,
  `excerpts/S715-projectmm-mapping/`). Because each *physical* light folds to at
  most one logical cell, `maxDest == driverCount` exactly — no N× over-allocation
  and no overflow ceiling (an earlier `logicalCount * maxMultiplier` product
  wrapped uint16 and black-screened no-PSRAM boards
  [S715:docs/history/decisions.md#L563-L567]).
- **Natural order is measured, not declared**: `isNaturalOrder()` does one
  allocation-free pass over the layout's coords to check `driverIdx == box index`;
  if true and no modifiers, the mapping is identity-memcpy — "the FPS floor for
  the common case" [S715:src/light/layers/Layer.h#L391-L408].
- **Adaptive memory + degradation cascade**: LUT and shared output buffer are
  allocated only when actually needed (>1 layer, or logical≠physical) and only if
  heap minus a 32 KB reserve allows; degradation order is full pipeline → skip
  LUT+output buffer (forced 1:1) → halve layer dimensions to a minimum 8×8, each
  step observable via per-module flags [S715:docs/architecture.md#L489-L516].
  Result: 16,384 LEDs (128×128) on a **classic ESP32 without PSRAM**
  [S715:README.md#L19].

### MoonModule base class

Everything is a MoonModule — effects, modifiers, layouts, drivers, *and* system
services (HTTP, WiFi, mDNS, OTA, filesystem) and peripherals (mic, gyro)
[S715:docs/architecture.md#L76-L88]. The base
[S715:src/core/MoonModule.h#L83-L140] provides:

- Lifecycle `setup()/loop()/loop20ms()/loop1s()/teardown()`, all auto-propagating
  to children (teardown reverse-iterates); leaf modules pay one predicted-not-taken
  branch [S715:docs/architecture.md#L90-L98].
- **Controls bind to member variables by reference** — the hot path reads the
  variable directly (zero call overhead); UI writes go through the pointer, and a
  three-tier change protocol governs reactions: (1) `onUpdate(name)` cheap
  in-place, (2) `controlChangeTriggersBuildState(name)` gate, (3) tree-wide
  `onBuildState()` rebuild sweep [S715:docs/architecture.md#L165-L175]. This is
  what delivers projectMM's headline property: **every configuration change —
  pin map, strand length, protocol, mic — applies live with no reboot**
  [S715:docs/architecture.md#L177-L181].
- Self-reporting: `classSize()` (captured via `sizeof(T)` at factory
  registration), `dynamicBytes()`, `loopTimeUs()` per module — this
  instrumentation exposed that ArtNet took 51% of frame time at 128×128 and that a
  mirror modifier over-allocated 64 KB [S715:docs/history/decisions.md#L360-L362].
- `ModuleFactory` maps type-name strings → create functions so the HTTP API can
  instantiate modules at runtime; roles (`Effect/Modifier/Driver/Layout/Layer/
  Peripheral`) are registration properties, **not** type guarantees — a
  role-keyed downcast crashed and the fix is factory-probed metadata
  [S715:docs/history/decisions.md#L559-L561].
- The UI is 100% module-driven: it renders any module from its declared controls;
  a new module type requires zero UI changes [S715:docs/architecture.md#L540-L548].

### Cross-platform layer (ESP32 / Teensy / Pi / desktop)

The claim is "one source tree, unmodified, on ESP32, Teensy, desktop, Raspberry
Pi" [S715:docs/architecture.md#L54]. Reality at the pinned commit: **only
`src/platform/esp32/` and `src/platform/desktop/` exist**; Linux desktop covers
the Pi, and "the platform layer for Teensy is added when the first hardware
target is wired in" [S715:docs/building.md#L225-L229] — Teensy is aspirational.

How the abstraction works:

- **One boundary, hard rule**: all `#ifdef`, platform includes, and hardware API
  calls live exclusively in `src/platform/`; everything else compiles on every
  target. Compile-time branching uses `if constexpr` on `platform_config.h`
  constants (`hasPsram`, `hasWiFi`, …), never preprocessor conditionals outside
  the boundary — enforced by a commit-gate script
  (`scripts/check/check_platform_boundary.py`) [S715:docs/architecture.md#L208-L221].
- The abstracted surface is deliberately tiny and demand-driven: time
  (millis/micros), memory (`alloc` prefers PSRAM, `freeHeap`, `maxAllocBlock`),
  executable memory (`allocExec/writeExec` for the JIT), sockets
  (`UdpSocket`, non-blocking `TcpConnection::writeSome`), scheduling
  (`yield/delayMs/delayUs/reboot`) [S715:docs/architecture.md#L210-L219].
  "Abstractions are added when a concrete implementation needs them, not
  pre-designed" — a direct reaction to v1, where only ~50 of 1,397 PAL lines were
  real platform abstraction [S715:docs/history/decisions.md#L137-L140].
- Separate build entry points: root CMakeLists for desktop, `esp32/` wrapper for
  IDF — no `if(ESP_PLATFORM)` pollution [S715:docs/history/decisions.md#L61-L64].
- A notable inhabitant of the platform layer: **MoonLive**, a live-scripting
  engine that compiles effect scripts to *native machine code* (recursive-descent
  parser → typed three-address IR → per-ISA MacroAssembler backends for Xtensa,
  RISC-V, and host arm64/x86-64), placed in `allocExec` memory and called via a
  function pointer per tick [S715:docs/architecture.md#L418-L428]. Scripted
  effects at near-native speed on a $4 MCU — the successor to
  ESPLiveScript/ARTI's bound-function model.

### Effect model & coordinate handling

- **Natively 3D**: coordinates, layouts, mappings all operate in (x, y, z); 1D/2D
  are just size-1 axes, no mode switch [S715:docs/architecture.md#L320-L329].
  Types: `lengthType = int16_t` for coordinates (negatives allowed for
  out-of-bounds motion), `nrOfLightsType = uint16_t` without PSRAM / `uint32_t`
  with, chosen at compile time — halves the LUT on small boards
  [S715:src/light/light_types.h#L22-L54].
- Effects receive logical `(width, height, depth)` + elapsed millis; they declare
  native dimensionality via `dimensions()` (`D1/D2/D3`) and the Layer **extrudes**
  lower-D output: a D1 effect writes one column (1D runs along Y so it is
  literally the first column of its 2D form), which is memcpy'd across x, then
  z=0 across z [S715:src/light/layers/Layer.h#L259-L287,
  docs/architecture.md#L385-L397]. Extrude is a no-op comparison for D3 and free
  when unused axes are size 1.
- **Buffer persists frame to frame** (FastLED/WLED convention); an early
  auto-clear design silently broke every trail/scroll/Game-of-Life effect and was
  reverted [S715:docs/history/decisions.md#L540-L549]. Fades are *collected*:
  effects call `fadeToBlackBy(amt)`, the Layer keeps the MIN across effects and
  applies one whole-buffer pass per frame [S715:src/light/layers/Layer.h#L300-L305].
- Speed controls are **BPM** (`uint8_t`, default 60), animation driven by elapsed
  time, never frame count; the binding robustness rules are "effects must run at
  every grid size (incl. 0×0×0)" and "must animate at every tick rate" — the
  canonical bug being `dt * bpm * K / 60000` truncating to zero on fast desktops,
  fixed by accumulating the raw `dt*bpm` numerator and dividing at the read site
  [S715:docs/architecture.md#L403-L414].

### Color depth: fixed vs float

The pipeline is **8-bit integer end to end**. Buffers are raw `uint8_t*` sized
`channelsPerLight × nrOfLights` with runtime `channelsPerLight` (3 = RGB, 4 =
RGBW, up to 255 for DMX fixtures) — no fixed channel layout, no float stage
[S715:docs/architecture.md#L485]. Hot-path rule: "integer math preferred over
float in per-light work" — ESP32's single-precision FPU compounds per-light
[S715:docs/architecture.md#L202]. The in-tree color library is FastLED-shaped but
independently written: integer `hsvToRgb` (hue as 6×256 sectors, all uint16
intermediates) and `scale8` with the +1 correction so `scale8(x,255)==x`
[S715:src/core/color.h#L13-L41]; integer trig lives in `math8.h`. Layer blending
is integer-only 8-bit alpha-over `(src·α + dst·(255−α))/255` and
additive-with-clamp [S715:docs/architecture.md#L347]. Output correction is a
256-entry brightness LUT + channel-order table + `W = min(r,g,b)` white
derivation, applied per light at the driver edge
[S715:src/light/drivers/Correction.h#L31-L81]. Individual effects may use float
*locally* for their own math (BouncingBalls, StarField, etc.) — the framework
neither provides nor requires it. **There is no >8-bit color depth, no gamma
table yet (the field is named `briLut` so gamma can land as a fill change), and
no temporal dithering** — precision is explicitly traded for scale (16 K lights
on a no-PSRAM chip). Contrast Section B, which spends its entire budget on the
opposite trade.

### Postmortem: what MoonLight/WLED decisions were abandoned, and why

`docs/history/decisions.md` [S715] is an explicit, written postmortem of four
iterations (MoonLight → v1 → v2 → v3). The abandoned decisions, each with its
stated reason:

1. **Building on a fork lineage at all.** MoonLight (WLED-MM era, on
   ESP32-SvelteKit) required tracking **1,271+ local changes to survive
   rebases**, and features stalled waiting for upstream (Ethernet, async
   webserver) [S715:docs/history/decisions.md#L88-L93]. projectMM is a clean
   slate with zero third-party libraries: no FastLED, no ESPAsyncWebServer, no
   ArduinoJson, no Arduino framework — ideas are carried forward and credited,
   code is written fresh from specs [S715:README.md#L41-L45].
2. **WLED's effect model (geometry folded into effects).** WLED effects carry
   their own mirror checkboxes, rotation, pinwheels because WLED has no modifier
   concept; projectMM strips these into composable modifiers so one Rotate works
   on every effect [S715:docs/architecture.md#L416].
3. **Segment-style 2D-as-special-mode.** Replaced by native 3D with size-1 axes
   [S715:docs/architecture.md#L320-L322].
4. **Reboot-to-apply configuration.** Most LED firmware (WLED included) needs a
   reboot for pin/output changes; the three-tier control-change protocol makes
   every change live [S715:docs/architecture.md#L177-L181].
5. **God classes.** v1's `StatefulModule` conflated five jobs (lifecycle, JSON,
   persistence, children, timing); `ModuleManager` was REST adapter + memory
   accountant + persister + debouncer at once. Split into narrow concerns
   [S715:docs/history/decisions.md#L132-L145].
6. **JSON persistence as assumed default.** A ~1700-LOC JSON persistence layer
   was fully abandoned; the working replacement is a small flat-file,
   control-list-driven design. Rule extracted: "question the format premise" —
   the helper-proliferation list is quoted as the smell
   [S715:docs/history/decisions.md#L479-L491].
7. **Abstraction-first development.** v2's "maximize minimalism" produced 19
   sprints of refactoring abstractions instead of shipping ("Architecture
   Astronaut trap"); rule: concrete first, abstract later — don't design the base
   class before the first effect works [S715:docs/history/decisions.md#L178-L196].
8. **Fixed-size arrays** (MAX_CHILDREN=8 etc.) → grow-on-demand in setup, since
   the hot path only iterates [S715:docs/history/decisions.md#L350-L352].
9. **Banning PSRAM** (an earlier stance) — wrong for 10 K+ LEDs; the refined rule
   is PSRAM for large contiguous boot-time blocks only, never small scattered
   loop allocations [S715:docs/history/decisions.md#L254-L261].
10. **Unpaced UDP output.** Blasting 97 ArtNet packets/frame caused receiver
    drops that *looked like rendering bugs*; frame pacing is mandatory,
    non-blocking gate only [S715:docs/history/decisions.md#L263-L269].
11. **Separate map stage with its own buffer** — doubles memory; replaced by
    map-on-the-fly during blend [S715:docs/history/decisions.md#L285-L292].

What was deliberately *kept* from MoonLight (the harvest list): PhysMap-style
compact mapping entries, the `nrOfLights` width typedef, controls-bound-to-members,
LightsHeader's `channelsPerLight` unification of LEDs + DMX, 1:1 fast-path flags,
the shared audio struct (16-band FFT), and driver-edge brightness/gamma/color-order
LUTs [S715:docs/history/decisions.md#L112-L126,L448].

Hardware lessons worth stealing directly: modern WS2812B revisions read a 412 ns
"0" as "1" — T0H max ≈ 380 ns on newer chips, so new encoders must target ≤375 ns
zero-slots (the classic FastLED-lineage 416 ns slot only works behind a 74HCT
level shifter) [S715:docs/history/decisions.md#L591]; and an i80/LCD_CAM bus
claims *all* its data GPIOs — partial pin sets never initialize
[S715:docs/history/decisions.md#L583].

### What pewpew should steal

- **The Layout / Layer / Modifier / Driver decomposition** — specifically
  modifiers as coordinate transforms folded into a cold-path LUT (zero per-frame
  cost for mirror/tile/crop) and the "effects render patterns, never transform
  geometry" rule. This is the cleanest separation of pattern vs geometry in any
  engine read so far.
- **The counting-sort CSR mapping build with the tight `maxDest == driverCount`
  bound** (excerpted) and the four-mapping-type taxonomy with a measured (not
  declared) identity fast path.
- **The three-tier control-change protocol** (`onUpdate` → gate → idempotent
  `onBuildState` sweep) giving live-reconfiguration-without-reboot; plus
  "resolve links at rebuild, tolerate null at use" as the stale-pointer
  robustness pattern.
- **Compile-time width selection** (`nrOfLightsType`) and the `int16_t`
  coordinate convention with per-axis guarded operators (`Coord3D`).
- **Per-module self-reporting** (`classSize/dynamicBytes/loopTimeUs`) — it found
  real bottlenecks (ArtNet 51% of frame) and real leaks.
- **The degradation-cascade philosophy** — shed quality (LUT, resolution, preview
  frame rate) in a defined order, observable, never crash. Also the preview
  transport's adaptive-bitrate design (resumable send, drop-new backpressure,
  lattice downsample).
- **The decisions.md practice itself**: an append-only postmortem doc per
  iteration is why this deep-dive was cheap; pewpew's ADR habit is the same idea.
- The WS2812B ≤375 ns T0H timing bound for any new encoder design.

### What to avoid

- **GPL-3.0**: code cannot be copied into pewpew unless pewpew accepts GPL-3.0;
  the EUPL heritage (WLED/MoonLight) is gone. Ideas/architecture are fair game;
  excerpts here are for study/citation only.
- **8-bit-only color path** — projectMM deliberately has no HD gamma, no
  dithering, no >8-bit anywhere; wrong trade for pewpew's stated fidelity goals
  (see fastled.md / fadecandy.md dives and Section B).
- **Everything-is-a-MoonModule for system services** is elegant but the authors
  themselves flag the trap that produced it twice (v1/v2 base-class-first
  over-engineering); adopt the uniform-module idea only after the pipeline works
  ("concrete first, abstract later" is *their* rule).
- **Bus factor / maturity**: effectively a single product owner + AI-agent
  workflow (CLAUDE.md-driven); v1.0.0 shipped 2026 with same-day commits at HEAD.
  Ascendant but young — treat as a design reference, not a dependency.
- Single-threaded render loop today; the two-core double-buffer handover is
  designed ("🚧") but **not implemented** — don't cite projectMM as proof of a
  working multicore pipeline.

### Open questions

- Teensy and Raspberry Pi are advertised targets but no Teensy platform layer
  exists at the pinned commit ("added when the first hardware target is wired
  in") and Pi appears to be just the Linux desktop build — actual portability
  beyond ESP32+desktop is unverified.
- Measured per-LED render cost and FPS tables exist (`docs/performance.md`) but
  were not read in this dive; the 128×128 @ ~19 FPS Ethernet ArtNet figure comes
  from decisions.md and needs confirming against performance.md before citing in
  an ADR.
- The MoonLive JIT's safety model (what stops a bad script from scribbling over
  IRAM) is deferred to a backlog doc not read here.
- How multi-layer blending interacts with the 1:N multimap `overwrites()` flag
  (plain-copy vs read-add-clamp, "≈4× faster") under real compositing loads is
  documented but not benchmarked in what was read.

---

## Section B — SmoothLed

- repo: https://github.com/mattshepcar/SmoothLed
- pinned: mattshepcar/SmoothLed@e09236cfc63a96c565d97ef316073452a38cf86d [S716]
- license: MIT (LICENSE file, © 2020 Matt Shepcar)
- accessed: 2026-07-03 (last commit 2020-07-07 — dormant since 2020; ~1,083 lines
  total across src/)
- Target: Arduino library for tinyAVR 0/1-series (ATtiny1614 etc.) under
  megaTinyCore. Self-description: "FadeCandy style control … gamma correction,
  interpolation and temporal dithering … good quality output at low intensities
  with smooth fades and no 'stair stepping'" [S716:README.md#L2-L4].

### How it achieves its signature quality (interpolation + dithering inner loop)

Two ideas, one hardware and one algorithmic:

**1. Hardware waveform generation (CCL trick).** The WS2812 waveform is produced
by chip peripherals, not bit-banging: the USART in MSPI mode (or SPI) supplies a
bit clock, a TCB timer runs one-shot pulses off that clock, and a CCL
(Configurable Custom Logic) lookup-table combines clock + serial data + timer
output into the WS2812 pulse train on an EVOUT/LUT-out pin — the SPI *data* pin
isn't even used [S716:README.md#L6-L10, src/SmoothLedCcl.h#L20-L25,L75-L130].
Low/high pulse widths are `begin()` parameters in nanoseconds (defaults 200/600),
converted to CPU cycles, with `USART0.BAUD = highCycles * 64` deriving the bit
rate [S716:src/SmoothLedCcl.h#L22,L107,L249]. The CPU's only wire-facing job is
writing one byte per channel into the USART data register when DREIF says ready.
Because output is a byte-at-a-time stream, **there is no frame/output buffer at
all** in the streaming path — color math executes *during* transmission.

**2. Per-channel Interpolator state machine.** All persistent state is one
5-byte struct per channel: `int16_t step; int16_t value; uint8_t dither;`
[S716:src/SmoothLed.h#L63-L79]. The per-channel, per-frame update
[S716:src/SmoothLed.cpp#L122-L131] (excerpted,
`excerpts/S716-smoothled-inner-loop/`):

```cpp
value = fmac(value, step, dt);                    // value += (step * dt) >> 7
if (highByte(maxvalue) < highByte(value))
    value = value < 0 ? 0 : maxvalue;             // clamp [0, maxValue]
lut += highByte(value);                           // gamma segment select
uint16_t corrected = lerp(lut[0], lut[1], lowByte(value)) + dither;
dither = lowByte(corrected) & ditherMask;         // carry the residual
return highByte(corrected);                       // byte sent to the wire
```

- **Interpolation coefficient (`dt`).** `beginFade(numFrames)` sets a fade-time
  accumulator increment `ΔT = 0x8000 / numFrames`; each frame `updateTime()`
  advances `m_Time += ΔT` and returns `dt` = the change in `m_Time`'s **high
  byte** [S716:src/SmoothLed.cpp#L51-L71]. Over a whole fade the high byte walks
  0→0x80, so the `dt` values sum to exactly 128 — and since the accumulate is
  `value += (step*dt) >> 7`, the total applied is exactly `step` (which
  `setFadeTarget` initialises to `target − value`
  [S716:src/SmoothLed.h#L93-L96]). Fades are therefore frame-rate independent
  and land exactly on target with no drift, using only an 8-bit multiplier per
  step. A Q1.15 `fraction` variant scales `step = (target−value)·fraction >> 15`
  for partial-convergence (exponential-style) fades
  [S716:src/SmoothLed.cpp#L200-L203].
- **Gamma via tiny piecewise-linear LUT.** Instead of a 256×16 table, a
  **32-entry × 16-bit** gamma-2.5 table (64 bytes) is linearly interpolated:
  high byte of `value` picks the segment, low byte lerps between adjacent
  entries (`a + ((b−a)·t) >> 8`) [S716:src/SmoothLed.cpp#L10-L17,L127-L128;
  src/SmoothLedMultiply.h#L77-L80]. A python generator
  (`extras/makeGammaTable.py`) builds custom tables. Table values are stored
  bit-inverted; the CCL LUT flips them back on the wire
  [S716:src/SmoothLed.cpp#L10].
- **Temporal dithering as error-feedback (Fadecandy's scheme, smaller).** The
  8 fractional bits of the 16-bit gamma-corrected intensity are not thrown away:
  the previous residual `dither` is added before truncation and the new residual
  (masked by `ditherMask`) is carried to the next frame — a first-order
  sigma-delta per channel. `DitherBits` selects how many fractional bits
  participate (DITHER0..DITHER8; default DITHER5 = keep top 5 fraction bits)
  because at low refresh rates full dithering flickers visibly — the README
  states ≥400 Hz update rate is wanted for full benefit
  [S716:README.md#L14-L16, src/SmoothLed.h#L13-L15]. Dither accumulators are
  seeded staggered (`i * 26`) across channels so neighbouring channels don't
  dither in phase [S716:src/SmoothLed.cpp#L27-L29].

### Precision at each stage

| Stage | Representation |
|---|---|
| API input | 8-bit per channel |
| Internal value | `int16_t`, "expanded range": `v8 × range + (v8×range >> 8)` → [0, range·256−1], range = LUT size − 1 = 31, i.e. ~13 bits of intensity resolution [S716:src/SmoothLed.h#L134-L143] |
| Fade step | `int16_t` (= target − value; optionally ×Q1.15 fraction via 20-cycle `fmul`) |
| Fade advance | `value += (step × dt) >> 7`, dt ∈ [0,128] — AVR `fmul/fmulsu` fractional-multiply instructions, 10 cycles [S716:src/SmoothLedMultiply.h#L24-L44] |
| Gamma out | 16-bit (8.8): 32×16-bit LUT + 8-bit lerp |
| Dither carry | 8-bit residual, masked to 1–8 configurable bits |
| Wire | 8-bit per channel, residual carried forward in time |

Net effect: 8-bit wire output that *temporally averages* to ~13-bit gamma-corrected
intensity — the same architecture as Fadecandy (16-bit interpolate → gamma →
temporal dither → 8-bit wire; see the fadecandy.md dive) scaled down to a 5-byte
per-channel state and a 64-byte table.

### Cycles per LED & footprint (RAM/flash minimums)

The hot loop exists twice: portable C++ and a hand-scheduled AVR asm version
(`SMOOTHLED_ASM_UPDATE`, default on). The asm loop is cycle-annotated in the
source [S716:src/SmoothLedUpdate.S#L26-L88]:

- interpolate + clamp + store: 22 cycles; gamma segment fetch: +10 (32); lerp:
  +16 (48); dither: +6 (54); DREIF wait + port write + loop: +10 = **64 cycles
  per channel** — the function is named `SmoothLedUpdate8cpb`: 8 cycles per bit
  × 8 wire bits per byte, i.e. the math exactly saturates the wire at 8 MHz
  ("8 cycle per bit loop for maximum throughput at 8MHz"
  [S716:src/SmoothLed.cpp#L88]).
- Per RGB LED: 3 × 64 = **192 cycles ≈ 24 µs at 8 MHz**, computed concurrently
  with transmission. The buffered variant (`SmoothLedUpdate`, render to RAM) is
  58 cycles/channel [S716:src/SmoothLedUpdate.S#L98-L167].
- **RAM**: 5 bytes per channel (15 B per RGB LED) of Interpolator state + ~8 B
  object fields; **zero output buffer** in streaming mode. A 60-LED wearable
  strip costs 900 B — fits an ATtiny1614's 2 KB with room to spare.
- **Flash**: whole src/ is ~1,083 lines; the update core is one ~90-instruction
  asm routine + a 64-byte gamma table. (No compiled-size figure published;
  the library targets 16 KB-flash ATtiny parts — see Open questions.)

### What pewpew should steal

- **The 5-byte Interpolator as the minimum viable quality layer**: value(16) +
  step(16) + dither(8) per channel is the floor for
  Fadecandy-class output — pewpew's wearable tier can budget RAM as
  `5 × channels`, full stop.
- **The exact-landing fade scheme**: accumulate a Q16 fade clock, feed the
  *high-byte delta* as dt, apply `(step·dt)>>7` — sums to precisely `step` over
  the fade with no float, no divide, no drift, frame-rate independent. Directly
  portable to any MCU (or to host-side pre-render).
- **Piecewise-linear gamma from a 32×16 LUT** (64 bytes) instead of a 512-byte
  256×16 table — with lerp, low-end quality is preserved where gamma curvature
  matters most.
- **Configurable dither depth** (`ditherMask`): the insight that dither bits
  must scale with refresh rate (fewer bits at low Hz to avoid visible flicker)
  is exactly the knob pewpew's quality layer needs, since wearable refresh rates
  vary with strip length.
- **Compute-during-transmit / zero-frame-buffer streaming** when the output
  peripheral gives a byte-granular ready flag — the general pattern, even though
  the CCL specifics are AVR-only.
- The staggered per-channel dither seeding (`i*26`) — free decorrelation.

### What to avoid

- The CCL/EVSYS/TCB waveform generator is **tinyAVR-0/1-specific** and consumed
  the USART/SPI + a timer + a CCL LUT + an event channel; nothing of it ports to
  ESP32/RP2040 (which have RMT/PIO instead). Steal the math, not the transport.
- Dormant since July 2020; Arduino/megaTinyCore API drift is untested. Use as
  algorithm reference, not a dependency.
- 8-bit-input API: the internal 13-bit space is only reachable through
  `set(uint16)`/`expandRange`; a pewpew port should widen the public input to
  16-bit rather than inherit the 8-bit entry point.
- The gamma table's last entry (0xffeb, i.e. −21 in the inverted/signed lerp)
  makes the top segment's endpoint slightly negative; combined with a zero
  dither accumulator this can momentarily truncate a full-brightness channel —
  harmless in practice but don't copy the table blindly (regenerate with the
  provided script and verify the endpoints).

### Open questions

- No published flash-size or maximum-LED-count benchmark; the 64-cycles/channel
  figure comes from the source's own cycle annotations and was not measured on
  hardware in this dive.
- The interaction between `updateTime()` returning 0 after a fade completes
  (dt = 0 → values freeze) and continued dithering: `update()` still runs the
  dither stage every frame, so temporal dithering continues on static colors —
  inferred from the code path, not documented.
- Whether the 8-cycles-per-bit pacing holds at 10/16/20 MHz clocks (the DREIF
  wait would just idle; throughput becomes wire-bound) is untested here.
- `SmoothLedBuffer.h`, `SmoothLedReceiver.h` (an interrupt-driven receive path)
  and `SmoothLedCcl` SPI mode were not read in depth.
