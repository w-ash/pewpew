# ADR-022: Effect programs — typed node graphs of ops, declared with params, saved as JSON

Status: Proposed (2026-11-05)

## Context

A pattern is a Python class (ADR-005). The idiom kit has no noise, no
palettes, no coordinate folds and no 3D or bilinear sampling, and nothing
lets one effect warp, mask or modulate another. Ten gallery patterns are
ten fixed looks.

The visualizer lineage gets its variety from composition, not from more
fixed effects. Hydra builds a look from 53 functions in five type
signatures (sources, coordinate transforms, color transforms, two-input
combines, and combines that warp coordinates), and any function composes
with any other. MilkDrop's signature is feedback: the previous frame is
warped and decayed each frame. Winamp AVS builds a preset from components,
and its web port saves one as a list of typed components. ISF declares
each input with a type and a range, which ADR-006 already copies for
params.

ADR-021 decides the stack a layer runs in. This ADR decides what runs
inside a layer, and how it is declared, checked, saved and described, so
that people, the page and agents (ADR-023) all work from one model.

## Decision

- **One graph model with three value types.** `Ty` is `signal` (one float
  per frame), `scalar` ((N,) float32) or `rgb` ((N,3) float32). Each op has
  a signature, `Sig`: `source`, `coord`, `color`, `combine`, `modulate`
  (a second input warps the first's coordinates) or `signal`. A port is
  `Port(name, ty)`, where `ty` may be `"same"` for a type-preserving coord
  op.
- **Frozen values.** `Node(id, op, args, inputs)`, `Graph(nodes)` and
  `Program(graph, out, alpha=None)` are frozen, slotted dataclasses. A node
  id follows the id rule and reserved words of the address grammar
  (ADR-006 amendment "layered paths"). A graph is a DAG kept in
  topological, insertion order: a cycle is refused, fan-out is allowed.
  The layer stack defines these values first (ADR-021), so programs add
  ops, not a new shape.
- **Feedback is never a cycle.** `prev()` is a source that reads the
  layer's last frame; `feedback(in, ...)` is a stateful node that keeps its
  own buffer.
- **Coordinate ops wrap what comes before them; color and combine ops
  apply forwards** — Hydra's rule. `osc().rotate()` rotates the
  oscillator's coordinates.
- **An op is to a node what a `Pattern` class is to a pattern.** Each op
  is a subclass of `Op(ABC)` that registers itself through
  `__init_subclass__(op="kaleid")`, as `Pattern.__init_subclass__` checks
  pattern classes. A class with the same module and qualified name
  replaces the entry, which hot reload needs; a different class under a
  taken name is refused. Class attributes: `sig`, `inputs`, `out`, `dims`,
  `stateful`, `examples` and `cost`. Hooks: `setup(ctx)`, `advance(ctx,
  inputs)` for stateful ops only, and `build(inputs) -> closure`, called
  once per bind.
- **Op args are `pewpew.params` params.** An op declares `sides = Int(5,
  1, 24)` as a pattern does, and `declared_params` reads it unchanged. An
  arg may not take the name of a class attribute the catalog reads (`op`,
  `sig`, `inputs`, `out`, `dims`, `stateful`, `examples`, `cost`), because
  it would shadow it, as `units` and `warpable` are refused as a pattern's
  param names. Each node's args are a `ParamSet` whose `name=` is the
  node's path, so a refusal names the node (ADR-006 amendment "layered
  paths"). Describe records, refusal wording, page controls, liveness
  tests and modulation come from one package; there is no second
  declaration system. A closure reads its args when it runs, so a live set
  shows on the next frame.
- **Signals and routes.** Signal ops (`lfo`, `env`, `band`, `beat`, `walk`,
  `knob`, `smooth`) form the look's signal graph, evaluated once per frame
  by the compositor (ADR-021). `Route(source, path, depth)` drives a
  modulatable param by `depth × signal`; ADR-006's amendment "layered
  paths" decides its units, its span check and the refused cycle. A macro
  is a `knob` with several routes, not a new type.
- **No callables as args.** Every value serializes. "An arg as a function
  of time" is a signal node plus a route, and the builder's refusal says
  so.
- **The fluent builder is sugar over the same values.**
  `osc(8, .1).kaleid(5).modulate(noise(3), .2).palette(...)` builds a
  `Program`. Literal args are parsed when built, with the same `ParamSet`
  wording. An id comes from `.id("waves")`, or else from the op name plus a
  deterministic ordinal; a builder object used twice is one node. A
  signal passed as an arg becomes a route. A stub file (`expr.pyi`)
  generated from the catalog gives editors completion, and a test fails
  when it drifts.
- **The catalog is the one description source.** One record per op: `op`,
  `sig`, `label`, `doc`, `inputs`, `out`, `dims`, `stateful`, `params` (the
  existing describe records), `cost` and `examples`, each example as
  fluent Python and as JSON. `cost` is `{ns_per_point, us_fixed}`:
  `us_fixed` is what a call costs whatever the map's size, a feedback
  grid's cells and deposited particles included. The catalog is a golden
  file. The page, the CLI, the MCP server, the generated docs and the
  tests read it; nothing describes an op twice. It is a custom record,
  not JSON Schema, as ADR-006 decided for params.
- **One codec.** `fx/codec.py` is the only module that turns JSON into
  values or back. `decode` never raises: it returns the value or None and a
  list of problems, each prefixed with its path, reusing `ParamSet.parse`
  wording, with a did-you-mean for an unknown name and type errors that say
  how to fix them. `encode` writes a fixed order. `to_python(program)`
  prints the fluent chain. One `check(program) -> problems` serves the
  builder and the codec.
- **`ProgramPattern` hosts a program in a normal `Renderer`.** It is a
  `Pattern`, so `load`, hot reload and `run file.py` work unchanged and the
  ADR-005 contract gains no hook. At bind it builds one op per node and
  applies the node's `ParamSet` to it, calls each op's `setup` (a node
  buffer is the host's `self.buffer(f"{nid}__{name}", ...)`, so it is
  locked read-only in `render` and carried across hot reload), then builds
  the closures bottom up. Stateful nodes advance in `before_render` in
  topological order, so `render` stays pure. A node's exception gets
  `exc.add_note("in node layers.<lid>.<nid> (<op>)")` and is contained by
  the `Renderer`. `errors.describe_exception` appends an exception's
  notes, scrubbed, so the status line and the page name the failing node,
  not only the logged traceback.
- **Node `ParamSet`s live as long as the host.** The host keeps each
  node's set by node id and hands it on, node by node, at a hot reload or
  a swap, as `Renderer.params` survives a reload of a pattern. A node
  whose op or args changed takes the values that still fit (`inherit`, the
  2026-08-22 reload rule), and a removed node's set goes.
- **The `pattern` op.** A pattern-only layer runs any pattern in the
  layer's own `Renderer` (ADR-021), fixture units included. Inside a
  program with other nodes, a `pattern` node takes only a pixel-unit,
  warpable pattern (ADR-005 amendment 2026-11-05): a fixture-unit pattern
  (`sparkle`, `pulse`) renders at fixture centres, not at the program's
  points, so it is refused there with the fix (put it on its own layer).
- **Dimensions.** Each op declares `dims` from {1, 2, 3}; a mapping's
  dimension is the number of axes it spans (`pewpew.mapping.dimensions`).
  An op that does not support it, or a coord op above a non-warpable
  pattern or above per-point state, is refused at check time with a fix
  (`kaleid` on a strip: "use `mirror` on u"). ADR-005's 2026-11-05
  amendment defines warpable patterns and `Coords.u`.
- **Ops centre on the map.** `BindCtx.centre` is the middle of the map's
  extent on each axis, (min + max) / 2: 0.5 on each axis a `line`, `grid`,
  `lattice` or room map spans, 0 on an axis with no extent, and the
  strip's or plane's own position on an axis `dimensions` counts as flat
  but that has some extent (a hand-measured strip that rises 3 mm over 4 m
  sits near y = 0.5, since the room map centres every axis with any
  extent; `src/pewpew/room/map.py`). Ops pass it to the primitives as
  `center`. The primitives' own default, `MID = (0.5, 0.5, 0.5)`, and a
  flat axis fixed at 0 would each pivot a fold, a shape or a tunnel half a
  unit off a strip's line or a panel's plane and show its edge.
- **Ops are built on plain NumPy primitives** (`pewpew.fx.prims`): `vec`
  (a point batch is a `Vec`, a tuple of per-axis float32 arrays, so one
  axis can be a scalar such as time), `noise` (value and gradient noise,
  fBm, ridged, turbulence, curl, domain warp), `space` (rotate, scale,
  polar, kaleidoscope, mirror, twist, tunnel, repeat), `sdf`, `sample`
  (linear reads of a field in as many dimensions as the point has, with
  clamp or wrap edges; `advect`; projections), `grid` (`deposit`, the
  adjoint of `sample`) and `knn` (an exact nearest-neighbour graph from a
  grid hash, with `diffuse`, `wave_step` and `gray_scott_step`, which
  refuse settings that would diverge). Each reads no clock and no
  global RNG and keeps float32, which NumPy 2's promotion rules hold, so
  `numpy>=2` is the floor. No scipy and no other runtime dependency.
- **Counter-based randomness, one key per tick.** A node draws from
  `Generator(Philox(key=[node_key, tick]))`, built in `advance`, where
  `node_key = (layer_seed << 32) | crc32(f"{lid}/{nid}".encode())` in
  Python ints, so the look's seed fills the key's high 32 bits (under
  NumPy 2 an `np.uint32` shifted by 32 is 0, which would drop the seed
  from every node's draws), and `tick` carries across reload. The tick
  goes in the key, not the counter (rejected below), because different
  keys give independent streams [S1412].
- **Float rule.** Time stays a Python float, and no op computes a phase
  as `t * rate` (rejected below). An op with a rate arg, and every signal,
  keeps its phase as node state: `phase += rate * dt` in a Python float in
  `advance`, wrapped into its period, carried across reload, as the gallery's
  `pulse`, `plasma` and `wave` keep theirs; so the phase speed stays
  within the rate's own range at any engine time, and a rate change never
  jumps. A phase is one number, not per-point state, so a coord op may sit
  above such an op. Its closure reads the phase; array math is float32.
- **Palettes interpolate in OKLab.** The `palette` kind's value (ADR-006
  amendment "layered paths") turns into a 256×3 float32 linear table
  through `pewpew.color.gradient_lut`, which interpolates between stops in
  OKLab, moves an out-of-gamut color in by chroma, and is cached by value;
  the `palette` op reads it (`pewpew.color.sample`). A palette is not
  modulatable, so hue drift is the palette op's own periodic `shift`.
- **Generation is a grammar over the catalog.** `surprise.generate(seed,
  mapping, *, audio=False)` takes the mapping, because the ops a look may
  use depend on its dimension and each candidate is rendered and gated
  (check, flash, darkness, motion) before one is returned; `mutate(look,
  seed, strength, keep)` changes a look. Both sample only inside declared
  ranges, stay within a cost budget summed from the catalog's `cost`, cap
  route rates so the result is flash-safe, and are byte-deterministic for
  a seed.

## Consequences

- A new op is one class with params and examples. Its catalog record, page
  card, CLI listing, MCP search result and docs follow from that; no tool
  definition changes (ADR-023).
- The ADR-005 contract is unchanged in shape. A hand-written pattern is a
  one-node program (op `pattern`), so the gallery runs in a stack as is.
- Hydra is AGPL-3.0 [S1400]. Under ADR-012 it is an idea source: the
  vocabulary is reimplemented from the documented findings, and no Hydra
  code is copied.
- A program pays one closure call per node per frame on top of its array
  math. Measured on this host for the primitives (`fx` at b17f82d, NumPy
  2.4.6, median of 50 calls at 300, 1,000 and 5,000 points, a straight
  line fitted): a rotation costs about 1 ns a point plus 3 µs a call;
  3D gradient noise 34 ns plus 58 µs; four-octave fBm 137 ns plus 244 µs;
  domain warp 427 ns plus 727 µs; a deposit of 500 particles 50 µs at any
  size; the kNN graph about 10 ms at 5,000 points, once per bind.
- Per-point state ((N,) arrays) cannot be read at warped coordinates.
  State that must be warped lives on a grid and is read with
  `prims.sample.sample` at the warped points.
- The research advice to pass `t` as float32 is not taken: a float32 time
  loses precision on a multi-day run (inference); phases accumulated in
  Python floats keep the speed and the precision.
- Tests hold these rules: every catalog example is float32 at every node;
  a node's draws at two consecutive ticks share no shifted run; a rate
  driven by a route an hour into a run moves the phase no faster per
  frame than at t = 0; a raising node is named on the status line; a set,
  a hot reload and a second set leave the node's set accepted and its
  value kept; an arg named after any class attribute the catalog reads is
  refused.

## Evidence

- [S1400] Hydra: five transform types; a `coord` step rewrites `uv` before
  the earlier steps run, so coordinate ops wrap what precedes them; a
  chain passed as an argument compiles recursively; a function or array
  argument becomes a per-frame uniform.
- [S1407] MilkDrop: a preset is a set of parameters; the previous frame is
  warped and decayed each frame, and shapes can be textured with it — the
  feedback that `prev()` and `feedback` model without a graph cycle.
- [S1406][S1408] AVS presets are stacks of typed components, and webvs
  saves them as plain JSON (`{"components": [{"type": ...}]}`): an effect
  graph saved as data, not code.
- [S214] ISF declares typed, ranged inputs beside the shader — args as
  declarations (ADR-006's precedent, reused per op).
- [S1409] Polars: its own expression serialization "is not stable across
  Polars versions" — a library's internal tree is not a save format, so
  pewpew owns a versioned codec.
- [S1410] Python's `__init_subclass__` runs on the base class whenever a
  class inherits from it: one registry, no decorator, no import-time list.
- [S1412][S1413] NumPy's Philox is keyed and counter-based: its counter
  steps once per four 64-bit draws, and different keys give independent
  streams, so a draw is a function of (node, tick) with no overlap
  between ticks; `hash()` is randomized per process.
- [S055][S1416] OKLab: HSV and CIELAB blends toward blue drift purple and
  OKLab does not; CSS Color 4 makes Oklab the default interpolation space.

## Rejected alternatives

- **Expression strings** (MilkDrop equations [S1407], Pixelblaze
  [S680], ARTI-FX [S207]), even an AST-whitelisted NumPy subset. ADR-005
  already rejected a language and VM. A string declares no ranges, so the
  page, generation and the refusal wording cannot reach inside it; it is a
  third way to declare a knob.
- **Callables as args**, as Hydra turns functions into uniforms [S1400].
  A lambda does not serialize, cannot be checked, and cannot be shown on
  the page. A signal node plus a route does all three.
- **A layer stack only, with no graph inside a layer.** Layers blend
  colors; they cannot let one effect warp another's coordinates, which is
  Hydra's `modulate` [S1400] and AVS's Dynamic Movement [S1406].
- **Saving the builder's object tree** (pickle, or a library's own
  serializer [S1409]). It ties a saved look to one version of the code.
- **Entry-point plugin discovery for ops** [S1414]. It finds installed
  packages, not a `.py` file passed to `run`, and does not see a hot
  reload. The in-process registry covers all three.
- **Feedback as a graph cycle.** Evaluation order inside a cycle is
  undefined. MilkDrop's feedback is a one-frame delay on the previous
  image [S1407], which `prev()` and stateful nodes give directly.
- **JSON Schema for the catalog** [S1360]: no unit, periodic or color
  keyword, as ADR-006 found for params.
- **The tick as Philox's counter** (`counter=tick`) [S1412]. The counter
  steps once per four 64-bit draws, so frame `tick + 1` would replay frame
  `tick`'s draws shifted by one block: a per-pixel random field slides
  four to eight pixels a frame instead of changing (observed with NumPy
  2.4).
- **A phase as `(t * rate) % 1.0`.** It needs no state, but under a route
  the phase speed is `rate + t · d(rate)/dt`, which grows with engine time,
  and a live set of the rate jumps the phase. A rate of 0.25/s under a
  0.1 Hz route of depth 0.05/s peaks near 113 cycles a second at t =
  3600 s (inference), far past WCAG's 3 flashes a second, and `verify
  looks`, which renders a few seconds from t = 0, cannot see it.
- **A cost per point only.** The measurements above put most of a noise
  op's cost on a 300-pixel strip in its fixed term, so a cost per point
  alone would misjudge small maps by several times; and a feedback grid
  or a particle deposit costs per cell or per particle, not per point. A
  budget from points alone would pass looks that miss the frame.
- **A node `ParamSet` built fresh at each bind.** Simpler, but
  `AuraControl` checks a set's identity before it writes, so a reload
  would orphan the set the aura holds and its next live set would be
  refused.

## Amendment (2026-11-05) — generation hints, and programs as built

Code: `src/pewpew/fx/` (`op.py`, `ops/`, `compile.py`, `host.py`,
`expr.py`, `codec.py`, `catalog.py`, `cli.py`) and `src/pewpew/params/kinds.py`.

### Decision

- **A ranged param carries two generation hints.** `Float` and `Int`
  take `sweet=(a, b)`, the part of the range where the knob looks best
  (the whole range when not given), and `flash_sensitive`, which says a
  fast change of the knob changes brightness at a point. Every `float`
  and `int` describe record carries both (`"sweet": [a, b]`,
  `"flash_sensitive": bool`), so `describe.json` and `wire.json` change
  once, here, and `surprise` (M9) reads them and nothing else. They are
  declared, not inferred from the unit: a layer's `opacity` has no unit
  and is the knob most likely to strobe under a fast route, against WCAG's
  three flashes a second [S1464]; and a generator that samples the whole
  range an operator may set draws mostly poor looks (inference, from the
  RA-25 notes on seeded generation). They never limit a value. Layer
  `opacity`, and every rate an op's crests or turns pass a point at, are
  flash-sensitive.
- **A rate is a `Rate` param**, a `Float` to every surface, whose phase
  the op keeps (the float rule), wrapped into its period centred on 0, so
  a phase that starts at 0 runs either way for half a period before it
  wraps. A drift (a noise's or a tunnel's) has the period 4096: within
  +-2048 float32 resolves a slow frame's step. A drifting noise loops its
  lattice along the drift axis at that period (its hash takes each cell
  index modulo 4096), so its wrap is seamless; what a tunnel reads need
  not repeat along depth, so the tunnel jumps once per wrap, every
  4096 / |speed| s.
- **`Op.warpable`** says a node gives a correct field at points other than
  the map's own. A pattern node takes its pattern's flag; `below` and
  `prev`, which hold one value per point, say False, as stateful nodes
  will. One check, "a coord op, or a modulate's first input, above a node
  that is not warpable", serves the pattern-node rule and the per-point
  state rule.
- **`plane` may be `auto`**, the two axes the map spreads most along, so
  a fold or a shape works on a wall as on a floor. A field that evolves
  (noise, voronoi) moves along the map's flat axis, so it changes in place
  on a strip or a panel.
- **Reload of a node's knobs.** A knob the operator moved from the old
  program's literal keeps its live value where the new declaration takes
  it; any other knob takes the new program's literal. A program file's
  literals are its content, so an edited literal must show on save; the
  2026-08-22 rule (keep every live value that fits) would hide it. The set
  itself is kept by node id, as decided above. A look that runs a pattern
  file whose class is a program keeps its one pattern node, the file
  link; a knob moved from the file's literal is saved on that node as the
  arg `<nid>.<arg>`, which a recall starts the node at as a moved knob,
  so a save, a recall and the liveness gate see the operator's value
  (ADR-006 "layered paths"). Expanding the node into the program's nodes
  was rejected: it would drop the file link, and a later edit of the file
  would no longer show.
- **Names.** A hosted program's renderer is named by the layer's address
  and each node's set by `layers.<lid>.<nid>`; a node's lid in its key is
  the last part of that name. A pattern node's pattern is seeded with its
  node's 32-bit seed, drawn from the node key, so a pattern in a program
  draws a stream of its own.
- **A program is checked against its map at bind**, so a look whose
  program the map cannot run is refused whole (`LayerError`), with each
  problem named by its node's address. A pattern file that turns into a
  program, or back, takes a restart, since its knobs change address. A
  program that reads `below()` runs per pixel, so `--units fixture` is
  refused for it.

## Amendment (2026-11-05) — stateful ops

Code: `src/pewpew/fx/field.py`, `src/pewpew/fx/ops/state.py`, `sims.py`,
`swarm.py`; tests `tests/test_fx_state.py`.

### Decision

- **A `state` signature.** An op that reads an input and keeps state
  from frame to frame (`feedback`, `trails`, `diffuse`) has `sig =
  state`, so the catalog lists it apart from the color ops, which map a
  value at the same point. A simulation that reads nothing (`ripple`,
  `reaction`, `life`, `particles`, `attractor`) stays a `source` with
  `stateful` set.
- **`BindCtx.gives`** is the type a node gives, so an op whose output is
  `same` (feedback, trails, diffuse) sizes its buffer for a scalar or an
  rgb field at bind (`BindCtx.channels`). The host and `check` work the
  types out with one function, `compile.node_types`.
- **Grid state lives on a `Lattice`** over the map's spanned axes: `u`
  on a strip, the map's plane on a panel, x, y, z in a volume, the last
  axis "up". Its cells are square in world units and a few times finer
  than the points (3 on a strip or a panel, 2 in a volume, at most 4096,
  128², 32³ nodes), since a field moved a little each frame and read back
  by interpolation blurs at the scale of its cells (RA-25 notes; MilkDrop
  draws the warped last frame at screen resolution [S1407]). Such state
  reads at any point, so a coord op may sit above `feedback`,
  `particles` and `attractor`; state held per point (`trails` and the
  graph sims) is not warpable. A state op reads its input at the map's
  own points before render, so `check` stops its walk for a warped node
  there: a coord op above `feedback` may warp it whatever it reads.
- **Feedback composites by the brighter of field and input, never by
  adding.** A field that adds its input settles at 1 / (1 - fade) times
  it, about 21 times at a 0.7 s decay and 30 fps (inference from
  `kit.fade`), which is the ratchet to white of the ADR-005 amendment of
  2026-07-27; the brighter-of rule bounds the field by the brightest the
  input has been. The input is known at the map's points only, so it
  reaches the field by normalized convolution (weighted values and
  weights spread and blurred alike, then divided).
- **Graph sims are stable at every knob setting.** Each takes as many
  explicit steps a frame as its speed needs (at most 32), each inside its
  scheme's limit (the limits are `pewpew.fx.prims.knn`'s), so a knob can
  slow a simulation but never make it diverge; the primitives' refusals
  stay as the guard for code that calls them directly. Nor does one
  drift over minutes: a `ripple` drop adds as much water as it takes,
  and its damping fades the whole pond, level and rings alike, so each
  part of a graph in parts settles too (velocity damping alone left the
  level free to climb to white); `life` moves a point on when one
  neighbour is ahead, and random sparks start new waves where they die
  out, since on the nearest-neighbour graph a higher threshold, and on a
  strip any setting, settled to a still frame within seconds (inference:
  measured on 60-point strips, 16x16 panels and 8x8x8 lattices).
- **Random events are a Poisson process per node**, drawn from the
  node's Philox stream keyed by its key and the tick [S1412], with the
  countdown in a node buffer: the first event falls on the first frame,
  and a hot reload carries the process on.
- **Rejected:** feedback that adds its input (the ratchet above); a
  `feed` and `kill` pair for Gray-Scott in place of a `kind` choice
  (most of the plane grows nothing, and a look generator sampling it
  would mostly draw dead looks; inference); a fixed `count` buffer for
  particles (a knob that resizes a buffer would drop the state on every
  move; a fixed pool with a birth rate keeps it).
