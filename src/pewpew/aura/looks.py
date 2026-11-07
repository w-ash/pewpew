"""Saved looks over the running aura: save, recall with a crossfade,
delete, the cycle flag, the idle cycle (pewpew.aura.director), the trigger
holds, and looks made for the aura (pewpew.aura.variety): played unsaved,
kept under a name they offer. The file format is `pewpew.aura.book`.

A recall starts its layers through the deck (pewpew.aura.deck), at the
look's values.

An override is journalled, not saved: it never changes `current` or the
file, so a restart during one comes back in the operator's look. The
journal is the live stack when the first hold began (LedFx's silence scene
[S1266]); later holds replace the look and the deadline but
keep the journal, and a hold of the look already held only moves the
deadline, so the look does not restart. An override never moves the
master: the master stays the operator's. An operator recall, save, sent
look or layer edit during a hold ends it, and the aura does not return: the
operator wins.

After a look a client sent no look is current: the room runs what the
client sent, not a saved look, so the page marks no look. The file still names the look last
recalled or saved, so a restart comes back in it. A made look plays the same way, unsaved (`play`),
until a save with no name saves it, under the name it offers (`surprise
7`), or that name with a number past the first one taken; a save under
another name and a delete rename it.

Every write replaces the whole file atomically (`write_atomic`), so a
crash at any point leaves either the old file or the new one, never half
of either.
"""

from __future__ import annotations

import itertools
import logging
import math
import re
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, NamedTuple

from pewpew.aura.book import MAX_LOOKS, MAX_NAME, LookBook, check_name
from pewpew.aura.deck import Deck
from pewpew.aura.director import Director, Slot
from pewpew.aura.master import Master
from pewpew.aura.variety import Made, Submit, Variety, fade_to, in_background
from pewpew.compose import DEFAULT_FADE, Layer, Look
from pewpew.compose.stack import parse_fade
from pewpew.errors import describe_exception, unknown
from pewpew.fx.graph import Graph
from pewpew.jsonfile import write_atomic

logger = logging.getLogger(__name__)

# What an operator's edit changes in a running look: its layers (each
# knob, node and mix), its signals' knobs and its front.
Edited = tuple[tuple[Layer, ...], Graph | None, tuple[str, ...]]

KEPT = "kept"  # what a save with no name names a look that was not made for the aura


def _edited(look: Look) -> Edited:
    return look.layers, look.signals, look.front


class _Saved(NamedTuple):
    """What the last recall or save set: the layers and signals at their
    live values (`_edited`), the master or None, and each knob's value
    then, by address, as JSON: what a page reverts a knob to."""

    edited: Edited
    master: float | None
    values: Mapping[str, Any]


# ---- the controller -------------------------------------------------------


class _Recall(NamedTuple):
    """A recall that starts later: the look's name (None for the
    journalled live state), the call that starts it at a frame's engine
    time, whether a trigger hold queued it (a hold's own look, or its
    return) rather than the operator, whether it is a hold's return, and
    whether it is still the live state (no held look has started since)."""

    name: str | None
    start: Callable[[float], str | None]
    by_hold: bool = False
    returning: bool = False
    live: bool = False


@dataclass(frozen=True)
class Hold:
    """A trigger's look held as a temporary override.

    `journal` is the recall that returns the aura at `until` (engine
    time). `until` is infinite while the look waits for a running fade:
    the hold counts from the frame its look starts. A look that then fails
    to start ends the hold; the aura returns, unless the journal is still
    the live state, which runs on.
    """

    trigger: str
    look: str
    rank: int
    until: float
    journal: _Recall


class Looks:
    """Saved looks over the running aura: save, recall with a crossfade,
    delete, the cycle flag, the idle cycle, and the file.

    Thread discipline: `state` runs on any thread. Everything else belongs
    to the loop thread (pewpew.aura.control queues it), and `before_frame`
    is a `before` hook of the paced loop, called before every frame renders.

    A recall during a fade waits for that fade to finish, then starts
    (Chromatik snapshots [S1265]). One recall waits at a time: a newer one
    replaces it, so an operator tapping through looks waits at most for the
    fade already running.

    `hold` is the trigger override (pewpew.aura.triggers): a look held
    until an engine-time deadline, then a return to the journalled state.
    `recall` and `save` end a hold without returning (`release`); a layer
    edit also drops a recall that waits (`edit`); a sent look leaves every
    look (`leave`).

    The idle cycle's fresh slots are made by `variety` (by default one of
    its own over `deck`), through `submit`, from the frame the director
    names one as its next slot (`Director.coming`): a slot, or the idle
    wait, ahead. Each slot starts at its own engine time, and the loop
    thread never waits for a make. A fresh slot whose look is made by then
    plays it; else it plays the look the director drew for it instead
    (`Director.instead`), says so in the log, and the next fresh slot plays
    the fresh look once it is made. A make that failed is dropped.

    So the cycle is the same on every run of the same inputs when each
    make is done by its slot's start: always with `variety.at_once`,
    which makes a look on the thread that steps the frames, for a caller
    that steps them on engine time alone (the tests' aura rig). A run is
    always live and makes with `in_background`, the default: a look in
    the slot before its own, a second or so against a dwell of tens of
    seconds. Up to the wall clock are only whether it is done by then, and
    the frames a loop that falls behind skips (pewpew.pace): a slot then
    begins on the first frame rendered after its time.
    """

    def __init__(
        self, path: Path, book: LookBook, deck: Deck, master: Master, *, variety: Variety | None = None,
        submit: Submit = in_background,
    ) -> None:
        self._path = Path(path)
        self._book = book
        # The look the file names, which a restart comes back in: the
        # current look, or while none is, the last one.
        self._restart = book.current
        self._deck = deck
        self._fader = deck.fader
        self._master = master
        self._pending: _Recall | None = None
        self._hold: Hold | None = None
        self._fading: str | None = None
        self._director = Director(deck.fader.t)
        self._variety = variety if variety is not None else Variety(deck)
        self._submit = submit
        # The look of the director's next fresh slot, by its seed, being
        # made off the loop thread.
        self._making: tuple[int, Future[Made]] | None = None
        # The made look that runs unsaved, which a save with no name keeps.
        self._made: Made | None = None
        # What the last recall or save set (`_Saved`). The page's "changed
        # since saved" marker compares live state with this. Replaced whole,
        # read by sink workers.
        self._recalled: _Saved | None = None
        # The last failed recall that nobody was waiting on (a queued one,
        # the idle cycle); the runner shows it on the status line.
        self.error: str | None = None

    @property
    def book(self) -> LookBook:
        return self._book

    @property
    def source(self) -> str | None:
        """The name of the look that plays, saved or made, or None: what a
        variation of it is named after. Any thread."""
        made = self._made
        return made.label if made is not None else self._book.current

    @property
    def held(self) -> Hold | None:
        """The trigger override holding, or None. Replaced whole; any thread."""
        return self._hold

    # ---- any thread ------------------------------------------------------

    def state(self) -> dict:
        """The page's view of the looks; JSON-ready, names only."""
        book = self._book
        fading = self._fading if self._fader.fading else None
        progress = self._fader.progress
        pending = self._pending
        recalled = self._recalled
        return {
            "items": [{"name": name, "cycle": look.cycle, "fade": look.fade} for name, look in book.looks.items()],
            "current": book.current,
            "changed": self.changed(),
            "fading": fading,
            # Coarse, so the state message changes a few times per fade
            # rather than on every frame.
            "progress": None if fading is None or progress is None else round(progress * 20) / 20,
            "pending": None if pending is None else pending[0],
            "cycling": self._director.running,
            # When the idle cycle starts (seconds without input; None: never)
            # and how long each look plays, shortest and longest.
            "idle": book.cycle.idle,
            "dwell": list(book.cycle.dwell),
            # The made look that plays unsaved, by the name it offers.
            "made": None if self._made is None else self._made.label,
            # The name a save with none gives the live state now (`offered`),
            # or None while a trigger holds a look, when it refuses.
            "offered": None if self._hold is not None else self.offered(),
            # Each knob's value as the current look was recalled or saved, or
            # the made look started, for as long as `changed` compares with it.
            "saved": recalled.values if recalled is not None and self._compared() else None,
        }

    def changed(self) -> bool:
        """Whether the live state has moved off the look last recalled or
        saved, or the made look that plays as it started: another node,
        param value or mix on a layer, or another master level when the
        look stores one. False while a trigger holds a look: the hold is
        not an edit, and the aura returns from it."""
        recalled = self._recalled
        if recalled is None or not self._compared():
            return False
        if _edited(self._deck.snapshot()) != recalled.edited:
            return True
        return recalled.master is not None and self._master.level != recalled.master

    def _compared(self) -> bool:
        """Whether `changed` compares the live state with `_recalled`: a
        look is current or a made one plays, and no trigger holds one."""
        return (self._book.current is not None or self._made is not None) and self._hold is None

    # ---- loop thread -------------------------------------------------------

    def begin(self) -> None:
        """The deck runs the current look as saved, as the run started it:
        compare the live state with it from now on."""
        current = self._book.current
        assert current is not None, "a run starts in the current look"
        self._recalled = self._saved(self._book.looks[current].master)

    def recall(self, name: str, fade: float | None = None) -> str | None:
        """Recall look `name` over `fade` seconds (None: its own fade).
        Returns why not, or None once it runs or waits for the running fade."""
        if name not in self._book.looks:
            return self._unknown(name)
        if fade is not None:
            fade, reason = parse_fade(fade)
            if reason is not None:
                return reason
        self.release()
        if self._fader.fading:
            self._pending = _Recall(name, lambda now: self._start(name, fade))
            return None
        return self._start(name, fade)

    def save(self, name: str | None = None, fade: float | None = None, master: bool | None = True) -> str | None:
        """Save the live state as look `name`, replacing one of that name;
        None saves it under the name it offers (`offered`), with the made
        look's fade, and not while a trigger holds a look: the live state is
        then the held look, not the operator's. `fade` is stored when given;
        otherwise the replaced look's fade, or the default. `master` False
        leaves the master out of the look, and None keeps the replaced
        look's choice (a new look holds it). A replaced look keeps its place
        in the idle cycle; a new one joins it when every other look is in
        it. Returns why not, or None."""
        if name is None:
            if (held := self._hold) is not None:
                return f"{held.trigger} is playing {held.look}: save when it ends"
            name = self.offered()
            made = self._made
            if fade is None and made is not None:
                fade = made.look.fade
        if (reason := check_name(name)) is not None:
            return reason
        if fade is not None:
            fade, reason = parse_fade(fade)
            if reason is not None:
                return reason
        old = self._book.looks.get(name)
        if master is None:
            master = old is None or old.master is not None
        if old is None and len(self._book.looks) >= MAX_LOOKS:
            return f"there are already {MAX_LOOKS} looks; delete one first"
        others = self._book.looks.values()
        look = replace(
            self._deck.snapshot(),
            master=self._master.level if master else None,
            fade=fade if fade is not None else (old.fade if old else DEFAULT_FADE),
            cycle=old.cycle if old else bool(others) and all(other.cycle for other in others),
        )
        reason = self._commit(self._book.with_look(name, look).with_current(name))
        if reason is None:
            self._recalled = self._saved(look.master)
            self._made = None
            self.error = None
            self.release()
        return reason

    def offered(self) -> str:
        """The name a save with none gives the live state: the one the made
        look that runs offers, else the current look's (a copy of it), else
        KEPT. A name that is taken counts on past it: a name that ends in a
        number by that number (`surprise 3` taken: `surprise 4`), another by
        one put after it (`tide 2`). Any thread."""
        made = self._made
        stem = (made.label if made is not None else self._book.current or KEPT)[: MAX_NAME - 4]  # room for " <k>"
        taken = self._book.looks
        counted = re.fullmatch(r"(.*\D) (\d{1,3})", stem)
        names = ((f"{counted[1]} {k}" for k in itertools.count(int(counted[2]))) if counted
                 else (stem if k == 1 else f"{stem} {k}" for k in itertools.count(1)))
        return next(n for n in names if n not in taken)

    def play(self, made: Made) -> str | None:
        """Fade to a look made for the aura over its own fade, unsaved: as a
        sent look, no look is current, a waiting recall and a hold end, and a
        save with no name saves it under its label. An edit to it is `changed`, as an
        edit to a recalled look is. Returns why not, or None."""
        if (reason := fade_to(self._deck, made)) is not None:
            return reason
        self.leave()
        self._made = made
        self._recalled = self._saved(None)
        logger.info("started a made look, %s", made.label)
        return None

    def delete(self, name: str) -> str | None:
        if name not in self._book.looks:
            return self._unknown(name)
        users = [t for t, trig in self._book.triggers.items() if trig.look == name]
        if users:
            return f"look {name!r} is held by trigger {', '.join(users)}; change the looks file to delete it"
        reason = self._commit(self._book.without(name))
        if reason is None:
            pending = self._pending
            if pending is not None and pending.name == name and not pending.by_hold:
                self._pending = None
            if self._book.current is None:
                self._recalled = None
        return reason

    def set_cycle(self, name: str, on: bool) -> str | None:
        look = self._book.looks.get(name)
        if look is None:
            return self._unknown(name)
        return self._commit(self._book.with_look(name, replace(look, cycle=bool(on))))

    def set_fade(self, name: str, fade: float) -> str | None:
        """Store `fade` as look `name`'s own fade, and nothing else: unsaved
        edits stay unsaved."""
        look = self._book.looks.get(name)
        if look is None:
            return self._unknown(name)
        seconds, reason = parse_fade(fade)
        if seconds is None:
            return reason
        return self._commit(self._book.with_look(name, replace(look, fade=seconds)))

    def touch(self) -> None:
        """Operator input arrived: stop the idle cycle and restart its wait."""
        self._director.touch(self._fader.t)

    def hold(self, trigger: str, name: str, seconds: float, rank: int, t: float) -> str | None:
        """Hold look `name` for trigger `trigger` until engine time
        `t + seconds`, then return to the journalled look. A hold already
        running is replaced and keeps its journal; when it holds the same
        look and nothing waits, only its deadline moves. The look starts
        with its own fade, or waits for a running one and holds from the
        frame it starts; it leaves the master alone. Returns why not, or
        None."""
        look = self._book.looks.get(name)
        if look is None:
            return self._unknown(name)
        held = self._hold
        if held is not None and held.look == name and self._pending is None and math.isfinite(held.until):
            # The look already runs: a fresh stack would restart it.
            self._hold = replace(held, trigger=trigger, rank=rank, until=float(t) + float(seconds))
            logger.info("trigger %s holds look %s for %gs", trigger, name, seconds)
            return None
        journal = held.journal if held is not None else self._journal()
        look = replace(look, master=None)
        if self._fader.fading:
            def start(now: float) -> str | None:
                reason = self._begin(look, name, None)
                hold = self._hold
                if hold is not None and hold.look == name:
                    if reason is None:  # hold from this frame
                        self._hold = replace(hold, until=float(now) + float(seconds),
                                             journal=hold.journal._replace(live=False))
                    elif hold.journal.live:
                        self._hold = None
                    else:
                        self._hold = replace(hold, until=float(now))  # returns at once
                return reason

            self._pending = _Recall(name, start, True)
            until = math.inf
        elif (reason := self._begin(look, name, None)) is not None:
            return reason
        else:
            # The journal holds a queued operator recall or return, and a
            # queued hold start is replaced by this one: either way it goes.
            self._pending = None
            until = float(t) + float(seconds)
            journal = journal._replace(live=False)
        self._hold = Hold(trigger, name, rank, until, journal)
        logger.info("trigger %s holds look %s for %gs", trigger, name, seconds)
        return None

    def release(self) -> None:
        """End a hold without returning: the operator took over."""
        self._hold = None
        if self._pending is not None and self._pending.by_hold:
            self._pending = None

    def edit(self) -> None:
        """The operator added, removed or moved a layer of the running
        stack, which ends a running fade: end a hold without returning, and
        drop a recall that waits for the fade, so neither replaces the edit.
        The look stays current, changed until a save keeps it; a made look
        stays the one a save with no name keeps, as edited, under its own
        name."""
        self._hold = self._pending = None

    def leave(self) -> None:
        """The operator sent a whole look: end a hold
        without returning, drop a recall that waits for the fade, clear the
        last recall's error, and make no look current or fading. The file
        keeps naming the last look (`_commit`)."""
        self._hold = self._pending = self._recalled = self._fading = self._made = self.error = None
        self._book = self._book.with_current(None)

    def _journal(self) -> _Recall:
        """Where a hold returns to: a return still queued from the last
        hold, else a recall the operator queued behind the running fade,
        else the live stack. A queued recall whose look is deleted before
        the return falls back to the live state."""
        pending = self._pending
        if pending is not None and pending.returning:
            return pending
        live = self._snapshot()
        if pending is not None and not pending.by_hold:
            name = pending.name

            def queued(now: float) -> str | None:
                return (pending.start if name in self._book.looks else live.start)(now)

            return pending._replace(start=queued)
        return live

    def _snapshot(self) -> _Recall:
        """A recall of the live stack."""
        current = self._book.current
        saved = self._book.looks.get(current) if current is not None else None
        look = replace(self._deck.snapshot(), fade=saved.fade if saved else DEFAULT_FADE)
        recalled = self._recalled

        def back(now: float) -> str | None:
            reason = self._begin(look, current, None)
            if reason is None:
                self._recalled = recalled
            return reason

        return _Recall(current, back, live=True)

    def before_frame(self, t: float) -> None:
        """Before the frame at engine time `t` renders: start a recall that
        waited for the last fade, end a trigger hold whose time is up, then
        step the idle cycle, which waits while a hold runs or the look has
        unsaved edits. Never raises."""
        try:
            if self._pending is not None and not self._fader.fading:
                start = self._pending.start
                self._pending = None
                if (reason := start(t)) is not None:
                    self._fail(reason)
            held = self._hold
            if held is not None and t >= held.until:
                self._hold = None
                # The room event counts as input: the idle wait restarts.
                self._director.touch(t)
                logger.info("trigger %s hold ended; returning", held.trigger)
                if self._fader.fading:
                    self._pending = held.journal._replace(by_hold=True, returning=True)
                elif (reason := held.journal.start(t)) is not None:
                    self._fail(reason)
            if self._hold is not None:
                return
            book = self._book
            # Unsaved edits are not idle: the wait starts again, so the cycle never drops them.
            if self._director.due(t, book.cycle) and self.changed():
                self._director.touch(t)
            if (slot := self._director.tick(t, book.in_cycle, book.cycle)) is not None:
                self._play_slot(slot)
            seed = self._director.coming(book.in_cycle, book.cycle)
            if seed is not None and (self._making is None or self._making[0] != seed):
                self._making = (seed, self._make(seed))
        except Exception as exc:  # noqa: BLE001  the aura must not end over a look
            self._fail(f"look recall failed: {describe_exception(exc)}")

    def _make(self, seed: int) -> Future[Made]:
        """Start making the look of a fresh slot from `seed` off the loop thread."""
        variety = self._variety
        return self._submit(lambda: variety.surprise(seed))

    def _play_slot(self, slot: Slot) -> None:
        """Play the director's `slot`: recall a saved look, unless it is the
        current one as saved and no fade runs, or play a fresh one."""
        book = self._book
        if slot.name is None:
            self._play_fresh(slot.seed)
        elif (
            slot.name in book.looks
            and (slot.name != book.current or self.changed() or self._fader.fading)
            and (reason := self.recall(slot.name)) is not None
        ):
            self._fail(reason)

    def _play_fresh(self, seed: int) -> None:
        """Play the look made fresh from `seed`, made ahead (or now) and done;
        else the look the director drew for the slot instead, keeping the
        making for the next fresh slot unless it failed (class docstring)."""
        making = self._making
        future = making[1] if making is not None and making[0] == seed else self._make(seed)
        if not future.done():
            self._making = (seed, future)
            slot = self._director.instead()
            logger.info("the fresh look from seed %d is not made yet, so this slot plays %s; the next fresh slot "
                        "plays it", seed, slot.name)
            self._play_slot(slot)
            return
        self._making = None
        try:
            made = future.result()
        except Exception as exc:  # noqa: BLE001  a make that failed: the slot plays a look of the cycle
            self._play_slot(self._director.instead(owe=False))
            self._fail(f"cannot make a fresh look: {describe_exception(exc)}")  # after the recall, which clears it
            return
        if (reason := self.play(made)) is not None:
            self._fail(reason)

    def _start(self, name: str, fade: float | None) -> str | None:
        """Recall saved look `name`: fade to it and make it current."""
        look = self._book.looks.get(name)
        if look is None:
            return f"cannot recall {name!r}: it was deleted"
        if (reason := self._begin(look, name, fade)) is not None:
            return reason
        self._recalled = self._saved(look.master)
        self._made = None
        self.error = None
        logger.info("recalled look %s", name)
        if self._commit(self._book.with_current(name)) is not None:
            logger.warning("look %r is running, but the looks file still names the last one", name)
        return None

    def _saved(self, master: float | None) -> _Saved:
        """What `changed` compares the live state with from now on: the
        running stack as it is, and `master`."""
        return _Saved(_edited(self._deck.snapshot()), master, self._deck.controls.snapshot_json())

    def _begin(self, look: Look, name: str | None, fade: float | None) -> str | None:
        """Build `look`'s stack and fade to it; `name` labels it (None: the
        journalled live state). Changes nothing unless every step that can
        fail has passed."""
        what = repr(name) if name is not None else "the look before the trigger"
        reason = (
            self._master.check(look.master) if look.master is not None else None
        ) or self._deck.recall(look, look.fade if fade is None else fade)
        if reason is not None:
            return f"cannot recall {what}: {reason}"
        self._fading = name
        if look.master is not None:
            self._master.set(look.master)
        return None

    def _commit(self, book: LookBook) -> str | None:
        """Write `book` to the file, then make it the live one. With no look
        current, the file names the look it named before while that look
        is in it, so a restart comes back in it."""
        kept = book.current is None and self._restart in book.looks
        on_file = book.with_current(self._restart) if kept else book
        try:
            write_atomic(self._path, on_file.to_bytes())
        except OSError:
            logger.warning("cannot write the looks file %s", self._path, exc_info=True)
            return "cannot write the looks file; nothing was saved"
        self._book = book
        self._restart = on_file.current
        return None

    def _fail(self, reason: str) -> None:
        self.error = reason
        logger.warning("%s", reason)

    def _unknown(self, name: str) -> str:
        return unknown("look", name, self._book.looks)
