"""The Gallery (pewpew.studio), driven through FastAPI's TestClient.

The app compiles with the real rig (`pewpew.rig.load_catalog`,
`compile_doc`), on small arrangements (`ring`); a test that counts or
slows the compiles wraps the real compile. A share is posted as the
Console's Publish posts it, a form with one field, `envelope`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
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
from pewpew import share
from pewpew.aura.book import examples_book
from pewpew.errors import Refusal
from pewpew.power import POWER_HZ, Limited, PowerCap, PowerLimiter
from pewpew.rig import EXAMPLES, load_arrangement, load_catalog
from pewpew.rig import models as rig_models
from pewpew.rig.runtime import compile_doc
from pewpew.sinks.preview import _MESSAGES, message, page, page_build, status_state, web_file, web_files
from pewpew.sinks.sink import DISPLAY_GAMMA, to_display_u8
from pewpew.studio.app import EXPORTING, NO_STORE, UNREADABLE, _Visitor, create_app
from pewpew.studio.limits import MAX_BODY_BYTES, MAX_FIXTURES, Limits, RateLimiter, address_key, client_ip
from pewpew.studio.session import FramePayload, NoLook, Session, Shared
from pewpew.studio.store import SqliteStore
from pewpew.studio.transport import MAX_CONTROL_BACKLOG, MAX_CONTROL_BYTES, Outbox

FPS = 120.0  # fast enough that a test waits milliseconds, not seconds
ROOT = Path(__file__).resolve().parents[1]
BOOK = examples_book(ROOT / "examples")
LOOKS = json.loads(BOOK.to_bytes())["looks"]  # each example look in the looks file's form
CHOSEN = ("tide", "warp-lane")
POWER = list(_MESSAGES).index("power")  # where a frame's texts hold the power reading
STRIP = np.column_stack([np.linspace(0, 1, 8), np.zeros(8), np.zeros(8)]).astype(np.float32)
CAPABILITIES = ["ack", "look", "export", "pause", "gallery"]


def ring(count, **extra):
    group = {"id": "big", "preset": "ring", "type": "clen-rgbw-bar-1m", "count": count, "start_radius_m": 1.0}
    return {"format": "pewpew.arrangement", "version": 1, "groups": [{**group, **extra}]}


ENVELOPE = share.envelope(ring(3), BOOK, CHOSEN)  # 192 pixels, in `tide` with `warp-lane` beside it


def plane(n: int) -> np.ndarray:
    """`n` points over two axes, in two rows: `tide` folds a plane, so a strip will not do."""
    return np.column_stack([np.linspace(0.0, 1.0, n), np.arange(n) % 2, np.zeros(n)]).astype(np.float32)


def state_of(client):
    return cast(Any, client.app).state


def make_app(**kw):
    """The app on a store in memory, its default share `ring(3)`; keyword arguments override any collaborator."""
    if "store" not in kw:  # made only when needed: an unclosed one warns when collected
        kw["store"] = SqliteStore(":memory:")
    return create_app(**{"default": ring(3), "fps": FPS, **kw})


@pytest.fixture
def client():
    with TestClient(make_app()) as c:
        yield c


def post(c, envelope: Any = ENVELOPE, headers=None, text: str | None = None):
    """Post `envelope` as the Console's Publish does: a form with one field."""
    body = {"envelope": json.dumps(envelope) if text is None else text}
    return c.post("/api/shares", data=body, headers=headers, follow_redirects=False)


def shared(c, envelope: Any = ENVELOPE, headers=None) -> str:
    """Post `envelope`; the id it is stored under."""
    r = post(c, envelope, headers)
    assert r.status_code == 303, r.text
    return r.headers["location"].removeprefix("/a/")


def connect(c, id: str | None = None, headers=None):
    return c.websocket_connect("/ws" if id is None else f"/ws?a={id}", headers=dict(headers or {}))


@pytest.fixture
def ws(client):
    """A socket on `ENVELOPE`, past its hello."""
    with connect(client, shared(client)) as socket:
        socket.receive_text()
        yield socket


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
    return np.frombuffer(frame[:8], dtype=np.dtype([("t", "<f4"), ("seq", "<u4")]))[0]


def first_knob(ws, kind="float"):
    """The first knob of `kind` the session declares."""
    return next(k for k in read_until(ws, is_type("declare"))["params"] if k["kind"] == kind)


def session_of(client) -> Session:
    (session,) = state_of(client).sessions.sessions()
    return session


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def counting_compile(calls):
    def compile_fn(arrangement, catalog):
        calls.append(arrangement)
        return compile_doc(arrangement, catalog)

    return compile_fn


# -- HTTP: shares --------------------------------------------------------------


def test_health_live(client):
    assert client.get("/health/live").json() == {"ok": True}


def test_a_posted_share_is_stored_and_answered_303_to_its_page(client):
    r = post(client)
    assert r.status_code == 303
    id_ = r.headers["location"].removeprefix("/a/")
    checked, _ = share.check(ENVELOPE)
    assert id_ == share.content_id(share.canonical_json(checked))
    assert state_of(client).shares.get(id_) is not None  # compiled once, kept for its sessions
    assert client.get(f"/a/{id_}").status_code == 200


def test_the_same_share_gets_the_same_id_whatever_its_key_order(client):
    reordered = json.loads(json.dumps(ENVELOPE), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
    assert shared(client) == shared(client, reordered)


@pytest.mark.parametrize("text, says", [
    ("{not json", "not JSON"),
    (json.dumps({"format": "pewpew.arrangement"}), "does not check"),
    (json.dumps(share.envelope(ring(3, type="no-such-bar"), BOOK, CHOSEN)), "does not compile"),
    (json.dumps({**ENVELOPE, "looks": {**ENVELOPE["looks"], "looks": {"tide": {"layers": "/etc/passwd"}}}}),
     "does not check"),
    ('{"a":' + "[" * 100_000 + "]" * 100_000 + "}", "not JSON"),
])
def test_what_is_not_a_share_gets_a_422_line_of_text(client, text, says):
    r = post(client, text=text)
    assert r.status_code == 422 and says in r.text
    assert r.headers["content-type"].startswith("text/plain") and "/etc" not in r.text


def test_a_form_of_other_fields_is_422(client):
    r = client.post("/api/shares", data={"other": "1"}, follow_redirects=False)
    assert r.status_code == 422 and "one field, envelope" in r.text
    two = client.post("/api/shares", content=b"envelope=1&envelope=2",
                      headers={"content-type": "application/x-www-form-urlencoded"})
    assert two.status_code == 422


def test_a_body_that_is_not_a_form_is_415(client):
    r = client.post("/api/shares", json=ENVELOPE)
    assert r.status_code == 415 and r.headers["content-type"].startswith("text/plain")


def test_an_oversized_share_is_413():
    with TestClient(make_app(limits=Limits(max_body_bytes=1000))) as c:
        r = post(c, text="x" * 3001)  # the form itself is over three times the limit
        assert r.status_code == 413 and "3000" in r.text
        r = post(c, text="x" * 1001)  # a form under that, with an envelope over the limit
        assert r.status_code == 413 and "1000 bytes" in r.text
        chunks = (b" " * 1024 for _ in range(4))  # a generator has no length, so it is sent chunked
        r = c.post("/api/shares", content=chunks, headers={"content-type": "application/x-www-form-urlencoded"})
        assert r.status_code == 413
        assert c.post("/health/live", content=b"x" * 1001).status_code == 413  # every other route keeps the limit


def test_shares_are_rate_limited_per_address():
    with TestClient(make_app(limits=Limits(saves_per_minute=2))) as c:
        h = {"Fly-Client-IP": "1.1.1.1"}
        assert post(c, headers=h).status_code == 303
        assert post(c, headers=h).status_code == 303
        r = post(c, headers=h)
        assert r.status_code == 429 and "2 shares per minute" in r.text and "retry-after" in r.headers
        assert post(c, headers={"Fly-Client-IP": "2.2.2.2"}).status_code == 303


def test_the_rate_limiter_window_slides():
    t = [0.0]
    lim = RateLimiter(1, now=lambda: t[0])
    assert lim.allow("a") is None
    assert lim.allow("a") is not None
    t[0] = 61.0
    assert lim.allow("a") is None


def test_no_response_carries_a_cors_header(client):
    id_ = shared(client)
    asset = min(web_files())
    preflight = {"Origin": "http://192.168.1.2:7447", "Access-Control-Request-Method": "POST"}
    responses = [
        client.get("/"), client.get(f"/a/{id_}"), client.get("/a/" + "A" * 22), client.get(f"/{asset}"),
        client.get("/parts.json"), post(client), post(client, text="{"), client.post("/api/shares", json={}),
        client.options("/api/shares", headers=preflight), client.options("/", headers=preflight),
        post(client, headers={"Origin": "http://192.168.1.2:7447"}),
    ]
    for r in responses:
        assert not [h for h in r.headers if h.lower().startswith("access-control-")], (r.request.url, r.headers)


def test_the_page_is_the_consoles_titled_for_the_gallery_and_never_cached(client):
    id_ = shared(client)
    for path in ("/", f"/a/{id_}"):
        r = client.get(path)
        assert r.status_code == 200 and "<title>pewpew Gallery</title>" in r.text
        assert r.headers["cache-control"] == "no-cache" and r.headers["content-type"].startswith("text/html")
    titled = re.sub(rb"<title>.*?</title>", b"<title>pewpew Gallery</title>", page()[0], count=1)
    assert client.get("/").content == titled  # the Console page, only its title changed


def test_an_unknown_share_page_is_a_404_line(client):
    for path in ("/a/" + "A" * 22, "/a/short", "/a/../../etc/passwd"):
        r = client.get(path)
        assert r.status_code == 404 and r.headers["content-type"].startswith("text/plain")


def test_each_file_of_the_page_is_served_immutable(client):
    for path in sorted(web_files()):
        r = client.get(f"/{path}")
        assert r.status_code == 200 and r.content == web_file(path)[0], path
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get("/assets/nope.js").status_code == 404
    assert client.get("/../../etc/passwd").status_code == 404


def test_the_deleted_routes_are_gone(client):
    for path in ("/api/catalog", "/api/looks", "/api/arrangements/" + "A" * 22, "/api/assembly/x.glb",
                 "/api/docs", "/api/openapi.json", "/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
    for path in ("/api/compile", "/api/arrangements"):
        assert client.post(path, json={}).status_code in (404, 405), path
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws/session") as ws:
        ws.receive_text()


def test_the_client_ip_prefers_the_fly_header():
    assert client_ip({"fly-client-ip": "9.9.9.9"}, "10.0.0.1") == "9.9.9.9"
    assert client_ip({}, "10.0.0.1") == "10.0.0.1"


class FailingStore(SqliteStore):
    """A store whose writes fail, as a database that is down does."""

    def put(self, id: str, canonical: str) -> None:
        raise sqlite3.OperationalError("database is locked")


def test_a_share_the_store_cannot_write_is_a_503_line_and_never_cached(caplog):
    with TestClient(make_app(store=FailingStore(":memory:"))) as c:
        r = post(c)
        assert (r.status_code, r.text) == (503, NO_STORE + "\n")
        assert "locked" not in r.text and "did not write" in caplog.text
        assert len(state_of(c).shares._shares) == 0
        id_ = share.content_id(share.canonical_json(share.check(ENVELOPE)[0]))
        assert c.get(f"/a/{id_}").status_code == 404


def test_the_store_is_idempotent():
    s = SqliteStore(":memory:")
    s.init()
    s.init()
    text = share.canonical_json({"b": 1, "a": [2]})
    s.put(share.content_id(text), text)
    s.put(share.content_id(text), text)
    try:
        assert s.get(share.content_id(text)) == text and s.get("x" * 22) is None
    finally:
        s.close()  # an unclosed connection warns when collected, in whichever test runs then


# -- HTTP: the parts catalog and its assemblies -----------------------------------


def serves_every_prebuilt_assembly(c):
    catalog = load_catalog()
    body = c.get("/parts.json").json()
    types = body["fixture_types"] + body["attachment_types"]
    assert {t["id"] for t in types} == set(catalog.fixture_types) | set(catalog.attachment_types)
    for t in types:
        assert t["assembly_url"] == f"/assembly/{t['digest']}.glb"
        r = c.get(t["assembly_url"])
        assert r.status_code == 200 and r.content[:4] == b"glTF"
        assert hashlib.sha256(r.content).hexdigest()[:16] == t["digest"]
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert c.get("/assembly/0000000000000000.glb").status_code == 404
    assert c.get("/assembly/nope.glb").status_code == 404


def test_the_parts_catalog_and_every_assembly_are_served_as_the_engine_serves_them(client):
    serves_every_prebuilt_assembly(client)
    zipped = client.get("/parts.json", headers={"Accept-Encoding": "gzip"})
    assert zipped.headers["content-encoding"] == "gzip" and zipped.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("missing", ["pewpew.rig.geometry", "manifold3d"])
def test_missing_geometry_still_serves_every_prebuilt_assembly(monkeypatch, missing):
    monkeypatch.setitem(sys.modules, missing, None)  # the import fails as if absent
    with TestClient(make_app()) as c:
        serves_every_prebuilt_assembly(c)


# -- the limits on what is compiled ------------------------------------------------


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
        r = post(c, {**ENVELOPE, "arrangement": arrangement})
        assert r.status_code == 422 and f"{MAX_FIXTURES} fixtures" in r.text
    assert calls == []


def test_the_gallery_holds_its_own_fixture_cap_under_the_rig_files():
    """A local rig file may have more fixtures than the Gallery takes."""
    assert Limits().max_fixtures == MAX_FIXTURES == 200 < rig_models.MAX_FIXTURES
    free = [{"id": f"b{i}", "type": "clen-rgbw-bar-1m"} for i in range(MAX_FIXTURES + 1)]
    doc = {"format": "pewpew.arrangement", "version": 1, "fixtures": free}
    assert len(load_arrangement(doc).fixtures) == MAX_FIXTURES + 1
    with TestClient(make_app()) as c:
        assert "200 fixtures" in post(c, {**ENVELOPE, "arrangement": doc}).text


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


def test_every_list_the_rig_model_caps_is_held_to_the_gallery_cap():
    calls = []
    with TestClient(make_app(compile=counting_compile(calls), limits=Limits(saves_per_minute=100))) as c:
        for field, doc in _probe(MAX_FIXTURES + 1).items():
            r = post(c, {**ENVELOPE, "arrangement": doc})
            assert r.status_code == 422 and str(MAX_FIXTURES) in r.text, field
    assert calls == []


@pytest.mark.parametrize(
    "arrangement",
    [
        ring(3, start_radius_m=10**400),
        ring(10**400),
        {"format": "pewpew.arrangement", "version": 1, "groups": "/etc/passwd"},
        {"format": "pewpew.arrangement", "version": 2},
    ],
)
def test_real_rig_errors_are_422_lines_never_500(arrangement):
    with TestClient(make_app()) as c:
        r = post(c, {**ENVELOPE, "arrangement": arrangement})
        assert r.status_code == 422 and "/etc" not in r.text


def test_the_pixel_cap():
    """The default compile (`compile_doc`) holds the pixel limit: one 64 px bar fits 64, two do not."""
    with TestClient(make_app(limits=Limits(max_pixels=64), default=ring(1))) as c:
        r = post(c, {**ENVELOPE, "arrangement": ring(2)})
        assert r.status_code == 422 and "64 pixels" in r.text


def test_compiles_are_rate_limited_per_address():
    with TestClient(make_app(limits=Limits(compile_burst=2))) as c:
        h = {"Fly-Client-IP": "1.2.3.4"}
        assert post(c, {**ENVELOPE, "arrangement": ring(1)}, h).status_code == 303
        assert post(c, {**ENVELOPE, "arrangement": ring(2)}, h).status_code == 303
        assert post(c, {**ENVELOPE, "arrangement": ring(1)}, h).status_code == 303  # compiled already: no compile
        r = post(c, {**ENVELOPE, "arrangement": ring(3)}, h)
        assert r.status_code == 429 and "compiles per minute" in r.text and "retry-after" in r.headers
        assert post(c, {**ENVELOPE, "arrangement": ring(3)}, {"Fly-Client-IP": "1.2.3.5"}).status_code == 303


def test_concurrent_compiles_are_bounded():
    entered, release = threading.Event(), threading.Event()

    def slow_compile(arrangement, catalog):
        if arrangement["groups"][0]["count"] == 2:
            entered.set()
            release.wait(5)
        return compile_doc(arrangement, catalog)

    limits = Limits(max_concurrent_compiles=1, compile_wait_s=0.05)
    with TestClient(make_app(compile=slow_compile, limits=limits)) as c:
        first = {}
        slow = {**ENVELOPE, "arrangement": ring(2)}
        worker = threading.Thread(target=lambda: first.update(r=post(c, slow, {"Fly-Client-IP": "9.0.0.1"})))
        worker.start()
        try:
            assert entered.wait(5)
            r = post(c, {**ENVELOPE, "arrangement": ring(1)})
            assert r.status_code == 503 and "retry-after" in r.headers
        finally:
            release.set()
            worker.join(5)
        assert first["r"].status_code == 303
        assert post(c, {**ENVELOPE, "arrangement": ring(1)}).status_code == 303


def test_an_unexpected_compile_error_is_refused_logged_and_never_named(caplog):
    def broken_compile(arrangement, catalog):
        raise RuntimeError("compiler bug")

    with TestClient(make_app(compile=broken_compile)) as c, caplog.at_level(logging.WARNING, "pewpew.studio.app"):
        r = post(c)
        assert r.status_code == 422 and "compiler bug" not in r.text
        with connect(c) as ws:
            refused = json.loads(ws.receive_text())
            assert refused["control"] == "session" and "compiler bug" not in refused["reason"]
    assert any(r.levelno == logging.WARNING and r.name == "pewpew.studio.app" for r in caplog.records)


# -- the websocket: one session on a share -------------------------------------------


def test_the_hello_draws_the_shared_rig_and_offers_the_gallerys_capabilities(client):
    id_ = shared(client)
    with connect(client, id_) as ws:
        hello = json.loads(ws.receive_text())
        assert hello["type"] == "hello" and hello["n"] == hello["total"] == 192 == len(hello["positions"])
        assert hello["capabilities"] == CAPABILITIES  # no arrange, no publish
        assert hello["rig"] is not None and hello["rig"]["fixtures"] and hello["room"]["fixtures"]
        assert hello["display_gamma"] == DISPLAY_GAMMA and hello["build"] == page_build()
        first = read_until(ws, is_frame)
        second = read_until(ws, is_frame)
        assert len(first) == 8 + 3 * hello["n"]
        assert header(second)["seq"] > header(first)["seq"]


def test_a_session_starts_in_the_shares_current_look_with_its_looks(client):
    with connect(client, shared(client)) as ws:
        aura = read_until(ws, is_type("aura"))
        assert aura["looks"]["current"] == "tide"
        assert [item["name"] for item in aura["looks"]["items"]] == list(CHOSEN)


def test_no_share_runs_the_default_one_with_the_example_looks(client):
    with connect(client) as ws:
        assert json.loads(ws.receive_text())["n"] == 192
        aura = read_until(ws, is_type("aura"))
        assert [item["name"] for item in aura["looks"]["items"]] == list(BOOK.looks)


def test_an_unknown_share_is_refused_then_closed(client):
    for id_ in ("A" * 22, "nope"):
        with connect(client, id_) as ws:
            refused = json.loads(ws.receive_text())
            assert refused["control"] == "session" and "no share" in refused["reason"]
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
    assert wait_for(lambda: len(state_of(client).admission) == 0)


def test_an_old_bare_row_opens_with_the_example_looks():
    store = SqliteStore(":memory:")
    with TestClient(make_app(store=store)) as c:
        text = share.canonical_json(ring(1))  # a row as an older Gallery stored it
        id_ = share.content_id(text)
        store.put(id_, text)
        assert c.get(f"/a/{id_}").status_code == 200
        with connect(c, id_) as ws:
            assert json.loads(ws.receive_text())["n"] == 64
            aura = read_until(ws, is_type("aura"))
            assert [item["name"] for item in aura["looks"]["items"]] == list(BOOK.looks)


@pytest.mark.parametrize("row", [
    '{"format": "pewpew.share", "version": 1}',  # no arrangement, no looks
    '{"format": "pewpew.share", "version": 1, "arrangement": {}, "looks": {"version": 3}}',  # looks of another version
    '{"format": "pewpew.thing"}',
    "[1, 2]",
])
def test_a_stored_row_that_cannot_be_read_is_refused_logged_and_closed_normally(row, caplog):
    store = SqliteStore(":memory:")
    with TestClient(make_app(store=store)) as c:
        id_ = share.content_id(row)
        store.put(id_, row)
        with connect(c, id_) as ws:
            assert json.loads(ws.receive_text()) == {"type": "refused", "control": "session", "id": None,
                                                     "name": None, "reason": UNREADABLE}
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_text()
            assert closed.value.code == 1000
        assert id_ in caplog.text and "cannot be read" in caplog.text
        assert wait_for(lambda: len(state_of(c).admission) == 0)


def test_a_session_never_runs_the_idle_cycle_on_a_share_or_the_examples(client):
    for id_ in (shared(client), None):
        with connect(client, id_) as ws:
            assert read_until(ws, is_type("aura"))["looks"]["idle"] is None
    assert BOOK.cycle.idle is not None and ENVELOPE["looks"]["cycle"]["idle"] is not None  # the books have one


def test_each_share_compiles_once_for_every_session_on_it():
    calls = []
    with TestClient(make_app(compile=counting_compile(calls), cached=1)) as c:
        id_ = shared(c)
        assert len(calls) == 1
        for _ in range(2):
            with connect(c, id_) as ws:
                ws.receive_text()
        assert len(calls) == 1
        other = shared(c, {**ENVELOPE, "arrangement": ring(1)})  # the cache holds one share
        assert len(calls) == 2
        with connect(c, id_) as ws:
            ws.receive_text()
        assert len(calls) == 3  # compiled again after it left the cache
        with connect(c) as ws, connect(c, other) as again:
            ws.receive_text()
            again.receive_text()
        with connect(c) as ws:
            ws.receive_text()
        assert len(calls) == 5  # the default share once, the other share again


def test_a_share_no_look_can_start_on_is_refused():
    looks_on_a_line = share.envelope(ring(1), BOOK, ["tide"])  # tide folds a plane: one bar is a line
    with TestClient(make_app()) as c, connect(c, shared(c, looks_on_a_line)) as ws:
        refused = json.loads(ws.receive_text())
        assert refused["control"] == "session" and "no look" in refused["reason"]


def test_a_look_message_is_applied_and_acked(ws):
    ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "fade": 0, "id": 7}))
    assert read_until(ws, is_type("ack")) == {"type": "ack", "id": 7, "control": "look"}
    want = [layer["id"] for layer in LOOKS["warp-lane"]["layers"]]
    aura = read_until(ws, lambda m: is_type("aura")(m) and [x["id"] for x in m["stack"]["layers"]] == want)
    assert aura["fading"] is False
    ws.send_text(json.dumps({"type": "look", "look": {"layers": "/etc/passwd"}, "id": 8}))
    refused = read_until(ws, is_type("refused"))
    assert (refused["control"], refused["id"]) == ("look", 8) and "/etc" not in refused["reason"]


def test_an_unknown_control_is_refused_with_its_id_and_passed_over_without(ws):
    ws.send_text(json.dumps({"type": "pattern", "name": "plasma"}))
    ws.send_text(json.dumps({"type": "pattern", "name": "plasma", "id": "a"}))
    refused = read_until(ws, lambda m: is_type("refused")(m) or is_type("ack")(m))
    assert (refused["type"], refused["control"], refused["id"]) == ("refused", "pattern", "a")
    assert "unknown control" in refused["reason"]


def test_requests_that_need_boards_or_a_rig_file_are_refused(ws):
    for i, request in enumerate([{"type": "scan"}, {"type": "blink", "fixture": "a"},
                                 {"type": "arrange", "arrangement": {}}, {"type": "export", "share": True}]):
        ws.send_text(json.dumps({**request, "id": i}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["id"]) == (request["type"], i)


def test_saves_renames_and_favorites_last_for_the_visit_and_write_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(make_app()) as c, connect(c, shared(c)) as ws:
        ws.receive_text()
        for i, request in enumerate([{"type": "save", "name": "mine"}, {"type": "rename", "name": "mine", "to": "ours"},
                                     {"type": "favorite", "name": "ours", "on": True}]):
            ws.send_text(json.dumps({**request, "id": i}))
            assert read_until(ws, lambda m: is_type("ack")(m) or is_type("refused")(m))["type"] == "ack", request
        looks = session_of(c).control.state()["looks"]
        assert [item["name"] for item in looks["items"]] == [*CHOSEN, "ours"] and "ours" in looks["favorites"]
    assert list(tmp_path.iterdir()) == []


def test_export_answers_with_a_looks_file_of_the_visit(ws):
    ws.send_text(json.dumps({"type": "favorite", "name": "warp-lane", "on": False, "id": 1}))
    read_until(ws, is_type("ack"))
    ws.send_text(json.dumps({"type": "export", "looks": None, "share": False}))  # answered without an id too
    exported = read_until(ws, is_type("exported"))
    assert exported["id"] is None and exported["gallery"] is None
    file = exported["file"]
    assert file["version"] == 4 and list(file["looks"]) == list(CHOSEN) and file["favorites"] == ["tide"]
    ws.send_text(json.dumps({"type": "export", "looks": ["tide"], "share": True, "id": 2}))
    refused = read_until(ws, is_type("refused"))
    assert (refused["control"], refused["id"]) == ("export", 2) and "Gallery" in refused["reason"]


def test_exports_are_rate_limited_per_session():
    with TestClient(make_app(limits=Limits(exports_per_minute=60, export_burst=2))) as c, connect(c) as ws:
        ws.receive_text()
        for i in range(2):
            ws.send_text(json.dumps({"type": "export", "id": i}))
            assert read_until(ws, lambda m: is_type("exported")(m) or is_type("refused")(m))["type"] == "exported"
        ws.send_text(json.dumps({"type": "export", "id": 2}))
        refused = read_until(ws, is_type("refused"))
        assert (refused["control"], refused["id"]) == ("export", 2) and "60 exports per minute" in refused["reason"]


def test_export_limits_hold_across_reconnects_from_one_address():
    with TestClient(make_app(limits=Limits(exports_per_minute=60, export_burst=2))) as c:
        for i in range(2):
            with connect(c) as ws:
                ws.receive_text()
                ws.send_text(json.dumps({"type": "export", "id": i}))
                assert read_until(ws, lambda m: is_type("exported")(m) or is_type("refused")(m))["type"] == "exported"
        with connect(c) as ws:  # a new socket from the same address
            ws.receive_text()
            ws.send_text(json.dumps({"type": "export", "id": 9}))
            refused = read_until(ws, is_type("refused"))
            assert refused["id"] == 9 and "60 exports per minute" in refused["reason"]
        with connect(c, headers={"fly-client-ip": "203.0.113.9"}) as ws:  # another address has its own
            ws.receive_text()
            ws.send_text(json.dumps({"type": "export", "id": 1}))
            assert read_until(ws, lambda m: is_type("exported")(m) or is_type("refused")(m))["type"] == "exported"


def test_an_export_keeps_the_shares_idle_setting_while_the_session_never_cycles(client):
    idle = ENVELOPE["looks"]["cycle"]["idle"]
    assert idle is not None
    with connect(client, shared(client)) as ws:
        assert read_until(ws, is_type("aura"))["looks"]["idle"] is None
        ws.send_text(json.dumps({"type": "export", "id": 1}))
        assert read_until(ws, is_type("exported"))["file"]["cycle"]["idle"] == idle


def test_a_stored_row_that_cannot_be_read_or_compiled_is_answered_from_memory_after_the_first_open(caplog):
    gets: list[str] = []
    store = SqliteStore(":memory:")
    real_get = store.get
    store.get = lambda id: gets.append(id) or real_get(id)
    unreadable = "[1, 2]"
    with TestClient(make_app(store=store)) as c:
        id_ = share.content_id(unreadable)
        store.put(id_, unreadable)
        for _ in range(3):
            with connect(c, id_) as ws:
                assert json.loads(ws.receive_text())["reason"] == UNREADABLE
    assert gets == [id_]
    assert caplog.text.count("cannot be read") == 1


def test_an_arrangement_that_does_not_compile_takes_one_compile_for_all_its_opens(caplog):
    compiles = []

    def compile(arrangement, catalog):
        compiles.append(1)
        raise ValueError("no")

    store = SqliteStore(":memory:")
    text = share.canonical_json(ENVELOPE)
    id_ = share.content_id(text)
    with TestClient(make_app(store=store, compile=compile, default=ring(3))) as c:
        store.put(id_, text)
        for _ in range(3):
            with connect(c, id_) as ws:
                assert "does not compile" in json.loads(ws.receive_text())["reason"]
    assert len(compiles) == 1
    assert caplog.text.count("does not compile") == 1


def test_a_closed_outbox_closes_the_socket_with_1008(monkeypatch):
    class Unread(Outbox):  # sends nothing, so the backlog fills
        async def pump(self, ws):
            self._sender = asyncio.current_task()
            await asyncio.Event().wait()

    monkeypatch.setattr("pewpew.studio.app.Outbox", Unread)
    monkeypatch.setattr("pewpew.studio.transport.MAX_CONTROL_BACKLOG", 3)
    with TestClient(make_app()) as c, connect(c) as ws:
        for i in range(6):
            ws.send_text(json.dumps({"type": "export", "id": i}))
        event = ws.receive()
        assert event["type"] == "websocket.close" and event["code"] == 1008


def test_a_visits_book_is_held_to_the_size_of_a_share():
    session = stepped(RecordingSink(), max_book_bytes=CHOSEN_BOOK.size() + 100)
    looks = session._aura.looks  # the loop thread's, called here with no loop running
    assert looks is not None
    try:
        assert "limited to" in str(looks.save("copy"))
        assert looks.rename("tide", "t") is None  # smaller: always allowed
        assert [name for name in looks.book.looks] == ["t", "warp-lane"]
        assert looks.book.size() <= CHOSEN_BOOK.size() + 100
    finally:
        session.close()
    plain = stepped(RecordingSink())  # by default, a share's limit
    try:
        assert plain._aura.looks is not None and plain._aura.looks._max_bytes == MAX_BODY_BYTES
    finally:
        plain.close()


def test_at_the_book_limit_a_recall_lands_and_a_favorite_or_fade_is_refused(caplog):
    book = CHOSEN_BOOK.with_current("tide")  # "warp-lane" is the longer name
    session = stepped(RecordingSink(), book=book, max_book_bytes=book.size())
    looks = session._aura.looks
    assert looks is not None
    try:
        assert looks.recall("warp-lane") is None
        assert looks.book.current == "warp-lane" and "still names" not in caplog.text
        assert "limited to" in str(looks.set_favorite("tide", True))
        assert "limited to" in str(looks.set_fade("tide", 12.34567))
        assert looks.book.current == "warp-lane"
    finally:
        session.close()


def test_a_refused_set_names_the_range_and_never_a_path_and_the_loop_survives(client, ws):
    knob = first_knob(ws)
    ws.send_text(json.dumps({"type": "set", "name": knob["name"], "value": 1e9}))
    refused = read_until(ws, is_type("refused"))
    assert (refused["control"], refused["name"]) == ("set", knob["name"])
    assert "/" not in refused["reason"] and ".py" not in refused["reason"]
    ws.send_text(json.dumps({"type": "set", "name": ["unhashable"], "value": 1, "id": 1}))
    assert read_until(ws, is_type("refused"))["id"] == 1
    read_until(ws, is_frame)
    assert session_of(client).alive


def test_a_set_by_address_reaches_the_layer_and_is_echoed_in_params(client, ws):
    name = "layers.sparks.sparks.rate"
    ws.send_text(json.dumps({"type": "set", "name": name, "value": 12.5, "id": 3}))
    assert read_until(ws, is_type("ack"))["control"] == "set"
    read_until(ws, lambda m: is_type("params")(m) and m["values"][name] == 12.5)
    assert session_of(client).control.values()[name] == 12.5


def test_a_typed_set_over_the_socket_is_echoed_in_its_json_form(ws):
    name = "layers.sparks.glint.palette"
    stops = [{"at": 0, "h": 0, "s": 1, "v": 1}, {"at": 1, "h": 240, "s": 1, "v": 1}]
    ws.send_text(json.dumps({"type": "set", "name": name, "value": {"stops": stops}}))
    read_until(ws, lambda m: is_type("params")(m) and m["values"][name]["stops"][1]["h"] == 240.0)
    ws.send_text(json.dumps({"type": "set", "name": name, "value": 3}))
    refused = read_until(ws, is_type("refused"))
    assert (refused["control"], refused["name"]) == ("set", name)


def test_a_huge_integer_set_is_refused_and_the_socket_stays_open(ws):
    knob = first_knob(ws)
    ws.send_text(f'{{"type":"set","name":"{knob["name"]}","value":{"9" * 400}}}')
    refused = read_until(ws, is_type("refused"))
    assert refused["name"] == knob["name"] and "finite" in refused["reason"]
    read_until(ws, is_frame)


def test_the_session_sends_the_status_and_each_state_after_the_hello(ws):
    status = read_until(ws, is_type("status"))
    assert status == {"type": "status", "error": None, "source": None, "path": None}
    for kind in ("declare", "params", "aura", "catalog"):
        read_until(ws, is_type(kind))


def test_the_power_reading_of_a_rig_with_a_power_block():
    capped = share.envelope(ring(3), BOOK, CHOSEN)
    capped["arrangement"]["power"] = {"max_brightness": 0.184}
    with TestClient(make_app()) as c, connect(c, shared(c, capped)) as ws:
        ws.receive_text()
        power = read_until(ws, is_type("power"))
        assert power["uncapped_watts"] > 0 and power["watts"] == pytest.approx(0.184 * power["uncapped_watts"])


# -- pausing, admission and the socket's own limits -------------------------------------


def test_pause_and_resume_freeze_engine_time(client, ws):
    read_until(ws, is_frame)
    session = session_of(client)
    ws.send_text(json.dumps({"type": "pause"}))
    assert wait_for(lambda: session.paused)
    time.sleep(0.1)
    t0 = session.t
    time.sleep(0.15)
    assert session.t == t0
    ws.send_text(json.dumps({"type": "resume"}))
    assert wait_for(lambda: session.t > t0)


def test_a_request_while_paused_is_refused_at_once(client, ws):
    ws.send_text(json.dumps({"type": "pause"}))
    assert wait_for(lambda: session_of(client).paused)
    start = time.monotonic()
    ws.send_text(json.dumps({"type": "set", "value": 1}))  # no id, no knob: passed over, as when running
    ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "id": 4}))
    refused = read_until(ws, is_type("refused"))
    assert (refused["control"], refused["id"]) == ("look", 4) and "paused" in refused["reason"]
    assert time.monotonic() - start < 2


def test_an_idle_session_pauses_and_a_message_resumes_it():
    with TestClient(make_app(idle_timeout_s=0.2)) as c, connect(c) as ws:
        ws.receive_text()
        session = session_of(c)
        assert wait_for(lambda: session.paused)
        ws.send_text(json.dumps({"type": "set", "name": "x", "value": 1}))
        assert wait_for(lambda: not session.paused)


def test_a_paused_session_closes_after_the_paused_deadline():
    with TestClient(make_app(paused_timeout_s=0.3)) as c, connect(c) as ws:
        ws.receive_text()
        ws.send_text(json.dumps({"type": "pause"}))
        refused = read_until(ws, is_type("refused"))
        assert refused["control"] == "session" and "paused" in refused["reason"]
        assert wait_for(lambda: len(state_of(c).admission) == 0 and len(state_of(c).sessions) == 0)


def test_an_idle_session_pauses_then_closes():
    with TestClient(make_app(idle_timeout_s=0.1, paused_timeout_s=0.2)) as c, connect(c) as ws:
        ws.receive_text()
        assert read_until(ws, is_type("refused"))["control"] == "session"
        assert wait_for(lambda: len(state_of(c).admission) == 0)


def test_the_per_address_socket_limit():
    with TestClient(make_app()) as c:
        h = {"Fly-Client-IP": "3.3.3.3"}
        opened = [connect(c, headers=h) for _ in range(3)]
        sockets = [o.__enter__() for o in opened]
        try:
            for ws in sockets:
                assert json.loads(ws.receive_text())["type"] == "hello"
            with connect(c, headers=h) as fourth:
                msg = json.loads(fourth.receive_text())
                assert msg["type"] == "refused" and "3 open sessions" in msg["reason"]
            with connect(c, headers={"Fly-Client-IP": "4.4.4.4"}) as other:
                assert json.loads(other.receive_text())["type"] == "hello"
        finally:
            for o in opened:
                o.__exit__(None, None, None)


def test_the_global_session_cap():
    with (
        TestClient(make_app(limits=Limits(max_sessions=1))) as c,
        connect(c, headers={"Fly-Client-IP": "5.5.5.5"}) as a,
    ):
        a.receive_text()
        with connect(c, headers={"Fly-Client-IP": "6.6.6.6"}) as b:
            assert "1 live sessions" in json.loads(b.receive_text())["reason"]


def test_a_full_server_evicts_the_session_paused_longest():
    with TestClient(make_app(limits=Limits(max_sessions=2))) as c:
        sessions = state_of(c).sessions
        with connect(c, headers={"Fly-Client-IP": "7.7.7.1"}) as a:
            a.receive_text()
            a.send_text(json.dumps({"type": "pause"}))
            assert wait_for(lambda: sessions.sessions()[0].paused)
            first = sessions.sessions()[0]
            with connect(c, headers={"Fly-Client-IP": "7.7.7.2"}) as b:
                b.receive_text()
                b.send_text(json.dumps({"type": "pause"}))
                assert wait_for(lambda: len(sessions) == 2 and all(s.paused for s in sessions.sessions()))
                second = next(s for s in sessions.sessions() if s is not first)
                with connect(c, headers={"Fly-Client-IP": "7.7.7.3"}) as newcomer:
                    assert json.loads(newcomer.receive_text())["type"] == "hello"
                    refused = read_until(a, is_type("refused"))
                    assert refused["control"] == "session" and "make room" in refused["reason"]
                    assert second in sessions.sessions() and first not in sessions.sessions()
                    assert len(state_of(c).admission) == 2


def test_ipv6_addresses_count_per_64():
    assert address_key("2001:db8::1") == address_key("2001:db8::ffff:1") == "2001:db8::/64"
    assert address_key("2001:db8:0:1::1") != address_key("2001:db8::1")
    assert address_key("::ffff:192.0.2.1") == "192.0.2.1"
    assert address_key("192.0.2.1") == "192.0.2.1" and address_key("testclient") == "testclient"
    with TestClient(make_app()) as c:
        opened = [connect(c, headers={"Fly-Client-IP": f"2001:db8::{i}"}) for i in range(1, 4)]
        try:
            for ws in [o.__enter__() for o in opened]:
                assert json.loads(ws.receive_text())["type"] == "hello"
            with connect(c, headers={"Fly-Client-IP": "2001:db8::4"}) as fourth:
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
        with connect(c) as ws, pytest.raises(WebSocketDisconnect):
            ws.receive_text()
        assert wait_for(lambda: len(state_of(c).admission) == 0)
        monkeypatch.undo()
        with connect(c) as ws:
            assert json.loads(ws.receive_text())["type"] == "hello"


def test_an_oversized_websocket_message_is_refused(ws):
    ws.send_text("x" * (256 * 1024 + 1))
    refused = read_until(ws, is_type("refused"))
    assert refused["control"] == "message" and "262144" in refused["reason"]


def test_message_size_is_counted_in_bytes(ws):
    text = "\U0001f600" * 70_000  # 70,000 characters, 280,000 bytes
    assert len(text) < 256 * 1024 < len(text.encode())
    ws.send_text(text)
    assert read_until(ws, is_type("refused"))["control"] == "message"


def test_closing_the_socket_stops_the_session_thread(client):
    with connect(client) as ws:
        ws.receive_text()
        session = session_of(client)
    assert wait_for(lambda: not session.alive)
    assert wait_for(lambda: len(state_of(client).sessions) == 0)


def test_close_all_stops_every_loop_inside_the_deadline(client):
    with connect(client) as ws:
        ws.receive_text()
        session = session_of(client)
        start = time.monotonic()
        state_of(client).sessions.close_all()
        assert not session.alive and time.monotonic() - start < 5


def test_the_rate_limiter_table_is_bounded_and_drops_idle_keys():
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


# -- the session on its own ---------------------------------------------------------------

CHOSEN_BOOK = share.chosen(BOOK, CHOSEN)


class RecordingSink:
    def __init__(self):
        self.controls = []
        self.frames = []

    def frame(self, payload):
        self.frames.append(payload)

    def control(self, message):
        self.controls.append(message)

    def closed(self):
        pass


def stepped(sink, mapping=None, limiter=None, book=CHOSEN_BOOK, **kw) -> Session:
    """A session on `mapping` (default a plane of 8) that a test steps itself, paced on fake time, so
    no slot is skipped; never started. `limiter` is the rig's power limit, made once."""
    made = None if limiter is None else (lambda: limiter)
    shared = Shared(plane(8) if mapping is None else mapping, None, None, made, book)
    session = Session(sink, shared, **{"fps": FPS, **kw})
    clock = FakeTime()
    session._loop._now, session._loop._sleep = clock.now, clock.sleep
    return session


def test_a_session_starts_in_the_first_look_that_runs_when_the_current_one_cannot():
    sink = RecordingSink()
    book = share.chosen(BOOK, ["copper-tide", "tide"]).with_current("tide")
    session = stepped(sink, STRIP, book=book)  # tide folds a plane: a strip has none
    session._loop.run(frames=1)
    aura = json.loads(sink.frames[-1].texts[4])
    copper = [layer.id for layer in BOOK.looks["copper-tide"].layers]
    assert [layer["id"] for layer in aura["stack"]["layers"]] == copper
    assert aura["looks"]["current"] is None  # it runs as a sent look: no look is current
    with pytest.raises(NoLook):
        stepped(sink, STRIP, book=share.chosen(BOOK, ["tide"]))


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
        assert isinstance(second, Refusal) and "still being made" in second.reason
    finally:
        made.set()
        session.close()
    assert first.result(timeout=5.0) is not None  # refused: nothing was made


def test_the_cap_runs_after_the_master_and_streams_both_power_readings():
    class Halve:
        cap = PowerCap(max_brightness=0.5)

        def __init__(self):
            self.seen = []

        def __call__(self, frame):
            self.seen.append(frame.copy())
            return Limited(frame * np.float32(0.5), 0.5, 1.0, 2.0)

    sink, halve = RecordingSink(), Halve()
    session = stepped(sink, limiter=cast(PowerLimiter, halve), fps=POWER_HZ)  # a power reading every frame
    session._loop.run(frames=2)
    assert session._loop._after == (session._aura.master.apply, session._meter)
    assert sink.frames[-1].data[8:] == to_display_u8(halve.seen[-1] * np.float32(0.5)).tobytes()
    assert json.loads(sink.frames[-1].texts[POWER]) == {"type": "power", "watts": 1.0, "uncapped_watts": 2.0}
    assert session.control.master(0.0) is None
    session._loop.run(frames=1)
    assert not halve.seen[-1].any()  # the limiter gets the frame at the master's level


def test_a_failed_frame_is_dropped_and_the_cap_holds():
    class Flaky(RecordingSink):
        failed = False

        def frame(self, payload):
            if not self.failed:
                self.failed = True
                raise RuntimeError("socket hiccup")
            self.frames.append(payload.data)

    sink = Flaky()
    session = stepped(sink, limiter=PowerLimiter(PowerCap(max_brightness=0.0)))
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
    session = stepped(RecordingSink(), limiter=cast(PowerLimiter, counting))
    session._loop.run(frames=3 * session._meter.every)
    assert counting.calls == 3


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
    assert texts["power"] is None  # nor a power reading without a limiter
    assert texts["arrangement"] is None and texts["report"] is None  # nor a rig file
    assert json.loads(texts["aura"])["master"] == BOOK.looks["tide"].master  # the start look's master


def test_two_sessions_with_one_seed_stream_the_same_frames():
    """Engine time comes from the slots, and every seed is injected: same inputs, same bytes."""
    a, b = RecordingSink(), RecordingSink()
    for sink in (a, b):
        stepped(sink, seed=5)._loop.run(frames=6)
    assert [f.data[8:] for f in a.frames] == [f.data[8:] for f in b.frames]
    assert any(f.data[8:] != a.frames[0].data[8:] for f in a.frames)  # and the look moves


# -- the outbox ------------------------------------------------------------------------------


class _Recorder:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def send_bytes(self, data):
        self.sent.append(data)


def test_an_ack_keeps_the_frame_queued_before_it_and_the_states_go_only_on_a_change():
    status = message("status", status_state(None))
    declare = message("declare", [{"name": "layers.base.osc.freq", "kind": "float"}])

    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        ws = _Recorder()
        pump = asyncio.ensure_future(box.pump(cast(Any, ws)))
        box.frame(FramePayload(b"ONE", (status, declare)))
        await asyncio.sleep(0.01)
        box.frame(FramePayload(b"OLD", (status, declare)))
        box.control({"type": "ack", "id": 1})
        await asyncio.sleep(0.01)
        box.frame(FramePayload(b"NEW", (status, declare)))
        await asyncio.sleep(0.01)
        box.close_with({"type": "bye"})
        await asyncio.wait_for(pump, 1)
        return ws.sent

    sent = asyncio.run(scenario())
    kinds = [m if isinstance(m, bytes) else m["type"] for m in sent]
    assert kinds == [b"ONE", "status", "declare", "ack", b"OLD", b"NEW", "bye"]


class _Stuck:
    """A client that reads nothing once its first `reads` sends have gone: each later send never returns."""

    def __init__(self, reads: int = 1):
        self.reads = reads
        self.sent: list[Any] = []

    async def send_text(self, text):
        await self._send(json.loads(text) if text.startswith("{") else text)

    async def send_bytes(self, data):
        await self._send(data)

    async def _send(self, message):
        if len(self.sent) >= self.reads:
            await asyncio.Event().wait()
        self.sent.append(message)


def test_the_outbox_holds_its_bytes_and_overflow_stops_a_send_that_never_returns():
    async def scenario():
        box = Outbox(asyncio.get_running_loop(), max_bytes=10_000)
        ws = _Stuck(reads=0)
        pump = asyncio.ensure_future(box.pump(cast(Any, ws)))
        box.control("x" * 50_000)  # over the cap, into an empty queue: a big rig's hello
        await asyncio.sleep(0.01)
        assert box.queued == 50_000 and not pump.done()  # held in a send the client does not read
        box.control({"type": "exported", "file": "y" * 100})
        await asyncio.sleep(0.01)
        assert box.overflow and box.queued == 0
        await asyncio.wait_for(asyncio.gather(pump, return_exceptions=True), 1)
        return pump

    assert asyncio.run(scenario()).cancelled()


def test_an_export_counts_until_it_is_sent_and_the_backlog_counts_messages():
    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        ws = _Stuck(reads=1)
        pump = asyncio.ensure_future(box.pump(cast(Any, ws)))
        box.control({"type": "exported", "id": 1})
        await asyncio.sleep(0.01)
        assert box.exports == 0 and ws.sent == [{"type": "exported", "id": 1}]
        box.control({"type": "exported", "id": 2})
        await asyncio.sleep(0.01)
        assert box.exports == 1  # stuck in its send
        for i in range(MAX_CONTROL_BACKLOG):
            box.control({"type": "ack", "id": i})
        await asyncio.sleep(0.01)
        assert box.overflow
        await asyncio.wait_for(asyncio.gather(pump, return_exceptions=True), 1)

    asyncio.run(scenario())


class _Client:
    """A websocket whose client sends `messages` and then waits, and reads nothing."""

    def __init__(self, messages: list[dict], box: Outbox):
        self.inbound = [{"type": "websocket.receive", "text": json.dumps(m)} for m in messages]
        self.box = box
        self.peak = 0
        self.stuck = _Stuck(reads=0)

    async def receive(self):
        self.peak = max(self.peak, self.box.queued)
        if self.inbound:
            return self.inbound.pop(0)
        await asyncio.Event().wait()

    async def send_text(self, text):
        await self.stuck.send_text(text)

    async def send_bytes(self, data):
        await self.stuck.send_bytes(data)


def live(sink, book=CHOSEN_BOOK) -> Session:
    """A started session on a plane of 8, on the wall clock."""
    session = Session(sink, Shared(plane(8), None, None, None, book), fps=FPS)
    session.start()
    return session


def test_a_client_that_reads_nothing_and_asks_256_exports_is_closed_with_bounded_memory():
    book = share.chosen(BOOK, list(BOOK.looks)[:6])  # the 6 example looks that start on a plane

    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        session = live(box, book)
        client = _Client([{"type": "export", "id": i} for i in range(256)], box)
        box.control(session.hello())
        pump = asyncio.ensure_future(box.pump(cast(Any, client)))
        visitor = _Visitor(cast(Any, client), session, box, pump, MAX_BODY_BYTES, 60.0, 60.0, RateLimiter(10, 3), "a")
        try:
            await asyncio.wait_for(visitor.serve(), 10)
        finally:
            session.close()
            pump.cancel()
        return client, box

    client, box = asyncio.run(scenario())
    assert box.overflow and not client.inbound and client.stuck.sent == []
    assert 0 < client.peak <= MAX_CONTROL_BYTES  # the hello, one export and the refusals of the rest


def test_a_second_export_while_one_is_on_its_way_is_refused():
    async def scenario():
        box = Outbox(asyncio.get_running_loop())
        session = live(box)
        client = _Client([{"type": "export", "id": 1}, {"type": "export", "id": 2}], box)
        client.stuck.reads = 99
        pump = asyncio.ensure_future(box.pump(cast(Any, client)))
        hold = asyncio.Event()
        real_send = client.stuck.send_text

        async def slow(text):  # the first export's send is held until the second is answered
            if json.loads(text).get("type") == "exported":
                await hold.wait()
            await real_send(text)

        client.send_text = slow
        visitor = _Visitor(cast(Any, client), session, box, pump, MAX_BODY_BYTES, 60.0, 60.0, RateLimiter(10, 3), "a")
        serving = asyncio.ensure_future(visitor.serve())
        # The refusal of export 2 queues behind export 1, which is held in its send.
        for _ in range(200):
            await asyncio.sleep(0.01)
            if box.exports == 1 and len(box._control) >= 2:
                break
        assert box.exports == 1 and len(box._control) >= 2
        hold.set()
        for _ in range(200):
            await asyncio.sleep(0.01)
            if any(isinstance(m, dict) and m.get("id") == 2 for m in client.stuck.sent):
                break
        serving.cancel()
        pump.cancel()
        session.close()
        return client.stuck.sent

    sent = asyncio.run(scenario())
    answers = {m["id"]: m for m in sent if isinstance(m, dict) and m.get("id") in (1, 2)}
    assert answers[2]["type"] == "refused" and answers[2]["reason"] == EXPORTING
    assert answers[1]["type"] == "exported"


# -- the wire contract ------------------------------------------------------------------------

SESSION_GOLDEN = ROOT / "tests" / "goldens" / "session.json"
CARDS = ("osc", "kaleid")  # the catalog cards the golden keeps, so an op added to the catalog does not change it
BUILD = "0123456789abcdef"  # the hello's build stamp follows the page; the golden holds this one
DIGEST = "0" * 64  # the rig's catalog digest follows every catalog entry; the golden holds this one
POWER_READING = {"watts": 1.5, "uncapped_watts": 2.0}  # the reading follows the frame; the golden holds this one


def capture_session() -> dict:
    """What a visitor is sent over `/ws?a={id}`, as the golden holds it: the greeting (the hello,
    then each per-frame state once), a `power` reading, the `exported` answer to an export of
    every look, and the `refused` message of each control the Gallery adds (`session`, `message`)
    and of a request made while paused."""
    capped = share.envelope(ring(3), BOOK, CHOSEN)
    capped["arrangement"]["power"] = {"max_brightness": 0.5}
    app = make_app(limits=Limits(max_sessions=1))
    with TestClient(app) as c:
        id_ = shared(c, capped)
        with connect(c, id_, headers={"Fly-Client-IP": "1.1.1.1"}) as ws:
            greeting = [json.loads(ws.receive_text())]
            while greeting[-1]["type"] != "catalog":  # the last of the states a frame brings first
                greeting.append(read_until(ws, lambda m: not is_frame(m)))
            hello = greeting[0]
            hello["build"] = BUILD
            hello["rig"]["catalog_digest"] = DIGEST
            # The live values are read at the engine time of whichever frame the mailbox kept.
            mod = next(m for m in greeting if m["type"] == "mod")
            mod["values"] = dict.fromkeys(mod["values"], 0.0)
            catalog = greeting[-1]
            catalog["cards"] = [card for card in catalog["cards"] if card["name"] in CARDS]
            power = {**read_until(ws, is_type("power")), **POWER_READING}
            ws.send_text(json.dumps({"type": "export", "looks": None, "share": False, "id": 1}))
            exported = read_until(ws, is_type("exported"))
            ws.send_bytes(b"\x00")
            refused_message = read_until(ws, is_type("refused"))
            with connect(c, id_, headers={"Fly-Client-IP": "2.2.2.2"}) as full:
                session = json.loads(full.receive_text())
            ws.send_text(json.dumps({"type": "pause"}))
            assert wait_for(lambda: session_of(c).paused)
            ws.send_text(json.dumps({"type": "look", "look": LOOKS["warp-lane"], "id": 4}))
            paused = read_until(ws, is_type("refused"))
    return {
        "greeting": greeting,
        "power": power,
        "exported": exported,
        "refused": {"session": session, "message": refused_message, "paused": paused},
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
    """The Gallery's greeting is the engine's, on the shared rig and with its own capabilities."""
    golden = json.loads(SESSION_GOLDEN.read_text())
    assert set(golden) == {"greeting", "power", "exported", "refused"}
    assert [m["type"] for m in golden["greeting"]] == ["hello", "status", "declare", "params", "mod", "aura", "catalog"]
    hello = golden["greeting"][0]
    assert hello["capabilities"] == CAPABILITIES and hello["rig"] is not None and hello["room"] is not None
    assert hello["n"] == len(hello["positions"]) == 192
    assert set(golden["power"]) == {"type", "watts", "uncapped_watts"}
    exported = golden["exported"]
    assert set(exported) == {"type", "id", "file", "gallery"} and exported["gallery"] is None
    assert list(exported["file"]["looks"]) == list(CHOSEN)
    assert {r["control"] for r in golden["refused"].values()} == {"session", "message", "look"}


def test_the_golden_rig_is_a_rig_view():
    rig = json.loads(SESSION_GOLDEN.read_text())["greeting"][0]["rig"]
    assert rig_models.RigView.model_validate(rig).model_dump(mode="json") == rig


def test_the_default_share_is_the_packaged_golden_rings():
    """`/` runs the arrangement the old studio page opened with."""
    golden_rings = json.loads((EXAMPLES / "golden-rings.json").read_text())
    calls = []
    app = create_app(store=SqliteStore(":memory:"), compile=counting_compile(calls), fps=FPS)
    with TestClient(app) as c, connect(c) as ws:
        assert json.loads(ws.receive_text())["n"] == 48 * 64
    assert calls == [golden_rings]


def test_an_app_without_example_looks_does_not_start(tmp_path):
    with pytest.raises(RuntimeError, match="no example looks"):
        create_app(examples=tmp_path)
