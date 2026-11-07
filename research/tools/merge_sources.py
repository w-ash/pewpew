"""Check the research bibliography, or merge new sources into it.

Both modes read research/SOURCES.md and every research/sources/_fragments/*.md,
and refuse a duplicate ID or an ID outside the S-ID block table in
research/README.md.

`--merge` writes the entries into SOURCES.md, grouped under their block and
sorted by ID, then deletes the fragments.

`--check` writes nothing. It fails when SOURCES.md is not in merged form,
when a cite in research/ or docs/ names no source, and when a source an ADR
cites breaks the archival rule (research/README.md): a web source has no
archive.org snapshot, a code source has no `pinned:`, or no excerpt
directory of a source holds a file an ADR cites by line: a file of its
name beside a LICENSE-NOTE.md that names its upstream path.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

from retry_archives import SNAPSHOT_RE

ROOT = Path(__file__).resolve().parents[1]  # research/
SOURCES = ROOT / "SOURCES.md"
FRAGS = ROOT / "sources" / "_fragments"
EXCERPTS = ROOT / "excerpts"
ADRS = ROOT / "synthesis" / "decisions"
CITING = (ROOT, ROOT.parent / "docs")
CLONES = ROOT / "clones"  # gitignored upstream checkouts

LACKS = {"archive": "archive.org snapshot", "pin": "`pinned:` commit"}
# Archival-rule breaks already tracked (docs/backlog/v0.1.x.md, "Close the
# ADR evidence gaps"). A new break fails, and so does a listed one that is
# fixed, so the list only shrinks.
KNOWN_GAPS = {
    "archive": {
        27, 159, 371, 372, 373, 374, 378, 379, 382, 422, 522, 911, 914, 1051,
        1057, 1172, 1258, 1262, 1265, 1269, 1278, 1280, 1294, 1295, 1304, 1305,
        1391,
    },
    "pin": {375, 377},
}

ENTRY_RE = re.compile(r"^### \[S(\d+)\]")
BLOCK_ROW = re.compile(r"^\| (S(\d+)–S(\d+)) \| (.+) \|$", re.MULTILINE)
CITE = re.compile(r"\[S(\d+)(?::([^\]]*))?\]")
FIELD = re.compile(r"^- ([a-z]+): (.*)$", re.MULTILINE)
EXCERPT_DIR = re.compile(r"S(\d+)-")


def blocks() -> list[tuple[int, int, str]]:
    """The S-ID blocks as (first, last, SOURCES.md heading), from the README table."""
    rows = BLOCK_ROW.findall((ROOT / "README.md").read_text())
    if not rows:
        sys.exit("research/README.md has no S-ID block table")
    return [(int(lo), int(hi), f"Block {ids} — {area}") for ids, lo, hi, area in rows]


def parse(text: str, collect_preamble: bool) -> tuple[str, dict[int, str]]:
    """Split a sources file into its preamble and its entries by ID."""
    preamble_lines: list[str] = []
    entries: dict[int, list[str]] = {}
    current: list[str] | None = None
    seen_block = False
    for line in text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            current = entries.setdefault(int(m.group(1)), [])
            if current:
                sys.exit(f"duplicate ID S{m.group(1):>03} within one file")
            current.append(line)
        elif line.startswith("## Block"):
            seen_block = True
            current = None
        elif current is not None:
            current.append(line)
        elif collect_preamble and not seen_block:
            preamble_lines.append(line)
    return (
        "\n".join(preamble_lines).rstrip(),
        {sid: "\n".join(lines).rstrip() for sid, lines in entries.items()},
    )


def load() -> tuple[str, str, dict[int, str], list[Path]]:
    """SOURCES.md's text and preamble, its entries plus every fragment's, and the fragments."""
    text = SOURCES.read_text()
    preamble, entries = parse(text, collect_preamble=True)
    frags = sorted(FRAGS.glob("*.md")) if FRAGS.is_dir() else []
    for frag in frags:
        _, more = parse(frag.read_text(), collect_preamble=False)
        if not more:
            print(f"warn: {frag.name} contains no entries")
        dup = sorted(more.keys() & entries.keys())
        if dup:
            sys.exit(f"duplicate IDs, already in SOURCES.md and also in {frag.name}: {dup}")
        entries.update(more)
    return text, preamble, entries, frags


def unplaced(entries: dict[int, str]) -> list[int]:
    """The IDs outside every block of the README table."""
    table = blocks()
    return sorted(sid for sid in entries if not any(lo <= sid <= hi for lo, hi, _ in table))


def render(preamble: str, entries: dict[int, str]) -> str:
    """SOURCES.md text: the preamble, then each block's entries sorted by ID."""
    table = blocks()
    out = [preamble, ""]
    for lo, hi, title in table:
        block_ids = sorted(sid for sid in entries if lo <= sid <= hi)
        if block_ids:
            out += [f"## {title}", ""]
            for sid in block_ids:
                out += [entries[sid], ""]
    return "\n".join(out).rstrip() + "\n"


def markdown(tree: Path) -> list[Path]:
    """Every .md file under `tree`, without walking research/clones."""
    found: list[Path] = []
    for child in sorted(tree.iterdir()):
        if child.is_dir() and child != CLONES:
            found += sorted(child.rglob("*.md"))
        elif child.suffix == ".md":
            found.append(child)
    return found


def unresolved(ids: set[int]) -> list[str]:
    """Every cite in research/ and docs/ that names no source."""
    found: list[str] = []
    for tree in CITING:
        for path in markdown(tree):
            for sid, _ in CITE.findall(path.read_text()):
                if int(sid) not in ids:
                    found.append(f"{path.relative_to(ROOT.parent)}: [S{sid}] names no source")
    return found


def adr_cites() -> list[tuple[int, str]]:
    """Every cite in an ADR, as (ID, what follows the colon or "")."""
    return [(int(sid), where) for adr in ADRS.glob("ADR-*.md") for sid, where in CITE.findall(adr.read_text())]


def evidence_gaps(entries: dict[int, str], cites: list[tuple[int, str]]) -> dict[str, set[int]]:
    """ADR-cited sources that break the archival rule, keyed as `LACKS`."""
    gaps: dict[str, set[int]] = {kind: set() for kind in LACKS}
    for sid in {sid for sid, _ in cites} & entries.keys():
        fields = dict(FIELD.findall(entries[sid]))
        if "pinned" in fields:
            continue
        if fields.get("type") == "code":
            gaps["pin"].add(sid)
        elif fields.get("url", "").startswith("http") and not SNAPSHOT_RE.match(fields.get("archive", "")):
            gaps["archive"].add(sid)
    return gaps


def holds(directory: Path, path: str) -> bool:
    """True if excerpt `directory` holds upstream file `path`: a file of its
    name, and a LICENSE-NOTE.md that names the whole path."""
    note = directory / "LICENSE-NOTE.md"
    named = re.compile(rf"(?<![\w./-]){re.escape(path)}(?![\w./-])")
    return (directory / PurePosixPath(path).name).is_file() and note.is_file() and bool(named.search(note.read_text()))


def excerpt_gaps(cites: list[tuple[int, str]]) -> set[str]:
    """Each file an ADR cites by line, as `S###:path`, that no excerpt
    directory of its source holds (`holds`)."""
    dirs: dict[int, list[Path]] = {}
    for d in sorted(EXCERPTS.iterdir()):
        if m := EXCERPT_DIR.match(d.name):
            dirs.setdefault(int(m.group(1)), []).append(d)
    gaps: set[str] = set()
    for sid, where in cites:
        path, anchor, _ = where.partition("#L")
        if anchor and not any(holds(d, path) for d in dirs.get(sid, [])):
            gaps.add(f"S{sid:03d}:{path}")
    return gaps


def check() -> int:
    """Print every problem; return the exit status."""
    text, preamble, entries, frags = load()
    problems = unresolved(set(entries))
    outside = unplaced(entries)
    if outside:
        problems.append(f"IDs outside every block of research/README.md: {outside}")
    elif not frags and render(preamble, entries) != text:
        problems.append("SOURCES.md is not in merged form: run --merge")
    cites = adr_cites()
    gaps = evidence_gaps(entries, cites)
    for kind, known in KNOWN_GAPS.items():
        lacks = LACKS[kind]
        problems += [f"S{sid:03d}: an ADR cites it and it has no {lacks}" for sid in sorted(gaps[kind] - known)]
        problems += [f"S{sid:03d}: is no longer missing its {lacks}; delete it from KNOWN_GAPS"
                     for sid in sorted(known - gaps[kind])]
    problems += [f"{cite}: an ADR cites its lines and no excerpt holds the file"
                 for cite in sorted(excerpt_gaps(cites))]
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"ok: {len(entries)} sources; every cite resolves; "
          f"{sum(map(len, KNOWN_GAPS.values()))} known ADR evidence gaps")
    return 0


def merge() -> int:
    """Write the merged SOURCES.md and delete the fragments; return the exit status."""
    _, preamble, entries, frags = load()
    outside = unplaced(entries)
    if outside:
        sys.exit(f"IDs outside every block of research/README.md: {outside}")
    SOURCES.write_text(render(preamble, entries))
    for frag in frags:
        frag.unlink()
    print(f"SOURCES.md: {len(entries)} entries; merged {', '.join(f.name for f in frags) or 'nothing'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check the bibliography; write nothing")
    mode.add_argument("--merge", action="store_true", help="merge the fragments into SOURCES.md")
    return check() if parser.parse_args().check else merge()


if __name__ == "__main__":
    sys.exit(main())
