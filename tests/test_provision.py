"""`pewpew.provision`: Improv Wi-Fi setup against a fake WLED board."""

from __future__ import annotations

import argparse
import json

import pytest

from pewpew import audit
from pewpew import provision as pv
from pewpew.__main__ import main


def board_packet(kind: int, data: bytes) -> bytes:
    """One packet as WLED sends it (improv.cpp: sendImprovStateResponse / sendImprovRPCResult)."""
    body = pv.HEADER + bytes([pv.VERSION, kind, len(data)]) + data
    return body + bytes([sum(body) & 0xFF])


def state(code: int) -> bytes:
    return board_packet(pv.CURRENT_STATE, bytes([code]))


def error(code: int) -> bytes:
    return board_packet(pv.ERROR_STATE, bytes([code]))


def result(cmd: int, *strings: str) -> bytes:
    body = b"".join(bytes([len(s)]) + s.encode() for s in strings)
    return board_packet(pv.RPC_RESULT, bytes([cmd, len(body)]) + body) + b"\n"


class FakeBoard:
    """A serial port with a WLED board behind it. Each read costs 0.2 s of fake time."""

    def __init__(self, *, boots_at: float = 0.0, joins: bytes | None = None, join_delay: float = 5.0,
                 connected_ip: str | None = None) -> None:
        self.t = 0.0
        self.boots_at = boots_at
        self.joins = joins
        self.join_delay = join_delay
        self.connected_ip = connected_ip
        self.writes: list[tuple[float, bytes]] = []
        self.pending: list[tuple[float, bytes]] = []
        self.closed = False

    def now(self) -> float:
        return self.t

    def write(self, data: bytes) -> int:
        self.writes.append((self.t, data))
        if self.t < self.boots_at:
            return len(data)
        cmd = data[9]
        if cmd == pv.CMD_STATE:
            if self.connected_ip:
                self.pending += [(self.t, state(0x04)), (self.t, result(pv.CMD_STATE, f"http://{self.connected_ip}"))]
            else:
                self.pending.append((self.t, state(0x02)))
        elif cmd == pv.CMD_WIFI:
            self.pending.append((self.t, state(0x03)))
            if self.joins is not None:
                self.pending.append((self.t + self.join_delay, self.joins))
        return len(data)

    def read(self, size: int) -> bytes:
        self.t += 0.2
        due = [b for at, b in self.pending if at <= self.t]
        self.pending = [(at, b) for at, b in self.pending if at > self.t]
        return b"".join(due)

    def close(self) -> None:
        self.closed = True

    def commands(self) -> list[int]:
        return [w[9] for _, w in self.writes]


# --- packets -------------------------------------------------------------


def test_packet_matches_wled_layout():
    p = pv.packet(pv.CMD_WIFI, pv.wifi_data(b"TestNet", b"secret12"))
    assert p[:6] == b"IMPROV" and p[6] == 1 and p[7] == pv.RPC_COMMAND
    assert p[8] == len(p) - 10  # length excludes the 9 header bytes and the checksum
    assert p[9] == pv.CMD_WIFI and p[10] == len(p) - 12
    assert p[11:].startswith(b"\x07TestNet\x08secret12")
    assert p[-1] == sum(p[:-1]) & 0xFF


def test_parser_finds_packets_split_across_reads_and_skips_junk():
    stream = b"boot noise" + state(0x02) + result(pv.CMD_WIFI, "http://10.0.0.7")
    parser = pv.Parser()
    events = [e for i in range(0, len(stream), 3) for e in parser.feed(stream[i : i + 3])]
    assert [e.kind for e in events] == [pv.CURRENT_STATE, pv.RPC_RESULT]
    assert events[1].strings() == ["http://10.0.0.7"]


def test_parser_resyncs_after_a_bad_checksum_without_losing_the_next_packet():
    bad = bytearray(state(0x02))
    bad[-1] ^= 0xFF
    events = pv.Parser().feed(bytes(bad) + state(0x04))
    assert [(e.kind, e.code) for e in events] == [(pv.CURRENT_STATE, 0x04)]


def test_parser_drops_empty_and_wrong_version_packets():
    empty = board_packet(pv.CURRENT_STATE, b"")
    v2 = bytearray(state(0x02))
    v2[6] = 2
    v2[-1] = sum(v2[:-1]) & 0xFF
    assert pv.Parser().feed(empty + bytes(v2)) == []


def test_parser_does_not_keep_non_improv_output():
    parser = pv.Parser()
    parser.feed(b"x" * 10_000 + b"IMPR")
    assert len(parser._buf) <= len(pv.HEADER) - 1
    assert [e.code for e in parser.feed(b"OV" + state(0x02)[6:])] == [0x02]


# --- provision -----------------------------------------------------------


def test_provision_returns_the_ip_from_the_wifi_result():
    board = FakeBoard(joins=state(0x04) + result(pv.CMD_WIFI, "http://192.168.1.50"))
    assert pv.provision(board, b"Home", b"password", now=board.now, log=lambda s: None) == "192.168.1.50"


def test_provision_sends_no_state_request_while_the_board_connects():
    board = FakeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.50"), join_delay=20.0)
    pv.provision(board, b"Home", b"password", now=board.now, log=lambda s: None)
    cmds = board.commands()
    assert cmds[-1] == pv.CMD_WIFI and cmds.count(pv.CMD_WIFI) == 1


def test_provision_ignores_the_ip_of_the_previous_network():
    board = FakeBoard(connected_ip="10.0.0.9", joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    lines: list[str] = []
    assert pv.provision(board, b"Home", b"password", now=board.now, log=lines.append) == "192.168.1.50"
    assert "board is on a network now at 10.0.0.9" in lines


def test_provision_waits_for_a_board_that_reset_when_the_port_opened():
    board = FakeBoard(boots_at=3.0, joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    assert pv.provision(board, b"Home", b"password", now=board.now, log=lambda s: None) == "192.168.1.50"
    assert board.commands().count(pv.CMD_STATE) >= 3  # one probe each second until the board answers


def test_provision_reports_cannot_connect_as_soon_as_the_board_says_so():
    board = FakeBoard(joins=error(0x03), join_delay=24.0)
    with pytest.raises(pv.ProvisionError, match="could not join"):
        pv.provision(board, b"Home", b"wrongpass", now=board.now, timeout=40.0, log=lambda s: None)
    assert board.t < 25.0


def test_provision_gives_up_when_the_board_never_replies():
    board = FakeBoard(boots_at=1e9)
    with pytest.raises(pv.ProvisionError, match="No Improv reply"):
        pv.provision(board, b"Home", b"password", now=board.now, probe_timeout=8.0, log=lambda s: None)
    assert board.t < 9.0


def test_provision_times_out_without_a_wifi_result():
    board = FakeBoard(joins=None)
    with pytest.raises(pv.ProvisionError, match="No IP within 10 s"):
        pv.provision(board, b"Home", b"password", now=board.now, timeout=10.0, log=lambda s: None)


# --- names ---------------------------------------------------------------


@pytest.mark.parametrize("name", ["pewpew-1", "a", "board7", "x" * 32])
def test_check_name_accepts_mdns_labels(name):
    assert pv.check_name(name) == name


@pytest.mark.parametrize("name", ["", "-a", "a-", "Pewpew", "pew pew", "pew_1", "x" * 33])
def test_check_name_rejects_bad_labels(name):
    with pytest.raises(ValueError):
        pv.check_name(name)


def test_set_name_posts_both_names_then_reboots():
    calls = []
    assert pv.set_name("10.0.0.7", "pewpew-1", post=lambda url, body: calls.append((url, body)))
    assert calls == [
        ("http://10.0.0.7/json/cfg", {"id": {"name": "pewpew-1", "mdns": "pewpew-1"}}),
        ("http://10.0.0.7/json/state", {"rb": True}),
    ]


# --- cli -----------------------------------------------------------------


def args(**kw):
    base = {"port": "/dev/cu.fake", "name": None, "dry_run": False, "timeout": 40.0, "ssid": None, "keychain": False}
    return argparse.Namespace(**{**base, **kw})


def run_cli(a, board=None, *, ssid="Home", password="password", **deps):
    """`pv.cli` on fakes: `board` behind the port (no board: opening the
    port fails the test), canned answers, and a keychain that fails the test
    when read. `deps` replaces any of them. Returns the exit code and the
    output."""
    lines: list[str] = []
    rc = pv.cli(a, **{
        "argv": ["pewpew", "wifi"],
        "ask": lambda prompt: ssid,
        "ask_secret": lambda prompt: password,
        "open_port": lambda path: board if board is not None else pytest.fail("port opened"),
        "post": lambda url, body: None,
        "keychain": lambda name, *, reveal: pytest.fail("keychain read"),
        "now": board.now if board is not None else (lambda: 0.0),
        "sleep": lambda s: None,
        "out": lines.append,
        **deps,
    })
    return rc, "\n".join(lines)


def test_dry_run_masks_the_password_and_opens_no_port(audit_log):
    rc, text = run_cli(args(dry_run=True, name="pewpew-1"), password="hunter2hunter2")
    assert rc == 0
    assert "hunter2" not in text and "68 75 6e 74" not in text  # "hunt" in hex
    assert "pewpew-1" in text and "nothing sent" in text
    assert not audit_log.exists()


@pytest.mark.parametrize("password", ["short", "x" * 64, "a" * 65])
def test_cli_rejects_a_password_wpa2_cannot_use(password, audit_log):
    rc, text = run_cli(args(), password=password)
    assert rc == 2 and "8-63 bytes" in text and not audit_log.exists()


@pytest.mark.parametrize("password", ["", "8bytes!!", "x" * 63, "0123456789abcdefABCDEF" * 2 + "0" * 20])
def test_check_password_accepts_open_passphrase_and_raw_psk(password):
    assert pv.check_password(password.encode()) is None


def test_cli_asks_no_password_when_the_wifi_name_is_empty():
    asked = []
    rc, _ = run_cli(args(), ssid="", ask_secret=lambda p: asked.append(p) or "x")
    assert rc == 2 and asked == []


def keychain_with(store):
    calls = []

    def lookup(ssid, *, reveal):
        calls.append((ssid, reveal))
        if ssid not in store:
            return None
        return store[ssid] if reveal else ""

    return lookup, calls


def test_cli_reads_the_password_from_the_keychain_without_prompting():
    board = FakeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    lookup, calls = keychain_with({"Home": "keychainpw1"})
    rc, text = run_cli(args(ssid="Home", keychain=True), board, keychain=lookup,
                       ask=lambda p: pytest.fail("asked"), ask_secret=lambda p: pytest.fail("asked"))
    assert rc == 0 and calls == [("Home", True)]
    wifi = next(w for _, w in board.writes if w[9] == pv.CMD_WIFI)
    assert b"keychainpw1" in wifi and "keychainpw1" not in text


def test_keychain_dry_run_checks_the_item_but_does_not_read_the_password():
    lookup, calls = keychain_with({"Home": "keychainpw1"})
    rc, text = run_cli(args(ssid="Home", keychain=True, dry_run=True), keychain=lookup)
    assert rc == 0 and calls == [("Home", False)] and "nothing sent" in text.splitlines()[-1]


def test_keychain_reports_a_missing_or_denied_item(audit_log):
    lookup, _ = keychain_with({})
    rc, text = run_cli(args(ssid="Elsewhere", keychain=True), keychain=lookup)
    assert rc == 1 and "No Wi-Fi password" in text.splitlines()[0] and not audit_log.exists()


def test_keychain_needs_ssid(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["wifi", "/dev/null", "--keychain"])
    assert exc.value.code == 2 and "--keychain needs --ssid" in capsys.readouterr().err  # a usage error


def test_cli_explains_when_there_is_no_terminal_to_ask_in():
    def no_input(prompt):
        raise EOFError

    rc, text = run_cli(args(), ask=no_input)
    assert rc == 2 and "interactive terminal" in text.strip().splitlines()[0]


def test_cli_sends_nothing_when_the_audit_log_cannot_be_written(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("")
    monkeypatch.setenv(audit.ENV_VAR, str(blocker / "audit.jsonl"))
    rc, text = run_cli(args())  # run_cli fails the test if the port is opened
    assert rc == 1 and "nothing was sent" in text


def test_cli_reports_a_lost_serial_port():
    board = FakeBoard(joins=None)

    def unplugged(size):
        raise OSError("device disconnected")

    board.read = unplugged
    rc, text = run_cli(args(), board)
    assert rc == 1 and board.closed and "Lost the serial port" in text


def test_set_name_retries_until_the_board_answers_http():
    calls = []

    def post(url, body):
        calls.append(url)
        if len(calls) < 3:
            raise OSError("timed out")

    assert pv.set_name("10.0.0.7", "pewpew-1", post=post, sleep=lambda s: None)
    assert calls[-2:] == ["http://10.0.0.7/json/cfg", "http://10.0.0.7/json/state"] and len(calls) == 4


def test_set_name_raises_when_the_board_never_answers():
    def post(url, body):
        raise OSError("timed out")

    with pytest.raises(OSError):
        pv.set_name("10.0.0.7", "pewpew-1", post=post, sleep=lambda s: None, attempts=3)


def test_provision_does_not_treat_an_error_reply_as_ready():
    board = FakeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    board.pending.append((0.0, error(0x01)))  # boot noise answered as "invalid packet"
    board.boots_at = 2.0
    assert pv.provision(board, b"Home", b"password", now=board.now, log=lambda s: None) == "192.168.1.50"
    first_wifi = next(t for t, w in board.writes if w[9] == pv.CMD_WIFI)
    assert first_wifi >= 2.0


def test_cli_provisions_names_and_logs_without_the_password(audit_log):
    board = FakeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    calls = []
    rc, text = run_cli(args(name="pewpew-1"), board, post=lambda url, body: calls.append(url))
    assert rc == 0 and board.closed
    assert "Board IP: 192.168.1.50" in text and "pewpew-1.local" in text
    assert calls == ["http://192.168.1.50/json/cfg", "http://192.168.1.50/json/state"]
    record = json.loads(audit_log.read_text())
    assert record["action"] == "wifi" and record["ssid"] == "Home" and record["name"] == "pewpew-1"
    assert "password" not in audit_log.read_text()


def test_cli_closes_the_port_and_fails_when_the_board_cannot_join():
    board = FakeBoard(joins=error(0x03), join_delay=24.0)
    rc, text = run_cli(args(), board)
    assert rc == 1 and board.closed and "could not join" in text


def test_cli_reports_a_failed_reboot_request():
    board = FakeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.50"))

    def post(url, body):
        if url.endswith("/json/state"):
            raise OSError("connection reset")

    rc, text = run_cli(args(name="pewpew-1"), board, post=post)
    assert rc == 1 and "Press RST" in text


@pytest.mark.parametrize("flags, message", [
    (["--name", "Bad Name"], "invalid name"), (["--timeout", "0"], "more than 0"),
])
def test_main_routes_wifi_and_rejects_bad_flags(flags, message, capsys):
    with pytest.raises(SystemExit):
        main(["wifi", "/dev/cu.fake", *flags])
    assert message in capsys.readouterr().err


# --- capture nodes -------------------------------------------------------


class FakeNodeBoard(FakeBoard):
    """A capture node behind the port (firmware/audio-node/main/improv.c):
    it answers device info with pewpew's firmware name and takes its names
    over Improv; `firmware` "WLED" makes it a WLED board that answers too."""

    def __init__(self, firmware: str = pv.FIRMWARE, **kw) -> None:
        super().__init__(**kw)
        self.firmware = firmware
        self.names: dict[int, str] = {}

    def write(self, data: bytes) -> int:
        cmd, payload = data[9], data[11:-1]
        if self.t >= self.boots_at and cmd == pv.CMD_INFO:
            self.writes.append((self.t, data))
            self.pending.append((self.t, result(pv.CMD_INFO, self.firmware, "0.1.0", "ESP32-S3", "pewpew-node-a1b2c3")))
            return len(data)
        if self.t >= self.boots_at and cmd in (pv.CMD_HOSTNAME, pv.CMD_DEVICE_NAME):
            self.writes.append((self.t, data))
            name = payload.decode()
            if pv.NAME_RE.match(name):
                self.names[cmd] = name
                self.pending.append((self.t, result(cmd, name)))
            else:
                self.pending.append((self.t, error(0x05)))
            return len(data)
        return super().write(data)


def test_a_capture_node_takes_its_names_over_improv_before_it_joins(audit_log):
    board = FakeNodeBoard(joins=result(pv.CMD_WIFI, "http://192.168.1.60"))
    rc, text = run_cli(args(name="pewpew-line-1"), board,
                       post=lambda url, body: pytest.fail("a node's HTTP is read-only"))
    assert rc == 0 and board.closed
    cmds = board.commands()
    order = [cmds.index(c) for c in (pv.CMD_INFO, pv.CMD_DEVICE_NAME, pv.CMD_HOSTNAME, pv.CMD_WIFI)]
    assert order == sorted(order)  # the names before the Wi-Fi, the device name first
    assert board.names == {pv.CMD_DEVICE_NAME: "pewpew-line-1", pv.CMD_HOSTNAME: "pewpew-line-1"}
    assert "Named pewpew-line-1. The node answers at pewpew-line-1.local." in text


def test_a_board_that_answers_device_info_as_wled_is_named_over_http():
    board = FakeNodeBoard(firmware="WLED", joins=result(pv.CMD_WIFI, "http://192.168.1.50"))
    calls = []
    rc, _ = run_cli(args(name="pewpew-1"), board, post=lambda url, body: calls.append(url))
    assert rc == 0 and calls == ["http://192.168.1.50/json/cfg", "http://192.168.1.50/json/state"]
    assert pv.CMD_HOSTNAME not in board.commands()


def test_a_node_that_refuses_its_name_stops_before_the_wifi():
    board = FakeNodeBoard()
    session = pv.Session(board, now=board.now, log=lambda s: None)
    session.probe()
    with pytest.raises(pv.ProvisionError, match="bad hostname"):
        session.name_node("Bad_Name")
    assert pv.CMD_WIFI not in board.commands()


def test_the_dry_run_prints_both_ways_of_naming(audit_log):
    rc, text = run_cli(args(name="pewpew-line-1", dry_run=True))
    assert rc == 0 and "on a capture node, before the Wi-Fi: set device name" in text
    assert "on a WLED board, after it: POST /json/cfg" in text and not audit_log.exists()
