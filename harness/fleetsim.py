"""Fleet-simulation interfaces — the mesh digital twin (ADR-017).

Typed interfaces only; implementations land with the engine. The contract
that matters and must never be broken: **the sim is deterministic** — same
(nodes, schedule, seed) -> byte-identical trace. That property is what makes
gossip/PCO/gradient-field behavior golden-testable and lets coding agents
iterate on coordination logic without hardware (architecture.md §4d,
ADR-015).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class NodeSpec:
    """One simulated mesh node."""

    node_id: int
    position: tuple[float, float]  # meters, plan view — drives link loss


@dataclass(frozen=True)
class Broadcast:
    """One state frame on the simulated air (ADR-014: ~11 B, fire-and-forget)."""

    sender: int
    t: float
    payload: bytes


class LossModel(Protocol):
    """Decides, deterministically from (broadcast, receiver, rng-seed),
    whether a receiver hears a broadcast. Implementations: uniform p,
    distance-based RSS curve, scheduled jamming windows."""

    def delivered(self, broadcast: Broadcast, receiver: NodeSpec, seed: int) -> bool: ...


@dataclass(frozen=True)
class PartitionEvent:
    """Fault injection: at time t, split the fleet into groups (rejoin =
    a later event with one group). Node churn is a group of size zero."""

    t: float
    groups: tuple[frozenset[int], ...]


@dataclass
class FleetTrace:
    """The deterministic output: everything a golden test or a bench
    comparison needs. Extended alongside ADR-017's implementation."""

    events: list[tuple[float, int, str]] = field(default_factory=list)


def simulate(
    nodes: list[NodeSpec],
    loss: LossModel,
    partitions: list[PartitionEvent],
    duration_s: float,
    seed: int,
) -> FleetTrace:
    """Run the fleet twin. TODO(ADR-017): implement with the engine —
    10 Hz beacon scheduler, epoch-gossip merge (ADR-015 Layer 1), optional
    PCO beat layer (Layer 2), gradient fields (Layer 2b)."""
    raise NotImplementedError("fleet sim lands with ADR-017's implementation phase")
