"""Variations: looks made from a seed, or made like a look, each rendered
for an agent to choose from (ADR-023 `vary`).

`vary(None, seed, n)` makes `n` looks from nothing
(pewpew.fx.surprise.generate); `vary(look, seed, n, strength, keep)`
makes `n` looks like `look` (`mutate`), holding the addresses in `keep`.
Candidate `i` comes from its own seed, `surprise.sub_seed(seed, i)`, so
a set of `n` is the first `n` of a larger set, and `generate` or `mutate`
makes one candidate again from its seed alone. Each is made for the map
`map_spec` names (`auto`: a look's bottom pattern's own map, or the 16x16
grid a program runs on), judged there (pewpew.fx.surprise), then
rendered as `render` renders it, its frames cached under its handle, so
`sheet`, `compare` and `rows` take it. The same arguments give the same
looks and handles.

Each look passes the content gate. The taste gates are a preference: a
made look passes them when one of its tries does, else it fails the
fewest, so a candidate carries the taste gates its render fails
(`surprise.taste`). A seed none of whose changes of the look passes the
content gate gives no candidate.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pewpew.compose import Look
from pewpew.fx import surprise  # read at call time: pewpew.fx.surprise renders through this package
from pewpew.fx.host import ProgramPattern
from pewpew.lab.check import LookDoc, ready
from pewpew.lab.geometry import AUTO, auto_geometry, parse_geometry
from pewpew.lab.handles import Cache
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, render, take, where
from pewpew.load import Catalog
from pewpew.metrics import Metrics, measure
from pewpew.result import Result
from pewpew.sheet import MAX_ROWS

MAX_VARIANTS = MAX_ROWS  # every candidate fits in one sheet of rows (`rows`)


@dataclass(frozen=True, slots=True)
class Candidate(Result):
    """One look `vary` made: the seed that made it, the look (looks-file
    form, every knob written out), its render (handle, metrics and
    warnings), and the taste gates the render fails (module docstring)."""

    seed: int
    look: dict[str, Any]
    handle: str
    metrics: Metrics
    warnings: tuple[str, ...] = ()
    taste: tuple[str, ...] = ()


@dataclass(frozen=True)
class Variations(Result):
    """The looks `vary` made from `seed`: like a look at `strength`, or from
    nothing (`strength` None), with the addresses it held, each a
    `Candidate`."""

    seed: int
    strength: float | None
    keep: tuple[str, ...]
    candidates: tuple[Candidate, ...]


def vary(
    look: LookDoc | None = None,
    seed: int = 0,
    n: int = 4,
    strength: float | None = None,
    keep: Iterable[str] = (),
    map_spec: str = AUTO,
    *,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    audio: bool = False,
    name: str | None = None,
    pattern_dir: Path | None = None,
    catalog: Catalog | None = None,
    cache: Cache | None = None,
) -> Variations:
    """`n` looks (1 to MAX_VARIANTS) made from `seed` (module docstring):
    from nothing when `look` is None, else like `look` (or the look `name`
    of a looks file) at `strength` (None: mutate's own default), holding
    `keep`; each rendered on the map `map_spec` names for `seconds` at
    `fps`. `audio` lets a made look follow the sound. A look's patterns
    resolve as `check_look` resolves them, from `pattern_dir` or through
    `catalog`. Raises Refused for a look with problems or a keep address
    that names nothing in it, NoLook when nothing made passes the content
    gate (a candidate whose seed makes nothing that does is left out), and
    ValueError for a bad n, seed, strength, map spec, seconds or fps."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_VARIANTS:
        raise ValueError(f"n is a whole number from 1 to {MAX_VARIANTS}, got {n!r}")
    surprise.require_seed(seed)
    strength = surprise.require_strength(surprise.STRENGTH if strength is None else strength)
    seeds = [surprise.sub_seed(seed, i) for i in range(n)]
    held = tuple(dict.fromkeys(keep))
    if look is None:
        if held:
            raise ValueError("keep holds addresses of a look; give the look to vary")
        geometry = auto_geometry(ProgramPattern) if map_spec == AUTO else parse_geometry(map_spec)
        made: list[Look | None] = [
            surprise.generate(s, geometry.mapping, grouping=geometry.grouping, audio=audio) for s in seeds
        ]
    else:
        staged = ready(look, name=name, pattern_dir=pattern_dir, catalog=catalog)
        geometry = where(map_spec, staged)
        made = []
        for s in seeds:
            try:
                made.append(surprise.mutate(
                    staged.look, s, geometry.mapping, strength=strength, keep=held, grouping=geometry.grouping,
                    audio=audio, pattern_dir=pattern_dir, catalog=catalog,
                ))
            except surprise.NoLook:
                made.append(None)
        if all(item is None for item in made):
            raise surprise.NoLook(f"nothing made like the look from seed {seed} passed the content gate; "
                                  "try another seed, or keep less")
    cache = cache if cache is not None else Cache()
    candidates = []
    for s, item in zip(seeds, made):
        if item is None:
            continue
        rendered = render(item, geometry, seconds, fps, pattern_dir=pattern_dir, catalog=catalog, cache=cache)
        assert rendered.spec is not None  # a fresh render carries its spec
        frames = take(rendered, cache).frames
        failed = surprise.taste(rendered.metrics, measure(frames[-round(fps):], fps), surprise.wants_colour(item))
        candidates.append(
            Candidate(s, rendered.spec.look, rendered.handle, rendered.metrics, rendered.warnings, failed)
        )
    return Variations(seed, None if look is None else strength, held, tuple(candidates))

