"""The port equivalence proof: `src/pewpew/patterns/*` must render bit-
identically to the frozen `bench/authoring/*` study evidence that gates
ADR-005 (§12 item 2). Not RMS-tolerant — `np.array_equal` on the raw
float32, exact.

Drives the prototype exactly as `bench/bench_authoring.py::run_sequence`
does (imports the `authoring` package the same way, via the same sys.path
insert, and literally reuses `run_sequence` itself rather than
re-implementing its `FakeClock` + `surface.set_now(t)` loop — any
divergence there would be a second source of truth, not a stronger test).
The port side is `pewpew.render_sequence`, which the docstring on
`render.py` claims reproduces the study's timestamps bit-for-bit; this file
is what proves that claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = REPO_ROOT / "bench"
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

import bench_authoring as study_runner  # noqa: E402  (needs the sys.path insert above)
from authoring.comet import Comet as StudyComet  # noqa: E402
from authoring.fire import Fire as StudyFire  # noqa: E402
from authoring.geq import Geq as StudyGeq  # noqa: E402
from authoring.plasma import Plasma as StudyPlasma  # noqa: E402
from authoring.sdf3d import Sdf3d as StudySdf3d  # noqa: E402

from pewpew import render_sequence
from pewpew.patterns import STUDY_CASES

SEED = study_runner.SEED  # 42
FPS = study_runner.FPS  # 60.0
FRAMES = study_runner.FRAMES  # 120

# The study class zipped onto the shared (port, fixture) table: pairing a
# prototype with its port is this file's whole subject, so only that pairing
# lives here. Order follows pewpew.patterns.STUDY_CASES.
STUDY_CLASSES = [StudyPlasma, StudyComet, StudyGeq, StudyFire, StudySdf3d]

CASES = [
    pytest.param(study, port, mapping, id=port.name)
    for study, (port, mapping) in zip(STUDY_CLASSES, STUDY_CASES, strict=True)
]


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
