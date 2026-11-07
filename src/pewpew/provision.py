"""Set up a stock WLED board or a pewpew capture node: its Wi-Fi over USB
serial, and its name.

`python -m pewpew wifi PORT [--name NAME]` sends the Wi-Fi settings with the
Improv serial protocol, waits for the board to report its new IP, and then
optionally sets the board's display name and mDNS name and reboots it.

A capture node (firmware/audio-node) serves a read-only `/json/info`, so
it takes its names over the same serial session: with `--name`, `wifi`
asks Improv's device information first, and when the firmware is
`pewpew.audio.wire.FIRMWARE` it sends Improv's Set Device Name (0x06),
then Set Hostname (0x05), the order the spec recommends, before the Wi-Fi
settings, so the node joins under its new name ([S1785],
https://www.improv-wifi.com/serial/). Each carries the name as its data.
Anything else, or no answer within `INFO_TIMEOUT_S`, is named as a WLED
board is.

The protocol details follow WLED v16.0.1:

- Packet layout: `wled00/improv.cpp` (`handleImprovPacket`).
- After the Wi-Fi command, the board sends state "connecting". When it
  joins, it sends state "connected" and an RPC result for the Wi-Fi command
  that holds `http://<ip>` (`wled00/wled.cpp:975-978`). If it cannot join,
  it sends error 0x03 about 24 s later (`wled00/wled.cpp:942-945`).
- Send state requests only before the Wi-Fi command. When a connected board
  answers one, it marks provisioning done (`improv.cpp`,
  `sendImprovIPRPCResult`). The Wi-Fi command marks it active again
  (`improv.cpp:271`), so a state request before it is safe. A state request
  after it can arrive while the board is still on the previous network: the
  answer then holds the old IP, and the Wi-Fi result never comes.
- The names are `id.name` and `id.mdns` in `/json/cfg` (`wled00/cfg.cpp:55-56`).

Writing Wi-Fi settings and names is tier-1 bench actuation (CLAUDE.md T-7):
`--dry-run` sends nothing, and a real run appends an audit record first. The
password comes from a hidden prompt only. It never goes to argv, the screen
or the audit log.
"""

from __future__ import annotations

import argparse
import getpass
import http.client
import ipaddress
import json
import re
import subprocess
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pewpew import audit, wled
from pewpew.audio.wire import FIRMWARE
from pewpew.jsonfile import loads

HEADER = b"IMPROV"
VERSION = 1

CURRENT_STATE = 0x01
ERROR_STATE = 0x02
RPC_COMMAND = 0x03
RPC_RESULT = 0x04

CMD_WIFI = 0x01
CMD_STATE = 0x02
CMD_INFO = 0x03
CMD_HOSTNAME = 0x05
CMD_DEVICE_NAME = 0x06

STATES = {0x02: "ready", 0x03: "connecting", 0x04: "connected"}
ERRORS = {0x01: "invalid packet", 0x02: "unknown command", 0x03: "cannot connect", 0x05: "bad hostname"}
ERR_CANNOT_CONNECT = 0x03
INFO_TIMEOUT_S = 3.0  # a board that has not answered device info by then is named as WLED is

NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")


class Port(Protocol):
    """The part of `serial.Serial` that `provision` uses."""

    def read(self, size: int, /) -> bytes: ...
    def write(self, data: bytes, /) -> int | None: ...
    def close(self) -> None: ...


class ProvisionError(Exception):
    """The board did not reply, rejected the settings, or could not join."""


@dataclass(frozen=True)
class Event:
    """One valid Improv packet from the board."""

    kind: int
    data: bytes

    @property
    def code(self) -> int:
        """The state or error code. Valid for CURRENT_STATE and ERROR_STATE."""
        return self.data[0]

    @property
    def command(self) -> int:
        """The command that an RPC result answers. Valid for RPC_RESULT."""
        return self.data[0]

    def strings(self) -> list[str]:
        """The length-prefixed strings of an RPC result."""
        end = min(len(self.data), 2 + self.data[1])
        out, pos = [], 2
        while pos < end:
            n = self.data[pos]
            out.append(self.data[pos + 1 : pos + 1 + n].decode(errors="replace"))
            pos += 1 + n
        return out


def packet(cmd: int, data: bytes = b"") -> bytes:
    """Return one Improv RPC command packet with its checksum."""
    payload = bytes([cmd, len(data)]) + data
    body = HEADER + bytes([VERSION, RPC_COMMAND, len(payload)]) + payload
    return body + bytes([sum(body) & 0xFF])


def wifi_data(ssid: bytes, password: bytes) -> bytes:
    """Return the data field of the Wi-Fi command."""
    return bytes([len(ssid)]) + ssid + bytes([len(password)]) + password


class Parser:
    """Find Improv packets in a serial byte stream."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> list[Event]:
        """Add bytes. Return the complete, valid packets they finish."""
        buf = self._buf
        buf.extend(chunk)
        out: list[Event] = []
        while True:
            i = buf.find(HEADER)
            if i < 0:
                del buf[: max(0, len(buf) - (len(HEADER) - 1))]
                return out
            del buf[:i]
            if len(buf) < 9:
                return out
            end = 9 + buf[8]
            if len(buf) <= end:
                return out
            pkt = bytes(buf[: end + 1])
            event = Event(pkt[7], pkt[9:-1])
            if pkt[6] == VERSION and sum(pkt[:-1]) & 0xFF == pkt[-1] and _complete(event):
                del buf[: end + 1]
                out.append(event)
            else:
                del buf[:1]


def _complete(event: Event) -> bool:
    if event.kind in (CURRENT_STATE, ERROR_STATE):
        return len(event.data) >= 1
    if event.kind == RPC_RESULT:
        return len(event.data) >= 2
    return False


def _ip_of(event: Event) -> str | None:
    for s in event.strings():
        if s.startswith("http://"):
            try:
                return str(ipaddress.IPv4Address(s.removeprefix("http://")))
            except ValueError:
                return None
    return None


def _error(code: int) -> str:
    """An Improv error code in words."""
    return ERRORS.get(code, hex(code))


def _describe(event: Event) -> str | None:
    if event.kind == CURRENT_STATE:
        return f"board state: {STATES.get(event.code, hex(event.code))}"
    if event.kind == ERROR_STATE and event.code:
        return f"board error: {_error(event.code)}"
    if event.kind == RPC_RESULT and event.command == CMD_STATE and (ip := _ip_of(event)):
        return f"board is on a network now at {ip}"
    return None


class Session:
    """One Improv conversation with the board behind `port`: `now` is the
    clock its timeouts run on, and `log` gets each event worth telling."""

    def __init__(self, port: Port, *, now: Callable[[], float] = time.monotonic,
                 log: Callable[[str], None] = print) -> None:
        self.port = port
        self.now = now
        self.log = log
        self._parser = Parser()

    def events(self) -> list[Event]:
        """The packets the next read finishes."""
        got = self._parser.feed(self.port.read(256))
        for event in got:
            if text := _describe(event):
                self.log(text)
        return got

    def probe(self, timeout: float = 8.0) -> None:
        """Send state requests, one each second, until the board replies,
        so that a board that reset when the port opened has time to boot.
        Raise ProvisionError on no reply within `timeout` seconds."""
        deadline = self.now() + timeout
        next_probe = self.now()
        while True:
            if self.now() >= deadline:
                raise ProvisionError(
                    "No Improv reply. Check the port, close any app that holds it, and check that WLED or the "
                    "capture node's firmware is installed."
                )
            if self.now() >= next_probe:
                self.port.write(packet(CMD_STATE))
                next_probe = self.now() + 1.0
            if any(e.kind == CURRENT_STATE for e in self.events()):
                return

    def ask(self, cmd: int, data: bytes = b"", timeout: float = INFO_TIMEOUT_S,
            refused: Callable[[int], str] | None = None) -> Event | None:
        """Send RPC `cmd` and return its result, or None after `timeout`
        seconds. Raise ProvisionError when the board answers with an error:
        `refused(code)` says why, by default the command and the error."""
        self.port.write(packet(cmd, data))
        deadline = self.now() + timeout
        while self.now() < deadline:
            for event in self.events():
                if event.kind == ERROR_STATE and event.code:
                    raise ProvisionError(refused(event.code) if refused else
                                         f"The board refused command {cmd:#04x}: {_error(event.code)}.")
                if event.kind == RPC_RESULT and event.command == cmd:
                    return event
        return None

    def join(self, ssid: bytes, password: bytes, timeout: float = 40.0) -> str:
        """Send the Wi-Fi settings and only listen; return the IPv4 address
        the board reports. Raise ProvisionError on an error from the board,
        or no IP within `timeout` seconds."""
        self.log("sending Wi-Fi settings")
        event = self.ask(CMD_WIFI, wifi_data(ssid, password), timeout, refused=_join_refused)
        if event is None:
            raise ProvisionError(f"No IP within {timeout:g} s. Check that the network is 2.4 GHz.")
        ip = _ip_of(event)
        if ip is None:
            raise ProvisionError(f"The board joined but reported no IPv4 address: {event.strings()}")
        return ip

    def name_node(self, name: str) -> bool:
        """Name a capture node over Improv (module docstring): True when the
        board is one and took the name, False when it is not a node. Raise
        ProvisionError when a node refuses the name."""
        try:
            info = self.ask(CMD_INFO)
        except ProvisionError:  # a firmware without device info is no node
            return False
        strings = info.strings() if info is not None else []
        if not strings or strings[0] != FIRMWARE:
            return False
        for cmd in (CMD_DEVICE_NAME, CMD_HOSTNAME):
            answer = self.ask(cmd, name.encode())
            if answer is None or answer.strings()[:1] != [name]:
                raise ProvisionError(f"The node did not take the name {name!r}.")
        self.log(f"capture node {strings[1] if len(strings) > 1 else ''} named {name}")
        return True


def _join_refused(code: int) -> str:
    if code == ERR_CANNOT_CONNECT:
        return ("The board could not join the network. Check the Wi-Fi name and password, and that the network "
                "is 2.4 GHz.")
    return f"The board rejected the settings: {_error(code)}."


def provision(
    port: Port,
    ssid: bytes,
    password: bytes,
    *,
    now: Callable[[], float] = time.monotonic,
    timeout: float = 40.0,
    probe_timeout: float = 8.0,
    log: Callable[[str], None] = print,
) -> str:
    """Send the Wi-Fi settings and return the IPv4 address the board reports.

    First send state requests until the board replies (`Session.probe`),
    then the Wi-Fi command, and only listen (`Session.join`). Raise
    ProvisionError on no reply, an error from the board, or no IP within
    `timeout` seconds.
    """
    session = Session(port, now=now, log=log)
    session.probe(probe_timeout)
    return session.join(ssid, password, timeout)


def _post(url: str, body: dict[str, Any]) -> Any:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return loads(resp.read() or b"null")


def set_name(
    ip: str,
    name: str,
    *,
    post: Callable[[str, dict[str, Any]], Any] = _post,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = 5,
) -> bool:
    """Set the board's display name and mDNS name, then reboot it to apply them.

    Try the names up to `attempts` times, 2 s apart, because a board that has
    just joined can be slow to answer HTTP. Raise the last error if all
    attempts fail. Return False if the names were set but the reboot request
    failed.
    """
    for attempt in range(attempts):
        try:
            post(f"http://{ip}/json/cfg", {"id": {"name": name, "mdns": name}})
            break
        except (OSError, ValueError, http.client.HTTPException):
            if attempt == attempts - 1:
                raise
            sleep(2.0)
    try:
        post(f"http://{ip}/json/state", {"rb": True})
    except (OSError, ValueError, http.client.HTTPException):
        return False
    return True


def check_name(name: str) -> str:
    """Return `name` if it is a valid mDNS label of at most 32 characters, else raise ValueError."""
    if not NAME_RE.match(name):
        raise ValueError(
            f"invalid name {name!r}: use 1-32 lowercase letters, digits and hyphens, "
            "with no hyphen at the start or end"
        )
    return name


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `wifi` subcommand to the CLI."""
    p = sub.add_parser("wifi", help="set a WLED board's or a capture node's Wi-Fi over USB serial, and optionally "
                       "its name")
    p.add_argument("port", help="serial port, for example /dev/cu.usbmodem1101 (the board's USB port)")
    p.add_argument("--name", type=_name_arg, default=None,
                   help="display and mDNS name, for example pewpew-1, or pewpew-line-1 for a capture node")
    p.add_argument("--ssid", default=None, help="Wi-Fi name; asked for if left out")
    p.add_argument(
        "--keychain",
        action="store_true",
        help="read the password for --ssid from the macOS Keychain instead of asking (macOS asks you to allow it)",
    )
    p.add_argument("--dry-run", action="store_true", help="print the packets and open no port")
    p.add_argument("--timeout", type=_seconds_arg, default=40.0, help="seconds to wait for the board to join")
    p.set_defaults(cli=lambda args, argv: cli(args, argv=argv))


def _seconds_arg(value: str) -> float:
    seconds = float(value)
    if not seconds > 0:
        raise argparse.ArgumentTypeError(f"must be more than 0, got {value}")
    return seconds


def check_password(password: bytes) -> str | None:
    """Return why WPA2 cannot use `password`, or None if it can. Empty means an open network."""
    if not password or 8 <= len(password) <= 63:
        return None
    if len(password) == 64 and all(c in b"0123456789abcdefABCDEF" for c in password):
        return None  # a raw PSK; WLED stores up to 64 characters (fcn_declare.h:65)
    return f"The password is {len(password)} bytes. A WPA2 password is 8-63 bytes, or 64 hex digits."


def _name_arg(value: str) -> str:
    try:
        return check_name(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from None


def keychain_password(ssid: str, *, reveal: bool) -> str | None:
    """Return the macOS Keychain's saved password for Wi-Fi network `ssid`, or None.

    macOS asks the person to allow the read. With `reveal` False, only check
    that the item exists and return "" without reading the password.
    """
    cmd = ["security", "find-generic-password", "-D", "AirPort network password", "-a", ssid]
    proc = subprocess.run(cmd + (["-w"] if reveal else []), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.removesuffix("\n") if reveal else ""


def _open_serial(path: str) -> Port:
    import serial

    s = serial.Serial()
    s.port, s.baudrate, s.timeout = path, 115200, 0.2
    s.dtr = s.rts = False  # keep EN and IO0 high so that the board does not reset or enter the bootloader
    s.open()
    return s


def cli(
    args: argparse.Namespace,
    *,
    argv: list[str],
    ask: Callable[[str], str] = input,
    ask_secret: Callable[[str], str] = getpass.getpass,
    open_port: Callable[[str], Port] = _open_serial,
    post: Callable[[str, dict[str, Any]], Any] = _post,
    keychain: Callable[..., str | None] = keychain_password,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
) -> int:
    """Run the `wifi` subcommand. Return the exit code."""
    try:
        ssid = (args.ssid if args.ssid is not None else ask("Wi-Fi name (2.4 GHz): ")).encode()
        if not 0 < len(ssid) <= 32:
            out("The Wi-Fi name must be 1-32 bytes.")
            return 2
        if args.keychain:
            found = keychain(args.ssid, reveal=not args.dry_run)
            if found is None:
                out(f"No Wi-Fi password for {args.ssid!r} in the Keychain, or the read was denied.")
                return 1
            password = found.encode() if not args.dry_run else b"*" * 8
            out(f"password: from the Keychain ({'not read in a dry run' if args.dry_run else 'read'})")
        else:
            password = ask_secret("Wi-Fi password (hidden, empty for an open network): ").encode()
    except EOFError:
        out(
            "\nThis command asks for the Wi-Fi name and password, so run it in an interactive terminal "
            "window, or pass --ssid NAME --keychain."
        )
        return 2
    if problem := check_password(password):
        out(problem)
        return 2

    if args.dry_run:
        masked = packet(CMD_WIFI, wifi_data(ssid, b"*" * len(password)))
        out(f"state request: {packet(CMD_STATE).hex(' ')}")
        out(f"Wi-Fi command, password masked: {masked.hex(' ')}")
        if args.name:
            name = args.name.encode()
            out(f"device info request: {packet(CMD_INFO).hex(' ')}")
            out(f"on a capture node, before the Wi-Fi: set device name {packet(CMD_DEVICE_NAME, name).hex(' ')}, "
                f"then set hostname {packet(CMD_HOSTNAME, name).hex(' ')}")
            out(f"on a WLED board, after it: POST /json/cfg {{'id': {{'name': {args.name!r}, 'mdns': {args.name!r}}}}} "
                "and reboot")
        out(f"Dry run: nothing sent to {args.port}.")
        return 0

    try:
        log = audit.record("wifi", argv=argv, port=args.port, ssid=ssid.decode(errors="replace"), name=args.name)
    except OSError as e:
        out(f"Cannot write the audit log, so nothing was sent: {e}")
        return 1
    out(f"audit record: {log}")
    try:
        port = open_port(args.port)
    except OSError as e:  # serial.SerialException is an OSError
        out(f"Cannot open {args.port}: {e}")
        return 1
    try:
        session = Session(port, now=now, log=out)
        session.probe()
        node = bool(args.name) and session.name_node(args.name)
        ip = session.join(ssid, password, args.timeout)
    except ProvisionError as e:
        out(str(e))
        return 1
    except OSError as e:
        out(f"Lost the serial port: {e}")
        return 1
    finally:
        port.close()
    out(f"Board IP: {ip}")

    if node:
        out(f"Named {args.name}. The node answers at {args.name}.local.")
    elif args.name:
        try:
            rebooted = set_name(ip, args.name, post=post, sleep=sleep)
        except (OSError, ValueError, http.client.HTTPException) as e:
            out(f"Could not set the name at http://{ip}: {e}")
            if wled.no_route(e):
                out(
                    "If `curl http://" + ip + "/json/info` works, macOS is blocking Python from the local "
                    f"network: allow your terminal app in {wled.PRIVACY}."
                )
            return 1
        if not rebooted:
            out(f"Named {args.name}, but the reboot request failed. Press RST to apply the name.")
            return 1
        out(f"Named {args.name}. The board reboots and then answers at {args.name}.local.")
    return 0
