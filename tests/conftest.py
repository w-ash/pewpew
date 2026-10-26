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


class FakeCallSoon:
    """Stands in for `PacedLoop.call_soon`, without a running loop."""

    def __init__(self) -> None:
        self.queued: list = []

    def __call__(self, fn) -> None:
        self.queued.append(fn)

    def drain(self) -> None:
        while self.queued:
            self.queued.pop(0)()


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


class UdpRecorder:
    """A UDP socket stand-in that keeps every datagram it is asked to send;
    sends to `fail_for` raise as an unreachable host would."""

    def __init__(self, fail_for: str | None = None) -> None:
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.closed = 0
        self.fail_for = fail_for

    def sendto(self, data: bytes, address: tuple[str, int]) -> int:
        if address[0] == self.fail_for:
            raise OSError(65, "No route to host")
        self.sent.append((bytes(data), address))
        return len(data)

    def close(self) -> None:
        self.closed += 1
