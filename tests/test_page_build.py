"""The preview page in src/pewpew/sinks/web/ is the build of its source in
web/ (`just web` rebuilds it): index.html and its own files, which the engine
serves from `files.json`. What the page always loads, what its 3D view loads
on demand and what its layout editor loads on demand each stay within a size
budget, the page fetches only its own files, and its stylesheet names only
tokens it defines."""

from __future__ import annotations

import gzip
import json
import re
from functools import cache
from pathlib import Path

from tools.webhash import WEB, web_hash

BUILT = Path(__file__).parents[1] / "src" / "pewpew" / "sinks" / "web"
PAGE = BUILT / "index.html"
SRC = WEB / "src"

# What the page always loads (index.html and the files it imports statically),
# gzipped file by file: 228,647 bytes as built on 2026-11-08, when the page
# was first split from its 3D view; 230,142 once the layout editor moved in
# (its own file on demand; the page keeps its wire, its layout panel and the
# editor's styles). The one-file page as built on 2026-11-06
# with the Martian fonts, their notice and the icon set was 224,888 bytes; the
# budget is that plus about 2.5%. The page before the fonts was 199,921 bytes against a
# budget of 217,855 (189,439 + 15%).
GZIP_BUDGET = 230_500
# What the 3D view loads on demand beyond the layout editor's files (three.js,
# @react-three, web/src/rig3d), gzipped file by file: THREE_D_MEASURED bytes as
# built on 2026-11-08 with the gizmo that edits a pose (drei's TransformControls),
# plus 3%. Without the gizmo it was 271,584.
THREE_D_MEASURED = 280_196
THREE_D_BUDGET = round(THREE_D_MEASURED * 1.03)
# What the layout editor and the report load on demand (web/src/arrange and
# zustand), gzipped file by file: RIG_MEASURED bytes as built on 2026-11-08
# with the sync that survives a reconnect, the delete that unwires, the
# phone's gizmo tools and the button that opens Publish, plus 3%; 16,436
# before them. The 3D view loads them too: it edits through the editor's store.
RIG_MEASURED = 18_473
RIG_BUDGET = round(RIG_MEASURED * 1.03)
# What Publish, export looks and the Gallery's chrome load on demand
# (web/src/share), gzipped file by file: SHARE_MEASURED bytes as built on
# 2026-11-08, plus 3%.
SHARE_MEASURED = 2_482
SHARE_BUDGET = round(SHARE_MEASURED * 1.03)

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
    assert "<title>pewpew Console</title>" in PAGE.read_text()


def test_the_page_is_built_from_the_current_source():
    stamp = re.search(r'<meta name="pewpew-build" content="([0-9a-f]+)"', PAGE.read_text())
    assert stamp, "the page has no build stamp: run `just web`"
    assert stamp.group(1) == web_hash(), "web/ changed since the page was built: run `just web`"


@cache
def served() -> tuple[str, ...]:
    """The files the engine serves beside the page (files.json)."""
    return tuple(json.loads((BUILT / "files.json").read_text()))


@cache
def manifest() -> dict[str, dict]:
    """The build's manifest: each chunk by its key (https://vite.dev/guide/backend-integration)."""
    return json.loads((BUILT / "manifest.json").read_text())


def imported(name: str, how: str) -> list[str]:
    """The files built file `name` imports, `how` being "imports" (static) or "dynamicImports"."""
    chunk = next((c for c in manifest().values() if c["file"] == name), {})
    return [manifest()[key]["file"] for key in chunk.get(how, [])]


def static_closure(files: list[str]) -> list[str]:
    """`files` and every chunk they import statically, each once, in the order found."""
    out: list[str] = []
    todo = list(files)
    while todo:
        name = todo.pop(0)
        if name not in out:
            out.append(name)
            todo += imported(name, "imports")
    return out


def entry_files() -> list[str]:
    """What the page always loads: index.html, the files it names, and their static imports."""
    named = re.findall(r'(?:src|href)="/([^"]+)"', PAGE.read_text())
    return ["index.html", *static_closure(named)]


def on_demand(group: str) -> list[str]:
    """What the page's dynamic import of the build's `group` file (a `codeSplitting` group in
    web/vite.config.ts) adds to what it always loads."""
    entry = entry_files()
    dynamic = [file for name in entry for file in imported(name, "dynamicImports")]
    found = [file for file in dynamic if file.startswith(f"assets/{group}-")]
    assert len(found) == 1, f"the page loads no one {group} file on demand: {dynamic}"
    return [name for name in static_closure(found) if name not in entry]


def rig_files() -> list[str]:
    """The layout editor's and the report's files."""
    return on_demand("console-rig")


def share_files() -> list[str]:
    """The files of Publish, export looks and the Gallery's chrome."""
    return on_demand("console-share")


def three_d_files() -> list[str]:
    """The 3D view's own files: what it loads beyond the layout editor's."""
    return [name for name in on_demand("console-3d") if name not in rig_files()]


def gzipped(files: list[str]) -> int:
    return sum(len(gzip.compress((BUILT / name).read_bytes(), mtime=0)) for name in files)


def test_what_the_page_always_loads_is_within_budget():
    size = gzipped(entry_files())
    assert size <= GZIP_BUDGET, f"the page always loads {size} gzipped bytes, over its {GZIP_BUDGET}-byte budget"


def test_the_3d_view_is_within_its_budget():
    files = three_d_files()
    assert files, "the page has no 3D view to load on demand"
    size = gzipped(files)
    assert size <= THREE_D_BUDGET, f"the 3D view loads {size} gzipped bytes, over its {THREE_D_BUDGET}-byte budget"


def test_the_layout_editor_is_within_its_budget():
    files = rig_files()
    size = gzipped(files)
    assert size <= RIG_BUDGET, f"the layout editor loads {size} gzipped bytes, over its {RIG_BUDGET}-byte budget"


def test_publish_and_the_gallery_chrome_are_within_their_budget():
    files = share_files()
    assert files, "the page has no Publish or Gallery chrome to load on demand"
    size = gzipped(files)
    assert size <= SHARE_BUDGET, f"Publish and the Gallery load {size} gzipped bytes, over {SHARE_BUDGET}"


def test_three_js_loads_only_with_the_3d_view():
    """three.js's renderer is in the 3D view's files, and in none the page always loads or the layout
    editor loads: a run without a rig, a page that never shows 3D, and the layout editor in 2D fetch none
    of it."""
    assert not [name for name in [*entry_files(), *rig_files()] if b"WebGLRenderer" in (BUILT / name).read_bytes()]
    assert any(b"WebGLRenderer" in (BUILT / name).read_bytes() for name in three_d_files())


def test_files_json_lists_every_file_of_the_build():
    on_disk = {p.relative_to(BUILT).as_posix() for p in BUILT.rglob("*") if p.is_file()}
    assert set(served()) == on_disk - {"index.html", "files.json", "manifest.json"}
    assert list(served()) == sorted(served())


def test_every_url_in_the_build_is_a_served_file():
    """The page fetches only files the engine serves: any other path gets the page back
    (sinks/preview.py), which would fail silently. Fonts and images are inline."""
    found = set(re.findall(r'(?:src|href)="/([^"]+)"', PAGE.read_text()))
    for name in served():
        text = (BUILT / name).read_text()
        found |= set(re.findall(r"/(assets/[\w.-]+\.(?:js|css))", text))
        found |= {f"assets/{m}" for m in re.findall(r"[\"'`]\./([\w.-]+\.(?:js|css))[\"'`]", text)}
        assert not re.search(r"""url\(\s*(?!["']?data:)""", text), name
    assert found and found <= set(served())
    css = "".join((BUILT / name).read_text() for name in served() if name.endswith(".css"))
    assert css.count("url(data:font/woff2;base64,") == 3  # Grotesk, Mono, and Mono again as the figures


def test_the_page_carries_the_fonts_licence():
    """OFL-1.1 §2: every copy carries the copyright notice and the licence."""
    page = PAGE.read_text()
    licence = page[page.rindex("<!--") :]
    for line in (SRC / "design" / "fonts" / "OFL.txt").read_text().splitlines()[:2]:
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
