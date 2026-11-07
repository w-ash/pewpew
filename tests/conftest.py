from __future__ import annotations

import itertools
import os
import sys
from collections.abc import Callable, Hashable, Iterator
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import websockets.sync.server
from hypothesis import settings

from fake_sounddevice import FakeSoundDevice, laptop
from fakes import EXAMPLE_ROOM, STATE_FILES, FakeProcess, Pooled, UdpRecorder, strict_worker
from pewpew import audit, awake, watchdog, wled
from pewpew.fx.host import ProgramPattern
from pewpew.room.map import load_room
from pewpew.sinks import ddp

# Property tests draw the same examples on every run and keep no database of
# failing examples, so the suite stays deterministic. Hypothesis still caches
# constants in .hypothesis/, which ignores itself in git. A property draws 50
# examples; `just test-thorough` loads "thorough" (`--hypothesis-profile`),
# which draws Hypothesis's default 100. A test that needs more draws a
# multiple of the loaded profile's count (`settings().max_examples`).
settings.register_profile("pewpew", derandomize=True, database=None, deadline=None, max_examples=50)
settings.register_profile("thorough", settings.get_profile("pewpew"), max_examples=100)
settings.load_profile("pewpew")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regen-goldens",
        action="store_true",
        default=False,
        help="rewrite golden baselines from current output instead of comparing",
    )


@pytest.fixture(scope="session")
def state_folders(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A new folder path for each test's state files, made by the code that
    writes one. `tmp_path` would make a folder for every test, after a scan
    of every folder made before it."""
    root = tmp_path_factory.mktemp("state")
    return (root / str(n) for n in itertools.count())


@pytest.fixture(autouse=True)
def no_real_side_effects(monkeypatch: pytest.MonkeyPatch, state_folders: Iterator[Path]) -> None:
    """No test reaches a board over HTTP or a resolver, holds a real sleep assertion,
    exits the process from the watchdog, reads or writes the real stall
    marker, appends to the real audit log, uses the real render cache or
    capture nodes' key file, or loads the real capture library: a test that
    wants one of these injects its own fake (`fake_sounddevice` for an
    input, `fake_node` for a capture node). The audit log goes to the
    `audit_log` path, and the render cache and the key file to this test's
    own folder.

    A preview's stop waits for its connection handlers in steps of the
    websockets server's shutdown poll, 0.1 s, nearly every time a client was
    connected; the tests poll at 1 ms. uv.lock pins websockets, so a rename
    upstream fails this setattr rather than slowing the suite."""

    def no_fetch(host: str, timeout: float = 0.0) -> dict:
        raise OSError("no network in tests")

    def no_exit(code: int) -> None:
        raise AssertionError(f"the watchdog tried to exit with {code}")

    monkeypatch.setattr(wled, "fetch_info", no_fetch)
    monkeypatch.setattr(wled, "sender_address", lambda host, port=0: None)
    monkeypatch.setattr(wled, "resolve_name", lambda name: (_ for _ in ()).throw(OSError("no resolver in tests")))
    monkeypatch.setattr(awake, "_spawn", lambda args: FakeProcess(args))
    monkeypatch.setattr(watchdog, "_exit", no_exit)
    monkeypatch.setitem(sys.modules, "sounddevice", None)  # an import of it raises ImportError
    folder = next(state_folders)
    for var, name in STATE_FILES.items():
        monkeypatch.setenv(var, str(folder / name))
    monkeypatch.setattr(websockets.sync.server.Server, "SHUTDOWN_POLLING_INTERVAL", 0.001)


@pytest.fixture(autouse=True)
def strict_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every node of every program a test runs is checked to give a float32
    field of the right shape (`ProgramPattern.strict`); a worker of the
    suite's process pool, and a process `fakes.in_new_process` starts, sets
    it with `fakes.strict`."""
    monkeypatch.setattr(ProgramPattern, "strict", True)


@pytest.fixture(scope="session", autouse=True)
def pool_jobs(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[ModuleType | None, Pooled]]:
    """Each module's `JOBS` results, by module. The jobs of every module
    whose selected tests read `pooled` start on one process pool before the
    first test, so they run beside the tests in front of them. `JOBS` maps a
    key to a job that takes no arguments and gives a result that pickles.
    Each worker holds the suite's rules (`fakes.strict_worker`)."""
    tables: dict[ModuleType | None, dict[Hashable, Callable[[], Any]]] = {
        item.module: getattr(item.module, "JOBS", {}) for item in request.session.items
        if isinstance(item, pytest.Function) and "pooled" in item.fixturenames}
    count = sum(map(len, tables.values()))
    if not count:
        yield {}
        return
    pool = ProcessPoolExecutor(min(count, os.cpu_count() or 1), initializer=strict_worker,
                               initargs=(tmp_path_factory.mktemp("workers"),))
    try:
        yield {module: Pooled({key: pool.submit(job) for key, job in jobs.items()}) for module, jobs in tables.items()}
    finally:
        pool.shutdown(cancel_futures=True)


@pytest.fixture
def pooled(pool_jobs: dict[ModuleType | None, Pooled], request: pytest.FixtureRequest) -> Pooled:
    """This module's `JOBS` results, by key."""
    return pool_jobs.get(request.module, Pooled({}))


@pytest.fixture
def audit_log() -> Path:
    """The audit log, in this test's own directory (set by `no_real_side_effects`)."""
    return audit.audit_path()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> UdpRecorder:
    """The socket every DDP sink the run opens sends through."""
    rec = UdpRecorder()
    monkeypatch.setattr(ddp, "_udp_socket", lambda: rec)
    return rec


@pytest.fixture
def sd(monkeypatch: pytest.MonkeyPatch) -> FakeSoundDevice:
    """The capture library, faked (fake_sounddevice.laptop): what every
    import of sounddevice gets in this test."""
    fake = laptop()
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    return fake


@pytest.fixture(scope="session")
def example():
    """The example room, compiled once: tests only read it."""
    return load_room(EXAMPLE_ROOM)[0]


@pytest.fixture
def regen_goldens(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--regen-goldens"))
