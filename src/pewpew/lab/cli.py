"""The lab's command line: `python -m pewpew fx VERB` and `verify looks`.

Tier 0, offline (CLAUDE.md T-7): each verb reads files and the render
cache, writes only the cache and the `--out` file, and sends nothing.

    fx check FILE            the problems of a looks file or look, or ok
    fx render FILE           render a look; its handle, spec and metrics
    fx sheet HANDLE|FILE     a contact sheet PNG
    fx metrics HANDLE|FILE   the metrics, and with --liveness each knob's
    fx compare A B           how B differs from A, each a handle or a file
    fx explain FILE          a look in words
    fx vary [FILE]           looks made from a seed, or like FILE, each rendered
    verify looks FILE|DIR    the content gate (pewpew.lab.verify)

FILE is a looks file (a `.look.json` file is one), as `run LOOKS`
reads it; `-` reads a looks file or a single look, as JSON, from stdin.
With `--json` a verb prints exactly one JSON document on stdout, its
result's `to_json()`, and diagnostics go to stderr. Exit codes: 0 ok; 1
problems with the look or a failed gate; 2 a usage error; 3 a handle the
cache no longer holds. `fx vary` exits 1 when nothing it made passes the
content gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pewpew.command import GONE, OK, PROBLEMS, STDIN, USAGE, number, png_path, positive, whole
from pewpew.fx.surprise import STRENGTH, NoLook, check_strength
from pewpew.lab.check import Check, LookDoc, check_look
from pewpew.lab.comparison import Comparison, compare, compare_sheet
from pewpew.lab.explanation import Explanation, explain
from pewpew.lab.geometry import parse_geometry
from pewpew.lab.handles import Expired, is_handle
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, MAX_FPS, MAX_SECONDS, Rendered, render
from pewpew.lab.variations import MAX_VARIANTS, Variations, vary
from pewpew.lab.verify import Verification, verify_looks
from pewpew.lab.views import Measured, Picture, metrics, rows, sheet
from pewpew.mapping import DEFAULT_MAP
from pewpew.problems import Problem, Refused
from pewpew.result import Result
from pewpew.sheet import LAYOUTS

Handler = Callable[[argparse.Namespace], int]


def add_parser(sub: argparse._SubParsersAction, verbs: argparse._SubParsersAction) -> None:
    """Add the lab's verbs to the `fx` command's `verbs` (`pewpew.fx.cli.add_parser`) and the `verify`
    command to `sub`."""
    out = _options()
    out.add_argument("--json", action="store_true",
                     help="print the result as one JSON document on stdout; diagnostics go to stderr")
    look = _options()
    look.add_argument("--look", dest="name", default=None, metavar="NAME",
                      help="the look of a looks file to use (default: its only look, else its 'current' one)")
    span = _options()
    span.add_argument("--map", type=_map, default=DEFAULT_MAP, metavar="SPEC",
                      help=f"line:64, grid:16x16, lattice:8 or a room map file (default {DEFAULT_MAP}, the map "
                      "`run` uses without --map or --room)")
    span.add_argument("--seconds", type=positive("seconds", MAX_SECONDS), default=DEFAULT_SECONDS, metavar="S",
                      help=f"how long to render (default {DEFAULT_SECONDS:g})")
    span.add_argument("--fps", type=positive("frames per second", MAX_FPS), default=DEFAULT_FPS,
                      help=f"frames per second (default {DEFAULT_FPS:g})")
    timing = _options(span)
    timing.add_argument("--seed", type=whole(0, "a seed"), default=0,
                        help="as `run --seed`: seeds the stand-in audio and room features (default 0); the "
                        "look's own seed seeds its layers")
    picture = _options()
    picture.add_argument("--out", type=png_path, default=None, metavar="PNG",
                         help="write the contact sheet to PNG (default: into the render cache)")
    draw = _options()
    draw.add_argument("--layout", choices=LAYOUTS, default="auto", help="the sheet's layout (default auto)")
    draw.add_argument("--width", type=int, default=1024, help="the sheet's width in px, 896 to 1568 (default 1024)")

    file_help = "a looks file (.look.json); - reads a looks file or a single look, as JSON, from stdin"
    source_help = "a render handle (r1-...), or a looks file or look to render; - reads stdin"

    p = verbs.add_parser("check", parents=[out], help="list a look's problems, or print it normalized")
    p.add_argument("source", type=_source, metavar="FILE", help=file_help)
    _handle(p, _check)

    p = verbs.add_parser("render", parents=[out, look, timing],
                         help="render a look; print its handle, spec and metrics")
    p.add_argument("source", type=_source, metavar="FILE", help=file_help)
    p.add_argument("--out", type=png_path, default=None, metavar="PNG", help="also write a contact sheet to PNG")
    _handle(p, _render)

    p = verbs.add_parser("sheet", parents=[out, look, timing, picture, draw],
                         help="draw a render as a contact sheet")
    p.add_argument("source", type=_source, metavar="HANDLE|FILE", help=source_help)
    p.add_argument("--tiles", type=int, default=8, help="frames a tiled sheet shows (default 8)")
    _handle(p, _sheet)

    p = verbs.add_parser("metrics", parents=[out, look, timing], help="measure a render's frames")
    p.add_argument("source", type=_source, metavar="HANDLE|FILE", help=source_help)
    p.add_argument("--liveness", action="store_true",
                   help="also check that each knob changes the picture (renders the look again per probe)")
    _handle(p, _metrics)

    p = verbs.add_parser("compare", parents=[out, look, timing, picture, draw],
                         help="how render B differs from render A")
    p.add_argument("a", type=_source, metavar="A", help=f"{source_help}; a look renders as B did when only B is a "
                   "render")
    p.add_argument("b", type=_source, metavar="B", help=f"{source_help}; a look renders as A did")
    p.add_argument("--tiles", type=int, default=4, help="frames per row of the sheet (default 4)")
    _handle(p, _compare)

    p = verbs.add_parser("explain", parents=[out, look], help="describe a look in words")
    p.add_argument("source", type=_source, metavar="FILE", help=file_help)
    _handle(p, _explain)

    p = verbs.add_parser("vary", parents=[out, look, span, draw],
                         help="make looks from a seed, or like a look; render each",
                         description="Without FILE, make looks from nothing (pewpew.fx.surprise); with it, make looks "
                         "like it. Each candidate comes from its own seed, is judged on the map (it checks, flashes "
                         "at most 3 times a second, is not black, and every knob changes the picture) and is "
                         "rendered; its handle takes fx sheet and fx compare.")
    p.add_argument("source", type=_source, nargs="?", default=None, metavar="FILE",
                   help=f"{file_help}; without it, looks are made from nothing")
    p.add_argument("--seed", type=whole(0, "a seed"), default=0, help="the seed the looks are made from (default 0)")
    p.add_argument("--n", type=whole(1, "a count", MAX_VARIANTS), default=4,
                   help=f"how many looks, 1 to {MAX_VARIANTS} (default 4)")
    p.add_argument("--strength", type=_strength, default=STRENGTH,
                   help=f"how far each look moves from FILE, above 0 and at most 1 (default {STRENGTH:g})")
    p.add_argument("--keep", action="append", default=[], metavar="PATH",
                   help="an address of FILE's look to hold as it is, with all under it: a knob "
                   "(layers.base.osc.freq), a node, a layer or a signal; give it again for more")
    p.add_argument("--audio", action="store_true", help="let a made look follow the sound")
    p.add_argument("--out", type=png_path, default=None, metavar="PNG",
                   help="also write the looks in one sheet, rows numbered 1 to n")
    _handle(p, _vary)

    verify = sub.add_parser("verify", help="gate content before a run (tier 0)")
    what = verify.add_subparsers(dest="verb", required=True, metavar="WHAT")
    p = what.add_parser("looks", parents=[out, timing], help="check, render and gate looks files",
                        description="A look passes when it checks, no layer raises, it flashes at most 3 times a "
                        "second, it is not all black, and every knob changes the picture.")
    p.add_argument("paths", type=Path, nargs="+", metavar="FILE|DIR",
                   help="a looks file, or a folder of *.look.json files")
    _handle(p, _verify)


# ---- the verbs ----------------------------------------------------------------


def _check(args: argparse.Namespace) -> int:
    result = check_look(_doc(args.source))
    _show(args, result, _check_text)
    return OK if result.ok else PROBLEMS


def _render(args: argparse.Namespace) -> int:
    rendered = _rendering(args, args.source)
    drawn = sheet(rendered, out=args.out) if args.out is not None else None
    _show(args, rendered, lambda r: _rendered_text(r) + ("" if drawn is None else f"\nsheet: {drawn.path}"))
    return OK


def _sheet(args: argparse.Namespace) -> int:
    source = _render_or_handle(args, args.source)
    _show(args, sheet(source, args.layout, args.tiles, args.width, out=args.out), _picture_text)
    return OK


def _metrics(args: argparse.Namespace) -> int:
    _show(args, metrics(_render_or_handle(args, args.source), liveness=args.liveness), _measured_text)
    return OK


def _compare(args: argparse.Namespace) -> int:
    if args.a == STDIN and args.b == STDIN:
        raise _Usage("only one of A and B can be -, stdin")
    a, b = (side if is_handle(side) else _doc(side) for side in (args.a, args.b))
    kw: dict[str, Any] = {"map_spec": args.map, "seconds": args.seconds, "fps": args.fps, "seed": args.seed,
                          "name": args.name}
    result = compare(a, b, **kw)
    drawn = None
    if args.out is not None:
        drawn = compare_sheet(a, b, layout=args.layout, tiles=args.tiles, width=args.width, out=args.out, **kw)
    _show(args, result, lambda c: _comparison_text(c) + ("" if drawn is None else f"\nsheet: {drawn.path}"))
    return OK


def _explain(args: argparse.Namespace) -> int:
    _show(args, explain(_doc(args.source), name=args.name), Explanation.text)
    return OK


def _vary(args: argparse.Namespace) -> int:
    if args.source is None and args.keep:
        raise _Usage("--keep holds addresses of a look; give the FILE to vary")
    try:
        result = vary(
            None if args.source is None else _doc(args.source), args.seed, args.n, args.strength, args.keep,
            args.map, seconds=args.seconds, fps=args.fps, audio=args.audio, name=args.name,
        )
    except NoLook as exc:
        print(f"{args.cmd} {args.verb}: {exc}", file=sys.stderr)
        return PROBLEMS
    drawn = None
    if args.out is not None:
        drawn = rows([c.handle for c in result.candidates], args.layout, 2, args.width, out=args.out)
    _show(args, result, lambda v: _variations_text(v) + ("" if drawn is None else f"\nsheet: {drawn.path}"))
    return OK


def _verify(args: argparse.Namespace) -> int:
    result = verify_looks(args.paths, map_spec=args.map, seconds=args.seconds, fps=args.fps, seed=args.seed)
    _show(args, result, _verification_text)
    return OK if result.ok else PROBLEMS


# ---- shared steps -----------------------------------------------------------------


class _Usage(Exception):
    """A usage error found after parsing: exit 2."""


def _handle(parser: argparse.ArgumentParser, verb: Handler) -> None:
    """Make `verb` the handler `python -m pewpew` runs for `parser`."""

    def run(args: argparse.Namespace, argv: list[str]) -> int:
        name = f"{args.cmd} {args.verb}"
        try:
            return verb(args)
        except Refused as exc:
            if args.json:
                _print_json(Check(False, None, exc.problems))
            else:
                for problem in exc.problems:
                    print(f"{name}: {_problem_text(problem)}", file=sys.stderr)
            return PROBLEMS
        except Expired as exc:
            if args.json:
                print(json.dumps(exc.to_json(), indent=2))
            print(f"{name}: {exc}", file=sys.stderr)
            return GONE
        except (_Usage, ValueError) as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            return USAGE
        except OSError as exc:
            print(f"{name}: {exc.strerror or exc}: {exc.filename or ''}".rstrip(": "), file=sys.stderr)
            return PROBLEMS

    parser.set_defaults(cli=run)


def _doc(source: str | Path) -> LookDoc:
    """The look `source` names: a file, or stdin for `-`."""
    if is_handle(source):
        raise _Usage(f"{source} is a render handle; this verb takes a look file. `fx vary --json` gives each "
                     "candidate's look (.candidates[i].look), to save as one")
    return sys.stdin.read() if source == STDIN else source


def _rendering(args: argparse.Namespace, source: str | Path) -> Rendered:
    """`source` rendered as the options say, its warnings on stderr."""
    rendered = render(_doc(source), args.map, args.seconds, args.fps, args.seed, name=args.name)
    for warning in rendered.warnings:
        print(f"{args.cmd} {args.verb}: {warning}", file=sys.stderr)
    return rendered


def _render_or_handle(args: argparse.Namespace, source: str | Path) -> Rendered | str:
    return source if is_handle(source) else _rendering(args, source)


def _show(args: argparse.Namespace, result: Result, text: Callable[[Any], str]) -> None:
    if args.json:
        _print_json(result)
    else:
        print(text(result))


def _print_json(result: Result) -> None:
    print(json.dumps(result.to_json(), indent=2))


# ---- argument types -----------------------------------------------------------------


def _options(*parents: argparse.ArgumentParser) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(add_help=False, parents=list(parents))


def _source(text: str) -> str | Path:
    """argparse type for a look or render: a handle, `-`, or a file."""
    return text if text == STDIN or is_handle(text) else Path(text)


def _strength(text: str) -> float:
    """argparse type for `--strength`: above 0, at most 1 (`check_strength`)."""
    value = number(text)
    if (reason := check_strength(value)) is not None:
        raise argparse.ArgumentTypeError(reason)
    return value


def _map(text: str) -> str:
    """argparse type for `--map`: a spec that gives a geometry."""
    try:
        parse_geometry(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return text


# ---- text for a person ------------------------------------------------------------------


def _problem_text(problem: Problem) -> str:
    """A problem and its code, then its fix on a line of its own."""
    return f"{problem} [{problem.code}]" + ("" if problem.fix is None else f"\n  fix: {problem.fix}")


def _check_text(check: Check) -> str:
    if not check.ok:
        return "\n".join(_problem_text(p) for p in check.problems)
    doc = check.look_normalized or {}
    key = "looks" if "looks" in doc else "layers"
    count = len(doc[key])
    return f"ok: {count} {key if count != 1 else key[:-1]}"


def _rendered_text(rendered: Rendered) -> str:
    spec, m = rendered.spec, rendered.metrics
    head = rendered.handle if spec is None else (
        f"{rendered.handle}: {spec.frames} frames of {spec.points} points ({spec.map}) at {spec.fps:g} fps, "
        f"features seed {spec.seed}"
    )
    numbers = (f"flashes {m.flash_rate_max:g}/s, mean luma {m.mean_luma:.3f} (p95 {m.p95_luma:.3f}), "
               f"black {m.black_fraction:.0%}, clipped {m.clip_fraction:.0%}, motion {m.motion_energy:.3f}/s, "
               f"frozen {m.frozen_fraction:.0%}")
    return f"{head}\n{numbers}"


def _picture_text(drawn: Picture) -> str:
    return f"{drawn.path} ({drawn.width} x {drawn.height} px, {drawn.layout})\n{drawn.legend}"


def _measured_text(measured: Measured) -> str:
    lines = [f"{name}: {value}" for name, value in measured.metrics.to_json().items()]
    if measured.liveness is not None:
        live = sum(probe.live for probe in measured.liveness)
        lines.append(f"liveness: {live} of {len(measured.liveness)} probes change the picture")
        lines += [f"  dead: {path}" for path in measured.dead]
        lines += [f"  not probed: {why}" for why in measured.unprobed]
    return "\n".join(lines)


def _comparison_text(c: Comparison) -> str:
    first = "none" if c.first_divergent_frame is None else str(c.first_divergent_frame)
    lines = [
        f"A {c.a}", f"B {c.b}",
        f"rms {c.rms:.4g}, max {c.max_abs:.4g}, first divergent frame {first}, ΔE p95 {c.delta_e_p95:.3g}",
    ]
    lines += [f"{change.path}: {json.dumps(change.a)} -> {json.dumps(change.b)}" for change in c.look_diff]
    return "\n".join(lines)


def _variations_text(v: Variations) -> str:
    made = "made from nothing" if v.strength is None else f"like the look at strength {v.strength:g}"
    lines = [f"{len(v.candidates)} looks {made}, from seed {v.seed}"]
    for i, c in enumerate(v.candidates, 1):
        m = c.metrics
        lines.append(f"{i}. {c.handle} seed {c.seed}: flashes {m.flash_rate_max:g}/s, mean luma {m.mean_luma:.3f}, "
                     f"motion {m.motion_energy:.3f}/s, {m.hue_clusters} hues")
    return "\n".join(lines)


def _verification_text(v: Verification) -> str:
    lines: list[str] = []
    looks = [look for f in v.files for look in f.looks]
    for f in v.files:
        lines += [f"FAIL {f.file}: {_problem_text(p)}" for p in f.problems]
        for look in f.looks:
            where = f"{f.file} {look.name}".rstrip()
            lines.append(f"PASS {where}" if look.ok else f"FAIL {where}: {'; '.join(look.failures)}")
    lines.append(f"{sum(look.ok for look in looks)} of {len(looks)} looks pass")
    return "\n".join(lines)
