"""The render core: a stateful `Renderer`.

`Renderer` runs one effect program bound to a mapping
(pewpew.fx.bound_program.BoundProgram), frame by frame; each layer of a
stack is one. The same inputs give byte-identical frames (architecture
§8 item 1): engine time comes from the caller (`advance_to`), never a
wall clock (req Q-5). It owns the engine's side of a frame:

1. **Purity.** The program's buffers are read-only across its render and
   writable again afterwards (ADR-005 amendment; architecture §3).
2. **Containment.** The program's advance and render are wrapped
   separately, per frame. A raising program yields a pulsing-red error
   frame and the loop keeps stepping and keeps calling it, so a failure
   that passes heals with no restart — led-control's precedent
   [S660:ledcontrol/animationcontroller.py#L418-L434] and Pixelblaze's
   crash-proof editor semantics [S504]. Errors never stop rendering (ADR-005).
3. **Bind poisoning.** A bind that raises leaves the renderer refusing to
   render until a later bind succeeds.
4. **Frame checks.** A frame that is not (n, 3) float32 is contained.
"""

from __future__ import annotations

import logging
import math
import traceback
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from pewpew.errors import blamed, describe_exception
from pewpew.features import FakeFeatures, FeatureSource
from pewpew.fx.bound_program import BoundProgram
from pewpew.fx.prims.vec import wave
from pewpew.fx.types import Coords

logger = logging.getLogger(__name__)

# Error-frame look: solid red pulsing at 2 Hz, never darker than 25% so it can
# never be mistaken for "the look is just dark right now" [S660].
_ERROR_PULSE_HZ = 2.0
_ERROR_FLOOR = 0.25


@dataclass(frozen=True)
class RenderFailure:
    """One contained render failure — what `Renderer.error` exposes. Its
    text names no frame, so a layer that fails every frame keeps one
    status line; the log gives the frame and time. `layer` is the address
    of the layer (or signal) that failed, such as `layers.base`."""

    layer: str
    phase: str  # "advance" | "render"
    exception: BaseException
    traceback: str
    frame: int
    t: float

    def __str__(self) -> str:
        return f"{self.layer}.{self.phase} raised: {describe_exception(self.exception)}"

    @property
    def path(self) -> str:
        """The address of the part that raised: the node of an effect
        program the exception names (`pewpew.errors.blamed`), else the
        layer's."""
        return blamed(self.exception) or self.layer


def contain(
    owner: str, phase: str, exc: Exception, frame: int, t: float, logged: set[tuple], *, outcome: str = "",
) -> RenderFailure:
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
    error = RenderFailure(owner, phase, exc, formatted, frame, t)
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
    def error(self) -> RenderFailure | None: ...

    def error_frame(self, t: float) -> np.ndarray: ...

    def rebind(self, mapping: np.ndarray) -> None: ...


def error_frame(n: int, t: float) -> np.ndarray:
    """The deterministic pulsing-red frame of `n` pixels at engine time `t`:
    what a contained failure shows."""
    level = _ERROR_FLOOR + (1.0 - _ERROR_FLOOR) * float(wave(_ERROR_PULSE_HZ * t))
    frame = np.zeros((n, 3), dtype=np.float32)
    frame[:, 0] = np.float32(level)
    return frame


class Renderer:
    """One bound program run frame by frame (module docstring)."""

    def __init__(
        self,
        bound: BoundProgram,
        mapping: np.ndarray,
        *,
        seed: int = 0,
        features: FeatureSource | None = None,
        t: float = 0.0,
    ) -> None:
        """Bind `bound` to `mapping`, its nodes keyed from `seed`. Errors
        name it by `bound.name`. `t` is the engine time it starts at, so a
        renderer built mid-run takes one slot as its first dt. Raises what
        the bind raises."""
        self.bound = bound
        self.seed = seed
        # The seeded fake by default, so a sequence follows from its arguments.
        self.features = FakeFeatures(seed) if features is None else features

        self._t = float(t)
        self._frame = 0
        self._error: RenderFailure | None = None
        # The failure sites already logged. Never cleared by a good frame: a
        # program that fails on alternate frames would otherwise log a
        # traceback 30 times a second.
        self._logged: set[tuple] = set()
        self.rebind(mapping)

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
    def error(self) -> RenderFailure | None:
        """The current contained failure, or None while the program is healthy."""
        return self._error

    # ---- binding -------------------------------------------------------

    def rebind(self, mapping: np.ndarray) -> None:
        """Bind the program to a new mapping.

        Buffers are reallocated at their fill (no resampling [S219]) and
        each op's `setup` runs again; the nodes' knobs are kept. Engine
        time and the frame counter continue: a new map mid-run is not a
        restart. Raises ValueError for a mapping that is not (N, 3), and
        what the bind raises.
        """
        mapping = np.asarray(mapping)
        if mapping.ndim != 2 or mapping.shape[1] != 3:
            raise ValueError(f"mapping must be (N,3) world coords, got {mapping.shape}")
        self._n = int(mapping.shape[0])
        # Read-only column views: they are views onto the caller's mapping,
        # outside the buffers, so an in-place `x += 0.5` in a render would
        # corrupt the mapping for every later frame.
        x, y, z = mapping[:, 0], mapping[:, 1], mapping[:, 2]
        index = np.arange(self._n, dtype=np.int32)
        for column in (x, y, z, index):
            column.setflags(write=False)
        # A raising bind leaves the program half-bound. Binding is not
        # contained (a bind failure is loud), so the renderer refuses to
        # render until a later bind succeeds.
        self._bind_failed = True
        self.bound.bind(Coords.of(x, y, z, index), self.seed)
        self._bind_failed = False

    # ---- the frame path -------------------------------------------------

    def advance_to(self, t: float) -> np.ndarray:
        """Render the frame at absolute time `t`; dt is `t - self.t`. The
        caller owns the timeline (`SlotClock`)."""
        if self._bind_failed:
            raise RuntimeError(
                f"{self.bound.name} is not bound: its bind raised, so its buffers are "
                "half-initialized. Rebind it to a map it can run on."
            )
        t = float(t)
        dt = t - self._t
        if dt < 0.0:
            # A stateful program cannot run backwards: a fade would amplify,
            # and a trail would saturate to white.
            raise ValueError(
                f"time never goes backwards: advance_to({t!r}) is before the current t={self._t!r}"
            )
        self._t = t
        frame_index = self._frame
        self._frame += 1
        bound = self.bound

        try:
            # Contained too: a failing feature source must not end the run.
            bound.advance(dt, self.features.at(t))
        except Exception as exc:  # noqa: BLE001  contained: a program must not take the aura down
            return self._contain("advance", exc, frame_index, t)

        try:
            with bound.buffers.locked():
                frame = bound.render()
        except Exception as exc:  # noqa: BLE001  contained: a program must not take the aura down
            return self._contain("render", exc, frame_index, t)

        # Shape and dtype only: a float64 frame would become a float64
        # `pixels`. Range and finiteness are O(N) on the hot path; the
        # goldens check them.
        if not isinstance(frame, np.ndarray) or frame.shape != (self._n, 3):
            got = f"{type(frame).__name__}"
            if isinstance(frame, np.ndarray):
                got = f"array of shape {frame.shape}"
            exc = TypeError(f"render must return an ({self._n},3) array, got {got}")
            return self._contain("render", exc, frame_index, t)
        if frame.dtype != np.float32:
            exc = TypeError(f"render must return float32, got {frame.dtype}")
            return self._contain("render", exc, frame_index, t)

        self._error = None
        # `pixels` gets a copy: the caller's frame must not be the state the
        # program reads back, which the next render also locks read-only.
        bound.buffers.pixels = frame.copy()
        return frame

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
        self._error = contain(self.bound.name, phase, exc, frame_index, t, self._logged)
        # Not assigned to `pixels`: a failed frame keeps the trail state.
        return self.error_frame(t)

    def error_frame(self, t: float) -> np.ndarray:
        """The pulsing-red frame at engine time `t`, one row per pixel of
        the current mapping."""
        return error_frame(self._n, t)


class SlotClock:
    """Engine time per schedule slot: `t += 1/fps`, repeated, so the first
    slot is at t = 1/fps.

    The one home of the float sequence every deterministic artifact is
    frozen against: it matches `pewpew.testing.clock.FakeClock.frames()` bit for
    bit, where `t = i/fps` would not. The offline renders and `pewpew.pace.PacedLoop` both use it.
    """

    def __init__(self, fps: float, start: float = 0.0) -> None:
        self.period = 1.0 / float(fps)
        self.t = float(start)

    def advance(self, slots: int = 1) -> float:
        for _ in range(slots):
            self.t += self.period
        return self.t


def check_frames(frames: np.ndarray, fps: float) -> np.ndarray:
    """`frames` as an offline render gives them: an (F, N, 3) float32
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
            f"frames must be an (F, N, 3) array with F >= 1, as a render gives, got {array.shape}"
        )
    if not (math.isfinite(fps) and fps > 0):
        raise ValueError(f"fps must be a positive number, got {fps!r}")
    return np.ascontiguousarray(array, dtype=np.float32)
