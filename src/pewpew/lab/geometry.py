"""Where a look renders: a mapping, named by the spec that gave it.

A map spec is what `run --map`, the `fx` verbs and the MCP tools take: a
synthetic mapping by name (`line:64`, `grid:16x16`, `lattice:8`;
pewpew.mapping.parse_map) or a rig file, a spec with a "/" or ending in
".json" (`is_file_spec`). A rig file is an arrangement, told by its
`format` field; a room map file, the older format, is migrated in memory
with a warning (pewpew.rig.runtime). `parse_geometry` is the one parser of
a map spec. `pewpew.mapping.DEFAULT_MAP` is the one `run` uses without
`--map`, and the offline renders' default.

The rig stack (pydantic) is imported only for a rig file, so a run or a
render on a synthetic map never loads it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from pewpew.mapping import dimensions, parse_map

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

SPEC_RULE = "line:64, grid:16x16, lattice:8 or an arrangement file (.json)"


@dataclass(frozen=True, slots=True, eq=False)
class Geometry:
    """A mapping, and the spec that named it. For a rig file, `rig` is the
    compiled rig and `data` the file's bytes."""

    spec: str
    mapping: np.ndarray
    rig: CompiledRig | None = None
    data: bytes = b""

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


def is_file_spec(spec: str) -> bool:
    """Whether the map spec `spec` names a rig file: it has a "/" or ends in ".json"."""
    return "/" in spec or spec.endswith(".json")


def check_spec(spec: str) -> str:
    """`spec` when it reads as a map spec, without opening a file: a rig
    file's name, or a synthetic map that parses. Raises ValueError."""
    if not is_file_spec(spec):
        _synthetic(spec)
    return spec


def parse_geometry(spec: str) -> Geometry:
    """The geometry the map spec `spec` names. Raises ValueError, saying
    why; a room map file also warns (`pewpew.rig.runtime.RoomFormatWarning`)."""
    if not is_file_spec(spec):
        return Geometry(spec, _synthetic(spec))
    from pewpew.rig import RigError
    from pewpew.rig.runtime import load_rig

    try:
        rig, data = load_rig(Path(spec))
    except RigError as exc:
        raise ValueError(f"{spec}: {exc}") from None
    if rig.n == 0:
        raise ValueError(f"{spec}: the arrangement has no pixels")
    return Geometry(spec, rig.mapping, rig, data)


def _synthetic(spec: str) -> np.ndarray:
    try:
        return parse_map(spec)
    except ValueError:
        raise ValueError(f"expected {SPEC_RULE}; got {spec!r}") from None
