"""Golden-frame storage and perceptual comparison.

Model: pytest-mpl's baseline-plus-RMS-tolerance [S518], applied to raw
linear-light float frames. Not byte-exact, so cross-platform float noise
cannot fail a test; a real regression is orders of magnitude above the
tolerance. `rms` is the engine's own (pewpew.metrics), with the liveness
bar `LIVENESS_RMS`, so an agent's liveness check and the suite's agree.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np

from pewpew.metrics import rms

# Linear-light RMS: float noise sits below 1e-6, a visible regression above 1e-3.
DEFAULT_RMS_TOLERANCE = 1e-5


def save_golden(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, allow_pickle=False, **arrays)


def load_golden(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {name: data[name] for name in data.files}


def assert_matches_golden(
    path: Path,
    arrays: np.ndarray | Mapping[str, np.ndarray],
    tolerance: float = DEFAULT_RMS_TOLERANCE,
    regen: bool = False,
) -> None:
    """Compare `arrays` against the stored baseline; regen rewrites it
    instead. A single array is frames, stored as float32 under the name
    `frames`; named arrays keep their dtypes."""
    named = {"frames": arrays.astype(np.float32)} if isinstance(arrays, np.ndarray) else dict(arrays)
    if regen or not path.exists():
        save_golden(path, named)
        if regen:
            return
        raise AssertionError(
            f"golden baseline {path} was missing — wrote a fresh one; "
            "review it, commit it, and re-run"
        )
    baseline = load_golden(path)
    if baseline.keys() != named.keys():
        raise AssertionError(
            f"golden {path.name} holds {sorted(baseline)}, the test made {sorted(named)}; "
            "regenerate it with --regen-goldens and review the diff"
        )
    for name, array in named.items():
        error = rms(baseline[name], array)
        if not error <= tolerance:  # NaN on either side fails too
            raise AssertionError(
                f"golden mismatch for {path.name}[{name}]: RMS {error:.3e} > tolerance {tolerance:.0e}"
            )
