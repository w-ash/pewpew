"""Write the committed JSON Schemas of the rig file formats.

    uv run python scripts/export_schemas.py

Writes `schemas/arrangement.v1.json` and `schemas/catalog.v1.json` from the
pydantic models in `pewpew.rig.models`. `tests/test_rig_schema.py` fails when
the committed copies differ from what this writes.
"""

from __future__ import annotations

from pathlib import Path

from pewpew.rig.models import json_schemas

SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


def main() -> None:
    SCHEMAS.mkdir(exist_ok=True)
    for name, text in json_schemas().items():
        (SCHEMAS / name).write_text(text, encoding="utf-8")
        print(f"wrote schemas/{name}")


if __name__ == "__main__":
    main()
