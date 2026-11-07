"""What pewpew's JSON files share: the room map (`pewpew.room.map`),
the saved looks (`pewpew.aura.book`), and the JSONL logs of runs (the
trigger log, `pewpew.aura.triggers`, and the feature log,
`pewpew.audio.features`).

Each loader collects every problem before it refuses, and no message names
a path, so the same text can cross the preview socket as a reload status.
Every rewrite goes through `write_atomic`.
"""

from __future__ import annotations

import json
import math
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeGuard, TypeVar

T = TypeVar("T")


class ProblemsError(ValueError):
    """A file's content is malformed. `problems` lists every reason; the
    message joins them on one line. No message contains a path."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = list(problems)


class _Repeated(Exception):
    """An object that names one key twice."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def _once(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """An object's pairs as a dict, each key once: JSON parsers keep the
    last of a repeated key, so a copied node or look would replace the
    first without a word."""
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _Repeated(key)
        out[key] = value
    return out


def parse_json(data: bytes | str, error: type[ProblemsError]) -> Any:
    """`data` parsed as JSON. Raises `error` with one problem if it is not,
    or if an object names a key twice."""
    try:
        return json.loads(data, object_pairs_hook=_once)
    except _Repeated as exc:
        raise error([f"duplicate key {exc.key!r}: an object names each key once, so give each its own name"]) from None
    except json.JSONDecodeError as exc:
        raise error([f"invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"]) from None
    except UnicodeDecodeError:
        raise error(["invalid JSON: the file is not UTF-8 text"]) from None
    except ValueError:  # an integer past Python's digit limit (sys.get_int_max_str_digits)
        raise error(["invalid JSON: a number has too many digits"]) from None


def read_or_exit(path: Path, noun: str, load: Callable[[], T]) -> T:
    """`load()`, with any failure to read `path` turned into one clean exit
    line naming the file, and a malformed file into one line per problem
    under it. For the command line only: the message names the path."""
    try:
        return load()
    except OSError as exc:
        raise SystemExit(f"{path}: cannot read the {noun}: {exc.strerror or exc}") from None
    except ProblemsError as exc:
        if len(exc.problems) == 1:
            raise SystemExit(f"{path}: {exc}") from None
        raise SystemExit("\n  ".join([f"{path}:", *exc.problems])) from None


def is_number(value: object) -> TypeGuard[int | float]:
    """Whether `value` is a finite int or float, and not a bool."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # a JSON integer past float's range
        return False


def temp_beside(path: Path) -> Path:
    """A hidden temporary path in the directory of `path`, its own for this
    process and thread, so two writers of `path` never share one."""
    return path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")


def write_atomic(path: Path, data: bytes, *, mode: int = 0o666) -> None:
    """Replace `path` with `data` so that a crash leaves the old file or the
    new one whole. The temporary file sits in the same directory, because a
    rename is atomic only within one file system. `mode` is the new file's
    permissions before the umask: 0o600 keeps a secret to its owner from the
    first byte."""
    path = Path(path)
    tmp = temp_beside(path)
    try:
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def read_run(path: Path, run: int = -1) -> list[dict]:
    """The records of one run of a JSONL log, in order, its header first:
    each run starts with a `{"run": {...}}` record, so a log that spans
    restarts separates its runs. `run` indexes the runs as a list does: -1
    (the default) is the last, 0 the first. Records before the first
    header count as one run. Raises IndexError for a run the log does not
    hold, and ValueError for a line that is not a JSON object."""
    runs: list[list[dict]] = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"line {n} is not a JSON object")  # noqa: TRY004  a bad file, not a caller error
            if "run" in record or not runs:
                runs.append([])
            runs[-1].append(record)
    return (runs or [[]])[run]
