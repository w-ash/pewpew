"""Abuse limits for a public, unauthenticated site.

Every refusal names the limit and never a path (the trust model in
`pewpew.sinks.preview`).
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pewpew.rig.models import MAX_FIXTURES

MAX_BODY_BYTES = 256 * 1024  # HTTP request bodies and inbound websocket messages
MAX_PIXELS = 16_384  # above 200 of the largest catalog fixture (64 px)
MAX_SOCKETS_PER_IP = 3
MAX_SESSIONS = 20
SAVES_PER_MINUTE = 10
COMPILES_PER_MINUTE = 60
COMPILE_BURST = 10
MAX_CONCURRENT_COMPILES = 2
COMPILE_WAIT_S = 5.0
MAX_TRACKED_ADDRESSES = 10_000


@dataclass(frozen=True)
class Limits:
    max_body_bytes: int = MAX_BODY_BYTES
    max_fixtures: int = MAX_FIXTURES
    max_pixels: int = MAX_PIXELS
    max_sockets_per_ip: int = MAX_SOCKETS_PER_IP
    max_sessions: int = MAX_SESSIONS
    saves_per_minute: int = SAVES_PER_MINUTE
    compiles_per_minute: int = COMPILES_PER_MINUTE
    compile_burst: int = COMPILE_BURST
    max_concurrent_compiles: int = MAX_CONCURRENT_COMPILES
    compile_wait_s: float = COMPILE_WAIT_S


def client_ip(headers: Mapping[str, str], peer: str | None) -> str:
    """The caller's address: `Fly-Client-IP`, else the peer address.

    Fly Proxy sets the header to the client address
    (https://docs.fly.io/networking/request-headers). Fly's page does not say
    it overwrites a client-supplied value, so off Fly the header is spoofable;
    the limits are a cost guard, not authentication.
    """
    value = headers.get("fly-client-ip", "").strip()
    return (value or peer or "unknown")[:64]


def address_key(ip: str) -> str:
    """The key that per-address limits count under.

    An IPv6 address counts as its /64: interface identifiers are 64 bits
    (https://www.rfc-editor.org/rfc/rfc4291#section-2.5.1), so one host can
    hold a whole /64. An IPv4-mapped address counts as its IPv4 address.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        return str(ipaddress.IPv6Network((addr, 64), strict=False))
    return str(addr)


def declared_fixtures(arrangement: Mapping[str, Any], cap: int) -> int:
    """The fixtures an arrangement declares: its `fixtures` plus each group's
    `count`, or the product of its `counts`.

    Reads the raw JSON and expands nothing. Stops counting once the total
    passes `cap`, so the result is exact up to `cap` and above it otherwise.
    """
    fixtures = arrangement.get("fixtures")
    total = len(fixtures) if isinstance(fixtures, list) else 0
    groups = arrangement.get("groups")
    for group in groups if isinstance(groups, list) else ():
        if total > cap:
            break
        if isinstance(group, dict):
            total += _group_size(group, cap)
    return total


def _group_size(group: Mapping[str, Any], cap: int) -> int:
    counts = group.get("counts", [group.get("count")])
    if not isinstance(counts, list):
        return 0
    numbers = [c for c in counts if isinstance(c, int) and not isinstance(c, bool)]
    size = 1 if numbers else 0
    for c in numbers:
        size *= max(c, 0)
        if size > cap:
            break
    return size


@dataclass(eq=False)
class Ticket:
    """One admitted socket. `Admission.release` frees it once."""

    key: str
    released: bool = False


class Admission:
    """Counts open sockets per address and overall; thread-safe."""

    def __init__(self, limits: Limits) -> None:
        self._limits = limits
        self._lock = threading.Lock()
        self._per_key: dict[str, int] = {}
        self._total = 0

    def acquire(self, key: str, evict: Callable[[], Ticket | None] = lambda: None) -> Ticket | str:
        """Take a slot. Returns the ticket, else the refusal reason.

        When the server is full, `evict` may free a slot: it returns the
        ticket of a session it closed, or None. It runs under this object's
        lock, so it must not call back into it.
        """
        with self._lock:
            if self._per_key.get(key, 0) >= self._limits.max_sockets_per_ip:
                return f"limit of {self._limits.max_sockets_per_ip} open sessions per address"
            if self._total >= self._limits.max_sessions:
                victim = evict()
                if victim is None:
                    return f"the server is at its limit of {self._limits.max_sessions} live sessions; try again shortly"
                self._release(victim)
            self._per_key[key] = self._per_key.get(key, 0) + 1
            self._total += 1
            return Ticket(key)

    def release(self, ticket: Ticket) -> None:
        with self._lock:
            self._release(ticket)

    def _release(self, ticket: Ticket) -> None:
        if ticket.released:
            return
        ticket.released = True
        self._total -= 1
        left = self._per_key[ticket.key] - 1
        if left:
            self._per_key[ticket.key] = left
        else:
            del self._per_key[ticket.key]

    def __len__(self) -> int:
        with self._lock:
            return self._total


class RateLimiter:
    """A token bucket per key: `burst` requests at once, refilled at
    `per_minute`; thread-safe.

    Keys are kept in last-use order. A key unused for long enough to refill
    is the same as a missing key, so those leave from the old end, in O(1)
    amortized time per call. The table never holds more than `max_keys`.
    """

    def __init__(
        self,
        per_minute: float,
        burst: int | None = None,
        *,
        now: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_TRACKED_ADDRESSES,
    ) -> None:
        self._rate = per_minute / 60.0
        self._burst = float(per_minute if burst is None else burst)
        self._refill_s = self._burst / self._rate
        self._now = now
        self._max_keys = max_keys
        self._lock = threading.Lock()
        self._keys: OrderedDict[str, tuple[float, float]] = OrderedDict()  # key -> (tokens, last use)

    def allow(self, key: str) -> float | None:
        """Take one token. Returns None if allowed, else seconds until one is free."""
        t = self._now()
        with self._lock:
            tokens, last = self._keys.pop(key, (self._burst, t))
            tokens = min(self._burst, tokens + (t - last) * self._rate)
            while self._keys:
                oldest = next(iter(self._keys))
                if len(self._keys) < self._max_keys and t - self._keys[oldest][1] < self._refill_s:
                    break
                del self._keys[oldest]
            if tokens >= 1.0:
                self._keys[key] = (tokens - 1.0, t)
                return None
            self._keys[key] = (tokens, t)
            return (1.0 - tokens) / self._rate

    def __len__(self) -> int:
        with self._lock:
            return len(self._keys)


class BodyLimit:
    """ASGI middleware: refuse HTTP bodies over `limit` bytes with 413.

    Checks `Content-Length` up front and counts streamed bytes for chunked
    bodies, which carry no length. A chunked body that crosses the limit gets
    the 413 from here, the app reads a disconnect, and its own reply is
    dropped.
    """

    def __init__(self, app, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.limit:
            await self._refuse(send)
            return
        seen = 0
        started = False
        refused = False

        async def counted():
            nonlocal seen, refused
            if refused:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.limit:
                    if not started:
                        await self._refuse(send)
                    refused = True
                    return {"type": "http.disconnect"}
            return message

        async def tracked(message):
            nonlocal started
            if refused:
                return
            started = started or message["type"] == "http.response.start"
            await send(message)

        await self.app(scope, counted, tracked)

    async def _refuse(self, send) -> None:
        body = b'{"detail":"request body over the limit of %d bytes"}' % self.limit
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body})
