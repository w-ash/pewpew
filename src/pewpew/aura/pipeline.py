"""The aura pipeline: the parts that run a look, built in dependency order.

`build_aura_pipeline` builds what `python -m pewpew run` and each studio
session run (ADR-025):

    calls, features -> layer stack -> crossfader -> deck -> master ->
    variety -> looks (with a looks file) -> triggers -> aura control

and `AuraPipeline.loop` puts it under a `PacedLoop`: the triggers, then
the looks, before each frame renders; the blink, the master, then the
caller's stages (a power limit) after it. What a run adds around it (DDP,
a room map, the health monitor, the watchdog, the sinks) stays with the
caller, which passes the blink, the boards and the health snapshot that
the control offers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import numpy as np

from pewpew.aura.book import LookBook
from pewpew.aura.control import AuraControl, Boards
from pewpew.aura.deck import Deck
from pewpew.aura.looks import Looks
from pewpew.aura.master import Master
from pewpew.aura.triggers import Triggers
from pewpew.aura.variety import Variety
from pewpew.compose import Compositor, Look, Resolved
from pewpew.crossfade import Crossfader
from pewpew.features import EventFeatures, FakeFeatures
from pewpew.load import Catalog, LoadedPattern
from pewpew.mapping import Grouping
from pewpew.pace import Calls, PacedLoop, PaceStats, Stage
from pewpew.reload import Watch
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
        looks = [self.looks.before_frame] if self.looks is not None else []
        blink = [self.blink.apply] if self.blink is not None else []
        return PacedLoop(
            self.fader, fps=fps, calls=self.calls, stats=stats, before=[*before, self.triggers.before_frame, *looks],
            after=[*blink, self.master.apply, *after], on_frame=on_frame,
        )


def build_aura_pipeline(
    look: Look,
    layers: Sequence[tuple[Resolved, LoadedPattern]],
    mapping: np.ndarray,
    *,
    catalog: Catalog,
    seed: int = 0,
    features: EventFeatures | None = None,
    grouping: Grouping | None = None,
    units: str | None = None,
    bypass: bool = False,
    now: Callable[[], float] | None = None,
    watch: Watch | None = None,
    master_cap: float = 1.0,
    looks_path: Path | None = None,
    book: LookBook | None = None,
    trigger_log: TextIO | None = None,
    trigger_log_max: int | None = None,
    blink: Blink | None = None,
    boards: Boards | None = None,
    health: Callable[[], dict] | None = None,
    accept_looks: bool = False,
) -> AuraPipeline:
    """Build the aura that starts in `look` on `mapping`.

    `layers` are `look`'s layers ready to build, each with the pattern its
    reloader follows (`pewpew.aura.deck.ready_layer`). `seed` seeds the
    made looks, and the default features (the seeded fake). `grouping`,
    `units`, `bypass` and `now` are as for `Compositor`. `book`, with its
    file at `looks_path`, gives the saved looks and the triggers; without
    it there are no looks and no triggers. `blink`, `boards`, `health` and
    `accept_looks` are as for `AuraControl`. Raises as `Compositor` does."""
    calls = Calls()
    features = features if features is not None else EventFeatures(FakeFeatures(seed))
    stack = Compositor(
        [resolved for resolved, _ in layers], mapping, seed=look.seed, signals=look.signals, routes=look.routes,
        front=look.front, features=features, grouping=grouping, units=units, bypass=bypass, now=now,
    )
    # The loop drives the crossfader, and everything that would reach the
    # stack reaches it, so a look recall can put a new stack in place.
    fader = Crossfader(stack)
    loaded: Mapping[str, LoadedPattern] = {resolved.layer.id: found for resolved, found in layers}
    deck = Deck(fader, catalog, calls.call_soon, loaded, watch=watch)
    master = Master(master_cap)
    variety = Variety(deck, seed=seed)
    looks = None
    if book is not None:
        assert looks_path is not None, "a looks book needs the path of its file"
        looks = Looks(looks_path, book, deck, master, variety=variety)
    triggers = Triggers(
        book.triggers if book is not None else {}, looks=looks, features=features, log=trigger_log,
        log_max=trigger_log_max,
    )
    control = AuraControl(
        calls, deck, master, triggers, looks=looks, blink=blink, boards=boards, health=health,
        accept_looks=accept_looks, variety=variety,
    )
    return AuraPipeline(calls, features, fader, deck, master, variety, looks, triggers, blink, control)
