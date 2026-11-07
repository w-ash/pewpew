"""Lattice noise in 1 to 3 dimensions, octave sums, curl noise, domain
warping and cellular noise.

A noise is a function `fn(p, *, seed, period)` from a `Vec` of 1 to 3
axes to float32 in [-1, 1]. `value` and `gradient` are the two base
noises; the other functions take a noise as `fn` and build on it, so they
compose:

    warped = domain_warp(partial(fbm, gradient), (x * 3, y * 3), 0.4, seed=7)
    clouds = fbm(gradient, warped, octaves=5, seed=7)

The seed goes through an integer hash, so the same points and seed give the
same bytes and nothing reads a global RNG. Different seeds and different
octaves get independent lattices. Lattice coordinates are float32, so keep
a coordinate below about 1e5 (reduce time to a phase first). `period`
gives, per axis, a whole number of lattice units after which the lattice
repeats, or None for never: the hash takes each cell index modulo it, so
a phase wrapped at that period moves the field on with no jump.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Protocol

import numpy as np
import numpy.typing as npt

from pewpew.fx.prims.vec import F32, Vec, VecLike, vec

U32 = npt.NDArray[np.uint32]
I32 = npt.NDArray[np.int32]
# Per axis, the lattice units after which a noise repeats, or None for never.
Period = Sequence[int | None] | None


class Noise(Protocol):
    """A noise: points to float32, seeded by an int, repeating per axis
    after `period` lattice units."""

    def __call__(self, p: VecLike, /, *, seed: int = ..., period: Period = ...) -> F32: ...


_MASK = 0xFFFFFFFF

# The fewest float32 steps of a coordinate that a curl's difference step
# spans, so rounding the stepped coordinates moves a slope by at most about 3%.
_STEP_ULPS = 16

# One odd multiplier per axis (the xxHash32 primes) spreads a lattice cell
# over the 32-bit hash input before `_mix` avalanches it.
_PRIMES = (np.uint32(0x9E3779B1), np.uint32(0x85EBCA77), np.uint32(0xC2B2AE3D))


def _mix(h: U32) -> U32:
    """lowbias32, a 32-bit avalanche (Chris Wellons, "Prospecting for Hash
    Functions", 2018)."""
    h = h ^ (h >> np.uint32(16))
    h = h * np.uint32(0x7FEB352D)
    h = h ^ (h >> np.uint32(15))
    h = h * np.uint32(0x846CA68B)
    return h ^ (h >> np.uint32(16))


@lru_cache(maxsize=1024)
def _derive(seed: int, salt: int) -> int:
    """Return an independent seed for part `salt` (an octave, an axis) of a
    noise seeded by `seed`."""
    h = _mix(np.array([seed & _MASK], dtype=np.uint32)) ^ np.uint32(salt & _MASK)
    return int(_mix(h)[0])


@lru_cache(maxsize=256)
def _shift(seed: int, d: int) -> tuple[float, ...]:
    """A seeded offset in [0, 1) per axis. It moves the lattice off the
    integers, where a regular mapping's points can all fall and gradient
    noise is zero."""
    return tuple(_derive(seed, 0x5EED + a) / 2.0**32 for a in range(d))


def _unit(h: U32) -> F32:
    """The top 24 bits of a hash as float32 in [0, 1)."""
    return (h >> np.uint32(8)).astype(np.float32) * np.float32(2.0**-24)


def _periods(period: Period, d: int) -> tuple[int | None, ...]:
    """`period` for points of `d` axes, one entry per axis. Raises
    ValueError for another count or an entry that is not a whole number
    above 0."""
    if period is None:
        return (None,) * d
    reps = tuple(period)
    if len(reps) != d or not all(r is None or (isinstance(r, int) and r > 0) for r in reps):
        raise ValueError(f"period gives a whole number above 0, or None, for each of the {d} axes, got {period!r}")
    return reps


def _wrapped(i: I32, rep: int | None) -> U32:
    """Lattice indices `i` along one axis, wrapped every `rep` cells, as
    the uint32 the hash takes."""
    return (i if rep is None else i % rep).view(np.uint32)


def _fade(f: F32) -> F32:
    """Perlin's quintic 6f^5 - 15f^4 + 10f^3 ("Improving Noise", 2002)."""
    return f * f * f * (f * (f * 6.0 - 15.0) + 10.0)


# Per number of axes, per axis, which side of the cell each of the 2^d
# corners takes (0 low, 1 high), the corners in product order: the last
# axis varies fastest.
_SIDES = {d: tuple(np.array([(c >> (d - 1 - a)) & 1 for c in range(2**d)]) for a in range(d)) for d in (1, 2, 3)}


def _lattice(p: VecLike, seed: int, corner: Callable[[U32, Vec], F32], period: Period = None) -> F32:
    """Interpolate `corner(hash, offset)` over the 2^d corners of each
    point's lattice cell, with quintic weights. All corners go at once, a
    row each; each element takes the same operations it would alone."""
    q = vec(p)
    if not 1 <= len(q) <= 3:
        raise ValueError(f"noise takes points of 1 to 3 axes, got {len(q)}")
    reps = _periods(period, len(q))
    shape = np.broadcast_shapes(*(c.shape for c in q))
    q = tuple(
        (c + s if c.shape == shape else np.broadcast_to(c + s, shape)).reshape(-1)
        for c, s in zip(q, _shift(seed, len(q)))
    )
    cells = [np.floor(c) for c in q]
    frac = [c - f for c, f in zip(q, cells)]
    with np.errstate(over="ignore"):  # uint32 arithmetic wraps by design
        keys: U32 = np.full((), seed & _MASK, dtype=np.uint32)
        offsets: list[F32] = []
        for f, cell, prime, rep, side in zip(frac, cells, _PRIMES, reps, _SIDES[len(q)]):
            i = cell.astype(np.int32)
            keys = keys + np.array((_wrapped(i, rep) * prime, _wrapped(i + 1, rep) * prime))[side]
            offsets.append(np.array((f, f - 1.0))[side])
        values = corner(_mix(keys), tuple(offsets))
    for w in reversed([_fade(f) for f in frac]):
        values = values[0::2] + (values[1::2] - values[0::2]) * w
    return values[0].reshape(shape)


def value(p: VecLike, *, seed: int = 0, period: Period = None) -> F32:
    """Value noise: a random value at each lattice point, interpolated
    with quintic weights. Float32 in [-1, 1)."""
    return _lattice(p, seed, lambda h, _: _unit(h) * 2.0 - 1.0, period)


def _directions(d: int) -> tuple[F32, ...]:
    """16 gradient directions in d dimensions, one array per axis."""
    if d == 1:
        g = np.linspace(-1.0, 1.0, 16)[:, None]
    elif d == 2:
        a = (np.arange(16) + 0.5) * (2.0 * math.pi / 16)
        g = np.stack([np.cos(a), np.sin(a)], axis=1)
    else:  # Perlin's 12 cube-edge directions, 4 of them twice (Perlin 2002)
        e = [(1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0), (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1)]
        e += [(0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1), (1, 1, 0), (-1, 1, 0), (0, -1, 1), (0, -1, -1)]
        g = np.array(e) / math.sqrt(2.0)
    # Perlin noise with unit gradients stays within sqrt(d)/2: scale to [-1, 1].
    g = g * (2.0 / math.sqrt(d))
    return tuple(np.ascontiguousarray(g[:, a], dtype=np.float32) for a in range(d))


_GRADIENTS = {d: _directions(d) for d in (1, 2, 3)}


def _gradient_corner(h: U32, offset: Vec) -> F32:
    pick = h >> np.uint32(28)
    table = _GRADIENTS[len(offset)]
    out = table[0][pick] * offset[0]
    for g, o in zip(table[1:], offset[1:]):
        out = out + g[pick] * o
    return out


def gradient(p: VecLike, *, seed: int = 0, period: Period = None) -> F32:
    """Gradient (Perlin) noise: a random slope at each lattice point and
    zero on the lattice, which the seed shifts off the integers (Perlin,
    "Improving Noise", 2002). Float32 in [-1, 1]."""
    return _lattice(p, seed, _gradient_corner, period)


def _octaves(
    fn: Noise,
    p: VecLike,
    octaves: int,
    lacunarity: float,
    gain: float,
    seed: int,
    shape: Callable[[F32], F32],
    period: Period,
) -> F32:
    """Sum `shape(fn)` over octaves of rising frequency and falling
    amplitude, divided by the sum of the amplitudes. With a `period`, each
    octave's lattice repeats where the first's does, which takes a whole
    `lacunarity`."""
    if octaves < 1:
        raise ValueError(f"octaves must be 1 or more, got {octaves}")
    lacunarity, gain = float(lacunarity), float(gain)
    if period is not None and octaves > 1 and not lacunarity.is_integer():
        raise ValueError(f"a periodic octave sum takes a whole lacunarity, got {lacunarity}")
    q = vec(p)
    total = shape(fn(q, seed=_derive(seed, 0), period=period))
    amp, freq, norm = 1.0, 1.0, 1.0
    for octave in range(1, octaves):
        amp, freq = amp * gain, freq * lacunarity
        norm += abs(amp)
        reps = None if period is None else [None if r is None else r * int(freq) for r in period]
        total = total + amp * shape(fn(tuple(c * freq for c in q), seed=_derive(seed, octave), period=reps))
    return total / norm


def fbm(
    fn: Noise, p: VecLike, octaves: int = 4, lacunarity: float = 2.0, gain: float = 0.5, *, seed: int = 0,
    period: Period = None,
) -> F32:
    """Fractal Brownian motion: sum of a^k fn(L^k p) for gain a and
    lacunarity L, normalized to the range of `fn`."""
    return _octaves(fn, p, octaves, lacunarity, gain, seed, lambda n: n, period)


def turbulence(
    fn: Noise, p: VecLike, octaves: int = 4, lacunarity: float = 2.0, gain: float = 0.5, *, seed: int = 0,
    period: Period = None,
) -> F32:
    """Perlin's turbulence: fbm of |fn|, with creases where `fn` crosses
    zero. Float32 in [0, 1]."""
    return _octaves(fn, p, octaves, lacunarity, gain, seed, np.abs, period)


def _ridge(n: F32) -> F32:
    r = 1.0 - np.abs(n)
    return r * r


def ridged(
    fn: Noise, p: VecLike, octaves: int = 4, lacunarity: float = 2.0, gain: float = 0.5, *, seed: int = 0,
    period: Period = None,
) -> F32:
    """Ridged noise: fbm of (1 - |fn|)^2, with sharp ridges where `fn`
    crosses zero (after Musgrave's ridged multifractal). Float32 in [0, 1]."""
    return _octaves(fn, p, octaves, lacunarity, gain, seed, _ridge, period)


def _slope(fn: Noise, q: Vec, axis: int, seed: int, eps: float) -> F32:
    """d fn / d axis, by central difference over a step of `eps`. Where
    float32 cannot resolve that step (a coordinate above about 1000), the
    step widens to _STEP_ULPS float32 steps of the coordinate."""
    c = q[axis]
    h = np.maximum(np.float32(eps), np.spacing(np.abs(c)) * np.float32(_STEP_ULPS))
    hi, lo = list(q), list(q)
    hi[axis], lo[axis] = c + h, c - h
    return (fn(tuple(hi), seed=seed) - fn(tuple(lo), seed=seed)) / (h + h)


def curl2(fn: Noise, p: VecLike, *, seed: int = 0, eps: float = 1e-3) -> Vec:
    """A divergence-free 2D flow: the curl (d psi/dy, -d psi/dx) of the
    stream function psi = fn(p) (Bridson et al., "Curl-Noise for Procedural
    Fluid Flow", 2007). Axes after the first two (for example time) reach
    `fn` unchanged."""
    q = vec(p)
    if len(q) < 2:
        raise ValueError(f"curl2 takes points of 2 or 3 axes, got {len(q)}")
    return _slope(fn, q, 1, seed, eps), -_slope(fn, q, 0, seed, eps)


def curl3(fn: Noise, p: VecLike, *, seed: int = 0, eps: float = 1e-3) -> Vec:
    """A divergence-free 3D flow: the curl of the vector potential whose
    three components are `fn` with three independent seeds (Bridson et al.
    2007). Costs 12 evaluations of `fn`."""
    q = vec(p)
    if len(q) != 3:
        raise ValueError(f"curl3 takes points of 3 axes, got {len(q)}")
    s1, s2, s3 = (_derive(seed, i) for i in range(3))

    def d(axis: int, s: int) -> F32:
        return _slope(fn, q, axis, s, eps)

    return d(1, s3) - d(2, s2), d(2, s1) - d(0, s3), d(0, s2) - d(1, s1)


def domain_warp(fn: Noise, p: VecLike, amount: float = 1.0, *, seed: int = 0) -> Vec:
    """Return p + amount * (fn(p) per axis, each with its own seed): the
    points to sample a field at for Inigo Quilez's domain warping
    (iquilezles.org/articles/warp). Warp the result again for his
    two-level look."""
    q, amount = vec(p), float(amount)
    return tuple(c + amount * fn(q, seed=_derive(seed, a)) for a, c in enumerate(q))


# One salt per axis for a feature point's offset in its cell.
_JITTER = tuple(np.uint32(0x68E31DA4 + 0x1B56C4E9 * a) for a in range(3))


def cellular(p: VecLike, *, seed: int = 0, period: Period = None) -> tuple[F32, F32]:
    """Cellular (Worley) noise: the distances from each point to the
    nearest and the second-nearest feature point, one point per lattice
    cell at a seeded spot inside it (Worley, "A Cellular Texture Basis
    Function", 1996). Float32 (f1, f2), each at least 0, f1 <= f2. On a
    unit lattice f1 stays below about sqrt(d) for d axes, and f2 - f1 is 0
    on a border between two cells."""
    q = vec(p)
    if not 1 <= len(q) <= 3:
        raise ValueError(f"cellular takes points of 1 to 3 axes, got {len(q)}")
    reps = _periods(period, len(q))
    shape = np.broadcast_shapes(*(c.shape for c in q))
    points = [np.broadcast_to(c, shape).reshape(1, -1) for c in q]  # (1, M) per axis
    # Every point's own cell and its neighbours at once: (3**d, M) per axis.
    offsets = np.array(list(itertools.product((-1.0, 0.0, 1.0), repeat=len(q))), dtype=np.float32)
    cells = [np.floor(c) + offsets[:, a, None] for a, c in enumerate(points)]
    with np.errstate(over="ignore"):  # uint32 arithmetic wraps by design
        key: U32 = np.full(1, seed & _MASK, dtype=np.uint32)
        for cell, prime, rep in zip(cells, _PRIMES, reps):
            key = key + _wrapped(cell.astype(np.int32), rep) * prime
        h = _mix(key)
        d2 = np.zeros_like(cells[0])
        for cell, c, salt in zip(cells, points, _JITTER):
            delta = cell + _unit(_mix(h ^ salt)) - c
            d2 = d2 + delta * delta
    nearest = np.partition(d2, 1, axis=0)
    return np.sqrt(nearest[0]).reshape(shape), np.sqrt(nearest[1]).reshape(shape)
