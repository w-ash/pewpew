# Code reading: fadecandy (firmware + fcserver)

- repo: https://github.com/PimentNoir/fadecandy (community mirror; original scanlime/fadecandy DELETED by author, see [S015][S027])
- pinned: PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d [S600]
- license: MIT — Copyright (c) 2013 Micah Elizabeth Scott (top-level LICENSE; same MIT header on every firmware/server source file) [S600:LICENSE#L1-L3]
- accessed: 2026-07-03
- provenance caveat: mirror authenticity checked 2026-07-03 — MIT LICENSE credits
  Micah Elizabeth Scott, README references scanlime assets/URLs throughout, and the
  shallow history's parent commits include `Merge branch 'master' of
  https://github.com/scanlime/fadecandy` (commit ee9da65). The mirror adds only
  trivial changes (a dependabot bump of `minimist` in examples/node, two comment/
  timeout tweaks to a Processing example). Firmware and server sources appear
  unmodified from upstream. Treat as authentic but remember it is not the
  author's repo; the pinned SHA is a mirror SHA.

Firmware is C++ for Teensy 3.x (Freescale MK20DX128, ARM Cortex-M4, DSP
instructions used: `__SMUADX`, `__USAT`, BFI). fcserver is C++ (libusbx +
libwebsockets + rapidjson), one binary, JSON config.

## Scope

THE canonical reference for "better than clown mode": hosts send ordinary 8-bit
RGB frames at ordinary frame rates; the device makes them look smooth via
(1) keyframe interpolation, (2) a 16-bit-in/16-bit-out interpolated color LUT,
and (3) per-channel temporal dithering, all re-run at the WS2811 hardware
refresh rate (~400–500 Hz), not the host frame rate.

## How it achieves its signature quality

### 1. Pipeline overview & data flow

Fixed geometry: 8 strips x 64 LEDs = 512 pixels, 1536 color channels
(`NUM_OUTPUT=8`, `LEDS_PER_STRIP=64`, `CHANNELS_TOTAL=1536`)
[S600:firmware/fc_defs.h#L30-L36].

Main loop (runs as fast as the LED DMA allows, no sleeping)
[S600:firmware/fadecandy.cpp#L145-L187]:

1. `calculateInterpCoefficient()` — where are we between the two most recent
   host keyframes? (section 2)
2. `updateDrawBuffer_IxDx(coefficient)` — for all 512 pixels: interpolate the
   two 8-bit keyframes to 16-bit, run each channel through the 257-entry LUT
   (16-bit → 16-bit), add the per-channel dither residual, round to 8 bits,
   store the new residual, and bit-plane-transpose into the OctoWS2811 DMA
   buffer [S600:firmware/fc_draw.cpp#L25-L327]. Four variants of this whole
   function are compiled (interpolation on/off x dithering on/off) by
   re-including the same source with `FCP_INTERPOLATION`/`FCP_DITHERING` macros
   [S600:firmware/fadecandy.cpp#L54-L94]; the variant is chosen per loop
   iteration from the config flags [S600:firmware/fadecandy.cpp#L159-L173].
3. `leds.show()` — swap double-buffered DMA bit-plane buffers and kick the
   next WS2811 transmission [S600:firmware/OctoWS2811z.cpp#L184-L225].
4. `buffers.finalizeFrame()` — promote a completed USB keyframe/LUT into the
   active set, in main-loop context (section 2)
   [S600:firmware/fc_usb.cpp#L38-L65].

USB receive happens in interrupt context (`usb_rx_handler` →
`fcBuffers::handleUSB`) and only stores packet references; all heavy work is
in the main loop [S600:firmware/fadecandy.cpp#L139-L143]
[S600:firmware/fc_usb.cpp#L68-L115].

USB protocol (bulk OUT, 64-byte packets; control byte = 2-bit type, 1 'final'
bit, 5-bit index) [S600:doc/fc_protocol_usb.md#L46-L68]:
- type 0: video keyframe, 25 packets x 21 pixels x 24-bit RGB (offset 1..63)
- type 1: color LUT, 25 packets x 31 little-endian uint16 entries (offset 2..63)
- type 2: config byte (dither/interp disable bits, LED control)

Output frame push rate: the WS2811 bit clock is 800 kHz (1.25 µs/bit)
[S600:firmware/OctoWS2811z.cpp#L92-L97]; a frame is always 64 LEDs x 24 bits =
1536 bit-times = 1.92 ms, plus a >= 50 µs latch enforced in `show()`
[S600:firmware/OctoWS2811z.cpp#L188-L196]. Rendering of frame N+1 overlaps DMA
transmission of frame N (double buffer swap, `std::swap(frameBuffer,
drawBuffer)`), so the loop period is max(render time, ~1.97 ms) — an upper
bound of ~507 Hz refresh, independent of how many LEDs are physically
attached (the firmware always clocks out all 64 per strip). Micah's project
materials describe the achieved rate as roughly 400 Hz [S016]; the exact
render time is not documented in-repo (see Open questions). Every one of
these ~400-500 Hz hardware frames is a fresh interpolation + LUT + dither
evaluation; the host can keep sending 30-60 fps.

### 2. Keyframe interpolation

Triple-buffered keyframes: `fbPrev` (interpolating from), `fbNext`
(interpolating to), `fbNew` (being filled by USB)
[S600:firmware/fc_usb.h#L120-L138]. When a video packet with the 'final' bit
arrives, the main loop rotates the buffers: `fbNew` is timestamped with
`millis()` and becomes `fbNext`, old `fbNext` becomes `fbPrev`, old `fbPrev`
is recycled as the new `fbNew` [S600:firmware/fc_usb.cpp#L117-L125]. While a
finalize is pending, further video packets are rejected (NAKed and retried via
`usb_rx_resume()`), which back-pressures the host to at most one frame per
output refresh [S600:firmware/fc_usb.cpp#L77-L89].

Coefficient (computed once per output frame, `calculateInterpCoefficient()`
[S600:firmware/fadecandy.cpp#L97-L120]):

```
now       = millis()                       # 1 ms resolution
tsDiff    = fbNext.timestamp - fbPrev.timestamp   # duration of previous host frame gap
tsElapsed = now - fbNext.timestamp
coefficient = (min(tsElapsed, tsDiff) << 16) / tsDiff   # in [0x0000, 0x10000]
```

I.e. the firmware assumes the *next* keyframe will arrive after the same
interval as the *previous* two, and slews linearly over that window; the
`min()` clamps at 100 % `fbNext` if the host stalls, so output freezes at the
last keyframe instead of extrapolating. Precision: 16-bit fixed point
(0x10000 = 100 % next), but the timestamps are only millisecond-resolution, so
at a 60 fps host rate there are only ~16 distinct coefficient values per
keyframe pair — each of which still lands on a distinct 16-bit color target.

Per pixel, per channel [S600:firmware/fc_pixel.cpp#L25-L50] with coefficients
pre-scaled in the caller [S600:firmware/fc_draw.cpp#L40-L51]:

```
icNext = 257 * coefficient          # [0, 0x1010000]
icPrev = 257 * (0x10000 - coefficient)
i16 = (prev8 * icPrev + next8 * icNext) >> 16    # [0, 0xFFFF]
```

The factor 257 folds the 8-bit → 16-bit expansion (`x * 257` == `x << 8 | x`)
into the interpolation multiply; `icPrev + icNext = 0x1010000` exactly, so
`prev8 == next8 == 255` yields exactly 0xFFFF. Products are 32-bit unsigned
(max 255 * 0x1010000 = 0xFFFF0000 — just fits). With interpolation disabled
the pipeline uses `next8 * 0x101` directly and coefficient 0x10000
[S600:firmware/fc_pixel.cpp#L46-L50] [S600:firmware/fadecandy.cpp#L164-L171].

### 3. LUT pipeline (gamma / color balance)

Structure: 3 channels x 257 entries of uint16, red array then green then blue
(`LUT_CH_SIZE 257`) [S600:firmware/fc_defs.h#L38-L39]
[S600:firmware/fc_usb.h#L106-L114]. Entry k represents input k/256 of full
scale; entry 256 corresponds to input 0x10000, "which can't quite be reached"
— it exists so `lut[index+1]` is always valid
[S600:firmware/fc_pixel_lut.cpp#L34-L36]. The host computes the whole table
(there is NO default; firmware boots with a zeroed LUT = black output)
[S600:doc/fc_protocol_usb.md#L38] and uploads 16-bit entries; at finalize time
the firmware stores each entry right-shifted by 1 (15-bit) so pairs can be
multiplied with the signed SMUAD DSP instruction
[S600:firmware/fc_usb.cpp#L127-L140].

Lookup with linear interpolation between adjacent entries, 16-bit in → 16-bit
out [S600:firmware/fc_pixel_lut.cpp#L26-L86]. Reference semantics (from the
in-source comment):

```
index    = arg >> 8         # [0, 255]
alpha    = arg & 0xFF       # [0, 255]
invAlpha = 0x100 - alpha
result   = (lut[index] * invAlpha + lut[index+1] * alpha) >> 8   # [0, 0xFFFF]
```

The shipped implementation loads `lut[index]` and `lut[index+1]` as one
unaligned 32-bit load, packs `alpha`/`invAlpha` into one word via
`0x01000000 + alpha - (alpha << 16)`, and computes both multiplies plus the
add in a single `__SMUADX`, then `>> 7` (the LUT was pre-shifted right 1, so
15-bit x 8-bit-sum >> 7 restores 16 bits)
[S600:firmware/fc_pixel_lut.cpp#L68-L81]. Max output is 0xFFFE, not 0xFFFF
(one LSB lost to the 15-bit storage). With interpolation compiled out the
lookup is just `lut[arg >> 8] << 1` [S600:firmware/fc_pixel_lut.cpp#L82-L85].

Note the LUT does gamma AND white-point/color-balance in one table — fcserver
bakes `gamma` and per-channel `whitepoint` scaling into the entries (section
6). LUT updates are async (not frame-synchronized) and "instant"; intended for
initialization/config time only [S600:firmware/fc_usb.cpp#L91-L99,127-L140].

### 4. Temporal dithering

Pure per-channel error accumulation carried across output frames — no spatial
diffusion, no ordered-dither matrix, no PRNG. State: one `int16_t` residual
per channel, 1536 total [S600:firmware/fadecandy.cpp#L40-L46]. Per channel per
output frame (~400-500 Hz), after interpolation and LUT
[S600:firmware/fc_pixel.cpp#L58-L88]:

```
i16 += residual              # add carry from previous output frame
out8 = clamp16(i16 + 0x80) >> 8    # round to nearest 8-bit (USAT saturate, then shift)
residual = i16 - out8 * 257        # new error vs. the 8-bit value re-expanded to 16-bit
```

Key details:
- The residual compares against `out8 * 257` (the exact 16-bit meaning of the
  emitted 8-bit code), so the error metric is consistent with the 8→16
  expansion used everywhere else.
- Rounding is `+ 0x80` then `__USAT(x, 16) >> 8`: the value may be negative
  before rounding (residual can be as low as about -128) and above 0xFFFF
  after, so it saturates to [0, 0xFFFF] before the shift
  [S600:firmware/fc_pixel.cpp#L65-L78].
- Residual is int16 rather than int8: "Usually 8 bits is enough, but there are
  edge cases when it isn't, and we don't have the spare CPU cycles to saturate
  values before storing" [S600:firmware/fadecandy.cpp#L40-L45]. Steady-state
  magnitude stays within about ±128.
- The dither rate equals the output frame rate (~400-500 Hz), NOT the host
  frame rate: a static dim color still flickers between adjacent 8-bit codes
  hundreds of times per second, time-averaging to the 16-bit target.
- Because dithering runs after interpolation + LUT, slow fades get 16-bit
  intermediate targets every output frame, and dithering renders each of those
  targets — this combination (not dithering alone) is what kills visible
  stair-stepping at low brightness.

Result packing is `(g8 << 16) | (r8 << 8) | b8` — WS2811 GRB wire order
[S600:firmware/fc_pixel.cpp#L87-L88] — then bit-transposed into 6 words per
pixel-row for OctoWS2811's 8-strips-in-parallel DMA format via bitfield
writes that compile to BFI instructions [S600:firmware/fc_draw.cpp#L61-L326].

### 5. End-to-end precision budget (host 8-bit RGB → emitted PWM)

| Stage | In | Out | Notes |
|---|---|---|---|
| Host OPC/sketch pixel | 8b/ch | 8b/ch | plus optional float ops in fcserver (section 6) |
| USB keyframe | 8b/ch | 8b/ch | 24-bit RGB, 21 px/packet [S600:doc/fc_protocol_usb.md#L70-L87] |
| Keyframe interpolation | 2 x 8b + 17-b coefficient (0..0x10000, ms-quantized) | 16b [0,0xFFFF] | exact at endpoints (x257 trick) [S600:firmware/fc_pixel.cpp#L40-L50] |
| Color LUT | 16b index; table 257 x 16b stored as 15b | 16b [0,0xFFFE] | linear interp, 8-bit alpha; 1 LSB lost to 15-bit storage [S600:firmware/fc_pixel_lut.cpp#L60-L81] |
| Dither add + round | 16b + int16 residual | 8b/ch | round-to-nearest with carry; error preserved exactly in residual [S600:firmware/fc_pixel.cpp#L58-L85] |
| WS2811 output | 8b/ch @ ~400-500 Hz | LED PWM | temporal average ≈ the 16-bit target |

So the *instantaneous* wire value is always 8 bits, but the *time-averaged*
output tracks a 16-bit target that is itself continuously slewed between host
keyframes. Effective added depth ≈ log2(ditherRate / flickerFusionRate); at
~500 Hz output vs ~50-100 Hz fusion this is roughly 2-3 bits of solid extra
depth plus smooth-in-time transitions, which is why fades that step visibly on
raw 8-bit hardware look continuous. There is no PWM-depth trick at the LED
itself: WS2811 PWM depth stays 8-bit; everything above 8 bits lives in time.

### 6. fcserver: OPC handling + config model

Single C++ daemon (libusbx + forked libwebsockets + rapidjson). One TCP port
(default 7890) serves three protocols; the first 4 bytes of each connection
are sniffed — `"GET "` means HTTP/WebSockets, anything else is treated as raw
OPC [S600:server/src/tcpnetserver.cpp#L163-L320]. HTTP serves a compiled-in
web UI; WebSockets carries a JSON API (`list_connected_devices`,
`server_info`, per-device `device_options` / `device_pixels` /
`device_color_correction`) [S600:server/src/fcserver.cpp#L446-L519]
[S600:server/src/fcdevice.cpp#L384-L415]. An optional `relay` port re-emits
every OPC message to subscribers [S600:server/src/fcserver.cpp#L143-L166].

**OPC message handling.** Standard OPC framing: channel byte, command byte,
16-bit big-endian length, payload [S600:server/src/opc.h#L40-L58]. Commands:
`0x00` Set Pixel Colors; `0xFF` SysEx with 32-bit ID — `0x00010001` Set
Global Color Correction (payload is JSON, parsed and fed to the same LUT
builder as the config file) and `0x00010002` Set Firmware Configuration (raw
config bytes) [S600:server/src/fcdevice.cpp#L453-L501]
[S600:doc/fc_protocol_opc.md#L42-L79]. Every complete OPC message is
broadcast to ALL attached devices; each device decides what applies to it via
its mapping table [S600:server/src/fcserver.cpp#L143-L166].

**Mapping.** Per-device `map` is an array of small array-instructions,
evaluated per message [S600:server/src/fcdevice.cpp#L503-L651]:
- `[opcChannel, firstOPCPixel, firstOutputPixel, count]` — contiguous copy
- `[opcChannel, firstOPCPixel, firstOutputPixel, count, "rgb"]` — plus a
  3-letter swizzle, each letter one of r/g/b/l (l = average luminosity)
  [S600:server/src/opc.h#L62-L90]
- negative `count` writes output pixels in reverse order
- the instruction only fires when `opcChannel == msg.channel` (exact match;
  the OPC "channel 0 = broadcast" convention is NOT implemented)
  [S600:server/src/fcdevice.cpp#L556-L558]
- all offsets/counts are clamped against both message size and the 512-pixel
  framebuffer, overflow-safe [S600:server/src/fcdevice.cpp#L560-L565]

Mapped pixels are written straight into a pre-built array of 25 64-byte USB
packets whose control bytes (type/index/final) were set once in the
constructor, so "send frame" is a single 1600-byte bulk transfer with zero
per-frame marshalling [S600:server/src/fcdevice.cpp#L69-L82]
[S600:server/src/fcdevice.h#L53-L64].

**Frame pacing.** A completed Set Pixel Colors immediately triggers
`writeFramebuffer()` — the host frame rate directly sets the firmware's
keyframe cadence. At most `MAX_FRAMES_PENDING = 2` USB frame transfers may be
in flight; beyond that the frame is not queued — a flag is set and the
(by-then newest) framebuffer contents are submitted when a transfer
completes, i.e. frames coalesce and the newest data wins. A source TODO
acknowledges there is no end-to-end flow control back to the OPC client
[S600:server/src/fcdevice.cpp#L362-L382,200-L233] [S600:server/src/fcdevice.h#L64].

**Config model.** One JSON document: `{listen, relay, verbose, color,
devices}` [S600:server/config.json#L1-L19]
[S600:doc/fc_server_config.md#L14-L122]. `devices` entries are matched to
hot-plugged hardware by `type` (e.g. "fadecandy", "enttec", "apa102spi") and
optional `serial` (null = any) [S600:server/src/usbdevice.cpp#L59-L78]
[S600:server/src/fcserver.cpp#L185-L255]; on match the device gets its `map`,
its firmware options (`led`, `dither`, `interpolate` → config packet bits)
[S600:server/src/fcdevice.cpp#L143-L170], and the global `color` correction.
Config is effectively static after startup except color correction and
firmware flags, which are runtime-mutable via OPC SysEx or WebSockets.

**LUT builder (`FCDevice::writeColorCorrection`)** — this is where gamma and
whitepoint become the 3 x 257 x 16-bit table, computed in double precision
[S600:server/src/fcdevice.cpp#L235-L360]:

```
for channel in r,g,b:
  for entry in 0..256:
    input = (entry << 8) / 65535.0        # 0 .. ~1.0000153 (entry 256 is the sentinel)
    input *= whitepoint[channel]           # whitepoint applied BEFORE gamma
    if input * linearSlope <= linearCutoff:
        output = input * linearSlope       # linear toe
    else:
        nonlinearInput = input - (linearSlope * linearCutoff)
        scale = 1.0 - linearCutoff
        output = linearCutoff + pow(nonlinearInput / scale, gamma) * scale
    entry16 = clamp(round(output * 0xFFFF), 0, 0xFFFF)   # little-endian uint16
```

Defaults: `gamma = 1.0`, `whitepoint = [1,1,1]`, `linearSlope = 1.0`,
`linearCutoff = 0.0` in code; the shipped config uses gamma 2.5
[S600:server/config.json#L6-L9]. The **linear toe is the anti-flicker knob**:
with a pure power curve, very dim inputs map to tiny 16-bit targets whose
dithering (e.g. flipping between PWM 0 and 1 at a low duty) can be visible
when LEDs are viewed directly; setting `linearCutoff` (suggested 1/256, the
lowest 8-bit PWM level) makes the bottom of the curve linear so dim values
land on/near real PWM steps, trading dynamic range for zero flicker
[S600:server/src/fcdevice.cpp#L243-L253] [S600:doc/fc_server_config.md#L90-L92].
Note the toe math is only self-consistent for `linearSlope == 1`: the
nonlinear branch subtracts `linearSlope * linearCutoff` where the actual
x-coordinate of the linear/nonlinear intersection is
`linearCutoff / linearSlope`, so other slopes produce a discontinuity (see
Open questions).

## What pewpew should steal

1. **The pipeline shape itself**: keyframe-interpolate (8→16 bit) → color LUT
   (16→16) → temporal dither (16→8), re-evaluated for every channel at the
   *output device rate*, fully decoupled from the pattern/host frame rate.
   This maps perfectly onto NumPy: three vectorized ops over a
   `(N_channels,)` uint16/int32 array per output tick.
2. **The x257 expansion convention**: expand 8→16 bit as `x * 257`, compute
   dither error against `out8 * 257`. Endpoints are exact (255 → 0xFFFF), and
   quantizer + error metric agree, so residuals can never drift.
3. **Interpolation coefficient from arrival timestamps**
   [S600:firmware/fadecandy.cpp#L97-L120]: assume the next keyframe arrives
   after the same interval as the last two; clamp at 100% so a stalled source
   freezes rather than extrapolating. No negotiated frame rate, no clock sync
   — dumb and robust.
4. **257-entry interpolated LUT**: entry k = input k/256, one sentinel entry
   at the top so `lut[i+1]` always exists. In NumPy this is exactly
   `np.interp` (or `idx = x >> 8; alpha = x & 0xFF` blending) over a
   `(3, 257)` uint16 table. Keep 16-bit entries — the 15-bit squeeze was an
   ARM SMUAD trick, not a design point.
5. **Per-channel signed residual accumulator for dithering**: one int16 array
   the size of the channel count, no PRNG, no ordered matrix; residual
   carries between *output* frames. With int32 NumPy arrays the
   "8 bits isn't quite enough" caveat disappears.
6. **The `linearCutoff` toe** in the gamma curve as a first-class,
   user-visible anti-flicker control — it directly encodes the tradeoff
   between low-end resolution and visible dither flicker on directly-viewed
   LEDs, which pewpew will face with any temporal dithering scheme.
7. **Host-computed LUT, dumb evaluator downstream**: gamma/whitepoint changes
   are a table re-upload (runtime JSON message), never a firmware change.
   Same split works for a Python host + microcontroller output node.
8. **Frame coalescing under backpressure** (`MAX_FRAMES_PENDING = 2`, newest
   frame wins, never queue stale video) — the correct policy for live LED
   video, worth copying in any transport pewpew builds.
9. **Declarative mapping instructions** `[channel, firstIn, firstOut,
   count(, swizzle)]` with negative-count reversal and hard clamping — a tiny
   language that covers strip direction, splits, and channel-order fixes
   without code.

## What to avoid

- **Millisecond timestamps for interpolation**: at a 60 fps host rate the
  coefficient only takes ~16 distinct values per keyframe pair
  [S600:firmware/fadecandy.cpp#L112-L119]. Harmless at Fadecandy's scale but
  a reimplementation should use a monotonic sub-ms clock.
- **Unguarded division by `tsDiff`**: two keyframes finalized within the same
  millisecond make `tsDiff == 0`; the code divides anyway
  [S600:firmware/fadecandy.cpp#L115-L119] and only survives because ARM
  Cortex-M UDIV returns 0 on divide-by-zero. Guard it explicitly.
- **The `linearSlope != 1` discontinuity** in `writeColorCorrection`
  [S600:server/src/fcdevice.cpp#L334-L342]: nonlinear branch offsets by
  `linearSlope * linearCutoff` instead of the intersection x-coordinate
  `linearCutoff / linearSlope`. Fix the math if the toe slope is exposed.
- **Fixed 64-LED frame length**: firmware always clocks out 64 pixels/strip
  [S600:firmware/fc_defs.h#L32-L35], so short strips still pay the full
  1.92 ms — dither rate can't rise when fewer LEDs are attached. A
  reimplementation should scale frame length to the real LED count (shorter
  strips → faster refresh → finer dithering).
- **No default LUT**: firmware boots with an all-zero LUT (black output)
  until the host uploads one [S600:doc/fc_protocol_usb.md#L38]. Fine when a
  daemon owns the device; a footgun otherwise. Ship an identity/gamma default.
- **Exact-match OPC channels**: the OPC convention of channel 0 as broadcast
  is not implemented — maps listening on channel 1 ignore channel-0 messages
  [S600:server/src/fcdevice.cpp#L556-L558]. Decide the semantics explicitly.
- **No end-to-end flow control** from OPC client to USB (acknowledged TODO
  [S600:server/src/fcdevice.cpp#L364-L370]); silent frame dropping is the
  right *default* but the producer should be able to observe it.

## Open questions

- **Exact achieved output refresh rate.** Deterministic lower structure: 64 x
  24 bits at 800 kHz = 1.92 ms + 50 µs latch → ≤ ~507 Hz; render overlaps DMA.
  The actual `updateDrawBuffer` render time on the 48 MHz MK20DX128 is not
  documented in-repo (there is a runtime `benchmark.py` reading the perf
  counter, but no recorded numbers). Project materials say "roughly 400 Hz"
  [S016][NEEDS-VERIFICATION for the exact figure].
- **Is the `tsDiff == 0` divide intentional?** No guard, no comment; works on
  Cortex-M because UDIV returns 0 (coefficient 0 → show fbPrev). Deliberate
  reliance or luck — undocumented.
- **Is the `linearSlope * linearCutoff` subtraction a bug?** For the shipped
  default `linearSlope = 1.0` the curve is continuous; the general case looks
  wrong but no upstream discussion is preserved in this mirror.
- **End-to-end latency budget** (OPC in → light out) is not characterized
  anywhere in-repo: firmware NAKs video packets while a finalize is pending
  [S600:firmware/fc_usb.cpp#L77-L89] and fcserver allows 2 in-flight frames,
  suggesting up to ~2 output frames (~4-5 ms) of transport latency plus one
  keyframe interval of interpolation lag (interpolation by construction
  displays the *previous* inter-frame span). The interpolation lag is
  inherent to the design: output always trails the newest keyframe by up to
  one host frame period.
- **WS2811 waveform timing choices** (T0H = 60/255, T1H = 176/255 of the bit
  period) are justified only by an empirical comment disputing the datasheet
  [S600:firmware/OctoWS2811z.cpp#L50-L66]; treat as folklore-grade, verify on
  target hardware.
