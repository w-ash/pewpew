"""The render core: a stateful `Renderer` and the pure `render_sequence`.

`render_sequence(...) -> (F,N,3)` is the pure function of architecture §8
item 1: the same arguments give byte-identical frames. It builds a fresh
pattern instance per call, so nothing leaks between calls.

`Renderer` is the live-loop form: one bound (pattern, mapping) pair,
advanced frame by frame. It owns four engine responsibilities the author
never sees:

1. **Frame scoping.** `t` is pushed into the kit's frame context around each
   frame so `time()` resolves without a wall clock (req Q-5).
2. **Purity.** Registered buffers are read-only across the `render` call and
   writable again afterwards (ADR-005 amendment; architecture §3).
3. **Fixture units.** A pattern whose `units` is "fixture" renders once per
   fixture at the fixture's centre, and the frame is gathered out to every
   pixel of that fixture (ADR-007 amendment 2026-10-30). The pattern sees
   F fixtures as its n; sinks always see the N-pixel frame.
4. **Containment.** `before_render` and `render` are wrapped separately, per
   frame. A raising pattern yields a pulsing-red error frame and the loop
   keeps stepping and keeps calling the pattern, so a fix applied by hot
   reload self-heals with no restart — led-control's precedent
   [S660:ledcontrol/animationcontroller.py#L418-L434] and Pixelblaze's
   crash-proof editor semantics [S504]. Errors never stop rendering (ADR-005).
"""

from __future__ import annotations

import logging
import math
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from pewpew import kit
from pewpew.classinfo import pattern_name
from pewpew.errors import blamed, describe_exception
from pewpew.features import FakeFeatures, FeatureSource
from pewpew.mapping import Grouping
from pewpew.params import ParamSet
from pewpew.pattern import Inheritance, Pattern, check_units

logger = logging.getLogger(__name__)

# Error-frame look: solid red pulsing at 2 Hz, never darker than 25% so it can
# never be mistaken for "the pattern is just dark right now" [S660].
_ERROR_PULSE_HZ = 2.0
_ERROR_FLOOR = 0.25


@dataclass(frozen=True)
class SwapReport:
    """What `Renderer.swap` kept and what it reset — for the reload log line."""

    reset_params: tuple[str, ...]  # params whose live value no longer fit; now at the new default
    buffers: tuple[str, ...]  # registered buffers the new pattern inherited (pixels included)
    scalars: tuple[str, ...]  # plain instance attributes the new pattern inherited
    skipped: tuple[str, ...]  # old instance attributes that did not qualify and started fresh


@dataclass(frozen=True)
class _Geometry:
    """What one binding renders over: the coordinate arrays handed to the
    pattern, and the gather from its frame to the pixel frame (None when
    the pattern renders per pixel)."""

    units: str
    n: int
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    index: np.ndarray
    gather: np.ndarray | None

    @classmethod
    def of(cls, units: str, coords: np.ndarray, gather: np.ndarray | None) -> _Geometry:
        # Read-only column views: they are views onto the caller's mapping,
        # outside the buffer registry, so an in-place `x += 0.5` in `render`
        # would corrupt the mapping for every later frame.
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        index = np.arange(len(coords), dtype=np.int32)
        for column in (x, y, z, index):
            column.setflags(write=False)
        return cls(units, len(coords), x, y, z, index, gather)


@dataclass(frozen=True)
class PatternError:
    """One contained pattern failure — what `Renderer.error` exposes. Its
    text names no frame, so a pattern that fails every frame keeps one
    status line; the log gives the frame and time."""

    pattern: str
    phase: str  # "before_render" | "render"
    exception: BaseException
    traceback: str
    frame: int
    t: float

    def __str__(self) -> str:
        return f"{self.pattern}.{self.phase} raised: {describe_exception(self.exception)}"

    @property
    def path(self) -> str:
        """The address of the part that raised: the node of an effect
        program the exception names (`pewpew.errors.blamed`), else the
        pattern's."""
        return blamed(self.exception) or self.pattern


def contain(
    owner: str, phase: str, exc: Exception, frame: int, t: float, logged: set[tuple], *, outcome: str = "",
) -> PatternError:
    """`exc`, which `owner` raised in `phase` at frame `frame` and engine
    time `t`, as a contained failure. It is logged once per failure site:
    `logged` holds the sites already logged, and `outcome` (what the
    engine does about it) follows the error in the log line."""
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    # Keyed on the site, not the message: a message with per-frame detail
    # would flood.
    sites = tuple((f.filename, f.lineno, f.name) for f in traceback.extract_tb(exc.__traceback__))
    key = (owner, phase, type(exc).__name__, sites)
    # Drop the traceback: it pins every frame's locals while the error is
    # set. The formatted text is what the record needs.
    exc.__traceback__ = None
    error = PatternError(owner, phase, exc, formatted, frame, t)
    if key not in logged:
        logged.add(key)
        logger.error("%s%s (frame %d, t=%.6f)\n%s", error, outcome, frame, t, formatted)
    return error


class FrameSource(Protocol):
    """What `pewpew.pace.PacedLoop` drives: engine time and one frame per
    slot. `Renderer`, `pewpew.compose.Compositor` and
    `pewpew.crossfade.Crossfader` are each one."""

    @property
    def t(self) -> float: ...

    def advance_to(self, t: float) -> np.ndarray: ...


class Live(FrameSource, Protocol):
    """A frame source the aura runs: its contained error, the frame that
    stands in for it, and a new map (`rebind`). Loop thread only, except
    `error`. `Renderer` and `pewpew.compose.Compositor` are each one, and
    `pewpew.crossfade.Crossfader` fades between two."""

    @property
    def error(self) -> PatternError | None: ...

    def error_frame(self, t: float) -> np.ndarray: ...

    def rebind(self, mapping: np.ndarray, grouping: Grouping | None = None) -> None: ...


class SwapTarget(Protocol):
    """What a hot reload swaps a new pattern into (pewpew.reload): a
    `Renderer`, or one layer of the running stack."""

    @property
    def t(self) -> float: ...

    def swap(self, pattern: Pattern) -> SwapReport: ...


def error_frame(n: int, t: float) -> np.ndarray:
    """The deterministic pulsing-red frame of `n` pixels at engine time `t`:
    what a contained failure shows."""
    level = _ERROR_FLOOR + (1.0 - _ERROR_FLOOR) * float(kit.wave(_ERROR_PULSE_HZ * t))
    frame = np.zeros((n, 3), dtype=np.float32)
    frame[:, 0] = np.float32(level)
    return frame


class Renderer:
    """One bound (pattern, mapping) pair, advanced frame by frame."""

    def __init__(
        self,
        pattern: Pattern,
        mapping: np.ndarray,
        *,
        params: Mapping[str, Any] | None = None,
        seed: int = 0,
        features: FeatureSource | None = None,
        grouping: Grouping | None = None,
        units: str | None = None,
        name: str | None = None,
        t: float = 0.0,
    ) -> None:
        """`name` is what errors and refusals call the pattern, for its whole
        life: by default its class's name (pewpew.classinfo). `t` is the
        engine time it starts at, so a renderer built mid-run takes one
        slot as its first dt."""
        if isinstance(pattern, type):
            raise TypeError(
                "Renderer takes a Pattern instance, not a class — "
                "pass Cls() here, or use render_sequence(Cls, ...)"
            )
        self.pattern = pattern
        self.name = name or pattern_name(type(pattern))
        # Built once and never replaced (see `params`): a bad `--param` is
        # refused before the first frame.
        self._params = ParamSet(type(pattern), params, name=self.name)
        self.seed = seed
        # The seeded fake by default, so a sequence follows from its arguments.
        self.features = FakeFeatures(seed) if features is None else features

        self._t = float(t)
        self._frame = 0
        self._error: PatternError | None = None
        # The failure sites and complaints already logged. Cleared only by
        # `swap`, never by a good frame: a pattern that fails on alternate
        # frames would otherwise log a traceback 30 times a second.
        self._logged: set[tuple] = set()
        # Overrides `units` for every pattern this renderer runs.
        self._units = None if units is None else check_units(units)
        self._bind_mapping(mapping, grouping)

    # ---- state ---------------------------------------------------------

    @property
    def t(self) -> float:
        """Engine time of the most recent frame, in seconds."""
        return self._t

    @property
    def n(self) -> int:
        """Pixels in every frame this renderer returns."""
        return self._n

    @property
    def units(self) -> str:
        """What the running pattern renders per: "pixel" or "fixture".
        "fixture" only when the mapping has a grouping to render at."""
        return self._geom.units

    @property
    def gather(self) -> np.ndarray | None:
        """The fixture of each pixel, which spreads a per-fixture frame to
        every pixel, or None while the pattern renders per pixel."""
        return self._geom.gather

    @property
    def params(self) -> ParamSet:
        """The pattern's declared params and their current values; `set` on
        it reaches the running pattern (loop thread only). The same object
        for this renderer's whole life, `rebind` and `swap` included. A
        pattern that reads a param only in `setup` misses a live set
        (tests/test_param_liveness.py)."""
        return self._params

    @property
    def error(self) -> PatternError | None:
        """The current contained failure, or None while the pattern is healthy."""
        return self._error

    # ---- binding -------------------------------------------------------

    def rebind(self, mapping: np.ndarray, grouping: Grouping | None = None) -> None:
        """Rebind the pattern to a new mapping and its fixture grouping, if any.

        Buffers are reallocated and zeroed (no resampling [S219]), the RNG is
        reseeded, and `setup` runs again. Engine time and the frame counter
        continue: a new map mid-run is not a restart.
        """
        self._bind_mapping(mapping, grouping)

    def spawn(self, pattern: Pattern, params: Mapping[str, Any] | None = None, name: str | None = None) -> Renderer:
        """A new renderer for `pattern`, called `name`, on this one's mapping,
        grouping, `units` override, seed and feature source, at this one's
        engine time.

        The incoming side of a crossfade (pewpew.crossfade): its first dt is
        one slot, and it inherits no state, so a recalled look renders the
        same whatever ran before it. Raises what `Renderer` raises, with
        this renderer untouched.
        """
        return Renderer(
            pattern, self._mapping, params=dict(params or {}), seed=self.seed,
            features=self.features, grouping=self._grouping, units=self._units, name=name, t=self._t,
        )

    def _bind_mapping(self, mapping: np.ndarray, grouping: Grouping | None) -> None:
        mapping = np.asarray(mapping)
        if mapping.ndim != 2 or mapping.shape[1] != 3:
            raise ValueError(f"mapping must be (N,3) world coords, got {mapping.shape}")
        if grouping is not None and len(grouping.of) != len(mapping):
            raise ValueError(
                f"fixture table covers {len(grouping.of)} pixels; the mapping has {len(mapping)}"
            )
        self._mapping = mapping
        self._grouping = grouping
        self._n = int(mapping.shape[0])
        self._geom = self._geometry(type(self.pattern))
        # A raising `setup` leaves the pattern half-initialized. Binding is
        # not contained (a bind failure is loud), so the renderer refuses to
        # render until a later bind succeeds.
        self._bind_failed = True
        self._bind_pattern(self.pattern, self._params, self._geom)
        self._bind_failed = False

    def _geometry(self, pattern_cls: type) -> _Geometry:
        """The render coordinates for `pattern_cls` on the current mapping.
        Raises ValueError for a `units` value that is not in `UNITS`."""
        units = check_units(self._units if self._units is not None else pattern_cls.units)
        if units == "fixture" and self._grouping is not None:
            return _Geometry.of("fixture", np.asarray(self._grouping.centres), np.asarray(self._grouping.of))
        return _Geometry.of("pixel", self._mapping, None)

    def _bind_pattern(
        self,
        pattern: Pattern,
        params: ParamSet | Mapping[str, Any],
        geom: _Geometry,
        inherit: Inheritance | None = None,
    ) -> None:
        """Bind one instance to `geom`, with no poison bookkeeping: `swap`
        binds a candidate here and must leave the live state untouched."""
        pattern._bind(
            geom.n, geom.x, geom.y, geom.z, geom.index,
            seed=self.seed, params=params, inherit=inherit, name=self.name,
        )

    def swap(self, pattern: Pattern) -> SwapReport:
        """Replace the running pattern with `pattern`, keeping the run's state:
        the hot-reload primitive. Loop thread only.

        The candidate binds before anything here changes, so a raising
        `setup` propagates with the old pattern untouched. Engine time and
        the frame count continue. The `ParamSet` keeps its identity and the
        values `ParamSet.inherit` keeps (ADR-006); buffers, the RNG stream
        and `__init__` scalars carry over per `pewpew.pattern.Inheritance`.
        A candidate with other `units` binds the other geometry. `error`
        stays until the next healthy frame. The once-per-site log guard
        resets, so a site fixed and broken again logs again.
        """
        if isinstance(pattern, type):
            raise TypeError("swap takes a Pattern instance, not a class — pass Cls() here")
        geom = self._geometry(type(pattern))  # may raise; nothing has changed yet
        values, reset = self._params.inherit(type(pattern))
        inheritance = Inheritance(self.pattern)
        self._bind_pattern(pattern, values, geom, inheritance)  # may raise; nothing has changed yet
        self.pattern = pattern
        self._geom = geom
        self._params.redeclare(pattern, values)
        self._bind_failed = False  # a full bind against the current geometry just succeeded
        self._logged.clear()
        return SwapReport(
            tuple(reset), tuple(inheritance.buffers), tuple(inheritance.scalars), tuple(inheritance.skipped)
        )

    # ---- the frame path -------------------------------------------------

    def advance_to(self, t: float) -> np.ndarray:
        """Render the frame at absolute time `t`; dt is `t - self.t`. The
        caller owns the timeline (`SlotClock`)."""
        if self._bind_failed:
            raise RuntimeError(
                f"{self.name} is not bound — its setup() raised, "
                "so its buffers are half-initialized. Fix the pattern and rebind."
            )
        t = float(t)
        dt = t - self._t
        if dt < 0.0:
            # A stateful pattern cannot run backwards: `fade` would amplify,
            # and a trail would saturate to white. Scrub with render_sequence.
            raise ValueError(
                f"time never goes backwards: advance_to({t!r}) is before the current t={self._t!r}"
            )
        self._t = t
        frame_index = self._frame
        self._frame += 1
        pattern = self.pattern
        geom = self._geom

        with kit._frame_time(t):
            try:
                # Contained too: a failing feature source must not end the run.
                features = self.features.at(t)
                pattern.before_render(dt, features)
            except Exception as exc:  # noqa: BLE001  contained: a pattern must not take the aura down
                return self._contain("before_render", exc, frame_index, t)

            locked, unlockable = pattern._lock_buffers()
            for complaint in unlockable:
                self._note(complaint)
            try:
                frame = pattern.render(geom.x, geom.y, geom.z, geom.index)
            except Exception as exc:  # noqa: BLE001  contained: a pattern must not take the aura down
                return self._contain("render", exc, frame_index, t)
            finally:
                pattern._unlock_buffers(locked)

            # Shape and dtype only: a float64 frame would break `pixels`'
            # BufferSpec. Range and finiteness are O(N) on the hot path; the
            # goldens and bench_authoring check them.
            if not isinstance(frame, np.ndarray) or frame.shape != (geom.n, 3):
                got = f"{type(frame).__name__}"
                if isinstance(frame, np.ndarray):
                    got = f"array of shape {frame.shape}"
                exc = TypeError(f"render must return an ({geom.n},3) array, got {got}")
                return self._contain("render", exc, frame_index, t)
            if frame.dtype != np.float32:
                exc = TypeError(f"render must return float32, got {frame.dtype}")
                return self._contain("render", exc, frame_index, t)

        self._error = None
        # `pixels` gets a copy: the caller's frame must not be the state the
        # pattern reads back, which the next render also locks read-only. The
        # gather returns a new array too.
        pattern.pixels = frame.copy()
        return frame if geom.gather is None else frame[geom.gather]

    def step(self, dt: float) -> np.ndarray:
        """Convenience: advance by `dt` seconds from the current engine time."""
        return self.advance_to(self._t + dt)

    def resume_at(self, t: float) -> None:
        """Move engine time forward to `t` without rendering, so the next
        frame's dt starts at `t`: a layer enabled again after a pause takes
        one slot as its first dt (pewpew.compose). Raises ValueError for a
        `t` before the current one."""
        t = float(t)
        if t < self._t:
            raise ValueError(f"time never goes backwards: resume_at({t!r}) is before the current t={self._t!r}")
        self._t = t

    # ---- containment ----------------------------------------------------

    def _contain(self, phase: str, exc: Exception, frame_index: int, t: float) -> np.ndarray:
        self._error = contain(self.name, phase, exc, frame_index, t, self._logged)
        # Not assigned to `pixels`: a failed frame keeps the trail state.
        return self.error_frame(t)

    def error_frame(self, t: float) -> np.ndarray:
        """The pulsing-red frame at engine time `t`, one row per pixel of
        the current mapping."""
        return error_frame(self._n, t)

    def _note(self, complaint: str) -> None:
        """Log a non-fatal engine complaint, once until the next `swap`."""
        key = ("note", complaint)
        if key not in self._logged:
            self._logged.add(key)
            logger.warning("%s: %s", self.name, complaint)


class SlotClock:
    """Engine time per schedule slot: `t += 1/fps`, repeated, so the first
    slot is at t = 1/fps.

    The one home of the float sequence every deterministic artifact is
    frozen against: it matches `harness.clock.FakeClock.frames()` and
    `bench/bench_authoring.py::run_sequence` bit for bit, where `t = i/fps`
    would not. `render_sequence` and `pewpew.pace.PacedLoop` both use it.
    """

    def __init__(self, fps: float, start: float = 0.0) -> None:
        self.period = 1.0 / float(fps)
        self.t = float(start)

    def advance(self, slots: int = 1) -> float:
        for _ in range(slots):
            self.t += self.period
        return self.t


def render_sequence(
    pattern_factory: Callable[[], Pattern],
    mapping: np.ndarray,
    *,
    params: Mapping[str, Any] | None = None,
    seed: int = 0,
    frames: int = 120,
    fps: float = 60.0,
    features: FeatureSource | None = None,
    grouping: Grouping | None = None,
    units: str | None = None,
) -> np.ndarray:
    """Render `frames` frames from a fresh pattern instance; (F,N,3) float32.

    `pattern_factory` is a Pattern class or any zero-arg callable that
    returns a new instance. Slot times come from `SlotClock`. `grouping`
    and `units` are as for `Renderer`.
    """
    if isinstance(pattern_factory, Pattern):
        raise TypeError(
            "render_sequence takes a Pattern class, not an instance — pass Cls here, or use Renderer(Cls(), ...)"
        )
    renderer = Renderer(
        pattern_factory(), mapping, params=params, seed=seed, features=features,
        grouping=grouping, units=units,
    )
    out = np.empty((frames, renderer.n, 3), dtype=np.float32)
    clock = SlotClock(fps)
    for i in range(frames):
        out[i] = renderer.advance_to(clock.advance())
    return out


def check_frames(frames: np.ndarray, fps: float) -> np.ndarray:
    """`frames` as `render_sequence` returns them: an (F, N, 3) float32
    array of linear light with F >= 1, played at `fps` > 0 frames per
    second. Frame i is at t = (i + 1) / fps (`SlotClock`).

    Raises ValueError, naming what it got, for any other shape, an integer
    (display) array, or a bad fps. The result is C-contiguous, so a
    reduction over it sums in one order whatever the input's layout.
    """
    array = np.asarray(frames)
    if not np.issubdtype(array.dtype, np.floating):
        raise ValueError(
            f"frames are linear light, floats in 0-1, got {array.dtype}; "
            "an 8-bit display frame divided by 255 is not linear"
        )
    if array.ndim != 3 or array.shape[2] != 3 or len(array) == 0:
        raise ValueError(
            f"frames must be an (F, N, 3) array with F >= 1, as render_sequence returns, got {array.shape}"
        )
    if not (math.isfinite(fps) and fps > 0):
        raise ValueError(f"fps must be a positive number, got {fps!r}")
    return np.ascontiguousarray(array, dtype=np.float32)
