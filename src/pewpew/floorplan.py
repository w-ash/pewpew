"""A floor-plan image under a map, calibrated by two points a known distance apart.

The room map and the arrangement share this `plan` block (xLights' two-point
ruler [S1279]):

    "plan": {"image": "plan.png", "points": [[120, 840], [1720, 840]],
             "meters": 8.0, "at": [0.0, 0.0]}

`image` is a .png, .jpg, .jpeg, .webp or .gif file, relative to the map
file. `points` are two image pixels (x right, y down, as image editors show
them) `meters` apart; `at` is where the first point sits on the plan, in
meters (default [0, 0]). The plan frame is x right, y up the page. The image
is not rotated: its x axis is the plan's x and its y axis runs down the
page. Calibration is checked here; whether the image exists is the
preview's concern, so a missing image never stops the run.

No pydantic and no rig import: a run on a room map loads this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pewpew.jsonfile import is_number

# The floor-plan image types the preview serves, by file suffix. SVG is left
# out: opened as a page, it runs scripts on that origin.
IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_PLAN_KEYS = {"image", "points", "meters", "at"}
_EPS = 1e-9

#: The JSON Schema of a `plan` block, for the arrangement schema.
PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "title": "Plan",
    "description": "A floor-plan image, calibrated by two image pixels `meters` apart.",
    "properties": {
        # ECMA-262 has no inline (?i), so each letter takes both cases.
        "image": {"type": "string", "pattern": r"\.([Pp][Nn][Gg]|[Jj][Pp][Ee]?[Gg]|[Ww][Ee][Bb][Pp]|[Gg][Ii][Ff])$"},
        "points": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
            "minItems": 2,
            "maxItems": 2,
        },
        "meters": {"type": "number", "exclusiveMinimum": 0},
        "at": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "default": [0.0, 0.0]},
    },
    "required": ["image", "points", "meters"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Plan:
    """A floor-plan image and its two-point calibration."""

    image: str  # relative to the map file
    points: tuple[tuple[float, float], tuple[float, float]]  # image pixels, y down
    meters: float  # distance between the two points
    at: tuple[float, float]  # plan meters of the first point

    @property
    def meters_per_pixel(self) -> float:
        (u1, v1), (u2, v2) = self.points
        return self.meters / math.hypot(u2 - u1, v2 - v1)

    @property
    def corner(self) -> tuple[float, float]:
        """Plan meters of the image's top-left corner."""
        (u1, v1), _ = self.points
        m = self.meters_per_pixel
        return (self.at[0] - u1 * m, self.at[1] + v1 * m)

    def to_json(self) -> dict[str, Any]:
        """The `plan` block as plain JSON types."""
        return {
            "image": self.image,
            "points": [list(p) for p in self.points],
            "meters": self.meters,
            "at": list(self.at),
        }


def parse_plan(raw: Any, *, file: str = "room file", frame: str = "room") -> tuple[Plan | None, list[str]]:
    """A `plan` block -> (Plan, []), or (None, problems).

    The messages name the `file` the image sits beside and the `frame` the
    meters are in. They never repeat the image name, which is a path.
    """
    problems: list[str] = []
    bad = problems.append
    if not isinstance(raw, dict):
        return None, ["must be an object with 'image', 'points' and 'meters'"]
    for key in sorted(set(raw) - _PLAN_KEYS):
        bad(f"unknown key {key!r}; expected {', '.join(sorted(_PLAN_KEYS))}")
    image = raw.get("image")
    if not isinstance(image, str) or not image.strip():
        bad(f"needs an 'image' file name, relative to the {file}")
    elif Path(image).suffix.lower() not in IMAGE_TYPES:
        bad(f"'image' must be a {', '.join(IMAGE_TYPES)} file")
    points = raw.get("points")
    pair: list[tuple[float, float]] = []
    if (
        not isinstance(points, list)
        or len(points) != 2
        or not all(isinstance(p, list) and len(p) == 2 and all(is_number(v) for v in p) for p in points)
    ):
        bad("'points' must be two image pixels, [[x, y], [x, y]]")
    else:
        pair = [(float(p[0]), float(p[1])) for p in points]
        if math.hypot(pair[1][0] - pair[0][0], pair[1][1] - pair[0][1]) <= _EPS:
            bad("the two 'points' are the same pixel; pick two points a known distance apart")
    meters = raw.get("meters")
    if not is_number(meters) or meters <= 0:
        bad("'meters' must be the positive distance between the two points")
    at = raw.get("at", [0.0, 0.0])
    if not isinstance(at, list) or len(at) != 2 or not all(is_number(v) for v in at):
        bad(f"'at' must be [x, y], the {frame} meters of the first point")
    if problems:
        return None, problems
    assert isinstance(image, str) and is_number(meters)  # refused above otherwise
    return Plan(image, (pair[0], pair[1]), float(meters), (float(at[0]), float(at[1]))), []
