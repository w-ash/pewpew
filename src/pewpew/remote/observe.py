"""Watch a running engine without changing it: `python -m pewpew observe URL`.

`capture` connects to an engine's preview port and reads its state and
the frames it streams for some seconds of engine time. `observe` reduces
a capture to an `Observation`: the aura, status, params and health the
engine sent last, `pewpew.metrics` over the frames, and on request a
contact sheet (`pewpew.sheet`) at the map's positions. Both are tier 0
(CLAUDE.md T-7): they send the engine no message, only the websocket's
own opening and closing handshakes.

Every number is approximate, and an Observation says so. The preview
sends 8-bit frames at display gamma, which `from_display_u8` takes back
to linear light less what quantization lost; it sends at most its
`max_pixels` of a map, evenly spaced (`sent_pixels` of `total_pixels`);
and it drops the frames a slow client cannot take (`dropped`).

Time is engine time, from the frame headers: the window runs from the
first frame to `seconds` after it, and the rate is the frames over the
engine time they span (`span`, the first frame to the last). The
metrics' own `seconds` is frames / fps, as for a rendered sequence, since
each frame stands for one slot. The wall clock bounds only the waits: `timeout`
seconds for the connection and the hello, then `seconds + timeout` for
the frames.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

from pewpew.cli_args import GONE, OK, PROBLEMS, parsed_by, png_path, positive
from pewpew.jsonfile import write_atomic
from pewpew.metrics import Metrics, measure
from pewpew.remote.client import Client, Frame, Unreachable, engine_url
from pewpew.result import Result
from pewpew.sheet import Sheet, contact_sheet
from pewpew.sinks.sink import from_display_u8

WATCH_S = 2.0  # engine time to watch by default
MAX_FRAMES = 600  # frames kept at most: 10 s at 60 fps
TIMEOUT_S = 5.0  # wall time to wait for the engine past what `seconds` needs
FADED = ("a crossfade ran in the window, so the metrics mix the outgoing look with the incoming one; "
         "observe again once the aura state's fading is false")


@dataclass(frozen=True)
class Observation(Result):
    """What `observe` saw of a running engine (see the module docstring).
    Frozen but not slotted, so an MCP tool can return it as structured
    content; `to_json` is its JSON form (pewpew.result)."""

    url: str
    build: str | None  # the build stamp of the page the engine serves
    frames: int  # frames in the window
    span: float  # engine time from the first frame in the window to the last: (frames - 1) / fps
    fps: float  # frames per second of engine time; 0 for fewer than two frames
    dropped: int  # frames the engine sent in the window that did not arrive here
    sent_pixels: int  # pixels a frame carries
    total_pixels: int  # pixels in the engine's map
    approximate: bool = True  # always: 8-bit display-gamma frames, maybe decimated
    status: dict[str, Any] | None = None  # the engine's error, as the `status` message gives it
    aura: dict[str, Any] | None = None  # the aura state, as the `aura` message gives it
    params: dict[str, Any] | None = None  # every param value, by full path, as the `params` message gives it
    health: dict[str, Any] | None = None  # None when the run has no health monitor
    faded: bool = False  # a crossfade ran in the window, so the frames mix two looks
    metrics: Metrics | None = None  # None for fewer than two frames
    sheet: str | None = None  # where the contact sheet was written
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Capture:
    """What one connection read: the last text message of each type, the
    frames of the window, oldest first, and what cut the window short."""

    url: str
    latest: Mapping[str, dict[str, Any]]
    frames: tuple[Frame, ...]
    notes: tuple[str, ...] = ()
    faded: bool = False  # an aura state of the window said a crossfade ran

    @property
    def view(self) -> dict[str, Any]:
        """The map the frames are drawn on: the hello, or the last layout."""
        return self.latest.get("layout") or self.latest["hello"]

    @property
    def positions(self) -> np.ndarray:
        """(n, 3) float64: the position of each pixel a frame carries."""
        return np.asarray(self.view["positions"], dtype=np.float64).reshape(-1, 3)

    @property
    def span(self) -> float:
        """Engine time from the first frame to the last."""
        return self.frames[-1].t - self.frames[0].t if self.frames else 0.0

    @property
    def fps(self) -> float:
        """Frames per second of engine time; 0 without two frames at
        different times."""
        span = self.span
        return (len(self.frames) - 1) / span if span > 0 else 0.0

    @property
    def dropped(self) -> int:
        """Frames between the first and the last that did not arrive: the
        gaps in their sequence numbers."""
        return sum((b.seq - a.seq - 1) % 2**32 for a, b in pairwise(self.frames))

    def linear(self) -> np.ndarray:
        """The frames as (F, n, 3) float32 approximate linear light."""
        rgb = np.array([f.rgb for f in self.frames], np.uint8).reshape(len(self.frames), self.view["n"], 3)
        return from_display_u8(rgb, self.latest["hello"]["display_gamma"])

    def sheet(self) -> Sheet | None:
        """The contact sheet of the frames at the map's positions, or None
        without two frames at different engine times."""
        return contact_sheet(self.linear(), self.positions, self.fps) if self.fps > 0 else None

    def observation(self, sheet: Path | None = None) -> Observation:
        """The capture reduced to an Observation. With `sheet`, the contact
        sheet (`Capture.sheet`) is written there as a PNG, when the frames
        allow one; a sheet that cannot be written is a warning."""
        fps, metrics, warnings = self.fps, None, self.notes
        if self.faded:
            warnings += (FADED,)
        if fps > 0:
            metrics = measure(self.linear(), fps)
            if metrics.flash_safe is None:
                warnings += (f"{metrics.seconds:.2f} s of frames: flash safety needs a window of 1 s or more",)
            if sheet is not None and (drawn := self.sheet()) is not None:
                try:
                    write_atomic(sheet, drawn.png)
                except OSError as exc:
                    warnings += (f"cannot write the sheet to {sheet}: {exc.strerror or exc}",)
                    sheet = None
        else:
            sheet = None
            warnings += (f"metrics and a sheet need two frames at different engine times; got {len(self.frames)}",)
        values = self.latest.get("params")
        return Observation(
            url=self.url,
            build=self.latest["hello"].get("build"),
            frames=len(self.frames),
            span=round(self.span, 4),
            fps=round(fps, 4),
            dropped=self.dropped,
            sent_pixels=self.view["n"],
            total_pixels=self.view["total"],
            status=_body(self.latest.get("status")),
            aura=_body(self.latest.get("aura")),
            params=None if values is None else values["values"],
            health=_body(self.latest.get("health")),
            faded=self.faded,
            metrics=metrics,
            sheet=None if sheet is None else str(sheet),
            warnings=warnings,
        )


def capture(
    url: str, seconds: float = WATCH_S, *, max_frames: int = MAX_FRAMES, timeout: float = TIMEOUT_S
) -> Capture:
    """Read the engine at `url` (`engine_url` takes it) for `seconds` of
    engine time or `max_frames` frames, whichever comes first.

    Raises Unreachable when nothing answers, or no hello comes, within
    `timeout` seconds, and ValueError for a bad argument. Frames that stop
    coming end the window `timeout` seconds past `seconds`, with a note.
    """
    if not (math.isfinite(seconds) and seconds > 0):
        raise ValueError(f"seconds must be a number above 0, got {seconds!r}")
    if max_frames < 2:
        raise ValueError(f"max_frames must be 2 or more, so the frames span some time; got {max_frames}")
    url = engine_url(url)
    fades: list[bool] = []

    def note(message: dict[str, Any]) -> None:
        if message["type"] == "aura" and message.get("fading"):
            fades.append(True)

    # Held, so a message that comes after the window cannot change what was read.
    with Client(url, keep_frames=max_frames, open_timeout=timeout, on_text=note) as client, client.hold():
        client.hello(timeout)
        whole = client.wait(lambda: _closes(client.frames, seconds, max_frames), seconds + timeout)
        cut = None if whole else "the engine closed the connection" if client.ended else "the frames stopped"
        seen = Capture(url, dict(client.latest), _window(client.frames, seconds), faded=bool(fades))
        remapped = client.counts["layout"] > 0
    notes = []
    if cut is not None:
        notes.append(f"{cut} {seen.span:.2f} s into the {seconds:g} s window, after {len(seen.frames)} frames "
                     f"(waited {seconds + timeout:g} s): check the engine's status and its render loop")
    elif len(seen.frames) >= max_frames and seen.span < seconds:
        notes.append(f"stopped at max_frames={max_frames}, {seen.span:.2f} s into the {seconds:g} s window")
    if remapped:
        notes.append("the map changed during the capture; the frames are those drawn on the new one")
    return replace(seen, notes=tuple(notes))


def observe(
    url: str,
    seconds: float = WATCH_S,
    *,
    max_frames: int = MAX_FRAMES,
    sheet: Path | None = None,
    timeout: float = TIMEOUT_S,
) -> Observation:
    """`capture` reduced to an Observation. With `sheet`, the contact
    sheet is written there as a PNG, when the frames allow one."""
    return capture(url, seconds, max_frames=max_frames, timeout=timeout).observation(sheet)


def _closes(frames: Sequence[Frame], seconds: float, max_frames: int) -> bool:
    """Whether `frames` hold a whole window: `seconds` of engine time past
    the first frame, or `max_frames` frames."""
    return len(frames) >= max_frames or (bool(frames) and frames[-1].t >= frames[0].t + seconds)


def _window(frames: Sequence[Frame], seconds: float) -> tuple[Frame, ...]:
    """The frames from the first one to `seconds` of engine time after it."""
    return tuple(f for f in frames if f.t < frames[0].t + seconds) if frames else ()


def _body(message: dict[str, Any] | None) -> dict[str, Any] | None:
    """A state message's fields, without its `type`."""
    return None if message is None else {k: v for k, v in message.items() if k != "type"}


# ---- the command line ----------------------------------------------------------


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `observe` subcommand to the CLI."""
    p = sub.add_parser("observe", help="watch a running engine's preview and measure what it shows (read-only)")
    p.add_argument("url", type=parsed_by(engine_url), metavar="URL",
                   help="the engine's preview address, as its `preview at` line prints it, or ws://HOST:PORT/")
    p.add_argument("--seconds", type=positive("seconds"), default=WATCH_S, metavar="S",
                   help=f"engine time to watch, in seconds (default {WATCH_S:g}; at most {MAX_FRAMES} frames)")
    p.add_argument("--sheet", type=png_path, default=None, metavar="PATH",
                   help="write a contact sheet of the frames to PATH as a PNG")
    p.add_argument("--json", action="store_true",
                   help="print the observation as one JSON document; diagnostics go to stderr")
    p.set_defaults(cli=lambda args, argv: cli(args))


def cli(args: argparse.Namespace) -> int:
    """Run `observe`. Exit 0 with metrics and any sheet asked for, 1
    without them (fewer than two frames, or a sheet not written), 3 when
    the engine does not answer."""
    try:
        seen = observe(args.url, args.seconds, sheet=args.sheet)
    except Unreachable as exc:
        print(f"observe: {exc}", file=sys.stderr)
        return GONE
    for warning in seen.warnings:
        print(f"observe: {warning}", file=sys.stderr)
    print(json.dumps(seen.to_json(), indent=2) if args.json else report(seen))
    complete = seen.metrics is not None and (args.sheet is None or seen.sheet is not None)
    return OK if complete else PROBLEMS


def report(seen: Observation) -> str:
    """The observation as lines of text, for a person."""
    head = (
        f"{seen.url}: {seen.frames} frames spanning {seen.span:.2f} s of engine time at {seen.fps:.1f} fps "
        f"({seen.dropped} dropped), {seen.sent_pixels} of {seen.total_pixels} pixels; approximate"
    )
    lines = [head]
    if seen.aura is not None:
        lines.append(f"master {seen.aura.get('master')}" + (", blackout" if seen.aura.get("blackout") else ""))
        lines += [f"layer {line}" for line in _layer_lines(seen.aura, seen.params or {})]
    if seen.status is not None and seen.status.get("error"):
        lines.append(f"error in {seen.status.get('source')}: {seen.status['error']}")
    if seen.metrics is not None:
        lines += [f"{name}: {value}" for name, value in seen.metrics.to_json().items()]
        safe = seen.metrics.flash_safe
        lines.append(f"flash_safe: {'unknown (a window under 1 s)' if safe is None else safe}")
    if seen.sheet is not None:
        lines.append(f"sheet: {seen.sheet}")
    return "\n".join(lines)


def _layer_lines(aura: Mapping[str, Any], params: Mapping[str, Any]) -> list[str]:
    """Each layer of the running look, bottom first: its id, what its
    nodes show, and its mix from `params`."""
    lines = []
    for layer in (aura.get("stack") or {}).get("layers", []):
        lid = layer.get("id")
        labels = ", ".join(str(node.get("label")) for node in layer.get("nodes", []))
        mix = {name: params.get(f"layers.{lid}.{name}") for name in ("blend", "opacity", "enabled")}
        off = "" if mix["enabled"] is not False else ", off"
        lines.append(f"{lid}: {labels} ({mix['blend']} at {mix['opacity']}{off})")
    return lines
