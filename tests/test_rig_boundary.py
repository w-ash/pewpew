"""Hostile and extreme inputs at the rig boundary.

Every error-level problem leaves `load_arrangement`, `load_catalog` and
`compile_rig` as a RigError with issues, never as a raw exception. The cases
are the findings in docs/studio/reports/reviews/ws1-code-review.md.
"""

from __future__ import annotations

import json
import math
import shutil
import threading

import numpy as np
import pytest

import pewpew.rig.migrate as migrate_module
from pewpew.rig import EXAMPLES, RigError, compile_rig, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import CATALOG_ENTRIES_DIR
from pewpew.rig.expr import MAX_DEPTH, ExprError, parse, resolve
from pewpew.rig.migrate import migrate
from pewpew.rig.models import MAX_FIXTURES, MAX_ISSUES, Issue, Pose, RingGroup, canonical_quat
from pewpew.rig.pose import aim, from_three

BAR = "clen-rgbw-bar-1m"
S3 = "esp32s3-devkitc1-ahct125"
GOLDEN = EXAMPLES / "golden-rings.json"


def arrangement(**parts) -> dict:
    return {"format": "pewpew.arrangement", "version": 1, **parts}


def codes(obj) -> set[str]:
    with pytest.raises(RigError) as exc:
        load_arrangement(obj)
    return {i.code for i in exc.value.issues}


def compile_codes(arr) -> set[str]:
    with pytest.raises(RigError) as exc:
        compile_rig(arr, load_catalog())
    return {i.code for i in exc.value.issues if i.level == "error"}


def nested(depth: int) -> list:
    out: list = []
    for _ in range(depth):
        out = [out]
    return out


def save(arr) -> str:
    """The canonical JSON a share id hashes."""
    return json.dumps(arr.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


# ---- 1. a str is JSON text; only an os.PathLike is a file ----------------------


def test_a_string_is_always_json_text_never_a_path():
    assert codes(str(GOLDEN)) == {"bad_json"}
    assert codes("/etc/hosts") == {"bad_json"}
    assert codes("[1]") == {"bad_format"}
    assert codes("null") == {"bad_format"}
    assert load_arrangement(GOLDEN.read_text()) == load_arrangement(GOLDEN)


def test_an_unreadable_file_is_a_rig_error(tmp_path):
    (tmp_path / "dir.json").mkdir()
    (tmp_path / "latin1.json").write_bytes(b'{"name": "\xe9"}')
    assert codes(tmp_path / "dir.json") == {"unreadable_file"}
    assert codes(tmp_path / "missing.json") == {"unreadable_file"}
    assert codes(tmp_path / "latin1.json") == {"bad_json"}
    with pytest.raises(RigError) as exc:
        load_arrangement(tmp_path / "missing.json")
    assert str(tmp_path) not in str(exc.value)


# ---- 2. deep nesting -----------------------------------------------------------


def test_deep_nesting_is_a_rig_error():
    head = json.dumps(arrangement())[:-1]
    for depth in (500, 100_000):
        assert codes(head + ', "name": ' + "[" * depth + "]" * depth + "}") == {"too_deep"}
    assert codes(arrangement(name=nested(5000))) == {"too_deep"}


def test_a_migration_step_on_deep_input_is_a_rig_error(monkeypatch):
    monkeypatch.setattr(migrate_module, "STEPS", {1: lambda d: {**d, "version": 2}})
    with pytest.raises(RigError) as exc:
        migrate(arrangement(name=nested(5000)), latest=2)
    assert [i.code for i in exc.value.issues] == ["too_deep"]


# ---- 3. magnitudes -------------------------------------------------------------


def test_out_of_range_lengths_are_refused_on_load():
    far = lambda x: {"id": "a", "type": BAR, "pose": {"position_m": [x, 0, 0]}}
    ring = lambda r: {"id": "r", "preset": "ring", "type": BAR, "count": 3, "start_radius_m": r}
    line = lambda step: {"id": "g", "preset": "array", "type": BAR, "counts": [3], "steps_m": [[step, 0, 0]]}
    assert codes(arrangement(fixtures=[far(1.7e308)])) == {"less_than_equal"}
    assert codes(arrangement(fixtures=[far(-1e5)])) == {"greater_than_equal"}
    assert codes(arrangement(groups=[ring(1e308)])) == {"less_than_equal"}
    assert codes(arrangement(groups=[ring(-1)])) == {"greater_than_equal"}
    assert codes(arrangement(groups=[line(1e308)])) == {"less_than_equal"}
    assert codes(arrangement(controllers=[{"id": "c", "profile": S3, "position_m": [0, 2e4, 0]}])) == {
        "less_than_equal"
    }


def test_an_arrangement_hundreds_of_meters_across_compiles():
    rig = compile_rig(
        load_arrangement(
            arrangement(
                groups=[
                    {"id": "r", "preset": "ring", "type": BAR, "count": 24, "start_radius_m": 150},
                    {
                        "id": "g",
                        "preset": "array",
                        "type": BAR,
                        "counts": [100],
                        "steps_m": [[4, 0, 0]],
                        "pose": {"position_m": [-200, 0, 300]},
                    },
                ],
                fixtures=[{"id": "far", "type": BAR, "pose": {"position_m": [400, 0, 0]}}],
            )
        ),
        load_catalog(),
    )
    assert np.isfinite(rig.mapping).all()
    assert np.ptp(rig.positions_m[:, 0]) > 500


def test_compile_refuses_positions_it_cannot_normalize():
    base = load_arrangement(arrangement(fixtures=[{"id": "a", "type": BAR}, {"id": "b", "type": BAR}]))

    def placed(*xs):
        poses = [Pose.model_construct(position_m=(x, 0.0, 0.0), quat_xyzw=None, aim=None) for x in xs]
        fixtures = [f.model_copy(update={"pose": p}) for f, p in zip(base.fixtures, poses)]
        return base.model_copy(update={"fixtures": fixtures})

    assert compile_codes(placed(math.inf, 0.0)) == {"not_finite"}
    assert compile_codes(placed(1.7e308, -1.7e308)) == {"not_finite"}


# ---- 4. quaternions are idempotent ---------------------------------------------


def test_canonical_quat_is_idempotent():
    rng = np.random.default_rng(0)
    for q in rng.normal(size=(5000, 4)):
        for scale in (1.0, 1 + 5e-7):
            once = canonical_quat(q / np.linalg.norm(q) * scale)
            assert canonical_quat(once) == once


def test_save_load_save_is_idempotent():
    rng = np.random.default_rng(1)
    quats = [list(q / np.linalg.norm(q)) for q in rng.normal(size=(MAX_FIXTURES, 4))]
    spun = arrangement(fixtures=[{"id": f"f{i}", "type": BAR, "pose": {"quat_xyzw": q}} for i, q in enumerate(quats)])
    for source in (GOLDEN, spun):
        first = save(load_arrangement(source))
        assert save(load_arrangement(first)) == first


# ---- 5. aim axes of any finite length ------------------------------------------


@pytest.mark.parametrize(
    ("axis", "direction"), [([1e-200, 0, 0], [1, 0, 0]), ([1e200, 1e200, 0], [1, 1, 0]), ([5e-324, 0, 0], [1, 0, 0])]
)
def test_aim_takes_the_direction_of_any_finite_axis(axis, direction):
    r = aim(axis)
    np.testing.assert_allclose(r, aim(direction), atol=1e-15, rtol=0)
    assert np.linalg.det(r) == pytest.approx(1.0, abs=1e-12)
    rig = compile_rig(
        load_arrangement(arrangement(fixtures=[{"id": "a", "type": BAR, "pose": {"aim": {"axis": axis}}}])),
        load_catalog(),
    )
    assert len(np.unique(rig.positions_m, axis=0)) == 64


# ---- 6. list caps and issue truncation -----------------------------------------


def test_every_arrangement_list_is_capped():
    ids = [f"x{i}" for i in range(10**6)]
    assert codes(arrangement(wiring={"chains": [{"id": "A", "controller": "c", "output": "o", "fixtures": ids}]})) == {
        "too_long"
    }
    over = MAX_FIXTURES + 1
    assert codes(arrangement(controllers=[{"id": f"c{i}", "profile": S3} for i in range(over)])) == {"too_long"}
    assert codes(arrangement(psus=[{"id": f"p{i}", "type": "x"} for i in range(over)])) == {"too_long"}
    assert codes(arrangement(fixtures=[{"id": f"f{i}", "type": BAR} for i in range(over)])) == {"too_long"}
    chain = lambda i: {"id": f"A{i}", "controller": "c", "output": "o", "fixtures": ["f"]}
    assert codes(arrangement(wiring={"chains": [chain(i) for i in range(over)]})) == {"too_long"}
    tags = [f"t{i}" for i in range(over)]
    assert codes(arrangement(fixtures=[{"id": "f", "type": BAR, "tags": tags}])) == {"too_long"}
    dims = {f"d{i}": 1.0 for i in range(over)}
    assert codes(arrangement(fixtures=[{"id": "f", "type": BAR, "dims": dims}])) == {"too_long"}


def test_a_rig_error_keeps_the_first_issues_errors_first():
    bad = load_arrangement(arrangement(fixtures=[{"id": f"f{i}", "type": "no-such-bar"} for i in range(150)]))
    with pytest.raises(RigError) as exc:
        compile_rig(bad, load_catalog())
    issues = exc.value.issues
    assert len(issues) == MAX_ISSUES + 1
    assert issues[-1].code == "too_many_issues" and issues[-1].message.startswith("50 more")
    warnings = [Issue.of("warning", "w", "w")] * MAX_ISSUES
    kept = RigError([*warnings, Issue.error("e", "e")]).issues
    assert kept[0].code == "e" and kept[-1].code == "too_many_issues"


# ---- 7. expressions ------------------------------------------------------------


@pytest.mark.parametrize(
    "src", ["1" + "0" * 400, "-" * 5000 + "1", "(" * 300 + "1" + ")" * 300, "1e400", "+".join("a" * 100)]
)
def test_expressions_out_of_range_are_expr_errors(src):
    with pytest.raises(ExprError):
        parse(src)


def test_long_dims_chains_are_expr_errors():
    chain = lambda n: {**{f"d{i}": f"d{i + 1} + 1" for i in range(n)}, f"d{n}": 1.0}
    assert resolve(chain(10))["d0"] == 11.0
    for n in (MAX_DEPTH + 1, 5000):
        with pytest.raises(ExprError, match="chain"):
            resolve(chain(n))


def test_a_bad_expression_in_the_catalog_is_a_rig_error(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    path = root / "fixture_type" / f"{BAR}.json"
    obj = json.loads(path.read_text())
    for bad in ("1" + "0" * 400, "-" * 5000 + "1"):
        obj["dims"]["zz"] = bad
        path.write_text(json.dumps(obj))
        with pytest.raises(RigError) as exc:
            read_catalog(root)
        assert {i.code for i in exc.value.issues} == {"bad_expression"}


def test_an_unreadable_catalog_is_a_rig_error(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    path = root / "fixture_type" / f"{BAR}.json"
    for content, code in ((b"[" * 100_000, "too_deep"), (b"\xff\xfe", "bad_json")):
        path.write_bytes(content)
        with pytest.raises(RigError) as exc:
            read_catalog(root)
        assert {i.code for i in exc.value.issues} == {code}
    with pytest.raises(RigError) as exc:
        load_catalog(tmp_path / "missing")
    assert [i.code for i in exc.value.issues] == ["unreadable_file"]


def test_the_stack_plays_no_part_in_the_depth_limit(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    (root / "fixture_type" / f"{BAR}.json").write_bytes(b"[" * 100_000)
    raised: list[BaseException] = []

    def read() -> None:
        try:
            read_catalog(root)
        except BaseException as exc:  # noqa: BLE001  the thread hands any exception to the test
            raised.append(exc)

    old = threading.stack_size(256 * 1024)
    try:
        thread = threading.Thread(target=read)
        thread.start()
    finally:
        threading.stack_size(old)
    thread.join()
    assert len(raised) == 1 and isinstance(raised[0], RigError)
    assert {i.code for i in raised[0].issues} == {"too_deep"}


# ---- 8. catalog zero values ----------------------------------------------------


@pytest.mark.parametrize(
    "edit",
    [
        lambda o: o["anchors"]["end_b"].update(dir=[0, 0, 0]),
        lambda o: o["anchors"]["tslot"].update(dir=[0, 0, 0]),
        lambda o: o["pixels"]["facing"].update(v=[0, 0, 0]),
        lambda o: o["power"]["v_nominal"].update(v=0),
        lambda o: o["pixels"]["span_m"].update(v=0),
        lambda o: o["pixels"]["span_m"].update(v="-length"),
    ],
)
def test_catalog_refuses_zero_directions_and_values(tmp_path, edit):
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    path = root / "fixture_type" / f"{BAR}.json"
    obj = json.loads(path.read_text())
    edit(obj)
    path.write_text(json.dumps(obj))
    with pytest.raises(RigError) as exc:
        read_catalog(root)
    assert {i.code for i in exc.value.issues} == {"bad_value"}


# ---- 9. strict types -----------------------------------------------------------


@pytest.mark.parametrize("count", [True, "3", 3.0])
def test_counts_must_be_integers(count):
    ring = {"id": "r", "preset": "ring", "type": BAR, "count": count, "start_radius_m": 1}
    assert codes(arrangement(groups=[ring])) == {"int_type"}


def test_positions_must_be_numbers():
    assert codes(arrangement(fixtures=[{"id": "a", "type": BAR, "pose": {"position_m": ["1", 0, 0]}}])) == {
        "float_type"
    }
    assert codes(arrangement(fixtures=[{"id": "a", "type": BAR, "pose": {"position_m": [True, 0, 0]}}])) == {
        "float_type"
    }
    # A JSON integer is a number, and a tuple from a Python caller is an array.
    pose = (
        load_arrangement(arrangement(fixtures=[{"id": "a", "type": BAR, "pose": {"position_m": (1, 0, 0)}}]))
        .fixtures[0]
        .pose
    )
    assert pose.position_m == (1.0, 0.0, 0.0)


# ---- 11. the ring docstring matches the geometry -------------------------------


def test_ring_docstring_matches_the_geometry():
    assert "midpoint at radius `start_radius_m + L/2`" in (RingGroup.__doc__ or "")
    r0, tilt = 0.618034, math.radians(30)
    rig = compile_rig(load_arrangement(GOLDEN), load_catalog())
    f = next(f for f in rig.fixtures if f.group == "inner")
    m = from_three(f.matrix)
    mid, inner_end = m[:3, 3], (m @ [0, -0.5, 0, 1])[:3]
    assert math.hypot(mid[0], mid[2]) == pytest.approx(r0 + 0.5, abs=1e-12)
    assert math.hypot(inner_end[0], inner_end[2]) == pytest.approx(r0 + 0.5 * (1 - math.cos(tilt)), abs=1e-12)


# ---- 12. a fixture listed twice in one chain -----------------------------------


def test_a_fixture_listed_twice_in_one_chain_has_its_own_code():
    obj = arrangement(
        fixtures=[{"id": "b0", "type": BAR}, {"id": "b1", "type": BAR}],
        controllers=[{"id": "c1", "profile": S3}],
        wiring={"chains": [{"id": "A", "controller": "c1", "output": "rmt0", "fixtures": ["b0", "b1", "b0"]}]},
    )
    with pytest.raises(RigError) as exc:
        compile_rig(load_arrangement(obj), load_catalog())
    [issue] = [i for i in exc.value.issues if i.level == "error"]
    assert issue.code == "duplicate_in_chain"
    assert issue.message == "b0 is listed twice in chain A"
