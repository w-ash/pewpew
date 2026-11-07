"""The asyncio side of a session: a one-slot frame mailbox and the sender.

The session thread posts through `loop.call_soon_threadsafe`. Frames and power
readings keep only the newest value, so a slow client loses frames and never
queues them. Discrete messages (hello, bound, refused) keep their order; their
queue is bounded, and overflow closes the socket. A hello drops the pending
frame, because that frame predates it, and every per-frame message goes
again after it.

Beside each frame the pump sends each per-frame message whose text has
changed since this client last got it, as the preview does
(`pewpew.sinks.preview.changed_texts`).
"""

from __future__ import annotations

import asyncio
import json
from collections import deque

from fastapi import WebSocket

from pewpew.sinks.preview import changed_texts
from pewpew.studio.session import FramePayload

MAX_CONTROL_BACKLOG = 256


class Outbox:
    """Implements `SessionSink`. Its methods are safe from any thread."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._event = asyncio.Event()
        # Each message, and whether it is a hello.
        self._control: deque[tuple[dict, bool]] = deque()
        self._frame: FramePayload | None = None
        self._power: tuple[float, float] | None = None
        self._dead = False
        self._closing = False
        self.overflow = False

    def _post(self, fn, *args) -> None:
        try:
            self._loop.call_soon_threadsafe(fn, *args)
        except RuntimeError:  # the event loop is closed: the server is going down
            pass

    # -- SessionSink (session thread) ----------------------------------------

    def frame(self, payload: FramePayload) -> None:
        self._post(self._put_frame, payload)

    def hello(self, message: dict) -> None:
        self._post(self._put_control, message, True)

    def control(self, message: dict) -> None:
        self._post(self._put_control, message, False)

    def power(self, watts: float, uncapped_watts: float) -> None:
        self._post(self._put_power, (watts, uncapped_watts))

    def closed(self) -> None:
        self._post(self._put_dead)

    # -- the app (any thread) ----------------------------------------------------

    def close_with(self, message: dict) -> None:
        """Send `message` after the queued ones, then end `pump`."""
        self._post(self._put_close, message)

    # -- event loop ------------------------------------------------------------

    def _put_frame(self, payload: FramePayload) -> None:
        self._frame = payload
        self._event.set()

    def _put_control(self, message: dict, hello: bool) -> None:
        if len(self._control) >= MAX_CONTROL_BACKLOG:
            self.overflow = True
        else:
            self._control.append((message, hello))
            if hello:
                self._frame = None
        self._event.set()

    def _put_close(self, message: dict) -> None:
        self._control.append((message, False))
        self._closing = True
        self._event.set()

    def _put_power(self, reading: tuple[float, float]) -> None:
        self._power = reading
        self._event.set()

    def _put_dead(self) -> None:
        self._dead = True
        self._event.set()

    async def pump(self, ws: WebSocket) -> None:
        """Send until the session dies, the backlog overflows or `close_with`
        is called. Each per-frame message goes out only on a change, as in
        the preview."""
        last: dict[str, str | None] = {}
        while True:
            await self._event.wait()
            self._event.clear()
            if self.overflow or self._dead:
                return
            while self._control:
                message, hello = self._control.popleft()
                await ws.send_text(json.dumps(message))
                if hello:
                    last.clear()
            if self._closing:
                return
            if self._power is not None:
                (watts, uncapped), self._power = self._power, None
                await ws.send_text(json.dumps({"type": "power", "watts": watts, "uncapped_watts": uncapped}))
            payload, self._frame = self._frame, None
            if payload is None:
                continue
            await ws.send_bytes(payload.data)
            for text in changed_texts(payload.texts, last):
                await ws.send_text(text)
