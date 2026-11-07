"""The bundled catalog: loading, cross-checks, digest and provenance."""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

import pytest

import pewpew.rig as rig_pkg
from pewpew.rig import RigError, compile_rig, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import DATA_ROOT
from pewpew.rig.models import Sourced

RIG_SRC = Path(rig_pkg.__file__).parent


def codes(exc: RigError) -> set[str]:
    return {i.code for i in exc.issues}


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    return root


def edit(path: Path, fn) -> None:
    obj = json.loads(path.read_text())
    fn(obj)
    path.write_text(json.dumps(obj))


def test_bundled_catalog_loads_every_kind():
    cat = load_catalog()
    assert set(cat.fixture_types) == {"clen-rgbw-bar-1m", "clen-360-tube-1500"}
    assert set(cat.attachment_types) == {"point-v0", "eye-v0"}
    assert set(cat.of_kind("chipset")) == {"sk6812", "ucs1903n"}
    assert set(cat.of_kind("connector")) == {"clen-4pin", "barrel-5.5x2.1"}
    assert set(cat.cables) == {"wire-16awg-pair", "wire-18awg-pair"}
    assert set(cat.psus) == {"meanwell-lrs-350-24", "btf-24v-5a-120w"}
    assert set(cat.of_kind("firmware")) == {"wled-16.0.1"}
    assert set(cat.controllers) == {"esp32s3-devkitc1-ahct125", "quinled-dig-octa-32-8l"}
    assert load_catalog() is cat


def test_bar_dims_and_the_flat_chord_check():
    d = load_catalog().dims("clen-rgbw-bar-1m")
    assert d["axis_z"] == pytest.approx(0.0304)
    assert d["flat_z"] == pytest.approx(0.0119)
    # docs/studio/domain-model.md:58: the flat's chord matches the 18 mm housing.
    chord = 2 * math.sqrt((d["diffuser_d"] / 2) ** 2 - d["flat_z"] ** 2)
    assert chord == pytest.approx(0.0186, abs=5e-5)
    assert abs(chord - d["housing_w"]) < 0.001


def test_wire_resistance_matches_the_awg_table():
    # R/m = ρ/A, ρ = 1/(58 MS/m): 13.17 and 20.95 mΩ/m
    # (https://en.wikipedia.org/wiki/American_wire_gauge).
    cat = load_catalog()
    rho = 1 / 58e6
    for cable, expected in (("wire-16awg-pair", 13.17e-3), ("wire-18awg-pair", 20.95e-3)):
        area = cat.need(cable, cat.get(cable).conductors_mm2.vplus) * 1e-6
        assert rho / area == pytest.approx(expected, abs=0.01e-3)


def test_digest_is_stable_and_follows_content(data_copy):
    assert read_catalog(DATA_ROOT).digest == load_catalog().digest
    path = data_copy / "fixture_type" / "clen-rgbw-bar-1m.json"
    path.write_text(json.dumps(json.loads(path.read_text()), indent=4))
    assert read_catalog(data_copy).digest == load_catalog().digest
    edit(path, lambda o: o["dims"]["length"].update(v=1.003))
    assert read_catalog(data_copy).digest != load_catalog().digest


def test_unknown_field_and_missing_src_are_errors(data_copy):
    path = data_copy / "chipset" / "sk6812.json"
    edit(path, lambda o: o.update(speed=800))
    with pytest.raises(RigError) as exc:
        read_catalog(data_copy)
    assert "extra_forbidden" in codes(exc.value)
    assert (exc.value.issues[0].ref or "").startswith("chipset/sk6812.json")

    edit(path, lambda o: (o.pop("speed"), o["reset_s"].pop("src")))
    with pytest.raises(RigError) as exc:
        read_catalog(data_copy)
    assert "missing_src" in codes(exc.value)


def test_unresolved_refs_and_expression_cycles_are_errors(data_copy):
    bar = data_copy / "fixture_type" / "clen-rgbw-bar-1m.json"
    edit(bar, lambda o: o["pixels"].update(chipset="ws2812"))
    edit(bar, lambda o: o["dims"].update(axis_z={"v": "flat_z + housing_h", "status": "derived"}))
    with pytest.raises(RigError, match="cycle"):
        read_catalog(data_copy)
    edit(bar, lambda o: o["dims"].update(axis_z={"v": "overall_h - diffuser_d/2", "status": "derived"}))
    with pytest.raises(RigError) as exc:
        read_catalog(data_copy)
    assert codes(exc.value) == {"unresolved_ref"}


def test_file_name_must_match_the_id(data_copy):
    (data_copy / "psu" / "meanwell-lrs-350-24.json").rename(data_copy / "psu" / "lrs.json")
    with pytest.raises(RigError) as exc:
        read_catalog(data_copy)
    assert codes(exc.value) == {"id_mismatch"}


def test_no_catalog_id_appears_in_rig_code():
    # docs/studio/domain-model.md:151-153: a new fixture is data, never code.
    ids = [e.id for e in load_catalog()]
    for path in sorted(RIG_SRC.glob("*.py")):
        text = path.read_text()
        found = [i for i in ids if i in text]
        assert not found, f"{path.name} names catalog ids {found}"


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def test_every_url_in_the_data_is_a_full_https_link():
    bare = re.compile(r"\bwww\.|\b[\w-]+\.(?:com|org|info|net|io|ge|sk)/")
    for path in sorted(DATA_ROOT.rglob("*.json")):
        for s in strings(json.loads(path.read_text())):
            assert "http://" not in s, f"{path.name}: {s}"
            rest = re.sub(r"https://\S+", "", s)
            assert not bare.search(rest), f"{path.name}: bare link in {s!r}"


def test_every_unmeasured_fact_names_its_source():
    def facts(model):
        if isinstance(model, Sourced):
            yield model
        if hasattr(model, "__pydantic_fields__"):
            for name in type(model).model_fields:
                yield from facts(getattr(model, name))
        elif isinstance(model, dict):
            for v in model.values():
                yield from facts(v)
        elif isinstance(model, (list, tuple)):
            for v in model:
                yield from facts(v)

    seen = 0
    for entity in load_catalog():
        for fact in facts(entity):
            seen += 1
            assert fact.src or fact.status == "derived", entity.id
    assert seen > 50


def test_no_home_paths_or_private_note_cites_in_committed_rig_files():
    root = RIG_SRC.parent.parent.parent
    paths = [*RIG_SRC.rglob("*.json"), *RIG_SRC.glob("*.py"), *(root / "schemas").glob("*.json")]
    for path in paths:
        assert "/Users/" not in path.read_text(), path
        assert not re.search(r"\bAsh\b|Aesc|[Vv]ault", path.read_text()), path


def test_catalog_json_has_what_the_studio_lists():
    out = load_catalog().to_json()
    assert set(out) >= {"digest", "fixture_types", "attachment_types", "controllers", "psus", "cables", "presets"}
    json.dumps(out)
    bar = next(f for f in out["fixture_types"] if f["id"] == "clen-rgbw-bar-1m")
    assert bar["name"] == "1M LED Pixel Bar"
    assert bar["pixels"]["count"]["v"] == 64
    assert bar["power"]["max_w"] == {"v": 25.6, "status": "stated", "src": bar["power"]["max_w"]["src"]}
    assert bar["dims"]["axis_z"]["expr"] == "overall_h - diffuser_d/2"
    assert bar["dims"]["axis_z"]["v"] == pytest.approx(0.0304)
    point = next(a for a in out["attachment_types"] if a["id"] == "point-v0")
    assert point["fits"] == "diffuser_outer" and point["dims"]["len"]["v"] == 0.1
    presets = {p["name"]: {q["name"]: q for q in p["params"]} for p in out["presets"]}
    assert presets["ring"]["count"]["required"] is True
    assert presets["ring"]["data_in"]["default"] == "inner"
    assert presets["ring"]["attach"]["default"] == {"inner": None, "outer": None}
    assert presets["array"]["member"]["default"]["position_m"] == [0.0, 0.0, 0.0]


def test_inv002_compiles_from_catalog_data_alone():
    # docs/studio/domain-model.md:361: 36 px, 3 B/px, 30 µs/px and 1.5 A.
    cat = load_catalog()
    arr = load_arrangement(
        {
            "format": "pewpew.arrangement",
            "version": 1,
            "fixtures": [{"id": "tube1", "type": "clen-360-tube-1500"}],
        }
    )
    rig = compile_rig(arr, cat)
    spec = cat.spec("clen-360-tube-1500")
    assert rig.n == 36
    assert spec.bytes_per_px == 3
    assert spec.t_px_s == pytest.approx(30e-6, rel=1e-12)
    assert spec.current_a == 1.5
    assert not rig.normals.any()  # omnidirectional
    span = 1.5 - 2 * 0.02
    assert rig.positions_m[0, 1] == pytest.approx(-span / 2 + span / 72)
