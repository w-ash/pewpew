"""PreviewSink protocol tests: real loopback sockets, no browser.

Ephemeral ports (port=0) so tests never collide; the sink's RateGate runs
on fake time so nothing here sleeps for pacing. The stall-isolation
guarantee itself (submit never blocks) is SinkDriver's, proven in
tests/test_sink_driver.py — here we prove the sink wires one driver per
client and contains a dead client without losing the live ones.
"""

from __future__ import annotations

import gzip
import hashlib
import http.client
import json
import re
import shutil
import socket
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pytest
from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

from fakes import (
    LEGACY_ROOM,
    FakeTime,
    LoopThread,
    arrangement,
    aura_rig,
    bar,
    client_for,
    greet,
    next_of,
    next_text,
    no_watch,
    peers,
    preview_sink,
    wait_until,
)
from pewpew.aura.master import Master
from pewpew.errors import Refusal
from pewpew.mapping import grid, line
from pewpew.params import HSV, Bool, Color, Float, Int, ParamSet
from pewpew.rig import load_catalog
from pewpew.rig.runtime import compile_doc, plan_view, rig_view
from pewpew.room.live import RigLive
from pewpew.sinks import preview
from pewpew.sinks.preview import PreviewSink
from pewpew.sinks.sink import DISPLAY_GAMMA, to_display_u8


class Knobs:
    """A param set of two sliders."""

    speed = Float(0.5, 0.0, 2.0, "/s", help="Cycles of the field per second")
    scale = Float(4.0, 1.0, 10.0, help="How many ripples fit across the map; higher is finer")


class Tint:
    """A param set of one color."""

    color = Color((200.0, 1.0, 1.0), help="The color of the crests")


class FakeControl:
    """A Control that applies each request on the calling thread: a set to
    a real ParamSet, a recall to a list of look names, the master and blackout to a
    real Master; any other request is recorded and answered from `replies`.
    The real AuraControl, with its loop-thread discipline, is
    tests/test_aura_control.py's."""

    capabilities = ()

    def __init__(self, knobs=Knobs, cap: float = 1.0, health=None, replies=None) -> None:
        self.params = ParamSet(knobs)
        self.master_ = Master(cap)
        self.current = "calm"
        self.looks = ["calm", "warm"]
        self.calls: list[dict] = []
        self.health_ = health
        self.replies = dict(replies or {})
        self.mods: dict[str, float] = {}
        self.mod_reads = 0
        self.catalog_: dict = {"cards": [], "blends": []}

    def describe(self) -> list[dict]:
        return self.params.describe()

    def values(self) -> dict:
        return self.params.snapshot_json()

    def mod(self) -> dict:
        self.mod_reads += 1
        return dict(self.mods)

    def state(self) -> dict:
        return {
            "looks": {"current": self.current, "items": [{"name": name} for name in self.looks]},
            "master": self.master_.level, "cap": self.master_.cap, "blackout": self.master_.blackout,
        }

    def health(self) -> dict | None:
        return self.health_() if self.health_ is not None else None

    def catalog(self) -> dict:
        return self.catalog_

    def arrangement(self) -> dict | None:
        return None

    def report(self) -> dict | None:
        return None

    def request(self, message: dict) -> Refusal | None:
        self.calls.append(dict(message))
        kind = message.get("type")
        if kind == "set":
            name, value = message.get("name"), message.get("value")
            reason = self.params.check(name, value)
            if reason is None:
                self.params.set(name, value)
                return None
            return Refusal(reason, name)
        reason = self._answer(kind, message)
        return None if reason is None else Refusal(reason)

    def _answer(self, kind, message: dict) -> str | None:
        if kind == "recall":
            name = message.get("name")
            if name not in self.looks:
                return f"no look {name!r}"
            self.current = name
            return None
        if kind == "master":
            reason = self.master_.check(message.get("value"))
            if reason is None:
                self.master_.set(message["value"])
            return reason
        if kind == "blackout":
            if not isinstance(message.get("on"), bool):
                return "blackout takes true or false"
            self.master_.set_blackout(message["on"])
            return None
        return self.replies.get(kind)


def test_hello_carries_positions_once():
    with preview_sink(grid(4, 4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["type"] == "hello"
            assert hello["n"] == hello["total"] == 16
            assert hello["is3d"] is False
            assert hello["positions"] == np.round(grid(4, 4).astype(np.float64), 4).tolist()


def test_hello_decimates_past_max_pixels_deterministically():
    with preview_sink(line(100), max_pixels=10) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["n"] == 10 and hello["total"] == 100
            assert hello["positions"][0] == [0.0, 0.0, 0.0]
            assert hello["positions"][-1] == [1.0, 0.0, 0.0]


def test_binary_frame_is_gamma_quantized_uint8_with_t_header():
    n = 8
    frame = np.zeros((n, 3), dtype=np.float32)
    frame[:, 1] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    with preview_sink(line(n)) as sink:
        ws, _ = client_for(sink)
        with ws:
            sink.send(0.5, frame)
            data = ws.recv(timeout=5.0)
            assert isinstance(data, bytes)
            t, seq = struct.unpack("<fI", data[:8])
            assert t == 0.5 and seq == 1
            assert data[8:] == to_display_u8(frame).tobytes()


def test_stalled_client_never_stalls_loop_or_other_clients():
    n = 4
    frame = np.full((n, 3), 0.5, dtype=np.float32)
    with preview_sink(line(n)) as sink:
        dead_ws, _ = client_for(sink)
        live_ws, _ = client_for(sink)
        with live_ws:
            dead_sock = dead_ws.socket
            dead_sock.close()  # yank the transport out from under its driver
            for i in range(5):
                sink.send(float(i), frame)  # must return promptly regardless
            # The live client still receives frames.
            assert isinstance(live_ws.recv(timeout=5.0), bytes)
        wait_until(lambda: len(peers(sink)) <= 1)  # dead client reaped


def test_remap_resends_positions_before_the_first_frame_drawn_on_them():
    with preview_sink(line(4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            sink.remap(grid(3, 2))
            sink.send(0.0, np.zeros((4, 3), dtype=np.float32))  # rendered before the remap: dropped
            sink.send(0.1, np.full((6, 3), 0.5, dtype=np.float32))
            layout = json.loads(ws.recv(timeout=5.0))
            assert layout["type"] == "layout"
            assert layout["n"] == layout["total"] == 6
            assert layout["positions"] == np.round(grid(3, 2).astype(np.float64), 4).tolist()
            data = ws.recv(timeout=5.0)
            assert isinstance(data, bytes) and len(data) == 8 + 6 * 3
            assert struct.unpack("<fI", data[:8])[0] == pytest.approx(0.1)
        # A page opened after the remap gets the new positions in its hello
        # and no layout message.
        ws, hello = client_for(sink)
        with ws:
            assert hello["total"] == 6
            sink.send(0.2, np.full((6, 3), 0.5, dtype=np.float32))
            assert isinstance(ws.recv(timeout=5.0), bytes)


def test_status_message_sent_on_error_change():
    # Frames may coalesce (newest-wins per client), so assert the status
    # *sequence*, not exact frame counts: one "boom", then one null — an
    # unchanged status between the two produces no duplicate message.
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    state: list[tuple[str, str, str | None] | None] = [None]

    with preview_sink(line(n), status=lambda: state[0]) as sink:
        ws, _ = client_for(sink)
        with ws:
            state[0] = ("render", "boom", "layers.base.plasma")
            sink.send(0.0, frame)
            assert next_text(ws) == {
                "type": "status", "error": "boom", "source": "render", "path": "layers.base.plasma",
            }
            sink.send(1 / 30, frame)  # unchanged: no status message
            state[0] = None
            sink.send(2 / 30, frame)  # cleared: the next status is null,
            # not a second "boom"
            assert next_text(ws) == {"type": "status", "error": None, "source": None, "path": None}


def test_a_new_client_gets_the_display_gamma_then_the_declarations_then_the_values():
    controls = FakeControl()
    with preview_sink(line(4), control=controls) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["hello"]["display_gamma"] == DISPLAY_GAMMA
            assert "params" not in greeting["hello"]
            assert greeting["declare"]["params"] == ParamSet(Knobs).describe()
            assert greeting["params"]["values"] == {"speed": 0.5, "scale": 4.0}
            speed = greeting["declare"]["params"][0]
            # The slider is built from these: endpoints and quantization must
            # all be on the wire, or the page has to invent them.
            assert speed["name"] == "speed" and speed["label"] == "Speed"
            assert (speed["lo"], speed["hi"]) == (0.0, 2.0)
            assert speed["step"] > 0.0 and speed["decimals"] >= 0


def test_a_client_without_controls_gets_the_hello_and_the_status_only():
    with preview_sink(line(4)) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert set(greeting) == {"hello", "status"}
            assert greeting["status"] == {"type": "status", "error": None, "source": None, "path": None}


def test_accepted_set_reaches_the_controls_and_echoes_to_every_client():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControl()
    with preview_sink(line(n), control=controls) as sink:
        setter, _ = client_for(sink)
        watcher, _ = client_for(sink)
        with setter, watcher:
            setter.send(json.dumps({"type": "set", "name": "speed", "value": 1.75}))
            wait_until(lambda: controls.calls)
            sink.send(0.0, frame)
            # The tab that never touched a slider learns what won: §5's
            # last-write-wins with the merged state pushed to every client.
            echo = next_text(watcher)
            assert echo == {"type": "params", "values": {"speed": 1.75, "scale": 4.0}}
            assert next_text(setter) == echo


def test_a_change_of_declarations_rebuilds_the_controls_then_fills_them():
    """A layer edit that adds or retunes a param. The client gets a `declare`
    (value-free) and then the `params` echo *even though* its text is the
    same as the last one sent — the rebuilt sliders are empty until it lands.
    An unchanged frame sends neither."""

    class Retuned(Knobs):
        gain = Float(0.5, 0.0, 1.0, label="Gain")

    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControl()
    with preview_sink(line(n), control=controls) as sink:
        ws, _hello = client_for(sink)
        with ws:
            # One frame at a time: back-to-back sends coalesce in the client's
            # driver (newest wins), which is not what is under test here.
            sink.send(0.0, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            sink.send(1 / 60, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            # Same declarations, same values: nothing but frames so far
            # (a text after the last frame would come before the next one).

            controls.params = ParamSet(Retuned)  # what a recall of a look with other knobs does
            sink.send(2 / 60, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            declare = next_text(ws)
            assert declare["type"] == "declare"
            assert [p["name"] for p in declare["params"]] == ["speed", "scale", "gain"]
            assert all("value" not in p for p in declare["params"])
            assert declare["params"][2]["label"] == "Gain"
            echo = next_text(ws)
            assert echo == {"type": "params", "values": {"speed": 0.5, "scale": 4.0, "gain": 0.5}}
            # Steady state again: the next frames bring no text.
            for t in (3 / 60, 4 / 60):
                sink.send(t, frame)
                assert isinstance(ws.recv(timeout=5.0), bytes)


def test_a_value_that_changes_kind_is_sent_in_its_new_kind():
    """An edit turns `Int(1, 0, 1)` into `Bool(True)`: 1 == True in
    Python, but the page's bool reads only `true`, so the text must change."""

    class Before:
        invert = Int(1, 0, 1)
        level = Float(1.0, 0.0, 2.0)

    class After:
        invert = Bool(True)
        level = Int(1, 0, 2)

    frame = np.zeros((4, 3), dtype=np.float32)
    controls = FakeControl(Before)
    with preview_sink(line(4), control=controls) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["params"]["values"] == {"invert": 1, "level": 1.0}
            controls.params = ParamSet(After)
            sink.send(0.0, frame)
            assert next_text(ws)["type"] == "declare"
            assert json.dumps(next_text(ws)) == '{"type": "params", "values": {"invert": true, "level": 1}}'


def test_a_color_set_echoes_its_json_value():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControl(Tint)
    with preview_sink(line(n), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "set", "name": "color", "value": {"h": 30, "s": 0.5, "v": 1}}))
            wait_until(lambda: controls.calls)
            sink.send(0.0, frame)
            echo = next_text(ws)
            assert echo["values"]["color"] == {"h": 30.0, "s": 0.5, "v": 1.0}
            assert controls.params["color"] == HSV(30.0, 0.5, 1.0)


def test_a_refused_color_names_its_part_and_never_a_path():
    controls = FakeControl(Tint)
    with preview_sink(line(4), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            value = {"h": 30, "s": 2.0, "v": 1}
            ws.send(json.dumps({"type": "set", "name": "color", "value": value}))
            reply = next_text(ws)
            assert reply == {"type": "refused", "control": "set", "name": "color", "id": None,
                             "reason": "tint.color.s must be within 0.0..1.0, got 2.0"}


def test_refused_set_names_the_range_but_never_a_source_path():
    controls = FakeControl()
    with preview_sink(line(4), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "set", "name": "scale", "value": 99.0}))
            reply = next_text(ws)
            assert reply["type"] == "refused" and reply["name"] == "scale"
            assert reply["control"] == "set"
            assert reply["reason"] == controls.params.check("scale", 99.0)
            assert "1.0..10.0" in reply["reason"]  # the range, so a UI can explain
            # This port is unauthenticated by design (architecture §5), so a
            # refusal must not serve the layout of the disk.
            assert ".py" not in reply["reason"] and "/" not in reply["reason"]
            assert controls.params["scale"] == 4.0  # unmoved


@pytest.mark.parametrize(
    "message",
    [
        "not json at all",
        "[1, 2, 3]",  # valid JSON, wrong shape
        json.dumps({"type": "set"}),  # no name
        json.dumps({"type": "set", "name": 7, "value": 1.0}),  # name not a string
        json.dumps({"type": []}),  # unhashable type
        json.dumps({"type": {"set": 1}}),
        "[" * 100_000 + "]" * 100_000,  # nested past the decoder's recursion limit
    ],
    ids=["bad-json", "not-an-object", "no-name", "name-not-string", "type-list", "type-dict", "deep-nesting"],
)
def test_malformed_messages_are_ignored_and_the_connection_survives(message):
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControl()
    with preview_sink(line(n), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(message)
            sink.send(0.0, frame)
            assert isinstance(ws.recv(timeout=5.0), bytes)  # still streaming
            assert controls.calls == []  # nothing reached the engine


def test_values_check_refuses_rather_than_the_sink():
    # bool and non-finite arrive from JSON and are ParamSet.parse's job, so
    # the sink writes no validation of its own and the wording stays in one
    # place. Both must come back refused, not accepted, not crash.
    controls = FakeControl()
    with preview_sink(line(4), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            for value in (True, float("inf"), "fast", None):
                ws.send(json.dumps({"type": "set", "name": "speed", "value": value}))
                reply = next_text(ws)
                assert reply["type"] == "refused", (value, reply)
            assert controls.params["speed"] == 0.5


def test_a_message_the_control_does_not_know_gets_no_reply():
    """Which controls exist is the control's business: the sink passes every
    well-formed request on, and an unknown one comes back as no refusal."""
    controls = FakeControl()
    with preview_sink(line(4), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "unknown"}))
            ws.send(json.dumps({"type": "set", "name": "nosuch", "value": 1}))  # refused: a barrier
            assert next_text(ws)["control"] == "set"
            assert [c["type"] for c in controls.calls] == ["unknown", "set"]


def test_set_is_ignored_when_no_controls_are_wired():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    with preview_sink(line(n)) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "set", "name": "speed", "value": 1.0}))
            sink.send(0.0, frame)
            assert isinstance(ws.recv(timeout=5.0), bytes)  # view-only, not broken


def test_get_root_serves_page():
    with preview_sink(line(4)) as sink, urllib.request.urlopen(f"http://127.0.0.1:{sink.port}/", timeout=5.0) as resp:
        assert resp.status == 200
        assert resp.headers.get_content_type() == "text/html"
        assert "pewpew preview" in resp.read().decode()


def test_the_page_is_gzipped_when_the_client_allows_it_and_read_once(monkeypatch):
    raw, zipped = preview._page()
    assert gzip.decompress(zipped) == raw
    preview.web_files()  # read once too: the page's path is looked up in it
    reads = []
    monkeypatch.setattr(preview.resources, "files", lambda *a: reads.append(a))  # a second read would fail
    with preview_sink(line(4)) as sink:
        for accept, encoding, body in (("gzip, deflate, br", "gzip", zipped), ("identity", None, raw),
                                       ("br;q=1.0, GZIP;q=0.8", "gzip", zipped)):
            conn = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=5.0)
            conn.request("GET", "/", headers={"Accept-Encoding": accept})
            resp = conn.getresponse()
            assert (resp.status, resp.getheader("Content-Encoding"), resp.read()) == (200, encoding, body), accept
            assert resp.getheader("Vary") == "Accept-Encoding"
            conn.close()
    assert reads == []


def fetch(port: int | None, path: str, accept: str = "identity") -> tuple[int, dict[str, str], bytes]:
    """GET `path` on `port`, a started sink's: the status, the headers (names lowercased) and the body as sent."""
    assert port is not None
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5.0)
    try:
        conn.request("GET", path, headers={"Accept-Encoding": accept})
        resp = conn.getresponse()
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
    finally:
        conn.close()


WEB = Path(preview.__file__).parent / "web"
FILE_TYPES = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}


def test_each_file_of_the_build_is_served_immutable_with_its_type():
    files = sorted(preview.web_files())
    assert files and files == json.loads((WEB / "files.json").read_text())
    with preview_sink(line(4)) as sink:
        for name in files:
            status, headers, body = fetch(sink.port, f"/{name}?v=1")
            assert status == 200, name
            assert headers["content-type"] == FILE_TYPES[Path(name).suffix]
            assert headers["cache-control"] == "public, max-age=31536000, immutable"
            assert body == (WEB / name).read_bytes()
            status, headers, body = fetch(sink.port, f"/{name}", accept="gzip")
            assert headers["content-encoding"] == "gzip" and gzip.decompress(body) == (WEB / name).read_bytes()
            # The path must match exactly: with a second slash it is not on the list.
            assert fetch(sink.port, f"//{name}")[2] == preview._page()[0]


@pytest.mark.parametrize("path", [
    "/assets/../index.html", "/assets/%2e%2e/files.json", "/files.json", "/manifest.json", "/assets/",
    "/assets/nope.js", "/a/b", "/assembly/../parts.json",
])
def test_any_other_path_gets_the_page(path):
    """Only a listed file is served as itself: a path that walks out of the build, or names a file of
    it that is not listed, gets the page, so no path is read from the request."""
    with preview_sink(line(4)) as sink:
        status, headers, body = fetch(sink.port, path)
    assert status == 200 and headers["content-type"] == "text/html; charset=utf-8"
    assert body == preview._page()[0]


def test_the_parts_catalog_and_each_assembly_are_served():
    from pewpew.rig.parts import parts_view

    parts = json.loads(parts_view().body)
    types = parts["fixture_types"] + parts["attachment_types"]
    with preview_sink(line(4)) as sink:
        status, headers, body = fetch(sink.port, "/parts.json")
        assert (status, headers["content-type"], headers["cache-control"]) == (200, "application/json", "no-cache")
        assert json.loads(body) == parts
        assert types and all(t["assembly_url"] == f"/assembly/{t['digest']}.glb" for t in types)
        for t in types:
            status, headers, body = fetch(sink.port, t["assembly_url"])
            assert (status, headers["content-type"]) == (200, "model/gltf-binary")
            assert headers["cache-control"] == "public, max-age=31536000, immutable"
            assert body[:4] == b"glTF" and body == parts_view().glb(t["digest"])
            status, headers, body = fetch(sink.port, t["assembly_url"], accept="gzip")
            assert (status, headers["content-encoding"], headers["vary"]) == (200, "gzip", "Accept-Encoding")
            assert gzip.decompress(body) == parts_view().glb(t["digest"]) and len(body) < len(gzip.decompress(body))
        assert fetch(sink.port, "/assembly/0000000000000000.glb")[0] == 404
        # Not a digest: the page, as for any other path.
        assert fetch(sink.port, "/assembly/strip.glb")[2] == preview._page()[0]


def test_a_grid_run_has_no_rig_so_the_page_never_loads_its_3d_view():
    """The page shows the 2D/3D switch, and loads the 3D files, only on a hello with a rig."""
    with preview_sink(grid(4, 4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["rig"] is None


def test_the_file_routes_keep_the_host_rule():
    with preview_sink(line(4)) as sink:
        name = next(iter(sorted(preview.web_files())))
        for path in (f"/{name}", "/parts.json", "/assembly/0000000000000000.glb"):
            conn = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=5.0)
            conn.request("GET", path, headers={"Host": f"evil.example:{sink.port}"})
            assert conn.getresponse().status == 403, path
            conn.close()


def raw_upgrade(port: int, host: str, *headers: str, upgrade: bool = True) -> tuple[socket.socket, int]:
    """A websocket handshake by hand with a chosen `Host` header and more
    `headers`, or a plain GET without `upgrade`: the open socket and the
    response status. The socket then sends nothing."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=5.0)
    handshake = (
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n"
    ) if upgrade else "Connection: close\r\n"
    extra = "".join(f"{header}\r\n" for header in headers)
    sock.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\n{extra}{handshake}\r\n".encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = sock.recv(4096)
        if not chunk:
            break
        head += chunk
    return sock, int(head.split(b" ", 2)[1])


def get_with_host(port: int, host: str) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5.0)
    try:
        conn.request("GET", "/", headers={"Host": host})
        return conn.getresponse().status
    finally:
        conn.close()


def test_a_foreign_origin_cannot_open_the_socket():
    # Any page open in a browser on the private network could otherwise drive
    # blackout, save and delete: the browser sends its own Origin.
    with preview_sink(line(4), control=FakeControl()) as sink:
        with pytest.raises(InvalidStatus) as refused:
            connect(f"ws://127.0.0.1:{sink.port}/", origin="http://evil.example")
        assert refused.value.response.status_code == 403
        with pytest.raises(InvalidStatus):  # same host, another port is another origin
            connect(f"ws://127.0.0.1:{sink.port}/", origin=f"http://127.0.0.1:{sink.port + 1}")
        assert not peers(sink)
        # The page itself, served from this port, gets in; so does a client
        # that sends no Origin at all (client_for sends none).
        with connect(f"ws://127.0.0.1:{sink.port}/", origin=f"http://127.0.0.1:{sink.port}") as ws:
            assert json.loads(ws.recv(timeout=5.0))["type"] == "hello"
        ws, hello = client_for(sink)
        with ws:
            assert hello["type"] == "hello"


@pytest.mark.parametrize("host", ["evil.example:{port}", "127.0.0.1:1", "127.0.0.1", "[::1", "127.0.0.1:\u00b2"])
def test_a_host_header_other_than_an_address_and_this_port_is_refused(host):
    # A hostname is what DNS rebinding moves: refused for the page and the
    # socket alike, so a rebound page can neither read nor drive the aura.
    with preview_sink(line(4)) as sink:
        host = host.format(port=sink.port)
        assert get_with_host(sink.port, host) == 403
        sock, status = raw_upgrade(sink.port, host)
        sock.close()
        assert status == 403 and not peers(sink)


def test_a_repeated_header_is_read_whole_and_never_raised_on(caplog):
    """Two `Host` or two `Origin` headers are refused like a wrong one, and
    two `Accept-Encoding` headers are read together: no 500, no traceback."""
    with preview_sink(line(4)) as sink:
        me = f"127.0.0.1:{sink.port}"
        cases = [
            ((f"Host: evil.example:{sink.port}",), True, 403),
            ((f"Origin: http://{me}", "Origin: http://evil.example"), True, 403),
            (("Accept-Encoding: identity", "Accept-Encoding: gzip"), False, 200),
        ]
        for headers, upgrade, status in cases:
            sock, got = raw_upgrade(sink.port, me, *headers, upgrade=upgrade)
            sock.close()
            assert got == status, headers
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


def test_the_hello_carries_the_build_stamp_of_the_page_it_serves():
    """A tab compares it with its own stamp, and reloads when they differ."""
    with preview_sink(line(4)) as sink:
        with urllib.request.urlopen(f"http://127.0.0.1:{sink.port}/", timeout=5.0) as resp:
            assert resp.headers["Cache-Control"] == "no-cache"
            stamp = re.search(rb'<meta name="pewpew-build" content="([0-9a-f]{16})"', resp.read())
        ws, hello = client_for(sink)
        with ws:
            assert stamp and hello["build"] == stamp.group(1).decode()


@pytest.mark.parametrize("host", ["127.0.0.1:{port}", "localhost:{port}", "10.0.0.2:{port}", "[::1]:{port}"])
def test_an_address_with_this_port_is_served(host):
    # Bound to 0.0.0.0 the page answers on every interface's address; the
    # check needs none of them listed.
    with preview_sink(line(4)) as sink:
        host = host.format(port=sink.port)
        assert get_with_host(sink.port, host) == 200
        sock, status = raw_upgrade(sink.port, host)
        sock.close()
        assert status == 101


def test_stop_does_not_wait_long_on_a_client_that_never_answers_the_close(monkeypatch):
    monkeypatch.setattr(preview, "CLOSE_TIMEOUT_S", 0.05)
    sink = preview_sink(line(4))
    sink.start()
    sock, status = raw_upgrade(sink.port, f"127.0.0.1:{sink.port}")
    try:
        assert status == 101
        wait_until(lambda: peers(sink))
        started = time.monotonic()
        sink.stop()
        assert time.monotonic() - started < 1.0  # bounded by the close timeout, not the client
    finally:
        sock.close()


def test_stop_closes_sockets_joins_threads_and_frees_port():
    sink = preview_sink(line(4))
    sink.start()
    port = sink.port
    ws, _ = client_for(sink)
    sink.stop()
    assert sink.port is None
    with pytest.raises(ConnectionClosed):  # server-initiated close reaches the client
        while True:
            ws.recv(timeout=5.0)
    # The port is genuinely free again: a new sink can bind it.
    reuse = preview.PreviewSink(line(4), port=port)
    reuse.start()
    reuse.stop()


# -- aura controls: recall, master, blackout ------------------------------------


def test_a_new_client_gets_the_aura_state():
    aura = FakeControl(cap=0.6)
    with preview_sink(line(4), control=aura) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["aura"] == {
                "type": "aura", "looks": {"current": "calm", "items": [{"name": "calm"}, {"name": "warm"}]},
                "master": 0.6, "cap": 0.6, "blackout": False,
            }


def test_an_accepted_recall_echoes_the_new_look_to_every_client():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    aura = FakeControl()
    with preview_sink(line(n), control=aura) as sink:
        asker, _ = client_for(sink)
        watcher, _ = client_for(sink)
        with asker, watcher:
            asker.send(json.dumps({"type": "recall", "name": "warm"}))
            wait_until(lambda: aura.calls)
            sink.send(0.0, frame)
            echo = next_text(watcher)
            assert echo["type"] == "aura" and echo["looks"]["current"] == "warm"
            assert next_text(asker) == echo  # no refusal came first
            for t in (1 / 30, 2 / 30):  # unchanged state: no second echo
                sink.send(t, frame)
                assert isinstance(watcher.recv(timeout=5.0), bytes)


def test_a_refused_recall_replies_to_the_asker_only():
    aura = FakeControl()
    with preview_sink(line(4), control=aura) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "recall", "name": "../../etc/x.py"}))
            reply = next_text(ws)
            assert reply == {"type": "refused", "control": "recall", "name": None, "id": None,
                             "reason": "no look '../../etc/x.py'"}
            assert aura.current == "calm"


def test_master_and_blackout_messages_reach_the_aura_and_echo():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    aura = FakeControl(cap=0.8)
    with preview_sink(line(n), control=aura) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "master", "value": 0.9}))
            reply = next_text(ws)
            assert reply["type"] == "refused" and reply["control"] == "master"
            assert reply["reason"] == "master must be within 0.0..0.8, got 0.9"
            ws.send(json.dumps({"type": "master", "value": 0.25}))
            ws.send(json.dumps({"type": "blackout", "on": True}))
            wait_until(lambda: len(aura.calls) == 3)
            sink.send(0.0, frame)
            echo = next_text(ws)
            assert (echo["master"], echo["blackout"]) == (0.25, True)
            ws.send(json.dumps({"type": "blackout", "on": "yes"}))
            assert next_text(ws)["control"] == "blackout"


def test_scan_and_rebind_reach_the_control_and_a_refusal_comes_back():
    controls = FakeControl(replies={"rebind": "that address was not in the last scan; scan again"})
    with preview_sink(line(4), control=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "scan"}))
            ws.send(json.dumps({"type": "rebind", "board": "A", "address": "192.0.2.20"}))
            reply = next_text(ws)
            assert reply == {
                "type": "refused", "control": "rebind", "name": None, "id": None,
                "reason": "that address was not in the last scan; scan again",
            }
            assert controls.calls == [{"type": "scan"}, {"type": "rebind", "board": "A", "address": "192.0.2.20"}]


def test_host_is_the_bound_address():
    with preview_sink(line(4), host="127.0.0.1") as sink:
        assert sink._server.socket.getsockname()[0] == "127.0.0.1"


# ---- room maps: pitch, floor plan, blink -------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # the server never decodes it


def room_sink(tmp_path, *, image=True, plan=True, **kw):
    folder = tmp_path / "private-folder"
    folder.mkdir(exist_ok=True)
    if image:
        (folder / "plan.png").write_bytes(PNG)
    doc = arrangement(bar("a", pixels=8), bar("b", pixels=8, start=[0.0, 1.0], end=[2.0, 1.0], input="end", chain=2))
    if plan:
        doc["plan"] = {"image": "plan.png", "points": [[0, 0], [100, 0]], "meters": 1.0}
    r = compile_doc(doc, load_catalog())
    image = folder / "plan.png" if plan else None
    return r, preview_sink(r.mapping, room=plan_view(r), rig=rig_view(r), plan_image=image, **kw)


def get(sink, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{sink.port}{path}", timeout=5.0) as resp:
            return resp.status, resp.headers.get_content_type(), resp.read()
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, exc.headers.get_content_type(), exc.read()


def test_hello_carries_each_fixtures_pitch_and_the_meters_scale(tmp_path):
    r, sink = room_sink(tmp_path, plan=False)
    with sink:
        ws, hello = client_for(sink)
        with ws:
            room = hello["room"]
            # Pixel centres span 0.0625-1.875 m in x, the longest extent.
            assert room["scale"] == pytest.approx(1 / 1.8125) == r.scale
            assert [f["pitch"] for f in room["fixtures"]] == [pytest.approx(1 / 8), pytest.approx(2 / 8)]
            assert room["fixture_of"] == [0] * 8 + [1] * 8
            # A rig's strips are drawn from their input end, so each input is its "start".
            assert [f["input"] for f in room["fixtures"]] == ["start", "start"]
            a, b = room["fixtures"]
            assert a["start"][0] < a["end"][0] and b["start"][0] > b["end"][0]
            assert room["plan"] is None
    # Maps without a rig carry neither a room nor a rig.
    with preview_sink(line(4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["room"] is None and hello["rig"] is None


def test_hello_of_a_rig_carries_the_rig_for_a_3d_view(tmp_path):
    r, sink = room_sink(tmp_path, plan=False)
    with sink:
        ws, hello = client_for(sink)
        with ws:
            assert set(hello["rig"]) == {
                "catalog_digest", "frame", "scale", "shift", "plan", "fixtures", "types", "controllers",
                "slices", "controller_slices", "issues",
            }
            assert hello["rig"]["scale"] == pytest.approx(r.scale)
            assert [f["id"] for f in hello["rig"]["fixtures"]] == ["a", "b"] and hello["rig"]["plan"] is None


def test_decimation_keeps_fixture_of_aligned_with_the_positions(tmp_path):
    r, sink = room_sink(tmp_path, plan=False, max_pixels=4)
    with sink:
        ws, hello = client_for(sink)
        with ws:
            idx = np.linspace(0.0, r.n - 1, 4).round().astype(int)
            assert hello["room"]["fixture_of"] == r.fixture_of[idx].tolist()


def test_plan_is_served_at_a_fixed_url_that_names_no_path(tmp_path):
    r, sink = room_sink(tmp_path)
    with sink:
        ws, hello = client_for(sink)
        with ws:
            plan = hello["room"]["plan"]
            assert plan["url"] == "/plan?v=0"
            assert plan["unit"] == pytest.approx(0.01 * r.scale)
            assert hello["rig"]["plan"]["url"] == "/plan?v=0"
            assert hello["rig"]["plan"]["meters_per_pixel"] == pytest.approx(0.01)
            text = json.dumps(hello)
            assert "private-folder" not in text and "plan.png" not in text and str(tmp_path) not in text
        assert get(sink, plan["url"]) == (200, "image/png", PNG)
        status, kind, body = get(sink, "/plan/../../etc/passwd")
        assert kind == "text/html"  # any other path is the page, never a file
        (tmp_path / "private-folder" / "plan.png").unlink()  # removed while running
        status, _, body = get(sink, "/plan")
        assert status == 404 and b"private-folder" not in body


def test_a_missing_plan_image_explains_itself_and_404s(tmp_path):
    _, sink = room_sink(tmp_path, image=False)
    with sink:
        ws, hello = client_for(sink)
        with ws:
            plan = hello["room"]["plan"]
            assert set(plan) == {"error"} and "floor plan image was not found" in plan["error"]
            assert "/" not in plan["error"] and "plan.png" not in plan["error"]
            assert hello["rig"]["plan"] == plan
        status, _, body = get(sink, "/plan")
        assert status == 404 and body == b"no floor plan image\n"
    with preview_sink(line(4)) as sink:  # no room at all
        assert get(sink, "/plan")[0] == 404


def test_remap_with_a_new_plan_busts_the_image_url(tmp_path):
    r, sink = room_sink(tmp_path)
    with sink:
        ws, _ = client_for(sink)
        with ws:
            sink.remap(r.mapping, plan_view(r), tmp_path / "private-folder" / "plan.png", rig_view(r))
            sink.send(0.0, np.zeros((r.n, 3), dtype=np.float32))
            layout = next_text(ws)
            assert layout["type"] == "layout" and layout["room"]["plan"]["url"] == "/plan?v=1"
            assert layout["rig"]["plan"]["url"] == "/plan?v=1"


def test_health_goes_out_on_connect_and_then_only_on_change():
    health = {"level": "ok", "boards": [], "sent_fps": None,
              "loop": {"level": "ok", "fps": 60.0, "target": 60.0, "skips": 0, "watchdog": None},
              "awake": {"level": "ok", "requested": False, "held": False, "detail": None}}
    frame = np.zeros((4, 3), dtype=np.float32)
    with preview_sink(line(4), control=FakeControl(health=lambda: health)) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["health"] == {"type": "health", **health}
            sink.send(0.1, frame)  # unchanged: the frame only
            health = {**health, "level": "bad", "boards": [{"host": "10.0.0.11", "level": "bad"}]}
            sink.send(0.2, frame)
            msg = next_text(ws)
            assert msg["type"] == "health" and msg["level"] == "bad"


def test_no_health_message_without_a_health_supplier():
    with preview_sink(line(4)) as sink:
        ws, _ = client_for(sink)
        with ws:
            for t in (0.0, 0.1):
                sink.send(t, np.zeros((4, 3), dtype=np.float32))
                assert isinstance(ws.recv(timeout=5.0), bytes)


def test_live_values_are_read_at_most_ten_times_a_second_and_sent_only_on_change():
    """The `mod` readout changes every frame a route runs; the sink reads it
    on its own clock at most `MOD_HZ` times a second (ADR-006 amendment
    "layered paths"), and a client gets it only when it changes."""
    ft = FakeTime()
    controls = FakeControl()
    frame = np.zeros((4, 3), dtype=np.float32)
    with PreviewSink(line(4), port=0, max_fps=60.0, now=ft.now, sleep=ft.sleep,
                     control=controls) as sink:  # type: ignore[arg-type]  # the fake has what a sink reads
        ws, greeting = greet(sink)
        with ws:
            assert greeting["mod"] == {"type": "mod", "values": {}}
            for i in range(60):  # a second at 60 fps, a new live value every frame
                controls.mods = {"speed": i / 100}
                sink.send(ft.now(), frame)
            assert ft.now() == pytest.approx(59 / 60)
            assert 9 <= controls.mod_reads <= 11, "read once a tenth of a second, the greeting's included"
            ft.sleep(0.2)
            controls.mods = {"speed": 0.25}
            sink.send(ft.now(), frame)
            while (message := next_text(ws))["values"] != {"speed": 0.25}:
                assert message["type"] == "mod"
            for _ in range(30):  # unchanged: read again, never sent again
                sink.send(ft.now(), frame)
            ft.sleep(0.2)
            controls.mods = {"speed": 0.5}
            sink.send(ft.now(), frame)
            assert next_text(ws) == {"type": "mod", "values": {"speed": 0.5}}


def test_the_catalog_comes_in_the_greeting_and_again_only_when_it_changes(monkeypatch):
    """The catalog is large and seldom changes (an op file loads): a client
    gets it in its greeting, then a new one only when it differs, and the
    sink serializes the same object once."""
    controls = FakeControl()
    controls.catalog_ = {"cards": [{"name": "plasma"}], "blends": []}
    frame = np.zeros((4, 3), dtype=np.float32)
    dumps = []
    real = json.dumps
    monkeypatch.setattr(preview.json, "dumps", lambda obj, **kw: (dumps.append(obj.get("type")), real(obj, **kw))[1])
    with preview_sink(line(4), control=controls) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["catalog"] == {"type": "catalog", "cards": [{"name": "plasma"}], "blends": []}
            for _ in range(5):
                sink.send(0.0, frame)
            assert dumps.count("catalog") == 1
            controls.catalog_ = {"cards": [{"name": "plasma"}], "blends": []}  # a new object, the same text
            sink.send(0.0, frame)
            controls.catalog_ = {"cards": [{"name": "plasma"}, {"name": "glow"}], "blends": []}
            sink.send(0.0, frame)
            assert next_of(ws, "catalog")["cards"] == [{"name": "plasma"}, {"name": "glow"}]


# ---- the rig file's states and the power reading ------------------------------------


def editable_rig(folder: Path, *, edits: bool = True):
    """An aura on a 2-pixel line whose control's layout is a `RigLive` over
    an arrangement file of one 2-pixel bar in `folder`."""
    doc = arrangement(bar("a", pixels=2))
    path = folder / "rig.arrangement.json"
    data = json.dumps(doc).encode()
    path.write_bytes(data)
    rig = aura_rig(mapping=line(2))
    rig.layout = RigLive(path, compile_doc(doc, load_catalog()), data, rig.fader, rig.calls, ddp=None,
                         argv=["run"], watch=no_watch, edits=edits)
    rig.control.layout = rig.layout
    return rig, doc


@pytest.mark.usefixtures("fake_ops")
def test_the_rig_files_states_and_the_power_reading_reach_a_client_as_they_change(tmp_path):
    rig, doc = editable_rig(tmp_path)
    reading: list[dict | None] = [None]
    with preview_sink(line(2), control=rig.control, power=lambda: reading[0]) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert "arrange" in greeting["hello"]["capabilities"] and "power" not in greeting
            base = hashlib.sha256((tmp_path / "rig.arrangement.json").read_bytes()).hexdigest()
            assert greeting["arrangement"] == {"type": "arrangement", "arrangement": doc, "base": base}
            assert greeting["report"] == {"type": "report", **rig.layout.rig.findings()}
            reading[0] = {"watts": 1.0, "uncapped_watts": 2.0}
            two = arrangement(bar("a", pixels=2), bar("b", pixels=2, chain=2, start=[0.0, 1.0], end=[1.0, 1.0]))
            with LoopThread(rig.calls):  # the commit, on the loop thread
                ws.send(json.dumps({"type": "arrange", "id": "e1", "arrangement": two, "base": base}))
                assert next_of(ws, "ack") == {"type": "ack", "id": "e1", "control": "arrange"}
            assert rig.layout.rig.n == 4  # acked once it runs
            sink.send(0.0, np.zeros((2, 3), np.float32))
            seen = {kind: next_of(ws, kind) for kind in ("power", "arrangement", "report")}
            assert seen["power"] == {"type": "power", "watts": 1.0, "uncapped_watts": 2.0}
            assert seen["arrangement"]["arrangement"] == two and seen["arrangement"]["base"] != base
            assert seen["report"]["report"]["totals"]["pixels"] == 4
            ws.send(json.dumps({"type": "arrange", "id": "e2", "arrangement": two, "base": base}))
            assert next_of(ws, "refused")["reason"] == "the layout changed; showing the current one"
            ws.send(json.dumps({"type": "arrange", "id": "e3", "arrangement": {"format": "pewpew.arrangement"},
                                "base": seen["arrangement"]["base"]}))
            refused = next_of(ws, "refused")
            assert (refused["control"], refused["id"]) == ("arrange", "e3") and refused["issues"]
            assert refused["reason"].startswith("the arrangement does not compile")
            ws.send(json.dumps({"type": "blackout", "id": "b", "on": "x"}))
            assert "issues" not in next_of(ws, "refused")  # only a refusal with issues carries them


@pytest.mark.usefixtures("fake_ops")
def test_an_unattended_rig_offers_no_layout_edit(tmp_path):
    rig, _doc = editable_rig(tmp_path, edits=False)
    sink = preview_sink(line(2), control=rig.control)
    assert json.loads(sink._view.hello)["capabilities"] == ["ack"]
    texts = dict(zip(preview._MESSAGES, sink._texts(None)))
    assert texts["report"] is not None
    assert json.loads(texts["arrangement"] or "") == {"type": "arrangement", "arrangement": None, "base": None}


@pytest.mark.usefixtures("fake_ops")
def test_a_room_file_saved_over_the_arrangement_tells_a_client_the_edits_have_ended(tmp_path):
    rig, _doc = editable_rig(tmp_path)
    with preview_sink(line(2), control=rig.control) as sink:
        ws, greeting = greet(sink)
        with ws:
            assert greeting["arrangement"]["arrangement"] is not None
            shutil.copy(LEGACY_ROOM, tmp_path / "rig.arrangement.json")
            assert rig.layout.reloader.reload() is True
            sink.send(0.0, np.zeros((2, 3), np.float32))
            assert next_of(ws, "arrangement") == {"type": "arrangement", "arrangement": None, "base": None}


def test_a_refusal_carries_its_issues_only_when_it_has_some():
    issue = {"level": "error", "code": "bad", "message": "bad", "ref": None}
    assert preview.answer("arrange", 1, Refusal("bad", issues=(issue,))) == {
        "type": "refused", "control": "arrange", "name": None, "id": 1, "reason": "bad", "issues": [issue]}
    assert preview.answer("arrange", 1, Refusal("bad")) == {
        "type": "refused", "control": "arrange", "name": None, "id": 1, "reason": "bad"}
