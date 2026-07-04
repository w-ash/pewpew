# ADR-006: Parameterization & control plane — one tree, typed params, everything addressable

Status: Proposed (2026-07-03)

## Context

Five parameter-exposure designs exist in the field, from WLED's fixed
relabeled slots to LX's first-class modulatable parameter objects (RA-05
survey). Separately, WLED's one-JSON-document API is why its third-party
ecosystem is the largest. pewpew needs pattern knobs, engine state, UI,
OSC/MIDI, and Home Assistant to hang off one mechanism, not five.

## Decision

- **Typed parameter objects declared in one line**
  (`Param(default, range, label)`), mounted into **one canonical state
  tree** with stable paths. Registration buys UI widget, OSC address,
  MIDI-learn target, and modulation input simultaneously (LX semantics,
  Pixelblaze ergonomics).
- Patterns serialize ISF-style: the parameter manifest travels with the
  pattern file as a portable document.
- **HTTP JSON GET/POST with partial-merge mutation; WebSocket speaks the
  identical vocabulary** plus server-push of merged state to all clients.
  No second WS-only vocabulary.
- **Parameters are modulation endpoints**: LFOs, audio features (ADR-009),
  and beat phase patch onto any knob at runtime; OSC uses normalized 0–1
  floats mirroring the tree; tempo/beat is externally settable.
- **`save` flag** separates live tweaks (RAM) from persisted state (disk);
  WLED-style presets (preset = any partial state) and playlist-as-data
  `{ps, dur, repeat, end}`. Scheduling minimal (boot preset + timers);
  calendars delegated to Home Assistant/cron.
- mDNS/zeroconf advertisement + push-on-change; live preview is an opt-in
  exclusive stream.

## Consequences

- Every controller class (built-in UI, OSC surface, MIDI hardware, HA,
  scripts) is a thin binding over the same tree — integrations stay cheap.
- The tree is the engine's public API contract; path stability becomes a
  compatibility promise from v1.
- Modulation routing makes parameters signal endpoints, so the frame
  pipeline must resolve modulated values once per frame (ADR-010).

## Evidence

- [S216] LX `CompoundParameter`: registered parameters get UI, OSC/MIDI
  mapping, and runtime modulation "patched onto any knob" — the semantics
  adopted.
- [S203] Pixelblaze's naming-convention controls: zero ceremony but no
  range/default metadata — the ergonomic bar and the gap we close.
- [S214] ISF's typed INPUTS manifest adjacent to code — the portable
  serialization model.
- [S550][S551] WLED: one JSON document, partial-merge over HTTP and WS with
  push fan-out — the property that made dozens of third-party apps cheap.
- [S552] Pixelblaze's `setVars`/`save` flag: pattern-exported variables as
  the extensibility surface; RAM-vs-flash persistence split.
- [S555][S556] LX OSC: normalized 0–1 floats, hierarchical paths, OSCQuery
  discovery, tempo as an addressable parameter; MIDI mappings are
  event-based (device-swappable).
- [S553] HA's WLED integration: mDNS discovery + local push + enumerable
  presets/effects are what earn first-class hub support.
- [S554] WLED presets replaced a separate macro system — one abstraction
  covering scenes, commands, playlists.

## Rejected alternatives

- **Fixed relabeled slots** (WLED: ≤5 knobs, uint8 only) — cannot express
  types, ranges, or more than a handful of parameters [S206].
- **Naming-convention reflection alone** (Pixelblaze) — no metadata, fixed
  widget vocabulary [S203].
- **Validation-schema-as-manifest** (LedFx voluptuous) — typed but verbose
  and static; no per-frame modulation [S208].
- **A second WS-only protocol vocabulary** — WLED demonstrates the single
  vocabulary is what keeps clients consistent [S550][S551].
- **MQTT as the core control plane** — kept as an optional thin bridge;
  it is the fallback pattern, not the native surface [S552][S553].
- **FPP-grade calendar scheduling** — out of scope; delegated to HA/cron
  [S554][S022].
