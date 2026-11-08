"""The aura pipeline: the parts that run a look, built in dependency order.

`build_aura_pipeline` builds what `python -m pewpew run` and each Gallery
session run (ADR-025):

    calls, features -> layer stack -> crossfader -> deck -> master ->
    variety -> looks (with a looks book) -> triggers -> aura control

and `AuraPipeline.loop` puts it under a `PacedLoop`: the triggers, then
the looks, before each frame renders; the blink, the master, then the
caller's stages (a power limit) after it. What a run adds around it (DDP,
a rig and its reload, the health monitor, the watchdog, the sinks) stays with the
caller, which passes the blink, the boards, the health snapshot and the
rig file's layout that the control offers.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import numpy as np

from pewpew.aura.book import LookBook
from pewpew.aura.control import AuraControl, Boards, Layout
from pewpew.aura.deck import Deck
from pewpew.aura.looks import Looks
from pewpew.aura.master import Master
from pewpew.aura.triggers import Triggers
from pewpew.aura.variety import Submit, Variety, in_background
from pewpew.compose import Compositor, Look
from pewpew.crossfade import Crossfader
from pewpew.features import EventFeatures, FakeFeatures
from pewpew.pace import ASK_TIMEOUT_S, Calls, PacedLoop, PaceStats, Stage
from pewpew.room.blink import Blink


@dataclass(frozen=True, eq=False)
class AuraPipeline:
    """The parts of one aura, each built from the ones before it. The loop
    drives `fader`; every request reaches the parts through `control`."""

    calls: Calls
    features: EventFeatures
    fader: Crossfader[Compositor]
    deck: Deck
    master: Master
    variety: Variety
    looks: Looks | None
    triggers: Triggers
    blink: Blink | None
    control: AuraControl

    def before_frame(self, t: float) -> None:
        """What runs before each frame renders: the triggers, then the looks."""
        self.triggers.before_frame(t)
        if self.looks is not None:
            self.looks.before_frame(t)

    def loop(
        self,
        fps: float,
        *,
        stats: PaceStats | None = None,
        before: Sequence[Callable[[float], None]] = (),
        after: Sequence[Stage] = (),
        on_frame: Sequence[Callable[[float, np.ndarray], None]] = (),
    ) -> PacedLoop:
        """A `PacedLoop` over the pipeline at `fps`. Each frame: `before`
        (an audio analysis), the triggers, then the looks, before it
        renders; the blink, the master, then `after` (a power limit), after
        it, so `after` gets the frame at the master's level."""
        blink = [self.blink.apply] if self.blink is not None else []
        return PacedLoop(
            self.fader, fps=fps, calls=self.calls, stats=stats, before=[*before, self.before_frame],
            after=[*blink, self.master.apply, *after], on_frame=on_frame,
        )


def build_aura_pipeline(
    look: Look,
    mapping: np.ndarray,
    *,
    seed: int = 0,
    features: EventFeatures | None = None,
    bypass: bool = False,
    now: Callable[[], float] | None = None,
    master_cap: float = 1.0,
    looks_path: Path | None = None,
    book: LookBook | None = None,
    gallery: str | None = None,
    trigger_log: TextIO | None = None,
    trigger_log_max: int | None = None,
    blink: Blink | None = None,
    boards: Boards | None = None,
    health: Callable[[], dict] | None = None,
    layout: Layout | None = None,
    accept_looks: bool = False,
    max_making: int | None = None,
    max_book_bytes: int | None = None,
    idle_off: bool = False,
    timeout: float = ASK_TIMEOUT_S,
    make_variety: Callable[[Deck], Variety] | None = None,
    submit: Submit = in_background,
) -> AuraPipeline:
    """Build the aura that starts in `look` on `mapping`, at the look's
    master when it has one.

    `seed` seeds the made looks, and the default features (the seeded
    fake). `bypass` and `now` are as for `Compositor`. `book`, with
    its file at `looks_path`, gives the saved looks and the triggers;
    without it there are no looks and no triggers. A book with no
    `looks_path` keeps its changes in memory (`Looks`). `gallery`, `blink`,
    `boards`, `health`, `layout`, `accept_looks`, `max_making` and
    `timeout` are as for `AuraControl`, and `max_book_bytes` as `max_bytes`
    for `Looks`, as does `idle_off`.
    `make_variety(deck)` makes the made looks' `Variety` (default: one
    seeded from `seed`), and `submit` is how the looks make a fresh slot's
    look (`Looks`). Raises as `Compositor` does."""
    calls = Calls()
    features = features if features is not None else EventFeatures(FakeFeatures(seed))
    stack = Compositor(
        look.layers, mapping, seed=look.seed, signals=look.signals, routes=look.routes, front=look.front,
        features=features, bypass=bypass, now=now,
    )
    # The loop drives the crossfader, and everything that would reach the
    # stack reaches it, so a look recall can put a new stack in place.
    fader = Crossfader(stack)
    deck = Deck(fader)
    master = Master(master_cap)
    if look.master is not None:
        master.set(look.master)
    variety = make_variety(deck) if make_variety is not None else Variety(deck, seed=seed)
    looks = None
    if book is not None:
        looks = Looks(looks_path, book, deck, master, variety=variety, submit=submit, max_bytes=max_book_bytes,
                      idle_off=idle_off)
    triggers = Triggers(
        book.triggers if book is not None else {}, looks=looks, features=features, log=trigger_log,
        log_max=trigger_log_max,
    )
    control = AuraControl(
        calls, deck, master, triggers, looks=looks, blink=blink, boards=boards, health=health,
        layout=layout, accept_looks=accept_looks, variety=variety, timeout=timeout, max_making=max_making,
        gallery=gallery,
    )
    return AuraPipeline(calls, features, fader, deck, master, variety, looks, triggers, blink, control)
