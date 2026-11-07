"""The JSON form that every result an agent reads shares: the lab's
(pewpew.lab) and `observe`'s (pewpew.remote.observe). A command prints it
with `--json`, and an MCP tool returns it as structured content."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from enum import Enum
from typing import Any, cast


class Result:
    """A mixin for a dataclass result: `to_json` gives one key per field, in
    field order, each value in its JSON form (`jsonable`)."""

    __slots__ = ()

    def to_json(self) -> dict[str, Any]:
        """The result as one JSON-ready object."""
        fields = dataclasses.fields(cast(Any, self))  # every subclass is a dataclass
        return {f.name: jsonable(getattr(self, f.name)) for f in fields}


def jsonable(value: Any) -> Any:
    """`value` as JSON-ready data: a value with `to_json` gives that, a
    tuple or list gives a list, a mapping a dict, an enum its value; any
    other value is itself."""
    if hasattr(value, "to_json"):
        return value.to_json()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value
