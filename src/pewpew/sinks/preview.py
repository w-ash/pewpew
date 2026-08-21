"""Browser preview sink: positions once, then compact color buffers.

Transport is `websockets.sync.server` (ADR-020) — a thread-per-connection
server matching the engine's thread-per-sink model; no asyncio anywhere.
One port serves both the page (any plain HTTP GET, via `process_request`)
and the websocket upgrade.

Wire protocol (§8: serve map positions once, stream compact buffers):
- text `{"type": "hello", "n", "total", "positions", "is3d", "fps"}` on
  connect — the only time positions cross the wire;
- binary frames: `<fI` little-endian header (engine time `t`, sequence
  number) then `n*3` display-ready uint8 RGB. Gamma and quantization
  happen server-side in `to_display_u8` (Q-1 quantize-once): a dumb
  client can never reintroduce the crushed-glow bug (b68b96a);
- text `{"type": "status", "error": str|null}` when the renderer's error
  state changes.

Budget (LedFx caps its frontend at 4096 px [S508]): mappings larger than
`max_pixels` are decimated once at construction with evenly spaced
indices; the hello carries only the decimated positions, so the client is
oblivious. `max_fps` throttles the stream via the shared `RateGate`.

Fan-out: `send` encodes each frame once, then submits the payload to one
`SinkDriver` per connected client wrapping that client's blocking
`connection.send` — a stalled tab stalls only its own driver and gets
newest-wins coalescing, never a queue. The payload carries the *current*
status string rather than a delta, so coalescing can never lose a status
transition: whichever payload survives holds the latest truth.
"""

from __future__ import annotations

import json
import logging
import struct
import threading
import time
from importlib import resources
from typing import Callable

import numpy as np
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve

from pewpew.pace import SinkDriver
from pewpew.sinks.base import RateGate, to_display_u8

logger = logging.getLogger(__name__)

_Payload = tuple[bytes, "str | None"]


class _Client:
    """One connected browser: its per-client driver and last-sent status."""

    def __init__(self, conn: ServerConnection, name: str) -> None:
        self.conn = conn
        self.last_status: str | None = None
        self.driver: SinkDriver[_Payload] = SinkDriver(self._send, name=name)

    def _send(self, t: float, payload: _Payload) -> None:
        data, status = payload
        self.conn.send(data)
        if status != self.last_status:
            self.last_status = status
            self.conn.send(json.dumps({"type": "status", "error": status}))


class PreviewSink:
    """Serve `http://host:port/` and stream frames to every open tab."""

    def __init__(
        self,
        mapping: np.ndarray,
        *,
        host: str = "127.0.0.1",
        port: int = 7447,
        max_fps: float = 30.0,
        max_pixels: int = 4096,
        status: Callable[[], str | None] | None = None,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        mapping = np.asarray(mapping, dtype=np.float32)
        n = len(mapping)
        if n > max_pixels:
            self._idx: np.ndarray | None = (
                np.linspace(0.0, n - 1, max_pixels).round().astype(np.int64)
            )
            sent = mapping[self._idx]
        else:
            self._idx = None
            sent = mapping
        self._hello = json.dumps(
            {
                "type": "hello",
                "n": len(sent),
                "total": n,
                "positions": np.round(sent.astype(np.float64), 4).tolist(),
                "is3d": bool(np.ptp(mapping[:, 2]) > 1e-6),
                "fps": max_fps,
            }
        )
        self._gate = RateGate(max_fps, now=now, sleep=sleep)
        self._status = status
        self._current_status: str | None = None
        self.host = host
        self._port_arg = port
        self.port: int | None = None  # actual bound port, set by start()
        self._server: Server | None = None
        self._thread: threading.Thread | None = None
        self._clients: dict[ServerConnection, _Client] = {}
        self._lock = threading.Lock()
        self._seq = 0

    # -- transport lifecycle --------------------------------------------------

    def start(self) -> None:
        if self._server is not None:
            raise RuntimeError("PreviewSink is already started")
        # compression=None: frames are small, fresh every tick, and latency
        # matters more than wire size on localhost.
        self._server = serve(
            self._handler,
            self.host,
            self._port_arg,
            process_request=self._process_request,
            compression=None,
        )
        self.port = self._server.socket.getsockname()[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="pewpew-preview-server", daemon=True
        )
        self._thread.start()
        # Debug, not info: the *runner* announces the URL (it must print even
        # when log records are being deferred away from the terminal), and two
        # copies of one line is worse than none. Embedders read `sink.port`.
        logger.debug("preview serving at http://%s:%d/", self.host, self.port)

    def stop(self) -> None:
        if self._server is None:
            return
        with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            try:
                client.conn.close()
            except Exception:  # closing a dying socket must not abort teardown
                pass
        self._server.shutdown()  # closes the listener, waits for handlers
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for client in clients:
            client.driver.stop(timeout=0.5)
        self._server = None
        self._thread = None
        self.port = None

    def __enter__(self) -> "PreviewSink":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- engine side ----------------------------------------------------------

    def send(self, t: float, frame: np.ndarray) -> None:
        self._gate.wait()
        u8 = to_display_u8(frame if self._idx is None else frame[self._idx])
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        data = struct.pack("<fI", t, self._seq) + u8.tobytes()
        status = self._status() if self._status is not None else None
        self._current_status = status
        with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            client.driver.submit(t, (data, status))

    # -- server side (per-connection threads) ---------------------------------

    def _process_request(self, conn: ServerConnection, request) -> object | None:
        if "Upgrade" in request.headers:
            return None  # continue the websocket handshake
        body = resources.files("pewpew.sinks").joinpath("web/index.html").read_text()
        response = conn.respond(200, body)
        del response.headers["Content-Type"]
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    def _handler(self, conn: ServerConnection) -> None:
        client = _Client(conn, name=f"preview-{str(conn.id)[:8]}")
        conn.send(self._hello)
        status = self._current_status
        client.last_status = status
        if status is not None:
            conn.send(json.dumps({"type": "status", "error": status}))
        client.driver.start()
        with self._lock:
            self._clients[conn] = client
        try:
            for _ in conn:  # drain (and ignore) client messages until close
                pass
        except ConnectionClosed:
            pass  # abrupt closes (killed tab, dead socket) are routine
        finally:
            with self._lock:
                self._clients.pop(conn, None)
            client.driver.stop(timeout=0.5)
