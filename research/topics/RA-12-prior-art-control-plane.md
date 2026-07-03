# RA-12: Prior-art gallery & control plane

Last researched: 2026-07-03
Status: draft
S-ID block: S550–S599

## Key questions

- (A) Which documented LED-art installations/artists carry transferable technique or taste lessons, and where exactly is each lesson written down (talk, repo, blog)?
- (B) What do the WLED and Pixelblaze control APIs actually look like (JSON/WebSocket), and what do OSC/MIDI/Home Assistant practice and presets/playlists/schedules models teach?
- What control surface should a Python LED engine expose?

## Findings

### A. Prior-art gallery

#### Micah Elizabeth Scott (scanlime)

Documented lesson: treat cheap LEDs as a *display medium* and fix their quality problems in the controller — Fadecandy's docs specify temporal dithering, keyframe interpolation between frames, and gamma/color correction as firmware features so "quality is not the artist's problem," plus Open Pixel Control as the deliberately simple host protocol [S016][S062]. This is the intellectual ancestor of every "HDR LED" feature since (FastLED APA102HD, Pixelblaze HDR drivers, NeoPXL8HDR — see RA-02) [S051][S014][S064]. The original repo was deleted by the author (~2021); the pixelmatix fork mirrors the code and docs [S015][S027][S062]. Where: Fadecandy README + `doc/` in the mirrored repo [S062].

- Maintenance: abandoned upstream (deleted); mirrors static — waning as software, foundational as documentation [S015][S027].

#### Ben Hencke (Pixelblaze installations)

Documented lessons, all first-party: (1) pattern-as-math with exported variables and web-based live editing as the whole authoring workflow (Pixelblaze docs and expression reference) [S200][S201]; (2) engineering render speed for *artistic* headroom — POV spinning props demand kHz-class frame rates, documented in the V3 Crowd Supply updates [S203]; (3) his 2023–2024 "pixel stack" rewrite thread documents moving to higher-precision internal color and perceptual handling, with concrete before/after reasoning [S063]; (4) the Sensor Expansion Board writeups document treating sound/accelerometer input as first-class pattern variables rather than a bolt-on [S204]. Where: bhencke.com blog + electromage.com docs + leds.social thread [S200][S063][S203][S204].

- Maintenance: active (v3.x releases through 2025) [S014].

#### Christopher Schardt (LED ceiling art, APA102 16-bit advocacy)

Schardt (Firmament, Nova; LED Lab author) is the documented case for APA102-class chips in fine art. His concrete technique contribution is in code: his 2017 PR to hzeller/spixels implements APA102 output that "calculat[es] 5-bit dimming for each 48-bit pixel value" — i.e. per-pixel use of the APA102 brightness field to extend effective dynamic range, plus SK9822 compensation "for the fact that 5-bit dimming the SK9822 doesn't dim the LEDs as much and makes them bluer/greener" [S557]. That is the same technique FastLED later shipped as APA102HD [S051][S052]. Firmament itself: a 52-ft canopy of 21,000+ LEDs, patterns composed to classical music — documented taste lesson that slow, high-bit-depth overhead imagery paired with curated music reads as fine art, not decoration [S559]. His trajectory ("engineer who did art → artist who used engineering") and art-first framing are documented in a Burning Man Journal interview [S558]. His LED Lab iOS app carries the same Raspberry-Pi + SPI-LED stack to other artists [S312][S559].

- Maintenance: practice active (BLINK Cincinnati 2026 listing) [S559][NEEDS-VERIFICATION].

#### Jason Coon / Evil Genius Labs (Fibonacci, polar mapping)

Documented lessons on evilgeniuslabs.org product/technique pages: Fibonacci128 arranges 128 LEDs in a Fermat's-spiral (golden-angle) layout; the physical wiring zig-zags center→edge→center, so *all* pattern work happens through pixel maps — an XY matrix map for raster effects and "a 2D polar (radius and angle) map [that] can allow you to easily make patterns that rotate clockwise or counterclockwise, expand, or contract" [S560]. This is the cleanest documented demonstration that map choice (Cartesian vs polar) is a creative primitive, not plumbing — the same geometry ships with ready-made maps for Pixelblaze's mapper and for his open-source FastLED webserver firmware (jasoncoon/esp8266-fastled-webserver, MIT) [S560][S304]. Form factor: desk-scale boards to wall pieces.

- Maintenance: active store/firmware as of 2025–2026 [S560][NEEDS-VERIFICATION on latest firmware release date].

#### GeekMomProjects (Debra Ansell)

Documented lessons: (1) **LEDs/PCBs as structure** — her Hackaday Remoticon 2021 talk (written up by Hackaday, 2022-01-20) documents techniques for joining PCBs mechanically and electrically so the circuit boards *are* the sculpture/wearable body [S561]; (2) **CircuitPython as an LED-art medium** — her PyCascades 2021 talk "Sparking Creativity in LED Art with CircuitPython" documents prototyping speed vs performance trade-offs for NeoPixel wearables [S561]. Where: hackaday.com writeup + talk video; geekmomprojects.com project posts.

#### Erin St Blaine

Documented lessons live in the Adafruit Learning System, where she is a staff author: the guide "Make It Glow: NeoPixel and LED Diffusion Tips & Tricks" is a rare *written-down* treatment of diffusion materials and spacing — the single biggest taste factor separating "LED project" from "light art" [S562]. Her FastLED-based guides (LED Campfire, Ever-Burning Flame Painting, NeoPixel Holiday Lights) consistently teach gradient-palette-driven design (`fire_gp` etc.) rather than raw RGB — palettes as the unit of visual taste [S562]. Form factor: costumes/wearables and home pieces.

#### Titanic's End (LXStudio-TE)

The largest documented open LED-art codebase: "This repo contains the shader and pattern code for the 128,000 LEDS, sound reactivity, MIDI control, OSC middleware, and ArtNet bidirectional control," self-described as "the largest team developing on Chromatik in the open, so other artists can benefit from our work" [S563]. Documented lessons: GLSL shaders as the pattern-authoring substrate on a sparse 3D model; **AutoVJ**, "an autopilot that uses Pioneer Rekordbox's phrase and beat analysis to change patterns when a human VJ would"; explicit team-maintainability standards (google-java-format, onboarding README, public design doc); and GigglePixel/Pixelblaze/ArtNet interop [S563]. Where: github.com/titanicsend/LXStudio-TE README + linked 2022 Lighting Design Doc [S563].

- License: custom LICENSE.md (GitHub reports NOASSERTION — not OSI standard; reuse requires reading it) [S563].
- Maintenance: active, pushed 2026-04-18 [S563].
- Form factor: room/vehicle scale on desktop JVM (Chromatik).

#### Squared (Charles Gadeken)

Squared / 2SQUARED (Coachella 2014, Burning Man): two 50-ft steel trees each carrying 768 polyurethane LED cubes in fractal arrangement; the artist's page documents the *interaction* lesson — two participant interfaces, an iPad app and a physical RFID-tag table, driving the visuals — i.e. installation-scale pieces need audience-facing control surfaces distinct from the artist's [S564]. Gadeken's cube lineage (Sugar Cubes 2013, with Symmetry Labs software) is the project family from which Mark Slee's LX engine emerged, making it the ancestor installation of the whole Chromatik ecosystem [S564][S035][NEEDS-VERIFICATION on exact SugarCubes→LX lineage claim].

#### Chromance (Zack Freedman)

A wall sculpture of hexagon edges (rhombic network) run by an ESP32; fully documented as a kit: repo (MIT) with firmware, BOM, STLs, and step-by-step Dozuki assembly guide, plus a build video [S565]. Documented lessons: (1) mapping a *graph* topology (nodes/edges) rather than a strip or matrix — the firmware routes "ripple" animations along the network's edges and junctions, an early popular example of topology-aware animation; (2) an ambient/default behavior (auto ripple effect) when the intended biometric input (EmotiBit) is absent [S565]. Community WLED ledmap ports of the same geometry exist, showing the mapping outliving the original firmware [S565].

- Maintenance: repo dormant since 2023-02-02 — waning as code, useful as documentation [S565].

#### Flaming Lotus Girls (FLG)

FLG's documented LED work is *Soma* (2009): two 25-ft neurons, originally fire-centric, retrofitted with "over 60 custom LED packages, each ... individually controllable" for long-term public display (Pier 14 SF, then Vallejo), with two public buttons triggering pattern sequences along the arch [S566]. The documented lessons are institutional rather than algorithmic: retrofit from fire to LEDs for permanence/permitting, and dead-simple public interaction (buttons). No code-level or technique writeup was found — noted in Open questions [S566].

### B. Control plane

#### WLED JSON + WebSocket API

WLED exposes its whole runtime state as one JSON document over HTTP (`/json`, with sub-paths `/json/state`, `/json/info`, `/json/eff`, `/json/pal`, `/json/fxdata`, `/json/live`): GET reads it, POST of a partial object mutates it — e.g. `{"on":"t","bri":128}` [S550]. Key state fields: `on` (bool or `"t"` toggle), `bri` 0–255, `transition` (crossfade in 100 ms units), `ps` (apply preset), `pl` (playlist), `nl` (nightlight timer object), `udpn` (sync send/receive), `live`, and a `seg` array [S550]. Each segment carries `id/start/stop`, `fx` (effect id — accepts relative notation `~`, `~-`, or `"r"` random), `sx` speed, `ix` intensity, up to 3 `col` slots (RGB arrays or hex strings), `pal`, per-segment `on/bri`, `rev/mi`, `cct` (0–255 relative or Kelvin), and `i` for direct per-LED writes (non-persistent, buffer-limited: ~10 KB command on ESP8266, 24 KB on ESP32) [S550]. Effects self-describe via `/json/fxdata` metadata strings (`<sliders>;<colors>;<palette>;<flags>;<defaults>`, flags `1`=1D `2`=2D `v`/`f`=audio) so generic UIs can render controls without hardcoding — the same mechanism cataloged in RA-05 [S550][S206].

The WebSocket at `/ws` (default since 0.10.2) is deliberately thin: clients send the *same* JSON state objects as HTTP POST; the server pushes the merged state+info document (`/json/si` equivalent) to all clients on any state change, so every UI stays in sync for free [S551]. `{"v":true}` requests a full state dump; `{"lv":true}` subscribes to a live per-LED preview stream ("Peek") which is exclusive to one client at a time; max 4 concurrent WS clients (2 recommended on ESP8266) [S551]. Architectural lesson: **one canonical JSON state document, mutable by partial merge over both HTTP and WS, with server-push fan-out of the merged result** — the WS layer adds no second vocabulary. This is why dozens of third-party apps/integrations could target WLED cheaply.

- License: EUPL-1.2 (WLED core) [S001]; docs page CC-hosted at kno.wled.ge [S550].
- Maintenance: active, 0.16.x cycle in 2025–2026 [S002].
- Form factor: the API model itself is transport-light and applies from wearable to room scale.

#### Pixelblaze WebSocket API

Pixelblaze's entire control surface — the stock web UI included — is a WebSocket on port 81 mixing JSON text frames and typed binary frames [S200][S552]. JSON commands (exact keys, from the pixelblaze-client implementation): `{"ping":true}`, `{"getConfig":true}`, `{"listPrograms":true}`, `{"activeProgramId":"<id>"}`, `{"brightness":<0.0–1.0>}`, `{"setVars":{...}}`, `{"getVars":true}`, `{"setControls":{...}}`, `{"getControls":"<id>"}`, `{"sequencerMode":<0|1|2>}` (Off/ShuffleAll/Playlist), `{"runSequencer":<bool>}`, `{"sequenceTimer":<ms>}`, `{"nextProgram":true}`, `{"deleteProgram":"<id>"}` [S552:pixelblaze/pixelblaze.py]. A near-universal `"save":true|false` flag on mutating commands chooses flash persistence vs RAM-only (default RAM) — a clean solution to the "live tweak vs committed setting" problem [S552]. Binary frames use a type byte: 1=putSourceCode, 3=putByteCode, 4=previewImage (JPEG), 5=previewFrame (rendered RGB pushed to client), 6=getSourceCode, 7=getProgramList (tab-separated `id\tname` lines), 8=putPixelMap, 9=ExpanderConfig, with first/middle/last continuation flags in byte 2 [S552].

The distinctive idea vs WLED: **patterns export named variables, and `setVars`/`getVars` gives every external controller typed live access to them** — the pattern author defines the control surface simply by exporting variables and declaring UI controls, and the same mechanism serves the built-in UI, Python clients, and MQTT bridges [S200][S552]. zranger1/pixelblaze-client (MIT, v1.1.7 released 2025-12-03, pushed 2025-12-20 — maintained) is the de-facto Python protocol reference since ElectroMage's own WS doc page is a JS app that resists scraping [S552].

- License: firmware proprietary; protocol publicly documented [S200]; client MIT [S552].
- Maintenance: Pixelblaze active (v3.x HDR drivers 2025) [S014]; client active as of 2025-12 [S552].
- Form factor: designed for single-controller art pieces (wearable→installation); one WS per device, no fleet abstraction (Firestorm/Flamecaster add that layer externally).

#### OSC and MIDI in light-art practice

Chromatik/LX (the engine behind Titanic's End and much large-scale LED art) is the best-documented model. OSC: "nearly every parameter" is addressable under a hierarchical `/lx/...` scheme (e.g. `/lx/mixer/channel/1`, `/lx/tempo/bpm`); continuous parameters are float32 **normalized 0–1**, discrete ints raw int32, booleans int32 0/1; the UI shows each control's OSC address on hover; separate UDP RX/TX ports with per-I/O address-prefix filters; and it implements **OSCQuery** (zeroconf-advertised HTTP service) for automatic address discovery, plus a nonstandard `/osc-query` suffix that dumps all descendant parameters [S555]. Tempo is first-class OSC: `/lx/tempo/beat` advances/sets the beat counter (1-indexed) so an external clock can drive the engine [S555].

MIDI: LX distinguishes (a) **control surfaces** — APC40 mkII, APCmini/mk2, Midi Fighter Twister, Pioneer DJM mixers — that map to the mixer/pattern model with zero configuration; (b) **generic MIDI mapping** — a learn mode (click parameter, wiggle knob) whose mappings are event-based, not device-specific, so hardware can be swapped; and (c) **MIDI into patterns** — note/CC/pitchbend/aftertouch routed to any pattern that opts in, with channel/note/velocity filters — plus MIDI Beat Clock tempo sync [S556]. The composite lesson: expose *one parameter tree*, then OSC addresses, MIDI mappings, and control surfaces are all just bindings onto it; and make tempo/beat an externally drivable parameter rather than an internal detail [S555][S556].

- License: LX core LGPL with special-use terms per heronarts (see [S035]); Chromatik app free.
- Maintenance: active, 2025–2026 releases [S034].
- Form factor: desktop JVM — room/installation scale; the parameter-tree + OSCQuery *pattern* transfers to any engine.

#### Home Assistant integration patterns

The HA WLED integration is the reference for how a smart-home hub wants to see an LED engine: auto-discovery (mDNS/zeroconf), then a mapping of engine concepts to standard entity types — each segment becomes a `light` entity (plus a master light for whole-strip power/brightness), presets/playlists/palettes become `select` entities, effect speed/intensity become `number` entities, nightlight/sync/reverse become `switch`es, restart a `button`, plus diagnostic sensors and a firmware `update` entity [S553]. Transport: it prefers the WebSocket for local push and "automatically falls back to polling ... every 10 seconds" if WS is unavailable; classified "Local Push" [S553]. Lessons for a Python engine: (1) advertise via mDNS so discovery is zero-config; (2) push state changes rather than making hubs poll; (3) name-addressable presets/playlists and enumerable effects/palettes are what turn an engine into `select` dropdowns — an integration can only expose what the API can enumerate [S553][S550].

Pixelblaze has no official HA integration; community bridges go through MQTT (e.g. NickWaterton's Pixelblaze-Async MQTT interface), which is the usual fallback pattern when a device speaks only a bespoke WS protocol [S552][NEEDS-VERIFICATION on current HA-Pixelblaze options].

#### Presets / playlists / schedules models

**WLED model.** A preset is a saved JSON state (or an arbitrary API command string), stored in `/presets.json` on the device FS, ≤250 slots, applied by id via `{"ps":N}`; presets optionally capture brightness and segment bounds (`ib`/`sb` flags on `psave`) [S550][S554]. A playlist is itself stored in a preset: `{"playlist":{"ps":[...],"dur":[...],"transition":N,"repeat":N,"end":N}}` — durations in 0.1 s units, `repeat:0` = infinite, `end` = preset to land on when done [S550]. Scheduling is built in but minimal: 8 timer slots (24 h clock) plus sunrise/sunset triggers with location, each firing a preset; a designated boot preset restores state at power-on [S554]. Practical limits are honest in the docs: preset apply <0.1 s but editing blocks on LittleFS writes; ~50 simple presets recommended [S554]. Key design point: **presets replaced a separate "macro" system by making a preset = any API command** — one abstraction covers scenes, commands, and playlists [S554].

**Pixelblaze model.** No JSON-scene concept; instead the sequencer has three modes — Off / ShuffleAll (auto-advance every `sequenceTimer` ms) / Playlist (ordered pattern ids with per-item durations) — driven over the same WS commands, with `save` deciding persistence [S552][S200]. Per-pattern UI-control values can be saved per pattern (`setControls` + `save`), so a "preset" is effectively (pattern id + its saved control state) [S552].

**FPP model (show-scale reference).** Falcon Player is built around a scheduler as a first-class subsystem: playlists of sequences/media with lead-in/lead-out, calendar/day-of-week schedules, and priority rules — the standard for whole-show automation in the xLights ecosystem [S022][NEEDS-VERIFICATION for current FPP 9.x scheduler details]. The gradient across the three is instructive: Pixelblaze = per-device shuffle, WLED = scenes+playlists+8 timers, FPP = full calendar scheduling. A Python engine should sit at the WLED point and leave calendars to Home Assistant/cron [S553].

### Recommendation: control surface for a Python engine

Synthesis of the three proven designs (WLED, Pixelblaze, LX):

1. **One canonical state/parameter tree** as the single source of truth. WLED proves the value of a single JSON state document mutable by partial merge [S550]; LX proves the value of making *every* parameter addressable in a hierarchy with normalized 0–1 floats [S555]. A Python engine should model engine + patterns + per-pattern parameters as one tree with stable paths.
2. **HTTP JSON for request/response, WebSocket for the same vocabulary plus push.** WLED's WS carries identical JSON to HTTP and broadcasts merged state on change, which keeps every client UI consistent for free and made the third-party ecosystem cheap to build [S550][S551]. Do not invent a second WS-only vocabulary.
3. **Pattern-exported variables as the extensibility mechanism.** Pixelblaze's `setVars`/`getVars` + declared UI controls let a pattern define its own control surface once, consumed identically by the built-in UI and external clients [S552][S200]. In Python this is "pattern declares typed parameters; engine mounts them into the tree."
4. **A `save` flag separating live tweaks from persisted state** (Pixelblaze) [S552], plus WLED-style named presets (preset = any API command / partial state) and playlist-as-data `{ps,dur,repeat,end}` [S550][S554]. Keep scheduling minimal (boot preset + a few timers at most) and delegate calendars to Home Assistant [S553][S554].
5. **Discovery + hub-friendliness:** mDNS/zeroconf advertisement and push-on-change are exactly what makes the HA integration "Local Push" grade [S553]; OSCQuery is the same idea for the OSC world [S555].
6. **OSC in (normalized floats, `/engine/...` paths mirroring the tree) and MIDI-learn mapping onto the same tree**, with beat/tempo as an externally settable parameter — straight from LX practice [S555][S556].
7. **Live preview as an opt-in exclusive stream** (WLED `{"lv":true}` peek; Pixelblaze binary previewFrame type 5) rather than always-on broadcast [S551][S552].

Net: HTTP+WS JSON core (WLED-shaped), Pixelblaze-style pattern variables and save-flag, LX-style full parameter tree with OSC/MIDI bindings layered on top. MQTT can be a thin optional bridge, not the core.

## Verdicts

- **WLED JSON+WS API model** — ascendant/stable: active 0.16 cycle, the de-facto target for third-party apps and HA "Local Push" integration [S002][S550][S553].
- **Pixelblaze WS protocol** — stable: device active (2025 releases), protocol unchanged for years, single-device scope [S014][S552].
- **Chromatik/LX parameter tree + OSC/OSCQuery/MIDI** — ascendant at installation scale: active releases, adopted by the biggest open art codebase (TE) [S034][S555][S563].
- **Fadecandy** — waning as software, foundational as documentation (upstream deleted ~2021) [S015][S027].
- **Chromance firmware** — waning (dormant since 2023-02); its graph-mapping idea lives on in ports [S565].
- **OPC (Open Pixel Control)** — waning with Fadecandy but still an LX-supported output; simplicity keeps it alive as a lowest-common-denominator [S016][S035].
- **MQTT-bridge pattern for HA** — stable fallback where no native integration exists [S552][S553].

## Code-reading queue

1. **zranger1/pixelblaze-client** (`pixelblaze/pixelblaze.py`, pinned @9be8470) — full enumeration of Pixelblaze WS commands, binary framing, and reconnect handling; answers "what does a complete client of a variable-export control model need?" [S552]
2. **WLED core** (`wled00/json.cpp`, `ws.cpp`, `presets.cpp` in Aircoookie/WLED) — how partial-JSON merge, state broadcast, and preset/playlist storage are implemented; answers "what does one-canonical-state cost in code, and where are its edge cases?" [S001][S550]
3. **titanicsend/LXStudio-TE** (`te-app` pattern classes + AutoVJ package, pinned @8639264) — how a large team structures shader patterns, OSC middleware, and a beat-analysis autopilot on LX; answers "what conventions keep 100+ patterns maintainable?" [S563]
4. **heronarts/LX** (`heronarts/lx/osc/`, `heronarts/lx/midi/surface/`) — parameter tree ↔ OSC address binding and the APC40 surface implementation; answers "how to bind OSC/MIDI to a parameter tree generically?" [S035][S555][S556]
5. **hzeller/spixels PR #1 + FastLED five_bit_hd_gamma** — compare Schardt's per-pixel 5-bit dimming to FastLED's APA102HD; answers "which HD algorithm should a Python engine port?" [S557][S051]
6. **ZackFreedman/Chromance** (firmware ripple logic, pinned @1cefefb) — minimal graph-topology animation routing; answers "what data structure suffices for node/edge maps?" [S565]

## Open questions

- Pixelblaze's official WebSocket doc page (electromage.com/docs/websockets-api) is a JS SPA that could not be scraped; protocol details here come from the MIT client implementation [S552]. A manual browser read (or ElectroMage forum thread) would confirm completeness, esp. any v3.5x additions.
- FPP 9.x scheduler specifics (priority rules, lead-in/out) were not re-verified this pass; needs a read of the FPP manual before citing in an ADR [S022][NEEDS-VERIFICATION].
- Current best path for Pixelblaze↔Home Assistant (native vs MQTT bridge) unverified; check HACS listings.
- Exact SugarCubes→LX lineage claim should be confirmed from the sugarcubes/SugarCubes repo README or Mark Slee interview before use in an ADR [S564][NEEDS-VERIFICATION].
- FLG has no published code/technique docs for Soma's LED system; only institutional lessons are citable [S566].
- LXStudio-TE's custom LICENSE.md terms (reuse constraints) need a direct read before any code is ported [S563].
- Schardt's 16-bit advocacy beyond the spixels PR (e.g. HD108 posts, talks) not located this pass; his LED Lab release notes may document it [S312][S557].
