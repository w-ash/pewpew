"""`ParamSet`: the declared params of one class and their values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple

from pewpew.classinfo import lowercase_name
from pewpew.errors import unknown
from pewpew.params.bound import Bound
from pewpew.params.kinds import Param, Parsed


def declared_params(cls: type) -> dict[str, Param[Any]]:
    """Every param declared on `cls` or inherited, in display order.

    Two orderings, deliberately different. *Which* declaration supplies a name
    is most-derived-wins, so a subclass can retune a base's param.
    *Iteration* is base-first, so a subclass adding params appends to a
    stable prefix rather than reshuffling the row above it. That order is
    what a control surface lays controls out in, so it is a contract with a
    test on it.
    """
    found: dict[str, Param[Any]] = {}
    for base in reversed(cls.__mro__):
        for name, value in vars(base).items():
            if isinstance(value, Param):
                found[name] = value  # dict keeps the first insertion's position
    return found


class ParamSet:
    """The declared params of one class (an op, a layer's mix), plus their
    current values.

    Values are native (`float`, `int`, `bool`, `str`, `HSV`, `Gradient`).
    `parse` and every write take native or JSON values; `snapshot_json`
    gives JSON values. A refusal names a param by its path, `owner.name`.

    One write path. `apply(target)` binds the set to the object that reads
    its values (`Bound`); from then on every `set` reaches the target too,
    so the set and the object that reads it never disagree. The set holds the
    base values: a driven param's target reads its base moved by an offset
    (`Bound.drive`). A set that was never applied only holds values.

    Threading. `parse`, `check`, the snapshots and `describe` are safe from
    any thread. `set` and `apply` belong to the loop thread, so
    a value never changes mid-frame; reach them through
    `pewpew.pace.Calls.call_soon` after `parse` passes (a queued closure
    that raises ends the run).
    """

    def __init__(
        self, owner_cls: type, overrides: Mapping[str, Any] | None = None, *, name: str | None = None
    ) -> None:
        """`name` is the owner a refusal names, a dotted path where the owner
        is nested (`layers.base.fold`): by default the class's name, lowercased."""
        self._state = _ParamState.of(owner_cls, None, name or lowercase_name(owner_cls))
        if overrides:
            self.set_many(overrides)

    # One tuple, replaced in a single attribute store, so a reader on
    # another thread can never pair a new binding with old values. Every
    # reader takes `self._state` once and works from it.

    @property
    def declarations(self) -> dict[str, Param[Any]]:
        return self._state.declarations

    @property
    def owner(self) -> str:
        """The path a refusal puts before a param's name."""
        return self._state.owner

    @property
    def bound(self) -> Bound | None:
        """The link to the target every write reaches, or None before `apply`."""
        return self._state.bound

    # ---- reads (any thread) --------------------------------------------

    def __getitem__(self, name: str) -> Any:
        return self._state.values[name]

    def __contains__(self, name: object) -> bool:
        return name in self._state.values

    def __iter__(self):
        return iter(self._state.values)

    def __len__(self) -> int:
        return len(self._state.values)

    def __repr__(self) -> str:
        state = self._state
        return f"ParamSet({state.owner}, {state.values})"

    def snapshot(self) -> dict[str, Any]:
        """Current native values; round-trips back in as `overrides`."""
        return dict(self._state.values)

    def snapshot_json(self) -> dict[str, Any]:
        """Current values in their JSON form: what is stored and compared."""
        state = self._state
        return {name: param.to_json(state.values[name]) for name, param in state.declarations.items()}

    def describe(self) -> list[dict[str, Any]]:
        """Each param's `spec()`, in display order. A list, not a dict, so
        display order survives transport. `snapshot_json` gives the values."""
        return [param.spec() for param in self._state.declarations.values()]

    def parse(self, name: str, value: object) -> Parsed[Any]:
        """`value` as `name`'s native value, or why it is refused.

        Never raises, and is the single source of every refusal wording, so
        a socket's synchronous reply and `set`'s exception can never
        describe the same rejection differently.
        """
        state = self._state
        param = state.declarations.get(name)
        if param is None:
            return None, f"{state.owner}: {unknown('param', name, state.declarations)}"
        return param.parse(f"{state.owner}.{name}", value)

    def check(self, name: str, value: object) -> str | None:
        """Why `value` would be refused for `name`, or None. Never raises."""
        return self.parse(name, value)[1]

    # ---- writes (loop thread) -------------------------------------------

    def set(self, name: str, value: object) -> bool:
        """Set one param; returns whether the value actually changed.

        Raises ValueError if refused — that is the CLI and authoring
        contract. A caller on another thread should `parse` first rather
        than catch this; see the class docstring.
        """
        return bool(self.set_many({name: value}))

    def set_many(self, values: Mapping[str, Any]) -> list[str]:
        """Set several params atomically, on the target too; returns the
        names that changed.

        Validate all, then apply, so a partial write can never leave an
        op running a mix of old and new values.
        """
        parsed = {name: self.parse(name, value) for name, value in values.items()}
        refusals = [reason for _, reason in parsed.values() if reason is not None]
        if refusals:
            raise ValueError("; ".join(refusals))
        state = self._state
        changed = [name for name, (value, _) in parsed.items() if state.values[name] != value]
        for name, (value, _) in parsed.items():
            state.values[name] = value
            if state.bound is not None:
                state.bound.write(name)
        return changed

    def apply(self, target: object) -> Bound:
        """Bind the set to `target`: set every value on it as an instance
        attribute, and make it the target every later `set` writes. Returns
        the binding.

        An op then reads `self.speed` as a plain value. The declaration
        wins over anything `__init__` assigned to the same name. Applying
        again to the same target (a rebind) keeps the binding and its
        drives; another target gets a new binding, and the old one stops
        working.
        """
        bound = self._state.bound
        if bound is None or bound.target is not target:
            bound = Bound(self, target)
            self._state = self._state._replace(bound=bound)
        for name in self._state.values:
            bound.write(name)
        return bound


class _ParamState(NamedTuple):
    """Everything a `ParamSet` holds for one class, as one value: `bound`
    links the set to the target `set` writes, or is None before `apply`."""

    declarations: dict[str, Param[Any]]
    values: dict[str, Any]
    owner: str
    bound: Bound | None = None

    @classmethod
    def of(cls, owner_cls: type, values: Mapping[str, Any] | None, owner: str) -> _ParamState:
        """The state for `owner_cls`, named `owner`, at `values` or at the defaults."""
        declarations = declared_params(owner_cls)
        if values is None:
            values = {name: param.default for name, param in declarations.items()}
        return cls(declarations, dict(values), owner)
