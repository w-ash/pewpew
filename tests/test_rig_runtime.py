"""`pewpew.rig.runtime`: a compiled rig as a run uses it, and the room map file read in place."""

from __future__ import annotations

import json

import pytest

from fakes import EXAMPLE_RIG, LEGACY_ROOM, arrangement, bar, looks_file, run_main
from pewpew.jsonfile import ProblemsError, replace_string
from pewpew.rig import RigError, load_catalog
from pewpew.rig.runtime import (
    RoomFormatWarning,
    compile_doc,
    ddp_targets,
    load_rig,
    parse_rig,
    plan_view,
    read_doc,
    rig_view,
    stream_refusals,
)

CATALOG = load_catalog()


def test_the_plan_view_draws_the_canopy_as_the_room_compiler_did(example):
    # The room compiler's `describe()` of examples/room-60-bars.json, before its deletion.
    view = plan_view(example)
    assert view["scale"] == 0.17287952458130737
    assert view["fixtures"][0] == {
        "id": "row01.1", "pitch": 0.015625, "start": [-0.001351, 0.119665], "end": [0.171529, 0.119665],
        "input": "start",
    }
    assert view["fixture_of"] == example.fixture_of.tolist() and view["plan"] is None


def test_the_rig_view_carries_what_a_3d_view_places():
    rig = compile_doc(arrangement(bar("a", pixels=4), bar("b", pixels=4, start=[0.0, 1.0], end=[1.0, 1.0], chain=2)),
                      CATALOG)
    view = json.loads(json.dumps(rig_view(rig)))  # JSON-ready
    assert sorted(view) == sorted([
        "catalog_digest", "frame", "scale", "shift", "plan", "fixtures", "types", "controllers", "slices",
        "controller_slices", "issues",
    ])
    assert [(f["id"], f["pixel_start"], f["pixel_count"], f["base_type_id"]) for f in view["fixtures"]] == [
        ("a", 0, 4, "strip"), ("b", 4, 4, "strip"),
    ]
    assert view["types"][view["fixtures"][0]["type_id"]] == {"count": 4, "span_m": 1.0, "z_m": 0.0, "facing": None}
    assert view["controllers"] == [{"id": "A", "profile": "esp32s3-devkitc1-ahct125", "host": "10.0.0.11",
                                    "port": 4048}]


def test_a_broken_cap_and_a_wired_controller_without_a_host_refuse_the_stream():
    over = compile_doc(arrangement(bar("long", pixels=64, instances=33, step=[1.0, 0.0])), CATALOG)
    assert any("output_over_cap" == i.code for i in over.issues)
    assert any("drives at most" in reason for reason in stream_refusals(over))
    doc = arrangement(bar("a"), bar("b", board="B"), boards={"A": "10.0.0.11", "B": "10.0.0.12"})
    del doc["controllers"][1]["host"]
    unhosted = compile_doc(doc, CATALOG)
    assert stream_refusals(unhosted) == ["controller 'B' drives 64 px but has no host"]
    assert [b.host for b in ddp_targets(unhosted)] == ["10.0.0.11"]
    assert stream_refusals(load_rig(EXAMPLE_RIG)[0]) == []


def test_compile_doc_holds_the_pixel_limit():
    doc = arrangement(bar("a", pixels=8))
    assert compile_doc(doc, CATALOG, max_pixels=8).n == 8
    with pytest.raises(RigError) as exc:
        compile_doc(doc, CATALOG, max_pixels=7)
    assert [i.code for i in exc.value.issues] == ["too_many_pixels"]


def test_a_rig_file_that_does_not_read_is_one_rig_error(tmp_path):
    with pytest.raises(RigError, match="no such file"):
        load_rig(tmp_path / "missing.json")
    with pytest.raises(RigError, match="not UTF-8"):
        read_doc(b'{"name": "\xe9"}')
    with pytest.raises(RigError) as exc, pytest.warns(RoomFormatWarning):
        parse_rig('{"boards": {"A": "10.0.0.11"}, "fixtures": []}')
    assert [i.code for i in exc.value.issues] == ["bad_room"]


def test_a_room_map_file_is_read_in_place_with_a_warning_that_names_the_migration():
    with pytest.warns(RoomFormatWarning, match="rig migrate-room"):
        legacy, _ = load_rig(LEGACY_ROOM)
    rig, _ = load_rig(EXAMPLE_RIG)
    assert legacy.mapping.tobytes() == rig.mapping.tobytes()
    assert ddp_targets(legacy) == ddp_targets(rig)


def test_a_run_on_a_room_map_file_warns_and_runs(capsys):
    rc, out = run_main(["run", looks_file(), "--room", str(LEGACY_ROOM), "--no-ddp", "--ansi", "--frames", "1"])
    err = capsys.readouterr().err
    assert rc == 0 and "\x1b[38;2;" in out
    assert "--room is the old name of --map" in err and "rig migrate-room" in err


def test_replace_string_changes_one_value_and_keeps_every_other_byte():
    data = b'{"a": "x",\n   "b": ["x2", "y"]}\n'
    expected = {"a": "z", "b": ["x2", "y"]}
    assert replace_string(data, "x", "z", expected) == b'{"a": "z",\n   "b": ["x2", "y"]}\n'
    with pytest.raises(ProblemsError, match="exactly once"):
        replace_string(b'{"a": "x", "b": "x"}', "x", "z", {})
    with pytest.raises(ProblemsError, match="changes more"):
        replace_string(data, "x", "z", {"a": "z"})
