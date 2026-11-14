"""The `branches` op: a tree of light grown out of a point. Its shape
(forks, lengths, widths), its seed, its soft glow, its beads' way, `grow`,
its flash limit, and the search that keeps its cost down. Every arg's
liveness on each map it takes is tests/test_fx_ops.py's."""

from __future__ import annotations

from functools import partial
from typing import Any

import numpy as np
import pytest

import fakes
from fakes import op_of, program_of
from pewpew.fx.ops import radiate
from pewpew.mapping import grid, lattice
from pewpew.metrics import FLASH_LIMIT, measure
from pewpew.render import SlotClock

FPS = 60.0
SEED = 42
hosted = partial(fakes.hosted, seed=SEED)


def run(chain: str, mapping: np.ndarray, frames: int, seed: int = SEED) -> np.ndarray:
    renderer = fakes.hosted(program_of(chain), mapping, seed=seed)
    clock = SlotClock(FPS)
    return np.stack([renderer.advance_to(clock.advance()).copy() for _ in range(frames)])[..., 0]


def tree_of(chain: str, mapping: np.ndarray) -> Any:
    renderer = hosted(program_of(chain), mapping)
    renderer.advance_to(1 / FPS)
    return op_of(renderer, "branches").tree()


def test_each_trunk_forks_in_two_each_level_each_arm_shrink_as_long_and_thin_from_its_parents_end() -> None:
    tree = tree_of("branches(3, 5, shrink=0.6, width=0.2, jitter=0)", grid(64, 64))
    plan = tree.plan
    assert [hi - lo for lo, hi in plan.levels] == [3 * 2**level for level in range(5)]
    child = plan.parent >= 0
    up = plan.parent[child]
    assert np.bincount(up, minlength=len(tree))[: plan.levels[-1][0]].tolist() == [2] * plan.levels[-1][0]
    np.testing.assert_allclose(tree.length[child], 0.6 * tree.length[up])
    np.testing.assert_allclose(tree.width[child], 0.6 * tree.width[up])
    np.testing.assert_allclose(tree.s0[child], tree.s0[up] + tree.length[up])
    np.testing.assert_allclose(tree.start[child], tree.start[up] + tree.chord[up], atol=1e-12)
    assert np.allclose(tree.start[: plan.levels[0][1]], 0.0) and tree.length[0] == pytest.approx(0.2)


def test_an_uneven_tree_forks_in_one_two_or_three_and_a_small_turn_of_jitter_moves_it_a_little() -> None:
    tree = tree_of("branches(6, 4, jitter=1)", grid(32, 32))
    arms = np.bincount(tree.plan.parent[tree.plan.parent >= 0], minlength=len(tree))[: tree.plan.levels[-1][0]]
    assert set(arms.tolist()) == {1, 2, 3}
    lengths = tree.length[tree.plan.level == 1] / tree.length[tree.plan.parent[tree.plan.level == 1]]
    assert lengths.std() > 0.05, "arms of their own length"

    def moved(step: float) -> float:
        renderer = hosted(program_of("branches(6, 4, jitter=0.5, floor=1)"), grid(32, 32))
        before = renderer.advance_to(1.0).copy()
        renderer.bound.node_params["branches"].set("jitter", 0.5 + step)
        return float(np.abs(renderer.advance_to(1.0 + 1 / FPS) - before).max())

    assert moved(0.001) < 0.05 and moved(0.001) < 0.4 * moved(0.004), "an arm grows in, it never pops"


def test_the_same_seed_grows_the_same_tree_byte_for_byte_and_another_seed_another() -> None:
    chain = "branches(jitter=0.6, sway=0.5, flow=0.5)"
    first, again, other = (run(chain, grid(24, 24), 30, seed) for seed in (SEED, SEED, SEED + 1))
    assert first.tobytes() == again.tobytes()
    assert not np.array_equal(first, other)


def test_a_branch_glows_softly_across_with_no_step_and_never_past_full() -> None:
    """Across a branch the light falls as the glow's profile, (1 - d²/w²)³,
    whose steepest slope is 1.72 / w: no hard line, for diffused lights."""
    n = 161
    frames = run("branches(2, 3, width=0.1, shrink=0.7, jitter=1, floor=1)", grid(n, n), 2)
    image = frames[-1].reshape(n, n)
    assert image.min() >= 0.0 and image.max() <= 1.0 and image.max() > 0.99
    step = max(np.abs(np.diff(image, axis=0)).max(), np.abs(np.diff(image, axis=1)).max())
    finest = 0.1 * 0.7**2
    assert step < 1.5 * 1.72 * (1.0 / (n - 1)) / finest


@pytest.mark.parametrize("flow", [0.5, -0.5])
def test_beads_run_out_along_a_trunk_and_back_in_below_zero(flow: float) -> None:
    """A bead's place along the trunk from x = 0.25 moves at `flow` beads
    a second, out when above 0: the phase of the beads along it turns
    by `flow` * 0.4 of a turn in 0.4 s."""
    n = 201
    renderer = hosted(program_of(f"branches(1, 2, width=0.08, jitter=0, floor=0, flow={flow}, beads=0.1, cx=0.25)"),
                      grid(n, n))
    row = slice(100 * n + 60, 100 * n + 80)  # y = 0.5, x from 0.3 to 0.4: one bead apart
    x = np.arange(60, 80) / (n - 1)

    def phase(t: float) -> float:
        light = renderer.advance_to(t)[row, 0]
        return float(np.angle((light * np.exp(-2j * np.pi * x / 0.1)).sum()))

    turned = (phase(1.0) - phase(1.4)) / (2 * np.pi)
    assert (turned + 0.5) % 1.0 - 0.5 == pytest.approx(flow * 0.4, abs=0.03)


def test_grow_draws_the_tree_from_the_point_out_from_only_its_glow_at_0_to_all_of_it_at_1() -> None:
    n = 65
    points = grid(n, n)
    away = np.linalg.norm(points[:, :2] - 0.5, axis=1)
    lit = {grow: run(f"branches(grow={grow}, jitter=0, floor=1)", points, 2)[-1] > 1e-6 for grow in (0, 0.3, 0.6, 1)}
    assert lit[0].any() and away[lit[0]].max() <= 0.06 + 1e-6, "only the origin's glow"
    assert (lit[0] <= lit[0.3]).all() and (lit[0.3] <= lit[0.6]).all() and (lit[0.6] <= lit[1]).all()
    tips = tree_of("branches(jitter=0)", points).tips
    assert away[lit[1]].max() > 0.6 * tips and away[lit[0.6]].max() < away[lit[1]].max()
    assert np.array_equal(lit[1], run("branches(jitter=0, floor=1)", points, 2)[-1] > 1e-6)


@pytest.mark.parametrize("chain, mapping", [
    ("branches(12, 7, width=0.01, jitter=1, flow=2, beads=0.02, floor=0, sway=1)", grid(24, 24)),
    ("branches(12, 7, width=0.3, jitter=1, flow=-2, beads=0.5, floor=0, sway=1, flat=0)", lattice(7)),
])
def test_a_tree_at_its_fastest_stays_within_the_flash_limit(chain: str, mapping: np.ndarray) -> None:
    """A point sees one train of beads, at `flow`, however many glows
    reach it and however the tree sways; and no glow is finer than the
    points, so a swaying twig does not blink across them."""
    renderer, clock = hosted(program_of(f'{chain}.palette("ember")'), mapping), SlotClock(FPS)
    frames = np.stack([renderer.advance_to(clock.advance()).copy() for _ in range(600)])
    assert 0.0 < measure(frames, FPS).flash_rate_max <= FLASH_LIMIT


def _every_pair(p: np.ndarray, tree: Any, reach: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.repeat(np.arange(len(p)), len(tree)), np.tile(np.arange(len(tree)), len(p))


@pytest.mark.parametrize("chain", ["branches(jitter=0.7, grow=0.8)", "branches(jitter=0.7, sway=1, flat=0.5)"])
def test_the_pairs_a_tree_searches_light_the_points_as_every_pair_would(
    chain: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A still tree finds which branches pass near which points once; a
    swaying one every REFRESH seconds, for wherever each branch goes until
    the next time. Neither leaves out a pair that lights a point."""
    searches = []
    near = radiate._near

    def counted(*args: Any) -> Any:
        searches.append(1)
        return near(*args)

    monkeypatch.setattr(radiate, "_near", counted)
    found = run(chain, lattice(10), 80)
    assert len(searches) == (1 if "sway" not in chain else 1 + int(80 / FPS / radiate.REFRESH))
    monkeypatch.setattr(radiate, "_near", _every_pair)
    assert np.array_equal(found, run(chain, lattice(10), 80))


def test_a_strip_is_refused_with_what_to_use() -> None:
    from pewpew.fx.compile import check

    (problem,) = check(program_of("branches()"), where="layers.base", dims=1)
    assert problem.endswith("use pulse")


def test_a_flat_tree_in_a_volume_takes_no_center_across_its_plane() -> None:
    """At `flat` 1 the tree lies in the map's main plane and lights the
    depth across it alike, so the center along that depth does nothing."""
    shown, cube = radiate.Branches.shows, [1.0, 1.0, 0.5]  # main plane xy
    assert not shown("cz", 0.0, 1.0, {"flat": 1.0}, cube)
    assert shown("cz", 0.0, 1.0, {"flat": 0.5}, cube) and shown("cy", 0.0, 1.0, {"flat": 1.0}, cube)
    assert not shown("flat", 0.0, 1.0, {"flat": 1.0}, [1.0, 1.0, 0.0])
