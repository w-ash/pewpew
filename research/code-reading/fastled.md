# Code reading: FastLED

- repo: https://github.com/FastLED/FastLED [S008]
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e (master, 2026-07-02;
  `FASTLED_VERSION 3010004` with release_notes.md marking 3.10.4 "Next Release" — i.e. this
  pin is unreleased 3.10.4-dev; seed [S008]'s "v3.10.5" claim does not match this tree)
- deep-dive source entry: [S615] (see `research/sources/_fragments/code-fastled.md`)
- license: MIT (LICENSE, "Copyright (c) 2013 FastLED")
- accessed: 2026-07-03
- scope: quality machinery only (dithering, HD gamma, color correction, palettes, chipset timing) — not the Arduino API

## How it achieves its signature quality

### 1. Binary temporal dithering

**Where it lives.** Entirely in `PixelController` (the per-show pixel iterator), not in chipset
drivers: state, init, and per-pixel application are in
[S615:src/pixel_controller.h#L96-L509]. Chipset drivers only *call* the composite
`loadAndScale<SLOT>()` helpers. `EDitherMode` is a byte with exactly two values:
`DISABLE_DITHER 0x00` / `BINARY_DITHER 0x01` [S615:src/dither_mode.h#L8-L15].

**State.** Two 3-byte arrays on the controller: `d[3]` = current per-channel dither offset,
`e[3]` = max per-channel dither range ("inversely proportional to brightness")
[S615:src/pixel_controller.h#L106-L107].

**Virtual-bit budget (how many D bits).** Compile-time:
`UPDATES_PER_FULL_DITHER_CYCLE = MAX_LIKELY_UPDATE_RATE_HZ(400) / MIN_ACCEPTABLE_DITHER_RATE_HZ(50) = 8`,
and `RECOMMENDED_VIRTUAL_BITS` counts how many powers of two fit in that ratio — a chain of
`(x>1)+(x>2)+(x>4)+…` comparisons yielding **3 virtual bits** at the default 400 Hz assumption
[S615:src/pixel_controller.h#L270-L302]. The header comment is explicit that 8-bit hardware then
gives ~11-bit perceived precision, that 400 Hz is "only possible with 85 pixels or fewer" on
WS2811-family, and flags a TODO to derive bits at runtime from ms-since-last-update
[S615:src/pixel_controller.h#L253-L291]. This is the "needs high refresh" coupling: the full
dither cycle is `2^bits` frames and must complete above ~50 Hz to be invisible; below that it
reads as flicker (docs tell you to disable for cameras/slow refresh)
[S615:src/pixel_controller.h#L257-L261].

**Per-frame init — `init_binary_dithering()`** [S615:src/pixel_controller.h#L309-L363]:
1. A **`static` frame counter `R`** (static local in the header — shared across *all*
   controllers/strips in the process) increments once per PixelController construction, i.e.
   once per strip per `show()`.
2. `R &= (1<<ditherBits)-1` — wraps to an 8-frame cycle.
3. **Bit-reverse** R into Q (bit0↔bit7 …): sequence 0,1,2,…,7 becomes 0,128,64,192,32,160,96,224.
   This is the "binary" in binary dithering — a bit-reversed (van der Corput) sequence so
   successive frames are maximally spaced instead of ramping [S615:src/pixel_controller.h#L319-L333].
4. **Center**: `Q += 1 << (7-ditherBits)` (adds 16 for 3 bits) so the pattern sits mid-bin
   [S615:src/pixel_controller.h#L335-L339].
5. **Per-channel scaling against brightness** — the key precision trick: for each channel i,
   `s = mColorAdjustment.premixed.raw[i]` (NB: this is brightness *premixed with* color
   correction and temperature, not raw master brightness), then
   `e[i] = s ? (256/s)+1 : 0` and `d[i] = scale8(Q, e[i])`; with `FASTLED_SCALE8_FIXED` a
   nonzero `d[i]` is decremented once, and `e[i]` is decremented for the toggle step
   [S615:src/pixel_controller.h#L341-L361]. So at premixed scale 255, e≈1 (almost no dither);
   at scale 51 (20%), e≈6 → offsets up to ~5 counts, exactly the size of one quantization bin
   at that brightness.

**Per-pixel application.** The pipeline is strictly **load → add dither → scale**:
`loadAndScale<SLOT>() = scale8(qadd8(byte, d[channel]), premixed[channel])`, with the rule that
**black is never dithered** (`b ? qadd8(b,d) : 0`) so idle pixels stay off
[S615:src/pixel_controller.h#L426-L474]. Between pixels, `stepDithering()` flips
`d[i] = e[i] - d[i]` — a two-phase spatial toggle so adjacent pixels round in opposite
directions within the same frame, hiding the temporal pattern spatially
[S615:src/pixel_controller.h#L396-L404]. Chipsets that pre-emit byte 0 call
`preStepFirstByteDithering()` to keep channel-0 phase aligned [S615:src/pixel_controller.h#L406-L409].

**Interaction with brightness scaling.** Because dither is added *before* `scale8` by the
premixed factor, the added noise (up to ~one output quantum / premixed-scale) causes the
truncating scale to alternate between adjacent output codes at exactly the duty cycle of the
lost fractional bits. `scale8(i, s) = (i*(s+1))>>8` in the default `FASTLED_SCALE8_FIXED=1`
build [S615:src/platforms/shared/scale8.h#L26-L32] — pure truncation, no rounding; dithering is
what recovers the truncated fraction over time. Disabling dithering just zeroes d[] and e[]
[S615:src/pixel_controller.h#L372-L379].

Excerpt: `research/excerpts/S615-binary-dither/pixel_controller.h`.

### 2. five_bit_hd_gamma — APA102HD pseudo-13-bit pipeline

**The idea.** APA102-class chips take 8-bit RGB PWM *plus* a 5-bit per-pixel "global
brightness" (a higher-frequency current/duty control). FastLED's HD mode does gamma in 16-bit,
then re-splits each pixel into (8-bit RGB × 5-bit brightness) so dark pixels use a small 5-bit
scale and keep most of their 8 RGB bits — ~`255×31 = 7905` distinguishable levels per channel
(log2 ≈ 12.9, the "pseudo-13-bit"). Implementation:
[S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L36-L130]; API in
[S615:src/fl/gfx/five_bit_hd_gamma.h#L14-L34] (output either as split spans or packed 4-byte
`CRGBA5 {CRGB color; u8 brightness_5bit;}`).

**Stage-by-stage precision** (per pixel; uniform factors precomputed per frame):
1. **8→16-bit gamma**: `r16 = GAMMA_2_8_LUT[c.r]` — a 256-entry u16 LUT generated as
   `round(pow(i/255, 2.8) * 65535)` [S615:src/fl/math/ease.cpp.hpp#L22-L25]. Entries 0–3 are 0;
   LUT[255]=65535.
2. **Color correction in 16-bit**: `r16 = (r16 * (colors_scale.r + 1)) >> 8` (branchless
   `scale16by8_nozero`, skipped when the scale channel is 0xff)
   [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L27-L32]. `colors_scale` is the
   *full-brightness* correction×temperature product (the `ColorAdjustment.color` field kept
   separate under `FASTLED_HD_COLOR_MIXING`), NOT the brightness-premixed scale.
3. **Global brightness in 16-bit**: same `(x * (brightness+1)) >> 8` multiply
   [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L49-L54].
4. **Joint quantization**: `scale = max(r16,g16,b16)`, then
   `S = (scale + (2047 - (scale >> 5))) >> 11`
   [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L56-L68]. Verified numerically: this is exactly
   `S = ceil(max16 * 31 / 65536)` for all 1..65535 — the smallest 5-bit brightness whose full
   range covers the max component (so no channel clips).
5. **Renormalize RGB against the chosen S**: `r8 = (r16 * BRIGHT_SCALE[S] + 0x808000) >> 24`
   where `BRIGHT_SCALE[ix] = 31*255*256/ix = 2023680/ix` (u32 table, truncated)
   [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L13-L19]. I.e.
   `r8 = round(r16 * (31/S) * (255/65536))`. **Rounding constant `0x808000` = 2^23 + 2^15**:
   2^23 is the round-to-nearest half for the >>24 shift; the extra 2^15 (half an input LSB)
   biases up to compensate the 65536-vs-65535 denominator. Verified: max output over all
   inputs is exactly 255 (no clipping), and reconstruction `(r8/255)·(S/31)` tracks
   `r16/65535` to within ~1 part in 2000 across the range.
6. **Edge cases**: brightness==0 → all zeros; all-black pixel → RGB 0 with
   `brightness_5bit = min(brightness,31)`; max16==0 after scaling → 0/0
   [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L42-L47,L61-L65,L91-L98].

**Driver wiring.** `APA102ControllerHD` = `APA102Controller` with
`GAMMA_CORRECTION_MODE = kFiveBitGammaCorrectionMode_BitShift` (and zeroed start/end frames)
[S615:src/fl/chipsets/apa102.h#L270-L297]. Its `showPixelsGammaBitShift()` pulls **raw**
pixel bytes (`getRawPixelData()` — bypassing the dither/scale pipeline entirely), processes
them through `five_bit_hd_gamma_bitshift` in stack batches of 8, and applies RGB reordering
only at write-out [S615:src/fl/chipsets/apa102.h#L174-L226]. Under `FASTLED_HD_COLOR_MIXING`
(default **on** for non-AVR [S615:src/crgb.h#L10-L18]) the controller gets the un-premixed
color scale and brightness separately via `loadRGBScaleAndBrightness()`
[S615:src/pixel_controller.h#L551-L576]. HD mode therefore does NOT use temporal dithering —
the 5-bit analog scale replaces it as the precision mechanism.

**Non-HD APA102 also gets a lesser version** ("this function is pure magic"): per *frame* (not
per pixel), it takes the premixed per-channel scales, computes
`brightness = ((max_scale + 1) * 31 - 1) / 256 + 1` and re-normalizes the three scale factors
by `s = (31*s + brightness/2) / brightness` — pushing global brightness into the 5-bit field
so the 8-bit scales stay high [S615:src/fl/chipsets/apa102.h#L130-L149], gated by
`FASTLED_USE_GLOBAL_BRIGHTNESS`. Under HD color mixing the non-HD controller instead maps
brightness 0–255 → 0–31 linearly with a floor of 1 for nonzero brightness (issue #1908 fix)
[S615:src/fl/chipsets/apa102.h#L108-L129].

Excerpt: `research/excerpts/S615-five-bit-hd-gamma/five_bit_hd_gamma.cpp.hpp`.

### 3. Color correction, temperature, and "video" scaling variants

**computeAdjustment — one premixed per-channel scale.** Master brightness (u8), color
correction (CRGB, e.g. `TypicalLEDStrip` = 0xFFB0F0) and color temperature (CRGB white point)
are folded into a single per-channel u8 scale at `show()` time, not per pixel:
for each channel, `adj = ((cc+1) * (ct+1) * scale) / 0x10000` (u32 intermediate, truncating
divide, then `& 0xFF`) [S615:src/crgb.cpp.hpp#L29-L52]. The `+1` on each u8 factor makes 255
behave as exactly 1.0 (255→256/256). If either correction or temperature channel is 0 the
channel scale is 0. `NO_CORRECTION=1` compiles it down to `(scale,scale,scale)`. Controllers
call this via `getAdjustment(brightness)` on each show
[S615:src/fl/channels/cled_controller.h#L367-L373]; comment notes it is deliberately
size-optimized because it runs once per frame, not per pixel.

The result lands in `ColorAdjustment.premixed`; with `FASTLED_HD_COLOR_MIXING` the struct
*additionally* carries the un-premixed `color` (correction×temperature at full brightness) and
raw `brightness` separately [S615:src/pixel_controller.h#L74-L92] — that split exists so the
HD (APA102HD) path can feed gamma-corrected color and brightness into the 5-bit optimizer
separately instead of consuming a single premixed scale (see §2).

**scale8 exact math** (default `FASTLED_SCALE8_FIXED=1`, set in
[S615:src/fastled_config.h#L40-L47]):
- `scale8(i, s) = (i * (s+1)) >> 8` — maps 255×255→255 (no off-by-one darkening), truncating
  [S615:src/platforms/shared/scale8.h#L26-L32].
- `scale8_video(i, s) = ((i*s) >> 8) + ((i && s) ? 1 : 0)` — **never drops a nonzero input to
  zero** as long as scale is nonzero [S615:src/platforms/shared/scale8.h#L39-L42]. This is the
  low-end-blackout guard: at brightness 10/255, `scale8(3,10)` = 0 (LED goes dark) but
  `scale8_video(3,10)` = 1 (LED stays minimally lit). The tradeoff is a systematic +1 bias, so
  "video" scaling is less colorimetrically accurate but preserves the *presence* of dim pixels.
- `nscale8x3(r,g,b,s)` / `nscale8x3_video(r,g,b,s)` are the in-place 3-channel versions; video
  computes `nonzeroscale = (scale!=0)` once and adds it to each nonzero channel
  [S615:src/platforms/scale8.h#L69-L118].
- 16-bit versions `scale16by8` / `scale16` use the same `(i*(s+1))>>bits` fixed-point trick
  [S615:src/platforms/shared/scale8.h#L88-L114].

Note the division of labor: the *output* pipeline (PixelController) uses plain truncating
`scale8` + temporal dither to preserve accuracy, while `_video` variants are for *user-space*
effect math (fades, `CRGB::nscale8_video`) where losing a dim pixel entirely is worse than a
small bias.

### 4. Palette system and gamma functions

**Representation.** Palettes are fixed-size arrays of CRGB (or CHSV): `CRGBPalette16/32/256`
built on `detail::TCRGBPalette<N>` [S615:src/fl/gfx/colorutils.h#L300-L306,L705]. Authoring
format is the **gradient palette**: packed 4-byte `(index, r, g, b)` entries (union with a
u32) where index runs 0–255 and the list terminates at index 255
[S615:src/fl/gfx/colorutils.h#L307-L321]; `DEFINE_GRADIENT_PALETTE` blobs are expanded into a
CRGBPalette16 at assignment, with documented semantics of **preserving every color stop at the
cost of exact stripe widths** (a 1-entry-wide spike survives as 1/16 of the palette) and a
safety cap `FASTLED_MAX_GRADIENT_PALETTE_ENTRIES` against missing terminators
[S615:src/fl/gfx/colorutils.h#L740-L800].

**Lookup — `ColorFromPalette(CRGBPalette16, u8 index, u8 brightness, TBlendType)`**
[S615:src/fl/gfx/colorutils.cpp.hpp#L395-L483]:
- `hi4 = index>>4` selects the entry, `lo4 = index&0x0F` is the blend fraction.
- If blending (`lo4 != 0` and not `NOBLEND`): `f2 = lo4<<4`, `f1 = 255-f2`, result =
  `scale8(entry, f1) + scale8(next, f2)` (sums provably can't overflow, so plain adds). Entry
  15 wraps to entry 0 — palettes are circular by default.
- `LINEARBLEND_NOWRAP` first remaps index via `map8(index, 0, 239)` so the top entry is a hard
  stop instead of wrapping [S615:src/fl/gfx/colorutils.cpp.hpp#L397-L400].
- Brightness applies a hand-rolled *approximate video* scale: `++brightness` then `scale8`
  only on nonzero channels (with a `++channel` compensation only in non-FIXED builds)
  [S615:src/fl/gfx/colorutils.cpp.hpp#L450-L480].
- `ColorFromPaletteExtended(pal, u16 index, …)` gives a 16-bit index: top 4 (or 5) bits select
  the entry, next 8 bits are the blend fraction — smoother palette sweeps
  [S615:src/fl/gfx/colorutils.cpp.hpp#L340-L386,L485].

**New HD lookup (3.10-era)** — `ColorFromPaletteHD` returns `CRGB16` (per-channel `u8x8`
8.8 fixed point): entries are promoted `<<8`, lerped in 24-bit intermediate
`(a₈.₈·(seg-frac) + b₈.₈·frac)/seg`, and brightness is a `u8x8` multiply with saturation at
0xFFFF [S615:src/fl/gfx/colorutils.cpp.hpp#L271-L336]. This is the palette-side half of the
HD color pipeline: palette blends no longer quantize to 8 bits before brightness scaling.

**Palette animation.** `nblendPaletteTowardPalette(current, target, maxChanges)` mutates at
most `maxChanges` byte-channels per call by ±1 (−2 when overshooting downward) — a rate-limited
per-frame crossfade that never allocates and converges in ≤255 frames
[S615:src/fl/gfx/colorutils.cpp.hpp#L1251-L1288]. `UpscalePalette` converts 16→32→256 entries
by interpolation or repetition [S615:src/fl/gfx/colorutils.cpp.hpp#L1185-L1230].

**Gamma functions** — three distinct mechanisms:
1. `GAMMA_2_8_LUT` / `gamma_2_8(u8)→u16`: the 256×u16 LUT (`round((i/255)^2.8·65535)`) used by
   HD pipelines [S615:src/fl/math/ease.cpp.hpp#L22-L54].
2. A runtime `Gamma8` cache: `Gamma8::getOrCreate(float)` builds arbitrary-gamma LUTs but
   *aliases* the precomputed 2.8 LUT for the default, guaranteeing bit-identical output
   [S615:src/fl/math/ease.cpp.hpp#L400-L491] (used by UCS7604's per-controller gamma override).
3. `applyGamma_video(u8, float)`: computes `(i/255)^gamma` in **s16x16 fixed point**
   (deliberately avoiding libm's ~2.7 KB `pow`, issues #2886/#2910), scales with round-half-up
   `(raw·255 + 0x8000)>>16`, and **clamps nonzero inputs to a minimum of 1** ("never
   gamma-adjust a positive number down to zero") — the video-variant blackout guard again
   [S615:src/fl/gfx/colorutils.cpp.hpp#L1290-L1310]. Array versions `napplyGamma_video`
   operate in place [S615:src/fl/gfx/colorutils.cpp.hpp#L1329-L1350].

Stock palettes (Cloud/Lava/Ocean/Forest/Rainbow/RainbowStripes/Party/Heat) live in
[S615:src/colorpalettes.cpp.hpp] as PROGMEM CRGBPalette16 data.

### 5. Chipset timing (chipsets.h): WS2812 vs APA102 vs HD107, HD108/16-bit status

**Timing model.** All clockless chips are described by a three-phase T1/T2/T3 model in
nanoseconds: line goes high at T=0; drops at T1 for a 0-bit; drops at T1+T2 for a 1-bit; cycle
ends at T1+T2+T3 [S615:src/fl/chipsets/led_timing.h#L1-L18]. Conversion from datasheet
T0H/T0L/T1H/T1L: `T1=T0H, T2=T1H-T0H, T3=duration-T1H` with worked WS2812B example
(400/850/850/400 → 400/450/400) [S615:src/chipsets.h#L380-L395]. As of this sha, timings are
*centralized* in `fl::TIMING_*` structs in `fl/chipsets/led_timing.h` (T1,T2,T3,RESET enum
members); `chipsets.h` controllers just bind them to `ClocklessControllerImpl`
[S615:src/chipsets.h#L398-L506].

**Key clockless entries** (T1/T2/T3 ns, RESET µs) [S615:src/fl/chipsets/led_timing.h#L100-L460]:

| Chip | T1 | T2 | T3 | RESET µs | notes |
|---|---|---|---|---|---|
| WS2812 (default) | 250 | 625 | 375 | 280 | overridable via `FASTLED_WS2812_T1/T2/T3` macros |
| WS2812B-Mini-V3 / V5 | 225 | 355 | 645 | 280 | newer silicon, tighter tolerances |
| WS2812 legacy | 320 | 320 | 640 | 280 | pre-centralization values |
| WS2813 | 320 | 320 | 640 | 300 | |
| SK6812 (RGBW) | 300 | 600 | 300 | 80 | |
| WS2811 @400kHz | 800 | 800 | 900 | — | datasheet-standard slow mode |
| WS2811 @800kHz | 250 | 350 | 650 | — | |
| WS2815 | 250 | 1090 | 550 | — | 12 V, long T2 |
| UCS7604 @800kHz | 250 | 625 | 375 | — | **16-bit clockless**, preamble protocol |
| UCS7604 @1600kHz | 100 | 350 | 175 | — | 16-bit at double rate |

A global overclock multiplier (`FASTLED_OVERCLOCK`, e.g. 1.2 = 20% faster, per-chipset
overridable `FASTLED_OVERCLOCK_WS2812` etc.) compresses these timings; comments state WS2812
tolerates ~20% [S615:src/fl/chipsets/led_timing.h#L25-L72].

**SPI (clocked) chips are defined by default clock rate, not bit timing**
[S615:src/fl/chipsets/apa102.h#L25-L372]:
- **APA102**: default `DATA_RATE_MHZ(6)` — deliberately slow because long strips degrade the
  regenerated clock (cites pjrc.com "why APA102 LEDs have trouble at 24 MHz"); "just works"
  prioritized over speed [S615:src/fl/chipsets/apa102.h#L28-L33].
- **SK9822**: same protocol, 12 MHz default, zeroed end frame.
- **HD107**: "just the APA102 with a default 40 MHz clock"; **HD107HD = APA102HD at 40 MHz**
  [S615:src/fl/chipsets/apa102.h#L343-L372]. Higher clock = more strips/frames per second, same
  4-byte frame format.
- End-frame math: APA102 needs `(nLeds/32)+1` extra dwords to clock data through the strip
  [S615:src/fl/chipsets/apa102.h#L46-L58,L261-L267].

**HD108 (16-bit) IS supported** [S615:src/fl/chipsets/hd108.h#L12-L98]: SPI MODE3, default
25 MHz (max 40). Protocol: 64-bit zero start frame; per LED 2 header bytes
(`[1][RRRRR][GG]`,`[GGG][BBBBB]` — three 5-bit per-channel *gain* fields, hardwired to 31 in
this driver) + 6 color bytes (three 16-bit big-endian channels); end frame `(nLeds/2)+4` bytes
of 0xFF. **Precision caveat**: the driver feeds it from the standard 8-bit pipeline —
`loadAndScaleRGB()` (8-bit premixed scale + dither) then `gamma_2_8()` LUT to 16-bit
[S615:src/fl/chipsets/hd108.h#L59-L88]. So HD108 gets 16-bit *gamma placement* but only 8-bit
*source resolution*; the 5-bit gain field is not used for HD-style joint optimization the way
APA102HD uses its brightness field. The UCS7604 16-bit path is more developed: it has a real
16-bit encoder with per-controller gamma override (`Gamma8::getOrCreate(gamma)`, default 2.8)
and 4-bit per-channel current control [S615:src/fl/chipsets/ucs7604.h#L17-L50,L160-L195].

### 6. release_notes.md: 3.9/3.10 color-mixing changes, 4.0 promises

All cites are `release_notes.md` at the pinned sha [S615]; the web copy is seed [S009].

**Color/quality timeline:**
- **3.9.0** ("Beta 4.0.0 release"): the HD split lands — "global brightness and color scaling
  are now separate for non-AVR platforms… APA102 and APA102HD now perform their own color
  mixing in pseudo 13 bit space", opt-out via `FASTLED_HD_COLOR_MIXING=0`
  [S615:release_notes.md#L916-L935]. Also async `show()` via ESP32 RMT5: prepare-next-frame
  overlaps draw; benchmark 34→59 fps on Animartrix [S615:release_notes.md#L953-L973].
- **3.9.12**: WS2816 "high definition" support — 16-bit-per-channel chip on the WS2812
  protocol with 4-bit on-chip gamma; "8-bit gamma correction from software + hardware is
  possible, but not implemented yet" [S615:release_notes.md#L645-L653].
- **3.9.13**: HD107(s) + HD mode arrive — "exactly the same as the APA102 chipset, but with
  turbo 40-mhz"; notes APA102 is deliberately underclocked for long-strip stability
  [S615:release_notes.md#L629-L635].
- **3.10.0**: Animartrix out of beta (the artist-focused pivot; see also [S010])
  [S615:release_notes.md#L493-L500].
- **3.10.2** — the big color-quality release:
  - **HSV16**: "CRGB → HSV → CRGB is highly lossy. CRGB → HSV16 → CRGB is almost perfect",
    integer-based [S615:release_notes.md#L446-L449].
  - **ColorBoost** (`CRGB::colorBoost()`): saturation-boosting alternative to gamma for RGB8
    chips — "preserves luminosity but allows you to increase saturation", built on HSV16
    [S615:release_notes.md#L450-L455].
  - Pluggable HSV→RGB conversion (`FASTLED_HSV_CONVERSION_RAINBOW/SPECTRUM/FULL_SPECTRUM`)
    [S615:release_notes.md#L456-L465].
  - **APA102HD gamma "completely rewritten with closed-form mathematical solution"** (credit
    gwgill; links a log-log plot of the old algorithm's quantization errors at argyllcms.com)
    [S615:release_notes.md#L476-L480]. The code analyzed in §2 IS this rewrite.
- **3.10.3**: WS2812B default reset time raised 50µs → 280µs across all platforms — newer
  WS2812B revisions showed "~80% failure rate" with the old 50µs latch (issue #2067)
  [S615:release_notes.md#L392-L400]. Hard-won compatibility constant.
- **3.10.4** (unreleased at pin): HD108/NS108 16-bit chipset (see §5) with claimed 27 kHz PWM
  vs APA102's ~20 kHz [S615:release_notes.md#L86-L102]; WS2812B-V5/Mini-V3 timings
  [S615:release_notes.md#L57-L63]; **native RGBW without emulation on RP2040/RP2350** (mixed
  RGB/RGBW strips in one parallel group) [S615:release_notes.md#L64-L70]; **RP2040 automatic
  parallel I/O driver** — up to 8 parallel WS2812 strips via PIO
  [S615:release_notes.md#L217-L220]; ESP32-S3/P4 LCD/PARLIO 16-lane drivers
  [S615:release_notes.md#L221-L285].

**4.0 promises** (as recorded in-repo): the whole 3.9.x line is explicitly labeled 4.0 betas
("3.9.8 is the 7th beta release of FastLED 4.0" [S615:release_notes.md#L736]; beta 2/3 labels
[S615:release_notes.md#L858-L871]); 3.9.9 declares the tree "header-stable with 4.0 release"
[S615:release_notes.md#L726]; deprecated `src/` stub headers will be removed at 4.0
[S615:release_notes.md#L807]; plus a teaser ("exciting stuff on the horizon", 3.9.4)
[S615:release_notes.md#L850]. **There is no consolidated 4.0 feature roadmap in the repo** —
the artist-focused-roadmap narrative comes from press coverage [S010], not release_notes.md.

## What pewpew should steal

1. **The output-pipeline ordering: load → add dither → scale (truncating), never the reverse.**
   Binary dithering with a bit-reversed frame counter, per-channel range `e = 256/premixed_scale`,
   and the per-pixel spatial toggle `d = e - d` is ~30 lines of integer math and delivers +2–3
   perceived bits on WS2812-class chips (§1). Skip dither on black pixels.
2. **The exact five_bit_hd_gamma math** for APA102/SK9822/HD107: 16-bit gamma LUT →
   16-bit correction/brightness multiplies → `S = ceil(max16·31/65536)` via the shift trick →
   `r8 = (r16·(2023680/S) + 0x808000) >> 24`. Two small tables (512 B + 128 B), no divides in
   the per-pixel path, numerically verified clip-free (§2).
3. **The premixed-adjustment pattern**: fold brightness × correction × temperature into one
   per-channel u8 once per frame (`(cc+1)(ct+1)·scale / 0x10000`), but *also* keep the
   un-premixed color scale and brightness separately so >8-bit output paths can apply them at
   higher precision (the `ColorAdjustment {premixed, color, brightness}` split, §3).
4. **`scale8` fixed-point semantics** `(i·(s+1))>>8` (so 255 acts as 1.0) and the `_video`
   variant's nonzero-preserving guard for user-space fades (§3).
5. **A centralized nanosecond T1/T2/T3 timing table** decoupled from drivers, with per-chipset
   RESET times and an overclock multiplier — the RP2040 PIO driver consumes the same structs
   by converting ns→cycles at compile time (§5). Adopt the 280µs WS2812 reset default (§6).
6. **Gradient-palette authoring format** (packed index+RGB stops, expand to 16-entry palettes
   preserving every color stop) and `nblendPaletteTowardPalette`'s allocation-free, rate-limited
   palette crossfade (§4). For a new engine, take the HD variant (`ColorFromPaletteHD` semantics:
   lerp and brightness in 8.8 fixed point) rather than the 8-bit-quantizing classic.

## What to avoid

- **The `static` dither frame counter** inside `init_binary_dithering()` — process-global
  mutable state shared by all strips, incremented once per controller per show
  [S615:src/pixel_controller.h#L312-L313]. Racy across cores; make it per-output state.
- **Compile-time virtual-bit budget** assuming 400 Hz refresh — the code's own comment admits
  it should be derived from measured ms-since-last-update [S615:src/pixel_controller.h#L282-L291].
  Compute dither depth from actual frame rate.
- **HD108 driver's 8-bit bottleneck**: it scales+dithers at 8 bits and only then expands via
  the gamma LUT, wasting the chip's 16-bit input; the three per-channel 5-bit gain fields are
  hardwired to 31 (§5). Feed a 16-bit chip 16-bit-native data instead.
- **Dual palette APIs** (classic 8-bit `ColorFromPalette` + new `ColorFromPaletteHD` CRGB16,
  plus Extended u16-index variants of each) — compat-driven sprawl; a new engine needs one
  16-bit-native path.
- **The `.cpp.hpp` unity-build layout and AVR-driven micro-optimizations**
  (`scale8_LEAVING_R1_DIRTY`/`cleanup_R1`, PROGMEM plumbing) — irrelevant noise off-AVR; steal
  the algorithms, not the structure.
- Undocumented magic where it exists: the two post-hoc decrements in dither init
  (`if(d[i]) --d[i]; if(e[i]) --e[i];`) carry no derivation (see Open questions) — re-derive
  before relying on them.

## RP2040 portability notes

- **All quality machinery in §§1–4 is portable integer math** (u8/u16/u32 multiplies, shifts,
  two small LUTs; the only divides are 3 per frame in dither init and the per-frame
  computeAdjustment). `applyGamma_video` deliberately avoids float `pow` via s16x16 fixed
  point. Nothing depends on Arduino APIs. Excellent fit for Cortex-M0+/M33.
- **FastLED already treats RP2040/RP2350 as first-class at this sha**: PIO-based clockless
  driver converts the shared ns timing structs to cycles
  (`(TIMING::T1 * (F_CPU/1e6) + 500)/1000`) [S615:src/platforms/arm/rp/rpcommon/clockless_rp_pio.h#L81-L83],
  auto-selects among 2 PIOs (RP2040) / 3 (RP2350) with DMA and an M0 bit-bang fallback
  [S615:src/platforms/arm/rp/rpcommon/README.md], supports 8-lane parallel output with native
  RGBW [S615:release_notes.md#L64-L70,L217-L220].
- **Temporal dithering survives the port unchanged**: the RP2040 PIO drivers drive the same
  `loadAndScale*/stepDithering` pipeline [S615:src/platforms/arm/rp/rpcommon/clockless_rp_pio.h#L335-L363,
  src/platforms/arm/rp/rpcommon/clockless_rp_pio_auto.cpp.hpp#L389-L413]. The refresh-rate
  constraint is physics, not platform: ≥400 Hz per lane ⇒ ≤~85 WS2812/lane for 3 virtual
  bits; parallel PIO lanes are the lever.
- **APA102HD path** is plain SPI + integer math; RP2040 hardware SPI comfortably reaches
  HD107's 40 MHz. This is arguably the highest-quality output pewpew can get from an RP2040.

## Open questions

- The two compensation decrements in `init_binary_dithering()` (`if(d[i]) --d[i];` for
  "scale8 implementation quirk", and `if(e[i]) --e[i];` before toggling)
  [S615:src/pixel_controller.h#L355-L360] have no derivation in code or docs; whether they are
  exactly right for `FASTLED_SCALE8_FIXED` truncation or empirically tuned is undocumented.
- HD108: the driver hardwires per-channel gain to 31 and does not attempt APA102HD-style joint
  optimization; the comment even hedges on the start-frame length ("some sources mention 128
  bits, but 64 bits works reliably") [S615:src/fl/chipsets/hd108.h#L54-L57]. Actual chip
  behavior of the per-channel gain fields is unverified here.
- WS2816's promised software+hardware 8-bit gamma ("may see a color correction enhancement
  down the line", 3.9.12) — no evidence in the tree that it landed by this sha.
- No consolidated 4.0 roadmap exists in-repo; 4.0 scope beyond "header-stable, deprecated
  headers removed" is press-sourced [S010], not verifiable from code.
- `MAX_LIKELY_UPDATE_RATE_HZ`/runtime virtual-bits TODO remains open at this sha — dither
  depth is still not adaptive.
- Whether APA102HD's bypass of temporal dithering (it uses raw pixel data) leaves quality on
  the table at brightness extremes (5-bit scale floor) is untested here; combining HD split
  with dithering is an open design idea for pewpew, not something FastLED does.
