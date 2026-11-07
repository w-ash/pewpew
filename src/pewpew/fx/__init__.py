"""Effects: layered, composable effect programs over a mapping's points
(ADR-022).

- `graph`: the program values (nodes, graphs, programs).
- `types`, `op`: what flows between nodes, and `Op`, the base of every op
  and its registry; `ops` holds the built-in ops.
- `expr`: the fluent builder (`osc(8).kaleid(5).palette("ember")`).
- `compile`: `check`, the one judge of a program, and its closures.
- `buffers`, `bound_program`: a program bound to a map, with the state
  its ops keep, which a `pewpew.render.Renderer` runs.
- `codec`: the one JSON form of programs and looks; `catalog`: the one
  description of every op; `cli`: the `fx` command group.
- `blend`: the blend modes layers and combine ops mix with; `prims`: the
  pure NumPy primitives (noise, sampling, coordinate ops, distance fields,
  neighbour graphs) the ops call; `field`: the grid over the map that a
  stateful op keeps its state on.
"""
