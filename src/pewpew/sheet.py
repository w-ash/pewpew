"""Contact sheets: a rendered sequence as one PNG that a vision model can judge.

An agent judges motion from a sheet, not from a video. `contact_sheet`
picks a layout from the shape of the mapping (`pewpew.mapping.dimensions`):

- `strip`, for a strip (0 or 1 dimensions): a space-time image, pixels
  across in order along the strip and frames down, with a time label
  every 0.5 s;
- `grid`, for a panel (2 dimensions, and the points fill a lattice): tiles
  at evenly spaced times, each labeled like `t=1.25s`, one cell per LED;
- `splat`, for a volume or a room (3 dimensions, or 2 that do not fill a
  lattice): the same tiles, each LED a dot.

A tile shows the plane of a flat mapping, whichever two axes it spans, and
a volume seen from above, z ignored.

`compare_sheet` draws two sequences in rows labeled A and B, at the same
times, and `rows_sheet` up to eight in rows numbered 1 to 8 (two columns
of rows when one would be too tall).

Sizes follow Anthropic's vision guide (platform.claude.com, "Vision"): an
image under 200 px reads poorly, a long edge over 1568 px is scaled down,
and an image costs ⌈w/28⌉ × ⌈h/28⌉ tokens. The default sheet is about
1024 × 560, near 740 tokens. Colours are 8-bit display gamma, as the
preview shows them (`to_display_u8`), and black is an unlit LED or no LED.
Frame i is at t = (i + 1) / fps (`SlotClock`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from pewpew.errors import unknown
from pewpew.mapping import dimensions, extents
from pewpew.png import encode_png
from pewpew.render import check_frames
from pewpew.sinks.base import to_display_u8

LAYOUTS = ("auto", "strip", "grid", "splat")
_AXES = "xyz"  # axis index -> its name in a legend

MIN_TILE = 200  # px: the smallest tile a vision model reads well
MAX_EDGE = 1568  # px: the longest edge a vision model takes unscaled
# px: four tiles a row stay at MIN_TILE or more, and a strip's plot at 768
# or more, beside compare_sheet's A/B column too. 896 is 32 token columns.
MIN_WIDTH = 896
STRIP_ROWS = 512  # px of time in a strip
MIN_STRIP = 128  # px of time in a strip that shares a sheet with others, at least
MAX_ROWS = 8  # renders in one sheet of rows
TICK = 0.5  # s between a strip's time labels; doubled until the labels fit

GUTTER = 8  # px around and between tiles
SCALE = 2  # label glyphs are drawn at 2x, 10 × 14 px
LETTER_SCALE = 3  # compare_sheet's A and B
GLYPH_W, GLYPH_H = 5, 7
BAND = GLYPH_H * SCALE + 6  # px: the label band above each tile
TICK_LEN = 4  # px
PAGE = 40  # the grey behind tiles and labels
INK = 255

# The label font: 5 × 7 glyphs, one block per row of keys.
_FONT = """
0     1     2     3     4     5     6     7     8     9
.###. ..#.. .###. ##### ...#. ##### ..##. ##### .###. .###.
#...# .##.. #...# ...#. ..##. #.... .#... ....# #...# #...#
#..## ..#.. ....# ..#.. .#.#. ####. #.... ...#. #...# #...#
#.#.# ..#.. ...#. ...#. #..#. ....# ####. ..#.. .###. .####
##..# ..#.. ..#.. ....# ##### ....# #...# .#... #...# ....#
#...# ..#.. .#... #...# ...#. #...# #...# .#... #...# ...#.
.###. .###. ##### .###. ...#. .###. .###. .#... .###. .##..

A     B     C     D     E     F     G     H     I     J     K     L     M
.###. ####. .###. ###.. ##### ##### .###. #...# .###. ..### #...# #.... #...#
#...# #...# #...# #..#. #.... #.... #...# #...# ..#.. ...#. #..#. #.... ##.##
#...# #...# #.... #...# #.... #.... #.... #...# ..#.. ...#. #.#.. #.... #.#.#
#...# ####. #.... #...# ####. ####. #.### ##### ..#.. ...#. ##... #.... #.#.#
##### #...# #.... #...# #.... #.... #...# #...# ..#.. ...#. #.#.. #.... #...#
#...# #...# #...# #..#. #.... #.... #...# #...# ..#.. #..#. #..#. #.... #...#
#...# ####. .###. ###.. ##### #.... .#### #...# .###. .##.. #...# ##### #...#

N     O     P     Q     R     S     T     U     V     W     X     Y     Z
#...# .###. ####. .###. ####. .#### ##### #...# #...# #...# #...# #...# #####
#...# #...# #...# #...# #...# #.... ..#.. #...# #...# #...# #...# #...# ....#
##..# #...# #...# #...# #...# #.... ..#.. #...# #...# #...# .#.#. .#.#. ...#.
#.#.# #...# ####. #...# ####. .###. ..#.. #...# #...# #.#.# ..#.. ..#.. ..#..
#..## #...# #.... #.#.# #.#.. ....# ..#.. #...# #...# #.#.# .#.#. ..#.. .#...
#...# #...# #.... #..#. #..#. ....# ..#.. #...# .#.#. #.#.# #...# ..#.. #....
#...# .###. #.... .##.# #...# ####. ..#.. .###. ..#.. .#.#. #...# ..#.. #####

t     s     .     =     -     :     /
.#... ..... ..... ..... ..... ..... .....
.#... ..... ..... ..... ..... .##.. ....#
###.. .###. ..... ##### ..... .##.. ...#.
.#... #.... ..... ..... ##### ..... ..#..
.#... .###. ..... ##### ..... .##.. .#...
.#..# ....# .##.. ..... ..... .##.. #....
..##. ####. .##.. ..... ..... ..... .....
"""


def _parse_font(table: str) -> dict[str, np.ndarray]:
    """Each key of `table` -> its (7, 5) bool glyph; the space is blank."""
    glyphs = {" ": np.zeros((GLYPH_H, GLYPH_W), bool)}
    for block in table.strip().split("\n\n"):
        keys, *rows = block.splitlines()
        cells = [row.split() for row in rows]
        for k, key in enumerate(keys.split()):
            glyphs[key] = np.array([[c == "#" for c in row[k]] for row in cells])
    return glyphs


_GLYPHS = _parse_font(_FONT)


@dataclass(frozen=True, slots=True)
class Sheet:
    """A contact sheet: the PNG file bytes, its size in px, the layout it
    used, and a legend that says how to read it."""

    png: bytes
    width: int
    height: int
    layout: str  # "strip", "grid" or "splat"
    legend: str


@dataclass(frozen=True, slots=True)
class _Run:
    """One checked sequence to draw."""

    frames: np.ndarray  # (F, N, 3) float32 linear light
    positions: np.ndarray  # (N, 3) float64
    reach: np.ndarray  # (3,) extent per axis
    dims: int  # axes the mapping spans (`dimensions`)
    fps: float

    @classmethod
    def of(cls, frames: np.ndarray, positions: np.ndarray, fps: float) -> _Run:
        frames = check_frames(frames, fps)
        positions = np.asarray(positions, dtype=np.float64)
        reach = extents(positions)
        if len(positions) != frames.shape[1]:
            raise ValueError(f"positions has {len(positions)} points, but each frame has {frames.shape[1]} pixels")
        return cls(frames, positions, reach, dimensions(positions), float(fps))

    @property
    def n(self) -> int:
        return len(self.positions)

    @property
    def seconds(self) -> float:
        return len(self.frames) / self.fps

    def time(self, i: int) -> float:
        return (i + 1) / self.fps


def contact_sheet(
    frames: np.ndarray,
    positions: np.ndarray,
    fps: float,
    *,
    layout: str = "auto",
    tiles: int = 8,
    width: int = 1024,
    labels: bool = True,
) -> Sheet:
    """`frames`, rendered at `fps` over `positions`, as one contact sheet.

    `layout` is "auto" (see the module docstring), "strip", "grid" or
    "splat". `tiles` is how many frames a grid or splat sheet shows (at
    most one per frame); `width` is the sheet's width in px, MIN_WIDTH to
    MAX_EDGE, and a tiled sheet may come out narrower. `labels` False
    leaves out every label. Raises ValueError for bad input or tiles that
    cannot each get MIN_TILE px.
    """
    run = _Run.of(frames, positions, fps)
    chosen = _choose(layout, run, tiles, width)
    image, legend = _panel(chosen, run, tiles, width, MAX_EDGE, labels)
    return _sheet(image, chosen, legend)


def compare_sheet(
    a_frames: np.ndarray,
    b_frames: np.ndarray,
    positions: np.ndarray,
    fps: float,
    *,
    layout: str = "auto",
    tiles: int = 4,
    width: int = 1024,
    labels: bool = True,
) -> Sheet:
    """Two sequences of the same shape in one sheet: row A shows
    `a_frames` and row B `b_frames`, at the same times and in the same
    layout. The arguments are as for `contact_sheet`; `tiles` is per row."""
    image, chosen, legend = _rows((a_frames, b_frames), "AB", positions, fps, layout, tiles, width, labels)
    return _sheet(image, chosen, f"Row A and row B are two renders at the same times. {legend}")


def rows_sheet(
    sequences: Sequence[np.ndarray],
    positions: np.ndarray,
    fps: float,
    *,
    layout: str = "auto",
    tiles: int = 2,
    width: int = 1024,
    labels: bool = True,
) -> Sheet:
    """Up to MAX_ROWS sequences of the same shape in one sheet, each a row
    labeled 1, 2, 3 ... in order, at the same times and in the same
    layout; past what one column holds, the rows run down two columns.
    The arguments are as for `contact_sheet`; `tiles` is per row."""
    if not 1 <= len(sequences) <= MAX_ROWS:
        raise ValueError(f"a sheet of rows takes 1 to {MAX_ROWS} renders, got {len(sequences)}")
    marks = "".join(str(k + 1) for k in range(len(sequences)))
    image, chosen, legend = _rows(sequences, marks, positions, fps, layout, tiles, width, labels)
    span = "Row 1 is one render" if len(sequences) == 1 else f"Rows 1 to {len(sequences)} are renders"
    return _sheet(image, chosen, f"{span} at the same times, each numbered at its left. {legend}")


def _rows(
    sequences: Sequence[np.ndarray], marks: str, positions: np.ndarray, fps: float, layout: str, tiles: int,
    width: int, labels: bool,
) -> tuple[np.ndarray, str, str]:
    """`sequences` drawn as rows, each with its mark (one character) at its
    left, at the same times in one layout; one column, or two when one
    column of rows would pass MAX_EDGE. The image, the layout and the
    legend of one row."""
    runs = [_Run.of(frames, positions, fps) for frames in sequences]
    shapes = {run.frames.shape for run in runs}
    if len(shapes) > 1:
        raise ValueError(
            f"{' and '.join(marks)} must have the same shape to compare, got "
            f"{' and '.join(str(run.frames.shape) for run in runs)}; render each with the same seconds and fps "
            "over the same mapping"
        )
    chosen = _choose(layout, runs[0], tiles, width)
    column = 2 * GUTTER + GLYPH_W * LETTER_SCALE
    least = 2 * GUTTER + (MIN_STRIP if chosen == "strip" else BAND + MIN_TILE)
    across = 1 if len(runs) * least <= MAX_EDGE else 2
    down = -(-len(runs) // across)
    drawn = [_panel(chosen, run, tiles, width // across - column, MAX_EDGE // down, labels) for run in runs]
    height, wide = drawn[0][0].shape[0], max(panel.shape[1] for panel, _ in drawn)
    image = _page(down * height, across * (column + wide))
    for k, ((panel, _), mark) in enumerate(zip(drawn, marks)):
        row, col = k % down, k // down
        x, y = col * (column + wide), row * height
        image[y : y + height, x + column : x + column + panel.shape[1]] = panel
        if labels:
            _text(image, mark, x + GUTTER, y + (height - GLYPH_H * LETTER_SCALE) // 2, LETTER_SCALE)
    return image, chosen, drawn[0][1]


# ---- layouts ----------------------------------------------------------------


def _choose(layout: str, run: _Run, tiles: int, width: int) -> str:
    """The layout to draw, after checking the size arguments."""
    if layout not in LAYOUTS:
        raise ValueError(unknown("layout", layout, LAYOUTS))
    if not MIN_WIDTH <= width <= MAX_EDGE:
        raise ValueError(
            f"width must be {MIN_WIDTH}-{MAX_EDGE} px, got {width}: narrower gives tiles under "
            f"{MIN_TILE} px, and a vision model scales a wider image down"
        )
    if tiles < 1:
        raise ValueError(f"tiles must be 1 or more, got {tiles}")
    if layout != "auto":
        return layout
    if run.dims <= 1:
        return "strip"
    return "grid" if run.dims == 2 and _fills_lattice(run) else "splat"


def _panel(layout: str, run: _Run, tiles: int, width: int, height: int, labels: bool) -> tuple[np.ndarray, str]:
    """One sequence drawn in `layout`, at most `width` × `height` px (a
    strip's time at most STRIP_ROWS px), and its legend."""
    rows = min(STRIP_ROWS, height - 2 * GUTTER)
    if layout == "strip":
        image = _strip(run, width, labels, rows)
    else:
        image = _tiles(run, _cells if layout == "grid" else _dots, tiles, width, height, labels)
    return image, _panel_legend(layout, run, tiles, rows)


def _strip(run: _Run, width: int, labels: bool, rows: int) -> np.ndarray:
    """Pixels across in order along the longest axis, frames down `rows`
    px, with the time labeled every TICK seconds or a multiple of it."""
    count = len(run.frames)
    step = _tick_step(run.seconds, rows)
    ticks = [step * k for k in range(1, int(run.seconds / step + 1e-9) + 1)]
    texts = [f"{t:.1f}s" for t in ticks]
    left = GUTTER + _text_width(max(texts, key=len, default="0.0s")) + GUTTER // 2 + TICK_LEN
    plot = width - left - GUTTER
    image = _page(rows + 2 * GUTTER, width)
    area = image[GUTTER : GUTTER + rows, left : left + plot]
    area[:] = 0  # what an empty mapping shows
    if run.n:
        order = np.argsort(run.positions[:, _axis(run)], kind="stable")
        area[:] = to_display_u8(run.frames)[_resample(count, rows)][:, order[_resample(run.n, plot)]]
    if labels:
        for t, text in zip(ticks, texts):
            i = min(count, max(1, round(t * run.fps))) - 1
            y = GUTTER + int((i + 0.5) * rows / count)
            image[y, left - TICK_LEN : left] = INK
            _text(image, text, left - TICK_LEN - GUTTER // 2 - _text_width(text), y - GLYPH_H * SCALE // 2)
    return image


_Stamp = Callable[[_Run, np.ndarray, np.ndarray], None]


def _tiles(run: _Run, stamp: _Stamp, tiles: int, width: int, height: int, labels: bool) -> np.ndarray:
    """Frames at evenly spaced times as labeled square tiles, drawn by
    `stamp` on black, left to right then down."""
    picks = _picks(run, tiles)
    cols, rows, size = _grid(len(picks), width, height)
    content = np.zeros((len(picks), size, size, 3), np.uint8)
    if run.n:
        stamp(run, picks, content)
    image = _page(GUTTER + rows * (BAND + size + GUTTER), GUTTER + cols * (size + GUTTER))
    for k, (i, tile) in enumerate(zip(picks, content)):
        row, col = divmod(k, cols)
        x, y = GUTTER + col * (size + GUTTER), GUTTER + row * (BAND + size + GUTTER)
        if labels:
            _text(image, f"t={run.time(int(i)):.2f}s", x, y + (BAND - GLYPH_H * SCALE) // 2)
        image[y + BAND : y + BAND + size, x : x + size] = tile
    return image


def _cells(run: _Run, picks: np.ndarray, tiles: np.ndarray) -> None:
    """Draw on `tiles`, (picks, size, size, 3), the tile plane (`_plane_axes`),
    its aspect kept. Each distinct position along an axis is one column
    or row of cells, so LEDs at distinct positions get distinct cells
    (up to `size` per axis) and an uneven gap between them closes up."""
    size = tiles.shape[1]
    (u, v), (reach_u, reach_v) = _plane(run)
    (rank_u, nu), (rank_v, nv) = _ranks(u), _ranks(v)
    gu, gv = min(nu, size), min(nv, size)
    cells = np.zeros((len(picks), gv, gu, 3), np.uint8)
    at = (rank_u * gu // nu, rank_v * gv // nv)
    np.maximum.at(cells, (np.arange(len(picks))[:, None], at[1], at[0]), to_display_u8(run.frames[picks]))
    w, h = _box(reach_u, reach_v, size, least=size // max(gu, gv))
    x, y = (size - w) // 2, (size - h) // 2
    tiles[:, y : y + h, x : x + w] = cells[:, gv - 1 - _resample(gv, h)][:, :, _resample(gu, w)]


def _dots(run: _Run, picks: np.ndarray, tiles: np.ndarray) -> None:
    """Draw on `tiles`, (picks, size, size, 3), the tile plane (`_plane_axes`),
    its aspect kept; each LED a dot, and the channel-wise maximum where
    dots overlap."""
    size = tiles.shape[1]
    radius = max(2, size // 64)
    inner = size - 2 * radius
    (u, v), (reach_u, reach_v) = _plane(run)
    w, h = _box(reach_u, reach_v, inner)
    px = radius + (inner - w) // 2 + _rint(u * (w - 1))
    py = radius + (inner - h) // 2 + _rint((1.0 - v) * (h - 1))
    dy, dx = _disc(radius)
    at = (np.arange(len(picks))[:, None, None], (py + dy[:, None])[None], (px + dx[:, None])[None])
    np.maximum.at(tiles, at, to_display_u8(run.frames[picks])[:, None])


def _panel_legend(layout: str, run: _Run, tiles: int, rows: int) -> str:
    """How to read one panel, in a few sentences."""
    count = len(run.frames)
    timing = f"{count} frames at {run.fps:g} fps ({run.seconds:.2f} s)"
    tail = "Colours are display gamma; black is an unlit LED or no LED."
    if layout == "strip":
        along = f" in order along {_AXES[_axis(run)]}" if run.n > 1 else ""
        step = _tick_step(run.seconds, rows)
        return f"Space-time strip: {run.n} pixels across{along}, {timing} down, time labeled every {step:g} s. {tail}"
    picks = _picks(run, tiles)
    span = f"{len(picks)} tiles from t={run.time(int(picks[0])):.2f}s to t={run.time(int(picks[-1])):.2f}s"
    right, up = (_AXES[a] for a in _plane_axes(run))
    plane, hidden = ("a top-down view", ", z ignored") if run.dims == 3 else (f"the {right}{up} plane", "")
    mark = "cell" if layout == "grid" else "dot"
    view = f"each tile is {plane}, {right} to the right and {up} up, one {mark} per LED{hidden}"
    return f"{span} of {timing}, read left to right then down; {view}. {tail}"


# ---- geometry -----------------------------------------------------------------


def _grid(count: int, width: int, height: int) -> tuple[int, int, int]:
    """Columns, rows and tile size in px for `count` tiles in at most
    `width` × `height` px. Raises ValueError if a tile would be under
    MIN_TILE px."""
    max_cols = max(1, (width - GUTTER) // (MIN_TILE + GUTTER))
    rows = -(-count // max_cols)
    cols = -(-count // rows)
    size = min((width - GUTTER) // cols - GUTTER, (height - GUTTER) // rows - BAND - GUTTER)
    if size < MIN_TILE:
        raise ValueError(
            f"{count} tiles do not fit at {MIN_TILE} px or more in a {width} × {height} px sheet; "
            "ask for fewer tiles"
        )
    return cols, rows, size


def _picks(run: _Run, tiles: int) -> np.ndarray:
    """The frames the tiles show: the last frame of each of `tiles` equal
    spans of the sequence, so the last tile is the last frame."""
    count = len(run.frames)
    shown = min(tiles, count)
    return np.array([count * (k + 1) // shown - 1 for k in range(shown)])


def _tick_step(seconds: float, rows: int) -> float:
    """TICK, doubled until time labels in a strip of `seconds` down `rows`
    px are a label band apart."""
    step = TICK
    while step * rows / seconds < BAND:
        step *= 2.0
    return step


def _axis(run: _Run) -> int:
    """The axis a strip is ordered along: the longest, x when there is none."""
    return int(np.argmax(run.reach))


def _plane_axes(run: _Run) -> tuple[int, int]:
    """The two axes a tile shows, first to the right and second up: x and
    y for a volume, seen from above; otherwise the two longest axes in
    axis order, ties to the lower axis, so a flat mapping in any plane
    shows its full extent."""
    if run.dims == 3:
        return 0, 1
    first, second = sorted(int(a) for a in np.argsort(-run.reach, kind="stable")[:2])
    return first, second


def _plane(run: _Run) -> tuple[tuple[np.ndarray, np.ndarray], tuple[float, float]]:
    """Positions along the two plane axes scaled to 0-1, and their reach."""
    axes = _plane_axes(run)
    coords = tuple(_unit(run.positions[:, a], run.reach[a]) for a in axes)
    return (coords[0], coords[1]), (float(run.reach[axes[0]]), float(run.reach[axes[1]]))


def _fills_lattice(run: _Run) -> bool:
    """Whether the points sit on a lattice that they mostly fill, as a
    panel's LEDs do: the distinct positions along the two plane axes
    multiply to at most twice the point count. A room's fixtures leave
    most of their lattice empty."""
    (u, v), _ = _plane(run)
    return _ranks(u)[1] * _ranks(v)[1] <= 2 * run.n


def _ranks(unit: np.ndarray) -> tuple[np.ndarray, int]:
    """Each 0-1 coordinate's rank among the distinct values, to 1/4096,
    and how many distinct values there are."""
    levels, rank = np.unique(np.rint(unit * 4096.0), return_inverse=True)
    return rank, len(levels)


def _unit(values: np.ndarray, reach: float) -> np.ndarray:
    """`values` scaled to 0-1 over their reach; 0.5 when they have none."""
    return (values - values.min()) / reach if reach > 0 else np.full(values.shape, 0.5)


def _box(reach_u: float, reach_v: float, size: int, least: int = 1) -> tuple[int, int]:
    """Width and height of the largest box with the aspect reach_u :
    reach_v inside size × size px, each side `least` px or more."""
    longest = max(reach_u, reach_v)
    if longest <= 0:
        return size, size
    return max(least, round(size * reach_u / longest)), max(least, round(size * reach_v / longest))


def _disc(radius: int) -> tuple[np.ndarray, np.ndarray]:
    """Row and column offsets of the px in a disc of `radius`."""
    span = np.arange(-radius, radius + 1)
    dy, dx = np.meshgrid(span, span, indexing="ij")
    inside = dx * dx + dy * dy <= radius * (radius + 1)
    return dy[inside], dx[inside]


def _resample(n: int, size: int) -> np.ndarray:
    """For each of `size` px, the index of the one of `n` items it shows (nearest)."""
    return np.arange(size) * n // size


def _rint(values: np.ndarray) -> np.ndarray:
    return np.rint(values).astype(np.intp)


# ---- drawing ------------------------------------------------------------------


def _page(height: int, width: int) -> np.ndarray:
    return np.full((height, width, 3), PAGE, np.uint8)


def _text(image: np.ndarray, text: str, x: int, y: int, scale: int = SCALE) -> None:
    """Draw `text` in INK with its top-left corner at (x, y)."""
    for char in text:
        mask = _GLYPHS[char].repeat(scale, axis=0).repeat(scale, axis=1)
        image[y : y + mask.shape[0], x : x + mask.shape[1]][mask] = INK
        x += (GLYPH_W + 1) * scale


def _text_width(text: str, scale: int = SCALE) -> int:
    return len(text) * (GLYPH_W + 1) * scale - scale


def _sheet(image: np.ndarray, layout: str, legend: str) -> Sheet:
    return Sheet(encode_png(image), image.shape[1], image.shape[0], layout, legend)
