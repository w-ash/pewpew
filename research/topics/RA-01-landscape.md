# RA-01: Landscape survey of LED control systems

Last researched: 2026-07-03
Status: draft
S-ID block: S001–S049 (new IDs from S024; S030–S049 reserved for Python-engine gap check)

## Key questions

- What does every serious addressable-LED control system (mid-2026) do best, and what should pewpew steal?
- Is MoonLight being superseded by a "ProjectMM" migration?
- Which systems are ascendant / stable / waning?
- License, maintenance status (dated), and form-factor fit (wearable/portable/room) per system.

## Findings

### WLED (upstream)

**Architecture:** monolithic C++ Arduino-framework firmware for ESP8266/ESP32 driving addressable strips; core loop of segments (per-strip regions) running one effect function each over a shared pixel buffer, with a self-hosted web UI, JSON/HTTP API, MQTT, and network ingest via E1.31/Art-Net/DDP/Hyperion; extensibility via compiled-in "usermods" [S001].

**0.16 status resolved:** the "0.16" release shipped as **v16.0.0 on 2026-05-03** (versioning scheme changed from 0.x to whole numbers), ~18 months of work, 59 contributors; a 16.0.1 bugfix milestone was in progress as of mid-2026, and "Audioreactive off-tree, and WLED/WLED-MM code harmonization" was "pushed to 16.1.x" [S002]. Headline 16.0 features: segment layering (stacked effects), a particle system, GIF playback on matrices, the PixelForge image/painting editor, custom fonts + UTF-8 scrolling text, 800+ palette editor, HUB75 matrix support, DMX serial input, dynamic button config [S002][S003]. Latest 0.15.x maintenance release was 0.15.4 (2026-03-14) [S002].

**What pewpew should steal:** the segment model (independently addressable sub-regions with per-segment effect/palette/brightness) and 16.0's segment layering; the ubiquity-through-simplicity lesson — one flashable binary, config entirely at runtime through the web UI; DDP/E1.31 receiver role so any host engine can drive it [S001][S003].

- License: EUPL-1.2 [S001].
- Maintenance: very active — v16.0.0 2026-05-03, nightlies as of 2026-07-02, six-person release team [S002].
- Form factor: portable and room-scale (ESP32 nodes); not wearable (needs WiFi/ESP32-class power, no battery-first design) [S001].
- Verdict: **ascendant** — largest ecosystem, a major release in May 2026, and planned upstream/fork harmonization pulling WLED-MM's audio work into mainline [S002].

### WLED-MM (MoonModules fork)

**Architecture:** same firmware skeleton as upstream WLED (Arduino C++, segments/effects, web UI) but tuned for large installs and audio: parallel LED outputs via hpwit's I2S drivers, higher LED counts per ESP32, HUB75 matrix drivers, DMX input, extra audio codecs (ES8388, AC101, ES8311), and the sound-reactive pipeline (GEQ, beat detection, audio sync) that upstream historically lacked [S004][S005].

**What it does best / pewpew should steal:** the embedded audio-reactive pipeline (FFT → GEQ bins → beat detection → network audio sync across nodes) — still the reference implementation, "2 years ahead" of upstream on audio; effects reportedly run 50-60% faster than upstream, 25-45 fps on complex 2D setups [S004][S005].

- License: EUPL-1.2 (inherited from WLED) [S004].
- Maintenance: active — v14.7.1 on 2026-01-13, nightlies through 2026-07-02 [S004].
- Form factor: portable/room-scale (ESP32-class); not wearable [S004].
- Verdict: **stable-to-waning as a distinct fork** — actively maintained, but its raison d'être is scheduled to dissolve: upstream's 16.1.x milestone plans "Audioreactive off-tree, and WLED/WLED-MM code harmonization" [S002], the fork itself describes usermods that "will move to upstream" [S005], and MoonModules' own new energy is in ProjectMM [S024].

### MoonModules MoonLight / ProjectMM

**The rumor is resolved: MoonLight is being superseded.** MoonLight v1.0.0 (released 2026-05-06) is explicitly the last release of that codebase; its release notes state "As of May 2026, active development is moving to ProjectMM. MoonLight v1.0.0 remains fully usable" [S006][S007]. The successor lives at github.com/ewowi/projectMM ("Drive large LED installations and DMX lighting from ESP32, Teensy, Raspberry Pi, Windows, macOS or Linux desktop. One source tree, multiple targets."), already at v2.0.0 as of 2026-06-24 [S024].

**MoonLight architecture:** ESP32 firmware built on MoonBase/ESP32-SvelteKit; ESP-IDF 5 + FastLED 3.10 core, Svelte 5 + Tailwind/DaisyUI web UI. Modular design of Effects, Modifiers, Layouts and Drivers. Claims up to 12,288 LEDs @ 100 FPS via 1/4/16/48 parallel strips; ESP32-P4 support landed in v0.7.0 (2025-12-22). License GPL-3.0 [S007].

**ProjectMM architecture:** pluggable pipeline of Layouts → Layers (effects + modifiers) → Drivers, with a uniform `MoonModule` base class where every effect/modifier/layout/driver shares one lifecycle and declared controls. Pure ESP-IDF (not Arduino) on ESP32; deliberately zero third-party libraries — color math, HTTP/WebSocket server and storage are all in-tree. C++ core with Python/JS support tooling. GPL-3.0. Explicitly written as independent code against a new architecture rather than copying WLED/StarLight/MoonLight structures [S024].

**What pewpew should steal:** the Layouts → Layers(effects+modifiers) → Drivers decomposition and the single-module-base-class-with-declared-controls pattern (auto-generated UI from module metadata); cross-platform "one source tree, ESP32-to-desktop" parity as an architectural goal [S024].

- License: GPL-3.0 (both MoonLight and ProjectMM) [S007][S024].
- Maintenance: MoonLight frozen at v1.0.0 (2026-05-06), PRs still accepted; ProjectMM very active, v2.0.0 on 2026-06-24, ~284 commits [S006][S024].
- Form factor: room-scale / stage installs primarily; portable plausible (ESP32); not wearable-oriented. ProjectMM's desktop/Pi targets extend it to host-driven room-scale [S024].
- Verdict: MoonLight **waning** (explicitly end-of-lined by its own authors [S006]); ProjectMM **ascendant** (successor with all active development, but very young — API churn risk between v1 and v2 within weeks) [S024].

### FastLED

**Architecture:** a C++ library (not a system) — chipset drivers + color math (CRGB/CHSV, palettes, temporal dithering, HD gamma) + a growing `fl::` platform layer (containers, ease functions, an fx engine, Animartrix polar-coordinate effects) compiled into user sketches; the 3.9.x series was explicitly "Beta 4.0.0", building async rendering (~70% speedup by decoupling frame computation from output), ESP32 RMT5 8-way parallel, Teensy ObjectFLED ("27,500 pixels @ 60fps" on Teensy 4.1 across 50 WS2812 strips), and Yves's I2S LCD driver for 12-way parallel on ESP32-S3 [S009].

**Post-3.10 artist era:** with 3.10.0 (June 2025), maintainer Zach Vorhies — who took over after original co-author Daniel Garcia's death — pledged an explicitly artist-focused roadmap [S010]. 3.10.x delivered Animartrix out of beta, corkscrew mapping for festival sticks, ease-function library, TrueType font rendering, cross-platform native RGBW, and new chipsets (WS2812B-V5, HD108, UCS7604); 4.0 is signposted ("header-stable with 4.0", `fl::` namespace consolidation, modular drivers) but unreleased as of 2026-07-03 [S009]. Latest release 3.10.5, June 2026 [S008].

**What pewpew should steal:** the color/output substrate — temporal dithering, five-bit HD gamma (APA102HD), palette machinery — plus the async render/output decoupling and the WASM compile path (fastled-wasm) for instant browser preview [S009][S500].

- License: MIT [S008].
- Maintenance: very active — 3.10.5 June 2026, near-daily commits, one dominant maintainer (bus-factor risk) [S008][S010].
- Form factor: all three — the only system here that spans ATtiny-class wearables to Teensy room-scale, because it's a library you size to the MCU [S008][S009].
- Verdict: **ascendant** — accelerating release cadence since the 2024 maintainer transition, 4.0 imminent, and it is becoming the substrate other systems build on (MoonLight uses FastLED 3.10 [S007]) [S009][S010].

### Pixelblaze (ElectroMage)

**Architecture:** closed-firmware ESP32 controller (V3 Standard / Pico) whose defining idea is a live-edit pattern language: users write small JS-like expression programs against a `(index, x, y, z)` render model with per-pixel `render()/render2D()/render3D()` callbacks, edited in a built-in browser IDE with instant hot-reload and on-device compilation; mapping is a first-class concept (pixel maps as JS or coordinates), and multi-unit sync via a leader/follower feature [S013][S200].

**What it does best / pewpew should steal:** the authoring experience — sub-second edit-to-glow loop, normalized coordinate render model that makes patterns portable across layouts, and the pattern-as-tiny-program abstraction; plus HDR output drivers (48-bit color on WS2816/NS108) done on closed firmware in 2023, before most open projects [S013][S014][S200].

**Vendor health:** effectively a one-person company (Ben Hencke / Hencke Technologies, Portland OR). The last major firmware release remains v3.47 (2023-07-13, total LED-driver rewrite with HDR support) [S014]; asked directly in Feb 2025 about a roadmap, Hencke replied "I don't have a roadmap shared," while remaining active in support threads through June 2026 [S025]. Community stays lively (third-party pattern IDE "PXLBLZ" June 2026; a "Pixelblaze Pico Plus" thread June 2026) [S025][NEEDS-VERIFICATION on Pico Plus being an official new SKU].

- License: proprietary firmware; hardware sold via ElectroMage/Tindie/Crowd Supply [S013].
- Maintenance: hardware in production and forum support active (June 2026), but firmware stagnant ~3 years [S014][S025].
- Form factor: portable and wearable-adjacent (Pico is popular for costumes/totems); room-scale only with output expanders/sync [S013][S025].
- Verdict: **waning** — beloved and functional, but a 3-year firmware gap, no public roadmap, and single-maintainer closed source make it a dependency risk; its ideas, not its platform, are what to adopt [S014][S025].

### LedFx

**Architecture:** a host-side Python engine (Python 3.10–3.13) that captures system/mic audio, runs DSP (mel banks, beat/onset detection), and renders audio-reactive effects onto "virtuals" — logical strips composed from one or more physical "devices" — then streams frames out over WLED-native realtime protocols, E1.31/sACN, DDP, Art-Net, OpenRGB, etc.; controlled by a React web UI over a REST/WebSocket API [S011][S012].

**What it does best / pewpew should steal:** the device/virtual split (logical canvases decoupled from physical outputs, spanning multiple controllers) and the proof that a Python host engine streaming to dumb network receivers is viable at real installs' scale; also its polished audio pipeline abstractions [S011][S012].

- License: GPL-3.0 (verified via GitHub API 2026-07-03) [S011].
- Maintenance: active — v2.1.9 released 2026-05-18, repo pushed 2026-07-03, multiple regular contributors (bigredfrog, YeonV, Djelibeybi) [S011].
- Form factor: room-scale/portable via a host PC or Pi plus network nodes; not standalone-wearable (requires a host computer) [S012].
- Verdict: **stable** — steady monthly 2.1.x cadence and feature work (new effects, playlists), but incremental rather than architectural momentum [S011].

### xLights

**Architecture:** desktop C++/wxWidgets sequencer for large synchronized displays: users define "models" (geometric LED arrangements: trees, matrices, arches, custom 3D layouts) on a virtual layout canvas, sequence timed effects against audio on a timeline, then either render to FSEQ files for players (FPP) or drive controllers live over E1.31/Art-Net/DDP; deep controller-vendor integration (auto-configures Falcon/Kulp/ESPixelStick/WLED outputs) [S021]. NOTE: the repo has moved — it now lives at github.com/xLightsSequencer/xLights, not github.com/xLights/xLights [S026].

**What it does best / pewpew should steal:** the model/layout abstraction (declarative geometry → automatic pixel-coordinate mapping) and its controller-config export — the mature answer to "how do I describe thousands of pixels across many controllers once" [S021][S026].

- License: GPL-3.0 (verified via GitHub API 2026-07-03) [S026].
- Maintenance: extremely active — date-versioned releases 2026.11 (2026-06-14) and 2026.12 (2026-07-02), repo pushed 2026-07-03 [S026].
- Form factor: room-scale/whole-house only; a desktop authoring tool, irrelevant to wearables [S021].
- Verdict: **ascendant** (within its niche) — release cadence of roughly every 2-3 weeks through mid-2026 and the center of gravity of the holiday-display ecosystem [S026].

### Falcon Player (FPP)

**Architecture:** Linux show player (Raspberry Pi/BeagleBone/Docker) that plays pre-rendered FSEQ sequences plus media, with output plugins for E1.31/DDP/Art-Net/serial/panel drivers, and **MultiSync** — its frame-accurate multi-device synchronization protocol that lets one master FPP coordinate many remotes (and WLED nodes) across a network; managed via a web UI [S022].

**What it does best / pewpew should steal:** MultiSync's approach to fleet-level frame sync, and the FSEQ compiled-sequence format (compact pre-rendered frames decoupling authoring from playback) [S022].

- License: mixed GPL/CC (GitHub reports NOASSERTION; components GPL-2.0-and-later per repo docs) [S022][NEEDS-VERIFICATION].
- Maintenance: very active — v9.5 on 2026-01-08, v9.4 2025-12-09, nightlies through 2026-07-03 [S022].
- Form factor: room-scale/installation; Pi-based so technically portable, not wearable [S022].
- Verdict: **stable** — mature, steady major-version cadence, entrenched as xLights' playback counterpart [S022].

### Fadecandy

**Architecture:** a USB controller (Teensy-class MCU) plus host-side `fcserver`: the host sends keyframes over USB/Open Pixel Control, and the firmware does the quality work — interpolating between keyframes at high refresh and applying temporal dithering so 8-bit WS2811 pixels behave like higher-bit-depth ones; explicitly designed so "video-like" smooth low-brightness output survives cheap LEDs [S015][S016].

**Status — dormant and now partially unhosted:** the original repo github.com/scanlime/fadecandy has been **deleted** (404 as of 2026-07-03) along with Micah Elizabeth Scott's other GitHub repos; community mirrors carry the code forward (e.g. github.com/PimentNoir/fadecandy, github.com/bluewavenet/fadecandyserver) and Adafruit forum users note "the fadecandy project has been discontinued by the original maker" [S027]. Hardware unavailable new; development ceased ~2018 [S015].

**What it does best / pewpew should steal:** the core thesis — put interpolation + temporal dithering *below* the pattern engine so every pattern gets smooth high-refresh output for free; SmoothLed proves the technique fits ATtiny-class wearables [S016][S019].

- License: MIT [S015].
- Maintenance: dead — no development since ~2018, original repo deleted; mirrors only [S015][S027].
- Form factor: designed for room-scale art installs (USB-tethered host); the technique (not the product) applies to wearables via SmoothLed [S016][S019].
- Verdict: **waning/dead as a product, ascendant as an idea** — its dithering+interpolation design is the quality bar successors (Pixelblaze HDR drivers, FastLED HD gamma, SmoothLed) keep re-implementing [S014][S019][S051].

### BiblioPixel

**Confirmed dead.** ManiacalLabs' Python LED animation framework (multi-controller, 1D/2D/3D addressing, remote UI): last push to master 2021-02-08; no releases, issues, or maintainer activity since [S028]. Its niche — a general Python LED framework — is now served by LedFx (audio-reactive) and led-control (pattern-engine style) [S011][S017].

- License: MIT [S028].
- Maintenance: none since 2021-02-08 [S028].
- Form factor: host-driven (Pi/PC), room/portable.
- Verdict: **dead** — >5 years without a commit [S028]. Worth a skim only for its multi-driver abstraction API.

### led-control (jackw01)

**Architecture:** Python/Flask web app for Raspberry Pi that treats animation patterns as Python functions acting like fragment shaders — each pattern is `f(t, dt, x, y, z, prev_state) → (color, mode)` evaluated per-pixel in HSV/RGB, with a restricted live-editable code editor in the web UI; supports 1D/2D/3D arrangements, sACN/E1.31 input/output, and claims ~150 fps for hundreds of LEDs on a Pi Zero via a C extension for the hot loop [S017].

**What it does best / pewpew should steal:** the closest existing "Pixelblaze-in-Python" — per-pixel shader-function authoring model with live editing, and the pragmatic C-extension escape hatch for the per-pixel inner loop [S017].

- License: MIT (verified via GitHub API 2026-07-03) [S017].
- Maintenance: dormant — last push 2023-11-10, single author [S017].
- Form factor: portable/room (Pi-class host); not wearable [S017].
- Verdict: **waning** — no activity in ~2.5 years, but small enough to be read fully and mined; the most directly relevant prior art for a Python pattern engine [S017].

### py-ledart (TkkrLab)

**Architecture:** hackerspace-grown Python framework for LED-matrix art: generator-based animation pipeline sending frames to network displays (UDP/artnet-style matrix protocols); minimal docs [S018].

- License: GPL-2.0 (verified via GitHub API 2026-07-03) [S018].
- Maintenance: dormant — last push 2023-10-03, 16 stars, effectively a personal/space project [S018].
- Form factor: room (fixed matrices).
- Verdict: **waning** — dormant and niche; useful only as a gap-check data point that no maintained general-purpose Python LED engine exists besides LedFx [S018].

### TouchDesigner (as used for LED art)

**Architecture (for LED work):** proprietary node-based realtime visual programming environment; LED workflows render content as textures (TOPs), sample pixels along mapped geometry, and emit via DMX In/Out CHOPs over Art-Net/sACN to pixel controllers (PixLite, Advatek, WLED, etc.). The 2025 release added **DMX POPs** — point-based operators where "each point and primitive represents a copy of the fixture with a position in 3D space", auto-constructing channels/universes or using a routing table — pushing fixture mapping into the geometry system itself [S029]. Practitioners note addressable LEDs still need a network-to-pixel bridge and that sACN is preferred over Art-Net for controller links [S029].

**What it does best / pewpew should steal:** treating LED layout as literal 3D geometry sampled by rendered content (mapping-by-scene-graph), and the texture-sampling model that makes any GPU content an LED pattern for free [S029].

- License: proprietary; free non-commercial tier with resolution limits, paid commercial licenses [S029].
- Maintenance: commercial and active — major 2025 release introduced POPs-based DMX workflow [S029].
- Form factor: room/stage installs tethered to a beefy PC; irrelevant to wearables, marginal for portable [S029].
- Verdict: **stable** (as LED infrastructure) — dominant among media artists for install work, but a closed, heavyweight, host-bound tool; pewpew competes on portability, not against its GPU compositing [S029].

### Hyperion.ng

**Architecture:** C++/Qt daemon for ambient ("bias") lighting: capture sources (screen grabbers, HDMI USB capture, video) feed a priority-muxed pipeline of color transforms (per-channel adjustment, blackbar detection, smoothing/latency filters) out to many device backends (WS281x on Pi, WLED, Philips Hue, Art-Net, serial Adalight); JSON API + web UI; effects engine runs Python-scripted effects as a secondary source [S023].

**What it does best / pewpew should steal:** the priority-source mux (multiple producers bid for the output with priorities and timeouts — clean preemption model for "audio effect overrides ambient unless paused") and its mature smoothing/latency filter chain [S023].

- License: MIT (verified via GitHub API 2026-07-03) [S023].
- Maintenance: active — v2.2.0 2026-02-03, v2.2.1 2026-04-06, repo pushed 2026-07-01 [S023].
- Form factor: room (TV/desk ambient); host-driven; not wearable/portable [S023].
- Verdict: **stable** — steady releases in its ambient-light niche, little relevance beyond it [S023].

### Other systems discovered

- **SmoothLed (mattshepcar):** modern Fadecandy-style interpolation + temporal dithering reimplemented for ATtiny-class MCUs — existence proof that the Fadecandy quality layer fits the wearable tier [S019].
- **fastled-wasm:** browser-compiled FastLED with sub-second recompiles — current best-in-class dev iteration loop; note the `fastled` PyPI package is this compiler CLI, *not* a Python engine [S500][S501].
- Leads not yet sourced (this doc's S-ID block S001–S029 is exhausted; assign IDs in a later pass): ESPixelStick (ESP pixel receiver firmware), NightDriverStrip (Plummer's ESP32 engine), StarLight (MoonLight's predecessor), PXLBLZ third-party Pixelblaze IDE (June 2026) [NEEDS-VERIFICATION].

## Verdicts

| System | Verdict | Rationale (cited above) |
|---|---|---|
| WLED upstream | **ascendant** | v16.0.0 2026-05-03, huge ecosystem, fork harmonization planned [S002] |
| WLED-MM | **stable→waning as a fork** | active, but audio work merging upstream in 16.1.x; team energy in ProjectMM [S002][S005][S024] |
| MoonLight | **waning** | authors froze it at v1.0.0 (2026-05-06) [S006] |
| ProjectMM | **ascendant** | all MoonModules dev moved here; v2.0.0 2026-06-24; very young [S024] |
| FastLED | **ascendant** | 3.10.5 June 2026, 4.0 imminent, substrate for others [S008][S009] |
| Pixelblaze | **waning** | firmware stagnant since 2023-07-13, no roadmap, one person, closed [S014][S025] |
| LedFx | **stable** | steady 2.1.x cadence, v2.1.9 2026-05-18 [S011] |
| xLights | **ascendant** (niche) | biweekly releases through 2026-07-02 [S026] |
| FPP | **stable** | v9.5 2026-01-08, entrenched playback role [S022] |
| Fadecandy | **dead** (product) / **ascendant** (idea) | repo deleted, mirrors only; technique keeps being reimplemented [S027][S019] |
| TouchDesigner | **stable** | commercial, 2025 DMX POPs; closed and host-bound [S029] |
| Hyperion.ng | **stable** | v2.2.1 2026-04-06, ambient niche [S023] |
| BiblioPixel | **dead** | no commits since 2021-02-08 [S028] |
| led-control | **waning** | last push 2023-11-10; still the best Python-pattern-engine prior art [S017] |
| py-ledart | **waning** | last push 2023-10-03, niche [S018] |

## Code-reading queue

Ranked by architecture-shaping value to pewpew:

1. **projectMM (github.com/ewowi/projectMM)** — module runtime: `MoonModule` base class, Layouts→Layers→Drivers pipeline, and how cross-platform (ESP-IDF vs desktop) parity is achieved. Answers: what does a 2026 clean-slate LED engine architecture look like, and what did MoonLight's authors decide was technical debt? [S024]
2. **led-control (github.com/jackw01/led-control)** — pattern-function API (`ledcontrol/animationcontroller.py`, the restricted-code editor path, and the C extension). Answers: what is the per-pixel Python shader model's real API surface and where does it need C? [S017]
3. **Fadecandy mirror (github.com/PimentNoir/fadecandy)** — `server/` keyframe interpolation and firmware dithering loop. Answers: exact interpolation/dither algorithm and its host↔device contract (feeds RA-02/RA-06) [S027][S015].
4. **LedFx (github.com/LedFx/LedFx)** — `ledfx/devices/` + `ledfx/virtuals.py` device/virtual split and output protocol senders. Answers: how to decouple logical canvases from heterogeneous physical outputs in Python [S011].
5. **FastLED (github.com/FastLED/FastLED)** — `src/fl/` async render/output decoupling (3.9.0's 70% speedup) and five_bit_hd_gamma. Answers: how output-driver decoupling and HD gamma are done in the reference implementation [S008][S009].
6. **WLED (github.com/wled/WLED)** — 16.0 segment layering & particle system (`wled00/FX_layer*`, particle FX files). Answers: how layering/compositing was retrofitted onto a segment engine — mistakes to avoid [S001][S002].
7. **xLights (github.com/xLightsSequencer/xLights)** — model definitions & FSEQ writer. Answers: mature declarative layout format worth being compatible with [S026].
8. **SmoothLed (github.com/mattshepcar/SmoothLed)** — the ATtiny interpolation/dither inner loop. Answers: minimum-viable quality layer for the wearable tier [S019].

## Open questions

- Is "Pixelblaze Pico Plus" (forum topic, 2026-06-28) an official new ElectroMage SKU or a community board? A read of the actual thread would settle it [S025][NEEDS-VERIFICATION].
- Was there any Pixelblaze firmware release between v3.47 (2023-07-13) and mid-2026? Forum search suggests no, but the releases category wasn't fully enumerable via fetch; browse forum.electromage.com/c/news-and-announcements/10 directly [S014][NEEDS-VERIFICATION].
- FPP's exact license composition (GitHub reports NOASSERTION); read the repo LICENSE files before any code reuse [S022].
- ProjectMM's v1→v2 jump within weeks of release: what broke, and how stable is the module API? Watch releases; ask on MoonModules Discord.
- WLED-MM's formal position on ProjectMM (will WLED-MM continue after 16.1.x harmonization?) — no explicit maintainer statement found [S005].
- Whether TouchDesigner's non-commercial tier limits (resolution/output) materially block LED-install use — check Derivative licensing page in a later pass [S029][NEEDS-VERIFICATION].
- Uncited leads needing IDs from a future block: ESPixelStick, NightDriverStrip, StarLight, PXLBLZ.
