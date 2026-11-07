"""Capture nodes, host side (pewpew.audio.net): the receiver's rules on
packets made in the test (order, late, duplicate, stray, loss, reboot,
backlog), a packet trace replayed over a seeded signal and through `Run`,
and `NetSource` against a fake node on loopback (the signed subscription,
refusals, finding the node again, the lost rule, the tier rules, the
audit records, and a loop that never waits on the supervisor)."""

from __future__ import annotations

import dataclasses
import errno
import io
import json
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from audio_signals import RATE, frame_bytes, kick_loop, noise, write_wav
from fake_node import MAC, FakeNode, clean, ready, source_for, synthetic_trace
from fakes import FakeTime, build, no_watch
from pewpew.__main__ import main, parse
from pewpew.audio import AudioFeatures, keys, net, wire
from pewpew.audio.analysis import HOP_S, LOST_S, Analyser
from pewpew.audio.clock import READY_S
from pewpew.audio.net import (
    OPENING_S,
    NetSource,
    NodeInfo,
    Receiver,
    Trace,
    TraceSource,
    looped_pcm,
    node_host,
    node_source,
)
from pewpew.audio.wire import Denial, Packet
from pewpew.render import SlotClock
from pewpew.run import Run

FPS = 60.0
SLOT = 1.0 / FPS
PER_PACKET = wire.SAMPLES / RATE
TRACE = Path(__file__).parent / "fixtures" / "audio_net" / "synthetic.trace"


def made(start: int, count: int = 1, *, nonce: int = 1, flags: int = 0) -> list[Packet]:
    """`count` packets of a seeded signal from sample `start`."""
    signal = noise(1.0, seed=1)
    indices = range(start, start + count * wire.SAMPLES, wire.SAMPLES)
    return [Packet(index, nonce, flags, looped_pcm(signal, index, wire.SAMPLES)) for index in indices]


def failing(exc: BaseException) -> Callable[[str, float], dict]:
    """A `fetch` that raises `exc`."""
    def fetch(address: str, timeout: float) -> dict:
        raise exc
    return fetch


def streamed(receiver: Receiver, seconds: float, *, start_tick: int = 1, nonce: int = 1, first: int = 0,
             delay: float = 0.004) -> int:
    """Feed `seconds` of on-time packets, each in the tick after it arrives; returns the next index."""
    index, k = first, start_tick
    clock = SlotClock(FPS, start=(start_tick - 1) / FPS)
    while (k - start_tick) / FPS < seconds:
        t = clock.advance()
        due = []
        while (index - first + wire.SAMPLES) / RATE + delay <= t - (start_tick - 1) / FPS:
            due += made(index, nonce=nonce)
            index += wire.SAMPLES
        receiver.receive(due, t)
        k += 1
    return index


# ---- the receiver ----------------------------------------------------------------


def test_packets_go_in_index_order_and_late_ones_and_duplicates_are_dropped() -> None:
    r = Receiver(FPS)
    a, b, c, d = made(0, 4)
    blocks = r.receive([b, a], SLOT)  # reordered within a tick
    assert [blk.start for blk in blocks] == [blocks[0].start, blocks[0].start + 480]
    assert r.receive([b, c], 2 * SLOT)[0].end == blocks[1].end + 480  # b again: a duplicate, so late
    assert r.receive([a], 3 * SLOT) == []  # behind what was taken: late
    assert r.counts.late == 2 and r.counts.packets == 3
    assert len(r.receive([d], 4 * SLOT)) == 1 and r.counts.missing == 0


def test_a_lost_packet_is_a_gap_the_analysis_fills_and_holds_seven_hops() -> None:
    def held(lose: set[int]) -> tuple[int, int]:
        trace = synthetic_trace(clean(seconds=4.0, jitter=0.0, drift_ppm=0.0, lose=lose))
        source, analyser = TraceSource(trace, noise(4.0, seed=2)), Analyser(RATE)
        clock, hops = SlotClock(FPS), []
        for _ in range(int(4.0 * FPS)):
            hops += analyser.feed(source.take(clock.advance())).hops
        return sum(h.held for h in hops), source.receiver.counts.missing

    assert held({200}) == (held(set())[0] + 7, wire.SAMPLES)


def test_a_stray_far_future_index_is_dropped_and_the_real_packets_go_on() -> None:
    r = Receiver(FPS)
    nxt = streamed(r, 1.0)
    stray = Packet(nxt + (1 << 40), 1, 0, made(nxt)[0].pcm)
    t = 1.0 + 2 * SLOT
    blocks = r.receive([stray, *made(nxt, 2)], t)
    assert r.counts.stray == 1 and len(blocks) == 2 and r.counts.late == 0


def test_strays_that_keep_coming_start_a_new_epoch() -> None:
    r = Receiver(FPS)
    nxt = streamed(r, 1.0)
    jumped = nxt + (1 << 40)  # say the node's index really did jump
    clock = SlotClock(FPS, start=1.0)
    taken = []
    for _ in range(int((LOST_S + 0.2) * FPS)):
        t = clock.advance()
        taken += r.receive(made(jumped), t)
        jumped += wire.SAMPLES
    assert taken and 0 < r.counts.stray <= LOST_S * FPS + 1


def test_a_far_future_first_packet_holds_the_input_lost_only_for_half_a_second() -> None:
    r = Receiver(FPS)
    r.receive([Packet(1 << 40, 1, 0, made(0)[0].pcm)], SLOT)  # the epoch's first packet: nothing to check it by
    streamed(r, 10.0, start_tick=2)
    assert r.counts.followed == 1 and r.counts.late <= round(LOST_S / PER_PACKET) + 2
    assert r.counts.packets > 0.9 * 10.0 / PER_PACKET and r.heard is not None and r.heard > 9.9


def test_the_loss_share_counts_only_the_part_of_an_outage_its_window_holds() -> None:
    r = Receiver(FPS)
    nxt = streamed(r, 10.0) + 30 * RATE  # no packet from 10 s to 40 s; the node's index keeps counting
    seen = {}
    for start, until in ((40.0, 41.0), (41.0, 45.0), (45.0, 49.0)):
        nxt = streamed(r, until - start, start_tick=round(start * FPS) + 1, first=nxt)
        seen[until] = r.loss
    assert r.counts.missing == 30 * RATE
    for until, share in seen.items():  # the window's own share: what of (until - 10, until] had no packet
        assert share == pytest.approx((50.0 - until) / 10.0, abs=0.01)


def test_a_reboot_starts_an_epoch_that_restarts_the_grid_and_the_fit_and_old_packets_are_stale() -> None:
    r = Receiver(FPS)
    old_end = streamed(r, READY_S + 1.0, nonce=1)
    assert r.clock.line() is not None
    before = r.receive(made(old_end, nonce=1), READY_S + 1.0 + SLOT)[0]
    after = r.receive(made(0, nonce=2), READY_S + 1.0 + 2 * SLOT)  # booted again: index 0, a new nonce
    assert r.counts.reboots == 1 and r.clock.line() is None
    assert after[0].start - before.end >= LOST_S * RATE  # the analysis restarts its grid
    assert r.receive(made(old_end + 480, nonce=1), READY_S + 1.0 + 3 * SLOT) == [] and r.counts.stale == 1


def test_a_stalled_loops_backlog_is_taken_not_dropped_as_strays() -> None:
    r = Receiver(FPS)
    nxt = streamed(r, READY_S + 1.0)
    backlog = made(nxt, round(2.0 / PER_PACKET))  # 2 s of packets drained in one late tick
    blocks = r.receive(backlog, READY_S + 1.0 + 2.0)
    assert len(blocks) == len(backlog) and r.counts.stray == 0
    analyser = Analyser(RATE)
    analyser.feed([blocks[0]])
    assert len(analyser.feed(blocks[1:]).hops) == 20  # the backlog rule: at most 20 hops a tick


def test_a_30_s_gap_restarts_the_grid_with_no_zero_fill() -> None:
    trace = synthetic_trace(clean(seconds=40.0, jitter=0.0, lose=set(range(500, 500 + round(30 / PER_PACKET)))))
    features = AudioFeatures(TraceSource(trace, noise(1.0, seed=2)), fps=FPS)
    clock = SlotClock(FPS)
    for _ in range(int(40 * FPS)):
        features.before_frame(clock.advance())
    state = features.state()
    assert state["restarts"] == 1 and state["filled"] == 0 and state["input"]["stray"] == 0


def test_the_fit_follows_a_drifting_node_within_a_slot() -> None:
    trace = synthetic_trace(clean(seconds=30.0, drift_ppm=50.0))
    source = TraceSource(trace, noise(1.0, seed=2))
    clock = SlotClock(FPS)
    for _ in range(int(30 * FPS)):
        source.take(clock.advance())
    period = PER_PACKET * (1 + 50e-6)
    for k in (1000, 2000, 3000):  # each packet's true arrival, before jitter, against the line
        arrival = (k + 1) * period + 0.004
        mapped = source.time(source.receiver._offset + (k + 1) * wire.SAMPLES)
        assert mapped is not None and 0.0 <= mapped - arrival <= SLOT + 0.004


# ---- a trace ---------------------------------------------------------------------


def test_the_synthetic_trace_is_its_scenario_and_round_trips(regen_goldens: bool) -> None:
    trace = synthetic_trace()
    if regen_goldens:
        TRACE.parent.mkdir(parents=True, exist_ok=True)
        TRACE.write_bytes(trace.to_bytes())
    assert TRACE.read_bytes() == trace.to_bytes()  # the scenario and the record layout, unchanged
    assert Trace.from_bytes(trace.to_bytes()) == trace and len(trace.to_bytes()) == 20 + 28 * len(trace.records)
    with pytest.raises(ValueError, match="not a packet trace"):
        Trace.from_bytes(trace.to_bytes()[:-1])


def replay(seconds: float = 12.0) -> tuple[list[bytes], dict]:
    """The synthetic trace through `AudioFeatures`: each frame's bytes, and the last state."""
    features = AudioFeatures(TraceSource(Trace.from_bytes(TRACE.read_bytes()), kick_loop(124.0, 2.0)), fps=FPS)
    clock, out = SlotClock(FPS), []
    for _ in range(int(seconds * FPS)):
        t = clock.advance()
        features.before_frame(t)
        out.append(frame_bytes(features.at(t)))
    return out, features.state()


def test_a_trace_replays_its_loss_reorder_duplicate_stray_and_reboot_byte_for_byte() -> None:
    first, state = replay()
    assert replay()[0] == first and len(set(first)) > 100
    node = state["input"]
    assert node["kind"] == "trace" and node["reboots"] == 1 and node["stray"] == 1 and node["late"] >= 1
    # Lost: packets 150, 151 and 420, the stray's own slot, and each late one but the duplicate.
    assert node["missing"] == (3 + 1 + node["late"] - 1) * wire.SAMPLES


# ---- in a run --------------------------------------------------------------------


def trace_run_frames(tmp_path: Path, seconds: float = 5.0) -> list[bytes]:
    """5 s of the synthetic trace through a built `Run` of geq, tick by tick."""
    wav = write_wav(tmp_path / "x.wav", noise(0.1))
    run = build(["run", "geq", "--audio", str(wav), "--ansi"])
    source = TraceSource(Trace.from_bytes(TRACE.read_bytes()), kick_loop(124.0, 2.0))
    run = type(run)(dataclasses.replace(run.launch, audio=source), ansi_stream=io.StringIO(), now=lambda: 0.0,
                    sleep=lambda s: None, watch=no_watch)
    assert run.audio is not None and run.audio.source is source and run.capture is None
    clock, out = SlotClock(FPS), []
    for _ in range(int(seconds * FPS)):
        t = clock.advance()
        for hook in run.loop._before:
            hook(t)
        out.append(run.fader.advance_to(t).tobytes() + frame_bytes(run.audio.at(t)))
    return out


def test_a_trace_through_run_is_byte_identical_across_two_runs(tmp_path: Path) -> None:
    first = trace_run_frames(tmp_path)
    assert trace_run_frames(tmp_path) == first and len(set(first)) > 30


# ---- naming a node and the tier rules ----------------------------------------------------


@pytest.mark.parametrize("name, host", [
    ("pewpew-line-1", "pewpew-line-1.local"), ("pewpew-line-1.local", "pewpew-line-1.local"),
    ("10.0.0.42", "10.0.0.42"), (" pewpew-line-1 ", "pewpew-line-1.local"),
])
def test_a_node_is_named_by_its_mdns_name_or_its_ipv4_address(name: str, host: str) -> None:
    assert node_host(name) == host


@pytest.mark.parametrize("name, reason", [
    ("", "net: needs a node"), ("bad name", "is not a node's name"), ("a/b", "is not a node's name"),
])
def test_a_malformed_node_name_is_refused(name: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        node_host(name)


def test_outside_an_unattended_run_a_node_needs_an_allow_host_that_names_its_address() -> None:
    with pytest.raises(ValueError, match="outside --unattended, a capture node is a bench node"):
        node_source("pewpew-line-1", fps=FPS, unattended=False)
    with pytest.raises(ValueError, match=r"pewpew-line-1.local is at 10.0.0.9, which --allow-host does not name"):
        node_source("pewpew-line-1", fps=FPS, unattended=False, allow_hosts=["10.0.0.8"], resolve=lambda h: "10.0.0.9")
    with pytest.raises(ValueError, match="cannot find pewpew-line-1.local"):
        node_source("pewpew-line-1", fps=FPS, unattended=False, allow_hosts=["10.0.0.8"])  # conftest: no resolver
    source = node_source("pewpew-line-1", fps=FPS, unattended=False, allow_hosts=["10.0.0.8"],
                         resolve=lambda h: "10.0.0.8")
    assert source.address == "10.0.0.8" and source.allowed == {"10.0.0.8"}
    unattended = node_source("pewpew-line-1", fps=FPS, unattended=True)
    assert unattended.allowed is None and unattended.address is None  # resolved on the supervisor, never at launch


@pytest.mark.parametrize("argv, problem", [
    (["--audio", "net:n", "--allow-host", "pewpew-line-1.local"], "expected an IP address"),
    (["--allow-host", "10.0.0.8"], "--allow-host only applies with --audio net:NODE"),
    (["--audio", "net:n", "--allow-host", "10.0.0.8", "--unattended"],
     "an unattended run (--unattended) subscribes to its node"),
    (["--audio", "net:n", "--audio-channel", "0", "--allow-host", "10.0.0.8"], "does not apply to a capture node"),
])
def test_node_options_that_rule_each_other_out_are_usage_errors(capsys, argv: list[str], problem: str) -> None:
    with pytest.raises(SystemExit) as exit_:
        parse(["run", "pulse", *argv])
    assert exit_.value.code == 2 and problem in capsys.readouterr().err


def test_a_dry_run_names_the_node_and_subscribes_to_nothing(capsys, audit_log: Path) -> None:
    assert main(["run", "pulse", "--audio", "net:10.0.0.42", "--allow-host", "10.0.0.42", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "dry run: nothing sent" in out and "capture node 10.0.0.42 at 10.0.0.42 (--allow-host names it)" in out
    assert not audit_log.exists()


# ---- a live node, on loopback -------------------------------------------------------


@pytest.fixture
def node():
    key = keys.ensure("aabbccddeeff")
    fake = FakeNode(key)
    yield fake
    fake.close()


@pytest.fixture
def opened():
    """`opened(source)` gives the source back, and stops it after the test."""
    sources: list[NetSource] = []

    def keep(source: NetSource) -> NetSource:
        sources.append(source)
        return source

    yield keep
    for source in sources:
        source.stop()


def stream(source: NetSource, node: FakeNode, t: float, count: int = 2, **kw) -> list:
    """The node sends `count` packets; the source takes them at tick `t`,
    once every one has landed in its socket."""
    want = source.receiver.counts.packets + count - len(kw.get("drop", ()))
    node.send(count, **kw)
    return taken(source, t, lambda: source.receiver.counts.packets >= want)


def taken(source: NetSource, t: float, done) -> list:
    """Take at tick `t` until `done()`, as datagrams land: loopback may
    deliver a burst over a few milliseconds."""
    blocks: list = []
    deadline = time.monotonic() + 2.0
    while True:
        ready(source._sock, 0.05)
        blocks += source.take(t)
        if done() or time.monotonic() > deadline:
            return blocks


def test_a_node_streams_to_the_host_that_signed_its_sub(node: FakeNode, opened) -> None:
    source = opened(source_for(node))
    source.step()
    assert node.serve() == [None] and node.holder is not None
    blocks = stream(source, node, SLOT)
    assert len(blocks) == 2 and np.allclose(np.concatenate([b.samples for b in blocks]),
                                            node.signal[:960], atol=1 / 32768)
    state = source.state()
    assert state["status"] == "listening" and state["kind"] == "node" and state["node"]["packets"] == 2
    assert state["node"]["address"] == "127.0.0.1" and state["node"]["mac"] == "aabbccddeeff"


def test_the_sub_is_renewed_every_pass_while_packets_come(node: FakeNode, opened) -> None:
    source = opened(source_for(node))
    source.step()
    node.serve()
    for k in range(3):
        stream(source, node, (k + 1) * SLOT)
        source.step()
        assert node.serve() == [None]
    assert node.fetches == 1  # the node never went quiet, so it was found once


@pytest.mark.parametrize("node_key, denial", [(bytes(32), Denial.KEY), (None, Denial.NO_KEY)])
def test_a_refused_sub_is_the_reason_the_input_is_lost(node_key, denial, opened) -> None:
    keys.ensure("aabbccddeeff")
    fake = FakeNode(node_key)
    try:
        source = opened(source_for(fake))
        source.step()
        assert fake.serve() == [denial]
        ready(source._sock)
        source.take(SLOT)
        source.step()
        state = source.state()
        assert state["status"] == "lost" and state["reason"] == wire.DENIALS[denial]
    finally:
        fake.close()


def test_a_node_held_by_another_host_reads_busy_until_it_frees(node: FakeNode, opened) -> None:
    node.holder, node.renewed = ("127.0.0.2", 9), 0.0
    source = opened(source_for(node))
    source.step()
    assert node.serve() == [Denial.HELD]
    ready(source._sock)
    source.take(SLOT)
    source.step()
    state = source.state()
    assert state["busy"] and state["status"] == "lost" and "another host holds" in state["reason"]
    node.now = wire.HOLD_S  # the other host stopped renewing
    assert node.serve() == [None]
    stream(source, node, 2 * SLOT)
    assert source.state()["status"] == "listening" and not source.state()["busy"]


def test_pewpew_without_a_key_for_the_node_does_not_subscribe(opened) -> None:
    fake = FakeNode(b"\1" * 32, mac="001122334455")
    try:
        source = opened(source_for(fake))
        source.step()
        assert fake.serve(wait=False) == []
        assert "pewpew has no key for node 00:11:22:33:44:55" in source.state()["reason"]
    finally:
        fake.close()


def test_a_rebooted_node_is_found_again_and_streams_a_new_epoch(node: FakeNode, audit_log: Path, opened) -> None:
    ft = FakeTime()
    source = opened(source_for(node, now=ft.now))
    source.audit(["run"])
    source.step()
    node.serve()
    stream(source, node, SLOT)
    ft.sleep(wire.RENEW_S)
    source.step()  # packets came: renew only
    assert node.fetches == 1 and node.serve() == [None]
    node.reboot(0xBEEF)
    ft.sleep(wire.RENEW_S)
    source.step()  # no packet since the last pass: find the node again
    assert node.fetches == 2 and node.serve() == [None]  # signed with the new nonce
    blocks = stream(source, node, 2 * SLOT)
    assert blocks and source.state()["node"]["reboots"] == 1
    actions = [json.loads(line)["action"] for line in audit_log.read_text().splitlines()]
    assert actions == ["audio-input"]  # the same address: no new record


def test_a_streaming_nodes_json_info_is_read_again_for_its_signal(node: FakeNode, opened) -> None:
    ft = FakeTime()
    source = opened(source_for(node, now=ft.now))
    source.step()
    node.serve()
    stream(source, node, SLOT)
    assert source.state()["node"]["rssi"] == -52
    node.info = lambda: {**FakeNode.info(node), "wifi": {"rssi": -77, "channel": 6}}
    ft.sleep(net.INFO_S)
    source.step()  # packets came: renew, then read /json/info again
    assert node.serve() == [None] and node.fetches == 2 and source.state()["node"]["rssi"] == -77


def test_a_stale_nonce_refusal_finds_the_node_at_once(node: FakeNode, opened) -> None:
    source = opened(source_for(node))
    source.step()
    node.serve()
    stream(source, node, SLOT)
    node.nonce = 0xBEEF  # rebooted between pewpew's read and its SUB
    source.step()
    assert node.serve() == [Denial.STALE]
    taken(source, 2 * SLOT, lambda: source._denial is Denial.STALE)
    source.step()  # the refusal: read /json/info again, though packets came
    assert node.fetches == 2 and node.serve() == [None]


def test_another_node_at_the_address_is_the_reason_the_input_is_lost_never_a_node_to_stream_from(
        node: FakeNode, opened) -> None:
    ft = FakeTime()
    source = opened(source_for(node, now=ft.now))
    source.step()
    node.serve()
    stream(source, node, SLOT)
    key = node.key
    node.reboot(0xBEEF)
    node.mac, node.key = "112233445566", keys.ensure("112233445566")  # DHCP gave the address to another node
    ft.sleep(wire.RENEW_S)
    source.step()  # packets came: renew, which the other node refuses
    assert node.serve() == [Denial.OTHER_NODE]
    taken(source, 2 * SLOT, lambda: source._denial is Denial.OTHER_NODE)
    source.step()  # the refusal: read /json/info again
    ready(node.sock, 0.1)
    assert node.fetches == 2 and node.serve(wait=False) == []  # no SUB to the other node
    source.take(2 * SLOT + LOST_S)
    state = source.state()
    assert state["status"] == "lost"
    assert "another node (11:22:33:44:55:66) answers at 127.0.0.1 now, not aa:bb:cc:dd:ee:ff" in state["reason"]
    assert state["node"]["mac"] == MAC and not state["busy"]
    source._poll(ft.now())  # a poll the other node answers keeps this node's numbers
    assert source.state()["node"]["mac"] == MAC
    node.mac, node.key = MAC, key  # the node is back at its address
    ft.sleep(2 * wire.RENEW_S)
    source.step()
    assert node.serve() == [None] and stream(source, node, 3 * SLOT + LOST_S)
    assert source.state()["status"] == "listening"


def test_a_refusal_that_persists_stays_the_reason_through_each_find(node: FakeNode, opened) -> None:
    node.holder, node.renewed = ("127.0.0.2", 9), 0.0  # the other host holds it all through the test
    ft = FakeTime()
    source = opened(source_for(node, now=ft.now))
    reasons = []
    for k in range(8):
        source.step()
        if k:
            reasons.append(source.state()["reason"])  # before the node answers this pass's SUB
        assert node.serve() == [Denial.HELD]
        taken(source, 1.0 + k * wire.RENEW_S, lambda: source._denial is Denial.HELD)
        reasons.append(source.state()["reason"])
        ft.sleep(wire.RENEW_S)
    assert node.fetches == 4  # found again every other pass, past the opening wait
    assert set(reasons) == {wire.DENIALS[Denial.HELD]}


def test_a_packet_of_a_nonce_this_host_did_not_sign_for_is_stale_never_a_reboot(node: FakeNode, opened) -> None:
    source = opened(source_for(node))
    source.step()
    node.serve()
    stream(source, node, SLOT)
    assert node.holder is not None
    node.sock.sendto(wire.encode(made(node.index, nonce=0xDEAD)[0]), node.holder)  # a spoofed one, say
    taken(source, 2 * SLOT, lambda: source.receiver.counts.stale == 1)
    blocks = stream(source, node, 3 * SLOT)
    numbers = source.state()["node"]
    assert len(blocks) == 2 and numbers["reboots"] == 0 and numbers["stale"] == 1


def test_a_quiet_node_is_lost_after_half_a_second_and_the_levels_go_silent(node: FakeNode, opened) -> None:
    source = opened(source_for(node))
    features = AudioFeatures(source, fps=FPS)
    source.step()
    node.serve()
    node.send(2)
    ready(source._sock)
    features.before_frame(SLOT)
    assert source.state()["status"] == "listening"
    t = SLOT
    while t < SLOT + LOST_S + SLOT:
        t += SLOT
        features.before_frame(t)
    assert source.state()["status"] == "lost" and source.state()["reason"] == f"no packets for {LOST_S:g} s"
    assert features.mode == "lost" and features.at(t).volume == 0.0


def test_a_node_that_never_sends_is_lost_after_the_opening_wait(opened) -> None:
    source = opened(source_for(None, port=9, fetch=failing(TimeoutError())))
    source.take(SLOT)
    assert source.state()["status"] == "opening"
    source.take(SLOT + OPENING_S)
    assert source.state()["status"] == "lost" and "no packets in" in source.state()["reason"]
    source.step()
    assert "does not answer /json/info: timed out" in source.state()["reason"]
    unroutable = OSError(errno.EHOSTUNREACH, "No route to host")
    blocked = opened(source_for(None, port=9, fetch=failing(unroutable)))
    blocked.step()
    assert "No route to host; on a Mac, allow this app in System Settings" in blocked.state()["reason"]


def test_a_node_that_moves_is_audited_before_its_new_address_and_refused_past_the_allow_list(
        node: FakeNode, audit_log: Path, opened) -> None:
    where = {"at": "127.0.0.1"}
    source = opened(NetSource("pewpew-line-1.local", fps=FPS, allowed=None, port=node.port, fetch=node.fetch,
                              resolve=lambda host: where["at"]))
    source.audit(["run", "--unattended"])
    source.step()
    assert node.serve() == [None]
    records = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert [r["action"] for r in records] == ["audio-input", "audio-readdress"]
    assert records[1]["address"] == "127.0.0.1" and records[1]["previous"] is None
    bench = opened(NetSource("pewpew-line-1.local", fps=FPS, allowed=frozenset({"127.0.0.2"}), address="127.0.0.2",
                             port=node.port, fetch=node.fetch, resolve=lambda host: where["at"]))
    bench.step()
    assert "is at 127.0.0.1 now, which --allow-host does not name" in bench.state()["reason"]
    assert node.serve(wait=False) == []


def test_the_loop_never_waits_on_a_supervisor_stuck_in_a_request(node: FakeNode) -> None:
    entered, release = threading.Event(), threading.Event()

    def slow(address: str, timeout: float) -> dict:
        entered.set()
        release.wait(5.0)
        return node.info()

    source = source_for(node, fetch=slow)
    source.start()
    try:
        assert entered.wait(5.0)
        done = threading.Event()

        def loop() -> None:
            for k in range(60):
                source.take((k + 1) * SLOT)
                source.state()
            done.set()

        worker = threading.Thread(target=loop)
        worker.start()
        assert done.wait(2.0), "take or state waited on the supervisor"
        worker.join()
    finally:
        release.set()
        source.stop()


def test_a_tick_drains_a_bounded_number_of_datagrams(node: FakeNode, monkeypatch: pytest.MonkeyPatch, opened) -> None:
    monkeypatch.setattr(net, "MAX_DATAGRAMS", 3)
    source = opened(source_for(node))
    source.step()
    node.serve()
    node.send(7)
    sizes: list[int] = []
    taken(source, SLOT, lambda: sizes.append(source.receiver.counts.packets) or sizes[-1] >= 7)
    assert sizes[-1] == 7 and max(b - a for a, b in zip([0, *sizes], sizes)) <= 3  # each take drains at most 3


def node_run(node: FakeNode) -> Run:
    """A built bench run of `net:127.0.0.1`, its source pointed at `node`."""
    run = build(["run", "pulse", "--audio", "net:127.0.0.1", "--allow-host", "127.0.0.1", "--ansi"])
    assert isinstance(run.capture, NetSource) and run.audio is not None and run.audio.source is run.capture
    run.capture._port, run.capture._fetch = node.port, node.fetch
    return run


def test_a_run_audits_before_its_first_sub_and_stops_its_supervisor(node: FakeNode, audit_log: Path) -> None:
    run = node_run(node)
    seen: list[bool] = []
    real = node.serve
    node.serve = lambda wait=True: seen.append(audit_log.exists()) or real(wait)
    run._start_capture()
    try:
        assert node.serve() == [None] and seen == [True]
    finally:
        assert run.capture is not None
        run.capture.stop()
    (entry,) = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert {k: entry[k] for k in ("action", "input", "kind", "address", "allow_hosts")} == {
        "action": "audio-input", "input": "127.0.0.1", "kind": "node", "address": "127.0.0.1",
        "allow_hosts": ["127.0.0.1"]}
    assert entry["privacy"] == net.PRIVACY


def test_no_sub_goes_out_when_its_audit_record_cannot_be_written(
        node: FakeNode, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PEWPEW_AUDIT_LOG", str(tmp_path))  # a directory: the append fails
    run = node_run(node)
    with pytest.raises(SystemExit, match="audio: "):
        run._start_capture()
    assert node.serve(wait=False) == [] and node.fetches == 0


# ---- what a node says of itself ---------------------------------------------------------


def test_node_info_reads_a_node_and_refuses_a_board(node: FakeNode) -> None:
    info = NodeInfo.of("10.0.0.42", node.info())
    assert info is not None and info.nonce == node.nonce and info.rssi == -52 and info.key
    assert info.row() == {"name": "pewpew-line-1", "address": "10.0.0.42", "mac": "aabbccddeeff", "input": "line",
                          "peak_db": -12.5, "ver": "0.1.0", "key": True, "holder": None}
    assert NodeInfo.of("10.0.0.11", {"ver": "16.0.1", "mac": "aabbccddeeff", "brand": "WLED"}) is None
    assert NodeInfo.of("10.0.0.42", {**node.info(), "nonce": "zz"}) is None


def test_hop_and_packet_are_one_10_ms(node: FakeNode) -> None:
    assert wire.SAMPLES == round(HOP_S * RATE)
