"""Capture nodes (firmware/audio-node): `NetSource`, an `AudioSource` over
UDP, and `TraceSource`, its deterministic twin, which replays a packet
trace over a seeded signal (ADR-009, 2026-11-06 amendment "capture
nodes"; RA-28 §6).

    --audio net:pewpew-line-1        pewpew-line-1.local, looked up again
                                     whenever the node goes quiet
    --audio net:10.0.0.42            an IPv4 address

**Receiving** (`Receiver`, the loop thread's half, the same for a live
node and a trace). Each tick drains what arrived and stamps it `t + 1/fps`,
the end of its slot, through a `SampleClock`. A boot nonce starts an
epoch: a new nonce (the node rebooted) restarts the fit and, through a
jump in the index, the analysis's grid. A live node streams only under
the nonce of the SUB this host signed, so its packets of any other nonce
are stale; a trace has no SUB, so each new nonce in it is a reboot. In an
epoch the packets go in index order, and:

- a packet whose samples were already passed is late, and dropped: a
  duplicate is one. There is no jitter buffer.
- a packet whose index maps more than `LOST_S` after its stamp is a stray
  from the future, and dropped, so one stray far-future index cannot make
  every real packet late. The map is the fit, or before the fit a line at
  the nominal rate through the last packet taken. The rule looks one way:
  packets a stalled loop drains late map before their stamps, and the
  analysis's backlog rule takes them.
- after `LOST_S` with nothing taken, a packet that would be dropped late
  or as a stray starts a new epoch instead (`Counts.followed`): so
  neither strays that keep coming nor a far-future first packet, which
  makes every real packet late, hold the input lost.
- a gap in the index is samples the network or the node's I2S driver lost
  (the node counts those into its index); the analysis fills a short one
  and holds the hops it touches (pewpew.audio.analysis). The loss share
  counts a gap only as far back as its window reaches from the packet
  that ends it.

**Subscribing** (the supervisor thread `pewpew-audio`, `step` every
`RENEW_S`). It resolves the name off the loop, reads the node's
`/json/info` (its MAC and boot nonce), finds its key (pewpew.audio.keys),
`connect()`s the socket to the node so the kernel drops anyone else's
datagrams, and sends the signed SUB every `RENEW_S`. It finds the node
again when no packet came since its last pass, or when the node refuses
with a stale nonce or another MAC; any other refusal is the reason the
input is lost until the node answers again. It subscribes only to the
node it first subscribed to, by its MAC: another node at the address is
the reason the input is lost, never a node to stream from. The socket
binds to `run --host` when that is an IPv4 address, the private router's
side.

**Tiers** (CLAUDE.md T-7; ADR-009 "capture nodes"). Subscribing is tier 1:
outside `--unattended`, `node_source` needs `--allow-host IP`, resolves the name
at launch and refuses an address the flag does not name, and the
supervisor connects only to an address it checked. The `audio-input`
audit record comes before the first SUB, and an `audio-readdress` record
before the first SUB to each new address. Reading `/json/info` is tier 0
(`find_nodes`, `audio list`).

**Lost** is no packet for `LOST_S`, or none `OPENING_S` after the loop
began; the features then keep the last tempo (pewpew.audio.features).

Privacy: the samples stay in memory, as a device's do (pewpew.audio.device),
and cross the private router only to this host.
"""

from __future__ import annotations

import ipaddress
import logging
import math
import socket
import struct
import threading
import time
from collections import deque
from collections.abc import Callable, Collection, Iterable
from dataclasses import asdict, dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path

import numpy as np

from pewpew import audit, wled
from pewpew.audio import keys
from pewpew.audio.analysis import LOST_S, restart_gap
from pewpew.audio.clock import SampleClock
from pewpew.audio.source import Block
from pewpew.audio.wire import (
    CLIP,
    DENIALS,
    HEADER,
    OVERFLOW,
    PORT,
    PRODUCT,
    RATE,
    RENEW_S,
    Denial,
    Packet,
    decode,
    header,
    pcm,
    refused,
    subscription,
)
from pewpew.errors import describe_exception
from pewpew.jsonfile import is_number
from pewpew.sinks.ddp import board_host, is_ipv4

logger = logging.getLogger(__name__)

PREFIX = "net:"
OPENING_S = 5.0  # no packet this long after the loop began reads as lost [inf]
INFO_S = 6.0  # a streaming node's /json/info is read this often, as the boards' are (pewpew.health)
POLL_TIMEOUT_S = 0.5  # that read's timeout: the whole read ends well inside the node's HOLD_S
LOSS_S = 10.0  # the window of the loss share [inf]
MAX_DATAGRAMS = 400  # one tick drains at most this many: 4 s of packets
RECEIVE_BUFFER = 1 << 20  # the socket's buffer: about 10 s of packets, through a stalled loop
PRIVACY = ("samples stay in memory, under a second of them, and never go to disk; a capture node's audio "
           "crosses the private router only to this host")
ALLOW = ("outside --unattended, a capture node is a bench node: name its IPv4 address with --allow-host IP "
         "(`python -m pewpew audio list` shows it)")
REFIND = (Denial.STALE, Denial.OTHER_NODE)  # refusals that a fresh /json/info answers


def node_host(name: str) -> str:
    """The host `net:NAME` names: an IPv4 address, or NAME's mDNS name
    (`pewpew-line-1` is `pewpew-line-1.local`). Raises ValueError for
    anything else."""
    text = name.strip()
    if not text:
        raise ValueError(f"{PREFIX} needs a node: its name, such as {PREFIX}pewpew-line-1, or its IPv4 address")
    host = text if is_ipv4(text) or text.lower().endswith(".local") else f"{text}.local"
    if not board_host(host):
        raise ValueError(f"{text!r} is not a node's name (letters, digits and hyphens) or an IPv4 address")
    return host


def node_source(
    name: str, *, fps: float, unattended: bool, allow_hosts: Collection[str] = (), bind: str | None = None,
    resolve: Callable[[str], str] | None = None,
) -> NetSource:
    """The node `net:NAME` names, as a source not yet started. Outside an
    unattended run it checks the tier-1 rule now (module docstring). Raises
    ValueError naming the cause: a malformed name, no `--allow-host`
    outside `--unattended`, a name that does not resolve, or an address the flag
    does not name."""
    host = node_host(name)
    if unattended:
        return NetSource(host, fps=fps, allowed=None, bind=bind)
    if not allow_hosts:
        raise ValueError(ALLOW)
    allowed = frozenset(str(ipaddress.ip_address(a)) for a in allow_hosts)
    try:
        address = _lookup(host, resolve)
    except OSError as exc:
        raise ValueError(f"cannot find {host}: {wled.failure(exc)}; check that the node is on and on this "
                         "network, or name it by its IPv4 address") from None
    if address not in allowed:
        raise ValueError(f"{host} is at {address}, which --allow-host does not name ({', '.join(sorted(allowed))}); "
                         f"check the address with `audio list`, then give --allow-host {address}")
    return NetSource(host, fps=fps, allowed=allowed, address=address, bind=bind)


def _lookup(host: str, resolve: Callable[[str], str] | None) -> str:
    """The IPv4 address of `host`: the host itself, or what `resolve` gives
    (by default `wled.resolve_name`, looked up at call time). Raises OSError."""
    return host if is_ipv4(host) else (resolve or wled.resolve_name)(host)


# ---- what a node says of itself ------------------------------------------


@dataclass(frozen=True, slots=True)
class NodeInfo:
    """A capture node's `/json/info` (firmware/audio-node/main/info.c), at
    `address`: the fields pewpew reads."""

    address: str
    mac: str  # 12 lowercase hex digits
    nonce: int
    name: str | None = None
    ver: str | None = None
    input: str | None = None
    peak_db: float | None = None
    rssi: int | None = None
    uptime: int | None = None
    reset_reason: str | None = None
    holder: str | None = None
    key: bool | None = None

    @classmethod
    def of(cls, address: str, info: object) -> NodeInfo | None:
        """The node `info` describes, or None when it is no capture node's."""
        if not isinstance(info, dict) or not wled.is_node(info) or info.get("product") != PRODUCT:
            return None
        try:
            mac, nonce = keys.mac_text(str(info.get("mac"))), int(str(info.get("nonce")), 16)
        except ValueError:
            return None
        wifi = info.get("wifi")
        peak, uptime, key = info.get("peak"), info.get("uptime"), info.get("key")
        rssi = wifi.get("rssi") if isinstance(wifi, dict) else None
        return cls(address, mac, nonce, name=_text(info.get("name")), ver=_text(info.get("ver")),
                   input=_text(info.get("input")), peak_db=float(peak) if is_number(peak) else None,
                   rssi=int(rssi) if is_number(rssi) else None, uptime=int(uptime) if is_number(uptime) else None,
                   reset_reason=_text(info.get("reset_reason")), holder=_text(info.get("holder")),
                   key=key if isinstance(key, bool) else None)

    def row(self) -> dict:
        """Its row in `audio list`."""
        return {"name": self.name, "address": self.address, "mac": self.mac, "input": self.input,
                "peak_db": self.peak_db, "ver": self.ver, "key": self.key, "holder": self.holder}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def node_lines(nodes: Iterable[NodeInfo]) -> list[str]:
    """One line per node, for a terminal: `boards scan` and `audio list`."""
    lines = []
    for node in nodes:
        peak = "silent" if node.peak_db is None else f"peak {node.peak_db:g} dBFS"
        held = f"streaming to {node.holder}" if node.holder else "no subscriber"
        key = "" if node.key is not False else "; no key flashed"
        lines.append(f"{node.address:<15}  {node.name or '?':<16}  MAC {wled.format_mac(node.mac)}  "
                     f"capture node {node.ver or '?'} ({node.input or '?'} in), {peak}, {held}{key}")
    return lines


def find_nodes(subnet: ipaddress.IPv4Network, mine: str | None,
               fetch: Callable[[str, float], dict] | None = None) -> list[NodeInfo]:
    """Every capture node in `subnet` that answers `/json/info`, by address.
    Reads only (tier 0)."""
    found = wled.replies(subnet, mine, fetch or wled.fetch_info)
    return [node for address, info in found if (node := NodeInfo.of(address, info)) is not None]


# ---- receiving -------------------------------------------------------------


@dataclass(slots=True)
class Counts:
    """What a receiver saw, from its start: packets taken, samples missing
    from the index (lost by the network or the node), and packets dropped
    late, as strays, or stale (of a nonce left behind, or not the one this
    host signed for); the node's overflow and clip flags; its reboots (new
    boot nonces); and the epochs started by following dropped packets
    (module docstring)."""

    packets: int = 0
    missing: int = 0
    late: int = 0
    stray: int = 0
    stale: int = 0
    overflows: int = 0
    clips: int = 0
    reboots: int = 0
    followed: int = 0


class Receiver:
    """Packets in, blocks out, on the loop thread (module docstring). The
    blocks' indices are the host's: each epoch's node indices, moved so a
    new epoch jumps by `restart_gap`."""

    def __init__(self, fps: float) -> None:
        self.clock = SampleClock(RATE, fps)
        self.counts = Counts()
        self.heard: float | None = None  # engine time of the last tick that took a packet
        self._nonce: int | None = None
        self._left: deque[int] = deque(maxlen=8)  # nonces of past epochs
        self._offset = 0  # host index = node index + offset
        self._next: int | None = None  # node index one past the last sample taken this epoch
        self._last: tuple[int, float] | None = None  # (node end, stamp) of the last packet taken
        self._end = 0  # host index one past the last sample taken
        self._t = 0.0  # engine time of the last tick
        self._recent: deque[tuple[float, int, int]] = deque()  # (tick, samples taken, samples missing)

    def receive(self, packets: Iterable[Packet], t: float, *, signed: int | None = None) -> list[Block]:
        """The blocks the packets drained at engine time `t` give, in index
        order. `signed` is the boot nonce of the SUB this host signed, for a
        live node, or None for a trace (module docstring)."""
        stamp = t + self.clock.slot
        out: list[Block] = []
        taken = missing = 0
        for nonce, arrived in groupby(packets, key=attrgetter("nonce")):
            run = sorted(arrived, key=attrgetter("index"))
            if nonce in self._left or signed is not None and nonce != signed:
                self.counts.stale += len(run)
                continue
            if nonce != self._nonce:
                if self._nonce is not None:
                    self._left.append(self._nonce)
                    self.counts.reboots += 1
                self._epoch(nonce, run[0].index)
            for packet in run:
                block, gap = self._take(packet, t, stamp)
                if block is not None:
                    out.append(block)
                    taken += len(block.samples)
                    missing += gap
        if out:
            self.heard = t
            self._recent.append((t, taken, missing))
        self._t = t
        while self._recent and self._recent[0][0] <= t - LOSS_S:
            self._recent.popleft()
        return out

    @property
    def loss(self) -> float | None:
        """The share of samples missing over the last `LOSS_S`, or None
        before any. A tick's missing samples come just before it, so only
        those the window reaches back to count."""
        since = self._t - LOSS_S
        taken = sum(r[1] for r in self._recent)
        missing = sum(min(gap, (tick - since) * RATE) for tick, _, gap in self._recent)
        return None if not taken + missing else missing / (taken + missing)

    def _epoch(self, nonce: int, index: int) -> None:
        self._nonce = nonce
        self._offset = self._end + restart_gap(RATE) - index
        self._next = self._last = None
        self.clock.restart()

    def _take(self, packet: Packet, t: float, stamp: float) -> tuple[Block | None, int]:
        """The block `packet` gives and the samples missing before it, or
        (None, 0) when it is dropped."""
        late = self._next is not None and packet.end <= self._next
        if late or self._stray(packet, stamp):
            if self.heard is None or t - self.heard < LOST_S:
                self.counts.late += late
                self.counts.stray += not late
                return None, 0
            self._epoch(packet.nonce, packet.index)  # only dropped packets came for LOST_S: follow them
            self.counts.followed += 1
        start = packet.index if self._next is None else max(packet.index, self._next)
        gap = 0 if self._next is None else max(0, packet.index - self._next)
        samples = packet.samples()[start - packet.index:]
        block = Block(start + self._offset, samples)
        self.clock.observe(block.end, t)
        self._next, self._last, self._end = packet.end, (packet.end, stamp), block.end
        self.counts.packets += 1
        self.counts.missing += gap
        self.counts.overflows += bool(packet.flags & OVERFLOW)
        self.counts.clips += bool(packet.flags & CLIP)
        return block, gap

    def _stray(self, packet: Packet, stamp: float) -> bool:
        if self._last is None:
            return False
        mapped = self.clock.time(packet.end + self._offset)
        if mapped is None:
            end, at = self._last
            mapped = at + (packet.end - end) / RATE
        return mapped - stamp > LOST_S


# ---- a recorded trace --------------------------------------------------------

TRACE_MAGIC = b"pewtrace"
TRACE_HEAD = struct.Struct("<8sdI")  # magic, the loop's fps, the rate
TRACE_RECORD = struct.Struct("<20sII")  # a packet's header, its sample count, the tick it was drained at


@dataclass(frozen=True, slots=True)
class Trace:
    """Packets as a loop at `fps` drained them: each packet's header, its
    sample count and its tick (`t = tick / fps`, the first tick 1), with no
    sample. A trace and a signal replay a node's run (`TraceSource`)."""

    fps: float
    records: tuple[tuple[bytes, int, int], ...] = ()

    def to_bytes(self) -> bytes:
        return TRACE_HEAD.pack(TRACE_MAGIC, self.fps, RATE) + b"".join(
            TRACE_RECORD.pack(head, count, tick) for head, count, tick in self.records)

    @classmethod
    def from_bytes(cls, data: bytes) -> Trace:
        """The trace `data` holds; ValueError when it holds none."""
        if len(data) < TRACE_HEAD.size or (len(data) - TRACE_HEAD.size) % TRACE_RECORD.size:
            raise ValueError("not a packet trace: its length is not a header and whole records")
        magic, fps, rate = TRACE_HEAD.unpack_from(data)
        if magic != TRACE_MAGIC or rate != RATE or not fps > 0:
            raise ValueError(f"not a packet trace of {RATE} Hz: its header does not match")
        return cls(fps, tuple(TRACE_RECORD.iter_unpack(data[TRACE_HEAD.size:])))

    @staticmethod
    def record(packet: Packet, tick: int) -> tuple[bytes, int, int]:
        """`packet`, drained at `tick`, as a record."""
        return header(packet), packet.count, tick


def looped_pcm(signal: np.ndarray, index: int, count: int) -> bytes:
    """The s16 payload of `count` samples of `signal`, read on a loop,
    from sample `index`."""
    return pcm(signal[np.arange(index, index + count) % len(signal)])


class TraceSource:
    """A node's run replayed: the packets of `trace`, drained at their
    ticks, carrying `signal` (float32 at `RATE`, read on a loop) at their
    indices, through the same `Receiver` as a live node. Deterministic: the
    same trace, signal and ticks give the same blocks."""

    kind = "trace"
    rate = RATE

    def __init__(self, trace: Trace, signal: np.ndarray, *, name: str = "trace") -> None:
        self.name = name
        self.trace = trace
        self.signal = np.asarray(signal, np.float32)
        self.receiver = Receiver(trace.fps)
        self._next = 0  # the next record to drain

    def take(self, t: float) -> list[Block]:
        tick = round(t * self.trace.fps)
        records = self.trace.records
        due: list[Packet] = []
        while self._next < len(records) and records[self._next][2] <= tick:
            head, count, _ = records[self._next]
            _, _, flags, index, nonce = HEADER.unpack(head)
            due.append(Packet(index, nonce, flags, looped_pcm(self.signal, index, count)))
            self._next += 1
        return self.receiver.receive(due, t)

    def time(self, index: float) -> float | None:
        return self.receiver.clock.time(index)

    def state(self) -> dict:
        return {"name": self.name, "kind": self.kind, "rate": RATE, **_view(self.receiver)}


def _view(receiver: Receiver) -> dict:
    """A receiver's numbers, JSON-ready."""
    drift = receiver.clock.drift_ppm
    loss = receiver.loss
    return {
        **asdict(receiver.counts),
        "loss": None if loss is None else round(loss, 4),
        "drift_ppm": None if drift is None else round(drift, 1),
    }


# ---- a live node ---------------------------------------------------------------


class NetSource:
    """A capture node at `host` as an `AudioSource` (module docstring).

    `allowed` is the addresses `--allow-host` names, or None in an unattended run,
    which subscribes to any address; `address` is the one the launch
    checked, if any. `bind` is `run --host`, `port` the node's (tests
    change it), and `now` the supervisor's clock. `resolve` and `fetch`
    default to `pewpew.wled`'s, looked up at call time. `tap`, when set,
    gets each tick's packets and `t` (the bench records traces with it).
    Call `start` once `audit` has written the record, and `stop` once the
    loop has stopped."""

    kind = "node"
    rate = RATE

    def __init__(
        self, host: str, *, fps: float, allowed: frozenset[str] | None, address: str | None = None,
        bind: str | None = None, port: int = PORT, now: Callable[[], float] = time.monotonic,
        resolve: Callable[[str], str] | None = None, fetch: Callable[[str, float], dict] | None = None,
    ) -> None:
        self.name = host
        self.allowed = allowed
        self.address = address
        self.receiver = Receiver(fps)
        self.tap: Callable[[list[Packet], float], None] | None = None
        self._bind = bind if bind is not None and is_ipv4(bind) else None
        self._port = port
        self._now = now
        self._resolve = resolve
        self._fetch = fetch
        self._argv: list[str] = []
        self._recorded = address  # the last address an audit record names
        # The loop thread's own.
        self._began: float | None = None
        self._takes = 0  # ticks that took a packet, which the supervisor reads to tell quiet
        # Shared, under the lock.
        self._lock = threading.Lock()
        self._sock: socket.socket | None = None
        self._node: NodeInfo | None = None
        self._sub: bytes | None = None
        self._signed: int | None = None  # the boot nonce the SUB names
        self._reason: str | None = None  # why the supervisor does not subscribe, until its next find
        self._denial: Denial | None = None  # the node's refusal of the SUB, until the node answers again
        self._view: dict = {"status": "opening", **_view(self.receiver)}
        # The supervisor's own.
        self._mac: str | None = None  # the node it subscribed to first: it subscribes to no other
        self._logged: str | None = None
        self._seen = 0
        self._next_find = -math.inf
        self._next_info = math.inf
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- any thread ------------------------------------------------------

    def state(self) -> dict:
        """JSON-ready: the input's name, kind and rate; its `status`
        (opening, listening or lost) and why it is lost; `busy` when another
        host holds the node; its overflows; and `node`, the node's numbers
        (address, what its /json/info says, and the receiver's counts)."""
        with self._lock:
            view, node, reason, denial = self._view, self._node, self._reason, self._denial
        if reason is None and denial is not None:
            reason = DENIALS[denial]
        status = view["status"]
        if status == "opening" and reason is not None:
            status = "lost"  # the supervisor knows why no packet will come
        lost_reason = None if status == "listening" else reason or view.get("why")
        info = {} if node is None else {
            "mac": node.mac, "ver": node.ver, "rssi": node.rssi, "uptime": node.uptime,
            "reset_reason": node.reset_reason}
        numbers = {k: v for k, v in view.items() if k not in ("status", "why")}
        return {
            "name": self.name, "kind": self.kind, "rate": RATE, "channel": None, "status": status,
            "reason": lost_reason, "busy": denial is Denial.HELD, "overflows": numbers["overflows"],
            "node": {"address": None if node is None else node.address, **info, **numbers},
        }

    def describe(self) -> str:
        """One line on the node, for `run --dry-run`."""
        where = (", looked up when the run starts" if self.allowed is None
                 else f" at {self.address} (--allow-host names it)")
        return f"audio: capture node {self.name}{where}; it subscribes after its audit record, at 48 kHz mono"

    def time(self, index: float) -> float | None:
        return self.receiver.clock.time(index)

    def audit(self, argv: list[str], *, feature_log: Path | None = None) -> Path:
        """Append the `audio-input` audit record before the first SUB;
        returns the log's path. Raises OSError when it cannot be written:
        then nothing subscribes."""
        self._argv = list(argv)
        return audit.record(
            "audio-input", argv=self._argv, input=self.name, kind=self.kind, rate=RATE, channel=None,
            address=self.address, allow_hosts=None if self.allowed is None else sorted(self.allowed),
            feature_log=None if feature_log is None else str(feature_log), privacy=PRIVACY,
        )

    def start(self) -> None:
        """Start the supervisor, which finds the node at once."""
        self._thread = threading.Thread(target=self._run, name="pewpew-audio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the supervisor and close the socket. After the loop has stopped."""
        self._stopping.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2 * wled.TIMEOUT_S + RENEW_S)
        with self._lock:
            sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()

    # ---- loop thread -----------------------------------------------------

    def take(self, t: float) -> list[Block]:
        """What the node sent since the last tick, read without waiting."""
        if self._began is None:
            self._began = t
        packets, denial = self._drain()
        if self.tap is not None:
            self.tap(packets, t)
        blocks = self.receiver.receive(packets, t, signed=self._signed)
        if blocks:
            self._takes += 1
        heard = self.receiver.heard
        if heard is not None and t - heard < LOST_S:
            status, why = "listening", None
        elif heard is not None:
            status, why = "lost", f"no packets for {LOST_S:g} s"
        elif t - self._began >= OPENING_S:
            status, why = "lost", (f"no packets in {OPENING_S:g} s; on a Mac, allow this app in {wled.PRIVACY}")
        else:
            status, why = "opening", None
        view = {"status": status, "why": why, **_view(self.receiver)}
        if heard is not None:
            view["age_s"] = round(t - heard, 3)
        with self._lock:
            self._view = view
            if denial is not None:
                self._denial = denial
            elif blocks:  # the node took the SUB
                self._denial = None
        return blocks

    def _drain(self) -> tuple[list[Packet], Denial | None]:
        """The packets waiting, and the last refusal among them."""
        sock = self._sock
        packets: list[Packet] = []
        denial = None
        if sock is None:
            return packets, denial
        for _ in range(MAX_DATAGRAMS):
            try:
                data = sock.recv(2048)
            except BlockingIOError:
                break
            except ConnectionRefusedError:  # the ICMP of a SUB that found no node listening
                continue
            except OSError:  # the supervisor closed or replaced the socket
                break
            packet = decode(data)
            if packet is not None:
                packets.append(packet)
            else:
                denial = refused(data) or denial
        return packets, denial

    # ---- the supervisor --------------------------------------------------

    def step(self) -> None:
        """One pass of the supervisor (module docstring)."""
        now = self._now()
        quiet = self._takes == self._seen
        self._seen = self._takes
        with self._lock:
            denial, sub = self._denial, self._sub
        if denial in REFIND or (sub is None or quiet) and now >= self._next_find:
            self._next_find = now + 2 * RENEW_S
            sub = self._find(now)
        if sub is not None:
            self._send(sub)
        if not quiet and now >= self._next_info:
            self._poll(now)  # after the renewal, and briefly, so the holder never lapses

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                self.step()
            except Exception:  # the supervisor must outlive anything a node or a resolver does
                logger.exception("capture node supervisor step failed (contained)")
            self._wake.wait(RENEW_S)

    def _find(self, now: float) -> bytes | None:
        """Look the node up and sign a SUB to it; None, with the reason,
        when that fails (module docstring)."""
        host = self.name
        try:
            address = _lookup(host, self._resolve)
        except OSError as exc:
            return self._lose(f"cannot find {host}: {wled.failure(exc)}; pewpew looks again every "
                              f"{2 * RENEW_S:g} s")
        if self.allowed is not None and address not in self.allowed:
            return self._lose(f"{host} is at {address} now, which --allow-host does not name, so pewpew does not "
                              "subscribe; check the node, then run again with that address")
        try:
            node = self._info(address, wled.TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001  any failure of the request: the node does not answer
            hint = f"; on a Mac, allow this app in {wled.PRIVACY}" if wled.no_route(exc) else ""
            return self._lose(f"the node at {address} does not answer /json/info: {wled.failure(exc)}{hint}")
        if node is None:
            return self._lose(f"{address} is not a capture node (its /json/info has no brand "
                              f"{wled.NODE_BRAND!r}); check the name")
        if self._mac is not None and node.mac != self._mac:
            return self._lose(f"another node ({wled.format_mac(node.mac)}) answers at {address} now, not "
                              f"{wled.format_mac(self._mac)}, the node this run streams from; pewpew looks again "
                              f"every {2 * RENEW_S:g} s (`audio list` shows where each node is)")
        try:
            key = keys.load(node.mac)
        except (OSError, ValueError) as exc:
            return self._lose(f"cannot read pewpew's node keys: {describe_exception(exc)}")
        if key is None:
            return self._lose(f"pewpew has no key for node {wled.format_mac(node.mac)}: make one and flash it "
                              "(`python -m pewpew audio key MAC`, docs/audio.md §8)")
        if address != self._recorded:
            try:
                audit.record("audio-readdress", argv=self._argv, input=host, address=address,
                             previous=self._recorded, mac=node.mac)
            except OSError as exc:
                return self._lose(f"cannot write the audit record for {address} ({describe_exception(exc)}), "
                                  "so pewpew does not subscribe there")
            self._recorded = address
        try:
            local = self._connect(address)
        except OSError as exc:
            return self._lose(f"cannot open a socket to {address}: {describe_exception(exc)}")
        sub = subscription(key, node.mac, node.nonce, local)
        with self._lock:
            self._node, self._sub, self._signed, self._reason = node, sub, node.nonce, None
        self._mac = node.mac
        self._logged = None
        self._next_info = now + INFO_S
        if address != self.address:
            logger.info("capture node %s at %s", host, address)
        self.address = address
        return sub

    def _poll(self, now: float) -> None:
        """Read a streaming node's /json/info again, for its signal and uptime."""
        self._next_info = now + INFO_S
        address = self.address
        if address is None:
            return
        try:
            node = self._info(address, POLL_TIMEOUT_S)
        except Exception:  # noqa: BLE001  a missed poll changes nothing; the packets say more
            return
        if node is not None and node.mac == self._mac:  # another node's reply is the next find's to judge
            with self._lock:
                self._node = node

    def _info(self, address: str, timeout: float) -> NodeInfo | None:
        """The node's `/json/info` at `address`, read within `timeout`; raises what the request raises."""
        return NodeInfo.of(address, (self._fetch or wled.fetch_info)(address, timeout))

    def _connect(self, address: str) -> tuple[str, int]:
        """Connect the socket to the node at `address`; the (IPv4, port)
        the node sees this host at."""
        with self._lock:
            sock = self._sock
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RECEIVE_BUFFER)
            sock.bind((self._bind or "0.0.0.0", 0))
            sock.setblocking(False)
        sock.connect((address, self._port))
        with self._lock:
            self._sock = sock
        ip, port = sock.getsockname()[:2]
        return ip, port

    def _send(self, sub: bytes) -> None:
        with self._lock:
            sock = self._sock
        if sock is None:
            return
        try:
            sock.send(sub)
        except OSError:  # no route, or the ICMP of the last one: the next pass tries again
            pass

    def _lose(self, reason: str) -> None:
        """Stop subscribing, for `reason`; the node's last refusal no longer applies."""
        with self._lock:
            self._reason, self._sub, self._denial = reason, None, None
        if reason != self._logged:
            self._logged = reason
            logger.warning("capture node %s: %s", self.name, reason)


__all__ = [
    "LOSS_S", "OPENING_S", "PREFIX", "Counts", "NetSource", "NodeInfo", "Receiver", "Trace", "TraceSource",
    "find_nodes", "looped_pcm", "node_host", "node_lines", "node_source",
]
