"""The golden harness itself (src/harness/goldens.py): a comparison that
cannot fail is no tripwire."""

from __future__ import annotations

import numpy as np
import pytest

from harness.goldens import assert_matches_golden, save_golden

FRAMES = np.linspace(0.0, 1.0, 24, dtype=np.float32).reshape(2, 4, 3)


def test_a_nan_output_or_baseline_fails_the_comparison(tmp_path):
    """NaN > tolerance is False, so a NaN RMS once passed every golden, and
    the renderer leaves finiteness to the goldens."""
    path = tmp_path / "g.npz"
    save_golden(path, {"frames": FRAMES})
    assert_matches_golden(path, FRAMES)
    broken = FRAMES.copy()
    broken[0, 0, 0] = np.nan
    with pytest.raises(AssertionError, match=r"RMS nan > tolerance"):
        assert_matches_golden(path, broken)
    save_golden(path, {"frames": broken})
    with pytest.raises(AssertionError, match=r"RMS nan > tolerance"):
        assert_matches_golden(path, FRAMES)  # a baseline holding NaN passes nothing


def test_named_arrays_must_match_the_baseline_names(tmp_path):
    path = tmp_path / "g.npz"
    save_golden(path, {"a": FRAMES})
    with pytest.raises(AssertionError, match=r"holds \['a'\], the test made \['b'\]"):
        assert_matches_golden(path, {"b": FRAMES})
