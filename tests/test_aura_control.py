"""Aura control: the requests, their checks on the caller's thread, what
reaches the loop thread, and the rule that no refusal names a path."""

from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import numpy as np
import pytest

from fakes import (
    LoopThread,
    Painter,
    aura_rig,
    build,
    ddp_sink,
    look,
    looks_file,
    next_of,
    serving,
    solid,
    wait_until,
)
from pewpew import wled
from pewpew.aura import control
from pewpew.aura.book import Trigger, load_looks
from pewpew.aura.control import MAKING, NO_LOOKS, OVERTAKEN, REQUESTS
from pewpew.awake import KeepAwake
from pewpew.compose import DEFAULT_FADE, Look
from pewpew.errors import Refusal, describe_exception
from pewpew.fx.op import REGISTRY, BindCtx, Op
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.health import HealthMonitor
from pewpew.mapping import line
from pewpew.params import HSV, ParamSet
from pewpew.sinks.ddp import Board

pytestmark = pytest.mark.usefixtures("fake_ops")

# Stripes: one `osc` node, its knobs at `layers.base.osc.*`.
STRIPES = look("osc", {"freq": 8.0})


def osc_rig(start: Look = STRIPES, **kw):
    """An aura on an 8-pixel line, running `start`."""
    return aura_rig(start, mapping=line(8), **kw)


def knobs(rig, nid: str = "osc") -> ParamSet:
    """The knobs of node `nid` of the program layer `base` runs now."""
    return rig.renderer().bound.node_params[nid]


# ---- params ------------------------------------------------------------------


def test_a_live_set_is_queued_for_the_loop_thread_not_applied_on_the_callers():
    rig = osc_rig()
    assert rig.control.set("layers.base.osc.freq", 16.0) is None
    # Nothing has touched the renderer yet: the queue drains at the top of a
    # tick, before advance_to, which is what keeps a frame from seeing half a
    # change.
    assert knobs(rig)["freq"] == 8.0
    rig.calls.drain()
    assert knobs(rig)["freq"] == 16.0
    assert rig.control.values()["layers.base.osc.freq"] == 16.0


def test_a_set_names_its_knob_by_address():
    """A bare name is refused, and the refusal lists the addresses; a
    layer's own mix is a knob too."""
    rig = osc_rig()
    reason = rig.control.set("freq", 16.0)
    assert reason.startswith("unknown knob 'freq'; knobs: layers.base.osc.freq, layers.base.osc.sync, ")
    assert rig.control.set("layers.base.opacity", 2.0) == "layers.base.opacity must be within 0.0..1.0, got 2.0"
    assert rig.control.set("layers.base.blend", "screen") is None
    rig.calls.drain()
    assert rig.fader.current.layer("base").mix.blend == "screen"
    assert rig.control.values()["layers.base.blend"] == "screen"


def test_a_set_checked_against_a_node_that_no_longer_runs_is_dropped(tmp_path, caplog, monkeypatch):
    """A recall queued ahead of the set runs another look first, whose
    node has the same address: the old node's slider must not move the
    new one's. The set is still operator input, so it stops the idle
    cycle."""
    rig = osc_rig(looks={"blue": solid(0.0, 0.0, 1.0)}, path=tmp_path / "looks.json")
    touched = []
    monkeypatch.setattr(rig.looks, "touch", lambda: touched.append(True))
    rig.calls.call_soon(lambda: rig.deck.recall(look("osc", {"freq": 4.0})))
    assert rig.control.set("layers.base.osc.freq", 16.0) is None  # checked against the running node
    rig.calls.drain()
    assert knobs(rig)["freq"] == 4.0
    assert "dropped a live set of 'layers.base.osc.freq': the node it was for no longer runs" in caplog.text
    assert touched == [True]


def test_a_live_set_queues_the_parsed_value():
    """The JSON a page sends is parsed once, on the caller's thread; the loop
    thread gets the native value."""
    rig = osc_rig(look("zoo_test"))
    assert rig.control.set("layers.base.zoo_test.color", {"h": 30, "s": 0.5, "v": 1}) is None
    rig.calls.drain()
    assert knobs(rig, "zoo_test")["color"] == HSV(30.0, 0.5, 1.0)


def test_an_out_of_range_live_set_is_refused_without_queueing_anything():
    # The live-crash path: a queued closure's exception ends run(), so an
    # out-of-range slider must never become a queued closure.
    rig = osc_rig()
    assert rig.control.set("layers.base.osc.freq", 99.0) == knobs(rig).check("freq", 99.0)
    rig.calls.drain()
    assert knobs(rig)["freq"] == 8.0


def test_a_queued_set_gone_stale_logs_instead_of_killing_the_loop(caplog, monkeypatch):
    # A value passes check on the connection thread, then the range moves
    # under it before the closure runs. Applying it must not raise.
    rig = osc_rig()
    rig.control.set("layers.base.osc.freq", 16.0)
    # Declarations are the class's own Param objects, shared by every test in
    # the process — monkeypatch so narrowing the range does not outlive this one.
    monkeypatch.setattr(knobs(rig).declarations["freq"], "hi", 10.0)
    with caplog.at_level(logging.WARNING, logger="pewpew"):
        rig.calls.drain()  # the loop thread; must return, not raise
    assert "freq" in caplog.text and knobs(rig)["freq"] == 8.0


# ---- the master --------------------------------------------------------------


def test_the_master_is_capped_and_queued_for_the_loop_thread():
    rig = osc_rig(cap=0.6)
    assert (rig.control.state()["master"], rig.control.state()["cap"]) == (0.6, 0.6)
    assert rig.control.master(0.7) == "master must be within 0.0..0.6, got 0.7"
    for bad in (True, float("nan"), -0.1, "bright", None):
        assert rig.control.master(bad) is not None
    rig.calls.drain()
    assert rig.master.level == 0.6  # nothing refused reached the loop
    assert rig.control.master(0.3) is None
    assert rig.master.level == 0.6  # not yet: the loop thread applies it
    rig.calls.drain()
    assert rig.master.level == 0.3


def test_blackout_forces_zero_and_restore_keeps_the_master():
    rig = osc_rig()
    rig.control.master(0.4)
    assert rig.control.blackout(True) is None
    rig.calls.drain()
    assert rig.master.blackout and rig.master.scale == 0.0 and rig.master.level == 0.4
    assert rig.control.state()["blackout"] is True
    assert rig.control.blackout("yes") == "blackout takes true or false, got 'yes'"
    rig.control.blackout(False)
    rig.calls.drain()
    assert rig.master.scale == 0.4


# ---- the request table ---------------------------------------------------------


def test_a_request_is_its_controls_method_with_the_tables_defaults(tmp_path):
    """`request` is the one dispatch a surface needs: each message type is
    the method of that name, its missing fields at their defaults."""
    rig = osc_rig(looks={"blue": solid(0.0, 0.0, 1.0)}, path=tmp_path / "looks.json")
    assert rig.control.request({"type": "blackout", "on": "yes"}) == Refusal("blackout takes true or false, got 'yes'")
    with LoopThread(rig.calls):
        unknown = Refusal("unknown look 'nosuch'; looks: blue")
        assert rig.control.request({"type": "recall", "name": "nosuch"}) == unknown
    assert rig.control.request({"type": "fire", "name": 7}) == Refusal("a trigger name is text, got 7")
    assert rig.control.request({"type": "rename", "name": "blue"}) == Refusal("a look name is text, got None")
    with LoopThread(rig.calls):
        assert rig.control.request({"type": "rename", "name": "blue", "to": "navy"}) is None
        assert list(load_looks(tmp_path / "looks.json").looks) == ["navy"]
    assert rig.control.request({"type": "favorite", "name": "navy", "on": 1}) == Refusal(
        "favorite takes true or false, got 1")
    with LoopThread(rig.calls):
        assert rig.control.request({"type": "favorite", "name": "navy", "on": False}) is None
        assert load_looks(tmp_path / "looks.json").favorites == ()
    # A refused set names its knob, so a page can show the refusal there.
    assert rig.control.request({"type": "set", "name": "layers.base.osc.freq", "value": "x"}) == Refusal(
        "layers.base.osc.freq takes a number, got 'x'", "layers.base.osc.freq")


def test_a_control_the_run_does_not_have_says_so_and_one_it_does_not_know_is_ignored():
    rig = osc_rig()  # no boards, no room
    for message, reason in (({"type": "scan"}, "this run streams to no boards"),
                            ({"type": "rebind", "board": "A", "address": "1.2.3.4"}, "this run streams to no boards"),
                            ({"type": "blink", "fixture": "a"},
                              "blink needs an arrangement map (run --map RIG.arrangement.json)"),
                            ({"type": "arrange", "arrangement": {}},
                              "layout edits need an arrangement map (run --map RIG.arrangement.json)"),
                            ({"type": "look", "look": {}}, NO_LOOKS)):
        assert rig.control.request(message) == Refusal(reason)
    for message in ({"type": "launch"}, {"type": 7}, {}):
        assert rig.control.request(message) is None


class FakeLayout:
    """A rig file the page edits: it records each arrangement sent, and
    refuses an empty one with an issue."""

    def __init__(self, editable: bool) -> None:
        self.editable = editable
        self.sent: list[object] = []
        self.state = {"arrangement": {"format": "pewpew.arrangement"} if editable else None,
                      "base": "b0" if editable else None}
        self.findings = {"issues": [], "report": None}

    def arrange(self, doc: object, base: object) -> Refusal | None:
        self.sent.append((doc, base))
        return None if doc else Refusal("empty", issues=({"code": "empty"},))

    def arrangement(self) -> dict:
        return self.state

    def report(self) -> dict:
        return self.findings


def test_arrange_goes_to_the_layout_and_leaves_the_looks_alone():
    layout = FakeLayout(editable=True)
    rig = osc_rig(layout=layout)
    assert rig.control.capabilities == ("arrange",)
    assert rig.control.request({"type": "arrange", "arrangement": {"a": 1}, "base": "b0"}) is None
    assert layout.sent == [({"a": 1}, "b0")]
    assert rig.control.request({"type": "arrange", "arrangement": {}}) == Refusal("empty", issues=({"code": "empty"},))
    assert layout.sent[-1] == ({}, None)  # the layout refuses an arrange without a base
    assert not rig.calls._queue  # not operator input: the looks are not touched
    states = control.wire_states(rig.control, {})
    assert states["arrangement"] is layout.state and states["report"] is layout.findings
    assert osc_rig(layout=FakeLayout(editable=False), accept_looks=True).control.capabilities == ("look",)
    bare = control.wire_states(osc_rig().control, {})
    assert bare["arrangement"] is None and bare["report"] is None


def test_a_control_it_does_not_know_is_refused_when_its_sender_waits_for_an_answer():
    """With an `id` the sender waits for an answer, so a typo is refused,
    never taken for an accepted request (ADR-020 amendment)."""
    rig = osc_rig()
    assert rig.control.request({"type": "sett", "id": 1}) == Refusal(
        f"unknown control 'sett'; controls: {', '.join(REQUESTS)}")
    assert rig.control.request({"type": 7, "id": "a"}) == Refusal(f"unknown control 7; controls: {', '.join(REQUESTS)}")


# ---- no refusal names a path ------------------------------------------------------


@pytest.fixture
def served_from_a_private_folder(tmp_path, monkeypatch):
    """An aura whose looks file sits in a folder whose name must never reach
    the socket, served over the preview."""
    private = tmp_path / "private-folder-xyz"
    private.mkdir()
    triggers = {"cue": Trigger(look="blue")}
    rig = aura_rig(mapping=line(4), looks={"blue": solid(0.0, 0.0, 1.0)},
                   triggers=triggers, path=private / "looks.json", timeout=2.0)
    with serving(rig.control, rig.calls) as (_, ws, _):
        yield rig, ws, private


def refusals(ws, messages) -> list[dict]:
    """Send each message, then read until a refusal for each has arrived."""
    for message in messages:
        ws.send(json.dumps(message))
    return [next_of(ws, "refused") for _ in messages]


def test_no_refusal_over_the_socket_names_a_path(served_from_a_private_folder, monkeypatch):
    """Every refusal crosses one socket, which anyone on the private network can
    reach (architecture §5): an op named by a path, a look request whose
    write fails, and every malformed message must say why without the
    folder, a file name or `.py`."""
    _, ws, private = served_from_a_private_folder
    mine = private / "mine.py"
    messages = [
        {"type": "recall", "name": "nosuch"}, {"type": "recall", "name": "../looks.json"},
        {"type": "recall", "name": 7}, {"type": "recall", "name": "blue", "fade": -2},
        {"type": "save", "name": "/etc/passwd"}, {"type": "save", "name": "ok", "master": "yes"},
        {"type": "delete", "name": "blue"}, {"type": "cycle", "name": "blue", "on": 1},
        {"type": "fire", "name": 7}, {"type": "fire", "name": "../looks.json"},
        {"type": "fire", "name": "cue", "value": "x"}, {"type": "arm", "on": 1},
        {"type": "add_layer", "layer": {"nodes": {"x": {"op": "../looks.json"}}}},
        {"type": "add_layer", "layer": {"nodes": {"x": {"op": "pattern", "args": {"pattern": str(mine)}}}}},
        {"type": "add_layer", "layer": {"nodes": {"x": {"op": "osc", "args": {"freq": str(private / "broken.py")}}}}},
        {"type": "set", "name": "nosuch", "value": 1},
        {"type": "rename", "name": "blue", "to": "red"}, {"type": "rename", "name": "blue", "to": "../looks.json"},
        {"type": "rename", "name": "nosuch", "to": "red"}, {"type": "rename", "name": "blue", "to": 7},
    ]
    replies = refusals(ws, messages)
    monkeypatch.setattr(os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError(28, "No space", str(private))))
    replies += refusals(ws, [{"type": "save", "name": "fresh"}])
    assert [r["control"] for r in replies] == [m["type"] for m in messages] + ["save"]
    for reply in replies:
        reason = reply["reason"]
        assert str(private) not in reason and "private-folder" not in reason, reason
        assert "mine.py" not in reason and "broken.py" not in reason and ".py" not in reason, reason
    assert "unknown op 'pattern'; ops: " in replies[13]["reason"]


SECRET = Path.home() / "secret-folder" / "mine.py"
# Errors whose text carries a path, as CPython and libraries word them.
PATH_ERRORS = {
    "import": lambda: ImportError(f"cannot import name 'Param' from 'pewpew' ({SECRET})", path=str(SECRET)),
    "message": lambda: ValueError("no table in /private/var/secret-folder/table.bin"),
    "home": lambda: RuntimeError(f"cannot write {Path.home()}"),
    "oserror": lambda: PermissionError(13, f"Permission denied: {SECRET}", str(SECRET)),
}


def leaks(text: str) -> bool:
    return "secret-folder" in text or str(Path.home()) in text or "/private" in text


@pytest.fixture
def raising_ops() -> Iterator[dict[str, Callable[[], Exception]]]:
    """Two ops in the registry for this test that raise the error the
    returned dict holds at `make`: `raising_test` as it renders and
    `unbuildable_test` as it binds."""
    before = dict(REGISTRY)
    errors: dict[str, Callable[[], Exception]] = {}

    class RaisingTest(Op, op="raising_test"):
        """Raises as it renders."""

        sig, out = Sig.SOURCE, Ty.RGB

        def build(self, inputs: Sequence[Fn]) -> Fn:
            def raising(c: Coords) -> np.ndarray:
                raise errors["make"]()

            return raising

    class UnbuildableTest(RaisingTest, op="unbuildable_test"):
        """Raises as it binds."""

        def setup(self, ctx: BindCtx) -> None:
            raise errors["make"]()

    try:
        yield errors
    finally:
        REGISTRY.clear()
        REGISTRY.update(before)


@pytest.mark.parametrize("make", PATH_ERRORS.values(), ids=PATH_ERRORS)
def test_no_error_text_that_reaches_the_page_names_a_path(make, raising_ops, tmp_path, monkeypatch):
    """Each channel an exception's text takes to the page: the render and
    looks status, a recall and failed-request refusal, a
    trigger's `last.error`, a board's reasons, the scan error and the sleep
    detail."""
    raising_ops["make"] = make
    rig = aura_rig(look("raising_test"), looks={"bad": look("unbuildable_test", fade=0.0)},
                   triggers={"cue": Trigger(look="bad", debounce=0.0)}, path=tmp_path / "looks.json")
    texts = [describe_exception(make()), wled.failure(make())]
    rig.frame(rig.clock.advance())
    texts.append(rig.fader.error and str(rig.fader.error))
    with LoopThread(rig.calls):
        texts.append(rig.control.recall("bad"))
        monkeypatch.setattr(rig.looks, "save", lambda *a: (_ for _ in ()).throw(make()))
        texts.append(rig.control.save("x"))
    rig.triggers.arm(True, "test")
    rig.triggers.submit("page", "cue")
    rig.frame(rig.clock.advance())
    texts.append(rig.triggers.state()["last"]["error"])
    rig.looks.before_frame(rig.clock.advance())

    sink, _, _ = ddp_sink([Board("10.0.0.11", 0, 4)], 4)
    monitor = HealthMonitor(sink, fetch=lambda host, timeout: (_ for _ in ()).throw(make()),
                            sender=lambda host, port: "10.0.0.2")
    monitor.step()
    texts += monitor.state()["boards"][0]["reasons"]
    monkeypatch.setattr(wled, "sweep", lambda *a, **kw: (_ for _ in ()).throw(make()))
    monitor.scan()
    wait_until(lambda: not monitor.state()["scan"]["running"])
    texts.append(monitor.state()["scan"]["error"])
    if isinstance(make(), OSError):
        awake = KeepAwake(spawn=lambda args: (_ for _ in ()).throw(make()), which=lambda name: name)
        awake.start()
        texts.append(awake.state()["detail"])
    assert all(texts) and not [text for text in texts if leaks(text)], texts


def test_a_look_request_that_raises_is_a_refusal_and_the_aura_goes_on(tmp_path, monkeypatch):
    rig = aura_rig(looks={"blue": solid(0.0, 0.0, 1.0)}, path=tmp_path / "looks.json", timeout=2.0)

    def broken(name, fade=None):
        raise RuntimeError("broken")

    monkeypatch.setattr(rig.looks, "recall", broken)
    with LoopThread(rig.calls):
        reason = rig.control.recall("blue")
    assert reason is not None and reason.startswith("the request failed: RuntimeError")
    np.testing.assert_array_equal(rig.frame(1 / 60), [[1.0, 0.0, 0.0]] * 4)


# ---- numbers at the edge -------------------------------------------------------


def test_a_value_a_hair_past_its_range_is_stored_on_the_range():
    """A slider's float noise is accepted and snapped, and the stored value
    is the snapped one, so a saved look never holds a master above the cap
    or a negative fade that a later load or recall would refuse."""
    rig = osc_rig(cap=0.6)
    assert rig.control.master(0.6 * (1 + 5e-10)) is None
    rig.calls.drain()
    assert rig.master.level == 0.6


def test_a_number_too_large_for_a_float_is_a_refusal_not_a_crash():
    rig = osc_rig()
    huge = 10**400  # JSON integers have no size limit
    assert rig.control.master(huge) == "master must be a finite number, got a number too large"
    assert rig.control.set("layers.base.osc.freq", huge) == (
        "layers.base.osc.freq must be a finite number, got a number too large"
    )
    assert rig.control.fire("cue", huge).startswith("a trigger value is a finite number or null")


# ---- looks made for the aura ------------------------------------------------------------


@pytest.fixture
def made(tmp_path):
    rig = aura_rig(looks={"blue": solid(0.0, 0.0, 1.0)}, current="blue", path=tmp_path / "looks.json",
                   variety=Painter, timeout=2.0)
    with serving(rig.control, rig.calls) as (_, ws, _):
        yield rig, ws


def test_a_surprise_and_a_vary_over_the_socket_are_acked_play_and_are_not_saved(made):
    rig, ws = made
    ws.send(json.dumps({"type": "surprise", "id": 1, "seed": 7}))
    assert next_of(ws, "ack") == {"type": "ack", "id": 1, "control": "surprise"}
    assert rig.looks.book.current is None and list(rig.looks.book.looks) == ["blue"]
    assert knobs(rig, "solid").snapshot_json()["green"] == 1.0
    ws.send(json.dumps({"type": "vary", "id": "v", "strength": 0.8, "seed": 2}))
    assert next_of(ws, "ack")["id"] == "v"
    assert knobs(rig, "solid").snapshot_json()["red"] == 0.8
    assert list(rig.looks.book.looks) == ["blue"] and not rig.path.exists()  # nothing written


def test_keep_saves_the_made_look_under_its_own_name_and_a_number_past_it(made):
    rig, ws = made
    for k in range(2):
        ws.send(json.dumps({"type": "surprise", "id": f"s{k}", "seed": 7}))
        next_of(ws, "ack")
        ws.send(json.dumps({"type": "keep", "id": f"k{k}"}))
        assert next_of(ws, "ack") == {"type": "ack", "id": f"k{k}", "control": "keep"}
    assert list(rig.looks.book.looks) == ["blue", "surprise 7", "surprise 8"]  # a taken name counts on by its number
    assert rig.looks.book.current == "surprise 8" and "surprise 8" in json.loads(rig.path.read_text())["looks"]
    ws.send(json.dumps({"type": "keep", "id": "k"}))  # not made: a copy of the current look, counted on
    next_of(ws, "ack")
    assert rig.looks.book.current == "surprise 9"


def test_a_save_with_no_name_keeps_the_made_look_under_the_name_it_offers_with_its_fade(made):
    rig, ws = made
    ws.send(json.dumps({"type": "surprise", "id": "s", "seed": 7}))
    next_of(ws, "ack")
    state = rig.looks.state()
    assert (state["made"], state["offered"]) == ("surprise 7", "surprise 7")  # what the page shows before it saves
    ws.send(json.dumps({"type": "save", "id": "k", "name": None, "fade": None, "master": None}))
    assert next_of(ws, "ack") == {"type": "ack", "id": "k", "control": "save"}
    saved = rig.looks.book.looks["surprise 7"]
    assert rig.looks.book.current == "surprise 7" and rig.looks.state()["made"] is None
    # The made look's fade, not the default; a new look holds the master.
    assert saved.fade == 0.0 != DEFAULT_FADE and saved.master is not None
    assert rig.looks.state()["offered"] == "surprise 8"  # a save with no name now copies it, counted on
    ws.send(json.dumps({"type": "save", "id": "x", "name": None, "fade": "slow"}))
    assert next_of(ws, "refused")["reason"].startswith("fade")


def test_a_bad_surprise_or_vary_is_refused_with_its_id_and_nothing_starts(made):
    rig, ws = made
    before = knobs(rig, "solid").snapshot_json()
    for message, words in (
        ({"type": "surprise", "id": 1, "seed": -1}, "a seed is a whole number of at least 0, got -1"),
        ({"type": "vary", "id": 2, "strength": 2},
         "a strength is a number above 0 and at most 1 (at 0 a look does not change), got 2"),
        ({"type": "vary", "id": 3, "seed": "x"}, "a seed is a whole number of at least 0, got 'x'"),
        ({"type": "vary", "id": 5, "strength": 0},
         "a strength is a number above 0 and at most 1 (at 0 a look does not change), got 0"),
    ):
        ws.send(json.dumps(message))
        refused = next_of(ws, "refused")
        assert (refused["id"], refused["control"], refused["reason"]) == (message["id"], message["type"], words)
    rig.control._variety.fail = True
    ws.send(json.dumps({"type": "surprise", "id": 4}))
    assert next_of(ws, "refused")["reason"].endswith("try another seed")
    assert knobs(rig, "solid").snapshot_json() == before and rig.looks.book.current == "blue"


class Slow(Painter):
    """A `Painter` whose surprise is made only once `made` is set: a make
    that takes as long as a test needs."""

    def __init__(self, deck) -> None:
        super().__init__(deck)
        self.made = threading.Event()

    def surprise(self, seed=None):
        assert self.made.wait(5.0)
        return super().surprise(seed)


@pytest.fixture
def slow(tmp_path):
    rig = aura_rig(looks={"blue": solid(0.0, 0.0, 1.0, fade=0.0), "red": solid(1.0, fade=0.0)}, current="blue",
                   path=tmp_path / "looks.json", variety=Slow, timeout=2.0)
    with serving(rig.control, rig.calls) as (_, ws, _):
        yield rig, ws


def test_a_look_being_made_holds_up_no_request_sent_after_it(slow):
    rig, ws = slow
    ws.send(json.dumps({"type": "surprise", "id": "s", "seed": 7}))
    ws.send(json.dumps({"type": "blackout", "id": "b", "on": True}))
    assert next_of(ws, "ack") == {"type": "ack", "id": "b", "control": "blackout"}  # the look is not made yet
    wait_until(lambda: rig.master.blackout)
    rig.variety.made.set()
    assert next_of(ws, "ack") == {"type": "ack", "id": "s", "control": "surprise"}
    assert knobs(rig, "solid").snapshot_json()["green"] == 1.0


def test_a_look_recalled_while_one_is_made_wins_over_it(slow):
    rig, ws = slow
    ws.send(json.dumps({"type": "surprise", "id": "s", "seed": 7}))
    ws.send(json.dumps({"type": "recall", "id": "r", "name": "red", "fade": 0}))
    assert next_of(ws, "ack")["id"] == "r"
    rig.variety.made.set()
    refused = next_of(ws, "refused")
    assert (refused["id"], refused["control"], refused["reason"]) == ("s", "surprise", OVERTAKEN)
    assert rig.looks.book.current == "red" and rig.looks.state()["made"] is None
    assert knobs(rig, "solid").snapshot_json()["red"] == 1.0


def test_a_look_that_cannot_be_made_for_a_bug_is_refused_naming_it():
    rig = aura_rig(variety=Painter)
    rig.variety.surprise = lambda seed=None: {}["nosuch"]
    with serving(rig.control, rig.calls) as (_, ws, _):
        ws.send(json.dumps({"type": "surprise", "id": 1}))
        assert next_of(ws, "refused")["reason"] == "the look cannot be made: KeyError: 'nosuch'"


def test_a_making_slot_comes_back_when_its_thread_cannot_start(monkeypatch):
    rig = aura_rig(variety=Painter, max_making=1)

    def no_thread(job):
        raise RuntimeError("can't start new thread")

    with monkeypatch.context() as patched:
        patched.setattr(control, "in_background", no_thread)
        with pytest.raises(RuntimeError):
            rig.control.request({"type": "surprise"})
    answered = rig.control.request({"type": "surprise"})
    assert not isinstance(answered, Refusal) or answered.reason != MAKING  # the slot was freed
    rig.calls.close()  # answers the made look's wait for the loop


def test_an_aura_without_a_looks_file_plays_a_surprise_but_cannot_keep_it():
    rig = aura_rig(variety=Painter)
    with serving(rig.control, rig.calls) as (_, ws, _):
        ws.send(json.dumps({"type": "surprise", "id": 1}))
        assert next_of(ws, "ack")["id"] == 1
        assert knobs(rig, "solid").snapshot_json()["green"] == 1.0
        ws.send(json.dumps({"type": "keep", "id": 2}))
        assert next_of(ws, "refused")["reason"] == "no looks file: this aura saves no looks"


def test_a_surprise_without_a_seed_takes_the_run_s_next_one_the_same_in_every_run():
    first, again = (aura_rig().variety for _ in range(2))
    seeds = [first.next_seed() for _ in range(3)]
    assert len(set(seeds)) == 3 and seeds == [again.next_seed() for _ in range(3)]


def test_a_run_varies_its_look_and_the_socket_answers_after(tmp_path):
    run = build(["run", looks_file(), "--map", "line:16"])
    with serving(run.aura.control, run.aura.calls) as (_, ws, _):
        ws.send(json.dumps({"type": "vary", "id": 1, "strength": 0.5, "seed": 3}))
        assert next_of(ws, "ack") == {"type": "ack", "id": 1, "control": "vary"}
        ws.send(json.dumps({"type": "master", "id": 3, "value": 0.5}))
        assert next_of(ws, "ack")["id"] == 3  # the socket still answers
