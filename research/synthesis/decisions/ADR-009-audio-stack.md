# ADR-009: Audio stack — LedFx-shaped features in NumPy, features-not-samples distribution

Status: Proposed (2026-07-03)

## Context

Audio reactivity needs a capture→features pipeline on the host and a way to
get features to patterns and remote nodes within the audio-to-photon
budget — ≤50 ms hard ceiling (P-4), ≤45 ms engine design budget (R-4). LedFx is the production-proven Python reference but is
GPL-3.0 and runs its DSP inside the audio callback; aubio (its DSP core) is
GPL and upstream-dormant. Compute is not the constraint — FFT+mel measured
<0.2 ms/hop in NumPy.

## Decision

- **Capture**: sounddevice (PortAudio) at a fixed 60 Hz analysis hop,
  resampled to a fixed internal rate. The callback only copies into a ring
  buffer; **analysis runs on the render clock** (ADR-010), not in the
  callback.
- **Features**: one shared windowed FFT; 2–3 mel-style filterbanks; named
  scalars (volume, beat/bass/mids/high power, onset, beat-now, bar-phase
  0–4) computed lazily, cached per hop, shared across all consumers.
- **All DSP math reimplemented in NumPy** from the documented findings — no
  GPL imports (aubio-ledfx excluded; ADR-012).
- **Distribution: features, never samples.** Patterns see one normalized
  read-only sensor frame (melbanks + scalars + IMU, W-8). Emit and consume
  the WLED audio-sync V2 packet (44 bytes, port 11988) for LAN interop.
- **Beats**: causal tempo + energy-beat default; BeatNet as an optional
  extra (downbeat/meter, PyTorch dependency).
- **Latency**: ≤45 ms engine design budget within the ≤50 ms hard ceiling
  (P-4/R-4); signed delay knob (±ms, up to seconds) for
  Bluetooth-delayed speakers. Fast AGC on band energies + slow LUFS-style
  gain riding. Live song-structure detection is out of scope.

## Consequences

- Every WLED/WLED-MM node on the LAN reacts to pewpew's analysis for free
  (V2 packet); the wearable consumes the same struct or its own mic GEQ.
- Reimplementing melbank/beat math costs implementation effort that
  importing aubio would not — the price of the license posture.
- Whether ~30 ms (not 45) is the real "feels tight" edge is folklore —
  prototype item #6 (user test).

## Evidence

- [S630:ledfx/effects/melbank.py#L20-L29]
  [S630:ledfx/effects/audio.py#L1346-L1354] LedFx's proven shape: 60 Hz
  hop, fixed internal rate, shared FFT, lazily-cached melbanks/features —
  the architecture adopted.
- [S630:ledfx/effects/audio.py#L1138-L1141] LedFx runs DSP and all
  subscriber callbacks in the PortAudio callback thread — the structural
  flaw we fix.
- [S451][S452] aubio-ledfx is GPL-3.0; upstream aubio has had no release
  since 0.4.9 (2019) — both licensing and maintenance argue for
  reimplementation.
- [S453] WLED-MM's audio-sync V2: 44-byte feature packet at ~43 Hz — the
  de-facto LAN feature-distribution format; ships features, not audio.
- [S204][S462] Pixelblaze sensor board: features arrive pre-chewed as
  pattern variables; patterns never process raw audio — the consumption
  model (W-8).
- [S459] ITU-R BT.1359-1: detectability ≈ +45 ms when audio leads — the
  budget's basis (R-4).
- [S630:ledfx/effects/audio.py#L459-L463] LedFx's 0–5000 ms delay knob for
  Bluetooth sinks — light pipelines outrun Bluetooth audio.
- [S457][S454][S456] BeatNet is the practical streaming downbeat option;
  madmom is unmaintained; librosa is batch-oriented by design.
- [S458] sounddevice: MIT, maintained, NumPy-native — the capture layer.

## Rejected alternatives

- **Import aubio-ledfx** — GPL-3.0, incompatible with ADR-012 [S451].
- **madmom** — PyPI stuck at 2018, install pain on modern Pythons [S454].
- **librosa on the live path** — explicitly batch-oriented; realtime is a
  non-goal upstream [S456].
- **DSP in the audio callback** (LedFx) — the pain point its own code
  documents [S630:ledfx/effects/audio.py#L1138-L1141].
- **Streaming raw audio to nodes** — orders of magnitude more bandwidth
  and jitter-sensitivity than a 44-byte feature packet [S453].
- **On-device analysis everywhere** (WLED-MM model) — right for
  standalone nodes, wasteful in hosted mode; pewpew supports both via the
  V2 packet [S453].

## Amendment (2026-11-02) — room events in the features frame

Records the event core of the "Room-event triggers" story
(`docs/backlog/v0.2.x.md`). Code:
`src/pewpew/triggers.py`, the `triggers` section and `Looks.hold` in
`src/pewpew/looks.py`, `src/pewpew/features.py`; wire messages in the
`src/pewpew/sinks/preview.py` module docstring. *(Since 2026-11-05 the
triggers are `src/pewpew/aura/triggers.py`, the `triggers` section is read
in `src/pewpew/aura/book.py`, `Looks.hold` is in `src/pewpew/aura/looks.py`,
`Event` and `EventFeatures` are in `src/pewpew/features.py`, and the wire
is described in `web/src/infra/wire/protocol.ts`.)* Scope
set by the maintainer on 2026-10-26: the core, the JSONL log, and the page's fire-cue
buttons and arm switch as the only input. HTTP and OSC inputs wait for a decision on what
the room events are.

### Decision

- **Events enter as tick-stamped data, never as wall-clock reads.** Every
  input calls one function, `Triggers.submit(source, name, value)`, from any
  thread; it checks the shape and queues the event. The queue drains on the
  loop thread at the top of the next frame (the crossfader's per-frame hook,
  after `PacedLoop.call_soon` has drained; *since 2026-11-05 a `before`
  hook of the loop, `Triggers.before_frame`, after the loop's `calls`
  drain, per ADR-010's 2026-11-05 amendment*), and each event is stamped with
  that frame's engine `t` and tick number. A new input is an adapter that
  calls `submit`.
- **What a pattern sees.** `FeatureFrame` gains `events`: a tuple of
  `Event(name, source, value, priority, t, tick)`, the events accepted at
  this frame's tick, highest priority class first, then in arrival order. It
  is empty on every other frame, so each event is seen exactly once, in the
  `before_render(dt, features)` of the frame it fired on. `value` is None for
  an impulse (a button) or a number (a sensor level). The frame stays
  read-only data. Every renderer running that frame, both sides of a
  crossfade included, sees the same tuple. **Deterministic:** the tuple is a
  function of the events submitted and the tick they landed on, never of
  wall time, so the same events at the same ticks give byte-identical frames
  (T-1…T-5). The fake feature source carries no events, so every golden
  frame is unchanged.
- **Arbitration on engine time**, the first matching rule dropping the
  event: disarmed; unknown name; debounce per source and name, counted from
  the last arrival; edge-only for levels, firing on a rise from ≤ 0 to > 0
  [S1265]; cooldown per source and name, counted from the last accepted
  event; outranked, when the trigger holds a look and a higher class's hold
  is running; a global rate limit (8 accepted per second; operator-class
  events are exempt). Classes, highest first:
  operator, performer, button, sensor. TouchDesigner's Trigger CHOP
  has the same re-trigger delay and minimum length for one-shot events over
  an ambient look [S1294].
- **A trigger can hold a look as a temporary override.** The looks file's
  `triggers` section maps an event name to `{look, hold, priority, debounce,
  cooldown}`. A hold recalls the look through the looks' recall path and
  fade, journals what was live (pattern and params), and returns to it after
  `hold` seconds of engine time, as LedFx's silence scene journals and
  restores [S1266]. The hold counts from the frame its look starts. It never
  writes `current` or the file, so a restart comes back in the operator's
  look, and it never moves the master. A later hold replaces the look and
  the deadline and keeps the journal. **The operator wins:** a recall, pick
  or save during a hold ends it with no return.
- **Every submitted event is logged** as one JSON line with its tick, `t`,
  source, name, value, class and verdict (`--trigger-log PATH`, off by
  default), arm changes included. Feeding the records back before the frame
  of the same `t` reproduces the run (`tests/test_triggers.py`), operator
  input aside.
- **Disarmed at launch unless `--armed`**, which the unattended run's
  LaunchAgent passes (the maintainer, 2026-11-04), so a restart mid-run comes back
  armed. Arming is not persisted.

### Consequences

- The pattern-facing contract grows by one read-only field; ADR-005 records
  it in its own 2026-11-02 amendment.
- Arbitration and the override live on the host. Routing sensors to pewpew
  rather than to the boards is required: a board-local trigger fights the
  DDP stream, and WLED takes control back about 2.5 s after realtime stops
  [S1258].
- A network input (HTTP `GET`, OSC) must add a token, a sender allowlist and
  a router-only bind before it calls `submit`, since OSC has no
  authentication and phones in the room are a known attack path [S1295].

### Evidence

- [S204][S462] Pixelblaze's sensor board hands patterns pre-chewed values as
  variables; patterns never poll a device — the same consumption model for
  events as for audio features.
- [S1265] Chromatik triggers fire on change only — the edge rule.
- [S1294] TouchDesigner Trigger CHOP: re-trigger delay and envelope over an
  ambient state — the cooldown and hold.
- [S1266] LedFx's silence scene journals the running state and restores it —
  the override's return.

### Rejected alternatives

- **An `on_event(event)` callback on the pattern** — a fourth lifecycle
  method, called at a time the engine would have to define, for what one
  read-only field in the frame already carries [S204][S462].
- **Events as param sets** — a param is a level that persists; an impulse
  would need an engine-side reset, and two events in one frame collapse to
  one value.
- **Holding an event in the frame for several frames** — every pattern would
  then need to de-duplicate; one frame, exactly once, is simpler to author
  against and to test.
- **Stamping on arrival with the wall clock** — non-deterministic, and a
  log of wall times cannot be replayed into the same frames (CLAUDE.md
  determinism rule).

## Amendment (2026-11-06) — live input

Records how pewpew hears a live line-in or room microphone, from RA-28
(`research/topics/RA-28-audio-input.md`) and its build plan, with the maintainer's
answers of 2026-11-06. It supersedes the Decision's "Capture" bullet (a
fixed 60 Hz hop, resampled, with a callback that fills a ring) and its
"Beats" bullet (energy beat and BeatNet). Code: `src/pewpew/audio/`
(sources, analysis, tracker, oscillator, `AudioFeatures`, the feature log
and replay), and live capture through sounddevice in
`src/pewpew/audio/device.py` (RA-28's M2).

### Decision

- **Capture polls a callback-free stream on the loop thread**, reading
  what is available each tick; no Python audio callback runs. A device is
  opened at its native rate, with no resampling, and is chosen by exact
  name, index or a substring that matches one input, never `default`. A
  supervisor thread opens and reopens it, and re-enumerates devices only
  with no stream open. sounddevice is the optional extra `pewpew[audio]`,
  imported only where a device is opened.
- **Analysis runs on the sample clock in ADR-010's `before` seat**, ahead
  of the triggers: hop n starts at sample n·hop, every 10 ms, and no
  analysis state reads wall time. Levels come from a 1024-point window
  (the maintainer's latency lever): 16 mel bands from 40 Hz to 16 kHz, and volume,
  bass, mid and high split at 250 and 3000 Hz, behind one gain rider and
  one gate on one `sensitivity` knob. `at(t)` returns the frame stored for
  the tick and never raises. `FeatureFrame` keeps its fields and gains no
  new one until an op reads it, so ADR-005's contract and every golden
  stand; with no `--audio`, every renderer reads `FakeFeatures`.
- **The beat is Stark, Davies & Plumbley's causal tracker as written**: the
  complex spectral difference of a 2048-point window, a cumulative score
  with α 0.9 and η 5, and a 6 s comb-filterbank tempo over 80–160 BPM with
  a one-step Viterbi-like update. `confidence` is the comb's peak salience,
  and below 0.3 the beat free-runs at the last confident tempo.
- **`beat_phase` is an engine-time oscillator** steered by a phase-locked
  loop within ±10% of its rate: it never steps back, and a wrap is a beat.
  A default lead of about 35 ms aims the beat at the light, and
  `--audio-delay MS` (signed) delays the levels and shrinks the lead.
- **A live input's samples map to engine time by a fitted line**: each
  drained block is stamped with the end of its slot, and the line is the
  median of the pairwise slopes through each second's earliest stamp over
  60 s. The PLL waits for 5 s of points.
- **Gaps:** under 0.5 s, counted zeros, and every hop whose detection value
  reads a window touching the gap holds its value and its levels (7 hops
  for one lost 10 ms block); 0.5 s or more is **lost**. At most 20 hops a
  tick; held hops past 10% of the tempo window free-run the beat.
- **Input lost** (the maintainer): levels go to silence, the beat free-runs at the
  last tempo, and health says "lost"; there is no fallback to another
  input or to simulated features.
- **Controls, stamped with the tick as triggers are:** tap (the median of
  four intervals sets the tempo, the tick the phase, and the tracker then
  corrects within ±4%), hold, auto, resync, nudge and sensitivity.
- **Feature log and replay:** `--feature-log` writes each frame as JSONL
  from a writer thread, capped in hours; `replay:PATH` plays it back byte
  for byte. It is off unless asked and never in the unattended run's LaunchAgent,
  since a microphone's 16-band log is close to a speech recording. Raw
  audio never goes to disk.

### Consequences

- The installation runs unchanged: only `--audio` changes the features.
- The tracker is right at the correct metrical level about half the time
  on real music, so tap, hold and free-run are part of the design, and
  RA-28's M4 tunes the thresholds and the lead on the maintainer's recordings.
- The beat lands 0–31 ms after a synthetic transient, depending on the
  sound; that latency of the 2048-point window joins the lead.
- One-slot stamps measure a live source's drift only to about one slot per
  window; the fit is for mapping samples to engine time, which it does
  within one slot.

### Evidence

- [S1754:src/sounddevice.py#L845] sounddevice runs a stream callback as a
  cffi callback, and [S1756:src/c/_cffi_backend.c#L6280-L6285] cffi takes
  the GIL to run one: a Python callback would make PortAudio's real-time
  thread wait on the render loop.
- [S1757:include/portaudio.h#L187-L192] the last `Pa_Terminate` closes
  every open stream, and [S1758] PortAudio has no hotplug: re-enumerate
  only with no stream open.
- [S1750] Stark et al. 2009: the tracker, its parameters, its 80–160 BPM
  octave, and Table 1's CMLt 58.7% and AMLt 73.6% (71.0% and 76.5% given
  the tempo and first beat): the case for confidence and tap.
- [S1751] Davies & Plumbley 2007: the moving-mean threshold, the
  normalised autocorrelation, the four-element comb and the Rayleigh
  weighting with β at 120 BPM.
- [S1752] Bello et al. 2005: the complex-domain detection function reads
  the two previous frames, which sets the hold of a gap.
- [S1760][S1761] Resolume's Tap, Resync and Nudge, and TouchDesigner's
  Beat CHOP from a tapped tempo: professional tools pair detection with
  manual tempo.
- [S1759:ledfx/effects/audio.py#L1268-L1300] LedFx's energy beat reads
  `time.time()`: the wall-clock analysis the sample clock replaces.
- [S1753] Moon, Skelly & Towsley: the lower-envelope clock fit, rejected
  below.
- [S1764][S1762][S1763] aubio-ledfx now ships wheels for Python 3.11–3.15
  but is GPL-3.0; BeatNet pins numba 0.54.1, which needs Python below 3.10.
- [S1765] Shannon et al. 1995: three or four band envelopes keep speech
  recognisable, so a feature log is opt-in.

### Rejected alternatives

- **A Python capture callback**, or DSP inside it as LedFx does — the GIL
  wait above [S1756], and the flaw ADR-009 already names [S630].
- **An analysis thread** — a hand-off for about 20 µs of work a hop, and a
  second owner of the analysis state.
- **Analysis inside `at(t)`** — a memoised reader that raises keeps
  nothing, so a second reader would find the samples drained.
- **Resampling to a fixed rate** — a dependency for no gain: the hop is
  `rate/100` samples at both common rates.
- **60–180 BPM** — Stark limits the tracker to one octave to stop it
  switching metrical levels [S1750].
- **A tap that locks the tempo** — a tempo 1% off drifts 45 ms in 4.5 s at
  120 BPM.
- **BeatNet, aubio-ledfx, BTrack, Essentia** — uninstallable or GPL/AGPL
  [S1762][S1763][S1764][S1768][S1767].
- **Moon et al.'s lower envelope** — one early point bounds the line until
  it leaves the window [S1753].
- **Committed music** — tests synthesise their signals from seeds and
  commit only a small feature fixture.

## Amendment (2026-11-06) — capture nodes

Records the ESP32 capture node of RA-28 (§6) and its build plan, with
the maintainer's answers of 2026-11-06. It narrows the Decision's "Distribution:
features, never samples" and the rejected "Streaming raw audio to nodes".
Code: RA-28's milestone M2b: `firmware/audio-node/` and `src/pewpew/audio/`
(`net.py`, `wire.py`, `keys.py`); its bench (`docs/audio.md` §9) is attended.

### Decision

- **"Features, never samples" still holds** for render nodes, the page and
  Audio Sync V2 output. **A capture node may send raw audio** to its one
  subscribed host, which analyses it as any input and never stores it.
- **Packets:** unicast UDP, 100 a second, each 480 s16 samples at 48 kHz
  behind a 20-byte header (magic, version, clip and overflow flags, a
  64-bit first-sample index and a boot nonce); no sequence number, since
  the index shows loss and order. Silence is sent too. The node counts
  samples the I2S driver dropped into its index and never blocks its reader
  on a send.
- **Trust model and ADR-009's network-input rule, as applied:** nodes join
  the private router only; the host's socket binds to the router address and
  `connect()`s to the node; `SUB`, renewed every second, carries an
  HMAC-SHA256 over the node's MAC, its boot nonce and the reply address,
  under a per-node key written at flash time. **The per-packet tag is
  waived** (the maintainer): the router is the boundary, and spoofed audio gives no
  new way to move the lights. **No encryption for the line-in node**; ask
  again before the microphone node.
- **Tiers:** outside `--unattended`, every subscribe needs `--allow-host IP` and
  writes an `audio-input` audit record first; agents only read a deployed
  node's `/json/info`.
- **Firmware:** a small ESP-IDF image that captures, sends, answers `SUB`,
  serves `GET /json/info` and speaks Improv, with ADR-019's task watchdog
  and reset reason. **No network OTA**: nodes update over USB.

### Consequences

- One analyser serves the laptop's interface and the nodes, and a packet
  trace with a seeded signal replays a node's run.
- One lost packet holds about 7 hops, where a features packet would lose
  one; at unicast loss under 0.1% that is under 0.7% of hops. A measured
  loss above about 1% in M4 reopens features on the node.
- The host measures each node's drift rather than assuming a crystal's.

### Evidence

- [S1771:usermods/audioreactive/audio_reactive.cpp#L799-L812] Audio Sync V2
  carries 16 untimed magnitude bytes and no phase, and [S1772] the MM fork
  stops sending after 30 s of silence: V2 cannot feed Stark's detection
  function [S1750][S1752].
- [S1773] a 1024-point complex FFT takes 97 847 cycles on the S3: CPU is
  not the reason to send raw audio; one implementation and replay are.
- [S1774] Wi-Fi multicast is unacknowledged and held for power savers, and
  ADR-003 measured retried unicast loss under 0.1% [S150].
- [S1775] Opus frames add look-ahead and the codec is lossy.
- [S1776] `connect()` on a datagram socket limits the remote sender.
- [S1777:components/esp_driver_i2s/i2s_common.c#L943-L946] a full I2S
  receive queue drops its oldest buffer and reports the size, which the
  node adds to its index;
  [S1777:components/soc/esp32s3/include/soc/clk_tree_defs.h#L327-L340] and
  [S1777:components/esp_driver_i2s/i2s_common.c#L1965-L1993] the S3 has no
  APLL and divides its master clock fractionally, and [S1778] IDF warns the
  rate "might be imprecise" at 24 bits: the host measures drift.

### Rejected alternatives

- **Features computed on the node** — a C twin of the tracker to keep
  equal, no replay from a trace, and nothing gained on a LAN with
  bandwidth to spare [S1773]; deferred to a host-less mesh (ADR-015).
- **Audio Sync V2 as a beat source** — no phase, no timestamps, per-node
  gain, multicast [S1771][S1774].
- **Opus** — packing delay already paid, a native binding on the host, and
  lossy phase [S1775].
- **ESPHome** — a GPLv3 runtime [S1779].
- **Multicast** — unacknowledged and delayed for power savers [S1774].
- **NTP or PTP on the node** — the sample index and a fitted line need no
  clock service; Moon et al.'s plain lower envelope is rejected in "live
  input" [S1753].
- **A counter in `SUB`** — the boot nonce and the holder rule already stop
  a replay from moving the stream to another host.
- **Unsigned network OTA** — any update path past USB uses ADR-016's
  signed images.
