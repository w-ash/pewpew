"""Resolve a pattern from a name or a path.

`resolve` tries, in order: an explicit path (`mine.py`, `effects/mine.py`,
`mine.py:ClassName`); `<search_dir>/<name>.py` (`name:ClassName` too); the
gallery by lowercased class name. The working directory is never searched,
so a stray `comet.py` cannot shadow the gallery's.

`Source.load` compiles the bytes in hand into a fresh module under a stable
`sys.modules` key (`pewpew_user.<stem>`): no bytecode cache (its mtime check
misses two same-length saves in one second), no `__pycache__` beside the
author's file, and no `importlib.reload`, which keeps a renamed class's old
name in the module.

Loading a file runs its code, so nothing here is reachable from the preview
socket (architecture §5). `LoadError` messages never name a path; the CLI
adds it.
"""

from __future__ import annotations

import hashlib
import sys
import types
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from pewpew.classinfo import pattern_name, source_file_of
from pewpew.errors import LoadError, describe_exception, unknown
from pewpew.pattern import Pattern

if TYPE_CHECKING:
    from pewpew.fx.op import Op

_MODULE_PREFIX = "pewpew_user"
_PACKAGE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class LoadedPattern:
    """One resolved pattern class and where it came from.

    `source` is the file that defines it (None for a class with no source,
    such as one built in a REPL); `attr` is the explicit `:ClassName` from
    the spec, or None when the single-subclass rule chose; `digest` is the
    SHA-256 of the source bytes, the unit hot reload uses to skip a no-op
    save.
    """

    cls: type
    source: Path | None
    attr: str | None
    digest: str


@dataclass(frozen=True)
class Source:
    """The bytes of one pattern file at one moment, and how to run them."""

    path: Path
    data: bytes

    @classmethod
    def read(cls, path: Path) -> Source:
        """One read. Raises `FileNotFoundError`/`OSError` as the filesystem does."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"no such pattern file: {path}")
        return cls(path, path.read_bytes())

    @cached_property
    def digest(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def load(self, attr: str | None = None) -> LoadedPattern:
        """Execute these bytes as a fresh module and pick the pattern class.

        `attr` names the class when the file defines several; otherwise the
        file must define exactly one `Pattern` subclass of its own (a base
        imported from a sibling module does not count). A user file's
        directory goes on `sys.path`, so sibling imports work as for a script.
        """
        name = f"{_MODULE_PREFIX}.{self.path.stem}"
        if not _inside_package(self.path):
            parent = str(self.path.parent.resolve())
            if parent not in sys.path:
                sys.path.insert(0, parent)
        module = types.ModuleType(name)
        module.__file__ = str(self.path)
        # Registered before execution: `dataclasses` and `inspect` look a
        # class's module up by name while the body runs. Put back if the body
        # fails, so a half-executed module never shadows the last good one.
        # The ops the file defines register as their class statements run
        # (pewpew.fx.op), so a load that fails puts the op registry back too.
        previous = sys.modules.get(name)
        ops = _op_registry()
        before = dict(ops)
        sys.modules[name] = module
        try:
            code = compile(self.data, str(self.path), "exec")
            exec(code, module.__dict__)  # noqa: S102  runs the author's pattern file
        except BaseException as exc:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
            _put_back(ops, before)
            if isinstance(exc, Exception):
                raise LoadError(describe_exception(exc), self.path) from exc
            raise
        try:
            cls = _pick(module, name, attr, self.path)
        except LoadError:
            _put_back(ops, before)
            raise
        return LoadedPattern(cls=cls, source=self.path, attr=attr, digest=self.digest)


def _op_registry() -> dict[str, type[Op]]:
    """The effect ops registered, by name (pewpew.fx.op.REGISTRY)."""
    from pewpew.fx.op import REGISTRY  # imported here: a pattern file without ops needs no effects engine

    return REGISTRY


def _put_back(ops: dict[str, type[Op]], before: dict[str, type[Op]]) -> None:
    ops.clear()
    ops.update(before)


def resolve(spec: str, *, search_dir: Path | None = None) -> LoadedPattern:
    """Resolve `spec` per the module docstring's order.

    Raises `LoadError` for a file that does not define exactly one usable
    pattern (or an unknown gallery name, naming the gallery) and
    `FileNotFoundError` for a path, or a `search_dir`, that does not exist.
    """
    if search_dir is not None:
        search_dir = Path(search_dir)
        if not search_dir.is_dir():
            raise FileNotFoundError(f"no such patterns directory: {search_dir}")
    name, attr = _split_spec(spec)
    if _looks_like_path(name):
        return load_file(Path(name), attr=attr)
    if search_dir is not None:
        candidate = search_dir / f"{name}.py"
        if candidate.is_file():
            return load_file(candidate, attr=attr)
    if attr is not None:
        raise LoadError(f"':{attr}' only applies to a file; {name!r} is not one")
    return _gallery(name)


def names(search_dir: Path | None = None) -> list[str]:
    """The bare names `resolve` accepts, sorted: the gallery's and, when
    given, `search_dir`'s `<name>.py` files.

    A name that is in both appears once; `resolve` picks the file. Names
    only, never paths: this list is what the preview's pattern picker
    offers, and a pick is accepted only if it is on the list. A missing
    `search_dir` adds nothing.
    """
    found = set(gallery())
    if search_dir is not None and Path(search_dir).is_dir():
        found.update(
            f.stem for f in Path(search_dir).glob("*.py")
            if f.stem.isidentifier() and not f.stem.startswith("_") and f.is_file()
        )
    return sorted(found)


class Catalog:
    """The patterns a run starts by name: `names(search_dir)`, kept until
    `rescan`, and the command line's pattern `launch` by its spec, which may
    be a path; a path to a `search_dir` file goes by that file's name. Any
    other name off the list never resolves, which is what keeps a path that
    came over the preview socket from ever reaching `resolve`."""

    def __init__(self, search_dir: Path | None = None, launch: str | None = None) -> None:
        self.search_dir = search_dir
        # Replaced whole by `rescan`; read by sink workers.
        self.names: list[str] = names(search_dir)
        self.launch = None if launch is None else self._listed(launch)

    def _listed(self, spec: str) -> str:
        """`spec`, or the name on the list of the `search_dir` file it is."""
        path, attr = _split_spec(spec)
        if attr is None and self.search_dir is not None and _looks_like_path(path):
            stem = Path(path).stem
            if stem in self.names and Path(path).resolve() == (Path(self.search_dir) / f"{stem}.py").resolve():
                return stem
        return spec

    def rescan(self) -> None:
        """Read the names again (a file added to `search_dir` since launch)."""
        self.names = names(self.search_dir)

    def offers(self, name: str) -> bool:
        """Whether `resolve` takes `name` without reading the list again."""
        return name == self.launch or name in self.names

    def resolve(self, name: str) -> LoadedPattern:
        """`resolve(name)` for a name it `offers`, read again first when the
        name is missing (a file added since the last read); LoadError for
        any other, which names no path."""
        if not self.offers(name):
            self.rescan()
            if not self.offers(name):
                if is_path(name):
                    raise LoadError("its pattern is a file this run was not started with")
                raise LoadError(unknown("pattern", name, self.names))
        return resolve(name, search_dir=self.search_dir)


def load_file(path: Path, *, attr: str | None) -> LoadedPattern:
    """`Source.read(path).load(attr)` — one read, one exec."""
    return Source.read(path).load(attr)


def from_class(cls: type) -> LoadedPattern:
    """A `LoadedPattern` for a class that was imported normally."""
    source = source_file_of(cls)
    digest = Source.read(source).digest if source is not None and source.is_file() else ""
    return LoadedPattern(cls=cls, source=source, attr=None, digest=digest)


def _split_spec(spec: str) -> tuple[str, str | None]:
    """`name:Attr` -> (name, Attr); anything else -> (spec, None)."""
    head, sep, tail = spec.rpartition(":")
    if sep and head and tail.isidentifier():
        return head, tail
    return spec, None


def _looks_like_path(text: str) -> bool:
    return "/" in text or text.endswith(".py")


def is_path(spec: str) -> bool:
    """Whether `spec` names a file (`mine.py`, `effects/mine`,
    `mine.py:Mine`) rather than a pattern by its name."""
    return _looks_like_path(_split_spec(spec)[0])


def _inside_package(path: Path) -> bool:
    return _PACKAGE_DIR in path.resolve().parents


def _pick(module: object, module_name: str, attr: str | None, path: Path) -> type:
    if attr is not None:
        cls = getattr(module, attr, None)
        if not (isinstance(cls, type) and issubclass(cls, Pattern) and cls is not Pattern):
            raise LoadError(f"{attr!r} is not a Pattern subclass defined in the file", path)
        return cls
    own = [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type)
        and issubclass(obj, Pattern)
        and obj is not Pattern
        and obj.__module__ == module_name
    ]
    if not own:
        raise LoadError("no Pattern subclass is defined in the file", path)
    if len(own) > 1:
        names = ", ".join(sorted(c.__name__ for c in own))
        raise LoadError(
            f"the file defines {len(own)} Pattern classes ({names}); pick one with :ClassName",
            path,
        )
    return own[0]


def gallery() -> dict[str, type]:
    """The gallery's patterns by name (lowercased class name), in the
    gallery's order."""
    # Imported on first use: the gallery brings every pattern and the room
    # compiler, which loading a pattern file does not need.
    import pewpew.patterns as gallery

    # `__all__` also holds the gallery's helpers (`STUDY_CASES`, ...).
    return {
        pattern_name(obj): obj
        for cls_name in gallery.__all__
        if isinstance(obj := getattr(gallery, cls_name), type) and issubclass(obj, Pattern)
    }


def _gallery(name: str) -> LoadedPattern:
    by_name = gallery()
    try:
        cls = by_name[name.lower()]
    except KeyError:
        raise LoadError(unknown("pattern", name, sorted(by_name))) from None
    return from_class(cls)
