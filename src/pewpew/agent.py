"""The `mcp` command: `python -m pewpew mcp --tier 0|1`, pewpew's tools for
an AI agent over MCP on stdio (pewpew.mcp_server; ADR-023).

The server needs the `agent` extra (`mcp`, which brings pydantic), so this
module imports it only when the command runs: `import pewpew` and every
other command load neither. Without the extra the command exits 2 and says
how to install it.

`--tier 0` (the default) serves the read-only tools; `--tier 1` adds the
writes to an engine on this machine, and `--allow-host IP` names a bench
machine they may write to as well (CLAUDE.md T-7, pewpew.remote.control).
"""

from __future__ import annotations

import argparse
import sys

from pewpew.command import OK, USAGE, add_allow_host

INSTALL = "the MCP server needs the agent extra: install pewpew[agent] (in this repo, `uv sync --extra agent`)"
# The packages the extra brings: a missing one is the extra missing, not a bug.
_EXTRA = {"mcp", "mcp_types", "pydantic", "pydantic_core"}


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `mcp` subcommand to the CLI."""
    p = sub.add_parser(
        "mcp", help="serve pewpew's tools to an AI agent over MCP on stdio (needs pewpew[agent])",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--tier", type=int, choices=(0, 1), default=0,
                   help="0: read-only tools (default); 1: also engine_apply and engine_set, which write to an "
                   "engine on this machine run with --accept-looks")
    add_allow_host(p, "also write to the engine at IP, a bench machine (default: only an engine on this machine)")
    p.set_defaults(cli=cli)


def conflict(args: argparse.Namespace) -> str | None:
    """Why the options rule each other out, or None."""
    return "--allow-host only applies with --tier 1" if args.allow_hosts and args.tier < 1 else None


def cli(args: argparse.Namespace, argv: list[str]) -> int:
    """Serve until the client closes stdin; exit 2 without the extra."""
    try:
        from pewpew import mcp_server  # here, so no other command loads the extra
    except ModuleNotFoundError as exc:
        if (exc.name or "").partition(".")[0] not in _EXTRA:
            raise
        print(f"mcp: {INSTALL}", file=sys.stderr)
        return USAGE
    mcp_server.serve(args.tier, allow_hosts=args.allow_hosts, argv=argv)
    return OK
