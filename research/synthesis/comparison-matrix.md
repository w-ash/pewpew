# Systems × capabilities comparison matrix

Date: 2026-07-03
Status: Proposed (Phase 3 synthesis). All verdicts as of research date;
maintenance claims are dated in the cited topic/code-reading docs.

Split into two tables for readability. Every non-obvious cell cites; obvious
cells (e.g. "none") that are load-bearing cite the doc that verified the
absence.

## Table A — quality core: authoring, precision, dithering, audio

| System | Authoring model | Internal precision | Temporal dithering | Audio |
|---|---|---|---|---|
| **WLED** | Compiled-in C++ `void mode()` globals over segment macros; metadata-string param DSL; no runtime effect injection [S645:wled00/FX.h#L106-L113,815][S205] | 8-bit RGBW end-to-end; 8→8 gamma LUT (γ2.2 default); ~5 effective bits at low brightness [S645:wled00/FX_fcn.cpp#L1781][S054] | None for addressable LEDs (issue #2416 open since 2021); PWM/analog buses only [S645:wled00/bus_manager.cpp#L422-L455][S054] | Audioreactive usermod upstreamed from MM: FFT → 16-band GEQ, AGC presets, `um_data_t` feature table [S645:usermods/audioreactive/audio_reactive.cpp#L27-L35][S453] |
| **WLED-MM** | Same as WLED (0.14-era fork); ARTI-FX interpreted effects exist as a bolt-on [S646:readme.md#L16-L18][S207] | 8-bit (0.14-era direct render; NeoPixelBusLg luminance layer, same 8-bit result) [S646:wled00/bus_wrapper.h#L200-L202] | None [S646][S054] | The reference embedded pipeline: 22 kHz I2S, 512-pt FFT, 16-band GEQ, mic profiles, AGC, UDP sound-sync V2 (44-byte feature packet) [S453] |
| **projectMM** | C++ MoonModules (effects/modifiers/layouts/drivers share one base class + declared controls); MoonLive JIT compiles scripts to native code on-device [S715:docs/architecture.md#L76-L88,L418-L428] | 8-bit integer end-to-end, deliberately (scale over depth: 16K LEDs on no-PSRAM ESP32); no gamma table yet [S715:docs/architecture.md#L202,L485] | None [S715:docs/architecture.md#L485] | Shared 16-band FFT audio struct carried over from MoonLight [S715:docs/history/decisions.md#L112-L126] |
| **FastLED** | C++ library — sketches call color/palette/driver APIs; not an engine [S008][S009] | 8-bit core with 16-bit HD paths: HSV16, `ColorFromPaletteHD` (8.8 fixed), 16-bit gamma LUT [S615:release_notes.md#L446-L455][S615:src/fl/gfx/colorutils.cpp.hpp#L271-L336] | Yes — binary (bit-reversed counter) dithering keyed to brightness, +2–3 perceived bits at 400 Hz; plus APA102HD 5-bit joint quantization (~13-bit, no refresh requirement) [S615:src/pixel_controller.h#L253-L363][S615:src/fl/gfx/five_bit_hd_gamma.cpp.hpp#L36-L130] | None built in (sketches roll their own) [S008] |
| **Pixelblaze** | Best-in-class: JS-subset per-pixel `render(index,x,y,z)` + `beforeRender(delta)`, browser compile-on-keystroke to on-device VM bytecode; `export var`/slider-naming auto-UI [S680:README.expressions.md#L19-L70][S681:pixelblaze/pixelblaze.py#L1490-L1512] | 16-bit per element throughout (v3.47 rewrite); 16.16 fixed-point pattern math [S063][S680:README.expressions.md#L25] | No — explicitly rejected in favor of HDR chips ("Temporal dithering only works well if you can refresh... very fast") [S684][S251] | Sensor expansion board: STM32 coprocessor streams 32-band FFT + energy + IMU at ~39 Hz; patterns read exported vars [S683:src/output.c#L71-L145][S204] |
| **LedFx** | Python effect classes + voluptuous schema → auto UI; contributor-oriented, no live user authoring [S630:ledfx/effects/__init__.py#L273-L340][S208] | Float64 NumPy 0–255 pipeline... truncated to uint8 at every network driver (`astype(np.uint8)`), no gamma [S630:ledfx/effects/__init__.py#L479-L547][S630:ledfx/devices/ddp.py#L25-L36] | None [S630][S011] | The reference host pipeline: sounddevice @60 Hz hop, 30 kHz internal rate, aubio FFT/tempo/onset, 3 AGC'd melbanks, bar-phase oscillator [S630:ledfx/effects/melbank.py#L20-L29,L380-L403][S630:ledfx/effects/audio.py#L1482-L1530] |
| **led-control** | Closest Python prior art: RestrictedPython per-pixel shader `pattern(t,dt,x,y,z,prev_state)`, browser editor, live recompile [S660:ledcontrol/animationfunctions.py#L10-L26][S660:ledcontrol/animationcontroller.py#L228-L282] | Float in pattern, quantized early to 8-bit in C renderer; gamma reduced to hardcoded `v*v`, real gamma commented out [S660:ledcontrol/driver/led_render.h#L93-L97,L196-L202] | None (grep-verified) [S660] | None (sACN receive only) [S660:ledcontrol/animationcontroller.py#L202-L208] |
| **Fadecandy** | Host sends plain 8-bit keyframes (OPC); no on-device authoring — quality layer, not an engine [S600:doc/fc_protocol_usb.md#L46-L68][S015] | 8-bit host → 16-bit device: interpolate ×257, 257-entry 16-bit LUT (gamma+whitepoint), int16 dither residual [S600:firmware/fc_pixel.cpp#L25-L88] | THE reference: per-channel error-feedback dither at ~400–500 Hz output, below the pattern engine [S600:firmware/fc_pixel.cpp#L58-L88][S016] | None [S015] |
| **HyperHDR** | Capture-driven ambient engine (screen/video → LEDs); Python-scripted effects secondary [S023][S031] | Float32 linear sRGB from ingest (uint16 linear LUT, integer accumulate) through smoothing; drivers self-quantize [S700:sources/base/ImageColorAveraging.cpp#L216-L258][S700:sources/led-drivers/LedDevice.cpp#L625-L678] | Yes — adaptive temporal error-diffusion per LED: static-scene freeze, monotonic-motion gate, leaky accumulator (0.96→0.80); runs at output rate (25–200 Hz) [S700:sources/led-drivers/InfiniteColorEngineRgbw.cpp#L80-L156][S032] | None (ambient, not music) [S023] |
| **xLights / FPP** | Offline sequencer: timeline effects rendered to per-model buffers, baked to FSEQ; FPP plays + MultiSyncs [S506][S258][S256] | 8-bit FSEQ frames at authoring-time fixed fps (20–40 typical) [S258][S263] | None [S258] | Sequenced to audio offline; FPP has media sync, not live DSP [S022][S256] |
| **Chromatik / LX** | Java `LXPattern` classes; first-class `CompoundParameter` objects → auto UI/OSC/MIDI + modulation matrix; GLSL shader patterns in TE practice [S216][S563] | Float/int Java pipeline, 8-bit protocol outputs (Art-Net/sACN/DDP/OPC/KiNet) [S035][S034] | None documented [S034][S035] | MIDI beat clock, OSC tempo, Rekordbox-driven AutoVJ in TE; no built-in DSP chain like LedFx [S556][S563] |
| **TouchDesigner** | Node-based GPU compositing; LED = texture sampled at fixture points (DMX POPs, 2025) [S029][S213] | GPU float internally; 8-bit DMX/sACN/Art-Net out [S029][S213] | None documented [S029] | Rich audio CHOPs ecosystem (host-grade, out of scope to enumerate) [S029] |

## Table B — integration: protocols, mapping, license, maintenance, fit

| System | Protocols (pixel I/O) | Mapping | License | Verdict | Form-factor fit |
|---|---|---|---|---|---|
| **WLED** | In: DDP, E1.31/sACN, Art-Net, WLED-UDP (WARLS/DRGB/DNRGB), TPM2, Hyperion; out: DDP/E1.31/Art-Net re-send (BusNetwork) [S645:wled00/e131.cpp#L20-L280][S645:wled00/udp.cpp#L604-L646] | `ledmap.json` index permutation + 2D w/h + `-1` gaps; no coordinates [S303] | EUPL-1.2 [S001] | **Ascendant** — v16.0.0 2026-05, largest ecosystem, MM harmonization planned [S002] | Portable + room receiver; not wearable (WiFi power) [S001][S411] |
| **WLED-MM** | Same + recommends DDP for WLED-to-WLED [S152] | Same as WLED [S303] | EUPL-1.2 [S004] | **Stable→waning as a fork** — audio merging upstream in 16.1.x; team energy in projectMM [S002][S005][S024] | Same as WLED [S004] |
| **projectMM** | ArtNet/E1.31/DDP drivers + WS2812 RMT/LCD/PARLIO; desktop + ESP32 targets [S715:docs/architecture.md#L285-L318] | Best-in-class decomposition: Layouts (coordinate iterators) → per-Layer mapping LUT (CSR, 4 types) → modifiers folded in at zero per-frame cost [S715:src/light/layers/MappingLUT.h#L10-L18][S715:docs/architecture.md#L331-L360] | GPL-3.0 [S024][S715] | **Ascendant but very young** — same-day commits, v2.0.0 2026-06; single product owner [S024][S715] | Room/stage; portable plausible; not wearable [S024] |
| **FastLED** | None (library drives chips directly; 50+ chipsets, ns-timing tables, RP2040 PIO/ESP32 RMT/LCD parallel) [S615:src/fl/chipsets/led_timing.h#L100-L460][S615:release_notes.md#L217-L285] | `fl::` sub-pixel splat + XYPath raster; corkscrew/screenmap helpers; no install-level map format [S261][S503] | MIT [S008] | **Ascendant** — 3.10.x cadence, 4.0 imminent; one dominant maintainer (bus factor) [S008][S009][S010] | All three tiers (ATtiny→Teensy) — it's a library you size [S008] |
| **Pixelblaze** | Own websocket (port 81) + UPXL expander serial (open, MIT); Firestorm sync; no standard pixel-stream input [S681][S682:README.md#L13-L30] | First-class JSON/JS-generated coordinate maps, normalized to 0–1 world units at install time; render2D/3D auto-selected [S680:README.mapper.md#L12-L36][S304] | Proprietary firmware; docs/expander/sensor MIT [S013][S682] | **Waning** — firmware stalled at v3.47 (2023-07); no roadmap; single maintainer; hardware business alive [S014][S025][S685] | Wearable-adjacent through mid-room (with expanders) [S013] |
| **LedFx** | Widest sender: DDP, E1.31, Art-Net, WLED-UDP (adaptive WARLS/DRGB), OpenRGB, Adalight, OPC + consumer ecosystems (Hue, LIFX, Govee...) [S630:ledfx/devices/ddp.py][S011] | Virtuals: ordered device segments → 1D canvas (span/copy, reverse, grouping, rows-2D); routing not geometry; precompiled gather = 13× claim [S305][S630:ledfx/virtuals.py#L409-L495] | GPL-3.0 [S011] | **Stable** — v2.1.9 2026-05, daily commits; app, not engine [S011] | Room/portable via host; not wearable [S012] |
| **led-control** | Local rpi_ws281x; sACN in; custom UDP/serial to ESP8266 companions [S660:ledcontrol/ledcontroller.py#L108-L142] | JSON point list normalized 0–1; 1D default [S660:ledcontrol/pixelmappings.py#L8-L17] | MIT [S017][S660] | **Waning** — dormant since 2023-11, bus factor 1 [S660][S017] | Pi portable/room; not wearable [S017] |
| **Fadecandy** | OPC over TCP in; USB to own boards out [S600:server/src/opc.h#L40-L58][S160] | Declarative map instructions `[chan, firstIn, firstOut, count, swizzle]` [S600:server/src/fcdevice.cpp#L503-L651] | MIT [S600:LICENSE#L1-L3] | **Dead as product, ascendant as idea** — original repo deleted; technique keeps being reimplemented [S027][S019][S062] | Was room-scale (USB-tethered); technique fits wearables (SmoothLed) [S016][S019] |
| **HyperHDR** | Out: SPI (HD108, SK6812), DDP, Art-Net, Adalight, HyperSPI, rpi PWM/PIO, Hue, LIFX [S700:sources/led-drivers/LedDevice.cpp#L625-L678] | Screen-zone geometry only (ambient) [S023] | MIT [S031][S700] | **Ascendant** (in ambient niche) — ICE float pipeline + adaptive dithering landed 2026 [S031][S032] | Room ambient only [S023] |
| **xLights / FPP** | E1.31, Art-Net, DDP out; deep controller-vendor integration; FPP MultiSync for fleet playback [S154][S164][S256] | Models (.xmodel XML): trees/matrices/custom voxel grids; buffer-style indirection [S306][S307] | GPL-3.0 (xLights) [S026]; FPP mixed GPL [S022][NEEDS-VERIFICATION] | **Ascendant (niche)** — biweekly releases [S026]; FPP **stable** v9.5 [S022] | Room/whole-house; irrelevant to wearables [S021] |
| **Chromatik / LX** | Art-Net, sACN, OPC, DDP, KiNet out with per-fixture output bindings [S034][S309] | Best open declarative format: `.lxf` JSON fixtures (points/strip/arc, nested transforms, y-up, physical units) + raw *and* normalized coords per point; tags/views as masks [S309] | Custom LX license — non-commercial cap ($25K revenue), not OSI [S035] | **Stable** — Chromatik 1.2.1 2025-11, LX pushed 2026-06; license-encumbered [S034][S035] | Room/installation on desktop JVM [S034] |
| **TouchDesigner** | DMX/Art-Net/sACN CHOPs; needs network-to-pixel bridge for addressable [S029][S213] | Fixtures as 3D points sampled from rendered scene (DMX POPs 2025) [S029] | Proprietary; free non-commercial tier with limits [S029] | **Stable** — commercial, active [S029] | Room/stage tethered to a beefy PC [S029] |

## What no single system has — what pewpew uniquely combines

From the RA-01b gap check [S011][S017][S030][S040], the union of features that
exists nowhere in one system:

1. **Live, user-facing pattern authoring in Python** — the led-control shader
   model [S660:ledcontrol/animationfunctions.py#L10-L26] with Pixelblaze's
   editor ergonomics [S680][S504] — rather than a fixed effect catalog
   (LedFx's gap [S011]) or compile-and-flash C++ (WLED's gap [S205][S207]).
2. **A high-fidelity output pipeline in Python** — float linear-light,
   quantize-once, temporal dithering, colorimetric correction — currently
   proven only in C++ (HyperHDR [S700], FastLED [S615], Fadecandy [S600]) and
   never shipped in any Python engine (LedFx truncates to uint8 with no gamma
   [S630:ledfx/devices/ddp.py#L25-L36]).
3. **16-bit end-to-end over the wire** — DDP's 16-bit format [S150] is
   unexploited by every system surveyed (LedFx hardcodes 8-bit DDP
   [S630:ledfx/devices/ddp.py#L36]; WLED accepts RGB24/RGBW32 only
   [S645:wled00/e131.cpp#L20-L93]) — terminating in 16-bit-native chips
   (HD108/WS2816) that make dithering unnecessary [S130][S122][S063].
4. **Vectorized execution of a per-pixel authoring surface** — authors write
   scalar-looking pure functions; the engine evaluates them over NumPy
   coordinate arrays. Nobody ships this: led-control pays per-pixel CPython
   calls (~22.5k px/s ceiling) [S660:README.md#L17-L24], LedFx exposes raw
   array semantics [S630:ledfx/effects/__init__.py#L273-L340], Pixelblaze
   built a custom VM [S681:pixelblaze/pixelblaze.py#L1490-L1512].
5. **One engine spanning all three form factors** — host engine (room),
   network receivers (portable), and an on-device Python (ulab) wearable
   runtime sharing the same pattern contract. FastLED spans the hardware but
   is a C++ library, not an engine [S008]; everything else picks one tier.
6. **Genuinely open license + pip-installable engine-as-library** — vs
   Chromatik's revenue-capped license [S035], Pixelblaze's closed firmware
   [S013], GPL app-coupling in LedFx [S011], and led-control's absence from
   PyPI [S017].
