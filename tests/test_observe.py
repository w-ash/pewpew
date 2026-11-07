"""`python -m pewpew observe` and `pewpew.remote` (tier 0): a real preview
on a free port, watched by a client that sends it nothing.

Frames go out with `push`, which waits until every client has each one,
so no frame is coalesced away and the window is exact. Engine times are
quarter seconds, which float32 holds exactly."""

from __future__ import annotations

import contextlib
import errno
import functools
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields

import numpy as np
import pytest
from websockets.datastructures import Headers
from websockets.exceptions import InvalidStatus
from websockets.http11 import Response
from websockets.sync.server import serve

import pewpew.remote.observe as remote_observe
from fakes import Solid, aura_rig, look, peers, preview_sink, wait_until
from pewpew import grid, line
from pewpew.__main__ import main
from pewpew.metrics import measure
from pewpew.remote.client import Client, Frame, Unreachable, engine_url, why_unreachable
from pewpew.remote.observe import Capture, Observation, observe
from pewpew.sinks.base import from_display_u8, to_display_u8
from pewpew.sinks.preview import FRAME_HEADER, page_build
from pngread import decode_png

TIMES = (0.25, 0.5, 0.75, 1.0, 1.25)  # one second of window, then the frame that closes it


def known(n: int, k: int) -> np.ndarray:
    """Frame k of n pixels: red rises along the pixels, green flashes on odd k."""
    out = np.zeros((n, 3), np.float32)
    out[:, 0] = np.arange(n) / (n - 1)
    out[:, 1] = 0.8 * (k % 2)
    return out


def push(sink, t: float, frame: np.ndarray) -> None:
    """Send `frame` at engine time `t` and wait until every client has it."""
    sink.send(t, frame)
    with sink._lock:
        clients = list(sink._clients.values())
    for client in clients:
        assert client.driver.drain()


@contextlib.contextmanager
def engine(mapping, **kw):
    """A started preview of `mapping` over an aura's control. Yields the
    sink and every message a client has sent it."""
    rig = aura_rig(Solid, mapping=mapping)
    with preview_sink(mapping, control=rig.control, **kw) as sink:
        received: list = []
        sink._on_message = lambda conn, message: received.append(message)
        yield sink, received


@contextlib.contextmanager
def watching(sink, watch):
    """Run `watch()` on a thread, and yield its future once `sink` sends
    to the watcher."""
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(watch)
        wait_until(lambda: len(peers(sink)) == 1 or future.done())
        yield future


def test_observe_measures_the_frames_it_was_sent_and_sends_nothing(tmp_path):
    n, sent = 64, np.linspace(0.0, 63, 16).round().astype(np.int64)  # the preview's even decimation
    frames = np.stack([known(n, k) for k in range(len(TIMES))])
    with engine(grid(8, 8), max_pixels=16) as (sink, received):
        url = f"ws://127.0.0.1:{sink.port}/"
        with watching(sink, lambda: observe(url, 1.0, sheet=tmp_path / "sheet.png")) as future:
            for t, frame in zip(TIMES, frames):
                push(sink, t, frame)
            seen = future.result(timeout=5.0)
    assert received == []  # nothing but the websocket handshakes
    assert (seen.frames, seen.span, seen.fps, seen.dropped) == (4, 0.75, 4.0, 0)
    assert (seen.sent_pixels, seen.total_pixels, seen.approximate) == (16, 64, True)
    assert seen.build == page_build() and seen.warnings == ()
    assert seen.aura is not None and seen.aura["pattern"] == "solid"
    assert seen.params == {"layers.base.solid.red": 1.0, "layers.base.solid.green": 0.0,
                           "layers.base.solid.blue": 0.0, "layers.base.opacity": 1.0,
                           "layers.base.blend": "normal", "layers.base.enabled": True}
    assert seen.status == {"error": None, "source": None, "path": None} and seen.health is None
    window = frames[:4, sent]  # a fancy-indexed view: measure reads it as a C-contiguous copy
    assert seen.metrics == measure(from_display_u8(to_display_u8(window)), 4.0)
    assert seen.metrics is not None and seen.metrics.flash_rate_max == 1.5
    assert abs(seen.metrics.mean_luma - measure(window, 4.0).mean_luma) < 0.005  # 8 bits cost little
    assert seen.sheet == str(tmp_path / "sheet.png")
    assert decode_png((tmp_path / "sheet.png").read_bytes()).shape[2] == 3


def test_an_observation_says_a_crossfade_ran_in_its_window():
    """Frames of a fade mix two looks, so their metrics are neither's."""
    rig = aura_rig(Solid, mapping=line(8))
    with preview_sink(line(8), control=rig.control) as sink:
        assert rig.deck.recall(look("wave"), 2.0) is None and rig.control.state()["fading"]
        url = f"ws://127.0.0.1:{sink.port}/"
        with watching(sink, lambda: observe(url, 1.0)) as future:
            for t in TIMES:
                push(sink, t, known(8, 0))
            seen = future.result(timeout=5.0)
    assert seen.faded and remote_observe.FADED in seen.warnings
    assert seen.aura is not None and seen.aura["fading"] is True


def test_a_capture_draws_the_sheet_it_writes_once_it_has_two_frames(tmp_path):
    hello = {"type": "hello", "n": 8, "total": 8, "positions": [[i / 7, 0.0, 0.0] for i in range(8)],
             "display_gamma": 2.2, "build": None}
    frames = tuple(Frame(t, k, to_display_u8(known(8, k))) for k, t in enumerate(TIMES))
    seen = Capture("ws://127.0.0.1:1/", {"hello": hello}, frames)
    drawn = seen.sheet()
    assert seen.observation(tmp_path / "s.png").sheet == str(tmp_path / "s.png")
    assert drawn is not None and drawn.png == (tmp_path / "s.png").read_bytes()
    assert Capture("ws://127.0.0.1:1/", {"hello": hello}, frames[:1]).sheet() is None


def test_a_new_map_restarts_the_window_on_its_frames():
    with engine(line(8)) as (sink, _):
        url = f"ws://127.0.0.1:{sink.port}/"
        with watching(sink, lambda: observe(url, 1.0)) as future:
            push(sink, 0.25, known(8, 0))
            sink.remap(line(4))
            for t in (0.5, 0.75, 1.0, 1.25, 1.5):
                push(sink, t, known(4, 1))
            seen = future.result(timeout=5.0)
    assert (seen.frames, seen.sent_pixels, seen.span) == (4, 4, 0.75)
    assert seen.warnings == ("the map changed during the capture; the frames are those drawn on the new one",)


def test_a_message_after_the_window_leaves_the_window_whole(monkeypatch):
    real_close = Client.close
    with engine(line(8)) as (sink, _):

        def close_after_a_new_map(client: Client) -> None:
            sink.remap(line(4))
            push(sink, 1.5, known(4, 1))  # the layout goes out before this frame
            assert client.wait(lambda: client.counts["layout"] == 1, 5.0)
            real_close(client)

        monkeypatch.setattr(Client, "close", close_after_a_new_map)
        url = f"ws://127.0.0.1:{sink.port}/"
        with watching(sink, lambda: observe(url, 1.0)) as future:
            for t in TIMES:
                push(sink, t, known(8, 0))
            seen = future.result(timeout=5.0)
    assert (seen.frames, seen.sent_pixels, seen.span, seen.warnings) == (4, 8, 0.75, ())


def test_max_frames_bounds_a_long_window():
    with engine(line(4)) as (sink, _):
        url = f"ws://127.0.0.1:{sink.port}/"
        with watching(sink, lambda: observe(url, 10.0, max_frames=3)) as future:
            for t in TIMES[:3]:
                push(sink, t, known(4, 0))
            seen = future.result(timeout=5.0)
    assert (seen.frames, seen.span, seen.fps) == (3, 0.5, 4.0)
    assert seen.metrics is not None and seen.metrics.seconds == 0.75 and seen.metrics.flash_safe is None
    assert seen.warnings == ("stopped at max_frames=3, 0.50 s into the 10 s window",
                             "0.75 s of frames: flash safety needs a window of 1 s or more")


def test_an_engine_that_sends_no_frames_gives_state_and_no_metrics():
    with engine(line(4)) as (sink, _):
        seen = observe(f"ws://127.0.0.1:{sink.port}/", 0.05, timeout=0.1)
    assert (seen.frames, seen.fps, seen.metrics) == (0, 0.0, None)
    assert seen.aura is not None and seen.aura["pattern"] == "solid"
    assert seen.warnings[0] == ("the frames stopped 0.00 s into the 0.05 s window, after 0 frames (waited 0.15 s): "
                                "check the engine's status and its render loop")
    assert seen.warnings[1] == "metrics and a sheet need two frames at different engine times; got 0"


def test_the_window_rate_and_drops_come_from_the_frame_headers():
    hello = {"type": "hello", "n": 1, "total": 1, "positions": [[0.0, 0.0, 0.0]], "display_gamma": 2.2}
    rgb = np.zeros((1, 3), np.uint8)
    seen = Capture("ws://x/", {"hello": hello}, tuple(Frame(t, seq, rgb) for t, seq in
                                                     ((0.5, 2**32 - 2), (1.0, 2**32 - 1), (1.5, 2), (2.0, 3))))
    assert (seen.span, seen.fps, seen.dropped) == (1.5, 2.0, 2)  # the count wraps at 2**32
    data = FRAME_HEADER.pack(0.25, 7) + bytes([1, 2, 3])
    frame = Frame.decode(data)
    assert frame is not None and (frame.t, frame.seq, frame.rgb.tolist()) == (0.25, 7, [[1, 2, 3]])
    assert Frame.decode(data[:-1]) is None and Frame.decode(data[:5]) is None


def test_the_json_is_the_observation_and_stdout_holds_only_it(tmp_path, monkeypatch, capsys):
    kept: list[Observation] = []
    real = remote_observe.observe
    monkeypatch.setattr(remote_observe, "observe", lambda *a, **kw: kept.append(real(*a, **kw)) or kept[-1])
    with engine(line(8)) as (sink, received):
        port = sink.port
        argv = ["observe", f"http://127.0.0.1:{port}/", "--seconds", "1", "--json", "--sheet", str(tmp_path / "s.png")]
        with watching(sink, lambda: main(argv)) as future:
            for k, t in enumerate(TIMES):
                push(sink, t, known(8, k))
            code = future.result(timeout=5.0)
    out, err = capsys.readouterr()
    doc = json.loads(out)
    assert code == 0 and err == "" and received == []
    assert doc == kept[0].to_json() and list(doc) == [f.name for f in fields(Observation)]
    assert doc["url"] == f"ws://127.0.0.1:{port}/" and doc["sheet"] == str(tmp_path / "s.png")
    assert doc["metrics"]["frames"] == 4 and doc["approximate"] is True


def test_a_sheet_that_cannot_be_written_is_a_warning_and_exit_1(tmp_path, monkeypatch, capsys):
    def full(path, data):
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

    monkeypatch.setattr(remote_observe, "write_atomic", full)
    sheet = tmp_path / "s.png"
    with engine(line(8)) as (sink, _):
        argv = ["observe", f"ws://127.0.0.1:{sink.port}/", "--seconds", "1", "--json", "--sheet", str(sheet)]
        with watching(sink, lambda: main(argv)) as future:
            for k, t in enumerate(TIMES):
                push(sink, t, known(8, k))
            code = future.result(timeout=5.0)
    out, err = capsys.readouterr()
    doc = json.loads(out)
    assert code == 1 and doc["sheet"] is None and doc["metrics"]["frames"] == 4
    assert doc["warnings"] == [f"cannot write the sheet to {sheet}: {os.strerror(errno.ENOSPC)}"]
    assert err == f"observe: {doc['warnings'][0]}\n"


def test_no_frames_exits_1_with_the_reason_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(remote_observe, "observe", functools.partial(remote_observe.observe, timeout=0.1))
    with engine(line(4)) as (sink, _):
        port = sink.port
        code = main(["observe", f"localhost:{port}", "--seconds", "0.05"])
    out, err = capsys.readouterr()
    assert code == 1
    assert out.startswith(f"ws://localhost:{port}/: 0 frames") and "\nlayer base: solid (normal at 1.0)\n" in out
    assert err.startswith("observe: the frames stopped 0.00 s into the 0.05 s window")


def test_an_engine_that_is_not_there_exits_3_and_says_what_to_do(capsys):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # free once the socket closes: nothing listens there
    assert main(["observe", f"127.0.0.1:{port}", "--json"]) == 3
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith(f"observe: nothing answered at ws://127.0.0.1:{port}/ (ConnectionRefusedError")
    assert "start the engine with `python -m pewpew run LOOKS --preview`" in err


def test_an_https_address_is_told_the_preview_speaks_plain_websocket():
    with engine(line(4)) as (sink, _):
        port = sink.port
        with pytest.raises(Unreachable) as exc:
            observe(f"https://127.0.0.1:{port}/", timeout=1.0)
    assert str(exc.value).startswith(f"wss://127.0.0.1:{port}/ did not answer TLS (")
    assert str(exc.value).endswith(f"a preview port speaks plain websocket, so give ws://127.0.0.1:{port}/")


def test_a_server_that_sends_no_hello_is_not_an_engine():
    def silent(conn) -> None:
        conn.recv()

    with serve(silent, "127.0.0.1", 0) as server:
        port = server.socket.getsockname()[1]
        with ThreadPoolExecutor(1) as pool:
            pool.submit(server.serve_forever)
            with pytest.raises(Unreachable, match=r"sent nothing for 0\.1 s before its hello: is it a pewpew"):
                observe(f"ws://127.0.0.1:{port}/", timeout=0.1)
            server.shutdown()


@pytest.mark.parametrize(("exc", "says"), [
    (InvalidStatus(Response(403, "Forbidden", Headers())), "answers only to an IP address or localhost"),
    (InvalidStatus(Response(404, "Not Found", Headers())), "answered HTTP 404: is it a pewpew engine's preview port?"),
    (TimeoutError("timed out"), "did not answer within 5 s"),
    (socket.gaierror(8, "nodename nor servname provided"), "cannot find the host of ws://pewpew.local:7447/"),
])
def test_each_failure_to_connect_says_what_to_try(exc, says):
    assert says in why_unreachable("ws://pewpew.local:7447/", exc, 5.0)


@pytest.mark.parametrize(("text", "url"), [
    ("http://127.0.0.1:7447/", "ws://127.0.0.1:7447/"),
    ("HTTPS://10.0.0.5:7447", "wss://10.0.0.5:7447/"),
    ("ws://[::1]:7447/ws?x=1", "ws://[::1]:7447/ws?x=1"),
    ("localhost:7447", "ws://localhost:7447/"),
    ("ws://pewpew.local", "ws://pewpew.local:80/"),
])
def test_an_engine_address_is_the_page_url_a_websocket_url_or_host_port(text, url):
    assert engine_url(text) == url


@pytest.mark.parametrize("argv", [
    ["observe", "ftp://127.0.0.1:7447/"],
    ["observe", "127.0.0.1:port"],
    ["observe", "ws://pewpew..local:7447/"],  # a host name socket cannot encode
    ["observe", "ws://127.0.0.1:7447/", "--seconds", "0"],
    ["observe", "ws://127.0.0.1:7447/", "--sheet", "/no/such/folder/s.png"],
    ["observe", "ws://127.0.0.1:7447/", "--sheet", "."],
])
def test_a_bad_argument_is_a_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2 and "observe: error:" in capsys.readouterr().err
