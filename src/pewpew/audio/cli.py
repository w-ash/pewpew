"""The `audio` command group: what pewpew hears in a sound file, what it
can hear on this computer and from the capture nodes on its network, and
a node's key.

    audio analyse FILE [--json] [--fps FPS] [--sensitivity S] [--feature-log PATH]
    audio list [--json] [--subnet CIDR]
    audio key MAC [--dry-run]

Tier 0 (CLAUDE.md T-7): `list` names this computer's inputs as PortAudio
lists them, and opens none; `run --audio NAME` takes a name exactly as it
prints it (pewpew.audio.device). The inputs need pewpew[audio]: without
it, `list` says how to install it, lists only the nodes and exits 1. It
also lists the capture nodes that answer `/json/info` on this laptop's
/24 (or `--subnet`), each with its level from that reply, never by
subscribing (pewpew.audio.net); `run --audio net:NAME` takes one. `analyse` reads a WAV file and writes stdout, and
with `--feature-log` the log, which `run --audio replay:PATH` plays back.
It runs the analysis `run` runs, frame by frame at `--fps`, with no lead,
so the beats are the file's own times: the tempo and its confidence, how
long the beat spent in each mode, the beat times patterns would see, and
each level's mean and peak. With `--json` it prints one JSON document.
`key` is tier 1 and attended: it makes the key of the node with that MAC
(or keeps the one it has), writes the NVS image's CSV that the node's
firmware is flashed with, and audits it first (pewpew.audio.keys); a dry
run writes nothing.

Exit codes: 0 ok; 1 a file it cannot read, no capture library, or a key it
cannot write; 2 a usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from pewpew import audit, wled
from pewpew.audio import keys
from pewpew.audio.device import Input, inputs
from pewpew.audio.features import LEVELS, MODES, AudioFeatures, FeatureLog, beat_times, play
from pewpew.audio.inputs import NET, wav_source
from pewpew.audio.net import NodeInfo, find_nodes, node_lines
from pewpew.boards import parse_subnet
from pewpew.command import OK, PROBLEMS, parsed_by, positive
from pewpew.errors import describe_exception

HELP = """\
What pewpew hears in a sound file, what it can hear on this computer and
from the capture nodes on its network, and a node's key.

    audio analyse FILE   tempo, confidence, beat times and levels, as a run
                         would analyse them, frame by frame (tier 0)
    audio list           this computer's inputs, for run --audio NAME (needs
                         pewpew[audio]), and the capture nodes on the
                         network, for run --audio net:NAME (tier 0)
    audio key MAC        make a capture node's key and the image to flash
                         it with (tier 1: --dry-run first; audited)

Exit codes: 0 ok; 1 a file it cannot read, no capture library, or a key it
cannot write; 2 a usage error.
"""

def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `audio` command to `sub`."""
    audio = sub.add_parser("audio", help="what pewpew hears in a sound file, and this computer's inputs (tier 0)",
                           description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = audio.add_subparsers(dest="verb", required=True, metavar="VERB")
    p = verbs.add_parser("analyse", help="the tempo, beats and levels of a WAV file")
    p.add_argument("file", type=Path, metavar="FILE", help="a PCM WAV file")
    p.add_argument("--json", action="store_true", help="print one JSON document")
    p.add_argument("--fps", type=positive("a rate in frames per second"), default=60.0,
                   help="the frame rate to analyse at, as run --fps (default 60)")
    p.add_argument("--sensitivity", type=positive("a sensitivity", most=1.0), default=0.5, metavar="S",
                   help="the gate and gain rider, above 0 and at most 1 (default 0.5)")
    p.add_argument("--feature-log", type=Path, default=None, metavar="PATH",
                   help="also write each frame's features to PATH, for run --audio replay:PATH")
    p.set_defaults(cli=analyse_cli)
    p = verbs.add_parser("list", help="this computer's inputs and the network's capture nodes, by the names "
                         "run --audio takes")
    p.add_argument("--json", action="store_true", help="print one JSON document")
    p.add_argument("--subnet", type=parsed_by(parse_subnet), default=None, metavar="CIDR",
                   help="the network to look for capture nodes on, such as 192.168.8.0/24 (default: this laptop's /24)")
    p.set_defaults(cli=list_cli)
    p = verbs.add_parser("key", help="make a capture node's key and its flash image (tier 1)")
    p.add_argument("mac", metavar="MAC", help="the node's MAC, as `esptool read-mac` prints it: aa:bb:cc:dd:ee:ff")
    p.add_argument("--dry-run", action="store_true", help="say what it would write, and write nothing")
    p.set_defaults(cli=key_cli)


def list_cli(args: argparse.Namespace, argv: list[str]) -> int:
    found: list[Input] | None = None
    error = None
    try:
        found = inputs()
    except ValueError as exc:  # no capture library: the nodes need none, so they are still listed
        error = str(exc)
        print(f"audio list: {error}; capture nodes need no extra, so they are listed", file=sys.stderr)
    subnet, nodes = _nodes(args.subnet)
    if args.json:
        devices = None if found is None else [asdict(i) for i in found]
        print(json.dumps({"devices": devices, "error": error, "nodes": [n.row() for n in nodes]}))
    else:
        if found is not None:
            _print_inputs(found)
        if subnet is not None:
            _print_nodes(subnet, nodes)
    return OK if error is None else PROBLEMS


def _print_inputs(found: list[Input]) -> None:
    if not found:
        print("This computer has no inputs.")
        return
    width = max(len(i.name) for i in found)
    print("This computer's inputs. Name one in run --audio exactly as it reads here; pewpew never\n"
          "opens the default input, and audits every input it opens.\n")
    print(f"  index  {'name':{width}}  channels  rate      host API")
    for i in found:
        print(f"  {i.index:<5}  {i.name:{width}}  {i.channels:<8}  {i.rate:<5} Hz  {i.api}")


def _print_nodes(subnet: ipaddress.IPv4Network, nodes: list[NodeInfo]) -> None:
    if nodes:
        print(f"\nCapture nodes on {subnet}. Name one as run --audio {NET}NAME; outside --unattended, add\n"
              "--allow-host ADDRESS (subscribing is tier 1).\n")
        print(*(f"  {line}" for line in node_lines(nodes)), sep="\n")
    else:
        print(f"\nNo capture node answered on {subnet}.")


def _nodes(subnet: ipaddress.IPv4Network | None) -> tuple[ipaddress.IPv4Network | None, list[NodeInfo]]:
    """The subnet looked on, and the capture nodes there; (None, []) when
    this laptop has no IPv4 address and no subnet was given."""
    target = wled.scan_subnet(subnet)
    if target is None:
        print("this laptop has no IPv4 address, so no capture node was looked for; give --subnet", file=sys.stderr)
        return None, []
    subnet, mine = target
    print(f"looking for capture nodes on {subnet}…", file=sys.stderr, flush=True)
    return subnet, find_nodes(subnet, mine)


def key_cli(args: argparse.Namespace, argv: list[str]) -> int:
    try:
        mac = keys.mac_text(args.mac)
        had = keys.load(mac) is not None
    except (OSError, ValueError) as exc:
        raise SystemExit(f"audio key: {describe_exception(exc)}") from None
    path, shown = keys.csv_path(mac), wled.format_mac(mac)
    action = "keep node {}'s key" if had else "make a key for node {}"
    if args.dry_run:
        print(f"dry run: would {action.format(shown)} in {keys.keys_path()} and write its flash image to {path}, "
              "after an audit record; nothing written")
        return OK
    try:
        log = audit.record("audio-node-key", argv=argv, mac=mac, made=not had, image=str(path))
    except OSError as exc:
        print(f"audio key: cannot write the audit record ({describe_exception(exc)}), so no key was written",
              file=sys.stderr)
        return PROBLEMS
    try:
        key = keys.ensure(mac)
        path = keys.write_csv(mac, key)
    except (OSError, ValueError) as exc:
        print(f"audio key: {describe_exception(exc)}", file=sys.stderr)
        return PROBLEMS
    print(f"{'kept' if had else 'made'} the key for node {shown}; audit record appended to {log}")
    print(f"its flash image, readable by you only: {path}")
    print("flash it with the firmware, attended (tier 1, docs/audio.md §8):")
    print(f'  idf.py -C firmware/audio-node -p PORT -DNODE_KEY="{path}" flash')
    return OK


def analyse_cli(args: argparse.Namespace, argv: list[str]) -> int:
    try:
        source = wav_source(args.file)
    except ValueError as exc:
        raise SystemExit(f"{args.file}: {exc}") from None
    with contextlib.ExitStack() as stack:
        log = None
        if args.feature_log is not None:
            try:
                out = stack.enter_context(open(args.feature_log, "w", encoding="utf-8"))
            except OSError as exc:
                raise SystemExit(f"{args.feature_log}: cannot write the feature log: {exc.strerror or exc}") from None
            log = FeatureLog(out, {"fps": args.fps, "audio": args.file.name, "delay_ms": 0.0})
            log.start()
            stack.callback(log.close)
        features = AudioFeatures(source, fps=args.fps, lead=0.0, sensitivity=args.sensitivity, log=log)
        report = analyse(features, source.seconds)
    report = {"file": args.file.name, "rate": source.rate, **report}
    if args.json:
        print(json.dumps(report))
    else:
        print(describe(report))
    return OK


def analyse(features: AudioFeatures, seconds: float) -> dict:
    """The report on `seconds` of `features`: JSON-ready."""
    ticks = list(play(features, seconds))
    modes = Counter(state["mode"] for _, _, state in ticks)
    tempo = [
        {"t": round(t, 3), "bpm": state["bpm"], "confidence": state["confidence"], "mode": state["mode"]}
        for k, (t, _, state) in enumerate(ticks) if (k + 1) % max(1, round(features.fps)) == 0
    ]
    final = ticks[-1][2]
    levels = {name: np.array([getattr(frame, name) for _, frame, _ in ticks]) for name in LEVELS}
    bands = np.array([frame.bands for _, frame, _ in ticks])
    return {
        "seconds": round(seconds, 3),
        "fps": features.fps,
        "bpm": final["bpm"],
        "confidence": final["confidence"],
        "mode": final["mode"],
        "modes": {mode: round(modes[mode] / len(ticks), 3) for mode in MODES if modes[mode]},
        "beats": [round(t, 3) for t in beat_times((t, frame) for t, frame, _ in ticks)],
        "tempo": tempo,
        "levels": {name: {"mean": _r(v.mean()), "peak": _r(v.max())} for name, v in levels.items()},
        "bands": {"mean": [_r(v) for v in bands.mean(axis=0)], "peak": [_r(v) for v in bands.max(axis=0)]},
    }


def describe(report: dict) -> str:
    """The report in a few lines of text."""
    modes = ", ".join(f"{mode} {share:.0%}" for mode, share in report["modes"].items())
    levels = ", ".join(f"{name} {v['mean']:.2f} (peak {v['peak']:.2f})" for name, v in report["levels"].items())
    beats = report["beats"]
    first = ", ".join(f"{t:.2f}" for t in beats[:8]) + (" …" if len(beats) > 8 else "")
    return "\n".join([
        f"{report['file']}: {report['seconds']:.2f} s at {report['rate']} Hz",
        f"tempo {report['bpm']:g} BPM, confidence {report['confidence']:.2f}, ending {report['mode']}",
        f"beat modes: {modes}",
        f"{len(beats)} beat{'' if len(beats) == 1 else 's'}{': ' + first if beats else ''}",
        f"levels (mean, 0-1): {levels}",
    ])


def _r(value: float) -> float:
    return round(float(value), 4)


__all__ = ["add_parser", "analyse", "describe"]
