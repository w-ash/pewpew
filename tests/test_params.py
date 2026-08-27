"""Typed-param declaration, validation, and control-surface semantics
(architecture §5 / ADR-006, amended 2026-08-22).

What is contractual: declared `Param`s materialize to plain floats before
`setup` runs; the declarations themselves outlive bind, so something can ask a
pattern what knobs it has; an override naming an undeclared knob, or landing
outside a declared range, is refused rather than silently becoming a knob that
appears to work and provably does nothing.

ADR-006's canonical state tree — paths, partial-merge mutation, presets — is
Phase 3 and is deliberately not modelled here.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pytest

from pewpew import Param, ParamSet, Pattern, Renderer, declared_params, line


class Knobs(Pattern):
    name = "knobs"
    speed = Param(0.4, 0.0, 2.0, "Rev/s")
    tail = Param(0.25, 0.01, 2.0, "Tail seconds")

    def render(self, x, y, z, index):
        return np.zeros((index.size, 3), dtype=np.float32)


def test_params_materialize_to_floats_before_setup() -> None:
    seen: dict[str, object] = {}

    class Probe(Knobs):
        def setup(self, n, x, y, z, index):
            seen["speed"] = self.speed

    Renderer(Probe(), line(4))
    # setup must see a number, not the Param declaration object.
    assert seen["speed"] == 0.4
    assert isinstance(seen["speed"], float)


def test_override_drives_a_declared_param() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 1.5})
    assert renderer.pattern.speed == 1.5
    assert renderer.pattern.tail == 0.25  # untouched declarations keep defaults


def test_override_coerces_to_float() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 2})
    assert isinstance(renderer.pattern.speed, float)


def test_undeclared_override_is_refused() -> None:
    """A dead knob must not be creatable.

    The sdf3d `spin` addendum in bench/results/authoring-2026-07-16.md is the
    motivating evidence: a parameter that appears to work and provably does
    nothing, which neither the authoring surface nor golden frames caught. An
    override landing on an undeclared name is the same failure one step
    earlier, and here it is cheap to refuse outright.
    """
    with pytest.raises(ValueError, match="no Param named 'sped'"):
        Renderer(Knobs(), line(4), params={"sped": 1.5})


def test_refusal_names_the_declared_params() -> None:
    with pytest.raises(ValueError, match="speed, tail"):
        Renderer(Knobs(), line(4), params={"nope": 1.0})


def test_params_survive_rebind() -> None:
    renderer = Renderer(Knobs(), line(4), params={"speed": 1.5})
    renderer.rebind(line(9))
    assert renderer.pattern.speed == 1.5
    assert renderer.n == 9


# ---- declaration-time validation -------------------------------------------


def test_range_must_be_orderable() -> None:
    """A knob that cannot move is dead by construction, so refuse it at import."""
    with pytest.raises(ValueError, match="lo < hi"):
        Param(0.5, 1.0, 1.0)


def test_default_must_lie_in_its_own_range() -> None:
    with pytest.raises(ValueError, match="outside its own range"):
        Param(5.0, 0.0, 1.0)


def test_range_must_be_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        Param(0.0, 0.0, float("inf"))


def test_step_and_decimals_are_derived() -> None:
    """Derived, so ADR-006's one-line declaration stays intact and every
    control surface quantizes a knob the same way."""
    assert Param(0.5, 0.0, 2.0).step == pytest.approx(0.01)
    assert Param(0.5, 0.0, 2.0).decimals == 2
    assert Param(14.0, 1.0, 40.0).step == pytest.approx(0.2)
    assert Param(14.0, 1.0, 40.0).decimals == 1


# ---- range enforcement ------------------------------------------------------


def test_out_of_range_override_is_refused() -> None:
    """The declared range is a contract, not decoration (ADR-006 amendment).

    Refusing rather than clamping is what lets a control surface trust that a
    knob's endpoints bound every value the engine renders: a clamp would run
    `hi` while the caller believed it had set something else.
    """
    with pytest.raises(ValueError, match=r"within 0\.0\.\.2\.0"):
        Renderer(Knobs(), line(4), params={"speed": 1e9})


def test_refusal_points_at_the_declaration() -> None:
    knobs = ParamSet(Knobs)
    assert knobs.hint("speed").endswith("or pick a value in range")
    assert "test_params.py" in knobs.hint("speed")
    # An undeclared name has no declaration to point at, and `check` already
    # lists what does exist.
    assert knobs.hint("nope") == ""


def test_check_carries_no_file_path() -> None:
    """`check` is what a network peer sees; `hint` is what the CLI adds.

    They stay separate so a refusal can be sent to whoever can reach the
    preview port without handing them the layout of the disk.
    """
    reason = ParamSet(Knobs).check("speed", 99.0)
    assert reason is not None and "test_params.py" not in reason


def test_endpoints_are_accepted() -> None:
    assert Renderer(Knobs(), line(4), params={"speed": 2.0}).pattern.speed == 2.0
    assert Renderer(Knobs(), line(4), params={"speed": 0.0}).pattern.speed == 0.0


def test_float_noise_at_an_endpoint_snaps_rather_than_refusing() -> None:
    """A slider stepping `lo + i*step` can land an ulp past `hi`; refusing a
    knob dragged to its own maximum would be absurd. Only noise moves."""
    knobs = ParamSet(Knobs)
    knobs.set("speed", 2.0 + 1e-15)
    assert knobs["speed"] == 2.0
    assert knobs.check("speed", 2.001) is not None  # a real overshoot still fails


def test_non_finite_values_are_refused_with_their_own_message() -> None:
    """json.loads accepts NaN and Infinity literals, so both arrive over the
    wire. NaN compares False against everything, so without this it would be
    reported as a range error, which reads as nonsense."""
    knobs = ParamSet(Knobs)
    for value in (float("nan"), float("inf"), float("-inf")):
        reason = knobs.check("speed", value)
        assert reason is not None and "finite" in reason


def test_bools_are_refused() -> None:
    """`float(True)` is 1.0, so a JSON `true` would otherwise land as a
    legal-looking value nobody chose."""
    assert "bool" in (ParamSet(Knobs).check("speed", True) or "")


def test_non_numeric_values_are_refused_as_valueerror() -> None:
    """`float()` raises TypeError for None and ValueError for a string; both
    normalize here so a caller need not catch two exception types."""
    knobs = ParamSet(Knobs)
    assert knobs.check("speed", "fast") is not None
    assert knobs.check("speed", None) is not None
    with pytest.raises(ValueError):
        knobs.set("speed", None)


# ---- the set as a control-surface contract ---------------------------------


def test_check_never_raises_and_is_the_refusal_wording() -> None:
    """`check` exists because an exception from a `PacedLoop.call_soon` closure
    propagates out of `run()` — a raising setter reached over a socket is a way
    to stop the show from a browser. A caller validates on its own thread."""
    knobs = ParamSet(Knobs)
    assert knobs.check("speed", 1.0) is None
    reason = knobs.check("speed", 99.0)
    assert reason is not None
    with pytest.raises(ValueError, match=re.escape(reason)):
        knobs.set("speed", 99.0)


def test_set_reports_whether_the_value_changed() -> None:
    knobs = ParamSet(Knobs)
    assert knobs.set("speed", 1.0) is True
    assert knobs.set("speed", 1.0) is False  # pointer jitter re-sends constantly


def test_set_many_is_all_or_nothing() -> None:
    """A partial write would leave a pattern running a mix of old and new
    values; hot-reload carry-over and a UI reset are both this call."""
    knobs = ParamSet(Knobs)
    with pytest.raises(ValueError):
        knobs.set_many({"speed": 1.0, "tail": 99.0})
    assert knobs.snapshot() == {"speed": 0.4, "tail": 0.25}
    assert sorted(knobs.set_many({"speed": 1.0, "tail": 1.0})) == ["speed", "tail"]


def test_describe_is_json_ready_in_declaration_order() -> None:
    """A list, not a dict, so display order survives transport — this is the
    order a control surface lays its sliders out in."""
    records = ParamSet(Knobs).describe()
    assert [r["name"] for r in records] == ["speed", "tail"]
    assert json.loads(json.dumps(records)) == records
    assert set(records[0]) == {
        "name", "label", "default", "lo", "hi", "step", "decimals", "value",
    }


def test_snapshot_round_trips_through_overrides() -> None:
    """How hot reload carries values across a swap, so it is pinned rather
    than left as an accident of both sides being plain floats."""
    original = ParamSet(Knobs, {"speed": 1.25})
    assert ParamSet(Knobs, original.snapshot()).snapshot() == original.snapshot()


def test_a_pattern_with_no_params_describes_as_empty() -> None:
    class Bare(Pattern):
        name = "bare"

        def render(self, x, y, z, index):
            return np.zeros((index.size, 3), dtype=np.float32)

    assert ParamSet(Bare).describe() == []
    assert Renderer(Bare(), line(4)).params.snapshot() == {}


# ---- declaration discovery --------------------------------------------------


def test_declarations_survive_bind() -> None:
    """The gap this story closes: before it, `lo`/`hi`/`label` were assigned
    and then read by nothing, so no UI could ask what knobs existed."""
    renderer = Renderer(Knobs(), line(4))
    speed = renderer.params.declarations["speed"]
    assert (speed.lo, speed.hi, speed.label) == (0.0, 2.0, "Rev/s")
    assert renderer.pattern.speed == 0.4  # and the instance still reads as a float


def test_most_derived_declaration_wins() -> None:
    class Faster(Knobs):
        speed = Param(1.9, 0.0, 3.0, "Rev/s")

    assert declared_params(Faster)["speed"].default == 1.9
    assert Renderer(Faster(), line(4)).pattern.speed == 1.9


def test_declaration_order_is_base_first() -> None:
    """A subclass appends to a stable prefix rather than reshuffling the row
    above it — that order is a control surface's slider order."""

    class Extra(Knobs):
        wobble = Param(0.1, 0.0, 1.0, "Wobble")

    assert list(declared_params(Extra)) == ["speed", "tail", "wobble"]


def test_declaration_beats_an_init_assignment() -> None:
    """Changed deliberately from the prototype, which let `__init__` win. The
    set owns the value, so a UI cannot be shown a number the pattern ignores."""

    class Stubborn(Knobs):
        def __init__(self):
            self.speed = 1.75

    assert Renderer(Stubborn(), line(4)).pattern.speed == 0.4


# ---- renderer ownership -----------------------------------------------------


def test_set_param_reaches_the_running_pattern() -> None:
    renderer = Renderer(Knobs(), line(4))
    assert renderer.set_param("speed", 1.5) is True
    assert renderer.pattern.speed == 1.5
    assert renderer.params["speed"] == 1.5


def test_param_set_identity_survives_rebind() -> None:
    """A control surface holds this object across rebinds, so replacing it
    would leave that surface driving a set nothing reads."""
    renderer = Renderer(Knobs(), line(4))
    before = renderer.params
    renderer.rebind(line(9))
    assert renderer.params is before
