"""Looks made from a seed, and looks made like a look (pewpew.fx.surprise,
pewpew.lab.variations, pewpew.aura.variety).

What takes renders runs once, as this file's `JOBS` on the suite's
process pool, each worker under the suite's rules (a warning is an
error, every node's output is checked; conftest.py): looks made on a
strip, a panel, a volume and a room, one of them again in a new process
that hashes strings another way; a look made like an example look,
holding a layer; a set of variations; and the aura's own making. Each
made look passes `verify looks` on its map (it checks, nothing raises, it
flashes at most 3 times a second, it is not black, every knob is live),
uses only ops its map's dimensions take, and stays within its cost
budget. The rest is drawn, never rendered."""

from __future__ import annotations

import hashlib
import json
import tempfile
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from fakes import EXAMPLE_ROOM, FLOW_LOOK, aura_rig, filed, in_new_process, solid
from pewpew import lab
from pewpew.aura.variety import in_background
from pewpew.color import PRESETS
from pewpew.compose import Look
from pewpew.fx import surprise
from pewpew.fx.codec import decode_look, encode_look
from pewpew.fx.ops import OPS
from pewpew.lab.check import ready
from pewpew.lab.geometry import parse_geometry
from pewpew.lab.handles import Cache
from pewpew.lab.rendering import play
from pewpew.mapping import dimensions, line, parse_map
from pewpew.metrics import Metrics
from pewpew.params import Palette, ParamSet
from pewpew.problems import Code, Refused

EXAMPLES = Path(__file__).parent.parent / "examples"
# A seed for each map. Any seed passes; these make their looks in few
# tries, which keeps the suite fast.
MAPS = {"line:32": 2, "grid:8x8": 3, "lattice:4": 4}
SMALL_BUDGET = 60.0


def _verified(look: Look, spec: str) -> tuple[bool, list[str]]:
    """`verify looks` of `look` alone on map `spec`, over 2 s."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "made.look.json"
        path.write_text(filed(encode_look(look)))
        verdict = lab.verify_looks([path], map_spec=spec, seconds=2.0)
    return verdict.ok, [reason for f in verdict.files for v in f.looks for reason in v.failures]


def _frames(look: Look, spec: str) -> str:
    """SHA-256 of 30 frames of `look` on `spec`."""
    frames, _ = play(ready(look), parse_geometry(spec), 30, 30.0, 0)
    return hashlib.sha256(frames.tobytes()).hexdigest()


def _made(spec: str, seed: int, budget: float = surprise.BUDGET_US) -> dict[str, Any]:
    """A look made from `seed` for map `spec`, and what the tests check of it."""
    mapping = parse_map(spec)
    look = surprise.generate(seed, mapping, budget=budget)
    ok, failures = _verified(look, spec)
    return {"look": json.dumps(encode_look(look)), "frames": _frames(look, spec), "ok": ok, "failures": failures,
            "cost": surprise.look_cost(look, len(mapping)), "dims": dimensions(mapping),
            "hashing": hash(spec)}  # how this process hashes a string, which PYTHONHASHSEED sets


def _made_for_the_room(seed: int) -> dict[str, Any]:
    """A look made for the example room, rendered there for a second."""
    geometry = parse_geometry(str(EXAMPLE_ROOM))
    look = surprise.generate(seed, geometry.mapping)
    with tempfile.TemporaryDirectory() as folder:
        rendered = lab.render(look, str(EXAMPLE_ROOM), 1.0, 30.0, cache=Cache(Path(folder)))
    return {"look": json.dumps(encode_look(look)), "warnings": rendered.warnings, "dims": geometry.dims,
            "checks": lab.check_look(look).ok}


def _mutated(name: str, spec: str, seed: int, keep: tuple[str, ...]) -> dict[str, Any]:
    """Example look `name` made more like itself from `seed` on map `spec`, holding `keep`."""
    look = ready(EXAMPLES / f"{name}.look.json").look
    made = surprise.mutate(look, seed, parse_map(spec), strength=0.8, keep=keep)
    ok, failures = _verified(made, spec)
    return {"before": encode_look(look), "after": encode_look(made), "ok": ok, "failures": failures}


def _varied() -> dict[str, Any]:
    """Two looks `vary` made from nothing on a strip, and their sheet."""
    with tempfile.TemporaryDirectory() as folder:
        cache = Cache(Path(folder))
        made = lab.vary(None, seed=4, n=2, map_spec="line:32", seconds=1.0, cache=cache)
        drawn = lab.rows([c.handle for c in made.candidates], cache=cache)
    return {"result": made.to_json(), "sheet": (drawn.width, drawn.height, drawn.legend)}


def _shown() -> dict[str, Any]:
    """An aura on a strip makes a surprise and a variation of it, plays each
    unsaved, then keeps the variation (pewpew.aura.variety)."""
    with tempfile.TemporaryDirectory() as folder:
        rig = aura_rig(FLOW_LOOK, mapping=line(24), looks={}, path=Path(folder) / "looks.json")
        made = rig.variety.surprise(8)
        played = rig.looks.play(made)
        rig.frame(rig.clock.advance())
        unsaved = dict(rig.looks.book.looks), rig.looks.book.current
        varied = rig.variety.vary(0.5, 4)
        again = rig.looks.play(varied)
        rig.frame(rig.clock.advance())
        kept = rig.looks.save()
        return {"played": (made.label, played, again, varied.label), "unsaved": unsaved, "kept": kept,
                "after": (list(rig.looks.book.looks), rig.looks.book.current),
                "changed": encode_look(made.look) != encode_look(varied.look)}


# Every job above, by name.
JOBS = {
    **{f"made {spec}": partial(_made, spec, seed) for spec, seed in MAPS.items()},
    # A new process, whose strings hash another way than the pool's even
    # where PYTHONHASHSEED fixes the suite's.
    "made grid:8x8 again": partial(in_new_process, partial(_made, "grid:8x8", MAPS["grid:8x8"]),
                                   PYTHONHASHSEED="random"),
    "made line:32 again": partial(_made, "line:32", 6),
    "made small": partial(_made, "line:32", 2, SMALL_BUDGET),
    "room": partial(_made_for_the_room, 4),
    "mutated": partial(_mutated, "copper-tide", "line:64", 4, ("layers.counter",)),
    "varied": _varied,
    "shown": _shown,
}


# ---- made looks ----------------------------------------------------------------------


@pytest.mark.parametrize("spec", [*MAPS, "line:32 again", "small"])
def test_a_made_look_passes_the_content_gate_within_its_budget(pooled, spec):
    made = pooled[f"made {spec}"]
    assert made["ok"], made["failures"]
    look, problems = decode_look(json.loads(made["look"]))
    assert look is not None and not problems
    budget = SMALL_BUDGET if spec == "small" else surprise.BUDGET_US
    assert made["cost"] <= budget
    assert all(made["dims"] in OPS[node.op].dims for item in look.layers for node in item.program.graph)


def test_the_same_seed_makes_the_same_look_and_frames_in_another_process(pooled):
    once, again = pooled["made grid:8x8"], pooled["made grid:8x8 again"]
    assert once["hashing"] != again["hashing"]  # another process, whose strings hash another way
    assert once["look"] == again["look"] and once["frames"] == again["frames"]
    assert pooled["made line:32"]["look"] != pooled["made line:32 again"]["look"]


def test_a_look_made_for_a_room_runs_there_on_ops_its_dimensions_take(pooled):
    room = pooled["room"]
    look, _ = decode_look(json.loads(room["look"]))
    assert look is not None and room["checks"] and room["warnings"] == ()
    assert all(room["dims"] in OPS[node.op].dims for item in look.layers for node in item.program.graph)


def test_a_mutated_look_passes_the_gate_and_holds_what_it_keeps(pooled):
    mutated = pooled["mutated"]
    assert mutated["ok"], mutated["failures"]
    before, after = mutated["before"], mutated["after"]
    assert before != after
    assert [lay for lay in after["layers"] if lay["id"] == "counter"] == [
        lay for lay in before["layers"] if lay["id"] == "counter"]
    assert not any(route["path"].startswith("layers.counter.") for route in after.get("routes", ())
                   if route not in before.get("routes", ()))


def test_vary_makes_n_candidates_each_rendered_and_numbered_in_one_sheet(pooled):
    result = pooled["varied"]["result"]
    assert result["seed"] == 4 and result["strength"] is None and len(result["candidates"]) == 2
    seeds = [c["seed"] for c in result["candidates"]]
    assert seeds == [surprise.sub_seed(4, i) for i in range(2)]
    assert all(c["metrics"]["flash_rate_max"] <= 3 and c["warnings"] == [] for c in result["candidates"])
    width, height, legend = pooled["varied"]["sheet"]
    assert legend.startswith("Rows 1 to 2 are renders at the same times") and width <= 1568 and height <= 1568


def test_the_aura_plays_a_made_look_unsaved_and_keeps_it_under_its_own_name(pooled):
    shown = pooled["shown"]
    label, played, again, varied = shown["played"]
    assert (label, played, again, varied) == ("surprise 1", None, None, "variation 1")  # counted, not the seed
    assert shown["unsaved"] == ({}, None) and shown["changed"]
    assert shown["kept"] is None and shown["after"] == (["variation 1"], "variation 1")


# ---- the grammar, drawn and not rendered ------------------------------------------------


def _space(spec: str) -> surprise.Space:
    return surprise.Space.of(parse_map(spec), surprise.BUDGET_US)


def test_every_knob_drawn_is_one_its_param_takes_and_within_its_sweet_range():
    for _, cls in sorted(OPS.items()):
        params = ParamSet(cls)
        for record in surprise.records(cls):
            for k in range(40):
                drawn = surprise.value(surprise.Draw("test", k, 0), record)
                assert params.check(record["name"], drawn) is None, (cls.op, record["name"], drawn)
                if record["kind"] in ("float", "int"):
                    lo, hi = record["sweet"]
                    assert lo <= drawn <= hi, (cls.op, record["name"], drawn)


def test_a_speed_stays_near_its_default_and_a_flash_sensitive_one_slow():
    noise = surprise.record_of(OPS["noise"], "speed")
    speeds = [surprise.number(surprise.Draw("test", k, 0), noise) for k in range(200)]
    assert all(0.1 / surprise.STEADY - 1e-3 <= v <= 0.1 * surprise.STEADY + 1e-3 for v in speeds)
    spin = surprise.record_of(OPS["rotate"], "speed")  # default 0: the slow share of its range
    spins = [surprise.number(surprise.Draw("test", k, 0), spin) for k in range(200)]
    assert max(abs(v) for v in spins) <= surprise.SLOW * 90 and min(spins) < 0 < max(spins)


def test_a_choice_never_names_an_axis_the_map_does_not_span():
    axis = surprise.record_of(OPS["osc"], "axis")
    plane = surprise.record_of(OPS["kaleid"], "plane")
    strip, panel = _space("line:16"), _space("grid:4x4")
    assert surprise.choices(axis, strip.axes) == ["u", "x"]
    assert surprise.choices(plane, panel.axes) == ["auto", "xy"]
    assert surprise.choices(plane, _space("lattice:3").axes) == ["auto", "xy", "xz", "yz"]


def test_the_ops_of_each_role_run_on_the_map_and_a_warp_along_an_axis_runs_on_every_map():
    for spec in ("line:16", "grid:4x4", "lattice:3"):
        space = _space(spec)
        for role in ("field", "sim", "warp", "tone", "state"):
            assert all(space.dims in cls.dims for cls in surprise.ops(space, role))
    warps = {spec: {cls.op for cls in surprise.ops(_space(spec), "warp")} for spec in ("line:16", "grid:4x4")}
    assert warps["line:16"] == {"mirror", "modulate", "repeat", "scale"}
    assert {"kaleid", "mirror", "polar", "repeat", "rotate", "scale", "tunnel"} <= warps["grid:4x4"]


def test_a_candidate_is_drawn_the_same_from_the_same_seed():
    space = _space("grid:6x6")
    drawn = [encode_look(surprise._drawn(surprise.Draw("surprise", 9, k), space, False)) for k in (0, 0, 1)]
    assert drawn[0] == drawn[1] != drawn[2]


def test_a_looped_palette_meets_its_ends_and_parses():
    for preset in PRESETS:
        looped = surprise.looped(preset)
        assert looped.stops[0].color == looped.stops[-1].color and looped.stops[-1].at == 1.0
        assert Palette(preset).parse("palette", looped)[1] is None


def test_a_nudge_stays_in_its_range_and_wraps_a_periodic_knob():
    shift = surprise.record_of(OPS["palette"], "shift")
    scale = surprise.record_of(OPS["noise"], "scale")
    for k in range(100):
        draw = surprise.Draw("nudge", k, 0)
        assert 0.0 <= surprise.nudge(draw, shift, 359.0, 1.0) < 360.0
        assert scale["lo"] <= surprise.nudge(draw, scale, 30.0, 1.0) <= 30.0  # set outside its sweet range


def test_the_taste_gates_name_a_dull_look():
    base = {f: 0.0 for f in Metrics.__dataclass_fields__} | {"frames": 30, "pixels": 4, "seconds": 1.0}
    lively = Metrics(**{**base, "mean_luma": 0.2, "p95_luma": 0.6, "motion_energy": 0.1, "hue_clusters": 2})
    assert surprise.taste(lively, lively, colour=True) == ()
    dull = Metrics(**{**base, "black_fraction": 0.97, "p95_luma": 0.02, "hue_clusters": 0})
    assert surprise.taste(dull, dull, colour=True) == ("too dark", "dies out", "frozen", "grey")
    assert "grey" not in surprise.taste(dull, dull, colour=False)


def test_a_bad_seed_or_a_budget_no_look_fits_is_refused():
    with pytest.raises(ValueError, match="a seed is a whole number"):
        surprise.generate(-1, parse_map("line:8"))
    with pytest.raises(ValueError, match="no look fits a budget of 1 µs"):
        surprise.generate(0, parse_map("line:8"), budget=1.0)


def test_nothing_that_passes_is_no_look_whether_made_or_changed(monkeypatch):
    monkeypatch.setattr(surprise, "judge", lambda candidate, space: surprise.Verdict(("flashes",)))
    with pytest.raises(surprise.NoLook, match="try another seed"):
        surprise.generate(0, parse_map("line:8"))
    look = ready(EXAMPLES / "mcp-tide.look.json").look
    with pytest.raises(surprise.NoLook, match="no change of the look made from seed 1 passed the content gate"):
        surprise.mutate(look, 1, parse_map("line:8"))


def test_an_op_defined_outside_the_engine_never_joins_the_grammar():
    """The same seed makes the same look in every process, whatever ops
    other code defined (module docstring)."""
    from pewpew.fx.op import REGISTRY, Op
    from pewpew.fx.types import Sig, Ty

    class Fog(Op, op="fog_test"):
        """A field code outside the engine might define."""

        sig = Sig.SOURCE
        out = Ty.SCALAR

    surprise._roles.cache_clear()
    try:
        assert surprise.role(Fog) == "field" and Fog not in surprise._roles()["field"]
    finally:
        REGISTRY.pop("fog_test")
        surprise._roles.cache_clear()


def test_keep_names_what_is_there():
    look = ready(EXAMPLES / "mcp-tide.look.json").look
    with pytest.raises(Refused) as caught:
        surprise.mutate(look, 0, parse_map("line:8"), keep=["layers.base", "layers.base.swel"])
    (problem,) = caught.value.problems
    assert (problem.path, problem.code, problem.did_you_mean) == ("keep[1]", Code.BAD_REF, "layers.base.swell")
    assert problem.reason.startswith("keep[1]: unknown address 'layers.base.swel' (did you mean 'layers.base.swell'?)")
    assert problem.fix == "set keep[1] to 'layers.base.swell'"
    assert surprise.Held.of(["layers.base.swell"], ready(look)).holds("layers.base.swell.freq")


def test_vary_holding_the_whole_look_makes_nothing_and_says_so(tmp_path):
    look = ready(EXAMPLES / "mcp-tide.look.json").look
    with pytest.raises(surprise.NoLook, match="keep less"):
        lab.vary(look, 3, 2, keep=["layers.base"], map_spec="line:32", cache=Cache(tmp_path))


def test_a_candidate_carries_the_taste_gates_its_render_fails(monkeypatch, tmp_path, fake_ops):
    """Taste is a preference: a made look that fails a gate is still given,
    and says which (pewpew.lab.variations)."""
    white = solid(1.0, 1.0, 1.0)
    monkeypatch.setattr(surprise, "generate", lambda seed, mapping, **kw: white)
    (made,) = lab.vary(None, 0, 1, map_spec="line:32", seconds=1.0, cache=Cache(tmp_path)).candidates
    assert made.metrics.mean_luma > surprise.WASHED and "washed out" in made.taste
    assert made.to_json()["taste"] == list(made.taste)


@pytest.mark.parametrize("strength", [0, 0.0, -1, 5.0, float("nan"), True, "0.5"])
def test_a_strength_not_above_0_and_at_most_1_is_refused_never_clamped(strength):
    look = ready(EXAMPLES / "mcp-tide.look.json").look
    words = r"a strength is a number above 0 and at most 1 \(at 0 a look does not change\), got "
    with pytest.raises(ValueError, match=words):
        surprise.mutate(look, 0, parse_map("line:8"), strength=strength)
    with pytest.raises(ValueError, match=words):
        lab.vary(look, 0, 1, strength=strength, map_spec="line:8")
    assert surprise.check_strength(strength) is not None and surprise.check_strength(1) is None


def test_a_map_whose_points_sit_at_one_place_is_refused_saying_why():
    for mapping in (np.zeros((1, 3), np.float32), np.ones((5, 3), np.float32)):
        with pytest.raises(ValueError, match=r"point\(s\) sit at one place: every op runs along an axis") as err:
            surprise.generate(0, mapping)
        assert not isinstance(err.value, surprise.NoLook)
        with pytest.raises(ValueError, match="sit at one place"):
            surprise.mutate(ready(EXAMPLES / "mcp-tide.look.json").look, 0, mapping)


@pytest.mark.parametrize("spec", ["line:32", "grid:16x16"])
def test_a_drawn_look_never_costs_more_than_its_budget(spec):
    mapping = parse_map(spec)
    for budget in (30.0, 60.0, 120.0):
        space = surprise.Space.of(mapping, budget)
        for seed in range(60):
            try:
                drawn = surprise._drawn(surprise.Draw("surprise", seed, 0), space, seed % 2 == 0)
            except ValueError:  # not even one layer fits
                continue
            assert surprise.look_cost(drawn, space.points) <= budget, (budget, seed)


def test_a_change_never_takes_a_look_past_its_budget():
    mapping = parse_map("grid:16x16")
    for name in ("copper-tide", "turing-garden", "mcp-tide"):
        staged = ready(EXAMPLES / f"{name}.look.json")
        budget = surprise.look_cost(staged.look, len(mapping))  # no room for one node more
        space = surprise.Space.of(mapping, budget)
        for seed in range(60):
            changed = surprise._mutated(surprise.Draw("mutate", seed, 0), staged, space, 1.0, surprise.Held(), True)
            assert surprise.look_cost(changed, space.points) <= budget, (name, seed)


def _changed(staged, spec: str, keep: list[str], seeds: int = 40) -> list[Look]:
    """Candidates like `staged`'s look at strength 1 on map `spec`, holding `keep`, drawn and not judged."""
    space, held = _space(spec), surprise.Held.of(keep, staged)
    return [surprise._mutated(surprise.Draw("mutate", seed, 0), staged, space, 1.0, held, False)
            for seed in range(seeds)]


def test_a_change_draws_a_choice_again_only_among_those_the_map_spans():
    staged = ready(EXAMPLES / "copper-tide.look.json")  # its mirror and its two oscs run along u
    space = _space("line:32")
    axes = set()
    for made in _changed(staged, "line:32", [], 60):
        for item in made.layers:
            for node in item.program.graph:
                for record in surprise.records(OPS[node.op]):
                    if record["kind"] == "choice" and record["name"] in node.args:
                        assert node.args[record["name"]] in surprise.choices(record, space.axes), (item.id, node.id)
                        axes.add(node.args[record["name"]])
    assert {"x", "u"} <= axes  # drawn again, within the strip's own


def test_a_held_layer_node_or_signal_holds_the_look_s_seed_and_a_held_knob_does_not():
    staged = ready(EXAMPLES / "mcp-tide.look.json")
    seed = staged.look.seed
    for keep in (["layers.base"], ["layers.base.chop"]):
        assert {made.seed for made in _changed(staged, "line:32", keep)} == {seed}
    assert {made.seed for made in _changed(staged, "line:32", ["layers.base.chop.scale"])} - {seed}
    # The look's one layer held: nothing is left to change, so nothing is made.
    with pytest.raises(surprise.NoLook, match="keep less"):
        surprise.mutate(staged.look, 3, parse_map("line:32"), strength=1.0, keep=["layers.base"])


def test_a_held_signal_keeps_its_routes_whatever_is_swapped():
    for name, signal in (("turing-garden", "grow"), ("warp-lane", "hue"), ("ember-fountain", "gust")):
        staged = ready(EXAMPLES / f"{name}.look.json")
        routes = {route for route in staged.look.routes if route.source == signal}
        assert routes
        for made in _changed(staged, "grid:16x16", [f"signals.{signal}"], 60):
            assert signal in {node.id for node in made.signals or ()} and routes <= set(made.routes), name


def test_with_audio_a_route_may_follow_a_sound_band_and_without_it_never_does_each_by_its_plain_name():
    space = _space("grid:6x6")
    nodes = {audio: [node for seed in range(40) for node in
                     surprise._drawn(surprise.Draw("surprise", seed, 0), space, audio).signals or ()]
             for audio in (False, True)}
    signals = {audio: {node.op for node in made} for audio, made in nodes.items()}
    assert "band" in signals[True] and "band" not in signals[False]
    assert signals[False] <= {"lfo", "walk"}
    assert all(node.id.startswith(surprise.SIGNAL_NAMES[node.op]) for node in nodes[True])


def test_the_aura_refuses_a_variation_that_changes_nothing(monkeypatch, tmp_path):
    rig = aura_rig(FLOW_LOOK, mapping=line(24), looks={}, path=tmp_path / "looks.json")
    rig.looks.play(rig.variety.surprise(8))
    rig.frame(rig.clock.advance())
    monkeypatch.setattr(surprise, "judge", lambda candidate, space: surprise.Verdict(("flashes",)))
    with pytest.raises(ValueError, match="no change of the look made from seed 3"):
        rig.variety.vary(0.5, 3)


def test_in_background_hands_back_the_result_or_the_error():
    assert in_background(lambda: 7).result(timeout=5.0) == 7
    with pytest.raises(ZeroDivisionError):
        in_background(lambda: 1 / 0).result(timeout=5.0)
