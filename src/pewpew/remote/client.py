"""A websocket client of an engine's preview port, as the page is one.

`Client` connects, reads every message on a thread of its own, and keeps
what it read: the last text message of each type (`latest`), a count of
each type (`counts`), and the newest binary frames in a bounded buffer
(`frames`). web/src/infra/wire/protocol.ts types every message, and
tests/goldens/wire.json holds real ones. A binary frame is the preview's
`FRAME_HEADER` (engine time, sequence number), then display-ready RGB,
one byte a channel. A `hello` or `layout` message starts a new map, so it
empties the frame buffer: a buffered frame is always drawn on the
positions it was sent for (`Client.view`).

Reading sends nothing. `send` is for a caller that controls the engine,
which is tier-1 actuation (CLAUDE.md T-7); bench/bench_soak.py is one.
"""

from __future__ import annotations

import contextlib
import json
import socket
import ssl
import threading
import time
from collections import Counter, deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Self

import numpy as np
from websockets.exceptions import ConnectionClosed, InvalidStatus, InvalidURI, WebSocketException
from websockets.sync.client import ClientConnection, connect
from websockets.uri import WebSocketURI, parse_uri

from pewpew.errors import describe_exception
from pewpew.sinks.preview import FRAME_HEADER

CLOSE_TIMEOUT_S = 2.0  # how long `close` waits for the engine to answer the close
_SCHEMES = {"ws": "ws", "wss": "wss", "http": "ws", "https": "wss"}
_EXAMPLE = "ws://127.0.0.1:7447/ or http://127.0.0.1:7447/"


class Unreachable(Exception):
    """The engine did not answer, or answered as no engine does. The
    message says why and what to try."""


@dataclass(frozen=True, slots=True)
class Frame:
    """One binary frame as the engine sent it."""

    t: float  # engine time; a float32 on the wire
    seq: int  # the engine's frame count, which wraps at 2**32
    rgb: np.ndarray  # (n, 3) uint8 at display gamma, read-only

    @classmethod
    def decode(cls, data: bytes) -> Frame | None:
        """The frame in `data`, or None when `data` is not a whole frame."""
        if len(data) < FRAME_HEADER.size or (len(data) - FRAME_HEADER.size) % 3:
            return None
        t, seq = FRAME_HEADER.unpack_from(data)
        return cls(t, seq, np.frombuffer(data, np.uint8, offset=FRAME_HEADER.size).reshape(-1, 3))


def engine_url(text: str) -> str:
    """`text` as the websocket URL of an engine's preview port, with its
    port and path written out. Takes a ws:// or wss:// URL, the http://
    address the run prints, or a bare HOST:PORT. Raises ValueError for
    anything else, such as a host name with an empty label."""
    scheme, sep, rest = text.strip().partition("://")
    try:
        uri = parse_uri(f"{_SCHEMES.get(scheme.lower(), '')}://{rest}" if sep else f"ws://{text.strip()}")
        uri.host.encode("idna")  # as `socket` encodes a host name before it looks it up
    except (InvalidURI, ValueError):  # ValueError: a port not from 0 to 65535, or a UnicodeError
        raise ValueError(f"expected an engine address such as {_EXAMPLE}, got {text!r}") from None
    return _written(uri, uri.host)


def with_host(url: str, host: str) -> str:
    """`url`, as `engine_url` writes it, with `host` (a name or an IP
    address) in its host's place."""
    return _written(parse_uri(url), host)


def _written(uri: WebSocketURI, host: str) -> str:
    """`uri` written out with `host` as its host, an IPv6 address bracketed."""
    host = f"[{host}]" if ":" in host else host
    return f"{'wss' if uri.secure else 'ws'}://{host}:{uri.port}{uri.resource_name}"


class Client:
    """A connection to an engine's preview port, read on a thread of its
    own (see the module docstring).

    `keep_frames` is how many of the newest frames to keep; 0 keeps none
    and only counts them. `on_text` gets each text message once it is kept,
    on the reader thread and while `wait` cannot read, so a caller can
    record more. Connecting makes up to `tries` attempts, `retry_s` apart,
    each given `open_timeout` seconds, and raises Unreachable when none
    connects.
    """

    def __init__(
        self,
        url: str,
        *,
        keep_frames: int = 0,
        on_text: Callable[[dict[str, Any]], None] | None = None,
        tries: int = 1,
        retry_s: float = 0.2,
        open_timeout: float = 5.0,
    ) -> None:
        self.url = url
        self._on_text = on_text
        self.latest: dict[str, dict[str, Any]] = {}
        self.counts: Counter[str] = Counter()
        self.frames: deque[Frame] = deque(maxlen=keep_frames)
        self.ended = False  # the reader has stopped: the connection closed
        self._cond = threading.Condition()
        self._ws = _connect(url, tries=tries, retry_s=retry_s, open_timeout=open_timeout)
        self._thread = threading.Thread(target=self._read, name="pewpew-remote-client", daemon=True)
        self._thread.start()

    @property
    def view(self) -> dict[str, Any] | None:
        """The map the buffered frames are drawn on: the hello, or the last
        layout after it. None before the hello."""
        return self.latest.get("layout") or self.latest.get("hello")

    def hello(self, timeout: float) -> dict[str, Any]:
        """Wait for the engine's hello and return it. Raises Unreachable when
        the connection closes, or nothing comes, within `timeout` seconds."""
        if not self.wait(lambda: self.view is not None, timeout):
            closed = "closed the connection" if self.ended else f"sent nothing for {timeout:g} s"
            raise Unreachable(f"{self.url} {closed} before its hello: is it a pewpew engine's preview port?")
        return self.latest["hello"]

    def wait(self, ready: Callable[[], bool], timeout: float) -> bool:
        """Block until `ready()` is true, the reader stops, or `timeout`
        seconds pass, and return `ready()`. `ready` runs while the reader
        waits, so what it reads holds still."""
        with self._cond:
            self._cond.wait_for(lambda: ready() or self.ended, timeout)
            return ready()

    @contextlib.contextmanager
    def hold(self) -> Iterator[None]:
        """Hold what the client keeps still for the block: in it, the
        reader keeps a message only while `wait` waits. So what a caller
        reads after a `wait` is what `ready` saw."""
        with self._cond:  # an RLock, which `wait` releases whole while it waits
            yield

    def send(self, message: dict[str, Any]) -> None:
        """Send one control message to the engine (tier 1). Raises
        Unreachable when the connection has closed, so it was not sent."""
        try:
            self._ws.send(json.dumps(message))
        except ConnectionClosed as exc:
            raise Unreachable(f"{self.url} closed the connection, so the {message.get('type')} was not sent: "
                              "observe the engine to see what it runs") from exc

    def close(self) -> None:
        """Close the connection and wait for the reader to stop."""
        with contextlib.suppress(Exception):
            self._ws.close()
        self._thread.join(timeout=3.0)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _read(self) -> None:
        try:
            for data in self._ws:
                self._take(data)
        except Exception as exc:  # noqa: BLE001  a dropped connection ends the reader
            with self._cond:
                self.counts[f"ended: {type(exc).__name__}"] += 1
        finally:
            with self._cond:
                self.ended = True
                self._cond.notify_all()

    def _take(self, data: str | bytes) -> None:
        """Keep one message. A text that is not a typed JSON object is left
        out, as the page leaves it out."""
        if isinstance(data, bytes):
            frame = Frame.decode(data) if self.frames.maxlen else None
            with self._cond:
                self.counts["frame"] += 1
                if frame is not None:
                    self.frames.append(frame)
                self._cond.notify_all()
            return
        try:
            message = json.loads(data)
        except (ValueError, RecursionError):
            return
        kind = message.get("type") if isinstance(message, dict) else None
        if not isinstance(kind, str):
            return
        with self._cond:
            self.counts[kind] += 1
            if kind in ("hello", "layout"):
                self.frames.clear()
            self.latest[kind] = message
            if self._on_text is not None:
                self._on_text(message)
            self._cond.notify_all()


def _connect(url: str, *, tries: int, retry_s: float, open_timeout: float) -> ClientConnection:
    """The open connection to `url`, after up to `tries` attempts."""
    failure: Exception | None = None
    for attempt in range(tries):
        if attempt:
            time.sleep(retry_s)
        try:
            # No proxy: an engine is on this machine or the private network.
            return connect(url, open_timeout=open_timeout, close_timeout=CLOSE_TIMEOUT_S, proxy=None)
        except (OSError, WebSocketException) as exc:
            failure = exc
    raise Unreachable(why_unreachable(url, failure, open_timeout)) from failure


def why_unreachable(url: str, exc: BaseException | None, open_timeout: float) -> str:
    """Why `url` did not connect, and what to try, in one sentence."""
    if isinstance(exc, InvalidStatus):
        status = exc.response.status_code
        if status == 403:
            return (
                f"{url} refused the connection (HTTP 403): a preview port answers only to an IP address "
                f"or localhost, such as {_EXAMPLE}"
            )
        return f"{url} answered HTTP {status}: is it a pewpew engine's preview port?"
    if isinstance(exc, WebSocketException):
        return f"{url} is not a pewpew engine's preview port ({describe_exception(exc)})"
    if isinstance(exc, ssl.SSLError):
        return (
            f"{url} did not answer TLS ({describe_exception(exc)}): a preview port speaks plain websocket, "
            f"so give {url.replace('wss://', 'ws://', 1)}"
        )
    if isinstance(exc, TimeoutError):
        return f"{url} did not answer within {open_timeout:g} s: check the address and that this machine can reach it"
    if isinstance(exc, socket.gaierror):
        return f"cannot find the host of {url} ({exc.strerror}): give its IP address, such as {_EXAMPLE}"
    reason = describe_exception(exc) if exc is not None else "no attempt"
    return (
        f"nothing answered at {url} ({reason}): start the engine with `python -m pewpew run PATTERN --preview`, "
        "or give the address its `preview at` line prints"
    )
