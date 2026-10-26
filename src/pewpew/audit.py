"""Append-only audit log for tier-1 bench actuation (CLAUDE.md T-7).

Every start that drives real hardware appends one JSON line before the
first packet goes out. The log lives outside the repo by default
(`~/.local/state/pewpew/audit.jsonl`); `PEWPEW_AUDIT_LOG` overrides it.
The record carries wall-clock UTC time: this is provenance, not pattern
code, so determinism does not apply.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

ENV_VAR = "PEWPEW_AUDIT_LOG"


def audit_path() -> Path:
    """Where records go: `$PEWPEW_AUDIT_LOG`, else the per-user state dir."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "state" / "pewpew" / "audit.jsonl"


def record(action: str, *, argv: list[str], **fields: object) -> Path:
    """Append one record and return the path written. Raises OSError if the
    log cannot be written; the caller must then not actuate."""
    entry = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "argv": argv,
        **fields,
    }
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return path
