"""The content gate for looks: `python -m pewpew verify looks FILE|DIR`.

A look passes when it checks (pewpew.lab.check), and its render, made
fresh with no cache read, has no layer that raises, flashes at most 3
times a second (WCAG 2.3.1), is not black in every frame, and every knob
of every enabled layer changes the picture (pewpew.lab.liveness). Each
of its colorways renders too, as the look with that colorway set, and
passes the same render gates (no layer raises, the flash rate, not all
black); its knobs are not probed again. Each pair of colorways must
differ by more than a knob must (`LIVENESS_RMS`), so no colorway repeats
another. A render under one second fails, since it cannot show the flash rate
(`Metrics.flash_safe`). A folder means every `*.look.json` file in it. A
folder with no such file fails, and so does a file with no look: a gate
never passes on nothing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pewpew.lab.check import Ready, painted, ready_looks
from pewpew.lab.geometry import Geometry, parse_geometry
from pewpew.lab.liveness import PATIENT_SECONDS, dead, probe_knobs, unprobed
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, frame_count, limits, play
from pewpew.mapping import DEFAULT_MAP
from pewpew.metrics import LIVENESS_RMS, Metrics, measure, rms
from pewpew.problems import Code, Problem, Refused
from pewpew.result import Result
from pewpew.sinks.sink import sanitize

PATTERN = "*.look.json"  # the files a folder stands for


@dataclass(frozen=True, slots=True)
class LookVerdict(Result):
    """One look's verdict: its name ("" for a file of one look), whether
    it passes, why not, its metrics (None when it did not render), and the
    knobs that do not change the picture."""

    name: str
    ok: bool
    failures: tuple[str, ...]
    metrics: Metrics | None
    dead: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FileVerdict(Result):
    """One file's verdict: the problems that stop it checking, or each of
    its looks' verdicts."""

    file: str
    ok: bool
    problems: tuple[Problem, ...] = ()
    looks: tuple[LookVerdict, ...] = ()


@dataclass(frozen=True)
class Verification(Result):
    """Whether every look of every file passes, and each file's verdict."""

    ok: bool
    files: tuple[FileVerdict, ...]


def verify_looks(
    paths: Iterable[Path],
    *,
    map_spec: str = DEFAULT_MAP,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    seed: int = 0,
) -> Verification:
    """The verdict on each looks file of `paths`, a folder standing for
    its `*.look.json` files. Each look renders on `map_spec` for `seconds` at `fps`, the features seeded `seed`. Raises
    ValueError for a bad map spec, seconds or fps."""
    frames = frame_count(seconds, fps)
    geometry = parse_geometry(map_spec)
    verdicts: list[FileVerdict] = []
    for path in paths:
        files = sorted(path.glob(PATTERN)) if path.is_dir() else [path]
        if not files:
            verdicts.append(_empty(path, "", f"no {PATTERN} file in {path}"))
        for file in files:
            try:
                looks = ready_looks(file)
            except Refused as exc:
                verdicts.append(FileVerdict(str(file), False, exc.problems))
                continue
            if not looks:
                verdicts.append(_empty(file, "looks", "the looks file holds no look"))
                continue
            judged = tuple(
                _judge(name, staged, geometry, frames, fps, seed)
                for name, staged in looks.items()
            )
            verdicts.append(FileVerdict(str(file), all(v.ok for v in judged), (), judged))
    return Verification(all(v.ok for v in verdicts), tuple(verdicts))


def _empty(where: Path, path: str, reason: str) -> FileVerdict:
    """The verdict on `where`, which holds nothing to pass."""
    return FileVerdict(str(where), False, (Problem(path, Code.MISSING, reason),))


def _judge(name: str, staged: Ready, geometry: Geometry, frames: int, fps: float, seed: int) -> LookVerdict:
    try:
        rendered, errors = play(staged, geometry, frames, fps, seed)
    except Refused as exc:
        return LookVerdict(name, False, tuple(str(p) for p in exc.problems), None)
    metrics = measure(rendered, fps)
    probed = probe_knobs(staged, geometry, seed)
    still = dead(probed)
    failures = (*errors, *limits(metrics), *unprobed(probed))
    if still:
        failures += (f"knobs that do not change the picture in {PATIENT_SECONDS:g} s: {', '.join(still)}",)
    failures += _colorways(staged, geometry, frames, fps, seed)
    return LookVerdict(name, not failures, failures, metrics, still)


def _colorways(staged: Ready, geometry: Geometry, frames: int, fps: float, seed: int) -> tuple[str, ...]:
    """Why `staged`'s colorways fail the gate (module docstring): each
    one's render gates, then each pair that shows the same picture."""
    failures: list[str] = []
    shown: dict[str, np.ndarray] = {}
    for colorway in staged.look.colorways:
        at = f"colorway {colorway!r}"
        try:
            rendered, errors = play(painted(staged, colorway), geometry, frames, fps, seed)
        except Refused as exc:
            failures += (f"{at}: {problem}" for problem in exc.problems)
            continue
        failures += (f"{at}: {reason}" for reason in (*errors, *limits(measure(rendered, fps))))
        shown[colorway] = sanitize(rendered)
    names = list(shown)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            change = rms(shown[a], shown[b])
            if change <= LIVENESS_RMS:
                failures.append(f"colorways {a!r} and {b!r} show the same picture (RMS {change:.2g}); "
                                "give each its own colours")
    return tuple(failures)
