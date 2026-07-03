# RA-01b: Python-native pattern engine gap check

Last researched: 2026-07-03
Status: draft
S-ID block: S030–S049

## Key questions

1. Does a dominant, actively maintained Python-native LED pattern engine exist in 2026?
2. For every credible candidate: pattern-authoring model, output quality (dithering / 16-bit / interpolation), protocol support, maintenance, adoption.
3. What serious non-Python engines (Rust/Go/C++) emerged 2024–2026 that compete or complement?
4. Honest conclusion: is the gap real, and what must pewpew do that nothing else does?

## Findings

### Candidate sweep methodology

GitHub topic sweeps run 2026-07-03 via `gh search repos` (topics: `led`, `neopixel`,
`wled`, `addressable-led`, `led-matrix`, `artnet`, `sacn`; Python-filtered where
sensible, sorted by stars), plus free-text searches ("led effect engine", "led
animation framework", Rust-filtered variants). Result: across all sweeps, the ONLY
Python repos that qualify as general-purpose pattern/effect *engines* (as opposed to
single-purpose apps like scoreboards, Piano-LED-Visualizer, or device-specific BLE
controllers) were LedFx [S011], led-control [S017], the dead BiblioPixel [S030], and
the dead py-ledart [S018]. No new Python engine with >50 stars created 2023–2026
surfaced in any sweep. The highest-starred *new* (2024+) Python LED project found was
WLEDVideoSync (64 stars) — a video/screen caster to E1.31/Art-Net/DDP, not a pattern
engine [S033].

### led-control (jackw01) [S017]

The closest thing to "pewpew already exists" — and it is unmaintained.

- **Pattern-authoring model**: Python functions acting as per-pixel fragment shaders
  over `(t, dt, x, y, z, prev_state)`, editable live in a web code editor; supports
  1D/2D/3D pixel arrangements [S017].
- **Output quality**: perceptually-tuned HSV and secondary color processing in a C
  extension for speed; claims ~150 fps for 150 LEDs on a Pi Zero [S017]. No temporal
  dithering, no 16-bit output path, no frame interpolation (README/docs describe
  none) [S017][NEEDS-VERIFICATION — confirm by code read].
- **Protocols**: E1.31 sACN in and out; direct WS2812/SK6812 on Pi GPIO [S017].
- **Maintenance**: MIT license; last commit 2023-11-10
  (`8e3fe1d0456e589213ecdef1dc8ce57aa15142b6`, master HEAD as of 2026-07-03); 193
  stars; no releases/commits in ~2.7 years — dormant [S017].
- **Form factor**: Pi-class hosts (portable/room); not wearable-tier.
- Verdict: waning (dormant since late 2023 despite being the best-designed Python
  authoring model found) [S017].

### py-ledart (TkkrLab) [S018]

Dead. GPL-2.0; last substantive commit 2018-04-22 (master HEAD
`8556e8137550619045d2b3589b082e1f9276cbd6`), repo pushed-at 2023-10 is metadata only;
16 stars [S018]. Hackerspace matrix-art toolkit, no dithering/16-bit/interp claims.
Not a competitor; at most minor prior art. Verdict: waning (dead).

### BiblioPixel (ManiacalLabs) — the historical answer [S030]

The brief's candidate list missed the most important historical datapoint:
BiblioPixel was THE general-purpose pure-Python LED animation framework
(1D/2D/3D/circular layouts, many drivers via serial/network, animation class
library), MIT, 265 stars — and it died: last commit 2020-10-15 (master HEAD
`afb993fbbe56e75e7c98f252df402b0f3e83bb6e`) [S030]. Its death without a successor is
itself evidence for the gap: the Python community's previous "dominant engine" slot
has been vacant since ~2020 [S030].

### led-control (jackw01) [S017]
<!-- TODO -->

### LedFx [S011] — the partial answer

The one large, alive Python engine. GPL-3.0, 1,984 stars, v2.1.9 released
2026-05-18, commits daily through 2026-07-03 (main HEAD
`566de0fb6d32231022d7efa7684298f3af615792` at research time) [S011]. All code
observations below are against that HEAD.

- **Pattern-authoring model**: effects are Python classes registered into the app
  (numpy float arrays + gaussian blur/HSV helpers in
  `ledfx/effects/__init__.py`); there is NO user-facing live pattern-authoring
  surface — users select and parameterize built-in effects via web UI; writing a new
  effect means contributing to the codebase [S011]. Framing is explicitly
  audio-reactive-first ("network based LED effect engine designed to deliver
  advanced real-time audio effects") [S011].
- **Output quality**: internal math in float, but every device flush quantizes with
  a bare `astype(np.uint8)` — e.g. `ledfx/devices/ddp.py` line ~137 (`byteData =
  memoryview(data.astype(np.uint8).ravel())`) [S011]. So: 8-bit wire output even
  over DDP (whose spec supports 16-bit [S150]), no temporal dithering, no
  error-diffusion at quantization. It DOES have effect-to-effect transitions
  (`ledfx/transitions.py`, configurable `transition_time`/`transition_mode` per
  virtual) and spatial `interpolate_pixels` for virtual-to-device size mapping, plus
  per-virtual configurable refresh rate [S011].
- **Protocols**: the widest of any candidate — DDP, E1.31/sACN, Art-Net, UDP/WLED
  realtime, OpenPixelControl, OpenRGB, Adalight serial, plus consumer ecosystems
  (Govee, Hue, LIFX, Nanoleaf, Twinkly, Launchpad, Zengge) per `ledfx/devices/`
  module listing [S011].
- **Maintenance/adoption**: very active; ~2k stars; the de-facto answer when
  Reddit/HN threads ask for host-side LED software with audio (see gap analysis).
- **Form factor**: desktop/Pi host feeding network receivers (portable/room); not
  wearable.
- Verdict: stable-to-ascendant as an audio-reactive *app*; NOT a general pattern
  engine — no authoring model, 8-bit clamped output, engine internals coupled to
  the application [S011].

### py-ledart (TkkrLab) [S018]
<!-- TODO -->

### Other Python candidates found in sweep

None qualify as pattern engines:

- **WLEDVideoSync** (zak-45, MIT, created 2024-04, active through 2026-06, 64
  stars): casts video/screen/camera to 2D matrices over E1.31/Art-Net/DDP — a
  content *player*, no pattern authoring [S033].
- **luma.led_matrix** (539 stars, active 2026): Pillow-canvas *driver* library for
  MAX7219/NeoPixel — drawing surface, not an engine (sweep observation, repo
  description).
- **Adafruit CircuitPython LED Animation** [S401]: canned-animation class library
  for the wearable tier; no shader-style authoring, no network protocols, no HD
  output.
- **Piano-LED-Visualizer** (743 stars, active 2026) and the scoreboard family
  (nhl-led-scoreboard 439 stars, etc.): single-purpose apps — they demonstrate
  sustained *demand* for Python-on-Pi LED software without any shared engine
  underneath (sweep observation).
- **Protocol building blocks are alive but engine-less**: PyPI has actively
  released transport libraries — `sacn` 1.11.0 (2025-02-18) [S037], `pyartnet` 2.0
  (2025-11-04) [S038], `stupidArtnet` 1.6.0 (2025-03-12) [S039] — but NO
  general-purpose DDP library (LedFx [S011] and WLEDVideoSync [S033] each implement
  DDP privately), and `led-control` was never even published to PyPI [S017].
  The Python ecosystem has bricks, no house.

### Non-Python engines emerged/advanced 2024–2026

- **HyperHDR "Infinite Color Engine"** (C++, MIT, 2,021 stars, very active): the
  single most important competitive development found. v22beta1 (2026-01-06)
  rebuilt the color pipeline on high-precision floating point in linear sRGB,
  with deep-color output beyond 24-bit to Hue/LIFX and **HD108 16-bit LEDs**;
  v22beta2 (2026-05-08) added **adaptive temporal dithering** for RGBW drivers
  [S031][S032]. It is scoped to ambient/screen-capture lighting, not pattern
  authoring — but it proves out, in shipping code, the exact float-pipeline +
  dithering + 16-bit output stack pewpew wants. Prime code-reading target.
- **Chromatik / LX** (Java, heronarts): LX Studio's successor, "Digital Lighting
  Workstation" with DAW-style UI; 3D-model-first procedural animation; outputs
  Art-Net, sACN, OPC, DDP, KiNet with RGBW [S034][S035]. Active: Chromatik 1.2.1
  released 2025-11-19; LX core pushed 2026-06 [S034][S035]. License is
  non-commercial-capped (custom "LX Studio Software License", $25K annual revenue
  limit for commercial use), not OSI open source [S035]. The strongest *pattern
  engine* competitor overall — but Java, desktop-workstation-shaped, and
  license-encumbered.
- **MoonLight** (C++, ESP32): new ground-up embedded engine claiming 12K LEDs @
  100 fps on S3/P4 [S006] — competes at the firmware tier, complements a host
  engine.
- **ChimeraFX** (C++, ESPHome, created 2026-02, 3 stars): declarative-YAML
  event-driven effects for ESP32/ESPHome [S036]. Too small to matter yet;
  worth a periodic re-check as the Home-Assistant-native approach.
- **Rust sweep: nothing.** Topic `led` + Rust yields peripheral controllers
  (eruption, 301 stars, RGB keyboards) and toys; WLED-adjacent Rust projects are
  all <35 stars (wled-json-api-library 34, rusty_lights audio visualizer 3,
  audiophore bridge 3). No serious Rust pattern engine exists as of 2026-07
  (sweep observation, 2026-07-03).

### Adoption/mindshare evidence (HN/Reddit)

The largest HN WLED thread ("WLED Project", 2022-12-23, 232 points, 82 comments)
mentions Pixelblaze 9 times and contains ZERO mentions of Python, LedFx,
BiblioPixel, led-control, or Fadecandy [S040]. Web searches for
Python-engine alternatives to WLED/Pixelblaze surface only WLED, Pixelblaze,
FastLED, and LEDLab [S020]. When hobbyists want host-side software the answer
given is LedFx (audio) or xLights (sequencing); nobody names a Python
*pattern-authoring* engine because none exists to name.

### Gap analysis & conclusion

**The gap is real, with one asterisk.** Adversarial sweeps across GitHub topics,
PyPI, Rust/Go/C++ spaces, and HN/Reddit found no actively maintained,
general-purpose, Python-native LED pattern engine in 2026:

- The best authoring model in Python (led-control: live-edited per-pixel shader
  functions over x/y/z) is dormant since 2023-11 [S017].
- The historical framework slot-holder (BiblioPixel) died in 2020, unreplaced [S030].
- The one thriving Python project (LedFx) is an audio-reactive *application*:
  no user pattern authoring, 8-bit `astype(np.uint8)` output even on DDP,
  no dithering [S011].
- The asterisk: LedFx owns the "Python + LEDs" mindshare and the audio niche;
  pewpew should not try to out-LedFx LedFx on audio-reactive club lighting.

**What pewpew must do that nothing else does** (union of features no single
system has):
1. Live, user-facing pattern authoring in Python (led-control's model [S017],
   Pixelblaze's ergonomics [S200]) — not a fixed effect catalog.
2. High-fidelity output pipeline: float/16-bit internal color, temporal
   dithering, gamma-correct quantization — currently proven only in C++
   (HyperHDR ICE [S031][S032], FastLED APA102HD [S051], Fadecandy [S015]) and
   never available in any Python engine.
3. 16-bit-capable transports end-to-end: DDP's 16-bit wire format [S150] is
   unexploited by every Python system found (LedFx sends uint8 over DDP [S011]).
4. Genuinely open license (vs Chromatik's revenue-capped license [S035]) and
   pip-installable engine-as-library (vs LedFx's app coupling; led-control's
   absence from PyPI).

## Verdicts

- **led-control** — waning: dormant since 2023-11, never on PyPI [S017].
- **py-ledart** — waning (dead since 2018) [S018].
- **BiblioPixel** — waning (dead since 2020) [S030].
- **LedFx** — stable/ascendant as an audio-reactive app (v2.1.9 2026-05, daily
  commits) but structurally not a pattern engine [S011].
- **HyperHDR** — ascendant: ICE float pipeline + adaptive dithering landed
  2026, very active [S031][S032]. Different scope (ambient), key prior art.
- **Chromatik/LX** — stable: active releases (1.2.1, 2025-11) with small
  community (22/56 stars); license limits reuse [S034][S035].
- **Python engine niche itself** — vacant since ~2020; demand persists
  (Piano-LED-Visualizer-class apps keep being built one-off).

## Code-reading queue

1. **HyperHDR** (awawa-dev/HyperHDR) — Infinite Color Engine: float linear-sRGB
   pipeline, adaptive temporal dithering (PRs #1261, #1483, #1490), HD108
   deep-color output. Question: what does a shipping float→dithered-LED
   quantizer look like, and what stability tricks avoid static-scene flicker?
   [S031][S032]
2. **led-control** (jackw01/led-control @ 8e3fe1d) — `ledcontrol/animationfunctions`
   + C extension: how the per-pixel Python-shader model and perceptual HSV are
   structured, and where its performance ceiling comes from. Question: what to
   copy/avoid in pewpew's authoring API. [S017]
3. **LedFx** (LedFx/LedFx @ 566de0f) — `ledfx/virtuals.py`, `ledfx/transitions.py`,
   `ledfx/devices/ddp.py`: virtual/segment abstraction and transition engine;
   confirm nothing beyond uint8 anywhere in the flush path. Question: is there
   any 16-bit hook worth upstream-contributing vs building fresh? [S011]
4. **LX core** (heronarts/LX) — model/geometry + modulation architecture (read
   for design, not reuse — license [S035]). Question: what a decade-refined
   3D-first pattern API looks like. [S035]
5. **BiblioPixel** (@ afb993f) — post-mortem read: layout/driver abstraction,
   and why maintenance collapsed (issue tracker). Question: which
   framework-shape mistakes to avoid. [S030]

## Open questions

- led-control's exact output path (does it do any gamma/dither before the
  ws281x driver?) — settle by code read (queue #2). Currently
  [S017][NEEDS-VERIFICATION].
- Reddit coverage was via web search only (API-less); a direct sweep of
  r/WLED, r/FastLED, r/led 2024–2026 for "python engine" asks would harden the
  mindshare claim [S040 covers HN only].
- Is anything brewing in LedFx toward user pattern authoring (their GitHub
  discussions/Discord)? A roadmap item there would shrink pewpew's moat —
  settle with a forum ask or discussions search.
- ProjectMM/MoonLight trajectory [S006][NEEDS-VERIFICATION] — covered by RA-01
  main; affects whether pewpew's receiver tier can assume a WLED-class DDP
  endpoint at 16-bit someday.
- Go ecosystem was only lightly swept (no topic search run); low prior of a
  hidden engine there, but unconfirmed.
