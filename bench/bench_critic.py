"""Pairwise taste check of made looks — evidence for tuning the grammar of
`pewpew.fx.surprise`, never a gate.

The judge (`surprise.judge`) catches what numbers can: flashing, black,
dead knobs, too dark, washed out, frozen, noise, grey. Whether a made look
is *good* is taste. This bench makes K looks from a seed on one map,
renders each, and writes everything a judge needs to compare them in
pairs, both ways round, since a judge prefers one position more often
than chance (`.claude/agents/look-critic.md`):

    bench/results/critic-<label>/
        manifest.json     the looks, their handles and seeds, and each pair
        looks.png         every look in rows numbered 1 to K
        look-<i>.json     look i, for look_check, look_render or `run --looks`
        pair-<i>-<j>.png  looks i and j as rows A and B, and pair-<j>-<i>.png

The procedure is manual (L1 bench, test-and-feedback.md §4; not a pytest
rig). For each pair in `manifest.json`, hand the look-critic subagent the
two handles and the brief, once each way round, or judge the two sheets
by eye, and write each verdict ({"winner": "A" | "B" | "tie", ...}) into
that pair's `verdicts` list. Then tally:

    uv run python -m bench.bench_critic --label mac --k 6 --seed 1 --map grid:16x16
    uv run python -m bench.bench_critic --tally bench/results/critic-mac/manifest.json

The tally counts each look's wins, a tie as half a win to each, and
leaves out a pair whose two orders disagree (the critic's own rule: no
agreement, a tie). A verdict is one sample of a noisy judge: report the
counts with the metrics, never as a pass or fail.
"""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from pewpew import lab
from pewpew.command import whole
from pewpew.lab.handles import Cache
from pewpew.lab.variations import MAX_VARIANTS

RESULTS = Path(__file__).parent / "results"
BRIEF = "a look for a quiet room at night: slow, dark ground, rich colour, never busy"


def make(label: str, k: int, seed: int, map_spec: str, seconds: float, brief: str) -> Path:
    """Make, render and draw K looks, and write the manifest (module
    docstring); returns the manifest's path."""
    out = RESULTS / f"critic-{label}"
    out.mkdir(parents=True, exist_ok=True)
    cache = Cache()  # the MCP server's own, so the critic's look_compare finds each handle
    made = lab.vary(None, seed, k, map_spec=map_spec, seconds=seconds, cache=cache)
    shutil.copy(lab.rows([c.handle for c in made.candidates], cache=cache).path, out / "looks.png")
    looks = []
    for i, candidate in enumerate(made.candidates, 1):
        (out / f"look-{i}.json").write_text(json.dumps(candidate.look, indent=2) + "\n")
        looks.append({"look": i, "seed": candidate.seed, "handle": candidate.handle,
                      "metrics": candidate.metrics.to_json()})
    pairs = []
    for i, j in itertools.combinations(range(1, k + 1), 2):
        a, b = made.candidates[i - 1].handle, made.candidates[j - 1].handle
        for first, second, x, y in ((a, b, i, j), (b, a, j, i)):
            lab.compare_sheet(first, second, out=out / f"pair-{x}-{y}.png", cache=cache)
        pairs.append({"a": i, "b": j, "sheets": [f"pair-{i}-{j}.png", f"pair-{j}-{i}.png"], "verdicts": []})
    manifest = {"label": label, "brief": brief, "seed": seed, "map": map_spec, "seconds": seconds,
                "looks": looks, "pairs": pairs}
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def tally(manifest: dict[str, Any]) -> dict[int, float]:
    """Each look's wins over its pairs (module docstring). A pair's first
    verdict reads it as A against B, its second as B against A."""
    wins: Counter[int] = Counter({look["look"]: 0.0 for look in manifest["looks"]})
    for pair in manifest["pairs"]:
        if len(pair["verdicts"]) != 2:
            continue
        a_first, b_first = (v["winner"] for v in pair["verdicts"])
        order = {"A": pair["a"], "B": pair["b"]}
        swapped = {"A": pair["b"], "B": pair["a"]}
        one, two = order.get(a_first), swapped.get(b_first)
        if one is not None and one == two:
            wins[one] += 1.0
        elif a_first == b_first == "tie":
            wins[pair["a"]] += 0.5
            wins[pair["b"]] += 0.5
    return dict(sorted(wins.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="local", help="names the results folder: critic-<label>")
    parser.add_argument("--k", type=whole(2, "a count", MAX_VARIANTS), default=6,
                        help=f"looks to make, 2 to {MAX_VARIANTS} (default 6)")
    parser.add_argument("--seed", type=whole(0, "a seed"), default=0, help="the seed the looks are made from")
    parser.add_argument("--map", default="grid:16x16", help="where they are made for and rendered")
    parser.add_argument("--seconds", type=float, default=4.0, help="how long each render is")
    parser.add_argument("--brief", default=BRIEF, help="what the judge judges the looks against")
    parser.add_argument("--tally", type=Path, default=None, metavar="MANIFEST",
                        help="count the verdicts written into a manifest, and make nothing")
    args = parser.parse_args(argv)
    if args.tally is not None:
        print(json.dumps(tally(json.loads(args.tally.read_text())), indent=2))
        return 0
    path = make(args.label, args.k, args.seed, args.map, args.seconds, args.brief)
    print(f"wrote {path}; judge each pair both ways (look-critic, or by eye), then --tally {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
