"""Change a running engine (tier 1): `python -m pewpew push URL LOOK`.

`push` sends a whole look, then any knob values, and `set_value` one knob
value. Each goes to the engine's preview port as the page's messages do,
with an `id`, and waits for the engine's `ack` or `refused` with that `id`
(ADR-020 amendment "capabilities"). Tier 1 (CLAUDE.md T-7, ADR-018
amendment 2026-11-05) holds in this code, not in a tool's description:

- The engine is on this machine: every address its host resolves to is
  loopback (127.0.0.0/8 or ::1), unless `allow_hosts` names it. Those are
  IP addresses, so what they allow cannot move with DNS. The client
  connects to an address it checked and never resolves again.
- A look is checked here first, as the engine checks it
  (`pewpew.lab.check_look`), and each knob value set after it against the
  look's knobs; a set alone is checked for a knob address's form. A dry
  run stops after the checks with the messages it would send, and opens
  no socket, so what only the engine knows (its map, `--accept-looks`,
  the knobs of the look it runs) is checked on a send alone. The look goes out as its document
  gives it, so the engine fills in its own defaults.
- An audit record (`pewpew.audit.record`) is written before the first byte
  goes out; a write that cannot be recorded is not sent.
- The engine's hello lists `look`, which only `run --accept-looks` gives
  and `--unattended` refuses. A set needs it too.

`Pushed` is frozen and not slotted, so an MCP tool can return it as
structured content (pewpew.result): the tier-1 MCP tools are thin adapters
over `push` and `set_value`.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, NoReturn

from websockets.uri import parse_uri

from pewpew import audit
from pewpew.cli_args import GONE, OK, PROBLEMS, REFUSED, STDIN, add_allow_host, number, parsed_by
from pewpew.compose import look_controls
from pewpew.compose.controls import address_problem
from pewpew.compose.stack import MAX_FADE, parse_fade
from pewpew.errors import describe_exception
from pewpew.fx.codec import encode_look
from pewpew.lab.check import Check, LookDoc, ready
from pewpew.pace import ASK_TIMEOUT_S
from pewpew.problems import Code, Problem, Refused, problem
from pewpew.remote.client import Client, Unreachable, engine_url, why_unreachable, with_host
from pewpew.result import Result

# How long to wait for the hello, and then for each answer: longer than
# the engine waits for its own loop, so a slow loop's answer still comes.
TIMEOUT_S = 2 * ASK_TIMEOUT_S
LOOK = "look"  # the capability a tier-1 write needs (ADR-018 amendment)
LACKS_LOOK = "engine lacks look; run it with --accept-looks or a newer pewpew"


class Forbidden(Exception):
    """A write that tier 1 rules out, or that the engine cannot take. The
    message says why and what to do instead."""


@dataclass(frozen=True, slots=True)
class Answer(Result):
    """The engine's answer to one message: an `ack`, or a refusal with its
    reason and the address of what it refused (None when no one part is
    to blame)."""

    id: str
    control: str
    ok: bool
    reason: str | None = None
    name: str | None = None

    @classmethod
    def of(cls, message: Mapping[str, Any]) -> Answer:
        """The answer in an `ack` or `refused` message."""
        if message["type"] == "ack":
            return cls(str(message["id"]), str(message.get("control")), True)
        return cls(str(message["id"]), str(message.get("control")), False, message.get("reason"), message.get("name"))


@dataclass(frozen=True)
class Pushed(Result):
    """What a write did (the module docstring). `messages` are in send
    order; a dry run's are what it would send, with no answers. The
    answers are in send order too, and a refusal is the last: nothing is
    sent after one. `ok` is true for a dry run that passed its checks, or
    when every message was acked."""

    url: str  # the engine, as `engine_url` writes it
    dry_run: bool
    ok: bool
    addresses: tuple[str, ...]  # every address the engine's host resolves to, each checked
    messages: tuple[dict[str, Any], ...]
    answers: tuple[Answer, ...] = ()
    connected: str | None = None  # the checked address the write went to
    audit: str | None = None  # the audit log the record went to


def push(
    url: str,
    look: LookDoc,
    *,
    fade: float | None = None,
    sets: Mapping[str, Any] | None = None,
    name: str | None = None,
    dry_run: bool = False,
    allow_hosts: Collection[str] = (),
    argv: Sequence[str] = (),
    timeout: float = TIMEOUT_S,
) -> Pushed:
    """Send `look` to the engine at `url` with `fade` (None: the look's
    own, which the message then names), then set each knob of `sets`, by
    address, to its value.

    `look` is a single look or a looks file, as `pewpew.lab.check_look`
    takes it; `name` picks a look of a file. The engine checks the look
    again.
    `argv` is the command line the audit record names. Raises Refused for
    problems with the look, `fade` or a set, Forbidden for a write tier 1
    rules out or the engine cannot take, Unreachable when the engine does
    not answer, and ValueError for an address that does not parse.
    """
    if fade is not None:
        fade, reason = parse_fade(fade)
        if reason is not None:
            raise Refused([problem(reason)])
    sets = dict(sets or {})
    staged = ready(look, name=name)
    knobs = look_controls(staged.look)
    problems = [replace(problem(reason), path=path) for path, value in sets.items()
                if (reason := knobs.parse(path, value)[1]) is not None]
    if problems:
        raise Refused(problems)
    # The fade the engine runs, said outright: the look's own when none is given.
    shown = staged.look.fade if fade is None else fade
    messages = [{"type": "look", "look": encode_look(staged.authored), "fade": shown}]
    messages += [{"type": "set", "name": path, "value": value} for path, value in sets.items()]
    return _write(url, messages, dry_run=dry_run, allow_hosts=allow_hosts, argv=argv, timeout=timeout)


def set_value(
    url: str,
    path: str,
    value: Any,
    *,
    dry_run: bool = False,
    allow_hosts: Collection[str] = (),
    argv: Sequence[str] = (),
    timeout: float = TIMEOUT_S,
) -> Pushed:
    """Set the knob at address `path` (`layers.base.osc.freq`) of the
    engine at `url` to `value`, a JSON value. `path` is checked here for a
    knob address's form; the engine checks that its look has the knob and
    that the knob takes the value. Raises as `push` does, but for the look."""
    if (reason := address_problem(path)) is not None:
        raise Refused([Problem(path, Code.BAD_REF, reason)])
    message = {"type": "set", "name": path, "value": value}
    return _write(url, [message], dry_run=dry_run, allow_hosts=allow_hosts, argv=argv, timeout=timeout)


def writable(url: str, allow_hosts: Collection[str] = ()) -> tuple[str, ...]:
    """Every address the host of `url` resolves to, once each, when tier 1
    may write to each: loopback, or one of `allow_hosts`. Raises Forbidden
    when one is neither, Unreachable when the host does not resolve, and
    ValueError for an address that does not parse."""
    url = engine_url(url)
    uri = parse_uri(url)
    allowed = {ipaddress.ip_address(host) for host in allow_hosts}
    try:
        found = socket.getaddrinfo(uri.host, uri.port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise Unreachable(why_unreachable(url, exc, 0.0)) from exc
    addresses = tuple(dict.fromkeys(str(info[4][0]) for info in found))
    fleet = [a for a in addresses if not ((ip := ipaddress.ip_address(a)).is_loopback or ip in allowed)]
    if fleet:
        where = uri.host if fleet == [uri.host] else f"{uri.host} resolves to {', '.join(fleet)}, which"
        raise Forbidden(
            f"{where} is not this machine: tier 1 writes only to an engine on this machine (127.0.0.1 or ::1). "
            f"Name a bench machine with --allow-host {fleet[0]}; a deployed engine is read-only, so watch it with "
            "`python -m pewpew observe`"
        )
    return addresses


def _write(
    url: str, messages: list[dict[str, Any]], *, dry_run: bool, allow_hosts: Collection[str], argv: Sequence[str],
    timeout: float,
) -> Pushed:
    """Number `messages`, check the engine's address, and unless `dry_run`
    record and send them, each after the last one's answer."""
    url = engine_url(url)
    planned = tuple({**message, "id": str(i)} for i, message in enumerate(messages, 1))
    addresses = writable(url, allow_hosts)
    if dry_run:
        return Pushed(url, True, True, addresses, planned)
    try:
        log = audit.record("push", argv=list(argv), url=url, addresses=list(addresses), messages=list(planned))
    except OSError as exc:
        raise Forbidden(f"cannot write the audit record ({describe_exception(exc)}), so nothing was sent: "
                        f"tier 1 sends only what it recorded; point {audit.ENV_VAR} at a file it can write") from exc
    replies: dict[str, Answer] = {}

    def keep(message: dict[str, Any]) -> None:
        if message["type"] in ("ack", "refused") and message.get("id") is not None:
            replies[str(message["id"])] = Answer.of(message)

    answers: list[Answer] = []
    with _connect(url, addresses, keep) as client:
        if LOOK not in (client.hello(timeout).get("capabilities") or ()):
            raise Forbidden(f"{client.url}: {LACKS_LOOK}")
        for message in planned:
            mid = message["id"]
            client.send(message)
            if not client.wait(lambda mid=mid: mid in replies, timeout):
                why = "closed the connection" if client.ended else f"did not answer within {timeout:g} s"
                raise Unreachable(f"{client.url} took the {message['type']} but {why}: "
                                  "observe the engine to see whether it ran")
            answers.append(replies[mid])
            if not answers[-1].ok:
                break
    ok = all(answer.ok for answer in answers)  # a refusal ends the answers
    return Pushed(url, False, ok, addresses, planned, tuple(answers), client.url, str(log))


def _connect(url: str, addresses: Sequence[str], keep: Callable[[dict[str, Any]], None]) -> Client:
    """A client of the engine at the first of `addresses` that answers,
    each in the place of `url`'s host."""
    failure: Unreachable | None = None
    for address in addresses:
        try:
            return Client(with_host(url, address), on_text=keep)
        except Unreachable as exc:
            failure = exc
    assert failure is not None  # `writable` returns at least one address
    raise failure


# ---- the command line ----------------------------------------------------------


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Add the `push` subcommand to the CLI."""
    p = sub.add_parser(
        "push", help="send a look to an engine on this machine started with --accept-looks (tier 1)",
        description="Exit codes: 0 sent and acked, or a dry run that passed; 1 problems with the look or a "
        "--set; 2 usage; 3 the engine did not answer; 4 refused by tier 1 or by the engine.",
    )
    p.add_argument("url", type=parsed_by(engine_url), metavar="URL",
                   help="the engine's preview address, as its `preview at` line prints it, or ws://HOST:PORT/")
    p.add_argument("source", metavar="LOOK",
                   help="a looks file (.look.json); - reads a looks file or a single look, as JSON, from stdin")
    p.add_argument("--look", dest="name", default=None, metavar="NAME",
                   help="the look of a looks file to send (default: its only look, else its 'current' one)")
    p.add_argument("--fade", type=_fade, default=None, metavar="S",
                   help="fade over S seconds (default: the look's own fade)")
    p.add_argument("--set", dest="sets", type=_assignment, action="append", default=[], metavar="PATH=VALUE",
                   help="then set the knob at PATH (layers.base.osc.freq) to VALUE, JSON or a choice key; "
                   "repeat per knob")
    add_allow_host(p, "also write to the engine at IP, a bench machine (default: only an engine on this machine)")
    p.add_argument("--dry-run", action="store_true",
                   help="check the look against this machine's catalog and that the engine is on this machine, "
                   "print what would be sent, and open no socket; the engine's map and --accept-looks are checked "
                   "only on a send")
    p.add_argument("--json", action="store_true",
                   help="print the result as one JSON document on stdout; diagnostics go to stderr")
    p.set_defaults(cli=cli)


def cli(args: argparse.Namespace, argv: list[str]) -> int:
    """Run `push`; the exit codes are in its `--help`."""
    doc: LookDoc = sys.stdin.read() if args.source == STDIN else Path(args.source)
    try:
        pushed = push(
            args.url, doc, fade=args.fade, sets=dict(args.sets), name=args.name, dry_run=args.dry_run,
            allow_hosts=args.allow_hosts, argv=argv,
        )
    except Refused as exc:
        if args.json:
            print(json.dumps(Check(False, None, exc.problems).to_json(), indent=2))
        for found in exc.problems:
            print(f"push: {found} [{found.code}]", file=sys.stderr)
        return PROBLEMS
    except Unreachable as exc:
        print(f"push: {exc}", file=sys.stderr)
        return GONE
    except Forbidden as exc:
        print(f"push: {exc}", file=sys.stderr)
        return REFUSED
    print(json.dumps(pushed.to_json(), indent=2) if args.json else report(pushed))
    return OK if pushed.ok else REFUSED


def report(pushed: Pushed) -> str:
    """The result as lines of text, for a person."""
    where = pushed.connected or f"{pushed.url} ({', '.join(pushed.addresses)})"
    lines = [f"dry run, nothing sent to {where}:" if pushed.dry_run else f"{where}:"]
    answers = {answer.id: answer for answer in pushed.answers}
    for message in pushed.messages:
        answer = answers.get(message["id"])
        if pushed.dry_run:
            outcome = "would send"
        elif answer is None:
            outcome = "not sent"
        elif answer.ok:
            outcome = "acked"
        else:
            outcome = f"refused{f' at {answer.name}' if answer.name else ''}: {answer.reason}"
        lines.append(f"  {_summary(message)}: {outcome}")
    if pushed.audit is not None:
        lines.append(f"audit record appended to {pushed.audit}")
    return "\n".join(lines)


def _summary(message: Mapping[str, Any]) -> str:
    """One message in a few words."""
    if message["type"] == "look":
        layers = len(message["look"]["layers"])
        return f"look of {layers} layer{'s' if layers != 1 else ''}, fading {message['fade']:g} s"
    return f"set {message['name']} to {json.dumps(message['value'])}"


def _fade(text: str) -> float:
    """argparse type for `--fade`: seconds, 0 to cut."""
    seconds, _ = parse_fade(number(text))
    if seconds is None:
        raise argparse.ArgumentTypeError(f"expected seconds from 0 to {MAX_FADE:g}, got {text!r}")
    return seconds


def _assignment(text: str) -> tuple[str, Any]:
    """argparse type for `--set PATH=VALUE`: VALUE as JSON when it parses,
    else the text (a choice key). NaN and Infinity are not JSON, so they
    stay text."""
    path, sep, value = text.partition("=")
    if not sep or not path:
        raise argparse.ArgumentTypeError(f"expected PATH=VALUE, such as layers.base.osc.freq=6; got {text!r}")
    try:
        return path, json.loads(value, parse_constant=_not_json)
    except ValueError:
        return path, value


def _not_json(name: str) -> NoReturn:
    """`json.loads`'s hook for NaN, Infinity and -Infinity: refuse them."""
    raise ValueError(f"{name} is not JSON")
