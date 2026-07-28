"""Shared bench pieces — one definition, imported by every bench script.

The plasma kernel and the mapping generator live here because two benches
time them and both reports claim they are the same workload. They were
briefly duplicated; a divergence would have silently invalidated that claim
(bench_throughput's agreement gate only covers its own transcriptions).
"""

from __future__ import annotations

import datetime
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

GOLDEN = 0.6180339887498949  # seed→phase hash, same convention as SolidPulse
TWO_PI = 2.0 * math.pi


def make_mapping(n: int, seed: int = 7) -> np.ndarray:
    """Seeded random 3D point cloud in [0,1] — honest 3D coords, no y=z=0."""
    rng = np.random.default_rng(seed)
    return rng.random((n, 3), dtype=np.float32)


def plasma_numpy(t: float, mapping: np.ndarray, seed: int) -> np.ndarray:
    """Transcendental-heavy plasma (~8 sin per pixel) — the representative load.

    Scalar spec is documented in bench_throughput.py's kernel A block; this is
    the vectorized transcription of it, and bench_throughput's agreement gate
    checks the loop and numba transcriptions against this function.
    """
    phase = (seed * GOLDEN) % 1.0
    u = 4.0 * mapping[:, 0]
    v = 4.0 * mapping[:, 1]
    w = 4.0 * mapping[:, 2]
    a = np.sin(u * 1.7 + t * 1.3)
    b = np.sin(v * 2.3 - t * 0.7 + np.sin(u * 3.1 + t))
    c = np.sin((u + v + w) * 1.9 + t * 2.1 + TWO_PI * phase)
    p = (a + b + c) / 3.0
    frame = np.empty((mapping.shape[0], 3), dtype=np.float32)
    frame[:, 0] = 0.5 + 0.5 * np.sin(np.pi * p)
    frame[:, 1] = 0.5 + 0.5 * np.sin(np.pi * p + 2.0943951023931953)
    frame[:, 2] = 0.5 + 0.5 * np.sin(np.pi * p + 4.1887902047863905)
    return frame


def try_cmd(cmd: list[str]) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def cpu_model() -> str | None:
    if sys.platform == "darwin":
        return try_cmd(["sysctl", "-n", "machdep.cpu.brand_string"])
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith(("model name", "model")):
                    return line.split(":", 1)[1].strip()
        except Exception:
            return None
    return None


def gather_meta(label: str, **extra) -> dict:
    """Host/toolchain provenance stamped into every results artifact."""
    return {
        "label": label,
        "date": datetime.date.today().isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu_model(),
        "cpu_count": __import__("os").cpu_count(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "git_sha": try_cmd(["git", "rev-parse", "--short", "HEAD"]),
        **extra,
    }
