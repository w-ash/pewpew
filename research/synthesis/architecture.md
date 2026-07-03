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

## 5. Parameterization & control plane

Decision ([ADR-006](decisions/ADR-006-parameterization.md)): **one canonical
parameter tree; typed one-line parameter declarations; every knob addressable
and modulatable.**

- **Typed parameter objects, declared in one line** (`Param(default, range,
  label)` as in §3's example): LX/Chromatik semantics — a registered parameter
  automatically gets UI, OSC/MIDI address, and modulation input [S216] — with
  Pixelblaze's zero-ceremony ergonomics (its naming-convention reflection has
  no range/default metadata, which is the gap we close) [S203]. Serialized
  ISF-style so a pattern file is a portable, self-describing document [S214].
  WLED's fixed-slot relabeling (≤5 knobs, uint8 only) is the anti-pattern
  [S206]; LedFx's voluptuous schemas are typed but verbose and static — no
  per-frame modulation [S208].
- **One canonical state tree, partial-merge mutation**: WLED's single JSON
  document, GET/POST over HTTP, identical vocabulary over WebSocket with
  server-push of merged state to all clients — the property that made its
  third-party ecosystem cheap [S550][S551]. No second WS-only vocabulary.
- **Parameters are modulation endpoints**: LFOs, audio features (§7), and beat
  phase patch onto any knob at runtime, DAW-style — LX's `CompoundParameter`
  model [S216]; OSC paths mirror the tree with normalized 0–1 floats, and
  tempo/beat is itself an externally settable parameter [S555]. MIDI-learn
  maps events (not devices) onto the same tree [S556].
- **Live-vs-persisted split**: a `save` flag on mutating commands (Pixelblaze:
  RAM-only by default, flash on request) [S552]; WLED-style named presets
  (preset = any partial state/command) and playlist-as-data
  `{ps, dur, repeat, end}` [S550][S554]. Scheduling stays minimal (boot preset
  + a few timers); calendars are delegated to Home Assistant/cron — FPP-grade
  show scheduling is out of scope [S554][S022].
- **Hub-friendliness**: mDNS/zeroconf advertisement and push-on-change are
  what earn HA's "Local Push" grade; enumerable presets/patterns/palettes are
  what become `select` entities [S553]. Live preview is an opt-in exclusive
  stream (WLED peek `{"lv":true}` / Pixelblaze binary previewFrame), never an
  always-on broadcast [S551][S552].

## 6. Mapping & calibration

Decision ([ADR-007](decisions/ADR-007-mapping-calibration.md)): **a
Chromatik-shaped declarative fixture format authored in physical units,
presented to patterns the Pixelblaze way, compiled to NumPy gathers at load;
marimapper as the external 3D calibration tool.**

- **Native map format**: declarative JSON fixtures — `points` (explicit
  array), `strip` (count + spacing), `arc`, nested/parametric fixtures with
  sequential translate/rotate/scale transforms; physical units (meters),
  y-up right-handed; per-component output bindings with
  start/reverse/stride/repeat. This is the `.lxf` shape, the most expressive
  open declarative format surveyed [S309] — concepts reimplemented from the
  documented spec, no LX code (LX's license is non-commercial-capped [S035]).
  Chromatik's tags/views idea gives masks as first-class named point-subset
  queries instead of `-1` sentinels [S309][S303].
- **Pattern-facing coordinates**: per-pixel normalized 0–1 world units with
  Fill/Contain scaling policy computed at load (Pixelblaze's proven
  portability model [S304]), plus raw physical coords for scale-aware
  effects and wiring index for 1D/index-space patterns — both-raw-and-
  normalized per Chromatik precedent [S309]. Orientation lives in two
  places, deliberately split: geometry transforms (yaw/pitch/roll) vs wiring
  byte-order flags (reverse/stride) — the split only Chromatik gets right
  [S309].
- **Runtime representation**: the map compiles to flat NumPy arrays
  (index→coord table; coord→output-slot gather per sink). LedFx's
  precompiled complex-segments path (claimed up to 13×) is the evidence that
  compiled gathers are the right Python runtime form [S305]
  [S630:ledfx/virtuals.py#L409-L495].
- **Import filters, not format adoption**: WLED `ledmap.json` (index
  permutation + width/height + `-1` gaps) [S303]; Pixelblaze map JSON
  [S304]; marimapper `led_map_3d.csv` (`index,x,y,z,xn,yn,zn,error`; units =
  median LED pitch, sparse missing indices — importer must rescale to meters
  from one measured spacing and preserve per-point error)
  [S670:marimapper/file_tools.py#L68-L85]; xLights `.xmodel` optional for
  the prop ecosystem [S306].
- **Calibration path**: marimapper — actively maintained (v3.4.2,
  2026-03), sequential-blink + COLMAP SfM with LED-IDs-as-keypoints, live
  3D feedback, documented two-method backend API (a pewpew/DDP backend is
  trivial) [S300][S670:marimapper/scanner.py#L48-L115]. GPL-3.0 is a
  non-issue run as a separate program whose CSV pewpew imports; never vendor
  its code [S300]. Its accuracy is unquantified upstream (reprojection error
  only, no metric ground truth [S670:marimapper/sfm_process.py#L135-L157]) —
  bench-test in prototype-to-verify. Built-in fallbacks for the regular-
  geometry 90%: grid/strip generators (Pixelblaze map-generator precedent
  [S304]) and click-on-photo manual mapping [S311].

## 7. Audio

Decision ([ADR-009](decisions/ADR-009-audio-stack.md)): **LedFx-shaped
feature pipeline, reimplemented in NumPy (no GPL imports); features — never
samples — distributed to patterns and nodes.**

- **Capture & analysis**: sounddevice (PortAudio, MIT, maintained [S458])
  at a fixed 60 Hz analysis hop, resampled to a fixed internal rate; one
  shared windowed FFT; 2–3 mel-style filterbanks + named scalars (volume,
  beat/bass/mids/high power, onset, beat-now, bar-phase 0–4) computed
  lazily, cached per hop, shared across all consumers — LedFx's proven
  shape [S011][S630:ledfx/effects/audio.py#L1346-L1354]
  [S630:ledfx/effects/melbank.py#L20-L29]. Cost is a non-issue: FFT+mel
  measured <0.2 ms/hop in NumPy — capture blocksize and WiFi jitter
  dominate, not compute [RA-10 findings].
- **Fix LedFx's structural flaw**: its DSP and all subscriber callbacks run
  inside the PortAudio callback thread
  [S630:ledfx/effects/audio.py#L1138-L1141]; pewpew's callback only copies
  the hop into a ring buffer — analysis runs on the render clock (§4a,
  [ADR-010](decisions/ADR-010-frame-pipeline.md)).
- **License boundary**: melbank/energy-beat/bar-phase math reimplemented in
  NumPy from our documented findings; `aubio-ledfx` (GPL-3.0 [S451]) is not
  imported. aubio upstream is waning anyway (no release since 0.4.9, 2019
  [S452]).
- **Feature bus, not audio bus**: one normalized read-only "sensor frame"
  (melbanks + scalars + IMU) is what patterns see (req W-8) — the
  Pixelblaze sensor-board lesson: features arrive pre-chewed, patterns never
  touch raw audio [S204][S462]. Emit WLED audio-sync V2 (44-byte packed
  struct, port 11988) as a first-class output so every WLED/WLED-MM node on
  the LAN reacts for free [S453]; consume it too (wearable/receiver tiers).
- **Beats**: aubio-style causal tempo + LedFx's energy-beat as default;
  BeatNet behind an optional extra for downbeat/meter (streaming CRNN, but
  drags in PyTorch and is lightly maintained [S457]). madmom rejected
  (unmaintained, PyPI 2018, install pain [S454]); librosa rejected for the
  live path (batch-oriented by design [S456]).
- **Latency & sync**: budget ≤45 ms audio-to-photon (ITU-R BT.1359-1
  detectability edge when audio leads [S459], req P-4/R-4); signed delay
  knob for Bluetooth-delayed speakers, as LedFx ships (0–5000 ms)
  [S630:ledfx/effects/audio.py#L459-L463]. Loudness: fast AGC on band
  energies for reactivity + slow LUFS-style gain riding so quiet tracks fill
  the visual range [S453][S461]. Live song-structure detection is out of
  scope — no production system does it; offline pre-analysis producing cue
  maps is the honest route [S456].
