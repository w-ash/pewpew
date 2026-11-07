"""The agent service (ADR-023): check, render, measure, compare and explain
looks offline, as plain functions over plain values.

The command line (`python -m pewpew fx ...`, `verify looks`;
pewpew.lab.cli) and the MCP server are thin adapters over these functions:

- `check_look(doc)` -> `Check`: the problems of a looks file or a single
  look (pewpew.problems), or the look normalized. Never raises.
- `render(look, map_spec, seconds, fps, seed)` -> `Rendered`: a handle,
  the spec it hashes, the metrics and warnings; the frames stay in the
  render cache (pewpew.lab.handles), never in the result.
- `sheet(rendered_or_handle)` -> `Picture`, a contact sheet as a PNG file;
  `metrics(rendered_or_handle, liveness=False)` -> `Measured`.
- `compare(a, b)` -> `Comparison` and `compare_sheet(a, b)` -> `Picture`.
- `explain(look)` -> `Explanation`, a look in words.
- `catalog(kind, query, detail, cursor)` -> `CatalogPage`, one page of a
  catalog search (pewpew.fx.catalog), and `describe(kind, name)` one whole
  record.
- `verify_looks(paths)` -> `Verification`, the content gate.
- `vary(look | None, seed, n, strength, keep, map_spec)` -> `Variations`:
  looks made from a seed, or like a look (pewpew.fx.surprise), each a
  rendered `Candidate`; `rows(handles)` -> `Picture` draws renders in
  numbered rows.

Every result is a frozen dataclass whose `to_json()` is its JSON form, so
`--json` output and an MCP tool's structured content are one object. A
result returned whole is not slotted (an MCP server reads its defaults off
the class); values inside one may be. A look that cannot run raises
`Refused` with its problems, and a handle the cache no longer holds
`Expired`, whose text says how to recover. The only I/O is the render
cache and a sheet written where it is asked for.
"""

from __future__ import annotations

from pewpew.lab.check import Check, LookDoc, check_look
from pewpew.lab.comparison import Change, Comparison, compare, compare_sheet
from pewpew.lab.explanation import Explanation, LayerNote, SignalNote, explain
from pewpew.lab.handles import Expired
from pewpew.lab.liveness import KnobProbe
from pewpew.lab.rendering import Rendered, RenderSpec, render
from pewpew.lab.search import CatalogItem, CatalogPage, catalog, describe
from pewpew.lab.variations import Candidate, Variations, vary
from pewpew.lab.verify import FileVerdict, LookVerdict, Verification, verify_looks
from pewpew.lab.views import Measured, Picture, metrics, rows, sheet
from pewpew.problems import Code, Problem, Refused

__all__ = [
    "Candidate", "CatalogItem", "CatalogPage", "Change", "Check", "Code", "Comparison", "Expired", "Explanation",
    "FileVerdict", "KnobProbe", "LayerNote", "LookDoc", "LookVerdict", "Measured", "Picture", "Problem", "Refused",
    "RenderSpec", "Rendered", "SignalNote", "Variations", "Verification", "catalog", "check_look", "compare",
    "compare_sheet", "describe", "explain", "metrics", "render", "rows", "sheet", "vary", "verify_looks",
]
