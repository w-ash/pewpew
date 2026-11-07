"""Aura control: every request an operator surface can make, in one place.

`AuraControl` is the object a surface holds: the preview page's socket
today, an MCP server next. Each request is a control name and its fields
(`REQUESTS`), as `request(message)` takes it, or a method of the same name.
It runs on the caller's thread and returns why it was refused, or None:
`request` a `Refusal`, a method its reason, or a `Refusal` that names the
part of a look it refused; a `surprise` or a `vary` returns a future of
its answer instead. A param is set by its address
(pewpew.compose.controls), such as `layers.base.comet.speed`,
`layers.base.opacity` or a signal's `signals.breath.rate`, and a pick runs
a pattern on one layer, the bottom one unless it names another. A `look`
request runs a whole look sent by a client outside the package, only in a
run that takes looks (`run --accept-looks`; ADR-020 amendment
"capabilities"). A `surprise` fades to a look made from a seed, a `vary`
to one made like the running look (pewpew.aura.variety), each unsaved
until a `save` with no name saves the running look under a name of its
own (`keep` is that save, for clients outside the package). The
reason, and every value in `state`, may cross an unauthenticated socket
(architecture §5): names, never paths.

Thread discipline. A request is checked on the caller's thread and only
what passed reaches the loop thread, through `Calls`: `call_soon` for a
change that cannot fail there (a param, the master, a blink), `ask` for
one whose outcome only the loop knows (a pick loads a file and builds a
layer; a look request writes the looks file; a look sent whole loads its
patterns and builds its layers). A `surprise` or `vary` makes its look
on a thread of its own (pewpew.aura.variety `in_background`), which takes
a second or more, and answers once the look starts or is refused: never
on the loop thread, nor on the caller's, so a blackout or any other
request sent after it is not held up. A request that changes what runs
(a pick, a layer edit, a recall, a look, a made look) does not run once
one asked for after it has run (`OVERTAKEN`): a look made while the
operator recalled another never replaces it. Every request but `arm`,
`fire`, `scan`, `rebind` and `blink` is operator input: on the loop thread
it first touches the looks, so the idle cycle stops. A cue fired from the
page stands in for a room event and leaves the idle cycle alone.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from typing import Any, Protocol, TypeVar, cast

from pewpew.aura.book import check_name
from pewpew.aura.deck import Deck
from pewpew.aura.looks import Looks
from pewpew.aura.master import Master
from pewpew.aura.triggers import Triggers
from pewpew.aura.variety import Made, Variety, fade_to, in_background
from pewpew.compose import Knob, Look, layer_address
from pewpew.compose.stack import check_fade, check_on_off, parse_fade
from pewpew.errors import Refusal, describe_exception, unknown
from pewpew.fx import catalog as book
from pewpew.fx.codec import MAX_LAYERS, decode_program
from pewpew.fx.graph import check_id, free_id
from pewpew.fx.ops import OPS
from pewpew.fx.surprise import check_seed, check_strength
from pewpew.lab.check import ready
from pewpew.pace import ASK_TIMEOUT_S, Calls
from pewpew.params import Int
from pewpew.params.kinds import Parsed
from pewpew.problems import Refused
from pewpew.room.blink import Blink

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Each request: its control name, which is also the method's, and the
# fields passed to that method in order, with their defaults. No field is
# `id`: any message may carry one, for its answer (pewpew.sinks.preview).
REQUESTS: dict[str, tuple[tuple[str, object], ...]] = {
    "set": (("name", None), ("value", None)),
    "pick": (("name", None), ("layer", None)),
    "add_layer": (("layer", None), ("below", None)),
    "remove_layer": (("lid", None),),
    "move_layer": (("lid", None), ("to", None)),
    "front": (("paths", None),),
    "master": (("value", None),),
    "blackout": (("on", None),),
    "recall": (("name", None), ("fade", None)),
    "look": (("look", None), ("fade", None)),
    "surprise": (("seed", None),),
    "vary": (("strength", None), ("seed", None)),
    "keep": (),
    "save": (("name", None), ("fade", None), ("master", True)),
    "delete": (("name", None),),
    "cycle": (("name", None), ("on", None)),
    "fade": (("name", None), ("fade", None)),
    "arm": (("on", None),),
    "fire": (("name", None), ("value", None)),
    "scan": (),
    "rebind": (("board", None), ("address", None)),
    "blink": (("fixture", None),),
}

NO_LOOKS = "this engine takes no looks: start it with `python -m pewpew run ... --preview --accept-looks`"
NO_LOOKS_FILE = "no looks file: start the run with --looks PATH"
BUSY = "the engine is busy, so the look did not start; send it again"
BUSY_LAYER = "the engine is busy, so the layer was not added; send it again"
OVERTAKEN = "a request sent after this one changed what runs first, so this one did not run"
# What an added layer's id is made from when it has no node to make one from.
LAYER = "layer"


class Boards(Protocol):
    """The two board fixes: find the boards on the network, and point a
    room board at one. `pewpew.health.HealthMonitor` implements it."""

    def scan(self) -> str | None: ...

    def rebind(self, board: object, address: object) -> str | None: ...


class AuraControl:
    """The aura's controls over one run: the deck, the master, the looks
    and triggers, and, when the run has them, the blink, the boards and the
    health snapshot. `accept_looks` lets a client send a whole look."""

    def __init__(
        self,
        calls: Calls,
        deck: Deck,
        master: Master,
        triggers: Triggers,
        *,
        looks: Looks | None = None,
        blink: Blink | None = None,
        boards: Boards | None = None,
        health: Callable[[], dict] | None = None,
        accept_looks: bool = False,
        variety: Variety | None = None,
        timeout: float = ASK_TIMEOUT_S,
    ) -> None:
        self._calls = calls
        self._deck = deck
        self._master = master
        self._triggers = triggers
        self._looks = looks
        self._blink = blink
        self._boards = boards
        self._health = health
        self._accept_looks = accept_looks
        self._variety = variety if variety is not None else Variety(deck)
        self._timeout = timeout
        # The catalog a page shows, and what it was made from: the ops and the pattern names.
        self._catalog: tuple[tuple[object, ...], dict] | None = None
        # Each request that changes what runs is numbered as it is asked
        # (any thread); `_ran` is the number of the last that ran (loop thread).
        self._numbers = itertools.count(1)
        self._ran = 0

    # ---- what a surface shows (any thread) -----------------------------------

    @property
    def capabilities(self) -> tuple[str, ...]:
        """The requests this run takes beyond the page's own: `look` when it
        takes looks. For clients outside the package; the page never reads
        it (ADR-020 amendment "capabilities")."""
        return ("look",) if self._accept_looks else ()

    def describe(self) -> list[dict]:
        """Every knob of the running stack, by address, in display order."""
        return self._deck.controls.describe()

    def values(self) -> dict:
        """Every knob's value in its JSON form, by address."""
        return self._deck.controls.snapshot_json()

    def mod(self) -> dict:
        """Each knob a route drives, at its live value, by address
        (pewpew.compose.modulation): a page's read-only readout."""
        return dict(self._deck.fader.current.mod())

    def state(self) -> dict:
        """The aura state; JSON-ready, names only. Cheap: a sink reads it
        every frame. `fading` and `progress` are the crossfade's, whatever
        started it: a recall, a pick, a pushed or a made look."""
        fader = self._deck.fader
        progress = fader.progress
        return {
            "pattern": self._deck.current,
            "patterns": self._deck.catalog.names,
            "stack": fader.current.state(),
            "fading": fader.fading,
            # Coarse, so the state message changes a few times per fade rather than every frame.
            "progress": None if progress is None else round(progress * 20) / 20,
            "master": self._master.level,
            "cap": self._master.cap,
            "blackout": self._master.blackout,
            "looks": self._looks.state() if self._looks is not None else None,
            "triggers": self._triggers.state(),
        }

    def health(self) -> dict | None:
        """The latest health snapshot, or None when the run has no monitor."""
        return self._health() if self._health is not None else None

    def catalog(self) -> dict:
        """What a layer can run, for a page's "add layer" cards, and what
        each blend mode does (pewpew.fx.catalog.page). The same object until
        an op registers (a pattern file that defines one loads or reloads)
        or the pattern names change, so a sink serializes it once. Never
        raises: when the catalog cannot be made (an op's example that does
        not build), the page keeps the last one, or gets no cards, and the
        log says why once."""
        names = self._deck.catalog.names
        made = (*OPS.values(), *names)
        cached = self._catalog
        if cached is None or cached[0] != made:
            try:
                cards = book.page(book.catalog(), names)
            except Exception:  # contained: one op file must not take the page down
                logger.warning("the page keeps its last catalog: the catalog cannot be made", exc_info=True)
                cards = cached[1] if cached is not None else {"cards": [], "blends": []}
            cached = self._catalog = (made, cards)
        return cached[1]

    def rescan(self) -> None:
        """Refresh the pattern names from disk (a file added since launch)."""
        self._deck.catalog.rescan()

    # ---- requests (any thread) -------------------------------------------------

    def request(self, message: Mapping[str, object]) -> Refusal | Future[Refusal | None] | None:
        """Act on one message `{"type": control, field: value, ...}`. Returns
        why it was refused, or None when it was accepted; for a look to make
        (`surprise`, `vary`) that passed its checks, a future of either. A
        message that names no control is refused when it carries an `id`, so
        its sender gets an answer, and passed over without one."""
        kind = message.get("type")
        if not isinstance(kind, str) or kind not in REQUESTS:
            return None if message.get("id") is None else Refusal(unknown("control", kind, REQUESTS))
        answer = getattr(self, kind)(*(message.get(key, default) for key, default in REQUESTS[kind]))
        if isinstance(answer, str):
            name = message.get("name") if kind == "set" else None  # a refused set names its knob
            return Refusal(answer, name if isinstance(name, str) else None)
        return answer

    def set(self, name: object, value: object) -> str | None:
        """Set the param at address `name` of the running stack, native or JSON."""
        if not isinstance(name, str):
            return f"set takes a param address, got {name!r}"
        found, reason = self._deck.controls.parse(name, value)
        if reason is not None:
            return reason  # network-safe wording; `hint` names a file, so it stays out
        assert found is not None
        knob, parsed = found
        self._calls.call_soon(lambda: self._set(name, knob, parsed))
        return None

    def pick(self, name: object, layer: object = None) -> str | None:
        """Run the named pattern, one of `state()["patterns"]`, fresh at its
        defaults on `layer` (None: the bottom one). On a look of several
        layers the pick is an edit of the look, which stays current and
        changed; on a lone layer it replaces the look, and no look is
        current. Waits for the loop thread; on refusal the old pattern keeps
        running."""
        if not isinstance(name, str):
            return f"pick takes a pattern name, got {name!r}"
        if layer is not None and (reason := self._layer(layer)) is not None:
            return reason
        catalog = self._deck.catalog
        catalog.rescan()
        if name not in catalog.names:
            # Refused before anything resolves: no path reaches `resolve`.
            return unknown("pattern", name, catalog.names)
        return self._ask(self._runs(lambda: self._pick(name, layer)),
                         f"{name!r} is still loading; the page shows it once it runs")

    def add_layer(self, layer: object, below: object = None) -> Refusal | str | None:
        """Add `layer`, a layer of a look in the looks file's form, to the
        running look, under layer `below`, or on top when None. Its patterns
        go by name, never by file, as a pick names one. Without an `id` it
        gets a free one made from its `out` node (`plasma`, `plasma2`). It
        is checked as the looks file's loader checks a layer, a problem
        named by its address, and edits the running look, which a save
        keeps; the other layers run on. Like a remove or a move, it ends a
        trigger's hold and a running fade, and drops a recall that waits for
        that fade (`Looks.edit`). Waits for the loop thread; a layer
        refused, also when the loop is too busy to take it in time, is never
        added, so sending it again cannot add it twice."""
        if not isinstance(layer, dict):
            return f"add_layer takes a layer, an object with 'nodes', got {type(layer).__name__}"
        if below is not None and (reason := self._layer(below)) is not None:
            return reason
        return self._ask(self._runs(lambda: self._add(layer, below)), BUSY_LAYER, definite=True)

    def remove_layer(self, lid: object) -> str | None:
        """Stop layer `lid` of the running look; the other layers run on.
        Waits for the loop thread."""
        if (reason := self._layer(lid)) is not None:
            return reason
        assert isinstance(lid, str)  # _layer refuses anything else
        # Checked again on the loop thread: a recall since may have changed the layers.
        return self._ask(self._runs(lambda: self._layer(lid) or self._edited(self._deck.remove(lid))),
                         f"layer {lid!r} is still going")

    def move_layer(self, lid: object, to: object) -> str | None:
        """Run layer `lid` of the running look at render index `to` among
        its layers (0: the bottom). Waits for the loop thread."""
        if (reason := self._layer(lid) or _place(to, len(self._deck.fader.current.layers))[1]) is not None:
            return reason
        assert isinstance(lid, str)  # _layer refuses anything else
        return self._ask(self._runs(lambda: self._move(lid, to)), f"layer {lid!r} is still moving")

    def front(self, paths: object) -> str | None:
        """Show the knobs at addresses `paths` first, in that order: the
        look's front, an edit a save keeps. Waits for the loop thread."""
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            return f"front takes a list of knob addresses, got {paths!r}"
        return self._ask(lambda: self._edited(self._deck.fader.current.set_front(paths)), "the front is still changing")

    def master(self, value: object) -> str | None:
        """Set the master level, at most the cap."""
        reason = self._master.check(value)
        if reason is not None:
            return reason
        level = float(value)  # type: ignore[arg-type]
        self._calls.call_soon(lambda: self._operator(lambda: self._master.set(level)))
        return None

    def blackout(self, on: object) -> str | None:
        """Black out (True) or restore the master level (False)."""
        reason = check_on_off("blackout", on)
        if reason is not None:
            return reason
        self._calls.call_soon(lambda: self._operator(lambda: self._master.set_blackout(bool(on))))
        return None

    def recall(self, name: object, fade: object = None) -> str | None:
        """Crossfade to a saved look over `fade` seconds, or its own fade."""
        return self._look(
            name, fade, "is still loading",
            lambda looks: looks.recall(name, fade),  # type: ignore[arg-type]
            runs=True,
        )

    def look(self, look: object, fade: object = None) -> Refusal | str | None:
        """Fade to `look`, one look in the looks file's form, over `fade`
        seconds or its own fade; a running fade ends first, as a pick ends
        it. Only a run that takes looks accepts one. It is checked as the
        looks file's loader checks a look, with each pattern named as a
        pick is, never by a file, and runs as a pick does: unsaved, with no
        look current, until a save keeps it. A look refused never starts,
        also when the loop is too busy to take it in time."""
        if not self._accept_looks:
            return NO_LOOKS
        if not isinstance(look, dict):
            return f"a look is an object with 'layers', got {type(look).__name__}"
        seconds = None
        if fade is not None:
            seconds, reason = parse_fade(fade)
            if reason is not None:
                return reason
        # Definite: a client that is told the look was refused must not see it start later.
        return self._ask(self._runs(lambda: self._play(look, seconds)), BUSY, definite=True)

    def surprise(self, seed: object = None) -> str | Future[Refusal | None]:
        """Fade to a look made from `seed` (None: the run's next) for this
        aura's map, over its own fade, unsaved, as a pick runs; a `save`
        with no name saves it. Returns why `seed` is refused, else a future
        of the answer (`_made`). A look refused never starts."""
        if seed is not None and (reason := check_seed(seed)) is not None:
            return reason
        return self._made(lambda: self._variety.surprise(cast("int | None", seed)))

    def vary(self, strength: object = None, seed: object = None) -> str | Future[Refusal | None]:
        """Fade to a look like the running one, moved by `strength` (above 0,
        at most 1; None: the default) from `seed` (None: the run's next),
        unsaved, as `surprise` does."""
        if strength is not None and (reason := check_strength(strength)) is not None:
            return reason
        if seed is not None and (reason := check_seed(seed)) is not None:
            return reason
        looks = self._looks
        source = looks.source if looks is not None else None
        by, seed_ = cast("float | None", strength), cast("int | None", seed)
        return self._made(lambda: self._variety.vary(by, seed_, of=source))

    def keep(self) -> str | None:
        """`save` with no name, for clients outside the package; the
        preview page sends that `save` itself."""
        return self.save(None)

    def save(self, name: object = None, fade: object = None, master: object = True) -> str | None:
        """Save the live state as look `name`, or with no name under the
        name it offers: a made look's (`surprise 7`), else a copy's of the
        current look, else `kept`, with a number past the first one taken
        (`Looks.offered`). `master` False leaves the master out, and None
        keeps the replaced look's choice."""
        return self._look(
            name, fade, "is still saving",
            lambda looks: looks.save(name, fade, master),  # type: ignore[arg-type]
            check_on_off("save's master", master) if master is not None else None,
            nameless=True,
        )

    def delete(self, name: object) -> str | None:
        """Delete a saved look."""
        return self._look(
            name, None, "is still being deleted",
            lambda looks: looks.delete(name),  # type: ignore[arg-type]
        )

    def cycle(self, name: object, on: object) -> str | None:
        """Set whether the idle cycle plays a look."""
        return self._look(
            name, None, "is still changing",
            lambda looks: looks.set_cycle(name, on),  # type: ignore[arg-type]
            check_on_off("cycle", on),
        )

    def fade(self, name: object, fade: object) -> str | None:
        """Set a look's own fade, leaving its knobs as saved."""
        return self._look(
            name, fade, "is still changing",
            lambda looks: looks.set_fade(name, fade),  # type: ignore[arg-type]
            None if fade is not None else "a look's fade needs a number of seconds",
        )

    def arm(self, on: object) -> str | None:
        """Arm (True) or disarm (False) the room-event triggers."""
        return self._triggers.arm(on, "page")

    def fire(self, name: object, value: object = None) -> str | None:
        """Submit a room event by trigger name, as a cue; its outcome shows
        in `state()["triggers"]`."""
        return self._triggers.submit("page", name, value)

    def scan(self) -> str | None:
        """Start looking for WLED boards on the network."""
        if self._boards is None:
            return "this run streams to no boards"
        return self._boards.scan()

    def rebind(self, board: object, address: object) -> str | None:
        """Point a room board at an address the last scan found."""
        if self._boards is None:
            return "this run streams to no boards"
        return self._boards.rebind(board, address)

    def blink(self, fixture: object) -> str | None:
        """Flash one room fixture white and off (pewpew.room.blink)."""
        blink = self._blink
        if blink is None:
            return "blink needs a room map (run --room)"
        reason = blink.check(fixture)
        if reason is None:
            self._calls.call_soon(lambda: blink.start(fixture))  # type: ignore[arg-type]
        return reason

    # ---- the loop thread -------------------------------------------------------

    def _ask(self, fn: Callable[[], T | None], late: str, *, definite: bool = False) -> T | str | None:
        return self._calls.ask(lambda: self._operator(fn), late, self._timeout, definite=definite)

    def _operator(self, fn: Callable[[], T]) -> T:
        """Operator input: stop the idle cycle, then run `fn`."""
        if self._looks is not None:
            self._looks.touch()
        return fn()

    def _set(self, path: str, knob: Knob, value: Any) -> None:
        """Operator input: set `knob` at address `path`, as it passed `parse`
        on another thread. Must not raise: a pick or a recall queued first
        runs another pattern by now, and a reload can narrow the range, so
        either drops the set, with the reason in the log."""

        def apply() -> None:
            found = self._deck.controls.find(path)
            if found is None or found.params is not knob.params:
                logger.warning("dropped a live set of %r: the pattern it was for no longer runs", path)
                return
            try:
                knob.params.set(knob.name, value)
            except ValueError:
                logger.warning("dropped a live set of %r to %r: the param no longer accepts it", path, value)

        self._operator(apply)

    def _layer(self, layer: object) -> str | None:
        """Why `layer` names no layer of the running stack, or None."""
        ids = [live.id for live in self._deck.fader.current.layers]
        return None if isinstance(layer, str) and layer in ids else unknown("layer", layer, ids)

    def _pick(self, name: str, layer: object) -> str | None:
        """Run `name` on `layer`, which `pick` checked: a layer id, or None
        for the bottom layer."""
        current = self._deck.fader.current
        lid = layer if isinstance(layer, str) else current.layers[0].id
        if (reason := self._layer(lid)) is not None:
            return reason  # a recall since the check changed the layers
        running = current.layer(lid).label
        reason = self._deck.put(lid, name)
        if reason is not None:
            return f"cannot switch to {name!r}, {running} is still running: {reason}"
        if self._looks is not None:
            # The operator's pick wins over a waiting recall and a hold. On a layer among others it
            # edits the look, which stays current, changed, as an added layer does; a lone layer's
            # pick replaces the look.
            if len(current.layers) > 1:
                self._looks.edit()
            else:
                self._looks.leave()
        logger.info("switched to %s", name)
        return None

    def _add(self, doc: dict, below: object) -> Refusal | str | None:
        """Check layer `doc` and run it under layer `below` (None: on top),
        as `add_layer` says. A problem with the layer names its part."""
        ids = [live.id for live in self._deck.fader.current.layers]
        if below is not None and below not in ids:
            return unknown("layer", below, ids)  # a recall since the check changed the layers
        if len(ids) >= MAX_LAYERS:
            return f"a look has at most {MAX_LAYERS} layers; remove one first"
        if "id" not in doc:
            doc = {"id": free_id(_id_base(doc), ids), **doc}
        elif doc["id"] in ids:
            return Refusal(f"the look has a layer {doc['id']!r}; give another id, or none for a free one",
                           layer_address(doc["id"]))
        look = self._ready({"layers": [doc]})
        if isinstance(look, Refusal):
            return look
        layer = look.layers[0]
        reason = self._edited(self._deck.add(layer, ids.index(below) if isinstance(below, str) else len(ids)))
        if reason is None:
            logger.info("added layer %s", layer.id)
        return reason

    def _move(self, lid: str, to: object) -> str | None:
        """Run layer `lid` at render index `to`, both checked again: a recall
        since the check may have changed the layers."""
        index, reason = _place(to, len(self._deck.fader.current.layers))
        if reason is not None:
            return reason
        assert index is not None
        return self._layer(lid) or self._edited(self._deck.move(lid, index))

    def _edited(self, reason: str | None) -> str | None:
        """Pass on `reason`, why a layer edit failed (None: it ran). After
        an edit that ran, the looks drop what would replace it
        (`Looks.edit`)."""
        if reason is None and self._looks is not None:
            self._looks.edit()
        return reason

    def _play(self, doc: dict, fade: float | None) -> Refusal | str | None:
        """Check look `doc` and start it, as `look` says; `fade` is checked.
        A problem with the look names its part."""
        look = self._ready(doc)
        if isinstance(look, Refusal):
            return look
        if look.master is not None and (reason := self._master.check(look.master)) is not None:
            return Refusal(reason, "master")
        reason = self._deck.recall(look, look.fade if fade is None else fade)
        if reason is not None:
            return f"cannot start the look: {reason}"
        if look.master is not None:
            self._master.set(look.master)
        if self._looks is not None:
            self._looks.leave()
        logger.info("started a look a client sent")
        return None

    def _ready(self, doc: dict) -> Look | Refusal:
        """Look `doc` as the looks file's loader checks one, each pattern
        named as a pick is, or its refusal, named by its first problem's
        part."""
        try:
            return ready(doc, catalog=self._deck.catalog).look
        except Refused as exc:
            return Refusal(str(exc), exc.problems[0].path or None)

    def _made(self, make: Callable[[], Made]) -> Future[Refusal | None]:
        """Make a look on a thread of its own, then start it on the loop
        thread (`Looks.play`, or the deck alone without a looks file), as a
        request numbered now (`_runs`). The future holds the answer once
        it starts or is refused; a look that cannot be made, or is
        refused, never starts."""
        number = next(self._numbers)

        def job() -> Refusal | None:
            try:
                made = make()
            except ValueError as exc:  # nothing made passed the content gate, or the look does not check
                return Refusal(str(exc))
            except Exception as exc:  # contained: the asker still gets its answer
                logger.warning("a look could not be made", exc_info=True)
                return Refusal(f"the look cannot be made: {describe_exception(exc)}")
            answer = self._ask(self._runs(lambda: self._play_made(made), number), BUSY, definite=True)
            return Refusal(answer) if isinstance(answer, str) else answer

        return in_background(job)

    def _play_made(self, made: Made) -> str | None:
        return self._looks.play(made) if self._looks is not None else fade_to(self._deck, made)

    def _look(
        self, name: object, fade: object, late: str, call: Callable[[Looks], str | None],
        refused: str | None = None, *, runs: bool = False, nameless: bool = False,
    ) -> str | None:
        """Check a look request on the caller's thread: the looks file, the
        name (None passes when `nameless`: the request means what plays),
        the fade, then `refused` (the request's own check). If all pass, run
        `call` on the loop thread, as a request that changes what runs when
        `runs` (`_runs`); `late` ends the timeout reply."""
        looks = self._looks
        if looks is None:
            return NO_LOOKS_FILE
        named = name is not None or not nameless
        reason = (check_name(name) if named else None) or (check_fade(fade) if fade is not None else None) or refused
        if reason is not None:
            return reason
        run = self._runs(lambda: call(looks)) if runs else lambda: call(looks)
        subject = f"look {name!r}" if named else "the look"
        return self._ask(run, f"{subject} {late}")

    def _runs(self, fn: Callable[[], T | None], number: int | None = None) -> Callable[[], T | str | None]:
        """`fn`, a request that changes what runs, numbered `number` (None:
        the next number, now), as the loop thread runs it: `OVERTAKEN` once
        a request numbered after it has run, else `fn`'s answer."""
        number = next(self._numbers) if number is None else number

        def run() -> T | str | None:
            if self._ran > number:
                return OVERTAKEN
            answer = fn()
            if answer is None:
                self._ran = number
            return answer

        return run


def _id_base(doc: dict) -> str:
    """What the id of layer `doc` (the looks file's form) is made from when
    it gives none: its program's `out` node's id, given or the last node in
    the order they run, as the loader decodes it, else `LAYER`."""
    program, _ = decode_program(doc)
    out = program.out if program is not None else doc.get("out")
    return out if isinstance(out, str) and check_id(out, "layer") is None else LAYER


def _place(value: object, count: int) -> Parsed[int]:
    """`value` as a render index among `count` layers, or why it cannot be
    one, in the params' words. Never raises."""
    if count < 2:
        return None, "the look has one layer, so it has nowhere else to go"
    return Int(0, 0, count - 1).parse("to", value)
