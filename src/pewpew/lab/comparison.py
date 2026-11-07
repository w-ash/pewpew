"""Comparing two renders, A and B: what differs between their looks, and
how far their frames differ.

Each side is a render, its handle, or a look. A look renders as the other
side did when that side is a render: on its map spec, for its seconds and
fps, with its seed. Two looks both render with the arguments given. So a
render's spec always gives its handle again, and two renders whose maps
differ do not compare. The look diff names each knob by its address (ADR-006), a
layer's or signal's node by its own (its op and what it reads), plus the
look's own fields, its layer order, its front knobs, and each route by
`routes[<source> -> <path>]`, its value the route's depth.

The frame numbers are diagnostics, never gates, taken from the frames as
a sink shows them (NaN to 0, +inf to 1, clipped to [0, 1]), as the
metrics are: RMS and the largest difference of linear light, the first
frame that differs at all, each metric of B less A's, and the 95th
percentile of the OKLab colour difference (ΔE).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from functools import partial
from pathlib import Path
from typing import Any, TypeGuard, cast

import numpy as np

from pewpew.color import oklab
from pewpew.compose import MIX, layer_address
from pewpew.compose.controls import signal_address
from pewpew.lab.check import LookDoc
from pewpew.lab.handles import Cache, is_handle
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, Rendered, Take, render, take
from pewpew.lab.views import Picture, picture
from pewpew.mapping import DEFAULT_MAP
from pewpew.metrics import measure, rms
from pewpew.result import Result
from pewpew.sheet import compare_sheet as draw_pair
from pewpew.sinks.sink import sanitize

# One side of a comparison: a render, its handle, or a look.
Side = Rendered | LookDoc


@dataclass(frozen=True, slots=True)
class Change(Result):
    """One knob or field whose value differs: its path, its value in A and
    its value in B (None where that side has none)."""

    path: str
    a: Any
    b: Any


@dataclass(frozen=True)
class Comparison(Result):
    """How render B differs from render A (module docstring)."""

    a: str
    b: str
    look_diff: tuple[Change, ...]
    rms: float
    max_abs: float
    first_divergent_frame: int | None
    metric_deltas: dict[str, float]
    delta_e_p95: float


def compare(
    a: Side,
    b: Side,
    *,
    map_spec: str = DEFAULT_MAP,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    seed: int = 0,
    name: str | None = None,
    cache: Cache | None = None,
) -> Comparison:
    """B against A (module docstring). The render arguments and `name`,
    the look of a looks file, apply to a side that is a look. Raises Refused, Expired, and
    ValueError for two renders that are not alike."""
    first, second = _pair(a, b, _Looks(map_spec, seconds, fps, seed, name), cache)
    ma, mb = measure(first.frames, first.spec.fps), measure(second.frames, second.spec.fps)
    fa, fb = sanitize(first.frames), sanitize(second.frames)
    divergent = np.flatnonzero((fa != fb).any(axis=(1, 2)))
    delta_e = np.linalg.norm(oklab(fa) - oklab(fb), axis=-1)
    return Comparison(
        a=first.handle,
        b=second.handle,
        look_diff=look_diff(first.spec.look, second.spec.look),
        rms=rms(fa, fb),
        max_abs=float(np.abs(fa.astype(np.float64) - fb).max(initial=0.0)),
        first_divergent_frame=int(divergent[0]) if divergent.size else None,
        metric_deltas={f.name: round(getattr(mb, f.name) - getattr(ma, f.name), 4) for f in fields(mb)},
        delta_e_p95=float(np.percentile(delta_e, 95)) if delta_e.size else 0.0,
    )


def compare_sheet(
    a: Side,
    b: Side,
    *,
    layout: str = "auto",
    tiles: int = 4,
    width: int = 1024,
    out: Path | None = None,
    map_spec: str = DEFAULT_MAP,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    seed: int = 0,
    name: str | None = None,
    cache: Cache | None = None,
) -> Picture:
    """A and B in one sheet, rows labeled A and B (pewpew.sheet.compare_sheet),
    written to `out` or into A's cache folder. Raises as `compare` does,
    and OSError when the file cannot be written."""
    cache = cache if cache is not None else Cache()
    first, second = _pair(a, b, _Looks(map_spec, seconds, fps, seed, name), cache)
    drawn = draw_pair(
        first.frames, second.frames, first.geometry.mapping, first.spec.fps, layout=layout, tiles=tiles, width=width,
    )
    path = out or cache.path(first.handle, f"vs-{second.handle}-{layout}-{tiles}-{width}.png")
    return picture((first.handle, second.handle), drawn, path)


def look_diff(a: Mapping[str, Any], b: Mapping[str, Any]) -> tuple[Change, ...]:
    """Each knob or field of looks `a` and `b` (looks-file form) whose
    values differ, in A's order, then B's."""
    ka, kb = _knobs(a), _knobs(b)
    return tuple(Change(path, ka.get(path), kb.get(path)) for path in {**ka, **kb} if ka.get(path) != kb.get(path))


def _knobs(look: Mapping[str, Any]) -> dict[str, Any]:
    """A look's values by path: its own fields, its layer order, each
    layer's mix, each node's and signal's op and args by address, each
    route's depth, and its front knobs (module docstring)."""
    layers = look["layers"]
    out: dict[str, Any] = {key: look.get(key) for key in ("seed", "master", "fade", "cycle", "front")}
    out["layers"] = [layer["id"] for layer in layers]
    for layer in layers:
        out |= {layer_address(layer["id"], key): layer.get(key) for key in (*MIX, "out", "alpha")}
        out |= _nodes(layer["nodes"], partial(layer_address, layer["id"]))
    out |= _nodes(look.get("signals") or {}, signal_address)
    out |= {f"routes[{route['source']} -> {route['path']}]": route["depth"] for route in look.get("routes") or ()}
    return out


def _nodes(nodes: Mapping[str, Any], address: Callable[[str], str]) -> dict[str, Any]:
    """Each of `nodes` (by id) at its `address`: its op and what it reads,
    then each arg."""
    out: dict[str, Any] = {}
    for nid, node in nodes.items():
        at = address(nid)
        out[at] = {key: value for key, value in node.items() if key != "args"}
        out |= {f"{at}.{arg}": value for arg, value in node.get("args", {}).items()}
    return out


@dataclass(frozen=True, slots=True)
class _Looks:
    """How to render a side that is a look."""

    map_spec: str
    seconds: float
    fps: float
    seed: int
    name: str | None


def _pair(a: Side, b: Side, how: _Looks, cache: Cache | None) -> tuple[Take, Take]:
    """The frames of A and of B. A side that is a look renders as the other
    side was: as B when only B is a render, else as A."""
    if _is_render(b) and not _is_render(a):
        second = _side(b, how, cache)
        first = _side(a, _like(second, how), cache)
    else:
        first = _side(a, how, cache)
        second = _side(b, _like(first, how), cache)
    if first.frames.shape != second.frames.shape or first.geometry.digest != second.geometry.digest:
        raise ValueError(
            f"A and B must be rendered alike to compare: A is {_shape(first)}, B is {_shape(second)}; "
            "render both on the same map with the same seconds and fps"
        )
    return first, second


def _is_render(side: Side) -> TypeGuard[Rendered | str]:
    return isinstance(side, Rendered) or is_handle(side)


def _like(rendered: Take, how: _Looks) -> _Looks:
    """`how` with the map spec, seconds, fps and seed of `rendered`."""
    spec = rendered.spec
    return replace(how, map_spec=spec.map, seconds=spec.seconds, fps=spec.fps, seed=spec.seed)


def _side(side: Side, how: _Looks, cache: Cache | None) -> Take:
    if _is_render(side):
        return take(side, cache)
    rendered = render(
        cast("LookDoc", side), how.map_spec, how.seconds, how.fps, how.seed, name=how.name, cache=cache,
    )
    return take(rendered, cache)


def _shape(got: Take) -> str:
    frames, points = got.frames.shape[:2]
    return f"{frames} frames of {points} points at {got.spec.fps:g} fps on {got.geometry.spec}"
