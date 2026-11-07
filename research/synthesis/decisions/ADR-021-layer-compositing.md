# ADR-021: Layer compositing — a stack of renderers blended once in linear light

Status: Proposed (2026-11-05)

## Context

The engine renders one pattern at a time. `Renderer` holds one `Pattern`,
and `PacedLoop` drives one `FrameSource` (`src/pewpew/render.py`,
`src/pewpew/pace.py`). The only blend is the look crossfade, which runs two
renderers and mixes their linear frames (ADR-006, 2026-10-30 amendment).
Architecture §2 stage 2 stated a compositing decision with no ADR, and the
backlog story "Layer compositing — combine N patterns into one frame"
(`docs/backlog/v0.2.x.md`) waited on one. That story asks four questions:
is a layer a `Renderer` or something lighter; how do a layer's buffers
survive another layer being added or removed; are opacity and blend mode
params; and what happens when one layer of five raises.

Every surveyed tool composites the same way: an ordered stack, each layer
with a blend mode and an opacity, and one blend set that also serves
transitions. Chromatik has mixer channels with a fader, a blend mode, an
optional view onto part of the model, and one level of groups. WLED 16
overlaps segments with 17 blend modes, the lower segment at the bottom.
Resolume's blend modes serve layers, effects and transitions alike, and
xLights stacks effect layers per model. LX and WLED blend packed 8-bit
colors, and every source warns that Add runs to white.

ADR-022 gives a layer its content: an effect program. This ADR decides the
stack the programs run in.

## Decision

- **A layer is a `Renderer`.** Each layer gets its own `Renderer` on the
  shared mapping, feature source and clock: its own pattern, buffers,
  params, error and seed. A layer's pattern is a `ProgramPattern`
  (ADR-022), or, for a pattern-only layer, the pattern itself, run as `run
  PATTERN` runs it today. Bind, per-frame containment, the buffer registry
  with read-only locking, hot reload and `swap` then work per layer with
  no new code.
  *(Since 2026-11-07 a layer always runs a `ProgramPattern`, and no layer follows a
  file; see ADR-025.)*
- **Values.** `Layer(id, program, opacity, blend, enabled)`, `Route(source,
  path, depth)` and `Look(layers, signals, routes, seed, master, fade,
  cycle, front)` are frozen, slotted dataclasses; `Look` replaces the one
  in `src/pewpew/aura/book.py`, and its file form is looks v4 (ADR-006
  amendment "layered paths", which also owns the id rule). A layer holds a
  `Program` (ADR-022's `Node`, `Graph` and `Program`) from the first stack
  on: until effect programs land, each is one node whose op is `pattern`,
  so neither `Layer` nor the codec changes shape when they do.
  *(Superseded 2026-11-07: there is no `pattern` op; see ADR-025.)*
- **The `Compositor` is a `Live` source; no protocol module is added.** In
  `render.py`, `Live` (what the crossfader, the room map reload and the
  aura reach through a source) narrows to `t`, `advance_to`, `error`,
  `error_frame(t)` and `rebind`, which a `Renderer` and a `Compositor` both
  implement, and a new `SwapTarget` (`t`, `swap`) is all `Reloader` uses.
  `params` and `swap` leave `Live`: a stack has no one `ParamSet` and no
  one pattern. `PacedLoop` still drives a `FrameSource` (`t`,
  `advance_to`). The `Crossfader` becomes generic over a `Live`-bound type
  variable with its arithmetic unchanged, and a look recall crossfades two
  compositors. Every run drives a compositor: `run PATTERN` is a one-layer
  look whose layer id is `base`.
  *(Since 2026-11-07 `run LOOKS` plays a looks file; see ADR-025.)*
- **Controls reach layers, not the fader.** `AuraControl` reads the
  current compositor's `Controls` (`deck.controls`) where it reads
  `fader.params` today. A recall or a layer change replaces them, and
  `set` checks on the loop thread that they are still current, as it
  checks the `ParamSet` today. `Deck.recall(look, fade)` builds a fresh
  compositor at the fader's time and fades or cuts to it; it changes
  nothing unless every layer resolves and binds, as `Deck.start` does.
- **The compositor is the modulation seat.** Each frame:
  1. The feature frame is computed once. `features.py` gains
     `MemoFeatures`, a one-entry cache keyed on `t`, which every layer's
     `Renderer` shares, since each calls `features.at(t)` itself.
  2. The look's signal graph is evaluated once (ADR-022), and each route's
     offset is computed.
  3. Layers run bottom to top. A disabled layer is not advanced: it costs
     nothing and its state holds. When it is enabled again, its renderer's
     engine time is first set to the stack's previous frame time, so its
     first dt is one slot, as a spawned renderer's is (`Renderer.spawn`).
     The time it spent disabled, given as one dt, would ignite every pixel
     of `sparkle` and every column of `fire` in one frame. For each
     enabled layer, the compositor drives that layer's route targets
     through their `Bound`s (ADR-006 amendment "layered paths"), gives it
     a read-only view of the accumulator so far (`below`), and advances
     it. Nothing in `Renderer.advance_to` reads a param between
     `features.at` and `before_render`, so this seat gives the frame a
     seat inside the renderer would, and `render.py`'s frame path is not
     edited. Only route targets are driven, so an unmodulated param costs
     nothing.
  4. Unless containment (below) bypasses it, each layer's frame is blended
     into the compositor's own float32 (N,3) accumulator:
     `BLENDS[blend](acc, frame, opacity · alpha)`. A layer's frame is
     never written in place.
  5. The accumulator is clamped to [0, 1] once, at the end. The master
     and the blink, `PacedLoop` after-stages, act on the clamped stack, so
     an Add stack that sums to 1.6 under a master of 0.5 shows 0.5.
- **One blend table**, `BLENDS` in `src/pewpew/fx/blend.py`, keyed by a
  `Blend` StrEnum: `normal`, `add`, `screen`, `multiply`, `max`, `min`,
  `difference`, `subtract`, `stencil` and `highlight`. Each blend writes
  into a caller-owned accumulator in linear float32 (ADR-001). Each but
  `screen` clamps nothing. `screen`, 1 − (1 − a)(1 − b), assumes a white
  ceiling of 1, the reason overlay, dodge and burn are rejected below, and
  darkens above it (a and b at 1.6 give 0.64), so it reads both inputs
  clipped to [0, 1]. Weights are coerced with `np.float32`, so an
  `np.float64` opacity cannot promote the frame: the `Renderer`'s float32
  check covers a pattern's output, not the compositor's. The same table
  serves the combine ops inside programs (ADR-022). `stencil` is WLED's:
  the top where it has color, the bottom where it is black. `highlight` is
  LX's: the bottom plus the bottom times the top.
- **Masks, not views.** A layer covers the whole map. A program's optional
  `alpha` output (one scalar per point) restricts it, multiplied by the
  layer's opacity. There is no per-layer point-subset field.
- **No nested groups.** A stack-level effect is an ordinary layer whose
  program starts from `below()`, for example a feedback echo of everything
  beneath it. A layer that reads `below()` renders per pixel, so
  `units="fixture"` is refused for it.
- **Identity fast path.** One enabled layer with `normal` blend, opacity 1
  and no alpha returns that layer's frame object as it is: no copy, no
  blend and no clamp. Its values outside [0, 1] reach the sinks, which
  sanitize every frame after the master (NaN to 0, then clipped to
  [0, 1]; `pewpew.sinks.base.sanitize`), as they do for a lone pattern
  today. A one-layer run therefore renders the bytes a bare `Renderer`
  renders.
- **Derived seeds, every layer.** A layer's seed is the Python int
  `int(SeedSequence([look.seed, crc32(lid.encode())]).generate_state(1)[0])`,
  because ADR-022 shifts it into a 64-bit key. It is derived for every
  layer, `base` included, even when it is the only one, so adding a layer
  never changes another layer's picture. `hash()` never seeds anything.
- **`LayerControls` are params.** `opacity = Float(1, 0, 1)`, `blend =
  Choice("normal", <BLENDS keys>)` and `enabled = Bool(True)` are declared
  on a `LayerControls` class that is never run as a pattern. Describe
  records, refusal wording, page controls and modulation come from
  `pewpew.params`: opacity is modulatable, blend and enabled are not
  (ADR-006). Their paths are `layers.<lid>.opacity`, `.blend` and
  `.enabled`.
- **Containment per layer.** Each layer's `Renderer` turns its pattern's
  failure into an error frame, as now, and the compositor reads each
  layer's `error` once the layer has advanced, before the fast path or the
  blend. In development the failing layer's error frame is blended in its
  slot, so the author sees which layer failed. With `--unattended` a
  failing layer is bypassed (it adds nothing) and the status line names it,
  so a bad layer leaves the other layers lit. When a layer is bypassed and no
  blended layer's mode lights black (`multiply`, `min`, `subtract` and
  `highlight` over nothing stay black) at an opacity above 0, so the
  bypass leaves the room dark, the stack's frame is the error frame, as a
  lone pattern's is today: a failing look shows the pulsing red, never
  black. The opacity read is the knob's own value, not a route's: a route
  that swings opacity through 0 would otherwise flash the error frame, and
  faster than 3 Hz past WCAG 2.3.1 [S1464]. With every
  layer disabled, or with healthy layers whose blends stay dark, the
  frame is black, since nothing failed. Signals run
  outside any layer's containment: a signal that raises, or gives an
  offset `drive` refuses (a non-finite one), holds its last offset, and
  the status names it as `signals.<sid>`, so the stack keeps rendering. A
  setup failure stays loud: the look or layer is refused and what ran
  keeps running, as `Deck.start` does today.
- **Effects over the whole frame are `PacedLoop` after-stages.** The master and the
  blink already are (ADR-010, 2026-11-05 amendment). An effect the
  operator owns whatever look runs is a new after-stage; an effect a look
  owns is a top layer that reads `below()`.
- **The deck owns one `Reloader` per layer id.** "Put pattern X on layer
  L" is `Deck.put(layer, name)`, reached through `AuraControl.request` as
  `pick` with a `layer` field (null for the bottom layer, which is what
  the page sends today); it replaces that layer's renderer with no fade,
  as a pick cuts today. Each reloader swaps through a `SwapTarget` slot
  that looks up `fader.current.layer(lid)` when the file changes, so after
  a recall it reloads the incoming stack, never the outgoing one; a reload
  whose layer is gone is refused and logged, never raised into the aura.
  A recall re-points the reloaders with `follow`, starts one for a new
  layer id and stops the one for a removed id. A hot reload swaps only
  that layer's renderer and carries its buffers by name and shape
  (ADR-005). Adding or removing a layer leaves the other layers'
  renderers, buffers and seeds alone.
  *(Superseded 2026-11-07: there is no `pick` and no `Reloader`; see ADR-025.)*
- **The wire shows the stack.** `aura` carries `stack`: `{layers: [{id,
  nodes: [{id, op, label}]}], signals: [{id, op, label}], routes:
  [{source, path, depth}], front: [path], dims}`, layers in render order
  (the bottom first). A `pattern` node's `label` is the pattern's display
  name, never a file path (architecture §5). `dims` is how many axes the
  map spans (`pewpew.mapping.dimensions`). A layer's opacity, blend and
  enabled travel as params in `declare` and `params`, not in `stack`.
  `stack` ships in full with the first compositor, `signals`, `routes` and
  `front` empty until signals land, so `tests/goldens/wire.json` changes
  shape once.
- **Per-layer render time** is measured with an injected clock (`now`),
  as `PacedLoop` takes one, and exposed for profiling only: it never
  reaches a frame, and tests inject a fake clock.

## Consequences

- A one-layer compositor renders the same bytes as `Renderer(pattern,
  seed=layer_seed, features=f)`, where `f` is the compositor's own feature
  source (a bare `Renderer` would build `FakeFeatures(layer_seed)`), for
  any pattern, in range or not. Existing goldens stay on the bare
  `Renderer` path and do not change; blends get their own goldens, and a
  test passes an `np.float64` opacity through every blend and gets
  float32 back.
- The fast path and the blended path differ only for a frame outside
  [0, 1]: a lone pattern at 1.6 under a master of 0.5 shows 0.8, the same
  pattern at opacity 0.99 shows 0.5. The gallery stays in [0, 1]
  (`tests/test_canopy_patterns.py`), so for it the two paths agree.
- `run PATTERN` is a one-layer stack, so a pattern that draws from its
  seed (comet, fire, sparkle) renders the stream of `layer_seed(seed,
  "base")` under `run`, not `seed`'s: still deterministic, but a new
  picture. `tests/test_runner.py`'s check that `run comet` equals
  `render_sequence(Comet)` moves to that seed, and `PacedLoop`'s equality
  with `render_sequence` (`src/pewpew/pace.py`) then holds for the
  layer's renderer.
  *(Superseded 2026-11-07: there is no `run PATTERN` or `render_sequence`; see ADR-025.)*
- N layers cost N renders and N blends per frame. During a recall fade two
  compositors run. Phase-0 kernels cost 0.03–0.08 ms per frame at 3,000 px
  (`bench/results/throughput-2026-07-15-mac-m5pro.json`); the per-layer
  timing shows when a stack outgrows the budget.
- The aura addresses a layer by id. A live set names a full path
  (ADR-006 amendment "layered paths"), and the page lists layers from
  `aura.stack`.
- The wire golden, `web/src/wire/protocol.ts` and the page's wire
  test change with the first compositor, because the page checks the
  `aura` keys and the controls exactly.
- Normal blending at 50% mixes light, not encoded values, so a dim layer
  over a bright one looks brighter than the same blend on a screen. That is
  ADR-001's working space doing what it should.
- Layer add, remove, reorder and undo are tested as a stateful property
  test: render(undo(op(s))) equals a fresh-state render of s (a feedback
  layer's running state would fail a comparison with the running stack),
  the JSON round-trips, ids stay stable, and one raising layer is
  contained [S1138]. A raising signal is tested to leave the stack
  rendering.
- This answers the four questions of the v0.2.x story. The build is
  scheduled in `docs/backlog/v0.3.x.md`.

## Evidence

- [S1401] Chromatik's mixer: each channel has Enabled, Fader, View, Blend
  Mode and a crossfader assignment; groups blend as one channel and "may
  not contain other groups"; Normal is alpha "treated linearly".
- [S035] LX at its pin: `LXBlend.blend(int[] dst, int[] src, double alpha,
  int[] output, LXModel model)` writes a blend into an output buffer over
  a model's points, and buffers are packed `int` colors, 8 bits per
  channel. (Same project as [S1401]: one lineage, not two.)
- [S1403] WLED 16: overlapping segments, a blend mode per segment, the
  lower segment at the bottom; Stencil "Shows top where it has any color;
  shows bottom where top is black"; Add clamps at white and "can become
  very bright very quickly"; "Begin with two layers before trying five".
- [S1404] Resolume: one blend set for layers, effects and transitions; Add
  is its default and "Bright visuals can quickly max out at white".
- [S1405] xLights: effect layers per model, each blended over the layer
  below.
- [S1406] Winamp AVS: presets are stacks of render and transform
  components "arranged in any combination" — the visualizer lineage of the
  stack.
- [S645:wled00/FX_fcn.cpp#L1330-L1367] WLED copies a whole segment for a
  transition, the engine-level blend architecture §2 avoids; the
  crossfade of two stacks blends two frames instead.
- [S660:ledcontrol/animationcontroller.py#L418-L434] led-control's
  per-frame error frame, the containment each layer keeps.
- [S1413] Python randomizes `str` hashes per process unless
  `PYTHONHASHSEED` is set, so `hash(layer_id)` cannot seed a byte-identical
  render.

## Rejected alternatives

- **A layer as a bare render callable**, lighter than a `Renderer`. The
  `Renderer` already owns frame scoping, render purity, fixture units and
  containment (`src/pewpew/render.py` docstring), plus the buffer registry
  and hot-reload carry; a lighter layer would rebuild them beside it.
- **Blending in 8 bits with a clamp per layer**, as LX and WLED do
  [S035][S1403]. Each add clips, so light a later multiply or subtract
  would bring back is lost. Float32 linear with one clamp at the end keeps
  it (ADR-001).
- **A point-subset view per layer** (Chromatik views [S1401], WLED
  segments [S1403], LedFx virtuals [S305], projectMM layers
  [S715:docs/architecture.md#L285-L318]). It is a second way to restrict a
  layer beside alpha. An alpha output also gives soft edges and moving
  masks, with one mechanism; a selection can come back as a source op that
  feeds alpha.
- **Nested groups** (Chromatik's one level [S1401], AVS effect lists
  [S1406]). Chromatik itself stops at one level. A `below()` layer covers
  the group use, an effect over what is beneath, with no tree in the look
  file, the page or the address grammar.
- **One seed shared by every layer, or `hash(layer_id)`** [S1413]. A shared
  stream changes every layer's picture when one is added; `hash` differs
  per process.
- **Stacking inside the `Crossfader`.** A crossfade is time, a stack is
  space. Kept apart, the crossfade arithmetic stays as tested, and a recall
  fades between two whole stacks.
- **A new source protocol module, a compositor that is only a
  `FrameSource`, or a `Live` that keeps `params` and `swap`.** The
  protocols already live in `render.py`. The crossfader also calls
  `error`, `error_frame` and `rebind` on its source, and `Deck` and
  `AuraControl` reach its params; a stack has no one `ParamSet` to hand
  them and no one pattern to swap. Path-keyed `Controls` and per-layer
  reloaders name the layer they mean.
- **The modulation seat inside `Renderer.advance_to`.** It would edit the
  frame path every bare renderer and every golden runs through, for a
  frame the compositor seat already gives, since no param is read before
  `before_render`.
- **Clamping the fast path too, or no clamp in the stack.** A clamped fast
  path copies every frame of every one-layer run and breaks its byte
  identity with a bare `Renderer` for a pattern that leaves [0, 1]. With
  no stack clamp, the master's effect on a blended stack would depend on
  how far the layers overshoot.
- **Wall-clock per-layer timing read inside the compositor.** No wall
  clock is read in pattern or coordination code (`CLAUDE.md`); an injected
  clock keeps the frames independent of it and the tests deterministic.
- **Advancing a disabled layer without blending it.** Its clock would keep
  step, but it would cost a full render every frame for a layer nobody
  sees; re-anchoring its clock on enable gives the same one-slot dt for
  nothing.
- **Bypassing the last failing layer under `--unattended`.** The room would go
  black, which reads as a dark look, not a failure; the error frame never
  drops below 25% so that it cannot be mistaken for one [S660].
- **Every blend mode the tools list** (17 in WLED [S1403], about 25 in
  Resolume [S1404]). Overlay, soft light, hard light, dodge and burn are
  defined on display-encoded values with a white ceiling; in linear light
  with an unbounded sum their meaning is unclear (inference). The ten kept
  cover the uses the sources describe: crossfade, light adding, masking
  and contrast. `screen` is the one kept formula with a white ceiling, so
  it reads its inputs clipped to [0, 1].
