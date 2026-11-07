"""A minimal PNG reader for tests: just enough to read what `pewpew.png`
writes (8-bit RGB, filter type 0, no interlace), standard library only."""

from __future__ import annotations

import struct
import zlib

import numpy as np

from pewpew.png import SIGNATURE


def chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """The (type, data) of each chunk, in order, each CRC checked."""
    assert data[:8] == SIGNATURE, "not a PNG signature"
    out, at = [], 8
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        (crc,) = struct.unpack(">I", data[at + 8 + length : at + 12 + length])
        assert crc == zlib.crc32(kind + body), f"bad CRC in {kind!r}"
        out.append((kind, body))
        at += 12 + length
    return out


def decode_png(data: bytes) -> np.ndarray:
    """The (H, W, 3) uint8 pixels of a PNG from `pewpew.png.encode_png`."""
    parts = chunks(data)
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", parts[0][1])
    assert (depth, colour, interlace) == (8, 2, 0), "only 8-bit RGB, not interlaced"
    raw = zlib.decompress(b"".join(body for kind, body in parts if kind == b"IDAT"))
    rows = np.frombuffer(raw, np.uint8).reshape(height, 1 + 3 * width)
    assert not rows[:, 0].any(), "only filter type 0"
    return rows[:, 1:].reshape(height, width, 3)
