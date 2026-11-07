"""research/tools/merge_sources.py: the archival gate's excerpt check
matches a line-anchored cite to the upstream path its excerpt records."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

TOOLS = Path(__file__).parents[1] / "research" / "tools"


@pytest.fixture
def merge_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    """The tool, reading excerpt directories from `tmp_path`."""
    monkeypatch.syspath_prepend(str(TOOLS))  # its sibling import, retry_archives
    module = importlib.import_module("merge_sources")
    monkeypatch.setattr(module, "EXCERPTS", tmp_path)
    return module


def excerpt(root: Path, name: str, file: str, note: str) -> None:
    directory = root / name
    directory.mkdir()
    (directory / file).write_text("verbatim\n")
    (directory / "LICENSE-NOTE.md").write_text(note)


def test_a_cite_is_held_only_where_the_note_names_its_upstream_path(merge_sources: ModuleType, tmp_path: Path):
    excerpt(tmp_path, "S630-effects", "__init__.py", "| `__init__.py` | `ledfx/effects/__init__.py` | 1-9 | why |\n")
    excerpt(tmp_path, "S645-ingest", "wled.h", "- excerpted path: wled00/wled.h#L451\n")
    excerpt(tmp_path, "S600-device", "LICENSE", "- license: MIT (LICENSE.txt in the repo root)\n")
    cites = [
        (630, "ledfx/effects/__init__.py#L1-L9"),
        (630, "ledfx/effects/__init__.py"),  # no line anchor: no excerpt needed
        (645, "wled00/wled.h#L451"),
        (630, "ledfx/devices/__init__.py#L1-L9"),  # same file name, another upstream file
        (645, "wled00/sub/wled.h#L1"),
        (600, "LICENSE#L1-L3"),  # the note names LICENSE.txt, not LICENSE
        (700, "src/a.cpp#L1"),  # no excerpt directory at all
    ]
    assert merge_sources.excerpt_gaps(cites) == {
        "S630:ledfx/devices/__init__.py",
        "S645:wled00/sub/wled.h",
        "S600:LICENSE",
        "S700:src/a.cpp",
    }


def test_a_note_that_names_the_path_without_the_file_holds_nothing(merge_sources: ModuleType, tmp_path: Path):
    excerpt(tmp_path, "S645-ingest", "udp.cpp", "| `udp.cpp` | `wled00/udp.cpp` |\n| `wled.h` | `wled00/wled.h` |\n")
    assert merge_sources.excerpt_gaps([(645, "wled00/udp.cpp#L1"), (645, "wled00/wled.h#L1")]) == {"S645:wled00/wled.h"}
