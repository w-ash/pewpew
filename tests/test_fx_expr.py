"""The fluent builder: positional and named args, literals parsed when
written, node ids, one node per builder object, and its refusals."""

from __future__ import annotations

import pytest

from pewpew.fx import expr
from pewpew.fx.expr import noise, osc, pattern, shape
from pewpew.fx.graph import Program
from pewpew.patterns import Plasma


def test_positional_args_follow_the_declared_order_and_names_go_anywhere() -> None:
    node = osc(8, 0.1, axis="u")
    assert dict(node.args) == {"freq": 8.0, "sync": 0.1, "axis": "u"}
    assert dict(osc(4).blend(noise(3), "screen", 0.5).args) == {"mode": "screen", "amount": 0.5}
    palette = osc(2).palette("ember").args["palette"]
    assert palette["label"] == "ember" and len(palette["stops"]) == 4  # a preset is stored by its stops


def test_ids_are_the_op_with_an_ordinal_or_the_one_pinned() -> None:
    program = osc(8).add(osc(3).id("slow")).add(osc(1)).program()
    assert [node.id for node in program.graph] == ["osc", "slow", "add", "osc3", "add2"]
    assert pattern("plasma").program().out == "plasma", "a pattern node is named after its pattern"
    blend = osc(2).blend(osc(3)).program()
    assert blend.out == "blend_", "an op named after a reserved word gets a '_'"
    with pytest.raises(ValueError, match="ids 'osc' are used by more than one node"):
        osc(1).add(osc(2).id("osc")).program()


def test_a_builder_used_twice_is_one_node() -> None:
    waves = osc(8)
    program = waves.add(waves.kaleid(5)).program()
    assert [node.id for node in program.graph] == ["osc", "kaleid", "add"]
    assert program.graph["add"].inputs == ("osc", "kaleid")
    assert Program.of(program) is program


def test_a_literal_is_parsed_when_written_in_the_params_words() -> None:
    with pytest.raises(ValueError, match=r"^kaleid.sides must be within 1..24, got 40$"):
        osc(8).kaleid(40)
    with pytest.raises(ValueError, match="plasma.speed must be within"):
        pattern(Plasma, speed=9.0)
    with pytest.raises(TypeError, match="takes 4 args"):
        osc(1, 2, 3, 4, 5)  # type: ignore[call-arg]  # on purpose
    with pytest.raises(TypeError, match="got 'freq' twice"):
        osc(1, freq=2)  # type: ignore[call-arg]  # on purpose


def test_an_arg_is_a_value_or_a_signal_never_a_function_or_a_field() -> None:
    with pytest.raises(TypeError, match="osc.freq takes a value or a signal, not a function"):
        osc(lambda t: t)  # type: ignore[arg-type]  # on purpose
    with pytest.raises(TypeError, match="takes a value or a signal, not a node: .*use modulate"):
        osc(noise(3))


def test_a_chain_names_what_it_cannot_be() -> None:
    with pytest.raises(AttributeError, match=r"unknown op 'kaleidd' \(did you mean 'kaleid'\?\)"):
        osc(8).kaleidd(5)
    with pytest.raises(AttributeError, match="noise is a source and reads no node; call noise"):
        osc(8).noise(3)
    with pytest.raises(TypeError, match="add reads 2 nodes; pass the node it reads on 'b' first, got 0.5"):
        osc(8).add(0.5)  # type: ignore[arg-type]
    with pytest.raises(AttributeError, match=r"unknown source 'kaleid'"):
        expr.kaleid  # noqa: B018
    assert shape(5).op == "shape"
