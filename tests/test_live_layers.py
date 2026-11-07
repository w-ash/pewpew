"""Editing the running look a layer at a time, as the page does: add a
layer (from a catalog card), remove one and move one, each through
`AuraControl.request`, and the catalog the page's cards come from."""

from __future__ import annotations

import json
import logging
from concurrent.futures import Future

import numpy as np
import pytest

from fakes import LOOK_CLASSES, FakeCatalog, LoopThread, Painter, Solid, aura_rig, look, next_text, rgb, serving, spec
from pewpew import grid, line
from pewpew.aura.book import load_looks
from pewpew.aura.control import BUSY_LAYER
from pewpew.compose import Look, Route, pattern_layer
from pewpew.errors import Refusal
from pewpew.fx import op as fx_op
from pewpew.fx.codec import MAX_LAYERS
from pewpew.fx.graph import Graph, Node
from pewpew.fx.types import Sig, Ty
from pewpew.lab.search import index
from pewpew.load import Catalog

RED = {"red": 1.0, "green": 0.0, "blue": 0.0}
BLUE = {"red": 0.0, "green": 0.0, "blue": 1.0}


def next_answer(ws) -> dict:
    """The next `ack` or `refused`, past the state the sink sends meanwhile."""
    while (message := next_text(ws))["type"] not in ("ack", "refused"):
        pass
    return message


def solid_layer(color: dict, **mix) -> dict:
    """A layer that runs solid at `color`, in the looks file's form, without an id."""
    return {"nodes": {"solid": {"op": "pattern", "args": {"pattern": "solid", **color}}}, **mix}


def rig_of(tmp_path, *layers, **look):
    """An aura on a 4-pixel line in look `duo` of `layers` and the rest of `look` (signals, routes)."""
    rig = aura_rig(Solid, looks={"duo": Look(layers, **look)}, current="duo", path=tmp_path / "looks.json")
    assert rig.looks.restore() is None
    return rig


def ask(rig, **message) -> Refusal | None:
    """`message` through the control, answered by a loop thread, also when
    the answer comes later (a look to make)."""
    with LoopThread(rig.calls):
        answer = rig.control.request(message)
        return answer.result(timeout=5.0) if isinstance(answer, Future) else answer


def ids(rig) -> list[str]:
    return [live.id for live in rig.fader.current.layers]


def test_an_added_layer_runs_on_top_with_a_free_id_and_the_rest_run_on(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    base = rig.renderer("base")
    assert ask(rig, type="add_layer", layer=solid_layer(BLUE, opacity=0.5)) is None
    assert ask(rig, type="add_layer", layer=solid_layer(BLUE, blend="add", enabled=False)) is None
    assert ids(rig) == ["base", "solid", "solid2"]
    assert rig.renderer("base") is base  # the other layers run on
    assert list(rig.deck.reloaders) == ["base", "solid", "solid2"]
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.5, 0.0, 0.5, 4))
    assert rig.control.state()["stack"]["layers"][1] == {
        "id": "solid", "nodes": [{"id": "solid", "op": "pattern", "label": "solid", "in": []}],
    }
    # An edit of the running look: it stays current, changed until a save keeps it.
    assert rig.looks.book.current == "duo" and rig.looks.changed()
    assert ask(rig, type="save", name="duo", fade=None, master=True) is None
    saved = load_looks(rig.path).looks["duo"]
    assert [(layer.id, layer.opacity, layer.blend, layer.enabled) for layer in saved.layers] == [
        ("base", 1.0, "normal", True), ("solid", 0.5, "normal", True), ("solid2", 1.0, "add", False),
    ]


def test_a_layer_added_below_another_goes_under_it_and_keeps_the_id_it_gives(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED), pattern_layer("top", "solid", BLUE, opacity=0.5))
    assert ask(rig, type="add_layer", layer={"id": "mid", **solid_layer(BLUE)}, below="top") is None
    assert ids(rig) == ["base", "mid", "top"]
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.0, 0.0, 1.0, 4))
    assert ask(rig, type="add_layer", layer={"id": "mid", **solid_layer(RED)}) == Refusal(
        "the look has a layer 'mid'; give another id, or none for a free one", "layers.mid",
    )
    assert ask(rig, type="add_layer", layer=solid_layer(RED), below="tpo") == Refusal(
        "unknown layer 'tpo'; layers: base, mid, top",
    )
    assert ask(rig, type="add_layer", layer="solid") == Refusal(
        "add_layer takes a layer, an object with 'nodes', got str",
    )
    assert ids(rig) == ["base", "mid", "top"]


def test_a_layer_that_names_its_pattern_by_file_is_refused_with_its_address_and_never_read(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    pathed = tmp_path / "x.py"
    pathed.write_text("raise SystemExit('a pattern file sent over the socket ran')\n")
    refusal = ask(rig, type="add_layer", layer={"out": "x", "nodes": {"x": {"op": "pattern",
                                                                            "args": {"pattern": str(pathed)}}}})
    assert refusal is not None and refusal.name == "layers.x.x.pattern"
    assert str(tmp_path) not in refusal.reason and "by name, never by file" in refusal.reason
    assert ids(rig) == ["base"]


def test_a_layer_the_look_or_the_map_cannot_run_is_refused_and_nothing_changes(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    before = rig.fader.current.layers
    refusal = ask(rig, type="add_layer", layer=solid_layer({"red": 7.0}))
    assert refusal == Refusal("layers.solid.solid.red must be within 0.0..1.0, got 7.0", "layers.solid.solid.red")
    fold = {"nodes": {"ramp": {"op": "osc"}, "fold": {"op": "kaleid", "in": ["ramp"]}}}
    assert ask(rig, type="add_layer", layer=fold) == Refusal(
        "layers.fold: layers.fold.fold: kaleid needs a map of 2 or 3 dimensions, and this map has 1; "
        "a strip has no plane to fold; use mirror along the strip",
    )
    assert rig.fader.current.layers == before and list(rig.deck.reloaders) == ["base"]


def test_a_look_holds_at_most_its_layers_cap(tmp_path, monkeypatch):
    monkeypatch.setattr("pewpew.aura.control.MAX_LAYERS", 2)
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    assert ask(rig, type="add_layer", layer=solid_layer(BLUE)) is None
    full = Refusal("a look has at most 2 layers; remove one first")
    assert ask(rig, type="add_layer", layer=solid_layer(BLUE)) == full
    assert MAX_LAYERS == 16  # the looks file's cap, which the patch above stands in for


def test_a_removed_layer_stops_with_its_reloader_and_a_route_into_it_rests(tmp_path):
    rig = rig_of(
        tmp_path, pattern_layer("base", "solid", RED), pattern_layer("top", "solid", BLUE, opacity=0.5),
        signals=Graph((Node("breath", "lfo", {"rate": 0.5}),)), routes=(Route("breath", "layers.top.opacity", 0.2),),
    )
    base, top = rig.renderer("base"), rig.deck.reloaders["top"]
    assert ask(rig, type="remove_layer", lid="top") is None
    assert ids(rig) == ["base"] and rig.renderer("base") is base
    assert list(rig.deck.reloaders) == ["base"] and top._stopped
    assert rig.control.state()["stack"]["routes"] == []
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(1.0, 0.0, 0.0, 4))
    assert ask(rig, type="remove_layer", lid="base") == Refusal("a look has at least one layer")
    assert ask(rig, type="remove_layer", lid="top") == Refusal("unknown layer 'top'; layers: base")


def test_a_moved_layer_blends_in_its_new_place_as_it_ran(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED), pattern_layer("top", "solid", BLUE))
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.0, 0.0, 1.0, 4))
    top = rig.renderer("top")
    assert ask(rig, type="move_layer", lid="top", to=0) is None
    assert ids(rig) == ["top", "base"] and rig.renderer("top") is top
    np.testing.assert_array_equal(rig.frame(2 / 60), rgb(1.0, 0.0, 0.0, 4))
    assert ask(rig, type="move_layer", lid="top", to=2) == Refusal("to must be within 0..1, got 2")
    assert ask(rig, type="move_layer", lid="top", to=True) == Refusal("to takes a number, got the bool True")
    assert ask(rig, type="move_layer", lid="nope", to=0) == Refusal("unknown layer 'nope'; layers: top, base")
    assert ask(rig, type="remove_layer", lid="base") is None
    assert ask(rig, type="move_layer", lid="top", to=0) == Refusal(
        "the look has one layer, so it has nowhere else to go",
    )


def test_an_edit_ends_a_running_fade_and_is_operator_input(tmp_path):
    rig = aura_rig(Solid, looks={"red": look("solid", RED), "blue": look("solid", BLUE)}, current="red",
                   path=tmp_path / "looks.json")
    assert rig.looks.restore() is None
    assert rig.looks.recall("blue", 2.0) is None and rig.fader.fading
    touched = []
    rig.looks.touch = lambda: touched.append(True)
    assert ask(rig, type="add_layer", layer=solid_layer(RED, opacity=0.5)) is None
    assert not rig.fader.fading and touched == [True]
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.5, 0.0, 0.5, 4))


def test_an_edit_drops_a_recall_that_waits_for_the_fade_it_ends(tmp_path):
    """The edit cut the fade, so a recall queued behind it would start on
    the next frame and drop the layer just acked."""
    rig = aura_rig(Solid, looks={"red": look("solid", RED), "blue": look("solid", BLUE), "green": look("solid", RED)},
                   current="red", path=tmp_path / "looks.json")
    assert rig.looks.restore() is None
    assert rig.looks.recall("blue", 2.0) is None and rig.looks.recall("green", 2.0) is None
    assert rig.looks.state()["pending"] == "green"
    assert ask(rig, type="add_layer", layer=solid_layer(RED, opacity=0.5)) is None
    rig.frame(1 / 60)
    assert ids(rig) == ["base", "solid"] and not rig.fader.fading
    state = rig.looks.state()
    assert (state["pending"], state["current"], state["changed"]) == (None, "blue", True)
    np.testing.assert_array_equal(rig.frame(2 / 60), rgb(0.5, 0.0, 0.5, 4))


@pytest.mark.parametrize("edit", [
    {"type": "add_layer", "layer": solid_layer(RED, opacity=0.5)},
    {"type": "move_layer", "lid": "top", "to": 0},
    {"type": "remove_layer", "lid": "top"},
])
def test_an_edit_during_a_trigger_hold_ends_it_and_the_aura_does_not_return(tmp_path, edit):
    """The operator wins, as a recall or a save during a hold does: the
    edit stays when the hold's time is up."""
    duo = Look((pattern_layer("base", "solid", RED), pattern_layer("top", "solid", BLUE, opacity=0.5)))
    rig = aura_rig(Solid, looks={"solo": look("solid", BLUE), "duo": duo}, current="solo",
                   path=tmp_path / "looks.json")
    assert rig.looks.restore() is None
    assert rig.looks.hold("door", "duo", 0.5, 0, rig.fader.t) is None and rig.looks.held is not None
    assert ask(rig, **edit) is None
    edited = ids(rig)
    assert rig.looks.held is None and not rig.fader.fading
    rig.frame(1.0)  # the hold's time is up: no return starts
    assert ids(rig) == edited and not rig.fader.fading
    assert rig.looks.book.current == "solo" and rig.looks.changed()


def test_a_keep_after_a_layer_edit_saves_the_made_look_as_edited_under_its_own_name(tmp_path):
    """An edit changes the made look that runs; it does not leave it, as a pick does."""
    rig = aura_rig(Solid, looks={"blue": look("solid", BLUE)}, current="blue", path=tmp_path / "looks.json",
                   variety=Painter)
    assert rig.looks.restore() is None
    assert ask(rig, type="surprise", seed=7) is None  # Painter's surprise: solid green on `base`
    assert ask(rig, type="add_layer", layer=solid_layer(RED, opacity=0.5)) is None
    assert rig.looks.book.current is None  # still the made look, unsaved
    assert ask(rig, type="keep") is None
    assert rig.looks.book.current == "surprise 7" and not rig.looks.changed()
    kept = load_looks(rig.path).looks["surprise 7"]
    assert [(layer.id, spec(layer), layer.opacity) for layer in kept.layers] == [
        ("base", "solid", 1.0), ("solid", "solid", 0.5),
    ]
    assert ask(rig, type="recall", name="surprise 7", fade=0) is None
    np.testing.assert_array_equal(rig.frame(1 / 60), rgb(0.5, 0.5, 0.0, 4))


def test_an_edit_to_a_made_look_is_changed_until_a_keep_saves_it(tmp_path):
    """A made look is compared with itself as it started, as a recalled
    look is with itself as saved: the page marks its edits and guards them."""
    rig = aura_rig(Solid, looks={"blue": look("solid", BLUE)}, current="blue", path=tmp_path / "looks.json",
                   variety=Painter)
    assert rig.looks.restore() is None
    assert ask(rig, type="surprise", seed=7) is None
    state = rig.looks.state()
    assert not rig.looks.changed() and state["made"] == "surprise 7" and state["saved"] is not None
    assert ask(rig, type="add_layer", layer=solid_layer(RED, opacity=0.5)) is None
    assert rig.looks.changed() and rig.looks.state()["changed"]
    assert ask(rig, type="keep") is None
    assert rig.looks.book.current == "surprise 7" and not rig.looks.changed()


def test_each_card_adds_its_example_as_it_is(tmp_path):
    """The page sends a card's example program with the mix it picks; the
    engine runs it. A card names the map dimensions it takes."""
    rig = aura_rig(Solid, mapping=grid(4, 4), catalog=FakeCatalog(LOOK_CLASSES))
    cards = {card["name"]: card for card in rig.control.catalog()["cards"]}
    assert [name for name, card in cards.items() if card["kind"] == "pattern"] == sorted(LOOK_CLASSES)
    assert cards["solid"] == {
        "kind": "pattern", "name": "solid", "label": "solid", "summary": "",
        "sig": None, "dims": None, "fix": "", "examples": [{"py": 'pattern("solid")', "json": {
            "out": "solid", "nodes": {"solid": {"op": "pattern", "args": {"pattern": "solid"}}}}, "dims": [1, 2, 3]}],
    }
    assert "lfo" not in cards and cards["kaleid"]["dims"] == [2, 3] and cards["kaleid"]["sig"] == "coord"
    # An example runs on the maps each of its ops takes: the pattern op runs on a strip, its example does not.
    assert cards["pattern"]["dims"] == [1, 2, 3]
    assert [e["dims"] for e in cards["pattern"]["examples"]] == [[2, 3], [1, 2, 3]]
    for name in ("solid", "kaleid", "below"):
        layer = {**cards[name]["examples"][0]["json"], "blend": "screen", "opacity": 0.7}
        assert ask(rig, type="add_layer", layer=layer) is None, name
    assert ids(rig) == ["base", "solid", "kaleid", "hue"]
    assert np.isfinite(rig.frame(1 / 60)).all()


def test_a_card_names_its_record_as_a_catalog_search_does():
    """The page and an agent describe one record in the same words."""
    rig = aura_rig(Solid, catalog=FakeCatalog(LOOK_CLASSES))
    cards = {(card["kind"], card["name"]): card for card in rig.control.catalog()["cards"]}
    found = {(item.kind, item.name): item.to_json() for item in index().items}
    short = ("kind", "name", "label", "summary", "sig")
    for key in (("pattern", "wave"), ("op", "kaleid")):
        assert [cards[key][k] for k in short] == [found[key][k] for k in short]
    assert cards["pattern", "wave"]["summary"] == "Bands of light cross the room in one direction."


def test_the_catalog_is_one_object_until_an_op_registers_or_a_pattern_file_comes(tmp_path, monkeypatch):
    rig = aura_rig(Solid, catalog=Catalog(tmp_path))
    first = rig.control.catalog()
    assert rig.control.catalog() is first
    assert [blend["name"] for blend in first["blends"]][:3] == ["normal", "add", "screen"]

    class Glow(fx_op.Op):
        """Glows."""

        sig, out = Sig.SOURCE, Ty.SCALAR

    Glow.op = "glow"
    monkeypatch.setitem(fx_op.REGISTRY, "glow", Glow)
    second = rig.control.catalog()
    assert second is not first and "glow" in [card["name"] for card in second["cards"]]
    (tmp_path / "mine.py").write_text("")
    rig.control.rescan()
    assert "mine" in [card["name"] for card in rig.control.catalog()["cards"]]


def test_an_op_whose_example_does_not_build_leaves_the_page_its_last_catalog(monkeypatch, caplog):
    """A typo in one op file's example must not take the page down: the
    page keeps the cards it had, or gets none, the log says why once, and
    a client is still greeted."""
    rig = aura_rig(Solid, mapping=line(4))
    first = rig.control.catalog()

    class Glow(fx_op.Op):
        """Glows."""

        sig, out = Sig.SOURCE, Ty.SCALAR
        examples = ("glow(",)

    Glow.op = "glow"
    monkeypatch.setitem(fx_op.REGISTRY, "glow", Glow)
    with caplog.at_level(logging.WARNING, logger="pewpew.aura.control"):
        assert rig.control.catalog() is first and rig.control.catalog() is first
    assert [r.getMessage() for r in caplog.records] == ["the page keeps its last catalog: the catalog cannot be made"]
    with serving(rig.control, rig.calls) as (_, _ws, greeting):
        assert greeting["catalog"]["cards"] == first["cards"]
    assert aura_rig(Solid, mapping=line(4)).control.catalog() == {"cards": [], "blends": []}


def test_a_layer_without_an_id_or_an_out_is_named_by_the_node_it_draws(tmp_path):
    """The last node in the order they run, as the loader decodes it,
    whatever order the client lists its nodes in."""
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    tinted = {"nodes": {"tint": {"op": "hue", "in": ["solid"], "args": {}},
                        "solid": {"op": "pattern", "args": {"pattern": "solid"}}}}
    assert ask(rig, type="add_layer", layer=tinted) is None
    assert ids(rig) == ["base", "tint"] and rig.fader.current.layer("tint").layer.program.out == "tint"


def test_a_client_with_an_id_gets_each_layer_edit_acked_or_refused_with_it(tmp_path):
    rig = rig_of(tmp_path, pattern_layer("base", "solid", RED))
    with serving(rig.control, rig.calls) as (_, ws, greeting):
        assert [card["name"] for card in greeting["catalog"]["cards"]][:3] == ["fixtureramp", "pixelramp", "pulse"]
        answers = []
        for message in (
            {"type": "add_layer", "id": 1, "layer": solid_layer(BLUE)},
            {"type": "move_layer", "id": 2, "lid": "solid", "to": 0},
            {"type": "remove_layer", "id": 3, "lid": "solid"},
            {"type": "remove_layer", "id": 4, "lid": "base"},
        ):
            ws.send(json.dumps(message))
            answers.append(next_answer(ws))
    assert answers == [
        {"type": "ack", "id": 1, "control": "add_layer"},
        {"type": "ack", "id": 2, "control": "move_layer"},
        {"type": "ack", "id": 3, "control": "remove_layer"},
        {"type": "refused", "control": "remove_layer", "name": None, "id": 4,
         "reason": "a look has at least one layer"},
    ]


def test_a_layer_the_loop_takes_too_late_is_refused_and_never_added():
    """A client told so may send it again without adding it twice."""
    rig = aura_rig(Solid, mapping=line(4), timeout=0.01)
    assert rig.control.request({"type": "add_layer", "layer": solid_layer(BLUE)}) == Refusal(BUSY_LAYER)
    rig.calls.drain()
    assert ids(rig) == ["base"]


@pytest.mark.parametrize(("message", "reason"), [
    ({"type": "remove_layer", "lid": 7}, "unknown layer 7; layers: base"),
    ({"type": "move_layer", "lid": "base", "to": "up"}, "the look has one layer, so it has nowhere else to go"),
    ({"type": "add_layer", "layer": None}, "add_layer takes a layer, an object with 'nodes', got NoneType"),
    ({"type": "add_layer", "layer": solid_layer(BLUE), "below": 3}, "unknown layer 3; layers: base"),
])
def test_a_bad_layer_request_is_refused_on_the_callers_thread(message, reason):
    """No loop thread runs here: a refusal that waited for one would time out."""
    rig = aura_rig(Solid, mapping=line(4), timeout=0.01)
    assert rig.control.request(message) == Refusal(reason)
