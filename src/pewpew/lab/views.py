"""What an agent reads off a render: a contact sheet, several renders in
numbered rows, and the metrics with liveness on request. Thin over pewpew.sheet, pewpew.metrics and
pewpew.lab.liveness; the frames come back through `take`.

A sheet's PNG goes into the render's cache folder, or to `out`; `Picture`
says where, never holding the bytes, so a result stays small JSON.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pewpew.jsonfile import write_atomic
from pewpew.lab.handles import Cache
from pewpew.lab.liveness import KnobProbe, dead, probe_knobs, unprobed
from pewpew.lab.rendering import Rendered, restage, take
from pewpew.metrics import Metrics, measure
from pewpew.result import Result
from pewpew.sheet import Sheet, contact_sheet, rows_sheet


@dataclass(frozen=True)
class Picture(Result):
    """A contact sheet written as a PNG: the handles of the renders it
    shows, where the file is, its size in px, its layout, and how to read
    it."""

    handles: tuple[str, ...]
    path: str
    width: int
    height: int
    layout: str
    legend: str


@dataclass(frozen=True)
class Measured(Result):
    """The metrics of one render's frames and, when asked for, the liveness
    of each knob (None when not measured)."""

    handle: str
    metrics: Metrics
    liveness: tuple[KnobProbe, ...] | None = None

    @property
    def dead(self) -> tuple[str, ...]:
        """The knobs whose probe did not change the picture."""
        return dead(self.liveness or ())

    @property
    def unprobed(self) -> tuple[str, ...]:
        """Each probe that could not run, as "<path>: <why>"."""
        return unprobed(self.liveness or ())


def sheet(
    source: Rendered | str,
    layout: str = "auto",
    tiles: int = 8,
    width: int = 1024,
    *,
    out: Path | None = None,
    cache: Cache | None = None,
) -> Picture:
    """A contact sheet (pewpew.sheet.contact_sheet) of `source`, a render
    or its handle, written to `out` or into the render's cache folder.
    Raises Expired, ValueError for a bad layout, tiles or width, and
    OSError when the file cannot be written."""
    cache = cache if cache is not None else Cache()
    got = take(source, cache)
    drawn = contact_sheet(got.frames, got.geometry.mapping, got.spec.fps, layout=layout, tiles=tiles, width=width)
    return picture((got.handle,), drawn, out or cache.path(got.handle, f"sheet-{layout}-{tiles}-{width}.png"))


def rows(
    sources: Sequence[Rendered | str],
    layout: str = "auto",
    tiles: int = 2,
    width: int = 1024,
    *,
    out: Path | None = None,
    cache: Cache | None = None,
) -> Picture:
    """`sources` (renders or handles, up to eight of one shape) in one
    sheet, in rows numbered 1 to n in their order
    (pewpew.sheet.rows_sheet), written to `out` or into the first render's
    cache folder. Raises Expired, ValueError for renders of other shapes
    or bad sheet arguments, and OSError when the file cannot be written."""
    cache = cache if cache is not None else Cache()
    got = [take(source, cache) for source in sources]
    if not got:
        raise ValueError("a sheet of rows takes at least one render")
    drawn = rows_sheet([g.frames for g in got], got[0].geometry.mapping, got[0].spec.fps, layout=layout, tiles=tiles,
                       width=width)
    handles = tuple(g.handle for g in got)
    digest = hashlib.sha256(" ".join(handles).encode()).hexdigest()[:12]
    return picture(handles, drawn, out or cache.path(handles[0], f"rows-{digest}-{layout}-{tiles}-{width}.png"))


def metrics(source: Rendered | str, *, liveness: bool = False, cache: Cache | None = None) -> Measured:
    """The metrics of `source`, a render or its handle, and with
    `liveness` each knob's liveness (`probe_knobs`), which renders
    the look again per probe. Raises Expired."""
    got = take(source, cache)
    probes = probe_knobs(restage(got.spec), got.geometry, got.spec.seed) if liveness else None
    return Measured(got.handle, measure(got.frames, got.spec.fps), probes)


def picture(handles: tuple[str, ...], drawn: Sheet, path: Path) -> Picture:
    """`drawn` written to `path`, as a Picture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, drawn.png)
    return Picture(handles, str(path), drawn.width, drawn.height, drawn.layout, drawn.legend)
