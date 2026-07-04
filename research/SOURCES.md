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
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
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
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
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
- archive: https://web.archive.org/web/20260505174829/https://electromage.com/pixelblaze/  # snapshot 2026-05-05
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
- archive: https://web.archive.org/web/20250706105326/https://www.misc.name/fadecandy/  # snapshot 2025-07-06
- relevance: design philosophy behind dithering/interpolation choices

### [S017] led-control (jackw01)
- type: code
- url: https://github.com/jackw01/led-control
- docs: https://jackw01.github.io/led-control/
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6  # master at read time; repo dormant since 2023-11-10
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
- archive: pending (archive.org save returned 520 on 2026-07-03, twice; origin 403s non-browser clients — likely anti-bot, not dead; no prior wayback snapshot exists)
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
- archive: https://web.archive.org/web/20260704005340/https://github.com/awawa-dev/HyperHDR/releases  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260704005414/https://github.com/FastLED/FastLED/wiki/FastLED-Temporal-Dithering  # captured 2026-07-03
- relevance: binary dithering design: preserves color/light output at low master brightness; needs >400 Hz refresh
- note: same underlying source as [S127] — do not co-cite the pair as independent corroboration

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
- archive: https://web.archive.org/web/20260704005444/https://github.com/wled/WLED/issues/2416  # captured 2026-07-03
- relevance: feasibility discussion of Fadecandy-grade dithering inside WLED's architecture — instructive about WLED's limits

### [S055] Björn Ottosson — OKLab color space
- type: article
- url: https://bottosson.github.io/posts/oklab/
- author: Björn Ottosson
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260627175017/https://bottosson.github.io/posts/oklab/  # snapshot 2026-06-27
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
- archive: https://web.archive.org/web/20260308001421/https://learn.adafruit.com/led-tricks-gamma-correction/the-issue  # snapshot 2026-03-08
- relevance: the community-standard gamma-2.8 8-bit table; also illustrates the low-end code collapse of 8->8 gamma

### [S059] ledshield — "LED Brightness to your eye, Gamma correction – No!"
- type: article
- url: https://ledshield.wordpress.com/2012/11/13/led-brightness-to-your-eye-gamma-correction-no/
- author: HP LED Shield blog
- published: 2012-11-13
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260105233202/https://ledshield.wordpress.com/2012/11/13/led-brightness-to-your-eye-gamma-correction-no/  # snapshot 2026-01-05
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
- archive: https://web.archive.org/web/20260124202640/https://photonstophotos.net/GeneralTopics/Exposure/Psychometric_Lightness_and_Gamma.htm  # snapshot 2026-01-24
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
- archive: https://web.archive.org/web/20260704005522/https://leds.social/@wizard/110703175509817505  # captured 2026-07-03
- relevance: primary statement that Pixelblaze v3.47 "HDR" = 16-bit-per-element internal pipeline + native WS2816/NS108 48-bit output; NS108 current draw

### [S064] Adafruit NeoPXL8HDR guide
- type: docs
- url: https://learn.adafruit.com/adafruit-neopxl8-featherwing-and-library/neopxl8hdr
- author: Phillip Burgess (Adafruit)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260413181215/https://learn.adafruit.com/adafruit-neopxl8-featherwing-and-library/neopxl8hdr  # snapshot 2026-04-13
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
- archive: https://web.archive.org/web/20260704005615/https://api.github.com/search/repositories?q=oklab+led  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260704005653/https://github.com/FastLED/FastLED/issues/1045  # captured 2026-07-03
- relevance: 16-bit chip protocol details and library support discussion

### [S101] Superlightingled — SK9822 vs APA102 vs APA107 vs HD107(s) vs HD108
- type: article
- url: https://www.superlightingled.com/blog/sk9822-vs-apa102-vs-apa107-vs-hd107-vs-hd107s-vs-hd108/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250926214129/https://www.superlightingled.com/blog/sk9822-vs-apa102-vs-apa107-vs-hd107-vs-hd107s-vs-hd108/  # snapshot 2025-09-26
- relevance: vendor comparison of clocked-chip family; PWM rates, protocol compat

### [S102] HD108 manufacturer page — HD107s/APA102/APA107/SK9822 relationship
- type: product
- url: https://www.hd108-led.com/about-hd107s-apa102-apa107-and-sk9822/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704005736/https://www.hd108-led.com/about-hd107s-apa102-apa107-and-sk9822/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260605123325/https://tomverbeure.github.io/2019/10/13/WS2812B_Reset_Old_and_New.html  # snapshot 2026-06-05
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
- archive: https://web.archive.org/web/20250801212513/https://lcsc.com/product-detail/RGB-LEDs-Built-in-IC_Worldsemi-WS2812B-2020_C965555.html  # snapshot 2025-08-01
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
- archive: https://web.archive.org/web/20251011214024/https://www.normandled.com/upload/201808/WS2815%20LED%20Datasheet.pdf  # snapshot 2025-10-11
- relevance: WS2815 12 V, BIN backup data input behavior, constant-current spec (~15 mA white)

### [S112] SDIP Light — What is WS2815 and how to use it
- type: article
- url: https://www.sdiplight.com/what-is-ws2815-and-how-to-use-ws2815-led/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250613201220/https://www.sdiplight.com/what-is-ws2815-and-how-to-use-ws2815-led/  # snapshot 2025-06-13
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
- archive: https://web.archive.org/web/20260606233015/https://cdn-shop.adafruit.com/product-files/1138/SK6812+LED+datasheet+.pdf  # snapshot 2026-06-06
- relevance: SK6812 timing, 1.2 kHz PWM, RGBW data format

### [S115] SuperLightingLED blog — SK6812 vs WS2812B
- type: article
- url: https://www.superlightingled.com/blog/sk6812-vs-ws2812b/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260310114317/https://www.superlightingled.com/blog/sk6812-vs-ws2812b/  # snapshot 2026-03-10
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
- archive: https://web.archive.org/web/20260704005823/https://www.btf-lighting.com/products/ws2814-rgbw-addressable-led-strip  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260704005905/https://forum.electromage.com/t/trying-out-ws2814-update-officially-supported/2644  # captured 2026-07-03
- relevance: WS2814 color-order gotcha vs SK6812 GRBW; Pixelblaze added explicit support

### [S122] FastLED issue #1855 — support WS2816 LEDs
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1855
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250311203105/https://github.com/FastLED/FastLED/issues/1855  # snapshot 2025-03-11
- relevance: WS2816 48-bit GRB format, hardware gamma, ~10 kHz refresh; FastLED support discussion

### [S123] WS2816B-2020 datasheet (TME mirror)
- type: datasheet
- url: https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf
- author: WorldSemi
- accessed: 2026-07-03
- archive: pending (archive.org save returned 520 on 2026-07-03, twice; origin 403s non-browser clients — likely anti-bot, not dead; no prior wayback snapshot exists)
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
- archive: https://web.archive.org/web/20260415200550/https://www.shiji-leds.com/blog/future-trends-in-addressable-led-strip-technology-and-applications/  # snapshot 2026-04-15
- relevance: 2026 market drift toward 24 V/48 V pixel systems and higher-refresh chips

### [S127] FastLED wiki — Temporal Dithering
- type: docs
- url: https://github.com/FastLED/FastLED/wiki/FastLED-Temporal-Dithering
- author: FastLED project (Mark Kriegsman)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704005414/https://github.com/FastLED/FastLED/wiki/FastLED-Temporal-Dithering  # snapshot 2026-07-04
- relevance: dithering quality proportional to refresh rate; the mechanism behind the strip-length dithering ceiling
- note: same underlying source as [S050] — do not co-cite the pair as independent corroboration

### [S128] cpldcpu — SK9822: a clone of the APA102?
- type: article
- url: https://cpldcpu.com/2016/12/13/sk9822-a-clone-of-the-apa102/
- author: Tim (cpldcpu)
- published: 2016-12-13
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260101013716/https://cpldcpu.com/2016/12/13/sk9822-a-clone-of-the-apa102/  # snapshot 2026-01-01
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
- archive: https://web.archive.org/web/20260704010046/https://www.hd108-led.com/product/48pixels-hd108-led-strip/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260618044601/https://learn.adafruit.com/neopixel-levelshifter  # snapshot 2026-06-18
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
- archive: https://web.archive.org/web/20260526053456/https://quinled.info/the-ultimate-led-strip-power-injection-guide/  # snapshot 2026-05-26
- relevance: voltage-drop budgets, wire gauge tables, injection-point spacing practice
- note: same underlying source as [S369] — do not co-cite the pair as independent corroboration

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
- archive: https://web.archive.org/web/20260327012755/https://www.3waylabs.com/ddp/  # snapshot 2026-03-27
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
- archive: https://web.archive.org/web/20260704010214/https://mm.kno.wled.ge/advanced/ddp/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260704005950/https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260312072216/http://openpixelcontrol.org/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260621121207/https://kno.wled.ge/interfaces/udp-realtime/  # snapshot 2026-06-21
- relevance: byte layouts, per-packet LED limits, timeout semantics of WLED-native realtime UDP
- note: same underlying source as [S253] — do not co-cite the pair as independent corroboration

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
- archive: https://web.archive.org/web/20260621120848/https://kno.wled.ge/basics/faq/  # snapshot 2026-06-21
- relevance: 750-LED per-controller guidance, 720 kbit/s @1000 LED/30fps, DDP-over-E1.31 recommendation, QuinLED/Olimex Ethernet advice

### [S166] Electric UI — "Latency comparison of common wireless links for microcontrollers"
- type: article
- url: https://electricui.com/blog/latency-comparison
- author: Electric UI
- published: 2024-02
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260520234140/https://electricui.com/blog/latency-comparison  # snapshot 2026-05-20
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
- archive: https://web.archive.org/web/20250612180210/https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3/updates/manufacturing-ui-controls-pov  # snapshot 2025-06-12
- relevance: introduces convention-based UI controls (sliderSpeed, hsvPickerColor) generated from exported function names

### [S204] Pixelblaze Sensor Expansion Board (ElectroMage shop / bhencke.com)
- type: product
- url: https://www.bhencke.com/pixelblaze-sensor-expansion
- author: Ben Hencke
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260420032034/https://electromage.com/docs/sensor-expansion-board/  # captured 2026-07-03
- relevance: sensor feature injection as exported pattern variables (frequencyData[32], energyAverage, accelerometer[3], light, analogInputs[5])

### [S205] WLED docs — Custom Features (adding effects via usermods)
- type: docs
- url: https://kno.wled.ge/advanced/custom-features/
- author: WLED project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260629193319/https://kno.wled.ge/advanced/custom-features/  # snapshot 2026-06-29
- relevance: effect function signature (free void fn + SEGMENT/SEGENV/SEGLEN macros), strip.addEffect registration, PROGMEM metadata string, compile-in-only effects

### [S206] WLED issue #3478 — effect metadata consistency (metadata string format)
- type: forum
- url: https://github.com/Aircoookie/WLED/issues/3478
- author: WLED maintainers/contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010048/https://github.com/wled/WLED/issues/3478  # captured 2026-07-03
- relevance: documents the `name@sliders;colors;palette;flags;defaults` metadata DSL and fixed slider slots (sx/ix/custom)

### [S207] WLED MoonModules — ARTI-FX documentation
- type: docs
- url: https://mm.kno.wled.ge/moonmodules/arti-fx/
- author: MoonModules (ewowi et al.)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260313074616/https://mm.kno.wled.ge/moonmodules/arti-fx/  # snapshot 2026-03-13
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
- archive: https://web.archive.org/web/20251128070835/https://jackw01.github.io/led-control/  # snapshot 2025-11-28
- relevance: Python-as-fragment-shader signature (t, dt, x, y, z, prev_state), RestrictedPython + C-extension perf split, 150 fps @ 150 RGBW on Pi Zero claim; repo dormant since 2023-11-10

### [S211] todbot — "Speed up CircuitPython LED animations 10x!" (+ code repo)
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt (todbot)
- published: 2022-10-21
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260519221054/https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/  # snapshot 2026-05-19
- relevance: measured vectorization gain: fire effect, 256 LEDs, RP2040 — ~40 ms/frame Python loop vs ~4 ms/frame ulab; working-copy idiom (code: github.com/todbot/circuitpython_led_effects)
- note: same underlying source as [S400] — do not co-cite the pair as independent corroboration

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
- archive: https://web.archive.org/web/20251208001252/https://derivative.ca/workshop/dmx-artnet-and-led-mapping-touchdesigner/71671  # snapshot 2025-12-08
- relevance: canonical GPU route — TOP sampled at SOP fixture points, DMX CHOP emits Art-Net/sACN; TouchLED library wraps mapping+visualizer

### [S214] ISF — Interactive Shader Format specification
- type: spec
- url: https://isf.vidvox.net/ (spec repo: https://github.com/mrRay/ISF_Spec/)
- author: VIDVOX (mrRay)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010407/https://isf.vidvox.net/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20251111015300/https://chromatik.co/develop/coding/  # snapshot 2025-11-11
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
- archive: https://web.archive.org/web/20260704010412/https://forum.electromage.com/t/output-expander-that-implements-fadecandy-dithering/840  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20260621121207/https://kno.wled.ge/interfaces/udp-realtime/  # snapshot 2026-06-21
- relevance: WLED's loss handling for realtime pixel streams — timeout byte, hold-then-revert semantics, per-protocol LED-count limits, no smoothing/interpolation
- note: same underlying source as [S162] — do not co-cite the pair as independent corroboration

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
- archive: https://web.archive.org/web/20250603142246/https://github.com/Cryptkeeper/fseq-file-format  # snapshot 2025-06-03
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
- archive: https://web.archive.org/web/20260621120941/https://kno.wled.ge/advanced/mapping/  # snapshot 2026-06-21
- relevance: canonical spec of WLED ledmap.json index-permutation format, -1 gaps, width/height 2D keys, per-preset map selection

### [S304] Pixelblaze mapper README (simap/pixelblaze)
- type: docs
- url: https://github.com/simap/pixelblaze/blob/master/README.mapper.md
- author: Ben Hencke
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260420032034/https://github.com/simap/pixelblaze/blob/master/README.mapper.md  # snapshot 2026-04-20
- relevance: spec of Pixelblaze pixel-map JSON, map generator functions, 0..1 world-unit normalization, Fill/Contain scaling, render2D/render3D
- note: same underlying document as [S680]'s README.mapper.md (seed URL vs pinned repo copy) — do not co-cite the pair as independent corroboration

### [S305] LedFx docs — "How to: Create and Edit Virtuals"
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/virtuals.html
- author: LedFx contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260521223731/https://docs.ledfx.app/en/latest/howto/virtuals.html  # snapshot 2026-05-21
- relevance: defines virtuals/segments (device,start,end,reverse), span vs copy modes, rows/grouping 2D reshaping, complex-segments numpy fast path

### [S306] xLights manual — Custom Model
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/custom-model
- author: xLights contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260317062924/https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/custom-model  # snapshot 2026-03-17
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
- archive: https://web.archive.org/web/20260309180104/https://falcon-player.gitbooks.io/falcon-player-manual/content/chapter_five_inputoutput_setup/pixel_overlay_models.html  # snapshot 2026-03-09
- relevance: FPP channel-arithmetic model definition (start channel, strands/strings, orientation) and overlay/transparency states

### [S309] Chromatik guide — Custom Fixtures (.lxf format)
- type: docs
- url: https://chromatik.co/guide/custom-fixtures/
- author: Mark Slee / Heron Arts
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010455/https://chromatik.co/guide/custom-fixtures/  # captured 2026-07-03
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
- archive: https://web.archive.org/web/20250828092218/https://forum.electromage.com/t/2d-pixel-coordinate-mapping-tool-for-images/714  # snapshot 2025-08-28
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

### [S351] WLED knowledge base — Compatible controllers
- type: docs
- url: https://kno.wled.ge/basics/compatible-controllers/
- author: WLED project (Aircoookie et al.)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260621121208/https://kno.wled.ge/basics/compatible-controllers/  # snapshot 2026-06-21
- relevance: official WLED hardware guidance — ESP8266 deprecation, ESP32 variant support tiers, Ethernet boards

### [S352] MoonModules/MoonLight — Releases (v0.5.8–v1.0.0)
- type: docs
- url: https://github.com/MoonModules/MoonLight/releases
- author: MoonModules (ewowi et al.)
- license: GPL-3.0
- published: 2025-08-15 through 2026-05-06 (v1.0.0)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251003145210/https://github.com/MoonModules/MoonLight/releases  # snapshot 2025-10-03
- relevance: MoonLight hardware targets (S3/P4 best, PSRAM 130K LEDs, PARLIO P4 driver, supported boards)

### [S353] Espressif Developer Portal — Wireless Connectivity Solutions for ESP32-P4
- type: docs
- url: https://developer.espressif.com/blog/wireless-connectivity-solutions-for-esp32-p4/
- author: Espressif Systems
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260415161024/https://developer.espressif.com/blog/wireless-connectivity-solutions-for-esp32-p4/  # snapshot 2026-04-15
- relevance: authoritative statement that P4 has no radio; ESP-Hosted/ESP-AT companion-chip (C6) architecture

### [S354] Hackaday — Poking at the ESP32-P4 and C6 dies in an ESP32-P4-M3 module
- type: article
- url: https://hackaday.com/2026/02/19/poking-at-the-esp32-p4-and-c6-dies-in-an-esp32-p4-m3-module/
- author: Hackaday
- published: 2026-02-19
- accessed: 2026-07-03
- relevance: evidence that newer P4 modules co-package a C6 die for WiFi

### [S355] esphome issue #10956 — P4 & C6 WiFi issues via esp32_hosted
- type: forum
- url: https://github.com/esphome/esphome/issues/10956
- author: esphome users
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010237/https://github.com/esphome/esphome/issues/10956  # captured 2026-07-03
- relevance: hosted-WiFi instability on P4+C6 boards as of early 2026 — P4 WiFi path not yet boring

### [S356] WLED issue #5576 — ESP8266 too big for OTA update (2-step _min workaround)
- type: forum
- url: https://github.com/wled/WLED/issues/5576
- author: WLED users/maintainers
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260512192114/https://github.com/wled/WLED/issues/5576  # snapshot 2026-05-12
- relevance: concrete evidence ESP8266 is being squeezed out of full WLED builds (flash exhaustion); see also #5363

### [S357] QuinLED Dig-Next-2 specifications
- type: product
- url: https://quinled.info/dig-next-2-specifications/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260418213721/https://quinled.info/dig-next-2-specifications/  # snapshot 2026-04-18
- relevance: current-gen QuinLED small board — ESP32 8MB/2MB PSRAM, 2 outputs, 5-48V, fusing, firmware compatibility list

### [S358] QuinLED Dig-Octa — modular WLED LED system
- type: product
- url: https://quinled.info/quinled-dig-octa/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260526015933/https://quinled.info/quinled-dig-octa/  # snapshot 2026-05-26
- relevance: room/stage-scale QuinLED — 8 channels + Ethernet brainboard on 30-100A fused powerboards, E1.31/Art-Net/DDP

### [S359] Falcon F16v5 pixel controller (store page)
- type: product
- url: https://pixelcontroller.com/store/featured/88-f16v5.html
- author: Falcon / pixelcontroller.com
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260620030843/https://pixelcontroller.com/store/featured/88-f16v5.html  # snapshot 2026-06-20
- relevance: F16v5 specs — $280, 16+4 ports (to 32), 1024 px/output, 192 universes E1.31/Art-Net/DDP, e-fuses, 2-port Ethernet switch

### [S360] Kulp K16A-B controller owner's manual
- type: docs
- url: https://kulplights.com/manuals/K16A-B-Manual.pdf
- author: Kulp Lights LLC
- accessed: 2026-07-03
- relevance: authoritative per-port limit statement — 800 px/port @40fps, 1500 @20fps; BeagleBone cape running FPP natively

### [S361] Kulp K40D-PB product page
- type: product
- url: https://kulplights.com/product/k40d-pb/
- author: Kulp Lights LLC
- accessed: 2026-07-03
- relevance: PocketBeagle cape, 10 RJ45 differential ports / 40 strings — long-range FPP-native architecture

### [S362] Advatek PixLite Mk3 range (A4-S product page + comparison)
- type: product
- url: https://www.advateklighting.com/products/a4-s-mk3
- author: Advatek Lighting
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260628152046/https://www.advateklighting.com/products/a4-s-mk3  # snapshot 2026-06-28
- relevance: professional tier — A4-S Mk3 4080 px over 4 outputs; E4-S Ethernet and T8-S long-range variants

### [S363] HinksPix Pro V3 CPU (HolidayCoro)
- type: product
- url: https://www.holidaycoro.com/HinksPix-Pro-V3-CPU-20-Long-Range-Jacks-80-Ports-p/952-6.htm
- author: HolidayCoro
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250423205030/https://www.holidaycoro.com/HinksPix-Pro-V3-CPU-20-Long-Range-Jacks-80-Ports-p/952-6.htm  # snapshot 2025-04-23
- relevance: high-density holiday-show controller — V3 CPU + expansions to 16,320 px, 80-port long-range configs

### [S364] forkineye/ESPixelStick — repository and releases
- type: code
- url: https://github.com/forkineye/ESPixelStick
- author: Shelby Merrick (forkineye)
- license: MIT
- accessed: 2026-07-03
- relevance: ESPixelStick V4 firmware stuck at v4.0-beta4 (2023-11) with development in fork/CI artifacts — waning evidence

### [S365] simap/pixelblaze_output_expander — firmware + serial protocol
- type: code
- url: https://github.com/simap/pixelblaze_output_expander
- author: Ben Hencke (simap)
- license: MIT
- accessed: 2026-07-03
- relevance: open 2Mbps framed serial protocol, 8 channels, 240 RGB/180 RGBW px buffered per channel, 8 boards per line; host-agnostic (Pi/Arduino)

### [S366] ElectroMage Pro Output Expander (shop page)
- type: product
- url: https://shop.electromage.com/products/pixelblaze-pro-output-expander-pro-8x-ws2812-apa102-led-driver
- author: ElectroMage (Ben Hencke)
- accessed: 2026-07-03
- relevance: Pro expander — 8-64 channels per serial line, 600/800 px per channel buffering

### [S367] jgarff/rpi_ws281x — Raspberry Pi 5 support (wiki + repo)
- type: code
- url: https://github.com/jgarff/rpi_ws281x/wiki/Raspberry-Pi-5-Support
- author: Jeremy Garff et al.
- license: BSD-2-Clause
- accessed: 2026-07-03
- relevance: Pi 5 RP1 chip broke legacy WS281x GPIO output; needs rp1_ws281x_pwm kernel module — evidence native Pi pixel output is a dead end

### [S368] FalconChristmas/fpp — releases (FPP 9.x Pi 5 support)
- type: code
- url: https://github.com/FalconChristmas/fpp/releases
- author: FalconChristmas
- license: GPL-2.0/GPL-3.0 mixed (FPP)
- accessed: 2026-07-03
- relevance: FPP 9.x (latest 9.5) images support Pi Zero through Pi 5 and BeagleBone — render-host OS support status

### [S369] QuinLED — The Ultimate LED Strip Power Injection Guide (+ wire thickness guide)
- type: docs
- url: https://quinled.info/the-ultimate-led-strip-power-injection-guide/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260526053456/https://quinled.info/the-ultimate-led-strip-power-injection-guide/  # snapshot 2026-05-26
- relevance: injection sizing (≤10% Vdrop), 5V-vs-12V injection cadence, 18AWG strip-feed guidance, edge-vs-mid injection fusing
- note: same underlying source as [S135] — do not co-cite the pair as independent corroboration

### [S370] AusChristmasLighting — pigtail connector plug type comparisons (Ray Wu vs xConnect)
- type: forum
- url: https://auschristmaslighting.com/threads/pigtail-connector-plug-type-comparisons.16968/
- author: AusChristmasLighting community
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251208125019/https://auschristmaslighting.com/threads/pigtail-connector-plug-type-comparisons.16968/  # snapshot 2025-12-08
- relevance: Ray Wu vs xConnect near-identical mechanically; xConnect single wiring standard + universal store stocking — the connector to standardize on

## Block S400–S449 — RA-09 Hardware: wearable tier

### [S400] todbot — "Speed up CircuitPython LED animations 10x with ulab"
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt
- published: 2022-10-21
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260519221054/https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/  # snapshot 2026-05-19
- relevance: establishes realistic CircuitPython frame-rate ceilings and the ulab escape hatch — central to the wearable-tier Python question
- note: same underlying source as [S211] — do not co-cite the pair as independent corroboration

### [S401] Adafruit CircuitPython LED Animation library
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_LED_Animation
- license: MIT
- accessed: 2026-07-03
- relevance: the standard wearable-tier animation library; API prior art

### [S402] Core Electronics — "Huge MicroPython Speed-Up With WS2812 LEDs" (The Factory)
- type: video
- url: https://core-electronics.com.au/videos/the-factory-huge-micropython-speed-up-with-ws2812-leds
- author: Core Electronics
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20220331190314/https://core-electronics.com.au/videos/the-factory-huge-micropython-speed-up-with-ws2812-leds  # snapshot 2022-03-31
- relevance: measured ~2x frame-rate gain (10 → ~22 fps) from @micropython.viper on a GlowBit WS2812 matrix; documents viper restrictions

### [S403] CircuitPython board pages — RP2350 boards (Feather RP2350, Plasma 2350 etc.)
- type: docs
- url: https://circuitpython.org/board/adafruit_feather_rp2350/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260414211530/https://circuitpython.org/board/adafruit_feather_rp2350/  # captured 2026-07-03
- relevance: confirms ulab is bundled for RP2350-class boards; RP2350 runs CircuitPython roughly 2x faster than RP2040

### [S404] Pixelblaze — language reference and product docs
- type: docs
- url: https://electromage.com/docs/language-reference/
- author: Ben Hencke (ElectroMage)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260209163257/https://electromage.com/docs/language-reference/  # snapshot 2026-02-09
- relevance: JS-like pattern language compiled off-device (in browser) to instructions executed on ESP32 — closest precedent for host-authored/device-executed patterns

### [S405] Pixelblaze V3 — Crowd Supply campaign page
- type: product
- url: https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3
- author: Ben Hencke (ElectroMage)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260605034712/https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3  # snapshot 2026-06-05
- relevance: performance claim ~48k pixels/sec on ESP32; bytecode is platform-dependent between v2/v3

### [S406] wled/WLED PR #4570 — "added support for fseq files"
- type: code
- url: https://github.com/wled/WLED/pull/4570
- author: Andrejchrcek
- license: EUPL-1.2 (WLED)
- accessed: 2026-07-03
- relevance: FSEQ-from-SD standalone playback merged into WLED (2025) — the bake-and-play portability path

### [S407] Adafruit CircuitPython BLE_File_Transfer library
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_BLE_File_Transfer
- author: Adafruit
- license: MIT
- accessed: 2026-07-03
- relevance: BLE service (UUID 0xfebb) for pushing files (i.e. Python patterns) to an nRF52840 wearable from a phone; self-described "simple (not fast)"

### [S408] todbot/circuitpython_led_effects
- type: code
- url: https://github.com/todbot/circuitpython_led_effects
- author: Tod Kurt
- license: TBD
- accessed: 2026-07-03
- relevance: benchmark code behind the ulab 10x speedup claim; idiomatic vectorized LED effects in CircuitPython

### [S409] Adafruit Learn — "Wirelessly Code your Bluetooth Device with CircuitPython"
- type: docs
- url: https://learn.adafruit.com/wirelessly-code-your-bluetooth-device-with-circuitpython/overview
- author: Adafruit
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010615/https://learn.adafruit.com/ble-claw  # captured 2026-07-03
- relevance: browser-based editing of CircuitPython files over BLE on nRF52840 — proves phone/laptop-to-wearable pattern push workflow

### [S410] Raspberry Pi — RP2350 datasheet
- type: datasheet
- url: https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf
- author: Raspberry Pi Ltd
- published: 2024-08-08
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251107121354/https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf  # snapshot 2025-11-07
- relevance: RP2350 specs — dual Cortex-M33/RISC-V 150 MHz, 3 PIO blocks / 12 state machines, 32-instruction PIO programs

### [S411] ESP32 Forum — "ESP32 Power consumption considerations" (thread t=2662)
- type: forum
- url: https://esp32.com/viewtopic.php?t=2662
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010652/https://esp32.com/ext/espressif/stupidbots/challenge.php?n=MTc4MzEyNzIxMC4zNDg4NzM1OTA3&c=833ba4547353e3fced0db144c46d504a0c2baba9216352357a63ccafed972991&h=2ec0c5f60947c67c2a41bdcdcc6acf3dcb3b2cd09435bc3a564e138e516acbf4&from=L3ZpZXd0b3BpYy5waHA/dD0yNjYy  # captured 2026-07-03
- relevance: measured ~130 mA average with 0.6 A spikes during active WiFi; notes esp_wifi_set_ps power save works only in station mode (not SoftAP)

### [S412] Seeed forum — msfujino, "BLE Advertising Current Comparison, ESP32C3,C6,S3, MG24, nRF52840"
- type: forum
- url: https://forum.seeedstudio.com/t/ble-advertising-current-comparison-esp32c3-c6-s3-mg24-nrf52840/287847
- author: msfujino
- published: 2025-01-17
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251026033759/https://forum.seeedstudio.com/t/ble-advertising-current-comparison-esp32c3-c6-s3-mg24-nrf52840/287847  # snapshot 2025-10-26
- relevance: measured cross-chip BLE advertising current; verdict "nRF52840 is by far the best for low current consumption BLE applications"

### [S413] FastLED Wiki — Power notes (setMaxPowerInVoltsAndMilliamps)
- type: docs
- url: https://github.com/FastLED/FastLED/wiki/Power-notes
- author: FastLED project
- license: MIT (FastLED)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260505174835/https://github.com/FastLED/FastLED/wiki/Power-notes  # snapshot 2026-05-05
- relevance: the reference brightness-limiting pattern — estimate frame power, scale global brightness; applied automatically in show()/delay(); assumes 5 V pixels

### [S414] Adafruit Sparkle Motion — product page (#6100)
- type: product
- url: https://www.adafruit.com/product/6100
- author: Adafruit
- published: 2025-01-24
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260703032624/https://www.adafruit.com/product/6100  # snapshot 2026-07-03
- relevance: 2025 flagship WLED/xLights board — ESP32, 4 outputs, USB-C PD 5/12/20V 100W, IR receiver, I2S mic, 33x45mm

### [S415] Adafruit Learn — Sparkle Motion Mini guide
- type: docs
- url: https://learn.adafruit.com/adafruit-sparkle-motion-mini/overview
- author: Adafruit
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260219011254/https://learn.adafruit.com/adafruit-sparkle-motion-mini/overview  # snapshot 2026-02-19
- relevance: 31.6x19.8mm ESP32 WLED board aimed at wearables/portable rigs; 2 outputs

### [S416] Adafruit LED Glasses Driver — nRF52840 Sensor Board (#5217) + EyeLights guide
- type: product
- url: https://www.adafruit.com/product/5217
- author: Adafruit
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260703033131/https://www.adafruit.com/product/5217  # snapshot 2026-07-03
- relevance: canonical nRF52840 wearable reference design — thin board, LiPo, LIS3DH, PDM mic, drives 116-LED glasses via IS31FL3741 I2C driver (hardware PWM offload)

### [S417] Adafruit NeoPixel Überguide — Powering NeoPixels
- type: docs
- url: https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels
- author: Adafruit
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260425060638/https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels  # snapshot 2026-04-25
- relevance: 60 mA/px worst-case planning constant ("rule of thumb, not hard science"), 3.7 V LiPo direct drive, brownout caps, wearable strain-relief guidance

### [S418] WLED knowledge base — Settings (Automatic Brightness Limiter)
- type: docs
- url: https://kno.wled.ge/features/settings/
- author: WLED project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260629193319/https://kno.wled.ge/features/settings/  # snapshot 2026-06-29
- relevance: WLED ABL — default 850 mA cap, tunable to supply/pack rating; the shipped-firmware version of estimate-and-scale power limiting

### [S419] Adafruit blog — CircuitPython 10.0.0 (2025-10-01) and 10.2.1 (2026-05-12) release posts
- type: article
- url: https://blog.adafruit.com/2025/10/01/circuitpython-10-0-0-released/
- author: Adafruit
- published: 2025-10-01
- accessed: 2026-07-03
- relevance: evidences healthy CircuitPython release cadence through mid-2026 (10.2.1 on 2026-05-12) — maintenance-status anchor for the wearable Python stack

### [S420] ElectroMage forum + shop — Pixelblaze availability/roadmap threads (2024-2025)
- type: forum
- url: https://forum.electromage.com/t/pixelblaze-for-burning-man-2025-sync-wifi-new-product-roadmap/3997
- author: ElectroMage community / Ben Hencke
- accessed: 2026-07-03
- relevance: maintenance-status anchor for Pixelblaze — V3 shipping, V2+ retired, Tindie store paused to 2027, no visible V4 roadmap

### [S421] Adafruit Learn — LIGHTSHIP: LED Animation over WiFi, "SD Card Playback"
- type: docs
- url: https://learn.adafruit.com/lightship-led-animation-over-wifi/sd-card-playback
- author: Adafruit
- published: 2016-02-04
- accessed: 2026-07-03
- relevance: early precedent for baked-frame SD playback at wearable scale (the bake-and-play portability strategy)

## Block S450–S499 — RA-10 Audio reactivity

### [S450] WLED-MM — Audio Reactive documentation
- type: docs
- url: https://mm.kno.wled.ge/advanced/audio-reactive/
- accessed: 2026-07-03
- relevance: most advanced embedded audio pipeline (GEQ, beat detection, sound sync)

### [S451] aubio-ledfx (LedFx's maintained aubio fork)
- type: code
- url: https://github.com/LedFx/aubio-ledfx
- pinned: LedFx/aubio-ledfx@c9b3bfeebc8acb87940d5e380a693c2f58f713fd
- author: LedFx team (fork of Paul Brossier's aubio)
- license: GPL-3.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: maintained wheels of aubio for modern Python; the DSP core LedFx actually ships

### [S452] aubio (upstream repository)
- type: code
- url: https://github.com/aubio/aubio
- author: Paul Brossier
- license: GPL-3.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: C library for onset/tempo/pitch used (via fork) by LedFx; last release 0.4.9 (2019-02-27), sporadic commits since (last 2026-04-10)

### [S453] WLED-AudioReactive-Usermod (MoonModules)
- type: code
- url: https://github.com/MoonModules/WLED-AudioReactive-Usermod
- pinned: MoonModules/WLED-AudioReactive-Usermod@8d988e985901e00a0a92e119aaa8e3249f817754
- author: MoonModules (softhack007 et al.)
- license: EUPL-1.2 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: the actual WLED-MM audioreactive DSP source (audio_reactive.h, audio_source.h): 22.05 kHz / 512-sample FFT, 16-ch GEQ, AGC, pink-noise mic profiles, UDP sound-sync V2 packet

### [S454] madmom (CPJKU)
- type: code
- url: https://github.com/CPJKU/madmom
- author: Sebastian Böck et al., JKU Linz CP group
- license: BSD-2-Clause with non-commercial clause on models (custom; GitHub shows NOASSERTION) (checked 2026-07-03)
- accessed: 2026-07-03
- relevance: state-of-the-art RNN/DBN beat & downbeat tracking; online mode exists but ~100-200 ms perceived lag reported; last commit 2024-08-25, PyPI 0.16.1 (2018) — effectively unmaintained

### [S455] BTrack (Adam Stark)
- type: code
- url: https://github.com/adamstark/BTrack
- author: Adam Stark
- license: GPL-3.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: classic C++ real-time causal beat tracker with Python module; stable/legacy academic code (repo pushed 2026-02-26)

### [S456] librosa issue #220 — "Real time analysis"
- type: forum
- url: https://github.com/librosa/librosa/issues/220
- author: librosa maintainers
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010807/https://github.com/librosa/librosa/issues/220
- relevance: maintainers confirm librosa targets batch/complete-signal analysis, not live streams; disqualifies librosa for pewpew's live path

### [S457] BeatNet (mjhydri)
- type: code
- url: https://github.com/mjhydri/BeatNet
- author: Mojtaba Heydari et al. (ISMIR 2021)
- license: CC-BY-4.0 (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: CRNN + particle-filter joint beat/downbeat/tempo/meter tracker with true streaming mode, commonly cited sub-50 ms; PyPI 1.1.3 (2023-11-28), repo pushed 2026-04-13; requires PyTorch

### [S458] python-sounddevice documentation
- type: docs
- url: https://python-sounddevice.readthedocs.io/
- author: Matthias Geier
- license: MIT (library)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260701120149/https://python-sounddevice.readthedocs.io/en/0.5.3/
- relevance: PortAudio binding used by LedFx; latency/blocksize semantics for the capture stage of the budget

### [S459] ITU-R BT.1359-1 — Relative timing of sound and vision
- type: spec
- url: https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- author: ITU-R
- published: 1998-11
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250903014127/https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- relevance: the canonical A/V sync thresholds: detectability +45/-125 ms, acceptability +90/-185 ms; grounds pewpew's <=50 ms audio-to-light target

### [S460] scottlawsonbc/audio-reactive-led-strip
- type: code
- url: https://github.com/scottlawsonbc/audio-reactive-led-strip
- author: Scott Lawson
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: ancestor of LedFx's melbank/energy-beat approach ("systematic_leds" lineage); documents 60 FPS as responsiveness/latency knob; archived-era but widely copied

### [S461] pyloudnorm
- type: code
- url: https://github.com/csteinmetz1/pyloudnorm
- author: Christian Steinmetz
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: Python EBU R128 / ITU-R BS.1770 loudness (LUFS); suits slow gain-riding, not per-hop AGC; pushed 2026-01-04

### [S462] pixelblaze_sensor_board (firmware + hardware)
- type: code
- url: https://github.com/simap/pixelblaze_sensor_board
- pinned: simap/pixelblaze_sensor_board@15b3d271e0d6535965a68b15f057bac58a3154d7
- author: Ben Hencke (ElectroMage)
- license: MIT (software), CC-BY-SA-4.0 (hardware) (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: STM32F0 coprocessor doing fixed-point FFT; serial "SB1.0" frame: 32x uint16 spectrum (37 Hz-10 kHz), energy, max-freq, 3-axis 16G accel, light, 5 analog — the wearable sensor-frame precedent

### [S463] PixelblazeSensorBoardLibrary (Arduino client)
- type: code
- url: https://github.com/simap/PixelblazeSensorBoardLibrary
- pinned: simap/PixelblazeSensorBoardLibrary@1185e4a71d7b0ce7091d381d99f237d49d78dbf5
- author: Ben Hencke (ElectroMage)
- license: MIT (verified 2026-07-03)
- accessed: 2026-07-03
- relevance: documents the SB1.0 frame parse (~8-9 ms/frame) and API for consuming sensor-board features on third-party MCUs

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

### [S502] jandelgado/fastled-wasm — "FastLED for the Web" (unrelated to zackees')
- type: code
- url: https://github.com/jandelgado/fastled-wasm
- author: Jan Delgado
- license: TBD
- accessed: 2026-07-03
- relevance: earlier independent FastLED->WASM port with live browser demo (jandelgado.github.io/fastled-wasm); disambiguation from [S500]

### [S503] FastLED WasmScreenCoords example (fastled.io docs)
- type: docs
- url: https://fastled.io/docs/_wasm_screen_coords_8ino.html
- author: FastLED project
- accessed: 2026-07-03
- relevance: shows the screenmap API — per-LED coordinates passed to the browser renderer for physical-layout preview

### [S504] Pixelblaze V3 Standard product listing (Tindie, ElectroMage)
- type: product
- url: https://www.tindie.com/products/electromage/pixelblaze-v3-standard-wifi-led-controller/
- author: Ben Hencke / ElectroMage
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260114105355/https://www.tindie.com/products/electromage/pixelblaze-v3-standard-wifi-led-controller/
- relevance: maintainer-written description of live editor: recompile-and-send on every change, inline syntax/runtime error highlighting, variable watcher, UI-controls-as-functions

### [S505] pixelblaze-client (Python websocket library)
- type: code
- url: https://github.com/zranger1/pixelblaze-client
- author: zranger1
- license: MIT
- published: 2025-12-03 (v1.1.7)
- accessed: 2026-07-03
- relevance: Python client for the Pixelblaze websocket API; proof the live-control channel is stable third-party tooling surface

### [S506] xLights Manual (manual.xlights.org)
- type: docs
- url: https://manual.xlights.org/
- author: xLights project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704012133/https://manual.xlights.org/xlights
- relevance: House Preview window, multiple preview layouts over background photos, per-model render buffers, Render All workflow, render-progress diagnostics

### [S507] AusChristmasLighting thread — "Speeding up rendering" (xLights)
- type: forum
- url: https://auschristmaslighting.com/threads/speeding-up-rendering.13383/
- accessed: 2026-07-03
- relevance: community evidence that xLights render iteration latency is a recurring pain point

### [S508] LedFx docs — "How to: Create a Dummy Matrix"
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/dummy_matrix.html
- author: LedFx project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251003085253/https://docs.ledfx.app/en/latest/howto/dummy_matrix.html
- relevance: dummy device renders only to browser frontend for hardware-free testing; 4096-px frontend pixel cap and throttle slider

### [S509] LedFx docs — "How to: Create and Edit Virtuals"
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/virtuals.html
- author: LedFx project
- accessed: 2026-07-03
- relevance: virtuals = remap arbitrary device pixel segments into one logical target; mapping layer doubling as preview target

### [S510] WLED docs — "Compiling WLED" (kno.wled.ge)
- type: docs
- url: https://kno.wled.ge/advanced/compiling-wled/
- author: WLED project
- accessed: 2026-07-03
- relevance: official build docs are PlatformIO/ESP-only — evidence WLED has no native PC/simulator build target

### [S511] wled-sim (13rac1) — desktop WLED simulator
- type: code
- url: https://github.com/13rac1/wled-sim
- author: 13rac1
- license: TBD
- accessed: 2026-07-03
- relevance: Go/Fyne desktop app emulating a WLED node (JSON API + DDP listener + GUI matrix) for client dev and integration tests; emulates API, not firmware effects

### [S512] Wokwi project — WLED Effects Editor on simulated ESP32
- type: code
- url: https://wokwi.com/projects/288883342157283852
- accessed: 2026-07-03
- relevance: full WLED firmware running in browser ESP32 instruction simulator — existence proof, but not a practical fast iteration loop

### [S513] Web LED/point-cloud previewer survey (ledcube-webgl; LEDCube-ThreeJS; potree)
- type: code
- url: https://github.com/ultrafez/ledcube-webgl
- accessed: 2026-07-03
- relevance: representative one-off WebGL/three.js LED simulators (also github.com/lrascius/LEDCube-ThreeJS, github.com/potree/potree) — pattern is common, no reusable packaged component found

### [S514] neopixel-plus (PyPI)
- type: code
- url: https://pypi.org/project/neopixel-plus/
- author: Marco Schlicht et al.
- license: TBD
- accessed: 2026-07-03
- relevance: NeoPixel library with terminal (ANSI) testing mode — preview LEDs in a terminal with no microcontroller

### [S515] Python NeoPixel GUI emulators (having11; Footleg)
- type: code
- url: https://github.com/having11/NeoPixel-Emulator
- accessed: 2026-07-03
- relevance: Pyglet strip/matrix emulator with Adafruit-GFX port; also github.com/Footleg/neopixel-emulator (API-compatible mock of Adafruit RPi NeoPixel library) — the hardware-API-mock preview pattern

### [S516] LedFx test suite (tests/ directory, inspected via GitHub API)
- type: code
- url: https://github.com/LedFx/LedFx/tree/main/tests
- author: LedFx project
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: direct inspection 2026-07-03: effect tests are HTTP-API smoke tests (set effect, assert JSON), no pixel-output/golden-frame assertions — evidence nobody frame-tests effects

### [S517] FastLED test suite (tests/ directory, inspected via GitHub API)
- type: code
- url: https://github.com/FastLED/FastLED/tree/master/tests
- author: FastLED project
- license: MIT
- accessed: 2026-07-03
- relevance: host-compiled doctest unit suite (math/color primitives, build-bloat regressions); no effect frame-snapshot tests found

### [S518] pytest-mpl — matplotlib image comparison plugin
- type: docs
- url: https://github.com/matplotlib/pytest-mpl
- author: matplotlib project
- license: BSD-3-Clause
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704012215/https://github.com/matplotlib/pytest-mpl
- relevance: the transferable golden-image testing pattern: baseline images + RMS tolerance instead of byte-exact diff

### [S519] watchfiles (samuelcolvin)
- type: code
- url: https://github.com/samuelcolvin/watchfiles
- author: Samuel Colvin
- license: MIT
- accessed: 2026-07-03
- relevance: standard Rust-backed Python file watcher; powers Uvicorn reload; sync/async APIs + run_process — substrate for pewpew's hot-reload loop

### [S520] Python hot-swap reloaders: jurigged & promplate/hmr
- type: code
- url: https://github.com/breuleux/jurigged
- author: Olivier Breuleux (jurigged); promplate (hmr, github.com/promplate/hmr)
- license: MIT (jurigged); hmr TBD
- accessed: 2026-07-03
- relevance: in-place code patching (jurigged: existing instances get new behavior) and reactive module re-run (hmr) — the state-preserving alternatives to process restart

## Block S550–S599 — RA-12 Prior art & control plane

### [S550] WLED docs — JSON API
- type: docs
- url: https://kno.wled.ge/interfaces/json-api/
- author: WLED project (Aircoookie et al.)
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251219022207/https://kno.wled.ge/interfaces/json-api/
- relevance: canonical spec of WLED's single-JSON-state control model: state/seg objects, presets, playlists, fxdata metadata, per-LED `i` writes and buffer limits.

### [S551] WLED docs — WebSocket interface
- type: docs
- url: https://kno.wled.ge/interfaces/websocket/
- author: WLED project
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251219071936/https://kno.wled.ge/interfaces/websocket/
- relevance: /ws semantics — same JSON vocabulary as HTTP, server-push of merged state on change, {"v":true} full state, {"lv":true} exclusive live-preview stream, 4-client limit.

### [S552] zranger1/pixelblaze-client (Python protocol reference)
- type: code
- url: https://github.com/zranger1/pixelblaze-client
- pinned: zranger1/pixelblaze-client@9be84700248fa17f0123c702a2939213ba69800a
- author: zranger1 (JEM) and contributors
- license: MIT
- published: v1.1.7 2025-12-03 (last push 2025-12-20)
- accessed: 2026-07-03
- relevance: de-facto documentation of the Pixelblaze ws://:81 protocol — exact JSON command keys, binary frame type bytes, sequencer modes, save-flag semantics.

### [S553] Home Assistant — WLED integration docs
- type: docs
- url: https://www.home-assistant.io/integrations/wled/
- author: Home Assistant project (integration by Franck Nijhof)
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251224021119/https://www.home-assistant.io/integrations/wled
- relevance: reference mapping of an LED engine to smart-home entities (segments→lights, presets/playlists/palettes→selects, speed/intensity→numbers); local-push via WebSocket with 10 s polling fallback.

### [S554] WLED docs — Presets (and timed presets)
- type: docs
- url: https://kno.wled.ge/features/presets/
- author: WLED project
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260116004106/https://kno.wled.ge/features/presets/
- relevance: preset storage model (/presets.json, 250 slots, preset=any API command), playlist-in-preset structure, 8 timer slots + sunrise/sunset, boot preset, LittleFS write-blocking caveats.

### [S555] Chromatik Guide — OSC
- type: docs
- url: https://chromatik.co/guide/osc/
- author: Heron Arts / Mark Slee
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260218122037/https://chromatik.co/guide/osc/
- relevance: the reference OSC design for LED engines — /lx/ parameter tree, normalized float32 semantics, OSCQuery zeroconf discovery, OSC-driven tempo/beat.

### [S556] Chromatik Guide — MIDI
- type: docs
- url: https://chromatik.co/guide/midi/
- author: Heron Arts / Mark Slee
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704012358/https://chromatik.co/guide/midi/
- relevance: three-tier MIDI model (native control surfaces incl. APC40 mkII, device-agnostic learn-mode mappings, MIDI-into-patterns) plus MIDI Beat Clock sync.

### [S557] hzeller/spixels PR #1 — Schardt's APA102/SK9822 per-pixel 5-bit dimming
- type: code
- url: https://github.com/hzeller/spixels/pull/1
- pinned: hzeller/spixels@n/a (PR of record; merged into spixels)
- author: Christopher Schardt (GitHub: schardt)
- license: TBD (spixels repo license)
- published: 2017 (PR)
- accessed: 2026-07-03
- relevance: primary-source documentation of Schardt's APA102 technique — per-48-bit-pixel 5-bit dimming for extended dynamic range and SK9822 color-shift compensation; ancestor of FastLED APA102HD.

### [S558] Burning Man Journal — "Christopher Schardt: from Engineering to Aesthetics"
- type: article
- url: https://journal.burningman.org/2015/12/burning-man-arts/brc-art/christopher-schardt-from-engineering-to-aesthetics/
- author: Burning Man Journal
- published: 2015-12
- accessed: 2026-07-03
- relevance: documented taste lesson — Schardt's engineer-to-artist transition and art-first framing of LED work.

### [S559] Piper Faust Public Art — Firmament (Christopher Schardt)
- type: article
- url: https://www.piperfaustpublicart.com/firmament
- author: Piper Faust Public Art (representing Schardt)
- published: n/a
- accessed: 2026-07-03
- relevance: Firmament specs — 52-ft canopy, 21,000+ LEDs, patterns paired with classical music; documents the overhead-canopy + curated-music presentation model.

### [S560] Evil Genius Labs — Fibonacci128 technique page
- type: docs
- url: https://www.evilgeniuslabs.org/fibonacci128
- author: Jason Coon
- published: n/a (living page)
- accessed: 2026-07-03
- relevance: documents Fermat's-spiral LED layout, zig-zag physical order, and XY vs polar (radius/angle) pixel maps as creative primitives; maps shipped for Pixelblaze and his MIT FastLED webserver firmware.

### [S561] Hackaday — "Remoticon 2021 // Debra Ansell Connects PCB In Ways You Didn't Expect"
- type: article
- url: https://hackaday.com/2022/01/20/remoticon-2021-debra-ansell-connects-pcb-in-ways-you-didnt-expect/
- author: Hackaday (talk by Debra Ansell / GeekMomProjects)
- published: 2022-01-20
- accessed: 2026-07-03
- relevance: documented LEDs/PCBs-as-structure techniques; companion to her PyCascades 2021 "Sparking Creativity in LED Art with CircuitPython" talk.

### [S562] Adafruit Learn — "Make It Glow: NeoPixel and LED Diffusion Tips & Tricks" (Erin St Blaine)
- type: docs
- url: https://learn.adafruit.com/make-it-glow-neopixel-and-led-diffusion-tips-tricks
- author: Erin St Blaine / Adafruit
- published: n/a
- accessed: 2026-07-03
- relevance: rare written treatment of diffusion materials/spacing; her FastLED guides (LED Campfire etc.) document gradient-palette-driven design.

### [S563] titanicsend/LXStudio-TE — Titanic's End Chromatik app
- type: code
- url: https://github.com/titanicsend/LXStudio-TE
- pinned: titanicsend/LXStudio-TE@863926450a3ae6102d8c5f89c26ffe3b443d944f
- author: Titanic's End collective (lead: Andrew Look)
- license: custom LICENSE.md (GitHub: NOASSERTION)
- published: 2022– (pushed 2026-04-18)
- accessed: 2026-07-03
- relevance: largest open LED-art codebase — GLSL shaders on 128k LEDs, AutoVJ (Rekordbox phrase/beat autopilot), MIDI/OSC/ArtNet middleware, team-maintainability practices.

### [S564] CharlesGadeken.com — Squared / 2SQUARED
- type: article
- url: https://www.charlesgadeken.com/squared
- author: Charles Gadeken
- published: n/a (work 2014)
- accessed: 2026-07-03
- relevance: 2×50-ft trees, 768 LED cubes each; documents audience-facing control surfaces (iPad app + RFID table); cube-installation family from which LX emerged.

### [S565] ZackFreedman/Chromance
- type: code
- url: https://github.com/ZackFreedman/Chromance
- pinned: ZackFreedman/Chromance@1cefefb0290369672de02d04cbe8fba5e3625fea
- author: Zack Freedman (Voidstar Lab)
- license: MIT
- published: 2021 (last push 2023-02-02)
- accessed: 2026-07-03
- relevance: documented graph-topology (node/edge) LED mapping with ripple routing, ambient default behavior, full kit docs (Dozuki guide, BOM, video).

### [S566] Flaming Lotus Girls — Soma
- type: article
- url: https://www.flaminglotus.com/sculptures/soma
- author: Flaming Lotus Girls
- published: n/a (work 2009)
- accessed: 2026-07-03
- relevance: fire→LED retrofit for long-term public install (60+ custom controllable LED packages) with button-triggered pattern interaction; no code-level docs found.

## Block S600–S699 — Code-reading deep dives

### [S600] fadecandy — firmware + fcserver (PimentNoir community mirror)
- type: code
- url: https://github.com/PimentNoir/fadecandy
- pinned: PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d
- author: Micah Elizabeth Scott (scanlime); mirror maintained by PimentNoir
- license: MIT (per-file headers; firmware and server carry MIT permission text)
- accessed: 2026-07-03
- relevance: canonical temporal-dithering + keyframe-interpolation LED controller; the reference for "better than clown mode" low-brightness fades
- provenance: original scanlime/fadecandy repo deleted by author (confirmed 2026-07-03 [S015][S027]); this is a community mirror. Authenticity checked 2026-07-03: MIT LICENSE (c) 2013 Micah Elizabeth Scott, README references scanlime URLs, shallow history includes "Merge branch 'master' of https://github.com/scanlime/fadecandy" (ee9da65); mirror-added changes are limited to examples (dependabot minimist bump, Processing example tweaks) — firmware/ and server/ appear unmodified from upstream.
- excerpts: research/excerpts/S600-fadecandy-pixel-pipeline/ (updatePixel, lutInterpolate, calculateInterpCoefficient)

### [S615] FastLED repository (deep-dive pin)
- type: code
- url: https://github.com/FastLED/FastLED
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
- author: Zach Vorhies (maintainer), Daniel Garcia & Mark Kriegsman (original)
- license: MIT (verified in LICENSE at pinned sha, 2026-07-03)
- accessed: 2026-07-03
- relevance: deep-dive pin for quality machinery — temporal dithering, five_bit_hd_gamma, color correction, palettes, chipset timing; supersedes seed [S008] for line-level cites. Findings: research/code-reading/fastled.md. Excerpts: research/excerpts/S615-binary-dither/, S615-five-bit-hd-gamma/, S615-compute-adjustment/. Note: tree is 3.10.4-dev (`FASTLED_VERSION 3010004`), release_notes.md at this sha lists 3.10.4 as "Next Release"

### [S630] LedFx — Python audio-reactive LED engine (repo)
- type: code
- url: https://github.com/LedFx/LedFx
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx developers (Austin Hodges et al.)
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: The most complete Python LED engine; object model, render loop, audio pipeline, and network output drivers directly inform pewpew's architecture.

### [S645] WLED repository (deep-dive pin)
- type: code
- url: https://github.com/wled/WLED
- pinned: wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63
- author: Christian Schwinne (Aircoookie) and WLED contributors
- license: EUPL v1.2 or later
- accessed: 2026-07-03
- relevance: candidate receiver tier for pewpew; segment/effect model, realtime UDP/E1.31/DDP ingest, bus_manager/NeoPixelBus output, ABL power limiting, sync + JSON API. Findings: research/code-reading/wled.md
- excerpts: research/excerpts/S645-abl-power-limiter/, S645-gamma-tables/, S645-ddp-ingest/

### [S646] WLED-MM (MoonModules fork)
- type: code
- url: https://github.com/MoonModules/WLED-MM
- pinned: MoonModules/WLED-MM@7c55f91f1aecca548a63582e25934fdb0b7f6988
- author: MoonModules team (ex Atuline/WLED-SR; @softhack007 et al.)
- license: EUPL v1.2 or later
- accessed: 2026-07-03
- relevance: WLED fork (v0.14 base, branch mdev, tag nightly) — origin of the audioreactive usermod and um_data_t audio exchange (since upstreamed); HUB75 output; doc-level diff in research/code-reading/wled.md §6

### [S660] led-control — web-controlled Python LED animation engine for Raspberry Pi
- type: code
- url: https://github.com/jackw01/led-control
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
- author: jackw01
- license: MIT
- accessed: 2026-07-03
- relevance: closest prior art to "Python per-pixel pattern engine done well"; RestrictedPython per-pixel shaders + SWIG C render extension; claims ~150 fps @ 150 RGBW on Pi Zero. Pinned code-reading record for seed [S017] (same sha as [S210]/[S255] pins). Maintenance (GitHub API, 2026-07-03): pushed_at 2023-11-10, 193 stars, 40 forks, 17 open issues, bus factor 1 (jackw01: 288 of ~294 contributions). Excerpts: excerpts/S660-hsv2rgb-rainbow-render/, S660-restricted-pattern-compile/, S660-frame-loop-hoisting/. Findings: code-reading/led-control.md

### [S670] marimapper — camera-based 3D LED mapper (code)
- type: code
- url: https://github.com/TheMariday/marimapper
- pinned: TheMariday/marimapper@7dc5f799a1b7c180573c2632f6d12a3be0cbf4fa
- author: TheMariday (Mari D)
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: current best open camera-based 3D LED mapper; candidate subprocess tool for pewpew spatial mapping

### [S671] marimapper issue tracker — detection failure modes
- type: forum
- url: https://github.com/TheMariday/marimapper/issues
- author: TheMariday + community
- accessed: 2026-07-03
- relevance: real-world failure modes (reflections #66/#54, detector hang #84, macOS exposure #51, large-scan corruption #48, LED count regression #37, disconnected maps #81) informing pewpew mapper robustness requirements

### [S672] GNU GPL FAQ — mere aggregation and arm's-length process separation
- type: docs
- url: https://www.gnu.org/licenses/gpl-faq.html
- author: Free Software Foundation
- accessed: 2026-07-03
- relevance: establishes that invoking GPLv3 marimapper as a separate process with file/CLI exchange ("pipes, sockets and command-line arguments are communication mechanisms normally used between two separate programs"; free and nonfree programs may ship together if they "communicate at arms length") keeps pewpew unconstrained

### [S680] simap/pixelblaze — official docs repo (language + mapper reference)
- type: docs
- url: https://github.com/simap/pixelblaze/tree/v3
- pinned: simap/pixelblaze@20d169f30f7912b2245c57ab9bd721436324bf04 (v3 branch)
- author: Ben Hencke (simap)
- license: no LICENSE file (docs repo; firmware itself closed). Third-party component licenses listed in README.
- published: last commit 2020-10-26
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260521061924/https://github.com/simap/pixelblaze/tree/v3
- relevance: canonical pattern-language reference (README.expressions.md) and mapper/world-units doc (README.mapper.md) — same text shipped in the device editor; also indexes all open Pixelblaze-adjacent repos
- note: README.mapper.md is the same underlying document as [S304] (pinned repo copy vs seed URL) — do not co-cite the pair as independent corroboration

### [S681] zranger1/pixelblaze-client — Python WebSocket client library
- type: code
- url: https://github.com/zranger1/pixelblaze-client
- pinned: zranger1/pixelblaze-client@9be84700248fa17f0123c702a2939213ba69800a
- author: ZRanger1 (Jon Belson) et al.
- license: MIT (verified in LICENSE.md, (c) 2020-2025 ZRanger1)
- published: last commit 2025-12-20
- accessed: 2026-07-03
- relevance: most complete open documentation of the Pixelblaze WebSocket API — pattern upload, setVars, preview frames, config, sequencer control

### [S682] simap/pixelblaze_output_expander — expander firmware + protocol spec (v3.x branch)
- type: code
- url: https://github.com/simap/pixelblaze_output_expander/tree/v3.x
- pinned: simap/pixelblaze_output_expander@7a6295b12056db35be3dfd2629783050020db7ae (v3.x branch)
- author: Ben Hencke (simap)
- license: MIT (firmware); CC-BY-SA-4.0 (hardware) — stated in README
- published: last commit 2023-07-07
- accessed: 2026-07-03
- relevance: the open "UPXL" 2 Mbps serial protocol — the one Pixelblaze interface pewpew could drive directly; STM32L432, 8ch, DMA bit-banging per Fadecandy/OctoWS2811

### [S683] simap/pixelblaze_sensor_board — sensor board firmware + serial format
- type: code
- url: https://github.com/simap/pixelblaze_sensor_board
- pinned: simap/pixelblaze_sensor_board@15b3d271e0d6535965a68b15f057bac58a3154d7
- author: Ben Hencke (simap)
- license: MIT (firmware); CC-BY-SA-4.0 (hardware) — stated in README
- published: last commit 2022-07-06
- accessed: 2026-07-03
- relevance: open "SB1.0" 115200-baud sensor stream; dual-rate fixed-point FFT (20 kHz + 400 Hz) into 32 log bands, accelerometer/light/analog — reusable audio front-end design

### [S684] ElectroMage forum — "Output expander that implements Fadecandy dithering"
- type: forum
- url: https://forum.electromage.com/t/output-expander-that-implements-fadecandy-dithering/840
- author: forum users; key reply by wizard (Ben Hencke)
- published: 2020-12-18 (wizard reply)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260704010412/https://forum.electromage.com/t/output-expander-that-implements-fadecandy-dithering/840
- relevance: Hencke's on-record position that Pixelblaze does NOT use temporal dithering (refresh-rate limits; prefers APA102-class global-brightness bits) — pins down what v3.47 "HDR" is and is not

### [S685] ElectroMage forum — recent-activity snapshot (latest topics, mid-2026)
- type: forum
- url: https://forum.electromage.com/latest
- author: forum community; wizard (Ben Hencke) active in Pico Plus thread
- accessed: 2026-07-03
- relevance: ecosystem-health evidence — forum active May–Jul 2026 (Pico Plus thread with wizard replies 2026-06-28, PXLBLZ third-party editor announced 2026-06-16, editable-vars feature request 2026-07-03); no firmware release announcement newer than v3.47 visible

## Block S700–S749 — Code-reading deep dives (Phase 1 additions)

### [S700] HyperHDR — high-performance ambient lighting engine (Infinite Color Engine)
- type: code
- url: https://github.com/awawa-dev/HyperHDR
- pinned: awawa-dev/HyperHDR@6d5fe8769c8e3d070003a25952d07424a2ae2584
- author: awawa-dev
- license: MIT (Copyright (c) 2020-2026 awawa-dev)
- accessed: 2026-07-03
- relevance: Only shipping implementation of pewpew's target output stack — float linear-sRGB pipeline + adaptive temporal dithering + deep-color (HD108) output. Master at pin contains the v22 Infinite Color Engine (tag v22.0.0.0beta2 = a6fa8a2d6e51734785f4331a2d758c4a0247fea0, plus smoothing drift fix #1561).

### [S715] projectMM (MoonModules v3 clean-slate LED/DMX runtime)
- type: code
- url: https://github.com/ewowi/projectMM (redirects to https://github.com/MoonModules/projectMM)
- pinned: ewowi/projectMM@d5ee07ce3d6c590019cbbde670de8c532b2df511
- author: ewowi (Ewoud Wijma) / MoonModules
- license: GPL-3.0 (verified from LICENSE, 2026-07-03)
- accessed: 2026-07-03
- relevance: 2026 clean-slate successor to MoonLight by the WLED-MM authors; Layouts→Layers→Drivers pipeline, modifier-as-LUT-fold mapping, live no-reboot reconfiguration, and an 818-line explicit postmortem of MoonLight/WLED architecture decisions — a free autopsy of the architectures pewpew might otherwise copy. Deep dive: code-reading/modern-engines.md §A.

### [S716] SmoothLed (ATtiny interpolating/dithering WS2812 driver)
- type: code
- url: https://github.com/mattshepcar/SmoothLed
- pinned: mattshepcar/SmoothLed@e09236cfc63a96c565d97ef316073452a38cf86d
- author: Matt Shepcar
- license: MIT (verified from LICENSE, 2026-07-03)
- published: 2020 (last commit 2020-07-07; dormant since)
- accessed: 2026-07-03
- relevance: Fadecandy-style interpolation + temporal dithering on ATtiny-class AVR (5 B RAM/channel, 64 cycles/channel, zero frame buffer via CCL hardware waveform) — existence proof for pewpew's wearable-tier quality layer. Deep dive: code-reading/modern-engines.md §B. Excerpts: excerpts/S716-smoothled-inner-loop/.

## Block S750+ — Synthesis & later additions

### [S750] Pixelblaze firmware release announcements V3.66 & V3.67 (ElectroMage forum)
- type: forum
- url: https://forum.electromage.com/c/news-and-announcements/10
- author: Ben Hencke (wizard)
- published: 2024-12-13 (V3.66), 2025-11-28 (V3.67)
- accessed: 2026-07-03
- archive: TBD — archive.org snapshot of the category page pending (Discourse JSON verified live 2026-07-03)
- relevance: corrects the "firmware stalled at v3.47" finding — V3.66 (Community Patterns overhaul, more LED types; finalized beta v3.60) and V3.67 (bugfixes, pb32 + pico32 binaries) shipped after v3.47; verified via category JSON and search.json cross-check on 2026-07-03

### [S751] Adafruit: "The Raspberry Pi RP2350 Speeds Up CircuitPython and MicroPython Projects!" (Python on Microcontrollers newsletter, 2024-08-26)
- type: article
- url: https://www.adafruitdaily.com/2024/08/26/python-on-microcontrollers-newsletter-the-raspberry-pi-rp2350-speeds-up-circuitpython-and-micropython-projects-circuitpython-python-micropython-thepsf-raspberry_pi/
- author: Adafruit
- published: 2024-08-26
- accessed: 2026-07-03
- relevance: vendor-measured corroboration for the RP2350 ~2x claim used by W-1/W-2 and ADR-008/ADR-013: "real world" MicroPython tests up to 2x faster vs RP2040; "The M33 has an FPU, and is 'basically' 2x as fast as the M0+ of the RP2040 when we speed-tested it"; C/C++ float up to 20x

### [S752] CircuitPython Zephyr port: Nordic nRF54L15 DK board page + XIAO nRF54L15 feature request (#10647)
- type: docs
- url: https://circuitpython.org/board/nordic_nrf54l15dk/
- author: CircuitPython project / Adafruit
- published: 2025-2026 (issue #10647 opened 2025-09; Arduino-core-for-nRF54L15 blog post 2026-02-17)
- accessed: 2026-07-03
- relevance: pins the nRF54-in-hobby-ecosystem status for RA-09/ADR-013: a Zephyr-port CircuitPython build exists for the nRF54L15 DK, but no mainstream hobby boards ship it (Seeed XIAO support still an open request) — nRF52840 not displaced as of 2026-07-03

### [S753] WLED releases/tags (wled/WLED) — v16.0.1, v0.15.5
- type: code
- url: https://github.com/wled/WLED/releases
- author: WLED project
- published: 2026-05-03 (v16.0.0), 2026-06-30 (v16.0.1 tag), 2026-04-11 (v0.15.5 tag)
- accessed: 2026-07-03
- relevance: freshness update for RA-01/RA-11: v16.0.1 bugfix release shipped 2026-06-30 (was "in progress" at research time); 0.15.x maintenance continued to 0.15.5 (2026-04-11); nightlies through 2026-07-02

### [S754] WLED docs — Getting Started (browser install & OTA updates)
- type: docs
- url: https://kno.wled.ge/basics/getting-started/
- author: WLED project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260624190621/https://kno.wled.ge/basics/getting-started/  # snapshot 2026-06-24
- relevance: WLED's standard field-update paths — browser-based initial flash (install.wled.me) and integrated OTA update from the device web UI — the update precedent pewpew's receiver firmware inherits (completeness-critique sweep 3)

### [S755] ESP Web Tools (ESPHome project)
- type: docs
- url: https://esphome.github.io/esp-web-tools/
- author: ESPHome / Open Home Foundation
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260622052935/https://esphome.github.io/esp-web-tools/  # snapshot 2026-06-22
- relevance: ecosystem-standard browser flashing (Web Serial) with Improv WiFi provisioning; powers the WLED/Tasmota one-click installers — the install/recovery path for pewpew receiver firmware (completeness-critique sweep 3)

### [S756] ESP-IDF documentation — Over The Air Updates (OTA), ESP32-S3
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html
- author: Espressif Systems
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260304210916/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html  # snapshot 2026-03-04
- relevance: esp-idf dual OTA app partitions with rollback/anti-rollback — the safe field-update and bad-flash-recovery mechanism for the Phase-4 ESP32-S3 pewpew receiver (completeness-critique sweep 3)

### [S757] WLED issue #4252 — Matter support discussion
- type: forum
- url: https://github.com/wled/WLED/issues/4252
- author: WLED community
- accessed: 2026-07-03
- relevance: native Matter support in WLED is an open discussion, not landed — the watch item for RA-12's Matter exclusion (completeness-critique sweep 2)

### [S758] zackelia/wled-matter-bridge
- type: code
- url: https://github.com/zackelia/wled-matter-bridge
- author: Zack Elia
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260511093720/https://github.com/zackelia/wled-matter-bridge  # snapshot 2026-05-11
- relevance: existence proof that Matter reaches WLED devices via a bridge process (on/off/brightness/color only) — bridging, not native, is the current Matter/LED state of the art (completeness-critique sweep 2)

### [S759] maui1911/TLED — Matter-over-Thread addressable LED controller
- type: code
- url: https://github.com/maui1911/TLED
- author: maui1911
- accessed: 2026-07-03
- relevance: ESP32-C6 Matter-over-Thread addressable controller — shows Matter's light model carries basic color/level control, not addressable effect surfaces (completeness-critique sweep 2)

### [S760] WLED issue #5020 — ESP32-C5 support request
- type: forum
- url: https://github.com/wled/WLED/issues/5020
- author: WLED community
- accessed: 2026-07-03
- relevance: ESP32-C5 (dual-band 2.4/5 GHz WiFi 6) in mass production and requested for WLED since 2025-10; no support landed as of 2026-07-03 — the RA-08 watch item; 5 GHz receivers would relieve the AP-capacity ceiling (completeness-critique sweep 1)
