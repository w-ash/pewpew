"""The MCP server: pewpew's tools, resources and prompts for an AI agent,
over stdio (`python -m pewpew mcp --tier 0|1`, pewpew.agent; ADR-023).

A thin adapter. Each tool calls the function its command line verb calls,
in the lab (pewpew.lab), the fleet survey (pewpew.boards) or the engine
client (pewpew.remote), and returns that result's `to_json()` as
structured content and as JSON text, with a contact sheet as a PNG where
it draws one. So a tool answers what the verb's `--json` prints, and its
output schema is the result's class. Tools, in this order:

    catalog_search  fx catalog      what a look can be made of
    look_check      fx check        a look's problems, or the look normalized
    look_render     fx render       a handle, metrics, warnings and a sheet
    look_compare    fx compare      how render B differs from A, and an A/B sheet
    look_vary       fx vary         looks made from a seed or like a look, and a numbered sheet
    engine_observe  observe         a running engine's state, metrics and a sheet
    fleet_status    boards scan     each WLED board on the network, and its health
    engine_apply    push            tier 1: send a look to an engine on this machine
    engine_set      push --set      tier 1: set one knob of that engine

The tier-0 tools only read (CLAUDE.md T-7). `--tier 1` adds the two
writes, each a dry run unless `dry_run` is false; pewpew.remote.control
holds tier 1 for them (an engine on this machine or an `--allow-host` IP,
run with `--accept-looks`, an audit record before the first byte). No
tool writes to the fleet.

A look's patterns resolve by their gallery names (pewpew.load), as on an
engine; no tool argument names a file the server runs.

A refused look, kind or cursor is an `isError` result that teaches: each
problem's code, path, reason and fix, then the corrected call or what to
do, as text, and then the problems as JSON text, in the form
`fx check --json` prints them. Any other failure the caller can fix (an
engine that does not answer, an expired handle, a bad map) is an
`isError` result whose text says what to do. An `isError` result has no
structured content: a client can check that against the tool's output
schema, which an error does not match (the TypeScript SDK client does).

Resources: the catalog (`pewpew://catalog`, a record at
`pewpew://catalog/{kind}/{id}`), the example looks of examples/
(`pewpew://looks/{name}`; the list names those there at start, and a
read finds one added since), the guides (`pewpew://docs/{topic}`: the
authoring guide and the generated catalog reference), one section of the
authoring guide by its number (`pewpew://docs/authoring/{section}`), and
a render's contact sheet (`pewpew://render/{handle}/sheet.png`). Prompts:
`design-look` and `critique-pair`.
"""

from __future__ import annotations

import base64
import functools
import inspect
import json
import re
from collections.abc import Callable, Mapping, Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp.server.mcpserver.resources import FileResource, FunctionResource
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations
from pydantic import ConfigDict, Field, create_model, model_validator

from pewpew import lab
from pewpew.boards import Fleet, parse_subnet, survey
from pewpew.errors import describe_exception, unknown
from pewpew.fx.catalog import KINDS, RECORD_KINDS, doc, markdown
from pewpew.fx.catalog import catalog as whole_catalog
from pewpew.fx.surprise import STRENGTH, NoLook
from pewpew.lab import CatalogPage, Check, Comparison, Expired, Problem, Refused, Rendered, Variations
from pewpew.lab.rendering import DEFAULT_FPS, DEFAULT_SECONDS, MAX_FPS, MAX_SECONDS
from pewpew.lab.search import Detail, example_looks, index
from pewpew.lab.variations import MAX_VARIANTS
from pewpew.mapping import DEFAULT_MAP
from pewpew.remote.client import Unreachable
from pewpew.remote.control import Forbidden, Pushed, push, report, set_value
from pewpew.remote.observe import WATCH_S, Observation, capture
from pewpew.result import Result

ROOT = Path(__file__).resolve().parents[2]  # the repo: examples/ and docs/ when run from a checkout
EXAMPLES = ROOT / "examples"
GUIDE = ROOT / "docs" / "authoring.md"
JSON = "application/json"
MAX_OBSERVE_S = 10.0

READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)
WATCH = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True)

INSTRUCTIONS = """\
pewpew renders looks for addressable LEDs. A look is layers bottom first, each running one pattern or an \
effect program (a graph of ops), and signals whose routes move its knobs each frame. Loop: catalog_search for \
the parts, write the look, look_check it, look_render it and read the metrics before the image, change one \
thing, look_compare against the last render. The look format is in pewpew://docs/authoring/4 (layers) and \
pewpew://docs/authoring/5 (effect programs); example looks are at pewpew://looks/{name}."""

# ---- argument types: module level, so the SDK reads them off the signatures --------------
# The SDK (mcp 2.3.0) resolves a tool's annotations, and its result dataclass's fields, in the
# defining module's globals when the tool registers. So import every type a tool signature or a
# result field names at run time, never under TYPE_CHECKING: registration fails on a NameError.
# Give a result field's default as a value (`= ()`), never `default_factory`: the SDK reads
# defaults with getattr, so it publishes that field as required, with no error.


def _either(words: Sequence[str]) -> str:
    """`words` as "a, b or c"."""
    return f"{', '.join(words[:-1])} or {words[-1]}"


PATTERN_LOOK, PROGRAM_LOOK = example_looks()
EXAMPLE_HANDLE = "r1-0123456789abcdef0123"
EXAMPLE_URL = "http://127.0.0.1:7447/"
LookArg = Annotated[dict[str, Any], Field(
    description='A look, {"layers": [...]}, bottom layer first, or a looks file, {"version": 4, "looks": {...}}. '
    'A layer is {"id", "nodes": {node id: {"op", "in": [node ids], "args": {...}}}}; a pattern node is '
    '{"op": "pattern", "args": {"pattern": NAME, ...its params}}. A look may add "signals", {signal id: {"op", '
    '"args"}}, and "routes", [{"source": signal id, "path": knob address, "depth"}], that move knobs each frame. '
    'Patterns go by name, never by file.',
    examples=[PATTERN_LOOK, PROGRAM_LOOK],
)]
Query = Annotated[str | None, Field(description="Words that each must appear in a name, label or doc",
                                    examples=["fold", "noise palette"])]
Kind = Annotated[str | None, Field(
    description=f"Only one kind: {_either(RECORD_KINDS)} (a param kind), or the ops of one signature: "
    f"{_either(KINDS[len(RECORD_KINDS):])}", examples=["coord", "palette"],
)]
Format = Annotated[Detail, Field(description="concise: kind, name, label and first sentence; detailed: also each "
                                 "whole record, with params and examples")]
Cursor = Annotated[str | None, Field(description="The next_cursor of the page before; omit for the first page")]
Explain = Annotated[bool, Field(description="Also describe the look in words, knob by knob; each look of a "
                                            "looks file")]
MapArg = Annotated[str, Field(
    description="Where it renders: line:N, grid:WxH, lattice:N, or a room map file",
    examples=["grid:16x16", "line:64"],
)]
Seconds = Annotated[float, Field(gt=0, le=MAX_SECONDS, description="Seconds to render; flashing needs at least 1")]
Fps = Annotated[float, Field(gt=0, le=MAX_FPS, description="Frames per second")]
Seed = Annotated[int, Field(ge=0, description="Seeds the stand-in audio and room features (`run --seed`)")]
SheetArg = Annotated[bool, Field(description="Also return the frames as a contact sheet image")]
RenderFormat = Annotated[Detail, Field(description="concise: handle, metrics and warnings; detailed: also the "
                                       "render spec, with the whole look normalized")]
Side = Annotated[str | dict[str, Any], Field(
    description="A render handle (r1-...) from look_render, or a look to render as the other side was",
    examples=[EXAMPLE_HANDLE, PATTERN_LOOK],
)]
VaryLook = Annotated[dict[str, Any] | None, Field(
    description="The look to make looks like, as look_check takes it; omit it to make looks from nothing",
    examples=[PROGRAM_LOOK],
)]
MakeSeed = Annotated[int, Field(ge=0, description="The seed the looks are made from; the same seed gives the "
                                "same looks")]
Count = Annotated[int, Field(ge=1, le=MAX_VARIANTS, description="How many looks to make")]
Strength = Annotated[float, Field(gt=0, le=1, description="How far each look moves from `look`, above 0 and at "
                                  "most 1: 1 changes it most")]
Keep = Annotated[list[str] | None, Field(
    description="Addresses of `look` to hold as they are, with all under them: a knob (layers.base.osc.freq), a "
    "node (layers.base.osc), a layer (layers.base) or a signal (signals.lfo)",
    examples=[["layers.base.osc"]],
)]
Audio = Annotated[bool, Field(description="Let a made look follow the sound (offline, the stand-in audio)")]
Url = Annotated[str, Field(description="The engine's preview address, as its `preview at` line prints it",
                           examples=[EXAMPLE_URL])]
ObserveSeconds = Annotated[float, Field(gt=0, le=MAX_OBSERVE_S, description="Seconds of engine time to watch")]
Subnet = Annotated[str | None, Field(description="The network to scan, a /22 or smaller; default this machine's /24",
                                     examples=["192.168.8.0/24"])]
Fade = Annotated[float | None, Field(ge=0, description="Seconds to fade over; default the look's own fade")]
DryRun = Annotated[bool, Field(description="Check and show what would be sent, and send nothing; false to send")]
Address = Annotated[str, Field(
    description="A knob's address: layers.<layer>.<node>.<arg>, layers.<layer>.opacity or signals.<signal>.<arg>",
    examples=["layers.base.comet.speed", "layers.top.opacity"],
)]
Value = Annotated[Any, Field(description="The knob's new value, as JSON: a number, a choice key, true or false",
                             examples=[0.4, "screen", True])]


def serve(tier: int, *, allow_hosts: Sequence[str] = (), argv: Sequence[str] = ()) -> None:
    """Serve the tools of `tier` on stdio until the client closes stdin."""
    build(tier, allow_hosts=allow_hosts, argv=argv).run()


def build(tier: int = 0, *, allow_hosts: Sequence[str] = (), argv: Sequence[str] = ()) -> MCPServer:
    """The server with the tools of `tier` (0 or 1), its resources and its
    prompts. `allow_hosts` and `argv` go to the tier-1 writes: the bench
    machines they may write to, and the command line the audit record
    names."""
    @_teaching
    def catalog_search(
        query: Query = None, kind: Kind = None, response_format: Format = "concise", cursor: Cursor = None,
    ) -> Annotated[CallToolResult, CatalogPage]:
        """Search what a look is made of: ops (by signature; kind lists them), gallery patterns, blend
        modes, palettes and param kinds. Concise items give each one's kind,
        name, label and first sentence; detailed ones add its whole record: params with defaults and ranges,
        and examples as builder chains and as JSON, a layer's program (out and nodes: a look holds it as
        {"layers": [{"id": "base", ...program}]}) or, for a signal op, a whole look. A page holds 50 concise or
        10 detailed items; pass next_cursor back as cursor for the next. pewpew://catalog/{kind}/{name} holds
        one record whole."""
        return _ok(lab.catalog(kind, query, response_format, cursor))

    @_teaching
    def look_check(look: LookArg, explain: Explain = False) -> Annotated[CallToolResult, Check]:
        """Check a look, or a looks file, without rendering it: the aura's own checks, each problem with a
        code, its path (layers.base.comet.speed), a did-you-mean and a fix. A look that checks comes back
        normalized, every knob of every node written out with its value."""
        checked = lab.check_look(look)
        if not checked.ok:
            raise Refused(checked.problems)
        return _ok(checked, texts=_words(look, checked) if explain else ())

    @_teaching
    def look_render(
        look: LookArg, map: MapArg = DEFAULT_MAP, seconds: Seconds = DEFAULT_SECONDS, fps: Fps = DEFAULT_FPS,
        seed: Seed = 0, sheet: SheetArg = True, response_format: RenderFormat = "concise",
    ) -> Annotated[CallToolResult, Rendered]:
        """Render a look offline, as the aura runs it, and measure the frames. Returns a handle (r1-...) that
        look_compare and pewpew://render/{handle}/sheet.png take; the metrics (flash_rate_max at most 3 per
        second, mean_luma, black_fraction, clip_fraction, motion_energy, frozen_fraction, palette_spread,
        ...); warnings, such as a gate the look would fail; and a contact sheet of the frames. Read the
        metrics before the image. The same arguments always give the same handle and frames."""
        rendered = lab.render(look, map, seconds, fps, seed)
        images = (Path(lab.sheet(rendered).path).read_bytes(),) if sheet else ()
        return _ok(rendered if response_format == "detailed" else rendered.brief(), images=images)

    @_teaching
    def look_compare(a: Side, b: Side, map: MapArg = DEFAULT_MAP) -> Annotated[CallToolResult, Comparison]:
        """How render B differs from render A: each knob, signal, route or front list that differs, by its
        path; RMS and largest difference of the frames; the first frame that differs; each metric of B less
        A's; and a sheet with rows A and B at the same times. A look renders as the other side was rendered
        (map, seconds, fps, seed); two looks both render on `map`. The numbers are evidence, never a verdict."""
        result = lab.compare(a, b, map_spec=map)
        drawn = lab.compare_sheet(a, b, map_spec=map)
        return _ok(result, images=(Path(drawn.path).read_bytes(),))

    @_teaching
    def look_vary(
        look: VaryLook = None, seed: MakeSeed = 0, n: Count = 4, strength: Strength = STRENGTH, keep: Keep = None,
        map: MapArg = DEFAULT_MAP, audio: Audio = False, sheet: SheetArg = True,
    ) -> Annotated[CallToolResult, Variations]:
        """Make n looks from a seed: from nothing, or like `look` at `strength`, holding the addresses in `keep`.
        Each is judged on the map before it is given (it checks, flashes at most 3 times a second, is not black,
        and every knob changes the picture), then rendered: each candidate gives its look, its own seed, its render
        handle (for look_compare and pewpew://render/{handle}/sheet.png), its metrics, and `taste`, the taste
        gates its render fails (too dark, washed out, dies out, frozen, noise, grey), which a made look avoids
        when it can. The sheet shows them in
        rows numbered 1 to n, at the same times. The same arguments always give the same looks."""
        made = lab.vary(look, seed, n, strength, keep or (), map, audio=audio)
        images = (Path(lab.rows([c.handle for c in made.candidates]).path).read_bytes(),) if sheet else ()
        return _ok(made, images=images)

    @_teaching
    def engine_observe(
        url: Url, seconds: ObserveSeconds = WATCH_S, sheet: SheetArg = True,
    ) -> Annotated[CallToolResult, Observation]:
        """Watch a running engine without changing it: its aura state (layers, master, whether a crossfade
        runs), status, every knob's value by address, health, the metrics of the frames it streams for
        `seconds` of engine time, and a contact sheet of them. The numbers are approximate: the frames arrive
        as 8-bit display gamma, and a large map is decimated. `faded` says a crossfade ran in the window, so
        the frames mix two looks: observe again once it ends."""
        seen = capture(url, seconds)
        drawn = seen.sheet() if sheet else None
        return _ok(seen.observation(), images=() if drawn is None else (drawn.png,))

    @_teaching
    def fleet_status(subnet: Subnet = None) -> Annotated[CallToolResult, Fleet]:
        """List each WLED board that answers on the network, by address: its name, MAC, WLED version, whether
        it shows a live stream and from where, its signal, free memory and uptime, and a health level with
        reasons and a fix. Reads only; takes a few seconds."""
        return _ok(survey(None if subnet is None else parse_subnet(subnet)))

    @_teaching
    def engine_apply(
        url: Url, look: LookArg, fade: Fade = None, dry_run: DryRun = True,
    ) -> Annotated[CallToolResult, Pushed]:
        """Send a whole look to an engine on this machine run with --preview --accept-looks, which fades to it
        over `fade` seconds (the look's own fade when none is given; the message says how long) and answers
        ack or refused. Observing during the fade measures both looks. The look is checked here first. A dry
        run (the default) checks the look against this machine's patterns and that the engine is on this
        machine, and shows the message it would send; the engine's map and --accept-looks are checked only on
        a send. Call again with dry_run false to send it, which appends an audit record first."""
        return _pushed(push(url, look, fade=fade, dry_run=dry_run, allow_hosts=allow_hosts,
                            argv=[*argv, "engine_apply"]))

    @_teaching
    def engine_set(url: Url, path: Address, value: Value, dry_run: DryRun = True) -> Annotated[CallToolResult, Pushed]:
        """Set one knob of the look an engine on this machine runs, by its address; the engine checks the knob
        and the value against its look and answers ack or refused. A dry run (the default) checks that the
        engine is on this machine and that the address has a knob's form, and shows the message; whether the
        look has that knob and takes the value is checked only on a send (engine_observe lists every knob and
        its value). Call again with dry_run false to send it, which appends an audit record first."""
        return _pushed(set_value(url, path, value, dry_run=dry_run, allow_hosts=allow_hosts,
                                 argv=[*argv, "engine_set"]))

    tools = [
        _tool(catalog_search, READ, {"query": "fold", "kind": "coord"}, {"kind": "palette"}),
        _tool(look_check, READ, {"look": PROGRAM_LOOK, "explain": True}),
        _tool(look_render, READ, {"look": PROGRAM_LOOK, "map": "grid:16x16", "seconds": 2}),
        _tool(look_compare, READ, {"a": EXAMPLE_HANDLE, "b": PATTERN_LOOK}),
        _tool(look_vary, READ, {"n": 4, "map": "grid:16x16"},
              {"look": PROGRAM_LOOK, "seed": 7, "n": 3, "strength": 0.4, "keep": ["layers.base.osc"]}),
        _tool(engine_observe, WATCH, {"url": EXAMPLE_URL, "seconds": 2}),
        _tool(fleet_status, WATCH, {}),
    ]
    if tier >= 1:
        tools += [
            _tool(engine_apply, WRITE, {"url": EXAMPLE_URL, "look": PROGRAM_LOOK, "fade": 2}),
            _tool(engine_set, WRITE, {"url": EXAMPLE_URL, "path": "layers.base.osc.freq", "value": 4}),
        ]
    server = MCPServer("pewpew", version=version("pewpew"), instructions=INSTRUCTIONS, tools=tools,
                       log_level="WARNING")
    _resources(server)
    _prompts(server)
    return server


# ---- results ------------------------------------------------------------------------------


def _ok(result: Result, *, texts: Sequence[str] = (), images: Sequence[bytes] = ()) -> CallToolResult:
    """`result` as structured content and as JSON text, then `texts` and
    `images` (PNG)."""
    data = result.to_json()
    return CallToolResult(
        content=[
            *(TextContent(type="text", text=text) for text in (json.dumps(data), *texts)),
            *(ImageContent(type="image", data=base64.b64encode(png).decode(), mime_type="image/png")
              for png in images),
        ],
        structured_content=data,
    )


def _failed(text: str, details: Result | None = None) -> CallToolResult:
    """An `isError` result: `text`, then `details` as JSON text (module
    docstring)."""
    texts = (text,) if details is None else (text, json.dumps(details.to_json()))
    return CallToolResult(is_error=True, content=[TextContent(type="text", text=t) for t in texts])


def _pushed(pushed: Pushed) -> CallToolResult:
    """A write's result; an error when the engine refused part of it."""
    if pushed.ok:
        return _ok(pushed)
    return _failed(f"{report(pushed)}\nfix what the engine refused and call again", pushed)


def _words(look: Mapping[str, Any], checked: Check) -> tuple[str, ...]:
    """The look that `checked` passed in words; for a looks file, each of
    its looks, by name."""
    names = (checked.look_normalized or {}).get("looks")
    if names is None:
        return (lab.explain(look).text(),)
    return tuple(f"look {name!r}: {lab.explain(look, name=name).text()}" for name in names)


def _teaching(tool: Callable[..., CallToolResult]) -> Callable[..., CallToolResult]:
    """`tool` with each failure its caller can fix answered as an `isError`
    result that says how (module docstring)."""
    defaults = {name: p.default for name, p in inspect.signature(tool).parameters.items()}

    @functools.wraps(tool)
    def answer(**args: Any) -> CallToolResult:
        try:
            return tool(**args)
        except Refused as exc:
            given = {name: value for name, value in args.items() if value != defaults.get(name)}
            return _failed(_teach(tool.__name__, given, exc.problems), Check(False, None, exc.problems))
        except (Expired, Unreachable, Forbidden, NoLook) as exc:
            return _failed(str(exc))
        except (ValueError, OSError) as exc:
            return _failed(describe_exception(exc).removeprefix("ValueError: "))

    return answer


def _teach(tool: str, given: Mapping[str, Any], problems: Sequence[Problem]) -> str:
    """Each problem's code, path, reason and fix, then the corrected call
    when every problem names an argument of `tool` and the value it takes,
    else what to do."""
    lines = []
    for p in problems:
        lines.append(f"{p.code} at {p.path or 'the look'}: {p}")
        if p.fix is not None:
            lines.append(f"  fix: {p.fix}")
    fixes = {p.path: p.did_you_mean for p in problems}
    if all(path in given and guess is not None for path, guess in fixes.items()):
        call = ", ".join(f"{name}={json.dumps(value)}" for name, value in {**given, **fixes}.items())
        lines.append(f"corrected call: {tool}({call})")
    else:
        lines.append(f"apply each fix and call {tool} again")
    return "\n".join(lines)


class _KnownArguments(ArgModelBase):
    """A tool's arguments that refuse one the tool does not take, naming
    the closest it does; the SDK would drop it without a word."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _known(cls, data: Any) -> Any:
        names = list(cls.model_fields)
        for key in data if isinstance(data, dict) else ():
            if key not in names:
                raise ValueError(unknown("argument", key, names, suggest=True))
        return data


def _tool(fn: Callable[..., CallToolResult], annotations: ToolAnnotations, *examples: dict[str, Any]) -> Tool:
    """`fn` as a tool with `annotations`, arguments that refuse an unknown
    one, and whole example calls in its input schema."""
    tool = Tool.from_function(fn, description=doc(fn), annotations=annotations)
    args = tool.fn_metadata.arg_model
    tool.fn_metadata.arg_model = create_model(args.__name__, __base__=(args, _KnownArguments))
    tool.parameters = {**tool.fn_metadata.arg_model.model_json_schema(by_alias=True), "examples": list(examples)}
    return tool


# ---- resources and prompts ----------------------------------------------------------------


def _resources(server: MCPServer) -> None:
    """The catalog, example looks, guides and render sheets (module
    docstring)."""

    @server.resource("pewpew://catalog", name="catalog", mime_type=JSON)
    def catalog_index() -> str:
        """Every op, pattern, blend, palette and param kind: kind, name, label and first sentence."""
        return json.dumps(index().to_json())

    @server.resource("pewpew://catalog/{kind}/{id}", name="catalog-record", mime_type=JSON)
    def catalog_record(kind: str, id: str) -> str:
        """One whole catalog record: kind is op, pattern, blend, palette or kind; id is its name."""
        try:
            return json.dumps(lab.describe(kind, id))
        except Refused as exc:
            raise ResourceNotFoundError("; ".join(str(p) for p in exc.problems)) from None

    for name, path in _examples().items():
        server.add_resource(FileResource(uri=f"pewpew://looks/{name}", name=f"look-{name}", path=path,
                                         mime_type=JSON, description=f"The example looks file {path.name}"))

    @server.resource("pewpew://looks/{name}", name="look", mime_type=JSON)
    def look_file(name: str) -> str:
        """An example looks file (version 4) from examples/, by its name."""
        looks = _examples()
        if name not in looks:
            raise ResourceNotFoundError(unknown("look", name, looks, suggest=True))
        return looks[name].read_text()

    guides: dict[str, Callable[[], str]] = {"authoring": GUIDE.read_text} if GUIDE.is_file() else {}
    guides["catalog"] = lambda: markdown(whole_catalog())
    about = {"authoring": "The authoring guide: knobs, layers (section 4), effect programs (section 5), "
             "the command line (section 6) and writing a new op (section 9)",
             "catalog": "The catalog reference: every op, pattern, blend, "
             "palette and param kind, with examples"}
    for topic, read in guides.items():
        server.add_resource(FunctionResource(uri=f"pewpew://docs/{topic}", name=f"docs-{topic}", fn=read,
                                             mime_type="text/markdown", description=about[topic]))

    @server.resource("pewpew://docs/{topic}", name="docs", mime_type="text/markdown")
    def guide(topic: str) -> str:
        """A guide by topic: authoring or catalog."""
        if topic not in guides:
            raise ResourceNotFoundError(unknown("topic", topic, guides, suggest=True))
        return guides[topic]()

    @server.resource("pewpew://docs/authoring/{section}", name="docs-authoring-section", mime_type="text/markdown")
    def authoring_section(section: str) -> str:
        """One section of the authoring guide, by its number: 4 is layers, 5 effect programs, 6 the
        command line, 7 the MCP server, 9 writing a new op."""
        text = GUIDE.read_text() if GUIDE.is_file() else ""
        found = section_of(text, section)
        if found is None:
            numbers = re.findall(r"^## (\d+)\.", text, re.MULTILINE)
            raise ResourceNotFoundError(unknown("section", section, numbers))
        return found

    @server.resource("pewpew://render/{handle}/sheet.png", name="render-sheet", mime_type="image/png")
    def render_sheet(handle: str) -> bytes:
        """The contact sheet of a render, by the handle look_render gave."""
        try:
            return Path(lab.sheet(handle).path).read_bytes()
        except (Expired, ValueError) as exc:
            raise ResourceNotFoundError(str(exc)) from None


def section_of(guide: str, number: str) -> str | None:
    """Section `number` of a Markdown `guide`: from its `## <number>.`
    heading up to the next `## ` heading; None when it has none."""
    found = re.search(rf"^## {re.escape(number)}\. .*?(?=^## |\Z)", guide, re.MULTILINE | re.DOTALL)
    return None if found is None else found[0]


def _examples() -> dict[str, Path]:
    """The example looks files in examples/ now, by name."""
    return {path.name.removesuffix(".look.json"): path for path in sorted(EXAMPLES.glob("*.look.json"))}


def _prompts(server: MCPServer) -> None:
    @server.prompt(name="design-look", title="Design a look")
    def design_look(brief: Annotated[str, Field(description="What the look should feel like")]) -> str:
        """Design a look from a brief, in the check, render and compare loop."""
        return (
            f"Design a pewpew look for this brief: {brief}\n\n"
            "1. catalog_search with words from the brief for ops, patterns, palettes and blends; read the "
            "detailed record of each part you use.\n"
            "2. Write the look as JSON (pewpew://docs/authoring/4 and pewpew://docs/authoring/5; examples at "
            "pewpew://looks/{name}).\n"
            "3. look_check it and apply each fix it gives.\n"
            "4. look_render it. Read the metrics and warnings before the image: flash_rate_max at most 3, "
            "black_fraction under 1, motion_energy above 0, palette_spread for variety.\n"
            "5. Change one thing at a time and look_compare each render against the one before.\n"
            "Give the final look, its handle, and what each layer does."
        )

    @server.prompt(name="critique-pair", title="Critique two renders")
    def critique_pair(
        a: Annotated[str, Field(description="Render A: a handle from look_render")],
        b: Annotated[str, Field(description="Render B: a handle from look_render")],
    ) -> str:
        """Judge two renders side by side, in both orders."""
        return (
            f"Compare render A ({a}) with render B ({b}).\n"
            f"Call look_compare(a={json.dumps(a)}, b={json.dumps(b)}), then look_compare with a and b swapped, "
            "and judge each order on its own before you combine them: which reads better on LEDs (motion, "
            "contrast, colour, no flashing), and why, citing the metric deltas. If the two orders disagree, "
            "the verdict is a tie.\n"
            'Answer as JSON: {"winner": "A" | "B" | "tie", "confidence": 0 to 1, "reasons": [...], '
            '"evidence": {metric: delta}}. A verdict is evidence, never a gate.'
        )
