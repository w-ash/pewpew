"""Where a look renders: a mapping, named by the spec that gave it.

A map spec is what `run` takes: a synthetic mapping by name (`line:64`,
`grid:16x16`, `lattice:8`; pewpew.mapping.parse_map) or a room map file
(`run --room`; pewpew.room.map), which brings its fixture grouping. `auto`
is the mapping `run` gives the look's bottom pattern when it has no `--map`
or `--room`: the gallery's study fixture for that pattern (`line:300` for
comet, the canopy room for pulse), else `grid:16x16`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import pewpew.patterns as gallery
from pewpew.errors import describe_exception
from pewpew.jsonfile import ProblemsError
from pewpew.mapping import Grouping, dimensions, parse_map
from pewpew.room.map import load_room

AUTO = "auto"


@dataclass(frozen=True, slots=True, eq=False)
class Geometry:
    """A mapping, its fixture grouping (None: no fixtures), and the spec
    that named it."""

    spec: str
    mapping: np.ndarray
    grouping: Grouping | None = None

    @property
    def points(self) -> int:
        return len(self.mapping)

    @property
    def dims(self) -> int:
        """How many axes the mapping spans (pewpew.mapping.dimensions)."""
        return dimensions(self.mapping)

    @property
    def digest(self) -> str:
        """SHA-256 of the mapping's and the grouping's numbers: equal for
        two specs that give the same points."""
        h = hashlib.sha256()
        arrays = [self.mapping] if self.grouping is None else [self.mapping, self.grouping.centres, self.grouping.of]
        for array in arrays:
            a = np.ascontiguousarray(array)
            h.update(f"{a.dtype.str}{a.shape}".encode())
            h.update(a.tobytes())
        return h.hexdigest()


def parse_geometry(spec: str) -> Geometry:
    """The geometry map spec `spec` names; not `auto`. A spec with a "/"
    or ending in ".json" is a room map file. Raises ValueError, saying why."""
    if "/" in spec or spec.endswith(".json"):
        try:
            room, _ = load_room(Path(spec))
        except (OSError, ProblemsError) as exc:
            raise ValueError(f"cannot read the room map {spec}: {describe_exception(exc)}") from None
        return Geometry(spec, room.mapping, room.grouping)
    try:
        return Geometry(spec, parse_map(spec))
    except ValueError:
        raise ValueError(
            f"expected auto, line:64, grid:16x16, lattice:8 or a room map file (.json); got {spec!r}"
        ) from None


def auto_geometry(bottom: type) -> Geometry:
    """The geometry `run` gives pattern class `bottom` without `--map` or
    `--room` (module docstring)."""
    mapping, grouping = gallery.default_geometry(bottom)
    return Geometry(AUTO, mapping, grouping)
