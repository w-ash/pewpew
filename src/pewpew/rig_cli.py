"""`python -m pewpew rig migrate-room`: turn a room map into an arrangement.

    python -m pewpew rig migrate-room ROOM.json -o OUT.json [--controller PROFILE] [--type FIXTURE_TYPE]

The verb reads ROOM.json and writes OUT.json only. It never writes in place
and never replaces a file. It compiles the result and, if the compile finds
an error or a cap violation (a room whose pixels per output do not fit the
controller, more fixtures than the arrangement allows), prints each issue to
stderr, writes nothing and exits 1. `--controller` and `--type` name catalog
entries; the defaults are the ESP32-S3 DevKitC-1 board of the room examples
and the parametric `strip`. See `pewpew.rig.room_import` for the mapping.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pewpew.jsonfile import parse_json, read_or_exit

if TYPE_CHECKING:
    from pewpew.rig.models import Issue

DEFAULT_CONTROLLER = "esp32s3-devkitc1-ahct125"
DEFAULT_TYPE = "strip"


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `rig` subcommand to the CLI."""
    rig = sub.add_parser("rig", help="work with rig files: migrate a room map to an arrangement")
    rig.set_defaults(cli=lambda args, argv: cli(args))
    actions = rig.add_subparsers(dest="action", required=True, metavar="COMMAND")
    p = actions.add_parser("migrate-room", help="write the arrangement a room map describes (writes only -o)")
    p.add_argument("room", type=Path, metavar="ROOM.json", help="the room map to read")
    p.add_argument("-o", "--output", type=Path, required=True, metavar="OUT.json",
                   help="the arrangement file to create; it must not exist")
    p.add_argument("--controller", default=DEFAULT_CONTROLLER, metavar="PROFILE",
                   help=f"the catalog controller every board becomes (default {DEFAULT_CONTROLLER})")
    p.add_argument("--type", dest="fixture_type", default=DEFAULT_TYPE, metavar="FIXTURE_TYPE",
                   help=f"the parametric catalog fixture type every strip becomes (default {DEFAULT_TYPE})")


def cli(args: argparse.Namespace) -> int:
    return migrate_room(args.room, args.output, controller=args.controller, fixture_type=args.fixture_type)


def migrate_room(room: Path, output: Path, *, controller: str, fixture_type: str) -> int:
    """Migrate the room file `room` to `output`; returns the exit status."""
    # Imported here: a `run` never loads the rig stack.
    from pewpew.rig import RigError, compile_rig, load_arrangement, load_catalog
    from pewpew.rig.room_import import room_to_arrangement
    from pewpew.room.map import RoomError

    if output.exists():
        raise SystemExit(f"{output}: already exists; give a new file with -o")
    doc = read_or_exit(room, "room map", lambda: parse_json(room.read_bytes(), RoomError))
    catalog = load_catalog()
    if not catalog.has(controller, "controller"):
        raise SystemExit(f"--controller: no controller {controller!r} in the catalog")
    if not catalog.has(fixture_type, "fixture_type"):
        raise SystemExit(f"--type: no fixture type {fixture_type!r} in the catalog")
    try:
        arrangement = room_to_arrangement(
            doc, controller_profile=catalog.get(controller, "controller"), fixture_type=fixture_type
        )
        rig = compile_rig(load_arrangement(arrangement), catalog)
    except RoomError as exc:
        raise SystemExit("\n  ".join([f"{room}:", *exc.problems])) from None
    except RigError as exc:
        return _refuse(output, [i for i in exc.issues if i.level != "warning"])
    bad = [i for i in rig.issues if i.level in ("error", "violation")]
    if bad:
        return _refuse(output, bad)
    with output.open("x", encoding="utf-8") as fh:
        fh.write(_text(arrangement) + "\n")
    print(f"{output}: {len(arrangement['fixtures'])} fixtures, {rig.n} pixels")
    return 0


def _refuse(output: Path, issues: list[Issue]) -> int:
    for issue in issues:
        print(f"{issue.level}: {issue.code}: {issue.message}", file=sys.stderr)
    print(f"{output}: not written; the migrated rig does not compile cleanly", file=sys.stderr)
    return 1


def _text(value: object, indent: int = 0, width: int = 100) -> str:
    """JSON text with 2-space indent, where a list or object that fits one line stays on it."""
    flat = json.dumps(value)
    if not isinstance(value, (dict, list)) or not value or indent + len(flat) <= width:
        return flat
    pad = " " * (indent + 2)
    if isinstance(value, dict):
        body = [f"{pad}{json.dumps(k)}: {_text(v, indent + 2, width)}" for k, v in value.items()]
        return "{\n" + ",\n".join(body) + "\n" + " " * indent + "}"
    body = [pad + _text(v, indent + 2, width) for v in value]
    return "[\n" + ",\n".join(body) + "\n" + " " * indent + "]"
