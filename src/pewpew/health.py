"""Aura health: each board's `/json/info`, the render loop's rate, and the
sleep assertion, for the page's health panel and the run's log.

Tier 0, read-only (CLAUDE.md T-7), so it runs alongside the aura. One
`HealthMonitor` thread polls the boards one at a time, each board every
`period` seconds (default 6, inside the 5-10 s band; Home Assistant's WLED
integration polls every 10 s), with a short timeout. It reads `/json/info`
only, never the full `/json`: polling that stalled output every 10 s
(wled/WLED#3411). Nothing here runs on the render loop's thread: the loop
reads nothing from the monitor, and `state()` returns the last snapshot
without waiting on a request in flight. The clock, the fetch, the sender
address and the resolver are injected, so tests run without a network.

Fields read from `/json/info` (WLED v16.0.1 `wled00/json.cpp`): `live` and
`lip` (realtime on, and its source address), `leds.fps` and `leds.count`,
`wifi.rssi` and `wifi.channel`, `uptime` (seconds since boot), `freeheap`,
`ver`, and `resetReason0`, which stock builds leave out: WLED sends it only
when built with `WLED_DEBUG` (`json.cpp:840-844`), so on a stock build a
brownout shows only as an `uptime` drop.

A board's level is the worst of its checks (`BoardHealth.assess`, against
the thresholds below). The `live`, `lip` and fps checks judge only a reply
to a poll sent at least `SETTLE_S` after the monitor first saw a DDP frame
sent: a poll made before the stream reached the board says nothing about
the stream. `FPS_WARN` is the Wi-Fi bench's "held" ratio
(`bench/bench_wifi.py`); the RSSI and heap figures are engineering choices,
not measured limits. The render loop warns below `LOOP_WARN` of its target
rate, and the sleep assertion when it was asked for and is not held. Each
board, loop and sleep row carries `fix`: one sentence on what to do about
its most urgent check, or None when nothing needs doing.

Addressing. UDP gets no answer, so a frame sent to a board's old address
after a power cycle fails silently: the board leaves realtime mode after
its 2500 ms timeout and shows its own look, WLED's default orange. A board
named by mDNS (`pewpew-1.local`, `pewpew.sinks.ddp.board_host`) is looked
up here, never on the loop: when it is first polled, and again whenever it
stops answering or another MAC answers at its address, so a board that
comes back on a new DHCP address is followed (Home Assistant updates a
WLED host when the same MAC appears at a new address). Pointing the DDP
sink at a new address is tier-1 actuation: an audit record
(`ddp-readdress`) is written first, and no frame goes there if that fails.

Audio. With `--audio`, the input gets a row too, judged from the
features' `state()` (pewpew.audio.AudioFeatures) each step: lost (with
why, and whether another program holds the input), only exact zeros for
`ZEROS_S` (macOS may deny the microphone), held hops past the tracker's
degraded share, clipping, and an overflow in the last `OVERFLOW_WARN_S`.
A capture node (pewpew.audio.net) also has its `node` numbers in the row,
and is judged on the share of samples lost over the last 10 s, its
signal, and a reboot in the last `REBOOT_WARN_S`; its drift is reported,
never judged. The thresholds are inferences, for RA-28's bench milestone
to tune. The
page draws no audio row, so the row's level stays out of the snapshot's
`level`, which the page's chip shows: the health message and the run's log
carry it.

Find boards. `scan` asks every address of this laptop's /24 for
`/json/info` (`pewpew.wled.sweep`) and lists the WLED boards that answer;
`rebind` hands one of them to `on_rebind`, which writes it into the room
file as a board's host (`pewpew.room.live`). A board named by mDNS is not
rebound: the name already follows it.
"""

from __future__ import annotations

import ipaddress
import logging
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pewpew import audit, wled
from pewpew.audio.beat import DEGRADED_ABOVE
from pewpew.audio.net import LOSS_S
from pewpew.audio.wire import HOLD_S
from pewpew.errors import unknown
from pewpew.jsonfile import is_number
from pewpew.pace import PaceStats
from pewpew.sinks.ddp import Board, DdpSink, is_ipv4
from pewpew.wled import PRIVACY, SCAN_TIMEOUT_S, TIMEOUT_S, failure, format_mac, no_route

logger = logging.getLogger(__name__)

PERIOD_S = 6.0  # each board polled this often
STEP_S = 1.0  # the monitor's own tick: loop rate and sleep state refresh this often

FPS_WARN, FPS_BAD = 0.9, 0.5  # leds.fps over the sent rate
RSSI_WARN, RSSI_BAD = -70, -80  # dBm
HEAP_WARN, HEAP_BAD = 30_000, 15_000  # bytes
REBOOT_WARN_S = 600.0  # a reboot keeps the board at warn this long
LOOP_WARN = 0.9  # loop fps over its target
SETTLE_S = 1.0  # the stream checks wait this long after the first frame sent
ZEROS_S = 5.0  # an input that reads only exact zeros this long is flagged [inf]
OVERFLOW_WARN_S = 60.0  # an overflow keeps the input at warn this long [inf]
CLIP_DB = -0.1  # a peak at or above this, in dBFS, is clipping [inf]
LOSS_WARN = 0.01  # a node's lost share over which features on the node come back up (RA-28 §6) [inf]

LEVELS = ("pending", "ok", "warn", "bad")


def extract(info: dict) -> dict:
    """The health fields of one `/json/info` reply; a field the board left
    out, or sent as another type, is None."""
    leds, wifi = _dict(info.get("leds")), _dict(info.get("wifi"))
    reset = info.get("resetReason0")
    return {
        "fps": _number(leds.get("fps")),
        "count": _number(leds.get("count")),
        "rssi": _number(wifi.get("rssi")),
        "channel": _number(wifi.get("channel")),
        "uptime": _number(info.get("uptime")),
        "live": live if isinstance(live := info.get("live"), bool) else None,
        "lip": _text(info.get("lip")),
        "freeheap": _number(info.get("freeheap")),
        "ver": _text(info.get("ver")),
        "reset_reason": reset if is_number(reset) or isinstance(reset, str) else None,
    }


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _number(value: object) -> int | float | None:
    return value if is_number(value) else None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _worst(levels: Sequence[str]) -> str:
    return max(levels, key=LEVELS.index, default="ok")


# A check that applies: (fix rank, level, reason, fix).
_Found = tuple[int, str, str, str]


def _fix(found: list[_Found]) -> str:
    """The fix of the worst check, and among those of the lowest rank."""
    return min(found, key=lambda f: (-LEVELS.index(f[1]), f[0]))[3]


def _log_change(what: str, before: str, after: str, reasons: list[str]) -> None:
    """Log a change of level, except a first verdict of ok."""
    if after != before and not (before == "pending" and after == "ok"):
        log = logger.info if after == "ok" else logger.warning
        log("%s %s -> %s%s", what, before, after, f": {'; '.join(reasons)}" if reasons else "")


def _band(found: list[_Found], rank: int, value: float, warn: float, bad: float, why: str, fix: str) -> None:
    """Add the check at "bad" below `bad`, else at "warn" below `warn`."""
    if value < bad:
        found.append((rank, "bad", why, fix))
    elif value < warn:
        found.append((rank, "warn", why, fix))


# The program macOS's Local Network setting lists for pewpew: the Python
# that runs it under launchd, or the terminal app that started it. A name,
# never a path: the sentence crosses the preview socket.
_APP = f"{Path(sys.executable).resolve().name if sys.executable else 'Python'} (or the terminal app that runs it)"
_FIX_MDNS = "name it by its mDNS name in the room file (\"pewpew-1.local\") so pewpew follows it."
_FIX_MOVED_NAMED = ("{host} still resolves to this address; pewpew looks it up again on "
                    "every poll and follows the board once its new address is known.")
_FIX_MOVED = "The board moved and another device took its address. {find}, or " + _FIX_MDNS
_FIX_GONE_NAMED = ("The board may be off or rebooting; pewpew looks {host} up again on every poll. "
                   "If it does not come back, check its power and Wi-Fi, and that its mDNS address in "
                   "WLED's WiFi settings is still {label}.")
_FIX_GONE = "The board may be off, rebooting, or on a new address after a power cycle. {find}, or " + _FIX_MDNS
_FIX_NO_ROUTE = (" \"No route to host\" while the board's own page opens in a browser means macOS "
                 f"blocks {_APP} from the local network ({PRIVACY}).")
_FIX_NOT_LIVE = ("It shows its own look (WLED's default is orange): pewpew's packets are not reaching "
                 f"it. Check that macOS lets {_APP} reach the local network ({PRIVACY}), "
                 "and that WLED's Sync settings receive UDP realtime on the board's DDP port.")
_FIX_FPS = ("The board shows fewer frames than pewpew sends: check its Wi-Fi signal and channel, "
            "or lower --ddp-fps.")
_FIX_RSSI = "Move the board or the router closer, or clear what stands between them."
_FIX_HEAP = "Turn off the WLED features pewpew does not use (the unattended checklist lists them)."
_FIX_COUNT = ("Set the LED count in WLED's LED Preferences to {expected}, the pixels pewpew streams "
              "to this board.")
_FIX_COUNT_REBOOTED = ("It rebooted and its LED count is wrong, so WLED may have reset its settings: "
                       "restore its backup in an attended session (boards restore, --dry-run first), "
                       "or set the LED count in WLED's LED Preferences to {expected}.")
_FIX_REBOOT = ("It rebooted. If it keeps rebooting it may be browning out: see the unattended checklist's v16 "
               "brownout fixes (a 3V3 capacitor, TX power 8.5 dBm or lower, stable USB power).")
_FIX_DARK = ("If the bars stay dark, the fault is off the network: check the LED supply and the data "
             "wire, then blink a fixture.")
_FIX_LOOP = "Check the laptop is on AC and nothing else is busy."
_FIX_AWAKE = ("pewpew restarts caffeinate itself; if it stays off, restart pewpew, or under launchd: "
              "launchctl kickstart -k gui/$UID/local.pewpew.aura")
_FIX_AUDIO_ERROR = ("The analysis failed, so the last good frame stands; the run's log has the traceback. "
                    "Restart pewpew if it stays.")
_FIX_AUDIO_LOST = ("Check that {input} is plugged in and on. pewpew opens it again by that exact name once it "
                   "is back (`audio list` shows the names); meanwhile the levels are silent and the beat keeps "
                   "its tempo.")
_FIX_AUDIO_BUSY = " Another program holds it: quit that program (on a Pi, PipeWire may hold the card)."
_FIX_AUDIO_ZEROS = ("A quiet room never gives exact zeros: macOS may deny pewpew the microphone. Allow "
                    f"{_APP} under System Settings → Privacy & Security → Microphone, then restart pewpew "
                    "(docs/audio.md). A digital input may instead be muted at its source.")
_FIX_AUDIO_HELD = ("The input drops samples, so the beat free-runs: check its cable and port, and that "
                   "nothing else loads the laptop.")
_FIX_AUDIO_CLIP = "Turn the input's gain, or the mixer's send, down until the peak stays under 0 dBFS."
_FIX_AUDIO_OVERFLOW = "The loop read the input too late and lost samples, so the beat restarted its fit. " + _FIX_LOOP
_FIX_NODE_LOST = ("Check that the node is powered and on the private router: its LED is blue on the network and "
                  "green while it streams. pewpew looks it up again and subscribes once it answers; meanwhile "
                  "the levels are silent and the beat keeps its tempo.")
_FIX_NODE_BUSY = f" Another host holds its stream: stop that run, and the node frees it {HOLD_S:g} s later."
_FIX_NODE_LOSS = ("Packets from the node go missing: move it or the router closer, and check the private router's "
                  "channel (docs/unattended-checklist.md §2).")
_FIX_NODE_RSSI = "Move the node or the router closer, or clear what stands between them."
_FIX_NODE_REBOOT = ("If it keeps rebooting, check its USB power; a task_wdt, panic or send-stall reason is a "
                    "firmware fault: keep its UART log for the bench (docs/audio.md §9).")
_FIX_NODE_OVERFLOW = ("The node's I2S reader fell behind and dropped samples, which the beat holds over. Unless "
                      "someone held its BOOT button, reboot the node and keep its UART log.")


def _find(board: str | None, lost: bool) -> str:
    """How the page finds a board's new address: the scan, then the "use
    for" button it offers a lost room board (`BoardHealth.lost`); before
    that, the scan is only the next step if it stays away."""
    if board is None:
        return 'Tap "find boards" for its new address, then run with that address'
    return f'Tap "find boards", then "use for {board}"' if lost else 'If it stays unreachable, tap "find boards"'


@dataclass
class BoardHealth:
    """What the monitor knows about one board, and its level."""

    host: str
    expected: int  # pixels streamed to it
    name: str | None = None
    address: str | None = None  # None for an mDNS name not yet looked up
    mac: str | None = None  # learned from its first good reply
    foreign: str | None = None  # the MAC of another device at its address
    no_route: bool = False
    polled: bool = False
    fix: str | None = None
    sample: dict | None = None  # the last good `extract`
    sampled_at: float | None = None  # monitor time its poll was sent
    failures: int = 0  # failed polls in a row
    error: str | None = None  # the last failure
    reboots: int = 0  # uptime drops seen this run
    rebooted_at: float | None = None  # monitor time of the last one
    reboot_moved_count: bool = False  # a reboot changed `leds.count`, and no one has set it since
    last_reset_reason: Any = None
    sender: str | None = None  # this laptop's address towards it
    level: str = "pending"
    reasons: list[str] = field(default_factory=list)

    @property
    def lost(self) -> bool:
        """Another device answers at its address, or two polls in a row went
        unanswered: the page offers to point the room board elsewhere."""
        return self.foreign is not None or self.failures >= 2

    def is_foreign(self, info: dict) -> bool:
        """Whether `info` comes from another device than this board."""
        mac = _text(info.get("mac"))
        return self.mac is not None and bool(mac) and mac != self.mac

    def record(self, info: dict, now: float, sender: str | None) -> None:
        """Take one good reply to a poll sent at monitor time `now`. A reply
        from another device ends the failure run too: the address answers."""
        self.failures = 0
        self.error = None
        self.no_route = False
        if self.is_foreign(info):
            self.foreign = _text(info.get("mac"))
            return
        self.foreign = None
        sample = extract(info)
        self.mac = self.mac or _text(info.get("mac"))
        old = self.sample
        if (
            old is not None and old["uptime"] is not None and sample["uptime"] is not None
            and sample["uptime"] < old["uptime"]
        ):
            self.reboots += 1
            self.rebooted_at = now
            self.reboot_moved_count |= sample["count"] != old["count"]
            self.last_reset_reason = sample["reset_reason"]
            reason = "" if sample["reset_reason"] is None else f", reset reason {sample['reset_reason']}"
            logger.warning("board %s rebooted (uptime %ss -> %ss%s)",
                           self.host, old["uptime"], sample["uptime"], reason)
        elif old is not None and None not in (old["count"], sample["count"]) and sample["count"] != old["count"]:
            self.reboot_moved_count = False  # set by hand: no longer a reset
        if sample["count"] == self.expected:
            self.reboot_moved_count = False
        self.sample = sample
        self.sampled_at = now
        self.sender = sender

    def fail(self, error: str, no_route: bool = False) -> None:
        self.failures += 1
        self.error = error
        self.no_route = no_route

    def assess(self, now: float, sent_fps: float | None, streaming_since: float | None) -> None:
        """Set `level`, `reasons` and `fix` from the thresholds above.

        `streaming_since` is the monitor time of the first DDP frame sent,
        or None before one. The stream checks judge the sample only when its
        poll was sent `SETTLE_S` or more after that. `fix` comes from the
        worst check, and among those from the lowest rank, not from the
        first reason.
        """
        found: list[_Found] = []
        named = not is_ipv4(self.host)
        if self.foreign is not None:
            found.append((0, "bad", (f"a different device answers at {self.address} "
                                     f"(MAC {format_mac(self.foreign)}, not {format_mac(self.mac)})"),
                          _FIX_MOVED_NAMED.format(host=self.host) if named
                          else _FIX_MOVED.format(find=_find(self.name, lost=True))))
        if self.failures:
            label = self.host[:-len(".local")] if self.host.lower().endswith(".local") else self.host
            fix = (_FIX_GONE_NAMED.format(host=self.host, label=label) if named
                   else _FIX_GONE.format(find=_find(self.name, lost=self.lost)))
            if self.no_route:
                fix += _FIX_NO_ROUTE
            found.append((1, "bad", f"unreachable: {self.error}", fix) if self.failures >= 2
                         else (1, "warn", f"no answer: {self.error}", fix))
        s = self.sample
        streamed = (
            s is not None and streaming_since is not None and self.sampled_at is not None
            and self.sampled_at >= streaming_since + SETTLE_S
        )
        if s is not None:
            if streamed and s["live"] is False:
                found.append((2, "bad", "not live: not showing the stream", _FIX_NOT_LIVE))
            if streamed and s["live"] and s["lip"] and self.sender is not None and s["lip"] != self.sender:
                found.append((3, "bad", f"live from {s['lip']}, not this laptop",
                              (f"Another program at {s['lip']} is streaming to this board. "
                               "Stop it, or the two streams fight.")))
            if streamed and s["live"] and sent_fps and s["fps"] is not None:
                _band(found, 5, s["fps"] / sent_fps, FPS_WARN, FPS_BAD,
                      f"shows {s['fps']} of {sent_fps:.0f} fps", _FIX_FPS)
            if s["rssi"] is not None:
                _band(found, 6, s["rssi"], RSSI_WARN, RSSI_BAD, f"weak signal {s['rssi']} dBm", _FIX_RSSI)
            if s["freeheap"] is not None:
                _band(found, 7, s["freeheap"], HEAP_WARN, HEAP_BAD, f"low heap {s['freeheap']} B", _FIX_HEAP)
            if s["count"] is not None and s["count"] != self.expected:
                found.append((
                    4, "bad" if s["count"] < self.expected else "warn",
                    f"{s['count']} LEDs configured, {self.expected} streamed",
                    (_FIX_COUNT_REBOOTED if self.reboot_moved_count else _FIX_COUNT).format(expected=self.expected),
                ))
            if self.rebooted_at is not None and now - self.rebooted_at < REBOOT_WARN_S:
                found.append((8, "warn", "rebooted", _FIX_REBOOT))
        self.level = _worst([lvl for _, lvl, _, _ in found]) if found or s is not None else "pending"
        self.reasons = [why for _, _, why, _ in found]
        if found:
            self.fix = _fix(found)
        else:
            # Only once the stream is known to reach it: then a dark bar is off the network.
            self.fix = _FIX_DARK if streamed and s is not None and s["live"] else None

    def describe(self) -> dict:
        """The board's row for the page; JSON-ready."""
        s = self.sample or {}
        return {
            "host": self.host,
            "board": self.name,
            "address": self.address,
            "mac": self.mac,
            "lost": self.lost,
            "fix": self.fix,
            "level": self.level,
            "reasons": self.reasons,
            "live": s.get("live"),
            "lip": s.get("lip") or None,
            "from_us": None if not s.get("lip") or self.sender is None else s["lip"] == self.sender,
            "fps": s.get("fps"),
            "count": s.get("count"),
            "expected": self.expected,
            "rssi": s.get("rssi"),
            "channel": s.get("channel"),
            "uptime": s.get("uptime"),
            "freeheap": s.get("freeheap"),
            "ver": s.get("ver"),
            "reboots": self.reboots,
            "reset_reason": self.last_reset_reason,
        }


@dataclass
class AudioHealth:
    """What the monitor knows about the audio input, and its level."""

    overflows: int = 0  # the input's overflows when last judged
    overflowed_at: float | None = None  # monitor time the overflows last rose
    reboots: int = 0  # a capture node's reboots when last judged
    rebooted_at: float | None = None  # monitor time they last rose
    level: str = "pending"

    def assess(self, state: dict, now: float) -> dict:
        """The input's row for the page, from the features' `state()` at
        monitor time `now`; JSON-ready. A live input says itself whether it
        is lost (`status`); a file is lost only while it gives no samples."""
        source = state.get("input") or {}
        status = source.get("status")
        node = source.get("node") if source.get("kind") == "node" else None
        overflows = source.get("overflows") or 0
        if overflows > self.overflows:
            self.overflowed_at = now
        self.overflows = overflows
        lost = status == "lost" if status is not None else state["mode"] == "lost"
        found: list[_Found] = []
        if state.get("error"):
            found.append((0, "bad", state["error"], _FIX_AUDIO_ERROR))
        if lost:
            if node is not None:
                fix = _FIX_NODE_LOST + (_FIX_NODE_BUSY if source.get("busy") else "")
            else:
                fix = _FIX_AUDIO_LOST.format(input=repr(source.get("name")))
                fix += _FIX_AUDIO_BUSY if source.get("busy") else ""
            found.append((1, "bad", f"lost: {source.get('reason') or 'no samples'}", fix))
        else:
            if status is not None and state["zeros_s"] >= ZEROS_S:
                found.append((2, "warn", f"only exact zeros for {state['zeros_s']:.0f} s", _FIX_AUDIO_ZEROS))
            if state["held"] > DEGRADED_ABOVE:
                found.append((3, "warn", f"{state['held']:.0%} of the tempo window's hops held",
                              _FIX_NODE_LOSS if node is not None else _FIX_AUDIO_HELD))
            if state["peak_db"] is not None and state["peak_db"] >= CLIP_DB:
                found.append((4, "warn", f"clipping: peak {state['peak_db']:g} dBFS", _FIX_AUDIO_CLIP))
        if self.overflowed_at is not None and now - self.overflowed_at < OVERFLOW_WARN_S:
            found.append((5, "warn", f"{overflows} overflow{'' if overflows == 1 else 's'}",
                          _FIX_NODE_OVERFLOW if node is not None else _FIX_AUDIO_OVERFLOW))
        if node is not None:
            found += self._judge_node(node, lost, now)
        known = bool(found) or status != "opening"
        self.level = _worst([lvl for _, lvl, _, _ in found]) if known else "pending"
        return {
            "input": source.get("name"),
            "kind": source.get("kind"),
            "status": status,
            "lost": lost,
            "mode": state["mode"],
            "bpm": state["bpm"],
            "confidence": state["confidence"],
            "peak_db": state["peak_db"],
            "overflows": source.get("overflows"),
            **({} if node is None else {"node": node}),
            "level": self.level,
            "reasons": [why for _, _, why, _ in found],
            "fix": _fix(found) if found else None,
        }

    def _judge_node(self, node: dict, lost: bool, now: float) -> list[_Found]:
        """A capture node's own checks: loss, signal and a recent reboot."""
        found: list[_Found] = []
        reboots = node.get("reboots") or 0
        if reboots > self.reboots:
            self.rebooted_at = now
        self.reboots = reboots
        loss = node.get("loss")
        if not lost and loss is not None and loss > LOSS_WARN:
            found.append((6, "warn", f"{loss:.1%} of the samples lost in the last {LOSS_S:g} s", _FIX_NODE_LOSS))
        if (rssi := node.get("rssi")) is not None:
            _band(found, 7, rssi, RSSI_WARN, RSSI_BAD, f"signal {rssi} dBm", _FIX_NODE_RSSI)
        if self.rebooted_at is not None and now - self.rebooted_at < REBOOT_WARN_S:
            reason = node.get("reset_reason")
            found.append((8, "warn", f"the node rebooted{f' (reset reason: {reason})' if reason else ''}",
                          _FIX_NODE_REBOOT))
        return found


class HealthMonitor:
    """One thread: polls the boards round robin and refreshes the loop and
    sleep state every `STEP_S`; `state()` is the latest snapshot.

    `ddp` is the DDP sink, or None without one. Its boards are read every
    step, so a room map reload that changes the boards changes what is
    polled; `names` gives the room's name for each, in the same order. Its
    frame counter gives the sent rate, and its address table where frames
    go, which the monitor writes for a board named by mDNS (after the audit
    record `record` writes). `stats` is the loop's counters and `target` its
    rate.
    `fetch`, `sender` and `resolve` default to `pewpew.wled`'s `fetch_info`,
    `sender_address` and `resolve_name`, looked up at call time.
    `on_rebind(board, address)` writes a room board's new host to the room
    file and returns a refusal or None; without it, `rebind` is refused.
    `audio` is the audio features' `state`, or None without `--audio`: the
    snapshot has an `audio` row only with it.
    """

    def __init__(
        self,
        ddp: DdpSink | None = None,
        *,
        stats: PaceStats | None = None,
        target: float | None = None,
        awake: Any = None,
        watchdog: float | None = None,
        period: float = PERIOD_S,
        timeout: float = TIMEOUT_S,
        step: float = STEP_S,
        fetch: Callable[[str, float], dict] | None = None,
        sender: Callable[[str, int], str | None] | None = None,
        now: Callable[[], float] = time.monotonic,
        names: Callable[[], Sequence[str]] | None = None,
        argv: Sequence[str] = (),
        resolve: Callable[[str], str] | None = None,
        record: Callable[..., object] = audit.record,
        on_rebind: Callable[[str, str], str | None] | None = None,
        scan_timeout: float = SCAN_TIMEOUT_S,
        audio: Callable[[], dict] | None = None,
    ) -> None:
        self._names = names
        self._ddp = ddp
        self._argv = list(argv)
        self._resolve = resolve
        self._record = record
        self._on_rebind = on_rebind
        self._scan_timeout = scan_timeout
        self._audio = audio
        self._audio_health = AudioHealth()
        self._audio_row = None if audio is None else self._audio_health.assess(audio(), now())
        self._scan: dict | None = None
        self._scan_lock = threading.Lock()
        self._stats = stats
        self._target = target
        self._awake = awake
        self._watchdog = watchdog
        self._period = period
        self._timeout = timeout
        self._step = step
        self._fetch = fetch
        self._sender = sender
        self._now = now
        self._records: dict[str, BoardHealth] = {}
        self._turn = 0
        self._next_poll: float | None = None  # due time of the next board poll
        self._rate_mark: tuple[float, int, int] | None = None  # (time, frames sent, loop ticks)
        self._streaming_since: float | None = None  # monitor time frames sent first read above 0
        self.sent_fps: float | None = None
        self.loop_fps: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: dict = self._compose()

    # ---- any thread ----------------------------------------------------------

    def state(self) -> dict:
        """The latest snapshot; never waits on a request."""
        return self._state

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="pewpew-health", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._timeout + 1.0)

    # ---- monitor thread --------------------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            began = self._now()
            try:
                self.step()
            except Exception:  # the monitor must outlive anything a board sends
                logger.exception("health step failed (contained)")
            self._stop.wait(max(0.0, self._step - (self._now() - began)))

    def step(self) -> None:
        """One tick: refresh the rates and the sleep state, poll the next
        board when one is due, and publish a new snapshot."""
        now = self._now()
        boards = self._boards()
        self._sync(boards)
        self._rates(now)
        if self._awake is not None:
            self._awake.check()
        # A named board gets no frames until a poll looks it up.
        fresh = next((b for b in boards
                      if not self._records[b.host].polled and self._records[b.host].address is None), None)
        if fresh is not None:
            self._poll(fresh)
        elif boards and (self._next_poll is None or now >= self._next_poll):
            board = boards[self._turn % len(boards)]
            self._turn += 1
            gap = self._period / len(boards)
            self._next_poll = max((self._next_poll or now) + gap, now)
            self._poll(board)
        for record in self._records.values():
            before = record.level
            record.assess(self._now(), self.sent_fps, self._streaming_since)
            _log_change(f"board {record.host}", before, record.level, record.reasons)
        if self._audio is not None:
            before = self._audio_health.level
            row = self._audio_row = self._audio_health.assess(self._audio(), self._now())
            _log_change(f"audio input {row['input']!r}", before, row["level"], row["reasons"])
        self._state = self._compose()

    def _boards(self) -> list[Board]:
        return list(self._ddp.boards) if self._ddp is not None else []

    def _room_names(self) -> list[str]:
        return list(self._names()) if self._names is not None else []

    def _sync(self, boards: list[Board]) -> None:
        names = self._room_names()
        records = {}
        for i, b in enumerate(boards):
            record = self._records.get(b.host) or BoardHealth(b.host, b.count)
            record.expected = b.count
            record.name = names[i] if i < len(names) else None
            record.address = self._address(b)
            records[b.host] = record
        self._records = records

    def _address(self, board: Board) -> str | None:
        """Where frames for `board` go, or None for a name not yet found."""
        assert self._ddp is not None  # there are boards only with a sink
        address = self._ddp.address(board.host, board.port)
        return None if address is None else address[0]

    def _poll(self, board: Board) -> None:
        record = self._records[board.host]
        record.polled = True
        named = not is_ipv4(board.host)
        asked = self._now()
        address = record.address
        looked_up = address is None and named
        if looked_up:
            address = self._follow(record, board)
        if address is None:
            record.fail(f"{board.host} does not resolve ({record.error})")
            return
        info, exc = self._ask(address)
        if named and not looked_up and (info is None or record.is_foreign(info)):
            moved = self._follow(record, board)
            if moved is not None:
                address = moved
                info, exc = self._ask(address)
        if info is None:
            assert exc is not None
            record.fail(failure(exc), no_route(exc))
            return
        sender = self._sender or wled.sender_address
        record.record(info, asked, sender(address, board.port))

    def _ask(self, address: str) -> tuple[dict | None, BaseException | None]:
        """One board's `/json/info`, or the exception that stopped it."""
        fetch = self._fetch or wled.fetch_info
        try:
            info = fetch(address, self._timeout)
            if not isinstance(info, dict):
                raise ValueError("the reply is not a JSON object")  # noqa: TRY004  a bad reply, not a caller error
        except Exception as exc:  # noqa: BLE001  a timeout or a bad reply is a health state, not a crash
            return None, exc
        return info, None

    def _follow(self, record: BoardHealth, board: Board) -> str | None:
        """Look a named board up again and point the sink at a new address.
        Returns the new address, or None when there is none to try."""
        resolve = self._resolve or wled.resolve_name
        try:
            ip = resolve(board.host)
        except OSError as exc:
            record.error = failure(exc)
            return None
        if ip == record.address:
            return None
        try:
            self._record(
                "ddp-readdress", argv=self._argv, board=record.name or board.host, host=board.host,
                address=ip, previous=record.address,
            )
        except OSError as exc:
            # The page gets the reason only: the exception names the log's path.
            record.error = f"pewpew could not write the audit record ({failure(exc)}), so no frames go to {ip}"
            logger.error("board %s: no audit record for %s, so no frames go there: %s", board.host, ip, exc)
            return None
        assert self._ddp is not None
        self._ddp.set_address(board.host, board.port, (ip, board.port))
        logger.info("board %s is at %s; streaming there", board.host, ip)
        record.address = ip
        return ip

    def _rates(self, now: float) -> None:
        sent = self._ddp.frames_sent if self._ddp is not None else 0
        ticks = self._stats.ticks if self._stats is not None else 0
        mark = self._rate_mark
        self._rate_mark = (now, sent, ticks)
        if sent > 0 and self._streaming_since is None:
            self._streaming_since = now
        if mark is None or now - mark[0] <= 0:
            return
        span = now - mark[0]
        if self._ddp is not None:
            self.sent_fps = round((sent - mark[1]) / span, 1)
        if self._stats is not None:
            self.loop_fps = round((ticks - mark[2]) / span, 1)

    def _compose(self) -> dict:
        loop_level = (
            "pending" if self.loop_fps is None or not self._target
            else "warn" if self.loop_fps < LOOP_WARN * self._target else "ok"
        )
        loop: dict[str, Any] = {
            "fps": self.loop_fps,
            "target": self._target,
            "skips": self._stats.skips if self._stats is not None else None,
            "watchdog": self._watchdog,
            "level": loop_level,
            "fix": _FIX_LOOP if loop_level == "warn" else None,
        }
        awake = self._awake.state() if self._awake is not None else {"requested": False, "held": False, "detail": None}
        held = not awake["requested"] or awake["held"]
        awake = {**awake, "level": "ok" if held else "warn", "fix": None if held else _FIX_AWAKE}
        boards = [r.describe() for r in self._records.values()]
        audio = {} if self._audio_row is None else {"audio": self._audio_row}
        levels = [b["level"] for b in boards] + [loop["level"], awake["level"]]  # the rows the page draws
        known = [lvl for lvl in levels if lvl != "pending"]
        return {
            "level": _worst(known) if known else "pending",
            "boards": boards,
            "sent_fps": self.sent_fps,
            "loop": loop,
            "awake": awake,
            "scan": self._scan,
            **audio,
        }

    # ---- find boards (any thread) ----------------------------------------------

    def scan(self) -> str | None:
        """Start a sweep of this laptop's /24 for WLED boards; None when it
        started, else why not."""
        with self._scan_lock:
            if self._scan is not None and self._scan.get("running"):
                return "a scan is already running"
            towards = next((r.address for r in self._records.values() if r.address), None)
            local = wled.local_subnet(towards, self._sender)
            if local is None:
                return "this laptop has no IPv4 address to scan from"
            mine, subnet = local
            self._scan = {"running": True, "subnet": str(subnet), "found": [], "error": None}
            self._state = self._compose()
        threading.Thread(
            target=self._sweep, args=(subnet, mine), name="pewpew-board-scan", daemon=True
        ).start()
        return None

    def _sweep(self, subnet: ipaddress.IPv4Network, mine: str) -> None:
        try:
            found = wled.sweep(subnet, mine, self._fetch or wled.fetch_info, self._scan_timeout, stop=self._stop)
            records = list(self._records.values())
            by_mac = {r.mac: r.name or r.host for r in records if r.mac}
            by_address = {r.address: r.name or r.host for r in records if r.address}
            for item in found:
                item["board"] = by_mac.get(item["mac"])
                item["at"] = by_address.get(item["address"])
            self._scan = {"running": False, "subnet": str(subnet), "found": found, "error": None}
        except Exception as exc:  # the sweep must not take the monitor down
            logger.exception("board scan failed")
            self._scan = {"running": False, "subnet": str(subnet), "found": [], "error": failure(exc)}
        self._state = self._compose()

    def rebind(self, board: object, address: object) -> str | None:
        """Point room board `board` at `address`, one the last scan found,
        by rewriting the room file. Returns a refusal or None."""
        if self._on_rebind is None:
            return "rebinding a board needs a room map (run --room)"
        names = self._room_names()
        if not isinstance(board, str) or board not in names:
            return unknown("board", board, names)
        host = self._boards()[names.index(board)].host
        if not is_ipv4(host):
            return (f"board {board} is named {host}, which pewpew follows; "
                    "to give it a fixed address instead, edit the room file")
        found = (self._scan or {}).get("found") or []
        if not isinstance(address, str) or address not in [item["address"] for item in found]:
            return "that address was not in the last scan; scan again"
        return self._on_rebind(board, address)


__all__ = ["AudioHealth", "BoardHealth", "HealthMonitor", "extract"]
