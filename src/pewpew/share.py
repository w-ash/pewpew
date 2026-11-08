"""The share envelope: a layout and the looks to show on it, as the Gallery stores it.

    {"format": "pewpew.share", "version": 1, "arrangement": {...}, "looks": {...}}

`arrangement` is an arrangement with no `controllers[].host` and no `plan`:
a share never names a board's address or holds the floor-plan image.
`looks` is a looks file, version 4 (`pewpew.aura.book`), of the chosen
looks only, with no `triggers` and no `notes`. Its `current` is the book's
current look when it is chosen, else the first chosen.

`envelope` makes one from a running layout and its looks book; `check`
reads one a client sent and refuses it with every problem
(`ShareError`). The Console's Publish posts an envelope to the Gallery,
which checks it, stores it under its content id (`content_id` of
`canonical_json`) and serves it at `/a/{id}`. `read` turns a stored row
into an envelope: a row is an envelope, or an older bare arrangement,
which opens with the example looks.

Imports nothing of `pewpew.rig`, so a run that does not use a rig loads
none of it.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from pewpew.aura.book import LookBook, LookError, parse_looks
from pewpew.lab.check import ready
from pewpew.problems import Refused
from pewpew.studio.limits import MAX_BODY_BYTES, MAX_FIXTURES, declared_fixtures, oversized_list

FORMAT = "pewpew.share"
VERSION = 1
ARRANGEMENT = "pewpew.arrangement"  # the `format` of an arrangement, and of an old stored row
_KEYS = {"format", "version", "arrangement", "looks"}


class ShareError(ValueError):
    """A share that does not check: `problems` lists every reason."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text: sorted keys, compact. Raises `ValueError` on NaN or infinity."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_id(canonical: str) -> str:
    """The id of `canonical` text: the first 128 bits of its SHA-256,
    base64url with no padding (22 characters). The same text always gets
    the same id."""
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()[:16]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def stripped(arrangement: Mapping[str, Any]) -> dict[str, Any]:
    """`arrangement` with no `plan` and no `host` on any controller. Keeps
    a controller that is not an object as it is, for the compiler to refuse."""
    out = {key: value for key, value in arrangement.items() if key != "plan"}
    controllers = out.get("controllers")
    if isinstance(controllers, list):
        out["controllers"] = [
            {k: v for k, v in c.items() if k != "host"} if isinstance(c, dict) else c for c in controllers
        ]
    return out


def chosen(book: LookBook, names: Iterable[str]) -> LookBook:
    """The book of looks `names` alone, in the book's order, with no
    triggers and no notes. The cycle and the favorites drop the other looks
    as `LookBook.without` does. `current` is the book's when chosen, else
    the first chosen. Every name must be a look of `book`."""
    keep = set(names)
    out = book
    for name in book.looks:
        if name not in keep:
            out = out.without(name)
    first = next(iter(out.looks), None)
    current = book.current if book.current in out.looks else first
    return replace(out, triggers={}, notes=None).with_current(current)


def looks_file(book: LookBook, names: Iterable[str]) -> dict[str, Any]:
    """The looks file of `chosen(book, names)`, as JSON values."""
    return json.loads(chosen(book, names).to_bytes())


def envelope(arrangement: Mapping[str, Any], book: LookBook, names: Iterable[str]) -> dict[str, Any]:
    """The share of `arrangement` with looks `names` of `book`, stripped
    (`stripped`, `chosen`). It is not checked: see `check`."""
    return {"format": FORMAT, "version": VERSION, "arrangement": stripped(arrangement),
            "looks": looks_file(book, names)}


def check(
    doc: object, *, max_bytes: int = MAX_BODY_BYTES, max_fixtures: int = MAX_FIXTURES,
) -> tuple[dict[str, Any], LookBook]:
    """The checked envelope of `doc` (parsed JSON) and its looks book.

    It is stripped again, and its looks file is written again from the
    parsed book, so a stored share has no host, plan, trigger or note. The
    canonical text is at most `max_bytes`; the arrangement declares at
    most `max_fixtures` fixtures and has no list or object longer than
    that; the looks file parses (its own limits: `MAX_LOOKS`, ...) and each
    look is ready to run (`pewpew.lab.check.ready`). Does not compile the
    arrangement. Raises ShareError with every problem it finds."""
    if not isinstance(doc, dict):
        raise ShareError([f'a share is a JSON object with "format": "{FORMAT}"'])
    try:
        size = len(canonical_json(doc).encode("utf-8"))
    except ValueError:
        raise ShareError(["a share is plain JSON: no NaN or infinity"]) from None
    if size > max_bytes:
        raise ShareError([f"a share is at most {max_bytes} bytes; this one is {size}"])
    problems = [f"unknown key {key!r}; expected {', '.join(sorted(_KEYS))}" for key in sorted(set(doc) - _KEYS)]
    if doc.get("format") != FORMAT or doc.get("version") != VERSION:
        problems.append(f'a share has "format": "{FORMAT}" and "version": {VERSION}')
    arrangement = doc.get("arrangement")
    if not isinstance(arrangement, dict):
        problems.append("'arrangement' is an arrangement object")
    elif declared_fixtures(arrangement, max_fixtures) > max_fixtures:
        problems.append(f"limit of {max_fixtures} fixtures per arrangement")
    elif (too_long := oversized_list(arrangement, max_fixtures)) is not None:
        problems.append(f"limit of {max_fixtures} entries in a list ({too_long})")
    looks = doc.get("looks")
    book = None
    file: dict[str, Any] = {}
    if not isinstance(looks, dict):
        problems.append("'looks' is a looks file object")
    else:
        try:
            book = parse_looks(json.dumps({k: v for k, v in looks.items() if k not in ("triggers", "notes")}))
        except LookError as exc:
            problems.extend(f"looks: {problem}" for problem in exc.problems)
    if book is not None:
        book = chosen(book, book.looks)
        if not book.looks:
            problems.append("a share holds at least one look")
        file = json.loads(book.to_bytes())
        problems.extend(_unready(file))
    if problems:
        raise ShareError(problems)
    assert isinstance(arrangement, dict) and book is not None
    return {"format": FORMAT, "version": VERSION, "arrangement": stripped(arrangement), "looks": file}, book


def _unready(file: Mapping[str, Any]) -> list[str]:
    """Why each look of the looks file `file` is not ready to run, by its name."""
    found = []
    for name, doc in file["looks"].items():
        try:
            ready(doc)
        except Refused as exc:
            found.append(f"look {name!r}: {exc}")
    return found


def read(text: str, examples: LookBook) -> tuple[dict[str, Any], LookBook]:
    """The envelope of a stored row and its looks book. A row is an
    envelope, stored checked, or an older bare arrangement (`format`
    `pewpew.arrangement`), which gets the looks of `examples`. Raises
    ValueError for a row that is neither."""
    doc = json.loads(text)
    kind = doc.get("format") if isinstance(doc, dict) else None
    if kind == FORMAT:
        return doc, parse_looks(json.dumps(doc["looks"]))
    if kind == ARRANGEMENT:
        return envelope(doc, examples, examples.looks), chosen(examples, examples.looks)
    raise ValueError(f"a stored share has format {FORMAT!r} or {ARRANGEMENT!r}")
