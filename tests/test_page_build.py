"""The preview page in src/pewpew/sinks/web/ is the build of its source in
web/ (`just web` rebuilds it), stays within its size budget, fetches nothing,
and its stylesheet names only tokens it defines."""

from __future__ import annotations

import gzip
import re
from pathlib import Path

from tools.webhash import WEB, web_hash

PAGE = Path(__file__).parents[1] / "src" / "pewpew" / "sinks" / "web" / "index.html"
SRC = WEB / "src"

# The gzipped page as built on 2026-11-06 with the Martian fonts, their notice
# and the icon set (224,888 bytes), plus about 2.5%. The page before the fonts
# was 199,921 bytes against a budget of 217,855 (189,439 + 15%).
GZIP_BUDGET = 230_500

# The token names RA-27c §3.8 retired, and the classes RA-27b §6.1 did: a
# var() of a name nothing defines fails silently.
RETIRED_TOKENS = (
    "--bg", "--panel", "--line", "--line-strong", "--muted", "--text", "--accent-soft", "--danger",
    "--danger-bg", "--danger-text", "--small", "--space-1", "--space-2", "--space-3", "--space-4",
    "--gap", "--radius", "--target", "--warn", "--raised", "--prose", "--prose-size", "--mono",
    "--fs-head", "--fs-row", "--fw-title", "--fw-head", "--fw-row",
)
RETIRED_CLASSES = ("quiet", "primary", "look", "step", "tag", "tag-button", "changed-mark", "muted", "deck-note")

# Custom properties Ark's parts set on themselves at run time.
ARK_VARS = {"--layer-index", "--left", "--top", "--width", "--height"}


def sources(*suffixes: str) -> dict[Path, str]:
    return {p: p.read_text() for p in sorted(SRC.rglob("*")) if p.suffix in suffixes}


def test_the_page_keeps_its_title():
    assert "<title>pewpew preview</title>" in PAGE.read_text()


def test_the_page_is_built_from_the_current_source():
    stamp = re.search(r'<meta name="pewpew-build" content="([0-9a-f]+)"', PAGE.read_text())
    assert stamp, "the page has no build stamp: run `just web`"
    assert stamp.group(1) == web_hash(), "web/ changed since the page was built: run `just web`"


def test_the_gzipped_page_is_within_budget():
    size = len(gzip.compress(PAGE.read_bytes(), mtime=0))
    assert size <= GZIP_BUDGET, f"the gzipped page is {size} bytes, over its {GZIP_BUDGET}-byte budget"


def test_the_page_fetches_no_file():
    """A font or image emitted as its own file would get the page back (sinks/preview.py answers any GET
    with it), and the page would silently fall back."""
    page = PAGE.read_text()
    assert page.count("url(data:font/woff2;base64,") == 3  # Grotesk, Mono, and Mono again as the figures
    assert not re.search(r"""url\(\s*(?!["']?data:)""", page)


def test_the_page_carries_the_fonts_licence():
    """OFL-1.1 §2: every copy carries the copyright notice and the licence."""
    page = PAGE.read_text()
    licence = page[page.rindex("<!--") :]
    for line in (SRC / "ui" / "fonts" / "OFL.txt").read_text().splitlines()[:2]:
        assert line in licence
    assert "SIL OPEN FONT LICENSE Version 1.1" in licence


def test_no_retired_token_or_class_remains():
    found = []
    for path, text in sources(".css", ".ts", ".tsx").items():
        found += [f"{path.name}: {name}" for name in RETIRED_TOKENS if re.search(rf"{re.escape(name)}(?![\w-])", text)]
        if path.suffix == ".tsx":
            names = " ".join(re.findall(r'className="([^"]*)"', text)).split()
            found += [f"{path.name}: .{name}" for name in RETIRED_CLASSES if name in names]
        elif path.suffix == ".css":
            found += [f"{path.name}: .{name}" for name in RETIRED_CLASSES if re.search(rf"\.{name}(?![\w-])", text)]
    assert not found


def test_every_token_used_is_defined():
    """Each var() in the stylesheet, and each property the page reads from it, is declared in CSS or set by
    the page's code, so no var() falls back to nothing unseen."""
    css, code = sources(".css"), sources(".ts", ".tsx")
    defined = {m for text in css.values() for m in re.findall(r"(--[\w-]+)\s*:", text)}
    defined |= {m for text in css.values() for m in re.findall(r"@property\s+(--[\w-]+)", text)}
    # Set by the code: a style object's key, setProperty, or the slot's measured heights (useHeightVar).
    set_by_code = r"""["'](--[\w-]+)["']\s*:|(?:setProperty|useHeightVar)\(\s*["'](--[\w-]+)"""
    defined |= {a or b for text in code.values() for a, b in re.findall(set_by_code, text)}
    used = {m for text in css.values() for m in re.findall(r"var\(\s*(--[\w-]+)", text)}
    used |= {m for text in code.values() for m in re.findall(r"""getPropertyValue\(\s*["'](--[\w-]+)""", text)}
    assert used - defined - ARK_VARS == set()
