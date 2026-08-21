"""Shared sink helpers: the display gamma/quantize step and the RateGate."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import FakeTime

from pewpew.sinks import RateGate, to_display_u8


def test_display_u8_matches_preview_fix_curve():
    # The b68b96a curve: v ** (1/2.2), then 8-bit. 0.5 -> 186, not 128 —
    # the whole point is that mid-greys stay bright on screen.
    frame = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    out = to_display_u8(frame)
    assert out.dtype == np.uint8
    assert out.tolist() == [[0, 186, 255]]


def test_display_u8_clamps_and_survives_nonfinite():
    frame = np.array([[-0.5, 2.0, np.nan], [np.inf, -np.inf, 0.25]], dtype=np.float32)
    out = to_display_u8(frame)
    expected_q = round((0.25 ** (1 / 2.2)) * 255)
    assert out.tolist() == [[0, 255, 0], [255, 0, expected_q]]


def test_display_u8_leaves_the_input_untouched():
    frame = np.full((4, 3), 0.5, dtype=np.float32)
    frame.setflags(write=False)  # as delivered by PacedLoop
    held = frame.copy()
    to_display_u8(frame)
    assert np.array_equal(frame, held)


def test_rate_gate_paces_with_fake_clock():
    ft = FakeTime()
    gate = RateGate(30.0, now=ft.now, sleep=ft.sleep)
    gate.wait()  # first frame passes immediately
    assert ft.sleeps == []
    for _ in range(3):
        gate.wait()
    # Each subsequent frame waits out the remainder of a 1/30 s slot.
    assert ft.sleeps == pytest.approx([1 / 30.0] * 3)
    assert ft.t == pytest.approx(3 / 30.0)


def test_rate_gate_rebases_when_behind_instead_of_bursting():
    ft = FakeTime()
    gate = RateGate(30.0, now=ft.now, sleep=ft.sleep)
    gate.wait()
    ft.t += 1.0  # a long stall (slow client) blows many slots
    gate.wait()  # no sleep: we are already late
    gate.wait()  # ...but the next frame waits one full period, no burst
    assert ft.sleeps == pytest.approx([1 / 30.0])


def test_rate_gate_rejects_nonpositive_fps():
    with pytest.raises(ValueError, match="max_fps"):
        RateGate(0.0)
