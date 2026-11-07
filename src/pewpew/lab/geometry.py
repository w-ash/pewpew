"""Where a look renders: a mapping, named by the spec that gave it.

A map spec is what `run` takes: a synthetic mapping by name (`line:64`,
`grid:16x16`, `lattice:8`; pewpew.mapping.parse_map) or a room map file
(`run --room`; pewpew.room.map).
`pewpew.mapping.DEFAULT_MAP` is the one `run` uses without `--map` or
`--room`, and the offline renders' default.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pewpew.errors import describe_exception
from pewpew.jsonfile import ProblemsError
from pewpew.mapping import dimensions, parse_map
from pewpew.room.map import load_room


@dataclass(frozen=True, slots=True, eq=False)
class Geometry:
    """A mapping, and the spec that named it."""

    spec: str
    mapping: np.ndarray

    @property
    def points(self) -> int:
        return len(self.mapping)

    @property
    def dims(self) -> int:
        """How many axes the mapping spans (pewpew.mapping.dimensions)."""
        return dimensions(self.mapping)

    @property
    def digest(self) -> str:
        """SHA-256 of the mapping's numbers: equal for two specs that give
        the same points."""
        a = np.ascontiguousarray(self.mapping)
        h = hashlib.sha256()
        h.update(f"{a.dtype.str}{a.shape}".encode())
        h.update(a.tobytes())
        return h.hexdigest()


def parse_geometry(spec: str) -> Geometry:
    """The geometry map spec `spec` names. A spec with a "/"
    or ending in ".json" is a room map file. Raises ValueError, saying why."""
    if "/" in spec or spec.endswith(".json"):
        try:
            room, _ = load_room(Path(spec))
        except (OSError, ProblemsError) as exc:
            raise ValueError(f"cannot read the room map {spec}: {describe_exception(exc)}") from None
        return Geometry(spec, room.mapping)
    try:
        return Geometry(spec, parse_map(spec))
    except ValueError:
        raise ValueError(
            f"expected line:64, grid:16x16, lattice:8 or a room map file (.json); got {spec!r}"
        ) from None

