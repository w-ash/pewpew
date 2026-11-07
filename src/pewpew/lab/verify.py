"""The content gate for looks: `python -m pewpew verify looks FILE|DIR`.

A look passes when it checks (pewpew.lab.check), and its render, made
fresh with no cache read, has no layer that raises, flashes at most 3
times a second (WCAG 2.3.1), is not black in every frame, and every knob
of every enabled layer changes the picture (pewpew.lab.liveness). A
render under one second fails, since it cannot show the flash rate
(`Metrics.flash_safe`). A folder means every `*.look.json` file in it. A
folder with no such file fails, and so does a file with no look: a gate
never passes on nothing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pewpew.lab.check import Ready, ready_looks
from pewpew.lab.geometry import AUTO, Geometry, parse_geometry
from pewpew.lab.liveness import dead, probe_knobs, unprobed
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, frame_count, limits, play, where
from pewpew.metrics import Metrics, measure
from pewpew.problems import Code, Problem, Refused
from pewpew.result import Result

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
    map_spec: str = AUTO,
    seconds: float = DEFAULT_SECONDS,
    fps: float = DEFAULT_FPS,
    seed: int = 0,
    pattern_dir: Path | None = None,
) -> Verification:
    """The verdict on each looks file of `paths`, a folder standing for
    its `*.look.json` files. Each look renders on `map_spec` (`auto`: each
    look's own) for `seconds` at `fps`, the features seeded `seed`. Raises
    ValueError for a bad map spec, seconds or fps."""
    frames = frame_count(seconds, fps)
    geometry: str | Geometry = map_spec if map_spec == AUTO else parse_geometry(map_spec)
    verdicts: list[FileVerdict] = []
    for path in paths:
        files = sorted(path.glob(PATTERN)) if path.is_dir() else [path]
        if not files:
            verdicts.append(_empty(path, "", f"no {PATTERN} file in {path}"))
        for file in files:
            try:
                looks = ready_looks(file, pattern_dir=pattern_dir)
            except Refused as exc:
                verdicts.append(FileVerdict(str(file), False, exc.problems))
                continue
            if not looks:
                verdicts.append(_empty(file, "looks", "the looks file holds no look"))
                continue
            judged = tuple(
                _judge(name, staged, where(geometry, staged), frames, fps, seed)
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
        failures += (f"knobs that do not change the picture: {', '.join(still)}",)
    return LookVerdict(name, not failures, failures, metrics, still)
