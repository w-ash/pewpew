"""What the engine reads off a class (an op, a param set's owner): its
name and what it does. Imports nothing from pewpew, so every layer can use it."""

from __future__ import annotations


def lowercase_name(cls: type) -> str:
    """The name of `cls`, lowercased."""
    return cls.__name__.lower()


def docstring_summary(cls: type) -> str:
    """What a class does, in one sentence: the first sentence of its
    docstring, else ""."""
    doc = (cls.__doc__ or "").strip()
    return first_sentence(" ".join(doc.split("\n\n")[0].split())) if doc else ""


def first_sentence(paragraph: str) -> str:
    """The first sentence of `paragraph`, a line of words: up to the first
    ". ", or all of it."""
    head, stop, _ = paragraph.partition(". ")
    return head + "." if stop else paragraph
