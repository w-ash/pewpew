"""The port equivalence proof: `src/pewpew/patterns/*` must render bit-
identically to the frozen `bench/authoring/*` study evidence that gates
ADR-005 (§12 item 2). Not RMS-tolerant — `np.array_equal` on the raw
float32, exact.

The study side is `bench/bench_authoring.py` itself: its classes and its
`run_sequence` (the `FakeClock` + `surface.set_now(t)` loop), never a copy,
which would be a second source of truth rather than a stronger test. The
port side is `pewpew.render_sequence`, which the docstring on `render.py`
claims reproduces the study's timestamps bit-for-bit; this file is what
proves that claim.
"""

from __future__ import annotations

import numpy as np
import pytest

from bench import bench_authoring as study_runner
from pewpew import render_sequence
from pewpew.classinfo import pattern_name
from pewpew.patterns import STUDY_CASES

SEED = study_runner.SEED  # 42
FPS = study_runner.FPS  # 60.0
FRAMES = study_runner.FRAMES  # 120

# Each study class paired by name with its port on the shared fixture table
# (pewpew.patterns.STUDY_CASES); the canopy set there has no prototype. A study
# pattern without a port fails collection.
PORTS = {pattern_name(port): (port, mapping) for port, mapping, _ in STUDY_CASES}
CASES = [pytest.param(study, *PORTS[study.name], id=study.name) for study, *_ in study_runner.STUDY]


def _assert_bit_exact(name: str, study: np.ndarray, port: np.ndarray) -> None:
    assert study.dtype == port.dtype, (
        f"{name}: dtype mismatch — study={study.dtype}, port={port.dtype}"
    )
    assert study.shape == port.shape, (
        f"{name}: shape mismatch — study={study.shape}, port={port.shape}"
    )
    if np.array_equal(study, port):
        return
    diff = np.abs(study.astype(np.float64) - port.astype(np.float64))
    per_frame_max = diff.reshape(diff.shape[0], -1).max(axis=1)
    bad_frame = int(np.argmax(per_frame_max))
    n_bad = int(np.count_nonzero(per_frame_max))
    pytest.fail(
        f"{name}: port is not bit-exact with the study — first (and worst) "
        f"divergence at frame {bad_frame} (max abs diff "
        f"{per_frame_max[bad_frame]:.3e}); {n_bad}/{diff.shape[0]} frames differ"
    )


@pytest.mark.parametrize("study_cls, port_cls, mapping", CASES)
def test_port_matches_study_bit_exact(study_cls, port_cls, mapping: np.ndarray) -> None:
    study_frames, violations = study_runner.run_sequence(study_cls, mapping, SEED, frames=FRAMES)
    assert violations == [], f"{study_cls.name}: frozen study evidence produced violations"

    port_frames = render_sequence(port_cls, mapping, seed=SEED, frames=FRAMES, fps=FPS)

    _assert_bit_exact(study_cls.name, study_frames, port_frames)
