# Pixelblaze (ElectroMage) — docs/forum deep dive

- **Firmware**: CLOSED SOURCE. No repo to pin. This dive reads official docs,
  Ben Hencke's forum/Mastodon posts, the open-source Python client
  (zranger1/pixelblaze-client), and the open output-expander firmware.
- **Author/vendor**: Ben Hencke (ElectroMage LLC), forum handle "wizard"
- **Accessed**: 2026-07-03
- **Open code pinned in this dive**: see sources fragment
  `research/sources/_fragments/code-pixelblaze.md` (S680–S699).

## 1. Pattern language semantics (render/render2D/render3D, built-ins, compile model)

Primary source: Ben Hencke's own docs repo simap/pixelblaze, v3 branch [S680] —
the same markdown that ships inside the Pixelblaze editor.

### Execution contract

- A pattern exports `render(index)`, called once **per pixel per frame**; the
  pattern sets the pixel's color as a side effect via `hsv()`/`rgb()`
  ("current pixel" is implicit state) [S680:README.expressions.md#L19-L21].
- If a 2D/3D pixel map is configured, `render2D(index, x, y)` /
  `render3D(index, x, y, z)` are used instead; a pattern may export several
  and the firmware auto-selects the best match for the installed map
  [S680:README.expressions.md#L21].
- `beforeRender(delta)` runs once per frame before the pixel loop; `delta` is
  elapsed milliseconds since the previous call, **"with a resolution of
  6.25 ns"** — i.e. delta is a fixed-point ms value carrying sub-µs fraction
  bits [S680:README.expressions.md#L23]. Idiomatic patterns do all
  time-dependent state updates in `beforeRender` and keep `render` a pure
  function of (index, coords, globals).

### Coordinate normalization ("world units")

The mapper accepts a JSON array-of-arrays (`[[x,y],…]` or `[[x,y,z],…]`) in
any physical unit, or a browser-side JS generator function `(pixelCount) =>
map`. The **editor** (not the device) rescales all coordinates to 0.0–1.0
"world units" from the bounding box of the map, so patterns are
size-independent [S680:README.mapper.md#L12-L16]. x/y/z passed to
render2D/render3D are in 0.0–1.0 **exclusive** [S680:README.mapper.md#L36].
Note the normalization is per-axis to the world bounding box (aspect ratio is
not preserved — a known community gotcha).

### Number model and language subset

- The language is JS (ES6) **syntax** with a heavily restricted semantics: all
  numbers are **16.16 fixed point** (range ±32,768, resolution 1/65,536)
  [S680:README.expressions.md#L25]. Bitwise operators act on the top 16 bits
  (i.e. the integer part) [S680:README.expressions.md#L76].
- Supported: functions (incl. first-class + arrow lambdas), `if/else`,
  `while/for/break/continue`, implicit globals, `var`,
  `array(size)` [S680:README.expressions.md#L76-L86].
- NOT supported: objects/classes/properties, closures (inner functions see
  only globals + own params), `switch`, `let`/`const`, array literals, any
  memory freeing (arrays are the only dynamic allocation and are never freed)
  [S680:README.expressions.md#L88-L105].
- Constants: `PI`, `PI2`, `E`, `SQRT2`, etc. [S680:README.expressions.md#L121].

### Built-ins with exact semantics

- `time(interval)` → sawtooth 0.0–1.0 with period `65.536 × interval` seconds
  (the 65.536 factor falls out of the 16.16 representation: interval is
  effectively a frequency in cycles per 65,536 ms). `.015 ≈ 1 s`. `time()` is
  the sync point: Firestorm or AP-mode following synchronizes these clocks
  across devices [S680:README.expressions.md#L151-L155].
- `wave(v)` = `(1 + sin(v·2π))/2`, sawtooth-in → sinusoid-out, 0–1 range,
  input wraps [S680:README.expressions.md#L157-L159]. `triangle(v)`,
  `square(v, duty)` are the same shape-converter pattern
  [S680:README.expressions.md#L160-L163]. This "phase in 0–1, composable
  waveform shapers" design is the core of Pixelblaze's expressiveness-per-line.
- `hsv(h, s, v)`: h wraps in 0–1 (negative wraps backward); on LEDs that
  support it the value maps to "24-bit color plus an additional 5 bits of
  brightness control" (APA102-class global brightness) — HDR at low light
  levels [S680:README.expressions.md#L167-L169]. `hsv24()` forces 24-bit only
  (documented as reducing flicker on some LEDs)
  [S680:README.expressions.md#L171-L173]. `rgb(r, g, b)` takes 0–1 floats
  [S680:README.expressions.md#L175-L177].
- Hardware I/O from patterns: `analogRead(pin)`, `pinMode`, `digitalRead/
  Write`, capacitive `touchRead(pin)` (V3) [S680:README.expressions.md#L179-L203];
  wall-clock `clockYear()…clockWeekday()` when the discovery service supplies
  time [S680:README.expressions.md#L205-L217].

### UI controls & variable export

Exporting a function named `slider<Name>(v)` / `hsvPicker<Name>(h,s,v)` /
`rgbPicker<Name>(r,g,b)` auto-generates persistent UI controls; values are
0–1 and replayed on pattern activation [S680:README.expressions.md#L41-L70].
`export var` makes globals visible to the editor's Var Watcher and readable/
writable over the WebSocket `getVars`/`setVars` API
[S680:README.expressions.md#L117] — this is the entire external-control
surface for a running pattern, and it is why pixelblaze-client can puppet
patterns without recompiling (§3).

### Compile model

The editor **compiles in the browser** as you type and ships the result to
the device; the firmware's web app bundles Esprima (a JS parser) among its
third-party licenses [S680:README.md#L40-L56], and patterns are stored with
separate source + compiled binary blobs (visible in the WebSocket pattern
format, §3). The device runs the compiled program on a fixed-point VM in the
closed firmware. Ben Hencke has described it as a bytecode/stack VM in forum
posts, and v3.30+ release notes describe VM-level optimizations; exact opcode
set is undocumented [NEEDS-VERIFICATION — see Open questions]. Consequences
of this split:
- the device never parses source (an ESP32 doing on-device JS parsing would
  be slow and RAM-hungry);
- a pattern `.epe` export contains the source, but a device-to-device binary
  copy works without the editor;
- offline compilation requires reimplementing the (closed, but stable)
  compiler — the community has not done so; pixelblaze-client uploads
  pre-compiled blobs or drives the live editor protocol instead (§3).

## 2. v3.47+ "HDR LED drivers" — precision at each stage

Firmware is closed, so this is assembled from Ben Hencke's own statements.

### What "HDR" means on Pixelblaze

- v3.47 (July 2023) was a **"total rewrite of all LED drivers"** adding "full
  HDR 48-bit color using WS2816 and NS108 LEDs" plus "much faster" WS2812
  output [S014].
- Hencke's design statement (Mastodon, 2023-07-12): "Rewrite of the pixel
  stack for #pixelblaze. **All 16 bit per element throughout.** Tons more HDR
  LED options now, and have NS108 and WS2816 LEDs support… ws2816 panel at 1%
  brightness" and "even 1% brightness leaves plenty of color resolution and
  smooth fade to black"; NS108 "driven here with 16 bits per element, 48 bit
  color… about 19 mA per element" [S063].

So the pipeline is: pattern math in 16.16 fixed point → `hsv()`/`rgb()`
convert into a **16-bit-per-element** internal pixel buffer → per-chip driver
maps that to the best the wire format offers:

| chip class | wire precision | how PB uses it |
|---|---|---|
| WS2812/WS2815 etc. | 8b/ch | truncated to 24-bit; benefit is speed, not depth [S014] |
| APA102/SK9822 | 8b/ch + 5b global | `hsv()` computes "24-bit color plus an additional 5 bits of brightness control", i.e. the global-brightness field is used as a per-pixel exponent-like extension ≈13 effective bits at low levels [S680:README.expressions.md#L167-L169] |
| WS2816 | 16b/ch, 48-bit | native 16-bit output [S063] |
| NS108 / HD108-class SPI | 16b/ch + global, 48-bit | native 16-bit output [S063] |

### Explicitly NOT temporal dithering

Hencke (2020-12-18, on a request for Fadecandy-style dithering in the output
expander): "Temporal dithering only works well if you can refresh the LEDs at
very fast rates, which is why FadeCandy has LED string length limits of 64…
I tend to gravitate toward the APA102/SK9822 type LEDs that have even better
brightness range (via global brightness data) than possible with temporal
dithering on WS2812s" [S684]. He called expander-side dithering and keyframe
interpolation "a cool feature to add" but never shipped it. No later source
contradicts this: Pixelblaze's HDR is **higher internal precision + chips
with more wire bits**, not dithering. On plain WS2812 the extra precision is
discarded.

- Master brightness is applied in the 16-bit domain (v3.47 also changed the
  editor preview to reflect pattern values only, not the brightness slider)
  [S014]. Gamma curves were reported unchanged by the rewrite ("I wouldn't
  think so" — wizard, replying to a user who perceived different response)
  [S014].
- Measured user gain from the rewrite: 864 WS2815 LEDs went from 12–24 fps to
  23–38 fps on direct output; expander-based rigs saw little change (the
  2 Mbps serial bus, not the driver, is their bottleneck) [S014].

### Relevance to pewpew

This is the *opposite* corner of the quality space from Fadecandy: Fadecandy
extracts pseudo-depth from 8-bit chips via ~400 Hz temporal dithering +
interpolation; Pixelblaze keeps a clean 16-bit pipeline and spends it only
where the chip can express it. pewpew's Python-host architecture can do both:
16-bit internal frames end-to-end (Pixelblaze's lesson: precision loss must
not happen before the last wire-format conversion), plus optional
receiver-side dithering for 8-bit chips (Fadecandy's lesson). Note the
`hsv()`/`hsv24()` split [S680:README.expressions.md#L167-L173]: exposing the
high-depth path as the default with an opt-out for flicker-sensitive chips is
a proven UX.

## 3. WebSocket API — driving Pixelblaze from Python

The firmware exposes a single WebSocket endpoint (`ws://<ip>:81`) carrying
**JSON text frames** for commands and **binary frames** for bulk data. There
is no official spec; zranger1/pixelblaze-client [S681] is the de-facto
documentation (MIT, last commit 2025-12-20 — still maintained).

### Binary frame envelope

First byte = message type, second byte = continuation flags
(frameFirst=1 / frameMiddle=2 / frameLast=4), so large payloads chunk across
frames [S681:pixelblaze/pixelblaze.py#L460-L479]:

| type | dir | meaning |
|---|---|---|
| 1 | →PB | putSourceCode (LZString-compressed source) |
| 3 | →PB | putByteCode (compiled program) |
| 4 | →PB | previewImage (JPEG for pattern list) |
| 5 | PB→ | previewFrame (live RGB preview of every render cycle) |
| 6 | PB→ | getSourceCode |
| 7 | →PB | getProgramList |
| 8 | →PB | putPixelMap |
| 9 | ↔ | ExpanderConfig |

### Key JSON commands (as exercised by the client)

- `{"getVars": true}` → `{"vars": {...}}`; `{"setVars": {name: value}}` sets
  any `export var` in the running pattern, silently ignoring unknown names
  [S681:pixelblaze/pixelblaze.py#L1227-L1243]. This is the low-latency
  external control channel (tens of Hz is practical).
- `{"setControls": {...}, "save": bool}` drives the auto-generated UI
  sliders/pickers [S681:pixelblaze/pixelblaze.py#L1245-L1258].
- `{"sendUpdates": true}` starts a stream of previewFrame binary messages —
  one per rendered frame, `pixelCount × (R,G,B)` bytes
  [S681:pixelblaze/pixelblaze.py#L891-L920]. This is how PixelTeleporter
  builds off-device simulation.
- `{"brightness": ...}`, sequencer control (`setSequencerMode`, playlists),
  `{"activeProgramId": ...}` for pattern switching, config fetch
  (`getConfig`), file I/O over HTTP endpoints (`/index.html.gz`, pattern
  files) [S681:pixelblaze/pixelblaze.py#L1006-L1177].

### Pattern upload / compile-from-Python

The client's `compilePattern()` is the most revealing method: since the
compiler lives in the device's **web UI JavaScript**, the client downloads
`/index.html.gz` from the device, scrapes out the `window.compile` script
(with version-specific adapters for firmware <3.0, ≤3.20, ≤3.40, >3.40), and
executes it in MiniRacer (embedded V8)
[S681:pixelblaze/pixelblaze.py#L1314-L1485]. The resulting program object's
`compiled` array is serialized to the device bytecode blob:

```
uint32le opcodeSectionBytes; uint32le exportSectionBytes;
int32le opcodes[];                        // 32-bit words
{ uint32le address; char name[]; \0 }[]   // exports table
```
[S681:pixelblaze/pixelblaze.py#L1490-L1512] — confirming the VM executes
32-bit-word bytecode with a name→address export table used by
getVars/setVars.

Live upload mimics the editor: `{"pause": true, "setCode": {size, crc32,
name, id}}` → binary putByteCode → `{"setControls"}` → `{"pause": false}`
[S681:pixelblaze/pixelblaze.py#L1549-L1565]. Persistent save writes a `.pbp`
file (pattern id, name, JPEG preview, bytecode, LZString-compressed source)
via `putFile` [S681:pixelblaze/pixelblaze.py#L1567-L1593].

### Expander config wire format

Binary type-9 message: 1 version byte (=5), then 12-byte rows, 8 rows per
board: `{addr(5b board|3b chan), ledType, numElements, colorOrder, uint16
pixelCount, uint16 startIndex, uint32 dataSpeed}`; colorOrder packs channel
indices 2 bits each (0x24='RGB') [S681:pixelblaze/pixelblaze.py#L1832-L1888].

### Discovery

Devices beacon to a cloud discovery service (discover.electromage.com), and
the client also enumerates by LAN probe; Firestorm (simap/Firestorm, Node.js)
does LAN-wide discovery + time sync for multi-device coordination
[S680:README.md#L26-L28].

Bottom line: Python can fully drive a Pixelblaze — set variables at animation
rate, switch/upload patterns, stream back rendered frames — but pattern
compilation depends on scraping the closed compiler out of the firmware's own
web bundle, which is fragile across firmware versions (four adapter variants
already) [S681:pixelblaze/pixelblaze.py#L1408-L1421].

## 4. Output expander serial protocol

Fully open (MIT firmware, CC-BY-SA hardware) [S682:README.md#L110-L125].
Board: STM32L432 @ 80 MHz (v3.x; v1.x was STM32F103), 8 output channels with
5 V level shifting, driven by **one 2 Mbps 8N1 UART line** from any host
[S682:firmware/Core/Src/main.c#L668]. Multiple boards share the bus: 3
cuttable jumpers set a 3-bit bus ID forming channel bits 3–5, so up to 8
boards × 8 channels = 64 channels per UART [S682:README.md#L33].

### Frame format

Every frame: 6-byte header, optional per-command struct + payload, then
CRC-32 over the whole frame (magic through last payload byte)
[S682:README.md#L13-L30]:

```c
typedef struct {
    int8_t  magic[4];   // "UPXL" — starts with 0x55, chosen for auto-baud detection
    uint8_t channel;    // bits 0-2 channel on board, bits 3-5 board bus ID
    uint8_t recordType;
} PBFrameHeader;
enum RecordType { SET_CHANNEL_WS2812 = 1, DRAW_ALL,
                  SET_CHANNEL_APA102_DATA, SET_CHANNEL_APA102_CLOCK };
```
[S682:firmware/Core/Src/app.c#L91-L93]

- `SET_CHANNEL_WS2812`: header, then
  `{uint8 numElements /*3 RGB, 4 RGBW, 0 disables*/; uint8 or:2,og:2,ob:2,ow:2 /*color order*/; uint16 pixels}`,
  then `numElements × pixels` raw bytes, then CRC
  [S682:firmware/Core/Src/app.c#L95-L99].
- `DRAW_ALL`: header + CRC only; latches **all channels on the bus
  simultaneously** [S682:README.md#L52-L58]. Data upload and draw latch are
  decoupled — the host tick-tocks: stream channel data, then one DRAW_ALL.
- `SET_CHANNEL_APA102_DATA`: adds `uint32 frequency` and 3×2-bit color order
  (data on the wire is "RGBV" — global brightness/value byte last, the
  firmware reorders to APA102's V-first frame); `SET_CHANNEL_APA102_CLOCK`
  dedicates a second channel as the APA102 clock (`{uint32 frequency}`)
  [S682:firmware/Core/Src/app.c#L101-L110]. Output timing is fixed at 800 kHz
  in the current firmware despite the frequency field
  [S682:firmware/Core/Src/app.c#L79-L84].

### CRC detail

CRC-32 (standard reflected CRC-32, implemented via STM32 hardware CRC with
`REV_IN|REV_OUT`, output XOR 0xFFFFFFFF) [S682:firmware/Core/Src/uart.c#L36-L44].
Transmitted little-endian after payload.

### Buffering, error handling, timing

- v3.x buffers `BYTES_PER_CHANNEL = 4808` bytes per channel = **1600 RGB or
  1200 RGBW pixels per channel** [S682:firmware/Core/Inc/app.h#L11-L12]. (The
  README's "240 RGB / 180 RGBW" figure is stale v1.x text; the v1 STM32F103
  had far less RAM.)
- **No double buffering.** On CRC mismatch the channel's data is zeroed and
  the channel disabled until a valid frame arrives — corrupt data is never
  displayed [S682:README.md#L62-L70]. The magic sequence realigns the stream
  after corruption; no inter-byte timeout is required
  [S682:README.md#L66-L68].
- Because there's no double buffer, channel data sent immediately after
  DRAW_ALL races the ongoing draw. WS2812 draw of a full 240-px v1 buffer
  takes 5760 bit-times @ 800 kHz = 7.2 ms; since input (2 Mbps ≈ 1.6 Mbps
  effective) is slower than output, waiting ~3.6 ms after DRAW_ALL guarantees
  data never overtakes the scan-out [S682:README.md#L72-L78].
- Output stage is the OctoWS2811/Fadecandy trick, credited as such: bytes are
  transposed into per-bit-position words ("bitMangler"), then TIM1 + 3 DMA
  channels bang all 8 GPIOs in parallel with zero CPU per bit — DMA1 sets
  start bits, DMA2 writes data bits (continuing or cutting the pulse), DMA3
  resets all lines [S682:README.md#L80-L100].

### Could pewpew's host drive expanders directly?

Yes, trivially — this is the protocol's design intent ("can be used with any
microcontroller that can output 2Mbps serial", no sustained-rate requirement)
[S682:README.md#L5-L7]. Existing third-party hosts prove it: a NodeJS library
(derwentx/js-pixelblaze-expander), a C library (bosporos/libpbx), and Ben's
own Arduino PBDriverAdapter [S680:README.md#L24-L38]. From a Linux host or
Pi, a 2 Mbps-capable UART (FTDI/CP2102N, or the Pi's PL011) plus this framing
is all that's needed. Budget: 2 Mbps ≈ 200 kB/s ≈ 66k RGB pixel-updates/s on
the whole bus — e.g. 8 channels × 275 px @ 30 fps, or fewer pixels at higher
rates. The bus, not the boards, is the bottleneck (the v3 firmware comments
note the hardware CRC could sustain >4 Mbaud, but the shipped baud is 2 M)
[S682:firmware/Core/Src/app.c#L15-L17].

## 5. Sensor board data format

Fully open (MIT firmware, CC-BY-SA hardware) [S683:README.md]. STM32F0 @
48 MHz doing all the DSP; host (Pixelblaze or anything else) just reads a
**115200-baud serial stream** [S683:src/main.c#L129] — the sensor board is a
self-contained audio-analysis peripheral, no handshake, broadcast-only.

### Wire format (frame ≈ every 25.6 ms, i.e. one per 512-sample window @ 20 kHz)

Per README [S683:README.md#L23-L33] and `processSensorData()`
[S683:src/output.c#L71-L145], all little-endian:

1. `"SB1.0\0"` (6 bytes)
2. `uint16 frequencyData[32]` — magnitudes, 12.5 Hz–10 kHz
3. `uint16 energyAverage`, `uint16 maxFrequencyMagnitude`, `uint16 maxFrequencyHz`
4. `int16 accelerometer[3]` (±16 g range)
5. `uint16 light` (ALS, 12-bit ADC << 4)
6. `uint16 analogInputs[5]` (12-bit ADC << 4)
7. `"END\0"` (4 bytes)

### The DSP worth studying — dual-rate FFT with log-spaced band merge

- Audio is sampled at 20 kHz by DMA; a ping-pong 512-sample buffer feeds a
  512-point fixed-point real FFT (fix_fft) → 256 bins @ ~39.06 Hz each
  [S683:src/output.c#L3-L8][S683:src/output.c#L118].
- Problem: 39 Hz bins can't resolve bass. Solution: the same stream is
  **downsampled by 50× (averaged) to 400 Hz** into a 32-sample circular
  buffer; a second 32-point FFT gives 12.5 Hz bins for the bottom end
  [S683:src/main.c#L274-L295].
- The 32 output bands are assembled as: **6 low bands** from the 400 Hz FFT
  (12.5–162.5 Hz, bin-map {3,4,6,8,10,13}) + **26 high bands** from the
  20 kHz FFT (195 Hz–10 kHz, quasi-log map {5,6,8,…,225,255}), each band
  taking the **max** (not sum) of its constituent bins
  [S683:src/output.c#L10-L17][S683:src/output.c#L86-L114].
- Windowing: Hann applied via the FFT's own sine LUT; magnitude via
  `fix16_sqrt` keeping 4 extra fractional bits ("only overloads… for REALLY
  LOUD inputs"), saturating at 16 bits [S683:src/output.c#L32-L69].
- `energyAverage` is the pre-window mean |sample|; `maxFrequency` is the
  argmax bin of the high FFT × 39.0625 Hz [S683:src/output.c#L98-L119].

This dual-rate trick (small FFT on decimated audio for bass + big FFT for the
rest) is a cheap, proven way to get musically useful low-frequency resolution
without a 4096-point FFT — directly reusable in pewpew's audio pipeline,
where it's nearly free in Python/numpy.

## 6. Ecosystem health signals (dated)

- **Firmware: stalled at v3.47 (2023-07-13).** No firmware release
  announcement newer than v3.47 is visible on the forum as of 2026-07-03
  [S014][S685]. Hencke, asked for a roadmap (2025-02): "I don't have a
  roadmap shared" [S025].
- **Vendor: alive, hardware-focused.** Ben Hencke was actively answering
  support/engineering questions on the forum on 2026-06-25/26 (Pixelblaze
  Pico Plus thread — a current compact product with castellated edge pads and
  level shifters) [S685]. Products (V3 Standard, Pico, Pico Plus, Pro
  Expander) remain on sale [S013].
- **Forum: modestly but consistently active** — ~15 topics with posts across
  May–July 2026, mostly hardware questions and pattern help [S685].
- **Community tooling is still appearing**: "PXLBLZ", a third-party pattern
  editor/sandbox/IDE + 30 patterns, announced 2026-06-16; repeated threads
  asking for offline emulators show demand the closed firmware can't satisfy
  [S685]. pixelblaze-client last commit 2025-12-20 (active) [S681].
- **Open-source periphery is frozen**: docs repo last commit 2020-10-26
  [S680], expander firmware 2023-07-07 [S682], sensor board 2022-07-06
  [S683].
- Verdict for pewpew's comparison matrix: **stable/waning** — healthy niche
  hardware business with a loyal community, but the software platform has had
  no visible evolution in 3 years and its single-maintainer, closed-source
  nature is the community's own stated pain point (offline editing,
  emulation, sync features repeatedly requested) [S025][S685].

## What pewpew should steal

1. **The pattern contract: per-pixel pure function over normalized
   coordinates.** `beforeRender(delta)` for stateful time evolution +
   `render{,2D,3D}(index, coords…)` as a pure color function, with the engine
   auto-selecting the render arity that matches the installed map
   [S680:README.expressions.md#L19-L23]. This one design decision is why
   Pixelblaze patterns are portable across any fixture — pewpew's pattern API
   should have the same shape (and in Python it can be vectorized: call once
   with coordinate arrays instead of once per pixel).
2. **World-unit normalization done at map-install time, not render time**
   [S680:README.mapper.md#L12-L16] — patterns never see physical units;
   the mapper (host-side, like Pixelblaze's browser-side JS map generators)
   does all scaling once.
3. **Composable 0–1 phase waveforms**: `time(interval)` sawtooth + `wave/
   triangle/square` shapers [S680:README.expressions.md#L151-L163]. Tiny API,
   huge expressiveness, and `time()` doubles as the cross-device sync point.
4. **Keep full precision to the last wire conversion**: 16-bit-per-element
   internal buffer, per-chip back-end deciding how to spend it (APA102 5-bit
   global brightness, WS2816/HD108 native 16-bit) [S063][S014], with an
   `hsv()`/`hsv24()`-style opt-out for flicker-sensitive chips
   [S680:README.expressions.md#L167-L173]. Combine with Fadecandy-style
   dithering for 8-bit chips — the two approaches are complementary and
   Hencke himself endorsed dithering as viable for short strings [S684].
5. **The output expander as a supported pewpew sink.** The UPXL protocol is
   open, trivially implementable (2 Mbps UART, CRC-32 framed, DRAW_ALL
   latch), and off-the-shelf boards give 8 level-shifted channels per board,
   64 per bus [S682]. A ~100-line Python driver lets pewpew drive existing
   Pixelblaze installations' wiring without any Pixelblaze.
6. **Zero-on-CRC-error, never display garbage** [S682:README.md#L62-L70] and
   magic-resync framing — the right robustness posture for any pewpew
   host→receiver serial link.
7. **Dual-rate FFT band analysis** from the sensor board: decimate 50× for a
   bass FFT, merge log-spaced max-of-bins bands [S683:src/output.c#L3-L17].
   Also: sensor boards are cheap, open, and pewpew could ingest their SB1.0
   serial stream directly.
8. **setVars/getVars via `export var`** — a single mechanism serves UI
   controls, debugging (var watcher), and external network control
   [S680:README.expressions.md#L117]; controls auto-generated from exported
   function names (`sliderFoo`) is excellent low-ceremony UX
   [S680:README.expressions.md#L41-L70].

## What to avoid

- **Closed compiler / closed VM.** The community pays for it constantly:
  pixelblaze-client must scrape `window.compile` out of the firmware's web
  bundle with four version-specific adapters [S681:pixelblaze/pixelblaze.py#L1408-L1421],
  and offline editors/emulators are perennial forum requests [S685]. pewpew's
  engine being open Python is the direct answer.
- **16.16 fixed point as the only number type** [S680:README.expressions.md#L25]
  made sense on ESP8266/ESP32 but leaks into pattern semantics (the 65.536 s
  `time()` factor, ±32k range limits, bitwise-on-top-16-bits). A Python
  engine should use floats and keep units human (seconds).
- **No closures, no objects, arrays never freed**
  [S680:README.expressions.md#L88-L105] — acceptable limits for a
  microcontroller DSL, but they cap pattern complexity; don't replicate.
- **Single-maintainer bus factor with no published roadmap** [S025] — the
  ecosystem-shaping risk that makes building *on* Pixelblaze (rather than
  merely interoperating with it) unattractive.
- **Per-axis bounding-box normalization without aspect-ratio preservation**
  [S680:README.mapper.md#L16] — a known source of distorted 2D patterns;
  pewpew should normalize with aspect preserved (or offer both).

## Open questions

- **VM internals**: opcode semantics of the 32-bit bytecode words
  [S681:pixelblaze/pixelblaze.py#L1490-L1512] are undocumented; whether the
  VM is stack- or register-based, and how `beforeRender`'s "6.25 ns
  resolution" delta is sourced (ESP32 cycle counter?), is not stated anywhere
  I found. Do not guess.
- **Exact WS2812 gamma/brightness math**: whether the closed drivers apply a
  gamma LUT before 16→8-bit truncation, and where the master brightness
  multiply happens for 8-bit chips, is not publicly specified; Hencke's only
  comment is that v3.47 didn't intentionally change curves [S014].
- **Preview frame encoding details**: pixelblaze-client treats type-5 frames
  as pixelCount×RGB bytes [S681:pixelblaze/pixelblaze.py#L904-L920]; whether
  preview is pre- or post-brightness changed in v3.47 [S014], and any header
  bytes/downsampling for large counts, unverified.
- **Pro Output Expander** (4× buffered channels, higher power) — its serial
  protocol is presumably UPXL-compatible but I found no open firmware for the
  Pro variant; the v3.x repo covers the standard 8-channel board only [S682].
- **"HDR" on plain WS2812**: no source states any depth benefit on 8-bit
  chips post-v3.47; inference (speed only) is from silence plus [S684] — a
  bench test would settle it.
- Whether any firmware beyond v3.47 shipped silently (device updater) without
  a forum announcement — forum evidence only shows none announced [S685].
