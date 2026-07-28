"""The render core: a stateful `Renderer` and the pure `render_sequence`.

`render_sequence(...) -> (F,N,3)` is the pure function architecture §8 item 1
asks for: same arguments in, byte-identical frames out, every time. It builds
a fresh pattern instance per call so nothing leaks between calls, which is
what makes golden-frame tests and deterministic scrubbing possible.

`Renderer` is the live-loop form of the same thing — one bound (pattern,
mapping) pair advanced frame by frame. It owns the three engine
responsibilities the author never sees:

1. **Frame scoping.** `t` is pushed into the kit's frame context around each
   frame so `time()` resolves without a wall clock (req Q-5).
2. **Purity.** Registered buffers are read-only across the `render` call and
   writable again afterwards (ADR-005 amendment; architecture §3).
3. **Containment.** `before_render` and `render` are wrapped separately, per
   frame. A raising pattern yields a pulsing-red error frame and the loop
   keeps stepping and keeps calling the pattern, so a fix applied by hot
   reload self-heals with no restart — led-control's precedent
   [S660:ledcontrol/animationcontroller.py#L418-L434] and Pixelblaze's
   crash-proof editor semantics [S504]. Errors never stop the show (ADR-005).
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from pewpew import kit
from pewpew.features import FakeFeatures
from pewpew.pattern import Pattern

logger = logging.getLogger(__name__)

# Error-frame look: solid red pulsing at 2 Hz, never darker than 25% so it can
# never be mistaken for "the pattern is just dark right now" [S660].
_ERROR_PULSE_HZ = 2.0
_ERROR_FLOOR = 0.25


@dataclass(frozen=True)
class PatternError:
    """One contained pattern failure — what `Renderer.error` exposes."""

    pattern: str
    phase: str  # "before_render" | "render"
    exception: BaseException
    traceback: str
    frame: int
    t: float

    def __str__(self) -> str:
        return (
            f"{self.pattern}.{self.phase} raised at frame {self.frame} "
            f"(t={self.t:.6f}): {type(self.exception).__name__}: {self.exception}"
        )


class Renderer:
    """One bound (pattern, mapping) pair, advanced frame by frame."""

    def __init__(
        self,
        pattern: Pattern,
        mapping: np.ndarray,
        params: dict[str, float] | None = None,
        seed: int = 0,
        features: Any = None,
    ) -> None:
        if isinstance(pattern, type):
            raise TypeError(
                "Renderer takes a Pattern instance, not a class — "
                "pass Cls() here, or use render_sequence(Cls, ...)"
            )
        self.pattern = pattern
        self.params = dict(params or {})
        self.seed = seed
        # Until the ADR-009 feature bus exists, an unspecified feature source
        # is the seeded fake — deterministic, and seeded from the same seed so
        # a sequence is reproducible from its arguments alone.
        self.features = FakeFeatures(seed) if features is None else features

        self._t = 0.0
        self._frame = 0
        self._error: PatternError | None = None
        self._logged: set[str] = set()
        self._diagnostics: list[str] = []
        self._bind_mapping(mapping)

    # ---- state ---------------------------------------------------------

    @property
    def t(self) -> float:
        """Engine time of the most recent frame, in seconds."""
        return self._t

    @property
    def mapping(self) -> np.ndarray:
        return self._mapping

    @property
    def n(self) -> int:
        return self._n

    @property
    def error(self) -> PatternError | None:
        """The current contained failure, or None while the pattern is healthy."""
        return self._error

    @property
    def diagnostics(self) -> tuple[str, ...]:
        """Non-fatal engine complaints, recorded once each (e.g. a buffer that
        could not be made read-only for `render`)."""
        return tuple(self._diagnostics)

    # ---- binding -------------------------------------------------------

    def rebind(self, mapping: np.ndarray) -> None:
        """Rebind the pattern to a new mapping.

        Buffers are reallocated and re-zeroed (resize re-zeros — no resampling
        semantics are invented [S219]), the RNG is reseeded, and `setup` runs
        again. Engine time and the frame counter are deliberately *not* reset:
        a geometry change mid-show is not a restart of the show.
        """
        self._bind_mapping(mapping)

    def _bind_mapping(self, mapping: np.ndarray) -> None:
        mapping = np.asarray(mapping)
        if mapping.ndim != 2 or mapping.shape[1] != 3:
            raise ValueError(f"mapping must be (N,3) world coords, got {mapping.shape}")
        self._mapping = mapping
        self._n = int(mapping.shape[0])
        # Column views, exactly as the study runner passed them.
        self._x, self._y, self._z = mapping[:, 0], mapping[:, 1], mapping[:, 2]
        self._index = np.arange(self._n, dtype=np.int32)
        self.pattern._bind(
            self._n, self._x, self._y, self._z, self._index, seed=self.seed, params=self.params
        )

    # ---- the frame path -------------------------------------------------

    def advance_to(self, t: float) -> np.ndarray:
        """Render the frame at absolute time `t`; dt is `t - self.t`.

        The exact-time form is primary because the caller owns the timeline
        (a fixed-step sequence, a scrub, a paced live loop) and float `t`
        accumulation must not be re-derived in two places.
        """
        t = float(t)
        dt = t - self._t
        self._t = t
        frame_index = self._frame
        self._frame += 1
        pattern = self.pattern

        with kit._frame_time(t):
            try:
                # The feature lookup sits inside the containment for the same
                # reason `before_render` does: a pattern must not be able to
                # take the show down, and neither must a flaky feature source.
                features = self.features.at(t)
                pattern.before_render(dt, features)
            except Exception as exc:
                return self._contain("before_render", exc, frame_index, t)

            locked, unlockable = pattern._lock_buffers()
            for complaint in unlockable:
                self._note(complaint)
            try:
                frame = pattern.render(self._x, self._y, self._z, self._index)
            except Exception as exc:
                return self._contain("render", exc, frame_index, t)
            finally:
                pattern._unlock_buffers(locked)

            if not isinstance(frame, np.ndarray) or frame.shape != (self._n, 3):
                got = f"{type(frame).__name__}"
                if isinstance(frame, np.ndarray):
                    got = f"array of shape {frame.shape}"
                # Returning the wrong thing is as much a pattern bug as raising,
                # and would otherwise escape containment downstream.
                exc = TypeError(f"render must return an ({self._n},3) array, got {got}")
                return self._contain("render", exc, frame_index, t)

        self._error = None
        self._logged.clear()  # a recurrence after a fix is worth logging again
        pattern.pixels = frame  # previous-frame buffer for the next render
        return frame

    def step(self, dt: float) -> np.ndarray:
        """Convenience: advance by `dt` seconds from the current engine time."""
        return self.advance_to(self._t + dt)

    # ---- containment ----------------------------------------------------

    def _contain(self, phase: str, exc: Exception, frame_index: int, t: float) -> np.ndarray:
        formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._error = PatternError(
            pattern=getattr(self.pattern, "name", type(self.pattern).__name__),
            phase=phase,
            exception=exc,
            traceback=formatted,
            frame=frame_index,
            t=t,
        )
        # De-duplicate on the *site* (phase + exception type + stack), never on
        # the formatted message: messages routinely carry per-frame detail
        # ("...at frame 41"), and keying on those would flood at 60 fps —
        # exactly what this guard exists to prevent. A different failure in the
        # same pattern still gets its own line.
        key = f"{phase}\n{type(exc).__name__}\n{''.join(traceback.format_tb(exc.__traceback__))}"
        if key not in self._logged:
            self._logged.add(key)
            logger.error("%s\n%s", self._error, formatted)
        # NB: the error frame is never assigned to pattern.pixels — a failed
        # frame must not corrupt the pattern's trail state.
        return self._error_frame(t)

    def _error_frame(self, t: float) -> np.ndarray:
        """Deterministic pulsing-red frame, derived from engine time only."""
        level = _ERROR_FLOOR + (1.0 - _ERROR_FLOOR) * float(kit.wave(_ERROR_PULSE_HZ * t))
        frame = np.zeros((self._n, 3), dtype=np.float32)
        frame[:, 0] = np.float32(level)
        return frame

    def _note(self, complaint: str) -> None:
        if complaint in self._diagnostics:
            return
        self._diagnostics.append(complaint)
        logger.warning("%s: %s", getattr(self.pattern, "name", "pattern"), complaint)


def render_sequence(
    pattern_factory: Callable[[], Pattern],
    mapping: np.ndarray,
    params: dict[str, float] | None = None,
    seed: int = 0,
    frames: int = 120,
    fps: float = 60.0,
    features: Any = None,
) -> np.ndarray:
    """Render `frames` frames from a fresh pattern instance; (F,N,3) float32.

    `pattern_factory` is a Pattern class or any zero-arg callable returning an
    instance — a new one every call, so no state survives between sequences.

    Timestamps are produced by repeated float accumulation (`t += 1.0/fps`,
    yielding t *after* each increment, so the first frame is at t=1/fps) and
    dt is the difference between successive accumulated values. That is not
    incidental: it reproduces `harness.clock.FakeClock.frames()` and the
    study runner `bench/bench_authoring.py::run_sequence` bit-for-bit, and
    `t = i/fps` or a constant `dt = 1/fps` would give different floats and
    break equivalence with the frozen study evidence. FakeClock is
    deliberately not imported — the engine does not depend on the harness.
    """
    renderer = Renderer(pattern_factory(), mapping, params=params, seed=seed, features=features)
    out = np.empty((frames, renderer.n, 3), dtype=np.float32)
    t = 0.0
    for i in range(frames):
        t += 1.0 / fps
        out[i] = renderer.advance_to(t)
    return out
