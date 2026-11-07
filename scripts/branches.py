#!/usr/bin/env python3
"""Report open work: unmerged branches, worktrees, uncommitted files, stashes,
and the project repos in projects/.

Run it before you start a feature, so you continue open work instead of
rebuilding it. Reads local git state only (no fetch). Always exits 0.

Usage: python3 scripts/branches.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAIN = "main"
MAX_FILES = 8


def git(*args: str, cwd: str | None = None) -> str:
    """Run git and return stdout without the final newline. Return "" on error."""
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def worktrees() -> list[dict[str, str]]:
    """Return one dict per worktree, from `git worktree list --porcelain`."""
    entries: list[dict[str, str]] = []
    for block in git("worktree", "list", "--porcelain").split("\n\n"):
        entry: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            entry[key] = value
        if "worktree" in entry:
            entries.append(entry)
    return entries


def dirty_files(path: str) -> list[str]:
    """Return the uncommitted paths in the worktree at path."""
    out = git("status", "--porcelain", cwd=path)
    return [line[3:] for line in out.splitlines()]


def summarize(paths: list[str]) -> str:
    """Return the first paths joined, with a count of the rest."""
    shown = ", ".join(paths[:MAX_FILES])
    rest = len(paths) - MAX_FILES
    return f"{shown}, +{rest} more" if rest > 0 else shown


def label(path: str, root: str) -> str:
    """Return path relative to root, or the full path when it is outside root."""
    if path == root:
        return "main checkout"
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return path


def project_findings(root: str) -> list[str]:
    """Return the open work in each project repo at projects/<project>/."""
    found: list[str] = []
    projects = Path(root, "projects")
    if not root or not projects.is_dir():
        return found
    for repo in sorted(p for p in projects.iterdir() if (p / ".git").exists()):
        path, name = str(repo), f"projects/{repo.name}"
        dirty = dirty_files(path)
        if dirty:
            found.append(f"- {name}: {len(dirty)} uncommitted\n    {summarize(dirty)}")
        if git("rev-parse", "--abbrev-ref", "@{upstream}", cwd=path):
            unpushed = git("rev-list", "--count", "@{upstream}..HEAD", cwd=path)
            if unpushed and unpushed != "0":
                found.append(f"- {name}: {unpushed} commits not pushed")
        else:
            found.append(f"- {name}: its branch has no upstream")
    return found


def main() -> int:
    """Print the report."""
    if not git("rev-parse", "--verify", "--quiet", MAIN):
        print(f"branches.py: no '{MAIN}' branch here", file=sys.stderr)
        return 0
    trees = worktrees()
    root = trees[0]["worktree"] if trees else ""
    tree_of = {
        t["branch"].removeprefix("refs/heads/"): t for t in trees if "branch" in t
    }
    findings: list[str] = []

    for branch in git("for-each-ref", "--format=%(refname:short)", "refs/heads").split():
        if branch == MAIN:
            continue
        ahead = int(git("rev-list", "--count", f"{MAIN}..{branch}") or 0)
        tree = tree_of.get(branch)
        where = f" in {label(tree['worktree'], root)}" if tree else ""
        if ahead == 0 and tree and dirty_files(tree["worktree"]):
            findings.append(f"- {branch}{where}: no commits yet, work in progress")
            continue
        if ahead == 0:
            findings.append(
                f"- {branch}{where}: merged into {MAIN}; remove its worktree and "
                f"run `git branch -d {branch}`"
            )
            continue
        upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
        if not upstream:
            pushed = "never pushed"
        else:
            unpushed = int(git("rev-list", "--count", f"{upstream}..{branch}") or 0)
            pushed = f"{unpushed} unpushed" if unpushed else f"pushed to {upstream}"
        date = git("log", "-1", "--format=%cs", branch)
        files = git("diff", "--name-only", f"{MAIN}...{branch}").splitlines()
        findings.append(
            f"- {branch}{where}: {ahead} commits not in {MAIN}, last {date}, "
            f"{pushed}\n    touches: {summarize(files)}"
        )

    for tree in trees:
        path = tree["worktree"]
        name = label(path, root)
        if "prunable" in tree:
            findings.append(f"- {name}: folder is gone; run `git worktree prune`")
            continue
        if path != root and "branch" not in tree:
            findings.append(f"- {name}: detached HEAD, no branch holds its commits")
        dirty = dirty_files(path)
        if dirty:
            findings.append(
                f"- {name}: {len(dirty)} uncommitted\n    {summarize(dirty)}"
            )

    findings.extend(project_findings(root))

    root_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root)
    if root and root_branch != MAIN:
        findings.append(f"- main checkout is on '{root_branch}', not {MAIN}")
    unpushed_main = git("rev-list", "--count", f"origin/{MAIN}..{MAIN}")
    if unpushed_main and unpushed_main != "0":
        findings.append(f"- {MAIN}: {unpushed_main} commits not pushed to origin")
    stashes = git("stash", "list").splitlines()
    if stashes:
        findings.append(f"- {len(stashes)} stash entries (`git stash list`)")

    if findings:
        print("Open work in this repo (check for overlap before you start):")
        print("\n".join(findings))
    else:
        print("No open branches, worktrees, uncommitted work, or stashes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
