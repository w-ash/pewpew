"""The param kinds: `Float`, `Int`, `Bool`, `Choice`, `Color` and `Palette`.

A param is a class attribute of a pattern:

    speed = Float(0.4, 0.0, 2.0, "/s", label="Speed")
    color = Color((200.0, 1.0, 1.0))

Each kind parses a value (native or JSON) and never raises while it does,
so one method gives both the value and the refusal wording. `spec()` is the
JSON record a control surface builds its control from. A `Float` or `Int`
can be modulated (`modulate`); the other kinds cannot (ADR-006).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from numbers import Integral, Real
from typing import Any, ClassVar, Generic, Self, TypeVar, cast, overload

from pewpew.errors import unknown
from pewpew.params.values import HSV, Gradient, Stop

T = TypeVar("T")
N = TypeVar("N", int, float)

# A parse result: the value and None, or None and why the value is refused.
Parsed = tuple[T, None] | tuple[None, str]

# The largest whole number a browser's JSON reader holds exactly.
_SAFE_INT = 2**53 - 1


def _pairs(mapping: Mapping[Any, str]) -> list[dict[str, Any]]:
    """`mapping` as the wire's `[{"value", "label"}]` list."""
    return [{"value": value, "label": label} for value, label in mapping.items()]


class Param(ABC, Generic[T]):
    """The base of every kind: a declared, typed, user-settable value of a
    pattern.

    A non-data descriptor. Before bind, `self.x` reads the default. At bind
    `ParamSet.apply` sets the instance attribute, which shadows the
    descriptor, so a frame reads a plain attribute with no indirection.

    `label` captions the control (default: the name, spaced and
    capitalized), `help` explains it, `group` places it with others on a
    surface (layout only, never part of an id), and `widget` asks for a
    control other than the kind's default one, one of the kind's `widgets`.
    """

    kind: ClassVar[str]
    native: ClassVar[type]
    widgets: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        default: Any,
        *,
        label: str = "",
        help: str = "",
        group: str = "",
        widget: str = "",
    ) -> None:
        if widget and widget not in self.widgets:
            offered = ", ".join(sorted(self.widgets)) or "none"
            raise ValueError(f"{type(self).__name__} has no widget {widget!r}; its widgets: {offered}")
        self.label, self.help, self.group, self.widget = label, help, group, widget
        # Filled by __set_name__, which runs only for a param assigned in a
        # class body; every reader tolerates the blank.
        self.name: str = ""
        self.owner: type | None = None
        self._spec: dict[str, Any] | None = None
        value, reason = self.parse("default", default)
        if reason is not None:
            raise ValueError(f"bad {type(self).__name__} declaration: {reason}")
        self.default: T = value  # type: ignore[assignment]

    def __set_name__(self, owner: type, name: str) -> None:
        self.name, self.owner, self._spec = name, owner, None
        if not self.label:
            self.label = name.replace("_", " ").capitalize()

    @overload
    def __get__(self, obj: None, owner: type | None = None) -> Self: ...
    @overload
    def __get__(self, obj: object, owner: type | None = None) -> T: ...
    def __get__(self, obj: object, owner: type | None = None) -> Self | T:
        return self if obj is None else self.default

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name or '?'}, default={self.default!r})"

    @abstractmethod
    def parse(self, where: str, value: object) -> Parsed[T]:
        """`value` as this kind's native value, or why it is refused.

        Takes the native value or its JSON form. Never raises. `where`
        starts the refusal, for example "pulse.color".
        """

    def to_json(self, value: T) -> object:
        """`value` in its JSON form."""
        return value

    def spec(self) -> dict[str, Any]:
        """The JSON declaration record a control surface builds from.
        Built once: a declaration does not change after its class is made."""
        if self._spec is None:
            self._spec = {
                "name": self.name,
                "kind": self.kind,
                "label": self.label,
                "help": self.help,
                "group": self.group,
                "widget": self.widget,
                "default": self.to_json(self.default),
                **self._extra(),
            }
        return dict(self._spec)

    def _extra(self) -> dict[str, Any]:
        """The fields this kind adds to `spec()`."""
        return {}


class Ranged(Param[N]):
    """A number on a closed range, `lo` to `hi`: `Kind(default, lo, hi, unit)`.

    The range is a contract: a value outside it is refused, never clamped,
    so a surface can trust that the endpoints bound every value the engine
    renders. Float noise just past an endpoint snaps onto it.

    `unit` is a short symbol ("°", "s", "/s", "Hz"). `periodic` says `lo`
    and `hi` are the same point (an angle). `text` names special values,
    for example `{0: "hold"}`. `widget="angle"` asks for a dial, and needs
    the range 0 to 360 and `periodic=True`.

    Two hints are for a generator of looks, never a limit on a value
    (ADR-022 amendment "generation hints"): `sweet` is the part of the
    range where the knob looks best, `(lo, hi)` when not given, and
    `flash_sensitive` says a fast change of the knob changes brightness at
    a point, so a generator keeps a route on it shallow.
    """

    # How far outside its range a value may land and still be read as float
    # noise rather than a mistake, as a fraction of the range's own width.
    snap_tol: ClassVar[float] = 0.0

    def __init__(
        self,
        default: N,
        lo: N,
        hi: N,
        unit: str = "",
        *,
        periodic: bool = False,
        text: Mapping[float, str] | None = None,
        sweet: tuple[N, N] | None = None,
        flash_sensitive: bool = False,
        **meta: Any,
    ) -> None:
        lo, hi = self._ends(lo, hi)
        if lo >= hi:
            raise ValueError(
                f"param range must have lo < hi, got {lo}..{hi} — a param that cannot move is dead by construction"
            )
        if meta.get("widget") == "angle" and "angle" in self.widgets and ((lo, hi) != (0, 360) or not periodic):
            raise ValueError(f"an angle widget needs the range 0..360 and periodic=True, got {lo}..{hi}"
                             f"{'' if periodic else ', not periodic'}")
        self.lo, self.hi, self.unit, self.periodic = lo, hi, unit, periodic
        self.text: dict[N, str] = {}
        if text:
            for value, label in text.items():
                number, reason = self.parse("text", value)
                if reason is not None:
                    raise ValueError(f"bad {type(self).__name__} declaration: {reason}")
                self.text[number] = label  # type: ignore[index]
        self.sweet: tuple[N, N] = (lo, hi) if sweet is None else self._sweet(sweet)
        self.flash_sensitive = flash_sensitive
        super().__init__(default, **meta)

    def _sweet(self, ends: tuple[N, N]) -> tuple[N, N]:
        """`ends` as a sweet range: two values in range, the first below the
        second. Raises ValueError otherwise."""
        parsed = [self.parse("sweet", end) for end in ends]
        reasons = [reason for _, reason in parsed if reason is not None]
        if reasons or len(parsed) != 2:
            raise ValueError(f"bad {type(self).__name__} declaration: {'; '.join(reasons) or 'sweet is (lo, hi)'}")
        a, b = (value for value, _ in parsed)
        assert a is not None and b is not None
        if a >= b:
            raise ValueError(f"bad {type(self).__name__} declaration: sweet must have lo < hi, got {a}..{b}")
        return a, b

    def parse(self, where: str, value: object) -> Parsed[N]:
        if isinstance(value, bool):
            # float(True) is 1.0, so a JSON `true` would otherwise land as a
            # legal-looking value nobody chose.
            return None, f"{where} takes a number, got the bool {value!r}"
        number, reason = self._coerce(where, value)
        if reason is not None:
            return None, reason
        assert number is not None
        snapped = self._snap(number)
        if snapped is None:
            return None, f"{where} must be within {self.lo}..{self.hi}, got {number}"
        return snapped, None

    @abstractmethod
    def _ends(self, lo: N, hi: N) -> tuple[N, N]:
        """The declared range as this kind's number type. Raises ValueError
        for ends the kind cannot hold."""

    @abstractmethod
    def _coerce(self, where: str, value: object) -> Parsed[N]:
        """`value` as this kind's number type, or why it is not one it holds."""

    def _snap(self, value: N) -> N | None:
        """`value` moved onto the range, or None if it is truly outside it.

        Only float noise moves: a slider stepping `lo + i*step` can land an
        ulp above `hi`. This is a snap, not a clamp.
        """
        if self.lo <= value <= self.hi:
            return value
        if not self.snap_tol:
            return None
        tol = (self.hi - self.lo) * self.snap_tol
        if self.lo - tol <= value < self.lo:
            return self.lo
        if self.hi < value <= self.hi + tol:
            return self.hi
        return None

    def modulate(self, base: N, offset: float) -> N:
        """`base` moved by `offset` in this param's units, kept in range
        (ADR-006): wrapped into `lo` up to `hi` when periodic, else clamped
        to `lo`..`hi`. An `Int` rounds half up. `base` is the operator's
        value, so it is in range; raises ValueError for an offset that is
        not finite."""
        if not math.isfinite(offset):
            raise ValueError(f"a modulation offset must be a finite number, got {offset}")
        span = self.hi - self.lo
        # Reduced first, so the sum stays finite: past a whole span, a
        # periodic offset repeats and any other saturates.
        offset = offset % span if self.periodic else min(max(offset, -span), span)
        value = self._nearest(base + offset)
        if not self.periodic:
            return min(max(value, self.lo), self.hi)
        if self.lo <= value < self.hi:
            return value  # untouched: the wrap below rounds a value far smaller than `lo`
        wrapped = self.lo + (value - self.lo) % span
        return wrapped if wrapped < self.hi else self.lo  # float noise can land on `hi`, the same point as `lo`

    @abstractmethod
    def _nearest(self, value: float) -> N:
        """The value of this kind's number type nearest `value`."""

    @property
    def step(self) -> float:
        """Control granularity: 1 for an `Int`; for a `Float`, about 200
        divisions of the range snapped to a 1/2/5 decade so the steps are
        round numbers. Derived, so every surface quantizes the same way."""
        if self.native is int:
            return 1
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

    def _extra(self) -> dict[str, Any]:
        return {**_number(self), "sweet": list(self.sweet), "flash_sensitive": self.flash_sensitive}


def _number(p: Ranged[Any]) -> dict[str, Any]:
    """The numeric fields of a record: a `Float` or `Int`, or a part."""
    return {
        "unit": p.unit, "lo": p.lo, "hi": p.hi, "step": p.step,
        "decimals": p.decimals, "periodic": p.periodic, "text": _pairs(p.text),
    }


def _part_records(parts: Mapping[str, Float]) -> dict[str, dict[str, Any]]:
    """The records of a compound value's parts, by name: each part's label and numeric fields."""
    return {name: {"label": part.label, **_number(part)} for name, part in parts.items()}


class Float(Ranged[float]):
    """A real number from `lo` to `hi`: `Float(default, lo, hi, unit)`."""

    kind = "float"
    native = float
    widgets = frozenset({"angle"})
    snap_tol = 1e-9

    def _ends(self, lo: float, hi: float) -> tuple[float, float]:
        lo, hi = float(lo), float(hi)
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise ValueError(f"param range must be finite, got {lo}..{hi}")
        return lo, hi

    def _coerce(self, where: str, value: object) -> Parsed[float]:
        if not isinstance(value, Real):
            return None, f"{where} takes a number, got {value!r}"
        try:
            number = float(value)
        except OverflowError:  # a JSON integer past float's range
            return None, f"{where} must be a finite number, got a number too large"
        if not math.isfinite(number):
            # json.loads accepts NaN and Infinity literals by default, so both
            # arrive over the wire. Every comparison with NaN is False, so the
            # range check would report it as out of range.
            return None, f"{where} must be a finite number, got {number}"
        return number, None

    def _nearest(self, value: float) -> float:
        return value


class Int(Ranged[int]):
    """A whole number from `lo` to `hi`: `Int(default, lo, hi, unit)`."""

    kind = "int"
    native = int

    def _ends(self, lo: int, hi: int) -> tuple[int, int]:
        for end in (lo, hi):
            if isinstance(end, bool) or not isinstance(end, Integral):
                raise TypeError(f"an Int range is whole numbers, got {lo}..{hi}")
            if abs(int(end)) > _SAFE_INT:
                raise ValueError(f"an Int range is within ±{_SAFE_INT}, which a page holds exactly")
        return int(lo), int(hi)

    def _coerce(self, where: str, value: object) -> Parsed[int]:
        if not isinstance(value, Integral):
            return None, f"{where} takes a whole number, got {value!r}"
        if abs(int(value)) > _SAFE_INT:  # past what a page holds exactly; not echoed, it may run to thousands of digits
            return None, f"{where} must be within {self.lo}..{self.hi}, got a number too large"
        return int(value), None

    def _nearest(self, value: float) -> int:
        return math.floor(value + 0.5)


class Bool(Param[bool]):
    """On or off: `Bool(default)`."""

    kind = "bool"
    native = bool

    def parse(self, where: str, value: object) -> Parsed[bool]:
        if not isinstance(value, bool):
            return None, f"{where} takes true or false, got {value!r}"
        return value, None


class Choice(Param[str]):
    """One of a fixed set of keys: `Choice(default, options)`.

    `options` is a sequence of keys, or a mapping of key to label. The value
    is the key, never an index.
    """

    kind = "choice"
    native = str

    def __init__(self, default: str, options: Sequence[str] | Mapping[str, str], **meta: Any) -> None:
        self.options: dict[str, str] = (
            dict(options) if isinstance(options, Mapping) else {key: key for key in options}
        )
        if len(self.options) < 2:
            raise ValueError(f"a Choice needs at least 2 options, got {list(self.options)}")
        if not all(isinstance(key, str) and key for key in cast("Iterable[object]", self.options)):
            raise ValueError(f"Choice options are non-empty text keys, got {list(self.options)}")
        super().__init__(default, **meta)

    def parse(self, where: str, value: object) -> Parsed[str]:
        if not isinstance(value, str) or value not in self.options:
            known = ", ".join(repr(key) for key in self.options)
            return None, f"{where} takes one of {known}, got {value!r}"
        return value, None

    def _extra(self) -> dict[str, Any]:
        return {"options": _pairs(self.options)}


class Color(Param[HSV]):
    """A color: `Color((h, s, v))` or `Color(HSV(h, s, v))`, read as an `HSV`.

    Three parts, each a `Float` named after an `HSV` field: `h` in degrees
    (0 to 360, periodic), `s` and `v` from 0 to 1. Its JSON form is
    `{"h", "s", "v"}`.
    """

    kind = "color"
    native = HSV

    def __init__(self, default: tuple[float, float, float] | HSV, **meta: Any) -> None:
        h, s, v = (default.h, default.s, default.v) if isinstance(default, HSV) else default
        self.parts: dict[str, Float] = {
            "h": Float(h, 0.0, 360.0, "°", periodic=True, label="Hue"),
            "s": Float(s, 0.0, 1.0, label="Saturation"),
            "v": Float(v, 0.0, 1.0, label="Brightness"),
        }
        for name, part in self.parts.items():
            part.name = name
        super().__init__(HSV(h, s, v), **meta)

    def parse(self, where: str, value: object) -> Parsed[HSV]:
        if isinstance(value, HSV):
            value = self.to_json(value)
        fields = cast("Mapping[object, object]", value) if isinstance(value, Mapping) else None
        if fields is None or set(fields) != set(self.parts):
            return None, f"{where} takes a color {{h, s, v}}, got {value!r}"
        parts: dict[str, float] = {}
        for name, part in self.parts.items():
            parsed, reason = part.parse(f"{where}.{name}", fields[name])
            if reason is not None:
                return None, reason
            assert parsed is not None
            parts[name] = parsed
        return HSV(**parts), None

    def to_json(self, value: HSV) -> dict[str, float]:
        return {name: getattr(value, name) for name in self.parts}

    def _extra(self) -> dict[str, Any]:
        return {"parts": _part_records(self.parts)}


class Palette(Param[Gradient]):
    """A gradient: `Palette(default, presets=...)`, read as a `Gradient`.

        from pewpew.color import EMBER, PRESETS
        palette = Palette(EMBER, presets=PRESETS)

    A stop is a position `at` from 0 to 1 and a color whose parts are a
    `Color`'s, checked and refused the same way. A palette has 2 to
    `max_stops` stops in order of `at`, the first at 0 and the last at 1,
    so one gradient has one form. `presets` are labeled gradients that a
    control offers to pick, held by label; a preset's label parses as the
    preset, so a stored value always holds its stops. Its JSON form is
    `{"label", "stops": [{"at", "h", "s", "v"}, ...]}`; `label` may be left
    out and reads as "".
    """

    kind = "palette"
    native = Gradient
    max_stops: ClassVar[int] = 16
    max_label: ClassVar[int] = 64

    def __init__(self, default: Gradient | str, *, presets: Iterable[Gradient] = (), **meta: Any) -> None:
        self._at = Float(0.0, 0.0, 1.0, label="Position")
        self._at.name = "at"
        self._color = Color((0.0, 0.0, 1.0))
        self._stop_parts: dict[str, Float] = {"at": self._at, **self._color.parts}
        listed = tuple(presets)
        self.presets: dict[str, Gradient] = {preset.label: preset for preset in listed}
        if "" in self.presets or len(self.presets) != len(listed):
            raise ValueError(f"Palette presets need distinct, non-empty labels, got {[p.label for p in listed]}")
        for label, preset in self.presets.items():
            if (reason := self.parse(f"preset {label!r}", preset)[1]) is not None:
                raise ValueError(f"bad Palette declaration: {reason}")
        super().__init__(default, **meta)

    def parse(self, where: str, value: object) -> Parsed[Gradient]:
        if isinstance(value, str):
            preset = self.presets.get(value)
            if preset is None:
                return None, f"{where}: {unknown('preset', value, self.presets)}"
            return preset, None
        if isinstance(value, Gradient):
            fields: Mapping[object, object] | None = {"label": value.label, "stops": value.stops}
        else:
            fields = cast("Mapping[object, object]", value) if isinstance(value, Mapping) else None
        stops = fields.get("stops") if fields is not None else None
        if fields is None or not set(fields) <= {"label", "stops"} or not isinstance(stops, list | tuple):
            named = f"a preset name ({', '.join(self.presets)}) or " if self.presets else ""
            shape = '{"stops": [{"at", "h", "s", "v"}, ...]} with an optional "label"'
            return None, f"{where} takes {named}{shape}, got {value!r}"
        label = fields.get("label", "")
        if not isinstance(label, str):
            return None, f"{where}.label takes text, got {label!r}"
        if len(label) > self.max_label:
            return None, f"{where}.label takes at most {self.max_label} characters, got {len(label)}"
        stops = cast("Sequence[object]", stops)
        if not 2 <= len(stops) <= self.max_stops:
            return None, f"{where}.stops takes 2 to {self.max_stops} stops, got {len(stops)}"
        parsed: list[Stop] = []
        for i, raw in enumerate(stops):
            stop, reason = self._stop(f"{where}.stops[{i}]", raw)
            if reason is not None:
                return None, reason
            assert stop is not None
            if not parsed and stop.at != 0.0:
                return None, f"{where}.stops[0].at must be 0.0, where a gradient starts, got {stop.at}"
            if parsed and stop.at < parsed[-1].at:
                before = parsed[-1].at
                return None, f"{where}.stops[{i}].at must be at least {before}, the stop before it, got {stop.at}"
            parsed.append(stop)
        if parsed[-1].at != 1.0:
            return None, f"{where}.stops[{len(parsed) - 1}].at must be 1.0, where a gradient ends, got {parsed[-1].at}"
        return Gradient(tuple(parsed), label), None

    def _stop(self, where: str, value: object) -> Parsed[Stop]:
        """One stop from its native or JSON form, or why it is refused."""
        if isinstance(value, Stop):
            color = cast("object", value.color)  # a Stop's fields are not checked when it is made
            if not isinstance(color, HSV):
                return None, f"{where}.color takes an HSV(h, s, v), got {color!r}"
            value = {"at": value.at, **self._color.to_json(color)}
        fields = cast("Mapping[object, object]", value) if isinstance(value, Mapping) else None
        if fields is None or set(fields) != set(self._stop_parts):
            return None, f"{where} takes a stop {{at, h, s, v}}, got {value!r}"
        at, reason = self._at.parse(f"{where}.at", fields["at"])
        if reason is not None:
            return None, reason
        color, reason = self._color.parse(where, {name: fields[name] for name in self._color.parts})
        if reason is not None:
            return None, reason
        assert at is not None and color is not None
        return Stop(at, color), None

    def to_json(self, value: Gradient) -> dict[str, Any]:
        stops = [{"at": stop.at, **self._color.to_json(stop.color)} for stop in value.stops]
        return {"label": value.label, "stops": stops}

    def _extra(self) -> dict[str, Any]:
        return {
            "stop": _part_records(self._stop_parts),
            "max_stops": self.max_stops,
            "presets": [{"value": self.to_json(preset), "label": label} for label, preset in self.presets.items()],
        }
