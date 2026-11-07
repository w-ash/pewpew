"""Live look control (tier 1): `push`, `set_value` and `python -m pewpew
push` against a real preview on a free port, over an aura that takes looks
(`run --accept-looks`), and the engine's answers on the wire: an `ack` or
a `refused` carrying the request's `id` (ADR-018 and ADR-020 amendments,
2026-11-05)."""

from __future__ import annotations

import contextlib
import json
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest
from websockets.sync.client import connect
from websockets.sync.server import serve

import pewpew.remote.control as remote_control
from fakes import (
    LoopThread,
    Solid,
    aura_rig,
    filed,
    layered,
    look,
    next_of,
    next_text,
    preview_sink,
    serving,
    wait_until,
)
from pewpew import grid, line
from pewpew.__main__ import main
from pewpew.aura.control import BUSY
from pewpew.load import Catalog
from pewpew.problems import Code, Refused
from pewpew.remote.client import Client, Unreachable
from pewpew.remote.control import Answer, Forbidden, push, set_value

COMET = layered("comet", {"speed": 0.4}, fade=0)
SPEED = "layers.base.comet.speed"
# Two layers: an effect program of three nodes, and a pattern screened over it.
TIDE = {"fade": 0, "layers": [
    {"id": "base", "nodes": {
        "waves": {"op": "osc", "args": {"freq": 8.0, "sync": 0.1}},
        "fold": {"op": "kaleid", "in": ["waves"], "args": {"sides": 5}},
        "tint": {"op": "palette", "in": ["fold"], "args": {"palette": "ember"}}}},
    {"id": "sparks", "blend": "screen", "opacity": 0.6, "nodes": {
        "comet": {"op": "pattern", "args": {"pattern": "comet", "speed": 0.6}}}},
]}
# The hello of an engine with no map, as a build before capabilities sent it.
OLD_HELLO = {"type": "hello", "n": 0, "total": 0, "positions": [], "is3d": False, "room": None,
             "display_gamma": 2.2, "build": None}


def with_pattern(spec: str) -> dict:
    """A one-layer look whose node `x` runs pattern `spec`."""
    return layered(spec, node="x")


@contextlib.contextmanager
def engine(catalog: Catalog | None = None, mapping=None, **kw):
    """An aura on `mapping` (default a 4-pixel line) whose catalog is
    `catalog`, by default the gallery, behind a started preview, its calls
    drained on a loop thread. Yields the aura and the engine's address."""
    mapping = line(4) if mapping is None else mapping
    rig = aura_rig(Solid, mapping=mapping, catalog=Catalog() if catalog is None else catalog, **kw)
    with preview_sink(mapping, control=rig.control) as sink, LoopThread(rig.calls):
        yield rig, f"ws://127.0.0.1:{sink.port}/"


def next_answer(ws) -> dict:
    """The next `ack` or `refused` on `ws`, past the state messages."""
    while (reply := next_text(ws))["type"] not in ("ack", "refused"):
        pass
    return reply


def answer(url: str, message: dict) -> dict:
    """Send `message` as a client of the preview at `url`, and read the
    `ack` or `refused` that answers it."""
    with connect(url) as ws:
        ws.send(json.dumps(message))
        return next_answer(ws)


@contextlib.contextmanager
def fake_engine(handler):
    """A websocket server on a free port whose connections `handler`
    serves. Yields its address."""
    with serve(handler, "127.0.0.1", 0) as server, ThreadPoolExecutor(1) as pool:
        pool.submit(server.serve_forever)
        try:
            yield f"ws://127.0.0.1:{server.socket.getsockname()[1]}/"
        finally:
            server.shutdown()  # else the pool waits for `serve_forever` without end


def resolving(monkeypatch, host: str, *addresses: str) -> None:
    """Make `host` resolve to `addresses`, as a resolver would."""
    real = socket.getaddrinfo

    def fake(name, port, *args, **kw):
        if name != host:
            return real(name, port, *args, **kw)
        return [(socket.AF_INET6 if ":" in a else socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port))
                for a in addresses]

    monkeypatch.setattr(socket, "getaddrinfo", fake)


# ---- push and set ---------------------------------------------------------------


def test_a_pushed_look_runs_and_is_acked_with_its_id():
    with engine(accept_looks=True) as (rig, url):
        pushed = push(url, COMET)
        assert rig.deck.current == "comet"
        assert rig.control.values()[SPEED] == 0.4
    assert pushed.ok and not pushed.dry_run
    assert pushed.answers == (Answer("1", "look", True),)
    assert pushed.connected == url and pushed.addresses == ("127.0.0.1",)
    sent = pushed.messages[0]
    assert (sent["type"], sent["id"], sent["fade"]) == ("look", "1", COMET["fade"])  # the look's own, said outright
    assert sent["look"]["layers"][0]["nodes"]["comet"]["args"] == {"pattern": "comet", "speed": 0.4}  # as authored


def test_a_look_goes_out_as_authored_so_the_engine_fills_in_its_own_defaults(tmp_path):
    """The engine's comet, from its --pattern-dir, has no `tail`: a look
    that never named one runs there, though the gallery comet has one."""
    (tmp_path / "comet.py").write_text(
        "import numpy as np\nfrom pewpew import Float, Pattern\n\n\nclass Comet(Pattern):\n"
        "    speed = Float(0.5, 0.0, 2.0)\n\n    def render(self, x, y, z, index):\n"
        "        return np.zeros((self.n, 3), dtype=np.float32)\n"
    )
    with engine(Catalog(tmp_path), accept_looks=True) as (rig, url):
        pushed = push(url, COMET)
        values = rig.control.values()
    assert pushed.answers == (Answer("1", "look", True),)
    assert values[SPEED] == 0.4 and "layers.base.comet.tail" not in values


def test_a_set_by_layered_path_follows_the_look_and_is_acked():
    with engine(accept_looks=True) as (rig, url):
        pushed = push(url, COMET, sets={SPEED: 0.7})
        wait_until(lambda: rig.control.values()[SPEED] == 0.7)
        alone = set_value(url, "layers.base.opacity", 0.5)
        wait_until(lambda: rig.control.values()["layers.base.opacity"] == 0.5)
    assert pushed.ok and pushed.answers == (Answer("1", "look", True), Answer("2", "set", True))
    assert alone.ok and alone.messages == ({"type": "set", "name": "layers.base.opacity", "value": 0.5, "id": "1"},)


def test_a_look_the_engine_refuses_comes_back_with_its_path_and_id_and_ends_the_write():
    # The check here allows any master; the engine holds it to its cap.
    with engine(accept_looks=True, cap=0.5) as (rig, url):
        pushed = push(url, {**COMET, "master": 0.8}, sets={SPEED: 0.7})
        assert rig.deck.current == "solid"
    assert not pushed.ok
    assert pushed.answers == (Answer("1", "look", False, "master must be within 0.0..0.5, got 0.8", "master"),)


def test_an_engine_that_takes_no_looks_is_written_to_by_neither_push_nor_set():
    with engine() as (rig, url):
        for write in (lambda: push(url, COMET), lambda: set_value(url, SPEED, 0.7)):
            with pytest.raises(Forbidden, match="engine lacks look; run it with --accept-looks or a newer pewpew"):
                write()
        assert rig.deck.current == "solid"


def test_an_engine_whose_hello_has_no_capabilities_lacks_look_and_gets_no_message():
    received = []

    def old_engine(conn):
        conn.send(json.dumps(OLD_HELLO))
        with contextlib.suppress(Exception):
            received.extend(conn)

    with fake_engine(old_engine) as url, pytest.raises(Forbidden, match="engine lacks look"):
        push(url, COMET)
    assert received == []


def test_an_engine_that_closes_mid_write_is_unreachable():
    """It acks the look and closes before the set: the set is not sent."""

    def closing_engine(conn):
        conn.send(json.dumps({**OLD_HELLO, "capabilities": ["ack", "look"]}))
        message = json.loads(conn.recv())
        conn.send(json.dumps({"type": "ack", "id": message["id"], "control": message["type"]}))
        conn.close()

    with fake_engine(closing_engine) as url, pytest.raises(Unreachable, match="closed the connection"):
        push(url, COMET, sets={SPEED: 0.7})


def test_a_send_after_the_engine_closed_is_unreachable():
    with fake_engine(lambda conn: (conn.send(json.dumps(OLD_HELLO)), conn.close())) as url, Client(url) as client:
        assert client.wait(lambda: client.ended, 5.0)
        with pytest.raises(Unreachable, match=r"closed the connection, so the set was not sent: observe the engine"):
            client.send({"type": "set", "name": SPEED, "value": 0.7})


@pytest.mark.parametrize("dry_run", [True, False])
def test_a_set_the_look_would_refuse_is_refused_here_before_any_socket(dry_run, audit_log):
    """Each set is checked against the knobs of the look it follows, so
    no write stops half done at a set the engine would refuse."""
    with pytest.raises(Refused) as bad:
        push("ws://127.0.0.1:9/", COMET, sets={"layers.base.comet.nope": 1, SPEED: 99}, dry_run=dry_run)
    assert [(p.path, p.code) for p in bad.value.problems] == [
        ("layers.base.comet.nope", Code.BAD_REF), (SPEED, Code.OUT_OF_RANGE)]  # as a route to it is
    assert "must be within 0.0..2.0, got 99" in bad.value.problems[1].reason
    assert not audit_log.exists()


def test_a_look_with_problems_is_refused_here_before_any_socket(audit_log):
    with pytest.raises(Refused) as bad:
        push("ws://127.0.0.1:9/", {**COMET, "layers": [{**COMET["layers"][0], "opacity": 3}]})
    assert [p.path for p in bad.value.problems] == ["layers.base.opacity"]
    with pytest.raises(Refused) as pathed:
        push("ws://127.0.0.1:9/", with_pattern("/tmp/x.py"))
    (found,) = pathed.value.problems
    assert found.path == "layers.base.x.pattern" and "/tmp" not in found.reason
    with pytest.raises(Refused, match="fade must be within 0.0..600.0"):
        push("ws://127.0.0.1:9/", COMET, fade=-1)
    assert not audit_log.exists()


# ---- tier 1 ------------------------------------------------------------------------


def test_tier_one_writes_only_to_loopback_unless_the_address_is_allowed(audit_log):
    for write in (lambda **kw: push("ws://192.168.1.50:7447/", COMET, **kw),
                  lambda **kw: set_value("ws://192.168.1.50:7447/", SPEED, 0.7, **kw)):
        for dry_run in (True, False):
            with pytest.raises(Forbidden, match=r"^192\.168\.1\.50 is not this machine: tier 1 writes only to an "
                                                r"engine on this machine .* --allow-host 192\.168\.1\.50"):
                write(dry_run=dry_run)
    assert not audit_log.exists()
    planned = push("ws://192.168.1.50:7447/", COMET, dry_run=True, allow_hosts=["192.168.1.50"])
    assert planned.ok and planned.addresses == ("192.168.1.50",)


def test_a_host_that_resolves_to_loopback_and_another_address_is_refused(monkeypatch):
    resolving(monkeypatch, "bench.test", "127.0.0.1", "10.0.0.7")
    with pytest.raises(Forbidden, match=r"^bench\.test resolves to 10\.0\.0\.7, which is not this machine: tier 1"):
        push("ws://bench.test:7447/", COMET, dry_run=True)


def test_the_write_goes_to_the_address_that_was_checked(monkeypatch):
    with engine(accept_looks=True) as (_, url):
        port = url.rsplit(":", 1)[1].rstrip("/")
        resolving(monkeypatch, "bench.test", "127.0.0.1")
        pushed = push(f"ws://bench.test:{port}/", COMET)
    # The preview refuses a Host that is a name, so only the checked address could connect.
    assert pushed.ok and pushed.url == f"ws://bench.test:{port}/" and pushed.connected == url


def test_a_dry_run_checks_and_plans_and_opens_no_socket(monkeypatch, audit_log):
    class NoSocket:
        def __init__(self, *args, **kw):
            raise AssertionError("a dry run opened a socket")

    monkeypatch.setattr(socket, "socket", NoSocket)
    pushed = push("ws://127.0.0.1:9/", COMET, fade=1.5, sets={SPEED: 0.7}, dry_run=True)
    assert pushed.ok and pushed.dry_run and pushed.answers == () and pushed.connected is None and pushed.audit is None
    assert [(m["type"], m["id"]) for m in pushed.messages] == [("look", "1"), ("set", "2")]
    assert pushed.messages[0]["fade"] == 1.5
    assert not audit_log.exists()


def test_the_audit_record_is_written_before_the_first_byte(monkeypatch, audit_log):
    logged_at_connect = []
    real = Client.__init__

    def spy(self, *args, **kw):
        logged_at_connect.append(audit_log.read_text() if audit_log.exists() else "")
        real(self, *args, **kw)

    monkeypatch.setattr(Client, "__init__", spy)
    with engine(accept_looks=True) as (_, url):
        pushed = push(url, COMET, argv=["push", url, "comet.look.json"])
    record = json.loads(logged_at_connect[0])
    assert (record["action"], record["argv"], record["url"]) == ("push", ["push", url, "comet.look.json"], url)
    assert record["messages"] == list(pushed.messages) and pushed.audit == str(audit_log)


def test_an_engine_that_is_not_there_is_unreachable(audit_log):
    sink = preview_sink(line(4))
    with sink:
        port = sink.port
    with pytest.raises(Unreachable, match=f"nothing answered at ws://127.0.0.1:{port}/"):
        push(f"ws://127.0.0.1:{port}/", COMET)


# ---- the engine's answers on the wire ------------------------------------------


def test_the_engine_answers_every_message_with_an_id_and_only_those():
    with engine(accept_looks=True) as (_, url):
        assert answer(url, {"type": "master", "id": 5, "value": 0.5}) == {"type": "ack", "id": 5, "control": "master"}
        bad = answer(url, {"type": "look", "id": "a", "look": layered("comet", {"speed": 99})})
        assert (bad["control"], bad["name"], bad["id"]) == ("look", SPEED, "a")
        assert "must be within" in bad["reason"]
        typo = answer(url, {"type": "sett", "id": 9, "name": SPEED, "value": 1})
        assert (typo["type"], typo["control"], typo["id"], typo["name"]) == ("refused", "sett", 9, None)
        assert typo["reason"].startswith("unknown control 'sett'; controls: set, pick, add_layer,")
        for message in ({"type": 7, "id": "a"}, {"typ": "look", "id": "a"}):  # no text type, but an id to answer
            untyped = answer(url, message)
            assert (untyped["type"], untyped["control"], untyped["id"]) == ("refused", None, "a")
            assert untyped["reason"].startswith(f"unknown control {message.get('type')!r}; controls: set, pick,")
        with connect(url) as ws:  # without an id, an unknown type is passed over and an accepted one unanswered
            ws.send(json.dumps({"type": "sett"}))
            ws.send(json.dumps({"type": "master", "value": 0.4}))
            ws.send(json.dumps({"type": "master", "value": 7}))
            reply = next_answer(ws)
            assert (reply["control"], reply["id"], reply["name"]) == ("master", None, None)


def test_a_look_that_names_a_file_is_refused_with_its_path_and_id():
    with engine(accept_looks=True) as (rig, url):
        reply = answer(url, {"type": "look", "id": 3, "look": with_pattern("/tmp/x.py")})
        assert rig.deck.current == "solid"
    assert (reply["type"], reply["control"], reply["id"]) == ("refused", "look", 3)
    assert reply["name"] == "layers.base.x.pattern"
    assert "/tmp" not in reply["reason"] and "never by file" in reply["reason"]


def test_a_program_look_runs_but_a_pattern_node_named_by_file_is_refused_inside_it():
    """A pushed look's program runs node by node; a pattern node anywhere
    in it is named by pick name, never by file."""
    nodes = {"p": {"op": "pattern", "args": {"pattern": "/tmp/x.py"}},
             "fold": {"op": "mirror", "in": ["p"]}, "tint": {"op": "hue", "in": ["fold"]}}
    with engine(mapping=grid(4, 4), accept_looks=True) as (rig, url):
        assert answer(url, {"type": "look", "id": 1, "look": TIDE}) == {"type": "ack", "id": 1, "control": "look"}
        assert rig.control.values()["layers.base.fold.sides"] == 5
        reply = answer(url, {"type": "look", "id": 2, "look": {"layers": [{"id": "base", "nodes": nodes}]}})
        assert rig.control.values()["layers.base.fold.sides"] == 5  # the refused look never started
    assert (reply["type"], reply["id"], reply["name"]) == ("refused", 2, "layers.base.p.pattern")
    assert "/tmp" not in reply["reason"] and "never by file" in reply["reason"]


def test_a_program_look_checks_renders_verifies_and_pushes(tmp_path, capsys):
    """End to end: a two-layer look whose bottom layer is a program passes
    `fx check`, renders with `fx render --json`, passes `verify looks`,
    and a live engine that takes looks acks it."""
    file = tmp_path / "tide.look.json"
    file.write_text(filed(TIDE))
    assert main(["fx", "check", str(file)]) == 0
    assert capsys.readouterr().out == "ok: 1 look\n"
    assert main(["fx", "render", str(file), "--map", "grid:16x16", "--seconds", "1", "--json"]) == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["spec"]["look"]["layers"][0]["nodes"]["fold"]["args"] == {"sides": 5, "plane": "auto"}
    assert rendered["metrics"]["black_fraction"] < 1.0
    assert main(["verify", "looks", str(file), "--map", "grid:16x16", "--seconds", "1"]) == 0
    assert capsys.readouterr().out.startswith("PASS ")
    with engine(mapping=grid(4, 4), accept_looks=True) as (rig, url):
        pushed = push(url, file)
        assert rig.deck.current == "program"
        assert rig.control.values()["layers.sparks.comet.speed"] == 0.6
    assert pushed.ok and pushed.answers == (Answer("1", "look", True),)


def test_a_modulated_look_pushes_with_a_set_on_a_signal_and_a_bad_route_is_refused_by_its_path():
    """A look's signals and routes cross the wire with it; a set on a
    signal's knob is checked before anything is sent, and the engine names
    a route that reaches no knob by its place in the look."""
    tide = {**TIDE, "signals": {"breath": {"op": "lfo", "args": {"rate": 0.1}}},
            "routes": [{"source": "breath", "path": "layers.base.tint.shift", "depth": 40}]}
    with pytest.raises(Refused, match="signals.breath.rate must be within 0.0..10.0, got 20"):
        push("ws://127.0.0.1:9/", tide, sets={"signals.breath.rate": 20}, dry_run=True)
    with engine(mapping=grid(4, 4), accept_looks=True) as (rig, url):
        pushed = push(url, tide, sets={"signals.breath.rate": 0.5})
        wait_until(lambda: rig.control.values().get("signals.breath.rate") == 0.5)
        assert rig.control.state()["stack"]["routes"] == tide["routes"]
        bad = {**tide, "routes": [{**tide["routes"][0], "path": "layers.base.tint.palette"}]}
        reply = answer(url, {"type": "look", "id": "r", "look": bad})
    assert pushed.ok and [a.control for a in pushed.answers] == ["look", "set"]
    assert (reply["type"], reply["name"]) == ("refused", "routes[0].path")
    assert "layers.base.tint.palette cannot be modulated: it is a palette" in reply["reason"]


def test_a_look_refusal_names_no_folder(tmp_path):
    private = tmp_path / "private-folder-xyz"
    private.mkdir()
    (private / "broken.py").write_text("def (:\n")
    rig = aura_rig(mapping=line(4), catalog=Catalog(private), accept_looks=True, timeout=2.0)
    with serving(rig.control, rig.calls) as (_, ws, _):
        for i, spec in enumerate(("broken", str(private / "mine.py"), f"{private}/mine", "nosuch")):
            ws.send(json.dumps({"type": "look", "id": i, "look": with_pattern(spec)}))
            reply = next_of(ws, "refused")
            assert (reply["id"], reply["name"]) == (i, "layers.base.x.pattern")
            assert str(private) not in reply["reason"] and "private-folder" not in reply["reason"], reply


def test_a_pushed_look_is_no_saved_look_until_a_save_keeps_it(tmp_path):
    path = tmp_path / "looks.json"
    rig = aura_rig(Solid, mapping=line(4), catalog=Catalog(), looks={"blue": look("wash")}, current="blue",
                   path=path, accept_looks=True)
    assert rig.looks.restore() is None
    with LoopThread(rig.calls):
        assert rig.control.look(COMET) is None
        assert rig.looks.book.current is None and list(rig.looks.book.looks) == ["blue"]
        assert rig.control.save("pushed") is None
    saved = json.loads(path.read_text())["looks"]["pushed"]
    assert saved["layers"][0]["nodes"]["comet"]["args"]["speed"] == 0.4


def test_a_pushed_look_leaves_the_last_recalled_look_out_of_the_fade(tmp_path):
    """The looks name no look as fading while a pushed look fades in: it
    has no name, and the last look recalled is not the one fading."""
    rig = aura_rig(Solid, mapping=line(4), catalog=Catalog(), looks={"blue": look("wash", fade=0.5)},
                   path=tmp_path / "looks.json", accept_looks=True)
    assert rig.looks.recall("blue") is None
    rig.frame(1.0)  # the recall's fade is over
    with LoopThread(rig.calls):
        assert rig.control.look(COMET, 2.0) is None
    assert rig.fader.fading
    state = rig.looks.state()
    assert (state["current"], state["fading"], state["progress"]) == (None, None, None)
    rig.frame(1.5)
    assert (rig.control.state()["fading"], rig.control.state()["progress"]) == (True, 0.25)  # the aura's own


def test_a_dry_run_names_the_fade_the_engine_will_run():
    pushed = push("ws://127.0.0.1:9/", {**COMET, "fade": 3.0}, dry_run=True)
    assert pushed.messages[0]["fade"] == 3.0  # the look's own


@pytest.mark.parametrize("path", ["bogus", "layers.nope", "layers.base.comet", "signals.breath", "layers.Base.x.y"])
def test_a_set_whose_address_has_no_knobs_form_is_refused_before_any_socket(path, audit_log):
    with pytest.raises(Refused) as caught:
        set_value("ws://127.0.0.1:9/", path, 1, dry_run=True)
    (problem,) = caught.value.problems
    assert (problem.path, problem.code) == (path, Code.BAD_REF) and "is not a knob's address" in problem.reason
    for good in (SPEED, "layers.base.opacity", "signals.breath.rate", "layers.base.comet.color.h"):
        assert set_value("ws://127.0.0.1:9/", good, 1, dry_run=True).ok


def test_a_look_the_loop_takes_too_late_is_refused_and_never_starts():
    """No loop drains the calls in time: the client hears the look was
    refused, so it must never start after that."""
    rig = aura_rig(Solid, mapping=line(4), catalog=Catalog(), accept_looks=True, timeout=0.05)
    assert rig.control.look(COMET) == BUSY
    rig.calls.drain()
    assert rig.deck.current == "solid"


def test_a_pushed_look_ends_a_running_fade_and_fades_from_its_target():
    rig = aura_rig(Solid, mapping=line(4), catalog=Catalog(), accept_looks=True)
    assert rig.deck.recall(look("wash"), 2.0) is None and rig.fader.fading
    with LoopThread(rig.calls):
        assert rig.control.look(COMET, 1.0) is None
    assert rig.fader.fading and rig.deck.current == "comet"


# ---- the command line --------------------------------------------------------------


def test_push_prints_its_result_and_exits_by_outcome(tmp_path, monkeypatch, capsys):
    file = tmp_path / "comet.look.json"
    file.write_text(filed(COMET))
    kept = []
    real = remote_control.push
    monkeypatch.setattr(remote_control, "push", lambda *a, **kw: kept.append(real(*a, **kw)) or kept[-1])
    with engine(accept_looks=True) as (_, url):
        assert main(["push", url, str(file), "--set", f"{SPEED}=0.7", "--json"]) == 0
        assert json.loads(capsys.readouterr().out) == kept[-1].to_json()
        assert main(["push", url, str(file), "--fade", "0.5", "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert out.startswith(f"dry run, nothing sent to {url} (127.0.0.1):") and "look of 1 layer, fading 0.5 s" in out
    with engine(accept_looks=True, cap=0.5) as (_, url):
        file.write_text(filed({**COMET, "master": 0.8}))
        assert main(["push", url, str(file)]) == 4
        assert "look of 1 layer, fading 0 s: refused at master: master must be within" in capsys.readouterr().out
    file.write_text(filed(with_pattern("comett")))
    assert main(["push", "ws://127.0.0.1:9/", str(file)]) == 1
    assert "did you mean 'comet'?" in capsys.readouterr().err
    file.write_text(filed(COMET))
    assert main(["push", "ws://10.0.0.7:7447/", str(file), "--dry-run"]) == 4
    assert main(["push", "ws://10.0.0.7:7447/", str(file), "--dry-run", "--allow-host", "10.0.0.7"]) == 0
    assert main(["push", "ws://127.0.0.1:9/", str(file)]) == 3


def test_a_set_of_nan_is_text_and_refused_so_the_output_stays_json(tmp_path, capsys):
    file = tmp_path / "comet.look.json"
    file.write_text(filed(COMET))
    for value in ("NaN", "Infinity", "-Infinity"):
        assert main(["push", "ws://127.0.0.1:9/", str(file), "--set", f"{SPEED}={value}", "--dry-run", "--json"]) == 1
        out = json.loads(capsys.readouterr().out, parse_constant=lambda name: pytest.fail(f"{name} in the output"))
        assert out["problems"][0]["reason"] == f"{SPEED} takes a number, got {value!r}"


def test_a_write_the_audit_log_cannot_record_is_refused_by_tier_one(tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("")
    monkeypatch.setenv("PEWPEW_AUDIT_LOG", str(blocker / "audit.jsonl"))  # its folder is a file
    file = tmp_path / "comet.look.json"
    file.write_text(filed(COMET))
    with pytest.raises(Forbidden, match="cannot write the audit record .*, so nothing was sent"):
        push("ws://127.0.0.1:9/", COMET)
    assert main(["push", "ws://127.0.0.1:9/", str(file)]) == 4
    assert "point PEWPEW_AUDIT_LOG at a file it can write" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["push", "ws://127.0.0.1:7447/", "x.json", "--allow-host", "bench.local"],
    ["push", "ws://127.0.0.1:7447/", "x.json", "--fade", "-1"],
    ["push", "ws://127.0.0.1:7447/", "x.json", "--set", "speed"],
    ["push", "ftp://127.0.0.1:7447/", "x.json"],
])
def test_a_bad_argument_is_a_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2 and "push: error:" in capsys.readouterr().err
