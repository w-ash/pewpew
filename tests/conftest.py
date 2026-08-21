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


class FakeTime:
    """Wall-time fake for pacing tests: a perfect sleeper whose sleep(s)
    advances the clock by exactly s. The pacing counterpart of the
    harness FakeClock, which fakes *pattern* time."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = float(start)
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


class Oversleeper(FakeTime):
    """macOS-shaped sleeper: every sleep lands `overshoot` seconds late."""

    def __init__(self, overshoot: float, start: float = 0.0) -> None:
        super().__init__(start)
        self.overshoot = overshoot

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s + self.overshoot
