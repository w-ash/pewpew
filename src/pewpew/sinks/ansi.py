"""ANSI truecolor terminal sink — the ssh/CI preview tier [S514].

Layout is computed once from the mapping, never sniffed from fixture
constructors: a 1D map renders as one row of `█`, a 2D map as `▀`
half-block rows (fg = upper pixel, bg = lower, doubling vertical
resolution; y=0 at the bottom, matching `grid()`), and a 3D map as its
z-slices side by side, ascending z left to right — the reading
`lattice()`'s index order was designed for. Pixels sharing a cell average
in linear light *before* display gamma; gamma-then-average would darken
exactly the low-end glow the gamma step exists to keep.

`AnsiLayout.render_frame` is a pure frame -> str function, so the golden
tests compare exact strings.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Self, TextIO

import numpy as np

from pewpew.color import bins
from pewpew.sinks.sink import to_display_u8

_RESET = "\x1b[0m"


def _axis_res(vals: np.ndarray, cap: int) -> int:
    """Grid resolution along one axis: distinct coordinate values, capped."""
    distinct = len(np.unique(np.round(vals.astype(np.float64), 4)))
    return int(np.clip(distinct, 1, max(1, cap)))


class AnsiLayout:
    """Mapping -> character-cell layout, fixed at construction."""

    def __init__(
        self,
        *,
        cols: int,
        px_rows: int,
        one_row: bool,
        flat: np.ndarray,
        counts: np.ndarray,
    ) -> None:
        self.cols = cols
        self.px_rows = px_rows
        self.one_row = one_row
        self.text_rows = 1 if one_row else px_rows // 2
        self._flat = flat
        self._counts = counts  # pixels per cell, (px_rows*cols,)
        self._occupied = counts > 0

    @classmethod
    def from_mapping(
        cls, mapping: np.ndarray, *, max_width: int = 80, max_height: int = 24
    ) -> AnsiLayout:
        """Character-cell layout for `mapping`, within a max_width x max_height
        budget.

        Assumes each axis spans 0-1: resolution counts the distinct values
        per axis, and `bins()` places each value over [0, 1], so a map on
        part of the range leaves cells blank. `line`, `grid` and `lattice`
        span 0-1.
        """
        x, y, z = mapping[:, 0], mapping[:, 1], mapping[:, 2]
        flat_y = float(np.ptp(y)) < 1e-6
        flat_z = float(np.ptp(z)) < 1e-6

        if flat_y and flat_z:
            nx = _axis_res(x, max_width)
            flat = bins(x, nx).astype(np.int64)
            counts = np.bincount(flat, minlength=nx)
            return cls(cols=nx, px_rows=1, one_row=True, flat=flat, counts=counts)

        nz = 1 if flat_z else _axis_res(z, max(1, (max_width + 1) // 2 - 1))
        nx = _axis_res(x, (max_width + 1) // nz - 1 if nz > 1 else max_width)
        ny = _axis_res(y, 2 * max_height)
        # Half-block rows pair pixel rows two at a time; odd heights pad
        # one blank row at the top so y=0 stays glued to the bottom.
        pad = ny & 1
        px_rows = ny + pad
        cols = nz * (nx + 1) - 1 if nz > 1 else nx  # one-space gutters

        row = (ny - 1) - bins(y, ny) + pad  # row 0 is the top of the screen
        col = bins(x, nx) + (bins(z, nz) * (nx + 1) if nz > 1 else 0)
        flat = (row.astype(np.int64) * cols + col).astype(np.int64)
        counts = np.bincount(flat, minlength=px_rows * cols)
        return cls(cols=cols, px_rows=px_rows, one_row=False, flat=flat, counts=counts)

    def _cell_colors(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per-cell display color: linear-light average, then gamma+u8."""
        size = self.px_rows * self.cols
        avg = np.zeros((size, 3), dtype=np.float64)
        for c in range(3):
            sums = np.bincount(self._flat, weights=frame[:, c], minlength=size)
            np.divide(sums, self._counts, out=avg[:, c], where=self._occupied)
        return to_display_u8(avg), self._occupied

    def render_frame(self, frame: np.ndarray) -> str:
        """One frame as SGR-colored text; every line ends reset + newline."""
        u8, occ = self._cell_colors(frame)
        u8 = u8.reshape(self.px_rows, self.cols, 3)
        occ = occ.reshape(self.px_rows, self.cols)
        if self.one_row:
            cells = [
                f"\x1b[38;2;{r};{g};{b}m█" if o else _RESET + " "
                for (r, g, b), o in zip(u8[0].tolist(), occ[0].tolist())
            ]
            return "".join(cells) + _RESET + "\n"
        out: list[str] = []
        for tr in range(self.text_rows):
            up_c, lo_c = u8[2 * tr].tolist(), u8[2 * tr + 1].tolist()
            up_o, lo_o = occ[2 * tr].tolist(), occ[2 * tr + 1].tolist()
            line: list[str] = []
            for (ur, ug, ub), (lr, lg, lb), uo, lo in zip(up_c, lo_c, up_o, lo_o):
                if not (uo or lo):
                    line.append(_RESET + " ")
                else:
                    line.append(f"\x1b[38;2;{ur};{ug};{ub}m\x1b[48;2;{lr};{lg};{lb}m▀")
            out.append("".join(line) + _RESET + "\n")
        return "".join(out)


class AnsiSink:
    """Terminal sink: an interactive TTY gets hide-cursor and cursor-up
    overwrite (no clear, no flicker); a pipe gets one plain block per frame.
    It takes at most `max_fps` frames a second, 30 by default."""

    def __init__(
        self,
        mapping: np.ndarray,
        *,
        stream: TextIO | None = None,
        max_fps: float = 30.0,
        interactive: bool | None = None,
        status: Callable[[], str | None] | None = None,
        max_width: int = 80,
        max_height: int = 24,
    ) -> None:
        self._stream = stream if stream is not None else sys.stdout
        # The status line costs a text row, so the grid gets one fewer or
        # the block outgrows the terminal and the rewind walks up the
        # scrollback. Budgeted on `status is not None`, not on `_active`:
        # the layout is fixed at construction, interactivity only at start().
        rows = max(1, max_height - 1) if status is not None else max_height
        self.layout = AnsiLayout.from_mapping(mapping, max_width=max_width, max_height=rows)
        self._status_width = max_width  # terminal width, not grid width
        self.max_fps = float(max_fps)
        self._interactive = interactive
        self._status = status
        self._active = False
        self._started = False
        self._last_lines = 0

    @property
    def interactive(self) -> bool:
        """Whether this sink will own the terminal: the explicit override if
        given, else the stream's `isatty`. Known before `start()`, so the
        runner can keep log records out of the rewind."""
        if self._interactive is not None:
            return bool(self._interactive)
        isatty = getattr(self._stream, "isatty", None)
        return bool(isatty()) if callable(isatty) else False

    def start(self) -> None:
        self._active = self.interactive
        self._started = True
        self._last_lines = 0
        if self._active:
            self._stream.write("\x1b[?25l")  # hide cursor
            self._stream.flush()

    def stop(self) -> None:
        if self._started and self._active:
            self._stream.write(_RESET + "\x1b[?25h\n")  # restore SGR + cursor
            self._stream.flush()
        self._started = False
        self._active = False

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def send(self, t: float, frame: np.ndarray) -> None:
        body = self.layout.render_frame(frame)
        text = self._status() if self._status is not None else None
        # Interactive mode keeps the (possibly empty) status line so the
        # block height is constant and rewind overwrites a cleared error;
        # pipe mode only prints it when there is something to say.
        if self._status is not None and (self._active or text):
            first = text.splitlines()[0] if text else ""
            body += f"\x1b[31m{first[: self._status_width]}{_RESET}\n"
        lines = self.layout.text_rows + (1 if self._status is not None and self._active else 0)
        if self._active:
            # Erase-to-EOL per line so a shrinking status never leaves
            # stale characters; rewind over last frame's block.
            body = body.replace("\n", "\x1b[K\n")
            prefix = f"\x1b[{self._last_lines}F" if self._last_lines else ""
            self._stream.write(prefix + body)
        else:
            self._stream.write(body + "\n")  # frame-per-block for pipes/CI
        self._stream.flush()
        self._last_lines = lines
