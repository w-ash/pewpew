"""The ADR-005 authoring contract: typed params, the `Pattern` base, and the
engine-managed buffer registry.

A pattern is a class with three author hooks:

    setup(n, x, y, z, index)      once per (pattern, mapping) binding
    before_render(dt, features)   once per frame; the only place RNG is drawn
    render(x, y, z, index)        pure; (N,) coord arrays -> (N,3) float32 RGB

Coordinates are normalized 0-1 world units (architecture §3); the returned
frame is linear-light RGB in [0,1] (ADR-001), quantized once at the sinks.

`render` is pure by construction: every buffer the engine knows about — the
persistent `self.pixels` output buffer plus everything declared with
`self.buffer(...)` — is flipped read-only for the duration of the call, so
per-pixel state can only advance in `setup`/`before_render` (ADR-005
amendment 2026-07-27). Purity is what golden-frame testing and determinism
rest on (architecture §8).

Supersedes `bench/authoring/surface.py`, whose arithmetic this preserves
bit-exactly. Of that prototype's two self-declared hacks, the module-global
`time()` is resolved (frame-scoped in `kit.py`); `Param` still materializes
to a plain float here, standing in for the typed parameter tree until
ADR-006 lands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

# `pixels` is engine-registered, so an author re-declaring it at a different
# shape would silently break the previous-frame contract. The other names are
# engine-provided instance state. Note this denylist is a *message* aid only —
# the real guard in `buffer()` refuses any name that already resolves on the
# class, which also covers the hooks (`render`, `setup`, ...), the registry
# internals (`_buffers`), and every declared `Param`.
_RESERVED_BUFFER_NAMES = frozenset({"n", "seed", "rng", "name", "pixels"})


# ---- typed params (ADR-006 semantics, still prototype-minimal) --------------


class Param:
    """One-line typed knob: Param(default, lo, hi, label).

    At bind the instance attribute becomes plain float(default), so pattern
    code reads `self.speed` as a number. The typed tree that drives UI/OSC/
    MIDI/modulation off these declarations is ADR-006's job; the declaration
    shape here is what it will read.
    """

    def __init__(self, default: float, lo: float = 0.0, hi: float = 1.0, label: str = ""):
        self.default, self.lo, self.hi, self.label = default, lo, hi, label


# ---- the buffer registry (ADR-005 amendment 2026-07-27) ---------------------


@dataclass(frozen=True)
class BufferSpec:
    """What the engine remembers about a declared buffer.

    Deliberately name -> *spec*, never name -> array identity: authors
    legitimately rebind their buffers (`self.heat = np.maximum(self.heat -
    cool, 0.0)` in fire's before_render), so the engine re-reads
    `getattr(pattern, name)` fresh whenever it needs the current value.
    Identity tracking would silently stop tracking on the first rebind.

    The spec is also the unit hot reload will carry buffers across by
    (name + shape, ADR-005 amendment).
    """

    shape: tuple[int, ...]
    dtype: np.dtype
    fill: float


def _normalize_shape(shape: int | Iterable[int]) -> tuple[int, ...]:
    if isinstance(shape, (int, np.integer)):
        return (int(shape),)
    return tuple(int(s) for s in shape)


# ---- the pattern base -------------------------------------------------------


class Pattern:
    """Base class for authored patterns; subclasses override the hooks.

    Engine-provided instance state, set at bind time: `self.n`, `self.seed`,
    `self.rng` (a seeded `np.random.default_rng`), and `self.pixels` — the
    (n,3) float32 buffer holding the previous frame's output, which persists
    across frames so trails and decay work [S630][S715].
    """

    name = "pattern"

    # Class-level defaults so an *unbound* instance is inert rather than
    # AttributeError-prone. `_buffers` is only ever mutated after `_bind` has
    # replaced it with a per-instance dict, so this shared dict stays empty.
    _buffers: dict[str, BufferSpec] = {}
    _buffers_open: bool = False

    # ---- author hooks -------------------------------------------------

    def setup(self, n: int, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> None:
        """Called once per (pattern, mapping) binding, before the first frame.

        The only place `self.buffer(...)` may be called. Receives the
        coordinate arrays: per-pixel state can be shaped by geometry here and
        then advanced in `before_render`, which is the unlock that keeps
        `render` pure (stumble #17).
        """

    def before_render(self, dt: float, features: Any) -> None:
        """Advance state once per frame. The only place RNG may be drawn."""

    def render(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, index: np.ndarray) -> np.ndarray:
        """Pure over coordinate arrays; returns (N,3) float32 in [0,1]."""
        raise NotImplementedError

    # ---- engine-provided API the author calls -------------------------

    def buffer(
        self,
        name: str,
        shape: int | Iterable[int],
        dtype: Any = np.float32,
        fill: float = 0.0,
    ) -> np.ndarray:
        """Declare engine-managed persistent state; returns the new array.

        Allocates the array, sets it as `self.<name>`, registers its spec, and
        hands it back. From then on the engine owns its lifecycle: zeroed on
        rebind, reallocated and re-zeroed when the mapping changes (no
        resampling semantics are invented [S219]), read-only inside `render`.

        `shape` is free-form — `n` or `(n,)` for per-pixel state, `(32, 16)`
        for an internal field at its own resolution (fire's heat grid,
        stumble #12). Both get the same sanctioned lifecycle.
        """
        if not self._buffers_open:
            raise RuntimeError(
                f"{type(self).__name__}.buffer({name!r}, ...) called outside setup(): "
                "buffers may only be declared inside setup(), because that is the one "
                "moment the engine can size them to the mapping and take over their "
                "lifecycle (ADR-005 amendment 2026-07-27). Declare it in setup() and "
                "write to it from before_render()."
            )
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError(f"buffer name must be a valid attribute name, got {name!r}")
        # Refuse anything that already resolves on the class. Enumerating a
        # denylist is not enough: `buffer("render", n)` would shadow the hook
        # (every later frame dies with "'ndarray' object is not callable"),
        # and `buffer("_buffers", n)` would replace the registry mid-`setup`
        # and raise *out* of binding, past all containment.
        if name in _RESERVED_BUFFER_NAMES or hasattr(type(self), name):
            if name == "pixels":
                reason = "the engine registers it for you as the previous-frame buffer"
            elif name in _RESERVED_BUFFER_NAMES:
                reason = "it is engine-provided instance state"
            else:
                reason = (
                    f"{type(self).__name__}.{name} already exists on the class "
                    f"({type(getattr(type(self), name)).__name__}) — a buffer would shadow it"
                )
            raise ValueError(f"buffer name {name!r} is reserved — {reason}")
        if name in self._buffers:
            raise ValueError(f"buffer {name!r} is already declared by this pattern")
        return self._declare(name, shape, dtype, fill)

    # ---- engine internals ---------------------------------------------

    def _declare(
        self, name: str, shape: int | Iterable[int], dtype: Any, fill: float
    ) -> np.ndarray:
        """Single allocation path, shared by `buffer()` and `self.pixels`."""
        spec = BufferSpec(_normalize_shape(shape), np.dtype(dtype), float(fill))
        array = np.full(spec.shape, spec.fill, dtype=spec.dtype)
        setattr(self, name, array)
        self._buffers[name] = spec
        return array

    def _bind(
        self,
        n: int,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        index: np.ndarray,
        seed: int = 0,
        params: dict[str, float] | None = None,
    ) -> None:
        """Engine-side binding of this instance to one mapping.

        Order is contractual: engine state, then params (so `setup` sees final
        values), then the registry with `self.pixels` in it, then the author's
        `setup` with buffer declaration enabled. Re-binding re-runs all of it:
        buffers are reallocated and re-zeroed, the RNG is reseeded from the
        same seed, and `setup` runs again.
        """
        self.n = int(n)
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Param materialization, verbatim from surface.py::Pattern._setup: MRO
        # order means the most-derived declaration wins, and the isinstance
        # guard is what makes that true (a base's Param sees a float already).
        declared: set[str] = set()
        for cls in type(self).__mro__:
            for k, val in vars(cls).items():
                if not isinstance(val, Param):
                    continue
                declared.add(k)
                if not isinstance(getattr(self, k), float):
                    setattr(self, k, float(val.default))
        for k, v in (params or {}).items():
            # An override that lands on an undeclared name is a dead knob: it
            # sets an attribute nothing reads, and nothing complains. That is
            # precisely the failure mode the sdf3d dead-`spin` addendum
            # records (bench/results/authoring-2026-07-16.md) — a parameter
            # that appears to work and provably does nothing. Refuse it here
            # rather than let it reach a stage where only a liveness check
            # could catch it.
            if k not in declared:
                known = ", ".join(sorted(declared)) or "(none)"
                raise ValueError(
                    f"{type(self).__name__} has no Param named {k!r}; "
                    f"declared params: {known}"
                )
            setattr(self, k, float(v))

        self._buffers = {}
        self._declare("pixels", (self.n, 3), np.float32, 0.0)

        self._buffers_open = True
        try:
            self.setup(self.n, x, y, z, index)
        finally:
            self._buffers_open = False

    def _lock_buffers(self) -> tuple[list[np.ndarray], list[str]]:
        """Flip every registered buffer read-only for the duration of `render`.

        Best-effort and total by design: an author who rebinds a buffer to a
        non-owning view (or to something that is not an array at all) must not
        crash the engine over a policy check, so failures are returned for the
        caller to record once, never raised. Returns (locked arrays, reasons
        for the ones that could not be locked).
        """
        locked: list[np.ndarray] = []
        failed: list[str] = []
        for name in self._buffers:
            value = getattr(self, name, None)
            if not isinstance(value, np.ndarray):
                failed.append(
                    f"buffer {name!r} is a {type(value).__name__}, not an ndarray — "
                    "render purity is not enforced for it"
                )
                continue
            if not value.flags.writeable:
                continue  # already read-only: purity holds, nothing to restore
            try:
                value.setflags(write=False)
            except Exception as exc:  # non-owning view, broadcast result, ...
                failed.append(
                    f"buffer {name!r} could not be made read-only ({exc}) — "
                    "render purity is not enforced for it"
                )
                continue
            locked.append(value)
        return locked, failed

    @staticmethod
    def _unlock_buffers(locked: list[np.ndarray]) -> None:
        """Restore writeability of exactly the arrays `_lock_buffers` locked."""
        for array in locked:
            try:
                array.setflags(write=True)
            except Exception:
                pass  # never raise into the frame path
