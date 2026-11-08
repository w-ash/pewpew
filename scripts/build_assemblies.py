"""Write the prebuilt 3D assemblies of the bundled catalog's fixture and attachment types.

    uv run python scripts/build_assemblies.py    (or: just assemblies)

Builds every type's GLB with `pewpew.rig.geometry.build_glb` (needs manifold3d)
in memory first, so a failed build writes nothing. Then writes
`src/pewpew/rig/assemblies/<digest>.glb` and `index.json`, which
`pewpew.rig.parts` serves, each through a temporary file and `os.replace`, the
index last. Deletes each .glb file the index does not name.
`tests/test_rig_assemblies.py` fails when the committed files are stale.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pewpew.rig import load_catalog
from pewpew.rig.geometry import build_glb
from pewpew.rig.parts import source_hash

OUT = Path(__file__).resolve().parent.parent / "src" / "pewpew" / "rig" / "assemblies"


def write(path: Path, data: bytes) -> None:
    """Write `data` to `path` through a temporary file beside it, so `path` is never partly written."""
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def main() -> None:
    catalog = load_catalog()
    built: dict[str, bytes] = {}
    index: dict[str, dict[str, str]] = {}
    for type_id in sorted([*catalog.fixture_types, *catalog.attachment_types]):
        glb = build_glb(type_id, catalog)
        digest = hashlib.sha256(glb).hexdigest()[:16]  # geometry.assembly_digest, without a second build
        built[digest] = glb
        index[type_id] = {"digest": digest, "source": source_hash(type_id, catalog)}
        print(f"{type_id}: {digest}")
    OUT.mkdir(exist_ok=True)
    for digest, glb in built.items():
        write(OUT / f"{digest}.glb", glb)
    write(OUT / "index.json", (json.dumps(index, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    for path in sorted(OUT.glob("*.glb")):
        if path.name not in {f"{d}.glb" for d in built}:
            path.unlink()
            print(f"deleted {path.name}")


if __name__ == "__main__":
    main()
