"""ANSI sink: layout from the mapping, exact-string goldens, TTY manners."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from conftest import FakeTime

from pewpew import grid, lattice, line
from pewpew.sinks import AnsiLayout, AnsiSink

GOLDENS = Path(__file__).parent / "goldens"


def solid(n: int, rgb: tuple[float, float, float]) -> np.ndarray:
    return np.tile(np.asarray(rgb, dtype=np.float32), (n, 1))


def make_sink(mapping, **kw) -> tuple[AnsiSink, io.StringIO]:
    ft = FakeTime()
    stream = io.StringIO()
    sink = AnsiSink(mapping, stream=stream, now=ft.now, sleep=ft.sleep, **kw)
    return sink, stream


def test_line_lays_out_as_one_row():
    layout = AnsiLayout.from_mapping(line(8))
    assert layout.one_row and layout.text_rows == 1 and layout.cols == 8
    s = layout.render_frame(solid(8, (1.0, 0.0, 0.0)))
    assert s.count("\n") == 1
    assert s.count("█") == 8
    assert "38;2;255;0;0" in s


def test_grid_half_blocks_put_y0_at_bottom():
    m = grid(2, 4)  # index = row*w + col, row 0 is y=0
    frame = np.zeros((8, 3), dtype=np.float32)
    frame[0:2, 0] = 1.0  # the y=0 row, red
    lines = AnsiLayout.from_mapping(m).render_frame(frame).splitlines()
    assert len(lines) == 2  # 4 pixel rows -> 2 half-block rows
    # y=0 is the lower half of the last text row: red arrives as bg (48;2).
    assert "48;2;255;0;0" in lines[-1]
    assert "255;0;0" not in lines[0]


def test_lattice_slices_read_left_to_right_by_z():
    m = lattice(2)  # index = (iz*2 + iy)*2 + ix
    frame = np.zeros((8, 3), dtype=np.float32)
    frame[4:, 2] = 1.0  # the z=1 slice, blue
    layout = AnsiLayout.from_mapping(m)
    assert layout.cols == 5  # two 2-wide slices + one gutter column
    (row,) = layout.render_frame(frame).splitlines()
    left, right = row.split("\x1b[0m ", 1)  # gutter renders reset+space
    assert "255" not in left  # z=0 slice is black
    assert right.count("48;2;0;0;255") == 2  # z=1 slice is blue


def test_cells_average_in_linear_light_before_gamma():
    m = np.zeros((2, 3), dtype=np.float32)  # two pixels, one cell
    frame = np.array([[0.0] * 3, [1.0] * 3], dtype=np.float32)
    s = AnsiLayout.from_mapping(m).render_frame(frame)
    # mean(0,1)=0.5 then gamma -> 186; gamma-then-average would give 127.
    assert "38;2;186;186;186" in s


def test_frame_string_golden_is_exact(regen_goldens):
    n = 16
    frame = np.zeros((n, 3), dtype=np.float32)
    frame[:, 0] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    frame[:, 2] = np.linspace(1.0, 0.0, n, dtype=np.float32)
    got = AnsiLayout.from_mapping(grid(4, 4)).render_frame(frame)
    path = GOLDENS / "ansi_grid4x4.txt"
    if regen_goldens or not path.exists():
        path.write_text(got)
    assert got == path.read_text()


def test_tty_gets_cursor_codes_and_pipe_does_not():
    frame = solid(4, (0.5, 0.5, 0.5))
    sink, stream = make_sink(line(4), interactive=True)
    with sink:
        sink.send(0.0, frame)
        sink.send(1 / 30, frame)
    out = stream.getvalue()
    assert "\x1b[?25l" in out  # cursor hidden
    assert "\x1b[1F" in out  # second frame rewinds over the first
    assert "\x1b[K" in out  # erase-to-EOL per line

    sink, stream = make_sink(line(4))  # StringIO.isatty() is False -> pipe mode
    with sink:
        sink.send(0.0, frame)
        sink.send(1 / 30, frame)
    out = stream.getvalue()
    assert "\x1b[?25l" not in out and "\x1b[F" not in out and "\x1b[K" not in out
    assert out.count("\n\n") == 2  # frame-per-block separators


def test_stop_restores_cursor_and_sgr():
    sink, stream = make_sink(line(4), interactive=True)
    sink.start()
    sink.stop()
    assert stream.getvalue().endswith("\x1b[0m\x1b[?25h\n")
    sink.stop()  # idempotent: no second restore
    assert stream.getvalue().count("\x1b[?25h") == 1


def test_status_line_renders_renderer_error_text():
    texts: list[str | None] = ["boom in render\n  trace line", None]
    sink, stream = make_sink(line(4), status=lambda: texts[0])
    with sink:
        sink.send(0.0, solid(4, (0.0, 0.0, 0.0)))
        texts[0] = texts[1]
        sink.send(1 / 30, solid(4, (0.0, 0.0, 0.0)))
    out = stream.getvalue()
    assert "\x1b[31mboom in render\x1b[0m" in out  # first line only, in red
    assert "trace line" not in out


def test_send_paces_on_its_rate_gate():
    ft = FakeTime()
    stream = io.StringIO()
    sink = AnsiSink(line(4), stream=stream, max_fps=30.0, now=ft.now, sleep=ft.sleep)
    with sink:
        for i in range(3):
            sink.send(i / 30, solid(4, (0.0, 0.0, 0.0)))
    assert ft.sleeps == pytest.approx([1 / 30.0] * 2)  # first frame free


def test_status_line_fits_inside_the_height_budget():
    """A tall map plus a status line must not outgrow the terminal: the block
    would scroll one line per frame while the rewind still counts the old
    height, walking the display up over the scrollback."""
    tall = grid(48, 48)
    plain, _ = make_sink(tall, max_height=24)
    with_status, _ = make_sink(tall, max_height=24, status=lambda: None)
    assert plain.layout.text_rows == 24  # the whole budget when nothing else needs a row
    assert with_status.layout.text_rows + 1 <= 24


def test_interactive_is_answerable_before_start():
    sink, _ = make_sink(line(4))
    assert sink.interactive is False  # a StringIO is not a tty
    forced, _ = make_sink(line(4), interactive=True)
    assert forced.interactive is True
    assert forced._active is False  # ...but nothing is owned until start()
