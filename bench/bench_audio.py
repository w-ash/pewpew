"""Attended replug test of a live input: RA-28 M2, run by a person at the bench.

PortAudio has no hotplug, so reopening an input after an unplug is the one
part of live capture a fake cannot prove (docs/audio.md §7). This opens one
input as a run does (`pewpew.audio.device.DeviceSource`, its supervisor
thread, and a loop here that reads it every tick), then asks the person at
the bench to unplug it and plug it back in, `--trials` times. A trial
passes when the input is lost within `LOST_WAIT_S` of "unplug" and
listening again within `BACK_WAIT_S` of "plug in". The results are each
trial's times and pass^k over the trials, never a gate (T-5).

Tiers (CLAUDE.md T-7): opening an input is a privacy act, so `--dry-run`
names the input and opens nothing, and a real run appends an
`audio-input` audit record before the first open. No sample is kept.

    uv run python -m bench.bench_audio "Scarlett 2i2 USB" --dry-run
    uv run python -m bench.bench_audio "Scarlett 2i2 USB" --trials 5 --label mac
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from bench.common import gather_meta
from pewpew.audio.device import DeviceSource, device_source

FPS = 60.0
LOST_WAIT_S = 30.0  # an unplugged input must read lost this soon [inf]
BACK_WAIT_S = 60.0  # a replugged input must listen again this soon: several of the supervisor's retries [inf]
RESULTS = Path(__file__).parent / "results"
PROMPTS = {"unplug": "Unplug the input's cable now.", "plug": "Plug it back in now."}


def wait_for(source: DeviceSource, status: str, timeout: float, *, now: Callable[[], float],
             sleep: Callable[[float], None], start: float) -> float | None:
    """Read the input every tick until its status is `status`: the seconds
    it took, or None at `timeout`. `start` is when engine time began."""
    asked = now()
    while (waited := now() - asked) < timeout:
        source.take(now() - start)
        if source.state()["status"] == status:
            return waited
        sleep(1.0 / FPS)
    return None


def replug(source: DeviceSource, trials: int, *, ask: Callable[[str], None], now: Callable[[], float],
           sleep: Callable[[float], None]) -> list[dict]:
    """Each trial's times: `ask("unplug")`, wait for lost, `ask("plug")`,
    wait for listening. The input must be listening first."""
    start = now()
    if wait_for(source, "listening", BACK_WAIT_S, now=now, sleep=sleep, start=start) is None:
        raise SystemExit(f"{source.name!r} never opened: {source.state()['reason']}")
    out = []
    for trial in range(trials):
        ask("unplug")
        lost = wait_for(source, "lost", LOST_WAIT_S, now=now, sleep=sleep, start=start)
        ask("plug")
        back = wait_for(source, "listening", BACK_WAIT_S, now=now, sleep=sleep, start=start)
        out.append({"trial": trial, "lost_s": lost, "back_s": back, "passed": None not in (lost, back),
                    "reason": source.state()["reason"]})
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m bench.bench_audio", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="the input's exact name, as `python -m pewpew audio list` prints it")
    parser.add_argument("--trials", type=int, default=5, help="unplug and replug this many times (default 5)")
    parser.add_argument("--label", default="bench", help="names the results file (default bench)")
    parser.add_argument("--dry-run", action="store_true", help="name the input and the steps; open nothing")
    args = parser.parse_args(argv)
    try:
        source = device_source(args.input, fps=FPS)
    except ValueError as exc:
        raise SystemExit(f"{args.input}: {exc}") from None
    print(source.describe())
    if args.dry_run:
        print(f"dry run: nothing opened; a run asks for {args.trials} unplug and replug trials")
        return
    out = RESULTS / f"audio-replug-{datetime.date.today().isoformat()}-{args.label}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; results files are never rewritten (use --label)")
    argv = sys.argv[1:] if argv is None else argv
    log = source.audit(argv, bench="replug")
    print(f"audit record appended to {log}")
    source.start()
    try:
        trials = replug(source, args.trials, ask=lambda step: print(PROMPTS[step], flush=True),
                        now=time.monotonic, sleep=time.sleep)
    finally:
        source.stop()
    passed = sum(t["passed"] for t in trials)
    RESULTS.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "meta": gather_meta(args.label, input=source.name, trials=args.trials),
        "trials": trials, "passed": passed, "pass_k": passed == len(trials),
    }, indent=2) + "\n")
    print(f"{passed} of {len(trials)} trials passed; results written to {out}")


if __name__ == "__main__":
    main()
