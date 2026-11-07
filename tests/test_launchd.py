"""deploy/launchd: the LaunchAgent template is a valid plist once its
placeholders are filled, and holds nothing personal."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

from fakes import EXAMPLE_ROOM
from pewpew.__main__ import main

TEMPLATE = Path(__file__).parents[1] / "deploy" / "launchd" / "pewpew-aura.plist"

VALUES = {
    "__REPO__": "/opt/pewpew/repo",
    "__PATTERN__": "plasma",
    "__ROOM__": "/opt/pewpew/room.json",
    "__LOOKS__": "/opt/pewpew/looks.json",
    "__HOST__": "192.0.2.2",  # TEST-NET-1
    "__LOGS__": "/opt/pewpew/logs",
    "__FPS__": "40",
}


def test_the_template_renders_to_a_valid_launch_agent():
    text = TEMPLATE.read_text()
    assert set(re.findall(r"__[A-Z]+__", text)) == set(VALUES)
    for name, value in VALUES.items():
        text = text.replace(name, value)
    job = plistlib.loads(text.encode())
    assert job["KeepAlive"] == {"SuccessfulExit": False}
    assert job["RunAtLoad"] is True
    assert job["ProcessType"] == "Interactive"
    assert job["WorkingDirectory"] == "/opt/pewpew/repo"
    assert job["StandardOutPath"] == job["StandardErrorPath"] == "/opt/pewpew/logs/pewpew-aura.log"
    args = job["ProgramArguments"]
    assert args[:5] == ["/opt/pewpew/repo/.venv/bin/python", "-m", "pewpew", "run", "plasma"]
    for flag in ("--armed", "--unattended", "--preview"):
        assert flag in args
    for flag, value in (("--looks", "/opt/pewpew/looks.json"), ("--room", "/opt/pewpew/room.json"),
                        ("--host", "192.0.2.2"), ("--ddp-fps", "40"),
                        ("--trigger-log", "/opt/pewpew/logs/triggers.jsonl")):
        assert args[args.index(flag) + 1] == value


def test_the_template_holds_no_personal_paths_or_addresses():
    text = TEMPLATE.read_text()
    assert "/Users/" not in text and "/home/" not in text
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)


def test_the_template_never_keeps_a_feature_log():
    # A microphone's feature log is close to a recording of speech (ADR-009, "live input").
    job = plistlib.loads(TEMPLATE.read_bytes())
    assert not any(arg.startswith("--feature-log") for arg in job["ProgramArguments"])
    assert "--feature-log" not in TEMPLATE.read_text()  # not even in a comment to copy from


def test_the_runner_accepts_the_templates_arguments(tmp_path, capsys):
    # A dry run reads the looks file (one not saved yet is an empty book)
    # and checks that the trigger log's folder takes the file.
    values = {**VALUES, "__ROOM__": str(EXAMPLE_ROOM), "__LOOKS__": str(tmp_path / "looks.json"),
              "__LOGS__": str(tmp_path)}
    text = TEMPLATE.read_text()
    for name, value in values.items():
        text = text.replace(name, value)
    args = plistlib.loads(text.encode())["ProgramArguments"][3:]
    assert main([*args, "--dry-run"]) == 0  # parsed and checked; nothing sent
    assert "dry run: nothing sent" in capsys.readouterr().out
