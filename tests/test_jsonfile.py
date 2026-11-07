"""The one JSON nesting limit, `pewpew.jsonfile.MAX_DEPTH`."""

from __future__ import annotations

import json

import pytest

from pewpew.jsonfile import MAX_DEPTH, ProblemsError, TooDeep, loads, nests_deeper, parse_json

SHAPES = [("[", "]"), ('{"k":', "}")]  # an array, and an object


def text(depth: int, open_: str, close: str) -> str:
    return open_ * depth + "0" * (depth > 0) + close * depth


@pytest.mark.parametrize(("open_", "close"), SHAPES, ids=["array", "object"])
def test_max_depth_is_accepted_and_one_more_refused(open_, close):
    at = text(MAX_DEPTH, open_, close)
    assert loads(at) == loads(at.encode()) == json.loads(at)
    over = text(MAX_DEPTH + 1, open_, close)
    for data in (over, over.encode(), over.encode("utf-16")):
        with pytest.raises(TooDeep) as exc:
            loads(data)
        assert exc.value.pos == MAX_DEPTH * len(open_)  # the bracket that goes past the limit


@pytest.mark.parametrize(("open_", "close"), SHAPES, ids=["array", "object"])
def test_a_value_at_max_depth_does_not_nest_deeper(open_, close):
    at = json.loads(text(MAX_DEPTH, open_, close))
    assert not nests_deeper(at)
    assert nests_deeper([at]) and nests_deeper({"k": at}) and nests_deeper((at,))


def test_unclosed_nesting_is_too_deep_before_the_end():
    with pytest.raises(TooDeep) as exc:
        loads("[" * 100_000)
    assert exc.value.pos == MAX_DEPTH


def test_brackets_in_strings_do_not_count():
    strings = ["[" * 200, "{" * 200, '"' + "[" * 200, '\\"[' * 100]  # escaped quotes stay in the string
    for s in strings:
        doc = "[" * (MAX_DEPTH - 1) + json.dumps([s]) + "]" * (MAX_DEPTH - 1)
        assert loads(doc) == json.loads(doc)  # the string's own array counts, its brackets do not
    ends_in_a_backslash = json.dumps("\\")  # the string closes, so the brackets after it count
    at = "[" * MAX_DEPTH + ends_in_a_backslash + "]" * MAX_DEPTH
    assert loads(at) == json.loads(at)
    with pytest.raises(TooDeep):
        loads("[" * MAX_DEPTH + ends_in_a_backslash + ",[]" + "]" * MAX_DEPTH)


def test_a_value_that_holds_itself_nests_deeper():
    loop: list = []
    loop.append(loop)
    assert nests_deeper(loop)
    assert not nests_deeper("[" * 100) and not nests_deeper(None)


def test_parse_json_names_the_limit():
    with pytest.raises(ProblemsError) as exc:
        parse_json("[" * 100, ProblemsError)
    reason = f"invalid JSON: arrays and objects nest deeper than {MAX_DEPTH} levels (at character {MAX_DEPTH})"
    assert exc.value.problems == [reason]
