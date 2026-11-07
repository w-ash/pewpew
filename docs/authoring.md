# Authoring patterns

A pattern is a class with up to three hooks:

```python
def setup(self, n, x, y, z, index):     # once, when the pattern binds to a mapping
def before_render(self, dt, features):  # once per frame — the only place state changes
def render(self, x, y, z, index):       # pure — called every frame, returns the frame
```

`render` runs once per *frame*, not once per pixel: `x`, `y`, `z` and `index`
are NumPy arrays with one element per pixel of the mapping, so code that reads
like scalar Python (`x + self.phase`) mostly works because NumPy broadcasts.
`render` must be pure (no writes, no RNG, no wall clock), which is what makes
golden frames and deterministic scrubbing possible (architecture §8). Where
scalar thinking breaks, with the failure you would see and the fix, is §7,
from a study that wrote five patterns against this contract
(`bench/results/authoring-2026-07-16.md`).

## 1. Running your own pattern

The runner takes a file as readily as a gallery name:

```
$ uv run python -m pewpew run effects/mine.py --map line:64 --preview
$ uv run python -m pewpew run effects/mine.py:Spark         # the file defines several
$ uv run python -m pewpew run mine --pattern-dir effects/   # effects/mine.py, then the gallery
$ uv run python -m pewpew run comet                         # always the gallery, never ./comet.py
```

A file must define exactly one `Pattern` subclass of its own, or name the one
you mean with `:ClassName`. A base class imported from a sibling module does
not count, and sibling imports work as they would for a script: the file's
directory is put on `sys.path`. A bare name is the gallery unless `--pattern-dir`
names a directory holding `<name>.py`; the working directory is never searched,
so a stray `comet.py` next to your shell cannot shadow the built-in.

The page's pattern picker lists the gallery by class name, lowercased
(`class Spark` is `spark`), and each `--pattern-dir` file by its file name
(`mine.py` is `mine`), leaving out a name that is not a Python identifier
or starts with `_`. A pattern goes by that one name in the picker and the
status line. Its params go by their address: the command line's pattern
runs on layer `base` in a node of its name, so plasma's `speed` is
`layers.base.plasma.speed` on the page, in every refusal and in `observe`
(§9). A pattern launched by path goes by its class name, lowercased, and is
not on the list; a look saved from it keeps the path, so recalling the look
runs that file again.

Loading a file runs it. That is what a local dev tool does; it is also why
nothing on the preview socket can ask the engine to load one.

## 2. Params are a contract, not a suggestion

A param is a typed class attribute. Declare one in a line, anywhere in the
class body:

```python
from pewpew import Bool, Choice, Color, Float, Int, Pattern

class Bands(Pattern):
    speed = Float(0.25, 0.0, 1.0, "/s", help="Crests passing a point per second")
    direction = Float(0.0, 0.0, 360.0, "°", periodic=True, widget="angle")
    count = Int(4, 1, 12)
    mirror = Bool(False)
    shape = Choice("sine", {"sine": "Sine", "saw": "Saw"})
    color = Color((200.0, 1.0, 1.0))
    cycle = Float(0.0, 0.0, 60.0, "s", text={0: "hold"}, group="Color")
```

| kind | declaration | `self.x` reads | JSON value |
|---|---|---|---|
| float | `Float(default, lo, hi, unit="")` | `float` | number |
| int | `Int(default, lo, hi, unit="")` | `int` | whole number |
| bool | `Bool(default)` | `bool` | `true` / `false` |
| choice | `Choice(default, options)` | the option's key | the key |
| color | `Color((h, s, v))` | `HSV` | `{"h", "s", "v"}` |
| palette | `Palette(gradient, presets=())` | `Gradient` | `{"label", "stops": [{"at", "h", "s", "v"}, ...]}` |

`unit` is a short symbol: `"°"`, `"s"`, `"/s"`, `"Hz"`. Words go in
`label` (default: the attribute name, capitalized) and `help`. `group`
puts params under one heading on the page; it is layout only, and the id of
a param is always its attribute name. `periodic=True` says `lo` and `hi`
are the same point (an angle). `text` names special values, for example
`{0: "hold"}`. `widget="angle"` asks for a dial and needs the range 0 to
360 and `periodic=True`; it is a `Float`'s only widget, and a kind refuses
any widget it does not offer. `options` is a list of keys or a mapping of
key to label; the value is the key, never an index.

A color is hue, saturation and value over linear-light primaries: `h` is
degrees (0 to 360, periodic), `s` and `v` 0 to 1. `self.color.rgb(level)`
is the colour as linear RGB with its value scaled by `level` per pixel, so
an (N,) `level` gives the (N,3) frame. A scalar `level` gives one (3,)
colour, which `render` must broadcast to (N,3) itself (`np.full`):

```python
    def render(self, x, y, z, index):
        return self.color.rgb(wave(x - self.phase))
```

`hsv` takes the hue as a 0-1 turn, which is `self.color.turn`, for a hue
that moves: `hsv(self.color.turn + self.spread * x, self.color.s, self.color.v)`.

A palette is a gradient: 2 to 16 stops, each a position `at` from 0 to 1
and a color like a color param's, in order, the first at 0 and the last at
1 (two stops at one position make a hard edge). `pewpew.color` has the
named presets (`EMBER`, `OCEAN`, `AURORA`, `SYNTHWAVE`, `FOREST`, `ICE`,
`CANDY`, `MONO`, all in `PRESETS`) that the page's picker offers when you
pass them. `self.palette.rgb(t)` reads the palette per pixel at a
position from 0 (the first stop) to 1 (the last), clamped past either end,
as `self.color.rgb(level)` reads a color. Pass `t % 1` for a gradient that
repeats. It reads a 256-entry table of linear RGB, blended in OKLab so a
blend keeps its hue and cached by value, so it costs one lookup per pixel;
`pewpew.color.gradient_lut` builds that table and `pewpew.color.sample`
reads one:

```python
from pewpew import Palette, Pattern
from pewpew.color import EMBER, PRESETS

class Glow(Pattern):
    palette = Palette(EMBER, presets=PRESETS)

    def render(self, x, y, z, index):
        return self.palette.rgb(x)
```

At bind the engine writes plain values onto the instance, so `self.speed`
reads as a number with no indirection on the frame path. The declaration
itself survives, which is what lets the runner, the preview page, and the
liveness check all ask a pattern what params it has.

**Ranges are enforced.** A value outside `lo`..`hi`, or of the wrong kind,
is refused, on the command line and everywhere else:

```
$ uv run python -m pewpew run plasma --param speed=5
layers.base.plasma.speed must be within 0.0..2.0, got 5.0; edit the 'speed' param in /path/to/src/pewpew/patterns/plasma.py, or pick a value it accepts
```

`--param` takes a param's name or its address (`speed` or
`layers.base.plasma.speed`), and reads its value as JSON when it can and
as text otherwise: `--param mirror=true`, `--param shape=saw`,
`--param 'color={"h": 30, "s": 1, "v": 1}'`, `--param palette=ocean` (a
preset's label). A color's part is refused by its path:
`layers.base.bands.color.s must be within 0.0..1.0, got 2.0`, and a
palette's stop by its index:
`layers.base.glow.palette.stops[1].h must be within 0.0..360.0, got 400.0`.

Widening the declaration is the intended way to go further, and it is a
better answer than it looks: the range is what a control's endpoints are
built from, so widening it moves the control too. The engine does not
clamp, because a clamp renders one value while every surface displays
another — which is the dead-param problem this contract exists to prevent.

**The declaration wins over `__init__`.** Assigning `self.speed` in
`__init__` does not change the param's starting value — the engine
overwrites it at bind. Set the value you want as the default.

**A param that changes nothing fails the build.**
`tests/test_param_liveness.py` renders every declared param at two values
(`lo` and `hi`; `lo` and the midpoint when periodic; false and true; each
option against the first; each part of a color; each preset of a palette
against its default) and requires the rendered sequence to
change. It exists because `sdf3d`'s `spin` was a mathematical no-op that
shipped: the pattern animated convincingly from other motion, and neither
review nor golden frames noticed. If your param fails it, either nothing
reads it in a way that reaches a pixel, or the range is too narrow to
matter — both are worth knowing.

**Your params become controls.** `uv run python -m pewpew run <pattern> --preview`
serves one control per declared param, built from its describe record
(`Param.spec()` in `src/pewpew/params/kinds.py`; `tests/goldens/describe.json`
holds every gallery pattern's).
They drive the real engine, so what a control shows is what is being
rendered; a refused value is refused on the socket the same way it is on
the command line, and every open tab follows whichever one moved last.

A live set goes through the renderer's params, `renderer.params.set(name,
value)`, which writes the pattern's attribute too, so the set and the
pattern never disagree. It belongs to the loop thread and raises
`ValueError` for a refused value; the runner checks a value on the
caller's thread and queues the set (`pewpew.aura.control`). One limit to
keep in mind: a value set while the aura runs only reaches a pattern that
reads it every frame. Precompute a
table from `self.count` in `setup` and a live change will not be seen
until the next bind — which `test_param_liveness.py` also checks, by
setting each param mid-sequence and requiring the frames after it to
diverge.

## 3. Save the file; the aura keeps running

While `run` is up, the pattern's source file is watched (`--no-reload` turns
that off; gallery files are watched too, so editing
`src/pewpew/patterns/comet.py` reloads it). A save re-executes the file and
swaps the new class in between two frames. The aura does not restart:

- **Engine time** continues. `time()` and every `dt` are what they would have
  been without the save.
- **Parameter values** are kept when they still fit the new declaration. A
  value outside a narrowed range resets to the *new default*, never a clamp
  (ADR-006), and so does a value whose param changed kind. A param you
  removed disappears from the page; one you added appears at its default.
  The preview page rebuilds its controls on the spot.
- **Buffers** — `self.pixels` and everything from `self.buffer` (§7.1) — are handed
  to the new instance when the name, shape and dtype still match. Each one
  is taken over at the moment `setup` declares it, so a view or derived
  array `setup` builds from it refers to the kept data. A buffer whose shape
  or dtype changed starts from its fill value; nothing is resampled.
- **The RNG stream** continues from where it was.
- **Plain scalar state** set in `__init__` (`self.head`, `self.phase`, a
  counter, a flag, a string) is kept when the new instance has an attribute
  of the same name and the same family after its own `__init__` ran. Numbers
  are one family, so `self.phase = 0` that has become `12.7` is kept. Lists,
  tuples and arrays you manage yourself start fresh; per-pixel state that
  must survive a save belongs in `self.buffer`.
- **`setup` runs again**, against the kept buffers, after the scalars above
  are in place. Whatever `setup` assigns is the new code's own, so editing a
  constant set there takes effect on save.

Two consequences worth knowing. A param default or an `__init__` constant
you edit is not what a *kept* value reads — the live value wins, so press
**reset** on the preview (params) or rename the attribute (scalars) to see
the new number. And a value kept from the old code is only as meaningful as
the new code's use of it: rename an attribute when its meaning changes, and
it starts fresh by construction.

A save that does not load — a syntax error, an import that fails, a `setup`
that raises, a second `Pattern` class with no `:ClassName` to choose it —
keeps the last-good pattern running and shows why on the status line under
the terminal grid and on the preview page's status bar, under the room (with
the line number and never the path). Fix the file and save again; the error
clears. The `run` log has the full traceback once the terminal is handed
back. Only the entry file is watched: an edit to a sibling module it
imports, or to the engine, needs a restart.

## 4. Rooms, and lighting a whole fixture as one unit

`--room PATH` runs a pattern on a room map file: straight fixtures in meters,
each with its board, output and chain position (`examples/room-60-bars.json`;
the format is in `src/pewpew/room/map.py`). The room gives the mapping and
the DDP boards; `--dry-run` prints the plan, `--no-ddp --preview` simulates without
sending, and saving the file applies it live as saving a pattern does (a bad
save keeps the last good map and shows why).

A board in the room's `boards` is an IPv4 address or the board's mDNS name,
such as `"A": "pewpew-1.local"`. Use the name on a network without DHCP
reservations: pewpew looks it up again when the board stops answering, so a
board that comes back on a new address keeps getting frames. While DDP is
on, the health button in the page's top bar opens one row per board with
what is wrong and what to do, and a banner names a board that has gone bad.
"Find boards" in that panel, or `uv run python -m pewpew boards scan` in a
terminal, lists the WLED boards on the network.

Coordinates are Contain-normalized: the room's long axis spans 0–1 and the
short axis is centred inside it, so (0.5, 0.5) is the middle of the room but
`y` may run only from, say, 0.12 to 0.88. Don't assume both axes reach 0 and 1.

To give each bar one colour, say so on the class:

```python
class Pulse(Pattern):
    units = "fixture"   # one colour per fixture; the default is "pixel"

    def render(self, x, y, z, index):
        return hsv(index / self.n, 1.0, wave(time(0.05)))
```

`render` is unchanged: it runs once per *fixture*, `x`, `y`, `z` are each
fixture's centre, `index` is its position in wire order, and `self.n` is the
number of fixtures. The engine copies each fixture's colour to all its pixels,
and the preview still draws every pixel where it really is. Buffers, including
`self.pixels`, are per fixture too. `run --units fixture` (or `pixel`) overrides
the class for a run, so any pattern can be tried per bar. A mapping without
fixtures (`--map line:64`) renders per pixel whatever `units` says.

## 5. Reacting to room events

A room event (today, a cue button on the control page; the trigger names
live in the looks file's `triggers` section) reaches the running pattern as
data: `features` is a `FeatureFrame`, and `features.events` is a tuple of
the `Event`s accepted at this frame's tick, empty on every other frame.
Each event has `name`, `source`, `value` (None for a button press, a number
for a sensor level), `priority`, and the engine `t` and `tick` it fired on.
Read it in `before_render` and change your own state there; `render` never
sees it.

```python
def before_render(self, dt, features):
    self.flash *= fade(dt, 0.3)
    if any(e.name == "cue1" for e in features.events):
        self.flash = 1.0
```

You see each event once, on one frame, so react to it then rather than
waiting for it. Events are stamped on engine time, so a recorded run with
the same events replays to the same frames.

## 6. Rendering a pattern in a test

`render_sequence` is the pure form: the same arguments give the same frames,
byte for byte. Everything after the mapping is a keyword:

```python
from pewpew import line, render_sequence
from pewpew.patterns import Comet

frames = render_sequence(Comet, line(64), params={"speed": 1.5}, seed=1, frames=60)  # (60, 64, 3)
```

It takes the class and builds a fresh instance; `Renderer(Comet(), line(64))`
takes an instance and renders one frame per `advance_to(t)`. A per-fixture
pattern renders through the room's `Grouping`, on the room's own mapping:

```python
from pathlib import Path

from pewpew import render_sequence
from pewpew.patterns import Pulse
from pewpew.room.map import load_room

room, _ = load_room(Path("examples/room-60-bars.json"))
frames = render_sequence(Pulse, room.mapping, grouping=room.grouping, frames=60)
```

`features=` takes any object whose `at(t)` returns a `FeatureFrame`;
without one, a seeded fake drives the audio fields. To test against real
sound, play a feature log back (§13):
`features=ReplayFeatures(Path("song.jsonl"))`, from `pewpew.audio`.

## 7. NumPy traps

### 7.1 Structured effects need a field, not the pixel list

**Symptom:** you're writing something with neighbors — fire, ripples,
cellular automata — and there's no way to ask "what's next to this pixel."
`x`, `y`, `z`, `index` in `render` are a flat, unordered point list. There is
no grid to walk.

Fire2012's heat-diffusion stencil (each cell blends with its horizontal
neighbors) cannot be written over `self.pixels`: nothing in the per-pixel
contract has a notion of "the cell to my left." This is the study's headline
finding, and it tripped even its NumPy-fluent author.

**The fix:** the pattern owns an internal field at whatever resolution suits
the effect — not the mapping's pixel count — advances it in `before_render`
with ordinary grid math (`np.roll` for neighbors), and `render` samples that
field at each pixel's world coordinate. Declare the field in `setup` with
`self.buffer(name, shape)`; the engine allocates it, zeroes it on rebind, and
reallocates it when the mapping changes. `sample2d(field, x, y)` does the coordinate →
cell lookup — nearest cell, edges clamped — so every field pattern doesn't
reinvent it:

```python
import numpy as np
from pewpew import Float, Pattern, sample2d

class Fire(Pattern):
    cooling = Float(0.9, 0.0, 3.0, "/s", help="Heat each cell loses per second, at most")
    sparking = Float(10.0, 0.0, 30.0, "/s", help="Sparks per second in each column")
    rise = Float(14.0, 1.0, 40.0, "/s", help="How fast heat climbs")
    W, H = 16, 32  # field resolution — independent of the mapping's pixel count

    def setup(self, n, x, y, z, index):
        self.heat = self.buffer("heat", (self.H, self.W))

    def before_render(self, dt, features):
        cool = self.rng.random(self.heat.shape, dtype="float32") * (self.cooling * dt)
        self.heat = np.maximum(self.heat - cool, 0.0)

        lift = 1.0 - np.exp(-dt * self.rise)
        below = self.heat[:-1]
        up = (below + np.roll(below, 1, axis=1) + np.roll(below, -1, axis=1)) / 3.0
        self.heat[1:] = self.heat[1:] * (1.0 - lift) + up * lift  # simultaneous, not sequential

        ignite = self.rng.random(self.W) < (self.sparking * dt)
        sparks = (0.7 + 0.3 * self.rng.random(self.W)).astype("float32")
        self.heat[0] = np.where(ignite, np.maximum(self.heat[0], sparks), self.heat[0])

    def render(self, x, y, z, index):
        h = sample2d(self.heat, x, y)
        r = np.clip(h * 3.0, 0.0, 1.0)
        g = np.clip(h * 3.0 - 1.0, 0.0, 1.0)
        b = np.clip(h * 3.0 - 2.0, 0.0, 1.0)
        return np.stack([r, g, b], axis=1).astype("float32")
```

One more trap in that same diffusion line: a hand-ported C/Arduino Fire2012
loop updates rows top-down *in place*, so row `k` reads row `k-1` already
updated this frame. `self.heat[1:] = ...` above updates every row
*simultaneously* — it reads pre-frame values throughout. That's a different
diffusion (still fine, just not identical to the sequential original), and
there's no way to get the sequential version without a Python loop over rows,
which defeats the point of vectorizing.

### 7.2 Per-pixel state that isn't the internal-field case

**Symptom:** a one-off sparkle overlay — added on top of the base pattern,
not a structured field — quietly turns solid white and stays there.

Adding a spark directly to `self.pixels` (the previous frame's output) and
reading it back next frame is a feedback loop with a fixed point. With
`keep = fade(dt, tail)` and a `+0.3` spark added whenever a per-pixel hash
cleared a threshold, the pixel value converges to `min(1, keep·v + 0.3)`,
whose fixed point is `1.0` — every channel maxed, i.e. white — for any pixel
that triggers more than once.

**The fix (ADR-005, 2026-07-27 amendment):** don't launder per-pixel state
through the output buffer. Declare a real buffer in `setup` and decay *it*
directly with `fade`, in `before_render` — never through `self.pixels`:

```python
import numpy as np
from pewpew import Float, Pattern, fade

class Sparkle(Pattern):
    chance = Float(0.02, 0.0, 1.0, "/s", help="Chance per second that a pixel ignites")
    tail = Float(0.15, 0.01, 1.0, "s", help="Seconds for a spark to fade to about a third")

    def setup(self, n, x, y, z, index):
        self.spark = self.buffer("spark", n)  # own state, not self.pixels

    def before_render(self, dt, features):
        self.spark = self.spark * fade(dt, self.tail)
        ignite = self.rng.random(self.n) < (self.chance * dt)
        self.spark = np.where(ignite, 1.0, self.spark)

    def render(self, x, y, z, index):
        v = self.spark
        return np.stack([v, v, v], axis=1).astype("float32")
```

Verified: a pixel that ignites once climbs to 1.0 and decays cleanly over the
next several frames (`1.0 → 0.89 → 0.80 → 0.72 → 0.64 → 0.57 → ...` at 60 fps,
`tail=0.15`) — no ratchet, because nothing is fed back through the output.
Compare a pixel that re-triggers every frame through `self.pixels` instead:
`0.30 → 0.58 → 0.84 → 1.0` and stuck.

`self.buffer(name, shape, dtype=np.float32, fill=0.0)` can only be called
inside `setup`; `shape` is free-form (`n` for one value per pixel, `(H, W)`
for a field as in §7.1 — same mechanism, either use). Any name that already
exists on the class is refused, which covers engine state (`n`, `seed`,
`rng`, `pixels`), the hooks themselves, and your own params. Buffers are
zeroed on rebind and reallocated when the mapping changes; keeping them
across a hot reload is what the registry's name+shape keying is *for* (§3).
Inside `render`, every buffer — `self.pixels` included — is a read-only
view; writing to one raises `ValueError`, not a silent no-op, so a stray
write in `render` fails loudly during development rather than corrupting
state in production.

### 7.3 `np.where` runs both branches — always

**Symptom:** a guarded `sqrt`/`log`/division throws a `RuntimeWarning`, or
worse, poisons pixels that the guard was supposed to protect.

`if`-thinking says a guard short-circuits: the false branch never executes.
`np.where(cond, a, b)` doesn't short-circuit — NumPy computes both `a` and
`b` for every element, then picks per-element. In Comet's
`np.where(d < 0.02, 1.0, np.exp(-40.0 * d))` that is harmless, since `exp`
has no domain error, but it is a real trap the moment the discarded branch
can produce `nan` or `inf`:

```python
x = np.array([-1.0, 0.0, 4.0], dtype="float32")
bad = np.where(x >= 0, np.sqrt(x), 0.0)
# RuntimeWarning: invalid value encountered in sqrt
# bad == [0.0, 0.0, 2.0] — looks fine here, but the warning means sqrt(-1)
# ran and NumPy discarded a NaN, not that it was never computed.
```

That warning is a smoke alarm, not the fire. The fire is any code that
*blends* instead of *selects* — `mask * a + (1 - mask) * b` instead of
`np.where(mask, a, b)` — because `inf * 0` and `nan * 0` are `nan`, so the
poison survives into the branch you meant to keep:

```python
mask = (x >= 0).astype("float32")
combined = mask * np.sqrt(x) + (1 - mask) * 0.0
# combined == [nan, 0.0, 2.0] — the -1 entry's NaN leaked through the "0" weight
```

**The fix:** make the guard input safe *before* the math, not just the
output selection lazy. Clamp the domain so the discarded branch never goes
invalid in the first place:

```python
safe = np.where(x >= 0, np.sqrt(np.maximum(x, 0.0)), 0.0)  # sqrt never sees a negative
```

Same idea for `log` (clamp away from zero/negative) and division (add an
epsilon to the denominator, or clamp it away from zero) — guard the input,
not just the branch you show.

### 7.4 RNG belongs in `setup`/`before_render`, never `render`

**Symptom:** a pattern that looks deterministic — same seed, same params —
renders differently on repeated runs, and golden-frame tests won't hold
still.

`render` is called with the array-broadcast machinery and is meant to be a
pure function of coordinates and current state; `self.rng` (a seeded
`np.random.default_rng`) is only meaningful if draws happen in a fixed order
at a fixed point in the frame. The Fire example in §7.1 shows the shape: a
scalar `if random() < chance: ignite` becomes a masked draw over the whole
spark row (`ignite`, always `W` values), the spark heights are drawn every
frame whether or not they are used (`sparks`), and both draws happen in
`before_render`.

Two rules, both load-bearing for determinism (`CLAUDE.md`: no unseeded RNG,
same inputs must give byte-identical output):

- **Draw only in `setup`/`before_render`.** `render` runs against read-only
  buffers and must stay pure — there's nowhere for a `render`-time draw to
  put its state.
- **Keep the draw shape and order stable per frame.** Two `self.rng.random(...)`
  calls consume the RNG stream in sequence; if a draw becomes conditional
  (`if some_condition: self.rng.random(...)`) the stream desyncs between runs
  where the condition differs, and two runs from the same seed stop matching
  even though nothing looks wrong. Draw unconditionally, every frame, and
  mask or discard afterward instead of skipping the draw.

### 7.5 Decay must be `fade(dt, tau)`, not a per-frame multiplier

**Symptom:** a comet's trail is the right length on your desktop and a
different length on the deployed host, or after a frame-rate change,
with no code changed.

The classic trail decay from per-frame-loop engines is a constant multiplier
applied every tick —
`v *= 0.94`, FastLED's `fadeToBlackBy`. That constant implicitly assumes a
fixed tick rate; pewpew patterns are parameterized by `dt` (req Q-5,
`CLAUDE.md`), and at a different frame rate the same `0.94` decays the trail
over a different amount of *time*, not the same amount.

```python
# WRONG — frame-rate dependent: same code, different trail length at 30 vs 60 fps
self.keep = 0.94

# RIGHT — decays over the same wall-clock tail regardless of frame rate
from pewpew import fade
self.keep = fade(dt, self.tail)   # self.tail is a time constant in seconds
```

`fade(dt, tau)` is `exp(-dt/tau)` — the frame-rate-independent form. Use it
for every per-frame decay: trail fade, peak-hold falloff, sparkle decay (§7.2).
It's a plain Python `float`, computed once per frame from scalars, not
vectorized — `dt` and `tau` aren't per-pixel.

### 7.6 Coordinates are float32 — thresholds and bins bite at the edges

**Symptom:** an `IndexError` that only fires on the rightmost pixel, or a
sparkle that flickers differently than a reference render even at the same
seed.

Two edge traps, and both tripped the study's NumPy-fluent author.

**Binning.** Scalar thinking says `int(x * n)` maps a 0–1
coordinate to a bin. It does — until `x == 1.0`, the mapping's own rightmost
pixel, which lands in bin `n`, one past the end:

```python
xs = np.array([0.0, 0.5, 0.999, 1.0], dtype="float32")
(xs * 16.0).astype("int32")   # [0, 8, 15, 16]  <- 16 is out of range for 16 bins
```

`x == 1.0` isn't a theoretical edge case — it's the pixel that gets it,
every time, on every mapping with an inclusive 0–1 range. Use `bins(x, n)`,
which clamps to `[0, n-1]`:

```python
from pewpew import bins
bins(xs, 16)   # [0, 8, 15, 15]
```

**Hash thresholds.** A per-pixel hash computed in `float32` disagrees with
the same expression in `float64` right at a comparison threshold: in the
study it flipped a handful of pixels across `> 0.995`. Two dtype paths
through the same formula give different boolean masks on the same input. `hash01(x, seed, salt)` promotes
to `float64` internally so this doesn't depend on the caller remembering to
cast:

```python
from pewpew import hash01
spark = hash01(x, seed=self.seed, salt=frame_salt)  # always float64 internally
lit = spark > 0.995
```

If you write a hash or threshold comparison by hand instead, cast to
`float64` before the comparison, not after. In a warpable pattern, hash
`index` or a key that `setup` keeps, not `render`'s `x` (§8).

## 8. Warpable patterns

A coordinate op in an effect program (a fold, a rotation, a zoom; ADR-022)
changes `x`, `y` and `z` before the pattern under it renders. A pattern
says whether it may sit under one:

```python
class Ripple(Pattern):
    warpable = True   # the default is False
```

The flag is a promise about `render` (ADR-005 amendment 2026-11-05):

- It gives a correct frame for any finite `x`, `y`, `z`, including values
  far outside 0–1 and values that change every frame. `setup` still sees
  the mapping. A coordinate op hands on finite values only: NaN and
  infinity are outside the contract.
- `index` is the stable identity. It is never warped, so point `i` is
  always point `i`, and a `self.buffer(name, n)` read per index stays valid.

To keep the promise:

- **Do not precompute from coordinates in `setup`.** A distance, bin or hue
  computed there shows the unwarped geometry. Compute it in `render`.
- **Key per-pixel randomness on identity.** `hash01(x, ...)` on `render`'s
  `x` draws new pixels each frame a warp moves, so sparks crawl and
  multiply. Hash `index`, or a key that `setup` keeps: comet sets
  `self.key = x` in `setup` and hashes `self.key`. `setup` runs again on
  every bind and reload, so the key stays current.
- **Accept coordinates outside 0–1.** `bins` and `sample2d` clamp any
  finite value to the edge, and `hsv` wraps the hue. A distance that wraps
  at 1 needs `% 1.0`: comet's head uses `np.abs(x - self.head) % 1.0`. To
  turn a coordinate into an index by hand, clamp the float before the
  `int32` cast, as `bins` does: a value past the `int32` range casts to a
  different index on each platform.

A field at its own resolution, such as fire's heat grid, is sampled at
`render`'s coordinates, so a warp moves the flames. That is the intended
result. A subclass inherits the flag; set `warpable = False` on a subclass
that breaks the promise. Every gallery pattern is warpable.
`tests/test_warpable.py` shows how to test one: subclass it to warp the
coordinates on their way into `render`, and check the frames. Then hold
the warp still and compare the bytes with the pattern bound on the warped
mapping: a pattern that keeps geometry from `setup` renders different
bytes. A pattern that keeps an identity key in `setup`, as comet does, is
exempt from that second check.

## 9. Layers

A look is a stack of layers, the bottom one first. Each layer runs a
program (§10), most often one pattern, and mixes onto the layers below it
by its `opacity` (0 to 1), its `blend` and its `enabled` switch; `run
PATTERN` is a look of one layer, `base`. On the preview page, `+ layer`
adds a pattern or an op's example from the catalog, screened over the
layers already running. With two layers or more, the page lists them top
first: a row turns its layer on or off, and the row picked opens to the
layer's pattern, opacity, blend (`?` says what it does), ▲ ▼ (or Alt+↑ ↓
on the row) and remove, while the panel under the list shows that
layer's knobs. These edit the running look, which a save keeps. A looks
file holds layers too, version 4, played with `run PATTERN --looks FILE
--map SPEC`: PATTERN runs when the file names no current look, and the
map comes from PATTERN unless `--map` names one, so give a map the
file's looks suit (`grid:16x16` for a look that folds a plane). A look
the map cannot run starts PATTERN instead and says which map to try.
Sparkle screened over wash:

```json
{
  "version": 4,
  "current": "dusk",
  "looks": {
    "dusk": {"layers": [
      {"id": "base", "nodes": {"wash": {"op": "pattern", "args": {"pattern": "wash", "speed": 0.01}}}},
      {"id": "sparks", "opacity": 0.6, "blend": "screen",
       "nodes": {"sparkle": {"op": "pattern", "args": {"pattern": "sparkle", "tail": 0.4}}}}
    ]}
  }
}
```

A layer id and a node id are a lowercase letter and then up to 23
lowercase letters, digits or `_`. A node's `pattern` arg names its pattern
as the picker does; its other args are that pattern's params, as JSON,
the form `--param` takes. Every key of a layer but `id` and `nodes` has a
default (opacity 1, blend normal, enabled), and a look holds at most 16
layers. The whole file, with the idle cycle and the triggers, is described
in the docstring of `src/pewpew/aura/book.py`.

Every knob has an address, which the page, a `set`, `observe`, `--param`
and every refusal use:

    layers.<layer>.<node>.<param>          a pattern's param: layers.sparks.sparkle.tail
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

## 10. Effect programs

A layer can run an effect program: a small graph of ops, each one node,
in place of one pattern (ADR-022). Write it as a chain, in a pattern file
that `run` plays and hot-reloads like any other:

```python
from pewpew.fx.expr import noise, osc
from pewpew.fx.host import ProgramPattern

class Tide(ProgramPattern):
    program = osc(8, 0.1).id("waves").kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember").id("tint")
```

A source (`osc`, `noise`, `voronoi`, `shape`, `pattern("plasma")`, ...) is
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
(`kaleid` on a strip: use `mirror` on u). Inside a program a pattern
renders at the program's points, so it must be a pixel-unit pattern, and
only a warpable one (§8) may sit under a coord op; a fixture-unit pattern
(`sparkle`) runs on a layer of its own.

A look that runs `Tide` (`run tide.py`, or a pick of it) keeps one
pattern node naming the file, so the file stays its content; its knobs
are the program's, `layers.base.waves.freq` and so on. A knob you move
from the file's literal is saved on that node as `"waves.freq": 9.0`,
and a recall starts the node there:
`{"tide": {"op": "pattern", "args": {"pattern": "tide", "waves.freq": 9.0}}}`.

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
  climbing to white (§7.2). `trails` is the same per point, with no motion.
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
print(render(made, "grid:16x16", seconds=2).metrics)  # render and measure it (§11)
saved = {"version": 4, "current": "mine", "looks": {"mine": encode_look(made)}}
Path("mine.look.json").write_text(json.dumps(saved))  # the looks file `run --looks` plays
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
is a `front` path that names no knob. When a pattern edit or a pick takes
a route's knob away, or narrows it below the route's depth, the route
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
  layer that feeds back the frame below, and sparkle on top.
- `firefly-ink` (any map): fireflies wander, and their glow bleeds along
  the points.

Each also has signals and routes (a slow `walk` or `lfo` on a hue, a warp
or a size; the beat or a sound band on what pulses) and a `front` list of
the knobs to turn first. In `milk-bloom`, `signals.trip.value` is a macro
over the feedback's zoom, decay and swirl.

## 11. Checking and rendering looks from the command line

A look can be checked, rendered, measured and compared without running
the aura. A file is a looks file (a `.look.json` file, version 4), as
`run --looks` plays it, even for one look; a single look, bare, goes on
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
  `layers.base.comet.speed`, the words the aura itself uses, and a
  did-you-mean: `pattern 'comt' does not load: unknown pattern 'comt'; ...
  (did you mean 'comet'?)`. A program's problems name its node
  (`layers.base.fold`), with codes such as `unknown-op`, `cycle` and
  `bad-ref`. With `--json`, a look that checks comes back normalized,
  every knob of every node written out.
- **`fx render`** renders through the aura's own layer stack and master,
  so the frames are what `run PATTERN --seed SEED --looks FILE --map SPEC`
  shows when it starts in that look, `SPEC` the map `fx render` names. `--seed` is `run --seed`: it seeds the stand-in
  audio and room features, and the look's own `seed` seeds its layers.
  `--map` takes `line:64`, `grid:16x16`, `lattice:8`, a room map file, or
  `auto` (the default): the geometry `run` gives the bottom layer's pattern,
  such as `line:300` for comet and the canopy for pulse, and `grid:16x16`
  for a program. A program the map does not support is refused before it
  renders (`wrong-dims`: `kaleid` on a strip).
- A render prints a **handle**, `r1-` and 20 hex digits, that `fx sheet`,
  `fx metrics` and `fx compare` take in place of a file. The same look,
  map, seconds, fps, seed and engine code always give the same handle.
  The frames are kept under `$PEWPEW_CACHE` (default
  `~/.cache/pewpew/renders`), which drops the least recently used past a
  size cap; a handle it dropped exits 3 with how to get it back: render
  the same spec again.
- **`fx compare A B`** renders a look B as A was rendered: the same map
  spec, seconds, fps and seed; a look A renders as B was when B alone is
  a handle. With `auto`, each look gets the map of its own bottom
  pattern, so two looks whose bottom patterns get different maps do not
  compare until you name one with `--map`.
- **`verify looks`** passes a look that checks, has no layer that raises,
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
plays unsaved, as a pick does. A `save` with a null name saves the running
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
why.

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

## 12. Agents: the MCP server

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

A look's patterns go by name only, so no tool runs a file. A refused look
comes back as an error that lists each problem's code, path and fix. The
server also serves the catalog (`pewpew://catalog`), the example looks
(`pewpew://looks/{name}`), this guide and the catalog reference
(`pewpew://docs/{topic}`) and render sheets
(`pewpew://render/{handle}/sheet.png`), and two prompts, `design-look`
and `critique-pair`. The `authoring-looks` skill in `.claude/skills/`
teaches the loop, and the `look-critic` subagent judges two renders.

## 13. Real sound

By default the audio fields come from a seeded stand-in: 16 bands of
slow sine waves and a beat at 120 BPM. `run --audio FILE.wav` analyses a
WAV file instead, frame by frame as live input will be analysed, and plays
it on a loop. pewpew only listens: nothing plays the file aloud.

```
uv run python -m pewpew run geq --audio song.wav
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
  tracker searches. A pattern reads the same fields with real or simulated
  sound, so nothing in it changes.

`audio analyse` prints the tempo, its confidence, the beat times and the
levels of a file; `--json` prints them for an agent. `--feature-log PATH`
(on `run` or `audio analyse`) writes each frame's features, and
`--audio replay:PATH` plays them back byte for byte, at any `--fps`. A
feature log from a microphone is close to a speech recording, so never
keep one with people in the room. `--audio-delay MS` is for speakers the room hears late,
such as Bluetooth ones: it delays the levels and moves the beat.

Live sound comes from one of the computer's inputs, an audio interface's
line-in or a microphone, named as `audio list` prints it:
`run geq --audio "Scarlett 2i2 USB"`. It needs the `audio` extra, and
`--audio-channel N` reads one channel. `docs/audio.md` covers choosing
the input, what happens when it is unplugged, its health row and privacy.
Capture nodes come later (`research/topics/RA-28-audio-input.md`).

## Reference

| Helper | Signature | What it's for |
|---|---|---|
| `time(interval)` | `time(interval) -> float` | 0–1 sawtooth phase, period `interval * 65.536` s |
| `wave(p)` | `wave(p) -> array` | 0–1 phase → 0–1 sine, `wave(0) = 0.5` rising |
| `triangle(p)` | `triangle(p) -> array` | 0–1 phase → 0→1→0 triangle |
| `square(p, duty=0.5)` | `square(p, duty) -> array` | 0–1 phase → 1/0 pulse |
| `hsv(h, s, v)` | `hsv(h, s, v) -> (...,3) array` | branch-free HSV → linear RGB |
| `fade(dt, tau)` | `fade(dt, tau) -> float` | frame-rate-independent decay keep-factor (§7.5) |
| `bins(x, n)` | `bins(x, n) -> int array` | coordinate → bin index, edge-clamped (§7.6) |
| `sample2d(field, x, y)` | `sample2d(field, x, y) -> array` | nearest-cell lookup into an internal field (§7.1) |
| `hash01(x, seed, salt)` | `hash01(x, seed, salt) -> array` | stable per-pixel pseudo-random value, float64 (§7.6) |
| `self.buffer(name, shape, dtype=np.float32, fill=0.0)` | called in `setup` only | declare engine-managed persistent state (§7.1, §7.2) |
| `Float`, `Int`, `Bool`, `Choice`, `Color`, `Palette` | class attribute, e.g. `Float(default, lo, hi, unit)` | declare a param; ranges and kinds are enforced (§2) |
| `self.color.rgb(level)` | `HSV.rgb(v) -> (N,3) array for an (N,) v` | a color param as linear RGB, its value scaled per pixel (§2) |
| `self.palette.rgb(t)` | `Gradient.rgb(t) -> (N,3) array for an (N,) t` | a palette param as linear RGB along a 0–1 position (§2); `pewpew.color.gradient_lut` and `sample` underneath |
| `uv run python -m pewpew run <spec>` | name, `file.py`, `file.py:Class`, `--pattern-dir DIR` | run a gallery or user pattern live; the file is hot-reloaded on save (§1, §3) |
| `units = "fixture"` | class attribute; `"pixel"` (default) or `"fixture"` | render once per fixture of a room map (§4) |
| `warpable = True` | class attribute; `False` (default) or `True` | let a coordinate op warp the pattern's `x`, `y`, `z` (§8) |
| `run <spec> --room PATH` | room map JSON; `--units`, `--no-ddp`, `--dry-run` | run on a room's fixtures and boards; the map reloads on save (§4) |
| `run <spec> --looks PATH` | looks file, version 4 | save and recall looks, layered ones included (§9) |
| `run <spec> --audio NAME` | an input's name, `FILE.wav` or `replay:PATH`; `--audio-channel N`, `--audio-delay MS`, `--feature-log PATH` | real sound in the audio fields: a line-in or a microphone (needs pewpew[audio]), a WAV file analysed on a loop, or a feature log played back (§13, docs/audio.md) |
| `uv run python -m pewpew audio analyse FILE` | a WAV file; `--json`, `--fps`, `--feature-log PATH` | the tempo, confidence, beat times and levels pewpew hears in a file (§13) |
| `uv run python -m pewpew audio list` | `--json` | this computer's inputs by the exact names `run --audio` takes; opens none (§13) |
| `ProgramPattern` | class attribute `program = osc(8).kaleid(5)...` | run an effect program as a pattern (§10) |
| `uv run python -m pewpew fx catalog` | `--kind K`, `--query Q`, `--json`, `--format markdown`; `fx show OP` | every op, pattern, blend, palette and param kind, with examples (§10) |
| `uv run python -m pewpew boards scan` | `--subnet CIDR` (default: this laptop's /24), `--json` | list the WLED boards on the network, with address, name, MAC and live state, and with `--json` each one's health (§4) |
| `uv run python -m pewpew observe URL` | the `preview at` address; `--seconds S`, `--sheet PATH`, `--json` | watch a running engine without changing it: its aura state and approximate metrics of the frames it streams, and a contact sheet |
| `uv run python -m pewpew push URL LOOK` | `--fade S`, `--set PATH=VALUE`, `--dry-run`, `--json`, `--allow-host IP` | send a whole look, then knob values, to an engine on this machine run with `--preview --accept-looks`; tier 1: check with `--dry-run` first; each send is audit-logged |
| `uv run --extra agent python -m pewpew mcp` | `--tier 0` (default) or `1`, `--allow-host IP` | serve the tools above to an AI agent over MCP on stdio (§12) |
| `features.events` | tuple of `Event(name, source, value, priority, t, tick)` | the room events that fired on this frame (§5) |
| `render_sequence(Cls, mapping, *, params, seed, frames, fps, features, grouping, units)` | returns (F,N,3) float32 | render a deterministic sequence (§6) |
| `Renderer(pattern, mapping, *, ...)` | `advance_to(t)`, `params.set(name, value)` | render live, one frame per call (§6) |

Every example above runs against the real engine (`src/pewpew/`), not the
frozen `bench/authoring/` prototype — verify a new API against the source
before trusting a docstring, this one included.
