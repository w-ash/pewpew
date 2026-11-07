"""What the tests share: fakes of time, sockets, processes and the loop's
call queue; a recorded DDP sink; socket helpers for the preview; room
documents; and the patterns test looks name. Imported by test modules;
conftest.py holds only hooks and fixtures."""

from __future__ import annotations

import contextlib
import io
import json
import os
import pickle
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from collections.abc import Callable, Hashable, Iterator, Mapping
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, TypeVar

import numpy as np
from websockets.sync.client import connect

from pewpew import Float, Pattern, Renderer, audit, line, watchdog
from pewpew.__main__ import main, parse
from pewpew.audio import keys
from pewpew.aura.book import CycleConfig, LookBook
from pewpew.aura.control import AuraControl
from pewpew.aura.deck import Deck
from pewpew.aura.looks import Looks
from pewpew.aura.master import Master
from pewpew.aura.triggers import Triggers
from pewpew.aura.variety import Made, Variety, at_once
from pewpew.classinfo import pattern_name
from pewpew.compose import Compositor, Layer, Look, Resolved, pattern_layer, pattern_of
from pewpew.crossfade import Crossfader
from pewpew.errors import LoadError, unknown
from pewpew.features import EventFeatures, FakeFeatures
from pewpew.fx import expr, surprise
from pewpew.fx.catalog import example as catalog_example
from pewpew.fx.compile import is_pattern_program
from pewpew.fx.expr import noise
from pewpew.fx.graph import Program
from pewpew.fx.host import ProgramPattern
from pewpew.lab import handles
from pewpew.load import LoadedPattern, from_class
from pewpew.pace import Calls
from pewpew.patterns import Pulse, Sparkle, Wave
from pewpew.render import SlotClock
from pewpew.run import Launch, Run
from pewpew.sinks.ddp import Board, DdpSink
from pewpew.sinks.preview import PreviewSink

T = TypeVar("T")

EXAMPLE_ROOM = Path(__file__).resolve().parents[1] / "examples" / "room-60-bars.json"


class FakeProcess:
    """A `subprocess.Popen` stand-in: running until `end` or `terminate`."""

    def __init__(self, args: list[str]) -> None:
        self.args = args
        self.code: int | None = None
        self.terminated = False

    def poll(self) -> int | None:
        return self.code

    def end(self, code: int = 0) -> None:
        self.code = code

    def terminate(self) -> None:
        self.terminated = True
        self.code = -15

    def wait(self, timeout: float | None = None) -> int | None:
        return self.code

    def kill(self) -> None:
        self.code = -9


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


def ddp_sink(boards: list[Board], n: int, *, fail_for: str | None = None,
             start: bool = True) -> tuple[DdpSink, UdpRecorder, FakeTime]:
    """A 40 fps DDP sink of `n` pixels on a fake clock and a recording
    socket, started unless `start` is False."""
    rec = UdpRecorder(fail_for)
    ft = FakeTime()
    sink = DdpSink(boards, n, open_socket=lambda: rec, now=ft.now, sleep=ft.sleep)
    if start:
        sink.start()
    return sink, rec, ft


def no_watch(source, stop):
    """A watcher that never fires, so no in-process run touches watchfiles."""
    return iter(())


class LoopThread:
    """Drains a call queue on a thread of its own, as the loop thread
    would, so a `pick` that waits for the loop's answer can be answered."""

    def __init__(self, queue: Calls) -> None:
        self.queue = queue
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.is_set():
            self.queue.drain()
            self.stop.wait(0.002)

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop.set()
        self.thread.join()


def next_text(ws) -> dict:
    """The next text message, skipping binary frames."""
    while True:
        msg = ws.recv(timeout=5.0)
        if isinstance(msg, str):
            return json.loads(msg)


def next_of(ws, kind: str, timeout: float = 5.0) -> dict:
    """The next text message of type `kind`, skipping frames and other messages."""
    deadline = time.monotonic() + timeout
    while (message := next_text(ws))["type"] != kind:
        assert time.monotonic() < deadline, f"no {kind!r} message came"
    return message


def wait_until(cond, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not cond():
        assert time.monotonic() < deadline, "condition never became true"
        time.sleep(0.005)


def greet(sink: PreviewSink):
    """Connect to `sink` and read what it sends a new client: the hello,
    the status, and with a control wired its declare, params, mod, aura,
    health and catalog. Returns the socket and those messages by type, in the
    order sent, once the sink also sends to this client: it greets a client
    before it registers one, and a frame sent between the two misses it."""
    control = sink._control
    kinds = {"hello", "status"}
    if control is not None:
        kinds |= {"declare", "params", "mod", "aura", "catalog"}
        if control.health() is not None:
            kinds.add("health")
    ws = connect(f"ws://127.0.0.1:{sink.port}/")
    greeting: dict[str, dict] = {}
    while set(greeting) != kinds:
        message = next_text(ws)
        greeting[message["type"]] = message
    me = ws.local_address
    wait_until(lambda: me in peers(sink))
    return ws, greeting


def client_for(sink: PreviewSink):
    """Connect to `sink` past its greeting; returns the socket and the hello."""
    ws, greeting = greet(sink)
    return ws, greeting["hello"]


def preview_sink(mapping, **kw) -> PreviewSink:
    """A preview of `mapping` on a free port and a fake clock, not started."""
    ft = FakeTime()
    return PreviewSink(mapping, port=0, now=ft.now, sleep=ft.sleep, **kw)


@contextlib.contextmanager
def serving(control: AuraControl, calls: Calls):
    """`control` behind a started 4-pixel preview on a fake clock, with
    `calls` drained on a loop thread. Yields the sink, a client past its
    greeting, and the greeting by type."""
    with preview_sink(line(4), control=control) as sink, LoopThread(calls):
        ws, greeting = greet(sink)
        with ws:
            yield sink, ws, greeting


def peers(sink: PreviewSink) -> set:
    """The clients `sink` sends to, each by its address, or by its
    connection id once its socket has closed."""
    with sink._lock:
        conns = tuple(sink._clients)
    out = set()
    for conn in conns:
        try:
            out.add(conn.remote_address)
        except OSError:
            out.add(conn.id)
    return out


def bar(fid: str = "bar", **kw) -> dict:
    """One room fixture: a 1 m, 64 px bar along x on board A output 1. A
    key given as None is left out."""
    spec = {
        "id": fid, "pixels": 64, "start": [0.0, 0.0], "end": [1.0, 0.0],
        "input": "start", "board": "A", "output": 1, "chain": 1,
    }
    spec.update(kw)
    return {k: v for k, v in spec.items() if v is not None}


def room(*fixtures: dict, boards: Mapping[str, str] | None = None) -> dict:
    """A room document of `fixtures`, on board A at 10.0.0.11 unless
    `boards` says otherwise."""
    return {"boards": dict(boards or {"A": "10.0.0.11"}), "fixtures": list(fixtures)}


class Solid(Pattern):
    """One colour everywhere, from three params."""

    red = Float(1.0, 0.0, 1.0)
    green = Float(0.0, 0.0, 1.0)
    blue = Float(0.0, 0.0, 1.0)

    def render(self, x, y, z, index):
        out = np.empty((self.n, 3), dtype=np.float32)
        out[:] = (self.red, self.green, self.blue)
        return out


class PixelRamp(Pattern):
    """Red rises along the pixels: index / n."""

    def render(self, x, y, z, index):
        out = np.zeros((self.n, 3), dtype=np.float32)
        out[:, 0] = index / self.n
        return out


class FixtureRamp(PixelRamp):
    """Blue rises along the fixtures; one value per fixture."""

    units = "fixture"

    def render(self, x, y, z, index):
        out = np.zeros((self.n, 3), dtype=np.float32)
        out[:, 2] = (index + 1) / self.n
        return out


class Raises(Solid):
    def render(self, x, y, z, index):
        raise RuntimeError("broken render")


# The patterns a look in the tests may name, by pattern name.
LOOK_CLASSES = {pattern_name(c): c for c in (Solid, PixelRamp, FixtureRamp, Raises, Pulse, Wave, Sparkle)}


def look(pattern: str, params: Mapping | None = None, **kw) -> Look:
    """A look of one layer, `base`, running `pattern` at `params`; `kw` are
    the look's own fields (master, fade, cycle, seed)."""
    return Look((pattern_layer("base", pattern, params),), **kw)


def layered(pattern: str, args=None, *, node: str | None = None, **fields) -> dict:
    """`look(pattern, args, **fields)` as a looks file holds it, its node
    id `node` (default: `pattern`, which a path is not). `args` that is not
    an object goes in as it is, without the pattern."""
    body = {"op": "pattern", "args": {"pattern": pattern, **(args or {})} if args is None or isinstance(args, Mapping)
            else args}
    return {"layers": [{"id": "base", "nodes": {node or pattern: body}}], **fields}


def filed(look: Mapping) -> str:
    """`look`, a single look's JSON form, as the text of a looks file that
    holds it alone: a look's one file form (ADR-006 amendment "layered paths")."""
    return json.dumps({"version": 4, "looks": {"look": look}})


def solid(r=0.0, g=0.0, b=0.0, **kw) -> Look:
    return look("solid", {"red": r, "green": g, "blue": b}, **kw)


def frames(source, count: int = 30, fps: float = 60.0) -> np.ndarray:
    """`count` frames of `source` (a renderer, a stack or a crossfader),
    each copied, one slot apart at `fps` from its time now."""
    clock = SlotClock(fps, start=source.t)
    return np.stack([source.advance_to(clock.advance()).copy() for _ in range(count)])


def the(pattern: object, cls: type[T]) -> T:
    """`pattern`, a renderer's, as the class `cls` it runs, to read its params."""
    assert isinstance(pattern, cls), pattern
    return pattern


def program_of(chain: str) -> Program:
    """The program a builder chain makes (pewpew.fx.catalog.example), for a
    chain of ops, not a whole look."""
    made = catalog_example(chain)
    assert isinstance(made, Program), chain
    return made


# A moving colour field: a frame source whose frames differ with time.
FLOW = ProgramPattern.of(Program.of(noise(4).palette("aurora")))


def hosted(source: object, mapping: np.ndarray | None = None, **kw) -> Renderer:
    """`source`, a program, a builder chain or a `ProgramPattern` class,
    running as layer `base` on `mapping` (line(16)); `kw` go to the
    renderer, such as its seed."""
    cls = source if isinstance(source, type) else ProgramPattern.of(Program.of(source))  # type: ignore[arg-type]
    return Renderer(cls(), line(16) if mapping is None else mapping, name="layers.base", **kw)


def program_layer(lid: str, source: object, **mix: object) -> tuple[Layer, type[Pattern]]:
    """A layer `lid` that runs `source`, a program or a builder chain, and the class that hosts it: a
    `stack` entry. `mix` are the layer's own fields, such as its blend."""
    program = Program.of(source)  # type: ignore[arg-type]
    return Layer(lid, program, **mix), ProgramPattern.of(program, {"solid": Solid})  # type: ignore[arg-type]


def stack(*layers: tuple[Layer, type[Pattern]], mapping=None, seed: int = 0, **kw) -> Compositor:
    """A compositor of `layers`, each (layer, class), on `mapping` (line(8)),
    each shown by its pattern's spec, a program by its layer's id."""
    shown = [Resolved(layer, cls, spec(layer) if is_pattern_program(layer.program) else layer.id)
             for layer, cls in layers]
    return Compositor(shown, line(8) if mapping is None else mapping, seed=seed, **kw)


class Pooled(Mapping[Hashable, Any]):
    """A module's `JOBS` results by key, from the suite's process pool
    (conftest.py). Reading one waits for its job and raises what the job
    raised."""

    def __init__(self, futures: Mapping[Hashable, Future[Any]]) -> None:
        self._futures = futures

    def __getitem__(self, key: Hashable) -> Any:
        return self._futures[key].result()

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._futures)

    def __len__(self) -> int:
        return len(self._futures)


# Each state file pewpew writes, by the environment variable that moves it.
# A test, and each worker of the suite's process pool, keeps its own
# (conftest.py).
STATE_FILES = {watchdog.MARKER_ENV: "stalled", audit.ENV_VAR: "audit.jsonl", handles.CACHE_ENV: "renders",
               keys.ENV_VAR: "audio-keys.json"}


def strict() -> None:
    """The suite's rules in a process where monkeypatch does not reach: a
    warning is an error, every node's output is checked to be a float32
    field, and the real capture library never loads (conftest.py)."""
    warnings.simplefilter("error")
    sys.modules.setdefault("sounddevice", None)  # type: ignore[assignment]  # an import of it raises ImportError
    ProgramPattern.strict = True


def strict_worker(state: Path) -> None:
    """`strict` in a worker of the suite's process pool, with the state
    files in a new folder under `state`, which a process the worker starts
    takes too (conftest.py)."""
    strict()
    folder = Path(tempfile.mkdtemp(dir=state))
    os.environ.update({var: str(folder / name) for var, name in STATE_FILES.items()})


def run_python(code: str, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    """`code` run by a new Python process with `args`, and `env` over this
    process's environment: its output, as text. Raises CalledProcessError
    when it exits non-zero."""
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, check=True,
                          env={**os.environ, **env})


# The new process of `in_new_process`: it runs the job pickled in its
# argument under the suite's rules and writes what the job gives, pickled,
# as the process pool passes a job between the suite's own processes.
_JOB_CODE = (
    "import pickle, sys, fakes\n"
    "fakes.strict()\n"
    "print(pickle.dumps(pickle.loads(bytes.fromhex(sys.argv[1]))()).hex())\n"
)


def in_new_process(job: Callable[[], T], **env: str) -> T:
    """What `job` gives when a new Python process runs it under the suite's
    rules (`strict`), with `env` over this process's environment. `job` and
    what it gives pickle; the process imports `job` from the tests folder."""
    out = run_python(_JOB_CODE, pickle.dumps(job).hex(), PYTHONPATH=str(Path(__file__).parent), **env)
    return pickle.loads(bytes.fromhex(out.stdout))


def spec(layer: Layer) -> str:
    """The pattern spec that `layer`'s one pattern node runs."""
    return pattern_of(layer.program.output)[0]


def rgb(r: float, g: float, b: float, n: int) -> np.ndarray:
    """A frame of `n` pixels of one float32 color."""
    return np.tile(np.array([r, g, b], np.float32), (n, 1))


def layer_renderer(aura, lid: str = "base") -> Renderer:
    """The renderer layer `lid` of a rig's or a run's running stack runs now."""
    return aura.fader.current.layer(lid).renderer


class FakeCatalog:
    """A `pewpew.load.Catalog` over test pattern classes, by pattern name."""

    def __init__(self, classes: Mapping[str, type]) -> None:
        self.classes = dict(classes)
        self.names = sorted(self.classes)
        self.search_dir: Path | None = None  # no pattern files

    def rescan(self) -> None:
        self.names = sorted(self.classes)

    def resolve(self, name: str) -> LoadedPattern:
        if name not in self.classes:
            raise LoadError(unknown("pattern", name, self.names))
        return from_class(self.classes[name])


def aura_rig(start: type = Solid, *, mapping=None, grouping=None, catalog=None, cap: float = 1.0,
             looks: Mapping[str, Look] | None = None, current: str | None = None, cycle=None,
             triggers: Mapping | None = None, path=None, watch=no_watch, timeout: float = 5.0,
             log=None, blink=None, boards=None, health=None, accept_looks: bool = False,
             variety=None, submit=None) -> SimpleNamespace:
    """An aura without a loop or sinks: a one-layer stack (`base`, running
    `start`), crossfader, deck, master, looks (when `looks` is given),
    triggers and the aura control, built as `pewpew.run.Run` builds them;
    `variety(deck)` makes the looks a surprise, a vary and the director's
    fresh slots play, and `submit` runs a fresh slot's making (default: at
    once, on the caller's thread).
    `frame(t)` runs the `before` hooks and renders, as one loop tick does;
    `calls.drain()` runs what the controls queued. `renderer(lid)` is the
    renderer layer `lid` runs now, and `reloader(lid)` its reloader."""
    r = SimpleNamespace()
    r.calls = Calls()
    r.features = EventFeatures(FakeFeatures(0))
    name = pattern_name(start)
    stack = Compositor([Resolved(pattern_layer("base", name), start, name)], line(4) if mapping is None else mapping,
                       features=r.features, grouping=grouping)
    r.fader = Crossfader(stack)
    r.catalog = catalog if catalog is not None else FakeCatalog(LOOK_CLASSES)
    r.deck = Deck(r.fader, r.catalog, r.calls.call_soon, {"base": from_class(start)}, watch=watch)
    r.renderer = lambda lid="base": layer_renderer(r, lid)
    r.reloader = lambda lid="base": r.deck.reloaders[lid]
    r.master = Master(cap)
    r.variety = variety(r.deck) if variety is not None else Variety(r.deck)
    r.looks = None
    if looks is not None:
        r.path = path
        r.book = LookBook(looks, current, cycle or CycleConfig(), triggers=triggers or {})
        r.looks = Looks(path, r.book, r.deck, r.master, variety=r.variety, submit=submit or at_once)
    r.triggers = Triggers(triggers or {}, looks=r.looks, features=r.features, log=log)
    r.control = AuraControl(r.calls, r.deck, r.master, r.triggers, looks=r.looks, blink=blink, boards=boards,
                            health=health, accept_looks=accept_looks, variety=r.variety, timeout=timeout)
    r.clock = SlotClock(60.0)

    def frame(t: float):
        r.triggers.before_frame(t)
        if r.looks is not None:
            r.looks.before_frame(t)
        return r.fader.advance_to(t)

    r.frame = frame
    return r


class Painter:
    """A `Variety` for `aura_rig(variety=Painter)` that makes solid looks at
    once: a surprise green, a variation as bright as its strength, or
    nothing when `fail` is set."""

    def __init__(self, deck) -> None:
        self.deck = deck
        self.fail = False

    def surprise(self, seed=None) -> Made:
        if self.fail:
            raise surprise.NoLook("nothing made from seed 9 passed the content gate in 16 tries; try another seed")
        return Made(solid(0.0, 1.0, 0.0, fade=0.0), f"surprise {seed}")

    def vary(self, strength=None, seed=None, of=None) -> Made:
        return Made(solid(strength or 0.3, fade=0.0), f"variation {seed}")


def run_main(argv: list[str], *, ansi_stream: io.StringIO | None = None, **kw) -> tuple[int, str]:
    """`main` on a fake sink clock, with no file watcher: the RateGate then
    costs no wall time and cannot let the loop outrun the driver, so frame
    counts are exact. Returns the exit code and what the ANSI sink wrote."""
    ft = FakeTime()
    stream = ansi_stream if ansi_stream is not None else io.StringIO()
    kw.setdefault("watch", no_watch)
    rc = main(argv, ansi_stream=stream, now=ft.now, sleep=ft.sleep, **kw)
    return rc, stream.getvalue()


def build(argv: list[str], **kw) -> Run:
    """The `Run` that `main(argv)` would serve, built and not started, on
    the same fakes as `run_main`."""
    ft = FakeTime()
    kw.setdefault("watch", no_watch)
    launch = Launch.read(parse(argv), argv, now=ft.now, sleep=ft.sleep)
    return Run(launch, ansi_stream=io.StringIO(), now=ft.now, sleep=ft.sleep, **kw)


def instant_looks(monkeypatch) -> None:
    """Make `pewpew.fx.surprise.generate` and `mutate` instant, for a test
    of what calls them: a look of stripes for each seed, and the look given
    reseeded, neither judged."""

    def generate(seed, mapping, **kw):
        return expr.look(expr.layer("base", expr.osc(1 + seed % 7, 0.1).palette("ember")), seed=seed % 1000)

    def mutate(made, seed, mapping, **kw):
        return replace(made, seed=seed % 1000)

    monkeypatch.setattr(surprise, "generate", generate)
    monkeypatch.setattr(surprise, "mutate", mutate)
