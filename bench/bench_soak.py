"""Soak the live aura rig for hours: ADR-010's GC retest.

A pure-NumPy loop allocates arrays, not gc-tracked containers, so the
pacing soak (`bench/bench_pacing.py`) sees no collections. ADR-010 names
three things that change that: sinks, the param tree and hot reload (gone
with hand-written patterns, ADR-025). This bench runs the whole aura rig as `python -m pewpew run` wires it
(`pewpew.__main__.main`, called in-process), and drives it the way an operator
does:

  room      the 60-bar example room (`examples/room-60-bars.json`) or `--room`;
            DDP to its boards at `--ddp-fps`, or with `--loopback` to a local
            UDP listener per board that counts packets and PUSH frames, so it
            runs without hardware
  preview   the control page server, with two scripted websocket clients: a
            control client connected for the whole run, and a churn client
            that connects, drags a slider (`set` at 20 Hz for 5 s, which the
            rig applies through `call_soon`) and disconnects, again and again
  looks     a looks file generated in a temp dir; periodic recalls with fades
  triggers  launched `--armed`; periodic `fire`s of a trigger that holds a
            look and of one that only reaches the running look as data

Every schedule comes from `--seed` and is printed by `--dry-run` and saved
in the JSON.

Two processes. The rig runs in this process with nothing else of the
bench's in it but light recorders: a `gc.callbacks` hook (collections per
generation, pause durations by `time.perf_counter`), a frame-time probe on
the paced loop, a log tap on the `pewpew` logger, and a sampler thread
(loop counters, thread names, `sys.modules`, sink counters, CPU time). The
websocket clients, the UDP listeners, the file edits, the RSS sampling and
the periodic JSON writes run in a child process (this script with
`--driver`). In-process clients would add their own allocations (a parsed
dict per message) to the GC counts this bench exists to measure, and their
own GIL time to the frame intervals.

Recorded: GC collections per generation and pause distribution; frame
interval distribution and outliers (each with the GC time inside it and
the nearest rig log event); skipped schedule slots; per-board delivered
fps (loopback: counted at the listener; real boards: the health poller's
`leds.fps` and `uptime`, as the page receives them); process RSS, thread
count by thread name, and module count over time, to catch leaks across
recalls and client churn. Distributions (min/p50/p90/p99/max), never a
pass/fail gate (T-5).

Output: `results/soak-<date>-<label>.{json,md}`, refused if either exists.
The child rewrites the JSON every minute with what it has, so a killed run
keeps its data; the final write adds the summary.

Tiers (CLAUDE.md T-7): streaming to real boards is tier-1 bench actuation,
so `--dry-run` prints the plan and sends nothing, and a real run appends a
`bench-soak` audit record (`pewpew.audit`) before the rig starts (the rig
then appends its own `ddp-stream` record). `--loopback` sends nothing off
this machine; its audit records go to a log in the temp dir.

    uv run python -m bench.bench_soak --loopback --duration 1200 --label loopback-<host>
    uv run python -m bench.bench_soak --dry-run
    uv run python -m bench.bench_soak --duration 14400 --label rig --note "<router settings>"

The bench measures with the wall clock; that is the subject. The rig's own
determinism is unchanged: it renders from schedule time (ADR-010 amendment).
"""

from __future__ import annotations

import argparse
import collections
import gc
import itertools
import json
import logging
import math
import os
import platform
import random
import re
import resource
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from bench.common import gather_meta

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).parent / "results"
DEFAULT_ROOM = ROOT / "examples" / "room-60-bars.json"


def shown(path: Path) -> str:
    """Return PATH relative to the repo, or its file name, for the public results."""
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name


FPS = 60.0  # the runner's default render rate
DDP_FPS = 40.0  # the runner's default DDP rate
DURATION_S = 4 * 3600.0
SAMPLE_S = 10.0  # one sample row per process this often
FLUSH_S = 60.0  # the child rewrites the JSON this often
SEED = 1
WARMUP_S = 120.0  # RSS slope is fitted after this; startup allocations are not a leak
STARTUP_S = 5.0  # pacing distributions start here: the first frames wait on imports and the first look

# Schedules, in seconds: each next event is uniform in (lo, hi) after the last.
RECALL_EVERY_S = (60.0, 90.0)
FIRE_EVERY_S = (80.0, 120.0)
CHURN_EVERY_S = (30.0, 50.0)  # connect to connect
CHURN_STAY_S = (12.0, 20.0)  # connected this long
DRAG_S, DRAG_HZ = 5.0, 20.0  # one slider drag per connection
END_MARGIN_S = 10.0  # no scripted action this close to the end
WATCHDOG_S = 5.0  # pewpew.watchdog.TIMEOUT_S; fixed here because the JSON key `watchdog_5s_would_fire` names it

OUTLIER_TOP = 20
LOG_KEEP = 5000

def _look(source: str, args: dict, palette: str, fade: float) -> dict:
    """A looks-file look of one layer, `base`: source op `source` at
    `args`, colored by preset `palette`."""
    return {"fade": fade, "layers": [{"id": "base", "nodes": {
        source: {"op": source, "args": args},
        "tint": {"op": "palette", "in": [source], "args": {"palette": palette}},
    }}]}


LOOKS = {
    "soak-a": _look("osc", {"freq": 4.0, "sync": 0.25}, "ocean", 2.0),
    "soak-b": _look("noise", {"scale": 4.0}, "aurora", 3.0),
    "soak-c": _look("osc", {"freq": 2.0, "sync": -0.1}, "ember", 1.5),
    "soak-d": _look("voronoi", {}, "forest", 2.0),
    "soak-cue": _look("noise", {"scale": 8.0}, "ice", 0.5),
}
RECALL_ORDER = ("soak-b", "soak-c", "soak-d", "soak-a")
TRIGGERS = {
    "cue1": {"look": "soak-cue", "hold": 8.0, "priority": "button", "cooldown": 1.0},
    "door": {"look": None, "priority": "sensor"},
}
FIRE_ORDER = ("cue1", "door")


# ---- shared: files and schedule --------------------------------------------


def looks_doc() -> dict:
    """The looks file the rig starts with. The idle cycle is off, so every
    recall in the run is one this bench scheduled."""
    from pewpew.aura.book import VERSION

    return {"version": VERSION, "current": "soak-a", "looks": LOOKS,
            "cycle": {"idle": None}, "triggers": TRIGGERS}


def build_schedule(duration: float, seed: int) -> list[dict]:
    """Every scripted action, sorted by time in seconds from the first frame."""
    rng = random.Random(seed)
    end = duration - END_MARGIN_S
    events: list[dict] = []

    def series(kind: str, every: tuple[float, float], make) -> None:
        t, i = rng.uniform(*every), 0
        while t < end:
            events.append({"t": round(t, 3), "kind": kind, **make(i)})
            t += rng.uniform(*every)
            i += 1

    series("recall", RECALL_EVERY_S, lambda i: {"look": RECALL_ORDER[i % len(RECALL_ORDER)]})
    series("fire", FIRE_EVERY_S, lambda i: {"trigger": FIRE_ORDER[i % len(FIRE_ORDER)]})
    t = rng.uniform(*CHURN_EVERY_S)
    while t + CHURN_STAY_S[1] < end:
        stay = rng.uniform(*CHURN_STAY_S)
        events.append({"t": round(t, 3), "kind": "churn", "stay": round(stay, 3),
                       "drag_at": round(rng.uniform(1.0, stay - DRAG_S - 1.0), 3)})
        t += max(stay + 2.0, rng.uniform(*CHURN_EVERY_S))
    return sorted(events, key=lambda e: e["t"])


# ---- summary (pure; tested on canned samples) --------------------------------


def dist(values: Any) -> dict | None:
    a = np.asarray(values, dtype=np.float64)
    if a.size == 0:
        return None
    return {
        "n": int(a.size),
        "min": float(a.min()),
        "p50": float(np.percentile(a, 50)),
        "p90": float(np.percentile(a, 90)),
        "p99": float(np.percentile(a, 99)),
        "max": float(a.max()),
        "mean": float(a.mean()),
    }


def summarize(frame_s: np.ndarray, period_s: float, gc_t: np.ndarray, gc_ms: np.ndarray,
              gc_gen: np.ndarray, events: list[tuple[float, str]] = (), top: int = OUTLIER_TOP,
              start_s: float = 0.0) -> dict:
    """Pacing and GC over one run.

    `frame_s` is each frame's hand-off time in seconds from the first frame,
    `gc_t`/`gc_ms`/`gc_gen` each collection's start, pause and generation,
    `events` the rig's log as (time, message). An interval's error is its
    length minus the period; an outlier is an interval with an error above
    one period, a whole frame of cadence lost, as in bench_pacing. Pacing
    counts only intervals that start at or after `start_s`; the ones before
    are reported as `startup`. GC counts every collection.
    """
    frame_s = np.asarray(frame_s, dtype=np.float64)
    gc_t = np.asarray(gc_t, dtype=np.float64)
    gc_ms = np.asarray(gc_ms, dtype=np.float64)
    gc_gen = np.asarray(gc_gen, dtype=np.int64)
    period_ms = period_s * 1000.0
    first = int(np.searchsorted(frame_s, start_s))  # first frame at or after start_s
    head = np.diff(frame_s[:first + 1]) * 1000.0
    frame_s = frame_s[first:]
    iv = np.diff(frame_s) * 1000.0
    err = np.abs(iv - period_ms)
    span = float(frame_s[-1] - frame_s[0]) if frame_s.size > 1 else 0.0

    gc_end = gc_t + gc_ms / 1000.0

    def gc_inside(i: int) -> tuple[float, list[int]]:
        """GC pause time inside interval i (frame i to i+1), in ms, and its generations."""
        a, b = frame_s[i], frame_s[i + 1]
        lo, hi = np.searchsorted(gc_t, [a - 1.0, b])  # no pause is near a second long
        overlap = np.clip(np.minimum(gc_end[lo:hi], b) - np.maximum(gc_t[lo:hi], a), 0.0, None)
        hit = overlap > 0.0
        return float(overlap.sum() * 1000.0), sorted({int(g) for g in gc_gen[lo:hi][hit]})

    def nearest(t: float) -> str | None:
        close = [(abs(et - t), msg) for et, msg in events if abs(et - t) <= 2.0]
        return min(close)[1] if close else None

    late = np.flatnonzero(err > period_ms)
    inside = {int(i): gc_inside(int(i)) for i in late}
    with_gc = sum(1 for g_ms, _ in inside.values() if g_ms > 0.0)
    order = late[np.argsort(-iv[late])][:top]
    outliers = []
    for i in order:
        g_ms, gens = inside[int(i)]
        outliers.append({
            "t_s": round(float(frame_s[i]), 3),
            "interval_ms": round(float(iv[i]), 3),
            "gc_ms": round(g_ms, 3),
            "gc_gens": gens,
            "near": nearest(float(frame_s[i])),
        })
    by_gen = {}
    for g in sorted({int(x) for x in gc_gen}):
        ms = gc_ms[gc_gen == g]
        by_gen[str(g)] = {"collections": int(ms.size), "total_ms": float(ms.sum()), "pause_ms": dist(ms)}
    return {
        "pacing": {
            "frames": int(frame_s.size),
            "span_s": span,
            "fps": (frame_s.size - 1) / span if span else 0.0,
            "interval_ms": dist(iv),
            "abs_error_ms": dist(err),
            "over_5ms": int((err > 5.0).sum()),
            "over_one_frame": int(late.size),
            "over_one_frame_with_gc": with_gc,
            "from_s": start_s,
            "startup": {"intervals": int(head.size), "max_ms": float(head.max()) if head.size else None},
        },
        "gc": {
            "collections": int(gc_ms.size),
            "total_ms": float(gc_ms.sum()),
            "pause_ms": dist(gc_ms),
            "over_period": int((gc_ms > period_ms).sum()),
            "by_gen": by_gen,
        },
        "outliers": outliers,
    }


def trend(rows: list[dict], key: str, after: float = WARMUP_S) -> dict | None:
    """First, last, min, max of `key` over sample rows, and its slope per
    hour fitted after `after` seconds."""
    pts = [(r["t"], r[key]) for r in rows if r.get(key) is not None]
    if not pts:
        return None
    t, v = np.array(pts, dtype=np.float64).T
    late = t >= after
    slope = float(np.polyfit(t[late], v[late], 1)[0] * 3600.0) if late.sum() >= 3 else None
    return {"first": float(v[0]), "last": float(v[-1]), "min": float(v.min()), "max": float(v.max()),
            "per_hour_after_warmup": slope}


def board_summary(rows: list[dict], names: list[str]) -> list[dict]:
    """Loopback: each board's delivered fps per sample window, from the
    listener's PUSH counts (the first window is startup, and left out)."""
    out = []
    for i, name in enumerate(names):
        seq = [r["boards"][i] for r in rows if r.get("boards")]
        fps = [b["fps"] for b in seq[1:] if b.get("fps") is not None]
        last = seq[-1] if seq else {}
        out.append({"board": name, "fps": dist(fps), "frames": last.get("frames", 0),
                    "packets": last.get("packets", 0), "incomplete_frames": last.get("incomplete", 0)})
    return out


def health_summary(samples: list[dict]) -> list[dict]:
    """Real boards: `leds.fps`, `uptime` drops and RSSI per board, from the
    health states the page received. Drift: median fps of the first and of
    the last tenth of the samples."""
    out = []
    for host in dict.fromkeys(s["host"] for s in samples):
        seq = [s for s in samples if s["host"] == host]
        fps = [s["fps"] for s in seq if s.get("fps") is not None]
        up = [s["uptime"] for s in seq if s.get("uptime") is not None]
        rssi = [s["rssi"] for s in seq if s.get("rssi") is not None]
        tenth = max(1, len(fps) // 10)
        out.append({
            "board": host,
            "fps": dist(fps),
            "fps_first_tenth_median": float(np.median(fps[:tenth])) if fps else None,
            "fps_last_tenth_median": float(np.median(fps[-tenth:])) if fps else None,
            "reboots": sum(1 for a, b in itertools.pairwise(up) if b < a),
            "uptime_first_last": [up[0], up[-1]] if up else None,
            "rssi_range": [min(rssi), max(rssi)] if rssi else None,
            "samples": len(seq),
        })
    return out


# ---- the rig process ----------------------------------------------------------


class Recorder:
    """Frame times and GC events in preallocated arrays: the hooks allocate
    no gc-tracked object per event, so recording does not feed what it
    records. Arrays are filled up front, so their pages count in the first
    RSS sample, not as growth."""

    def __init__(self, duration: float, fps: float) -> None:
        self.frames = np.full(int(duration * fps * 1.05) + 6000, np.nan)
        self.n_frames = 0
        cap = int(duration * 50) + 20000
        self.gc_t = np.full(cap, np.nan)
        self.gc_ms = np.full(cap, np.nan)
        self.gc_gen = np.full(cap, -1, dtype=np.int8)
        self.n_gc = 0
        self.gc_dropped = 0
        self.gen_counts = [0, 0, 0]
        self.t0 = time.perf_counter()
        self.first_frame = threading.Event()
        self.loop: Any = None
        self.drivers: list = []
        self._gc_start = 0.0

    def frame(self, t: float, frame: Any) -> None:
        i = self.n_frames
        if i < self.frames.size:
            self.frames[i] = time.perf_counter() - self.t0
            self.n_frames = i + 1
        if i == 0:
            self.first_frame.set()

    def gc_hook(self, phase: str, info: dict) -> None:
        if phase == "start":
            self._gc_start = time.perf_counter()
            return
        end = time.perf_counter()
        gen = info.get("generation", 0)
        if 0 <= gen < 3:
            self.gen_counts[gen] += 1
        i = self.n_gc
        if i < self.gc_t.size:
            self.gc_t[i] = self._gc_start - self.t0
            self.gc_ms[i] = (end - self._gc_start) * 1000.0
            self.gc_gen[i] = gen
            self.n_gc = i + 1
        else:
            self.gc_dropped += 1

    def probe_class(self):
        """A `PacedLoop` that also calls `frame` and hands itself over."""
        from pewpew.pace import PacedLoop
        from pewpew.sinks.base import SinkDriver

        rec = self

        class ProbeLoop(PacedLoop):
            def __init__(self, source, fps=60.0, *, on_frame=(), **kw):
                super().__init__(source, fps, on_frame=[*on_frame, rec.frame], **kw)
                rec.loop = self
                rec.drivers = [d for d in on_frame if isinstance(d, SinkDriver)]

        return ProbeLoop


class LogTap(logging.Handler):
    """Every `pewpew` log record, timestamped on the bench's clock."""

    def __init__(self, t0: float) -> None:
        super().__init__(logging.INFO)
        self.t0 = t0
        self.records: collections.deque = collections.deque(maxlen=LOG_KEEP)
        self.counts: collections.Counter = collections.Counter()

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        self.records.append((round(time.perf_counter() - self.t0, 3), record.levelname, msg))
        self.counts[re.sub(r"[\d.]+|'[^']*'|\(.*", "#", msg)[:60]] += 1


def thread_groups() -> dict[str, int]:
    """Live threads by name, digits folded, so a leak shows as one growing group."""
    return dict(collections.Counter(re.sub(r"\d+", "#", t.name) for t in threading.enumerate()))


class RowLog:
    """Sample rows kept as JSON text. A str is not gc-tracked, so the rows
    held for the whole run add nothing to the collections the soak counts,
    and less to its RSS slope than live dicts would. `rows` decodes them."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def __len__(self) -> int:
        return len(self._lines)

    def append(self, row: dict) -> None:
        self._lines.append(json.dumps(row))

    def rows(self) -> list[dict]:
        return [json.loads(line) for line in self._lines]


def sample_row(rec: Recorder, since: tuple[int, int], gc_before: list[int],
               t: float) -> tuple[dict, tuple[int, int], list[int]]:
    """One rig sample: counters, and the frame intervals and collections
    since the last row. Also returns the marks the next row starts from.
    The marks are read first, so a collection that the row's own
    allocations trigger counts in the next row."""
    hi, n_gc, gc_now = rec.n_frames, rec.n_gc, list(rec.gen_counts)
    stats = rec.loop.stats if rec.loop is not None else None
    iv = np.diff(rec.frames[max(since[0] - 1, 0):hi]) * 1000.0
    pauses = rec.gc_ms[since[1]:n_gc]
    ru = resource.getrusage(resource.RUSAGE_SELF)
    drivers = {}
    for d in rec.drivers:
        sink = getattr(d._send, "__self__", None)
        drivers[d.name] = {"dropped": d.dropped, "errors": d.errors,
                           "frames_sent": getattr(sink, "frames_sent", None)}
    row = {
        "t": round(t, 3),
        "ticks": stats.ticks if stats else 0,
        "skips": stats.skips if stats else 0,
        "missed_frames": stats.missed_frames if stats else 0,
        "interval_ms": None if iv.size == 0 else {
            "p50": round(float(np.median(iv)), 3), "p99": round(float(np.percentile(iv, 99)), 3),
            "max": round(float(iv.max()), 3)},
        "gc": [gc_now[g] - gc_before[g] for g in range(3)],
        "gc_max_ms": round(float(pauses.max()), 3) if pauses.size else 0.0,
        "threads": threading.active_count(),
        "thread_groups": thread_groups(),
        "modules": len(sys.modules),
        "cpu_s": round(ru.ru_utime + ru.ru_stime, 3),
        "drivers": drivers,
    }
    return row, (hi, n_gc), gc_now


def prepare(args: argparse.Namespace, tmp: Path, ports: list[int] | None) -> tuple[Path, Path]:
    """Write the looks file and (loopback) the room with every board moved
    to its local listener. Returns (looks file, room file)."""
    looks_dir = tmp / "looks"
    looks_dir.mkdir()
    looks = looks_dir / "looks.json"
    looks.write_text(json.dumps(looks_doc(), indent=2) + "\n")
    if ports is None:
        return looks, args.room
    doc = json.loads(args.room.read_text())
    doc["boards"] = {name: f"127.0.0.1:{port}" for name, port in zip(doc["boards"], ports)}
    plan = doc.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("image"), str):
        plan["image"] = str((args.room.parent / plan["image"]).resolve())
    room_dir = tmp / "room"
    room_dir.mkdir()
    room = room_dir / "room.json"
    room.write_text(json.dumps(doc, indent=2) + "\n")
    return looks, room


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(args: argparse.Namespace) -> None:
    from pewpew import audit
    from pewpew.room.map import load_room

    room, _ = load_room(args.room)
    schedule = build_schedule(args.duration, args.seed)
    kinds = collections.Counter(e["kind"] for e in schedule)
    port = args.port or free_port()
    print(f"room {args.room}: {room.n} px on {len(room.boards)} boards; "
          f"render {args.fps:g} fps, DDP {args.ddp_fps:g} fps; {args.duration:g} s "
          f"({args.duration / 3600:.2f} h), seed {args.seed}")
    if args.loopback:
        print("  loopback: every board moves to a local UDP listener; nothing leaves this machine")
    else:
        for line in room.plan(args.ddp_fps):
            print(f"  {line}")
    print(f"  preview on 127.0.0.1:{port}; scripted: "
          + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
          + f"; slider drag {DRAG_S:g} s at {DRAG_HZ:g} Hz per churn connection")
    for e in schedule[:6]:
        print(f"    t={e['t']:8.1f}s {e['kind']} {({k: v for k, v in e.items() if k not in ('t', 'kind')})}")
    if args.dry_run:
        print("dry run: nothing sent, no rig started")
        return

    meta = gather_meta(args.label, note=args.note, mode="loopback" if args.loopback else "ddp",
                       gc_enabled=gc.isenabled(), gc_thresholds=gc.get_threshold(),
                       switch_interval_s=sys.getswitchinterval())
    # Absolute: the driver runs in ROOT and writes the partial JSON to this same path.
    out_json = (Path(args.out) if args.out else RESULTS / f"soak-{meta['date']}-{args.label}.json").resolve()
    out_md = out_json.with_suffix(".md")
    for p in (out_json, out_md):
        if p.exists():
            raise SystemExit(f"{p} exists; results files are never rewritten (use --label or --out)")
    out_json.parent.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix="pewpew-soak-"))
    if args.loopback:
        os.environ[audit.ENV_VAR] = str(tmp / "audit.jsonl")  # loopback is not hardware
    else:
        log = audit.record("bench-soak", argv=sys.argv, targets=[b.spec for b in room.boards],
                           fps=args.ddp_fps, duration_s=args.duration, room=shown(args.room))
        print(f"audit record appended to {log}")

    config = {
        "mode": meta["mode"], "room": shown(args.room), "boards": list(room.board_names),
        "fps": args.fps, "ddp_fps": args.ddp_fps, "duration_s": args.duration,
        "sample_s": SAMPLE_S, "seed": args.seed, "preview_port": port,
        "master_cap": args.master_cap, "looks": looks_doc(),
        "churn": {"every_s": CHURN_EVERY_S, "stay_s": CHURN_STAY_S, "drag_s": DRAG_S, "drag_hz": DRAG_HZ},
        "recall_every_s": RECALL_EVERY_S, "fire_every_s": FIRE_EVERY_S,
    }
    driver_cfg = {
        "packets_per_frame": [b.packets_per_frame for b in room.boards],
        "schedule": schedule,
        "out_json": str(out_json), "meta": meta, "config": config, "parent_pid": os.getpid(),
    }
    (tmp / "driver.json").write_text(json.dumps(driver_cfg))
    child = subprocess.Popen(
        [sys.executable, "-m", "bench.bench_soak", "--driver", str(tmp / "driver.json")],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        # The child binds the loopback listeners first; their ports go in the room.
        ready = _last_json(child.stdout.readline(), "ready")
        if not ready or (args.loopback and not ready.get("ports")):
            raise SystemExit("bench_soak: the driver process did not start")
        looks, room_file = prepare(args, tmp, ready.get("ports"))
        rig_argv = [
            "run", str(looks), "--room", str(room_file),
            "--fps", f"{args.fps:g}", "--ddp-fps", f"{args.ddp_fps:g}",
            "--preview", "--port", str(port), "--trigger-log", str(tmp / "triggers.jsonl"),
            "--armed", "--keep-awake", "--master-cap", f"{args.master_cap:g}",
        ]
        config["rig_argv"] = rig_argv
        doc = soak(args, rig_argv, child, meta, config, schedule)
    finally:
        if child.poll() is None:
            child.kill()
    from pewpew.jsonfile import write_atomic

    doc["summary"]["temp_dir"] = str(tmp)
    write_atomic(out_json, (json.dumps(doc, indent=1) + "\n").encode())
    out_md.write_text(render_md(doc, out_json.name))
    print(f"\nresults written to {out_json} and {out_md.name}")
    if not args.keep_temp:
        shutil.rmtree(tmp, ignore_errors=True)


def soak(args, rig_argv: list[str], child: subprocess.Popen, meta: dict, config: dict,
         schedule: list[dict]) -> dict:
    """Run the rig on this thread until the duration is up; return the doc."""
    from unittest import mock

    import pewpew.__main__ as cli
    import pewpew.run as rig

    rec = Recorder(args.duration, args.fps)
    tap = LogTap(rec.t0)
    logging.getLogger("pewpew").addHandler(tap)
    row_log = RowLog()
    done = threading.Event()

    def send(msg: dict) -> None:
        try:
            child.stdin.write(json.dumps(msg) + "\n")
            child.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass  # a dead driver loses its own data, not the rig's

    def sampler() -> None:
        if not rec.first_frame.wait(120.0):
            print("bench_soak: no frame within 120 s; stopping the rig", file=sys.stderr)
            # stop() is a standing request: it holds if the loop has not started.
            while rec.loop is None and not done.wait(0.5):
                pass
            if rec.loop is not None:
                rec.loop.stop()
            return
        start = rec.frames[0]
        send({"kind": "go", "t0": time.monotonic() - (time.perf_counter() - rec.t0 - start)})
        since, gc_before = (0, 0), list(rec.gen_counts)
        next_at, end = start + SAMPLE_S, start + args.duration
        while True:
            now = time.perf_counter() - rec.t0
            if now >= end or done.wait(max(0.0, min(next_at, end) - now)):
                break
            t =time.perf_counter() - rec.t0 - start
            row, since, gc_before = sample_row(rec, since, gc_before, t)
            row_log.append(row)
            send({"kind": "row", "row": row})
            if len(row_log) % 6 == 0:
                iv = row["interval_ms"] or {}
                print(f"t={t:7.0f}s ticks {row['ticks']} skips {row['skips']} "
                      f"gc(total) {rec.gen_counts} max interval {iv.get('max', 0):.1f} ms "
                      f"threads {row['threads']} modules {row['modules']}", flush=True)
            next_at += SAMPLE_S
        if rec.loop is not None:
            rec.loop.stop()

    gc.collect()  # a known heap to start from; GC stays on, it is the subject
    gc_start = gc.get_stats()
    gc.callbacks.append(rec.gc_hook)
    thread = threading.Thread(target=sampler, name="bench-sampler", daemon=True)
    thread.start()
    started = time.perf_counter()
    try:
        with mock.patch.object(rig, "PacedLoop", rec.probe_class()):
            cli.main(rig_argv)
    finally:
        gc.callbacks.remove(rec.gc_hook)
        gc_end = gc.get_stats()  # the same window as the callback's counts
        done.set()
        logging.getLogger("pewpew").removeHandler(tap)
    stopped_early = time.perf_counter() - started < args.duration * 0.98
    thread.join(timeout=5.0)

    # EOF on its stdin stops the driver; it then prints its final record.
    try:
        final = _last_json(child.communicate(timeout=60.0)[0])
    except (subprocess.TimeoutExpired, OSError, ValueError):
        final = {}

    start = rec.frames[0] if rec.n_frames else 0.0
    frames = rec.frames[:rec.n_frames] - start
    events = [(t - start, msg) for t, _, msg in tap.records]
    summary = summarize(frames, 1.0 / args.fps, rec.gc_t[:rec.n_gc] - start,
                        rec.gc_ms[:rec.n_gc], rec.gc_gen[:rec.n_gc], events, start_s=STARTUP_S)
    stats =rec.loop.stats if rec.loop is not None else None
    driver_rows = final.get("samples", [])
    rows = row_log.rows()
    summary.update({
        "stopped_early": stopped_early,
        "skips": {"events": stats.skips, "missed_frames": stats.missed_frames} if stats else None,
        "gc_counts_by_gen": list(rec.gen_counts),
        "gc_events_not_stored": rec.gc_dropped,
        "gc_stats_end": gc_end,
        "watchdog_5s_would_fire": int((np.diff(frames) > WATCHDOG_S).sum()) if frames.size > 1 else 0,
        "gc_stats_start": gc_start,
        "rss_kb": trend(driver_rows, "rss_kb"),
        "threads": trend(rows, "threads"),
        "modules": trend(rows, "modules"),
        "thread_groups_first_last": [rows[0]["thread_groups"], rows[-1]["thread_groups"]] if rows else None,
        "cpu_s": rows[-1]["cpu_s"] if rows else None,
        "drivers_end": rows[-1]["drivers"] if rows else None,
        "boards": board_summary(driver_rows, config["boards"]) if args.loopback else None,
        "health": health_summary(final.get("health", [])),
        "log_counts": dict(tap.counts.most_common()),
        "client": final.get("client"),
        "actions": final.get("actions"),
    })
    return {
        "meta": meta, "config": config, "partial": False, "summary": summary,
        "schedule": schedule, "rig_samples": rows, "driver_samples": driver_rows,
        "driver_events": final.get("events", []),
        "health_samples": final.get("health", []),
        "log": [[round(t - start, 3), lvl, msg] for t, lvl, msg in tap.records],
    }


def _last_json(text: str, kind: str = "final") -> dict:
    """The last line of `text` that is a JSON object of this `kind`, or {}."""
    for line in reversed((text or "").splitlines()):
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("kind") == kind:
            return doc
    return {}


# ---- the driver process ----------------------------------------------------------


class Listener:
    """One UDP socket per board on 127.0.0.1: packets, bytes, PUSH frames,
    and frames whose packet count since the last PUSH was not the board's."""

    def __init__(self, packets_per_frame: list[int]) -> None:
        self.expected = packets_per_frame
        n = len(packets_per_frame)
        self.packets, self.bytes, self.frames, self.incomplete = [0] * n, [0] * n, [0] * n, [0] * n
        self._since = [0] * n
        self.socks = []
        for _ in range(n):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 22)
            s.bind(("127.0.0.1", 0))
            s.setblocking(False)
            self.socks.append(s)
        self.ports = [s.getsockname()[1] for s in self.socks]

    def run(self, stop: threading.Event) -> None:
        from pewpew.sinks.ddp import FLAG_PUSH, HEADER_LEN

        sel = selectors.DefaultSelector()
        for i, s in enumerate(self.socks):
            sel.register(s, selectors.EVENT_READ, i)
        buf = bytearray(2048)
        while not stop.is_set():
            for key, _ in sel.select(0.2):
                i, s = key.data, key.fileobj
                while True:
                    try:
                        n = s.recv_into(buf)
                    except BlockingIOError:
                        break
                    self.packets[i] += 1
                    self.bytes[i] += n
                    self._since[i] += 1
                    if n >= HEADER_LEN and buf[0] & FLAG_PUSH:
                        self.frames[i] += 1
                        if self._since[i] != self.expected[i]:
                            self.incomplete[i] += 1
                        self._since[i] = 0
        for s in self.socks:
            s.close()


class Client:
    """A websocket client like the page (`pewpew.remote.client.Client`):
    drains every message on its own thread and keeps what the soak reads
    (params, aura state, refusals, fired triggers, health)."""

    def __init__(self, url: str, t0: float, health: list | None = None, tries: int = 3) -> None:
        from pewpew.remote.client import Client as Wire  # in the driver process only (module docstring)

        self.t0 = t0
        self.health = health
        self.refused: list[dict] = []
        self.fired: list[dict] = []
        self.look: str | None = None
        self.looks_seen: collections.Counter = collections.Counter()
        self._last_health: dict[str, tuple] = {}
        self._last_trigger: Any = None
        self.wire = Wire(url, on_text=self._record, tries=tries)

    @property
    def counts(self) -> collections.Counter:
        return self.wire.counts

    @property
    def params(self) -> list[dict]:
        return self.wire.latest.get("declare", {}).get("params", [])

    def send(self, msg: dict) -> None:
        self.wire.send(msg)

    def close(self) -> None:
        self.wire.close()

    def _record(self, doc: dict) -> None:
        kind = doc["type"]
        if kind == "aura":
            current = (doc.get("looks") or {}).get("current")
            if current != self.look:
                self.look = current
                self.looks_seen[self.look] += 1
            last = (doc.get("triggers") or {}).get("last")
            if last and last != self._last_trigger:
                self._last_trigger = last
                self.fired.append({"t": round(time.monotonic() - self.t0, 3), **last})
        elif kind == "refused" and len(self.refused) < 200:
            self.refused.append({"t": round(time.monotonic() - self.t0, 3), **doc})
        elif kind == "health" and self.health is not None:
            for b in doc.get("boards", []):
                key = (b.get("uptime"), b.get("fps"), b.get("level"))
                if self._last_health.get(b["host"]) != key:
                    self._last_health[b["host"]] = key
                    self.health.append({"t": round(time.monotonic() - self.t0, 3),
                                        **{k: b.get(k) for k in ("host", "fps", "uptime", "rssi",
                                                                 "live", "level", "reboots")}})


def sliders(params: list[dict]) -> list[dict]:
    """The `declare` records a churn client drags: the nodes' float
    params. A layer's own controls (no `node`) and params with no range
    are left out. A `set` names a param by its record's `name`, the full path."""
    return [p for p in params if p.get("node") and p.get("kind") == "float"]


def rss_kb(pid: int) -> int | None:
    status = Path(f"/proc/{pid}/status")
    try:
        if status.exists():
            for line in status.read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=5, check=False
        )
        return int(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def driver_main(cfg_path: Path) -> None:
    """The child: listeners, clients, scripted actions, RSS, partial writes."""
    from pewpew.jsonfile import write_atomic

    stop = threading.Event()
    go = threading.Event()
    clock: dict = {}
    rig_rows: list[dict] = []
    listener = None
    # Ctrl-C reaches the whole process group; the parent's "stop" ends this
    # process, so it still reports what it recorded.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    cfg = json.loads(cfg_path.read_text())
    config = cfg["config"]
    if config["mode"] == "loopback":
        listener = Listener(cfg["packets_per_frame"])
        threading.Thread(target=listener.run, args=(stop,), daemon=True).start()
    print(json.dumps({"kind": "ready", "ports": listener.ports if listener else None}), flush=True)

    def from_parent() -> None:
        for line in sys.stdin:
            msg = json.loads(line)
            if msg["kind"] == "go":
                clock["t0"] = msg["t0"]
                go.set()
            elif msg["kind"] == "row":
                rig_rows.append(msg["row"])
        stop.set()  # EOF: the rig is done, or the parent died
        go.set()

    threading.Thread(target=from_parent, daemon=True).start()
    try:
        go.wait()
        if stop.is_set():
            return
        t0 = clock["t0"]
        url = f"ws://127.0.0.1:{config['preview_port']}/"
        health: list[dict] = []
        events: list[dict] = []
        actions: collections.Counter = collections.Counter()
        control = Client(url, t0, health, tries=150)
        churn_stats: collections.Counter = collections.Counter()

        def log(kind: str, **kw: Any) -> None:
            events.append({"t": round(time.monotonic() - t0, 3), "kind": kind, **kw})

        def wait_until(t: float) -> bool:
            return not stop.wait(max(0.0, t0 + t - time.monotonic()))

        def conductor() -> None:
            for e in cfg["schedule"]:
                if e["kind"] == "churn":
                    continue
                if not wait_until(e["t"]):
                    return
                try:
                    if e["kind"] == "recall":
                        control.send({"type": "recall", "name": e["look"]})
                    elif e["kind"] == "fire":
                        control.send({"type": "fire", "name": e["trigger"]})
                    actions[e["kind"]] += 1
                    log(e["kind"], **{k: v for k, v in e.items() if k not in ("t", "kind")})
                except Exception as exc:  # noqa: BLE001  a failed action is logged; the soak goes on
                    log("error", action=e["kind"], error=f"{type(exc).__name__}: {exc}")

        def churner() -> None:
            rng = random.Random(config["seed"] + 1)
            for e in cfg["schedule"]:
                if e["kind"] != "churn":
                    continue
                if not wait_until(e["t"]):
                    return
                try:
                    c = Client(url, t0)
                except Exception as exc:  # noqa: BLE001  a failed connect is logged; the soak goes on
                    churn_stats["errors"] += 1
                    log("error", action="churn", error=f"{type(exc).__name__}: {exc}")
                    continue
                churn_stats["connects"] += 1
                log("connect")
                try:
                    if wait_until(e["t"] + e["drag_at"]) and (drag := sliders(c.params)):
                        p = rng.choice(drag)
                        steps = int(DRAG_S * DRAG_HZ)
                        for i in range(steps):
                            if stop.is_set():
                                break
                            v = p["lo"] + (p["hi"] - p["lo"]) * (0.5 + 0.5 * math.sin(2 * math.pi * i / steps))
                            c.send({"type": "set", "name": p["name"], "value": round(v, 4)})
                            churn_stats["sets"] += 1
                            stop.wait(1.0 / DRAG_HZ)
                        log("drag", param=p["name"], sets=steps)
                    wait_until(e["t"] + e["stay"])
                except Exception as exc:  # noqa: BLE001  a failed drag is logged; the soak goes on
                    churn_stats["errors"] += 1
                    log("error", action="churn", error=f"{type(exc).__name__}: {exc}")
                finally:
                    # An open client keeps receiving every frame: always close it.
                    churn_stats["refused"] += len(c.refused)
                    churn_stats["frames"] += c.counts["frame"]
                    c.close()
                    churn_stats["disconnects"] += 1
                    log("disconnect")

        threads = [threading.Thread(target=conductor, daemon=True), threading.Thread(target=churner, daemon=True)]
        for th in threads:
            th.start()

        samples: list[dict] = []
        out = Path(cfg["out_json"])
        last = [0] * len(cfg["packets_per_frame"])
        last_t = time.monotonic()
        next_at, next_flush = SAMPLE_S, FLUSH_S

        def snapshot() -> dict:
            nonlocal last, last_t
            now = time.monotonic()
            row: dict = {"t": round(now - t0, 3), "rss_kb": rss_kb(cfg["parent_pid"]),
                         "control_frames": control.counts["frame"]}
            if listener is not None:
                dt = now - last_t
                row["boards"] = [
                    {"packets": listener.packets[i], "bytes": listener.bytes[i], "frames": listener.frames[i],
                     "incomplete": listener.incomplete[i],
                     "fps": round((listener.frames[i] - last[i]) / dt, 3) if dt > 0 else None}
                    for i in range(len(last))
                ]
                last = list(listener.frames)
            last_t = now
            return row

        def write_partial() -> None:
            doc = {"meta": cfg["meta"], "config": config, "partial": True,
                   "schedule": cfg["schedule"], "rig_samples": rig_rows, "driver_samples": samples,
                   "driver_events": events, "health_samples": health}
            write_atomic(out, (json.dumps(doc) + "\n").encode())

        while wait_until(next_at):
            samples.append(snapshot())
            next_at += SAMPLE_S
            if next_at > next_flush:
                write_partial()
                next_flush += FLUSH_S
                b = samples[-1].get("boards") or []
                print(f"  driver t={samples[-1]['t']:7.0f}s rss {samples[-1]['rss_kb']} KB "
                      f"board fps {[x['fps'] for x in b]} actions {dict(actions)} churn {dict(churn_stats)}",
                      file=sys.stderr, flush=True)
        stop.set()
        for th in threads:
            th.join(timeout=10.0)
        control.close()
        final = {
            "kind": "final", "samples": samples, "events": events, "health": health,
            "actions": dict(actions),
            "client": {"control": {"counts": dict(control.counts), "refused": control.refused,
                                   "trigger_last": control.fired,
                                   "looks_seen": dict(control.looks_seen)},
                       "churn": dict(churn_stats)},
        }
        print(json.dumps(final), flush=True)
    finally:
        stop.set()


# ---- report -----------------------------------------------------------------------


def _f(d: dict | None, key: str, fmt: str = ".2f") -> str:
    return "-" if not d or d.get(key) is None else format(d[key], fmt)


def _dist_row(label: str, d: dict | None, fmt: str = ".2f") -> str:
    cells = " | ".join(_f(d, k, fmt) for k in ("min", "p50", "p90", "p99", "max"))
    return f"| {label} | {_f(d, 'n', 'd')} | {cells} |"


LOOPBACK_NOTE = """\
**Loopback run: no Wi-Fi, no WLED.** Every board in the room was moved to a
UDP listener on 127.0.0.1 in the driver process, which counts packets and
PUSH frames. What this answers for ADR-010: how often the collector runs
and how long it pauses with the real rig's allocations in play (DDP sink,
preview fan-out with client churn, slider sets through `call_soon`, look
recalls with crossfades, triggers), whether those pauses
reach the frame cadence, and whether memory, threads or modules grow over
the run. What it does not answer: Wi-Fi loss and latency, what each board
actually shows (`leds.fps`), board-side drift over hours (wled/WLED#4320),
or the router. The health poller ran but polled 127.0.0.1, where no WLED
answers, so its board data here is failures by construction. ADR-010's
other open caveat, the R-8 host (Pi 5 / N100), is not touched either.
The real-rig run of this bench answers the board side."""


def render_md(doc: dict, json_name: str) -> str:
    meta, cfg, s = doc["meta"], doc["config"], doc["summary"]
    p, g = s["pacing"], s["gc"]
    loopback = cfg["mode"] == "loopback"
    period_ms = 1000.0 / cfg["fps"]
    lines = [
        f"# Aura rig soak — {meta['date']}, {meta['label']}",
        "",
        f"- bench: `bench/bench_soak.py` @ `{meta['git_sha']}`; raw data `{json_name}`",
        (f"- host: {meta['cpu'] or meta['machine']}, {meta['platform']}, Python {meta['python']}, "
         f"GC thresholds {tuple(meta['gc_thresholds'])}"),
        f"- rig: `python -m pewpew {' '.join(cfg.get('rig_argv', []))}`" if cfg.get("rig_argv") else "- rig: -",
        (f"- mode: {'loopback (local UDP listeners)' if loopback else 'DDP to the real boards'}; "
         f"room `{Path(cfg['room']).name}`, boards {', '.join(cfg['boards'])}; "
         f"render {cfg['fps']:g} fps, DDP {cfg['ddp_fps']:g} fps"),
        f"- run: {p['span_s'] / 60:.1f} min of {cfg['duration_s'] / 60:.1f} planned"
        + ("; **stopped early**" if s["stopped_early"] else "")
        + f"; seed {cfg['seed']}; note: {meta.get('note') or '(none)'}",
        "- A measurement, not a gate (T-5): distributions below, no pass/fail.",
        "",
    ]
    if loopback:
        lines += [LOOPBACK_NOTE, ""]
    acts = s.get("actions") or {}
    churn = (s.get("client") or {}).get("churn") or {}
    lines += [
        "## Scripted actions",
        "",
        f"- look recalls sent: {acts.get('recall', 0)}; trigger fires sent: {acts.get('fire', 0)}",
        (f"- churn client: {churn.get('connects', 0)} connects, {churn.get('disconnects', 0)} disconnects, "
         f"{churn.get('sets', 0)} slider sets, {churn.get('refused', 0)} refused, {churn.get('errors', 0)} errors"),
        "",
        "## Frame pacing",
        "",
        (f"Interval between consecutive frames handed to the sinks, from {p['from_s']:g} s on; "
         f"period {period_ms:.2f} ms. The first {p['startup']['intervals']} intervals (startup) are "
         f"left out; the longest was {_f(p['startup'], 'max_ms', '.1f')} ms."),
        "",
        "| metric | n | min | p50 | p90 | p99 | max |",
        "|---|---|---|---|---|---|---|",
        _dist_row("interval ms", p["interval_ms"]),
        _dist_row("abs error ms", p["abs_error_ms"]),
        "",
        (f"- {p['fps']:.2f} fps over {p['frames']} frames; {p['over_5ms']} intervals off by more than 5 ms, "
         f"{p['over_one_frame']} by more than a frame ({p['over_one_frame_with_gc']} of them with a GC pause inside)"),
        (f"- deadline skips: {(s['skips'] or {}).get('events', '-')} events, "
         f"{(s['skips'] or {}).get('missed_frames', '-')} schedule slots skipped; "
         f"gaps over {WATCHDOG_S:g} s (the unattended run's watchdog timeout): {s['watchdog_5s_would_fire']}"),
        "- sink drivers at the end (dropped = coalesced by newest-wins, expected when a sink's rate is "
        "below the loop's): " + "; ".join(
            f"{k} dropped {v['dropped']}, errors {v['errors']}"
            + (f", frames sent {v['frames_sent']}" if v.get("frames_sent") is not None else "")
            for k, v in (s.get("drivers_end") or {}).items()),
        "",
        "## GC",
        "",
        (f"{g['collections']} collections, {g['total_ms']:.1f} ms in total; "
         f"{g['over_period']} longer than one frame period. Counts by generation from the callback: "
         f"{s['gc_counts_by_gen']}."),
        "",
        "| generation | n | min ms | p50 | p90 | p99 | max |",
        "|---|---|---|---|---|---|---|",
        *[_dist_row(gen, v["pause_ms"], ".3f") for gen, v in g["by_gen"].items()],
        _dist_row("all", g["pause_ms"], ".3f"),
        "",
        "## Per-board delivery",
        "",
    ]
    if loopback and s.get("boards"):
        sent = next((d.get("frames_sent") for d in (s.get("drivers_end") or {}).values()
                     if d.get("frames_sent") is not None), None)
        lines += [
            f"Counted at the listener per {SAMPLE_S:g} s window; the DDP sink sent {sent} frames to each board.",
            "",
            "| board | windows | min fps | p50 | p90 | p99 | max | frames | incomplete |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for b in s["boards"]:
            lines.append(_dist_row(b["board"], b["fps"]) + f" {b['frames']} | {b['incomplete_frames']} |")
    else:
        lines += [
            "From the health poller's `/json/info` (`leds.fps`, `uptime`), as the page received it.",
            "",
            "| board | samples | fps min | p50 | p90 | max | first-tenth median | last-tenth median | reboots | RSSI |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for b in s["health"]:
            d = b["fps"]
            cells = " | ".join(_f(d, k, ".1f") for k in ("min", "p50", "p90", "max"))
            lines.append(f"| {b['board']} | {b['samples']} | {cells} | {b['fps_first_tenth_median']} | "
                         f"{b['fps_last_tenth_median']} | {b['reboots']} | {b['rssi_range']} |")
    rss, th, mod = s["rss_kb"] or {}, s["threads"] or {}, s["modules"] or {}

    def tr(name: str, d: dict, unit: str) -> str:
        slope = d.get("per_hour_after_warmup")
        return (f"| {name} | {_f(d, 'first', '.0f')} | {_f(d, 'last', '.0f')} | {_f(d, 'min', '.0f')} | "
                f"{_f(d, 'max', '.0f')} | {'-' if slope is None else f'{slope:+.1f} {unit}/h'} |")

    lines += [
        "",
        "## Process",
        "",
        f"Sampled every {SAMPLE_S:g} s; slope fitted after the first {WARMUP_S:g} s.",
        "",
        "| series | first | last | min | max | slope |",
        "|---|---|---|---|---|---|",
        tr("RSS KB", rss, "KB"),
        tr("threads", th, "threads"),
        tr("modules", mod, "modules"),
        "",
    ]
    groups = s.get("thread_groups_first_last")
    if groups:
        first, last = groups
        changed = {k: (first.get(k, 0), last.get(k, 0)) for k in sorted(set(first) | set(last))
                   if first.get(k, 0) != last.get(k, 0)}
        lines.append(f"Thread groups that changed first→last sample: {changed or 'none'}.")
        lines.append("")
    if s["outliers"]:
        lines += [
            f"## Largest intervals over one frame of error (top {len(s['outliers'])})",
            "",
            "| t s | interval ms | GC ms inside | gens | nearest rig log line (±2 s) |",
            "|---|---|---|---|---|",
            *[f"| {o['t_s']:.1f} | {o['interval_ms']:.1f} | {o['gc_ms']:.2f} | {o['gc_gens'] or '-'} | "
              f"{(o['near'] or '-')[:80]} |" for o in s["outliers"]],
            "",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--room", type=Path, default=DEFAULT_ROOM, help="room map file (default: the 60-bar example)")
    ap.add_argument("--loopback", action="store_true", help="send DDP to local UDP listeners, not the boards")
    ap.add_argument("--duration", type=float, default=DURATION_S, help=f"seconds (default {DURATION_S:g})")
    ap.add_argument("--fps", type=float, default=FPS, help=f"render rate (default {FPS:g})")
    ap.add_argument("--ddp-fps", type=float, default=DDP_FPS, help=f"DDP rate (default {DDP_FPS:g})")
    ap.add_argument("--master-cap", type=float, default=1.0, help="the rig's master cap (default 1)")
    ap.add_argument("--port", type=int, default=None, help="preview port (default: a free one)")
    ap.add_argument("--seed", type=int, default=SEED, help=f"schedule seed (default {SEED})")
    ap.add_argument("--label", default=platform.node() or "unknown-host")
    ap.add_argument("--note", default="", help="rig settings to record (router, firmware, ...)")
    ap.add_argument("--out", default=None, help="JSON output path (the .md goes beside it)")
    ap.add_argument("--keep-temp", action="store_true", help="keep the temp dir (looks, trigger log, edits)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit without sending")
    ap.add_argument("--driver", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.driver is not None:
        driver_main(args.driver)
        return
    if args.duration <= END_MARGIN_S + CHURN_STAY_S[1]:
        raise SystemExit(f"--duration must be above {END_MARGIN_S + CHURN_STAY_S[1]:g} s")
    run(args)


if __name__ == "__main__":
    main()
