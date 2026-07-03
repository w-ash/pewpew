# Code reading: LedFx

- repo: https://github.com/LedFx/LedFx
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792 (HEAD 2026-07-02)
- license: GPL-3.0
- accessed: 2026-07-03
- source: [S630]

The most complete Python LED engine: audio-reactive effects rendered per
"virtual" strip and shipped to network devices (WLED/DDP/E1.31/Art-Net/UDP).

## 1. Core object model: Devices vs Virtuals vs Effects

Three registries hang off a singleton `LedFxCore`: `Devices`, `Effects`,
`Virtuals`, plus an `Events` pub/sub bus and an aiohttp API server, all built
on one asyncio loop (uvloop/winloop when available)
[S630:ledfx/core.py#L120-L138][S630:ledfx/core.py#L520-L527].

- **Device** = one physical output (a WLED node, an E1.31 universe set, a
  serial Adalight...). Owns a `(pixel_count, 3)` float64 numpy buffer
  `self._pixels` created on `activate()` [S630:ledfx/devices/__init__.py#L208-L210],
  a `refresh_rate` config cap, and an abstract `flush(data)` that subclasses
  implement per protocol [S630:ledfx/devices/__init__.py#L222-L227].
- **Virtual** = the render surface an effect draws on. It is a list of
  *segments* `[device_id, start_pixel, end_pixel, invert]` spanning one or
  more devices (with `gap-` placeholder devices for dead space)
  [S630:ledfx/virtuals.py#L225-L230]. A virtual has mapping mode `span`
  (effect stretched across all segments) or `copy` (effect duplicated per
  segment) [S630:ledfx/virtuals.py#L41-L45], optional pixel `grouping`
  (render at 1/N resolution, `np.repeat` up at flush)
  [S630:ledfx/virtuals.py#L1487-L1524], `rows` for 2D matrices, per-virtual
  audio frequency range, and per-virtual transition config. Every device
  automatically gets a paired 1-segment virtual at creation
  (`is_device=device.id`) [S630:ledfx/devices/__init__.py#L920-L946] — the
  UI's "one effect per device" case is just a special virtual.
- **Effect** = a stateless-ish renderer instantiated per virtual, writing a
  `(effective_pixel_count, 3)` float array (see section 4).

**Frame flow**: effect `_render()` → `Virtual.assemble_frame()` (clamp 0-255,
center-offset roll, transition blend, brightness multiplies)
[S630:ledfx/virtuals.py#L879-L945] → `Virtual.flush()` slices the span buffer
per device segment (`pixels[start:stop:step]`, negative step implements
invert) [S630:ledfx/virtuals.py#L1070-L1125] →
`Device.update_pixels(virtual_id, data)` scatter/range-writes into the
device's own pixel buffer [S630:ledfx/devices/__init__.py#L145-L194] → when
the writing virtual is the device's "priority virtual" (the active virtual
with the highest refresh rate [S630:ledfx/devices/__init__.py#L247-L265]),
the device assembles and `flush()`es a protocol packet. Multiple virtuals can
share a device only on non-overlapping pixel ranges; overlap is detected with
per-virtual sorted-interval binary search and either raises or force-
deactivates the blocker [S630:ledfx/devices/__init__.py#L296-L424]. There is
no compositing: last writer wins per pixel range, and `assemble_frame` at the
device level is just the raw buffer plus an optional `np.roll`
[S630:ledfx/devices/__init__.py#L196-L206].

An optional `complex_segments` fast path precompiles per-device
`src`/`dst` int32 index arrays so flush becomes two fancy-indexing ops
(claimed 13x for many-segment virtuals)
[S630:ledfx/virtuals.py#L409-L495][S630:ledfx/virtuals.py#L1127-L1153]. That
this is an opt-in bool rather than the only code path is telling — see
section 7.

## 2. Render loop: threading, per-virtual frame rate, pacing

**One OS thread per active virtual.** `Virtual.activate()` spawns
`threading.Thread(target=self.thread_function)`
[S630:ledfx/virtuals.py#L947-L979]. The loop body: take the virtual's
`threading.Lock`, `assemble_frame()`, `flush()` (which does synchronous
socket sends inline), fire `VirtualUpdateEvent`, then sleep
[S630:ledfx/virtuals.py#L832-L877]. Commented-out code shows they tried
running assemble/flush through the asyncio executor and abandoned it
[S630:ledfx/virtuals.py#L850-L860].

**Pacing** is sleep-based, not deadline-based:
`sleep_time = max(0.001, fps_to_sleep_interval(refresh_rate) - run_time)`
[S630:ledfx/virtuals.py#L864-L870]. `fps_to_sleep_interval` quantizes the
target FPS to an `AVAILABLE_FPS` table derived from the OS sleep-clock
resolution and returns `resolution * (ticks-1)` — i.e. it deliberately
undershoots by one clock tick, then a post-sleep check re-sleeps if the
elapsed time is under half the minimum clock resolution (a Windows
high-res-timer workaround) [S630:ledfx/utils.py#L120-L136]
[S630:ledfx/virtuals.py#L872-L877]. There is no accumulated-error correction:
each frame's period is computed independently, so long-term rate drifts with
scheduler jitter; there is also no frame-drop/catch-up concept.

**Per-virtual frame rate** = `min(device.max_refresh_rate for its devices)`
(a `cached_property`) [S630:ledfx/virtuals.py#L1313-L1317]; device
`refresh_rate` defaults to ~60 and is validated against the FPS table
[S630:ledfx/devices/__init__.py#L38-L44,L67-L74]. Devices have no clock of
their own — a device is flushed at the moment its priority virtual writes it,
so a device shared by a 30 FPS and a 60 FPS virtual is transmitted at the
priority (fastest) virtual's cadence, and the slower virtual's pixels are
simply whatever was last written when the flush happens.

The websocket/UI preview is decoupled: `VIRTUAL_UPDATE`/`DEVICE_UPDATE`
events are rate-limited to `visualisation_fps` and downsampled to
`visualisation_maxlen` pixels before being base64'd to the frontend
[S630:ledfx/core.py#L315-L400].

## 3. Audio pipeline

Capture stack: **sounddevice (PortAudio)** `InputStream` with
`latency="low"`, `dtype=float32`, blocksize = `device_rate / 60`
[S630:ledfx/effects/audio.py#L866-L878]. Special sources plug in behind the
same callback interface: WASAPI loopback of the default output (preferred
default on Windows) [S630:ledfx/effects/audio.py#L322-L384], browser "WEB
AUDIO" over websocket, and "Sendspin" network audio servers
[S630:ledfx/effects/audio.py#L843-L864]. Considerable code (hundreds of
lines) deals purely with PortAudio device-index drift, hotplug recovery by
device *name*, and poisoned-WDM-KS reinit retries
[S630:ledfx/effects/audio.py#L51-L282,L892-L973] — a warning about how much
robustness work raw PortAudio demands.

**Fixed internal rate trick**: everything downstream runs at a pretend
`MIC_RATE = 30000 Hz` with `FFT_SIZE = 4096`; the callback resamples each
device block to `30000/60 = 500` samples with libsamplerate `sinc_fastest`,
downmixed to mono [S630:ledfx/effects/melbank.py#L20-L29]
[S630:ledfx/effects/audio.py#L1091-L1133]. The comment explains why: lying
about the rate increases bass frequency resolution (4096 bins over 15 kHz
instead of 22 kHz) and slightly reduces latency. Audio "frames" therefore
arrive at 60 Hz (`sample_rate` config default 60)
[S630:ledfx/effects/audio.py#L449].

**Per-block processing** (in the PortAudio callback thread!): NaN scrub →
volume via `aubio.db_spl` + ExpFilter → below `min_volume` gate the spectrum
is zeroed; otherwise a biquad pre-emphasis filter (three hand-tuned
coefficient sets keyed to melbank type) → `aubio.pvoc` phase vocoder for the
windowed FFT [S630:ledfx/effects/audio.py#L748-L768,L1147-L1178]. An optional
`delay_ms` (0-5000) is implemented as a bounded queue of blocks to sync with
laggy Bluetooth output [S630:ledfx/effects/audio.py#L790-L796,L1119-L1128].
Then all subscriber callbacks run synchronously in the callback thread
[S630:ledfx/effects/audio.py#L1138-L1141].

**Mel banks**: aubio is used throughout (`aubio.filterbank`, `pvoc`, `tempo`,
`onset`, `pitch`) — beat/onset/pitch detection is NOT custom. Three shared
melbanks of 24 bands each cover 20-350 Hz, 20-2000 Hz, 20-15000 Hz
(`MEL_MAX_FREQS`); they are global, not per-virtual, explicitly for
performance [S630:ledfx/effects/melbank.py#L32,L406-L412]. Seven selectable
frequency-warp curves; default `matt_mel` = `3700*log12(1+f/230)`, a custom
log curve that stretches bass and compresses highs
[S630:ledfx/effects/melbank.py#L264-L287]. Per melbank per block
[S630:ledfx/effects/melbank.py#L380-L403]:

1. `filterbank(fft)` → 24 float values;
2. `x ** power_factor` where `power_factor = tan(pi/4 * (peak_isolation+1))`
   — a tunable peak-isolation exponent (default peak_isolation 0.4 ≈ x²)
   [S630:ledfx/effects/melbank.py#L100-L108];
3. **auto-gain**: `mel_gain` ExpFilter (rise 0.99 / decay 0.01) tracks
   `max(gaussian_blur(banks))` and divides — slow-release AGC so quiet and
   loud tracks fill the same 0..1 range;
4. `mel_smoothing` ExpFilter (decay 0.7/rise 0.99) → `melbanks[i]`;
5. a "filtered" variant: `diff_filter.update(banks - common_filter.value)`
   — a high-pass over time that emphasizes transients → `melbanks_filtered[i]`.

All of this is float32/float64 numpy; nothing is quantized until the device
driver. Excerpt: `research/excerpts/S630-melbank-agc/melbank.py`.

**Derived features** (`AudioAnalysisSource`) computed once per audio frame
and memoized with `lru_cache` until `_invalidate_caches()` at the next block
[S630:ledfx/effects/audio.py#L1346-L1354]: aubio pitch (yinfft→MIDI), aubio
onset (hfc default), aubio tempo → `bpm_beat_now`; a custom
`volume_beat_now` (beat if low-band energy exceeds the 0.2 s rolling average
by 50%, with amplitude floor and 100 ms refractory)
[S630:ledfx/effects/audio.py#L1384-L1419]; `bar_oscillator` — a 0..4 sawtooth
phase-locked to aubio tempo ticks, interpolating between beats with
`time_since_beat / beat_period` [S630:ledfx/effects/audio.py#L1482-L1530];
and a 4-band `freq_power` (beat/bass/mids/high at 100/250/3000/10000 Hz cut
points) with ExpFilter smoothing [S630:ledfx/effects/audio.py#L1242-L1249,
L1421-L1447]. Excerpt: `research/excerpts/S630-beat-osc/audio.py`.

**How features reach effects**: `AudioReactiveEffect.activate()` subscribes
the effect to the audio source; on each audio frame the effect's
`audio_data_updated(data)` runs (in the audio callback thread, under the
effect's lock) and typically stashes filtered values on `self`; the render
thread later reads them [S630:ledfx/effects/audio.py#L1533-L1599]. The
`melbank(filtered=, size=)` helper slices the right shared melbank by the
virtual's frequency range and `np.interp`s it to pixel count, with all
selection indices cached [S630:ledfx/effects/audio.py#L1619-L1724].

**Latency budget**: one audio block ≈16.7 ms + FFT window (pvoc with 4096
window at hop 500 spans ~136 ms of history, dominating low-frequency
response) + effect renders at next virtual tick (0-16.7 ms at 60 FPS) +
protocol send. No end-to-end latency instrumentation exists in the code;
audio-to-light is roughly 2-3 frames plus window smear, and the `delay_ms`
knob only *adds* delay to match slow speakers.

## 4. Effect authoring

~70 effects live as one module each under `ledfx/effects/`, auto-discovered
by a `RegistryLoader` that imports the package and registers subclasses. Base
class `Effect` provides a voluptuous `CONFIG_SCHEMA` (blur, flip, mirror,
brightness, background color, diag) that children *extend*; schemas are
merged up the MRO and drive both validation and auto-generated UI
[S630:ledfx/effects/__init__.py#L273-L340]. Mixin bases add capabilities:
`AudioReactiveEffect` (subscribe/melbank helpers), `GradientEffect`
(gradient LUT + `apply_gradient(intensity)`), `TemporalEffect` (its own
per-effect animation thread!), `HSVEffect`, 2D/GIF bases.

Boilerplate per new effect is genuinely small — `Magnitude` is ~33 lines:
NAME/CATEGORY, a 1-key schema, `on_activate` (init state),
`config_updated` (precompute), `audio_data_updated` (grab a power value),
`render` (write `self.pixels`) [S630:ledfx/effects/magnitude.py#L1-L33].
This authoring surface is LedFx's best asset.

**Numeric model: float 0-255 RGB throughout, not 8-bit.** `self.pixels` is a
float64 numpy `(N,3)` array in 0..255 units. `get_pixels()` copies it and
applies flip → mirror (adjacent-max downsample of the doubled array, chosen
to avoid dimming/flicker) → additive background color → brightness multiply
→ Gaussian blur via `np.convolve` per channel with an `lru_cache`d kernel
[S630:ledfx/effects/__init__.py#L479-L547]. Quantization to uint8 happens
only inside device drivers (and the UI event path). There is no gamma
correction, no color calibration, and no dithering anywhere in the engine —
a float pipeline whose extra precision is thrown away at the very last
`astype(np.uint8)` truncation.

NumPy idioms available to authors: shared Gaussian kernel cache
(`_gaussian_kernel1d`, `lru_cache(1024)`), `fast_blur_pixels/array` with
mirrored-edge `smooth()`, vectorized `fill_rainbow` via `hsv_to_rgb`, and
`ExpFilter` (asymmetric attack/decay one-pole) from `effects/math.py` used
everywhere for envelopes [S630:ledfx/effects/__init__.py#L130-L270].

Concurrency: every effect has its own `threading.Lock`; `_render`,
`get_pixels`, `update_config`, and the audio callback all contend for it
[S630:ledfx/effects/__init__.py#L462-L468,L486]. Effects keep wall-clock
`self.passed` (time since last frame) for speed-independent animation
[S630:ledfx/effects/__init__.py#L563-L567]; `TemporalEffect` instead runs
its own thread at `speed * 10 Hz`, decoupled from the render thread that
samples `self.pixels` [S630:ledfx/effects/temporal.py#L17-L56].

## 5. Output drivers

All drivers implement `flush(data)` and are called synchronously from the
virtual's render thread; **there is no per-device pacing thread, send queue,
or rate limiter** — the virtual's sleep loop IS the pacing, and a slow/
blocking send stalls that virtual's rendering.

- **DDP** (`ddp.py`, default for modern WLED): 10-byte header
  `struct.pack("!BBBBLH", VER1|PUSH-on-last, seq 1-15, DATATYPE=0x0B,
  destination_id, byte_offset, length)`; payload is
  `data.astype(np.uint8).ravel()` chunked at 480 pixels/1440 bytes per UDP
  packet with only the final chunk carrying the PUSH flag
  [S630:ledfx/devices/ddp.py#L25-L36,L113-L204]. Clean, minimal, offset-based
  — the best protocol implementation in the codebase. Connection loss is
  detected via OSError on send and reported by event, with auto-recovery
  logging [S630:ledfx/devices/ddp.py#L71-L110].
- **UDP realtime (WLED legacy)** (`udp.py` + `packets.py`): builds
  WARLS/DRGB/DRGBW/DNRGB packets; `adaptive_smallest` compares the changed-
  pixel count to choose WARLS (index+RGB per changed pixel) vs DRGB whole-
  frame [S630:ledfx/devices/udp.py#L104-L121]. `minimise_traffic` suppresses
  duplicate frames but still sends a keepalive at half the WLED timeout so
  the device doesn't fall back to its local effect
  [S630:ledfx/devices/udp.py#L148-L166].
- **E1.31/sACN** (`e131.py`): delegates to the `sacn` library with
  `manual_flush=True`; flush slices the flattened channel array across
  universes (universe_size default 510, channel_offset supported) and
  round-trips through `dmx_data.tolist()` because the library demands Python
  ints — a per-frame numpy→list conversion [S630:ledfx/devices/e131.py#L120-L172].
- **Art-Net** (`artnet.py`): `StupidArtnet` library; adds pre/post-amble
  bytes, per-device pixel chunking, RGB reorder and RGBW white-channel
  synthesis via an `OutputMode` helper; skips the frame if the device lock
  is contended ("we have a mutex deadlock between devices and virtuals
  protections") [S630:ledfx/devices/artnet.py#L171-L186].

**Bit depth**: every network driver quantizes with `astype(np.uint8)` —
truncation, not rounding, no dithering, no gamma. The single 16-bit path is
LIFX, whose protocol is natively 16-bit HSBK
(`(h*65535).astype(np.uint16)`) [S630:ledfx/devices/lifx.py#L87-L89]. DDP's
16-bit-per-channel capability is unused (DATATYPE hardcoded to 8-bit RGB
[S630:ledfx/devices/ddp.py#L36]). RGBW exists only as per-driver hacks
(Art-Net white funcs, DRGBW), not as a first-class pipeline concept
[S630:ledfx/effects/__init__.py#L526-L546] (TODO comments admit this).

## 6. Transitions / blending

Transitions are a per-virtual crossfade between the outgoing effect (kept
alive as `_transition_effect`, still rendering every frame) and the incoming
one. On `set_effect`, `transition_frame_total = refresh_rate *
transition_time` and a frame counter advances each render; `weight =
counter/total` [S630:ledfx/virtuals.py#L626-L646,L913-L941]. Both frames are
fully rendered each tick, then blended in-place by one of seven numpy
functions in a 112-line `Transitions` class: Add (weighted sum), Dissolve
(random per-pixel mask vs weight), Push/Slide (`np.roll` + slice copy), Iris
(center-out index mask), Through White/Black (clip toward 255/0 then back)
[S630:ledfx/transitions.py#L1-L131]. Transitioning *to nothing* uses a
`DummyEffect` that renders zeros so the same path handles clear-with-fade
[S630:ledfx/virtuals.py#L687-L717]. Cost: 2x render for the transition
duration — simple and correct, fine at these pixel counts.

Related one-off overlays ("oneshots", e.g. flash-on-trigger from
integrations) are applied per segment after the effect frame is assembled
[S630:ledfx/virtuals.py#L1020-L1028,L1094-L1098].

## 7. Honest engineering assessment

What LedFx gets right: the Device/Virtual/Effect separation, the tiny
per-effect authoring surface, and an audio feature layer (AGC'd melbanks +
beat oscillator) that makes naive effects look good. Its signature quality —
"any effect looks musical" — comes from the melbank pipeline (section 3),
not from the effects themselves.

Design decisions that hurt it, with code:

1. **Threads everywhere, no unified scheduler.** One thread per virtual
   [S630:ledfx/virtuals.py#L970-L973], plus another per TemporalEffect
   [S630:ledfx/effects/temporal.py#L36-L56], plus the PortAudio callback
   thread running all effect audio callbacks, plus asyncio for HTTP —
   coordinated by per-virtual, per-effect, and per-device locks. The
   comments betray the pain: "All of this requires thread lock management
   that's a bit unwieldy" [S630:ledfx/virtuals.py#L746-L779]; Art-Net's
   flush skips frames because "we have a mutex deadlock between devices and
   virtuals protections" [S630:ledfx/devices/artnet.py#L176-L179]. Under
   Python's GIL the threads buy no parallelism for the numpy-light parts and
   cost real complexity.
2. **Audio DSP in the capture callback.** Resample, FFT, three melbanks,
   pitch/onset/tempo, and every subscribed effect's `audio_data_updated` run
   inside the PortAudio callback [S630:ledfx/effects/audio.py#L1091-L1141].
   One slow effect callback risks input overflow for all.
3. **No output pacing/compensation.** Sleep-based loop with no accumulated-
   error correction (section 2); device sends inline in the render thread;
   no notion of frame deadline, no jitter measurement.
4. **Precision thrown away at the edge.** Full float pipeline, then
   `astype(np.uint8)` truncation with no gamma, no dithering, no 16-bit DDP
   (section 5). All the smoothness of the float melbank work is quantized
   to 8-bit steps at the wire.
5. **Mutable-config sprawl.** Config dicts are mutated in place all over
   (`virtual_cfg` references into `self._ledfx.config`, `save_config`
   sprinkled through business logic, e.g.
   [S630:ledfx/virtuals.py#L1339-L1361]); `Virtuals` is a singleton with a
   `reset_for_core` escape hatch acknowledging stale-state bugs across
   restarts [S630:ledfx/virtuals.py#L1747-L1782].
6. **Optimizations as opt-in flags instead of fixes.** `complex_segments`
   (precompiled remap, "13x") is a per-virtual bool the user must enable
   [S630:ledfx/virtuals.py#L46-L50] — the fast path and slow path both live
   forever, doubling flush code paths (plus separate calibration branches).
7. **cached_property + manual invalidation as the dependency system.**
   `invalidate_cached_props()` lists of attribute names on both Virtual and
   Device [S630:ledfx/virtuals.py#L329-L340]
   [S630:ledfx/devices/__init__.py#L457-L461] are effectively a hand-rolled,
   easy-to-miss dependency graph; several bugs the comments describe
   (poisoned configs, zero-segment virtuals crashing startup) trace back to
   this state management [S630:ledfx/devices/__init__.py#L473-L513].
8. **PortAudio device-identity swamp**: ~400 lines of audio.py handle index
   drift, hotplug, and reinit (section 3) — inherent to PortAudio's
   index-based API, and a cost any PortAudio-based design inherits.

## What pewpew should steal

- **The melbank normalization chain** (excerpt S630-melbank-agc): custom log
  frequency warp, `tan`-mapped peak-isolation exponent, slow-release AGC by
  dividing by an ExpFilter of the blurred max, plus the transient-emphasis
  "filtered" variant. This is the distilled, battle-tested core of LedFx's
  audio look.
- **Fixed pretend sample rate** (30 kHz) + resample-at-ingest: decouples all
  DSP constants from device hardware and buys bass resolution
  [S630:ledfx/effects/melbank.py#L20-L29].
- **A small number of shared melbanks at tiered frequency ranges**
  (350/2000/15000 Hz), sliced+interpolated per consumer, instead of per-
  consumer FFT work [S630:ledfx/effects/melbank.py#L406-L412].
- **The bar/beat oscillator** (excerpt S630-beat-osc): continuous 0..4 phase
  interpolated between aubio tempo ticks — a far better effect input than a
  beat boolean.
- **The effect authoring contract**: declarative schema → auto UI,
  `on_activate`/`config_updated`/`audio_data_updated`/`render` lifecycle,
  common flip/mirror/blur/brightness applied by the base class
  (adjacent-max mirror trick included) [S630:ledfx/effects/__init__.py#L479-L547].
- **Virtual/segment mapping model** including span-vs-copy, invert-by-
  negative-stride, pixel grouping, and gap devices — proven UX for mapping
  effects onto multi-device installations.
- **WLED-family protocol details**: DDP chunking with PUSH-on-last;
  `adaptive_smallest` WARLS/DRGB selection; keepalive-at-half-timeout when
  suppressing duplicate frames.

## What to avoid

- Thread-per-virtual + thread-per-temporal-effect + DSP in the audio
  callback; use one paced render scheduler and move DSP out of capture.
- Sleep-based pacing without deadline/error correction.
- 8-bit truncation at the driver boundary with no gamma/dither; keep
  precision to the wire (DDP supports 16-bit; WLED gamma exists).
- Singleton registries with mutable shared config and manual cache
  invalidation lists.
- Dual slow/fast code paths behind user-facing performance flags.
- GPL-3.0: code cannot be copied into a permissively-licensed pewpew;
  reimplement from the documented algorithms.

## Open questions

- The "13x" complex_segments speedup is asserted only in a code comment
  [S630:ledfx/virtuals.py#L1130]; no benchmark exists in-repo. Unverified.
- Why `complex_segments` remains opt-in (correctness concern with copy mode
  and calibration, or just caution?) — undocumented.
- End-to-end audio→light latency is uninstrumented; my ~2-3 frame + FFT
  window estimate in section 3 is derived from block sizes, not measured.
- Whether the priority-virtual flush rule can starve a lower-rate virtual's
  pixels on a shared device (write-then-no-flush windows) — the code permits
  it [S630:ledfx/devices/__init__.py#L180-L194]; no test covers it.
- `sendspin` network-audio subsystem and `nowplaying` providers were not
  read in depth (peripheral to pewpew's questions).
