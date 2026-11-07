"""Looks made for the running aura: a surprise from a seed, or a variation
of the look that runs, each made for the stack's own mapping
(pewpew.fx.surprise, which judges each before it gives it).

`Variety` makes them; the aura control's `surprise` and `vary` requests
and the director's fresh slots play them unsaved (`Looks.play`, or
`fade_to` without a looks file), and a `keep` saves the running look
under the name the made look offers: `surprise <n>`, or `<look> variation
<n>` after the look it varies, counted in the run from 1, so a name says
which of the run's made looks it is and where it came from; the look holds
its seed. A request without a seed takes
the run's next one,
counted from the run's seed (`surprise.sub_seed`), so a run makes the
same looks in the same order every time.

Making a look renders it a few times over, so it takes a second or
more: a request makes it on a thread of its own (`in_background`;
pewpew.aura.control), and the director's fresh slot a slot ahead
(pewpew.aura.looks) through a `Submit`. A run, which is always live,
makes it with `in_background`, so its loop thread never waits for one;
`at_once` makes it on the thread that steps the frames, for a caller
that steps them on engine time alone, as the tests' aura rig does.
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from typing import TypeVar

from pewpew.aura.book import MAX_NAME
from pewpew.aura.deck import Deck
from pewpew.compose import Look
from pewpew.errors import scrub
from pewpew.fx import surprise
from pewpew.problems import Refused

T = TypeVar("T")

# Runs a job off the loop thread; its future holds the job's result or error.
Submit = Callable[[Callable[[], T]], "Future[T]"]


@dataclass(frozen=True, slots=True)
class Made:
    """A look made for the aura, and the name a keep saves it under first."""

    look: Look
    label: str


class Variety:
    """Makes looks for the aura that `deck` runs (module docstring). Any
    thread: it reads the stack's mapping and look, never writes them."""

    def __init__(self, deck: Deck, *, seed: int = 0) -> None:
        self._deck = deck
        self._seed = seed
        self._count = itertools.count()
        self._surprises = itertools.count(1)
        self._variations = itertools.count(1)

    def next_seed(self) -> int:
        """The run's next seed for a look made without one."""
        return surprise.sub_seed(self._seed, next(self._count))

    def surprise(self, seed: int | None = None) -> Made:
        """A look made from `seed` (None: the run's next) for the running
        stack's mapping. Raises ValueError (pewpew.fx.surprise.NoLook)
        when nothing made passes the content gate."""
        seed = self.next_seed() if seed is None else seed
        stack = self._deck.fader.current
        look = surprise.generate(seed, stack.mapping, grouping=stack.grouping)
        return Made(look, f"surprise {next(self._surprises)}")

    def vary(self, strength: float | None = None, seed: int | None = None, of: str | None = None) -> Made:
        """A look like the running one, moved by `strength` (None: mutate's
        default) from `seed` (None: the run's next), named after `of`, the
        look that runs (`tide variation 2`), when it has a name. Its patterns resolve
        as the run resolves them (pewpew.load.resolve): a pattern the run
        was launched with may be a file. Raises ValueError when the running
        look does not check (a pattern file broken since it started), or
        no change of it passes the content gate."""
        seed = self.next_seed() if seed is None else seed
        stack = self._deck.fader.current
        running = self._deck.snapshot()
        try:
            look = surprise.mutate(
                running, seed, stack.mapping, strength=surprise.STRENGTH if strength is None else strength,
                grouping=stack.grouping, pattern_dir=self._deck.catalog.search_dir,
            )
        except Refused as exc:
            raise ValueError(f"the running look cannot vary: {scrub(str(exc))}") from exc
        label = f"variation {next(self._variations)}"
        return Made(look, f"{of[: MAX_NAME - 5 - len(label)]} {label}" if of else label)  # `keep` keeps 4 for " <k>"


def fade_to(deck: Deck, made: Made) -> str | None:
    """Fade `deck` to `made` over the made look's own fade. Returns why
    not, or None."""
    if (reason := deck.recall(made.look, made.look.fade)) is not None:
        return f"cannot start {made.label!r}: {reason}"
    return None


def at_once(job: Callable[[], T]) -> Future[T]:
    """Run `job` now, on the caller's thread; its future, done, holds its
    result or its error. For a caller that steps frames on engine time
    alone: each fresh slot's look is then made by its start."""
    future: Future[T] = Future()
    try:
        future.set_result(job())
    except Exception as exc:  # noqa: BLE001  handed to whoever reads the future
        future.set_exception(exc)
    return future


def in_background(job: Callable[[], T]) -> Future[T]:
    """Run `job` on a daemon thread of its own; its future holds its result
    or its error."""
    future: Future[T] = Future()

    def run() -> None:
        try:
            future.set_result(job())
        except BaseException as exc:  # noqa: BLE001  handed to whoever reads the future
            future.set_exception(exc)

    threading.Thread(target=run, name="pewpew-made-look", daemon=True).start()
    return future
