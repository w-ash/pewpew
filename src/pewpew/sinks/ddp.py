"""DDP 8-bit sink: one frame to several stock WLED boards over UDP.

Each `Board` takes a contiguous pixel range of the map. Per frame the sink
quantizes once, slices each board's range, and sends that slice as DDP
packets (3waylabs DDP spec; WLED v16.0.1 `wled00/e131.cpp`):

- 10-byte header, big-endian: flags, sequence, data type, destination ID,
  32-bit byte offset, 16-bit data length. No timecode: WLED skips it.
- flags `0x40` (version 1), plus `0x01` (PUSH) on each board's last packet
  only, so a board fills its buffer and shows the whole frame at once
  (ADR-003 fill-then-latch). Every board gets its own PUSH; there is no
  broadcast latch yet.
- data type `0x0B`: RGB, 8 bits per channel. WLED reads 4 bytes per pixel
  only when the type bits are `011` (RGBW), else 3. RGB is enough on RGBW
  bars: WLED derives W from each output's auto-white mode.
- destination ID 1, the default output device.
- at most 1440 data bytes (480 px) per packet, WLED's own
  `DDP_CHANNELS_PER_PACKET` and the spec's figure for one Ethernet frame.
- sequence 1-15 per board, one step per packet, continuous across frames;
  0 means "unused" to a receiver, so it is never sent. It starts at 1 on
  every start and is not kept across restarts, so WLED's "skip
  out-of-sequence" option (`if.live.dmx.seqskip`, off by default,
  `wled00/wled.h:488`) must stay off: with it on, a board that still holds
  the old run's last sequence number drops packets of the new run's first
  frame (`wled00/e131.cpp:43-52`).

Colour: linear light quantized once to u8 (`to_linear_u8`), no gamma. LED
duty is linear in light (ADR-001), and WLED applies no colour gamma to
realtime data by default (`arlsDisableGammaCorrection`, `wled00/wled.h`).
WLED still scales realtime data by its own brightness, so each board is
pinned at 255 with "Force max brightness" (architecture §4b).

Pacing: `RateGate` at `max_fps` (default 40). WLED shows a streamed frame
only when more than 15 ms have passed since it last showed one, so a steady
rate below about 66 fps is what a board can display.

Packet bytes depend only on the frames sent and their order: no clock
shapes them, and the socket is injectable so tests read packets without a
network.

Addressing. A board's host is an IPv4 address literal or an mDNS name such
as `pewpew-1.local`, the name WLED advertises (`board_host`). The sink
never looks a name up: a name that no resolver answers blocks for seconds,
and the sink runs beside the render loop. It keeps one address table,
keyed by (host, port), that outlives relayouts. An IPv4 board's address is
its host. A named board has no address until `set_address` gives it one
(`pewpew.health.HealthMonitor` looks names up on its own thread), and until
then `send` skips it.

Relayout: a room map reload hands the sink new board ranges with
`prepare` (validate, changing nothing) then `commit` (one attribute
store), so a frame mid-send finishes on the layout it began with. A board
whose host and port are unchanged keeps its address.
"""

from __future__ import annotations

import ipaddress
import itertools
import logging
import math
import re
import socket
import struct
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from pewpew.sinks.sink import RateGate, to_linear_u8

logger = logging.getLogger(__name__)

DDP_PORT = 4048
HEADER_LEN = 10
MAX_DATA = 1440  # bytes per packet: 480 RGB pixels
BYTES_PER_PX = 3
FLAG_VER1 = 0x40
FLAG_PUSH = 0x01
TYPE_RGB8 = 0x0B  # 00 001 011: standard, RGB, 8 bits per element
ID_DISPLAY = 1
SEQ_MAX = 15

_HEADER = struct.Struct(">BBBBIH")


class DatagramSocket(Protocol):
    """The part of a UDP socket the sink uses; tests pass a recorder."""

    def sendto(self, data: bytes, address: tuple[str, int], /) -> int: ...

    def close(self) -> None: ...


def _udp_socket() -> DatagramSocket:
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


@dataclass(frozen=True)
class Board:
    """One receiver: `count` pixels of the map from `start`, at host:port."""

    host: str
    start: int
    count: int
    port: int = DDP_PORT

    @property
    def stop(self) -> int:
        return self.start + self.count

    @property
    def spec(self) -> str:
        """`HOST:PORT=START+COUNT`, the form `parse_board` reads."""
        return f"{self.host}:{self.port}={self.start}+{self.count}"

    @property
    def packets_per_frame(self) -> int:
        return math.ceil(self.count * BYTES_PER_PX / MAX_DATA)

    @property
    def bytes_per_frame(self) -> int:
        """UDP payload per frame: pixel data plus one header per packet."""
        return self.count * BYTES_PER_PX + HEADER_LEN * self.packets_per_frame

    def describe(self, fps: float) -> str:
        """One plan line: address, range, packets per frame, payload rate."""
        return (
            f"ddp {self.host}:{self.port}  pixels {self.start}-{self.stop - 1} ({self.count})  "
            f"{self.packets_per_frame} packets/frame  "
            f"{round(self.bytes_per_frame * fps):,} B/s at {fps:g} fps"
        )


def is_ipv4(host: str) -> bool:
    """Whether `host` is an IPv4 address literal, such as 10.0.0.11."""
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return False
    return True


# One DNS label, then `.local`: the form of a WLED mDNS name (`pewpew-1`
# becomes `pewpew-1.local`).
_MDNS_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local", re.IGNORECASE)


def board_host(host: str) -> bool:
    """Whether `host` can address a board: an IPv4 literal or an mDNS name."""
    return is_ipv4(host) or _MDNS_NAME.fullmatch(host) is not None


HOST_RULE = "an IPv4 address or an mDNS name such as pewpew-1.local"


def parse_target(target: str) -> tuple[str, int]:
    """`HOST[:PORT]` -> (host, port), HOST per `board_host` and PORT
    `DDP_PORT` when left out. Raises ValueError naming the bad part."""
    host, colon, port = target.partition(":")
    if ":" in port:
        raise ValueError(f"{target!r} has more than one ':'; HOST is {HOST_RULE}")
    if not host:
        raise ValueError(f"give HOST or HOST:PORT, HOST {HOST_RULE}")
    if not board_host(host):
        raise ValueError(f"{host!r} is not {HOST_RULE}")
    if not colon:
        return host, DDP_PORT
    number = int(port) if port.isascii() and port.isdigit() and len(port) <= 5 else 0
    if not 0 < number < 65536:
        raise ValueError(f"port {port!r} is not 1-65535")
    return host, number


def parse_board(spec: str) -> Board:
    """`HOST[:PORT]=START+COUNT` -> Board, the target per `parse_target`.
    Raises ValueError with a one-line reason a front end prints as is."""
    target, _, span = spec.partition("=")
    first, _, count = span.partition("+")
    try:
        start, n = int(first), int(count)
    except ValueError:
        raise ValueError(f"bad DDP target {spec!r}; expected HOST[:PORT]=START+COUNT") from None
    if start < 0 or n < 1:
        raise ValueError(f"bad DDP target {spec!r}; START >= 0, COUNT >= 1")
    try:
        host, port = parse_target(target)
    except ValueError as exc:
        raise ValueError(f"bad DDP target {spec!r}; {exc}") from None
    return Board(host, start, n, port)


def check_boards(boards: Sequence[Board], n_pixels: int) -> None:
    """Every range inside the map and no two overlapping, else ValueError."""
    for b in boards:
        if b.stop > n_pixels:
            raise ValueError(
                f"DDP target {b.host} pixels {b.start}-{b.stop - 1} do not fit the "
                f"{n_pixels}-pixel map"
            )
    ordered = sorted(boards, key=lambda b: b.start)
    for a, b in itertools.pairwise(ordered):
        if b.start < a.stop:
            raise ValueError(
                f"DDP target {a.host} pixels {a.start}-{a.stop - 1} overlap "
                f"{b.host} pixels {b.start}-{b.stop - 1}"
            )


def board_packets(data: bytes, seq: int) -> tuple[list[bytes], int]:
    """One board's frame as DDP packets, and the sequence number to use next.

    `data` is the board's RGB bytes; offsets count bytes from the board's
    first pixel. PUSH is set on the last packet only.
    """
    packets = []
    for offset in range(0, len(data), MAX_DATA):
        chunk = data[offset : offset + MAX_DATA]
        last = offset + MAX_DATA >= len(data)
        flags = FLAG_VER1 | (FLAG_PUSH if last else 0)
        packets.append(_HEADER.pack(flags, seq, TYPE_RGB8, ID_DISPLAY, offset, len(chunk)) + chunk)
        seq = seq % SEQ_MAX + 1  # 1..15, then 1 again
    return packets, seq


Address = tuple[str, int]


@dataclass(frozen=True)
class Layout:
    """The boards one frame is cut for, swapped whole by `DdpSink.commit`.

    `seq` and `errors` are per board and mutated only by the sending
    thread; a new layout starts them afresh. `errors` counts the frames a
    socket error stopped. `previous_n` is the map size of the layout this
    one replaced: a frame of that size reaching `send` after the swap was
    rendered before it and is dropped.
    """

    boards: tuple[Board, ...]
    n_pixels: int
    seq: list[int]
    errors: list[int]
    previous_n: int | None = None


class DdpSink:
    """Send each frame to every board as DDP, paced by `RateGate`."""

    def __init__(
        self,
        boards: Sequence[Board],
        n_pixels: int,
        *,
        max_fps: float = 40.0,
        open_socket: Callable[[], DatagramSocket] | None = None,
        now: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.max_fps = float(max_fps)
        self._gate = RateGate(max_fps, now=now, sleep=sleep)
        self._open_socket = open_socket
        self._sock: DatagramSocket | None = None
        # (host, port) -> socket address, or None while a name is unresolved.
        # Written by `_learn` (new keys only) and `set_address`; one dict
        # item store each, read once per board per frame.
        self._addresses: dict[Address, Address | None] = {}
        self._layout = self.prepare(boards, n_pixels)
        self._learn(self._layout)
        self.frames_sent = 0

    @property
    def boards(self) -> tuple[Board, ...]:
        return self._layout.boards

    @property
    def n_pixels(self) -> int:
        return self._layout.n_pixels

    @property
    def errors(self) -> list[int]:
        """Contained socket errors per board, for the current layout."""
        return self._layout.errors

    def plan(self) -> list[str]:
        """The per-board plan, one line each, as `--dry-run` prints it."""
        return [b.describe(self.max_fps) for b in self.boards]

    def address(self, host: str, port: int = DDP_PORT) -> Address | None:
        """Where frames for board (host, port) go, or None while unresolved."""
        return self._addresses.get((host, port))

    def set_address(self, host: str, port: int, address: Address | None) -> None:
        """Send later frames for board (host, port) to `address`; None stops
        them until an address is set again. Any thread."""
        self._addresses[(host, port)] = address

    def prepare(self, boards: Sequence[Board], n_pixels: int) -> Layout:
        """Check `boards` against an `n_pixels` map. Looks up no name and
        changes nothing; raises ValueError."""
        if not boards:
            raise ValueError("DdpSink needs at least one board")
        check_boards(boards, n_pixels)
        previous = getattr(self, "_layout", None)
        n = len(boards)
        return Layout(tuple(boards), n_pixels, [1] * n, [0] * n, None if previous is None else previous.n_pixels)

    def commit(self, layout: Layout) -> None:
        """Send every later frame to `layout`'s boards. One attribute store,
        so a frame mid-send finishes on the layout it started with."""
        self._learn(layout)
        self._layout = layout

    def _learn(self, layout: Layout) -> None:
        """Add the table entries `layout` needs: an IPv4 board's own address,
        None for a new name. A known board keeps its address."""
        for b in layout.boards:
            key = (b.host, b.port)
            if key not in self._addresses:
                self._addresses[key] = key if is_ipv4(b.host) else None

    def start(self) -> None:
        self._sock = (self._open_socket or _udp_socket)()

    def stop(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()

    def send(self, t: float, frame: np.ndarray) -> None:
        self._gate.wait()
        sock = self._sock
        if sock is None:
            raise RuntimeError("DdpSink.send() before start()")
        layout = self._layout
        if len(frame) != layout.n_pixels:
            if len(frame) == layout.previous_n:
                return  # rendered before a map reload; the next frame fits
            raise ValueError(f"frame has {len(frame)} pixels; the boards were laid out for {layout.n_pixels}")
        rgb = to_linear_u8(frame)
        for i, board in enumerate(layout.boards):
            packets, layout.seq[i] = board_packets(rgb[board.start : board.stop].tobytes(), layout.seq[i])
            addr = self._addresses.get((board.host, board.port))
            if addr is None:
                continue  # a name not yet looked up; the monitor reports it
            # Contained per board: one unreachable board must not starve the
            # others of this frame, which raising out of `send` would do.
            try:
                for packet in packets:
                    sock.sendto(packet, addr)
            except OSError as exc:
                layout.errors[i] += 1
                if layout.errors[i] == 1:
                    logger.warning("ddp send to %s failed: %s (logged once per board)", board.host, exc)
        self.frames_sent += 1
