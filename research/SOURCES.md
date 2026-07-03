# SOURCES — pewpew research bibliography

Append-only. One `### [S###]` heading per source; see
[`README.md`](README.md) for entry format, citation rules, and S-ID block
allocation. Retrieve any entry with `grep -A10 '\[S014\]' research/SOURCES.md`.

Entries below marked `seed` were collected during initial scouting
(2026-07-03) and are pending verification/enrichment by the Phase 1 research
pass — treat `license:`/`published:` fields as unconfirmed until the seed tag
is removed.

---

## Block S001–S049 — RA-01 Landscape

### [S001] WLED (upstream repository)
- type: code
- url: https://github.com/wled/WLED
- author: Aircoookie & wled org contributors
- license: EUPL-1.2 (seed — verify)
- accessed: 2026-07-03
- relevance: dominant ESP32 LED firmware; baseline candidate for pewpew's network-receiver tier

### [S002] WLED 0.16 release prep (issue #4901)
- type: forum
- url: https://github.com/wled/WLED/issues/4901
- accessed: 2026-07-03
- relevance: 0.16 in active release prep mid-2026; claims about WLED capabilities rot fast right now

### [S003] Adafruit Learning System — "WLED 16: What's New"
- type: article
- url: https://learn.adafruit.com/wled-16-what-is-new/overview
- author: Adafruit
- accessed: 2026-07-03
- relevance: PixelForge pixel-graphics toolbox, GIF playback on matrices — WLED 16 headline features

### [S004] WLED-MM (MoonModules fork)
- type: code
- url: https://github.com/MoonModules/WLED-MM
- author: MoonModules
- license: EUPL-1.2 (seed — verify)
- accessed: 2026-07-03
- relevance: fork focused on large installs + advanced audio analysis; ~2 years ahead of upstream on audio

### [S005] WLED MoonModules documentation
- type: docs
- url: https://mm.kno.wled.ge/
- accessed: 2026-07-03
- relevance: fork comparison, audioreactive docs, DDP/virtual-LED guidance

### [S006] MoonModules/MoonLight
- type: code
- url: https://github.com/MoonModules/MoonLight
- accessed: 2026-07-03
- relevance: new ground-up ESP32 engine; claims 12K LEDs @ 100 fps on S3/P4, 3D effects; possibly migrating to "ProjectMM" [NEEDS-VERIFICATION]

### [S007] MoonLight documentation
- type: docs
- url: https://moonmodules.org/MoonLight/
- accessed: 2026-07-03
- relevance: architecture and roadmap of the newest serious ESP32 engine

### [S008] FastLED (repository)
- type: code
- url: https://github.com/FastLED/FastLED
- author: Zach Vorhies (maintainer), Daniel Garcia & Mark Kriegsman (original)
- license: MIT
- accessed: 2026-07-03
- relevance: canonical embedded LED library; dithering, color math, chipset drivers; v3.10.5 June 2026

### [S009] FastLED release notes
- type: docs
- url: https://github.com/FastLED/FastLED/blob/master/release_notes.md
- accessed: 2026-07-03
- relevance: 3.9/3.10-era changes: runtime driver control, parallel output, timing fixes

### [S010] Hackster — "FastLED 3.10.0, artist-focused development roadmap"
- type: article
- url: https://www.hackster.io/news/zachary-vorhies-releases-fastled-3-10-0-pledges-a-more-artist-focused-development-roadmap-b024649dd289
- accessed: 2026-07-03
- relevance: maintainer transition after Daniel Garcia's passing; explicit artist-focused pivot; 4.0 on horizon

### [S011] LedFx (repository)
- type: code
- url: https://github.com/LedFx/LedFx
- license: GPL-3.0 (seed — verify)
- accessed: 2026-07-03
- relevance: the most complete Python LED engine in existence; audio-reactive; active (2.1.x, May 2026); key architecture study

### [S012] LedFx documentation
- type: docs
- url: https://docs.ledfx.app/en/latest/installing.html
- accessed: 2026-07-03
- relevance: Python 3.10–3.13 support; device/virtual model docs

### [S013] Pixelblaze product page (ElectroMage)
- type: product
- url: https://electromage.com/pixelblaze/
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: V3 Standard/Pico current; live-editor pattern engine; closed firmware

### [S014] Pixelblaze v3.47 release — "New HDR LED Drivers"
- type: forum
- url: https://forum.electromage.com/t/release-v3-47-new-hdr-led-drivers-faster-ws2812-and-editor-improvements/3045
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: must-read for RA-02 — HDR driver rewrite, faster WS2812 output on closed-source firmware

### [S015] Fadecandy (repository, dormant)
- type: code
- url: https://github.com/scanlime/fadecandy
- author: Micah Elizabeth Scott (scanlime)
- license: MIT
- accessed: 2026-07-03
- relevance: THE canonical "better than clown mode" reference — temporal dithering + keyframe interpolation firmware; dormant since ~2018

### [S016] Fadecandy project page
- type: article
- url: http://www.misc.name/fadecandy
- author: Micah Elizabeth Scott
- accessed: 2026-07-03
- relevance: design philosophy behind dithering/interpolation choices

### [S017] led-control (jackw01)
- type: code
- url: https://github.com/jackw01/led-control
- docs: https://jackw01.github.io/led-control/
- license: MIT (seed — verify)
- accessed: 2026-07-03
- relevance: closest existing "Python pattern engine done well" — Python functions as fragment shaders, 1D/2D/3D, sACN, ~150 fps on Pi Zero claim

### [S018] py-ledart (TkkrLab)
- type: code
- url: https://github.com/TkkrLab/py-ledart
- accessed: 2026-07-03
- relevance: Python LED art framework prior art; maintenance status unknown [NEEDS-VERIFICATION]

### [S019] SmoothLed (mattshepcar)
- type: code
- url: https://github.com/mattshepcar/SmoothLed
- accessed: 2026-07-03
- relevance: modern reimplementation of Fadecandy-style interpolation+dithering on ATtiny — proof the technique fits tiny MCUs (wearable tier)

### [S020] Adafruit blog — WLED / Pixelblaze / LEDLab mapping comparison
- type: article
- url: https://blog.adafruit.com/2024/09/04/led-pixel-mapping-wled-pixelblaze-and-ledlab-comparison/
- published: 2024-09-04
- accessed: 2026-07-03
- relevance: practitioner comparison of the three main mapping workflows

### [S021] xLights (repository)
- type: code
- url: https://github.com/xLights/xLights
- accessed: 2026-07-03
- relevance: dominant sequencing tool for large displays; model/mapping formats worth studying (seed)

### [S022] Falcon Player / FPP (repository)
- type: code
- url: https://github.com/FalconChristmas/fpp
- accessed: 2026-07-03
- relevance: show player + MultiSync protocol; multi-device sync prior art (seed)

### [S023] Hyperion.ng (repository)
- type: code
- url: https://github.com/hyperion-project/hyperion.ng
- accessed: 2026-07-03
- relevance: ambient-light engine; capture→LED pipeline prior art (seed)

## Block S050–S099 — RA-02 Color science & high-fidelity output

### [S050] FastLED wiki — Temporal Dithering
- type: docs
- url: https://github.com/FastLED/FastLED/wiki/FastLED-Temporal-Dithering
- accessed: 2026-07-03
- relevance: binary dithering design: preserves color/light output at low master brightness; needs >400 Hz refresh

### [S051] FastLED PR #1546 — APA102HD gamma correction
- type: code
- url: https://github.com/FastLED/FastLED/pull/1546
- accessed: 2026-07-03
- relevance: gamma-correct into 16-bit then split across 8-bit RGB + 5-bit brightness ("pseudo-13-bit") — the APA102HD algorithm's origin

### [S052] FastLED issue #1545 — APA102HD discussion
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1545
- accessed: 2026-07-03
- relevance: design discussion behind the five-bit HD gamma approach

### [S053] FastLED APA102.md
- type: docs
- url: https://github.com/FastLED/FastLED/blob/master/APA102.md
- accessed: 2026-07-03
- relevance: official description of APA102 HD mode

### [S054] WLED issue #2416 — Fadecandy-style dithering request
- type: forum
- url: https://github.com/Aircoookie/WLED/issues/2416
- accessed: 2026-07-03
- relevance: feasibility discussion of Fadecandy-grade dithering inside WLED's architecture — instructive about WLED's limits

### [S055] Björn Ottosson — OKLab color space
- type: article
- url: https://bottosson.github.io/posts/oklab/
- author: Björn Ottosson
- accessed: 2026-07-03
- relevance: perceptual color space for blending/gradients; candidate for pewpew's internal color model

### [S056] Sarah Alroe — temporal dithering of NeoPixels on ATtiny412
- type: article
- url: http://sarah.alroe.dk/2025/NeoInf/
- published: 2025
- accessed: 2026-07-03
- relevance: recent independent implementation + analysis of WS2812 temporal dithering limits

### [S057] I2SClocklessLedDriver issue #5 — temporal dithering & color magic
- type: forum
- url: https://github.com/hpwit/I2SClocklessLedDriver/issues/5
- accessed: 2026-07-03
- relevance: dithering discussion for high-throughput parallel ESP32 output (hpwit drives WLED-MM's large-install performance)

## Block S100–S149 — RA-03 LED chips & electrical limits

### [S100] FastLED issue #1045 — new chip type NS108/HD108
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1045
- accessed: 2026-07-03
- relevance: 16-bit chip protocol details and library support discussion

### [S101] Superlightingled — SK9822 vs APA102 vs APA107 vs HD107(s) vs HD108
- type: article
- url: https://www.superlightingled.com/blog/sk9822-vs-apa102-vs-apa107-vs-hd107-vs-hd107s-vs-hd108/
- accessed: 2026-07-03
- relevance: vendor comparison of clocked-chip family; PWM rates, protocol compat

### [S102] HD108 manufacturer page — HD107s/APA102/APA107/SK9822 relationship
- type: product
- url: https://www.hd108-led.com/about-hd107s-apa102-apa107-and-sk9822/
- accessed: 2026-07-03
- relevance: HD108: 16-bit/channel, 27 kHz PWM, APA102-style protocol, 3.0V logic threshold (3.3V-friendly)

### [S103] Newstar NS108 product page (27 kHz, 16-bit)
- type: product
- url: https://www.ledstrip-newstar.com/product/27khz-ns108-16bit-65536-5050-rgb-pixel-led-chip/
- accessed: 2026-07-03
- relevance: second-source availability of 16-bit chips; HD108-compatible

## Block S150–S199 — RA-04 Protocols & transport

### [S150] DDP — Distributed Display Protocol specification
- type: spec
- url: http://www.3waylabs.com/ddp/
- author: 3waylabs
- accessed: 2026-07-03
- relevance: 10-byte header; up to 1440 channels/packet; native 1/4/8/16/24/32-bit per-channel — the only mainstream pixel transport with a 16-bit wire format

### [S151] DDP vs E1.31 vs Art-Net comparison (pixel-led-effects, 2025)
- type: article
- url: https://pixel-led-effects.com/led-comparisons/ddp-vs-e131-vs-artnet-wled-xlights/
- published: 2025
- accessed: 2026-07-03
- relevance: practical throughput/overhead comparison across the three transports

### [S152] WLED-MM — DDP & virtual LEDs documentation
- type: docs
- url: https://mm.kno.wled.ge/advanced/ddp/
- accessed: 2026-07-03
- relevance: DDP receiver behavior and large-install topology guidance

## Block S200–S249 — RA-05 Pattern-engine design

### [S200] ElectroMage / Pixelblaze documentation
- type: docs
- url: https://electromage.com/docs/
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: the expression-language + (index, x, y, z) render model — best-in-class pattern authoring to learn from

## Block S300–S349 — RA-07 Mapping & topology

### [S300] marimapper (TheMariday)
- type: code
- url: https://github.com/TheMariday/marimapper
- license: GPL-3.0 (seed — verify)
- accessed: 2026-07-03
- relevance: current active camera-based 3D LED mapper

### [S301] Lightwork (PWRFLcreative)
- type: code
- url: https://github.com/PWRFLcreative/Lightwork
- accessed: 2026-07-03
- relevance: earlier camera-mapping pipeline; prior art

### [S302] ElectroMage forum — LED 3D mapping tool thread
- type: forum
- url: https://forum.electromage.com/t/i-made-an-led-3d-mapping-tool-that-might-be-of-interest/3598/11
- accessed: 2026-07-03
- relevance: practitioner mapping workflows in the Pixelblaze ecosystem

## Block S350–S399 — RA-08 Hardware: host-driven tier

### [S350] QuinLED project site
- type: docs
- url: https://quinled.info/
- author: Quindor
- accessed: 2026-07-03
- relevance: reference DIY controller boards + extensive practical wiring/power-injection guides (seed)

## Block S400–S449 — RA-09 Hardware: wearable tier

### [S400] todbot — "Speed up CircuitPython LED animations 10x with ulab"
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt
- published: 2022-10-21
- accessed: 2026-07-03
- relevance: establishes realistic CircuitPython frame-rate ceilings and the ulab escape hatch — central to the wearable-tier Python question

### [S401] Adafruit CircuitPython LED Animation library
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_LED_Animation
- license: MIT
- accessed: 2026-07-03
- relevance: the standard wearable-tier animation library; API prior art

## Block S450–S499 — RA-10 Audio reactivity

### [S450] WLED-MM — Audio Reactive documentation
- type: docs
- url: https://mm.kno.wled.ge/advanced/audio-reactive/
- accessed: 2026-07-03
- relevance: most advanced embedded audio pipeline (GEQ, beat detection, sound sync)

## Block S500–S549 — RA-11 Simulation, preview & dev ergonomics

### [S500] fastled-wasm (zackees)
- type: code
- url: https://github.com/zackees/fastled-wasm
- accessed: 2026-07-03
- relevance: browser-compiled FastLED sketches with sub-second recompiles — state of the art for LED dev iteration loops

### [S501] fastled on PyPI (WASM compiler CLI)
- type: docs
- url: https://pypi.org/project/fastled/
- accessed: 2026-07-03
- relevance: NOT a Python LED engine — it's the CLI for the WASM compiler; disambiguation matters
