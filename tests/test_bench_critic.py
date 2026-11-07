"""The pairwise critic bench's tally (bench/bench_critic.py): a pair
counts only when its two orders agree, and a tie both ways is half a win
to each."""

from __future__ import annotations

from bench.bench_critic import tally


def test_a_pair_counts_when_both_orders_agree_and_a_tie_is_half_to_each():
    manifest = {
        "looks": [{"look": 1}, {"look": 2}, {"look": 3}],
        "pairs": [
            {"a": 1, "b": 2, "verdicts": [{"winner": "A"}, {"winner": "B"}]},  # 1 both ways
            {"a": 1, "b": 3, "verdicts": [{"winner": "tie"}, {"winner": "tie"}]},
            {"a": 2, "b": 3, "verdicts": [{"winner": "A"}, {"winner": "A"}]},  # each order its first: no agreement
            {"a": 2, "b": 1, "verdicts": [{"winner": "B"}]},  # one order only: not counted
        ],
    }
    assert tally(manifest) == {1: 1.5, 2: 0.0, 3: 0.5}
