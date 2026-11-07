"""Write the studio's OpenAPI spec to openapi.json at the repo root, for orval.

Run from the project root: uv run python scripts/export_openapi.py
"""

import json
from pathlib import Path

from pewpew.studio.app import create_app

output = Path(__file__).resolve().parent.parent / "openapi.json"
output.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
print(f"Wrote {output}")
