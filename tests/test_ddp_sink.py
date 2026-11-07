"""DDP sink: packet bytes, per-board split, sequence, quantization."""

from __future__ import annotations

import struct

import numpy as np
import pytest

from fakes import ddp_sink
from pewpew.sinks import ddp
from pewpew.sinks.base import to_linear_u8
from pewpew.sinks.ddp import Board, check_boards, parse_board


def header(packet: bytes) -> tuple[int, int, int, int, int, int]:
    return struct.unpack(">BBBBIH", packet[:10])


THREE = [Board("10.0.0.11", 0, 1280), Board("10.0.0.12", 1280, 1280), Board("10.0.0.13", 2560, 1280)]


def frame(n: int, t: float = 0.0) -> np.ndarray:
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    f = np.stack([ramp, (ramp + t) % 1.0, 1.0 - ramp], axis=1).astype(np.float32)
    f.setflags(write=False)
    return f


def test_header_and_payload_golden():
    sink, rec, _ = ddp_sink([Board("10.0.0.11", 0, 2)], 2)
    sink.send(0.0, np.array([[1.0, 0.0, 0.5], [0.0, 1.0, 0.0]], dtype=np.float32))
    [(packet, addr)] = rec.sent
    assert addr == ("10.0.0.11", 4048)
    # flags V=01 + PUSH, seq 1, type RGB 8-bit, dest 1, offset 0, length 6.
    assert packet == bytes.fromhex("41 01 0b 01 00000000 0006") + bytes([255, 0, 128, 0, 255, 0])


def test_three_boards_split_into_offset_packets_with_push_last():
    sink, rec, _ = ddp_sink(THREE, 3840)
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
    sink, rec, _ = ddp_sink(THREE, 3840)
    for k in range(6):
        sink.send(k / 40, frame(3840, k / 10))
    for board in THREE:
        seqs = [header(p)[1] for p, addr in rec.sent if addr[0] == board.host]
        assert seqs == list(range(1, 16)) + [1, 2, 3]  # never 0, which means "unused"
    assert sink.frames_sent == 6


def test_packet_bytes_are_identical_run_to_run():
    runs = []
    for _ in range(2):
        sink, rec, _ = ddp_sink(THREE, 3840)
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


def test_one_failing_board_does_not_starve_the_others_and_is_counted_with_its_text(caplog):
    sink, rec, _ = ddp_sink(THREE, 3840, fail_for="10.0.0.12")
    sink.send(0.0, frame(3840))
    assert {addr[0] for _, addr in rec.sent} == {"10.0.0.11", "10.0.0.13"}
    assert sink.errors == [0, 1, 0]
    assert "10.0.0.12 failed: [Errno 65] No route to host" in caplog.text


def test_frame_size_mismatch_and_lifecycle():
    sink, rec, _ = ddp_sink(THREE, 3840, start=False)
    with pytest.raises(RuntimeError, match="before start"):
        sink.send(0.0, frame(3840))
    sink.start()
    with pytest.raises(ValueError, match="laid out for 3840"):
        sink.send(0.0, frame(300))
    sink.stop()
    sink.stop()  # idempotent
    assert rec.closed == 1


def test_rate_gate_paces_sends():
    sink, _, ft = ddp_sink([Board("10.0.0.11", 0, 8)], 8)
    for _ in range(3):
        sink.send(0.0, frame(8))
    assert ft.sleeps == pytest.approx([0.025, 0.025])


@pytest.mark.parametrize(
    "spec, board",
    [
        ("10.0.0.11=0+1280", Board("10.0.0.11", 0, 1280)),
        ("10.0.0.12:4049=1280+64", Board("10.0.0.12", 1280, 64, 4049)),
        ("pewpew-1.local=0+64", Board("pewpew-1.local", 0, 64)),
        ("WLED-353a18.local:4049=0+8", Board("WLED-353a18.local", 0, 8, 4049)),
    ],
)
def test_parse_board(spec, board):
    assert parse_board(spec) == board


@pytest.mark.parametrize(
    "spec", [
        "10.0.0.11", "10.0.0.11=0", "=0+5", "h=a+5", "h:x=0+5", "h=0+0", "h=-1+5", "h:70000=0+5",
        "lights.example.com=0+5", "a.b.local=0+5", "-x.local=0+5", "10.0.0=0+5", "10.0.0.256:4048=0+5",
    ]
)
def test_parse_board_rejects_with_one_line(spec):
    with pytest.raises(ValueError) as exc:
        parse_board(spec)
    assert "\n" not in str(exc.value)
    assert spec in str(exc.value)


@pytest.mark.parametrize("spec", ["::1=0+8", "[::1]:4048=0+8", "fe80::2=0+8"])
def test_parse_board_rejects_ipv6(spec):
    with pytest.raises(ValueError, match="HOST is an IPv4 address or an mDNS name"):
        parse_board(spec)


def test_check_boards_rejects_overflow_and_overlap():
    with pytest.raises(ValueError, match="do not fit the 3000-pixel map"):
        check_boards(THREE, 3000)
    with pytest.raises(ValueError, match="overlap"):
        check_boards([Board("a", 0, 100), Board("b", 99, 10)], 200)
    check_boards([Board("b", 100, 100), Board("a", 0, 100)], 200)  # touching, any order


def test_relayout_swaps_board_ranges_and_drops_a_stale_frame():
    sink, rec, _ = ddp_sink(THREE, 3840)
    layout = sink.prepare([Board("10.0.0.21", 0, 64), Board("10.0.0.22", 64, 64)], 128)
    assert sink.n_pixels == 3840  # prepare changes nothing
    sink.commit(layout)
    sink.send(0.0, frame(3840))  # rendered before the reload: dropped, not an error
    assert rec.sent == []
    sink.send(0.0, frame(128))
    assert [addr[0] for _, addr in rec.sent] == ["10.0.0.21", "10.0.0.22"]
    assert [header(p)[1] for p, _ in rec.sent] == [1, 1]  # each new board starts its sequence
    with pytest.raises(ValueError, match="laid out for 128"):
        sink.send(0.0, frame(300))  # neither the old size nor the new: a real bug


def test_prepare_looks_up_no_name_and_a_named_board_waits_for_its_address(monkeypatch):
    """The sink never asks a resolver: a room reload must not wait on one.
    A named board is skipped until `set_address` gives it an address."""
    monkeypatch.setattr(ddp.socket, "gethostbyname", lambda host: pytest.fail(f"looked up {host}"))
    boards = [Board("10.0.0.11", 0, 4), Board("pewpew-2.local", 4, 4)]
    sink, rec, _ = ddp_sink(boards, 8)
    assert sink.address("10.0.0.11") == ("10.0.0.11", 4048)
    assert sink.address("pewpew-2.local") is None
    sink.send(0.0, frame(8))
    assert [addr for _, addr in rec.sent] == [("10.0.0.11", 4048)]
    sink.set_address("pewpew-2.local", 4048, ("192.0.2.20", 4048))
    sink.send(0.0, frame(8))
    assert [addr for _, addr in rec.sent][1:] == [("10.0.0.11", 4048), ("192.0.2.20", 4048)]


def test_an_address_outlives_a_relayout_that_keeps_the_board():
    sink, rec, _ = ddp_sink([Board("pewpew-1.local", 0, 4)], 4)
    sink.set_address("pewpew-1.local", 4048, ("192.0.2.20", 4048))
    sink.commit(sink.prepare([Board("pewpew-1.local", 0, 8), Board("10.0.0.12", 8, 4)], 12))
    sink.send(0.0, frame(12))
    assert [addr for _, addr in rec.sent] == [("192.0.2.20", 4048), ("10.0.0.12", 4048)]


def test_prepare_refuses_boards_that_do_not_fit():
    sink, _, _ = ddp_sink(THREE, 3840)
    with pytest.raises(ValueError, match="do not fit"):
        sink.prepare([Board("10.0.0.21", 0, 200)], 128)
    assert sink.n_pixels == 3840
