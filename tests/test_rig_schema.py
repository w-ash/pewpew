"""The committed JSON Schemas and arrangement migration."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import pewpew.rig.migrate as migrate_module
from pewpew.rig import EXAMPLES, Arrangement, RigError, load_arrangement
from pewpew.rig.migrate import migrate
from pewpew.rig.models import json_schemas

SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


def test_committed_schemas_match_the_models():
    for name, text in json_schemas().items():
        committed = (SCHEMAS / name).read_text(encoding="utf-8")
        assert committed == text, f"schemas/{name} is stale; run `uv run python scripts/export_schemas.py`"


def test_v1_passes_migration_unchanged():
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    before = copy.deepcopy(data)
    out = migrate(data)
    assert out == before and out is not data
    assert data == before


def test_a_newer_file_is_refused():
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    with pytest.raises(RigError) as exc:
        load_arrangement({**data, "version": 2})
    assert [i.code for i in exc.value.issues] == ["version_too_new"]
    for bad, code in (({**data, "version": "1"}, "bad_version"), ({**data, "format": "x"}, "bad_format")):
        with pytest.raises(RigError) as exc:
            load_arrangement(bad)
        assert [i.code for i in exc.value.issues] == [code]


def test_steps_run_in_order_up_to_the_latest(monkeypatch):
    def v1_to_v2(d):
        return {**d, "version": 2, "trail": d.get("trail", []) + [1]}

    def v2_to_v3(d):
        return {**d, "version": 3, "trail": d["trail"] + [2]}

    monkeypatch.setattr(migrate_module, "STEPS", {1: v1_to_v2, 2: v2_to_v3})
    out = migrate({"format": "pewpew.arrangement", "version": 1}, latest=3)
    assert out == {"format": "pewpew.arrangement", "version": 3, "trail": [1, 2]}


def test_the_example_round_trips_through_the_model():
    arr = load_arrangement(EXAMPLES / "golden-rings.json")
    again = Arrangement.model_validate(arr.model_dump(mode="json"))
    assert again == arr
    assert load_arrangement(json.dumps(arr.model_dump(mode="json"))) == arr
