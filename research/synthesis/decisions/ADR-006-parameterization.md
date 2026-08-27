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
- What a pewpew *project* is on disk (directory layout for patterns +
  fixtures + calibration CSVs + presets, with a schema-version field for
  migration across engine versions) is deliberately undefined here — to be
  defined at build Phase 3, when presets/playlists are implemented.
- The palette model is deferred to build Phase 1: palettes enter as gradient
  assets addressable in this parameter tree (every surveyed system treats
  palettes as a first-class creative primitive — RA-12 carries the taste
  evidence); no separate ADR is needed unless Phase 1 proves otherwise.

## Evidence

- [S216] LX `CompoundParameter`: registered parameters get UI, OSC/MIDI
  mapping, and runtime modulation patchable onto any knob (paraphrase of
  S216's "easily mapped to UI components, MIDI controllers, or OSC
  messages" / "opens up interesting modulation possibilities") — the
  semantics adopted.
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

## Amendment (2026-08-22) — Phase 1 lands declarations; ranges are enforced

Records what build Phase 1 (v0.2.2) implements of this ADR, and settles the
range question the backlog left open: *"declared `lo`/`hi` are not
range-checked, so `{"speed": 1e9}` is accepted... decide it here rather than
leaving it as an accident"* (`docs/backlog/v0.2.x.md`).

Status stays **Proposed**. Phase 1 implements the declaration half only. The
control plane this ADR decides — one canonical tree with stable paths, HTTP
JSON partial-merge, the identical vocabulary over WebSocket, presets, the
`save` flag, mDNS — is Phase 3 and untouched. The Phase-1 object is
deliberately named `ParamSet`, not a tree: it has no paths and no nesting, and
must not pre-spend the vocabulary the tree will need.

### Decision

- **Declarations outlive bind.** `Param(default, lo, hi, label)` is unchanged
  as the one declaration form; what changes is that `declared_params(cls)`
  reads them back off the class, so something can ask a pattern what knobs it
  has. Before this they were assigned and then read by nothing. This is the
  minimum the auto-generated-UI model in [S216] and [S214] requires, and the
  metadata gap that convention-based reflection [S203] cannot close.
- **A value outside `[lo, hi]` is refused**, at every entry point: `--param`,
  the `params=` override, and any live set. The range is a contract, not a
  UI hint. Float noise at an endpoint snaps to the endpoint (a slider stepping
  `lo + i*step` can land an ulp past `hi`); anything further out is refused.
  Widening the declaration is the sanctioned way to reach further, and it
  moves the control surface's endpoints with it.
- **Refusals are two fields, `reason` and `hint`.** The reason names the knob
  and the range; the hint names the source file. Only the reason may cross a
  network boundary — the preview server is unauthenticated by design
  (architecture §5, Trust model), and a refusal must not serve the layout of
  the disk to whoever can reach the port.
- **Validation is separable from mutation.** `ParamSet.check(name, value)`
  returns the refusal reason and never raises; `set` is built on it. This is
  not stylistic: `PacedLoop.call_soon` propagates a closure's exception out of
  `run()`, so a raising setter reached over a socket is a way to stop the show
  from a browser. Verified — queueing an out-of-range `set_param` through
  `call_soon` kills `run()` with the ValueError. Callers off the loop thread
  validate on their own thread and queue only what passed.
- **Values resolve at bind, not per frame.** ADR-010's per-frame resolution
  seat is for *modulated* values and needs `t` and the resolved feature frame
  as inputs; a Phase-1 signature that has neither would be the wrong shape
  built early. It lands beside `features.at(t)` in `Renderer.advance_to` when
  ADR-009 gives it something to resolve.
- **Reload policy (for ADR-005's hot-reload story).** When a reloaded class
  narrows a range below the live value, values that still validate carry and
  the rest **reset to the new default** — not clamped. The author just edited
  that declaration, so their new default is the intended answer; a clamp would
  invent a value nobody chose and pin the surface at an edge.

### Consequences

- The declared range becomes load-bearing for every surface downstream: a
  slider's endpoints now bound every value the engine can render, so slider
  position always equals true value.
- `Param.step` and `Param.decimals` are **derived** (`(hi-lo)/200` snapped to
  a 1/2/5 decade), not declared, so this ADR's one-line declaration form
  survives while the wire still carries a real quantization every surface
  agrees on. The retired playground hand-tuned a step per knob and the browser
  was the only thing that knew it.
- The backlog's hedge that "modulation endpoints may legitimately drive a knob
  past its UI range" is **not** adopted, and needs no bypass: §5 has OSC
  mirroring the tree with normalized 0–1 floats, so a modulation source maps
  *into* the declared range by construction.
- A live set only reaches a pattern that reads the knob each frame. One
  precomputing from a knob in `setup` would ignore it until the next bind.
  Not fixed here; a live-set liveness check is the answer when a pattern makes
  it real.
- Landing the `ParamSet` **arms** the second of ADR-010's three GC-retest
  triggers. It does not discharge it: that is a measurement, due once sinks,
  params and hot reload all exist.

### Rejected alternatives

- **Clamping into range** — silently renders one value while every surface
  displays another, which is the dead-parameter failure this work exists to
  remove, one layer up. Live engines commonly do clamp, and that survey was
  not run against sourced evidence here; the decision rests on the displayed
  value having to be the rendered one, which is verifiable on its own.
- **Accepting with a warning** — the runner buffers log records while the ANSI
  sink owns the terminal and replays them at exit, so the warning would arrive
  after the show it described.
- **A descriptor `Param`** (`__get__`/`__set__`) — the idiomatic answer, and
  it would type `self.speed` as `float` for a checker. Measured on this host
  (Python 3.14.3): 4.15 ns for a plain instance attribute, 7.4 ns for the
  current shape, 25–35 ns for a data descriptor. Against a 22–118 µs frame
  that cost is irrelevant; it is rejected only because the repo runs no mypy,
  pyright, CI, or lint, so the benefit is currently zero. Revisit on the day a
  type checker lands.
- **An int/bool/enum type taxonomy** — this ADR mandates exactly one
  declaration form and names no taxonomy; none of the nine knobs in the
  gallery wants one. Any expansion needs its own amendment.
- **Per-param logarithmic scaling** — five of the nine declared knobs have
  `lo = 0.0`, where a log scale is undefined, so it can never be a default and
  would have to be a declaration-shape change. A control surface can choose
  log travel from `lo`/`hi` alone.
