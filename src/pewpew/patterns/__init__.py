"""The built-in pattern gallery — engine ports of the five ADR-005 study
patterns (bench/authoring/, frozen evidence). Each port preserves its
prototype's arithmetic bit-exactly; see tests/test_port_equivalence.py.

    from pewpew.patterns import Plasma, Comet, Geq, Fire, Sdf3d
"""

from __future__ import annotations

from pewpew.patterns.comet import Comet
from pewpew.patterns.fire import Fire
from pewpew.patterns.geq import Geq
from pewpew.patterns.plasma import Plasma
from pewpew.patterns.sdf3d import Sdf3d

__all__ = ["Plasma", "Comet", "Geq", "Fire", "Sdf3d"]
