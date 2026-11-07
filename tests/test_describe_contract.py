"""The describe contract: `tests/goldens/describe.json` is what the page is
built and tested against (web/), so it must equal the live `describe()` of
every gallery pattern and the params zoo, and every value in it must pass
`check`. `--regen-goldens` rewrites it; review the diff before committing."""

from __future__ import annotations

import json
from pathlib import Path

from params_zoo import PARAM_CASES
from pewpew.classinfo import pattern_name
from pewpew.params import ParamSet
from pewpew.params.probes import leaves, probes
from pewpew.sinks.base import DISPLAY_GAMMA

GOLDEN = Path(__file__).parent / "goldens" / "describe.json"
CLASSES = {pattern_name(cls): cls for cls, _, _ in PARAM_CASES}


def live() -> dict:
    return {
        "display_gamma": DISPLAY_GAMMA,
        "patterns": {name: ParamSet(cls).describe() for name, cls in CLASSES.items()},
    }


def test_the_golden_is_the_live_describe(regen_goldens: bool) -> None:
    if regen_goldens:
        GOLDEN.write_text(json.dumps(live(), indent=2, ensure_ascii=False) + "\n")
    assert json.loads(GOLDEN.read_text()) == live(), "run `uv run pytest --regen-goldens` and review the diff"


def _values(record: dict) -> list:
    """Every value the record names: its default, both sides of each probe,
    and the ends and `text` values of each numeric leaf."""
    out = [record["default"]]
    out += [v for _, a, b in probes(record) for v in (a, b)]
    for _, spec, value in leaves(record):
        out += [value(x) for x in (spec["lo"], spec["hi"], *(t["value"] for t in spec["text"]))]
    return out


def test_every_value_in_the_golden_passes_check() -> None:
    golden = json.loads(GOLDEN.read_text())
    for pattern, records in golden["patterns"].items():
        params = ParamSet(CLASSES[pattern])
        for record in records:
            for value in _values(record):
                assert params.check(record["name"], value) is None, (pattern, record["name"], value)
