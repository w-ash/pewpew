"""`Buffers`: the persistent state of one bind of an effect program, and
the lock that keeps it read-only while the program renders (ADR-005
amendment 2026-07-27, ADR-022).

An op declares its state through `BindCtx.buffer`, which allocates it
here under the node's id. `pixels` is the program's last frame, which
`prev()` reads. Each bind makes a new `Buffers`, so a new map starts every
array at its fill (no resampling [S219]). While `locked` holds, every
array is read-only, so a render cannot change state: state moves only in
`advance`. Purity is what golden frames and determinism rest on
(architecture §8).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import numpy as np


class Buffers(Mapping[str, np.ndarray]):
    """The arrays one bind of a program owns, by name, and `pixels`, the
    (n, 3) float32 last frame, at 0 until the first frame."""

    def __init__(self, n: int) -> None:
        self.pixels = np.zeros((n, 3), dtype=np.float32)
        self._arrays: dict[str, np.ndarray] = {}

    def declare(self, name: str, shape: int | tuple[int, ...], dtype: Any = np.float32,
                fill: float = 0.0) -> np.ndarray:
        """A new array of `shape` and `dtype` at `fill`, kept as `name`.
        Raises ValueError for a name already declared."""
        if name in self._arrays:
            raise ValueError(f"buffer {name!r} is already declared")
        array = np.full(shape, fill, dtype=dtype)
        self._arrays[name] = array
        return array

    def __getitem__(self, name: str) -> np.ndarray:
        return self._arrays[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._arrays)

    def __len__(self) -> int:
        return len(self._arrays)

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Every array, `pixels` included, read-only while the block runs,
        and writable again after it."""
        locked = [array for array in (self.pixels, *self._arrays.values()) if array.flags.writeable]
        for array in locked:
            array.setflags(write=False)
        try:
            yield
        finally:
            for array in locked:
                array.setflags(write=True)
