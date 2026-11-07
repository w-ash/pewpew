"""A deterministic PNG encoder for 8-bit RGB images, standard library only.

The same pixels always give the same bytes: the file holds the IHDR, IDAT
and IEND chunks and nothing else (no time or text chunk), every row has
filter type 0 (none), and zlib compresses at one fixed level (PNG
specification, third edition, W3C: datastream §5, filtering §9,
compression §10). So a contact sheet (`pewpew.sheet`) is an artifact an
agent can hash and cache, given the same zlib build: zlib-ng, for one,
deflates the same rows to other bytes.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np

SIGNATURE = b"\x89PNG\r\n\x1a\n"

# zlib's default level, fixed here so that a zlib default change cannot
# change the bytes.
LEVEL = 6

# IHDR after width and height: bit depth 8, colour type 2 (RGB), deflate
# compression, filter method 0, no interlace.
_RGB8 = (8, 2, 0, 0, 0)


def encode_png(rgb: np.ndarray) -> bytes:
    """`rgb`, an (H, W, 3) uint8 array with H, W >= 1, as the bytes of a
    PNG file (8-bit RGB, no alpha). Raises ValueError for any other array."""
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or 0 in rgb.shape:
        got = f"{rgb.dtype} {rgb.shape}" if isinstance(rgb, np.ndarray) else type(rgb).__name__
        hint = "; a float frame goes through pewpew.sinks.base.to_display_u8 first" if _is_float(rgb) else ""
        raise ValueError(f"encode_png takes an (H, W, 3) uint8 array with H, W >= 1, got {got}{hint}")
    height, width = rgb.shape[:2]
    rows = np.zeros((height, 1 + 3 * width), np.uint8)  # byte 0 of each row is its filter type, 0
    rows[:, 1:] = rgb.reshape(height, 3 * width)
    return b"".join(
        (
            SIGNATURE,
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, *_RGB8)),
            _chunk(b"IDAT", zlib.compress(rows.tobytes(), LEVEL)),
            _chunk(b"IEND", b""),
        )
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    """One chunk: data length, type, data, and the CRC-32 of type and data."""
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _is_float(value: object) -> bool:
    return isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.floating)
