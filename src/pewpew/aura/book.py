"""The looks file: saved looks, the idle cycle and the room-event triggers.

A look is ADR-006's preset shape, a partial state: its layers
(pewpew.compose.stack), bottom first, and optionally the master. It also
carries its own `fade` time and a `cycle` flag for the idle cycle. Looks
live in one JSON file on the laptop (`run LOOKS`), never on the
boards: writing a WLED preset freezes the board's lights for seconds
[S554]. A `.look.json` file is a looks file too. The file, version 4
(ADR-006 amendments 2026-10-30 and "one shape per wire fact"; layered looks
2026-11-05):

    {
      "version": 4,
      "current": "dusk",
      "looks": {
        "dusk": {"seed": 0, "master": 0.6, "fade": 4.0, "cycle": true,
                 "layers": [
                   {"id": "base", "opacity": 1.0, "blend": "normal", "enabled": true, "out": "wash",
                    "nodes": {"wash": {"op": "pattern", "args": {"pattern": "wash",
                                                                 "color": {"h": 30.0, "s": 0.8, "v": 1.0},
                                                                 "speed": 0.01}}}},
                   {"id": "sparks", "opacity": 0.6, "blend": "screen", "out": "sparkle",
                    "nodes": {"sparkle": {"op": "pattern", "args": {"pattern": "sparkle", "tail": 0.4}}}}],
                 "signals": {"breath": {"op": "lfo", "args": {"rate": 0.05}}},
                 "routes": [{"source": "breath", "path": "layers.sparks.opacity", "depth": 0.3}],
                 "front": ["layers.base.wash.speed"]},
        "breathe": {"layers": [{"id": "base", "nodes": {"pulse": {"op": "pattern",
                                                                  "args": {"pattern": "pulse", "depth": 0.5}}}}]}
      },
      "cycle": {"idle": 300, "each": [40, 90], "rounds": 0, "end": null,
                "seed": 0, "window": 2, "fresh": 0, "weights": {"dusk": 2}},
      "triggers": {
        "cue1": {"look": "breathe", "hold": 8, "priority": "button",
                 "debounce": 0.05, "cooldown": 1.0},
        "door": {"look": null, "priority": "sensor"}
      },
      "notes": "anything; kept as written"
    }

`looks` keeps its order, which is the order the page shows. Each look's
body (its layers and their programs, its signals, routes and front knobs,
seed, master, fade and cycle) is the effect-program codec's
(pewpew.fx.codec), which reads and writes it; this module holds the file
around it. A node's `pattern` arg names its pattern
by its name in the catalog (pewpew.load). A pattern's params are judged at recall, and `pattern_problems`
lists at launch what no longer fits. `current` is the look last recalled
or saved, so a restart comes back in it.

`cycle` is the idle cycle, ADR-006's playlist under pewpew's own names,
run by a seeded director (pewpew.aura.director): after `idle` seconds of
engine time with no operator input, it recalls the looks whose `cycle` is
true in a random order, each as likely as its weight in `weights` (1 when
not named there) but none of the last `window` it played, each for a dwell
of `each` seconds (a number, or a range `[min, max]` it draws from); every
`fresh`th slot (0, the default, is never) it plays a look made fresh
(pewpew.fx.surprise) instead, unsaved. After `rounds` rounds of as many
slots as there are looks (0 is forever) it recalls `end` (null stays on
the last). `seed` seeds its draws, so the same file plays the same order.
`idle` null turns it off. Any operator input stops it.

`version` is required. A file of another version, or of none, is refused:
move it aside and save the looks again from the page. There is no
migration.

`triggers` maps a room-event name to what the event does
(pewpew.aura.triggers): `look` names a look to hold as a temporary
override for `hold` seconds of engine time before the aura returns to the
look it left (null: the event only reaches the pattern as data).
`priority` is its class, one of `PRIORITIES`; `debounce` and `cooldown`
are seconds. Every key but the name is optional. The page never edits
this section; a rewrite keeps it, and a look that a trigger names cannot
be deleted from the page.

The loader refuses anything malformed with every problem listed, so a bad
file fails at launch, not mid-run. A look whose pattern no longer loads,
or whose params no longer fit it, is not malformed: `pattern_problems`
lists those for a launch warning, and a recall runs the look with the
params that still fit, or refuses it.

`check_name` is the aura's request check for a look's name too, on any
thread. Names only: a look name and a pattern name may cross the preview
socket; the file's path never does.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from pewpew.compose.controls import layer_address, look_controls
from pewpew.compose.modulation import route_problems
from pewpew.compose.stack import Look, is_seed
from pewpew.fx.codec import decode_look, encode_look
from pewpew.fx.compile import check
from pewpew.jsonfile import ProblemsError, is_number, parse_json

VERSION = 4
MAX_LOOKS = 64
MAX_NAME = 32  # characters in a look's name
# Letters and digits first, then also space, "_" and "-": short enough for a
# phone button, and nothing that reads as a path.
_NAME = re.compile(rf"[A-Za-z0-9][A-Za-z0-9 _-]{{0,{MAX_NAME - 1}}}")

_TOP_KEYS = {"version", "current", "looks", "cycle", "triggers", "notes"}
_CYCLE_KEYS = {"idle", "each", "rounds", "end", "seed", "window", "fresh", "weights"}
_TRIGGER_KEYS = {"look", "hold", "priority", "debounce", "cooldown"}

# Trigger priority classes, lowest first; a class's rank is its index.
PRIORITIES = ("sensor", "button", "performer", "operator")
MAX_TRIGGERS = 32
DEFAULT_HOLD = 10.0
MAX_HOLD = 3600.0
DEFAULT_DEBOUNCE = 0.05
DEFAULT_COOLDOWN = 1.0
MAX_GAP = 600.0  # the longest debounce or cooldown, in seconds


class LookError(ProblemsError):
    """The looks file is malformed."""


def check_name(name: object, noun: str = "look") -> str | None:
    """Why `name` cannot name a look (or a `noun`), or None. Never raises."""
    if not isinstance(name, str):
        return f"a {noun} name is text, got {name!r}"
    if not _NAME.fullmatch(name):
        return (
            f"bad {noun} name {name!r}: 1 to {MAX_NAME} letters, digits, spaces, '_' or '-', "
            "starting with a letter or digit"
        )
    return None


@dataclass(frozen=True)
class CycleConfig:
    """The idle cycle's settings; see the module docstring. `each` is a
    dwell in seconds, or a `(min, max)` range of them."""

    idle: float | None = 300.0
    each: float | tuple[float, float] = 60.0
    rounds: int = 0
    end: str | None = None
    seed: int = 0
    window: int = 2
    fresh: int = 0
    weights: Mapping[str, float] = field(default_factory=dict)

    @property
    def dwell(self) -> tuple[float, float]:
        """The shortest and longest dwell, in seconds."""
        return self.each if isinstance(self.each, tuple) else (self.each, self.each)

    def to_json(self) -> dict:
        return {"idle": self.idle, "each": list(self.each) if isinstance(self.each, tuple) else self.each,
                "rounds": self.rounds, "end": self.end, "seed": self.seed, "window": self.window,
                "fresh": self.fresh, "weights": dict(self.weights)}


@dataclass(frozen=True)
class Trigger:
    """What one room event does; see the module docstring."""

    look: str | None = None
    hold: float = DEFAULT_HOLD
    priority: str = "button"
    debounce: float = DEFAULT_DEBOUNCE
    cooldown: float = DEFAULT_COOLDOWN

    @property
    def rank(self) -> int:
        return PRIORITIES.index(self.priority)

    def to_json(self) -> dict:
        return {"look": self.look, "hold": self.hold, "priority": self.priority,
                "debounce": self.debounce, "cooldown": self.cooldown}


@dataclass(frozen=True)
class LookBook:
    """The whole looks file as one value. Every change makes a new book, so
    a reader on another thread never sees a dict change under it."""

    looks: Mapping[str, Look] = field(default_factory=dict)
    current: str | None = None
    cycle: CycleConfig = field(default_factory=CycleConfig)
    notes: Any = None  # the file's free "notes" value, written back unchanged
    triggers: Mapping[str, Trigger] = field(default_factory=dict)

    @property
    def in_cycle(self) -> list[str]:
        """The looks the idle cycle plays, in file order."""
        return [name for name, look in self.looks.items() if look.cycle]

    def after(self, name: str | None) -> list[str]:
        """Every look but `name`, in the idle cycle's order from `name` on:
        the looks of the cycle (`in_cycle`) after it, round to the start,
        then the others in file order."""
        cycle = self.in_cycle
        if name in cycle:
            i = cycle.index(name)
            cycle = cycle[i + 1:] + cycle[:i]
        return [*cycle, *(other for other in self.looks if other not in cycle and other != name)]

    def with_look(self, name: str, look: Look) -> LookBook:
        return replace(self, looks={**self.looks, name: look})

    def without(self, name: str) -> LookBook:
        looks = {k: v for k, v in self.looks.items() if k != name}
        cycle = replace(self.cycle, end=None if self.cycle.end == name else self.cycle.end,
                        weights={k: w for k, w in self.cycle.weights.items() if k != name})
        current = None if self.current == name else self.current
        return replace(self, looks=looks, current=current, cycle=cycle)

    def with_current(self, name: str | None) -> LookBook:
        return replace(self, current=name)

    def to_bytes(self) -> bytes:
        doc = {
            "version": VERSION,
            "current": self.current,
            "looks": {name: encode_look(look) for name, look in self.looks.items()},
            "cycle": self.cycle.to_json(),
        }
        if self.triggers:
            doc["triggers"] = {name: trig.to_json() for name, trig in self.triggers.items()}
        if self.notes is not None:
            doc["notes"] = self.notes
        return (json.dumps(doc, indent=2) + "\n").encode()


# ---- reading and writing the file -----------------------------------------


def parse_looks(data: bytes | str, *, cap: float = 1.0) -> LookBook:
    """Validate looks-file JSON text. Raises LookError listing every problem.

    `cap` is the launch's master cap: a stored master above it is refused.
    Which patterns and params a look names is not checked here; see
    `pattern_problems`.
    """
    doc = parse_json(data, LookError)
    if not isinstance(doc, dict):
        raise LookError(["a looks file is a JSON object with 'looks'"])
    if doc.get("version") != VERSION:
        found = f"is version {doc['version']!r}" if "version" in doc else "has no version"
        if "version" not in doc and "layers" in doc:  # one look, as the lab and a push take it
            fix = (f'this is a single look, and a looks file wraps it: {{"version": {VERSION}, "current": "look", '
                   '"looks": {"look": <this look>}}')
        else:
            fix = "move it aside and save the looks again from the page"
        raise LookError([f"looks file {found}; this pewpew reads version {VERSION}: {fix}"])
    problems: list[str] = []
    for key in sorted(set(doc) - _TOP_KEYS):
        problems.append(f"unknown key {key!r}; expected {', '.join(sorted(_TOP_KEYS))}")
    raw = doc.get("looks", {})
    looks: dict[str, Look] = {}
    if not isinstance(raw, dict):
        problems.append("'looks' is an object of name: look")
        raw = {}
    if len(raw) > MAX_LOOKS:
        problems.append(f"{len(raw)} looks; at most {MAX_LOOKS}")
    for name, item in raw.items():
        if (reason := check_name(name)) is not None:
            problems.append(reason)
            continue
        look, found = decode_look(item, where=f"look {name!r}", cap=cap)
        problems.extend(found)
        if look is not None:
            looks[name] = look
    current = doc.get("current")
    if current is not None and (not isinstance(current, str) or current not in raw):
        problems.append(f"'current' names {current!r}, which is not a look")
    cycle = _cycle(doc.get("cycle", {}), raw, problems)
    triggers = _triggers(doc.get("triggers", {}), raw, problems)
    if problems:
        raise LookError(problems)
    return LookBook(looks, current, cycle, doc.get("notes"), triggers)


def pattern_problems(book: LookBook, declared: Callable[[str], type | None]) -> list[str]:
    """What stops each look from recalling as saved: a pattern that nothing
    offers or that does not load, params it does not declare or accept, a
    pattern a program cannot run, and, once its patterns resolve, a route
    that reaches no knob it can move or a front knob that is not there
    (pewpew.compose.modulation.route_problems), each named by its path.

    `declared(pattern)` returns the class a pattern name runs, or None for a
    name nothing offers. Never raises.
    """
    return [
        f"look {name!r}: {problem}" for name, look in book.looks.items() for problem in _look_problems(look, declared)
    ]


def _look_problems(look: Look, declared: Callable[[str], type | None]) -> list[str]:
    found = [problem for layer in look.layers
             for problem in check(layer.program, where=layer_address(layer.id), resolve=declared)]
    if found or not (look.routes or look.front):
        return found
    return route_problems(look.routes, look.front, look_controls(look, declared))


def _cycle(raw: Any, looks: Mapping[str, Any], problems: list[str]) -> CycleConfig:
    if not isinstance(raw, dict):
        problems.append(f"'cycle' is an object with {', '.join(repr(key) for key in sorted(_CYCLE_KEYS))}")
        return CycleConfig()
    before = len(problems)
    for key in sorted(set(raw) - _CYCLE_KEYS):
        problems.append(f"cycle: unknown key {key!r}; expected {', '.join(sorted(_CYCLE_KEYS))}")
    base = CycleConfig()
    idle = raw.get("idle", base.idle)
    if idle is not None and not (is_number(idle) and idle > 0):
        problems.append(f"cycle: 'idle' is a number of seconds above 0, or null for off; got {idle!r}")
    each = raw.get("each", base.each)
    dwell = each if isinstance(each, list) and len(each) == 2 else [each, each]
    if not (all(is_number(x) and x > 0 for x in dwell) and dwell[0] <= dwell[1]):
        problems.append(f"cycle: 'each' is a number of seconds above 0, or a range [min, max] of them; got {each!r}")
    rounds = raw.get("rounds", base.rounds)
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        problems.append(f"cycle: 'rounds' is a whole number, 0 for forever; got {rounds!r}")
    end = raw.get("end", base.end)
    if end is not None and (not isinstance(end, str) or end not in looks):
        problems.append(f"cycle: 'end' names {end!r}, which is not a look")
    counts = {key: raw.get(key, getattr(base, key)) for key in ("seed", "window", "fresh")}
    for key, count in counts.items():
        if not is_seed(count):  # a whole number of at least 0
            problems.append(f"cycle: {key!r} is a whole number of at least 0, got {count!r}")
    weights = raw.get("weights", {})
    if not isinstance(weights, dict):
        problems.append(f"cycle: 'weights' is an object of look name: weight, got {weights!r}")
        weights = {}
    for name, weight in weights.items():
        if name not in looks:
            problems.append(f"cycle: 'weights' names {name!r}, which is not a look")
        elif not (is_number(weight) and weight > 0):
            problems.append(f"cycle: the weight of {name!r} is a number above 0, got {weight!r}")
    if len(problems) > before:
        return base
    return CycleConfig(
        None if idle is None else float(idle), float(each) if is_number(each) else (float(each[0]), float(each[1])),
        int(rounds), end, weights={name: float(weight) for name, weight in weights.items()}, **counts,
    )


def _triggers(raw: Any, looks: Mapping[str, Any], problems: list[str]) -> dict[str, Trigger]:
    if not isinstance(raw, dict):
        problems.append("'triggers' is an object of name: trigger")
        return {}
    if len(raw) > MAX_TRIGGERS:
        problems.append(f"{len(raw)} triggers; at most {MAX_TRIGGERS}")
    out: dict[str, Trigger] = {}
    for name, item in raw.items():
        if (reason := check_name(name, "trigger")) is not None:
            problems.append(reason)
            continue
        where = f"trigger {name!r}"
        if not isinstance(item, dict):
            problems.append(f"{where} is an object with 'look', 'hold' and 'priority'")
            continue
        before = len(problems)
        for key in sorted(set(item) - _TRIGGER_KEYS):
            problems.append(f"{where}: unknown key {key!r}; expected {', '.join(sorted(_TRIGGER_KEYS))}")
        base = Trigger()
        look = item.get("look")
        if look is not None and (not isinstance(look, str) or look not in looks):
            problems.append(f"{where}: 'look' names {look!r}, which is not a look")
        hold = item.get("hold", base.hold)
        if not (is_number(hold) and 0.0 < hold <= MAX_HOLD):
            problems.append(f"{where}: 'hold' is a number of seconds above 0, at most {MAX_HOLD:g}; got {hold!r}")
        priority = item.get("priority", base.priority)
        if priority not in PRIORITIES:
            problems.append(f"{where}: 'priority' is one of {', '.join(PRIORITIES)}; got {priority!r}")
        gaps = {}
        for key in ("debounce", "cooldown"):
            gaps[key] = item.get(key, getattr(base, key))
            if not (is_number(gaps[key]) and 0.0 <= gaps[key] <= MAX_GAP):
                problems.append(f"{where}: {key!r} is a number of seconds from 0 to {MAX_GAP:g}; got {gaps[key]!r}")
        if len(problems) == before:
            out[name] = Trigger(look, float(hold), priority, float(gaps["debounce"]), float(gaps["cooldown"]))
    return out


def load_looks(path: Path, **kw: Any) -> LookBook:
    """Read and validate a looks file. Raises OSError as the filesystem
    does, LookError for the content."""
    return parse_looks(Path(path).read_bytes(), **kw)
