"""Room map to arrangement: a pure migration of a room file's meaning.

`room_to_arrangement` reads a room map (`pewpew.room.map`) and returns an
arrangement dict, so a rig described as a room map compiles with
`compile_rig` to the same mapping, pixel order, fixture ids and DDP ranges.

- A board becomes a controller with its `host`. Output n becomes the
  profile's n-th output, and each (board, output) a chain `BOARD-N`.
- Every fixture, `instances` copies included, becomes a free fixture with
  the room's id (`row.3`), its tags, and `dims` for its pixels, length and
  pitch.
- A free fixture's pixel 0 sits at local -y. The pose is the strip midpoint
  with `aim` along the strip from its input end to its far end, so the
  room's `input` end is in the pose and no field carries it.
- The room's plan frame (x right, y up the plan, z height) goes to the
  arrangement's y-up frame by C^T, where C is `MVR_C`.
- `label` becomes `name`; `notes` and `plan` carry over.

The room's own checks run first; a room that fails them raises `RoomError`.
Nothing is guessed: an output the profile lacks raises `RigError`.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pewpew.rig.models import Controller, Issue, RigError
from pewpew.rig.pose import MVR_C
from pewpew.room.map import Fixture, compile_room


def room_to_arrangement(doc: Any, *, controller_profile: Controller, fixture_type: str) -> dict[str, Any]:
    """The arrangement dict for the parsed room document `doc`.

    `controller_profile` is the catalog controller every board becomes and
    `fixture_type` the parametric catalog type every strip becomes; it takes
    the dims `pixels`, `length` and `pitch`. Raises `RoomError` for a room
    that does not compile and `RigError` for an output the profile lacks.
    Numbers are kept to 12 significant digits. The result is not yet
    validated; load it with `load_arrangement`.
    """
    room = compile_room(doc)
    outputs = [o.id for o in controller_profile.outputs]
    tags = _tags(doc)
    missing = sorted({f.output for f in room.fixtures if f.output > len(outputs)})
    if missing:
        raise RigError([
            Issue.error(
                "output_missing",
                f"output {n} does not exist on {controller_profile.id!r}, which has {len(outputs)} outputs",
            )
            for n in missing
        ])
    chains: dict[tuple[str, int], list[Fixture]] = {}
    for fixture in room.fixtures:
        chains.setdefault((fixture.board, fixture.output), []).append(fixture)
    out: dict[str, Any] = {"format": "pewpew.arrangement", "version": 1}
    if doc.get("label"):
        out["name"] = doc["label"]
    if doc.get("notes"):
        out["notes"] = doc["notes"]
    out["controllers"] = [
        {"id": name, "profile": controller_profile.id, "host": doc["boards"][name]} for name in room.board_names
    ]
    out["fixtures"] = [_placement(f, fixture_type, tags.get(f.id, [])) for f in room.fixtures]
    out["wiring"] = {
        "chains": [
            {
                "id": f"{board}-{output}",
                "controller": board,
                "output": outputs[output - 1],
                "fixtures": [f.id for f in chain],
            }
            for (board, output), chain in chains.items()
        ]
    }
    if room.floor_plan is not None:
        out["plan"] = room.floor_plan.to_json()
    return out


def _placement(fixture: Fixture, fixture_type: str, tags: list[str]) -> dict[str, Any]:
    start, end = np.array(fixture.start), np.array(fixture.end)
    near, far = (start, end) if fixture.input == "start" else (end, start)
    length = float(np.linalg.norm(end - start))
    placement: dict[str, Any] = {
        "id": fixture.id,
        "type": fixture_type,
        "pose": {
            "position_m": _vec(MVR_C.T @ ((start + end) / 2.0)),
            "aim": {"axis": _vec(MVR_C.T @ (far - near))},
        },
        "dims": {"pixels": fixture.pixels, "length": _clean(length), "pitch": _clean(fixture.pitch)},
    }
    if tags:
        placement["tags"] = tags
    return placement


def _vec(v: np.ndarray) -> list[float]:
    return [_clean(float(c)) for c in v]


def _clean(x: float) -> float:
    """`x` to 12 significant digits, so a sum such as 1.1 + 3 * 1.2 reads 5.2;
    the error is far below the mapping's float32 steps."""
    return float(f"{x:.12g}") + 0.0  # + 0.0 turns -0.0 into 0.0


def _tags(doc: dict[str, Any]) -> dict[str, list[str]]:
    """Each fixture's tags by the id it has after `instances` expands."""
    out: dict[str, list[str]] = {}
    for item in doc["fixtures"]:
        tags = item.get("tags", [])
        count = item.get("instances", 1)
        ids = [item["id"]] if count == 1 else [f"{item['id']}.{k}" for k in range(1, count + 1)]
        for fid in ids:
            out[fid] = list(tags)
    return out
