"""The agent docs (ADR-023): the `authoring-looks` skill, the `look-critic`
subagent, the looks rule and `.mcp.json` stay in step with the code they
name. Each look shape the skill teaches checks and renders without a
warning, the critic's tools are tools the server lists, and each server
entry is a command that parses."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pewpew.__main__ import parse
from pewpew.lab import check_look, render

ROOT = Path(__file__).parent.parent
SKILL = ROOT / ".claude" / "skills" / "authoring-looks"
CRITIC = ROOT / ".claude" / "agents" / "look-critic.md"
RULE = ROOT / ".claude" / "rules" / "looks.md"
TOOLS = ROOT / "tests" / "goldens" / "mcp_tools.json"


def front(path: Path) -> dict[str, str]:
    """The `key: value` lines of a file's front matter."""
    head = path.read_text().split("---\n")[1]
    return dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)


def test_the_skill_has_its_name_a_description_and_stays_short() -> None:
    meta = front(SKILL / "SKILL.md")
    assert meta["name"] == SKILL.name and 0 < len(meta["description"]) <= 1024
    text = (SKILL / "SKILL.md").read_text()
    assert len(text.splitlines()) < 300
    for linked in re.findall(r"`(references/[\w.-]+)`", text):
        assert (SKILL / linked).is_file(), linked


def test_every_look_shape_the_skill_teaches_checks_and_renders_without_a_warning() -> None:
    blocks = re.findall(r"```json\n(.*?)```", (SKILL / "references" / "patterns.md").read_text(), re.DOTALL)
    assert len(blocks) >= 6
    for block in blocks:
        assert check_look(block).ok, block
        assert render(block, "grid:16x16", seconds=1.0, fps=30.0).warnings == (), block


def test_the_critic_only_renders_compares_checks_and_reads() -> None:
    served = {f"mcp__pewpew__{tool['name']}" for tool in json.loads(TOOLS.read_text())}
    tools = [name.strip() for name in front(CRITIC)["tools"].split(",")]
    assert tools == ["mcp__pewpew__look_render", "mcp__pewpew__look_compare", "mcp__pewpew__look_check", "Read"]
    assert set(tools) - {"Read"} <= served


def test_the_looks_rule_names_paths_that_exist() -> None:
    globs = re.findall(r'^  - "(.+)"$', RULE.read_text(), re.MULTILINE)
    assert globs == ["examples/**", "src/pewpew/compose/**"]
    assert all(any(ROOT.glob(pattern)) for pattern in globs)


def test_each_mcp_json_server_is_a_command_that_parses() -> None:
    servers = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
    tiers = {}
    for name, server in servers.items():
        args = server["args"]
        assert server["command"] == "uv" and args[:5] == ["run", "--extra", "agent", "python", "-m"]
        assert args[5] == "pewpew"
        tiers[name] = parse(args[6:]).tier
    assert tiers == {"pewpew": 0, "pewpew-live": 1}
