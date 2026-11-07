"""The `python -m pewpew run` entry point, driven in-process."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import socket
import subprocess
import sys

import numpy as np
import pytest

import pewpew.run as run_module
from fakes import EXAMPLES as EXAMPLE_LOOKS
from fakes import FakeTime, build, filed, frames, hosted, layered, looks_file, program_of, run_main, wait_until
from pewpew.__main__ import main
from pewpew.aura.master import Master
from pewpew.compose import layer_seed
from pewpew.fx import expr
from pewpew.fx.host import ProgramPattern
from pewpew.mapping import line
from pewpew.pace import PacedLoop
from pewpew.rig import EXAMPLES
from pewpew.run import preview_url, status_line
from pewpew.sinks import ddp, preview
from pewpew.sinks.base import to_linear_u8

# A program that keeps a trail: what it renders next depends on what it rendered.
TRAIL = 'osc(2, 0.4).trails(0.8).palette("ember")'


def unknown_op(tmp_path, op: str = "nope") -> str:
    """The path, as text, of a looks file whose one look runs op `op`, which
    no catalog holds."""
    path = tmp_path / f"{op}.look.json"
    path.write_text(filed(layered(op)))
    return str(path)


def usage_error(argv, capsys) -> str:
    """What argparse prints for a refused command line, which exits 2."""
    with pytest.raises(SystemExit) as exc:
        run_main(argv)
    assert exc.value.code == 2
    return capsys.readouterr().err


def test_run_renders_n_frames_to_ansi_and_exits_clean():
    rc, out = run_main(["run", looks_file(), "--map", "line:8", "--frames", "3"])
    assert rc == 0
    # Pipe mode (StringIO is not a tty): three frame blocks, no cursor codes.
    # Exactly three because teardown drains the mailbox before stopping —
    # `stop()` alone discards the pending frame, losing the last one.
    assert out.count("\n\n") == 3
    assert "\x1b[?25l" not in out
    assert "\x1b[38;2;" in out


def test_run_defaults_the_map_to_a_16x16_grid():
    rc, out = run_main(["run", looks_file(), "--frames", "1"])
    assert rc == 0 and out.count("▀") == 128  # two rows of the grid a character
    assert build(["run", looks_file()]).launch.mapping.shape == (256, 3)


def test_an_explicit_map_wins_over_the_default():
    rc, out = run_main(["run", looks_file(), "--map", "line:8", "--frames", "1"])
    assert rc == 0
    assert out.count("█") == 8  # the 8 asked for, not the default grid's 256


def test_run_rejects_a_bad_looks_file_and_a_bad_map(tmp_path, capsys):
    with pytest.raises(SystemExit, match=r"nope.look.json: cannot read the looks file: No such file or directory$"):
        main(["run", str(tmp_path / "nope.look.json"), "--frames", "1"])
    unknown = unknown_op(tmp_path)
    with pytest.raises(SystemExit, match=rf"^{re.escape(unknown)}: look 'look': layers.base.nope: unknown "
                       "op 'nope'; ops: add, "):
        main(["run", unknown, "--frames", "1"])
    # The gallery's `pattern` op is gone: a look that names it is refused as any unknown op is.
    with pytest.raises(SystemExit, match=r"layers.base.pattern: unknown op 'pattern'; ops: add, "):
        main(["run", unknown_op(tmp_path, "pattern"), "--frames", "1"])
    assert "argument --map: expected line:64, grid:16x16 or lattice:8, sizes at least 1; got 'torus:9'" in usage_error(
        ["run", looks_file(), "--map", "torus:9", "--frames", "1"], capsys)
    for flag in (["--param", "speed=1"], ["--units", "pixel"], ["--pattern-dir", "."], ["--no-reload"],
                 ["--looks", unknown]):
        assert "unrecognized arguments" in usage_error(["run", looks_file(), *flag, "--frames", "1"], capsys)


def test_a_run_starts_in_the_current_look_else_the_first(tmp_path, fake_ops):
    two = {"version": 4, "looks": {"warm": layered("solid_test", {"red": 0.5}), "cool": layered("solid_test")}}
    path = tmp_path / "looks.json"
    path.write_text(json.dumps(two))
    run = build(["run", str(path), "--map", "line:8"])
    assert run.looks.book.current == "warm" and run.control.values()["layers.base.solid.red"] == 0.5
    path.write_text(json.dumps({**two, "current": "cool"}))
    run = build(["run", str(path), "--map", "line:8"])
    assert run.looks.book.current == "cool" and run.control.values()["layers.base.solid.red"] != 0.5
    path.write_text(json.dumps({"version": 4, "looks": {}}))
    with pytest.raises(SystemExit, match=r"looks.json: the looks file holds no look$"):
        build(["run", str(path)])


def test_a_look_the_map_cannot_run_is_refused_with_a_map_that_can(tmp_path):
    path = tmp_path / "tide.look.json"
    path.write_bytes((EXAMPLE_LOOKS / "tide.look.json").read_bytes())
    with pytest.raises(SystemExit, match=r"cannot start look 'tide': .*needs a map of 2 or 3 dimensions.*; run with "
                       "--map grid:16x16 or --map lattice:8$"):
        build(["run", str(path), "--map", "line:8", "--ddp", "10.0.0.11=0+8", "--dry-run"])


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
    status = status_line(("render", renderer))
    # Testing the attribute and then formatting it would return the string
    # "None" here: truthy on the first read, gone on the second.
    assert status() == ("render", "boom", None)
    assert renderer.reads == 1


def test_run_announces_the_preview_url(capsys):
    rc, _ = run_main(["run", looks_file(), "--map", "line:8", "--frames", "1", "--preview", "--port", "0"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "preview at http://127.0.0.1:" in err  # port 0 -> whatever we bound
    assert "http://127.0.0.1:0/" not in err  # the real port, not the request


def test_a_preview_that_cannot_listen_leaves_the_room_running_and_tries_again(audit_log, recorder, capsys,
                                                                             monkeypatch):
    """A held port (or a router not up at login) is no traceback and
    no dark room: DDP streams, and the page comes up once the port frees."""
    monkeypatch.setattr(run_module, "PREVIEW_RETRY_S", 0.01)
    with socket.socket() as held:
        held.bind(("127.0.0.1", 0))
        held.listen()
        port = held.getsockname()[1]
        argv = ["run", looks_file(), "--map", "line:8", "--ddp", "127.0.0.1=0+8", "--preview", "--port", str(port)]
        assert run_main([*argv, "--frames", "3"])[0] == 0
        assert recorder.sent  # the boards got frames
        assert f"preview: cannot listen on 127.0.0.1:{port} (Address already in use); the aura runs on" in (
            capsys.readouterr().err)
        run = build(argv)
        run._start_preview()
    wait_until(lambda: run.preview.port == port)
    run._stopping.set()
    run.preview_retry.join()
    run.preview.stop()
    assert f"preview at http://127.0.0.1:{port}/" in capsys.readouterr().err


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
    rc, out = run_main(["run", looks_file(), "--map", "line:8", "--frames", "3"], ansi_stream=term)
    assert rc == 0
    assert "TRACEBACK" in out  # deferred, never dropped
    # ...and only after the sink restored the cursor and released the terminal.
    assert out.index("\x1b[?25h") < out.index("TRACEBACK")
    assert "\x1b[?25l" in out  # this really was the interactive path


def test_cli_logging_leaves_no_handler_behind():
    root = logging.getLogger("pewpew")
    before = list(root.handlers)
    run_main(["run", looks_file(), "--map", "line:8", "--frames", "1"])
    run_main(["run", looks_file(), "--map", "line:8", "--frames", "1"])
    assert root.handlers == before  # repeated in-process runs must not stack


def test_ctrl_c_ends_the_run_through_the_whole_teardown(recorder, monkeypatch):
    """Ctrl-C is how a run ends from the terminal: exit 0, with the outputs
    stopped as at the end of `--frames`."""

    def interrupted(self, x, y, z, index):
        raise KeyboardInterrupt

    monkeypatch.setattr(ProgramPattern, "render", interrupted)
    try:
        rc, _ = run_main(["run", looks_file(), "--map", "line:4", "--frames", "100", "--ddp", "127.0.0.1=0+4"])
    except KeyboardInterrupt:
        pytest.fail("Ctrl-C escaped the run")
    assert rc == 0
    assert recorder.sent == [] and recorder.closed == 1  # the DDP sink stopped and closed its socket


def test_status_prefers_the_reload_error_over_the_pattern_error():
    class Src:
        def __init__(self, error):
            self.error = error

    def status(reload, render):
        return status_line(("reload", Src(reload)), ("render", Src(render)))()

    assert status("reload failed", "render raised")[:2] == ("reload", "reload failed")
    assert status(None, "render raised")[:2] == ("render", "render raised")
    assert status(None, None) is None


def test_dry_run_prints_the_plan_and_sends_nothing(audit_log, recorder, capsys):
    argv = ["run", looks_file(), "--map", "line:3840", "--dry-run"]
    for i in range(3):
        argv += ["--ddp", f"10.0.0.1{i + 1}={1280 * i}+1280"]
    assert run_main(argv)[0] == 0
    out = capsys.readouterr().out
    assert "nothing sent" in out
    assert "ddp 10.0.0.12:4048  pixels 1280-2559 (1280)  3 packets/frame  154,800 B/s at 40 fps" in out
    assert recorder.sent == []
    assert not audit_log.exists()


@pytest.mark.parametrize(
    "looks, message",
    [
        ("{old}", "looks file is version 1; this pewpew reads version 4"),
        ("{folder}", r"folder: cannot read the looks file: Is a directory$"),
        ("{unknown}", r"look 'look': layers.base.nope: unknown op 'nope'"),
    ],
)
def test_dry_run_refuses_what_a_launch_would(looks, message, tmp_path, recorder):
    old = tmp_path / "looks.json"
    old.write_text(json.dumps({"version": 1, "looks": {}}))
    (tmp_path / "folder").mkdir()
    looks = looks.format(old=old, folder=tmp_path / "folder", unknown=unknown_op(tmp_path))
    with pytest.raises(SystemExit, match=message):
        run_main(["run", looks, "--map", "line:8", "--ddp", "10.0.0.11=0+8", "--dry-run"])
    assert recorder.sent == []


def test_real_run_audits_first_then_streams(audit_log, recorder, capsys):
    argv = ["run", looks_file(), "--map", "line:8", "--frames", "3", "--ddp", "127.0.0.1:4049=0+8",
            "--ddp-fps", "50"]
    assert run_main(argv)[0] == 0
    assert len(recorder.sent) == 3  # one packet per frame, last frame drained
    assert {addr for _, addr in recorder.sent} == {("127.0.0.1", 4049)}
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["action"] == "ddp-stream"
    assert entry["argv"] == argv
    assert entry["targets"] == ["127.0.0.1:4049=0+8"]
    assert entry["fps"] == 50.0
    assert entry["utc"].endswith("+00:00")
    # DDP alone does not take over the terminal; the plan goes to stderr.
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "audit record appended" in captured.err


def test_ddp_rate_is_capped_by_the_loop_rate(audit_log, recorder, capsys):
    base = ["run", looks_file(), "--map", "line:8", "--fps", "30", "--ddp", "127.0.0.1=0+8", "--ddp-fps", "60"]
    assert run_main([*base, "--dry-run"])[0] == 0
    assert "at 30 fps" in capsys.readouterr().out
    assert run_main([*base, "--frames", "2"])[0] == 0
    [entry] = [json.loads(s) for s in audit_log.read_text().splitlines()]
    assert entry["fps"] == 30.0


@pytest.mark.parametrize("flag, value, message", [
    ("--fps", "0", "argument --fps: expected a rate in frames per second above 0, got '0'"),
    ("--ddp-fps", "0", "argument --ddp-fps: expected a rate in frames per second above 0, got '0'"),
    ("--trigger-log-max", "nan", "argument --trigger-log-max: expected megabytes above 0, got 'nan'"),
    ("--watchdog", "-1", "argument --watchdog: expected seconds, or 0 for off, got '-1'"),
    ("--watchdog", "inf", "argument --watchdog: expected seconds, or 0 for off, got 'inf'"),
    ("--port", "70000", "argument --port: expected a port from 0 to 65535, got '70000'"),
    ("--seed", "-1", "argument --seed: expected a seed, a whole number of at least 0, got '-1'"),
    ("--frames", "-5", "argument --frames: expected a frame count, a whole number of at least 1, got '-5'"),
    ("--frames", "0", "argument --frames: expected a frame count, a whole number of at least 1, got '0'"),
    ("--map", "line:0", "argument --map: expected line:64, grid:16x16 or lattice:8, sizes at least 1; got 'line:0'"),
    ("--map", "grid:0x4", "sizes at least 1; got 'grid:0x4'"),
    ("--map", "lattice:0", "sizes at least 1; got 'lattice:0'"),
    ("--map", "grid:4", "sizes at least 1; got 'grid:4'"),
])
def test_a_bad_value_is_a_usage_error_naming_its_flag(flag, value, message, capsys):
    assert message in usage_error(["run", looks_file(), "--map", "line:8", "--frames", "1", flag, value], capsys)


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--ddp", "10.0.0.11=0+9"], "do not fit the 8-pixel map"),
        (["--ddp", "10.0.0.11=0+4", "--ddp", "10.0.0.12=3+4"], "overlap"),
        (["--ddp", "10.0.0.11=0"], "bad DDP target"),
        (["--ddp", "lights.example.com=0+4"], "'lights.example.com' is not an IPv4 address or an mDNS name"),
    ],
)
def test_cli_rejects_bad_targets_with_one_line(extra, message, audit_log, recorder):
    with pytest.raises(SystemExit, match=message) as exc:
        run_main(["run", looks_file(), "--map", "line:8", "--dry-run", *extra])
    assert "\n" not in str(exc.value)
    assert recorder.sent == []
    assert not audit_log.exists()


def test_a_dry_run_with_nothing_to_stream_is_a_usage_error(capsys, audit_log):
    assert "--dry-run needs at least one --ddp target, a --room or --audio net:NODE" in usage_error(
        ["run", looks_file(), "--map", "line:8", "--dry-run"], capsys)
    assert not audit_log.exists()


# -- the control page: --host, master, blackout ------


def test_host_reaches_the_server_and_the_url_line(monkeypatch, capsys):
    """`--host` is what the server binds. The real bind here is loopback (a
    test must not listen on a LAN); the recorded address proves the wiring."""
    bound = []
    real_serve = preview.serve

    def serve(handler, host, port, **kw):
        bound.append(host)
        return real_serve(handler, "127.0.0.1", port, **kw)

    monkeypatch.setattr(preview, "serve", serve)
    rc, _ = run_main(["run", looks_file(), "--map", "line:8", "--frames", "1", "--preview", "--port", "0",
                      "--host", "10.0.0.2"])
    assert rc == 0 and bound == ["10.0.0.2"]
    assert "preview at http://10.0.0.2:" in capsys.readouterr().err
    assert "a phone on the same network" in preview_url("10.0.0.2", 7447)
    assert "every interface" in preview_url("0.0.0.0", 7447)
    assert preview_url("127.0.0.1", 7447) == "preview at http://127.0.0.1:7447/"


def test_the_preview_url_brackets_ipv6_and_knows_localhost_is_loopback():
    assert preview_url("localhost", 7447) == "preview at http://localhost:7447/"
    assert preview_url("::1", 7447) == "preview at http://[::1]:7447/"
    assert preview_url("fd00::2", 7447) == "preview at http://[fd00::2]:7447/ (a phone on the same network opens this)"
    assert "every interface" in preview_url("::", 7447)


@pytest.mark.parametrize("flag", [["--host", "10.0.0.2"], ["--port", "0"], ["--accept-looks"]])
def test_host_and_port_need_the_preview(flag, capsys):
    assert f"{flag[0]} only applies with --preview" in usage_error(
        ["run", looks_file(), "--map", "line:8", "--frames", "1", *flag], capsys)


def test_a_run_takes_looks_only_when_asked_and_never_an_unattended_run(capsys):
    """`--accept-looks` lets any client of the preview change the look, so
    only a run that asks offers `look`, and an unattended run refuses the flag
    (ADR-020 amendment "capabilities")."""
    argv = ["run", looks_file(), "--map", "line:8", "--frames", "1", "--preview", "--port", "0"]
    assert build(argv).control.capabilities == ()
    assert build([*argv, "--accept-looks"]).control.capabilities == ("look",)
    assert "--accept-looks lets any client of the preview change the look, which --unattended refuses" in (
        usage_error([*argv, "--accept-looks", "--unattended"], capsys))


def test_the_preview_flag_takes_no_value_so_it_never_swallows_the_looks_file():
    path = looks_file()
    run_ = build(["run", "--preview", path, "--map", "line:8", "--frames", "1"])
    assert str(run_.args.looks) == path and run_.args.port == 7447


@pytest.mark.parametrize("cap", ["0", "1.5", "-0.1", "nan", "bright"])
def test_the_master_cap_must_be_above_0_and_at_most_1(cap, capsys):
    assert "argument --master-cap: expected a number above 0 and at most 1" in usage_error(
        ["run", looks_file(), "--map", "line:8", "--frames", "1", "--master-cap", cap], capsys)


@pytest.mark.parametrize("extra, chain, scale", [
    (["--master-cap", "0.5"], TRAIL, 0.5),
    ([], 'osc(3, 0.2).trails(2.0).palette("ember")', 1.0),
], ids=["master-cap", "args"])
def test_the_boards_receive_the_render_of_the_args_dimmed_by_the_master(extra, chain, scale, recorder):
    start = expr.look(expr.layer("base", program_of(chain)))
    argv = ["run", looks_file(start), "--map", "line:8", "--frames", "3", "--fps", "60",
            "--ddp-fps", "60", "--ddp", "127.0.0.1=0+8", *extra]
    assert run_main(argv)[0] == 0
    # The look runs its layer `base`, seeded from the look's own seed.
    made = frames(hosted(program_of(chain), line(8), seed=layer_seed(0, "base")), 3)
    want = [to_linear_u8(f * np.float32(scale)).tobytes() for f in made]
    assert [data[ddp.HEADER_LEN:] for data, _ in recorder.sent] == want


def test_master_scales_sink_output_without_touching_the_render():
    """The master multiplies the copy the sinks get. The program keeps a
    trail, so a product written back into the renderer's frame would change
    every later frame; the undimmed sequence must stay what a lone renderer
    gives."""

    renderer = hosted(program_of(TRAIL))
    master = Master()
    seen = []
    ft = FakeTime()
    loop = PacedLoop(renderer, fps=60.0, after=[master.apply], on_frame=[lambda t, f: seen.append(f)],
                     now=ft.now, sleep=ft.sleep)
    loop.run(frames=4)
    loop.calls.call_soon(lambda: master.set(0.25))
    loop.run(frames=4)
    loop.calls.call_soon(lambda: master.set_blackout(True))
    loop.run(frames=2)
    ref = frames(hosted(program_of(TRAIL)), 10)
    for i, frame in enumerate(seen):
        scale = 1.0 if i < 4 else 0.25 if i < 8 else 0.0
        assert np.array_equal(frame, ref[i] * np.float32(scale)), i
        assert not frame.flags.writeable


def test_boards_lists_what_the_sweep_found(monkeypatch, capsys):
    import pewpew.wled

    asked = []
    info = {"mac": "020000000001", "name": "pewpew-1", "ver": "16.0.1", "live": True, "lm": "DDP",
            "lip": "192.0.2.10", "leds": {"count": 60, "fps": 40}, "wifi": {"rssi": -60}, "freeheap": 90000}

    def fetch(host, timeout):
        asked.append(host)
        if host != "192.0.2.20":
            raise OSError("no answer")
        return info

    monkeypatch.setattr(pewpew.wled, "sender_address", lambda host, port=0: "192.0.2.10")
    monkeypatch.setattr(pewpew.wled, "fetch_info", fetch)
    assert main(["boards", "scan"]) == 0
    assert len(asked) == 253 and "192.0.2.10" not in asked  # this laptop's /24, less itself
    out = capsys.readouterr()
    assert out.out.splitlines() == [
        "192.0.2.20       pewpew-1          MAC 02:00:00:00:00:01  WLED 16.0.1  live DDP from 192.0.2.10"
    ]
    assert main(["boards", "scan", "--json"]) == 0
    fleet = json.loads(capsys.readouterr().out)
    (board,) = fleet["boards"]
    assert fleet["subnet"] == "192.0.2.0/24" and board["address"] == "192.0.2.20"
    assert (board["count"], board["rssi"], board["level"], board["reasons"], board["fix"]) == (60, -60, "ok", [], None)
    assert main(["boards", "scan", "--subnet", "10.0.0.0/24"]) == 1
    assert "no WLED board answered in 10.0.0.0/24" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["boards", "scan", "--subnet", "10.0.0.0/8"])


# ---- unattended safety: --armed, the watchdog, the sleep assertion, health ----------


def test_armed_arms_the_triggers_at_the_first_tick(tmp_path):
    log = tmp_path / "events.jsonl"
    argv = ["run", looks_file(), "--map", "line:8", "--frames", "2", "--armed", "--trigger-log", str(log)]
    assert run_main(argv)[0] == 0
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        {"run": {"seed": 0, "fps": 60.0, "look": "look", "armed": True}},
        {"tick": 0, "t": 1 / 60, "source": "launch", "arm": True},
    ]


def test_triggers_start_disarmed_without_armed(tmp_path):
    log = tmp_path / "events.jsonl"
    assert run_main(["run", looks_file(), "--map", "line:8", "--frames", "2", "--trigger-log", str(log)])[0] == 0
    assert [json.loads(line).get("run", {}).get("armed") for line in log.read_text().splitlines()] == [False]


def test_an_unattended_run_holds_the_sleep_assertion_and_arms_the_watchdog():
    unattended = build(["run", looks_file(), "--map", "line:8", "--frames", "3", "--unattended"])
    assert unattended.awake is not None and unattended.awake.args[:4] == ["caffeinate", "-i", "-s", "-w"]
    assert unattended.watchdog is not None and unattended.watchdog.timeout == 5.0
    assert unattended.serve() == 0
    assert unattended.awake.state()["held"] is False and not unattended.watchdog.fired  # released at the end

    dev = build(["run", looks_file(), "--map", "line:8", "--frames", "1", "--preview", "--port", "0"])
    assert dev.awake is None and dev.watchdog is None  # a dev run holds neither
    held = build(["run", looks_file(), "--map", "line:8", "--frames", "1", "--keep-awake", "--watchdog", "2"])
    assert held.awake is not None and held.watchdog is not None and held.watchdog.timeout == 2.0
    held.watchdog.stop()  # armed as the run was built; it is never served
    off = build(["run", looks_file(), "--map", "line:8", "--frames", "1", "--unattended", "--watchdog", "0"])
    assert off.watchdog is None and off.monitor is not None and off.monitor.state()["loop"]["watchdog"] is None


def test_keep_awake_alone_gets_a_monitor_that_restarts_caffeinate():
    run_ = build(["run", looks_file(), "--map", "line:8", "--frames", "1", "--keep-awake"])
    assert run_.monitor is not None and run_.monitor.state()["awake"]["requested"] is True


def test_the_health_monitor_polls_the_ddp_boards(recorder):
    run_ = build(["run", looks_file(), "--map", "line:8", "--frames", "3", "--ddp", "127.0.0.1:4049=0+8"])
    assert run_.monitor is not None
    run_.monitor.step()
    assert [b["host"] for b in run_.monitor.state()["boards"]] == ["127.0.0.1"]
    assert run_.serve() == 0
    assert run_.monitor._thread is not None and not run_.monitor._thread.is_alive()  # stopped with the run


# ---- an arrangement map and the power limit ---------------------------------------

GOLDEN_RINGS = EXAMPLES / "golden-rings.json"


def test_run_accepts_an_arrangement_map(capsys):
    rc, out = run_main(["run", looks_file(), "--map", str(GOLDEN_RINGS), "--frames", "1"])
    assert rc == 0 and "\x1b[38;2;" in out
    assert "warning: connector/clen-4pin.rated_a = 4.0 is assumed" in capsys.readouterr().err
    launch = build(["run", looks_file(), "--map", str(GOLDEN_RINGS), "--frames", "1"]).launch
    assert len(launch.mapping) == 3072


def test_run_reports_a_bad_arrangement(tmp_path):
    with pytest.raises(SystemExit, match="no such file"):
        main(["run", looks_file(), "--map", str(tmp_path / "missing.json"), "--frames", "1"])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"format": "pewpew.arrangement", "version": 1, "fixtures": [{"id": "x", "type": "no-such-bar"}]}
    ))
    with pytest.raises(SystemExit, match="no fixture type 'no-such-bar'"):
        main(["run", looks_file(), "--map", str(bad), "--frames", "1"])


def test_run_reports_an_unreadable_or_empty_arrangement(tmp_path):
    (tmp_path / "dir.json").mkdir()
    with pytest.raises(SystemExit, match="cannot read the file: is a directory"):
        main(["run", looks_file(), "--map", str(tmp_path / "dir.json"), "--frames", "1"])
    latin1 = tmp_path / "latin1.json"
    latin1.write_bytes(b'{"name": "\xe9"}')
    with pytest.raises(SystemExit, match="not UTF-8"):
        main(["run", looks_file(), "--map", str(latin1), "--frames", "1"])
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"format": "pewpew.arrangement", "version": 1}))
    with pytest.raises(SystemExit, match="has no pixels"):
        main(["run", looks_file(), "--map", str(empty), "--frames", "1"])


def test_a_run_on_any_other_map_never_imports_the_rig_stack():
    # A subprocess, so imports made by other tests cannot mask the result.
    code = (
        "import io, sys\n"
        "from pewpew.__main__ import main\n"
        f"rc = main(['run', {looks_file()!r}, '--map', 'line:8', '--frames', '1'], "
        "ansi_stream=io.StringIO())\n"
        "assert rc == 0\n"
        f"rc = main(['run', {looks_file()!r}, '--frames', '1'], ansi_stream=io.StringIO())\n"
        "assert rc == 0\n"
        "bad = [m for m in ('pewpew.rig', 'pydantic', 'pewpew.studio.app') if m in sys.modules]\n"
        "assert not bad, bad\n"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_a_failing_rig_compile_cannot_break_a_run_on_another_map(monkeypatch):
    import pewpew.rig

    def boom(*args, **kwargs):
        raise RuntimeError("rig compile broke")

    monkeypatch.setattr(pewpew.rig, "compile_rig", boom)
    assert run_main(["run", looks_file(), "--map", "line:8", "--frames", "1"])[0] == 0
    with pytest.raises(RuntimeError, match="rig compile broke"):
        run_main(["run", looks_file(), "--map", str(GOLDEN_RINGS), "--frames", "1"])


def _colors(out: str) -> set[str]:
    return set(re.findall(r"\x1b\[38;2;(\d+;\d+;\d+)m", out))


def test_max_brightness_caps_every_frame_before_the_sink():
    _, lit = run_main(["run", looks_file(), "--map", "line:8", "--frames", "1"])
    rc, dark = run_main(["run", looks_file(), "--map", "line:8", "--frames", "1", "--max-brightness", "0"])
    assert rc == 0 and _colors(lit) != {"0;0;0"} and _colors(dark) == {"0;0;0"}


def test_an_arrangement_cap_applies_and_each_flag_replaces_its_value(tmp_path):
    data = json.loads(GOLDEN_RINGS.read_text())
    capped = tmp_path / "capped.json"
    capped.write_text(json.dumps({**data, "power": {"max_brightness": 0.0, "max_watts": 500}}))
    _, dark = run_main(["run", looks_file(), "--map", str(capped), "--frames", "1"])
    assert _colors(dark) == {"0;0;0"}
    _, lit = run_main(["run", looks_file(), "--map", str(capped), "--frames", "1", "--max-brightness", "1"])
    assert _colors(lit) != {"0;0;0"}


def test_the_power_limit_runs_after_the_master():
    """Architecture §2 stage 3: the master dims, then the limit caps what is left."""
    run = build(["run", looks_file(), "--map", str(GOLDEN_RINGS), "--max-watts", "50", "--frames", "1"])
    assert run.launch.limiter is not None
    run.master.set(0.5)
    frame = np.ones((3072, 3), np.float32)
    stages = run.loop._after
    assert stages[0] == run.master.apply and len(stages) == 2
    out = stages[1](0.0, stages[0](0.0, frame))
    watts = run.launch.limiter.model.watts(out)  # type: ignore[union-attr]
    assert watts == pytest.approx(50.0, rel=1e-3) and (frame == 1.0).all()


def test_bad_power_flags_are_refused(capsys):
    assert "--max-watts needs --map with an arrangement .json" in usage_error(
        ["run", looks_file(), "--map", "line:8", "--frames", "1", "--max-watts", "100"], capsys)
    assert "argument --max-brightness: expected a number from 0 to 1, got '1.5'" in usage_error(
        ["run", looks_file(), "--map", "line:8", "--frames", "1", "--max-brightness", "1.5"], capsys)
    assert "argument --max-watts: expected watts above 0, got '0'" in usage_error(
        ["run", looks_file(), "--map", str(GOLDEN_RINGS), "--frames", "1", "--max-watts", "0"], capsys)
    with pytest.raises(SystemExit, match="bad power cap: max_watts must be over 0 and at most"):
        main(["run", looks_file(), "--map", str(GOLDEN_RINGS), "--frames", "1", "--max-watts", "1e7"])


def test_studio_serves_its_app_with_the_message_cap(monkeypatch, tmp_path):
    uvicorn = pytest.importorskip("uvicorn")
    from pewpew.studio.limits import MAX_BODY_BYTES

    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setenv("PEWPEW_STUDIO_DB", "restored after the test")
    db = tmp_path / "share.sqlite3"
    assert main(["studio", "--port", "8010", "--db", str(db)]) == 0
    (app,), kw = calls[0]
    assert app == "pewpew.studio.app:create_app" and kw["factory"] and kw["ws_max_size"] == MAX_BODY_BYTES == 262144
    assert kw["timeout_graceful_shutdown"] == 30
    assert (kw["host"], kw["port"]) == ("127.0.0.1", 8010)
    assert os.environ["PEWPEW_STUDIO_DB"] == str(db)


def test_studio_without_db_keeps_the_db_path_from_the_environment(monkeypatch):
    uvicorn = pytest.importorskip("uvicorn")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: None)
    monkeypatch.setenv("PEWPEW_STUDIO_DB", "/data/studio.sqlite3")
    assert main(["studio"]) == 0
    assert os.environ["PEWPEW_STUDIO_DB"] == "/data/studio.sqlite3"
