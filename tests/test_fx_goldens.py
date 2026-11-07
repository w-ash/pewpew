"""Stored frames of effect programs, and the ADR-022 key derivations as
literals. The other fx tests compare a process with itself, so a change to
an op's math, to the host, to signals and routes, or to how a node's key,
seed and random stream are made would pass them; it fails here.

`--regen-goldens` rewrites tests/goldens/fx_programs.npz; review why the
frames moved before committing it."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pewpew.compose import Look, layer_seed
from pewpew.fx.catalog import example
from pewpew.fx.expr import layer, look
from pewpew.fx.graph import Program
from pewpew.fx.op import node_key, node_seed, stream
from pewpew.fx.ops import OPS
from pewpew.lab.check import ready
from pewpew.lab.geometry import parse_geometry
from pewpew.lab.rendering import play
from pewpew.testing.goldens import assert_matches_golden

GOLDEN = Path(__file__).parent / "goldens" / "fx_programs.npz"
FRAMES, FPS = 10, 30.0

# Each catalog example below, by name, and the map it renders on: a warp
# and a palette, a simulation, a swarm, a trail, a signal of each kind on
# a route, a layer that reads the one below, and two that need a plane.
PROGRAMS = {
    "field": ('noise(4).mirror().palette("ocean")', "line:32"),
    "life": ('life(5, speed=4).palette("synthwave", cycle=0.02)', "line:32"),
    "particles": ('particles(12, 6, 0.05, -0.1, 0.3, "top").palette("ice")', "line:32"),
    "trail": ('osc(2, 0.4, axis="u").posterize(4).trails(1.2).palette("aurora")', "line:32"),
    "walk": (OPS["walk"].examples[0], "line:32"),
    "lfo": (OPS["lfo"].examples[1], "line:32"),
    "reaction": ('reaction("maze", speed=90).contrast(1.6).palette("forest")', "grid:8x8"),
    "attractor": ('attractor("clifford", 2000, 0.05, 0, 0.04, 2).palette("ember")', "grid:8x8"),
}


def _look(chain: str) -> Look:
    made = example(chain)
    return made if isinstance(made, Look) else look(layer("base", made), seed=7)


def _below() -> Look:
    """A layer that reads the stack below it: hue-turned noise over noise."""
    base = example('noise(2, 0.07, octaves=3).palette("aurora")')
    top = example("below().hue(90)")
    assert isinstance(base, Program) and isinstance(top, Program)
    return look(layer("base", base), layer("tint", top, blend="screen", opacity=0.5), seed=7)


def _frames(made: Look, spec: str) -> np.ndarray:
    frames, errors = play(ready(made), parse_geometry(spec), FRAMES, FPS, 0)
    assert errors == ()
    return frames


def test_each_program_renders_its_stored_frames(regen_goldens: bool) -> None:
    arrays = {name: _frames(_look(chain), spec) for name, (chain, spec) in PROGRAMS.items()}
    arrays["below"] = _frames(_below(), "line:32")
    for name, frames in arrays.items():
        assert frames.std() > 0, f"{name} renders one flat frame, which pins nothing"
    assert_matches_golden(GOLDEN, arrays, regen=regen_goldens)


def test_a_nodes_key_seed_and_stream_are_the_same_numbers_in_every_version() -> None:
    """ADR-022: a node's key is its layer's seed and the CRC-32 of its
    layer and node ids; its seed and its counter-based stream come from
    the key. Every random op's frames follow from these numbers."""
    seed = layer_seed(7, "base")
    key = node_key(seed, "base", "fx")
    assert (seed, key, node_seed(key)) == (1718781062, 0x66728486AE0FF791, 1602141336)
    assert stream(key, 1).random(3).tolist() == pytest.approx(
        [0.5758195234084904, 0.8489166149708269, 0.5819149354183115], abs=0.0
    )
