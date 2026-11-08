"""The parts catalog as the engine serves it, with each type's prebuilt 3D assembly.

`PartsView.of(catalog)` gives the `parts.json` body: `Catalog.to_json()` with a
`digest` and an `assembly_url` on each fixture and attachment type, and every
assembly's GLB by digest. The GLBs are package data in `rig/assemblies/`,
written by `scripts/build_assemblies.py` (`just assemblies`), so the runtime
needs no manifold3d and does not import `pewpew.rig.geometry`.

`assemblies/index.json` maps each base type id to `{"digest", "source"}`.
`digest` is `geometry.assembly_digest`, the first 16 hex digits of the SHA-256
of the GLB, which is `<digest>.glb` beside the index. `source` is
`source_hash` of the type when the GLB was built. A type whose `source`
differs from its current `source_hash` has no assembly until the GLBs are
built again.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from typing import Any

from pewpew.rig.catalog import Catalog, load_catalog
from pewpew.rig.models import AttachmentType

logger = logging.getLogger(__name__)

ASSEMBLY_URL = "/assembly/{digest}.glb"

#: A type id and its catalog to `(digest, GLB)`, or None when the type has no assembly.
Assemblies = Callable[[str, Catalog], tuple[str, bytes] | None]

_PACKAGE = "pewpew.rig"
_FOLDER = "assemblies"


def source_hash(type_id: str, catalog: Catalog) -> str:
    """SHA-256 hex over the catalog data that the type's GLB is built from.

    The data is the type's entity and, for an attachment type, each fixture
    type with an anchor that accepts it, in catalog order (the hosts of
    `geometry.part_meshes`). The JSON is canonical, as `Catalog.digest`
    writes it.
    """
    entity = catalog.get(type_id)
    data = [entity.model_dump(mode="json")]
    if isinstance(entity, AttachmentType):
        data += [
            ft.model_dump(mode="json")
            for ft in catalog.fixture_types.values()
            if any(a.accepts == entity.fits for a in ft.anchors.values())
        ]
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@functools.cache
def _index() -> dict[str, dict[str, str]]:
    path = resources.files(_PACKAGE).joinpath(f"{_FOLDER}/index.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def prebuilt(type_id: str, catalog: Catalog) -> tuple[str, bytes] | None:
    """The packaged digest and GLB of a type, or None when the package has none for its data.

    Logs a warning when the index has no entry for the type or its `source`
    is stale.
    """
    entry = _index().get(type_id)
    if entry is None or entry.get("source") != source_hash(type_id, catalog):
        why = "no prebuilt assembly" if entry is None else "a stale prebuilt assembly"
        logger.warning("%s has %s; run `just assemblies`", type_id, why)
        return None
    digest = entry["digest"]
    glb = resources.files(_PACKAGE).joinpath(f"{_FOLDER}/{digest}.glb")
    try:
        return digest, glb.read_bytes()
    except FileNotFoundError:
        logger.warning("%s has no file %s.glb; run `just assemblies`", type_id, digest)
        return None


@dataclass(frozen=True)
class PartsView:
    """The `parts.json` body as sent, and every assembly's GLB by digest.

    Built once per catalog, so serving a GLB only looks it up.
    """

    body: bytes
    assemblies: dict[str, bytes]  # assembly digest -> GLB

    @classmethod
    def of(cls, catalog: Catalog, assemblies: Assemblies = prebuilt, url: str = ASSEMBLY_URL) -> PartsView:
        """The view of `catalog`. `url` is a format string with `{digest}`."""
        body: dict[str, Any] = dict(catalog.to_json())
        glbs: dict[str, bytes] = {}
        for key in ("fixture_types", "attachment_types"):
            entries = []
            for entry in body.get(key, []):
                built = assemblies(entry["id"], catalog)
                digest = None
                if built is not None:
                    digest, glbs[digest] = built
                link = None if digest is None else url.format(digest=digest)
                entries.append({**entry, "digest": digest, "assembly_url": link})
            body[key] = entries
        return cls(json.dumps(body).encode(), glbs)

    def glb(self, digest: str) -> bytes | None:
        """The GLB with this digest, or None."""
        return self.assemblies.get(digest)


@functools.cache
def parts_view() -> PartsView:
    """The bundled catalog with its prebuilt assemblies: what the engine serves."""
    return PartsView.of(load_catalog())
