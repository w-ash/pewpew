"""pewpew.awdl: AWDL active on the Wi-Fi route to a board, read from macOS's
own commands, each faked here."""

from __future__ import annotations

import subprocess

from pewpew.awdl import stalls  # before conftest swaps it out

IFCONFIG_ACTIVE = "awdl0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500\n\tstatus: active\n"
IFCONFIG_DOWN = "awdl0: flags=8822<BROADCAST,SMART,SIMPLEX,MULTICAST> mtu 1500\n\tstatus: inactive\n"
ROUTE = "   route to: 192.168.7.59\ndestination: 192.168.7.0\n  interface: {iface}\n      flags: <UP,DONE,CLONING>\n"
PORTS = ("Hardware Port: Ethernet\nDevice: en5\nEthernet Address: 00:00:00:00:00:01\n\n"
         "Hardware Port: Wi-Fi\nDevice: en0\nEthernet Address: 00:00:00:00:00:02\n")


def fake(ifconfig: str, iface: str):
    def run(args):
        return {"ifconfig": ifconfig, "route": ROUTE.format(iface=iface), "networksetup": PORTS}[args[0]]
    return run


def test_awdl_active_on_the_wifi_route_stalls():
    assert stalls("192.168.7.59", fake(IFCONFIG_ACTIVE, "en0"), platform="darwin") is True


def test_awdl_down_or_a_wired_route_does_not():
    assert stalls("192.168.7.59", fake(IFCONFIG_DOWN, "en0"), platform="darwin") is False
    assert stalls("192.168.7.59", fake(IFCONFIG_ACTIVE, "en5"), platform="darwin") is False


def test_off_macos_or_when_a_command_fails_it_is_unknown():
    assert stalls("192.168.7.59", fake(IFCONFIG_ACTIVE, "en0"), platform="linux") is None

    def failing(args):
        raise subprocess.CalledProcessError(1, args)

    assert stalls("192.168.7.59", failing, platform="darwin") is None
