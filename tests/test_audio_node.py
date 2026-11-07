"""A capture node around the host: its health row, `audio list`'s nodes,
`audio key` (tier 1), and scans that show a node as a node and never offer
one as a DDP board. The fake node and the receiver are in
test_audio_net.py."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from fake_node import FakeNode
from fakes import FakeTime, wait_until
from pewpew import wled
from pewpew.__main__ import main
from pewpew.audio import keys
from pewpew.audio.device import INSTALL
from pewpew.health import LOSS_WARN, REBOOT_WARN_S, AudioHealth, HealthMonitor

MAC = "aabbccddeeff"


# ---- health ------------------------------------------------------------------------


def node_state(status: str = "listening", reason: str | None = None, **node) -> dict:
    """The features' state of a capture node, with overrides of its numbers."""
    numbers = {"address": "10.0.0.42", "mac": MAC, "ver": "0.1.0", "rssi": -55, "uptime": 300,
               "reset_reason": "poweron", "packets": 1000, "missing": 0, "late": 0, "stray": 0, "stale": 0,
               "overflows": 0, "clips": 0, "reboots": 0, "followed": 0, "loss": 0.0, "drift_ppm": 12.5, **node}
    return {"input": {"name": "pewpew-line-1.local", "kind": "node", "status": status, "reason": reason,
                      "busy": False, "overflows": numbers["overflows"], "node": numbers},
            "mode": "locked", "bpm": 124.0, "confidence": 0.6, "peak_db": -12.0, "held": 0.0, "zeros_s": 0.0,
            "error": None}


@pytest.mark.parametrize("state, level, reason, fix", [
    (node_state(), "ok", None, None),
    (node_state("lost", "no packets for 0.5 s"), "bad", "lost: no packets for 0.5 s",
     "powered and on the private router"),
    (node_state(loss=2 * LOSS_WARN), "warn", "2.0% of the samples lost in the last 10 s", "Packets from the node"),
    (node_state(rssi=-85), "bad", "signal -85 dBm", "Move the node or the router closer"),
    (node_state(drift_ppm=900.0), "ok", None, None),  # drift is reported, never judged
])
def test_the_node_row_judges_loss_signal_and_the_lost_rule(state: dict, level: str, reason, fix) -> None:
    row = AudioHealth().assess(state, 0.0)
    assert row["level"] == level and row["reasons"] == ([] if reason is None else [reason])
    assert (row["fix"] is None) if fix is None else fix in row["fix"]
    assert row["node"]["drift_ppm"] == state["input"]["node"]["drift_ppm"]


def test_a_node_held_elsewhere_says_another_host_holds_it() -> None:
    state = node_state("lost", "another host holds the node's stream")
    state["input"]["busy"] = True
    assert "Another host holds its stream" in AudioHealth().assess(state, 0.0)["fix"]


def test_a_reboot_warns_for_ten_minutes_with_its_reset_reason() -> None:
    health = AudioHealth()
    assert health.assess(node_state(), 0.0)["level"] == "ok"
    row = health.assess(node_state(reboots=1, reset_reason="task_wdt"), 5.0)
    assert row["reasons"] == ["the node rebooted (reset reason: task_wdt)"] and "firmware fault" in row["fix"]
    assert health.assess(node_state(reboots=1), 5.0 + REBOOT_WARN_S)["level"] == "ok"


def test_a_node_overflow_blames_the_nodes_reader_not_the_loop() -> None:
    health = AudioHealth()
    health.assess(node_state(), 0.0)
    row = health.assess(node_state(overflows=1), 1.0)
    assert row["reasons"] == ["1 overflow"] and "I2S reader" in row["fix"]


# ---- audio list and audio key ----------------------------------------------------------


def test_audio_list_lists_the_nodes_from_their_json_info(sd, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    node = FakeNode(None)
    node.close()
    asked: list[str] = []

    def fetch(host: str, timeout: float) -> dict:
        asked.append(host)
        if host == "10.0.0.2":
            return node.info()
        if host == "10.0.0.1":
            return {"ver": "16.0.1", "mac": "020000000001", "brand": "WLED"}
        raise OSError("no answer")

    monkeypatch.setattr(wled, "fetch_info", fetch)
    assert main(["audio", "list", "--json", "--subnet", "10.0.0.0/30"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [n["address"] for n in listed["nodes"]] == ["10.0.0.2"] and listed["nodes"][0]["key"] is False
    assert listed["devices"] and sorted(asked) == ["10.0.0.1", "10.0.0.2"]
    assert main(["audio", "list", "--subnet", "10.0.0.0/30"]) == 0
    text = capsys.readouterr().out
    assert "Capture nodes on 10.0.0.0/30" in text and "run --audio net:NAME" in text
    assert "10.0.0.2         pewpew-line-1     MAC aa:bb:cc:dd:ee:ff  capture node 0.1.0 (line in)" in text
    assert "no key flashed" in text


def test_audio_list_without_the_extra_still_lists_the_nodes(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    # conftest puts None in sys.modules["sounddevice"]: the extra is missing.
    node = FakeNode(None)
    node.close()

    def fetch(host: str, timeout: float) -> dict:
        if host == "10.0.0.2":
            return node.info()
        raise OSError("no answer")

    monkeypatch.setattr(wled, "fetch_info", fetch)
    assert main(["audio", "list", "--json", "--subnet", "10.0.0.0/30"]) == 1
    out = capsys.readouterr()
    listed = json.loads(out.out)
    assert listed["devices"] is None and listed["error"] == INSTALL and INSTALL in out.err
    assert [n["address"] for n in listed["nodes"]] == ["10.0.0.2"]
    assert main(["audio", "list", "--subnet", "10.0.0.0/30"]) == 1
    assert "Capture nodes on 10.0.0.0/30" in capsys.readouterr().out


def test_audio_key_audits_then_makes_a_key_only_its_owner_reads(audit_log: Path, capsys) -> None:
    assert main(["audio", "key", "AA:BB:CC:DD:EE:FF", "--dry-run"]) == 0
    assert "nothing written" in capsys.readouterr().out
    assert not audit_log.exists() and not keys.keys_path().exists()
    assert main(["audio", "key", "AA:BB:CC:DD:EE:FF"]) == 0
    out = capsys.readouterr().out
    key = keys.load(MAC)
    assert key is not None and len(key) == 32
    csv = keys.csv_path(MAC)
    assert csv.read_text() == keys.csv(key) and f'-DNODE_KEY="{csv}" flash' in out
    for path in (keys.keys_path(), csv):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    (entry,) = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert entry["action"] == "audio-node-key" and entry["mac"] == MAC and entry["made"]
    assert key.hex() not in audit_log.read_text() and key.hex() not in out
    assert main(["audio", "key", MAC]) == 0 and keys.load(MAC) == key  # a reflash keeps the node's key
    assert "kept the key" in capsys.readouterr().out


def test_audio_key_refuses_a_malformed_mac_and_writes_no_key_unaudited(monkeypatch, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="is not a MAC address"):
        main(["audio", "key", "aa:bb"])
    monkeypatch.setenv("PEWPEW_AUDIT_LOG", str(tmp_path))  # a directory: the append fails
    assert main(["audio", "key", MAC]) == 1 and not keys.keys_path().exists()


def test_the_nvs_csv_holds_the_key_in_the_nodes_namespace() -> None:
    assert keys.csv(bytes(range(32))).splitlines() == [
        "key,type,encoding,value", "pewpew,namespace,,",
        "key,data,hex2bin,000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
    ]


# ---- scans: a node is no board -----------------------------------------------------------


def test_boards_scan_lists_a_node_as_a_node_and_never_as_a_board(monkeypatch, capsys) -> None:
    node = FakeNode(b"\0" * 32)
    node.close()
    board = {"mac": "020000000001", "name": "pewpew-1", "ver": "16.0.1", "live": False, "brand": "WLED"}
    monkeypatch.setattr(wled, "fetch_info", lambda host, timeout: {"10.0.0.1": board, "10.0.0.2": node.info()}[host]
                        if host in ("10.0.0.1", "10.0.0.2") else (_ for _ in ()).throw(OSError("no answer")))
    assert main(["boards", "scan", "--subnet", "10.0.0.0/30"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("10.0.0.1 ") and "WLED 16.0.1" in lines[0]
    assert lines[1].startswith("10.0.0.2 ") and "capture node 0.1.0" in lines[1]
    assert main(["boards", "scan", "--subnet", "10.0.0.0/30", "--json"]) == 0
    assert [b["address"] for b in json.loads(capsys.readouterr().out)["boards"]] == ["10.0.0.1"]


def test_the_pages_board_scan_leaves_a_node_out_so_no_room_board_points_at_one() -> None:
    node = FakeNode(None)
    node.close()
    replies = {"10.0.0.20": {"mac": "020000000001", "ver": "16.0.1"}, "10.0.0.21": node.info()}

    def fetch(host: str, timeout: float) -> dict:
        if host not in replies:
            raise OSError("no answer")
        return replies[host]

    monitor = HealthMonitor(ddp=None, fetch=fetch, sender=lambda host, port: "10.0.0.2", now=FakeTime().now,
                            on_rebind=lambda b, a: None, scan_timeout=0.01)
    assert monitor.scan() is None
    wait_until(lambda: not monitor.state()["scan"]["running"])
    assert [f["address"] for f in monitor.state()["scan"]["found"]] == ["10.0.0.20"]
    assert wled.sweep(wled.ipaddress.IPv4Network("10.0.0.20/31"), None, fetch) == [
        wled.board_row("10.0.0.20", replies["10.0.0.20"])]


def test_a_node_is_told_from_a_board_by_its_brand() -> None:
    assert wled.is_node({"brand": "pewpew"}) and not wled.is_node({"brand": "WLED"}) and not wled.is_node({})
