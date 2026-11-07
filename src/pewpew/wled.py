"""Talking to a WLED board over HTTP, and finding boards on the network.

`fetch_info` reads one board's `/json/info` within a size and time bound;
`replies` asks every address of a subnet for it (`scan_subnet` names the
subnet), and `sweep` keeps the WLED boards that answer, with `scan_lines`
their rows for a terminal. A
pewpew capture node answers `/json/info` too, with WLED's `ver` and `mac`;
its `brand` is `NODE_BRAND` where a board's is "WLED" (`is_node`), so a
sweep leaves it out and `audio list` lists it (pewpew.audio.net). `resolve_name`
looks an mDNS name up and `sender_address` gives this laptop's address on
the route to a board. `failure` puts a failed request in a few words, and
`no_route` spots the macOS Local Network block (`PRIVACY`), so every
command words it the same way. Reads only: tier 0 (CLAUDE.md T-7).
"""

from __future__ import annotations

import errno
import ipaddress
import socket
import threading
import time
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pewpew.errors import scrub
from pewpew.jsonfile import loads
from pewpew.sinks.ddp import DDP_PORT

TIMEOUT_S = 2.0  # per request
MAX_INFO_BYTES = 64 * 1024  # a WLED /json/info reply is a few KB
SCAN_TIMEOUT_S = 0.8
SCAN_WORKERS = 32
PRIVACY = "System Settings → Privacy & Security → Local Network"
NODE_BRAND = "pewpew"  # a capture node's `brand` (firmware/audio-node/main/wire.h)


def fetch_info(host: str, timeout: float = TIMEOUT_S) -> dict:
    """GET `http://host/json/info` and parse it. The whole request ends
    within about twice `timeout` and reads at most `MAX_INFO_BYTES`, so a
    device that answers slowly or without end cannot hold a scan worker."""
    deadline = time.monotonic() + 2 * timeout
    with urllib.request.urlopen(f"http://{host}/json/info", timeout=timeout) as reply:
        body = bytearray()
        while chunk := reply.read1(16 * 1024):
            body += chunk
            if len(body) > MAX_INFO_BYTES:
                raise ValueError("the reply is too large for /json/info")
            if time.monotonic() > deadline:
                raise TimeoutError("the reply took too long")
        return loads(body)


def resolve_name(name: str) -> str:
    """The IPv4 address of `name`. On macOS the system resolver asks
    mDNSResponder for a `.local` name. Blocks; raises OSError."""
    return socket.gethostbyname(name)


def failure(exc: BaseException) -> str:
    """A failed poll in a few words; never a path or a traceback."""
    reason = getattr(exc, "reason", exc)  # urllib wraps socket errors
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timed out"
    if isinstance(reason, OSError) and reason.strerror:
        return scrub(reason.strerror)
    return scrub(f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__)


def no_route(exc: BaseException) -> bool:
    """Whether `exc` is "No route to host". On macOS, while the board's own
    page opens in a browser, that is the Local Network privacy setting
    (`PRIVACY`) blocking this terminal app."""
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, OSError) and reason.errno == errno.EHOSTUNREACH


def local_subnet(
    towards: str | None = None, sender: Callable[[str, int], str | None] | None = None
) -> tuple[str, ipaddress.IPv4Network] | None:
    """This laptop's address towards `towards` (default: the default route)
    and its /24; None without an IPv4 address. `sender` defaults to
    `sender_address`."""
    mine = (sender or sender_address)(towards or "192.0.2.1", DDP_PORT)  # TEST-NET-1
    if mine is None:
        return None
    return mine, ipaddress.IPv4Network(f"{mine}/24", strict=False)


def sender_address(host: str, port: int = DDP_PORT) -> str | None:
    """This laptop's address on the route to `host` (a UDP connect sends
    nothing), to compare with a board's `lip`; None without a route."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((host, port))
            return s.getsockname()[0]
    except OSError:
        return None


def scan_subnet(subnet: ipaddress.IPv4Network | None) -> tuple[ipaddress.IPv4Network, str | None] | None:
    """The subnet a scan asks, `subnet` or else this laptop's /24, and this
    laptop's address, which it skips; None when neither is known."""
    local = local_subnet()
    mine = local[0] if local else None
    if subnet is not None:
        return subnet, mine
    return None if local is None else (local[1], mine)


def replies(
    subnet: ipaddress.IPv4Network,
    mine: str | None,
    fetch: Callable[[str, float], dict] = fetch_info,
    timeout: float = SCAN_TIMEOUT_S,
    workers: int = SCAN_WORKERS,
    stop: threading.Event | None = None,
) -> list[tuple[str, dict]]:
    """Every `/json/info` reply in `subnet` that has a string `ver` and
    `mac`, as WLED's has, by address, in address order. `mine` is skipped.
    Once `stop` is set, no address is asked: the interpreter's exit waits
    only for the requests in flight."""
    hosts = [str(h) for h in subnet.hosts() if str(h) != mine]

    def ask(host: str) -> tuple[str, dict] | None:
        if stop is not None and stop.is_set():
            return None
        try:
            info = fetch(host, timeout)
        except Exception:  # noqa: BLE001  no answer: not a board
            return None
        if not isinstance(info, dict) or not isinstance(info.get("ver"), str) or not isinstance(info.get("mac"), str):
            return None  # answered, but not WLED
        return host, info

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pewpew-scan") as pool:
        answers = list(pool.map(ask, hosts))
    return [a for a in answers if a is not None]


def is_node(info: dict) -> bool:
    """Whether a `/json/info` reply is a pewpew capture node's, not a board's."""
    return info.get("brand") == NODE_BRAND


def board_row(address: str, info: dict) -> dict:
    """A board's row: `{"address", "mac", "name", "ver", "live", "lm", "lip"}`."""
    text = {k: v if isinstance(v := info.get(k), str) else None for k in ("name", "lm", "lip")}
    live = info.get("live")
    return {"address": address, "mac": info["mac"], "name": text["name"], "ver": info["ver"],
            "live": live if isinstance(live, bool) else None, "lm": text["lm"], "lip": text["lip"]}


def sweep(
    subnet: ipaddress.IPv4Network,
    mine: str | None,
    fetch: Callable[[str, float], dict] = fetch_info,
    timeout: float = SCAN_TIMEOUT_S,
    workers: int = SCAN_WORKERS,
    stop: threading.Event | None = None,
) -> list[dict]:
    """Every WLED board in `subnet` that answers `/json/info`, by address
    (`board_row`); a capture node is no board, so it is left out
    (`replies` takes the other arguments)."""
    return [board_row(address, info) for address, info in replies(subnet, mine, fetch, timeout, workers, stop)
            if not is_node(info)]


def scan_lines(found: Iterable[dict]) -> list[str]:
    """One line per board `sweep` found, for `python -m pewpew boards scan`."""
    lines = []
    for item in found:
        live = f"live {item['lm'] or '?'} from {item['lip'] or '?'}" if item["live"] else "not live"
        lines.append(
            f"{item['address']:<15}  {item['name'] or '?':<16}  MAC {format_mac(item['mac'])}  "
            f"WLED {item['ver']}  {live}"
        )
    return lines


def format_mac(mac: Any) -> str:
    """`020000000001` as `02:00:00:00:00:01`."""
    if isinstance(mac, str) and len(mac) == 12:
        return ":".join(mac[i : i + 2] for i in range(0, 12, 2))
    return str(mac)
