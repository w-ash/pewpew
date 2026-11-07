# Looks by shape

Shapes that work, as small single looks. Each one passes `look_check`
(a test in `tests/test_agent_docs.py` checks and renders every JSON
block here). The ops' args, ranges and defaults are in the catalog, not
here: call `catalog_search` before you change one.

## A field through a palette

The basic look: a source op makes a scalar field from 0 to 1, and
`palette` colours it. Most sources move on their own (`sync`, `speed`);
`palette`'s `cycle` turns the colours slowly.

```json
{"layers": [{"id": "base", "out": "tint", "nodes": {
  "swell": {"op": "osc", "args": {"freq": 3.0, "sync": 0.15, "axis": "u"}},
  "tint": {"op": "palette", "in": ["swell"], "args": {"palette": "ocean"}}}}]}
```

On a strip, use `axis: "u"` (the distance along the strip); x, y and z
are positions in space.

## Ripple one field with another

`modulate` lets a second field (`noise`, usually) displace the first, so
straight bands wander. Keep `amount` small (0.05 to 0.2).

```json
{"layers": [{"id": "base", "out": "tint", "nodes": {
  "swell": {"op": "osc", "args": {"freq": 3.0, "sync": 0.15, "axis": "u"}},
  "chop": {"op": "noise", "args": {"scale": 2.0, "speed": 0.07}},
  "ripple": {"op": "modulate", "in": ["swell", "chop"], "args": {"amount": 0.12}},
  "tint": {"op": "palette", "in": ["ripple"], "args": {"palette": "ocean"}}}}]}
```

## Fold or turn space

A coord op (`kaleid`, `polar`, `rotate`, `mirror`, `repeat`, ...)
changes where the node it reads samples, so it sits after its input in
`in` and wraps it. A plane op needs a map with two axes or more: on a
strip, `look_check` and `look_render` refuse it with what to use instead
(`mirror` on u). Only a warpable source may sit under a coord op; an
op's catalog record says whether it is.

```json
{"layers": [{"id": "base", "out": "tint", "nodes": {
  "rings": {"op": "osc", "args": {"freq": 5.0, "sync": 0.1, "axis": "y"}},
  "swirl": {"op": "polar", "in": ["rings"], "args": {}},
  "fold": {"op": "kaleid", "in": ["swirl"], "args": {"sides": 5}},
  "tint": {"op": "palette", "in": ["fold"], "args": {"palette": "synthwave"}}}}]}
```

## Sparks over a field

Two layers: a calm field at the bottom and sparse `particles` on top,
mixed with `screen` at part opacity. `screen` adds light without washing
out to white; `add` runs to white and clips.

```json
{"layers": [
  {"id": "base", "out": "glow", "nodes": {
    "heat": {"op": "noise", "args": {"scale": 2.0, "speed": 0.07}},
    "glow": {"op": "palette", "in": ["heat"], "args": {"palette": "ember"}}}},
  {"id": "sparks", "blend": "screen", "opacity": 0.6, "out": "glint", "nodes": {
    "motes": {"op": "particles", "args": {"rate": 80.0, "life": 0.6, "speed": 0.02, "emit": "anywhere", "size": 0.03}},
    "glint": {"op": "palette", "in": ["motes"], "args": {"palette": "ember"}}}}]}
```

## An effect on the layers below

A layer whose program starts from `below` reads the stack blended so
far, so it changes what is under it (a hue turn, a fold) rather than
adding a picture of its own. On the bottom layer it reads black.

```json
{"layers": [
  {"id": "base", "out": "tint", "nodes": {
    "swell": {"op": "osc", "args": {"freq": 3.0, "sync": 0.15, "axis": "u"}},
    "tint": {"op": "palette", "in": ["swell"], "args": {"palette": "ocean"}}}},
  {"id": "tilt", "out": "turn", "nodes": {
    "under": {"op": "below", "args": {}},
    "turn": {"op": "hue", "in": ["under"], "args": {"amount": 90.0}}}}]}
```

## Trails

`prev` reads the layer's own last frame. Blend it under a moving thing
with `max` to leave a trail; the blend's `amount` sets how long it lasts.

```json
{"layers": [{"id": "base", "out": "trail", "nodes": {
  "head": {"op": "lissajous", "args": {"heads": 1}},
  "last": {"op": "prev", "args": {}},
  "trail": {"op": "blend", "in": ["head", "last"], "args": {"mode": "max", "amount": 0.9}}}}]}
```

## Move a knob with a signal

A look's `signals` each give one number a frame: `lfo` and `walk` swing
from -1 to 1; `env`, `band`, `beat` and `knob` give 0 to 1
(`catalog_search` with kind `signal`). Each route adds `depth` times its
signal to the knob at `path`, in the knob's own units, so the knob's own
value is where it rests. Keep a route on brightness or opacity slow: a
fast one strobes.

```json
{"layers": [{"id": "base", "out": "tint", "nodes": {
  "swell": {"op": "osc", "args": {"freq": 3.0, "sync": 0.15, "axis": "u"}},
  "tint": {"op": "palette", "in": ["swell"], "args": {"palette": "ocean"}}}}],
 "signals": {"breath": {"op": "lfo", "args": {"rate": 0.1}}},
 "routes": [{"source": "breath", "path": "layers.base.swell.freq", "depth": 2.0}]}
```

## Rules of thumb

These come from the gates and the metrics, not from taste:

- Flashing is counted per pixel: a fast `sync`, a high `freq` with
  `posterize`, or a fast palette `cycle` through a dark stop can pass 3
  flashes a second. Read `flash_rate_max` after every speed change.
- Every knob must change the picture (`verify looks`). A node whose
  output nothing reads, or an arg its op ignores at that setting, fails
  the gate: remove it.
- One idea per layer. Name each node for its role (`swell`, `tint`),
  since its id is part of every knob address and never changes.
