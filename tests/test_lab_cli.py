"""The lab's command line: `python -m pewpew fx ...` and `verify looks`.
With `--json` stdout holds exactly one JSON document, the result's
`to_json()`; the exit codes are 0 ok, 1 problems or a failed gate, 2 usage
and 3 an expired handle."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from fakes import filed, instant_looks
from pewpew import lab
from pewpew.__main__ import main
from pewpew.fx import surprise


def stripes(args: dict) -> dict:
    """A look of stripes through a palette, its stripes node `waves` at `args`."""
    return {"layers": [{"id": "base", "nodes": {"waves": {"op": "osc", "args": args},
                                                "tint": {"op": "palette", "in": ["waves"]}}}], "seed": 3}


LOOK = stripes({"freq": 4.0})
FASTER = stripes({"freq": 8.0})
BAD = stripes({"frek": 4.0})
TIMING = ["--map", "line:64", "--seconds", "2", "--fps", "30"]
RENDER = {"map_spec": "line:64", "seconds": 2.0, "fps": 30.0}


@pytest.fixture
def files(tmp_path: Path) -> dict[str, Path]:
    out = {}
    for name, doc in (("look", LOOK), ("faster", FASTER), ("bad", BAD)):
        out[name] = tmp_path / f"{name}.look.json"
        out[name].write_text(filed(doc))
    return out


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def test_check_json_is_the_check(files, capsys):
    code, out, _ = run(["fx", "check", str(files["look"]), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.check_look(files["look"]).to_json()


def test_render_json_is_the_render_and_out_writes_a_sheet(files, tmp_path, capsys):
    png = tmp_path / "s.png"
    code, out, _ = run(["fx", "render", str(files["look"]), *TIMING, "--out", str(png), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.render(files["look"], **RENDER).to_json()
    assert png.read_bytes().startswith(b"\x89PNG")


def test_sheet_metrics_and_compare_take_a_handle_or_a_file(files, tmp_path, capsys):
    rendered = lab.render(files["look"], **RENDER)
    code, out, _ = run(["fx", "sheet", rendered.handle, "--out", str(tmp_path / "s.png"), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.sheet(rendered, out=tmp_path / "s.png").to_json()
    code, out, _ = run(["fx", "metrics", str(files["look"]), *TIMING, "--liveness", "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.metrics(rendered, liveness=True).to_json()
    code, out, _ = run(["fx", "compare", rendered.handle, str(files["faster"]), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.compare(rendered, files["faster"]).to_json()
    assert json.loads(out)["look_diff"] == [{"path": "layers.base.waves.freq", "a": 4.0, "b": 8.0}]


def test_explain_json_is_the_explanation(files, capsys):
    code, out, _ = run(["fx", "explain", str(files["look"]), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.explain(files["look"]).to_json()


def test_verify_json_is_the_verification(files, capsys):
    code, out, _ = run(["verify", "looks", str(files["look"]), *TIMING, "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.verify_looks([files["look"]], **RENDER).to_json()


def test_a_look_with_problems_exits_1_with_its_problems(files, capsys):
    code, out, err = run(["fx", "check", str(files["bad"])], capsys)
    assert code == 1 and "(did you mean 'freq'?)" in out and "[unknown-key]" in out and err == ""
    code, out, err = run(["fx", "render", str(files["bad"]), *TIMING, "--json"], capsys)
    assert code == 1 and json.loads(out) == lab.check_look(files["bad"]).to_json()
    code, out, err = run(["fx", "render", str(files["bad"]), *TIMING], capsys)
    assert code == 1 and out == "" and "fx render: look 'look': layers.base.waves: unknown param 'frek'" in err
    assert "\n  fix: rename 'frek' to 'freq'" in err
    code, _, _ = run(["verify", "looks", str(files["bad"]), *TIMING], capsys)
    assert code == 1


def test_an_expired_handle_exits_3_and_says_how_to_recover(capsys):
    gone = "r1-" + "0" * 20
    code, out, err = run(["fx", "metrics", gone, "--json"], capsys)
    assert code == 3 and json.loads(out) == {"handle": gone, "expired": True, "reason": str(lab.Expired(gone))}
    assert "render again" in err


@pytest.mark.parametrize("argv", [
    ["fx", "render", "x.look.json", "--map", "ring:9"],
    ["fx", "render", "x.look.json", "--seconds", "0"],
    ["fx", "render", "x.look.json", "--fps", "1000"],
    ["fx", "sheet", "x.look.json", "--layout", "spiral"],
    ["fx", "vary", "--n", "9"],
    ["fx", "vary", "--strength", "2"],
    ["fx", "vary", "--strength", "0"],
    ["fx", "dance", "x.look.json"],
    ["verify", "looks"],
])
def test_a_bad_argument_is_a_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2 and "error:" in capsys.readouterr().err


def test_usage_found_after_parsing_exits_2(files, capsys):
    code, out, err = run(["fx", "compare", "-", "-"], capsys)
    assert code == 2 and out == "" and "only one of A and B" in err
    code, _, err = run(["fx", "explain", "r1-" + "0" * 20], capsys)
    assert code == 2 and "render handle" in err and "`fx vary --json` gives each candidate's look" in err
    code, _, err = run(["fx", "sheet", str(files["look"]), *TIMING, "--width", "10"], capsys)
    assert code == 2 and "width must be" in err
    code, _, err = run(["fx", "vary", "--keep", "layers.base"], capsys)
    assert code == 2 and "--keep holds addresses of a look; give the FILE to vary" in err


def test_fx_help_names_every_verb_and_exit_code(capsys):
    with pytest.raises(SystemExit):
        main(["fx", "--help"])
    out = capsys.readouterr().out
    for verb in ("catalog", "show", "check", "render", "sheet", "metrics", "compare", "explain", "vary"):
        assert f"    fx {verb} " in out
    assert "3 a render handle the cache no longer holds" in " ".join(out.split()) and "add_parser" not in out


def test_a_look_can_come_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(LOOK)))
    code, out, _ = run(["fx", "check", "-", "--json"], capsys)
    assert code == 0 and json.loads(out)["ok"] is True


def test_human_output_is_short(files, capsys):
    code, out, _ = run(["fx", "render", str(files["look"]), *TIMING], capsys)
    assert code == 0 and out.startswith("r1-") and len(out.splitlines()) == 2
    code, out, _ = run(["verify", "looks", str(files["look"]), *TIMING], capsys)
    assert code == 0 and out.splitlines() == [f"PASS {files['look']} look", "1 of 1 looks pass"]


def test_vary_json_is_the_variations_and_out_writes_the_numbered_sheet(files, tmp_path, monkeypatch, capsys):
    instant_looks(monkeypatch)
    png = tmp_path / "v.png"
    code, out, _ = run(["fx", "vary", "--seed", "4", "--n", "2", *TIMING, "--out", str(png), "--json"], capsys)
    assert code == 0 and json.loads(out) == lab.vary(None, 4, 2, **RENDER).to_json()
    assert png.read_bytes().startswith(b"\x89PNG")
    code, out, _ = run(["fx", "vary", str(files["look"]), "--keep", "layers.base.waves", "--n", "1", *TIMING, "--json"],
                       capsys)
    made = json.loads(out)
    assert code == 0 and made == lab.vary(files["look"], 0, 1, keep=["layers.base.waves"], **RENDER).to_json()
    assert (made["strength"], made["keep"]) == (0.3, ["layers.base.waves"])


def test_vary_that_makes_nothing_exits_1_saying_why(monkeypatch, capsys):
    def nothing(seed, mapping, **kw):
        raise surprise.NoLook("nothing made from seed 0 passed the content gate in 16 tries; try another seed")

    monkeypatch.setattr(surprise, "generate", nothing)
    code, out, err = run(["fx", "vary", *TIMING, "--json"], capsys)
    assert code == 1 and out == "" and "try another seed" in err


