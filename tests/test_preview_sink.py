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

from pewpew import grid, line
from pewpew.sinks import PreviewSink, to_display_u8


def make_sink(mapping, **kw) -> PreviewSink:
    ft = FakeTime()
    return PreviewSink(mapping, port=0, now=ft.now, sleep=ft.sleep, **kw)


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

    def next_status(ws) -> dict:
        while True:
            msg = ws.recv(timeout=5.0)
            if isinstance(msg, str):
                return json.loads(msg)

    with make_sink(line(n), status=lambda: state[0]) as sink:
        ws, _ = client_for(sink)
        with ws:
            wait_until(lambda: sink._clients)
            state[0] = "boom"
            sink.send(0.0, frame)
            assert next_status(ws) == {"type": "status", "error": "boom"}
            sink.send(1 / 30, frame)  # unchanged: no status message
            state[0] = None
            sink.send(2 / 30, frame)  # cleared: the next status is null,
            assert next_status(ws) == {"type": "status", "error": None}  # not a second "boom"


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
