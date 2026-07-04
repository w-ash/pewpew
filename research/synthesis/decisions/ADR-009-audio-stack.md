# ADR-009: Audio stack — LedFx-shaped features in NumPy, features-not-samples distribution

Status: Proposed (2026-07-03)

## Context

Audio reactivity needs a capture→features pipeline on the host and a way to
get features to patterns and remote nodes within a ≤45 ms audio-to-photon
budget (P-4, R-4). LedFx is the production-proven Python reference but is
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
- **Latency**: ≤45 ms budget; signed delay knob (±ms, up to seconds) for
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
