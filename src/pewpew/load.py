"""The gallery's patterns by name: what a look's `pattern` node runs.

A pattern runs by its gallery name alone (ADR-025): nothing here reads a
file. `Catalog` holds the names a run offers and resolves each; the
gallery's by default, or a test's own classes.
"""

from __future__ import annotations

from collections.abc import Mapping

from pewpew.classinfo import pattern_name
from pewpew.errors import LoadError, unknown
from pewpew.pattern import Pattern


def gallery() -> dict[str, type]:
    """The gallery's patterns by name (lowercased class name), in the
    gallery's order."""
    # Imported on first use: the gallery brings every pattern and the room compiler.
    from pewpew import patterns

    # `__all__` also holds the gallery's helpers (`STUDY_CASES`, ...).
    return {
        pattern_name(obj): obj
        for cls_name in patterns.__all__
        if isinstance(obj := getattr(patterns, cls_name), type) and issubclass(obj, Pattern)
    }


def resolve(name: str) -> type:
    """The gallery pattern `name`. Raises LoadError, naming the gallery."""
    return Catalog().resolve(name)


class Catalog:
    """Patterns by name: the gallery's, or `classes`. A name off the list
    never resolves."""

    def __init__(self, classes: Mapping[str, type] | None = None) -> None:
        self._classes = dict(gallery() if classes is None else classes)
        self.names: list[str] = sorted(self._classes)

    def resolve(self, name: str) -> type:
        """The pattern `name`. Raises LoadError, naming the list."""
        try:
            return self._classes[name]
        except KeyError:
            raise LoadError(unknown("pattern", name, self.names)) from None
