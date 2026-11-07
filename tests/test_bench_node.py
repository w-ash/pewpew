"""bench/bench_node.py: the summary of a packet trace, a recorded run
against the fake node on a fake clock, and the dry run. The trials
themselves need a person, a node and its router."""

from __future__ import annotations

from pathlib import Path

import pytest

from bench.bench_node import main, record, summarize
from fake_node import FakeNode, clean, ready, source_for, synthetic_trace
from fakes import FakeTime
from pewpew.audio import keys, wire
from pewpew.audio.analysis import restart_gap
from pewpew.audio.wire import HEADER


def test_the_summary_reports_each_gap_but_a_reboots_epoch() -> None:
    summary = summarize(synthetic_trace())
    assert summary["reboots"] == 1 and summary["stray"] == 1 and summary["late"] >= 1
    lost = [g for g in summary["gaps"] if g["samples"] == 2 * wire.SAMPLES]  # packets 150 and 151
    assert len(lost) == 1 and summary["longest_gap_s"] == pytest.approx(2 * wire.SAMPLES / wire.RATE)
    assert sum(g["samples"] for g in summary["gaps"]) == summary["missing"]
    assert 0 < summary["loss"] < 0.01 and summary["seconds"] > 11


def test_a_loss_as_long_as_an_epochs_jump_is_a_gap() -> None:
    lost = round(restart_gap(wire.RATE) / wire.SAMPLES)  # 50 packets: the very jump a new epoch makes
    summary = summarize(synthetic_trace(clean(seconds=6.0, jitter=0.0, lose=set(range(200, 200 + lost)))))
    assert summary["reboots"] == summary["followed"] == 0
    assert [g["samples"] for g in summary["gaps"]] == [restart_gap(wire.RATE)] == [summary["missing"]]
    assert summary["longest_gap_s"] == pytest.approx(0.5)


def test_a_run_records_each_packet_with_the_tick_that_drained_it() -> None:
    key = keys.ensure("aabbccddeeff")
    node = FakeNode(key)
    ft = FakeTime()
    source = source_for(node, now=ft.now)
    try:
        source.step()
        node.serve()
        sent = []

        def sleep(seconds: float) -> None:  # one slot: the node sends what came due
            ft.sleep(seconds)
            sent.extend(node.send(1 + (len(sent) % 3 == 0)))
            ready(source._sock)

        trace = record(source, 0.5, now=ft.now, sleep=sleep)
    finally:
        source.stop()
        node.close()
    assert [HEADER.unpack(head)[3] for head, _, _ in trace.records] == [p.index for p in sent[:len(trace.records)]]
    ticks = [tick for _, _, tick in trace.records]
    assert ticks == sorted(ticks) and ticks[0] == 2 and len(trace.records) >= 30
    assert summarize(trace)["missing"] == 0


def test_the_dry_run_names_the_node_and_subscribes_to_nothing(capsys, audit_log: Path) -> None:
    main(["10.0.0.42", "--allow-host", "10.0.0.42", "--dry-run"])
    out = capsys.readouterr().out
    assert "capture node 10.0.0.42 at 10.0.0.42" in out and "nothing subscribed" in out
    assert not audit_log.exists()
    with pytest.raises(SystemExit, match="outside --unattended, a capture node is a bench node"):
        main(["10.0.0.42", "--dry-run"])
