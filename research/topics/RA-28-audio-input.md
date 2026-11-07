# RA-28: Live audio input

Last researched: 2026-11-06
Status: reviewed. The build plan had four revisions and a 12-item review, and the maintainer
answered its questions on 2026-11-06 (Decisions).
S-ID block: S1750–S1799 (S1750–S1797 used). It also cites S011, S150, S166,
S453, S454, S456, S458, S459 and S630 from earlier blocks.

This study asks what pewpew needs to react to real sound: a live line-in or
room microphone at the pewpew host, and dedicated ESP32 capture nodes. It
records the research behind ADR-009's amendments of 2026-11-06 ("live
input" and "capture nodes") and ADR-012's ("protocol interop"). **[inf]**
marks an inference, **[arith]** arithmetic from the figures cited, and
**not found** a search that found nothing.

## Key questions

1. Which capture library, and how does the loop get samples without a
   Python audio callback?
2. Which onset and beat algorithm, under ADR-012's licence boundary, and how
   good is it?
3. How does analysis stay deterministic when samples arrive on their own
   clock?
4. What happens when the input is lost, and how does a person correct the
   beat?
5. How does a capture node get sound to the host: raw audio or features, on
   what firmware, and under what trust model?
6. What does a feature log reveal, and what may be stored?

## Decisions (the maintainer, 2026-11-06)

- **Input:** line-in and a room microphone, chosen per run by device name,
  and dedicated ESP32 capture nodes.
- **Input lost:** keep the last tempo. Levels go to silence, the beat
  free-runs, and health shows "lost".
- **Tap:** nudges the tracker, which keeps correcting; "hold" and "auto"
  are explicit controls.
- **Feature log:** off unless asked, never in the unattended run's LaunchAgent.
- **Per-packet tag:** waived under the private-router trust model (§6); `SUB`
  is signed.
- **Encryption:** none for the line-in node; ask again before the
  microphone node.
- **Level latency:** a 1024-point level window, and Wi-Fi power saving off
  on the nodes.
- **Hosts:** the Mac first, the Pi 5 after the bench milestone; that
  milestone reports capture-to-onset only until the photodiode rig exists.

## Findings

### 1. Capture

- **sounddevice** is MIT and maintained; 0.5.6 (2026-08-17) ships a macOS
  wheel that bundles PortAudio and a pure wheel for Linux, which needs the
  system `libportaudio2` [S1755][S1754]. CI has no PortAudio, so the L1
  suite never imports it; it becomes the extra `pewpew[audio]` [inf].
- **No Python callback.** sounddevice builds each stream callback with
  `_ffi.callback` [S1754:src/sounddevice.py#L845], and cffi takes the GIL
  before it runs one [S1756:src/c/_cffi_backend.c#L6280-L6285], so
  PortAudio's real-time thread would wait whenever the render loop holds the
  GIL. A stream opened without a callback can be polled from the loop
  thread: `read_available` and `read()`, which reports overflow
  [S1754]. scottlawsonbc's MIT strip captures the same way, a blocking
  read and then a drain of what is available [S1794]. LedFx does the
  opposite, its DSP and every subscriber inside the callback [S630]
  [S011].
- **No hotplug.** PortAudio's hotplug request has been open since 2006
  [S1758], and the last `Pa_Terminate` "will automatically close any
  PortAudio streams that are still open"
  [S1757:include/portaudio.h#L187-L192]. So a supervisor re-enumerates only
  with no stream open, through sounddevice's private `_terminate` and
  `_lib.Pa_Initialize`, pinned and tested [inf].
- **Pi 5.** It has no analogue audio [S1793], so its input is a USB
  interface or a node. Debian trixie ships PortAudio 19.6, which reaches the
  interface through ALSA [S1795]; the PortAudio release is v19.7.0 of 2021
  [S1757]. Not found: sounddevice tested on PipeWire under trixie, and the
  Pi 5's analysis cost.
- **Built in M2** (`src/pewpew/audio/device.py`): a callback-free stream
  read each tick at the input's own rate, at a latency of 0.02 s on Core
  Audio and 0.04 s elsewhere [inf]; a supervisor thread that opens it, and
  after a loss lists the inputs again and reopens by exact name at most
  every 5 s, only with no stream open; an overflow or a new stream starts a
  new epoch, which restarts the hop grid and the clock's fit [inf]; a
  stream that opens at another rate restarts the analysis at it. It calls
  `Pa_Initialize` itself: sounddevice's `_initialize` points stderr at
  /dev/null while PortAudio starts [S1754:src/sounddevice.py#L2921], which
  would drop the other threads' log lines. Tested on a fake sounddevice
  module; the replug is tested attended (`docs/audio.md` §7).

### 2. Analysis

- **Cost is no constraint.** A hop of a 2048-point Hann FFT, 16 mel bands,
  flux and tempo cost p50 about 21 µs and p99 about 39 µs on an M5 Pro in
  the plan's measurement (local script, not committed).
- **The tracker: Stark, Davies & Plumbley 2009** [S1750]. It is causal and
  built from the complex spectral difference detection function, a
  cumulative score with α 0.9 and η 5, and a tempo from a 6 s frame,
  limited to one octave, 80–160 BPM, "to minimise the common beat tracking
  error of switching between metrical levels" [S1750]. Its tempo stage is
  Davies & Plumbley's comb filterbank with Rayleigh weighting, β = 43
  samples at 11.6 ms, "equivalent to 120 bpm" [S1751]. The detection
  function reads the current and the two previous frames, since the phase
  deviation is the second difference of the phase [S1752].
- **Expected accuracy.** On Hainsworth's 222 excerpts the default tracker
  scores CMLt 58.7% and AMLt 73.6%, and 71.0% and 76.5% when given the
  tempo and the first beat [S1750]: on real music the beat is right at the
  correct metrical level only about half the time. That is the case for
  confidence, free-run and tap.
- **Libraries.** aubio-ledfx 0.4.12 now ships wheels for cp311–cp315,
  aarch64 included, so only its GPL-3.0 licence excludes it [S1764].
  BeatNet 1.1.3 pins `numba ==0.54.1` [S1762], which needs Python below 3.10
  [S1763]: ADR-009's "BeatNet as an optional extra" cannot install. Essentia
  is AGPL-3.0 [S1767], BTrack GPL-3.0 [S1768], madmom unmaintained [S454],
  and librosa 1.0 still has no causal tracking [S1770][S456]. Beat This! is
  MIT but works on whole files [S1769]: a candidate for offline cue maps.
- **Built in M1** (`src/pewpew/audio/`): a 10 ms hop at the native rate
  with no resampling; levels from a 1024-point window (the maintainer's lever) with one
  gain rider and one gate behind one `sensitivity` knob, less a DC offset
  learnt over about 1 s, which a MEMS microphone or an ADC can have [inf];
  the onset
  from the 2048-point window; Stark's tracker as written, with Davies &
  Plumbley's threshold, autocorrelation and comb [S1750][S1751];
  `confidence` as the comb's peak salience, free-running below 0.3 [inf].
- **Measured in M1, on synthetic tracks.** The tempo of click tracks at 90,
  120, 133 and 150 BPM and of a kick loop at 124 BPM is exact after 6–10 s,
  and noise gives confidence about 0.1. The beat lands 0–31 ms after a
  click or kick, depending on the sound: the 2048-point detection function
  rises over the four hops a transient spends in the window, and the score
  can peak anywhere on that plateau. The analysis's latency joins the lead,
  which M4 calibrates [inf].

### 3. Controls

- Professional tools pair a cheap detector with manual tempo control:
  Resolume's BPM page offers typed BPM, Tap, Resync and Nudge [S1760], and
  TouchDesigner's Beat CHOP generates its ramps from a tapped tempo
  [S1761].
- A tap seeds the tracker and does not lock: a tempo 1% off drifts 45 ms in
  4.5 s at 120 BPM [arith]. The median of the last four intervals sets the
  tempo, the tick of the tap sets the phase, and the tracker corrects within
  ±4% [inf]. In M1 a tap outside 80–160 BPM folds into it by a power of
  two and the beat runs at the tapped multiple, and until "auto" the beat
  keeps to the nearer of the tracker's beats and off-beats: a tap moves a
  beat that locked half a beat off, and the tracker still corrects a tap
  that is less than a quarter beat out [inf]. "hold" free-runs, "auto" releases both, "resync" jumps forward
  to a beat, and "nudge" biases the rate by ±2% while held.
- Ableton Link is GPL-2.0-or-later [S1797], so it could only arrive through
  a separate process (ADR-012 rule 2), later.

### 4. Clocks and determinism

- **The sample counter is the analysis clock.** Hop n starts at sample
  n·hop; nothing reads wall time. LedFx's energy beat reads `time.time()`
  [S1759:ledfx/effects/audio.py#L1268-L1300], the pattern to avoid.
- **The beat is an engine-time oscillator**, `phase += dt·bpm/60·(1 + c)`,
  with a phase-locked loop setting `c` within ±0.1 [inf]. It never steps
  back, and a wrap is a beat, so `beat`'s pulse never fires twice.
- **Live samples get a fitted clock** [inf]. Each drained block is stamped
  with the end of its tick's slot. The fit keeps each second's earliest
  stamp against its index, over 60 s, and takes the median of the pairwise
  slopes and of the residuals. Moon, Skelly & Towsley's line "under all the
  data points" [S1753] would follow one early point until it left the
  window; the medians do not.
- **M1 finding: one-slot stamps measure drift only coarsely.** In
  simulation the fitted line follows the samples' own clock within one slot
  over the window, and one point a slot early moves it by under 1 ms, but
  the drift it reports is good to about one slot per window (about 280 ppm
  at 60 fps over 60 s), not the plan's 1 ppm: 1 ppm over 60 s is 60 µs
  against a 16.7 ms stamp [arith]. Mapping, not drift, is what the beat
  needs; a finer drift figure needs a longer window or finer stamps [inf].
- **Replay.** A feature log holds each tick's frame with exact floats, so a
  live run replays byte for byte at its fps and returns the record at or
  before `t` at any other. Tests synthesise their signals from seeds and
  commit only a small feature fixture; analysis outputs compared with a
  committed file use tolerances (±1 hop, ±2% BPM), since FFT output can
  differ in its last bits across platforms [inf].

### 5. Gaps, loss and backlog [inf unless cited]

- A gap under 0.5 s is filled with counted zeros, and every hop whose
  detection value reads a window touching it holds its value and its
  levels: one lost 10 ms block holds 7 hops with a 2048-sample window and a
  480-sample hop [arith; S1752].
- A gap of 0.5 s or more is "lost": no zero-fill, and the grid restarts.
  Zero-filling a 30 s outage would mean about 3 000 hops in one tick
  [arith].
- One tick analyses at most 20 hops; older due hops are skipped and
  counted. Held hops above 10% of the tempo window stop tempo and phase.
- A node's packet is a stray, and dropped, when its index maps more than
  0.5 s *after* its stamp. The plan's rule looked both ways; M2b looks one
  way, because a stalled loop drains packets that map before their stamps,
  and the backlog rule must take them, not drop them as strays. Strays that
  keep coming for 0.5 s start a new epoch, so a real jump is followed.

### 6. Capture nodes

- **Raw audio, not node features.** The S3 could compute features: a
  1024-point complex FFT is 97 847 cycles, about 0.41 ms at 240 MHz
  [S1773][arith]. Raw audio wins because it keeps one DSP implementation,
  replays from a packet trace and a seeded signal, and fits the bandwidth:
  ~0.8 Mbit/s a node [arith]. WLED's Audio Sync V2 cannot feed the tracker:
  it carries 16 untimed magnitude bytes and no phase
  [S1771:usermods/audioreactive/audio_reactive.cpp#L799-L812], and the MM
  fork stops sending after 30 s of silence [S1772].
- **Transport.** Unicast UDP, 100 packets a second of 480 s16 samples at
  48 kHz behind a 20-byte header with a 64-bit first-sample index and a boot
  nonce [inf]. Wi-Fi multicast is unacknowledged, slow and held for
  power-saving stations [S1774], and ADR-003 measured unicast loss under
  0.1% [S150]. Nodes join the private router only, one Wi-Fi hop, about 9 ms
  median [S166].
- **Opus is rejected:** 10 ms raw packets already pay 10 ms of packing, a
  CELT frame adds 2.5 ms look-ahead, and the codec is lossy, so it changes
  the per-bin phase the detector reads [S1775]; the network has bandwidth
  to spare, and the host would need a native binding [inf].
- **On the node.** When the I2S receive queue is full, IDF drops the oldest
  buffer and reports its size through `on_recv_q_ovf`
  [S1777:components/esp_driver_i2s/i2s_common.c#L943-L946], so the node
  adds the dropped samples to its index and the host sees an honest gap
  [inf]. The S3 has no APLL
  [S1777:components/soc/esp32s3/include/soc/clk_tree_defs.h#L327-L340] and
  divides the master clock fractionally
  [S1777:components/esp_driver_i2s/i2s_common.c#L1965-L1993]; IDF warns that
  at 24 bits the rate "might be imprecise" [S1778]. So health reports the
  drift it measures and judges none, and the firmware picks a slot width
  and MCLK multiple with an integer BCLK divider [inf].
- **Trust.** The private router is the boundary (architecture §5 "Trust
  model"); DDP and WLED's JSON API already accept anyone on it, so spoofed
  audio opens no new way to move the lights [inf]. The socket binds to the
  router address and `connect()`s to the node, so the kernel drops other
  senders [S1776]. `SUB` carries an HMAC-SHA256 over the node's MAC, its
  boot nonce and the reply address, under a per-node key written at flash
  time [inf]. The per-packet tag is waived (Decisions).
- **Naming.** Improv serial's 0x05 Set Hostname and 0x06 Set Device Name
  name a node over the USB session that joins it to Wi-Fi; Improv defines
  no vendor commands, so the key goes in an NVS image [S1785].
- **Firmware.** A small ESP-IDF firmware (Apache-2.0 IDF, `mdns` and the
  Improv SDK [S1777][S1786][S1787]) that captures, sends, answers `SUB`,
  serves `GET /json/info` and speaks Improv, with no OTA. An image also
  holds BSD, MIT and Apache-2.0 components [S1788], and the Wi-Fi binaries
  are Apache-2.0 [S1789]; a published binary ships a notices file [inf].
  atomic14's walkie-talkie is an MIT reference for I2S over UDP [S1790].
  ESPHome's runtime is GPLv3 [S1779]: a throwaway bench prototype at most.

### 7. Hardware

- **Line-in node (M2b):** an ESP32-S3-DevKitC-1 and a PCM1808, an active
  24-bit ADC with a 3 Vp-p single-ended full scale that needs SCKI at 256,
  384 or 512 fs [S1791]. A +4 dBu sine (3.47 Vp-p) clips it and −10 dBV
  (0.89 Vp-p) fits [arith], so it takes the mixer's REC or booth output.
- **Microphone node (later):** the ICS-43434 is listed as obsolete; buy
  spares before that variant [S1792].

### 8. Latency

- R-4 and P-4 set a 45 ms audio-to-photon budget [S459]. Capture is about
  18 ms over USB and about 19 ms from a node (DMA, packing and one Wi-Fi
  hop) [S166][arith]. The beat is predicted by the lead, so its target is
  0 ms; the levels take about 65 ms (`geq`) to 100 ms (`band("bass")`)
  [arith], which the maintainer's two levers shorten.

### 9. Privacy

- Speech stays highly recognisable from the envelopes of three or four
  bands [S1765], so a 16-band log from a microphone is close to a speech
  recording [inf]. Raw audio stays in RAM; a capture node's audio crosses
  the private router only to its one subscribed host. The feature log is off
  unless asked, capped in hours, and never in the plist.
- macOS may give a process without microphone permission all-zero input
  and no error [S1766][NEEDS-VERIFICATION]; a bundled app declares its use
  [S1796]. A LaunchAgent's behaviour: not found, so health flags exact
  zeros and the first run is attended.

### 10. Licences and interop

- WLED is "EUPL v. 1.2 or later" [S1771], and its audioreactive usermod
  uses the GPL-3.0 ArduinoFFT by default [S1784]; pewpew ships no WLED
  binary. Receiving the V2 protocol creates no obligation: EUPL's copyleft
  binds one who distributes or communicates the work or a derivative
  (Art. 5), and what counts as a derivative is copyright law's (Art. 1)
  [S1780]; EU law does not protect the ideas behind interfaces [S1781],
  data file formats are not protected expression [S1782], and US copyright
  never covers a method of operation [S1783]. The condition is a parser
  written from a byte-offset table, never from the struct's text [inf].

## Verdicts

- **sounddevice:** ascendant; maintained, MIT, wheels for both hosts
  [S1755].
- **Stark et al. 2009's causal tracker:** stable; the published real-time
  hybrid, with figures to calibrate against [S1750].
- **aubio-ledfx, BTrack, Essentia:** excluded by licence, not by health
  [S1764][S1768][S1767].
- **BeatNet:** waning; it cannot install on Python 3.11 or later
  [S1762][S1763].
- **WLED Audio Sync V2:** stable as a levels-only interop source, never a
  beat source [S1771].
- **Opus for capture nodes:** not needed on a LAN with bandwidth to spare
  [S1775].

## Code-reading queue

1. `spatialaudio/python-sounddevice` [S1754]: read for M2 at 0.5.6. `read`
   reports an overflow as input "discarded by PortAudio after the previous
   call and before this call" [S1754:src/sounddevice.py#L1463-L1498]; it
   does not say where in the returned samples the loss falls, so M2 starts
   a new epoch at the block that reports it [inf]. PortAudio's own Core
   Audio and ALSA blocking paths: not read; M2's attended replug test and
   M4 observe them.
2. `espressif/esp-idf` I2S standard RX [S1777]: the integer-BCLK slot
   configurations for the PCM1808, before M2b.
3. `atomic14/esp32-walkie-talkie` [S1790]: its UDP send path, for M2b.

## Open questions

- Pi 5 analysis cost, and sounddevice on PipeWire under trixie: not found;
  M4 measures.
- A LaunchAgent's microphone permission on macOS: not found; the first
  attended run checks (`docs/audio.md` §6).
- Wi-Fi jitter of an S3 sending 100 packets a second: not found; M4's soak
  measures loss and drift.
- M2b's attended bench (`docs/audio.md` §9): not run. The PCM1808 module's
  labels and regulator, the octal-flash N32R16V, and whether the node's
  gap after a forced overflow is exactly the dropped length (the drop sits
  within one 5 ms DMA buffer of where the driver made it [inf]) wait on it.
- The default lead (35 ms [inf]) and the tracker's thresholds: M4 tunes them
  on the maintainer's recordings with a loopback.

## Corrections to the 2026-11-06 ESP32 notes

The ESP32 research notes preceded the plan's review. Where they differ, the
plan governs and this doc records the plan:

- the clock fit is the median fit of §4, not a lower envelope;
- Opus is rejected on bandwidth, binding and phase (§6), not on frame delay
  alone;
- the packet header is 20 bytes with no sequence number: the sample index
  shows loss and order;
- a short gap holds its hops (§5); only a long one is "lost";
- `SUB` signs the MAC, the boot nonce and the reply address;
- a node has no OTA: it is updated over USB;
- "never send audio over the network" narrows to render nodes, the page and
  V2 output.
