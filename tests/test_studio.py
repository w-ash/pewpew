"""The studio backend, driven through FastAPI's TestClient.

Most tests inject a fake rig: `create_app` takes the catalog, compile function
and assemblies as arguments. The tests marked "real rig" use the
defaults, `pewpew.rig.load_catalog` and `compile_rig`.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import struct
import sys
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx2")

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from fakes import FakeTime
from pewpew.power import POWER_HZ, Limited, PowerCap, PowerLimiter
from pewpew.rig import EXAMPLES, load_arrangement, load_catalog
from pewpew.rig import models as rig_models
from pewpew.sinks.preview import _MESSAGES, message, status_state
from pewpew.sinks.sink import DISPLAY_GAMMA, to_display_u8
from pewpew.studio.app import create_app
from pewpew.studio.limits import MAX_FIXTURES, Limits, RateLimiter, address_key, client_ip
from pewpew.studio.session import START, FramePayload, Session, example_looks, start_looks
from pewpew.studio.store import SqliteStore, arrangement_id, canonical_json
from pewpew.studio.transport import Outbox

FPS = 120.0  # fast enough that a test waits milliseconds, not seconds
ROOT = Path(__file__).resolve().parents[1]
LOOKS = example_looks(ROOT / "examples")
STARTS = start_looks(LOOKS)  # as the app gives them: the start look first
START_LOOK = STARTS[START]
POWER = list(_MESSAGES).index("power")  # where a frame's texts hold the power reading
STRIP = np.column_stack([np.linspace(0, 1, 8), np.zeros(8), np.zeros(8)]).astype(np.float32)


class FakeRigError(ValueError):
    def __init__(self, issues):
        super().__init__(issues[0]["message"])
        self.issues = issues


def plane(n: int) -> np.ndarray:
    """`n` points over two axes, in two rows: the example looks fold a plane, so a strip will not do."""
    return np.column_stack([np.linspace(0.0, 1.0, n), np.arange(n) % 2, np.zeros(n)]).astype(np.float32)


class FakeRig:
    def __init__(self, n: int, issues=()):
        self.n = n
        self.mapping = plane(n)
        self.catalog_digest = "digest-1"
        self.issues = issues
        self.report = None
        self.to_json_calls = 0

    def to_json(self):
        self.to_json_calls += 1
        return {"n": self.n, "issues": list(self.issues), "report": None, "catalog_digest": self.catalog_digest}


class FakeLimiter:
    """Caps nothing to the eye, and reports fixed readings."""

    cap = PowerCap(max_brightness=0.5)

    def __call__(self, frame):
        return Limited(frame, 1.0, 1.5, 2.0)


class PoweredRig(FakeRig):
    def limiter(self):
        return FakeLimiter()


class FakeCatalog:
    def to_json(self):
        return {
            "digest": "cat-1",
            "fixture_types": [{"id": "bar", "name": "Bar"}],
            "attachment_types": [{"id": "point", "name": "Point"}],
            "controllers": [],
            "psus": [],
            "cables": [],
            "presets": [],
        }


def fake_compile(arrangement, catalog):
    if "bad" in arrangement:
        raise FakeRigError([{"level": "error", "code": "bad", "message": "bad arrangement", "ref": None}])
    return (PoweredRig if arrangement.get("power") else FakeRig)(arrangement.get("n", 8))


def fake_assembly(type_id, catalog):
    return "d" + type_id, b"glTF-" + type_id.encode()


def state_of(client):
    return cast(Any, client.app).state


def make_app(**kw):
    """The app with a fake rig; keyword arguments override any collaborator."""
    defaults = {
        "catalog": FakeCatalog(),
        "compile": fake_compile,
        "store": SqliteStore(":memory:"),
        "assemblies": fake_assembly,
        "web_dist": Path("/nonexistent"),
        "fps": FPS,
    }
    return create_app(**{**defaults, **kw})


@pytest.fixture
def client():
    with TestClient(make_app()) as c:
        yield c


def read_until(ws, pred, limit=400):
    """Receive until `pred(message)` holds; text arrives as dicts, frames as bytes."""
    for _ in range(limit):
        event = ws.receive()
        if event["type"] == "websocket.close":
            raise AssertionError("socket closed")
        msg = json.loads(event["text"]) if event.get("text") is not None else event["bytes"]
        if pred(msg):
            return msg
    raise AssertionError("message never arrived")


def is_type(kind):
    return lambda m: isinstance(m, dict) and m.get("type") == kind


def is_frame(m):
    return isinstance(m, bytes)


def header(frame):
    return struct.unpack("<fI", frame[:8])


def first_knob(ws, kind="float"):
    """The first knob of `kind` the session declares."""
    return next(k for k in read_until(ws, is_type("declare"))["params"] if k["kind"] == kind)


def session_of(client) -> Session:
    (session,) = state_of(client).sessions.sessions()
    return session


# -- HTTP ----------------------------------------------------------------------


def test_health_live(client):
    assert client.get("/health/live").json() == {"ok": True}


def test_catalog_adds_digest_and_assembly_url(client):
    body = client.get("/api/catalog").json()
    bar = body["fixture_types"][0]
    assert bar["digest"] == "dbar" and bar["assembly_url"] == "/api/assembly/dbar.glb"
    assert body["attachment_types"][0]["assembly_url"] == "/api/assembly/dpoint.glb"


def test_assembly_is_immutable_and_unknown_digest_is_404(client):
    r = client.get("/api/assembly/dbar.glb")
    assert r.content == b"glTF-bar"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get("/api/assembly/nope.glb").status_code == 404


def test_looks_lists_each_example_look_by_its_file_name(client):
    body = client.get("/api/looks").json()
    files = sorted(ROOT.glob("examples/*.look.json"))
    assert sorted(body) == [path.name.removesuffix(".look.json") for path in files]
    tide = json.loads((ROOT / "examples" / "tide.look.json").read_text())
    assert body["tide"] == tide["looks"][tide["current"]]


def test_an_app_without_the_start_look_does_not_start(tmp_path):
    with pytest.raises(RuntimeError, match="tide"):
        create_app(examples=tmp_path)


def test_compile_success_and_422(client):
    ok = client.post("/api/compile", json={"n": 5})
    assert ok.status_code == 200 and ok.json()["n"] == 5
    bad = client.post("/api/compile", json={"bad": 1})
    assert bad.status_code == 422
    assert bad.json()["issues"][0]["code"] == "bad"


def test_save_and_load_round_trip_with_deterministic_id(client):
    a = client.post("/api/arrangements", json={"n": 3, "name": "x"}).json()["id"]
    b = client.post("/api/arrangements", json={"name": "x", "n": 3}).json()["id"]
    assert a == b and len(a) == 22
    text = '{"n":3,"name":"x"}'
    want = base64.urlsafe_b64encode(hashlib.sha256(text.encode()).digest()[:16]).decode().rstrip("=")
    assert a == want
    assert client.get(f"/api/arrangements/{a}").json() == {"n": 3, "name": "x"}
    assert client.get("/api/arrangements/" + "A" * 22).status_code == 404
    assert client.get("/api/arrangements/short").status_code == 404


def test_save_rejects_an_invalid_arrangement(client):
    assert client.post("/api/arrangements", json={"bad": 1}).status_code == 422


def test_save_rate_limit_per_address():
    with TestClient(make_app(limits=Limits(saves_per_minute=2))) as c:
        h = {"Fly-Client-IP": "1.1.1.1"}
        assert c.post("/api/arrangements", json={"n": 1}, headers=h).status_code == 200
        assert c.post("/api/arrangements", json={"n": 2}, headers=h).status_code == 200
        r = c.post("/api/arrangements", json={"n": 3}, headers=h)
        assert r.status_code == 429 and "2 saves per minute" in r.json()["detail"]
        assert "retry-after" in r.headers
        assert c.post("/api/arrangements", json={"n": 3}, headers={"Fly-Client-IP": "2.2.2.2"}).status_code == 200


def test_save_limiter_window_slides():
    t = [0.0]
    lim = RateLimiter(1, now=lambda: t[0])
    assert lim.allow("a") is None
    assert lim.allow("a") is not None
    t[0] = 61.0
    assert lim.allow("a") is None


def test_body_over_256_kib_is_413(client):
    r = client.post(
        "/api/compile", content=b"{" + b" " * (256 * 1024) + b"}", headers={"content-type": "application/json"}
    )
    assert r.status_code == 413 and "262144" in r.json()["detail"]


def test_more_than_200_fixtures_is_refused(client):
    r = client.post("/api/arrangements", json={"fixtures": [{}] * 201})
    assert r.status_code == 422
    assert "200 fixtures" in r.json()["issues"][0]["message"]


def test_client_ip_prefers_fly_header():
    assert client_ip({"fly-client-ip": "9.9.9.9"}, "10.0.0.1") == "9.9.9.9"
    assert client_ip({}, "10.0.0.1") == "10.0.0.1"


def test_spa_index_fallback(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "a.js").write_text("1")
    (tmp_path / "index.html").write_text("<html>spa</html>")
    with TestClient(make_app(web_dist=tmp_path)) as c:
        assert "spa" in c.get("/").text
        assert "spa" in c.get("/a/abc").text
        assert c.get("/assets/a.js").text == "1"
        assert c.get("/api/unknown").status_code == 404
        assert c.get("/../../etc/passwd").status_code == 404


def test_store_is_idempotent():
    s = SqliteStore(":memory:")
    s.init()
    s.init()
    text = canonical_json({"b": 1, "a": [2]})
    assert text == '{"a":[2],"b":1}'
    s.put(arrangement_id(text), text)
    s.put(arrangement_id(text), text)
    try:
        assert s.get(arrangement_id(text)) == text and s.get("x" * 22) is None
    finally:
        s.close()  # an unclosed connection warns when collected, in whichever test runs then


# -- websocket -------------------------------------------------------------------


def test_hello_then_frames_of_the_right_length(client):
    with client.websocket_connect("/ws/session") as ws:
        hello = json.loads(ws.receive_text())
        assert hello["type"] == "hello" and hello["n"] == hello["total"] == 256
        assert hello["display_gamma"] == DISPLAY_GAMMA and hello["build"] is None
        assert hello["capabilities"] == ["ack", "look"] and hello["room"] is None and not hello["is3d"]
        assert len(hello["positions"]) == 256
        first = read_until(ws, is_frame)
        second = read_until(ws, is_frame)
        assert len(first) == 8 + 3 * hello["n"]
        assert header(second)[1] > header(first)[1]


def test_bind_keeps_t_and_changes_n(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        before = None
        for _ in range(5):
            before = read_until(ws, is_frame)
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"n": 16}}))
        layout = read_until(ws, is_type("layout"))
        assert layout["n"] == layout["total"] == 16 and len(layout["positions"]) == 16
        after = read_until(ws, lambda m: is_frame(m) and len(m) == 8 + 48)
        assert header(after)[0] > header(before)[0] > 0


def test_bind_of_a_bad_arrangement_is_refused_and_the_run_goes_on(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"bad": 1}}))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "bind" and refused["issues"][0]["code"] == "bad"
        read_until(ws, is_frame)


def test_a_look_message_is_applied_and_acked(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "fade": 0, "id": 7}))
        assert read_until(ws, is_type("ack")) == {"type": "ack", "id": 7, "control": "look"}
        want = [layer["id"] for layer in LOOKS["warp-lane"]["layers"]]
        aura = read_until(ws, lambda m: is_type("aura")(m) and [x["id"] for x in m["stack"]["layers"]] == want)
        assert aura["fading"] is False
        ws.send_text(json.dumps({"type": "look", "look": {"layers": "/etc/passwd"}, "id": 8}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["id"]) == ("look", 8) and "/etc" not in refused["reason"]


def test_an_unknown_control_is_refused_with_its_id_and_passed_over_without(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pattern", "name": "plasma"}))
        ws.send_text(json.dumps({"type": "pattern", "name": "plasma", "id": "a"}))
        refused = read_until(ws, lambda m: is_type("refused")(m) or is_type("ack")(m))
        assert (refused["type"], refused["control"], refused["id"]) == ("refused", "pattern", "a")
        assert "unknown control" in refused["reason"]


def test_requests_that_need_a_looks_file_or_boards_are_refused(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        for i, request in enumerate([{"type": "save", "name": "x"}, {"type": "keep"}, {"type": "scan"},
                                     {"type": "blink", "fixture": "a"}]):
            ws.send_text(json.dumps({**request, "id": i}))
            refused = read_until(ws, is_type("refused"))
            assert (refused["control"], refused["id"]) == (request["type"], i)


def test_refused_set_names_the_range_and_never_a_path_and_the_loop_survives(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        knob = first_knob(ws)
        ws.send_text(json.dumps({"type": "set", "name": knob["name"], "value": 1e9}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["name"]) == ("set", knob["name"])
        assert "/" not in refused["reason"] and ".py" not in refused["reason"]
        ws.send_text(json.dumps({"type": "set", "name": ["unhashable"], "value": 1, "id": 1}))
        assert read_until(ws, is_type("refused"))["id"] == 1
        read_until(ws, is_frame)
        assert session_of(client).alive


def test_a_set_by_address_reaches_the_layer_and_is_echoed_in_params(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        name = "layers.sparks.sparks.rate"
        ws.send_text(json.dumps({"type": "set", "name": name, "value": 12.5, "id": 3}))
        assert read_until(ws, is_type("ack"))["control"] == "set"
        read_until(ws, lambda m: is_type("params")(m) and m["values"][name] == 12.5)
        layer = session_of(client).control.values()
        assert layer[name] == 12.5


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_pause_and_resume_freeze_engine_time(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        read_until(ws, is_frame)
        session = state_of(client).sessions.sessions()[0]
        ws.send_text(json.dumps({"type": "pause"}))
        assert wait_for(lambda: session.paused)
        time.sleep(0.1)
        t0 = session.t
        time.sleep(0.15)
        assert session.t == t0
        ws.send_text(json.dumps({"type": "resume"}))
        assert wait_for(lambda: session.t > t0)


def test_idle_session_pauses_and_a_message_resumes_it():
    with TestClient(make_app(idle_timeout_s=0.2)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        session = state_of(c).sessions.sessions()[0]
        assert wait_for(lambda: session.paused)
        ws.send_text(json.dumps({"type": "set", "name": "x", "value": 1}))
        assert wait_for(lambda: not session.paused)


def test_power_message_when_the_rig_reports_an_estimate(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"n": 4, "power": True}}))
        power = read_until(ws, is_type("power"))
        assert (power["watts"], power["uncapped_watts"]) == (1.5, 2.0)


def test_per_address_socket_limit():
    with TestClient(make_app()) as c:
        h = {"Fly-Client-IP": "3.3.3.3"}
        opened = [c.websocket_connect("/ws/session", headers=h) for _ in range(3)]
        sockets = [o.__enter__() for o in opened]
        try:
            for ws in sockets:
                assert json.loads(ws.receive_text())["type"] == "hello"
            with c.websocket_connect("/ws/session", headers=h) as fourth:
                msg = json.loads(fourth.receive_text())
                assert msg["type"] == "refused" and "3 open sessions" in msg["reason"]
            with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "4.4.4.4"}) as other:
                assert json.loads(other.receive_text())["type"] == "hello"
        finally:
            for o in opened:
                o.__exit__(None, None, None)


def test_global_session_cap():
    with (
        TestClient(make_app(limits=Limits(max_sessions=1))) as c,
        c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "5.5.5.5"}) as a,
    ):
        a.receive_text()
        with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "6.6.6.6"}) as b:
            assert "1 live sessions" in json.loads(b.receive_text())["reason"]


def test_oversized_websocket_message_is_refused(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text("x" * (256 * 1024 + 1))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "message" and "262144" in refused["reason"]


def test_closing_the_socket_stops_the_session_thread(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        session = state_of(client).sessions.sessions()[0]
    assert wait_for(lambda: not session.alive)
    assert wait_for(lambda: len(state_of(client).sessions) == 0)


def test_close_all_stops_every_loop_inside_the_deadline(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        session = state_of(client).sessions.sessions()[0]
        start = time.monotonic()
        state_of(client).sessions.close_all()
        assert not session.alive and time.monotonic() - start < 5


# -- the real rig ------------------------------------------------------------------

GOLDEN = json.loads((EXAMPLES / "golden-rings.json").read_text())


def real_app(**kw):
    """The app with its default rig: `load_catalog` and `compile_rig`."""
    kw.setdefault("fps", FPS)
    return create_app(store=SqliteStore(":memory:"), web_dist=Path("/nonexistent"), **kw)


def ring(count, **extra):
    group = {"id": "big", "preset": "ring", "type": "clen-rgbw-bar-1m", "count": count, "start_radius_m": 1.0}
    return {"format": "pewpew.arrangement", "version": 1, "groups": [{**group, **extra}]}


def nested(depth):
    out = inner = []
    for _ in range(depth):
        inner.append([])
        inner = inner[0]
    return out


def test_real_rig_compiles_and_binds_golden_rings():
    with TestClient(real_app()) as c:
        r = c.post("/api/compile", json=GOLDEN)
        assert r.status_code == 200
        body = r.json()
        assert body["n"] == 48 * 64 and body["catalog_digest"] == load_catalog().digest
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": GOLDEN}))
            assert read_until(ws, is_type("layout"))["n"] == 3072
            assert len(read_until(ws, is_frame)) == 8 + 3 * 3072


# -- coalesced binds (review finding 1) ----------------------------------------------


class RecordingSink:
    def __init__(self):
        self.controls = []
        self.frames = []

    def frame(self, payload):
        self.frames.append(payload)

    def control(self, message):
        self.controls.append(message)

    def layout(self, message):
        self.controls.append(message)

    def closed(self):
        pass


def stepped(sink, **kw) -> Session:
    """A session in the start look that a test steps itself, paced on fake time, so no slot is
    skipped; never started."""
    session = Session(sink, kw.pop("looks", STARTS), **{"fps": FPS, **kw})
    clock = FakeTime()
    session._loop._now, session._loop._sleep = clock.now, clock.sleep
    return session


def test_pending_binds_coalesce_into_one_closure():
    sink = RecordingSink()
    session = stepped(sink)
    for n in range(4, 500):
        session.bind(plane(n), limiter=None)
    assert len(session._aura.calls._queue) == 1  # one apply closure for every bind above
    session._loop.run(frames=1)
    assert session.n == 499
    assert [json.loads(m)["type"] for m in sink.controls] == ["layout"]
    layout, hello = json.loads(sink.controls[0]), json.loads(session.hello())
    assert layout["n"] == 499 and hello["n"] == 499  # a hello after a bind describes the bound rig
    assert hello == {**layout, "type": "hello", "display_gamma": DISPLAY_GAMMA, "build": None,
                     "capabilities": ["ack", "look"]}


def test_a_bind_the_look_cannot_run_on_cuts_to_the_first_look_that_runs_and_says_so():
    sink = RecordingSink()
    session = stepped(sink)
    session.bind(STRIP, limiter=None)  # tide folds a plane: a strip has none
    session._loop.run(frames=2)
    assert [json.loads(m)["type"] for m in sink.controls] == ["layout"] and session.n == 8
    first = next(name for name, look in STARTS.items() if name != START)  # copper-tide runs on a strip
    stack = json.loads(sink.frames[-1].texts[4])["stack"]
    assert [layer["id"] for layer in stack["layers"]] == [layer.id for layer in STARTS[first].layers]
    status = json.loads(sink.frames[-1].texts[0])
    assert status["source"] == "bind" and f"so {first} runs" in status["error"] and "kaleid" in status["error"]
    assert session._aura.deck.recall(STARTS["warp-lane"]) is None  # another look: the status clears
    session._loop.run(frames=1)
    assert json.loads(sink.frames[-1].texts[0])["error"] is None


def test_a_bind_no_look_can_run_on_is_refused_and_the_old_map_stays():
    sink = RecordingSink()
    session = stepped(sink, looks={START: START_LOOK})
    session.bind(STRIP, limiter=None)
    session._loop.run(frames=2)
    assert sink.controls[-1]["type"] == "refused" and sink.controls[-1]["control"] == "bind"
    assert session.n == 256 and len(sink.frames[-1].data) == 8 + 3 * 256


def test_a_session_makes_one_look_at_a_time(monkeypatch):
    session = stepped(RecordingSink())
    made = threading.Event()

    def surprise(seed=None):  # a make that lasts until the test lets it end
        assert made.wait(5.0)
        raise ValueError("nothing made")

    monkeypatch.setattr(session._aura.variety, "surprise", surprise)
    try:
        first = session.control.request({"type": "surprise", "seed": 1})
        second = session.control.request({"type": "vary", "id": 2})
        assert isinstance(first, Future)
        assert second is not None and not isinstance(second, Future) and "still being made" in second.reason
    finally:
        made.set()
        session.close()
    assert first.result(timeout=5.0) is not None  # refused: nothing was made


def test_a_request_while_paused_is_refused_at_once(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pause"}))
        assert wait_for(lambda: session_of(client).paused)
        start = time.monotonic()
        ws.send_text(json.dumps({"type": "set", "value": 1}))  # no id, no knob: passed over, as when running
        ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "id": 4}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["id"]) == ("look", 4) and "paused" in refused["reason"]
        assert time.monotonic() - start < 2


def test_the_cap_runs_after_the_master_and_streams_both_power_readings():
    class Halve:
        cap = PowerCap(max_brightness=0.5)

        def __init__(self):
            self.seen = []

        def __call__(self, frame):
            self.seen.append(frame.copy())
            return Limited(frame * np.float32(0.5), 0.5, 1.0, 2.0)

    sink, halve = RecordingSink(), Halve()
    session = stepped(sink, fps=POWER_HZ)  # a power reading every frame
    session.bind(plane(8), limiter=cast(PowerLimiter, halve))
    session._loop.run(frames=2)
    assert session._loop._after == (session._aura.master.apply, session._meter)
    assert sink.frames[-1].data[8:] == to_display_u8(halve.seen[-1] * np.float32(0.5)).tobytes()
    assert json.loads(sink.frames[-1].texts[POWER]) == {"type": "power", "watts": 1.0, "uncapped_watts": 2.0}
    assert session.control.master(0.0) is None
    session._loop.run(frames=1)
    assert not halve.seen[-1].any()  # the limiter gets the frame at the master's level


def test_a_failed_frame_is_dropped_and_the_cap_stays_bound():
    class Flaky(RecordingSink):
        failed = False

        def frame(self, payload):
            if not self.failed:
                self.failed = True
                raise RuntimeError("socket hiccup")
            self.frames.append(payload.data)

    sink = Flaky()
    session = stepped(sink)
    session.bind(plane(8), limiter=PowerLimiter(PowerCap(max_brightness=0.0)))
    session._loop.run(frames=3)
    assert sink.failed and len(sink.frames) == 2
    assert all(not any(data[8:]) for data in sink.frames)  # still black: the cap held


def test_an_uncapped_limiter_runs_only_when_a_reading_is_due():
    class Counting:
        cap = PowerCap()

        def __init__(self):
            self.calls = 0

        def __call__(self, frame):
            self.calls += 1
            return Limited(frame, 1.0, 1.0, 1.0)

    counting = Counting()
    session = stepped(RecordingSink())
    session.bind(plane(8), limiter=cast(PowerLimiter, counting))
    session._loop.run(frames=3 * session._meter.every)
    assert counting.calls == 3


def test_a_bind_to_a_rig_without_a_limiter_clears_the_power_reading():
    class Fixed:
        cap = PowerCap(max_brightness=0.5)

        def __call__(self, frame):
            return Limited(frame, 0.5, 1.0, 2.0)

    sink = RecordingSink()
    session = stepped(sink, fps=POWER_HZ)
    session.bind(plane(8), limiter=cast(PowerLimiter, Fixed()))
    session._loop.run(frames=2)
    assert json.loads(sink.frames[-1].texts[POWER])["watts"] == 1.0
    session.bind(plane(8), limiter=None)
    session._loop.run(frames=2)
    assert sink.frames[-1].texts[POWER] is None


def test_frames_carry_the_previews_states_in_its_wire_text():
    sink = RecordingSink()
    session = stepped(sink, seed=3)
    session._loop.run(frames=2)
    control = session.control
    kinds = ["status", "declare", "params", "mod", "aura", "health", "catalog", "power", "arrangement", "report"]
    assert list(_MESSAGES) == kinds
    texts = dict(zip(kinds, sink.frames[-1].texts))
    assert texts["status"] == message("status", status_state(None))
    assert texts["declare"] == message("declare", control.describe())
    assert texts["params"] == message("params", control.values())
    assert texts["aura"] == message("aura", control.state())
    assert texts["catalog"] == message("catalog", control.catalog())
    assert texts["health"] is None  # a session has no health monitor
    assert texts["power"] is None  # nor a power reading before a rig with a limiter is bound
    assert texts["arrangement"] is None and texts["report"] is None  # nor a rig file
    assert json.loads(texts["aura"])["master"] == START_LOOK.master  # the start look's master


def test_two_sessions_with_one_seed_stream_the_same_frames():
    """Engine time comes from the slots, and every seed is injected: same inputs, same bytes."""
    a, b = RecordingSink(), RecordingSink()
    for sink in (a, b):
        stepped(sink, seed=5)._loop.run(frames=6)
    assert [f.data[8:] for f in a.frames] == [f.data[8:] for f in b.frames]
    assert any(f.data[8:] != a.frames[0].data[8:] for f in a.frames)  # and the look moves


def test_the_session_sends_the_status_and_each_state_after_the_hello(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        status = read_until(ws, is_type("status"))
        assert status == {"type": "status", "error": None, "source": None, "path": None}
        for kind in ("declare", "params", "aura", "catalog"):
            read_until(ws, is_type(kind))


def test_a_typed_set_over_the_socket_is_echoed_in_its_json_form(client):
    name = "layers.sparks.glint.palette"
    stops = [{"at": 0, "h": 0, "s": 1, "v": 1}, {"at": 1, "h": 240, "s": 1, "v": 1}]
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "set", "name": name, "value": {"stops": stops}}))
        read_until(ws, lambda m: is_type("params")(m) and m["values"][name]["stops"][1]["h"] == 240.0)
        ws.send_text(json.dumps({"type": "set", "name": name, "value": 3}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["name"]) == ("set", name)


# -- paused sessions and admission (finding 2, finding 10) ---------------------------


def test_a_paused_session_closes_after_the_paused_deadline():
    with TestClient(make_app(paused_timeout_s=0.3)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pause"}))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "session" and "paused" in refused["reason"]
        assert wait_for(lambda: len(state_of(c).admission) == 0 and len(state_of(c).sessions) == 0)


def test_an_idle_session_pauses_then_closes():
    with TestClient(make_app(idle_timeout_s=0.1, paused_timeout_s=0.2)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        assert read_until(ws, is_type("refused"))["control"] == "session"
        assert wait_for(lambda: len(state_of(c).admission) == 0)


def test_a_full_server_evicts_the_session_paused_longest():
    with TestClient(make_app(limits=Limits(max_sessions=2))) as c:
        sessions = state_of(c).sessions
        with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "7.7.7.1"}) as a:
            a.receive_text()
            a.send_text(json.dumps({"type": "pause"}))
            assert wait_for(lambda: sessions.sessions()[0].paused)
            first = sessions.sessions()[0]
            with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "7.7.7.2"}) as b:
                b.receive_text()
                b.send_text(json.dumps({"type": "pause"}))
                assert wait_for(lambda: len(sessions) == 2 and all(s.paused for s in sessions.sessions()))
                second = next(s for s in sessions.sessions() if s is not first)
                with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "7.7.7.3"}) as newcomer:
                    assert json.loads(newcomer.receive_text())["type"] == "hello"
                    refused = read_until(a, is_type("refused"))
                    assert refused["control"] == "session" and "make room" in refused["reason"]
                    assert second in sessions.sessions() and first not in sessions.sessions()
                    assert len(state_of(c).admission) == 2


def test_a_full_server_with_no_paused_session_still_refuses():
    with (
        TestClient(make_app(limits=Limits(max_sessions=1))) as c,
        c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "8.8.8.1"}) as a,
    ):
        a.receive_text()
        with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "8.8.8.2"}) as b:
            assert "1 live sessions" in json.loads(b.receive_text())["reason"]


def test_ipv6_addresses_count_per_64():
    assert address_key("2001:db8::1") == address_key("2001:db8::ffff:1") == "2001:db8::/64"
    assert address_key("2001:db8:0:1::1") != address_key("2001:db8::1")
    assert address_key("::ffff:192.0.2.1") == "192.0.2.1"
    assert address_key("192.0.2.1") == "192.0.2.1" and address_key("testclient") == "testclient"
    with TestClient(make_app()) as c:
        opened = [c.websocket_connect("/ws/session", headers={"Fly-Client-IP": f"2001:db8::{i}"}) for i in range(1, 4)]
        try:
            for ws in [o.__enter__() for o in opened]:
                assert json.loads(ws.receive_text())["type"] == "hello"
            with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "2001:db8::4"}) as fourth:
                assert "3 open sessions" in json.loads(fourth.receive_text())["reason"]
        finally:
            for o in opened:
                o.__exit__(None, None, None)


def test_a_session_that_fails_to_start_releases_its_slot(monkeypatch):
    import pewpew.studio.app as app_module

    def broken(*args, **kwargs):
        raise RuntimeError("no session")

    with TestClient(make_app(limits=Limits(max_sessions=1))) as c:
        monkeypatch.setattr(app_module, "Session", broken)
        with c.websocket_connect("/ws/session") as ws, pytest.raises(WebSocketDisconnect):
            ws.receive_text()
        assert wait_for(lambda: len(state_of(c).admission) == 0)
        monkeypatch.undo()
        with c.websocket_connect("/ws/session") as ws:
            assert json.loads(ws.receive_text())["type"] == "hello"


# -- fixture and pixel caps (finding 3) ----------------------------------------------


def counting_compile(calls):
    def compile_fn(arrangement, catalog):
        calls.append(arrangement)
        return fake_compile(arrangement, catalog)

    return compile_fn


@pytest.mark.parametrize(
    "arrangement",
    [
        {"groups": [{"preset": "ring", "count": 10_000_000}]},
        {"groups": [{"preset": "array", "counts": [15, 15]}]},
        {"groups": [{"preset": "array", "counts": [10**400, 10**400]}]},
        {"fixtures": [{}] * 150, "groups": [{"count": 30}, {"counts": [3, 7]}]},
    ],
)
def test_group_sizes_count_toward_the_fixture_cap_before_compiling(arrangement):
    calls = []
    with TestClient(make_app(compile=counting_compile(calls))) as c:
        r = c.post("/api/compile", json=arrangement)
        assert r.status_code == 422 and r.json()["issues"][0]["code"] == "too_many_fixtures"
        assert c.post("/api/arrangements", json=arrangement).status_code == 422
    assert calls == []


def test_an_arrangement_at_the_fixture_cap_compiles():
    calls = []
    with TestClient(make_app(compile=counting_compile(calls))) as c:
        assert (
            c.post("/api/compile", json={"fixtures": [{}] * 100, "groups": [{"counts": [10, 10]}]}).status_code == 200
        )
    assert len(calls) == 1


def test_real_rig_streams_capped_power_from_the_arrangement_block():
    with TestClient(real_app()) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {**GOLDEN, "power": {"max_brightness": 0.184}}}))
        read_until(ws, is_type("layout"))
        power = read_until(ws, is_type("power"))
        assert power["uncapped_watts"] > 0 and power["watts"] == pytest.approx(0.184 * power["uncapped_watts"])


def test_real_rig_refuses_a_huge_group_before_expanding(monkeypatch):
    import pewpew.rig.compile as rig_compile

    def no_expansion(*args):
        raise AssertionError("expanded an arrangement over the cap")

    monkeypatch.setattr(rig_compile, "expand", no_expansion)
    with TestClient(real_app(limits=Limits(max_fixtures=10**9))) as c:  # past the studio's own check
        r = c.post("/api/compile", json=ring(10_000_000))
        assert r.status_code == 422
        assert "too_many_fixtures" in {i["code"] for i in r.json()["issues"]}


def test_the_studio_holds_its_own_fixture_cap_under_the_rig_files():
    """A local rig file may have more fixtures than the public studio takes."""
    assert Limits().max_fixtures == MAX_FIXTURES == 200 < rig_models.MAX_FIXTURES
    free = [{"id": f"b{i}", "type": "clen-rgbw-bar-1m"} for i in range(MAX_FIXTURES + 1)]
    doc = {"format": "pewpew.arrangement", "version": 1, "fixtures": free}
    assert len(load_arrangement(doc).fixtures) == MAX_FIXTURES + 1
    with TestClient(real_app()) as c:
        r = c.post("/api/compile", json=doc)
        assert r.status_code == 422 and r.json()["issues"][0]["code"] == "too_many_fixtures"
        assert c.post("/api/compile", json={**doc, "fixtures": free[:MAX_FIXTURES]}).status_code == 200


def _doc(**parts) -> dict:
    return {"format": "pewpew.arrangement", "version": 1, **parts}


def _capped_lists() -> set[str]:
    """`Model.field` of every list or object the rig model caps at its MAX_FIXTURES."""
    found: set[str] = set()
    schema = rig_models.Arrangement.model_json_schema()

    def walk(node: Any, owner: str, field: str) -> None:
        if isinstance(node, dict):
            if rig_models.MAX_FIXTURES in (node.get("maxItems"), node.get("maxProperties")):
                found.add(f"{owner}.{field}")
            for child in node.values():
                walk(child, owner, field)
        elif isinstance(node, list):
            for child in node:
                walk(child, owner, field)

    for name, definition in {"Arrangement": schema, **schema["$defs"]}.items():
        for prop, sub in definition.get("properties", {}).items():
            walk(sub, name, prop)
    return found


def _probe(n: int) -> dict[str, dict]:
    """An arrangement with `n` entries in each capped list, by `Model.field`."""
    return {
        "Arrangement.groups": _doc(groups=[{"preset": "ring", "count": 1}] * n),
        "Arrangement.fixtures": _doc(fixtures=[{}] * n),
        "Arrangement.controllers": _doc(controllers=[{}] * n),
        "Arrangement.psus": _doc(psus=[{}] * n),
        "Wiring.chains": _doc(wiring={"chains": [{}] * n}),
        "Wiring.feeds": _doc(wiring={"feeds": [{}] * n}),
        "Chain.fixtures": _doc(wiring={"chains": [{"fixtures": ["a"] * n}]}),
        "PsuPlacement.powers": _doc(psus=[{"powers": ["a"] * n}]),
        "FixturePlacement.tags": _doc(fixtures=[{"tags": ["a"] * n}]),
        "FixturePlacement.dims": _doc(fixtures=[{"dims": {f"d{i}": 1.0 for i in range(n)}}]),
        "RingGroup.tags": _doc(groups=[{"tags": ["a"] * n}]),
        "RingGroup.dims": _doc(groups=[{"dims": {f"d{i}": 1.0 for i in range(n)}}]),
        "ArrayGroup.tags": _doc(groups=[{"tags": ["a"] * n}]),
        "ArrayGroup.dims": _doc(groups=[{"dims": {f"d{i}": 1.0 for i in range(n)}}]),
    }


def test_the_probes_cover_every_list_the_rig_model_caps():
    assert set(_probe(1)) == _capped_lists()


@pytest.mark.parametrize("field", sorted(_capped_lists()))
def test_every_list_the_rig_model_caps_is_held_to_the_studio_cap(field):
    calls = []
    with TestClient(make_app(compile=counting_compile(calls))) as c:
        r = c.post("/api/compile", json=_probe(MAX_FIXTURES + 1)[field])
        assert r.status_code == 422 and r.json()["issues"][0]["code"] in {"too_many_entries", "too_many_fixtures"}
        assert str(MAX_FIXTURES) in r.json()["issues"][0]["message"]
    assert calls == []


@pytest.mark.parametrize("key", ["feeds", "controllers", "psus", "chains"])
def test_a_list_over_the_studio_cap_is_refused_with_its_name_and_one_at_the_cap_compiles(key):
    calls = []
    wiring = key in {"feeds", "chains"}

    def doc(n: int) -> dict:
        return _doc(wiring={key: [{}] * n}) if wiring else _doc(**{key: [{}] * n})

    with TestClient(make_app(compile=counting_compile(calls))) as c:
        r = c.post("/api/compile", json=doc(MAX_FIXTURES + 1))
        issue = r.json()["issues"][0]
        assert r.status_code == 422 and issue["code"] == "too_many_entries" and key in issue["message"]
        assert calls == []
        assert c.post("/api/compile", json=doc(MAX_FIXTURES)).status_code == 200
    assert len(calls) == 1


def test_pixel_cap():
    """The default compile (`compile_doc`) holds the pixel limit: one 64 px bar fits 64, two do not."""
    with TestClient(real_app(limits=Limits(max_pixels=64))) as c:
        r = c.post("/api/compile", json=ring(2))
        assert r.status_code == 422 and r.json()["issues"][0]["code"] == "too_many_pixels"
        assert c.post("/api/compile", json=ring(1)).status_code == 200
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": ring(2)}))
            assert "64 pixels" in read_until(ws, is_type("refused"))["reason"]


# -- websocket message size (finding 4) ----------------------------------------------


def test_message_size_is_counted_in_bytes(client):
    text = "\U0001f600" * 70_000  # 70,000 characters, 280,000 bytes
    assert len(text) < 256 * 1024 < len(text.encode())
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(text)
        assert read_until(ws, is_type("refused"))["control"] == "message"


# -- compile limits (finding 5) ------------------------------------------------------


def test_compile_rate_limit_per_address():
    with TestClient(make_app(limits=Limits(compile_burst=2))) as c:
        h = {"Fly-Client-IP": "1.2.3.4"}
        assert c.post("/api/compile", json={"n": 1}, headers=h).status_code == 200
        assert c.post("/api/compile", json={"n": 1}, headers=h).status_code == 200
        r = c.post("/api/compile", json={"n": 1}, headers=h)
        assert r.status_code == 429 and "compiles per minute" in r.json()["detail"]
        assert "retry-after" in r.headers
        assert c.post("/api/compile", json={"n": 1}, headers={"Fly-Client-IP": "1.2.3.5"}).status_code == 200
        with c.websocket_connect("/ws/session", headers=h) as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": {"n": 4}}))
            assert "compiles per minute" in read_until(ws, is_type("refused"))["reason"]


def test_concurrent_compiles_are_bounded():
    entered, release = threading.Event(), threading.Event()

    def slow_compile(arrangement, catalog):
        if arrangement.get("slow"):
            entered.set()
            release.wait(5)
        return fake_compile(arrangement, catalog)

    limits = Limits(max_concurrent_compiles=1, compile_wait_s=0.05)
    with TestClient(make_app(compile=slow_compile, limits=limits)) as c:
        first = {}
        worker = threading.Thread(target=lambda: first.update(r=c.post("/api/compile", json={"slow": True})))
        worker.start()
        try:
            assert entered.wait(5)
            r = c.post("/api/compile", json={"n": 1})
            assert r.status_code == 503 and "retry-after" in r.headers
        finally:
            release.set()
            worker.join(5)
        assert first["r"].status_code == 200
        assert c.post("/api/compile", json={"n": 1}).status_code == 200


def test_bind_never_serializes_the_rig():
    warning = {"level": "warning", "code": "unwired", "message": "no wiring", "ref": None}
    rigs = []

    def compile_fn(arrangement, catalog):
        rigs.append(FakeRig(4, issues=(warning,)))
        return rigs[-1]

    with TestClient(make_app(compile=compile_fn)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {}}))
        assert read_until(ws, is_type("layout"))["n"] == 4
    assert rigs[0].to_json_calls == 0


# -- HTTP bodies (finding 6, finding 12) ---------------------------------------------


def test_a_chunked_body_over_the_limit_is_413(client):
    chunks = (b" " * 1024 for _ in range(400))  # a generator has no length, so it is sent chunked
    r = client.post("/api/arrangements", content=chunks, headers={"content-type": "application/json"})
    assert r.status_code == 413 and "262144" in r.json()["detail"]


DEEP_BODY = b'{"a":' + b"[" * 100_000 + b"]" * 100_000 + b"}"


@pytest.mark.parametrize("body", [b"{not json", b"[1, 2]", b'"/etc/passwd"', DEEP_BODY, b"\xff\xfe"])
def test_every_422_carries_issues(client, body):
    for path in ("/api/compile", "/api/arrangements"):
        r = client.post(path, content=body, headers={"content-type": "application/json"})
        assert r.status_code == 422, (path, r.text[:200])
        issues = r.json()["issues"]
        assert issues and all({"level", "code", "message"} <= set(i) for i in issues)
        if body == DEEP_BODY:
            assert [i["code"] for i in issues] == ["too_deep"]


# -- the rig's own refusals, and what reaches it -------------------------------------


@pytest.mark.parametrize(
    "arrangement",
    [
        ring(3, start_radius_m=10**400),
        ring(10**400),
        {"format": "pewpew.arrangement", "version": 1, "groups": "/etc/passwd"},
        {"format": "pewpew.arrangement", "version": 2},
    ],
)
def test_real_rig_errors_are_422_issues_never_500(arrangement):
    with TestClient(real_app()) as c:
        r = c.post("/api/compile", json=arrangement)
        assert r.status_code == 422 and r.json()["issues"]
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": arrangement}))
            assert read_until(ws, is_type("refused"))["control"] == "bind"
            read_until(ws, is_frame)


def test_nesting_past_the_limit_never_reaches_the_rig():
    deep = ring(3, start_radius_m=nested(900))
    with TestClient(real_app()) as c:
        r = c.post("/api/compile", json=deep)
        assert r.status_code == 422 and [i["code"] for i in r.json()["issues"]] == ["too_deep"]
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": deep}))  # left out, as text that is not JSON is
            ws.send_text(json.dumps({"type": "bind", "arrangement": {"bad": 1}}))
            assert read_until(ws, is_type("refused"))["issues"][0]["code"] == "bad_format"
            read_until(ws, is_frame)


def test_only_dicts_reach_the_rig(monkeypatch):
    from pewpew.rig import runtime

    seen = []
    real = runtime.load_arrangement
    monkeypatch.setattr(runtime, "load_arrangement", lambda obj: seen.append(type(obj)) or real(obj))
    with TestClient(real_app()) as c:
        assert c.post("/api/compile", json="/etc/passwd").status_code == 422
        assert c.post("/api/compile", json=GOLDEN).status_code == 200
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": "/etc/passwd"}))
            assert read_until(ws, is_type("refused"))["reason"] == "bind needs an arrangement object"
    assert seen == [dict]


# -- the rate limiter (finding 7) ----------------------------------------------------


def test_rate_limiter_table_is_bounded_and_drops_idle_keys():
    t = [0.0]
    lim = RateLimiter(60, burst=1, now=lambda: t[0], max_keys=100)  # a key refills in 1 s
    for i in range(1_000):
        assert lim.allow(f"k{i}") is None
    assert len(lim) == 100
    t[0] = 0.5
    assert lim.allow("k999") is not None  # still empty: kept, not forgotten
    t[0] = 10.0
    assert lim.allow("fresh") is None
    assert len(lim) == 1


# -- the OpenAPI export (finding 8) ---------------------------------------------------


def test_committed_openapi_matches_the_app():
    committed = json.loads((ROOT / "openapi.json").read_text())
    assert committed == create_app().openapi(), "run: uv run python scripts/export_openapi.py"


# -- the wire contract ------------------------------------------------------------

SESSION_GOLDEN = ROOT / "tests" / "goldens" / "session.json"
CARDS = ("osc", "kaleid")  # the catalog cards the golden keeps, so an op added to the catalog does not change it


def capture_session() -> dict:
    """What a visitor is sent over `/ws/session`, as the golden holds it: the greeting (the hello,
    then each per-frame state once), the `layout` after a bind, a `power` reading, and the
    `refused` message of each control the studio adds (`bind`, `session`, `message`) and of a
    request made while paused."""
    app = make_app(limits=Limits(max_sessions=1))
    with TestClient(app) as c, c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "1.1.1.1"}) as ws:
        greeting = [json.loads(ws.receive_text())]
        while greeting[-1]["type"] != "catalog":  # the last of the states a frame brings first
            message = read_until(ws, lambda m: not is_frame(m))
            greeting.append(message)
        # The live values are read at the engine time of whichever frame the mailbox kept.
        mod = next(m for m in greeting if m["type"] == "mod")
        mod["values"] = dict.fromkeys(mod["values"], 0.0)
        catalog = greeting[-1]
        catalog["cards"] = [card for card in catalog["cards"] if card["name"] in CARDS]
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"n": 16, "power": True}}))
        layout = read_until(ws, is_type("layout"))
        power = read_until(ws, is_type("power"))
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"bad": 1}}))
        bind = read_until(ws, is_type("refused"))
        ws.send_bytes(b"\x00")
        refused_message = read_until(ws, is_type("refused"))
        with c.websocket_connect("/ws/session", headers={"Fly-Client-IP": "2.2.2.2"}) as full:
            session = json.loads(full.receive_text())
        ws.send_text(json.dumps({"type": "pause"}))
        assert wait_for(lambda: session_of(c).paused)
        ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "id": 4}))
        paused = read_until(ws, is_type("refused"))
    return {
        "greeting": greeting,
        "layout": layout,
        "power": power,
        "refused": {"bind": bind, "session": session, "message": refused_message, "paused": paused},
    }


def dump_session(live: dict) -> str:
    """The golden's text: one line a message, so a review reads a diff by message."""
    lines = []
    for key, value in live.items():
        if isinstance(value, list):
            body = ",\n".join("    " + json.dumps(m, ensure_ascii=False) for m in value)
            lines.append(f'  "{key}": [\n{body}\n  ]')
        elif key == "refused":
            body = ",\n".join(f'    "{k}": {json.dumps(m, ensure_ascii=False)}' for k, m in value.items())
            lines.append(f'  "{key}": {{\n{body}\n  }}')
        else:
            lines.append(f'  "{key}": {json.dumps(value, ensure_ascii=False)}')
    return "{\n" + ",\n".join(lines) + "\n}\n"


def test_the_golden_is_the_live_session_wire(regen_goldens: bool):
    live = capture_session()
    if regen_goldens:
        SESSION_GOLDEN.write_text(dump_session(live))
    assert json.loads(SESSION_GOLDEN.read_text()) == live, "run `uv run pytest --regen-goldens` and review the diff"


def test_the_session_golden_speaks_the_engines_wire():
    golden = json.loads(SESSION_GOLDEN.read_text())
    assert [m["type"] for m in golden["greeting"]] == ["hello", "status", "declare", "params", "mod", "aura", "catalog"]
    hello, layout = golden["greeting"][0], golden["layout"]
    assert set(hello) == set(layout) | {"display_gamma", "build", "capabilities"}
    assert layout["type"] == "layout" and layout["n"] == len(layout["positions"]) == 16
    assert set(golden["power"]) == {"type", "watts", "uncapped_watts"}
    assert {r["control"] for r in golden["refused"].values()} == {"bind", "session", "message", "look"}


# -- the outbox (finding 9) ------------------------------------------------------------


class _Recorder:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def send_bytes(self, data):
        self.sent.append(data)


def _pump_kinds(control, new_map=False):
    """Queue a frame, send `control` after a pending one, and return the kinds sent.
    `new_map` sends it as a layout."""
    status = message("status", status_state(None))
    declare = message("declare", [{"name": "layers.base.osc.freq", "kind": "float"}])

    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        ws = _Recorder()
        pump = asyncio.ensure_future(box.pump(cast(Any, ws)))
        box.frame(FramePayload(b"ONE", (status, declare)))
        await asyncio.sleep(0.01)
        box.frame(FramePayload(b"OLD", (status, declare)))
        (box.layout if new_map else box.control)(control)
        await asyncio.sleep(0.01)
        box.frame(FramePayload(b"NEW", (status, declare)))
        await asyncio.sleep(0.01)
        box.close_with({"type": "bye"})
        await asyncio.wait_for(pump, 1)
        return ws.sent

    sent = asyncio.run(scenario())
    return sent, [m if isinstance(m, bytes) else m["type"] for m in sent]


def test_a_layout_drops_the_frame_queued_before_it():
    sent, kinds = _pump_kinds('{"type": "layout", "n": 2}', new_map=True)
    assert b"OLD" not in sent
    # The states are absolute: a layout does not send them again.
    assert kinds == [b"ONE", "status", "declare", "layout", b"NEW", "bye"]


def test_an_ack_keeps_the_frame_queued_before_it():
    sent, kinds = _pump_kinds({"type": "ack", "id": 1})
    assert b"OLD" in sent and b"NEW" in sent
    assert kinds.index("ack") < kinds.index("bye")


# -- unexpected input (finding 11) -------------------------------------------------------


def test_a_huge_integer_set_is_refused_and_the_socket_stays_open(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        knob = first_knob(ws)
        ws.send_text(f'{{"type":"set","name":"{knob["name"]}","value":{"9" * 400}}}')
        refused = read_until(ws, is_type("refused"))
        assert refused["name"] == knob["name"] and "finite" in refused["reason"]
        read_until(ws, is_frame)


def test_an_unexpected_compile_error_is_refused_and_logged(caplog):
    def broken_compile(arrangement, catalog):
        raise RuntimeError("compiler bug")

    with TestClient(make_app(compile=broken_compile)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        with caplog.at_level(logging.WARNING, logger="pewpew.studio.app"):
            ws.send_text(json.dumps({"type": "bind", "arrangement": {}}))
            refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "bind" and "compiler bug" not in refused["reason"]
        read_until(ws, is_frame)
    assert any(r.levelno == logging.WARNING and r.name == "pewpew.studio.app" for r in caplog.records)


# -- repeated work and the prebuilt assemblies (finding 13) --------------------------------


def test_the_digest_map_is_built_once_and_unknown_assemblies_rebuild_nothing():
    calls = []

    def assemblies(type_id, cat):
        calls.append(type_id)
        return fake_assembly(type_id, cat)

    with TestClient(make_app(assemblies=assemblies)) as c:
        for _ in range(3):
            assert c.get("/api/assembly/nope.glb").status_code == 404
            assert c.get("/api/catalog").status_code == 200
            assert c.get("/api/assembly/dbar.glb").status_code == 200
    assert sorted(calls) == ["bar", "point"]


def test_a_type_without_an_assembly_has_null_urls():
    with TestClient(make_app(assemblies=lambda type_id, cat: None)) as c:
        body = c.get("/api/catalog").json()
        assert body["fixture_types"][0]["digest"] is None
        assert body["fixture_types"][0]["assembly_url"] is None
        assert body["attachment_types"][0]["assembly_url"] is None
        assert c.get("/api/assembly/dbar.glb").status_code == 404


def serves_every_prebuilt_assembly(c):
    catalog = load_catalog()
    body = c.get("/api/catalog").json()
    types = body["fixture_types"] + body["attachment_types"]
    assert {t["id"] for t in types} == set(catalog.fixture_types) | set(catalog.attachment_types)
    for t in types:
        assert t["assembly_url"] == f"/api/assembly/{t['digest']}.glb"
        r = c.get(t["assembly_url"])
        assert r.status_code == 200 and r.content[:4] == b"glTF"
        assert hashlib.sha256(r.content).hexdigest()[:16] == t["digest"]
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert c.get("/api/assembly/0000000000000000.glb").status_code == 404


def test_the_real_app_serves_every_prebuilt_assembly():
    with TestClient(real_app()) as c:
        serves_every_prebuilt_assembly(c)


@pytest.mark.parametrize("missing", ["pewpew.rig.geometry", "manifold3d"])
def test_missing_geometry_still_serves_every_prebuilt_assembly(monkeypatch, missing):
    monkeypatch.setitem(sys.modules, missing, None)  # the import fails as if absent
    with TestClient(real_app()) as c:
        serves_every_prebuilt_assembly(c)
