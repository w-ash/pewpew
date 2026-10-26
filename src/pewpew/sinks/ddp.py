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
  0 means "unused" to a receiver, so it is never sent.

Colour: linear light quantized once to u8 (`to_linear_u8`), no gamma. LED
duty is linear in light (ADR-001), and WLED applies no colour gamma to
realtime data by default (`arlsDisableGammaCorrection`, `wled00/wled.h`).
WLED still scales realtime data by its own brightness, so each board is
pinned at 255 with "Force max brightness" (architecture §4b).

Pacing: `RateGate` at `max_fps` (default 40). WLED shows a streamed frame
only when more than 15 ms have passed since the last show, so a steady
rate below about 66 fps is what a board can display.

Packet bytes depend only on the frames sent and their order: no clock
shapes them, and the socket is injectable so tests read packets without a
network. Hosts resolve once in `start()`; give boards fixed addresses.
"""

from __future__ import annotations

import logging
import math
import socket
import struct
import time
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

import numpy as np

from pewpew.sinks.base import RateGate, to_linear_u8

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


def parse_board(spec: str) -> Board:
    """`HOST[:PORT]=START+COUNT` -> Board. Raises ValueError with a one-line
    reason a front end prints as is."""
    target, sep, span = spec.partition("=")
    if target.count(":") > 1:
        raise ValueError(f"bad DDP target {spec!r}; the DDP sink is IPv4-only, give an IPv4 address or hostname")
    first, plus, count = span.partition("+")
    host, colon, port = target.rpartition(":") if ":" in target else (target, "", "")
    try:
        if not (sep and plus and host):
            raise ValueError
        board = Board(host, int(first), int(count), int(port) if colon else DDP_PORT)
    except ValueError:
        raise ValueError(
            f"bad DDP target {spec!r}; expected HOST=START+COUNT or HOST:PORT=START+COUNT"
        ) from None
    if board.start < 0 or board.count < 1 or not 0 < board.port < 65536:
        raise ValueError(f"bad DDP target {spec!r}; START >= 0, COUNT >= 1, PORT 1-65535")
    return board


def check_boards(boards: Sequence[Board], n_pixels: int) -> None:
    """Every range inside the map and no two overlapping, else ValueError."""
    for b in boards:
        if b.stop > n_pixels:
            raise ValueError(
                f"DDP target {b.host} pixels {b.start}-{b.stop - 1} do not fit the "
                f"{n_pixels}-pixel map"
            )
    ordered = sorted(boards, key=lambda b: b.start)
    for a, b in zip(ordered, ordered[1:]):
        if b.start < a.stop:
            raise ValueError(
                f"DDP target {a.host} pixels {a.start}-{a.stop - 1} overlap "
                f"{b.host} pixels {b.start}-{b.stop - 1}"
            )


def next_seq(seq: int) -> int:
    """The sequence number after `seq`: 1..15, then 1 again."""
    return seq % SEQ_MAX + 1


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
        seq = next_seq(seq)
    return packets, seq


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
        if not boards:
            raise ValueError("DdpSink needs at least one board")
        check_boards(boards, n_pixels)
        self.boards = tuple(boards)
        self.n_pixels = n_pixels
        self.max_fps = float(max_fps)
        self._gate = RateGate(max_fps, now=now, sleep=sleep)
        self._open_socket = open_socket
        self._sock: DatagramSocket | None = None
        self._addrs: list[tuple[str, int]] = []
        self._seq = [1] * len(self.boards)
        self.frames_sent = 0
        self.errors = [0] * len(self.boards)  # contained socket errors per board

    def plan(self) -> list[str]:
        """The per-board plan, one line each, as `--dry-run` prints it."""
        return [b.describe(self.max_fps) for b in self.boards]

    def start(self) -> None:
        addrs = []
        for b in self.boards:
            try:
                addrs.append((socket.gethostbyname(b.host), b.port))
            except OSError as exc:
                raise OSError(f"cannot resolve DDP host {b.host!r}: {exc}") from None
        self._addrs = addrs
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
        if len(frame) != self.n_pixels:
            raise ValueError(f"frame has {len(frame)} pixels; the boards were laid out for {self.n_pixels}")
        rgb = to_linear_u8(frame)
        for i, board in enumerate(self.boards):
            packets, self._seq[i] = board_packets(rgb[board.start : board.stop].tobytes(), self._seq[i])
            # Contained per board: one unreachable board must not starve the
            # others of this frame, which raising out of `send` would do.
            try:
                for packet in packets:
                    sock.sendto(packet, self._addrs[i])
            except OSError as exc:
                self.errors[i] += 1
                if self.errors[i] == 1:
                    logger.warning("ddp send to %s failed: %s (logged once per board)", board.host, exc)
        self.frames_sent += 1
