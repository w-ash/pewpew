"""Resolve a pattern from a name, a path, or a search directory.

`python -m pewpew run <spec>` names its pattern through `resolve`, in this
order:

1. an explicit path — `mine.py`, `effects/mine.py`, or `mine.py:ClassName`
   when the file defines more than one `Pattern` subclass;
2. `<search_dir>/<name>.py` (`name:ClassName` works here too) when the
   runner was given `--patterns DIR`;
3. the built-in gallery by lowercased class name (`comet`, `fire`, ...).

There is no implicit search of the working directory: a bare `comet` is
always the gallery, so a stray `comet.py` next to the shell cannot shadow it.

`Source` is one read of one file: the bytes, their digest, and `load`, which
compiles *those bytes* and executes them into a fresh module object. The
bytes in hand are the only truth — never the import system's bytecode cache,
whose mtime-and-size check cannot tell two same-length saves in one second
apart, and which would leave a `__pycache__` beside the author's file. The
module is registered in `sys.modules` under a stable key (`pewpew_user.<stem>`
by default), so repeated loads — hot reload re-executes the edited file —
never grow the module table, and `inspect.getsourcefile` keeps resolving for
both the old and the new class. `importlib.reload` is deliberately not used:
it re-executes into the same module object, so a renamed class leaves both
names behind (and the single-subclass rule then trips on the author's own
rename), and for a gallery file it would rebind `pewpew.patterns.comet.Comet`
underneath `STUDY_CASES`.

Loading a Python file is arbitrary code execution by definition. That is
fine for a local dev tool driven from the shell; nothing here may ever be
reachable from the preview socket, which is unauthenticated by design
(architecture §5). For the same reason `LoadError` messages name classes
and line numbers but never a path — the CLI prefixes the path itself,
because it is the one surface that may say it. A `SyntaxError` is
reformatted without its filename; other exceptions raised while executing
the file are reported as `Type: message`, which is the same residual leak
`PatternError.__str__` already accepts from a pattern's own exceptions.
"""

from __future__ import annotations

import hashlib
import sys
import types
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from pewpew.pattern import Pattern, source_file_of

_MODULE_PREFIX = "pewpew_user"
_PACKAGE_DIR = Path(__file__).resolve().parent


class LoadError(ValueError):
    """The spec did not resolve to exactly one usable `Pattern` subclass.

    The message never contains a path (see the module docstring); `path` is
    the file it concerns, or None, for the one caller allowed to print it.
    """

    def __init__(self, message: str, path: Path | None = None) -> None:
        super().__init__(message)
        self.path = path


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
    def read(cls, path: Path) -> "Source":
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
        directory goes on `sys.path` so sibling imports work as they would
        for a script — a process-global side effect, accepted for a dev-tool
        entry point and skipped for files inside the pewpew package itself.
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
        previous = sys.modules.get(name)
        sys.modules[name] = module
        try:
            code = compile(self.data, str(self.path), "exec")
            exec(code, module.__dict__)
        except BaseException as exc:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
            if isinstance(exc, Exception):
                raise LoadError(describe_exception(exc), self.path) from exc
            raise
        cls = _pick(module, name, attr, self.path)
        return LoadedPattern(cls=cls, source=self.path, attr=attr, digest=self.digest)


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


def load_file(path: Path, *, attr: str | None) -> LoadedPattern:
    """`Source.read(path).load(attr)` — one read, one exec."""
    return Source.read(path).load(attr)


def from_class(cls: type) -> LoadedPattern:
    """A `LoadedPattern` for a class that was imported normally."""
    source = source_file_of(cls)
    digest = Source.read(source).digest if source is not None and source.is_file() else ""
    return LoadedPattern(cls=cls, source=source, attr=None, digest=digest)


def describe_exception(exc: BaseException) -> str:
    """`Type: message` for `exc`, with a SyntaxError's filename dropped.

    A `LoadError` is already in that form, so it passes through unprefixed.
    """
    if isinstance(exc, LoadError):
        return str(exc)
    if isinstance(exc, SyntaxError):
        where = f" (line {exc.lineno})" if exc.lineno is not None else ""
        return f"SyntaxError: {exc.msg}{where}"
    text = str(exc)
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _split_spec(spec: str) -> tuple[str, str | None]:
    """`name:Attr` -> (name, Attr); anything else -> (spec, None)."""
    head, sep, tail = spec.rpartition(":")
    if sep and head and tail.isidentifier():
        return head, tail
    return spec, None


def _looks_like_path(text: str) -> bool:
    return "/" in text or text.endswith(".py")


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


def _gallery(name: str) -> LoadedPattern:
    # Imported here, not at module top: `pewpew.patterns` imports the engine,
    # and the engine must not import the gallery.
    import pewpew.patterns as gallery

    # Pattern subclasses only: the gallery's __all__ is its public API, which
    # is wider than its runnable patterns (`STUDY_CASES` is in it).
    by_name = {
        cls_name.lower(): obj
        for cls_name in gallery.__all__
        if isinstance(obj := getattr(gallery, cls_name), type) and issubclass(obj, Pattern)
    }
    try:
        cls = by_name[name.lower()]
    except KeyError:
        raise LoadError(
            f"unknown pattern {name!r}; available: {', '.join(sorted(by_name))}"
        ) from None
    return from_class(cls)
