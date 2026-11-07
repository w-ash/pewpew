"""The warpable contract (ADR-005 amendment 2026-11-05): a pattern with
`warpable = True` renders a correct frame when `render` gets any finite
coordinates other than the ones `setup` saw, values far outside 0-1 included.
`index` is the stable identity and is never warped.

No engine seam warps coordinates yet (ADR-022 adds coordinate ops), so each
test subclasses the pattern and warps the coordinates on their way into
`render`. `setup` sees the mapping, as it does under a coordinate op.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest

from pewpew import Pattern, Renderer, hsv, lattice, line
from pewpew.classinfo import pattern_name
from pewpew.patterns import STUDY_CASES, Comet

Coords = tuple[np.ndarray, np.ndarray, np.ndarray]
# x, y, z and the engine time in seconds -> the coordinates `render` gets.
Warp = Callable[[np.ndarray, np.ndarray, np.ndarray, float], Coords]

FPS = 60.0
FRAMES = 30
SEED = 42
MAPPING = lattice(5)  # 125 points that span all three axes


def _translate(x, y, z, t) -> Coords:
    """Drift past 1 on x and below 0 on y."""
    return x + 1.25 + 2.0 * t, y - 0.75 - t, z + 0.5


def _scale(x, y, z, t) -> Coords:
    """Zoom out about the centre by 2 to 5 times."""
    k = 3.5 + 1.5 * math.sin(6.0 * t)
    return 0.5 + k * (x - 0.5), 0.5 + k * (y - 0.5), 0.5 + k * (z - 0.5)


def _rotate(x, y, z, t) -> Coords:
    """Turn about the centre in the xy plane, then in the xz plane."""
    a, b = 0.6 + 3.0 * t, 0.4 - 2.0 * t
    px, py, pz = x - 0.5, y - 0.5, z - 0.5
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return 0.5 + rx * math.cos(b) - pz * math.sin(b), 0.5 + ry, 0.5 + rx * math.sin(b) + pz * math.cos(b)


def _far(x, y, z, t) -> Coords:
    """Fling the points out past +-2e9, beyond what an int32 holds."""
    k = 4e9 * (1.0 + t)
    return k * (x - 0.5), k * (y - 0.5), k * (z - 0.5)


WARPS = [
    pytest.param(_translate, id="translate"),
    pytest.param(_scale, id="scale"),
    pytest.param(_rotate, id="rotate"),
    pytest.param(_far, id="far"),
]
WARPABLE = [cls for cls, *_ in STUDY_CASES if cls.warpable]
# Comet keeps its `setup` x as the spark key on purpose (§8), so a still
# warp moves its head but not its sparks.
KEYED_IN_SETUP = (Comet,)


def _none(x, y, z, t) -> Coords:
    """No warp."""
    return x, y, z


def _held(warp: Warp) -> Warp:
    """`warp` frozen at its t = 0 shape."""
    return lambda x, y, z, t: warp(x, y, z, 0.0)


def _warped(cls: type[Pattern], warp: Warp) -> Pattern:
    """A `cls` whose `render` gets the coordinates `warp` makes."""

    class Warped(cls):
        warp_t = 0.0  # engine time, summed from dt

        def before_render(self, dt, features):
            super().before_render(dt, features)
            self.warp_t += dt

        def render(self, x, y, z, index):
            coords = [np.asarray(c, dtype=np.float32) for c in warp(x, y, z, self.warp_t)]
            for c in coords:
                c.setflags(write=False)  # read-only, as the engine hands coordinates over
            return super().render(*coords, index)  # type: ignore[call-arg]  # coords is (x, y, z)

    return Warped()


def _render(
    cls: type[Pattern], mapping: np.ndarray, warp: Warp, *, frames: int = FRAMES, params: dict | None = None
) -> np.ndarray:
    """`frames` frames of `cls` under `warp`. Fails on an error the engine contained."""
    renderer = Renderer(_warped(cls, warp), mapping, seed=SEED, params=params, name=pattern_name(cls))
    out = []
    for _ in range(frames):
        out.append(renderer.step(1.0 / FPS))
        assert renderer.error is None, f"{renderer.error} under the warp"
    return np.stack(out)


def test_warpable_is_opt_in_and_the_whole_gallery_has_opted_in() -> None:
    """A pattern is not warpable until it says so. The 2026-11 audit cleared
    every gallery pattern; one that is not warpable is named here with why."""

    class Plain(Pattern):
        pass

    assert Pattern.warpable is False and Plain.warpable is False
    assert [pattern_name(cls) for cls, *_ in STUDY_CASES if not cls.warpable] == []


@pytest.mark.parametrize("warp", WARPS)
def test_each_warp_leaves_the_unit_cube(warp: Warp) -> None:
    x, y, z = MAPPING.T
    reach = np.stack([np.stack(warp(x, y, z, k / FPS)) for k in range(1, FRAMES + 1)])
    assert reach.min() < 0.0 and reach.max() > 1.0


@pytest.mark.parametrize("warp", WARPS)
@pytest.mark.parametrize("cls", WARPABLE, ids=pattern_name)
def test_a_warpable_pattern_renders_a_valid_frame_under_a_moving_warp(cls: type[Pattern], warp: Warp) -> None:
    frames = _render(cls, MAPPING, warp)
    assert frames.dtype == np.float32
    assert np.isfinite(frames).all()
    assert frames.min() >= 0.0 and frames.max() <= 1.0
    assert _render(cls, MAPPING, warp).tobytes() == frames.tobytes(), "the same warp rendered different bytes"


def _still_warp_renders_the_warped_mapping(cls: type[Pattern], warp: Warp) -> bool:
    """True if `cls` under `warp` held at t = 0 renders the bytes it renders
    when bound on the mapping that warp makes, so `render` reads the geometry
    from its coordinates and not from `setup`."""
    moved = np.stack(warp(*MAPPING.T, 0.0), axis=1).astype(np.float32)  # type: ignore[call-arg]  # x, y, z
    return _render(cls, MAPPING, _held(warp)).tobytes() == _render(cls, moved, _none).tobytes()


@pytest.mark.parametrize("warp", WARPS)
@pytest.mark.parametrize("cls", [c for c in WARPABLE if c not in KEYED_IN_SETUP], ids=pattern_name)
def test_a_warpable_pattern_takes_its_geometry_from_render(cls: type[Pattern], warp: Warp) -> None:
    assert _still_warp_renders_the_warped_mapping(cls, warp)


class _Rings(Pattern):
    """Hue by distance from the centre, computed in `render`."""

    def render(self, x, y, z, index):
        return hsv(np.hypot(x - 0.5, y - 0.5), 1.0, 1.0)


class _CachedRings(_Rings):
    """`_Rings` with the distance computed in `setup`: the first bug §8 names."""

    def setup(self, n, x, y, z, index):
        self.r = np.hypot(x - 0.5, y - 0.5)

    def render(self, x, y, z, index):
        return hsv(self.r, 1.0, 1.0)


@pytest.mark.parametrize("warp", WARPS)
def test_the_geometry_check_catches_a_distance_kept_from_setup(warp: Warp) -> None:
    """`_CachedRings` renders valid, deterministic frames under every warp,
    but they show the unwarped rings. This check is the one that sees it."""
    assert _still_warp_renders_the_warped_mapping(_Rings, warp)
    assert not _still_warp_renders_the_warped_mapping(_CachedRings, warp)


# ---- comet: sparks keyed on identity, and a wrap that holds outside 0-1 -------


def _away_from_the_head(warp: Warp) -> Warp:
    """`warp` folded into 0.25..0.75 on x, clear of a head parked at x = 0."""

    def folded(x, y, z, t) -> Coords:
        wx, wy, wz = warp(x, y, z, t)
        return 0.25 + 0.5 * (wx % 1.0), wy, wz

    return folded


@pytest.mark.parametrize("warp", WARPS)
def test_comet_sparks_do_not_crawl_under_a_moving_warp(warp: Warp) -> None:
    """Sparks hash an identity key, so a moving warp shows the sparks a still
    one does. Hashed on the warped x, each frame drew new random pixels: 6 to
    19 times as many sparks here.

    The head is parked at x = 0, the warp keeps every point clear of it, and
    the trail dies within a frame or two, so a red rise of 0.25 or more is the
    start of a spark (each adds 0.3) and nothing else."""
    parked = {"speed": 0.0, "tail": 0.01}
    mapping = line(300)
    warp = _away_from_the_head(warp)

    def sparks(w: Warp) -> int:
        red = _render(Comet, mapping, w, frames=120, params=parked)[:, :, 0]
        return int((np.diff(red, axis=0) >= 0.25).sum())

    still, moving = sparks(_held(warp)), sparks(warp)
    assert still >= 10, f"only {still} sparks: the test would not see a crawl"
    assert abs(moving - still) <= 0.1 * still, f"{moving} sparks under a moving warp, {still} under a still one"


@pytest.mark.parametrize("shift", [-2.0, 3.0])
def test_comet_wraps_coordinates_outside_0_1(shift: float) -> None:
    """The head's distance wraps at 1, so a whole-unit shift lights as much
    of the strip as no shift: about 4% at full red, the head's core. Without
    the `% 1.0` the distance went negative there and lit all of it."""
    mapping = line(64)

    def core(warp: Warp) -> float:
        return float((_render(Comet, mapping, warp)[:, :, 0] >= 0.999).mean())

    still = core(_none)
    assert 0.0 < still < 0.1
    assert core(lambda x, y, z, t: (x + shift, y, z)) == pytest.approx(still, abs=0.01)
