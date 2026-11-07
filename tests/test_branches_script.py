"""scripts/branches.py: the open-work report names a worktree outside the
repo root by its full path and still exits 0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "branches.py"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_a_worktree_outside_the_root_is_named_by_its_full_path(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    git("commit", "-q", "--allow-empty", "-m", "start", cwd=repo)
    outside = (tmp_path / "outside").resolve()
    git("worktree", "add", "-q", "--detach", str(outside), cwd=repo)

    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert f"- {outside}: detached HEAD" in result.stdout
