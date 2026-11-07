"""The restricted dims-expression evaluator (pewpew.rig.expr)."""

from __future__ import annotations

import pytest

from pewpew.rig.expr import ExprError, evaluate, names, parse, resolve


def test_arithmetic_over_dims():
    env = {"overall_h": 0.0455, "diffuser_d": 0.0302}
    assert evaluate("overall_h - diffuser_d/2", env) == 0.0455 - 0.0302 / 2
    assert evaluate("-(1 + 2) * 3 / 4", {}) == -(1 + 2) * 3 / 4
    assert evaluate("2*wall", {"wall": 0.0015}) == 0.003
    assert evaluate("+1e-3", {}) == 0.001
    assert names("lip_t + slot_h/2 - axis_z") == {"lip_t", "slot_h", "axis_z"}


@pytest.mark.parametrize(
    "src",
    [
        "2 ** 3",
        "abs(x)",
        "__import__('os')",
        "x.real",
        "x[0]",
        "True",
        "'text'",
        "1 if x else 2",
        "x < 1",
        "x == 1",
        "x // 2",
        "x % 2",
        "lambda: 1",
        "not x",
        "(x := 1)",
        "1j",
        "[1, 2]",
        "",
    ],
)
def test_everything_else_is_refused_before_evaluation(src):
    with pytest.raises(ExprError):
        parse(src)


def test_unknown_names_and_division_by_zero_are_errors():
    with pytest.raises(ExprError, match="'housing_d', which is not a dim"):
        evaluate("housing_d / 2", {"housing_w": 0.018})
    with pytest.raises(ExprError, match="divides by zero"):
        evaluate("1 / (a - a)", {"a": 1.0})


def test_resolve_orders_by_dependency_not_by_declaration():
    dims = {
        "flat_z": "axis_z - housing_h",
        "axis_z": "overall_h - d/2",
        "overall_h": 0.0455,
        "d": 0.0302,
        "housing_h": 0.0185,
    }
    out = resolve(dims)
    assert out["axis_z"] == 0.0455 - 0.0302 / 2
    assert out["flat_z"] == out["axis_z"] - 0.0185


def test_resolve_names_the_cycle():
    with pytest.raises(ExprError, match="dims cycle: a -> b -> a"):
        resolve({"a": "b + 1", "b": "a * 2"})
    with pytest.raises(ExprError, match="cycle: c -> c"):
        resolve({"c": "c"})
    with pytest.raises(ExprError, match="names 'nope'"):
        resolve({"a": "nope + 1"})
