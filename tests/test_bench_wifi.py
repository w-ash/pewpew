"""bench/bench_wifi.py: target parsing and the summary over canned
`/json/info` samples. The streaming itself needs the real rig."""

from __future__ import annotations

import pytest

from bench.bench_wifi import extract, parse_targets, summarize

INFO = {
    "ver": "16.0.1",
    "leds": {"count": 1280, "fps": 39, "pwr": 0},
    "wifi": {"bssid": "x", "rssi": -61, "signal": 78, "channel": 6},
    "live": True,
    "lip": "10.0.0.2",
    "uptime": 812,
    "freeheap": 151000,
}


def sample(board, rate, trial, t, fps, uptime, rssi=-60, live=True, lip="10.0.0.2"):
    info = {**INFO, "leds": {"count": 1280, "fps": fps}, "wifi": {"rssi": rssi, "channel": 6},
            "uptime": uptime, "live": live, "lip": lip}
    return {"board": board, "rate": rate, "trial": trial, "t": t, "ok": True, **extract(info)}


CELLS = [
    {"rate": 40.0, "trial": 0, "sent_fps": 40.0},
    {"rate": 60.0, "trial": 0, "sent_fps": 59.9},
    {"rate": 40.0, "trial": 1, "sent_fps": 40.0},
    {"rate": 60.0, "trial": 1, "sent_fps": 60.0},
]


def test_extract_reads_the_recorded_fields():
    assert extract(INFO) == {
        "fps": 39, "count": 1280, "rssi": -61, "channel": 6, "uptime": 812,
        "live": True, "lip": "10.0.0.2", "freeheap": 151000, "ver": "16.0.1",
    }


def test_summary_distributions_reboots_and_pass_k():
    samples = [
        # board a: holds 40 in both trials; at 60 it delivers ~45.
        sample("a", 40.0, 0, 1.0, 39, 100, rssi=-58),
        sample("a", 40.0, 0, 2.0, 40, 101, rssi=-64),
        sample("a", 60.0, 0, 3.0, 45, 102),
        sample("a", 40.0, 1, 5.0, 38, 104),
        sample("a", 60.0, 1, 7.0, 44, 106, lip="10.0.0.9"),
        # board b: reboots during 60 fps trial 1 (uptime drops) but keeps fps.
        sample("b", 40.0, 0, 1.5, 40, 500),
        sample("b", 60.0, 0, 3.5, 58, 502),
        sample("b", 40.0, 1, 5.5, 40, 504),
        sample("b", 60.0, 1, 7.5, 59, 3, live=False, lip=""),
        {"board": "b", "rate": 60.0, "trial": 1, "t": 8.0, "ok": False, "error": "TimeoutError: timed out"},
    ]
    rows = {(r["board"], r["rate"]): r for r in summarize(samples, CELLS, hold=0.9, sender_ip="10.0.0.2")}

    a40 = rows[("a", 40.0)]
    assert a40["fps"]["min"] == 38 and a40["fps"]["median"] == 39 and a40["fps"]["max"] == 40
    assert a40["rssi_range"] == [-64, -58]
    assert (a40["trials_held"], a40["trials"], a40["pass_k"]) == (2, 2, True)

    a60 = rows[("a", 60.0)]
    assert a60["fps_ratio_median"] == pytest.approx(44.5 / 59.95)
    assert (a60["trials_held"], a60["pass_k"]) == (0, False)
    assert a60["foreign_source"] == 1

    b60 = rows[("b", 60.0)]
    assert b60["reboot_trials"] == 1
    assert b60["poll_failures"] == 1 and b60["samples"] == 3
    # Not live with an empty `lip` is not a foreign source.
    assert b60["not_live"] == 1 and b60["foreign_source"] == 0
    assert b60["trials_held"] == 1  # trial 0 held; the reboot costs trial 1
    assert rows[("b", 40.0)]["reboot_trials"] == 0
    assert a40["versions"] == ["16.0.1"] and a40["led_counts"] == [1280]


def test_parse_targets_fills_bare_hosts_contiguously():
    boards = parse_targets(["10.0.0.11", "10.0.0.12:4049", "10.0.0.13=5000+64"], 1280)
    assert [(b.host, b.port, b.start, b.count) for b in boards] == [
        ("10.0.0.11", 4048, 0, 1280),
        ("10.0.0.12", 4049, 1280, 1280),
        ("10.0.0.13", 4048, 5000, 64),
    ]
    with pytest.raises(ValueError, match="different board"):
        parse_targets(["10.0.0.11", "10.0.0.11"], 1280)
    with pytest.raises(ValueError, match="overlap"):
        parse_targets(["a=0+100", "b=50+100"], 1280)
