"""The rig model: a fixture catalog, arrangements of fixtures, and the compiler.

    from pewpew.rig import load_arrangement, load_catalog, compile_rig

    rig = compile_rig(load_arrangement(Path("rings.json")), load_catalog())
    renderer = Renderer(pattern, rig.mapping)

The design is docs/studio/domain-model.md and the API is
docs/studio/contracts.md:25-67. Layout: `models` (file formats and compiled
shapes), `expr` (dims expressions), `catalog` (loading and digests), `pose`
(rotations and frames), `presets` (ring, array), `wiring` (auto-wiring),
`electrical` (the power, wiring and controller report, and effect power),
`compile` (`compile_rig`), `migrate` (file versions).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pewpew.rig.catalog import Catalog, FixtureSpec, load_catalog, read_catalog, validation_issues
from pewpew.rig.compile import compile_rig, contain
from pewpew.rig.migrate import migrate as _migrate
from pewpew.rig.models import (
    Arrangement,
    CompiledRig,
    ControllerSlice,
    FixtureInstance,
    Instance,
    Issue,
    OutputSlice,
    RigError,
    WiringPlan,
    fixture_grouping,
)

EXAMPLES = Path(__file__).with_name("examples")

_TOO_DEEP = Issue.error("too_deep", "the arrangement nests too deeply")


def load_arrangement(obj: str | os.PathLike[str] | Mapping[str, Any]) -> Arrangement:
    """An arrangement from a dict, JSON text or a file, migrated and validated.

    A `str` is always JSON text, never a path; give a file as an
    `os.PathLike` such as a `Path`. Validation is strict: a number given as a
    string or a bool is an error. Raises RigError with one issue per problem.
    """
    data: Any = obj
    if isinstance(obj, os.PathLike):
        data = _read(obj)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as exc:  # JSONDecodeError, or an integer of too many digits
            raise RigError([Issue.error("bad_json", str(exc))]) from None
        except RecursionError:
            raise RigError([_TOO_DEEP]) from None
    data = _migrate(data)
    try:
        # JSON mode, so that strict mode takes a JSON array for a tuple.
        text = json.dumps(data)
    except RecursionError:
        raise RigError([_TOO_DEEP]) from None
    except (TypeError, ValueError) as exc:
        raise RigError([Issue.error("bad_json", f"the arrangement is not JSON data: {exc}")]) from None
    try:
        return Arrangement.model_validate_json(text, strict=True)
    except ValidationError as exc:
        raise RigError(validation_issues(exc)) from None


def _read(path: os.PathLike[str]) -> str:
    try:
        return Path(path).read_text("utf-8")
    except UnicodeDecodeError:
        raise RigError([Issue.error("bad_json", "the file is not UTF-8 text")]) from None
    except (OSError, ValueError) as exc:  # ValueError: a null byte in the path
        reason = (exc.strerror if isinstance(exc, OSError) else str(exc)) or type(exc).__name__
        raise RigError([Issue.error("unreadable_file", f"cannot read the file: {reason.lower()}")]) from None


__all__ = [
    "EXAMPLES",
    "Arrangement",
    "Catalog",
    "CompiledRig",
    "ControllerSlice",
    "FixtureInstance",
    "FixtureSpec",
    "Instance",
    "Issue",
    "OutputSlice",
    "RigError",
    "WiringPlan",
    "compile_rig",
    "contain",
    "fixture_grouping",
    "load_arrangement",
    "load_catalog",
    "read_catalog",
]
