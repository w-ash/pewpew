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
- archive: https://web.archive.org/web/20260621120941/https://kno.wled.ge/interfaces/e1.31-dmx/
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
- archive: https://web.archive.org/web/20250628110943/https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt
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

## Block S750–S799 — Synthesis & later additions

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

## Block S800–S849 — RA-13 ESP-NOW & fleet scaling

### [S800] ESP-IDF Programming Guide — ESP-NOW (ESP32-S3, latest/v5.x)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710143137/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html
- relevance: Authoritative API reference: v1 (250 B) vs v2 (1470 B) payload limits and mixing rules, 20-peer table / 7-default-encrypted-peer limits (CONFIG_ESP_WIFI_ESPNOW_MAX_ENCRYPT_NUM up to 17), PMK/LMK CCMP encryption model, vendor-specific action-frame layout (category 127, OUI 0x18fe34, 4-byte random field), default 1 Mbps rate, esp_now_set_peer_rate_config, send-callback semantics ("received successfully on the MAC layer" — no app-layer guarantee), "encrypting multicast vendor-specific action frame is not supported", ESP_ERR_ESPNOW_NO_MEM back-pressure guidance, wake-window power save.

### [S801] Espressif ESP-NOW solution overview page
- type: product
- url: https://www.espressif.com/en/solutions/low-power-solutions/esp-now
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Vendor positioning: one-to-many and many-to-many topologies, "millisecond-level delay", 200 m open-space range, +21 dBm TX, supported chip families (ESP8266/ESP32/S-series/C-series — Espressif-only, no third-party silicon), coexistence with WiFi and BLE.

### [S802] ESP-FAQ — ESP-NOW section
- type: docs
- url: https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260319154338/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html
- relevance: Official FAQ: 20 unicast peers max; ~6 simultaneously controllable encrypted peers; broadcast "theoretically there is no limitation in the number of devices"; ESP-NOW+WiFi STA must share the AP's channel; measured one-to-one throughput 214 kbps (open) / 555 kbps (shielded); default 1 Mbps changeable via esp_wifi_config_espnow_rate; 250 B v1 limit "does not support configuration" (IE-field constraint).

### [S803] arduino-esp32 issue #11261 — "Support ESP-Now Version 2 packet size"
- type: forum
- url: https://github.com/espressif/arduino-esp32/issues/11261
- author: arduino-esp32 community / Espressif maintainers
- published: 2025-04-19
- accessed: 2026-07-09
- relevance: Shows the Arduino-ESP32 ESP_NOW wrapper still capped payloads at ESP_NOW_MAX_DATA_LEN (250 B) as of April 2025 even where the underlying IDF supports v2; 1000-byte v2 frames tested working on ESP32-S3 once the cap is lifted (PR #11524). Evidence that wrapper support lags IDF and that v2 capability is IDF-version-, not hardware-, dependent.

### [S804] Becker et al., "ESP-NOW Performance in Outdoor Environments: Field Experiments and Analysis" (WONS 2025)
- type: article
- url: https://dl.ifip.org/db/conf/wons/wons2025/1571077625.pdf
- author: B. Becker, C. Oberli, J. Zobel, R. Steinmetz, T. Meuser (TU Darmstadt / PUC Chile)
- published: 2025
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251009212258/https://dl.ifip.org/db/conf/wons/wons2025/1571077625.pdf
- relevance: Best sniffer-verified low-level study found. ESP-NOW (IDF 4.4.6 defaults, ESP32-S3 Heltec boards) transmits 802.11b MPDUs at 1 Mbit/s / 20 MHz; unicast performs up to 31 retransmissions with p-persistent geometric backoff (~481 µs average slot, first retransmission at ~3.4 ms); driver-to-first-transmission latency 2673–2780 µs for 250 B payloads; farmland PDR 99.97 % below 55 m (0.95 m antenna height) collapsing non-monotonically beyond; forest 133/205 positions usable; validated delay model (t_tx = 2800 µs, t_rtx = 3350 µs, n_max = 31). Also confirms CSMA carrier sensing and cites prior latency measurements (1059 µs for 1 B, 1869 µs for 100 B payloads).

### [S805] Espressif Developer Portal — "Data transmission reliability over ESP-NOW protocol in indoor environment"
- type: article
- url: https://developer.espressif.com/blog/reliability-esp-now/
- author: Michal Kubaščík (Espressif developer portal)
- published: 2024-12-19
- accessed: 2026-07-09
- relevance: Official-portal measured writeup: 8 ESP32 sensor nodes unicasting at 4 packets/s indoors through walls to an ESP32-S3/C6 hub; only ~half the node placements delivered reliably; packet loss dominated by building structure; recommends segmenting deployments and app-level delivery control. Grounds the claim that RSS/obstruction, not airtime, is the first-order loss factor at small fleet sizes.

### [S806] Magzym et al., "Synchronized ESP-NOW for Improved Energy Efficiency" (IEEE BlackSeaCom 2023)
- type: article
- url: https://www2.compute.dtu.dk/~xefa/files/conf/2023-blacksea-eps-now.pdf
- author: Y. Magzym, A. Eduard, D. Urazayev, X. Fafoutis, D. Zorbas (Nazarbayev University / DTU)
- published: 2023
- accessed: 2026-07-09
- archive: pending
- relevance: Documents the full ESP-NOW frame layout with byte counts (24 B MAC header + 1 B category + 3 B OUI + 4 B random + 7 B vendor-IE header + 0–250 B body + 4 B FCS = 43 B protocol overhead); "No acknowledgment is required for broadcast transmissions"; "The default IEEE802.11 CSMA mechanism is used to avoid collisions"; broadcast not encryptable, app-layer pre-shared keys suggested; LR mode = proprietary modulation at 250/500 kbps requiring all devices set to LR. Measured broadcast PRR at 20 dBm/LR-250kbps indoors: 98.4–100 % at RSS ≥ −72 dBm, 79.8 % at −80.5 dBm, 29.8 % at −92 dBm (always-on receivers); 40 Mbit/s co-channel WiFi interference cost <1 percentage point PRR at −65 dBm.

### [S807] ESP-IDF Programming Guide v5.2 — Wi-Fi Driver (ESP32), Long Range section
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32/api-guides/wifi.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20240720014143/https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32/api-guides/wifi.html (snapshot predates accessed date; refresh next verification pass)
- relevance: LR mode specifics: Espressif-proprietary PHY at "1/2 Mbps and 1/4 Mbps"; "reception sensitivity gain of LR is about 4 dB larger than that of the traditional 802.11b mode"; "theoretically, the transmission distance is about 2 to 2.5 times the distance of 11B"; LR works only between Espressif devices ("ESP32 chip series devices (except ESP32-C2)"); recommended when both ends are Espressif and throughput needs are small.

### [S808] WLED docs — ESP-NOW remote (WiZmote) support
- type: docs
- url: https://kno.wled.ge/interfaces/infrared/
- author: WLED project (EUPL-1.2 project; docs page)
- accessed: 2026-07-09
- relevance: Established-project ESP-NOW deployment: "Since version WLED 0.14.0-beta3: An ESP-NOW compatible remote control is supported" (WiZmote); remote is identified by MAC address; DIY remotes on ESP32-C3 supported. Shows the fixed-layout small-payload broadcast pattern in a mainstream LED firmware.

### [S809] Arduino-ESP32 documentation — ESP-NOW library (3.x API)
- type: docs
- url: https://docs.espressif.com/projects/arduino-esp32/en/latest/api/espnow.html
- author: Espressif Systems (arduino-esp32, LGPL-2.1)
- accessed: 2026-07-09
- relevance: Current Arduino wrapper: ESP_NOW class + ESP_NOW_Peer abstract class, broadcast via dedicated broadcast address, ESP_NOW.getMaxDataLen(); broadcast-slave example receives frames from unregistered senders and registers them on the fly — evidence that reception does not require prior peer registration; same-channel requirement stated.

### [S810] espressif/esp-now application-layer component (User_Guide.md)
- type: code
- url: https://github.com/espressif/esp-now
- pinned: espressif/esp-now@4432294ef6a6cb274b441c0678414455a4055cff
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: Espressif's app layer above raw ESP-NOW: provisioning, bind/control, ESP-NOW OTA ("50 devices can be upgraded in 3 minutes"), debug/log, ECDH + AES128-CCM app-layer security ("16 devices can be configured in 5 seconds"); one-to-many/many-to-many control. User Guide targets IDF release/v4.4–v5.2 — lags current IDF. Last commit 2026-02-04; 766 stars. Reference for app-layer reliability/security patterns over unencrypted broadcast.

### [S811] esp-idf `esp_now.h` header (constants across v5.3/v5.4/v5.5/master)
- type: code
- url: https://github.com/espressif/esp-idf/blob/master/components/esp_wifi/include/esp_now.h
- pinned: espressif/esp-idf@f0887bcf8763266effe3fa0b358340df226a04b5
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: Primary evidence for API evolution, compared across git tags at read time: v5.3 has only ESP_NOW_MAX_DATA_LEN=250; v5.4 introduces ESP_NOW_MAX_DATA_LEN_V2=1490; v5.5 and master correct it to 1470. ESP_NOW_MAX_TOTAL_PEER_NUM=20, ESP_NOW_MAX_ENCRYPT_PEER_NUM=6 at pinned master L32–L37; v1/v2 truncate-or-discard mixing rule L150–L151; esp_now_set_peer_rate_config(peer_addr, wifi_tx_rate_config_t) L283. esp_wifi_config_espnow_rate is marked deprecated in the v5.5 tag ("please use esp_now_set_peer_rate_config() instead", "only work when not use Wi-Fi 6") and is removed entirely at pinned master.

### [S812] ESP-IDF Programming Guide — RF Coexistence (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/coexist.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: WiFi/BLE share one 2.4 GHz RF chain by time-division: "a module cannot receive or transmit data while another module is engaged in data transmission or reception"; dynamic priority arbitration by WiFi state; coexistence table marks ESP-NOW TX stable ("Y") alongside BLE but ESP-NOW RX only "stable in STA mode, otherwise not supported"; recommends CONFIG_ESP_COEX_SW_COEXIST_ENABLE and pinning WiFi/BT tasks to separate cores.

### [S813] "Field Testing and QoS Analysis of ESP-NOW Communication on ESP32" (IEEE, 2024)
- type: article
- url: https://ieeexplore.ieee.org/document/10824617/
- author: IEEE conference publication
- published: 2024
- accessed: 2026-07-09
- relevance: Field QoS measurements: ESP-NOW latency 5.13–46 ms across tested distances; packet loss becomes substantial beyond 180 m; up to 99 % packet error rate at 300 m. (Read via abstract; full text paywalled.)

### [S814] espressif/esp-now issue #115 — "esp_now latency (AEGHB-603)"
- type: forum
- url: https://github.com/espressif/esp-now/issues/115
- author: espressif/esp-now issue tracker
- published: 2024-03-30
- accessed: 2026-07-09
- relevance: User measurement: broadcast latency normally 5–7 ms; when successive sends were spaced <20 ms apart the send queue backed up and latency ballooned to 50–200 ms — concrete evidence of the send-queue congestion failure mode at high offered rates.

### [S815] WLED issue #4063 — "Implement ESP-NOW broadcast on selected channel"
- type: forum
- url: https://github.com/Aircoookie/WLED/issues/4063
- author: WLED community
- published: 2024-07-19
- accessed: 2026-07-09
- relevance: Practitioner statement of the channel constraint: "ESP-NOW sync message is currently transmitted on the same channel as connected WiFi", so nodes not on the AP's channel never hear broadcasts; the only workaround discussed is disconnect-send-reconnect with websocket-client fallout. Real-world consequence of the coexistence channel rule for mixed WiFi/ESP-NOW fleets.

### [S816] esp32.com thread — "ESPNOW messages being dropped" (t=35066)
- type: forum
- url: https://esp32.com/viewtopic.php?f=13&t=35066
- author: esp32.com community
- accessed: 2026-07-09
- relevance: Reported fleet-congestion data point: 13 ESP32-C3 nodes each sending up to 10 msg/s (~130 msg/s aggregate on one channel) saw ~20 % packet drop, attributed in-thread to channel congestion; guidance to pace sends on the send callback. NOTE: thread body is behind a bot-challenge wall at access time; figures taken from search-index excerpts — [NEEDS-VERIFICATION].

### [S817] IEEE 802.11-2020 — DSSS/HR-DSSS PHY and DCF MAC timing parameters
- type: spec
- url: https://standards.ieee.org/ieee/802.11/7028/
- author: IEEE
- published: 2021-02-26
- accessed: 2026-07-09
- archive: pending
- relevance: Source of the airtime constants used in the fleet-scaling arithmetic: 1 Mbit/s DSSS long PLCP preamble+header = 192 µs; 2.4 GHz DSSS slot time 20 µs, DIFS 50 µs, CWmin 31; group-addressed (broadcast/multicast) frames are never ACKed or retransmitted under DCF. (Standard consulted at parameter level; full text via IEEE Get-802 program.)

### [S818] WLED CHANGELOG — ESP-NOW feature timeline
- type: docs
- url: https://github.com/wled/WLED/blob/main/CHANGELOG.md
- author: WLED project (EUPL-1.2)
- accessed: 2026-07-09
- relevance: Dates WLED's ESP-NOW adoption: remote support build 2306270 (2023-06-27, #3237), WiZmote JSON overrides build 2306020, ESP-NOW packet modification build 2402090 (2024-02-09), WiZmote byte-format cleanup build 2409100 (#4114). Confirms stock WLED uses ESP-NOW for remote control only — pixel/effect sync remains UDP-over-WiFi.

## Block S850–S899 — RA-14 Mesh transport alternatives

### [S850] painlessMesh — canonical GitLab repository
- type: code
- url: https://gitlab.com/painlessMesh/painlessMesh
- pinned: painlessMesh/painlessMesh@1b2a02be2603b8a3e418338811326a81642bd46f
  (GitLab, branch `develop`, HEAD at access time; resolve via
  https://gitlab.com/painlessMesh/painlessMesh/-/blob/<sha>/<path>)
- author: painlessMesh contributors (orig. forked from Coopdis/easyMesh)
- license: GPL-3.0
- accessed: 2026-07-09
- relevance: ad-hoc softAP+STA WiFi mesh candidate for the autonomous-group
  tier; README documents architecture, JSON messaging, heap-bound size limit,
  and message-loss caveats. Last release v1.5.7 (2025-10-01); last repo
  activity 2026-06-14; not archived.

### [S851] painlessMesh issue #217 — "mesh is not working on 72 nodes (ESP8266)"
- type: forum
- url: https://gitlab.com/painlessMesh/painlessMesh/-/work_items/217
- author: painlessMesh issue reporter (72-node NodeMCU experiment)
- accessed: 2026-07-09
- archive: pending
- relevance: best available field data on painlessMesh scaling: 36 nodes OK,
  26/50 visible at 50 nodes, 0/72 at 72 nodes, with free heap remaining —
  failure at exactly pewpew's target fleet size.

### [S852] painlessMesh issue #490 — "Maximum number of nodes"
- type: forum
- url: https://gitlab.com/painlessMesh/painlessMesh/-/issues/490
- author: painlessMesh issue reporter (60-node build targeting 200)
- accessed: 2026-07-09
- archive: pending
- relevance: corroborating scaling report: 40–44 of 60 nodes stable, older
  nodes drop as new ones join; ~1200-byte subConnectionJson topology payload;
  200-node question unanswered by maintainers.

### [S853] ESP-IDF Programming Guide — ESP-WIFI-MESH API guide
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-guides/esp-wifi-mesh.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251118072742/https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-guides/esp-wifi-mesh.html
- relevance: authoritative description of tree topology, softAP+STA node
  roles, router-RSSI root election (90% vote threshold), fixed-root/no-router
  mode, and vendor performance figures (100-device test, 6 layers × 6
  downstream, per-hop delay 10–30 ms, healing <10 s root / <5 s child).

### [S854] ESP-FAQ — ESP-WIFI-MESH Application Framework
- type: docs
- url: https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/wifi-mesh-development-framework.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260601145155/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/wifi-mesh-development-framework.html
- relevance: Espressif's own steering: "recommended to use our newly released
  ESP-Mesh-Lite solution, instead of Wi-Fi Mesh" for new designs; no-router
  caveat that a designated root that crashes cannot be recovered from; claims
  ESP32 Wi-Fi mesh supports 1,000 devices (≤512 recommended).

### [S855] espressif/esp-mesh-lite — repository incl. User Guide
- type: code
- url: https://github.com/espressif/esp-mesh-lite
- pinned: espressif/esp-mesh-lite@88d690d16bcd505270e512f4050b6871b16e5922
- author: Espressif Systems
- license: Apache-2.0 (license text), but mesh core distributed only as
  precompiled static libraries (components/mesh_lite/lib/libesp_mesh_lite_*.a)
- accessed: 2026-07-09
- relevance: Espressif's recommended successor Wi-Fi mesh; IP-layer NAT tree
  (15 layers × 10 downstream max), per-hop delay 8–12 ms, repair <50 s root /
  <45 s child on a 50-device test; no_router example requires a statically
  designated root. Branch release/v1.0 pushed 2025-09-30.

### [S856] Alteriom/painlessMesh — active third-party fork
- type: code
- url: https://github.com/Alteriom/painlessMesh
- pinned: TBD (repo-level citation only: maintenance-status evidence)
- author: Alteriom
- license: GPL-3.0
- accessed: 2026-07-09
- relevance: evidence on painlessMesh ecosystem health: fork releasing
  through v1.9.20 (2026-03-27) while upstream idles, but with negligible
  adoption (9 stars) — the community has not consolidated on a successor.

### [S857] gmag11/painlessMesh — GitHub mirror notice
- type: code
- url: https://github.com/gmag11/painlessMesh
- pinned: TBD (repo-level citation only: mirror/migration status)
- author: gmag11 (Germán Martín)
- license: GPL-3.0
- accessed: 2026-07-09
- relevance: documents the GitHub→GitLab migration: repo describes itself as
  "a mirror copy of https://gitlab.com/painlessMesh/painlessMesh" with issues
  and PRs centralized on GitLab.

### [S858] ESP-IDF Programming Guide — ESP-BLE-MESH overview
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/esp-ble-mesh/ble-mesh-index.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: ESP32 BLE-mesh implementation status: built on Zephyr mesh
  stack, certified to Mesh Profile v1.0.1 with v1.1 protocol examples;
  fast-provisioning example claims 100 devices provisioned in 60 s.

### [S859] ESP-BLE-MESH FAQ — coexistence and configuration
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/esp-ble-mesh/ble-mesh-faq.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Wi-Fi + BLE-mesh coexistence on one chip: throughput low without
  PSRAM, ">1 Mbps" with PSRAM — quantifies the single-radio time-slicing cost
  relevant to running any BLE stack beside rendering + ESP-NOW interop.

### [S860] Silicon Labs — Bluetooth Mesh 1.1 Network Performance
- type: docs
- url: https://docs.silabs.com/btmesh/latest/btmesh-11-network-performance/05-summary
- author: Silicon Labs
- accessed: 2026-07-09
- archive: pending
- relevance: largest published physical BLE-mesh measurement: 256 nodes on a
  38 m × 19 m floor; "latency … below 200 milliseconds, even out to 6 hops if
  the payload is less than 16 bytes", reliability >99% — but at dispatch
  intervals of 1.5–3 s per sender, ~15–30× below pewpew's 10 Hz per node.

### [S861] Rondón et al. — "Understanding the Performance of Bluetooth Mesh:
  Reliability, Delay and Scalability Analysis" (2019)
- type: article
- url: https://arxiv.org/abs/1910.03345
- author: R. Rondón, A. Mahmood, S. Grimaldi, M. Gidlund (Mid Sweden Univ.)
- published: 2019-10-08
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260103131441/https://arxiv.org/abs/1910.03345
- relevance: peer-reviewed scalability analysis: BLE mesh "is prone to
  broadcast storm"; in 52–106-device grids, density beyond ~86 devices
  increases loss and delay; 10% side-traffic pushes loss >10%; avg delay
  ~250 ms over 10+ hops worst-case; vulnerable to WLAN interference.

### [S862] Bluetooth SIG blog — "How Bluetooth Mesh Networking puts the
  'large' in large-scale wireless networks" (M. Woolley)
- type: article
- url: https://www.bluetooth.com/blog/mesh-in-large-scale-networks/
- author: Martin Woolley, Bluetooth SIG
- accessed: 2026-07-09
- archive: pending
- relevance: official SIG capacity framing: 32,767-node theoretical max;
  spec origination bound "less than 100 Lower Transport PDUs in a moving
  10-second window" (≤10 msg/s/node — pewpew's rate is at the cap); "ten
  relays will more or less multiply the number of packets … by ten".

### [S863] TI SimpleLink BLE5-Stack User's Guide — Developing a Bluetooth
  Mesh Application
- type: docs
- url: https://software-dl.ti.com/simplelink/esd/simplelink_cc13x2_26x2_sdk/4.40.00.44/exports/docs/ble5stack/ble_user_guide/html/ble-mesh/developing-a-ble-mesh-application.html
- author: Texas Instruments
- accessed: 2026-07-09
- relevance: vendor statement of transport limits ("maximum unsegmented
  payload of up to 15 bytes"; segmented: 12 bytes × ≤32 segments) and of the
  provisioning model (network key + address assignment per device).

### [S864] Bluetooth SIG — Mesh Protocol v1.1 specification
- type: spec
- url: https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/MshPRT_v1.1/out/en/index-en.html
- author: Bluetooth SIG
- published: 2023 (Mesh Protocol 1.1)
- accessed: 2026-07-09
- relevance: normative source for managed flooding, TTL, message cache,
  sequence numbers, provisioning data (NetKey/AppKey/unicast address), and
  unsegmented access-payload limits cited in RA-14.

### [S865] ESP-IDF Programming Guide — OpenThread (ESP32-C6)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/api-guides/openthread.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260502090443/https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/api-guides/openthread.html
- relevance: which Espressif chips have native 802.15.4 (H2/C6/C5); RCP
  architecture that adds Thread to Wi-Fi chips (incl. ESP32-S3) over
  UART/SPI, SPI recommended for latency — defines the hardware cost of a
  Thread coordination radio next to an S3.

### [S866] OpenThread — Thread Primer: Node Roles and Types
- type: docs
- url: https://openthread.io/guides/thread-primer/node-roles-and-types
- author: OpenThread project (Google)
- accessed: 2026-07-09
- relevance: router cap ("Thread tries to keep the number of Routers between
  16 and 23", 32 active router IDs), self-elected Leader, and Border Router
  defined as bridging to non-Thread networks ("any device may serve") — i.e.
  egress feature, not a requirement for a closed mesh.

### [S867] Silicon Labs AN1142 — Mesh Network Performance Comparison
  (Zigbee / Thread / Bluetooth mesh), Rev 0.5
- type: docs
- url: https://www.silabs.com/documents/public/application-notes/an1142-mesh-network-performance-comparison.pdf
- author: Silicon Labs
- accessed: 2026-07-09
- archive: pending
- relevance: only published like-for-like measurement of the three meshes at
  24–192 nodes: small-payload multicast latency "well under 200 ms" for all,
  Thread degrades least with payload, reliability ≥99.9% — but at 1 multicast
  per 3 s, with the caution that performance "deteriorate[s] further as this
  multicast load is increased"; also documents Thread all-device multicast as
  flooding with "three re-broadcasts from each router".

### [S868] ESP-IDF Wi-Fi Driver guide (ESP32, v4.4.4) — LR mode, softAP
  limits, multicast power-save behavior
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/v4.4.4/esp32/api-guides/wifi.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20240810125422/https://docs.espressif.com/projects/esp-idf/en/v4.4.4/esp32/api-guides/wifi.html (snapshot predates accessed date; refresh next verification pass)
- relevance: primary source for Espressif Long Range mode ("Espressif-
  patented", "only ESP32 devices can transmit and receive the LR data", PHY
  rates 1/4 and 1/2 Mbps, ~4 dB sensitivity gain, 2–2.5× 11B distance,
  1 km LoS claim); ESP32 softAP limit "up to 15 (ESP_WIFI_MAX_CONN_NUM)"
  (default 10); AP does not cache multicast for power-save stations.

### [S869] Cisco Meraki — Approximating Maximum Clients per Access Point
- type: docs
- url: https://documentation.meraki.com/MR/Wi-Fi_Basics_and_Best_Practices/Approximating_Maximum_Clients_per_Access_Point
- author: Cisco Meraki
- accessed: 2026-07-09
- archive: pending
- relevance: theoretical association limits per radio (128 for Wi-Fi 5 W1,
  512 for Wi-Fi 6) with explicit vendor caveat that real-world limits are
  "far lower" and theoretical maxima are not design targets — grounds the
  50-vs-150-station judgment for a single portable AP.

### [S870] 7SIGNAL — How to Determine Maximum Clients per Access Point
- type: article
- url: https://www.7signal.com/news/blog/how-to-determine-clients-per-ap
- author: 7SIGNAL
- accessed: 2026-07-09
- archive: pending
- relevance: enterprise Wi-Fi practice recommendation of ~30 active clients
  per AP in most environments — the practical ceiling figure used against
  the ~150-node design ceiling.

### [S871] ESP-IDF API Reference — ESP-NOW (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: cited here only for rate configurability ("The default ESP-NOW
  bit rate is 1 Mbps"; per-peer `esp_now_set_peer_rate_config()`), which is
  how the LR PHY composes with the RA-13 ESP-NOW design. ESP-NOW itself is
  RA-13's subject.

### [S872] espressif/esp-idf — Wi-Fi types header (LR PHY rates)
- type: code
- url: https://github.com/espressif/esp-idf
- pinned: espressif/esp-idf@f0887bcf8763266effe3fa0b358340df226a04b5
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: `WIFI_PHY_RATE_LORA_250K`/`WIFI_PHY_RATE_LORA_500K` defined as
  "Espressif-specific Long Range mode rate" in
  components/esp_wifi/include/esp_wifi_types_generic.h#L1236-L1237 —
  evidence that LR rates are exposed to ESP-NOW-style traffic in current IDF.

### [S873] The Things Network docs — Duty Cycle
- type: docs
- url: https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/
- author: The Things Network / The Things Industries
- accessed: 2026-07-09
- archive: pending
- relevance: ETSI EN 300 220 sub-band duty-cycle table (0.1%/1%/10% at
  868 MHz) and TTN fair-use policy (30 s uplink airtime/day) — the
  regulatory arithmetic that disqualifies LoRa at 10 Hz.

### [S874] The Things Network docs — Limitations
- type: docs
- url: https://www.thethingsnetwork.org/docs/lorawan/limitations/index.html
- author: The Things Network / The Things Industries
- accessed: 2026-07-09
- archive: pending
- relevance: "Low bandwidth - between 250bit/s and 11kbit/s in Europe";
  LoRaWAN unsuitable for "Realtime data - you can only send small packets
  every couple of minutes" — established-project statement of the rate
  ceiling.

## Block S900–S949 — RA-15 Decentralized coordination & sync

### [S900] Mirollo & Strogatz — Synchronization of pulse-coupled biological oscillators
- type: article
- url: https://epubs.siam.org/doi/10.1137/0150098
- author: Renato E. Mirollo, Steven H. Strogatz
- published: 1990 (SIAM Journal on Applied Mathematics, vol. 50 no. 6, pp. 1645–1662)
- accessed: 2026-07-09
- archive: pending
- relevance: the foundational firefly-sync model — proves all-to-all pulse-coupled integrate-and-fire oscillators converge to synchrony from almost all initial conditions; basis of every timestamp-free phase-sync scheme considered for pewpew's mesh tier. Author PDF: https://www.stevenstrogatz.com/articles/synchronization-of-pulse-coupled-biological-oscillators

### [S901] Werner-Allen et al. — Firefly-Inspired Sensor Network Synchronicity with Realistic Radio Effects (RFA)
- type: article
- url: https://mdw.la/papers/firefly-sensys05.pdf
- author: Geoffrey Werner-Allen, Geetika Tewari, Ankit Patel, Matt Welsh, Radhika Nagpal
- published: 2005 (ACM SenSys '05)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250318100936/https://mdw.la/papers/firefly-sensys05.pdf
- relevance: the canonical "firefly sync on real lossy radios" paper — Reachback Firefly Algorithm on 24 MicaZ motes; ~100–150 µs group spread, 1/ε convergence, MAC timestamping, reachback response, 25 ms pre-emptive message staggering. Directly informs pewpew's beat-phase layer design.

### [S902] Tyrrell, Auer & Bettstetter — Fireflies as Role Models for Synchronization in Ad Hoc Networks
- type: article
- url: https://eudl.eu/doi/10.1145/1315843.1315848
- author: Alexander Tyrrell, Gunther Auer, Christian Bettstetter
- published: 2006 (BIONETICS '06, ACM/ICST)
- accessed: 2026-07-09
- relevance: adapts Mirollo–Strogatz to wireless ad hoc constraints via delayed pulse emission and refractory periods; accuracy limited only by propagation delay in simulation. Full text not retrieved (403); details beyond abstract flagged NEEDS-VERIFICATION.

### [S903] Klinglmayr, Kirst, Bettstetter & Timme — Guaranteeing global synchronization in networks with stochastic interactions
- type: article
- url: https://iopscience.iop.org/article/10.1088/1367-2630/14/7/073031
- author: Johannes Klinglmayr, Christoph Kirst, Christian Bettstetter, Marc Timme
- published: 2012 (New Journal of Physics 14, 073031)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20220201173235/https://iopscience.iop.org/article/10.1088/1367-2630/14/7/073031 (snapshot predates accessed date; refresh next verification pass)
- relevance: proves PCO convergence to synchrony on arbitrary connected topologies with variable delays, where *stochastic/unreliable* pulse delivery is part of the convergence mechanism — the theoretical basis for claiming ESP-NOW-class packet loss does not break firefly sync.

### [S904] Bettstetter research group — Self-Organizing Synchronization (project summary)
- type: docs
- url: https://bettstetter.com/research/sync/
- author: Christian Bettstetter (research group page)
- accessed: 2026-07-09
- relevance: consolidated claims for the PCO line of work incl. Computer Networks 2016 hardware result — PCO sync with phase-rate correction on six programmable radio boards achieving sub-microsecond precision; first PCO evaluation on real radio hardware.

### [S905] Demers et al. — Epidemic Algorithms for Replicated Database Maintenance
- type: article
- url: http://bitsavers.trailing-edge.com/pdf/xerox/parc/techReports/CSL-89-1_Epidemic_Algorithms_for_Replicated_Database_Maintenance.pdf
- author: Alan Demers, Dan Greene, Carl Hauser, Wes Irish, John Larson, Scott Shenker, Howard Sturgis, Dan Swinehart, Doug Terry (Xerox PARC)
- published: 1987 (ACM PODC '87; Xerox PARC CSL-89-1)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250426184746/http://bitsavers.trailing-edge.com/pdf/xerox/parc/techReports/CSL-89-1_Epidemic_Algorithms_for_Replicated_Database_Maintenance.pdf
- relevance: origin of the anti-entropy / rumor-mongering / direct-mail taxonomy and the exponential-spread convergence argument underlying pewpew's parameter-gossip layer.

### [S906] Karp, Schindelhauer, Shenker & Vöcking — Randomized Rumor Spreading
- type: article
- url: https://zoo.cs.yale.edu/classes/cs426/2013/bib/karp00randomized.pdf
- author: Richard Karp, Christian Schindelhauer, Scott Shenker, Berthold Vöcking
- published: 2000 (IEEE FOCS 2000)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20180517132001/http://zoo.cs.yale.edu:80/classes/cs426/2013/bib/karp00randomized.pdf (snapshot predates accessed date; refresh next verification pass)
- relevance: rigorous O(log N) round bounds and Ω(n ln ln n) message lower bound for push-pull gossip — the convergence-bound baseline against which pewpew's broadcast-domain gossip is strictly easier.

### [S907] Shapiro, Preguiça, Baquero & Zawirski — Conflict-free Replicated Data Types
- type: article
- url: https://inria.hal.science/inria-00609399v1
- author: Marc Shapiro, Nuno Preguiça, Carlos Baquero, Marek Zawirski
- published: 2011 (SSS 2011; INRIA RR-7687)
- accessed: 2026-07-09
- archive: pending
- relevance: defines Strong Eventual Consistency and proves state-based CRDT convergence given a monotonic-semilattice merge — the formal justification that pewpew's max-epoch LWW parameter register converges under loss/reorder/duplication with no coordination.

### [S908] Lamport — Time, Clocks, and the Ordering of Events in a Distributed System
- type: article
- url: https://dl.acm.org/doi/10.1145/359545.359563
- author: Leslie Lamport
- published: 1978 (Communications of the ACM 21(7), 558–565)
- accessed: 2026-07-09
- relevance: logical (Lamport) clocks — the multi-writer generalization of pewpew's single-writer epoch counter; total order via counter + node-ID tiebreak.

### [S909] Parker et al. — Detection of Mutual Inconsistency in Distributed Systems
- type: article
- url: https://dl.acm.org/doi/10.1109/TSE.1983.236733
- author: D. Stott Parker Jr., Gerald Popek, Gerard Rudisin, Allen Stoughton, Bruce Walker, Evelyn Walton, Johanna Chow, David Edwards, Stephen Kiser, Charles Kline
- published: 1983 (IEEE Transactions on Software Engineering SE-9(3))
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250527141518/https://dl.acm.org/doi/10.1109/TSE.1983.236733
- relevance: version vectors — per-writer counters that detect (rather than arbitrate) concurrent updates; cited to show why they are overkill/oversized for pewpew's 11-byte single-writer state.

### [S910] RFC 6206 — The Trickle Algorithm
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc6206.html
- author: P. Levis, T. Clausen, J. Hui, O. Gnawali, J. Ko (IETF ROLL WG)
- published: 2011-03
- accessed: 2026-07-09
- archive: pending
- relevance: the standardized "gossip a version number over a lossy shared medium" algorithm (Imin/Imax/k, suppression, reset-on-inconsistency); production-proven in RPL. Pewpew borrows its suppression and reset semantics for the parameter-epoch layer.

### [S911] Levis, Patel, Culler & Shenker — Trickle: A Self-Regulating Algorithm for Code Propagation and Maintenance in Wireless Sensor Networks
- type: article
- url: https://www.usenix.org/legacy/event/nsdi04/tech/full_papers/levis/levis.pdf
- author: Philip Levis, Neil Patel, David Culler, Scott Shenker
- published: 2004 (USENIX/ACM NSDI 2004)
- accessed: 2026-07-09
- archive: pending
- relevance: original Trickle paper — empirical propagation-vs-maintenance-cost results in lossy multi-hop sensor networks that RFC 6206 later standardized.

### [S912] RFC 1982 — Serial Number Arithmetic
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc1982.html
- author: R. Elz, R. Bush (IETF)
- published: 1996-08
- accessed: 2026-07-09
- archive: pending
- relevance: defines wraparound-safe comparison of fixed-width monotonic counters (half-range window) — the correct comparison rule for pewpew's 1–2-byte parameter epoch field.

### [S913] Fatès — A Guided Tour of Asynchronous Cellular Automata
- type: article
- url: https://arxiv.org/pdf/1406.0792
- author: Nazim Fatès
- published: 2014 (Journal of Cellular Automata; arXiv:1406.0792)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251211075327/https://arxiv.org/pdf/1406.0792
- relevance: survey establishing that update policy (synchronous vs α-asynchronous vs random-order) is a first-class determinant of CA behavior — evidence that pewpew cannot naively port synchronous CA rules onto lossy asynchronous broadcast.

### [S914] Blok & Bergersen — Synchronous versus asynchronous updating in the "game of Life"
- type: article
- url: https://link.aps.org/doi/10.1103/PhysRevE.59.3876
- author: Hendrik J. Blok, Birger Bergersen
- published: 1999 (Physical Review E 59, 3876)
- accessed: 2026-07-09
- archive: pending
- relevance: quantifies α-asynchronism in Life — a critical phase transition (directed-percolation class) below which synchronous-tuned structures dissolve; the concrete warning that loss/async can kill emergent CA patterns.

### [S915] Abelson et al. — Amorphous Computing
- type: article
- url: https://cacm.acm.org/research/amorphous-computing/
- author: Harold Abelson, Don Allen, Daniel Coore, Chris Hanson, George Homsy, Thomas F. Knight Jr., Radhika Nagpal, Erik Rauch, Gerald Jay Sussman, Ron Weiss
- published: 2000 (Communications of the ACM 43(5), 74–82)
- accessed: 2026-07-09
- archive: pending
- relevance: foundational treatment of computing over "vast numbers of unreliable, locally communicating simple devices" with no global clock; the gradient/diffusion-wave primitive is pewpew's robust alternative to literal CA rules for neighbor-propagated waves.

### [S916] Wertheimer / Korte — apparent motion (beta movement) timing
- type: article
- url: https://en.wikipedia.org/wiki/Korte%27s_third_law_of_apparent_motion
- author: Max Wertheimer (1912); Adolf Korte (1915); summarized via secondary references
- published: 1912/1915 (historical); accessed via encyclopedic summary 2026-07-09
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251205094841/https://en.wikipedia.org/wiki/Korte%27s_third_law_of_apparent_motion
- relevance: bounds the perceptual window for smooth apparent motion between discrete lights (~30–400 ms inter-element interval, optimal ~60 ms) — the basis for the claim that 10 Hz (100 ms/step) inter-group wave propagation reads as coherent motion. Primary-source figures flagged where derived from secondary summaries.

### [S917] Maróti, Kusy, Simon & Lédeczi — The Flooding Time Synchronization Protocol (FTSP)
- type: article
- url: https://www.math.u-szeged.hu/tagok/mmaroti/okt/2009o/ftsp.pdf
- author: Miklós Maróti, Branislav Kusy, Gyula Simon, Ákos Lédeczi
- published: 2004 (ACM SenSys '04)
- accessed: 2026-07-09
- archive: pending
- relevance: canonical flooding time-sync with MAC-layer timestamping + skew estimation; ~1.48 µs single-hop, ~1 µs average per-hop, robust to node/link failure — the reference for "cheap flooding absolute clock", and the illustration of why ESP-NOW (no app-level MAC TX timestamp) cannot reach µs-class this way.

### [S918] u-blox — Precision Timing / 1PPS accuracy specifications
- type: docs
- url: https://content.u-blox.com/sites/default/files/products/documents/Timing_AppNote_(GPS.G6-X-11007).pdf
- author: u-blox AG
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260320101858/https://content.u-blox.com/sites/default/files/products/documents/Timing_AppNote_%28GPS.G6-X-11007%29.pdf
- relevance: GPS/PPS timing spec — timing modules deliver ~15–30 ns RMS 1PPS, giving every equipped node a drift-free fleet-wide absolute second boundary with zero radio coordination; the cheapest route to sub-µs absolute time outdoors at art scale.

## Block S950–S999 — RA-16 ESP32-S3 render+radio coexistence

### [S950] ESP-IDF Programming Guide — Remote Control Transceiver (RMT), ESP32-S3, stable
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/rmt.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: IDF 5/6 RMT driver on S3: `with_dma` TX flag exists on S3; official mitigation list for interrupt-latency transmission glitches (increase mem_block_symbols in steps of 48, IRAM_ATTR encoder, enable DMA, install driver on a core away from WiFi/BT)

### [S951] FastLED issue #2082 — "Feature Request: Improved RMT5 to resist WIFI flickering"
- type: forum
- url: https://github.com/FastLED/FastLED/issues/2082
- author: zackees (FastLED maintainer)
- published: 2025-09-16
- accessed: 2026-07-09
- relevance: engineering analysis of why the IDF5 RMT driver (via led_strip) is more WiFi-jitter-sensitive than FastLED's RMT4 ping-pong refill; measured 40–50 µs ISR jitter under light WiFi vs ~35 µs refill deadline; driver interrupt priority capped at level 3

### [S952] FastLED — ESP32 platform README (driver matrix)
- type: docs
- url: https://github.com/FastLED/FastLED/blob/master/src/platforms/esp/32/README.md
- pinned: FastLED/FastLED@b424d5b687b62b4819561fe8a6b0196e771fa7bb
- author: FastLED project
- license: MIT
- accessed: 2026-07-09
- relevance: authoritative matrix of FastLED's ESP32 drivers: RMT4 vs RMT5 defaults (RMT5 on IDF≥5), I2S parallel (ESP32/S2/S3, up to 24 lanes, shared timing), multi-lane SPI DMA for APA102/SK9822/HD107S, per-driver WiFi-flicker notes and build flags

### [S953] NeoPixelBus wiki — ESP32 NeoMethods
- type: docs
- url: https://github.com/Makuna/NeoPixelBus/wiki/ESP32-NeoMethods
- author: Michael C. Miller (Makuna)
- accessed: 2026-07-09
- relevance: per-variant driver methods: RMT channel counts (ESP32 8, S2/S3 4, C3 2), I2S single/X8/X16 on classic ESP32, "ESP32S3/ESP32C3 ... do not support I2S at this time; RMT method is used by default"; RMT needs a hardware-read buffer equal to the pixel buffer, I2S needs 4x

### [S954] NeoPixelBus (repository)
- type: code
- url: https://github.com/Makuna/NeoPixelBus
- pinned: Makuna/NeoPixelBus@882b804205f537b12788978c1abb7cd50fefffd4
- author: Michael C. Miller (Makuna)
- license: LGPL-3.0
- accessed: 2026-07-09
- relevance: S3 methods in tree: `NeoEsp32LcdXMethod.h` (LCD_CAM+GDMA x8 parallel, S3-only, 3-step cadence), `DotStarEsp32DmaSpiMethod.h` (SPI-DMA clocked chips), RMT and I2sX methods; latest release 2.8.4 (2025-05-02), master last commit 2026-02-16

### [S955] WLED PR #4484 — WWA support & parallel I2S/LCD for S2/S3 (4→12 outputs)
- type: forum
- url: https://github.com/wled/WLED/pull/4484
- author: blazoncek
- published: 2025-02-13 (merged)
- accessed: 2026-07-09
- relevance: WLED raises ESP32-S3 from 4 (RMT) to 12 outputs by adding parallel LCD/I2S output; backported to 0.15.1 (2025-02-22); production evidence that S3 DMA-parallel output works under WLED's normal WiFi load

### [S956] WLED issue #5266 — "Make I2S optional and use RMT by default"
- type: forum
- url: https://github.com/wled/WLED/issues/5266
- accessed: 2026-07-09
- relevance: documents WLED 0.15's switch to I2S-first bus allocation and resulting flicker reports; on S3 "the LCD driver has the exact same timings as I2S"; RMT T0H ~320–400 ns vs I2S 3-step ~417 ns — timing-marginal strips flicker on the DMA drivers, motivating per-chip driver choice

### [S957] ESP-IDF Programming Guide — Speed Optimization (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/performance/speed.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: built-in task priorities: WiFi driver task priority 23 pinned to core 0 by default, lwIP 18 unpinned, app_main priority 1 on core 0; advice to place latency-sensitive interrupts/tasks on core 1; non-yielding tasks starve lower-priority tasks and trip the task watchdog

### [S958] arduino-esp32 releases (espressif/arduino-esp32)
- type: docs
- url: https://github.com/espressif/arduino-esp32/releases
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Arduino core ↔ IDF mapping and cadence: 3.0.0 = IDF 5.1.4 (2024-05-27), 3.1.0 = IDF 5.3.2 (2024-12-16), 3.2.0 = IDF 5.4.1 (2025-03-28), 3.3.0 = IDF 5.5.0 (2025-07-23), 3.3.10 = IDF 5.5.4 (2026-06-05, latest)

### [S959] arduino-esp32 discussion #10039 — "Community Platformio support for Arduino core 3.x.x"
- type: forum
- url: https://github.com/espressif/arduino-esp32/discussions/10039
- author: Jason2866 et al.
- accessed: 2026-07-09
- relevance: records that PlatformIO declined official Arduino-core-3.x support (platform-espressif32 #1225) and that the pioarduino fork was created (2024) to carry Arduino 3.x on PlatformIO

### [S960] pioarduino/platform-espressif32 releases
- type: code
- url: https://github.com/pioarduino/platform-espressif32/releases
- author: pioarduino (Jason2866 et al.)
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: fork actively tracking Arduino cores: release 55.03.39 (2026-06-04) ships Arduino 3.3.9 / IDF 5.5.4 — days behind upstream Arduino releases

### [S961] platformio/platform-espressif32 releases (official)
- type: code
- url: https://github.com/platformio/platform-espressif32/releases
- author: PlatformIO
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: official platform still actively updated for **ESP-IDF** (v7.0.1, 2026-05-12, adds IDF 6.0.1) but ships no Arduino 3.x framework — Arduino-on-PlatformIO requires the pioarduino fork

### [S962] ESP-IDF Programming Guide — Support for External RAM (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/external-ram.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: PSRAM constraints for hot paths: DMA descriptors cannot live in PSRAM, DMA bandwidth to external RAM is very limited (worse under concurrent core access), PSRAM inaccessible while flash cache is disabled (flash writes/OTA), internal-memory pool reserved for DMA allocations

### [S963] ESP-FAQ — Remote Control Transceiver (RMT) peripheral
- type: docs
- url: https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/peripherals/rmt.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Espressif's own answer to "RMT + WS2812 + WiFi/BT = data frame exceptions": raise mem blocks, pin RMT interrupt away from WiFi core, switch to SPI-DMA, or "ESP32-S3 is recommended because it is currently the only chip with RMT DMA support. This ensures RMT is not interfered by interrupts caused by Wi-Fi, Bluetooth, and other peripherals."

### [S964] espressif/led_strip component (ESP Component Registry, v3.0.3)
- type: docs
- url: https://components.espressif.com/components/espressif/led_strip/
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: official led_strip driver docs: without DMA "the driver will going into interrupt very frequently, thus result in a high CPU usage"; if a WiFi interrupt lands on the same core "the RMT transaction will be corrupted and the LEDs will display incorrect colors"; "you'd better to enable the DMA feature if possible"; SPI backend exists but monopolizes the SPI bus (no chip select)

### [S965] idf-extra-components issue #466 — led_strip DMA broken on some ESP32-S3 boards
- type: forum
- url: https://github.com/espressif/idf-extra-components/issues/466
- accessed: 2026-07-09
- relevance: open bug report (2025) that led_strip with RMT DMA fails on the Xiao ESP32-S3 variant and possibly others — RMT-DMA on S3 is the right architecture but not yet friction-free in practice

### [S966] FastLED issue #2156 — RMT DMA mem_block_symbols validation on ESP32-S3
- type: forum
- url: https://github.com/FastLED/FastLED/issues/2156
- accessed: 2026-07-09
- relevance: FastLED's computed DMA mem_block_symbols failed ESP-IDF validation on S3; fixed value of 1024 lets the DMA channel be created — documents current-day rough edges of the S3 RMT-DMA path

### [S967] ESP32-S3 Series Datasheet (Espressif, v2.x)
- type: datasheet
- url: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: dual Xtensa LX7 up to 240 MHz, single-precision FPU, 512 KB internal SRAM, Processor Instruction Extensions (PIE) with 128-bit SIMD (8/16/32-bit vector ops), 4× RMT TX + 4× RX channels, LCD interface, GDMA

### [S968] Espressif Developer Portal — "Explore the PIE capabilities" (PIE/SIMD introduction)
- type: article
- url: https://developer.espressif.com/blog/2024/12/pie-introduction/
- author: Espressif Systems
- published: 2024-12
- accessed: 2026-07-09
- relevance: programmer's view of the PIE SIMD extension shared by S3/P4: 8×128-bit q registers, vector MAC — the acceleration path esp-dsp uses; relevant to fixed-point 16-bit pixel math

### [S969] espressif/esp-dsp (repository)
- type: code
- url: https://github.com/espressif/esp-dsp
- pinned: espressif/esp-dsp@3c8ac0fdfec83740b783e200862c8d0c056de0ad
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: official DSP library with assembly-optimized (PIE/SIMD) dot products, matrix math, FFT for S3; active (last commit 2026-05-11); the ready-made route to vectorized 16-bit pixel arithmetic

### [S970] hpwit/I2SClockLessLedDriveresp32s3 (Yves's S3 I2S/LCD parallel driver)
- type: code
- url: https://github.com/hpwit/I2SClockLessLedDriveresp32s3
- pinned: hpwit/I2SClockLessLedDriveresp32s3@48e9cb6d3db0e902703b0325bfaa153074f071d8
- author: Yves Bazin (hpwit)
- license: none declared (no LICENSE file at pin)
- accessed: 2026-07-09
- relevance: the S3 parallel driver FastLED vendored in 3.9.9 (third_party/yves): 16-way parallel via LCD/I2S DMA; README requires PSRAM ("buffers are declared in PSRAM"); last commit 2024-11-15 — upstream dormant, FastLED maintains its vendored copy

### [S971] FastLED issue #1609 — inefficient SPI transmission for APA102/SK9822 on ESP32
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1609
- accessed: 2026-07-09
- relevance: measured 30-px APA102 update = ~422 µs at 5 MHz and ~244 µs at 20 MHz with ~1.7 µs gaps between bytes — FastLED's ESP32 SPI path wastes most of the clock headroom; issue still open (stale) — clocked-chip refresh ceilings are driver-bound, not protocol-bound

### [S972] ESP-IDF Programming Guide — Watchdogs (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/wdts.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: task watchdog (TWDT) subscribes both CPUs' idle tasks by default (CONFIG_ESP_TASK_WDT_CHECK_IDLE_TASK_CPU0/CPU1); a never-yielding render loop pinned to core 1 starves idle1 and trips the TWDT — loops must block (DMA-done, queue) or idle1 must be unsubscribed

### [S973] esp-idf (repository — RMT TX driver source)
- type: code
- url: https://github.com/espressif/esp-idf
- pinned: espressif/esp-idf@f0887bcf8763266effe3fa0b358340df226a04b5
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: driver-source ground truth: rmt_tx.c "Only the last channel has the DMA capability" — exactly ONE RMT TX channel per group can use DMA on S3; DMA mode forces mem_block_num=1 and requires GDMA IRAM options for cache-safe ISR

### [S974] arduino-esp32 (repository — default partition table)
- type: code
- url: https://github.com/espressif/arduino-esp32
- pinned: espressif/arduino-esp32@b1208ef0293c363dd93fa2aa704fc05791433317
- author: Espressif Systems
- license: LGPL-2.1
- accessed: 2026-07-09
- relevance: tools/partitions/default.csv: stock 4 MB layout = 2 OTA app slots of 0x140000 (1.25 MiB) each + 1.4 MiB SPIFFS — the size box a dual-partition OTA receiver firmware must fit on 4 MB flash

### [S975] FastLED issue #1835 — RMT5 issues on ESP32 and ESP32-S3
- type: forum
- url: https://github.com/FastLED/FastLED/issues/1835
- published: 2025-01-08
- accessed: 2026-07-09
- relevance: measured that RMT5 pins do not transmit in parallel (per-pin time grows linearly) and single-pin S3 show() was slower than classic ESP32 (378 µs vs 238 µs) in early 3.9.x — RMT5 growing pains; closed since

### [S976] arduino-esp32 docs — Arduino as an ESP-IDF component
- type: docs
- url: https://docs.espressif.com/projects/arduino-esp32/en/latest/esp-idf_component.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: official path to mix stacks: "You can use the Arduino framework as an ESP-IDF component ... with the full flexibility of the ESP-IDF"; page states Arduino core 3.3.10 is compatible with ESP-IDF v5.5 — lets a pewpew receiver use IDF task/peripheral control plus Arduino-ecosystem LED libraries

## Block S1000–S1049 — RA-17 Fleet ops & mesh gateway

### [S1000] ESP-FAQ — ESP-NOW application solution page
- type: docs
- url: https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260319154338/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html
- relevance: Official FAQ stating the gateway-critical constraints: ESP-NOW channel must equal the connected AP's channel, no channel switching after WiFi connect, modem-sleep breaks ESP-NOW receive, connectionless-power-save wake-interval APIs, peer-count limits under coexistence.

### [S1001] espressif/esp-now — application-layer ESP-NOW component (pairing, control, provisioning, OTA, debug, security)
- type: code
- url: https://github.com/espressif/esp-now
- pinned: espressif/esp-now@4432294ef6a6cb274b441c0678414455a4055cff
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: Espressif's first-party ESP-NOW application component. Its get-started example is a UART↔ESP-NOW-broadcast bridge (the serial-dongle gateway pattern); its OTA feature claims "50 devices can be upgraded in 3 minutes" over ESP-NOW with resume; provisioning claims "16 devices can be configured in 5 seconds". 766 stars, last push 2026-02-04.

### [S1002] esp-idf issue #10341 — "ESP-NOW does not working with WiFi (STA) mode"
- type: forum
- url: https://github.com/espressif/esp-idf/issues/10341
- author: rajneeshsinha et al.; Espressif staff Xiehanxin, zhangyanjiaoesp
- published: 2022-12
- accessed: 2026-07-09
- archive: pending
- relevance: Documented ESP-NOW+STA coexistence pitfalls: broken before IDF 5.0 (staff: "this issue is fixed in IDF 5.0 and later version"; workaround on 4.x: init ESP-NOW before AP connect); staff claim that a STA-connected node "will only receive the broadcast packet whose bssid is equal to the associated AP bssid" (disputed in-thread by reporter).

### [S1003] ESP-IDF Programming Guide — Over The Air Updates (OTA), ESP32-S3, latest/v5.x
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/ota.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260312072212/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/ota.html
- relevance: Authoritative OTA model: two OTA app slots (ota_0/ota_1) + otadata partition; app rollback via esp_ota_mark_app_valid_cancel_rollback()/ESP_OTA_IMG_PENDING_VERIFY with automatic rollback on unconfirmed reboot; eFuse anti-rollback ("the version in the bootable firmware must be greater than or equal to the version in the chip"); signed OTA images verifiable "even without enabling hardware secure boot" (CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT).

### [S1004] ESP-IDF Programming Guide — Wi-Fi performance and power save
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi-driver/wifi-performance-and-power-save.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Default power-save is WIFI_PS_MIN_MODEM (wake at DTIM); "Disabling it increases power consumption, but minimizes the delay in receiving Wi-Fi data in real time" (WIFI_PS_NONE); ESP-NOW-at-STA sleep support and esp_wifi_set_connectionless_interval(); lab UDP throughput 75–85 Mbit/s. Grounds the gateway's WiFi-hop latency behavior.

### [S1005] espressif/esp-mesh-lite — mesh solution with root-distributed OTA
- type: code
- url: https://github.com/espressif/esp-mesh-lite
- pinned: espressif/esp-mesh-lite@da20046fb3b0421881b0143d4dc130915d3bc952
- author: Espressif Systems
- license: Apache-2.0 (components/mesh_lite/license.txt; no repo-level license auto-detected by GitHub)
- accessed: 2026-07-09
- relevance: Espressif's supported WiFi-mesh with in-mesh OTA: root node downloads firmware then disseminates to child nodes; OTA tuning knobs (CONFIG_OTA_DATA_LEN vs RAM, max node number, max level vs latency) illustrate the configuration complexity mesh OTA brings. 207 stars, last push 2025-09-30.

### [S1006] painlessMesh work item #387 — "OTA API lacking feedback features"
- type: forum
- url: https://gitlab.com/painlessMesh/painlessMesh/-/work_items/387
- author: painlessMesh users/maintainers
- accessed: 2026-07-09
- archive: pending
- relevance: Documented mesh-OTA pain: the OTA API "does not allow tracking of the OTA update process across the network", nodes are rebooted "without any chance for the gateway to know what is going on", and per-node chunk requests "can in some cases create a lot of additional network traffic". Direct evidence for avoiding gossiped OTA.

### [S1007] painlessMesh — self-forming ESP mesh (GitLab upstream)
- type: code
- url: https://gitlab.com/painlessMesh/painlessMesh
- pinned: painlessMesh/painlessMesh@1b2a02be2603b8a3e418338811326a81642bd46f (develop, committed 2025-10-01)
- author: painlessMesh contributors
- license: GPL-3.0-only (GitLab-detected)
- accessed: 2026-07-09
- relevance: The canonical hobby ESP mesh with built-in OTA plugin (ota::Announce/DataRequest/Data chunk protocol). Maintenance: last repository activity 2026-06-14, last code commit on develop 2025-10-01, 271 GitLab stars — low-intensity maintenance.

### [S1008] ESPHome — ESP-NOW component documentation
- type: docs
- url: https://esphome.io/components/espnow/
- author: ESPHome (Open Home Foundation)
- accessed: 2026-07-09
- relevance: ESPHome's first-party ESP-NOW support (unicast/broadcast, auto_add_peer, on_broadcast triggers). States the gateway constraint plainly: channel "Cannot be set when Wi-Fi is used, as ESP-NOW will use the same channel as the Wi-Fi network"; notes 250 B payload cap and unacknowledged broadcast.

### [S1009] ESP-IDF Programming Guide — USB Serial/JTAG Controller Console (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/usb-serial-jtag-console.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: Behavior of the S3's built-in USB CDC vs an external USB-UART bridge: host-side flow control ("many PC Terminals wait for the ESP32-S3 to ingest the bytes"), 50 ms one-time wait when no terminal drains the TX buffer, dies in light/deep sleep, device disappears if pins are reconfigured. Grounds serial-dongle gateway design constraints.

### [S1010] ESP-IDF Programming Guide — Non-Volatile Storage (NVS) library (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260213110244/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html
- relevance: Key-value config store in its own flash partition: namespaces, power-fail safety ("one should be able to power off the device at any point"), built-in wear levelling, optional NVS encryption. Basis for config-vs-firmware separation.

### [S1011] ESP-IDF Programming Guide — Miscellaneous System APIs: MAC addresses (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260303122027/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html
- relevance: Base MAC is "pre-programmed into the ESP32-S3 eFuse in the factory during production"; esp_read_mac()/esp_efuse_mac_get_default(); per-interface MACs derived from base MAC; custom base MAC possible via esp_base_mac_addr_set(). Basis for zero-touch MAC-derived node identity.

### [S1012] Random Nerd Tutorials — "ESP32: ESP-NOW Web Server Sensor Dashboard (ESP-NOW + Wi-Fi)"
- type: article
- url: https://randomnerdtutorials.com/esp32-esp-now-wi-fi-web-server/
- author: Rui Santos / Random Nerd Tutorials
- accessed: 2026-07-09
- archive: pending
- relevance: The widely-cited single-chip gateway recipe: receiver in WIFI_AP_STA runs ESP-NOW + web server; "The ESP32 sender boards must use the same Wi-Fi channel of the receiver board"; senders scan for the gateway's SSID channel and apply it with esp_wifi_set_channel(). Documents the channel-pinning pattern and its ordering pitfall (connect WiFi before registering peers).

### [S1013] ESP-IDF Programming Guide — App Image Format / esp_app_desc_t (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/app_image_format.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260513185641/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/app_image_format.html
- relevance: Every app image embeds esp_app_desc_t (version string ≤32 chars, project name, compile date/time, IDF version, ELF SHA-256) at a fixed offset, readable via esp_app_get_description(); "useful for identification of images uploaded via Over-the-Air (OTA) updates". Basis for version self-reporting telemetry.

### [S1014] ESPHome 2025.11.0 changelog — ESP-NOW packet transport
- type: docs
- url: https://esphome.io/changelog/2025.11.0/
- author: ESPHome (Open Home Foundation)
- published: 2025-11
- accessed: 2026-07-09
- relevance: "ESP-NOW now available as transport platform for packet_transport component, enabling direct ESP32-to-ESP32 wireless sensor data transmission"; ESP-NOW RX/TX-completion event processing moved to a ~12 µs in-ISR-adjacent path. Dates ESPHome's ESP-NOW investment (component landed 2025.8, transport 2025.11).

### [S1015] Home Assistant — ZHA integration documentation
- type: docs
- url: https://www.home-assistant.io/integrations/zha/
- author: Home Assistant / Open Home Foundation
- accessed: 2026-07-09
- archive: pending
- relevance: The serial-attached radio-coordinator convention pewpew's dongle gateway mirrors: "A hardware radio adapter (typically a USB dongle) that plugs directly into the same computer" — host software speaks a serial protocol to a dedicated radio SoC (EmberZNet EZSP, TI Z-Stack ZNP, deCONZ, XBee families).

## Block S1050–S1099 — RA-18 Wearable bridging

### [S1050] Novel Bits — "Maximum Data Size in a Bluetooth LE Advertising Packet"
- type: article
- url: https://novelbits.io/maximum-data-bluetooth-advertising-packet-ble/
- author: Novel Bits (Mohammad Afaneh)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251006021903/https://novelbits.io/maximum-data-bluetooth-advertising-packet-ble/
- relevance: payload math for legacy (31 B AD, 29 B after LTV overhead, 27 B custom via Manufacturer Specific Data) and extended advertising (254 B per AUX PDU, 250 B custom via MSD); notes extended advertising is optional and not universally supported by scanners

### [S1051] Nordic DevZone — "reducing power consumption during BLE scan"
- type: forum
- url: https://devzone.nordicsemi.com/f/nordic-q-a/57352/reducing-power-consumption-during-ble-scan
- author: Nordic Semiconductor support (Simon R.)
- accessed: 2026-07-09
- archive: pending
- relevance: Nordic engineer confirms continuous-scanning RX current on nRF52 is ~6.5 mA with DCDC enabled (~10 mA without); duty-cycling scan window/interval is the only lever — "the radio does consume quite a bit of power when it is running"

### [S1052] nRF52840 Product Specification — Radio current consumption (RADIO chapter)
- type: datasheet
- url: https://docs.nordicsemi.com/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/current/parameters.i_radio.html
- author: Nordic Semiconductor
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260510231003/https://docs.nordicsemi.com/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/CURRENT/parameters.i_radio.html
- relevance: official radio currents — IRADIO_RX0 (RX @1 Mbps BLE, HFXO, DCDC) = 6.26 mA typ; IRADIO_TX1 (0 dBm, DCDC) = 6.40 mA typ; anchors the observer-role duty-cycle power math

### [S1053] ESP-IDF Programming Guide — RF Coexistence (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/coexist.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260228151623/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/coexist.html
- relevance: S3 has one 2.4 GHz RF module time-sliced between WiFi and BLE; coexistence table marks WiFi-STA + BLE advertising stable ("Y") but ESP-NOW RX only "supported and the performance is stable in STA mode, otherwise not supported"; SoftAP + BLE marked unstable ("C1") — decides the bridge's WiFi mode

### [S1054] ESP-IDF Programming Guide — ESP-NOW API reference (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_now.html
- author: Espressif
- accessed: 2026-07-09
- archive: pending
- relevance: ESP-NOW v1 250 B / v2 1470 B payloads; connectionless power save via esp_now_set_wake_window() + esp_wifi_connectionless_module_set_wake_interval(); "Sleep is supported only when ESP32-S3 is configured as station"

### [S1055] CircuitPython core docs — `_bleio` shared bindings
- type: docs
- url: https://docs.circuitpython.org/en/latest/shared-bindings/_bleio/index.html
- author: Adafruit / CircuitPython project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260527030025/https://docs.circuitpython.org/en/latest/shared-bindings/_bleio/index.html
- relevance: `Adapter.start_scan(prefixes, *, buffer_size=512, extended=False, timeout=None, interval=0.1, window=0.1, minimum_rssi=-80, active=True)` — observer role with hardware prefix filtering and a scan window/interval duty-cycle lever (interval 0.0025–40.96 s, window ≤ interval); passive scanning via active=False

### [S1056] adafruit/Adafruit_CircuitPython_BLE
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_BLE
- pinned: adafruit/Adafruit_CircuitPython_BLE@82ada04a0f4019de00d103256621f73b80151a0d
- author: Adafruit
- license: MIT
- accessed: 2026-07-09
- relevance: the high-level BLE library over _bleio (BLERadio.start_scan yields Advertisement objects incl. ManufacturerData); actively maintained — release 10.1.3 on 2026-04-23

### [S1057] Nordic DevZone — "Nature of pseudo-random delay advDelay (0–10 ms) added to the advertising interval"
- type: forum
- url: https://devzone.nordicsemi.com/f/nordic-q-a/85629/nature-of-pseudo-random-delay-advdelay-0-10-ms-added-to-the-advertising-interval
- author: Nordic Semiconductor support
- accessed: 2026-07-09
- archive: pending
- relevance: per Core spec, T_advEvent = advInterval + advDelay with advDelay pseudo-random 0–10 ms per event, generated by the link layer and not modifiable — the floor on BLE-advertising timing jitter

### [S1058] ESP-IDF Programming Guide — Introduction to Low Power Mode in Wi-Fi Scenarios (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-wifi.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260319185803/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-wifi.html
- relevance: measured (shielded-box) modem-sleep averages on ESP32-S3: ~19.5–20.7 mA with DFS on (DTIM 10–1), ~38–40 mA without DFS, peaks ~113 mA during radio activity — the realistic floor for any duty-cycled WiFi/ESP-NOW receiver on S3

### [S1059] Nordic DevZone — "nRF52 DK — 20 ms non connectable advertising interval"
- type: forum
- url: https://devzone.nordicsemi.com/f/nordic-q-a/15372/nrf52-dk---20ms-non-connectable-advertising-interval
- author: Nordic Semiconductor support / community
- accessed: 2026-07-09
- archive: pending
- relevance: BT 4.x mandated "the advInterval shall not be less than 100 ms" for non-connectable advertising, enforced by the SoftDevice; the Bluetooth 5.0 spec (Vol 6, Part B, 4.4.2.2.1) removed the restriction, allowing 20 ms non-connectable intervals

### [S1060] adafruit/Adafruit_CircuitPython_BLE_BroadcastNet
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_BLE_BroadcastNet
- pinned: adafruit/Adafruit_CircuitPython_BLE_BroadcastNet@020fa28503b3580bd7bb3a37c7cc416eea35d286
- author: Adafruit
- license: MIT
- accessed: 2026-07-09
- relevance: official Adafruit library implementing exactly pewpew's wearable pattern in reverse: compact fixed-layout sensor state packed into Manufacturer Specific Data and broadcast connectionlessly ("think of this system as 'broadcasting' in the truest sense of the word"); template for the group-state advertisement format

### [S1061] Adafruit Learn — "Bluetooth LE Sensor Nodes to Raspberry Pi WiFi Bridge"
- type: docs
- url: https://learn.adafruit.com/bluetooth-le-broadcastnet-sensor-node-raspberry-pi-wifi-bridge
- author: Adafruit
- accessed: 2026-07-09
- relevance: official worked example of a BLE-advertisement↔WiFi bridge node plus connectionless CircuitPython broadcasters — the mirror image of pewpew's ESP-NOW→BLE bridge, proving the pattern at the ecosystem level

### [S1062] adafruit/circuitpython issue #3119 — "BLE start_scan dies with MemoryError"
- type: forum
- url: https://github.com/adafruit/circuitpython/issues/3119
- author: CircuitPython community (reported 2020-07-04, closed 2023-10-28)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251121042516/https://github.com/adafruit/circuitpython/issues/3119
- relevance: historical evidence that unfiltered long-running scans put large allocations (64 KB-class) on the CircuitPython heap; motivates prefix-filtered, bounded-buffer, short-burst scanning in a render loop

### [S1063] Nordic Semiconductor — Enhanced ShockBurst (ESB), nRF Connect SDK protocol docs
- type: docs
- url: https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/esb/index.html
- author: Nordic Semiconductor
- accessed: 2026-07-09
- archive: pending
- relevance: ESB is Nordic-proprietary 2.4 GHz (interop limited to nRF5/nRF52/nRF53/nRF24 devices), delivered as an nRF Connect SDK library requiring exclusive radio-resource access — no ESP32 interop and no CircuitPython exposure; disqualifies it as pewpew's wearable link

### [S1064] The Things Network docs — "Duty Cycle" (EU868 regulatory limits)
- type: docs
- url: https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/
- author: The Things Network
- accessed: 2026-07-09
- archive: pending
- relevance: EU 868 MHz ISM band imposes ~1% transmit duty cycle (864 s airtime/day) on LoRa devices — a continuous ~10 Hz state broadcast is regulatorily impossible; kills LoRa for group-state distribution

### [S1065] ESP-IDF Programming Guide — RF Coexistence (ESP32-C6)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-guides/coexist.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260410144209/https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-guides/coexist.html
- relevance: ESP32-C6 likewise has a single time-sliced 2.4 GHz RF module (WiFi/BLE/802.15.4); same coexistence matrix shape as S3 (STA+BLE-adv "Y", ESP-NOW RX stable only in STA mode) — C6 offers no coexistence advantage over S3 for the bridge role

### [S1066] Adafruit Learn — "Circuit Playground Bluefruit NeoPixel Animation and Color Remote Control"
- type: docs
- url: https://learn.adafruit.com/circuit-playground-bluefruit-neopixel-animation-and-color-remote-control
- author: Adafruit (published 2019-12-16, still current in Learn system)
- accessed: 2026-07-09
- relevance: official guide running CircuitPython BLE radio activity concurrently with NeoPixel animation on nRF52840-class boards — ecosystem existence proof for radio+render, albeit at low pixel counts, not a 60 fps benchmark

## Block S1100–S1149 — RA-19 Embedded test loops (sim/emulation/HIL)

### [S1100] Wokwi docs — ESP32 Simulation guide (chips + peripheral table)
- type: docs
- url: https://docs.wokwi.com/guides/esp32
- author: Wokwi (CodeMagic LTD)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710040009/https://docs.wokwi.com/guides/esp32
- relevance: authoritative peripheral matrix — S3 sim covers GPIO/SPI/ADC/LEDC/USB-CDC + WiFi, RMT partial "transmit-only, use to control WS2812 LED strips", I2S and BLE not implemented; default simulated CPU clock capped (~8 MHz equiv, `cpuFrequency` attr) so timing is not real-time

### [S1101] Wokwi docs — ESP32 WiFi Networking guide
- type: docs
- url: https://docs.wokwi.com/guides/esp32-wifi
- author: Wokwi (CodeMagic LTD)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260620122714/https://docs.wokwi.com/guides/esp32-wifi
- relevance: WiFi simulated "from the 802.11 MAC layer" via virtual open AP "Wokwi-GUEST" (BSSID 42:13:37:55:aa:01, ch 6) + IoT gateway carrying TCP and UDP (no ICMP) — enough for DDP-over-UDP receiver testing, STA/infrastructure mode only

### [S1102] Wokwi docs — Wokwi for CI, getting started
- type: docs
- url: https://docs.wokwi.com/wokwi-ci/getting-started
- author: Wokwi (CodeMagic LTD)
- accessed: 2026-07-09
- relevance: wokwi-cli uploads firmware to Wokwi's cloud, streams serial back; scenario YAML (expect-serial, set controls, timeouts); GitHub Actions/GitLab CI integrations; WOKWI_CLI_TOKEN auth; experimental MCP server for AI agents; CI minutes plan-gated (Free 50/mo, Hobby 200, Pro 2000)

### [S1103] Wokwi pricing page
- type: product
- url: https://wokwi.com/pricing
- author: Wokwi (CodeMagic LTD)
- accessed: 2026-07-09
- relevance: 2026 tiers — Free (unlimited public sims), Hobby $5.6/mo, Hobby+ $8.1/mo, Pro $20/seat/mo with 2000 CI min/mo; quantifies the cost of leaning on Wokwi CI

### [S1104] wokwi/wokwi-cli
- type: code
- url: https://github.com/wokwi/wokwi-cli
- pinned: wokwi/wokwi-cli@7a208779ef6579463626a24f898ab08495ee247e
- author: Wokwi (Uri Shaked et al.)
- license: MIT
- published: latest release v0.26.1, 2026-02-23
- accessed: 2026-07-09
- relevance: the CI client — MIT and active (pushed 2026-06), but it is a thin client; the ESP32 simulation engine itself has no public source repo and runs in Wokwi's cloud

### [S1105] ESP-IDF Programming Guide — QEMU Emulator (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/tools/qemu.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260214045143/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/tools/qemu.html
- relevance: QEMU is a first-class IDF tool — `idf.py qemu monitor` / `idf.py qemu gdb`, prebuilt binaries for Linux/macOS/Windows; S3 emulation of "CPU, memory, and several peripherals"; virtual framebuffer, eFuse/secure-boot emulation

### [S1106] espressif/esp-toolchain-docs — QEMU README (chip/peripheral coverage)
- type: docs
- url: https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md
- author: Espressif
- accessed: 2026-07-09
- archive: pending
- relevance: definitive coverage table — chips ESP32/S3/C3; WiFi NOT emulated on any ("The Ethernet controller can be used for networking instead"); also missing: Bluetooth, USB, RMT, GP-SPI, I2C, I2S, ULP, GPIO matrix; "Espressif does not provide support for QEMU"

### [S1107] espressif/qemu
- type: code
- url: https://github.com/espressif/qemu
- pinned: espressif/qemu@febae182e132e4055529be423a818225ebddaa3a
- author: Espressif (QEMU fork)
- license: GPL-2.0 (QEMU base; per-file mix incl. LGPL-2.1)
- published: release esp-develop-9.2.2-20260417, 2026-04-17
- accessed: 2026-07-09
- relevance: the emulator behind `idf.py qemu`; active (pushed 2026-06-09), 334 stars

### [S1108] emb-team/esp-idf-qemu — QEMU WiFi/BLE emulation proof-of-concept
- type: code
- url: https://github.com/emb-team/esp-idf-qemu
- pinned: emb-team/esp-idf-qemu@c2046e152d72abb58b556ee000466b866aaba05c
- author: emb-team
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: the only known WiFi/BLE-in-QEMU attempt for ESP32 — STA/softAP redirected over emulated Ethernet; pinned to IDF v3.2.2, last push 2020-06-11, 8 stars — dead PoC, evidence that radio emulation was tried and abandoned

### [S1109] Renode docs — Bluetooth Low Energy simulation tutorial
- type: docs
- url: https://renode.readthedocs.io/en/latest/tutorials/ble-simulation.html
- author: Antmicro
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251011204153/https://renode.readthedocs.io/en/latest/tutorials/ble-simulation.html
- relevance: shared wireless-medium model (`BLEMedium`), multi-machine radio linking, Python packet-interception hooks; canonical demo = two nRF52840s running Zephyr BLE — Renode's multi-node radio sim is real but nRF-centric

### [S1110] Renode docs — supported boards
- type: docs
- url: https://renode.readthedocs.io/en/latest/introduction/supported-boards.html
- author: Antmicro
- accessed: 2026-07-09
- archive: pending
- relevance: no ESP32/Espressif platform in the supported list; only Xtensa entry is `xtensa-sample-controller` — ESP32-in-Renode would be a platform-porting project, not configuration

### [S1111] renode/renode
- type: code
- url: https://github.com/renode/renode
- pinned: renode/renode@40c62fbd070fa617ee01899433ad5623ab839d59
- author: Antmicro
- license: MIT
- published: latest release v1.16.1, 2026-02-16
- accessed: 2026-07-09
- relevance: very active (pushed 2026-07-09, 2.6k stars); MIT per LICENSE ("distributed under the terms of the MIT license", copyright Antmicro)

### [S1112] Antmicro blog — "Simulating low-power mesh IoT systems in Renode with Silicon Labs Wireless Gecko Series 2"
- type: article
- url: https://antmicro.com/blog/2025/08/silabs-series-2-in-renode
- author: Antmicro
- published: 2025-08
- accessed: 2026-07-09
- relevance: 2025 state of Renode multi-node radio: SiLabs Series 2 2.4 GHz multiprotocol (BLE/Zigbee/Thread/Matter) mesh networks simulated — proves the medium model scales to mesh, and that vendor buy-in (not community patches) is what gets a chip there

### [S1113] wokwi/wokwi-features issue #446 — "ESP-NOW support (direct communication between two ESP chips)"
- type: forum
- url: https://github.com/wokwi/wokwi-features/issues/446
- author: Wokwi community / maintainers
- published: 2022-11-11
- accessed: 2026-07-09
- archive: pending
- relevance: ESP-NOW in Wokwi is an open, "open for vote" feature request since 2022; 2025 duplicate (#1015, incl. multi-MCU projects) closed against it; no implementation as of 2026-07 — the mesh tier cannot be simulated

### [S1114] Wokwi FAQ — AVR8js open-source engine
- type: docs
- url: https://docs.wokwi.com/faq
- author: Wokwi (CodeMagic LTD)
- accessed: 2026-07-09
- relevance: only the AVR8js AVR engine is called out as open source; the ESP32 engine has no public repo — Wokwi's ESP32 simulation is a proprietary cloud dependency

### [S1115] pytest-embedded documentation
- type: docs
- url: https://docs.espressif.com/projects/pytest-embedded/en/latest/
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260701130032/https://docs.espressif.com/projects/pytest-embedded/en/latest/
- relevance: the plugin family — services `serial`/`esp`/`idf`/`qemu`/`wokwi`/`arduino`/`nuttx` behind one `dut.expect()` API; same test body runs on simulator or devkit by swapping `--embedded-services`; per-DUT log capture built in

### [S1116] espressif/pytest-embedded
- type: code
- url: https://github.com/espressif/pytest-embedded
- pinned: espressif/pytest-embedded@eebeb04b19b0a4aba864f09dcb6a831cef86e4a9
- author: Espressif
- license: MIT (repo default; per-package LICENSE files; examples CC0-1.0)
- published: v2.8.1 current on PyPI
- accessed: 2026-07-09
- relevance: active (pushed 2026-06-30, 145 stars); what Espressif itself maintains for on-target + emulator testing

### [S1117] ESP-IDF Programming Guide — "ESP-IDF Tests with Pytest" contributor guide
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/contribute/esp-idf-tests-with-pytest.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260702205830/https://docs.espressif.com/projects/esp-idf/en/latest/esp32/contribute/esp-idf-tests-with-pytest.html
- relevance: how Espressif runs its own hardware CI — pytest-embedded(esp,idf) + pytest-rerunfailures; `target` + `env` markers route tests to CI runners with matching tags; multi-DUT via `count`/`'esp32|esp32s2'` parameterization and per-DUT `app_path`; flake vocabulary `flaky(reruns=3)`, `xfail`, `temp_skip_ci`

### [S1118] ESP-IDF Programming Guide — Unit Testing in ESP32 (Unity on target)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/unit-tests.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710120644/https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/unit-tests.html
- relevance: Unity `TEST_CASE` in component `test/` dirs, central test app with serial menu; `TEST_CASE_MULTIPLE_DEVICES` synchronizes up to 5 DUTs via UART signals — the native shape for two-board radio/protocol tests; `TEST_CASE_MULTIPLE_STAGES` for reset-spanning tests

### [S1119] labgrid-project/labgrid
- type: code
- url: https://github.com/labgrid-project/labgrid
- pinned: labgrid-project/labgrid@0e8d23341a34cb1742059a699f8b71aff31db901
- author: Pengutronix / labgrid project
- license: LGPL-2.1
- published: v26.0, 2026-06-22
- accessed: 2026-07-09
- relevance: the established open-source embedded-lab framework since 2016 — coordinator/exporter/client board farm, power/reset/serial/SD-mux/USB drivers, pytest plugin; active (pushed 2026-07-08, 490 stars); Linux-SBC-flavored but the reference resource-model for a bench

### [S1120] GitHub Docs — About self-hosted runners
- type: docs
- url: https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners
- author: GitHub
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250615070344/https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners
- relevance: self-hosted runners give hardware/OS control and USB access, route via labels, poll GitHub over HTTPS; GitHub recommends them only for private repos (fork PRs can execute arbitrary code on the runner)

### [S1121] Ferrous Systems — "Running hardware-in-the-loop tests on GitHub Actions"
- type: article
- url: https://ferrous-systems.com/blog/gha-hil-tests/
- author: Ferrous Systems
- published: 2021-03-17
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260317053019/https://ferrous-systems.com/blog/gha-hil-tests/
- relevance: canonical HIL-on-GHA writeup — nRF52840-DK on a Pi 4 self-hosted runner, probe-run/defmt-test `cargo test` on target; two-repo public-proxy→private-runner pattern + merge-queue approval to keep untrusted PRs off hardware

### [S1122] The Good Penguin — "Automated Testing with GitHub Actions, pytest and a Board Farm"
- type: article
- url: https://www.thegoodpenguin.co.uk/blog/automated-testing-with-github-actions-pytest-and-a-board-farm/
- author: The Good Penguin (consultancy blog)
- published: 2023-03-17
- accessed: 2026-07-09
- archive: pending
- relevance: working board-farm CI: exclusive board arbitration per runner, USB relays power-cycling around every flash, SD-mux image handoff, pytest+pexpect serial validation, upload-artifact for images/logs

### [S1123] GitHub Docs — Actions usage limits
- type: docs
- url: https://docs.github.com/en/actions/reference/limits
- author: GitHub
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260625171148/https://docs.github.com/en/actions/reference/limits
- relevance: job limits — 6 h GitHub-hosted vs 5 days self-hosted, 35-day workflow runs — which is what makes multi-day soak-as-CI-job feasible on own hardware; artifact storage plan-limited (500 MB Free)

### [S1124] pytest-dev/pytest-rerunfailures
- type: code
- url: https://github.com/pytest-dev/pytest-rerunfailures
- pinned: pytest-dev/pytest-rerunfailures@1087cc27aeb477d179ed244843c2e5428d8a1e28
- author: pytest-dev
- license: MPL-2.0
- published: v16.4 current on PyPI
- accessed: 2026-07-09
- relevance: the retry/flake plugin Espressif's own CI uses (`@pytest.mark.flaky(reruns=3, reruns_delay=5)`); active (pushed 2026-07-01)

### [S1125] sigrok wiki — sigrok-cli
- type: docs
- url: https://sigrok.org/wiki/Sigrok-cli
- author: sigrok project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260623070520/http://sigrok.org/wiki/Sigrok-cli
- relevance: fully headless capture + decode: `--driver fx2lafw --time 3s`, stacked protocol decoders via `-P`, binary/CSV outputs — explicitly aimed at scripts and CI pipelines

### [S1126] sigrokproject/libsigrokdecode
- type: code
- url: https://github.com/sigrokproject/libsigrokdecode
- pinned: sigrokproject/libsigrokdecode@71f451443029322d57376214c330b518efd84f88
- author: sigrok project
- license: GPL-3.0
- accessed: 2026-07-09
- relevance: mainline decoder set includes `decoders/rgb_led_ws281x` (WS281x one-wire → RGB values) and `rgb_led_spi` — LED protocol decode in CI with zero custom code; slow-moving (pushed 2024-10-13) but stable

### [S1127] sigrok wiki — fx2lafw
- type: docs
- url: https://sigrok.org/wiki/Fx2lafw
- author: sigrok project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260704001351/http://sigrok.org/wiki/Fx2lafw
- relevance: open firmware (GPLv2+) for $10–25 Cypress FX2 logic-analyzer clones (Saleae Logic/USBee clones); 24 MHz crystal, 8 probes (PB0–7) or 16 — 24 MS/s is ~30 samples/bit for 800 kHz WS2812, adequate for decode and skew timestamps

### [S1128] Saleae Logic 2 Automation API documentation
- type: docs
- url: https://saleae.github.io/logic2-automation/
- author: Saleae
- accessed: 2026-07-09
- archive: pending
- relevance: official automation: gRPC socket + Python wrapper; start captures, add analyzers, export data; requires the Logic 2 app running (documented headless-on-Linux mode exists)

### [S1129] saleae/logic2-automation
- type: code
- url: https://github.com/saleae/logic2-automation
- pinned: saleae/logic2-automation@ee5e1ceebfb63c285828eb337f597f133f7125e4
- author: Saleae
- license: Apache-2.0
- published: v1.0.2, 2022-10-12
- accessed: 2026-07-09
- relevance: the Python package behind the automation API; maintained (pushed 2026-05-04) though release-quiet since 2022

### [S1130] Saleae — Logic 8 product page
- type: product
- url: https://www.saleae.com/products/logic-8
- author: Saleae
- accessed: 2026-07-09
- archive: pending
- relevance: Logic 8 = 8 digital channels at 100 MS/s + analog recording 10 MS/s/10-bit on the same probes, "Python automation API" first-party — one instrument covers protocol decode AND photodiode digitization; price not published on page

### [S1131] Nordic Semiconductor — Power Profiler Kit II product page
- type: product
- url: https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2
- author: Nordic Semiconductor
- accessed: 2026-07-09
- archive: pending
- relevance: official specs: 200 nA–1 A range, 100 nA resolution, 100 kS/s; SMU mode sources 0.8–5 V up to 1 A (needs two USB cables for full current); ampere-meter mode for external supplies; UI is nRF Connect Power Profiler

### [S1132] IRNAS/ppk2-api-python
- type: code
- url: https://github.com/IRNAS/ppk2-api-python
- pinned: IRNAS/ppk2-api-python@6f5cdcc444643f18182022cb2550928aa92854aa
- author: IRNAS (engineering company)
- license: GPL-2.0
- accessed: 2026-07-09
- relevance: the de-facto Python automation for PPK2 (unofficial — Nordic doesn't document the serial protocol): use_source_meter()/set_source_voltage()/start_measuring()/get_samples(), multiprocessing sampler for the 100 kS/s stream; active (pushed 2026-05-19, 239 stars)

### [S1133] mvp/uhubctl
- type: code
- url: https://github.com/mvp/uhubctl
- pinned: mvp/uhubctl@2985dfcfc3dfb5e574e50d4ec6b2578cdcccc9b0
- author: Vadim Mikhailov
- license: GPL-2.0 (custom LICENSE text, GPLv2 terms; copyright Vadim Mikhailov 2009-2025)
- published: v2.6.0, 2024-08-31
- accessed: 2026-07-09
- relevance: per-port VBUS switching on hubs that truly support USB per-port power switching; README warns most hubs gang ports or never cut VBUS and maintains the verified-hub list (Rosonway RSH-A13/RSH-A37S, Inateck HB2025A among 2026 picks); repo pushed 2026-06-07

### [S1134] ESP-IDF Programming Guide — esp_wifi API (promiscuous mode, ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_wifi.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251207093313/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_wifi.html
- relevance: esp_wifi_set_promiscuous() + esp_wifi_set_promiscuous_filter() deliver management frames (incl. ESP-NOW's action frames) to a callback with wifi_pkt_rx_ctrl_t metadata (RSSI etc.) — a spare ESP32 becomes a channel sniffer with ESP32-radio-eye RSSI

### [S1135] morrownr/USB-WiFi — Linux USB WiFi adapter reference
- type: docs
- url: https://github.com/morrownr/USB-WiFi
- pinned: morrownr/USB-WiFi@8e6997ddaf27b303ee8745b1ce0e9bbde1385aac
- author: morrownr (community-maintained reference; 4.4k stars)
- license: none declared
- accessed: 2026-07-09
- relevance: the widely-cited monitor-mode adapter compatibility list — mainlined chipsets to buy: AR9271 (ath9k_htc, kernel ≥3.2, 2.4 GHz-only) and MT7612U (mt76x2u, kernel ≥4.19, dual-band); pushed 2026-07-07

### [S1136] Scapy documentation — Usage (sniffing, 802.11, pcap)
- type: docs
- url: https://scapy.readthedocs.io/en/latest/usage.html
- author: Scapy project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260624121923/https://scapy.readthedocs.io/en/latest/usage.html
- relevance: `sniff(monitor=True)` on monitor-mode interfaces, Dot11 dissection, BPF filters at OS level, `wrpcap`/`rdpcap` for pcap artifacts — the Python half of the ESP-NOW PDR-counting pipeline

### [S1137] Power Electronic Tips — "How to gauge LED flicker" (+ IEEE 1789-2015 context)
- type: article
- url: https://www.powerelectronictips.com/how-to-gauge-led-flicker-faq/
- author: Power Electronic Tips (WTWH Media engineering site)
- accessed: 2026-07-09
- archive: pending
- relevance: the established low-cost flicker rig — integrated photodiode+transimpedance chip (TSL257 light-to-voltage converter) into a scope; percent flicker (Lmax−Lmin)/(Lmax+Lmin) and flicker index per IEEE 1789-2015 (~8 % limit at 100 Hz); lab gear samples light at up to 200 kHz — sets the ADC bar for pewpew's dither bench (site blocks fetch with 403; claims from search excerpt + cross-search 2026-07-09)

### [S1138] Hypothesis documentation — Stateful testing
- type: docs
- url: https://hypothesis.readthedocs.io/en/latest/stateful.html
- author: Hypothesis project (David R. MacIver et al.)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260518144923/https://hypothesis.readthedocs.io/en/latest/stateful.html
- relevance: RuleBasedStateMachine — @rule methods chained into generated sequences, Bundles pass values between steps, @invariant checked after every step, failures shrink to a minimal reproducible program — the exact shape for gossip/epoch protocol model testing

### [S1139] HypothesisWorks/hypothesis
- type: code
- url: https://github.com/HypothesisWorks/hypothesis
- pinned: HypothesisWorks/hypothesis@8683661fb051b5e541e317c844aa3ad5e907e0dc
- author: Hypothesis project
- license: MPL-2.0
- published: v6.156.4 current on PyPI
- accessed: 2026-07-09
- relevance: the standard Python property-testing library; very active (pushed 2026-07-08, 8.8k stars) — codec round-trip + CRDT-law properties build on it

### [S1140] LLVM documentation — libFuzzer
- type: docs
- url: https://llvm.org/docs/LibFuzzer.html
- author: LLVM project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260707105930/https://llvm.org/docs/LibFuzzer.html
- relevance: in-process coverage-guided fuzzing via -fsanitize=fuzzer; status quote: "The original authors of libFuzzer have stopped active work on it and switched to working on another fuzzing engine, Centipede. LibFuzzer is still fully supported in that important bugs will get fixed" — maintenance-only

### [S1141] AFLplusplus/AFLplusplus
- type: code
- url: https://github.com/AFLplusplus/AFLplusplus
- pinned: AFLplusplus/AFLplusplus@011cd189801830253c66ecd3cd6919ec01b46c34
- author: AFL++ project
- license: AGPL-3.0 (relicensed at v5.00c, 2026-06-03: "AFL++ is now an AGPL 3.0 project"; pre-v5 files that could not be switched remain Apache-2.0)
- published: v5.02c, 2026-06-29
- accessed: 2026-07-09
- relevance: the actively developed general-purpose fuzzer (pushed 2026-07-09, 6.6k stars); AGPL is irrelevant for fuzzing pewpew's own parsers (tool use, no linking) but must be recorded

### [S1142] espressif/esp-protocols — mDNS host unit tests + AFL++ fuzzing harness
- type: code
- url: https://github.com/espressif/esp-protocols/tree/master/components/mdns/tests/host_unit_test
- pinned: espressif/esp-protocols@8f1ecbe6cff5fd9a05498bfa1af3fabf9318e760
- author: Espressif
- license: Apache-2.0 (esp-protocols repo)
- accessed: 2026-07-09
- relevance: Espressif's own host-fuzzing pattern — "builds the mDNS component as a Linux host binary with stubs for ESP-IDF networking"; Unity/CMock tests under ASan/UBSan + "AFL++ harness that feeds random packets into the receive path" — the template for host-fuzzing pewpew's 11-byte frame parser

### [S1143] GitHub Docs — Events that trigger workflows (schedule, workflow_dispatch)
- type: docs
- url: https://docs.github.com/en/actions/reference/events-that-trigger-workflows
- author: GitHub
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250718094418/https://docs.github.com/en/actions/reference/events-that-trigger-workflows
- relevance: `schedule` cron (min 5-minute interval; runs may be delayed or dropped under load; default branch only; auto-disabled after 60 days inactivity on public repos) + `workflow_dispatch` manual runs — the constraints that shape soak-as-background-CI-job design

## Block S1150–S1199 — RA-20 Agentic feedback loops

### [S1150] Claude Code docs — Best practices for Claude Code
- type: docs
- url: https://code.claude.com/docs/en/best-practices
- author: Anthropic
- published: continuously updated; content current as of access (documents 2026-era features: `/goal` conditions, auto permission mode, agent teams, `/code-review` skill)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260709165558/https://code.claude.com/docs/en/best-practices
- relevance: the canonical vendor statement of verification-first agent workflow — "Give Claude a way to verify its work" is the first practice listed; also CLAUDE.md authoring rules, hook/skill/subagent selection, fan-out patterns, adversarial review

### [S1151] Claude Code docs — Hooks reference
- type: docs
- url: https://code.claude.com/docs/en/hooks
- author: Anthropic
- published: continuously updated; describes behavior as of Claude Code v2.1.139+
- accessed: 2026-07-09
- relevance: the deterministic-enforcement mechanism: PreToolUse allow/deny/ask/defer decisions, Stop hooks that block completion until a check passes, TaskCompleted/TeammateIdle quality gates

### [S1152] Claude Code docs — Orchestrate teams of Claude Code sessions (agent teams)
- type: docs
- url: https://code.claude.com/docs/en/agent-teams
- author: Anthropic
- published: continuously updated; describes v2.1.178+ behavior, feature marked experimental
- accessed: 2026-07-09
- relevance: 2026 shape of multi-agent coordination — shared task list, inter-agent messaging, adversarial hypothesis debate, hook-enforced quality gates; documents that teammate messages are never treated as user consent

### [S1153] Anthropic engineering — Writing effective tools for agents — with agents
- type: article
- url: https://www.anthropic.com/engineering/writing-tools-for-agents
- author: Anthropic Applied AI team
- published: 2025-09-11
- accessed: 2026-07-09
- relevance: tool-design principles (high-leverage tools, namespacing, semantic identifiers over UUIDs, token-efficient responses, eval-driven tool iteration) still the reference cited by 2026 material; carried-forward baseline for pewpew's MCP/CLI surfaces

### [S1154] Anthropic engineering — Demystifying evals for AI agents
- type: article
- url: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- author: Anthropic
- published: 2026-01-09
- accessed: 2026-07-09
- archive: pending
- relevance: current statistical discipline for noisy agent/system tests — pass@k vs pass^k, clean-environment trials, capability evals graduating into continuously-run regression suites, "read the transcripts" verification

### [S1155] Anthropic engineering — How we built Claude Code auto mode
- type: article
- url: https://www.anthropic.com/engineering/claude-code-auto-mode
- author: Anthropic
- published: 2026-03-25
- accessed: 2026-07-09
- archive: pending
- relevance: permission tiering for autonomous agents: 93% prompt-approval habituation data, three-tier allowlist→file-ops→transcript-classifier design, five blocked categories, 0.4% FP / 17% FN rates — the template for pewpew's bench-actuation gating

### [S1156] Anthropic engineering — Making Claude Code more secure and autonomous with sandboxing
- type: article
- url: https://www.anthropic.com/engineering/claude-code-sandboxing
- author: Anthropic
- published: 2025-11 (covered by InfoQ 2025-11)
- accessed: 2026-07-09
- archive: pending
- relevance: OS-level filesystem + network (proxy-enforced domain allowlist) isolation as the replacement for permission-prompt-per-command; 84% prompt reduction internally; runtime open-sourced (see S1157)

### [S1157] anthropic-experimental/sandbox-runtime — open-source agent sandbox
- type: code
- url: https://github.com/anthropic-experimental/sandbox-runtime
- pinned: anthropic-experimental/sandbox-runtime@00da2a8da0d86751abf6dfd4a8286434d95701e1
- author: Anthropic
- license: Apache-2.0
- published: created 2025-10-20; last push 2026-07-10; 4,617 stars at access
- accessed: 2026-07-09
- relevance: the reference implementation of OS-level sandboxing (filesystem + proxy-based network isolation) for coding agents; candidate substrate for confining pewpew bench-driving sessions

### [S1158] AGENTS.md — open format for guiding coding agents
- type: spec
- url: https://agents.md/
- author: originated by OpenAI Codex, Amp, Google Jules, Cursor, Factory; stewarded by the Agentic AI Foundation under the Linux Foundation (donated 2025-12)
- published: 2025-08 (format announcement); site current as of access
- accessed: 2026-07-09
- relevance: the cross-vendor repo-conventions standard — "a README for agents"; 60k+ open-source projects, 25+ agent products consume it; nearest-file-wins proximity rule for monorepos

### [S1159] MCP blog — The 2026-07-28 MCP Specification Release Candidate
- type: article
- url: https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- author: Model Context Protocol maintainers
- published: 2026-05-21
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260629215216/https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- relevance: where MCP is going as of mid-2026: stateless core (no initialize handshake/session header), Tasks extension for long-running tool calls (tools/call returns a task handle; tasks/get / tasks/update / tasks/cancel), extensions framework, Sampling/Roots/Logging deprecated

### [S1160] MCP specification 2025-11-25 — Server tools
- type: spec
- url: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- author: Model Context Protocol project
- published: 2025-11-25
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260704182228/https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- relevance: current-ratified norms for tool safety: human-in-the-loop SHOULD with ability to deny invocations, tool annotations treated as untrusted unless server is trusted, outputSchema/structuredContent for machine-parseable results, isError execution errors designed for agent self-correction, "log tool usage for audit purposes"

### [S1161] beriberikix/awesome-mcp-hardware — curated hardware MCP server list
- type: code
- url: https://github.com/beriberikix/awesome-mcp-hardware
- pinned: beriberikix/awesome-mcp-hardware@50e72818ac70be677fe9c982abba2d77bb97925c
- author: Jonathan Beri
- license: Apache-2.0
- published: created 2025-11-07; last push 2026-04-17; 47 stars at access
- accessed: 2026-07-09
- relevance: the best available census of hardware-facing MCP servers (serial, probe-rs debuggers, Saleae logic analyzers, oscilloscopes, STM32/ESP32 build-flash, Modbus/OPC UA); its small size and star count are themselves evidence the space is nascent

### [S1162] Adancurusul/embedded-debugger-mcp — probe-rs debug MCP server
- type: code
- url: https://github.com/Adancurusul/embedded-debugger-mcp
- pinned: Adancurusul/embedded-debugger-mcp@128703b13d3c402a8da2fdbf2f0052cd9c19dbe3
- author: Adancurusul
- license: MIT
- published: created 2025-08-05; last push 2026-06-24; 123 stars at access
- accessed: 2026-07-09
- relevance: the most-starred embedded-debug MCP server found — ARM Cortex-M/RISC-V debugging via J-Link/ST-Link/DAPLink through probe-rs; a concrete template for exposing pewpew's bench probes to agents

### [S1163] Adancurusul/serial-mcp-server — serial-port MCP server
- type: code
- url: https://github.com/Adancurusul/serial-mcp-server
- pinned: Adancurusul/serial-mcp-server@6c05e3808dac7f797a574d3f4a2e38f940d7ee4b
- author: Adancurusul
- license: MIT
- published: created 2025-08-06; last push 2026-07-07; 74 stars at access
- accessed: 2026-07-09
- relevance: actively maintained (pushed 2 days before access) serial-console MCP surface — read/monitor/write tool split relevant to pewpew's read-vs-actuate tiering for device consoles

### [S1164] Parker Dorris — MCP For Debug Instruments (Switching Context)
- type: article
- url: https://www.switchingcontext.com/p/mcp-for-debug-instruments
- author: Parker Dorris (embedded systems developer)
- published: 2025-08-16
- accessed: 2026-07-09
- relevance: earliest coherent argument for exposing bench instruments to agents via MCP to close the code→observe→debug loop; author's own proof-of-concept "not really" working is honest evidence of 2025 immaturity

### [S1165] GitHub Docs — About Copilot cloud agent (coding agent)
- type: docs
- url: https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- author: GitHub
- published: continuously updated; current as of access
- accessed: 2026-07-09
- relevance: the mainstream background-agent shape: issue-in/PR-out, ephemeral GitHub-Actions dev environment where the agent runs tests and linters, copilot-setup-steps.yml, firewall, MCP servers (GitHub + Playwright default), branch-protection containment, 59-minute session cap

### [S1166] Cursor docs — Cloud agents
- type: docs
- url: https://cursor.com/docs/cloud-agent
- author: Cursor (Anysphere)
- published: continuously updated; current as of access
- accessed: 2026-07-09
- relevance: second mainstream background-agent shape: isolated VMs configured via .cursor/environment.json (install/start commands, snapshots, Dockerfiles), "cloud agents can build, test, and interact with the changed software", evidence artifacts (screenshots, videos, logs), hooks for policy checks

### [S1167] OpenAI Codex docs — Cloud tasks
- type: docs
- url: https://developers.openai.com/codex/cloud
- author: OpenAI
- published: continuously updated; current as of access (redirects to learn.chatgpt.com/docs/cloud)
- accessed: 2026-07-09
- relevance: third mainstream background-agent shape: parallel cloud environments with per-repo setup scripts and configurable (default-restricted) internet access; confirms the cross-vendor convergence on sandboxed run-and-verify environments

### [S1168] Justin Poehnelt — You Need to Rewrite Your CLI for AI Agents
- type: article
- url: https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/
- author: Justin Poehnelt, Senior Software Engineer at Google (built the Google Workspace CLI agent-first)
- published: 2026-03-04
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260706195226/https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/
- relevance: concrete 2026 statement of agent-first CLI design from a practitioner who shipped one: deterministic JSON output, runtime schema introspection, --dry-run on mutating operations, adversarial input validation, skill files over --help

### [S1169] Espressif Developer Portal — Developing a Zephyr IoT app with AI
- type: article
- url: https://developer.espressif.com/blog/2026/06/zephyr-coding-with-ai/
- author: Ricardo F. Tafas Jr., Senior Software Manager, Espressif
- published: 2026-06-15
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710100456/https://developer.espressif.com/blog/2026/06/zephyr-coding-with-ai/
- relevance: the ESP32 vendor's own mid-2026 account of agent-assisted firmware development: Plan→Execute→Commit→Test loop, "UART as ground truth", journal of failed attempts, component-before-product; notable for testing on real hardware only (no simulator in the loop)

### [S1170] Scrolltest — Flaky Tests: Detection, Quarantine, and Prevention in 2026
- type: article
- url: https://scrolltest.com/flaky-tests-detection-quarantine-prevention-guide-2026/
- author: Scrolltest
- published: 2026-03-19
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260411172428/https://scrolltest.com/flaky-tests-detection-quarantine-prevention-guide-2026/
- relevance: 2026 flake discipline: run new/changed tests 5–10× pre-merge, flakiness scores per test, quarantine lanes with owner + two-week deadline, blind retries explicitly deprecated ("a test that needs retries to pass consistently is still broken")

### [S1171] Sentry docs — Seer (AI debugging agent)
- type: docs
- url: https://docs.sentry.io/product/ai-in-sentry/seer/
- author: Sentry
- published: continuously updated; current as of access
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260519071048/https://docs.sentry.io/product/ai-in-sentry/seer/
- relevance: production example of a telemetry-watching background agent: auto-scans incoming issues, background root-cause analysis over traces/logs/profiles, hands fixes off to Claude Code / Cursor cloud agents / Copilot; PR creation gated on explicit human prompt with org-level disable controls

### [S1172] Sentry press release — Sentry Launches Seer Agent
- type: article
- url: https://sentry.io/about/press-releases/sentry-launches-seer-agent/
- author: Sentry
- published: 2026-04-28
- accessed: 2026-07-09
- archive: pending
- relevance: dates the telemetry-agent pattern going mainstream (natural-language investigation over errors, spans, logs, traces); companion 2026-01-27 release extended Seer to local dev and code review

### [S1173] PPC Land — llms.txt adoption rises 8.8x but 97% of files get zero AI requests
- type: article
- url: https://ppc.land/llms-txt-adoption-rises-8-8x-but-97-of-files-get-zero-ai-requests/
- author: PPC Land
- published: 2026 (May–June; reports OtterlyAI 90-day measurement: 84 of 62,100 AI bot requests hit llms.txt)
- accessed: 2026-07-09
- relevance: evidence that llms.txt failed as a machine-readable context standard (no major LLM provider crawler supports it), in contrast to AGENTS.md's adoption — calibrates which "machine-readable project map" conventions actually won

## Block S1200–S1249 — RA-21 Fleet resilience

### [S1200] ESP-IDF Watchdogs guide (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/wdts.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260113062456/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/wdts.html
- relevance: first-party reference for IWDT/TWDT/XTWDT config, defaults, and the subscribe/reset API a render loop must use

### [S1201] ESP-IDF Fatal Errors guide (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/fatal-errors.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260310155012/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/fatal-errors.html
- relevance: panic-handler behaviors (CONFIG_ESP_SYSTEM_PANIC), Guru Meditation classes, brownout reset behavior, RTC-watchdog-as-final-failsafe

### [S1202] ESP-IDF Core Dump guide (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/core_dump.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710133500/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/core_dump.html
- relevance: core-dump-to-flash config, ELF format, SHA256 integrity, partition sizing formula — the black-box recorder for crashed nodes

### [S1203] esp-idf espcoredump runtime API (esp_core_dump.h)
- type: code
- url: https://github.com/espressif/esp-idf/blob/master/components/espcoredump/include/esp_core_dump.h
- pinned: espressif/esp-idf@f0887bcf8763266effe3fa0b358340df226a04b5
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: proves programmatic on-device retrieval: esp_core_dump_image_check/image_get/image_erase, esp_core_dump_get_summary, esp_core_dump_get_panic_reason

### [S1204] ESP-IDF Miscellaneous System API (esp_reset_reason)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260303122027/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html
- relevance: full esp_reset_reason_t enum (PANIC, INT_WDT, TASK_WDT, BROWNOUT, PWR_GLITCH, CPU_LOCKUP…), shutdown handlers, esp_get_minimum_free_heap_size

### [S1205] ESP-IDF Non-Volatile Storage (NVS) docs
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260213110244/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html
- relevance: log-structured append semantics (÷126 erase amortization), power-loss guarantees, CONFIG_NVS_FLASH_VERIFY_ERASE for weak supplies — the write-frequency discipline evidence

### [S1206] ESP32-S3 brownout Kconfig (Kconfig.power)
- type: code
- url: https://github.com/espressif/esp-idf/blob/master/components/esp_hw_support/power_supply/port/esp32s3/Kconfig.power
- pinned: espressif/esp-idf@f0887bcf8763266effe3fa0b358340df226a04b5
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-07-09
- relevance: exact S3 brownout levels — default LVL_SEL_7 ≈ 2.44 V up to 3.30 V — with Espressif's own in-file caveat that the voltages are estimates

### [S1207] ESP32-S3-MINI-1/1U module datasheet
- type: datasheet
- url: https://documentation.espressif.com/esp32-s3-mini-1_mini-1u_datasheet_en.html
- author: Espressif Systems
- accessed: 2026-07-09
- relevance: –40 to 85 °C operating ambient, flash endurance 100,000 P/E cycles / 20-year retention — thermal-derating and NVS-wear anchors

### [S1208] esp32.com: preserving error info between reboots with RTC_NOINIT_ATTR
- type: forum
- url: https://esp32.com/viewtopic.php?t=16659
- author: esp32.com community (Espressif-hosted forum)
- accessed: 2026-07-09
- archive: pending
- relevance: RTC_NOINIT_ATTR survives SW/WDT/panic resets but not power loss or brownout; caller must gate re-init on reset reason — the crash-counter mechanism

### [S1209] esp-idf issue #9400: WiFi stuck while connecting, watchdog not triggered
- type: forum
- url: https://github.com/espressif/esp-idf/issues/9400
- author: espressif/esp-idf issue tracker
- published: 2022-07
- accessed: 2026-07-09
- archive: pending
- relevance: first-party tracker evidence that the WiFi stack can wedge in states the default watchdogs do not catch — motivates application-level radio liveness supervision

### [S1210] ESPHome Safe Mode component docs
- type: docs
- url: https://esphome.io/components/safe_mode/
- author: ESPHome project (Open Home Foundation)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260622152128/https://esphome.io/components/safe_mode/
- relevance: production boot-loop-detection pattern: N consecutive failed boots (default 10) → minimal firmware with only network+OTA; boot "good" after 1 min; the safe-mode design pewpew should copy

### [S1211] esphome issue #15796: safe-mode counter misses setup-phase crashes
- type: forum
- url: https://github.com/esphome/esphome/issues/15796
- author: esphome issue tracker
- published: 2024
- accessed: 2026-07-09
- archive: pending
- relevance: documented gap in the counter-in-app pattern — a crash before the counter increments defeats boot-loop detection; argues for bootloader-side or earliest-init counting

### [S1212] Memfault MCU coredump docs
- type: docs
- url: https://docs.memfault.com/docs/mcu/coredumps
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260601155918/https://docs.memfault.com/docs/mcu/coredumps
- relevance: what a commercial device-observability pipeline captures on fault (registers, tasks, selected RAM regions), store-then-upload-on-next-boot, fallback to minimal trace if storage fails

### [S1213] Memfault MCU reboot reason tracking docs
- type: docs
- url: https://docs.memfault.com/docs/mcu/reboot-reason-tracking
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260321104846/https://docs.memfault.com/docs/mcu/reboot-reason-tracking
- relevance: two-source reboot attribution (hardware register + software-marked imminent reason), noinit-RAM tracking, expected-vs-unexpected classification, bootloop metric — the forensics-minimum reference design

### [S1214] Memfault OTA & release management docs
- type: docs
- url: https://docs.memfault.com/docs/platform/ota
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260321104825/https://docs.memfault.com/docs/platform/ota
- relevance: cohorts + percentage staged rollout + fleet-health comparison charts as the abort signal — vendor-practice reference for rollout rings

### [S1215] Interrupt (Memfault) — watchdog timer best practices guide
- type: article
- url: https://interrupt.memfault.com/blog/firmware-watchdog-best-practices
- author: Interrupt / Memfault engineering blog
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260408021818/https://interrupt.memfault.com/blog/firmware-watchdog-best-practices
- relevance: hardware WDT as last resort + software WDT for state capture; feed from a low-priority task, never a timer ISR; all-tasks-check-in pattern; always-reboot-never-wedge stance

### [S1216] Google SRE Workbook ch. 16 — Canarying Releases
- type: article
- url: https://sre.google/workbook/canarying-releases/
- author: Google (Site Reliability Workbook)
- published: 2018
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260627024041/https://sre.google/workbook/canarying-releases/
- relevance: canary definition, population sizing vs blast radius, metric selection, small-population caveats — the discipline to shrink to 50 nodes

### [S1217] AWS IoT Device Management — job rollout, abort, timeout, retry configurations
- type: docs
- url: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-configurations-details.html
- author: Amazon Web Services
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260703211645/https://docs.aws.amazon.com/iot/latest/developerguide/jobs-configurations-details.html
- relevance: production fleet-OTA machinery: exponential rollout rates gated on success counts, abort on failure-percentage thresholds, maintenance windows — "avoid a bad update from being sent to an entire fleet"

### [S1218] balena docs — release policies (fleet default vs device pinning)
- type: docs
- url: https://docs.balena.io/learn/deploy/release-strategy/release-policy/
- author: balena
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251202153028/https://docs.balena.io/learn/deploy/release-strategy/release-policy/
- relevance: per-device release pinning "when performing a canary deployment" — the small-fleet adaptation of rollout rings

### [S1219] Golioth OTA docs — cohorts, packages, rollout
- type: docs
- url: https://docs.golioth.io/device-management/ota/
- author: Golioth
- accessed: 2026-07-09
- relevance: cohort-based targeting and a rollout toggle (stage a release, notify on enable, unselect to roll back) sized for small/mid IoT fleets

### [S1220] Principles of Chaos Engineering
- type: article
- url: https://principlesofchaos.org/
- author: Chaos community (originating at Netflix)
- published: 2019 (last revision)
- accessed: 2026-07-09
- archive: pending
- relevance: canonical definition, steady-state hypothesis, vary-real-world-events, minimize blast radius — the principles RA-21 adapts to a 50-node bench

### [S1221] Kalka & Szydlo — µChaos: Moving Chaos Engineering To IoT Devices (ICCS 2024)
- type: article
- url: https://www.iccs-meeting.org/archive/iccs2024/papers/148380231.pdf
- author: Wojciech Kalka, Tomasz Szydlo (AGH Krakow / Newcastle University)
- published: 2024
- accessed: 2026-07-09
- archive: pending
- relevance: the state of embedded chaos engineering — open-source Zephyr-OS fault-injection component (CPU, memory, network, sensor, application faults via serial API); documents that end-device chaos tooling barely exists

### [S1222] Candea & Fox — Crash-Only Software (HotOS IX, 2003)
- type: article
- url: https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea_html/index.html
- author: George Candea, Armando Fox (Stanford)
- published: 2003-05
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260115050447/https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea_html/index.html
- relevance: the academic case for reboot-as-recovery: one way to stop (crash) and one way to start (recover) yields simpler, more reliable systems — grounds the self-reboot-on-anomaly stance

### [S1223] Doug Fleenor Design — DMX512 to 0-10 V Analog Converter owner's manual
- type: docs
- url: https://www.dfd.com/pdf/24anl-man.pdf
- author: Doug Fleenor Design
- published: 2019-07 (manual revision)
- accessed: 2026-07-09
- archive: pending
- relevance: stage-lighting hold-last-look convention in writing: holds last levels on DMX loss until control restored or power removed; levels reset to zero on power-up; optional jumper for blackout ~1 s after loss

### [S1224] ANSI E1.11-assoc. ANSI E1.31-2016 — sACN (Streaming ACN)
- type: spec
- url: https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
- author: ESTA Technical Standards Program
- published: 2016
- accessed: 2026-07-09
- archive: pending
- relevance: codified loss-of-data machinery: E131_NETWORK_DATA_LOSS_TIMEOUT (2.5 s of silence) and the stream-terminated option bit (sent 3×) — receiver-local timers decide degradation, no consensus

### [S1225] Battery University BU-502 — Discharging at High and Low Temperatures
- type: article
- url: https://batteryuniversity.com/article/bu-502-discharging-at-high-and-low-temperatures
- author: Battery University (Cadex Electronics)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260622174801/https://www.batteryuniversity.com/article/bu-502-discharging-at-high-and-low-temperatures
- relevance: capacity ≈50 % at –18 °C, internal-resistance rise in cold, cycle-life loss above 30 °C — battery-vs-temperature priors for outdoor fleet planning

### [S1226] MacroFab — Conformal Coating vs. Potting/Encapsulation
- type: article
- url: https://www.macrofab.com/blog/conformal-coating-vs-potting-encapsulation
- author: MacroFab (electronics manufacturer engineering blog)
- accessed: 2026-07-09
- archive: pending
- relevance: protection-vs-serviceability tradeoff: thin coatings (~25–75 µm) rework-friendly and thermally benign; potting seals to IP67/68 but kills rework and stresses solder joints in thermal cycling

### [S1227] PCBCart — Burn-In Testing: Filtering Out Infant Mortality
- type: article
- url: https://www.pcbcart.com/article/content/burn-in-testing-electronics-reliability.html
- author: PCBCart (electronics manufacturer)
- accessed: 2026-07-09
- archive: pending
- relevance: bathtub-curve rationale for pre-deployment soak; typical durations (8–48 h consumer, up to 168 h high-reliability) under elevated temperature/voltage/load

### [S1228] Reliability Analytics Toolkit — Poisson spares analysis
- type: docs
- url: https://reliabilityanalyticstoolkit.appspot.com/poisson_spares_analysis
- author: Reliability Analytics (method per USAF Rome Laboratory Reliability Engineer's Toolkit, 1993)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260119174046/https://reliabilityanalyticstoolkit.appspot.com/poisson_spares_analysis
- relevance: the standard spares formula: Poisson on population × failure rate × resupply interval at a chosen confidence — the method RA-21 applies to a 50-node fleet

### [S1229] Advatek PixLite 16 Plug & Play Mk2 user manual
- type: docs
- url: https://cdn.prod.website-files.com/6526c8266f9d6acac8ef145f/661d4804085c9f0866d03279_PixLite%2016%20Plug%20And%20Play%20Mk2%20User%20Manual_20230823.pdf
- author: Advatek Lighting
- published: 2023-08-23
- accessed: 2026-07-09
- archive: pending
- relevance: professional outdoor-pixel install practice: IP67 screw-lock connectors with gold pins, warning that poor waterproofing lets rain short supply onto data lines, ≤15 m controller-to-first-pixel rule
