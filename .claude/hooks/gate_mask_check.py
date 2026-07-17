#!/usr/bin/env python3
"""PreToolUse(Bash) hook: block pipe-masked gates before commit/push.

`verify | tail -1 && git commit` takes the pipe consumer's exit status, so
a red gate ships anyway (it happened twice on 2026-07-16). If a command
chains git commit/push after a piped stage, block it and ask for the gate
to run unpiped first.
"""
import json
import re
import sys

try:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)  # malformed payload: never wedge the session

# a single `|` (not `||`) stage, then `&&`, then git commit/push
PATTERN = re.compile(r"(^|[^|])\|[^|&][^&]*&&.*git (commit|push)")

if PATTERN.search(command):
    sys.stderr.write(
        "Blocked: a pipe before `&& git commit/push` masks the gate's exit "
        "code (the pipe consumer's status wins). Run the gating check "
        "unpiped as its own command first, then commit/push separately.\n"
    )
    sys.exit(2)
sys.exit(0)
