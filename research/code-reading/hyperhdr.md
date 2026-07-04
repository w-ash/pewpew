# Code reading: HyperHDR "Infinite Color Engine"

- repo: https://github.com/awawa-dev/HyperHDR [S700]
- pinned: awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584 (master, 2026; = v22.0.0.0beta2 tag a6fa8a2d… + smoothing drift fix #1561)
- license: MIT (Copyright (c) 2020-2026 awawa-dev)
- accessed: 2026-07-03
- scope: float linear-sRGB pipeline, adaptive temporal dithering, deep-color/HD108 output, output scheduling, portability to a Python/NumPy engine

## 1. Color pipeline: where float/linear happens, LUTs, quantization

### Note on branches

Master at the pinned sha IS the Infinite Color Engine: tag `v22.0.0.0beta2`
(`a6fa8a2d…`) plus one commit ("Fix smoothing algorithm drift in long-running
sessions (#1561)") that touched the interpolators. No separate beta branch
exists; the engine lives in `sources/infinite-color-engine/` and
`sources/led-drivers/InfiniteColorEngineRgbw.cpp` [S700].

### Entry: capture → linear float at the averaging step

Linearization happens at the earliest possible moment — inside per-LED image
averaging. Each 8-bit sRGB pixel is looked up in a 256-entry
`uint8 → linear uint16` LUT (`_srgb_uint8_to_linear_uint16_lut`, exact
sRGB EOTF with the 0.04045/12.92 linear toe, scaled to 0..65535 with +0.5
rounding) [S700:include/infinite-color-engine/InfiniteProcessing.h#L229-L242].
The averaging accumulates those uint16 linear values into a
`uint_fast64_t` 3-vector — i.e. the mean over a LED's pixel zone is computed
in LINEAR light using integer accumulation (no float rounding per pixel),
then divided once and normalized by 65535 to a `float3` in 0..1
[S700:sources/base/ImageColorAveraging.cpp#L216-L258]. This is the classic
"average in linear, not gamma" fix, done with a LUT so it costs one table
lookup per pixel.

From that point on, the whole per-frame representation is
`std::vector<linalg::vec<float,3>>` (`float3`), shared between stages as
`SharedOutputColors = std::shared_ptr<std::vector<float3>>`
[S700:include/infinite-color-engine/SharedOutputColors.h#L49].

### Processing chain (InfiniteProcessing::applyyAllProcessingSteps)

Per frame, per LED, in this exact order
[S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L181-L238]:

1. **Temperature** — multiply by an RGB tint (`Warm = {1, .93, .85}`,
   `Cold = {.9, .95, 1}`, or custom), clamp 0..1. LINEAR space.
2. **Colorspace calibration** — two modes
   [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L297-L474]:
   - *Matrix* (primaries only): 3x3 matrix whose columns are the measured
     R/G/B primaries (as float3/255), applied by `linalg::mul`, clamp.
   - *LUT* (8-point RGBCMYK+W+B): a **9×9×9 float3 LUT** (LUT_DIMENSION=9)
     built by trilinear interpolation of the 8 measured corner colors over
     the RGB cube, then sampled at runtime with trilinear interpolation.
     Both build and lookup are plain lerps — no matrix solve.
   LINEAR space.
3. **Scale output** — scalar multiply 0..2, clamp. LINEAR.
4. **Linear → nonlinear sRGB** via a 512-entry float LUT
   (`_linear_to_srgb_lut`, LUT_SIZE=512) with linear interpolation between
   entries [S700:include/infinite-color-engine/InfiniteProcessing.h#L140-L155,
   #L216-L227]. Everything downstream of this point (user gamma, smoothing,
   dithering, quantization) operates on **nonlinear (gamma-encoded) float
   0..1**.
5. **User gamma** — `pow(x, gamma)` via a 512-entry LUT rebuilt on config
   change, lerp between entries (default gamma 1.5)
   [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L476-L517].
6. **Brightness/saturation** — RGB→HSV, scale V and S, HSV→RGB, clamp
   [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L586-L600].
7. **Minimal backlight** — floor each channel (colored) or replace with grey
   floor if the average is below threshold.
8. **Power limit** (whole frame, not per LED) — sum all channels; if above
   `ledCount*3*limit`, scale every LED by the ratio
   [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L646-L663].
9. **Color-order swizzle** (RGB→GRB etc.) done here in float, EXCEPT when the
   RGBW dithering engine is enabled — then the mixer stays RGB and the
   swizzle happens after white extraction in the driver
   [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L163-L179].

Precision summary: 8-bit sRGB in → uint16 linear (LUT) → uint64 integer
accumulate → float32 linear → float32 processing → float32 nonlinear sRGB →
(smoothing in float32) → quantization only at the driver.

Config snapshotting: calibration state is an immutable
`shared_ptr<CalibrationSnapshot>` swapped atomically on config change, so
the render path reads it lock-free
[S700:include/infinite-color-engine/InfiniteProcessing.h#L28-L55].

### LUT structure/precision recap

| LUT | size | in → out | interp |
|---|---|---|---|
| sRGB decode (int path) | 256 | uint8 sRGB → uint16 linear | exact (table is the function) |
| sRGB decode (float path) | 512 | float sRGB → float linear | lerp |
| sRGB encode | 512 | float linear → float sRGB | lerp |
| user gamma | 512 | float → float | lerp |
| color calibration | 9×9×9 float3 | RGB cube → RGB | trilinear |

All computed at startup/config-time (`make_lut` constexpr generator)
[S700:include/infinite-color-engine/InfiniteProcessing.h#L192-L242].

### Where quantization happens

Never in the engine. Colors stay float3 through smoothing and are handed to
`LedDevice::write(SharedOutputColors)`. Each driver either:

- implements `writeInfiniteColors()` (the "deep color" path) and quantizes
  itself — to 16-bit (HD108), to 8-bit-with-temporal-dithering (RGBW engine),
  or to whatever the protocol wants; or
- falls back to the "finity" path: `round(v*255)` per channel, with an
  optional **anti-flicker filter**: a stored last-quantized-input per LED is
  only updated when the new float value differs by more than 0.49/255 —
  i.e. sub-half-LSB float jitter cannot toggle the 8-bit output
  [S700:sources/led-drivers/LedDevice.cpp#L625-L678]. If a driver supports
  deep color, the anti-flicker filter is auto-disabled with a log message
  (it exists only to hide 8-bit quantization noise).

## 2. Adaptive temporal dithering (incl. v22beta2 static-scene stabilization)

The dithering lives in ONE place: `InfiniteColorEngineRgbw` — the RGBW
white-mixing encoder used by 8-bit RGBW-capable drivers (SK6812, DDP, ArtNet,
Adalight, rpi PWM/PIO, HyperSPI, file) when the user enables `enable_ice_rgbw`
[S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp]. HD108 does NOT
dither — at 16 bits it just rounds. So "adaptive temporal dithering" in
HyperHDR = a way to get >8-bit effective depth out of 8-bit LEDs, gated by
motion detection.

### Algorithm (per LED, per output frame)

State per LED: `last_input` (float3), `error` (float3 accumulator in 0..255
units), `flow_control` (int8 sign of last dominant change),
`last_sent_bytes` (byte4) [S700:include/led-drivers/InfiniteColorEngineRgbw.h#L9-L14].

`encodeRgbwFrame()` [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L80-L156]:

1. **Static-scene stabilization (the v22beta2 fix):** if the incoming float3
   is *bitwise equal* to `last_input`, zero the error accumulator and resend
   the exact previous bytes. A static scene therefore produces a rock-solid,
   completely non-shimmering output — dithering only ever runs while the
   input is actually changing. (This is the key anti-shimmer decision:
   HyperHDR chose "no dithering when static" over "keep dithering carefully".)
2. **Near-black cutoff:** if `max(rgb) < 0.5/255`, reset all state and
   resend previous bytes (prevents dither sparkle at black).
3. **Motion/direction gate:** compute `diff = new - last_input`; find the
   channel with the largest |diff|; take its sign as `newFlow`. Dithering is
   enabled only if (a) the sign matches the previous frame's sign
   (`std::exchange(state.flow_control, newFlow) == newFlow`) — i.e. the value
   is moving monotonically, not oscillating — AND (b) |diff| of the dominant
   channel ≥ a motion threshold (0.01/255, scaled down proportionally when
   the output interval is < 17 ms)
   [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L63-L65]
   [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L97-L101]. Direction reversals
   (which is what noisy oscillating inputs look like) get NO error carry,
   killing feedback shimmer.
4. **Error feedback:** `input255 = rgb*255 + error` (only if dithering
   enabled). Then RGBW white extraction (below), then
   `target_rounded = clamp(round(target4), 0, 255)`.
5. **Leaky error accumulator:** the new error is
   `(target - rounded) * leak`, where
   `leak = lerp(0.96, 0.80, clamp(|diff|² * 50, 0, 1))`
   [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L121-L127] —
   slow fades keep 96% of the quantization error (high effective depth
   where it matters), fast motion keeps only 80% (error is pointless and
   riskier during motion). This is a **temporal error-diffusion per LED**
   (Floyd–Steinberg in time, not space), NOT blue-noise and NOT a spatial
   kernel. The white (W) channel error is not carried — only RGB.

So "adaptive" = three separate adaptations: (a) dithering on/off by
static-scene detection + monotonic-motion gate, (b) motion threshold scaled
by output interval, (c) error-leak factor scaled by motion magnitude.

### RGBW white mixing (same function)

`common = min(rgb*255)` (optionally weighted by a white-point RGB for
custom white temperature); a soft threshold ramp
`w_factor = clamp((common - thr255)/(255 - thr255), 0, 1)` decides how much
of the common grey goes to W; `w = round(common*w_factor / whiteIntensity)`;
the RGB channels get `w*whiteIntensity` (times white point) subtracted
[S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L104-L117]. The
rounding error of both W and RGB flows into the same
temporal dither accumulator (via target4 vs target_rounded), so W-channel
quantization is also temporally smoothed indirectly through RGB.

### Refresh-rate requirements

The dithering runs at the LED output rate (`_currentInterval`, from the
smoothing config's update frequency — default 25 Hz, floor 20 Hz, cap
200 Hz; see section 4). There is no separate high-frequency dither clock:
temporal dithering happens once per output frame. The interval-aware motion
threshold (`currentInterval < 17 ms` ⇒ scale threshold by interval/17)
exists precisely so behavior stays consistent between ~60 Hz and ~25 Hz
output [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L63-L65].
Practical implication: effective extra bit depth is
bounded by output Hz vs. eye integration; HyperHDR accepts this and uses
dithering mainly to smooth slow fades (where 8-bit steps are visible), not
to fake 12-bit static color.

## 3. Deep-color output path (HD108 / >8-bit sinks)

Deep color is carried as **float3 all the way into the driver** — there is no
intermediate 16-bit integer frame format. A driver opts in by overriding
`writeInfiniteColors(SharedOutputColors)` and returning `{true, bytes}`;
returning `{false, _}` falls back to the 8-bit `writeFiniteColors` path
[S700:sources/led-drivers/LedDevice.cpp#L625-L678]. Drivers overriding it at
the pin: HD108 (SPI), SK6812 (SPI RGBW), HyperSPI, Adalight (serial), DDP,
ArtNet, Lifx, Philips Hue, rpi PWM (ws281x), rpi PIO, and the file writer.

**HD108** is the only true 16-bit-per-channel sink: per LED it emits a 64-bit
frame — 16-bit level word (`0b1` start bit + three 5-bit current-gain fields,
gain from config, default max 31) followed by `round(float * 0xffff)` for
R, G, B, byte-swapped to MSB-first
[S700:sources/led-drivers/spi/DriverSpiHD108.cpp#L76-L119]. Note the floats
arriving here are **nonlinear sRGB + user gamma** — HyperHDR does not
re-linearize for the LED's native response; the 16-bit DAC resolution simply
preserves the gamma-encoded value with no visible quantization. No dithering
is applied (`renderRgbwFrame` is not used) — 16 bits is treated as enough.
HD108's 5-bit analog current gain is used as a static global brightness
limit, NOT modulated per frame (unlike FastLED's APA102 "five-bit HD gamma"
trick).

Everything else that overrides `writeInfiniteColors` is still 8-bit on the
wire but gets the RGBW white-mix + temporal dithering treatment of section 2
(SK6812, DDP, ArtNet, Adalight, HyperSPI, rpi PWM/PIO), or protocol-native
float/16-bit color models (Lifx HSBK is uint16; Philips Hue Entertainment
gets linear→xy conversion with its own gamut handling
[S700:sources/led-drivers/net/DriverNetPhilipsHue.cpp#L2178]).

The 8-bit fallback path also carries a lesson: `writeFiniteColors` +
anti-flicker hysteresis (only accept a new 8-bit value when the float moved
> 0.49 LSB) is the "cheap" alternative to dithering for sinks that shimmer
[S700:sources/led-drivers/LedDevice.cpp#L633-L658].

## 3b. Smoothing/interpolators (what actually eats capture jitter)

Between processing and output sits `InfiniteSmoothing` with six pluggable
interpolators (Stepper, Rgb, Yuv, HybridRgb, Hybrid, Exponential), selected
by config [S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L111-L147].
Data flow: capture frame → `applyyAllProcessingSteps` → `incomingColors`
sets the interpolator's *target* (mutex-protected) → the master clock tick
calls `updateLeds()` which advances the interpolator by wall-clock dt and
emits the current colors
[S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L220-L283].

The flagship `InfiniteHybridInterpolator` is a **critically-tunable
spring-damper in BT.709 YUV space**, per LED
[S700:sources/infinite-color-engine/InfiniteHybridInterpolator.cpp#L122-L185]:

- Targets converted RGB→YUV on arrival (`rgb_to_bt709`); state = current YUV
  + velocity YUV per LED.
- Each tick: `acc = stiffness*diff - damping*vel` (defaults 200/26),
  semi-implicit Euler with dt in seconds, dt clamped to 0.001..100 ms.
- Optional **per-frame luminance rate limit** (`y_limit`): if the Y component
  of the step exceeds it, the whole step AND velocity are scaled down — this
  is a flicker/strobe guard that limits brightness slew without distorting
  chroma trajectory
  [S700:sources/infinite-color-engine/InfiniteHybridInterpolator.cpp#L151-L157].
- Completion test: max |diff| < ~0.000137 AND max |vel| < 0.0005 ⇒ snap to
  target exactly and stop
  [S700:sources/infinite-color-engine/InfiniteHybridInterpolator.cpp#L133-L142].
  When complete, `getCurrentColors`
  returns the exact RGB targets (not the YUV round-trip), avoiding
  steady-state conversion error
  [S700:sources/infinite-color-engine/InfiniteHybridInterpolator.cpp#L187-L208].
- Once the animation completes and `continuousOutput` is off, output pauses
  after a 3-tick cooldown — static scenes stop producing frames entirely
  [S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L265-L282].

The single post-beta2 fix (#1561, "smoothing drift in long-running
sessions") changed interpolator timestamps from `float` ms to `long long`
ms: float32 cannot represent millisecond timestamps past ~2^24 ms (≈4.6 h
uptime), so `currentTimeMs - _lastUpdate` collapsed and animation stalled.
Subtraction now happens in int64 and only the small dt is cast to float
[S700:sources/infinite-color-engine/InfiniteHybridInterpolator.cpp#L129].
Direct lesson for pewpew: never carry absolute time in float32.

## 4. Output scheduling: refresh clock vs capture rate

Fully decoupled, with an interesting twist: **the LED device owns the master
clock, and the smoothing engine slaves to it.**

- Capture frames arrive asynchronously at whatever rate the grabber runs;
  they only ever *retarget* the interpolator (`setTargetColors`), never
  directly cause output [S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L220-L247].
- The output clock is a per-device `QTimer` with `Qt::PreciseTimer` at
  `_currentInterval` ms. When smoothing is active, the timer's timeout emits
  `SignalSmoothingClockTick`, routed (DirectConnection) through the instance
  to `InfiniteSmoothing::updateLeds`
  [S700:sources/led-drivers/LedDevice.cpp#L383-L409;
  S700:sources/led-drivers/LedDeviceWrapper.cpp#L106]. `updateLeds`
  advances the spring model by measured wall-clock dt (so timer jitter does
  not distort the animation) and emits the frame, which lands back in
  `LedDevice::handleSignalFinalOutputColorsReady` → `rewriteLEDs()` → write
  [S700:sources/led-drivers/LedDevice.cpp#L496-L589].
- Interval priority: device-forced interval (`forcedRefreshTime`, for
  protocol-limited devices) > smoothing config interval > user
  `refreshTime` [S700:sources/led-drivers/LedDevice.cpp#L437-L472]. The
  smoothing frequency defaults to 25 Hz with a floor of 20 Hz and a cap of
  5 ms per interval (=200 Hz max)
  [S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L191-L202].
- With smoothing disabled or no interval, output is event-driven: each
  incoming frame sets `_newFrame2Send` and queues a manual `rewriteLEDs`;
  a still-pending frame counts as dropped (latest-wins, no queue depth)
  [S700:sources/led-drivers/LedDevice.cpp#L537-L546].
- When the clocked animation finishes and `continuousOutput` is false,
  frames stop flowing (after 3 cooldown ticks + a 1 s resend guard), so
  idle static scenes cost zero bus traffic
  [S700:sources/infinite-color-engine/InfiniteSmoothing.cpp#L249-L283].
- The dithering encoder is told the current interval so it can normalize
  its motion threshold across refresh rates (section 2).

## What pewpew should steal (portable to Python/NumPy)

Almost everything here is math over per-LED float3 arrays — it vectorizes
trivially in NumPy. Concretely:

1. **Linearize at the source with an integer LUT, average in linear.** The
   256→uint16 sRGB decode LUT + integer accumulation
   [S700:sources/base/ImageColorAveraging.cpp#L216-L258] maps 1:1 to
   `lut[img].sum(axis=...)` in NumPy and is exactly what a Python engine
   needs for zone averaging without float-per-pixel cost.
2. **Keep everything float until the driver; drivers self-quantize.** The
   `writeInfiniteColors`-with-fallback pattern (deep-color sinks consume
   float directly; legacy sinks get round(v*255)) is a clean sink API shape
   for pewpew [S700:sources/led-drivers/LedDevice.cpp#L625-L678].
3. **The adaptive temporal dither recipe** (excerpted): per-LED float3 error
   accumulator; dither only when input is changing monotonically and above
   an interval-normalized motion threshold; freeze bytes + zero error on
   exactly-static input; leak factor 0.96→0.80 scaled by motion². All
   NumPy-friendly: `np.sign`, `np.argmax`, boolean masks, one persistent
   error array. This solves the shimmer problem that killed naive temporal
   dithering.
4. **The 0.49-LSB anti-flicker hysteresis** for non-dithered 8-bit sinks —
   two lines of NumPy (`np.where(|new-old|*255 > 0.49, new, old)`) and it
   eliminates static-scene flicker from float jitter
   [S700:sources/led-drivers/LedDevice.cpp#L640-L651].
5. **Spring-damper smoothing in YUV with Y slew limiting** and
   snap-to-exact-target on completion; semi-implicit Euler with measured dt.
   Pure array math. The "return exact RGB targets once settled" trick avoids
   both drift and round-trip error.
6. **Device-owned output clock, capture only retargets.** The scheduling
   split (interpolator target updated by capture; output frames produced by
   a fixed-rate device clock, dt measured not assumed) is the right
   architecture for pewpew's decoupled render loop, and the
   stop-output-when-settled cooldown is free efficiency.
7. **Immutable config snapshots** (`shared_ptr<const Snapshot>` swap) — in
   Python, an atomically-replaced frozen dataclass/arrays object serves the
   same role against a render thread.
8. **HD108 frame format** — 16-bit level word + 3×16-bit big-endian channels;
   send gamma-encoded values scaled by 0xffff; keep the 5-bit current gain
   static [S700:sources/led-drivers/spi/DriverSpiHD108.cpp#L76-L119].
9. **int64 milliseconds for all timestamps** (the #1561 drift bug): float32
   time breaks after ~4.6 h. In NumPy terms: keep clocks as int64 ns/ms,
   cast only dt to float.

C++-only / non-portable bits: the Qt signal plumbing, `Qt::PreciseTimer`
(Python needs a monotonic-clock loop with drift-compensated sleep), the
constexpr LUT generation (irrelevant — NumPy builds LUTs at import), and the
SIMD-ish `linalg` vec types (replaced by array axes).

## What to avoid

- **Per-LED scalar loops as the code structure.** HyperHDR iterates
  LED-by-LED with per-color function calls (fine in C++, fatal in Python).
  Port the math, not the loop shape — every stage must become whole-array
  ops.
- **Order-of-operations wart:** user gamma, brightness/saturation (HSV), and
  the backlight floor run in *nonlinear* space after the linear stages, and
  smoothing interpolates gamma-encoded values converted to YUV — the
  "linear pipeline" is only linear up to the encode step
  [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L181-L199].
  Perceptually defensible for ambient light, but pewpew should decide its
  spaces deliberately rather than copy this hybrid.
- **The power limiter runs on gamma-encoded values**
  [S700:sources/infinite-color-engine/InfiniteProcessing.cpp#L646-L663] —
  channel sum of sRGB-encoded values is a poor proxy for LED current (which
  is ~linear in duty cycle). A real current limiter should work on linear
  values.
- **No spatial dithering at all** — HyperHDR's LEDs are behind a TV so
  neighboring-LED correlation doesn't matter; for direct-view pewpew
  fixtures, purely temporal per-LED dithering at 25-60 Hz may be visible;
  don't assume this closes the question of blue-noise/spatial distribution.
- **Dithering capped at output frame rate** with no high-rate modulation:
  at HyperHDR's default 25 Hz the temporal dither is really a slow-fade
  de-banding tool. pewpew targets higher output rates; don't copy the 25 Hz
  default.
- **Bitwise float equality as the static-scene test**
  [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L86-L89] works only
  because upstream stops producing new frames when settled (the interpolator
  snaps to exact targets). If pewpew's generator emits fresh floats each
  frame, this gate never triggers — an epsilon or an explicit "scene
  settled" signal is needed instead.
- Typo-level API noise (`applyyAllProcessingSteps`, Polish comments) — the
  codebase is one maintainer's; treat it as a reference implementation, not
  a dependency.

## Open questions

- **Effective bit depth achieved:** no measurement or documentation in-repo
  of how many extra bits the temporal dither buys at 25/60 Hz; the leak
  constants (0.96/0.80), motion threshold (0.01/255), and the `*50`
  motion-to-leak scaling are magic numbers with no derivation or comment.
- **Why W-channel error is not carried** in the RGBW dither accumulator
  (state.error is float3; target4.w's rounding error is dropped) — deliberate
  (W rounding folds into RGB next frame) or oversight? Undocumented.
- **Interaction of dithering with the anti-flicker filter** when a driver
  supports both paths: writeInfiniteColors wins and the filter is force-
  disabled, but only after a frame arrives — startup ordering unverified.
- **HD108 gamma handling:** sending gamma-encoded (sRGB+user-gamma) floats
  scaled to 16 bits assumes the HD108 PWM is linear and the encoded curve is
  the desired light response. No calibration against the chip's actual PWM
  curve exists in-repo.
- The HDR/LUT subsystem (`lut-calibrator/`, 3D LUT files for HDR grabbers)
  was out of scope here; it precedes the engine (operates on video frames,
  not LED colors) and deserves its own read if pewpew ever ingests HDR
  video.
- Whether `SignalSmoothingClockTick` DirectConnection means the interpolator
  runs on the device thread (it appears so — the timer fires in the device
  thread and DirectConnection executes updateLeds there), making
  `_dataSynchro` the only guard between capture and output threads;
  not traced exhaustively.
