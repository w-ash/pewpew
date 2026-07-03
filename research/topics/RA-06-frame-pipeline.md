# RA-06: Frame pipeline & motion quality

Last researched: 2026-07-03
Status: draft
S-ID block: S250–S299

## Key questions

1. What exactly is Fadecandy's keyframe-interpolation + dithering model (rates, math, protocol)?
2. Who else decouples render rate from output rate (WLED? Pixelblaze HDR drivers? SmoothLed?)
3. How do software engines pace frames (LedFx loop, led-control scheduler)? Fixed tick vs free-run?
4. How is frame pacing handled over lossy UDP — drop, hold, or extrapolate?
5. Multi-device sync state of the art: FPP MultiSync, WLED UDP sync, xLights FSEQ timing.
6. Does anyone do proper sub-pixel motion / spatial antialiasing along a strip?
7. Easing/motion-curve norms in LED frameworks.
8. What fps do quality installations target, and why?
9. => What pipeline stages must pewpew have?

## Findings

### Fadecandy: the canonical interpolate+dither pipeline

Micah Elizabeth Scott's Fadecandy (MIT; original repo deleted, mirrored at pixelmatix/fadecandy, last push 2020-12-23 — **dead upstream but the design remains the reference**) is the clearest articulation of a two-rate pipeline: the host renders at whatever rate it can, the device treats every completed host frame as a *keyframe* and synthesizes intermediate frames at its own much higher output rate [S015][S062].

The device-side pipeline stages, per the firmware README [S062:README.md]:

1. **Expand** 8-bit host framebuffer values to 16-bit.
2. **Interpolate** linearly between the previous and current keyframe. "The interpolation duration is determined by the elapsed time between when the final packet of one frame is received and when the final packet of the next frame is received" — i.e. the device *measures* the host's frame cadence and stretches each transition over exactly that duration; no explicit timestamps are sent [S062:README.md]. This works best when host frames arrive at a consistent rate.
3. **Color LUT**: three per-channel tables of 257 entries × 16 bits each, applied with linear interpolation between entries; carries gamma, brightness/contrast, and white-point correction in one lookup [S062:doc/fc_protocol_usb.md].
4. **Temporal dither** the 16-bit result down to the LED's 8-bit PWM: "a form of delta-sigma modulation. It rapidly wiggles each pixel's value up or down by one 8-bit step, in order to achieve 16-bit resolution for fades" [S062:README.md].
5. **Format + stream** to OctoWS2811-style DMA output.

Output rate: for 64 WS2811 LEDs "the theoretical maximum frame rate for 64 LEDs is 507.6 FPS"; "The Fadecandy Controller actually gets more like 425 FPS most of the time, since the CPU speed tends to be the limiting factor" [S062:README.md] — this is the origin of the "device dithers at ~400 Hz while the host sends 30–60 fps" model [S016].

Protocol (USB, 64-byte packets): control byte = 2-bit type (0 video / 1 LUT / 2 config), a "final" bit, 5-bit packet index; up to 21 RGB pixels per video packet, 25 packets per 512-LED frame. "When you complete a frame, the firmware immediately begins interpolating to it." Config packet bit 0 disables dithering, bit 1 disables keyframe interpolation — both are opt-out, on by default [S062:doc/fc_protocol_usb.md].

**Architectural takeaways for pewpew:** (a) interpolation state, the LUT, and dithering all live *on the device*, adjacent to the output DMA — the host link only needs ~30–60 keyframes/s; (b) keyframe duration inferred from arrival cadence is simple but makes motion quality hostage to host jitter (see Open questions); (c) dithering requires the high device-side refresh to be effective — the two features are coupled.

### SmoothLed: Fadecandy technique on tiny MCUs

SmoothLed (mattshepcar, MIT-era hobby lib for AVR 0/1-series ATtiny, e.g. ATtiny1614 with megaTinyCore) reimplements the Fadecandy recipe — interpolation for "smooth fades and no 'stair stepping' effect", gamma LUT (`setGammaLut`, with a Python generator script), and temporal dithering — on a sub-dollar MCU using SPI/USART-MSPI plus CCL peripherals for waveform generation [S019]. Its README independently corroborates the refresh-rate coupling: "To benefit from temporal dithering the LED strip must be updated at a high frequency, preferably above 400Hz", and exposes `setDitherMask` to trade dither depth against low-intensity flicker at lower refresh rates [S019]. Form-factor evidence: the interpolate+dither stage fits comfortably in the wearable tier; it is not inherently a big-controller feature. Maintenance: hobby project, low activity — treat as technique documentation, not a dependency [S019][NEEDS-VERIFICATION on exact last-commit date].

### Pixelblaze: free-running pipelined render, HDR depth instead of dithering

Pixelblaze (closed firmware, ESP32) is the counter-model to Fadecandy: **render rate = output rate**, no device-side interpolation. Ben Hencke: "Pixelblaze renders as fast as the cpu and pixels can keep up. It will stall a frame if it is still busy sending data out", and recent firmware "now pipelines ws2812, rendering the next frame as the last one streams out" [S250]. Overdrawing is possible when an output expander is unbalanced — "In that case it skips frames" [S250]. So the pacing strategy is: free-run, backpressure from the output driver, drop on overdraw.

On dithering, Hencke explicitly declined the Fadecandy route: "Temporal dithering only works well if you can refresh the LEDs at very fast rates" (why Fadecandy caps strings at 64 LEDs); he instead "tend[s] to gravitate toward the APA102/SK9822 type LEDs that have even better brightness range (via global brightness data) than possible with temporal dithering on WS2812s", though he conceded Fadecandy-style dithering + keyframe interpolation "would be a cool feature to add" for short WS2812 runs [S251]. The v3.47 release (the current expression of that philosophy) "now supports full HDR 48-bit color using WS2816 and NS108 LEDs" — i.e. smooth fades via *native 16-bit-per-channel LED chips*, not via temporal tricks; a user reported WS2815 throughput rising from "12-24 fps to 23-38 fps ... with 864 LED" on one output [S014]. The release post itself contains no dithering/interpolation detail [S014].

**Takeaway:** there are two roads to fade smoothness — add temporal machinery (Fadecandy) or buy bit depth in silicon (Pixelblaze HDR, APA102 global brightness). Pixelblaze demonstrates a quality engine can skip interpolation entirely *if* it renders fast enough that keyframes are dense (100+ fps rendered on-device). Interpolation matters most when render or transport is the bottleneck — which is exactly pewpew's host-driven case.

### WLED: fixed ~42 fps tick, no interpolation, hold-on-loss

WLED (EUPL-1.2; very active, 0.16 cycle in 2025–26 [S001][S002]) renders effects on a main-loop tick against a configurable "Target FPS" whose intended default is 42 (frametime constant `1000/42` ms); a 2026 bug report shows it accidentally defaulting to 0 = "unlimited," labeled "not recommended, experimental" [S252]. There is **no render/output decoupling**: the effect frame written into the segment buffer is the frame clocked out; no device-side interpolation between frames exists. The community request to add Fadecandy-style temporal dithering + keyframe interpolation (issue #2416, open since 2021) is tagged "backburner," with the discussion noting dithering "requires quite high refresh rates" and effectively ≤64 LEDs per line — structurally at odds with WLED's long-single-pin-strip usage [S054].

In UDP realtime mode (WARLS/DRGB/DRGBW/DNRGB), WLED's loss strategy is **hold-then-revert**: a header byte "tells the server how many seconds to wait after the last received packet before returning to normal mode" (recommended 1–2 s; 255 = stay in realtime indefinitely). No interpolation, extrapolation, or smoothing of incoming realtime streams is documented; incoming pixels get current brightness + gamma applied and are shown as-is [S253].

**Form-factor:** room-scale/architectural mainstay; the 42 fps ceiling and absence of interpolation is the quality gap pewpew targets.

### Software frame clocks: LedFx, led-control

Both leading Python engines use the same primitive: **one thread per output group, running a compensated sleep loop at a fixed target fps**. Neither decouples render from output, and neither interpolates.

**LedFx** (GPL-3.0; very active, pushed 2026-07-03): each `Virtual` runs `thread_function()` — render (`assemble_frame`) + send (`flush`) under a lock, then `time.sleep(max(0.001, fps_to_sleep_interval(refresh_rate) - run_time))`, i.e. sleep compensated by the measured frame-assembly time, plus a Windows-specific adaptive re-sleep against the OS clock resolution [S254:ledfx/virtuals.py#L832-L877]. The tick rate is `refresh_rate = min(device.max_refresh_rate for device in self._devices)` — the *slowest device in the virtual sets the clock* [S254:ledfx/virtuals.py#L1313-L1317]. Effect-to-effect changes are smoothed by a configurable crossfade (`transition_time`, default 0.4 s, modes from a `Transitions` enum) rendered in software — transition smoothing, not motion interpolation [S254:ledfx/virtuals.py#L77-L88]. Dead code in the file (commented-out `interp_channel`/`interpolate` helpers) shows pixel-count interpolation was once present at flush and removed [S254:ledfx/virtuals.py#L993-L1012].

**led-control** (MIT; effectively dormant — last push 2023-11-10): `AnimationController` uses an `IntervalTimer` thread — measure `cycle_time` for render+output, `wait = interval - cycle_time` (clamped ≥ 0), plus a Windows variant compensating against loop-start drift; default `--fps 60` [S255:ledcontrol/intervaltimer.py][S255:ledcontrol/__init__.py#L19-L20]. Pattern functions receive `(t, dt, x, y, z)` so animation position is derived from a running clock, not frame counts — meaning a dropped/late frame slows nothing, it just samples the animation later (time-based, frame-rate-independent animation) [S017].

**Takeaway:** the Python state of the art is a compensated fixed-tick loop with time-parameterized patterns. Nobody in this tier does render-ahead, frame queues, or interpolation; jitter tolerance comes entirely from time-based pattern parameterization. A pewpew scheduler should at minimum match compensated-tick + time-parameterization; device-side interpolation is what would exceed the field.

### Frame pacing over lossy UDP: universal answer is hold-last-frame

No surveyed system extrapolates or interpolates through packet loss. The field-standard behaviors:

- **Hold + timeout revert (WLED realtime):** show last received frame; after a sender-specified timeout (1–2 s typical) fall back to local effects [S253].
- **Sequence numbers for reorder/dup detection, not recovery (DDP):** DDP carries a 4-bit sequence number (1–15, 0 = unused); "a sender can send duplicate packets with the same sequence number ... for redundancy. a receiver can ignore duplicates received back-to-back" — i.e. loss mitigation by blind retransmission, still no reconstruction [S150]. DDP was explicitly designed because DMX-over-IP had "no methods for display synchronization" [S150].
- **Atomic frame latch (DDP Push, E1.31 sync):** DDP's Push flag decouples *fill buffer* from *display buffer*: data packets fill, a (possibly broadcast, data-less) Push displays everywhere simultaneously; optionally a Push carries an NTP-format timecode telling devices "at what future time to do the final Push," requiring NTP-synced devices [S150]. ANSI E1.31-2016 added the equivalent Universe Synchronization packet: data packets advertise a Synchronization Address, and receivers latch buffered data only when the sync packet for that address arrives [S259]. Both solve *tearing across universes/devices*, not loss.

**Takeaway:** the transport-level toolkit is (a) fill-then-latch to prevent tearing, (b) hold-last on loss, (c) sender-side redundant retransmit. Anything smarter (device-side extrapolation, keyframe interpolation across a lossy link à la Fadecandy-over-UDP) is unoccupied territory — and Fadecandy's model maps naturally onto it, since a lost keyframe just lengthens one interpolation interval instead of freezing motion.

### Multi-device sync: FPP MultiSync, WLED UDP sync, xLights/FSEQ

Three distinct sync models exist in the field, at three levels of abstraction:

**1. FPP MultiSync — playback-position sync.** FPP (GPL-2.0 core; actively maintained) syncs a *master timeline*, not pixels: UDP port 32320, multicast 239.70.80.80, "FPPD"-header packets. A sync packet (type 0x01) carries Sync Action (Start/Stop/Sync/Open), Sync Type (0x00 FSEQ / 0x01 Media), a 4-byte frame number, "seconds elapsed as float," and the sequence filename [S256]. Every remote plays its own local copy of the sequence; the master periodically republishes its position and remotes adjust playback speed/position to track it. Send frequency and the remotes' catch-up algorithm (slew vs skip) are **not in the protocol doc** — code-reading item [S256][NEEDS-VERIFICATION].

**2. WLED UDP sync — state sync only.** The WLED UDP notifier broadcasts a ~24-byte state packet: brightness, primary/secondary color, effect index/speed/intensity/palette, nightlight — receivers re-render locally from that state. "The documentation does not describe how timing synchronization works" because there is none: no frame numbers, no clocks; effects on two devices run the same effect but free-run on local clocks [S257]. Good enough for "matching vibes," not for a coherent animation spanning devices.

**3. xLights/FSEQ — pre-rendered fixed-timebase frames.** FSEQ v2 is a baked frame stream: header carries a uint8 "Frame timing interval in milliseconds" at byte 18 (50 ms = 20 fps, 40 ms = 25 fps, 33 ms ≈ 30 fps), uint32 frame count, uint32 channel count, optional zstd/zlib chunk compression [S258]. The whole holiday-lighting ecosystem (xLights render → FPP playback [S026][S022]) therefore runs at a *fixed authoring-time frame rate*, typically 20–40 fps, with sync achieved by everyone indexing into the same file by frame number [S256][S258]. Motion quality is capped at author fps; no player-side interpolation is documented anywhere in this stack.

**Takeaway:** position-sync of independently-rendering nodes (FPP model) is the strongest prior art for pewpew multi-device sync — it tolerates lossy transport (a missed sync packet costs drift correction, not frames) and needs only ~1 packet/s class bandwidth. Streamed-pixel sync (E1.31/DDP) instead makes the network the frame clock, inheriting its jitter.

### Sub-pixel motion & spatial antialiasing

Sub-pixel motion on strips is a *known but manual* technique, not a pipeline stage anywhere:

- **The canonical demo** is Mark Kriegsman's "Anti-aliased light bar" (Nov 2013): position tracked in 1/16ths of a pixel, edge pixels lit proportionally to fractional coverage; his comments call 16ths "a good balance of data size, expressive range, and code size and speed" and the point is explicitly that the fractional bar "moves much more smoothly" than the integer one at identical speed [S260]. This is coverage-weighted box filtering, applied per-effect by hand.
- **FastLED (MIT, very active 2026)** recently promoted this to library machinery: the `fl::` namespace has sub-pixel rendering with "floating point x,y coordinates and splatting pixels to a 2x2 tile," giving "256 effective steps in the X and Y directions between neighbors," plus `XYPath` rasterization to a sparse raster for trails/curves [S261]. This is the only surveyed framework where sub-pixel drawing is a first-class primitive.
- Shader-style engines (Pixelblaze, led-control) get a *related* benefit for free: patterns are continuous functions of normalized position sampled at each pixel, so smooth functions produce smooth spatial gradients [S200][S017]. But point sampling a hard edge still aliases; nobody band-limits/prefilters pattern functions.

No engine filters *temporally* (motion blur) either. Fadecandy's interpolation is temporal smoothing of pixel values, which incidentally approximates sub-pixel motion for slow movement — its README's whole demo is a slow fade looking continuous [S062:README.md].

### Easing norms

Easing is ubiquitous as a *pattern-authoring* utility, absent as a pipeline feature. FastLED's lib8tion ships fixed-point `ease8InOutQuad` (x² piecewise), `ease8InOutCubic` (3x²−2x³, i.e. smoothstep), `ease8InOutApprox` (fast approximation), and 16-bit variants [S262:src/lib8tion.h#L139-L531]. Pixelblaze's idiom is waveform helpers — `wave()`, `triangle()`, `square()` of a time phase — rather than named easing curves [S200]. LedFx's only engine-level easing is the effect-transition crossfade (default 0.4 s) [S254]. The norm: smoothstep-class in/out curves plus periodic waveforms, computed in the pattern; no framework applies easing to motion on the author's behalf.

### Target frame rates in quality installations

- **Holiday/show ecosystem (xLights→FSEQ→FPP):** 20 fps (50 ms) was the long-time norm; current practitioner advice is 40 fps (25 ms) for dense/HD modern displays, with 20 fps sequences still common and importable [S263]; FSEQ's uint8 ms step time structurally caps this class at 1000 fps but in practice 20–40 [S258].
- **Live/interactive engines:** Chromatik/LX defaults to 60 fps (`BoundedParameter("FPS", 60, 1, 300)`) on a fixed-rate scheduled executor with a separate 60 Hz input-event tick [S264:src/main/java/heronarts/lx/LXEngine.java#L109-L110]; led-control defaults 60 [S255]; WLED defaults 42 [S252]; LedFx runs at the slowest member device's max refresh [S254].
- **Pixelblaze markets "hundreds of frames per second"** rendered on-device; users report 100+ fps on mid-size strips [S250][S013].
- **Rationale seen in sources:** higher fps buys (a) smoother motion at 8-bit depth without interpolation, (b) lower latency for audio-reactive work (WLED audio sync recommends only 15–30 fps for the *audio data* stream [S253]), (c) strobe/persistence effects [S250]. Fadecandy's position is that past ~30–60 host fps, extra *content* frames matter less than device-side interpolation+dithering quality [S062:README.md][S016].

### Implications: pewpew pipeline stages

Evidence-backed stage list for a host-driven pipeline that would match or beat the field:

1. **Pattern evaluation, time-parameterized** — patterns as functions of `(t, x…)` so motion speed is independent of achieved frame rate (led-control, Pixelblaze norm) [S017][S200].
2. **Host frame clock: compensated fixed tick** at a configurable target (42–60 fps norm; LX's `scheduleAtFixedRate` + measured actual-fps reporting is the cleanest reference) [S264][S254][S255].
3. **Sub-pixel-aware drawing primitives** (fractional bars / 2×2 splat) so 1D/2D motion isn't quantized to pixel steps — only FastLED offers this today; cheap differentiation [S260][S261].
4. **Transport with fill-then-latch semantics + sequence numbers** (DDP push flag model) to avoid tearing and detect loss [S150]; hold-last-frame on loss with timeout fallback (WLED precedent) [S253].
5. **Device-side keyframe interpolation + LUT + temporal dithering** at ≥400 Hz output where hardware permits (Fadecandy/SmoothLed model) — the single biggest unclaimed quality lever, absent from WLED/LedFx/Pixelblaze-WS2812 paths [S062][S019][S054][S251]. On 16-bit chips (HD108/WS2816) the dither stage can be replaced by native depth (Pixelblaze HDR route) but interpolation is still needed when host fps < output Hz [S014][S251].
6. **Multi-device: sync playback position (or a shared clock), not pixels** — FPP MultiSync model; NTP/timecode latch (DDP) for tight cross-device simultaneity [S256][S150].

## Verdicts

- **Fadecandy technique (interpolate+dither):** ascendant *as a technique*, dead as a product — original repo deleted, mirror frozen 2020 [S015][S062]; still requested in WLED (open issue since 2021) [S054] and reimplemented on modern MCUs (SmoothLed) [S019]. Build on the idea, not the code.
- **Free-run pipelined render (Pixelblaze):** stable, proven; closed-source; its HDR-chip direction (48-bit WS2816/NS108) is ascendant [S014][S250].
- **Fixed-tick no-interpolation loops (WLED/LedFx/led-control):** stable and dominant; motion quality plateaued — the gap pewpew exploits [S252][S254][S255].
- **FSEQ/MultiSync show stack:** stable, entrenched in holiday domain; fixed 20–40 fps authoring model is waning for high-density work only in the sense that fps creeps up [S258][S263][S256].
- **E1.31 sync / DDP push+timecode:** stable specs; DDP ascendant among hobby controllers for its simplicity [S150][S151][S259].
- **FastLED sub-pixel/`fl::` raster work:** ascendant — active 2025–26 investment in exactly the motion-quality primitives this RA cares about [S261][S008].

## Code-reading queue

1. **pixelmatix/fadecandy — `firmware/fc_pixel_lut.cpp`, `firmware/fc_dither.cpp` (or equivalents) + `server/`** — exact interpolation coefficient math, dither error-feedback form, and how the server paces USB keyframes; answers "what does a correct device-side interpolate+dither loop look like, byte for byte" [S062].
2. **FalconChristmas/fpp — `src/MultiSync.cpp`, `src/Sequence.cpp`** — sync packet send cadence and the remote's catch-up policy (slew vs frame-skip thresholds); answers the biggest hole left by ControlProtocol.txt [S022][S256].
3. **FastLED — `src/fl/xypath*.{h,cpp}`, raster/splat code** — how 2×2 splatting and sparse rasters are implemented and what API shape works for sub-pixel drawing [S008][S261].
4. **heronarts/LX — `LXEngine.java` double-buffering (`Frame`/buffer swap around L1283+) and OSC/output timing** — how a mature 60 fps engine isolates render thread from output/UI threads [S264].
5. **mattshepcar/SmoothLed — `SmoothLed.cpp` interpolation inner loop** — minimal-footprint (AVR) formulation of interpolate+dither; sizing evidence for wearable tier [S019].
6. **LedFx — `ledfx/transitions.py`** — transition mode catalog worth matching for effect crossfades [S254].

## Open questions

- **FPP MultiSync cadence & correction algorithm:** protocol doc omits send frequency and remote adjustment (slew vs skip). Settle by reading `MultiSync.cpp` (queue item 2). Secondary web sources claim ~100 ms–1 s cadence [NEEDS-VERIFICATION].
- **Fadecandy interpolation arithmetic details:** README gives the model; exact fixed-point blend (and whether interpolation is in LUT-space or linear space — order matters for perceived fade linearity) needs the firmware read (queue item 1).
- **Pixelblaze v3.47 internals:** closed firmware; whether the "HDR drivers" also temporally dither on 8-bit chips is unknown — release post is silent [S014]. Could ask on the ElectroMage forum.
- **Does any engine band-limit pattern sampling (true spatial antialiasing of procedural patterns)?** Found none; absence is hard to prove. A targeted look at Chromatik's pattern API and TouchDesigner LED workflows would raise confidence.
- **Perceptual thresholds:** no primary source found quantifying at what keyframe rate interpolation stops being visible on LED strips (vs. the folk 30–60 fps figure). A bench test with pewpew hardware would settle it better than literature.
- **SmoothLed maintenance dates** — did not verify last-commit date or license file contents beyond README claims [S019].
