"""The live run behind `python -m pewpew run`: read and check the launch,
build the aura in dependency order, start it, and tear it down.

`Launch.read` turns the parsed command line into everything a run needs
and refuses what it cannot run with one clean exit line (a bad pattern
file, room map, arrangement, power cap, looks file, `--param`, `--ddp` or
`--audio`); `--dry-run` stops there with `Launch.plan`. `Run` builds the
parts, each from the ones before it:

    stats -> features -> DDP sink, blink -> watchdog, keep-awake, health
    -> the aura (pewpew.aura.pipeline) -> room -> sinks -> the paced loop

so every part gets what it needs at construction. The health monitor
reaches the room, built after the aura, only once the run starts. The command line's
pattern runs as a stack of one layer, `base` (pewpew.compose), so its
knobs are `layers.base.<pattern>.<param>` and its seed is derived from
`--seed` as every layer's is. An arrangement `--map` (`pewpew.rig`) gives
the mapping, one unit per fixture, and a power model. Its `power` block,
with `--max-watts` and `--max-brightness` replacing its values, is the
power limit: the loop's last `after` stage, behind the master, so every
sink gets the capped frame. The one exception is
the preview's view of the room: the room reload pushes a new map to the
preview, and the preview reads the room reload's status, so the preview
subscribes to the room after both exist (`RoomLive.listeners`).

The features are the seeded stand-in, or with `--audio` the analysis of
one of this computer's inputs, a capture node or a WAV file
(`pewpew.audio.AudioFeatures`, a `before` stage ahead of the triggers), or
a feature log played back.

`serve` starts the parts, runs the loop, and stops them in reverse. Real
boards are tier-1 hardware (CLAUDE.md T-7): the DDP sink starts only after
its audit record is written. Opening an input is a privacy act, so the
supervisor of a live input (a device or a node) starts only after its
`audio-input` audit record is written, and stops once the loop has
stopped (pewpew.audio.device, pewpew.audio.net). A preview that
cannot listen yet (its port held, or a router not up at login) never
darkens the room: the aura runs on, and the preview tries again every
`PREVIEW_RETRY_S`.

The library logs and the application presents. `pewpew.*` modules only
ever `getLogger(__name__)`; `serve` installs the one handler for a run,
and a *deferring* one whenever the ANSI sink owns an interactive terminal.
A pattern that raises makes `Renderer._contain` log a multi-line
traceback, and that text landing on stderr mid-frame would desync the
sink's `\\x1b[nF` rewind from the block it is rewinding over. The red
status line under the grid is the in-band error channel while the aura
runs; the buffered records replay to stderr once the terminal is handed
back.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import functools
import ipaddress
import json
import logging
import os
import re
import shutil
import sys
import threading
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TextIO

import numpy as np

import pewpew.patterns as gallery
from pewpew import audit
from pewpew.audio import AudioFeatures, AudioSource, FeatureLog, LiveSource, ReplayFeatures
from pewpew.audio.inputs import read_input
from pewpew.aura.book import LookBook, load_looks, pattern_problems
from pewpew.aura.deck import pattern_label
from pewpew.aura.pipeline import build_aura_pipeline
from pewpew.awake import KeepAwake
from pewpew.compose import Look, Resolved, layer_address, pattern_layer
from pewpew.errors import LoadError
from pewpew.features import EventFeatures, FakeFeatures, FeatureSource
from pewpew.fx.graph import as_id
from pewpew.health import HealthMonitor
from pewpew.jsonfile import read_or_exit
from pewpew.load import Catalog, LoadedPattern, resolve
from pewpew.mapping import Grouping
from pewpew.pace import PaceStats
from pewpew.params import ParamSet
from pewpew.power import PowerCap, PowerLimiter, power_stage
from pewpew.reload import Watch
from pewpew.render import PatternError
from pewpew.room.blink import Blink
from pewpew.room.live import RoomLive
from pewpew.room.map import RoomMap, load_room
from pewpew.sinks.ansi import AnsiSink
from pewpew.sinks.base import Sink, SinkDriver
from pewpew.sinks.ddp import DdpSink, parse_board
from pewpew.sinks.preview import PreviewSink
from pewpew.watchdog import TIMEOUT_S as WATCHDOG_S
from pewpew.watchdog import Watchdog, marker_path, take_marker

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

logger = logging.getLogger(__name__)

GRACE_S = 2.0  # extra seconds to wait on a mid-send worker before releasing
PREVIEW_RETRY_S = 5.0  # how often a preview that cannot listen tries again
BASE = "base"  # the layer the command line's pattern runs on


@dataclass(frozen=True)
class Launch:
    """Everything a run reads and checks before anything starts: the
    pattern, the room map, the geometry, the power limit, the DDP sink,
    the looks file, the `--param` values and the `--audio` input. `read`
    refuses a launch it cannot run with one clean exit line, before a dry
    run returns, so the unattended checklist's attended dry run refuses what
    launchd's restarts would."""

    args: argparse.Namespace
    argv: list[str]  # the command line, as the audit log records it
    loaded: LoadedPattern
    catalog: Catalog
    room: RoomMap | None
    room_bytes: bytes
    mapping: np.ndarray
    grouping: Grouping | None
    limiter: PowerLimiter | None
    ddp: DdpSink | None
    book: LookBook | None
    params: dict[str, Any]
    audio: AudioSource | ReplayFeatures | None

    @classmethod
    def read(
        cls, args: argparse.Namespace, argv: list[str], *,
        now: Callable[[], float], sleep: Callable[[float], None],
    ) -> Launch:
        loaded = load(args.pattern, args.pattern_dir)
        catalog = Catalog(args.pattern_dir, launch=args.pattern)
        room, room_bytes = (None, b"") if args.room is None else read_or_exit(
            args.room, "room map", lambda: load_room(args.room)
        )
        rig = None
        if isinstance(args.map, Path):
            rig = rig_map(args.map)
            mapping, grouping = rig.mapping, rig.grouping
        else:
            mapping, grouping = geometry(args.map, loaded.cls, room)
        limiter = power_limiter(args.max_watts, args.max_brightness, rig)
        if args.units == "fixture" and grouping is None:
            raise SystemExit("--units fixture needs --room or an arrangement --map: other maps have no fixtures")
        streams = bool(args.ddp) or (room is not None and not args.no_ddp)
        ddp = None
        if streams:
            try:
                boards = room.boards if room is not None else [parse_board(spec) for spec in args.ddp]
                # The loop feeds the sink at most `--fps` frames a second.
                ddp = DdpSink(boards, len(mapping), max_fps=min(args.fps, args.ddp_fps), now=now, sleep=sleep)
            except ValueError as exc:
                raise SystemExit(str(exc)) from None
        book = looks_book(args.looks, args.master_cap, catalog) if args.looks is not None else None
        node = as_id(pattern_label(catalog.launch or args.pattern, loaded.cls, catalog.names))
        params = parse_params(args.param, loaded.cls, layer_address(BASE, node))
        if args.trigger_log is not None:
            check_log(args.trigger_log, "trigger log")
        audio = None
        if args.audio is not None:
            try:
                audio = read_input(args.audio, fps=args.fps, channel=args.audio_channel, unattended=args.unattended,
                                   allow_hosts=args.allow_hosts, bind=args.host)
            except ValueError as exc:
                raise SystemExit(f"--audio {args.audio}: {exc}") from None
        if args.feature_log is not None:
            check_log(args.feature_log, "feature log")
        return cls(
            args, argv, loaded, catalog, room, room_bytes, mapping, grouping, limiter, ddp, book, params, audio,
        )

    @property
    def spec(self) -> str:
        """The launch pattern as a look stores it (pewpew.load.Catalog)."""
        return self.catalog.launch or self.args.pattern

    @property
    def label(self) -> str:
        """The launch pattern's name on the page: never a path."""
        return pattern_label(self.spec, self.loaded.cls, self.catalog.names)

    @property
    def look(self) -> Look:
        """The launch: one layer, `BASE`, running the pattern at the
        `--param` values, seeded by `--seed`."""
        values = ParamSet(self.loaded.cls, self.params).snapshot_json()
        layer = pattern_layer(BASE, self.spec, values, node=as_id(self.label))
        return Look((layer,), seed=self.args.seed)

    def plan(self) -> list[str]:
        """The per-board DDP plan and the input to open, as `--dry-run` prints them."""
        lines: list[str] = []
        if self.ddp is not None:
            lines += self.room.plan(self.ddp.max_fps) if self.room is not None else self.ddp.plan()
        if isinstance(self.audio, LiveSource):
            lines.append(self.audio.describe())
        return lines


class Run:
    """One live run, built from a `Launch` in dependency order (the module
    docstring). Every part is an attribute; `serve` starts them, runs the
    loop until `--frames` or ^C, and tears them down."""

    def __init__(
        self,
        launch: Launch,
        *,
        ansi_stream: TextIO | None = None,
        now: Callable[[], float],
        sleep: Callable[[float], None],
        watch: Watch | None = None,
    ) -> None:
        args = self.args = launch.args
        self.launch = launch
        self.stats = PaceStats()
        # Opened once every argument has passed, so a refused launch leaves no file behind.
        self.feature_log = None
        if args.feature_log is not None:
            header = {"seed": args.seed, "fps": args.fps, "audio": args.audio, "delay_ms": args.audio_delay}
            self.feature_log = FeatureLog(open_log(args.feature_log, "feature log"), header,
                                          hours=args.feature_log_hours)
        self.audio = None
        self.capture = launch.audio if isinstance(launch.audio, LiveSource) else None
        base: FeatureSource = FakeFeatures(args.seed)
        if isinstance(launch.audio, ReplayFeatures):
            base = launch.audio
        elif launch.audio is not None:
            self.audio = base = AudioFeatures(
                launch.audio, fps=args.fps, delay=args.audio_delay / 1000.0, log=self.feature_log,
            )
        features = EventFeatures(base)
        # Opened once every argument has passed, so a refused launch leaves no file behind.
        self.trigger_log = open_log(args.trigger_log, "trigger log") if args.trigger_log is not None else None
        self.ddp = launch.ddp
        room = launch.room
        self.blink = Blink(room) if room is not None else None
        # `--watchdog`, else on for an unattended run only, so a debugger stopped at
        # a breakpoint in a dev run is not killed; 0 is off.
        watchdog_s = (args.watchdog if args.watchdog is not None else WATCHDOG_S if args.unattended else 0.0) or None
        self.watchdog = Watchdog(watchdog_s, marker=marker_path()) if watchdog_s is not None else None
        self.awake = KeepAwake() if args.keep_awake or args.unattended else None
        # The monitor also restarts caffeinate when it ends, so `awake` needs it.
        self.monitor = None
        if args.preview or self.ddp is not None or self.awake is not None:
            self.monitor = HealthMonitor(
                self.ddp, stats=self.stats, target=args.fps, awake=self.awake, watchdog=watchdog_s,
                names=self._board_names if room is not None else None,
                argv=launch.argv, on_rebind=self._rebind_board if room is not None else None,
                audio=self.audio.state if self.audio is not None else None,
            )
        look = launch.look
        # An unattended run leaves a failing layer out of the mix (`bypass`); its
        # error still reaches the status line.
        self.aura = build_aura_pipeline(
            look, [(Resolved(look.layers[0], launch.loaded.cls, launch.label), launch.loaded)], launch.mapping,
            catalog=launch.catalog, seed=args.seed, features=features, grouping=launch.grouping, units=args.units,
            bypass=args.unattended, now=now, watch=watch, master_cap=args.master_cap, looks_path=args.looks,
            book=launch.book, trigger_log=self.trigger_log, trigger_log_max=int(args.trigger_log_max * 1_000_000),
            blink=self.blink, boards=self.monitor if self.ddp is not None else None,
            health=self.monitor.state if self.monitor is not None else None, accept_looks=args.accept_looks,
        )
        self.calls, self.features, self.fader, self.deck = self.aura.calls, features, self.aura.fader, self.aura.deck
        self.master, self.variety, self.looks = self.aura.master, self.aura.variety, self.aura.looks
        self.triggers, self.control = self.aura.triggers, self.aura.control
        if args.armed:
            self.triggers.arm(True, "launch")  # applied and logged at the first tick
        self.room = None if room is None else RoomLive(
            args.room, room, launch.room_bytes, self.fader, self.calls.call_soon,
            ddp=self.ddp, argv=launch.argv, blink=self.blink, watch=watch,
        )
        sources: list[tuple[Source, Any]] = [
            ("reload", self.deck), ("reload", self.room), ("render", self.fader), ("looks", self.looks),
        ]
        status = status_line(*(source for source in sources if source[1] is not None))
        # Each output and how it starts, in start order.
        self.outputs: list[tuple[Sink, Callable[[], None]]] = []
        self.ansi = None
        if args.ansi or (not args.preview and self.ddp is None):
            # The terminal budget is sniffed here, never in the sink: keeping
            # AnsiLayout's defaults fixed is what keeps render_frame pure and
            # the exact-string goldens valid. Only a real stdout is measured.
            size = shutil.get_terminal_size((80, 24)) if ansi_stream is None else os.terminal_size((80, 24))
            self.ansi = AnsiSink(
                launch.mapping, stream=ansi_stream, status=status_text(status), max_width=size.columns,
                max_height=size.lines, now=now, sleep=sleep,
            )
            self.outputs.append((self.ansi, self.ansi.start))
        self.preview = None
        self.preview_retry: threading.Thread | None = None
        self._stopping = threading.Event()
        if args.preview:
            self.preview = PreviewSink(
                launch.mapping, host=args.host or "127.0.0.1", port=args.port, status=status,
                control=self.control,
                room=room.describe() if room is not None else None,
                plan_image=room.plan_file(args.room) if room is not None else None,
                now=now, sleep=sleep,
            )
            self.outputs.append((self.preview, self._start_preview))
            if self.room is not None:
                self.room.listeners.append(self._show_room)
        if self.ddp is not None:
            self.outputs.append((self.ddp, self._start_ddp))
        self.drivers = [SinkDriver(sink.send, name=type(sink).__name__) for sink, _ in self.outputs]
        # Each frame: the audio, then the aura's own stages, before it renders;
        # after it, the aura's, then the power limit, behind the master.
        self.loop = self.aura.loop(
            args.fps, stats=self.stats,
            before=[self.audio.before_frame] if self.audio is not None else [],
            after=[power_stage(launch.limiter)] if launch.limiter is not None else [],
            on_frame=[*self.drivers, *([self.watchdog.beat] if self.watchdog is not None else [])],
        )

    def serve(self) -> int:
        """Start every part, run the loop, then stop them in reverse.

        Whoever owns the terminal decides where log records may go:
        `interactive` is answerable before `start`, so the handler is in
        place for the whole sink lifecycle."""
        deferred = _DeferredLog()
        handler: logging.Handler = (
            deferred if self.ansi is not None and self.ansi.interactive else logging.StreamHandler(sys.stderr)
        )
        services = [s for s in (self.awake, self.monitor) if s is not None]
        try:
            with _cli_logging(handler):
                try:
                    self._start(services)
                    self.loop.run(frames=self.args.frames)
                except KeyboardInterrupt:
                    pass
                finally:
                    self._stop(services)
        finally:
            deferred.replay(sys.stderr)
        return 0

    def _start(self, services: list) -> None:
        # Armed before the look restore, so a restored pattern that hangs in
        # `setup` or in its first render still ends the run.
        if self.watchdog is not None:
            self.watchdog.start()
        start_look = self._restore() if self.looks is not None else None
        self.triggers.begin_run(
            seed=self.args.seed, fps=self.args.fps, pattern=self.deck.current, look=start_look,
            armed=self.args.armed,
        )
        for _, start in self.outputs:
            start()
        for driver in self.drivers:
            driver.start()
        if self.feature_log is not None:
            self.feature_log.start()
        if self.capture is not None:
            self._start_capture()
        if not self.args.no_reload:
            self.deck.watch()
            if self.room is not None:
                self.room.start()
        for service in services:  # started last and stopped first
            service.start()

    def _stop(self, services: list) -> None:
        self._stopping.set()
        # The watchdog stops first: the teardown may take seconds.
        if self.watchdog is not None:
            self.watchdog.stop()
        for service in reversed(services):
            service.stop()
        if self.capture is not None:
            self.capture.stop()
        self.calls.close()
        if self.trigger_log is not None:
            # A flush that fails here must not skip the teardown.
            with contextlib.suppress(OSError):
                self.trigger_log.close()
        if self.feature_log is not None:
            self.feature_log.close()
        self.deck.unwatch()
        if self.room is not None:
            self.room.stop()
        if self.preview_retry is not None:
            self.preview_retry.join()  # so no listener opens after the teardown
        teardown(self.drivers, [sink for sink, _ in self.outputs])

    def _restore(self) -> str | None:
        """Start in the look the looks file names, with no fade. Returns that
        look, or None when the run starts in the command line's pattern."""
        looks = self.looks
        assert looks is not None
        name, current = looks.book.current, self.deck.current
        stalled = take_marker(marker_path())
        if stalled is not None and name is not None:
            # The last run's watchdog fired, maybe on this look's pattern:
            # restoring it could hang again and restart forever.
            reason = (f"the last run stalled {stalled:.0f} s ago, so look {name!r} was not restored; "
                      f"starting with {current}")
            print(reason, file=sys.stderr, flush=True)
            looks.error = reason
            return None
        if (reason := looks.restore()) is not None:
            print(f"{reason}; starting with {current}{map_hint(reason)}", file=sys.stderr, flush=True)
            looks.error = reason
            return None
        return name

    def _start_preview(self) -> None:
        """Listen and print the URL; if the address cannot be bound, say so
        and keep trying on a thread of its own (the module docstring)."""
        preview = self.preview
        assert preview is not None
        try:
            preview.start()
        except OSError as exc:
            # socket.create_server appends " (while attempting to bind on address ...)".
            reason = str(exc.strerror or exc).partition(" (while attempting")[0]
            print(f"preview: cannot listen on {preview.host}:{self.args.port} ({reason}); "
                  f"the aura runs on, and the preview tries again every {PREVIEW_RETRY_S:g} s",
                  file=sys.stderr, flush=True)
            self.preview_retry = threading.Thread(target=self._retry_preview, name="pewpew-preview-retry", daemon=True)
            self.preview_retry.start()
            return
        print(preview_url(preview.host, preview.port), file=sys.stderr, flush=True)  # type: ignore[arg-type]

    def _retry_preview(self) -> None:
        """Try to listen again every `PREVIEW_RETRY_S` until it works or the
        run stops, then print the URL."""
        preview = self.preview
        assert preview is not None
        while not self._stopping.wait(PREVIEW_RETRY_S):
            try:
                preview.start()
            except OSError:
                continue
            url = preview_url(preview.host, preview.port)  # type: ignore[arg-type]
            if self.ansi is not None and self.ansi.interactive:
                logger.info("%s", url)  # text mid-frame would desync the grid; replayed at the end
            else:
                print(url, file=sys.stderr, flush=True)
            return

    def _start_ddp(self) -> None:
        """Audit, then open the socket. Real boards are tier-1 hardware: no
        packet goes out unless the record was written first."""
        ddp = self.ddp
        assert ddp is not None
        extra = {} if self.args.room is None else {"room": str(self.args.room)}
        try:
            path = audit.record(
                "ddp-stream", argv=self.launch.argv, targets=[b.spec for b in ddp.boards], fps=ddp.max_fps, **extra,
            )
            ddp.start()
        except OSError as exc:
            raise SystemExit(f"ddp: {exc}") from None
        for line in self.launch.plan():
            print(line, file=sys.stderr, flush=True)
        print(f"audit record appended to {path}", file=sys.stderr, flush=True)

    def _start_capture(self) -> None:
        """Audit, then start the input's supervisor: no stream opens unless
        the record was written first."""
        capture = self.capture
        assert capture is not None
        try:
            path = capture.audit(self.launch.argv, feature_log=self.args.feature_log)
        except OSError as exc:
            raise SystemExit(f"audio: {exc}") from None
        capture.start()
        print(f"audio: opening {capture.kind} {capture.name!r}; audit record appended to {path}", file=sys.stderr,
              flush=True)

    def _board_names(self) -> tuple[str, ...]:
        """The room's board names, for the health monitor (`RoomLive.board_names`)."""
        return self.room.board_names() if self.room is not None else ()

    def _rebind_board(self, board: str, address: str) -> str | None:
        """Point a room board at `address`, for the health monitor (`RoomLive.rebind`)."""
        assert self.room is not None, "only a run with a room map rebinds a board"
        return self.room.rebind(board, address)

    def _show_room(self, room: RoomMap) -> None:
        """Draw a reloaded room map on the preview. Loop thread."""
        assert self.preview is not None
        self.preview.remap(room.mapping, room.describe(), room.plan_file(self.args.room))


def load(spec: str, search_dir: Path | None = None) -> LoadedPattern:
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


def geometry(
    mapping: np.ndarray | None, pattern_cls: type, room: RoomMap | None
) -> tuple[np.ndarray, Grouping | None]:
    """The mapping and its fixture grouping: the room's, the `--map`'s (no
    grouping), or the pattern's own study fixture with its grouping, so a
    bare `run pulse` renders per bar on the canopy as the room would. A
    pattern outside the study table gets `grid:16x16`."""
    if room is not None:
        return room.mapping, room.grouping
    if mapping is not None:
        return mapping, None
    return gallery.default_geometry(pattern_cls)


def rig_map(path: Path) -> CompiledRig:
    """Compile the arrangement file at `path` into a `CompiledRig`, with one
    clean exit line for a file that does not compile or has no pixels. Its
    warnings go to stderr. `pewpew.rig` and pydantic, a base dependency,
    are imported here, so a run on any other map loads neither."""
    from pewpew.rig import RigError, compile_rig, load_arrangement, load_catalog

    try:
        # A missing, unreadable or non-UTF-8 file is a RigError too.
        rig = compile_rig(load_arrangement(path), load_catalog())
    except RigError as exc:
        raise SystemExit(f"--map {path}: {exc}") from None
    for issue in rig.issues:
        where = f" ({issue.ref})" if issue.ref else ""
        print(f"{path}: {issue.level}: {issue.message}{where}", file=sys.stderr, flush=True)
    if rig.n == 0:
        raise SystemExit(f"--map {path}: the arrangement has no pixels")
    return rig


def power_limiter(
    max_watts: float | None, max_brightness: float | None, rig: CompiledRig | None
) -> PowerLimiter | None:
    """The run's power limit, or None when it caps nothing: the cap of the
    arrangement `rig`, if any, with each value given replacing its own.
    A watt cap needs `rig`, whose fixtures give the power model; the
    command line refuses one without it (`python -m pewpew`)."""
    base = PowerCap() if rig is None else rig.power_cap
    try:
        cap = PowerCap(
            base.max_watts if max_watts is None else max_watts,
            base.max_brightness if max_brightness is None else max_brightness,
        )
    except ValueError as exc:
        raise SystemExit(f"bad power cap: {exc}") from None
    if not cap.caps:
        return None
    return PowerLimiter(cap) if rig is None else rig.limiter(cap)


def looks_book(path: Path, cap: float, catalog: Catalog) -> LookBook:
    """Load and check `--looks` at launch. A malformed file is one clean
    exit line naming it; a look whose pattern or params no longer fit is a
    warning, and its recall copes as it does mid-run. A missing file is an
    empty book that the first save creates."""

    @functools.cache  # one load per pattern, however many looks use it
    def declared(pattern: str) -> type | None:
        return catalog.resolve(pattern).cls if catalog.offers(pattern) else None

    book = read_or_exit(path, "looks file", lambda: load_looks(path, cap=cap))
    for problem in pattern_problems(book, declared):
        logger.warning("%s: %s", path, problem)
    if not path.exists():
        print(f"{path} does not exist yet; the first saved look creates it", file=sys.stderr, flush=True)
    return book


def parse_params(pairs: list[str], pattern_cls: type, owner: str | None = None) -> dict[str, Any]:
    """`--param NAME=VALUE`, each checked against the declarations.

    `owner` is the address of the launch pattern's node
    (`layers.base.plasma`): NAME may be that address's knob,
    `layers.base.plasma.speed`, as `observe` and the page name it, or the
    bare `speed`, and a refusal names the knob by its address, as the
    socket does. VALUE is JSON when it parses as JSON (`1.5`, `true`,
    `{"h": 30, "s": 1, "v": 1}`) and the param takes it, else the raw text
    (a choice key, even one that reads as a number). Checked here rather
    than by catching what `Renderer` raises, because that constructor also
    raises for a bad mapping and propagates whatever `setup` raises.
    Binding is deliberately loud (render.py) and a blanket except would
    reduce an author's traceback to one line on the primary dev loop, so
    only param errors are turned into a clean exit.
    """
    params = ParamSet(pattern_cls, name=owner)
    out: dict[str, Any] = {}
    for pair in pairs:
        key, sep, text = pair.partition("=")
        if not sep:
            raise SystemExit(f"bad --param {pair!r}; expected name=value")
        if owner is not None and key.startswith(f"{owner}."):
            key = key.removeprefix(f"{owner}.")
        elif key.startswith("layers."):
            raise SystemExit(f"--param {key}: the command line sets only the launch pattern's knobs, "
                             f"{owner or params.owner}.NAME or NAME")
        try:
            raw = json.loads(text)
        except ValueError:
            raw = text
        value, reason = params.parse(key, raw)
        if reason is not None and raw != text and params.check(key, text) is None:
            value, reason = text, None  # a choice key that reads as JSON, such as "2"
        if reason is not None:
            raise SystemExit(params.refusal(key, reason))
        out[key] = value
    return out


Source = Literal["render", "reload", "looks"]  # the part an error comes from


class Status(NamedTuple):
    """An error for the status line: the part it comes from, its text, and
    for a render error the address of the part that raised
    (`layers.<layer>.<node>`), which during a fade may not be in the look
    fading in."""

    source: Source
    text: str
    path: str | None = None


# A map of each dimension, for a look whose ops need one the run's map is not.
_MAPS = {"1": "line:64", "2": "grid:16x16", "3": "lattice:8"}


def map_hint(reason: str) -> str:
    """`; run with --map ...` when `reason` refuses a look for its map's
    dimensions (pewpew.fx.compile), naming a map of each it takes; else
    nothing. `run`'s map follows its pattern, not the looks file."""
    found = re.search(r"needs a map of ([\d ]+(?:or [\d ]+)?)dimensions", reason)
    if found is None:
        return ""
    return "; run with " + " or ".join(f"--map {_MAPS[d]}" for d in found[1].replace("or", "").split() if d in _MAPS)


def status_line(*sources: tuple[Source, Any]) -> Callable[[], Status | None]:
    """The `status` supplier: the `Status` of the first `.error` that is
    set, in the order given, each source as (tag, object), or None. The run
    puts the reloads first: a reload's outcome is the freshest thing the
    author acted on, so a fix with a SyntaxError shows over the old
    pattern's error. A render error, which the room shows, goes before a
    failed look recall.

    Reads each `.error` once: this runs on a SinkDriver worker while the loop
    thread clears the error on the first healthy frame, so a test and a
    second read could race and paint a status reading `None`.
    """

    def status() -> Status | None:
        for tag, source in sources:
            err = source.error
            if err:
                return Status(tag, str(err), err.path if isinstance(err, PatternError) else None)
        return None

    return status


def status_text(status: Callable[[], Status | None]) -> Callable[[], str | None]:
    """The text alone, for a sink that shows one line."""
    return lambda: None if (found := status()) is None else found.text


def preview_url(host: str, port: int) -> str:
    """The line announcing the preview; one extra clause when the address is
    reachable from other machines. An IPv6 address is bracketed in the URL."""
    try:
        address: ipaddress.IPv4Address | ipaddress.IPv6Address | None = ipaddress.ip_address(host)
    except ValueError:
        address = None
    shown = f"[{host}]" if address is not None and address.version == 6 else host
    url = f"preview at http://{shown}:{port}/"
    if host.lower() == "localhost" or (address is not None and address.is_loopback):
        return url
    if address is not None and address.is_unspecified:
        return (
            f"preview on every interface, port {port}: open http://<this laptop's address>:{port}/ "
            "from a phone. Anyone on any network this laptop joins can reach it; "
            "prefer --host <the private router's address>"
        )
    return f"{url} (a phone on the same network opens this)"


_LOG_REFUSED = "{path}: cannot open the {noun} for appending: {reason}"


def check_log(path: Path, noun: str) -> None:
    """One clean exit line, as `open_log` gives, when the log at `path`
    cannot be appended to. Creates nothing, so a dry run checks it too."""
    if path.parent.is_file():
        code = errno.ENOTDIR
    elif not path.parent.is_dir():
        code = errno.ENOENT
    elif path.is_dir():
        code = errno.EISDIR
    elif not os.access(path if path.exists() else path.parent, os.W_OK):
        code = errno.EACCES
    else:
        return
    raise SystemExit(_LOG_REFUSED.format(path=path, noun=noun, reason=os.strerror(code)))


def open_log(path: Path, noun: str) -> TextIO:
    """A log opened for appending; one clean exit line if not."""
    try:
        return open(path, "a", encoding="utf-8")
    except OSError as exc:
        raise SystemExit(_LOG_REFUSED.format(path=path, noun=noun, reason=exc.strerror or exc)) from None


def teardown(drivers: list[SinkDriver], sinks: list[Sink]) -> None:
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
        if not driver.stop() and not driver.stop(timeout=GRACE_S):
            logger.warning(
                "sink %r is still sending after %.0fs; releasing its transport anyway", driver.name, GRACE_S,
            )
        sink.stop()


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
        # Removed rather than left in place: the tests run many sessions in
        # one process, and stacked handlers would duplicate every record.
        root.removeHandler(handler)
        root.setLevel(previous_level)
        root.propagate = previous_propagate
