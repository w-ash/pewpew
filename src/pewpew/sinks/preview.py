"""Browser preview sink: positions once, then compact color buffers.

Transport is `websockets.sync.server` (ADR-020) — a thread-per-connection
server matching the engine's thread-per-sink model; no asyncio anywhere.
One port serves both the page (any plain HTTP GET, via `process_request`)
and the websocket upgrade.

Wire protocol (§8: serve map positions once, stream compact buffers):
- text `{"type": "hello", "n", "total", "positions", "is3d", "fps",
  "params"}` on connect — the only time positions cross the wire.
  `params` is `ParamSet.describe()`, or `[]` when no `controls` are wired;
- binary frames: `<fI` little-endian header (engine time `t`, sequence
  number) then `n*3` display-ready uint8 RGB. Gamma and quantization
  happen server-side in `to_display_u8` (Q-1 quantize-once): a dumb
  client can never reintroduce the crushed-glow bug (b68b96a);
- text `{"type": "status", "error": str|null}` when the renderer's error
  state changes;
- text `{"type": "params", "values": {name: value}}` to every client when
  a set is accepted, so a second tab's sliders follow the one that moved
  (architecture §5: last-write-wins, server pushes merged state);
- text `{"type": "declare", "params": [...]}` — the hello's `params` minus
  the values — when the declarations themselves change, which a hot reload
  that adds, drops or retunes a knob does; the client rebuilds its sliders
  and the `params` echo that follows fills them in;
- text `{"type": "refused", "name", "reason"}` to the client that asked,
  when `controls.set` declines. The reason names the knob and its range
  and never a source path — this port is unauthenticated by design;
- inbound, the only message a client may send:
  `{"type": "set", "name": str, "value": number}`.

Budget (LedFx caps its frontend at 4096 px [S508]): mappings larger than
`max_pixels` are decimated once at construction with evenly spaced
indices; the hello carries only the decimated positions, so the client is
oblivious. `max_fps` throttles the stream via the shared `RateGate`.

Fan-out: `send` encodes each frame once, then submits the payload to one
`SinkDriver` per connected client wrapping that client's blocking
`connection.send` — a stalled tab stalls only its own driver and gets
newest-wins coalescing, never a queue. The payload carries the *current*
status string and the *current* param echo rather than deltas, so
coalescing can never lose a transition: whichever payload survives holds
the latest truth.
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
from pewpew.sinks.base import Controls, RateGate, to_display_u8

logger = logging.getLogger(__name__)

# (frame bytes, current status, current param echo, current declarations) —
# see the module docstring on why the last three are absolute state, not
# deltas.
_Payload = tuple[bytes, "str | None", "str | None", "str | None"]


def _params_message(declared: list[dict]) -> str:
    """The `params` echo for a set of declarations, as wire text."""
    return json.dumps({"type": "params", "values": {p["name"]: p["value"] for p in declared}})


def _declare_message(declared: list[dict]) -> str:
    """The value-free declarations as wire text — both the `declare` message
    and the signature a client compares to notice a change."""
    return json.dumps(
        {"type": "declare", "params": [{k: v for k, v in p.items() if k != "value"} for p in declared]}
    )


class _Client:
    """One connected browser: its per-client driver and what it last saw.

    Two threads call `self.conn.send`: this client's driver worker, and the
    connection's own handler thread replying to a refusal. That is safe
    without a lock here — `websockets.sync`'s `Connection.send` serializes
    unfragmented sends on its `protocol_mutex` (see `send_context`).
    """

    def __init__(self, conn: ServerConnection, name: str) -> None:
        self.conn = conn
        self.last_status: str | None = None
        self.last_params: str | None = None
        self.last_declare: str | None = None
        self.driver: SinkDriver[_Payload] = SinkDriver(self._send, name=name)

    def _send(self, t: float, payload: _Payload) -> None:
        data, status, params, declare = payload
        self.conn.send(data)
        if status != self.last_status:
            self.last_status = status
            self.conn.send(json.dumps({"type": "status", "error": status}))
        if declare != self.last_declare:
            # New sliders, built empty. The values echo must follow even when
            # its text is identical to the last one sent: a reload that keeps
            # every value still leaves the rebuilt levers to be filled in.
            # `declare` is a str here: it is None only when no controls are
            # wired, and then `last_declare` was seeded None too.
            self.last_declare = declare
            self.last_params = None
            self.conn.send(declare)
        if params != self.last_params:
            self.last_params = params
            self.conn.send(params)


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
        controls: Controls | None = None,
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
        # Everything in the hello except `params`, which is read per
        # connection: values move while the show runs, so a tab opened later
        # must see where the knobs are now, not where they started.
        self._hello_fixed = {
            "type": "hello",
            "n": len(sent),
            "total": n,
            "positions": np.round(sent.astype(np.float64), 4).tolist(),
            "is3d": bool(np.ptp(mapping[:, 2]) > 1e-6),
            "fps": max_fps,
        }
        self._gate = RateGate(max_fps, now=now, sleep=sleep)
        self._status = status
        self._controls = controls
        self._current_status: str | None = None
        self.host = host
        self._port_arg = port
        self.port: int | None = None  # actual bound port, set by start()
        self._server: Server | None = None
        self._thread: threading.Thread | None = None
        self._clients: dict[ServerConnection, _Client] = {}
        self._lock = threading.Lock()
        self._stopping = threading.Event()
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
        self._stopping.clear()
        self._thread = threading.Thread(
            target=self._serve, name="pewpew-preview-server", daemon=True
        )
        self._thread.start()
        # Debug, not info: the *runner* announces the URL (it must print even
        # when log records are being deferred away from the terminal), and two
        # copies of one line is worse than none. Embedders read `sink.port`.
        logger.debug("preview serving at http://%s:%d/", self.host, self.port)

    def _serve(self) -> None:
        """Run the accept loop, tolerating a listener closed out from under
        it by `stop()`.

        `start()` returns as soon as the thread is spawned, so a stop that
        arrives immediately can close the socket before `serve_forever` has
        finished starting — it then raises EBADF from its own opening log
        line. That is an orderly teardown, not a failure; anything raised
        while we are *not* stopping still propagates.
        """
        try:
            self._server.serve_forever()  # type: ignore[union-attr]
        except OSError:
            if not self._stopping.is_set():
                raise
            logger.debug("preview listener closed while starting up")

    def stop(self) -> None:
        if self._server is None:
            return
        self._stopping.set()
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
        # Recomposed every frame rather than pushed when a set lands: a set
        # is queued onto the loop thread, so at the moment it is accepted the
        # value has not moved yet and an echo built then would ship the old
        # one. Reading current truth here is 2 us, on this worker thread, and
        # never touches the render loop. Clients see it only on a change.
        params, declare = self._echo()
        with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            client.driver.submit(t, (data, status, params, declare))

    def _echo(self) -> tuple[str | None, str | None]:
        """The current knob state as a (`params`, `declare`) message pair from
        one `describe()` call, or (None, None) if no controls are wired."""
        if self._controls is None:
            return None, None
        declared = self._controls.describe()
        return _params_message(declared), _declare_message(declared)

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
        declared = self._controls.describe() if self._controls is not None else []
        conn.send(json.dumps({**self._hello_fixed, "params": declared}))
        status = self._current_status
        client.last_status = status
        if status is not None:
            conn.send(json.dumps({"type": "status", "error": status}))
        # The hello just carried these values, so an echo identical to them is
        # not news to this client — same seeding as `last_status`. If a set
        # lands before the next frame, that frame's echo corrects it.
        client.last_params = _params_message(declared) if self._controls is not None else None
        client.last_declare = _declare_message(declared) if self._controls is not None else None
        client.driver.start()
        with self._lock:
            self._clients[conn] = client
        try:
            for message in conn:
                self._on_message(conn, message)
        except ConnectionClosed:
            pass  # abrupt closes (killed tab, dead socket) are routine
        finally:
            with self._lock:
                self._clients.pop(conn, None)
            client.driver.stop(timeout=0.5)

    def _on_message(self, conn: ServerConnection, message: object) -> None:
        """Handle one inbound message. Anything malformed is ignored.

        A viewer is not trusted to send well-formed anything, and this runs
        on the connection's own thread: raising here would drop a live tab
        over a typo in someone's console. The *value* is passed through
        untouched — `ParamSet.check` already rejects bools, non-numbers and
        non-finite values, and is the single source of every refusal
        wording, so this sink writes no validation of its own.
        """
        if self._controls is None or not isinstance(message, str):
            return
        try:
            request = json.loads(message)
        except ValueError:
            return
        if not isinstance(request, dict) or request.get("type") != "set":
            return
        name = request.get("name")
        if not isinstance(name, str):
            return
        reason = self._controls.set(name, request.get("value"))
        if reason is not None:
            conn.send(json.dumps({"type": "refused", "name": name, "reason": reason}))
        # An accepted set needs no reply: `send` republishes the whole knob
        # state on the next frame, and every tab converges on what won.
