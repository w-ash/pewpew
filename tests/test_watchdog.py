"""pewpew.watchdog and pewpew.awake: the stall exit and the sleep assertion."""

from __future__ import annotations

import json
import threading

import numpy as np
import pytest

from fakes import FakeProcess, FakeTime
from pewpew import watchdog as watchdog_module
from pewpew.awake import KeepAwake
from pewpew.mapping import line
from pewpew.pace import PacedLoop
from pewpew.pattern import Pattern
from pewpew.render import Renderer
from pewpew.watchdog import EXIT_STALL, MARKER_FRESH_S, Stall, Watchdog, marker_path, take_marker


def armed(ft: FakeTime) -> Watchdog:
    """A started 5 s watchdog on `ft` whose thread checks once an hour, so
    only the test's own `check` calls count."""
    dog = Watchdog(5.0, interval=3600.0, now=ft.now)
    dog.start()
    return dog


def test_no_check_fires_before_start():
    ft = FakeTime()
    dog = Watchdog(5.0, now=ft.now)
    ft.t = 100.0
    assert dog.check() is None


def test_the_startup_allowance_defaults_to_three_timeouts_and_at_least_15_s():
    assert Watchdog(2.0).startup == 15.0
    assert Watchdog(10.0).startup == 30.0
    assert Watchdog(2.0, startup=4.0).startup == 4.0
    with pytest.raises(ValueError, match="startup"):
        Watchdog(2.0, startup=0.0)


def test_a_first_frame_that_never_comes_fires_after_the_startup_allowance():
    ft = FakeTime(50.0)
    dog = armed(ft)
    try:
        ft.t = 64.9  # a normal start: restore, sinks, preview, first render
        assert dog.check() is None
        ft.t = 65.0
        assert dog.check() == pytest.approx(15.0)
    finally:
        dog.stop()


def test_a_first_frame_inside_the_allowance_then_a_stall_fires_on_the_timeout():
    ft = FakeTime()
    dog = armed(ft)
    try:
        ft.t = 12.0
        dog.beat()
        ft.t = 16.9
        assert dog.check() is None
        ft.t = 17.0  # under the startup allowance, past the timeout after the first beat
        assert dog.check() == pytest.approx(5.0)
    finally:
        dog.stop()


def test_a_hitch_under_the_timeout_does_not_fire_and_a_stall_does():
    ft = FakeTime()
    dog = Watchdog(5.0, now=ft.now)
    dog.beat()
    ft.t = 4.9  # a hot reload or a room reload between two frames
    assert dog.check() is None
    dog.beat()
    ft.t = 9.8
    assert dog.check() is None
    ft.t = 9.9
    assert dog.check() == pytest.approx(5.0)


def test_the_default_stall_action_marks_says_and_exits_with_70(monkeypatch, capfd, tmp_path):
    codes: list[int] = []
    monkeypatch.setattr(watchdog_module, "_exit", codes.append)
    marker = tmp_path / "state" / "stalled"
    Watchdog(1.0, marker=marker)._fire(1.2)
    assert codes == [EXIT_STALL] == [70]
    assert json.loads(marker.read_text()) == {"stalled": 1.2, "looks": []}
    # Straight to the process's stderr: a deferring log handler would lose it at os._exit.
    assert "CRITICAL pewpew.watchdog: render loop stalled" in capfd.readouterr().err


def test_a_fresh_stall_marker_is_taken_once_and_a_stale_one_is_ignored(tmp_path):
    marker = tmp_path / "stalled"
    marker.write_text("6.0\n")
    written = marker.stat().st_mtime
    # the older shape names no look
    taken = take_marker(marker, now=lambda: written + 30.0)
    assert taken is not None and taken.age == pytest.approx(30.0) and taken.looks == ()
    assert not marker.exists()
    assert take_marker(marker, now=lambda: written + 30.0) is None
    marker.write_text("6.0\n")
    assert take_marker(marker, now=lambda: marker.stat().st_mtime + MARKER_FRESH_S) is None
    assert not marker.exists()


def test_the_stall_marker_defaults_beside_the_audit_log(monkeypatch, tmp_path):
    monkeypatch.delenv(watchdog_module.MARKER_ENV)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert marker_path() == tmp_path / ".local" / "state" / "pewpew" / "stalled"


class Flat(Pattern):
    def render(self, x, y, z, index):
        return np.zeros((len(x), 3), dtype=np.float32)


def test_the_thread_fires_once_on_a_stall():
    """The thread checks on fake time: a stall past the timeout fires once,
    with the stall it measured, and the thread then ends."""
    ft = FakeTime()
    fired: list[float] = []
    stalled = threading.Event()

    def on_stall(seconds: float) -> None:
        fired.append(seconds)
        stalled.set()

    dog = Watchdog(5.0, interval=0.001, now=ft.now, on_stall=on_stall)
    dog.start()
    try:
        dog.beat()
        ft.t += 4.9  # a hitch under the timeout
        dog.beat()
        ft.t += 5.0
        assert stalled.wait(2.0)
    finally:
        dog.stop()
    assert fired == [pytest.approx(5.0)] and dog.fired


def test_each_frame_the_loop_completes_is_a_beat():
    """The loop drives the watchdog through `on_frame`: the stall is measured
    from the last frame, not from the start."""
    ft = FakeTime()
    dog = Watchdog(5.0, now=ft.now)
    loop = PacedLoop(Renderer(Flat(), line(8)), fps=60.0, on_frame=[dog.beat], now=ft.now, sleep=ft.sleep)
    loop.run(frames=3)
    last = ft.t - ft.sleeps[-1]  # the beat comes before the frame's sleep
    ft.t = last + 4.9
    assert dog.check() is None
    ft.t = last + 5.0
    assert dog.check() == pytest.approx(5.0)


# ---- the sleep assertion ----------------------------------------------------


def awake_with(spawned: list) -> KeepAwake:
    def spawn(args):
        proc = FakeProcess(args)
        spawned.append(proc)
        return proc

    return KeepAwake(spawn=spawn, which=lambda name: "/usr/bin/caffeinate", pid=4242)


def test_keep_awake_holds_caffeinate_on_this_process():
    spawned: list[FakeProcess] = []
    awake = awake_with(spawned)
    awake.start()
    assert spawned[0].args == ["caffeinate", "-i", "-s", "-w", "4242"]
    assert awake.state() == {"requested": True, "held": True, "detail": None}
    awake.stop()
    assert spawned[0].terminated


def test_keep_awake_restarts_caffeinate_when_it_ends(caplog):
    spawned: list[FakeProcess] = []
    awake = awake_with(spawned)
    awake.start()
    spawned[0].end(1)
    assert awake.state() == {"requested": True, "held": False, "detail": "caffeinate exited (1)"}
    awake.check()
    assert len(spawned) == 2 and awake.state()["held"]
    assert "caffeinate exited" in caplog.text


def test_keep_awake_retries_a_caffeinate_that_failed_to_start(caplog):
    spawned: list[FakeProcess] = []
    failures = [OSError(35, "Resource temporarily unavailable")] * 2

    def spawn(args):
        if failures:
            raise failures.pop()
        spawned.append(FakeProcess(args))
        return spawned[-1]

    awake = KeepAwake(spawn=spawn, which=lambda name: "/usr/bin/caffeinate", pid=4242)
    awake.start()
    assert not awake.state()["held"]
    awake.check()  # fails the same way: not logged again
    assert caplog.text.count("cannot keep the laptop awake") == 1
    awake.check()
    assert len(spawned) == 1 and awake.state() == {"requested": True, "held": True, "detail": None}


def test_keep_awake_reports_a_missing_caffeinate():
    awake = KeepAwake(spawn=lambda args: pytest.fail("spawned"), which=lambda name: None)
    awake.start()
    assert awake.state() == {"requested": True, "held": False, "detail": "caffeinate not found: macOS only"}


def test_the_marker_names_the_look_that_played_and_the_fresh_ones_it_took(monkeypatch, tmp_path):
    monkeypatch.setattr(watchdog_module, "_exit", lambda code: None)
    marker = tmp_path / "stalled"
    ft = FakeTime()
    dog = Watchdog(1.0, interval=3600.0, marker=marker, playing=lambda: "b",
                   earlier=Stall(100.0, ("a", "b")), now=ft.now)
    dog.start()
    dog.stop()
    dog._fire(1.0)
    assert json.loads(marker.read_text())["looks"] == ["a", "b"]  # once each
    ft.t = MARKER_FRESH_S  # the earlier stall is now past the window
    dog._fire(1.0)
    assert json.loads(marker.read_text())["looks"] == ["b"]
    marker.write_text(json.dumps({"stalled": 1.0, "looks": ["x", 3, "x", "y"]}))
    assert take_marker(marker, now=lambda: marker.stat().st_mtime + 1.0) == Stall(1.0, ("x", "y"))
    marker.write_text("not json")
    assert take_marker(marker, now=lambda: marker.stat().st_mtime + 1.0) == Stall(1.0, ())
