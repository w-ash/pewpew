"""The PNG encoder (src/pewpew/png.py): lossless, byte-deterministic, and
strict about its input."""

from __future__ import annotations

import hashlib
import zlib
from types import SimpleNamespace

import numpy as np
import pytest

from pewpew.png import encode_png
from pngread import chunks, decode_png

# sha256 of `_checker()` encoded. Classic zlib deflates the same rows to the
# same bytes; zlib-ng does not, so the hash holds only under classic zlib.
GOLDEN_SHA256 = "cdf25f2f45d0d985d9e3fe98b1cfb632cdc84884fb9b72e7f4bab2ad9eb73c84"


def _checker() -> np.ndarray:
    """A 6 × 5 test image: a red/blue checker with a grey ramp in green."""
    y, x = np.mgrid[0:6, 0:5]
    rgb = np.zeros((6, 5, 3), np.uint8)
    rgb[..., 0] = np.where((x + y) % 2, 255, 0)
    rgb[..., 1] = (x * 50 + y * 7).astype(np.uint8)
    rgb[..., 2] = np.where((x + y) % 2, 0, 200)
    return rgb


@pytest.mark.parametrize("shape", [(1, 1), (6, 5), (31, 17)])
def test_decoding_gives_back_the_pixels(shape):
    rgb = np.random.default_rng(3).integers(0, 256, (*shape, 3), dtype=np.uint8)
    assert np.array_equal(decode_png(encode_png(rgb)), rgb)


def test_a_strided_view_encodes_the_pixels_it_holds():
    view = _checker()[::2, ::-1]
    assert np.array_equal(decode_png(encode_png(view)), view)


def test_the_file_holds_only_header_data_and_end_chunks():
    assert [kind for kind, _ in chunks(encode_png(_checker()))] == [b"IHDR", b"IDAT", b"IEND"]


def test_the_same_pixels_give_the_same_bytes():
    assert encode_png(_checker()) == encode_png(_checker().copy())


def zlib_ng(module: object = zlib) -> bool:
    """Whether `module` (zlib) runs on zlib-ng: CPython says so from 3.14
    (`ZLIBNG_VERSION`); before, a zlib-ng-compat system libz (Fedora 40 on)
    only names itself in `ZLIB_RUNTIME_VERSION`, such as "1.3.0.zlib-ng"."""
    return hasattr(module, "ZLIBNG_VERSION") or "zlib-ng" in getattr(module, "ZLIB_RUNTIME_VERSION", "")


def test_zlib_ng_is_seen_on_every_python_the_project_supports():
    assert zlib_ng(SimpleNamespace(ZLIB_RUNTIME_VERSION="1.3.0.zlib-ng"))  # 3.11-3.13 on zlib-ng-compat
    assert zlib_ng(SimpleNamespace(ZLIBNG_VERSION="2.2.4", ZLIB_RUNTIME_VERSION="1.3.1.zlib-ng"))
    assert not zlib_ng(SimpleNamespace(ZLIB_RUNTIME_VERSION="1.2.12"))


@pytest.mark.skipif(zlib_ng(), reason="zlib-ng deflates to other bytes than classic zlib")
def test_the_bytes_match_the_golden():
    """If this fails and the decode tests pass, the encoder's choices
    changed (chunks, filter or level), or zlib now deflates differently
    (zlib.ZLIB_RUNTIME_VERSION). Update the hash only on purpose."""
    assert hashlib.sha256(encode_png(_checker())).hexdigest() == GOLDEN_SHA256


@pytest.mark.parametrize(
    ("bad", "says"),
    [
        (np.zeros((4, 4, 3), np.float32), "to_display_u8 first"),
        (np.zeros((4, 4), np.uint8), "(4, 4)"),
        (np.zeros((4, 4, 4), np.uint8), "(4, 4, 4)"),
        (np.zeros((0, 4, 3), np.uint8), "H, W >= 1"),
        (np.zeros((4, 4, 3), np.uint16), "uint16"),
        ([[[0, 0, 0]]], "list"),
    ],
)
def test_anything_but_an_rgb8_array_is_refused_with_the_fix(bad, says):
    with pytest.raises(ValueError, match="encode_png takes an \\(H, W, 3\\) uint8 array") as caught:
        encode_png(bad)
    assert says in str(caught.value)
