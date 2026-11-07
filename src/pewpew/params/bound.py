"""`Bound`: a `ParamSet` bound to the object that reads its values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from pewpew.errors import unknown
from pewpew.params.kinds import Color, Param, Parsed, Ranged

if TYPE_CHECKING:
    from pewpew.params.paramset import ParamSet


def drive_range(param: Param[Any], where: str, part: str = "") -> Parsed[Ranged[Any]]:
    """The ranged declaration a drive of `param` moves: the param itself,
    or the color's `part`; or why it cannot be modulated (ADR-006). `where`
    is the param's path (`layers.base.tint.color`). Never raises."""
    path = f"{where}.{part}" if part else where
    if isinstance(param, Color):
        if part not in param.parts:
            name = where.rpartition(".")[2]
            parts = ", ".join(f"{name}.{p}" for p in param.parts)
            return None, f"{path} cannot be modulated: drive one of the color's parts, {parts}"
        return param.parts[part], None
    if not isinstance(param, Ranged):
        return None, f"{path} cannot be modulated: it is a {param.kind}; only a float, an int or a color's part can be"
    if part:
        return None, f"{where} is a {param.kind}, which has no part {part!r}"
    return param, None


class Bound:
    """The link from a `ParamSet` to its target, the object that reads each
    value as an attribute (an op, a layer's mix).

    The target's attribute is the param's base value, or, while the param
    is driven, the base moved by an offset in plain units (ADR-006). The
    base stays in the set, so a control and a saved look see the
    operator's value, never the modulated one.

    Made by `ParamSet.apply` and kept as `ParamSet.bound`; every write to
    the set reaches the target through `write`. A rebind to the same target
    keeps the binding and its drives. Only the set's current binding acts:
    after the set binds another target, or for a Bound built directly, each
    call raises RuntimeError. A path is a param's name, or `name.part` for
    a color's part (`color.h`). Loop thread only, as `ParamSet.set` is.
    """

    __slots__ = ("_offsets", "params", "target")

    def __init__(self, params: ParamSet, target: object) -> None:
        self.params = params
        self.target = target
        # The offset of each driven path: by param name, then by part, "" for the whole param.
        self._offsets: dict[str, dict[str, float]] = {}

    def set(self, name: str, value: object) -> bool:
        """Set the base value of `name`; returns whether it changed. Raises
        ValueError if refused (`ParamSet.set`)."""
        self._check_current()
        return self.params.set(name, value)

    def drive(self, path: str, offset: float) -> None:
        """Move `path` by `offset` on the target only: the base stays, and a
        later `set` moves the base under the same offset. Raises ValueError
        for a path the set does not declare or an offset that is not
        finite, and TypeError for a param that cannot be modulated."""
        self._check_current()
        name, part = self._modulatable(path)
        offsets = {**self._offsets.get(name, {}), part: float(offset)}
        value = self._moved(name, offsets)  # raises before anything changes
        self._offsets[name] = offsets
        setattr(self.target, name, value)

    def undrive(self, path: str) -> None:
        """Stop driving `path`: the target reads its base again."""
        self._check_current()
        name, _, part = path.partition(".")
        offsets = self._offsets.get(name, {})
        if part in offsets:
            del offsets[part]
            if not offsets:
                del self._offsets[name]
            self.write(name)

    def settle(self) -> None:
        """Stop driving every path: the target reads every base again."""
        self._check_current()
        driven, self._offsets = self._offsets, {}
        for name in driven:
            self.write(name)

    def write(self, name: str) -> None:
        """Set the target's `name` to `value(name)`."""
        setattr(self.target, name, self.value(name))

    def value(self, name: str) -> Any:
        """What the target reads for `name`: the base, moved by the offset of
        each driven path."""
        self._check_current()
        return self._moved(name, self._offsets.get(name, {}))

    def _check_current(self) -> None:
        """Raise RuntimeError unless this is the set's binding."""
        if self.params.bound is not self:
            raise RuntimeError(
                f"{self.params.owner}: this Bound is not the set's binding; "
                "use ParamSet.bound, or bind with ParamSet.apply(target)"
            )

    def _moved(self, name: str, offsets: Mapping[str, float]) -> Any:
        """The base value of `name` moved by `offsets`, by part."""
        base = self.params[name]
        if not offsets:
            return base
        param = self.params.declarations[name]
        if isinstance(param, Color):
            moved = {part: param.parts[part].modulate(getattr(base, part), x) for part, x in offsets.items()}
            return replace(base, **moved)
        assert isinstance(param, Ranged)
        return param.modulate(base, offsets[""])

    def _modulatable(self, path: str) -> tuple[str, str]:
        """`path` as (name, part), or why it cannot be driven: ValueError
        for a name or part the set does not have, TypeError for a kind
        that cannot be modulated."""
        owner = self.params.owner
        name, _, part = path.partition(".")
        param = self.params.declarations.get(name)
        if param is None:
            raise ValueError(f"{owner}: {unknown('param', name, self.params.declarations)}")
        _, reason = drive_range(param, f"{owner}.{name}", part)
        if reason is not None:
            raise (ValueError if isinstance(param, Ranged) else TypeError)(reason)
        return name, part
