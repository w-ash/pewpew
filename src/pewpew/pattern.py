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
bit-exactly. Both of that prototype's self-declared hacks are resolved: the
module-global `time()` is frame-scoped in `kit.py`, and `Param` declarations
now outlive bind as a `ParamSet` (ADR-006 amendment 2026-08-22) rather than
collapsing to floats that nothing could read back.
"""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple

import numpy as np

# `pixels` is engine-registered, so an author re-declaring it at a different
# shape would silently break the previous-frame contract. The other names are
# engine-provided instance state. Note this denylist is a *message* aid only —
# the real guard in `buffer()` refuses any name that already resolves on the
# class, which also covers the hooks (`render`, `setup`, ...), the registry
# internals (`_buffers`), and every declared `Param`.
_RESERVED_BUFFER_NAMES = frozenset({"n", "seed", "rng", "name", "pixels"})


# ---- typed params (ADR-006, amended 2026-08-22) -----------------------------

# How far outside its range a value may land and still be read as float noise
# rather than a mistake, as a fraction of the range's own width.
_SNAP_TOL = 1e-9


class Param:
    """One-line typed knob: Param(default, lo, hi, label).

    `lo`/`hi` are a contract, not decoration: a value outside them is refused,
    so a control surface can trust that a knob's declared endpoints bound every
    value the engine will ever render. Widening the range is a one-line edit to
    the declaration, which is the honest way to reach further — it moves the
    slider's endpoints too.

    `label` is the *unit*, not the name ("Rev/s", "Sparks/s per column"): a UI
    captions from `name` and annotates with `label`.

    At bind the instance attribute becomes a plain float, so pattern code reads
    `self.speed` as a number with no indirection on the frame path. The
    declarations stay readable off the class via `declared_params`, which is
    what `ParamSet` and any control surface read.
    """

    def __init__(self, default: float, lo: float = 0.0, hi: float = 1.0, label: str = ""):
        default, lo, hi = float(default), float(lo), float(hi)
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise ValueError(f"Param range must be finite, got {lo}..{hi}")
        if lo >= hi:
            raise ValueError(
                f"Param range must have lo < hi, got {lo}..{hi} — "
                "a knob that cannot move is dead by construction"
            )
        if not lo <= default <= hi:
            raise ValueError(f"Param default {default} is outside its own range {lo}..{hi}")
        self.default, self.lo, self.hi, self.label = default, lo, hi, label
        # Filled by __set_name__, which fires only for a Param assigned in a
        # class body. One set onto a class afterwards never gets there, so
        # every reader tolerates the blank.
        self.name: str = ""
        self.owner: type | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.name, self.owner = name, owner

    def __repr__(self) -> str:
        return f"Param({self.default}, {self.lo}, {self.hi}, {self.label!r})"

    @property
    def step(self) -> float:
        """Slider granularity: ~200 divisions of the range, snapped to a 1/2/5
        decade so the steps are round numbers.

        Derived rather than declared, so ADR-006's one-line declaration form
        stays intact and every control surface quantizes identically — the
        retired playground hand-tuned this per knob and the browser was the
        only thing that knew.
        """
        raw = (self.hi - self.lo) / 200.0
        decade = 10.0 ** math.floor(math.log10(raw))
        for mult in (1.0, 2.0, 5.0):
            if raw <= mult * decade:
                return mult * decade
        return 10.0 * decade

    @property
    def decimals(self) -> int:
        """Digits after the point for a value readout, derived from `step`."""
        return max(0, -math.floor(math.log10(self.step)))


def declared_params(cls: type) -> dict[str, Param]:
    """Every `Param` declared on `cls` or inherited, in display order.

    Two orderings, deliberately different. *Which* declaration supplies a name
    is most-derived-wins, so a subclass can retune a base's knob. *Iteration*
    is base-first, so a subclass adding knobs appends to a stable prefix rather
    than reshuffling the row above it. That order is what a control surface
    lays sliders out in, so it is a contract with a test on it.
    """
    found: dict[str, Param] = {}
    for base in reversed(cls.__mro__):
        for name, value in vars(base).items():
            if isinstance(value, Param):
                found[name] = value  # dict keeps the first insertion's position
    return found


class ParamSet:
    """The declared knobs of one pattern class, plus their current values.

    Not a tree: no paths, no nesting, no mount points. ADR-006's canonical
    state tree is Phase 3, and this deliberately does not pre-spend its
    vocabulary. What it owns is the pair a control surface needs — what knobs
    exist (`describe`) and what they read right now (`snapshot`) — behind one
    validated write path.

    Threading. `check`, `snapshot` and `describe` are safe from any thread: the
    key set is fixed at construction, so no rehash ever occurs and a concurrent
    reader sees a consistent set of names with possibly one-tick-stale values.
    `set` and `apply` mutate and belong to the loop thread — reach them through
    `PacedLoop.call_soon`. Validate with `check` on the *calling* thread first:
    an exception from a queued closure propagates out of `PacedLoop.run()`
    (pace.py), so a raising setter reached over a socket is a way to kill the
    show from a browser.
    """

    def __init__(self, pattern_cls: type, overrides: Mapping[str, float] | None = None) -> None:
        self._state = _ParamState.of(pattern_cls, None)
        if overrides:
            self.set_many(overrides)

    # One tuple, swapped in a single attribute store by `redeclare`, so a
    # reader on another thread can never pair new declarations with old
    # values — `describe` iterating one dict and indexing the other across a
    # hot reload would otherwise KeyError on a sink worker. Every reader
    # takes `self._state` once and works from that one tuple.

    @property
    def declarations(self) -> dict[str, Param]:
        return self._state.declarations

    # ---- reads (any thread) --------------------------------------------

    def __getitem__(self, name: str) -> float:
        return self._state.values[name]

    def __contains__(self, name: object) -> bool:
        return name in self._state.values

    def __iter__(self):
        return iter(self._state.values)

    def __len__(self) -> int:
        return len(self._state.values)

    def __repr__(self) -> str:
        _, values, pattern = self._state
        return f"ParamSet({pattern}, {values})"

    def snapshot(self) -> dict[str, float]:
        """Current values; round-trips back in as `overrides`.

        That round-trip is what `inherit` builds on, so it has a test rather
        than being an accident of both being plain floats.
        """
        return dict(self._state.values)

    def describe(self) -> list[dict[str, Any]]:
        """JSON-ready declarations in display order — the control-surface payload.

        A list, not a dict, so display order survives transport. Built here and
        not in a sink, so a field added to `Param` reaches every surface at once
        instead of stopping at whichever one remembered to marshal it.
        """
        declarations, values, _ = self._state
        return [
            {
                "name": name,
                "label": param.label,
                "default": param.default,
                "lo": param.lo,
                "hi": param.hi,
                "step": param.step,
                "decimals": param.decimals,
                "value": values[name],
            }
            for name, param in declarations.items()
        ]

    def inherit(self, pattern_cls: type) -> tuple[dict[str, float], list[str]]:
        """The values a swap to `pattern_cls` would start from, and which
        knobs reset.

        ADR-006's reload policy: a current value that still lands in the new
        declaration's range is kept; one that no longer fits resets to the
        *new default*, never a clamp — the author just edited that
        declaration, so their default is the intended answer. Knobs the new
        class does not declare are dropped; new knobs start at their default.
        Pure and safe from any thread; `redeclare` is the write.
        """
        declarations, values, _ = self._state
        out: dict[str, float] = {}
        reset: list[str] = []
        for name, param in declared_params(pattern_cls).items():
            kept = _snap(param, values[name]) if name in values else None
            if kept is None:
                out[name] = param.default
                if name in values:
                    reset.append(name)
            else:
                out[name] = kept
        return out, reset

    def check(self, name: str, value: Any) -> str | None:
        """Why `value` would be refused for `name`, or None if it is acceptable.

        Never raises, and is the single source of every refusal wording, so a
        socket's synchronous reply and `set`'s exception can never describe the
        same rejection differently.

        Carries no file path: that is `hint`, kept separate so a refusal can be
        sent to whoever can reach the preview port without serving them the
        layout of the disk.
        """
        declarations, _, pattern = self._state
        param = declarations.get(name)
        if param is None:
            known = ", ".join(declarations) or "(none)"
            return f"{pattern} has no Param named {name!r}; declared params: {known}"
        if isinstance(value, bool):
            # float(True) is 1.0, so a JSON `true` would otherwise land as a
            # legal-looking value nobody chose.
            return f"{pattern}.{name} takes a number, got the bool {value!r}"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return f"{pattern}.{name} takes a number, got {value!r}"
        if not math.isfinite(number):
            # json.loads accepts NaN and Infinity literals by default, so both
            # arrive over the wire. Caught here for its own message: every
            # comparison with NaN is False, so the range check below would
            # report it as out of range, which reads as nonsense.
            return f"{pattern}.{name} must be a finite number, got {number}"
        if _snap(param, number) is None:
            return f"{pattern}.{name} must be within {param.lo}..{param.hi}, got {number}"
        return None

    def hint(self, name: str) -> str:
        """Where to edit the declaration, or "" when there is nothing to point at.

        Deliberately not part of `check`: the CLI wants this line and a browser
        must not receive it.
        """
        param = self.declarations.get(name)
        if param is None or param.owner is None:
            return ""
        where = source_file_of(param.owner) or param.owner.__name__
        return f"widen the {name!r} Param in {where}, or pick a value in range"

    # ---- writes (loop thread) -------------------------------------------

    def set(self, name: str, value: Any) -> bool:
        """Set one knob; returns whether the value actually changed.

        Raises ValueError if refused — that is the CLI and authoring contract.
        A caller on another thread should `check` first rather than catch this;
        see the class docstring for why that is not a style preference.
        """
        reason = self.check(name, value)
        if reason is not None:
            raise ValueError(self._refusal(name, reason))
        declarations, values, _ = self._state
        number = _snap(declarations[name], float(value))
        assert number is not None  # check() already proved it lands in range
        changed = values[name] != number
        values[name] = number
        return changed

    def set_many(self, values: Mapping[str, float]) -> list[str]:
        """Set several knobs atomically; returns the names that changed.

        Validate all, then apply, so a partial write can never leave a pattern
        running a mix of old and new values. Hot reload's `inherit` and a UI's
        "reset all" are both this, and without it each would invent its own
        partial-failure semantics.
        """
        refusals = [
            self._refusal(name, reason)
            for name, value in values.items()
            if (reason := self.check(name, value)) is not None
        ]
        if refusals:
            raise ValueError("; ".join(refusals))
        return [name for name, value in values.items() if self.set(name, value)]

    def apply(self, pattern: Pattern) -> None:
        """Materialize current values as plain floats on the pattern instance.

        Runs once per bind, before `setup`, so pattern code reads `self.speed`
        as a number. The declaration wins over anything `__init__` assigned to
        the same name.
        """
        for name, value in self._state.values.items():
            setattr(pattern, name, value)

    def redeclare(self, pattern_cls: type, values: Mapping[str, float]) -> None:
        """Become the set for `pattern_cls`, holding `values` — the write half
        of a hot reload, after `inherit` chose the values and the new pattern
        bound against them. One attribute store, so it is atomic to readers.
        Identity is preserved: a control surface holding this object keeps
        driving the live pattern.
        """
        self._state = _ParamState.of(pattern_cls, values)

    def _refusal(self, name: str, reason: str) -> str:
        hint = self.hint(name)
        return f"{reason}. {hint}" if hint else reason


class _ParamState(NamedTuple):
    """Everything a `ParamSet` holds for one pattern class, as one value."""

    declarations: dict[str, Param]
    values: dict[str, float]
    pattern: str

    @classmethod
    def of(cls, pattern_cls: type, values: Mapping[str, float] | None) -> "_ParamState":
        """The state for `pattern_cls`, at `values` or at the defaults."""
        declarations = declared_params(pattern_cls)
        if values is None:
            values = {name: param.default for name, param in declarations.items()}
        return cls(declarations, dict(values), pattern_name(pattern_cls))


def pattern_name(pattern_cls: type) -> str:
    """The display name of a pattern class: its `name` attribute, else the class name."""
    return getattr(pattern_cls, "name", None) or pattern_cls.__name__


def source_file_of(cls: type) -> Path | None:
    """The file `cls` was defined in, or None for a class with no source
    (built dynamically, REPL)."""
    try:
        file = inspect.getsourcefile(cls)
    except TypeError:
        return None
    return Path(file) if file else None


def _snap(param: Param, value: float) -> float | None:
    """`value` moved onto the declared range, or None if it is truly outside it.

    Only float noise moves. A slider stepping `lo + i*step` can land an ulp
    above `hi`, and refusing a knob dragged to its own maximum would be absurd.
    Anything further out stays refused — this is a snap, not a clamp, and the
    difference is the whole point of the range decision: a clamp would render
    one value while the surface displayed another.
    """
    if param.lo <= value <= param.hi:
        return value
    tol = (param.hi - param.lo) * _SNAP_TOL
    if param.lo - tol <= value < param.lo:
        return param.lo
    if param.hi < value <= param.hi + tol:
        return param.hi
    return None


# ---- the buffer registry (ADR-005 amendment 2026-07-27) ---------------------


@dataclass(frozen=True)
class BufferSpec:
    """What the engine remembers about a declared buffer.

    Deliberately name -> *spec*, never name -> array identity: authors
    legitimately rebind their buffers (`self.heat = np.maximum(self.heat -
    cool, 0.0)` in fire's before_render), so the engine re-reads
    `getattr(pattern, name)` fresh whenever it needs the current value.
    Identity tracking would silently stop tracking on the first rebind.

    The spec is also the unit hot reload hands buffers over by (name +
    shape, ADR-005 amendment; `Renderer.swap`).
    """

    shape: tuple[int, ...]
    dtype: np.dtype
    fill: float


def _normalize_shape(shape: int | Iterable[int]) -> tuple[int, ...]:
    if isinstance(shape, (int, np.integer)):
        return (int(shape),)
    return tuple(int(s) for s in shape)


# ---- what a new instance takes from the one it replaces ----------------------

# Instance state the engine itself sets at bind; never inherited as if it
# were the author's.
_ENGINE_ATTRS = _RESERVED_BUFFER_NAMES | {"_buffers", "_buffers_open", "_inherit"}


def _scalar_kind(value: Any) -> str | None:
    """The family a plain attribute belongs to for inheritance, or None.

    Numbers are one family: `self.phase = 0` in `__init__` and the float it
    has become after ten frames must match, or every save would reset the
    animation. `bool` is checked first because it subclasses `int`.
    """
    if isinstance(value, (bool, np.bool_)):
        return "bool"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return "number"
    if isinstance(value, str):
        return "str"
    return None


class Inheritance:
    """What a new pattern instance takes from the one it replaces (hot reload).

    Built from the old instance and handed to `_bind`, which consults it at
    the two moments that matter: plain scalar state is applied *before*
    `setup`, so anything `setup` assigns is the new code's own; and each
    buffer is taken over at the moment `self.buffer(...)` declares it, so a
    view or derived array `setup` builds from it refers to the inherited
    data. Buffers match on name and full `BufferSpec` (shape, dtype, fill)
    and are *copied* — one O(N) copy per reload, in exchange for a strong
    guarantee: a candidate whose `setup` writes into a buffer and then raises
    has touched nothing the old pattern still owns. The RNG stream continues
    from the old generator's state.

    Records what it did (`buffers`, `scalars`, `skipped`) for the reload log.
    """

    def __init__(self, old: "Pattern") -> None:
        self._arrays = {
            name: (spec, getattr(old, name, None)) for name, spec in old._buffers.items()
        }
        excluded = _ENGINE_ATTRS | set(old._buffers) | set(declared_params(type(old)))
        self._scalars: dict[str, Any] = {}
        self._rng_state = old.rng.bit_generator.state if hasattr(old, "rng") else None
        self.buffers: list[str] = []
        self.scalars: list[str] = []
        self.skipped: list[str] = []
        for name, value in vars(old).items():
            if name in excluded:
                continue
            if _scalar_kind(value) is None:
                self.skipped.append(name)
            else:
                self._scalars[name] = value

    def buffer(self, name: str, spec: BufferSpec) -> np.ndarray | None:
        """A copy of the old buffer for `name` if its spec still matches, else None."""
        old_spec, array = self._arrays.get(name, (None, None))
        if (
            old_spec == spec
            and isinstance(array, np.ndarray)
            and array.shape == spec.shape
            and array.dtype == spec.dtype
        ):
            self.buffers.append(name)
            return array.copy()
        return None

    def apply_scalars(self, new: "Pattern") -> None:
        """Set old scalar values onto `new` where `__init__` gave it the same
        name in the same family; a name declared as a `Param` on the new class
        is never touched, so a knob demoted to a constant takes the constant."""
        fresh = vars(new)
        params = declared_params(type(new))
        for name, value in self._scalars.items():
            if name in params:
                continue
            if name in fresh and _scalar_kind(fresh[name]) == _scalar_kind(value):
                setattr(new, name, value)
                self.scalars.append(name)
            else:
                self.skipped.append(name)

    def apply_rng(self, new: "Pattern") -> None:
        if self._rng_state is not None:
            new.rng.bit_generator.state = self._rng_state


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
    _inherit: Inheritance | None = None

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
        """Single allocation path, shared by `buffer()` and `self.pixels`.
        During a hot reload the inherited array takes the place of a fresh one."""
        spec = BufferSpec(_normalize_shape(shape), np.dtype(dtype), float(fill))
        array = self._inherit.buffer(name, spec) if self._inherit is not None else None
        if array is None:
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
        params: ParamSet | Mapping[str, float] | None = None,
        inherit: Inheritance | None = None,
    ) -> None:
        """Engine-side binding of this instance to one mapping.

        Order is contractual: engine state, then params (so `setup` sees final
        values), then inherited scalars and RNG state if this is a hot-reload
        swap, then the registry with `self.pixels` in it, then the author's
        `setup` with buffer declaration enabled — each declaration taking the
        inherited array when there is one. Re-binding re-runs all of it:
        buffers are reallocated and re-zeroed, the RNG is reseeded from the
        same seed, and `setup` runs again.

        `params` is the renderer's `ParamSet`; a plain mapping (or nothing) is
        accepted so a pattern can be bound directly in a test.
        """
        self.n = int(n)
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # The ParamSet owns declaration, validation and current values; this
        # only materializes them. An override naming an undeclared knob, or
        # landing outside a declared range, was already refused when the set
        # was built — both are dead knobs, and the sdf3d `spin` addendum
        # (bench/results/authoring-2026-07-16.md) is what a dead knob costs
        # when nothing refuses it.
        if not isinstance(params, ParamSet):
            params = ParamSet(type(self), params)
        params.apply(self)
        if inherit is not None:
            inherit.apply_scalars(self)
            inherit.apply_rng(self)

        self._buffers = {}
        self._inherit = inherit
        try:
            self._declare("pixels", (self.n, 3), np.float32, 0.0)
            self._buffers_open = True
            self.setup(self.n, x, y, z, index)
        finally:
            self._buffers_open = False
            self._inherit = None

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
