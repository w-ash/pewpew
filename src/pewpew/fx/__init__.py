"""Effects: layered, composable effect programs over a mapping's points
(ADR-022).

- `graph`: the program values (nodes, graphs, programs).
- `types`, `op`: what flows between nodes, and `Op`, the base of every op
  and its registry; `ops` holds the built-in ops.
- `expr`: the fluent builder (`osc(8).kaleid(5).palette("ember")`).
- `compile`: `check`, the one judge of a program, and its closures.
- `host`: `ProgramPattern`, a program run as a pattern.
- `codec`: the one JSON form of programs and looks; `catalog`: the one
  description of every op; `cli`: the `fx` command group.
- `blend`: the blend modes layers and combine ops mix with; `prims`: the
  pure NumPy primitives (noise, sampling, coordinate ops, distance fields,
  neighbour graphs) the ops call; `field`: the grid over the map that a
  stateful op keeps its state on.

A program as a pattern class:

    from pewpew.fx.expr import noise, osc
    from pewpew.fx.host import ProgramPattern

    class Tide(ProgramPattern):
        program = osc(8, 0.1).kaleid(5).modulate(noise(3, 0.1), 0.2).palette("ember")
"""
