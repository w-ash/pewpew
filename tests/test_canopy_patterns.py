"""The canopy set (pulse, wave, wash, sparkle) on the example room: geometry,
fixture units, and photosensitive safety."""

from __future__ import annotations

import numpy as np
import pytest

from pewpew import Float, Pattern, hsv, render_sequence
from pewpew.classinfo import pattern_name
from pewpew.metrics import FLASH_LIMIT, flash_rates
from pewpew.params import ParamSet
from pewpew.params.probes import leaves
from pewpew.patterns import Pulse, Sparkle, Wash, Wave, canopy

CANOPY_SET = (Pulse, Wave, Wash, Sparkle)

FPS = 60.0
SECONDS = 4

# Each pattern at its most aggressive settings for flashing: speed at the top
# of its range, and the colour and shape that swing luminance the most.
# Saturation 0 is white, the widest luminance swing for a brightness change;
# the wash changes only hue, so it flashes most fully saturated. Brightness
# is always full.
WHITE = {"h": 0.0, "s": 0.0, "v": 1.0}
AGGRESSIVE = {
    Pulse: {"speed": 1.0, "depth": 1.0, "color": WHITE},
    Wave: {"speed": 1.0, "width": 0.1, "color": WHITE},
    Wash: {"speed": 0.1, "spread": 2.0, "color": {"h": 0.0, "s": 1.0, "v": 1.0}},
    Sparkle: {"speed": 1.0, "tail": 0.1, "color": WHITE},
}


def test_the_gallery_canopy_is_the_example_room(example):
    """STUDY_CASES renders the canopy set on `canopy()`, a copy of the example
    room built in code. If the example changes, update `canopy()` to match
    (and regenerate the canopy set's baselines) or let the two part on purpose."""
    built = canopy()
    assert np.array_equal(built.mapping, example.mapping)
    assert np.array_equal(built.centres, example.centres)
    assert np.array_equal(built.fixture_of, example.fixture_of)


@pytest.mark.parametrize("cls", CANOPY_SET, ids=[pattern_name(c) for c in CANOPY_SET])
@pytest.mark.parametrize("units", ["pixel", "fixture"])
def test_runs_on_the_room_in_either_units(cls, units, example):
    frames = render_sequence(cls, example.mapping, seed=7, frames=20, grouping=example.grouping, units=units)
    assert frames.shape == (20, example.n, 3)
    assert np.isfinite(frames).all() and frames.min() >= 0.0 and frames.max() <= 1.0
    assert frames.std(axis=0).max() > 0.0  # it moves
    if units == "fixture":
        firsts = [f.first for f in example.fixtures]
        assert np.array_equal(frames[:, firsts][:, example.fixture_of], frames)


def test_wave_travels_in_its_direction(example):
    """Direction 90 sends the crests up the plan (+y): in half a second the
    crest moves a tenth of the room's length toward +y, give or take the
    0.07 between rows of bars."""
    frames = render_sequence(
        Wave, example.mapping, params={"direction": 90.0, "speed": 0.2, "width": 1.0, "color": WHITE},
        frames=31, grouping=example.grouping,
    )
    y = example.mapping[:, 1]
    lum = frames[..., 0]
    peak = [float(y[np.argmax(frame)]) for frame in lum[[0, 30]]]
    assert 0.0 < peak[1] - peak[0] < 0.2


class _Strobe(Pattern):
    """Test-only: a white on/off square wave, `rate` cycles per second."""

    rate = Float(5.0, 0.1, 30.0, "Hz")

    def __init__(self):
        self.t = 0.0

    def before_render(self, dt, features):
        self.t += dt

    def render(self, x, y, z, index):
        on = float((self.t * self.rate) % 1.0 < 0.5)
        return hsv(0.0, 0.0, np.full(x.shape, on, np.float32))


@pytest.mark.parametrize("rate", [2.0, 3.5, 5.0])
def test_the_flash_count_reads_a_strobe_correctly(rate):
    """A window that holds an odd number of changes counts the half flash, so
    a strobe reads up to half a flash above its rate; the safety check below
    uses that stricter reading."""
    frames = render_sequence(_Strobe, np.zeros((4, 3), np.float32), params={"rate": rate}, frames=int(FPS * 3))
    assert rate <= flash_rates(frames, FPS).max() <= rate + 0.5


@pytest.mark.parametrize("cls", CANOPY_SET, ids=[pattern_name(c) for c in CANOPY_SET])
@pytest.mark.parametrize("units", ["pixel", "fixture"])
def test_nothing_flashes_faster_than_3_per_second(cls, units, example):
    """Photosensitive safety: 3-30 flashes per second is the common seizure
    range (Epilepsy Society, 2023), and WCAG 2.2 SC 2.3.1 allows no more
    than three in any second."""
    frames = render_sequence(
        cls, example.mapping, params=AGGRESSIVE[cls], seed=3, frames=int(FPS * SECONDS),
        fps=FPS, grouping=example.grouping, units=units,
    )
    worst = float(flash_rates(frames, FPS).max())
    assert worst <= FLASH_LIMIT, f"{pattern_name(cls)} ({units}): {worst} flashes in one second"


def test_aggressive_settings_are_range_endpoints():
    """Every numeric leaf set here (a float, or a color's s and v) sits at an
    end of its range. A periodic leaf (hue) has no end to sit at."""
    for cls, params in AGGRESSIVE.items():
        for record in ParamSet(cls).describe():
            if record["name"] not in params:
                continue
            for leaf, spec, _ in leaves(record):
                if spec["periodic"]:
                    continue
                part = leaf.partition(".")[2]
                value = params[record["name"]]
                assert (value[part] if part else value) in (spec["lo"], spec["hi"]), f"{pattern_name(cls)}.{leaf}"
