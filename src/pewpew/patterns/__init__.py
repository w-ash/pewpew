"""The built-in pattern gallery — engine ports of the five ADR-005 study
patterns (bench/authoring/, frozen evidence). Each port preserves its
prototype's arithmetic bit-exactly; see tests/test_port_equivalence.py.

    from pewpew.patterns import Plasma, Comet, Geq, Fire, Sdf3d
"""

from __future__ import annotations

import numpy as np

from pewpew.mapping import grid, lattice, line
from pewpew.patterns.comet import Comet
from pewpew.patterns.fire import Fire
from pewpew.patterns.geq import Geq
from pewpew.patterns.plasma import Plasma
from pewpew.patterns.sdf3d import Sdf3d

# Each pattern paired with the fixture it was written against, from the
# authoring study (bench/bench_authoring.py::STUDY). One home for a triple that
# was hand-copied into three test files, each re-deriving it from the study
# runner. Frame counts stay with the callers — those legitimately differ.
#
# Read-only because the table is shared: the engine treats a mapping as
# immutable (render.py locks its column views for the same reason), and a
# module-level fixture that one test could scribble on would leak into every
# other.
def _frozen(mapping: np.ndarray) -> np.ndarray:
    mapping.setflags(write=False)
    return mapping


STUDY_CASES: tuple[tuple[type, np.ndarray], ...] = (
    (Plasma, _frozen(line(300))),
    (Comet, _frozen(line(300))),
    (Geq, _frozen(grid(16, 16))),
    (Fire, _frozen(grid(16, 32))),
    (Sdf3d, _frozen(lattice(10))),
)

def default_mapping(pattern_cls: type) -> np.ndarray | None:
    """The fixture `pattern_cls` was authored against, or None if it has no
    entry. The runner uses this so a bare `run <pattern>` shows a pattern on
    the geometry it was designed for."""
    for cls, mapping in STUDY_CASES:
        if cls is pattern_cls:
            return mapping
    return None


__all__ = ["Plasma", "Comet", "Geq", "Fire", "Sdf3d", "STUDY_CASES", "default_mapping"]
