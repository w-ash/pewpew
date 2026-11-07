"""The asyncio side of a session: a one-slot frame mailbox and the sender.

The session thread posts through `loop.call_soon_threadsafe`. Frames and power
readings keep only the newest value, so a slow client loses frames and never
queues them. Discrete messages (hello, bound, refused) keep their order; their
queue is bounded, and overflow closes the socket. A hello drops the pending
frame, because that frame predates it.
"""

from __future__ import annotations

import asyncio
import json
from collections import deque

from fastapi import WebSocket

from pewpew.studio.session import Echo, FramePayload

MAX_CONTROL_BACKLOG = 256


class Outbox:
    """Implements `SessionSink`. Its methods are safe from any thread."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._event = asyncio.Event()
        self._control: deque[tuple[dict, Echo | None]] = deque()
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

    def control(self, message: dict, seen: Echo | None = None) -> None:
        self._post(self._put_control, message, seen)

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

    def _put_control(self, message: dict, seen: Echo | None) -> None:
        if len(self._control) >= MAX_CONTROL_BACKLOG:
            self.overflow = True
        else:
            self._control.append((message, seen))
            if seen is not None:
                self._frame = None
        self._event.set()

    def _put_close(self, message: dict) -> None:
        self._control.append((message, None))
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
        is called. Status, declarations and values go out only on a change,
        as in the preview."""
        last_status: str | None = None
        last_params: str | None = None
        last_declare: str | None = None
        while True:
            await self._event.wait()
            self._event.clear()
            if self.overflow or self._dead:
                return
            while self._control:
                message, seen = self._control.popleft()
                await ws.send_text(json.dumps(message))
                if seen is not None:  # a hello already carries these
                    last_declare, last_params = seen.declare, seen.params
            if self._closing:
                return
            if self._power is not None:
                (watts, uncapped), self._power = self._power, None
                await ws.send_text(json.dumps({"type": "power", "watts": watts, "uncapped_watts": uncapped}))
            payload, self._frame = self._frame, None
            if payload is None:
                continue
            await ws.send_bytes(payload.data)
            if payload.status != last_status:
                last_status = payload.status
                await ws.send_text(payload.status)
            if payload.echo.declare != last_declare:
                last_declare = payload.echo.declare
                # New controls, built empty: the values follow even when unchanged.
                last_params = None
                await ws.send_text(payload.echo.declare)
            if payload.echo.params != last_params:
                last_params = payload.echo.params
                await ws.send_text(payload.echo.params)
