# pewpew — recommended architecture

Date: 2026-07-03
Status: Proposed (Phase 3 synthesis). Every major decision links to an ADR in
[`decisions/`](decisions/); requirements referenced as `Q-*/W-*/P-*/R-*` live
in [`requirements.md`](requirements.md).

pewpew is a **Python-first addressable-LED engine** with one pattern contract
spanning four tiers: a host engine (room-scale), dumb network receivers
(portable/room), an on-device ulab runtime (wearable), and an autonomous
mesh-group tier (independent fixtures coordinating leaderlessly over
ESP-NOW, §4d). Its differentiator
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

  MESH GROUP TIER (autonomous fixtures, host optional): ESP32-S3 nodes, local render + 16-bit/dither
    ~11 B state broadcasts (ESP-NOW, 10 Hz) ──► epoch gossip + optional firefly beat ──► coordinated autonomy
    host joins via USB serial-dongle gateway ◄──► fleet; wearables listen via a BLE bridge node
```

Tier responsibilities (details in §4):

| Tier | Renders | Quality layer location | Decision |
|---|---|---|---|
| Host engine | Everything for portable/room | Host: float pipeline; receiver: dither where firmware allows | [ADR-001](decisions/ADR-001-internal-color-pipeline.md), [ADR-002](decisions/ADR-002-dithering-strategy.md) |
| Network receivers | Nothing (dumb sinks) — local effects only as fallback | Stock WLED: none (8-bit); pewpew receiver (phase 4): interpolate+dither | [ADR-004](decisions/ADR-004-receiver-strategy.md) |
| Wearable | On-device (ulab) | On-device: 16-bit pipeline + dither at ≥400 Hz | [ADR-008](decisions/ADR-008-wearable-tier-strategy.md) |
| Mesh group | On-device (S3 firmware), autonomous | On-device: 16-bit + dither, DMA-only output under radio (M-6) | [ADR-014](decisions/ADR-014-mesh-transport.md), [ADR-015](decisions/ADR-015-mesh-coordination.md), [ADR-016](decisions/ADR-016-mesh-gateway-and-bridges.md) |

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

### 4d. Mesh group tier

Decisions ([ADR-014](decisions/ADR-014-mesh-transport.md),
[ADR-015](decisions/ADR-015-mesh-coordination.md),
[ADR-016](decisions/ADR-016-mesh-gateway-and-bridges.md)): **25–50 autonomous
ESP32-S3 fixtures, each rendering locally at ~60 fps with the full quality
pipeline, coordinating leaderlessly over ESP-NOW broadcast — ~11-byte
fixed-layout state frames at ~10 Hz, no ACKs, no membership, no central
clock.** This tier inverts the host-engine relationship: nodes are
self-sufficient by default and the host is an optional guest.

- **Transport**: unencrypted ESP-NOW broadcast on one fixed fleet channel;
  default 1 Mbps carries 50 nodes at ~31 % airtime; the ~150-node ceiling
  requires raising the broadcast TX rate to 6–11 Mbps (still decodable by
  default-config peers) [S806][S817][S811]. Every mesh alternative surveyed
  fails structurally at this workload — softAP+STA trees on root-SPOF and
  scaling collapse, flooding meshes on spec-capped origination rates, LoRa
  on duty-cycle law [S851][S854][S855][S862][S867][S873] (RA-14).
- **Coordination** (ADR-015): parameter state rides every beacon as a
  `(session_id, epoch, params)` LWW register — a state-based CRDT, so every
  node relays without knowing it [S907][S912]; a host edit converges
  fleet-wide in ~200–400 ms at 50 nodes even at 20 % loss [S905][S906],
  which is what makes the §8 live-editing loop reach this tier (M-4). Beat
  phase, when wanted, is a pulse-coupled (firefly) oscillator with reachback
  and stagger — timestamp-free, ms-class, proven convergent under loss
  [S900][S901][S903]. Inter-group waves are gradient/activation fields, not
  literal CA rules (which dissolve under asynchrony [S914][S915]).
- **Node firmware** (RA-16): ESP-IDF 5.5.x; WiFi/ESP-NOW callbacks
  copy-and-enqueue on core 0, render + quantize-once + dither + DMA on
  core 1 [S957][S800]. LED output is DMA-only under active radio — SPI-DMA
  for clocked chips (≥400 Hz with margin at 500 px), LCD_CAM parallel or the
  single RMT-DMA lane for one-wire; interrupt-refilled RMT is disqualified
  by a decade of WiFi-glitch evidence [S963][S964][S955][S951].
- **Host access** (ADR-016): a USB serial-dongle gateway (ESP32-S3 on the
  host, Zigbee-coordinator pattern) bridges the Python control plane into
  the broadcast domain without chaining the fleet to any AP's channel
  [S1001][S1015][S1000]; telemetry returns as slow phase-offset status
  beacons. Fleet OTA is standard dual-slot + rollback in maintenance
  windows — never mesh-gossiped [S1003][S1006].
- **Wearables** (ADR-016): a dedicated non-rendering S3 bridge re-emits
  group state as BLE manufacturer-data advertisements; nRF52840 wearables
  duty-cycle-scan it for ~0.04–0.2 mA — scene/palette/tempo within 1–2 s,
  beat-phase deliberately excluded [S1050][S1051][S1057].

The P-6 hold-and-revert contract generalizes here to the tier itself: with
no host and no gateway, nothing degrades — the fleet keeps coordinating on
the last-set epoch (M-5) [S907][S903].

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

### Trust model (explicit decision)

- **Unauthenticated trusted LAN, by design** — the field norm pewpew's
  entire control-plane precedent set ships (WLED exposes HTTP/WS/UDP with no
  auth by default [S550]); the deployment context is a private LAN/AP the
  operator controls. This is a decision, not an omission: adding day-one
  auth would break the third-party-ecosystem property §5 is built on.
  An opt-in PIN/token gate (WLED-style settings PIN) is the planned later
  hardening for shared-network deployments; anything stronger (TLS,
  per-user accounts) is out of scope for a LAN art tool.
- **Concurrent writers: last-write-wins with server-push merge.** Multiple
  controllers/editors may mutate the tree simultaneously; the server merges
  partial updates in arrival order and pushes merged state to all clients
  [S550][S551], so every client converges on what won. No locking, no CRDTs
  — matching the WLED/LedFx field norm where concurrent control is rare and
  a lost knob-turn is recoverable by turning the knob again.

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
- **Latency & sync**: ≤45 ms audio-to-photon engine design budget inside
  the ≤50 ms hard ceiling (ITU-R BT.1359-1 detectability edge when audio
  leads [S459], req P-4/R-4); signed delay
  knob for Bluetooth-delayed speakers, as LedFx ships (0–5000 ms)
  [S630:ledfx/effects/audio.py#L459-L463]. Loudness: fast AGC on band
  energies for reactivity + slow LUFS-style gain riding so quiet tracks fill
  the visual range [S453][S461]. Live song-structure detection is out of
  scope — no production system does it; offline pre-analysis producing cue
  maps is the honest route [S456].

## 8. Preview & dev loop

The dev loop is a first-class deliverable: Pixelblaze's editor is the UX
benchmark (recompile-and-push on every keystroke; runtime errors surface as
annotations while the last valid pattern keeps running [S504]), and a Python
engine gets that loop cheaper than anyone — no compile step, versus
fastled-wasm's 1–3 s state of the art for compiled LED dev [S500].

Build order (leverage-ordered, from RA-11's recommendation):

1. **Pure render core + preview-as-a-sink.** `render(t, mapping, params,
   seed) → frame` is pure; the preview is just another sink beside DDP/sACN —
   LedFx's dummy device proves this costs ~nothing and is the documented
   no-hardware dev path [S508]. Purity unlocks deterministic scrubbing and
   testing.
2. **Hot-reload with state carry-over.** watchfiles-driven re-import of the
   edited pattern module while the engine keeps running; `t`, parameter
   values, and the frame buffer carry across the swap [S519]. Leaf-module
   re-import, not jurigged-style whole-process hot-patching — patterns are
   small modules with a known interface [S520]. Per-frame exception
   containment per §3 [S504][S660:ledcontrol/animationcontroller.py#L418-L434].
3. **Browser preview over websocket**: serve map positions once, stream
   compact color buffers; 2D canvas first, three.js `Points` cloud when the
   map is 3D (tens of thousands of points at 60 fps is routine WebGL
   [S513]; Chromatik's 3D-first UI is the authoring precedent [S034]).
   Budget the stream deliberately — LedFx's frontend caps at 4096 px with a
   throttle slider [S508]. ANSI terminal preview comes free via the same
   sink interface (ssh/CI) [S514]; xLights' photo-underlay preview is the
   later nice-to-have [S506].
4. **Golden-frame tests from day one.** Fixed seed + fake clock → N frames
   per pattern, compared with perceptual tolerance (pytest-mpl's
   baseline+RMS model [S518]). No surveyed project tests effect output at
   all — LedFx asserts HTTP responses, FastLED tests primitives, WLED has
   no effect tests [S516][S517] — the pure core makes pewpew the first.

Anti-goals: no device emulator before the engine exists (wled-sim's lane
[S511]); no offline pre-render loop (xLights' model — pewpew is a live
engine [S506]).

## 9. What we ADOPT / BUILD / INTEGRATE

License policy ([ADR-012](decisions/ADR-012-pewpew-license.md)): pewpew is
permissively licensed, so **GPL/EUPL/LX-licensed systems are integration
targets and idea sources only — algorithms are reimplemented from the
documented findings in this research tree; their code is never copied or
linked in-process.** This applies to LedFx (GPL-3.0 [S011]), marimapper
(GPL-3.0 [S670:LICENSE#L1-L5]), aubio-ledfx (GPL-3.0 [S451]), WLED
(EUPL-1.2 [S001]), WLED-MM (EUPL-1.2 [S646]), xLights (GPL-3.0 [S026]),
projectMM (GPL-3.0 [S715]), and Chromatik/LX (custom
non-commercial-capped license [S035]). MIT sources (Fadecandy
[S600:LICENSE#L1-L3], FastLED [S008], led-control [S017], pixelblaze-client
[S552], UPXL expander firmware [S682]) could legally be ported with
attribution, but the default is still reimplementation against our documented
findings — the excerpts in `research/excerpts/` exist for verification, not
transplanting.

**ADOPT (use directly, as dependency, tool, or peer device):**

| What | Why | License posture |
|---|---|---|
| NumPy / CircuitPython+ulab | The two-tier array substrate; ulab mirrors NumPy by design [S400][S403] | BSD/MIT — fine |
| sounddevice (PortAudio) | Capture; maintained, NumPy-native [S458] | MIT — fine |
| watchfiles | Hot-reload watcher; de-facto standard [S519] | MIT — fine |
| DDP + sACN/Art-Net wire formats | Protocols, not code [S150][S157] | Specs — fine |
| WLED audio-sync V2 packet format | 44-byte feature struct, port 11988 — wire format only [S453] | Format — fine |
| Stock WLED / WLED-MM firmware | Day-one receivers over the network ([ADR-004]) | Separate device; network boundary |
| marimapper | External calibration tool; pewpew imports its CSV [S300] | GPL, separate process — no obligation |
| Pixelblaze output expanders | Host-driven serial sinks via open UPXL protocol [S682][S365] | MIT — fine |

**BUILD (pewpew's own code, reimplemented from documented findings):**

- Float32-linear quantize-once pipeline, 16-bit perceptual LUT, linear toe
  ([ADR-001]) — technique from Fadecandy/HyperHDR/Pixelblaze findings
  [S600][S700][S063].
- Host-side adaptive temporal dithering + five-bit-HD joint quantizer
  ([ADR-002]) — HyperHDR and FastLED recipes, reimplemented [S700][S615].
- Vectorized pattern engine + authoring surface ([ADR-005]), parameter tree
  ([ADR-006]), mapping compiler ([ADR-007]), paced frame pipeline
  ([ADR-010]).
- NumPy melbank/energy-beat/bar-phase feature bus ([ADR-009]) — LedFx's
  shape, our math [S630][S011].
- Estimate-and-scale power limiter with per-chip current models —
  FastLED's algorithm, reimplemented [S413] (req Q-8).
- Later: pewpew receiver firmware (ESP32-S3 interpolate+dither, [ADR-004])
  and the wearable device runtime ([ADR-008]).

**INTEGRATE (interoperate with, never depend on):**

- WLED ecosystem — DDP out, its JSON API model informs ours [S550][S645].
- LedFx — can coexist as a feature source/peer on the LAN [S011].
- Home Assistant — mDNS discovery + push, WLED-integration-shaped [S553].
- xLights/FPP ecosystem — `.xmodel` import [S306]; FSEQ as the wearable
  baked-frames format [S406][S258].
- Chromatik/LX — `.lxf` concepts clean-roomed from the documented spec
  [S309]; OSC/OSCQuery conventions [S555].

## 10. Buy / avoid hardware list

Decision ([ADR-013](decisions/ADR-013-hardware-bets.md)). Verdicts as of
2026-07; full rationale in RA-03/RA-08/RA-09.

**Chips — buy:**

- SK6812 / SK6812-RGBW (5 V wearable/portable workhorse: 1.2 kHz PWM, small
  packages) [S114][S115]; WS2812B only in current revisions
  (V5/2020-package, ~2 kHz PWM — never legacy 400 Hz stock) [S109][S105].
- WS2815 (12 V RGB room default: per-pixel, backup data line, relaxed
  injection) [S111][S112]; WS2814 (ascendant commodity 12/24 V RGBW — mind
  its color-order trap [S121]) [S119].
- HD107s (vendor-claimed 27 kHz PWM / 40 MHz clock — community measurement
  still pending per RA-03 open questions; 3.3 V-friendly, though the
  documented 3.0 V threshold figure belongs to HD108 — the de-facto APA102
  of 2026) [S101][S102]; SK9822 as the budget clocked part (current-source
  global brightness → flicker-free pseudo-13-bit) [S128].
- HD108/NS108 (16-bit in silicon — ends dithering; FastLED support merged
  2025-10-30; specialty supply) [S130][S100][S131] and WS2816 (16-bit
  one-wire, watch availability [S122][S123]) — the chips the 16-bit pipeline
  exists for (req Q-6).

**Chips — avoid:** genuine APA102 (440 Hz global-brightness PWM; clone
displacement) [S128][S101]; WS2811 3-LED-group strips (displaced) [S126];
legacy-revision WS2812B [S109].

**Receivers/controllers — buy:** classic ESP32 for WLED-upstream duty (its
only production-recommended chip [S351]); ESP32-S3 with PSRAM as the default
new buy and the future pewpew-receiver target (MoonLight's sweet spot
[S352]); QuinLED Dig-Next-2 / Dig-Octa (fused, level-shifted, 5–48 V,
ecosystem fit [S357][S358]); Falcon F16v5 for the Ethernet room backbone
(16×1,024 px, DDP, e-fuses, ~$17.50/port [S359]); Olimex ESP32-POE-class
boards for wired satellites [S351]. Keep and reuse: existing Pixelblaze
output expanders (open protocol, host-agnostic [S365][S682]).

**Receivers — avoid:** ESP8266 (WLED: "should not be used for any new
installations" [S351][S356]); ESP32-C3/S2 (single-core stutter, bad board
revisions [S351]); ESP32-P4 except Ethernet-attached early-adopter use (no
onboard radio; hosted WiFi still flaky [S353][S355]); ESPixelStick (V4 beta
since 2023, niche lost to WLED [S364]); HinksPix (Windows/holiday-show
ecosystem mismatch [S363]). Advatek is fine gear priced for paid installs —
not for this project [S362].

**Mesh-tier nodes & bridges — buy:** ESP32-S3 with PSRAM for every
mesh-tier role — group node, gateway dongle, BLE bridge — one SKU, three
firmwares (fleet fungibility per ADR-016); S3 specifically because it is
"the only chip with RMT DMA" and carries LCD_CAM parallel + a free core for
rendering under radio [S963][S955]. On mesh nodes prefer clocked chips
(HD107s/SK9822) or ≤74 px/line one-wire runs so the ≥400 Hz dither budget
survives (M-6) [S971][S106]. **Avoid** for mesh nodes: ESP32-C3/C6
(single-core, no RMT-DMA/LCD advantage [S1065][S963]); any one-wire run
>300 px/line on a dithered node (≈108 Hz ceiling) [S106][S105]. Toolchain
note: official PlatformIO is waning for Arduino-ESP32 3.x — use ESP-IDF
5.5.x directly or pioarduino [S959][S960][S961].

**Hosts — buy:** Pi 5 or N100-class mini-PC, wired gigabit (req R-8); the
Pi 5's broken native WS2812 output is irrelevant when receivers do the pixel
wiggling [S367][S368]. Pi Zero 2 W only as a per-prop portable host (WiFi-
only, 512 MB [S368]).

**Wearable MCUs — buy:** RP2350 boards for the non-radio core (PIO output +
best interpreted-Python throughput [S410][S403]); nRF52840 (LED Glasses
Driver-class) for the BLE tier — measured best-in-class BLE current
([S412] is a single hobbyist's careful measurement, pending
Nordic/Espressif datasheet corroboration; the direction of the conclusion
is not in doubt) [S412][S416]. 1200–2000 mAh LiPo + JST-PH, software current cap per W-6
[S418][S417]. **Avoid** for all-day on-body: any ESP32 that must keep
SoftAP up (~100–130 mA radio floor [S411]); SAMD21-class legacy wearables
(too slow for the engine [S416]).

**Wiring/power standards:** AHCT125-class shifters as a fixed assumption at
5 V [S133]; ≤10% voltage-drop injection sizing (2.5–5 m at 5 V, 5–10 m at
12 V) [S135][S369]; fuse every power channel [S369]; xConnect pigtails for
all new gear [S370].

## 11. Phased build plan

Ordering rationale: the two riskiest bets (vectorized authoring surface,
Python throughput at scale) are validated before any engine code hardens
around them; everything hardware-custom (receiver firmware, wearable
runtime) comes last because stock WLED and baked frames are adequate interim
carriers ([ADR-004](decisions/ADR-004-receiver-strategy.md),
[ADR-008](decisions/ADR-008-wearable-tier-strategy.md)).

**Phase 0 — de-risk (benchmarks before architecture hardens).**
The two execution-model gates from §12: the NumPy/Numba throughput
microbenchmark (N ∈ {300, 3k, 30k}; no published figure exists at this
scale [RA-05 open questions]) and a ~5-pattern prototype of the
scalar-looking-over-arrays authoring surface, including the `if` vs
`np.where` branching question ([ADR-005], [ADR-011]). Failure here changes
ADR-011 (Numba/compiled tier promoted from optional to required), not the
product shape. **Feedback before features**: the test-harness skeleton
(golden-frame loop, fake clock, fleet-twin interfaces) is already landed in
`harness/`; Phase 0 also assembles the ~$200 bench core
([ADR-018](decisions/ADR-018-agent-driveable-bench.md)) so every later
phase's §12 items run as scripted rigs, not lab afternoons (§13).

**Phase 1 — host engine core, end-to-end on real LEDs.** Pure render core
(`render(t, mapping, params, seed)`), pattern contract (§3), typed params
(§5), preview-as-a-sink + ANSI sink, hot reload with state carry-over (§8),
one paced clock ([ADR-010]), DDP 8-bit out to a stock WLED node
([ADR-003], [ADR-004]). Golden-frame tests start here, not later (§8).

**Phase 2 — the quality pipeline.** Float32-linear stages 1–6 of §2:
16-bit perceptual LUT + linear toe, white-point trim, estimate-and-scale
power limiter, host-side adaptive dithering for 8-bit sinks, DDP 16-bit
sink, five-bit-HD quantizer for APA102-family via the UPXL expander sink
([ADR-001], [ADR-002]). Photodiode bench rig built here (it settles three
§12 items).

**Phase 3 — control plane, audio, mapping.** HTTP+WS JSON tree, presets/
playlists, OSC + MIDI-learn, mDNS/HA (§5); feature bus + WLED sync V2 out
(§7, [ADR-009]); fixture format, map compiler, marimapper import + pewpew
backend, three.js 3D preview (§6, [ADR-007]).

**Phase 4 — the custom hardware tiers.** Wearable runtime: ulab pattern
subset, device pipeline (16-bit interpolate+dither), BLE GATT control,
FSEQ-style baked-frames fallback ([ADR-008]). pewpew receiver firmware
(ESP32-S3): DDP16 ingest, keyframe interpolation + ≥400 Hz device-side
dithering — the field's biggest unclaimed quality lever [S600][S054][S251]
([ADR-004]).

**Phase 5 — the mesh group tier.** Builds on the Phase-4 receiver firmware
(same S3 render/dither core): ESP-NOW state radio + epoch gossip
([ADR-014], [ADR-015]), gateway dongle firmware + host-side serial driver
([ADR-016]), the coordination simulator in the §8 preview harness (the CA/
gradient-field aesthetics sweep is a preview-side deliverable, not
firmware), then the optional firefly beat layer and the wearable BLE
bridge. Mesh benches (§12 items 15–20) gate the fleet buy, not the design —
25–50 nodes at defaults is already inside the evidence.

## 12. Prototype-to-verify

Claims the research could not settle from sources — only a bench settles
them. Drawn from the topic docs' open questions; requirement IDs link back
to [requirements.md](requirements.md).

| # | Claim to verify | Gap | Bench |
|---|---|---|---|
| 1 | A NumPy engine sustains ≥20k px × 60 fps on a Pi 5-class host (R-9) | No published NumPy LED benchmark at 5k–50k px anywhere [RA-05] | Microbenchmark: per-pixel loop vs NumPy vs Numba, N ∈ {300, 3k, 30k}, desktop + Pi 5 |
| 2 | Authors tolerate the vectorized surface (scalar-looking code over arrays) | No prior art in the LED space [RA-05] | Write 5 canonical patterns (fire, comet, plasma, GEQ, 3D SDF); count `np.where` stumbles |
| 3 | DDP broadcast-Push latches N WiFi receivers within ≤1 frame (R-10, R-5) | No source measures real Push skew [RA-04][S150] | 3+ ESP32s + photodiode/logic-analyzer rig (method of [S166]) |
| 4 | Stock WLED/WLED-MM handling of 16-bit DDP (truncate? dither?) | Listed as a format [S152]; behavior unverified [RA-04] | Code read of the DDP ingest path + on-device test |
| 5 | Dither effective-bit gain vs refresh rate (Q-3, W-3) | Only figure is NeoPXL8HDR's "12–13 bits" [S064]; no measured curve [RA-02] | Photodiode bench: bits gained vs Hz on WS2812/SK6812 |
| 6 | ≤45 ms audio-to-photon is met; whether ~30 ms is the real "tight" edge (R-4, P-4) | 30 ms is uncited folklore [S459][RA-10] | Click-to-photodiode latency rig + small variable-delay user test |
| 7 | marimapper accuracy is adequate (§6) | Upstream publishes no error figures [S300][RA-07] | Map a known-geometry grid; compute RMS vs ground truth |
| 8 | RP2350 runs the ulab contract ~2× RP2040 (W-1, W-2) | Inferred from vendor pages, not benchmarked [S403][RA-09] | Run the fire benchmark [S408] on RP2350 |
| 9 | BLE pattern push is seconds, not minutes (W-5) | FileTransferService is "simple (not fast)" — no KB/s figure [S407][RA-09] | Push a 100 KB pattern via FileTransferService; measure |
| 10 | One AP sustains enough 60 fps unicast streams for a room (R-1, R-5) | Community guidance qualitative only [S165][RA-04] | Airtime math + incremental-receiver soak test |
| 11 | Device-side keyframe interpolation is invisible at host rates ≥30 fps (Phase 4 receiver) | No primary source on the threshold [RA-06] | Vary keyframe rate on the interp+dither receiver; observe fades |
| 12 | OKLab blending is affordable on the wearable tier (§2 stage 1) | No fixed-point MCU OKLab implementation found [RA-02] | ulab OKLab µbenchmark on RP2350 |
| 13 | CPython paces a 16.7 ms tick with low jitter under real load (ADR-010's silent dependency: GC pauses, GIL contention with the capture thread, sleep quantization) | Item 1 benches throughput, not pacing jitter; cadence consistency is what device interpolation is hostage to [RA-06] | 10-min soak of the paced loop on Pi 5, tick-error histogram (p99 vs 16.7 ms) with GC active + audio thread running |
| 14 | One stock WLED node sustains 60 fps unicast DDP ingest at its assigned pixel count (ADR-004's day-one Phase 1 path) | Item 3 benches Push skew, item 10 AP capacity — nothing benches per-receiver sustained ingest on real firmware [RA-04] | One ESP32 + one S3 WLED node, 60 fps unicast DDP at 300/800/2000 px, measure delivered fps/drops |
| 15 | ESP-NOW broadcast delivery holds at fleet load (M-1): the 31 %-@50-nodes airtime figure is computed, not sniffed; hidden-node and beacon-phase-alignment behavior unknown [RA-13] | Only published fleet datapoint is a bot-walled 13-node/~20 %-loss report [S816][NEEDS-VERIFICATION] | 10–20 S3 senders × 11 B × 10 Hz, monitor-mode sniffer counting per-sender PDR at 1/6/11 Mbps; three-cluster hidden-node variant; fixed vs ±10 % jittered timers |
| 16 | Timestamp-free firefly beat phase reaches tens-of-ms spread and converges in tens of periods at 25+ nodes (ADR-015 Layer 2) | µs-class literature results all use MAC timestamps [S901]; the ms-class claim is reasoned from RA-13 latency, not measured [RA-15] | N nodes running staggered-reachback PCO, GPIO toggled at each local downbeat, logic analyzer measures group spread vs node count and load; also settles whether the tx-done callback yields a usable timestamp |
| 17 | S3 LED output is glitch-free under mesh radio for weeks, and LCD X8 cadence fits SK6812 timing (M-6) | RMT-DMA has open board-specific bugs [S965][S966]; LCD T0H ≈417 ns is marginal for some one-wire variants [S956][RA-16] | 2-week soak: RMT-DMA + LCD X8 + SPI-DMA outputs with ESP-NOW 10 Hz + STA traffic, logic analyzer on data lines; SK6812 datasheet-window check |
| 18 | 16-bit pipeline + dither costs ~13 % of one S3 core at 500 px/400 Hz (M-6) | No published benchmark of HD-gamma/dither cost on any ESP32 exists (searched 2026-07-09) — the figure is arithmetic [RA-16] | Cycle-count the quantize+dither loop on S3 (FastLED five_bit_hd_gamma as reference), with radio active |
| 19 | Gateway command path is low-single-digit ms, and the fallback STA gateway actually receives broadcasts (ADR-016) | No published S3 USB-CDC round-trip figure; the STA BSSID broadcast-filter claim is disputed and would silently break the fallback's RX path [S1002][RA-17] | 30-min bench: host→dongle echo timestamps; two-board test of broadcast RX while STA-associated on IDF 5.x |
| 20 | The BLE bridge misses <~20 % of mesh broadcasts while advertising, and a wearable scan-while-render holds 60 fps at ~0.2 mA (M-9) | Coexistence matrix says "stable" but publishes no loss numbers [S1053]; no data on CircuitPython scan-under-render jitter [S1062][RA-18] | Two-node bridge bench with counters both sides (escalate to two-chip UART bridge if worse); fire benchmark + 30 ms/1 s scan on Feather nRF52840 with PPK2 on the rail |

Items 1–2 and 13 gate Phase 1 (13 gates ADR-010); 3–6 and 14 gate Phase 2/3
defaults (14 gates ADR-004; they can only *retune* constants, not change
structure); 7–12 gate Phase 3/4 details; 15–20 gate Phase 5 (the mesh tier:
15–16 gate ADR-014/015 constants at the ceiling, 17–18 gate M-6 output-driver
choices, 19–20 gate ADR-016's fallback gateway and bridge dispositions — none
change the tier's structure at the 25–50 node design target).

Every item is mapped to a feedback-pyramid level and marked one-off vs
permanent rig in [test-and-feedback.md §4](test-and-feedback.md); the
permanent rigs are the bench's standing capabilities ([ADR-018]).

## 13. Test, feedback & resilience architecture

Decisions ([ADR-017](decisions/ADR-017-simulation-first-testing.md),
[ADR-018](decisions/ADR-018-agent-driveable-bench.md),
[ADR-019](decisions/ADR-019-resilience-policy.md)); full design with
requirements (T-1…T-10) in **[test-and-feedback.md](test-and-feedback.md)**.
The one-paragraph version:

Development feedback runs on a five-level pyramid — pure-Python golden
frames and property tests (ms; already landed in `harness/`), the
deterministic **fleet digital twin** (the mesh tier simulated with
seed-derived fault injection; same seed → same trace), a thin emulation
tier (QEMU-S3/Wokwi for firmware logic; **no emulator exercises ESP-NOW**
[S1113][S1106], so the radio is the sim/HIL boundary), the **agent- and
CI-driveable bench** (pytest-embedded + scripted instruments; pass^k
statistical gating, never session-blocking [S1154]), and read-only fleet
telemetry. Coding agents get one allowlisted verify verb per level with
`--json` output and machine-readable failure artifacts [S1150][S1168];
hardware actuation is tiered (bench allowlisted + dry-run + audit; deployed
fleet read-only, always). Resilience over perfection is policy ([ADR-019]):
a four-rung local-decision degradation ladder, reboot-don't-wedge watchdog
discipline, black-box forensics on every node, pinned-canary rollout rings
with zero-unexpected-reset promotion gates, chaos drills that test
ADR-015's convergence claims as falsifiable hypotheses, and burn-in +
Poisson-sized spares (swap-don't-debug).
