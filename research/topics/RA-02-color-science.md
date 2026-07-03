# RA-02: Color science & high-fidelity output

Last researched: 2026-07-03
Status: draft
S-ID block: S050–S099 (new IDs from S058)

## Key questions

1. Gamma correction vs CIE 1931 lightness for perceived-brightness linearization — which, and where in the pipeline?
2. Temporal dithering: how do FastLED, Fadecandy, SmoothLed, and recent implementations work; what refresh rate does each chip class permit; how many effective bits can dithering add per class?
3. What does FastLED's APA102HD "pseudo-13-bit" gamma actually do, and what hardware does it require?
4. What do Pixelblaze v3.47 "HDR LED drivers" actually do?
5. What is WLED's dithering situation?
6. Is OKLab/OKLCh used by any LED project yet; should pewpew use it for blending?
7. RGBW: W-channel derivation strategies.
8. White-point calibration across LED batches.
9. End-to-end 16-bit pipeline design — where quantization must happen and why.
10. Which techniques require which hardware tier (wearable / portable / room)?

## Findings

### Perceived-brightness linearization: gamma vs CIE 1931 lightness

Human lightness perception is not linear in luminance; two curves compete for
linearizing it in LED work:

- **Power-law "gamma"** (typically γ=2.2–2.8). Historically a CRT display
  transfer characteristic, not a perception model. The Adafruit LED community
  convention is a γ=2.8 8-bit→8-bit table [S058]; WLED's default gamma is 2.8
  (see WLED section below).
- **CIE 1931 lightness (L\*)** — the psychometric lightness function used in
  CIELAB: L\* = 116·(Y/Yn)^(1/3) − 16 for Y/Yn > 0.008856, L\* = 903.3·(Y/Yn)
  below that; inverted for driving LEDs it is Y = ((L\*+16)/116)^3 with a
  linear toe [S059][S060]. Two maker-community treatments argue this is the
  *correct* perceptual linearization and that gamma "appears to work" only by
  coincidence, because a γ≈2.2 power curve happens to roughly track the L\*
  cube-law-with-offset curve [S059][S060]. The photography-side analysis
  concurs: "CIE Lightness is the more precise formulation than gamma
  functions" — γ=2.2 puts 18% gray at 46% rather than the perceptual 50%
  (L\*≈53.8 for 21.8% gray) [S061].

Practical consequences for pewpew:

- The difference between γ=2.2/2.8 and inverse-L\* is modest at mid/high
  levels but significant near black — exactly the region LEDs render worst.
  Inverse-L\* is effectively a ~3.0 exponent with an offset, i.e. *steeper*
  at the low end than γ=2.2 [S059][S061].
- Either curve, applied 8-bit→8-bit, collapses the bottom of the range: a
  γ=2.8 table maps the first ~16 input codes to output 0 or 1 [S058]. This is
  the quantization problem that motivates 16-bit intermediates plus temporal
  dithering or extra hardware bits (APA102HD) — see below. **The curve choice
  matters less than the bit depth at which it is applied** [S058][S059].
- Both community sources implement via lookup table (power/cube ops too slow
  on MCUs); jared.geek.nz recommends 8-bit-in → 10-bit-PWM-out minimum, the
  ledshield post computes 16-bit internal values [S059][S060].

Verdict for pewpew: linearize with inverse-CIE-L\* (or a per-install
configurable exponent defaulting near 2.6–3.0), applied as the *last* lossy
step from a ≥16-bit linear working space, never as an 8→8 table.

### Temporal dithering

**Principle.** Refresh the strip much faster than the animation frame rate and
alternate each pixel between adjacent 8-bit codes so the time-average carries
the sub-LSB information; the eye integrates it. All implementations agree on
the constraint: quality is bounded by refresh rate.

**FastLED "binary dithering"** (since v2.1, still current in 2026). Activates
automatically when master brightness < 255 and the sketch calls
`FastLED.show()`/`FastLED.delay()` frequently; without it the brightness scaler
"reverts back to 'flooring' integer values", losing dim colors entirely [S050].
Its purpose is narrow: preserving color/light *under master-brightness
scaling*, not a general 16-bit pipeline. The wiki warns that at low refresh
rates + low brightness "you may see the dithered pixel output as flickering",
and recommends disabling for POV/light-painting (`FastLED.setDither(0)`)
[S050]. Community rule of thumb: strip refresh should exceed ~400 Hz for
invisible dithering [S050][S019]. Implementation detail (binary/ordered
counter per channel) is in `controller.h` — code-reading queue item.

**Fadecandy** (Micah Elizabeth Scott, 2013). The canonical high-fidelity
pipeline: host sends 24-bit keyframes over USB; firmware linearly interpolates
between keyframes at the hardware refresh rate, pushes the interpolated value
through a host-uploaded 16-bit color LUT ("There is no default table, the
firmware expects you to calculate one based on the gamma and whitepoint you'd
like to use"), then temporally dithers the 16-bit result down to the WS2811's
8 bits [S015][S016][S062:doc/fc_protocol_usb.md]. The dither is described as
"a form of delta-sigma modulation that rapidly wiggles each pixel's value up
or down by one 8-bit step, in order to achieve 16-bit resolution for fades"
[S016]. Board spec: 8 strings × 64 pixels at "~400 fps" hardware refresh — the
64-pixel-per-line limit is exactly what keeps WS2811 refresh at ~400 Hz
[S015][S016]. Interpolation and dithering are independently disableable via
config bits [S062:doc/fc_protocol_usb.md]. Status: **dormant/waning as a
product** — original repo `scanlime/fadecandy` has been deleted from GitHub
(404 as of 2026-07-03); surviving forks (e.g. pixelmatix/fadecandy, MIT, last
push 2020-12-23) carry the code [S062]. The *technique* is ascendant — it is
the reference every later effort cites [S054][S057][S019].

**SmoothLed** (mattshepcar). Fadecandy-style interpolation + temporal
dithering reimplemented for ATtiny 0/1-series (e.g. ATtiny1614) using the SPI/
USART-MSPI + CCL peripherals for low-CPU WS2812 output; README states "the
LED strip must be updated at a high frequency, preferably above 400Hz" and
supports custom gamma LUTs (`setGammaLut`) and a dither mask
(`setDitherMask`). MIT license; v1.0.1, 2020-07-07, no activity since —
dormant but complete; proof the technique fits the **wearable tier** [S019].

**Sarah Alroe, 2025 (ATtiny412, 27× WS2812B).** Recent independent
implementation using *error diffusion* rather than ordered dithering:
compute in 16-bit, output 8-bit, carry the truncated LSBs into the next
cycle's calculation (27 bytes of state for 27 pixels). Found ordered dither
"noticeably more flickery" than error diffusion, attributed to aliasing
between the dither pattern and recomputed animation colors [S056]. Gamma done
arithmetically (cube / averaged squares) to avoid a 256-byte LUT in 256 B RAM
[S056]. No quantified bit-gain or frame-rate numbers published [S056].

**ESP32 parallel output (hpwit I2SClocklessLedDriver).** 2022 discussion of
adding Fadecandy-grade dithering inside the ESP32 I2S parallel driver;
contributor swifty99 estimates temporal dithering adds "2-4 Bits color depth"
and sketches a post-`show()` "pixel pipeline" (gamma, fading, dithering)
below the application; hpwit judged it feasible ("with the full DMA buffer
option of the driver the dither should be a breeze just the time to calculate
the buffer") but the thread shows no completed implementation [S057]. The
significance: 16-way parallel I2S output divides pixels-per-line by 16, so
room-scale installs can stay above the ~400 Hz dither threshold [S057].

**Adafruit NeoPXL8HDR** (maintained, RP2040/ESP32-S3 focus). The most
complete *quantified* modern implementation: 16-bit-per-channel input
(48/64-bit RGB/RGBW), temporal dithering to WS2812, built-in gamma
("perceptually-linear brightness ramps … built into the library"), and
frame-to-frame blending. Effective depth: "12 bits by default, and with
shorter pixel runs you might manage 13 bits" — i.e. dithering adds ~4–5 bits
over the chip's 8 when refresh is high enough. Costs: "consumes inordinate
RAM and resources" (+6/8 bytes per pixel just for blending); wants a
dedicated core ("works best with a Feather RP2040 or ESP32-S3", M4 degraded,
M0 unsupported); ~1000 pixels split 8 ways is the guideline budget. The
guide is blunt about the mechanism: "NeoPixels still use 8-bit brightness
levels, this doesn't magically make them 16-bit" [S064].

**Refresh-rate budget per chip class** (drives how many effective bits
dithering can add):

- *WS2812-class (800 kbps one-wire):* 30 µs/pixel + ≥280 µs latch ⇒ ~400 Hz
  is reached at roughly 64–80 pixels per line — precisely Fadecandy's
  64-pixel channel limit [S015][S016]. Longer lines need parallel output
  (OctoWS2811 8-way, ESP32 I2S/LCD 16-way) to keep the rate [S057]. Practical
  gain at 400–1 kHz refresh with ~30–60 fps animation: ~3–4 effective bits
  [S057]; Fadecandy's "16-bit resolution for fades" claim [S016] is about
  smoothness of *slow fades* (time-averaged), not 16 simultaneously
  distinguishable static levels.
- *APA102/SK9822-class (2-wire SPI, multi-MHz):* data rate no longer the
  binding constraint; kHz-range strip refresh is easy even on long lines, so
  dithering headroom is much larger — and the chip additionally offers a
  hardware 5-bit global-brightness field (see APA102HD below). Best chip
  class for high-fidelity output; cost and 4-wire cabling are the tradeoff
  [S051][S053].
- *Chip-internal PWM floor:* the LED's own PWM (~1–20 kHz depending on chip
  generation) sets a ceiling; dithering toggles whole 8-bit codes so it is
  not limited by it, but low-frequency chip PWM (older WS2812, APA102's
  ~440 Hz 5-bit brightness stage) can beat against dithering and camera
  shutters [S053][NEEDS-VERIFICATION — exact per-chip PWM rates belong to
  RA-03].

### FastLED APA102HD "pseudo-13-bit" gamma

APA102/SK9822 frames carry 8-bit RGB *plus a per-LED 5-bit brightness field*.
FastLED long used that field only as a global brightness workaround; the HD
mode (PR #1546, shipped ~3.6.x, rewritten in 3.9.0) exploits it per-pixel
[S051][S053]. Pipeline: `RGB8 → RGB16 + 5-bit gamma → RGB8 + 5-bit gamma` —
i.e. gamma-correct each channel into 16 bits, then find the smallest 5-bit
brightness that accommodates the largest component and rescale the RGB back
to 8 bits under it [S053]. "Pseudo-13-bit" because the extra resolution only
materializes when *all* components are small: `CRGB(255,1,1)` gains nothing
(the 255 pins brightness at max), `CRGB(8,8,8)` gains a lot — "precisely
where increased resolution is most desired" [S053]. The 3.9.0 closed-form
quantization (`scale = (max + (2047 - (max >> 5))) >> 11`, LUT-scaled with
rounding) claims worst-case 0.2% / average 0.05% error vs the float
reference, and runs on AVR [S053]. 3.9.0 also stopped pre-mixing global
brightness into color scales for APA102: brightness goes into the 5-bit
field, color correction into the RGB — so even *non*-HD APA102 mode gains
resolution under `setBrightness()` [S053].

Notes for pewpew: this is a *spatially local, per-frame* technique — no
refresh-rate requirement, unlike dithering — but it is hardware-gated to the
APA102/SK9822/HD107 class (and 16-bit chips like HD108 supersede it). It
also bakes a gamma decision into the driver ("gamma correction is applied to
preserve the RGB8 format" [S053]), which conflicts with a system that wants
its own linearization curve; a 16-bit-native pipeline would instead feed the
quantizer linear 16-bit values. Design discussion in issue #1545 [S052];
implementation lives in `src/fl/five_bit_hd_gamma.*` (code-reading queue).

### Pixelblaze v3.47 "HDR LED drivers"

Release v3.47 (July 2023): "Total rewrite of all LED drivers … Now supports
full HDR 48-bit color using WS2816 and NS108 LEDs"; previews "no longer dim
based on brightness settings - only pattern values"; users reported ~2×
frame-rate gains (12–24 → 23–38 fps at 864 LEDs) [S014]. Ben Hencke's
contemporaneous Mastodon thread is the clearest technical statement:
"Rewrite of the pixel stack for #pixelblaze. All 16 bit per element
throughout. Tons more HDR LED options now, and have NS108 and WS2816 LEDs
support" — demoed with a WS2816 panel at 1% brightness with "plenty of color
resolution and smooth fade to black" [S063].

So Pixelblaze "HDR" is **not** temporal dithering: it is (a) a 16-bit-per-
channel internal pixel pipeline, with brightness/gamma applied in that
16-bit space, plus (b) drivers that deliver all 16 bits to natively-16-bit
chips (WS2816: 48-bit color, built-in gamma, ~10 kHz internal PWM refresh
[S065]; NS108/HD108: 16 bit/element SPI chips, ~19 mA/element per Hencke
[S063]). On 8-bit chips the 16-bit stack still helps (quantization happens
once, at the very end) but there is no public evidence Pixelblaze dithers
them [S014][S063][NEEDS-VERIFICATION — firmware is closed-source]. This is
the closest existing product to the pipeline pewpew wants; it validates
"16-bit internal, quantize last, exploit HDR chips where present" as a
shippable architecture on an ESP32-class MCU [S014][S063].

### WLED dithering situation

WLED (GPL/EUPL lineage; repo now `wled/WLED`; actively maintained 2026) has
**no temporal dithering**. Issue #2416 ("Add Fadecandy-style dithering,
gamma and color correction, maybe interpolation", opened 2021-12) remains
open as of 2026-07-03 [S054]. The thread is the best documentation of *why*:
"WLED uses an 8 bit color model for the effects, and has no plans to switch,
so for memory efficiency we should keep the colors stored as 8 bit as long
as possible" (embedded-creations, 2021-12-14) [S054]. Contributors sketched
a NeoPixelBus-level "pixel pipeline" (gamma → brightness → dither in the
DMA-refresh layer, ~40 bytes/RGBW-pixel of state) and Makuna pointed at
NeoPixelBus's DIB + shader hooks as the natural place, but nothing shipped
in WLED or NeoPixelBus [S054]. What WLED *does* have: optional gamma
correction for colors and brightness, default γ=2.8, user-adjustable —
applied 8-bit→8-bit, with the attendant low-end code collapse [S066][S058].
Palette handling has its own gamma inconsistencies (issue #3399) [S054].

Architectural takeaway: retrofitting fidelity into an 8-bit-buffer engine is
socially and technically hard even for the biggest project in the space —
pewpew should be ≥16-bit from day one rather than plan to upgrade later
[S054].

### OKLab/OKLCh for perceptual blending

OKLab (Björn Ottosson, 2020) is a perceptual color space built so that
Euclidean blends and gradients behave: uniform lightness/chroma prediction,
hue linearity, and a cheap transform (3×3 matrix → cube root → 3×3 matrix
from linear sRGB) [S055]. OKLCh is its cylindrical form; both entered CSS
Color Level 4, making them the de-facto modern standard for perceptual
gradients on the web [S067]. Its concrete win over HSV blending: no
mid-gradient brightness dips or hue drift (the classic red→green through
muddy dark yellow problem) [S055].

**Adoption in LED projects as of 2026-07-03: effectively none.** GitHub
repository search for "oklab led" returns zero results; issue search finds
no OKLab work in FastLED, WLED, or Pixelblaze — the only sighting is a
Nanoleaf screen-mirror tool using "OKLab zone averaging" for color
extraction [S068]. FastLED's palettes and blends remain RGB/HSV-based;
Pixelblaze patterns use HSV/RGB helpers [S014]. This is an open
differentiation opportunity, not a validated practice.

Costs/caveats for pewpew:
- The transform needs a cube root per channel; on MCU-tier hardware this
  wants a LUT or fixed-point approximation, on host-tier it is free.
  Blending in OKLab and converting to linear RGB once per pixel per frame is
  the natural placement (analysis; no source implements this on LEDs yet).
- OKLab is defined relative to sRGB/D65 primaries [S055]; LED strip
  primaries are *not* sRGB (typically wider, non-standard), so out-of-gamut
  and white-point questions (below) still need handling after conversion —
  OKLab organizes the *blend*, not the device mapping (analysis).

### RGBW rendering: W-channel derivation

The problem: SK6812-class RGBW strips add a phosphor white die; the engine
renders RGB, and something must derive W. Known strategies, as shipped:

**WLED** ("Auto-calculate white channel from RGB", per-pixel) [S069]:
- *Accurate*: W = min(R,G,B), then subtract W from RGB — correct chromaticity
  but lower peak brightness (RGB dies idle on pure white).
- *Brighter*: W = min(R,G,B), RGB left untouched — brighter, but whites shift
  toward the RGB-mix color and are over-driven.
- *Dual / None*: manual W slider (Dual falls back to Brighter math when
  slider is 0) [S069].

**FastLED** (`fl::RGBW_MODE`, observed at HEAD 8df8258 2026-07-03) [S008]:
- `kRGBWExactColors` (default): color-transfer to white, documented as "the
  most accurate white point for a given color temperature and reduces power
  usage … however the pixel will never achieve full brightness since the
  white channel is 3x more efficient" — e.g. RGB(255,255,255) →
  RGBW(0,0,0,85) [S008:src/fl/gfx/rgbw.h].
- `kRGBWBoostedWhite`, `kRGBWMaxBrightness`, `kRGBWNullWhitePixel` — the
  brightness-vs-accuracy ladder.
- **New in 2025/26: chromaticity-aware modes** `kRGBWColorimetric` /
  `kRGBWColorimetricBoosted` (issue #2545), gated behind
  `FASTLED_RGBW_COLORIMETRIC`, using a per-strip `DiodeProfile` ("diode
  chromaticity + peak luminance … datasheet-derived values for SK6812
  RGBW3535 at 6000K" by default, colorimeter-overridable) plus an input
  gamut [S008:src/fl/gfx/rgbw.h]. This is the state of the art in open
  code: W derivation as a real colorimetric mapping rather than min(R,G,B),
  and it doubles as a per-batch calibration hook.
- A white color temperature parameter (`white_color_temp`) is part of the
  API — acknowledging that the W die is not the same white as R+G+B
  [S008:src/fl/gfx/rgbw.h].

Design note for a 16-bit pipeline: min-subtract in *gamma* space (WLED)
distorts chromaticity; the derivation should happen in linear 16-bit space
using the W die's measured chromaticity/luminance (FastLED's colorimetric
direction), then quantize (analysis grounded in [S008][S069]).

### White-point calibration across LED batches

Addressable LEDs ship uncalibrated; different chip generations, vendors and
bins have visibly different primaries and white points, so serious installs
need a per-strip (ideally per-batch) correction. Shipped mechanisms:

- **FastLED `setCorrection()`**: a per-controller RGB scale; canonical value
  `TypicalSMD5050`/`TypicalLEDStrip` = (255, 176, 240) — i.e. typical 5050
  strips run green-strong and need G scaled to ~69% [S008:src/color.h#L11-L26].
  A separate `setTemperature()` applies lighting-designer color temperatures
  (Candle 1900 K … ClearBlueSky 20000 K) as another RGB scale
  [S008:src/color.h#L46-L62]. Both are 8-bit multipliers — cheap but they
  further shrink the 8-bit code space, another argument for ≥16-bit
  intermediates (analysis).
- **Fadecandy fcserver**: per-device `"color"` config with `gamma` exponent
  and a `whitepoint: [r, g, b]` vector "to multiply by colors prior to gamma
  correction", compiled into the per-channel 16-bit LUT uploaded to the
  device — calibration and linearization share one LUT. It also supports
  `linearSlope`/`linearCutoff` to splice a linear toe under the gamma curve,
  explicitly to "avoid creating very low output values that will cause
  distracting flicker when dithered" (suggested cutoff 1/256)
  [S062:doc/fc_server_config.md]. This gamma+linear-toe shape is
  structurally the same as the CIE L\*/sRGB piecewise curves — convergent
  evolution worth copying [S062][S059].
- **FastLED colorimetric RGBW profiles** (`DiodeProfile`, above) extend this
  to measured per-die chromaticity/luminance and are explicitly designed to
  be overridden "users with a colorimeter can build their own profile"
  [S008:src/fl/gfx/rgbw.h] — the only open-code path toward real batch
  calibration found in this research.
- **WLED**: global RGB color correction is not a first-class feature; users
  approximate via segment color tweaks or per-bus settings
  [NEEDS-VERIFICATION — a WLED code read should confirm what per-bus color
  trim exists in 0.15+].

Gap: no open project does *measured* per-batch white-point calibration with
a documented workflow (measure → matrix/LUT → deploy); everything is
eyeballed scalar trims except FastLED's new DiodeProfile hook [S008].

### End-to-end 16-bit pipeline design

Every high-fidelity system studied converges on the same shape; the
differences are only *where the final quantization lands*:

1. **Render/blend in a wide linear space.** Patterns compute in float or
   16-bit linear RGB (optionally blending in OKLab and converting out).
   Pixelblaze v3.47: "All 16 bit per element throughout" [S063]; Fadecandy
   interpolates 24-bit keyframes into 16-bit values [S016][S062];
   NeoPXL8HDR takes 48/64-bit pixels [S064].
2. **Apply, in the wide space and in this order:** white-point/batch
   correction (multiplicative, before nonlinearity — Fadecandy multiplies
   whitepoint "prior to gamma correction" [S062:doc/fc_server_config.md]),
   RGBW W-derivation (linear space, colorimetric [S008]), master brightness,
   then the perceptual curve (inverse-L\* or gamma, with a linear toe to
   protect the dither floor [S062][S059]).
3. **Quantize exactly once, at the driver, using the best trick the chip
   supports:**
   - 16-bit-native chips (WS2816, NS108/HD108): send all 16 bits; done
     [S063][S065].
   - APA102/SK9822: closed-form 16→(8+5-bit) quantization (APA102HD)
     [S053]; optionally + dithering of the residual.
   - 8-bit one-wire (WS281x/SK6812): temporal dithering of the 16-bit
     residual, viable only when line length/parallelism keeps refresh
     ≳400 Hz [S050][S064][S015]; below that, plain rounding.

Why quantization must be last and singular: any intermediate 8-bit
narrowing (WLED's effect buffers [S054], FastLED's premixed 8-bit scales
pre-3.9 [S053], 8→8 gamma tables [S058]) irreversibly collapses the dark
end, and no later stage can reconstruct it. The WLED thread is the
counterexample proving retrofit cost [S054].

**Hardware-tier applicability summary:**

| Technique | Wearable (ATtiny/small ARM) | Portable (ESP32/RP2040) | Room-scale (host + many lines) |
|---|---|---|---|
| 16-bit internal pipeline | tight but proven (SmoothLed, Alroe) [S019][S056] | proven (Pixelblaze, NeoPXL8HDR) [S063][S064] | trivial (host CPU) |
| Temporal dithering ≥400 Hz | yes, short strips (<~64 px) [S019][S056] | yes with parallel output, ~1000 px / 8 ways [S064][S057] | yes if per-line length capped (Fadecandy: 64/line) [S015] |
| APA102HD 8+5-bit | yes (SPI cheap) [S053] | yes | yes; SPI clock also solves long-line refresh |
| Native 16-bit chips | costlier LEDs, else fine | Pixelblaze-proven [S063] | best fidelity path, chip cost dominates |
| OKLab blending | LUT/fixed-point needed (analysis) | fine | free |
| Colorimetric calibration | LUT fits flash | fine | fine |

## Verdicts

- **Temporal dithering (technique): ascendant.** Reinvented independently in
  2020–2025 (SmoothLed 2020, NeoPXL8HDR, Alroe 2025, hpwit thread 2022)
  because it is the only fidelity path on the dominant 8-bit one-wire chips
  [S019][S064][S056][S057].
- **Fadecandy (product/repo): waning/dead** — original repo deleted, forks
  last pushed 2020 [S062]; but its pipeline (16-bit LUT with whitepoint +
  linear toe, interpolation, dithering) remains the design template [S016].
- **SmoothLed: dormant** (v1.0.1, 2020-07) but complete and MIT; usable as
  wearable-tier reference code, not a dependency [S019].
- **FastLED color machinery: ascendant** — APA102HD rewrite (3.9.0),
  colorimetric RGBW profiles (issue #2545) show active investment through
  2025/26; MIT [S053][S008].
- **Pixelblaze HDR approach: ascendant but closed** — validates 16-bit
  pipeline + HDR chips commercially; not reusable code [S014][S063].
- **WLED 8-bit pipeline: stable-but-stuck** — project is healthy, its color
  pipeline is architecturally frozen at 8-bit with γ2.8 tables; dithering
  request open since 2021 [S054][S066].
- **Native 16-bit chips (WS2816/NS108/HD108): ascendant** — supported by
  Pixelblaze and FastLED; removes the software-fidelity problem where budget
  allows [S063][S065].
- **OKLab for LED blending: ascendant in general computing, unadopted in
  LED land** — zero LED projects found using it; low-risk differentiator
  [S055][S067][S068].
- **CIE-L\* linearization: stable niche knowledge** — 2012/2013 sources still
  the canonical references; correct but rarely shipped (everyone ships gamma
  tables) [S059][S060][S058].

## Code-reading queue

1. **FastLED `src/fl/five_bit_hd_gamma.{h,cpp}`** (FastLED/FastLED@8df8258)
   — verify the closed-form 16→8+5 quantizer against APA102.md's claimed
   0.2% worst-case error; extract the algorithm for pewpew's APA102 driver
   [S053][S008].
2. **Fadecandy firmware `firmware/fc_pixel_lut.cpp` + dither core**
   (pixelmatix/fadecandy@5d76575) — the only complete
   interpolate→LUT→dither firmware; answer: how is the dither residual
   stored/updated per pixel, and how does it avoid flicker at the toe?
   [S062].
3. **Adafruit_NeoPXL8 `NeoPXL8HDR` class** (Adafruit/Adafruit_NeoPXL8) — how
   it schedules dither sub-frames on RP2040 PIO/ESP32-S3 LCD, its gamma
   table format, and the source of the "12–13 bit" effective-depth claim
   [S064].
4. **FastLED `src/fl/gfx/rgbw.*`** — colorimetric DiodeProfile math: is it a
   proper 3×3/4×4 mapping? Reusable for pewpew's calibration story? [S008].
5. **FastLED `controller.h` binary dither counters** — exact bit pattern of
   "binary dithering" and its interaction with `setBrightness` scaling
   [S050][S008].
6. **SmoothLed `SmoothLed.cpp`** (mattshepcar/SmoothLed) — how
   interpolation+dither fits in 2 KB RAM ATtiny; wearable-tier feasibility
   numbers [S019].
7. **WLED `bus_manager.cpp` / NeoPixelBus shader hooks** — confirm absence
   of any per-bus color trim / dither hook in 0.15+, for the comparison
   matrix [S054].

## Open questions

- **Pixelblaze internals** are closed-source: does v3.47+ temporally dither
  8-bit chips, or only widen the internal math? Settle by asking on the
  ElectroMage forum or measuring a WS2812 strip with a photodiode/scope
  [S014][S063].
- **Exact effective-bit gain vs refresh rate**: no source publishes a
  measured curve (bits gained vs Hz vs viewing condition); NeoPXL8HDR's
  "12–13 bits" is the only number [S064]. Settle with a photodiode
  bench test in Phase 2.
- **Chip-internal PWM rates per generation** (WS2812 old/new, SK6812,
  WS2813/15, SK9822 vs APA102 brightness-stage PWM) and their beat
  interaction with dithering — deferred to RA-03; needed to finish the
  refresh-budget table here.
- **WLED per-bus color trim in 0.15+** — code read item 7.
- **OKLab on MCU cost**: no published fixed-point OKLab implementation for
  MCUs found; prototype needed to know if wearable tier can afford it.
- **White-point measurement workflow**: does any tool exist (open) that goes
  colorimeter → correction profile for addressable strips? Nothing found;
  may be a genuine gap pewpew could fill.
- **HD108 16-bit + 5-bit brightness interaction** — whether FastLED/others
  exploit HD108's brightness field the way APA102HD does; RA-03 overlap
  [S100].
