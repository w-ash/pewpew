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

from fakes import LoopThread, aura_rig, filed, restore
from params_zoo import ZOO
from pewpew import lab
from pewpew.__main__ import main
from pewpew.aura.book import CycleConfig, parse_looks
from pewpew.color import EMBER, ICE, MONO, gradient_lut, oklab
from pewpew.compose import Layer
from pewpew.compose.stack import Drift, kept_drift, with_colorway
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


# ---- the drift ---------------------------------------------------------------------

THREE = {**DOC["colorways"], "dawn": {PALETTE: "candy", SHIFT: 10}}
DRIFTING = {**DOC, "colorways": THREE, "colorway_drift": {"every": [2, 4]}}


def test_a_drift_round_trips_and_is_written_only_when_given():
    look = decoded(DRIFTING)
    assert look.drift == Drift((2.0, 4.0))
    assert encode_look(look)["colorway_drift"] == {"every": [2.0, 4.0]}
    assert decoded(encode_look(look)) == look
    named = decoded({**DRIFTING, "colorway_drift": {"every": 30, "names": ["ice", "dawn"], "on": False}})
    assert encode_look(named)["colorway_drift"] == {"every": 30.0, "names": ["ice", "dawn"], "on": False}
    assert "colorway_drift" not in encode_look(decoded())
    assert "colorway_drift={'every': [2.0, 4.0]}" in to_python(look).replace('"', "'")
    built = expr.look(expr.layer("base", expr.osc(4.0).id("waves").palette("ember").id("tint")),
                      colorways=THREE, colorway_drift={"every": [2, 4]})
    assert built.drift == look.drift


@pytest.mark.parametrize(("drift", "path", "code", "fix"), [
    ({"every": 0}, "colorway_drift.every", Code.OUT_OF_RANGE, "set colorway_drift.every within 1..86400"),
    ({"every": [9, 3]}, "colorway_drift.every", Code.OUT_OF_RANGE, "set colorway_drift.every within 1..86400"),
    ({"evry": 30}, "colorway_drift.evry", Code.UNKNOWN_KEY, "rename 'evry' to 'every'"),
    ({"names": ["ice", "icee"]}, "colorway_drift.names[1]", Code.BAD_REF, "set colorway_drift.names[1] to 'ice'"),
    ({"names": ["ice"]}, "colorway_drift.names", Code.WRONG_KIND, None),
    ({"on": "yes"}, "colorway_drift.on", Code.WRONG_KIND, "set colorway_drift.on to true or false"),
    (30, "colorway_drift", Code.WRONG_KIND, None),
])
def test_a_bad_drift_is_refused_with_its_path(drift, path, code, fix):
    doc = {**DRIFTING, "colorway_drift": drift}
    (problem,) = lab.check_look(doc).problems
    assert (problem.path, problem.code, problem.fix) == (path, code, fix)
    (in_file,) = lab.check_look(json.loads(filed(doc))).problems
    assert in_file.path == f"looks.look.{path}"


def test_a_drift_needs_two_colorways_to_move_between():
    doc = {**DOC, "colorways": {"ice": DOC["colorways"]["ice"]}, "colorway_drift": {}}
    (problem,) = lab.check_look(doc).problems
    assert (problem.path, problem.reason) == (
        "colorway_drift", "colorway_drift: a drift moves between at least 2 colorways, and the look has 1")
    assert kept_drift(Drift(names=("ice", "dawn")), ["ember", "ice"]) is None, "one name left: it goes"
    assert kept_drift(Drift(names=("ice", "dawn", "ember")), ["ember", "ice"]) == Drift(names=("ice", "ember"))


def drifted(rig, seconds: float, step: int = 6) -> list[tuple[float, str | None]]:
    """Each change of the active colorway over `seconds` of frames, `step` slots apart: its time and name."""
    seen, out = stack_state(rig)["colorway"], []
    end = rig.clock.t + seconds
    while rig.clock.t < end:
        rig.frame(rig.clock.advance(step))
        if (now := stack_state(rig)["colorway"]) != seen:
            out.append((round(rig.clock.t, 4), now))
            seen = now
    return out


def test_a_drift_changes_colorway_by_engine_time_the_same_way_every_run():
    runs = [drifted(dusk(decoded(DRIFTING)), 40.0) for _ in range(2)]
    assert runs[0] == runs[1], "same seed, same engine times: the same changes"
    times, names = [t for t, _ in runs[0]], [n for _, n in runs[0]]
    assert len(times) >= 8 and set(names) == set(THREE)
    gaps = np.diff([0.0, *times])
    assert all(1.9 <= gap <= 4.2 for gap in gaps), gaps
    assert all(a != b for a, b in zip(["ember", *names], names)), "never the same one twice running"
    other = drifted(dusk(replace(decoded(DRIFTING), seed=5)), 40.0)
    assert other != runs[0], "another seed draws other changes"


def test_a_drift_is_the_look_playing_not_an_edit():
    cycle = CycleConfig(idle=1000.0, each=60.0)
    rig = dusk(replace(decoded(DRIFTING), cycle=True), cycle=cycle)
    looks = rig.looks.state()
    assert not looks["changed"] and looks["next"] is not None
    changes = drifted(rig, 12.0)
    assert changes, "it drifted"
    after = rig.looks.state()
    assert not after["changed"], "no unsaved edit"
    assert after["next"] == looks["next"], "the idle wait never restarted: no operator input"
    assert after["saved"][PALETTE] == rig.control.values()[PALETTE], "a knob reverts to the drifted colours"
    assert rig.control.set(FREQ, 8.0) is None
    rig.calls.drain()
    drifted(rig, 6.0)
    assert rig.looks.changed(), "an edit of another knob stays an edit across a drift"


def test_a_press_holds_the_drift_off_for_a_dwell_and_a_recall_starts_it_again():
    rig = dusk(decoded(DRIFTING))
    drifted(rig, 5.0)
    assert rig.control.colorway("ice") is None
    rig.calls.drain()
    pressed = rig.clock.t
    first = drifted(rig, 10.0)
    assert first and first[0][0] - pressed >= 2.0, "a whole dwell after the press"
    assert rig.looks.recall("dusk", 0.0) is None
    recalled = rig.clock.t
    fresh = drifted(dusk(decoded(DRIFTING)), 10.0)[0][0]
    assert drifted(rig, 10.0)[0][0] - recalled == pytest.approx(fresh, abs=0.1), "a recall draws its first dwell afresh"


def test_the_drift_takes_only_its_names_and_a_switch_stores_it():
    look = decoded({**DRIFTING, "colorway_drift": {"every": 2, "names": ["ice", "dawn"]}})
    rig = dusk(look)
    names = {name for _, name in drifted(rig, 20.0)}
    assert names == {"ice", "dawn"}
    with LoopThread(rig.calls):
        assert rig.control.request({"type": "drift", "name": "dusk", "on": False}) is None
    assert rig.looks.book.looks["dusk"].drift == Drift((2.0, 2.0), ("ice", "dawn"), on=False)
    assert rig.looks.state()["items"][0]["drift"] is False
    assert drifted(rig, 10.0) == [], "off: the colours stay"
    plain = dusk()
    with LoopThread(plain.calls):
        assert plain.control.request({"type": "drift", "name": "dusk", "on": True}) is None
    assert plain.looks.book.looks["dusk"].drift == Drift()
    assert plain.looks.state()["items"][0]["drift"] is True
    single = dusk(replace(decoded(), colorways={"ice": decoded().colorways["ice"]}))
    with LoopThread(single.calls):
        reason = single.control.request({"type": "drift", "name": "dusk", "on": True})
    assert reason is not None and "at least 2 colorways" in reason.reason


def test_a_save_keeps_the_drift_less_the_colorways_gone():
    look = decoded({**DRIFTING, "colorway_drift": {"names": ["ember", "ice", "dawn"]}})
    rig = dusk(look)
    assert rig.looks.save("dusk") is None
    assert rig.looks.book.looks["dusk"].drift == look.drift
    assert rig.looks.save("copy") is None
    assert rig.looks.book.looks["copy"].drift is None, "a new look starts with none"


# ---- the idle cycle's picks -------------------------------------------------------------


def test_the_cycle_s_colorways_key_is_read_written_only_when_on_and_refused_by_its_path():
    book = parse_looks(json.dumps({"version": 4, "looks": {"dusk": DOC}, "cycle": {"colorways": True}}))
    assert book.cycle.colorways and book.to_json()["cycle"]["colorways"] is True
    assert parse_looks(book.to_bytes()) == book
    plain = parse_looks(json.dumps({"version": 4, "looks": {"dusk": DOC}}))
    assert not plain.cycle.colorways and "colorways" not in plain.to_json()["cycle"]
    doc = {"version": 4, "looks": {"dusk": DOC}, "cycle": {"colorways": "yes"}}
    (problem,) = lab.check_look(doc).problems
    assert (problem.path, problem.code) == ("cycle.colorways", Code.WRONG_KIND)


def shuffled(colorways: bool, seconds: float = 90.0, **looks) -> list[tuple[str | None, str | None, bool]]:
    """Each look the idle cycle starts over `seconds`, with the colorway it shows once it has faded in and
    whether it reads changed, on a cycle that starts at once and plays each look 6 s."""
    looks = looks or {name: replace(decoded({**DOC, "colorways": THREE}), cycle=True) for name in ("a", "b", "c")}
    cycle = CycleConfig(idle=1.0, each=6.0, seed=3, window=0, colorways=colorways)
    rig = aura_rig(next(iter(looks.values())), looks=looks, current=next(iter(looks)), cycle=cycle)
    assert restore(rig) is None
    out, seen = [], None
    end = rig.clock.t + seconds
    while rig.clock.t < end:
        rig.frame(rig.clock.advance(6))
        current = rig.looks.book.current
        if current != seen and not rig.fader.fading:
            out.append((current, stack_state(rig)["colorway"], rig.looks.changed()))
            seen = current
    return out


def test_the_cycle_starts_each_look_in_a_seeded_colorway_the_same_way_every_run():
    runs = [shuffled(True) for _ in range(2)]
    assert runs[0] == runs[1], "same seed, same file: the same looks in the same colorways"
    assert len(runs[0]) >= 10
    assert len({colorway for _, colorway, _ in runs[0]}) == 3, "the picks reach every colorway"
    assert not any(changed for _, _, changed in runs[0]), "a pick is the look playing, not an unsaved edit"
    saved = shuffled(False)
    assert {colorway for _, colorway, _ in saved[1:]} == {"ember"}, "off, each look plays as saved"
    assert [name for name, _, _ in saved] == [name for name, _, _ in runs[0]], "the order is the cycle's own"


def test_the_cycle_leaves_a_look_that_drifts_to_its_drift():
    drifting = replace(decoded({**DRIFTING, "colorway_drift": {"every": 600}}), cycle=True)
    looks = {name: drifting for name in ("a", "b")}
    assert {colorway for _, colorway, _ in shuffled(True, 60.0, **looks)} == {"ember"}


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
