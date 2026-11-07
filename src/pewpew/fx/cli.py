"""The `fx` command group: what a look can be made of, from the catalog.

    fx catalog [--kind K] [--query Q] [--json | --format markdown]
    fx show NAME [--json]

Tier 0 (CLAUDE.md T-7): each verb reads the package only and writes only
to stdout. `catalog` lists ops, blend modes, palettes and param
kinds (`--kind` narrows to one, or to the ops of one signature, such as
`coord`); `show` prints one op's (or blend's, palette's or
kind's) whole record, with its examples as builder chains and as JSON.
`--format markdown` prints the reference page, docs/reference/catalog.md.
With `--json` a verb prints one JSON document on stdout. Exit codes: 0
ok, 1 a name the catalog does not hold, 2 a usage error.

The lab's verbs (check, render, sheet, metrics, compare, explain, vary)
join the group too, through the verbs `add_parser` returns (`pewpew.lab.cli`).
Each verb registers its handler (`set_defaults(cli=...)`), called with
the parsed args and the command line.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from pewpew.errors import unknown
from pewpew.fx.catalog import KINDS, SECTIONS, catalog, entries, items, markdown, name_of

# What `fx --help` says: for a person, every verb; the module docstring is for a developer.
HELP = """\
What a look can be made of, and the lab that checks, renders, measures and
compares looks. Tier 0: nothing is sent to an engine or a board.

    fx catalog [--kind K] [--query Q]   ops, blends, palettes, param kinds
    fx show NAME                        one record whole, with its examples
    fx check FILE                       the problems of a look or looks file, or ok
    fx render FILE                      render a look: its handle, spec and metrics
    fx sheet HANDLE|FILE                a contact sheet PNG
    fx metrics HANDLE|FILE              the metrics; with --liveness, each knob's
    fx compare A B                      how B differs from A, each a handle or a file
    fx explain FILE                     a look in words
    fx vary [FILE]                      looks made from a seed, or like FILE

catalog and show read the package only. The others also write the render
cache and the --out file. FILE is a looks file, as run LOOKS reads it; -
reads a looks file or a single look, as JSON, from stdin. With --json a
verb prints one JSON document on stdout. Exit codes: 0 ok; 1 an unknown
name, problems with a look or nothing made; 2 a usage error; 3 a render
handle the cache no longer holds.
"""


def add_parser(sub: argparse._SubParsersAction) -> argparse._SubParsersAction:
    """Add the `fx` command to `sub`; returns its verbs, for others to join."""
    fx = sub.add_parser("fx", help="what a look can be made of; check, render, measure and compare looks (tier 0)",
                        description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = fx.add_subparsers(dest="verb", required=True, metavar="VERB")
    add_verbs(verbs)
    return verbs


def add_verbs(verbs: argparse._SubParsersAction) -> None:
    """Add `catalog` and `show` to the `fx` verbs."""
    p = verbs.add_parser("catalog", help="list the ops, blends, palettes and param kinds")
    p.add_argument("--kind", choices=KINDS, default=None,
                   help="only one section (op, blend, palette, kind) or the ops of one signature")
    p.add_argument("--query", default=None, metavar="TEXT", help="only what names or describes every word of TEXT")
    form = p.add_mutually_exclusive_group()
    form.add_argument("--json", action="store_true", help="print one JSON document: {items: [...]}")
    form.add_argument("--format", choices=("text", "markdown"), default="text",
                      help="text (one line each) or markdown (the reference page)")
    p.set_defaults(cli=catalog_cli)

    p = verbs.add_parser("show", help="print one op's whole record, with its examples")
    p.add_argument("name", metavar="NAME", help="an op (kaleid), or a blend, palette or kind")
    p.add_argument("--json", action="store_true", help="print the record as one JSON document")
    p.set_defaults(cli=show_cli)


def catalog_cli(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    book = catalog()
    found = entries(book, args.kind, args.query)
    records = [record for _, record in found]
    if args.json:
        print(json.dumps({"items": records}, indent=2))
    elif args.format == "markdown":
        print(markdown({section: [r for r in book[section] if r in records] for section in SECTIONS}), end="")
    else:
        for kind, record in found:
            print(f"{name_of(record):<14} {record.get('sig', kind):<9} {record.get('doc', '')}")
    return 0


def show_cli(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    book = catalog()
    everything = items(book)
    record = next((r for r in everything if name_of(r) == args.name), None)
    record = record or next((r for r in book["ops"] if r["label"].lower() == args.name.lower()), None)
    if record is None:
        ops = [name_of(r) for r in book["ops"]]
        print(unknown("op", args.name, ops, suggest=True, aliases={r["label"]: name_of(r) for r in book["ops"]}),
              file=sys.stderr)
        return 1
    print(json.dumps(record, indent=2) if args.json else "\n".join(_lines(record)))
    return 0


def _lines(record: dict[str, Any]) -> list[str]:
    """One record, for a reader: its name and doc, then each field."""
    lines = [f"{name_of(record)} — {record.get('label', name_of(record))}", f"  {record.get('doc', '')}"]
    for key, value in record.items():
        if key in ("op", "label", "doc", "name", "kind", "params", "examples"):
            continue
        lines.append(f"  {key}: {json.dumps(value)}")
    for param in record.get("params", []):
        lines.append(f"  param {param['name']} ({param['kind']}): default {json.dumps(param['default'])}"
                     + (f", {param['lo']}..{param['hi']} {param['unit']}".rstrip() if "lo" in param else "")
                     + (f" — {param['help']}" if param["help"] else ""))
    for example in record.get("examples", []):
        lines.append(f"  example: {example['py']}")
    return lines
