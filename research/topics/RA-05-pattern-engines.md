# RA-05: Pattern-engine design

Last researched: 2026-07-03
Status: draft
S-ID block: S200–S249

## Key questions

1. What authoring model does Pixelblaze use (expression language, render(index)/2D/3D, coordinate normalization, time() built-ins, live-compile UX, sensor bindings), and why is it considered best-in-class?
2. How does WLED's segment+effect model work, what is the effect-function signature, and why is authoring custom effects hard?
3. How does LedFx structure its effect class hierarchy, virtuals/devices split, and audio-feature injection?
4. How does led-control implement "Python functions as fragment shaders", and what is its performance approach?
5. What NumPy vectorized frame-generation idioms exist, and what real throughput do people report?
6. What do GPU/shader routes (Shadertoy-to-LED, ISF, TouchDesigner) offer, and at what cost?
7. How do engines expose parameters/knobs to UIs?
8. What authoring model should a new Python engine adopt to beat these?

## Findings

### Pixelblaze (expression-language, per-pixel render model)

- License/status: firmware is closed-source; the public `simap/pixelblaze` repo holds docs (expressions, mapper) and hardware references, no license file, last push 2024-06-04 [S201]. Product line (V3 Standard/Pico) actively sold; firmware releases continue (v3.47 HDR drivers 2023-07; V3.66 2024-12; V3.67 2025-11) [S013][S014][S750]. Form factor: dedicated ESP32 controller — wearable through room-scale.
- **Language**: "based on JavaScript (ES6) syntax, but with a subset of the language features available. All numbers in Pixelblaze are 16.16 fixed-point numbers... between -32,768 to +32,768 with fractional accuracy down to 1/65,536ths" [S201]. No objects, named properties, or classes; arrays via `array(size)`; lambda functions but no closures ("any function defined in another function won't have access to parameters or local variables") [S201].
- **Render model**: the pattern exports `beforeRender(delta)` (per-frame setup; `delta` = elapsed ms since last call, "with a resolution of 6.25ns") plus exactly one of `render(index)`, `render2D(index, x, y)`, `render3D(index, x, y, z)` — the engine picks the variant matching the installed pixel map [S201][S200]. Inside render the pattern calls `hsv(h,s,v)` or `rgb(r,g,b)` to set the current pixel. This is a *pure per-pixel function of (index, coords, time-derived globals)* — effectively a fragment shader in scalar form.
- **Coordinate normalization**: the mapper converts arbitrary physical coordinates (inches, mm, pixels) into "world units" 0.0–1.0 per axis, auto-scaled from the map's bounding box, so patterns are resolution- and geometry-independent [S202][S200]. This is the single feature most cited for pattern portability across installations.
- **Time built-ins**: `time(interval)` returns "a sawtooth waveform between 0.0 and 1.0 that loops about every 65.536*interval seconds"; `wave(v)`, `square(v, duty)`, `triangle(v)` reshape a 0–1 sawtooth into sinusoid/square/triangle [S201]. Convention: call `time()` in `beforeRender`, not per pixel. The 0–1-phase idiom composes: `wave(time(0.1) + x)` gives a spatial wave with zero bookkeeping.
- **Live-compile UX**: "everything you type is compiled on the fly. If your program is valid, it is sent down to Pixelblaze, and you'll see your changes instantly!" [S201]. Sub-second edit→light feedback is the core of Pixelblaze's authoring reputation.
- **UI controls by naming convention**: exporting a function whose name starts with a control prefix auto-generates a widget — e.g. `export function sliderSpeed(v) { speed = 1000 * v * v }` creates a "Speed" slider (0–1 value passed in); `hsvPickerColor(h,s,v)` / rgbPicker create color pickers [S203]. Controls are discovered by reflection over exports; no separate manifest.
- **Sensor bindings**: the sensor expansion board (mic, line-in, FFT, 3-axis accelerometer, light sensor, 5 analog ins, own coprocessor) injects pre-processed data as plain exported vars: `frequencyData` (32-element FFT array, 12.5 Hz–10 kHz), `energyAverage`, `maxFrequency`/`maxFrequencyMagnitude`, `accelerometer[3]`, `light`, `analogInputs[5]` — declared with `export var` and defaultable when the board is absent [S204]. Patterns consume features, never raw audio: "fed directly into your pattern as variables so you can focus on using the data instead of processing it" [S204].

Takeaway: Pixelblaze wins on (a) per-pixel purity + normalized world coords, (b) 0–1 phase/time idioms, (c) zero-ceremony UI controls, (d) pre-chewed sensor features, (e) instant compile loop. Its costs: fixed-point-only math, no data structures, single pattern at a time, closed engine.

### WLED (segment + effect model)

- License/status: MIT (EUPL for 0.15+ core — see RA-01 [S001]); very active as of 2026 (0.16 cycle) [S002]. Form factor: ESP32/ESP8266 firmware — wearable through room-scale.
- **Model**: the strip is divided into *segments*; each segment independently runs one effect from a compiled-in table, with a palette, speed/intensity sliders, and up to 3 color slots. Effects are free C++ `void mode_myEffect()` functions that write pixels through segment-scoped macros: `SEGMENT` (current segment), `SEGENV` (per-segment state/timing environment), `SEGLEN`, `SEGCOLOR(n)` [S205].
- **Effect signature & registration**: an effect = function + PROGMEM metadata string, registered with `strip.addEffect(id, &mode_myEffect, _data_FX_MODE_MY_EFFECT)`; "Writing effects as usermods is the recommended way to add new LED effects to a WLED build — no core source files need changing" [S205].
- **Parameter exposure**: the metadata string is a terse DSL: `<name>@<slider labels>;<colors>;<palette>;<flags>;<defaults>`, e.g. `"Fire 2012@Cooling,Spark rate,,2D Blur,Boost;;!;1;pal=35,sx=64,ix=160,m12=1,c2=128"` — labels rename the fixed hardware-slot sliders (speed `sx`, intensity `ix`, three custom sliders/checkboxes), and the UI renders them generically [S206]. Effects read them as `SEGMENT.speed`, `SEGMENT.intensity` (uint8_t 0–255). So parameterization is *fixed slots with relabeling*, not arbitrary typed parameters.
- **Why authoring is hard**: effects are compiled into the firmware binary; there is "no runtime effect injection mechanism" — adding one means setting up PlatformIO, writing C++ against segment macros, encoding the metadata string, and reflashing [S205]. Contrast with Pixelblaze's in-browser live compile.
- **Community response — ARTI-FX**: WLED-SR/MoonModules built ARTI-FX, "effects which are not compiled in the WLED repository but specified by a file (program file) which is interpreted in real time", so "anybody can create effects without releasing a new version of WLED"; programs define `renderFrame` (once per frame) and `renderLed` (once per LED) and even ship Pixelblaze-compat functions (`time`, `wave`, `triangle`, `square`) — but it is admittedly slower than compiled effects [S207]. The existence of ARTI-FX (and its deliberate Pixelblaze mimicry) is strong evidence that the segment+compiled-effect model is felt as an authoring bottleneck by WLED's own power users [S207].

Takeaway: WLED's segment model is excellent *operationally* (mix effects per zone, generic UI from metadata) but poor *authorially* (C++ + reflash, fixed parameter slots, 1D-first with 2D bolted on).

### LedFx (Python effect classes, virtuals/devices, audio injection)

- License/status: GPL-3.0, active (2.1.x releases through May 2026) [S011][S012]. Form factor: host-side Python (PC/Pi) driving WLED/E1.31/etc. — room-scale primary.
- **Three-layer architecture**: Devices (physical endpoints, fixed pixel counts) ← Virtuals (logical strips mapping onto device segments; spans/splits allowed) ← Effects (render algorithms). Effects render to a virtual, never a device; the virtual applies post-processing and the device flushes protocol packets [S208][S011].
- **Effect base class** (`ledfx/effects/__init__.py`): class-based, registry-loaded (`Effect(BaseRegistry)`). Subclass implements `render(self)` which "Must act on self.pixels" — a NumPy `(pixel_count, 3)` float array; docstring notes "The effect can use self.pixels to see the previous effect" (frame persistence for trails) [S208:ledfx/effects/__init__.py#L274-L479]. Optional `on_activate(pixel_count)` and `config_updated(config)` hooks.
- **Config/parameters**: every effect declares a voluptuous `CONFIG_SCHEMA`; base Effect contributes universal knobs (`blur` 0–10 float, `flip`, `mirror`, brightness, background color); schemas are merged up the MRO so subclasses inherit parent knobs automatically [S208:ledfx/effects/__init__.py#L291-L394]. The frontend renders controls generically from schema metadata (description, default, range) — schema-as-UI-contract.
- **Class hierarchy**: `Effect` → mixins/intermediates like `GradientEffect` (palette/gradient handling), `TemporalEffect` (own render thread at a fixed speed), `AudioReactiveEffect` (audio) — effects combine them by inheritance [S209][S208].
- **Audio-feature injection**: a shared `AudioAnalysisSource` runs mic capture + FFT once, feeding subscribed analyzers: `Melbanks` (3 filterbank resolutions), pitch, onset, `bar_oscillator`, `volume_beat_now`, `freq_power` [S209:ledfx/effects/audio.py#L1196-L1265]. `AudioReactiveEffect` "just subscribes to the melbank input source and forwards input along to the subclasses" via an `audio_data_updated(data)` callback; a `melbank(filtered, size)` helper returns the melbank clipped to the *virtual's* configured frequency range and interpolated to any requested size [S209:ledfx/effects/audio.py#L1534-L1707]. Analysis is computed once and shared across all running effects — the key efficiency decision.
- **Authoring friction**: writing an effect means a new Python class inside the package (registry import), voluptuous boilerplate, and a LedFx restart; there is no in-app editor or hot reload — authoring is contributor-oriented, not user-oriented [S208][S012]. Effects are 1D-first (pixel vector); 2D matrix support exists but is a later graft.

Takeaway: LedFx demonstrates the right *host-side plumbing* (virtual/device split, schema-driven UI, shared audio analysis) but its authoring loop (edit package code, restart) is the weakest of the systems studied.

### led-control (Python functions as fragment shaders)

- License/status: MIT; last commit 2023-11-10 — **unmaintained ~2.5 years** as of 2026-07-03 (193 stars) [S017][S210]. Form factor: Raspberry Pi (SPI/PWM LEDs) — wearable-adjacent to portable.
- **Authoring model**: "Animation patterns are defined as Python functions that work similarly to GLSL fragment shaders or DirectX pixel shaders" [S210]. Per LED per frame the function receives `t` (time in cycles = speed × seconds), `dt`, `x, y, z` (normalized 0–1 coordinates), and `prev_state` (previous pixel color), and returns a color tuple plus a color-space tag (`hsv` or `rgb`) [S210]. This is the closest existing translation of the Pixelblaze model into Python, including the 0–1 coordinate normalization.
- **Performance approach**: user pattern code is "compiled using RestrictedPython" (sandboxed exec); "color conversions, color correction, and final rendering operations are implemented in a C extension module"; wave helpers (`wave_sine`, `wave_cubic`, `wave_triangle`, `wave_pulse`, plasma, Perlin) have "optimized C implementations" on the Pi [S210]. Claimed: "up to 150 FPS on 150 RGBW LEDs on a Raspberry Pi Zero" [S210] — i.e., ~22.5k pixel-evaluations/s of *interpreted-Python-per-pixel* with C-side helpers; this is the ceiling of the per-pixel-Python-callable approach and shows why it does not scale to thousands of pixels without vectorization.
- **Palettes/UI**: `palette(t)` / `palette_mirrored(t)` interpolated in HSV; in-browser code editor and palette editor for live authoring [S210]. Output includes an E1.31/sACN *receiver* mode for LedFx integration [S210].

Takeaway: led-control validates the Pixelblaze-in-Python authoring UX (shader-style function, normalized coords, browser editor) but its per-pixel Python-call execution strategy caps throughput; a successor must keep the authoring surface while executing vectorized.

### NumPy vectorized frame generation

- **The core idiom**: keep the whole frame as one `(N, 3)` float array; effects are whole-array expressions (broadcasted math over a precomputed coordinate array), not per-pixel Python calls. LedFx's `Effect.render()` mutating `self.pixels: np.zeros((pixel_count, 3))` is the canonical production example [S208:ledfx/effects/__init__.py#L350-L479]. The companion idiom: precompute coordinate/index arrays once at activation (`on_activate`), so per-frame work is pure arithmetic on cached arrays [S208].
- **Working-copy idiom** (from the microcontroller end but identical in shape): "create a 'working copy' of the LED data in a ulab array, and use ulab functions as much as possible... then at the last possible moment, copy the working copy data to the real LEDs object" — todbot measured a fire effect on 256 LEDs at ~40 ms/frame in a Python loop vs ~4 ms/frame vectorized on an RP2040 — a 10x speedup even on a microcontroller [S211].
- **Real throughput reports** (sparse, honest summary):
  - Per-pixel interpreted Python: led-control's ~150 fps × 150 LEDs on Pi Zero (~22.5k px/s) is the best documented figure for that strategy, and it needed C helpers to get there [S210][S017].
  - scottlawsonbc's audio-reactive-led-strip (NumPy/SciPy per frame, ~256 pixels): "Raspberry Pi is just fast enough to run the visualization, but it is too slow to run the GUI window as well" [S212]; users report ~60–90 fps at 60–174 pixels on a Pi with FPS falling as counts rise [S212][NEEDS-VERIFICATION].
  - LedFx routinely drives many WLED devices at its default 60 fps tick from a desktop; per-effect cost is dominated by melbank interpolation and blur, both vectorized [S208][S209]. No published px/s ceiling was found — an open question below.
  - Rule of thumb consistent with the above: interpreted per-pixel Python plateaus at low tens of kilopixels/s; vectorized NumPy gains ~1–2 orders of magnitude, which is what makes 10k+ pixels at 60 fps plausible on a host CPU [S211][S210][NEEDS-VERIFICATION — no direct 10k-pixel benchmark located; settle with our own microbenchmark].
- **Implication for authoring**: the vectorized style conflicts with the beginner-friendly per-pixel shader style. Engines must either (a) expose array semantics directly (LedFx — harder to author), (b) accept the per-pixel ceiling (led-control), or (c) compile per-pixel source into vectorized/native code (Numba `@njit`/`vectorize`, or NumPy AST transforms) — nobody in the LED space ships (c) today, which is the open lane [S208][S210].

### GPU / shader routes (Shadertoy, ISF, TouchDesigner)

- **The common pattern**: render content to a texture/framebuffer on GPU, then *sample* the pixels at each LED's mapped (u,v) position and ship the sampled colors out via Art-Net/sACN/DMX. TouchDesigner formalizes this: fixtures/LEDs are laid out as points in a SOP (3D), the video TOP is sampled at those points, and a DMX CHOP emits Art-Net/sACN; community libraries like TouchLED wrap the whole mapping + visualizer flow [S213]. This is content-sampling, not per-pixel programs — great for video-like room-scale content, indifferent to strip topology semantics [S213].
- **ISF (Interactive Shader Format)**: "a [slightly modified] GLSL fragment shader with a JSON blob at the beginning that describes how to interact with the shader (how many inputs/uniform variables it has, what their names are, what kind of inputs/variables they are)" [S214]. ISF is the cleanest existing *parameter-manifest* design: typed INPUTS (float/bool/color/point/image + ranges/defaults/labels) declared next to the code, letting any host auto-build UI. Open spec (github.com/mrRay/ISF_Spec), used by VDMX and other VJ hosts [S214]. Directly stealable idea for a Python engine even without GPUs.
- **Shadertoy-to-LED**: no canonical maintained project found; the route exists as one-off integrations (render Shadertoy-style GLSL offscreen, read back, map to LEDs) and as commercial bridges (ENTTEC ELM exposes each effect parameter "via DMX, Art-Net, sACN, OSC and HTTP") [S215][NEEDS-VERIFICATION — survey was shallow; a deeper hunt may find maintained shader-to-sACN bridges].
- **Costs of the GPU route**: needs a GPU + windowing/offscreen context (fragile headless on Pi), readback latency, and authors must think in image space rather than strip space; the win is huge parallel throughput and an enormous existing shader corpus [S213][S214]. For pewpew's host-side Python engine the transferable pieces are (a) ISF-style typed parameter manifests and (b) "sample a field at mapped coordinates" as an optional content source — not GPU-first authoring.

### Parameterization: exposing knobs to UIs

Five distinct designs observed, from weakest to strongest:

1. **Fixed slots, relabeled** (WLED): 2 standard + 3 custom sliders/checkboxes per effect; the metadata string only renames them (`Fire 2012@Cooling,Spark rate,...`) [S206]. Cheap for a firmware UI; cannot express types, ranges, or more than ~5 knobs.
2. **Naming-convention reflection** (Pixelblaze): exporting `sliderSpeed(v)` / `hsvPickerColor(h,s,v)` auto-creates widgets; value pushed into pattern globals [S203]. Zero ceremony, but the vocabulary is limited to the prefixes the firmware knows, and there is no range/default metadata.
3. **Validation-schema-as-manifest** (LedFx): voluptuous `CONFIG_SCHEMA` per effect with description/default/Range per key, merged through the class hierarchy, rendered generically by the web UI [S208]. Typed and self-documenting; verbose to author; static (no per-frame modulation of a config value).
4. **Sidecar JSON manifest** (ISF): typed INPUTS block adjacent to shader code — the portable-document version of (3) [S214].
5. **First-class parameter objects** (LX/Chromatik): patterns register `CompoundParameter("Label", init, min, max).setDescription(...)` fields via `addParameter()`; registered parameters automatically get UI knobs and "the ability to be easily mapped to UI components, MIDI controllers, or OSC messages"; docs advise CompoundParameter "as this opens up interesting modulation possibilities" — i.e. LFOs/audio modulators can be *patched onto any knob* at runtime, DAW-style [S216]. This is the most powerful model: parameters are addressable, modulatable signal endpoints, not just config values.

Cross-cutting: ENTTEC ELM shows the pro-lighting convention that every parameter is remotely addressable (DMX/Art-Net/sACN/OSC/HTTP) [S215]. The synthesis target is (5)'s semantics with (2)'s ergonomics: declare a typed parameter in one line of Python (default+range+label), get UI, OSC/MIDI address, and modulation input for free.

### Candidate answer: authoring model for a Python engine

Evidence-backed synthesis — the model that beats the field combines the best-verified feature of each system:

1. **Authoring surface: Pixelblaze's per-pixel purity, in real Python.** Patterns are pure functions of `(coords, time-phase, params, features)` with coordinates normalized to 0–1 world units [S201][S202][S210]. This survived two independent reimplementations (led-control [S210], ARTI-FX [S207]) — strong evidence it is the model users want.
2. **Execution: vectorized, not per-pixel-interpreted.** Per-pixel Python caps out ~22.5k px/s on small hardware [S210]; vectorization buys ~10x even on an RP2040 [S211]. The engine should evaluate the *same authored function* over coordinate arrays (author writes scalar-looking NumPy-compatible expressions; engine passes arrays — the "NumPy ufunc trick"), with an optional Numba/compiled tier. No existing LED system does this; it is the differentiator.
3. **State model: `beforeRender(delta)` / render split** [S201] plus LedFx's persistent `self.pixels` previous-frame access for trails/decay [S208].
4. **Parameters: LX-style typed parameter objects declared in one line** — auto UI + OSC/MIDI address + modulation input [S216], serialized ISF-style so patterns are portable documents [S214].
5. **Sensor/audio: Pixelblaze/LedFx-style feature injection** — one shared analysis pipeline (melbank, onset, beat phase, energy) computed once per frame and handed to patterns as read-only variables; patterns never touch raw audio [S204][S209].
6. **Composition: WLED/LedFx's operational layer** — virtuals/segments map patterns onto subsets of the installation, independent of pattern code [S208][S205].
7. **Feedback loop: live editing is non-negotiable.** Pixelblaze's compile-on-keystroke [S201] and ARTI-FX's raison d'être [S207] both prove demand; Python gives it nearly free (exec module on save/keystroke, crossfade to new instance on success, keep old on error).

Anti-goals from the evidence: don't require firmware flashes for effects (WLED's core weakness [S205]); don't make authors write registry classes + schema boilerplate (LedFx's weakness [S208]); don't adopt GPU-first authoring (context fragility; steal ISF manifests and field-sampling instead [S213][S214]).

## Verdicts

- **Pixelblaze**: stable/ascendant as a product (V3 line current, firmware releases continue [S013][S014]), but its public docs repo is quiet since 2024-06 [S201] and the engine is closed — study it, don't build on it.
- **WLED (effect model)**: ascendant as a platform, waning as an *authoring* model — its own community built ARTI-FX to route around compiled-in effects [S207][S002].
- **LedFx**: stable and active (2.1.x, 2026) [S011]; its virtual/device split and shared audio analysis are current best practice; its authoring loop is not.
- **led-control**: waning — unmaintained since 2023-11 [S210]; its authoring surface remains the best Python prior art.
- **ISF / parameter manifests**: stable, widely adopted in VJ software [S214] — adopt the idea.
- **LX/Chromatik parameter+modulation model**: stable, actively developed [S034][S216] — the semantics to copy for knobs.
- **TouchDesigner GPU sampling route**: stable/ascendant commercially [S029][S213], wrong authoring center of gravity for a Python engine; interop target, not architecture.

## Code-reading queue

1. **LedFx — `ledfx/effects/__init__.py`, `audio.py`, `virtuals.py`** (pin S208/S209): exactly how schema→UI flows, how the virtual applies post-fx and frequency ranges, per-frame cost structure. Answers: what plumbing to reuse conceptually vs. redesign (GPL-3.0 — read for ideas, no code reuse if pewpew is permissively licensed).
2. **led-control — `ledcontrol/animationcontroller.py`, `ledcontrol/rpi_ws281x/` C extension, pattern compile path** (pin S210/S017): how RestrictedPython compilation + per-pixel dispatch is implemented and where the 22.5k px/s ceiling comes from. Answers: what to keep from the authoring surface and precise cost of the per-pixel model.
3. **heronarts/LX — `LXPattern`, `parameter/` package, `modulator/` package** [S035][S216]: parameter objects, modulation routing, normalization. Answers: minimal Python translation of parameter-as-modulatable-endpoint.
4. **MoonModules ARTI-FX interpreter (`arti_wled.h`, wled-sr repo)** [S207]: what a small interpreted effect language on MCU looks like; renderFrame/renderLed calling convention. Answers: whether a shared pattern format could target both host and MCU tiers.
5. **simap/pixelblaze docs + community pattern corpus (patterns.electromage.com)** [S201]: survey 20 popular patterns for which built-ins/idioms carry the load (time/wave/hsv usage frequency). Answers: the minimum built-in library a competitor must ship.
6. **todbot/circuitpython_led_effects `ulab_speedup/`** [S211]: the measured 10x pair, as a template for our own vectorization microbenchmark.

## Open questions

- **No published benchmark of NumPy LED frame generation at 5k–50k pixels on desktop/Pi 4/Pi 5.** Settle with a ~50-line microbenchmark (per-pixel loop vs NumPy vs Numba, N ∈ {300, 3k, 30k}) before any execution-model ADR. [gap noted in Findings]
- **Can scalar-looking Python pattern code be transparently evaluated over arrays** (ufunc trick) without confusing authors on branching (`if` vs `np.where`)? Needs a prototype; no prior art found in the LED space.
- **Pixelblaze's exact UI-control vocabulary** (full list of recognized prefixes: slider*, *Picker*, trigger*, toggle*?) — [S203] shows examples only; verify against electromage docs when reachable (docs site JS-rendered, 404s under fetch).
- **Maintained Shadertoy/GLSL→sACN bridges**: shallow survey found none canonical; a deeper hunt (GitHub topic search, LedFx GLSL plugin rumors) could change the GPU-route verdict.
- **LedFx real-world throughput ceiling** (pixels × fps before frame drops): no published figure; could ask on their Discord or measure.
- **ARTI-FX current status inside MoonLight** (the MoonModules successor [S006]): is it still developed in 2026, or replaced by MoonLight's "Nodes"/live scripts? Affects code-reading item 4 priority. [NEEDS-VERIFICATION]
