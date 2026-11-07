"""Render handles and the render cache (ADR-023).

A handle is a content address: `r1-` and the first 20 hex digits of the
SHA-256 of what a render depends on, written as canonical JSON (`handle`):
the normalized look, the mapping's numbers, seconds, fps, seed, the engine
fingerprint and each layer's pattern source. The same render always has
the same handle, in any process; a changed input has another.

`ENGINE` fingerprints the code that renders: the source of every module of
the `pewpew` package, read once when this module loads, and the Python and
NumPy versions. A package version would not do: it stays the same between
commits.

`Cache` keeps rendered frames under `$PEWPEW_CACHE` (default
`~/.cache/pewpew/renders`), one folder per handle, and drops the least
recently used once the folders pass a size cap. A handle's folder also
holds the sheets drawn of it, and can hold only those once its entry is
dropped. It only saves time: a render it does not hold is rendered again,
and a handle it no longer holds is `Expired`.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import time
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeGuard

import numpy as np

from pewpew.jsonfile import temp_beside
from pewpew.lab.geometry import Geometry
from pewpew.mapping import Grouping

HANDLE = re.compile(r"r1-[0-9a-f]{20}")
CACHE_ENV = "PEWPEW_CACHE"
CAP_BYTES = 512 * 2**20

_PACKAGE = Path(__file__).resolve().parent.parent
_FRAMES = "frames.npz"
_ENTRY = "entry.json"


def fingerprint(package: Path = _PACKAGE) -> str:
    """16 hex digits of SHA-256 over the Python and NumPy versions and the
    path and bytes of every `.py` file under `package`, in path order."""
    h = hashlib.sha256(f"python {platform.python_version()} numpy {np.__version__}\n".encode())
    for path in sorted(package.rglob("*.py")):
        h.update(path.relative_to(package).as_posix().encode() + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()[:16]


ENGINE = fingerprint()


def handle(parts: Mapping[str, Any]) -> str:
    """The handle of a render that depends on `parts` (JSON data)."""
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "r1-" + hashlib.sha256(text.encode()).hexdigest()[:20]


def is_handle(text: object) -> TypeGuard[str]:
    return isinstance(text, str) and HANDLE.fullmatch(text) is not None


@dataclass(frozen=True, slots=True, eq=False)
class Entry:
    """What the cache holds for one handle: the frames, the geometry they
    were rendered on, and the render's record (JSON data)."""

    frames: np.ndarray
    geometry: Geometry
    record: dict[str, Any]


class Cache:
    """Rendered frames by handle, in `root`, at most `cap` bytes once a
    store has evicted (the newest entry stays even when it alone passes
    `cap`). `now` gives the time in ns that marks an entry used."""

    def __init__(self, root: Path | None = None, cap: int = CAP_BYTES, now: Callable[[], int] = time.time_ns) -> None:
        self.root = Path(root) if root is not None else default_root()
        self.cap = cap
        self._now = now

    def path(self, handle: str, name: str) -> Path:
        """The file `name` in the folder of `handle`."""
        return self.root / handle / name

    def load(self, handle: str) -> Entry | None:
        """The entry of `handle`, marked used where the cache can be
        written, or None when the cache does not hold it."""
        try:
            with np.load(self.path(handle, _FRAMES), allow_pickle=False) as data:
                arrays = {name: data[name] for name in data.files}
            record = json.loads(self.path(handle, _ENTRY).read_text())
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):  # gone, or half written by a crash
            return None
        with contextlib.suppress(OSError):  # read-only, or another user's: the entry still answers
            self._touch(handle)
        grouping = Grouping(arrays["centres"], arrays["of"]) if "of" in arrays else None
        return Entry(arrays["frames"], Geometry(record["map"], arrays["positions"], grouping), record)

    def store(self, handle: str, frames: np.ndarray, geometry: Geometry, record: Mapping[str, Any]) -> None:
        """Keep `frames`, rendered on `geometry`, and `record` (JSON data;
        the geometry's spec is added as its "map") under `handle`, then
        evict down to the cap. An entry appears whole or not at all. Raises
        OSError as the file system does."""
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = temp_beside(self.root / handle)
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        try:
            arrays = {"frames": frames, "positions": geometry.mapping}
            if geometry.grouping is not None:
                arrays |= {"centres": geometry.grouping.centres, "of": geometry.grouping.of}
            np.savez(tmp / _FRAMES, allow_pickle=False, **arrays)
            (tmp / _ENTRY).write_text(json.dumps({**record, "map": geometry.spec}))
            folder = self.root / handle
            try:
                tmp.rename(folder)
            except OSError:
                if not folder.is_dir():
                    raise
                # Stored by another process first, or holding only sheets: the same handle has the same
                # frames, so move them in, the entry last, as `load` and `evict` read it.
                for name in (_FRAMES, _ENTRY):
                    os.replace(tmp / name, folder / name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self._touch(handle)
        self.evict(keep=handle)

    def evict(self, keep: str | None = None) -> None:
        """Remove the least recently used entries until the rest fit in
        `cap`, never `keep`."""
        entries = []
        for folder in self.root.iterdir():
            if not is_handle(folder.name):
                continue
            entry = folder / _ENTRY
            try:
                used = (entry if entry.exists() else folder).stat().st_mtime_ns  # sheets only: when last drawn
                size = sum(f.stat().st_size for f in folder.iterdir())
            except OSError:
                continue  # removed meanwhile
            entries.append((used, folder.name, size))
        total = sum(size for _, _, size in entries)
        for _, name, size in sorted(entries):
            if total <= self.cap:
                break
            if name != keep:
                shutil.rmtree(self.root / name, ignore_errors=True)
                total -= size

    def _touch(self, handle: str) -> None:
        now = self._now()
        os.utime(self.path(handle, _ENTRY), ns=(now, now))


def default_root() -> Path:
    """`$PEWPEW_CACHE`, else `~/.cache/pewpew/renders`."""
    configured = os.environ.get(CACHE_ENV)
    return Path(configured) if configured else Path.home() / ".cache" / "pewpew" / "renders"


class Expired(Exception):
    """A render handle that the cache no longer holds."""

    def __init__(self, handle: str) -> None:
        self.handle = handle
        super().__init__(
            f"handle {handle} expired from the render cache; render again with the same look, map, seconds, "
            "fps and seed, which gives the same handle"
        )

    def to_json(self) -> dict[str, Any]:
        return {"handle": self.handle, "expired": True, "reason": str(self)}
