"""Hot reload: `Renderer.swap` keeps the show's state, and `Reloader` keeps
the show alive when the edit is broken."""

from __future__ import annotations

import logging
import textwrap
import threading

import numpy as np
import pytest
from conftest import FakeCallSoon

from pewpew import Param, Pattern, Renderer, line, render_sequence
from pewpew.load import load_file, resolve
from pewpew.patterns import STUDY_CASES
from pewpew.reload import Reloader
from pewpew.render import SlotClock


def run(renderer, clock, frames):
    return [renderer.advance_to(clock.advance()) for _ in range(frames)]


# ---- Renderer.swap ---------------------------------------------------------


@pytest.mark.parametrize("cls,mapping", STUDY_CASES, ids=[c.__name__ for c, _ in STUDY_CASES])
def test_swap_to_the_same_source_is_invisible_in_the_frames(cls, mapping):
    """The star test. A swap mid-sequence — to a fresh instance of the same
    class, and to a class re-executed from the same file the way a reload
    does — renders bit-identically to no swap at all. That is what proves
    the inherited set (pixels, buffers, rng, scalars, t) is complete."""
    reference = render_sequence(cls, mapping, seed=42, frames=90)
    fresh = load_file(resolve(cls.__name__.lower()).source, attr=None).cls
    assert fresh is not cls
    for candidate in (cls, fresh):
        renderer = Renderer(cls(), mapping, seed=42)
        clock = SlotClock(60.0)
        frames = run(renderer, clock, 30)
        renderer.swap(candidate())
        frames += run(renderer, clock, 30)
        renderer.swap(candidate())
        frames += run(renderer, clock, 30)
        assert np.array_equal(np.stack(frames), reference), candidate.__module__
        assert renderer.t == clock.t


class Counter(Pattern):
    name = "counter"
    gain = Param(0.5, 0.0, 1.0, "Gain")

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
    renderer.set_param("gain", 0.25)
    clock = SlotClock(60.0)
    run(renderer, clock, 3)
    old = renderer.pattern

    report = renderer.swap(Counter())

    assert renderer.pattern is not old
    assert renderer.params is params  # the control surface keeps driving the show
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
    # ...and the show simply continues.
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
    assert not renderer._bind_failed
    assert renderer.step(1 / 60).shape == (4, 3)  # still rendering, not poisoned


def test_a_swap_repairs_a_poisoned_renderer():
    class Flaky(Counter):
        fail = False

        def setup(self, n, x, y, z, index):
            if self.fail:
                raise RuntimeError("no")
            super().setup(n, x, y, z, index)

    renderer = Renderer(Flaky(), line(4))
    renderer.pattern.fail = True
    with pytest.raises(RuntimeError, match="no"):
        renderer.rebind(line(4))
    with pytest.raises(RuntimeError, match="not bound"):
        renderer.step(1 / 60)
    renderer.swap(Counter())  # a full bind against the geometry succeeded
    assert renderer.step(1 / 60).shape == (4, 3)


def test_param_policy_on_swap_follows_adr_006():
    class Retuned(Pattern):
        name = "counter"
        gain = Param(0.9, 0.5, 1.0, "Gain")  # narrowed: 0.25 no longer fits
        extra = Param(3.0, 0.0, 10.0, "New")

        def render(self, x, y, z, index):
            return np.zeros((self.n, 3), dtype=np.float32)

    renderer = Renderer(Counter(), line(4))
    renderer.set_param("gain", 0.25)
    report = renderer.swap(Retuned())
    assert report.reset_params == ("gain",)
    assert renderer.params["gain"] == 0.9  # the new default, not a clamp to 0.5
    assert renderer.params["extra"] == 3.0
    assert [p["name"] for p in renderer.params.describe()] == ["gain", "extra"]
    assert renderer.params.check("gain", 0.25) is not None  # the new range is live

    # Widened: the value is kept.
    class Wider(Retuned):
        gain = Param(0.9, 0.0, 5.0, "Gain")

    renderer.set_param("gain", 0.75)
    renderer.swap(Wider())
    assert renderer.params["gain"] == 0.75


def test_a_knob_demoted_to_a_constant_takes_the_new_constant():
    class Demoted(Pattern):
        name = "counter"

        def __init__(self):
            self.gain = 0.1  # was a Param; now the author's constant

        def render(self, x, y, z, index):
            return np.zeros((self.n, 3), dtype=np.float32)

    renderer = Renderer(Counter(), line(4))
    renderer.set_param("gain", 0.25)
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


def test_a_buffer_whose_dtype_changed_starts_fresh():
    class Doubled(Counter):
        def setup(self, n, x, y, z, index):
            self.acc = self.buffer("acc", n, dtype=np.float64)

    renderer = Renderer(Counter(), line(4))
    renderer.step(1 / 60)
    report = renderer.swap(Doubled())
    assert "acc" not in report.buffers
    assert renderer.pattern.acc.dtype == np.float64 and not renderer.pattern.acc.any()
    assert renderer.pattern._buffers["acc"].dtype == renderer.pattern.acc.dtype


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
        name = "phase"

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


# ---- Reloader --------------------------------------------------------------

SOURCE = '''
import numpy as np
from pewpew import Param, Pattern

class Mine(Pattern):
    name = "mine"
    level = Param({default}, 0.0, 1.0, "Level")

    def __init__(self):
        self.ticks = 0

    def before_render(self, dt, features):
        self.ticks += 1

    def render(self, x, y, z, index):
        return np.full((self.n, 3), self.level, dtype=np.float32)
'''


def make(tmp_path, body=SOURCE, default=0.5):
    path = tmp_path / "mine.py"
    path.write_text(textwrap.dedent(body).format(default=default))
    loaded = resolve(str(path))
    renderer = Renderer(loaded.cls(), line(4))
    queue = FakeCallSoon()
    return path, renderer, Reloader(renderer, loaded, queue), queue


def test_reload_swaps_in_the_edited_file_and_keeps_state(tmp_path):
    path, renderer, reloader, _ = make(tmp_path)
    renderer.set_param("level", 0.2)
    renderer.step(1 / 60)
    renderer.step(1 / 60)
    path.write_text(textwrap.dedent(SOURCE).format(default=0.9).replace("np.full", "np.full  # edited"))
    assert reloader.reload() is True
    assert reloader.error is None and reloader.reloads == 1
    assert renderer.pattern.ticks == 2
    assert renderer.params["level"] == 0.2  # the live value still fits, so it stays
    assert renderer.pattern.__class__.__module__ == "pewpew_user.mine"


def test_unchanged_bytes_are_a_no_op(tmp_path):
    path, renderer, reloader, _ = make(tmp_path)
    old = renderer.pattern
    path.write_text(path.read_text())  # an editor "save" with nothing changed
    assert reloader.reload() is False
    assert renderer.pattern is old and reloader.reloads == 0


def test_a_broken_edit_keeps_the_last_good_pattern_and_shows_why(tmp_path, caplog):
    path, renderer, reloader, _ = make(tmp_path)
    old = renderer.pattern
    path.write_text("def (:\n")
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        assert reloader.reload() is False
    assert renderer.pattern is old
    assert reloader.error is not None
    assert reloader.error == (
        "reload failed, last-good pattern still running: SyntaxError: invalid syntax (line 1)"
    )
    assert "/" not in reloader.error and ".py" not in reloader.error
    assert renderer.step(1 / 60).shape == (4, 3)  # the show goes on
    assert "reload failed" in caplog.text
    # A second event for the same broken bytes is not a second traceback.
    assert reloader.reload() is False and reloader.failures == 1
    # The fix clears it.
    path.write_text(textwrap.dedent(SOURCE).format(default=0.5) + "\n# fixed\n")
    assert reloader.reload() is True
    assert reloader.error is None


def test_a_setup_that_raises_on_reload_is_a_failure_not_a_crash(tmp_path):
    path, renderer, reloader, _ = make(tmp_path)
    old = renderer.pattern
    path.write_text(
        textwrap.dedent(SOURCE).format(default=0.5)
        + "    def setup(self, n, x, y, z, index):\n        raise RuntimeError('no')\n"
    )
    assert reloader.reload() is False
    assert renderer.pattern is old
    assert reloader.error is not None and "RuntimeError: no" in reloader.error


def test_a_second_class_appearing_needs_a_name(tmp_path):
    path, renderer, reloader, _ = make(tmp_path)
    path.write_text(textwrap.dedent(SOURCE).format(default=0.5) + "\nclass Other(Mine):\n    name = 'other'\n")
    assert reloader.reload() is False
    assert "pick one with :ClassName" in (reloader.error or "")


def test_an_explicit_class_name_is_honoured_on_reload(tmp_path):
    body = textwrap.dedent(SOURCE).format(default=0.5) + "\nclass Other(Mine):\n    name = 'other'\n"
    path = tmp_path / "two.py"
    path.write_text(body)
    loaded = resolve(f"{path}:Other")
    renderer = Renderer(loaded.cls(), line(4))
    reloader = Reloader(renderer, loaded, FakeCallSoon())
    path.write_text(body + "# edit\n")
    assert reloader.reload() is True
    assert renderer.pattern.name == "other"


def test_a_gone_file_is_reported_and_its_return_clears_the_error(tmp_path):
    path, renderer, reloader, _ = make(tmp_path)
    body = path.read_text()
    path.unlink()
    assert reloader.reload() is False
    assert reloader.error is not None and "gone" in reloader.error
    assert "/" not in reloader.error
    assert renderer.step(1 / 60).shape == (4, 3)
    path.write_text(body)  # `git stash pop`: byte-identical
    assert reloader.reload() is True
    assert reloader.error is None


def test_two_same_length_saves_in_one_second_both_take_effect(tmp_path):
    """The bytes in hand are the truth, never the bytecode cache, whose
    mtime-and-size check cannot tell these two saves apart."""
    path, renderer, reloader, _ = make(tmp_path, default=0.3)
    stat = path.stat()
    path.write_text(textwrap.dedent(SOURCE).format(default=0.7))
    import os

    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same second, same size
    assert reloader.reload() is True
    # The live value 0.3 still fits and is kept (ADR-006); the *declaration*
    # is what proves the new bytes ran.
    assert renderer.params.declarations["level"].default == 0.7
    assert not (tmp_path / "__pycache__").exists()


def test_watcher_events_queue_reloads_on_the_loop_thread_and_stop_joins(tmp_path):
    fired = threading.Event()

    def watch(source, stop):
        assert source == tmp_path / "mine.py"
        yield {"one batch"}
        fired.set()
        stop.wait()  # block like the real watcher until asked to stop

    path = tmp_path / "mine.py"
    path.write_text(textwrap.dedent(SOURCE).format(default=0.5))
    loaded = resolve(str(path))
    renderer = Renderer(loaded.cls(), line(4))
    queue = FakeCallSoon()
    reloader = Reloader(renderer, loaded, queue, watch=watch)
    reloader.start()
    assert fired.wait(2.0)
    assert reloader.active
    assert queue.queued and queue.queued[0] == reloader.reload
    queue.drain()  # nothing changed on disk: a no-op, and nothing raised
    reloader.stop()
    assert not reloader.active


def test_a_dying_watcher_disables_reload_but_not_the_show(tmp_path, caplog):
    def watch(source, stop):
        raise OSError("inotify limit")
        yield  # pragma: no cover

    path, renderer, _, queue = make(tmp_path)
    reloader = Reloader(renderer, resolve(str(path)), queue, watch=watch)
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        reloader.start()
        reloader.stop()
    assert "watcher died" in caplog.text
    assert renderer.step(1 / 60).shape == (4, 3)


def test_a_pattern_without_a_source_has_nothing_to_watch():
    from pewpew.load import LoadedPattern

    loaded = LoadedPattern(cls=Counter, source=None, attr=None, digest="")
    renderer = Renderer(Counter(), line(4))
    reloader = Reloader(renderer, loaded, FakeCallSoon())
    reloader.start()
    assert not reloader.active
    assert reloader.reload() is False
