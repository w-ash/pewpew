# Authoring patterns

A pattern is a class with up to three hooks:

```python
def setup(self, n, x, y, z, index):     # once, when the pattern binds to a mapping
def before_render(self, dt, features):  # once per frame — the only place state changes
def render(self, x, y, z, index):       # pure — called every frame, returns the frame
```

`render` looks like it runs once per pixel. It doesn't: `x`, `y`, `z`, `index` are
NumPy arrays — one element per pixel in the mapping — and `render` runs once
per *frame*, over the whole array at once. Code that reads like scalar Python
(`x + self.phase`, `hsv(hue, 1, v)`) mostly works unchanged, because NumPy
broadcasts. The places it doesn't are exactly the places `bench/authoring/*.py`
hit friction writing five real patterns against this contract
(`bench/results/authoring-2026-07-16.md`). That study's own framing is the
one to trust here: **13 of its 17 recorded stumbles were only avoided because
the author already knew NumPy** — a scalar-thinking author hits every one.
This document is those six friction points, each with the failure you'd
actually see and the fix. `# STUMBLE-N` citations point at the exact line in
`bench/authoring/*.py`.

`render` must be pure — no writes, no RNG, no wall clock. That purity is what
makes patterns testable (golden frames, deterministic scrubbing) and is not
optional (architecture §8, `CLAUDE.md`).

## 1. Structured effects need a field, not the pixel list

**Symptom:** you're writing something with neighbors — fire, ripples,
cellular automata — and there's no way to ask "what's next to this pixel."
`x`, `y`, `z`, `index` in `render` are a flat, unordered point list. There is
no grid to walk.

This is stumble **#12**, the study's headline finding, and it was a `hit` —
it tripped even the NumPy-fluent author. Fire2012's heat-diffusion stencil
(each cell blends with its horizontal neighbors) is inexpressible over
`self.pixels` as given; nothing in the per-pixel contract has a notion of
"the cell to my left."

**The fix:** the pattern owns an internal field at whatever resolution suits
the effect — not the mapping's pixel count — advances it in `before_render`
with ordinary grid math (`np.roll` for neighbors), and `render` samples that
field at each pixel's world coordinate. Declare the field in `setup` with
`self.buffer(name, shape)`; the engine allocates it, zeroes it on rebind, and
reallocates it when the mapping changes. `sample2d(field, x, y)` does the coordinate →
cell lookup — nearest cell, edges clamped — so every field pattern doesn't
reinvent it (stumble **#15**, the same boilerplate repeated in every field
pattern before this helper existed):

```python
import numpy as np
from pewpew import Pattern, Param, sample2d

class Fire(Pattern):
    name = "fire"
    cooling = Param(0.9, 0.0, 3.0, "Cooling/s")
    sparking = Param(10.0, 0.0, 30.0, "Sparks/s per column")
    rise = Param(14.0, 1.0, 40.0, "Rise rate")
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
which defeats the point of vectorizing (stumble **#13**, shielded).

## 2. Per-pixel state that isn't the internal-field case

**Symptom:** a one-off sparkle overlay — added on top of the base pattern,
not a structured field — quietly turns solid white and stays there.

This is stumble **#17**, a `hit`: the first draft added a spark directly to
`self.pixels` (the previous frame's output) and read it back next frame. That
feedback loop has a fixed point. With `keep = fade(dt, tail)` and a `+0.3`
spark added whenever a per-pixel hash cleared a threshold, the pixel value
converges to `min(1, keep·v + 0.3)`, whose fixed point is `1.0` — every
channel maxed, i.e. white — for any pixel that triggers more than once. The
study's original workaround was to re-salt the hash every 125 ms so no pixel
kept re-triggering; that dodges the ratchet but doesn't remove the trap.

**The fix (ADR-005, 2026-07-27 amendment):** don't launder per-pixel state
through the output buffer. Declare a real buffer in `setup` and decay *it*
directly with `fade`, in `before_render` — never through `self.pixels`:

```python
import numpy as np
from pewpew import Pattern, Param, fade

class Sparkle(Pattern):
    name = "sparkle"
    chance = Param(0.02, 0.0, 1.0, "Ignite chance/s")
    tail = Param(0.15, 0.01, 1.0, "Spark decay, s")

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
for a field as in §1 — same mechanism, either use). Any name that already
exists on the class is refused, which covers engine state (`n`, `seed`,
`rng`, `pixels`), the hooks themselves, and your own `Param`s. Buffers are
zeroed on rebind and reallocated when the mapping changes; keeping them
across a hot reload is what the registry's name+shape keying is *for* (§9).
Inside `render`, every buffer — `self.pixels` included — is a read-only
view; writing to one raises `ValueError`, not a silent no-op, so a stray
write in `render` fails loudly during development rather than corrupting
state in production.

## 3. `np.where` runs both branches — always

**Symptom:** a guarded `sqrt`/`log`/division throws a `RuntimeWarning`, or
worse, poisons pixels that the guard was supposed to protect.

`if`-thinking says a guard short-circuits: the false branch never executes.
`np.where(cond, a, b)` doesn't short-circuit — NumPy computes both `a` and
`b` for every element, then picks per-element. This is stumble **#5**,
shielded in the comet pattern (`np.where(d < 0.02, 1.0, np.exp(-40.0 * d))` —
harmless, `exp` has no domain error) but a real trap the moment the
discarded branch can produce `nan` or `inf`:

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

## 4. RNG belongs in `setup`/`before_render`, never `render`

**Symptom:** a pattern that looks deterministic — same seed, same params —
renders differently on repeated runs, and golden-frame tests won't hold
still.

`render` is called with the array-broadcast machinery and is meant to be a
pure function of coordinates and current state; `self.rng` (a seeded
`np.random.default_rng`) is only meaningful if draws happen in a fixed order
at a fixed point in the frame. Fire's ignition step is stumble **#14**
(shielded, but friction even so): a scalar `if random() < chance: ignite`
becomes a masked draw over the whole ignition array, and the draw itself must
happen in `before_render`:

```python
def before_render(self, dt, features):
    ignite = self.rng.random(self.W) < (self.sparking * dt)   # draw shape: always (W,)
    sparks = (0.7 + 0.3 * self.rng.random(self.W)).astype("float32")  # always drawn, in this order
    self.heat[0] = np.where(ignite, np.maximum(self.heat[0], sparks), self.heat[0])
```

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

## 5. Decay must be `fade(dt, tau)`, not a per-frame multiplier

**Symptom:** a comet's trail is the right length on your desktop and a
different length on the deployed host, or after a frame-rate change,
with no code changed.

This is stumble **#2**, shielded but real: the classic trail decay from
per-frame-loop engines is a constant multiplier applied every tick —
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
for every per-frame decay: trail fade, peak-hold falloff, sparkle decay (§2).
It's a plain Python `float`, computed once per frame from scalars, not
vectorized — `dt` and `tau` aren't per-pixel.

## 6. Coordinates are float32 — thresholds and bins bite at the edges

**Symptom:** an `IndexError` that only fires on the rightmost pixel, or a
sparkle that flickers differently than a reference render even at the same
seed.

Two distinct edge traps, both `hit` even by the NumPy-fluent study author —
these are the two stumbles that tripped everyone, shielded or not.

**Binning (stumble #9).** Scalar thinking says `int(x * n)` maps a 0–1
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

**Hash thresholds (stumble #6).** A per-pixel hash computed in `float32`
disagrees with the same expression in `float64` right at a comparison
threshold — close enough to flip a handful of pixels across `> 0.995`, on
the exact fixture used in the study. This is a real, measured divergence,
not a rounding curiosity: two dtype paths through the same formula give
different boolean masks on the same input. `hash01(x, seed, salt)` promotes
to `float64` internally so this doesn't depend on the caller remembering to
cast:

```python
from pewpew import hash01
spark = hash01(x, seed=self.seed, salt=frame_salt)  # always float64 internally
lit = spark > 0.995
```

If you write a hash or threshold comparison by hand instead, cast to
`float64` before the comparison, not after.

## 7. Params are a contract, not a suggestion

Declare a knob in one line, anywhere in the class body:

```python
class Plasma(Pattern):
    name = "plasma"
    speed = Param(0.5, 0.0, 2.0, "Speed")     # default, lo, hi, label
    scale = Param(4.0, 1.0, 10.0, "Scale")
```

At bind the engine writes plain floats onto the instance, so `self.speed`
reads as a number with no indirection on the frame path. The declaration
itself survives, which is what lets the runner, the preview page, and the
liveness check all ask a pattern what knobs it has.

**`lo` and `hi` are enforced.** A value outside them is refused, on the
command line and everywhere else:

```
$ python -m pewpew run plasma --param speed=5
plasma.speed must be within 0.0..2.0, got 5.0. widen the 'speed' Param in
src/pewpew/patterns/plasma.py, or pick a value in range
```

Widening the declaration is the intended way to go further, and it is a
better answer than it looks: the range is what a slider's endpoints are
built from, so widening it moves the slider too. The engine does not clamp,
because a clamp renders one value while every surface displays another —
which is the dead-knob problem this contract exists to prevent.

**`label` is the unit, not the name.** `"Rev/s"`, `"Sparks/s per column"`.
The attribute name is what a control surface captions with; the label is
what it annotates with. Write it as a unit and it stays useful.

**The declaration wins over `__init__`.** Assigning `self.speed` in
`__init__` does not change the knob's starting value — the engine overwrites
it at bind. Set the value you want as the `Param` default.

**A knob that changes nothing fails the build.** `tests/test_param_liveness.py`
moves every declared param from `lo` to `hi` and requires the rendered
sequence to change. It exists because `sdf3d`'s `spin` was a mathematical
no-op that shipped: the pattern animated convincingly from other motion, and
neither review nor golden frames noticed. If your knob fails it, either
nothing reads it in a way that reaches a pixel, or the range is too narrow to
matter — both are worth knowing.

**Your knobs become sliders.** `python -m pewpew run <pattern> --preview`
serves one slider per declared `Param`, bounded by `lo`/`hi` and stepped by
the quantization the engine derives from them. They drive the real engine,
so what a slider shows is what is being rendered; an out-of-range value is
refused on the socket the same way it is on the command line, and every open
tab follows whichever one moved last.

One limit to keep in mind: a value set while the show runs only reaches a
pattern that reads it every frame. Precompute a table from `self.scale` in
`setup` and a live change will not be seen until the next bind — which
`test_param_liveness.py` now also checks, by turning each knob mid-sequence
and requiring the frames after it to diverge.

## 8. Running your own pattern

The runner takes a file as readily as a gallery name:

```
$ python -m pewpew run effects/mine.py --map line:64 --preview
$ python -m pewpew run effects/mine.py:Spark      # the file defines several
$ python -m pewpew run mine --patterns effects/   # effects/mine.py, then the gallery
$ python -m pewpew run comet                      # always the gallery, never ./comet.py
```

A file must define exactly one `Pattern` subclass of its own, or name the one
you mean with `:ClassName`. A base class imported from a sibling module does
not count, and sibling imports work as they would for a script: the file's
directory is put on `sys.path`. A bare name is the gallery unless `--patterns`
names a directory holding `<name>.py`; the working directory is never searched,
so a stray `comet.py` next to your shell cannot shadow the built-in.

Loading a file runs it. That is what a local dev tool does; it is also why
nothing on the preview socket can ask the engine to load one.

## 9. Save the file; the show keeps running

While `run` is up, the pattern's source file is watched (`--no-reload` turns
that off; gallery files are watched too, so editing
`src/pewpew/patterns/comet.py` reloads it). A save re-executes the file and
swaps the new class in between two frames. The show does not restart:

- **Engine time** continues. `time()` and every `dt` are what they would have
  been without the save.
- **Parameter values** are kept when they still fit the new declaration. A
  value outside a narrowed range resets to the *new default*, never a clamp
  (ADR-006). A knob you removed disappears from the sliders; one you added
  appears at its default. The preview page rebuilds its sliders on the spot.
- **Buffers** — `self.pixels` and everything from `self.buffer` — are handed
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

Two consequences worth knowing. A `Param` default or an `__init__` constant
you edit is not what a *kept* value reads — the live value wins, so press
**reset** on the preview (params) or rename the attribute (scalars) to see
the new number. And a value kept from the old code is only as meaningful as
the new code's use of it: rename an attribute when its meaning changes, and
it starts fresh by construction.

A save that does not load — a syntax error, an import that fails, a `setup`
that raises, a second `Pattern` class with no `:ClassName` to choose it —
keeps the last-good pattern running and shows why on the status line under
the terminal grid and the preview page's banner (with the line number and
never the path). Fix the file and save again; the error clears. The `run`
log has the full traceback once the terminal is handed back. Only the entry
file is watched: an edit to a sibling module it imports, or to the engine,
needs a restart.

## Reference

| Helper | Signature | What it's for |
|---|---|---|
| `time(interval)` | `time(interval) -> float` | 0–1 sawtooth phase, period `interval * 65.536` s |
| `wave(p)` | `wave(p) -> array` | 0–1 phase → 0–1 sine, `wave(0) = 0.5` rising |
| `triangle(p)` | `triangle(p) -> array` | 0–1 phase → 0→1→0 triangle |
| `square(p, duty=0.5)` | `square(p, duty) -> array` | 0–1 phase → 1/0 pulse |
| `hsv(h, s, v)` | `hsv(h, s, v) -> (...,3) array` | branch-free HSV → linear RGB |
| `fade(dt, tau)` | `fade(dt, tau) -> float` | frame-rate-independent decay keep-factor (§5) |
| `bins(x, n)` | `bins(x, n) -> int array` | coordinate → bin index, edge-clamped (§6) |
| `sample2d(field, x, y)` | `sample2d(field, x, y) -> array` | nearest-cell lookup into an internal field (§1) |
| `hash01(x, seed, salt)` | `hash01(x, seed, salt) -> array` | stable per-pixel pseudo-random value, float64 (§6) |
| `self.buffer(name, shape, dtype=np.float32, fill=0.0)` | called in `setup` only | declare engine-managed persistent state (§1, §2) |
| `Param(default, lo, hi, label)` | class attribute | declare a knob; `lo`/`hi` are enforced, `label` is the unit (§7) |
| `python -m pewpew run <spec>` | name, `file.py`, `file.py:Class`, `--patterns DIR` | run a gallery or user pattern live; the file is hot-reloaded on save (§8, §9) |

Every example above runs against the real engine (`src/pewpew/`), not the
frozen `bench/authoring/` prototype — verify a new API against the source
before trusting a docstring, this one included.
