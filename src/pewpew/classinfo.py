"""What the engine reads off a pattern class: its name, what it does and
its source file. Imports nothing from pewpew, so every layer can use it."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


def pattern_name(pattern_cls: type) -> str:
    """The name of a pattern class: its class name, lowercased. The gallery
    goes by it (pewpew.load)."""
    return pattern_cls.__name__.lower()


def pattern_summary(pattern_cls: type) -> str:
    """What a pattern class does, in one sentence: the first sentence of
    its docstring, else of its module's (the gallery's convention), else ""."""
    module = sys.modules.get(pattern_cls.__module__)
    for doc in (pattern_cls.__doc__, getattr(module, "__doc__", None)):
        if doc and doc.strip():
            return first_sentence(" ".join(doc.strip().split("\n\n")[0].split()))
    return ""


def first_sentence(paragraph: str) -> str:
    """The first sentence of `paragraph`, a line of words: up to the first
    ". ", or all of it."""
    head, stop, _ = paragraph.partition(". ")
    return head + "." if stop else paragraph


def source_file_of(cls: type) -> Path | None:
    """The file `cls` was defined in, or None for a class with no source
    (built dynamically, REPL, `python -c`)."""
    try:
        file = inspect.getsourcefile(cls)
    except (TypeError, OSError):
        return None
    return Path(file) if file else None
