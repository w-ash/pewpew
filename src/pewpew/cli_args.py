"""What the subcommands of `python -m pewpew` share: their exit codes, the
argument that reads stdin, and the argparse types of their options.

Each type returns the parsed value, or raises `ArgumentTypeError` with the
value expected and the text given, so a bad option is a usage error.
"""

from __future__ import annotations

import argparse
import ipaddress
import math
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

OK = 0
PROBLEMS = 1  # a look with problems, a failed gate, an observation without its metrics
USAGE = 2  # argparse's own code for a usage error
GONE = 3  # an engine that does not answer, or a render handle the cache no longer holds
REFUSED = 4  # a write that tier 1 rules out, or that the engine refused

STDIN = "-"  # a source argument that reads stdin


def number(text: str) -> float:
    """`text` as a float; NaN for text that is not a number."""
    try:
        return float(text)
    except ValueError:
        return math.nan


def parsed_by(parse: Callable[[str], T]) -> Callable[[str], T]:
    """argparse type: `parse(text)`, its ValueError a usage error with its
    message."""

    def checked(text: str) -> T:
        try:
            return parse(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None

    return checked


def whole(least: int, what: str, most: int | None = None) -> Callable[[str], int]:
    """argparse type: a whole number of at least `least` and at most `most`."""
    bound = "" if most is None else f" and at most {most}"

    def parse(text: str) -> int:
        try:
            if least <= (value := int(text)) and (most is None or value <= most):
                return value
        except ValueError:
            pass
        raise argparse.ArgumentTypeError(f"expected {what}, a whole number of at least {least}{bound}, got {text!r}")

    return parse


def positive(what: str, most: float = math.inf) -> Callable[[str], float]:
    """argparse type: a finite number above 0 and at most `most`."""
    bound = "" if most == math.inf else f" and at most {most:g}"

    def parse(text: str) -> float:
        value = number(text)
        if not (math.isfinite(value) and 0.0 < value <= most):
            raise argparse.ArgumentTypeError(f"expected {what} above 0{bound}, got {text!r}")
        return value

    return parse


def port(text: str) -> int:
    """argparse type for a `--port`: 0 to 65535."""
    if not text.isdigit() or int(text) > 65535:
        raise argparse.ArgumentTypeError(f"expected a port from 0 to 65535, got {text!r}")
    return int(text)


def web_url(text: str) -> str:
    """argparse type for a site's base URL (`run --gallery`): http or https
    with a host, returned with no trailing slash."""
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(text)
        good = parts.hostname is not None and parts.scheme in ("http", "https") and not (parts.query or parts.fragment)
    except ValueError:  # a malformed port or IPv6 address
        good = False
    if not good:
        raise argparse.ArgumentTypeError(f"expected an http or https URL with a host, such as https://example.org, "
                                         f"got {text!r}")
    return text.rstrip("/")


def png_path(text: str) -> Path:
    """argparse type for a PNG to write (`observe --sheet`, `fx --out`): a
    path in a folder that exists, and not a folder itself."""
    path = Path(text)
    if not path.parent.is_dir():
        raise argparse.ArgumentTypeError(f"no folder {str(path.parent)!r} to write the sheet in")
    if path.is_dir():
        raise argparse.ArgumentTypeError(f"{text!r} is a folder: give the sheet a file name, such as "
                                         f"{str(path / 'sheet.png')!r}")
    return path


def add_allow_host(parser: argparse._ActionsContainer, help: str) -> None:
    """Add `--allow-host IP` to `parser`, as `allow_hosts`: one IP address
    per use, never a name, so what it allows cannot move with DNS. Tier 1
    reaches past this machine only to what it names (CLAUDE.md T-7)."""
    parser.add_argument("--allow-host", dest="allow_hosts", type=parsed_by(ip_address), action="append", default=[],
                        metavar="IP", help=help)


def ip_address(text: str) -> str:
    """`text` as an IP address in its normal form; ValueError for anything else."""
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        raise ValueError(f"expected an IP address, such as 192.168.1.20, got {text!r}") from None
