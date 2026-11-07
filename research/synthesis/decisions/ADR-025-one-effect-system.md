# ADR-025: One effect system — looks over the op catalog, everywhere

Status: Proposed (2026-11-07)

## Context

Two effect systems run side by side. The first is ADR-005's: a pattern is
a Python class, the gallery holds eleven of them, `run PATTERN` plays one,
a user's `file.py` or `--pattern-dir` adds more with hot reload, and a
pattern may render per fixture (ADR-007, 2026-10-30 amendment). The second
is ADR-021's and ADR-022's: a look is a stack of layers, each an effect
program over the op catalog, saved as JSON (looks version 4).

The second absorbed the first instead of replacing it. A program may hold
a `pattern` node, a layer that is one pattern node runs the pattern
directly in the compositor, `run` still needs a pattern before `--looks`,
the aura still takes a `pick`, and an op registers only when a pattern file
loads. The hosted studio (ADR-024) uses only the first system: each
visitor runs one gallery pattern with a flat param set, through its own
session code and its own page controls. So a knob, a layer and a saved
effect each have two shapes, and two front ends describe params two ways.

The maintainer wants one compact, composable system with clean breaks and
no second way to do anything, and decided (2026-11-07): drop the six
gallery patterns that no op reproduces (plasma, colorplasma, fire, geq,
sdf3d, comet), drop hand-written Python effects, drop fixture units, and
give the studio the control page's full look editor, with no looks saved
server-side.

## Decision

- **A look is the only effect.** Looks version 4 over the op catalog
  (ADR-022) is the one authoring surface, for people, the control page, the
  studio and agents (ADR-023). A look is data: every op it names is in the
  catalog, every arg is a declared param, and the codec checks it whole
  [S1408][S1400].
- **The gallery, the `pattern` op and the direct-pattern layer go.** A
  layer always hosts a program. A look that names op `pattern` is refused
  as any unknown op is, with the codec's wording. The looks file stays at
  version 4: its shape does not change, so there is no version bump and no
  migration code.
- **No hand-written Python.** `run file.py`, `file.py:Class`,
  `--pattern-dir`, pattern-file hot reload (`Reloader`) and op registration
  from a loaded file go. A new effect is a new op in `src/pewpew/fx/ops/`,
  with its tests, catalog record and examples (ADR-022). The authoring loop
  is `fx check`/`render`/`compare` and the MCP tools.
- **No fixture units.** Every layer renders per pixel. `Pattern.units`,
  `run --units` and the per-fixture gather go. Room maps keep their
  fixtures for wiring, power and DDP (ADR-007).
- **`run LOOKS` plays a looks file.** The file is a version-4 book (a
  `.look.json` included) and the run starts in its `current` look. It
  replaces `run PATTERN --looks FILE`; `--param` and `--map auto` go with
  the launch pattern, and a run without `--map` or `--room` uses
  `grid:16x16`.
- **The studio runs the aura.** One factory in `pewpew.aura` builds the
  pipeline that `run` builds today (compositor, crossfader, deck, master,
  variety, triggers, `AuraControl`), and the studio session calls it.
  The studio's websocket takes the aura's requests (`aura.control.REQUESTS`)
  and sends the per-frame states the preview sends (`declare`, `params`,
  `mod`, `aura`, `catalog`), through one function both transports call; it
  adds only `bind`, `pause` and `resume`. The session takes whole looks
  (`accept_looks`) and has no looks file and no boards, so the requests
  that need either are refused by the existing code. `/api/patterns` and
  the `pattern` message go; `/api/looks` serves the example looks.
- **One page library.** The wire store, the params decoder, the knob panel,
  the layer list and the add-layer cards move from `web/` into one package
  that `web/` and `studio-web/` both import.
- **`Pattern`, `Renderer`, `Crossfader` and `ParamSet` stay, as
  internals.** `ProgramPattern` is a `Pattern` and every layer is a
  `Renderer` (ADR-021, ADR-022); the crossfader fades two stacks and op
  args are param sets. None is exported or documented as an author API.

## Consequences

- Removed: `src/pewpew/patterns/`, `pewpew.load`, `fx/ops/pattern.py`,
  `Reloader`, the aura's `pick`, the `pattern`/`patterns` fields of the
  `aura` state, `render_sequence`, the author exports of `pewpew`, and
  the per-pattern goldens. The removed effects' looks are gone with them:
  wave, wash, rainbow, pulse and sparkle are approximated by existing ops
  (`osc`, `rotate`, `polar`, `lfo`, `particles`); the other six are not.
- `examples/tide.look.json` and `examples/mcp-ember.look.json` replace
  their `sparkle` pattern node with `particles`.
- The studio's trust model (ADR-024) becomes: public, unauthenticated,
  JSON looks over the built-in op catalog, checked by `lab.check.ready`
  and the codec's caps (16 layers, 32 nodes a layer); no file, path or code
  crosses the socket. The per-IP limits stand.
- The control page and the studio speak one wire vocabulary and show knobs
  through one panel, so a param kind, a refusal or a layer control changes
  in one place.
- A new effect needs an engine change and a release; an operator can no
  longer drop a file in and see it live. That is the price of one
  extension point.

## Evidence

- [S1400] Hydra: 53 functions in five type signatures, any of which
  composes with any other — variety from composing a fixed vocabulary,
  not from adding fixed effects.
- [S1406][S1408] AVS builds a preset from typed components, and webvs
  saves a preset as plain JSON — an effect as data over a known component
  set, which the studio can take from a public visitor.
- [S1414] Plugin discovery finds installed packages, not a file handed to
  a running program (ADR-022's rejection of entry points) — a loader for
  user op files would be a second mechanism beside the in-process
  registry.

Single-source caveat: the removals themselves are the maintainer's
product decision (2026-11-07), not a finding; the sources above support
the model kept, not the choice of which effects to drop.

## Rejected alternatives

- **Keep the gallery as the `pattern` op** (ADR-022, "The `pattern` op").
  It keeps two ways to write an effect (a class, a program) and two layer
  paths in the compositor (direct and hosted), and every surface carries
  both — the duplication this ADR removes.
- **Port the six patterns to ops.** Possible later, one op at a time, as
  any new op; the maintainer chose not to carry them now.
- **An `--ops-dir` that loads and hot-reloads user op files.** A second
  extension point beside `src/pewpew/fx/ops/`, with its own reload,
  trust and fingerprint rules (ADR-023's render fingerprint hashes pattern
  files today), for a use the maintainer does not need [S1414].
- **A layer `units` key** to keep per-fixture rendering inside programs
  (ADR-007's precedents [S1278][S305][S1262]). The maintainer never wants a
  bar lit as one lamp.
- **A studio session with its own look runtime.** It would repeat the
  deck, the controls and the wire states the aura already has, and drift
  from them.
- **Looks version 5 with a migration.** The file's shape does not change;
  only one op leaves the catalog, which the codec already refuses by name.
