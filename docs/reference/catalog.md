# Effects catalog

Generated from `pewpew.fx.catalog` by `python -m pewpew fx catalog --format markdown`;
a test fails when it drifts. Do not edit it by hand.

An op's args are params: `default lo..hi unit`. A source op is a function (`osc(8)`); every
other op is a method of what it reads (`.kaleid(5)`). Coord ops change the coordinates their
input reads, so they wrap what comes before them. A signal op gives one number a frame, which
a look's route adds to a knob (`lfo(0.1).to("layers.base.osc.freq", depth=2)`), or which sweeps
the knob's sweet range when given as its arg (`osc(8, sync=lfo(0.1))`).

## Source ops

### `attractor` — Attractor

Glowing trails that fly round a looping butterfly or cloud, a strange attractor: points fly along a Lorenz butterfly, or hop across a Clifford cloud of filaments that slowly morphs, and their glow builds up and fades as the figure turns about the upright axis. `count` points glow for `trail` and turn at `spin`. On a panel the butterfly faces front, wings upright, and the flat Clifford cloud lies in the panel's plane and turns in it. Brightness is the glow against its mean over the lit cells, so a few heads and a dense cloud read alike.

Reads none; gives scalar. Dimensions: 2, 3. a strip shows only a line through it; use lissajous or particles

- `kind`: 'lorenz' of lorenz, clifford. Lorenz: a butterfly ribbon in 3D; Clifford: a flat cloud of filaments.
- `count`: 24 1..2000. Points it draws: a few ribbons, or a dense cloud.
- `speed`: 0.3 0.0..1.0 Hz. How fast it moves: Lorenz points fly, a Clifford cloud morphs.
- `spin`: 10.0 -90.0..90.0 °/s. How fast the figure turns.
- `size`: 0.04 0.02..0.3. Radius of each point's glow.
- `trail`: 1.0 0.1..10.0 s. How long its glow lasts.

    attractor("lorenz", 24, 0.3, 10)
    attractor("clifford", 2000, 0.05, 0, 0.04, 2).palette("ember")

### `below` — Below

The frame of the layers below this one, as blended so far: a layer whose program starts here is an effect on the stack below it.

Reads none; gives rgb. Dimensions: 1, 2, 3.

    below().hue(90)

### `life` — Chase

Waves of color that chase round and round across the lights: a cyclic cellular automaton, each point counting round its steps and moving on a step when a neighbor is one step ahead. `states` sets how many steps. From noise, waves and turning spirals form. On a strip or a small map the waves die out and the points settle, so `sparks` move points on at random, and each starts a new wave. It shows each point's step as a share of the cycle, so give it a palette whose ends match. With `cell` above 0 it runs on a grid of square cells laid over the map instead, each light showing the cell it is in, so waves cross the gaps between strips a few apart.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `states`: 6 3..12. Steps in one cycle: more give wider bands, which settle sooner.
- `speed`: 6.0 0.5..20.0 /s. How fast the waves chase.
- `sparks`: 2.0 0.0..20.0 /s. Points a second that move on by themselves, each starting a wave; at 0 a strip settles.
- `cell`: 0.0 0.0..8.0 ×. At 0 it runs on the lights; above 0 on square cells this many times the lights' mean spacing wide, laid over the map, so waves cross the gaps between strips.

    life(6, 20, 4)
    life(5, speed=4).palette("synthwave", cycle=0.02)
    life(8, 6, 8, cell=1.5)

### `lissajous` — Lissajous

Glowing heads that trace a looping knot through the room: a Lissajous figure, its own number of loops along each axis. `a`, `b` and `c` are the loops a cycle along x, y and z.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `a`: 3 1..9. How many times the knot crosses the room side to side.
- `b`: 4 1..9. How many times the knot rises and falls.
- `c`: 5 1..9. How many times the knot comes near and goes far.
- `speed`: 0.1 0.0..1.0 Hz. How fast the heads run round the knot.
- `heads`: 3 1..8. Heads spaced evenly along the knot.
- `width`: 0.06 0.01..0.3. Size of each head's glow.

    lissajous(3, 4, 5, 0.1, 3, 0.15)
    lissajous(heads=5).palette("ice")

### `metaballs` — Metaballs

Soft blobs that wander the room and melt together where they meet.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `count`: 5 1..16. How many blobs.
- `radius`: 0.15 0.02..0.5. Size of each blob.
- `smooth`: 0.1 0.0..0.5. How far apart blobs start to melt together.
- `speed`: 0.1 0.0..1.0 Hz. How fast the blobs wander.
- `glow`: 0.1 0.01..0.5. Softness of the blobs' edges.

    metaballs(5, 0.16, 0.12, 0.08)
    metaballs(3).palette("candy")

### `noise` — Noise

Smooth random hills that slowly change, finer ones on top. `octaves` sets how many finer layers, and `speed` how fast they change.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `scale`: 3.0 0.1..40.0. How many hills fit across; more is finer.
- `speed`: 0.1 0.0..2.0 /s. How fast the hills change.
- `octaves`: 1 1..6. Finer detail on top of the hills.
- `kind`: 'gradient' of gradient, value. Gradient noise is smoother; value noise is blockier.

    noise(3, 0.1)
    noise(2, 0.07, octaves=3).palette("aurora")

### `osc` — Oscillator

Stripes along one axis that travel across the room.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `freq`: 4.0 0.5..32.0. More stripes across the room.
- `sync`: 0.1 -1.0..1.0 Hz. How fast the stripes travel: crests a second past each point; below 0 they run back.
- `offset`: 0.0 0.0..1.0. Moves the stripes along by part of a crest.
- `axis`: 'x' of u, x, y, z. Which way the stripes run; u runs along a strip from its first light.
- `shape`: 'sine' of sine, saw. Sine rises and falls; saw climbs from 0 to 1, then jumps back to 0, so a palette wraps round.

    osc(8, 0.1)
    osc(3, 0.15, axis="u").palette("ocean")
    osc(0.8, 0.1, shape="saw").palette("candy", cycle=0.03)

### `particles` — Particles

Sparks that drift, rise and fade: up to 256 at once, each born where the emit choice says, setting off in a random direction, falling or rising, drifting on a breeze and fading in and out. `rate` are born a second, each sets off at `speed`, falls or rises under `gravity`, drifts on a curl-noise breeze (`swirl`), and fades over its `life`. Sparks fly fast from the center and fall; snow drifts down from the top; fireflies hang anywhere and wander.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `rate`: 20.0 0.0..120.0 /s. More sparks at once.
- `life`: 2.0 0.1..10.0 s. Seconds each lives, fading in and out.
- `speed`: 0.2 0.0..2.0 /s. How fast each spark sets off, in a random direction.
- `gravity`: 0.0 -2.0..2.0 /s². Pull upward: above 0 up, below 0 down.
- `swirl`: 0.0 0.0..1.0 /s. How fast the breeze they drift on swirls.
- `emit`: 'centre' of centre, bottom, top, anywhere. Where they are born: the center, along the bottom or top edge, or anywhere.
- `size`: 0.06 0.02..0.3. Radius of each particle's glow.

    particles(30, 1.2, 0.8, -1, emit="centre")
    particles(12, 6, 0.05, -0.1, 0.3, "top").palette("ice")
    particles(8, 3, 0, 0, 0.3, "anywhere", 0.05).palette("forest")

### `prev` — Prev

The layer's own last frame: with a fade or a color op after it, a trail (feedback with no warp).

Reads none; gives rgb. Dimensions: 1, 2, 3.

    lissajous(heads=1).blend(prev(), "max", 0.9)

### `quasicrystal` — Quasicrystal

Patterns with many-fold symmetry that never repeat: waves from several evenly turned directions, summed. `waves` sets how many directions.

Reads none; gives scalar. Dimensions: 2, 3. a strip shows only swelling stripes; use oscillator

- `waves`: 7 3..12. Directions of the waves; 5 and 7 never repeat.
- `scale`: 8.0 1.0..40.0. Higher: more, smaller waves.
- `speed`: 0.1 -1.0..1.0 Hz. How fast the waves move.
- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    quasicrystal(7, 7, 0.12)
    quasicrystal(5, 4.5).palette("synthwave")

### `reaction` — Reaction

Coral, dividing cells, spots or a maze that grow across the lights from a few seeds: two chemicals that feed, react and spread. Brighter is more of the second chemical.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `kind`: 'coral' of coral, mitosis, spots, maze. Coral, mitosis, spots or maze.
- `size`: 0.4 0.15..0.8. How big its shapes grow.
- `speed`: 60.0 5.0..240.0 /s. How fast it grows.
- `seeds`: 0.2 0.0..4.0 /s. New seeds a second at random points.

    reaction("coral", 0.4, 120, 1)
    reaction("maze", speed=90).contrast(1.6).palette("forest")

### `ripple` — Ripple

A pond across the lights: drops fall at random points, and rings spread from each along the points, bounce off the ends and die away. Still water is 0.5; a crest is brighter, a trough darker. A drop lifts its point as much as it lowers the rest, and the whole pond settles at `damping`, so the water stays level however long it runs.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `speed`: 0.5 0.05..2.0 /s. How fast the rings spread.
- `damping`: 0.5 0.1..5.0 /s. How quickly ripples fade.
- `drops`: 0.5 0.0..4.0 /s. How often a drop falls, each at a random point.
- `size`: 0.08 0.02..0.3. Bigger splashes.

    ripple(0.6, 0.8, 4, 0.1)
    ripple(drops=1).palette("ice")

### `shape` — Shape

A filled circle or regular polygon at the room's center: a sphere in a volume, a segment on a strip.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `sides`: 0 0..12. Corners; fewer than 3 draws a circle.
- `radius`: 0.3 0.0..1.0. Size from the center to the rim or a corner.
- `smooth`: 0.05 0.0..0.5. Softness of the edge.
- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    shape(5, 0.3)
    shape(0, 0.2, 0.1).palette("ember")

### `voronoi` — Voronoi

Cells around scattered points: bright at each point fading to its cell's rim, or bright rims between the cells. `edge` draws the rims.

Reads none; gives scalar. Dimensions: 1, 2, 3.

- `scale`: 5.0 1.0..32.0. Cells across the room; more is smaller.
- `speed`: 0.2 0.0..2.0 /s. How fast the cells move.
- `edge`: 0.0 0.0..1.0. 0 lights each cell's middle; 1 lights the borders between cells.

    voronoi(4, 0.15, edge=0.8)
    voronoi(6).palette("forest")

## Coord ops

### `dither` — Dither

Breaks hard edges into a sparkle: each light reads the pattern a little off its own spot, and jumps to a new spot now and then, on a clock of its own. Where the pattern is flat nothing changes; at an edge a light twinkles between the colors on each side, as often as the edge covers its spot, so a hard edge reads as glitter and an edge that moves shimmers across the lights rather than stepping from one to the next. `amount` sets how far a light reaches, in the spacing of the lights along each axis, and `rate` how often each light jumps.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 0.5 0.0..3.0 ×. How far each light reaches: 0.5 is halfway to its neighbours; more sparkles wider.
- `rate`: 2.0 0.0..6.0 /s. Jumps a second for each light: more twinkles faster; above about 2 an edge can flash.

    osc(5, axis="y").polar().kaleid(5).dither(1).palette("synthwave")
    voronoi(4, edge=0.8).dither(1, 1.5).palette("aurora")

### `kaleid` — Kaleidoscope

Folds a pattern into mirrored wedges about the center, as a kaleidoscope does. `sides` sets how many.

Reads `in` (same); gives same. Dimensions: 2, 3. a strip has no plane to fold; use mirror along the strip

- `sides`: 5 1..24. More mirror slices.
- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    osc(8).kaleid(5)
    voronoi(4, edge=0.8).kaleid(6).palette("synthwave")

### `mirror` — Mirror

Mirrors one side of a pattern onto the other: folded along one axis, at a point you set. `centre` sets where.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `axis`: 'x' of u, x, y, z. The direction it folds across; u folds a strip along its wiring.
- `centre`: 0.5 0.0..1.0. Where the fold sits, from the low end (0) to the high end (1).

    osc(3, 0.15, axis="u").mirror("u")
    noise(4).mirror().palette("ocean")

### `polar` — Polar

Bends a pattern into rings and spokes round the center: stripes along x become rings and stripes along y become spokes. In polar coordinates, the plane's first axis becomes the radius and its second the turn.

Reads `in` (same); gives same. Dimensions: 2, 3. a strip has no plane to wrap round; use mirror along the strip

- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    osc(6).polar()
    osc(5, axis="y").polar().palette("aurora")

### `repeat` — Repeat

Tiles a pattern across the room, each tile showing the whole of it, along one axis or all of them. `count` sets how many tiles.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `count`: 2 1..16. Tiles along the axis.
- `axis`: 'all' of all, u, x, y, z. The axis it tiles along, or all of them.

    noise(2).repeat(3)
    shape(0, 0.3).repeat(3)
    osc(2, axis="u").repeat(4, "u").palette("candy")

### `rotate` — Rotate

Turns a pattern about the center, to an angle and on at a speed. `angle` sets how far, `speed` how fast it keeps turning.

Reads `in` (same); gives same. Dimensions: 2, 3. a strip has no plane to turn in; use scale or mirror along the strip

- `angle`: 0.0 0.0..360.0 °. Where it starts, before speed turns it on.
- `speed`: 0.0 -90.0..90.0 °/s. Which way and how fast it keeps turning.
- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    osc(3).rotate(30)
    quasicrystal(7).rotate(speed=2).palette("ocean")

### `scale` — Scale

Zooms a pattern about the center: above 1 enlarges it.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 1.0 0.1..10.0 ×. Zoom: above 1 enlarges, below 1 shrinks.
- `axis`: 'all' of all, u, x, y, z. The axis it zooms along, or all of them.

    noise(3).scale(2)
    noise(3).scale(0.5, "x").palette("ember")

### `tunnel` — Tunnel

Rushes a pattern out of the center, as down a tunnel. It reads depth (1 / distance from the center) and turn, moving at `speed`.

Reads `in` (same); gives same. Dimensions: 2, 3. a strip has no plane to look down; use scale along the strip (u)

- `depth`: 0.3 0.05..2.0. How deep the tunnel looks.
- `speed`: 0.2 -2.0..2.0 /s. How fast it flies down the tunnel.
- `core`: 0.08 0.0..0.5. A still circle at the center, so the middle does not flicker.
- `plane`: 'auto' of auto, xy, xz, yz. Which two axes it works across; auto picks the room's.

    osc(4).tunnel(0.35, 0.25)
    voronoi(3, 0.1, edge=0.6).tunnel(0.35, 0.25).palette("aurora")

### `twist` — Twist

Twists a volume into a corkscrew: each slice turned a little more than the one before it. Each turns about `axis` by `amount` degrees per unit along it.

Reads `in` (same); gives same. Dimensions: 3. twist turns the slices of a volume; on a panel use rotate, on a strip scale

- `amount`: 0.0 -360.0..360.0 °/unit. Degrees of turn per unit along the axis.
- `axis`: 'z' of x, y, z. The axis the slices turn about.

    osc(3).twist(90)
    metaballs(5).twist(90, "z").palette("ember")

## Color ops

### `contrast` — Contrast

Pushes colors away from the middle gray for more punch, or toward it for less.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 1.0 0.0..4.0. Above 1 sharpens, below 1 flattens toward gray.

    noise(9).contrast(1.6)
    voronoi(5).contrast(2).palette("forest")

### `hue` — Hue

Turns every color's hue round the color wheel, keeping how light and how strong it is. `amount` sets how far, in degrees. A color turned past what LEDs show is clipped for red, green and blue separately, which moves its hue a little; a palette's `shift` turns its colors without that.

Reads `in` (rgb); gives rgb. Dimensions: 1, 2, 3.

- `amount`: 0.0 0.0..360.0 °. Degrees the hues turn.

    noise(2).palette("ember").hue(120)
    below().hue(90)

### `palette` — Palette

Colors a pattern through a gradient: its lowest values take the first color and its highest the last. `shift` turns every color's hue, in steps of 0.5°, and a color it turns past what LEDs show gets less strong, never a different hue; `cycle` slides the colors along the field, wrapping round.

Reads `in` (scalar); gives rgb. Dimensions: 1, 2, 3.

- `palette`: palette, default ember. Press a dot to edit its color; the left end colors the low parts, the right the high.
- `shift`: 0.0 0.0..360.0 °. Turns every color's hue.
- `cycle`: 0.0 -1.0..1.0 /s. Slides the colors along, round and round; give both ends one color for no seam.

    noise(3).palette("ocean")
    osc(4, 0.1).palette("aurora", shift=40, cycle=0.03)

### `posterize` — Posterize

Bands instead of a smooth ramp: values rounded down to a few steps from 0 to 1. `levels` sets how many. On a fast-changing field the bands flicker.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `levels`: 4 2..16. Steps from dark to bright.

    osc(2).posterize(4)
    noise(2, 0.05).posterize(5).palette("synthwave")

## Combine ops

### `add` — Add

Adds two patterns, light on light. `b` goes onto `a`.

Reads `a` (same), `b` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 1.0 0.0..1.0. How much of the second pattern shows over the first.

    osc(4).add(noise(3), 0.5)
    shape(0, 0.2).add(osc(10), 0.3).palette("ember")

### `blend` — Blend

Lays one pattern onto another, mixed as layers mix: the second onto the first. `b` goes onto `a`.

Reads `a` (same), `b` (same); gives same. Dimensions: 1, 2, 3.

- `mode`: 'normal' of normal, add, screen, multiply, max, min, difference, subtract, stencil, highlight. How the second pattern mixes into the first.
- `amount`: 1.0 0.0..1.0. How much of the second pattern shows over the first.

    noise(2).palette("ember").blend(osc(3).posterize(2), "multiply", 0.6)

### `diff` — Difference

Bright where two patterns disagree. It is the difference of `a` and `b`, for red, green and blue separately.

Reads `a` (same), `b` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 1.0 0.0..1.0. How much of the second pattern shows over the first.

    osc(4).diff(osc(5, -0.1))
    noise(3).diff(voronoi(4)).palette("synthwave")

### `mult` — Multiply

One pattern masks another: dark where the mask is dark. `a` is multiplied by `b`.

Reads `a` (same), `b` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 1.0 0.0..1.0. How much of the second pattern shows over the first.

    osc(4).mult(shape(0, 0.4))
    noise(3).palette("ember").mult(osc(2, axis="y"))

## Modulate ops

### `modulate` — Ripple

Ripples one pattern with another: each point moves as far as the second says there. Each point of `in` moves by `amount` times `mod`. A color's red, green and blue move x, y and z.

Reads `in` (same), `mod` (same); gives same. Dimensions: 1, 2, 3.

- `amount`: 0.1 0.0..1.0. How strongly the second pattern warps the first.

    osc(8).modulate(noise(3), 0.2)
    osc(3, axis="u").modulate(noise(2, 0.07), 0.12).palette("ember")

## State ops

### `diffuse` — Diffuse

Heat that bleeds from light to light: what it reads glows, spreads to the lights next to it (never across a gap with none) and fades.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `bleed`: 6.0 0.0..40.0 /s. How fast the glow spreads to the next points.
- `decay`: 2.0 0.05..20.0 s. How long the glow lasts.

    lissajous(3, 4, 5, 0.07, 3, 0.05).diffuse(6, 2.5)
    shape(0, 0.1).diffuse(20, 1).palette("ice")

### `feedback` — Feedback

Trails that stream and fade: each frame what it showed moves (zooms, spins, swirls, drifts up, wobbles) and fades, and keeps the brighter of that and what it reads. On a strip it runs along the strip; spin and swirl turn a panel's plane, or a volume about its up axis.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `decay`: 1.0 0.05..10.0 s. How long a trail lasts.
- `zoom`: 1.0 0.25..4.0 ×/s. How much it grows a second: above 1 it streams out of the center, below 1 into it.
- `spin`: 0.0 -180.0..180.0 °/s. Which way and how fast it turns about the center; nothing on a strip.
- `swirl`: 0.0 -360.0..360.0 °/s. Degrees a second the middle turns, falling off outward: a whirlpool; nothing on a strip.
- `drift`: 0.0 -1.0..1.0 /s. How fast it flows upward (below 0, down).
- `warp`: 0.0 0.0..1.0. How much a slow noise wobbles the flow.

    lissajous(heads=2).feedback(1.5, 1.4, 30, 40, 0.1, 0.3)
    shape(0, 0.05).feedback(0.7, 2.2).palette("ember")
    voronoi(4, 0.15, edge=0.8).kaleid(6).palette("synthwave").feedback(0.9, 0.7, 20, warp=0.15)
    below().feedback(0.6, 0.8, -12)

### `trails` — Trails

A trail behind anything that moves: each light keeps the brighter of the pattern and its own fading past. Per point, so cheap on any map; it has no value between the points, so no coord op may sit above it.

Reads `in` (same); gives same. Dimensions: 1, 2, 3.

- `tail`: 0.5 0.02..10.0 s. How long a trail lasts.

    lissajous(heads=1, width=0.15).trails(0.8)
    osc(2, 0.4, axis="u").posterize(4).trails(1.2).palette("aurora")

## Signal ops

### `band` — Audio follower

How loud a part of the sound is, 0 to 1: the volume, or the bass, mid or high bands, times `gain`. It rises with time constant `attack` and falls with `release`, as an audio-reactive light smooths its levels (about 50 ms up and 200 ms down).

Reads none; gives signal. Dimensions: 1, 2, 3.

- `band`: 'bass' of volume, bass, mid, high. The part of the sound it follows.
- `gain`: 1.0 0.0..4.0 ×. Turns the level up; it never goes past full.
- `attack`: 0.05 0.0..2.0 s. How soon it follows the sound up.
- `release`: 0.2 0.0..5.0 s. How slowly it lets go as the sound falls.

    look(layer("base", shape(0, 0.2).palette("ember")), routes=[band("bass").to("layers.base.shape.radius", depth=0.3)])

### `beat` — Beat

The beat, 0 to 1: a `pulse` on for the first `width` of each beat, the beat's `phase` rising from 0 to 1, or a `fall` from 1 at each beat to 0 at the next.

Reads none; gives signal. Dimensions: 1, 2, 3.

- `shape`: 'pulse' of pulse, phase, fall. Pulse flashes on each beat; phase climbs through the beat; fall drops from each beat.
- `width`: 0.25 0.05..0.95. How much of each beat the pulse is on.

    look(layer("base", osc(6).palette("ocean")), routes=[beat("fall").to("layers.base.osc.offset", depth=0.25)])

### `env` — Envelope

An envelope its `gate` signal plays, 0 to 1: when the gate turns on (0.5 or more) it rises to 1 over `attack`, falls to `sustain` over `decay` and holds there; when the gate turns off it falls to 0 over `release`. On the beat: `beat().env(...)`.

Reads `gate` (signal); gives signal. Dimensions: 1, 2, 3.

- `attack`: 0.01 0.0..5.0 s. Seconds to rise from 0 to 1.
- `decay`: 0.3 0.0..5.0 s. Seconds to fall from 1 to the sustain level.
- `sustain`: 0.0 0.0..1.0. The level it holds while the pulse lasts.
- `release`: 0.3 0.0..10.0 s. Seconds to fall to nothing after the pulse ends.

    look(layer("base", shape(0, 0.3).palette("ember")), routes=[beat().env(0.01, 0.3).to("layers.base.shape.radius", depth=0.2)])

### `knob` — Macro

A value a person sets, 0 to 1. With several routes it is a macro: at 0 each knob it drives sits at its own value, and at 1 each has moved by its route's depth.

Reads none; gives signal. Dimensions: 1, 2, 3.

- `value`: 0.0 0.0..1.0. A knob of the look's own: turn it to move what it drives.

    look(layer("base", osc(8).kaleid(5).palette("ember")), routes=[(macro_ := knob(0.5).id("macro")).to("layers.base.osc.freq", depth=8), macro_.to("layers.base.kaleid.sides", depth=6)])

### `lfo` — LFO

A wave that swings from -1 to 1 `rate` times a second: a sine, a triangle, a square, a saw that falls or a ramp that rises. Each starts at 0 rising, but the square and the saw, which start at the top, and the ramp, at the bottom.

Reads none; gives signal. Dimensions: 1, 2, 3.

- `rate`: 0.25 0.0..10.0 Hz. Higher: what it moves swings faster.
- `shape`: 'sine' of sine, triangle, square, saw, ramp. Sine glides; square jumps; saw and ramp climb or fall, then jump back.
- `offset`: 0.0 0.0..1.0. Moves the wave along by part of a cycle.

    look(layer("base", noise(3).palette("ember", shift=lfo(0.05))))
    look(layer("base", osc(8).palette("ocean")), routes=[lfo(0.25, "triangle").to("layers.base.osc.freq", depth=4)])

### `smooth` — Smooth

Another signal, smoothed: it follows its input with a lag of `time` seconds (a one-pole filter), so a jump becomes a glide. Gives what its input gives.

Reads `in` (signal); gives signal. Dimensions: 1, 2, 3.

- `time`: 0.2 0.0..10.0 s. How long it takes to catch up.

    look(layer("base", osc(8).palette("ember")), routes=[band("bass").smooth(0.5).to("layers.base.palette.shift", depth=90)])

### `walk` — Random

A smooth random wander from -1 to 1: it eases to a new random level `rate` times a second. The look's seed and the signal's id choose the levels, so a look wanders the same way on every run.

Reads none; gives signal. Dimensions: 1, 2, 3.

- `rate`: 0.25 0.0..4.0 Hz. How often it wanders somewhere new.

    look(layer("base", voronoi(5).palette("forest")), routes=[walk(0.3).to("layers.base.palette.shift", depth=90)])

## Blend modes

- `normal`: Shows the layer over what is below
- `add`: Adds the layer's light to what is below
- `screen`: Adds light without washing out to white
- `multiply`: Darkens what is below where the layer is dark
- `max`: The brighter of the two, for red, green and blue separately
- `min`: The darker of the two, for red, green and blue separately
- `difference`: Bright where the two differ
- `subtract`: Takes the layer's light away from what is below
- `stencil`: Shows the layer where it has any color, what is below where it is black
- `highlight`: Lights only where what is below is already lit

## Palettes

- `ember`
- `ocean`
- `aurora`
- `synthwave`
- `forest`
- `ice`
- `candy`
- `mono`

## Param kinds

- `float`: A real number from `lo` to `hi`
- `int`: A whole number from `lo` to `hi`
- `bool`: On or off
- `choice`: One of a fixed set of keys
- `color`: A color
- `palette`: A gradient
