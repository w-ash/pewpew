"""Room-event triggers: arbitration, the queue and its tick stamp, the
features exposure, the look override and its return, the JSONL log and its
replay, the looks file's triggers section, and the page's messages."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator, Sequence

import numpy as np
import pytest

import pewpew.run as run_module
from fakes import (
    FakeTime,
    aura_rig,
    layered,
    look,
    looks_file,
    next_of,
    program_of,
    restore,
    run_main,
    serving,
    solid,
    wait_until,
)
from pewpew.aura.book import VERSION, CycleConfig, LookBook, LookError, Trigger, parse_looks
from pewpew.aura.triggers import MAX_QUEUE, Arbiter, Triggers
from pewpew.aura.variety import Made
from pewpew.compose import Layer, Look
from pewpew.features import EventFeatures, FakeFeatures
from pewpew.fx.host import ProgramPattern
from pewpew.fx.op import REGISTRY, BindCtx, FrameCtx, Op
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.jsonfile import read_run
from pewpew.mapping import line
from pewpew.pace import PacedLoop
from pewpew.pattern import Pattern
from pewpew.render import Renderer, SlotClock

pytestmark = pytest.mark.usefixtures("fake_ops")


class Counter(Pattern):
    """Red steps up by 0.1 for every room event the pattern sees."""

    def setup(self, n, x, y, z, index):
        self.seen = 0
        self.log: list = []

    def before_render(self, dt, features):
        self.log.append(features.events)
        self.seen += len(features.events)

    def render(self, x, y, z, index):
        out = np.zeros((self.n, 3), dtype=np.float32)
        out[:, 0] = min(1.0, 0.1 * self.seen)
        return out


@pytest.fixture
def counter_op() -> Iterator[None]:
    """`counter_test` in the op registry for this test: Counter as an op,
    so a look can run it."""
    before = dict(REGISTRY)

    class CounterTest(Op, op="counter_test"):
        """Red steps up by 0.1 for every room event the program sees."""

        sig = Sig.SOURCE
        out = Ty.RGB
        stateful = True

        def setup(self, ctx: BindCtx) -> None:
            super().setup(ctx)
            self.seen = ctx.buffer("seen", 1)

        def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
            self.seen += len(ctx.features.events)

        def build(self, inputs: Sequence[Fn]) -> Fn:
            def counter(c: Coords) -> np.ndarray:
                out = np.zeros((len(c.index), 3), dtype=np.float32)
                out[:, 0] = min(1.0, 0.1 * float(self.seen[0]))
                return out

            return counter

    try:
        yield
    finally:
        REGISTRY.clear()
        REGISTRY.update(before)


BLUE, RED, GREEN = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)


# ---- arbitration ---------------------------------------------------------------

CUE = Trigger(look=None, priority="button", debounce=0.05, cooldown=1.0)
HOLDS = Trigger(look="red", priority="button", debounce=0.0, cooldown=0.0)
QUICK = Trigger(look=None, debounce=0.0, cooldown=0.0)


@pytest.mark.parametrize("trigger, arrivals, expect", [
    # (t, source, value[, held rank]) per arrival; the reason each gets.
    (CUE, [(0.0, "a", None)], [None]),
    (None, [(0.0, "a", None)], ["unknown"]),
    (CUE, [(0.0, "a", None), (0.03, "a", None)], [None, "debounce"]),
    # Chatter counts from the last arrival, so it stays dropped.
    (CUE, [(0.0, "a", None), (0.04, "a", None), (0.08, "a", None), (2.0, "a", None)],
     [None, "debounce", "debounce", None]),
    (CUE, [(0.0, "a", None), (0.5, "a", None), (1.0, "a", None)], [None, "cooldown", None]),
    # Cooldown is per source.
    (CUE, [(0.0, "a", None), (0.5, "b", None)], [None, None]),
    # Levels fire on the rise only.
    (CUE, [(0.0, "a", 1.0), (2.0, "a", 1.0), (4.0, "a", 0.0), (6.0, "a", 0.5)], [None, "edge", "edge", None]),
    (CUE, [(0.0, "a", 0.0), (2.0, "a", -1.0)], ["edge", "edge"]),
    # A rise during the cooldown is spent: the level is high when it ends.
    (CUE, [(0.0, "a", 1.0), (0.2, "a", 0.0), (0.4, "a", 1.0), (2.0, "a", 1.0)], [None, "edge", "cooldown", "edge"]),
    # A fall inside the debounce still lowers the level, so the next rise fires.
    (CUE, [(0.0, "a", 1.0), (0.02, "a", 0.0), (10.0, "a", 1.0)], [None, "debounce", None]),
    # A higher class's hold outranks a look; an equal one is replaced.
    (HOLDS, [(0.0, "a", None, 3)], ["outranked"]),
    (HOLDS, [(0.0, "a", None, 1)], [None]),
    (HOLDS, [(0.0, "a", None, 0)], [None]),
    (CUE, [(0.0, "a", None, 3)], [None]),  # no look: nothing to outrank
])
def test_arbitration(trigger, arrivals, expect):
    arbiter = Arbiter()
    got = [arbiter.judge(a[1], "cue", a[2], trigger, a[0], a[3] if len(a) > 3 else None) for a in arrivals]
    assert got == expect


def test_the_rate_limit_is_global_and_slides_on_engine_time():
    arbiter = Arbiter(rate_max=3, rate_window=1.0)
    got = [arbiter.judge(src, "cue", None, QUICK, t) for t, src in
           [(0.0, "a"), (0.1, "b"), (0.2, "c"), (0.3, "d"), (1.0, "e"), (1.05, "f")]]
    assert got == [None, None, None, "rate", None, "rate"]


def test_operator_events_skip_the_rate_limit_and_do_not_fill_it():
    arbiter = Arbiter(rate_max=2, rate_window=1.0)
    boss = Trigger(priority="operator", debounce=0.0, cooldown=0.0)
    got = [arbiter.judge(src, name, None, trig, t) for t, src, name, trig in [
        (0.0, "a", "cue", QUICK), (0.1, "op", "boss", boss), (0.2, "op2", "boss", boss),
        (0.3, "b", "cue", QUICK), (0.4, "c", "cue", QUICK), (0.5, "op3", "boss", boss),
    ]]
    assert got == [None, None, None, None, "rate", None]


# ---- the queue ----------------------------------------------------------------


def test_disarmed_events_are_dropped_and_logged_and_arming_is_stamped_in_order():
    log = io.StringIO()
    features = EventFeatures(FakeFeatures(0))
    trig = Triggers({"cue": QUICK}, features=features, log=log)
    trig.submit("page", "cue")
    trig.before_frame(0.5)
    assert features.at(0.5).events == ()
    trig.submit("page", "cue")  # judged before the arm queued after it
    trig.arm(True)
    trig.submit("page", "cue")
    trig.before_frame(1.0)
    records = [json.loads(line) for line in log.getvalue().splitlines()]
    assert [(r["tick"], r["t"], r.get("arm"), r.get("reason")) for r in records] == [
        (0, 0.5, None, "disarmed"),
        (1, 1.0, None, "disarmed"),
        (1, 1.0, True, None),
        (1, 1.0, None, None),
    ]
    assert [e.name for e in features.at(1.0).events] == ["cue"]
    assert trig.last == {"name": "cue", "fired": True, "reason": None, "error": None}


def test_one_tick_judges_the_highest_class_first():
    features = EventFeatures(FakeFeatures(0))
    trig = Triggers({
        "door": Trigger(priority="sensor", debounce=0.05, cooldown=0.0),
        "cue": Trigger(priority="performer", debounce=0.0, cooldown=0.0),
    }, features=features)
    trig.arm(True)
    trig.before_frame(0.1)
    for name in ("door", "cue", "door"):
        trig.submit("x", name)
    trig.before_frame(0.2)
    events = features.at(0.2).events
    assert [(e.name, e.priority, e.tick) for e in events] == [("cue", "performer", 1), ("door", "sensor", 1)]
    assert trig.last["reason"] == "debounce"  # the second door, judged last


@pytest.mark.parametrize("name, value, reason", [
    (7, None, "a trigger name is text, got 7"),
    ("../looks.json", None, "bad trigger name '../looks.json'"),
    ("cue", "loud", "a trigger value is a finite number or null, got 'loud'"),
    ("cue", float("inf"), "a trigger value is a finite number or null"),
    ("cue", True, "a trigger value is a finite number or null, got True"),
])
def test_a_malformed_event_is_refused_and_never_queued(name, value, reason):
    trig = Triggers({"cue": QUICK}, features=EventFeatures(FakeFeatures(0)))
    assert trig.submit("page", name, value).startswith(reason)
    assert trig.arm("yes") == "arm takes true or false, got 'yes'"
    trig.before_frame(0.1)
    assert trig.last is None


def test_a_full_queue_refuses_more():
    trig = Triggers({"cue": QUICK}, features=EventFeatures(FakeFeatures(0)))
    for _ in range(MAX_QUEUE):
        assert trig.submit("x", "cue") is None
    assert trig.submit("x", "cue") is not None
    trig.before_frame(0.1)
    assert trig.submit("x", "cue") is None


# ---- features ------------------------------------------------------------------


def test_a_pattern_sees_each_fired_event_on_one_frame_only():
    features = EventFeatures(FakeFeatures(0))
    trig = Triggers({"cue": QUICK, "door": Trigger(priority="sensor", debounce=0.0, cooldown=0.0)}, features=features)
    pattern = Counter()
    renderer = Renderer(pattern, line(4), features=features)
    clock = SlotClock(60.0)

    def frame() -> None:
        t = clock.advance()
        trig.before_frame(t)
        renderer.advance_to(t)

    trig.arm(True)
    frame()
    trig.submit("page", "cue")
    trig.submit("hall", "door", 1.0)
    trig.submit("page", "nosuch")
    frame()
    frame()
    assert [len(e) for e in pattern.log] == [0, 2, 0]
    cue, door = pattern.log[1]
    assert (cue.name, cue.source, cue.value, cue.priority, cue.tick) == ("cue", "page", None, "button", 1)
    assert cue.t == SlotClock(60.0).advance(2)  # the engine time of the frame it fired on
    assert (door.name, door.value, door.priority) == ("door", 1.0, "sensor")
    assert trig.last["reason"] == "unknown"
    # The fake source never carries events, so goldens are untouched.
    assert FakeFeatures(0).at(1.0).events == ()


# ---- the override ----------------------------------------------------------------


def make(tmp_path, triggers, looks=None, current="blue", log=None, mapping=None, armed=True):
    looks = looks if looks is not None else {
        "blue": solid(*BLUE, fade=0.0), "red": solid(*RED, fade=0.0, master=1.0), "green": solid(*GREEN, fade=0.0),
    }
    r = aura_rig(mapping=mapping, looks=looks, current=current, cycle=CycleConfig(idle=None), triggers=triggers,
                 path=tmp_path / "looks.json", log=log, timeout=2.0)
    r.trig = r.triggers
    assert restore(r) is None
    if armed:
        r.trig.arm(True)

    def step(n=1):
        for _ in range(n):
            out = r.frame(r.clock.advance())
        return tuple(float(v) for v in out[0])

    r.step = step
    return r


HOLD_RED = {"cue": Trigger(look="red", hold=0.5, debounce=0.0, cooldown=0.0)}


def test_a_held_look_returns_to_the_live_state_after_its_hold(tmp_path):
    r = make(tmp_path, HOLD_RED)
    assert r.step() == BLUE
    saved = r.path.read_bytes()
    pattern = r.renderer().pattern
    assert isinstance(pattern, ProgramPattern)
    pattern.node_params["solid"].set("green", 0.5)  # an unsaved tweak: the journal keeps it
    r.master.set(0.4)
    r.trig.submit("page", "cue")
    assert r.step() == RED
    held = r.looks.held
    assert (held.trigger, held.look) == ("cue", "red") and held.until == pytest.approx(r.fader.t + 0.5)
    assert r.master.level == 0.4  # the override leaves the master alone
    assert r.looks.state()["changed"] is False  # a hold is not an edit
    assert r.looks.book.current == "blue" and r.path.read_bytes() == saved  # journalled, not saved
    assert r.step(28) == RED
    assert r.step(2) == (0.0, 0.5, 1.0)
    assert r.looks.held is None and r.looks.state()["changed"] is True


def test_a_retrigger_extends_the_hold_and_keeps_the_journal(tmp_path):
    triggers = {**HOLD_RED, "go": Trigger(look="green", hold=0.5, debounce=0.0, cooldown=0.0)}
    r = make(tmp_path, triggers)
    r.step()
    r.trig.submit("page", "cue")
    assert r.step(20) == RED
    r.trig.submit("page", "go")
    assert r.step(25) == GREEN  # past the first hold's end
    assert r.step(6) == BLUE  # back to where the first hold began


def test_an_operator_recall_during_a_hold_cancels_the_return(tmp_path):
    r = make(tmp_path, HOLD_RED)
    r.step()
    r.trig.submit("page", "cue")
    assert r.step() == RED
    assert r.looks.recall("green") is None
    assert r.looks.held is None
    assert r.step(60) == GREEN
    assert r.looks.book.current == "green"


def test_keep_during_a_hold_is_refused_and_keeps_the_made_look_once_the_aura_returns(tmp_path):
    r = make(tmp_path, HOLD_RED)
    r.step()
    assert r.looks.play(Made(solid(*GREEN, fade=0.0), "surprise 7")) is None
    assert r.step() == GREEN
    r.trig.submit("page", "cue")
    assert r.step() == RED
    saved = r.path.read_bytes()
    assert r.looks.save() == "cue is playing red: save when it ends"
    assert r.looks.held is not None and r.path.read_bytes() == saved
    assert r.step(30 + 125) == GREEN  # the hold ran out: back to the made look, over the default fade
    assert r.looks.save() is None and r.looks.book.current == "surprise 7"
    assert r.looks.recall("blue", 0.0) is None and r.step() == BLUE
    assert r.looks.recall("surprise 7", 0.0) is None and r.step() == GREEN  # kept as it played, not as held


def test_a_lower_class_cannot_replace_a_higher_hold(tmp_path):
    triggers = {
        "boss": Trigger(look="green", hold=1.0, priority="performer", debounce=0.0, cooldown=0.0),
        "cue": Trigger(look="red", hold=1.0, priority="sensor", debounce=0.0, cooldown=0.0),
    }
    r = make(tmp_path, triggers)
    r.step()
    r.trig.submit("x", "boss")
    r.step()
    r.trig.submit("x", "cue")
    assert r.step() == GREEN
    assert r.trig.last == {"name": "cue", "fired": False, "reason": "outranked", "error": None}


def test_a_hold_during_a_fade_waits_for_it(tmp_path):
    looks = {"blue": solid(*BLUE, fade=0.0), "red": solid(*RED, fade=0.0), "green": solid(*GREEN, fade=1.0)}
    r = make(tmp_path, HOLD_RED, looks=looks)
    r.step()
    assert r.looks.recall("green") is None
    r.step(10)
    r.trig.submit("page", "cue")
    r.step()
    assert r.looks.state()["pending"] == "red" and r.fader.fading
    assert r.step(55) == RED  # the fade ended at 1 s, then the hold began
    assert r.looks.held.until == pytest.approx(r.fader.t + 0.5, abs=0.1)
    assert r.step(90) == GREEN  # back over green's own 1 s fade


def test_a_held_look_that_fails_after_a_fade_leaves_the_live_look_running(tmp_path):
    """The look the hold would return to is the one that faded in, so it
    runs on: no fresh renderer, no fade from it to itself."""
    looks = {"blue": solid(*BLUE, fade=0.0), "broken": look("gone", fade=0.0), "green": solid(*GREEN, fade=0.5)}
    triggers = {"cue": Trigger(look="broken", hold=60.0, debounce=0.0, cooldown=0.0)}
    r = make(tmp_path, triggers, looks=looks)
    r.step()
    r.looks.recall("green")
    r.step()
    green = r.fader.current
    r.trig.submit("page", "cue")  # waits for green's fade; its op is unknown
    r.step(40)
    assert r.looks.held is None and r.looks.error.startswith("cannot recall 'broken'")
    assert r.step(40) == GREEN
    assert r.fader.current is green and not r.fader.fading


def test_a_hold_that_fails_keeps_the_operator_recall_it_queued_behind(tmp_path):
    looks = {"blue": solid(*BLUE, fade=0.0), "broken": look("gone", fade=0.0),
             "green": solid(*GREEN, fade=0.5), "red": solid(*RED, fade=0.0)}
    triggers = {"cue": Trigger(look="broken", hold=1.0, debounce=0.0, cooldown=0.0)}
    r = make(tmp_path, triggers, looks=looks)
    r.step()
    r.looks.recall("green")
    r.step(5)
    r.looks.recall("red")  # waits for green's fade
    while r.fader.fading:
        r.step()
    # The fade is over and red still waits: the event is judged first.
    assert r.looks.state()["pending"] == "red"
    r.trig.submit("page", "cue")
    assert r.step() == RED
    assert r.trig.last["fired"] is True and r.looks.held is None
    # The page says why the look did not hold.
    assert r.trig.last["error"].startswith("cannot recall 'broken': ")


def test_a_second_trigger_during_a_queued_return_returns_to_the_first_journal(tmp_path):
    # red's 1 s fade outlasts its 0.3 s hold, so its return waits for the fade.
    looks = {"blue": solid(*BLUE, fade=0.0), "red": solid(*RED, fade=1.0), "green": solid(*GREEN, fade=0.0)}
    triggers = {"cue": Trigger(look="red", hold=0.3, debounce=0.0, cooldown=0.0),
                "go": Trigger(look="green", hold=0.3, debounce=0.0, cooldown=0.0)}
    r = make(tmp_path, triggers, looks=looks)
    r.step()
    r.trig.submit("page", "cue")
    r.step(30)
    assert r.looks.held is None and r.fader.fading  # the return waits
    r.trig.submit("page", "go")
    r.step(200)
    assert r.step() == BLUE


def test_a_hold_on_the_tick_a_fade_ends_drops_the_older_queued_hold(tmp_path):
    looks = {"blue": solid(*BLUE, fade=0.0), "red": solid(*RED, fade=0.0), "green": solid(*GREEN, fade=0.0),
             "slow": solid(0.5, 0.5, 0.5, fade=0.5)}
    triggers = {"cue": Trigger(look="red", hold=5.0, debounce=0.0, cooldown=0.0),
                "go": Trigger(look="green", hold=5.0, debounce=0.0, cooldown=0.0)}
    r = make(tmp_path, triggers, looks=looks)
    r.step()
    r.looks.recall("slow")
    r.step(3)
    r.trig.submit("page", "cue")  # queued behind slow's fade
    while r.fader.fading:
        r.step()
    assert r.looks.state()["pending"] == "red"  # the fade is over; red starts next tick
    r.trig.submit("page", "go")  # judged on that tick, before red starts
    assert r.step(10) == GREEN
    assert r.looks.held.look == "green"


def test_deleting_the_look_a_hold_returns_to_falls_back_to_the_live_state(tmp_path):
    looks = {"blue": solid(*BLUE, fade=0.0), "red": solid(*RED, fade=0.0),
             "green": solid(*GREEN, fade=0.0), "slow": solid(0.5, 0.5, 0.5, fade=0.5)}
    r = make(tmp_path, {"cue": Trigger(look="red", hold=0.2, debounce=0.0, cooldown=0.0)}, looks=looks)
    r.step()
    r.looks.recall("slow")
    r.step(2)
    r.looks.recall("green")  # queued behind slow's fade
    r.trig.submit("page", "cue")  # the hold returns to the queued green
    r.step()
    assert r.looks.delete("green") is None
    r.step(80)
    assert r.looks.held is None and r.looks.error is None
    assert r.step() == (0.5, 0.5, 0.5)  # slow, the live state when the hold began


def test_firing_the_held_look_again_extends_the_hold_without_restarting_it(tmp_path):
    r = make(tmp_path, HOLD_RED)
    r.step()
    r.trig.submit("page", "cue")
    r.step(10)
    renderer, journal = r.fader.current, r.looks.held.journal
    r.trig.submit("page", "cue")
    r.step()
    assert r.fader.current is renderer and not r.fader.fading  # the same look runs on
    held = r.looks.held
    assert held.journal is journal and held.until == pytest.approx(r.fader.t + 0.5)
    assert r.step(28) == RED  # past the first hold's end
    assert r.step(3) == BLUE


def test_deleting_a_look_a_trigger_holds_is_refused(tmp_path):
    r = make(tmp_path, HOLD_RED)
    assert r.looks.delete("red").startswith("look 'red' is held by trigger cue")
    assert r.looks.delete("green") is None


# ---- the log and its replay ----------------------------------------------------------


def log_rig(tmp_path, **kw):
    """Counter, whose frames show how many events it saw, and a cue that
    holds a red look for 0.25 s."""
    triggers = {
        "cue": Trigger(look="red", hold=0.25, debounce=0.0, cooldown=0.5),
        "door": Trigger(priority="sensor", debounce=0.1, cooldown=0.0),
    }
    looks = {"count": look("counter_test", fade=0.0), "red": solid(*RED, fade=0.1)}
    return make(tmp_path, triggers, looks=looks, current="count", **kw)


def live(tmp_path, log_path):
    """The log rig through PacedLoop on fake time, with events submitted
    between runs, as another thread would."""
    with open(log_path, "w", encoding="utf-8") as log:
        r = log_rig(tmp_path, log=log)
        ft = FakeTime()
        out: list[bytes] = []
        loop = PacedLoop(r.fader, fps=60.0, before=[r.trig.before_frame, r.looks.before_frame],
                         after=[r.master.apply], on_frame=[lambda t, f: out.append(f.tobytes())],
                         now=ft.now, sleep=ft.sleep)
        plan = [(5, [("hall", "door", 1.0)]), (3, [("hall", "door", 0.0), ("hall", "door", 1.0)]),
                (10, [("page", "cue", None), ("hall", "door", 0.0)]), (4, [("page", "cue", None)]),
                (30, [("hall", "door", 1.0), ("page", "nosuch", None)]), (40, [])]
        for frames, events in plan:
            loop.run(frames=frames)
            for source, name, value in events:
                r.trig.submit(source, name, value)
        r.trig.arm(False)
        r.trig.submit("page", "cue")
        loop.run(frames=5)
    return out


def replay(tmp_path, records):
    """The records fed back before the frame of their `t`, rendered at
    every slot with no loop."""
    by_t: dict[float, list] = {}
    for record in records:
        by_t.setdefault(record["t"], []).append(record)
    r = log_rig(tmp_path, armed=False)  # the log's own arm record arms it
    out = []
    clock = SlotClock(60.0)
    for _ in range(97):
        t = clock.advance()
        for record in by_t.get(t, ()):
            r.trig.feed(record)
        out.append(r.master.apply(t, r.frame(t)).tobytes())
    return out


# What `live` submits, as judged: the arm make() queued; a door rise; a fall
# and a rise inside the door's debounce; a cue, then a door fall (judged
# after the cue, a lower class); a cue inside its cooldown; a door rise and
# an unknown name; the disarm, then a cue while disarmed.
REASONS = ["arm", None, "debounce", "debounce", None, "edge", "cooldown", None, "unknown", "arm", "disarmed"]


@pytest.mark.usefixtures("counter_op")
def test_a_recorded_log_replays_to_byte_identical_frames(tmp_path):
    (tmp_path / "live").mkdir()
    (tmp_path / "replay").mkdir()
    log_path = tmp_path / "triggers.jsonl"
    frames = live(tmp_path / "live", log_path)
    records = read_run(log_path)
    reasons = [r.get("reason", "arm") for r in records]
    assert reasons == REASONS
    assert all(isinstance(r["tick"], int) for r in records)
    replayed = replay(tmp_path / "replay", records)
    assert len(frames) == len(replayed) == 97
    assert frames == replayed
    assert len(set(frames)) > 3  # events and the hold changed what was shown


def test_a_log_spanning_restarts_reads_one_run_by_its_header(tmp_path):
    path = tmp_path / "triggers.jsonl"
    for seed in (1, 2):
        with open(path, "a", encoding="utf-8") as log:
            trig = Triggers({"cue": QUICK}, log=log, features=EventFeatures(FakeFeatures(0)))
            trig.begin_run(seed=seed)
            trig.arm(True)
            trig.submit("page", "cue")
            trig.before_frame(0.5)
    first, last = read_run(path, 0), read_run(path)
    assert first[0] == {"run": {"seed": 1}} and last[0] == {"run": {"seed": 2}}
    assert [r["tick"] for r in last[1:]] == [0, 0]  # each run counts its own ticks
    with pytest.raises(IndexError):
        read_run(path, 2)
    features = EventFeatures(FakeFeatures(0))
    replayed = Triggers({"cue": QUICK}, features=features)
    for record in last:
        replayed.feed(record)  # the header is skipped
    replayed.before_frame(0.5)
    assert [e.name for e in features.at(0.5).events] == ["cue"]


def test_the_log_stops_at_its_byte_cap_with_one_warning(tmp_path, caplog):
    path = tmp_path / "triggers.jsonl"
    path.write_text("x" * 100 + "\n")  # what an earlier run left counts too
    with open(path, "a", encoding="utf-8") as log:
        trig = Triggers({"cue": QUICK}, log=log, log_max=400, features=EventFeatures(FakeFeatures(0)))
        trig.arm(True)
        for tick in range(10):
            trig.submit("page", "cue")
            trig.before_frame(float(tick))
    assert 101 < path.stat().st_size <= 400
    assert caplog.text.count("reached its cap of 400 bytes") == 1


# ---- the looks file --------------------------------------------------------------------


def test_the_triggers_section_round_trips_with_defaults_filled_in():
    text = json.dumps({
        "version": VERSION,
        "looks": {"a": layered("solid_test"), "b": layered("ramp_test")},
        "triggers": {"cue1": {"look": "a", "hold": 8, "priority": "performer"}, "door": {}},
    })
    book = parse_looks(text)
    assert book.triggers == {"cue1": Trigger("a", 8.0, "performer"), "door": Trigger()}
    again = parse_looks(book.to_bytes())
    assert again == book
    assert json.loads(book.to_bytes())["triggers"]["door"] == {
        "look": None, "hold": 10.0, "priority": "button", "debounce": 0.05, "cooldown": 1.0,
    }
    assert "triggers" not in json.loads(LookBook().to_bytes())


@pytest.mark.parametrize("triggers, message", [
    ([], "'triggers' is an object of name: trigger"),
    ({"../x": {}}, "bad trigger name '../x'"),
    ({"cue": []}, "trigger 'cue' is an object"),
    ({"cue": {"when": 1}}, "trigger 'cue': unknown key 'when'"),
    ({"cue": {"look": "nosuch"}}, "trigger 'cue': 'look' names 'nosuch', which is not a look"),
    ({"cue": {"look": ["a"]}}, "trigger 'cue': 'look' names ['a'], which is not a look"),
    ({"cue": {"hold": 0}}, "trigger 'cue': 'hold' is a number of seconds above 0"),
    ({"cue": {"priority": "vip"}}, "trigger 'cue': 'priority' is one of sensor, button, performer, operator"),
    ({"cue": {"cooldown": -1}}, "trigger 'cue': 'cooldown' is a number of seconds from 0"),
])
def test_a_bad_triggers_section_is_refused(triggers, message):
    with pytest.raises(LookError) as err:
        parse_looks(json.dumps({"version": VERSION, "looks": {"a": layered("solid_test")}, "triggers": triggers}))
    assert any(p.startswith(message) for p in err.value.problems), err.value.problems


def test_a_saved_look_rewrites_the_file_with_its_triggers(tmp_path):
    r = make(tmp_path, HOLD_RED)
    assert r.looks.save("new") is None
    assert parse_looks(r.path.read_bytes()).triggers == HOLD_RED


def test_the_runner_writes_the_trigger_log_and_starts_disarmed(tmp_path):
    looks = tmp_path / "looks.json"
    doc = {"version": VERSION, "looks": {"a": layered("osc"), "b": layered("ramp_test")},
           "triggers": {"cue": {"look": "b"}}}
    looks.write_text(json.dumps(doc))
    log = tmp_path / "events.jsonl"
    run_main(["run", str(looks), "--map", "line:8", "--trigger-log", str(log), "--frames", "2"])
    assert read_run(log) == [{"run": {"seed": 0, "fps": 60.0, "look": "a", "armed": False}}]
    with pytest.raises(SystemExit, match="cannot open the trigger log for appending"):
        run_main(["run", looks_file(), "--map", "line:8", "--trigger-log", str(tmp_path / "no" / "x.jsonl"),
                  "--frames", "1"])


def test_a_dry_run_refuses_a_trigger_log_the_launch_cannot_open(tmp_path, audit_log):
    base = ["run", looks_file(), "--map", "line:8", "--ddp", "10.0.0.11=0+8", "--dry-run", "--trigger-log"]
    (tmp_path / "file").write_text("")
    cases = ((tmp_path / "no" / "x.jsonl", "No such file or directory"), (tmp_path, "Is a directory"),
             (tmp_path / "file" / "x.jsonl", "Not a directory"))
    for path, reason in cases:
        with pytest.raises(SystemExit, match=f"cannot open the trigger log for appending: {reason}$"):
            run_main([*base, str(path)])
    assert run_main([*base, str(tmp_path / "x.jsonl")])[0] == 0
    assert not (tmp_path / "x.jsonl").exists()


def test_a_refused_launch_creates_no_trigger_log(tmp_path, capsys):
    log = tmp_path / "events.jsonl"
    folded = Look((Layer("base", program_of("osc(8).kaleid(5)")),))  # a fold, which a strip cannot run
    with pytest.raises(SystemExit, match="cannot start look 'nope'"):
        run_main(["run", looks_file(folded, "nope"), "--map", "line:8", "--trigger-log", str(log), "--frames", "1"])
    with pytest.raises(SystemExit) as exc:
        run_main(["run", looks_file(), "--map", "line:8", "--trigger-log", str(log), "--trigger-log-max", "0"])
    assert exc.value.code == 2 and "argument --trigger-log-max: expected megabytes above 0" in capsys.readouterr().err
    assert not log.exists()


def test_a_trigger_log_that_fails_to_close_still_tears_the_aura_down(tmp_path, monkeypatch):
    class FailingClose(io.StringIO):
        def close(self):
            super().close()  # closed, so garbage collection does not raise it again
            raise OSError(28, "No space left on device")

    torn: list = []
    teardown = run_module.teardown
    monkeypatch.setattr(run_module, "open_log", lambda path, noun: FailingClose())
    monkeypatch.setattr(run_module, "teardown", lambda *a: (torn.append(True), teardown(*a)))
    argv = ["run", looks_file(), "--map", "line:8", "--trigger-log", str(tmp_path / "x"), "--frames", "1"]
    assert run_main(argv)[0] == 0
    assert torn == [True]


# ---- the socket ------------------------------------------------------------------------


@pytest.fixture
def served(tmp_path):
    r = make(tmp_path, HOLD_RED, armed=False)  # disarmed, as every launch starts
    with serving(r.control, r.calls) as (sink, ws, greeting):
        yield r, sink, ws, greeting


def tick(r, sink):
    """Run one engine tick once the socket's request is queued, then push
    the state as the next frame would."""
    wait_until(lambda: len(r.trig._queue) > 0)
    r.step()
    sink.send(r.fader.t, np.zeros((4, 3), np.float32))


def test_a_new_client_gets_the_triggers_disarmed(served):
    _, _, _, greeting = served
    assert greeting["aura"]["triggers"] == {
        "armed": False, "names": ["cue"], "cues": {"cue": {"look": "red", "hold": 0.5}}, "held": None, "last": None,
    }


def test_arm_and_fire_over_the_socket_echo_the_outcome(served):
    r, sink, ws, _ = served
    ws.send(json.dumps({"type": "fire", "name": "cue"}))
    tick(r, sink)
    echo = next_of(ws, "aura")
    assert echo["triggers"]["last"] == {"name": "cue", "fired": False, "reason": "disarmed", "error": None}
    ws.send(json.dumps({"type": "arm", "on": True}))
    tick(r, sink)
    assert next_of(ws, "aura")["triggers"]["armed"] is True
    ws.send(json.dumps({"type": "fire", "name": "cue", "value": None}))
    tick(r, sink)
    state = next_of(ws, "aura")["triggers"]
    assert state["last"]["fired"] is True
    assert state["held"] == {"trigger": "cue", "look": "red", "until": pytest.approx(r.fader.t + 0.5)}
