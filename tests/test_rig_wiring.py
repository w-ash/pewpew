"""Auto-wiring: chains, outputs, derived controllers, feeds and PSUs (docs/studio/domain-model.md:217-226)."""

from __future__ import annotations

import copy
import json
import shutil

import pytest

from pewpew.rig import EXAMPLES, RigError, compile_rig, load_arrangement, load_catalog, read_catalog
from pewpew.rig.catalog import CATALOG_ENTRIES_DIR
from pewpew.rig.electrical import has_conductors, max_px
from pewpew.rig.wiring import lowest_loss_cable

BAR = "clen-rgbw-bar-1m"
TUBE = "clen-360-tube-1500"
S3 = "esp32s3-devkitc1-ahct125"
PSU = "meanwell-lrs-350-24"
OCTA = "quinled-dig-octa-32-8l"
GOLDEN = json.loads((EXAMPLES / "golden-rings.json").read_text())


def compiled(obj, catalog=None):
    return compile_rig(load_arrangement(obj), catalog or load_catalog())


def line(type_id, n, step=(1.0, 0.0, 0.0), prefix="x"):
    """`n` free fixtures `step` apart, all along +y, as a list of placements."""
    return [
        {"id": f"{prefix}{i}", "type": type_id, "pose": {"position_m": [step[0] * i, step[1] * i, step[2] * i]}}
        for i in range(n)
    ]


def auto(fixtures, controllers=({"id": "c1", "profile": S3},), psus=({"id": "p1", "type": PSU},), **options):
    return {
        "format": "pewpew.arrangement",
        "version": 1,
        "fixtures": fixtures,
        "controllers": list(controllers),
        "psus": list(psus),
        "wiring": {"auto": options},
    }


def golden(catalog=None, **options):
    obj = copy.deepcopy(GOLDEN)
    obj["wiring"]["auto"].update(options)
    return compiled(obj, catalog)


def brighter_wled():
    """WLED set to Brighter auto-white: an RGB frame then reaches every channel
    of a bar, so a PSU's load is its feeds' every-channel current."""
    wled = json.loads((CATALOG_ENTRIES_DIR / "firmware/wled-16.0.1.json").read_text())
    return {**wled, "ingest": {**wled["ingest"], "auto_white": "brighter"}}


@pytest.fixture(scope="module")
def brighter(tmp_path_factory):
    """The bundled catalog with `brighter_wled`, for the PSU-packing tests written at every-channel loads."""
    root = tmp_path_factory.mktemp("brighter") / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    (root / "firmware/wled-16.0.1.json").write_text(json.dumps(brighter_wled()))
    return read_catalog(root)


# ---- the per-output cap -------------------------------------------------------------


def test_pixels_per_output_from_frame_rate():
    # docs/studio/domain-model.md:362, and the 30/40/60 fps rows of the A3 report
    # (docs/studio/planning/2026-10-22-a3-power-wiring-controllers.md:87-91).
    assert max_px(40e-6, 80e-6, 40) == 623
    assert max_px(40e-6, 80e-6, 30) == 831
    assert max_px(40e-6, 80e-6, 60) == 414
    assert max_px(40e-6, 80e-6, 1e6) == 0


def test_golden_rings_at_four_per_output_take_twelve_chains_on_three_boards():
    # docs/studio/domain-model.md:365.
    rig = golden(fixtures_per_output=4)
    assert len(rig.slices) == 12
    assert {s.count for s in rig.slices} == {4 * 64}
    assert [c.controller for c in rig.controller_slices] == ["c1", "c2", "c3"]
    assert [(c.id, c.derived, c.outputs_used) for c in rig.report.controllers] == [
        ("c1", False, 4),
        ("c2", True, 4),
        ("c3", True, 4),
    ]
    assert rig.report.totals.controllers == 3
    assert "Auto-wiring added controllers c2, c3" in rig.report.notes[0]
    # Pixels run controller, then output, then chain, then pixel.
    assert [s.start for s in rig.slices] == [k * 256 for k in range(12)]
    assert [f.id for f in rig.fixtures[:5]] == ["inner/0", "inner/1", "inner/2", "inner/3", "inner/4"]
    assert rig.fixtures[4].chain == "c1.rmt1"


def test_golden_rings_at_the_default_cap_take_six_chains_of_eight():
    # 40 fps caps an output at ⌊623/64⌋ = 9 bars, so each ring of 24 is 3 chains of 8.
    rig = golden()
    assert [(s.controller, s.output, s.count // 64) for s in rig.slices] == [
        ("c1", "rmt0", 8),
        ("c1", "rmt1", 8),
        ("c1", "rmt2", 8),
        ("c1", "rmt3", 8),
        ("c2", "rmt0", 8),
        ("c2", "rmt1", 8),
    ]
    assert {f.group for f in rig.fixtures[:24]} == {"inner"}


def test_chains_are_even_and_break_at_long_hops():
    ten = compiled(auto(line(BAR, 10)))  # cap 9, so 5 + 5
    assert [s.count // 64 for s in ten.slices] == [5, 5]
    # x0..x2 1 m apart, then a 5 m gap: the hop is about 5 x 1.2 + 0.4 m of pigtails.
    gap = line(BAR, 3) + [{"id": f"y{i}", "type": BAR, "pose": {"position_m": [7.0 + i, 0, 0]}} for i in range(3)]
    rig = compiled(auto(gap))
    assert [[f.id for f in rig.fixtures if f.chain == s.chain] for s in rig.slices] == [
        ["x0", "x1", "x2"],
        ["y0", "y1", "y2"],
    ]
    assert "hop_over_limit" not in {i.code for i in rig.issues}
    longer = compiled(auto(gap, max_hop_m=8))
    assert len(longer.slices) == 1


def test_runs_split_by_pixel_format_and_led_type_groups(tmp_path):
    fixtures = line(BAR, 2) + line(TUBE, 2, prefix="t")
    rig = compiled(auto(fixtures))
    assert [(s.controller, s.output, s.led_type) for s in rig.slices] == [("c1", "rmt0", 30), ("c1", "rmt1", 22)]
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    path = root / "controller" / f"{S3}.json"
    obj = json.loads(path.read_text())
    obj["groups"]["rmt"]["same_led_type"] = True
    path.write_text(json.dumps(obj))
    rig = compiled(auto(fixtures), read_catalog(root))
    assert [(s.controller, s.output, s.led_type) for s in rig.slices] == [("c1", "rmt0", 30), ("c2", "rmt0", 22)]


def test_derived_ids_skip_the_declared_ones():
    ctrls = ({"id": "c1", "profile": S3}, {"id": "c3", "profile": S3})
    rig = compiled(auto(line(BAR, 9 * 9), controllers=ctrls))  # 9 chains of 9: 4 + 4 + 1 outputs
    assert [c.id for c in rig.report.controllers] == ["c1", "c3", "c4"]


def test_without_a_controller_or_a_psu_nothing_is_guessed():
    rig = compiled(auto(line(BAR, 2), controllers=()))
    assert rig.slices == ()
    assert [i.code for i in rig.issues if i.code != "rests_on_assumed"] == ["unwired"]
    rig = compiled(auto(line(BAR, 2), psus=()))
    assert rig.feeds == () and rig.report.psus == []
    unfed = [i for i in rig.issues if i.code == "unfed"]
    assert len(unfed) == 1 and "declare a PSU" in unfed[0].message


# ---- feeds and PSUs ---------------------------------------------------------------


def feed_sizes(rig):
    return [f.count for f in rig.feeds]


def test_feeds_hold_the_connector_at_75_percent():
    # docs/studio/domain-model.md:363 and RES-033 (the maintainer's private notes):
    # on 4 A at 75%, 2 bars fit (2.133 A), 3 bars do not (3.2 A), 2 tubes fit at exactly 3.0 A.
    assert feed_sizes(compiled(auto(line(BAR, 3)))) == [2, 1]
    assert feed_sizes(compiled(auto(line(BAR, 4)))) == [2, 2]
    tubes = compiled(auto(line(TUBE, 4, step=(0, 0, 0.5))))
    assert feed_sizes(tubes) == [2, 2]
    assert tubes.report.feeds[0].current_a == 3.0
    bars = compiled(auto(line(BAR, 2)))
    assert bars.report.feeds[0].current_a == pytest.approx(2.1333, abs=5e-5)
    assert bars.feeds[0].fuse_a == 3.0
    assert tubes.feeds[0].fuse_a == 4.0  # the window is [4.0, 4.0]


def test_drop_limits_feeds_too():
    far = {"id": "p1", "type": PSU, "position_m": [0, 0, -40.0]}
    rig = compiled(auto(line(BAR, 2), psus=(far,), feed_cable="wire-18awg-pair"))
    assert feed_sizes(rig) == [1, 1]  # 48 m of 18 AWG drops 2.1 V on one bar, 4.3 V on two
    assert rig.feeds[0].length_m == pytest.approx(1.2 * 40.0, abs=0.1)


def test_psus_fill_first_fit_to_80_percent_and_more_are_added(brighter):
    rig = golden(brighter)
    psus = rig.report.psus
    assert [(p.id, p.derived, len(p.feeds)) for p in psus] == [
        ("p1", False, 5),
        ("p2", True, 5),
        ("p3", True, 5),
        ("p4", True, 5),
        ("p5", True, 4),
    ]
    assert max(p.load_fraction for p in psus) <= 0.8
    assert sum(p.current_a for p in psus) == pytest.approx(51.2)
    assert len(rig.feeds) == 24 and {f.fuse_a for f in rig.feeds} == {3.0}
    assert "Auto-wiring added PSUs p2, p3, p4, p5" in rig.report.notes[1]
    # p1 has no position: feeds run from the origin, flagged as assumed.
    assert "psu p1.position_m" in {i.ref for i in rig.issues if i.code == "rests_on_assumed"}


def test_accurate_auto_white_halves_each_psu_load():
    # Under Accurate an RGB frame reaches 2 of a bar's 4 channels, so a PSU carries 10 two-bar feeds, not 5.
    rig = golden()
    assert [(p.id, len(p.feeds)) for p in rig.report.psus] == [("p1", 10), ("p2", 10), ("p3", 4)]
    assert sum(p.current_a for p in rig.report.psus) == pytest.approx(51.2 / 2)
    assert sum(p.worst_a for p in rig.report.psus) == pytest.approx(51.2)
    assert len(rig.feeds) == 24 and {f.fuse_a for f in rig.feeds} == {3.0}
    assert {i.ref for i in rig.issues if i.code == "psu_full_white_overload"} == {"psu p1", "psu p2"}


def test_the_feed_cable_defaults_to_the_lowest_loss_one():
    assert lowest_loss_cable(load_catalog()) == "wire-16awg-pair"
    assert {f.cable for f in golden().feeds} == {"wire-16awg-pair"}
    assert {f.cable for f in golden(feed_cable="wire-18awg-pair").feeds} == {"wire-18awg-pair"}
    with pytest.raises(RigError) as exc:
        golden(feed_cable="no-such-cable")
    assert "unresolved_ref" in {i.code for i in exc.value.issues}


def test_auto_wiring_is_deterministic():
    a, b = golden(fixtures_per_output=4), golden(fixtures_per_output=4)
    assert json.dumps(a.to_json()) == json.dumps(b.to_json())


# ---- the ws2 review (docs/studio/reports/reviews/ws2-code-review.md) ----------------------


def bundled(rel):
    return json.loads((CATALOG_ENTRIES_DIR / rel).read_text())


def catalog_with(tmp_path, files):
    """The bundled catalog with `files` ({path under data/: entity}) written over it."""
    root = tmp_path / "data"
    shutil.copytree(CATALOG_ENTRIES_DIR, root)
    for rel, obj in files.items():
        (root / rel).write_text(json.dumps(obj))
    return read_catalog(root)


def codes(rig):
    return {i.code for i in rig.issues if i.code != "rests_on_assumed"}


def test_a_feed_is_sized_for_the_psu_it_is_on(brighter):
    # Finding 1: p1 is full after 10 bars, and the two left go to p2, 40 m away, one bar a feed.
    psus = (
        {"id": "p1", "type": PSU, "position_m": [0, 0, 0.5]},
        {"id": "p2", "type": PSU, "position_m": [0, 0, -40.0]},
    )
    rig = compiled(auto(line(BAR, 12), psus=psus, feed_cable="wire-18awg-pair"), brighter)
    assert [(f.psu, f.count) for f in rig.feeds] == [("p1", 2)] * 5 + [("p2", 1)] * 2
    assert max(f.drop_fraction for f in rig.report.feeds) <= 0.10
    assert "drop_over_limit" not in codes(rig)


def test_a_feed_never_outgrows_its_psu(brighter):
    # Finding 4: at 10% of 14.6 A a PSU carries one bar (1.07 A), not the two the connector allows.
    rig = compiled(auto(line(BAR, 4), psu_load_fraction=0.1), brighter)
    assert [(f.psu, f.count) for f in rig.feeds] == [("p1", 1), ("p2", 1), ("p3", 1), ("p4", 1)]
    assert not {"psu_over_derating", "psu_overload"} & codes(rig)
    # One bar over a whole PSU's share: another PSU cannot help, so the bars stay on p1, flagged.
    rig = compiled(auto(line(BAR, 3), psu_load_fraction=0.05), brighter)
    assert [(f.psu, f.count) for f in rig.feeds] == [("p1", 1)] * 3
    assert [p.id for p in rig.report.psus] == ["p1"] and "psu_over_derating" in codes(rig)


def test_a_chain_fits_the_board_pixel_limit():
    # Finding 5: the Dig-Octa advises 2,000 px, so a chain takes at most 31 bars, and c1 is used.
    rig = compiled(auto(line(BAR, 64), controllers=({"id": "c1", "profile": OCTA},), target_fps=1))
    assert [(s.controller, s.count // 64) for s in rig.slices] == [("c1", 22), ("c2", 21), ("c3", 21)]
    assert "controller_over_advised" not in codes(rig)


def test_an_added_board_has_a_profile_that_drives_the_chain(tmp_path):
    # Finding 6: board a drives no RGBW, so the board added for the fifth chain copies b.
    wled = bundled("firmware/wled-16.0.1.json")
    rgb_only = {**wled, "id": "rgb-only", "led_types": [t for t in wled["led_types"] if t["channels"] == "RGB"]}
    board = {**bundled(f"controller/{S3}.json"), "id": "rgb-board", "firmware": "rgb-only"}
    cat = catalog_with(tmp_path, {"firmware/rgb-only.json": rgb_only, "controller/rgb-board.json": board})
    ctrls = ({"id": "a", "profile": "rgb-board"}, {"id": "b", "profile": S3, "position_m": [0, 0, -1.0]})
    rig = compiled(auto(line(BAR, 45), controllers=ctrls), cat)  # 5 chains of 9
    assert "unwired" not in codes(rig) and rig.n == 45 * 64
    assert [(c.id, c.profile, c.derived) for c in rig.report.controllers] == [
        ("a", "rgb-board", False),
        ("b", S3, False),
        ("c3", S3, True),
    ]
    assert f"Each has b's profile ({S3}) and position." in rig.report.notes[0]
    # c3 stands at b's position, so no lead runs from an assumed origin.
    assert not any((i.ref or "").startswith("controller ") for i in rig.issues if i.code == "rests_on_assumed")


def test_feeds_go_to_a_psu_of_their_voltage(tmp_path):
    # Finding 7: the 24 V bars skip the 5 V p1, and the PSU added copies p2.
    five = {**bundled(f"psu/{PSU}.json"), "id": "test-5v", "v_out": 5}
    cat = catalog_with(tmp_path, {"psu/test-5v.json": five, "firmware/wled-16.0.1.json": brighter_wled()})
    psus = ({"id": "p1", "type": "test-5v"}, {"id": "p2", "type": PSU})
    rig = compiled(auto(line(BAR, 4), psus=psus), cat)
    assert {f.psu for f in rig.feeds} == {"p2"} and "psu_voltage" not in codes(rig)
    rig = compiled(auto(line(BAR, 12), psus=psus), cat)  # 12.8 A is over p2's 11.68 A
    assert [(p.id, p.type, len(p.feeds)) for p in rig.report.psus] == [
        ("p1", "test-5v", 0),
        ("p2", PSU, 5),
        ("p3", PSU, 1),
    ]
    assert f"Each has p2's type ({PSU}) and position." in rig.report.notes[0]


def test_a_chain_fed_from_two_psus_gets_a_note(brighter):
    # Finding 10: RES-032 says to feed each chain from one supply (the maintainer's private notes).
    note = next(n for n in golden(brighter).report.notes if n.startswith("Chains"))
    assert note.startswith("Chains c1.rmt1, c1.rmt2, c1.rmt3 take feeds from more than one PSU.")
    assert not any(n.startswith("Chains") for n in compiled(auto(line(BAR, 4))).report.notes)


def test_a_declared_id_never_reads_as_added(brighter):
    # Finding 11: controller p2 is declared, while PSU p2 is added.
    obj = copy.deepcopy(GOLDEN)
    obj["controllers"][0]["id"] = "p2"
    rig = compiled(obj, brighter)
    assert [(c.id, c.derived) for c in rig.report.controllers] == [("p2", False), ("c2", True)]
    assert [p.id for p in rig.report.psus if p.derived] == ["p2", "p3", "p4", "p5"]


def test_a_cable_without_power_conductors_is_never_a_feed_cable(tmp_path):
    # Finding 14: one check, `has_conductors`, serves auto-wiring and explicit feeds.
    data_only = {**bundled("cable/wire-18awg-pair.json"), "id": "data-only", "conductors_mm2": {"data": 0.2}}
    cat = catalog_with(tmp_path, {"cable/data-only.json": data_only})
    assert not has_conductors(cat, "data-only") and has_conductors(cat, "wire-16awg-pair")
    assert lowest_loss_cable(cat) == "wire-16awg-pair"
    with pytest.raises(RigError) as exc:
        compiled(auto(line(BAR, 2), feed_cable="data-only"), cat)
    assert [i.code for i in exc.value.issues] == ["no_conductors"]
    fixtures = line(BAR, 2)
    explicit = {
        **auto(fixtures),
        "wiring": {
            "chains": [{"id": "A", "controller": "c1", "output": "rmt0", "fixtures": ["x0", "x1"]}],
            "feeds": [
                {"id": "f", "psu": "p1", "chain": "A", "first": 0, "count": 2, "cable": "data-only", "length_m": 1.0}
            ],
        },
    }
    with pytest.raises(RigError) as exc:
        compiled(explicit, cat)
    assert [i.code for i in exc.value.issues] == ["no_conductors"]
