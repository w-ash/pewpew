"""The GLB assemblies: determinism, structure, the bar's shape, INV-002, the attachments and bad data."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import tracemalloc

import numpy as np
import pytest

m3d = pytest.importorskip("manifold3d")

from pewpew.rig import compile_rig, geometry, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import CATALOG_ENTRIES_DIR
from pewpew.rig.geometry import SMOOTH_ANGLE_DEG, GeometryError, assembly_digest, build_glb

BAR, TUBE, POINT, EYE = "clen-rgbw-bar-1m", "clen-360-tube-1500", "point-v0", "eye-v0"
TYPES = [BAR, TUBE, POINT, EYE]
FIX, ATT = "fixture_type", "attachment_type"
MM = 1e-3
TOL = 1e-6  # float32 positions under 1 m are good to about 6e-8 m
FACET = 2e-5  # a 96-gon lies up to about 12 µm inside its circle between vertices

#: The same on macOS arm64, Linux arm64 and Linux x86_64 (docs/studio/reports/reviews/ws1b-fixes.md).
#: A change here changes the served assemblies: check the new GLBs, then update these.
DIGESTS = {BAR: "b0c0e942081d867f", TUBE: "62efbd86ef6eeea1", POINT: "30ba296fe9412539", EYE: "e30716ce61f71662"}


@pytest.fixture(scope="module")
def cat():
    return load_catalog()


@pytest.fixture(scope="module")
def glbs(cat):
    return {t: build_glb(t, cat) for t in TYPES}


# ---- an independent GLB reader ------------------------------------------------


def read_glb(data: bytes) -> tuple[dict, bytes]:
    """The JSON and BIN chunks; asserts the header, the chunk order and the alignment."""
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    json_len, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A and json_len % 4 == 0
    text = data[20 : 20 + json_len]
    assert text.rstrip(b" ").endswith(b"}") and len(text) - len(text.rstrip(b" ")) < 4
    doc = json.loads(text)
    at = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<II", data, at)
    assert bin_type == 0x004E4942 and bin_len % 4 == 0
    assert at + 8 + bin_len == len(data)
    return doc, data[at + 8 :]


def accessor(doc: dict, blob: bytes, index: int) -> np.ndarray:
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    dtype = {5126: "<f4", 5125: "<u4"}[acc["componentType"]]
    width = {"SCALAR": 1, "VEC3": 3}[acc["type"]]
    start = view["byteOffset"] + acc.get("byteOffset", 0)
    assert start % 4 == 0
    assert acc.get("byteOffset", 0) + acc["count"] * width * 4 <= view["byteLength"]
    assert view["byteOffset"] + view["byteLength"] <= doc["buffers"][0]["byteLength"]
    out = np.frombuffer(blob, dtype, acc["count"] * width, start)
    return out.reshape(-1, width) if width > 1 else out


def parts(data: bytes) -> dict[str, dict]:
    """Each part node's arrays, extras and material name, by part id."""
    doc, blob = read_glb(data)
    out = {}
    for node in doc["nodes"][1:]:
        prim = doc["meshes"][node["mesh"]]["primitives"][0]
        out[node["name"]] = {
            "positions": accessor(doc, blob, prim["attributes"]["POSITION"]).astype(np.float64),
            "normals": accessor(doc, blob, prim["attributes"]["NORMAL"]).astype(np.float64),
            "indices": accessor(doc, blob, prim["indices"]).reshape(-1, 3),
            "extras": node["extras"],
            "material": doc["materials"][prim["material"]]["name"],
        }
    return out


def bounds(arrays) -> tuple[np.ndarray, np.ndarray]:
    stacked = np.vstack([a["positions"] for a in arrays])
    return stacked.min(axis=0), stacked.max(axis=0)


def solid(part: dict):
    """The part's mesh as a manifold3d solid, vertices merged by position."""
    mesh = m3d.Mesh(
        vert_properties=np.array(part["positions"], dtype=np.float32),
        tri_verts=np.array(part["indices"], dtype=np.uint32),
    )
    mesh.merge()
    return m3d.Manifold(mesh)


def ray_z(part: dict, x: float, y: float) -> list[float]:
    """The z of every surface crossing of the vertical line at (x, y), ascending."""
    hits = solid(part).ray_cast((x, y, -1.0), (x, y, 1.0))
    return sorted(h.position[2] for h in hits)


def catalog_with(tmp_path, kind: str, type_id: str, edit, new_id: str | None = None):
    """The bundled catalog with one entity edited, or with an edited copy added as `new_id`."""
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    obj = json.loads((root / kind / f"{type_id}.json").read_text())
    edit(obj)
    if new_id is not None:
        obj["id"] = new_id
    (root / kind / f"{new_id or type_id}.json").write_text(json.dumps(obj))
    return read_catalog(root)


def part_of(obj: dict, part_id: str) -> dict:
    return next(p for p in obj["parts"] if p["id"] == part_id)


# ---- determinism and digest -----------------------------------------------------


@pytest.mark.parametrize("type_id", TYPES)
def test_glb_is_byte_identical_when_built_twice(cat, glbs, type_id):
    assert build_glb(type_id, cat) == glbs[type_id]
    digest = assembly_digest(type_id, cat)
    assert digest == hashlib.sha256(glbs[type_id]).hexdigest()[:16]


def test_digests_differ_between_types(cat):
    assert len({assembly_digest(t, cat) for t in TYPES}) == len(TYPES)


def test_digests_are_pinned(glbs):
    assert {t: hashlib.sha256(glbs[t]).hexdigest()[:16] for t in TYPES} == DIGESTS


@pytest.mark.parametrize("toward", [np.inf, -np.inf])
def test_last_bit_differences_do_not_reach_the_bytes(cat, glbs, monkeypatch, toward):
    # macOS and Linux differ in the last bit of np.arccos (ws1b review, finding 1).
    arccos, arrays = np.arccos, geometry._arrays

    def nudged(solid):
        positions, triangles = arrays(solid)
        return np.nextafter(positions, toward), triangles

    monkeypatch.setattr(np, "arccos", lambda x: np.nextafter(arccos(x), toward))
    monkeypatch.setattr(geometry, "_arrays", nudged)
    for t in TYPES:
        assert build_glb(t, cat) == glbs[t], t


def test_the_chunked_normal_sum_gives_the_same_bytes(cat, glbs, monkeypatch):
    monkeypatch.setattr(geometry, "PAIR_CHUNK", 50)  # below the 77 faces at the point's apex
    for t in TYPES:
        assert build_glb(t, cat) == glbs[t], t


def test_normals_memory_stays_bounded_at_a_fine_cone_apex(tmp_path):
    # A 2000-point profile tapered to 0 puts 2000 faces on one vertex (ws1b review, finding 4).
    n = 2000
    points = [[0.015 * math.cos(2 * math.pi * i / n), 0.015 * math.sin(2 * math.pi * i / n)] for i in range(n)]

    def fine(obj):
        obj["profiles"] = {"fine": {"polygon": points}}
        part_of(obj, "cone")["profile"] = "fine"

    cat = catalog_with(tmp_path, ATT, POINT, fine)
    tracemalloc.start()
    try:
        build_glb(POINT, cat)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 64e6  # numpy's arrays; about 11 MB, and above 300 MB with every pair at once


def test_only_assembly_types_build(cat):
    with pytest.raises(KeyError):
        build_glb("sk6812", cat)
    with pytest.raises(KeyError):
        build_glb("no-such-type", cat)


# ---- structure ------------------------------------------------------------------


@pytest.mark.parametrize("type_id", TYPES)
def test_glb_structure(cat, glbs, type_id):
    entity = cat.get(type_id)
    doc, blob = read_glb(glbs[type_id])
    assert doc["asset"] == {"version": "2.0"}
    assert doc["scene"] == 0 and doc["scenes"] == [{"nodes": [0]}]
    root, *nodes = doc["nodes"]
    assert root["name"] == type_id
    assert root["children"] == list(range(1, len(entity.parts) + 1))
    assert [n["name"] for n in nodes] == [p.id for p in entity.parts]
    assert len(doc["meshes"]) == len(entity.parts)
    size = doc["buffers"][0]["byteLength"]
    assert len(blob) - 3 <= size <= len(blob) and not blob[size:].strip(b"\0")
    assert "uri" not in doc["buffers"][0]
    finishes = sorted({p.finish or "unspecified" for p in entity.parts})
    assert [m["name"] for m in doc["materials"]] == finishes

    for node, part in zip(nodes, entity.parts):
        assert node["extras"] == {"glow": part.glow, "gain": cat.num(type_id, part.gain), "part": part.id}
        (prim,) = doc["meshes"][node["mesh"]]["primitives"]
        assert prim["mode"] == 4 and set(prim["attributes"]) == {"POSITION", "NORMAL"}
        pos_acc = doc["accessors"][prim["attributes"]["POSITION"]]
        idx_acc = doc["accessors"][prim["indices"]]
        assert pos_acc["componentType"] == 5126 and pos_acc["type"] == "VEC3"
        assert idx_acc["componentType"] == 5125 and idx_acc["type"] == "SCALAR"
        assert doc["bufferViews"][pos_acc["bufferView"]]["target"] == 34962
        assert doc["bufferViews"][idx_acc["bufferView"]]["target"] == 34963
        positions = accessor(doc, blob, prim["attributes"]["POSITION"])
        normals = accessor(doc, blob, prim["attributes"]["NORMAL"])
        indices = accessor(doc, blob, prim["indices"])
        assert len(normals) == len(positions) == pos_acc["count"]
        assert np.array_equal(np.float32(pos_acc["min"]), positions.min(axis=0))
        assert np.array_equal(np.float32(pos_acc["max"]), positions.max(axis=0))
        assert len(indices) % 3 == 0 and indices.max() < len(positions)
        assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-5)


@pytest.mark.parametrize("type_id", TYPES)
def test_parts_are_closed_solids_with_outward_normals(glbs, type_id):
    limit = math.cos(math.radians(SMOOTH_ANGLE_DEG)) - 1e-5
    for name, part in parts(glbs[type_id]).items():
        body = solid(part)
        assert body.status() == m3d.Error.NoError, name
        assert body.volume() > 0, name  # counter-clockwise seen from outside
        p = part["positions"][part["indices"]]
        face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        face /= np.linalg.norm(face, axis=1, keepdims=True)
        corner = part["normals"][part["indices"]]
        assert np.einsum("tj,tkj->tk", face, corner).min() >= limit, name


@pytest.mark.parametrize(("type_id", "part"), [(BAR, "diffuser"), (POINT, "plug"), (EYE, "plug")])
def test_flat_feet_have_flat_normals(glbs, type_id, part):
    # The feet meet the walls at 39° (diffuser) and 28° (plug), so both edges are creases.
    mesh = parts(glbs[type_id])[part]
    z = mesh["positions"][mesh["indices"]][:, :, 2]
    feet = mesh["indices"][(z == z.min()).all(axis=1)]
    assert len(feet) >= 2
    assert (mesh["normals"][feet] == [0.0, 0.0, -1.0]).all()


# ---- the bar (INV-001) ------------------------------------------------------------


def test_bar_bounds(glbs):
    # docs/studio/domain-model.md:58: axis_z = 45.5 - 30.2/2 = 30.4 mm, so the
    # housing base is at z = -30.4 mm and the diffuser top at +15.1 mm.
    # domain-model.md:367 gives x ±9 mm; that is the 18 mm housing. The
    # 30.2 mm diffuser is wider and reaches ±15.1 mm.
    bar = parts(glbs[BAR])
    lo, hi = bounds(bar.values())
    assert lo == pytest.approx([-15.1 * MM, -0.5, -30.4 * MM], abs=TOL)
    assert hi == pytest.approx([15.1 * MM, 0.5, 15.1 * MM], abs=TOL)
    lo, hi = bounds([bar["housing"], bar["cap_a"], bar["cap_b"]])
    assert lo == pytest.approx([-9 * MM, -0.5, -30.4 * MM], abs=TOL)
    assert hi == pytest.approx([9 * MM, 0.5, -11.9 * MM], abs=TOL)


def test_bar_diffuser_flat_sits_on_the_housing(glbs):
    bar = parts(glbs[BAR])
    diffuser, housing = bar["diffuser"]["positions"], bar["housing"]["positions"]
    flat = -11.9 * MM  # housing_h - axis_z = 18.5 - 30.4 mm
    assert diffuser[:, 2].min() == pytest.approx(flat, abs=TOL)
    assert housing[:, 2].max() == pytest.approx(flat, abs=TOL)
    feet = np.abs(diffuser[np.abs(diffuser[:, 2] - flat) < TOL, 0])
    chord = math.sqrt(15.1**2 - 11.9**2) * MM  # 9.296 mm, half the 18.6 mm flat
    inner = math.sqrt(13.6**2 - 11.9**2) * MM
    assert feet.max() == pytest.approx(chord, abs=FACET)
    assert feet.min() == pytest.approx(inner, abs=FACET)
    assert abs(feet.max() - 9 * MM) < 1 * MM  # the flat-chord check, domain-model.md:320


def test_bar_tslot_is_open_on_the_bottom(glbs):
    housing = parts(glbs[BAR])["housing"]
    # Up the middle, the first surface is the slot's ceiling, lip_t + slot_h
    # above the base: -30.4 + 1.5 + 3.0 = -25.9 mm.
    assert ray_z(housing, 0.0003, 0.123) == pytest.approx([-25.9 * MM, -11.9 * MM], abs=TOL)
    # Under a lip, inside the cavity: lip bottom, lip top, ceiling, top face.
    for x in (-5.5 * MM, 5.5 * MM):
        assert ray_z(housing, x, 0.123) == pytest.approx([-30.4 * MM, -28.9 * MM, -25.9 * MM, -11.9 * MM], abs=TOL)


def test_bar_leds_sit_at_the_pixel_positions(cat, glbs):
    doc, _ = read_glb(glbs[BAR])
    assert doc["nodes"][0]["extras"] == {"pixel_axis": {"y0": -0.5, "span": 1.0, "count": 64}}
    leds = parts(glbs[BAR])["leds"]["positions"]
    assert len(leds) == 64 * 24  # 64 boxes, 4 vertices per face
    rig = compile_rig(
        load_arrangement({"format": "pewpew.arrangement", "version": 1, "fixtures": [{"id": "b", "type": BAR}]}), cat
    )
    box = np.argsort(leds[:, 1], kind="stable").reshape(64, 24)
    centres = (leds[box].min(axis=1) + leds[box].max(axis=1)) / 2
    assert centres == pytest.approx(rig.positions_m, abs=TOL)
    size = leds[box].max(axis=1) - leds[box].min(axis=1)
    assert size == pytest.approx(np.tile([5 * MM, 5 * MM, 1.6 * MM], (64, 1)), abs=TOL)


# ---- the tube (INV-002) -----------------------------------------------------------


def test_tube_builds_from_catalog_data_alone(glbs):
    # No tube id appears in rig code (test_rig_catalog.py checks geometry.py too).
    doc, _ = read_glb(glbs[TUBE])
    axis = doc["nodes"][0]["extras"]["pixel_axis"]
    assert axis["count"] == 36
    assert axis["span"] == pytest.approx(1.46) and axis["y0"] == pytest.approx(-0.73)
    tube = parts(glbs[TUBE])
    assert list(tube) == ["tube", "cap_a", "cap_b"]
    assert tube["tube"]["extras"]["glow"] == "pixels" and tube["tube"]["material"] == "opal"
    assert tube["cap_a"]["material"] == tube["cap_b"]["material"] == "aluminum"
    lo, hi = bounds(tube.values())
    assert lo == pytest.approx([-21 * MM, -0.75, -21 * MM], abs=TOL)
    assert hi == pytest.approx([21 * MM, 0.75, 21 * MM], abs=TOL)
    lo, hi = bounds([tube["tube"]])
    assert (lo[1], hi[1]) == pytest.approx((-0.73, 0.73), abs=TOL)
    hits = ray_z(tube["tube"], 0.0003, 0.123)
    assert hits == pytest.approx([-20 * MM, -18 * MM, 18 * MM, 20 * MM], abs=FACET)


# ---- the attachments ----------------------------------------------------------------


def ring(positions: np.ndarray, y: float) -> set[tuple[float, float]]:
    at = positions[np.abs(positions[:, 1] - y) < TOL]
    return {(round(x, 7), round(z, 7)) for x, _, z in at}


def test_point_is_a_cone_on_the_host_profile(glbs):
    doc, _ = read_glb(glbs[POINT])
    assert doc["nodes"][0]["extras"] == {"pixel_axis": None}
    point = parts(glbs[POINT])
    assert list(point) == ["cone", "plug"]
    assert {p["extras"]["glow"] for p in point.values()} == {"pixels"}
    assert {p["extras"]["gain"] for p in point.values()} == {0.25}
    cone = point["cone"]["positions"]
    # The apex is on the axis. Each side face has its own vertex there.
    apex = np.flatnonzero(cone[:, 1] == cone[:, 1].max())
    assert cone[apex] == pytest.approx(np.tile([0.0, 0.1, 0.0], (len(apex), 1)), abs=TOL)
    indices = point["cone"]["indices"]
    assert sorted(indices[np.isin(indices, apex)]) == sorted(apex)
    # The base is the bar's diffuser outline, so the cone fits the end flush.
    diffuser = parts(glbs[BAR])["diffuser"]["positions"]
    assert ring(cone, 0.0) <= ring(diffuser, 0.5)
    lo, hi = bounds([point["plug"]])
    assert lo == pytest.approx([-13.6 * MM, -15 * MM, -11.9 * MM], abs=TOL)
    assert hi == pytest.approx([13.6 * MM, 0.0, 13.6 * MM], abs=TOL)


def test_eye_is_a_slotted_blade_on_a_plug(glbs):
    eye = parts(glbs[EYE])
    assert list(eye) == ["plug", "blade", "blade_tip"]
    lo, hi = bounds([eye["blade"], eye["blade_tip"]])
    assert lo == pytest.approx([-15 * MM, 0.0, -10 * MM], abs=TOL)
    assert hi == pytest.approx([15 * MM, 0.1, 10 * MM], abs=TOL)
    blade = eye["blade"]
    assert ray_z(blade, 0.0003, 0.05) == []  # through the slot
    assert ray_z(blade, 12 * MM, 0.05) == pytest.approx([-10 * MM, 10 * MM], abs=TOL)


def test_an_attachment_builds_on_hosts_that_mesh_it_alike(tmp_path, glbs):
    # A 2 m bar has the same end profiles, so the point and the eye keep their GLBs.
    cat = catalog_with(tmp_path, FIX, BAR, lambda o: o["dims"]["length"].update(v=2.0), new_id="bar-2m")
    for t in (POINT, EYE):
        assert build_glb(t, cat) == glbs[t], t
    build_glb("bar-2m", cat)


def test_an_attachment_refuses_hosts_that_mesh_it_differently(tmp_path):
    cat = catalog_with(tmp_path, FIX, BAR, lambda o: o["dims"]["diffuser_d"].update(v=0.032), new_id="wide-bar")
    with pytest.raises(GeometryError, match=f"meshes differently on {BAR} and wide-bar"):
        build_glb(POINT, cat)


# ---- data that cannot be meshed ------------------------------------------------------


def _no_accepts(obj):
    for anchor in obj["anchors"].values():
        anchor.pop("accepts", None)


def _set(part_id: str, **fields):
    return lambda obj: part_of(obj, part_id).update(fields)


BAD_DATA = {
    "no parts": (FIX, BAR, lambda o: o.update(parts=[]), BAR, "has no parts"),
    "no host": (FIX, BAR, _no_accepts, POINT, "no fixture type accepts"),
    "negative taper": (ATT, POINT, _set("cone", taper_to=-1), POINT, "taper_to must be at least 0"),
    "zero box size": (FIX, BAR, _set("strip", box=[0.01, 0, 0.01]), BAR, "box sizes"),
    "zero rect size": (FIX, BAR, lambda o: o["profiles"]["housing"]["minus"][0].update(rect=[0, "lip_t"]), BAR, "rect"),
    "huge range": (FIX, BAR, _set("diffuser", range_m=[0, 1e300]), BAR, "float32 range"),
    "at on a profile part": (FIX, BAR, _set("diffuser", at=[0, 0, 0.005]), BAR, "takes no at"),
    "at_pixels on a profile part": (FIX, BAR, _set("diffuser", at_pixels=True), BAR, "takes no at"),
    "range_m on a box part": (FIX, BAR, _set("strip", range_m=[0, 1]), BAR, "takes no range_m"),
    "taper_to on a box part": (FIX, BAR, _set("strip", taper_to=0.5), BAR, "takes no range_m"),
    "axis on a box part": (FIX, BAR, _set("strip", axis="z"), BAR, "takes no range_m"),
}


@pytest.mark.parametrize(("kind", "type_id", "edit", "built", "match"), BAD_DATA.values(), ids=BAD_DATA.keys())
def test_data_that_cannot_be_meshed_raises(tmp_path, kind, type_id, edit, built, match):
    cat = catalog_with(tmp_path, kind, type_id, edit)
    with pytest.raises(GeometryError, match=match):
        build_glb(built, cat)
