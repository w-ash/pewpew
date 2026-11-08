"""`pewpew.mapping.contain` keeps room mappings bit-identical."""

from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from fakes import EXAMPLE_ROOM
from pewpew.mapping import contain, pixel_offsets
from pewpew.room.map import _compile, _Spec, load_room


def _reference(meters: np.ndarray):
    """The room compiler's arithmetic before `contain` was shared."""
    lo, hi = meters.min(axis=0), meters.max(axis=0)
    extent = hi - lo
    longest = float(extent.max()) or 1.0
    span = extent / longest
    offset = np.where(extent > 0, (1.0 - span) / 2.0, 0.0)
    mapping = np.ascontiguousarray((meters - lo) / longest + offset, dtype=np.float32)
    shift = tuple(float(v) for v in offset - lo / longest)
    return mapping, tuple(float(s) for s in span), tuple(float(e) for e in extent), 1.0 / longest, shift


def _same(meters: np.ndarray, room) -> None:
    mapping, span, extent, scale, shift = _reference(meters)
    assert room.mapping.tobytes() == mapping.tobytes()
    assert (room.span, room.extent, room.scale, room.shift) == (span, extent, scale, shift)
    got = contain(meters)
    assert got.mapping.tobytes() == mapping.tobytes()
    assert (got.span, got.extent, got.scale, got.shift) == (span, extent, scale, shift)


def test_room_example_mapping_is_bit_equal():
    room, _ = load_room(EXAMPLE_ROOM)
    _same(room.meters, room)


_coord = st.floats(-20, 20, allow_nan=False, allow_infinity=False, width=32)


@st.composite
def _rooms(draw):
    n = draw(st.integers(1, 5))
    specs = []
    for i in range(n):
        start = np.array([draw(_coord), draw(_coord), draw(st.sampled_from([0.0, draw(_coord)]))])
        delta = np.array([draw(_coord), draw(_coord), 0.0]) + np.array([0.5, 0.0, 0.0])
        specs.append(
            _Spec(
                id=f"f{i}", pixels=draw(st.integers(1, 30)), start=start, end=start + delta,
                pitch=draw(st.floats(0.005, 0.1)), input=draw(st.sampled_from(["start", "end"])),
                board="b", output=i, chain=0,
            )
        )
    return specs


@given(_rooms())
def test_generated_room_mapping_is_bit_equal(specs):
    room = _compile(specs, {"b": ("10.0.0.1", 4048)})
    _same(room.meters, room)


def test_contain_edge_cases():
    one = contain(np.array([[3.0, 4.0, 5.0]]))
    assert one.mapping.tolist() == [[0.0, 0.0, 0.0]]
    flat = contain(np.array([[0.0, 0.0, 7.0], [4.0, 2.0, 7.0]]))
    assert flat.mapping.tolist() == [[0.0, 0.25, 0.0], [1.0, 0.75, 0.0]]
    assert contain(np.zeros((0, 3))).mapping.shape == (0, 3)


def test_pixel_offsets_centre_the_pixels():
    assert pixel_offsets(4, 2.0).tolist() == [-0.75, -0.25, 0.25, 0.75]
    assert pixel_offsets(1, 3.0).tolist() == [0.0]
