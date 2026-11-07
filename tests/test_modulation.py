"""Modulation (ADR-006): a driven param renders its base plus an offset in
plain units, wrapped when periodic and clamped otherwise, while the
`ParamSet` keeps the operator's base value.

`modulate` is the rule, held by properties over drawn ranges; `Bound` is
where it reaches a target, and every write to a `ParamSet` goes through it.
"""

from __future__ import annotations

import math
import re
from types import SimpleNamespace

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from fakes import hosted, one_node
from params_zoo import ZOO
from pewpew.color import EMBER
from pewpew.mapping import line
from pewpew.params import HSV, Bool, Bound, Color, Float, Int, Palette, ParamSet
from pewpew.params.kinds import Ranged
from pewpew.render import Renderer


class Knobs:
    """A class that declares params; a pattern and an op are two such."""

    speed = Float(0.4, 0.0, 2.0, "/s")
    angle = Float(90.0, 0.0, 360.0, "°", periodic=True)
    count = Int(3, 1, 8)
    mirror = Bool(False)
    color = Color((200.0, 0.5, 1.0))
    palette = Palette(EMBER)


def bound(name: str | None = None):
    """A set of `Knobs` params applied to a bare target, and the binding."""
    params = ParamSet(Knobs, name=name)
    target = SimpleNamespace()
    return params, target, params.apply(target)


# ---- the rule ------------------------------------------------------------------

FINITE = st.floats(allow_nan=False, allow_infinity=False)
SMALL = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False)
EITHER = st.booleans()


@st.composite
def ranged(
    draw: st.DrawFn, periodic: st.SearchStrategy[bool] = EITHER, whole: st.SearchStrategy[bool] = EITHER
) -> tuple[Ranged, float]:
    """A Float or Int declaration over a drawn range, and a base in it."""
    wraps = draw(periodic)
    if draw(whole):
        lo = draw(st.integers(-1000, 1000))
        hi = lo + draw(st.integers(1, 1000))
        param: Ranged = Int(lo, lo, hi, periodic=wraps)
        return param, draw(st.integers(lo, hi))
    lo = draw(SMALL)
    hi = lo + draw(st.floats(min_value=1e-3, max_value=1e6))
    param = Float(lo, lo, hi, periodic=wraps)
    return param, draw(st.floats(min_value=lo, max_value=hi))


def circular(param: Ranged, a: float, b: float) -> float:
    """How far apart `a` and `b` are on a periodic range."""
    d = abs(a - b) % (param.hi - param.lo)
    return min(d, (param.hi - param.lo) - d)


@given(ranged(), FINITE)
def test_a_modulated_value_is_always_in_range(case, offset) -> None:
    param, base = case
    value = param.modulate(base, offset)
    assert type(value) is param.native
    assert param.lo <= value <= param.hi
    if param.periodic:
        assert value < param.hi  # `hi` is the same point as `lo`, and reads as `lo`
    assert param.parse("x", value)[1] is None


@given(ranged())
def test_offset_zero_gives_the_base(case) -> None:
    param, base = case
    expected = param.lo if param.periodic and base == param.hi else base
    assert param.modulate(base, 0.0) == expected


@given(ranged(periodic=st.just(True), whole=st.just(False)), SMALL, st.floats(min_value=-1.0, max_value=1.0))
def test_a_periodic_wrap_is_continuous(case, offset, nudge) -> None:
    """A small move of the offset is a small move of the value, across the
    wrap too; a whole span later the value is where it started."""
    param, base = case
    span = param.hi - param.lo
    noise = 1e-9 * (span + abs(base) + abs(offset))
    a = param.modulate(base, offset)
    assert circular(param, a, param.modulate(base, offset + nudge)) <= abs(nudge) + noise
    assert circular(param, a, param.modulate(base, offset + span)) <= noise


@given(ranged(periodic=st.just(False)), FINITE, FINITE)
def test_a_clamped_value_never_runs_backwards(case, a, b) -> None:
    param, base = case
    low, high = sorted((a, b))
    assert param.modulate(base, low) <= param.modulate(base, high)


@pytest.mark.parametrize(
    "param, base, offset, expected",
    [
        (Float(0.4, 0.0, 2.0), 0.4, 5.0, 2.0),
        (Float(0.4, 0.0, 2.0), 0.4, -5.0, 0.0),
        (Float(90.0, 0.0, 360.0, periodic=True), 350.0, 20.0, 10.0),
        (Float(90.0, 0.0, 360.0, periodic=True), 10.0, -20.0, 350.0),
        (Float(90.0, 0.0, 360.0, periodic=True), 10.0, -1e-30, 10.0),
        (Int(3, 1, 8), 3, 1.5, 5),  # half rounds up
        (Int(3, 1, 8), 3, 1.49, 4),
        (Int(3, 1, 8), 3, 99.0, 8),
        (Int(0, 0, 12, periodic=True), 11, 1.6, 1),
    ],
)
def test_modulate_wraps_clamps_and_rounds(param, base, offset, expected) -> None:
    assert param.modulate(base, offset) == expected


def test_a_non_finite_offset_is_refused() -> None:
    for offset in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError, match="a modulation offset must be a finite number"):
            Float(0.4, 0.0, 2.0).modulate(0.4, offset)


def test_only_a_number_kind_can_modulate() -> None:
    for param in (Bool(False), Color((0.0, 1.0, 1.0)), Palette(EMBER)):
        assert not hasattr(param, "modulate")


# ---- Bound: the one write path to a target ---------------------------------------


def test_apply_binds_the_set_and_writes_every_value() -> None:
    params, target, link = bound()
    assert params.bound is link and link.target is target and link.params is params
    assert vars(target) == params.snapshot()


def test_a_drive_moves_the_target_and_leaves_the_base() -> None:
    """A slider and a saved look read the set, so they show the operator's
    value; the pattern reads the modulated one."""
    params, target, link = bound()
    link.drive("speed", 0.5)
    assert target.speed == pytest.approx(0.9)
    assert params["speed"] == 0.4 and params.snapshot_json()["speed"] == 0.4
    link.drive("speed", 5.0)
    assert target.speed == 2.0


def test_a_set_while_driven_moves_the_base_under_the_offset() -> None:
    params, target, link = bound()
    link.drive("angle", 300.0)
    assert link.set("angle", 100.0) is True
    assert params["angle"] == 100.0 and target.angle == 40.0
    params.set("angle", 120.0)  # the set itself, as a control surface writes it
    assert target.angle == 60.0


def test_undrive_and_settle_restore_the_bases() -> None:
    params, target, link = bound()
    link.drive("speed", 1.0)
    link.drive("count", 2.0)
    link.undrive("speed")
    assert (target.speed, target.count) == (0.4, 5)
    link.undrive("speed")  # not driven: nothing to do
    link.settle()
    assert vars(target) == params.snapshot()


def test_a_color_is_driven_by_its_parts() -> None:
    params, target, link = bound()
    link.drive("color.h", 200.0)
    link.drive("color.v", -0.75)
    assert target.color == HSV(40.0, 0.5, 0.25)
    assert params["color"] == HSV(200.0, 0.5, 1.0)
    link.undrive("color.h")
    assert target.color == HSV(200.0, 0.5, 0.25)


@pytest.mark.parametrize(
    "path, error, reason",
    [
        ("mirror", TypeError, (
            "layers.base.knobs.mirror cannot be modulated: it is a bool; only a float, an int or a color's part can be"
        )),
        ("palette", TypeError, "layers.base.knobs.palette cannot be modulated: it is a palette"),
        ("color", TypeError, (
            "layers.base.knobs.color cannot be modulated: drive one of the color's parts, color.h, color.s, color.v"
        )),
        ("color.a", TypeError, "drive one of the color's parts"),
        ("speed.x", ValueError, "layers.base.knobs.speed is a float, which has no part 'x'"),
        ("sped", ValueError, "layers.base.knobs: unknown param 'sped'"),
    ],
)
def test_a_drive_that_cannot_modulate_says_why(path, error, reason) -> None:
    _, _, link = bound("layers.base.knobs")
    with pytest.raises(error, match=re.escape(reason)):
        link.drive(path, 1.0)


def test_a_refused_offset_changes_nothing() -> None:
    _, target, link = bound()
    link.drive("speed", 0.5)
    with pytest.raises(ValueError, match="finite"):
        link.drive("speed", math.nan)
    assert target.speed == pytest.approx(0.9)
    link.settle()
    assert target.speed == 0.4


STALE = "this Bound is not the set's binding; use ParamSet.bound, or bind with ParamSet.apply(target)"


def test_a_bound_built_directly_refuses_and_changes_nothing() -> None:
    """Only `apply` links a set to a target, so a Bound built any other way
    would write past the set's offsets and miss its own target."""
    params, target = ParamSet(Knobs, name="knobs"), SimpleNamespace()
    loose = Bound(params, target)
    for call in (lambda: loose.set("speed", 1.5), lambda: loose.drive("speed", 0.2), loose.settle,
                 lambda: loose.undrive("speed"), lambda: loose.value("speed")):
        with pytest.raises(RuntimeError, match=re.escape(f"knobs: {STALE}")):
            call()
    assert vars(target) == {} and params["speed"] == 0.4 and params.bound is None


def test_applying_to_the_same_target_keeps_the_binding_and_its_drives() -> None:
    params, target, link = bound()
    link.drive("speed", 0.5)
    assert params.apply(target) is link and target.speed == pytest.approx(0.9)
    params.set("speed", 1.0)
    assert target.speed == pytest.approx(1.5)


def zoo(mapping: np.ndarray) -> tuple[Renderer, ParamSet]:
    """A renderer of one `zoo_test` node, `zoo`, and the node's knobs."""
    renderer = hosted(one_node(ZOO, node="zoo"), mapping)
    return renderer, renderer.pattern.node_params["zoo"]  # type: ignore[attr-defined]  # a ProgramPattern


@pytest.mark.usefixtures("fake_ops")
def test_a_rebind_keeps_the_drive() -> None:
    """A new room map is not a restart: the node's binding and its drives
    survive it."""
    r, params = zoo(line(64))
    link = params.bound
    assert link is not None
    link.drive("level", -0.4)
    r.rebind(line(32))
    assert params.bound is link and link.target.level == pytest.approx(0.1)  # type: ignore[attr-defined]  # the zoo op
    params.set("level", 0.6)
    assert link.target.level == pytest.approx(0.2) and link.value("level") == pytest.approx(0.2)  # type: ignore[attr-defined]  # the zoo op


@pytest.mark.usefixtures("fake_ops")
def test_a_driven_param_reaches_the_running_node() -> None:
    """A node's set is bound to its op; a drive changes the picture while
    the set, and so every surface, keeps the base."""
    held, _ = zoo(line(64))
    driven, params = zoo(line(64))
    assert params.bound is not None
    params.bound.drive("level", -0.4)
    assert params.bound.target.level == pytest.approx(0.1) and params["level"] == 0.5  # type: ignore[attr-defined]  # the zoo op
    assert not np.array_equal(held.step(1 / 60), driven.step(1 / 60))
