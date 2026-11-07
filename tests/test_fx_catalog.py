"""The catalog: one record per op (and pattern, blend, palette, kind), held
by a golden, and the files made from it (the reference page, the
builder's stub), each checked for drift; and the `fx` verbs that print
it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fakes import run_main
from pewpew.fx.catalog import catalog, encode_example, example, items, markdown, stub
from pewpew.fx.ops import OPS

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "tests" / "goldens" / "catalog.json"
MADE = {ROOT / "docs" / "reference" / "catalog.md": markdown, ROOT / "src" / "pewpew" / "fx" / "expr.pyi": stub}


def test_the_golden_is_the_live_catalog(regen_goldens: bool) -> None:
    live = catalog()
    if regen_goldens:
        GOLDEN.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n")
    assert json.loads(GOLDEN.read_text()) == live, "run `uv run pytest --regen-goldens` and review the diff"


@pytest.mark.parametrize("path", MADE, ids=lambda p: p.name)
def test_each_file_made_from_the_catalog_matches_it(path: Path, regen_goldens: bool) -> None:
    made = MADE[path](catalog())
    if regen_goldens:
        path.write_text(made)
    assert path.read_text() == made, f"{path.name} drifted from the catalog; run `uv run pytest --regen-goldens`"


def test_every_op_has_one_record_whose_examples_are_its_json() -> None:
    book = catalog()
    assert sorted(r["op"] for r in book["ops"]) == sorted(OPS)
    for record in book["ops"]:
        for item in record["examples"]:
            assert item["json"] == encode_example(example(item["py"]))
            assert ("layers" in item["json"]) == (record["sig"] == "signal"), "a signal's example is a look"
    assert {r["name"] for r in book["blends"]} >= {"normal", "screen", "stencil"}
    assert [r["kind"] for r in book["kinds"]] == ["float", "int", "bool", "choice", "color", "palette"]


def test_a_search_narrows_by_kind_and_words() -> None:
    book = catalog()
    assert [r["op"] for r in items(book, "coord", "fold")] == ["kaleid", "mirror"]
    assert [r["op"] for r in items(book, "coord", "mirrored FOLD")] == ["kaleid"]  # every word, in any order
    assert [r["op"] for r in items(book, "signal")] == ["band", "beat", "env", "knob", "lfo", "smooth", "walk"]
    assert [r["name"] for r in items(book, "palette", "ember")] == ["ember"]


def test_the_fx_verbs_print_the_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_main(["fx", "catalog", "--kind", "coord", "--json"])[0] == 0
    found = json.loads(capsys.readouterr().out)["items"]
    assert [r["sig"] for r in found] == ["coord"] * len(found) and len(found) == 8
    assert run_main(["fx", "catalog", "--query", "kaleidoscope"])[0] == 0
    assert capsys.readouterr().out.startswith("kaleid ")
    assert run_main(["fx", "show", "kaleid", "--json"])[0] == 0
    assert json.loads(capsys.readouterr().out)["fix"] == "a strip has no plane to fold; use mirror along the strip"
    assert run_main(["fx", "show", "kaleid"])[0] == 0
    assert "example: osc(8).kaleid(5)" in capsys.readouterr().out
    assert run_main(["fx", "show", "kaleidd"])[0] == 1
    assert "unknown op 'kaleidd' (did you mean 'kaleid'?)" in capsys.readouterr().err
    assert run_main(["fx", "show", "Kaleidoscope", "--json"])[0] == 0  # its label, as the page shows it
    assert json.loads(capsys.readouterr().out)["op"] == "kaleid"
    assert run_main(["fx", "show", "multiplier"])[0] == 1
    assert "unknown op 'multiplier' (did you mean 'mult'?)" in capsys.readouterr().err
    assert run_main(["fx", "catalog", "--format", "markdown"])[0] == 0
    assert capsys.readouterr().out == markdown(catalog())
