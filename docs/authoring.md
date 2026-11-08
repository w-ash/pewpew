# Authoring looks

A look is the only effect (ADR-025). It is a stack of layers (§4), each an
effect program (§5): a small graph of ops from the catalog, whose args are
knobs (§2) and which signals can move. A look is data, JSON in a looks file
(version 4), so people, the control page, the studio and agents all write,
check and play it the same way.

```
$ uv run python -m pewpew run examples/tide.look.json --preview
$ uv run python -m pewpew run mine.look.json --map line:64 --preview
$ uv run python -m pewpew run looks.json --map examples/canopy-60-bars.arrangement.json
```

`run LOOKS` plays a looks file, a version-4 book of looks (a `.look.json`
file is one), starting in its `current` look. The control page's saves go
to that same file. With no `--map` the map is `grid:16x16`.
The other flags are in `run --help`.

You change a look with the control page, the `fx` verbs (§6) or an agent
(§7). A new kind of effect is a new op (§9).

## 1. Looks and ops

An op is a node of a program: a source (`osc`, `noise`), a coordinate
change (`kaleid`, `rotate`), a color (`palette`), a mix (`blend`), a state
(`feedback`, `particles`) or a signal (`lfo`, `band`). The catalog lists
them all, with each op's args, ranges and examples:

```
$ uv run python -m pewpew fx catalog --query kaleid
$ uv run python -m pewpew fx show kaleid
```

`docs/reference/catalog.md` is the same list as a page. Check the catalog
rather than recalling an op's args: they change as ops are added.

## 2. Knobs are op args

Every arg of an op is a typed param with a range, and a knob on the control
page. Its kinds:

| kind | declared as | JSON value |
|---|---|---|
| float | `Float(default, lo, hi, unit="")` | number |
| int | `Int(default, lo, hi, unit="")` | whole number |
| bool | `Bool(default)` | `true` / `false` |
| choice | `Choice(default, options)` | the option's key |
| color | `Color((h, s, v))` | `{"h", "s", "v"}` |
| palette | `Palette(gradient, presets=())` | a preset's name, or `{"stops": [{"at", "h", "s", "v"}, ...]}` |

`pewpew.params` declares them, and `fx catalog --kind kind` lists them.
`unit` is a short symbol (`"°"`, `"s"`, `"/s"`, `"Hz"`). `label` and `help`
are words for the page. `periodic=True` says `lo` and `hi` are the same
point (an angle). `options` is a list of keys or a mapping of key to
label; the value is the key, never an index. `sweet=(lo, hi)` is the
part of the range that looks good, which `fx vary` and a signal given as
an arg (§5) stay inside.

A color is hue, saturation and value over linear-light primaries: `h` is
degrees (0 to 360, periodic), `s` and `v` 0 to 1. A palette is a gradient
of 2 to 16 stops, each a position `at` from 0 to 1 and a color, in order,
the first at 0 and the last at 1 (two stops at one position make a hard
edge). `fx catalog --kind palette` lists the named presets. The gradient
is blended in OKLab, so a blend keeps its hue.

Ranges are enforced, on the command line, in a file and on the socket:

```
layers.base.k.sides must be within 1..24, got 40 [out-of-range]
  fix: set layers.base.k.sides within 1..24
```

An op that wants a wider range widens its declaration. The engine does not
clamp, because a clamp renders one value while every surface displays
another.

A knob that changes nothing fails the gate. `verify looks` renders each
knob of each node at two values and requires the frames to differ (§6), and
`tests/test_fx_ops.py` does the same for every arg of every op.

On the page there is one control per knob, built from the param's
describe record (`Param.spec()` in `src/pewpew/params/kinds.py`). The
controls drive the real engine, so a control shows what is being rendered;
a refused value is refused on the socket as on the command line, and every
open tab follows whichever one moved last.

## 3. Rooms and maps

`--map SPEC` is `line:64`, `grid:16x16`, `lattice:8` or an arrangement
`.json`. An arrangement is the one way to run a real rig
(`examples/canopy-60-bars.arrangement.json`): its fixtures give the mapping,
its controllers give the DDP boards (each with a `host`), and its floor plan
is drawn in the preview. `--dry-run` prints the plan, `--no-ddp --preview`
simulates without sending, and saving the file applies it live (a bad save
keeps the last good map and shows why). Every layer renders per pixel; the
fixtures give wiring, power limits and DDP (ADR-007). `--max-watts` works on
any arrangement. `--ddp` is refused with controllers that have hosts. A run
refuses to stream when the arrangement breaks a firmware pixel cap
(`output_over_cap`, `controller_over_cap`) or a wired controller has no host.

A room map file (the old format) passed to `--map` is migrated in memory with
a warning. `--room PATH` is the old name of `--map` and goes in the next
release, as does reading a room file. Migrate once:
`python -m pewpew rig migrate-room ROOM.json -o OUT.arrangement.json`.

A controller's `host` is an IPv4 address or the board's mDNS name,
such as `"host": "pewpew-1.local"`. Use the name on a network without DHCP
reservations: pewpew looks it up again when the board stops answering, so a
board that comes back on a new address keeps getting frames. While DDP is
on, the health button in the page's top bar opens one row per board with
what is wrong and what to do, and a banner names a board that has gone bad.
"Find boards" in that panel, or `uv run python -m pewpew boards scan` in a
terminal, lists the WLED boards on the network. "use for A" there rewrites controller
A's `host` in the arrangement file, also in an `--unattended` run, and the
new board set is audit-logged before any frame goes to it; it is refused on a
room file (migrate it first).

### Layout editing in the Console

On an arrangement run, `layout` in the Console's top bar (or `L`) opens the
layout panel in the side slot: the build-day tools (input-end markers,
blink), then the arrangement editor (name, undo and redo, export and import,
add a bar, ring or array, and the selected fixture's or group's pose, ends
and preset). `report` opens the power, wiring and controller report, with
the live draw and the power cap. With the panel open, the 3D view picks a
fixture or group on a press and moves or turns it with a gizmo.

Each edit runs live. Once edits settle (0.4 s), the page sends the whole
arrangement in one `arrange` request, one at a time, naming the digest of
the file it edited (`base`): the engine refuses it when the file has
changed since (a save by hand, "use for A", another tab), sending the
current layout with the refusal, and the page shows that layout. Otherwise
the engine compiles it once, refuses it with every issue when it does not
compile or its boards cannot take it (nothing is written), else writes the
file whole and atomically, audit-logged when DDP is on, and applies it as a
save of the file does. It answers once the new rig runs; when the rig does
not run (a program's setup raises on the new geometry), every part of the
run takes the old rig again, the edit is refused and the file holds its old
bytes again. Once the new rig runs the edit stands: a later part that fails
(the preview, the power cap) puts a warning on the status line. A refused
edit is not sent again by itself: `send again` sends it, and so do an undo
and a redo. The engine rewrites the file as indented JSON, so a hand-kept
layout of the file is lost on the first edit. Undo and redo are the page's
own; an arrangement that comes from elsewhere replaces the page's history,
and when the history held an edit the engine had not taken, the panel says
it was not applied. While the connection is down the editor is read-only;
on a reconnect to the same file the history stays and an edit not yet taken
goes again. With the panel open, the 3D view draws each fixture at the
pose the editor holds, so an edit, an undo or a redo shows before the
engine answers. Deleting a fixture or a group takes it out of its chain
(a chain left empty goes) and moves the chain's feeds to match. Delete and
Backspace delete the selection only after a press or focus in the layout
panel or the 3D view, never after one on a deck button or blank page. Edits
are off in an `--unattended` run and on a room map file, and stop when a
room map file is saved over the arrangement.

Coordinates are Contain-normalized: the rig's long axis spans 0–1 and the
short axis is centred inside it, so (0.5, 0.5) is the middle of the rig but
`y` may run only from, say, 0.12 to 0.88. Don't assume both axes reach 0 and 1.

An op declares the maps it takes. A look that uses a plane op is refused on
a strip with what to use instead (`kaleid` on a strip: use `mirror` on u),
and `verify looks --map` gates a looks file on the map it is for (§6).

A room event (today, a cue button on the control page) is a trigger in the
looks file's `triggers` section: it recalls a look for a `hold`, then the
run returns to where it was. The section is described in the docstring of
`src/pewpew/aura/book.py`. Events are stamped on engine time, so a recorded
run with the same events replays to the same frames.

## 4. Layers

A look is a stack of layers, the bottom one first. Each layer runs a
program (§5) and mixes onto the layers below it by its `opacity` (0 to 1),
its `blend` and its `enabled` switch. On the preview page, `+ layer` adds
an op's example from the catalog, screened over the layers already running.
With two layers or more, the page lists them top first: a row turns its
layer on or off, and the row picked opens to the layer's opacity, blend
(`?` says what it does), ▲ ▼ (or Alt+↑ ↓ on the row) and remove, while the
panel under the list shows that layer's knobs. These edit the running look,
which a save keeps. A looks file holds layers too, version 4, and an optional
`favorites` list of up to 20 looks for the page's row (absent: the first nine),
played with `run LOOKS --map SPEC`. Give a map the file's looks suit (`grid:16x16`, the
default, for a look that folds a plane). Sparks screened over a haze:

```json
{
  "version": 4,
  "current": "dusk",
  "looks": {
    "dusk": {"layers": [
      {"id": "base", "out": "tint", "nodes": {
        "haze": {"op": "noise", "args": {"scale": 2.0, "speed": 0.05}},
        "tint": {"op": "palette", "in": ["haze"], "args": {"palette": "ember"}}}},
      {"id": "sparks", "opacity": 0.6, "blend": "screen", "out": "glint", "nodes": {
        "motes": {"op": "particles", "args": {"rate": 80.0, "life": 0.6, "speed": 0.02, "emit": "anywhere", "size": 0.03}},
        "glint": {"op": "palette", "in": ["motes"], "args": {"palette": "ember"}}}}
    ]}
  }
}
```

A layer id and a node id are a lowercase letter and then up to 23
lowercase letters, digits or `_`. A node's `args` are its op's knobs
(§2), as JSON. Every key of a layer but `id` and `nodes` has a default
(opacity 1, blend normal, enabled), and a look holds at most 16 layers. The whole file, with the idle cycle and the triggers, is described
in the docstring of `src/pewpew/aura/book.py`.

Every knob has an address, which the page, a `set`, `observe` and every
refusal use:

    layers.<layer>.<node>.<arg>            an op's arg: layers.sparks.motes.life
    layers.<layer>.opacity|blend|enabled   a layer's mix

The blends work in linear light, and the stack is clamped to 0–1 once, on
top:

| `blend` | the layer onto the layers below |
|---|---|
| `normal` | over them, by opacity |
| `add` | its light added; runs to white |
| `screen` | added without washing out, on both inputs clipped to 0–1 |
| `multiply` | as a filter: darker only |
| `max`, `min` | the brighter or darker, per channel |
| `difference` | the difference, per channel |
| `subtract` | its light taken away |
| `stencil` | the layer where it has color, the layers below where it is black |
| `highlight` | lights only what the layers below already light |

Multiply, min, subtract and highlight over black stay black, so on the
bottom layer they black the room. Each layer draws its own random stream
from the look's `seed` and its own id, so adding a layer never changes
another layer's picture. Under `--unattended` a failing layer is left out of
the mix and the status line names it; when that leaves the room dark, the
room pulses red instead.

## 5. Effect programs

A layer runs an effect program: a small graph of ops, each one node
(ADR-022). In Python, write it as a chain with the builder in
`pewpew.fx.expr`, which encodes to the JSON a looks file holds:

```python
from pewpew.fx.expr import noise, osc

program = osc(8, 0.1).id("waves").kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember").id("tint")
```

A source (`osc`, `noise`, `voronoi`, `shape`, ...) is
a function; every other op is a method of what it reads. A coord op
(`kaleid`, `rotate`, `mirror`, `polar`, `tunnel`, ...) changes the
coordinates its input reads, so it wraps what comes before it:
`osc(8).rotate(30)` turns the stripes. `palette` colors a scalar field;
`add`, `mult`, `diff` and `blend` mix two inputs; `a.modulate(b, 0.2)` lets
`b` ripple `a`. `python -m pewpew fx catalog` lists every op and `fx show
kaleid` one op's args and examples; docs/reference/catalog.md is the same
list.

Each node's args are params with ranges, so a bad value fails where it is
written (`kaleid.sides must be within 1..24, got 40`), and each is a knob
with an address, `layers.<layer>.<node>.<arg>` (`layers.base.waves.freq`).
A node's id is the one `.id()` gives, or its op's name (`osc`, then
`osc2`); `blend` becomes `blend_`, since `layers.<layer>.blend` is the
layer's own blend mode, as the layer's other keys (`opacity`, `enabled`,
`out`, `alpha`, `nodes`) do. On a save, a knob you moved keeps your value; one you did not
takes the file's new literal. The program is checked against the map: an
op that needs a plane is refused on a strip with what to use instead
(`kaleid` on a strip: use `mirror` on u).

In a looks file a program is the layer's `nodes`, each with its `op`, the
nodes it reads (`in`) and its `args`; `out` names the node the layer
shows (default: the last) and `alpha` a scalar node that masks it:

```json
{"id": "base", "out": "tint", "nodes": {
  "waves": {"op": "osc", "args": {"freq": 8.0, "sync": 0.1}},
  "fold": {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
  "tint": {"op": "palette", "in": ["fold"], "args": {"palette": "ember"}}}}
```

A program that starts from `below()` is an effect on the layers below it,
and `prev()` reads the layer's own last frame, for trails.

### Ops that keep state

Some ops keep state from frame to frame (`fx catalog --kind state`, and
the sources that run a simulation):

- `feedback` is the MilkDrop loop: a field over the map, finer than the
  points, that each frame zooms, spins, swirls, drifts and wobbles, fades
  over `decay` seconds, and takes the brighter of itself and what it reads.
  It never adds, so a still input holds at its own brightness instead of
  climbing to white (§9.2). `trails` is the same per point, with no motion.
- `diffuse`, `ripple`, `reaction` and `life` run on the map's own points,
  each linked to its nearest neighbours, so heat, rings, Gray-Scott growth
  and a cyclic automaton follow the wiring and never jump a gap. Each takes
  as many small steps a frame as its speed needs, so no knob makes it blow
  up.
- `particles` (sparks, snow and fireflies are settings of it) and
  `attractor` (a Lorenz butterfly or a morphing Clifford cloud) draw many
  moving points as glow.

`feedback`, `particles` and `attractor` keep their state on a grid, so a
coord op may sit above them; the others keep one value per point, so it may
not. `feedback` reads what is under it at the map's own points, so it may
read state per point, or `below()`, and still sit under a coord op. State
lives in the node's buffers, so a save carries it on, and each node draws
from a random stream of its own, so a look renders the same frames every
time.

### Signals and routes

A knob can move by itself. A look's `signals` are signal ops, each one
number a frame: `lfo` and `walk` swing from -1 to 1; `env`, `band`,
`beat` and `knob` give a level from 0 to 1; `smooth` follows another
signal. A route adds `depth` times a signal to a knob, in the knob's own
units: a hue wraps round, anything else stops at its range. The knob's
own value stays what the page shows and a save stores; the page marks
where the route moves it now. Signals and routes belong to a look, so
the builder makes one with `look(...)`:

```python
import json
from pathlib import Path

from pewpew.fx.codec import encode_look
from pewpew.fx.expr import beat, knob, layer, lfo, look, noise
from pewpew.lab import render

made = look(
    layer("base", noise(3).palette("ember", shift=lfo(0.05))),
    routes=[
        (macro_ := knob(0.5).id("macro")).to("layers.base.noise.scale", depth=4),
        macro_.to("layers.base.opacity", depth=-0.3),
        beat().env(0.01, 0.3).to("layers.base.palette.cycle", depth=0.2),
    ],
    front=["signals.macro.value"],
)
print(render(made, "grid:16x16", seconds=2).metrics)  # render and measure it (§6)
saved = {"version": 4, "current": "mine", "looks": {"mine": encode_look(made)}}
Path("mine.look.json").write_text(json.dumps(saved))  # `run mine.look.json` plays it
```

Every op is a name in `pewpew.fx.expr`, imported by name (`from
pewpew.fx.expr import *` brings none, since they come from the catalog).

A signal given as an arg (`shift=lfo(0.05)`) sweeps the arg's sweet
range. A `knob` with several routes is a macro: turn
`signals.macro.value` and every knob it reaches moves. A route may also
drive another signal's knob (`signals.breath.rate`), but never in a
cycle. `front` lists the knobs a page shows first. In a looks file:

```json
"signals": {"macro": {"op": "knob", "args": {"value": 0.5}}},
"routes": [{"source": "macro", "path": "layers.base.noise.scale", "depth": 4}],
"front": ["signals.macro.value"]
```

A signal's knobs have addresses too, `signals.<signal>.<arg>`. A route
that names no knob, a knob that cannot move (a choice, a switch, a
palette, a whole color: route `.color.h` instead), or a depth past the
knob's span is refused with its place, such as `routes[0].path`, and so
is a `front` path that names no knob. When an edit takes a route's knob away,
or narrows it below the route's depth, the route
rests and a save leaves it out; a stale `front` path is left out the same
way, so the look still recalls. A signal that raises holds its last
value and the status line names it, `signals.<signal>`, while the aura
renders on. A fast route on brightness strobes: `verify looks` counts the
flashes, as for any look.

### Example looks

`examples/` holds thirteen looks, one per file: the ten below and three
small ones the MCP examples use (`mcp-ember`, `mcp-prism`, `mcp-tide`),
each passing `verify looks
examples/` (which renders a program on a 16x16 panel) and `verify looks
--map` on the maps it is for (`line:120` for a strip, `lattice:6` for a
volume). The gate does not probe what a map's shape cannot show, as each
op declares it (`planar`, `along`, and its axis and plane choices): on a
strip, `feedback`'s spin and swirl; a knob along an axis the map does not
spread along, such as `lissajous`'s `b` on a strip along x, or `mirror`'s
`centre` when it folds z on a panel; a choice of such an axis; and two
choices that read the map alike, such as `u` against the axis a strip runs
along.

- `copper-tide` (strip): copper and teal tides meet in the middle, their
  palettes cycling a golden ratio apart.
- `warp-lane` (strip): stars at the centre stream out to both ends through
  a zooming feedback field.
- `milk-bloom` (panel): a kaleidoscope of noise falls into a swirling
  feedback drain.
- `penrose-lagoon` (panel): seven-fold quasicrystal waves under a
  five-fold glint, palettes cycling a golden ratio apart.
- `turing-garden` (panel): Gray-Scott coral grows from seeds and keeps
  reseeding.
- `depth-charge` (volume): drops fall in a pond of points and rings spread
  through it.
- `lorenz-lantern` (volume): sixteen Lorenz moths trail light as the
  butterfly turns.
- `ember-fountain` (volume or room): embers rise from the floor on a
  curl-noise breeze, smoke trailing up.
- `tide` (panel or room): five-fold stripes rippled by noise, an echo
  layer that feeds back the frame below, and sparks on top.
- `firefly-ink` (any map): fireflies wander, and their glow bleeds along
  the points.

Each also has signals and routes (a slow `walk` or `lfo` on a hue, a warp
or a size; the beat or a sound band on what pulses) and a `front` list of
the knobs to turn first. In `milk-bloom`, `signals.trip.value` is a macro
over the feedback's zoom, decay and swirl.

## 6. Checking and rendering looks from the command line

A look can be checked, rendered, measured and compared without running
the aura. A file is a looks file (a `.look.json` file, version 4), as
`run` plays it, even for one look; a single look, bare, goes on
stdin (`-`) or to the lab's functions as JSON data. These verbs are
offline: they read files, write only the render cache and an `--out` PNG,
and send nothing to a board.

```sh
python -m pewpew fx check dusk.look.json            # its problems, or "ok"
python -m pewpew fx render dusk.look.json --map grid:16x16 --seconds 2 --out dusk.png
python -m pewpew fx metrics r1-3f0c2a9e41b77d5c08e6 --liveness   # a render, by its handle
python -m pewpew fx compare dusk.look.json dusk2.look.json --out ab.png
python -m pewpew fx explain dusk.look.json          # the look in words, knob by knob
python -m pewpew fx vary --seed 7 --n 4 --out new.png          # four looks made from nothing
python -m pewpew fx vary dusk.look.json --keep layers.base --out like.png   # four like dusk
python -m pewpew verify looks looks/                # the gate before an unattended run
```

- **`fx check`** lists every problem with a code (`unknown-key`,
  `out-of-range`, `bad-ref`, ...), the path of what it refuses, such as
  `layers.base.fold.sides`, the words the aura itself uses, and a
  did-you-mean: `layers.base.a: unknown op 'oscc' (did you mean 'osc'?)`.
  A problem names its node (`layers.base.fold`), with codes such as
  `unknown-op`, `cycle` and `bad-ref`. With `--json`, a look that checks comes back normalized,
  every knob of every node written out.
- **`fx render`** renders through the aura's own layer stack and master,
  so the frames are what `run LOOKS --seed SEED --map SPEC` shows when it
  starts in that look, `SPEC` the map `fx render` names. `--seed` is `run
  --seed`: it seeds the stand-in features and the looks made in the run, and the
  look's own `seed` seeds its layers. `--map` takes `line:64`, `grid:16x16`,
  `lattice:8` or an arrangement `.json` (default `grid:16x16`, the map `run` uses
  without `--map`). A program the map does not support is
  refused before it renders (`wrong-dims`: `kaleid` on a strip).
- A render prints a **handle**, `r1-` and 20 hex digits, that `fx sheet`,
  `fx metrics` and `fx compare` take in place of a file. The same look,
  map, seconds, fps, seed and engine code always give the same handle.
  The frames are kept under `$PEWPEW_CACHE` (default
  `~/.cache/pewpew/renders`), which drops the least recently used past a
  size cap; a handle it dropped exits 3 with how to get it back: render
  the same spec again.
- **`fx compare A B`** renders a look B as A was rendered: the same map
  spec, seconds, fps and seed; a look A renders as B was when B alone is
  a handle.
- **`verify looks`** (its `--map` defaults to `grid:16x16`, as do `fx
  render`, `compare`, `vary` and the MCP tools) passes a look that checks, has no layer that raises,
  flashes at most 3 times a second (WCAG 2.3.1), is not black in every
  frame, and whose every knob, each node's of a program, changes the
  picture (the method of `tests/test_param_liveness.py`), each probe
  rendered for 1 s at 30 fps and compared over its last 0.5 s, so what
  builds up (a trail, a feedback field, a simulation) has filled. A knob it
  cannot probe fails too: a palette with no preset to move to, or a knob
  at one end of its range that stops the look from running. A probe the
  map's shape cannot show is not run (pewpew.lab.liveness). A render under one second fails,
  since it is too short to count flashes per second. It renders fresh,
  never from the cache. A folder stands for its `*.look.json` files; a folder with none,
  or a file with no look, fails.

- **`fx vary`** makes looks (pewpew.fx.surprise): from nothing, or like
  FILE, moved by `--strength` (above 0, at most 1; default 0.3), holding
  each `--keep` address and all under it (a knob, a node
  `layers.base.osc`, a layer or a signal; holding one of the last three
  holds the look's seed too, as its noise comes from it). A made look is a grammar over the catalog: a
  source, warps, a palette that starts dark, maybe one or two more layers
  and a slow route or two, each knob inside its param's `sweet` range and
  each speed near its default. Each is judged on the map before it is
  given: it passes `verify looks` (with room to spare on each knob's
  probe). Taste is a preference: a made look is not too dark, washed
  out, dying out, frozen, noise or grey when one of its tries manages
  that, else it fails the fewest of those, and `--json` lists each
  candidate's failures as `taste`. A seed whose changes of FILE all fail
  the gate gives no candidate. `--seed` is the seed the looks are made from, not the features'
  seed; the same arguments give the same looks. Each candidate prints its
  render handle; `--out` draws them in one sheet, rows numbered 1 to n.
  `--json` gives each candidate's look too (`.candidates[i].look`): save
  one to a file to check, explain or edit it, since those verbs take a
  file, not a handle.
  Making a look renders it a few times over, about a second each.

FILE may be `-` for stdin, and `--look NAME` picks one look of a file
that holds several. With `--json`, a verb prints exactly one JSON
document on stdout and its diagnostics on stderr. Exit codes: 0 ok, 1 a
look with problems or a failed gate, 2 a usage error, 3 an expired handle.

The verbs are thin over `pewpew.lab`, the same functions in Python:

```python
from pathlib import Path

from pewpew.lab import check_look, render, sheet

assert check_look(Path("dusk.look.json")).ok
rendered = render(Path("dusk.look.json"), "grid:16x16", seconds=2)
print(rendered.metrics.flash_rate_max, sheet(rendered).path)
```

A running aura makes looks too. A client sends `surprise` (a look made
from a seed for the aura's own map) or `vary` (one like the look that
runs, at a strength); either fades in over the made look's own fade and
plays unsaved. A `save` with a null name saves the running
look under the name the made look offers, `surprise 3` or `variation 2`,
counted in the run (`kept` for a look not made; the look holds its seed),
counting on past a name that is taken, with the made look's fade; the aura
state's `looks.offered` says that name first. A save under another name and
a delete rename it. `keep` is that save under its old name, for clients that
send it; the control page sends `save`. On the control page (with a looks
file) these are `surprise me` and `vary this`, on their own row under the
saved looks, and the one `save` in the look's header, or the keys `s`, `m`
and `k` (over unsaved edits, `surprise me` and `vary this` take two
presses); the header names the made look with a draft badge, its `▾` opens
`save as new…` to give it another name, and a press on one that is off says
why. The same `⋯` holds `rename…`, which gives the look a new name in place
(its place, fade and shuffle flag kept; a taken name is refused) and a
`favorite` switch, which puts it in the row (at most 20; the row sorts them,
and keys 1–9 press the first nine). The `all N ›` list is alphabetical, marks
the favorites, and filters as you type: ↑ and ↓ move, Enter plays, Esc clears
and then closes.

The page calls a look's signals **modulators**, each by its kind: LFO,
random (`walk`), beat, envelope (`env`), audio follower (`band`), macro
(`knob`) and smooth. A knob a route moves reads `modulated by ‘breath’
±0.2 Hz`: ± for a modulator that swings both ways (`lfo`, `walk`, a
`smooth` of either), and the route's own sign, + or −, for one that gives a
level. The master is the page's **brightness**, its cap its **max**; the
idle cycle is **shuffle**; arming the triggers turns **cues on**; a node is
a **step**; and a look's `front` knobs are its **main knobs**.

The idle cycle is a seeded director (pewpew.aura.director): after `idle`
seconds with no operator input and no unsaved edits, it plays the looks whose `cycle` flag is
on in a random order, each as likely as its weight, none of the last
`window` again, each for a dwell drawn from `each` (`[40, 90]` for 40 to
90 seconds), and every `fresh`th slot a look made fresh, during the slot
before it. Each slot starts at its own time, and the aura never waits
for a make: a make takes a second or so, and a fresh slot whose look is
not made yet plays a look of the cycle instead, says so in the log, and
the next fresh slot plays the fresh look, so keep `each` above a few
seconds. Its `seed` makes the order and each slot's start the same on
every run of the same file; in a live run, only whether each make is
done by its slot's start, and which frames a loop that falls behind
skips, are up to the wall clock:

```json
"cycle": {"idle": 300, "each": [40, 90], "rounds": 0, "end": null,
          "seed": 0, "window": 2, "fresh": 5, "weights": {"dusk": 2}}
```

## 7. Agents: the MCP server

`python -m pewpew mcp` serves the same verbs to an AI agent over MCP, on
stdio. It needs the `agent` extra (`uv sync --extra agent`; the dev group
has it), and `.mcp.json` registers it for Claude Code as `pewpew`. Its
tools answer with the JSON the matching verb prints with `--json`:

| Tool | Verb | |
|---|---|---|
| `catalog_search` | `fx catalog` | a page of the catalog; concise, or detailed with each whole record |
| `look_check` | `fx check`, `fx explain` | a look's problems, each with a fix, or the look normalized |
| `look_render` | `fx render` | a handle, the metrics, warnings and a contact sheet image |
| `look_compare` | `fx compare` | how render B differs from A, and an A/B sheet |
| `look_vary` | `fx vary` | up to 8 looks made from a seed or like a look, each rendered, and a numbered sheet |
| `engine_observe` | `observe` | a running engine's state and approximate metrics, and a sheet |
| `fleet_status` | `boards scan --json` | each WLED board on the network, with its health |
| `engine_apply`, `engine_set` | `push`, `push --set` | tier 1 only (`mcp --tier 1`, `pewpew-live`): a dry run unless `dry_run` is false |
| `engine_rename` | `rename` (control verb; no CLI verb) | tier 1 only, as above, and the engine runs with `--accept-looks`; refuses a taken or bad name, an unknown look, or a look a trigger names |

A look is JSON over the built-in ops, so no tool runs a file or code. A refused look
comes back as an error that lists each problem's code, path and fix. The
server also serves the catalog (`pewpew://catalog`), the example looks
(`pewpew://looks/{name}`), this guide and the catalog reference
(`pewpew://docs/{topic}`) and render sheets
(`pewpew://render/{handle}/sheet.png`), and two prompts, `design-look`
and `critique-pair`. The `authoring-looks` skill in `.claude/skills/`
teaches the loop, and the `look-critic` subagent judges two renders.

## 8. Real sound

By default the audio fields come from a seeded stand-in: 16 bands of
slow sine waves and a beat at 120 BPM. `run --audio FILE.wav` analyses a
WAV file instead, frame by frame as live input will be analysed, and plays
it on a loop. pewpew only listens: nothing plays the file aloud.

```
uv run python -m pewpew run examples/warp-lane.look.json --map line:120 --audio song.wav
uv run python -m pewpew audio analyse song.wav
```

With real sound the fields mean:

- `bands`: 16 bands on the mel scale from 40 Hz to 16 kHz, each 0 to 1.
  1 is the loudest the gain rider has heard lately, and 0 is 36 dB below
  it or a gate that is shut on silence.
- `volume`, `bass`, `mid` and `high`: on the same scale. Bass is below
  250 Hz and high is above 3 kHz.
- `beat_phase`: rises from 0 to 1 over each beat and wraps on the beat.
  The beat tracker steers an oscillator rather than setting the phase, so
  the phase never steps back and each wrap is one beat, even while the
  tracker searches.

A look reads these fields through signals (§5): `band` follows the volume,
bass, mid or high level (shaped by `attack` and `release`), and `beat`
follows the beat. `examples/warp-lane.look.json` routes
the mid band and the beat to its knobs. A look reads the same signals with
real or simulated sound, so nothing in it changes.

`audio analyse` prints the tempo, its confidence, the beat times and the
levels of a file; `--json` prints them for an agent. `--feature-log PATH`
(on `run` or `audio analyse`) writes each frame's features, and
`--audio replay:PATH` plays them back byte for byte, at any `--fps`. A
feature log from a microphone is close to a speech recording, so never
keep one with people in the room. `--audio-delay MS` is for speakers the room hears late,
such as Bluetooth ones: it delays the levels and moves the beat.

Live sound comes from one of the computer's inputs, an audio interface's
line-in or a microphone, named as `audio list` prints it:
`run examples/warp-lane.look.json --map line:120 --audio "Scarlett 2i2 USB"`. It needs the `audio` extra, and
`--audio-channel N` reads one channel. `docs/audio.md` covers choosing
the input, what happens when it is unplugged, its health row and privacy.
Capture nodes come later (`research/topics/RA-28-audio-input.md`).

## 9. Writing a new op

A new effect is a new op (ADR-025). It is the only extension point:
`run` loads no Python file, and a look can name only ops in the catalog.
An op is a subclass of `Op` in a module of `src/pewpew/fx/ops/`, which
registers it by name when the module is imported (add the module to
`src/pewpew/fx/ops/__init__.py`).

Read ADR-022 (`research/synthesis/decisions/ADR-022-effect-programs.md`) and the
docstring of `src/pewpew/fx/op.py`, then take an existing op as the model:
`Osc` in `src/pewpew/fx/ops/source.py` for a source with no state,
`Particles` in `src/pewpew/fx/ops/swarm.py` for one with state. An op
declares:

- `sig` and `out`: what it is (source, coord, color, combine, modulate,
  state or signal) and what it gives (signal, scalar, rgb, or `SAME`, the
  type it reads).
- Its args as params (§2), each with a `help`; `Rate` for a speed, whose
  phase the op keeps; `dims`, `planar` and `along` for the maps it takes.
- `examples`: builder chains that the catalog shows and the tests render.
- `build(inputs)`, which returns the closure that gives the node's field
  from the points it is asked about. The closure reads its args when it
  runs, so a live change shows on the next frame.
- For state, `setup(ctx)` (the points, the node's seeds, its buffers) and
  `advance(ctx, inputs)` once per frame before any render.

An op is done when:

1. Its tests pass. `tests/test_fx_ops.py` renders every example on each map
   the op takes and requires every arg to change the picture; add a test for
   what is particular to the op.
2. The catalog is regenerated: `uv run pytest --regen-goldens` rewrites the
   catalog golden, `docs/reference/catalog.md` and `src/pewpew/fx/expr.pyi`.
   Review the diff.
3. An example look under `examples/` uses it, if it earns one, and passes
   `verify looks examples/` (§6).
4. `just check` is green.

The rest of this section is the NumPy discipline for an op that is not a
formula of the point's coordinates.

### 9.1 Structured effects need a field, not the pixel list

A closure gets the map's points as a flat, unordered list. There is no
notion of "the point to my left", so a stencil (heat diffusion, ripples, a
cellular automaton) cannot be written over it. Keep the state in a field
and read the field per point. `src/pewpew/fx/ops/sims.py` links each point
to its nearest neighbours, so a simulation follows the wiring;
`swarm.py` and `state.py` keep a grid (`Lattice.over(ctx, ...)`) that the
closure samples at the points. Advance the field in `advance` with
ordinary array math (`np.roll` for neighbours), and sample it in the
closure. An update that writes `field[1:]` from `field[:-1]` reads
pre-frame values throughout: that is a simultaneous update, not the
sequential one of a hand-ported C loop, which needs a Python loop over
rows.

### 9.2 Per-pixel state is not the output buffer

A spark added to last frame's output and read back next frame is a
feedback loop with a fixed point. With `keep = fade(dt, tail)` and `+0.3`
added whenever a pixel triggers, the value converges to
`min(1, keep * v + 0.3)`, whose fixed point is 1.0: a pixel that triggers
more than once climbs `0.30 → 0.58 → 0.84 → 1.0` and stays white.

Don't launder state through the output. Declare a buffer in `setup` with
`ctx.buffer(name, shape, dtype, fill)` and decay it directly with `fade`
in `advance`. A buffer is read-only while the program renders, so a stray
write in the closure raises `ValueError` instead of corrupting state, and a
save of the look carries it on. Where a feedback must take in new light
(`feedback` in `state.py`), take the brighter of the state and the input
rather than adding, so a still input holds at its own brightness.

### 9.3 `np.where` runs both branches, always

`np.where(cond, a, b)` computes `a` and `b` for every element and then
picks. That is harmless for `exp`, but a guarded `sqrt`, `log` or division
raises a `RuntimeWarning`, or poisons the result:

```python
x = np.array([-1.0, 0.0, 4.0], dtype="float32")
bad = np.where(x >= 0, np.sqrt(x), 0.0)
# RuntimeWarning: invalid value encountered in sqrt; bad == [0.0, 0.0, 2.0]
```

The warning is the smoke alarm. The fire is code that blends instead of
selects, `mask * a + (1 - mask) * b`, because `nan * 0` is `nan`:

```python
mask = (x >= 0).astype("float32")
combined = mask * np.sqrt(x) + (1 - mask) * 0.0   # [nan, 0.0, 2.0]
```

Make the guard input safe before the math: `np.sqrt(np.maximum(x, 0.0))`;
clamp `log` away from zero, and add an epsilon to a denominator.

### 9.4 Random draws belong in `advance`

Draw from `ctx.rng()` in `advance`, never from an RNG of your own, the wall
clock or the closure: it is a stream keyed by the node and the frame, so
the same look renders the same frames every time (`CLAUDE.md`: no unseeded
RNG; same inputs, byte-identical output). A frame has a stream of its own,
so a skipped draw does not shift later frames. Within a frame the draws are
in order, so keep their shape fixed: draw `W` values and mask them, instead
of drawing only when a condition holds.

### 9.5 Decay is `fade(dt, tau)`, not a per-frame multiplier

`v *= 0.94` assumes a fixed frame rate; at another rate the same constant
decays over a different time. `from pewpew.fx.prims.vec import fade`, then
`v *= fade(ctx.dt, tau)` with `tau` a time constant in seconds. `fade` is
`exp(-dt / tau)` as a Python float, computed once per frame.

### 9.6 Coordinates are float32

Binning: `int(x * n)` puts `x == 1.0`, the map's last point, in bin `n`,
one past the end. Use `pewpew.color.bins(x, n)`, which clamps to `[0, n-1]`,
and clamp a float before an `int32` cast by hand, as `bins` does.

Hash thresholds: a hash in `float32` disagrees with the same expression in
`float64` right at a threshold, and flips a few pixels. Cast to `float64`
before the comparison, not after.

An op with `warpable = True` (the default) gives a correct field at any
finite point, including points far outside 0–1 that change every frame,
because a coord op above it moves them. So don't compute from the
coordinates in `setup` (a distance or hue made there shows the unwarped
geometry), and key per-point randomness on identity rather than on the
closure's coordinates. Set `warpable = False` for an op that reads per-point
state (`below`, `prev`).

## Reference

| Helper | Signature | What it's for |
|---|---|---|
| `fade(dt, tau)` | `pewpew.fx.prims.vec.fade(dt, tau) -> float` | frame-rate-independent decay keep-factor (§9.5) |
| `bins(x, n)` | `pewpew.color.bins(x, n) -> int array` | coordinate → bin index, edge-clamped (§9.6) |
| `wave(p)` | `pewpew.fx.prims.vec.wave(p) -> array` | 0–1 phase → 0–1 sine |
| `ctx.buffer(name, shape, dtype, fill)` | `BindCtx.buffer`, in `setup` | declare an op's persistent state (§9.2) |
| `ctx.rng()` | `FrameCtx.rng`, in `advance` | this node's random stream for this frame (§9.4) |
| `Float`, `Int`, `Bool`, `Choice`, `Color`, `Palette` | `pewpew.params`; `Float(default, lo, hi, unit)` | declare an arg; ranges and kinds are enforced (§2) |
| `uv run python -m pewpew run LOOKS` | looks file; `--map SPEC`, default `grid:16x16` | play a looks file live, starting in its `current` look; saves go to the same file (intro, §4) |
| `run LOOKS --map RIG.arrangement.json` | arrangement JSON; `--no-ddp`, `--dry-run` | run on a rig's fixtures and controllers; the map reloads on save (§3) |
| `run LOOKS --audio NAME` | an input's name, `FILE.wav` or `replay:PATH`; `--audio-channel N`, `--audio-delay MS`, `--feature-log PATH` | real sound in the audio signals: a line-in or a microphone (needs pewpew[audio]), a WAV file analysed on a loop, or a feature log played back (§8, docs/audio.md) |
| `uv run python -m pewpew audio analyse FILE` | a WAV file; `--json`, `--fps`, `--feature-log PATH` | the tempo, confidence, beat times and levels pewpew hears in a file (§8) |
| `uv run python -m pewpew audio list` | `--json` | this computer's inputs by the exact names `run --audio` takes; opens none (§8) |
| `uv run python -m pewpew fx catalog` | `--kind K`, `--query Q`, `--json`, `--format markdown`; `fx show OP` | every op, blend, palette and param kind, with examples (§1, §5) |
| `uv run python -m pewpew fx check`, `render`, `compare`, `vary`, `explain` | a looks file; `--map SPEC`, `--json` | check, render, compare and make looks offline (§6) |
| `uv run python -m pewpew boards scan` | `--subnet CIDR` (default: this laptop's /24), `--json` | list the WLED boards on the network, with address, name, MAC and live state, and with `--json` each one's health (§3) |
| `uv run python -m pewpew observe URL` | the `preview at` address; `--seconds S`, `--sheet PATH`, `--json` | watch a running engine without changing it: its aura state and approximate metrics of the frames it streams, and a contact sheet |
| `uv run python -m pewpew push URL LOOK` | `--fade S`, `--set PATH=VALUE`, `--dry-run`, `--json`, `--allow-host IP` | send a whole look, then knob values, to an engine on this machine run with `--preview --accept-looks`; tier 1: check with `--dry-run` first; each send is audit-logged |
| `uv run --extra agent python -m pewpew mcp` | `--tier 0` (default) or `1`, `--allow-host IP` | serve the tools above to an AI agent over MCP on stdio (§7) |

Every example above runs against the real engine (`src/pewpew/`): verify a
new API against the source before trusting a docstring, this one included.
