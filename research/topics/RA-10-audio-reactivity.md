# RA-10: Audio reactivity

Last researched: 2026-07-03
Status: draft
S-ID block: S450–S499 (fragment: S451+)

## Key questions

1. What exactly is LedFx's DSP chain (mel banks? aubio?), how are effects bound to audio features, and what latency does it achieve?
2. What does WLED-MM audioreactive do (GEQ, beat detection, UDP sound sync, mic vs line-in), and what is reusable?
3. Is Python realtime audio viable on a host: capture latency (sounddevice/pyaudio), aubio vs librosa realtime, FFT/mel cost, beat tracking (BTrack, madmom status)?
4. What end-to-end latency budget makes lights "feel synced," per practitioners?
5. Beyond beats: tempo tracking, structure detection, loudness normalization — what is practical realtime?
6. Sensor (IMU) reactivity for wearables — Pixelblaze sensor-board precedent.
7. Cited recommendation for pewpew's audio stack.

## Findings

### LedFx DSP chain

License GPL-3.0; active — v2.1.9 released 2026-05-18, commits to main on 2026-07-03 [S011]. Form factor: host-only (desktop/laptop/SBC Python app); pairs with WLED/E1.31/DDP endpoints. Read at pin `LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792` (main, 2026-07-03); key files `ledfx/effects/audio.py` and `ledfx/effects/melbank.py` [S011].

**Capture.** `sounddevice` (PortAudio) `InputStream` with `latency="low"` and `blocksize = device_rate / sample_rate` where `sample_rate` is the *analysis* frame rate, default 60 — i.e. one audio hop every ~16.7 ms [S011:ledfx/effects/audio.py#L866-L880]. Each hop is resampled to a fixed internal rate `MIC_RATE = 30000 Hz` with `samplerate` (libsamplerate) `sinc_fastest` [S011:ledfx/effects/audio.py#L880, L1098-L1104]. The 30 kHz internal rate is deliberate: "I've forced fft to use mic rate of 30000Hz even if mic is actually ~40000Hz. This increases frequency resolution a lot and reduces latency a bit, improved resolution is noticable for bass" [S011:ledfx/effects/melbank.py#L22-L26]. A `delay_ms` option (0–5000 ms, queue of hops) delays LedFx's *output* to sync with laggy audio sinks ("Useful for Bluetooth devices") — i.e. in practice the light pipeline is faster than Bluetooth audio [S011:ledfx/effects/audio.py#L459-L463].

**Per-hop DSP (in the audio callback thread).** (1) NaN scrub; (2) volume estimate via `aubio.db_spl` smoothed by an exponential filter, gating everything below `min_volume` (default 0.2) to a null spectrum; (3) pre-emphasis biquad (`aubio.digital_filter`, coefficients chosen per melbank `coeffs_type`) to balance lows vs highs; (4) `aubio.pvoc` phase vocoder producing a windowed FFT — `FFT_SIZE = 4096` (hardcoded), hop 500 samples at 30 kHz [S011:ledfx/effects/audio.py#L748-L786, L1150-L1185; melbank.py#L28-L29]. Note the implied analysis window is 4096/30000 ≈ 137 ms — good bass resolution (~7.3 Hz/bin) at the cost of temporal smearing; the 60 Hz hop keeps *reaction* latency low even though the window is long.

**Melbanks.** Three parallel mel-style filterbanks over the same spectrum, with max frequencies 350 / 2000 / 15000 Hz (lows/mids/highs), default 24 bands each, built with `aubio.filterbank` [S011:ledfx/effects/melbank.py#L32, L406-L432]. Ten selectable coefficient types (`triangle`, `bark`, `slaney`, `mel`, `htk`, `scott`, `scott_mel`, `matt_mel` (default), `fixed`, `fixed_simple`) — the custom `matt_mel`/`scott_mel` curves are community-tuned perceptual variants, a lineage that traces back to Scott Lawson's audio-reactive-led-strip [S011:ledfx/effects/melbank.py#L59-L64, L111-L346].

**Analysis features (aubio).** An `AudioAnalysisSource` subscribes per-hop computations: melbanks, `aubio.pitch` (default `yinfft`, MIDI units), `aubio.onset` (default `hfc`), `aubio.tempo` (beat prediction → `bpm_beat_now()`), a `bar_oscillator()` (float 0–4, position within a 4-beat bar, phase-accurate between detected beats but with no downbeat detection), a `volume_beat_now()` energy-beat detector (sum of the lows-melbank below ~100 Hz vs a 0.2 s rolling history; fires on ≥50% power jump, amplitude ≥0.5, ≥0.1 s refractory — "optimised... from the original implementation in systematic_leds"), and `freq_power` — four ExpFilter-smoothed band powers named beat/bass/mids/high with edges at 100/250/3000/10000 Hz [S011:ledfx/effects/audio.py#L1197-L1470].

**Effect-to-feature binding.** Pull model with per-hop cache invalidation. Effects subclass `AudioReactiveEffect`, which subscribes an `audio_data_updated(audio)` callback; features are computed lazily via `lru_cache`-wrapped methods, all caches cleared at the start of each hop — so only features an active effect actually queries are computed, once, and shared across effects [S011:ledfx/effects/audio.py#L1345-L1360, L1534-L1600]. Effects declare which scalar drives them via `POWER_FUNCS_MAPPING` ("Beat"/"Bass"/"Lows"/"Mids"/"High" → `*_power()` methods) exposed as a schema dropdown, and each *virtual* (output surface) carries a `frequency_range` that selects and slices/interpolates the appropriate melbank — feature binding is thus per-effect-config, not hardcoded [S011:ledfx/effects/audio.py#L1543-L1549, L1620-L1680].

**aubio fork.** Upstream aubio's last release is 0.4.9 (2019-02-27), though the repo still gets occasional commits (last 2026-04-10) [S452]. LedFx maintains `aubio-ledfx` (GPL-3.0, last push 2025-12-07) to ship maintained wheels for modern Pythons [S451].

**Measured latency.** No official end-to-end latency benchmark found in LedFx docs; the structural floor is one 16.7 ms hop + PortAudio "low" input latency + effect render + network transport. Third-party descriptions cite "~16 ms" audio-to-LED, which matches the hop size but is not a measured end-to-end figure [S011][NEEDS-VERIFICATION].

### WLED-MM audioreactive

License EUPL-1.2; the audioreactive usermod now lives in its own repo `MoonModules/WLED-AudioReactive-Usermod`, pulled into WLED-MM as a PlatformIO lib dep ("WLEDMM audioreactive usermod, licensed under EUPL-1.2" in platformio.ini) [S004][S453]. Active: WLED-MM v14.7.1 released 2026-01-13, commits 2026-07-01; usermod repo pushed 2026-06-20 [S004][S453]. Form factor: on-device (ESP32 family) — the whole point is audio analysis on the controller itself; wearable-capable if the wearable runs an ESP32.

**Capture / inputs.** ESP32 I2S at `SAMPLE_RATE = 22050 Hz`, `samplesFFT = 512` → 23.2 ms per sample batch, ~43 Hz/bin [S453:audio_reactive.h#L366-L409]. A compile option enables a sliding window with 50% overlap (`FFT_USE_SLIDING_WINDOW`), cutting effective FFT cadence to ~12 ms [S453:audio_reactive.h#L38, L371-L377]. FFT runs in its own FreeRTOS task, priority tunable relative to the network task [S453:audio_reactive.h#L48-L52]. Input classes: I2S digital mics (INMP441, ICS-43434 — recommended), PDM mics (SPM1423; classic ESP32 and S3 only, with known IDF bugs on S3/C3), analog ADC mics (MAX4466/MAX9814 — "not recommended"), and line-in via I2S ADC chips (CS5343, PCM1808, ES7243 — "Best Option") [S450][S453:audio_source.h#L296-L308].

**DSP.** arduinoFFT (float) with windowing tuned for "sharper peaks" (`FFT_PREFER_EXACT_PEAKS`); per-microphone "pink noise" spectral-tilt correction tables (profiles for line-in, INMP441, ICS-43434, SPM1423, user-defined, flat) applied before major-peak detection; selectable post-scaling (sqrt default, log, linear); AGC with three presets (normal/vivid/lazy) plus squelch/noise gate that decays the GEQ to zero when closed [S453:audio_reactive.h#L38-L59, L226-L330, L151-L238, L885-L892].

**GEQ.** 16 fixed channels (`NUM_GEQ_CHANNELS 16`, "Don't change !!"), mapped from FFT bins ~43 Hz to ~9.3 kHz with hand-tuned band edges ("1 kHz should always be the center") and damping on the top bands to avoid aliasing contamination; effects consume `fftResult[16]` as uint8 per channel [S453:audio_reactive.h#L147-L176, L837-L882].

**Beat detection is crude.** The maintainers' own comment: "this code continuously triggers while volume in the selected bin is above a certain threshold. So it does not detect peaks - it detects volume in a frequency bin. Poor man's beat detection" — `samplePeak` fires when a chosen FFT bin exceeds a user threshold with a 100 ms refractory; an alternative FFT_MajorPeak-based detector is `#if 0`'d out as "Not much better" [S453:audio_reactive.h#L1074-L1100]. There is no tempo tracking. Takeaway: WLED-MM's strength is the GEQ + AGC + mic-profile plumbing, not rhythm analysis.

**UDP sound sync.** One node analyzes, others receive: modes off/send/receive/receive+local-fallback, default port 11988 [S453:audio_reactive.h#L134-L137, L1212]. V2 packet is a packed 44-byte struct, header "00002": sound pressure (8.8 fixed), raw + smoothed sample (AGC-dependent), samplePeak flag, rolling frameCounter for duplicate/out-of-order detection, 16 GEQ bytes, zero-crossing count, FFT magnitude and major-peak frequency [S453:audio_reactive.h#L1165-L1178]. Receivers poll every 18 ms (23 ms batch time minus 5 ms network margin) [S453:audio_reactive.h#L1193]. This is the de-facto LAN audio-feature-distribution format among WLED-family nodes; whether LedFx can emit it directly is unconfirmed (code-reading queue item) [NEEDS-VERIFICATION]. Architecturally notable for pewpew: the packet ships *features*, not audio — tiny, latency-tolerant, multicast-friendly.

**Upstream WLED** (AKA "SR merged subset"): upstream `Aircoookie/WLED` carries a reduced audioreactive usermod (same GEQ/sync lineage, fewer mic profiles and options); WLED-MM is "~2 years ahead of upstream on audio" [S004].

### Python realtime audio viability

**Capture.** Both `pyaudio` and `sounddevice` are PortAudio bindings; `sounddevice` (MIT, actively maintained) is the modern choice — numpy-native callbacks, `latency="low"` hint, explicit `blocksize` [S458]. LedFx proves the pattern in production: a 60 Hz callback (16.7 ms blocks) feeding a lock-protected analysis chain works reliably across Windows/macOS/Linux, including on Raspberry Pi [S011][S012]. Capture latency is essentially one blocksize plus driver buffer: with 256–1024-sample blocks at 44.1/48 kHz, 6–23 ms.

**FFT/mel cost is negligible.** Measured on this machine (arm64, numpy 2.0.2): a windowed 4096-point `np.fft.rfft` costs ~74 µs/call and a 24-band mel matmul ~3 µs — under 0.5% of a 16.7 ms hop budget (bench script, this repo's research run, 2026-07-03). Even a 10× slower SBC leaves >95% headroom. Spectral analysis is not the bottleneck for a Python host engine; capture buffering and transport are.

**aubio.** C library with Python bindings — onset, tempo (predictive beat), pitch, mel filterbanks, all streaming/causal by design. Upstream is effectively dormant for packaging purposes (last release 0.4.9, 2019-02-27; sporadic commits, last 2026-04-10) [S452]; PyPI `aubio` is still 0.4.9 [S452]. The practical route is LedFx's `aubio-ledfx` fork, which exists precisely to ship wheels for current Pythons (GPL-3.0, pushed 2025-12-07) [S451]. GPL-3.0 is a licensing constraint to note.

**librosa.** v0.11.0 on PyPI; batch-oriented — its onset/beat functions are designed for complete signals, and maintainers have long pointed users elsewhere for live streams (`librosa.stream` is for fixed-length buffered *file* reading; real-time analysis is an explicitly acknowledged non-goal in issue discussions) [S456]. Fine for offline pre-analysis of tracks (structure, tempo maps), wrong tool for the live path.

**Beat tracking options.**
- *aubio.tempo*: causal, cheap, no neural nets; predicts next beat from onset periodicity. What LedFx ships [S011][S451].
- *BTrack* (Adam Stark): C++ real-time beat tracker with Python module; GPL-3.0; repo pushed 2026-02-26 but essentially a stable/legacy academic codebase [S455].
- *madmom* (`DBNBeatTracker --online`): RNN + DBN, state-of-the-art accuracy offline; online mode exists but users report ~100–200 ms perceived lag, and the project is minimally maintained (last commit 2024-08-25, PyPI 0.16.1 from 2018, 80 open issues; repo metadata touched 2026-03) [S454]. Historically painful to install on new Pythons (Cython/numpy pinning).
- *BeatNet* (CRNN + particle filtering, ISMIR 2021): joint beat/downbeat/tempo/meter in a real streaming mode, commonly cited at sub-50 ms latency and recommended over madmom for live use [S457]. CC-BY-4.0 (a code-as-CC oddity), PyPI 1.1.3 (2023-11-28), repo pushed 2026-04-13 — usable but not vigorously maintained, and it drags in PyTorch [S457].

**Bottom line.** A Python host can comfortably run capture → FFT → melbank → band powers → energy-beat at 60 Hz with aubio-or-numpy-level tooling (LedFx is the existence proof [S011]); neural beat/downbeat tracking (BeatNet) is the step up if downbeat/meter awareness is wanted, at the price of a PyTorch dependency [S457].

### Latency targets & end-to-end budget

**Perceptual thresholds.** The best-studied numbers are ITU-R BT.1359-1 (A/V sync for broadcast): detectability at about +45 ms (audio leads vision) to −125 ms (audio lags), acceptability at about +90 ms to −185 ms [S459]. Lights reacting to music are the "audio leads" case — the light event arrives *after* the sound — which is the direction humans are *most* sensitive to, so the relevant edges are ~45 ms (detectable) and ~90 ms (objectionable) [S459]. Beat-flash content is more transient-y than lip sync, so practitioner systems aim well under that: LedFx runs a 16.7 ms analysis hop [S011], WLED-MM produces a fresh GEQ every 23 ms (12 ms with sliding window) and receivers poll sync at 18 ms [S453], and Scott Lawson's original visualizer documented 60 FPS as the point where "higher framerates improve responsiveness and reduce the latency" [S460]. A practical target: **≤50 ms end-to-end, with ≤30 ms felt as "tight"** [S459][NEEDS-VERIFICATION on the 30 ms figure — folklore consensus, no controlled study found].

**Budget for a pewpew-style host pipeline** (capture → DSP → render → transport → LED):
| Stage | Typical | Notes |
|---|---|---|
| Capture block | 8–17 ms | one blocksize; LedFx uses 16.7 ms [S011] |
| Driver/OS buffer | 2–10 ms | PortAudio `latency="low"` [S458] |
| DSP (FFT+mel+features) | <1 ms | measured ~0.1 ms in numpy (this doc) |
| Effect render | 1–5 ms | frame-rate dependent, overlaps next hop |
| Transport (WiFi UDP/DDP) | 2–10 ms | LAN; jitter matters more than mean |
| LED strip refresh | 1–10 ms | 30 µs/LED WS281x; 300 LEDs ≈ 9 ms |
| **Total** | **~15–50 ms** | comfortably inside 45 ms if blocks are small |

The dominant terms are capture blocksize and WiFi jitter — not computation. Corollary: Bluetooth *audio playback* latency (100–200 ms) is far larger than the light pipeline, which is why LedFx offers `delay_ms` up to 5000 ms to *slow the lights down* to match delayed speakers [S011]. Any pewpew design should include the same signed-delay knob.

### Latency targets & end-to-end budget
<!-- TODO -->

### Beyond beats: tempo, structure, loudness

**Tempo tracking (live).** aubio.tempo gives a causal BPM estimate and next-beat prediction cheaply [S451][S452]; BeatNet adds downbeat and meter in streaming mode [S457]. LedFx's `bar_oscillator` shows the useful abstraction: a continuous 0–4 bar-phase ramp, phase-locked to detected beats even when absolute beat-1 is unknown — effects can sweep, not just flash [S011:ledfx/effects/audio.py#L1480-L1500]. Downbeat detection remains the weak point of non-neural stacks; LedFx explicitly documents "no attempt to guess which beat is the first in the bar" [S011].

**Structure detection (sections, drops).** No production LED system does this live. Realistic pattern: *offline pre-analysis* of known tracks (librosa segmentation / self-similarity, or neural structure analyzers) producing a cue map that a player fires in sync — i.e. structure becomes sequencing metadata, not a live DSP feature [S456]. For unknown live audio, the practical proxies are long-window energy/novelty trends (build-up/drop heuristics), which is exactly what freq-band ExpFilters with asymmetric attack/decay give you [S011].

**Loudness normalization.** Live path: WLED-MM's AGC (three presets + squelch) is the on-device answer [S453]; LedFx normalizes implicitly via per-band exponential filters and a `min_volume` gate [S011]. For perceptual loudness (EBU R128 / LUFS) the Python reference is `pyloudnorm` (MIT, pushed 2026-01-04) — but R128 gating is block-based (400 ms) and suits offline/slow AGC, not per-hop scaling [S461]. Recommended split: fast AGC on band energies for reactivity; slow LUFS-style gain riding (seconds) so quiet tracks still fill the visual dynamic range [S453][S461].

### Sensor reactivity for wearables (IMU)

**Pixelblaze Sensor Expansion Board** (Ben Hencke) is the design precedent: a dedicated STM32F0 coprocessor doing fixed-point FFT, streaming a compact frame over 115200-baud serial — header "SB1.0", 32×uint16 frequency magnitudes (37 Hz–10 kHz, "designed to work in very loud environments"), energy average, max-frequency magnitude + Hz, 3-axis 16 g accelerometer, ambient light, 5 analog pot inputs, "END" [S462:README.md]. Frame read takes ~8–9 ms in the Arduino library — sensor data arrives at pattern-frame rate, not audio rate [S463]. Firmware MIT, hardware CC-BY-SA-4.0 [S462]. Licenses and simplicity make this protocol directly borrowable.

**Architectural lesson for pewpew:** the sensor board treats audio + IMU identically — *both are just low-rate feature streams into the pattern engine* (Pixelblaze patterns read `frequencyData[]`, `energyAverage`, `accelerometer[]` as globals) [S013][S462]. A pewpew wearable can do the same: whatever produces features (on-board mic FFT, IMU, or WLED-style UDP sync frames from a host) normalizes into one "sensor frame" struct consumed by patterns. IMU-driven effects (orientation-gravity color, shake energy) need only ~50–100 Hz accel sampling and no DSP beyond smoothing — far cheaper than audio [S462].

### Recommendation for pewpew

1. **Host tier: adopt the LedFx-shaped pipeline** — sounddevice capture at a fixed analysis hop (start at 60 Hz), resample to a fixed internal rate, one shared windowed FFT, 2–3 mel-style filterbanks plus a handful of named scalar features (volume, beat/bass/mids/high power, onset, beat-now, bar-phase), computed lazily and cached per hop [S011]. This is proven, and the costs are trivial in numpy (measured <0.2 ms/hop, this doc). Implement the melbank/energy-beat math natively in numpy rather than importing GPL aubio wholesale if pewpew wants a non-GPL license; use `aubio-ledfx` only if GPL-3.0 is acceptable [S451].
2. **Feature bus, not audio bus:** distribute *features* to render nodes, not samples. Speak WLED's audio-sync V2 UDP format (44-byte packed struct, port 11988) as a first-class output so every WLED/WLED-MM node on the LAN reacts for free, and use the same struct locally as the pattern-engine input [S453].
3. **Beats:** ship aubio-style tempo + LedFx-style energy-beat as default; add BeatNet behind an optional extra for downbeat/meter when PyTorch is present [S457]. Skip madmom (unmaintained, install pain) [S454] and librosa on the live path (batch-oriented) [S456].
4. **Latency:** budget ≤45 ms audio-to-photon (ITU detectability edge for lagging visuals) and expose a signed delay knob (±ms) for Bluetooth-delayed playback, as LedFx does [S459][S011].
5. **Wearable tier:** treat audio and IMU as one normalized sensor-frame input, Pixelblaze-sensor-board style; on-device 16-band GEQ à la WLED-MM if the wearable has a mic, or receive the V2 sync packet over WiFi [S453][S462].

## Verdicts

- **LedFx** — *stable/ascendant*: v2.1.9 (2026-05-18), daily commits, the reference Python audio-LED architecture [S011].
- **WLED-MM audioreactive** — *stable*: actively maintained (usermod repo pushed 2026-06-20), best-in-class embedded GEQ/AGC/sync; beat detection deliberately primitive [S453].
- **aubio (upstream)** — *waning*: no release since 0.4.9 (2019); survives via the aubio-ledfx fork (pushed 2025-12) [S451][S452].
- **librosa** — *stable but out of scope for live*: healthy releases (0.11.0) yet batch-oriented by design [S456].
- **madmom** — *waning*: last commit 2024-08, PyPI stuck at 0.16.1 (2018), install friction on modern Pythons [S454].
- **BeatNet** — *stable niche*: the practical real-time downbeat option; light maintenance (PyPI 2023, repo pushed 2026-04) and a PyTorch dependency [S457].
- **BTrack** — *waning/legacy*: correct causal design, but a dormant academic codebase [S455].
- **Pixelblaze sensor-board pattern** — *stable*: MIT protocol, unchanged for years, still shipping; ideal wearable precedent [S013][S462].

## Code-reading queue

1. **LedFx melbank + effect binding** — `LedFx/LedFx@566de0f`, `ledfx/effects/melbank.py` (the ten coeffs types, esp. `matt_mel`) and 2–3 audio effects (e.g. `magnitude`, `scan`, `blade_power_plus`): exactly how do effects map scalar/melbank features to pixels, and which filters get duplicated per effect? Answers what pewpew's feature-API surface must expose. [S011]
2. **WLED-MM `postProcessFFTResults` + AGC** — `MoonModules/WLED-AudioReactive-Usermod@8d988e9`, `audio_reactive.h` L640–L1000: the exact AGC preset math and pink-noise scaling; answers how to make a 16-band GEQ look right on a mic without manual tuning. [S453]
3. **LedFx UDP audio-sync transmitter** — does LedFx emit the WLED V2 sync packet, and from which module (`sendspin`? `ledfx/utils`?); answers whether pewpew can interop-test against LedFx as a feature source. [S011][S453]
4. **BeatNet streaming mode** — `mjhydri/BeatNet`, `BeatNet.py` particle-filter loop: measure actual hop latency and CPU on a Pi-class host; answers whether downbeat tracking fits the wearable-host budget. [S457]
5. **Pixelblaze sensor-board firmware FFT** — `simap/pixelblaze_sensor_board@15b3d27`, `src/main.c` + `fix_fft.c`: window/averaging strategy for the 32 bands on an M0; answers what a pewpew wearable coprocessor (or RP2040 core-1) would need. [S462]

## Open questions

1. **Measured end-to-end LedFx latency** — no published capture→LED measurement found; settle with a photodiode + loopback bench (play a click, measure LED-on delta) once pewpew has hardware. [S011][NEEDS-VERIFICATION]
2. **"Feels synced" threshold for beat-flash content specifically** — ITU BT.1359 numbers are for speech/lip-sync; transient flashes may be stricter. No controlled study found; a small user test (variable inserted delay) would settle it. [S459]
3. **WLED audio-sync V2 vs upstream WLED 0.15+ sync format drift** — does upstream still parse the MM V2 packet byte-for-byte, and is there a V3 in flight? A read of upstream `usermods/audioreactive/audio_reactive.h` (clone available) settles it.
4. **madmom licensing** — code BSD-ish but pretrained models carry a non-commercial clause; exact terms unverified (GitHub reports NOASSERTION). Only matters if madmom is revisited. [S454][NEEDS-VERIFICATION]
5. **BeatNet CPU on SBCs** — "sub-50 ms" latency claims are from the paper's context; no Raspberry Pi benchmark found. [S457][NEEDS-VERIFICATION]
6. **LedFx "sendspin"** — a new (2026) audio-over-network subsystem appearing in `audio.py`; purpose and protocol undocumented in what was read; worth a look during code-reading item 3. [S011]
