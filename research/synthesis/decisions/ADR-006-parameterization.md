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
  Pixelblaze ergonomics). *(Since 2026-11-04 the one-line form is a kind
  constructor, such as `Float(default, lo, hi, unit)`; see that amendment.)*
- Patterns serialize ISF-style: the parameter manifest travels with the
  pattern file as a portable document.
  *(Superseded 2026-11-07: the portable document is a look; see ADR-025.)*
- **HTTP JSON GET/POST with partial-merge mutation; WebSocket speaks the
  identical vocabulary** plus server-push of merged state to all clients.
  No second WS-only vocabulary.
- **Parameters are modulation endpoints**: LFOs, audio features (ADR-009),
  and beat phase patch onto any knob at runtime; OSC uses normalized 0–1
  floats mirroring the tree; tempo/beat is externally settable.
  *(Superseded 2026-11-04: values cross OSC in plain units; see that
  amendment.)*
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
  and static; no per-frame modulation [S208]. *([S208] is stale: LedFx
  now uses pydantic [S1356]; see the 2026-11-04 amendment.)*
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
  *(Since 2026-11-04 the declaration form is a kind constructor; see that
  amendment.)*
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
  `run()`, so a raising setter reached over a socket is a way to stop the aura
  from a browser. Verified — queueing an out-of-range `set_param` through
  `call_soon` kills `run()` with the ValueError. Callers off the loop thread
  validate on their own thread and queue only what passed. *(Since
  2026-11-05 a live set is `ParamSet.set`, `Renderer.set_param` is gone,
  and a request that needs the loop's answer goes through `Calls.ask`,
  which turns an exception into a refusal; see ADR-010's 2026-11-05
  amendment.)*
- **Values resolve at bind, not per frame.** ADR-010's per-frame resolution
  seat is for *modulated* values and needs `t` and the resolved feature frame
  as inputs; a Phase-1 signature that has neither would be the wrong shape
  built early. It lands beside `features.at(t)` in `Renderer.advance_to` when
  ADR-009 gives it something to resolve. *(Since 2026-11-05 the seat is the
  layer compositor, which drives each layer's targets before the layer
  advances; see the amendment "layered paths" and ADR-021.)*
- **Reload policy (for ADR-005's hot-reload story).** When a reloaded class
  narrows a range below the live value, values that still validate carry and
  the rest **reset to the new default** — not clamped. The author just edited
  that declaration, so their new default is the intended answer; a clamp would
  invent a value nobody chose and pin the surface at an edge.

### Consequences

- The declared range becomes load-bearing for every surface downstream: a
  slider's endpoints now bound every value the engine can render, so slider
  position always equals true value. *(Since 2026-11-04 this holds for the
  base value; a modulated param renders base plus offset.)*
- `Param.step` and `Param.decimals` are **derived** (`(hi-lo)/200` snapped to
  a 1/2/5 decade), not declared, so this ADR's one-line declaration form
  survives while the wire still carries a real quantization every surface
  agrees on. The retired playground hand-tuned a step per knob and the browser
  was the only thing that knew it.
- The backlog's hedge that "modulation endpoints may legitimately drive a knob
  past its UI range" is **not** adopted, and needs no bypass: §5 has OSC
  mirroring the tree with normalized 0–1 floats, so a modulation source maps
  *into* the declared range by construction. *(Superseded 2026-11-04: values
  are plain, and the modulated sum wraps or clamps.)*
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
  after the run it described.
- **A descriptor `Param`** (`__get__`/`__set__`) — the idiomatic answer, and
  it would type `self.speed` as `float` for a checker. Measured on this host
  (Python 3.14.3): 4.15 ns for a plain instance attribute, 7.4 ns for the
  current shape, 25–35 ns for a data descriptor. Against a 22–118 µs frame
  that cost is irrelevant; it is rejected only because the repo runs no mypy,
  pyright, CI, or lint, so the benefit is currently zero. Revisit on the day a
  type checker lands. *(Revisited 2026-11-04: a non-data descriptor.)*
- **An int/bool/enum type taxonomy** — this ADR mandates exactly one
  declaration form and names no taxonomy; none of the nine knobs in the
  gallery wants one. Any expansion needs its own amendment. *(Superseded
  2026-11-04 by the kinds amendment.)*
- **Per-param logarithmic scaling** — five of the nine declared knobs have
  `lo = 0.0`, where a log scale is undefined, so it can never be a default and
  would have to be a declaration-shape change. A control surface can choose
  log travel from `lo`/`hi` alone.

## Amendment (2026-10-30) — saved looks and the two-renderer crossfade

Pulls presets and playlists forward from Phase 3 for the three-board rig
(`docs/backlog/v0.2.x.md`, story "Saved looks with crossfade recall"). Code:
`src/pewpew/looks.py`, `src/pewpew/crossfade.py`; wire messages in the
`src/pewpew/sinks/preview.py` module docstring. *(Since 2026-11-05 the
looks file format is `src/pewpew/aura/book.py`, the looks controller is
`src/pewpew/aura/looks.py`, and the wire is described in
`web/src/wire/protocol.ts`; see the amendment "one shape per wire
fact".)*

Status stays **Proposed**. The canonical state tree, the `save` flag, HTTP
partial-merge and mDNS are still Phase 3. A look is the first persisted
partial state, and the tree must absorb this file shape rather than
contradict it.

### Decision

- **A look is a preset, partial state.** It stores a pattern name (for a
  pattern launched by path, that path, so a recall runs the same file; it
  never crosses the socket), that pattern's param values and, optionally,
  the master; leaving the master out
  leaves it alone on recall. WLED presets may omit brightness [S554], and
  Chromatik snapshots choose what they store [S1265]. Each look also stores
  its own `fade` (seconds, default 2) and a `cycle` flag. A param the look
  omits starts at its default. On recall, a stored value that no longer fits
  the pattern's declaration also starts at its default, as in this ADR's
  2026-08-22 reload policy.
- **One JSON file on the laptop, written whole and atomically.** `run --looks
  PATH`:

      {"version": 1, "current": "dusk",
       "looks": {"dusk": {"pattern": "wash", "params": {"hue": 30.0},
                          "master": 0.6, "fade": 4.0, "cycle": true}},
       "attract": {"idle": 300, "dur": 60, "repeat": 0, "end": null}}

  *(Since 2026-11-04 the file is version 2 and a color is one value, such
  as `"color": {"h": 30.0, "s": 0.8, "v": 1.0}`; see that amendment. Since
  2026-11-05 it is version 3, with `"cycle": {"idle", "each", "rounds",
  "end"}` for `attract`; see the amendment "one shape per wire fact".)*

  Every change (save, delete, cycle flag, and every recall, which moves
  `current`) writes a temporary file in the same directory, flushes it to
  disk, and renames it over the old one. `current` is the restart path: a
  start comes back in that look with no fade, whatever pattern the command
  line names. The loader refuses a malformed file at launch and lists every
  problem: unknown keys, bad names, an unknown pattern, an undeclared or
  out-of-range param, a stored master above `--max-brightness` (named
  `--master-cap` since 2026-11-05). Looks are
  never written to the boards, because writing a WLED preset freezes the
  lights for seconds [S554].
- **Names on the socket, never paths.** A look name is 1–32 letters, digits,
  spaces, `_` or `-`. Requests name a look; refusals name the look or the
  pattern, never the file.
- **Crossfade: two renderers, two frames, one blend.** A recall builds a new
  `Renderer` for the look at the current engine time, on the same mapping,
  fixtures, seed and feature source (`Renderer.spawn`). For the fade, the
  old and new renderers both render every frame, and the loop gets
  `old·(1−a) + new·a` with `a = (t − t0)/fade` from engine time. Engine
  time keeps the fade deterministic. The blend is on the linear (N,3)
  pixel frame after each renderer's fixture gather, so looks with different
  `units` blend pixel for pixel. This is architecture §2 stage 2's rule,
  "blend frames, never engines", for two frames; WLED's transition instead
  copies the whole segment [S645:wled00/FX_fcn.cpp#L1330-L1367]. The master
  stays one scalar outside the blend: a look's stored master is set when
  its fade starts.
- **A recall during a fade waits for that fade to finish**, then starts
  [S1265]. Only one recall waits, and a newer one replaces it, so the
  longest wait is the rest of the fade that is running. The page shows the
  waiting look. A recall that cuts the running fade was rejected (below).
- **A fade time chosen on the page overrides the stored one** [S1269]; "cut"
  is 0.
- **The current renderer is the incoming one.** A live set, a pattern pick
  and a hot reload all act on the look fading in. A room map reload rebinds
  both sides; if the outgoing side cannot bind, the fade ends early. Each
  `Renderer` already turns a pattern's failure into an error frame, so a
  failing side still blends into a rendered frame. If the outgoing side
  raises anyway (a renderer left unbound), the fade ends early and the frame
  still renders.
- **Idle cycle as a playlist.** `attract` is this ADR's playlist
  `{ps, dur, repeat, end}` [S550], plus `idle`. `ps` is not stored: it is
  the looks flagged `cycle`, in file order, as in Chromatik's per-snapshot
  auto-cycle [S1265]. After `idle` seconds of engine time with no operator
  input, each look in `ps` plays for `dur` seconds. After `repeat` rounds
  (0 means forever), `end` is recalled. Any operator request stops the
  cycle and restarts the idle wait. *(Since 2026-11-05 the keys are
  `cycle: {idle, each, rounds, end}`; the director amendment below
  replaces the file-order playlist and adds `seed`, `window`, `fresh` and
  `weights`.)*
- **"Changed since saved."** Once the live pattern, a param value, or a
  stored master moves off the look last recalled or saved, the page marks
  that look as changed. This is grandMA3's changed-since-stored idea
  [S1269]. *(Since 2026-11-05 a pattern pick leaves every look, so no look
  is current, rather than marking the last one changed.)*
- **Triggers section (added 2026-11-04).** The looks file also carries a
  `triggers` section mapping event names to looks; its shape and the hold
  and return rules are decided in ADR-009's 2026-11-02 amendment, not here.

### Consequences

- The layer-compositing ADR (v0.2.9) inherits a working two-layer case:
  N renderers on one clock, blended per frame, each containing its own
  failures. A crossfade becomes a compositor with two layers and an opacity
  ramp. The open questions it must answer (a `Renderer` per layer, opacity
  as a `Param`) are unchanged. *(Since 2026-11-05 ADR-021 keeps the
  crossfade out of the stack: a recall fades between two whole
  compositors, and the `Crossfader` is not a two-layer compositor.)*
- A recalled look starts from fresh pattern state (`self.pixels`, buffers
  and RNG are not inherited), so recalling a look renders the same frames
  whatever ran before it. A pick, which goes through `Renderer.swap`, still
  keeps state.
- During a fade, two patterns render each frame. Phase-0 kernels cost
  0.03–0.08 ms per frame at 3,000 px
  (`bench/results/throughput-2026-07-15-mac-m5pro.json`), so this does not
  affect the budget.
- The control surface holds a new `ParamSet` after each recall. Callers
  read `params` through the crossfader every time and must not keep it.
- The looks file has a `version` field. It is the first piece of the
  on-disk project that this ADR's Consequences left undefined.

### Evidence

- [S1265] Chromatik snapshots: choose what they store, carry a transition
  time and an auto-cycle flag, and a re-recall finishes the running fade.
- [S554] WLED presets: any partial state, brightness optional; writing
  presets freezes output.
- [S550] WLED playlists: steps with duration, repeat and end preset — the
  `{ps, dur, repeat, end}` shape.
- [S1269] Lighting desks: a typed fade time overrides the stored one;
  grandMA3 counts changes since a store.
- [S645:wled00/FX_fcn.cpp#L1330-L1367] WLED copies the whole segment for a
  transition. This is the engine-level blend that architecture §2 rejects.

### Rejected alternatives

- **A recall during a fade cuts it and starts the new fade from the blended
  frame.** This answers faster, but the outgoing frame would be a blend of
  three renderers, or a frozen snapshot. Three renderers is the N-layer
  compositor this amendment must not pre-empt, and a snapshot stops motion.
  The wait is at most one fade, and blackout stays a one-message override.
- **A queue of every recall made during a fade.** An operator tapping
  through looks would sit through each fade in turn. Newest-wins keeps the
  wait to one fade.
- **Fading by `swap`ping the pattern into the running renderer.** One
  renderer cannot render two patterns in the same frame.
- **Storing looks as WLED presets on the boards.** Writing them freezes the
  lights for seconds, and the DDP stream overrides them anyway [S554].
- **Fade progress from the wall clock.** A replayed fade would then give
  different frames, against T-1…T-5. Engine time costs nothing.

## Amendment (2026-11-04) — typed kinds, parts, units and stable ids

Every param was one bounded float, `Param(default, lo, hi, label)`, with
the unit in `label`. A color was several loose floats that the page grouped
by a name pattern (`COLOR_PART` in `src/pewpew/sinks/web/index.html`), an
angle could not say it wraps, and every hue was declared 0..359. Backlog:
`docs/backlog/v0.2.x.md`, story "Typed params and a schema-driven control
page". The page that renders these records is ADR-020's 2026-11-04
amendment.

Status stays **Proposed**: the canonical tree, HTTP partial-merge and mDNS
are still Phase 3. This amendment fixes the shape of a param and of its
value, which the tree inherits.

### Decision

- **The `pewpew.params` package is the param bounded context.** It holds
  the kinds, the `HSV` value object and `ParamSet`; `pattern.py` keeps the
  `Pattern` contract and imports from it. Authors write `from pewpew import
  Float, Color`. Each rule (range check, snap, refusal wording, JSON form)
  is written once, in this package.
- **Five kinds**, each a subclass of an abstract `Param`:

  | kind | `self.x` | JSON value | page control (ADR-020) |
  |---|---|---|---|
  | `float` | `float` | number | slider; angle slider with `widget="angle"` |
  | `int` | `int` | integer | slider, step 1 |
  | `bool` | `bool` | `true`/`false` | switch |
  | `choice` | `str` key | the key | segment group (≤ 5 options), else select |
  | `color` | `HSV` | `{"h", "s", "v"}` | inline color picker |

  `palette` and `point2d` are reserved names, built when a pattern first
  needs one. *(Since 2026-11-05 `palette` is built; see the amendment
  "layered paths".)* Chataigne's parameter library has the same split: one
  class per type, a single `ColorParameter` and a `Point2DParameter`
  [S1357]; OSCQuery gives color and boolean their own type tags (`r`,
  `T`/`F`) [S1350].
- **Common fields:** `label`, `help`, `group`, `widget`. `float` and `int`
  add `lo`, `hi`, `unit`, `periodic` and `text` (a map from value to a word,
  such as `{0: "hold"}`), and carry `step` and `decimals`, still derived as in
  the 2026-08-22 amendment. `choice` adds `options`. `color` adds `parts`.
  `widget="angle"` is for a periodic `float` over 0..360.
- **On the wire** `params` is an ordered list of records. Every record has
  `name`, `kind`, `label`, `help`, `group`, `widget`, `default` and
  `value`, plus its kind's fields; a color's `parts` are `{h, s, v}`, each a
  numeric record. `text` and `options` cross as `[{value, label}]`, and
  an unset `widget` or `text` is null. *(Since 2026-11-05 a record carries
  no `value`, an unset `group` or `widget` is `""`, no `text` is `[]`, and
  a part is a slim numeric record; see the amendment "one shape per wire
  fact".)* Every value (a `set`, the echo, and
  each record's `default`, `declare` included) is the kind's JSON value; a
  refused `set` names the param and the reason, and carries no value.
- **Compound values have parts.** A `color` is three ranged parts: `h` over
  0..360 and periodic, `s` and `v` over 0..1. It is HSV over linear-light
  primaries, the space `kit.hsv` already works in (ADR-001). A part is
  checked by the same range rule as a `float`, and a refusal names the part:
  `pulse.color.s must be within 0.0..1.0, got 2.0`. One color is one param,
  as in Chataigne [S1357]; TouchDesigner instead makes each component its
  own `Par` in a group [S1355].
- **Units are short symbols** (`°`, `s`, `/s`, `Hz`), never sentences.
  Descriptive text moves to `label` and `help`. OSCQuery's UNIT list has
  `angle.degree`, `time.second` and `time.hz` [S1350]; JSON Schema has no
  unit keyword at all [S1360].
- **Ids never change.** A param's id is its attribute `name`; a value's
  path is `pattern.name[.part]`. CLAP: a "Stable parameter identifier, it
  must never change" [S1351:include/clap/ext/params.h#L212]; VST 3: "it is
  not allowed to change this assignment at any time" [S1352], and a changed
  id needs a host remap interface [S1353]. Renaming a param is a clean
  break: saved looks lose that value, and there is no alias. This
  amendment's own renames (hue and saturation into `color`) are the clean
  break below.
- **A group is layout only.** It orders and folds params on a surface and
  is never part of an id or a path. CLAP keeps `module` out of the id and
  the name [S1351:include/clap/ext/params.h#L244-L251]; TouchDesigner pages
  are layout [S1354].
- **Values are stored and sent in plain units**, never normalized: in the
  looks file, on the wire, and in `--param`. CLAP's host advice is "store
  plain values in the document" [S1351:include/clap/ext/params.h#L78-L115].
- **`Param` is a non-data descriptor.** Its typed `__get__` gives a type
  checker `self.speed: float`. Bind sets the value on the instance, which
  takes precedence over a non-data descriptor [S1387], so the per-frame read
  stays a plain attribute read. This revisits the 2026-08-22 rejection of a
  descriptor, which waited for a type checker: basedpyright now runs in
  `just check`. That rejection measured a *data* descriptor (25–35 ns); this
  one is never on the read path.
- **Parsing never raises.** Each kind implements `parse(where, value) ->
  (value, None) | (None, reason)`; `ParamSet.check` is `parse(...)[1]`. The
  float wording stays byte-identical. `parse` takes native and JSON values.
  On a reload, `inherit` keeps a live value only if it fits the new
  declaration, so a param whose kind changed resets to its default (the
  2026-08-22 reload policy, extended to kinds).
- **Modulation is a base value plus an offset in plain units.** The
  operator's value is the base; a modulation source adds an offset, and the
  per-frame result wraps when the param is `periodic` and clamps to
  `[lo, hi]` otherwise. `bool` and `choice` cannot be modulated. CLAP:
  "store modulation amount in plain value delta, not in percentage"
  [S1351:include/clap/ext/params.h#L78-L115], with `IS_PERIODIC` "for
  periodic parameters like a phase" and `IS_MODULATABLE` per param
  [S1351]. The clamp acts on the modulated sum, never on a value someone
  set: a set outside the range is still refused (2026-08-22). Modulation is
  still unbuilt; it lands at ADR-010's per-frame resolution seat. *(Since
  2026-11-05 it is built: `Bound.drive`, at the layer compositor's seat;
  see the amendment "layered paths".)*
- **There is no `trigger` kind.** ADR-009's 2026-11-02 amendment rejects
  events as param sets, and cues already carry impulses. Chataigne's
  `Trigger` is not a `Parameter` [S1357].
- **External surfaces map records one to one.** When pewpew grows an OSC
  surface, each record maps to OSCQuery attributes [S1350]:

  | record | OSCQuery |
  |---|---|
  | path `pattern.name[.part]` | `FULL_PATH` `/pattern/name[/part]` |
  | `float` / `int` / `bool` / `choice` | `TYPE` `f` / `i` / `T` / `s` |
  | `color` | `TYPE` `fff`, `EXTENDED_TYPE` `color.hsv.h`, `.s`, `.v` (type tag `r` names no color space in [S1350]) |
  | `lo`, `hi` | `RANGE` `[{"MIN", "MAX"}]` |
  | `choice` options | `RANGE` `[{"VALS": [keys]}]` |
  | `unit` `°` / `s` / `Hz` | `UNIT` `angle.degree` / `time.second` / `time.hz` |
  | `unit` `/s` | no UNIT (units.md lists no rate; not found) |
  | refuse out of range | no `CLIPMODE`; clients must keep to `RANGE`, and a value outside it is refused |
  | `label`, `help` | `DESCRIPTION` |
  | settable and readable | `ACCESS` 3 |

  LX sends normalized 0–1 floats [S555]; pewpew sends plain values, so an
  OSC or modulation source maps into the range by the record's `lo`/`hi`.
- **Clean breaks.** Hue-and-saturation float pairs become one `color` each,
  and every declaration moves to a kind constructor in one pass. The looks
  file is version 2 only; a version-1 file is refused with `looks file is
  version 1; this pewpew reads version 2 (re-save your looks)`. *(Since
  2026-11-05 the file is version 3 and the refusal, in
  `src/pewpew/aura/book.py`, says "move it aside and save the looks again
  from the page".)* A stored
  value is a number, bool, string, or object of numbers. The wire changes
  in place with no `protocol` field. No aliases, no migration code.

### Consequences

- This amendment supersedes, in this ADR: "OSC uses normalized 0–1 floats"
  in the Decision (values are plain); the 2026-08-22 consequence that
  normalized OSC maps modulation into range "by construction" (the clamp
  above does); the 2026-08-22 rejected alternatives "A descriptor `Param`"
  and "An int/bool/enum type taxonomy".
- [S208] is stale: LedFx effect configs are now pydantic models with hex
  color strings [S1356]. The rejection of "validation-schema-as-manifest"
  still holds, on the pydantic grounds below.
- Every surface reads one record shape per kind, so the page renders a
  pattern's controls from its declaration with no per-pattern code
  (ADR-020's 2026-11-04 amendment). The describe output is a golden file
  (`tests/goldens/describe.json`) that both the Python and the page tests
  check.
- A hue now spans 0..360 and wraps, so 0° and 360° are one color. The old
  0..359 range put 359° and 0° one degree apart at opposite slider ends.
- Looks files from v0.2.6–v0.2.7 must be re-saved. A refused looks file
  stops startup with a non-zero exit, so under launchd it restarts every
  10 s [S1296] until the file is fixed. `run --dry-run` reads the looks
  file and checks each `--param`, so the unattended checklist's attended dry run
  finds a version-1 file before an unattended run does. A page built before this
  change cannot drive an engine after it, and the reverse.
- colorplasma keeps three colors, each a `color` in its own group with its
  cycle rate.

### Evidence

- [S1351:include/clap/ext/params.h#L78-L115][S1351:include/clap/ext/params.h#L212][S1351:include/clap/ext/params.h#L244-L251]
  CLAP: stable ids, plain-value storage, modulation as a plain delta,
  stepped/periodic/enum/modulatable flags, `module` kept out of the id.
- [S1352][S1353] VST 3: ids may never change; normalized automation breaks
  when a list grows; a changed id needs a remap interface.
- [S1350] OSCQuery: one record per address with type, range, unit, clip mode
  and access — the mapping target.
- [S1357] Chataigne's parameter library: one class per kind, a single color
  parameter, Point2D, and triggers outside the parameter type.
- [S1354][S1355] TouchDesigner: pages as layout; compound values as grouped
  per-component parameters.
- [S1359] xLights: the permanent load-path converter for value curves saved
  on the old 0–100 scale.
- [S1387] Python: an instance attribute shadows a non-data descriptor.

### Rejected alternatives

- **Grouping by a name convention** (`hue_a`, `saturation_a`), as the page
  did with `COLOR_PART`. A typo makes a loose slider, and the engine
  never knows the floats form one value. Pixelblaze's naming convention has
  the same gap [S203].
- **A color as adjacent scalars.** FFGL represents a color "as three Params"
  and the host checks "if the current one and the two followings" match
  [S1358]; TouchDesigner suffixes an index per component [S1354]. Grouping
  by position or suffix keeps the gap above and makes the refusal name a
  scalar, not the color.
- **Normalized 0–1 storage.** Every range change silently moves saved
  values. VST 3 automation "will be invalid now" when a list grows [S1352];
  CLAP notes knob-position automation is not robust to a range increase
  [S1351:include/clap/ext/params.h#L78-L115]; xLights still carries a converter
  for curves saved on the old 0–100 scale, with a version check and a
  warning that some "cannot be converted automatically" [S1359:src-core/render/ValueCurve.cpp#L1555-L1607].
- **JSON Schema plus a UI schema.** JSON Schema has no unit, periodic or
  color keyword [S1360], so each needs an extension key; react-jsonschema-form
  and JSON Forms then put widgets and layout in a second document that
  mirrors the first [S1361][S1362]. The kind record carries all of it in
  one place.
- **pydantic models.** LedFx shows they work for effect configs [S1356], but
  pydantic 2.14.2 pins pydantic-core, a compiled dependency with
  per-platform wheels [S1385], and its error text ("Input should be greater
  than 42 [type=greater_than, ...]") is not the refusal wording that the
  page, the looks loader and `--param` share [S1384].
- **OKLCH storage.** The engine's color math is HSV over linear-light
  primaries (`kit.hsv`, ADR-001); OKLCH would add a per-frame conversion and
  change every render, against the bit-identical port. The page's color
  picker speaks rgba, hsla or hsba only [S1364].
- **A palette param for colorplasma.** Each of its three colors has its own
  cycle rate, which one gradient does not express, and the port must render
  bit-identical. `palette` stays reserved for the first pattern that reads a
  gradient (this ADR's palette consequence).
- **A `trigger` kind.** ADR-009's 2026-11-02 amendment rejects events as
  param sets: a param persists, an impulse does not, and two in one frame
  collapse. Chataigne keeps `Trigger` outside `Parameter` [S1357], and
  TouchDesigner's Pulse is a separate momentary type [S1354].

## Amendment (2026-11-05) — trust model

The control plane decided above is, so far, the preview server: the page,
`/plan`, and the websocket that sets params, recalls looks, blacks out and
fires triggers (ADR-020). Architecture §5 stated its trust model with no
ADR, and the Host and Origin checks added in v0.2.6
(`docs/backlog/v0.2.x.md`, story "Phone control page") were recorded
nowhere in the synthesis. Code: `src/pewpew/sinks/preview.py`.

### Decision

- **No authentication, on a private network.** Any client that reaches
  the port can send any message. The server binds `127.0.0.1` unless
  `--host` names the private router's side of the laptop, never a shared
  network. WLED's JSON API and websocket take no credentials either
  [S550][S551]. An opt-in PIN or
  token is the later hardening for a shared network; TLS and user accounts
  are out of scope.
- **Last write wins.** The server applies messages in arrival order, with
  no locks, and pushes the merged state to every client, as decided above
  [S550][S551].
- **Any request whose `Host` is not an IP address or `localhost` gets
  403.** A page that rebinds its own name to the
  laptop's address (DNS rebinding) then cannot read the page or open the
  socket: rejecting unexpected `Host` headers is the server-side defense
  [S1390]. The operator opens the page by IP address, never by a `.local`
  name.
- **An upgrade whose `Origin` is not the request's `Host` gets 403**, so a
  page from another site, open in a browser on the private network, cannot
  drive the aura. RFC 6455 tells a server meant for certain sites only to
  check `Origin` and answer 403 [S522]. An upgrade with no `Origin` is not
  from a browser, and is accepted.
- **An input that listens elsewhere** (HTTP `GET`, OSC; both deferred) has
  no browser `Origin` to check, so it follows ADR-009's rule for network
  inputs (2026-11-02 amendment).

### Consequences

- The checks keep other web pages out, not other devices: the private
  router is the boundary.
- ADR-020's dev proxy rewrites `Origin` and `Host`, so the dev server
  makes the `Origin` check itself (`web/dev-origin.ts`).

### Evidence

- [S550][S551] WLED's JSON API and websocket: no credentials, one merged
  state pushed to every client.
- [S1390] Jackson et al. (CCS 2007): reject unexpected `Host` headers
  against DNS rebinding.
- [S522] RFC 6455 §10.2: a server for certain sites only verifies
  `Origin` and answers 403.

### Rejected alternatives

- **Authentication from day one**: it would break the third-party
  property the WLED-shaped control plane is built on [S550], when the
  private router already bounds who reaches the port.
- **The `Origin` check alone**: after DNS rebinding the attacker's page
  and the server share one origin, so `Origin` matches `Host` and passes;
  only the `Host` check refuses it [S1390].
- **Locks or CRDTs for concurrent writers**: concurrent control is rare,
  and a lost knob turn is recovered by turning the knob again; WLED merges
  in arrival order [S550][S551].

## Amendment (2026-11-05) — one shape per wire fact; looks file version 3

The 2026-11-04 amendment put each param's `value` in its record. The hello
carried the records with their values, while a change sent `declare` (the
records without values) and a `params` echo, so the page decoded params two
ways. The wire also carried fields no consumer read, and named one thing two
ways: `a`/`b` for a fixture's `start`/`end`, and `attract`, `dur`, `repeat`
for what the page and the per-look flag call the idle cycle. Code:
`src/pewpew/sinks/preview.py`, `src/pewpew/params/`, `src/pewpew/aura/`; the
wire is described in `web/src/wire/protocol.ts`.

Status stays **Proposed**.

### Decision

- **Each wire fact has one message and one shape.** The hello carries the
  map and the display gamma only. A new client then gets the current
  `status`, `declare`, `params`, `aura` and `health`, the same messages a
  change sends, so the page has one decode path for each. A param record is
  its declaration only; values travel only in `params`. WLED's JSON API
  likewise keeps effect metadata (`fxdata`) apart from the state that holds
  values [S550], and its websocket pushes the merged state on each change
  [S551].
- **One empty form per field.** An unset `group` or `widget` is `""` and no
  `text` is `[]`, the defaults the kinds take, so no record field is null.
  A color part is `{label, unit, lo, hi, step, decimals, periodic, text}`.
- **Fields no consumer reads are not sent:** the hello's `fps`; a look
  item's `pattern`, `fade` and `master` (an item is `{name, cycle}`); a
  trigger `last`'s `source`; a health board's `port` and `wled`.
- **Fixture ends are `start` and `end`** on the wire, as in the room file.
- **`status` says where an error comes from:** `{error, source, pattern}`,
  `source` one of `render`, `reload` or `looks` (null with no error), and
  `pattern` the pattern that raised, for a render error. The page leads a
  render error with what the room shows and what to do.
- **A trigger's `last` carries `error`**, why a fired event's look could not
  be held, and **the loop and sleep health rows carry a `fix`**, as board
  rows do. A board row says whether the board is `lost` (another device at
  its address, or two polls in a row unanswered); its fix sentence and the
  page's "use for" offer both follow that one field.
- **Looks file version 3, one name for the idle cycle.** The section is
  `"cycle": {"idle", "each", "rounds", "end"}` (it was `attract` with `dur`
  and `repeat`), matching the per-look `cycle` flag and the page's "idle
  cycle"; the looks state says `cycling`. It is this ADR's playlist [S550],
  with the looks to play flagged per look as in Chromatik's auto-cycle
  [S1265], under pewpew's own names. `version` is required: a file of
  another version, or of none, is refused with that one problem, for
  example `looks file is version 2; this pewpew reads version 3: move it
  aside and save the looks again from the page`.
- **A pick leaves every look.** After a pattern pick no look is current, in
  the file too, so a restart comes back in the command line's pattern. A
  recall that waits behind the fade is dropped, and a trigger's hold ends
  without returning.

### Consequences

- A page built before this change cannot drive an engine after it, and the
  reverse.
- A version-2 looks file stops the launch, and `run --dry-run` refuses it as
  a launch would, so the unattended checklist's attended dry run finds it. Its
  looks are saved again from the page; there is no migration.
- The describe golden (`tests/goldens/describe.json`) carries no `value`.

### Evidence

- [S550] WLED's JSON API: state, effect metadata and playlists as separate
  objects, and the playlist keys this file no longer copies.
- [S551] WLED's websocket: one JSON vocabulary, the merged state pushed on
  change.
- [S1265] Chromatik snapshots: the per-snapshot auto-cycle flag the `cycle`
  name follows.
- [S1350] OSCQuery: two forms for one state (`CLIPMODE` "none" or left out),
  the case the empty-form rule avoids.
- [S1359] xLights: a format converter that stays in the load path.

### Rejected alternatives

- **Values inside the records**, as OSCQuery puts `VALUE` in each address's
  description [S1350]: the hello and the echo then carry each value twice,
  and the page needs two decode paths for one state.
- **null for an unset field:** two empty forms for one record, which every
  reader has to fold into one. OSCQuery has this for no clipping:
  `CLIPMODE` "none", or `CLIPMODE` left out [S1350].
- **WLED's playlist keys `{ps, dur, repeat, end}`** [S550]: the looks file
  is pewpew's own and never reaches a board (2026-10-30 amendment), so
  matching WLED's keys buys nothing, and `attract` named what the page calls
  the idle cycle.
- **Reading version 2 through a key rename:** migration code, which the
  2026-11-04 amendment's clean-break rule rules out; such a converter stays
  in the load path for good, as xLights' value-curve converter has [S1359].

## Amendment (2026-11-05) — layered paths; palettes, routes and looks version 4

ADR-021 stacks layers and ADR-022 builds each layer from a graph of ops
whose args are params. Several params of one name now run at once (two
layers can both run `plasma`), a modulation source can drive any knob, and
a look holds a whole stack. The 2026-11-04 amendment left the `palette`
kind reserved and modulation unbuilt. Code (the params half, built):
`src/pewpew/params/` (`kinds.py`, `bound.py`, `values.py`) and
`src/pewpew/color/`. Backlog: `docs/backlog/v0.3.x.md`.

Status stays **Proposed**.

### Decision

- **The `palette` kind is active.** Its value is a frozen `Gradient`: a
  tuple of `Stop(at, color)`, each color the existing `HSV` value of the
  `color` kind, so pewpew stores one color model, plus a `label`. Its JSON
  form is the first array-valued one: `{"label": "ember", "stops": [{"at":
  0, "h": 30, "s": 0.8, "v": 0.3}, ...]}`, where `label` is a name of at
  most 64 characters: a preset's, the user's own, or empty (as it reads
  when left out). A label is a caption, never checked against the stops,
  so a preset is its label and its stops together, and a control matches a
  preset by both. Each stop's color is parsed by the `color` kind's parts
  and its `at` as a 0–1 `float`, so the refusal wording is the one that
  exists. A palette has 2 to 16 stops; the first is at 0, the last at 1,
  and each `at` is at least the one before it (two stops at one `at` make
  a hard edge). Stops out of order are refused, never sorted, so a decoded
  palette keeps its stops as given (encoding always writes `label`, `""`
  for one left out), and the page's control keeps its stops in order as
  one is dragged past another. Presets come from the declaration,
  `Palette(default, presets=...)`, as labeled gradients
  (`pewpew.color.PRESETS`); a value given as a preset's label alone, a
  string, parses as that preset, so `--param palette=ocean` works, and the
  stored value holds the stops, so a look stays self-contained. A
  palette's describe record adds `stop` (the numeric records of `at`, `h`,
  `s` and `v`), `max_stops` and `presets` (`[{value, label}]`, as
  `options` cross). Interpolation happens in OKLab, through `pewpew.color`
  (ADR-022), never in storage. A palette is not modulatable. The
  2026-11-04 rule "a stored value is a number, bool, string, or object of
  numbers" gains "or an object holding a list of such objects".
- **One address grammar:**

      layers.<lid>.(opacity|blend|enabled)
      layers.<lid>.<nid>.<arg>[.<part>]
      signals.<sid>.<arg>[.<part>]

  A pattern-only layer's single node id defaults to the pattern's name
  made into an id (lowercased, each character outside `[a-z0-9_]` as `_`,
  `p` before a first character that is not a letter, cut to 24
  characters, and `_` after a reserved word), because a pickable name is
  any Python identifier (`Glow`, a long stem, `blend`). So today's
  `plasma.speed` becomes `layers.<lid>.plasma.speed`. *(Superseded
  2026-11-07: no layer is pattern-only; see ADR-025.)* A layer,
  node or signal id matches `[a-z][a-z0-9_]{0,23}` and never changes
  (2026-11-04); `opacity`, `blend`, `enabled`, `nodes`, `out` and `alpha`
  are refused as node ids, and `layers` and `signals`, the heads of an
  address, as layer ids: a look's signals draw their random streams as a
  layer named `signals` would (ADR-022 keys). OSCQuery's `FULL_PATH` maps the grammar one to
  one, dots to slashes [S1350].
- **A `ParamSet` is named by its owner's path.** Its `name=` keyword, the
  refusal prefix, takes the owner's path and defaults to the pattern name,
  and the set reads it back as `owner` (the internal `pattern` field is
  renamed). A node's refusal then reads `layers.base.fold.sides must be
  within 1..24, got 40` with no new wording code.
- **Modulation is built.** A ranged kind (`Float`, `Int`, and so each
  part of a `color`) has `modulate(base, offset)`: wrap if `periodic`,
  clamp to `[lo, hi]` otherwise, round half up for `int`; a non-finite
  offset raises. Kinds without it (`bool`, `choice`, `palette`) cannot be
  modulated, by construction. The write goes through the set's binding:
  `ParamSet.apply(target)` returns a `Bound`, kept as `ParamSet.bound`.
  `Bound.drive(path, offset)` moves the target's attribute only (`path`
  is a param's name, or `name.part` for a color's part), `undrive(path)`
  and `settle()` return it to the base, and a `set` moves the base under
  the same offset. So the target holds the modulated value for the frame,
  while the slider, `snapshot_json` and a saved look see the operator's
  value. Applying the set again to the same target (a new room map) keeps
  the binding and its drives; after the set binds another target or a
  swap redeclares it, the old `Bound` refuses every call, so a stale
  binding never writes into a replaced pattern. The compositor is the
  seat (ADR-021): it evaluates the signal graph once per frame on the
  single clock, as ADR-010 resolves modulation, and drives each layer's
  route targets just before that layer advances.
- **A route is `{source, path, depth}`**, `depth` in the target's plain
  units (CLAP's plain delta [S1351]), checked at bind against the target's
  span (`|depth| ≤ hi − lo`). Routes may target `signals.*`; a cycle among
  signals is refused.
- **A describe record names its full path and nothing live.** For a
  layered knob, the record of the amendment "one shape per wire fact"
  keeps its shape, with `name` the full path and two added fields,
  `layer` and `node`, each `""` where it does not apply (a layer's own
  controls have no node, a signal's knob no layer), by that amendment's
  one empty form per field. It carries no value and no modulation: values
  stay in `params`; routes travel in `aura.stack` (ADR-021); and a
  modulated knob's current value travels in a throttled outbound
  `{"type": "mod", "values": {path: number}}`, sent at most 10 times a
  second, gated on an injected clock and rounded to the param's decimals,
  for the page's read-only readout.
- **`status` names the part that raised by its path:** the 2026-11-04
  `{error, source, pattern}` becomes `{error, source, path}`, where `path`
  is the address of what raised a render error, a layer's node
  (`layers.<lid>.<nid>`) or, once signals run, a signal (`signals.<sid>`,
  ADR-021), and null otherwise. Kept as `pattern`, one key would hold an
  address in `status` and a pattern's name in `aura`.
- **Looks file version 4.** A look holds `layers` (each `{id, opacity,
  blend, enabled, out, alpha, nodes}`, nodes keyed by id with `op`, `in`
  and `args`, and a `pattern` node naming its pattern by its `pattern`
  arg), `signals` (a graph of signal nodes keyed by id), `routes`, `seed`,
  `master`, `fade`, `cycle` and `front` (a layout-only list of paths shown
  first on the page). A pattern layer is a one-node program with op
  `pattern`. That node's `pattern` arg sits beside the pattern's params
  and has the address a param of that name would have
  (`layers.<lid>.<nid>.pattern`), so `pattern` joins the names a pattern's
  param may not take (ADR-005 amendment 2026-11-05). *(Superseded
  2026-11-07: there is no `pattern` op or node, and a book plays with
  `run LOOKS`; see ADR-025.)* The `triggers`
  section is unchanged from version 3; the `cycle` section takes the
  director's keys (amendment "the director", below). A version-3 file is
  refused with the existing wording (`looks file is version 3; this pewpew
  reads version 4: move it aside and save the looks again from the page`);
  there is no migration code. A `.look.json` file is a version-4 looks
  book, played with `run --looks FILE`; there is no second file form for
  one look. One codec reads and writes the look body (ADR-022), inside the
  book's envelope.

### Consequences

- Answers this ADR's palette consequence: palettes are params in the tree,
  addressable and saved with the look; Chromatik keeps palettes as global
  swatches [S1265], pewpew keeps them per op arg.
- The 2026-10-30 consequence names "the layer-compositing ADR (v0.2.9)";
  that is ADR-021, scheduled in v0.3.x. Its sentence "a
  crossfade becomes a compositor with two layers" no longer holds:
  ADR-021 rejects stacking inside the `Crossfader`, and that consequence
  now says so.
- A looks file from v0.2.8 stops a launch, as the version-3 break did.
  An unattended run uses `main`, and version 4 lands only on `fx`, which
  merges to `main` with the maintainer's go-ahead.
- `tests/goldens/describe.json` changed once, for the `palette` kind
  (built on `fx`). `ParamSet.describe` itself keeps its shape: the full
  path, `layer` and `node` come from the compositor's `Controls`, so they
  change `tests/goldens/wire.json`, once, with the first compositor.
- Tests (built for the params half): the wrap and clamp rule and `int`
  rounding at the edges, a drive that leaves the base and the snapshot
  alone, a rebind that keeps drives, a stale `Bound` that refuses, and a
  palette refused for each broken stop rule in the existing wording.

### Evidence

- [S1350] OSCQuery: hierarchical `FULL_PATH` addresses, one record per
  address — the target of the grammar.
- [S1351] CLAP: modulation as a plain-value delta, `IS_MODULATABLE` per
  param, and stable ids.
- [S1265] Chromatik: modulators patch onto any parameter with a mapped
  range, and palettes are first-class swatches.
- [S055][S1416] OKLab interpolation keeps a blue-to-white blend from
  drifting purple, and is the web platform's default interpolation space.

### Rejected alternatives

- **Flat `pattern.name` paths.** Two layers running one pattern would
  share every path.
- **A new `where=` keyword for the owner's path.** `name=` already set
  the refusal prefix; a second keyword for the same thing would leave two
  ways to name a set.
- **Modulating by writing the base**, as a plain `set` per frame. The
  slider would chase the modulation, a save would store a modulated value,
  and the rule that a set outside the range is refused (2026-08-22) would
  refuse the modulation's own writes. CLAP keeps modulation as a delta on
  top of the stored value [S1351].
- **A `value` or a `mod` list in each describe record.** The amendment
  "one shape per wire fact" took values out of the records so the page
  decodes each fact one way; a route list per record would put routes in
  two messages, and a value that moves every frame would resend every
  record that holds it.
- **Normalized 0–1 route depth.** A range change would silently rescale
  every route, the failure the 2026-11-04 amendment rejected for values
  [S1352].
- **A palette as several `color` params**, as colorplasma keeps three. The
  stop count is fixed by the declaration, and nothing interpolates between
  them.
- **A palette stored by preset name only.** A look would depend on a
  preset list that can change between versions; storing the stops keeps
  it self-contained.
- **OKLCH-stored palette stops.** The 2026-11-04 amendment rejected OKLCH
  storage, because the page's color picker speaks rgba, hsla or hsba only
  [S1364]; OKLab is used only to interpolate (ADR-022).
- **Evaluating signals per layer.** Each layer would pay for the signal
  graph, and two layers driven by one LFO could drift apart.

## Amendment (2026-11-05) — the director: a seeded, weighted idle cycle

The idle cycle above plays the flagged looks in file order, each for one
dwell, so an unattended run repeats one sequence. M9 (`docs/backlog/v0.3.x.md`)
asked for a cycle that does not repeat and that sometimes plays a look made
fresh (ADR-022 "Generation is a grammar over the catalog").

### Decision

- **The director picks each slot.** After `idle` seconds with no
  operator input, `pewpew.aura.director` plays the looks whose `cycle`
  flag is on: each slot draws one at random, as likely as its weight
  (`weights`, a look name to a number above 0, 1 by default), but none of
  the last `window` looks it played (0: any). Each slot lasts a dwell
  drawn from `each`, a number of seconds or a range `[min, max]`. After
  `rounds` rounds of as many slots as there are looks (0: forever), it
  plays `end` and stops; any operator input stops it, as before.
- **Fresh slots.** Every `fresh`th slot (0: never) plays a look made
  fresh from a seed of its own (pewpew.aura.variety), unsaved. It is named
  a slot ahead, so its look is made before the slot starts; a fresh look
  not made by then gives way to a drawn look for that slot.
- **Determinism.** Each slot draws from a counter-based stream keyed by
  the cycle's `seed` and the slot's number in the run [S1412], so the same
  inputs at the same engine times play the same looks for the same dwells,
  with no wall clock. The slot count, the looks last played and a fresh
  look still owed carry across an operator touch.
- **The file.** `cycle` takes `{idle, each, rounds, end, seed, window,
  fresh, weights}`; every key but `idle` has a default, and a refusal
  lists every key it takes.

### Consequences

- An unattended run varies its order and its dwells, and with `fresh`
  plays new looks between the saved ones.
- A cycle replays exactly from its seed, so a recording of engine time
  and inputs reproduces a run.

### Evidence

- [S1266] LedFx playlists play in sequence or shuffled, with a duration
  variation per item: the shuffle and the dwell range.
- [S550] WLED playlists: steps with a duration each, repeat and an end
  preset, the shape of `rounds` and `end`.
- [S1265] Chromatik's per-snapshot auto-cycle flag, the `cycle` flag a
  look keeps.
- [S1412] NumPy's Philox is keyed and counter-based, so a slot's draw
  needs no carried generator state.

### Rejected alternatives

- **Keep the file-order playlist.** An unattended run repeats one
  sequence, which is what M9 set out to stop; LedFx offers shuffle for the
  same reason [S1266].
- **A plain shuffle with no window.** A look could play twice in a row;
  the window bounds that, and 0 keeps the plain shuffle.
- **A generator seeded once per run.** A touch, or a fresh slot whose look
  is late, would shift every later draw; a stream per slot number keeps
  each slot's draw its own [S1412].

