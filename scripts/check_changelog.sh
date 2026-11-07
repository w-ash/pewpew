#!/usr/bin/env bash
# Fail when the branch changes shipped code but not CHANGELOG.md.
#
# Usage: scripts/check_changelog.sh [base]   (default base: main)
# Compares the working tree with the merge base, so uncommitted edits count.
# A change with nothing to tell users (refactor, CI, docs) passes when a
# commit in the range has the trailer line `Changelog: none`.
set -euo pipefail

base="${1:-main}"
mb=$(git merge-base "$base" HEAD)

code=$(git diff --name-only "$mb" -- src deploy bench ':!bench/results')
if [ -z "$code" ]; then
  echo "ok: no shipped code changed since $base"
  exit 0
fi
if [ -n "$(git diff --name-only "$mb" -- CHANGELOG.md)" ]; then
  echo "ok: CHANGELOG.md updated"
  exit 0
fi
if git log --format=%B "$mb..HEAD" | grep -qx 'Changelog: none'; then
  echo "ok: a commit says 'Changelog: none'"
  exit 0
fi

echo "CHANGELOG FAIL: code changed since $base but CHANGELOG.md did not:"
echo "$code" | sed 's/^/  /'
echo "Add an entry under [Unreleased], or add the trailer 'Changelog: none'"
echo "to a commit message when users see no change."
exit 1
