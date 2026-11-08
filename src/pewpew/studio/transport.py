"""The asyncio side of a Gallery session: a one-slot frame mailbox and the sender.

The session thread posts through `loop.call_soon_threadsafe`. Frames and power
readings keep only the newest value, so a slow client loses frames and never
queues them. Discrete messages (hello, ack, exported, refused) keep their
order. Each is serialized on the thread that sends it, and their queue is
bounded in messages (`MAX_CONTROL_BACKLOG`) and in bytes (`max_bytes`):
overflow stops the pump at once, even in a send that a client that does not
read holds up, and the socket closes. A message over `max_bytes` (a large
rig's hello) is queued only when nothing else is.

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
# Queued discrete messages, in bytes of text. Over a hello of the largest rig
# (`Limits.max_pixels`) and an export of the largest book (`Limits.max_body_bytes`).
MAX_CONTROL_BYTES = 1024 * 1024


class Outbox:
    """Implements `SessionSink`. Its methods are safe from any thread."""

    def __init__(self, loop: asyncio.AbstractEventLoop, max_bytes: int = MAX_CONTROL_BYTES) -> None:
        self._loop = loop
        self._max_bytes = max_bytes
        self._event = asyncio.Event()
        self._control: deque[tuple[str, bool]] = deque()  # (text, whether it is an `exported`)
        self._frame: FramePayload | None = None
        self._dead = False
        self._closing = False
        self._sender: asyncio.Task | None = None
        self.overflow = False
        self.queued = 0  # bytes of text queued, the one being sent among them
        self.exports = 0  # `exported` messages queued or being sent

    def _post(self, fn, *args) -> None:
        try:
            self._loop.call_soon_threadsafe(fn, *args)
        except RuntimeError:  # the event loop is closed: the server is going down
            pass

    # -- SessionSink (session thread) ----------------------------------------

    def frame(self, payload: FramePayload) -> None:
        self._post(self._put_frame, payload)

    def control(self, message: dict | str) -> None:
        text = message if isinstance(message, str) else json.dumps(message)
        self._post(self._put_control, text, isinstance(message, dict) and message.get("type") == "exported")

    def closed(self) -> None:
        self._post(self._put_dead)

    # -- the app (any thread) ----------------------------------------------------

    def close_with(self, message: dict) -> None:
        """Send `message` after the queued ones, then end `pump`."""
        self._post(self._put_close, json.dumps(message))

    # -- event loop ------------------------------------------------------------

    def _put_frame(self, payload: FramePayload) -> None:
        self._frame = payload
        self._event.set()

    def _put_control(self, text: str, exported: bool) -> None:
        if self.overflow:
            return
        if len(self._control) >= MAX_CONTROL_BACKLOG or (self._control and self.queued + len(text) > self._max_bytes):
            self.overflow = True
            self._control.clear()
            self.queued = 0
            if self._sender is not None:
                self._sender.cancel()  # a send the client does not read may never return
        else:
            self._control.append((text, exported))
            self.queued += len(text)
            self.exports += exported
        self._event.set()

    def _put_close(self, text: str) -> None:
        self._control.append((text, False))
        self.queued += len(text)
        self._closing = True
        self._event.set()

    def _put_dead(self) -> None:
        self._dead = True
        self._event.set()

    async def pump(self, ws: WebSocket) -> None:
        """Send until the session dies, the backlog overflows or `close_with`
        is called. Each per-frame message goes out only on a change, as in
        the preview."""
        self._sender = asyncio.current_task()
        last: dict[str, str | None] = {}
        while not self.overflow:
            await self._event.wait()
            self._event.clear()
            if self.overflow or self._dead:
                return
            while self._control:
                text, exported = self._control[0]
                await ws.send_text(text)
                self._control.popleft()
                self.queued -= len(text)
                self.exports -= exported
            if self._closing:
                return
            payload, self._frame = self._frame, None
            if payload is None:
                continue
            await ws.send_bytes(payload.data)
            for text in changed_texts(payload.texts, last):
                await ws.send_text(text)
