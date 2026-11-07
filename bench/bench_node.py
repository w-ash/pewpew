"""Attended bench run of a capture node: RA-28 M2b, run by a person at the bench
(docs/audio.md §9).

It streams from one bench node for `--seconds` as a run does
(`pewpew.audio.net.NetSource`, its supervisor, and a loop here that takes
the packets every tick at `FPS`), records the packet trace, which holds
each packet's header and tick and never a sample, and writes a summary:
the packets taken, the samples lost, the late and stray packets, the
node's reboots and overflow flags, the epochs started by following
dropped packets, each gap with its tick and length, the longest one, and
the drift the fit measured. The procedure's steps (drop
the Wi-Fi, reboot the node, hold BOOT for a forced I2S overflow) are done
by hand during a run; the summary shows each as a gap, a reboot or an
overflow. The results are distributions, never a gate (T-5): each run is
one trial, and docs/audio.md says what each trial must show for pass^k.
With `--tone PATH` it also keeps the first `TONE_PACKETS` datagrams whole,
samples and all, for a run with a generated 1 kHz tone on the line in and
nothing else: they pin the byte layout and the sample order a real node
sends (tests/fixtures/audio_net/).

Tiers (CLAUDE.md T-7): subscribing is tier 1, so it needs `--allow-host`
with the node's IPv4 address, `--dry-run` names the node and subscribes
to nothing, and a real run appends the `audio-input` audit record before
the first SUB. `TraceSource` replays a trace over a seeded signal.

    uv run python -m bench.bench_node pewpew-line-1 --allow-host 192.168.8.42 --dry-run
    uv run python -m bench.bench_node pewpew-line-1 --allow-host 192.168.8.42 --seconds 3600 --label soak
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import numpy as np

from bench.common import gather_meta
from pewpew.audio import wire
from pewpew.audio.analysis import restart_gap
from pewpew.audio.net import NetSource, Trace, TraceSource, node_source
from pewpew.audio.wire import Packet
from pewpew.command import add_allow_host, positive
from pewpew.render import SlotClock

FPS = 60.0
TONE_PACKETS = 20
RESULTS = Path(__file__).parent / "results"


def record(source: NetSource, seconds: float, *, now: Callable[[], float] = time.monotonic,
           sleep: Callable[[float], None] = time.sleep, whole: list[bytes] | None = None) -> Trace:
    """Take from `source` once a slot for `seconds`, as the paced loop does,
    and return the trace of what it drained; `whole`, when given, gets the
    first `TONE_PACKETS` datagrams as the node sent them. The supervisor
    must run."""
    records: list[tuple[bytes, int, int]] = []
    clock, tick = SlotClock(FPS), 0

    def keep(packets: list[Packet], t: float) -> None:
        records.extend(Trace.record(p, tick) for p in packets)
        if whole is not None:
            whole.extend(wire.encode(p) for p in packets[:TONE_PACKETS - len(whole)])

    source.tap = keep
    began = now()
    while clock.t < seconds:
        t = clock.advance()
        tick += 1
        source.take(t)
        sleep(max(0.0, began + t - now()))
    source.tap = None
    return Trace(FPS, tuple(records))


def summarize(trace: Trace) -> dict:
    """What `trace` shows, replayed over silence through a `TraceSource`
    at each tick it drained packets at: JSON-ready (module docstring). A
    new epoch (a reboot, or dropped packets followed) moves the index by
    `restart_gap`, which is no loss; the receiver's counts say how many
    epochs each tick started."""
    source = TraceSource(trace, np.zeros(1, np.float32))
    counts = source.receiver.counts
    ticks = sorted({tick for _, _, tick in trace.records})
    gaps, end, taken = [], None, 0
    for tick in ticks:
        before = counts.reboots + counts.followed
        blocks = source.take(tick / trace.fps)
        epochs = counts.reboots + counts.followed - before  # the epochs this tick started
        for block in blocks:
            taken += len(block.samples)
            jump = 0 if end is None else block.start - end
            if jump == restart_gap(wire.RATE) and epochs:
                epochs -= 1
            elif jump > 0:
                gaps.append({"tick": tick, "samples": jump})
            end = block.end
    drift = source.receiver.clock.drift_ppm
    return {
        "seconds": round((ticks[-1] if ticks else 0) / trace.fps, 2), **asdict(counts),
        "loss": round(counts.missing / max(1, counts.missing + taken), 6),
        "longest_gap_s": round(max((g["samples"] for g in gaps), default=0) / wire.RATE, 4), "gaps": gaps,
        "drift_ppm": None if drift is None else round(drift, 1),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.bench_node", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("node", help="the node's name (pewpew-line-1) or IPv4 address")
    add_allow_host(parser, "the node's IPv4 address: a bench node (subscribing is tier 1)")
    parser.add_argument("--seconds", type=positive("seconds"), default=60.0, help="how long to stream (default 60)")
    parser.add_argument("--label", default="bench", help="names the results file (default bench)")
    parser.add_argument("--trace", type=Path, default=None, metavar="PATH",
                        help="also write the packet trace (headers and ticks, no samples) to PATH")
    parser.add_argument("--tone", type=Path, default=None, metavar="PATH",
                        help=f"also write the first {TONE_PACKETS} packets whole to PATH: only with a generated "
                        "1 kHz tone on the line in")
    parser.add_argument("--dry-run", action="store_true", help="name the node and subscribe to nothing")
    args = parser.parse_args(argv)
    try:
        source = node_source(args.node, fps=FPS, unattended=False, allow_hosts=args.allow_hosts)
    except ValueError as exc:
        raise SystemExit(f"{args.node}: {exc}") from None
    print(source.describe())
    if args.dry_run:
        print(f"dry run: nothing subscribed; a run streams {args.seconds:g} s")
        return
    out = RESULTS / f"audio-node-{datetime.date.today().isoformat()}-{args.label}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; results files are never rewritten (use --label)")
    log = source.audit(sys.argv[1:] if argv is None else list(argv))
    print(f"audit record appended to {log}")
    whole: list[bytes] = []
    source.start()
    try:
        trace = record(source, args.seconds, whole=whole if args.tone is not None else None)
    finally:
        source.stop()
    if args.trace is not None:
        args.trace.write_bytes(trace.to_bytes())
    if args.tone is not None:
        args.tone.write_bytes(b"".join(whole))
    summary = summarize(trace)
    RESULTS.mkdir(exist_ok=True)
    out.write_text(json.dumps({"meta": gather_meta(args.label, node=source.name, address=source.address),
                               "summary": summary}, indent=2) + "\n")
    print(f"{summary['packets']} packets, {summary['loss']:.3%} lost, {len(summary['gaps'])} gaps "
          f"(longest {summary['longest_gap_s']:g} s), {summary['reboots']} reboots, "
          f"{summary['overflows']} overflow flags, drift {summary['drift_ppm']} ppm; results written to {out}")


if __name__ == "__main__":
    main()
