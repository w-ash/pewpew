"""Write the prebuilt 3D assemblies of the bundled catalog's fixture and attachment types.

    uv run python scripts/build_assemblies.py    (or: just assemblies)

Builds each type's GLB with `pewpew.rig.geometry.build_glb` (needs manifold3d)
and writes `src/pewpew/rig/assemblies/<digest>.glb` and `index.json`, which
`pewpew.rig.parts` serves. Deletes each .glb file the index does not name.
`tests/test_rig_assemblies.py` fails when the committed files are stale.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pewpew.rig import load_catalog
from pewpew.rig.geometry import build_glb
from pewpew.rig.parts import source_hash

OUT = Path(__file__).resolve().parent.parent / "src" / "pewpew" / "rig" / "assemblies"


def main() -> None:
    catalog = load_catalog()
    OUT.mkdir(exist_ok=True)
    index: dict[str, dict[str, str]] = {}
    for type_id in sorted([*catalog.fixture_types, *catalog.attachment_types]):
        glb = build_glb(type_id, catalog)
        digest = hashlib.sha256(glb).hexdigest()[:16]  # geometry.assembly_digest, without a second build
        (OUT / f"{digest}.glb").write_bytes(glb)
        index[type_id] = {"digest": digest, "source": source_hash(type_id, catalog)}
        print(f"{type_id}: {digest}")
    (OUT / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    keep = {f"{e['digest']}.glb" for e in index.values()}
    for path in sorted(OUT.glob("*.glb")):
        if path.name not in keep:
            path.unlink()
            print(f"deleted {path.name}")


if __name__ == "__main__":
    main()
