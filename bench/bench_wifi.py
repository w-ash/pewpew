"""Wi-Fi ingest test on the real rig — §12 item 14 for the first installation.

Streams DDP through `pewpew.sinks.DdpSink` to every board at once (default
1,280 px per board) at 40, 50 and 60 fps, and reads back what each board
actually shows. Wi-Fi is the scale question nobody has measured for stock
WLED on an ESP32-S3 at this pixel count (docs/backlog/v0.2.x.md, "First
installation").

The sender is the real pipeline: `Renderer(Comet)` -> `PacedLoop` ->
`SinkDriver` -> `DdpSink`, at the rate under test. Comet moves every frame
and keeps most pixels dark, so the bench does not load the LED supplies.

The receiver side is each board's `GET /json/info`, one board at a time,
each board every `--poll` seconds (default 6), on its own thread so a slow
board never stalls the sender. Never the full `/json`: polling it stalled
output (wled/WLED#3411). Per sample: `leds.fps` (WLED's smoothed show
rate), `wifi.rssi`, `wifi.channel`, `uptime` (a drop is a reboot), `live`,
`lip` (the realtime source address), `freeheap`, `leds.count` and `ver`.

Cells run trial-major (40, 50, 60, 40, 50, 60, ...) so slow drift in the
room's Wi-Fi does not land on one rate. Results are distributions per board
per rate, with pass^k as a summary — never a gate (T-5). The JSON is
rewritten after every cell, so an aborted run keeps what completed.

Tiers (CLAUDE.md T-7): streaming is tier-1 bench actuation, so `--dry-run`
prints the plan and sends nothing, and a real run appends an audit record
(`pewpew.audit`) before the first packet. Polling is read-only (tier 0).

    uv run python bench/bench_wifi.py 10.0.0.11 10.0.0.12 10.0.0.13 --dry-run
    uv run python bench/bench_wifi.py 10.0.0.11=0+1280 10.0.0.12=1280+1280 \\
        10.0.0.13=2560+1280 --label hotel-router --note "ch 6, 20 MHz, WMM off"

A target is `HOST[:PORT]=START+COUNT`, or a bare `HOST[:PORT]` that takes
the next `--px` pixels after the previous target.
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import threading
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path

import numpy as np

from bench.common import gather_meta
from pewpew import PacedLoop, Renderer, SinkDriver, audit, line
from pewpew.patterns import Comet
from pewpew.sinks.ddp import Board, DdpSink, check_boards, parse_board

DEFAULT_PX = 1280
RATES = (40.0, 50.0, 60.0)
DURATION_S = 60.0
TRIALS = 3
POLL_S = 6.0  # each board every 6 s: inside the story's 5-10 s band
POLL_TIMEOUT_S = 2.0
WARMUP_S = 2.0  # no polls this long into a cell; leds.fps is a running average
HOLD = 0.9  # a trial holds a rate when the board's median leds.fps >= HOLD x sent fps
RESULTS = Path(__file__).parent / "results"


def parse_targets(specs: list[str], px: int) -> list[Board]:
    """Targets -> Boards; a bare host takes the next `px` pixels."""
    boards: list[Board] = []
    for spec in specs:
        if "=" in spec:
            boards.append(parse_board(spec))
            continue
        start = boards[-1].stop if boards else 0
        boards.append(parse_board(f"{spec}={start}+{px}"))
    check_boards(boards, max(b.stop for b in boards))
    if len({b.host for b in boards}) < len(boards):
        raise ValueError("each target must be a different board: polling and results key on HOST")
    return boards


def extract(info: dict) -> dict:
    """The fields this bench records, from one `/json/info` reply."""
    leds = info.get("leds", {})
    wifi = info.get("wifi", {})
    return {
        "fps": leds.get("fps"),
        "count": leds.get("count"),
        "rssi": wifi.get("rssi"),
        "channel": wifi.get("channel"),
        "uptime": info.get("uptime"),
        "live": info.get("live"),
        "lip": info.get("lip"),
        "freeheap": info.get("freeheap"),
        "ver": info.get("ver"),
    }


def fetch_info(host: str, timeout: float = POLL_TIMEOUT_S) -> dict:
    with urllib.request.urlopen(f"http://{host}/json/info", timeout=timeout) as r:
        return json.loads(r.read())


class Poller:
    """Round-robin `/json/info` poller: one request at a time, each board
    every `period` seconds. Tags each sample with the current cell and
    skips a poll slot during the first `WARMUP_S` of a cell, where
    `leds.fps` still averages over the previous rate."""

    def __init__(self, boards: list[Board], period: float, fetch=fetch_info) -> None:
        self.hosts = [b.host for b in boards]
        self.gap = period / len(self.hosts)
        self.fetch = fetch
        self.samples: list[dict] = []
        self._cell: tuple[dict, float] | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="wifi-poller", daemon=True)

    def enter_cell(self, rate: float, trial: int) -> None:
        self._cell = ({"rate": rate, "trial": trial}, time.monotonic())

    def leave_cell(self) -> None:
        """Stop tagging samples: no cell is streaming."""
        self._cell = None

    def start(self) -> None:
        self._t0 = time.monotonic()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=POLL_TIMEOUT_S + 1.0)

    def _run(self) -> None:
        i = 0
        while not self._stop.is_set():
            began = time.monotonic()
            cell = self._cell
            if cell is None or began - cell[1] < WARMUP_S:
                self._stop.wait(self.gap)
                continue
            host = self.hosts[i % len(self.hosts)]
            sample = {"board": host, **cell[0], "t": round(began - self._t0, 3)}
            try:
                sample.update(ok=True, **extract(self.fetch(host)))
            except Exception as exc:  # a timeout or a bad reply is data, not a crash
                sample.update(ok=False, error=f"{type(exc).__name__}: {exc}")
            # A fetch that spans a cell change describes neither cell.
            if self._cell is cell:
                self.samples.append(sample)
            i += 1
            self._stop.wait(max(0.0, self.gap - (time.monotonic() - began)))


def stream_cell(boards: list[Board], rate: float, duration: float) -> dict:
    """Stream Comet to every board at `rate` for `duration` seconds."""
    n = max(b.stop for b in boards)
    sink = DdpSink(boards, n, max_fps=rate)
    driver = SinkDriver(sink.send, name="ddp")
    loop = PacedLoop(Renderer(Comet(), line(n)), fps=rate, on_frame=[driver])
    sink.start()
    driver.start()
    try:
        t0 = time.perf_counter()
        stats = loop.run(frames=round(rate * duration))
        driver.drain()
        elapsed = time.perf_counter() - t0
    finally:
        worker_stopped = driver.stop()
        sink.stop()
    return {
        "frames_sent": sink.frames_sent,
        "elapsed_s": round(elapsed, 3),
        "sent_fps": round(sink.frames_sent / elapsed, 3),
        "coalesced": driver.dropped,
        "loop_skips": stats.skips,
        # A failed sendto drops the rest of that board's packets for the
        # frame, so each error is one board-frame lost, not one packet.
        "failed_board_frames": {b.host: e for b, e in zip(boards, sink.errors)},
        "worker_stopped": worker_stopped,
    }


def _pct(values: list[float]) -> dict | None:
    if not values:
        return None
    a = np.asarray(values, dtype=np.float64)
    return {
        "min": float(a.min()),
        "p10": float(np.percentile(a, 10)),
        "median": float(np.median(a)),
        "p90": float(np.percentile(a, 90)),
        "max": float(a.max()),
    }


def _present(samples: list[dict], key: str) -> list:
    """Each sample's `key`, where the board reported it."""
    return [s[key] for s in samples if s[key] is not None]


def summarize(samples: list[dict], cells: list[dict], hold: float = HOLD, sender_ip: str | None = None) -> list[dict]:
    """Per board per rate: delivered fps against sent fps as distributions,
    signal range, reboot trials, and pass^k.

    A trial holds a rate for a board when the median `leds.fps` of that
    trial's samples is at least `hold` x the trial's sent fps and the board
    did not reboot during it. pass^k is "all k trials held". A reboot is any
    `uptime` drop between consecutive good samples of one board, charged to
    the cell of the later sample.
    """
    good: dict[str, list[dict]] = {}
    for s in sorted(samples, key=lambda s: s["t"]):
        if s.get("ok"):
            good.setdefault(s["board"], []).append(s)
    reboots: set[tuple[str, float, int]] = set()
    for board, seq in good.items():
        for prev, cur in zip(seq, seq[1:]):
            if cur["uptime"] is not None and prev["uptime"] is not None and cur["uptime"] < prev["uptime"]:
                reboots.add((board, cur["rate"], cur["trial"]))

    sent = {(c["rate"], c["trial"]): c["sent_fps"] for c in cells}
    trials_of = {
        rate: sorted({c["trial"] for c in cells if c["rate"] == rate})
        for rate in sorted({c["rate"] for c in cells})
    }
    boards = list(dict.fromkeys(s["board"] for s in samples))
    rows = []
    for board in boards:
        for rate, trials in trials_of.items():
            mine = [s for s in samples if s["board"] == board and s["rate"] == rate]
            ok = [s for s in mine if s.get("ok")]
            held = 0
            for k in trials:
                fps_k = [s["fps"] for s in ok if s["trial"] == k and s["fps"] is not None]
                if (
                    fps_k
                    and float(np.median(fps_k)) >= hold * sent[(rate, k)]
                    and (board, rate, k) not in reboots
                ):
                    held += 1
            fps, rssi, heap = _present(ok, "fps"), _present(ok, "rssi"), _present(ok, "freeheap")
            sent_fps = [sent[(rate, k)] for k in trials]
            rows.append(
                {
                    "board": board,
                    "rate": rate,
                    "samples": len(mine),
                    "poll_failures": len(mine) - len(ok),
                    "sent_fps": _pct(sent_fps),
                    "fps": _pct(fps),
                    "fps_ratio_median": (float(np.median(fps)) / float(np.median(sent_fps))) if fps else None,
                    "rssi_range": [min(rssi), max(rssi)] if rssi else None,
                    "channels": sorted(set(_present(ok, "channel"))),
                    "not_live": sum(1 for s in ok if not s["live"]),
                    "foreign_source": (
                        sum(1 for s in ok if s["live"] and s["lip"] and s["lip"] != sender_ip)
                        if sender_ip is not None
                        else None
                    ),
                    "reboot_trials": sum(1 for r in reboots if r[:2] == (board, rate)),
                    "freeheap_min": min(heap) if heap else None,
                    "led_counts": sorted(set(_present(ok, "count"))),
                    "versions": sorted(set(_present(ok, "ver"))),
                    "trials_held": held,
                    "trials": len(trials),
                    "pass_k": held == len(trials) and len(trials) > 0,
                }
            )
    return rows


def sender_address(board: Board) -> str | None:
    """This host's address on the route to `board` (a UDP connect sends
    nothing). Compared with each board's `lip`."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((board.host, board.port))
            return s.getsockname()[0]
    except OSError:
        return None


def summary_table(rows: list[dict]) -> list[str]:
    def f(d: dict | None, key: str) -> str:
        return "-" if d is None else f"{d[key]:.1f}"

    out = [
        "| board | rate | sent fps (median) | leds.fps min / p10 / median / p90 | RSSI dBm | reboot trials | not live | poll fails | held | pass^k |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        rssi = "-" if r["rssi_range"] is None else f"{r['rssi_range'][0]} to {r['rssi_range'][1]}"
        fps = r["fps"]
        out.append(
            f"| {r['board']} | {r['rate']:g} | {f(r['sent_fps'], 'median')} | "
            f"{f(fps, 'min')} / {f(fps, 'p10')} / {f(fps, 'median')} / {f(fps, 'p90')} | {rssi} | "
            f"{r['reboot_trials']} | {r['not_live']} | {r['poll_failures']} | "
            f"{r['trials_held']}/{r['trials']} | {'yes' if r['pass_k'] else 'no'} |"
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="+", metavar="HOST[:PORT][=START+COUNT]")
    ap.add_argument("--px", type=int, default=DEFAULT_PX, help=f"pixels per bare-host target (default {DEFAULT_PX})")
    ap.add_argument("--rates", type=float, nargs="+", default=list(RATES), help="fps to test (default 40 50 60)")
    ap.add_argument("--duration", type=float, default=DURATION_S, help=f"seconds per cell (default {DURATION_S:g})")
    ap.add_argument("--trials", type=int, default=TRIALS, help=f"k trials per rate (default {TRIALS})")
    ap.add_argument("--poll", type=float, default=POLL_S, help=f"seconds between polls of one board (default {POLL_S:g})")
    ap.add_argument("--hold", type=float, default=HOLD, help=f"fraction of sent fps a trial must hold (default {HOLD})")
    ap.add_argument("--label", default=platform.node() or "unknown-host")
    ap.add_argument("--note", default="", help="rig settings to record (router channel, firmware, ...)")
    ap.add_argument("--out", default=None, help="JSON output path (the .md goes beside it)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit without sending")
    args = ap.parse_args()

    try:
        boards = parse_targets(args.targets, args.px)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    cells = [(rate, k) for k in range(args.trials) for rate in args.rates]

    print(f"{len(boards)} boards, {len(cells)} cells of {args.duration:g} s "
          f"({len(cells) * args.duration / 60:.1f} min), each board polled every {args.poll:g} s")
    for rate in args.rates:
        for b in boards:
            print(f"  {b.describe(rate)}")
    if args.dry_run:
        print("dry run: nothing sent, nothing polled")
        return

    meta = gather_meta(args.label, note=args.note)
    out_path = Path(args.out) if args.out else RESULTS / f"wifi-{meta['date']}-{args.label}.json"
    md_path = out_path.with_suffix(".md")
    for p in (out_path, md_path):
        if p.exists():
            raise SystemExit(f"{p} exists; results files are never rewritten (use --label or --out)")
    sender_ip = sender_address(boards[0])
    meta.update(sender_ip=sender_ip)

    log = audit.record(
        "bench-wifi",
        argv=sys.argv,
        targets=[b.spec for b in boards],
        fps=args.rates,
        duration_s=args.duration,
        trials=args.trials,
    )
    print(f"audit record appended to {log}")

    config = {
        "rates": args.rates, "duration_s": args.duration, "trials": args.trials,
        "poll_s": args.poll, "hold": args.hold,
        "boards": [asdict(b) for b in boards],
    }
    done: list[dict] = []
    poller = Poller(boards, args.poll)

    def flush() -> list[dict]:
        samples = list(poller.samples)  # the poller thread keeps appending
        rows = summarize(samples, done, args.hold, sender_ip)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(
            {"meta": meta, "config": config, "summary": rows, "cells": done, "samples": samples},
            indent=2,
        ) + "\n")
        return rows

    poller.start()
    try:
        for order, (rate, k) in enumerate(cells):
            poller.enter_cell(rate, k)
            result = stream_cell(boards, rate, args.duration)
            poller.leave_cell()
            cell = {"rate": rate, "trial": k, "order": order, **result}
            done.append(cell)
            print(f"cell {order + 1}/{len(cells)}: {rate:g} fps trial {k + 1}: "
                  f"sent {cell['sent_fps']:.2f} fps, failed board-frames {cell['failed_board_frames']}")
            flush()
    finally:
        poller.stop()
    rows = flush()

    table = summary_table(rows)
    md_path.write_text("\n".join([
        f"# Wi-Fi ingest test — {meta['date']}, {args.label}",
        "",
        f"- bench: `bench/bench_wifi.py` @ `{meta['git_sha']}`; raw data `{out_path.name}`",
        f"- sender: {meta['cpu'] or meta['machine']}, {sender_ip}",
        f"- rig: {args.note or '(not recorded)'}",
        f"- cells: {args.trials} trials x rates {', '.join(f'{r:g}' for r in args.rates)} fps, "
        f"{args.duration:g} s each; each board polled every {args.poll:g} s",
        f"- held: median `leds.fps` >= {args.hold:g} x sent fps with no reboot; "
        "pass^k = every trial held. A distribution, not a gate (T-5).",
        "",
        *table,
        "",
    ]))
    print("\n".join(["", *table, "", f"results written to {out_path} and {md_path.name}"]))


if __name__ == "__main__":
    main()
