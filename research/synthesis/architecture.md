# pewpew — recommended architecture

Date: 2026-07-03
Status: Proposed (Phase 3 synthesis). Every major decision links to an ADR in
[`decisions/`](decisions/); requirements referenced as `Q-*/W-*/P-*/R-*` live
in [`requirements.md`](requirements.md).

pewpew is a **Python-first addressable-LED engine** with one pattern contract
spanning three tiers: a host engine (room-scale), dumb network receivers
(portable/room), and an on-device ulab runtime (wearable). Its differentiator
is the union no existing system has (see
[comparison-matrix.md](comparison-matrix.md#what-no-single-system-has--what-pewpew-uniquely-combines)):
live Python pattern authoring, a float-linear quantize-once pipeline, 16-bit
transport, and vectorized execution of a per-pixel authoring surface.

## 1. Overview

```
                             ┌─────────────────────── HOST ENGINE (Python, Pi 5 / mini-PC / laptop) ───────────────────────┐
                             │                                                                                             │
  audio in ──► Feature bus   │   Patterns (pure fns over normalized coords)      Parameter tree (typed params)             │
  (mic/line) │ melbanks,beat │        │  beforeRender(dt) / render(coords)            │  auto UI / OSC / MIDI / HA         │
             └──────────────►│        ▼                                               ▼                                    │
                             │   ┌──────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌────────────────────┐  │
   map file (fixtures,       │   │ evaluate │──►│ composite│──►│ color ops  │──►│ per-sink     │──►│ sinks (self-       │  │
   marimapper CSV import) ──►│   │ NumPy    │   │ layers / │   │ linear f32:│   │ split: pace, │   │ quantizing):       │  │
                             │   │ f32 (N,3)│   │ canvases │   │ correction,│   │ newest-wins  │   │ DDP16/DDP8, sACN,  │  │
                             │   └──────────┘   └──────────┘   │ W-derive,  │   │ backpressure │   │ UPXL serial, GPIO, │  │
                             │                                 │ brightness,│   └──────────────┘   │ preview WS, ANSI   │  │
                             │                                 │ power limit│                      └────────────────────┘  │
                             │                                 └────────────┘                                              │
                             └────────────────────────────────────────────┬────────────────────────────────────┬──────────┘
                                                    unicast UDP (DDP, Push-per-frame)                  websocket │
                                          ┌─────────────────┬─────────────┴──────────────┐                      ▼
                                          ▼                 ▼                            ▼               browser preview
                                   WLED (stock)      Falcon/QuinLED-Octa       pewpew receiver (later:     (three.js
                                   ESP32 receiver    Ethernet controllers      ESP32-S3, interp+dither)    point cloud)
                                   [dumb sink]       [room backbone]           [quality sink]
                                          │                 │                            │
                                       WS281x           WS281x/WS2815              WS281x / HD108

  WEARABLE TIER (standalone, no host): CircuitPython + ulab on RP2350 / nRF52840
    same pattern contract (ulab mirrors NumPy) ──► on-device pipeline (16-bit) ──► PIO/SPI output
    phone tweaks over BLE GATT; baked-frames fallback for patterns outside the ulab subset
```

Tier responsibilities (details in §4):

| Tier | Renders | Quality layer location | Decision |
|---|---|---|---|
| Host engine | Everything for portable/room | Host: float pipeline; receiver: dither where firmware allows | [ADR-001](decisions/ADR-001-internal-color-pipeline.md), [ADR-002](decisions/ADR-002-dithering-strategy.md) |
| Network receivers | Nothing (dumb sinks) — local effects only as fallback | Stock WLED: none (8-bit); pewpew receiver (phase 4): interpolate+dither | [ADR-004](decisions/ADR-004-receiver-strategy.md) |
| Wearable | On-device (ulab) | On-device: 16-bit pipeline + dither at ≥400 Hz | [ADR-008](decisions/ADR-008-wearable-tier-strategy.md) |

## 2. Render pipeline, stage by stage (host tier)

Decision: **float32 linear-light working space, quantize exactly once at the
sink** ([ADR-001](decisions/ADR-001-internal-color-pipeline.md)). This is the
Fadecandy pipeline shape [S600:firmware/fc_draw.cpp#L25-L327] generalized with
HyperHDR's float/driver-self-quantize pattern
[S700:sources/led-drivers/LedDevice.cpp#L625-L678] and Pixelblaze's
16-bit-throughout lesson [S063]; the ordering (correction before curve) follows
Fadecandy's LUT builder [S600:server/src/fcdevice.cpp#L235-L360] (req Q-1, Q-2, Q-7).

| # | Stage | Representation | Notes |
|---|---|---|---|
| 1 | Pattern evaluation | float32 `(N,3)` linear RGB, 0–1; coords float32 `(N,3)` normalized | Vectorized over the whole map ([ADR-005](decisions/ADR-005-pattern-authoring-model.md)); optional OKLab blending helpers convert out to linear RGB per frame — no LED project uses OKLab yet, low-risk differentiator [S055][S068] |
| 2 | Layer compositing | float32 linear | Alpha-over / additive in linear space; layers = canvases mapped onto point subsets (LedFx virtuals model [S305], projectMM layers [S715:docs/architecture.md#L285-L318]); crossfade transitions blend two rendered frames, never two engines (avoid WLED's copy-the-whole-Segment transition [S645:wled00/FX_fcn.cpp#L1330-L1367]) |
| 3 | Color ops (per sink group) | float32 linear | Order: white-point/batch trim (multiplicative [S600:server/src/fcdevice.cpp#L235-L360]) → RGBW W-derivation, colorimetric where profiled (FastLED DiodeProfile direction [S008:src/fl/gfx/rgbw.h]) → master brightness → power limit (estimate-and-scale on linear values, per-chip current model [S413][S645:wled00/bus_manager.cpp#L183-L253], req Q-8) |
| 4 | Perceptual curve | float32 → uint16 | Inverse-CIE-L\*/configurable gamma ≈2.6–3.0 with linear toe, as a 16-bit LUT — the last lossy step (req Q-2) [S059][S061][S600:server/src/fcdevice.cpp#L243-L253] |
| 5 | Sink split + pacing | uint16 per-sink slices | Compiled index gathers per sink (LedFx complex-segments idea, 13× claim [S630:ledfx/virtuals.py#L409-L495]); one paced scheduler, deadline-corrected; newest-wins backpressure per sink ([ADR-010](decisions/ADR-010-frame-pipeline.md)) — Fadecandy's `MAX_FRAMES_PENDING=2` coalescing [S600:server/src/fcdevice.cpp#L362-L382], HyperHDR's latest-wins drop [S700:sources/led-drivers/LedDevice.cpp#L537-L546] |
| 6 | Sink quantization | uint16 → wire | Each sink self-quantizes to the best the wire supports ([ADR-002](decisions/ADR-002-dithering-strategy.md)): DDP 16-bit type passes uint16 through [S150]; DDP/sACN 8-bit sinks apply host-side adaptive temporal error-diffusion (HyperHDR recipe: static-freeze, motion gate, leaky accumulator [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L80-L156]) or 0.49-LSB hysteresis when the output rate is too low to dither [S700:sources/led-drivers/LedDevice.cpp#L633-L658]; UPXL/APA102-family sinks use the five-bit-HD joint quantizer (`S = ceil(max16·31/65536)`) [S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L36-L130] |

Where the *dither loop* runs per tier is the precision-spending decision
([ADR-002](decisions/ADR-002-dithering-strategy.md)): host-side at the sink's
output rate for network receivers today (HyperHDR-style, effective mainly on
slow fades [S700]), device-side at ≥400 Hz on the wearable tier and future
pewpew receivers (Fadecandy/SmoothLed-style, real +2–3 bits
[S600:firmware/fc_pixel.cpp#L58-L88][S716:src/SmoothLed.cpp#L122-L131]), and
**not at all** on 16-bit chips, where native depth replaces it (Pixelblaze's
route [S063][S684], req Q-6).

## 3. Pattern authoring model

Decision ([ADR-005](decisions/ADR-005-pattern-authoring-model.md)): patterns
are **Pixelblaze-shaped, Python-real, NumPy-executed**.

```python
class Comet(Pattern):
    speed = Param(0.5, 0..1, "Speed")          # typed param object → UI/OSC/MIDI (ADR-006)

    def before_render(self, dt, features):     # once per frame: advance state
        self.phase = wrap(self.phase + dt * self.speed)

    def render(self, x, y, z, index):          # pure; x/y/z are ARRAYS (N,)
        return hsv(x + self.phase, 1.0, wave(x * 3 + self.phase))
```

- **`before_render(dt)` / `render(coords)` split** and 0–1 phase idioms
  (`time()`, `wave()`, `triangle()`, `square()`) come straight from Pixelblaze
  [S680:README.expressions.md#L19-L23,L151-L163]; the per-pixel-pure-function
  model survived two independent reimplementations (led-control [S660], ARTI-FX
  [S207]) — strong evidence it is what authors want.
- **Coordinates arrive normalized 0–1 world units**, computed at map-load time
  (Fill and Contain policies; aspect-preserving default — fixing Pixelblaze's
  known distortion gotcha [S680:README.mapper.md#L12-L36][S304]). Raw physical
  coords and wiring index remain available (Chromatik precedent: both raw and
  normalized per point [S309]).
- **Execution is vectorized**: the same author-visible function is called once
  per frame with coordinate *arrays*; scalar-looking NumPy-compatible
  expressions broadcast. Rationale: per-pixel CPython caps at ~22.5k px/s
  [S660:README.md#L17-L24] while vectorization buys ≥10× even on an RP2040
  [S400][S211] ([ADR-011](decisions/ADR-011-language-performance.md)). Whether
  authors trip over branching (`if` vs `np.where`) is a prototype item.
- **Frame buffer persists** (`self.pixels` prev-frame access) for
  trails/decay — LedFx convention [S630:ledfx/effects/__init__.py#L479-L547];
  projectMM learned the hard way that auto-clearing breaks every trail effect
  [S715:docs/history/decisions.md#L540-L549].
- **Errors never stop the show**: per-frame exception containment with a
  visible error state and the last-good pattern kept running — led-control's
  pulsing-red frame [S660:ledcontrol/animationcontroller.py#L418-L434] and
  Pixelblaze's crash-proof editor semantics [S504].
- Sandboxing (RestrictedPython) is **not** adopted for the trusted local case;
  it taxes the hot loop and still can't stop unbounded loops
  [S660:ledcontrol/animationcontroller.py#L228-L282] — patterns are plain
  modules; a future shared-pattern-gallery mode can revisit.

## 4. The tiers

### 4a. Host engine (portable + room)

One Python process: pattern scheduler + parameter tree + feature bus + sinks.
One paced render clock, deadline-corrected (measure elapsed, sleep the
remainder, correct accumulated error) — LedFx/led-control both use compensated
sleeps but without accumulated-error correction, and LedFx's rate drifts with
scheduler jitter [S630:ledfx/virtuals.py#L864-L877][S660:ledcontrol/intervaltimer.py];
LX's fixed-rate executor is the cleaner reference [S264]. No
thread-per-virtual, no DSP in the audio callback — the two LedFx pain points
its own comments document [S630:ledfx/virtuals.py#L746-L779][S630:ledfx/devices/artnet.py#L176-L179]
([ADR-010](decisions/ADR-010-frame-pipeline.md)).

### 4b. Network receivers

Decision ([ADR-004](decisions/ADR-004-receiver-strategy.md)): **stock WLED as
the day-one dumb receiver; Ethernet pixel controllers (Falcon/QuinLED-Octa)
as the room backbone; a custom pewpew receiver firmware is a later phase, not
a prerequisite.** WLED already implements the exact contract needed: DDP ingest
with offset + PUSH render flag, realtime preemption of local effects, timeout
fallback [S645:wled00/e131.cpp#L20-L93][S645:wled00/udp.cpp#L410-L456].
Caveats a pewpew sender must handle: pin receiver brightness to 255 or account
for its scaling (WLED still applies master brightness to realtime data;
gamma is off by default) [S645:wled00/wled.h#L453-L454], and WLED ignores the
DDP timecode flag [S645:wled00/e131.cpp#L63]. The user's Pixelblaze output
expanders are reusable as host-driven dumb sinks over 2 Mbps serial — the UPXL
protocol is open/MIT, CRC-framed, with a DRAW_ALL latch, ~66k px/s per bus
[S682:README.md#L13-L78][S365]. The future custom receiver (ESP32-S3) adds
what stock WLED cannot: device-side keyframe interpolation + ≥400 Hz temporal
dithering — the single biggest unclaimed quality lever in the field
[S600][S054][S251].

### 4c. Wearable tier

Decision ([ADR-008](decisions/ADR-008-wearable-tier-strategy.md)):
**CircuitPython + ulab on RP2350 (non-radio) or nRF52840 (BLE), running the
same pattern contract against ulab arrays; baked-frames (FSEQ-style) fallback
for patterns outside the ulab subset; BLE GATT for phone control.** ulab
deliberately mirrors NumPy's API, so a disciplined pattern subset runs
unmodified on both tiers [S400][S403]. Measured basis: 256 px fire at
~4 ms/frame vectorized on RP2040 [S400] (req W-1/W-2). The device pipeline is
SmoothLed's 5-bytes-per-channel interpolate+dither loop, widened to a 16-bit
entry point [S716:src/SmoothLed.h#L63-L79][S019] (req W-3/W-4). BLE because
ESP32 SoftAP costs ~100–130 mA with no power-save in AP mode, vs µA-class BLE
idle on nRF52840 [S411][S412] (req W-5). Compile-to-VM (Pixelblaze's model
[S681:pixelblaze/pixelblaze.py#L1490-L1512]) is explicitly deferred: highest
performance-per-flexibility but a compiler+VM maintenance burden the evidence
doesn't yet justify.
