"""The asyncio side of a session: a one-slot frame mailbox and the sender.

The session thread posts through `loop.call_soon_threadsafe`. Frames and power
readings keep only the newest value, so a slow client loses frames and never
queues them. Discrete messages (hello, layout, refused) keep their order;
their queue is bounded, and overflow closes the socket. A `layout` drops the
pending frame: a frame laid out for the map before it must not follow it, and
the next frame carries the whole state.

Beside each frame the pump sends each per-frame message (the `power`
reading among them) whose text has changed since this client last got it,
as the preview does (`pewpew.sinks.preview.changed_texts`).
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
        self._control: deque[dict | str] = deque()
        self._frame: FramePayload | None = None
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

    def control(self, message: dict | str) -> None:
        self._post(self._put_control, message)

    def layout(self, message: dict | str) -> None:
        self._post(self._put_control, message, True)

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

    def _put_control(self, message: dict | str, new_map: bool = False) -> None:
        if len(self._control) >= MAX_CONTROL_BACKLOG:
            self.overflow = True
        else:
            self._control.append(message)
            if new_map:
                self._frame = None  # packed for the old map
        self._event.set()

    def _put_close(self, message: dict) -> None:
        self._control.append(message)
        self._closing = True
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
                message = self._control.popleft()
                await ws.send_text(message if isinstance(message, str) else json.dumps(message))
            if self._closing:
                return
            payload, self._frame = self._frame, None
            if payload is None:
                continue
            await ws.send_bytes(payload.data)
            for text in changed_texts(payload.texts, last):
                await ws.send_text(text)
