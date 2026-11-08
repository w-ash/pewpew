"""Contact sheets (src/pewpew/sheet.py): the layout each mapping gets, the
geometry a vision model needs, labels, orientation and determinism. Every
sheet is decoded back to pixels with the test reader in pngread.py."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from fakes import EXAMPLE_RIG
from pewpew.mapping import dimensions, grid, lattice, line
from pewpew.rig.runtime import load_rig
from pewpew.sheet import (
    GUTTER,
    INK,
    MAX_EDGE,
    MAX_ROWS,
    MIN_TILE,
    PAGE,
    STRIP_ROWS,
    Sheet,
    compare_sheet,
    contact_sheet,
    rows_sheet,
)
from pngread import decode_png

FPS = 30.0

# sha256 of the decoded pixels of `_golden_sheet(layout)`. The frames hold
# only 0 and 1, which display gamma maps exactly, so the hash pins the
# drawing on every platform. Update one only for an intended visual change.
GOLDEN = {
    "strip": "86325437e004bbafd207140e3e80e6f6d67cf5adbb61a55d6fc924024ef9f7d1",
    "grid": "44daf569f98de5dfe2523e076f3a034adbcb25a6e57bd7f699f5a1891718cf82",
    "splat": "5046d97f7980a317bacd99cab0ad11654e8cb64b6d6afc39bcc6924755dba72a",
}


def _sparse_room() -> np.ndarray:
    """Two bars in an L, as a room's fixtures sit: most of their lattice is empty."""
    bar = np.linspace(0.0, 1.0, 32, dtype=np.float32)
    zero = np.zeros_like(bar)
    along_x, along_y = np.stack([bar, zero, zero], 1), np.stack([zero, bar, zero], 1)
    return np.concatenate([along_x, along_y[1:]])  # one LED at the shared corner


def _holey_grid() -> np.ndarray:
    """An 8 × 8 panel with every seventh LED missing."""
    m = grid(8, 8)
    return m[np.arange(len(m)) % 7 != 3]


def _random(frames: int, n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).random((frames, n, 3), dtype=np.float32)


def _white(frames: int, n: int) -> np.ndarray:
    return np.ones((frames, n, 3), np.float32)


def _draw(compare: bool, frames: np.ndarray, mapping: np.ndarray, **options) -> Sheet:
    """A contact sheet of `frames`, or a compare sheet with `frames` as both A and B."""
    if compare:
        return compare_sheet(frames, frames, mapping, FPS, **options)
    return contact_sheet(frames, mapping, FPS, **options)


def _pixels(sheet: Sheet) -> np.ndarray:
    rgb = decode_png(sheet.png)
    assert rgb.shape == (sheet.height, sheet.width, 3)
    return rgb


def _labeled(compare: bool, frames: np.ndarray, mapping: np.ndarray, **options) -> tuple[Sheet, np.ndarray, np.ndarray]:
    """A labeled sheet as `_draw` makes it, its pixels, and the pixels of
    the same sheet without labels."""
    sheet = _draw(compare, frames, mapping, **options)
    return sheet, _pixels(sheet), _pixels(_draw(compare, frames, mapping, labels=False, **options))


def _runs(mask: np.ndarray) -> list[int]:
    """Lengths of the runs of True in a 1-D mask."""
    edges = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(np.int8), [0]])))
    return (edges[1::2] - edges[::2]).tolist()


def _drawn(rgb: np.ndarray) -> tuple[list[int], list[int]]:
    """Widths and heights of what is drawn off the page grey: tiles, or a strip's plot."""
    mask = (rgb != PAGE).any(axis=-1)
    return _runs(mask.any(axis=0)), _runs(mask.any(axis=1))


# ---- layouts ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mapping", "layout"),
    [
        (line(32), "strip"),
        (line(32)[:, [1, 0, 2]], "strip"),  # a strip along y
        (np.zeros((1, 3), np.float32), "strip"),
        (np.zeros((0, 3), np.float32), "strip"),
        (grid(8, 8), "grid"),
        (_holey_grid(), "grid"),
        (load_rig(EXAMPLE_RIG)[0].mapping, "grid"),  # the canopy's bars fill a lattice
        (lattice(4), "splat"),
        (_sparse_room(), "splat"),
    ],
    ids=["line", "line-y", "one", "empty", "grid", "holey-grid", "canopy", "lattice", "sparse-room"],
)
def test_auto_picks_the_layout_for_the_mapping(mapping, layout):
    assert contact_sheet(_random(4, len(mapping)), mapping, FPS).layout == layout


def test_dimensions_counts_the_spanned_axes():
    assert [dimensions(m) for m in (np.zeros((0, 3)), np.zeros((3, 3)), line(8), grid(4, 4), lattice(3))] == [
        0, 0, 1, 2, 3,
    ]
    flat = grid(4, 4)
    flat[:, 2] = np.float32(1e-5) * np.arange(16)  # float noise in z
    assert dimensions(flat) == 2


# ---- geometry -----------------------------------------------------------------


def test_the_default_grid_sheet_is_about_1024_by_560_with_8_tiles_over_200_px():
    sheet = contact_sheet(_white(60, 256), grid(16, 16), FPS, labels=False)
    widths, heights = _drawn(_pixels(sheet))
    assert sheet.width == 1024 and 520 <= sheet.height <= 600
    assert len(widths) == 4 and len(heights) == 2
    assert min(widths + heights) >= MIN_TILE


def test_the_default_strip_plot_is_at_least_768_by_512():
    sheet = contact_sheet(_white(60, 64), line(64), FPS, labels=False)
    (plot_w,), (plot_h,) = _drawn(_pixels(sheet))
    assert plot_w >= 768 and plot_h == STRIP_ROWS
    assert sheet.width == 1024 and sheet.height <= 600


@pytest.mark.parametrize("width", [896, 1024, 1568])
@pytest.mark.parametrize("tiles", [1, 3, 8, 16])
@pytest.mark.parametrize("compare", [False, True], ids=["single", "compare"])
def test_every_tile_is_200_px_or_more_and_the_long_edge_1568_or_less(width, tiles, compare):
    try:
        sheet = _draw(compare, _white(16, 16), grid(4, 4), tiles=tiles, width=width, labels=False)
    except ValueError as exc:
        assert "ask for fewer tiles" in str(exc)
        return
    widths, heights = _drawn(_pixels(sheet))
    assert len(widths) * len(heights) >= tiles * (2 if compare else 1)
    assert min(widths + heights) >= MIN_TILE
    assert max(sheet.width, sheet.height) <= MAX_EDGE == 1568
    assert sheet.width <= width


def test_a_tile_keeps_the_mapping_aspect():
    wide = grid(8, 8) * np.array([1.0, 0.5, 0.0], np.float32)  # twice as wide as tall
    rgb = _pixels(contact_sheet(_white(4, 64), wide, FPS, tiles=1, labels=False))
    widths, heights = _drawn(rgb)
    white = (rgb == 255).all(axis=-1)
    assert _runs(white.any(axis=0))[0] == pytest.approx(2 * _runs(white.any(axis=1))[0], abs=2)
    assert widths == heights  # the tile itself stays square


def test_fewer_frames_than_tiles_draws_each_frame_once():
    sheet = contact_sheet(_white(3, 16), grid(4, 4), FPS, labels=False)
    assert len(_drawn(_pixels(sheet))[0]) == 3
    assert "3 tiles from t=0.03s to t=0.10s" in sheet.legend


# ---- labels -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mapping", "layout"), [(line(16), "strip"), (grid(4, 4), "grid"), (lattice(3), "splat")]
)
def test_labels_are_ink_on_the_page_and_nothing_else(mapping, layout):
    frames = _random(30, len(mapping))
    for compare in (False, True):
        _, labeled, bare = _labeled(compare, frames, mapping, layout=layout)
        changed = (labeled != bare).any(axis=-1)
        assert changed.sum() > 50
        assert (labeled[changed] == INK).all() and (bare[changed] == PAGE).all()


@pytest.mark.parametrize(
    ("frames", "ticks", "step"),
    [
        (60, 4, "0.5"),  # 2 s: 0.5, 1.0, 1.5 and 2.0 s
        (1800, 15, "4"),  # 60 s: every 4 s, so the labels never touch
    ],
    ids=["2s", "60s"],
)
def test_a_strip_labels_time_every_half_second_or_wider_to_fit(frames, ticks, step):
    sheet, labeled, bare = _labeled(False, _white(frames, 4), line(4))
    rows = (labeled != bare).any(axis=-1).any(axis=1)
    assert len(_runs(rows)) == ticks
    assert f"every {step} s" in sheet.legend


def test_the_legend_gives_the_tile_times():
    sheet = contact_sheet(_random(120, 16), grid(4, 4), FPS)  # 4 s
    assert "8 tiles from t=0.50s to t=4.00s of 120 frames at 30 fps" in sheet.legend


# ---- orientation --------------------------------------------------------------


def _lit(rgb: np.ndarray) -> tuple[float, float]:
    """Mean x and y, as a fraction of the drawn area, of the white px."""
    widths, heights = _drawn(rgb)
    ys, xs = np.nonzero((rgb == 255).all(axis=-1))
    mask = (rgb != PAGE).any(axis=-1)
    x0, y0 = np.flatnonzero(mask.any(axis=0))[0], np.flatnonzero(mask.any(axis=1))[0]
    return float((xs.mean() - x0) / widths[0]), float((ys.mean() - y0) / heights[0])


@pytest.mark.parametrize(("mapping", "layout"), [(grid(4, 4), "grid"), (lattice(3), "splat")])
def test_the_first_led_at_the_origin_is_drawn_bottom_left(mapping, layout):
    frames = np.zeros((1, len(mapping), 3), np.float32)
    frames[0, 0] = 1.0
    x, y = _lit(_pixels(contact_sheet(frames, mapping, FPS, layout=layout, labels=False)))
    assert x < 0.25 and y > 0.75


def _ring(plane: str, n: int = 48) -> np.ndarray:
    """`n` LEDs on a circle 1 across in `plane`, for example "xz"."""
    theta = 2.0 * np.pi * np.arange(n) / n
    ring = np.zeros((n, 3), np.float32)
    ring[:, "xyz".index(plane[0])] = 0.5 + 0.5 * np.cos(theta)
    ring[:, "xyz".index(plane[1])] = 0.5 + 0.5 * np.sin(theta)
    return ring


@pytest.mark.parametrize(
    ("mapping", "view"),
    [
        (_ring("xy"), "the xy plane, x to the right and y up"),
        (_ring("xz"), "the xz plane, x to the right and z up"),  # fixtures on a wall: z is height
        (_ring("yz"), "the yz plane, y to the right and z up"),
        (lattice(3) * np.array([1.0, 1.0, 4.0], np.float32), "a top-down view, x to the right and y up"),
    ],
    ids=["xy", "xz", "yz", "tall-volume"],
)
def test_a_tile_draws_a_flat_mapping_in_its_plane_and_a_volume_from_above(mapping, view):
    sheet = contact_sheet(_white(4, len(mapping)), mapping, FPS, tiles=1, labels=False)
    ys, xs = np.nonzero((_pixels(sheet) == 255).all(axis=-1))
    assert sheet.layout == "splat" and view in sheet.legend
    assert np.ptp(ys) == pytest.approx(np.ptp(xs), abs=2)  # a circle, or the volume's square floor


def test_leds_at_distinct_positions_get_distinct_cells_on_an_uneven_lattice():
    """Two 8 × 8 panels two pitches apart: x is 0-7 and 10-17. Columns are
    red and blue in turn, so two columns in one cell would show magenta."""
    xs = np.r_[0:8, 10:18]
    mapping = np.array([[x, y, 0.0] for y in range(8) for x in xs], np.float32)
    frames = np.zeros((1, len(mapping), 3), np.float32)
    frames[0, :, 0] = mapping[:, 0] % 2 == 0
    frames[0, :, 2] = mapping[:, 0] % 2 == 1
    sheet = contact_sheet(frames, mapping, FPS, labels=False)
    rgb = _pixels(sheet)
    red, blue, magenta = ((rgb == colour).all(axis=-1) for colour in ([255, 0, 0], [0, 0, 255], [255, 0, 255]))
    middle = int(np.median(np.flatnonzero(red.any(axis=1))))
    assert sheet.layout == "grid" and not magenta.any()
    assert len(_runs(red[middle])) == len(_runs(blue[middle])) == 8


def test_a_strip_runs_along_x_whatever_the_wiring_order():
    reversed_line = line(16)[::-1].copy()  # pixel 0 at x = 1
    frames = np.zeros((4, 16, 3), np.float32)
    frames[:, 0] = 1.0
    x, _ = _lit(_pixels(contact_sheet(frames, reversed_line, FPS, labels=False)))
    assert x > 0.9


# ---- determinism and edge cases ------------------------------------------------


def _golden_sheet(layout: str) -> Sheet:
    mapping = {"strip": line(12), "grid": grid(4, 3), "splat": lattice(3)}[layout]
    i = np.arange(len(mapping))
    frames = np.zeros((20, len(mapping), 3), np.float32)
    for f in range(20):
        frames[f, (i + f) % 3 == 0, f % 3] = 1.0
    return contact_sheet(frames, mapping, FPS, layout=layout)


@pytest.mark.parametrize("layout", ["strip", "grid", "splat"])
def test_the_pixels_match_the_golden(layout):
    rgb = _pixels(_golden_sheet(layout))
    assert hashlib.sha256(rgb.tobytes()).hexdigest() == GOLDEN[layout]


@pytest.mark.parametrize("mapping", [line(16), grid(4, 4), lattice(3)], ids=["strip", "grid", "splat"])
def test_the_same_frames_give_the_same_bytes(mapping):
    frames = _random(24, len(mapping), seed=4)
    assert contact_sheet(frames, mapping, FPS) == contact_sheet(frames.copy(), mapping.copy(), FPS)


@pytest.mark.parametrize("layout", ["auto", "strip", "grid", "splat"])
@pytest.mark.parametrize("n", [0, 1])
def test_empty_and_one_pixel_mappings_draw(layout, n):
    positions = np.full((n, 3), 0.5, np.float32)
    for sheet in (
        contact_sheet(_white(5, n), positions, FPS, layout=layout),
        compare_sheet(_white(5, n), _white(5, n), positions, FPS, layout=layout),
    ):
        _pixels(sheet)


# ---- compare ------------------------------------------------------------------


def test_compare_draws_a_over_b_at_the_same_times():
    frames = _random(30, 16)
    same = _pixels(compare_sheet(frames, frames, grid(4, 4), FPS, labels=False))
    half = same.shape[0] // 2
    assert np.array_equal(same[:half], same[half:])
    other = _pixels(compare_sheet(frames, _random(30, 16, seed=9), grid(4, 4), FPS, labels=False))
    assert np.array_equal(other[:half], same[:half]) and not np.array_equal(other[half:], same[half:])


@pytest.mark.parametrize("layout, mapping", [("grid", grid(4, 4)), ("strip", line(16))])
def test_rows_number_each_render_and_run_down_two_columns_past_what_one_holds(layout, mapping):
    runs = [_random(30, len(mapping), seed=k) for k in range(MAX_ROWS)]
    for count in (2, MAX_ROWS):
        sheet = rows_sheet(runs[:count], mapping, FPS, layout=layout)
        image = _pixels(sheet)
        assert max(image.shape[:2]) <= MAX_EDGE and sheet.legend.startswith(f"Rows 1 to {count} are renders")
    one_column = _pixels(rows_sheet(runs[:2], mapping, FPS, layout=layout, labels=False))
    assert np.array_equal(one_column, _pixels(compare_sheet(runs[0], runs[1], mapping, FPS, layout=layout, tiles=2,
                                                            labels=False)))
    two_columns = _pixels(rows_sheet(runs, mapping, FPS, layout=layout, labels=False))
    if layout == "grid":  # eight rows of tiles do not fit one column: four rows, each half as wide
        assert two_columns.shape[0] < 4 * one_column.shape[0] and abs(two_columns.shape[1] - one_column.shape[1]) < 8
    with pytest.raises(ValueError, match="takes 1 to 8 renders"):
        rows_sheet([*runs, runs[0]], mapping, FPS)


def test_compare_labels_its_rows_a_and_b():
    sheet, labeled, bare = _labeled(True, _random(30, 16), grid(4, 4))
    letters = (labeled != bare).any(axis=-1)[:, : 2 * GUTTER]  # the A/B column
    assert len(_runs(letters.any(axis=1))) == 2
    assert sheet.legend.startswith("Row A and row B")


# ---- refusals -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("call", "says"),
    [
        (lambda: contact_sheet(_white(4, 4), line(4), FPS, layout="grdi"), "unknown layout 'grdi'; layouts: auto"),
        (lambda: contact_sheet(_white(4, 4), line(4), FPS, width=640), "width must be 896-1568 px"),
        (lambda: contact_sheet(_white(4, 4), line(4), FPS, tiles=0), "tiles must be 1 or more"),
        (lambda: contact_sheet(_white(4, 4), line(4)[:, :2], FPS), "(N, 3)"),
        (lambda: contact_sheet(_white(4, 5), line(4), FPS), "positions has 4 points, but each frame has 5"),
        (lambda: contact_sheet(_white(4, 4), line(4), -1.0), "fps must be a positive number"),
        (lambda: compare_sheet(_white(4, 4), _white(5, 4), line(4), FPS), "same seconds and fps"),
        (lambda: compare_sheet(_white(40, 16), _white(40, 16), grid(4, 4), FPS, tiles=16), "ask for fewer tiles"),
    ],
)
def test_bad_input_is_refused_with_the_fix(call, says):
    with pytest.raises(ValueError) as caught:
        call()
    assert says in str(caught.value)
