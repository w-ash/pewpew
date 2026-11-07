"""A capture node for the tests (pewpew.audio.net): `FakeNode` answers SUBs
on loopback as the firmware does (`sub.c`: `wire.check_subscription`, then
the holder rule) and streams a seeded signal when the test says so; and
`synthetic_trace` makes a packet trace with seeded jitter, loss,
reordering, a duplicate, a stray far-future index and a reboot. No audio
is stored: the samples come from `audio_signals`."""

from __future__ import annotations

import dataclasses
import select
import socket
from collections.abc import Collection
from dataclasses import dataclass, field

import numpy as np

from audio_signals import noise
from pewpew.audio import wire
from pewpew.audio.net import NetSource, Trace, looped_pcm
from pewpew.audio.wire import Denial, Packet

MAC = "aabbccddeeff"


def ready(sock: socket.socket | None, timeout: float = 1.0) -> None:
    """Wait until `sock` has a datagram to read (loopback delivers at once
    on most systems; this makes sure)."""
    assert sock is not None
    select.select([sock], [], [], timeout)


class FakeNode:
    """A node at 127.0.0.1 on a port of its own (module docstring). `key`
    None is a node with no key flashed."""

    def __init__(self, key: bytes | None, *, mac: str = MAC, nonce: int = 0x1234_5678_9ABC_DEF0,
                 signal: np.ndarray | None = None, now: float = 0.0) -> None:
        self.key = key
        self.mac = mac
        self.nonce = nonce
        self.signal = noise(1.0, seed=3) if signal is None else signal
        self.now = now  # the node's clock, in seconds; the test moves it
        self.index = 0
        self.holder: tuple[str, int] | None = None
        self.renewed = -np.inf
        self.denials: list[Denial | None] = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.setblocking(False)
        self.port = self.sock.getsockname()[1]
        self.fetches = 0

    def info(self) -> dict:
        """Its `/json/info`, as firmware/audio-node/main/info.c writes it."""
        return {"ver": "0.1.0", "name": "pewpew-line-1", "mdns": "pewpew-line-1", "mac": self.mac, "brand": "pewpew",
                "product": "audio-node", "uptime": int(self.now), "wifi": {"rssi": -52, "channel": 6},
                "input": "line", "rate": wire.RATE, "nonce": f"{self.nonce:016x}", "peak": -12.5,
                "key": self.key is not None, "holder": None if self.holder is None else self.holder[0],
                "reset_reason": "poweron", "sent": 0, "send_errors": 0, "queue_full": 0, "overflows": 0,
                "overflow_samples": 0, "clips": 0}

    def fetch(self, address: str, timeout: float) -> dict:
        """`wled.fetch_info` for a source that asks this node."""
        self.fetches += 1
        return self.info()

    def streaming(self) -> bool:
        return self.holder is not None and self.now - self.renewed < wire.HOLD_S

    def serve(self, wait: bool = True) -> list[Denial | None]:
        """Answer every SUB waiting, as the firmware does; returns what it
        said to each (None: taken)."""
        if wait:
            ready(self.sock)
        said: list[Denial | None] = []
        while True:
            try:
                data, source = self.sock.recvfrom(64)
            except BlockingIOError:
                break
            denial = wire.check_subscription(data, mac=self.mac, nonce=self.nonce, key=self.key, source=source)
            if denial is None and self.streaming() and self.holder is not None and self.holder[0] != source[0]:
                denial = Denial.HELD
            if denial is None:
                self.holder, self.renewed = source, self.now
            else:
                self.sock.sendto(wire.refusal(denial), source)
            said.append(denial)
        self.denials += said
        return said

    def send(self, count: int = 1, *, drop: Collection[int] = (), flags: int = 0) -> list[Packet]:
        """Make the next `count` packets of the signal and send each to the
        holder, but those whose ordinal is in `drop`; returns them all."""
        made = []
        for k in range(count):
            packet = Packet(self.index, self.nonce, flags, looped_pcm(self.signal, self.index, wire.SAMPLES))
            self.index = packet.end
            made.append(packet)
            if k not in drop and self.streaming() and self.holder is not None:
                self.sock.sendto(wire.encode(packet), self.holder)
        return made

    def reboot(self, nonce: int) -> None:
        """Boot again: a new nonce, the index from 0, and no holder."""
        self.nonce, self.index, self.holder, self.renewed = nonce, 0, None, -np.inf

    def close(self) -> None:
        self.sock.close()


def source_for(node: FakeNode | None, *, fps: float = 60.0, **kw) -> NetSource:
    """A bench-run source at 127.0.0.1: by default subscribed to `node`,
    its /json/info read from the node; `kw` overrides either."""
    at_node = {} if node is None else {"port": node.port, "fetch": node.fetch}
    return NetSource("127.0.0.1", fps=fps, allowed=frozenset({"127.0.0.1"}), address="127.0.0.1",
                     **{**at_node, **kw})


@dataclass
class Scenario:
    """What `synthetic_trace` puts in a trace: `seconds` of packets drained
    at `fps`, each `delay` plus a seeded exponential `jitter` after its last
    sample, from a node whose rate is off by `drift_ppm`. `lose` drops
    packets by ordinal, `swap` sends a packet after the one behind it,
    `twice` sends one again a tick later, `stray` puts a far-future index
    on one, and `reboot` boots again at that packet with a new nonce."""

    seconds: float = 12.0
    fps: float = 60.0
    seed: int = 7
    delay: float = 0.004
    jitter: float = 0.003
    drift_ppm: float = 20.0
    lose: set[int] = field(default_factory=lambda: {150, 151, 420})
    swap: set[int] = field(default_factory=lambda: {300})
    twice: set[int] = field(default_factory=lambda: {360})
    stray: set[int] = field(default_factory=lambda: {500})
    reboot: int | None = 800


def clean(**kw) -> Scenario:
    """A scenario with no loss, reordering, duplicate, stray or reboot,
    but what `kw` puts in."""
    return dataclasses.replace(Scenario(lose=set(), swap=set(), twice=set(), stray=set(), reboot=None), **kw)


def synthetic_trace(s: Scenario | None = None) -> Trace:
    """The trace of scenario `s`, by default `Scenario()`; deterministic for its seed."""
    s = s or Scenario()
    rng = np.random.default_rng(s.seed)
    period = wire.SAMPLES / wire.RATE * (1.0 + s.drift_ppm * 1e-6)
    nonce, index = 0x0F00_0000_0000_0001, 0
    sent: list[tuple[float, Packet]] = []
    for k in range(int(s.seconds / period)):
        if k == s.reboot:
            nonce, index = 0x0F00_0000_0000_0002, 0
        packet = Packet(index, nonce, 0, b"\0\0" * wire.SAMPLES)
        index = packet.end
        arrival = (k + 1) * period + s.delay + float(rng.exponential(s.jitter))
        if k in s.lose:
            continue
        if k in s.stray:
            packet = Packet(packet.index + (1 << 40), nonce, 0, packet.pcm)
        if k in s.swap:
            arrival += period * 1.5
        sent.append((arrival, packet))
        if k in s.twice:
            sent.append((arrival + 1.0 / s.fps, packet))
    sent.sort(key=lambda pair: pair[0])  # the order they arrive in
    records = tuple(Trace.record(packet, max(1, int(np.ceil(at * s.fps)))) for at, packet in sent)
    return Trace(s.fps, records)
