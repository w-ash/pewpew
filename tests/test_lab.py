"""The agent service, pewpew.lab: checking looks with coded problems,
rendering them as the aura does under content-addressed handles, the
render cache, sheets, metrics, liveness, comparison, explanation and the
`verify looks` gate. Renders stay at line:64 for 2 s at 30 fps or less."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import pkgutil
import shutil
import threading
from collections.abc import Callable
from functools import partial
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fakes import Pooled, build, run_python
from pewpew import lab
from pewpew.aura.book import LookError, parse_looks
from pewpew.color import EMBER
from pewpew.compose import look_controls
from pewpew.fx.op import FrameCtx, Op
from pewpew.fx.ops.source import Osc
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.jsonfile import write_atomic
from pewpew.lab import (
    Code,
    Expired,
    Refused,
    check_look,
    compare,
    comparison,
    explain,
    metrics,
    render,
    search,
    sheet,
    verify_looks,
)
from pewpew.lab.check import ready
from pewpew.lab.geometry import Geometry, parse_geometry
from pewpew.lab.handles import ENGINE, Cache, fingerprint
from pewpew.lab.rendering import take
from pewpew.metrics import LIVENESS_RMS
from pewpew.params import Float, Int, Palette, ParamSet
from pewpew.problems import problem
from pewpew.render import SlotClock
from pngread import decode_png

MAP, SECONDS, FPS = "line:64", 2.0, 30.0


def layer(lid: str, mix: dict | None = None, **nodes: dict) -> dict:
    """Layer `lid` of `nodes`, its mix `mix`."""
    return {"id": lid, **(mix or {}), "nodes": nodes}


def stripes(lid: str = "base", mix: dict | None = None, **args) -> dict:
    """Layer `lid`: stripes (`waves`, osc at freq 4 and `args`) through the ember palette (`tint`)."""
    return layer(lid, mix, waves={"op": "osc", "args": {"freq": 4.0, **args}},
                 tint={"op": "palette", "in": ["waves"], "args": {"palette": "ember"}})


def glow(lid: str = "top", mix: dict | None = None, **args) -> dict:
    """Layer `lid`: noise hills (`hills`, at `args`) through the aurora palette (`tone`)."""
    return layer(lid, mix, hills={"op": "noise", "args": args},
                 tone={"op": "palette", "in": ["hills"], "args": {"palette": "aurora"}})


def one(op: str, nid: str | None = None, **args) -> dict:
    """A look of one layer, `base`, of one node of `op` (id `nid`, default `op`) at `args`."""
    return {"layers": [layer("base", **{nid or op: {"op": op, "args": args}})]}


STRIPES = {"seed": 3, "layers": [stripes()]}
FREQ = "layers.base.waves.freq"
DUO = {"seed": 3, "master": 0.8, "layers": [stripes(), glow("top", {"blend": "screen", "opacity": 0.5})]}


def program(**nodes: dict) -> dict:
    """A look of one layer, `base`, that runs a program of `nodes`."""
    return {"layers": [{"id": "base", "nodes": nodes}]}


# A program of three nodes, with a second program screened over it.
TIDE = {"seed": 3, "layers": [
    program(waves={"op": "osc", "args": {"freq": 8.0, "sync": 0.1}},
            fold={"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
            tint={"op": "palette", "in": ["fold"], "args": {"palette": "ember"}})["layers"][0],
    glow("top", {"blend": "screen", "opacity": 0.6}),
]}
OSC = {"op": "osc", "args": {"freq": 8.0}}


def normalized(result: lab.Check) -> dict:
    """The look a check that passed gives back."""
    assert result.look_normalized is not None
    return result.look_normalized


def spec_of(rendered: lab.Rendered) -> lab.RenderSpec:
    assert rendered.spec is not None  # a fresh render carries its spec
    return rendered.spec


def probes_of(measured: lab.Measured) -> tuple[lab.KnobProbe, ...]:
    assert measured.liveness is not None  # asked for
    return measured.liveness


def book(**looks: dict) -> dict:
    return {"version": 4, "looks": looks}


def draw(look: dict | Path = STRIPES, *, map_spec: str = MAP, seconds: float = SECONDS, fps: float = FPS,
         **kw) -> lab.Rendered:
    return render(look, map_spec, seconds, fps, **kw)


# ---- check ------------------------------------------------------------------------


def test_a_look_that_checks_comes_back_with_every_param_written_out():
    result = check_look(STRIPES)
    assert result.ok and result.problems == ()
    tint = normalized(result)["layers"][0]["nodes"]["tint"]
    assert normalized(result) == {
        "seed": 3, "fade": 2.0, "cycle": False, "layers": [{
            "id": "base", "opacity": 1.0, "blend": "normal", "enabled": True, "out": "tint",
            "nodes": {"waves": {"op": "osc", "args": {"freq": 4.0, "sync": 0.1, "offset": 0.0, "axis": "x"}},
                      "tint": {"op": "palette", "in": ["waves"], "args": {
                          "palette": tint["args"]["palette"], "shift": 0.0, "cycle": 0.0}}},
        }],
    }
    assert tint["args"]["palette"]["label"] == "ember"
    assert check_look(normalized(result)).look_normalized == result.look_normalized  # normalizing is idempotent


def test_a_looks_file_checks_whole_and_keeps_its_other_sections(tmp_path):
    doc = {**book(duo=DUO, one=STRIPES), "current": "duo", "cycle": {"idle": None},
           "triggers": {"cue": {"look": "one"}}, "notes": "kept"}
    path = tmp_path / "saved.look.json"
    path.write_text(json.dumps(doc))
    result = check_look(path)
    assert result.ok
    doc = normalized(result)
    assert list(doc["looks"]) == ["duo", "one"] and doc["current"] == "duo"
    assert doc["triggers"]["cue"]["look"] == "one" and doc["notes"] == "kept"
    assert parse_looks(json.dumps(doc)).looks["duo"].master == 0.8  # what the aura loads


def test_check_takes_a_look_value_json_data_and_text_alike(tmp_path):
    value = parse_looks(json.dumps(book(a=STRIPES))).looks["a"]
    results = [check_look(doc) for doc in (STRIPES, json.dumps(STRIPES), value)]
    assert all(r == results[0] for r in results) and results[0].ok


def test_a_file_is_a_looks_file_as_run_reads_it(tmp_path):
    """A `.look.json` file is a looks book, the one file form `run LOOKS`
    plays (ADR-006 amendment "layered paths"): a single look in a file
    is refused with the file that holds it."""
    path = tmp_path / "a.look.json"
    path.write_text(json.dumps(STRIPES))
    (problem,) = check_look(path).problems
    assert (problem.code, problem.path) == (Code.MISSING, "")
    assert "this is a single look, and a looks file wraps it" in problem.reason
    assert problem.example == {"version": 4, "current": "look", "looks": {"look": STRIPES}}
    path.write_text(json.dumps(problem.example))
    assert check_look(path).ok and (tmp_path / "a.look.json").read_text()
    with pytest.raises(LookError, match="this is a single look"):
        parse_looks(json.dumps(STRIPES))  # as `run LOOKS` refuses it


@pytest.mark.parametrize("doc, path, code, guess", [
    ({"layers": [{**stripes(), "opacty": 1}]}, "layers.base.opacty", Code.UNKNOWN_KEY, "opacity"),
    ({"layers": [stripes(frek=1)]}, "layers.base.waves.frek", Code.UNKNOWN_KEY, "freq"),
    ({"layers": [stripes(freq=99)]}, FREQ, Code.OUT_OF_RANGE, None),
    ({"layers": [stripes(freq="fast")]}, FREQ, Code.WRONG_KIND, None),
    ({"layers": [stripes(mix={"blend": "screem"})]}, "layers.base.blend", Code.OUT_OF_RANGE, "screen"),
    ({"layers": [{"id": "base", "nodes": {"o": {"op": "osci"}}}]}, "layers.base.o.op", Code.UNKNOWN_OP, "osc"),
    ({"layers": [{"id": "base", "nodes": {"o": {"op": "pattern"}}}]}, "layers.base.o.op", Code.UNKNOWN_OP, None),
    ({"seed": 1}, "layers", Code.MISSING, None),
    ({"layers": []}, "layers", Code.WRONG_KIND, None),
    ({"layers": [stripes(), glow("base")]}, "layers.base", Code.BAD_REF, None),
    ({"layers": [stripes()], "signals": [1]}, "signals", Code.WRONG_KIND, None),
    ({"layers": [stripes("Base")]}, "layers[0].id", Code.WRONG_KIND, None),
    ({"version": 3}, "version", Code.WRONG_VERSION, None),
    ({"looks": {}}, "version", Code.MISSING, None),
    ({**book(a=STRIPES), "current": "b"}, "current", Code.BAD_REF, None),
    ({**book(a=STRIPES), "triggers": {"t": {"priority": "buton"}}}, "triggers.t.priority", Code.OUT_OF_RANGE,
     "button"),
    ({**book(a={**STRIPES, "master": 2})}, "looks.a.master", Code.OUT_OF_RANGE, None),
    ({**book(), "cycle": {"idle": 10**400}}, "cycle.idle", Code.WRONG_KIND, None),  # past float range
    ({**book(), "cycle": {"each": 10**400}}, "cycle.each", Code.WRONG_KIND, None),
    ([1, 2], "", Code.NOT_A_LOOK, None),
    ("{nope", "", Code.NOT_A_LOOK, None),
    (program(w={"op": "osc", "args": {"freqq": 2}}), "layers.base.w.freqq", Code.UNKNOWN_KEY, "freq"),
    (program(w=OSC, f={"op": "kaleid", "in": ["w"], "args": {"sides": 40}}), "layers.base.f.sides",
     Code.OUT_OF_RANGE, None),
    (program(w={**OSC, "arg": {}}), "layers.base.w.arg", Code.UNKNOWN_KEY, "args"),
    (program(f={"op": "kaleid", "args": {}}), "layers.base.f.in", Code.WRONG_KIND, None),
    (program(f={"op": "kaleid", "in": ["w"]}), "layers.base.f.in", Code.BAD_REF, None),
    (program(a={"op": "kaleid", "in": ["b"]}, b={"op": "kaleid", "in": ["a"]}), "layers.base", Code.CYCLE, None),
    (program(w=OSC, t={"op": "hue", "in": ["w"]}), "layers.base.t.in", Code.WRONG_KIND, None),
    (program(d=OSC, w=OSC), "layers.base.d", Code.BAD_REF, None),
    ({"layers": [{**program(w=OSC)["layers"][0], "out": "x"}]}, "layers.base.out", Code.BAD_REF, None),
    (program(w=OSC, t={"op": "palette", "in": ["w"], "args": {"palette": "aurore"}}), "layers.base.t.palette",
     Code.OUT_OF_RANGE, "aurora"),
    (program(w=OSC, t={"op": "palette", "in": ["w"], "args": {"palette": {"stops": [
        {"at": 0, "h": 0, "s": 100, "v": 1}, {"at": 1, "h": 0, "s": 1, "v": 1}]}}}),
     "layers.base.t.palette.stops[0].s", Code.OUT_OF_RANGE, None),
    ({"layers": [{**program(w=OSC, t={"op": "palette", "in": ["w"]})["layers"][0], "alpha": "t"}]},
     "layers.base.alpha", Code.WRONG_KIND, None),
    ({"layers": [stripes(f"l{i}") for i in range(17)]}, "layers", Code.OUT_OF_RANGE, None),
    ({"seed": -1, "layers": [stripes()]}, "seed", Code.OUT_OF_RANGE, None),
    ({"seed": "x", "layers": [stripes()]}, "seed", Code.WRONG_KIND, None),
    ({"layers": [stripes()], "front": [FREQ, FREQ]}, "front[1]", Code.BAD_REF, None),
    ({"layers": [stripes()], "front": ["layers.base.waves.frek"]}, "front[0]", Code.BAD_REF, FREQ),
    ({"layers": [stripes()], "signals": {"b": {"op": "lfo"}},
      "routes": [{"source": "b", "path": "layers.base.waves.frek", "depth": 0.1}]}, "routes[0].path", Code.BAD_REF,
     FREQ),
    (program(o={"op": "oscillator"}), "layers.base.o.op", Code.UNKNOWN_OP, "osc"),  # its label
    (program(o={"op": "Kaleidoscope", "in": []}), "layers.base.o.op", Code.UNKNOWN_OP, "kaleid"),
    ({"layers": [stripes()], "signals": {"e": {"op": "envelope"}}}, "signals.e.op", Code.UNKNOWN_OP,
     "env"),
])
def test_each_problem_has_a_stable_code_a_path_and_a_did_you_mean(doc, path, code, guess):
    result = check_look(doc)
    assert not result.ok and result.look_normalized is None
    found = {(p.path, p.code): p for p in result.problems}
    assert (path, code) in found, [(p.path, p.code, p.reason) for p in result.problems]
    assert found[path, code].did_you_mean == guess


def test_a_program_checks_node_by_node_with_every_knob_written_out():
    result = check_look(TIDE)
    assert result.ok
    nodes = normalized(result)["layers"][0]["nodes"]
    assert nodes["fold"] == {"op": "kaleid", "in": ["waves"], "args": {"sides": 5, "plane": "auto"}}
    assert nodes["waves"]["args"] == {"freq": 8.0, "sync": 0.1, "offset": 0.0, "axis": "x"}
    assert check_look(normalized(result)).look_normalized == result.look_normalized


def test_a_program_the_map_does_not_support_is_refused_before_it_renders():
    with pytest.raises(Refused) as refused:
        draw(TIDE, map_spec="line:64")
    (found,) = refused.value.problems
    assert (found.path, found.code, found.valid) == ("layers.base.fold", Code.WRONG_DIMS, ("2", "3"))
    assert "use mirror along the strip" in found.reason


def test_a_program_renders_explains_and_probes_each_node():
    rendered = draw(TIDE, map_spec="grid:8x8", seconds=1.0)
    assert rendered.metrics.black_fraction < 1.0
    words = explain(TIDE)
    assert words.summary.startswith("2 layers, bottom first: base (normal blend at opacity 1), then top")
    assert words.layers[0].about.startswith("3 nodes: waves (osc, Oscillator): Stripes along one axis")
    assert words.layers[0].knobs[0].startswith("waves.freq = 8 ")
    assert words.layers[1].knobs[0].startswith("hills.scale = 3 ")
    probed = {p.path: p for p in probes_of(metrics(rendered, liveness=True))}
    assert "layers.base.fold.plane=xy" not in probed  # auto takes xy on a grid: the same plane
    assert {"layers.base.fold.sides", "layers.base.tint.shift", "layers.top.hills.scale"} <= probed.keys()
    assert all(p.live for p in probed.values()), [p.path for p in probed.values() if not p.live]


def test_a_problem_keeps_the_words_the_aura_uses_and_gives_an_example():
    (problem,) = check_look({"layers": [stripes(freq=99)]}).problems
    assert problem.reason == ParamSet(Osc, name="layers.base.waves").check("freq", 99)
    assert problem.valid == ("0.5..32.0",)
    assert problem.example == Osc.freq.default  # the knob's default, as a route's out-of-range depth gives
    (mixed,) = check_look(book(a={"layers": [stripes(mix={"opacity": 3})]})).problems
    assert (mixed.path, mixed.example) == ("looks.a.layers.base.opacity", 1.0)
    (missing,) = check_look({"seed": 1}).problems
    assert missing.example[0]["nodes"]["waves"]["op"] == "osc"  # a layer to start from
    assert check_look(missing.example and {"layers": missing.example}).ok


@pytest.mark.parametrize("doc", [
    {"layers": [stripes(freq="unknown op 'x'; ops: {[]: 1}, ")]},
    {**book(), "triggers": {"t": {"priority": "a, {[]: 1}; got b"}}},
    '{"version": 4, "looks": {}, "cycle": {"idle": ' + "1" * 5000 + "}}",  # past Python's digit limit
], ids=["unknown-op-echoed", "one-of-echoed", "long-integer"])
def test_check_reads_a_refusal_that_echoes_a_python_literal_or_a_huge_number(doc):
    result = check_look(doc)
    assert not result.ok and all(isinstance(p.code, Code) for p in result.problems)


# Refusal wordings that list values, and pieces of Python literals to echo in them.
HEADS = st.sampled_from(["unknown op 'x'; ops: ", "unknown key 'k'; expected ", "'priority' is one of ",
                         "speed must be one of ", "trigger 't': 'priority' is one of ",
                         "layers.base.f: unknown op 'x' (did you mean 'y'?); ops: ",
                         "look 'a': layers.base.w: unknown key 'k' (did you mean 'kk'?); expected ",
                         "layers.base: nodes ", "layers.base.f: kaleid needs a map of ",
                         "layers.base.t: hue takes rgb on 'in'; "])
ECHOED = st.lists(st.text(alphabet="'\"{}[]():, \\ab0", max_size=12), max_size=4)


@given(HEADS, ECHOED, st.sampled_from(["", "; got 'b'", ", got 'b'"]))
def test_reading_a_refusal_never_raises(head, items, tail):
    assert isinstance(problem(head + ", ".join(items) + tail).code, Code)


def test_a_book_with_several_looks_needs_a_name_to_render():
    doc = book(a=STRIPES, b=DUO)
    with pytest.raises(Refused) as refused:
        draw(doc)
    assert refused.value.problems[0].code == Code.MISSING and refused.value.problems[0].valid == ("a", "b")
    with pytest.raises(Refused) as refused:
        draw(doc, name="c")
    assert refused.value.problems[0].code == Code.BAD_REF
    assert spec_of(draw(doc, name="b")).look["master"] == 0.8
    assert draw({**doc, "current": "b"}).handle == draw(doc, name="b").handle


# Values that JSON can hold, small enough to keep each example quick.
JSONISH = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=8),
    lambda inner: st.lists(inner, max_size=3) | st.dictionaries(st.text(max_size=8), inner, max_size=3),
    max_leaves=12,
)
# Keys a look really has, so a patch reaches past the first refusal.
KEYS = st.sampled_from([
    "version", "looks", "current", "cycle", "triggers", "layers", "id", "nodes", "op", "args", "in",
    "out", "alpha", "opacity", "blend", "enabled", "seed", "master", "fade", "signals", "freq", "sync", "palette",
    "scale", "idle", "end", "look", "priority",
])
PATCH = st.dictionaries(KEYS, JSONISH, max_size=3)


@given(JSONISH)
def test_check_never_raises_on_json_data(doc):
    result = check_look(doc)
    assert json.dumps(result.to_json(), allow_nan=True)
    assert result.ok == (not result.problems)


@given(st.text(max_size=40))
def test_check_never_raises_on_text(text):
    check_look(text)


@settings(max_examples=3 * settings().max_examples)  # three times a property's (conftest.py)
@given(PATCH, PATCH, PATCH, PATCH, st.booleans())
def test_check_never_raises_on_a_look_patched_at_any_depth(top, mix, nodes, args, as_book):
    doc = copy.deepcopy(DUO)  # patched from the deepest level up, so no patch removes another's place
    doc["layers"][0]["nodes"]["waves"]["args"].update(args)
    doc["layers"][1]["nodes"]["hills"].update(nodes)
    doc["layers"][0].update(mix)
    doc.update(top)
    result = check_look(book(a=doc) if as_book else doc)
    assert all(isinstance(p.code, Code) for p in result.problems)


# A node's parts, patched: other ops, inputs and ids that do or do not exist.
NODE_PATCH = st.dictionaries(
    st.sampled_from(["op", "in", "args", "out", "alpha", "nodes", "sides", "freq", "palette", "plane"]),
    JSONISH | st.sampled_from(["osc", "kaleid", "palette", "hue", "below", "prev", "mirror", "nope"])
    | st.lists(st.sampled_from(["waves", "fold", "tint", "x"]), max_size=3),
    max_size=3,
)


@settings(max_examples=3 * settings().max_examples)  # three times a property's (conftest.py)
@given(NODE_PATCH, NODE_PATCH, NODE_PATCH, PATCH, st.booleans())
def test_check_never_raises_on_a_program_patched_at_any_depth(node, args, other, mix, as_book):
    doc = copy.deepcopy(TIDE)
    nodes = doc["layers"][0]["nodes"]
    nodes["waves"]["args"].update(args)
    nodes["fold"].update(node)
    nodes["tint"].update(other)
    doc["layers"][0].update(mix)
    result = check_look(book(a=doc) if as_book else doc)
    assert all(isinstance(p.code, Code) for p in result.problems)
    assert result.ok == (not result.problems)


# ---- render -------------------------------------------------------------------------


def test_a_render_is_what_run_looks_renders(tmp_path):
    """The lab renders through the aura's own path: `run LOOKS --seed 5`
    starting in the look shows these frames, byte for byte, master and all."""
    path = tmp_path / "duo.look.json"
    path.write_text(json.dumps({**book(duo=DUO), "current": "duo"}))
    rendered = draw(path, seed=5)
    run = build(["run", str(path), "--map", MAP, "--seed", "5"])
    clock = SlotClock(FPS)
    aura = run.aura
    shown = np.stack([aura.master.apply(t, aura.fader.advance_to(t)) for t in (clock.advance() for _ in range(60))])
    assert np.array_equal(take(rendered).frames, shown)


def test_a_render_comes_back_without_its_frames():
    rendered = draw()
    assert rendered.handle.startswith("r1-") and len(rendered.handle) == 23
    spec = spec_of(rendered)
    assert (spec.frames, spec.points, spec.dims) == (60, 64, 1)
    assert spec.engine == ENGINE and spec.look == check_look(STRIPES).look_normalized
    assert len(json.dumps(rendered.to_json())) < 4000
    assert take(rendered).frames.shape == (60, 64, 3)


def test_a_render_without_a_map_is_on_the_map_run_uses_without_one():
    rendered = render({"layers": [stripes()]}, seconds=0.2)
    spec = spec_of(rendered)
    assert (spec.map, spec.points, spec.dims) == ("grid:16x16", 256, 2)


# `draw()` in a new process: its handle and the SHA-256 of its frames.
ELSEWHERE_CODE = (
    "import hashlib, json, sys\n"
    "from pewpew.lab import render\n"
    "from pewpew.lab.rendering import take\n"
    "r = render(json.loads(sys.argv[1]), 'line:64', 2.0, 30.0)\n"
    "print(r.handle, hashlib.sha256(take(r).frames.tobytes()).hexdigest())\n"
)


# The new process, run on the suite's process pool (conftest.py), with the
# render cache of its worker, not of the test (`fakes.strict_worker`).
JOBS = {"elsewhere": partial(run_python, ELSEWHERE_CODE, json.dumps(STRIPES))}


def test_the_same_render_has_the_same_handle_and_bytes_in_another_process(pooled: Pooled):
    rendered = draw()
    frames = take(rendered).frames
    assert pooled["elsewhere"].stdout.split() == [rendered.handle, hashlib.sha256(frames.tobytes()).hexdigest()]


def test_any_changed_input_changes_the_handle():
    handles = {
        draw().handle,
        draw(seconds=1.0).handle,
        draw(fps=20.0).handle,
        draw(seed=1).handle,
        draw(map_spec="grid:8x8").handle,
        draw({**STRIPES, "seed": 4}).handle,
        draw({"seed": 3, "layers": [stripes(freq=4.5)]}).handle,
    }
    assert len(handles) == 7
    assert draw({"seed": 3, "layers": [stripes(offset=0.0)]}).handle == draw().handle


def test_the_engine_fingerprint_follows_every_byte_of_the_package(tmp_path):
    package = Path(lab.__file__).parent.parent
    copied = tmp_path / "pewpew"
    shutil.copytree(package, copied, ignore=shutil.ignore_patterns("__pycache__", "web"))
    assert fingerprint(copied) == ENGINE
    blend = copied / "fx" / "blend.py"
    blend.write_bytes(blend.read_bytes() + b"\n")
    assert fingerprint(copied) != ENGINE


def test_a_layer_that_raises_is_contained_and_warned_about(fake_ops):
    rendered = draw(one("raises_test", "raises"), seconds=0.5)
    assert any("layers.base.render raised: RuntimeError: broken render (in node layers.base.raises (raises_test))"
               in w for w in rendered.warnings), rendered.warnings


def test_an_expired_handle_says_how_to_recover():
    rendered = draw()
    frames = take(rendered).frames
    shutil.rmtree(Cache().root)
    with pytest.raises(Expired, match="render again with the same look, map, seconds, fps and seed"):
        take(rendered.handle)
    assert np.array_equal(take(rendered).frames, frames)  # a render's spec renders it again


def test_a_brief_render_drops_its_spec_and_cannot_render_again():
    rendered = draw()
    brief = rendered.brief()
    assert brief.to_json() == {**rendered.to_json(), "spec": None}
    assert np.array_equal(take(brief).frames, take(rendered).frames)  # from the cache
    shutil.rmtree(Cache().root)
    with pytest.raises(Expired):
        take(brief)


def test_every_verb_refuses_a_look_that_names_op_pattern_as_any_unknown_op():
    """No op `pattern` runs a file: a look that names
    it is refused as any unknown op is (ADR-025)."""
    named = {"layers": [{"id": "base", "nodes": {"mine": {"op": "pattern", "args": {"pattern": "comet"}}}}]}
    for verb in (lambda: render(named, MAP, SECONDS, FPS), lambda: compare(STRIPES, named, map_spec=MAP),
                 lambda: explain(named)):
        with pytest.raises(Refused) as refused:
            verb()
        assert refused.value.problems[0].code == Code.UNKNOWN_OP


def _entry_size(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.iterdir())


def test_the_cache_stays_under_its_cap_and_drops_the_least_recently_used(tmp_path):
    ticks = iter(range(1, 100))
    geometry = Geometry("line:4", parse_geometry("line:4").mapping)
    frames = np.zeros((2, 4, 3), np.float32)
    names = [f"r1-{i:020x}" for i in range(3)]
    probe = Cache(tmp_path / "probe")
    probe.store(names[0], frames, geometry, {"warnings": []})
    size = _entry_size(probe.root / names[0])
    cache = Cache(tmp_path / "lru", cap=2 * size + size // 2, now=lambda: next(ticks))
    a, b, c = names
    cache.store(a, frames, geometry, {"warnings": []})
    cache.store(b, frames, geometry, {"warnings": []})
    assert cache.load(a) is not None  # a is now newer than b
    cache.store(c, frames, geometry, {"warnings": []})
    assert cache.load(b) is None and cache.load(a) is not None and cache.load(c) is not None
    assert sum(_entry_size(f) for f in cache.root.iterdir()) <= cache.cap


def test_a_sheet_of_a_dropped_render_leaves_its_handle_cacheable():
    rendered = draw()
    folder = Cache().root / rendered.handle
    shutil.rmtree(folder)  # as the LRU drops it
    sheet(rendered)
    assert [f.suffix for f in folder.iterdir()] == [".png"]
    assert draw() == rendered  # stored again, with no "not cached" warning
    assert take(rendered.handle).frames.shape == (60, 64, 3)


def test_the_cache_drops_a_folder_that_holds_only_sheets(tmp_path):
    cache = Cache(tmp_path / "c", cap=0)
    stray = cache.root / f"r1-{0:020x}"
    stray.mkdir(parents=True)
    (stray / "sheet.png").write_bytes(b"png")
    cache.store(f"r1-{1:020x}", np.zeros((2, 4, 3), np.float32), parse_geometry("line:4"), {"warnings": []})
    assert not stray.exists()


def both_at_once(monkeypatch, target: str, call: Callable[[], object]) -> list[BaseException]:
    """What `call` raises when two threads run it and each waits at the
    function `target` (a dotted name) until both reach it, as two tool
    calls of one MCP server can."""
    barrier = threading.Barrier(2, timeout=2)
    original = pkgutil.resolve_name(target)

    def meet(*args, **kw):
        barrier.wait()
        return original(*args, **kw)

    monkeypatch.setattr(target, meet)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            call()
        except BaseException as exc:  # noqa: BLE001 - the test reports whatever a thread raised
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_two_threads_store_one_handle_at_once(tmp_path, monkeypatch):
    cache, key = Cache(tmp_path / "c"), f"r1-{0:020x}"

    def store() -> None:
        cache.store(key, np.zeros((2, 4, 3), np.float32), parse_geometry("line:4"), {"warnings": []})

    assert both_at_once(monkeypatch, "numpy.savez", store) == []
    assert [f.name for f in cache.root.iterdir()] == [key] and cache.load(key) is not None


def test_two_threads_write_one_file_at_once(tmp_path, monkeypatch):
    path = tmp_path / "sheet.png"
    assert both_at_once(monkeypatch, "os.fsync", lambda: write_atomic(path, b"png")) == []
    assert [f.name for f in tmp_path.iterdir()] == ["sheet.png"] and path.read_bytes() == b"png"


def test_an_entry_the_cache_cannot_mark_used_still_loads(tmp_path, monkeypatch):
    cache = Cache(tmp_path / "c")
    cache.store(f"r1-{0:020x}", np.zeros((2, 4, 3), np.float32), parse_geometry("line:4"), {"warnings": []})

    def read_only(*args, **kw):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "utime", read_only)  # another user's cache, or a read-only volume
    assert cache.load(f"r1-{0:020x}") is not None


# ---- sheet, metrics, compare, explain ---------------------------------------------------


def test_a_sheet_is_a_png_of_the_render(tmp_path):
    rendered = draw()
    drawn = sheet(rendered.handle, out=tmp_path / "s.png")
    pixels = decode_png((tmp_path / "s.png").read_bytes())
    assert pixels.shape == (drawn.height, drawn.width, 3) and drawn.layout == "strip"
    cached = sheet(rendered)
    assert Path(cached.path).parent == Cache().root / rendered.handle
    assert Path(cached.path).read_bytes() == (tmp_path / "s.png").read_bytes()


def test_metrics_with_liveness_name_each_dead_knob():
    hidden = {"layers": [stripes(), glow("top", {"opacity": 0.0})]}
    measured = metrics(draw(hidden), liveness=True)
    assert measured.metrics == draw(hidden).metrics
    assert set(measured.dead) >= {"layers.top.hills.scale", "layers.top.hills.speed", "layers.top.tone.shift"}
    assert all(path.startswith("layers.top.") for path in measured.dead)
    assert {p.path for p in probes_of(measured) if p.live} >= {FREQ, "layers.base.waves.sync", "layers.base.tint.shift"}
    assert all(p.path.startswith("layers.base.") for p in probes_of(measured) if p.live)
    assert all(p.rms is not None and p.rms > LIVENESS_RMS for p in probes_of(measured) if p.live)
    assert metrics(draw(hidden)).liveness is None


def test_liveness_moves_a_color_part_with_the_others_as_the_look_sets_them(fake_ops):
    white = one("zoo_test", "zoo", color={"h": 30, "s": 0, "v": 1})
    probes = {p.path: p for p in metrics(draw(white), liveness=True).liveness or ()}
    hue = probes["layers.base.zoo.color.h"]
    assert hue.a["s"] == hue.b["s"] == 0 and not hue.live  # no saturation, so no hue to see
    assert probes["layers.base.zoo.color.s"].live


def late_op() -> None:
    """Define op `late_test`: its `level` shows only once it has run half a
    second, as a trail or a simulation shows once it has filled; its `idle`
    never shows."""

    class LateTest(Op, op="late_test"):
        sig = Sig.SOURCE
        out = Ty.RGB
        stateful = True
        level = Float(0.5, 0.0, 1.0)
        idle = Float(0.5, 0.0, 1.0)

        def setup(self, ctx) -> None:
            super().setup(ctx)
            self.t = 0.0

        def advance(self, ctx: FrameCtx, inputs) -> None:
            self.t += ctx.dt

        def build(self, inputs) -> Fn:
            def late(c: Coords) -> np.ndarray:
                return np.full((len(c.index), 3), self.level * min(max(self.t - 0.5, 0.0), 0.5), np.float32)

            return late


def test_liveness_warms_up_so_a_knob_that_acts_late_is_live_and_one_that_never_acts_is_dead(fake_ops):
    late_op()
    cold = compare(one("late_test", "late", level=0.0), one("late_test", "late", level=1.0),
                   map_spec=MAP, seconds=0.5, fps=FPS)
    assert cold.rms == 0.0  # from a cold start, its first half second shows nothing of it
    probed = {p.path: p for p in metrics(draw(one("late_test", "late"), seconds=1.0),
                                         liveness=True).liveness or ()}
    late, idle = probed["layers.base.late.level"], probed["layers.base.late.idle"]
    assert late.live and late.rms is not None and late.rms > 100 * LIVENESS_RMS
    assert not idle.live and idle.rms == 0.0


def test_liveness_leaves_out_what_the_map_cannot_draw():
    """On a strip along x, lissajous's loops along y and z do nothing, so
    they are not probed; its loops along x are, and are live."""
    knot = program(head={"op": "lissajous", "args": {}}, tint={"op": "palette", "in": ["head"], "args": {}})
    measured = metrics(draw(knot, seconds=1.0), liveness=True)
    paths = {p.path for p in measured.liveness or ()}
    assert "layers.base.head.a" in paths and not {"layers.base.head.b", "layers.base.head.c"} & paths
    assert measured.dead == ()


def unprobable_ops() -> None:
    """Define op `glow_test`, whose palette offers no preset to probe, and
    op `bands_test`, which does not run with its `width` at 0."""

    class GlowTest(Op, op="glow_test"):
        sig = Sig.SOURCE
        out = Ty.RGB
        palette = Palette(EMBER)

        def build(self, inputs) -> Fn:
            return lambda c: np.full((len(c.index), 3), 0.5, np.float32)

    class BandsTest(Op, op="bands_test"):
        sig = Sig.SOURCE
        out = Ty.RGB
        width = Int(4, 0, 8)

        def build(self, inputs) -> Fn:
            step = 1.0 / self.width
            return lambda c: np.full((len(c.index), 3), 0.1 * step, np.float32)


def test_a_knob_that_cannot_be_probed_fails_its_own_look_only(tmp_path, fake_ops):
    unprobable_ops()
    looks = tmp_path / "looks"
    looks.mkdir()
    for name, doc in (("glow", one("glow_test", "glow")), ("bands", one("bands_test", "bands")), ("calm", STRIPES)):
        _write(looks, f"{name}.look.json", book(look=doc))
    result = verify_looks([looks], map_spec=MAP, seconds=1.0, fps=FPS)
    verdicts = {Path(f.file).name: f.looks[0] for f in result.files}
    assert verdicts["calm.look.json"].ok and not result.ok
    assert verdicts["glow.look.json"].failures == (
        "layers.base.glow.palette: palette 'palette' offers no preset other than its default, so nothing probes it",
    )
    (failure,) = verdicts["bands.look.json"].failures
    assert failure.startswith("layers.base.bands.width: the look does not run with it at 0: ")
    measured = metrics(draw(one("bands_test", "bands"), seconds=0.5), liveness=True)
    assert measured.unprobed == (failure,) and measured.dead == ()


def test_a_look_compared_with_itself_differs_nowhere():
    same = compare(STRIPES, STRIPES, map_spec=MAP, seconds=SECONDS, fps=FPS)
    assert same.a == same.b and same.look_diff == ()
    assert (same.rms, same.max_abs, same.first_divergent_frame, same.delta_e_p95) == (0.0, 0.0, None, 0.0)
    assert set(same.metric_deltas.values()) == {0}


def test_compare_names_each_changed_knob_and_where_the_frames_part():
    finer = {"seed": 3, "layers": [stripes(freq=8.0)]}
    a = draw()
    diff = compare(a, finer)  # the look renders as A did
    assert diff.a == a.handle and diff.b == draw(finer).handle
    assert [(c.path, c.a, c.b) for c in diff.look_diff] == [(FREQ, 4.0, 8.0)]
    assert diff.rms > 0 and diff.first_divergent_frame is not None and diff.metric_deltas["frames"] == 0
    with pytest.raises(ValueError, match="rendered alike"):
        compare(a, draw(seconds=1.0))


def test_the_look_diff_names_each_signal_route_and_front_change():
    """Modulation changes the picture as a knob does, so the diff names it
    (ADR-006: `signals.<signal>.<arg>` is a knob's address)."""
    base = check_look({**TIDE, "signals": {"breath": {"op": "lfo", "args": {"rate": 0.05}}},
                       "routes": [{"source": "breath", "path": "layers.base.tint.shift", "depth": 30.0}]})
    assert base.ok and base.look_normalized is not None
    a = base.look_normalized
    b = json.loads(json.dumps(a))
    b["signals"]["breath"]["args"] |= {"rate": 0.5, "shape": "square"}
    b["routes"][0]["depth"] = 45.0
    b["front"] = ["layers.base.waves.freq"]
    assert [(c.path, c.a, c.b) for c in comparison.look_diff(a, b)] == [
        ("front", None, ["layers.base.waves.freq"]),
        ("signals.breath.rate", 0.05, 0.5),
        ("signals.breath.shape", "sine", "square"),
        ("routes[breath -> layers.base.tint.shift]", 30.0, 45.0),
    ]
    b["signals"]["breath"]["op"] = "walk"
    assert comparison.look_diff(a, b)[1].path == "signals.breath"  # its op, as a node's is


def test_compare_renders_a_look_on_the_map_spec_of_a_so_its_spec_gives_its_handle():
    a = render(STRIPES, "line:16", seconds=0.5)
    diff = compare(a, {"seed": 3, "layers": [glow("base")]})  # on A's line:16, not the default
    spec = take(diff.b).spec
    assert spec.map == "line:16"
    assert render(spec.look, spec.map, spec.seconds, spec.fps, spec.seed).handle == diff.b
    with pytest.raises(ValueError, match="A and B must be rendered alike to compare"):
        compare(a, render(STRIPES, seconds=0.5))  # on the default grid


def test_a_look_on_side_a_renders_as_the_render_on_side_b():
    finer = {"seed": 3, "layers": [stripes(freq=8.0)]}
    b = draw(finer, seconds=1.0)
    diff = compare(STRIPES, b)  # not the default auto map and seconds: those of B
    assert (diff.a, diff.b) == (draw(seconds=1.0).handle, b.handle)
    assert [(c.path, c.a, c.b) for c in diff.look_diff] == [(FREQ, 4.0, 8.0)]


def test_frames_holding_nan_compare_and_probe_as_a_sink_draws_them(fake_ops):
    class NannyTest(Op, op="nanny_test"):
        sig = Sig.SOURCE
        out = Ty.RGB
        level = Float(0.5, 0.0, 1.0)

        def build(self, inputs) -> Fn:
            def nanny(c: Coords) -> np.ndarray:
                out = np.full((len(c.index), 3), self.level, np.float32)
                out[0] = np.nan
                return out

            return nanny

    look = one("nanny_test", "nanny")
    same = compare(look, look, map_spec=MAP, seconds=0.5, fps=FPS)
    assert (same.rms, same.max_abs, same.first_divergent_frame) == (0.0, 0.0, None)
    measured = metrics(draw(look, seconds=0.5), liveness=True)
    assert measured.metrics.nonfinite > 0 and measured.dead == ()  # level moves every pixel but the NaN one
    for result in (same, measured):
        json.dumps(result.to_json(), allow_nan=False)  # NaN is not JSON


def test_compare_sheet_draws_a_over_b(tmp_path):
    drawn = lab.compare_sheet(STRIPES, DUO, out=tmp_path / "ab.png", map_spec=MAP, seconds=SECONDS, fps=FPS)
    assert drawn.legend.startswith("Row A and row B") and len(drawn.handles) == 2


def test_explain_tells_each_layer_and_knob_the_same_way_every_time():
    words = explain(DUO)
    assert words == explain(json.dumps(DUO))
    assert words.summary.startswith("2 layers, bottom first: base (normal blend at opacity 1), then top")
    assert "sets the master to 0.8" in words.summary
    assert words.layers[0].knobs[0] == "waves.freq = 4 (0.5..32): More stripes across the room"
    assert words.layers[0].about.startswith("2 nodes: waves (osc, Oscillator): Stripes along one axis")
    assert words.layers[1].mix == "screen blend at opacity 0.5"


# ---- verify looks -------------------------------------------------------------------------

def strobe_op() -> None:
    """Define op `strobe_test`: the whole map on and off `rate` times a second."""

    class StrobeTest(Op, op="strobe_test"):
        sig = Sig.SOURCE
        out = Ty.RGB
        stateful = True
        rate = Float(5.0, 1.0, 10.0, "/s")

        def setup(self, ctx) -> None:
            super().setup(ctx)
            self.t = 0.0

        def advance(self, ctx: FrameCtx, inputs) -> None:
            self.t += ctx.dt

        def build(self, inputs) -> Fn:
            def strobe(c: Coords) -> np.ndarray:
                on = (self.t * self.rate) % 1.0 < 0.5
                return np.full((len(c.index), 3), 1.0 if on else 0.0, np.float32)

            return strobe


def _write(folder: Path, name: str, doc: dict) -> Path:
    path = folder / name
    path.write_text(json.dumps(doc))
    return path


def test_verify_passes_a_calm_look_and_fails_a_strobe_and_a_black_look(tmp_path, fake_ops):
    strobe_op()
    looks = tmp_path / "looks"
    looks.mkdir()
    _write(looks, "calm.look.json", book(calm=STRIPES))
    _write(looks, "strobe.look.json", book(strobe=one("strobe_test", "strobe")))
    _write(looks, "dark.look.json", book(dark={"layers": [stripes(mix={"opacity": 0.0})]}))
    _write(looks, "notes.json", {"not": "a look"})  # not a *.look.json file
    result = verify_looks([looks], map_spec=MAP, seconds=SECONDS, fps=FPS)
    verdicts = {v.name: v for f in result.files for v in f.looks}
    assert not result.ok and set(verdicts) == {"calm", "strobe", "dark"}
    assert verdicts["calm"].ok and verdicts["calm"].failures == ()
    assert any(f.startswith("flashes up to 5") for f in verdicts["strobe"].failures)
    assert "every frame is black" in verdicts["dark"].failures
    assert verdicts["dark"].dead  # nothing it does shows


def test_verify_fails_a_render_too_short_to_judge_flashing(tmp_path):
    path = _write(tmp_path, "calm.look.json", book(calm=STRIPES))
    (verdict,) = verify_looks([path], map_spec=MAP, seconds=0.5, fps=FPS).files[0].looks
    (failure,) = verdict.failures
    assert failure.startswith("0.5 s is too short to judge flashing") and not verdict.ok


def test_verify_fails_a_file_that_does_not_check_and_a_folder_or_file_with_no_looks(tmp_path):
    bad = _write(tmp_path, "bad.look.json", book(bad={"layers": [stripes(frek=4.0)]}))
    empty = tmp_path / "empty"
    empty.mkdir()
    hollow = _write(tmp_path, "hollow.look.json", book())
    result = verify_looks([bad, empty, hollow], map_spec=MAP, seconds=SECONDS, fps=FPS)
    assert not result.ok
    assert [f.problems[0].code for f in result.files] == [Code.UNKNOWN_KEY, Code.MISSING, Code.MISSING]
    assert result.files[2].problems[0].path == "looks"


def test_verify_renders_fresh_and_never_reads_the_cache(tmp_path, monkeypatch):
    path = _write(tmp_path, "calm.look.json", book(calm=STRIPES))
    monkeypatch.setattr(Cache, "load", lambda self, key: pytest.fail("verify read the cache"))
    (verdict,) = verify_looks([path], map_spec=MAP, seconds=SECONDS, fps=FPS).files[0].looks
    assert verdict.ok and verdict.name == "calm"


# ---- the catalog, a page at a time ------------------------------------------------------------


def test_a_catalog_search_pages_concise_items_and_details_on_request():
    first = lab.catalog()
    assert len(first.items) == search.PAGE["concise"] and first.next_cursor == "50"
    rest = lab.catalog(cursor=first.next_cursor)
    found = [(item.kind, item.name) for item in (*first.items, *rest.items)]
    assert rest.next_cursor is None and len(set(found)) == first.total == len(search.index().items)
    assert {kind for kind, _ in found} == {"op", "blend", "palette", "kind"}
    (kaleid,) = lab.catalog("coord", "mirrored fold").items
    assert (kaleid.name, kaleid.sig, kaleid.label, kaleid.record) == ("kaleid", "coord", "Kaleidoscope", None)
    assert kaleid.summary == "Folds a pattern into mirrored wedges about the center, as a kaleidoscope does."
    detailed = lab.catalog("palette", detail="detailed")
    assert len(detailed.items) == search.PAGE["detailed"] - 2 and detailed.next_cursor is None
    assert detailed.items[0].record == lab.describe("palette", "ember")


@pytest.mark.parametrize(("call", "path", "code", "guess"), [
    (lambda: lab.catalog("cord"), "kind", Code.OUT_OF_RANGE, "coord"),
    (lambda: lab.catalog(cursor="7x"), "cursor", Code.OUT_OF_RANGE, None),
    (lambda: lab.catalog(detail="brief"), "detail", Code.OUT_OF_RANGE, None),  # type: ignore[arg-type]
    (lambda: lab.describe("ops", "kaleid"), "kind", Code.OUT_OF_RANGE, "op"),
    (lambda: lab.describe("op", "kaleidd"), "name", Code.UNKNOWN_OP, "kaleid"),
    (lambda: lab.describe("blend", "scren"), "name", Code.BAD_REF, "screen"),
])
def test_a_search_for_what_is_not_there_is_one_coded_problem(call, path, code, guess):
    with pytest.raises(Refused) as refused:
        call()
    (found,) = refused.value.problems
    assert (found.path, found.code, found.did_you_mean) == (path, code, guess)


def test_example_looks_check():
    first, program = search.example_looks()
    assert check_look(first).ok and check_look(program).ok
    assert program["layers"][0]["nodes"]["kaleid"]["op"] == search.EXAMPLE_OP


@pytest.mark.parametrize(("found", "fix"), [
    (lab.Problem("layers.base.waves.frek", Code.UNKNOWN_KEY, "", "freq", ("freq", "sync")),
     "rename 'frek' to 'freq'"),
    (lab.Problem("layers.base.waves.zz", Code.UNKNOWN_KEY, "", None, ("freq", "sync")),
     "remove 'zz'; the keys there are freq, sync"),
    (lab.Problem("layers.base.blend", Code.OUT_OF_RANGE, "", "screen", ("normal", "screen")),
     "set layers.base.blend to 'screen'"),
    (lab.Problem(FREQ, Code.OUT_OF_RANGE, "", None, ("0.5..32.0",), 4.0),
     "set layers.base.waves.freq within 0.5..32.0, such as 4.0"),
    (lab.Problem("layers.base.osc.axis", Code.OUT_OF_RANGE, "", None, ("u", "x", "y")),
     "set layers.base.osc.axis to one of u, x, y"),
    (lab.Problem("layers.base.on", Code.WRONG_KIND, "", None, ("true", "false")),
     "set layers.base.on to true or false"),
    (lab.Problem("", Code.NOT_A_LOOK, "", example={"layers": []}), 'set the look to {"layers": []}'),
    (lab.Problem("layers.base.k", Code.WRONG_DIMS, "", valid=("2", "3")),
     "render on a map of 2 or 3 dimensions"),
    (lab.Problem("version", Code.WRONG_VERSION, "", valid=("4",), example=4), "set version to 4"),
    (lab.Problem("layers.base.k", Code.CYCLE, ""), None),
    (lab.Problem("layers.base.o.op", Code.UNKNOWN_OP, "unknown op 'x'; ops: add, below, blend", None,
                 ("add", "below", "blend")), "set layers.base.o.op to one of the 3 its reason lists"),
    (lab.Problem("layers.base.zz", Code.UNKNOWN_KEY, "unknown key 'zz'; expected id, nodes, out", None,
                 ("id", "nodes", "out")), "remove 'zz'"),
])
def test_a_problem_says_the_edit_that_fixes_it(found, fix):
    assert found.fix == fix
    assert found.to_json()["fix"] == fix  # the JSON an agent reads carries it


def test_one_misspelt_address_is_one_code_wherever_it_is_written():
    """A set, a route and a front knob name a knob alike (ADR-023 codes)."""
    reason = look_controls(ready(STRIPES).look).parse("layers.base.waves.frek", 1)[1]
    found = problem(reason or "")
    assert (found.code, found.did_you_mean) == (Code.BAD_REF, FREQ)


def test_a_program_given_as_a_look_is_told_to_wrap_it_as_a_layer():
    """A catalog example's JSON is a layer's program (pewpew.fx.catalog)."""
    (shown,) = lab.describe("op", "noise")["examples"][:1]
    (found,) = check_look(shown["json"]).problems
    assert found.code == Code.NOT_A_LOOK and "wrap" not in found.reason and "holds it as a layer" in found.reason
    assert found.example == {"layers": [{"id": "base", **shown["json"]}]}
    assert check_look(found.example).ok


def test_a_key_written_twice_is_refused_not_dropped():
    text = ('{"layers": [{"id": "base", "nodes": {"osc": {"op": "osc"}, "osc": {"op": "noise"}, '
            '"t": {"op": "palette", "in": ["osc"]}}}]}')
    (found,) = check_look(text).problems
    assert found.code == Code.BAD_REF and found.reason.startswith("duplicate key 'osc': ")


# ---- results -----------------------------------------------------------------------------------

ROOTS = (lab.Check, lab.Rendered, lab.Picture, lab.Measured, lab.Comparison, lab.Explanation, lab.Verification,
         lab.CatalogPage)


@pytest.mark.parametrize("cls", ROOTS, ids=[c.__name__ for c in ROOTS])
def test_a_root_result_is_frozen_and_not_slotted(cls):
    """An MCP tool returns these whole; its SDK reads their defaults off the
    class, which a slotted class hides (ADR-023)."""
    assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen  # type: ignore[attr-defined]
    assert "__slots__" not in cls.__dict__
    assert not any(f.default_factory is not dataclasses.MISSING for f in dataclasses.fields(cls))


def test_to_json_keeps_field_order_and_round_trips_as_json():
    rendered = draw()
    doc = rendered.to_json()
    assert list(doc) == [f.name for f in dataclasses.fields(lab.Rendered)]
    assert list(doc["spec"]) == [f.name for f in dataclasses.fields(lab.RenderSpec)]
    assert json.loads(json.dumps(doc)) == doc
