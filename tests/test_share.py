"""The share envelope (pewpew.share): what Publish sends and the Gallery stores."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from pewpew import share
from pewpew.aura.book import LookBook, Trigger, examples_book
from pewpew.studio.limits import MAX_BODY_BYTES, MAX_FIXTURES

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
BOOK = examples_book(EXAMPLES)
ARRANGEMENT = {
    "format": "pewpew.arrangement", "version": 1,
    "controllers": [{"id": "A", "profile": "x", "host": "192.168.1.50"}, {"id": "B", "profile": "x"}],
    "plan": {"image": "plan.png", "points": [[0, 0], [100, 0]], "meters": 1.0},
}


def test_the_examples_book_holds_each_files_current_look_named_by_the_file_the_first_current():
    names = sorted(path.name.removesuffix(".look.json") for path in EXAMPLES.glob("*.look.json"))
    assert list(BOOK.looks) == names and BOOK.current == names[0]
    assert not BOOK.triggers and BOOK.notes is None


def test_an_envelope_strips_every_board_address_and_the_plan():
    env = share.envelope(ARRANGEMENT, BOOK, ["tide"])
    assert (env["format"], env["version"]) == ("pewpew.share", 1)
    assert env["arrangement"]["controllers"] == [{"id": "A", "profile": "x"}, {"id": "B", "profile": "x"}]
    assert "plan" not in env["arrangement"]
    assert ARRANGEMENT["controllers"][0]["host"] == "192.168.1.50"  # the run's own is left alone
    checked, _ = share.check({**env, "arrangement": ARRANGEMENT})  # and a client's is stripped again
    assert checked["arrangement"] == env["arrangement"]


def test_triggers_and_notes_are_dropped_and_the_cycle_and_favorites_keep_only_chosen_looks():
    tide, warp = BOOK.looks["tide"], BOOK.looks["warp-lane"]
    book = LookBook({"tide": tide, "warp-lane": warp, "milk": BOOK.looks["milk-bloom"]}, "milk",
                    triggers={"door": Trigger(look="tide")}, notes="mine", favorites=("milk", "tide"))
    looks = share.envelope(ARRANGEMENT, book, ["warp-lane", "tide"])["looks"]
    assert list(looks["looks"]) == ["tide", "warp-lane"]  # the book's order
    assert looks["current"] == "tide"  # `milk` is not chosen: the first chosen
    assert looks["favorites"] == ["tide"] and "triggers" not in looks and "notes" not in looks
    with_notes = {**looks, "notes": "x", "triggers": {"door": {"look": "tide"}}}
    checked, _ = share.check(share.envelope(ARRANGEMENT, book, ["tide"]) | {"looks": with_notes})
    assert "notes" not in checked["looks"] and "triggers" not in checked["looks"]


def test_a_bad_look_is_refused_with_its_name():
    env = share.envelope(ARRANGEMENT, BOOK, ["tide"])
    env["looks"]["looks"]["tide"]["layers"][0]["nodes"] = {"x": {"op": "nosuch"}}
    with pytest.raises(share.ShareError) as refused:
        share.check(env)
    assert any("tide" in problem for problem in refused.value.problems)


@pytest.mark.parametrize("doc, says", [
    ([], "JSON object"),
    ({"format": "pewpew.arrangement", "version": 1, "arrangement": {}, "looks": {}}, '"format": "pewpew.share"'),
    ({"format": "pewpew.share", "version": 1, "arrangement": [], "looks": {"version": 4, "looks": {}}}, "arrangement"),
    ({"format": "pewpew.share", "version": 1, "arrangement": {}, "looks": {"version": 4, "looks": {}}}, "one look"),
    ({"format": "pewpew.share", "version": 1, "arrangement": {}, "looks": {}, "extra": 1}, "unknown key 'extra'"),
    ({"format": "pewpew.share", "version": 1, "arrangement": {"x": float("nan")}, "looks": {}}, "NaN"),
])
def test_what_is_not_a_share_is_refused(doc, says):
    with pytest.raises(share.ShareError, match=says):
        share.check(doc)


def test_the_id_is_stable_whatever_the_key_order():
    checked, _ = share.check(share.envelope(ARRANGEMENT, BOOK, ["tide", "warp-lane"]))
    text = share.canonical_json(checked)
    shuffled = json.loads(json.dumps(checked, sort_keys=True), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
    again, _ = share.check(shuffled)
    assert share.content_id(share.canonical_json(again)) == share.content_id(text)
    want = base64.urlsafe_b64encode(hashlib.sha256(text.encode()).digest()[:16]).decode().rstrip("=")
    assert share.content_id(text) == want and len(want) == 22
    assert share.canonical_json({"b": 1, "a": [2]}) == '{"a":[2],"b":1}'


def test_an_old_bare_row_reads_as_an_envelope_with_the_example_looks():
    old = {"format": "pewpew.arrangement", "version": 1, "controllers": [{"id": "A", "host": "10.0.0.2"}]}
    env, book = share.read(share.canonical_json(old), BOOK)
    assert env["format"] == "pewpew.share" and env["arrangement"]["controllers"] == [{"id": "A"}]
    assert list(env["looks"]["looks"]) == list(BOOK.looks) and list(book.looks) == list(BOOK.looks)
    stored, _ = share.check(share.envelope(ARRANGEMENT, BOOK, ["tide"]))
    env, book = share.read(share.canonical_json(stored), BOOK)
    assert env == stored and list(book.looks) == ["tide"]
    with pytest.raises(ValueError):
        share.read('{"format": "other"}', BOOK)


def test_a_share_over_the_size_cap_is_refused():
    env = share.envelope({**ARRANGEMENT, "notes": "x" * MAX_BODY_BYTES}, BOOK, ["tide"])
    with pytest.raises(share.ShareError, match=f"at most {MAX_BODY_BYTES} bytes"):
        share.check(env)
    small = share.envelope(ARRANGEMENT, BOOK, ["tide"])
    with pytest.raises(share.ShareError, match="at most 100 bytes"):
        share.check(small, max_bytes=100)


def test_the_fixture_cap_and_the_cap_on_every_list():
    over = {"format": "pewpew.arrangement", "version": 1, "groups": [{"preset": "ring", "count": MAX_FIXTURES + 1}]}
    with pytest.raises(share.ShareError, match=f"{MAX_FIXTURES} fixtures"):
        share.check(share.envelope(over, BOOK, ["tide"]))
    long = {**ARRANGEMENT, "psus": [{}] * (MAX_FIXTURES + 1)}
    with pytest.raises(share.ShareError, match=rf"{MAX_FIXTURES} entries in a list \(psus\)"):
        share.check(share.envelope(long, BOOK, ["tide"]))
    at_cap = {**ARRANGEMENT, "psus": [{}] * MAX_FIXTURES}
    share.check(share.envelope(at_cap, BOOK, ["tide"]))  # the cap itself is allowed
