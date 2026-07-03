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
- license: EUPL-1.2 (verified 2026-07-03)
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
- license: EUPL-1.2 (verified 2026-07-03)
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
- relevance: ground-up ESP32 engine; superseded — frozen at v1.0.0 (2026-05-06), active development moved to projectMM [S024]

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
- license: GPL-3.0 (verified 2026-07-03)
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

### [S015] Fadecandy (original repository, DELETED)
- type: code
- url: https://github.com/scanlime/fadecandy
- author: Micah Elizabeth Scott (scanlime)
- license: MIT
- accessed: 2026-07-03
- relevance: THE canonical "better than clown mode" reference — temporal dithering + keyframe interpolation firmware; original repo deleted by author (404 as of 2026-07-03), community mirrors survive — see [S027]

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
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: closest existing "Python pattern engine done well" — Python functions as fragment shaders, 1D/2D/3D, sACN, ~150 fps on Pi Zero claim

### [S018] py-ledart (TkkrLab)
- type: code
- url: https://github.com/TkkrLab/py-ledart
- license: GPL-2.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: Python LED art framework prior art; confirmed dormant (no activity for years as of 2026-07-03)

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

### [S021] xLights (repository, STALE URL)
- type: code
- url: https://github.com/xLights/xLights
- accessed: 2026-07-03
- relevance: dominant sequencing tool for large displays; this URL 404s as of 2026-07-03 — repo moved, use [S026] (github.com/xLightsSequencer/xLights)

### [S022] Falcon Player / FPP (repository)
- type: code
- url: https://github.com/FalconChristmas/fpp
- accessed: 2026-07-03
- relevance: show player + MultiSync protocol; multi-device sync prior art (seed)

### [S023] Hyperion.ng (repository)
- type: code
- url: https://github.com/hyperion-project/hyperion.ng
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: ambient-light engine; capture→LED pipeline prior art

### [S024] projectMM (ewowi) — MoonLight successor
- type: code
- url: https://github.com/ewowi/projectMM
- author: ewowi (Ewoud Wijma) / MoonModules
- license: GPL-3.0
- published: 2026 (v2.0.0 2026-06-24)
- accessed: 2026-07-03
- relevance: confirmed successor to MoonLight; cross-platform (ESP32/Teensy/Pi/desktop) module runtime, pure ESP-IDF, zero third-party deps

### [S025] ElectroMage forum — "Pixelblaze for Burning Man 2025? Sync/Wifi + New product roadmap?"
- type: forum
- url: https://forum.electromage.com/t/pixelblaze-for-burning-man-2025-sync-wifi-new-product-roadmap/3997
- author: ElectroMage forum users; replies by wizard (Ben Hencke)
- published: 2025-02-15 (thread active through 2026-06-07)
- accessed: 2026-07-03
- relevance: vendor-health signal — Hencke: "I don't have a roadmap shared" (2025-02-19); support active but no firmware since v3.47 (2023)

### [S026] xLights repository (current location)
- type: code
- url: https://github.com/xLightsSequencer/xLights
- author: xLights contributors
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: canonical xLights repo — has MOVED from github.com/xLights/xLights (S021 URL is stale); releases 2026.12 on 2026-07-02

### [S027] Adafruit forum — "Fadecandy server is gone!"
- type: forum
- url: https://forums.adafruit.com/viewtopic.php?t=207469
- accessed: 2026-07-03
- relevance: documents that scanlime deleted the original Fadecandy GitHub repo (S015 URL 404s); names surviving mirrors github.com/PimentNoir/fadecandy and github.com/bluewavenet/fadecandyserver

### [S028] BiblioPixel (ManiacalLabs)
- type: code
- url: https://github.com/ManiacalLabs/BiblioPixel
- author: ManiacalLabs (Adam Haile, Tom Swirly)
- license: MIT
- published: last push 2021-02-08
- accessed: 2026-07-03
- relevance: former general-purpose Python LED framework; confirmed dead (no commits since 2021-02-08 per GitHub API)

### [S029] Interactive & Immersive HQ — "What's New in the 2025 TouchDesigner Release"
- type: article
- url: https://interactiveimmersive.io/blog/touchdesigner-resources/whats-new-in-the-2025-touchdesigner-release/
- author: The Interactive & Immersive HQ
- published: 2025
- accessed: 2026-07-03
- relevance: documents DMX POPs — fixture-as-3D-point mapping workflow in TouchDesigner 2025; state of the art for GPU-based LED mapping

### [S030] BiblioPixel (ManiacalLabs) — dead pure-Python LED framework
- type: code
- url: https://github.com/ManiacalLabs/BiblioPixel
- pinned: ManiacalLabs/BiblioPixel@afb993fbbe56e75e7c98f252df402b0f3e83bb6e
- author: ManiacalLabs (Adam Haile, Dan Ternes, Tom Swirly)
- license: MIT
- published: 2014-11-08 (repo created)
- accessed: 2026-07-03
- relevance: the previous "dominant Python LED engine" (1D/2D/3D layouts, driver abstraction); last commit 2020-10-15 — its unreplaced death is direct evidence for the gap pewpew targets

### [S031] HyperHDR (repository)
- type: code
- url: https://github.com/awawa-dev/HyperHDR
- author: awawa-dev
- license: MIT
- published: 2020-08-01 (repo created)
- accessed: 2026-07-03
- relevance: C++ ambient-lighting engine, 2,021 stars, very active (pushed 2026-07-01); its 2026 "Infinite Color Engine" ships the float-pipeline + temporal-dithering + 16-bit-output stack pewpew wants — strongest output-quality prior art of the 2024–2026 crop

### [S032] HyperHDR v22 release notes (beta1 2026-01-06, beta2 2026-05-08)
- type: docs
- url: https://github.com/awawa-dev/HyperHDR/releases
- author: awawa-dev
- published: 2026-01-06 / 2026-05-08
- accessed: 2026-07-03
- relevance: primary source for Infinite Color Engine: "high-precision floating-point arithmetic" in linear sRGB, deep-color beyond 24-bit incl. HD108 LEDs (beta1, PR #1261); "adaptive temporal dithering" for RGBW with static-scene stabilization (beta2, PRs #1483/#1490)

### [S033] WLEDVideoSync (zak-45)
- type: code
- url: https://github.com/zak-45/WLEDVideoSync
- pinned: zak-45/WLEDVideoSync@f26b6884a2de80d70c915bb58f723a6545e87970
- author: zak-45
- license: MIT
- published: 2024-04-19 (repo created)
- accessed: 2026-07-03
- relevance: highest-starred NEW (2024+) Python LED project found in sweep (64 stars, active 2026-06); a video caster to E1.31/Art-Net/DDP, not a pattern engine — shows new Python energy goes to casting, not engines

### [S034] Chromatik (heronarts) — Digital Lighting Workstation
- type: code
- url: https://github.com/heronarts/Chromatik
- author: Mark C. Slee / heronarts
- license: LX Studio Software License (custom, non-commercial cap — NOT OSI)
- published: 2023-05-16 (repo created); v1.2.1 2025-11-19
- accessed: 2026-07-03
- relevance: LX Studio's successor; the strongest non-Python pattern-engine competitor — DAW-style 3D-first authoring, outputs Art-Net/sACN/OPC/DDP/KiNet with RGBW; Java + license cap keep it out of pewpew's lane

### [S035] LX core library (heronarts/LX)
- type: code
- url: https://github.com/heronarts/LX
- author: Mark C. Slee / heronarts
- license: LX Studio Software License (custom: free non-commercial; commercial use capped at $25K total annual revenue)
- published: 2018-01-08 (repo created); v1.2.1 2025-11-19; pushed 2026-06-19
- accessed: 2026-07-03
- relevance: "Core library for 3D LED lighting engines" underlying Chromatik; decade-refined model/modulation/pattern API worth a design-only read

### [S036] ChimeraFX (effelle)
- type: code
- url: https://github.com/effelle/ChimeraFX
- author: effelle
- license: TBD (GitHub reports NOASSERTION)
- published: 2026-02-02 (repo created)
- accessed: 2026-07-03
- relevance: brand-new (2026) declarative-YAML effect engine for ESP32/ESPHome; 3 stars — too small to compete yet, tracks the Home-Assistant-native approach

### [S037] sacn (PyPI package, Hundemeier)
- type: code
- url: https://pypi.org/project/sacn/
- author: Hundemeier
- license: MIT
- published: v1.11.0 2025-02-18
- accessed: 2026-07-03
- relevance: actively maintained Python E1.31/sACN transport lib — evidence Python has live protocol bricks but no engine on top

### [S038] pyartnet (PyPI package)
- type: code
- url: https://pypi.org/project/pyartnet/
- author: spacemanspiff2007
- license: MIT
- published: v2.0 2025-11-04
- accessed: 2026-07-03
- relevance: actively maintained asyncio Art-Net (also sACN/KiNet) sender for Python; fading/channel abstraction only, no pattern layer

### [S039] stupidArtnet (PyPI package)
- type: code
- url: https://pypi.org/project/stupidArtnet/
- author: cpvalente
- license: MIT
- published: v1.6.0 2025-03-12
- accessed: 2026-07-03
- relevance: third live Python Art-Net lib — confirms transport-layer vitality vs engine-layer vacancy

### [S040] Hacker News — "WLED Project" thread (id 34105815)
- type: forum
- url: https://news.ycombinator.com/item?id=34105815
- published: 2022-12-23
- accessed: 2026-07-03
- relevance: largest HN WLED discussion (232 points, 82 comments): Pixelblaze named 9x, zero mentions of Python/LedFx/BiblioPixel/led-control — mindshare evidence that no Python engine registers as an alternative

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

### [S058] Adafruit Learn — LED Tricks: Gamma Correction
- type: docs
- url: https://learn.adafruit.com/led-tricks-gamma-correction/the-issue
- author: Phillip Burgess (Adafruit)
- accessed: 2026-07-03
- relevance: the community-standard gamma-2.8 8-bit table; also illustrates the low-end code collapse of 8->8 gamma

### [S059] ledshield — "LED Brightness to your eye, Gamma correction – No!"
- type: article
- url: https://ledshield.wordpress.com/2012/11/13/led-brightness-to-your-eye-gamma-correction-no/
- author: HP LED Shield blog
- published: 2012-11-13
- accessed: 2026-07-03
- relevance: argues CIE 1931 L* (not gamma) is the correct perceptual linearization for direct-view LEDs; 16-bit LUT implementation

### [S060] Jared Sanson — "Linear LED PWM"
- type: article
- url: https://jared.geek.nz/2013/02/linear-led-pwm/
- author: Jared Sanson
- published: 2013-02
- accessed: 2026-07-03
- relevance: inverse CIE-L* formula and LUT generator for MCU LED dimming; recommends >=10-bit PWM output

### [S061] photonstophotos — Psychometric Lightness and Gamma
- type: article
- url: https://www.photonstophotos.net/GeneralTopics/Exposure/Psychometric_Lightness_and_Gamma.htm
- author: Bill Claff
- accessed: 2026-07-03
- relevance: quantitative comparison of gamma-2.2 vs CIE L* (18% gray -> 46% vs perceptual 50%)

### [S062] Fadecandy — pixelmatix fork (live mirror of deleted scanlime repo)
- type: code
- url: https://github.com/pixelmatix/fadecandy
- pinned: pixelmatix/fadecandy@5d7657569e6153852d516d5993432c948a7eb59c
- author: Micah Elizabeth Scott (scanlime); fork maintained by Pixelmatix
- license: MIT
- published: last push 2020-12-23
- accessed: 2026-07-03
- relevance: surviving source tree for Fadecandy firmware/server; original scanlime/fadecandy 404s as of 2026-07-03. USB protocol doc details the 16-bit LUT + interpolation + dithering pipeline

### [S063] Ben Hencke (@wizard@leds.social) — Pixelblaze pixel-stack rewrite thread
- type: forum
- url: https://leds.social/@wizard/110703175509817505
- author: Ben Hencke
- published: 2023-07
- accessed: 2026-07-03
- relevance: primary statement that Pixelblaze v3.47 "HDR" = 16-bit-per-element internal pipeline + native WS2816/NS108 48-bit output; NS108 current draw

### [S064] Adafruit NeoPXL8HDR guide
- type: docs
- url: https://learn.adafruit.com/adafruit-neopxl8-featherwing-and-library/neopxl8hdr
- author: Phillip Burgess (Adafruit)
- accessed: 2026-07-03
- relevance: production 16-bit-in / temporal-dither-out library for 8-way parallel WS2812 on RP2040/ESP32-S3; quantifies ~12-13 effective bits and ~1000-pixel budget; built-in gamma + frame blending

### [S065] ElectroMage forum — WS2816 discussion
- type: forum
- url: https://forum.electromage.com/t/ws2816-discussion/1021
- accessed: 2026-07-03
- relevance: WS2816 characteristics as understood by the Pixelblaze community: 16 bit/channel (48-bit), built-in hardware gamma, ~10 kHz refresh

### [S066] WLED Discourse — Gamma Correction thread
- type: forum
- url: https://wled.discourse.group/t/gamma-correction/6070
- accessed: 2026-07-03
- relevance: confirms WLED gamma default 2.8, user-adjustable, applied to colors/brightness in the 8-bit pipeline

### [S067] Wikipedia — Oklab color space
- type: article
- url: https://en.wikipedia.org/wiki/Oklab_color_space
- accessed: 2026-07-03
- relevance: OKLab/OKLCh standardization status (CSS Color Level 4/5) and design goals

### [S068] GitHub search evidence — OKLab adoption in LED projects
- type: forum
- url: https://api.github.com/search/repositories?q=oklab+led
- accessed: 2026-07-03
- relevance: negative result: zero repos matching "oklab led"; issue search shows no OKLab work in FastLED/WLED/Pixelblaze as of 2026-07-03 (only a Nanoleaf screen-mirror tool, SpinGiantCRM/Nanoleaf-Screen-Mirror-for-KDE, uses OKLab)

### [S069] WLED docs — White handling (CCT & auto-white modes)
- type: docs
- url: https://kno.wled.ge/features/cct/
- author: WLED project
- accessed: 2026-07-03
- relevance: definitions of WLED's per-pixel auto-white modes (Accurate/Brighter/Dual/None) and CCT handling for RGBW/CCT strips

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

### [S104] FastLED issue #1311 — change timing to match WS2812B-V5 datasheet
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1311
- accessed: 2026-07-03
- relevance: documents V5 timing drift (T1L, RES) and library-side handling of WS2812B revision churn

### [S105] Tom Verbeure — WS2812B Reset Old & New
- type: article
- url: https://tomverbeure.github.io/2019/10/13/WS2812B_Reset_Old_and_New.html
- author: Tom Verbeure
- published: 2019-10-13
- accessed: 2026-07-03
- relevance: measured incompatibility between 50 µs (old) and 280 µs (new) WS2812B reset requirements

### [S106] WS2812B-V5/W datasheet (WorldSemi, via LCSC)
- type: datasheet
- url: https://www.lcsc.com/datasheet/C2874885.pdf
- author: WorldSemi
- accessed: 2026-07-03
- relevance: current-revision WS2812B timing incl. RESET >280 µs (PDF not machine-extractable via fetch; values cross-checked via S104/S105)

### [S107] cpldcpu — Light_WS2812 V2.0 Part I: Understanding the WS2812
- type: article
- url: https://cpldcpu.com/2014/01/14/light_ws2812-library-v2-0-part-i-understanding-the-ws2812/
- author: Tim (cpldcpu)
- published: 2014-01-14
- accessed: 2026-07-03
- relevance: reverse-engineered real timing tolerances of WS2812; basis for "universal" one-wire timing

### [S108] WS2812B classic datasheet (Adafruit mirror)
- type: datasheet
- url: https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf
- author: WorldSemi
- accessed: 2026-07-03
- relevance: original WS2812B spec: >50 µs reset, ≥400 Hz scan frequency, 800 kbps

### [S109] LCSC product page — WS2812B-2020
- type: product
- url: https://www.lcsc.com/product-detail/RGB-LEDs-Built-in-IC_Worldsemi-WS2812B-2020_C965555.html
- accessed: 2026-07-03
- relevance: WS2812B-2020 (2020 package) with 2 kHz port refresh frequency vs 400 Hz classic

### [S110] NeoPixelBus PR #795 — WS2812x ESP32 RMT timing for WS2815 compat
- type: forum
- url: https://github.com/Makuna/NeoPixelBus/pull/795
- accessed: 2026-07-03
- relevance: library-side evidence of WS2815/WS2812 timing unification

### [S111] WS2815 datasheet (Normand LED mirror)
- type: datasheet
- url: https://www.normandled.com/upload/201808/WS2815%20LED%20Datasheet.pdf
- author: WorldSemi
- accessed: 2026-07-03
- relevance: WS2815 12 V, BIN backup data input behavior, constant-current spec (~15 mA white)

### [S112] SDIP Light — What is WS2815 and how to use it
- type: article
- url: https://www.sdiplight.com/what-is-ws2815-and-how-to-use-ws2815-led/
- accessed: 2026-07-03
- relevance: WS2815 practical characteristics: per-pixel addressing at 12 V, failure bypass, power behavior

### [S113] WLED forum — Wiring of WS2815 question
- type: forum
- url: https://wled.discourse.group/t/wiring-of-ws2815-question/5626
- accessed: 2026-07-03
- relevance: field wiring practice: BI tied to GND at strip head

### [S114] SK6812 technical datasheet (Adafruit mirror)
- type: datasheet
- url: https://cdn-shop.adafruit.com/product-files/1138/SK6812+LED+datasheet+.pdf
- author: Opsco Optoelectronics
- accessed: 2026-07-03
- relevance: SK6812 timing, 1.2 kHz PWM, RGBW data format

### [S115] SuperLightingLED blog — SK6812 vs WS2812B
- type: article
- url: https://www.superlightingled.com/blog/sk6812-vs-ws2812b/
- accessed: 2026-07-03
- relevance: vendor comparison: PWM rates (1.2 kHz vs 400 Hz), timing margin, brightness

### [S116] TM1814 datasheet (Titan Micro, SuperLightingLED mirror)
- type: datasheet
- url: https://www.superlightingled.com/PDF/TM1814-TitanMicro.pdf
- author: Titan Micro Electronics
- accessed: 2026-07-03
- relevance: TM1814 WRGB 32-bit format, 800 kbps, 6.5–38 mA settable constant current

### [S117] Adafruit Learning — Driving TM1814 addressable LEDs
- type: docs
- url: https://learn.adafruit.com/driving-tm1814-addressable-leds/overview
- author: Jeff Epler / Adafruit
- accessed: 2026-07-03
- relevance: TM1814 inverted-signal requirement, settings frame, driver support

### [S118] Advatek — TM1814 pixel protocol page
- type: docs
- url: https://www.advateklighting.com/pixel-protocols/tm1814
- accessed: 2026-07-03
- relevance: pro-controller support and positioning of TM1814

### [S119] BTF-Lighting product — WS2814 12V/24V RGBW strip
- type: product
- url: https://www.btf-lighting.com/products/ws2814-12v-24v-4-in-1-similar-sk6812-rgbw-pixels-addressable-ws2811-rgbww-rgbcw-5050-3pin-led-lights
- accessed: 2026-07-03
- relevance: WS2814 commodity availability, 12/24 V RGBW form factors, SK6812-compat claim

### [S120] WS2814 RGBW datasheet (SuperLightingLED mirror)
- type: datasheet
- url: https://www.superlightingled.com/PDF/SPEC/WS2814-RGBW-Datasheet.pdf
- author: WorldSemi
- accessed: 2026-07-03
- relevance: WS2814 4-channel driver, 20 V constant-current outputs, RGBW order high-bit-first

### [S121] ElectroMage forum — Trying out WS2814 (officially supported)
- type: forum
- url: https://forum.electromage.com/t/trying-out-ws2814-update-officially-supported/2644
- accessed: 2026-07-03
- relevance: WS2814 color-order gotcha vs SK6812 GRBW; Pixelblaze added explicit support

### [S122] FastLED issue #1855 — support WS2816 LEDs
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1855
- accessed: 2026-07-03
- relevance: WS2816 48-bit GRB format, hardware gamma, ~10 kHz refresh; FastLED support discussion

### [S123] WS2816B-2020 datasheet (TME mirror)
- type: datasheet
- url: https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf
- author: WorldSemi
- accessed: 2026-07-03
- relevance: 16-bit/channel, 65536 grayscale, built-in 4-bit gamma, 2020 package

### [S124] NeoPixelBus issue #357 — WS2816 support
- type: forum
- url: https://github.com/Makuna/NeoPixelBus/issues/357
- accessed: 2026-07-03
- relevance: second-library support status for WS2816

### [S125] BTF-Lighting blog — FCOB RGBCCT dual-IC addressable strips
- type: article
- url: https://www.btf-lighting.com/blogs/blog/illuminating-innovation-btf-lighting-fcob-rgbcct-dual-ic-addressable-led-strips-ws2811
- accessed: 2026-07-03
- relevance: FCOB addressable trend, 840–960 LED/m densities, RGBCCT dual-IC

### [S126] Shiji Lighting — Future trends in addressable LED strip technology
- type: article
- url: https://www.shiji-leds.com/blog/future-trends-in-addressable-led-strip-technology-and-applications/
- accessed: 2026-07-03
- relevance: 2026 market drift toward 24 V/48 V pixel systems and higher-refresh chips

### [S127] FastLED wiki — Temporal Dithering
- type: docs
- url: https://github.com/FastLED/FastLED/wiki/FastLED-Temporal-Dithering
- author: FastLED project (Mark Kriegsman)
- accessed: 2026-07-03
- relevance: dithering quality proportional to refresh rate; the mechanism behind the strip-length dithering ceiling

### [S128] cpldcpu — SK9822: a clone of the APA102?
- type: article
- url: https://cpldcpu.com/2016/12/13/sk9822-a-clone-of-the-apa102/
- author: Tim (cpldcpu)
- published: 2016-12-13
- accessed: 2026-07-03
- relevance: measured PWM rates (APA102 ~19.2 kHz + ~440 Hz global-brightness PWM; SK9822 4.7 kHz + current-source global brightness); latch/update and end-frame differences

### [S129] cpldcpu — Understanding the APA102 "Superled"
- type: article
- url: https://cpldcpu.com/2014/11/30/understanding-the-apa102-superled/
- author: Tim (cpldcpu)
- published: 2014-11-30
- accessed: 2026-07-03
- relevance: APA102 clock regeneration (half-cycle delay per pixel), end-frame length n/2, achievable SPI clock rates

### [S130] FastLED PR #2119 — hd108: initial working state (merged)
- type: code
- url: https://github.com/FastLED/FastLED/pull/2119
- author: arfoll / FastLED
- license: MIT
- accessed: 2026-07-03
- relevance: native HD108 16-bit support merged into FastLED master 2025-10-30

### [S131] Hida — 48 pixels/m 16-bit HD108 LED strip product page
- type: product
- url: https://www.hd108-led.com/product/48pixels-hd108-led-strip/
- author: Hida (Shenzhen)
- accessed: 2026-07-03
- relevance: real-world HD108 strip availability and form factor from the originating manufacturer

### [S132] Newstar — NS108/HD108 16-bit LED strip page
- type: product
- url: https://addressableledstrip.com/NS108HD108LEDStrip-34/19.html
- author: Newstar LED Co.
- accessed: 2026-07-03
- relevance: NS108 as second source; NS108/HD108 equivalence in vendor positioning

### [S133] Adafruit Learning — Level Shifting 3.3V microcontrollers and NeoPixels
- type: docs
- url: https://learn.adafruit.com/neopixel-levelshifter
- author: Adafruit
- accessed: 2026-07-03
- relevance: 74AHCT125 as canonical WS281x level shifter; why I2C MOSFET shifters fail at 800 kHz

### [S134] Hackaday — Cheating at 5V WS2812 control to use 3.3V data
- type: article
- url: https://hackaday.com/2017/01/20/cheating-at-5v-ws2812-control-to-use-a-3-3v-data-line/
- published: 2017-01-20
- accessed: 2026-07-03
- relevance: sacrificial-pixel / diode-drop level-shift technique

### [S135] QuinLED — The Ultimate LED Strip Power Injection Guide
- type: docs
- url: https://quinled.info/the-ultimate-led-strip-power-injection-guide/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- relevance: voltage-drop budgets, wire gauge tables, injection-point spacing practice

### [S136] QuinLED — How much power do addressable LEDs use?
- type: docs
- url: https://quinled.info/2020/03/12/digital-led-power-usage/
- author: Quindor
- published: 2020-03-12
- accessed: 2026-07-03
- relevance: measured per-strip power draw vs theoretical 60 mA/pixel folklore

### [S137] QuinLED — 24v power distribution for 5v LEDs
- type: docs
- url: https://quinled.info/24v-power-distribution-for-5v-leds/
- author: Quindor
- accessed: 2026-07-03
- relevance: distribute-high-voltage, buck-locally pattern for large 5 V installs

### [S138] WLED forum — ESP32 + SN74AHCT125N wiring, max data cable length to SK6812
- type: forum
- url: https://wled.discourse.group/t/esp32-sn74ahct125n-wiring-max-length-data-cable-to-sk6812/2294
- accessed: 2026-07-03
- relevance: field wiring of AHCT125, series resistor values, practical data-run lengths

### [S139] QuinLED — Why Ethernet cable isn't suitable for LEDs
- type: docs
- url: https://quinled.info/why-ethernet-cable-cat5e-cat6-etc-isnt-suitable-for-leds/
- author: Quindor
- accessed: 2026-07-03
- relevance: conductor gauge limits of Cat5e/6 for pixel power/data runs

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

### [S153] WLED changelog — DDP realtime support added in 0.11.0
- type: docs
- url: https://github.com/wled/WLED/blob/main/CHANGELOG.md
- author: WLED contributors (Aircoookie et al.)
- license: EUPL-1.2
- accessed: 2026-07-03
- relevance: dates WLED's DDP receive (0.11.0, 2020-11) and DDP send (0.13) support

### [S154] xLights documentation — controller output protocols (DDP, E1.31, Art-Net)
- type: docs
- url: https://manual.xlights.org/
- author: xLights contributors
- accessed: 2026-07-03
- relevance: confirms DDP as a mainstream sequencer output alongside E1.31/Art-Net

### [S155] Falcon Player (FPP) documentation — channel outputs incl. DDP
- type: docs
- url: https://falconchristmas.github.io/FPP_Manual(5.0).pdf
- author: Falcon Christmas / FPP contributors (Rick Harris)
- published: 2021-08-07
- accessed: 2026-07-03
- relevance: FPP output support for DDP/E1.31/Art-Net; MultiSync protocol owner

### [S156] LedFx — Python engine DDP device implementation
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/devices/ddp.py
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx contributors
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: existing Python engine that chose DDP as primary transport

### [S157] ANSI E1.31-2016 — Entertainment Technology: Lightweight streaming protocol for transport of DMX512 using ACN
- type: spec
- url: https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
- author: ESTA Technical Standards Program (CP/2014-1009r3)
- published: 2016
- accessed: 2026-07-03
- relevance: normative sACN packet layout (126-byte overhead + 513 data), priority 0-200, sync packets, 2.5s data-loss timeout, multicast mapping

### [S158] WLED knowledge base — E1.31/Art-Net/DDP interfaces and multicast guidance
- type: docs
- url: https://kno.wled.ge/interfaces/e1.31-dmx/
- author: WLED contributors
- accessed: 2026-07-03
- relevance: WLED receiver behavior for sACN/Art-Net/DDP; unicast-over-multicast guidance on WiFi

### [S159] Art-Net 4 Protocol Release V1.4 (rev 1.4dp, 2025-10-23)
- type: spec
- url: https://art-net.org.uk/downloads/art-net.pdf
- author: Artistic Licence Engineering Ltd
- license: royalty-free use, copyright Artistic Licence, trademark credit required
- published: 2025-10-23
- accessed: 2026-07-03
- relevance: normative ArtDmx (18B header + 512B), unicast-only ArtDmx rule, ArtSync semantics with 4s timeout, 40/400/4000 universe rule of thumb

### [S160] Open Pixel Control protocol description
- type: spec
- url: http://openpixelcontrol.org/
- author: Ka-Ping Yee (protocol page); ecosystem by Micah Scott (FadeCandy)
- accessed: 2026-07-03
- relevance: OPC wire format (4-byte header, TCP), 8-bit-only standard messages

### [S161] scanlime/fadecandy — archived GitHub repository
- type: code
- url: https://github.com/scanlime/fadecandy
- author: Micah Elizabeth Scott
- license: MIT (firmware/server mixed licenses)
- accessed: 2026-07-03
- relevance: evidence OPC's flagship implementation is discontinued/archived — waning verdict

### [S162] WLED knowledge base — UDP Realtime Control (WARLS/DRGB/DRGBW/DNRGB)
- type: docs
- url: https://kno.wled.ge/interfaces/udp-realtime/
- author: WLED contributors
- accessed: 2026-07-03
- relevance: byte layouts, per-packet LED limits, timeout semantics of WLED-native realtime UDP

### [S163] FPP ControlProtocol.txt — MultiSync wire protocol
- type: docs
- url: https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt
- author: Falcon Christmas / FPP contributors
- license: GPL-2.0 (FPP repo)
- accessed: 2026-07-03
- relevance: MultiSync packet format — port 32320, multicast 239.70.80.80, frame-number sync of pre-stored sequences

### [S164] xLights Manual — Controllers Settings / lighting networks (protocol support matrix)
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks
- author: xLights contributors
- accessed: 2026-07-03
- relevance: lists DDP support across FPP/Kulp, HinksPix, Falcon v3/v4/v5, WLED, Genius, Minleon; calls DDP more efficient than Art-Net/E1.31

### [S165] WLED knowledge base — FAQ (LED count, WiFi limits, DDP and Ethernet recommendations)
- type: docs
- url: https://kno.wled.ge/basics/faq/
- author: WLED contributors
- accessed: 2026-07-03
- relevance: 750-LED per-controller guidance, 720 kbit/s @1000 LED/30fps, DDP-over-E1.31 recommendation, QuinLED/Olimex Ethernet advice

### [S166] Electric UI — "Latency comparison of common wireless links for microcontrollers"
- type: article
- url: https://electricui.com/blog/latency-comparison
- author: Electric UI
- published: 2024-02
- accessed: 2026-07-03
- relevance: logic-analyzer-measured ESP32 WiFi latency: 74-84 ms default config; ~6 ms TCP / ~9 ms UDP median, ~25 ms outliers after power-save/Nagle/IRAM tuning

### [S167] espressif/esp-idf issue #15345 — "Making UDP send latency more predictable (reducing jitter)"
- type: forum
- url: https://github.com/espressif/esp-idf/issues/15345
- author: esp-idf users / Espressif
- accessed: 2026-07-03
- relevance: documents FreeRTOS-scheduler-driven UDP jitter tail on ESP32; power-save (WIFI_PS_NONE) as main latency lever

### [S168] ESP32 forum — "UDP packet delays" (noisy-WiFi delay measurements)
- type: forum
- url: https://esp32.com/viewtopic.php?t=27665
- author: esp32.com community
- accessed: 2026-07-03
- relevance: reported 200-388 ms UDP delays in congested RF — worst-case WiFi tail for realtime pixels

## Block S200–S249 — RA-05 Pattern-engine design

### [S200] ElectroMage / Pixelblaze documentation
- type: docs
- url: https://electromage.com/docs/
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: the expression-language + (index, x, y, z) render model — best-in-class pattern authoring to learn from

### [S201] Pixelblaze expression language reference (README.expressions.md)
- type: docs
- url: https://github.com/simap/pixelblaze/blob/master/README.expressions.md
- pinned: simap/pixelblaze@209c587253236301e0e7391e1635d5c553791ba8
- author: Ben Hencke (simap)
- license: none stated in repo (docs for closed firmware)
- accessed: 2026-07-03
- relevance: authoritative spec of the Pixelblaze language: 16.16 fixed point, render/render2D/render3D + beforeRender(delta), time()/wave() built-ins, live compile

### [S202] Pixelblaze mapper reference (README.mapper.md)
- type: docs
- url: https://github.com/simap/pixelblaze/blob/master/README.mapper.md
- pinned: simap/pixelblaze@209c587253236301e0e7391e1635d5c553791ba8
- author: Ben Hencke (simap)
- license: none stated in repo
- accessed: 2026-07-03
- relevance: coordinate normalization to 0..1 "world units" from arbitrary physical units

### [S203] Pixelblaze V3 Crowd Supply update — "Manufacturing, UI Controls, POV!"
- type: article
- url: https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3/updates/manufacturing-ui-controls-pov
- author: Ben Hencke
- published: 2020 (campaign update)
- accessed: 2026-07-03
- relevance: introduces convention-based UI controls (sliderSpeed, hsvPickerColor) generated from exported function names

### [S204] Pixelblaze Sensor Expansion Board (ElectroMage shop / bhencke.com)
- type: product
- url: https://www.bhencke.com/pixelblaze-sensor-expansion
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: sensor feature injection as exported pattern variables (frequencyData[32], energyAverage, accelerometer[3], light, analogInputs[5])

### [S205] WLED docs — Custom Features (adding effects via usermods)
- type: docs
- url: https://kno.wled.ge/advanced/custom-features/
- author: WLED project
- accessed: 2026-07-03
- relevance: effect function signature (free void fn + SEGMENT/SEGENV/SEGLEN macros), strip.addEffect registration, PROGMEM metadata string, compile-in-only effects

### [S206] WLED issue #3478 — effect metadata consistency (metadata string format)
- type: forum
- url: https://github.com/Aircoookie/WLED/issues/3478
- author: WLED maintainers/contributors
- accessed: 2026-07-03
- relevance: documents the `name@sliders;colors;palette;flags;defaults` metadata DSL and fixed slider slots (sx/ix/custom)

### [S207] WLED MoonModules — ARTI-FX documentation
- type: docs
- url: https://mm.kno.wled.ge/moonmodules/arti-fx/
- author: MoonModules (ewowi et al.)
- accessed: 2026-07-03
- relevance: runtime-interpreted effect language bolted onto WLED-SR; renderFrame/renderLed split; Pixelblaze-compat functions; evidence WLED authoring model is a felt bottleneck

### [S208] LedFx effect base module (ledfx/effects/__init__.py)
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/effects/__init__.py
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx team
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: Effect base class, render() on self.pixels NumPy (N,3), voluptuous CONFIG_SCHEMA merged up MRO, universal blur/flip/mirror knobs

### [S209] LedFx audio analysis + AudioReactiveEffect (ledfx/effects/audio.py)
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx team
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: shared AudioAnalysisSource (melbanks/pitch/onset/bar_oscillator), audio_data_updated callback, per-virtual frequency-range melbank helper

### [S210] led-control documentation site
- type: docs
- url: https://jackw01.github.io/led-control/
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- author: jackw01
- license: MIT
- accessed: 2026-07-03
- relevance: Python-as-fragment-shader signature (t, dt, x, y, z, prev_state), RestrictedPython + C-extension perf split, 150 fps @ 150 RGBW on Pi Zero claim; repo dormant since 2023-11-10

### [S211] todbot — "Speed up CircuitPython LED animations 10x!" (+ code repo)
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt (todbot)
- published: 2022-10-21
- accessed: 2026-07-03
- relevance: measured vectorization gain: fire effect, 256 LEDs, RP2040 — ~40 ms/frame Python loop vs ~4 ms/frame ulab; working-copy idiom (code: github.com/todbot/circuitpython_led_effects)

### [S212] scottlawsonbc/audio-reactive-led-strip
- type: code
- url: https://github.com/scottlawsonbc/audio-reactive-led-strip
- author: Scott Lawson
- license: MIT
- accessed: 2026-07-03
- relevance: archetypal NumPy-per-frame audio visualizer (ancestor of LedFx); Pi "just fast enough" at ~256 px; unmaintained (archived-era, last activity ~2018)

### [S213] TouchDesigner DMX/Art-Net LED mapping workflow (Derivative workshop + TouchLED)
- type: docs
- url: https://derivative.ca/workshop/dmx-artnet-and-led-mapping-touchdesigner/71671
- also: https://github.com/yastefan/TouchLED-DMX
- author: Derivative / yastefan
- accessed: 2026-07-03
- relevance: canonical GPU route — TOP sampled at SOP fixture points, DMX CHOP emits Art-Net/sACN; TouchLED library wraps mapping+visualizer

### [S214] ISF — Interactive Shader Format specification
- type: spec
- url: https://isf.vidvox.net/ (spec repo: https://github.com/mrRay/ISF_Spec/)
- author: VIDVOX (mrRay)
- accessed: 2026-07-03
- relevance: GLSL fragment shader + JSON header declaring typed INPUTS — best-in-class parameter-manifest design for auto-generated UIs

### [S215] ENTTEC ELM Effects documentation
- type: docs
- url: https://support.enttec.com/dmx-software/elm/elm-effects
- author: ENTTEC
- accessed: 2026-07-03
- relevance: commercial media-server bridge; every effect parameter remotely controllable via DMX/Art-Net/sACN/OSC/HTTP — parameter-as-address pattern

### [S216] Chromatik / LX — "Coding in LX" developer guide
- type: docs
- url: https://chromatik.co/develop/coding/
- author: Mark Slee / heronarts
- accessed: 2026-07-03
- relevance: first-class parameter objects: addParameter + CompoundParameter(label, init, min, max) → auto UI knob + MIDI/OSC mapping + LFO modulation; LXPattern.run(deltaMs) lifecycle

## Block S250–S299 — RA-06 Frame pipeline & motion quality

### [S250] ElectroMage forum — "Rendered FPS vs maximum refresh rate ... for strobing"
- type: forum
- url: https://forum.electromage.com/t/rendered-fps-vs-maximum-refresh-rate-for-strobing/3255
- author: Ben Hencke (wizard) et al.
- accessed: 2026-07-03
- relevance: authoritative statement of Pixelblaze's frame pacing model — free-running render, pipelined WS2812 output, frame skip on overdraw

### [S251] ElectroMage forum — "Output expander that implements Fadecandy dithering"
- type: forum
- url: https://forum.electromage.com/t/output-expander-that-implements-fadecandy-dithering/840
- author: Ben Hencke (wizard) et al.
- accessed: 2026-07-03
- relevance: Hencke's rationale for NOT doing Fadecandy-style temporal dithering (refresh-rate coupling, 64-LED cap) and preferring APA102-class global brightness / HDR chips

### [S252] WLED issue #5408 — "FPS target set to 0 by default"
- type: forum
- url: https://github.com/wled/WLED/issues/5408
- accessed: 2026-07-03
- relevance: documents WLED's intended default target FPS of 42, the 1000/42 frametime constant, and that FPS 0 = "unlimited, not recommended, experimental"

### [S253] WLED docs — UDP Realtime / WARLS / DRGB / DNRGB
- type: docs
- url: https://kno.wled.ge/interfaces/udp-realtime/
- author: WLED project
- accessed: 2026-07-03
- relevance: WLED's loss handling for realtime pixel streams — timeout byte, hold-then-revert semantics, per-protocol LED-count limits, no smoothing/interpolation

### [S254] LedFx — virtuals.py frame loop (code)
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/virtuals.py
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx team
- license: GPL-3.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: LedFx's per-virtual frame clock — compensated sleep loop, refresh rate = min of member devices, 0.4 s default effect crossfade, removed interpolation dead code

### [S255] led-control — IntervalTimer scheduler (code)
- type: code
- url: https://github.com/jackw01/led-control/blob/master/ledcontrol/intervaltimer.py
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- author: jackw01
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: led-control's frame scheduler — cycle-time-compensated interval thread, default 60 fps, Windows drift variant; paired with time-parameterized (t, dt) pattern functions

### [S256] FPP — ControlProtocol.txt (MultiSync wire format)
- type: spec
- url: https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt
- author: FalconChristmas / FPP developers
- accessed: 2026-07-03
- relevance: MultiSync packet layout — UDP 32320, multicast 239.70.80.80, sync packet with frame number + elapsed-seconds float + filename; playback-position sync model

### [S257] WLED docs — UDP Sync (notifier)
- type: docs
- url: https://kno.wled.ge/interfaces/udp-notifier/
- author: WLED project
- accessed: 2026-07-03
- relevance: WLED sync is state-only (brightness/color/effect/palette in ~24-byte packet); no frame or clock synchronization exists

### [S258] Cryptkeeper — fseq-file-format (reverse-engineered FSEQ v2 spec)
- type: spec
- url: https://github.com/Cryptkeeper/fseq-file-format
- author: Cryptkeeper (Nick Krecklow)
- accessed: 2026-07-03
- relevance: FSEQ v2 header — uint8 step time in ms at byte 18 (20-30 fps typical), frame/channel counts, zstd/zlib chunk compression; fixes the xLights/FPP ecosystem's authoring frame rate

### [S259] ANSI E1.31-2016 — Lightweight streaming protocol for transport of DMX512 (sACN)
- type: spec
- url: https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
- author: ESTA Technical Standards Program
- published: 2016-10-11
- accessed: 2026-07-03
- relevance: Universe Synchronization packets (added in 2016 revision) — buffered data latched on sync packet per Synchronization Address; sync address 0 reserved/ignored

### [S260] Mark Kriegsman — "Anti-aliased light bar example" (FastLED demo)
- type: code
- url: https://pastebin.com/yAgKs0Ay
- author: Mark Kriegsman
- published: 2013-11-29
- accessed: 2026-07-03
- relevance: canonical sub-pixel strip motion technique — 1/16th-pixel positions, coverage-proportional edge brightness; the reference every later AA-on-a-strip discussion cites

### [S261] FastLED — release_notes.md (sub-pixel rendering, XYPath, fl:: raster)
- type: docs
- url: https://github.com/FastLED/FastLED/blob/master/release_notes.md
- author: FastLED project (Zach Vorhies et al.)
- license: MIT
- accessed: 2026-07-03
- relevance: only framework with first-class sub-pixel drawing — float-coordinate 2x2 splatting ("256 effective steps ... between neighbors"), XYPath rasterization to sparse rasters

### [S262] FastLED — lib8tion.h easing functions (code)
- type: code
- url: https://github.com/FastLED/FastLED/blob/master/src/lib8tion.h
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
- author: FastLED project
- license: MIT
- accessed: 2026-07-03
- relevance: de facto easing norms in LED land — ease8InOutQuad, ease8InOutCubic (3x^2-2x^3 smoothstep), ease8InOutApprox, 16-bit variants; fixed-point, pattern-side

### [S263] AusChristmasLighting forum — "Convert 20 to 40 fps"
- type: forum
- url: https://auschristmaslighting.com/threads/convert-20-to-40-fps.13740/
- accessed: 2026-07-03
- relevance: practitioner norms on show frame rates — 20 fps legacy standard, 40 fps recommended for dense/HD modern displays

### [S264] heronarts/LX — LXEngine.java (code)
- type: code
- url: https://github.com/heronarts/LX/blob/master/src/main/java/heronarts/lx/LXEngine.java
- pinned: heronarts/LX@b7c10b3cf5d588de6bd95fb9200eb649b77f366c
- author: Mark Slee / Heron Arts
- license: custom "CHROMATIK / LX SOFTWARE LICENSE AND DISTRIBUTION AGREEMENT" (source-available, NOT OSI; verified header 2026-07-03 — read terms before any reuse)
- accessed: 2026-07-03
- relevance: mature engine frame clock — FPS BoundedParameter default 60 (range 1-300), scheduleAtFixedRate render loop, separate 60 Hz input tick, actual-frame-rate measurement, deltaMs clamping

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

### [S303] WLED knowledge base — Mapping (ledmap.json)
- type: docs
- url: https://kno.wled.ge/advanced/mapping/
- author: WLED contributors
- accessed: 2026-07-03
- relevance: canonical spec of WLED ledmap.json index-permutation format, -1 gaps, width/height 2D keys, per-preset map selection

### [S304] Pixelblaze mapper README (simap/pixelblaze)
- type: docs
- url: https://github.com/simap/pixelblaze/blob/master/README.mapper.md
- author: Ben Hencke
- accessed: 2026-07-03
- relevance: spec of Pixelblaze pixel-map JSON, map generator functions, 0..1 world-unit normalization, Fill/Contain scaling, render2D/render3D

### [S305] LedFx docs — "How to: Create and Edit Virtuals"
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/virtuals.html
- author: LedFx contributors
- accessed: 2026-07-03
- relevance: defines virtuals/segments (device,start,end,reverse), span vs copy modes, rows/grouping 2D reshaping, complex-segments numpy fast path

### [S306] xLights manual — Custom Model
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/custom-model
- author: xLights contributors
- accessed: 2026-07-03
- relevance: custom-model node-number grid format, depth for 3D voxel models, .xmodel export

### [S307] xLights manual — Model Settings (buffer styles)
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/model-attribute
- author: xLights contributors
- accessed: 2026-07-03
- relevance: buffer render styles decouple effect buffer layout from wiring; per-model and group buffer styles

### [S308] FPP manual — Pixel Overlay Models
- type: docs
- url: https://falcon-player.gitbooks.io/falcon-player-manual/content/chapter_five_inputoutput_setup/pixel_overlay_models.html
- author: FalconChristmas contributors
- accessed: 2026-07-03
- relevance: FPP channel-arithmetic model definition (start channel, strands/strings, orientation) and overlay/transparency states

### [S309] Chromatik guide — Custom Fixtures (.lxf format)
- type: docs
- url: https://chromatik.co/guide/custom-fixtures/
- author: Mark Slee / Heron Arts
- accessed: 2026-07-03
- relevance: the most complete declarative LED map format: point/points/strip/arc components, nested fixtures, translate/yaw-pitch-roll transforms, +Y-up convention, parametric variables, per-component protocol outputs

### [S310] ElectroMage forum — "Automatic Mapping Preview" (zranger1)
- type: forum
- url: https://forum.electromage.com/t/automatic-mapping-preview/3453
- author: zranger1
- published: 2024-03-11
- accessed: 2026-07-03
- relevance: OpenCV webcam auto-mapper for Pixelblaze; JSON/CSV export or direct push; documents practical CV pitfalls (auto-exposure frame discard, reflections); prototype at github.com/zranger1/CVTest

### [S311] ElectroMage forum — 2D pixel coordinate mapping tool for images
- type: forum
- url: https://forum.electromage.com/t/2d-pixel-coordinate-mapping-tool-for-images/714
- accessed: 2026-07-03
- relevance: manual click-on-photo mapping tool emitting Pixelblaze map JSON — the low-tech manual path

### [S312] L.E.D. Lab (iOS app, App Store listing)
- type: product
- url: https://apps.apple.com/us/app/l-e-d-lab/id832042156
- author: Christopher Schardt
- accessed: 2026-07-03
- relevance: mature commercial phone/tablet camera-mapping path; photographic map files; drives LEDs over Art-Net, layers over WLED

### [S313] savdb/led_camera_map
- type: code
- url: https://github.com/savdb/led_camera_map
- author: savdb
- license: MIT
- accessed: 2026-07-03
- relevance: OpenCV + Art-Net blink mapper that emits WLED ledmap.json directly; automates WLED's manual format

### [S314] Vitminee/wled-mapper
- type: code
- url: https://github.com/Vitminee/wled-mapper
- author: Vitminee
- license: TBD
- accessed: 2026-07-03
- relevance: camera capture to WLED ledmap + 2D gap mask export; AI-assisted authorship; recent hobby tool

### [S315] ENTTEC ELM pixel-mapping software (product page)
- type: product
- url: https://www.enttec.com/product/dmx-lighting-control-software/pixel-mapping-software/
- author: ENTTEC
- accessed: 2026-07-03
- relevance: commercial 2D/3D pixel mapper with DXF CAD import — CAD-drawing (not camera) mapping convention in the pro space

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
