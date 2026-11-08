"""Golden outputs of the fx primitives (src/pewpew/fx/prims/) at fixed
seeds on the study fixtures: a regression tripwire for any change to what a
primitive returns. Every output is float32 (or int32 for neighbour indexes)
and the same bytes on every run.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from functools import partial
from pathlib import Path

import numpy as np
import pytest

from pewpew.fx.prims import grid, knn, noise, sample, sdf, space
from pewpew.mapping import grid as panel
from pewpew.mapping import lattice, line
from pewpew.testing.goldens import assert_matches_golden

GOLDEN = Path(__file__).parent / "goldens" / "prims.npz"

STRIP = tuple(line(64).T)
PANEL = tuple(panel(16, 16).T)
CUBE = tuple(lattice(6).T)


def _scaled(p, s: float):
    return tuple(c * np.float32(s) for c in p)


def _gray_scott() -> np.ndarray:
    nbrs = knn.neighbors(lattice(6), 6)
    a, b = np.ones(216, np.float32), np.zeros(216, np.float32)
    b[[100, 101, 106, 107]] = 1.0
    for _ in range(80):
        a, b = knn.gray_scott_step(a, b, nbrs)
    return b


def _wave() -> np.ndarray:
    nbrs = knn.neighbors(panel(16, 16), 4)
    u = np.zeros(256, np.float32)
    u[136] = 1.0
    prev = u.copy()
    for _ in range(20):
        u, prev = knn.wave_step(u, prev, nbrs, 1.0, 0.02), u
    return u


def _advected() -> np.ndarray:
    field = noise.gradient(np.meshgrid(*(np.linspace(0, 3, 24, dtype=np.float32),) * 2), seed=2)
    vx, vy = noise.curl2(noise.gradient, np.meshgrid(*(np.linspace(0, 2, 24, dtype=np.float32),) * 2), seed=3)
    for _ in range(3):
        field = sample.advect(field, (vx * 0.02, vy * 0.02), 1.0, "wrap")
    return field


FBM = partial(noise.fbm, noise.gradient, octaves=3)

CASES: dict[str, Callable[[], np.ndarray]] = {
    "value_strip": lambda: noise.value(_scaled(STRIP[:1], 8.0), seed=1),
    "value_panel": lambda: noise.value(_scaled(PANEL[:2], 4.0), seed=1),
    "gradient_panel": lambda: noise.gradient(_scaled(PANEL[:2], 4.0), seed=1),
    "gradient_cube": lambda: noise.gradient(_scaled(CUBE, 3.0), seed=1),
    "fbm_panel": lambda: noise.fbm(noise.gradient, _scaled(PANEL[:2], 3.0), octaves=5, seed=2),
    "ridged_panel": lambda: noise.ridged(noise.value, _scaled(PANEL[:2], 3.0), seed=2),
    "turbulence_cube": lambda: noise.turbulence(noise.gradient, _scaled(CUBE, 2.0), seed=2),
    "curl2_panel": lambda: np.stack(noise.curl2(FBM, _scaled(PANEL[:2], 2.0), seed=3)),
    "curl3_cube": lambda: np.stack(noise.curl3(noise.gradient, _scaled(CUBE, 2.0), seed=3)),
    "warp_panel": lambda: noise.fbm(noise.gradient, noise.domain_warp(FBM, _scaled(PANEL[:2], 3.0), 0.5, seed=4)),
    "kaleid_panel": lambda: np.stack(space.kaleid(PANEL, 5)),
    "twist_cube": lambda: np.stack(space.twist(CUBE, 3.0)),
    "tunnel_panel": lambda: np.stack(space.tunnel(PANEL)),
    "rotate_about_cube": lambda: np.stack(space.rotate_about(CUBE, 0.7, (1.0, 2.0, 0.5))),
    "bilinear_panel": lambda: sample.sample(np.arange(20, dtype=np.float32).reshape(4, 5), _scaled(PANEL[:2], 1.3)),
    "spherical_cube": lambda: np.stack(sample.spherical(CUBE)),
    "advect_wrap": _advected,
    "sdf_scene": lambda: sdf.onion(
        sdf.subtract(
            sdf.union(sdf.torus(space.twist(CUBE, 2.0), 0.3, 0.08), sdf.sphere(CUBE, 0.2), 0.1), sdf.box(CUBE, 0.12)
        ),
        0.02,
    ),
    "deposit_cube": lambda: grid.deposit(_scaled(CUBE, 0.9), np.linspace(0, 1, 216, dtype=np.float32), (5, 5, 5)),
    "knn_idx": lambda: knn.neighbors(lattice(6), 6).idx,
    "knn_dist": lambda: knn.neighbors(lattice(6), 6).dist,
    "gray_scott_b": _gray_scott,
    "wave_panel": _wave,
}


def test_prims_match_golden(regen_goldens: bool) -> None:
    arrays = {name: make() for name, make in CASES.items()}
    for name, array in arrays.items():
        assert array.dtype == (np.int32 if name == "knn_idx" else np.float32), name
    assert_matches_golden(GOLDEN, arrays, regen=regen_goldens)


@pytest.mark.parametrize("name", list(CASES))
def test_prims_are_deterministic(name: str) -> None:
    assert CASES[name]().tobytes() == CASES[name]().tobytes()


def test_numpy_floor_keeps_scalar_math_in_float32() -> None:
    """The prims stay float32 through NumPy 2's promotion (NEP 50). NumPy 1
    turns a float32 scalar times a Python float into float64, so the floor
    must be NumPy 2."""
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]
    (floor,) = [dep.removeprefix("numpy>=") for dep in project["dependencies"] if dep.startswith("numpy")]
    assert int(floor.split(".")[0]) >= 2
    assert space.rotate((np.float32(0.3), np.float32(0.7)), 1.0)[0].dtype == np.float32
    assert sdf.sphere((0.3, 0.7, 0.1), 0.2).dtype == np.float32


def _f64(value):
    """`value` with every number a NumPy float64 scalar, as `vec.wave` and `np.mean` return."""
    return tuple(map(np.float64, value)) if isinstance(value, tuple) else np.float64(value)


# Each prim called with every scalar argument given: called with float64s it must give the same bytes.
SCALAR_ARGS: dict[str, tuple[Callable[..., object], dict[str, object]]] = {
    "translate": (lambda **a: space.translate(CUBE, **a), {"offset": (0.1, 0.2, 0.3)}),
    "scale": (lambda **a: space.scale(CUBE, **a), {"factor": 1.5, "center": (0.4, 0.5, 0.6)}),
    "rotate": (lambda **a: space.rotate(CUBE, **a), {"angle": 0.7, "center": (0.4, 0.5, 0.6)}),
    "rotate_about": (lambda **a: space.rotate_about(CUBE, **a), {"angle": 0.7, "axis": (1.0, 2.0, 0.5),
                                                                 "center": (0.4, 0.5, 0.6)}),
    "polar": (lambda **a: space.polar(CUBE, **a), {"center": (0.4, 0.5, 0.6)}),
    "cartesian": (lambda **a: space.cartesian(CUBE, **a), {"center": (0.4, 0.5, 0.6)}),
    "kaleid": (lambda **a: space.kaleid(CUBE, 5, **a), {"center": (0.4, 0.5, 0.6)}),
    "mirror": (lambda **a: space.mirror(CUBE, "xz", **a), {"center": (0.4, 0.5, 0.6)}),
    "twist": (lambda **a: space.twist(CUBE, **a), {"rate": 0.7, "center": (0.4, 0.5, 0.6)}),
    "tunnel": (lambda **a: space.tunnel(CUBE, **a), {"center": (0.4, 0.5, 0.6), "radius": 0.01}),
    "repeat": (lambda **a: space.repeat(CUBE, **a), {"period": 0.3, "center": (0.4, 0.5, 0.6)}),
    "sphere": (lambda **a: sdf.sphere(CUBE, **a), {"radius": 0.2, "center": (0.4, 0.5, 0.6)}),
    "box": (lambda **a: sdf.box(CUBE, **a), {"half": (0.1, 0.2, 0.3), "center": (0.4, 0.5, 0.6)}),
    "torus": (lambda **a: sdf.torus(CUBE, **a), {"major": 0.3, "minor": 0.1, "center": (0.4, 0.5, 0.6)}),
    "capsule": (lambda **a: sdf.capsule(CUBE, **a), {"a": (0.2, 0.1, 0.3), "b": (0.7, 0.8, 0.6), "radius": 0.1}),
    "halfspace": (lambda **a: sdf.halfspace(CUBE, **a), {"normal": (0.0, 2.0, 1.0), "center": (0.4, 0.5, 0.6)}),
    "smooth_union": (lambda **a: sdf.union(sdf.sphere(CUBE, 0.2), sdf.box(CUBE, 0.12), **a), {"k": 0.1}),
    "rounded": (lambda **a: sdf.rounded(sdf.box(CUBE, 0.12), **a), {"radius": 0.05}),
    "spherical": (lambda **a: sample.spherical(CUBE, **a), {"center": (0.4, 0.5, 0.6)}),
    "cylindrical": (lambda **a: sample.cylindrical(CUBE, **a), {"center": (0.4, 0.5, 0.6)}),
    "advect": (lambda **a: sample.advect(np.ones((6, 6), np.float32), (0.1, 0.2), **a), {"dt": 0.5}),
    "fbm": (lambda **a: noise.fbm(noise.gradient, PANEL[:2], **a), {"lacunarity": 2.1, "gain": 0.6}),
    "domain_warp": (lambda **a: noise.domain_warp(noise.value, PANEL[:2], **a), {"amount": 0.4}),
}


@pytest.mark.parametrize("name", list(SCALAR_ARGS))
def test_a_numpy_float64_argument_keeps_a_prim_float32(name: str) -> None:
    """`vec.wave`, `np.sin(t)` and `np.mean` give NumPy float64 scalars, which
    are not weak under NEP 50: a prim takes each scalar as a Python float,
    so its result is float32 and the same bytes as with Python floats."""
    prim, args = SCALAR_ARGS[name]
    want, got = prim(**args), prim(**{key: _f64(value) for key, value in args.items()})
    for w, g in zip(np.broadcast_arrays(*want) if isinstance(want, tuple) else (want,),
                    np.broadcast_arrays(*got) if isinstance(got, tuple) else (got,), strict=True):
        w, g = np.asarray(w), np.asarray(g)
        assert g.dtype == np.float32 and g.tobytes() == w.tobytes()
