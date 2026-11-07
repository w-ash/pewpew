"""The command line: `python -m pewpew run|studio|wifi|boards|observe|push|fx|verify|audio|mcp`.

`run` plays a looks file live to one or more sinks (`pewpew.run`), `studio`
serves the 3D studio (`pewpew.studio`, the `studio` extra), `wifi` sets up
a new WLED board over USB serial (`pewpew.provision`),
`boards scan|backup|restore` finds the boards and saves and restores their
config (`pewpew.boards`), `observe` watches a running engine's preview
and measures what it shows, read-only (`pewpew.remote.observe`), `push`
sends a look to an engine on this machine (tier 1, `pewpew.remote.control`),
`fx catalog|show` lists what a look can be made of (`pewpew.fx.cli`), and
the other `fx` verbs and `verify looks` check, render and gate looks
offline (`pewpew.lab.cli`), `audio analyse` reports the tempo, beats and
levels of a WAV file (`pewpew.audio.cli`), and `mcp` serves these tools to
an AI agent (`pewpew.mcp_cli`).
Each module adds its own subcommand (`add_parser`) and its handler
(`set_defaults(cli=...)`); `run` alone is served here. `run --help` lists
the options, and docs/authoring.md and docs/unattended-checklist.md show their
use.

An option the others rule out is a usage error (exit 2, through argparse);
a launch refused at run time is one line on stderr (exit 1).
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from pewpew import boards, mcp_cli, provision, studio
from pewpew.audio import cli as audio_cli
from pewpew.audio.inputs import NET, REPLAY
from pewpew.cli_args import add_allow_host, number, parsed_by, port, positive, whole
from pewpew.fx import cli as fx_cli
from pewpew.lab import cli as lab_cli
from pewpew.mapping import DEFAULT_MAP, parse_map
from pewpew.reload import Watch
from pewpew.remote import control as remote_control
from pewpew.remote import observe
from pewpew.run import Launch, Run
from pewpew.watchdog import TIMEOUT_S as WATCHDOG_S

if TYPE_CHECKING:
    import numpy as np

PREVIEW_PORT = 7447


def main(
    argv: list[str] | None = None,
    *,
    ansi_stream: TextIO | None = None,
    now: Callable[[], float] = time.perf_counter,
    sleep: Callable[[float], None] = time.sleep,
    watch: Watch | None = None,
) -> int:
    args = parse(argv)
    record = sys.argv[1:] if argv is None else list(argv)  # what the audit log records
    if args.cmd != "run":
        return args.cli(args, record)  # each other command's own handler (`set_defaults(cli=...)`)
    launch = Launch.read(args, record, now=now, sleep=sleep)
    if args.dry_run:
        print("dry run: nothing sent", *launch.plan(), sep="\n")
        return 0
    return Run(launch, ansi_stream=ansi_stream, now=now, sleep=sleep, watch=watch).serve()


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """The command line, with every option combination checked; a bad one
    is a usage error that exits 2."""
    parser = _parser()
    args = parser.parse_args(argv)
    problem = _conflict(args)
    if problem is not None:
        parser.error(problem)
    if args.cmd == "run" and args.preview and args.port is None:
        args.port = PREVIEW_PORT
    return args


def _conflict(args: argparse.Namespace) -> str | None:
    """Why the options rule each other out, or None."""
    if args.cmd == "wifi":
        return "--keychain needs --ssid" if args.keychain and not args.ssid else None
    if args.cmd == "mcp":
        return mcp_cli.conflict(args)
    if args.cmd != "run":
        return None
    if not args.preview:
        for flag, given in (("--host", args.host is not None), ("--port", args.port is not None),
                            ("--accept-looks", args.accept_looks)):
            if given:
                return f"{flag} only applies with --preview"
    if args.accept_looks and args.unattended:
        return "--accept-looks lets any client of the preview change the look, which --unattended refuses"
    if (problem := _audio_conflict(args)) is not None:
        return problem
    if args.max_watts is not None and not isinstance(args.map, Path):
        return "--max-watts needs --map with an arrangement .json, whose fixtures give the power model"
    if args.room is None:
        if args.no_ddp:
            return "--no-ddp only applies with --room"
        if args.dry_run and not args.ddp and not (args.audio or "").startswith(NET):
            return f"--dry-run needs at least one --ddp target, a --room or --audio {NET}NODE"
        return None
    for flag, given in (("--map", args.map is not None), ("--ddp", bool(args.ddp))):
        if given:
            return f"--room supplies the mapping and the DDP boards; drop {flag}"
    if args.ansi:
        return "--ansi cannot draw a room map; use --preview"
    if args.no_ddp and args.dry_run:
        return "--dry-run prints the DDP plan, which --no-ddp turns off"
    if args.no_ddp and not args.preview:
        return "--room --no-ddp sends nothing to the boards; add --preview to see it"
    return None


def _audio_conflict(args: argparse.Namespace) -> str | None:
    """Why the audio options rule each other out, or None."""
    node = (args.audio or "").startswith(NET)
    if args.allow_hosts and not node:
        return f"--allow-host only applies with --audio {NET}NODE, a capture node"
    if args.allow_hosts and args.unattended:
        return "--allow-host names a bench node; an unattended run (--unattended) subscribes to its node without it"
    if node and args.audio_channel is not None:
        return "--audio-channel does not apply to a capture node, which sends one channel, the mean of its two"
    for flag, given in (("--audio-delay", args.audio_delay != 0.0), ("--audio-channel", args.audio_channel is not None),
                        ("--feature-log", args.feature_log is not None)):
        if given and args.audio is None:
            return f"{flag} needs --audio: without it the features are simulated"
        if given and args.audio.startswith(REPLAY):
            return f"{flag} needs an analysed input; --audio {REPLAY}... plays logged features back as they were"
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pewpew")
    sub = parser.add_subparsers(dest="cmd", required=True, metavar="COMMAND")
    run = sub.add_parser("run", help="play a looks file live to one or more sinks")

    looks = run.add_argument_group("the looks")
    looks.add_argument("looks", type=Path, metavar="LOOKS",
                       help="a looks file, version 4 (a .look.json file is one): the run starts in its current "
                       "look, and the page's saves go to it (docs/authoring.md)")
    looks.add_argument("--seed", type=whole(0, "a seed"), default=0,
                       help="seeds the stand-in features and the looks made in the run (default 0); each look's "
                       "own seed seeds its layers")

    where = run.add_argument_group("the geometry")
    where.add_argument("--map", type=parsed_by(_map_spec), default=None, metavar="SPEC",
                       help="line:64, grid:16x16, lattice:8 or an arrangement .json "
                       f"(default {DEFAULT_MAP})")
    where.add_argument("--room", type=Path, default=None, metavar="PATH",
                       help="room map file: the mapping and the DDP boards, reloaded on save")

    out = run.add_argument_group("the outputs")
    out.add_argument("--ansi", action="store_true", help="terminal sink (the default sink)")
    out.add_argument("--preview", action="store_true", help="browser preview and control page")
    out.add_argument("--port", type=port, default=None, metavar="PORT",
                     help=f"the preview's port; 0 picks a free one (default {PREVIEW_PORT})")
    out.add_argument("--host", default=None, metavar="ADDR",
                     help="the preview's address (default 127.0.0.1); the private router's side for a phone")
    out.add_argument("--accept-looks", action="store_true",
                     help="let a client of the preview send a whole look (`python -m pewpew push`); "
                     "never with --unattended")
    out.add_argument("--ddp", action="append", default=[], metavar="HOST=START+COUNT",
                     help="stream DDP to a WLED board (HOST or HOST:PORT, HOST an IPv4 address or NAME.local); "
                     "repeat once per board")
    out.add_argument("--no-ddp", action="store_true", help="with --room: simulate only, send nothing to the boards")
    out.add_argument("--ddp-fps", type=positive("a rate in frames per second"), default=40.0, metavar="FPS",
                     help="DDP output rate, at most --fps (default 40)")
    out.add_argument("--dry-run", action="store_true", help="print the DDP plan and exit without sending")
    out.add_argument("--max-brightness", type=_fraction, default=None, metavar="B",
                     help="power limit: a ceiling on light output, 0 to 1, after the master "
                     "(default: the arrangement's, else 1)")
    out.add_argument("--max-watts", type=positive("watts"), default=None, metavar="W",
                     help="power limit: hold the estimated draw at W watts; needs an arrangement --map "
                     "(default: the arrangement's, else none)")

    aura = run.add_argument_group("the aura")
    aura.add_argument("--unattended", action="store_true",
                      help="an unattended run: hold a sleep assertion, arm the loop watchdog, and leave a failing "
                      "layer out of the mix")
    aura.add_argument("--keep-awake", action="store_true",
                      help="hold a sleep assertion (caffeinate) while running; --unattended implies it")
    aura.add_argument("--watchdog", type=_seconds_or_off, default=None, metavar="SECONDS",
                      help=f"exit with code 70 when no frame completes for SECONDS, so launchd restarts the aura; "
                      f"0 is off (default {WATCHDOG_S:g} with --unattended, else off)")
    aura.add_argument("--master-cap", type=positive("a number", most=1.0), default=1.0, metavar="CAP",
                      help="cap on the master dimmer, above 0 and at most 1 (default 1); the page cannot exceed it")
    aura.add_argument("--armed", action="store_true",
                      help="start with the room-event triggers armed (default: disarmed until the page arms them)")
    aura.add_argument("--trigger-log", type=Path, default=None, metavar="PATH",
                      help="append every room event, fired or dropped, to PATH as JSONL (default: no log)")
    aura.add_argument("--trigger-log-max", type=positive("megabytes"), default=50.0, metavar="MB",
                      help="stop the trigger log once its file would pass MB megabytes (default 50)")

    audio = run.add_argument_group("the audio")
    audio.add_argument("--audio", default=None, metavar="SPEC",
                       help="the sound the features come from: one of this computer's inputs by its name as "
                       "`audio list` prints it (a line-in or a microphone; needs pewpew[audio]), "
                       f"{NET}NODE (a capture node by its name or IPv4 address), FILE.wav "
                       f"(analysed, on a loop) or {REPLAY}PATH.jsonl (a feature log played back); "
                       "default: simulated features")
    add_allow_host(audio, f"with --audio {NET}NODE outside --unattended: subscribe to the capture node only at IP, a "
                   "bench node; repeat per address (subscribing is tier 1)")
    audio.add_argument("--audio-channel", type=whole(0, "a channel, numbered from 0"), default=None, metavar="N",
                       help="read only channel N of the input or the WAV file, numbered from 0 "
                       "(default: the mean of all its channels)")
    audio.add_argument("--audio-delay", type=_milliseconds, default=0.0, metavar="MS",
                       help="how much later the room hears the sound than pewpew does, such as a Bluetooth "
                       "speaker's delay: delays the levels and moves the beat (default 0; may be negative)")
    audio.add_argument("--feature-log", type=Path, default=None, metavar="PATH",
                       help="append each frame's features to PATH as JSONL, for replay:PATH (default: no log; "
                       "a microphone's log is close to a speech recording, so never with people in the room)")
    audio.add_argument("--feature-log-hours", type=positive("hours"), default=1.0, metavar="HOURS",
                       help="stop the feature log after HOURS of the run (default 1, about 90 MB at 60 fps)")

    loop = run.add_argument_group("the loop")
    loop.add_argument("--fps", type=positive("a rate in frames per second"), default=60.0,
                      help="the render loop's rate (default 60)")
    loop.add_argument("--frames", type=whole(1, "a frame count"), default=None, metavar="N",
                      help="stop after N frames (default: run until ^C)")

    studio.add_parser(sub)
    provision.add_parser(sub)
    boards.add_parser(sub)
    observe.add_parser(sub)
    remote_control.add_parser(sub)
    lab_cli.add_parser(sub, fx_cli.add_parser(sub))
    audio_cli.add_parser(sub)
    mcp_cli.add_parser(sub)
    return parser


def _seconds_or_off(text: str) -> float:
    """argparse type for `--watchdog`: seconds above 0, or 0 for off."""
    value = number(text)
    if not (math.isfinite(value) and value >= 0.0):
        raise argparse.ArgumentTypeError(f"expected seconds, or 0 for off, got {text!r}")
    return value


def _milliseconds(text: str) -> float:
    """argparse type for `--audio-delay`: a finite number of milliseconds, of at most 10 s either way."""
    value = number(text)
    if not (math.isfinite(value) and abs(value) <= 10_000.0):
        raise argparse.ArgumentTypeError(f"expected milliseconds from -10000 to 10000, got {text!r}")
    return value


def _map_spec(spec: str) -> np.ndarray | Path:
    """The `--map` value: the path of an arrangement `.json`, which
    `pewpew.run.rig_map` compiles, or a synthetic mapping (`parse_map`)."""
    return Path(spec) if spec.endswith(".json") else parse_map(spec)


def _fraction(text: str) -> float:
    """argparse type for `--max-brightness`: a number from 0 to 1."""
    value = number(text)
    if not (0.0 <= value <= 1.0):
        raise argparse.ArgumentTypeError(f"expected a number from 0 to 1, got {text!r}")
    return value


if __name__ == "__main__":
    sys.exit(main())
