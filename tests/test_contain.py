"""`pewpew.mapping.contain` keeps mappings bit-identical to the original arithmetic."""

from __future__ import annotations

import json

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from fakes import EXAMPLE_RIG, LEGACY_ROOM, room_meters
from pewpew.mapping import contain, pixel_offsets
from pewpew.rig.runtime import load_rig


def _reference(meters: np.ndarray):
    """The arithmetic of the room compiler before `contain` was shared."""
    lo, hi = meters.min(axis=0), meters.max(axis=0)
    extent = hi - lo
    longest = float(extent.max()) or 1.0
    span = extent / longest
    offset = np.where(extent > 0, (1.0 - span) / 2.0, 0.0)
    mapping = np.ascontiguousarray((meters - lo) / longest + offset, dtype=np.float32)
    shift = tuple(float(v) for v in offset - lo / longest)
    return mapping, tuple(float(s) for s in span), tuple(float(e) for e in extent), 1.0 / longest, shift


def _same(meters: np.ndarray) -> None:
    mapping, span, extent, scale, shift = _reference(meters)
    got = contain(meters)
    assert got.mapping.tobytes() == mapping.tobytes()
    assert (got.span, got.extent, got.scale, got.shift) == (span, extent, scale, shift)


def test_room_example_mapping_is_bit_equal():
    _same(room_meters(json.loads(LEGACY_ROOM.read_text())))


def test_the_canopy_rig_mapping_is_the_contained_room():
    meters = room_meters(json.loads(LEGACY_ROOM.read_text()))
    rig, _ = load_rig(EXAMPLE_RIG)
    assert np.abs(rig.mapping.astype(np.float64) - contain(meters).mapping).max() <= 1e-7


_coord = st.floats(-20, 20, allow_nan=False, allow_infinity=False, width=32)


_point = st.tuples(_coord, _coord, st.sampled_from([0.0, 1.5, -3.0]))


@given(st.lists(_point, min_size=1, max_size=60))
def test_generated_point_mapping_is_bit_equal(points):
    _same(np.array(points, dtype=np.float64))


def test_contain_edge_cases():
    one = contain(np.array([[3.0, 4.0, 5.0]]))
    assert one.mapping.tolist() == [[0.0, 0.0, 0.0]]
    flat = contain(np.array([[0.0, 0.0, 7.0], [4.0, 2.0, 7.0]]))
    assert flat.mapping.tolist() == [[0.0, 0.25, 0.0], [1.0, 0.75, 0.0]]
    assert contain(np.zeros((0, 3))).mapping.shape == (0, 3)


def test_pixel_offsets_centre_the_pixels():
    assert pixel_offsets(4, 2.0).tolist() == [-0.75, -0.25, 0.25, 0.75]
    assert pixel_offsets(1, 3.0).tolist() == [0.0]
