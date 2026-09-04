"""PreviewSink protocol tests: real loopback sockets, no browser.

Ephemeral ports (port=0) so tests never collide; the sink's RateGate runs
on fake time so nothing here sleeps for pacing. The stall-isolation
guarantee itself (submit never blocks) is SinkDriver's, proven in
tests/test_sink_driver.py — here we prove the sink wires one driver per
client and contains a dead client without losing the live ones.
"""

from __future__ import annotations

import json
import struct
import time
import urllib.request

import numpy as np
import pytest
from conftest import FakeTime
from websockets.sync.client import connect

from pewpew import ParamSet, grid, line
from pewpew.patterns import Plasma
from pewpew.sinks import PreviewSink, to_display_u8


class FakeControls:
    """A Controls over a real ParamSet, applied on the calling thread.

    The runner's `_LoopControls` defers the write to the loop thread; that
    discipline is its own to prove (tests/test_runner.py). Here the sink is
    under test, so the set lands immediately and the echo is observable
    without a running loop.
    """

    def __init__(self, pattern_cls=Plasma) -> None:
        self.params = ParamSet(pattern_cls)
        self.calls: list[tuple[str, object]] = []

    def describe(self) -> list[dict]:
        return self.params.describe()

    def set(self, name: str, value: object) -> str | None:
        self.calls.append((name, value))
        reason = self.params.check(name, value)
        if reason is None:
            self.params.set(name, value)
        return reason


def make_sink(mapping, **kw) -> PreviewSink:
    ft = FakeTime()
    return PreviewSink(mapping, port=0, now=ft.now, sleep=ft.sleep, **kw)


def next_text(ws) -> dict:
    """The next text message, skipping binary frames."""
    while True:
        msg = ws.recv(timeout=5.0)
        if isinstance(msg, str):
            return json.loads(msg)


def wait_until(cond, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not cond():
        assert time.monotonic() < deadline, "condition never became true"
        time.sleep(0.005)


def client_for(sink: PreviewSink):
    ws = connect(f"ws://127.0.0.1:{sink.port}/")
    hello = json.loads(ws.recv(timeout=5.0))
    return ws, hello


def test_hello_carries_positions_once():
    with make_sink(grid(4, 4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["type"] == "hello"
            assert hello["n"] == hello["total"] == 16
            assert hello["is3d"] is False
            assert hello["positions"] == np.round(grid(4, 4).astype(np.float64), 4).tolist()


def test_hello_decimates_past_max_pixels_deterministically():
    with make_sink(line(100), max_pixels=10) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["n"] == 10 and hello["total"] == 100
            assert hello["positions"][0] == [0.0, 0.0, 0.0]
            assert hello["positions"][-1] == [1.0, 0.0, 0.0]


def test_binary_frame_is_gamma_quantized_uint8_with_t_header():
    n = 8
    frame = np.zeros((n, 3), dtype=np.float32)
    frame[:, 1] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    with make_sink(line(n)) as sink:
        ws, _ = client_for(sink)
        with ws:
            wait_until(lambda: sink._clients)
            sink.send(0.5, frame)
            data = ws.recv(timeout=5.0)
            assert isinstance(data, bytes)
            t, seq = struct.unpack("<fI", data[:8])
            assert t == 0.5 and seq == 1
            assert data[8:] == to_display_u8(frame).tobytes()


def test_stalled_client_never_stalls_loop_or_other_clients():
    n = 4
    frame = np.full((n, 3), 0.5, dtype=np.float32)
    with make_sink(line(n)) as sink:
        dead_ws, _ = client_for(sink)
        live_ws, _ = client_for(sink)
        with live_ws:
            wait_until(lambda: len(sink._clients) == 2)
            dead_sock = dead_ws.socket
            dead_sock.close()  # yank the transport out from under its driver
            for i in range(5):
                sink.send(float(i), frame)  # must return promptly regardless
            # The live client still receives frames.
            assert isinstance(live_ws.recv(timeout=5.0), bytes)
        wait_until(lambda: len(sink._clients) <= 1)  # dead client reaped


def test_status_message_sent_on_error_change():
    # Frames may coalesce (newest-wins per client), so assert the status
    # *sequence*, not exact frame counts: one "boom", then one null — an
    # unchanged status between the two produces no duplicate message.
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    state: list[str | None] = [None]

    with make_sink(line(n), status=lambda: state[0]) as sink:
        ws, _ = client_for(sink)
        with ws:
            wait_until(lambda: sink._clients)
            state[0] = "boom"
            sink.send(0.0, frame)
            assert next_text(ws) == {"type": "status", "error": "boom"}
            sink.send(1 / 30, frame)  # unchanged: no status message
            state[0] = None
            sink.send(2 / 30, frame)  # cleared: the next status is null,
            assert next_text(ws) == {"type": "status", "error": None}  # not a second "boom"


def test_hello_carries_the_declared_params():
    controls = FakeControls()
    with make_sink(line(4), controls=controls) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["params"] == ParamSet(Plasma).describe()
            speed = hello["params"][0]
            # The slider is built from these: endpoints and quantization must
            # all be on the wire, or the page has to invent them.
            assert speed["name"] == "speed" and speed["label"] == "Speed"
            assert (speed["lo"], speed["hi"], speed["value"]) == (0.0, 2.0, 0.5)
            assert speed["step"] > 0.0 and speed["decimals"] >= 0


def test_hello_carries_no_params_without_controls():
    with make_sink(line(4)) as sink:
        ws, hello = client_for(sink)
        with ws:
            assert hello["params"] == []


def test_accepted_set_reaches_the_controls_and_echoes_to_every_client():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControls()
    with make_sink(line(n), controls=controls) as sink:
        setter, _ = client_for(sink)
        watcher, _ = client_for(sink)
        with setter, watcher:
            wait_until(lambda: len(sink._clients) == 2)
            setter.send(json.dumps({"type": "set", "name": "speed", "value": 1.75}))
            wait_until(lambda: controls.calls)
            sink.send(0.0, frame)
            # The tab that never touched a slider learns what won: §5's
            # last-write-wins with the merged state pushed to every client.
            echo = next_text(watcher)
            assert echo == {"type": "params", "values": {"speed": 1.75, "scale": 4.0}}
            assert next_text(setter) == echo


def test_a_change_of_declarations_rebuilds_the_levers_then_fills_them():
    """A hot reload that adds or retunes a knob. The client gets a `declare`
    (value-free) and then the `params` echo *even though* its text is the
    same as the last one sent — the rebuilt sliders are empty until it lands.
    An unchanged frame sends neither."""
    from pewpew import Param

    class Retuned(Plasma):
        gain = Param(0.5, 0.0, 1.0, "Gain")

    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControls()
    with make_sink(line(n), controls=controls) as sink:
        ws, hello = client_for(sink)
        with ws:
            wait_until(lambda: len(sink._clients) == 1)
            # One frame at a time: back-to-back sends coalesce in the client's
            # driver (newest wins), which is not what is under test here.
            sink.send(0.0, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            sink.send(1 / 60, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            # Same declarations, same values: nothing but frames so far.
            with pytest.raises(TimeoutError):
                ws.recv(timeout=0.2)

            controls.params = ParamSet(Retuned)  # what Renderer.swap does, in place
            sink.send(2 / 60, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            declare = next_text(ws)
            assert declare["type"] == "declare"
            assert [p["name"] for p in declare["params"]] == ["speed", "scale", "gain"]
            assert all("value" not in p for p in declare["params"])
            assert declare["params"][2]["label"] == "Gain"
            echo = next_text(ws)
            assert echo == {"type": "params", "values": {"speed": 0.5, "scale": 4.0, "gain": 0.5}}
            # Steady state again: the next frame brings no text.
            sink.send(3 / 60, frame)
            assert not isinstance(ws.recv(timeout=5.0), str)
            with pytest.raises(TimeoutError):
                ws.recv(timeout=0.2)


def test_refused_set_names_the_range_but_never_a_source_path():
    controls = FakeControls()
    with make_sink(line(4), controls=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            ws.send(json.dumps({"type": "set", "name": "scale", "value": 99.0}))
            reply = next_text(ws)
            assert reply["type"] == "refused" and reply["name"] == "scale"
            assert reply["reason"] == controls.params.check("scale", 99.0)
            assert "1.0..10.0" in reply["reason"]  # the range, so a UI can explain
            # This port is unauthenticated by design (architecture §5), so a
            # refusal must not serve the layout of the disk. `hint` is the
            # half that names a file, and it stays on the CLI.
            hint = controls.params.hint("scale")
            assert hint and hint not in reply["reason"]
            assert ".py" not in reply["reason"] and "/" not in reply["reason"]
            assert controls.params["scale"] == 4.0  # unmoved


@pytest.mark.parametrize(
    "message",
    [
        "not json at all",
        "[1, 2, 3]",  # valid JSON, wrong shape
        json.dumps({"type": "unknown"}),
        json.dumps({"type": "set"}),  # no name
        json.dumps({"type": "set", "name": 7, "value": 1.0}),  # name not a string
    ],
    ids=["bad-json", "not-an-object", "unknown-type", "no-name", "name-not-string"],
)
def test_malformed_messages_are_ignored_and_the_connection_survives(message):
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    controls = FakeControls()
    with make_sink(line(n), controls=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            wait_until(lambda: sink._clients)
            ws.send(message)
            sink.send(0.0, frame)
            assert isinstance(ws.recv(timeout=5.0), bytes)  # still streaming
            assert controls.calls == []  # nothing reached the engine


def test_values_check_refuses_rather_than_the_sink():
    # bool and non-finite arrive from JSON and are ParamSet.check's job, so
    # the sink writes no validation of its own and the wording stays in one
    # place. Both must come back refused, not accepted, not crash.
    controls = FakeControls()
    with make_sink(line(4), controls=controls) as sink:
        ws, _ = client_for(sink)
        with ws:
            for value in (True, float("inf"), "fast", None):
                ws.send(json.dumps({"type": "set", "name": "speed", "value": value}))
                reply = next_text(ws)
                assert reply["type"] == "refused", (value, reply)
            assert controls.params["speed"] == 0.5


def test_set_is_ignored_when_no_controls_are_wired():
    n = 4
    frame = np.zeros((n, 3), dtype=np.float32)
    with make_sink(line(n)) as sink:
        ws, _ = client_for(sink)
        with ws:
            wait_until(lambda: sink._clients)
            ws.send(json.dumps({"type": "set", "name": "speed", "value": 1.0}))
            sink.send(0.0, frame)
            assert isinstance(ws.recv(timeout=5.0), bytes)  # view-only, not broken


def test_get_root_serves_page():
    with make_sink(line(4)) as sink:
        with urllib.request.urlopen(f"http://127.0.0.1:{sink.port}/", timeout=5.0) as resp:
            assert resp.status == 200
            assert resp.headers.get_content_type() == "text/html"
            assert "pewpew preview" in resp.read().decode()


def test_stop_closes_sockets_joins_threads_and_frees_port():
    sink = make_sink(line(4))
    sink.start()
    port = sink.port
    ws, _ = client_for(sink)
    sink.stop()
    assert sink.port is None
    with pytest.raises(Exception):  # server-initiated close reaches the client
        while True:
            ws.recv(timeout=5.0)
    # The port is genuinely free again: a new sink can bind it.
    reuse = PreviewSink(line(4), port=port)
    reuse.start()
    reuse.stop()
