"""Arrangement file migration: pure `vN -> vN+1` functions over plain dicts.

Loading runs every step from the file's version up to `LATEST`; saving always
writes `LATEST`. A file newer than this code is refused
(docs/studio/domain-model.md:300).
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from pewpew.jsonfile import TooDeep, nests_deeper
from pewpew.rig.models import ARRANGEMENT_FORMAT, ARRANGEMENT_VERSION, Issue, RigError

LATEST = ARRANGEMENT_VERSION

#: STEPS[n] turns a version-n dict into a version-(n+1) dict. Version 1 is the
#: first, so there are none yet.
STEPS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(data: Mapping[str, Any], latest: int | None = None) -> dict[str, Any]:
    """`data` brought to the latest version, as a new dict; the input is not changed.

    At the latest version the new dict is a shallow copy.
    """
    latest = LATEST if latest is None else latest
    if nests_deeper(data):
        raise RigError([Issue.error("too_deep", str(TooDeep()))])
    if not isinstance(data, Mapping):
        raise RigError([Issue.error("bad_format", f"an arrangement is a JSON object, not {type(data).__name__}")])
    if data.get("format") != ARRANGEMENT_FORMAT:
        raise RigError(
            [Issue.error("bad_format", f"format is {data.get('format')!r}, expected {ARRANGEMENT_FORMAT!r}", "format")]
        )
    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise RigError(
            [Issue.error("bad_version", f"version must be a whole number from 1, got {version!r}", "version")]
        )
    if version > latest:
        raise RigError(
            [
                Issue.error(
                    "version_too_new",
                    f"version {version} is newer than this code, which reads up to {latest}",
                    "version",
                )
            ]
        )
    out = dict(data)
    if version == latest:
        return out
    out = copy.deepcopy(out)  # a step may edit nested values in place
    while out["version"] < latest:
        out = STEPS[out["version"]](out)
    return out
