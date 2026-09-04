r"""The minimal live runner: `python -m pewpew run <pattern>`.

Wires renderer -> PacedLoop -> SinkDriver-wrapped sinks so the no-hardware
dev path (§8) is one command:

    uv run python -m pewpew run comet --map line:64 --ansi
    uv run python -m pewpew run fire --map grid:16x16 --preview

Deliberately minimal — argparse only. The pattern comes from `pewpew.load`
(a gallery name, a file, or `--patterns DIR`), and `pewpew.reload` watches
its source so a save swaps the new class in while the show runs.

The library logs and the application presents. `pewpew.*` modules only ever
`getLogger(__name__)`; this is the one place that installs a handler, and
it installs a *deferring* one whenever the ANSI sink owns an interactive
terminal. A pattern that raises makes `Renderer._contain` log a multi-line
traceback, and that text landing on stderr mid-frame would desync the
sink's `\x1b[nF` rewind from the block it is rewinding over — every later
frame would then scribble on the wrong rows. The red status line under the
grid is the in-band error channel while the show runs; the buffered
records replay to stderr once the terminal is handed back.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import shutil
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterator, TextIO

import numpy as np

import pewpew.patterns as gallery
from pewpew import PacedLoop, ParamSet, Renderer, SinkDriver, grid, lattice, line
from pewpew.load import LoadedPattern, LoadError, resolve
from pewpew.reload import Reloader, Watch
from pewpew.sinks import AnsiSink, PreviewSink

logger = logging.getLogger(__name__)

_GRACE = 2.0  # extra seconds to wait on a mid-send worker before releasing


def _load(spec: str, search_dir: Path | None = None) -> LoadedPattern:
    """Resolve the `pattern` argument, turning every load failure into one
    clean exit line. The path is prefixed here and nowhere else: `LoadError`
    text is path-free by contract so the same wording can cross the preview
    socket as a reload status (pewpew.load)."""
    try:
        return resolve(spec, search_dir=search_dir)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from None
    except LoadError as exc:
        raise SystemExit(f"{exc.path}: {exc}" if exc.path is not None else str(exc)) from None


def _mapping(spec: str) -> np.ndarray:
    kind, _, arg = spec.partition(":")
    try:
        if kind == "line":
            return line(int(arg))
        if kind == "grid":
            w, _, h = arg.partition("x")
            return grid(int(w), int(h))
        if kind == "lattice":
            return lattice(int(arg))
    except ValueError:
        pass
    raise SystemExit(f"bad --map {spec!r}; expected line:64, grid:16x16, or lattice:8")


def _default_mapping(pattern_cls: type) -> np.ndarray:
    """The fixture a pattern was authored against, for a bare `run <pattern>`.

    `grid:16x16` fits geq and fire and nothing else — comet and plasma were
    written for `line(300)`, sdf3d for `lattice(10)` — so the no-argument run,
    the first thing anyone types, showed three of five patterns on geometry
    they were never designed against. A pattern outside the study table keeps
    the old default.
    """
    mapping = gallery.default_mapping(pattern_cls)
    return _mapping("grid:16x16") if mapping is None else mapping


def _params(pairs: list[str], pattern_cls: type) -> dict[str, float]:
    """Parse `--param NAME=VALUE` and validate it against the declarations.

    Validated here rather than by catching what `Renderer` raises, because that
    constructor also raises for a bad mapping and propagates whatever `setup`
    raises. Binding is deliberately loud (render.py) and a blanket except would
    reduce an author's traceback to one line on the primary dev loop, so only
    knob errors are turned into a clean exit.
    """
    knobs = ParamSet(pattern_cls)
    out: dict[str, float] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"bad --param {pair!r}; expected name=value")
        try:
            out[key] = float(value)
        except ValueError:
            raise SystemExit(f"bad --param value in {pair!r}; expected a number") from None
        reason = knobs.check(key, out[key])
        if reason is not None:
            hint = knobs.hint(key)
            raise SystemExit(f"{reason}. {hint}" if hint else reason)
    return out


def _status_of(*sources: Any) -> Callable[[], str | None]:
    """The `status` supplier both sinks take: the first `.error` that is set,
    in the order given. The reloader goes first — its outcome is the freshest
    thing the author acted on; if the old pattern is broken *and* the fix has
    a SyntaxError, the SyntaxError is what they need to see.

    Snapshots each `.error` once: this runs on a SinkDriver worker while the
    loop thread clears the error on the first healthy frame, so testing the
    attribute and then formatting it would race — a pattern that heals
    between the two reads would paint a red status line reading `None`.
    """

    def status() -> str | None:
        for source in sources:
            err = source.error
            if err:
                return str(err)
        return None

    return status


class _LoopControls:
    """Bridges the preview's back-channel to the renderer's loop thread.

    Validation happens on the caller's thread and only what passed is
    queued, because `PacedLoop.call_soon` propagates a closure's exception
    out of `run()` — a raising setter reached over a socket is a way to
    stop the show from a browser (ADR-006 amendment, verified).
    """

    def __init__(self, renderer: Renderer, call_soon: Callable[[Callable[[], None]], None]) -> None:
        self._renderer = renderer
        self._call_soon = call_soon

    def describe(self) -> list[dict]:
        return self._renderer.params.describe()

    def set(self, name: str, value: object) -> str | None:
        reason = self._renderer.params.check(name, value)
        if reason is not None:
            return reason  # network-safe wording; `hint` names a file, so it stays here
        self._call_soon(lambda: self._apply(name, float(value)))  # type: ignore[arg-type]
        return None

    def _apply(self, name: str, value: float) -> None:
        """Runs on the loop thread, where `call_soon` drains before
        `advance_to`, so no frame sees half a change. Must not raise: the
        value passed `check` on another thread, but a reload could narrow
        its range in between, and that must not be how the show ends."""
        try:
            self._renderer.set_param(name, value)
        except ValueError:
            logger.warning("dropped a live set of %r to %r: no longer in range", name, value)


class _DeferredLog(logging.Handler):
    """Hold log records while a sink owns the terminal; replay on release.

    Bounded because a wedged run must not grow without limit; 200 is far
    above what the engine can produce, since `Renderer._contain` already
    logs once per distinct failure site and `SinkDriver` once per exception
    type — nothing on the frame path logs per frame.
    """

    def __init__(self, limit: int = 200) -> None:
        super().__init__()
        self.records: deque[logging.LogRecord] = deque(maxlen=limit)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def replay(self, stream: TextIO) -> None:
        while self.records:
            stream.write(self.format(self.records.popleft()) + "\n")
        stream.flush()


@contextlib.contextmanager
def _cli_logging(handler: logging.Handler) -> Iterator[None]:
    """Install `handler` on the `pewpew` logger for the life of one run."""
    root = logging.getLogger("pewpew")
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    previous_level, previous_propagate = root.level, root.propagate
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False
    try:
        yield
    finally:
        # Removed rather than left in place: the tests call main() repeatedly
        # in one process and stacked handlers would duplicate every record.
        root.removeHandler(handler)
        root.setLevel(previous_level)
        root.propagate = previous_propagate


def main(
    argv: list[str] | None = None,
    *,
    ansi_stream: TextIO | None = None,
    now: Callable[[], float] = time.perf_counter,
    sleep: Callable[[float], None] = time.sleep,
    watch: Watch | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m pewpew")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="render a pattern live to one or more sinks")
    run.add_argument(
        "pattern",
        help="gallery name (comet, fire, ...), path/to/file.py, or file.py:ClassName",
    )
    run.add_argument(
        "--patterns",
        type=Path,
        default=None,
        metavar="DIR",
        help="also resolve a bare name as DIR/<name>.py (before the gallery)",
    )
    run.add_argument(
        "--map",
        default=None,
        dest="map_spec",
        metavar="SPEC",
        help="line:64, grid:16x16 or lattice:8 (default: the pattern's own study fixture)",
    )
    run.add_argument("--fps", type=float, default=60.0)
    run.add_argument("--ansi", action="store_true", help="terminal sink (the default sink)")
    run.add_argument(
        "--preview",
        nargs="?",
        const=7447,
        type=int,
        default=None,
        metavar="PORT",
        help="browser preview sink on PORT (default 7447)",
    )
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--param", action="append", default=[], metavar="NAME=VALUE")
    run.add_argument("--frames", type=int, default=None, help="stop after N frames (default: run until ^C)")
    run.add_argument(
        "--no-reload",
        action="store_true",
        help="do not watch the pattern's source file for edits (default: hot reload on)",
    )
    args = parser.parse_args(argv)

    loaded = _load(args.pattern, args.patterns)
    pattern_cls = loaded.cls
    mapping = _default_mapping(pattern_cls) if args.map_spec is None else _mapping(args.map_spec)
    renderer = Renderer(
        pattern_cls(), mapping, params=_params(args.param, pattern_cls), seed=args.seed
    )
    # `loop` is assigned further down; no watcher runs until reloader.start(),
    # so the late binding is safe (same reasoning as the preview's controls).
    reloader = Reloader(renderer, loaded, lambda fn: loop.call_soon(fn), watch=watch)
    status = _status_of(reloader, renderer)

    sinks: list = []
    ansi: AnsiSink | None = None
    if args.ansi or args.preview is None:
        # The terminal budget is sniffed here, never in the sink: keeping
        # AnsiLayout's defaults fixed is what keeps render_frame pure and
        # the exact-string goldens valid. Only a real stdout is measured.
        size = shutil.get_terminal_size((80, 24)) if ansi_stream is None else None
        ansi = AnsiSink(
            mapping,
            stream=ansi_stream,
            status=status,
            now=now,
            sleep=sleep,
            **({"max_width": size.columns, "max_height": size.lines} if size else {}),
        )
        sinks.append(ansi)
    if args.preview is not None:
        # `loop` is assigned a few lines down and no client can connect until
        # sink.start(), so binding it late here is safe and keeps the loop's
        # construction order (it needs the drivers, which need the sinks).
        controls = _LoopControls(renderer, lambda fn: loop.call_soon(fn))
        sinks.append(
            PreviewSink(
                mapping,
                port=args.preview,
                status=status,
                controls=controls,
                now=now,
                sleep=sleep,
            )
        )

    drivers = [SinkDriver(s.send, name=type(s).__name__) for s in sinks]
    loop = PacedLoop(renderer, fps=args.fps, on_frame=drivers)

    # Whoever owns the terminal decides where log records may go. `interactive`
    # is answerable before start(), so the handler is in place for the whole
    # sink lifecycle rather than only once the loop is running.
    deferred = _DeferredLog()
    handler: logging.Handler = (
        deferred if ansi is not None and ansi.interactive else logging.StreamHandler(sys.stderr)
    )
    try:
        with _cli_logging(handler):
            try:
                for sink in sinks:
                    sink.start()
                    if isinstance(sink, PreviewSink):
                        print(
                            f"preview at http://{sink.host}:{sink.port}/",
                            file=sys.stderr,
                            flush=True,
                        )
                for driver in drivers:
                    driver.start()
                if not args.no_reload:
                    reloader.start()
                loop.run(frames=args.frames)
            except KeyboardInterrupt:
                pass
            finally:
                reloader.stop()
                _teardown(drivers, sinks)
    finally:
        deferred.replay(sys.stderr)
    return 0


def _teardown(drivers: list[SinkDriver], sinks: list) -> None:
    """Let the last frame land, then release each transport in order.

    `SinkDriver.stop()` returns False while its worker is still mid-send —
    "do not tear down its transport yet". Honour it with one bounded grace
    period, then release anyway: at exit the alternative is a hung process
    with the cursor still hidden and the preview port still held. The
    warning is what makes the rare case visible.
    """
    for driver in drivers:
        driver.drain()
    for driver, sink in zip(drivers, sinks):
        if not driver.stop() and not driver.stop(timeout=_GRACE):
            logger.warning(
                "sink %r is still sending after %.0fs; releasing its transport anyway",
                driver.name,
                _GRACE,
            )
        sink.stop()


if __name__ == "__main__":
    sys.exit(main())
