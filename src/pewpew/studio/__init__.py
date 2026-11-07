"""The studio backend: one real renderer per visitor, streamed over a websocket.

`create_app` (`pewpew.studio.app`) is the FastAPI factory; run it with
`uvicorn --factory` or `python -m pewpew studio`, which calls `serve`.
Needs the `studio` extra. This module imports none of it, so the command
line loads without the extra.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pewpew.cli_args import port


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `studio` subcommand to the CLI."""
    p = sub.add_parser("studio", help="serve the 3D studio: one live renderer per visitor")
    p.add_argument("--host", default="127.0.0.1", metavar="ADDR", help="the address to listen on (default 127.0.0.1)")
    p.add_argument("--port", type=port, default=8000, metavar="PORT", help="the port to listen on (default 8000)")
    p.add_argument("--db", type=Path, default=None, metavar="PATH",
                   help="SQLite file for share links, ignored when DATABASE_URL is set "
                   "(default: PEWPEW_STUDIO_DB, else ./studio.sqlite3)")
    p.set_defaults(cli=lambda args, argv: serve(args.host, args.port, args.db))


def serve(host: str, port: int, db: Path | None = None) -> int:
    """Serve the studio app under uvicorn until it is stopped. Share links
    go to SQLite at `db`, else at `PEWPEW_STUDIO_DB`, unless `DATABASE_URL`
    is set. Exits with one line when the `studio` extra is missing."""
    try:
        import uvicorn

        from pewpew.studio.limits import MAX_BODY_BYTES
    except ImportError as exc:
        raise SystemExit(f"the studio needs the studio extra ({exc}): pip install 'pewpew[studio]'") from None
    if db is not None:
        os.environ["PEWPEW_STUDIO_DB"] = str(db)
    uvicorn.run(
        "pewpew.studio.app:create_app",
        factory=True,
        host=host,
        port=port,
        ws_max_size=MAX_BODY_BYTES,
        timeout_graceful_shutdown=30,
        access_log=False,
    )
    return 0
