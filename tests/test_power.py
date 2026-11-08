"""Stage 3's power limit (`pewpew.power`): the cap arithmetic, the limiter's
edges, its supply shares, determinism, and the `after` stage."""

from __future__ import annotations

import json

import numpy as np
import pytest

from fakes import FLOW, hosted
from fakes import frames as render_frames
from pewpew.power import POWER_HZ, EffectPower, PowerCap, PowerLimiter, PowerMeter, clean
from pewpew.rig import EXAMPLES, compile_rig, load_arrangement, load_catalog
from pewpew.sinks.sink import to_display_u8


def golden(power: dict | None = None):
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    if power is not None:
        data["power"] = power
    return compile_rig(load_arrangement(data), load_catalog())


def frames(n: int, count: int = 8, seed: int = 0) -> list[np.ndarray]:
    """Seeded frames, some with values out of range and not finite."""
    rng = np.random.default_rng(seed)
    out = [np.zeros((n, 3), np.float32), np.ones((n, 3), np.float32)]
    for _ in range(count):
        f = rng.uniform(-0.2, 1.3, (n, 3)).astype(np.float32)
        f[rng.integers(0, n, 5), rng.integers(0, 3, 5)] = np.nan
        f[rng.integers(0, n, 5), 0] = np.inf
        out.append(f)
    return out


def two_supplies(flat: float = 0.0) -> EffectPower:
    """Four RGB pixels of 1 W a channel: pixels 0-1 on supply 0, 2-3 on supply 1."""
    ro = lambda a: (a.setflags(write=False), a)[1]
    return EffectPower(
        channel_w=ro(np.ones(4)),
        min_term_w=ro(np.zeros(4)),
        max_term_w=ro(np.zeros(4)),
        supply_of=ro(np.array([0, 0, 1, 1], dtype=np.intp)),
        flat_w=ro(np.array([flat, 0.0, 0.0])),
        worst_w=ro(np.array([6.0, 6.0, 0.0])),
    )


# ---- the cap ---------------------------------------------------------------------


def test_cap_scale_takes_the_tighter_of_brightness_and_watts():
    assert PowerCap().scale(1000.0) == 1.0 and not PowerCap().caps
    assert PowerCap(max_brightness=0.25).scale(1000.0) == 0.25
    assert PowerCap(max_watts=500.0).scale(1000.0) == 0.5
    assert PowerCap(max_watts=500.0, max_brightness=0.25).scale(1000.0) == 0.25
    assert PowerCap(max_watts=2000.0).scale(1000.0) == 1.0  # a loose cap never brightens
    assert PowerCap(max_watts=150.0).scale(100.0, flat_w=100.0) == 0.5  # flat draw is not scaled
    assert PowerCap(max_watts=50.0).scale(100.0, flat_w=100.0) == 0.0
    assert PowerCap(max_watts=500.0).watts(1000.0, flat_w=10.0) == pytest.approx(500.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_brightness": 1.01},
        {"max_brightness": -0.1},
        {"max_brightness": float("nan")},
        {"max_watts": 0.0},
        {"max_watts": float("inf")},
        {"max_watts": float("nan")},
        {"max_watts": 5e9},
    ],
)
def test_cap_refuses_values_out_of_range(kwargs):
    with pytest.raises(ValueError):
        PowerCap(**kwargs)


# ---- the limiter's edges ---------------------------------------------------------


def test_no_cap_passes_the_frame_through_unchanged():
    rig = golden()
    limiter = rig.limiter()
    for frame in frames(rig.n, 2):
        out = limiter(frame)
        assert out.frame is frame and out.scale == 1.0
        assert out.watts == out.uncapped_watts == pytest.approx(rig.estimate_effect_power(frame))


def test_brightness_scales_the_clean_frame_linearly():
    rig = golden()
    limiter = rig.limiter(PowerCap(max_brightness=0.184))
    for frame in frames(rig.n, 3):
        out = limiter(frame)
        assert out.scale == 0.184
        np.testing.assert_array_equal(out.frame, clean(frame) * np.float32(0.184))
        assert out.uncapped_watts is not None
        assert out.watts == pytest.approx(0.184 * out.uncapped_watts)


def test_watts_cap_holds_full_white_at_the_cap_and_lets_a_dim_frame_through():
    rig = golden()
    white = np.ones((rig.n, 3), np.float32)
    full = rig.estimate_effect_power(white)
    at_edge = rig.limiter(PowerCap(max_watts=full))(white)
    assert at_edge.scale == pytest.approx(1.0)
    capped = rig.limiter(PowerCap(max_watts=100.0))(white)
    assert capped.watts == pytest.approx(100.0) and capped.uncapped_watts == pytest.approx(full)
    assert rig.estimate_effect_power(capped.frame) == pytest.approx(capped.watts)
    dim = np.full((rig.n, 3), 0.01, np.float32)
    assert rig.limiter(PowerCap(max_watts=100.0))(dim).scale == 1.0


def test_zero_brightness_and_a_cap_under_the_flat_draw_give_black():
    model = two_supplies(flat=5.0)
    frame = np.ones((4, 3), np.float32)
    for cap in (PowerCap(max_brightness=0.0), PowerCap(max_watts=4.0)):
        out = PowerLimiter(cap, model)(frame)
        assert not out.frame.any() and out.watts == pytest.approx(5.0)


def test_the_limiter_never_brightens():
    rig = golden()
    for cap in (
        PowerCap(max_brightness=0.5),
        PowerCap(max_watts=300.0),
        PowerCap(max_watts=1e6),
        PowerCap(max_watts=500.0, max_brightness=0.9),
    ):
        limiter = rig.limiter(cap)
        for frame in frames(rig.n, 4, seed=1):
            out = limiter(frame)
            assert 0.0 <= out.scale <= 1.0
            assert (to_display_u8(out.frame) <= to_display_u8(frame)).all()
            assert out.watts is not None and out.uncapped_watts is not None
            assert out.watts <= out.uncapped_watts + 1e-9


def test_brightness_alone_needs_no_model_and_watts_does():
    frame = np.full((4, 3), 0.5, np.float32)
    out = PowerLimiter(PowerCap(max_brightness=0.5))(frame)
    np.testing.assert_array_equal(out.frame, np.full((4, 3), 0.25, np.float32))
    assert out.watts is None
    assert PowerLimiter(PowerCap())(frame).frame is frame
    with pytest.raises(ValueError, match="power model"):
        PowerLimiter(PowerCap(max_watts=10.0))


# ---- supply shares ---------------------------------------------------------------


def test_each_supply_keeps_within_its_share_of_the_cap():
    # 12 W at full white, capped at 6 W: each supply's share is 3 W.
    limiter = PowerLimiter(PowerCap(max_watts=6.0), two_supplies())
    one_side = np.array([[1, 1, 1], [1, 1, 1], [0, 0, 0], [0, 0, 0]], np.float32)
    out = limiter(one_side)
    assert out.uncapped_watts == 6.0 and out.watts == pytest.approx(3.0)
    assert limiter(np.ones((4, 3), np.float32)).watts == pytest.approx(6.0)


def test_golden_rings_supplies_keep_within_their_capped_report_loads():
    rig = golden({"max_watts": 500})
    psus = {p.id: p.watts for p in rig.report.psus}
    assert len(psus) == 2 and sum(psus.values()) == pytest.approx(500.0)
    fed = {fid: f.psu for f in rig.report.feeds for fid in f.fixtures}
    limiter = rig.limiter()
    for psu, budget in psus.items():
        frame = np.zeros((rig.n, 3), np.float32)
        for fx in rig.fixtures:
            if fed.get(fx.id) == psu:
                # Red and green full: two channels after WLED's Accurate auto-white, the most RGB can draw.
                frame[fx.pixel_start : fx.pixel_start + fx.pixel_count] = (1.0, 1.0, 0.0)
        out = limiter(frame)
        assert out.uncapped_watts > budget and out.watts == pytest.approx(budget)


# ---- determinism and goldens -----------------------------------------------------


def test_the_limiter_is_deterministic():
    rig = golden({"max_watts": 300, "max_brightness": 0.8})
    for frame in frames(rig.n, 3, seed=2):
        a, b = rig.limiter()(frame), golden({"max_watts": 300, "max_brightness": 0.8}).limiter()(frame)
        assert a.frame.tobytes() == b.frame.tobytes() and a.watts == b.watts


def test_an_uncapped_limiter_changes_no_displayed_byte():
    rig = golden()
    sequence = render_frames(hosted(FLOW, rig.mapping, seed=42), 30)
    for cap in (PowerCap(), PowerCap(max_watts=1e6)):
        limiter = rig.limiter(cap)
        limited = np.stack([limiter(f).frame for f in sequence])
        assert to_display_u8(limited).tobytes() == to_display_u8(sequence).tobytes()


def test_the_meter_blacks_out_a_frame_the_limiter_refuses():
    class Refusing(PowerLimiter):
        def __call__(self, frame):
            raise ValueError("frame shape")

    out = PowerMeter(60.0, Refusing(PowerCap(max_brightness=0.5)))(0.0, np.ones((2, 3), np.float32))
    assert out.shape == (2, 3) and not out.any()


def test_the_meter_returns_the_limited_frame_and_leaves_its_input_alone():
    frame = np.ones((2, 3), np.float32)
    out = PowerMeter(60.0, PowerLimiter(PowerCap(max_brightness=0.5)))(1.5, frame)
    assert (out == 0.5).all() and (frame == 1.0).all()


def test_the_meter_reads_an_uncapped_rig_only_when_a_reading_is_due():
    rig = golden()
    limiter = rig.limiter(PowerCap())
    calls = []

    class Counting(PowerLimiter):
        def __call__(self, frame):
            calls.append(frame)
            return limiter(frame)

    meter = PowerMeter(4 * POWER_HZ, Counting(PowerCap(), limiter.model))
    frame = np.full((rig.n, 3), 0.5, np.float32)
    outs = [meter(i / 8, frame) for i in range(8)]
    assert len(calls) == 2 and all(out is frame for out in outs)
    assert meter.reading is not None and meter.reading["watts"] == pytest.approx(rig.estimate_effect_power(frame))
    meter.limiter = None
    assert meter.reading is None and meter(1.0, frame) is frame
