"""The director: what the idle cycle plays next, and for how long.

After `idle` seconds of engine time with no operator input, the director
plays the looks whose `cycle` flag is on (pewpew.aura.book `CycleConfig`):

- each slot picks one of them at random, as likely as its weight
  (`weights`, 1 by default), but none of the last `window` it played;
- each slot lasts a dwell drawn from `each`, a number of seconds or a
  range `[min, max]`; a look fades in over its own fade;
- every `fresh`th slot of a run (0: never) is a look made fresh from a
  seed of its own instead (pewpew.aura.variety), which plays unsaved;
  `coming` names it a slot ahead, so its look can be made before it. A
  fresh slot whose look is not made by its start plays the look drawn
  for it instead (`instead`), and the next fresh slot plays the fresh look;
- after `rounds` rounds of as many slots as there are looks (0: forever),
  it plays `end` (null: stays on the last) and stops.

Any operator input stops it and restarts the idle wait (`touch`). Each
slot draws from a counter-based stream keyed by the cycle's `seed` and
the slot's number in the run, so a run with the same inputs at the same
engine times plays the same looks for the same dwells, each slot from
the frame at its engine time; no wall clock. The slot count, the looks
last played and a fresh look still owed carry on across a touch, so the
next run of the cycle goes on with the sequence rather than repeat it.

Pure: `tick` says what to play, and the caller plays it.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import islice

from pewpew.aura.book import MAX_LOOKS, CycleConfig
from pewpew.fx.surprise import Draw


@dataclass(frozen=True, slots=True)
class Slot:
    """What the director plays next: the saved look `name`, or a look made
    fresh from `seed` when `name` is None."""

    name: str | None
    seed: int = 0


class Director:
    """The idle cycle's state, stepped by engine time (module docstring).
    Idle time counts from the last `touch` or from `start`."""

    def __init__(self, start: float = 0.0) -> None:
        self._last_input = float(start)
        self._running = False
        self._done = False
        self._since = 0.0  # engine time the slot playing began
        self._dwell = 0.0  # how long it plays
        self._slot = 0  # slots played this run: the stream's counter
        self._count = 0  # slots played since the cycle last began
        self._recent: deque[str] = deque(maxlen=MAX_LOOKS)  # the window never spans more
        # The fresh slot playing: its seed and the look drawn to play instead.
        self._fresh: tuple[int, str] | None = None
        # The seed of a fresh look a slot played `instead`, which the next fresh slot plays.
        self._owed: int | None = None

    @property
    def running(self) -> bool:
        return self._running

    def touch(self, t: float) -> None:
        """Operator input at engine time `t`: stop, and restart the idle wait."""
        self._last_input = float(t)
        self._running = False
        self._done = False

    def due(self, t: float, config: CycleConfig) -> bool:
        """Whether the idle wait is over at engine time `t`: a `tick` then
        begins the cycle, given looks to play."""
        return config.idle is not None and not self._running and not self._done and t - self._last_input >= config.idle

    def coming(self, names: Sequence[str], config: CycleConfig) -> int | None:
        """The seed of the next slot when it is a fresh look, else None: the
        slot a `tick` with these `names` and `config` begins next, while
        the cycle runs or waits to begin."""
        if config.idle is None or not names or self._done:
            return None
        if self._running and self._rounds_done(names, config):
            return None  # the end look comes next
        count = self._count + 1 if self._running else 1
        return self._seed(config, self._slot) if _is_fresh(count, config) else None

    def tick(self, t: float, names: Sequence[str], config: CycleConfig) -> Slot | None:
        """What to play at engine time `t`, or None: a slot of one of
        `names`, the looks the cycle plays, a fresh look, or the config's
        `end` once its rounds are done."""
        if config.idle is None or not names:
            self._running = False
            return None
        if not self._running:
            if self._done or t - self._last_input < config.idle:
                return None
            self._running, self._count = True, 0
            return self._next(t, names, config)
        if t - self._since < self._dwell:
            return None
        if self._rounds_done(names, config):
            self._running, self._done = False, True
            return None if config.end is None else Slot(config.end)
        return self._next(t, names, config)

    def instead(self, *, owe: bool = True) -> Slot:
        """The look the fresh slot begun at the last `tick` plays when its
        fresh look is not made by its start: one of the cycle, drawn for
        that slot. With `owe`, the next fresh slot plays the fresh look;
        without (its making failed), it plays one of its own."""
        assert self._fresh is not None, "instead follows a tick that began a fresh slot"
        seed, name = self._fresh
        self._fresh = None
        self._owed = seed if owe else None
        self._recent.append(name)
        return Slot(name)

    def _rounds_done(self, names: Sequence[str], config: CycleConfig) -> bool:
        return bool(config.rounds) and self._count >= config.rounds * len(names)

    def _next(self, t: float, names: Sequence[str], config: CycleConfig) -> Slot:
        """Begin the next slot at `t`: draw its dwell and one of `names`,
        then play a fresh look or that one (module docstring)."""
        slot, draw = self._slot, Draw("director", config.seed, self._slot)
        self._slot += 1
        self._count += 1
        self._since = t
        self._dwell = draw.uniform(*config.dwell)
        recent = set(islice(reversed(self._recent), min(config.window, len(names) - 1)))
        name = draw.pick({name: config.weights.get(name, 1.0) for name in names if name not in recent})
        if _is_fresh(self._count, config):
            seed = self._seed(config, slot)
            self._fresh, self._owed = (seed, name), None
            return Slot(None, seed)
        self._fresh = None
        self._recent.append(name)
        return Slot(name)

    def _seed(self, config: CycleConfig, slot: int) -> int:
        """The seed of the look made fresh for slot `slot` of the run: the
        one owed, else one of its own."""
        return self._owed if self._owed is not None else Draw("fresh", config.seed, slot).seed()


def _is_fresh(count: int, config: CycleConfig) -> bool:
    """Whether slot `count` of a run (from 1) is a fresh look."""
    return bool(config.fresh) and count % config.fresh == 0
