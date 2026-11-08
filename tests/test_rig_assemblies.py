"""The prebuilt 3D assemblies in `pewpew.rig.assemblies` and the parts view that serves them.

None of these tests needs manifold3d. A failure here after a catalog change
means the committed GLBs are stale: run `just assemblies`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path

import pytest

from pewpew.rig import load_catalog
from pewpew.rig.catalog import Catalog
from pewpew.rig.parts import ASSEMBLY_URL, PartsView, parts_view, prebuilt, source_hash

FOLDER = Path(__file__).resolve().parents[1] / "src" / "pewpew" / "rig" / "assemblies"
INDEX: dict[str, dict[str, str]] = json.loads((FOLDER / "index.json").read_text(encoding="utf-8"))
STALE = "run `just assemblies`"


def type_ids(catalog: Catalog) -> set[str]:
    return set(catalog.fixture_types) | set(catalog.attachment_types)


def test_the_index_covers_every_fixture_and_attachment_type():
    assert set(INDEX) == type_ids(load_catalog()), STALE


def test_each_source_is_current():
    catalog = load_catalog()
    for type_id, entry in INDEX.items():
        assert entry["source"] == source_hash(type_id, catalog), f"{type_id}: {STALE}"


def test_each_glb_is_named_by_its_digest():
    for type_id, entry in INDEX.items():
        glb = (FOLDER / f"{entry['digest']}.glb").read_bytes()
        assert glb[:4] == b"glTF", type_id
        assert hashlib.sha256(glb).hexdigest()[:16] == entry["digest"], type_id


def test_no_stray_glb_files():
    assert {p.name for p in FOLDER.glob("*.glb")} == {f"{e['digest']}.glb" for e in INDEX.values()}


def test_the_index_is_written_canonically():
    assert (FOLDER / "index.json").read_text(encoding="utf-8") == json.dumps(INDEX, indent=2, sort_keys=True) + "\n"


def test_parts_view_gives_every_type_an_assembly():
    view = parts_view()
    body = json.loads(view.body)
    types = body["fixture_types"] + body["attachment_types"]
    assert {t["id"] for t in types} == type_ids(load_catalog())
    for t in types:
        assert t["digest"] == INDEX[t["id"]]["digest"]
        assert t["assembly_url"] == ASSEMBLY_URL.format(digest=t["digest"])
        assert view.glb(t["digest"]) == (FOLDER / f"{t['digest']}.glb").read_bytes()
    assert view.glb("0000000000000000") is None


def test_the_url_is_a_format_string():
    view = PartsView.of(load_catalog(), url="/api/assembly/{digest}.glb")
    for t in json.loads(view.body)["fixture_types"]:
        assert t["assembly_url"] == f"/api/assembly/{t['digest']}.glb"


def test_assemblies_need_neither_manifold3d_nor_the_geometry_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "manifold3d", None)  # the import fails as if absent
    monkeypatch.setitem(sys.modules, "pewpew.rig.geometry", None)
    view = PartsView.of(load_catalog())
    body = json.loads(view.body)
    for t in body["fixture_types"] + body["attachment_types"]:
        assert t["digest"] is not None, t["id"]
        glb = view.glb(t["digest"])
        assert glb is not None and glb[:4] == b"glTF"


def test_a_changed_type_has_no_assembly(caplog):
    loaded = load_catalog()
    changed = loaded.get("clen-rgbw-bar-1m")
    catalog = Catalog([changed.model_copy(update={"name": "Renamed"}) if e is changed else e for e in loaded])
    assert source_hash(changed.id, catalog) != INDEX[changed.id]["source"]
    with caplog.at_level(logging.WARNING, logger="pewpew.rig.parts"):
        assert prebuilt(changed.id, catalog) is None
    assert any(changed.id in r.getMessage() and "just assemblies" in r.getMessage() for r in caplog.records)
    body = json.loads(PartsView.of(catalog).body)
    (bar,) = (t for t in body["fixture_types"] if t["id"] == changed.id)
    assert bar["digest"] is None and bar["assembly_url"] is None


@pytest.mark.parametrize("type_id", ["eye-v0", "point-v0"])
def test_an_attachment_goes_stale_when_a_host_changes(type_id):
    loaded = load_catalog()
    host = loaded.get("clen-rgbw-bar-1m")
    catalog = Catalog([host.model_copy(update={"name": "Renamed"}) if e is host else e for e in loaded])
    assert source_hash(type_id, catalog) != INDEX[type_id]["source"]
