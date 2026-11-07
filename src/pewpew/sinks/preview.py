"""Browser preview sink: map positions once, then compact color frames.

Transport is `websockets.sync.server` (ADR-020): one thread per connection,
no asyncio. One port serves the page (any HTTP GET), the floor plan
(`GET /plan`) and the websocket upgrade (any path; the page uses `/ws`).

Wire protocol. web/src/wire/protocol.ts types every message and says
what its fields mean. Each message has one source here: `hello` and
`layout` are `_View.of` (`room` is `RoomMap.describe()`), `status` is the
`status` supplier, and `declare`, `params`, `mod`, `aura`, `health` and
`catalog` are the control's states (`pewpew.aura.control.wire_states`),
made text by `StateTexts`, which the studio uses too. A state that is the
same object as the last one read keeps its text, so the large `catalog`
is serialized once, and again only when it changes (an op file loads).
`mod`, the live values of the knobs a route drives, changes every frame,
so it is read at most `MOD_HZ` times a second on the injected clock, and
sent no more often (ADR-006 amendment "layered paths"). The hello
carries the page's build stamp, so a tab opened on an older page reloads.
A new client gets the hello, then the current text of every other message
but `layout` and `refused`; after that, each one when its text changes. A
binary frame is a `<fI` header (engine `t`, sequence number) and `n*3`
display-ready RGB: gamma and quantization happen here, once (Q-1). Every
text message is absolute state, so the last write wins on every tab.
`refused` goes only to the client that asked; its reason names a param,
layer, look, fixture or cap, never a path. Each inbound message goes
whole to `Control.request`, in the order it came; a request that answers
later (a look to make) is answered when its future is done, and the
messages after it are read meanwhile (`answer_request`, which the studio
uses too).

Any client may give a message an `id`; the engine then answers it,
accepted or not: `ack` with the `id` and the control, or `refused` with
them, the control null when the `type` is not text (ADR-020 amendment
"capabilities"). The bundled page gives one only to the requests it
shows busy until they are answered: `surprise`, `vary` and `keep`. The
hello's `capabilities` names what a client outside the package (`push`,
an agent) may rely on: `ack`, and the control's own (`look`). The page
never reads `capabilities`: it ships with its engine.

Security. The port has no login (architecture §5, ADR-006's trust model
amendment): bind `host` to the private router. Every request gets 403
unless it has one `Host`, an IP address or `localhost` with the bound
port, so DNS rebinding cannot reach it. An upgrade with more than one
`Origin`, or one that is not its `Host`, gets 403, so a page from another
site cannot drive the aura; an upgrade with no `Origin` is accepted. `/plan` serves one fixed file, and no path
crosses the socket. An input that listens elsewhere needs a token and a
sender allowlist (ADR-009).

Budget: a map over `max_pixels` (LedFx caps at 4096 [S508]) is decimated
once, evenly; the client never knows. `max_fps` throttles through
`RateGate`.

Fan-out: `send` encodes each frame once and submits it to one `SinkDriver`
per client, so a stalled tab stalls only itself. The payload carries the
current text of every message, not deltas, so newest-wins coalescing never
loses a transition.
"""

from __future__ import annotations

import functools
import gzip
import ipaddress
import json
import logging
import re
import struct
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Self

import numpy as np
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response
from websockets.sync.server import Server, ServerConnection, serve

from pewpew.aura.control import wire_states
from pewpew.errors import Refusal
from pewpew.jsonfile import loads
from pewpew.room.map import IMAGE_TYPES
from pewpew.sinks.sink import DISPLAY_GAMMA, Control, RateGate, SinkDriver, to_display_u8

logger = logging.getLogger(__name__)

# The text messages a client gets when their text changes, in send order,
# each with the key its state goes under (None: the state is the body).
# Each is absolute state, not a delta; None means its source is not wired,
# and is never sent.
_MESSAGES = {
    "status": None, "declare": "params", "params": "values", "mod": "values", "aura": None, "health": None,
    "catalog": None,
}
# How often the `mod` message's values are read, at most, a second.
MOD_HZ = 10.0
# (frame bytes, current view, the current text of each of `_MESSAGES`)
_Payload = tuple[bytes, "_View", "tuple[str | None, ...]"]

# How long `stop()` waits on each client that does not answer the close.
CLOSE_TIMEOUT_S = 1.0

FRAME_HEADER = struct.Struct("<fI")  # a binary frame's engine time and sequence number

PLAN_URL = "/plan"


def message(kind: str, state: Any) -> str:
    """The wire text of the `kind` message of `_MESSAGES` for `state`: the
    status, the declarations, the values, the live values, the `aura`
    state, the health or the catalog. The studio sends the same text
    (pewpew.studio.session)."""
    key = _MESSAGES[kind]
    return json.dumps({"type": kind, **(state if key is None else {key: state})})


def status_state(status: tuple[str, str, str | None] | None) -> dict[str, str | None]:
    """The `status` message's state for a `(source, error, path)` status, or for none."""
    source, error, path = status or (None, None, None)
    return {"error": error, "source": source, "path": path}


def refusal(
    control: str | None, reason: str, *, name: str | None = None, id: object = None, **extra: object,
) -> dict[str, Any]:
    """A `refused` message: the control refused (None when the request's
    `type` is not text), the knob it named, the request's `id`, and why.
    The studio sends the same shape (pewpew.studio.app)."""
    return {"type": "refused", "control": control, "name": name, "id": id, "reason": reason, **extra}


_PLAN_MISSING = "the floor plan image was not found or is not a file; drawing the room without it"


@dataclass(frozen=True)
class _View:
    """The positions clients draw, swapped whole by `remap`.

    `generation` counts remaps; a client compares it with the one it last
    saw. `total` is the full map size, which a frame must match.
    """

    generation: int
    total: int
    idx: np.ndarray | None  # decimation indices, or None to send every pixel
    hello: str  # the `hello` message text
    layout: str  # the `layout` message text
    plan_image: Path | None = None  # the file served at PLAN_URL

    @classmethod
    def of(
        cls,
        mapping: np.ndarray,
        max_pixels: int,
        generation: int,
        room: dict | None = None,
        plan_image: Path | None = None,
        capabilities: tuple[str, ...] = (),
    ) -> _View:
        mapping = np.asarray(mapping, dtype=np.float32)
        n = len(mapping)
        idx = np.linspace(0.0, n - 1, max_pixels).round().astype(np.int64) if n > max_pixels else None
        sent = mapping if idx is None else mapping[idx]
        served = None
        if room is not None:
            room = dict(room)
            if idx is not None:
                room["fixture_of"] = [room["fixture_of"][i] for i in idx.tolist()]
            if room.get("plan") is not None:
                if plan_image is not None and plan_image.is_file():
                    served = plan_image
                    # The generation busts the browser cache after a reload.
                    room["plan"] = {**room["plan"], "url": f"{PLAN_URL}?v={generation}"}
                else:
                    room["plan"] = {"error": _PLAN_MISSING}
        shape = {
            "n": len(sent),
            "total": n,
            "positions": np.round(sent.astype(np.float64), 4).tolist(),
            "is3d": bool(np.ptp(mapping[:, 2]) > 1e-6),
            "room": room,
        }
        return cls(
            generation, n, idx,
            json.dumps({"type": "hello", **shape, "display_gamma": DISPLAY_GAMMA, "build": page_build(),
                        "capabilities": list(capabilities)}),
            json.dumps({"type": "layout", **shape}),
            served,
        )


def _split_host(value: str) -> tuple[str, int] | None:
    """Split a `Host` or origin authority into (host, port), or None when it
    does not parse. The port is 80 when absent (plain HTTP is all this
    server speaks); an IPv6 host loses its brackets."""
    value = value.strip().lower()
    if value.startswith("["):
        host, sep, rest = value[1:].partition("]")
        if not sep or (rest and not rest.startswith(":")):
            return None
        port = rest[1:]
    else:
        host, _, port = value.partition(":")
    if not host:
        return None
    if not port:
        return host, 80
    return (host, int(port)) if port.isascii() and port.isdigit() else None


def _is_address(host: str) -> bool:
    """True for an IP literal or `localhost`: names no DNS answer can move."""
    if host == "localhost":
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


@functools.cache
def _page() -> tuple[bytes, bytes]:
    """The page as served: (raw bytes, gzipped bytes). Read once per process."""
    raw = resources.files("pewpew.sinks").joinpath("web/index.html").read_bytes()
    # mtime=0 keeps the gzip bytes the same from run to run.
    return raw, gzip.compress(raw, mtime=0)


@functools.cache
def page_build() -> str | None:
    """The served page's build stamp (tools/webhash.py), or None without one."""
    found = re.search(rb'<meta name="pewpew-build" content="([0-9a-f]+)"', _page()[0])
    return found.group(1).decode() if found else None


def _accepts_gzip(accept: str) -> bool:
    """Whether an `Accept-Encoding` value lists gzip. Every browser sends it
    plainly, so q-values are not read."""
    return "gzip" in (item.partition(";")[0].strip() for item in accept.lower().split(","))


def _set_header(response: Response, name: str, value: str) -> None:
    """Replace header `name` of an HTTP response, or add it."""
    if name in response.headers:
        del response.headers[name]
    response.headers[name] = value


def _bytes_response(conn: ServerConnection, body: bytes, headers: dict[str, str]) -> Response:
    """A 200 response carrying `body`, with its length and `headers`."""
    response = conn.respond(200, "")
    response.body = body
    for name, value in {"Content-Length": str(len(body)), **headers}.items():
        _set_header(response, name, value)
    return response


def answer(control: str | None, rid: object, refused: Refusal | None) -> dict[str, Any] | None:
    """The answer to a request: `refused` with that refusal's reason, else
    `ack` when it carries an `id`, `rid`, else None. An accepted request
    without an id needs no reply: the next frame carries the whole state,
    and every tab converges on what won."""
    if refused is not None:
        return refusal(control, refused.reason, name=refused.name, id=rid)
    return None if rid is None else {"type": "ack", "id": rid, "control": control}


def answer_request(control: Control, request: dict, reply: Callable[[dict[str, Any]], None]) -> None:
    """Pass `request`, one inbound message, whole to `control`, and `reply`
    with its `answer`: at once, or for a request that answers later (a look
    to make) on the thread that finishes it. A message with no `id` that
    names no control, or sets no knob, is passed over: there is nobody to
    tell. May block until the loop thread has answered (`Control.request`)."""
    kind, rid = request.get("type"), request.get("id")
    if rid is None and (not isinstance(kind, str) or (kind == "set" and not isinstance(request.get("name"), str))):
        return
    name = kind if isinstance(kind, str) else None
    answered = control.request(request)
    if isinstance(answered, Future):
        answered.add_done_callback(lambda done: _reply(reply, answer(name, rid, done.result())))
    else:
        _reply(reply, answer(name, rid, answered))


def _reply(reply: Callable[[dict[str, Any]], None], message: dict[str, Any] | None) -> None:
    if message is not None:
        reply(message)


def changed_texts(texts: tuple[str | None, ...], last: dict[str, str | None]) -> Iterator[str]:
    """Each of `texts`, the current text of each of `_MESSAGES` in order,
    that differs from `last`, the text a client last got of each kind;
    `last` is updated as each is yielded. A new `declare` makes the
    `params` after it go too, even when its text is the same: the client
    builds its controls empty, and a reload that keeps every value still
    leaves them to be filled in."""
    for kind, text in zip(_MESSAGES, texts):
        if text is None or text == last.get(kind):
            continue
        last[kind] = text
        if kind == "declare":
            last["params"] = None
        yield text


class StateTexts:
    """The current text of each of `_MESSAGES` for one control (None: no
    control), read whole each time (the module docstring): the `status`
    given, and the control's states (`wire_states`), None for a source not
    wired. Read every frame rather than pushed when a set lands: a set is
    queued onto the loop thread, so when it is accepted the value has not
    moved yet. Serialized every frame, so a client compares texts, and a
    value that changes kind (1 to true) is sent even when it compares
    equal."""

    def __init__(self, control: Control | None, now: Callable[[], float]) -> None:
        self._control = control
        self._now = now
        # When the `mod` values may next be read, and the last read.
        self._mod: tuple[float, dict | None] = (0.0, None)
        # Each message's last state and its text, by message type: see `_text`.
        self._texts: dict[str, tuple[object, str]] = {}

    def __call__(self, status: tuple[str, str, str | None] | None) -> tuple[str | None, ...]:
        states: dict[str, Any] = {"status": status_state(status)}
        if self._control is not None:
            states |= wire_states(self._control, self._mod_values(self._control))
        return tuple(self._text(kind, states.get(kind)) for kind in _MESSAGES)

    def _text(self, kind: str, state: Any) -> str | None:
        """Message `kind`'s text for `state` (`message`), or None for no
        state. A state that is the same object as the last one keeps its
        text: a source replaces its state whole when it changes."""
        if state is None:
            return None
        last = self._texts.get(kind)
        if last is not None and last[0] is state:
            return last[1]
        text = message(kind, state)
        self._texts[kind] = (state, text)
        return text

    def _mod_values(self, control: Control) -> dict:
        """The driven knobs' live values (`Control.mod`), read at most
        `MOD_HZ` times a second; between reads, the last one. Each read is
        one swap of `_mod`, so a connection thread and the sending thread
        share it safely."""
        due, values = self._mod
        t = self._now()
        if values is None or t >= due:
            values = control.mod()
            self._mod = (t + 1.0 / MOD_HZ, values)
        return values


def _send(conn: ServerConnection, message: dict[str, Any]) -> None:
    """Send `message` on `conn`, unless the tab has closed."""
    try:
        conn.send(json.dumps(message))
    except ConnectionClosed:
        pass  # the tab closed while its request ran


class _Client:
    """One connected browser: its per-client driver and what it last saw.

    Two threads call `self.conn.send`: this client's driver worker, and the
    connection's own handler thread replying to a refusal. That is safe
    without a lock here — `websockets.sync`'s `Connection.send` serializes
    unfragmented sends on its `protocol_mutex` (see `send_context`).
    """

    def __init__(self, conn: ServerConnection, name: str, view: int, last: tuple[str | None, ...]) -> None:
        self.conn = conn
        self.last: dict[str, str | None] = dict(zip(_MESSAGES, last))
        self.last_view = view
        self.driver: SinkDriver[_Payload] = SinkDriver(self._send, name=name)

    def _send(self, t: float, payload: _Payload) -> None:
        data, view, messages = payload
        if view.generation != self.last_view:
            # Before the frame: its bytes are laid out for the new positions.
            self.last_view = view.generation
            self.conn.send(view.layout)
        self.conn.send(data)
        for text in changed_texts(messages, self.last):
            self.conn.send(text)


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
        status: Callable[[], tuple[str, str, str | None] | None] | None = None,
        control: Control | None = None,
        room: dict | None = None,
        plan_image: Path | None = None,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_pixels = max_pixels
        # A client's `id` is answered only when there is a control to ask.
        self._capabilities = ("ack", *control.capabilities) if control is not None else ()
        self._view = _View.of(mapping, max_pixels, 0, room, plan_image, self._capabilities)
        self._control = control
        self._states = StateTexts(control, now)
        self._gate = RateGate(max_fps, now=now, sleep=sleep)
        self._status = status
        self._current_status: tuple[str, str, str | None] | None = None
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
            close_timeout=CLOSE_TIMEOUT_S,
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
        """Run the accept loop. A `stop()` right after `start()` can close the
        listener before `serve_forever` is up, and that EBADF is no failure
        while stopping."""
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
        self._server.shutdown()  # closes the listener and every client at once, waits for handlers
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for client in clients:
            client.driver.stop(timeout=0.5)
        self._server = None
        self._thread = None
        self.port = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- engine side ----------------------------------------------------------

    def remap(self, mapping: np.ndarray, room: dict | None = None, plan_image: Path | None = None) -> None:
        """Draw later frames at `mapping`'s positions, with `room` and
        `plan_image` as the constructor takes them. Every open page gets a
        `layout` message before the first such frame. Call it after the
        renderer was rebound, from the thread that feeds `send`'s frames."""
        self._view = _View.of(
            mapping, self._max_pixels, self._view.generation + 1, room, plan_image, self._capabilities,
        )

    def send(self, t: float, frame: np.ndarray) -> None:
        self._gate.wait()
        view = self._view
        if len(frame) != view.total:
            return  # rendered before a remap; the next frame fits
        status = self._status() if self._status is not None else None
        self._current_status = status  # a later hello reads it
        with self._lock:
            clients = list(self._clients.values())
        if not clients:
            return
        u8 = to_display_u8(frame if view.idx is None else frame[view.idx])
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        data = FRAME_HEADER.pack(t, self._seq) + u8.tobytes()
        messages = self._states(status)
        for client in clients:
            client.driver.submit(t, (data, view, messages))

    # -- server side (per-connection threads) ---------------------------------

    def _process_request(self, conn: ServerConnection, request: Request) -> Response | None:
        """The page, the plan or the handshake, or 403 (the module docstring's
        security rules). A repeated header is read whole, never raised on."""
        headers = request.headers
        hosts = headers.get_all("Host")
        authority = _split_host(hosts[0]) if len(hosts) == 1 else None
        if authority is None or not _is_address(authority[0]) or authority[1] != self.port:
            return conn.respond(403, "open this page by the laptop's address\n")
        if "Upgrade" in headers:
            origins = headers.get_all("Origin")
            if len(origins) > 1 or (origins and _split_host(origins[0].partition("://")[2]) != authority):
                return conn.respond(403, "cross-origin websocket refused\n")
            return None  # continue the websocket handshake
        if request.path.partition("?")[0] == PLAN_URL:
            return self._plan_response(conn)
        return self._page_response(conn, ", ".join(headers.get_all("Accept-Encoding")))

    def _page_response(self, conn: ServerConnection, accept: str) -> Response:
        """The page, gzipped when `accept` (the request's Accept-Encoding)
        allows it."""
        raw, gz = _page()
        # no-cache: a reload after an engine upgrade gets the new page.
        headers = {"Content-Type": "text/html; charset=utf-8", "Vary": "Accept-Encoding", "Cache-Control": "no-cache"}
        if _accepts_gzip(accept):
            return _bytes_response(conn, gz, {**headers, "Content-Encoding": "gzip"})
        return _bytes_response(conn, raw, headers)

    def _plan_response(self, conn: ServerConnection) -> Response:
        """The floor-plan image, read fresh, or a 404 that names no path."""
        image = self._view.plan_image
        try:
            if image is None:
                raise FileNotFoundError
            data = image.read_bytes()
        except OSError:
            return conn.respond(404, "no floor plan image\n")
        kind = IMAGE_TYPES.get(image.suffix.lower(), "application/octet-stream")
        return _bytes_response(conn, data, {"Content-Type": kind, "Cache-Control": "no-store"})

    def _handler(self, conn: ServerConnection) -> None:
        view = self._view
        messages = self._states(self._current_status)
        conn.send(view.hello)
        for message in messages:
            if message is not None:
                conn.send(message)
        client = _Client(conn, f"preview-{str(conn.id)[:8]}", view.generation, messages)
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
        over a typo in someone's console. Values are passed through
        untouched — the control rejects values of the wrong type or range
        and is the single source of every refusal wording, so this sink
        writes no validation of its own. A message with an `id` is answered
        either way (the module docstring), at once or when the future the
        control returns is done; the `id` comes back as sent.
        """
        if not isinstance(message, str):
            return
        try:
            request = loads(message)
        except ValueError:  # not JSON, or nested too deep
            return
        if not isinstance(request, dict):
            return
        if self._control is not None:
            answer_request(self._control, request, lambda reply: _send(conn, reply))
