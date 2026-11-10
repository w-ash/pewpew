"""pewpew.health: `/json/info` parsing, thresholds, reboot and drift
detection over canned replies, a monitor that never blocks the loop, mDNS
addressing, the MAC check, and find boards."""

from __future__ import annotations

import ipaddress
import threading
import time
import urllib.error

import pytest

from fakes import FLOW, FakeTime, ddp_sink, hosted, wait_until
from pewpew import wled
from pewpew.health import REBOOT_WARN_S, SETTLE_S, BoardHealth, HealthMonitor, extract
from pewpew.mapping import line
from pewpew.pace import PacedLoop, PaceStats
from pewpew.sinks.ddp import Board, is_ipv4
from pewpew.wled import fetch_info as REAL_FETCH_INFO  # before conftest swaps it out
from pewpew.wled import scan_lines

US = "10.0.0.2"
SINCE = -10.0  # the first DDP frame went out well before the polls


def info(**kw) -> dict:
    """A healthy `/json/info` reply from a 1,280-px board, with overrides."""
    base = {
        "ver": "16.0.1", "live": True, "lip": US, "uptime": 812, "freeheap": 151000,
        "leds": {"count": 1280, "fps": 39},
        "wifi": {"bssid": "x", "rssi": -61, "signal": 78, "channel": 6},
    }
    for key, value in kw.items():
        if key in ("fps", "count"):
            base["leds"] = {**base["leds"], key: value}
        elif key in ("rssi", "channel"):
            base["wifi"] = {**base["wifi"], key: value}
        else:
            base[key] = value
    return base


def judged(*replies: dict, sent: float = 40.0, streaming: bool = True, now: float = 0.0) -> BoardHealth:
    board = BoardHealth("10.0.0.11", 1280)
    for reply in replies:
        board.record(reply, now, US)
    board.assess(now, sent, SINCE if streaming else None)
    return board


def test_extract_reads_the_health_fields_and_the_debug_reset_reason():
    assert extract(info()) == {
        "fps": 39, "count": 1280, "rssi": -61, "channel": 6, "uptime": 812, "live": True,
        "lip": US, "freeheap": 151000, "ver": "16.0.1", "reset_reason": None,
    }
    assert extract(info(resetReason0=15))["reset_reason"] == 15
    assert extract({})["fps"] is None  # a field left out is None, never a KeyError


def test_a_field_of_the_wrong_type_is_left_out_and_the_board_is_still_judged():
    """A device that sends `"rssi": "-50"` (or a non-WLED device at the
    board's address) must not stop the health of every board."""
    reply = info(rssi="-50", channel=[6], fps=None, live="yes", lip=7, ver=16, mac=12, resetReason0={"x": 1})
    sample = extract({**reply, "leds": [], "wifi": "x"})
    assert (sample["fps"], sample["count"], sample["rssi"], sample["channel"]) == (None, None, None, None)
    assert (sample["live"], sample["lip"], sample["ver"], sample["reset_reason"]) == (None, None, None, None)
    board = judged(reply)
    assert board.level == "ok" and board.mac is None and board.describe()["rssi"] is None


def test_a_healthy_board_is_ok():
    board = judged(info())
    assert (board.level, board.reasons) == ("ok", [])


@pytest.mark.parametrize("reply, level, words", [
    (info(live=False), "bad", "not live"),
    (info(lip="10.0.0.99"), "bad", "10.0.0.99"),
    (info(fps=19), "bad", "19 of 40 fps"),
    (info(fps=34), "warn", "34 of 40 fps"),
    (info(fps=36), "ok", None),  # 0.9 x 40 holds
    (info(rssi=-81), "bad", "-81 dBm"),
    (info(rssi=-72), "warn", "-72 dBm"),
    (info(freeheap=12000), "bad", "low heap"),
    (info(freeheap=25000), "warn", "low heap"),
    (info(count=1000), "bad", "1000 LEDs configured, 1280 streamed"),
    (info(count=1500), "warn", "1500 LEDs configured"),
])
def test_thresholds(reply, level, words):
    board = judged(reply)
    assert board.level == level
    if words is None:
        assert board.reasons == []
    else:
        assert any(words in r for r in board.reasons), board.reasons


def test_not_live_and_fps_are_not_judged_without_a_stream():
    board = judged(info(live=False, fps=0), streaming=False)
    assert board.level == "ok"


def test_stream_checks_judge_only_a_poll_sent_after_the_stream_settled():
    board = BoardHealth("10.0.0.11", 1280)
    board.record(info(live=False, lip="10.0.0.99", fps=0), 0.0, US)  # polled before the first frame
    board.assess(0.0, 40.0, None)
    assert board.level == "ok"
    board.assess(5.0, 40.0, 0.0)  # frames go out from t=0; the sample is still from t=0
    assert board.level == "ok"
    board.record(info(live=False, lip="10.0.0.99", fps=0), SETTLE_S - 0.1, US)
    board.assess(5.0, 40.0, 0.0)
    assert board.level == "ok"
    board.record(info(live=False), SETTLE_S, US)
    board.assess(5.0, 40.0, 0.0)
    assert board.level == "bad" and "not live" in board.reasons[0]
    board.record(info(lip="10.0.0.99"), SETTLE_S + 6, US)
    board.assess(10.0, 40.0, 0.0)
    assert board.level == "bad" and "10.0.0.99" in board.reasons[0]


def test_the_worst_threshold_sets_the_level():
    board = judged(info(rssi=-72, live=False))
    assert board.level == "bad" and len(board.reasons) == 2


def test_one_failed_poll_warns_and_two_in_a_row_are_bad():
    board = judged(info())
    board.fail("TimeoutError")
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "warn" and "no answer" in board.reasons[0]
    board.fail("TimeoutError")
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "bad" and "unreachable" in board.reasons[0]
    board.record(info(), 0.0, US)
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "ok"


def test_a_board_never_answered_is_pending_then_warns():
    board = BoardHealth("10.0.0.11", 1280)
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "pending"
    board.fail("OSError")
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "warn"


def test_an_uptime_drop_is_a_reboot_that_warns_for_ten_minutes(caplog):
    board = BoardHealth("10.0.0.11", 1280)
    board.record(info(uptime=5000), 0.0, US)
    board.record(info(uptime=5006), 6.0, US)
    assert board.reboots == 0
    board.record(info(uptime=3, resetReason0=15), 12.0, US)
    assert board.reboots == 1 and board.last_reset_reason == 15
    assert "rebooted" in caplog.text and "reset reason 15" in caplog.text
    board.assess(12.0 + REBOOT_WARN_S - 1, 40.0, SINCE)
    assert board.level == "warn" and board.reasons == ["rebooted"]
    board.assess(12.0 + REBOOT_WARN_S, 40.0, SINCE)
    assert board.level == "ok"
    assert board.describe()["reboots"] == 1  # the count stays for the page


def boards3() -> list[Board]:
    return [Board(f"10.0.0.1{i + 1}", 1280 * i, 1280) for i in range(3)]


class CannedFetch:
    """Replies per host, recording each request."""

    def __init__(self, replies: dict[str, dict]) -> None:
        self.replies = replies
        self.calls: list[str] = []

    def __call__(self, host: str, timeout: float) -> dict:
        self.calls.append(host)
        reply = self.replies.get(host)
        if reply is None:
            raise TimeoutError("timed out")
        return reply


class Stream:
    """The DDP sink as the monitor reads it: its boards, its frame count and
    where frames go. `boards` may change between steps, as a reload does."""

    def __init__(self, boards) -> None:
        self.boards = boards
        self.frames_sent = 0

    def address(self, host, port=4048):
        return (host, port) if is_ipv4(host) else None


def monitor_for(boards, fetch, ft, ddp=None, **kw) -> HealthMonitor:
    return HealthMonitor(ddp or Stream(boards), fetch=fetch, sender=lambda host, port: US, now=ft.now, **kw)


def test_the_monitor_polls_one_board_at_a_time_each_every_period():
    ft = FakeTime()
    boards = boards3()
    fetch = CannedFetch({b.host: info() for b in boards})
    monitor = monitor_for(boards, fetch, ft, period=6.0)
    for _ in range(12):  # 12 s of 1-s steps
        monitor.step()
        ft.t += 1.0
    # A board every 2 s, round robin: each board twice in 12 s.
    assert fetch.calls == [b.host for b in boards] * 2
    state = monitor.state()
    assert [b["host"] for b in state["boards"]] == [b.host for b in boards]
    assert {b["level"] for b in state["boards"]} == {"ok"}


def test_the_monitor_follows_a_new_board_set():
    ft = FakeTime()
    boards = boards3()
    fetch = CannedFetch({b.host: info() for b in boards})
    current = list(boards)
    monitor = monitor_for(current, fetch, ft)
    monitor.step()
    current[:] = boards[1:]
    ft.t += 10.0
    monitor.step()
    assert [b["host"] for b in monitor.state()["boards"]] == ["10.0.0.12", "10.0.0.13"]


def test_the_monitor_measures_the_sent_and_loop_rates():
    ft = FakeTime()
    stats, stream = PaceStats(), Stream([])
    monitor = monitor_for([], CannedFetch({}), ft, ddp=stream, stats=stats, target=60.0)
    monitor.step()
    ft.t += 2.0
    stream.frames_sent += 80
    stats.ticks += 100  # 50 fps against a 60 target
    monitor.step()
    state = monitor.state()
    assert state["sent_fps"] == 40.0
    assert state["loop"]["fps"] == 50.0 and state["loop"]["level"] == "warn"
    assert state["loop"]["fix"] == "Check the laptop is on AC and nothing else is busy."
    assert state["awake"] == {"requested": False, "held": False, "detail": None, "level": "ok", "fix": None}


def test_a_sleep_assertion_not_held_says_how_to_get_it_back():
    class Awake:
        def check(self) -> None:
            pass

        def state(self) -> dict:
            return {"requested": True, "held": False, "detail": "caffeinate exited"}

    monitor = monitor_for([], CannedFetch({}), FakeTime(), awake=Awake())
    monitor.step()
    awake = monitor.state()["awake"]
    assert awake["level"] == "warn" and "launchctl kickstart -k gui/$UID/local.pewpew.aura" in awake["fix"]


def test_the_dark_bars_hint_waits_until_the_stream_reaches_the_board():
    assert judged(info()).fix.startswith("If the bars stay dark")
    assert judged(info(), streaming=False).fix is None  # no frame sent yet: nothing to say about dark bars


def test_a_reboot_that_changed_the_led_count_points_at_the_backup():
    assert judged(info(count=1000)).fix.startswith("Set the LED count")
    board = judged(info(uptime=5000), info(uptime=3, count=1000))
    assert board.reboots == 1 and "restore its backup" in board.fix and "boards restore" in board.fix
    # A reboot that kept a count already wrong is no reset: set the count.
    assert judged(info(uptime=5000, count=1000), info(uptime=3, count=1000)).fix.startswith("Set the LED count")
    # A second reboot keeps the reset in view until the count is right.
    again = judged(info(uptime=5000), info(uptime=3, count=1000), info(uptime=1, count=1000))
    assert again.reboots == 2 and "restore its backup" in again.fix
    assert judged(info(uptime=5000), info(uptime=3, count=1000), info(uptime=9)).reboot_moved_count is False
    # A count set by hand since the reset, even to another wrong value, is no reset.
    edited = judged(info(uptime=5000), info(uptime=3, count=1000), info(uptime=9, count=1500))
    assert edited.fix.startswith("Set the LED count")
    # A reply that leaves the count out is no edit.
    gap = judged(info(uptime=5000), info(uptime=3, count=1000), {**info(uptime=9), "leds": {}},
                 info(uptime=15, count=1000))
    assert "restore its backup" in gap.fix


def test_find_boards_is_offered_as_the_page_offers_it():
    board = BoardHealth("10.0.0.11", 1280, name="A")
    board.fail("timed out")
    board.assess(0.0, 40.0, SINCE)
    assert board.level == "warn" and 'If it stays unreachable, tap "find boards"' in board.fix
    board.fail("timed out")
    board.assess(0.0, 40.0, SINCE)
    assert board.describe()["lost"] and 'Tap "find boards", then "use for A"' in board.fix
    unnamed = BoardHealth("10.0.0.11", 1280)  # no room map: no button
    unnamed.fail("timed out")
    unnamed.assess(0.0, 40.0, SINCE)
    assert "then run with that address" in unnamed.fix
    # One missed poll on a board bad for another reason: not lost, and the worse check's fix leads.
    short = BoardHealth("10.0.0.11", 1280, name="A")
    short.record(info(count=1000), 0.0, US)
    short.fail("timed out")
    short.assess(0.0, 40.0, SINCE)
    assert short.level == "bad" and not short.describe()["lost"] and short.fix.startswith("Set the LED count")


def test_the_mdns_fix_gives_the_name_as_wleds_field_holds_it():
    board = BoardHealth("pewpew-9.LOCAL", 1280)
    board.fail("timed out")
    board.assess(0.0, 40.0, SINCE)
    assert board.fix.endswith("WLED's WiFi settings is still pewpew-9.")


def test_a_poll_before_the_first_frame_is_not_flagged_not_live(caplog):
    """At launch the first poll goes out before any DDP frame: the board is
    not live yet, and that is not a fault."""
    ft = FakeTime()
    boards = boards3()[:1]
    reply = {"r": info(live=False, fps=0)}
    fetch = lambda host, timeout: reply["r"]
    sent = Stream(boards)
    monitor = monitor_for(boards, fetch, ft, ddp=sent, period=6.0)
    monitor.step()  # t=0: polled, nothing sent yet
    assert monitor.state()["boards"][0]["level"] == "ok"
    for _ in range(5):  # frames go out from t=1; the board takes the stream
        ft.t += 1.0
        sent.frames_sent += 40
        reply["r"] = info()
        monitor.step()
        assert monitor.state()["boards"][0]["level"] == "ok"
    ft.t += 1.0
    sent.frames_sent += 40
    monitor.step()  # t=6: the next poll, after the stream settled
    assert monitor.state()["boards"][0]["level"] == "ok"
    assert "not live" not in caplog.text
    reply["r"] = info(live=False)  # the board drops the stream
    ft.t += 6.0
    sent.frames_sent += 240
    monitor.step()
    assert monitor.state()["boards"][0]["level"] == "bad"
    assert "not live" in caplog.text


def test_a_board_level_change_is_logged(caplog):
    ft = FakeTime()
    boards = boards3()[:1]
    fetch = CannedFetch({})
    monitor = monitor_for(boards, fetch, ft, period=6.0)
    monitor.step()  # first failure: pending -> warn
    ft.t += 6.0
    monitor.step()  # second: warn -> bad
    assert "10.0.0.11 pending -> warn" in caplog.text
    assert "10.0.0.11 warn -> bad: unreachable" in caplog.text
    assert monitor.state()["level"] == "bad"


def test_a_slow_board_never_blocks_the_loop_or_the_state():
    """The fetch hangs until released; the loop and every state() read go on."""
    release = threading.Event()
    entered = threading.Event()

    def hanging(host: str, timeout: float) -> dict:
        entered.set()
        release.wait(10.0)
        return info()

    boards = boards3()
    monitor = HealthMonitor(Stream(boards), fetch=hanging, sender=lambda h, p: US, step=0.01)
    reads: list[float] = []

    def read_health(t, frame) -> None:  # a sink reading the panel every frame
        began = time.perf_counter()
        monitor.state()
        reads.append(time.perf_counter() - began)

    ft = FakeTime()
    loop = PacedLoop(hosted(FLOW, line(64)), fps=60, on_frame=[read_health], now=ft.now, sleep=ft.sleep)
    monitor.start()
    try:
        assert entered.wait(5.0)
        began = time.perf_counter()
        loop.run(frames=120)
        assert time.perf_counter() - began < 2.0
        assert len(reads) == 120 and max(reads) < 0.05
    finally:
        release.set()
        monitor.stop()


# ---- addressing: mDNS names, the MAC check, find boards ------------------------

MAC_A, MAC_B = "020000000001", "0123456789ab"


class Net:
    """Names a fake resolver answers, and the audit records written."""

    def __init__(self, names: dict[str, str]) -> None:
        self.names = names
        self.records: list[dict] = []
        self.audit_fails = False

    def resolve(self, name: str) -> str:
        if name not in self.names:
            raise OSError(8, "nodename nor servname provided, or not known")
        return self.names[name]

    def record(self, action: str, **fields) -> None:
        if self.audit_fails:
            raise FileNotFoundError(2, "No such file or directory", "/Users/someone/.local/state/audit.jsonl")
        self.records.append({"action": action, **fields})


def named_rig(boards, replies, names, **kw):
    """A started DDP sink on a recorder, and a monitor over it."""
    sink, _ = ddp_sink(boards, sum(b.count for b in boards))
    net = Net(names)
    fetch = CannedFetch(replies)
    ft = FakeTime()
    monitor = monitor_for(
        boards, fetch, ft, ddp=sink, names=lambda: [chr(65 + i) for i in range(len(boards))],
        argv=["run"], resolve=net.resolve, record=net.record, **kw,
    )
    return monitor, sink, net, fetch, ft


def row(monitor, i=0) -> dict:
    return monitor.state()["boards"][i]


def test_a_named_board_is_looked_up_audited_and_followed_to_a_new_address():
    board = Board("pewpew-1.local", 0, 1280)
    monitor, sink, net, fetch, ft = named_rig(
        [board], {"192.0.2.47": info(mac=MAC_A)}, {"pewpew-1.local": "192.0.2.47"},
    )
    assert sink.address("pewpew-1.local") is None  # nothing is sent before the lookup
    monitor.step()
    assert sink.address("pewpew-1.local") == ("192.0.2.47", 4048)
    assert net.records == [{
        "action": "ddp-readdress", "argv": ["run"], "board": "A", "host": "pewpew-1.local",
        "address": "192.0.2.47", "previous": None,
    }]
    assert (row(monitor)["board"], row(monitor)["address"], row(monitor)["mac"]) == ("A", "192.0.2.47", MAC_A)
    # A power cycle: the board comes back on a new DHCP address.
    fetch.replies = {"192.0.2.20": info(mac=MAC_A, uptime=3)}
    net.names["pewpew-1.local"] = "192.0.2.20"
    ft.t += 10.0
    monitor.step()
    assert sink.address("pewpew-1.local") == ("192.0.2.20", 4048)
    assert net.records[-1]["previous"] == "192.0.2.47"
    assert (row(monitor)["address"], row(monitor)["reboots"]) == ("192.0.2.20", 1)


def test_named_boards_that_swapped_addresses_each_follow_their_name():
    boards = [Board("pewpew-1.local", 0, 1280), Board("pewpew-2.local", 1280, 1280)]
    monitor, sink, net, fetch, ft = named_rig(
        boards, {"10.0.0.11": info(mac=MAC_A), "10.0.0.12": info(mac=MAC_B)},
        {"pewpew-1.local": "10.0.0.11", "pewpew-2.local": "10.0.0.12"},
    )
    monitor.step(); monitor.step()
    fetch.replies = {"10.0.0.11": info(mac=MAC_B), "10.0.0.12": info(mac=MAC_A)}
    net.names.update({"pewpew-1.local": "10.0.0.12", "pewpew-2.local": "10.0.0.11"})
    for _ in range(4):
        ft.t += 3.0
        monitor.step()
    assert sink.address("pewpew-1.local") == ("10.0.0.12", 4048)
    assert sink.address("pewpew-2.local") == ("10.0.0.11", 4048)
    assert [b["level"] for b in monitor.state()["boards"]] == ["ok", "ok"]


def test_another_mac_at_an_ipv4_board_is_bad_and_says_how_to_find_it():
    monitor, *_, fetch, ft = named_rig([Board("10.0.0.11", 0, 1280)], {"10.0.0.11": info(mac=MAC_A)}, {})
    monitor.step()
    fetch.replies["10.0.0.11"] = info(mac=MAC_B)
    ft.t += 10.0
    monitor.step()
    r = row(monitor)
    assert r["level"] == "bad" and any("01:23:45:67:89:ab" in why for why in r["reasons"])
    assert 'Tap "find boards", then "use for A"' in r["fix"]


def test_a_reply_from_another_device_ends_the_unreachable_reason():
    monitor, *_, fetch, ft = named_rig([Board("10.0.0.11", 0, 1280)], {"10.0.0.11": info(mac=MAC_A)}, {})
    monitor.step()
    fetch.replies = {}  # two timeouts in a row
    for _ in range(2):
        ft.t += 10.0
        monitor.step()
    assert any(why.startswith("unreachable") for why in row(monitor)["reasons"])
    fetch.replies["10.0.0.11"] = info(mac=MAC_B)
    ft.t += 10.0
    monitor.step()
    assert [why.split(" (")[0] for why in row(monitor)["reasons"]] == ["a different device answers at 10.0.0.11"]


def test_a_found_board_keeps_its_field_types_and_a_device_without_them_is_no_board():
    replies = {
        "10.250.0.1": {"ver": "16.0.1", "mac": MAC_A, "name": 7, "live": "yes", "lm": None, "lip": ["x"]},
        "10.250.0.2": {"ver": 1, "mac": []},
    }

    def fetch(host, timeout):
        return replies[host]

    found = wled.sweep(ipaddress.IPv4Network("10.250.0.0/30"), None, fetch, 0.01)
    assert found == [{"address": "10.250.0.1", "mac": MAC_A, "name": None, "ver": "16.0.1", "live": None,
                      "lm": None, "lip": None}]


def test_a_failed_request_keeps_the_http_status_and_reason():
    with urllib.error.HTTPError("http://10.0.0.11/json/info", 404, "Not Found", None, None) as error:
        assert wled.failure(error) == "HTTPError: HTTP Error 404: Not Found"


def test_a_stopped_sweep_asks_no_more_addresses():
    asked, stop = [], threading.Event()

    def fetch(host, timeout):
        asked.append(host)
        stop.set()  # the monitor stops while the first request is in flight
        raise OSError("no answer")

    assert wled.sweep(ipaddress.IPv4Network("10.250.0.0/24"), None, fetch, 0.01, workers=1, stop=stop) == []
    assert asked == ["10.250.0.1"]


def test_a_name_that_does_not_resolve_is_unreachable():
    monitor, _sink, *_ = named_rig([Board("pewpew-9.local", 0, 1280)], {}, {})
    monitor.step()
    r = row(monitor)
    assert r["level"] == "warn" and "pewpew-9.local does not resolve" in r["reasons"][0]
    assert "looks pewpew-9.local up again" in r["fix"] and r["address"] is None
    assert "find boards" not in r["fix"]  # a rebind refuses a board named by mDNS
    assert r["fix"].endswith("WLED's WiFi settings is still pewpew-9.")  # WLED adds the .local


def test_without_an_audit_record_no_frame_moves_and_the_page_gets_no_path():
    monitor, sink, net, fetch, _ft = named_rig(
        [Board("pewpew-1.local", 0, 1280)], {}, {"pewpew-1.local": "192.0.2.47"},
    )
    net.audit_fails = True
    monitor.step()
    assert sink.address("pewpew-1.local") is None and fetch.calls == []
    reason = row(monitor)["reasons"][0]
    assert "could not write the audit record (No such file or directory)" in reason
    assert "/Users" not in reason


def test_no_route_to_host_names_macos_local_network_privacy():
    import errno
    import urllib.error

    def fetch(host, timeout):
        raise urllib.error.URLError(OSError(errno.EHOSTUNREACH, "No route to host"))

    monitor = monitor_for([Board("10.0.0.11", 0, 1280)], fetch, FakeTime())
    monitor.step()
    r = row(monitor)
    assert "No route to host" in r["reasons"][0] and "Local Network" in r["fix"]
    assert "this terminal app" not in r["fix"] and "/" not in r["fix"]  # the program by name, never a path


def test_scan_matches_boards_by_mac_and_rebind_takes_only_a_scanned_address():
    asked = []
    monitor, *_, fetch, _ft = named_rig(
        [Board("192.0.2.47", 0, 1280)], {"192.0.2.47": info(mac=MAC_A)}, {},
        on_rebind=lambda b, a: asked.append((b, a)), scan_timeout=0.01,
    )
    monitor.step()
    assert monitor.rebind("A", "192.0.2.20") == "that address was not in the last scan; scan again"
    fetch.replies = {
        "10.0.0.20": info(mac=MAC_A), "10.0.0.21": info(mac=MAC_B), "10.0.0.1": {"model": "router"},
    }
    assert monitor.scan() is None
    wait_until(lambda: not monitor.state()["scan"]["running"])
    scan = monitor.state()["scan"]
    assert scan["subnet"] == "10.0.0.0/24"  # the sender address faked as 10.0.0.2
    by_address = {f["address"]: f for f in scan["found"]}
    assert set(by_address) == {"10.0.0.20", "10.0.0.21"}
    assert (by_address["10.0.0.20"]["board"], by_address["10.0.0.21"]["board"]) == ("A", None)
    assert monitor.rebind("Z", "10.0.0.20") == "unknown board 'Z'; boards: A"
    assert monitor.rebind("A", "10.0.0.20") is None and asked == [("A", "10.0.0.20")]


def test_rebind_is_refused_without_a_room_and_for_a_name_pewpew_follows():
    plain, *_ = named_rig([Board("10.0.0.11", 0, 1280)], {}, {})
    assert plain.rebind("A", "10.0.0.12") == (
        "rebinding a board needs an arrangement map (run --map RIG.arrangement.json)")
    named, *_ = named_rig([Board("pewpew-1.local", 0, 1280)], {}, {}, on_rebind=lambda b, a: None)
    assert named.rebind("A", "10.0.0.12").startswith("board A is named pewpew-1.local, which pewpew follows")


class _Reply:
    def __init__(self, chunks, clock):
        self.chunks, self.clock = list(chunks), clock

    def read1(self, n):
        self.clock[0] += 1.0
        return self.chunks.pop(0) if self.chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize("chunks, error", [([b"x" * 16384] * 5, "too large"), ([b" "] * 10, "took too long")])
def test_fetch_info_bounds_the_size_and_the_time_of_a_reply(monkeypatch, chunks, error):
    clock = [0.0]
    monkeypatch.setattr(wled.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(wled.urllib.request, "urlopen", lambda url, timeout: _Reply(chunks, clock))
    with pytest.raises((ValueError, TimeoutError), match=error):
        REAL_FETCH_INFO("10.0.0.11", 2.0)


def test_scan_lines_reads_like_the_terminal_table():
    found = [{"address": "192.0.2.20", "mac": MAC_A, "name": "pewpew-1", "ver": "16.0.1",
              "live": True, "lm": "DDP", "lip": "192.0.2.10"},
             {"address": "192.0.2.21", "mac": MAC_B, "name": None, "ver": "16.0.1",
              "live": False, "lm": "", "lip": ""}]
    assert scan_lines(found) == [
        "192.0.2.20       pewpew-1          MAC 02:00:00:00:00:01  WLED 16.0.1  live DDP from 192.0.2.10",
        "192.0.2.21       ?                 MAC 01:23:45:67:89:ab  WLED 16.0.1  not live",
    ]


# ---- the board's target refresh rate and the host's AWDL ---------------------------


class Rated(Stream):
    """A sink fed at `max_fps`, as the monitor reads its rate."""

    def __init__(self, boards, max_fps: float) -> None:
        super().__init__(boards)
        self.max_fps = max_fps


def cfg(fps: int) -> dict:
    return {"hw": {"led": {"total": 1280, "fps": fps}}}


def test_a_target_refresh_rate_below_the_sent_rate_warns_with_the_setting_to_change():
    ft = FakeTime()
    boards = boards3()[:1]
    reads: list[str] = []

    def fetch_cfg(host, timeout):
        reads.append(host)
        return cfg(42)

    monitor = monitor_for(boards, CannedFetch({boards[0].host: info()}), ft, ddp=Rated(boards, 60.0),
                          target=60.0, fetch_cfg=fetch_cfg)
    monitor.step()
    (row,) = monitor.state()["boards"]
    assert row["level"] == "warn"
    assert "WLED target refresh rate 42 fps, below the 60 sent" in row["reasons"]
    assert "Target refresh rate to 60 or more" in row["fix"]
    for _ in range(12):  # later polls do not read the settings again
        ft.t += 1.0
        monitor.step()
    assert reads == [boards[0].host]


@pytest.mark.parametrize("fps", [60, 120, 0])
def test_a_target_refresh_rate_at_or_above_the_sent_rate_or_none_is_ok(fps):
    ft = FakeTime()
    boards = boards3()[:1]
    monitor = monitor_for(boards, CannedFetch({boards[0].host: info()}), ft, ddp=Rated(boards, 60.0),
                          target=60.0, fetch_cfg=lambda host, timeout: cfg(fps))
    monitor.step()
    assert monitor.state()["boards"][0]["level"] == "ok"


def test_the_settings_are_read_again_after_a_reboot():
    board = BoardHealth("10.0.0.11", 1280)
    board.record(info(uptime=900), 0.0, US)
    board.cfg_read, board.target_fps = True, 60
    board.record(info(uptime=3), 6.0, US)
    assert board.cfg_read is False


def test_awdl_on_the_route_to_the_boards_is_logged_when_it_comes_and_goes(caplog):
    ft = FakeTime()
    boards = boards3()[:1]
    verdicts = iter([True, True, False])
    asked: list[str] = []

    def stalls(address):
        asked.append(address)
        return next(verdicts)

    monitor = monitor_for(boards, CannedFetch({boards[0].host: info()}), ft, period=6.0, stalls=stalls)
    caplog.set_level("INFO", logger="pewpew.health")
    for _ in range(13):
        monitor.step()
        ft.t += 1.0
    assert asked == [boards[0].host] * 3  # once a period
    messages = [r.getMessage() for r in caplog.records if "AWDL" in r.getMessage()]
    assert len(messages) == 2
    assert messages[0].startswith("AWDL is active") and "sudo ifconfig awdl0 down" in messages[0]
    assert messages[1] == "AWDL is no longer active on the route to the boards"
