"""Phase-0 authoring-surface prototype runner — §12 item 2 (gates ADR-005).

Drives the five canonical patterns (bench/authoring/) against the
prototyped ADR-005 contract for 120 deterministic frames each, validates
output (shape/dtype/finite/[0,1]), gates on determinism (full sequence
rendered twice from fresh instances must hash identically), and emits a
JSON artifact to bench/results/. The stumble inventory itself is the
hand-written report next to that JSON — this runner only contributes the
mechanical census (np.where/np.select occurrences + STUMBLE tags per file).

    uv run python bench/bench_authoring.py [--show] [--pattern <name>]

L1 one-off study (test-and-feedback.md §4) — not a pytest rig. The bench
harness may use wall-clock-free FakeClock only; nothing here is timed.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

BENCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH_DIR))

from authoring import surface
from authoring.comet import Comet
from authoring.fire import Fire
from authoring.geq import Geq
from authoring.plasma import Plasma
from authoring.sdf3d import Sdf3d
from authoring.surface import FakeFeatures, grid, lattice, line
from harness.clock import FakeClock

SEED = 42
FPS = 60.0
FRAMES = 120

# (class, mapping, fixture label, display shape for --show)
STUDY = [
    (Plasma, line(300), "line(300)", ("line", 300)),
    (Comet, line(300), "line(300)", ("line", 300)),
    (Geq, grid(16, 16), "grid(16x16)", ("grid", (16, 16))),
    (Fire, grid(16, 32), "grid(16x32)", ("grid", (16, 32))),
    (Sdf3d, lattice(10), "lattice(10^3)", ("lattice", 10)),
]


def run_sequence(cls, mapping: np.ndarray, seed: int, frames: int = FRAMES):
    """Render the full deterministic sequence; returns (frames arr, violations)."""
    n = mapping.shape[0]
    pat = cls()
    pat._setup(n, seed)
    feats = FakeFeatures(seed)
    x, y, z = mapping[:, 0], mapping[:, 1], mapping[:, 2]
    index = np.arange(n, dtype=np.int32)
    out = np.empty((frames, n, 3), dtype=np.float32)
    violations = []
    prev_t = 0.0
    for i, t in enumerate(FakeClock().frames(frames, fps=FPS)):
        dt = t - prev_t
        prev_t = t
        surface.set_now(t)
        pat.before_render(dt, feats.at(t))
        frame = pat.render(x, y, z, index)
        if frame.shape != (n, 3):
            violations.append({"frame": i, "kind": f"shape {frame.shape}"})
        if frame.dtype != np.float32:
            violations.append({"frame": i, "kind": f"dtype {frame.dtype}"})
        if not np.all(np.isfinite(frame)):
            violations.append({"frame": i, "kind": "non-finite"})
        elif frame.min() < 0.0 or frame.max() > 1.0:
            violations.append({"frame": i, "kind": f"range [{frame.min():.3g}, {frame.max():.3g}]"})
        pat.pixels = frame  # previous-frame buffer for the next render
        out[i] = frame
    return out, violations


def seq_hash(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


def census(pattern_file: Path) -> dict:
    src = pattern_file.read_text()
    code_lines = [
        ln for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("#")
    ]
    return {
        "np_where": len(re.findall(r"np\.where\(", src)),
        "np_select": len(re.findall(r"np\.select\(", src)),
        "stumble_tags": sorted(set(int(m) for m in re.findall(r"STUMBLE-(\d+)", src))),
        "code_lines": len(code_lines),
    }


def gather_meta() -> dict:
    def try_cmd(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip() or None
        except Exception:
            return None

    return {
        "date": datetime.date.today().isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "git_sha": try_cmd(["git", "rev-parse", "--short", "HEAD"]),
        "seed": SEED,
        "frames": FRAMES,
        "fps": FPS,
    }


# ---- ANSI eyeball (--show); display-only, never touches the data path -------


def _row_to_ansi(row: np.ndarray) -> str:
    disp = (np.clip(row, 0.0, 1.0) ** (1 / 2.2) * 255).astype(np.uint8)
    return "".join(f"\x1b[48;2;{r};{g};{b}m  " for r, g, b in disp) + "\x1b[0m"


def show_frame(frame: np.ndarray, display) -> None:
    kind, dims = display
    if kind == "line":
        cols = np.linspace(0, dims - 1, min(dims, 72)).astype(int)
        print(_row_to_ansi(frame[cols]))
    elif kind == "grid":
        w, h = dims
        panel = frame.reshape(h, w, 3)
        for row in reversed(range(h)):  # y=1 at top
            print(_row_to_ansi(panel[row]))
    elif kind == "lattice":
        k = dims
        cube = frame.reshape(k, k, k, 3)  # [z][y][x]
        for row in reversed(range(k)):
            print("  ".join(_row_to_ansi(cube[zi, row]) for zi in range(k)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true", help="ANSI-render frames 0/30/60/119")
    ap.add_argument("--pattern", default=None, help="run only this pattern")
    ap.add_argument("--out", default=None, help="JSON output path")
    args = ap.parse_args()

    meta = gather_meta()
    entries = []
    failed = False

    for cls, mapping, fixture, display in STUDY:
        if args.pattern and cls.name != args.pattern:
            continue
        frames_a, violations = run_sequence(cls, mapping, SEED)
        frames_b, _ = run_sequence(cls, mapping, SEED)
        frames_alt, _ = run_sequence(cls, mapping, SEED + 1)
        h_a, h_b, h_alt = seq_hash(frames_a), seq_hash(frames_b), seq_hash(frames_alt)
        deterministic = h_a == h_b
        seed_load_bearing = h_a != h_alt  # informational, not gated

        entry = {
            "pattern": cls.name,
            "fixture": fixture,
            "n": mapping.shape[0],
            "deterministic": deterministic,
            "sequence_sha256": h_a,  # informational golden (same-platform libm)
            "seed_load_bearing": seed_load_bearing,
            "violations": violations,
            **census(BENCH_DIR / "authoring" / f"{cls.name}.py"),
        }
        entries.append(entry)

        status = "ok" if deterministic and not violations else "FAIL"
        print(
            f"{cls.name:<12} {fixture:<14} det={'yes' if deterministic else 'NO'} "
            f"violations={len(violations)} np.where={entry['np_where']} "
            f"stumbles={entry['stumble_tags']} loc={entry['code_lines']}  [{status}]"
        )
        if violations:
            for v in violations[:5]:
                print(f"    frame {v['frame']}: {v['kind']}")
        failed = failed or not deterministic or bool(violations)

        if args.show:
            for fi in (0, 30, 60, FRAMES - 1):
                print(f"\n{cls.name} — frame {fi} (t={fi / FPS + 1 / FPS:.2f}s)")
                show_frame(frames_a[fi], display)
            print()

    if not args.pattern:
        out_path = Path(args.out) if args.out else (
            BENCH_DIR / "results" / f"authoring-{meta['date']}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"meta": meta, "patterns": entries}, indent=2) + "\n")
        print(f"\nresults written to {out_path}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
