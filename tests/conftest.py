from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regen-goldens",
        action="store_true",
        default=False,
        help="rewrite golden baselines from current output instead of comparing",
    )


@pytest.fixture
def regen_goldens(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--regen-goldens"))
