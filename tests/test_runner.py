"""The `python -m pewpew run` entry point, driven in-process."""

from __future__ import annotations

import io
import logging
import sys

import pytest
from conftest import FakeTime

from pewpew.__main__ import _status_of, main


def run(argv, **kw):
    """`main` on a fake sink clock: the RateGate then costs no wall time and
    cannot let the loop outrun the driver, so frame counts are exact."""
    ft = FakeTime()
    stream = io.StringIO()
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


def test_run_rejects_unknown_pattern_and_bad_map():
    with pytest.raises(SystemExit, match="unknown pattern"):
        main(["run", "nope", "--frames", "1"])
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
    )
    assert rc == 0
    out = term.getvalue()
    assert "TRACEBACK" in out  # deferred, never dropped
    # ...and only after the sink restored the cursor and released the terminal.
    assert out.index("\x1b[?25h") < out.index("TRACEBACK")
    assert "\x1b[?25l" in out  # this really was the interactive path


def test_cli_logging_leaves_no_handler_behind():
    root = logging.getLogger("pewpew")
    before = list(root.handlers)
    run(["run", "comet", "--map", "line:8", "--frames", "1"])
    run(["run", "comet", "--map", "line:8", "--frames", "1"])
    assert root.handlers == before  # repeated in-process runs must not stack
