"""Error text that may cross the preview socket: never a path.

`describe_exception` is the one formatter for an exception whose text a
status line, a reload error or a refusal carries, and `scrub` the one
filter it applies: every absolute path goes, and the home dir with it.
`unknown` is the one wording for a name nothing answers to, and
`typo_hint` its did-you-mean. `Refusal` is a refused request as the
socket answers it. `blame` marks an exception with the address of the part
that raised it (a node of an effect program), and `blamed` reads it back.
Imports nothing from pewpew, so every layer can use them.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

# A path part: no slash, quote, bracket, separator or line break. A space
# may be in a part, so a path runs to the next of those or to the end.
_PART = r"[^/'\"(),:;\n]+"
# An absolute path of two or more parts, or one under `~`. The lookbehind
# keeps a ratio ("40/60"), a subnet ("/24") and a URL's path ("//host/x").
_PATH = rf"(?<![\w.:/~-])(?:~|/{_PART})(?:/{_PART})+/?"
# How alike two names must be (difflib's ratio) for one to be a typo of the
# other: `sped` and `speed` are, `palette` and `master` are not.
_TYPO = 0.75
_WRAPPED = re.compile(rf" ?\({_PATH}\)")
_BARE = re.compile(_PATH)


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why a request was refused, and the address of what it refused: a
    knob (`layers.base.waves.freq`), or a part of a look sent whole
    (`layers.base.waves.op`, `master`); None when no one part is to
    blame. Both cross the preview socket, so neither names a path."""

    reason: str
    name: str | None = None


class Worded(ValueError):
    """A refusal whose message is the whole account, in its own words:
    `describe_exception` gives it without its type, and a log needs no
    traceback for it."""


def scrub(text: str) -> str:
    """`text` with no absolute path and no home dir: a path in brackets
    goes with its brackets (CPython's `ImportError` adds one), any other
    becomes "…", taking the words after it up to the next separator, and
    the home dir alone becomes "~"."""
    home = str(Path.home())
    if len(home) > 1:
        text = text.replace(home, "~")
    return _BARE.sub("…", _WRAPPED.sub("", text))


def describe_exception(exc: BaseException) -> str:
    """`Type: message` for `exc`, scrubbed: a SyntaxError gives its message
    and line, an OSError its `strerror` alone (or only its type). Notes the
    exception carries (`add_note`, such as the node of an effect program
    that raised) follow in brackets.

    A `Worded` refusal is already in that form, so it passes through
    unprefixed.
    """
    if isinstance(exc, Worded):
        text = str(exc)
    elif isinstance(exc, SyntaxError):
        where = f" (line {exc.lineno})" if exc.lineno is not None else ""
        text = f"SyntaxError: {exc.msg}{where}"
    elif isinstance(exc, OSError):
        text = f"{type(exc).__name__}: {exc.strerror}" if exc.strerror else type(exc).__name__
    else:
        text = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    notes = getattr(exc, "__notes__", None)
    if notes:
        text = f"{text} ({'; '.join(str(note) for note in notes)})"
    return scrub(text)


def unknown(
    noun: str, name: object, known: Iterable[str], *, suggest: bool = False, aliases: Mapping[str, str] | None = None,
) -> str:
    """`unknown look 'x'; looks: a, b`: the refusal for a name that is not
    one of `known`, which it lists. With `suggest`, the closest of `known`
    follows the name: `unknown op 'kaleidd' (did you mean 'kaleid'?); ops:
    ...`, found through `aliases` too (`did_you_mean`)."""
    known = list(known)
    hint = typo_hint(name, known, aliases) if suggest else ""
    plural = f"{noun}es" if noun.endswith("s") else f"{noun}s"
    return f"unknown {noun} {name!r}{hint}; {plural}: {', '.join(known) or '(none)'}"


def did_you_mean(name: object, known: Iterable[str], aliases: Mapping[str, str] | None = None) -> str | None:
    """The one of `known` closest to `name` (difflib), or else the one whose
    other word in `aliases` (a label, by any case) is closest to it; None
    when none is close enough to be a typo or `name` is not text."""
    if not isinstance(name, str):
        return None
    found = difflib.get_close_matches(name, list(known), n=1, cutoff=_TYPO)
    if found:
        return found[0]
    words = {word.lower(): target for word, target in (aliases or {}).items()}
    found = difflib.get_close_matches(name.lower(), list(words), n=1, cutoff=_TYPO)
    return words[found[0]] if found else None


def typo_hint(name: object, known: Iterable[str], aliases: Mapping[str, str] | None = None) -> str:
    """` (did you mean 'x'?)` when `name` is a typo of `x`, one of `known`
    (`did_you_mean`), else nothing: the words a refusal puts after a name."""
    guess = did_you_mean(name, known, aliases)
    return f" (did you mean {guess!r}?)" if guess is not None else ""


def blame(exc: BaseException, path: str, note: str) -> None:
    """Mark `exc` as raised by the part at address `path`, once: the first
    part to blame it is the innermost, and `note` is added for the reader."""
    if blamed(exc) is None:
        exc.pewpew_path = path  # type: ignore[attr-defined]  # read back by `blamed`
        exc.add_note(note)


def blamed(exc: BaseException) -> str | None:
    """The address `blame` marked `exc` with, or None."""
    path = getattr(exc, "pewpew_path", None)
    return path if isinstance(path, str) else None
