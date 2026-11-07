---
name: authoring-looks
description: Designs, checks, renders and refines pewpew looks (layered LED effects, looks file version 4) through the pewpew MCP tools or the `python -m pewpew fx` verbs, reading metrics before pictures and judging versions pairwise. Use when asked to make, change, tune, fix or compare a look, an effect program or an example under examples/, or to judge which of two looks reads better on LEDs.
---

# Authoring looks

A look is a stack of layers, bottom first. Each layer runs one gallery
pattern or an effect program (a small graph of ops), mixes onto the
layers below by `opacity`, `blend` and `enabled`, and every knob has an
address such as `layers.base.comet.speed`. The format, with examples, is
in `docs/authoring.md` §9 (layers) and §10 (effect programs); the MCP
server serves each section alone, as `pewpew://docs/authoring/9` and
`pewpew://docs/authoring/10`.

Never write from memory what the catalog says. Op names, args, ranges,
defaults, palettes and blend modes change as ops are added: ask
`catalog_search` every time.

## Tools

Use the `pewpew` MCP server when it is connected; otherwise use the same
verbs on the command line. Each pair gives the same JSON.

| Step | MCP tool | Command line |
|---|---|---|
| Find parts | `catalog_search(query, kind, response_format)` | `python -m pewpew fx catalog --query Q --kind K --json`; `fx show NAME --json` |
| Check | `look_check(look, explain)` | `python -m pewpew fx check FILE --json`; `fx explain FILE` |
| Render and measure | `look_render(look, map, seconds, fps, seed)` | `python -m pewpew fx render FILE --map M --seconds S --out sheet.png --json` |
| Compare | `look_compare(a, b, map)` | `python -m pewpew fx compare A B --out ab.png --json` |
| Explore | `look_vary(look?, seed, n, strength, keep, map)` | `python -m pewpew fx vary [FILE] --seed S --n N --keep PATH --out rows.png --json` |
| Gate | (none) | `python -m pewpew verify looks FILE` |

Every one of these is tier 0: it reads files and the render cache and
sends nothing to a board. Writing to a running engine (`engine_apply`,
`engine_set`, `push`) is tier 1: only in an attended bench session, dry
run first, and only when the person asked for it.

## The loop

1. **Find the parts.** Pick words from the brief and search:
   `catalog_search(query="noise palette")`, `catalog_search(kind="coord")`.
   Concise results list names and first sentences. Before you use a part,
   read its whole record (`response_format="detailed"`, or
   `pewpew://catalog/op/kaleid`): its args, their ranges and defaults, the
   map dimensions it supports, and its examples as builder chains and as
   JSON. An op's example JSON is a layer's program (`out` and `nodes`):
   put it in a look as `{"layers": [{"id": "base", ...the program}]}`. A
   signal op's example is a whole look. Copy an example's JSON as a
   starting point rather than inventing arg names.

2. **Write the look.** Start from an example (`pewpew://looks/{name}`,
   `examples/*.look.json`), a catalog example, or a made look:
   `look_vary(n=4, map=...)` makes looks from nothing, and
   `look_vary(look, strength=0.3, keep=[...])` makes looks like one,
   holding the addresses you name. Each candidate already passes the
   content gate on that map; read its metrics, view the numbered sheet,
   and take the best as the start. Keep it small: one layer
   that works beats three that fight. Name layers and nodes for what they
   do (`swell`, `tint`), since ids appear in every knob address and never
   change. Patterns go by name, never by file path.
   Patterns that suit the shape are in `references/patterns.md`.

3. **Check it.** `look_check(look)`. A refusal lists each problem with a
   code, the path, the aura's own words, a did-you-mean and a `fix:`
   line; apply every fix and check again. With `explain=true` a look that
   checks comes back described knob by knob: read it to confirm the look
   says what you meant.

4. **Render it and read the numbers first.** `look_render(look,
   map=...)`. Choose the map the look is for: `line:64` for a strip,
   `grid:16x16` for a panel, `lattice:8` for a volume, or a room map
   file; `auto` picks the bottom pattern's own geometry. Render at least
   1 s (flashing is counted per second); 2 to 4 s at 30 fps is the norm.
   Read `warnings` and `metrics` before the image (`references/metrics.md`):
   - `flash_rate_max` above 3 fails the WCAG gate. Fix it before anything else.
   - `black_fraction` near 1 or `mean_luma` near 0: the look is dark.
   - `clip_fraction` high over added layers: it saturates; lower opacity, use
     `screen`, not `add`. One bright layer alone reads high too.
   - `frozen_fraction` near 1 or `motion_energy` near 0: nothing moves.
   - `palette_spread` and `hue_clusters`: how much colour variety there is.
   Then look at the sheet image to judge form, rhythm and colour.

5. **Iterate one change at a time.** Change one knob or one node, render
   again, and compare against the render before:
   `look_compare(a=<last handle>, b=<new look>)`. B renders exactly as A
   did (map, seconds, fps, seed), so the difference is your change alone.
   `look_diff` names each knob that moved; the metric deltas say what it
   did. Keep the handle of the best version so far as the baseline.

6. **Compare against the baseline.** When the brief is met, compare the
   final look against the baseline the person gave (or the example you
   started from) and against the last version you rejected.

7. **Hand off to the critic.** For a judgment of taste, give the
   `look-critic` subagent the two handles and the brief. It compares in
   both orders and returns a structured verdict. A verdict is evidence,
   not a gate: report it with the metrics, and let the person decide.

8. **Gate before you commit an example.** A look under `examples/` must
   pass `python -m pewpew verify looks examples/`: it checks, no layer
   raises, it flashes at most 3 times a second, it is not all black, and
   every knob changes the picture. A knob that changes nothing is a bug in
   the look: remove the node or give the knob something to do.

## Errors and how to recover

- A refused look: apply each `fix:` line, then call the same tool again.
  `wrong-dims` means an op needs more axes than the map has (`kaleid` on a
  strip); the reason says what to use instead.
- `handle ... expired`: the render cache dropped it. Render the same look
  with the same map, seconds, fps and seed; that gives the same handle.
- `A and B must be rendered alike`: give both sides the same `map`, or
  compare two handles rendered on the same map.
- A wrong argument (`kind="cord"`): the error text ends with the corrected
  call.

## Done means

- The look checks and renders without warnings on the map it is for.
- You read the metrics and the sheet, and you can say what each layer does.
- You compared it against a baseline and say what changed and why.
- An example under `examples/` passes `verify looks`.
