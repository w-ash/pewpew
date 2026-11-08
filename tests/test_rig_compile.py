"""compile_rig: placement, pixel order, normalization and the validation tiers."""

from __future__ import annotations

import copy
import json
import math
import re
import shutil

import numpy as np
import pytest

from pewpew.rig import EXAMPLES, RigError, compile_rig, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import CATALOG_ENTRIES_DIR
from pewpew.rig.pose import MVR_C, from_three, matrix_to_quat, quat_to_matrix

BAR = "clen-rgbw-bar-1m"
TUBE = "clen-360-tube-1500"
S3 = "esp32s3-devkitc1-ahct125"
GOLDEN = EXAMPLES / "golden-rings.json"

# docs/studio/domain-model.md:148-167, the explicit-wiring example.
RING_AND_TUBE = {
    "format": "pewpew.arrangement",
    "version": 1,
    "name": "ring of 8 + tube",
    "groups": [
        {
            "id": "ring",
            "preset": "ring",
            "type": BAR,
            "count": 8,
            "start_radius_m": 0.618034,
            "angle_offset_deg": 0,
            "tilt_deg": 30,
            "roll_deg": 0,
            "data_in": "inner",
            "attach": {"inner": "point-v0", "outer": "eye-v0"},
            "pose": {"position_m": [0, 0.9, 0], "quat_xyzw": [0, 0, 0, 1]},
        }
    ],
    "fixtures": [
        {"id": "tube1", "type": TUBE, "pose": {"position_m": [0, 2.0, 0], "quat_xyzw": [0, 0, 0.7071068, 0.7071068]}}
    ],
    "controllers": [{"id": "c1", "profile": S3, "position_m": [0, 0, -1.5]}],
    "psus": [{"id": "p1", "type": "meanwell-lrs-350-24"}],
    "wiring": {
        "target_fps": 40,
        "chains": [
            {"id": "A", "controller": "c1", "output": "rmt0", "fixtures": ["ring/0", "ring/1", "ring/2", "ring/3"]},
            {"id": "B", "controller": "c1", "output": "rmt1", "fixtures": ["ring/4", "ring/5", "ring/6", "ring/7"]},
            {"id": "T", "controller": "c1", "output": "rmt2", "fixtures": ["tube1"]},
        ],
        "feeds": [
            {
                "id": "f1",
                "psu": "p1",
                "chain": "A",
                "first": 0,
                "count": 2,
                "cable": "wire-16awg-pair",
                "length_m": 2.0,
                "fuse_a": 3,
            },
            {
                "id": "f2",
                "psu": "p1",
                "chain": "A",
                "first": 2,
                "count": 2,
                "cable": "wire-16awg-pair",
                "length_m": 2.0,
                "fuse_a": 3,
            },
            {
                "id": "f3",
                "psu": "p1",
                "chain": "B",
                "first": 0,
                "count": 2,
                "cable": "wire-16awg-pair",
                "length_m": 2.0,
                "fuse_a": 3,
            },
            {
                "id": "f4",
                "psu": "p1",
                "chain": "B",
                "first": 2,
                "count": 2,
                "cable": "wire-16awg-pair",
                "length_m": 2.0,
                "fuse_a": 3,
            },
            {
                "id": "f5",
                "psu": "p1",
                "chain": "T",
                "first": 0,
                "count": 1,
                "cable": "wire-16awg-pair",
                "length_m": 2.0,
                "fuse_a": 3,
            },
        ],
    },
}


def arrangement(**parts) -> dict:
    return {"format": "pewpew.arrangement", "version": 1, **parts}


def compiled(obj):
    return compile_rig(load_arrangement(obj), load_catalog())


def codes(rig, *levels) -> list[tuple[str, str]]:
    """(level, code) of each issue at `levels`, or of every issue that does not rest on an assumed value."""
    return [(i.level, i.code) for i in rig.issues if (i.level in levels if levels else i.code != "rests_on_assumed")]


def error_codes(obj) -> set[str]:
    with pytest.raises(RigError) as exc:
        compiled(obj)
    return {i.code for i in exc.value.issues if i.level == "error"}


def world(matrix16, local) -> np.ndarray:
    return (from_three(matrix16) @ np.array([*local, 1.0]))[:3]


@pytest.fixture(scope="module")
def golden():
    return compiled(GOLDEN)


# ---- golden rings against the prototype (docs/studio/prototype/golden-tubes-3d.html) ----


def ends(rig, group=None):
    return np.array([world(f.matrix, (0, y, 0)) for f in rig.fixtures if group in (None, f.group) for y in (-0.5, 0.5)])


def tips(rig):
    return np.array(
        [world(m, (0, 0.1, 0)) for f in rig.fixtures for m in f.attachment_matrices.values() if m is not None]
    )


def plan_radius(points):
    return np.hypot(points[:, 0], points[:, 2])


def test_golden_rings_match_the_prototype_dimensions(golden):
    assert golden.n == 48 * 64
    pivots = {f.group: math.hypot(f.matrix[12], f.matrix[14]) for f in golden.fixtures}
    assert pivots["inner"] == pytest.approx(1.118034, abs=1e-9)  # GT:268, 111.8
    assert pivots["outer"] == pytest.approx(1.5, abs=1e-12)  # GT:268, 150.0
    inner = plan_radius(ends(golden, "inner"))
    assert inner.min() == pytest.approx(0.685, abs=5e-4)  # GT:270, 68.5-155.1
    assert inner.max() == pytest.approx(1.551, abs=5e-4)
    # GT:273 and GT:431-441: overall width 386.6 cm without points and eyes.
    assert 2 * plan_radius(ends(golden)).max() == pytest.approx(3.866, abs=5e-4)
    assert 2 * plan_radius(tips(golden)).max() == pytest.approx(4.039, abs=5e-4)
    # GT:269: band height 50.0 cm, and 60 cm with the 10 cm attachments.
    assert np.ptp(ends(golden)[:, 1]) == pytest.approx(0.5, abs=1e-12)
    assert np.ptp(tips(golden)[:, 1]) == pytest.approx(0.6, abs=1e-12)


def test_ring_basis_matches_the_prototype(golden):
    # GT:426-429: dir, side, face = side × dir, then makeBasis(side, dir, face).
    a = math.radians(30)
    for f in golden.fixtures:
        k = int(f.id.split("/")[1])
        t = math.radians((0 if f.group == "inner" else 7.5) + k * 360 / 24)
        side = np.array([-math.sin(t), 0, math.cos(t)])
        direction = np.array([math.cos(a) * math.cos(t), math.sin(a), math.cos(a) * math.sin(t)])
        expected = np.column_stack([side, direction, np.cross(side, direction)])
        r = from_three(f.matrix)[:3, :3]
        np.testing.assert_allclose(r, expected, atol=1e-12, rtol=0)
        q = matrix_to_quat(r)
        assert q[3] >= 0
        np.testing.assert_allclose(quat_to_matrix(q), r, atol=1e-12, rtol=0)


def test_attachments_follow_the_ring_ends(golden):
    f = golden.fixtures[0]
    assert f.attachments == {"end_a": "point-v0", "end_b": "eye-v0"}
    point, eye = (world(f.attachment_matrices[k], (0, 0.1, 0)) for k in ("end_a", "end_b"))
    assert math.hypot(point[0], point[2]) < math.hypot(eye[0], eye[2])


# ---- pixels ---------------------------------------------------------------------


def test_pixel_pitch_is_exact():
    rig = compiled(arrangement(fixtures=[{"id": "bar", "type": BAR}]))
    i = np.arange(64)
    np.testing.assert_array_equal(rig.positions_m[:, 1], -0.5 + (i + 0.5) / 64)
    assert set(np.diff(rig.positions_m[:, 1])) == {0.015625}
    assert not rig.positions_m[:, 0].any()
    flat_z = load_catalog().dims(BAR)["flat_z"]
    np.testing.assert_array_equal(rig.positions_m[:, 2], -flat_z)
    np.testing.assert_array_equal(rig.normals, np.tile([0.0, 0.0, 1.0], (64, 1)))
    np.testing.assert_array_equal(rig.pixel_in_fixture, i)


def test_data_in_outer_reverses_world_order_and_keeps_facing():
    ring = {
        "id": "r",
        "preset": "ring",
        "type": BAR,
        "count": 3,
        "start_radius_m": 1.0,
        "tilt_deg": 20,
        "attach": {"inner": "point-v0", "outer": "eye-v0"},
    }
    inner = compiled(arrangement(groups=[ring]))
    outer = compiled(arrangement(groups=[{**ring, "data_in": "outer"}]))
    for f in range(3):
        a = inner.positions_m[f * 64 : (f + 1) * 64]
        b = outer.positions_m[f * 64 : (f + 1) * 64]
        np.testing.assert_allclose(b, a[::-1], atol=1e-12, rtol=0)
    np.testing.assert_allclose(outer.normals, inner.normals, atol=1e-12, rtol=0)
    assert outer.fixtures[0].attachments == {"end_a": "eye-v0", "end_b": "point-v0"}


def test_mapping_is_the_contained_plan_frame(golden):
    m = golden.mapping
    assert m.dtype == np.float32 and m.shape == (golden.n, 3)
    assert not m.flags.writeable
    plan = golden.positions_m @ MVR_C.T
    ext = np.ptp(plan, axis=0)
    longest = int(ext.argmax())
    assert m[:, longest].min() == 0.0 and m[:, longest].max() == 1.0
    np.testing.assert_allclose((m.min(axis=0) + m.max(axis=0)) / 2, 0.5, atol=1e-6)
    np.testing.assert_allclose(np.ptp(m, axis=0), ext / ext.max(), atol=1e-6)


def at(y: float, z: float, type_id: str = BAR) -> dict:
    return {"type": type_id, "pose": {"position_m": [0, y, z], "quat_xyzw": [0, 0, 0, 1]}}


def test_arrangement_up_is_plan_height_and_arrangement_depth_is_plan_y():
    fixtures = [
        {"id": "low", **at(0.0, 0.0)},
        {"id": "high", **at(2.0, 0.0)},
        {"id": "back", **at(0.0, -1.0)},
        {"id": "front", **at(0.0, 1.0)},
    ]
    rig = compiled(arrangement(fixtures=fixtures))
    centre = {f.id: rig.mapping[rig.fixture_of == i].mean(axis=0) for i, f in enumerate(rig.fixtures)}
    assert centre["high"][2] > centre["low"][2]
    assert centre["back"][1] > centre["front"][1]
    # The fixtures differ in the file's y only on `high`, so that is plan z alone.
    assert centre["high"][1] == pytest.approx(centre["low"][1], abs=1e-6)
    # Matrices and positions stay y-up.
    assert rig.positions_m[rig.fixture_of == 1, 1].mean() > rig.positions_m[rig.fixture_of == 0, 1].mean()


# ---- wiring order ---------------------------------------------------------------


def test_explicit_chains_index_pixels_in_data_order():
    rig = compiled(RING_AND_TUBE)
    assert rig.n == 548  # docs/studio/domain-model.md:236
    got = [(s.chain, s.start, s.count, s.led_type, s.color_order) for s in rig.slices]
    assert got == [("A", 0, 256, 30, "GRBW"), ("B", 256, 256, 30, "GRBW"), ("T", 512, 36, 22, "RGB")]
    assert [(c.controller, c.start, c.count) for c in rig.controller_slices] == [("c1", 0, 548)]
    assert [f.id for f in rig.fixtures][:2] == ["ring/0", "ring/1"]
    assert rig.fixtures[-1].pixel_start == 512 and rig.fixtures[-1].chain == "T"
    assert codes(rig) == []
    assert len(rig.feeds) == 5


def test_order_is_controllers_in_file_order_then_outputs_in_profile_order():
    obj = copy.deepcopy(RING_AND_TUBE)
    obj["controllers"] = [{"id": "c2", "profile": S3}, {"id": "c1", "profile": S3}]
    chains = obj["wiring"]["chains"]
    chains[0]["output"], chains[1]["output"] = "rmt1", "rmt0"  # A on rmt1, B on rmt0
    chains[2]["controller"] = "c2"
    rig = compiled(obj)
    assert [s.chain for s in rig.slices] == ["T", "B", "A"]
    assert [f.id for f in rig.fixtures][:2] == ["tube1", "ring/4"]
    assert [(c.controller, c.start, c.count) for c in rig.controller_slices] == [("c2", 0, 36), ("c1", 36, 512)]


def test_unwired_fixtures_come_last_in_authoring_order():
    obj = copy.deepcopy(RING_AND_TUBE)
    obj["wiring"] = {"chains": [{"id": "T", "controller": "c1", "output": "rmt0", "fixtures": ["tube1"]}]}
    rig = compiled(obj)
    assert [f.id for f in rig.fixtures] == ["tube1", *(f"ring/{k}" for k in range(8))]
    assert rig.fixtures[1].chain is None
    assert codes(rig) == [("warning", "unwired"), ("warning", "unfed")]


# ---- validation tiers -----------------------------------------------------------


def with_chains(*chains, fixtures=None):
    return arrangement(
        fixtures=fixtures or [{"id": f"b{i}", "type": BAR} for i in range(4)] + [{"id": "t0", "type": TUBE}],
        controllers=[{"id": "c1", "profile": S3}],
        wiring={"chains": list(chains)},
    )


def test_structural_errors():
    chain = lambda cid, out, *fx: {"id": cid, "controller": "c1", "output": out, "fixtures": list(fx)}
    assert error_codes(with_chains(chain("A", "rmt0", "b0", "b1"), chain("B", "rmt1", "b1"))) == {
        "fixture_in_two_chains"
    }
    assert error_codes(with_chains(chain("A", "rmt0", "b0"), chain("B", "rmt0", "b1"))) == {"output_used_twice"}
    assert error_codes(with_chains(chain("A", "rmt0", "b0", "t0"))) == {"mixed_pixel_format"}
    assert error_codes(with_chains(chain("A", "rmt9", "b0"))) == {"unresolved_ref"}
    assert error_codes(with_chains(chain("A", "rmt0", "nope"))) == {"unresolved_ref"}
    assert error_codes(with_chains(chain("A", "rmt0", "b0"), chain("A", "rmt1", "b1"))) == {"duplicate_id"}
    assert error_codes(arrangement(fixtures=[{"id": "x", "type": "no-such-bar"}])) == {"unresolved_ref"}
    assert error_codes(arrangement(fixtures=[{"id": "x", "type": BAR}, {"id": "x", "type": BAR}])) == {"duplicate_id"}
    ring = {"id": "g", "preset": "ring", "type": BAR, "count": 2, "start_radius_m": 1}
    assert error_codes(arrangement(groups=[ring, ring])) == {"duplicate_id"}
    feed = {"id": "f", "psu": "p1", "chain": "A", "first": 1, "count": 2, "cable": "wire-16awg-pair", "length_m": 1}
    obj = with_chains(chain("A", "rmt0", "b0", "b1"))
    obj["psus"] = [{"id": "p1", "type": "meanwell-lrs-350-24"}]
    obj["wiring"]["feeds"] = [feed]
    assert error_codes(obj) == {"feed_range"}


def test_attachment_errors():
    on = lambda type_id, attach: arrangement(fixtures=[{"id": "x", "type": type_id, "attach": attach}])
    assert error_codes(on(TUBE, {"end_a": "point-v0"})) == {"attach_mismatch"}  # the tube's ends accept nothing
    assert error_codes(on(BAR, {"end_a": "cone-v9"})) == {"unresolved_ref"}
    assert error_codes(on(BAR, {"middle": "point-v0"})) == {"unresolved_ref"}
    assert compiled(on(BAR, {"end_b": "eye-v0"})).fixtures[0].attachments == {"end_a": None, "end_b": "eye-v0"}


def test_missing_led_type_is_an_error(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    fw = root / "firmware" / "wled-16.0.1.json"
    obj = json.loads(fw.read_text())
    obj["led_types"] = [t for t in obj["led_types"] if t["chipset"] != "ucs1903n"]
    fw.write_text(json.dumps(obj))
    arr = load_arrangement(with_chains({"id": "T", "controller": "c1", "output": "rmt0", "fixtures": ["t0"]}))
    with pytest.raises(RigError) as exc:
        compile_rig(arr, read_catalog(root))
    assert {i.code for i in exc.value.issues if i.level == "error"} == {"missing_led_type"}


@pytest.mark.parametrize(
    ("pose", "code"),
    [
        ({"quat_xyzw": [0, 0, 0, 1], "aim": {"axis": [0, 1, 0]}}, "quat_and_aim"),
        ({"quat_xyzw": [0, 0, 0, 1.001]}, "bad_quaternion"),
        ({"aim": {"axis": [0, 0, 0]}}, "bad_aim"),
        ({"position_m": [0, 0, 0], "scale": 2}, "extra_forbidden"),
    ],
)
def test_pose_errors_refuse_the_file(pose, code):
    with pytest.raises(RigError) as exc:
        load_arrangement(arrangement(fixtures=[{"id": "x", "type": BAR, "pose": pose}]))
    assert code in {i.code for i in exc.value.issues}


def test_quaternions_are_stored_canonical():
    arr = load_arrangement(arrangement(fixtures=[{"id": "x", "type": BAR, "pose": {"quat_xyzw": [0, 0, -0.6, -0.8]}}]))
    assert arr.fixtures[0].pose.quat_xyzw == pytest.approx((0.0, 0.0, 0.6, 0.8), abs=1e-15)


def test_oversize_arrangements_are_refused_before_expansion():
    ring = lambda gid, n: {"id": gid, "preset": "ring", "type": BAR, "count": n, "start_radius_m": 1}
    grid = {"id": "g", "preset": "array", "type": BAR, "counts": [20, 20], "steps_m": [[1, 0, 0], [0, 1, 0]]}
    for obj in (
        arrangement(groups=[ring("r", 10**9)]),
        arrangement(groups=[ring("a", 150), ring("b", 60)]),
        arrangement(groups=[grid]),
        arrangement(groups=[ring("a", 200)], fixtures=[{"id": "x", "type": BAR}]),
    ):
        with pytest.raises(RigError) as exc:
            load_arrangement(obj)
        assert "too_many_fixtures" in {i.code for i in exc.value.issues}
    assert compiled(arrangement(groups=[ring("a", 200)])).n == 200 * 64


def test_firmware_caps_are_violations_and_warnings():
    def bars_on_one_output(n, profile=S3, output="rmt0"):
        return arrangement(
            fixtures=[{"id": f"b{i}", "type": BAR} for i in range(n)],
            controllers=[{"id": "c1", "profile": profile}],
            wiring={
                "chains": [{"id": "A", "controller": "c1", "output": output, "fixtures": [f"b{i}" for i in range(n)]}]
            },
        )

    levels = lambda rig: [c for c in codes(rig) if c[1] != "unfed"]
    assert levels(compiled(bars_on_one_output(12))) == []  # 768 px
    assert levels(compiled(bars_on_one_output(13))) == [("warning", "output_over_warn")]  # 832 > 800
    assert levels(compiled(bars_on_one_output(33))) == [("violation", "output_over_cap")]  # 2112 > 2048
    octa = levels(compiled(bars_on_one_output(32, "quinled-dig-octa-32-8l", "o1")))  # 2048 px
    assert octa == [("warning", "output_over_warn"), ("warning", "controller_over_advised")]


# ---- determinism and JSON ----------------------------------------------


def test_compiling_twice_is_identical(golden):
    again = compiled(GOLDEN)
    for name in ("mapping", "positions_m", "normals", "fixture_of", "pixel_in_fixture"):
        a, b = getattr(golden, name), getattr(again, name)
        assert a.dtype == b.dtype and a.tobytes() == b.tobytes()
    assert json.dumps(golden.to_json()) == json.dumps(again.to_json())
    assert golden.catalog_digest == load_catalog().digest


def test_to_json_is_plain_json(golden):
    out = json.loads(json.dumps(golden.to_json()))
    assert out["n"] == 3072
    assert len(out["fixtures"][0]["matrix"]) == 16
    assert out["fixtures"][0]["pixel_count"] == 64
    assert {i["code"] for i in out["issues"]} == {"rests_on_assumed", "psu_full_white_overload"}
    assert out["report"]["totals"]["pixels"] == 3072


# ---- the parametric strip, hosts, plan, notes and tags -------------------------


def strip(fid, **dims):
    return {"id": fid, "type": "strip", "dims": dims}


def test_strip_pixels_sit_centred_at_their_pitch():
    rig = compiled(arrangement(fixtures=[strip("s", pixels=4, length=1.0, pitch=0.1)]))
    np.testing.assert_allclose(rig.positions_m[:, 1], [-0.15, -0.05, 0.05, 0.15], atol=1e-15)
    assert not rig.positions_m[:, [0, 2]].any()


def test_strip_pitch_defaults_to_length_over_pixels():
    # The room map's rule: a 64-pixel, 1 m strip has a 1/64 m pitch.
    rig = compiled(arrangement(fixtures=[strip("s", pixels=64, length=1.0)]))
    y = rig.positions_m[:, 1]
    assert y[0] == pytest.approx(-0.5 + 1 / 128) and y[-1] == pytest.approx(0.5 - 1 / 128)
    np.testing.assert_allclose(np.diff(y), 1 / 64)


def test_variant_ids_are_deterministic_and_shared_by_equal_dims():
    doc = arrangement(
        fixtures=[strip("a", pixels=30, length=0.5), strip("b", length=0.5, pixels=30), strip("c", pixels=10)]
    )
    rig, again = compiled(doc), compiled(doc)
    ids = [f.type_id for f in rig.fixtures]
    assert ids[0] == ids[1] != ids[2]
    assert all(re.fullmatch(r"strip\.[0-9a-f]{8}", i) for i in ids)
    assert ids == [f.type_id for f in again.fixtures]
    assert [v.id for v in rig.variants] == [ids[0], ids[2]]
    assert rig.variants[0].type == "strip" and rig.variants[0].dims["pixels"] == 30
    assert rig.variants[0].dims["pitch"] == pytest.approx(0.5 / 30)
    assert rig.catalog_digest == load_catalog().digest
    assert not load_catalog().has(ids[0], "fixture_type")


def test_dims_on_a_group_reach_every_member():
    group = {"id": "row", "preset": "array", "type": "strip", "counts": [3], "steps_m": [[1, 0, 0]]}
    rig = compiled(arrangement(groups=[{**group, "dims": {"pixels": 8}, "tags": ["canopy"]}]))
    assert rig.n == 24
    assert {f.type_id for f in rig.fixtures} == {rig.variants[0].id}
    assert all(f.tags == ["canopy"] and f.dims == {"pixels": 8.0} for f in rig.fixtures)


@pytest.mark.parametrize(
    ("dims", "code"),
    [
        ({"pixels": 2.5}, "bad_value"),
        ({"pixels": 0}, "bad_expression"),  # the default pitch, length / pixels, divides by 0
        ({"pixels": 0, "pitch": 0.1}, "bad_value"),
        ({"pixels": 1e6}, "bad_value"),
        ({"pixels": 10, "length": 1.0, "pitch": 0.2}, "pixels_past_ends"),
        ({"colour": 1.0}, "unknown_dim"),
    ],
)
def test_bad_dims_are_errors_that_name_the_placement(dims, code):
    with pytest.raises(RigError) as exc:
        compiled(arrangement(fixtures=[strip("s", **dims)]))
    assert {(i.code, i.ref) for i in exc.value.issues if i.level == "error"} == {(code, "fixtures[0].dims")}


def test_a_host_address_used_twice_is_an_error():
    ctrl = lambda cid, host: {"id": cid, "profile": S3, "host": host}
    doc = arrangement(controllers=[ctrl("a", "10.0.0.11"), ctrl("b", "10.0.0.11:4048"), ctrl("c", "10.0.0.11:4049")])
    with pytest.raises(RigError) as exc:
        compiled(doc)
    assert [(i.code, i.ref) for i in exc.value.issues] == [("address_used_twice", "b")]
    assert "10.0.0.11:4048" in exc.value.issues[0].message


@pytest.mark.parametrize("host", ["", "10.0.0.11:0", "a b", "10.0.0.11:1:2", "http://x"])
def test_a_bad_host_is_refused_on_load(host):
    with pytest.raises(RigError) as exc:
        load_arrangement(arrangement(controllers=[{"id": "a", "profile": S3, "host": host}]))
    assert {i.code for i in exc.value.issues} == {"bad_host"}


def test_tags_dims_plan_and_notes_round_trip():
    plan = {"image": "floor/plan.png", "points": [[100, 400], [500, 400]], "meters": 2.0, "at": [0.5, 1.0]}
    doc = arrangement(
        notes="hung from the truss",
        plan=plan,
        controllers=[{"id": "a", "profile": S3, "host": "pewpew-1.local"}],
        fixtures=[{**strip("s", pixels=12), "tags": ["left", "low"]}],
    )
    arr = load_arrangement(doc)
    dumped = arr.model_dump(mode="json")
    assert dumped["notes"] == "hung from the truss" and dumped["plan"] == plan
    assert dumped["fixtures"][0]["tags"] == ["left", "low"] and dumped["fixtures"][0]["dims"] == {"pixels": 12.0}
    assert load_arrangement(json.dumps(dumped)) == arr
    assert arr.plan is not None and arr.plan.meters_per_pixel == pytest.approx(2.0 / 400)


@pytest.mark.parametrize(
    ("plan", "message"),
    [
        ({"image": "plan.svg", "points": [[0, 0], [1, 0]], "meters": 1}, "'image' must be a"),
        ({"image": "p.png"}, "'points'"),
    ],
)
def test_a_bad_plan_is_refused_with_the_room_maps_messages(plan, message):
    with pytest.raises(RigError) as exc:
        load_arrangement(arrangement(plan=plan))
    assert [i.code for i in exc.value.issues] == ["bad_plan"] and message in exc.value.issues[0].message


def test_to_json_carries_controllers_scale_shift_plan_and_variants():
    plan = {"image": "plan.png", "points": [[0, 0], [100, 0]], "meters": 2.0, "at": [0.0, 0.0]}
    doc = arrangement(
        plan=plan,
        controllers=[{"id": "a", "profile": S3, "host": "10.0.0.11"}, {"id": "b", "profile": S3}],
        fixtures=[
            strip("s", pixels=4, length=2.0),
            {**strip("t", pixels=4, length=2.0), "pose": {"position_m": [0, 1, 0]}},
        ],
        wiring={"chains": [{"id": "A", "controller": "a", "output": "rmt0", "fixtures": ["s", "t"]}]},
    )
    rig = compiled(doc)
    out = json.loads(json.dumps(rig.to_json()))
    assert out["controllers"] == [
        {"id": "a", "profile": S3, "host": "10.0.0.11", "port": 4048},
        {"id": "b", "profile": S3, "host": None, "port": None},
    ]
    assert out["plan"] == plan
    assert out["variants"] == [{"id": rig.fixtures[0].type_id, "type": "strip", "dims": out["variants"][0]["dims"]}]
    # mapping = plan-frame meters * scale + shift, the frame the plan is in.
    plan_m = rig.positions_m @ MVR_C.T
    np.testing.assert_allclose(plan_m * out["scale"] + np.array(out["shift"]), rig.mapping, atol=1e-6)
    assert out["scale"] == pytest.approx(1 / 2.5)  # both strips run up y: centres from -0.75 to 1.75 m
