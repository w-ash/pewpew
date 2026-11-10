"""Whether macOS's AWDL interface can stall the stream to a board.

AWDL (Apple Wireless Direct Link: AirDrop, Handoff, Universal Control)
shares the Wi-Fi radio. While it is active the radio leaves the router's
channel at a steady rhythm, so packets to a board queue and then arrive
bunched. WLED shows a frame only when more than 15 ms have passed since
its last show (`wled00/udp.cpp`), so a bunched frame is dropped and
motion jerks at that rhythm on the LEDs, never in the preview. On the
bench, pings from a MacBook to a board on Wi-Fi spiked to 75 ms every
0.46 s with AWDL active and stopped when it went down.

AWDL matters only when this Mac reaches the board over Wi-Fi: over
Ethernet the radio's absence from the channel delays nothing. The check
reads `ifconfig awdl0`, `route -n get` and `networksetup
-listallhardwareports`; each runs with a short timeout, and any failure
reads as unknown.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable, Sequence

TIMEOUT_S = 1.0  # per command

# Shown when the check finds AWDL active on the route to a board.
FIX = ("macOS's AWDL (AirDrop, Handoff, Universal Control) is active and this Mac reaches the boards over "
       "Wi-Fi: the radio leaves the channel about twice a second, and the LEDs jerk at that rhythm. "
       "Run `sudo ifconfig awdl0 down` in a terminal (until the next restart), or turn AirDrop to No One "
       "and Handoff off, or connect this Mac to the router by Ethernet.")

Run = Callable[[Sequence[str]], str]


def _run(args: Sequence[str]) -> str:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=TIMEOUT_S, check=True).stdout


def active(run: Run = _run) -> bool:
    """Whether the `awdl0` interface is up and active."""
    out = run(["ifconfig", "awdl0"])
    return bool(re.search(r"^\s*status:\s*active\s*$", out, re.MULTILINE))


def route_interface(address: str, run: Run = _run) -> str | None:
    """The interface this Mac sends to `address` through, or None."""
    found = re.search(r"^\s*interface:\s*(\S+)\s*$", run(["route", "-n", "get", address]), re.MULTILINE)
    return found.group(1) if found else None


def wifi_devices(run: Run = _run) -> set[str]:
    """The devices of this Mac's Wi-Fi hardware ports (`en0` on most)."""
    out = run(["networksetup", "-listallhardwareports"])
    return set(re.findall(r"Hardware Port:\s*Wi-Fi\s*\nDevice:\s*(\S+)", out))


def stalls(address: str, run: Run = _run, platform: str = sys.platform) -> bool | None:
    """Whether AWDL is active while this Mac reaches `address` over Wi-Fi:
    True or False, or None off macOS or when a command fails."""
    if platform != "darwin":
        return None
    try:
        if not active(run):
            return False
        return route_interface(address, run) in wifi_devices(run)
    except (OSError, subprocess.SubprocessError):
        return None
