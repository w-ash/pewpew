"""Colorways: a look's named sets of knob values (ADR-006 amendment
"colorways"). The codec reads, checks and writes them; a press sets one
on the running look in one frame while its motion carries on, and what
the ops read glides there over the look's fade; a save keeps them, less
what names no knob; the lab renders, explains and gates a look in each."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from fakes import aura_rig, filed, restore
from params_zoo import ZOO
from pewpew import lab
from pewpew.__main__ import main
from pewpew.color import EMBER, ICE, MONO, gradient_lut, oklab
from pewpew.compose import Layer
from pewpew.compose.stack import with_colorway
from pewpew.fx import expr, surprise
from pewpew.fx.codec import decode_look, encode_look, to_python
from pewpew.fx.graph import Graph, Node
from pewpew.fx.ops import OPS
from pewpew.lab.verify import verify_looks
from pewpew.params import HSV, Color, Float, Gradient, Int, Palette, ParamSet, Stop
from pewpew.problems import Code, Refused

SHIFT, PALETTE, FREQ = "layers.base.tint.shift", "layers.base.tint.palette", "layers.base.waves.freq"
DOC = {
    "layers": [{"id": "base", "out": "tint", "nodes": {
        "waves": {"op": "osc", "args": {"freq": 4.0}},
        "tint": {"op": "palette", "in": ["waves"], "args": {"palette": "ember"}}}}],
    "signals": {"breath": {"op": "lfo", "args": {"rate": 0.5}}},
    "routes": [{"source": "breath", "path": SHIFT, "depth": 20.0}],
    "colorways": {"ember": {PALETTE: "ember", SHIFT: 0},
                  "ice": {PALETTE: "ice", SHIFT: 40, "layers.base.opacity": 0.8}},
}
RENDER = {"map_spec": "line:16", "seconds": 1.0, "fps": 10.0}


def palette(name: str) -> dict:
    """Preset `name` in a palette knob's JSON form."""
    return ParamSet(OPS["palette"], {"palette": name}).snapshot_json()["palette"]


def decoded(doc: dict = DOC):
    look, problems = decode_look(doc)
    assert look is not None, problems
    return look


# ---- the file ------------------------------------------------------------------


def test_colorways_round_trip_in_their_knobs_json_form():
    look = decoded()
    assert look.colorways == {"ember": {PALETTE: palette("ember"), SHIFT: 0.0},
                              "ice": {PALETTE: palette("ice"), SHIFT: 40.0, "layers.base.opacity": 0.8}}
    assert list(look.colorways) == ["ember", "ice"], "file order"
    assert decoded(encode_look(look)) == look
    assert "colorways={" in to_python(look)
    built = expr.look(expr.layer("base", expr.osc(4.0).id("waves").palette("ember").id("tint")),
                      colorways=DOC["colorways"])
    assert built.colorways == look.colorways


@pytest.mark.parametrize(("colorways", "path", "code", "fix"), [
    ({"ice": {"layers.base.tnt.palette": "ice"}}, "colorways.ice.layers.base.tnt.palette", Code.UNKNOWN_KEY,
     f"rename 'layers.base.tnt.palette' to '{PALETTE}'"),
    ({"ice": {SHIFT: 999}}, f"colorways.ice.{SHIFT}", Code.OUT_OF_RANGE,
     f"set colorways.ice.{SHIFT} within 0.0..360.0"),
    ({"ice": {PALETTE: "icee"}}, f"colorways.ice.{PALETTE}", Code.OUT_OF_RANGE,
     f"set colorways.ice.{PALETTE} to 'ice'"),
    ({"ice": {}}, "colorways.ice", Code.WRONG_KIND, None),
    ({"no.dots": {SHIFT: 1}}, "colorways.no.dots", Code.WRONG_KIND, None),
    ({f"c{i}": {SHIFT: i} for i in range(25)}, "colorways", Code.OUT_OF_RANGE, None),
])
def test_a_bad_colorway_is_refused_with_its_path(colorways, path, code, fix):
    doc = {**DOC, "colorways": colorways}
    (problem,) = lab.check_look(doc).problems
    assert (problem.path, problem.code, problem.fix) == (path, code, fix)
    (in_file,) = lab.check_look(json.loads(filed(doc))).problems
    assert in_file.path == f"looks.look.{path}"


@pytest.mark.usefixtures("fake_ops")
def test_a_part_of_a_knob_is_refused_by_its_address():
    doc = {"layers": [{"id": "base", "nodes": {"zoo": {"op": ZOO, "args": {}}}}],
           "colorways": {"warm": {"layers.base.zoo.color.h": 30.0}}}
    (problem,) = lab.check_look(doc).problems
    assert (problem.path, problem.code) == ("colorways.warm.layers.base.zoo.color.h", Code.WRONG_KIND)
    assert problem.reason.endswith("set layers.base.zoo.color as a whole")


def test_with_colorway_sets_its_knobs_and_names_the_closest_when_it_has_none():
    look = with_colorway(decoded(), "ice")
    assert look.layers[0].opacity == 0.8
    assert look.layers[0].program.graph["tint"].args["shift"] == 40.0
    with pytest.raises(ValueError, match=r"unknown colorway 'icee' \(did you mean 'ice'\?\)"):
        with_colorway(decoded(), "icee")


# ---- the running aura -------------------------------------------------------------


def dusk(look=None, **kw):
    look = look or decoded()
    rig = aura_rig(look, looks={"dusk": look}, current="dusk", **kw)
    assert restore(rig) is None
    rig.frame(rig.clock.advance())
    return rig


def stack_state(rig) -> dict:
    return rig.control.state()["stack"]


def test_a_press_sets_every_knob_in_one_frame_and_the_motion_carries_on():
    rig = dusk()
    stack, renderer = rig.fader.current, rig.renderer()
    assert (stack_state(rig)["colorways"], stack_state(rig)["colorway"]) == (["ember", "ice"], "ember")
    assert rig.control.request({"type": "colorway", "name": "ice"}) is None
    assert rig.control.values()[SHIFT] == 0.0, "nothing lands before the loop runs the press"
    rig.calls.drain()
    values = rig.control.values()
    assert (values[PALETTE], values[SHIFT], values["layers.base.opacity"]) == (palette("ice"), 40.0, 0.8)
    rig.frame(rig.clock.advance())
    assert rig.fader.current is stack and rig.renderer() is renderer, "the same stack runs on: no recall"
    assert stack_state(rig)["colorway"] == "ice" and rig.looks.changed()
    assert stack_state(rig)["routes"] == DOC["routes"]
    rig.frame(rig.clock.advance(130))  # past the look's 2 s fade: the glide has landed
    assert 20.0 <= rig.control.mod()[SHIFT] <= 60.0, "the route moves around the colorway's value"
    assert rig.looks.recall("dusk", 0.0) is None
    assert stack_state(rig)["colorway"] == "ember" and not rig.looks.changed(), "revert brings the saved colours"


def test_one_refused_value_refuses_the_whole_colorway():
    bad = replace(decoded(), colorways={**decoded().colorways, "bad": {SHIFT: 10.0, FREQ: 999.0}})
    rig = dusk(bad)
    reason = rig.control.colorway("bad")
    assert reason is not None and reason.startswith(f"colorway 'bad': {FREQ} must be within")
    rig.calls.drain()
    assert rig.control.values()[SHIFT] == 0.0
    assert rig.control.colorway("icee") == "unknown colorway 'icee' (did you mean 'ice'?); colorways: ember, ice, bad"


def test_a_save_keeps_the_values_and_the_colorways_less_what_names_no_knob():
    two = replace(decoded(), layers=(*decoded().layers, Layer("top", decoded().layers[0].program, opacity=0.5)),
                  colorways={**decoded().colorways, "top": {"layers.top.tint.shift": 90.0},
                             "both": {SHIFT: 10.0, "layers.top.opacity": 0.2}})
    rig = dusk(two)
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    assert rig.deck.remove("top") is None
    assert stack_state(rig)["colorways"] == ["ember", "ice", "both"]
    assert rig.looks.save("dusk") is None
    saved = rig.looks.book.looks["dusk"]
    assert saved.colorways == {**decoded().colorways, "both": {SHIFT: 10.0}}
    assert saved.layers[0].program.graph["tint"].args["shift"] == 40.0
    assert stack_state(rig)["colorway"] == "ice", "the active colorway is the values, so a save keeps it"


# ---- the glide ---------------------------------------------------------------------


def test_a_number_glides_on_a_line_and_a_hue_the_short_way_round():
    assert Float(0.0, 0.0, 10.0).mix(2.0, 6.0, 0.25) == 3.0
    angle = Float(0.0, 0.0, 360.0, periodic=True)
    assert angle.mix(350.0, 30.0, 0.5) == 10.0, "through 0, not through 180"
    assert angle.mix(30.0, 350.0, 0.75) == pytest.approx(0.0)
    assert Int(0, 0, 10).mix(0, 3, 0.5) == 2, "an Int rounds half up"
    color = Color((0.0, 1.0, 1.0)).mix(HSV(340.0, 1.0, 0.0), HSV(20.0, 0.0, 1.0), 0.5)
    assert (color.h, color.s, color.v) == pytest.approx((0.0, 0.5, 0.5))


def test_a_palette_glides_in_oklab_whatever_stops_each_has():
    edge = Gradient((Stop(0.0, HSV(0.0, 1.0, 1.0)), Stop(0.5, HSV(0.0, 1.0, 1.0)),
                     Stop(0.5, HSV(240.0, 1.0, 1.0)), Stop(0.8, HSV(200.0, 1.0, 0.5)), Stop(1.0, HSV(240.0, 1.0, 1.0))))
    kind = Palette(EMBER)
    for start, end in ((EMBER, MONO), (MONO, ICE), (EMBER, edge), (edge, ICE)):
        assert len(start.stops) != len(end.stops)
        for w in (0.25, 0.5, 0.75):
            shown = kind.mix(start, end, w)
            assert (shown.stops, shown.glide) == (end.stops, (start, w)), "the target's stops, gliding from the start"
            a, b = oklab(gradient_lut(start)), oklab(gradient_lut(end))
            np.testing.assert_allclose(oklab(gradient_lut(shown)), a + (b - a) * w, atol=2e-3)
        assert kind.mix(start, end, 1.0) is end
        np.testing.assert_allclose(gradient_lut(kind.mix(start, end, 0.0)), gradient_lut(start), atol=1e-5)
    assert kind.mix(EMBER, ICE, 0.3).glide == (EMBER, 38 / 128), "the weight steps in 1/128ths"
    assert kind.parse("p", kind.mix(EMBER, ICE, 0.5)) == (ICE, None), "a set of a gliding value lands the target"


def target(rig, path: str):
    """The live value of the knob at `path` as its op reads it."""
    knob = rig.deck.controls.find(path)
    return getattr(knob.params.bound.target, knob.name)


def test_a_press_glides_what_the_ops_read_over_the_look_s_fade_while_its_own_values_land():
    rig = dusk()
    t0 = rig.clock.t
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    assert rig.control.values()[PALETTE] == palette("ice"), "the own value is the target at once"
    assert stack_state(rig)["colorway"] == "ice", "the active colorway names the target from the press on"
    rig.frame(rig.clock.advance(60))  # one of the look's two seconds
    shown = target(rig, PALETTE)
    assert shown.glide is not None and shown.glide[0] == EMBER and shown.glide[1] == pytest.approx(0.5, abs=0.01)
    assert target(rig, "layers.base.opacity") == pytest.approx(0.9, abs=0.01)
    assert rig.fader.current.gliding() == [PALETTE, SHIFT, "layers.base.opacity"]
    rig.frame(rig.clock.advance(61))
    assert rig.clock.t - t0 > 2.0
    assert target(rig, PALETTE) == ICE and target(rig, "layers.base.opacity") == 0.8
    assert rig.fader.current.gliding() == [], "each glide has landed"


def test_a_press_mid_glide_glides_on_from_what_shows():
    rig = dusk()
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    rig.frame(rig.clock.advance(30))  # a quarter of the way to ice
    before = target(rig, PALETTE)
    assert rig.control.colorway("ember") is None
    rig.calls.drain()
    now = target(rig, PALETTE)
    assert now.glide == (before, 0.0) and now.stops == EMBER.stops, "it starts from what showed, not from ice"
    np.testing.assert_allclose(gradient_lut(now), gradient_lut(before), atol=1e-5)
    rig.frame(rig.clock.advance(121))
    assert target(rig, PALETTE) == EMBER


def test_a_save_during_a_glide_stores_the_target_and_a_set_lands_it():
    rig = dusk()
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    rig.frame(rig.clock.advance(30))
    assert rig.looks.save("dusk") is None
    saved = rig.looks.book.looks["dusk"]
    assert saved.layers[0].program.graph["tint"].args["palette"] == palette("ice")
    assert saved.layers[0].opacity == 0.8
    assert rig.control.set("layers.base.opacity", 0.5) is None
    rig.calls.drain()
    assert target(rig, "layers.base.opacity") == 0.5, "a set of a gliding knob shows at once"
    rig.frame(rig.clock.advance())
    assert "layers.base.opacity" not in rig.fader.current.gliding()


def test_a_look_that_cuts_changes_colour_at_once_and_a_choice_never_glides():
    look = replace(decoded(), fade=0.0)
    rig = dusk(look)
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    assert target(rig, PALETTE) == ICE and rig.fader.current.gliding() == []
    blend = replace(decoded(), colorways={"soft": {"layers.base.blend": "screen", "layers.base.opacity": 0.5}})
    rig = dusk(blend)
    assert rig.control.colorway("soft") is None
    rig.calls.drain()
    assert target(rig, "layers.base.blend") == "screen", "a choice switches at the start"
    assert rig.fader.current.gliding() == ["layers.base.opacity"]


# ---- the lab -----------------------------------------------------------------------


def test_render_takes_a_colorway_and_names_the_closest_when_it_has_none():
    plain, ice = lab.render(DOC, **RENDER), lab.render(DOC, **RENDER, colorway="ice")
    assert plain.handle != ice.handle and plain.metrics != ice.metrics
    assert ice.spec is not None and ice.spec.look["layers"][0]["opacity"] == 0.8
    with pytest.raises(Refused) as caught:
        lab.render(json.loads(filed(DOC)), **RENDER, colorway="icee")
    (problem,) = caught.value.problems
    assert (problem.path, problem.code, problem.did_you_mean) == ("looks.look.colorways", Code.BAD_REF, "ice")
    assert "Colorways: ember, ice." in lab.explain(DOC).summary


def test_the_cli_renders_a_colorway(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    file = tmp_path / "dusk.look.json"
    file.write_text(filed(DOC))
    timing = ["--map", "line:16", "--seconds", "1", "--fps", "10"]
    assert main(["fx", "render", str(file), *timing, "--colorway", "ice", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == lab.render(file, **RENDER, colorway="ice").to_json()
    assert main(["fx", "render", str(file), *timing, "--colorway", "icee"]) == 1
    assert "did you mean 'ice'?" in capsys.readouterr().err
    assert main(["fx", "explain", str(file), "--colorway", "ice"]) == 0
    assert "opacity 0.8" in capsys.readouterr().out


def test_verify_gates_each_colorway_and_refuses_two_alike(tmp_path: Path):
    distinct, alike = tmp_path / "distinct.look.json", tmp_path / "alike.look.json"
    distinct.write_text(filed(DOC))
    alike.write_text(filed({**DOC, "colorways": {**DOC["colorways"], "copy": {PALETTE: "ice", SHIFT: 40.0,
                                                                          "layers.base.opacity": 0.8}}}))
    dark = tmp_path / "dark.look.json"
    dark.write_text(filed({**DOC, "colorways": {**DOC["colorways"], "off": {"layers.base.opacity": 0.0}}}))
    verdict = verify_looks([distinct, alike, dark], map_spec="line:16", seconds=1.0, fps=10.0)
    ok, same, black = (f.looks[0] for f in verdict.files)
    assert ok.ok, ok.failures
    assert same.failures == ("colorways 'ice' and 'copy' show the same picture (RMS 0); give each its own colours",)
    assert black.failures == ("colorway 'off': every frame is black",)


def test_a_variation_drops_a_colorway_knob_that_is_gone():
    look = decoded()
    stale = replace(look, colorways={"ice": look.colorways["ice"], "ghost": {"layers.base.ghost.freq": 2.0},
                                     "breath": {"signals.breath.rate": 0.2, SHIFT: 5.0}})
    unread = Node("idle", "lfo", {"rate": 0.1})
    made = surprise._pruned(stale, [*(look.signals or ()), unread], look.routes)
    assert made.colorways == {"ice": look.colorways["ice"], "breath": {"signals.breath.rate": 0.2, SHIFT: 5.0}}
    gone = surprise._pruned(replace(stale, colorways={"idle": {"signals.idle.rate": 0.2}}),
                            [*(look.signals or ()), unread], look.routes)
    assert gone.colorways == {} and gone.signals == Graph(tuple(look.signals or ()))
