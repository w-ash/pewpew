"""The param domain (pewpew.params; ADR-006): each kind's parse and refusal
wording, declaration-time validation, `ParamSet` as the control-surface
contract, and declaration discovery.

What is contractual: declared params materialize to native values before
`setup` runs; the declarations outlive bind, so something can ask a pattern
what params it has; a value naming an undeclared param, of the wrong kind,
or outside a declared range is refused rather than silently becoming a
param that appears to work and provably does nothing.
"""

from __future__ import annotations

import json
import re
import sys
import types
from functools import partial

import numpy as np
import pytest

from fakes import Pooled, run_python
from pewpew.color import EMBER, OCEAN, PRESETS
from pewpew.mapping import line
from pewpew.params import (
    HSV,
    Bool,
    Choice,
    Color,
    Float,
    Gradient,
    Int,
    Palette,
    Param,
    ParamSet,
    Stop,
    declared_params,
)
from pewpew.pattern import Pattern
from pewpew.render import Renderer


class Probe(Pattern):
    speed = Float(0.4, 0.0, 2.0, "/s")
    tail = Float(0.25, 0.01, 2.0, "s")
    count = Int(3, 1, 8)
    mirror = Bool(False)
    mode = Choice("bands", {"bands": "Bands", "dots": "Dots", "solid": "Solid"})
    color = Color((200.0, 1.0, 1.0))

    def render(self, x, y, z, index):
        return np.zeros((index.size, 3), dtype=np.float32)


def check(name: str, value: object) -> str | None:
    return ParamSet(Probe).check(name, value)


# ---- float: the wording is pinned byte for byte ---------------------------


@pytest.mark.parametrize(
    "value, reason",
    [
        (True, "probe.speed takes a number, got the bool True"),
        ("fast", "probe.speed takes a number, got 'fast'"),
        (None, "probe.speed takes a number, got None"),
        (float("nan"), "probe.speed must be a finite number, got nan"),
        (float("inf"), "probe.speed must be a finite number, got inf"),
        (99.0, "probe.speed must be within 0.0..2.0, got 99.0"),
        (-1, "probe.speed must be within 0.0..2.0, got -1.0"),
    ],
)
def test_float_refusal_wording(value, reason) -> None:
    assert check("speed", value) == reason


def test_float_parses_to_a_float() -> None:
    assert ParamSet(Probe).parse("speed", 2) == (2.0, None)
    assert isinstance(ParamSet(Probe).parse("speed", np.float32(1.5))[0], float)


def test_float_noise_at_an_endpoint_snaps_rather_than_refusing() -> None:
    """A slider stepping `lo + i*step` can land an ulp past `hi`; refusing a
    param dragged to its own maximum would be absurd. Only noise moves."""
    params = ParamSet(Probe)
    params.set("speed", 2.0 + 1e-15)
    assert params["speed"] == 2.0
    assert params.check("speed", 2.001) is not None  # a real overshoot still fails


def test_float_endpoints_are_accepted() -> None:
    assert check("speed", 0.0) is None and check("speed", 2.0) is None


def test_step_and_decimals_are_derived() -> None:
    assert Float(0.5, 0.0, 2.0).step == pytest.approx(0.01)
    assert Float(0.5, 0.0, 2.0).decimals == 2
    assert Float(14.0, 1.0, 40.0).step == pytest.approx(0.2)
    assert Float(14.0, 1.0, 40.0).decimals == 1


# ---- int ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, reason",
    [
        (True, "probe.count takes a number, got the bool True"),
        (2.5, "probe.count takes a whole number, got 2.5"),
        (3.0, "probe.count takes a whole number, got 3.0"),
        ("3", "probe.count takes a whole number, got '3'"),
        (9, "probe.count must be within 1..8, got 9"),
    ],
)
def test_int_refusals(value, reason) -> None:
    assert check("count", value) == reason


def test_int_parses_to_an_int() -> None:
    value, reason = ParamSet(Probe).parse("count", np.int64(5))
    assert (value, reason) == (5, None) and type(value) is int


def test_an_int_range_is_whole_numbers() -> None:
    with pytest.raises(TypeError, match="whole numbers"):
        Int(1, 0, 2.5)  # type: ignore[arg-type]


# ---- bool -------------------------------------------------------------------


def test_bool_takes_only_true_or_false() -> None:
    assert check("mirror", True) is None
    assert check("mirror", 1) == "probe.mirror takes true or false, got 1"
    assert check("mirror", "true") == "probe.mirror takes true or false, got 'true'"


# ---- choice -----------------------------------------------------------------


def test_choice_takes_a_key() -> None:
    assert check("mode", "dots") is None
    assert check("mode", "stripes") == "probe.mode takes one of 'bands', 'dots', 'solid', got 'stripes'"


def test_a_choice_index_is_refused() -> None:
    """The value is the key: an index would change meaning when an option is
    added in the middle."""
    assert check("mode", 1) == "probe.mode takes one of 'bands', 'dots', 'solid', got 1"


def test_choice_declaration_is_checked() -> None:
    with pytest.raises(ValueError, match="at least 2 options"):
        Choice("a", ["a"])
    with pytest.raises(ValueError, match="takes one of"):
        Choice("c", ["a", "b"])


# ---- color ------------------------------------------------------------------


def test_color_parses_json_and_native() -> None:
    params = ParamSet(Probe)
    assert params.parse("color", {"h": 10, "s": 0.5, "v": 1}) == (HSV(10.0, 0.5, 1.0), None)
    assert params.parse("color", HSV(10.0, 0.5, 1.0)) == (HSV(10.0, 0.5, 1.0), None)


def test_color_refuses_a_part_by_its_path() -> None:
    assert check("color", {"h": 10, "s": 2.0, "v": 1}) == "probe.color.s must be within 0.0..1.0, got 2.0"
    assert check("color", {"h": 400, "s": 1, "v": 1}) == "probe.color.h must be within 0.0..360.0, got 400.0"
    assert check("color", {"h": 10, "s": True, "v": 1}) == "probe.color.s takes a number, got the bool True"


def test_color_needs_exactly_its_parts() -> None:
    for value in ({"h": 10, "s": 1}, {"h": 10, "s": 1, "v": 1, "a": 1}, [10, 1, 1], 0.5):
        assert check("color", value) == f"probe.color takes a color {{h, s, v}}, got {value!r}"


def test_color_default_is_checked_part_by_part() -> None:
    with pytest.raises(ValueError, match=r"default must be within 0\.0\.\.1\.0, got 1\.5"):
        Color((0.0, 1.5, 1.0))


def test_hsv_turn_is_the_hue_as_a_fraction() -> None:
    assert HSV(90.0, 1.0, 1.0).turn == 0.25


# ---- palette ------------------------------------------------------------------


class Tinted:
    palette = Palette(EMBER, presets=PRESETS)


def stop(at: object, h: object = 0.0, s: object = 1.0, v: object = 1.0) -> dict[str, object]:
    return {"at": at, "h": h, "s": s, "v": v}


RED_TO_BLUE = Gradient((Stop(0.0, HSV(0.0, 1.0, 1.0)), Stop(1.0, HSV(240.0, 1.0, 1.0))))


def test_palette_parses_json_native_and_a_preset_label() -> None:
    params = ParamSet(Tinted)
    assert params.parse("palette", {"stops": [stop(0), stop(1, h=240)]}) == (RED_TO_BLUE, None)
    assert params.parse("palette", RED_TO_BLUE) == (RED_TO_BLUE, None)
    assert params.parse("palette", "ocean") == (OCEAN, None)  # the stops, so a saved look holds them
    labeled = params.parse("palette", {"label": "warm", "stops": [stop(0), stop(1, h=240)]})[0]
    assert labeled is not None and labeled.label == "warm"


# A palette's shape refusal: it names the presets a name may give, and the stops' form.
NAMED = f"a preset name ({', '.join(p.label for p in PRESETS)}) or "
TAKES = f'tint.palette takes {NAMED}{{"stops": [{{"at", "h", "s", "v"}}, ...]}} with an optional "label", got '



def test_a_palette_takes_two_stops_at_one_position_as_a_hard_edge() -> None:
    edge = {"stops": [stop(0), stop(0.5), stop(0.5, h=240), stop(1, h=240)]}
    assert ParamSet(Tinted).check("palette", edge) is None


@pytest.mark.parametrize(
    "value, reason",
    [
        ([1, 2], f"{TAKES}[1, 2]"),
        ({"stops": [stop(0), stop(1)], "name": "x"}, (
            f"{TAKES}{{'stops': [{{'at': 0, 'h': 0.0, 's': 1.0, 'v': 1.0}}, "
            "{'at': 1, 'h': 0.0, 's': 1.0, 'v': 1.0}], 'name': 'x'}"
        )),
        ({"label": 3, "stops": [stop(0), stop(1)]}, "tint.palette.label takes text, got 3"),
        ({"label": "x" * 65, "stops": [stop(0), stop(1)]}, "tint.palette.label takes at most 64 characters, got 65"),
        ({"stops": [stop(0)]}, "tint.palette.stops takes 2 to 16 stops, got 1"),
        ({"stops": [stop(i / 16) for i in range(17)]}, "tint.palette.stops takes 2 to 16 stops, got 17"),
        ({"stops": [stop(0), {"at": 1}]}, "tint.palette.stops[1] takes a stop {at, h, s, v}, got {'at': 1}"),
        ({"stops": [stop(0), stop(1, s=2)]}, "tint.palette.stops[1].s must be within 0.0..1.0, got 2.0"),
        ({"stops": [stop(0), stop(1, h=True)]}, "tint.palette.stops[1].h takes a number, got the bool True"),
        ({"stops": [stop(0), stop(1.5)]}, "tint.palette.stops[1].at must be within 0.0..1.0, got 1.5"),
        ({"stops": [stop(0.1), stop(1)]}, "tint.palette.stops[0].at must be 0.0, where a gradient starts, got 0.1"),
        ({"stops": [stop(0), stop(0.9)]}, "tint.palette.stops[1].at must be 1.0, where a gradient ends, got 0.9"),
        ({"stops": [stop(0), stop(0.6), stop(0.5), stop(1)]},
         "tint.palette.stops[2].at must be at least 0.6, the stop before it, got 0.5"),
        ("embers", "tint.palette: unknown preset 'embers'; presets: " + ", ".join(p.label for p in PRESETS)),
    ],
)
def test_palette_refusal_wording(value, reason) -> None:
    assert ParamSet(Tinted, name="tint").check("palette", value) == reason


TUPLE_STOPS = Gradient((Stop(0.0, (0, 1, 1)), Stop(1.0, (0, 1, 1))))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value, reason",
    [
        (TUPLE_STOPS, "tint.palette.stops[0].color takes an HSV(h, s, v), got (0, 1, 1)"),
        (Gradient((Stop(0.0, HSV(0.0, 1.0, 1.0)), Stop(1.0, HSV(400.0, 1.0, 1.0)))),
         "tint.palette.stops[1].h must be within 0.0..360.0, got 400.0"),  # the JSON form's wording
        (Gradient(5), f"{TAKES}Gradient(stops=5, label='')"),  # type: ignore[arg-type]  # on purpose
        (Gradient((Stop(0.0, HSV(0.0, 1.0, 1.0)), 7)),  # type: ignore[arg-type]  # on purpose
         "tint.palette.stops[1] takes a stop {at, h, s, v}, got 7"),
    ],
)
def test_a_native_palette_is_refused_never_raised(value, reason) -> None:
    """`Stop(at, (h, s, v))` reads like `Color((h, s, v))`, so an author
    writes it; parse refuses it and names the field."""
    assert ParamSet(Tinted, name="tint").check("palette", value) == reason
    declared = reason.replace("tint.palette", "default", 1).replace(NAMED, "")  # a declaration names no presets
    with pytest.raises(ValueError, match=re.escape(f"bad Palette declaration: {declared}")):
        Palette(value)


def test_palette_json_round_trips_and_always_carries_a_label() -> None:
    params = ParamSet(Tinted, {"palette": {"stops": [stop(0), stop(1, h=240)]}})
    assert params.snapshot_json()["palette"] == {
        "label": "", "stops": [{"at": 0.0, "h": 0.0, "s": 1.0, "v": 1.0}, {"at": 1.0, "h": 240.0, "s": 1.0, "v": 1.0}],
    }
    assert json.loads(json.dumps(params.snapshot_json())) == params.snapshot_json()
    assert ParamSet(Tinted, params.snapshot_json()).snapshot() == params.snapshot()
    assert params.set("palette", RED_TO_BLUE) is False  # the same value, however it arrives


def test_palette_record_carries_the_stop_parts_the_cap_and_the_presets() -> None:
    record = ParamSet(Tinted).describe()[0]
    assert set(record) == COMMON | {"stop", "max_stops", "presets"}
    assert list(record["stop"]) == ["at", "h", "s", "v"]
    for part in record["stop"].values():
        assert set(part) == {"label"} | NUMERIC
    color = {r["name"]: r for r in ParamSet(Probe).describe()}["color"]
    assert {k: v for k, v in record["stop"].items() if k != "at"} == color["parts"]  # one color model
    assert record["max_stops"] == Palette.max_stops
    assert [p["label"] for p in record["presets"]] == [p.label for p in PRESETS]
    assert record["presets"][0]["value"] == record["default"]


def test_palette_declaration_is_checked() -> None:
    with pytest.raises(ValueError, match="distinct, non-empty labels"):
        Palette(EMBER, presets=(EMBER, EMBER))
    with pytest.raises(ValueError, match="distinct, non-empty labels"):
        Palette(EMBER, presets=(RED_TO_BLUE,))
    backwards = Gradient((Stop(1.0, HSV(0.0, 1.0, 1.0)), Stop(0.0, HSV(0.0, 1.0, 1.0))), "backwards")
    with pytest.raises(ValueError, match=r"bad Palette declaration: preset 'backwards'.stops\[0\].at must be 0.0"):
        Palette(EMBER, presets=(backwards,))
    with pytest.raises(ValueError, match=r"bad Palette declaration: default.stops\[0\].at must be 0.0"):
        Palette(backwards)
    assert Palette("ember", presets=PRESETS).default == EMBER


# ---- an owner named by a path -------------------------------------------------


def test_a_refusal_names_a_nested_owner_by_its_path() -> None:
    """A node of a layered look is owned by `layers.<layer>.<node>`; the
    path goes before each param name in the existing wording."""
    params = ParamSet(Probe, name="layers.base.fold")
    assert params.owner == "layers.base.fold"
    assert params.check("count", 40) == "layers.base.fold.count must be within 1..8, got 40"
    color = {"h": 10, "s": 2, "v": 1}
    assert params.check("color", color) == "layers.base.fold.color.s must be within 0.0..1.0, got 2.0"
    assert params.check("sides", 5) == (
        "layers.base.fold: unknown param 'sides'; params: speed, tail, count, mirror, mode, color"
    )
    reason = params.check("count", 40)
    assert reason is not None
    assert params.refusal("count", reason).startswith(f"{reason}; edit the 'count' param in ")


def test_a_nested_owner_names_the_set_and_stays_off_the_records() -> None:
    renderer = Renderer(Probe(), line(4), name="layers.base.fold")
    assert renderer.params.owner == "layers.base.fold"
    assert renderer.params.check("count", 40) == "layers.base.fold.count must be within 1..8, got 40"
    assert renderer.params.describe() == ParamSet(Probe).describe()


# ---- declaration-time validation ----------------------------------------------


def test_range_must_be_orderable() -> None:
    """A param that cannot move is dead by construction, so refuse it at import."""
    with pytest.raises(ValueError, match="lo < hi"):
        Float(0.5, 1.0, 1.0)


@pytest.mark.parametrize("reserved", ["n", "seed", "rng", "pixels"])
def test_a_param_cannot_take_a_name_the_engine_reads(reserved) -> None:
    """`pixels = Float(...)` would shadow the frame the engine keeps, and
    the class definition says why instead, also for a param a mixin
    declares."""
    with pytest.raises(ValueError, match=f"Broken.{reserved}: '{reserved}' is reserved for the engine"):
        type("Broken", (Pattern,), {reserved: Float(1.0, 0.0, 2.0)})
    mixin = type("Mixin", (), {reserved: Float(1.0, 0.0, 2.0)})
    with pytest.raises(ValueError, match=f"Broken.{reserved}: '{reserved}' is reserved for the engine"):
        type("Broken", (mixin, Pattern), {})


# The refusal of a class with three reserved names, from a new process at
# each of two hash seeds, run on the suite's process pool (conftest.py).
RESERVED_CODE = (
    "from pewpew.params import Float\n"
    "from pewpew.pattern import Pattern\n"
    "try:\n"
    "    type('P', (Pattern,), {k: Float(1.0, 0.0, 2.0) for k in ('seed', 'rng', 'pixels')})\n"
    "except ValueError as e:\n"
    "    print(str(e).split(':')[0])\n"
)
JOBS = {seed: partial(run_python, RESERVED_CODE, PYTHONHASHSEED=seed) for seed in ("1", "3")}


def test_several_reserved_names_give_one_message_whatever_the_hash_seed(pooled: Pooled) -> None:
    """A set of names iterates in string-hash order, which PYTHONHASHSEED
    changes per process (seeds 1 and 3 differed); the first name sorted is
    the one refused."""
    for seed, out in pooled.items():
        assert out.stdout.strip() == "P.pixels", seed


def test_the_base_is_abstract_and_a_color_takes_an_hsv_default() -> None:
    with pytest.raises(TypeError, match="abstract"):
        Param(0.5)  # type: ignore[abstract]
    assert Color(HSV(30.0, 1.0, 0.5)).default == HSV(30.0, 1.0, 0.5)


def test_default_must_lie_in_its_own_range() -> None:
    with pytest.raises(ValueError, match="bad Float declaration: default must be within"):
        Float(5.0, 0.0, 1.0)


def test_range_must_be_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        Float(0.0, 0.0, float("inf"))


def test_text_names_values_in_range() -> None:
    with pytest.raises(ValueError, match="text must be within"):
        Float(0.0, 0.0, 1.0, text={2.0: "too far"})


def test_an_angle_widget_needs_a_full_turn_that_wraps() -> None:
    with pytest.raises(ValueError, match="0..360"):
        Float(0.0, 0.0, 359.0, "°", periodic=True, widget="angle")
    # Without periodic the page would clamp most of the dial to 0.
    with pytest.raises(ValueError, match="0.0..360.0, not periodic"):
        Float(0.0, 0.0, 360.0, "°", widget="angle")


def test_an_int_too_large_for_a_float_is_refused_not_raised() -> None:
    for huge in (10**400, -(10**5000)):
        assert Int(1, 0, 10).parse("x", huge)[1] == "x must be within 0..10, got a number too large"
    with pytest.raises(ValueError, match="within ±9007199254740991"):
        Int(1, 0, 10**400)


def test_a_whole_number_outside_a_wide_int_range_is_refused_not_snapped() -> None:
    wide = Int(0, -(10**12), 10**12)
    assert wide.parse("x", -(10**12) - 500)[1] == f"x must be within {-(10**12)}..{10**12}, got {-(10**12) - 500}"


def test_a_widget_the_kind_does_not_offer_is_refused() -> None:
    """A typo, or a widget of another kind, must not quietly fall back to
    the default control."""
    with pytest.raises(ValueError, match="Float has no widget 'angel'; its widgets: angle"):
        Float(0.0, 0.0, 360.0, widget="angel")
    with pytest.raises(ValueError, match="Bool has no widget 'dial'; its widgets: none"):
        Bool(False, widget="dial")
    with pytest.raises(ValueError, match="Int has no widget 'angle'"):
        Int(0, 0, 90, widget="angle")


def test_the_label_defaults_to_the_name() -> None:
    assert declared_params(Probe)["speed"].label == "Speed"
    assert Float(0.0, 0.0, 1.0, label="Rate").label == "Rate"


# ---- describe ---------------------------------------------------------------

COMMON = {"name", "kind", "label", "help", "group", "widget", "default"}
NUMERIC = {"unit", "lo", "hi", "step", "decimals", "periodic", "text"}
HINTS = {"sweet", "flash_sensitive"}  # a ranged param's generation hints, on the param, never on a part


def test_describe_key_set_per_kind() -> None:
    records = {r["name"]: r for r in ParamSet(Probe).describe()}
    assert set(records["speed"]) == COMMON | NUMERIC | HINTS
    assert set(records["count"]) == COMMON | NUMERIC | HINTS
    assert set(records["mirror"]) == COMMON
    assert set(records["mode"]) == COMMON | {"options"}
    assert set(records["color"]) == COMMON | {"parts"}
    for part in records["color"]["parts"].values():
        assert set(part) == {"label"} | NUMERIC
    # An unset group or widget is "", and no text is [].
    assert (records["mirror"]["group"], records["mirror"]["widget"], records["speed"]["text"]) == ("", "", [])


def test_describe_is_json_ready_in_declaration_order() -> None:
    """A list, not a dict, so display order survives transport."""
    records = ParamSet(Probe).describe()
    assert [r["name"] for r in records] == ["speed", "tail", "count", "mirror", "mode", "color"]
    assert json.loads(json.dumps(records)) == records
    assert records[-1]["default"] == {"h": 200.0, "s": 1.0, "v": 1.0}
    assert records[4]["options"][1] == {"value": "dots", "label": "Dots"}


def test_text_goes_on_the_wire_as_value_label_pairs() -> None:
    class Held(Probe):
        cycle = Float(0.0, 0.0, 60.0, "s", text={0: "hold"})

    record = ParamSet(Held).describe()[-1]
    assert record["text"] == [{"value": 0.0, "label": "hold"}]


def test_a_pattern_with_no_params_describes_as_empty() -> None:
    class Bare(Pattern):
        def render(self, x, y, z, index):
            return np.zeros((index.size, 3), dtype=np.float32)

    assert ParamSet(Bare).describe() == []
    assert Renderer(Bare(), line(4)).params.snapshot() == {}


# ---- the set as a control-surface contract ---------------------------------


def test_check_is_parse_and_never_raises() -> None:
    """`parse` exists because an exception from a `pewpew.pace.Calls.call_soon`
    closure propagates out of `run()` — a raising setter reached over a
    socket is a way to stop the run from a browser."""
    params = ParamSet(Probe)
    assert params.check("speed", 1.0) is None
    reason = params.check("speed", 99.0)
    assert reason is not None and params.parse("speed", 99.0) == (None, reason)
    with pytest.raises(ValueError, match=re.escape(reason)):
        params.set("speed", 99.0)


def test_undeclared_name_is_refused_with_the_declared_names() -> None:
    assert check("sped", 1.0) == (
        "probe: unknown param 'sped'; params: speed, tail, count, mirror, mode, color"
    )
    with pytest.raises(ValueError, match="unknown param 'sped'"):
        Renderer(Probe(), line(4), params={"sped": 1.5})


def test_refusal_points_at_the_declaration_only_through_hint() -> None:
    """`parse` is what a network peer sees; `hint` is what the CLI adds, so
    a refusal never serves the layout of the disk."""
    params = ParamSet(Probe)
    assert "test_params.py" in params.hint("speed")
    assert "test_params.py" not in (params.check("speed", 99.0) or "")
    assert params.hint("nope") == ""


def test_set_reports_whether_the_value_changed() -> None:
    params = ParamSet(Probe)
    assert params.set("color", {"h": 1, "s": 1, "v": 1}) is True
    assert params.set("color", HSV(1.0, 1.0, 1.0)) is False  # pointer jitter re-sends constantly


def test_set_many_is_all_or_nothing() -> None:
    params = ParamSet(Probe)
    before = params.snapshot()
    with pytest.raises(ValueError):
        params.set_many({"speed": 1.0, "mode": "nope"})
    assert params.snapshot() == before
    assert sorted(params.set_many({"speed": 1.0, "mirror": True})) == ["mirror", "speed"]


def test_snapshot_is_native_and_snapshot_json_is_json() -> None:
    params = ParamSet(Probe, {"color": {"h": 30, "s": 0.5, "v": 1}})
    assert params.snapshot()["color"] == HSV(30.0, 0.5, 1.0)
    assert params.snapshot_json()["color"] == {"h": 30.0, "s": 0.5, "v": 1.0}
    assert json.loads(json.dumps(params.snapshot_json())) == params.snapshot_json()


def test_both_snapshots_round_trip_through_overrides() -> None:
    original = ParamSet(Probe, {"speed": 1.25, "mode": "dots", "color": {"h": 5, "s": 1, "v": 0.5}})
    assert ParamSet(Probe, original.snapshot()).snapshot() == original.snapshot()
    assert ParamSet(Probe, original.snapshot_json()).snapshot() == original.snapshot()


# ---- binding and discovery --------------------------------------------------


def test_params_materialize_to_native_values_before_setup() -> None:
    seen: dict[str, object] = {}

    class Seen(Probe):
        def setup(self, n, x, y, z, index):
            seen.update(speed=self.speed, color=self.color, mode=self.mode)

    Renderer(Seen(), line(4))
    assert seen == {"speed": 0.4, "color": HSV(200.0, 1.0, 1.0), "mode": "bands"}


def test_an_unbound_instance_reads_the_defaults() -> None:
    assert Probe().speed == 0.4 and Probe().color == HSV(200.0, 1.0, 1.0)
    assert isinstance(Probe.speed, Param)


def test_override_drives_a_declared_param() -> None:
    renderer = Renderer(Probe(), line(4), params={"speed": 1.5, "color": {"h": 0, "s": 0, "v": 1}})
    assert renderer.pattern.speed == 1.5 and renderer.pattern.color == HSV(0.0, 0.0, 1.0)
    assert renderer.pattern.tail == 0.25  # untouched declarations keep defaults


def test_params_and_the_set_itself_survive_rebind() -> None:
    """A control surface holds the set across rebinds, so replacing it
    would leave that surface driving a set nothing reads."""
    renderer = Renderer(Probe(), line(4), params={"speed": 1.5})
    before = renderer.params
    renderer.rebind(line(9))
    assert renderer.pattern.speed == 1.5 and renderer.params is before
    assert renderer.n == 9


def test_declarations_survive_bind() -> None:
    renderer = Renderer(Probe(), line(4))
    speed = renderer.params.declarations["speed"]
    assert isinstance(speed, Float) and (speed.lo, speed.hi, speed.unit) == (0.0, 2.0, "/s")
    assert renderer.pattern.speed == 0.4


def test_most_derived_declaration_wins() -> None:
    class Faster(Probe):
        speed = Float(1.9, 0.0, 3.0)

    assert declared_params(Faster)["speed"].default == 1.9
    assert Renderer(Faster(), line(4)).pattern.speed == 1.9


def test_declaration_order_is_base_first() -> None:
    """A subclass appends to a stable prefix rather than reshuffling the row
    above it — that order is a control surface's layout order."""

    class Extra(Probe):
        wobble = Float(0.1, 0.0, 1.0)

    assert list(declared_params(Extra))[-2:] == ["color", "wobble"]


def test_declaration_beats_an_init_assignment() -> None:
    """The set owns the value, so a UI cannot be shown a value the pattern
    ignores."""

    class Stubborn(Probe):
        def __init__(self):
            self.speed = 1.75  # type: ignore[assignment]

    assert Renderer(Stubborn(), line(4)).pattern.speed == 0.4


def test_a_set_on_the_renderers_params_reaches_the_running_pattern() -> None:
    """One write path: the set and the pattern never disagree, and a set
    that no pattern was bound to only holds values."""
    renderer = Renderer(Probe(), line(4))
    assert renderer.params.set("mode", "solid") is True
    assert renderer.pattern.mode == "solid"
    assert renderer.params["mode"] == "solid"
    unbound = ParamSet(Probe)
    unbound.set("speed", 1.5)
    assert unbound["speed"] == 1.5


def test_a_refusal_for_a_class_with_no_source_file_is_still_a_refusal(monkeypatch) -> None:
    """A class built in a REPL or `python -c` has no source file, and
    `inspect` raises OSError for it; the refusal is still a ValueError."""
    monkeypatch.setitem(sys.modules, "__main__", types.ModuleType("__main__"))  # no __file__

    class Spark(Pattern):
        speed = Float(0.5, 0.0, 1.0)

    Spark.__module__ = "__main__"
    with pytest.raises(ValueError, match="speed must be within 0.0..1.0, got 3.0. edit the 'speed' param in Spark"):
        ParamSet(Spark, {"speed": 3})

