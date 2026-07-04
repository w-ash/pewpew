# RA-11: Simulation, preview & dev ergonomics

Last researched: 2026-07-03
Status: draft
S-ID block: S500–S549

## Key questions

- How does fastled-wasm work and what iteration speed does it achieve? [S500][S501]
- What makes the Pixelblaze live editor's instant-feedback loop work, and why do users love it? [S200][S013]
- What do xLights preview [S021], LedFx virtual preview [S011], and WLED simulators offer?
- What web 3D previewers (three.js point clouds) and Python terminal/pygame previewers exist?
- Does anyone test LED effects (golden-frame, perceptual diff)?
- How is hot-reload done in Python pattern dev (watchfiles, livecoding culture)?
- What preview/iteration stack should pewpew build first?

## Findings

### fastled-wasm — browser-compiled FastLED sketches

- **What it is.** A compiler toolchain (`pip install fastled`) that transpiles an Arduino/FastLED C++ sketch to HTML/JS/WASM via Emscripten and runs it in the browser against virtual LEDs [S500][S501]. The GitHub tagline is "The FastLED web compiler. Lightning fast 3 second compile and 1 second deploy on fast machines." [S500].
- **Iteration speed.** Cold compile ~3 s; incremental sketch-only edits recompile "in under a second" thanks to "aggressive object caching and sketch fingerprinting"; header changes take longer [S500][S501]. This is the current speed benchmark for LED dev loops on the C++ side.
- **Hot reload.** File watching triggers automatic recompilation; the browser reloads and build output is streamed to the browser in real time via Server-Sent Events. `--fastled-path` extends watching to the FastLED library sources themselves [S500].
- **Preview model.** Sketches can ship a "screenmap" (per-LED coordinates) so the browser renders the actual physical layout, not just a strip; FastLED's `examples/WasmScreenCoords` demonstrates the API [S500][S503]. An `--app` flag gives an app-like browser window; Playwright is bundled for automated browser control [S500].
- **Ergonomics extras.** Emulated SD card via a `/data` directory + `files.json` manifest; quick/release/debug compile modes; bundled localhost HTTPS certs so browser mic access works (audio-reactive sketches testable in-browser) [S501].
- **Maintenance.** Very active: v2.0.13 released 2026-06-12, 191 releases, ~1,700 commits, CI across Linux/Windows/macOS x86+ARM [S500][S501]. License: repo says MIT, PyPI metadata says BSD-3-Clause — conflicting [S500][S501][NEEDS-VERIFICATION] (re-checked 2026-07-03: still conflicting — GitHub API license MIT, repo pushed 2026-06-25; PyPI `fastled` license field "BSD 3-Clause License", latest 2.0.13; needs an upstream issue to settle before any code reuse).
- **Distinct project, same name:** jandelgado/fastled-wasm is an unrelated earlier "FastLED for the Web" port with a live browser demo of virtual LEDs [S502]. Disambiguation matters when citing.
- **Form factor:** development-time tool only; applies to any target that runs FastLED. **Key lesson for pewpew:** even with a C++ compile in the loop, sub-second incremental rebuild + auto browser refresh is achievable; a Python engine should beat this trivially since it needs no compile step at all.

### Pixelblaze live editor

- **Instant-feedback design.** The web editor recompiles and pushes the pattern to the device on every edit: "Your pattern is recompiled and sent to Pixelblaze on every change so you can see your changes live" — "As long as your pattern is valid, it's live and running on Pixelblaze" [S504]. There is no compile-upload-flash cycle at all; the LEDs themselves are the preview surface, updating within a keystroke's latency [S504][S013].
- **Error handling.** "Inline syntax and runtime error highlighting"; "even run-time errors that would usually just crash your program are harmless and show up right in the editor" [S504]. The pattern VM sandboxes runtime faults (out-of-bounds, infinite loops) so a bad edit never crashes or bricks the device — errors surface as editor annotations while the last valid pattern keeps running [S504]. This crash-proof-by-construction property is arguably the single biggest reason the editor feels safe to experiment in.
- **Live variable watcher + auto UI.** The editor includes a "real-time compiler" and "variable watcher" (live inspection of exported pattern variables), and "adding UI controls to a pattern [is] as easy as writing a function" — declaring `sliderFoo()`/color-picker functions auto-generates UI controls [S504][S200].
- **Architecture.** Patterns are a JavaScript-like ES6 subset executed by a highly optimized expression engine on the ESP32; a WebSocket API carries editor↔device traffic and third-party control [S200][S013]. Community consensus and the maintainer's docs indicate the browser compiles source to a compact bytecode which is streamed to the on-device VM over the websocket, and the device streams preview pixel frames back to the editor's strip-preview widget — but electromage.com/docs is a JS SPA that WebFetch cannot render, so the compile-in-browser/bytecode detail could not be primary-source-verified this pass [S200][NEEDS-VERIFICATION].
- **Why users love it (synthesis).** (1) zero-latency feedback on real LEDs, (2) impossible to crash the device from pattern code, (3) UI controls for free, (4) live variable inspection. Together these make the *hardware* feel like a REPL [S504][S013].
- **Ecosystem note.** `pixelblaze-client` (MIT, v1.1.7 Dec 2025, maintained) drives the same websocket API from Python — evidence the live-control channel is stable enough to build tooling on [S505].
- **Maintenance/form factor.** Active product line (V3 Standard/Pico current, firmware releases through 2025+) [S013]; closed firmware. Applicability: the *pattern* of live-push-to-device + on-device sandbox VM applies to wearable and portable tiers; the editor concept applies everywhere.

### xLights preview

- **Model.** xLights is an *offline sequencer*: effects are rendered onto per-model rectangular "render buffers", composited, then previewed [S506][S021]. Preview is thus playback of pre-rendered frames, not a live engine — the opposite end of the spectrum from Pixelblaze.
- **House Preview.** A "House Preview" window plays the whole display over a photo of the actual house/venue; models are placed on a 2D background image or in a full 3D layout, and multiple named preview layouts can exist (e.g., different viewing angles, multiple houses) [S506]. Play/pause/scrub controls appear when the window is large enough [S506]. Placing pixels over a photograph of the real installation is xLights' signature ergonomics win: sequencers judge effects in situ before the display exists.
- **Iteration cost.** The workflow is drag effect → "Render All" → play; rendering large sequences is slow enough that the project maintains render caching, background shader compilation, GPU video decode, and a per-model render-progress dialog to diagnose slow models [S506][S507]. Community threads on render speed are common [S507]. Iteration latency is seconds-to-minutes, acceptable only because the artifact is a fixed show, not a live pattern.
- **Maintenance/license/form factor.** Actively developed (repo now at xLightsSequencer/xLights [S026]); GPLv3 wxWidgets desktop app. Room/house-scale displays; irrelevant to wearables. Lesson for pewpew: background-photo/3D *in-situ* preview is worth stealing; the offline render loop is not.

### LedFx browser frontend + virtual preview

- **Frontend.** LedFx "comes with a browser based front end for configuration, control and live visualisation" (default port 8888); the React frontend renders live pixel state streamed from the Python engine [S011][S012]. A "Preview Only" toggle previews an effect without updating real devices [S012].
- **Dummy devices.** A dummy device "will only render to the browser front end and is intended for testing" — the documented workflow for developing 2D effects and triaging audio response entirely without hardware [S508]. Users set pixel count and a `rows` value to make a matrix (e.g., 64x64 = 4096 px, "the current limit of the front end update pixel count"); a Frontend Pixels slider in Settings/UI throttles how many pixels the backend streams to the browser [S508].
- **Virtuals.** "Virtuals" remap segments of physical devices (any pixel ranges, any order) into one logical strip/matrix that carries the effect — a mapping layer that doubles as a preview target [S509].
- **Limits.** The preview is a flat strip/2D-matrix widget — no 3D spatial view; and the 4096-pixel frontend cap with a throttle slider shows websocket pixel-streaming to a browser has real bandwidth limits to design around [S508].
- **Maintenance/license/form factor.** Active (2.1.x, May 2026), GPL-3.0 [S011]. Runs on a host PC — portable/room-scale; the dummy-device pattern applies directly to pewpew's host-driven tier.

### LedFx browser frontend + virtual preview
<!-- TODO -->

### WLED simulators / PC builds

- **No official PC build.** Upstream WLED [S001] targets ESP32/ESP8266 via PlatformIO cross-compilation only; the official compiling docs describe no native x86/host build, and searches surfaced no upstream native-Linux target [S510]. WLED's effect-dev loop is therefore compile → flash → reboot device — tens of seconds per iteration at best, plus physical hardware in the loop.
- **Community workarounds:**
  - **wled-sim** (13rac1, Go/Fyne): a desktop app that "behaves like a real WLED node" — GUI LED matrix + WLED-compatible JSON REST API + DDP UDP listener — aimed at *client* development and automated integration tests, not at running WLED's own effect code [S511]. It emulates the API surface, not the firmware.
  - **Wokwi**: browser ESP32 simulator with community WLED "Effects Editor" projects — full-firmware simulation is possible but is an instruction-level emulator, so it runs well below real-time for heavy effect code [S512][NEEDS-VERIFICATION on exact real-time factor].
- **Takeaway.** Even the most popular LED firmware in the world has *no* first-party simulator; its enormous effect library was built despite a flash-cycle iteration loop, and third parties fill the gap only at the API layer [S510][S511]. This is a major ergonomics gap pewpew can exploit: a host-native Python engine is its own simulator for free.
- **Maintenance:** wled-sim is small, young, and now dormant — created 2025-07-16, last push 2025-08-05 (11 months idle as of re-check 2026-07-03), 6 stars, license AGPL-3.0 (fine to co-run as a separate process; do not link/vendor its code) [S511]; WLED itself very active (v16.0.0 2026-05-03, v16.0.1 2026-06-30 [S753]).

### Web 3D LED previewers (three.js point clouds)

- **The pattern is well-trodden but there is no reusable standard component.** LED-as-point-cloud in WebGL appears repeatedly as small one-off projects: ledcube-webgl (WebGL LED-cube simulator) [S513], LEDCube-ThreeJS (three.js cube sim taking 3D coordinate files) [S513], and fastled-wasm's screenmap-driven browser renderer [S500][S503]. General-purpose three.js point-cloud viewers (e.g., Potree for massive datasets) prove the rendering approach scales far beyond any LED count pewpew will hit [S513].
- **The strongest 3D-preview prior art is not web:** Chromatik/LX renders the whole installation as a 3D point cloud in a Java desktop UI and is "3D-first" by design [S034]; TouchDesigner 2025's DMX POPs treat fixtures as 3D points on the GPU [S029]. Both demonstrate that serious spatial-effect authoring wants a 3D view of the actual geometry, not a strip widget.
- **Technique notes.** A three.js `Points` object with a `BufferGeometry` position attribute (from the mapping file) and a per-frame-updated color attribute renders tens of thousands of LEDs at 60 fps in any browser; additive blending + round sprites approximate LED glow. This is a weekend-sized component, which is why everyone rebuilds it and nobody packages it [S513] (inference from survey; no packaged npm "led-previewer" found this pass).

### Terminal / pygame previewers in Python projects

- **neopixel-plus** (PyPI): NeoPixel library with a "terminal testing mode — so you can see how your LEDs would behave directly in the terminal, without any microcontroller" — ANSI-color blocks as a zero-dependency preview [S514]. The cheapest possible preview tier; good for CI logs and ssh sessions.
- **Pyglet/pygame GUI emulators:** having11/NeoPixel-Emulator emulates strip + matrix with an Adafruit-GFX port in Pyglet [S515]; Footleg/neopixel-emulator mocks the Adafruit RPi NeoPixel API so unmodified scripts render to a window [S515]. The common trick: *API-compatible mock of the hardware library* so pattern code is unchanged between sim and device.
- **led-control** [S017] and LedFx [S011] both preview via their web UIs rather than pygame — in mature Python engines the browser won as the preview surface.
- **Maintenance reality:** these emulators are mostly small, single-author, and dormant (activity typically 2019–2022 era) [S514][S515][NEEDS-VERIFICATION per-repo]. The *pattern* (hardware-API mock + ANSI/window renderer) is trivial to reimplement; the projects themselves are not dependencies to build on.

### Terminal / pygame previewers in Python projects
<!-- TODO -->

### Testing LED effects: golden-frame & perceptual diff

- **Short answer: essentially nobody golden-frame-tests LED effects.** Direct inspection of the two most relevant test suites (2026-07-03):
  - **LedFx** ([S011], `tests/`): tests are HTTP-API-level — set effect via POST, assert JSON response, `proof_of_life.py`-style smoke tests that effects activate without crashing. No pixel-output assertions, no golden frames anywhere in `tests/test_definitions/effects.py` or `all_effects.py` [S516].
  - **FastLED** (`tests/` [S517]): a host-compiled doctest-based unit suite exists (doctest_main.cpp plus build-tooling tests), covering math/color primitives and build regressions (e.g., `test_esp32s3_bloat_regression.py`) — but no frame-snapshot tests of effects were found [S517].
  - **WLED**: no effect test suite at all (firmware repo, hardware-tested by humans) [S001].
- **Why the gap.** Effects are judged aesthetically; outputs depend on wall-clock time, randomness, and audio input; and a byte-exact diff breaks on any intentional tweak. But the standard remedies from graphics are directly transferable: fixed seed + injected fake clock + N golden frames per effect, compared with a *perceptual* tolerance (per-channel epsilon, or SSIM) rather than exact equality — exactly what pytest-mpl does for matplotlib figures (`--mpl` baseline images with RMS tolerance) [S518].
- **Opportunity.** A pattern engine whose render function is pure (`frame = render(t, mapping, params, rng_seed)`) makes golden-frame testing trivial; the engines above can't do it because time, audio, and device state are woven through their render paths. Pewpew doing this would be genuinely novel in this niche [S516][S517] (inference).

### Hot-reload in Python pattern dev / livecoding culture

- **watchfiles** (samuelcolvin): the current-standard Rust-backed file watcher; powers Uvicorn's `--reload`; sync + asyncio APIs (`watch`/`awatch`) and a `run_process` helper that restarts a target on change [S519]. This is the boring, reliable substrate for a reload loop.
- **Process restart vs true hot-swap.** Two schools:
  - *Restart* (watchfiles/uvicorn style): kill and re-exec. Simple, always correct, but loses all runtime state — for LEDs that means animation phase, audio history, and brightness state reset every save.
  - *Hot-swap*: *jurigged* patches function code in place "so that all existing instances are simultaneously modified" [S520]; *promplate/hmr* re-runs only the dependency-affected modules reactively instead of restarting the whole process [S520]. These preserve state, at the cost of edge cases (changed class layouts, module-level side effects).
  - The livecoding sweet spot for LEDs is narrower and easier than general HMR: patterns are small leaf modules with a known interface, so "re-import the pattern module, keep the engine and its state running, carry `t` across the swap" gives Pixelblaze-style continuity with none of jurigged's generality risks (design inference from [S504][S519][S520]).
- **Culture.** Pixelblaze is livecoding culture applied to LEDs (feedback on keystroke, crash-safe VM) [S504]; shader livecoding (Shadertoy et al.) and music livecoding (TidalCycles/Sonic Pi) established the norms — sub-100 ms feedback, errors never stop the show, state carries across edits. No prominent Python LED project was found that ships hot-reload of patterns out of the box; led-control reloads via its web UI's code editor for its embedded pattern DSL [S017][NEEDS-VERIFICATION on exact reload semantics].

### Hot-reload in Python pattern dev / livecoding culture
<!-- TODO -->

## Recommendation: what preview/iteration stack pewpew should build first

Ordered by leverage; each layer is independently useful and the earlier ones are prerequisites for tastefully building the later ones.

1. **Pure render core + virtual output device (build first).** Make `render(t, mapping, params, seed) -> frame` pure, and make "a preview sink" just another output alongside real transports — LedFx's dummy device shows this costs almost nothing and is the documented no-hardware dev path [S508]. Purity is also what unlocks testing (below) and deterministic scrubbing.
2. **Hot-reload of pattern modules with state carry-over.** watchfiles-driven re-import of the edited pattern module while the engine keeps running; carry `t` and parameter values across the swap so the animation never glitches [S519]. This delivers the Pixelblaze feel — "recompiled and sent on every change" [S504] — and in Python it's cheaper than fastled-wasm's 1–3 s compile loop because there is no compile [S500]. Pattern exceptions must be caught per-frame and shown, never fatal, copying Pixelblaze's crash-proof editor semantics [S504].
3. **Browser preview via websocket, 2D first, three.js points when mapping goes 3D.** Serve the mapping (positions) once, stream compact per-frame color buffers; render as a strip/matrix canvas initially and a three.js `Points` cloud once RA-07 mapping lands. Precedents: LedFx's live-visualization frontend (note its 4096-px stream cap — budget bandwidth deliberately) [S508], fastled-wasm's screenmap renderer [S503], Chromatik's 3D-first UI [S034]. xLights teaches one extra feature worth having eventually: preview over a photo of the real installation [S506].
4. **Golden-frame tests from day one.** With a pure core: fixed seed + fixed timestamps → N frames per pattern, compared with perceptual tolerance (pytest-mpl-style baseline-plus-RMS, or per-channel epsilon) [S518]. No surveyed project does this [S516][S517]; it is cheap insurance for refactors of color/mapping code where regressions are invisible in unit tests but obvious on a tree.
5. **Later, not first:** terminal ANSI preview (nice for ssh/CI, trivial via the same sink interface) [S514]; scrub/timeline playback; photo-underlay preview [S506]; live variable watcher + auto-generated parameter sliders in the web UI (Pixelblaze's UI-controls-as-code is the model [S504]).

Anti-recommendations: do not build a device emulator (wled-sim-style API mock) before the engine exists [S511]; do not adopt jurigged-style whole-process hot-patching when leaf-module re-import suffices [S520]; do not pre-render like xLights — pewpew is a live engine [S506].

## Verdicts

- **fastled-wasm**: ascendant — very active through 2026-06, sets the iteration-speed bar (≤1 s incremental) for compiled LED dev [S500][S501].
- **Pixelblaze live editor**: stable — mature product, editor design unchanged because it's already right; the UX benchmark to copy [S013][S504].
- **xLights preview**: stable — dominant in sequenced house displays, actively developed, but offline-render model is irrelevant to live engines [S026][S506].
- **LedFx frontend/dummy devices**: stable/ascendant — active 2.1.x (2026-05); its dummy-device + browser-visualization pattern is the direct template for pewpew's host tier [S011][S508].
- **WLED simulation story**: waning/nonexistent — no first-party simulator; third-party API mocks only [S510][S511].
- **Standalone Python NeoPixel emulators**: waning — small dormant one-offs; reimplement the pattern, don't depend on them [S514][S515].
- **watchfiles**: ascendant/stable — de-facto standard watcher (Uvicorn dependency) [S519].
- **Golden-frame effect testing**: nonexistent in the wild — open lane [S516][S517].

## Code-reading queue

1. **LedFx** [S011] — `ledfx/devices/dummy.py` (or equivalent) + the websocket/frontend pixel-streaming path: how frames reach the browser, the 4096-px cap's cause, serialization format. Answers: what preview-stream bandwidth budget and wire format should pewpew use? [S508]
2. **fastled-wasm / FastLED wasm platform** [S500] — `src/platforms/wasm/` in FastLED + the compiler server's caching (`sketch fingerprinting`): how screenmap coordinates flow to the JS renderer and how SSE hot-reload is wired. Answers: what does a polished browser LED renderer + reload protocol look like?
3. **pixelblaze-client** [S505] — websocket message shapes: how pattern code/controls/preview frames are framed on the wire. Answers: the concrete protocol behind Pixelblaze's editor feel (compensates for the unfetchable SPA docs).
4. **Chromatik/LX** [S034][S035] — `heronarts.lx.model` + UI preview classes (design-only read; license forbids reuse): how a decade-refined 3D point-cloud preview organizes camera/model/color pipelines.
5. **watchfiles** [S519] — `run_process` and `awatch` semantics (debounce, event coalescing). Answers: correct debounce strategy so rapid saves don't thrash the reloader.
6. **xLights** [S026] — house-preview background-image/3D model placement code, low priority. Answers: what would photo-underlay preview take?

## Open questions

- Pixelblaze internals: is compilation to bytecode really done in the browser, and what exactly streams back to the editor preview strip? electromage.com/docs is an unfetchable JS SPA; settle by reading pixelblaze-client's protocol handling [S505] or the forum. [S200][NEEDS-VERIFICATION]
- fastled-wasm license: repo footer says MIT, PyPI says BSD-3-Clause — check LICENSE file at HEAD before any reuse [S500][S501].
- LedFx frontend pixel cap: is 4096 a websocket-bandwidth limit or a rendering limit, and has 2.1.x raised it? Code read #1 settles it [S508].
- led-control's editor reload semantics (does it hot-swap its pattern DSL live?) — needs a code read of [S017]/[S210].
- Do any pro tools (Madrix, Resolume, TouchDesigner) regression-test effect output perceptually? Closed-source; unanswered this pass.
- Real-time factor of WLED under Wokwi — unmeasured; only matters if someone proposes Wokwi as a dev loop [S512].
