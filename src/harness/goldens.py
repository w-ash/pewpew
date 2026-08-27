"""Golden-frame storage and perceptual comparison.

Model: pytest-mpl's baseline-plus-RMS-tolerance [S518], applied to raw
linear-light float frames instead of rendered images. Byte-exact equality is
deliberately not required — cross-platform float noise must not fail a test,
real regressions (wrong color, wrong motion) are orders of magnitude above
the tolerance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# Linear-light RMS. Empirically tiny float noise sits < 1e-6; visible
# regressions sit > 1e-3. Revisit with a perceptual (e.g. OKLab) metric when
# the color pipeline lands (ADR-001).
DEFAULT_RMS_TOLERANCE = 1e-5

# The other side of the same scale: the bar an input must clear to count as
# having changed the picture at all. Used wherever a test asserts that wiggling
# something (a seed, a parameter) is not a no-op.
LIVENESS_RMS = 1e-3


def save_golden(path: Path, frames: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, frames=frames.astype(np.float32))


def load_golden(path: Path) -> np.ndarray:
    with np.load(path) as data:
        return data["frames"]


def rms(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        raise AssertionError(f"shape mismatch: {a.shape} vs {b.shape}")
    return float(np.sqrt(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)))


def assert_matches_golden(
    path: Path,
    frames: np.ndarray,
    tolerance: float = DEFAULT_RMS_TOLERANCE,
    regen: bool = False,
) -> None:
    """Compare frames against the stored baseline; regen rewrites it instead."""
    if regen or not path.exists():
        save_golden(path, frames)
        if regen:
            return
        raise AssertionError(
            f"golden baseline {path} was missing — wrote a fresh one; "
            "review it, commit it, and re-run"
        )
    baseline = load_golden(path)
    error = rms(baseline, frames)
    if error > tolerance:
        raise AssertionError(
            f"golden mismatch for {path.name}: RMS {error:.3e} > tolerance {tolerance:.0e}"
        )
