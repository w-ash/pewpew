"""Room-event triggers: one queue, stamped at the render tick, arbitrated
on engine time, logged as JSONL.

An input (today only the preview page's fire-cue buttons and arm switch)
calls `Triggers.submit(source, name, value)` from any thread; the call only
checks the event's shape and queues it. The queue drains on the loop thread
before the next frame renders (`before_frame`, a `before` hook of the paced
loop), where each event is stamped with that frame's engine `t` and tick
number, judged, logged, and applied. Nothing on this path reads a wall
clock, so the same events at the same ticks give the same frames
(T-1…T-5).

A new input is an adapter that calls `submit` (and, if it can arm, `arm`).
It names itself as the event's `source`. ADR-009's 2026-11-02 amendment
says what a network input must add before it is wired.

An event is a trigger name from the looks file's `triggers` section
(pewpew.aura.book), a source, and an optional number: None is an impulse (a
button press), a number is a level (a sensor). The trigger gives its
priority class and what it does: hold a look as a temporary override
(`Looks.hold`), and in every case reach the running look as data in
`features.events` for that one frame (`pewpew.features.EventFeatures`).

Arbitration (`Arbiter.judge`), in this order, every interval in engine
seconds; the first rule that matches drops the event with its reason:

1. `disarmed`: the arm switch is off. Nothing else is recorded.
2. `unknown`: no trigger has the name.
3. `debounce`: the same source sent the same name less than the trigger's
   `debounce` ago, counting dropped arrivals too, so chatter stays dropped.
4. `edge`: a level that is not a rise from <= 0 to > 0 for that source and
   name (Chromatik triggers fire on change only [S1265]). Every level
   arrival sets the level, a debounced one too, so a fall that chatter
   hid still lets the next rise fire. Impulses are always edges.
5. `cooldown`: that source's last accepted event of that name is less than
   the trigger's `cooldown` ago.
6. `outranked`: the trigger holds a look, and a hold of a higher class is
   still running. An equal or higher class replaces the hold.
7. `rate`: `RATE_MAX` events were accepted in the last `RATE_WINDOW`
   seconds, all sources together. Operator-class events are deliberate:
   the rate limit neither drops nor counts them.

Within one tick, arm changes apply in arrival order, and the events between
them are judged highest class first (operator, performer, button, sensor),
then in arrival order.

The log has one JSON object per line. Each run starts with a header
record, written at launch, so a log that spans restarts (launchd appends
to the same file) separates its runs; then the events, in the order judged:

    {"run": {"seed": 0, "fps": 60.0, "look": "dusk", "armed": false}}
    {"tick": 412, "t": 6.866666666666667, "source": "page", "arm": true}
    {"tick": 530, "t": 8.833333333333334, "source": "page", "name": "cue1",
     "value": null, "priority": "button", "fired": true, "reason": null}

`reason` is the drop reason above, or null when it fired; `error` is added
when a fired event's look could not be held. `tick` counts frames from the
start of the run; `t` is exact (JSON floats round-trip). Replaying one
run's records (`pewpew.jsonfile.read_run`, then `feed`) before the frame
of the same `t` reproduces the run, operator input aside, which the log
does not hold.

`log_max` caps the log file's size in bytes: a write that would pass it
ends the log, as a failed write does, with one warning.

Thread discipline: `submit`, `arm` and `state` run on any thread;
`before_frame` belongs to the loop thread.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from collections import deque
from collections.abc import Mapping
from typing import Any, TextIO

from pewpew.aura.book import Trigger, check_name
from pewpew.aura.looks import Looks
from pewpew.compose.stack import check_on_off
from pewpew.features import Event, EventFeatures
from pewpew.jsonfile import is_number

logger = logging.getLogger(__name__)

RATE_MAX = 8  # accepted events per window, all sources together
RATE_WINDOW = 1.0  # seconds of engine time
MAX_QUEUE = 256  # events waiting for one tick; more are refused
_SOURCE_MAX = 64


class Arbiter:
    """The arbitration rules from 2 on (the module docstring), with the
    state they keep. Pure: time is the `t` passed in."""

    def __init__(self, rate_max: int = RATE_MAX, rate_window: float = RATE_WINDOW) -> None:
        self._rate_max = rate_max
        self._rate_window = rate_window
        self._arrived: dict[tuple[str, str], float] = {}
        self._fired: dict[tuple[str, str], float] = {}
        self._level: dict[tuple[str, str], bool] = {}
        self._recent: deque[float] = deque()

    def judge(
        self, source: str, name: str, value: float | None, trigger: Trigger | None,
        t: float, held_rank: int | None = None,
    ) -> str | None:
        """Why the event is dropped, or None to fire it. `held_rank` is the
        rank of the hold still running, or None."""
        if trigger is None:
            return "unknown"
        key = (source, name)
        last = self._arrived.get(key)
        self._arrived[key] = t
        rising = True
        if value is not None:
            on = value > 0.0
            rising = on and not self._level.get(key, False)
            self._level[key] = on
        if last is not None and t - last < trigger.debounce:
            return "debounce"
        if not rising:
            return "edge"
        fired = self._fired.get(key)
        if fired is not None and t - fired < trigger.cooldown:
            return "cooldown"
        if trigger.look is not None and held_rank is not None and held_rank > trigger.rank:
            return "outranked"
        if trigger.priority != "operator":  # deliberate: never rate-limited
            while self._recent and self._recent[0] <= t - self._rate_window:
                self._recent.popleft()
            if len(self._recent) >= self._rate_max:
                return "rate"
            self._recent.append(t)
        self._fired[key] = t
        return None


class Triggers:
    """The event queue, the arm switch, arbitration, effects and the log.

    `looks` is the aura's saved looks, or None without a looks file; a
    trigger that holds a look needs them. `features` gets each frame's
    fired events, for the running look. `log` is an open text file the JSONL
    goes to, or None; `log_max` caps its size in bytes, counting what the
    file held when opened. A failed write, or one past the cap, is logged
    once and ends the log, never the aura.
    """

    def __init__(self, config: Mapping[str, Trigger], *, features: EventFeatures,
                 looks: Looks | None = None, log: TextIO | None = None,
                 log_max: int | None = None, arbiter: Arbiter | None = None) -> None:
        self._config = dict(config)
        self._arbiter = arbiter or Arbiter()
        self._log = log
        self._log_max = log_max
        self._log_size = _size(log) if log is not None else 0
        self._lock = threading.Lock()
        self._queue: deque[tuple] = deque()
        self._tick = 0
        self._looks = looks
        self._features = features
        self.armed = False
        # The last event judged, for the page: replaced whole.
        self.last: dict | None = None

    @property
    def names(self) -> list[str]:
        return list(self._config)

    # ---- any thread ----------------------------------------------------------

    def submit(self, source: str, name: object, value: object = None) -> str | None:
        """Queue one event for the next tick. Returns why it was refused
        (malformed, or the queue is full), else None; a queued event is
        judged and logged at the tick, whatever its fate."""
        if (reason := check_name(name, "trigger")) is not None:
            return reason
        if value is not None and not is_number(value):
            return f"a trigger value is a finite number or null, got {value!r}"
        return self._put(("event", _source(source), name, None if value is None else float(value)))

    def arm(self, on: object, source: str = "page") -> str | None:
        """Queue an arm switch change for the next tick."""
        if (reason := check_on_off("arm", on)) is not None:
            return reason
        return self._put(("arm", _source(source), on))

    def begin_run(self, **header: Any) -> None:
        """Write the run's header record to the log. Loop thread, before
        the first tick."""
        self._write([{"run": header}])

    def feed(self, record: Mapping[str, Any]) -> None:
        """Queue one log record again, for a replay; a header is skipped."""
        if "run" in record:
            return
        if "arm" in record:
            self.arm(record["arm"], record["source"])
        else:
            self.submit(record["source"], record["name"], record["value"])

    def state(self) -> dict:
        """The page's view; JSON-ready, names only."""
        held = self._looks.held if self._looks is not None else None
        return {
            "armed": self.armed,
            "names": self.names,
            # What each fires: the look it holds and for how long (None: the
            # event only reaches the running look as data).
            "cues": {name: {"look": trigger.look, "hold": trigger.hold} for name, trigger in self._config.items()},
            "held": None if held is None else {
                "trigger": held.trigger, "look": held.look,
                # Infinite while the look waits for a fade; JSON has no infinity.
                "until": held.until if math.isfinite(held.until) else None,
            },
            "last": self.last,
        }

    def _put(self, item: tuple) -> str | None:
        with self._lock:
            if len(self._queue) >= MAX_QUEUE:
                return "too many trigger events at once; this one was dropped"
            self._queue.append(item)
        return None

    # ---- loop thread ---------------------------------------------------------

    def before_frame(self, t: float) -> None:
        """Drain, judge, log and apply the events for the frame at engine
        time `t`, before it renders. Never raises."""
        tick = self._tick
        self._tick += 1
        with self._lock:
            batch = list(self._queue)
            self._queue.clear()
        if batch:
            try:
                self._drain(batch, float(t), tick)
            except Exception:  # the aura must not end over a room event
                logger.exception("trigger events at t=%s were lost", t)

    def _drain(self, batch: list[tuple], t: float, tick: int) -> None:
        records: list[dict] = []
        fired: list[Event] = []
        waiting: list[tuple] = []

        def judge_waiting() -> None:
            waiting.sort(key=lambda item: -_rank(self._config.get(item[2])))  # stable
            for _, source, name, value in waiting:
                records.append(self._judge(source, name, value, t, tick, fired))
            waiting.clear()

        for item in batch:
            if item[0] == "arm":
                judge_waiting()
                self.armed = item[2]
                records.append({"tick": tick, "t": t, "source": item[1], "arm": item[2]})
                logger.info("triggers %s", "armed" if item[2] else "disarmed")
            else:
                waiting.append(item)
        judge_waiting()
        self._features.post(t, tuple(fired))
        self._write(records)

    def _judge(self, source: str, name: str, value: float | None, t: float, tick: int,
               fired: list[Event]) -> dict:
        trigger = self._config.get(name)
        record: dict[str, Any] = {
            "tick": tick, "t": t, "source": source, "name": name, "value": value,
            "priority": trigger.priority if trigger is not None else None,
        }
        if not self.armed:
            reason: str | None = "disarmed"
        else:
            held = self._looks.held if self._looks is not None else None
            held_rank = held.rank if held is not None and t < held.until else None
            reason = self._arbiter.judge(source, name, value, trigger, t, held_rank)
        record["fired"] = reason is None
        record["reason"] = reason
        error = None
        if reason is None and trigger is not None:
            fired.append(Event(name, source, value, trigger.priority, t, tick))
            if trigger.look is not None:
                error = (
                    "no looks file" if self._looks is None
                    else self._looks.hold(name, trigger.look, trigger.hold, trigger.rank, t)
                )
                if error is not None:
                    record["error"] = error
                    logger.warning("trigger %s fired, but %s", name, error)
        self.last = {"name": name, "fired": reason is None, "reason": reason, "error": error}
        return record

    def _write(self, records: list[dict]) -> None:
        if self._log is None or not records:
            return
        text = "".join(json.dumps(r) + "\n" for r in records)
        size = len(text.encode("utf-8"))
        if self._log_max is not None and self._log_size + size > self._log_max:
            logger.warning("the trigger log reached its cap of %d bytes; it stops here", self._log_max)
            self._log = None
            return
        try:
            self._log.write(text)
            self._log.flush()
        except (OSError, ValueError):  # ValueError: the file was closed
            logger.warning("cannot write the trigger log; it stops here", exc_info=True)
            self._log = None
            return
        self._log_size += size


def _size(log: TextIO) -> int:
    """The bytes `log` held when opened; 0 when it is not a real file."""
    try:
        return os.fstat(log.fileno()).st_size
    except (OSError, ValueError):  # io.UnsupportedOperation is both
        return 0


def _rank(trigger: Trigger | None) -> int:
    return trigger.rank if trigger is not None else -1


def _source(source: str) -> str:
    """Inputs name themselves; a long name is cut, never refused."""
    return str(source)[:_SOURCE_MAX]


__all__ = ["Arbiter", "Triggers"]
