"""The electrical report, its validation tiers, and effect power (docs/studio/domain-model.md:228-243, 302-321)."""

from __future__ import annotations

import json
import math
import shutil

import numpy as np
import pytest

from pewpew.rig import EXAMPLES, RigError, compile_rig, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import DATA_ROOT
from pewpew.rig.electrical import (
    AUTO_WHITE_TERMS,
    BUCK_EFFICIENCY,
    RHO_CU_OHM_M,
    feed_drop_v,
    frame_s,
    fuse_window,
    loop_ohm_per_m,
    pick_fuse,
    rgb_reach,
)
from pewpew.rig.models import MAX_ISSUES, value
from test_rig_compile import RING_AND_TUBE

BAR = "clen-rgbw-bar-1m"
TUBE = "clen-360-tube-1500"
S3 = "esp32s3-devkitc1-ahct125"
PSU = "meanwell-lrs-350-24"
I_BAR = 25.6 / 24  # RES-033, the maintainer's private notes


def compiled(obj, catalog=None):
    return compile_rig(load_arrangement(obj), catalog or load_catalog())


def codes(rig, level=None):
    return [i.code for i in rig.issues if i.code != "rests_on_assumed" and level in (None, i.level)]


@pytest.fixture(scope="module")
def example():
    return compiled(RING_AND_TUBE)


@pytest.fixture(scope="module")
def golden():
    return compiled(EXAMPLES / "golden-rings.json")


def one_chain(n, type_id=BAR, step=(1.0, 0, 0), feeds=(), target_fps=None, controller_at=None, psu_type=PSU):
    fixtures = [
        {"id": f"x{i}", "type": type_id, "pose": {"position_m": [step[0] * i, step[1] * i, step[2] * i]}}
        for i in range(n)
    ]
    wiring = {
        "chains": [{"id": "A", "controller": "c1", "output": "rmt0", "fixtures": [f["id"] for f in fixtures]}],
        "feeds": [{"psu": "p1", "chain": "A", "cable": "wire-16awg-pair", "length_m": 2.0, **f} for f in feeds],
    }
    if target_fps is not None:
        wiring["target_fps"] = target_fps
    return {
        "format": "pewpew.arrangement",
        "version": 1,
        "fixtures": fixtures,
        "controllers": [{"id": "c1", "profile": S3, "position_m": controller_at}],
        "psus": [{"id": "p1", "type": psu_type}],
        "wiring": wiring,
    }


# ---- arithmetic -------------------------------------------------------------------


def test_frame_times():
    # docs/studio/domain-model.md:237-238 and :362.
    assert 1 / frame_s(640, 40e-6, 80e-6) == pytest.approx(38.94, abs=0.005)  # a 10-bar chain
    assert frame_s(216, 30e-6, 24e-6) == pytest.approx(6.504e-3, rel=1e-12)  # a 6-tube chain
    assert frame_s(256, 40e-6, 80e-6) == pytest.approx(10.32e-3, rel=1e-12)
    spec = load_catalog().spec(TUBE)
    assert frame_s(6 * spec.count, spec.t_px_s, spec.reset_s) == pytest.approx(6.504e-3, rel=1e-12)


def test_feed_drop_reproduces_the_design_arithmetic():
    # docs/studio/domain-model.md:241: 0.0527 Ω × 2.133 A + 0.0528 Ω × 1.067 A = 0.169 V (0.70%).
    drop = feed_drop_v([I_BAR, I_BAR], 0.0527, [0.0528])
    assert drop == pytest.approx(0.169, abs=5e-4)
    assert drop / 24 == pytest.approx(0.0070, abs=5e-5)
    # 2 m of a 16 AWG pair, there and back: 0.0527 Ω.
    assert 2.0 * loop_ohm_per_m(1.309, 1.309) == pytest.approx(0.0527, abs=5e-5)
    assert RHO_CU_OHM_M == pytest.approx(1.724e-8, rel=1e-3)


def test_fuse_window_and_choice():
    # docs/studio/domain-model.md:240: 2.133 A gives 2.84-4.0 A, and a 3 A fuse fits.
    lo, hi = fuse_window(2 * I_BAR, 4.0, 0.75)
    assert (round(lo, 2), hi) == (2.84, 4.0)
    assert pick_fuse(2 * I_BAR, 4.0, 0.75) == 3.0
    assert pick_fuse(1.5, 4.0, 0.75) == 2.0
    assert pick_fuse(3 * I_BAR, 4.0, 0.75) is None  # the window is empty
    assert pick_fuse(3 * I_BAR, None, 0.75) == 5.0


def wled_auto_white(rgb, mode):
    """RGBW from RGB with W = 0, as WLED's Bus::autoWhiteCalc gives it
    (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L101-L126)."""
    r, g, b = rgb
    if mode in (None, "manual"):
        return r, g, b, 0.0
    if mode == "max":
        return r, g, b, max(r, g, b)
    w = min(r, g, b)  # brighter, accurate, and dual on a frame with no W
    if mode == "accurate":
        r, g, b = r - w, g - w, b - w
    return r, g, b, w


def test_auto_white_terms_follow_wled_for_every_mode():
    colours = np.random.default_rng(1).random((200, 3))
    for mode, (a, b) in AUTO_WHITE_TERMS.items():
        for c in colours:
            want = sum(wled_auto_white(c, mode))
            assert c.sum() + a * c.min() + b * c.max() == pytest.approx(want, abs=1e-12), mode


# ---- the worked example (docs/studio/domain-model.md:235-243) -------------------------


def test_example_totals_outputs_and_psu(example):
    r = example.report
    assert (r.totals.pixels, r.totals.fixtures, r.totals.controllers, r.totals.feeds) == (548, 9, 1, 5)
    assert r.totals.worst_w == pytest.approx(240.8, abs=1e-9)
    assert r.totals.worst_a == pytest.approx(10.0333, abs=5e-5)
    out = {o.chain: o for o in r.outputs}
    assert out["A"].frame_s == pytest.approx(10.32e-3) and round(out["A"].wire_fps, 1) == 96.9
    assert out["T"].frame_s == pytest.approx(1.104e-3) and out["T"].led_label == "WS281x RGB"
    (p1,) = r.psus
    # 10.03 A with every channel full (docs/studio/domain-model.md:242); the RGB stream draws half of each bar's.
    assert round(p1.worst_a, 2) == 10.03 and round(p1.current_a, 2) == round(8 * I_BAR / 2 + 1.5, 2)
    assert p1.feeds == ["f1", "f2", "f3", "f4", "f5"]
    assert codes(example) == []


def test_example_feed_f1(example):
    f1 = example.report.feeds[0]
    assert f1.fixtures == ["ring/0", "ring/1"]
    assert f1.current_a == pytest.approx(2.1333, abs=5e-5)
    assert f1.fuse_window_a[0] == pytest.approx(2.8444, abs=5e-5) and f1.fuse_window_a[1] == 4.0
    assert f1.connector_a == 4.0 and f1.fuse_a == 3.0
    assert f1.loop_ohm == pytest.approx(0.0527, abs=5e-5)
    assert f1.va == pytest.approx(51.2) and f1.note is None
    # The link into ring/1 follows the data hop and has the feed cable's conductors (an
    # assumption): 0.0527 ohm x 2.133 A + 0.0450 ohm x 1.067 A = 0.160 V.
    hop = next(h for h in example.report.hops if h.kind == "link" and h.target == "ring/1")
    assert hop.path_m == pytest.approx(1.708, abs=5e-4)
    link_ohm = hop.path_m * f1.loop_ohm / f1.length_m
    assert f1.drop_v == pytest.approx(feed_drop_v([I_BAR, I_BAR], f1.loop_ohm, [link_ohm]), rel=1e-12)
    assert f1.drop_v == pytest.approx(0.160, abs=5e-4)


def test_example_hops_and_leads(example):
    hops = example.report.hops
    assert [(h.kind, h.source, h.target) for h in hops[:2]] == [("lead", "c1", "ring/0"), ("link", "ring/0", "ring/1")]
    assert len([h for h in hops if h.kind == "lead"]) == 3
    # |out - in| between neighbours on the ring of 8 is 1.090 m between the pigtail exits,
    # which sit on the underside 0.15 m in from each end.
    link = hops[1]
    assert link.run_m / 1.2 == pytest.approx(1.090, abs=5e-4)
    assert link.path_m == pytest.approx(link.run_m + 0.4, rel=1e-12)


def test_the_basis_lists_unmeasured_values_with_their_sources(example):
    basis = {b.fact: b for b in example.report.basis}
    rated = basis["connector/clen-4pin.rated_a"]
    assert (rated.v, rated.status, rated.used_for) == (4.0, "assumed", ["feed limits", "fuse windows"])
    assert "automationdirect" in rated.src
    assert basis[f"fixture_type/{BAR}.power.max_w"].status == "stated"
    assert f"fixture_type/{BAR}.dims.pigtail" not in basis  # measured
    assert basis["chipset/sk6812.reset_s"].used_for == ["timing"]
    assert basis[f"fixture_type/{BAR}.power.model"].v == "linear"
    assert all(b.status != "measured" for b in basis.values())
    warned = {i.ref for i in example.issues if i.code == "rests_on_assumed"}
    assert warned == {f for f, b in basis.items() if b.status == "assumed"}


def test_golden_bill_of_materials(golden):
    bom = {(b.kind, b.item): b for b in golden.report.bom}
    assert bom[("fixture", BAR)].count == 48
    assert bom[("attachment", "point-v0")].count == 48 and bom[("attachment", "eye-v0")].count == 48
    assert bom[("controller", S3)].count == 2
    assert bom[("component", "74AHCT125 quad level shifter")].count == 2
    assert bom[("psu", PSU)].count == 3  # sized for the 614.4 W the RGB stream draws
    assert bom[("fuse", "3 A")].count == 24
    feed_cable = bom[("cable", "wire-16awg-pair")]
    assert feed_cable.count == 24 and feed_cable.length_m == pytest.approx(sum(f.length_m for f in golden.feeds))
    assert bom[("cable", "lead")].count == 6 and bom[("cable", "link")].count == 42
    assert golden.report.totals.worst_w == pytest.approx(48 * 25.6)
    json.dumps(golden.to_json())


# ---- validation tiers -------------------------------------------------------------


def test_feed_current_and_fuse_window():
    assert codes(compiled(one_chain(2, feeds=[{"id": "f", "first": 0, "count": 2, "fuse_a": 3}]))) == []
    over = compiled(one_chain(3, feeds=[{"id": "f", "first": 0, "count": 3, "fuse_a": 4}]))
    assert codes(over) == ["feed_over_rating", "fuse_outside_window"]  # 3.2 A > 3 A; window [4.27, 4]
    assert codes(compiled(one_chain(2, feeds=[{"id": "f", "first": 0, "count": 2, "fuse_a": 5}]))) == [
        "fuse_outside_window"
    ]
    assert codes(compiled(one_chain(2, feeds=[{"id": "f", "first": 0, "count": 2}]))) == ["feed_unfused"]


def test_drop_hop_lead_and_timing_warnings():
    long_feed = one_chain(2, feeds=[{"id": "f", "first": 0, "count": 2, "fuse_a": 3, "length_m": 50}])
    assert codes(compiled(long_feed)) == ["drop_over_limit"]  # 2.13 A x 1.32 Ω is 12%
    assert codes(compiled(one_chain(2, step=(4.0, 0, 0)))) == ["hop_over_limit", "unfed"]
    assert codes(compiled(one_chain(1, controller_at=[0, 0, 12.0]))) == ["lead_over_limit", "unfed"]
    # Wiring.target_fps drives the timing warning: a 10-bar chain runs at 38.9 fps.
    slow = compiled(one_chain(10, step=(0.5, 0, 0), target_fps=40))
    assert codes(slow) == ["fps_below_target", "unfed"]
    assert round(slow.report.outputs[0].wire_fps, 1) == 38.9
    assert slow.report.target_fps == 40
    assert codes(compiled(one_chain(9, step=(0.5, 0, 0), target_fps=40))) == ["unfed"]


def test_psu_load_overlap_and_voltage(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    wled = root / "firmware" / "wled-16.0.1.json"
    brighter = json.loads(wled.read_text())
    brighter["ingest"]["auto_white"] = (
        "brighter"  # RGB reaches every channel, so a PSU's load is its feeds' full current
    )
    wled.write_text(json.dumps(brighter))
    feeds = [{"id": f"f{k}", "first": k * 2, "count": 2, "fuse_a": 3} for k in range(7)]
    fourteen = lambda n: compiled(
        one_chain(14, step=(0.5, 0, 0), feeds=feeds[:n]), read_catalog(root)
    )  # 896 px: over 800
    assert codes(fourteen(5)) == ["output_over_warn", "unfed"]  # 10.7 A, 73%
    assert codes(fourteen(6)) == ["output_over_warn", "unfed", "psu_over_derating"]  # 12.8 A, 88%
    assert codes(fourteen(7)) == ["output_over_warn", "psu_overload"]  # 14.9 A
    overlap = feeds[:1] + [{"id": "g", "first": 1, "count": 1, "fuse_a": 2}]
    assert codes(compiled(one_chain(2, feeds=overlap))) == ["feed_overlap"]
    wled.write_text(json.dumps({**brighter, "ingest": {**brighter["ingest"], "auto_white": "accurate"}}))
    path = root / "psu" / f"{PSU}.json"
    obj = json.loads(path.read_text())
    obj["v_out"]["v"] = 12
    path.write_text(json.dumps(obj))
    assert codes(compiled(one_chain(2, feeds=feeds[:1]), read_catalog(root))) == ["psu_voltage"]


# ---- effect power -----------------------------------------------------------------


def test_effect_power_off_white_and_every_channel(example):
    n = example.n
    assert example.estimate_effect_power(np.zeros((n, 3), dtype=np.float32)) == 0.0
    white = np.ones((n, 3), dtype=np.float32)
    bars, tube = slice(0, 512), slice(512, 548)
    only_tube = np.zeros((n, 3))
    only_tube[tube] = 1.0
    assert example.estimate_effect_power(only_tube) == pytest.approx(36.0)  # RGB white is every channel
    only_bars = np.zeros((n, 3))
    only_bars[bars] = 1.0
    # Accurate auto-white turns RGB white into W alone: one channel of four.
    assert example.estimate_effect_power(only_bars) == pytest.approx(8 * 25.6 / 4)
    only_bars[bars] = (1.0, 1.0, 0.0)  # yellow keeps R and G and lights no W
    assert example.estimate_effect_power(only_bars) == pytest.approx(8 * 25.6 / 2)
    assert example.estimate_effect_power(white) == pytest.approx(8 * 6.4 + 36.0)
    # With every channel full, each fixture draws max_w.
    power = example.power
    for f in example.fixtures:
        rows = slice(f.pixel_start, f.pixel_start + f.pixel_count)
        spec = load_catalog().spec(f.type_id)
        assert power.channel_w[rows].sum() * len(spec.channels) == pytest.approx(spec.max_w)


def test_effect_power_sanitizes_and_checks_the_frame(example):
    frame = np.full((example.n, 3), np.nan)
    frame[0] = (np.inf, -np.inf, 2.0)
    assert example.estimate_effect_power(frame) == pytest.approx(2 * 25.6 / 256)  # R and B full on one pixel
    with pytest.raises(ValueError, match="frame shape"):
        example.estimate_effect_power(np.zeros((example.n, 4)))


def test_a_flat_fixture_draws_max_w_whatever_it_lights(tmp_path):
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    path = root / "fixture_type" / f"{BAR}.json"
    obj = json.loads(path.read_text())
    obj["power"]["model"] = {
        "v": "flat",
        "status": "inferred",
        "src": "https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png",
    }
    path.write_text(json.dumps(obj))
    cat = read_catalog(root)
    rig = compiled(RING_AND_TUBE, cat)
    off = np.zeros((rig.n, 3))
    assert rig.estimate_effect_power(off) == pytest.approx(8 * 25.6)
    assert rig.estimate_effect_power(np.ones((rig.n, 3))) == pytest.approx(8 * 25.6 + 36.0)
    assert f"fixture_type/{BAR}.power.model" not in {i.ref for i in rig.issues}
    bar = next(f for f in cat.to_json()["fixture_types"] if f["id"] == BAR)
    assert bar["power"]["model"]["v"] == "flat"
    default = next(f for f in load_catalog().to_json()["fixture_types"] if f["id"] == BAR)
    assert (default["power"]["model"]["v"], default["power"]["model"]["status"]) == ("linear", "assumed")


def test_effect_power_is_vectorized(golden):
    # 3072 px; the session calls it about twice a second (docs/studio/contracts.md:110).
    frame = np.random.default_rng(0).random((golden.n, 3), dtype=np.float32)
    w = golden.estimate_effect_power(frame)
    assert 0 < w < golden.report.totals.worst_w
    assert math.isfinite(w)
    assert golden.power.channel_w.shape == (golden.n,) and not golden.power.channel_w.flags.writeable


# ---- the ws2 review (docs/studio/reports/reviews/ws2-code-review.md) ----------------------


def edited_catalog(tmp_path, rel, edit):
    """The bundled catalog with `edit(entity)` applied to the file `rel` under data/."""
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    path = root / rel
    obj = json.loads(path.read_text())
    edit(obj)
    path.write_text(json.dumps(obj))
    return read_catalog(root)


def auto_line(n, step=(1.0, 0, 0), psu_at=None, **options):
    return {
        "format": "pewpew.arrangement",
        "version": 1,
        "fixtures": [{"id": f"x{i}", "type": BAR, "pose": {"position_m": [s * i for s in step]}} for i in range(n)],
        "controllers": [{"id": "c1", "profile": S3}],
        "psus": [{"id": "p1", "type": PSU, "position_m": psu_at}],
        "wiring": {"auto": options},
    }


@pytest.mark.parametrize(
    "option, bad",
    [
        ("target_fps", 5e-324),
        ("hop_slack", 1e308),
        ("connector_load_fraction", 5e-324),
        ("max_drop_fraction", 1e-300),
        ("psu_load_fraction", 1e-300),
    ],
)
def test_options_that_overflow_the_arithmetic_are_refused(option, bad):
    # Finding 2: each of these passed validation, and compile raised OverflowError or ValidationError.
    with pytest.raises(RigError):
        load_arrangement(auto_line(2, **{option: bad}))
    with pytest.raises(RigError):
        load_arrangement(one_chain(2, feeds=[{"id": "f", "first": 0, "count": 2, "length_m": 1e308}]))


def test_the_report_is_finite_at_every_bound():
    far = auto_line(
        3,
        step=(5e3, 0, 0),
        psu_at=[-1e4, -1e4, -1e4],
        target_fps=0.1,
        hop_slack=10,
        max_hop_m=1e300,
        connector_load_fraction=0.01,
        max_drop_fraction=0.01,
        psu_load_fraction=0.01,
    )
    long_feed = one_chain(
        40, step=(0.5, 0, 0), feeds=[{"id": "f", "first": 0, "count": 40, "length_m": 1e6, "fuse_a": 1e308}]
    )
    # The longest auto feed: from the far corner to the end of an array 199 km along each axis.
    widest = {
        **auto_line(0, psu_at=[-1e4, -1e4, -1e4], hop_slack=10),
        "groups": [
            {
                "id": "g",
                "preset": "array",
                "type": BAR,
                "counts": [200],
                "steps_m": [[-1e3, -1e3, -1e3]],
                "pose": {"position_m": [1e4, 1e4, 1e4]},
            }
        ],
    }
    widest["psus"].append({"id": "p2", "type": PSU, "position_m": [1e4, 1e4, 1e4]})
    for obj in (far, long_feed, widest):
        rig = compiled(obj)
        json.dumps(rig.to_json(), allow_nan=False)
    assert max(f.length_m for f in rig.feeds) > 1e6


def test_overlapping_feeds_give_one_issue_a_feed_and_issues_are_capped():
    # Finding 3: 200 feeds over one 200-bar chain gave 40,408 issues.
    overlap = [
        {"id": "f", "first": 0, "count": 3, "fuse_a": 5},
        {"id": "g", "first": 1, "count": 2, "fuse_a": 3},
        {"id": "h", "first": 0, "count": 3, "fuse_a": 5},
    ]
    issues = [(i.ref, i.message) for i in compiled(one_chain(3, feeds=overlap)).issues if i.code == "feed_overlap"]
    assert issues == [
        ("feed g", "x1 and 1 more fixture are also in feed f"),
        ("feed h", "x0 and 2 more fixtures are also in feed f"),
    ]
    every = [{"id": f"f{k}", "first": 0, "count": 200} for k in range(200)]
    rig = compiled(one_chain(200, step=(0.5, 0, 0), feeds=every))
    assert len(rig.issues) == MAX_ISSUES + 1
    assert (rig.issues[-1].code, rig.issues[-1].level) == ("too_many_issues", "violation")
    assert {i.level for i in rig.issues[:-1]} == {"violation"}


def test_a_measured_pass_through_adds_to_the_drop(tmp_path, example):
    # Finding 8: the link into ring/1 carries ring/1's current through ring/0's pass-through.
    def measured(obj):
        obj["power"]["passthrough_ohm"] = {"v": 0.5, "status": "measured", "src": "a bench test"}

    rig = compiled(RING_AND_TUBE, edited_catalog(tmp_path, f"fixture_type/{BAR}.json", measured))
    f1, before = rig.report.feeds[0], example.report.feeds[0]
    assert f1.drop_v == pytest.approx(before.drop_v + 0.5 * I_BAR, rel=1e-12)
    assert f"fixture_type/{BAR}.power.passthrough_ohm" not in {b.fact for b in rig.report.basis}


@pytest.mark.parametrize(
    "mode, bar_w",
    [(None, 19.2), ("manual", 19.2), ("brighter", 25.6), ("accurate", 6.4), ("dual", 25.6), ("max", 25.6)],
)
def test_effect_power_follows_the_firmware_auto_white(tmp_path, mode, bar_w):
    # Finding 9: RGB white is R + G + B, plus W as each of WLED's modes derives it.
    def set_mode(obj):
        obj["ingest"]["auto_white"] = mode

    rig = compiled(RING_AND_TUBE, edited_catalog(tmp_path, "firmware/wled-16.0.1.json", set_mode))
    only_bars = np.zeros((rig.n, 3))
    only_bars[:512] = 1.0
    assert rig.estimate_effect_power(only_bars) == pytest.approx(8 * bar_w)


def test_unwired_rgbw_fixtures_take_accurate_white_as_an_assumption():
    rig = compiled({**auto_line(2), "controllers": []})
    basis = {b.fact: b for b in rig.report.basis}
    assert (basis["wiring.unwired_auto_white"].v, basis["wiring.unwired_auto_white"].status) == ("accurate", "assumed")
    assert rig.estimate_effect_power(np.ones((rig.n, 3))) == pytest.approx(2 * 6.4)
    assert "wiring.unwired_auto_white" not in {b.fact for b in compiled(auto_line(2)).report.basis}


def test_the_link_conductor_basis_names_every_feed_cable():
    # Finding 12: it named only the first feed's cable.
    feeds = [
        {"id": "f", "first": 0, "count": 2, "fuse_a": 3},
        {"id": "g", "first": 2, "count": 2, "fuse_a": 3, "cable": "wire-18awg-pair"},
    ]
    basis = {b.fact: b for b in compiled(one_chain(4, feeds=feeds)).report.basis}
    assert basis["wiring.link_conductors"].v == ["wire-16awg-pair", "wire-18awg-pair"]


def _zero(*keys):
    def edit(obj):
        for key in keys[:-1]:
            obj = obj[key]
        if isinstance(obj[keys[-1]], dict):
            obj[keys[-1]]["v"] = 0
        else:
            obj[keys[-1]] = 0

    return edit


@pytest.mark.parametrize(
    "rel, keys",
    [
        (f"psu/{PSU}.json", ("i_max_a",)),
        (f"psu/{PSU}.json", ("v_out",)),
        ("cable/wire-16awg-pair.json", ("conductors_mm2", "vplus")),
        ("chipset/sk6812.json", ("bit_s",)),
        ("connector/clen-4pin.json", ("rated_a",)),
    ],
)
def test_a_zero_divisor_in_the_catalog_is_refused(tmp_path, rel, keys):
    # Finding 13: these divided by zero in compile_rig.
    with pytest.raises(RigError) as exc:
        edited_catalog(tmp_path, rel, _zero(*keys))
    assert [(i.code, i.ref) for i in exc.value.issues] == [
        ("bad_value", f"{rel.split('/')[0]}/{json.loads((DATA_ROOT / rel).read_text())['id']}.{'.'.join(keys)}")
    ]


# ---- the power cap (pewpew.power, ADR-001 amendment 2026-10-23) ---------------------


def golden_capped(**power):
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    return compiled({**data, "power": power})


def test_rgb_reach_follows_each_auto_white_mode():
    # The largest channel sum of an RGB frame, in full channels (WLED's autoWhiteCalc,
    # https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125).
    assert {mode: rgb_reach("RGBW", mode) for mode in AUTO_WHITE_TERMS} == {
        None: 3,
        "manual": 3,
        "brighter": 4,
        "accurate": 2,
        "dual": 4,
        "max": 4,
    }
    assert rgb_reach("RGB", "accurate") == 3


def test_effect_power_reaches_its_worst_case(golden):
    # Yellow is the most an RGB frame draws from an Accurate RGBW bar: W = 0, two channels full.
    yellow = np.zeros((golden.n, 3), np.float32)
    yellow[:, :2] = 1.0
    assert golden.estimate_effect_power(yellow) == pytest.approx(golden.power.worst_w.sum())
    assert golden.power.worst_w.sum() == pytest.approx(golden.report.totals.rgb_worst_w)


def test_psus_are_sized_for_the_rgb_worst_case_without_a_cap(golden):
    totals = golden.report.totals
    assert golden.power_cap.caps is False
    assert (totals.worst_w, totals.worst_a) == (pytest.approx(1228.8), pytest.approx(51.2))
    assert (totals.rgb_worst_w, totals.capped_w) == (pytest.approx(614.4), pytest.approx(614.4))
    assert len(golden.report.psus) == 3
    note = next(n for n in golden.report.notes if n.startswith("PSUs are sized"))
    assert "614.4 W, not the 1228.8 W" in note and "Accurate" in note and "power cap" not in note
    assert not any(n.startswith("Under the power cap") for n in golden.report.notes)
    for f in golden.report.feeds:  # without a cap the feeds are checked with every channel full
        assert f.fuse_window_a[0] == pytest.approx(f.current_a / 0.75)
    assumed = {i.ref: i.message for i in golden.issues if i.code == "rests_on_assumed"}
    assert "PSU sizing" in assumed["firmware/wled-16.0.1.ingest.auto_white"]
    assert "PSU sizing" in assumed[f"fixture_type/{BAR}.power.channel_split"]


@pytest.mark.parametrize(
    "power, capped_w, psus",
    [
        # 48 bars x 25.6 W x 2/4 channels = 614.4 W; x 0.184 = 113.0 W.
        # An LRS-350-24 carries 0.8 x 14.6 A x 24 V = 280.3 W.
        ({"max_brightness": 0.184}, 614.4 * 0.184, 1),
        ({"max_watts": 500}, 500.0, 2),  # ceil(500 / 280.3) = 2
        ({"max_watts": 280}, 280.0, 1),
        ({"max_watts": 500, "max_brightness": 0.184}, 614.4 * 0.184, 1),
        ({"max_watts": 2000}, 614.4, 3),  # a cap over the RGB worst case scales nothing
    ],
)
def test_psus_are_sized_for_the_capped_worst_case(power, capped_w, psus):
    rig = golden_capped(**power)
    totals = rig.report.totals
    assert (totals.worst_w, totals.rgb_worst_w) == (pytest.approx(1228.8), pytest.approx(614.4))
    assert totals.capped_w == pytest.approx(capped_w) and totals.capped_a == pytest.approx(capped_w / 24)
    assert totals.psus == psus == len(rig.report.psus)
    assert sum(p.watts for p in rig.report.psus) == pytest.approx(capped_w)
    assert all(p.load_fraction <= 0.8 + 1e-9 for p in rig.report.psus)
    assert sum(p.worst_a for p in rig.report.psus) == pytest.approx(51.2)
    assert totals.controllers == 2  # the boards follow the pixels, not the cap
    assert not codes(rig, "violation")


def test_a_cap_checks_feeds_at_the_capped_current():
    rig = golden_capped(max_brightness=0.184)
    feeds = rig.report.feeds
    assert len(feeds) < 24  # the cap lets each feed take more bars
    for f in feeds:
        assert f.capped_a == pytest.approx(f.current_a / 2 * 0.184)
        lo, hi = f.fuse_window_a
        assert lo == pytest.approx(f.capped_a / 0.75) and hi == 4.0 and lo <= f.fuse_a <= hi
        assert f.drop_fraction <= 0.10  # the drop still takes every channel full
    relies = {i.ref for i in rig.issues if i.code == "relies_on_cap_and_fuse"}
    assert relies == {f"feed {f.id}" for f in feeds if f.current_a > 4.0} != set()
    note = next(n for n in rig.report.notes if n.startswith("Under the power cap"))
    assert "fuse" in note and "NOT guaranteed" in note
    assert "113.0 W" in next(n for n in rig.report.notes if n.startswith("PSUs are sized"))


def capped_chain(n, power, fuse_a):
    obj = one_chain(n, step=(0.5, 0, 0), feeds=[{"id": "f", "first": 0, "count": n, "fuse_a": fuse_a}])
    return compiled({**obj, "power": power} if power else obj)


def test_a_capped_feed_needs_a_fuse_and_warns_when_it_relies_on_one():
    # 4 bars: 4.27 A with every channel full, over the 4 A connector; 2.13 A at most from RGB.
    assert codes(capped_chain(4, None, 3)) == ["feed_over_rating", "fuse_outside_window"]
    assert codes(capped_chain(4, {"max_brightness": 0.5}, None)) == ["cap_without_fuse"]
    rig = capped_chain(4, {"max_brightness": 0.5}, 3)  # 1.07 A under the cap, window [1.42, 4] A
    assert codes(rig) == ["relies_on_cap_and_fuse"]
    (relies,) = [i.message for i in rig.issues if i.code == "relies_on_cap_and_fuse"]
    assert "4.27 A" in relies and "3 A fuse" in relies
    assert codes(capped_chain(12, {"max_brightness": 0.5}, 4))[:1] == ["feed_over_rating"]  # 3.2 A under the cap
    assert codes(capped_chain(2, {"max_brightness": 0.5}, 3)) == []  # 2.13 A is within the 4 A connector


def test_a_psu_that_only_the_cap_keeps_in_rating_is_flagged():
    rig = golden_capped(max_brightness=0.0)
    (p1,) = rig.report.psus
    assert (p1.current_a, p1.worst_a) == (0.0, pytest.approx(51.2))
    (warning,) = [i for i in rig.issues if i.code == "psu_full_white_overload"]
    assert "51.2 A of its 14.6 A" in warning.message


def test_a_psu_output_connector_limits_its_feeds(tmp_path):
    rig = compiled(EXAMPLES / "golden-rings-4-bricks.json")
    assert {f.connector_a for f in rig.report.feeds} == {4.0}  # the bars' 4 A binds under the barrel's 5 A
    root = tmp_path / "data"
    shutil.copytree(DATA_ROOT, root)
    path = root / "connector" / "barrel-5.5x2.1.json"
    barrel = json.loads(path.read_text())
    barrel["rated_a"]["v"] = 2
    path.write_text(json.dumps(barrel))
    weak = compiled(EXAMPLES / "golden-rings-4-bricks.json", read_catalog(root))
    assert {f.connector_a for f in weak.report.feeds} == {2.0}
    assert "fuse_outside_window" in codes(weak)  # a 3 A fuse is over the 2 A barrel


def test_the_rig_limiter_follows_the_arrangement_cap():
    rig = golden_capped(max_watts=500)
    yellow = np.ones((rig.n, 3), np.float32)
    yellow[:, 2] = 0.0  # red and green: the most an RGB frame draws through Accurate auto-white
    out = rig.limiter()(yellow)
    assert out.uncapped_watts == pytest.approx(1228.8 / 2) and out.watts == pytest.approx(500.0)


# ---- the four-brick examples ---------------------------------------------------------


def ceiling(rig, basis):
    """The largest `max_brightness` under which every feed, fuse and PSU of the
    uncapped `rig` passes the capped checks: the head current within the
    connector's and the fuse's loading, and each PSU within its derating.
    `basis` "rgb" takes the RGB worst case, "all" every channel full. The cap
    does not scale a PSU's `board_a`."""
    limits = rig.report.limits
    terms = [1.0]
    for f in rig.report.feeds:
        amps = f.capped_a if basis == "rgb" else f.current_a
        terms += [
            limits.connector_load_fraction * f.connector_a / amps,
            limits.connector_load_fraction * f.fuse_a / amps,
        ]
    for p in rig.report.psus:
        amps = (p.current_a if basis == "rgb" else p.worst_a) - p.board_a
        if p.feeds:
            terms.append((limits.psu_load_fraction * p.i_max_a - p.board_a) / amps)
    return min(terms)


BOARD_A = 0.6 / 0.7 / 24  # one DevKitC-1's 0.6 W through the assumed 70% buck, at 24 V


@pytest.mark.parametrize(
    "name, rgb, conservative, binds",
    [
        ("golden-rings-4-bricks.json", 0.625, 0.3125, "psu_over_derating"),  # 12 bars x 12.8 W x b <= 96 W
        ("golden-rings-4-bricks-head-fed.json", 0.46875, 0.234375, "feed_over_rating"),  # 6.4 A x b <= 3 A
        # 12 bars x 0.533 A x b + the board <= 4 A
        ("golden-rings-4-sets.json", (4 - BOARD_A) / 6.4, (4 - BOARD_A) / 12.8, "psu_over_derating"),
        # 16 bars x 0.533 A x b + the board <= 4 A
        ("golden-rings-tees.json", (4 - BOARD_A) / (16 * I_BAR / 2), (4 - BOARD_A) / (16 * I_BAR), "psu_over_derating"),
    ],
)
def test_four_brick_examples_run_at_their_largest_clean_brightness(name, rgb, conservative, binds):
    # Each example holds the largest cap, to 4 places, with no violation and no PSU over its derating.
    data = json.loads((EXAMPLES / name).read_text())
    uncapped = compiled({**data, "power": {}})
    assert ceiling(uncapped, "rgb") == pytest.approx(rgb) and ceiling(uncapped, "all") == pytest.approx(conservative)
    b = data["power"]["max_brightness"]
    assert ceiling(uncapped, "rgb") - 1e-4 < b <= ceiling(uncapped, "rgb") + 1e-12
    rig = compiled(EXAMPLES / name)
    assert codes(rig, "violation") == [] and "psu_over_derating" not in codes(rig)
    over = compiled({**data, "power": {"max_brightness": round(b + 1e-4, 4)}})
    assert binds in codes(over)


def test_four_brick_report():
    rig = compiled(EXAMPLES / "golden-rings-4-bricks.json")
    r = rig.report
    assert (r.totals.controllers, len(r.outputs), r.totals.psus, r.totals.feeds) == (3, 12, 4, 12)
    assert {(o.pixels, round(o.wire_fps, 1), round(o.fps, 1)) for o in r.outputs} == {(256, 96.9, 66.7)}
    assert [(p.type, round(p.watts, 6), round(p.load_fraction, 6)) for p in r.psus] == [
        ("btf-24v-5a-120w", 96.0, 0.8)
    ] * 4
    assert [len(p.feeds) for p in r.psus] == [3] * 4 and {f.fuse_a for f in r.feeds} == {3.0}
    assert codes(rig).count("relies_on_cap_and_fuse") == 12 and codes(rig).count("psu_full_white_overload") == 4
    assert "fixture_type/clen-rgbw-bar-1m.power.passthrough_ohm" in {
        i.ref for i in rig.issues if i.code == "rests_on_assumed"
    }
    head_fed = compiled(EXAMPLES / "golden-rings-4-bricks-head-fed.json")
    assert {(o.pixels, round(o.fps, 1)) for o in head_fed.report.outputs} == {(768, 32.5)}
    assert codes(head_fed).count("drop_over_limit") == 4 and not codes(head_fed, "violation")


# ---- boards powered from a PSU (PsuPlacement.powers) ------------------------------------


def powered(n=1, profile=S3, powers=("c1",)):
    obj = one_chain(n, step=(0.5, 0, 0), feeds=[{"id": "f", "first": 0, "count": n, "fuse_a": 3}])
    obj["controllers"][0]["profile"] = profile
    obj["wiring"]["chains"][0]["output"] = load_catalog().get(profile).outputs[0].id
    obj["psus"][0]["powers"] = list(powers)
    return compiled(obj)


def test_a_psu_carries_the_board_it_powers():
    plain, rig = (
        compiled(one_chain(1, step=(0.5, 0, 0), feeds=[{"id": "f", "first": 0, "count": 1, "fuse_a": 3}])),
        powered(),
    )
    (p0,), (p1,) = plain.report.psus, rig.report.psus
    assert BUCK_EFFICIENCY.status == "assumed"
    board_a = 0.6 / value(BUCK_EFFICIENCY) / 24  # the S3 profile's power_w through the buck, at the LRS-350-24's 24 V
    assert (p0.powers, p0.board_a) == ([], 0.0) and (p1.powers, p1.board_a) == (["c1"], pytest.approx(board_a))
    assert p1.current_a == pytest.approx(p0.current_a + board_a) and p1.worst_a == pytest.approx(p0.worst_a + board_a)
    assert p1.watts == pytest.approx(p1.current_a * 24) and p1.load_fraction == pytest.approx(p1.current_a / 14.6)
    # The board is a flat load in every total, and in effect power.
    t0, t1 = plain.report.totals, rig.report.totals
    board_w = board_a * 24
    for name in ("worst_w", "rgb_worst_w", "capped_w"):
        assert getattr(t1, name) == pytest.approx(getattr(t0, name) + board_w)
    for name in ("worst_a", "rgb_worst_a", "capped_a"):
        assert getattr(t1, name) == pytest.approx(getattr(t0, name) + board_a)
    dark = np.zeros((rig.n, 3), np.float32)
    assert (plain.estimate_effect_power(dark), rig.estimate_effect_power(dark)) == (0.0, pytest.approx(board_w))
    assert sum(p.watts for p in rig.report.psus) == pytest.approx(t1.capped_w)
    basis = {b.fact: b for b in rig.report.basis}
    assert basis["wiring.buck_efficiency"].used_for == ["PSU loads"]
    assert basis[f"controller/{S3}.power_w"].status == "inferred"
    assert "wiring.buck_efficiency" in {i.ref for i in rig.issues if i.code == "rests_on_assumed"}
    assert "wiring.buck_efficiency" not in {b.fact for b in plain.report.basis}
    (note,) = [n for n in rig.report.notes if "buck" in n]
    assert "PSU p1 also powers board c1 " in note and f"{board_w:.2f} W" in note
    assert [(b.item, b.count) for b in rig.report.bom if b.kind == "component"] == [
        ("74AHCT125 quad level shifter", 1),
        ("buck converter", 1),
    ]
    assert "buck converter" not in {b.item for b in plain.report.bom}


def test_a_watt_cap_counts_the_board():
    # The board's flat draw comes off the watt cap before the bars are scaled, in the report and the limiter alike.
    obj = one_chain(4, step=(0.5, 0, 0), feeds=[{"id": "f", "first": 0, "count": 4, "fuse_a": 3}])
    obj["psus"][0]["powers"] = ["c1"]
    rig = compiled({**obj, "power": {"max_watts": 20}})
    board_w = 0.6 / value(BUCK_EFFICIENCY)
    assert rig.report.totals.capped_w == pytest.approx(20.0)
    assert rig.report.psus[0].watts == pytest.approx(20.0)
    yellow = np.ones((rig.n, 3), np.float32)
    yellow[:, 2] = 0.0
    out = rig.limiter()(yellow)
    assert out.watts == pytest.approx(20.0) and out.scale == pytest.approx((20.0 - board_w) / (4 * 25.6 / 2))


def test_a_board_without_a_power_figure_is_flagged():
    rig = powered(profile="quinled-dig-octa-32-8l")
    assert rig.report.psus[0].board_a == 0.0
    (warning,) = [i for i in rig.issues if i.code == "board_power_unknown"]
    assert warning.ref == "psu p1" and "c1" in warning.message
    # Nothing rests on the buck then, so there is no basis and no note for it.
    assert "wiring.buck_efficiency" not in {b.fact for b in rig.report.basis}
    assert not [n for n in rig.report.notes if "buck" in n]


@pytest.mark.parametrize(
    "powers, code, message",
    [
        (("c9",), "unresolved_ref", "no controller 'c9'"),
        (("c1", "c1"), "powered_twice", "PSU 'p1' lists controller 'c1' twice"),
    ],
)
def test_powers_names_each_declared_board_once(powers, code, message):
    with pytest.raises(RigError) as exc:
        powered(powers=powers)
    assert [(i.code, i.ref, i.message) for i in exc.value.issues] == [(code, "psus[0].powers", message)]


def test_a_board_powered_by_two_psus_is_refused():
    obj = one_chain(1)
    obj["psus"] = [{"id": "p1", "type": PSU, "powers": ["c1"]}, {"id": "p2", "type": PSU, "powers": ["c1"]}]
    with pytest.raises(RigError) as exc:
        compiled(obj)
    assert [(i.code, i.ref) for i in exc.value.issues] == [("powered_twice", "psus[1].powers")]
    assert "'p1' and PSU 'p2'" in exc.value.issues[0].message


def test_a_negative_board_power_is_refused(tmp_path):
    def edit(obj):
        obj["power_w"]["v"] = -1

    with pytest.raises(RigError) as exc:
        edited_catalog(tmp_path, f"controller/{S3}.json", edit)
    assert [(i.code, i.ref) for i in exc.value.issues] == [("bad_value", f"controller/{S3}.power_w")]


def test_auto_wiring_leaves_room_for_the_board(tmp_path):
    # Under Brighter a bar asks 1.07 A, and 7.4% of 14.6 A is 1.08 A: room for one bar, but not for one bar
    # and the board's 0.036 A. So a PSU that powers c1 takes no bar, and each bar goes on a PSU of its own.
    brighter = edited_catalog(
        tmp_path, "firmware/wled-16.0.1.json", lambda obj: obj["ingest"].update(auto_white="brighter")
    )
    obj = auto_line(2, psu_load_fraction=0.074)
    assert [f.psu for f in compiled(obj, brighter).feeds] == ["p1", "p2"]
    obj["psus"][0]["powers"] = ["c1"]
    rig = compiled(obj, brighter)
    assert [f.psu for f in rig.feeds] == ["p2", "p3"]
    assert rig.report.psus[0].feeds == [] and rig.report.psus[0].board_a == pytest.approx(
        0.6 / value(BUCK_EFFICIENCY) / 24
    )
    assert not {"psu_over_derating", "psu_overload"} & set(codes(rig))
    assert all(p.powers == [] for p in rig.report.psus[1:])  # an added PSU copies the type, not the boards


# ---- the four-set example ---------------------------------------------------------------


def test_four_sets_are_self_contained():
    data = json.loads((EXAMPLES / "golden-rings-4-sets.json").read_text())
    rig = compiled(data)
    r = rig.report
    assert (r.totals.controllers, len(r.outputs), r.totals.psus, r.totals.feeds, r.totals.fixtures) == (
        4,
        12,
        4,
        12,
        48,
    )
    assert [(c.outputs, c.outputs_used, c.pixels) for c in r.controllers] == [(4, 3, 768)] * 4
    chains = {c["id"]: c for c in data["wiring"]["chains"]}
    for k, p in enumerate(r.psus, 1):
        # Set k: brick pk powers board ck and feeds the three chains on it, and only those.
        assert (p.id, p.powers, p.board_a) == (f"p{k}", [f"c{k}"], pytest.approx(BOARD_A))
        assert {chains[f.chain]["controller"] for f in r.feeds if f.psu == p.id} == {f"c{k}"}
        assert len(p.feeds) == 3 and round(p.load_fraction, 4) == 0.8
    assert {(o.pixels, round(o.wire_fps, 1), round(o.fps, 1)) for o in r.outputs} == {(256, 96.9, 66.7)}
    assert {f.fuse_a for f in r.feeds} == {3.0} and all(
        f.fuse_window_a[0] <= 3.0 <= f.fuse_window_a[1] for f in r.feeds
    )
    # Each set is one quadrant of both rings, and its box is within 0.65 m (run) of every chain head.
    for k in range(1, 5):
        bars = [fid for c in chains.values() if c["controller"] == f"c{k}" for fid in c["fixtures"]]
        index = {f.id: f for f in rig.fixtures}
        angles = []
        for fid in bars:
            f = index[fid]
            x, z = rig.positions_m[f.pixel_start : f.pixel_start + f.pixel_count][:, [0, 2]].mean(axis=0)
            angles.append(math.degrees(math.atan2(z, x)) % 360)
        assert len(bars) == 12 and all(90 * (k - 1) <= a < 90 * k for a in angles)
    leads = [h for h in r.hops if h.kind == "lead"]
    assert len(leads) == 12 and max(h.run_m for h in leads) < 0.65
    assert max(h.path_m for h in r.hops if h.kind == "link") < r.limits.max_hop_m
    assert "board_power_unknown" not in codes(rig)


# ---- T trunks (Chain.tee) --------------------------------------------------------------


def test_a_tee_chain_runs_its_links_from_input_to_input():
    # Three bars 0.5 m apart. On T drops each hop runs along the trunk between the bars' inputs,
    # and its path adds both pigtails and the first bar's 0.7 m return between its pigtail exits;
    # the link carries no pass-through.
    feeds = [{"id": "f", "first": 0, "count": 3, "fuse_a": 3}]
    series, tee = one_chain(3, step=(0.5, 0, 0), feeds=feeds), one_chain(3, step=(0.5, 0, 0), feeds=feeds)
    tee["wiring"]["chains"][0]["tee"] = True
    a, b = compiled(series).report, compiled(tee).report
    links = [h for h in b.hops if h.kind == "link"]
    assert [(round(h.run_m, 9), round(h.path_m, 9)) for h in links] == [(0.6, 0.6 + 2 * 0.2 + 0.7)] * 2
    assert [round(h.run_m, 6) for h in a.hops if h.kind == "link"] == [round(1.2 * math.hypot(0.5, 0.7), 6)] * 2
    per_m = loop_ohm_per_m(1.309, 1.309)
    assert b.feeds[0].drop_v == pytest.approx(feed_drop_v([I_BAR] * 3, 2.0 * per_m, [0.6 * per_m] * 2), rel=1e-12)
    assert b.feeds[0].drop_v < a.feeds[0].drop_v
    # The power numbers do not depend on the topology.
    assert (b.feeds[0].current_a, b.feeds[0].capped_a, b.feeds[0].connector_a) == (
        a.feeds[0].current_a,
        a.feeds[0].capped_a,
        a.feeds[0].connector_a,
    )
    facts = {x.fact for x in b.basis}
    assert f"fixture_type/{BAR}.power.passthrough_ohm" not in facts
    assert f"fixture_type/{BAR}.power.passthrough_ohm" in {x.fact for x in a.basis}
    bom = {line.item: (line.count, line.length_m) for line in b.bom if line.kind == "cable"}
    assert "link" not in bom and bom["trunk"] == (2, pytest.approx(1.2))
    assert {line.item for line in a.bom if line.kind == "cable"} >= {"link"}
    # The T parts' rating and gauge are not found, so the report names them as assumed.
    basis = {x.fact: x for x in b.basis}
    assert basis["wiring.tee_connectors"].status == "assumed" and "wiring.tee_connectors" not in {
        x.fact for x in a.basis
    }
    assert "T-trunk" in basis["wiring.link_conductors"].src
    assert "T-trunk" not in {x.fact: x for x in a.basis}["wiring.link_conductors"].src


def test_a_t_trunk_fed_from_two_psus_is_a_violation():
    # A trunk's V+ runs along every T, so it cannot be left open between two supplies (RES-032).
    feeds = [
        {"id": "f", "first": 0, "count": 2, "fuse_a": 3},
        {"id": "g", "first": 2, "count": 2, "fuse_a": 3, "psu": "p2"},
    ]
    obj = one_chain(4, step=(0.5, 0, 0), feeds=feeds)
    obj["psus"].append({"id": "p2", "type": PSU})
    series = compiled(obj)
    obj["wiring"]["chains"][0]["tee"] = True
    tee = compiled(obj)
    assert "tee_supplies_join" not in codes(series) and any("Keep V+ open" in n for n in series.report.notes)
    (issue,) = [i for i in tee.issues if i.code == "tee_supplies_join"]
    assert (issue.level, issue.ref) == ("violation", "chain A") and "p1, p2" in issue.message
    assert not any("Keep V+ open" in n for n in tee.report.notes)
    # One PSU feeding a trunk twice joins nothing.
    obj["wiring"]["feeds"][1]["psu"] = "p1"
    assert "tee_supplies_join" not in codes(compiled(obj))


def test_the_t_trunk_example_hangs_each_set_on_two_trunks():
    data = json.loads((EXAMPLES / "golden-rings-tees.json").read_text())
    rig = compiled(data)
    r = rig.report
    assert (r.totals.controllers, len(r.outputs), r.totals.psus, r.totals.feeds, r.totals.fixtures) == (2, 6, 3, 6, 48)
    assert [(c.outputs, c.outputs_used, c.pixels) for c in r.controllers] == [(4, 4, 2048), (4, 2, 1024)]
    assert {(o.pixels, round(o.wire_fps, 1), round(o.fps, 1)) for o in r.outputs} == {(512, 48.6, 48.6)}
    chains = {c["id"]: c for c in data["wiring"]["chains"]}
    assert all(c["tee"] for c in chains.values())
    assert sorted(f for c in chains.values() for f in c["fixtures"]) == sorted(
        f"{g}/{k}" for g in ("inner", "outer") for k in range(24)
    )
    # One feed per trunk, so no two bricks share a trunk's V+ (RES-032); the cap holds each head and brick.
    assert sorted(f.chain for f in r.feeds) == sorted(chains)
    assert [(p.id, p.powers, len(p.feeds)) for p in r.psus] == [("p1", ["c1"], 2), ("p2", [], 2), ("p3", ["c2"], 2)]
    assert all(p.load_fraction <= 0.8 + 1e-9 for p in r.psus)
    assert all(
        f.capped_a <= 0.75 * f.connector_a + 1e-9 and f.fuse_window_a[0] <= 3.0 <= f.fuse_window_a[1] for f in r.feeds
    )
    # Each trunk is 8 neighbouring bars of one ring, in one 120-degree set, headed from its set's box.
    index = {f.id: f for f in rig.fixtures}
    for cid, chain in chains.items():
        k = int(cid[1])
        angles = []
        for fid in chain["fixtures"]:
            f = index[fid]
            x, z = rig.positions_m[f.pixel_start : f.pixel_start + f.pixel_count][:, [0, 2]].mean(axis=0)
            angles.append(round(math.degrees(math.atan2(z, x)) % 360, 6))
        assert len(angles) == 8 and all(120 * (k - 1) <= a < 120 * k for a in angles), cid
    leads = [h for h in r.hops if h.kind == "lead"]
    assert len(leads) == 6 and max(h.run_m for h in leads) < 1.0
    assert max(h.path_m for h in r.hops if h.kind == "link") < r.limits.max_hop_m
    bom = {line.item: line.count for line in r.bom if line.kind == "cable"}
    assert "link" not in bom and bom["trunk"] == 42
    assert codes(rig).count("relies_on_cap_and_fuse") == 6 and "board_power_unknown" not in codes(rig)


@pytest.mark.parametrize(
    "power",
    [
        {"max_watts": 0},
        {"max_watts": -5},
        {"max_watts": 1e7},
        {"max_brightness": 1.5},
        {"max_brightness": -0.1},
        {"max_amps": 3},
    ],
)
def test_the_power_block_is_bounded(power):
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    with pytest.raises(RigError):
        load_arrangement({**data, "power": power})


def test_the_power_block_round_trips_and_defaults():
    data = json.loads((EXAMPLES / "golden-rings.json").read_text())
    assert "power" not in data and data["version"] == 1
    assert load_arrangement(data).power.cap.caps is False
    arr = load_arrangement({**data, "power": {"max_watts": 500, "max_brightness": 0.5}})
    assert (arr.power.max_watts, arr.power.max_brightness) == (500.0, 0.5)
    assert load_arrangement(arr.model_dump(mode="json")) == arr
    assert load_arrangement({**data, "power": {"max_watts": None}}).power.cap.caps is False
