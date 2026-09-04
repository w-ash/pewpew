"""The `python -m pewpew run` entry point, driven in-process."""

from __future__ import annotations

import io
import logging
import sys

import pytest
from conftest import FakeCallSoon, FakeTime

from pewpew import Renderer, line
from pewpew.__main__ import _default_mapping, _load, _LoopControls, _status_of, main
from pewpew.patterns import Plasma


def no_watch(source, stop):
    """A watcher that never fires, so no in-process run touches watchfiles."""
    return iter(())


def run(argv, **kw):
    """`main` on a fake sink clock: the RateGate then costs no wall time and
    cannot let the loop outrun the driver, so frame counts are exact."""
    ft = FakeTime()
    stream = io.StringIO()
    kw.setdefault("watch", no_watch)
    rc = main(argv, ansi_stream=stream, now=ft.now, sleep=ft.sleep, **kw)
    return rc, stream.getvalue()


def test_run_renders_n_frames_to_ansi_and_exits_clean():
    rc, out = run(["run", "comet", "--map", "line:8", "--frames", "3"])
    assert rc == 0
    # Pipe mode (StringIO is not a tty): three frame blocks, no cursor codes.
    # Exactly three because teardown drains the mailbox before stopping —
    # `stop()` alone discards the pending frame, losing the last one.
    assert out.count("\n\n") == 3
    assert "\x1b[?25l" not in out
    assert "\x1b[38;2;" in out


def test_run_defaults_the_map_to_the_patterns_own_study_fixture():
    # comet was authored against line(300); the old fixed grid:16x16 default
    # showed it on geometry it was never designed for.
    for name, expected in [("comet", 300), ("plasma", 300), ("geq", 256), ("fire", 512), ("sdf3d", 1000)]:
        assert len(_default_mapping(_load(name).cls)) == expected


def test_explicit_map_still_wins_over_the_default():
    rc, out = run(["run", "comet", "--map", "line:8", "--frames", "1"])
    assert rc == 0
    assert out.count("█") == 8  # the 8 asked for, not comet's 300


def test_run_rejects_unknown_pattern_and_bad_map():
    with pytest.raises(SystemExit, match="unknown pattern") as exc:
        main(["run", "nope", "--frames", "1"])
    # The gallery's __all__ is wider than its runnable patterns; only Pattern
    # subclasses may be offered.
    assert "study_cases" not in str(exc.value)
    with pytest.raises(SystemExit, match="bad --map"):
        main(["run", "comet", "--map", "torus:9", "--frames", "1"])
    with pytest.raises(SystemExit, match="bad --param"):
        main(["run", "comet", "--param", "speed", "--frames", "1"])


def test_run_passes_declared_params_through():
    rc, _ = run(["run", "comet", "--map", "line:8", "--frames", "1", "--param", "speed=1.5"])
    assert rc == 0


class _HealingRenderer:
    """A renderer whose error clears between two reads of the attribute —
    the interleaving the loop thread really produces when a pattern recovers
    while a SinkDriver worker is formatting the status line."""

    def __init__(self) -> None:
        self.reads = 0

    @property
    def error(self):
        self.reads += 1
        return "boom" if self.reads == 1 else None


def test_status_supplier_snapshots_the_error_once():
    renderer = _HealingRenderer()
    status = _status_of(renderer)
    # Testing the attribute and then formatting it would return the string
    # "None" here: truthy on the first read, gone on the second.
    assert status() == "boom"
    assert renderer.reads == 1


def test_run_announces_the_preview_url(capsys):
    rc, _ = run(["run", "comet", "--map", "line:8", "--frames", "1", "--preview", "0"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "preview at http://127.0.0.1:" in err  # port 0 -> whatever we bound
    assert "http://127.0.0.1:0/" not in err  # the real port, not the request


def test_log_records_are_deferred_while_the_ansi_sink_owns_the_terminal(monkeypatch):
    r"""A pattern that raises logs a traceback, and stderr and stdout are the
    same device in a terminal. That text landing between frames would desync
    the sink's `\x1b[nF` rewind from the block it rewinds over, so every later
    frame scribbles on the wrong rows. Records are held and replayed once the
    sink hands the terminal back."""

    class Tty(io.StringIO):
        logged = False

        def isatty(self) -> bool:
            return True

        def write(self, s: str) -> int:
            # Whatever the engine logs mid-frame — Renderer._contain's
            # traceback is the real one — must not reach the terminal now.
            # Once only, so a handler that writes here cannot recurse.
            if not Tty.logged:
                Tty.logged = True
                logging.getLogger("pewpew.fake").error("TRACEBACK")
            return super().write(s)

    term = Tty()
    monkeypatch.setattr(sys, "stderr", term)  # one device, as in a real shell
    ft = FakeTime()
    rc = main(
        ["run", "comet", "--map", "line:8", "--frames", "3"],
        ansi_stream=term,
        now=ft.now,
        sleep=ft.sleep,
        watch=no_watch,
    )
    assert rc == 0
    out = term.getvalue()
    assert "TRACEBACK" in out  # deferred, never dropped
    # ...and only after the sink restored the cursor and released the terminal.
    assert out.index("\x1b[?25h") < out.index("TRACEBACK")
    assert "\x1b[?25l" in out  # this really was the interactive path


def test_live_set_is_queued_for_the_loop_thread_not_applied_on_the_callers():
    renderer = Renderer(Plasma(), line(8))
    queue = FakeCallSoon()
    controls = _LoopControls(renderer, queue)

    assert controls.set("speed", 1.75) is None
    # Nothing has touched the renderer yet: call_soon drains at the top of a
    # tick, before advance_to, which is what keeps a frame from seeing half a
    # change (plasma reads speed in before_render and scale in render).
    assert renderer.pattern.speed == 0.5
    queue.drain()
    assert renderer.pattern.speed == 1.75
    assert renderer.params["speed"] == 1.75
    assert controls.describe()[0]["value"] == 1.75


def test_out_of_range_live_set_is_refused_without_queueing_anything():
    # The live-crash path: call_soon propagates a closure's exception out of
    # run(), so an out-of-range slider must never become a queued closure.
    renderer = Renderer(Plasma(), line(8))
    queue = FakeCallSoon()
    controls = _LoopControls(renderer, queue)

    reason = controls.set("scale", 99.0)
    assert reason == renderer.params.check("scale", 99.0)
    assert queue.queued == []
    assert renderer.params["scale"] == 4.0


def test_a_queued_set_gone_stale_logs_instead_of_killing_the_loop(caplog, monkeypatch):
    # A value passes check on the connection thread, then the range moves
    # under it before the closure runs. Applying it must not raise: that
    # exception would come out of PacedLoop.run() and stop the show.
    renderer = Renderer(Plasma(), line(8))
    queue = FakeCallSoon()
    controls = _LoopControls(renderer, queue)
    controls.set("speed", 1.75)
    # Declarations are the class's own Param objects, shared by every test in
    # the process — monkeypatch so narrowing the range does not outlive this
    # one. A reload would swap the whole class; this reaches the same state.
    monkeypatch.setattr(renderer.params.declarations["speed"], "hi", 1.0)

    with caplog.at_level(logging.WARNING, logger="pewpew"):
        queue.drain()  # the loop thread; must return, not raise
    assert "speed" in caplog.text
    assert renderer.pattern.speed == 0.5  # unchanged, and the loop lives


def test_cli_logging_leaves_no_handler_behind():
    root = logging.getLogger("pewpew")
    before = list(root.handlers)
    run(["run", "comet", "--map", "line:8", "--frames", "1"])
    run(["run", "comet", "--map", "line:8", "--frames", "1"])
    assert root.handlers == before  # repeated in-process runs must not stack


def test_run_takes_a_pattern_file_and_a_search_dir(tmp_path):
    (tmp_path / "mine.py").write_text(
        "import numpy as np\nfrom pewpew import Pattern\n"
        "class Mine(Pattern):\n    name = 'mine'\n"
        "    def render(self, x, y, z, index):\n"
        "        return np.ones((self.n, 3), dtype=np.float32)\n"
    )
    rc, out = run(["run", str(tmp_path / "mine.py"), "--map", "line:4", "--frames", "1"])
    assert rc == 0 and out.count("█") == 4
    rc, _ = run(["run", "mine", "--patterns", str(tmp_path), "--map", "line:4", "--frames", "1"])
    assert rc == 0
    # A load failure is one clean line naming the file — the CLI is the one
    # surface allowed to print a path.
    (tmp_path / "broken.py").write_text("def (:\n")
    with pytest.raises(SystemExit) as exc:
        main(["run", str(tmp_path / "broken.py"), "--frames", "1"])
    assert str(exc.value) == f"{tmp_path / 'broken.py'}: SyntaxError: invalid syntax (line 1)"


def test_reload_watches_the_source_by_default_and_not_with_no_reload(tmp_path):
    calls = []

    def watch(source, stop):
        calls.append((source, stop))
        return iter(())

    rc, _ = run(["run", "comet", "--map", "line:8", "--frames", "1"], watch=watch)
    assert rc == 0
    assert len(calls) == 1
    source, stop = calls[0]
    assert source.name == "comet.py"  # gallery patterns reload too
    assert stop.is_set()  # teardown stopped the watcher before the sinks

    calls.clear()
    rc, _ = run(["run", "comet", "--map", "line:8", "--frames", "1", "--no-reload"], watch=watch)
    assert rc == 0 and calls == []


def test_status_prefers_the_reload_error_over_the_pattern_error():
    class Src:
        def __init__(self, error):
            self.error = error

    assert _status_of(Src("reload failed"), Src("render raised"))() == "reload failed"
    assert _status_of(Src(None), Src("render raised"))() == "render raised"
    assert _status_of(Src(None), Src(None))() is None
