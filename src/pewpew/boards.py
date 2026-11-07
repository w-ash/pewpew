"""Find the WLED boards on the network, and back up and restore each
board's config: `python -m pewpew boards`.

    python -m pewpew boards scan [--subnet 192.168.8.0/24] [--json]
    python -m pewpew boards backup DIR --room ROOM.json
    python -m pewpew boards restore DIR --room ROOM.json --dry-run
    python -m pewpew boards restore DIR --board 10.0.0.11 --board 10.0.0.12

The boards come from `--room` (its `boards`) or from `--board`, given as
HOST[:PORT] or as `run --ddp`'s HOST[:PORT]=START+COUNT; only the host is
used.
Files go to DIR/<host>/cfg.json and DIR/<host>/presets.json.

Backup is tier 0 (read-only): `GET /cfg.json` and `GET /presets.json`,
the files WLED's own Backup links fetch (WLED v16.0.1
`wled00/data/settings_sec.htm:76-79`). A file that is already in DIR is
never overwritten: a board that has just reset its config would otherwise
replace the good backup with the reset one. Use a new DIR each time.
Passwords are not in the backup: WLED keeps them in `/wsec.json`
(`wled00/cfg.cpp:1269-1271`), and its file server refuses any path containing
"sec" (`wled00/file.cpp:427`). A restored `cfg.json` without them keeps
the board's current passwords (`cfg.cpp:99-107`).

Restore is tier 1 (it writes to the boards, CLAUDE.md T-7): `--dry-run`
prints each file and board and sends nothing, and a real restore appends
an audit record before the first write. Every file is read and checked as
a JSON object before anything is sent. Each file is a multipart POST to
`/upload` with the file name "/presets.json" or "/cfg.json", as WLED's
settings page sends it (`wled00/data/common.js:156-162`). WLED's
`handleUpload` (`wled00/wled_server.cpp:196-226`, routed at `:489-492`)
writes the file under that name; for `cfg.json` it then reboots the
board (`:216-218`). Presets go first, so the reboot loads both. A board
with a settings PIN refuses the upload with 401 (`:197-199`). The first
failure stops the restore.

Scan is tier 0: it asks every address of this laptop's /24 (or
`--subnet`) for `/json/info` and prints each WLED board that answers, with
its address, name, MAC and whether it is live (`pewpew.wled.sweep`), and
then each pewpew capture node, which is no board (`pewpew.audio.net`).
`survey` gives the same boards as a `Fleet`, each with its health: the
fields of its reply that `pewpew.health` reads, and the level, reasons and
fix of one look at them. `--json` prints it, and the MCP tool
`fleet_status` returns it.

Backups also flag WLED's "skip out-of-sequence" option
(`if.live.dmx.seqskip`, `cfg.cpp:600`), which must stay off
(`pewpew.sinks.ddp`).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TextIO

from pewpew import audit, wled
from pewpew.audio.net import NodeInfo, node_lines
from pewpew.cli_args import parsed_by
from pewpew.health import BoardHealth, extract
from pewpew.jsonfile import loads, read_or_exit
from pewpew.result import Result
from pewpew.room.map import load_room
from pewpew.sinks.ddp import parse_board, parse_target

FILES = ("presets.json", "cfg.json")  # restore order: cfg.json reboots the board
TIMEOUT_S = 10.0


class Http(Protocol):
    """The HTTP the command uses; tests pass a fake."""

    def get(self, url: str, timeout: float) -> bytes: ...

    def upload(self, url: str, filename: str, data: bytes, timeout: float) -> tuple[int, str]: ...


class UrllibHttp:
    """`Http` over urllib."""

    def get(self, url: str, timeout: float) -> bytes:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()

    def upload(self, url: str, filename: str, data: bytes, timeout: float) -> tuple[int, str]:
        boundary = uuid.uuid4().hex
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="data"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: application/json\r\n\r\n",
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read().decode("utf-8", "replace")


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add `boards scan`, `boards backup` and `boards restore` to the command's subparsers."""
    boards = sub.add_parser("boards", help="find the WLED boards on the network; back up or restore their config")
    boards.set_defaults(cli=lambda args, argv: cli(args, argv=argv))
    actions = boards.add_subparsers(dest="action", required=True, metavar="COMMAND")
    scan = actions.add_parser("scan", help="list the WLED boards on this laptop's network (read-only)")
    scan.add_argument("--subnet", type=parsed_by(parse_subnet), default=None, metavar="CIDR",
                      help="the network to scan, such as 192.168.8.0/24 (default: this laptop's /24)")
    scan.add_argument("--json", action="store_true",
                      help="print the boards and their health as one JSON document on stdout")
    for name, text in (
        ("backup", "download each board's cfg.json and presets.json into DIR/<host>/ (read-only)"),
        ("restore", "upload DIR/<host>/ files to each board; cfg.json reboots it (writes: --dry-run first)"),
    ):
        p = actions.add_parser(name, help=text)
        p.add_argument("dir", type=Path, metavar="DIR", help="the backup folder, one DIR/<host>/ per board")
        given = p.add_mutually_exclusive_group(required=True)
        given.add_argument("--room", type=Path, default=None, metavar="PATH", help="take the boards from a room map")
        given.add_argument("--board", action="append", default=[], metavar="BOARD",
                           help="a board, as HOST[:PORT] or HOST[:PORT]=START+COUNT; repeat once per board")
        if name == "restore":
            p.add_argument("--dry-run", action="store_true", help="print what would be written and send nothing")


def hosts_of(args: argparse.Namespace) -> list[str]:
    """The board hosts from `--room` or `--board`, in order, each once."""
    if args.room is not None:
        room, _ = read_or_exit(args.room, "room map", lambda: load_room(args.room))
        hosts = [b.host for b in room.boards]
    else:
        hosts = []
        for spec in args.board:
            try:
                hosts.append(parse_board(spec).host if "=" in spec else parse_target(spec)[0])
            except ValueError as exc:
                raise SystemExit(f"--board: {exc}") from None
    if not hosts:
        raise SystemExit("the room map names no boards")
    return list(dict.fromkeys(hosts))


def _json_object(data: bytes) -> dict | None:
    try:
        value = loads(data)
    except (ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def seqskip(cfg: dict) -> bool:
    """Whether a cfg.json turns on WLED's DDP "skip out-of-sequence"."""
    try:
        return bool(cfg["if"]["live"]["dmx"]["seqskip"])
    except (KeyError, TypeError):
        return False


def backup(directory: Path, hosts: list[str], http: Http, out: TextIO | None = None) -> int:
    """Download every board's files into `directory`; 0 if all arrived."""
    out = out or sys.stdout
    failed = 0
    for host in hosts:
        folder = directory / host
        for name in FILES:
            path = folder / name
            if path.exists():
                print(f"{host}: {path} exists; not overwritten (use a new DIR)", file=out)
                failed += 1
                continue
            try:
                data = http.get(f"http://{host}/{name}", TIMEOUT_S)
            except OSError as exc:
                print(f"{host}: cannot read /{name}: {exc}", file=out)
                failed += 1
                continue
            parsed = _json_object(data)
            if parsed is None:
                print(f"{host}: /{name} is not a JSON object; not saved", file=out)
                failed += 1
                continue
            folder.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print(f"{host}: saved {path} ({len(data):,} B)", file=out)
            if name == "cfg.json" and seqskip(parsed):
                print(f"{host}: note: 'skip out-of-sequence' is on; turn it off "
                      "(pewpew's DDP sequence restarts with pewpew)", file=out)
    return 1 if failed else 0


def restore(
    directory: Path, hosts: list[str], http: Http, *, dry_run: bool, argv: list[str], out: TextIO | None = None
) -> int:
    """Upload every board's files from `directory`. Checks every file
    first; audits before the first write; stops at the first failure."""
    out = out or sys.stdout
    plan: list[tuple[str, str, bytes]] = []
    problems = []
    for host in hosts:
        found = False
        for name in FILES:
            path = directory / host / name
            if not path.is_file():
                continue
            found = True
            data = path.read_bytes()
            if _json_object(data) is None:
                problems.append(f"{path} is not a JSON object")
            plan.append((host, name, data))
        if not found:
            problems.append(f"no backup for {host} in {directory / host}")
    if problems:
        raise SystemExit("nothing restored: " + "; ".join(problems))
    for host, name, data in plan:
        reboot = " (the board reboots)" if name == "cfg.json" else ""
        verb = "would upload" if dry_run else "uploading"
        print(f"{verb} {directory / host / name} ({len(data):,} B) to http://{host}/upload as /{name}{reboot}",
              file=out)
    if dry_run:
        print("dry run: nothing sent", file=out)
        return 0
    try:
        log = audit.record(
            "boards-restore", argv=argv, targets=hosts,
            files=[f"{h}/{n}" for h, n, _ in plan],
        )
    except OSError as exc:
        raise SystemExit(f"cannot write the audit log, nothing restored: {exc}") from None
    print(f"audit record appended to {log}", file=out)
    for host, name, data in plan:
        try:
            status, body = http.upload(f"http://{host}/upload", f"/{name}", data, TIMEOUT_S)
        except OSError as exc:
            print(f"{host}: upload of /{name} failed: {exc}; stopping", file=out)
            return 1
        if status != 200:
            print(f"{host}: upload of /{name} refused ({status}): {body.strip()}; stopping", file=out)
            return 1
        print(f"{host}: /{name} restored: {body.strip()}", file=out)
    return 0


def parse_subnet(value: str) -> ipaddress.IPv4Network:
    """The IPv4 network `value` names, a /22 or smaller. Raises ValueError,
    saying why."""
    try:
        net = ipaddress.IPv4Network(value, strict=False)
    except ValueError:
        raise ValueError(f"bad subnet {value!r}; expected CIDR such as 192.168.8.0/24") from None
    if net.num_addresses > 1024:
        raise ValueError(f"subnet {value!r} is too large; scan a /22 or smaller")
    return net


@dataclass(frozen=True)
class Fleet(Result):
    """What `survey` found: the subnet it asked, and each WLED board that
    answered, by address. A board is `wled.sweep`'s row for it, the health
    fields of its reply (`pewpew.health.extract`), and the `level`,
    `reasons` and `fix` of one look at them. Frozen but not slotted, so an
    MCP tool can return it as structured content (pewpew.result)."""

    subnet: str
    boards: tuple[dict[str, Any], ...] = ()


def survey(
    subnet: ipaddress.IPv4Network | None = None, *, fetch: Callable[[str, float], dict] | None = None,
) -> Fleet:
    """Every WLED board in `subnet`, by default this laptop's /24, and its
    health (`Fleet`). Reads only. `fetch` defaults to `wled.fetch_info`.
    Raises ValueError when there is no subnet to scan."""
    target = wled.scan_subnet(subnet)
    if target is None:
        raise ValueError("this laptop has no IPv4 address; give a subnet to scan, such as 192.168.8.0/24")
    return _survey(*target, fetch)[0]


def _survey(
    subnet: ipaddress.IPv4Network, mine: str | None, fetch: Callable[[str, float], dict] | None,
) -> tuple[Fleet, list[NodeInfo]]:
    """The boards in `subnet` (`survey`), and the capture nodes that answered."""
    boards, nodes = [], []
    for address, info in wled.replies(subnet, mine, fetch or wled.fetch_info):
        if wled.is_node(info):
            if (node := NodeInfo.of(address, info)) is not None:
                nodes.append(node)
            continue
        row = wled.board_row(address, info)
        sample = extract(info)
        # No room says how many pixels go to it, so the count it has is taken as right.
        health = BoardHealth(address, expected=sample["count"] or 0, name=row["name"], address=address)
        health.record(info, 0.0, None)
        health.assess(0.0, None, None)
        boards.append({**row, **sample, "level": health.level, "reasons": health.reasons, "fix": health.fix})
    return Fleet(str(subnet), tuple(boards)), nodes


def scan(subnet: ipaddress.IPv4Network | None, *, as_json: bool = False) -> int:
    """Print every WLED board in `subnet`, by default this laptop's /24,
    then the capture nodes; with `as_json`, the `Fleet` as one JSON
    document (`audio list --json` lists the nodes)."""
    target = wled.scan_subnet(subnet)
    if target is None:
        raise SystemExit("this laptop has no IPv4 address; give --subnet")
    subnet, mine = target
    print(f"scanning {subnet} for WLED boards…", file=sys.stderr, flush=True)
    fleet, nodes = _survey(subnet, mine, None)
    if as_json:
        print(json.dumps(fleet.to_json(), indent=2))
    elif lines := [*wled.scan_lines(fleet.boards), *node_lines(nodes)]:
        print(*lines, sep="\n")
    if not fleet.boards:
        print(f"no WLED board answered in {subnet}", file=sys.stderr)
        return 1
    return 0


def cli(args: argparse.Namespace, *, argv: list[str], http: Http | None = None) -> int:
    if args.action == "scan":
        return scan(args.subnet, as_json=args.json)
    hosts = hosts_of(args)
    http = http or UrllibHttp()
    if args.action == "backup":
        return backup(args.dir, hosts, http)
    return restore(args.dir, hosts, http, dry_run=args.dry_run, argv=argv)


__all__ = [
    "FILES", "Fleet", "Http", "UrllibHttp", "add_parser", "backup", "cli", "parse_subnet", "restore", "scan",
    "seqskip", "survey",
]
