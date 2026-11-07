"""Rendering a look offline, as the aura would run it.

`play` is the one render path: it builds the look's layer stack with its
signals and routes (pewpew.compose.Compositor) and the master
(pewpew.aura.master.Master) as
`python -m pewpew run LOOKS --seed SEED` does when it starts in the
look, and steps them on the loop's slot times (`SlotClock`). So the frames
are what that run shows, byte for byte. `seed` is `run --seed`: it seeds
the stand-in audio and room features (`FakeFeatures`); the look's own
`seed` seeds its layers. A layer that raises is contained as in the aura,
and its error is a warning.

`render` checks the look, renders it, keeps the frames in the cache under
the render's handle (pewpew.lab.handles), and returns a `Rendered`: the
handle, the frame metrics (pewpew.metrics), warnings, and the normalized
spec the handle hashes. Never the frames: `take` gets them back by handle,
rendering again on a miss when it has the spec.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from pewpew.aura.master import Master
from pewpew.compose import Compositor, LayerError
from pewpew.features import EventFeatures, FakeFeatures
from pewpew.fx.codec import encode_look
from pewpew.lab.check import LookDoc, Ready, dims_problems, ready
from pewpew.lab.geometry import Geometry, parse_geometry
from pewpew.lab.handles import ENGINE, Cache, Expired, handle, is_handle
from pewpew.mapping import DEFAULT_MAP
from pewpew.metrics import FLASH_LIMIT, Metrics, measure
from pewpew.problems import Refused, problem
from pewpew.render import SlotClock
from pewpew.result import Result

DEFAULT_SECONDS = 4.0
DEFAULT_FPS = 30.0
MAX_SECONDS = 60.0
MAX_FPS = 240.0


@dataclass(frozen=True, slots=True)
class RenderSpec(Result):
    """What a render depends on, normalized: the look (looks-file form,
    every param written out), the map spec and what it gave (points, axes
    spanned), seconds, fps, the frame count, the features' seed, and the
    engine fingerprint."""

    look: dict[str, Any]
    map: str
    points: int
    dims: int
    seconds: float
    fps: float
    frames: int
    seed: int
    engine: str


@dataclass(frozen=True)
class Rendered(Result):
    """One render: its handle, the metrics of its frames, what to know
    about it (a layer that raised, a gate it would fail), and its spec
    (None in a `brief` render)."""

    handle: str
    metrics: Metrics
    warnings: tuple[str, ...] = ()
    spec: RenderSpec | None = None

    def brief(self) -> Rendered:
        """The render without its spec, which holds the whole look."""
        return replace(self, spec=None)


@dataclass(frozen=True, slots=True, eq=False)
class Take:
    """One render's frames, from the cache or rendered again: the handle,
    its spec, the frames and the geometry they show."""

    handle: str
    spec: RenderSpec
    frames: np.ndarray
    geometry: Geometry


def render(
    look: LookDoc,
    map_spec: str | Geometry = DEFAULT_MAP,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    seed: int = 0,
    *,
    name: str | None = None,
    cache: Cache | None = None,
) -> Rendered:
    """Render `look` (a look, or the look `name` of a looks file) on the
    map `map_spec` names (pewpew.lab.geometry), or on a geometry, for
    `seconds` at `fps`, the features seeded `seed` (module docstring). The
    cache answers a render it holds. Raises Refused for a look with problems, and ValueError for
    a bad map spec, seconds or fps."""
    staged = ready(look, name=name)
    geometry = where(map_spec)
    spec = RenderSpec(
        encode_look(staged.look), geometry.spec, geometry.points, geometry.dims, float(seconds), float(fps),
        frame_count(seconds, fps), int(seed), ENGINE,
    )
    key = handle({
        "look": spec.look, "map": geometry.digest, "seconds": spec.seconds, "fps": spec.fps, "seed": spec.seed,
        "engine": ENGINE,
    })
    cache = cache if cache is not None else Cache()
    notes: tuple[str, ...] = ()
    entry = cache.load(key)
    if entry is not None:
        frames, warnings = entry.frames, tuple(entry.record["warnings"])
    else:
        frames, warnings = play(staged, geometry, spec.frames, spec.fps, spec.seed)
        try:
            cache.store(key, frames, geometry, {"spec": spec.to_json(), "warnings": list(warnings)})
        except OSError as exc:
            notes = (f"the frames are not cached ({exc.strerror or exc}); a sheet or compare renders them again",)
    metrics = measure(frames, spec.fps)
    return Rendered(key, metrics, warnings + limits(metrics) + notes, spec)


def play(staged: Ready, geometry: Geometry, frames: int, fps: float, seed: int) -> tuple[np.ndarray, tuple[str, ...]]:
    """`frames` frames of `staged` on `geometry` at `fps`, as (frames, N, 3)
    float32 linear light, and the error of each layer that raised, once
    each (module docstring). Raises Refused for a program that `geometry`
    does not support, or a layer that cannot be built on it."""
    if problems := dims_problems(staged, geometry.dims):
        raise Refused(problems)
    look = staged.look
    try:
        stack = Compositor(
            staged.layers, geometry.mapping, seed=look.seed, signals=look.signals, routes=look.routes,
            front=look.front, features=EventFeatures(FakeFeatures(seed)), grouping=geometry.grouping,
        )
    except (LayerError, ValueError) as exc:  # ValueError: a route the stack's knobs refuse
        raise Refused([problem(str(exc))]) from exc
    master = Master()
    if staged.look.master is not None:
        master.set(staged.look.master)
    out = np.empty((frames, geometry.points, 3), np.float32)
    errors: dict[str, None] = {}
    clock = SlotClock(fps)
    for i in range(frames):
        t = clock.advance()
        out[i] = master.apply(t, stack.advance_to(t))
        if (error := stack.error) is not None:
            errors.setdefault(str(error))
    return out, tuple(errors)


def take(source: Rendered | str, cache: Cache | None = None) -> Take:
    """The frames of `source`, a render or its handle: from the cache, or
    rendered again from a render's spec. Raises Expired for a handle the
    cache no longer holds, and ValueError for text that is not a handle."""
    key = source.handle if isinstance(source, Rendered) else source
    if not is_handle(key):
        raise ValueError(f"expected a render handle such as r1-0123456789abcdef0123, got {key!r}")
    entry = (cache if cache is not None else Cache()).load(key)
    if entry is not None:
        return Take(key, RenderSpec(**entry.record["spec"]), entry.frames, entry.geometry)
    spec = source.spec if isinstance(source, Rendered) else None
    if spec is None:
        raise Expired(key)
    staged = restage(spec)
    geometry = where(spec.map)
    frames, _ = play(staged, geometry, spec.frames, spec.fps, spec.seed)
    return Take(key, spec, frames, geometry)


def restage(spec: RenderSpec) -> Ready:
    """The look of `spec` ready to run again. Raises Refused as `ready`
    does."""
    return ready(spec.look)


def where(map_spec: str | Geometry) -> Geometry:
    """The geometry `map_spec` names (pewpew.lab.geometry), or `map_spec`
    when it is one."""
    return map_spec if isinstance(map_spec, Geometry) else parse_geometry(map_spec)


def frame_count(seconds: float, fps: float) -> int:
    """The frames `seconds` at `fps` take, at least 1. Raises ValueError
    for seconds or fps out of range."""
    if not 0.0 < seconds <= MAX_SECONDS:
        raise ValueError(f"seconds must be above 0 and at most {MAX_SECONDS:g}, got {seconds!r}")
    if not 0.0 < fps <= MAX_FPS:
        raise ValueError(f"fps must be above 0 and at most {MAX_FPS:g}, got {fps!r}")
    return max(1, round(seconds * fps))


def limits(metrics: Metrics) -> tuple[str, ...]:
    """Why frames with `metrics` fail the content gate (`verify looks`):
    flashing faster than WCAG allows, too short to tell, or no light at
    all."""
    out = []
    safe = metrics.flash_safe
    if safe is None:
        out.append(f"{metrics.seconds:g} s is too short to judge flashing; WCAG 2.3.1 counts any one second, "
                   "so render at least 1 s")
    elif not safe:
        out.append(f"flashes up to {metrics.flash_rate_max:g} times a second; WCAG 2.3.1 allows {FLASH_LIMIT:g}")
    if metrics.black_fraction >= 1.0:
        out.append("every frame is black")
    return tuple(out)
