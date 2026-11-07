"""Hot reload: `FileReloader` applies each saved version and keeps the
run alive when an edit is broken."""

from __future__ import annotations

import hashlib
import logging
import os
import threading

from pewpew.pace import Calls
from pewpew.reload import FileReloader


class Applied:
    """What a `FileReloader` applied, in order; it raises for bytes that
    start with "broken"."""

    def __init__(self) -> None:
        self.versions: list[bytes] = []

    def __call__(self, data: bytes) -> str:
        if data.startswith(b"broken"):
            raise ValueError("the map has no fixtures")
        self.versions.append(data)
        return f"applied {data!r}"


def make(tmp_path, data=b"one", **kw):
    path = tmp_path / "room.json"
    path.write_bytes(data)
    applied = Applied()
    queue = Calls()
    return path, applied, FileReloader(path, hashlib.sha256(data).hexdigest(), queue.call_soon, applied,
                                       noun="map", **kw)


def test_a_changed_file_is_applied_and_unchanged_bytes_are_a_no_op(tmp_path):
    path, applied, reloader = make(tmp_path)
    path.write_bytes(b"one")  # an editor "save" with nothing changed
    assert reloader.reload() is False and applied.versions == []
    path.write_bytes(b"two")
    assert reloader.reload() is True and applied.versions == [b"two"] and reloader.error is None


def test_a_broken_edit_keeps_the_last_good_version_and_says_why(tmp_path, caplog):
    path, applied, reloader = make(tmp_path)
    path.write_bytes(b"broken")
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        assert reloader.reload() is False
    assert applied.versions == []
    assert reloader.error == "reload failed, last-good map still running: ValueError: the map has no fixtures"
    # A second event for the same broken bytes is not a second traceback.
    assert reloader.reload() is False and caplog.text.count("reload failed") == 1
    path.write_bytes(b"fixed")
    assert reloader.reload() is True and reloader.error is None


def test_a_gone_file_is_reported_and_its_return_clears_the_error(tmp_path):
    path, _, reloader = make(tmp_path)
    path.write_bytes(b"two")
    assert reloader.reload() is True
    path.unlink()
    assert reloader.reload() is False
    assert reloader.error is not None and "gone" in reloader.error and "/" not in reloader.error
    path.write_bytes(b"two")  # `git stash pop`: byte-identical
    assert reloader.reload() is True and reloader.error is None


def test_two_same_length_saves_in_one_second_both_take_effect(tmp_path):
    """The bytes in hand are the truth, never a file's mtime and size."""
    path, applied, reloader = make(tmp_path, b"aaa")
    stat = path.stat()
    path.write_bytes(b"bbb")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same second, same size
    assert reloader.reload() is True and applied.versions == [b"bbb"]


def test_watcher_events_queue_reloads_on_the_loop_thread_and_stop_joins(tmp_path):
    fired = threading.Event()

    def watch(source, stop):
        assert source == tmp_path / "room.json"
        yield {"one batch"}
        fired.set()
        stop.wait()  # block like the real watcher until asked to stop

    path = tmp_path / "room.json"
    path.write_bytes(b"one")
    queued: list = []
    reloader = FileReloader(path, None, queued.append, Applied(), noun="map", watch=watch)
    reloader.start()
    assert fired.wait(2.0)
    assert reloader.active
    assert queued and queued[0] == reloader.reload
    reloader.stop()
    assert not reloader.active


def test_a_dying_watcher_disables_reload_but_not_the_run(tmp_path, caplog):
    def watch(source, stop):
        raise OSError("inotify limit")
        yield  # pragma: no cover

    _, _, reloader = make(tmp_path, watch=watch)
    with caplog.at_level(logging.ERROR, logger="pewpew"):
        reloader.start()
        reloader.stop()
    assert "watcher died" in caplog.text
