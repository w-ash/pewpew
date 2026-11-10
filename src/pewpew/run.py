"""The live run behind `python -m pewpew run`: read and check the launch,
build the aura in dependency order, start it, and tear it down.

`Launch.read` turns the parsed command line into everything a run needs
and refuses what it cannot run with one clean exit line (a bad looks
file, a look it cannot start, a bad map, power cap, `--ddp` or
`--audio`, or a rig whose boards cannot take it); `--dry-run` stops there
with `Launch.plan`. `Run` builds the parts, each from the ones before it:

    stats -> features -> DDP sink, blink -> watchdog, keep-awake, health
    -> the aura (pewpew.aura.pipeline) -> rig reload -> sinks -> the paced loop

so every part gets what it needs at construction. The health monitor
reaches the rig reload, built after the aura, only once the run starts. The
watchdog is armed before the aura is built, so a look that hangs while it
builds still ends the run. The run starts in the looks file's current
look (else its first), and saves go to the same file; after a stall it
starts in the next look the stall marker does not name instead (`after_stall`). The map is `--map`
(`pewpew.lab.geometry.parse_geometry`), else `DEFAULT_MAP`. An arrangement
`--map` (a rig, `pewpew.rig.runtime`) gives the mapping, a power model,
the DDP boards (each controller with a host, unless `--no-ddp`), the
blink's fixtures and the preview's drawing, and reloads on save. Its
`power` block, with `--max-watts` and `--max-brightness` replacing its
values, is the power limit (`pewpew.power.PowerMeter`): the loop's last
`after` stage, behind the master, so every sink gets the capped frame.
On a rig it is always there, so the preview gets the `power` reading; a
limit that caps nothing runs only when a reading is due. The limit
follows each reload, rebuilt from the new rig with the same options. The
one exception is the preview's view of the rig: the rig reload pushes a
new map to the preview, and the preview reads the reload's status, so the
preview subscribes to the reload after both exist (`RigLive.listeners`).
The rig reload is also the aura control's `layout`: the page's layout
edit writes the rig file through it, in an attended run only, and the
page's Publish sends it to the Gallery at `--gallery` as a share.

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
A layer that raises makes `Renderer._contain` log a multi-line
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
import ipaddress
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

from pewpew import audit
from pewpew.audio import AudioFeatures, AudioSource, FeatureLog, LiveSource, ReplayFeatures
from pewpew.audio.inputs import NET, read_input
from pewpew.aura.book import LookBook, load_looks, route_reasons
from pewpew.aura.looks import Looks
from pewpew.aura.pipeline import build_aura_pipeline
from pewpew.awake import KeepAwake
from pewpew.compose import LayerError, Look
from pewpew.features import EventFeatures, FakeFeatures, FeatureSource
from pewpew.health import HealthMonitor
from pewpew.jsonfile import read_or_exit
from pewpew.lab.check import dims_reasons
from pewpew.lab.geometry import Geometry, parse_geometry
from pewpew.mapping import DEFAULT_MAP, dimensions
from pewpew.pace import PaceStats
from pewpew.power import PowerCap, PowerLimiter, PowerMeter
from pewpew.reload import Watch
from pewpew.render import RenderFailure
from pewpew.room.blink import Blink
from pewpew.room.live import RigLive
from pewpew.sinks.ansi import AnsiSink
from pewpew.sinks.ddp import Board, DdpSink, parse_board
from pewpew.sinks.preview import PreviewSink
from pewpew.sinks.sink import Sink, SinkDriver, stride
from pewpew.watchdog import TIMEOUT_S as WATCHDOG_S
from pewpew.watchdog import Stall, Watchdog, marker_path, take_marker

if TYPE_CHECKING:
    from pewpew.rig import CompiledRig

logger = logging.getLogger(__name__)

GRACE_S = 2.0  # extra seconds to wait on a mid-send worker before releasing
PREVIEW_RETRY_S = 5.0  # how often a preview that cannot listen tries again


@dataclass(frozen=True)
class Launch:
    """Everything a run reads and checks before anything starts: the
    looks file, with the look the run starts in current, the map (a
    synthetic one, or a rig and the bytes of its file), the power limit,
    the DDP sink and the `--audio` input. `follow` is whether the DDP sink
    streams to the rig's controllers. `read` refuses a launch it cannot
    run with one clean exit line, before a dry run returns, so the
    unattended checklist's attended dry run refuses what launchd's
    restarts would."""

    args: argparse.Namespace
    argv: list[str]  # the command line, as the audit log records it
    book: LookBook
    geometry: Geometry
    limiter: PowerLimiter | None
    ddp: DdpSink | None
    follow: bool
    audio: AudioSource | ReplayFeatures | None

    @property
    def mapping(self) -> np.ndarray:
        return self.geometry.mapping

    @property
    def rig(self) -> CompiledRig | None:
        return self.geometry.rig

    @classmethod
    def read(cls, args: argparse.Namespace, argv: list[str]) -> Launch:
        book = looks_book(args.looks, args.master_cap)
        geometry = map_geometry(args.map)
        rig, mapping = geometry.rig, geometry.mapping
        book = start_look(args.looks, book, mapping)
        limiter = power_limiter(args.max_watts, args.max_brightness, rig)
        boards = rig_boards(geometry.spec, rig, args.ddp) if rig is not None and not args.no_ddp else None
        follow = boards is not None
        ddp = None
        if follow or args.ddp:
            try:
                boards = boards if boards is not None else [parse_board(spec) for spec in args.ddp]
                # The loop feeds the sink every k-th tick: `--fps / k`, at most `--ddp-fps`.
                rate = args.fps / stride(args.fps, args.ddp_fps)
                ddp = DdpSink(boards, len(mapping), max_fps=rate)
            except ValueError as exc:
                raise SystemExit(str(exc)) from None
        elif args.dry_run and not (args.audio or "").startswith(NET):
            raise SystemExit(f"--dry-run: no controller of {geometry.spec} has a host, so nothing would stream; "
                             "give each a host, or add --ddp")
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
        return cls(args, argv, book, geometry, limiter, ddp, follow, audio)

    def plan(self) -> list[str]:
        """The per-board DDP plan and the input to open, as `--dry-run`
        prints them: for a rig's controllers, also each output as WLED's
        LED settings take it (`pewpew.rig.runtime.wled_plan`)."""
        lines: list[str] = []
        if self.ddp is not None and self.follow:
            from pewpew.rig.runtime import wled_plan

            assert self.rig is not None
            lines += wled_plan(self.rig, self.ddp.max_fps)
        elif self.ddp is not None:
            lines += self.ddp.plan()
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
        rig = launch.rig
        self.blink = None
        if rig is not None:
            from pewpew.rig.runtime import fixture_spans

            self.blink = Blink(fixture_spans(rig))
        # `--watchdog`, else on for an unattended run only, so a debugger stopped at
        # a breakpoint in a dev run is not killed; 0 is off.
        watchdog_s = (args.watchdog if args.watchdog is not None else WATCHDOG_S if args.unattended else 0.0) or None
        stall = take_marker(marker_path())
        # The look the run starts in, then the one that plays; what a stall marker names.
        self._started: str | None = None
        self.watchdog = Watchdog(
            watchdog_s, marker=marker_path(), earlier=stall, playing=self._playing, now=now,
        ) if watchdog_s is not None else None
        self.awake = KeepAwake() if args.keep_awake or args.unattended else None
        # The monitor also restarts caffeinate when it ends, so `awake` needs it.
        self.monitor = None
        if args.preview or self.ddp is not None or self.awake is not None:
            self.monitor = HealthMonitor(
                self.ddp, stats=self.stats, target=args.fps, awake=self.awake, watchdog=watchdog_s,
                names=self._board_names if rig is not None else None,
                argv=launch.argv, on_rebind=self._rebind_board if rig is not None else None,
                audio=self.audio.state if self.audio is not None else None,
            )
        # Armed before the stack is built, so a look that hangs in its setup or
        # its first render still ends the run.
        if self.watchdog is not None:
            self.watchdog.start()
        book = launch.book
        start, stalled = after_stall(launch, stall)
        self._started = start  # before the build, so a look that hangs in it is named
        # An unattended run leaves a failing layer out of the mix (`bypass`); its
        # error still reaches the status line.
        try:
            self.aura = build_aura_pipeline(
                book.looks[start], launch.mapping, seed=args.seed, features=features, bypass=args.unattended,
                now=now, master_cap=args.master_cap,
                looks_path=args.looks, book=book, trigger_log=self.trigger_log,
                trigger_log_max=int(args.trigger_log_max * 1_000_000), blink=self.blink,
                boards=self.monitor if self.ddp is not None else None,
                health=self.monitor.state if self.monitor is not None else None, accept_looks=args.accept_looks,
                gallery=args.gallery,
            )
        except (LayerError, ValueError) as exc:  # ValueError: a signal or route the stack cannot run
            if self.watchdog is not None:
                self.watchdog.stop()
            raise SystemExit(f"{args.looks}: cannot start look {start!r}: {exc}") from None
        if start != book.current:
            self.looks.leave()  # runs as a sent look does: no look is current, and the file keeps its own
        if stalled is not None:
            print(stalled, file=sys.stderr, flush=True)
            self.looks.error = stalled
        if args.armed:
            self.aura.triggers.arm(True, "launch")  # applied and logged at the first tick
        # The plan's rule is "refused unattended unless --accept-looks", and the
        # command line refuses --accept-looks with --unattended.
        self.rig = None if rig is None else RigLive(
            Path(args.map), rig, launch.geometry.data, self.aura.fader, self.aura.calls,
            ddp=self.ddp, argv=launch.argv, blink=self.blink, watch=watch, follow=launch.follow,
            edits=not args.unattended,
        )
        # The power limit, and on a rig its reading for the preview.
        self.power = PowerMeter(args.fps, launch.limiter) if launch.limiter is not None else None
        if self.rig is not None:
            self.aura.control.layout = self.rig  # before any sink reads the capabilities
            self.rig.listeners.append(self._relimit)
        sources: list[tuple[Source, Any]] = [
            ("reload", self.rig), ("render", self.aura.fader), ("looks", self.looks),
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
                max_height=size.lines,
            )
            self.outputs.append((self.ansi, self.ansi.start))
        self.preview = None
        self.preview_retry: threading.Thread | None = None
        self._stopping = threading.Event()
        if args.preview:
            self.preview = PreviewSink(
                launch.mapping, host=args.host or "127.0.0.1", port=args.port, status=status,
                control=self.aura.control, power=self._power_reading, now=now, **self._drawing(rig),
            )
            self.outputs.append((self.preview, self._start_preview))
            if self.rig is not None:
                self.rig.listeners.append(self._show_rig)
        if self.ddp is not None:
            self.outputs.append((self.ddp, self._start_ddp))
        self.drivers = [
            SinkDriver(sink.send, name=type(sink).__name__, every=stride(args.fps, sink.max_fps))
            for sink, _ in self.outputs
        ]
        # Each frame: the audio, then the aura's own stages, before it renders;
        # after it, the aura's, then the power limit, behind the master.
        self.loop = self.aura.loop(
            args.fps, stats=self.stats,
            before=[self.audio.before_frame] if self.audio is not None else [],
            after=[self.power] if self.power is not None else [],
            on_frame=[*self.drivers, *([self.watchdog.beat] if self.watchdog is not None else [])],
        )

    def _playing(self) -> str | None:
        """The name of the look that plays: the aura's, else the one the run
        started in (a start after a stall plays as a sent look). Any thread."""
        looks = self.aura.looks if hasattr(self, "aura") else None
        return (looks.source if looks is not None else None) or self._started

    @property
    def looks(self) -> Looks:
        """The aura's looks: a run always has its looks file."""
        looks = self.aura.looks
        assert looks is not None
        return looks

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
        if self.looks.book.current is not None:
            self.looks.begin()
        self.aura.triggers.begin_run(
            seed=self.args.seed, fps=self.args.fps, look=self.looks.book.current,
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
        if self.rig is not None:
            self.rig.start()
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
        self.aura.calls.close()
        if self.trigger_log is not None:
            # A flush that fails here must not skip the teardown.
            with contextlib.suppress(OSError):
                self.trigger_log.close()
        if self.feature_log is not None:
            self.feature_log.close()
        if self.rig is not None:
            self.rig.stop()
        if self.preview_retry is not None:
            self.preview_retry.join()  # so no listener opens after the teardown
        teardown(self.drivers, [sink for sink, _ in self.outputs])

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
        extra = {} if self.rig is None else {"map": str(self.args.map)}
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
        """The controller ids of the sink's boards, for the health monitor (`RigLive.board_names`)."""
        return self.rig.board_names() if self.rig is not None else ()

    def _rebind_board(self, controller: str, address: str) -> str | None:
        """Point a controller at `address`, for the health monitor (`RigLive.rebind`)."""
        assert self.rig is not None, "only a run on a rig rebinds a board"
        return self.rig.rebind(controller, address)

    def _drawing(self, rig: CompiledRig | None) -> dict[str, Any]:
        """The preview's `room`, `rig` and `plan_image` for `rig`, or none."""
        if rig is None:
            return {}
        from pewpew.rig.runtime import plan_view, rig_view

        image = None if rig.plan is None else Path(self.args.map).parent / rig.plan.image  # beside the rig file
        return {"room": plan_view(rig), "rig": rig_view(rig), "plan_image": image}

    def _power_reading(self) -> dict[str, float] | None:
        """The latest power reading, for the preview. Any thread."""
        return self.power.reading if self.power is not None else None

    def _relimit(self, rig: CompiledRig) -> None:
        """Cap a reloaded rig as the run caps its launch rig. Loop thread.
        A cap that cannot be made keeps the old limit, whose frames of
        another size go out black (`PowerMeter`), never uncapped."""
        assert self.power is not None
        try:
            self.power.limiter = rig.limiter(power_cap(self.args.max_watts, self.args.max_brightness, rig))
        except ValueError:
            logger.exception("the reloaded map's power cap cannot be made; the old one holds")

    def _show_rig(self, rig: CompiledRig) -> None:
        """Draw a reloaded rig on the preview. Loop thread."""
        assert self.preview is not None
        self.preview.remap(rig.mapping, **self._drawing(rig))


def map_geometry(spec: str | None) -> Geometry:
    """The geometry of `--map` (`parse_geometry`), else `DEFAULT_MAP`, with
    one clean exit line for a file that does not compile or has no pixels.
    A rig's issues, and the warning of a room map file, go to stderr. The
    rig stack is imported only for a rig file, so a run on any other map
    never loads it."""
    spec = DEFAULT_MAP if spec is None else spec
    notices: list[str] = []
    try:
        geometry = parse_geometry(spec, notices=notices)
    except ValueError as exc:
        raise SystemExit(f"--map {exc}") from None
    for notice in notices:
        print(f"{spec}: warning: {notice}", file=sys.stderr, flush=True)
    for issue in geometry.rig.issues if geometry.rig is not None else ():
        where = f" ({issue.ref})" if issue.ref else ""
        print(f"{spec}: {issue.level}: {issue.message}{where}", file=sys.stderr, flush=True)
    return geometry


def rig_boards(spec: str, rig: CompiledRig, ddp: list[str]) -> tuple[Board, ...] | None:
    """The DDP boards of `rig`'s controllers (`ddp_targets`), or None when
    no controller has a host. One clean exit line when `--ddp` (`ddp`) is
    given too, or the rig breaks a pixel cap or has a wired controller
    with no host (`stream_refusals`)."""
    from pewpew.rig.runtime import ddp_targets, stream_refusals

    if all(c.host is None for c in rig.controllers):
        return None
    if ddp:
        raise SystemExit(
            f"--ddp: {spec} gives its controllers' hosts; drop --ddp to stream to them, "
            "or remove the hosts from the file to stream to the --ddp boards"
        )
    if reasons := stream_refusals(rig):
        raise SystemExit(f"--map {spec}: the boards cannot take this map, so nothing streams: {'; '.join(reasons)}")
    return ddp_targets(rig)


def power_limiter(
    max_watts: float | None, max_brightness: float | None, rig: CompiledRig | None
) -> PowerLimiter | None:
    """The run's power limit (`power_cap`): on the arrangement `rig` always,
    for its power reading, else None when it caps nothing. A watt cap needs
    `rig`, whose fixtures give the power model; the command line refuses
    one without it (`python -m pewpew`)."""
    try:
        cap = power_cap(max_watts, max_brightness, rig)
    except ValueError as exc:
        raise SystemExit(f"bad power cap: {exc}") from None
    if rig is not None:
        return rig.limiter(cap)
    return PowerLimiter(cap) if cap.caps else None


def power_cap(max_watts: float | None, max_brightness: float | None, rig: CompiledRig | None) -> PowerCap:
    """The cap of the arrangement `rig`, if any, with each value given
    replacing its own. Raises ValueError."""
    base = PowerCap() if rig is None else rig.power_cap
    return PowerCap(
        base.max_watts if max_watts is None else max_watts,
        base.max_brightness if max_brightness is None else max_brightness,
    )


def looks_book(path: Path, cap: float) -> LookBook:
    """Load and check the looks file at launch. A missing or malformed file
    is one clean exit line naming it; a look whose route reaches no knob is
    a warning, and its recall refuses it as it does mid-run."""
    book = read_or_exit(path, "looks file", lambda: load_looks(path, cap=cap))
    for problem in route_reasons(book):
        logger.warning("%s: %s", path, problem)
    return book


def start_look(path: Path, book: LookBook, mapping: np.ndarray) -> LookBook:
    """`book` with the look the run starts in current: its current look,
    else its first. One clean exit line when the file holds no look, or the
    look cannot start on `mapping` (`check_map`)."""
    name = book.current if book.current is not None else next(iter(book.looks), None)
    if name is None:
        raise SystemExit(f"{path}: the looks file holds no look")
    try:
        check_map(book.looks[name], mapping)
    except ValueError as exc:
        raise SystemExit(f"{path}: cannot start look {name!r}: {exc}") from None
    return book.with_current(name)


def check_map(look: Look, mapping: np.ndarray) -> None:
    """Raise ValueError saying why `look`'s programs cannot run on
    `mapping`, with a map that can (`map_hint`)."""
    if reasons := dims_reasons(look.layers, dimensions(mapping)):
        reason = "; ".join(reasons)
        raise ValueError(f"{reason}{map_hint(reason)}")


def after_stall(launch: Launch, stall: Stall | None) -> tuple[str, str | None]:
    """The look the run starts in, and what to say about it. After a stall
    (`stall`, the marker, pewpew.watchdog), the run does not start in a look
    the marker names, or in the launch's current one when it names none: it
    starts in the first of the launch's current look and the others in the
    idle cycle's order after it (`LookBook.after`) that is not named and
    can start, which the run plays as a sent look, so the file's `current`
    stays the operator's. With none, it starts the current look again."""
    book = launch.book
    current = book.current
    assert current is not None, "the launch made the look it starts in current"
    if stall is None:
        return current, None
    stalled = stall.looks or (current,)
    named = ", ".join(repr(name) for name in stalled)
    for name in (current, *book.after(current)):
        if name in stalled:
            continue
        try:
            check_map(book.looks[name], launch.mapping)
        except ValueError as exc:
            logger.warning("after the stall, look %r cannot start either: %s", name, exc)
            continue
        return name, f"the last run stalled in {named}, so {name!r} runs"
    if len(stalled) == 1:
        return current, f"the last run stalled in {named}, the only look that starts, so it runs again"
    return current, f"the last run stalled in {named}, no other look starts, so {current!r} runs again"


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
    nothing."""
    found = re.search(r"needs a map of ([\d ]+(?:or [\d ]+)?)dimensions", reason)
    if found is None:
        return ""
    return "; run with " + " or ".join(f"--map {_MAPS[d]}" for d in found[1].replace("or", "").split() if d in _MAPS)


def status_line(*sources: tuple[Source, Any]) -> Callable[[], Status | None]:
    """The `status` supplier: the `Status` of the first `.error` that is
    set, in the order given, each source as (tag, object), or None. The run
    puts the rig file's reload first: its outcome is the freshest thing the
    operator acted on. A render error, which the room shows, goes before a
    failed look recall.

    Reads each `.error` once: this runs on a SinkDriver worker while the loop
    thread clears the error on the first healthy frame, so a test and a
    second read could race and paint a status reading `None`.
    """

    def status() -> Status | None:
        for tag, source in sources:
            err = source.error
            if err:
                return Status(tag, str(err), err.path if isinstance(err, RenderFailure) else None)
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
