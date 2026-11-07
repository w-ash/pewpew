"""The built-in ops, registered by importing their modules, and `OPS`, the
registry by op name once they are in.

- `source`: osc, noise, voronoi, shape, quasicrystal, metaballs,
  lissajous, below, prev
- `coord`: rotate, scale, kaleid, polar, mirror, twist, tunnel, repeat
- `color`: palette, hue, contrast, posterize
- `combine`: add, mult, diff, blend, and modulate
- `signal`: lfo, env, band, beat, walk, knob, smooth: one number a
  frame, which a look's routes add to its knobs
- `state`: feedback, trails
- `sims`: diffuse, ripple, reaction, life, on the map's own points
- `swarm`: particles, attractor
"""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType

from pewpew.fx.op import REGISTRY
from pewpew.fx.ops import color, combine, coord, signal, sims, source, state, swarm

OPS = MappingProxyType(REGISTRY)


def labels(ops: Iterable[str]) -> dict[str, str]:
    """Each of `ops` by its label (`kaleid` by "Kaleidoscope", `mult` by
    "Multiply"): the word an author may type first, for a did-you-mean
    (pewpew.errors.did_you_mean)."""
    return {OPS[op].label: op for op in ops}


__all__ = ["OPS", "color", "combine", "coord", "labels", "signal", "sims", "source", "state", "swarm"]
