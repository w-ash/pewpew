"""The built-in pattern gallery: engine ports of the five ADR-005 study
patterns (bench/authoring/, frozen evidence), the canopy set (pulse, wave, wash, sparkle),
colorplasma (plasma with a palette) and rainbow (the studio's first
effect). Each study port keeps its prototype's arithmetic bit for bit
(tests/test_port_equivalence.py).

    from pewpew.patterns import Plasma, Comet, Geq, Fire, Sdf3d
    from pewpew.patterns import Pulse, Wave, Wash, Sparkle
    from pewpew.patterns import ColorPlasma, Rainbow
"""

from __future__ import annotations

import numpy as np

from pewpew.mapping import Grouping, grid, lattice, line
from pewpew.patterns.colorplasma import ColorPlasma
from pewpew.patterns.comet import Comet
from pewpew.patterns.fire import Fire
from pewpew.patterns.geq import Geq
from pewpew.patterns.plasma import Plasma
from pewpew.patterns.pulse import Pulse
from pewpew.patterns.rainbow import Rainbow
from pewpew.patterns.sdf3d import Sdf3d
from pewpew.patterns.sparkle import Sparkle
from pewpew.patterns.wash import Wash
from pewpew.patterns.wave import Wave
from pewpew.room.map import RoomMap, compile_room


def _frozen(mapping: np.ndarray) -> np.ndarray:
    mapping.setflags(write=False)
    return mapping


def canopy() -> RoomMap:
    """The 60-bar ceiling canopy of `examples/room-60-bars.json`, built in code
    so the package does not read a file outside itself. tests/test_canopy_patterns.py
    holds the two equal."""
    rows = []
    for k in range(12):
        board = "ABC"[k // 4]
        rows.append({
            "id": f"row{k + 1:02d}", "pixels": 64, "length": 1.0,
            "start": [1.1, round(0.8 + 0.4 * k, 1)], "angle": 0,
            "input": "end" if board == "B" else "start",
            "board": board, "output": k % 4 + 1, "chain": 1,
            "instances": 5, "step": [1.2, 0.0],
        })
    boards = {"A": "10.0.0.11", "B": "10.0.0.12", "C": "10.0.0.13"}
    return compile_room({"boards": boards, "fixtures": rows})


_CANOPY = canopy()
_CANOPY_BARS = _CANOPY.grouping

# Each pattern with the mapping it was written against and its fixture
# grouping (None: no fixtures). The study five come from
# bench/bench_authoring.py::STUDY; Pulse, Wave, Wash, Sparkle and Rainbow run
# on the canopy (Rainbow's own golden rings come from the rig compiler, which
# `import pewpew.patterns` does not load). The tests
# share this table, so every mapping in it is read-only.
STUDY_CASES: tuple[tuple[type, np.ndarray, Grouping | None], ...] = (
    (Plasma, _frozen(line(300)), None),
    (Comet, _frozen(line(300)), None),
    (Geq, _frozen(grid(16, 16)), None),
    (Fire, _frozen(grid(16, 32)), None),
    (Sdf3d, _frozen(lattice(10)), None),
    (Pulse, _CANOPY.mapping, _CANOPY_BARS),
    (Wave, _CANOPY.mapping, _CANOPY_BARS),
    (Wash, _CANOPY.mapping, _CANOPY_BARS),
    (Sparkle, _CANOPY.mapping, _CANOPY_BARS),
    (ColorPlasma, _frozen(line(300)), None),
    (Rainbow, _CANOPY.mapping, _CANOPY_BARS),
)


__all__ = [  # noqa: RUF022  study ports, then the canopy set
    "Plasma", "Comet", "Geq", "Fire", "Sdf3d",
    "Pulse", "Wave", "Wash", "Sparkle", "ColorPlasma", "Rainbow",
    "STUDY_CASES", "canopy",
]
