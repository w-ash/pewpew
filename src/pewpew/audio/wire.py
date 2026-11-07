"""The capture node's wire format, host side (ADR-009, 2026-11-06
amendment "capture nodes"). `firmware/audio-node/main/wire.h` holds the
same values, and the tests check that the two agree.

Every number is little-endian. Three datagrams cross the private router:

- **audio**, node to host: `PA`, the version, flags (`CLIP`,
  `OVERFLOW`), the first sample's index (u64) and the boot nonce (u64),
  then 1 to `MAX_SAMPLES` s16 samples at `RATE`: `SAMPLES`, one 10 ms hop,
  unless the I2S driver dropped samples inside the packet. The index
  counts every sample since boot, dropped ones included, so it shows loss
  and order with no sequence number. Silence is sent too.
- **SUB**, host to node, every `RENEW_S`: `PS`, the version, the node's
  MAC, its boot nonce, and the IPv4 address and port the host wants the
  stream at, then an HMAC-SHA256 tag over those 23 bytes under the
  node's key. The node checks each against itself and the datagram's
  source (`check_subscription`), so a replayed SUB can only send the
  stream to the host that signed it. The holder keeps the stream while it
  renews; anyone else is refused until `HOLD_S` pass without a renewal.
- **refusal**, node to host: `PR`, the version and a `Denial`.

There is no per-packet tag (the maintainer, 2026-11-06): the private router is the
boundary, and the host's socket is `connect()`ed to the node, so the
kernel drops datagrams from anyone else.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import struct
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

PORT = 7448
RATE = 48000
SAMPLES = 480
MAX_SAMPLES = 726  # the most that fit one 1 472-byte UDP payload
VERSION = 1
AUDIO_MAGIC = b"PA"
SUB_MAGIC = b"PS"
REFUSAL_MAGIC = b"PR"
HEADER = struct.Struct("<2sBBQQ")  # magic, version, flags, first-sample index, boot nonce
SUB_HEAD = struct.Struct("<2sB6sQ4sH")  # magic, version, MAC, nonce, reply IPv4, reply port
REFUSAL = struct.Struct("<2sBB")  # magic, version, code
TAG_SIZE = 32
SUB_SIZE = SUB_HEAD.size + TAG_SIZE
KEY_SIZE = 32
CLIP = 0x01
OVERFLOW = 0x02
HOLD_S = 3.0
RENEW_S = 1.0
PRODUCT = "audio-node"
FIRMWARE = "pewpew-audio-node"  # the firmware name Improv's device info gives
FULL_SCALE = 32768.0


class Denial(IntEnum):
    """Why a node refused a SUB, in the order it checks."""

    MALFORMED = 1
    OTHER_NODE = 2
    STALE = 3
    ADDRESS = 4
    NO_KEY = 5
    KEY = 6
    HELD = 7


# What each denial means, and what to do about it; no path, since the
# sentence crosses the preview socket.
DENIALS = {
    Denial.MALFORMED: "the node cannot read pewpew's subscription: flash the node from this checkout "
                      "(docs/audio.md §8)",
    Denial.OTHER_NODE: "another node answers at this address now (its MAC differs); pewpew looks the name up again",
    Denial.STALE: "the node rebooted since pewpew read its boot nonce; pewpew reads it again",
    Denial.ADDRESS: "the node saw the subscription come from another address than it names, so something "
                    "between them rewrites addresses; run with --host set to this computer's address on the "
                    "private router",
    Denial.NO_KEY: "the node has no key: flash its key image (`python -m pewpew audio key MAC`, docs/audio.md §8)",
    Denial.KEY: "the node refuses pewpew's key for it, so its key image and pewpew's key file differ: flash its "
                "key image again (`python -m pewpew audio key MAC`, docs/audio.md §8)",
    Denial.HELD: f"another host holds the node's stream; the node frees it {HOLD_S:g} s after that host stops",
}


@dataclass(frozen=True, slots=True)
class Packet:
    """One audio datagram: `pcm` is its s16 little-endian samples, the
    first of them sample `index` of the boot `nonce`."""

    index: int
    nonce: int
    flags: int
    pcm: bytes

    @property
    def count(self) -> int:
        """How many samples it holds."""
        return len(self.pcm) // 2

    @property
    def end(self) -> int:
        """The index one past its last sample."""
        return self.index + self.count

    def samples(self) -> np.ndarray:
        """Its samples as read-only float32 in -1 to 1."""
        out = np.frombuffer(self.pcm, "<i2").astype(np.float32) / np.float32(FULL_SCALE)
        out.setflags(write=False)
        return out


def header(packet: Packet) -> bytes:
    """The header of `packet` as the node sends it, with no sample."""
    return HEADER.pack(AUDIO_MAGIC, VERSION, packet.flags, packet.index, packet.nonce)


def encode(packet: Packet) -> bytes:
    """`packet` as the node sends it."""
    return header(packet) + packet.pcm


def decode(data: bytes) -> Packet | None:
    """The audio packet `data` holds, or None for any other datagram."""
    size = len(data) - HEADER.size
    if size <= 0 or size % 2 or size > 2 * MAX_SAMPLES:
        return None
    magic, version, flags, index, nonce = HEADER.unpack_from(data)
    if magic != AUDIO_MAGIC or version != VERSION:
        return None
    return Packet(index, nonce, flags, bytes(data[HEADER.size:]))


def pcm(samples: np.ndarray) -> bytes:
    """Float samples in -1 to 1 as a packet's s16 payload, clipped and
    rounded as the node's converter would give them."""
    ints = np.clip(np.round(np.asarray(samples, np.float64) * FULL_SCALE), -FULL_SCALE, FULL_SCALE - 1)
    return ints.astype("<i2").tobytes()


def mac_bytes(mac: str) -> bytes:
    """`aabbccddeeff` (as /json/info gives it) or `aa:bb:cc:dd:ee:ff` (as
    esptool prints it) as 6 bytes. Raises ValueError for anything else."""
    text = mac.strip().lower().replace(":", "").replace("-", "")
    if len(text) != 12 or any(c not in "0123456789abcdef" for c in text):
        raise ValueError(f"{mac!r} is not a MAC address; give 12 hex digits, such as aa:bb:cc:dd:ee:ff")
    return bytes.fromhex(text)


def subscription(key: bytes, mac: str, nonce: int, address: tuple[str, int]) -> bytes:
    """The SUB that asks node `mac`, booted with `nonce`, to stream to
    `address`, the (IPv4, port) the host sends it from."""
    ip, port = address
    head = SUB_HEAD.pack(SUB_MAGIC, VERSION, mac_bytes(mac), nonce, ipaddress.IPv4Address(ip).packed, port)
    return head + hmac.new(key, head, hashlib.sha256).digest()


def check_subscription(data: bytes, *, mac: str, nonce: int, key: bytes | None,
                       source: tuple[str, int]) -> Denial | None:
    """The node's check of a SUB that came from `source`, as its firmware
    runs it (`sub.c`) but without the holder: the first `Denial` it fails,
    or None for a good one. The fake node in the tests and the bench use it."""
    if len(data) != SUB_SIZE or data[:2] != SUB_MAGIC or data[2] != VERSION:
        return Denial.MALFORMED
    _, _, sub_mac, sub_nonce, ip, port = SUB_HEAD.unpack_from(data)
    if sub_mac != mac_bytes(mac):
        return Denial.OTHER_NODE
    if sub_nonce != nonce:
        return Denial.STALE
    if (str(ipaddress.IPv4Address(ip)), port) != source:
        return Denial.ADDRESS
    if key is None:
        return Denial.NO_KEY
    if not hmac.compare_digest(hmac.new(key, data[:SUB_HEAD.size], hashlib.sha256).digest(), data[SUB_HEAD.size:]):
        return Denial.KEY
    return None


def refusal(denial: Denial) -> bytes:
    """The refusal a node sends for `denial`."""
    return REFUSAL.pack(REFUSAL_MAGIC, VERSION, denial)


def refused(data: bytes) -> Denial | None:
    """The denial a refusal datagram carries, or None for any other datagram."""
    if len(data) != REFUSAL.size:
        return None
    magic, version, code = REFUSAL.unpack(data)
    if magic != REFUSAL_MAGIC or version != VERSION or code not in iter(Denial):
        return None
    return Denial(code)


__all__ = [
    "AUDIO_MAGIC", "CLIP", "DENIALS", "FIRMWARE", "HEADER", "HOLD_S", "KEY_SIZE", "MAX_SAMPLES", "OVERFLOW", "PORT",
    "PRODUCT", "RATE", "REFUSAL", "REFUSAL_MAGIC", "RENEW_S", "SAMPLES", "SUB_HEAD", "SUB_MAGIC", "SUB_SIZE",
    "TAG_SIZE", "VERSION", "Denial", "Packet", "check_subscription", "decode", "encode", "header", "mac_bytes", "pcm",
    "refusal", "refused", "subscription",
]
