"""Build the page's Martian font subsets from their pinned upstream files.

Run it only when the fonts change (`just fonts`). It needs fontTools and
brotli, which `just fonts` adds for the run alone; pewpew does not depend on
them. It writes three files into web/src/ui/fonts/, which are committed:

- martian-grotesk.woff2: Martian Grotesk, wght 400-600 at wdth 100, for UI text;
- martian-mono.woff2: Martian Mono, wght 400 at wdth 87.5, for keycaps, board
  addresses and the digits and signs of live values;
- OFL.txt: both fonts' copyright lines, then the SIL Open Font License.

Each upstream file is checked against its pinned hash before use. Two runs
with the same fontTools and brotli give byte-identical files.
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

OUT = Path(__file__).resolve().parent.parent / "web" / "src" / "ui" / "fonts"

GROTESK = "https://raw.githubusercontent.com/evilmartians/grotesk/0b66b31f4ffaac140587b6b6ea5e2194c6a7444f"
MONO = "https://raw.githubusercontent.com/evilmartians/mono/8ffa86c2998677256252336f3662d60997e74b05"
MONO_ZIP = "https://github.com/evilmartians/mono/releases/download/v1.1.0/martian-mono-1.1.0-variable.zip"

# sha256 of each font file [S1700][S1701]; git blob ids of the licence texts.
GROTESK_TTF = (f"{GROTESK}/fonts/variable/MartianGrotesk%5Bwdth,wght%5D.ttf",
               "f81807163c34ff754e6d915b0b59f76cca88332b67c45cfc7453ace5751ae912")
MONO_TTF = ("MartianMonoVF.ttf", "60e0eee102be3f96b3c2c6431e6bb7101ff20735baee480e091af1765d7d49c7")
GROTESK_OFL = (f"{GROTESK}/OFL.txt", "68afb7372a040929f4e219e7f9c04432291444bf")
MONO_OFL = (f"{MONO}/OFL.txt", "3d86611f3660e09781ef246830e82374cbd7dfab")

# UI text: ASCII, plus the other characters the page and the engine's strings
# use that Grotesk has. Look and board names are ASCII by rule (aura/book.py,
# provision.py); µ comes from an engine error ("µs a frame").
GROTESK_TEXT = ("U+0020-007E,U+00A0,U+00B0-00B3,U+00B5,U+00B7,U+00B9,U+00D7,U+2011,U+2013-2014,U+2018-2019,"
                "U+201C-201D,U+2022,U+2026,U+2039-203A,U+2074-2079,U+2190-2193,U+2212,U+2248,U+2260")
# Keycaps and addresses: ASCII, the value signs, and the arrows keycaps show.
MONO_TEXT = "U+0020-007E,U+00A0,U+00B0,U+00B1,U+00B7,U+00D7,U+2013,U+2026,U+2190-2193,U+2212"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    """The id git gives `data` as a blob."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def checked(data: bytes, pin: str, what: str, digest: Callable[[bytes], str] = sha256) -> bytes:
    """Return `data` if its `digest` is `pin`, else exit."""
    got = digest(data)
    if got != pin:
        sys.exit(f"{what}: {digest.__name__} {got}, pinned {pin}")
    return data


def subset(ttf: bytes, axes: dict[str, float | tuple[float, float]], text: str, features: list[str]) -> bytes:
    """Instance `ttf` to `axes`, keep the glyphs for `text` with `features`, and return it as woff2."""
    from fontTools import subset as ft_subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    source = TTFont(io.BytesIO(ttf), recalcTimestamp=False)
    font = instancer.instantiateVariableFont(source, axes, updateFontNames=False)
    staged = io.BytesIO()
    font.save(staged)
    font = TTFont(io.BytesIO(staged.getvalue()), recalcTimestamp=False)
    options = ft_subset.Options()
    options.layout_features = features
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]  # copyright, names, licence and its URL
    options.notdef_outline = True
    options.hinting = False  # Apple ignores hints, and phones render at 3x
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(unicodes=ft_subset.parse_unicodes(text))
    subsetter.subset(font)
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def notice(grotesk: bytes, mono: bytes) -> bytes:
    """Both copyright lines, then the licence, which the two files share word for word."""
    g_head, g_body = grotesk.decode().split("\n", 1)
    m_head, m_body = mono.decode().split("\n", 1)
    if g_body != m_body:
        sys.exit("the two OFL.txt files differ past their copyright lines")
    return f"{g_head}\n{m_head}\n{m_body}".encode()


def main() -> None:
    grotesk_ttf = checked(fetch(GROTESK_TTF[0]), GROTESK_TTF[1], "Martian Grotesk")
    with zipfile.ZipFile(io.BytesIO(fetch(MONO_ZIP))) as release:
        mono_ttf = checked(release.read(MONO_TTF[0]), MONO_TTF[1], "Martian Mono")
    licence = notice(checked(fetch(GROTESK_OFL[0]), GROTESK_OFL[1], "Grotesk OFL.txt", git_blob),
                     checked(fetch(MONO_OFL[0]), MONO_OFL[1], "Mono OFL.txt", git_blob))
    files = {
        # kern for quality; case raises signs beside capitals; calt and liga are Grotesk's few.
        "martian-grotesk.woff2": subset(grotesk_ttf, {"wdth": 100, "wght": (400, 600)}, GROTESK_TEXT,
                                        ["kern", "case", "calt", "liga"]),
        # No calt: Mono's coding ligatures would fuse "..", "::" and "->".
        "martian-mono.woff2": subset(mono_ttf, {"wdth": 87.5, "wght": 400}, MONO_TEXT, ["case"]),
        "OFL.txt": licence,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (OUT / name).write_bytes(data)
        print(f"{name}: {len(data):,} B, sha256 {hashlib.sha256(data).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
