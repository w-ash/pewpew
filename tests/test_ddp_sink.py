"""DDP sink: packet bytes, per-board split, sequence, quantization."""

from __future__ import annotations

import struct

import numpy as np
import pytest
from conftest import FakeTime, UdpRecorder

from pewpew.sinks.base import to_linear_u8
from pewpew.sinks.ddp import Board, DdpSink, check_boards, parse_board


def header(packet: bytes) -> tuple[int, int, int, int, int, int]:
    return struct.unpack(">BBBBIH", packet[:10])


def make_sink(boards, n, fail_for=None, start=True):
    """A 40 fps sink on a fake clock and a recording socket."""
    rec = UdpRecorder(fail_for)
    ft = FakeTime()
    sink = DdpSink(boards, n, open_socket=lambda: rec, now=ft.now, sleep=ft.sleep)
    if start:
        sink.start()
    return sink, rec, ft


THREE = [Board("10.0.0.11", 0, 1280), Board("10.0.0.12", 1280, 1280), Board("10.0.0.13", 2560, 1280)]


def frame(n: int, t: float = 0.0) -> np.ndarray:
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    f = np.stack([ramp, (ramp + t) % 1.0, 1.0 - ramp], axis=1).astype(np.float32)
    f.setflags(write=False)
    return f


def test_header_and_payload_golden():
    sink, rec, _ = make_sink([Board("10.0.0.11", 0, 2)], 2)
    sink.send(0.0, np.array([[1.0, 0.0, 0.5], [0.0, 1.0, 0.0]], dtype=np.float32))
    [(packet, addr)] = rec.sent
    assert addr == ("10.0.0.11", 4048)
    # flags V=01 + PUSH, seq 1, type RGB 8-bit, dest 1, offset 0, length 6.
    assert packet == bytes.fromhex("41 01 0b 01 00000000 0006") + bytes([255, 0, 128, 0, 255, 0])


def test_three_boards_split_into_offset_packets_with_push_last():
    sink, rec, _ = make_sink(THREE, 3840)
    f = frame(3840)
    sink.send(0.0, f)
    assert len(rec.sent) == 9
    expected = to_linear_u8(f)
    for b_i, board in enumerate(THREE):
        packets = rec.sent[3 * b_i : 3 * b_i + 3]
        assert {addr for _, addr in packets} == {(board.host, 4048)}
        heads = [header(p) for p, _ in packets]
        assert [h[4] for h in heads] == [0, 1440, 2880]  # byte offsets within the board
        assert [h[5] for h in heads] == [1440, 1440, 960]
        assert [h[0] for h in heads] == [0x40, 0x40, 0x41]  # PUSH only on the last
        assert all(h[2] == 0x0B and h[3] == 1 for h in heads)
        data = b"".join(p[10:] for p, _ in packets)
        assert data == expected[board.start : board.stop].tobytes()
    assert board.packets_per_frame == 3
    assert board.bytes_per_frame == 3840 + 30


def test_sequence_is_continuous_across_frames_and_wraps_past_15():
    sink, rec, _ = make_sink(THREE, 3840)
    for k in range(6):
        sink.send(k / 40, frame(3840, k / 10))
    for board in THREE:
        seqs = [header(p)[1] for p, addr in rec.sent if addr[0] == board.host]
        assert seqs == list(range(1, 16)) + [1, 2, 3]  # never 0, which means "unused"
    assert sink.frames_sent == 6


def test_packet_bytes_are_identical_run_to_run():
    runs = []
    for _ in range(2):
        sink, rec, _ = make_sink(THREE, 3840)
        for k in range(4):
            sink.send(k / 40, frame(3840, k / 10))
        runs.append(rec.sent)
    assert runs[0] == runs[1]


def test_quantization_is_linear_and_rounds_once():
    v = np.array(
        [0.0, 1.0, np.nextafter(np.float32(1.0), np.float32(0.0)), 0.998, 1 / 255, np.nan, np.inf, -1.0, 2.0],
        dtype=np.float32,
    )
    out = to_linear_u8(np.stack([v, v, v], axis=1))[:, 0]
    assert out.tolist() == [0, 255, 255, 254, 1, 0, 255, 0, 255]
    # No display gamma: mid-grey stays mid code, unlike to_display_u8's 186.
    assert to_linear_u8(np.full((1, 3), 0.5, np.float32))[0, 0] == 128


def test_one_failing_board_does_not_starve_the_others():
    sink, rec, _ = make_sink(THREE, 3840, fail_for="10.0.0.12")
    sink.send(0.0, frame(3840))
    assert {addr[0] for _, addr in rec.sent} == {"10.0.0.11", "10.0.0.13"}
    assert sink.errors == [0, 1, 0]


def test_frame_size_mismatch_and_lifecycle():
    sink, rec, _ = make_sink(THREE, 3840, start=False)
    with pytest.raises(RuntimeError, match="before start"):
        sink.send(0.0, frame(3840))
    sink.start()
    with pytest.raises(ValueError, match="laid out for 3840"):
        sink.send(0.0, frame(300))
    sink.stop()
    sink.stop()  # idempotent
    assert rec.closed == 1


def test_rate_gate_paces_sends():
    sink, _, ft = make_sink([Board("10.0.0.11", 0, 8)], 8)
    for _ in range(3):
        sink.send(0.0, frame(8))
    assert ft.sleeps == pytest.approx([0.025, 0.025])


@pytest.mark.parametrize(
    "spec, board",
    [
        ("10.0.0.11=0+1280", Board("10.0.0.11", 0, 1280)),
        ("wled-a.local:4049=1280+64", Board("wled-a.local", 1280, 64, 4049)),
    ],
)
def test_parse_board(spec, board):
    assert parse_board(spec) == board


@pytest.mark.parametrize(
    "spec", ["10.0.0.11", "10.0.0.11=0", "=0+5", "h=a+5", "h:x=0+5", "h=0+0", "h=-1+5", "h:70000=0+5"]
)
def test_parse_board_rejects_with_one_line(spec):
    with pytest.raises(ValueError) as exc:
        parse_board(spec)
    assert "\n" not in str(exc.value)
    assert spec in str(exc.value)


@pytest.mark.parametrize("spec", ["::1=0+8", "[::1]:4048=0+8", "fe80::2=0+8"])
def test_parse_board_rejects_ipv6(spec):
    with pytest.raises(ValueError, match="IPv4-only"):
        parse_board(spec)


def test_check_boards_rejects_overflow_and_overlap():
    with pytest.raises(ValueError, match="do not fit the 3000-pixel map"):
        check_boards(THREE, 3000)
    with pytest.raises(ValueError, match="overlap"):
        check_boards([Board("a", 0, 100), Board("b", 99, 10)], 200)
    check_boards([Board("b", 100, 100), Board("a", 0, 100)], 200)  # touching, any order
