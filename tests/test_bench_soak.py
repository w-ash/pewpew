"""bench/bench_soak.py: the summary over canned samples, and the seeded
schedule. The soak itself runs for hours and is never run here."""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pytest

from bench.bench_soak import (
    DEFAULT_MAP,
    WATCHDOG_S,
    Client,
    Recorder,
    RowLog,
    board_summary,
    build_schedule,
    check_loopback,
    health_summary,
    prepare,
    probe_installed,
    sliders,
    summarize,
    trend,
)
from fakes import LoopThread, aura_rig, peers, preview_sink, solid, wait_until
from pewpew.aura import pipeline
from pewpew.mapping import line
from pewpew.rig.runtime import ddp_targets, load_rig, target_names
from pewpew.watchdog import TIMEOUT_S

PERIOD = 1.0 / 60.0


def frames_with_gap(gap_at: float = 6.0, gap: float = 0.050) -> np.ndarray:
    t = np.arange(0.0, 10.0, PERIOD)
    t[t > gap_at] += gap - PERIOD  # one interval of `gap` seconds instead of one period
    return t


def test_summary_pacing_and_gc():
    frames = frames_with_gap()
    gap_start = frames[np.argmax(np.diff(frames))]
    gc_t = np.array([2.0, gap_start + 0.010, 8.0])
    gc_ms = np.array([0.2, 3.0, 0.3])
    gc_gen = np.array([0, 2, 0])
    events = [(gap_start + 0.5, "reloaded Wave (t=6.5)"), (9.9, "far away")]
    s = summarize(frames, PERIOD, gc_t, gc_ms, gc_gen, events, start_s=1.0 - PERIOD / 2)
    p = s["pacing"]
    assert p["over_one_frame"] == 1
    assert p["over_one_frame_with_gc"] == 1
    assert p["startup"]["intervals"] == 60  # the first second, left out of the distribution
    assert abs(p["interval_ms"]["max"] - 50.0) < 1e-6
    assert abs(p["interval_ms"]["p50"] - PERIOD * 1000.0) < 1e-6
    (o,) = s["outliers"]
    assert o["gc_gens"] == [2] and abs(o["gc_ms"] - 3.0) < 1e-6
    assert o["near"] == "reloaded Wave (t=6.5)"
    g = s["gc"]
    assert g["collections"] == 3 and g["over_period"] == 0
    assert g["by_gen"]["0"]["collections"] == 2 and g["by_gen"]["2"]["pause_ms"]["max"] == 3.0


def test_gc_pause_that_starts_before_the_interval_still_counts():
    frames = frames_with_gap()
    i = int(np.argmax(np.diff(frames)))
    s = summarize(frames, PERIOD, np.array([frames[i] - 0.002]), np.array([5.0]), np.array([1]))
    assert abs(s["outliers"][0]["gc_ms"] - 3.0) < 1e-6  # 5 ms pause, 3 ms of it inside


def test_trend_slope_after_warmup():
    rows = [{"t": t, "rss": 1000.0 + (t if t >= 120 else 500.0)} for t in range(0, 3600, 10)]
    d = trend(rows, "rss")
    assert d["first"] == 1500.0 and abs(d["per_hour_after_warmup"] - 3600.0) < 1e-6


def test_board_summary_leaves_out_the_startup_window():
    rows = [{"boards": [{"board": "B", "fps": 1.0, "frames": 1, "packets": 1, "incomplete": 0},
                        {"board": "A", "fps": f, "frames": n, "packets": 3 * n, "incomplete": 0}]}
            for f, n in ((12.0, 120), (40.0, 520), (39.9, 919))]
    (b,) = board_summary(rows, ["A"])  # by controller id, not by position
    assert b["board"] == "A" and b["fps"]["min"] == 39.9 and b["frames"] == 919


def spare_first(tmp_path):
    """The example canopy with a hosted controller that drives no pixels
    declared first, so declaration order and target order differ."""
    doc = json.loads(DEFAULT_MAP.read_text())
    doc["controllers"].insert(0, {"id": "spare", "profile": doc["controllers"][0]["profile"], "host": "10.0.0.99"})
    src = tmp_path / "src.arrangement.json"
    src.write_text(json.dumps(doc))
    return src


def test_loopback_moves_every_target_to_its_own_listener_by_id(tmp_path):
    src = spare_first(tmp_path)
    names = target_names(load_rig(src)[0])
    assert "spare" not in names
    ports = [50001 + i for i in range(len(names))]
    _, out = prepare(argparse.Namespace(map=src), tmp_path, ports)
    rig, _ = load_rig(out)
    assert [(n, b.host, b.port) for n, b in zip(target_names(rig), ddp_targets(rig), strict=True)] == [
        (n, "127.0.0.1", p) for n, p in zip(names, ports, strict=True)
    ]
    assert {c.id: c.host for c in rig.controllers}["spare"] is None  # no host left for anything to reach


def test_loopback_aborts_before_streaming_to_another_host(tmp_path):
    src = spare_first(tmp_path)
    names = target_names(load_rig(src)[0])
    ports = [50001 + i for i in range(len(names))]
    with pytest.raises(SystemExit, match="10.0.0.11"):
        check_loopback(src, names, ports)  # the real hosts
    _, out = prepare(argparse.Namespace(map=src), tmp_path, ports)
    check_loopback(out, names, ports)
    with pytest.raises(SystemExit, match="not the listeners"):
        check_loopback(out, names, ports[::-1])
    doc = json.loads(out.read_text())
    doc["controllers"][0]["host"] = "10.0.0.99"  # a controller with no pixels still gets no host
    out.write_text(json.dumps(doc))
    with pytest.raises(SystemExit, match="spare -> 10.0.0.99"):
        check_loopback(out, names, ports)


def test_loopback_refuses_a_port_per_target_mismatch(tmp_path):
    src = spare_first(tmp_path)
    with pytest.raises(SystemExit, match="listener ports"):
        prepare(argparse.Namespace(map=src), tmp_path, [50001])


def test_the_probe_loop_replaces_the_loop_the_aura_builds(fake_ops):
    rec = Recorder(1.0, 60.0)
    with probe_installed(rec):  # the patch soak() installs around the rig run
        loop = pipeline.build_aura_pipeline(solid(1.0), line(4)).loop(60.0)
    assert rec.loop is loop


def test_health_summary_counts_uptime_drops():
    samples = [{"host": "10.0.0.11", "fps": f, "uptime": u, "rssi": -60}
               for f, u in ((40, 100), (39, 106), (38, 3), (40, 9))]
    (b,) = health_summary(samples)
    assert b["reboots"] == 1 and b["uptime_first_last"] == [100, 9]


def test_schedule_is_seeded_and_ordered():
    a, b = build_schedule(1200.0, 1), build_schedule(1200.0, 1)
    assert a == b and a != build_schedule(1200.0, 2)
    assert [e["t"] for e in a] == sorted(e["t"] for e in a)
    assert {e["kind"] for e in a} == {"recall", "fire", "churn"}
    assert all(e["t"] < 1200.0 - 10.0 for e in a)
    churn = [e for e in a if e["kind"] == "churn"]
    assert all(1.0 <= e["drag_at"] and e["drag_at"] + 5.0 < e["stay"] for e in churn)


def test_watchdog_threshold_matches_the_unattended_watchdog():
    assert WATCHDOG_S == TIMEOUT_S  # the JSON key `watchdog_5s_would_fire` names this value


def test_row_log_writes_the_same_json_as_live_rows():
    rows = [{"t": 10.004, "ticks": 600, "interval_ms": {"p50": 16.667, "p99": 21.3, "max": 34.1},
             "gc": [1, 0, 0], "thread_groups": {"MainThread": 1, "Thread-# (serve)": 3},
             "drivers": {"DdpSink": {"dropped": 0, "errors": 0, "frames_sent": None}}},
            {"t": 20.0, "ticks": 1200, "interval_ms": None, "gc": [0, 0, 0], "thread_groups": {}, "drivers": {}}]
    log = RowLog()
    for row in rows:
        log.append(row)
    assert len(log) == 2 and all(isinstance(line, str) for line in log._lines)
    assert json.dumps({"rig_samples": log.rows()}, indent=1) == json.dumps({"rig_samples": rows}, indent=1)


def test_the_soak_client_keeps_what_the_soak_reads(fake_ops):
    rig = aura_rig()
    with preview_sink(line(4), control=rig.control) as sink, LoopThread(rig.calls):
        client = Client(f"ws://127.0.0.1:{sink.port}/", time.monotonic(), health=[])
        try:
            wait_until(lambda: client.params and len(peers(sink)) == 1)
            client.send({"type": "set", "name": "layers.base.solid.red", "value": 3})
            sink.send(0.5, rig.frame(0.5))
            wait_until(lambda: client.refused and client.counts["frame"] == 1)
        finally:
            client.close()
    rgb = [f"layers.base.solid.{c}" for c in ("red", "green", "blue")]
    assert [p["name"] for p in client.params] == [*rgb, *(f"layers.base.{c}" for c in ("opacity", "blend", "enabled"))]
    assert [p["name"] for p in sliders(client.params)] == rgb  # not the layer's own controls
    assert client.fired == []
    (refused,) = client.refused
    assert refused["name"] == "layers.base.solid.red" and refused["control"] == "set" and refused["t"] >= 0
    assert refused["reason"].endswith("must be within 0.0..1.0, got 3.0")
    assert client.counts["hello"] == client.counts["aura"] == 1 and client.health == []
