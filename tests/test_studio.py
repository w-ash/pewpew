"""The studio backend, driven through FastAPI's TestClient.

Most tests inject a fake rig: `create_app` takes the catalog, compile function
and geometry builders as arguments. The tests marked "real rig" use the
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
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx2")

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from fakes import Pooled
from pewpew import Pattern
from pewpew.load import gallery
from pewpew.mapping import Grouping, line
from pewpew.params import ParamSet
from pewpew.power import Limited, PowerCap, PowerLimiter
from pewpew.rig import EXAMPLES, load_catalog
from pewpew.sinks.base import to_display_u8
from pewpew.sinks.preview import message, status_state
from pewpew.studio.app import create_app
from pewpew.studio.limits import Limits, RateLimiter, address_key, client_ip
from pewpew.studio.session import POWER_HZ, Echo, FramePayload, Session
from pewpew.studio.store import SqliteStore, arrangement_id, canonical_json
from pewpew.studio.transport import Outbox

FPS = 120.0  # fast enough that a test waits milliseconds, not seconds


class FakeRigError(ValueError):
    def __init__(self, issues):
        super().__init__(issues[0]["message"])
        self.issues = issues


class FakeRig:
    def __init__(self, n: int, issues=()):
        self.n = n
        self.mapping = line(n)
        self.catalog_digest = "digest-1"
        self.issues = issues
        self.report = None
        self.grouping = None
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


def state_of(client):
    return cast(Any, client.app).state


def make_app(**kw):
    """The app with a fake rig; keyword arguments override any collaborator."""
    defaults = {
        "catalog": FakeCatalog(),
        "compile": fake_compile,
        "store": SqliteStore(":memory:"),
        "build_glb": lambda type_id, cat: b"glTF-" + type_id.encode(),
        "assembly_digest": lambda type_id, cat: "d" + type_id,
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


def test_patterns_lists_the_gallery_as_the_describe_golden_has_it(client):
    body = client.get("/api/patterns").json()
    assert {p["name"] for p in body} == set(gallery())
    golden = json.loads((Path(__file__).parent / "goldens" / "describe.json").read_text())["patterns"]
    for p in body:
        assert p["params"] == golden[p["name"]]
        assert p["values"] == ParamSet(gallery()[p["name"]]).snapshot_json()


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
        assert hello["type"] == "hello" and hello["fps"] == FPS
        assert hello["pattern"] in hello["patterns"]
        assert hello["pattern"] == ("rainbow" if "rainbow" in hello["patterns"] else "plasma")
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
        bound = read_until(ws, is_type("bound"))
        assert bound["n"] == 16 and bound["catalog_digest"] == "digest-1"
        assert read_until(ws, is_type("hello"))["n"] == 16
        after = read_until(ws, lambda m: is_frame(m) and len(m) == 8 + 48)
        assert header(after)[0] > header(before)[0] > 0


def test_bind_of_a_bad_arrangement_is_refused_and_the_run_goes_on(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {"bad": 1}}))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "bind" and refused["issues"][0]["code"] == "bad"
        read_until(ws, is_frame)


def test_pattern_swap_sends_a_new_hello(client):
    with client.websocket_connect("/ws/session") as ws:
        hello = json.loads(ws.receive_text())
        other = next(p for p in hello["patterns"] if p != hello["pattern"])
        ws.send_text(json.dumps({"type": "pattern", "name": other}))
        assert read_until(ws, is_type("hello"))["pattern"] == other
        ws.send_text(json.dumps({"type": "pattern", "name": "../../etc/passwd"}))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "pattern" and "/" not in refused["reason"]


def test_refused_set_names_the_range_and_never_a_path_and_the_loop_survives(client):
    with client.websocket_connect("/ws/session") as ws:
        hello = json.loads(ws.receive_text())
        knob = hello["params"][0]
        ws.send_text(json.dumps({"type": "set", "name": knob["name"], "value": 1e9}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["name"]) == ("set", knob["name"])
        assert "/" not in refused["reason"] and ".py" not in refused["reason"]
        ws.send_text(json.dumps({"type": "set", "name": ["unhashable"], "value": 1}))
        read_until(ws, is_type("refused"))
        read_until(ws, is_frame)
        assert state_of(client).sessions.sessions()[0].alive


def test_accepted_set_is_echoed_in_params(client):
    with client.websocket_connect("/ws/session") as ws:
        knob = json.loads(ws.receive_text())["params"][0]
        value = (knob["lo"] + knob["hi"]) / 2 if "lo" in knob else knob["default"]
        ws.send_text(json.dumps({"type": "set", "name": knob["name"], "value": value}))
        msg = read_until(ws, lambda m: is_type("params")(m) and m["values"][knob["name"]] == value)
        assert msg["values"][knob["name"]] == value


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

ROOT = Path(__file__).resolve().parents[1]
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
            bound = read_until(ws, is_type("bound"))
            assert bound["n"] == 3072
            assert bound["issues"] == body["issues"]
            assert read_until(ws, is_type("hello"))["n"] == 3072
            assert len(read_until(ws, is_frame)) == 8 + 3 * 3072


def _bound_golden_rings() -> tuple[str, bool]:
    """Bind the golden rings over the socket with Pulse running: the bound
    renderer's units, and whether it spreads each fixture's colour to that
    fixture's pixels as the compiled rig groups them."""
    from pewpew.rig import compile_rig, load_arrangement

    with TestClient(real_app()) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pattern", "name": "pulse"}))
        read_until(ws, is_type("hello"))
        ws.send_text(json.dumps({"type": "bind", "arrangement": GOLDEN}))
        read_until(ws, is_type("bound"))
        read_until(ws, is_type("hello"))
        (session,) = state_of(c).sessions.sessions()
        gather = session.renderer.gather
        fixture_of = compile_rig(load_arrangement(GOLDEN), load_catalog()).fixture_of
        return session.renderer.units, gather is not None and bool((gather == fixture_of).all())


# The bind on the suite's process pool (conftest.py).
JOBS = {"bound": _bound_golden_rings}


def test_a_bind_gives_the_session_the_rigs_fixture_grouping(pooled: Pooled):
    """A per-fixture pattern renders once per fixture of the bound rig."""
    assert pooled["bound"] == ("fixture", True)


# -- coalesced changes (review finding 1) -------------------------------------------


class RecordingSink:
    def __init__(self):
        self.controls = []

    def frame(self, payload):
        pass

    def control(self, message, seen=None):
        self.controls.append(message)

    def power(self, watts, uncapped_watts):
        pass

    def closed(self):
        pass


def test_pending_changes_coalesce_into_one_closure():
    sink = RecordingSink()
    session = Session(sink, pattern="plasma", fps=FPS)  # never started, so nothing drains
    names = sorted(gallery())
    for name in names * 50 + ["plasma"]:
        assert session.pattern(name) is None
    for n in range(1, 500):
        session.bind(line(n), catalog_digest="d", issues=[], limiter=None)
    knob = session.hello()[0]["params"][0]
    values = [knob["lo"] + (knob["hi"] - knob["lo"]) * k / 10_000 for k in range(10_000)]
    for value in values:
        assert session.set(knob["name"], value) is None
    assert len(session._loop.calls._queue) == 1  # one apply closure for every change above
    session._loop.run(frames=1)
    assert session.n == 499
    # The sets were parsed against the plasma that the new plasma replaced.
    assert session.renderer.params[knob["name"]] == knob["default"]
    kinds = [m["type"] for m in sink.controls]
    assert kinds == ["bound", "hello"] and sink.controls[1]["pattern"] == "plasma"
    assert not {"params", "values"} & set(sink.controls[0])  # the hello after it carries them
    for value in values:
        assert session.set(knob["name"], value) is None
    assert len(session._loop.calls._queue) == 1
    session._loop.run(frames=1)
    assert session.renderer.params[knob["name"]] == values[-1]


def test_a_pattern_change_starts_the_new_pattern_at_its_defaults():
    session = Session(RecordingSink(), pattern="sparkle", fps=FPS)
    session.set("color", {"h": 10, "s": 1, "v": 1})
    session._loop.run(frames=1)
    session.pattern("wave")
    session._loop.run(frames=1)
    assert session.renderer.params.snapshot_json() == ParamSet(gallery()["wave"]).snapshot_json()
    assert session.t > 0  # the new renderer took up the engine time


def test_the_session_streams_the_capped_frame_and_both_power_readings():
    class Sink(RecordingSink):
        def __init__(self):
            super().__init__()
            self.frames, self.powers = [], []

        def frame(self, payload):
            self.frames.append(payload.data)

        def power(self, watts, uncapped_watts):
            self.powers.append((watts, uncapped_watts))

    class Halve:
        cap = PowerCap(max_brightness=0.5)

        def __init__(self):
            self.seen = []

        def __call__(self, frame):
            self.seen.append(frame.copy())
            return Limited(frame * np.float32(0.5), 0.5, 1.0, 2.0)

    sink, halve = Sink(), Halve()
    session = Session(sink, pattern="plasma", fps=POWER_HZ)  # a power reading every frame
    session._loop._sleep = lambda s: None
    session.bind(line(8), catalog_digest="d", issues=[], limiter=cast(PowerLimiter, halve))
    session._loop.run(frames=2)
    # No master and no other stage: the limiter runs in on_frame, after the render.
    assert session._loop._after == ()
    assert sink.frames[-1][8:] == to_display_u8(halve.seen[-1] * np.float32(0.5)).tobytes()
    assert sink.powers[-1] == (1.0, 2.0)


def test_a_failed_frame_is_dropped_and_the_cap_stays_bound():
    class Flaky(RecordingSink):
        def __init__(self):
            super().__init__()
            self.frames, self.failed = [], False

        def frame(self, payload):
            if not self.failed:
                self.failed = True
                raise RuntimeError("socket hiccup")
            self.frames.append(payload.data)

    sink = Flaky()
    session = Session(sink, pattern="plasma", fps=FPS)
    session._loop._sleep = lambda s: None
    session.bind(line(8), catalog_digest="d", issues=[], limiter=PowerLimiter(PowerCap(max_brightness=0.0)))
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
    session = Session(RecordingSink(), pattern="plasma", fps=FPS)
    session._loop._sleep = lambda s: None
    session.bind(line(8), catalog_digest="d", issues=[], limiter=cast(PowerLimiter, counting))
    session._loop.run(frames=3 * session._power_every)
    assert counting.calls == 3


def test_a_pattern_change_drops_sets_checked_against_the_old_pattern():
    session = Session(RecordingSink(), pattern="plasma", fps=FPS)
    knob = session.hello()[0]["params"][0]
    session.set(knob["name"], knob["hi"])
    other = next(n for n in sorted(gallery()) if n != "plasma")
    session.pattern(other)
    session.pattern("plasma")
    session._loop.run(frames=1)
    assert session.renderer.params[knob["name"]] == knob["default"]


def test_hello_carries_specs_and_values_and_status_has_the_preview_shape(client):
    with client.websocket_connect("/ws/session") as ws:
        hello = json.loads(ws.receive_text())
        params = ParamSet(gallery()[hello["pattern"]])
        assert hello["params"] == params.describe() and hello["values"] == params.snapshot_json()
        status = read_until(ws, is_type("status"))
        assert status == {"type": "status", "error": None, "source": None, "path": None}


def test_every_param_kind_is_parsed_by_its_own_kind_and_set_on_the_loop(monkeypatch):
    import pewpew.studio.session as session_module
    from params_zoo import Zoo

    monkeypatch.setattr(session_module, "gallery", lambda: {"zoo": Zoo})
    session = Session(RecordingSink(), fps=FPS)
    for name, value in [("level", 0.25), ("bands", 4), ("invert", True), ("shape", "steps")]:
        assert session.set(name, value) is None
    assert session.set("color", {"h": 30, "s": 1, "v": 0.5}) is None
    stops = [{"at": 0, "h": 0, "s": 1, "v": 1}, {"at": 1, "h": 240, "s": 1, "v": 1}]
    assert session.set("palette", {"stops": stops}) is None
    assert "takes a whole number" in (session.set("bands", 2.5) or "")
    assert "one of" in (session.set("shape", "stripes") or "")
    assert session.set("invert", 1) is not None
    assert "must be 0.0" in (session.set("palette", {"stops": [{**stops[0], "at": 0.5}, stops[1]]}) or "")
    assert "unknown preset" in (session.set("palette", "nosuch") or "")
    session._loop.run(frames=1)
    assert session.renderer.params.snapshot_json() == {
        "level": 0.25, "bands": 4, "invert": True, "shape": "steps", "color": {"h": 30.0, "s": 1.0, "v": 0.5},
        "palette": {"label": "", "stops": [{"at": 0.0, "h": 0.0, "s": 1.0, "v": 1.0},
                                           {"at": 1.0, "h": 240.0, "s": 1.0, "v": 1.0}]},
    }
    assert json.loads(session.echo().params)["values"]["shape"] == "steps"
    # A preset is set by its label, and its stops come back in the JSON form.
    assert session.set("palette", "ocean") is None
    session._loop.run(frames=1)
    assert session.renderer.params.snapshot_json()["palette"] == Zoo.palette.to_json(Zoo.palette.presets["ocean"])


def test_a_typed_set_over_the_socket_is_echoed_in_its_json_form(client):
    with client.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pattern", "name": "pulse"}))
        assert read_until(ws, is_type("hello"))["pattern"] == "pulse"
        ws.send_text(json.dumps({"type": "set", "name": "color", "value": {"h": 30, "s": 1, "v": 1}}))
        read_until(ws, lambda m: is_type("params")(m) and m["values"]["color"] == {"h": 30.0, "s": 1.0, "v": 1.0})
        ws.send_text(json.dumps({"type": "set", "name": "color", "value": 3}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["name"]) == ("set", "color")


class ByX(Pattern):
    """Grey by x: per fixture, every pixel of a fixture takes its centre's x."""

    units = "fixture"

    def render(self, x, y, z, index):
        return np.stack([x, x, x], axis=1)


def test_a_bind_with_fixtures_renders_a_per_fixture_pattern_one_colour_per_fixture(monkeypatch):
    import pewpew.studio.session as session_module

    class Sink(RecordingSink):
        def __init__(self):
            super().__init__()
            self.frames = []

        def frame(self, payload):
            self.frames.append(payload.data)

    monkeypatch.setattr(session_module, "gallery", lambda: {"byx": ByX})
    sink = Sink()
    session = Session(sink, fps=FPS)
    session._loop._sleep = lambda s: None
    grouping = Grouping(np.array([[0.25, 0.0, 0.0], [0.75, 0.0, 0.0]], np.float32), np.repeat([0, 1], 4))
    session.bind(line(8), grouping=grouping, catalog_digest="d", issues=[], limiter=None)
    session._loop.run(frames=2)
    shown = np.frombuffer(sink.frames[-1][8:], np.uint8).reshape(8, 3)
    expected = to_display_u8(np.repeat(np.array([[0.25] * 3, [0.75] * 3], np.float32), 4, axis=0))
    assert (shown == expected).all()


def test_the_real_rig_binds_one_unit_per_fixture():
    from pewpew.rig import compile_rig, fixture_grouping, load_arrangement

    rig = compile_rig(load_arrangement(GOLDEN), load_catalog())
    grouping = fixture_grouping(rig.mapping, rig.fixtures)
    assert grouping is not None and len(grouping.centres) == len(rig.fixtures) == 48
    assert (grouping.of == rig.fixture_of).all()
    first = rig.fixtures[0]
    span = slice(first.pixel_start, first.pixel_start + first.pixel_count)
    assert grouping.centres[0] == pytest.approx(rig.mapping[span].mean(axis=0), abs=1e-6)
    assert fixture_grouping(rig.mapping, ()) is None


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
        read_until(ws, is_type("bound"))
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


def test_pixel_cap():
    with TestClient(make_app(limits=Limits(max_pixels=10))) as c:
        r = c.post("/api/compile", json={"n": 16})
        assert r.status_code == 422 and r.json()["issues"][0]["code"] == "too_many_pixels"
        assert c.post("/api/compile", json={"n": 10}).status_code == 200
        with c.websocket_connect("/ws/session") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "bind", "arrangement": {"n": 16}}))
            assert "10 pixels" in read_until(ws, is_type("refused"))["reason"]


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


def test_bind_takes_issues_from_the_rig_and_never_serializes_it():
    warning = {"level": "warning", "code": "unwired", "message": "no wiring", "ref": None}
    rigs = []

    def compile_fn(arrangement, catalog):
        rigs.append(FakeRig(4, issues=(warning,)))
        return rigs[-1]

    with TestClient(make_app(compile=compile_fn)) as c, c.websocket_connect("/ws/session") as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "bind", "arrangement": {}}))
        assert read_until(ws, is_type("bound"))["issues"] == [warning]
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
    import pewpew.studio.app as app_module

    seen = []
    real = app_module.load_arrangement
    monkeypatch.setattr(app_module, "load_arrangement", lambda obj: seen.append(type(obj)) or real(obj))
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


# -- the outbox (finding 9) ------------------------------------------------------------


def test_a_hello_drops_the_frame_queued_before_it():
    class Recorder:
        def __init__(self):
            self.sent = []

        async def send_text(self, text):
            self.sent.append(json.loads(text))

        async def send_bytes(self, data):
            self.sent.append(data)

    old = [{"name": "speed", "kind": "float", "lo": 0, "hi": 1, "default": 0.5}]
    new = [{"name": "scale", "kind": "float", "lo": 0, "hi": 1, "default": 0.5}]

    def echo(declared):
        return Echo(message("declare", declared), message("params", {p["name"]: p["default"] for p in declared}))

    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        ws = Recorder()
        box.frame(FramePayload(b"OLD", message("status", status_state(None)), echo(old)))
        box.control({"type": "hello", "params": new}, echo(new))
        pump = asyncio.ensure_future(box.pump(cast(Any, ws)))
        await asyncio.sleep(0.01)
        box.close_with({"type": "bye"})
        await asyncio.wait_for(pump, 1)
        return ws.sent

    sent = asyncio.run(scenario())
    assert b"OLD" not in sent
    assert [m["type"] for m in sent] == ["hello", "bye"]


# -- unexpected input (finding 11) -------------------------------------------------------


def test_param_check_refuses_an_integer_too_large_for_a_float():
    params = ParamSet(gallery()["plasma"])
    name = params.describe()[0]["name"]
    assert "finite" in (params.check(name, 10**400) or "")


def test_a_huge_integer_set_is_refused_and_the_socket_stays_open(client):
    with client.websocket_connect("/ws/session") as ws:
        knob = json.loads(ws.receive_text())["params"][0]
        ws.send_text(f'{{"type":"set","name":"{knob["name"]}","value":{"9" * 400}}}')
        assert read_until(ws, is_type("refused"))["name"] == knob["name"]
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


# -- repeated work and missing geometry (finding 13) --------------------------------------


def test_the_digest_map_is_built_once_and_unknown_assemblies_rebuild_nothing():
    digests, builds = [], []

    def digest_of(type_id, cat):
        digests.append(type_id)
        return "d" + type_id

    def build(type_id, cat):
        builds.append(type_id)
        return b"glTF-" + type_id.encode()

    with TestClient(make_app(build_glb=build, assembly_digest=digest_of)) as c:
        for _ in range(3):
            assert c.get("/api/assembly/nope.glb").status_code == 404
            assert c.get("/api/catalog").status_code == 200
            assert c.get("/api/assembly/dbar.glb").status_code == 200
    assert sorted(digests) == sorted(builds) == ["bar", "point"]


def test_real_geometry_serves_every_assembly_once_built():
    from pewpew.rig import geometry

    catalog = load_catalog()
    with TestClient(real_app()) as c:
        body = c.get("/api/catalog").json()
        types = body["fixture_types"] + body["attachment_types"]
        assert {t["id"] for t in types} == set(catalog.fixture_types) | set(catalog.attachment_types)
        for t in types:
            assert t["digest"] == geometry.assembly_digest(t["id"], catalog)
            r = c.get(t["assembly_url"])
            assert r.status_code == 200 and r.content[:4] == b"glTF"
            assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert c.get("/api/assembly/0000000000000000.glb").status_code == 404


@pytest.mark.parametrize("missing", ["pewpew.rig.geometry", "manifold3d"])
def test_missing_geometry_gives_503_and_no_assembly_urls(monkeypatch, missing):
    monkeypatch.setitem(sys.modules, missing, None)  # the import fails as if absent
    with TestClient(real_app()) as c:
        body = c.get("/api/catalog").json()
        assert body["fixture_types"] and all(f["assembly_url"] is None for f in body["fixture_types"])
        r = c.get("/api/assembly/anything.glb")
        assert r.status_code == 503 and "geometry" in r.json()["detail"]
