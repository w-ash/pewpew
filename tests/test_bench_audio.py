"""bench/bench_audio.py: the replug trials on a fake input, timed on a fake
clock, and the dry run. The trials themselves need a person and a real cable."""

from __future__ import annotations

import numpy as np

from bench.bench_audio import LOST_WAIT_S, main, replug
from fake_sounddevice import LINE, Device, FakeSoundDevice
from fakes import FakeTime
from pewpew.audio.device import RETRY_S, device_source


def test_each_trial_times_the_loss_and_the_reopen(sd: FakeSoundDevice) -> None:
    ft = FakeTime()
    source = device_source(LINE, fps=60.0, now=ft.now)

    def ask(step: str) -> None:  # the person at the bench, at once
        if step == "unplug":
            sd.unplug(LINE)
        else:
            sd.plug(Device(LINE, 2))

    def sleep(seconds: float) -> None:  # one tick: the supervisor steps, and an open input hears 800 samples
        ft.sleep(seconds)
        source.step()
        stream = sd.streams[-1] if sd.streams else None
        if stream is not None and not stream.closed and stream.fail is None:
            stream.push(np.zeros(800))

    trials = replug(source, 2, ask=ask, now=ft.now, sleep=sleep)
    assert [t["passed"] for t in trials] == [True, True]
    assert all(t["lost_s"] < 0.1 and t["back_s"] <= RETRY_S + 0.1 for t in trials)


def test_an_input_that_stays_unplugged_fails_its_trial(sd: FakeSoundDevice) -> None:
    ft = FakeTime()
    source = device_source(LINE, fps=60.0, now=ft.now)

    def sleep(seconds: float) -> None:
        ft.sleep(seconds)
        source.step()

    (trial,) = replug(source, 1, ask=lambda step: sd.unplug(LINE) if step == "unplug" else None, now=ft.now,
                      sleep=sleep)
    assert trial["lost_s"] is not None and trial["lost_s"] < LOST_WAIT_S and trial["back_s"] is None
    assert not trial["passed"] and trial["reason"] == "no input is named 'Scarlett 2i2 USB'"


def test_the_dry_run_names_the_input_and_opens_nothing(sd: FakeSoundDevice, capsys) -> None:
    main([LINE, "--dry-run"])
    out = capsys.readouterr().out
    assert "audio: 'Scarlett 2i2 USB' (Core Audio)" in out and "dry run: nothing opened" in out
    assert sd.streams == []
