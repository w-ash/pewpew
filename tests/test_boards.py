"""`python -m pewpew boards`: backup and restore over a fake HTTP layer.
No test here reaches a network."""

from __future__ import annotations

import io
import json
import re

import pytest

from fakes import arrangement, bar, room
from pewpew import boards
from pewpew.__main__ import main

CFG = {"id": {"name": "bar-a"}, "if": {"live": {"dmx": {"seqskip": False}}}}
PRESETS = {"0": {}, "1": {"n": "fallback"}}


class FakeHttp:
    """Serves canned files per host and records uploads; `audit` is the
    audit log path, read at each upload to prove the record came first."""

    def __init__(self, files: dict[str, dict[str, bytes]], audit=None, refuse: int | None = None) -> None:
        self.files = files
        self.audit = audit
        self.refuse = refuse
        self.gets: list[str] = []
        self.uploads: list[tuple[str, str, bytes, bool]] = []

    def get(self, url: str, timeout: float) -> bytes:
        self.gets.append(url)
        host, _, name = url.removeprefix("http://").partition("/")
        if name not in self.files.get(host, {}):
            raise OSError("connection refused")
        return self.files[host][name]

    def upload(self, url: str, filename: str, data: bytes, timeout: float) -> tuple[int, str]:
        audited = self.audit is not None and self.audit.exists()
        self.uploads.append((url, filename, data, audited))
        if self.refuse is not None:
            return self.refuse, "PIN required"
        return 200, "Config restore ok.\nRebooting..." if "cfg" in filename else "File Uploaded!"


def board_files(cfg=CFG) -> dict[str, bytes]:
    return {"cfg.json": json.dumps(cfg).encode(), "presets.json": json.dumps(PRESETS).encode()}


HOSTS = ["10.0.0.11", "10.0.0.12"]


def test_backup_saves_each_boards_files(tmp_path):
    http = FakeHttp({h: board_files() for h in HOSTS})
    out = io.StringIO()
    assert boards.backup(tmp_path / "b", HOSTS, http, out) == 0
    assert http.gets == [f"http://{h}/{n}" for h in HOSTS for n in ("presets.json", "cfg.json")]
    assert json.loads((tmp_path / "b/10.0.0.12/cfg.json").read_text()) == CFG
    assert json.loads((tmp_path / "b/10.0.0.11/presets.json").read_text()) == PRESETS


def test_backup_never_overwrites_and_reports_a_failed_board(tmp_path):
    (tmp_path / "b/10.0.0.11").mkdir(parents=True)
    (tmp_path / "b/10.0.0.11/cfg.json").write_text('{"good": 1}')
    http = FakeHttp({"10.0.0.11": board_files()})
    out = io.StringIO()
    assert boards.backup(tmp_path / "b", HOSTS, http, out) == 1
    assert (tmp_path / "b/10.0.0.11/cfg.json").read_text() == '{"good": 1}'
    assert "exists; not overwritten" in out.getvalue()
    assert "10.0.0.12: cannot read /presets.json" in out.getvalue()


def test_backup_flags_skip_out_of_sequence(tmp_path):
    http = FakeHttp({"10.0.0.11": board_files({"if": {"live": {"dmx": {"seqskip": True}}}})})
    out = io.StringIO()
    boards.backup(tmp_path, ["10.0.0.11"], http, out)
    assert "'skip out-of-sequence' is on" in out.getvalue()


def saved(tmp_path, hosts=HOSTS):
    for h in hosts:
        (tmp_path / h).mkdir(parents=True, exist_ok=True)
        for name, data in board_files().items():
            (tmp_path / h / name).write_bytes(data)
    return tmp_path


def test_a_dry_run_restore_prints_the_plan_and_sends_nothing(tmp_path, audit_log):
    http = FakeHttp({})
    out = io.StringIO()
    assert boards.restore(saved(tmp_path), HOSTS, http, dry_run=True, argv=[], out=out) == 0
    assert http.uploads == [] and not audit_log.exists()
    text = out.getvalue()
    assert "would upload" in text and "to http://10.0.0.12/upload as /cfg.json (the board reboots)" in text
    assert "dry run: nothing sent" in text


def test_a_restore_audits_before_the_first_write_presets_first(tmp_path, audit_log):
    http = FakeHttp({}, audit=audit_log)
    argv = ["boards", "restore", str(tmp_path)]
    assert boards.restore(saved(tmp_path), HOSTS, http, dry_run=False, argv=argv, out=io.StringIO()) == 0
    assert [(u, f) for u, f, _, _ in http.uploads] == [
        ("http://10.0.0.11/upload", "/presets.json"), ("http://10.0.0.11/upload", "/cfg.json"),
        ("http://10.0.0.12/upload", "/presets.json"), ("http://10.0.0.12/upload", "/cfg.json"),
    ]
    assert all(audited for *_, audited in http.uploads)
    [entry] = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert entry["action"] == "boards-restore" and entry["argv"] == argv
    assert entry["targets"] == HOSTS
    assert entry["files"][0] == "10.0.0.11/presets.json"


def test_a_restore_stops_at_the_first_refusal(tmp_path):
    http = FakeHttp({}, refuse=401)
    out = io.StringIO()
    assert boards.restore(saved(tmp_path), HOSTS, http, dry_run=False, argv=[], out=out) == 1
    assert len(http.uploads) == 1
    assert "refused (401): PIN required; stopping" in out.getvalue()


def test_a_bad_file_or_a_missing_board_restores_nothing(tmp_path, audit_log):
    saved(tmp_path, ["10.0.0.11"])
    (tmp_path / "10.0.0.11/cfg.json").write_text("[1, 2]")
    http = FakeHttp({})
    with pytest.raises(SystemExit, match="nothing restored") as exc:
        boards.restore(tmp_path, HOSTS, http, dry_run=False, argv=[], out=io.StringIO())
    assert "not a JSON object" in str(exc.value) and "no backup for 10.0.0.12" in str(exc.value)
    assert http.uploads == [] and not audit_log.exists()


def test_the_command_takes_boards_from_a_list_or_a_room(tmp_path, monkeypatch, capsys):
    http = FakeHttp({})
    monkeypatch.setattr(boards, "UrllibHttp", lambda: http)
    saved(tmp_path / "b", ["10.0.0.11", "10.0.0.12"])
    rc = main(["boards", "restore", str(tmp_path / "b"), "--board", "10.0.0.11:4049", "--board", "10.0.0.12:4048=0+64",
               "--dry-run"])
    assert rc == 0 and http.uploads == []
    assert capsys.readouterr().out.count("would upload") == 4

    rig_file = tmp_path / "rig.arrangement.json"
    rig_file.write_text(json.dumps(arrangement(bar())))
    monkeypatch.setattr(boards, "UrllibHttp", lambda: FakeHttp({"10.0.0.11": board_files()}))
    assert main(["boards", "backup", str(tmp_path / "new"), "--map", str(rig_file)]) == 0
    assert (tmp_path / "new/10.0.0.11/cfg.json").exists()


def test_the_old_room_flag_still_works_with_a_warning(tmp_path, monkeypatch, capsys):
    room_file = tmp_path / "room.json"
    room_file.write_text(json.dumps(room(bar())))
    monkeypatch.setattr(boards, "UrllibHttp", lambda: FakeHttp({"10.0.0.11": board_files()}))
    assert main(["boards", "backup", str(tmp_path / "new"), "--room", str(room_file)]) == 0
    err = capsys.readouterr().err
    assert "--room is the old name of --map" in err and "this is a room map" in err
    assert (tmp_path / "new/10.0.0.11/cfg.json").exists()


@pytest.mark.parametrize("extra, message", [
    ([], "one of the arguments --map --room --board is required"),
    (["--map", "r.json", "--board", "10.0.0.11"], "argument --board: not allowed with argument --map"),
])
def test_a_board_list_needs_exactly_one_source(tmp_path, extra, message, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["boards", "backup", str(tmp_path), *extra])
    assert exc.value.code == 2 and message in capsys.readouterr().err  # a usage error


@pytest.mark.parametrize("board, message", [
    ("lights.example.com", "--board: 'lights.example.com' is not an IPv4 address"),
    ("10.0.0.11:abc", "--board: port 'abc' is not 1-65535"),
    ("10.0.0.11=0", "--board: bad DDP target '10.0.0.11=0'; expected HOST[:PORT]=START+COUNT"),
])
def test_a_bad_board_is_one_line(board, message):
    with pytest.raises(SystemExit, match=re.escape(message)):
        main(["boards", "backup", "x", "--board", board])
