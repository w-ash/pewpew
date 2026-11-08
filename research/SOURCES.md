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
- pinned: wled/WLED@26f032ef4976f76470d7603fdd17766f5e8a93f2
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
- archive: https://web.archive.org/web/20260505174829/https://electromage.com/pixelblaze/  # snapshot 2026-05-05 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250706105326/https://www.misc.name/fadecandy/  # snapshot 2025-07-06 (snapshot predates accessed date; refresh next verification pass)
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
- pinned: mattshepcar/SmoothLed@e09236cfc63a96c565d97ef316073452a38cf86d
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
- pinned: FalconChristmas/fpp@05d9dfa914a2b259cf09ee9f0315083f7dd78e7b
- accessed: 2026-07-03
- relevance: sequence player + MultiSync protocol; multi-device sync prior art (seed)

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
- pinned: xLightsSequencer/xLights@47edb093528fb1d0e8a67712b2941fcf509f5f19
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
- pinned: heronarts/LX@b7c10b3cf5d588de6bd95fb9200eb649b77f366c
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
- archive: https://web.archive.org/web/20260627175017/https://bottosson.github.io/posts/oklab/  # snapshot 2026-06-27 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260308001421/https://learn.adafruit.com/led-tricks-gamma-correction/the-issue  # snapshot 2026-03-08 (snapshot predates accessed date; refresh next verification pass)
- relevance: the community-standard gamma-2.8 8-bit table; also illustrates the low-end code collapse of 8->8 gamma

### [S059] ledshield — "LED Brightness to your eye, Gamma correction – No!"
- type: article
- url: https://ledshield.wordpress.com/2012/11/13/led-brightness-to-your-eye-gamma-correction-no/
- author: HP LED Shield blog
- published: 2012-11-13
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260105233202/https://ledshield.wordpress.com/2012/11/13/led-brightness-to-your-eye-gamma-correction-no/  # snapshot 2026-01-05 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260124202640/https://photonstophotos.net/GeneralTopics/Exposure/Psychometric_Lightness_and_Gamma.htm  # snapshot 2026-01-24 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260413181215/https://learn.adafruit.com/adafruit-neopxl8-featherwing-and-library/neopxl8hdr  # snapshot 2026-04-13 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250926214129/https://www.superlightingled.com/blog/sk9822-vs-apa102-vs-apa107-vs-hd107-vs-hd107s-vs-hd108/  # snapshot 2025-09-26 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260605123325/https://tomverbeure.github.io/2019/10/13/WS2812B_Reset_Old_and_New.html  # snapshot 2026-06-05 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250801212513/https://lcsc.com/product-detail/RGB-LEDs-Built-in-IC_Worldsemi-WS2812B-2020_C965555.html  # snapshot 2025-08-01 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251011214024/https://www.normandled.com/upload/201808/WS2815%20LED%20Datasheet.pdf  # snapshot 2025-10-11 (snapshot predates accessed date; refresh next verification pass)
- relevance: WS2815 12 V, BIN backup data input behavior, constant-current spec (~15 mA white)

### [S112] SDIP Light — What is WS2815 and how to use it
- type: article
- url: https://www.sdiplight.com/what-is-ws2815-and-how-to-use-ws2815-led/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250613201220/https://www.sdiplight.com/what-is-ws2815-and-how-to-use-ws2815-led/  # snapshot 2025-06-13 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260606233015/https://cdn-shop.adafruit.com/product-files/1138/SK6812+LED+datasheet+.pdf  # snapshot 2026-06-06 (snapshot predates accessed date; refresh next verification pass)
- relevance: SK6812 timing, 1.2 kHz PWM, RGBW data format

### [S115] SuperLightingLED blog — SK6812 vs WS2812B
- type: article
- url: https://www.superlightingled.com/blog/sk6812-vs-ws2812b/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260310114317/https://www.superlightingled.com/blog/sk6812-vs-ws2812b/  # snapshot 2026-03-10 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250311203105/https://github.com/FastLED/FastLED/issues/1855  # snapshot 2025-03-11 (snapshot predates accessed date; refresh next verification pass)
- relevance: WS2816 48-bit GRB format, hardware gamma, ~10 kHz refresh; FastLED support discussion

### [S123] WS2816B-2020 datasheet (TME mirror)
- type: datasheet
- url: https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf
- author: WorldSemi
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260727054006/https://www.tme.eu/Document/6e37dbd0c854ce14f428cca7891158c6/WS2816B-2020.pdf
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
- archive: https://web.archive.org/web/20260415200550/https://www.shiji-leds.com/blog/future-trends-in-addressable-led-strip-technology-and-applications/  # snapshot 2026-04-15 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260101013716/https://cpldcpu.com/2016/12/13/sk9822-a-clone-of-the-apa102/  # snapshot 2026-01-01 (snapshot predates accessed date; refresh next verification pass)
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
- pinned: FastLED/FastLED@11de483f4244041f14efe55e73bcea7ccea1c8f6
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
- archive: https://web.archive.org/web/20260618044601/https://learn.adafruit.com/neopixel-levelshifter  # snapshot 2026-06-18 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260526053456/https://quinled.info/the-ultimate-led-strip-power-injection-guide/  # snapshot 2026-05-26 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260327012755/https://www.3waylabs.com/ddp/  # snapshot 2026-03-27 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260621120941/https://kno.wled.ge/interfaces/e1.31-dmx/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260312072216/http://openpixelcontrol.org/  # captured 2026-07-03 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260621121207/https://kno.wled.ge/interfaces/udp-realtime/  # snapshot 2026-06-21 (snapshot predates accessed date; refresh next verification pass)
- relevance: byte layouts, per-packet LED limits, timeout semantics of WLED-native realtime UDP
- note: same underlying source as [S253] — do not co-cite the pair as independent corroboration

### [S163] FPP ControlProtocol.txt — MultiSync wire protocol
- type: docs
- url: https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt
- author: Falcon Christmas / FPP contributors
- license: GPL-2.0 (FPP repo)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250628110943/https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt (snapshot predates accessed date; refresh next verification pass)
- relevance: MultiSync packet format — port 32320, multicast 239.70.80.80, frame-number sync of pre-stored sequences

### [S164] xLights Manual — Controllers Settings / lighting networks (protocol support matrix)
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks
- author: xLights contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260611013232/https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks  # snapshot 2026-06-11 (snapshot predates accessed date; refresh next verification pass)
- relevance: lists DDP support across FPP/Kulp, HinksPix, Falcon v3/v4/v5, WLED, Genius, Minleon; calls DDP more efficient than Art-Net/E1.31. Re-read 2026-11-07: two controller outputs with the same IP put xLights in "Unmanaged" mode, "valid" but "highly not recommended"

### [S165] WLED knowledge base — FAQ (LED count, WiFi limits, DDP and Ethernet recommendations)
- type: docs
- url: https://kno.wled.ge/basics/faq/
- author: WLED contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260621120848/https://kno.wled.ge/basics/faq/  # snapshot 2026-06-21 (snapshot predates accessed date; refresh next verification pass)
- relevance: 750-LED per-controller guidance, 720 kbit/s @1000 LED/30fps, DDP-over-E1.31 recommendation, QuinLED/Olimex Ethernet advice

### [S166] Electric UI — "Latency comparison of common wireless links for microcontrollers"
- type: article
- url: https://electricui.com/blog/latency-comparison
- author: Electric UI
- published: 2024-02
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260520234140/https://electricui.com/blog/latency-comparison  # snapshot 2026-05-20 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250612180210/https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3/updates/manufacturing-ui-controls-pov  # snapshot 2025-06-12 (snapshot predates accessed date; refresh next verification pass)
- relevance: introduces convention-based UI controls (sliderSpeed, hsvPickerColor) generated from exported function names

### [S204] Pixelblaze Sensor Expansion Board (ElectroMage shop / bhencke.com)
- type: product
- url: https://www.bhencke.com/pixelblaze-sensor-expansion
- author: Ben Hencke
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260420032034/https://electromage.com/docs/sensor-expansion-board/  # captured 2026-07-03 (snapshot predates accessed date; refresh next verification pass)
- relevance: sensor feature injection as exported pattern variables (frequencyData[32], energyAverage, accelerometer[3], light, analogInputs[5])

### [S205] WLED docs — Custom Features (adding effects via usermods)
- type: docs
- url: https://kno.wled.ge/advanced/custom-features/
- author: WLED project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260629193319/https://kno.wled.ge/advanced/custom-features/  # snapshot 2026-06-29 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260313074616/https://mm.kno.wled.ge/moonmodules/arti-fx/  # snapshot 2026-03-13 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251128070835/https://jackw01.github.io/led-control/  # snapshot 2025-11-28 (snapshot predates accessed date; refresh next verification pass)
- relevance: Python-as-fragment-shader signature (t, dt, x, y, z, prev_state), RestrictedPython + C-extension perf split, 150 fps @ 150 RGBW on Pi Zero claim; repo dormant since 2023-11-10

### [S211] todbot — "Speed up CircuitPython LED animations 10x!" (+ code repo)
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt (todbot)
- published: 2022-10-21
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260519221054/https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/  # snapshot 2026-05-19 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251208001252/https://derivative.ca/workshop/dmx-artnet-and-led-mapping-touchdesigner/71671  # snapshot 2025-12-08 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251111015300/https://chromatik.co/develop/coding/  # snapshot 2025-11-11 (snapshot predates accessed date; refresh next verification pass)
- relevance: first-class parameter objects: addParameter + CompoundParameter(label, init, min, max) → auto UI knob + MIDI/OSC mapping + LFO modulation; LXPattern.run(deltaMs) lifecycle

### [S217] Pixelblaze Language Reference (hosted docs, current firmware)
- type: docs
- url: https://electromage.com/docs/language-reference/
- author: Ben Hencke / ElectroMage (Hencke Technologies, Inc.)
- published: page states it is current for firmware v3.30 (v3 devices) and v2.24 (v2)
- accessed: 2026-07-27
- archive: pending (UNARCHIVABLE by the usual route: the page is a JS-rendered Nuxt SPA. Save-Page-Now on 2026-07-27 declined to re-capture and redirected to an existing 2026-07-04 snapshot, which predates this read AND stores only the loader shell — it contains none of the cited text. Recording that URL would satisfy a grep and prove nothing. Needs a rendered-DOM capture or a verbatim excerpt under research/excerpts/; content below was read from the live rendered DOM on 2026-07-27.)
- relevance: arrays are first-class persistent globals — created with `array(n)` or array literals, mutated in place through an Array Functions library (`arrayMutate`, `arrayMapTo`, `arrayReduce`, `arraySum`) that the 2020 pinned copy [S680] predates — so per-pixel state beyond the output buffer already survives frames in the model ADR-005 copies. Counterpoint recorded with it: `beforeRender(delta)` receives no coordinates, and the docs assume globals may be written inside `render()` ("If you export a global variable that is modified inside `render()`"), i.e. Pixelblaze buys per-pixel state with an impure render — the opposite trade to ADR-005's.
- note: the hosted, continuously-updated sibling of [S680]'s pinned `README.expressions.md`. Overlapping text (array creation, no-free, the Var Watcher render() note) is the SAME document lineage — do not co-cite the pair as independent corroboration. Only the Array Functions library and the firmware-currency statement are genuinely additive over S680.
- note: no per-pattern array-element budget is stated anywhere on this page; the widely-repeated "10,240 elements" figure is NOT sourced here and is not claimed.
- note: **deliberately not cited by any ADR**, so the pending archive above is not an ADR-000 rule-4 violation. The ADR-005 amendment that this source was read for anchors every load-bearing Pixelblaze claim on the pinned, excerpted [S680] instead — array creation and the no-free rule at `README.expressions.md#L86,L93`, the coordinate-free `beforeRender(delta)` at `#L23`, and the globals-written-inside-`render()` note at `#L35`. Retained here because the read produced two findings worth keeping: the Array Functions library that postdates the S680 pin, and the negative result about the "10,240" figure. Promote to a cited source only alongside a rendered-DOM capture or an excerpt under `research/excerpts/`.

### [S218] ISF — Multi-Pass and Persistent Buffer Reference
- type: docs
- url: https://docs.isf.video/ref_multipass.html
- author: VIDVOX (mrRay)
- accessed: 2026-07-27
- archive: https://web.archive.org/web/20260728022305/https://docs.isf.video/ref_multipass.html#multi-pass-shaders
- relevance: the host-allocated, author-declared persistent-buffer model. Buffers are declared per entry in the `PASSES` manifest with `PERSISTENT: true`; "the ISF host will automatically create buffers to render into"; they "stay with the ISF file for as long as it exists". Optional `FLOAT: true` selects 32-bit storage and optional per-buffer `WIDTH`/`HEIGHT` expressions (`"$WIDTH/16.0"`) let a buffer live at its own resolution — direct precedent for engine-managed state buffers declared up front, at a shape the pattern chooses rather than the output's.
- note: same project and authorship as [S214] (ISF spec, cited in ADR-006 for the typed-param manifest) — the manifest mechanism extended to state, NOT an independent second source. Do not count S214 and S218 as two.
- note: this page does not describe pooling or per-frame discard of NON-persistent buffers; it says only that the host creates them. No claim about their lifetime is made here.

### [S219] Shadertoy unofficial — "Special Shadertoy features" (Buffers A..D)
- type: article
- url: https://shadertoyunofficial.wordpress.com/2016/07/20/special-shadertoy-features/
- author: Fabrice Neyret (fabriceN) — community documentation, not Shadertoy's own
- published: 2016-07-20 (page byline shows a 2025-08-25 revision)
- accessed: 2026-07-27
- archive: https://web.archive.org/web/20260728022346/https://shadertoyunofficial.wordpress.com/2016/07/20/special-shadertoy-features/
- relevance: the third independent lineage for persistent render-target state. Buffers A–D store their result instead of displaying it, are "evaluated in A..D order, then image", are 32-bit float rather than byte, and the canonical feedback idiom is stated outright: "For persistent or incremental effects, make your buffer read the same texture it produces (i.e. previous state vs next state). It seems to be initialized to 0." Also independently supports re-initialising persistent state when geometry changes: "For buffers relying on persistence, they won't keep valid if resolution changes while running: consider testing change, or a magic key to reinitialize."

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
- archive: https://web.archive.org/web/20260621121207/https://kno.wled.ge/interfaces/udp-realtime/  # snapshot 2026-06-21 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250603142246/https://github.com/Cryptkeeper/fseq-file-format  # snapshot 2025-06-03 (snapshot predates accessed date; refresh next verification pass)
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
- relevance: practitioner norms on sequence frame rates — 20 fps legacy standard, 40 fps recommended for dense/HD modern displays

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
- pinned: TheMariday/marimapper@7dc5f799a1b7c180573c2632f6d12a3be0cbf4fa
- license: GPL-3.0 (seed — verify)
- accessed: 2026-07-03
- relevance: current active camera-based 3D LED mapper

### [S301] Lightwork (PWRFLcreative)
- type: code
- url: https://github.com/PWRFLcreative/Lightwork
- pinned: PWRFLcreative/Lightwork@48fa902b006dbc9a981e6c61218422cba5700c3c
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
- archive: https://web.archive.org/web/20260621120941/https://kno.wled.ge/advanced/mapping/  # snapshot 2026-06-21 (snapshot predates accessed date; refresh next verification pass)
- relevance: canonical spec of WLED ledmap.json index-permutation format, -1 gaps, width/height 2D keys, per-preset map selection

### [S304] Pixelblaze mapper README (simap/pixelblaze)
- type: docs
- url: https://github.com/simap/pixelblaze/blob/master/README.mapper.md
- author: Ben Hencke
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260420032034/https://github.com/simap/pixelblaze/blob/master/README.mapper.md  # snapshot 2026-04-20 (snapshot predates accessed date; refresh next verification pass)
- relevance: spec of Pixelblaze pixel-map JSON, map generator functions, 0..1 world-unit normalization, Fill/Contain scaling, render2D/render3D
- note: same underlying document as [S680]'s README.mapper.md (seed URL vs pinned repo copy) — do not co-cite the pair as independent corroboration

### [S305] LedFx docs — "How to: Create and Edit Virtuals"
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/virtuals.html
- author: LedFx contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260521223731/https://docs.ledfx.app/en/latest/howto/virtuals.html  # snapshot 2026-05-21 (snapshot predates accessed date; refresh next verification pass)
- relevance: defines virtuals/segments (device,start,end,reverse), span vs copy modes, rows/grouping 2D reshaping, complex-segments numpy fast path

### [S306] xLights manual — Custom Model
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/custom-model
- author: xLights contributors
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260317062924/https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/custom-model  # snapshot 2026-03-17 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260309180104/https://falcon-player.gitbooks.io/falcon-player-manual/content/chapter_five_inputoutput_setup/pixel_overlay_models.html  # snapshot 2026-03-09 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250828092218/https://forum.electromage.com/t/2d-pixel-coordinate-mapping-tool-for-images/714  # snapshot 2025-08-28 (snapshot predates accessed date; refresh next verification pass)
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

### [S316] GDTF and MVR specifications (mvrdevelopment/spec)
- type: spec
- url: https://github.com/mvrdevelopment/spec
- pinned: mvrdevelopment/spec@098d3791f77f0895bd859adf01864b4826e2006f
- author: MVR-group (GDTF / MVR working group, DIN SPEC 15800 and 15801)
- license: TBD (no LICENSE file in the repository root; the README grants free use of the default meshes only)
- accessed: 2026-10-22
- archive: https://web.archive.org/web/2026/https://github.com/mvrdevelopment/spec (not yet captured; spec text is pinned by commit above)
- relevance: GDTF is the catalog half (fixture type, geometry, WiringObject with power source, consumer and fuse, but no cable length or gauge, `gdtf-spec.md` L1612-L1646) and MVR the scene half (fixture instance with a right-handed Z-up millimetre `Matrix` and `Addresses`, `mvr-spec.md` L1005-L1007). The model for the arrangement/catalog split in the ADR-007 amendment and the fixed Z-up mm conversion on MVR import and export.

### [S317] Chromatik guide — Model Definition
- type: docs
- url: https://chromatik.co/guide/model-definition/
- author: Mark Slee / Heron Arts
- accessed: 2026-11-07
- archive: https://web.archive.org/web/20260704010506/https://chromatik.co/guide/model-definition/  # snapshot 2026-07-04 (snapshot predates accessed date; refresh next verification pass)
- relevance: the built-in Strip fixture is "a linear strip of points" set by two parameters, Points and Spacing; +Y up, units the author's choice — the precedent for the parametric `strip` type with `pixels` and `pitch`

### [S318] xLights manual — Single Line Model
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/single-line-model
- author: xLights contributors
- accessed: 2026-11-07
- archive: https://web.archive.org/web/20260517144641/https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/single-line-model  # snapshot 2026-05-17 (snapshot predates accessed date; refresh next verification pass)
- relevance: a straight line set by # Strings and Nodes/String, with Starting Location naming "which end the wiring starts from" — a parametric strip whose data-in end sets its direction

### [S319] MVR specification — File Format Definition (GDTF Hub)
- type: spec
- url: https://gdtf.eu/mvr/mvr-spec/file-format-definition/
- author: MVR-group (GDTF / MVR working group, DIN SPEC 15801)
- accessed: 2026-11-07
- archive: https://web.archive.org/web/20260514193442/https://www.gdtf.eu/mvr/mvr-spec/file-format-definition/  # snapshot 2026-05-14 (snapshot predates accessed date; refresh next verification pass)
- relevance: the rendered MVR spec: a fixture's `Addresses` hold DMX addresses and a `Network` node with an IPv4 address or hostname; the Matrix is right-handed, Z-up, 1 unit = 1 mm. The scene file carries each device's network address, as the arrangement's `controllers[].host` does. S316 pins the same spec's source.

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
- archive: https://web.archive.org/web/20260621121208/https://kno.wled.ge/basics/compatible-controllers/  # snapshot 2026-06-21 (snapshot predates accessed date; refresh next verification pass)
- relevance: official WLED hardware guidance — ESP8266 deprecation, ESP32 variant support tiers, Ethernet boards

### [S352] MoonModules/MoonLight — Releases (v0.5.8–v1.0.0)
- type: docs
- url: https://github.com/MoonModules/MoonLight/releases
- author: MoonModules (ewowi et al.)
- license: GPL-3.0
- published: 2025-08-15 through 2026-05-06 (v1.0.0)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251003145210/https://github.com/MoonModules/MoonLight/releases  # snapshot 2025-10-03 (snapshot predates accessed date; refresh next verification pass)
- relevance: MoonLight hardware targets (S3/P4 best, PSRAM 130K LEDs, PARLIO P4 driver, supported boards)

### [S353] Espressif Developer Portal — Wireless Connectivity Solutions for ESP32-P4
- type: docs
- url: https://developer.espressif.com/blog/wireless-connectivity-solutions-for-esp32-p4/
- author: Espressif Systems
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260415161024/https://developer.espressif.com/blog/wireless-connectivity-solutions-for-esp32-p4/  # snapshot 2026-04-15 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260512192114/https://github.com/wled/WLED/issues/5576  # snapshot 2026-05-12 (snapshot predates accessed date; refresh next verification pass)
- relevance: concrete evidence ESP8266 is being squeezed out of full WLED builds (flash exhaustion); see also #5363

### [S357] QuinLED Dig-Next-2 specifications
- type: product
- url: https://quinled.info/dig-next-2-specifications/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260418213721/https://quinled.info/dig-next-2-specifications/  # snapshot 2026-04-18 (snapshot predates accessed date; refresh next verification pass)
- relevance: current-gen QuinLED small board — ESP32 8MB/2MB PSRAM, 2 outputs, 5-48V, fusing, firmware compatibility list

### [S358] QuinLED Dig-Octa — modular WLED LED system
- type: product
- url: https://quinled.info/quinled-dig-octa/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260526015933/https://quinled.info/quinled-dig-octa/  # snapshot 2026-05-26 (snapshot predates accessed date; refresh next verification pass)
- relevance: room/stage-scale QuinLED — 8 channels + Ethernet brainboard on 30-100A fused powerboards, E1.31/Art-Net/DDP

### [S359] Falcon F16v5 pixel controller (store page)
- type: product
- url: https://pixelcontroller.com/store/featured/88-f16v5.html
- author: Falcon / pixelcontroller.com
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260620030843/https://pixelcontroller.com/store/featured/88-f16v5.html  # snapshot 2026-06-20 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260628152046/https://www.advateklighting.com/products/a4-s-mk3  # snapshot 2026-06-28 (snapshot predates accessed date; refresh next verification pass)
- relevance: professional tier — A4-S Mk3 4080 px over 4 outputs; E4-S Ethernet and T8-S long-range variants

### [S363] HinksPix Pro V3 CPU (HolidayCoro)
- type: product
- url: https://www.holidaycoro.com/HinksPix-Pro-V3-CPU-20-Long-Range-Jacks-80-Ports-p/952-6.htm
- author: HolidayCoro
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250423205030/https://www.holidaycoro.com/HinksPix-Pro-V3-CPU-20-Long-Range-Jacks-80-Ports-p/952-6.htm  # snapshot 2025-04-23 (snapshot predates accessed date; refresh next verification pass)
- relevance: high-density holiday-display controller — V3 CPU + expansions to 16,320 px, 80-port long-range configs

### [S364] forkineye/ESPixelStick — repository and releases
- type: code
- url: https://github.com/forkineye/ESPixelStick
- pinned: forkineye/ESPixelStick@255736f9a134d0d4e9553dabda95b5ab76c3931b
- author: Shelby Merrick (forkineye)
- license: MIT
- accessed: 2026-07-03
- relevance: ESPixelStick V4 firmware stuck at v4.0-beta4 (2023-11) with development in fork/CI artifacts — waning evidence

### [S365] simap/pixelblaze_output_expander — firmware + serial protocol
- type: code
- url: https://github.com/simap/pixelblaze_output_expander
- pinned: simap/pixelblaze_output_expander@3e7390bd469d449cc5f85146929d644567e83201
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
- pinned: jgarff/rpi_ws281x@22f2e35012704845d82e06d2fa2e10fbc810ecaa
- author: Jeremy Garff et al.
- license: BSD-2-Clause
- accessed: 2026-07-03
- relevance: Pi 5 RP1 chip broke legacy WS281x GPIO output; needs rp1_ws281x_pwm kernel module — evidence native Pi pixel output is a dead end

### [S368] FalconChristmas/fpp — releases (FPP 9.x Pi 5 support)
- type: code
- url: https://github.com/FalconChristmas/fpp/releases
- pinned: FalconChristmas/fpp@05d9dfa914a2b259cf09ee9f0315083f7dd78e7b
- author: FalconChristmas
- license: GPL-2.0/GPL-3.0 mixed (FPP)
- accessed: 2026-07-03
- relevance: FPP 9.x (latest 9.5) images support Pi Zero through Pi 5 and BeagleBone — render-host OS support status

### [S369] QuinLED — The Ultimate LED Strip Power Injection Guide (+ wire thickness guide)
- type: docs
- url: https://quinled.info/the-ultimate-led-strip-power-injection-guide/
- author: Quindor (Intermittent Technology)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260526053456/https://quinled.info/the-ultimate-led-strip-power-injection-guide/  # snapshot 2026-05-26 (snapshot predates accessed date; refresh next verification pass)
- relevance: injection sizing (≤10% Vdrop), 5V-vs-12V injection cadence, 18AWG strip-feed guidance, edge-vs-mid injection fusing
- note: same underlying source as [S135] — do not co-cite the pair as independent corroboration

### [S370] AusChristmasLighting — pigtail connector plug type comparisons (Ray Wu vs xConnect)
- type: forum
- url: https://auschristmaslighting.com/threads/pigtail-connector-plug-type-comparisons.16968/
- author: AusChristmasLighting community
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251208125019/https://auschristmaslighting.com/threads/pigtail-connector-plug-type-comparisons.16968/  # snapshot 2025-12-08 (snapshot predates accessed date; refresh next verification pass)
- relevance: Ray Wu vs xConnect near-identical mechanically; xConnect single wiring standard + universal store stocking — the connector to standardize on

### [S371] ESP32-S31 — announcement and mass production
- type: news
- url: https://www.espressif.com/en/news/ESP32_S31_Release
- author: Espressif Systems
- published: 2026-03-26 (announcement); mass production declared 2026-07-27 (https://www.espressif.com/en/news/ESP32_S31_Mass_Production)
- accessed: 2026-08-22
- relevance: the S3's heir for the receiver workload — dual-core RISC-V 320 MHz (one core 128-bit SIMD), 512 KB SRAM, 250 MHz DDR-PSRAM support, WiFi 6 (2.4 GHz) + BT 5.4 + 802.15.4, GbE MAC, 60 GPIOs, 8–24-bit parallel LCD bus, ~$4.51 launch price (Hackster). Weeks into mass production as of 2026-08: no devkit ecosystem, no WLED/FastLED port, no independent radio/power measurements — the named re-evaluation trigger for the fleet buy, not a buy today.

### [S372] Espressif longevity commitment — per-chip production end dates
- type: docs
- url: https://www.espressif.com/en/products/longevity-commitment
- author: Espressif Systems
- published: n/a (living page, undated)
- accessed: 2026-08-22
- relevance: guaranteed production — classic ESP32 to 2031-01-01, S3/C3 to 2033, C6 to 2035, C5/P4 to 2037. An S3 fleet buy has ~6.5 years of guaranteed supply; EOL creates no urgency to move.

### [S373] ESP32-C5 — mass production and capabilities
- type: news
- url: https://developer.espressif.com/blog/2025/05/news-esp32c5-mp/
- author: Espressif Systems
- published: 2025-05 (also cnx-software 2025-04-30)
- accessed: 2026-08-22
- relevance: dual-band WiFi 6 (2.4+5 GHz, TWT/OFDMA), BLE 5.0, 802.15.4; single-core RISC-V 240 MHz, 384 KB SRAM, up to 8 MB PSRAM (C5HR8); has RMT and PARLIO but no LCD_CAM and only 29 GPIOs. DevKitC-1 ≈ $15. The 5 GHz escape hatch if 2.4 GHz congestion in a busy room becomes the observed failure mode — at a receiver-peripheral cost vs the S3.

### [S374] ESP32-C5 practical reviews (2025–2026)
- type: article
- url: https://jrattechworks.com/esp32-c5-explained/
- author: JRat TechWorks (2026-03-19); DigiKey FireBeetle 2 C5 review (2025-01-29, https://www.digikey.com/en/maker/blogs/2025/firebeetle-2-esp32-c5-review-dual-band-wi-fi-6-and-solar-charging)
- published: 2026-03-19 / 2025-01-29
- accessed: 2026-08-22
- relevance: consensus reading — C5 is "not the universal default ESP32 choice in 2026": right for congested-RF nodes, not display/LED-heavy work. Deep-sleep 23 µA measured board-level; datasheet WiFi RX ~110 mA @ 2.4 GHz / ~105 mA @ 5 GHz — same order as S3, so streaming power stays LED-dominated. No rigorous third-party latency/jitter benchmark of C5/C6 station-mode streaming vs S3 WiFi 4 found in 2025–26 [NEEDS-VERIFICATION for the WiFi-6 jitter benefit specifically].

### [S375] esp-hosted-mcu — P4 hosted-WiFi architecture
- type: code
- url: https://github.com/espressif/esp-hosted-mcu
- author: Espressif Systems
- license: Apache-2.0
- published: active repo, v2.5.x (2026)
- accessed: 2026-08-22
- relevance: P4's radio story is a two-chip architecture (P4 + C6/C61 co-processor over 4-bit SDIO, ~68 Mbit/s UDP host-RX quoted — enough for 60 fps DDP). Matured through 2025–26 but breaks one-SKU economics; no P4 variant with integrated radio exists.

### [S376] WLED v16 releases
- type: release
- url: https://github.com/wled/WLED/releases
- author: WLED project
- published: v16.0.0 2026-05-03; v16.0.1 2026-07-07
- accessed: 2026-08-22
- relevance: the current production line still ships on ESP-IDF 4.4.8 / arduino-esp32 2.0.18; headline features include segment layering, particle system, and multiple ESP-NOW remotes — mainline LED firmware now leans on ESP-NOW in production. S3 builds ship, but official docs still label S3 "experimental" with a stale summer-2023 marker (documentation lag, kno.wled.ge/basics/compatible-controllers/).

### [S377] WLED next-chip era — IDF5 migration and C6/C5/P4 support
- type: code
- url: https://github.com/wled/WLED/pull/4838
- author: WLED project
- license: EUPL-1.2
- published: PR #4838 (IDF v5 port) merged 2026-07-19; PR #5048 (adds C6/C5/P4 to V5 builds) merged 2026-06-23; status issue #3078 pinned update 2026-07-04
- accessed: 2026-08-22
- relevance: the C6/C5/P4 era formally begins with WLED 17, and is explicitly "absolutely not suitable for production" today — effects/UI/WiFi/PSRAM work, OTA and WLED sync unstable, NTP broken on C5, P4 Ethernet not working; P4 runs with a C6 hosted-WiFi co-processor. The ecosystem argument for S3 holds until this stabilizes.

### [S378] MoonLight v1.0.0 and the ProjectMM pivot
- type: release
- url: https://github.com/MoonModules/MoonLight/releases
- author: MoonModules
- published: v0.6.0 2025-11-07; v0.8.0 (P4 parlio driver) 2026-01-16; v1.0.0 2026-05-06; ProjectMM pivot notice 2026-05 (moonmodules.org)
- accessed: 2026-08-22
- relevance: the high-pixel-count frontier targets S3 and P4 (~130k LEDs claimed with PSRAM; C3 capped at 1024); WLED-MM keeps S3+PSRAM as primary target (v14.7.1 2026-01-13). Confirms and extends the S352 trajectory claim: S3 for today, P4 for the high end.

### [S379] FastLED 2025–2026 releases — parallel-driver maturation
- type: release
- url: https://github.com/FastLED/FastLED/releases
- author: FastLED project
- published: 3.9.9 2025-01 (16-way S3 I2S driver) through 3.10.4 2026-06-16; P4 support 3.10.0 2025-06-16; C5 support 3.10.2 2025-08-22
- accessed: 2026-08-22
- relevance: S3 parallel paths (I2S + RMT5-DMA) read as mature after the 2025 fix series; the P4 LCD/RGB 16-strip driver (issue #2113) is experimental and "untested on hardware." No RP2350 support in any 2025–26 release.

### [S380] ESP-IDF v6.0 release
- type: news
- url: https://developer.espressif.com/blog/2026/03/idf-v6-0-release/
- author: Espressif Systems
- published: 2026-03-24
- accessed: 2026-08-22
- relevance: C5 and C61 graduate to full support; H21/H4 in preview. ESP-NOW component v2.5.3 (~2026-02) "supports all targets," so S3↔C6/C5 mesh interop is a supported configuration — the mesh tier does not lock the fleet to one chip generation.

### [S381] ESP32-C61 modules at ~$2
- type: news
- url: https://www.cnx-software.com/2026/08/04/espressif-esp32-c61-mini-1-1u-wi-fi-6-and-ble-iot-module-2-dollars/
- author: CNX Software
- published: 2026-08-04
- accessed: 2026-08-22
- relevance: WiFi-6 silicon floor price — C61-MINI-1 modules ~$2.14, devkits $9–12; single weak core, 320 KB SRAM: a sensor/bridge tier, not a renderer. Marks where radio cost is heading for future co-processor or gateway roles.

### [S382] QuinLED Dig-Next-2 — 2026 flagship still classic-ESP32
- type: docs
- url: https://quinled.info/dig-next-2/
- author: Quindor (QuinLED)
- published: 2026 (product page)
- accessed: 2026-08-22
- relevance: the leading WLED-adjacent board vendor's 2026 entry flagship remains classic ESP32 (8 MB flash, 2 MB PSRAM), marketed WLED/MoonLight-ready — commercial LED hardware has not moved past classic ESP32, placing the S3 buy ahead of, not behind, the commercial curve.

## Block S400–S449 — RA-09 Hardware: wearable tier

### [S400] todbot — "Speed up CircuitPython LED animations 10x with ulab"
- type: article
- url: https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/
- author: Tod Kurt
- published: 2022-10-21
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260519221054/https://todbot.com/blog/2022/10/21/speed-up-circuitpython-led-animations-10x/  # snapshot 2026-05-19 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20220331190314/https://core-electronics.com.au/videos/the-factory-huge-micropython-speed-up-with-ws2812-leds  # snapshot 2022-03-31 (snapshot predates accessed date; refresh next verification pass)
- relevance: measured ~2x frame-rate gain (10 → ~22 fps) from @micropython.viper on a GlowBit WS2812 matrix; documents viper restrictions

### [S403] CircuitPython board pages — RP2350 boards (Feather RP2350, Plasma 2350 etc.)
- type: docs
- url: https://circuitpython.org/board/adafruit_feather_rp2350/
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260414211530/https://circuitpython.org/board/adafruit_feather_rp2350/  # captured 2026-07-03 (snapshot predates accessed date; refresh next verification pass)
- relevance: confirms ulab is bundled for RP2350-class boards; RP2350 runs CircuitPython roughly 2x faster than RP2040

### [S404] Pixelblaze — language reference and product docs
- type: docs
- url: https://electromage.com/docs/language-reference/
- author: Ben Hencke (ElectroMage)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260209163257/https://electromage.com/docs/language-reference/  # snapshot 2026-02-09 (snapshot predates accessed date; refresh next verification pass)
- relevance: JS-like pattern language compiled off-device (in browser) to instructions executed on ESP32 — closest precedent for host-authored/device-executed patterns

### [S405] Pixelblaze V3 — Crowd Supply campaign page
- type: product
- url: https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3
- author: Ben Hencke (ElectroMage)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260605034712/https://www.crowdsupply.com/hencke-technologies/pixelblaze-v3  # snapshot 2026-06-05 (snapshot predates accessed date; refresh next verification pass)
- relevance: performance claim ~48k pixels/sec on ESP32; bytecode is platform-dependent between v2/v3

### [S406] wled/WLED PR #4570 — "added support for fseq files"
- type: code
- url: https://github.com/wled/WLED/pull/4570
- pinned: wled/WLED@40d8e0ed8f4f2d0bc577e8a087a3117e8d4eca34
- author: Andrejchrcek
- license: EUPL-1.2 (WLED)
- accessed: 2026-07-03
- relevance: FSEQ-from-SD standalone playback merged into WLED (2025) — the bake-and-play portability path

### [S407] Adafruit CircuitPython BLE_File_Transfer library
- type: code
- url: https://github.com/adafruit/Adafruit_CircuitPython_BLE_File_Transfer
- pinned: adafruit/Adafruit_CircuitPython_BLE_File_Transfer@14c0870bc915aba90cf6e8a4002adeb563bc95fe
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
- archive: https://web.archive.org/web/20251107121354/https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf  # snapshot 2025-11-07 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251026033759/https://forum.seeedstudio.com/t/ble-advertising-current-comparison-esp32c3-c6-s3-mg24-nrf52840/287847  # snapshot 2025-10-26 (snapshot predates accessed date; refresh next verification pass)
- relevance: measured cross-chip BLE advertising current; verdict "nRF52840 is by far the best for low current consumption BLE applications"

### [S413] FastLED Wiki — Power notes (setMaxPowerInVoltsAndMilliamps)
- type: docs
- url: https://github.com/FastLED/FastLED/wiki/Power-notes
- author: FastLED project
- license: MIT (FastLED)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260505174835/https://github.com/FastLED/FastLED/wiki/Power-notes  # snapshot 2026-05-05 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260219011254/https://learn.adafruit.com/adafruit-sparkle-motion-mini/overview  # snapshot 2026-02-19 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260425060638/https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels  # snapshot 2026-04-25 (snapshot predates accessed date; refresh next verification pass)
- relevance: 60 mA/px worst-case planning constant ("rule of thumb, not hard science"), 3.7 V LiPo direct drive, brownout caps, wearable strain-relief guidance

### [S418] WLED knowledge base — Settings (Automatic Brightness Limiter)
- type: docs
- url: https://kno.wled.ge/features/settings/
- author: WLED project
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260629193319/https://kno.wled.ge/features/settings/  # snapshot 2026-06-29 (snapshot predates accessed date; refresh next verification pass)
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

### [S422] Nordic nRF54L15 — shipping wearable-tier upgrade
- type: docs
- url: https://www.nordicsemi.com/Products/nRF54L15
- author: Nordic Semiconductor
- published: full-volume production since 2024-12 (product page, accessed 2026-08-22); XIAO nRF54L15 board $9.90 (Seeed, 2025-07-30)
- accessed: 2026-08-22
- relevance: direct shipping upgrade for the W-5 nRF52840 slot — ~2× better power (sub-1 µA sleep; 3.0 µA System ON with 256 KB RAM retention), BT 6.0 Channel Sounding (cm-level node-to-node ranging — a new capability for prop-to-prop distance effects), cheaper boards. nRF54H20 still selective-sampling mid-2026, not buyable.

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
- pinned: aubio/aubio@ad5cf975aed08cc4562dd008cf9f83b12b82ffb8
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
- pinned: CPJKU/madmom@27f032e8947204902c675e5e341a3faf5dc86dae
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
- pinned: mjhydri/BeatNet@81cedd4beeb7235262db80969a0c9ce9a48a0ed4
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
- archive: https://web.archive.org/web/20260701120149/https://python-sounddevice.readthedocs.io/en/0.5.3/ (snapshot predates accessed date; refresh next verification pass)
- relevance: PortAudio binding used by LedFx; latency/blocksize semantics for the capture stage of the budget

### [S459] ITU-R BT.1359-1 — Relative timing of sound and vision
- type: spec
- url: https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- author: ITU-R
- published: 1998-11
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20250903014127/https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260114105355/https://www.tindie.com/products/electromage/pixelblaze-v3-standard-wifi-led-controller/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251003085253/https://docs.ledfx.app/en/latest/howto/dummy_matrix.html (snapshot predates accessed date; refresh next verification pass)
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
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- author: LedFx project
- license: GPL-3.0
- accessed: 2026-07-03
- relevance: direct inspection 2026-07-03: effect tests are HTTP-API smoke tests (set effect, assert JSON), no pixel-output/golden-frame assertions — evidence nobody frame-tests effects

### [S517] FastLED test suite (tests/ directory, inspected via GitHub API)
- type: code
- url: https://github.com/FastLED/FastLED/tree/master/tests
- pinned: FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
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

### [S521] websockets (python-websockets) — sync/threading server
- type: code
- url: https://github.com/python-websockets/websockets
- author: Aymeric Augustin et al.
- license: BSD-3-Clause
- pinned: python-websockets/websockets@fd3f16cc4f57ace08e323a7806f1432e957cb75e
- published: 17.0.1 released 2026-07-31 (PyPI)
- accessed: 2026-08-20
- relevance: the reference RFC 6455/7692 implementation for Python; `websockets.sync.server` is a thread-per-connection server (no asyncio) matching the engine's thread-per-sink model, with a `process_request` hook that serves plain HTTP from the same port; C extension accelerates frame masking; requires Python >=3.11, same floor as pewpew. Evidence for ADR-020's adopt decision.

### [S522] RFC 6455 — The WebSocket Protocol
- type: spec
- url: https://datatracker.ietf.org/doc/html/rfc6455
- author: IETF (Fette, Melnikov)
- published: 2011-12
- accessed: 2026-08-20
- relevance: the protocol itself — sizes ADR-020's rejected hand-roll alternative: the server-side subset pewpew needs (upgrade handshake, unmasked server-to-client frames, ping/pong, close) is small, but close-handshake and fragmentation edge cases are where hand-rolled implementations rot.

### [S523] three.js r186
- type: code
- url: https://github.com/mrdoob/three.js
- pinned: mrdoob/three.js@9b4a2ac29c63ccb43fd51c5661f2f873ac2c39b8
- author: mrdoob and contributors
- license: MIT
- published: r186 tagged 2026-09-24 (npm `three` 0.186.1)
- accessed: 2026-10-22
- relevance: the 3D engine for the studio frontend. r186 is the current release; `WebGLRenderer` defaults to `outputColorSpace = SRGBColorSpace` and `NoToneMapping`, and `TransformControls` and `OrbitControls` ship in `examples/jsm`.

### [S524] three.js manual — WebGPURenderer
- type: docs
- url: https://threejs.org/manual/pages/webgpurenderer.html
- author: three.js project
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260928222951/https://threejs.org/manual/pages/webgpurenderer.html
- relevance: states the renderer "is still in an experimental state" and that `ShaderMaterial`, `RawShaderMaterial` and `onBeforeCompile()` are not supported in `WebGPURenderer`. The studio's LED shader is a `ShaderMaterial`, so this rules WebGPURenderer out.

### [S525] three.js manual — Color management
- type: docs
- url: https://threejs.org/manual/pages/color-management.html
- author: three.js project
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261010141505/https://threejs.org/manual/pages/color-management.html
- relevance: `ShaderMaterial` must do its own output colour-space conversion; textures tagged `SRGBColorSpace` are decoded on sampling. The basis for sending display-ready sRGB bytes unchanged to the page.

### [S526] React Three Fiber (pmndrs/react-three-fiber)
- type: code
- url: https://github.com/pmndrs/react-three-fiber
- pinned: pmndrs/react-three-fiber@d74622ea8ed717f7212d7e19d65ff3e325508389
- author: Poimandres (pmndrs)
- license: MIT
- published: v9.8.2 (2026-10-15 per GitHub releases)
- accessed: 2026-10-22
- relevance: the React renderer for three.js (docs: https://r3f.docs.pmnd.rs/getting-started/introduction). v9.8.2 peers `react >=19 <19.4` and `three >=0.156` (npm registry). Matches the React 19 stack of the maintainer's other apps. A v10 alpha exists (v10.0.0-alpha.6, 2026-10-17), so the studio pins `^9`.

### [S527] glTF 2.0 specification (Khronos)
- type: spec
- url: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- author: Khronos Group
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261008114737/https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- relevance: defines the binary GLB container and per-node `extras`. The studio serves each fixture type as a deterministic GLB whose nodes carry `glow` and `gain` in `extras`.

## Block S550–S599 — RA-12 Prior art & control plane

### [S550] WLED docs — JSON API
- type: docs
- url: https://kno.wled.ge/interfaces/json-api/
- author: WLED project (Aircoookie et al.)
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251219022207/https://kno.wled.ge/interfaces/json-api/ (snapshot predates accessed date; refresh next verification pass)
- relevance: canonical spec of WLED's single-JSON-state control model: state/seg objects, presets, playlists, fxdata metadata, per-LED `i` writes and buffer limits.

### [S551] WLED docs — WebSocket interface
- type: docs
- url: https://kno.wled.ge/interfaces/websocket/
- author: WLED project
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20251219071936/https://kno.wled.ge/interfaces/websocket/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251224021119/https://www.home-assistant.io/integrations/wled (snapshot predates accessed date; refresh next verification pass)
- relevance: reference mapping of an LED engine to smart-home entities (segments→lights, presets/playlists/palettes→selects, speed/intensity→numbers); local-push via WebSocket with 10 s polling fallback.

### [S554] WLED docs — Presets (and timed presets)
- type: docs
- url: https://kno.wled.ge/features/presets/
- author: WLED project
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260116004106/https://kno.wled.ge/features/presets/ (snapshot predates accessed date; refresh next verification pass)
- relevance: preset storage model (/presets.json, 250 slots, preset=any API command), playlist-in-preset structure, 8 timer slots + sunrise/sunset, boot preset, LittleFS write-blocking caveats.

### [S555] Chromatik Guide — OSC
- type: docs
- url: https://chromatik.co/guide/osc/
- author: Heron Arts / Mark Slee
- published: n/a (living doc)
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260218122037/https://chromatik.co/guide/osc/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260521061924/https://github.com/simap/pixelblaze/tree/v3 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260624190621/https://kno.wled.ge/basics/getting-started/  # snapshot 2026-06-24 (snapshot predates accessed date; refresh next verification pass)
- relevance: WLED's standard field-update paths — browser-based initial flash (install.wled.me) and integrated OTA update from the device web UI — the update precedent pewpew's receiver firmware inherits (completeness-critique sweep 3)

### [S755] ESP Web Tools (ESPHome project)
- type: docs
- url: https://esphome.github.io/esp-web-tools/
- author: ESPHome / Open Home Foundation
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260622052935/https://esphome.github.io/esp-web-tools/  # snapshot 2026-06-22 (snapshot predates accessed date; refresh next verification pass)
- relevance: ecosystem-standard browser flashing (Web Serial) with Improv WiFi provisioning; powers the WLED/Tasmota one-click installers — the install/recovery path for pewpew receiver firmware (completeness-critique sweep 3)

### [S756] ESP-IDF documentation — Over The Air Updates (OTA), ESP32-S3
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html
- author: Espressif Systems
- accessed: 2026-07-03
- archive: https://web.archive.org/web/20260304210916/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html  # snapshot 2026-03-04 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260511093720/https://github.com/zackelia/wled-matter-bridge  # snapshot 2026-05-11 (snapshot predates accessed date; refresh next verification pass)
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

### [S761] Adafruit — Mini Skinny NeoPixel RGBW LED strip, 60 LED/m, 1 m (product 4914)
- type: product
- url: https://www.adafruit.com/product/4914
- author: Adafruit Industries
- accessed: 2026-10-30
- archive: https://web.archive.org/web/20261023190744/https://www.adafruit.com/product/4914  # snapshot 2026-10-23
- relevance: "60 LEDs-per-meter", "60 NeoPixel-compatible LEDs" in "a 1-meter long tube": the pixel count of a 1 m strip equals its per-meter density, so the pitch is length / count (1/60 m), not length / (count − 1). The v0.2.5 bench strip; the room map's pitch default rests on this.

### [S762] Adafruit NeoPixel Überguide — NeoPixel strips
- type: docs
- url: https://learn.adafruit.com/adafruit-neopixel-uberguide/neopixel-strips
- author: Adafruit Industries (Learning System)
- accessed: 2026-10-30
- archive: https://web.archive.org/web/20260815041739/https://learn.adafruit.com/adafruit-neopixel-uberguide/neopixel-strips  # snapshot 2026-08-15 (snapshot predates accessed date; refresh next verification pass)
- relevance: strips are sold by LEDs per meter (30, 60, 144); "Some batches of 144 pixel strip don't have pads between the LEDs", so cut pads normally sit between LEDs and each LED sits inside its own pitch-long segment; "The pixel spacing across these joins is usually 2-3 millimeters different than the rest" (half-meter joins), why a measured `pitch` can override the default.

### [S763] Fly.io docs — Request headers
- type: docs
- url: https://docs.fly.io/networking/request-headers
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261023033611/https://docs.fly.io/networking/request-headers
- relevance: `Fly-Client-IP` carries the client address; the key for the studio's per-IP limits.

### [S764] Fly.io docs — Pricing
- type: docs
- url: https://docs.fly.io/about/pricing
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260927113403/https://docs.fly.io/about/pricing/
- relevance: shared-cpu-1x 256 MB about $2.19/month, 512 MB about $3.69/month, outbound bandwidth $0.02/GB in North America and Europe. Egress is the dominant cost of streaming frames, so the page stops frames while its tab is hidden.

### [S765] Fly.io docs — Volumes overview
- type: docs
- url: https://docs.fly.io/volumes/overview
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261107042847/https://docs.fly.io/volumes/overview
- relevance: a volume attaches to one Machine and is not replicated; the docs advise at least two volumes per app. Why share links do not live on a volume.

### [S766] Fly.io docs — Tigris object storage
- type: docs
- url: https://docs.fly.io/tigris
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261010214723/https://docs.fly.io/tigris
- relevance: `fly storage create` provisions an S3-compatible bucket billed through Fly. The considered-and-rejected store for share links: workable, but a second service for write-once rows a Neon database already holds.

### [S767] Fly community — proxy resets a stalled HTTP stream after 30 s
- type: forum
- url: https://community.fly.io/t/fly-proxy-resets-a-stalled-http-stream-after-30s-on-edge-and-flycast-hops-http-options-idle-timeout-has-no-effect/28755
- author: Fly.io staff reply (2026-10-08 per the A1 planning report)
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261008004946/https://community.fly.io/t/fly-proxy-resets-a-stalled-http-stream-after-30s-on-edge-and-flycast-hops-http-options-idle-timeout-has-no-effect/28755
- relevance: a fixed 30 s `TCP_USER_TIMEOUT` resets connections whose receive window stays at zero. A client that cannot keep up gets cut off, so the studio drops frames and never queues them.

### [S768] websockets docs — Deploy and server FAQ
- type: docs
- url: https://websockets.readthedocs.io/en/stable/deploy/index.html
- author: Aymeric Augustin
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260707111813/https://websockets.readthedocs.io/en/stable/deploy/index.html
- relevance: "Don't scale with threads. Scale only with processes." The server FAQ (https://websockets.readthedocs.io/en/stable/faq/server.html, archive https://web.archive.org/web/20260714231458/https://websockets.readthedocs.io/en/stable/faq/server.html) calls serving HTTP "out of scope". Both bound the sync server's fit for public traffic (ADR-024).

### [S769] FastAPI
- type: code
- url: https://github.com/fastapi/fastapi
- pinned: fastapi/fastapi@69ddc2badf9da1123bba4d360225ae6b085985f6
- author: Sebastián Ramírez and contributors
- license: MIT
- published: 0.161.1 (2026-10-22 per GitHub releases)
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261005084951/https://fastapi.tiangolo.com/advanced/websockets/ (websocket docs page)
- relevance: async web framework with websocket endpoints (docs: https://fastapi.tiangolo.com/advanced/websockets/), request-body REST routes and generated OpenAPI that feeds the frontend's orval client. The framework the maintainer's other fly.io apps run.

### [S770] uvicorn
- type: code
- url: https://github.com/encode/uvicorn
- pinned: encode/uvicorn@3eb9a9ab9af69005c687728097461c1fd2a95db9
- author: Encode
- license: BSD-3-Clause
- published: 0.54.0 (2026-09-25 per GitHub releases)
- accessed: 2026-10-22
- relevance: ASGI server for FastAPI; `uvicorn --factory` runs the studio app factory. Its reloader uses watchfiles, already an ADOPT in architecture §9 (S519).

### [S771] pydantic
- type: code
- url: https://github.com/pydantic/pydantic
- pinned: pydantic/pydantic@b2212c787fb5c73386dc770681ec49cd09da8e73
- author: Samuel Colvin and contributors
- license: MIT
- published: v2.14.1 (2026-10-11 per GitHub releases)
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261010131530/https://pydantic.dev/docs/validation/latest/get-started/ (docs)
- relevance: validates the arrangement and catalog formats (discriminated unions on `kind`, JSON Schema export) and is the model layer FastAPI uses, so one library serves the file format and the HTTP API.

### [S772] psycopg 3
- type: code
- url: https://github.com/psycopg/psycopg
- pinned: psycopg/psycopg@a67654d1e7afbf9b3a619557838f62de1c790e7c
- author: Daniele Varrazzo and contributors
- license: LGPL-3.0 (psycopg PyPI 3.3.6 lists no license string; GitHub reports LGPL-3.0)
- published: 3.3.6 uploaded 2026-09-18 (PyPI)
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261005133414/https://www.psycopg.org/psycopg3/docs/ (docs)
- relevance: PostgreSQL driver for the Neon-backed share store. The LGPL licence is a posture note: pewpew imports it unmodified as a separate installed package in the optional `studio` extra, never vendors it (inference from ADR-012's policy of not copying copyleft code).

### [S773] Neon docs — Introduction
- type: docs
- url: https://neon.com/docs/introduction
- author: Neon
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261021194024/https://neon.com/docs/introduction
- relevance: Neon is serverless Postgres; the managed database the maintainer's other fly.io apps use, so no volume or second storage service is needed for share links.

### [S774] Neon docs — Connection pooling
- type: docs
- url: https://neon.com/docs/connect/connection-pooling
- author: Neon
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260824215936/https://neon.com/docs/connect/connection-pooling
- relevance: pooled connection strings for short-lived clients; informs how the studio store opens psycopg connections (one machine, few connections).

### [S775] manifold (elalish/manifold) and manifold3d
- type: code
- url: https://github.com/elalish/manifold
- pinned: elalish/manifold@ce50d78021d64507f89e8c9fc2c2e51018117857
- author: Emmett Lalish and contributors
- license: Apache-2.0
- published: v3.5.4 (2026-09-25); PyPI `manifold3d` 3.5.4 (https://pypi.org/project/manifold3d/)
- accessed: 2026-10-22
- relevance: robust CSG over triangle meshes with Python bindings. Builds the bar's housing, T-slot, flat-cut diffuser and end caps server-side into a deterministic GLB (the determinism claim is the plan's design intent, not tested here).

### [S776] Pyodide
- type: code
- url: https://github.com/pyodide/pyodide
- pinned: pyodide/pyodide@b1e4fcc2488962f6360a97f19b9982d6fdb5d16f
- author: Pyodide contributors
- license: MPL-2.0
- published: 314.0.7 (2026-09-14 per GitHub releases)
- accessed: 2026-10-22
- relevance: CPython compiled to WebAssembly, the in-browser alternative to server rendering. Rejected for the hosted studio; see S777-S779 for what it costs.

### [S777] Pyodide 314 release post
- type: article
- url: https://blog.pyodide.org/posts/314-release/
- author: Pyodide team
- published: 2026-06-09
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260615165942/https://blog.pyodide.org/posts/314-release/
- relevance: Pyodide 314.0 runs Python 3.14.2, newer than pewpew's >=3.11 floor, so an in-browser engine is feasible; the cost is download and speed, not compatibility.

### [S778] Pyodide roadmap
- type: docs
- url: https://pyodide.org/en/stable/project/roadmap.html
- author: Pyodide team
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20260924192437/https://pyodide.org/en/stable/project/roadmap.html
- relevance: states 4-5 s initialisation and "3x to 5x slower than native Python"; the text predates recent releases, so treat the figures as stale and a rough bound only. Phone startup benchmarks: not found.

### [S779] Pyodide 314.0.7 files on jsDelivr
- type: product
- url: https://cdn.jsdelivr.net/npm/pyodide@314.0.7/
- author: jsDelivr (CDN of the Pyodide npm package)
- published: 2026-09-14
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261107042910/https://cdn.jsdelivr.net/npm/pyodide@314.0.7/
- relevance: `pyodide.asm.wasm` is 9,598,218 bytes uncompressed and 3,438,516 bytes brotli-encoded on the wire; `python_stdlib.zip` is 2,545,637 bytes (a zip; no further compression). Measured 2026-10-22 and re-checked 2026-11-06 with `curl -sI -H 'Accept-Encoding: identity'` (content-length) and `curl -s -H 'Accept-Encoding: br' -o /dev/null -w '%{size_download}'`. The directory listing's size column is raw file size in MiB (9.15 MB = 9,598,218 B; 2.43 MB = 2,545,637 B), not transfer size; the jsDelivr data API reports the same raw bytes. The directory URL returns 403 to a plain request; the files resolve individually. The numpy wheel (about 2.9 MB) is from the A1 planning report, `docs/studio/planning/2026-10-22-a1-flyio-hosting-and-share-links.md`.

### [S780] OWASP Session Management Cheat Sheet
- type: docs
- url: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- author: OWASP
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261016142133/https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- relevance: identifiers should carry at least 64 bits of entropy from a cryptographic generator. The studio's share ids are 128 bits; (inference) they are content hashes, so a link is guessable only by someone who can reproduce the exact content; treat the link as a capability for public data, not a secret.

### [S781] Fly.io docs — fly.toml app configuration reference
- type: docs
- url: https://docs.fly.io/reference/configuration
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261023033435/https://docs.fly.io/reference/configuration
- relevance: `auto_stop_machines`, `auto_start_machines`, `min_machines_running`, concurrency `type` and `soft_limit`, and `[[http_service.checks]]` health checks. The settings the studio's `fly.toml` uses.

### [S782] Fly.io docs — Fly Proxy autostop/autostart
- type: docs
- url: https://docs.fly.io/reference/fly-proxy-autostop-autostart
- author: Fly.io
- accessed: 2026-10-22
- archive: https://web.archive.org/web/20261023033554/https://docs.fly.io/reference/fly-proxy-autostop-autostart
- relevance: a Machine alone in its region stops only when it has "no traffic (a load of 0)". How an open websocket counts toward load is not documented (not found), so the studio adds its own idle-session timeout.

### [S783] PEP 387 — Backwards Compatibility Policy
- type: spec
- url: https://peps.python.org/pep-0387/
- author: Benjamin Peterson
- accessed: 2026-11-07
- archive: https://web.archive.org/web/20261024201249/https://peps.python.org/pep-0387/  # snapshot 2026-10-24 (snapshot predates accessed date; refresh next verification pass)
- relevance: incompatible changes go through a warning first ("Add a warning to the current main branch", naming the release the change becomes default), a wait of at least two minor versions, then removal — the shape of the `--room` deprecation window, shortened to one release

### [S784] MDN — Cross-Origin Resource Sharing (CORS), simple requests
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS
- author: MDN contributors
- accessed: 2026-11-08
- archive: https://web.archive.org/web/20261101205044/https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS
- relevance: a POST whose Content-Type is `application/x-www-form-urlencoded` is a simple request and triggers no preflight; an HTML `<form>` can already submit such a request to any origin, so a server need not opt in to receive it. The Gallery's share POST is that request and sends no CORS headers.

### [S785] Chrome for Developers — Local Network Access
- type: docs
- url: https://developer.chrome.com/blog/local-network-access
- author: Chrome team
- accessed: 2026-11-08
- archive: https://web.archive.org/web/20261025205432/https://developer.chrome.com/blog/local-network-access
- relevance: a local network request is any request from the public network to a local or loopback address, and needs the user's permission; in Chrome 138 the prompt covers `fetch()`, subresource loading and subframe navigation (the page does not mention top-level navigations or form submissions). A Gallery that fetched from the LAN engine would hit this prompt.

### [S786] RFC 9110 — HTTP Semantics, section 15.4.4 (303 See Other)
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc9110#section-15.4.4
- author: IETF (Fielding, Nottingham, Reschke)
- published: 2022-06
- accessed: 2026-11-08
- archive: https://web.archive.org/web/20260520194653/https://www.rfc-editor.org/rfc/rfc9110
- relevance: 303 is "primarily used to allow the output of a POST action to redirect the user agent to a different resource", which the user agent retrieves with GET; the share POST answers 303 to `/a/{id}` so the new tab shows a bookmarkable page.

### [S787] MDN — rel="noreferrer"
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noreferrer
- author: MDN contributors
- accessed: 2026-11-08
- archive: https://web.archive.org/web/20261104015708/https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noreferrer
- relevance: `noreferrer` on `<a>`, `<area>` and `<form>` omits the `Referer` header when fetching the target and implies `noopener`; the Console's publish form uses it so the Gallery never sees the Console's LAN address.

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
- archive: https://web.archive.org/web/20260319154338/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251009212258/https://dl.ifip.org/db/conf/wons/wons2025/1571077625.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260727054030/https://www2.compute.dtu.dk/~xefa/files/conf/2023-blacksea-eps-now.pdf
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
- archive: https://web.archive.org/web/20260724231629/https://standards.ieee.org/ieee/802.11/7028/
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
- archive: https://web.archive.org/web/20260727054048/https://gitlab.com/painlessMesh/painlessMesh/-/work_items/217
- relevance: best available field data on painlessMesh scaling: 36 nodes OK,
  26/50 visible at 50 nodes, 0/72 at 72 nodes, with free heap remaining —
  failure at exactly pewpew's target fleet size.

### [S852] painlessMesh issue #490 — "Maximum number of nodes"
- type: forum
- url: https://gitlab.com/painlessMesh/painlessMesh/-/issues/490
- author: painlessMesh issue reporter (60-node build targeting 200)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727054116/https://gitlab.com/painlessMesh/painlessMesh/-/work_items/490
- relevance: corroborating scaling report: 40–44 of 60 nodes stable, older
  nodes drop as new ones join; ~1200-byte subConnectionJson topology payload;
  200-node question unanswered by maintainers.

### [S853] ESP-IDF Programming Guide — ESP-WIFI-MESH API guide
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-guides/esp-wifi-mesh.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251118072742/https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-guides/esp-wifi-mesh.html (snapshot predates accessed date; refresh next verification pass)
- relevance: authoritative description of tree topology, softAP+STA node
  roles, router-RSSI root election (90% vote threshold), fixed-root/no-router
  mode, and vendor performance figures (100-device test, 6 layers × 6
  downstream, per-hop delay 10–30 ms, healing <10 s root / <5 s child).

### [S854] ESP-FAQ — ESP-WIFI-MESH Application Framework
- type: docs
- url: https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/wifi-mesh-development-framework.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260601145155/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/wifi-mesh-development-framework.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260727054147/https://docs.silabs.com/btmesh/latest/btmesh-11-network-performance/05-summary
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
- archive: https://web.archive.org/web/20260103131441/https://arxiv.org/abs/1910.03345 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260226192136/https://www.bluetooth.com/blog/mesh-in-large-scale-networks/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260502090443/https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/api-guides/openthread.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260524010739/https://www.silabs.com/documents/public/application-notes/an1142-mesh-network-performance-comparison.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260728010419/https://documentation.meraki.com/Wireless/Design_and_Configure/Architecture_and_Best_Practices/Approximating_Maximum_Clients_per_Access_Point
- relevance: theoretical association limits per radio (128 for Wi-Fi 5 W1,
  512 for Wi-Fi 6) with explicit vendor caveat that real-world limits are
  "far lower" and theoretical maxima are not design targets — grounds the
  50-vs-150-station judgment for a single portable AP.

### [S870] 7SIGNAL — How to Determine Maximum Clients per Access Point
- type: article
- url: https://www.7signal.com/news/blog/how-to-determine-clients-per-ap
- author: 7SIGNAL
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728010445/https://www.7signal.com/blog/how-to-determine-clients-per-ap
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
- archive: https://web.archive.org/web/20260715150711/https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/
- relevance: ETSI EN 300 220 sub-band duty-cycle table (0.1%/1%/10% at
  868 MHz) and TTN fair-use policy (30 s uplink airtime/day) — the
  regulatory arithmetic that disqualifies LoRa at 10 Hz.

### [S874] The Things Network docs — Limitations
- type: docs
- url: https://www.thethingsnetwork.org/docs/lorawan/limitations/index.html
- author: The Things Network / The Things Industries
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727054220/https://www.thethingsnetwork.org/docs/lorawan/limitations/index.html
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
- archive: https://web.archive.org/web/20260727054251/https://epubs.siam.org/doi/10.1137/0150098
- relevance: the foundational firefly-sync model — proves all-to-all pulse-coupled integrate-and-fire oscillators converge to synchrony from almost all initial conditions; basis of every timestamp-free phase-sync scheme considered for pewpew's mesh tier. Author PDF: https://www.stevenstrogatz.com/articles/synchronization-of-pulse-coupled-biological-oscillators

### [S901] Werner-Allen et al. — Firefly-Inspired Sensor Network Synchronicity with Realistic Radio Effects (RFA)
- type: article
- url: https://mdw.la/papers/firefly-sensys05.pdf
- author: Geoffrey Werner-Allen, Geetika Tewari, Ankit Patel, Matt Welsh, Radhika Nagpal
- published: 2005 (ACM SenSys '05)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20250318100936/https://mdw.la/papers/firefly-sensys05.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250426184746/http://bitsavers.trailing-edge.com/pdf/xerox/parc/techReports/CSL-89-1_Epidemic_Algorithms_for_Replicated_Database_Maintenance.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260728010531/https://inria.hal.science/inria-00609399v1
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
- archive: https://web.archive.org/web/20250527141518/https://dl.acm.org/doi/10.1109/TSE.1983.236733 (snapshot predates accessed date; refresh next verification pass)
- relevance: version vectors — per-writer counters that detect (rather than arbitrate) concurrent updates; cited to show why they are overkill/oversized for pewpew's 11-byte single-writer state.

### [S910] RFC 6206 — The Trickle Algorithm
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc6206.html
- author: P. Levis, T. Clausen, J. Hui, O. Gnawali, J. Ko (IETF ROLL WG)
- published: 2011-03
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728010613/https://www.rfc-editor.org/rfc/rfc6206.html
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
- archive: https://web.archive.org/web/20260728010728/https://www.rfc-editor.org/rfc/rfc1982.html
- relevance: defines wraparound-safe comparison of fixed-width monotonic counters (half-range window) — the correct comparison rule for pewpew's 1–2-byte parameter epoch field.

### [S913] Fatès — A Guided Tour of Asynchronous Cellular Automata
- type: article
- url: https://arxiv.org/pdf/1406.0792
- author: Nazim Fatès
- published: 2014 (Journal of Cellular Automata; arXiv:1406.0792)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251211075327/https://arxiv.org/pdf/1406.0792 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250914150754/https://cacm.acm.org/research/amorphous-computing/ (snapshot predates accessed date; refresh next verification pass)
- relevance: foundational treatment of computing over "vast numbers of unreliable, locally communicating simple devices" with no global clock; the gradient/diffusion-wave primitive is pewpew's robust alternative to literal CA rules for neighbor-propagated waves.

### [S916] Wertheimer / Korte — apparent motion (beta movement) timing
- type: article
- url: https://en.wikipedia.org/wiki/Korte%27s_third_law_of_apparent_motion
- author: Max Wertheimer (1912); Adolf Korte (1915); summarized via secondary references
- published: 1912/1915 (historical); accessed via encyclopedic summary 2026-07-09
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251205094841/https://en.wikipedia.org/wiki/Korte%27s_third_law_of_apparent_motion (snapshot predates accessed date; refresh next verification pass)
- relevance: bounds the perceptual window for smooth apparent motion between discrete lights (~30–400 ms inter-element interval, optimal ~60 ms) — the basis for the claim that 10 Hz (100 ms/step) inter-group wave propagation reads as coherent motion. Primary-source figures flagged where derived from secondary summaries.

### [S917] Maróti, Kusy, Simon & Lédeczi — The Flooding Time Synchronization Protocol (FTSP)
- type: article
- url: https://www.math.u-szeged.hu/tagok/mmaroti/okt/2009o/ftsp.pdf
- author: Miklós Maróti, Branislav Kusy, Gyula Simon, Ákos Lédeczi
- published: 2004 (ACM SenSys '04)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727054359/https://www.math.u-szeged.hu/tagok/mmaroti/okt/2009o/ftsp.pdf
- relevance: canonical flooding time-sync with MAC-layer timestamping + skew estimation; ~1.48 µs single-hop, ~1 µs average per-hop, robust to node/link failure — the reference for "cheap flooding absolute clock", and the illustration of why ESP-NOW (no app-level MAC TX timestamp) cannot reach µs-class this way.

### [S918] u-blox — Precision Timing / 1PPS accuracy specifications
- type: docs
- url: https://content.u-blox.com/sites/default/files/products/documents/Timing_AppNote_(GPS.G6-X-11007).pdf
- author: u-blox AG
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260320101858/https://content.u-blox.com/sites/default/files/products/documents/Timing_AppNote_%28GPS.G6-X-11007%29.pdf (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260319154338/https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/esp-now.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260727053503/https://github.com/espressif/esp-idf/issues/10341
- relevance: Documented ESP-NOW+STA coexistence pitfalls: broken before IDF 5.0 (staff: "this issue is fixed in IDF 5.0 and later version"; workaround on 4.x: init ESP-NOW before AP connect); staff claim that a STA-connected node "will only receive the broadcast packet whose bssid is equal to the associated AP bssid" (disputed in-thread by reporter).

### [S1003] ESP-IDF Programming Guide — Over The Air Updates (OTA), ESP32-S3, latest/v5.x
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/ota.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260312072212/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/ota.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260727053534/https://gitlab.com/painlessMesh/painlessMesh/-/work_items/387
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
- archive: https://web.archive.org/web/20260213110244/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html (snapshot predates accessed date; refresh next verification pass)
- relevance: Key-value config store in its own flash partition: namespaces, power-fail safety ("one should be able to power off the device at any point"), built-in wear levelling, optional NVS encryption. Basis for config-vs-firmware separation.

### [S1011] ESP-IDF Programming Guide — Miscellaneous System APIs: MAC addresses (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260303122027/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html (snapshot predates accessed date; refresh next verification pass)
- relevance: Base MAC is "pre-programmed into the ESP32-S3 eFuse in the factory during production"; esp_read_mac()/esp_efuse_mac_get_default(); per-interface MACs derived from base MAC; custom base MAC possible via esp_base_mac_addr_set(). Basis for zero-touch MAC-derived node identity.

### [S1012] Random Nerd Tutorials — "ESP32: ESP-NOW Web Server Sensor Dashboard (ESP-NOW + Wi-Fi)"
- type: article
- url: https://randomnerdtutorials.com/esp32-esp-now-wi-fi-web-server/
- author: Rui Santos / Random Nerd Tutorials
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728005547/https://randomnerdtutorials.com/esp32-esp-now-wi-fi-web-server/
- relevance: The widely-cited single-chip gateway recipe: receiver in WIFI_AP_STA runs ESP-NOW + web server; "The ESP32 sender boards must use the same Wi-Fi channel of the receiver board"; senders scan for the gateway's SSID channel and apply it with esp_wifi_set_channel(). Documents the channel-pinning pattern and its ordering pitfall (connect WiFi before registering peers).

### [S1013] ESP-IDF Programming Guide — App Image Format / esp_app_desc_t (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/app_image_format.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260513185641/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/app_image_format.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260725153443/https://www.home-assistant.io/integrations/zha
- relevance: The serial-attached radio-coordinator convention pewpew's dongle gateway mirrors: "A hardware radio adapter (typically a USB dongle) that plugs directly into the same computer" — host software speaks a serial protocol to a dedicated radio SoC (EmberZNet EZSP, TI Z-Stack ZNP, deCONZ, XBee families).

## Block S1050–S1099 — RA-18 Wearable bridging

### [S1050] Novel Bits — "Maximum Data Size in a Bluetooth LE Advertising Packet"
- type: article
- url: https://novelbits.io/maximum-data-bluetooth-advertising-packet-ble/
- author: Novel Bits (Mohammad Afaneh)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251006021903/https://novelbits.io/maximum-data-bluetooth-advertising-packet-ble/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260510231003/https://docs.nordicsemi.com/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/CURRENT/parameters.i_radio.html (snapshot predates accessed date; refresh next verification pass)
- relevance: official radio currents — IRADIO_RX0 (RX @1 Mbps BLE, HFXO, DCDC) = 6.26 mA typ; IRADIO_TX1 (0 dBm, DCDC) = 6.40 mA typ; anchors the observer-role duty-cycle power math

### [S1053] ESP-IDF Programming Guide — RF Coexistence (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/coexist.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260228151623/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/coexist.html (snapshot predates accessed date; refresh next verification pass)
- relevance: S3 has one 2.4 GHz RF module time-sliced between WiFi and BLE; coexistence table marks WiFi-STA + BLE advertising stable ("Y") but ESP-NOW RX only "supported and the performance is stable in STA mode, otherwise not supported"; SoftAP + BLE marked unstable ("C1") — decides the bridge's WiFi mode

### [S1054] ESP-IDF Programming Guide — ESP-NOW API reference (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_now.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710145255/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_now.html
- relevance: ESP-NOW v1 250 B / v2 1470 B payloads; connectionless power save via esp_now_set_wake_window() + esp_wifi_connectionless_module_set_wake_interval(); "Sleep is supported only when ESP32-S3 is configured as station"

### [S1055] CircuitPython core docs — `_bleio` shared bindings
- type: docs
- url: https://docs.circuitpython.org/en/latest/shared-bindings/_bleio/index.html
- author: Adafruit / CircuitPython project
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260527030025/https://docs.circuitpython.org/en/latest/shared-bindings/_bleio/index.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260319185803/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/low-power-mode/low-power-mode-wifi.html (snapshot predates accessed date; refresh next verification pass)
- relevance: measured (shielded-box) modem-sleep averages on ESP32-S3: ~19.5–20.7 mA with DFS on (DTIM 10–1), ~38–40 mA without DFS, peaks ~113 mA during radio activity — the realistic floor for any duty-cycled WiFi/ESP-NOW receiver on S3

### [S1059] Nordic DevZone — "nRF52 DK — 20 ms non connectable advertising interval"
- type: forum
- url: https://devzone.nordicsemi.com/f/nordic-q-a/15372/nrf52-dk---20ms-non-connectable-advertising-interval
- author: Nordic Semiconductor support / community
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727053639/https://devzone.nordicsemi.com/f/nordic-q-a/15372/nrf52-dk---20ms-non-connectable-advertising-interval
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
- archive: https://web.archive.org/web/20251121042516/https://github.com/adafruit/circuitpython/issues/3119 (snapshot predates accessed date; refresh next verification pass)
- relevance: historical evidence that unfiltered long-running scans put large allocations (64 KB-class) on the CircuitPython heap; motivates prefix-filtered, bounded-buffer, short-burst scanning in a render loop

### [S1063] Nordic Semiconductor — Enhanced ShockBurst (ESB), nRF Connect SDK protocol docs
- type: docs
- url: https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/esb/index.html
- author: Nordic Semiconductor
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260526040240/https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/esb/index.html (snapshot predates accessed date; refresh next verification pass)
- relevance: ESB is Nordic-proprietary 2.4 GHz (interop limited to nRF5/nRF52/nRF53/nRF24 devices), delivered as an nRF Connect SDK library requiring exclusive radio-resource access — no ESP32 interop and no CircuitPython exposure; disqualifies it as pewpew's wearable link

### [S1064] The Things Network docs — "Duty Cycle" (EU868 regulatory limits)
- type: docs
- url: https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/
- author: The Things Network
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260715150711/https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/
- relevance: EU 868 MHz ISM band imposes ~1% transmit duty cycle (864 s airtime/day) on LoRa devices — a continuous ~10 Hz state broadcast is regulatorily impossible; kills LoRa for group-state distribution

### [S1065] ESP-IDF Programming Guide — RF Coexistence (ESP32-C6)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-guides/coexist.html
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260410144209/https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-guides/coexist.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260620122714/https://docs.wokwi.com/guides/esp32-wifi (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260214045143/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/tools/qemu.html (snapshot predates accessed date; refresh next verification pass)
- relevance: QEMU is a first-class IDF tool — `idf.py qemu monitor` / `idf.py qemu gdb`, prebuilt binaries for Linux/macOS/Windows; S3 emulation of "CPU, memory, and several peripherals"; virtual framebuffer, eFuse/secure-boot emulation

### [S1106] espressif/esp-toolchain-docs — QEMU README (chip/peripheral coverage)
- type: docs
- url: https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md
- author: Espressif
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728005743/https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md
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
- archive: https://web.archive.org/web/20251011204153/https://renode.readthedocs.io/en/latest/tutorials/ble-simulation.html (snapshot predates accessed date; refresh next verification pass)
- relevance: shared wireless-medium model (`BLEMedium`), multi-machine radio linking, Python packet-interception hooks; canonical demo = two nRF52840s running Zephyr BLE — Renode's multi-node radio sim is real but nRF-centric

### [S1110] Renode docs — supported boards
- type: docs
- url: https://renode.readthedocs.io/en/latest/introduction/supported-boards.html
- author: Antmicro
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260724003113/https://renode.readthedocs.io/en/latest/introduction/supported-boards.html
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
- archive: https://web.archive.org/web/20260727053716/https://github.com/wokwi/wokwi-features/issues/446
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
- archive: https://web.archive.org/web/20260701130032/https://docs.espressif.com/projects/pytest-embedded/en/latest/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260702205830/https://docs.espressif.com/projects/esp-idf/en/latest/esp32/contribute/esp-idf-tests-with-pytest.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250615070344/https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners (snapshot predates accessed date; refresh next verification pass)
- relevance: self-hosted runners give hardware/OS control and USB access, route via labels, poll GitHub over HTTPS; GitHub recommends them only for private repos (fork PRs can execute arbitrary code on the runner)

### [S1121] Ferrous Systems — "Running hardware-in-the-loop tests on GitHub Actions"
- type: article
- url: https://ferrous-systems.com/blog/gha-hil-tests/
- author: Ferrous Systems
- published: 2021-03-17
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260317053019/https://ferrous-systems.com/blog/gha-hil-tests/ (snapshot predates accessed date; refresh next verification pass)
- relevance: canonical HIL-on-GHA writeup — nRF52840-DK on a Pi 4 self-hosted runner, probe-run/defmt-test `cargo test` on target; two-repo public-proxy→private-runner pattern + merge-queue approval to keep untrusted PRs off hardware

### [S1122] The Good Penguin — "Automated Testing with GitHub Actions, pytest and a Board Farm"
- type: article
- url: https://www.thegoodpenguin.co.uk/blog/automated-testing-with-github-actions-pytest-and-a-board-farm/
- author: The Good Penguin (consultancy blog)
- published: 2023-03-17
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728005814/https://www.thegoodpenguin.co.uk/blog/automated-testing-with-github-actions-pytest-and-a-board-farm/
- relevance: working board-farm CI: exclusive board arbitration per runner, USB relays power-cycling around every flash, SD-mux image handoff, pytest+pexpect serial validation, upload-artifact for images/logs

### [S1123] GitHub Docs — Actions usage limits
- type: docs
- url: https://docs.github.com/en/actions/reference/limits
- author: GitHub
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260625171148/https://docs.github.com/en/actions/reference/limits (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260623070520/http://sigrok.org/wiki/Sigrok-cli (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260704001351/http://sigrok.org/wiki/Fx2lafw (snapshot predates accessed date; refresh next verification pass)
- relevance: open firmware (GPLv2+) for $10–25 Cypress FX2 logic-analyzer clones (Saleae Logic/USBee clones); 24 MHz crystal, 8 probes (PB0–7) or 16 — 24 MS/s is ~30 samples/bit for 800 kHz WS2812, adequate for decode and skew timestamps

### [S1128] Saleae Logic 2 Automation API documentation
- type: docs
- url: https://saleae.github.io/logic2-automation/
- author: Saleae
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727053745/https://saleae.github.io/logic2-automation/
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
- archive: https://web.archive.org/web/20260714205346/https://www.saleae.com/products/logic-8
- relevance: Logic 8 = 8 digital channels at 100 MS/s + analog recording 10 MS/s/10-bit on the same probes, "Python automation API" first-party — one instrument covers protocol decode AND photodiode digitization; price not published on page

### [S1131] Nordic Semiconductor — Power Profiler Kit II product page
- type: product
- url: https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2
- author: Nordic Semiconductor
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260511185822/https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2 (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20251207093313/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_wifi.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260624121923/https://scapy.readthedocs.io/en/latest/usage.html (snapshot predates accessed date; refresh next verification pass)
- relevance: `sniff(monitor=True)` on monitor-mode interfaces, Dot11 dissection, BPF filters at OS level, `wrpcap`/`rdpcap` for pcap artifacts — the Python half of the ESP-NOW PDR-counting pipeline

### [S1137] Power Electronic Tips — "How to gauge LED flicker" (+ IEEE 1789-2015 context)
- type: article
- url: https://www.powerelectronictips.com/how-to-gauge-led-flicker-faq/
- author: Power Electronic Tips (WTWH Media engineering site)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728005904/https://www.powerelectronictips.com/how-to-gauge-led-flicker-faq/
- relevance: the established low-cost flicker rig — integrated photodiode+transimpedance chip (TSL257 light-to-voltage converter) into a scope; percent flicker (Lmax−Lmin)/(Lmax+Lmin) and flicker index per IEEE 1789-2015 (~8 % limit at 100 Hz); lab gear samples light at up to 200 kHz — sets the ADC bar for pewpew's dither bench (site blocks fetch with 403; claims from search excerpt + cross-search 2026-07-09)

### [S1138] Hypothesis documentation — Stateful testing
- type: docs
- url: https://hypothesis.readthedocs.io/en/latest/stateful.html
- author: Hypothesis project (David R. MacIver et al.)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260518144923/https://hypothesis.readthedocs.io/en/latest/stateful.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260707105930/https://llvm.org/docs/LibFuzzer.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20250718094418/https://docs.github.com/en/actions/reference/events-that-trigger-workflows (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20261019210306/https://www.anthropic.com/engineering/writing-tools-for-agents
- relevance: tool-design principles (high-leverage tools, namespacing, semantic identifiers over UUIDs, token-efficient responses, eval-driven tool iteration) still the reference cited by 2026 material; carried-forward baseline for pewpew's MCP/CLI surfaces

### [S1154] Anthropic engineering — Demystifying evals for AI agents
- type: article
- url: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- author: Anthropic
- published: 2026-01-09
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260724004259/https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- relevance: current statistical discipline for noisy agent/system tests — pass@k vs pass^k, clean-environment trials, capability evals graduating into continuously-run regression suites, "read the transcripts" verification

### [S1155] Anthropic engineering — How we built Claude Code auto mode
- type: article
- url: https://www.anthropic.com/engineering/claude-code-auto-mode
- author: Anthropic
- published: 2026-03-25
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260720170404/https://www.anthropic.com/engineering/claude-code-auto-mode
- relevance: permission tiering for autonomous agents: 93% prompt-approval habituation data, three-tier allowlist→file-ops→transcript-classifier design, five blocked categories, 0.4% FP / 17% FN rates — the template for pewpew's bench-actuation gating

### [S1156] Anthropic engineering — Making Claude Code more secure and autonomous with sandboxing
- type: article
- url: https://www.anthropic.com/engineering/claude-code-sandboxing
- author: Anthropic
- published: 2025-11 (covered by InfoQ 2025-11)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260714134922/https://www.anthropic.com/engineering/claude-code-sandboxing
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
- archive: https://web.archive.org/web/20260629215216/https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ (snapshot predates accessed date; refresh next verification pass)
- relevance: where MCP is going as of mid-2026: stateless core (no initialize handshake/session header), Tasks extension for long-running tool calls (tools/call returns a task handle; tasks/get / tasks/update / tasks/cancel), extensions framework, Sampling/Roots/Logging deprecated

### [S1160] MCP specification 2025-11-25 — Server tools
- type: spec
- url: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- author: Model Context Protocol project
- published: 2025-11-25
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260704182228/https://modelcontextprotocol.io/specification/2025-11-25/server/tools (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260706195226/https://justin.poehnelt.com/posts/rewrite-your-cli-for-ai-agents/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260411172428/https://scrolltest.com/flaky-tests-detection-quarantine-prevention-guide-2026/ (snapshot predates accessed date; refresh next verification pass)
- relevance: 2026 flake discipline: run new/changed tests 5–10× pre-merge, flakiness scores per test, quarantine lanes with owner + two-week deadline, blind retries explicitly deprecated ("a test that needs retries to pass consistently is still broken")

### [S1171] Sentry docs — Seer (AI debugging agent)
- type: docs
- url: https://docs.sentry.io/product/ai-in-sentry/seer/
- author: Sentry
- published: continuously updated; current as of access
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260519071048/https://docs.sentry.io/product/ai-in-sentry/seer/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260113062456/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/wdts.html (snapshot predates accessed date; refresh next verification pass)
- relevance: first-party reference for IWDT/TWDT/XTWDT config, defaults, and the subscribe/reset API a render loop must use

### [S1201] ESP-IDF Fatal Errors guide (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/fatal-errors.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260310155012/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/fatal-errors.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260303122027/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/misc_system_api.html (snapshot predates accessed date; refresh next verification pass)
- relevance: full esp_reset_reason_t enum (PANIC, INT_WDT, TASK_WDT, BROWNOUT, PWR_GLITCH, CPU_LOCKUP…), shutdown handlers, esp_get_minimum_free_heap_size

### [S1205] ESP-IDF Non-Volatile Storage (NVS) docs
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html
- author: Espressif Systems
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260213110244/https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/storage/nvs_flash.html (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260727053827/https://esp32.com/ext/espressif/stupidbots/challenge.php?n=MTc4NTEzMDcwMy4zNDg4NzM1NTM5&c=c53b0e66ef41e6d092d724e051a4514a361bf38fed361e1254b4685b5d88ea59&h=1891a3fd72ea7c07db05445a50935f878a936220cd9018836f153b6930bf6577&from=L3ZpZXd0b3BpYy5waHA%2FdD0xNjY1OQ%3D%3D
- relevance: RTC_NOINIT_ATTR survives SW/WDT/panic resets but not power loss or brownout; caller must gate re-init on reset reason — the crash-counter mechanism

### [S1209] esp-idf issue #9400: WiFi stuck while connecting, watchdog not triggered
- type: forum
- url: https://github.com/espressif/esp-idf/issues/9400
- author: espressif/esp-idf issue tracker
- published: 2022-07
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727053854/https://github.com/espressif/esp-idf/issues/9400
- relevance: first-party tracker evidence that the WiFi stack can wedge in states the default watchdogs do not catch — motivates application-level radio liveness supervision

### [S1210] ESPHome Safe Mode component docs
- type: docs
- url: https://esphome.io/components/safe_mode/
- author: ESPHome project (Open Home Foundation)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260622152128/https://esphome.io/components/safe_mode/ (snapshot predates accessed date; refresh next verification pass)
- relevance: production boot-loop-detection pattern: N consecutive failed boots (default 10) → minimal firmware with only network+OTA; boot "good" after 1 min; the safe-mode design pewpew should copy

### [S1211] esphome issue #15796: safe-mode counter misses setup-phase crashes
- type: forum
- url: https://github.com/esphome/esphome/issues/15796
- author: esphome issue tracker
- published: 2024
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260727053929/https://github.com/esphome/esphome/issues/15796
- relevance: documented gap in the counter-in-app pattern — a crash before the counter increments defeats boot-loop detection; argues for bootloader-side or earliest-init counting

### [S1212] Memfault MCU coredump docs
- type: docs
- url: https://docs.memfault.com/docs/mcu/coredumps
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260601155918/https://docs.memfault.com/docs/mcu/coredumps (snapshot predates accessed date; refresh next verification pass)
- relevance: what a commercial device-observability pipeline captures on fault (registers, tasks, selected RAM regions), store-then-upload-on-next-boot, fallback to minimal trace if storage fails

### [S1213] Memfault MCU reboot reason tracking docs
- type: docs
- url: https://docs.memfault.com/docs/mcu/reboot-reason-tracking
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260321104846/https://docs.memfault.com/docs/mcu/reboot-reason-tracking (snapshot predates accessed date; refresh next verification pass)
- relevance: two-source reboot attribution (hardware register + software-marked imminent reason), noinit-RAM tracking, expected-vs-unexpected classification, bootloop metric — the forensics-minimum reference design

### [S1214] Memfault OTA & release management docs
- type: docs
- url: https://docs.memfault.com/docs/platform/ota
- author: Memfault
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260321104825/https://docs.memfault.com/docs/platform/ota (snapshot predates accessed date; refresh next verification pass)
- relevance: cohorts + percentage staged rollout + fleet-health comparison charts as the abort signal — vendor-practice reference for rollout rings

### [S1215] Interrupt (Memfault) — watchdog timer best practices guide
- type: article
- url: https://interrupt.memfault.com/blog/firmware-watchdog-best-practices
- author: Interrupt / Memfault engineering blog
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260408021818/https://interrupt.memfault.com/blog/firmware-watchdog-best-practices (snapshot predates accessed date; refresh next verification pass)
- relevance: hardware WDT as last resort + software WDT for state capture; feed from a low-priority task, never a timer ISR; all-tasks-check-in pattern; always-reboot-never-wedge stance

### [S1216] Google SRE Workbook ch. 16 — Canarying Releases
- type: article
- url: https://sre.google/workbook/canarying-releases/
- author: Google (Site Reliability Workbook)
- published: 2018
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260627024041/https://sre.google/workbook/canarying-releases/ (snapshot predates accessed date; refresh next verification pass)
- relevance: canary definition, population sizing vs blast radius, metric selection, small-population caveats — the discipline to shrink to 50 nodes

### [S1217] AWS IoT Device Management — job rollout, abort, timeout, retry configurations
- type: docs
- url: https://docs.aws.amazon.com/iot/latest/developerguide/jobs-configurations-details.html
- author: Amazon Web Services
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260703211645/https://docs.aws.amazon.com/iot/latest/developerguide/jobs-configurations-details.html (snapshot predates accessed date; refresh next verification pass)
- relevance: production fleet-OTA machinery: exponential rollout rates gated on success counts, abort on failure-percentage thresholds, maintenance windows — "avoid a bad update from being sent to an entire fleet"

### [S1218] balena docs — release policies (fleet default vs device pinning)
- type: docs
- url: https://docs.balena.io/learn/deploy/release-strategy/release-policy/
- author: balena
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20251202153028/https://docs.balena.io/learn/deploy/release-strategy/release-policy/ (snapshot predates accessed date; refresh next verification pass)
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
- archive: https://web.archive.org/web/20260728005939/https://principlesofchaos.org/
- relevance: canonical definition, steady-state hypothesis, vary-real-world-events, minimize blast radius — the principles RA-21 adapts to a 50-node bench

### [S1221] Kalka & Szydlo — µChaos: Moving Chaos Engineering To IoT Devices (ICCS 2024)
- type: article
- url: https://www.iccs-meeting.org/archive/iccs2024/papers/148380231.pdf
- author: Wojciech Kalka, Tomasz Szydlo (AGH Krakow / Newcastle University)
- published: 2024
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260510080930/https://www.iccs-meeting.org/archive/iccs2024/papers/148380231.pdf (snapshot predates accessed date; refresh next verification pass)
- relevance: the state of embedded chaos engineering — open-source Zephyr-OS fault-injection component (CPU, memory, network, sensor, application faults via serial API); documents that end-device chaos tooling barely exists

### [S1222] Candea & Fox — Crash-Only Software (HotOS IX, 2003)
- type: article
- url: https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea_html/index.html
- author: George Candea, Armando Fox (Stanford)
- published: 2003-05
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260115050447/https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea_html/index.html (snapshot predates accessed date; refresh next verification pass)
- relevance: the academic case for reboot-as-recovery: one way to stop (crash) and one way to start (recover) yields simpler, more reliable systems — grounds the self-reboot-on-anomaly stance

### [S1223] Doug Fleenor Design — DMX512 to 0-10 V Analog Converter owner's manual
- type: docs
- url: https://www.dfd.com/pdf/24anl-man.pdf
- author: Doug Fleenor Design
- published: 2019-07 (manual revision)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260724153629/http://www.dfd.com/pdf/24anl-man.pdf
- relevance: stage-lighting hold-last-look convention in writing: holds last levels on DMX loss until control restored or power removed; levels reset to zero on power-up; optional jumper for blackout ~1 s after loss

### [S1224] ANSI E1.11-assoc. ANSI E1.31-2016 — sACN (Streaming ACN)
- type: spec
- url: https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
- author: ESTA Technical Standards Program
- published: 2016
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260704005950/https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf (snapshot predates accessed date; refresh next verification pass)
- relevance: codified loss-of-data machinery: E131_NETWORK_DATA_LOSS_TIMEOUT (2.5 s of silence) and the stream-terminated option bit (sent 3×) — receiver-local timers decide degradation, no consensus

### [S1225] Battery University BU-502 — Discharging at High and Low Temperatures
- type: article
- url: https://batteryuniversity.com/article/bu-502-discharging-at-high-and-low-temperatures
- author: Battery University (Cadex Electronics)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260622174801/https://www.batteryuniversity.com/article/bu-502-discharging-at-high-and-low-temperatures (snapshot predates accessed date; refresh next verification pass)
- relevance: capacity ≈50 % at –18 °C, internal-resistance rise in cold, cycle-life loss above 30 °C — battery-vs-temperature priors for outdoor fleet planning

### [S1226] MacroFab — Conformal Coating vs. Potting/Encapsulation
- type: article
- url: https://www.macrofab.com/blog/conformal-coating-vs-potting-encapsulation
- author: MacroFab (electronics manufacturer engineering blog)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728010101/https://www.macrofab.com/blog/conformal-coating-vs-potting-encapsulation
- relevance: protection-vs-serviceability tradeoff: thin coatings (~25–75 µm) rework-friendly and thermally benign; potting seals to IP67/68 but kills rework and stresses solder joints in thermal cycling

### [S1227] PCBCart — Burn-In Testing: Filtering Out Infant Mortality
- type: article
- url: https://www.pcbcart.com/article/content/burn-in-testing-electronics-reliability.html
- author: PCBCart (electronics manufacturer)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260728010150/https://www.pcbcart.com/article/content/burn-in-testing-electronics-reliability.html
- relevance: bathtub-curve rationale for pre-deployment soak; typical durations (8–48 h consumer, up to 168 h high-reliability) under elevated temperature/voltage/load

### [S1228] Reliability Analytics Toolkit — Poisson spares analysis
- type: docs
- url: https://reliabilityanalyticstoolkit.appspot.com/poisson_spares_analysis
- author: Reliability Analytics (method per USAF Rome Laboratory Reliability Engineer's Toolkit, 1993)
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260119174046/https://reliabilityanalyticstoolkit.appspot.com/poisson_spares_analysis (snapshot predates accessed date; refresh next verification pass)
- relevance: the standard spares formula: Poisson on population × failure rate × resupply interval at a chosen confidence — the method RA-21 applies to a 50-node fleet

### [S1229] Advatek PixLite 16 Plug & Play Mk2 user manual
- type: docs
- url: https://cdn.prod.website-files.com/6526c8266f9d6acac8ef145f/661d4804085c9f0866d03279_PixLite%2016%20Plug%20And%20Play%20Mk2%20User%20Manual_20230823.pdf
- author: Advatek Lighting
- published: 2023-08-23
- accessed: 2026-07-09
- archive: https://web.archive.org/web/20260710090028/https://cdn.prod.website-files.com/6526c8266f9d6acac8ef145f/661d4804085c9f0866d03279_PixLite%2016%20Plug%20And%20Play%20Mk2%20User%20Manual_20230823.pdf
- relevance: professional outdoor-pixel install practice: IP67 screw-lock connectors with gold pins, warning that poor waterproofing lets rain short supply onto data lines, ≤15 m controller-to-first-pixel rule

## Block S1250–S1299 — RA-22 Stock-WLED DDP over a private router

### [S1250] WLED source at tag v16.0.1
- type: code
- url: https://github.com/wled/WLED/tree/v16.0.1
- pinned: wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c
- author: WLED contributors
- license: EUPL-1.2 (GitHub API, 2026-10-26)
- published: tag commit 2026-06-30; release 2026-07-07
- accessed: 2026-10-19
- relevance: the firmware the three-board rig runs. DDP bytes per pixel (`wled00/e131.cpp#L54-L57`), auto-white on streamed data (`wled00/bus_manager.cpp#L275`, `#L102-L125`), the 15 ms `show()` gate (`wled00/udp.cpp#L477`), Wi-Fi sleep off on ESP32 (`wled00/wled.h#L372`), DDP unicast only (`wled00/wled.cpp#L875`), 4 RMT outputs on S3 (`wled00/const.h#L88`), settings-PIN scope, config backup files. S001 and S645 pin earlier commits.

### [S1251] Espressif — ESP32-S3 Wi-Fi performance guide and product page
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/wifi-driver/wifi-performance-and-power-save.html
- also: https://www.espressif.com/en/products/socs/esp32-s3
- author: Espressif Systems
- accessed: 2026-10-19 (performance table rechecked 2026-10-26)
- relevance: S3 iperf UDP RX 30 Mbit/s over the air in lab (88 Mbit/s shielded); modem sleep can delay RX by a DTIM cycle; the S3 is 2.4 GHz only. S1004 is the classic-ESP32 page of the same guide.

### [S1252] LedFx hosted docs — performance tips and API reference
- type: docs
- url: https://docs.ledfx.app/en/latest/howto/tips.html
- also: https://ledfx.readthedocs.io/en/v2.0.58/api.html
- author: LedFx contributors
- accessed: 2026-10-19
- relevance: LED-wire frame-time formula and a measured WLED Dig-Octa fps fall-off above ~1,400 LEDs; LedFx segment form `[device,start,end,invert]`.

### [S1253] WLED GitHub issues — realtime stutter and lag reports
- type: forum
- url: https://github.com/wled/WLED/issues/4320
- also: https://github.com/wled/WLED/issues/5575, https://github.com/wled/WLED/issues/5596, https://github.com/wled/WLED/issues/3411
- author: WLED users and maintainers
- published: #4320 2024-11-25 (closed not planned 2025-07-27); #5575 2026-05-07 (open); #5596 2026-05-11 (closed not planned); #3411 2023-10-02 (closed not planned)
- accessed: 2026-10-19 (states rechecked 2026-10-26)
- relevance: #4320 DDP stutter building over hours, cured by reboot; #5575 ~1 s lag on v16.0.0; #5596 maintainer DedeHai: live-mode stutter "is related to wifi signal. you need a clean wifi channel with no other traffic on it"; #3411 full-`/json` polling by Home Assistant stalls output every 10 s.

### [S1254] WLED GitHub — DDP protocol handling changes in the v16 line
- type: code
- url: https://github.com/wled/WLED/issues/5532
- also: https://github.com/wled/WLED/issues/5412, https://github.com/wled/WLED/pull/5547, https://github.com/wled/WLED/pull/5554, https://github.com/wled/WLED/pull/5896
- author: WLED contributors (softhack007, DedeHai, dustinreed-info)
- license: EUPL-1.2
- published: #5412 2026-03-09; #5532 2026-04-24; #5554 merged to 16_x 2026-05-01; #5547 merged to main 2026-05-13; #5896 opened 2026-10-09 (open)
- accessed: 2026-10-19 (rechecked 2026-10-26)
- relevance: "skip out-of-sequence" assumes ≤4 packets per frame (#5412); v16 nightlies rejected undefined DDP data types (#5532), relaxed on 16_x by #5554 ("basically the same as #5547"), which is in the v16.0.0 and v16.0.1 tags; stale sequence numbers after a sender restart (#5896, unmerged).

### [S1255] W5500 Ethernet options for WLED on ESP32-S3
- type: forum
- url: https://github.com/wled/WLED/issues/5478
- also: https://github.com/MoonModules/WLED-MM/pull/320, https://maker.wiznet.io/Benjamin/projects/thebreeze-w5500-ethernet-ddp-receiver-for-wled/
- author: softhack007 (WLED); troyhacks (WLED-MM PR); WIZnet maker community
- published: #5478 comment 2026-04-05; WLED-MM PR #320 opened 2026-01-15 (open)
- accessed: 2026-10-19 (rechecked 2026-10-26)
- relevance: "normal WLED does not support W5500 ethernet"; the WLED-MM PR is "largely untested except by author" (softhack007 in #5478); a single-commit third-party usermod exists. Grounds "no wired fallback on stock WLED S3".

### [S1256] WLED per-output pixel caps across releases
- type: code
- url: https://github.com/wled/WLED/pull/5267
- also: https://newreleases.io/project/github/wled/WLED/release/v0.15.0-b4
- author: WLED contributors
- license: EUPL-1.2
- published: PR #5267 opened 2026-01-03, closed unmerged 2026-01-19
- accessed: 2026-10-19 (PR state checked 2026-10-26)
- relevance: 0.15.0-b4 caps parallel I2S at 300 LEDs per output; the S3 PR that used 600 was closed without merging.

### [S1257] WLED v16 brownout and boot-failure reports
- type: forum
- url: https://github.com/wled/WLED/issues/5570
- also: https://wled.discourse.group/t/16-x-problems-with-early-quinled-esp32s/15450
- author: WLED users and maintainers
- published: #5570 2026-05-05 (open, reopened)
- accessed: 2026-10-19
- relevance: v16 crashes on weak 3.3 V supplies; reported fixes are a capacitor on 3V3, TX power ≤8.5 dBm and stable USB power; reports run through 2026-10-12.

### [S1258] WLED Discourse — scale, network and realtime-handover threads
- type: forum
- url: https://wled.discourse.group/t/12-16-x-16-panels-esp32-ddp-laggy-not-sure-best-way-to-drive-all-12-panels/12974
- also: https://wled.discourse.group/t/all-my-wled-is-offline-unifi-6/14143, https://wled.discourse.group/t/dmx-e1-31-effect-control/3283
- author: WLED community
- published: 14143 2025-03-03
- accessed: 2026-10-19
- relevance: ~4k px on 5 ESP32s over DDP "no lag on wifi" (no fps or version); client isolation and auto channel selection took nodes offline; WLED resumes local control ~2.5 s after realtime stops.

### [S1259] RFC 9119 — Multicast Considerations over IEEE 802 Wireless Media
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc9119.html
- author: C. Perkins, M. McBride, D. Stanley, W. Kumari, JC. Zúñiga (IETF)
- published: 2021-10
- accessed: 2026-10-19
- relevance: Wi-Fi multicast "is generally transmitted at the slowest rate of all the connected devices" (§3.1.2) with "no ACKs" (§3.1.1) (rechecked 2026-10-26).

### [S1260] Wi-Fi deployment practice for realtime LED streams
- type: article
- url: https://quinled.info/quinled-dig-octa-system-usage-examples/
- also: https://intel.vn/content/www/vn/vi/support/network-and-i-o/wireless-networking/000005799.html, https://esp32.com/viewtopic.php?p=119475
- author: QuinLED; Intel support; esp32.com forum
- accessed: 2026-10-19
- relevance: Wi-Fi is a shared medium where one device receives at a time, so QuinLED recommends Ethernet for realtime; use channels 1/6/11 at 20 MHz in 2.4 GHz; the DevKitC-1U variant has a U.FL antenna connector.

### [S1261] WLED knowledge base — boot-loop recovery and wiring
- type: docs
- url: https://kno.wled.ge/advanced/bootloop-recovery/
- also: https://kno.wled.ge/advanced/wiring/
- author: WLED contributors
- accessed: 2026-10-19 (boot-loop page rechecked 2026-10-26)
- relevance: after 5 crashes in a 2-minute window WLED restores the backup config, then resets config, then (ESP32) rolls back firmware, one step per boot; fuse each supply close to it.

### [S1262] WLED knowledge base — segments, multi-strip, MQTT, macros
- type: docs
- url: https://kno.wled.ge/features/segments/
- also: https://kno.wled.ge/features/multi-strip/, https://kno.wled.ge/interfaces/mqtt/, https://kno.wled.ge/features/macros/
- author: WLED contributors
- accessed: 2026-10-19
- relevance: segment grouping; 512 LEDs per pin on 4 outputs given as "perfect performance"; MQTT has no TLS; button/PIR preset triggers on the board.

### [S1263] WLED-MM docs — settings and PIR sensor usermod pages
- type: docs
- url: https://mm.kno.wled.ge/features/settings/
- also: https://mm.kno.wled.ge/usermods/PIRsensorSwitch/
- author: MoonModules / WLED contributors
- accessed: 2026-10-19
- relevance: the current limiter is one estimate for all outputs and still applies to "Force max brightness" streams; WLED brightness scales incoming realtime data unless that option is set; PIR usermod runs an off-preset after a timeout. S005 is this doc site's root.

### [S1264] QLC+ documentation — Grand Master, kiosk mode, web interface, input profiles
- type: docs
- url: https://qlcplus.org/docs/html_en_EN/concept.html
- also: https://docs.qlcplus.org/v4/advanced/kiosk-mode, https://qlcplus.org/docs/html_en_EN/webinterface.html, https://docs.qlcplus.org/v5/input-output/input-profiles
- author: Massimo Callegari and QLC+ contributors
- published: webinterface page 2022-08-28
- accessed: 2026-10-19
- relevance: Grand Master "Reduce" vs "Limit"; kiosk/operate mode with the web login limited to the Virtual Console; the web page lacks Grand Master and crossfade sliders (2022 doc); input profiles map MIDI/OSC to controls.

### [S1265] Chromatik Guide — snapshots, performance mode, palette, model definition, modulation
- type: docs
- url: https://chromatik.co/guide/snapshots/
- also: https://chromatik.co/guide/performance-mode/, https://chromatik.co/guide/color-palette/, https://chromatik.co/guide/application-overview/, https://chromatik.co/guide/model-definition/, https://chromatik.co/guide/modulation/
- author: Heron Arts / Mark Slee
- published: n/a (living docs)
- accessed: 2026-10-19
- relevance: snapshots toggle what they store, carry a transition time and an auto-cycle flag, finish a fade on re-recall; Performance Mode; global palette swatches; tags drive views and `.lxm` reload; triggers fire on change only. S309 (custom fixtures) and S555 (OSC) are sibling pages.

### [S1266] LedFx repository docs — scenes, playlists, silence scene
- type: code
- url: https://github.com/LedFx/LedFx/tree/main/docs
- pinned: LedFx/LedFx@ccd299502b2d12621b6eba4a75b9eeadc410af64
- author: LedFx contributors
- license: GPL-3.0
- published: playlists.md 2025-12-28; silence_scene.md 2026-10-12
- accessed: 2026-10-19
- relevance: `docs/settings/scenes.md` (per-output activate/ignore/force black/stop), `docs/settings/playlists.md` (sequence/shuffle, duration variation), `docs/developer/silence_scene.md` (journal state, switch, restore). S011 pins an earlier commit.

### [S1267] LedFx releases — v2.1.8 and v2.2.1
- type: release
- url: https://github.com/LedFx/LedFx/releases
- author: LedFx contributors
- published: v2.1.8 2026-04-21; v2.2.1 2026-10-04
- accessed: 2026-10-19 (dates rechecked 2026-10-26)
- relevance: startup playlist (v2.1.8); scene REST, Launchpad and Home Assistant event inputs (v2.2.1).

### [S1268] ElectroMage docs — Pixelblaze user interface and websocket API
- type: docs
- url: https://electromage.com/docs/user-interface
- also: https://electromage.com/docs/websockets-api
- author: ElectroMage (Ben Hencke)
- accessed: 2026-10-19
- relevance: "Limit Brightness" as a hard cap; `setVars` over websocket port 81 as an event path.

### [S1269] Lighting console manuals — grandMA3, ETC Ion, Avolites
- type: docs
- url: https://help.malighting.com/grandMA3/2.5/ (pages ws_masters_window, masters_speed, keyword_oops)
- also: ETC Ion help Grandmaster_Configuration.htm; https://community.etcconnect.com (thread 5007); https://manual.avolites.com/docs/palettes/timing-with-palettes
- author: MA Lighting; ETC; Avolites
- accessed: 2026-10-19
- relevance: speed masters with tap/×2/÷2 and Oops undo; ETC hardware blackout needs two keys while the on-screen one fires on one touch; a typed fade time overrides the stored one. Page names as given in the 2026-10-19 report; full paths not re-resolved.

### [S1270] Open Stage Control — docs, forum and releases
- type: docs
- url: https://openstagecontrol.ammd.net/ (pages server-configuration, client-options; v1.31.0)
- also: https://openstagecontrol.discourse.group/t/3182; https://github.com/jean-emmanuel/open-stage-control/releases
- author: Jean-Emmanuel Doucet
- published: v1.31.0 2026-09-23
- accessed: 2026-10-19 (release date rechecked 2026-10-26)
- relevance: `read-only` and `remote-saving` server options; users ask to turn off client sync (`clientSync=0`); sends OSC.

### [S1271] Touch-target size and thumb-reach guidance
- type: article
- url: https://frontendchecklist.io/rules/accessibility/touch-targets
- also: https://alistapart.com/article/how-we-hold-our-gadgets/
- author: Front-End Checklist; Steven Hoober (A List Apart)
- published: A List Apart 2015
- accessed: 2026-10-19
- archive: https://web.archive.org/web/20261105072930/https://frontendchecklist.io/rules/accessibility/touch-targets
- relevance: 24 CSS px WCAG AA floor and 44 px common target; ~75% of phone use is thumb-driven, bottom third most reachable.

### [S1272] MDN — Service Worker API
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- author: Mozilla contributors
- published: last modified 2026-08-15
- accessed: 2026-10-19
- archive: https://web.archive.org/web/20261024012143/https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API  # snapshot 2026-10-24
- relevance: service workers need a secure context (HTTPS or localhost), so a phone on `http://<laptop-ip>` gets no offline cache.

### [S1273] Epilepsy Society — Photosensitive epilepsy factsheet
- type: article
- url: https://epilepsysociety.org.uk (PhotosensitiveepilepsyJuly2023.pdf; full path as given in the 2026-10-19 report not recorded)
- author: Epilepsy Society (UK)
- published: 2023-07
- accessed: 2026-10-19
- relevance: flashes at 3–30 per second are the common trigger range for photosensitive seizures.

### [S1274] AusChristmasLighting forum — xSchedule status and channel-gap warning threads
- type: forum
- url: https://auschristmaslighting.com/goto/post?id=146337
- also: https://auschristmaslighting.com/threads/warn-gap-in-models-on-pixel-port-1-channel.17225
- author: AusChristmasLighting community
- published: post 146337 2026-04-02
- accessed: 2026-10-19
- relevance: xSchedule reportedly discontinued with EZPlayer replacing it; xLights allocates channels contiguously, so inserting a model mid-port shifts the rest.

### [S1275] Resolume — OSC support and pixel-mapping article
- type: docs
- url: https://resolume.com/support/en/osc
- also: https://resolume.com/article/27
- author: Resolume
- accessed: 2026-10-19
- relevance: OSC input on port 7000 with fixed addresses and a 200-message monitor; build the pixel map in advance and assign the node in the room.

### [S1276] MadMapper documentation — DMX fixtures, LED scanner, Cue Scheduler
- type: docs
- url: https://docs.madmapper.com/ (pages dmx-fixtures, tools-led-scanner)
- also: https://madmapper.com/files/07-Cue%20Scheduler.pdf
- author: GarageCube
- accessed: 2026-10-19
- relevance: 16 scan orders and `avoidCrossUniversePixels`; camera LED scanner for setup; cue scheduling.

### [S1277] heronarts/GLX — UIPointCloud.java
- type: code
- url: https://github.com/heronarts/GLX/blob/master/src/main/java/heronarts/glx/ui/component/UIPointCloud.java
- pinned: heronarts/GLX@9abda8dbe1ff401637aceb67e7d7a63593efa7e8
- author: Mark C. Slee / Heron Arts
- license: CHROMATIK / LX SOFTWARE LICENSE AND DISTRIBUTION AGREEMENT (custom, not OSI; LICENSE header read 2026-10-26)
- published: file last changed 2026-07-10
- accessed: 2026-10-19
- relevance: Chromatik's point-cloud preview controls: point size, feather, sparkle, contrast, gamma and floor, LED textures, alpha blend.

### [S1278] xLights manual — layout, models, controller visualizer, testing
- type: docs
- url: https://manual.xlights.org/ (pages moving-model-objects, models, keyboard-shortcuts, objects, controller-visualizer, layout, layer-settings, quick-start testing)
- also: https://xlights.org/tip-of-the-day-040 (2017-11-15)
- author: xLights contributors
- accessed: 2026-10-19
- relevance: layout editing (drag, rotate, align to first selected, lock, nudge, groups); background brightness; "Single Line as a Pixel"; overlap checks; visualizer refuses upload on errors; green start / blue end markers; pixel size and blended-circle preview; test mode. Page names as given in the 2026-10-19 report. S506 is the manual root.

### [S1279] xLights source — ruler, model keys, WLED controller limits
- type: code
- url: https://github.com/xLightsSequencer/xLights
- pinned: xLightsSequencer/xLights@8acb3714eb7f92dc5b1c7bb66a1ab0c8e74c6dac
- author: xLights contributors
- license: GPL-3.0
- accessed: 2026-10-19 (pin = last commit on master at 2026-10-19, resolved 2026-10-26)
- relevance: `src-core/models/RulerObject.h` (two-point ruler sets units and real length), `src-core/XmlSerializer/XmlNodeKeys.h` and `src-ui-wx/modelproperties/ModelPropertyAdapter.cpp` (model attributes, Model Chain), `resources/controllers/wled.xcontroller` (ESP32 `MaxPixelPortChannels` 3600). S026 pins an earlier commit.

### [S1280] FastLED — ScreenMap header
- type: docs
- url: https://fastled.io/docs/screenmap_8h_source.html (the report gives fastled.io screenmap_8h_source.html; `/docs/` prefix inferred from S503)
- author: FastLED contributors
- published: FastLED 3.9.15 docs
- accessed: 2026-10-19
- relevance: ScreenMap is x[], y[] and a dot diameter (0.5 for 5 mm LEDs) for browser preview.

### [S1281] isocorDev/EasyLEDMap
- type: code
- url: https://github.com/isocorDev/EasyLEDMap
- pinned: isocorDev/EasyLEDMap@85801afb14dc86e0aa8475234a509740d1f88b36
- author: isocorDev
- license: MIT
- published: repo created 2026-10-08 (v0.1)
- accessed: 2026-10-19
- relevance: traces the data path over a photo of the install; new and early.

### [S1282] mic159/wled-mapper
- type: code
- url: https://github.com/mic159/wled-mapper
- pinned: mic159/wled-mapper@157e620fee919943fef8186788022f46fb506c06
- author: mic159
- license: none stated (GitHub API reports no license, 2026-10-26)
- published: last commit 2023-01-10; last push 2023-07-12
- accessed: 2026-10-19
- relevance: drag-and-drop WLED mapping that lights the current LED to identify it. Not the same project as S314 (Vitminee/wled-mapper).

### [S1283] python-osc
- type: code
- url: https://github.com/attwad/python-osc
- pinned: attwad/python-osc@e91ace85525bd25858a5cea77528d0159cb5ff14
- author: attwad and contributors
- license: Unlicense
- published: v1.10.2 2026-04-02 (tag commit)
- accessed: 2026-10-19
- relevance: pure-Python OSC server/client; handlers can receive the sender address, which an allowlist needs. Candidate runtime dependency for OSC event input.

### [S1284] OSC control-surface releases — TouchOSC and Bitfocus Companion
- type: release
- url: https://hexler.net/touchosc/releases
- also: https://github.com/bitfocus/companion/releases; https://github.com/bitfocus/companion-module-generic-osc
- pinned: bitfocus/companion-module-generic-osc@44de2d14c6d7a23ef9b684a40cda5d92a361a536 (module only)
- author: hexler; Bitfocus
- license: generic-osc module MIT
- published: TouchOSC 1.5.3 2026-09-27; Companion v5.1.0 2026-10-11
- accessed: 2026-10-19 (Companion date rechecked 2026-10-26)
- relevance: current, maintained OSC senders an operator can use (Companion drives a Stream Deck).

### [S1285] shells-dw/StreamDeck-OSC
- type: code
- url: https://github.com/shells-dw/StreamDeck-OSC
- pinned: shells-dw/StreamDeck-OSC@47ce42787ab2dc2cd79fdbac8a950c5da72f1319
- author: shells-dw
- license: MIT
- accessed: 2026-10-19
- relevance: community Stream Deck plugin that sends OSC directly.

### [S1286] Home Assistant docs — RESTful Command and automation modes
- type: docs
- url: https://www.home-assistant.io/integrations/rest_command/
- also: https://www.home-assistant.io/docs/automation/modes/
- author: Home Assistant contributors
- accessed: 2026-10-19
- relevance: `rest_command` is HTTP-only, so Home Assistant reaches pewpew over HTTP, not OSC; single/restart/queued automation modes are precedents for event arbitration.

### [S1287] home-assistant/core — WLED integration constants
- type: code
- url: https://github.com/home-assistant/core/blob/dev/homeassistant/components/wled/const.py
- pinned: home-assistant/core@9b4cd3839f905ef55ddafbfebf5202d033a96aa8
- author: Home Assistant contributors
- license: Apache-2.0
- accessed: 2026-10-19 (pinned and checked 2026-10-26)
- relevance: `SCAN_INTERVAL = timedelta(seconds=10)` (`homeassistant/components/wled/const.py#L14`): the polling interval a widely deployed WLED client uses.

### [S1288] ESPHome component docs — HTTP request, UDP, LD2410/LD2450, sound level, binary sensor
- type: docs
- url: https://esphome.io/components/http_request/
- also: https://esphome.io/components/udp/, https://esphome.io/changelog/2025.5.0/, https://esphome.io/components/sensor/ld2410/, https://esphome.io/components/sensor/ld2450/, https://esphome.io/components/sensor/sound_level/, https://esphome.io/components/binary_sensor/
- author: ESPHome contributors
- published: http_request page at ESPHome 2026.9.1
- accessed: 2026-10-19
- relevance: `http_request` runs on the main loop with a 4.5 s default timeout; `udp.write` sends raw bytes; LD2410 gates, timeouts and engineering mode; LD2450 3-target tracking and filter zones; `sound_level` needs an I²S mic; `delayed_on`/`delayed_off` debounce.

### [S1289] Mosquitto — Migrating to 2.0
- type: docs
- url: https://mosquitto.org/documentation/migrating-to-2-0/
- author: Eclipse Mosquitto
- accessed: 2026-10-19
- relevance: Mosquitto 2.0 binds to localhost until configured and then requires authentication; MQTT adds a broker to run.

### [S1290] Network MIDI 2.0 — MIDI Association spec page and Microsoft transport notes
- type: spec
- url: https://midi.org/network-midi-2-0
- also: https://microsoft.github.io/MIDI/kb/network-midi2-transport
- author: MIDI Association; Microsoft
- published: Network MIDI 2.0 ratified 2024-11
- accessed: 2026-10-19
- relevance: Network MIDI 2.0 is new; Microsoft's transport lacks authentication. Grounds deferring network MIDI.

### [S1291] Presence-sensor field notes — mmWave, PIR, VL53L1X
- type: article
- url: https://help.inovelli.com/en/articles/13147206
- also: https://matteralpha.com/explainer/mmwave-make-your-home-smarter; shillehtek.com HC-SR501 manual (path not recorded in the report); https://community.home-assistant.io/t/1022697; https://esp32.co.uk/?p=991425
- author: Inovelli; Matter Alpha; ShillehTek; Home Assistant community; esp32.co.uk
- accessed: 2026-10-19
- relevance: mmWave false triggers from fans, curtains and airflow and through thin walls; PIR needs ~1 min warm-up and false-triggers on power-rail noise; VL53L1X has no native ESPHome support.

### [S1292] PeterkoCZ91/HLK-LD2450-security
- type: code
- url: https://github.com/PeterkoCZ91/HLK-LD2450-security
- pinned: PeterkoCZ91/HLK-LD2450-security@68dfa8ef84e176a74430ed30a9708e66ecc97503
- author: PeterkoCZ91
- license: MIT
- accessed: 2026-10-19
- relevance: field report of LD2450 ghost targets from furniture and metal.

### [S1293] MediaPipe Pose Landmarker — Python guide
- type: docs
- url: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python
- author: Google
- accessed: 2026-10-19
- relevance: live-stream mode drops frames to keep latency down; no latency figures published (not found).

### [S1294] TouchDesigner docs — Trigger CHOP and OSC In DAT
- type: docs
- url: https://docs.derivative.ca/Trigger_CHOP
- also: https://docs.derivative.ca/OSC_In_DAT
- author: Derivative
- accessed: 2026-10-19
- relevance: trigger envelopes with re-trigger delay and minimum length, the model for one-shot events over an ambient look; OSC In filters by address, not sender. S213 is a different Derivative page.

### [S1295] Interactive-installation precedents — NTU student installation; Hindle, "Hacking NIMEs"
- type: article
- url: https://nime.org/proc/nime2016_hindle/
- also: https://oss.adm.ntu.edu.sg/a150112/?p=661
- author: Abram Hindle (NIME 2016, pp. 359–364, doi:10.5281/zenodo.1176026); NTU ADM student blog
- published: 2016 (NIME)
- accessed: 2026-10-19 (NIME listing located 2026-10-26)
- relevance: many NIMEs can be hacked from audience smartphones, and OSC has no authentication; a student installation fired after 15 s of sustained activity.

### [S1296] macOS 27.0 manual pages — caffeinate(8), launchd.plist(5), pmset(1)
- type: docs
- url: n/a (local `man caffeinate`, `man launchd.plist`, `man pmset` on macOS 27.0)
- author: Apple
- accessed: 2026-10-19
- relevance: `caffeinate -i -s -w <pid>`; launchd restarts a job only when it exits, `KeepAlive {SuccessfulExit=false}`, `ThrottleInterval` 10 s default, unset `ProcessType` means throttled CPU and I/O, `LegacyTimers`; `pmset -c sleep 0 …`; `disablesleep` is absent from the 27.0 pmset page.

### [S1297] Apple Support — FileVault auto-login and Focus
- type: docs
- url: https://support.apple.com/102316
- also: https://support.apple.com/en-ca/guide/mac-help/mchl613dc43f/mac
- author: Apple
- accessed: 2026-10-19
- relevance: automatic login is unavailable while FileVault is on; Do Not Disturb Focus.

### [S1298] Third-party macOS unattended-operation articles
- type: article
- url: https://braindetox.kr/en/posts/electronic_clam_clamshell_agent_2026.html
- also: https://eclecticlight.co/2025/11/06/how-tahoe-26-1-has-enabled-automatic-security-updates/, https://junian.dev/tech/macos-disable-auto-update/
- author: braindetox.kr; Howard Oakley (The Eclectic Light Company); Junian
- published: eclecticlight 2025-11-06
- accessed: 2026-10-19
- relevance: only `pmset disablesleep 1` stops lid-closed sleep and it persists until reverted; Background Security Improvements (Tahoe 26.1+) install silently; which update toggles to turn off.

### [S1299] Community install-practice threads — power-up order and spare boards
- type: forum
- url: https://forum.makerforums.info/t/first-led-is-broken-again-and-again-when-i-powered-up-my-stripe/62988
- also: https://eplaya.burningman.org/viewtopic.php?p=354379
- author: Maker Forums community; ePlaya community
- accessed: 2026-10-19
- relevance: community power-up order (ground, V+, then data; pixels before or with the controller); carry spare board, PSU and cable. No official power-up order found.

## Block S1300–S1349 — RA-23 Board connectivity & health

### [S1300] Home Assistant WLED integration — config flow
- type: code
- url: https://github.com/home-assistant/core/blob/dev/homeassistant/components/wled/config_flow.py
- pinned: home-assistant/core@db50c01e164020f0179e679c9923138bf4172e9c
- author: Home Assistant contributors
- license: Apache-2.0 (GitHub API, 2026-11-04)
- accessed: 2026-11-04
- relevance: identifies a WLED board by its MAC (`async_set_unique_id(mac_address)`, L77) and, when that MAC appears at a new address, updates the stored host (`_abort_if_unique_id_configured(updates={CONF_HOST: host})`, L91; mismatch check L80-L89). The model for following a board to a new DHCP address.

### [S1301] Falcon Player (FPP) — MultiSync status page
- type: code
- url: https://github.com/FalconChristmas/fpp/blob/master/www/multisync.php
- pinned: FalconChristmas/fpp@49c9591f3ca33c023c804e5a124966aa132c7d12
- author: FalconChristmas contributors
- license: GPL-2.0-or-later for `www/multisync.php` (GitHub reports no SPDX ID; the repo LICENSE, read 2026-11-05, puts every file not listed as LGPL, CC-BY-ND or external under the GPL v2 or later)
- accessed: 2026-11-04
- relevance: a status table per remote system; counts failed polls per IP (`unavailables[ip]++`, L1696; reset L1758) and marks a system unreachable only after 4 in a row (`unavailables[ip] < 4`, L1804). Prior art for debouncing a health state.

### [S1302] LedFx — device base class
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/devices/__init__.py
- pinned: LedFx/LedFx@bf10b599efe74c809a743c6e7c319dcbf77e7dc3
- author: LedFx contributors
- license: GPL-3.0 (GitHub API, 2026-11-04)
- accessed: 2026-11-04
- relevance: each device carries an `online` flag (L87, L193, L327) set false when its destination cannot be resolved (L267); a WLED that changes IP is not re-addressed by MAC. The rejected "mark offline, wait for the user" alternative.

### [S1303] W3C — Understanding WCAG 2.2 SC 1.4.1 Use of Color
- type: docs
- url: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261021110603/https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html  # snapshot 2026-10-21 (predates accessed date)
- relevance: information shown by colour must also be available another way (text or shape); why each board state is a glyph and a word, not a coloured dot.

### [S1304] Apple — dns-sd(1) man page
- type: docs
- url: https://www.unix.com/man-page/osx/1/dns-sd/
- author: Apple
- accessed: 2026-11-04
- relevance: `dns-sd` is "primarily intended for interactive use" and scripting it "will generally be fragile"; the reason pewpew does not shell out to it for discovery.

### [S1305] python-zeroconf on PyPI
- type: docs
- url: https://pypi.org/project/zeroconf/
- author: python-zeroconf contributors
- license: LGPL-2.1-or-later (PyPI metadata, 2026-11-04)
- accessed: 2026-11-04
- relevance: the pure-Python mDNS/DNS-SD browser (0.153.0 needs Python 3.11+; `ServiceBrowser` runs its own thread). Rejected for board discovery: a fifth runtime dependency (after pyserial), under LGPL, where an HTTP sweep of the /24 finds the same boards with the standard library.

## Block S1350–S1399 — RA-24 Control-surface domain model & UI

### [S1350] OSCQuery proposal (Vidvox/OSCQueryProposal)
- type: spec
- url: https://github.com/Vidvox/OSCQueryProposal
- pinned: Vidvox/OSCQueryProposal@e3d8e3b91020c617f47fd88de157a1fe053e0583
- author: Vidvox
- license: none declared (GitHub reports no license; the repo holds README.md, units.md, extended_types.md only)
- published: 2018-08-31 (last push)
- accessed: 2026-11-04
- relevance: a JSON description of an OSC address space. TYPE is the OSC type tag string and sets the length of the VALUE, RANGE, UNIT, EXTENDED_TYPE and CLIPMODE arrays (one entry per value); RANGE entries hold MIN, MAX or VALS (the only acceptable values, "typically used to describe a series of menu options"); ACCESS is a mask (1 read, 2 write, 3 both); CLIPMODE is none/low/high/both and absent means no clipping; type tag `r` is "Color" with a colour-picker UI, T/F are booleans. units.md lists `angle.degree`, `time.second`, `time.hz`; extended_types.md lists `color.hsv.[hsva]`. units.md has no per-second rate unit (not found).

### [S1351] CLAP — parameters extension (include/clap/ext/params.h)
- type: code
- url: https://github.com/free-audio/clap/blob/main/include/clap/ext/params.h
- pinned: free-audio/clap@a47f6badb49d948fd009998f28309cdab78979c9
- author: free-audio (Alexandre Bique et al.)
- license: MIT
- accessed: 2026-11-04
- relevance: `clap_param_info.id` is a "Stable parameter identifier, it must never change" (L212); `module` is a '/'-separated path for display only, and `name` must not include it (L244-L251); `CLAP_PARAM_IS_STEPPED`, `IS_PERIODIC` ("Useful for periodic parameters like a phase"), `IS_ENUM` (requires STEPPED) and `IS_MODULATABLE` flags; host advice "store plain values in the document" and "store modulation amount in plain value delta, not in percentage" (L111-L112); automating the knob position is not robust to a range increase (L83-L85); `rescan(CLAP_PARAM_RESCAN_ALL)` is needed when flags or the range change. Excerpt: `research/excerpts/S1351-clap-params/`.

### [S1352] Steinberg VST 3 — Parameters and Automation
- type: docs
- url: https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Parameters+Automation/Index.html
- author: Steinberg Media Technologies
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105071815/https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Parameters+Automation/Index.html  # captured 2026-11-04
- relevance: each parameter gets a unique 32-bit ID and "it is not allowed to change this assignment at any time"; values are "always transmitted in a normalized floating point (64bit double) representation [0.0, 1.0]"; when a new version adds a list entry, normalized automation "will be invalid now" and the plug-in "must recalculate the automation data accordingly" — the migration cost of normalized storage.

### [S1353] Steinberg VST 3 — IRemapParamID (SDK 3.7.11)
- type: docs
- url: https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Change+History/3.7.11/IRemapParamID.html
- author: Steinberg Media Technologies
- published: 2024-04-22 (SDK 3.7.11)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105071932/https://steinbergmedia.github.io/vst3_dev_portal/pages/Technical+Documentation/Change+History/3.7.11/IRemapParamID.html  # captured 2026-11-04
- relevance: an interface added in 3.7.11 so a plug-in whose ParamIDs changed can ask the host to remap automation (`kParamIDMappingChanged`); evidence that a changed parameter id needs a remap layer, which stable ids avoid.

### [S1354] TouchDesigner — Custom Parameters
- type: docs
- url: https://docs.derivative.ca/Custom_Parameters
- author: Derivative
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073130/https://docs.derivative.ca/Custom_Parameters
- relevance: custom parameters live on user-defined pages (layout); multi-value parameters (`size`, up to 4; prebuilt RGB, RGBA, XYZ) are a tuplet, "a list of related parameters that will appear on one row", whose members get the name plus an index suffix; Pulse is a separate momentary type fired by `.pulse()` or a CHOP 0→1→0 signal.

### [S1355] TouchDesigner — Par Class
- type: docs
- url: https://docs.derivative.ca/Par_Class
- author: Derivative
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073216/https://docs.derivative.ca/Par_Class
- relevance: each component of a multi-value parameter is its own `Par` in a `ParGroup` ("a set of parameters sharing one line on a parameter dialog with a common label"), with `min`/`max`, separate `normMin`/`normMax` slider bounds, `clampMin`/`clampMax`, `default`, `menuNames` and `page`; a compound value is addressed part by part.

### [S1356] LedFx — pydantic effect configs (ledfx/effects/energy.py, ledfx/configuration/fields.py)
- type: code
- url: https://github.com/LedFx/LedFx/blob/main/ledfx/effects/energy.py
- pinned: LedFx/LedFx@bf10b599efe74c809a743c6e7c319dcbf77e7dc3
- author: LedFx developers
- license: GPL-3.0
- published: v2.2.1 released 2026-10-04
- accessed: 2026-11-04
- relevance: supersedes [S208] (voluptuous). Effect configs are now pydantic models (`pyproject.toml` requires `pydantic>=2.13,<3`): `blur: CoercedFloat = Field(4.0, ge=0.0, le=10)`, `mixing_mode: Literal["additive", "overlap"]`, and colours as `Color = Annotated[str, ..., JsonExtra({"format": "color"})]` holding hex strings such as `"#FF0000"` (fields.py L193); the frontend reads the generated JSON Schema plus `x-ledfx-*` extension keys. Typed and range-checked, still static (no per-frame modulation).

### [S1357] juce_organicui (Chataigne) — parameter types
- type: code
- url: https://github.com/benkuper/juce_organicui/tree/master/controllable/parameter
- pinned: benkuper/juce_organicui@e74374afed925dad3ff53532d4d98a2c3fa7f5fc
- author: Ben Kuper
- license: GPL-3.0
- accessed: 2026-11-04
- relevance: the parameter types of Chataigne's UI library are Bool, Color, Enum, File, Float, Int, Point2D, Point3D, String and Target, each a `Parameter` subclass; colour is one `ColorParameter` holding a `juce::Colour`, not three floats; `FloatParameter` picks its UI by `enum UIType { NONE, SLIDER, STEPPER, LABEL, TIME }`; `Trigger` derives from `Controllable`, not `Parameter`.

### [S1358] FFGL SDK (resolume/ffgl)
- type: code
- url: https://github.com/resolume/ffgl
- pinned: resolume/ffgl@5b6e07840277df9ec35a228b9eb067636316350f
- author: Resolume
- license: BSD-3-Clause
- accessed: 2026-11-04
- relevance: FFGL parameter types include `FF_TYPE_RED/GREEN/BLUE` and `FF_TYPE_HUE/SATURATION/BRIGHTNESS` as separate scalar params (source/lib/ffgl/FFGL.h L419-L435); a colour is "represented as three Params", and the host finds it by checking "if the current one and the two followings" match (`IsHueColor`, source/lib/ffglquickstart/FFGLPlugin.h L165-L182) — adjacent scalars grouped by position.

### [S1359] xLights — value curves (src-core/render/ValueCurve.cpp)
- type: code
- url: https://github.com/xLightsSequencer/xLights/blob/master/src-core/render/ValueCurve.cpp
- pinned: xLightsSequencer/xLights@a57c5ace577ca84421273d2f859a1a0c3f728297
- author: xLights contributors
- license: GPL-3.0
- accessed: 2026-11-04
- relevance: value curves were once stored on a 0-100 scale; the load path still carries a converter for curves not yet marked converted (`RV=TRUE`), and when the stored scale is ambiguous it warns "Sequence contains value curves that cannot be converted automatically. Please open and save this sequence in v2018.23 before proceeding." (L1555-L1607). The comment notes the check must be bumped every release "until we decide to change a slider range for the first time". Excerpt: `research/excerpts/S1359-xlights-value-curve/`.

### [S1360] JSON Schema 2020-12 — Validation vocabulary
- type: spec
- url: https://json-schema.org/draft/2020-12/json-schema-validation
- author: JSON Schema org (A. Wright, H. Andrews, B. Hutton)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073353/https://json-schema.org/draft/2020-12/json-schema-validation
- relevance: numeric keywords are `multipleOf`, `maximum`, `exclusiveMaximum`, `minimum`, `exclusiveMinimum`; meta-data annotations are `title`, `description`, `default`, `deprecated`, `readOnly`, `writeOnly`, `examples`. No `unit` keyword exists, and the format vocabulary defines no colour format; units, widgets and periodicity need extension keys.

### [S1361] react-jsonschema-form — uiSchema reference
- type: docs
- url: https://rjsf-team.github.io/react-jsonschema-form/docs/api-reference/uiSchema/
- author: rjsf-team
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073455/https://rjsf-team.github.io/react-jsonschema-form/docs/api-reference/uiSchema/
- relevance: the JSON Schema says "what" and a second object, the uiSchema, says "how": it "follows the tree structure of the form field hierarchy" and sets `ui:widget` and order per field — two documents to keep in step.

### [S1362] JSON Forms — UI schema layouts
- type: docs
- url: https://jsonforms.io/docs/uischema/layouts
- author: EclipseSource
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073527/https://jsonforms.io/docs/uischema/layouts
- relevance: layout lives in a separate UI schema (VerticalLayout, HorizontalLayout, Group with a label, Categorization) whose controls point into the data schema by `scope` (e.g. `"#/properties/name"`).

### [S1363] Ark UI documentation — components and styling guide
- type: docs
- url: https://ark-ui.com/docs/components/color-picker
- also: https://ark-ui.com/docs/components/ pages angle-slider, slider, segment-group, field, accordion, drawer, splitter; https://ark-ui.com/docs/guides/styling
- author: Chakra UI (Segun Adebayo et al.)
- license: MIT (package @ark-ui/react)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073617/https://ark-ui.com/docs/components/color-picker
- relevance: headless React components. ColorPicker renders "inline without a popover by using the `inline` prop", with `format`/`defaultFormat`, Area, ChannelSlider and ChannelInput parts; AngleSlider is "for selecting a value within a circular range"; Slider "Complies with the Slider WAI-ARIA design pattern" and takes `getAriaValueText`, `thumbAlignment`, `origin`; SegmentGroup follows the Radio pattern; Field provides Label, HelperText, ErrorText and `invalid`; Accordion has `multiple` and a controlled `value`; Drawer is non-modal with `modal={false}` and has `snapPoints`; Splitter follows the Window Splitter pattern with `keyboardResizeBy`. Styling: "Ark UI is a headless component library that works with any styling solution"; parts carry `data-scope`/`data-part`, state is `data-state`, and `--layer-index` is "a zero-based index for open dismissible layers". The angle-slider page documents no keyboard interactions (not found).

### [S1364] Zag.js — the state machines under Ark UI
- type: code
- url: https://github.com/chakra-ui/zag
- pinned: chakra-ui/zag@0fbee3b2e10e93774353e8b3779f6c5c29ef22ae
- author: Chakra UI
- license: MIT
- accessed: 2026-11-04
- relevance: framework-agnostic machines that @ark-ui/react 5.40.0 depends on (@zag-js/* 1.47.0); `packages/machines/` at the pin includes accordion, angle-slider, color-picker, drawer, number-input, radio-group, select, slider, splitter and switch. `ColorFormat = "rgba" | "hsla" | "hsba"` (packages/utilities/color-utils/src/types.ts L3); ColorPicker has `inline` and `format` props (packages/machines/color-picker/src/color-picker.types.ts); AngleSlider clamps to `MIN_VALUE = 0`, `MAX_VALUE = 359` (packages/machines/angle-slider/src/angle-slider.utils.ts L5-L6) while its thumb reports `role: "slider"`, `aria-valuemin` 0 and `aria-valuemax` 360 (angle-slider.connect.ts L122-L128), and handles Home/End; Drawer `modal` defaults to true (drawer.types.ts L113-L116).

### [S1365] React — useSyncExternalStore
- type: docs
- url: https://react.dev/reference/react/useSyncExternalStore
- author: Meta / React team
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073705/https://react.dev/reference/react/useSyncExternalStore
- relevance: "a React Hook that lets you subscribe to an external store"; `getSnapshot` must return the same value while the store is unchanged and an immutable snapshot when it changes, compared by `Object.is` — the contract for a socket-fed store with per-param subscriptions.

### [S1366] React Compiler v1.0 (react.dev blog, 2025-10-07)
- type: article
- url: https://react.dev/blog/2025/10/07/react-compiler-1
- author: Lauren Tan, Joe Savona, Mofei Zhang (Meta)
- published: 2025-10-07
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073833/https://react.dev/blog/2025/10/07/react-compiler-1
- relevance: "the compiler's first stable release"; "a build-time tool that optimizes your React app through automatic memoization", "implemented as a Babel plugin currently", usable from Vite through the React plugin; `useMemo`/`useCallback` remain escape hatches.

### [S1367] Vite — Getting Started (v8 docs)
- type: docs
- url: https://vite.dev/guide/
- author: Vite team (VoidZero)
- license: MIT (package vite)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261104195425/https://vite.dev/guide/  # captured 2026-11-04
- relevance: Vite is a dev server plus "A build command that bundles your code with Rolldown" (v8.3.6 docs); "Vite requires Node.js version 20.19+, 22.12+" — Node is a build-time requirement only.

### [S1368] Vite — server options (server.proxy, server.host)
- type: docs
- url: https://vite.dev/config/server-options
- author: Vite team (VoidZero)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105073956/https://vite.dev/config/server-options
- relevance: `server.proxy` proxies websockets with `ws: true` and supports `changeOrigin`; it warns "Vite does not check the origin of WebSocket requests before proxying" and that `rewriteWsOrigin` "can leave the proxying open to CSRF attacks"; `server.host` defaults to `'localhost'`.

### [S1369] vite-plugin-singlefile
- type: code
- url: https://github.com/richardtallent/vite-plugin-singlefile
- pinned: richardtallent/vite-plugin-singlefile@59e8faa9ed8df908baf06b86101641d8abd73ca3
- author: Richard Tallent
- license: MIT
- accessed: 2026-11-04
- relevance: inlines "all JavaScript and CSS resources directly into the final `dist/index.html`" so the app ships as one HTML file; caveats: `public` folder files are not inlined, and dynamic `import()` or lazy routes can leave non-inlined chunks (README). Version 2.3.4 peers on vite ^5.4.21 through ^8.0.0.

### [S1370] Vitest — Browser Mode
- type: docs
- url: https://vitest.dev/guide/browser/
- author: Vitest team
- license: MIT (package vitest)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074143/https://vitest.dev/guide/browser/
- relevance: runs tests "in the browser natively"; a provider is required (`preview`, `playwright`, `webdriverio`); playwright supports chromium, firefox and webkit; providers ship as `@vitest/browser-playwright`, React rendering as community `vitest-browser-react`.

### [S1371] Web Awesome — Color Picker and component index
- type: docs
- url: https://webawesome.com/docs/components/color-picker
- also: https://webawesome.com/docs/components/ (component index)
- author: Font Awesome (Web Awesome team)
- license: MIT (package @awesome.me/webawesome 3.14.0)
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074221/https://webawesome.com/docs/components/color-picker
- relevance: rejected-alternative evidence. The colour picker opens only as a dropdown from a trigger button (the `open` attribute "Indicates whether or not the popup is open"; no inline mode documented); formats hex/rgb/hsl/hsv. The component index has a linear Slider, Radio Group, Drawer and Split Panel but no angle slider, knob or dial.

### [S1372] React Aria (adobe/react-spectrum, react-aria-components)
- type: code
- url: https://react-aria.adobe.com/ColorPicker
- pinned: adobe/react-spectrum@36f3adde26ccd12f3cc18c9d0293ece0f10e94c7
- author: Adobe
- license: Apache-2.0
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074259/https://react-aria.adobe.com/ColorPicker
- relevance: rejected-alternative evidence. "style-free out of the box"; ColorPicker composes ColorArea, ColorSlider, ColorWheel and ColorField. `packages/react-aria-components/src` at the pin has Slider, ToggleButtonGroup, Disclosure, Modal and Sheet but no Splitter and no general angle slider (ColorWheel is hue-only).

### [S1373] Tweakpane
- type: code
- url: https://tweakpane.github.io/docs/
- pinned: cocopon/tweakpane@50a18c3dba67cb78431d7248dbe4d5a76336885a
- author: Hiroki Kokubun (cocopon)
- license: MIT
- published: last release 4.0.5, 2024-11-03; last commit 2026-03-15
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074356/https://tweakpane.github.io/docs/
- relevance: rejected-alternative evidence. "Compact pane library for fine-tuning parameters and monitoring value changes" with Number, String, Boolean, Color and Point bindings; the docs say nothing about touch or mobile, and no release in two years.

### [S1374] W3C — Understanding WCAG 2.2 SC 2.5.8 Target Size (Minimum)
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261002233942/https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html  # snapshot 2026-10-02 (predates accessed date)
- relevance: Level AA: "The size of the target for pointer inputs is at least 24 by 24 CSS pixels", with listed exceptions.

### [S1375] W3C — Understanding WCAG 2.2 SC 2.5.5 Target Size (Enhanced)
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261010171426/https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html  # snapshot 2026-10-10 (predates accessed date)
- relevance: Level AAA: "The size of the target for pointer inputs is at least 44 by 44 CSS pixels", with listed exceptions.

### [S1376] W3C — Understanding WCAG 2.2 SC 2.5.7 Dragging Movements
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261011212220/https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html  # snapshot 2026-10-11 (predates accessed date)
- relevance: Level AA: "All functionality that uses a dragging movement for operation can be achieved by a single pointer without dragging", unless dragging is essential; the examples name a range slider's thumb.

### [S1377] W3C ARIA Authoring Practices — Slider pattern
- type: spec
- url: https://www.w3.org/WAI/ARIA/apg/patterns/slider/
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261006034825/https://www.w3.org/WAI/ARIA/apg/patterns/slider/  # snapshot 2026-10-06 (predates accessed date)
- relevance: the focusable control has role `slider` with `aria-valuenow`, `aria-valuemin` and `aria-valuemax`; use `aria-valuetext` "If the value of aria-valuenow is not user-friendly"; arrows step, Home/End go to the range ends, Page Up/Down are optional larger steps.

### [S1378] MDN — Screen Wake Lock API
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074739/https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API
- relevance: "prevents the screen from turning off, dimming or locking"; "available only in secure contexts (HTTPS)"; Baseline 2025.

### [S1379] MDN — Secure contexts
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074829/https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts
- relevance: potentially trustworthy origins are `https`, `wss` and `file` schemes, `127.0.0.0/8`, `::1`, and `localhost`/`*.localhost`; a plain `http://` URL is "Not secure". Inference: a phone loading the page from the laptop's LAN address over http is not a secure context.

### [S1380] MDN — pointer media feature
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/pointer
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105074935/https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/pointer
- relevance: tests "how accurate the _primary_ pointing device is": `coarse` is "a finger on a touchscreen", `fine` "such as a mouse"; `any-pointer` tests any device.

### [S1381] MDN — hover media feature
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/hover
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075041/https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/hover
- relevance: tests whether the primary input "can conveniently hover"; `none` covers many mobile devices.

### [S1382] MDN — Container size and style queries
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_size_and_style_queries
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075219/https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_size_and_style_queries
- relevance: `@container` styles elements "based on a containing element's size ... rather than the viewport's"; declare with `container-type: inline-size`.

### [S1383] MDN — `<meta name="viewport">`
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport
- author: Mozilla
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075243/https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport
- relevance: `viewport-fit=cover` scales the viewport "to fill the device display" and the page should then use the safe-area inset variables; `interactive-widget=resizes-content` makes the viewport resize for the on-screen keyboard (default `resizes-visual`).

### [S1384] Pydantic — validation errors
- type: docs
- url: https://pydantic.dev/docs/validation/latest/errors/errors/
- author: Pydantic
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075332/https://pydantic.dev/docs/validation/latest/errors/errors/
- relevance: a `ValidationError` prints as "N validation errors for Model", then the field location and e.g. "Input should be greater than 42 [type=greater_than, input_value=21, input_type=int]"; `errors()` entries carry `type`, `loc`, `msg`, `input`, `ctx` and `url`. Its wording is not pewpew's refusal wording.

### [S1385] PyPI — pydantic 2.14.2 and pydantic-core 2.50.2
- type: product
- url: https://pypi.org/project/pydantic-core/2.50.2/
- also: https://pypi.org/pypi/pydantic/2.14.2/json (requires_dist)
- author: Pydantic
- license: MIT
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075725/https://pypi.org/project/pydantic_core/2.50.2/
- relevance: pydantic 2.14.2 requires `pydantic-core==2.50.2`, which ships 140 platform-specific wheels plus an sdist and no pure-Python wheel (PyPI JSON API, 2026-11-04) — a compiled dependency.

### [S1386] npm registry — versions and licenses of the page build stack
- type: product
- url: https://registry.npmjs.org/@ark-ui/react/5.40.0
- also: https://registry.npmjs.org/<package>/<version> for each package and version below
- author: npm, Inc.
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261105075910/https://registry.npmjs.org/@ark-ui/react/5.40.0
- relevance: `npm view` on 2026-11-04: react 19.3.1 (MIT, released 2026-10-14), @ark-ui/react 5.40.0 (MIT), @zag-js/core 1.47.0 (MIT), vite 8.3.6 (MIT), vite-plugin-singlefile 2.3.4 (MIT), vitest 5.1.0 (MIT), tweakpane 4.0.5 (MIT, last modified 2024-11-03), @awesome.me/webawesome 3.14.0 (MIT), react-aria-components 1.22.1 (Apache-2.0), typescript 7.0.2 (Apache-2.0), @vitejs/plugin-react 6.2.1, @rolldown/plugin-babel 0.3.0, babel-plugin-react-compiler 1.0.0, @vitest/browser-playwright 5.1.0, vitest-browser-react 2.3.0, pnpm 12.16.1 (all MIT). Every page dependency is permissive (ADR-012).

### [S1387] Python docs — Descriptor Guide
- type: docs
- url: https://docs.python.org/3/howto/descriptor.html
- author: Raymond Hettinger (Python Software Foundation)
- license: PSF documentation license
- accessed: 2026-11-04
- archive: https://web.archive.org/web/20261104023532/https://docs.python.org/3/howto/descriptor.html
- relevance: a descriptor with only `__get__` is a non-data descriptor; "If an instance's dictionary has an entry with the same name as a non-data descriptor, the dictionary entry takes precedence" — so a value set on the instance at bind is read as a plain attribute, past the descriptor.

### [S1388] npm registry — pnpm 10.33.2
- type: product
- url: https://registry.npmjs.org/pnpm/10.33.2
- author: npm, Inc.
- published: 2026-04-23
- accessed: 2026-11-05
- archive: not found; no snapshot existed on 2026-11-05 and none was taken
- relevance: The version `web/package.json` pins for `packageManager` and `engines` (the `latest` dist-tag that day was 12.16.1); license MIT. Its registry `time` gives the 2026-04-23 release.

### [S1389] pyserial (upstream repository)
- type: code
- url: https://github.com/pyserial/pyserial
- pinned: pyserial/pyserial@a5c48d445fbc1943d4fabf8d9090a50fda3172fd
- author: Chris Liechti and pyserial contributors
- license: BSD-3-Clause (LICENSE.txt's SPDX identifier; GitHub reports NOASSERTION)
- published: 3.5 uploaded to PyPI 2020-11-23; last commit 2026-02-27
- accessed: 2026-11-05
- relevance: the USB-serial library `pewpew wifi` uses for Improv board setup, a runtime dependency in `pyproject.toml`; permissive, so ADR-012 allows it as a dependency.

### [S1390] Jackson, Barth, Bortz, Shao, Boneh — Protecting Browsers from DNS Rebinding Attacks (CCS 2007)
- type: article
- url: https://crypto.stanford.edu/dns/dns-rebinding.pdf
- author: Collin Jackson, Adam Barth, Andrew Bortz, Weidong Shao, Dan Boneh (Stanford University)
- published: 2007-10 (ACM CCS '07)
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261002230827/https://crypto.stanford.edu/dns/dns-rebinding.pdf (snapshot predates accessed date; refresh next verification pass)
- relevance: DNS rebinding makes a browser treat a rebound name as one origin with the attacker's page; "One server-side defense for these attacks is therefore to reject incoming HTTP requests with unexpected Host headers" (§5.3, "Checking Host Header"). The basis for refusing a non-IP `Host`.

### [S1391] npm registry — licenses of the versions `web/package.json` pins
- type: product
- url: https://registry.npmjs.org/playwright/1.64.1
- also: https://registry.npmjs.org/<package>/<version> for each package and version below
- author: npm, Inc.
- accessed: 2026-11-05
- archive: not found; no snapshot of these registry records existed on 2026-11-05, and Save Page Now was not run
- relevance: the `license` field of every exact pin in `web/package.json` at commit d01d23a: MIT, except playwright 1.64.1 and typescript 7.0.2 (Apache-2.0).

### [S1392] W3C — Understanding WCAG 2.2 SC 2.1.4 Character Key Shortcuts
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261024223331/https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html  # snapshot 2026-10-24 (predates accessed date)
- relevance: Level A: a shortcut "using only letter (including upper- and lower-case letters), punctuation, number, or symbol characters" needs a mechanism to turn it off, to remap it to include a non-printable key, or to be active only on focus; the intent names speech input users, "whose dictation is interpreted as strings of letters".

### [S1393] W3C WAI-ARIA Authoring Practices Guide — Switch Pattern
- type: spec
- url: https://www.w3.org/WAI/ARIA/apg/patterns/switch/
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20260529135114/https://www.w3.org/WAI/ARIA/apg/patterns/switch/  # snapshot 2026-05-29 (predates accessed date)
- relevance: a switch is binary input, "on or off"; its examples include "Switch Example Using HTML Checkbox Input" on `input[type="checkbox"]` elements; Space changes the state; the element has role `switch`, and "the label on a switch does not change when its state changes".

### [S1394] W3C WAI-ARIA Authoring Practices Guide — Button Pattern
- type: spec
- url: https://www.w3.org/WAI/ARIA/apg/patterns/button/
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261027043032/https://www.w3.org/WAI/ARIA/apg/patterns/button/  # snapshot 2026-10-27 (predates accessed date)
- relevance: a toggle button is "a two-state button that can be either off (not pressed) or on (pressed)", marked by `aria-pressed`; Space and Enter activate a button; the label does not change with the state.

### [S1395] web-features explorer — `<dialog closedby>`
- type: docs
- url: https://web-platform-dx.github.io/web-features-explorer/features/dialog-closedby/
- author: web-platform-dx (GitHub organization)
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20251213004954/https://web-platform-dx.github.io/web-features-explorer/features/dialog-closedby/  # snapshot 2025-12-13 (predates accessed date; Safari unsupported there too)
- relevance: `closedby="any"` "allows the dialog to be closed by clicking outside of it"; supported from Chrome 134 and Firefox 141; Safari and Safari on iOS "Not supported" on 2026-11-05 (Safari 27.2 current), so Baseline is "blocked since July 2025 by Safari".

### [S1396] Vite — Backend Integration (v8 docs)
- type: docs
- url: https://vite.dev/guide/backend-integration
- author: Vite team (VoidZero)
- license: MIT (package vite)
- accessed: 2026-11-08
- archive: https://web.archive.org/web/20261002161049/https://vite.dev/guide/backend-integration  # snapshot 2026-10-02
- relevance: for HTML served by a backend rather than Vite; `build.manifest` writes a manifest that "maps source files to their build outputs and dependencies", with each chunk's `imports` ("statically imported chunks"), `dynamicImports` ("dynamically imported chunks") and `css`, so a backend can tell which built files a page loads and which load on demand.

## Block S1400–S1449 — RA-25 Layered effects & effect programs

### [S1400] hydra-synth (Hydra live-coding video synth)
- type: code
- url: https://github.com/hydra-synth/hydra-synth
- pinned: hydra-synth/hydra-synth@9d29a9f4fd8f9081b9759943f38db36f05b9a88f
- author: Olivia Jack and hydra-synth contributors
- license: AGPL-3.0 (GitHub API, 2026-11-05) — idea source only under ADR-012
- published: commit 2026-07-16 (main)
- accessed: 2026-11-05
- relevance: a chain of method calls compiled to one shader. `src/glsl/glsl-functions.js` gives every function one of five transform types (`src` 9, `coord` 10, `color` 16, `combine` 7, `combineCoord` 11). `src/generate-glsl.js` emits a `coord` or `combineCoord` step as `uv = f(uv, ...)` before the earlier steps run, so a coordinate op warps everything before it, while `color` and `combine` steps apply forwards; an argument that is itself a chain compiles recursively on a copy of the current `uv`. `src/format-arguments.js` turns a function or an array argument into a per-frame uniform.

### [S1401] Chromatik Guide — Mixer
- type: docs
- url: https://chromatik.co/guide/mixer/
- author: Heron Arts / Mark Slee
- published: n/a (living docs)
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165336/https://chromatik.co/guide/mixer/
- relevance: each channel has Enabled, Fader, View ("selects a sub-view of the model for this channel"), Blend Mode and an A/B crossfader assignment; a fader at 0 still runs the channel's animation; a group composites its channels left to right and then blends as one channel with its own blend mode, and "Groups may not contain other groups, only one level of nesting is supported"; Normal blending replaces "subject to alpha transparency (which is treated linearly)", called Dissolve on the crossfader.

### [S1402] Chromatik API — heronarts.lx.blend.LXBlend
- type: docs
- url: https://chromatik.co/api/heronarts/lx/blend/LXBlend.html
- author: Heron Arts / Mark Slee
- accessed: 2026-11-05
- archive: not found; no snapshot existed on 2026-11-05, and Save Page Now was not run
- relevance: a blend is an object with `blend(int[] dst, int[] src, double alpha, int[] output, LXModel model)`, writing into an output buffer over the points of a model; `lerp(from, to, amt, output, model)` "Transitions from one buffer to another" by blending from-to with alpha 0–1, then to-from with alpha 1–0. Buffers are packed `int[]` colors, so LX blends stored 8-bit values.

### [S1403] Adafruit Learning System — WLED 16: segment layering and blend modes
- type: article
- url: https://learn.adafruit.com/wled-16-what-is-new/segment-layering-and-blend-modes
- author: Adafruit
- published: page last edited 2026-06-15
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165343/https://learn.adafruit.com/wled-16-what-is-new/segment-layering-and-blend-modes
- relevance: WLED 16 blends overlapping segments per segment, lower segment ID at the bottom, with Top, Bottom, Add ("clamping at white"), Subtract, Difference, Average, Multiply, Divide, Lighten, Darken, Screen, Overlay, Hard Light, Soft Light, Dodge, Burn and Stencil ("Shows top where it has any color; shows bottom where top is black"). Tips: "Begin with two layers before trying five", fast stacked effects "can get visually chaotic", and "Additive blending can become very bright very quickly".

### [S1404] Resolume — Blend Modes
- type: docs
- url: https://resolume.com/support/en/blend-modes
- author: Resolume
- published: page for Resolume 7.22.5
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165423/https://resolume.com/support/en/blend-modes
- relevance: VJ compositing groups its blend modes as General (Alpha, AlphaCut), Darken, Lighten (Lighten, Screen, Dodge), Contrast, Comparative (Add, Subtract, Difference, Exclusion) and Composite (Luma Key, Luma is Alpha, Displace, 50Mask, RGB); the same modes serve layers, effects and transitions. Add is the Arena and Avenue default and "Bright visuals can quickly max out at white"; Screen is the soft alternative.

### [S1405] xLights manual — Layer Blending
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/layers/layer-blending
- author: xLights project
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165457/https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/layers/layer-blending
- relevance: effects stack in layers per model; "the current layer is considered layer 1 and the layer below is considered layer 2"; Morph makes effect 1 morph into effect 2 over the timing cell — a timeline sequencer's version of the layer stack.

### [S1406] Wikipedia — Advanced Visualization Studio
- type: article
- url: https://en.wikipedia.org/wiki/Advanced_Visualization_Studio
- author: Wikipedia contributors
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165603/https://en.wikipedia.org/wiki/Advanced_Visualization_Studio
- relevance: Winamp's AVS presets are made of components in three categories ("Render draws shapes, Trans transforms the current image and Misc ..."), pre-defined effects "arranged in any combination", later codeable components (SuperScope, Dynamic Movement); open-sourced in May 2005 under a BSD-style license.

### [S1407] Ryan Geiss — MilkDrop preset authoring guide
- type: docs
- url: https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html
- author: Ryan Geiss
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165618/https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html
- relevance: a preset "is a collection of parameters that tell MilkDrop how to draw the wave, how to warp the image around, and so on"; per-frame code sets the motion variables, `decay` "controls the eventual fade to black; 1=no fade, 0.9=strong fade, 0.98=recommended", custom shapes can be textured "with the image from the previous frame", and MilkDrop 2 moves the warp and composite into pixel shaders. The feedback-loop lineage.

### [S1408] webvs — a Winamp AVS-like visualization library for the web
- type: code
- url: https://github.com/azeem/webvs
- pinned: azeem/webvs@17166a12705a6ab26ec2e2e9b258f7478c7a81cf
- author: Azeem Arshad
- license: MIT (GitHub API, 2026-11-05)
- published: last commit 2018-06-25
- accessed: 2026-11-05
- relevance: an AVS reimplementation whose preset is plain JSON, `{"clearFrame": true, "components": [{"type": "SuperScope", "source": "WAVEFORM", "code": {...}, "colors": [...]}]}` (README.md): a stack of typed components saved as data.

### [S1409] Polars — Expr.meta.serialize
- type: docs
- url: https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.meta.serialize.html
- author: Polars contributors
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165648/https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.meta.serialize.html
- relevance: a fluent expression library serializes its expression trees, and warns: "Serialization is not stable across Polars versions: a LazyFrame serialized in one Polars version may not be deserializable in another Polars version." A library's internal tree format is not a save format.

### [S1410] Python Language Reference — Data model: customizing class creation
- type: docs
- url: https://docs.python.org/3/reference/datamodel.html
- author: Python Software Foundation
- license: PSF documentation license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165714/https://docs.python.org/3/reference/datamodel.html
- relevance: §3.3.3: "Whenever a class inherits from another class, `__init_subclass__()` is called on the parent class. This way, it is possible to write classes which change the behavior of subclasses"; keyword arguments in the class statement reach it. The hook a base class uses to register its subclasses.

### [S1411] NumPy — numpy.random.SeedSequence
- type: docs
- url: https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html
- author: NumPy developers
- accessed: 2026-11-05
- archive: not found; no snapshot existed on 2026-11-05, and Save Page Now was not run
- relevance: "SeedSequence mixes sources of entropy in a reproducible way to set the initial state for independent and very probably non-overlapping BitGenerators"; entropy may be a sequence of integers and `generate_state` returns the derived words.

### [S1412] NumPy — Philox counter-based RNG
- type: docs
- url: https://numpy.org/doc/stable/reference/random/bit_generators/philox.html
- author: NumPy developers
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165743/https://numpy.org/doc/stable/reference/random/bit_generators/philox.html
- relevance: `Philox(seed=None, counter=None, key=None)`, a 4x64 counter-based generator: a stream is fixed by its key and counter, so a draw for a given (key, tick) is reproducible without carried generator state. The 256-bit counter "is incremented by 1 for every 4 64-bit randoms produced", so streams that start at consecutive counters overlap; the 128-bit key "determined the sequence produced. Using different keys produces independent sequences" (the class docstring the page renders; checked against NumPy 2.4.6).

### [S1413] Python docs — Command line and environment (`PYTHONHASHSEED`)
- type: docs
- url: https://docs.python.org/3/using/cmdline.html
- author: Python Software Foundation
- license: PSF documentation license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165810/https://docs.python.org/3/using/cmdline.html
- relevance: "If this variable is not set or set to random, a random value is used to seed the hashes of str and bytes objects"; hash randomization is on by default. So `hash()` of a layer or node name differs between runs and cannot seed anything that must be byte-identical.

### [S1414] Python Packaging User Guide — Creating and discovering plugins
- type: docs
- url: https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
- author: Python Packaging Authority
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165837/https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
- relevance: plugins are found by naming convention, namespace packages, or package metadata: "Packages can have metadata for plugins described in the Entry points specification", which another installed package reads to discover them. The packaging-level alternative to an in-process registry.

### [S1415] Inigo Quilez — Palettes
- type: article
- url: https://iquilezles.org/articles/palettes/
- author: Inigo Quilez
- accessed: 2026-11-05
- archive: not found; no snapshot existed on 2026-11-05, and Save Page Now was not run
- relevance: a procedural palette is `color(t) = a + b ⋅ cos[2π(c⋅t+d)]`, four RGB vectors: twelve floats that loop and interpolate, but that name no colors a person picks.

### [S1416] W3C CSS Color Module Level 4 (Editor's Draft) — color interpolation
- type: spec
- url: https://drafts.csswg.org/css-color-4/
- author: W3C CSS Working Group
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165906/https://drafts.csswg.org/css-color-4/
- relevance: "If the host syntax does not define what color space interpolation should take place in, it defaults to Oklab" (the changes list: "Host syntax that does not declare a default now uses Oklab by default"), and a constant-hue CIE Lab blend toward blue shows "noticeable purpling" that an OkLCh slice does not. The web platform's gradients interpolate in Oklab.

## Block S1450–S1499 — RA-26 Agent connectivity

### [S1450] MCP specification 2026-07-28 — Key changes (changelog)
- type: spec
- url: https://modelcontextprotocol.io/specification/2026-07-28/changelog
- author: Model Context Protocol project
- published: 2026-07-28
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105142046/https://modelcontextprotocol.io/specification/2026-07-28/changelog
- relevance: the final 2026-07-28 revision: "Make MCP stateless: remove the initialize / notifications/initialized handshake"; "Servers that need cross-call state use explicit, server-minted handles passed as ordinary tool arguments"; `server/discover` advertises a server's protocol versions and capabilities; "Servers SHOULD return tools from tools/list in a deterministic order"; tasks move to the `io.modelcontextprotocol/tasks` extension; `inputSchema`/`outputSchema` allow any JSON Schema 2020-12 keywords.

### [S1451] MCP specification 2026-07-28 — Server: Tools
- type: spec
- url: https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- author: Model Context Protocol project
- published: 2026-07-28
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105165941/https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- relevance: a tool result carries text, image (`{"type": "image", "data": base64, "mimeType": "image/png"}`), audio or resource content plus `structuredContent`, and "a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block"; input-validation and business errors are results with `isError: true`, and "Clients SHOULD provide tool execution errors to language models to enable self-correction"; Stateful Tools (non-normative): "MCP has no protocol-level session", so state across calls rides "an explicit handle" the model carries forward.

### [S1452] MCP Python SDK — What's new in v2
- type: docs
- url: https://py.sdk.modelcontextprotocol.io/whats-new/
- author: Model Context Protocol project
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170009/https://py.sdk.modelcontextprotocol.io/whats-new/#upgrading-from-v1
- relevance: `pip install mcp` installs 2.x; "FastMCP is now MCPServer" and the old path "is gone rather than deprecated" (`from mcp.server import MCPServer`); decorated tools keep taking their input schema from type hints.

### [S1453] MCP Python SDK — Structured output
- type: docs
- url: https://py.sdk.modelcontextprotocol.io/servers/structured-output/
- author: Model Context Protocol project
- accessed: 2026-11-05
- archive: not found; no snapshot existed on 2026-11-05, and Save Page Now was not run
- relevance: "the return type annotation is the output schema"; a tool may return a model, a TypedDict or a dataclass ("The SDK builds a Pydantic model out of the annotations behind the scenes"), and a result goes out on two channels, text `content` and `structured_content`.

### [S1454] MCP Python SDK — Images, audio & icons
- type: docs
- url: https://py.sdk.modelcontextprotocol.io/servers/media/
- author: Model Context Protocol project
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170042/https://py.sdk.modelcontextprotocol.io/servers/media/
- relevance: a tool annotated to return `Image` (`from mcp.server.mcpserver import Image`) sends image content; with raw `data=` bytes the caller must pass `format=`, or the SDK labels it `image/png`.

### [S1455] Anthropic engineering — Introducing advanced tool use on the Claude Developer Platform
- type: article
- url: https://www.anthropic.com/engineering/advanced-tool-use
- author: Anthropic
- published: 2025-11-24
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170110/https://www.anthropic.com/research/advanced-tool-use
- relevance: `input_examples` on a tool definition show concrete calls; "In our own internal testing, tool use examples improved accuracy from 72% to 90% on complex parameter handling". Also the Tool Search Tool and programmatic tool calling.

### [S1456] Claude Platform docs — Vision
- type: docs
- url: https://platform.claude.com/docs/en/build-with-claude/vision
- author: Anthropic
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170139/https://platform.claude.com/docs/en/build-with-claude/vision
- relevance: "An image, therefore, costs ⌈width / 28⌉ × ⌈height / 28⌉ visual tokens" (a 200×200 image is 64 tokens, 1000×1000 is 1,296), and Claude "might hallucinate or make mistakes when interpreting low-quality, rotated, or very small images under 200 pixels".

### [S1457] Agent Skills — Specification
- type: spec
- url: https://agentskills.io/specification
- author: Agent Skills project
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170220/https://agentskills.io/specification
- relevance: a skill is a folder with `SKILL.md`: YAML frontmatter with `name` (max 64 characters, lowercase, digits, hyphens) and `description` (max 1024 characters, "Describes what the skill does and when to use it"), then Markdown, with optional `scripts/`, `references/` and `assets/` and a "Progressive disclosure" section on keeping the main file short.

### [S1458] Claude Code docs — Create custom subagents
- type: docs
- url: https://code.claude.com/docs/en/sub-agents
- author: Anthropic
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170246/https://code.claude.com/docs/en/sub-agents
- relevance: a subagent is a Markdown file under `.claude/agents/` (or `~/.claude/agents/`) whose frontmatter gives `name`, `description`, a `tools` list and a `model`, followed by its system prompt; the `tools` field limits the tools it may call.

### [S1459] Claude Code docs — How Claude remembers your project (memory)
- type: docs
- url: https://code.claude.com/docs/en/memory
- author: Anthropic
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170315/https://code.claude.com/docs/en/memory
- relevance: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence. Move instructions that matter for only part of the codebase into path-scoped rules", which load only when Claude works with matching files (`.claude/rules/`).

### [S1460] Gu et al. — A Survey on LLM-as-a-Judge (arXiv:2411.15594)
- type: article
- url: https://arxiv.org/abs/2411.15594
- author: Jiawei Gu, Xuhui Jiang, Zhichao Shi, et al.
- published: 2024-11-23 (v6 2025-10-19)
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170343/https://arxiv.org/abs/2411.15594
- relevance: reliability of LLM judges "remains a significant challenge"; their inherent biases include "length bias, position bias, and concreteness bias", and "position bias, which is common in pairwise evaluations" is mitigated by "randomly swapping contents to be evaluated" (full text, arxiv.org/html/2411.15594v6).

### [S1461] Li et al. — AesBiasBench: Evaluating Bias and Alignment in Multimodal Language Models for Personalized Image Aesthetic Assessment (arXiv:2509.11620)
- type: article
- url: https://arxiv.org/abs/2509.11620v1
- author: Kun Li, Lai-Man Po, Hongzheng Yang, et al.
- published: 2025-09-15
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170408/https://arxiv.org/abs/2509.11620v1
- relevance: 19 multimodal models, Claude-3.5-Sonnet and GPT-4o among them, judging image aesthetics: "their predictions may reflect subtle biases", "smaller models exhibit stronger stereotype biases, whereas larger models align more closely with human preferences" — a vision model's aesthetic verdict is a biased estimate, not ground truth.

### [S1462] RFC 2083 — PNG (Portable Network Graphics) Specification Version 1.0
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc2083
- author: T. Boutell et al.
- published: 1997-03
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20260513034151/https://www.rfc-editor.org/rfc/rfc2083 (snapshot predates accessed date; refresh next verification pass)
- relevance: a PNG is a signature plus chunks, each with a 4-byte CRC "calculated on the preceding bytes in the chunk, including the chunk type code and chunk data fields"; image data is a zlib datastream with "method code 8 ("deflate")"; `tIME` ("the time of the last image modification") is an ancillary chunk an encoder may leave out. Everything an RGB8 encoder needs is in Python's stdlib `zlib`.

### [S1463] PyPI — pillow 13.0.0
- type: product
- url: https://pypi.org/project/pillow/
- also: https://pypi.org/pypi/pillow/json
- author: Jeffrey 'Alex' Clark and contributors
- license: MIT-CMU
- published: 13.0.0
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170610/https://pypi.org/project/pillow/
- relevance: the "friendly PIL fork" ships 13.0.0 as 82 platform-specific wheels plus an sdist and no pure-Python wheel (PyPI JSON API, 2026-11-05): a compiled dependency.

### [S1464] W3C — Understanding WCAG 2.2 SC 2.3.1 Three Flashes or Below Threshold
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
- author: W3C Web Accessibility Initiative
- accessed: 2026-11-05 (read through the archive snapshot; w3.org answered 403 to a script)
- archive: https://web.archive.org/web/20261001165853/https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html (snapshot predates accessed date; it is the copy read)
- relevance: "Web pages do not contain anything that flashes more than three times in any one second period, or the flash is below the general flash and red flash thresholds"; a flash is "a pair of opposing changes in relative luminance". The limit `tests/test_canopy_patterns.py` already counts against.

### [S1465] JSON-RPC 2.0 Specification
- type: spec
- url: https://www.jsonrpc.org/specification
- author: JSON-RPC Working Group
- published: 2010-03-26 (origin date; later updated)
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261019190342/https://www.jsonrpc.org/specification (snapshot predates accessed date; refresh next verification pass)
- relevance: a response's `id` "is REQUIRED. It MUST be the same as the value of the id member in the Request Object" — the request-id echo that lets a client match an answer to its request over one socket.

### [S1466] Python docs — ipaddress
- type: docs
- url: https://docs.python.org/3/library/ipaddress.html
- author: Python Software Foundation
- license: PSF documentation license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170715/https://docs.python.org/3/library/ipaddress.html
- relevance: `is_loopback` is "True if this is a loopback address. See RFC 3330 (for IPv4) or RFC 2373 (for IPv6)" — a stdlib test for 127.0.0.0/8 and ::1.

### [S1467] Anthropic engineering — Code execution with MCP
- type: article
- url: https://www.anthropic.com/engineering/code-execution-with-mcp
- author: Anthropic
- published: 2025-11-04
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261019193540/https://www.anthropic.com/engineering/code-execution-with-mcp (snapshot predates accessed date; refresh next verification pass)
- relevance: loading tool definitions on demand instead of all up front "reduces the token usage from 150,000 tokens to 2,000 tokens" — progressive disclosure keeps a large catalog out of the context until it is needed.

### [S1468] PyPI — mcp 2.3.0 (MCP Python SDK)
- type: product
- url: https://pypi.org/project/mcp/
- also: https://pypi.org/pypi/mcp/json
- author: Model Context Protocol project (Anthropic)
- license: MIT
- published: 2.3.0
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261105170858/https://pypi.org/project/mcp/
- relevance: `requires_python >=3.10`; its unconditional `requires_dist` includes pydantic, starlette, uvicorn, sse-starlette, httpx2, jsonschema, pyjwt and opentelemetry-api (PyPI JSON API, 2026-11-05) — a web stack, not a small library.

### [S1469] Python docs — socket.create_connection
- type: docs
- url: https://docs.python.org/3/library/socket.html#socket.create_connection
- author: Python Software Foundation
- license: PSF documentation license
- accessed: 2026-11-05
- archive: https://web.archive.org/web/20261027202158/https://docs.python.org/3/library/socket.html (snapshot predates accessed date; refresh next verification pass)
- relevance: "if host is a non-numeric hostname, it will try to resolve it for both AF_INET and AF_INET6, and then try to connect to all possible addresses in turn until a connection succeeds" — so a client that checks only one resolved address may still connect to another; a tier-1 write must check every address and connect to the one it checked.

## Block S1500–S1549 — RA-27 Control-page UX

### [S1500] Resolume Arena manual — clips, decks, layers, effects, dashboard
- type: docs
- url: https://resolume.com/support/en/clips
- also: https://resolume.com/support/en/decks, https://resolume.com/support/en/layers, https://resolume.com/support/en/effects, https://resolume.com/support/en/dashboard
- author: Resolume
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: clips: a grid of layers (rows) × columns, a clip fires on a thumbnail click, has a settable thumbnail and an optional pastel colour, a column fires all its clips "to switch between looks that work well together", persistent clips keep their slot in every deck; decks: group the grid "like the records in a DJ's record bag", picked from a button row, named, colour-coded, closable without deleting; layers: each strip has blend and opacity, and Layer Properties' Blend Mode and Opacity "match the layer strip controls"; effects: sit at clip, layer/group and composition level; dashboard: dials for the most-used parameters. S1404 is the blend-modes page.

### [S1501] Resolume blog — Arena 7.7 and 7.22 release notes
- type: article
- url: https://resolume.com/blog/27125
- also: https://resolume.com/blog/21042
- author: Resolume
- accessed: 2026-11-05
- relevance: 7.22 (blog/27125): selecting a column no longer fires it; a separate play button does. 7.7 (blog/21042): a heart favourites an effect or source, and favourites rise to the top of the lists.

### [S1502] Ryan Geiss — MilkDrop 2 documentation
- type: docs
- url: https://geisswerks.com/milkdrop/milkdrop.html
- author: Ryan Geiss
- accessed: 2026-11-05
- relevance: the performer seldom browses the preset library: random and next traversal, ratings 0–5 that "decide how often the presets will be randomly loaded" (0 keeps a preset out of random play); L opens a load menu; BACKSPACE steps back through up to 64 recent presets; Scroll Lock pins the current preset; Space blends to the next, H hard-cuts; A mashes two random presets' shaders into a new one and S saves it. Actions are keys, never preset buttons. S1407 is the preset-authoring guide.

### [S1503] WLED web UI source — Presets tab (wled00/data)
- type: code
- url: https://github.com/wled/WLED
- pinned: wled/WLED@fffa05a765d41d7126b66ab5a3d1ce1f41e7d11e
- author: WLED contributors
- license: EUPL-1.2 (GitHub API, 2026-11-05)
- published: commit 2026-11-06 05:59 UTC (2026-11-05 Pacific), "Fix PWM for new chips on V5 (#5862)"
- accessed: 2026-11-05
- relevance: `wled00/data/index.htm` and `wled00/data/index.js`, read directly: the Presets tab reads top to bottom as a "Quick load" row of round buttons (labels of ≤2 characters or 1 emoji), a sticky search box, the list (playlists first with a play icon, a startup-preset icon, an edit pencil and expand arrow per row, sort by ID or name), and a bottom bar with "+ Preset" and "+ Playlist" styled unlike the rows. S001, S645 and S1250 pin earlier commits.

### [S1504] WLED docs — effects and palettes
- type: docs
- url: https://kno.wled.ge/features/effects/
- also: https://kno.wled.ge/features/palettes/
- author: WLED project
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: effect parameters include Speed and Intensity; a palette is the colour gradient an effect paints with, as in pewpew. S554 is the presets page.

### [S1505] WLED forum — "Preset ordering tip"
- type: forum
- url: https://wled.discourse.group/t/preset-ordering-tip/1698
- author: WLED forum users
- accessed: 2026-11-05
- relevance: the preset list sorts by name, so users force an order with numeric name prefixes.

### [S1506] Chromatik Guide — Devices
- type: docs
- url: https://chromatik.co/guide/devices/
- author: Heron Arts / Mark Slee
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: each channel has its own device bin and a line marks the focused channel; a separator splits pattern effects from channel effects, which cannot be reordered across it; device presets are files saved from a right-click menu. S1265 covers snapshots, the application overview and modulation; S1401 the mixer.

### [S1507] LucieMrc — Madmapper_2spi ("Utiliser Madmapper rapidement", community guide, French)
- type: docs
- url: https://github.com/LucieMrc/Madmapper_2spi
- pinned: LucieMrc/Madmapper_2spi@f6b8534a5c685459aa81ea3c9b432e2a36fdb1a5
- author: LucieMrc
- license: MIT (GitHub API, 2026-11-05)
- published: last commit 2026-03-30
- accessed: 2026-11-05
- relevance: MadMapper scenes sit in a table of cells: + in an empty cell makes one, a gear sets colour and fade; columns play once, in a loop or at random; a scene stores everything, a cue only the chosen parameters. A community guide, not GarageCube's docs (S1276).

### [S1508] MA Lighting — grandMA3 user manual: executors, preset pools
- type: docs
- url: https://help.malighting.com/grandMA3/2.4/HTML/executor.html
- also: https://help.malighting.com/grandMA3/2.5/HTML/presets_pools.html
- author: MA Lighting
- accessed: 2026-11-05
- relevance: executors are "handles and controls to other objects", and the sequences they fire live in a pool; up to 9,999 executor pages; pool windows are numbered grids with labels, appearances (colour or image) and a "Show Empty" toggle; Store with no number fills the first free slot; Store, Edit and Delete are hardware keys, never pool tiles. S1269 covers other grandMA3 pages.

### [S1509] ChamSys — MagicQ manual: Execute window
- type: docs
- url: https://docs.chamsys.co.uk/magicq/1.9.9.x/manual/execute.html
- author: ChamSys
- accessed: 2026-11-05
- relevance: a user-designed grid of up to 40×40 cells that mixes stored items with "special items" (Exec Page Up/Down, Release, Clear); separate Design and Execute views split arranging from playing; "Coloured" appearance colours buttons by function; a common setup is a Home grid of page-jump buttons.

### [S1510] Obsidian Control — Onyx manual: playback banks, virtual playback buttons, cuelist directory, selecting cuelists
- type: docs
- url: https://support.obsidiancontrol.com/Content/Onyx_Manual/Playback/Main_Playback_Pages_(Banks).htm
- also: https://support.obsidiancontrol.com/Content/Onyx_Manual/Playback/Virtual_Playback_Buttons.htm, https://support.obsidiancontrol.com/Content/Onyx_Manual/Playback/Selecting_Cuelists.htm; Cuelist_Directory/Cuelist_Directory.htm (path as given in the 2026-11-05 study; full URL not re-resolved, the guess under Onyx_Manual/ returned 404)
- author: Obsidian Control Systems
- accessed: 2026-11-05
- relevance: 500 named banks of 10 playbacks, a swipe changes bank; 100 pages of 10×10 virtual buttons on which you pick the verb (Go, Release, Select) and then the cuelist; the Cuelist Directory is the store (grid and list views, live status per tile) and playback controls only point into it, with a cuelist's colour shown everywhere; only one cuelist can be selected, and selecting does not run it.

### [S1511] ETC console manuals (third-party mirrors) — Ion Xe, Element 2
- type: docs
- url: https://www.manualslib.com/manual/1416288/Etc-Ion-Xe.html
- also: https://manualmachine.com/etc/element2controlconsole/7216631-datasheet/
- author: ETC (mirrored by ManualsLib and ManualMachine)
- accessed: 2026-11-05
- relevance: consoles call the whole-rig fader the grandmaster; on a console a palette is a stored reference, not a colour gradient. S1269 covers the ETC Ion help pages.

### [S1512] Ableton Live 12 manual — browser, Live concepts, racks (with CDM coverage)
- type: docs
- url: https://www.ableton.com/en/live-manual/12/working-with-the-browser/
- also: https://www.ableton.com/en/live-manual/12/live-concepts/ (via search), https://www.ableton.com/en/manual/instrument-drum-and-effect-racks/; https://cdm.link/?p=121062 (CDM article, a second account of Similarity Search)
- author: Ableton; CDM (Create Digital Music)
- accessed: 2026-11-05
- relevance: browser: collections are colour labels (keys 1–7 assign, 0 clears), tags in groups with a Tag Editor and Quick Tags, Ctrl/Cmd-click multi-select, Preview auditions with the arrow keys, Similarity Search's "Show Similar Files" lists results under the reference from most to least similar; racks: contents are "always contained between end brackets", the chain list drives the devices view, 8–16 Macro Controls each drive "any number of parameters", Macro Variations store their states and "Rand" randomises them, Map mode overlays mappable parameters.

### [S1513] Native Instruments — Komplete Kontrol manual: Browser
- type: docs
- url: https://docs.native-instruments.com/online-guides/komplete-kontrol-manual/en/browser
- author: Native Instruments
- accessed: 2026-11-05
- relevance: a star shows on a hovered or selected preset and a search-field icon filters to Favorites; Sound Type is a two-level hierarchy that matches any selected tag, Character tags must all match; one click auditions without loading, a double-click loads, the arrow keys step. A random control: not found.

### [S1514] Synth preset browsers — random, shuffle and favourites (survey)
- type: docs
- url: https://manual.minimal.audio/eprom-memory-rites-manual/presets.md
- also: https://soniccharge.com/forum/topic/3376-i-made-a-preset-browser-for-synplant-2-free?~post16436 (forum); https://www.kvraudio.com/forum/viewtopic.php?p=8694632 (forum, Arturia Analog Lab); https://rekkerd.org/analog-lab-2-instrument-by-arturia-released/ (article); https://xferrecords.com/web-manual/serum-2/loading-a-serum-preset; https://torley.substack.com/p/whats-missing-from-electronic-music (article); https://forum.vital.audio/t/shuffle-presets/10685 (forum)
- author: Minimal Audio; Sonic Charge forum user; KVR forum users; Rekkerd; Xfer Records; Torley; Vital forum users
- accessed: 2026-11-05
- relevance: Eprom's browser Random "loads a randomly selected preset instantly", beside a Heart and category filters; a community Synplant 2 browser's random "jumps to a random preset, respecting the active filter", with a star per row and a Favorites view; Analog Lab's shuffle icon reorders the list without loading, and a user asked for a separate dice button; Analog Lab playlists hold sounds for program-change recall; Serum 2's < > arrows step the subfolder; Vital and Serum 2 have no random loader (Substack) and Vital users ask for one. Where random exists it sits in the browser chrome; none was found among the preset items.

### [S1515] Lightroom Killer Tips — presets and profiles
- type: article
- url: https://lightroomkillertips.com/give-recommended-presets-a-try/
- also: https://lightroomkillertips.com/?p=10957, https://lightroomkillertips.com/tips-for-managing-profiles/
- author: Lightroom Killer Tips
- accessed: 2026-11-05
- relevance: hovering a preset thumbnail previews it on the photo (a preference turns this off); the Recommended tab's hover button "More like this" "will filter the presets down further"; a starred profile appears in a Favorites folder at the top and in the Basic panel drop-down; Manage Presets hides unused groups. Third-party: Adobe's help returned 403.

### [S1516] Procreate Handbook — Brush Library
- type: docs
- url: https://help.procreate.com/procreate/handbook/brushes/brush-library
- author: Savage Interactive (Procreate)
- accessed: 2026-11-05
- relevance: the Recent set fills itself with up to eight brushes and a brush can be pinned there; each brush row previews "the stroke it makes"; sets can be created, brushes and sets dragged to reorder, and a swipe duplicates a brush.

### [S1517] Rearranging Instagram filters — third-party guides (How-To Geek, Cult of Mac)
- type: article
- url: https://www.howtogeek.com/299133/how-to-rearrange-your-instagram-filters-and-hide-the-ones-you-dont-like/
- also: https://www.cultofmac.com/?p=413930
- author: How-To Geek; Cult of Mac
- accessed: 2026-11-05
- relevance: a Manage item with a gear icon ends the filter row and opens a screen to drag filters into a new order and uncheck the ones to hide. Third-party guides; the current app may differ.

### [S1518] Roland — XPS-60 FAVORITE scenes (support article and reference manual)
- type: docs
- url: https://support.roland.com/hc/en-us/articles/33546774473371-XPS-60-How-Do-I-Quickly-Recall-Frequently-Used-Scenes-FAVORITE
- also: https://static.roland.com/assets/media/pdf/XPS-60_reference_eng04_W.pdf
- author: Roland
- accessed: 2026-11-05
- relevance: hold FAVORITE and press [1]–[16] to store a scene; 16 banks of 16 slots ("Favorite 256" in the spec); an asterisk marks an edited, unsaved scene, which must be saved before it can be stored; the same 16 buttons select tone categories in another mode.

### [S1519] Line 6 — Helix owner's manual and cheat sheet (Thomann mirrors)
- type: docs
- url: https://images.static-thomann.de/pics/atg/atgdata/document/misc/helix_owners_manual_rev_b_english_rev.pdf
- also: https://im.static-thomann.de/pics/atg/atgdata/document/misc/helix_cheat_sheet_english_rev_a.pdf
- author: Line 6
- accessed: 2026-11-05
- relevance: 8 setlists of 128 presets; footswitches FS1 and FS7 step banks, and a global setting makes them step single presets.

### [S1520] Fractal Softworks — Starsector dev blog: save/load UI, autosave
- type: article
- url: https://fractalsoftworks.com/2024/04/10/save-load-ui-autosave-intel-map-markers-and-more
- author: Fractal Softworks
- published: 2024-04-10
- accessed: 2026-11-05
- relevance: autosave rotates through three labelled slots and "will NEVER overwrite a manually-created save slot"; several quicksave slots were rejected as clutter. Read via a search excerpt only.

### [S1521] Apple Human Interface Guidelines — segmented controls, buttons, toggles
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/segmented-controls
- also: https://developer.apple.com/design/human-interface-guidelines/buttons, https://developer.apple.com/design/human-interface-guidelines/toggles
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: segmented controls: "Don't assign actions to segments in a control that otherwise represents selection state", about 5 segments at most on iPhone; buttons: roles normal, primary, cancel and destructive, "Keep the number of prominent buttons to one or two per view", "Use style — not size — to visually distinguish the preferred choice", never give a destructive action the primary role, an ellipsis means the button needs more input, 44×44 pt targets; toggles: "Outside of a list, use a button that behaves like a toggle".

### [S1522] Apple Human Interface Guidelines — collections, panels, sidebars, outline views
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/collections
- also: https://developer.apple.com/design/human-interface-guidelines/panels, https://developer.apple.com/design/human-interface-guidelines/sidebars, https://developer.apple.com/design/human-interface-guidelines/outline-views
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: collections suit images and text reads better in a list, tap selects and touch-and-hold edits; an inspector "displays the details of the currently selected item"; a sidebar shows at most two levels and deeper needs a split view; outline views keep people's expansion choices.

### [S1523] Material Design 3 — buttons, icon buttons, chips, split button, surface roles
- type: docs
- url: https://github.com/material-components/material-web/blob/main/docs/components/button.md
- also: https://github.com/material-components/material-web/blob/main/docs/components/icon-button.md, https://github.com/material-components/material-web/blob/main/docs/components/chip.md, https://material-web.dev/components/chip/, https://kotlinlang.org/api/compose-multiplatform/material3/androidx.compose.material3/-split-button-layout.html, https://m3.material.io/blog/tone-based-surface-color-m3 (search snippet only; m3.material.io pages did not render)
- author: Google (Material Design); JetBrains (Compose Multiplatform API docs)
- accessed: 2026-11-05
- relevance: buttons: filled has "the most visual impact after the FAB" and suits final actions such as save, tonal is the middle ground, outlined is "medium-emphasis", text buttons are for the "lowest priority actions"; toggle icon buttons cover on/off; chips are a set of items distinct from buttons, assist chips are actions that "appear dynamically and contextually", filter chips narrow content; a split button's leading part runs the main action and its trailing part opens related actions; surface container roles run from lowest to highest emphasis and are no longer tied to elevation.

### [S1524] Nielsen Norman Group — disclosure and help: progressive disclosure, tooltips, instructional overlays, empty states
- type: article
- url: https://www.nngroup.com/articles/progressive-disclosure/
- also: https://www.nngroup.com/articles/tooltip-guidelines/, https://www.nngroup.com/articles/mobile-instructional-overlay/, https://www.nngroup.com/articles/empty-state-interface-design/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: progressive disclosure: designs with more than two disclosure levels "typically have low usability", and past two "users often get lost"; tooltips: they do not work on touch, must never hold task-critical information, and help that adds nothing should be skipped, and `title` text never shows on phones; instructional overlays: users dismiss coach marks and forget them within about 20 s; empty states: show system status, give learning cues and offer "direct pathways" to the key task.

### [S1525] Nielsen Norman Group — visual structure: visual hierarchy, common region, mobile accordions, mobile carousels, flat-UI signifiers
- type: article
- url: https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
- also: https://www.nngroup.com/articles/common-region/, https://www.nngroup.com/articles/mobile-accordions/, https://www.nngroup.com/articles/mobile-carousels/, https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: use about three type sizes and at most three contrast variations; a boundary "can overpower" proximity and similarity, but too many borders clutter; long open accordion sections on a phone need a sticky header; carousel users should reach the last item in "3–4 steps", a long set needs a list view, and a partly visible next item is "a strong carousel cue"; with weak signifiers tasks took 22% longer and caused "click uncertainty".

### [S1526] Nielsen Norman Group — controls and language: toggle switches, confirmation dialogs, user control and freedom, match with the real world
- type: article
- url: https://www.nngroup.com/articles/toggle-switch-guidelines/
- also: https://www.nngroup.com/articles/confirmation-dialog/, https://www.nngroup.com/articles/user-control-and-freedom/, https://www.nngroup.com/articles/match-system-real-world/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: switches "should take immediate effect", and mixing immediate switches with settings that wait for a save "confuses users"; "If you warn people too much, they stop paying attention", so prefer undo and confirm only serious, irreversible actions; "speak the users' language" (the basis of RA-27's party test). An NN/g article on primary versus secondary buttons: not found.

### [S1527] Figma Help Center — right sidebar and layer properties
- type: docs
- url: https://help.figma.com/hc/en-us/articles/360039832014-Design-prototype-and-explore-layer-properties-in-the-right-sidebar
- also: https://help.figma.com/hc/en-us/articles/360040667874
- author: Figma
- accessed: 2026-11-05
- relevance: the right sidebar shows controls for the selected layer, and page and file options when nothing is selected; a layer's blend sits in the sidebar's Appearance section.

### [S1528] Blender manual — Modifiers: introduction
- type: docs
- url: https://docs.blender.org/manual/en/latest/modeling/modifiers/introduction.html
- author: Blender Foundation
- accessed: 2026-11-05
- relevance: one collapsible panel per modifier, evaluated top to bottom, with the active one outlined.

### [S1529] Derivative — TouchDesigner Parameter Dialog
- type: docs
- url: https://docs.derivative.ca/Parameter_Dialog
- author: Derivative
- accessed: 2026-11-05
- relevance: the parameter dialog's header names the operator, and its parameters are split into pages. S1354 and S1355 are sibling pages.

### [S1530] W3C WAI-ARIA Authoring Practices Guide — Disclosure, Accordion and Tooltip patterns
- type: spec
- url: https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
- also: https://www.w3.org/WAI/ARIA/apg/patterns/accordion/, https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- relevance: a disclosure is a button that shows and hides content, with `aria-expanded` and `aria-controls`; each accordion header button is wrapped in a heading with a fitting `aria-level`; the tooltip pattern is still "work in progress". S1377, S1393 and S1394 are sibling patterns.

### [S1531] W3C — Understanding WCAG 2.2: SC 1.3.1, 1.4.11, 1.4.13, 2.4.7, 3.2.4, 3.3.2, 4.1.2
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html
- also: https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html, https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html, https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html, https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html (not fetched), https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html, https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- relevance: 1.4.13: content shown on hover or focus must be dismissible, hoverable and persistent, and the `title` attribute is out of scope because the browser controls it; 1.3.1: visual relationships must be programmatic; 1.4.11: user-interface components and their states need 3:1 contrast; 2.4.7: focus is visible; 3.2.4: one function, one name, across pages; 3.3.2: controls have labels or instructions; 4.1.2: controls expose name, role and state. S1303, S1374, S1375, S1376, S1392 and S1464 are other SCs.

### [S1532] Heydon Pickering — Inclusive Components: Tooltips & Toggletips
- type: article
- url: https://inclusive-components.design/tooltips-toggletips/
- author: Heydon Pickering
- accessed: 2026-11-05
- relevance: a toggletip opens on click, so it behaves the same on touch and with a mouse.

### [S1533] MDN — Popover API
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/API/Popover_API
- author: MDN contributors
- accessed: 2026-11-05
- relevance: the page marks the Popover API "Baseline 2025" (seen in the page HTML, 2026-11-05).

### [S1534] GOV.UK Design System — Button
- type: docs
- url: https://design-system.service.gov.uk/components/button/
- author: Government Digital Service (UK)
- accessed: 2026-11-05
- relevance: disabled buttons "can confuse some users, so avoid them if possible"; "Avoid using multiple default buttons on a single page".

### [S1535] IBM Carbon Design System — Button usage
- type: docs
- url: https://carbondesignsystem.com/components/button/usage/
- author: IBM
- accessed: 2026-11-05
- relevance: "Each page should have only one primary button"; optional destructive actions use the tertiary or ghost danger style.

### [S1536] Ark UI — Toggle
- type: docs
- url: https://ark-ui.com/docs/components/toggle
- author: Chakra UI (Segun Adebayo et al.)
- license: MIT (package @ark-ui/react)
- accessed: 2026-11-05
- relevance: Ark's Toggle is "a two-state button" carrying `data-state` on or off; Ark has no Button primitive. S1363 covers the other Ark pages pewpew uses.

### [S1537] Park UI — Button
- type: docs
- url: https://park-ui.com/docs/components/button
- author: Park UI contributors
- accessed: 2026-11-05
- relevance: the styled layer over Ark has one Button with a variant prop (solid, surface, subtle, outline, plain), sizes and a `loading` state.

## Block S1550–S1599 — RA-27 Control-page UX (design-led)

### [S1550] Spotify Design — Better in Black: rethinking our most important buttons
- type: article
- url: https://spotify.design/article/better-in-black-rethinking-our-most-important-buttons
- archive: https://web.archive.org/web/2023/https://spotify.design/article/better-in-black-rethinking-our-most-important-buttons (2023 capture; the live page returns 404)
- author: Spotify Design
- accessed: 2026-11-05
- relevance: play is the button "you use every time you open Spotify"; Encore buttons moved to black text on Spotify green (10.9:1) and sentence case, which takes 20–30% less space and is "less shouty".

### [S1551] Figma blog — Creating coherence: how Spotify's design system goes beyond platforms
- type: article
- url: https://www.figma.com/blog/creating-coherence-how-spotifys-design-system-goes-beyond-platforms/
- author: Figma
- published: 2023-08-31
- accessed: 2026-11-05
- relevance: Encore has three button tiers (primary, secondary, tertiary) under one size framework and naming scheme that every platform reuses. No public Encore button spec with sizes or states was found.

### [S1552] Spotify Design — Designing a new foundation: Spotify for Desktop
- type: article
- url: https://spotify.design/article/designing-a-new-foundation-spotify-for-desktop
- archive: https://web.archive.org/web/2023/https://spotify.design/article/designing-a-new-foundation-spotify-for-desktop (2023 capture; the live page returns 404)
- author: Spotify Design
- accessed: 2026-11-05
- relevance: "Shortcuts on the top of Home give quick access to those favorite go-to's"; ? or ⌘/ opens a shortcuts dialog that works with screen readers, meets contrast requirements and runs from the keyboard alone; track rows use "shared components".

### [S1553] Spotify Design — Naming personalized playlists at Spotify
- type: article
- url: https://spotify.design/article/naming-personalized-playlists-at-spotify
- archive: https://web.archive.org/web/2023/https://spotify.design/article/naming-personalized-playlists-at-spotify (2023 capture; the live page returns 404)
- author: Spotify Design
- accessed: 2026-11-05
- relevance: a name describes what is inside and helps people decide; the process sets goals, runs a timed "Namestorm", writes each candidate into a real sentence and tests it in context with users; "Your" was dropped as overused.

### [S1554] Spotify newsroom — desktop redesign: Your Library and Now Playing view
- type: article
- url: https://newsroom.spotify.com/2023-06-20/spotify-desktop-experience-redesign-your-library-now-playing-views-customize/
- author: Spotify
- published: 2023-06-20
- accessed: 2026-11-05
- relevance: the desktop app keeps Your Library on the left, collapsible to icons, and the Now Playing view on the right, as separate regions.

### [S1555] Spotify newsroom — Smart Shuffle
- type: article
- url: https://newsroom.spotify.com/2023-03-08/smart-shuffle-new-life-spotify-playlists/
- author: Spotify
- published: 2023-03-08
- accessed: 2026-11-05
- relevance: Smart Shuffle marks its recommended tracks with a sparkle (✨) and does not add them to the playlist; you save the ones you like and tap minus to reject one.

### [S1556] Spotify Support — Shuffle play
- type: docs
- url: https://support.spotify.com/us/article/shuffle-play/
- author: Spotify
- accessed: 2026-11-05
- relevance: the shuffle icon cycles through off, Shuffle and Smart Shuffle; the recommendation mark is called an "Enhance badge". pewpew's "shuffle" word rests on this.

### [S1557] Spotify newsroom — AI Playlist in beta
- type: article
- url: https://newsroom.spotify.com/2024-04-07/spotify-premium-users-can-now-turn-any-idea-into-a-personalized-playlist-with-ai-playlist-in-beta/
- author: Spotify
- published: 2024-04-07
- accessed: 2026-11-05
- relevance: AI Playlist is reached from the "+" in Your Library; you preview, refine with follow-up prompts and delete tracks, and nothing is saved until "Create".

### [S1558] Spotify newsroom — more controls and discovery tools
- type: article
- url: https://newsroom.spotify.com/2025-05-07/experience-a-new-dimension-of-music-discovery-with-more-controls-and-enhanced-tools/
- author: Spotify
- published: 2025-05-07
- accessed: 2026-11-05
- relevance: one "+" Create button opens new playlist, Blend, Jam and AI Playlist, so the generators sit behind a button, not among the items; the queue holds Shuffle, Smart Shuffle, Repeat and Sleep timer.

### [S1559] 9to5Mac — Spotify's heart button turns into a Plus button
- type: article
- url: https://9to5mac.com/2023/02/27/spotify-heart-button-turns-to-plus-button/
- author: 9to5Mac, quoting Spotify
- published: 2023-02-27
- accessed: 2026-11-05
- relevance: one Plus button replaced the heart and "Add to playlist", to "save and choose the destination": one tap saves, and a second tap picks where; Spotify said testing showed it saved people time (paraphrased).

### [S1560] Mezha — Spotify lets users pin up to 20 items in Your Library
- type: article
- url: https://mezha.ua/en/news/spotify-lets-users-pin-up-to-20-items-in-your-library-313103/
- author: Mezha, citing @Spotify on X
- accessed: 2026-11-05
- relevance: pinned items sit at the top of Your Library, and the pin limit rose from 4 to 20 in July 2026. A news report, not Spotify's own docs.

### [S1561] Linear Now — Behind the latest design refresh
- type: article
- url: https://linear.app/now/behind-the-latest-design-refresh
- author: Linear
- accessed: 2026-11-05
- relevance: the 2026 refresh rests on "Don't compete for attention you haven't earned" and "Structure should be felt not seen": the sidebar is "a few notches dimmer", separators were softened or removed, icons shrank, and coloured icon backgrounds went.

### [S1562] Linear changelog — UI refresh (2026-03-12)
- type: article
- url: https://linear.app/changelog/2026-03-12-ui-refresh
- author: Linear
- published: 2026-03-12
- accessed: 2026-11-05
- relevance: header actions had "no longer appeared in predictable places", so headers and view controls became "consistent across projects, issues, reviews, and documents".

### [S1563] Linear Now — How we redesigned the Linear UI
- type: article
- url: https://linear.app/now/how-we-redesigned-the-linear-ui
- author: Linear
- accessed: 2026-11-05
- relevance: the 2024 redesign centres on the "inverted L" chrome (sidebar plus header) "that controls the content in the main view", with side panels for meta properties; buttons were harmonised, and themes come from base, accent and contrast variables in LCH.

### [S1564] The Linear Method — Introduction
- type: docs
- url: https://linear.app/method/introduction
- author: Linear
- accessed: 2026-11-05
- relevance: "Projects should be called projects" and "Simple first, then powerful": plain words, one per concept.

### [S1565] Linear enablement — Navigating Linear
- type: docs
- url: https://linear.app/enablement/guide/navigating-linear
- author: Linear
- accessed: 2026-11-05
- relevance: Cmd+K opens the command menu, where you type "the page or action you need"; `/` searches everything.

### [S1566] Linear changelog — Better menus and view options (2020-08-26)
- type: article
- url: https://linear.app/changelog/2020-08-26-better-menus-and-view-options
- author: Linear
- published: 2020-08-26
- accessed: 2026-11-05
- relevance: right-click menus show each action's shortcut, "a nice way to learn the most important keyboard shortcuts".

### [S1567] Linear changelog — Keyboard shortcuts help (2021-03-25)
- type: article
- url: https://linear.app/changelog/2021-03-25-keyboard-shortcuts-help
- author: Linear
- published: 2021-03-25
- accessed: 2026-11-05
- relevance: `?` opens a searchable shortcut help screen.

### [S1568] Linear docs — Favorites
- type: docs
- url: https://linear.app/docs/favorites
- author: Linear
- accessed: 2026-11-05
- relevance: almost any object can be starred, from its row, its header, Alt+F or the command menu, and favourites can be grouped into folders; a starred thing stays an object you open, while actions live in menus.

### [S1569] Linear changelog — Personalized sidebar (2024-12-18)
- type: article
- url: https://linear.app/changelog/2024-12-18-personalized-sidebar
- author: Linear
- published: 2024-12-18
- accessed: 2026-11-05
- relevance: the sidebar can be reordered by drag, and rarely used items hidden "behind a More menu".

### [S1570] Linear docs — Parent and sub-issues
- type: docs
- url: https://linear.app/docs/parent-and-sub-issues
- author: Linear
- accessed: 2026-11-05
- relevance: a parent issue lists its sub-issues inside it, and you choose "the properties that display" on those rows.

### [S1571] Linear changelog — collapsible sidebar; Edit leaves the issue view
- type: article
- url: https://linear.app/changelog/unpublished-collapsible-sidebar
- author: Linear
- accessed: 2026-11-05
- relevance: the separate Edit button left the issue view, and Edit moved to the ••• menu and the E key, so you edit in place. URL as read; its slug says "unpublished".

### [S1572] Figma blog — Behind our redesign: UI3
- type: article
- url: https://www.figma.com/blog/behind-our-redesign-ui3/
- author: Figma
- accessed: 2026-11-05
- relevance: UI that showed only on hover was tried and rejected ("work environment too unstable"); UI3 began by "stripping away features until they were missed"; swapping size and position "disrupted muscle memory too much"; component controls got "top billing"; property labels became optional; inputs got backgrounds and dropdowns got borders.

### [S1573] Figma blog — Our approach to designing UI3
- type: article
- url: https://www.figma.com/blog/our-approach-to-designing-ui3/
- author: Figma
- accessed: 2026-11-05
- relevance: beta floating panels were reverted because "they slowed people down" ("Speed is a feature"); a label-free design was dropped for accessibility ("This was a deal breaker"), and visible labels match screen-reader labels; blend mode behind an icon became an inline dropdown.

### [S1574] Figma Help Center — component properties
- type: docs
- url: https://help.figma.com/hc/en-us/articles/5579474826519
- author: Figma
- accessed: 2026-11-05
- relevance: an instance shows "a single set of consolidated controls in the right panel", and nested instances' properties can be exposed at the top level; "simplified instances", which hid inner layers, are deprecated from 23 March 2026, so all properties and layers show by default.

### [S1575] Figma Help Center — instance overrides
- type: docs
- url: https://help.figma.com/hc/en-us/articles/360039150733
- author: Figma
- accessed: 2026-11-05
- relevance: an override changes an instance without changing its main component; Reset offers one property or "Reset all changes"; "Push changes to main component" sits in More actions beside the component name.

### [S1576] Figma Help Center — Minimize UI
- type: docs
- url: https://help.figma.com/hc/en-us/articles/41414918021271
- author: Figma
- accessed: 2026-11-05
- relevance: in Minimize UI the right sidebar expands on selection and minimizes on deselect.

### [S1577] Figma Simple Design System (SDS) — Button primitive
- type: code
- url: https://github.com/figma/sds
- pinned: figma/sds@05525f75192a3aa5d5690c5e41277ebd19d2efe1
- author: Figma
- license: MIT (GitHub API, 2026-11-05)
- published: commit 2026-10-02
- accessed: 2026-11-05
- relevance: `src/ui/primitives/Button/Button.tsx`: one Button with `variant: primary | neutral | subtle` and `size: small | medium`; a separate `ButtonDanger` is "Only used for destructive actions"; `ButtonGroup` sets alignment.

### [S1578] Figma Help Center — toolbar
- type: docs
- url: https://help.figma.com/hc/en-us/articles/360041064174
- author: Figma
- accessed: 2026-11-05
- relevance: the bottom toolbar holds the tools, the Actions menu and a mode switch: verbs live in the toolbar, and the things you make live on the canvas.

### [S1579] Vercel Geist — Button
- type: docs
- url: https://vercel.com/geist/button
- author: Vercel
- accessed: 2026-11-05
- relevance: one Button with variants default (primary), secondary, tertiary, error and warning, sizes tiny to large, square or circle icon-only buttons with an `aria-label`, and `loading` that keeps the label; "Disable a button only when the action is impossible right now", with a tooltip saying why.

### [S1580] Vercel Geist — Split Button
- type: docs
- url: https://vercel.com/geist/split-button
- author: Vercel
- accessed: 2026-11-05
- relevance: "Use a Split Button when one action is the clear default and 1–4 close variants belong next to it"; the menu's first item repeats the button label, and destructive items are blocked.

### [S1581] Vercel Geist — Menu
- type: docs
- url: https://vercel.com/geist/menu
- author: Vercel
- accessed: 2026-11-05
- relevance: a menu holds "actions on a single resource (a dots menu on a row…)", about 10 items at most, opens on click, labels are Verb + Noun with "…" only when a dialog follows, and destructive items go last after a divider.

### [S1582] Vercel Geist — Context Menu
- type: docs
- url: https://vercel.com/geist/context-menu
- author: Vercel
- accessed: 2026-11-05
- relevance: a context menu "must never be the only entry point".

### [S1583] Vercel Geist — Command Menu
- type: docs
- url: https://vercel.com/geist/command-menu
- author: Vercel
- accessed: 2026-11-05
- relevance: a global keyboard palette that splits into pages past about 30 items; an empty input shows recent items; the placeholder names its scope ("Bare `Search…` is wrong"); shortcuts show as `Kbd`.

### [S1584] Vercel Geist — Breadcrumbs
- type: docs
- url: https://vercel.com/geist/breadcrumbs
- author: Vercel
- accessed: 2026-11-05
- relevance: the Breadcrumb component has a `menu` type; how that menu behaves was not found on the page.

### [S1585] Vercel Geist — Toast
- type: docs
- url: https://vercel.com/geist/toast
- author: Vercel
- accessed: 2026-11-05
- relevance: a non-blocking confirmation reads "{Noun} {past-participle}", never "successfully", and matches the button verb; an undo toast stays 5–10 s with a literal `Undo`; it is announced with polite `aria-live`.

### [S1586] Vercel Geist — Badge
- type: docs
- url: https://vercel.com/geist/badge
- author: Vercel
- accessed: 2026-11-05
- relevance: badges are static labels of one or two words.

### [S1587] Vercel Geist — Entity
- type: docs
- url: https://vercel.com/geist/entity
- author: Vercel
- accessed: 2026-11-05
- relevance: an entity row (a thing, not an action) allows at most two controls, and the rest go in a dots menu; a loading row shows a skeleton.

### [S1588] Vercel Geist — Tooltip
- type: docs
- url: https://vercel.com/geist/tooltip
- author: Vercel
- accessed: 2026-11-05
- relevance: a tooltip says why (a limit), never what, in one sentence, after about 150 ms; "Touch users can't reach a hover-revealed control", so help goes on a sibling icon.

### [S1589] Vercel Geist — Empty State
- type: docs
- url: https://vercel.com/geist/empty-state
- author: Vercel
- accessed: 2026-11-05
- relevance: "Three CTAs is a smell": an empty state gets one primary, plus a secondary only for two real paths; its kinds are Blank Slate, Informational, Educational and Guide; it shows rather than tells and never auto-starts a tour.

### [S1590] Vercel — Web Interface Guidelines
- type: docs
- url: https://vercel.com/design/guidelines
- author: Vercel
- accessed: 2026-11-05
- relevance: "Inline help first… tooltips as a last resort"; "Keep nouns consistent. Introduce as few unique terms as possible."; "Instead of 'Continue' say 'Save API Key'"; destructive actions need a confirmation or an "Undo with a safe window"; targets of at least 24 px, or 44 px on mobile.

### [S1591] Superhuman blog — How to build a remarkable command palette
- type: article
- url: https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/
- author: Superhuman
- accessed: 2026-11-05
- relevance: Cmd+K runs any action "and also learn the shortcut for next time"; it is "the one place where users can find every command"; matching is fuzzy and includes synonyms; context changes ranking, not availability; buttons "should continue to exist".

### [S1592] Superhuman blog — Superhuman is built for speed
- type: article
- url: https://blog.superhuman.com/superhuman-is-built-for-speed/
- author: Superhuman
- accessed: 2026-11-05
- relevance: the ceiling is 100 ms per interaction, and Superhuman "aims for latency less than 50ms"; it prerenders likely next views and uses minimal animation.

### [S1593] Superhuman blog — Superhuman AI Instant Reply
- type: article
- url: https://blog.superhuman.com/superhuman-ai-instant-reply/
- author: Superhuman
- published: 2024-02
- accessed: 2026-11-05
- relevance: "three draft replies under each conversation", "precomputed, so you never have to wait": generated drafts get their own slot, and you pick one, edit, then send.

### [S1594] Business of Software — Rahul Vohra, the email game (talk transcript)
- type: video
- url: https://businessofsoftware.org/talks/email-game/
- author: Rahul Vohra (Superhuman)
- published: 2019
- accessed: 2026-11-05
- relevance: reading an email hides the inbox, one thing at a time; on every screen ask "What can I remove"; the command palette exists because "people would forget the shortcuts".

### [S1595] First Round Review — the Superhuman onboarding playbook
- type: article
- url: https://review.firstround.com/superhuman-onboarding-playbook.md
- author: Gaurav Vohra (built Superhuman's onboarding)
- published: 2025-04
- accessed: 2026-11-05
- relevance: "Checklists, tooltips, and timed nudges… yielded zero impact"; teaching works best "the split second after" the action; the teaching order is "do > show > tell"; onboarding assumes "the user is drunk" and protects people from losing work.

### [S1596] Superhuman Help Center — Undo
- type: docs
- url: https://help.superhuman.com/hc/en-us/articles/47278253460499-Undo
- author: Superhuman
- accessed: 2026-11-05
- relevance: Z undoes the last action, a send included, within 10 s. The page returned 403; this was read from search-result text only, so cites carry [NEEDS-VERIFICATION].

## Block S1600–S1649 — RA-27 Control-page UX (visual foundations)

### [S1600] Nielsen Norman Group — 5 principles of visual design in UX
- type: article
- url: https://www.nngroup.com/articles/principles-visual-design/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: use 2–3 type sizes per view; balance spreads visual signal evenly, and area counts as well as the number of elements.

### [S1601] Nielsen Norman Group — Proximity principle in visual design
- type: article
- url: https://www.nngroup.com/articles/gestalt-proximity/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: varying whitespace "to either unite or separate elements is key"; a label sits close to its field; proximity works on relative distance and can overpower similarity of colour or shape.

### [S1602] Nielsen Norman Group — Similarity principle in visual design
- type: article
- url: https://www.nngroup.com/articles/gestalt-similarity/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: elements that look alike are perceived as one group; "Same-color buttons will be perceived as sharing the same level of importance".

### [S1603] Nielsen Norman Group — F-shaped pattern of reading on the web
- type: article
- url: https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: readers fall into the F-pattern "when there are no strong cues"; put the information-carrying words first.

### [S1604] Nielsen Norman Group — The layer-cake pattern of scanning content
- type: article
- url: https://www.nngroup.com/articles/layer-cake-pattern-scanning/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: eyes land on the headings, so headings must visually stand out, be styled "in a consistent, predictable manner" and make clear which content each one owns.

### [S1605] Nielsen Norman Group — Beyond blue links: making clickable elements recognizable
- type: article
- url: https://www.nngroup.com/articles/clickable-elements/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: flat controls "should look clickable even without heavier effects"; "Don't make nonclickable items look like buttons".

### [S1606] Nielsen Norman Group — Button states: communicate interaction
- type: article
- url: https://www.nngroup.com/articles/button-states-communicate-interaction/
- author: Nielsen Norman Group
- accessed: 2026-11-05
- relevance: the states are enabled, disabled, hover, focus, pressed, selected and loading; focus shows as an outline, not colour alone; selected "is not a button state"; a disabled control stays readable at lower contrast.

### [S1607] Adam Wathan and Steve Schoger — Refactoring UI (book site and table of contents)
- type: product
- url: https://www.refactoringui.com/
- author: Adam Wathan, Steve Schoger
- accessed: 2026-11-05
- relevance: chapter titles only, from the public table of contents (the chapter text was not read): "De-emphasize to emphasize", "Size isn't everything", "Line-height is proportional", "Separate visual hierarchy from document hierarchy", "Establish a spacing and sizing system", "Avoid ambiguous spacing", "Start with too much white space", "Greys don't have to be grey", "Don't use grey text on colored backgrounds"; the home page says too many borders feel "busy and cluttered".

### [S1608] Refactoring UI — Building your color palette (preview chapter)
- type: article
- url: https://www.refactoringui.com/previews/building-your-color-palette
- author: Adam Wathan, Steve Schoger
- accessed: 2026-11-05
- relevance: build 8–10 greys and 5–10 shades of the primary colour, and use accent colours "pretty sparingly".

### [S1609] Adam Wathan and Steve Schoger — 7 practical tips for cheating at design (Medium)
- type: article
- url: https://medium.com/refactoring-ui/7-practical-tips-for-cheating-at-design-40c736799886
- author: Adam Wathan, Steve Schoger
- accessed: 2026-11-05
- relevance: rendered with Playwright. Primary actions "should be obvious… solid, high contrast background colors"; rank with weight and colour, not only size; "use fewer borders" and "resist immediately reaching for a border", separating with background or space instead.

### [S1610] Android Developers — Material Design 3 in Compose
- type: docs
- url: https://developer.android.com/develop/ui/compose/designsystems/material3
- author: Google
- accessed: 2026-11-05
- relevance: the M3 type table (15 styles; "your product will likely not need all 15"): label 12/16 Medium, body 14/20, title 16/24 Medium, large title 22/28, bodyLarge 16/24, titleMedium 16/24, titleSmall 14/20, headlineSmall 24/32; line height 1.43 at 14 px and 1.27 at 22 px; elevation is "mainly … tonal color overlays"; text roles on-surface and on-surface-variant. Read in place of m3.material.io, which renders only with JavaScript.

### [S1611] material-web — Color theming docs
- type: docs
- url: https://github.com/material-components/material-web/blob/main/docs/theming/color.md
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: M3 has one surface plus five surface containers, lowest to highest.

### [S1612] Android Developers — Buttons in Compose
- type: docs
- url: https://developer.android.com/develop/ui/compose/components/button
- author: Google
- accessed: 2026-11-05
- relevance: filled buttons are high emphasis, for primary actions such as "save"; outlined are medium emphasis, for alternatives; text buttons are low emphasis.

### [S1613] Material Components for Android — Dark theme docs
- type: docs
- url: https://github.com/material-components/material-components-android/blob/master/docs/theming/Dark.md
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: in a dark theme, surfaces "become lighter … at higher elevations", on dark grey, not black.

### [S1614] Material Design 3 — All buttons
- type: docs
- url: https://m3.material.io/components/all-buttons
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: rendered with Playwright. A button's appearance matches its emphasis, and text buttons are for "actions not essential to the user journey".

### [S1615] Material Design 3 — Type scale tokens
- type: docs
- url: https://m3.material.io/styles/typography/type-scale-tokens
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: rendered with Playwright. 15 baseline styles, from Display to Label; the exact sizes were not in the rendered text.

### [S1616] Material Design 3 — Elevation overview
- type: docs
- url: https://m3.material.io/styles/elevation/overview
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: rendered with Playwright. Elevation shows as tonal surfaces.

### [S1617] Material Design 3 — Color roles
- type: docs
- url: https://m3.material.io/styles/color/roles
- author: Google (Material Design)
- accessed: 2026-11-05
- relevance: rendered with Playwright. Each colour has one role.

### [S1618] Apple Human Interface Guidelines — Typography
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/typography
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: text defaults to 17 pt on iOS (11 pt minimum) and 13 pt on macOS (10 pt minimum); use Regular to Bold and avoid Light and Thin; mixing many typefaces "can obscure your information hierarchy".

### [S1619] Apple Human Interface Guidelines — Layout
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/layout
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: place the most important items "near the top and leading side"; "People assume that aligned items are related"; use indentation to convey hierarchy.

### [S1620] Apple Human Interface Guidelines — Color
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/color
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: reserve colour for "status indicators or primary actions"; "Avoid using the same color to mean different things"; text tiers label, secondary, tertiary and quaternary.

### [S1621] Apple Human Interface Guidelines — Dark Mode
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/dark-mode
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: dimmer base colours recede and brighter elevated ones advance; for small text, "strive for … 7:1".

### [S1622] Apple Human Interface Guidelines — Accessibility
- type: docs
- url: https://developer.apple.com/design/human-interface-guidelines/accessibility
- author: Apple
- published: n/a (living docs)
- accessed: 2026-11-05
- relevance: default control size is 44×44 pt on iOS and 28×28 pt on macOS (read from Apple's JSON for the page).

### [S1623] Matthew Butterick — Practical Typography: Line spacing
- type: article
- url: https://practicaltypography.com/line-spacing.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: body text takes line spacing of 120–145% of its point size.

### [S1624] Matthew Butterick — Practical Typography: Letterspacing
- type: article
- url: https://practicaltypography.com/letterspacing.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: add 5–12% letterspacing to caps, and do not letterspace lowercase.

### [S1625] Matthew Butterick — Practical Typography: All caps
- type: article
- url: https://practicaltypography.com/all-caps.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: use all caps only for text shorter than one line.

### [S1626] Matthew Butterick — Practical Typography: Headings
- type: article
- url: https://practicaltypography.com/headings.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: mark a heading with space above and below and bold, at "the smallest increment necessary" in size; at most three heading levels, and "Two is better".

### [S1627] Matthew Butterick — Practical Typography: Alternate figures
- type: article
- url: https://practicaltypography.com/alternate-figures.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: tabular figures for numbers that change or align in columns.

### [S1628] Matthew Butterick — Practical Typography: Bold or italic
- type: article
- url: https://practicaltypography.com/bold-or-italic.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: in sans text, emphasize with bold, not italic; "If everything is emphasized, then nothing is emphasized".

### [S1629] Matthew Butterick — Practical Typography: Monospaced fonts
- type: article
- url: https://practicaltypography.com/monospaced-fonts.html
- author: Matthew Butterick
- accessed: 2026-11-05
- relevance: monospaced text is "harder to read" than proportional text.

### [S1630] Laws of UX — Law of Common Region
- type: article
- url: https://lawsofux.com/law-of-common-region/
- author: Jon Yablonski
- accessed: 2026-11-05
- relevance: a background tint makes a common region without a border.

### [S1631] Laws of UX — Von Restorff effect
- type: article
- url: https://lawsofux.com/von-restorff-effect/
- author: Jon Yablonski
- accessed: 2026-11-05
- relevance: the item that differs is the one remembered, so isolation works only when one item differs; use "restraint".

### [S1632] W3C — Understanding WCAG 2.2 SC 1.4.3 Contrast (Minimum)
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- relevance: text needs 4.5:1 and large text (about 24 px, or 18.66 px bold) 3:1; an "inactive user interface component" is exempt.

### [S1633] W3C — Understanding WCAG 2.2 SC 1.4.1 Use of Color
- type: spec
- url: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- author: W3C WAI
- license: W3C document license
- accessed: 2026-11-05
- relevance: colour is never the only visual means of conveying information or a state.

### [S1634] Vercel Geist — Colors
- type: docs
- url: https://vercel.com/geist/colors
- author: Vercel
- accessed: 2026-11-05
- relevance: 2 backgrounds, the second used "sparingly"; separate component-background steps for default, hover and active, and separate border steps; step 1000 for primary text and 900 for secondary.

### [S1635] Vercel Geist — Typography
- type: docs
- url: https://vercel.com/geist/typography
- author: Vercel
- accessed: 2026-11-05
- relevance: separate Heading (14–72), Label, Copy and Button styles; single-line labels get less line height than multi-line copy; tabular figures for numbers.

### [S1636] Vercel Geist — Materials
- type: docs
- url: https://vercel.com/geist/materials
- author: Vercel
- accessed: 2026-11-05
- relevance: four on-page materials and four floating ones.

### [S1637] Every Layout — Modular scale
- type: article
- url: https://every-layout.dev/rudiments/modular-scale/
- author: Heydon Pickering, Andy Bell
- accessed: 2026-11-05
- relevance: a modular scale multiplies a base by one ratio; its example uses 1.5.

### [S1638] Every Layout — The Stack
- type: article
- url: https://every-layout.dev/layouts/stack/
- author: Heydon Pickering, Andy Bell
- accessed: 2026-11-05
- relevance: the parent sets the gap between its children (the owl selector), not each child's own margin, and a small stack nests inside a larger one.

### [S1639] IBM Carbon Design System — Spacing overview
- type: docs
- url: https://carbondesignsystem.com/elements/spacing/overview/
- author: IBM
- accessed: 2026-11-05
- relevance: a spacing scale of 2, 4, 8, 12, 16, 24, 32, 40, 48 and 64 px; extra space around an element makes it seem more important, and as space grows the perceived relation weakens.

## Block S1650–S1699 — RA-27 Control-page UX (modulator terms)

### [S1650] Bitwig Studio user guide — Modulators
- type: docs
- url: https://bitwig.com/userguide/latest/modulator
- author: Bitwig
- accessed: 2026-11-06
- relevance: files every source under "Modulators"; "Random" is "a tempo-synced random low-frequency oscillator"; "Beat LFO" is tempo-synced; ADSR and AHDSR envelopes, Envelope Follower, Audio Sidechain, Sample and Hold and macros are separate modulators.

### [S1651] Bitwig Studio user guide — The unified modulation system
- type: docs
- url: https://www.bitwig.com/userguide/latest/the_unified_modulation_system/
- author: Bitwig
- accessed: 2026-11-06
- relevance: "modulation is the idea that one component can influence another in a controlled way"; each destination has "its own modulation amount" (amount five times, depth twice); "modulation routing"; the amount shows in orange on the knob.

### [S1652] Ableton Live manual — Max for Live devices
- type: docs
- url: https://www.ableton.com/en/manual/max-for-live-devices/
- author: Ableton
- accessed: 2026-11-06
- relevance: LFO, Envelope Follower and Shaper are each "a modulator device", mapped to a target with a Map button; the LFO's control is "Depth", and Envelope MIDI has "Modulation Amount" and "Amount"; an ADSR envelope.

### [S1653] Ableton Live manual — Clip envelopes
- type: docs
- url: https://www.ableton.com/en/manual/clip-envelopes/
- author: Ableton
- accessed: 2026-11-06
- relevance: automation envelopes "define the absolute value of a control", while modulation envelopes "can only influence this defined value": modulation is relative to the knob's setting.

### [S1654] Vital — product page
- type: product
- url: https://vital.audio/
- author: Matt Tytel (Vital Audio)
- accessed: 2026-11-06
- relevance: says "modulation" and "modulation source", speaks of connecting a source to a target, and offers noise as a source.

### [S1655] Dakota State University DAD-222 — Vital, part 3 (course lecture)
- type: article
- url: https://dsu-digital-sound-design.github.io/f-22-DAD-222-Audio-Production-I/lectures/week-11/vital-pt-3
- author: Dakota State University, Digital Sound Design course
- accessed: 2026-11-06
- relevance: a secondary account of Vital's LFOs, envelopes, random, macros, modulation amount and modulation matrix, used where Vital's own docs were not read.

### [S1656] Xfer Records — What's New in Serum 2 (PDF)
- type: docs
- url: https://static.xferrecords.com/Serum%202%20What's%20New.pdf
- author: Xfer Records
- accessed: 2026-11-06
- relevance: LFOs, envelopes and eight macros as modulation sources; LFO chaos modes; envelopes gain a BPM option; a mod matrix. The matrix's "amount" wording was not verified here.

### [S1657] Apple — Alchemy modulation overview in Logic Pro for Mac
- type: docs
- url: https://support.apple.com/guide/logicpro/alchemy-modulation-overview-lgsidbc6a2da/mac
- author: Apple
- accessed: 2026-11-06
- relevance: a knob "can be modulated by as many as ten modulators"; "Rotate the Depth knob" and "depth (amount it affects the target)"; an orange arc "shows the modulation range"; LFOs, envelopes and envelope followers as modulators.

### [S1658] Apple — Sample Alchemy Mod Matrix in Logic Pro for iPad
- type: docs
- url: https://support.apple.com/guide/logicpro-ipad/mod-matrix-lpipcd5da5ba/ipados
- author: Apple
- accessed: 2026-11-06
- relevance: "up to four independent routings of modulation sources and targets in the Mod Matrix pane"; a "Depth field" sets "the maximum value or intensity of modulation".

### [S1659] Apple — Modulator MIDI plug-in LFO in Logic Pro for iPad
- type: docs
- url: https://support.apple.com/guide/logicpro-ipad/lpipdbb777b1/ipados
- author: Apple
- accessed: 2026-11-06
- relevance: the LFO's rate is set in hertz "or in beat values when the Sync button is on"; random is one of its shapes.

### [S1660] Native Instruments — Massive X manual: Modulators
- type: docs
- url: https://docs.native-instruments.com/online-guides/massive-x-manual/en/modulators
- author: Native Instruments
- accessed: 2026-11-06
- relevance: a "Modulators" page with envelopes, a "Switcher LFO" and a "Random LFO"; a modulator is assigned to a target.

### [S1661] Arturia — Pigments overview
- type: product
- url: https://www.arturia.com/products/software-instruments/pigments/overview
- author: Arturia
- accessed: 2026-11-06
- relevance: "Modulate practically any parameter with anything you choose"; LFOs, envelopes, random generators and macros as modulation sources; "modulation routing" to a destination; sidechain input.

### [S1662] Kilohearts — Modulation (docs)
- type: docs
- url: https://kilohearts.com/docs/modulation
- author: Kilohearts
- accessed: 2026-11-06
- relevance: "modulator module" and "modulation source"; LFO, envelope, random, Audio Follower and macros; "The output depth of all modulators can be scaled", and each connection shows "the modulation amount".

### [S1663] Teenage Engineering — OP-1 guide: LFO
- type: docs
- url: https://teenage.engineering/guides/op-1/original/lfo
- author: Teenage Engineering
- accessed: 2026-11-06
- relevance: calls every modulation source an "LFO", MIDI and "crank" included, with a random one; each sends to a destination with an amount.

### [S1664] TouchDesigner docs — LFO, Lag and Beat CHOPs
- type: docs
- url: https://docs.derivative.ca/LFO_CHOP
- also: https://docs.derivative.ca/Lag_CHOP, https://docs.derivative.ca/Beat_CHOP
- author: Derivative
- accessed: 2026-11-06
- relevance: each source is a CHOP with no umbrella word for them; an LFO CHOP, a Lag CHOP, and a Beat CHOP that gives ramps and pulses in time with the beat. S1294 holds the Trigger CHOP (envelopes).

### [S1665] Resolume 6 manual — Parameter animation
- type: docs
- url: https://resolume.com/support/en/6/parameter-animation
- author: Resolume
- accessed: 2026-11-06
- relevance: calls modulation "parameter animation", with "BPM Sync" and audio analysis (FFT, with Gain and Fall). No LFO by that name was found.

### [S1666] Chromatik Guide — Modulation and Modulators
- type: docs
- url: https://chromatik.co/guide/modulators/
- also: https://chromatik.co/guide/modulation/
- author: Heron Arts / Mark Slee
- accessed: 2026-11-06
- relevance: "Nearly every parameter in the application can have its value automatically modified by algorithmic or interactive inputs"; modulators include an LFO, Randomizer, Noise ("pseudorandom movement using a noise algorithm"), Smoother ("Smoothes input with exponential decay"), Band Filter, Beat Detect, envelopes (ADSR) and Knobs ("Generic mappable macro knobs"); a Parameter Mapping has a Range. S1265 cites the modulation page for other facts.

### [S1667] Minimal Audio manual — Envelope follower
- type: docs
- url: https://manual.minimal.audio/current-manual/modulation/envelope-follower
- author: Minimal Audio
- accessed: 2026-11-06
- relevance: "envelope follower" names the modulator that follows an audio signal's loudness.

### [S1668] Learning Modular — Glossary: slew limiter
- type: article
- url: https://learningmodular.com/glossary/slew-limiter/
- author: Learning Modular
- accessed: 2026-11-06
- relevance: names the slew limiter, also called a lag generator: the smoothing modulator's modular-synth names.

### [S1669] Wikipedia — Low-frequency oscillation
- type: article
- url: https://en.wikipedia.org/wiki/Low-frequency_oscillation
- author: Wikipedia contributors
- accessed: 2026-11-06
- relevance: an LFO runs usually below 20 Hz and makes "a rhythmic pulse or sweep" used to modulate other parameters.

### [S1670] Modcan — B-series Lag module
- type: product
- url: https://www.modcan.com/bmodules/lag.html
- author: Modcan
- accessed: 2026-11-06
- relevance: "Lag is also known as glide, slew or portomento" (sic): one function, four names.

## Block S1700–S1749 — RA-27 Control-page UX (type)

### [S1700] Martian Grotesk (repository)
- type: code
- url: https://github.com/evilmartians/grotesk
- pinned: evilmartians/grotesk@0b66b31f4ffaac140587b6b6ea5e2194c6a7444f
- author: Evil Martians
- license: OFL-1.1
- accessed: 2026-11-06
- relevance: `fonts/variable/MartianGrotesk[wdth,wght].ttf`, sha256 f81807163c34ff754e6d915b0b59f76cca88332b67c45cfc7453ace5751ae912, v1.100; `OFL.txt` (blob 68afb7372a040929f4e219e7f9c04432291444bf) declares no Reserved Font Name; README: "styles from regular to bold are finely tuned for use in body text", vertical metrics "vertically centered".

### [S1701] Martian Mono v1.1.0 (release)
- type: code
- url: https://github.com/evilmartians/mono/releases/tag/v1.1.0
- pinned: evilmartians/mono@8ffa86c2998677256252336f3662d60997e74b05
- author: Evil Martians
- license: OFL-1.1
- accessed: 2026-11-06
- relevance: release asset `martian-mono-1.1.0-variable.zip` → `MartianMonoVF.ttf`, sha256 60e0eee102be3f96b3c2c6431e6bb7101ff20735baee480e091af1765d7d49c7, 821 glyphs (adds ✓ ✗ and box drawing over v1.000); `OFL.txt` (blob 3d86611f3660e09781ef246830e82374cbd7dfab) declares no Reserved Font Name; README: "a reasonable choice for any user interface design", an editor example at `'wdth' 87.5`.

### [S1702] Martian Grotesk v1.0.0 (release)
- type: code
- url: https://github.com/evilmartians/grotesk/releases/tag/v1.0.0
- pinned: evilmartians/grotesk@8263a7abe781b3649f2515df2661d37fcb909c21
- author: Evil Martians
- accessed: 2026-11-06
- relevance: the release binaries carry no licence string, and name ID 14 points to a commercial EULA: do not use them.

### [S1703] Martian Grotesk EULA (gist)
- type: docs
- url: https://gist.github.com/romashamin/1eb129751d10e22a69a4c9679c0cbba6
- author: Roman Shamin
- accessed: 2026-11-06
- archive: pending
- relevance: the EULA that v1.0.0's name ID 14 points to forbids distribution.

### [S1704] Google Fonts — Martian Mono METADATA.pb
- type: code
- url: https://github.com/google/fonts/blob/main/ofl/martianmono/METADATA.pb
- author: Google Fonts
- license: OFL-1.1 (the font)
- accessed: 2026-11-06
- relevance: Google Fonts ships Martian Mono v1.000 (567 glyphs), older than the v1.1.0 release.

### [S1705] Evil Martians — Martian Grotesk product page
- type: docs
- url: https://evilmartians.com/products/martian-grotesk
- author: Evil Martians
- accessed: 2026-11-06
- archive: pending
- relevance: "available under OFL license"; heights fit the pixel grid at "10, 15, and 20 pixels".

### [S1706] Evil Martians — Martian summer: open source (blog)
- type: article
- url: https://evilmartians.com/chronicles/martian-summer-blogs-talks-open-source-ready-for-sfruby-nov
- author: Evil Martians
- accessed: 2026-11-06
- archive: pending
- relevance: Martian Grotesk is "now fully open source" (2025-10-07).

### [S1707] Evil Martians — Variable fonts in real life
- type: article
- url: https://evilmartians.com/chronicles/variable-fonts-in-real-life-how-to-use-and-love-them
- author: Evil Martians
- accessed: 2026-11-06
- archive: pending
- relevance: light text on dark "will visually expand and appear bolder", so "make the white text slightly lighter" (2022-03-24).

### [S1708] google/fonts issue 10568 — add Martian Grotesk
- type: docs
- url: https://github.com/google/fonts/issues/10568
- author: Google Fonts
- accessed: 2026-11-06
- archive: pending
- relevance: a request to add Martian Grotesk to Google Fonts is open.

### [S1709] MDN — font-smooth
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/font-smooth
- author: MDN
- accessed: 2026-11-06
- archive: pending
- relevance: `-webkit-font-smoothing: antialiased` makes light text on dark "look lighter"; it and `-moz-osx-font-smoothing` work on macOS only and are non-standard.

### [S1710] MDN — Variable fonts guide
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_fonts/Variable_fonts_guide
- author: MDN
- accessed: 2026-11-06
- archive: pending
- relevance: a grade axis changes weight without reflow; the weight axis reflows.

### [S1711] FontLab — The four-stack of screen rendering
- type: article
- url: https://blog.fontlab.com/2026/02/17/the-four-stack-of-screen-rendering/
- author: FontLab
- accessed: 2026-11-06
- archive: pending
- relevance: Apple ignores TrueType hints; Windows handling is in dispute.

### [S1712] MDN — font-synthesis
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/font-synthesis
- author: MDN
- accessed: 2026-11-06
- archive: pending
- relevance: `font-synthesis: none` stops the browser faking bold or italic faces a family lacks.

### [S1713] MDN — font-display
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/font-display
- author: MDN
- accessed: 2026-11-06
- archive: pending
- relevance: `swap` gives "an extremely small block period and an infinite swap period"; during a block period text is laid out with an "invisible fallback font face".

### [S1714] MDN — font-variation-settings
- type: docs
- url: https://developer.mozilla.org/en-US/docs/Web/CSS/font-variation-settings
- author: MDN
- accessed: 2026-11-06
- archive: pending
- relevance: use it "only when no basic properties exist"; it overrides `font-weight` "no matter where they appear in the cascade".

### [S1715] Apple — About Lockdown Mode
- type: docs
- url: https://support.apple.com/en-us/105120
- author: Apple
- accessed: 2026-11-06
- archive: pending
- relevance: under Lockdown Mode "web fonts might not be displayed", so the fallback stack must render the page (published 2026-09-14).

## Block S1750–S1799 — RA-28 Live audio input

### [S1750] Stark, Davies & Plumbley — "Real-time beat-synchronous analysis of musical audio" (DAFx-09)
- type: article
- url: https://dafx.de/paper-archive/2009/papers/paper_65.pdf
- author: Adam M. Stark, Matthew E. P. Davies, Mark D. Plumbley
- published: 2009-09
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005406/https://dafx.de/paper-archive/2009/papers/paper_65.pdf
- relevance: the causal beat tracker pewpew implements: complex spectral difference detection function at 11.6 ms (§2.1, eq. 1), cumulative score with α 0.9 and η 5 and a one-beat future window (§2.2, eqs. 2–5), tempo from a 6 s frame by moving-mean threshold, autocorrelation, comb filterbank and a one-step "Viterbi-like" update, limited to 80–160 BPM "to minimise the common beat tracking error of switching between metrical levels" (§2.3, eqs. 6–12); Table 1 gives CMLc 51.7%, CMLt 58.7%, AMLc 63.3%, AMLt 73.6% for the default tracker and 60.6/71.0/64.9/76.5% when given the tempo and first beat, on Hainsworth's 222 excerpts.

### [S1751] Davies & Plumbley — "Context-dependent beat tracking of musical audio" (IEEE TASLP 15(3):1009–1020, 2007)
- type: article
- url: https://doi.org/10.1109/TASL.2006.885257
- author: Matthew E. P. Davies, Mark D. Plumbley
- published: 2007-03
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20120617091619/http://www.elec.qmul.ac.uk:80/people/markp/2007/DaviesPlumbley07-taslp.pdf (the authors' copy, read from this snapshot on 2026-11-06; volume, issue and pages confirmed via Crossref)
- relevance: the tempo stage Stark §2.3 refers to: a moving-mean threshold over Q = 16 DF samples then half-wave rectification (eqs. 3–4), an autocorrelation normalised by |l − B_f| (eq. 5), a comb template of four elements p = 1…4, each 2p − 1 lags wide and weighted 1/(2p − 1) (eq. 7), and a Rayleigh tempo weighting w(τ) = τ/β² · exp(−τ²/2β²) with β = 43 DF samples, "equivalent to 120 bpm" (eq. 8).

### [S1752] Bello et al. — "A tutorial on onset detection in music signals" (IEEE TSAP 13(5), 2005)
- type: article
- url: https://www.cs.bu.edu/fac/snyder/cs583/Literature%20and%20Resources/bello_onset_tutorial.pdf
- author: Juan Pablo Bello, Laurent Daudet, Samer Abdallah, Chris Duxbury, Mike Davies, Mark B. Sandler
- published: 2005-09
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005424/https://www.cs.bu.edu/fac/snyder/cs583/Literature%20and%20Resources/bello_onset_tutorial.pdf
- relevance: §II-B.3: the phase deviation is "the second difference of the phase", and the complex-domain detection function is the distance between the observed spectral bin and the one predicted from the previous frames, so each detection value reads the current and the two previous frames.

### [S1753] Moon, Skelly & Towsley — "Estimation and removal of clock skew from network delay measurements" (INFOCOM '99)
- type: article
- url: https://web.cs.umass.edu/publication/docs/1998/UM-CS-1998-043.pdf
- author: Sue B. Moon, Paul Skelly, Don Towsley
- published: 1999-03
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005445/https://web.cs.umass.edu/publication/docs/1998/UM-CS-1998-043.pdf
- relevance: estimates the skew between two clocks from one-way delays with a line that "lies under all the data points, but as closely to them as possible" (a linear program); doi:10.1109/INFCOM.1999.749287. The rejected alternative to pewpew's median fit: one early point bounds the whole line.

### [S1754] python-sounddevice (repository)
- type: code
- url: https://github.com/spatialaudio/python-sounddevice
- pinned: spatialaudio/python-sounddevice@283f40d6ebdedda2c0d609c41a6a14476c1dc87e
- author: Matthias Geier and contributors
- license: MIT
- accessed: 2026-11-06
- relevance: `src/sounddevice.py` L845 builds every stream's callback with `_ffi.callback` (a cffi callback); `read_available` (L1180–1185) and `read()` with its overflow flag (L1463–1498) allow a callback-free stream polled from the loop thread; `_initialize` (L2921) and `_terminate` (L2949) are the private calls a re-enumeration needs.

### [S1755] sounddevice 0.5.6 on PyPI
- type: docs
- url: https://pypi.org/project/sounddevice/0.5.6/
- author: Matthias Geier
- published: 2026-08-17
- accessed: 2026-11-06
- relevance: 0.5.6 ships a `py3-none-macosx_10_6_x86_64.macosx_10_6_universal2` wheel that bundles PortAudio and a `py3-none-any` wheel for Linux, which needs the system `libportaudio2`; so CI, which has no PortAudio, must never import it.

### [S1756] cffi (repository)
- type: code
- url: https://github.com/python-cffi/cffi
- pinned: python-cffi/cffi@e20c65d938842f82ce63983150b286956081cb27
- author: Armin Rigo, Maciej Fijalkowski and contributors
- license: MIT
- accessed: 2026-11-06
- relevance: `src/c/_cffi_backend.c` L6280–6285: `invoke_callback` takes the GIL (`gil_ensure`) before it runs a Python callback, so PortAudio's real-time thread waits whenever another Python thread holds the GIL.

### [S1757] PortAudio (repository)
- type: code
- url: https://github.com/PortAudio/portaudio
- pinned: PortAudio/portaudio@0dce0e9cf5c2235f04f2caeb2ca09db358cb8a6e
- author: Ross Bencina, Phil Burk and contributors
- license: MIT-style (LICENSE.txt)
- accessed: 2026-11-06
- relevance: `include/portaudio.h` L187–192: "The final matching call to Pa_Terminate() will automatically close any PortAudio streams that are still open", so re-enumerating devices is safe only with no stream open. Its last release is v19.7.0 (2021-04-06).

### [S1758] PortAudio issue #11 — the hotplug request
- type: forum
- url: https://github.com/PortAudio/portaudio/issues/11
- author: PortAudio contributors
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005557/https://github.com/PortAudio/portaudio/issues/11
- relevance: PortAudio has no hotplug API: the request has been open since 2006, and PortAudio lists devices when it initialises, so a replugged interface needs a re-enumeration.

### [S1759] LedFx (repository, audio pin)
- type: code
- url: https://github.com/LedFx/LedFx
- pinned: LedFx/LedFx@bf10b599efe74c809a743c6e7c319dcbf77e7dc3
- author: LedFx developers
- license: GPL-3.0 (read only, never copied; ADR-012)
- accessed: 2026-11-06
- relevance: `ledfx/effects/audio.py` L1268–1300: the energy beat reads `time.time()` for its refractory period, the wall-clock pattern pewpew's sample clock replaces; LedFx 2.2.1 (2026-10-04) still depends on `aubio-ledfx` and `sounddevice`.

### [S1760] Resolume — BPM (manual page)
- type: docs
- url: https://resolume.com/support/en/bpm
- author: Resolume
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005707/https://resolume.com/support/en/bpm
- relevance: a professional VJ tool's tempo controls: typed BPM, Tap, Resync and Nudge; the page says nothing about detection either way.

### [S1761] TouchDesigner — Beat CHOP (documentation)
- type: docs
- url: https://docs.derivative.ca/Beat_CHOP
- author: Derivative
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005701/https://docs.derivative.ca/Beat_CHOP
- relevance: generates ramp, pulse, count and bar channels from a tapped or set tempo rather than from detection: the tap-and-resync precedent.

### [S1762] BeatNet on PyPI (JSON metadata)
- type: docs
- url: https://pypi.org/pypi/BeatNet/json
- author: Mojtaba Heydari
- published: 2023-11-28
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005750/https://pypi.org/pypi/BeatNet/json
- relevance: BeatNet 1.1.3, its last release, requires `numba ==0.54.1` and `librosa`; with S1763 it cannot install on Python 3.11–3.14.

### [S1763] numba 0.54.1 on PyPI (JSON metadata)
- type: docs
- url: https://pypi.org/pypi/numba/0.54.1/json
- author: Anaconda, Inc. and contributors
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005806/https://pypi.org/pypi/numba/0.54.1/json
- relevance: `requires_python` is `>=3.7,<3.10`, so BeatNet's pin needs a Python older than pewpew's 3.11 floor.

### [S1764] aubio-ledfx on PyPI (JSON metadata)
- type: docs
- url: https://pypi.org/pypi/aubio-ledfx/json
- author: LedFx developers
- published: 2026-10-03
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005825/https://pypi.org/pypi/aubio-ledfx/json
- relevance: 0.4.12 ships wheels for cp311–cp315, manylinux aarch64 included, under GPL-3.0: the maintenance objection is gone and the licence objection remains.

### [S1765] Shannon et al. — "Speech recognition with primarily temporal cues" (Science 270:303–304, 1995)
- type: article
- url: https://www.cns.nyu.edu/events/earclub/artfiles/Shannon1995.pdf
- author: Robert V. Shannon, Fan-Gang Zeng, Vivek Kamath, John Wygonski, Michael Ekelid
- published: 1995-10-13
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005846/https://www.cns.nyu.edu/events/earclub/artfiles/Shannon1995.pdf
- relevance: speech stays highly recognisable from the envelopes of three or four broad bands; envelope cut-offs of 50–500 Hz did not differ significantly. So a 16-band feature log from a microphone is close to a speech recording.

### [S1766] python-sounddevice issue #267 — all-zero input on macOS
- type: forum
- url: https://github.com/spatialaudio/python-sounddevice/issues/267
- author: python-sounddevice users
- accessed: 2026-11-06
- relevance: users report that macOS gives a process without microphone permission all-zero input and no error (issue #574 reports the same); whether a LaunchAgent gets this is not verified.

### [S1767] Essentia (repository)
- type: code
- url: https://github.com/MTG/essentia
- pinned: MTG/essentia@23ae7baddecfc3227ba23ad69fa11f73ac5293a4
- author: Music Technology Group, Universitat Pompeu Fabra
- license: AGPL-3.0
- accessed: 2026-11-06
- relevance: a full audio-analysis library ruled out by its licence (ADR-012); its 2.1b6.dev1438 build (2026-05-19) has no Linux aarch64 wheel.

### [S1768] BTrack (repository, pinned)
- type: code
- url: https://github.com/adamstark/BTrack
- pinned: adamstark/BTrack@9d6127618a5679e9caa74c594b88f1d74f0e035f
- author: Adam Stark
- license: GPL-3.0
- accessed: 2026-11-06
- relevance: the GPL implementation of Stark et al. 2009 (S1750); pewpew takes the algorithm from the papers and never reads or copies this code. `btrack-beat-tracker` 1.0.7 (2025-12-31) ships macOS arm64 wheels only.

### [S1769] Beat This! (repository)
- type: code
- url: https://github.com/CPJKU/beat_this
- pinned: CPJKU/beat_this@b95c8ab0c58c2d9fcfd40508ae8dffbc05ac4f5c
- author: Francesco Foscarin, Jan Schlüter, Gerhard Widmer
- license: MIT
- accessed: 2026-11-06
- relevance: a 2024 transformer beat tracker (1.1.0, 2026-04-14, PyTorch) that works on whole files: a candidate for offline cue maps, not the live path.

### [S1770] librosa changelog (1.0.0)
- type: docs
- url: https://librosa.org/doc/latest/changelog.html
- author: librosa developers
- published: 2026-08-11
- accessed: 2026-11-06
- relevance: librosa 1.0.0 (ISC, Python ≥3.12, numba, scipy, scikit-learn) adds no streaming or causal onset or beat tracking: offline only.

### [S1771] WLED (repository, v16.0.1 pin)
- type: code
- url: https://github.com/wled/WLED
- pinned: wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c
- author: Christian Schwinne and WLED contributors
- license: "EUPL v. 1.2 or later" (LICENSE L2)
- accessed: 2026-11-06
- relevance: `usermods/audioreactive/audio_reactive.cpp` L799–812: the Audio Sync V2 packet is 44 bytes of levels, a peak flag, 16 GEQ magnitude bytes and the major peak, with no timestamp and no phase; the usermod uses ArduinoFFT by default on the ESP32 and S3 (L123, L131); `wled00/json.cpp` L908–909 set `brand` and `product` in `/json/info`.

### [S1772] WLED-AudioReactive-Usermod (MoonModules, 2026 pin)
- type: code
- url: https://github.com/MoonModules/WLED-AudioReactive-Usermod
- pinned: MoonModules/WLED-AudioReactive-Usermod@a4338f2ae26e303653c8fffbbb9af975401cefc5
- author: MoonModules contributors
- license: EUPL-1.2
- accessed: 2026-11-06
- relevance: the MM fork adds an 8-bit frame counter to the V2 packet and by default stops sending after 30 s of silence (`audio_reactive.h` L234, L241), so silence looks like loss.

### [S1773] esp-dsp benchmarks (Espressif)
- type: docs
- url: https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html
- author: Espressif Systems
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261009074429/https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/esp-dsp-benchmarks.html (snapshot predates accessed date; Save Page Now answered 429 on 2026-11-06; refresh next verification pass)
- relevance: `dsps_fft2r_fc32` takes 97 847 cycles for a 1024-point complex FFT on the ESP32-S3 (O2): about 0.41 ms at 240 MHz, so CPU is not what rules out features on a capture node.

### [S1774] RFC 9119 — Multicast considerations over IEEE 802 wireless media
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc9119.html
- author: C. Perkins, M. McBride, D. Stanley, W. Kumari, JC. Zúñiga
- published: 2021-10
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107005943/https://www.rfc-editor.org/rfc/rfc9119.html
- relevance: §3.1: Wi-Fi multicast gets no acknowledgement and goes at a basic rate, and it is held for power-saving stations until the next DTIM beacon; the reason capture nodes send unicast (with ADR-003).

### [S1775] RFC 6716 — Definition of the Opus audio codec
- type: spec
- url: https://www.rfc-editor.org/rfc/rfc6716.html
- author: JM. Valin, K. Vos, T. Terriberry
- published: 2012-09
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010017/https://www.rfc-editor.org/rfc/rfc6716.html
- relevance: §2 and §3.1 (Table 2): CELT frames of 2.5–20 ms with a 2.5 ms look-ahead; the codec is lossy, so it changes the per-bin phase an onset detector reads.

### [S1776] POSIX.1-2024 — connect()
- type: spec
- url: https://pubs.opengroup.org/onlinepubs/9799919799/functions/connect.html
- author: The Open Group / IEEE
- published: 2024
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010121/https://pubs.opengroup.org/onlinepubs/9799919799/functions/connect.html
- relevance: on a connectionless socket, `connect()` sets the peer address, and the socket then receives datagrams from that address only: the kernel drops a capture node's spoofed or stray senders.

### [S1777] ESP-IDF (repository, audio-node pin)
- type: code
- url: https://github.com/espressif/esp-idf
- pinned: espressif/esp-idf@0e6b480f858c69862ffb6001d96e9eef74599a6e
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-11-06
- relevance: `components/esp_driver_i2s/i2s_common.c` L943–946: when the receive queue is full the driver drops the oldest buffer and calls `on_recv_q_ovf`, whose event carries the dropped size (`include/driver/i2s_types.h` L72–75); L1965–1993 divide the master clock fractionally; `components/soc/esp32s3/include/soc/clk_tree_defs.h` L327–340: the S3's I2S clock sources are PLL_F240M, PLL_F160M, XTAL and external, with no APLL.

### [S1778] ESP-IDF I2S driver documentation (ESP32-S3, stable)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/i2s.html
- author: Espressif Systems
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010205/https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/i2s.html
- relevance: the S3 has two I2S controllers with standard, PDM and TDM modes; at 24 bits the sample rate "might be imprecise since the BCLK division is not a integer", so a node chooses a slot width and MCLK multiple that keep it integer.

### [S1779] ESPHome (repository)
- type: code
- url: https://github.com/esphome/esphome
- pinned: esphome/esphome@3ebcb88c5b21f19635dfcbbeaf0c99d5dd79e9c9
- author: ESPHome contributors
- license: GPL-3.0 for the C++ runtime (LICENSE)
- accessed: 2026-11-06
- relevance: its runtime is GPLv3 and its microphone component has no stream to an arbitrary host, so it is at most an unpublished bench prototype for a capture node.

### [S1780] EUPL v1.2 — Commission Implementing Decision (EU) 2017/863
- type: spec
- url: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32017D0863
- author: European Commission
- published: 2017-05-18
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010239/https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32017D0863
- relevance: Art. 5's copyleft binds a licensee who "distributes or communicates copies of the Original Works or Derivative Works"; Art. 1 leaves what counts as a derivative work to copyright law.

### [S1781] Directive 2009/24/EC on the legal protection of computer programs
- type: spec
- url: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32009L0024
- author: European Parliament and Council
- published: 2009-04-23
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010310/https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32009L0024
- relevance: Art. 1(2) and Recital 11: ideas and principles underlying a program, including those of its interfaces, are not protected by copyright.

### [S1782] CJEU C-406/10, SAS Institute Inc. v World Programming Ltd (2012)
- type: spec
- url: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62010CJ0406
- author: Court of Justice of the European Union
- published: 2012-05-02
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261107010407/https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62010CJ0406
- relevance: ruling 1, paras 39 and 46: a program's functionality, programming language and data file formats are not a form of expression protected under Directive 91/250, which 2009/24/EC codifies.

### [S1783] 17 U.S. Code §102 — Subject matter of copyright (Cornell LII)
- type: spec
- url: https://www.law.cornell.edu/uscode/text/17/102
- author: United States Congress (via Legal Information Institute)
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261102200509/https://www.law.cornell.edu/uscode/text/17/102 (snapshot predates accessed date; Save Page Now answered 429 on 2026-11-06; refresh next verification pass)
- relevance: §102(b): copyright never extends to any idea, procedure, process, system or method of operation, so a wire format implemented from its byte layout carries no obligation in the US either.

### [S1784] arduinoFFT (repository)
- type: code
- url: https://github.com/kosme/arduinoFFT
- pinned: kosme/arduinoFFT@6b3ef9732db800bb2c658eefb7ad8939eb44e6e2
- author: Enrique Condes
- license: GPL-3.0
- accessed: 2026-11-06
- relevance: the FFT that WLED's audioreactive usermod uses by default on the ESP32 and S3; a reason pewpew never ships a WLED audio build.

### [S1785] Improv Wi-Fi — serial protocol
- type: spec
- url: https://www.improv-wifi.com/serial/
- author: Improv Wi-Fi (Open Home Foundation)
- accessed: 2026-11-06
- relevance: the serial provisioning protocol `python -m pewpew wifi` speaks; commands 0x05 Set Hostname and 0x06 Set Device Name name a node over the same USB session, and the spec defines no vendor command range.

### [S1786] esp-protocols (repository, mdns)
- type: code
- url: https://github.com/espressif/esp-protocols
- pinned: espressif/esp-protocols@4072d2d5916ae740502920b42b586d67eb7914e7
- author: Espressif Systems
- license: Apache-2.0
- accessed: 2026-11-06
- relevance: the `mdns` 1.15.1 component a capture node uses to answer as `pewpew-line-N.local`.

### [S1787] Improv Wi-Fi SDK for C++ (repository)
- type: code
- url: https://github.com/improv-wifi/sdk-cpp
- pinned: improv-wifi/sdk-cpp@8e87b560bd5dd7de296847538ea11edb70401d65
- author: Improv Wi-Fi contributors
- license: Apache-2.0
- accessed: 2026-11-06
- relevance: the device side of Improv serial for the capture-node firmware.

### [S1788] ESP-IDF copyrights and licences page (ESP32-S3)
- type: docs
- url: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/COPYRIGHT.html
- author: Espressif Systems
- accessed: 2026-11-06
- relevance: an IDF image also holds BSD (newlib, lwIP, wpa_supplicant, FreeBSD net80211), MIT (FreeRTOS) and Apache-2.0 (Mbed TLS) code, so a published node binary ships a notices file.

### [S1789] esp32-wifi-lib (repository)
- type: code
- url: https://github.com/espressif/esp32-wifi-lib
- pinned: espressif/esp32-wifi-lib@a7b9e5a0ccb03200428bec766562248f9124718f
- author: Espressif Systems
- license: Apache-2.0 (README.rst L8)
- accessed: 2026-11-06
- relevance: the licence of the binary Wi-Fi libraries in every IDF image.

### [S1790] esp32-walkie-talkie (repository)
- type: code
- url: https://github.com/atomic14/esp32-walkie-talkie
- pinned: atomic14/esp32-walkie-talkie@bd357bc50032e08e7017bd9b59e01fd23bcedef1
- author: Chris Greening (atomic14)
- license: MIT
- accessed: 2026-11-06
- relevance: an MIT reference for I2S capture sent over UDP from an ESP32.

### [S1791] Texas Instruments PCM1808 (product page)
- type: datasheet
- url: https://www.ti.com/product/PCM1808
- author: Texas Instruments
- accessed: 2026-11-06
- relevance: an active 24-bit stereo ADC with 99 dB SNR and a 3 Vp-p single-ended full scale that needs a system clock of 256, 384 or 512 fs: the line-in node's converter. A +4 dBu sine (3.47 Vp-p) clips it; −10 dBV (0.89 Vp-p) fits.

### [S1792] DigiKey — TDK InvenSense ICS-43434
- type: product
- url: https://www.digikey.com/en/products/detail/tdk-invensense/ICS-43434/6140298
- author: DigiKey
- accessed: 2026-11-06
- relevance: the I2S MEMS microphone of the later mic node is listed as Obsolete (53 692 in stock on 2026-11-06), so buy spares before that variant.

### [S1793] Raspberry Pi 5 (product page)
- type: product
- url: https://www.raspberrypi.com/products/raspberry-pi-5/
- author: Raspberry Pi Ltd
- accessed: 2026-11-06
- relevance: the specification lists no analogue audio, so a Pi 5 pewpew host takes audio from a USB interface or a capture node.

### [S1794] scottlawsonbc/audio-reactive-led-strip (2026 pin)
- type: code
- url: https://github.com/scottlawsonbc/audio-reactive-led-strip
- pinned: scottlawsonbc/audio-reactive-led-strip@91dabce8fcea0392a040852f21d5bca80fb754fa
- author: Scott Lawson
- license: MIT
- accessed: 2026-11-06
- relevance: `python/microphone.py` captures in blocking mode, a PyAudio `read` followed by draining what is available, with no Python callback: precedent for polled capture.

### [S1795] Debian trixie — libportaudio2 package
- type: docs
- url: https://packages.debian.org/trixie/libportaudio2
- author: Debian
- accessed: 2026-11-06
- relevance: trixie ships `libportaudio2` 19.6.0-1.2+b3 for arm64, older than PortAudio's PulseAudio host API, so on Pi OS PortAudio reaches the interface through ALSA.

### [S1796] Apple — NSMicrophoneUsageDescription
- type: docs
- url: https://developer.apple.com/documentation/bundleresources/information-property-list/nsmicrophoneusagedescription
- author: Apple
- accessed: 2026-11-06
- relevance: a bundled macOS app must declare why it uses the microphone; a LaunchAgent's permission path is not documented, so the first attended run checks for all-zero input.

### [S1797] Ableton Link (repository)
- type: code
- url: https://github.com/Ableton/link
- pinned: Ableton/link@5ba907ae027a8c2ec8824463e37296dcefc5e9be
- author: Ableton AG
- license: GPL-2.0-or-later
- accessed: 2026-11-06
- relevance: tempo sync between music apps; GPL, so pewpew could only reach it through a separate process such as Carabiner (ADR-012 rule 2), later.

## Block S1800–S1849 — RA-29 Naming the aura

### [S1800] Chromatik Guide — application overview
- type: docs
- url: https://chromatik.co/guide/application-overview/
- author: Heron Arts
- accessed: 2026-11-06
- relevance: names the live object "the Chromatik runtime" and the saved file a project: "Chromatik projects are stored in files using the .lxp extension".

### [S1801] TouchDesigner wiki — Perform Mode and the .toe file
- type: docs
- url: https://derivative.ca/UserGuide/Perform_Mode
- also: https://derivative.ca/UserGuide/.toe (via search)
- author: Derivative
- accessed: 2026-11-06
- relevance: Perform Mode is "an optimized mode for live performance"; the saved file is "A TouchDesigner Environment file (.toe), or 'Project file'" (the .toe line from a search summary).

### [S1802] Resolume — decks and compositions
- type: docs
- url: https://resolume.com/support/en/decks
- also: https://jonasjohansson.gitbooks.io/guide/live-visuals/resolume.html (a community guide)
- author: Resolume; Jonas Johansson
- accessed: 2026-11-06
- relevance: the saved file is a composition, which "can contain a number of decks"; the community guide gives the .avc extension and "save the comp".

### [S1803] MadMapper — project files, scenes and cues
- type: docs
- url: https://docs.madmapper.com/
- also: https://artslab.unm.edu/wp-content/uploads/MadMapper-Tutorial.pdf (UNM ARTSLab tutorial)
- author: GarageCUBE; UNM ARTSLab
- accessed: 2026-11-06
- relevance: the docs list "MadMapper Project File Structure" and "Merging Projects", and Scenes & Cues under "Live Performance & Control"; the .mad extension was not confirmed on an official page.

### [S1804] pixelblaze-client 1.0.1 (PyPI)
- type: docs
- url: https://pypi.org/project/pixelblaze-client/1.0.1/
- author: zranger1
- accessed: 2026-11-06
- relevance: Pixelblaze binary backups (.pbb), from a search summary.

### [S1805] xLights manual — defining the show directory
- type: docs
- url: https://manual.xlights.org/xlights/chapters/chapter-two-quick-start-guide/defining-the-show-directory
- author: xLights
- accessed: 2026-11-06
- relevance: xLights' saved state is a show directory, "where all your xLights files are stored and where your sequences will be created"; sequences are .xsq (via search).

### [S1806] Falcon Player manual — status and control page
- type: docs
- url: https://falcon-player.gitbooks.io/falcon-player-manual/chapter_seven_status__control/status_page.html
- author: Falcon Player project
- accessed: 2026-11-06
- relevance: FPP's saved items are playlists, schedules and sequences; Master and Remote modes (via search).

### [S1807] LedFx API docs v2.0.58
- type: docs
- url: https://ledfx.readthedocs.io/en/v2.0.58/api.html
- author: LedFx
- accessed: 2026-11-06
- relevance: `/api/config` holds `virtuals` and `scenes` keys (via search).

### [S1808] Ableton help — Live Sets and Live Projects
- type: docs
- url: https://help.ableton.com/hc/en-us/articles/360002864179
- author: Ableton
- accessed: 2026-11-06
- relevance: a Live Set is saved as .als inside a Live Project (via search).

### [S1809] Cycling '74 Max user guide — pattr and projects
- type: docs
- url: https://docs.cycling74.com/userguide/pattr/
- also: https://docs.cycling74.com/userguide/projects/
- author: Cycling '74
- accessed: 2026-11-06
- relevance: Max saves "a patcher to a .maxpat document"; projects "collect and organize dependencies".

### [S1810] Notch manual — Blocks and media servers
- type: docs
- url: https://manual.notch.one/1.0/en/docs/workflows/working-with-media-servers/blocks
- also: https://manual.notch.one/1.0/en/docs/reference/user-interface/resources-window
- author: Notch
- accessed: 2026-11-06
- relevance: a Notch Block is a "self-contained, single-file export" played inside a media server; the project file is .dfx (via search).

### [S1811] QLab fundamentals (third-party notes)
- type: article
- url: https://techie-docs.pages.dev/qlab/qlab-fundamentals
- accessed: 2026-11-06
- relevance: QLab's saved file is a workspace holding cue lists and carts; the official page was not fetched.

### [S1812] grandMA3 help 2.5 — show file management
- type: docs
- url: https://help.malighting.com/grandMA3/2.5/HTML/show_file_management.html
- author: MA Lighting
- accessed: 2026-11-06
- relevance: the console's saved file is a show file, which "contains all the information that is related to the show" (patch, cues, timings).

### [S1813] ETC Eos family help — saving show files
- type: docs
- url: https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/05_Show_Files/Saving_Show_Files.htm
- author: ETC
- accessed: 2026-11-06
- relevance: Eos saves a show file in ESF3D, ESF2 or ESF format.

### [S1814] Philips Hue — entertainment configurations, scenes and effects
- type: docs
- url: https://pub.dev/documentation/dart_hue/2.3.0/domain_models_entertainment_configuration_entertainment_configuration/EntertainmentConfiguration-class.html
- also: https://pypi.org/project/hue-entertainment/, https://philips-hue.com/en-gb/support/topic/scenes-effects/100081
- author: dart_hue; hue-entertainment; Signify
- accessed: 2026-11-06
- relevance: the streaming object is an entertainment configuration ("Start streaming for this entertainment configuration"), an entertainment area in the app; saved states are scenes and effects. The Hue developer pages were not read (login wall).

### [S1815] Nanoleaf app (App Store listing)
- type: product
- url: https://apps.apple.com/us/app/nanoleaf/id1049333656
- author: Nanoleaf
- accessed: 2026-11-06
- relevance: saved states are Scenes, with Playlists and Schedules.

### [S1816] Twinkly help — creating an effects playlist
- type: docs
- url: https://help.twinkly.com/hc/en-gb/articles/18277795063069-how-do-i-create-my-effects-playlist
- author: Twinkly
- accessed: 2026-11-06
- relevance: saved states are effects and a playlist of effects.

### [S1817] Enlighted app (App Store listing)
- type: product
- url: https://apps.apple.com/us/app/enlighted/id1440237978
- author: Enlighted
- accessed: 2026-11-06
- relevance: LED garments ("Enlighted art or clothing") hold modes; "Mimic" drives several garments at once; master brightness is on Device Settings.

### [S1818] MIT Media Lab Responsive Environments — Halo
- type: article
- url: https://resenv.media.mit.edu/halo/
- author: MIT Media Lab
- accessed: 2026-11-06
- relevance: "Halo is a wearable lighting device", phone-controlled and "pre-programmed with a range of lighting compositions".

### [S1819] ColorMorph Halo app (App Store listing)
- type: product
- url: https://apps.apple.com/app/id1071028691
- accessed: 2026-11-06
- relevance: a wearable light's app with modes and saved colours (via search).

### [S1820] Adafruit Learn — Bluefruit Luminary Lanterns with capacitive touch
- type: article
- url: https://learn.adafruit.com/bluefruit-luminary-lanterns-with-capacitive-touch
- author: Adafruit
- accessed: 2026-11-06
- relevance: CircuitPython and NeoPixel lanterns whose modes (Off, Reading Light, Candle Flame, Rainbow Swirl) switch from a BLE app or by touch (via search).

### [S1821] Processing — environment reference
- type: docs
- url: https://processing.org/environment/
- author: Processing Foundation
- accessed: 2026-11-06
- relevance: "a computer program is called a sketch"; sketches live in the Sketchbook; the running sketch is a PApplet subclass (via search).

### [S1822] openFrameworks ofBook — setup and project structure
- type: docs
- url: https://openframeworks.cc/ofBook/chapters/setup_and_project_structure.html
- author: openFrameworks community
- accessed: 2026-11-06
- relevance: the running thing is the app (`ofApp`, from `ofBaseApp`, via search); the saved unit is a project under `apps/myApps`.

### [S1823] VCV Rack manual
- type: docs
- url: https://vcvrack.com/manual
- author: VCV
- accessed: 2026-11-06
- relevance: the running thing is the rack; the saved file is a patch (.vcv) (via search).

### [S1824] QLC+ v4 docs — glossary and concepts
- type: docs
- url: https://docs.qlcplus.org/v4/basics/glossary-and-concepts
- author: QLC+ project
- accessed: 2026-11-06
- relevance: QLC+ functions include Scene, Chaser, and a Show function for "a time driven light show"; the live surface is the Virtual Console.

### [S1825] MADRIX 5 help — setup files
- type: docs
- url: https://help.madrix.com/m5/html/madrix/hidd_madrix_setup_new_open.html
- author: inoage
- accessed: 2026-11-06
- relevance: MADRIX saves a Setup file (via search).

### [S1826] openrgb-python docs — usage
- type: docs
- url: https://openrgb-python.readthedocs.io/en/stable/pages/usage.html
- accessed: 2026-11-06
- relevance: OpenRGB's saved state is a profile (.orp), loaded on the server (via search).

### [S1827] hyperion-py (PyPI)
- type: docs
- url: https://pypi.org/project/hyperion-py
- accessed: 2026-11-06
- relevance: Hyperion's running object is an instance (via search).

### [S1828] ASUS ROG — how to customize your PC's RGB lighting with Aura Sync
- type: article
- url: https://rog.asus.com/articles/guides/how-to-customize-your-pcs-rgb-lighting-with-aura-sync/
- author: ASUS
- accessed: 2026-11-06
- relevance: ASUS Aura / Aura Sync is RGB-lighting control software with effect presets and Scenario Profiles (via search): the one prior use of "aura" in lighting found.

### [S1829] Remote Falcon docs — control panel settings
- type: docs
- url: https://docs.remotefalcon.com/docs/docs/control-panel/remote-falcon-settings
- author: Remote Falcon
- accessed: 2026-11-06
- relevance: an FPP plugin whose Jukebox mode adds "a requested sequence ... to a queue", beside a Voting mode (via search; the page returned 404 when fetched).

### [S1830] corajr/loom — an audiovisual pattern language library for Processing
- type: code
- url: https://github.com/corajr/loom
- pinned: corajr/loom@e2f4cf82f1b98108d39801e512db91318aada320
- author: Cora Johnson-Roberson
- license: other (license.txt; GitHub reports NOASSERTION)
- published: 2019-12-19 (last commit; archived)
- accessed: 2026-11-06
- relevance: prior use of "loom" in creative coding: patterns that "may unfold along a linear timeline or recur cyclically", set off by sensors or user actions.

### [S1831] Evan Brooks — Loom (RISD)
- type: article
- url: https://htmloutput.risd.gd/project-brooks-loom
- author: Evan Brooks
- accessed: 2026-11-06
- relevance: Loom is "a live coding environment" whose edits "appear instantly in all browsers".

### [S1832] Wikipedia — Jacquard machine
- type: article
- url: https://en.wikipedia.org/wiki/Jacquard_machine
- accessed: 2026-11-06
- relevance: the loom metaphor: a Jacquard loom weaves from "punched cards laced together into a continuous sequence".

### [S1833] Wikipedia — Light organ
- type: article
- url: https://en.wikipedia.org/wiki/Light_organ
- accessed: 2026-11-06
- relevance: a light organ is "an electronic device that automatically converts an audio signal" into light.

### [S1834] Wiktionary — loom, jukebox, lantern, aura
- type: docs
- url: https://en.wiktionary.org/wiki/aura
- also: https://en.wiktionary.org/wiki/loom, https://en.wiktionary.org/wiki/jukebox, https://en.wiktionary.org/wiki/lantern
- author: Wiktionary contributors
- license: CC BY-SA 4.0
- accessed: 2026-11-06
- relevance: everyday senses of the four finalists: aura "A distinctive atmosphere or quality surrounding or associated with something or someone"; loom "A frame or machine … in which a weaver forms cloth out of thread", and the verb "To appear in an exaggerated or threatening form"; jukebox "A coin-operated machine that plays recorded music, with push-buttons to make selections", and software "capable of replaying tracks"; lantern "A case of translucent or transparent material made to protect a flame, or light, used to illuminate its surroundings".

## Block S1850–S1899 — pewpew's licence (ADR-012)

### [S1850] Apache License, Version 2.0 (Apache Software Foundation)
- type: spec
- url: https://www.apache.org/licenses/LICENSE-2.0.txt
- author: Apache Software Foundation
- published: 2004-01
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261103064928/https://www.apache.org/licenses/LICENSE-2.0.txt (snapshot predates accessed date; refresh next verification pass)
- relevance: §3 grants each contributor's patent licence and ends it for anyone who sues over the work's patents; §4 sets the redistribution conditions (a copy of the licence, notices on changed files, a NOTICE file passed on if present); §5 puts a contribution under the same licence unless its author states otherwise. The text of pewpew's root `LICENSE`.

### [S1851] choosealicense.com — Apache License 2.0
- type: docs
- url: https://choosealicense.com/licenses/apache-2.0/
- author: GitHub (choosealicense.com)
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261026205518/https://choosealicense.com/licenses/apache-2.0/ (snapshot predates accessed date; refresh next verification pass)
- relevance: "Contributors provide an express grant of patent rights"; lists "Patent use" among the permissions and "State changes" among the conditions.

### [S1852] choosealicense.com — MIT License
- type: docs
- url: https://choosealicense.com/licenses/mit/
- author: GitHub (choosealicense.com)
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261030174003/https://choosealicense.com/licenses/mit/ (snapshot predates accessed date; refresh next verification pass)
- relevance: MIT's permissions omit "Patent use", and its one condition is that the copyright and licence notice go with every copy — the per-copy notice the excerpt notes keep.

### [S1853] FSF — Various Licenses and Comments about Them
- type: docs
- url: https://www.gnu.org/licenses/license-list.html
- author: Free Software Foundation
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261017101707/https://www.gnu.org/licenses/license-list.html (snapshot predates accessed date; refresh next verification pass)
- relevance: Apache 2.0 is "compatible with version 3 of the GNU GPL" but "not compatible with GPL version 2" (patent termination and indemnification); the FSF recommends it "for substantial programs over other lax permissive licenses" for its patent termination provision; Expat (MIT) is compatible with the GPL.

### [S1854] Open Source Initiative — Apache License, Version 2.0
- type: docs
- url: https://opensource.org/license/apache-2-0
- author: Open Source Initiative
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20260310123931/https://opensource.org/license/apache-2-0 (snapshot predates accessed date; refresh next verification pass)
- relevance: an OSI-approved licence in its "Popular / Strong Community" set, SPDX short identifier `Apache-2.0`.

### [S1855] GNU General Public License, version 3 (FSF)
- type: spec
- url: https://www.gnu.org/licenses/gpl-3.0.txt
- author: Free Software Foundation
- published: 2007-06-29
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261026121547/http://www.gnu.org/licenses/gpl-3.0.txt (snapshot predates accessed date; refresh next verification pass)
- relevance: §4: verbatim copies may be conveyed if their notices stay intact and every recipient gets a copy of the licence — the condition `research/excerpts/LICENSES/GPL-3.0.txt` meets.

### [S1856] GNU General Public License, version 2 (FSF)
- type: spec
- url: https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
- author: Free Software Foundation
- published: 1991-06
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261024005644/http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt (snapshot predates accessed date; refresh next verification pass)
- relevance: §1: verbatim copies may be distributed with the copyright notice, the notices kept intact and a copy of the licence — the condition `research/excerpts/LICENSES/GPL-2.0.txt` meets for the FPP excerpt.

### [S1857] 17 U.S. Code §107 — Limitations on exclusive rights: Fair use (Cornell LII)
- type: spec
- url: https://www.law.cornell.edu/uscode/text/17/107
- author: United States Congress (via Legal Information Institute)
- accessed: 2026-11-06
- archive: https://web.archive.org/web/20261101224924/https://www.law.cornell.edu/uscode/text/17/107 (snapshot predates accessed date; refresh next verification pass)
- relevance: fair use for "criticism, comment … scholarship, or research", weighed by purpose, the amount used and the effect on the market — the basis for keeping only brief quotations of the unlicensed Pixelblaze docs [S680].
