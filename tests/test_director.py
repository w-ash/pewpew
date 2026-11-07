"""The idle cycle's director (pewpew.aura.director) and the cycle section
of the looks file: a seeded order, no repeat within the window, a dwell
drawn from its range, weights, every Nth slot a fresh look, rounds and
the end look, and operator input stopping it, all on engine time; a
fresh look made a slot ahead and played from its slot's own frame, or,
not made by then, a look of the cycle in its place and the fresh look at
the next fresh slot."""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from fakes import Painter, aura_rig, restore, rgb, solid
from pewpew.aura.book import CycleConfig, LookBook, LookError, load_looks, parse_looks
from pewpew.aura.director import Director, Slot
from pewpew.aura.variety import at_once
from pewpew.compose import Look
from pewpew.jsonfile import write_atomic

NAMES = ["a", "b", "c", "d"]


def played(director: Director, config: CycleConfig, until: float, step: float = 0.5,
           names: list[str] = NAMES) -> list[tuple[float, Slot]]:
    """Each slot `director` plays from engine time 0 to `until`, with when."""
    out = []
    for t in np.arange(0.0, until, step):
        if (slot := director.tick(float(t), names, config)) is not None:
            out.append((float(t), slot))
    return out


def test_the_same_seed_plays_the_same_slots_at_the_same_times_and_another_seed_does_not():
    config = CycleConfig(idle=10.0, each=(5.0, 20.0), seed=3)
    first, again = played(Director(), config, 600.0), played(Director(), config, 600.0)
    assert first == again and len(first) > 20
    other = played(Director(), CycleConfig(idle=10.0, each=(5.0, 20.0), seed=4), 600.0)
    assert [s for _, s in other] != [s for _, s in first]


def test_no_look_repeats_within_the_window_and_each_dwell_is_within_its_range():
    for window in (1, 2, 3):
        config = CycleConfig(idle=1.0, each=(4.0, 9.0), window=window, seed=window)
        slots = played(Director(), config, 2000.0)
        names = [slot.name for _, slot in slots]
        assert all(names[i] not in names[max(0, i - window):i] for i in range(len(names)))
        gaps = np.diff([t for t, _ in slots])
        assert gaps.min() >= 4.0 and gaps.max() <= 9.0 + 0.5  # within a tick of the drawn dwell
        assert len(set(np.round(gaps, 1))) > 3  # the dwell varies


def test_a_window_past_the_looks_still_plays_and_one_look_plays_alone():
    slots = played(Director(), CycleConfig(idle=1.0, each=2.0, window=9), 100.0, names=["a", "b"])
    assert [s.name for _, s in slots][:6] in (["a", "b"] * 3, ["b", "a"] * 3)
    assert {s.name for _, s in played(Director(), CycleConfig(idle=1.0, each=2.0), 20.0, names=["a"])} == {"a"}


def test_a_heavier_look_plays_more_often():
    config = CycleConfig(idle=1.0, each=1.0, window=0, weights={"a": 6.0})
    counts = Counter(slot.name for _, slot in played(Director(), config, 2000.0))
    assert counts["a"] > 1.5 * max(counts[name] for name in NAMES[1:])


def test_every_fresh_th_slot_is_a_fresh_look_with_a_seed_of_its_own():
    slots = [slot for _, slot in played(Director(), CycleConfig(idle=1.0, each=3.0, fresh=3), 200.0)]
    fresh = [slot for slot in slots if slot.name is None]
    assert all(slot.name is None for slot in slots[2::3]) and len(fresh) == len(slots) // 3
    assert len({slot.seed for slot in fresh}) == len(fresh)
    assert not any(slot.name is None for _, slot in played(Director(), CycleConfig(idle=1.0, each=3.0), 200.0))


def test_after_its_rounds_it_plays_the_end_look_and_stops_until_input():
    director = Director()
    config = CycleConfig(idle=10.0, each=2.0, rounds=2, end="z")
    slots = played(director, config, 60.0)
    assert [slot.name for _, slot in slots][-1] == "z" and len(slots) == 2 * len(NAMES) + 1
    assert not director.running and director.tick(100.0, NAMES, config) is None
    director.touch(100.0)
    assert director.tick(105.0, NAMES, config) is None and director.tick(110.0, NAMES, config) is not None


def test_operator_input_stops_it_and_the_next_run_goes_on_with_the_sequence():
    config = CycleConfig(idle=5.0, each=2.0, seed=1)
    whole = [slot for _, slot in played(Director(), config, 40.0)]
    director = Director()
    first = [slot for _, slot in played(director, config, 9.0)]
    director.touch(9.0)
    assert not director.running and director.tick(13.0, NAMES, config) is None
    rest = [director.tick(14.0, NAMES, config)]
    assert first + rest == whole[: len(first) + 1]


def test_no_idle_or_no_looks_plays_nothing():
    assert played(Director(), CycleConfig(idle=None), 100.0) == []
    assert played(Director(), CycleConfig(idle=1.0), 100.0, names=[]) == []


# ---- the cycle section of the looks file --------------------------------------------------


def looks_text(**cycle) -> str:
    return json.dumps({"version": 4, "looks": {"a": {"layers": [{"id": "base", "nodes": {
        "solid": {"op": "pattern", "args": {"pattern": "solid"}}}}]}}, "cycle": cycle})


def test_the_cycle_section_round_trips_with_a_dwell_range_seed_window_fresh_and_weights(tmp_path):
    config = CycleConfig(idle=60.0, each=(30.0, 90.0), seed=5, window=1, fresh=4, weights={"a": 2.0})
    book = LookBook({"a": solid(1.0, cycle=True)}, cycle=config)
    write_atomic(tmp_path / "looks.json", book.to_bytes())
    again = load_looks(tmp_path / "looks.json")
    assert again.cycle == config and again.cycle.dwell == (30.0, 90.0)
    assert json.loads((tmp_path / "looks.json").read_text())["cycle"]["each"] == [30.0, 90.0]
    assert CycleConfig(each=20.0).dwell == (20.0, 20.0)
    assert book.without("a").cycle.weights == {}


@pytest.mark.parametrize("cycle, message", [
    ({"each": [5, 2]}, "'each' is a number of seconds above 0, or a range [min, max] of them"),
    ({"each": [0, 2]}, "'each' is a number of seconds above 0"),
    ({"seed": -1}, "'seed' is a whole number of at least 0"),
    ({"window": 1.5}, "'window' is a whole number of at least 0"),
    ({"fresh": True}, "'fresh' is a whole number of at least 0"),
    ({"weights": {"zz": 1}}, "'weights' names 'zz', which is not a look"),
    ({"weights": {"a": 0}}, "the weight of 'a' is a number above 0"),
])
def test_a_bad_cycle_section_is_refused_naming_the_problem(cycle, message):
    with pytest.raises(LookError) as err:
        parse_looks(looks_text(**cycle))
    assert message in str(err.value)


# ---- the director through the aura --------------------------------------------------------


def test_the_aura_plays_the_director_s_slots_a_fresh_one_unsaved_and_input_stops_it(tmp_path: Path):
    looks: dict[str, Look] = {
        "red": solid(1.0, fade=0.0, cycle=True), "blue": solid(0.0, 0.0, 1.0, fade=0.0, cycle=True), "skip": solid(0.5),
    }
    rig = aura_rig(looks=looks, path=tmp_path / "looks.json", cycle=CycleConfig(idle=1.0, each=0.5, fresh=3),
                   variety=Painter)
    currents = []
    for k in range(1, 10):
        rig.frame(k * 0.5)
        currents.append(rig.looks.book.current)
    assert rig.looks.state()["cycling"]
    assert "skip" not in currents and {"red", "blue"} <= set(currents)
    assert None in currents[2:]  # the fresh slot: a made look, unsaved
    assert set(rig.looks.book.looks) == set(looks)
    rig.looks.touch()
    assert not rig.looks.state()["cycling"]


def test_unsaved_edits_hold_the_idle_cycle_off_until_they_are_undone(tmp_path: Path):
    looks = {"red": solid(1.0, fade=0.0, cycle=True), "blue": solid(0.0, 0.0, 1.0, fade=0.0, cycle=True)}
    rig = aura_rig(looks=looks, current="red", path=tmp_path / "looks.json", cycle=CycleConfig(idle=1.0, each=0.5))
    assert restore(rig) is None
    rig.renderer().params.set("green", 0.5)
    for k in range(1, 9):
        rig.frame(k * 0.5)
    assert rig.looks.book.current == "red" and rig.looks.changed() and not rig.looks.state()["cycling"]
    rig.renderer().params.set("green", 0.0)  # undone by hand, so the look is as saved
    for k in range(9, 15):
        rig.frame(k * 0.5)
    assert rig.looks.state()["cycling"]


class Held:
    """A `Submit` whose makes are done only when `release` runs them: a make
    slower than any slot."""

    def __init__(self) -> None:
        self.makes = 0
        self.waiting: list[tuple[Callable[[], Any], Future]] = []

    def __call__(self, job: Callable[[], Any]) -> Future:
        self.makes += 1
        future: Future = Future()
        self.waiting.append((job, future))
        return future

    def release(self) -> None:
        for job, future in self.waiting:
            future.set_result(job())
        self.waiting.clear()


LOOKS = {"red": solid(1.0, fade=0.0, cycle=True), "blue": solid(0.0, 0.0, 1.0, fade=0.0, cycle=True)}
# The cycle begins at 1 s; slot 2, fresh, at 1.5 s and slot 4 at 2.5 s.
FRESH = CycleConfig(idle=1.0, each=0.5, fresh=2)
GREEN, RED, BLUE = (rgb(*c, 4).tobytes() for c in ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))


def shown(folder: Path, submit=at_once, *, variety: type = Painter, release_at: float | None = None):
    """Each frame, every 0.25 s from 0.25 to 2.75, of an aura whose idle
    cycle is `FRESH`, its fresh looks made by `variety` through `submit`;
    `release_at` lets a `Held` make finish before the frame at that time.
    Returns the frames and the rig."""
    folder.mkdir()
    rig = aura_rig(looks=LOOKS, path=folder / "looks.json", cycle=FRESH, variety=variety, submit=submit)
    out = []
    for k in range(1, 12):
        if k * 0.25 == release_at:
            submit.release()
        out.append(rig.frame(k * 0.25).tobytes())
    return out, rig


def test_a_fresh_slot_made_a_slot_ahead_plays_from_the_frame_at_its_own_time(tmp_path: Path):
    """Made at once, each fresh look plays from its slot's own frame, and
    the same inputs give the same frames."""
    jobs: list[Callable[[], Any]] = []

    def counted(job):
        jobs.append(job)
        return at_once(job)

    first, _ = shown(tmp_path / "a", counted)
    again, _ = shown(tmp_path / "b")
    assert first == again
    assert first[5] == first[6] == GREEN != first[7] and first[9] == GREEN  # from 1.5 s and 2.5 s, for 0.5 s
    assert len(jobs) == 2  # one make per fresh slot, each named a slot ahead


def test_a_fresh_slot_not_made_by_its_start_plays_a_cycle_look_and_the_next_fresh_slot_plays_it(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
):
    held = Held()
    with caplog.at_level(logging.INFO, logger="pewpew.aura.looks"):
        frames, rig = shown(tmp_path / "held", held, release_at=2.0)
    assert frames[5] in (RED, BLUE)  # 1.5 s: on time, but a look of the cycle
    assert "is not made yet, so this slot plays" in caplog.text
    assert frames[9] == GREEN and held.makes == 1  # 2.5 s: the look owed, not a second make
    director = Director()
    director.tick(1.0, list(LOOKS), FRESH)
    label = f"surprise {director.coming(list(LOOKS), FRESH)}"  # made for the cycle's second slot
    assert rig.looks.state()["made"] == label
    assert rig.looks.save() is None and rig.looks.book.current == label and rig.looks.state()["made"] is None
    again, _ = shown(tmp_path / "again", Held(), release_at=2.0)
    assert again == frames  # the same outcome of each make gives the same frames


def test_a_make_that_fails_plays_a_cycle_look_and_the_next_fresh_slot_makes_its_own(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
):
    seeds: list[int | None] = []

    class Failing(Painter):
        def surprise(self, seed=None):
            seeds.append(seed)
            self.fail = len(seeds) == 1
            return super().surprise(seed)

    folder = tmp_path / "f"
    folder.mkdir()
    rig = aura_rig(looks=LOOKS, path=folder / "looks.json", cycle=FRESH, variety=Failing)
    frames, errors = [], []
    for k in range(1, 12):
        frames.append(rig.frame(k * 0.25).tobytes())
        errors.append(rig.looks.error)
    assert frames[5] in (RED, BLUE) and frames[9] == GREEN
    failed = "cannot make a fresh look: NoLook: nothing made from seed 9"
    assert failed in caplog.text
    assert errors[5].startswith(failed) and errors[4] is None  # on the status line from the slot that failed
    assert len(seeds) == 2 and seeds[0] != seeds[1]


def test_a_fresh_slot_played_instead_owes_its_seed_to_the_next_fresh_slot():
    config = CycleConfig(idle=1.0, each=1.0, fresh=2, window=1)
    director = Director()
    first = director.tick(1.0, NAMES, config)
    fresh = director.tick(2.0, NAMES, config)
    assert first is not None and fresh is not None and fresh.name is None
    instead = director.instead()
    assert instead.name in NAMES and instead.name != first.name  # drawn for its slot, outside the window
    assert director.tick(3.0, NAMES, config) is not None and director.coming(NAMES, config) == fresh.seed
    assert director.tick(4.0, NAMES, config) == fresh  # the owed look, at its slot's time
    twin = Director()
    for t in (1.0, 2.0):
        twin.tick(t, NAMES, config)
    assert twin.instead() == instead  # the same draws for the same slots
    dropped = director.instead(owe=False)
    assert dropped.name in NAMES
    director.tick(5.0, NAMES, config)
    assert director.coming(NAMES, config) not in (None, fresh.seed)
