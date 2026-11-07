"""Searching the catalog (pewpew.fx.catalog) a page at a time, as an agent
reads it.

`catalog` gives one page of the records of a kind whose name, label or doc
holds every word of a query, and `index` every record on one page. An item
is concise by default: its kind (`op`, `blend`, `palette` or
`kind`), name, label, first sentence, and an op's signature. With
`detail="detailed"` each item also holds its whole record, params and
examples included. A page holds at most `PAGE[detail]` items and ends with
the cursor of the next page, or None after the last. `describe` gives one
whole record by its kind and name.

A kind, cursor or name that does not exist raises Refused with one coded
problem (pewpew.problems): its path is the argument refused, and it
carries a did-you-mean and the valid values.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, get_args

from pewpew.errors import did_you_mean, unknown
from pewpew.fx import catalog as book
from pewpew.problems import EXAMPLE_LOOK, Code, Problem, Refused
from pewpew.result import Result

Detail = Literal["concise", "detailed"]
DETAILS: tuple[Detail, ...] = get_args(Detail)
# Items per page: a detailed record holds its params and examples.
PAGE: dict[Detail, int] = {"concise": 50, "detailed": 10}
# The op whose first example the example program look runs.
EXAMPLE_OP = "kaleid"


@dataclass(frozen=True, slots=True)
class CatalogItem(Result):
    """One record found: its kind, name, label, first sentence and, for an
    op, its signature (`source`, `coord`, ...); with `detail="detailed"`,
    the whole record too."""

    kind: str
    name: str
    label: str
    summary: str
    sig: str | None = None
    record: dict[str, Any] | None = None


@dataclass(frozen=True)
class CatalogPage(Result):
    """One page of a search: its items, how many items match in all, and
    the cursor of the next page (None after the last)."""

    items: tuple[CatalogItem, ...]
    total: int
    next_cursor: str | None = None


def catalog(
    kind: str | None = None, query: str | None = None, detail: Detail = "concise", cursor: str | None = None,
) -> CatalogPage:
    """One page of the records of `kind` (`pewpew.fx.catalog.KINDS`: a kind,
    or an op signature; None for all) that hold every word of `query`,
    from `cursor` (None: the first page). Raises Refused for a kind, detail
    or cursor that does not exist."""
    if kind is not None and kind not in book.KINDS:
        raise Refused([_unknown("kind", "kind", kind, book.KINDS)])
    if detail not in DETAILS:
        raise Refused([_unknown("detail", "detail", detail, DETAILS)])
    found = book.entries(book.catalog(), kind, query)
    start = _offset(cursor, len(found))
    end = start + PAGE[detail]
    page = tuple(_item(k, record, detail) for k, record in found[start:end])
    return CatalogPage(page, len(found), str(end) if end < len(found) else None)


def describe(kind: str, name: str) -> dict[str, Any]:
    """The whole record of `name`, of `kind` (a record kind,
    `pewpew.fx.catalog.RECORD_KINDS`). Raises Refused for a kind or name
    that does not exist."""
    if kind not in book.RECORD_KINDS:
        raise Refused([_unknown("kind", "kind", kind, book.RECORD_KINDS)])
    records = {book.name_of(record): record for _, record in book.entries(book.catalog(), kind)}
    if name not in records:
        raise Refused([_unknown("name", kind, name, records, Code.UNKNOWN_OP if kind == "op" else Code.BAD_REF)])
    return records[name]


def index() -> CatalogPage:
    """Every record, concise, in one page: the catalog's contents."""
    found = book.entries(book.catalog())
    return CatalogPage(tuple(_item(kind, record, "concise") for kind, record in found), len(found))


def example_looks() -> tuple[dict[str, Any], dict[str, Any]]:
    """Two looks an agent can start from: palette-colored stripes
    (`problems.EXAMPLE_LOOK`), and one layer, `base`, that runs the first
    example of op `EXAMPLE_OP`."""
    program = describe("op", EXAMPLE_OP)["examples"][0]["json"]
    return EXAMPLE_LOOK, {"layers": [{"id": "base", **program}]}


def _item(kind: str, record: dict[str, Any], detail: Detail) -> CatalogItem:
    return CatalogItem(**book.item(kind, record), record=record if detail == "detailed" else None)


def _offset(cursor: str | None, total: int) -> int:
    """Where the page that `cursor` names starts. Raises Refused for a
    cursor that no page of this search gave."""
    if cursor is None:
        return 0
    if cursor.isdigit() and 0 < int(cursor) < total:
        return int(cursor)
    reason = (f"cursor {cursor!r} is not one this search gives; pass the next_cursor of the page before, "
              "with the same kind and query, or no cursor for the first page")
    raise Refused([Problem("cursor", Code.OUT_OF_RANGE, reason)])


def _unknown(path: str, noun: str, name: str, known: Iterable[str], code: Code = Code.OUT_OF_RANGE) -> Problem:
    """The problem at argument `path` of a `noun` named `name` that is not
    one of `known`."""
    names = tuple(known)
    return Problem(path, code, unknown(noun, name, names, suggest=True), did_you_mean(name, names), names)
