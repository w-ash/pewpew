"""Tests for the noise primitives (src/pewpew/fx/prims/noise.py): range,
float32, determinism, smoothness, and the curl's zero divergence."""

from __future__ import annotations

from functools import partial

import numpy as np
import pytest

from pewpew.fx.prims import noise
from pewpew.fx.prims.noise import curl2, curl3, domain_warp, fbm, gradient, ridged, turbulence, value
from pewpew.metrics import LIVENESS_RMS, rms

BASES = [pytest.param(value, id="value"), pytest.param(gradient, id="gradient")]


def _points(d: int, n: int = 4000, spread: float = 40.0, seed: int = 0) -> tuple[np.ndarray, ...]:
    rng = np.random.default_rng(seed)
    return tuple(rng.uniform(-spread, spread, n).astype(np.float32) for _ in range(d))


@pytest.mark.parametrize("fn", BASES)
@pytest.mark.parametrize("d", [1, 2, 3])
def test_base_noise_is_float32_within_minus_one_to_one(fn, d: int) -> None:
    out = fn(_points(d), seed=5)
    assert out.dtype == np.float32
    assert out.shape == (4000,)
    assert np.all(np.abs(out) <= 1.0)
    assert out.std() > 0.1  # a noise, not a constant


@pytest.mark.parametrize("fn", BASES)
def test_same_seed_gives_same_bytes_and_seeds_differ(fn) -> None:
    p = _points(3)
    assert fn(p, seed=3).tobytes() == fn(p, seed=3).tobytes()
    assert rms(fn(p, seed=3), fn(p, seed=4)) > LIVENESS_RMS


@pytest.mark.parametrize("fn", BASES)
@pytest.mark.parametrize("d", [1, 2, 3])
def test_noise_is_smooth(fn, d: int) -> None:
    """A step of h moves the noise by less than a few h: the quintic fade
    keeps the slope bounded across lattice cells."""
    p = _points(d, spread=8.0)
    h = 1e-3
    moved = fn(tuple(c + np.float32(h) for c in p), seed=1)
    assert np.max(np.abs(moved - fn(p, seed=1))) < 8 * d * h


def test_gradient_noise_is_not_zero_on_a_regular_grid() -> None:
    """Points on whole numbers sit on an unshifted lattice, where gradient
    noise is zero; the seed shifts the lattice off them."""
    i = np.arange(16, dtype=np.float32)
    xs, ys = np.meshgrid(i, i)
    assert np.abs(gradient((xs.ravel(), ys.ravel()), seed=0)).mean() > 0.1


def test_scalar_axis_broadcasts() -> None:
    x = np.linspace(0, 4, 50, dtype=np.float32)
    out = gradient((x, x, 2.5), seed=2)
    assert out.shape == (50,)
    assert out.tobytes() == gradient((x, x, np.full(50, 2.5, np.float32)), seed=2).tobytes()


@pytest.mark.parametrize(
    "fn, lo, hi",
    [(fbm, -1.0, 1.0), (turbulence, 0.0, 1.0), (ridged, 0.0, 1.0)],
    ids=["fbm", "turbulence", "ridged"],
)
def test_octave_sums_keep_their_range(fn, lo: float, hi: float) -> None:
    for octaves in (1, 3, 6):
        out = fn(gradient, _points(2), octaves=octaves, seed=9)
        assert out.dtype == np.float32
        assert lo <= out.min() and out.max() <= hi


def test_octaves_add_detail() -> None:
    p = _points(2, spread=4.0)
    one, five = fbm(gradient, p, octaves=1), fbm(gradient, p, octaves=5)
    assert rms(one, five) > LIVENESS_RMS


def _divergence(field, p: tuple[np.ndarray, ...], h: float = 1e-2) -> tuple[np.ndarray, np.ndarray]:
    """The divergence of `field` at `p`, and the sum of the sizes of its
    terms, by central differences in float64."""
    div = np.zeros(len(p[0]))
    size = np.zeros(len(p[0]))
    for a in range(len(p)):
        hi = [c.astype(np.float64) for c in p]
        lo = [c.astype(np.float64) for c in p]
        hi[a] += h
        lo[a] -= h
        term = (field(tuple(hi))[a].astype(np.float64) - field(tuple(lo))[a]) / (2 * h)
        div += term
        size += np.abs(term)
    return div, size


@pytest.mark.parametrize("curl, d", [(curl2, 2), (curl3, 3)], ids=["curl2", "curl3"])
def test_curl_is_divergence_free(curl, d: int) -> None:
    flow = partial(curl, partial(fbm, gradient, octaves=2), seed=4)
    div, size = _divergence(flow, _points(d, n=500, spread=3.0))
    assert np.abs(div).mean() < 0.02 * size.mean()


def test_curl_is_float32_per_axis() -> None:
    vx, vy = curl2(gradient, _points(2))
    assert vx.dtype == vy.dtype == np.float32
    assert all(c.dtype == np.float32 for c in curl3(value, _points(3)))


def test_curl2_passes_time_through_to_the_noise() -> None:
    x, y = _points(2)
    early, late = curl2(gradient, (x, y, 0.0)), curl2(gradient, (x, y, 0.5))
    assert rms(early[0], late[0]) > LIVENESS_RMS


def _mean_speeds(curl, offset: float) -> np.ndarray:
    """The mean size of each component of `curl` over 16 x 16 lattice cells
    whose x starts at `offset`."""
    g = np.linspace(0.0, 16.0, 64)
    xs, ys = (c.ravel() for c in np.meshgrid(g, g))
    p = ((xs + offset).astype(np.float32), ys.astype(np.float32), np.full(xs.size, 5.0, np.float32))
    return np.array([np.abs(c).mean() for c in curl(gradient, p[: 2 if curl is curl2 else 3], seed=1)])


@pytest.mark.parametrize("offset", [20000.0, 40000.0, 90000.0])
@pytest.mark.parametrize("curl", [curl2, curl3], ids=["curl2", "curl3"])
def test_curl_keeps_its_size_far_from_the_origin(curl, offset: float) -> None:
    """A step of 1e-3 rounds to twice its size past 2^14 and to nothing past
    2^15 in float32, which doubled or stopped the flow."""
    assert np.allclose(_mean_speeds(curl, offset), _mean_speeds(curl, 10.0), rtol=0.15)


def test_domain_warp_moves_each_axis_by_at_most_amount() -> None:
    p = _points(3, spread=2.0)
    warped = domain_warp(partial(fbm, gradient), p, 0.3, seed=1)
    for before, after in zip(p, warped):
        assert after.dtype == np.float32
        assert np.max(np.abs(after - before)) <= 0.3 + 1e-6
    assert warped[0].tobytes() != warped[1].tobytes()  # each axis has its own seed


def test_refusals_name_the_fix() -> None:
    with pytest.raises(ValueError, match="1 to 3 axes, got 4"):
        value(_points(4))
    with pytest.raises(ValueError, match="octaves must be 1 or more, got 0"):
        fbm(value, _points(1), octaves=0)
    with pytest.raises(ValueError, match="curl2 takes points of 2 or 3 axes, got 1"):
        curl2(value, _points(1))
    with pytest.raises(ValueError, match="curl3 takes points of 3 axes, got 2"):
        curl3(value, _points(2))
    with pytest.raises(TypeError, match=r"points must be one array per axis, such as \(x, y\), got one array"):
        value(np.zeros((3, 3), np.float32))  # type: ignore[arg-type]  # on purpose


def test_a_noise_partial_is_a_noise() -> None:
    """`partial(fbm, gradient, ...)` takes the place of a base noise."""
    fn: noise.Noise = partial(fbm, gradient, octaves=3)
    assert fn(_points(2), seed=1).dtype == np.float32


@pytest.mark.parametrize("d", [1, 2, 3])
def test_cellular_gives_the_two_nearest_distances_in_float32(d: int) -> None:
    p = _points(d, n=2000, spread=8.0)
    f1, f2 = noise.cellular(p, seed=4)
    assert f1.dtype == f2.dtype == np.float32 and f1.shape == f2.shape == (2000,)
    assert np.all(f1 >= 0.0) and np.all(f1 <= f2)
    assert f1.max() < np.sqrt(d) and f1.std() > 0.05
    assert f1.tobytes() == noise.cellular(p, seed=4)[0].tobytes()
    assert rms(f1, noise.cellular(p, seed=5)[0]) > LIVENESS_RMS


def test_cellular_is_zero_at_a_feature_point_and_continuous() -> None:
    """f1 is a distance field: it changes no faster than the points move."""
    x = np.linspace(0.0, 6.0, 6001, dtype=np.float32)
    f1, f2 = noise.cellular((x, np.full_like(x, 0.3)), seed=1)
    assert np.all(np.abs(np.diff(f1)) <= 1.001e-3 + 1e-6)
    assert f1.min() < 0.05 and (f2 - f1).min() < 1e-2  # it passes near a point and across a border


PERIODIC = [
    pytest.param(value, 1e-4, id="value"),
    pytest.param(gradient, 1e-4, id="gradient"),
    pytest.param(partial(fbm, gradient, octaves=4), 1e-3, id="fbm"),
    pytest.param(partial(ridged, value, octaves=3), 1e-3, id="ridged"),
    pytest.param(lambda p, **kw: noise.cellular(p, **kw)[0], 1e-4, id="cellular"),
]


@pytest.mark.parametrize("fn, tol", PERIODIC)
@pytest.mark.parametrize("d", [1, 2, 3])
def test_a_periodic_noise_repeats_along_its_periodic_axis_only(fn, tol: float, d: int) -> None:
    """With `period`, a phase that wraps by the period along that axis gives
    the same field: Perlin's periodic noise. The other axes do not repeat."""
    p = _points(d, n=1000, spread=8.0)
    period = [None] * (d - 1) + [64]
    moved = (*p[:-1], p[-1] + np.float32(64.0))
    np.testing.assert_allclose(fn(moved, seed=3, period=period), fn(p, seed=3, period=period), atol=tol)
    assert rms(fn(moved, seed=3), fn(p, seed=3)) > LIVENESS_RMS, "without a period it does not repeat"
    if d > 1:
        aside = (p[0] + np.float32(64.0), *p[1:])
        assert rms(fn(aside, seed=3, period=period), fn(p, seed=3, period=period)) > LIVENESS_RMS


def test_a_period_is_refused_unless_whole_per_axis() -> None:
    for bad in ([64], [64, 0], [64, 2.5]):
        with pytest.raises(ValueError, match="period gives a whole number above 0, or None, for each of the 2 axes"):
            gradient(_points(2), period=bad)
    with pytest.raises(ValueError, match="a periodic octave sum takes a whole lacunarity, got 2.1"):
        fbm(gradient, _points(2), lacunarity=2.1, period=[None, 64])
