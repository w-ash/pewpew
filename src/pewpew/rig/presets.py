"""Group presets: `ring` and `array` expanded into member placements.

Each function returns the members of one group in id order, with matrices in
the group's own frame. The compiler puts them in the world with the group's
pose: `M_world = M_group · M_member` (docs/studio/domain-model.md:175).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import TypeAdapter

from pewpew.rig.models import ArrayGroup, RingGroup
from pewpew.rig.pose import FLIP_Z, compose, pose_matrix, rot_y

PRESETS: dict[str, type] = {"ring": RingGroup, "array": ArrayGroup}

# Fields every group has; `describe_presets` lists only the rest.
_COMMON_FIELDS = ("id", "preset", "type")


@dataclass(frozen=True)
class Member:
    """One group member: its id, its matrix in the group frame, its attachments."""

    id: str
    matrix: np.ndarray
    attach: Mapping[str, str | None]


def ring(group: RingGroup, length_m: float) -> list[Member]:
    """The members of a ring of fixtures `length_m` long, end anchor to end anchor.

    For member k at θ = offset + 360k/n, tilt a and roll ρ
    (docs/studio/domain-model.md:193-200):

    - midpoint m = (r₀ + L/2)(cos θ, 0, sin θ);
    - x = (−sin θ, 0, cos θ), y = (cos a cos θ, sin a, cos a sin θ), z = x × y;
    - R = [x y z] · Ry(ρ), then · Rz(180°) when data enters at the outer end.

    This is the prototype's basis (docs/studio/prototype/golden-tubes-3d.html:425-429).
    With data in at the inner end, the inner end is `end_a` (local −y).
    """
    a = math.radians(group.tilt_deg)
    roll = rot_y(group.roll_deg)
    r_mid = group.start_radius_m + length_m / 2
    outer_in = group.data_in == "outer"
    attach = (
        {"end_a": group.attach.outer, "end_b": group.attach.inner}
        if outer_in
        else {"end_a": group.attach.inner, "end_b": group.attach.outer}
    )
    members = []
    for k in range(group.count):
        theta = math.radians(group.angle_offset_deg + 360.0 * k / group.count)
        c, s = math.cos(theta), math.sin(theta)
        x = np.array([-s, 0.0, c])
        y = np.array([math.cos(a) * c, math.sin(a), math.cos(a) * s])
        r = np.column_stack([x, y, np.cross(x, y)]) @ roll
        if outer_in:
            r = r @ FLIP_Z
        members.append(Member(f"{group.id}/{k}", compose((r_mid * c, 0.0, r_mid * s), r), attach))
    return members


def array(group: ArrayGroup) -> list[Member]:
    """The members of a line or grid, row-major: k = i·counts[1] + j."""
    member = pose_matrix(group.member)
    steps = [np.asarray(s, dtype=np.float64) for s in group.steps_m]
    cells = (
        [(i,) for i in range(group.counts[0])]
        if len(group.counts) == 1
        else [(i, j) for i in range(group.counts[0]) for j in range(group.counts[1])]
    )
    attach = dict(group.attach)
    members = []
    for k, cell in enumerate(cells):
        offset = sum((n * step for n, step in zip(cell, steps)), np.zeros(3))
        members.append(Member(f"{group.id}/{k}", compose(offset, np.eye(3)) @ member, attach))
    return members


def describe_presets() -> list[dict[str, Any]]:
    """Each preset's name and parameter fields, with defaults, as JSON types."""
    out = []
    for name, model in PRESETS.items():
        params = []
        for field_name, info in model.model_fields.items():
            if field_name in _COMMON_FIELDS:
                continue
            entry: dict[str, Any] = {"name": field_name, "required": info.is_required()}
            if not info.is_required():
                entry["default"] = TypeAdapter(info.annotation).dump_python(info.default, mode="json")
            params.append(entry)
        out.append({"name": name, "doc": (model.__doc__ or "").strip(), "params": params})
    return out
