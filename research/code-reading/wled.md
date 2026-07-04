# Code reading: WLED

- repo: https://github.com/wled/WLED
- pinned: wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63 [S645]
- license: EUPL v1.2 or later
- accessed: 2026-07-03
- role for pewpew: likely **receiver tier** (network → pixels), and a cautionary
  tale for effect-engine design.

## 1. Segment / effect model (FX.h, FX.cpp, FX_fcn.cpp)

Note: this pin is the post-0.15 dev tree (2026-07). It differs materially from
the widely deployed 0.14/0.15: each Segment now owns a full-length `uint32_t`
render buffer and segments are composited into a global frame buffer with
Photoshop-style blend modes. Older releases rendered segments directly into the
bus buffer.

### Segment class

`Segment` (FX.h, "segment, 76 bytes") is simultaneously: geometry (start/stop,
startY/stopY for 2D, grouping, spacing, offset), UI state (bitfield options:
selected/reverse/on/mirror/freeze/reset/reverse_y/mirror_y/transpose/map1D2D/
soundSim/set), effect parameters (mode, palette, speed, intensity, custom1-3,
check1-3, 3× uint32 colors, opacity, cct, blendMode), effect runtime scratch
(step, call, aux0, aux1, plus a heap `data` blob), a private per-segment pixel
buffer `uint32_t *pixels`, and an optional `Transition` struct that heap-copies
the ENTIRE old Segment for cross-fading [S645:wled00/FX.h#L419-L530]. One class,
five responsibilities — the central design smell.

Effect drawing state is communicated through **static class members**
(`_vLength/_vWidth/_vHeight`, `_currentColors`, `_currentPalette`, `_modeBlend`
semaphore, clipping rect) [S645:wled00/FX.h#L485-L498], set up by
`beginDraw()` before each effect call. This makes the renderer single-threaded
by construction and effects impossible to run concurrently.

### Effect function contract

An effect is `typedef void (*mode_ptr)()` — a bare global function of no
arguments [S645:wled00/FX.h#L815]. It communicates entirely via macros over a
global `strip._currentSegment` pointer:

- `SEGMENT` / `SEGENV` → `(*strip._currentSegment)` [S645:wled00/FX.h#L106-L110]
- `SEGLEN` → `Segment::vLength()` (static, virtual length after
  grouping/spacing/mirror/1D-to-2D mapping)
- `SEGCOLOR(x)`, `SEGPALETTE` → the static transition-blended copies
- speed knob idiom `SPEED_FORMULA_L = 5 + 50*(255-speed)/SEGLEN`
  [S645:wled00/FX.h#L113]

Effects keep state in `SEGENV.step/call/aux0/aux1` or call
`SEGENV.allocateData(len)` for a heap blob that is silently freed/reallocated
on segment resize (effects must re-init when `SEGENV.call == 0`). Registration
is `addEffect(FX_MODE_X, &mode_x, _data_FX_MODE_X)` where `_data_*` is a
**string** metadata DSL, e.g. `"Blends@Shift speed,Blend speed;;!"` encoding
name, slider labels, color slots, palette usage and 1D/2D flags — parsed by the
JS UI, not the firmware.

**Why custom effects are hard**: (a) no stable ABI — effects are compiled in;
adding one means forking FX.cpp (11,224 lines, ~190 effects in one file) and
FX.h's mode-ID enum; (b) the contract is implicit — a correct effect must know
about `SEGENV.call==0` re-init, `progress()`/`modeBlend` transition semantics,
virtual-vs-physical length, vStrip index hacks packed into the upper 16 bits of
the pixel index for M12_pBar mode [S645:wled00/FX_fcn.cpp#L757-L773]; (c) all
state is via globals/statics, so effects cannot be tested off-device; (d) the
mode function returns nothing and is called blind — misbehaving effects stall
the whole loop (WLED just logs "Slow effects").

### Palettes

Palettes are FastLED `CRGBPalette16` (16 RGB entries, interpolated).
`loadPalette()` maps palette id → built-in gradient palettes (palettes.cpp,
progmem 4-byte-per-entry gradient format), harmonics-generated random palettes,
or custom palettes from JSON files. Effects sample via
`Segment::color_from_palette(i, mapping, moving, mcol, pbri)` which wraps
FastLED `ColorFromPalette` with wrap policy `paletteBlend` (wrap-when-moving /
always / never / no-interpolation) and re-attaches the W channel from the
segment color slot [S645:wled00/FX_fcn.cpp#L1166-L1187]. All 8-bit.

### Transitions and blending

Two independent mechanisms:

1. **Segment-internal transition** (`startTransition`): heap-copies the whole
   old Segment (including its pixel buffer) into `_t->_oldSegment`. Every
   frame, `service()` runs the NEW effect, then — if the mode changed or the
   blending style isn't FADE — sets a `_modeBlend` semaphore and runs the OLD
   effect too on the copy [S645:wled00/FX_fcn.cpp#L1330-L1367]. So during any
   transition, CPU cost per segment roughly doubles and RAM temporarily holds
   two full pixel buffers + two effect-data blobs. Palette transition is
   incremental: `nblendPaletteTowardPalette` called `(255*prog/65535 -
   prevBlends)` times per frame — ~255 blend passes over the transition
   [S645:wled00/FX_fcn.cpp#L407-L432].

2. **Segment compositing** (`WS2812FX::blendSegment`): each frame `show()`
   clears the global `uint32_t *_pixels` frame buffer and blends every active
   segment into it with one of 17 blend modes (add, multiply, screen, overlay,
   softlight, dodge, burn... 8-bit integer approximations)
   [S645:wled00/FX_fcn.cpp#L1388-L1443]. A fast path handles
   no-transition/no-grouping/no-mirror segments with pointer-stepped loops;
   the slow path applies 18 transition *styles* (swipe/push/circular/fairy
   dust) implemented as per-pixel clipping rectangles + index shifts, plus
   grouping expansion and mirroring [S645:wled00/FX_fcn.cpp#L1514-L1732].
   Non-rectangular transitions decide old-vs-new per pixel via
   `isPixelClipped()`; FAIRY_DUST is a per-pixel `hashInt(i) % len` threshold
   against 16-bit progress [S645:wled00/FX_fcn.cpp#L739-L755].

### Frame loop

`WS2812FX::service()` [S645:wled00/FX_fcn.cpp#L1318-L1386]: fixed frametime
(`_frametime = 1000/_targetFps`, default 42 fps; `MIN_FRAME_DELAY` floor "to
keep wifi alive"), cooperative — one pass per Arduino `loop()`. Per frame:
handleTransition → resetIfRequired → beginDraw → run mode fn (+ old mode fn if
transitioning) per segment, then `show()`: composite segments → optional
per-pixel `gamma32()` → `BusManager::setPixelColor(getMappedPixelIndex(i), c)`
per pixel → `BusManager::show()` [S645:wled00/FX_fcn.cpp#L1734-L1799]. The
ledmap indirection (`getMappedPixelIndex`) is applied at paint time, per pixel,
every frame.

## 2. Realtime / receiver paths (udp.cpp, e131.cpp, DDP)

### Protocol inventory

- **DDP** (port 4048): handled in `handleDDPPacket()` [S645:wled00/e131.cpp#L20-L93].
  RGB24 or RGBW32 (data-type bits `0b011` → 4 ch/LED); channelOffset gives the
  pixel start so frames span multiple packets; PUSH flag = "render now". WLED
  tracks whether the sender ever sets PUSH (`ddpSeenPush`) and renders every
  packet if not. 4-bit sequence number; with `e131SkipOutOfSequence` it drops
  packets up to 5 behind the last push [S645:wled00/e131.cpp#L42-L52]. DDP is
  the only realtime protocol with an explicit per-frame offset AND a render
  flag — the sanest of the bunch and the natural pewpew→WLED wire format.
- **E1.31/sACN and Art-Net**: `handleE131Packet()` — universe math (170 RGB or
  128 RGBW LEDs/universe), `DMXAddress` offset, multiple DMX modes including
  "effect mode" where DMX channels drive mode/speed/intensity/palette instead
  of raw pixels [S645:wled00/e131.cpp#L96-L280]. Out-of-order frames dropped by
  8-bit sequence compare with wraparound heuristic (`seq < last && seq > 20 &&
  last < 250`) [S645:wled00/e131.cpp#L160-L164].
- **WLED UDP realtime** (port 21324): 1-byte protocol id — WARLS (index+RGB
  quads), DRGB, DRGBW, DNRGB/DNRGBW (16-bit start index)
  [S645:wled00/udp.cpp#L604-L646]. Byte 1 is the timeout in seconds. Max packet
  `UDP_IN_MAXSIZE = 1472` (one Ethernet MTU) [S645:wled00/udp.cpp#L10], so DRGB
  caps at 490 pixels/packet; multi-packet frames need DNRGB with explicit
  offsets and have **no render/push marker** — tearing between packets is
  structural.
- **TPM2.net** and **Hyperion raw RGB** (port 19446): legacy; TPM2.net assumes
  constant per-packet payload size to infer offsets [S645:wled00/udp.cpp#L569-L601].

### Per-packet cost

Every payload byte-triple goes through `setRealtimePixel(i,...)` →
`strip.setRealtimePixelColor(pix + arlsOffset, RGBW32(r,g,b,w))` — a function
call per pixel writing a uint32 into either the main segment's buffer
(`useMainSegmentOnly`) or the global frame buffer
[S645:wled00/udp.cpp#L669-L673, S645:wled00/FX_fcn.cpp#L1801-L1808]. No
memcpy fast path even for contiguous DRGB/DDP data. Rendering: E1.31/DDP set
`e131NewData`, and `handleNotifications()` shows at most once per 15 ms
(~66 fps ceiling) [S645:wled00/udp.cpp#L478-L483]; WLED-UDP and final TPM2
packets call `strip.show()` inline from the receive path. In realtime mode,
`show()` skips segment compositing entirely (frame buffer is not cleared) and
goes straight to per-pixel gamma + bus paint [S645:wled00/FX_fcn.cpp#L1752-L1783].

### Timeout / packet-loss behavior

`realtimeLock(timeoutMs, mode)` [S645:wled00/udp.cpp#L410-L440]: on entry it
clears the strip (or freezes the main segment), forces brightness on if the
strip was off, optionally forces max brightness (`arlsForceMaxBri`). Timeout
default 2500 ms (`realtimeTimeoutMs`, configurable in 100 ms units; magic
values 255001/65000 = "forever") [S645:wled00/wled.h#L451]. Each packet re-arms
the deadline; `handleNotifications()` polls `millis() > realtimeTimeout` →
`exitRealtime()` which restores the local effect state
[S645:wled00/udp.cpp#L442-L456,486]. Consequence of pure UDP + last-write-wins:
a lost packet leaves the previous frame's pixels in that region (frame buffer
persists in realtime mode); a lost stream leaves the last frame lit for 2.5 s
then snaps back to the local effect. There is no ACK, no retransmit, no
interpolation, and no frame-complete signal except DDP PUSH.

### Realistic scale

`MAX_LEDS` is 16384 on ESP32-class, 1536 (ESP8266)/2048 (S2) on small targets
[S645:wled00/const.h#L545-L549], `MAX_LEDS_PER_BUS` 2048
[S645:wled00/const.h#L575]. Practical streaming rates are set by (a) the 15 ms
show throttle, (b) WS2812 wire time (~30 µs/LED per bus — 800 LEDs/bus ≈ 41 fps
ceiling regardless of network), and (c) WiFi loss/jitter, which the code
handles only by dropping (sequence check) or displaying stale pixels. No
in-repo benchmark exists; realistic WiFi-vs-Ethernet fps/pixel-count numbers
need empirical sources — see Open questions.

## 3. Bus / output layer (bus_manager, NeoPixelBus, ABL)

### Architecture

`BusManager` owns a list of polymorphic `Bus` objects: `BusDigital` (clocked +
clockless LED chips via NeoPixelBus), `BusPwm` (LEDC analog channels),
`BusOnOff` (relays), `BusNetwork` (re-transmit pixels as DDP/E1.31/Art-Net to
another node — WLED can itself be a sender), `BusHub75Matrix`. `PolyBus`
(bus_wrapper.h) is a giant compile-time dispatch over ~840 `I_*` type constants
— every (chip × platform × driver-peripheral) combination is a distinct
`NeoPixelBus<Feature, Method>` template instantiation selected by a runtime
switch [S645:wled00/bus_wrapper.h#L16-L260]. This is the price of NeoPixelBus's
template design: supporting N chips on M peripherals means N×M template types
compiled in.

### Supported chips

Clockless: WS2812/WS2811 (+400 kHz variant), SK6812 RGBW, TM1814, TM1829,
TM1914, UCS8903/UCS8904 (16-bit chips, driven at 8-bit), FW1906 (RGB+CCT),
WS2805 (RGB+CCT), SM16825, APA106, GS8608, WS2812 1-channel-x3 white, WWA
[S645:wled00/const.h#L316-L337]. Clocked (2-wire): WS2801, APA102, LPD8806,
LPD6803, P9813 [S645:wled00/const.h#L349-L355]. Plus PWM 1-5ch, on/off,
HUB75, and "network" buses.

### ESP32 parallel output

Per-target channel budget in const.h [S645:wled00/const.h#L65-L101]:
classic ESP32 = 8 RMT + 8 I2S-parallel; S2 = 4 RMT + 8 (I2S0 parallel);
S3 = 4 RMT + 8 via **LCD peripheral** (I2S methods unsupported on S3, LCD
x8 always used) [S645:wled00/bus_wrapper.h#L208-L259]; C3 = 2 RMT only.
Driver choice is per-bus (`bus.driverType`): >1 I2S bus on classic
ESP32/S2 switches to the x8 parallel method, where all 8 outputs share one
DMA-fed peripheral and must be padded to the longest strip (memory estimated in
`finalizeInit()` [S645:wled00/FX_fcn.cpp#L1209-L1245]). RMT on recent IDF uses
`NeoEsp32RmtHIMethod` (high-priority interrupt) to fight flicker under WiFi
load.

### Per-pixel paint cost (BusDigital::setPixelColor)

Every pixel, every frame goes through: CCT color correction
(`colorBalanceFromKelvin`) → auto-white calc (RGBW modes: subtract/max/dual)
→ `color_fade(c, _bri)` global-brightness scaling (**brightness is baked into
the 8-bit bus buffer**, not applied in hardware) → ABL color-sum accumulation →
reverse/skip/color-order lookup → `PolyBus::setPixelColor`
[S645:wled00/bus_manager.cpp#L270-L309]. `getPixelColor` returns
`restoreColorLossy(raw, _NPBbri)` — un-scaling the brightness with rounding
loss; WLED explicitly accepts read-back error [S645:wled00/bus_manager.cpp#L312-L317].

### Auto brightness limiter (ABL)

Three-phase estimate-then-clamp, excerpted in
`research/excerpts/S645-abl-power-limiter/` [S645:wled00/bus_manager.cpp#L183-L253]:

1. **Accumulate**: `setPixelColor` sums post-brightness R+G+B+W into
   `_colorSum` per bus.
2. **Estimate**: `estimateCurrent()` → `mA = colorSum * mAPerLed /
   (3*255 or 4*255) + length` (1 mA/LED standby). Sentinel `mAPerLed == 255`
   selects the "wacky WS2815 model": max(R,G,B) per pixel at 12 mA
   (constant-current chip, one channel at a time; issue #549).
3. **Clamp**: `applyBriLimit()` — if estimate > limit, compute `newBri =
   limit*255/total + 1` and **rewrite every pixel in the bus buffer** with
   `color_fade(c, newBri)` (a full read-modify-write pass over the bus).
   The residual scale is stored in `_NPBbri` so `getPixelColor` can undo it.

Honest caveats are in the comments: "It is NOT a measurement and NOT guaranteed
to stay within the ablMilliampsMax margin."
[S645:wled00/bus_manager.cpp#L183-L186] The estimate ignores gamma already
applied, voltage drop, and per-chip datasheet variance; it is a linear model
with a user-set mA/LED (default 55 mA for WS2812 class).

## 4. Precision: 8-bit pipeline, dithering, gamma

**Confirmed: 8 bits per channel at every stage.** The full chain:

1. Effects compute 8-bit RGBW packed in `uint32_t` (`RGBW32`), write into the
   per-segment `uint32_t` buffer [S645:wled00/FX.h#L472,537].
2. Palette sampling: FastLED `ColorFromPalette` on `CRGBPalette16`, 8-bit in,
   8-bit out [S645:wled00/FX_fcn.cpp#L1166-L1187]. Transition progress is
   16-bit (`color_blend16`), but operands and results are 8-bit.
3. Segment compositing: 8-bit blend-mode math into the 8-bit global frame
   buffer [S645:wled00/FX_fcn.cpp#L1388-L1443].
4. Gamma: single shared 256-entry 8-bit→8-bit LUT, default gamma 2.2
   (`gammaCorrectVal`, on by default for colors, off for brightness)
   [S645:wled00/wled.h#L412-L414], recomputed at runtime by
   `NeoGammaWLEDMethod::calcGammaTable()`
   [S645:wled00/colors.cpp#L647-L662]. An inverse LUT (`gammaT_inv`, built
   with a −0.5 bias for round-trip stability) is used to pre-invert segment
   opacity so opacity scaling composes correctly with gamma (issue #5343)
   [S645:wled00/FX_fcn.cpp#L1455]. Applied once per pixel in `show()` — 8-bit
   in, 8-bit out, so a 2.2 LUT collapses 256 input codes to ~180 distinct
   outputs and the bottom ~13 inputs map to 0.
5. Global brightness: `color_fade(c, _bri)` **after** gamma, inside
   `BusDigital::setPixelColor` (comment: "applying gamma after brightness has
   too much color loss" [S645:wled00/FX_fcn.cpp#L1781]) — still 8-bit, so at
   bri=32 the whole pipeline has ~5.3 effective bits per channel.
6. Bus buffer and wire: NeoPixelBus 8-bit buffer; 16-bit-capable chips
   (UCS8903/04) are fed 8-bit values shifted up.

**Temporal dithering: none for addressable LEDs.** Issue #2416 (feature
request for FastLED-style temporal dithering, 2021) was never implemented; at
this HEAD the only dithering in the tree is for **PWM/analog buses**: LEDC
runs at 8-bit hardware resolution with 4 fractional bits, giving 12-bit
effective duty via hardware dither (PR #4115, credited to @dedehai and
@zalatnaicsongor) [S645:wled00/bus_manager.cpp#L422-L455,530-L585]. PWM
brightness also gets a CIE-lightness curve (linear below 21/255, cubic above)
computed at up-to-14-bit PWM resolution — the one place WLED exceeds 8 bits
[S645:wled00/bus_manager.cpp#L546-L555]. Contrast: FastLED's 5-bit APA102 HD
gamma + binary dithering [S615]; Fadecandy's 16-bit interpolation + dither
[S600]. WLED's low-brightness rendering is visibly stepped by comparison —
this is the strongest quality argument for pewpew keeping its own renderer and
using WLED only as a dumb receiver (and even then, WLED re-gammas and re-scales
incoming realtime data unless `arlsDisableGammaCorrection`/`arlsForceMaxBri`
are set appropriately [S645:wled00/FX_fcn.cpp#L1770]).

## 5. Sync protocol + JSON/WebSocket API (control-plane interop)

### UDP sync ("WLED notifier", port 21324, packet byte0 = 0)

Hand-rolled binary struct, `notify()` [S645:wled00/udp.cpp#L20-L151]:
41-byte global header (callMode, bri, primary/secondary/tertiary RGBW colors,
nightlight, main-segment mode/speed/intensity/palette, 16-bit transitionDelay,
32-bit effect timebase `millis()+strip.timebase`, time source + 32-bit unix +
16-bit ms system-time sync, syncGroups bitmask, CCT) followed by
`nSegments × 36-byte` per-segment records (bounds, grouping/spacing/offset,
options bits, opacity, mode/speed/intensity/palette, 3× RGBW colors, cct,
2D bounds, custom sliders/checks). Byte 11 is a **compatibility version**
(currently 12) with 12 documented historical layouts; the receiver
(`parseNotifyPacket`) gates every field group on `version > N`
[S645:wled00/udp.cpp#L212-L255]. Retransmit: same packet re-sent after 250 ms
up to `udpNumRetries` (fire-and-forget reliability)
[S645:wled00/udp.cpp#L474-L476]. Also shipped over ESP-NOW in fragmented
'W'-tagged packets [S645:wled00/udp.cpp#L152-L169]. Receivers apply granular
filters (receiveNotificationBrightness/Color/Effects/SegmentOptions/Bounds).
The design lesson: an unversioned-schema binary blob accreted 12 versions of
appendix fields and can never be refactored; every field is main-segment-biased
because segments were bolted on later.

### JSON API (HTTP `/json`, same schema over WebSocket `/ws`)

- `/json/state` ↔ `serializeState`/`deserializeState`
  [S645:wled00/json.cpp#L370,647]: `{on, bri, transition, ps/pl (presets),
  nl (nightlight), udpn (sync send/recv), lor (live override), mainseg,
  seg:[{id,start,stop,startY,stopY,grp,spc,of,col[[r,g,b,w]×3],fx,sx,ix,pal,
  c1,c2,c3,o1,o2,o3,sel,rev,mi,on,bri,cct,set,n(ame),...}]}` — the seg object
  is a 1:1 JSON projection of the Segment class, UI knobs included.
- `/json/info` — version, ledcount, fps, RAM, WiFi; `/json/effects`,
  `/json/palettes` — name arrays where the *index* is the wire ID (effect ids
  are array positions; custom builds shift nothing because unused slots keep
  reserved names).
- WebSocket: send `{"v":true}` → full state+info push on every change;
  `{"lv":true}` subscribes to **live preview**: binary frames tagged 'L'
  (v1 1D / v2 2D with w,h header), RGB truncated to ≤1024 LEDs by serving
  every n-th pixel, W folded in with `qadd8` [S645:wled00/ws.cpp#L186-L243].
  One live client at a time (`wsLiveClientId`).
- Same JSON accepted over UDP port 21324 (byte0 = '{') and MQTT — the state
  schema is the real control-plane contract, transport-agnostic.

For pewpew interop: `deserializeState` is the stable, documented (kno.wled.ge)
entry point — presets, playlists, per-segment addressing all reachable; the
UDP notifier should be treated as WLED-internal and not implemented.

## 6. WLED-MM (MoonModules) diff — doc-level

- repo: https://github.com/MoonModules/WLED-MM, pinned
  MoonModules/WLED-MM@7c55f91f1aecca548a63582e25934fdb0b7f6988 (branch `mdev`,
  tag `nightly`, 2026-07-01) [S646], EUPL v1.2, accessed 2026-07-03.

MM is a fork of WLED **v0.14** by the former SoundReactive (Atuline/WLED) team
[S646:readme.md#L16-L18]; it tracks its own `mdev` line and has NOT absorbed
upstream's post-0.15 per-segment-buffer/blend-mode renderer (its FX_fcn.cpp is
the 0.14-era direct-render design; FX.cpp 12,452 lines).

Key deltas at these pins:

- **Audioreactive architecture**: the audio pipeline lives in an external
  PlatformIO library `wled-audioreactive` (include path injected in
  platformio.ini, plus a build-script patch)
  [S646:platformio.ini#L1216,248]. Effects consume audio via the generic
  usermod data-exchange: `usermod->getUMData(um_data_t**)` returns a pointer
  table (volumeSmth, volumeRaw, fftResult[16 GEQ bins], FFT_MajorPeak, etc.)
  [S646:wled00/fcn_declare.h#L343-L400]. This same mechanism and the
  audioreactive usermod itself have since been **upstreamed**: mainline WLED at
  [S645] ships `usermods/audioreactive/` (ArduinoFFT float path on
  ESP32/S3, integer esp-dsp path on S2/C3, AGC presets, I2S mic sources)
  [S645:usermods/audioreactive/audio_reactive.cpp#L27-L35,94-L99] and the
  identical `um_data_t` contract [S645:wled00/fcn_declare.h#L351-L400]. So
  "audioreactive" is no longer an MM differentiator — MM's remaining edge is
  tuning, extra AR effects, and 8266 support work.
- **Parallel output**: contrary to MM's historical reputation, at these pins it
  is **upstream** that has the wider parallel story (x8 I2S on ESP32/S2, x8
  LCD on S3 [S645:wled00/bus_wrapper.h#L208-L259]); MM's bus_wrapper still
  offers single I2S0/I2S1 + RMT methods and explicitly marks S3 I2S
  "not supported yet" [S646:wled00/bus_wrapper.h#L7-L17]. MM instead invests
  in **HUB75 panel** output via ESP32-HUB75-MatrixPanel-DMA (dedicated build
  envs, S3 LCD clock-divider workarounds) [S646:platformio.ini#L79-L89,1238].
- **Brightness handling**: MM uses NeoPixelBus's `NeoPixelBusLg` (luminance +
  gamma template layer) [S646:wled00/bus_wrapper.h#L200-L202] where upstream
  bakes brightness into the buffer itself — same 8-bit result, different
  plumbing.
- MM raises some limits (e.g. `MAX_LEDS 8464` "92x92" on classic ESP32
  [S646:wled00/const.h#L429-L435]) and carries many more usermods in-tree.

Takeaway for pewpew: MM's lasting contribution is the audio pipeline + the
`um_data_t` producer/consumer pattern, both now in mainline; treat MM as a
0.14-era side branch, not a target platform.

## What pewpew should steal

1. **DDP as the render-tier wire protocol.** channelOffset addressing +
   PUSH-flag frame commit + tiny 10-byte header + RGB/RGBW typing is exactly
   the right shape for streaming to receivers, and every WLED node already
   speaks it [S645:wled00/e131.cpp#L20-L93] (excerpt: S645-ddp-ingest). Add
   what DDP-in-WLED lacks: a real frame sequence number and receiver-side
   frame-completeness handling.
2. **Realtime-lock semantics**: streaming preempts local effects, every packet
   re-arms a timeout (default 2.5 s), on timeout the node falls back to its
   local state [S645:wled00/udp.cpp#L410-L456]. This makes receivers
   self-healing when the show controller dies — pewpew should keep this
   contract when driving WLED and replicate it in any native receiver.
3. **ABL power limiting** as a receiver-side safety net: sum post-brightness
   channel values, linear mA model + per-LED standby current, clamp by
   rescaling the frame [S645:wled00/bus_manager.cpp#L183-L253] (excerpt:
   S645-abl-power-limiter). The WS2815 max(R,G,B) special case is a good
   reminder that the power model is per-chip-family. Pewpew should compute the
   limit in the renderer *before* quantization instead of rewriting an 8-bit
   buffer.
4. **Inverse-gamma-corrected opacity** (gammaT_inv applied to brightness so
   opacity scaling composes with gamma, issue #5343)
   [S645:wled00/FX_fcn.cpp#L1455, S645:wled00/colors.cpp#L647-L683] — a subtle
   correctness detail worth carrying into any pipeline that gammas before
   scaling.
5. **JSON state schema + per-index effect/palette name arrays** for
   control-plane interop: one transport-agnostic document over HTTP, WS, UDP
   and MQTT is genuinely convenient; the WS binary 'L' live-preview channel
   (decimate to ≤1024 px) is a cheap, effective monitoring pattern
   [S645:wled00/ws.cpp#L186-L243].
6. **um_data_t producer/consumer** pattern for audio → effects decoupling
   [S645:wled00/fcn_declare.h#L351-L400] — a primitive plugin bus, but the
   right idea: effects declare data needs, providers fill a typed pointer
   table.

## What to avoid

1. **The God-object Segment.** Geometry + UI + effect params + runtime scratch
   + pixel buffer + transition copy in one 76-byte-header class with
   `mutable` members and static side-channels [S645:wled00/FX.h#L419-L530].
   Every subsystem (JSON, UDP sync, effects, compositor) reaches into it
   directly; the UDP sync packet is literally a field-order dump of it.
   Separate scene description from render state from transport encoding.
2. **Effects as void() globals communicating via macros over statics.**
   Untestable, unschedulable, fork-to-extend, single-threaded by construction
   [S645:wled00/FX.h#L106-L113,815]. Pewpew's effect contract should be a pure
   function of (time, params, geometry) → buffer with explicit arguments.
3. **8-bit end-to-end with no temporal dithering** (issue #2416 unresolved
   since 2021): gamma LUT 8→8 then brightness scaling 8→8 leaves ~5 effective
   bits at typical indoor brightness — see §4. Render in ≥16-bit, quantize
   with dithering at the very last stage (FastLED [S615] and Fadecandy [S600]
   both prove this out).
4. **Transition-by-copying-the-world**: cloning the whole Segment (including
   pixel buffer) and running both effects every frame doubles CPU/RAM at
   exactly the wrong moment [S645:wled00/FX_fcn.cpp#L1330-L1367]. Crossfade
   *frames* (two buffers, one blend) rather than *engines*.
5. **N×M template explosion** (~840 `I_*` constants in bus_wrapper.h) from
   binding chip timing into peripheral driver types at compile time
   [S645:wled00/bus_wrapper.h]. Keep chip encoding (bit timings, color order,
   bit depth) as data, peripherals as a small driver interface.
6. **Unversioned-schema accretion**: the notifier packet's 12 compatibility
   layers [S645:wled00/udp.cpp#L54-L60] and effect-IDs-as-array-indexes both
   make every published constant permanent. Version envelopes and stable IDs
   from day one.
7. **Per-pixel function-call paint path**: pixel index mapping, CCT
   correction, white calc, brightness, color order — all re-decided per pixel
   per frame in `show()`/`BusDigital::setPixelColor`
   [S645:wled00/FX_fcn.cpp#L1772-L1783, S645:wled00/bus_manager.cpp#L270-L309]
   instead of precompiled per-strip transforms.

## Open questions

- **Empirical WiFi vs Ethernet throughput**: no benchmarks in-repo; the 15 ms
  show throttle and WS2812 wire time bound fps from above, but real packet-loss
  rates for E1.31/DDP over ESP32 WiFi at 4-10 universes need measurement or an
  external source (kno.wled.ge gives guidance but no data). Not verified here.
- **PSRAM pixel-buffer cost**: comment claims <2% FPS impact with QSPI PSRAM
  [S645:wled00/FX.h#L599] — unverified, and octal-PSRAM S3 boards may differ.
- **`prevRays` static in `setPixelColor` pinwheel path**
  [S645:wled00/FX_fcn.cpp#L833] is function-static shared across segments —
  looks like a cross-segment rendering bug waiting to happen; undocumented.
- **WLED-MM parallel/virtual drivers**: MM's reputation for 16+ way parallel
  output (Yves Bazin-style I2S drivers) is not present at the pinned mdev
  HEAD; whether it lives in a separate MM branch/usermod was not established
  (doc-level review only).
- **DDP timecode**: WLED parses but ignores the DDP TIME flag
  [S645:wled00/e131.cpp#L63]; no latency-compensation hook exists on the
  receiver — pewpew would need firmware changes for synced multi-node frames
  beyond "render on PUSH arrival".
- (Resolved during review) double-gamma risk for a pewpew sender: stock WLED
  defaults `arlsDisableGammaCorrection = true` and `arlsForceMaxBri = false`
  [S645:wled00/wled.h#L453-L454], so realtime data is NOT re-gammaed by
  default but IS still scaled by the node's master brightness — pewpew must
  either pin receiver bri=255 or account for it.
