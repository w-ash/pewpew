# Code reading: led-control (jackw01/led-control)

- repo: https://github.com/jackw01/led-control (seed [S017]; docs site [S210])
- pinned: jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6 [S660]
- license: MIT (Copyright (c) 2021 jackw01) [S660:LICENSE#L1-L3]
- accessed: 2026-07-03
- language split: ~2,270 lines of Python in `ledcontrol/` plus two C headers
  compiled into a SWIG extension (`led_render.h`, `animation_utils.h`); vendored
  rpi_ws281x as a git submodule [S660:.gitmodules#L1-L3]

## How it achieves its signature quality

The signature is: **arbitrary user Python as a per-pixel shader, per-pixel in
pure CPython, made fast enough by pushing everything that is NOT the user
function (color conversion, correction, quantization, output) into a C
extension, and by aggressive caching of everything that is loop-invariant.**

### 1. Pattern authoring: user Python as per-pixel shaders

Exact contract: the user writes a module that defines a function named
`pattern` with signature `pattern(t, dt, x, y, z, prev_state)` returning
`(color_tuple, color_mode)` where color is a float `(h,s,v)` or `(r,g,b)`
0..1 tuple and mode is the injected global `hsv` or `rgb` (a Python Enum)
[S660:ledcontrol/animationfunctions.py#L10-L26]. `prev_state` is that pixel's
color tuple from the previous frame, giving stateful effects (twinkle decay
stores its own countdown in the value channel)
[S660:ledcontrol/animationfunctions.py#L64-L74]. A degenerate `blank`
function is the fallback for uncompiled function IDs
[S660:ledcontrol/animationfunctions.py#L12-L13].

**Coordinates.** Every LED index is mapped once at startup to a normalized
`Point(x, y, z)`; the default is a 1D line `i/count` and 2D/3D come from a
user JSON array of points normalized into 0..0.999
[S660:ledcontrol/pixelmappings.py#L8-L17]
[S660:ledcontrol/app.py#L37-L45]. Per group, a scaled mapping is cached:
`(pos / scale) % 1` per axis, recomputed only when `scale` changes — so the
shader always sees coordinates in cycle units, and "scale" costs nothing per
frame [S660:ledcontrol/animationcontroller.py#L150-L165].

**Time.** `t` is `(perf_counter - start) % 604800` (weekly reset "to prevent
strange math issues") times the group's `speed` in cycles/s; `dt` is the
frame delta times speed [S660:ledcontrol/animationcontroller.py#L368-L373].
So both time and space arrive pre-normalized to "1.0 = one cycle", which is
why the built-in waveform helpers can all have period 1 and range 0..1
[S660:ledcontrol/driver/animation_utils.h#L19-L48].

**Sandbox/compile strategy: RestrictedPython, not plain exec.** On every
save/compile, `set_pattern_function` runs
`RestrictedPython.compile_restricted_exec(source)` and then `exec`s the
resulting code object with `safe_builtins`, `safer_getattr`, a custom
`_getitem_` that only permits list/tuple/dict indexing, and
`full_write_guard`; the compiled module's local `pattern` is stored in a dict
keyed by function ID [S660:ledcontrol/animationcontroller.py#L228-L282].
Compilation is the caching step — at render time the function object is a
plain Python callable, no per-call sandbox overhead beyond RestrictedPython's
rewritten bytecode (attribute access and subscripts go through guard
functions, which does tax the hot loop). The injected environment is a
closed, curated global namespace: `math`, `random`, `palette(t)` /
`palette_mirrored(t)`, `hsv`/`rgb` enums, `clamp`, and the C helpers
`wave_pulse/triangle/sine/cubic`, `plasma_sines`, `plasma_sines_octave`,
`perlin_noise_3d`, `fbm_noise_3d`, `impulse_exp`, `fract`,
`blackbody_to_rgb`, `blackbody_correction_rgb`
[S660:ledcontrol/animationcontroller.py#L238-L264]. Undefined names are
reported as warnings at compile time by diffing `result.used_names` against
the allowed globals + arg names [S660:ledcontrol/animationcontroller.py#L268-L272];
compile errors/warnings are returned to the web UI as JSON
[S660:ledcontrol/app.py#L212-L217].

**Runtime error containment:** any exception while running a pattern is
caught per frame; the whole range is set to a pulsing dim red as a visible
error indicator, and the traceback is printed
[S660:ledcontrol/animationcontroller.py#L418-L434].

### 2. Performance strategy: what the ~150 fps on Pi Zero actually is

README claim: "up to 150 FPS on 150 RGBW LEDs on a Raspberry Pi Zero," with
the honest caveat that the wire-protocol ceiling at 800 kHz is 166.67 fps for
150 RGBW pixels and that "all built-in animations run at over 50 FPS"; the
default limit is 60 fps [S660:README.md#L17-L24]. So 150 fps is the best
case (trivial patterns), 50+ fps the typical case, at only 150 pixels. No
NumPy in the render path at all — NumPy appears only for packing remote-render
packets [S660:ledcontrol/ledcontroller.py#L124-L131].

The architecture is a strict split:

- **Python side, per pixel per frame:** exactly one call of the user function
  per pixel, in a list comprehension
  [S660:ledcontrol/animationcontroller.py#L384-L391]. Everything else is
  hoisted out of the loop: palette table selection, computed brightness
  (`on * global_brightness * group brightness`), computed saturation,
  function lookup, time math
  [S660:ledcontrol/animationcontroller.py#L362-L373].
- **C side, per frame:** the whole float-tuple list crosses the SWIG boundary
  once into `ws2811_hsv_render_range_float` / `ws2811_rgb_render_range_float`,
  which loop in C doing HSV→RGB, saturation, brightness, color correction,
  8-bit quantization, and write packed `uint32_t` words directly into the
  rpi_ws281x channel buffer [S660:ledcontrol/driver/led_render.h#L313-L357].
  `render()` then calls `ws2811_render` (DMA/PWM output) once
  [S660:ledcontrol/ledcontroller.py#L157-L160].
- **C side, inside the user function:** the expensive primitives users would
  otherwise write in Python (waveforms, plasma, Perlin/fBm noise) are C
  functions exposed through the same SWIG module and injected into the
  sandbox — the README notes this gives "a surprisingly significant
  performance improvement" [S660:README.md#L229]
  [S660:ledcontrol/driver/animation_utils.h#L23-L162]. Even
  float→palette-index conversion is a C function (`float_to_int_1000`)
  because it beat the equivalent Python expression
  [S660:ledcontrol/animationcontroller.py#L300-L308]
  [S660:ledcontrol/driver/animation_utils.h#L11-L17].

**Other load-shedding tricks:**

- **Palette lookup tables:** palettes are lists of HSV stops; a 1000-entry
  interpolated table per palette is precomputed at edit time with
  shortest-path hue interpolation (full-spectrum allowed when endpoints are
  0 and 1), so `palette(t)` at render time is one C float→int call plus one
  list index [S660:ledcontrol/animationcontroller.py#L111-L140].
- **Idle suppression:** `_update_needed` — if the current function is a
  static-color ID, speed is 0, or computed brightness is 0, no rendering
  happens at all until a setting changes
  [S660:ledcontrol/animationcontroller.py#L436-L442].
- **Frame scheduler:** a daemon-thread `IntervalTimer` that subtracts the
  measured cycle time from the sleep interval (compensated fixed-rate loop;
  a Windows variant measures start-to-start instead), with running
  perf-average and fps counters (see seed [S255])
  [S660:ledcontrol/intervaltimer.py#L30-L47].
- **Mode probe hack:** each frame the function is called once with dummy args
  `(0, 0.1, 0, 0, 0, (0,0,0))` just to read its color-mode return, so the
  whole range can be dispatched to the HSV or RGB C renderer in one batch
  [S660:ledcontrol/animationcontroller.py#L380-L381]. This assumes a pattern
  returns the same mode for all pixels and burns one extra call per frame.
- **Server:** Flask served by bjoern (fast C libev WSGI) on Linux
  [S660:setup.py#L34-L43]. On non-Pi hosts the C extension is replaced by a
  pure-Python shim (plus pyfastnoisesimd for noise), same API
  [S660:ledcontrol/driver/__init__.py#L15-L19]
  [S660:ledcontrol/driver/driver_non_raspberry_pi.py#L1-L62].

**What it gives up:** per-pixel CPython calls put a hard ceiling on pixel
count (the claim is only ever made for 150 pixels — scaling to thousands of
pixels at 60 fps is out of reach); RestrictedPython guard overhead in the hot
loop; a stray `time.sleep` or infinite loop in user code stalls the single
render thread (RestrictedPython prevents imports but not unbounded loops);
one process, one strip channel used (channel 1 of ws2811_t is zeroed out)
[S660:ledcontrol/ledcontroller.py#L62-L77].

### 3. HSV pipeline, gamma, brightness, dithering — precision at each stage

Pipeline per pixel (HSV path), all in C
[S660:ledcontrol/driver/led_render.h#L90-L226]:

1. Pattern output: float HSV, unbounded (hue wraps via `fmod`).
2. Quantize **early** to 8 bits: `hue = fmod(h,1.0)*255`, `sat = s*saturation*255`.
3. Value: `val = (v*v)*255` — squaring the value channel is the only gamma
   correction in the system (a hardcoded gamma-2.0 on V only), then a `+1`
   nudge for nonzero values, then `scale_8` by 8-bit brightness
   [S660:ledcontrol/driver/led_render.h#L93-L97]. A real per-channel gamma
   pow() exists but is commented out in both HSV and RGB paths
   [S660:ledcontrol/driver/led_render.h#L196-L202]
   [S660:ledcontrol/driver/led_render.h#L274-L280]; the `gamma` function
   parameter is accepted and ignored, and the rpi_ws281x library gamma table
   is explicitly set to identity `list(range(256))`
   [S660:ledcontrol/ledcontroller.py#L72].
4. Hue→RGB: FastLED-style "rainbow" transform — 8 sections of 32 hue steps,
   integer thirds, yellow boosted (the visually-even rainbow, not spectrum
   HSV) [S660:ledcontrol/driver/led_render.h#L102-L162].
5. Desaturation: `desat = scale_8(255-sat, 255-sat)` (squared, i.e.
   gamma-ish white blend); on RGBW strips the desaturated component goes to
   the W channel instead of being added to RGB
   [S660:ledcontrol/driver/led_render.h#L164-L203].
6. Value scaling and per-channel color correction by `scale_8` against a
   packed 24-bit correction word (user RGB trim × blackbody temp curve,
   precomputed in Python on settings change)
   [S660:ledcontrol/driver/led_render.h#L205-L222]
   [S660:ledcontrol/animationcontroller.py#L142-L148].
7. Pack to `uint32_t` WRGB. Final precision: plain 8 bits per channel.

RGB path: clamp to 0..1 float, desaturate by moving channels toward their
mean (author's own comment: "Not sure if this is the technically correct way
but it seems to work?"), RGBW extraction as `w = min*min` after
max-anchored desaturation, then float×brightness×255 quantization
[S660:ledcontrol/driver/led_render.h#L229-L293].

**Dithering: confirmed none.** No temporal or spatial dithering anywhere in
the repo (grep over .py/.h/.c); brightness is applied multiplicatively in
8-bit space (`scale_8`), so low global brightness collapses the resolution to
a handful of levels — exactly the low-brightness banding problem FastLED's
temporal dithering and HD gamma exist to solve (cf. S615 excerpts).

### 4. Outputs

- **Local:** rpi_ws281x via a SWIG-wrapped C extension that statically links
  the vendored submodule; Python sets up the `ws2811_t` struct field-by-field
  through generated setters (pixel order incl. RGBW variants, GPIO pin, DMA
  channel, 800 kHz), and the render functions write into the channel's LED
  array directly [S660:ledcontrol/ledcontroller.py#L28-L90]
  [S660:setup.py#L45-L51]. The extension is only built on a real Pi
  (detected via `/sys/firmware/devicetree/base/model`)
  [S660:setup.py#L25-L32].
- **sACN/E1.31: input, not output.** The `sacn` package is used as a
  *receiver* — DMX data replaces the pattern engine and is rendered to the
  local strip [S660:ledcontrol/animationcontroller.py#L202-L208]
  [S660:ledcontrol/animationcontroller.py#L446-L458]. led-control does not
  transmit sACN.
- **Remote render targets:** each group can render to `serial` or `udp`
  instead of `local`; a custom binary packet (type byte, HSV/RGB flag, length,
  correction, sat, brightness, range, u8 pixel data — hue kept mod-1 via a
  NumPy strided fmod) is sent to a companion ESP8266 firmware, i.e. the
  correction/brightness math is deferred to the receiver
  [S660:ledcontrol/ledcontroller.py#L108-L142].
- **HomeKit:** optional HAP-python accessory exposing on/brightness/
  saturation only [S660:ledcontrol/app.py#L299-L313].

### 5. Web UI, control exposure, hot reload

Flask serves a static Vue 3 SPA (Vue + vue-router + axios + lodash + Pickr +
CodeMirror, all vendored) [S660:ledcontrol/app.py#L167-L170]. The API is a
flat JSON GET/POST set: settings, presets, groups, functions, palettes, fps
[S660:ledcontrol/app.py#L172-L258]. Control model: a settings dict
recursively merged on POST, with dirty-flags deciding what to recompute
(color correction, mappings, LED clear) — the reactive-recompute pattern
[S660:ledcontrol/animationcontroller.py#L173-L219].

Hot reload story: the browser edits pattern source in CodeMirror, POSTs
`/updatefunction` then `/compilefunction`; compile errors and name warnings
come back as JSON arrays and the new function takes effect on the next frame
without any restart [S660:ledcontrol/app.py#L212-L229]
[S660:ledcontrol/static/js/Store.js#L125]. Persistence: everything
(settings, non-default functions/palettes, presets) autosaves to
`/etc/ledcontrol.json` on a timer and atexit, with versioned migration and
`.bak`/`.error` backup files on upgrade or parse failure
[S660:ledcontrol/app.py#L60-L158] [S660:ledcontrol/app.py#L260-L297].

### 6. Maintenance reality

Dormant. Last commit 2023-11-09 ("fix bizarre windows/linux timer behavior
issue" = the pinned HEAD); as of 2026-07-03 GitHub reports pushed_at
2023-11-10, 193 stars, 40 forks, 17 open issues [S660]. Bus factor 1:
jackw01 has 288 of ~294 contributions; the next contributor has 4 [S660].
Version 2.0.0, pinned old deps (Flask 2.2.2, Werkzeug 2.2.2, HAP-python
4.4.0) [S660:setup.py#L34-L43]. ~2.5 years without maintenance; treat as a
design reference, not a dependency.

## What pewpew should steal

1. **The shader contract itself**: `pattern(t, dt, x, y, z, prev_state) ->
   (color, mode)` with normalized cycle-unit time and space is a genuinely
   good authoring API — speed and scale become engine-side multipliers, all
   waveform helpers can be period-1/range-0..1, and `prev_state` gives
   per-pixel statefulness for free
   [S660:ledcontrol/animationfunctions.py#L24-L26]
   [S660:ledcontrol/animationcontroller.py#L368-L373].
2. **Compile-once RestrictedPython with a curated injected namespace** and
   compile-time used-names checking returned to the editor as warnings; plus
   the pulsing-red-frame runtime error containment
   [S660:ledcontrol/animationcontroller.py#L228-L282]
   [S660:ledcontrol/animationcontroller.py#L418-L434].
3. **Hoist-everything frame loop**: precomputed scaled mappings invalidated
   by dirty flags, precomputed palette LUTs (with shortest-path hue lerp),
   precomputed packed correction word, `_update_needed` idle suppression
   [S660:ledcontrol/animationcontroller.py#L111-L165]
   [S660:ledcontrol/animationcontroller.py#L436-L442].
4. **The native/Python split boundary**: user creativity in Python, the
   entire post-shader color pipeline (convert/correct/quantize/pack) as one
   native call per frame, and fast primitives (noise, plasma, waves) injected
   *into* the sandbox so user code stays fast without vectorizing
   [S660:ledcontrol/driver/led_render.h#L313-L357]
   [S660:ledcontrol/driver/animation_utils.h#L19-L162].
5. **Settings dict + recursive merge + recompute flags** as the whole control
   plane; trivially serializable, versioned autosave with backups
   [S660:ledcontrol/animationcontroller.py#L173-L219]
   [S660:ledcontrol/app.py#L260-L297].
6. RGBW handling in both color paths (desaturated component routed to W)
   [S660:ledcontrol/driver/led_render.h#L166-L181]
   [S660:ledcontrol/driver/led_render.h#L238-L255].

## What to avoid

1. **Per-pixel CPython calls as the only execution model** — it caps the
   system at ~150 pixels/60 fps on small hardware and is the reason the
   headline number is unimpressive at scale. pewpew should offer a vectorized
   (NumPy/native) path and treat per-pixel Python as a compatibility mode.
2. **8-bit-early color pipeline with no dithering and no real gamma**: hue
   and sat quantized to 8 bits before conversion, gamma reduced to a
   hardcoded `v*v` on the value channel with the real gamma code commented
   out, identity LUT handed to rpi_ws281x, brightness applied in 8-bit space
   [S660:ledcontrol/driver/led_render.h#L93-L97]
   [S660:ledcontrol/ledcontroller.py#L72]. Keep float precision to the last
   stage and add temporal dithering (cf. FastLED S615).
3. **SWIG struct-setter plumbing** ("This is bad but it's the only way" —
   author's own comment) [S660:ledcontrol/ledcontroller.py#L29]; use cffi/
   pybind11/ctypes with a clean facade instead.
4. **The per-frame mode-probe call** with dummy arguments to discover the
   pattern's color mode — fragile (assumes uniform mode, executes user code
   with fake inputs); declare the mode instead
   [S660:ledcontrol/animationcontroller.py#L380-L381].
5. **Render thread shared with user-code hazards**: no timeout/budget on the
   user function; a `while True:` in a pattern hangs the engine.
6. **Weekly time wrap** `t % 604800` as a band-aid for float precision — a
   visible glitch every 7 days; use double time-in-cycles per pattern start
   instead [S660:ledcontrol/animationcontroller.py#L369-L370].
7. Blocking print-based logging in the render thread every 100 frames
   [S660:ledcontrol/animationcontroller.py#L336-L337].

## Open questions

- The 150 fps figure is a README claim [S660:README.md#L17]; no benchmark
  script or CI numbers exist in the repo, and the built-in-animations number
  is stated as ">50 fps". Which patterns hit 150 (presumably static/near-
  trivial ones benefiting from `_update_needed` early-out) is undocumented.
- RestrictedPython guard overhead vs plain `exec` is not measured anywhere;
  the sandbox's per-opcode cost share of the frame budget is unknown.
- The remote-render UDP/serial packet format is implemented but the companion
  receiver firmware (referenced ESP8266 project) is not in this repo; the
  `firmware/` directory contains a newer Pico W (PIO ws2812b + lwIP) receiver
  whose maturity/compatibility is unclear — it postdates the docs.
- Why the author disabled the real gamma pow() (commented out in both render
  paths) is not documented — likely performance on Pi Zero, but that is a
  guess and is flagged as such.
- Whether `getiter` returning the object unguarded
  [S660:ledcontrol/animationcontroller.py#L235-L236] weakens the
  RestrictedPython sandbox (iteration over arbitrary objects) has not been
  security-reviewed here.
