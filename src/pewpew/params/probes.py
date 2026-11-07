"""Probe pairs from describe records: two values of one param that must
render differently (the liveness method, tests/test_param_liveness.py).

Read from `ParamSet.describe()` records, not from the declarations, so a
probe uses only what any control surface sees. Each pair is (id, a, b) with
JSON values, its id the param's name or the part or option it moves:

- float and int: `lo` against `hi`, or `lo` against the midpoint when the
  range is periodic (its ends are the same point);
- bool: false against true;
- choice: the first option against each of the others (`name=option`);
- color: each part (h, s, v) on its own, the others at the default or
  at a value given (`name.part`);
- palette: the default against each preset that differs from it
  (`name=label`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

Record = Mapping[str, Any]
Probe = tuple[str, Any, Any]
# A numeric leaf of a record: its id, its numeric record, and how to build
# the record's value with the leaf set to a number.
Leaf = tuple[str, Record, Callable[[Any], Any]]


def leaves(record: Record, at: Any = None) -> list[Leaf]:
    """The numeric leaves of a record: the record itself for float and int,
    each part for color, none for the other kinds. A part's value keeps the
    other parts as `at` has them, a value of the param (default: the
    record's default)."""
    name, kind = record["name"], record["kind"]
    if kind in ("float", "int"):
        return [(name, record, lambda x: x)]
    if kind == "color":
        base = record["default"] if at is None else at
        return [
            (f"{name}.{part}", spec, lambda x, part=part: {**base, part: x})
            for part, spec in record["parts"].items()
        ]
    if kind in ("bool", "choice", "palette"):
        return []
    raise ValueError(f"no leaves for kind {kind!r}")


def span(spec: Record) -> tuple[Any, Any]:
    """Two values of a numeric record that are not the same point."""
    lo, hi = spec["lo"], spec["hi"]
    if not spec["periodic"]:
        return lo, hi
    mid = lo + (hi - lo) / 2
    return lo, (int(mid) if isinstance(lo, int) else mid)  # an int's ends are ints


def probes(record: Record, at: Any = None) -> list[Probe]:
    """The probe pairs for one describe record; a color part's pair keeps
    the other parts as `at` has them (`leaves`). Raises ValueError for a
    palette with nothing to probe it against."""
    name, kind = record["name"], record["kind"]
    if kind == "bool":
        return [(name, False, True)]
    if kind == "choice":
        first, *others = (option["value"] for option in record["options"])
        return [(f"{name}={other}", first, other) for other in others]
    if kind == "palette":
        default = record["default"]
        out = [(f"{name}={p['label']}", default, p["value"]) for p in record["presets"] if p["value"] != default]
        if not out:
            raise ValueError(f"palette {name!r} offers no preset other than its default, so nothing probes it")
        return out
    out: list[Probe] = []
    for leaf, spec, value in leaves(record, at):
        a, b = span(spec)
        out.append((leaf, value(a), value(b)))
    return out
