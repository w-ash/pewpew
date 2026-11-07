"""Hot reload: `Renderer.swap` keeps the run's state, and `FileReloader`
keeps the run alive when an edit is broken."""

from __future__ import annotations

import hashlib
import logging
import os
import threading

import numpy as np
import pytest

from pewpew import Float, Pattern, Renderer, line, render_sequence
from pewpew.pace import Calls
from pewpew.patterns import STUDY_CASES
from pewpew.reload import FileReloader
from pewpew.render import SlotClock


def run(renderer, clock, frames):
    return [renderer.advance_to(clock.advance()) for _ in range(frames)]


# ---- Renderer.swap ---------------------------------------------------------


@pytest.mark.parametrize(
    "cls,mapping", [case[:2] for case in STUDY_CASES], ids=[c.__name__ for c, *_ in STUDY_CASES]
)
def test_swap_to_the_same_source_is_invisible_in_the_frames(cls, mapping):
    """The star test. A swap mid-sequence to a fresh instance of the same
    class renders bit-identically to no swap at all. That is what proves
    the inherited set (pixels, buffers, rng, scalars, t) is complete."""
    reference = render_sequence(cls, mapping, seed=42, frames=90)
    renderer = Renderer(cls(), mapping, seed=42)
    clock = SlotClock(60.0)
    frames = run(renderer, clock, 30)
    renderer.swap(cls())
    frames += run(renderer, clock, 30)
    renderer.swap(cls())
    frames += run(renderer, clock, 30)
    assert np.array_equal(np.stack(frames), reference)
    assert renderer.t == clock.t


class Counter(Pattern):
    gain = Float(0.5, 0.0, 1.0, label="Gain")

    def __init__(self):
        self.ticks = 0
        self.label = "a"
        self.table = [1, 2]

    def setup(self, n, x, y, z, index):
        self.acc = self.buffer("acc", n)

    def before_render(self, dt, features):
        self.ticks += 1
        self.acc = self.acc + np.float32(self.gain)

    def render(self, x, y, z, index):
        return np.stack([self.acc, self.acc, self.acc], axis=1).astype(np.float32)


def test_swap_keeps_t_frame_params_identity_buffers_and_scalars():
    renderer = Renderer(Counter(), line(4))
    params = renderer.params
    renderer.params.set("gain", 0.25)
    clock = SlotClock(60.0)
    run(renderer, clock, 3)
    old = renderer.pattern

    report = renderer.swap(Counter())

    assert renderer.pattern is not old
    assert renderer.params is params  # the control surface keeps driving the run
    assert renderer.params["gain"] == 0.25 and renderer.pattern.gain == 0.25
    assert renderer.pattern.ticks == 3 and renderer.pattern.label == "a"
    assert np.array_equal(renderer.pattern.acc, old.acc)
    assert renderer.pattern.acc is not old.acc  # a copy: the old instance is never touched
    assert np.array_equal(renderer.pattern.pixels, old.pixels)
    assert renderer.t == clock.t
    assert report.buffers == ("pixels", "acc")
    assert report.scalars == ("ticks", "label")
    assert report.skipped == ("table",)  # a list is not a scalar; starts fresh
    assert renderer.pattern.table == [1, 2]
    # ...and the run simply continues.
    frame = renderer.step(1 / 60)
    assert np.allclose(frame[:, 0], 0.25 * 4)


def test_swap_rejects_a_class():
    renderer = Renderer(Counter(), line(4))
    with pytest.raises(TypeError, match="Pattern instance"):
        renderer.swap(Counter)


def test_a_failing_setup_leaves_the_renderer_exactly_as_it_was():
    class Broken(Counter):
        def setup(self, n, x, y, z, index):
            raise RuntimeError("no")

    renderer = Renderer(Counter(), line(4))
    clock = SlotClock(60.0)
    run(renderer, clock, 2)
    old, before = renderer.pattern, renderer.params.describe()
    with pytest.raises(RuntimeError, match="no"):
        renderer.swap(Broken())
    assert renderer.pattern is old
    assert renderer.params.describe() == before
    assert renderer.step(1 / 60).shape == (4, 3)  # still rendering, not poisoned


def test_param_policy_on_swap_follows_adr_006():
    class Retuned(Pattern):
        gain = Float(0.9, 0.5, 1.0, label="Gain")  # narrowed: 0.25 no longer fits
        extra = Float(3.0, 0.0, 10.0, label="New")

        def render(self, x, y, z, index):
            return np.zeros((self.n, 3), dtype=np.float32)

    renderer = Renderer(Counter(), line(4))
    renderer.params.set("gain", 0.25)
    report = renderer.swap(Retuned())
    assert report.reset_params == ("gain",)
    assert renderer.params["gain"] == 0.9  # the new default, not a clamp to 0.5
    assert renderer.params["extra"] == 3.0
    assert [p["name"] for p in renderer.params.describe()] == ["gain", "extra"]
    assert renderer.params.check("gain", 0.25) is not None  # the new range is live

    # Widened: the value is kept.
    class Wider(Retuned):
        gain = Float(0.9, 0.0, 5.0, label="Gain")

    renderer.params.set("gain", 0.75)
    renderer.swap(Wider())
    assert renderer.params["gain"] == 0.75


def test_a_knob_demoted_to_a_constant_takes_the_new_constant():
    class Demoted(Pattern):
        def __init__(self):
            self.gain = 0.1  # was a Param; now the author's constant

        def render(self, x, y, z, index):
            return np.zeros((self.n, 3), dtype=np.float32)

    renderer = Renderer(Counter(), line(4))
    renderer.params.set("gain", 0.25)
    report = renderer.swap(Demoted())
    assert renderer.pattern.gain == 0.1
    assert "gain" not in report.scalars
    assert len(renderer.params) == 0


def test_a_buffer_whose_shape_changed_starts_fresh_while_the_rest_are_kept():
    class Wider(Counter):
        def setup(self, n, x, y, z, index):
            self.acc = self.buffer("acc", (n, 2))

    renderer = Renderer(Counter(), line(4))
    renderer.step(1 / 60)
    old = renderer.pattern
    report = renderer.swap(Wider())
    assert report.buffers == ("pixels",)
    assert renderer.pattern.acc.shape == (4, 2) and not renderer.pattern.acc.any()
    assert np.array_equal(renderer.pattern.pixels, old.pixels)


def test_a_buffer_whose_dtype_changed_starts_fresh_and_carries_over_as_the_new_dtype():
    class Doubled(Counter):
        def setup(self, n, x, y, z, index):
            self.acc = self.buffer("acc", n, dtype=np.float64)

    renderer = Renderer(Counter(), line(4))
    renderer.step(1 / 60)
    report = renderer.swap(Doubled())
    assert "acc" not in report.buffers
    assert renderer.pattern.acc.dtype == np.float64 and not renderer.pattern.acc.any()
    assert "acc" in renderer.swap(Doubled()).buffers  # the next swap keeps it


def test_setup_owns_what_it_assigns_and_sees_inherited_buffers():
    """Scalars set in `setup` are the new code's own (editing one takes
    effect on save), and a view `setup` derives from a buffer refers to the
    inherited data, because the buffer is taken over at declaration."""

    class Derived(Counter):
        def setup(self, n, x, y, z, index):
            self.acc = self.buffer("acc", n)
            self.decay = 0.9
            self.top = self.acc[:2]  # a view onto the buffer

        def before_render(self, dt, features):
            self.top += np.float32(1.0)

        def render(self, x, y, z, index):
            return np.stack([self.acc] * 3, axis=1)

    class Edited(Derived):
        def setup(self, n, x, y, z, index):
            super().setup(n, x, y, z, index)
            self.decay = 0.5

    renderer = Renderer(Derived(), line(4))
    renderer.step(1 / 60)
    renderer.step(1 / 60)
    assert renderer.pattern.acc[0] == 2.0
    report = renderer.swap(Edited())
    assert renderer.pattern.decay == 0.5  # setup's value, not the old 0.9
    assert "decay" not in report.scalars
    assert renderer.pattern.top.base is renderer.pattern.acc
    renderer.step(1 / 60)
    assert renderer.pattern.acc[0] == 3.0  # counting continues through the view


def test_numbers_are_one_family_so_an_int_literal_that_became_a_float_is_kept():
    class Phase(Pattern):
        def __init__(self):
            self.phase = 0  # the common idiom: an int literal

        def before_render(self, dt, features):
            self.phase += dt * 3.0  # ...that becomes a float

        def render(self, x, y, z, index):
            return np.zeros((self.n, 3), dtype=np.float32)

    renderer = Renderer(Phase(), line(4))
    renderer.step(1 / 60)
    before = renderer.pattern.phase
    assert isinstance(before, float)
    report = renderer.swap(Phase())
    assert renderer.pattern.phase == before and report.scalars == ("phase",)


def test_a_candidate_that_scribbles_on_a_buffer_and_raises_leaves_the_old_pattern_intact():
    class Vandal(Counter):
        def setup(self, n, x, y, z, index):
            self.acc = self.buffer("acc", n)
            self.acc[:] = 99.0
            raise RuntimeError("no")

    renderer = Renderer(Counter(), line(4))
    renderer.step(1 / 60)
    with pytest.raises(RuntimeError):
        renderer.swap(Vandal())
    assert renderer.pattern.acc[0] == 0.5  # the inherited buffer was a copy


def test_swap_resets_the_once_per_site_log_guard(caplog):
    class Raises(Counter):
        def render(self, x, y, z, index):
            raise ValueError("boom")

    renderer = Renderer(Raises(), line(4))
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        renderer.step(1 / 60)
        renderer.step(1 / 60)
        assert len(caplog.records) == 1
        renderer.swap(Raises())  # same file, same line: same site key
        renderer.step(1 / 60)
        assert len(caplog.records) == 2


def test_error_clears_on_the_first_healthy_frame_after_a_swap():
    class Raises(Counter):
        def render(self, x, y, z, index):
            raise ValueError("boom")

    renderer = Renderer(Raises(), line(4))
    renderer.step(1 / 60)
    assert renderer.error is not None
    renderer.swap(Counter())
    assert renderer.error is not None  # untouched by the swap itself
    renderer.step(1 / 60)
    assert renderer.error is None


# ---- FileReloader ---------------------------------------------------------


class Applied:
    """What a `FileReloader` applied, in order; it raises for bytes that
    start with "broken"."""

    def __init__(self) -> None:
        self.versions: list[bytes] = []

    def __call__(self, data: bytes) -> str:
        if data.startswith(b"broken"):
            raise ValueError("the map has no fixtures")
        self.versions.append(data)
        return f"applied {data!r}"


def make(tmp_path, data=b"one", **kw):
    path = tmp_path / "room.json"
    path.write_bytes(data)
    applied = Applied()
    queue = Calls()
    return path, applied, FileReloader(path, hashlib.sha256(data).hexdigest(), queue.call_soon, applied,
                                       noun="map", **kw)


def test_a_changed_file_is_applied_and_unchanged_bytes_are_a_no_op(tmp_path):
    path, applied, reloader = make(tmp_path)
    path.write_bytes(b"one")  # an editor "save" with nothing changed
    assert reloader.reload() is False and applied.versions == []
    path.write_bytes(b"two")
    assert reloader.reload() is True and applied.versions == [b"two"] and reloader.error is None


def test_a_broken_edit_keeps_the_last_good_version_and_says_why(tmp_path, caplog):
    path, applied, reloader = make(tmp_path)
    path.write_bytes(b"broken")
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        assert reloader.reload() is False
    assert applied.versions == []
    assert reloader.error == "reload failed, last-good map still running: ValueError: the map has no fixtures"
    # A second event for the same broken bytes is not a second traceback.
    assert reloader.reload() is False and caplog.text.count("reload failed") == 1
    path.write_bytes(b"fixed")
    assert reloader.reload() is True and reloader.error is None


def test_a_gone_file_is_reported_and_its_return_clears_the_error(tmp_path):
    path, _, reloader = make(tmp_path)
    path.write_bytes(b"two")
    assert reloader.reload() is True
    path.unlink()
    assert reloader.reload() is False
    assert reloader.error is not None and "gone" in reloader.error and "/" not in reloader.error
    path.write_bytes(b"two")  # `git stash pop`: byte-identical
    assert reloader.reload() is True and reloader.error is None


def test_two_same_length_saves_in_one_second_both_take_effect(tmp_path):
    """The bytes in hand are the truth, never a file's mtime and size."""
    path, applied, reloader = make(tmp_path, b"aaa")
    stat = path.stat()
    path.write_bytes(b"bbb")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same second, same size
    assert reloader.reload() is True and applied.versions == [b"bbb"]


def test_watcher_events_queue_reloads_on_the_loop_thread_and_stop_joins(tmp_path):
    fired = threading.Event()

    def watch(source, stop):
        assert source == tmp_path / "room.json"
        yield {"one batch"}
        fired.set()
        stop.wait()  # block like the real watcher until asked to stop

    path = tmp_path / "room.json"
    path.write_bytes(b"one")
    queued: list = []
    reloader = FileReloader(path, None, queued.append, Applied(), noun="map", watch=watch)
    reloader.start()
    assert fired.wait(2.0)
    assert reloader.active
    assert queued and queued[0] == reloader.reload
    reloader.stop()
    assert not reloader.active


def test_a_dying_watcher_disables_reload_but_not_the_run(tmp_path, caplog):
    def watch(source, stop):
        raise OSError("inotify limit")
        yield  # pragma: no cover

    _, _, reloader = make(tmp_path, watch=watch)
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        reloader.start()
        reloader.stop()
    assert "watcher died" in caplog.text
