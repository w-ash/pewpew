"""The MCP server (pewpew.mcp_server, ADR-023): an in-memory client over
the real server. Its tool list is a golden; each tool answers with its
lab result's JSON as structured content and as text (and a sheet where it
draws one); each failure is an `isError` result that teaches; resources
and prompts list and read; and the extra stays out of `import pewpew` and
out of stdout. Renders stay at line:64 or the 16x16 grid, 1 s at 10 fps."""

from __future__ import annotations

import base64
import contextlib
import json
import subprocess
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path
from typing import IO

import numpy as np
import pytest

pytest.importorskip("mcp")

from mcp import Client, MCPError
from mcp.types import BlobResourceContents, TextContent, TextResourceContents

from fakes import LoopThread, Pooled, Solid, aura_rig, instant_looks, layered, preview_sink, run_python
from pewpew import boards, lab, line, wled
from pewpew.fx import op as fx_op
from pewpew.fx.types import Sig, Ty
from pewpew.lab import search
from pewpew.load import Catalog
from pewpew.mcp_server import EXAMPLES, build
from pewpew.problems import EXAMPLE_LOOK
from pewpew.remote.client import Frame
from pewpew.remote.observe import Capture
from pngread import decode_png

pytestmark = pytest.mark.anyio

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "tests" / "goldens" / "mcp_tools.json"
TIER0 = ["catalog_search", "look_check", "look_render", "look_compare", "look_vary", "engine_observe", "fleet_status"]
FAST = {"map": "line:64", "seconds": 1, "fps": 10}
COMET = EXAMPLE_LOOK
SPED = layered("comet", {"sped": 0.4})
LOCAL = "ws://127.0.0.1:9/"
ARGV = ["mcp", "--tier", "1"]  # the command line the audit record names


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(build(1, argv=ARGV), mode="auto") as c:
        yield c


def wire(tools) -> list[dict]:
    return [tool.model_dump(by_alias=True, mode="json", exclude_none=True) for tool in tools]


def payload(result) -> dict:
    """A result's structured content, after checking that its first block
    is the same JSON as text."""
    assert json.loads(text(result.content[0])) == result.structured_content
    return result.structured_content


def refusal(result) -> dict:
    """The JSON an error result gives after its text. It carries no
    structured content, which a client would check against the tool's
    output schema (the TypeScript SDK client does, even on an error)."""
    assert result.is_error and result.structured_content is None
    return json.loads(text(result.content[1]))


def text(block: object) -> str:
    """The text of a text block: a tool's content, a resource's contents or
    a prompt's message."""
    assert isinstance(block, (TextContent, TextResourceContents)), block
    return block.text


def blob(contents: object) -> str:
    """The base64 of a resource's binary contents."""
    assert isinstance(contents, BlobResourceContents), contents
    return contents.blob


def png(block) -> bytes:
    assert block.type == "image" and block.mime_type == "image/png"
    data = base64.b64decode(block.data)
    assert decode_png(data).shape[2] == 3
    return data


# ---- the tool list -----------------------------------------------------------------


async def test_the_tool_list_is_the_golden_in_a_fixed_order_with_every_output_schema(
    client: Client, regen_goldens: bool,
) -> None:
    tools = wire((await client.list_tools()).tools)
    if regen_goldens:
        GOLDEN.write_text(json.dumps(tools, indent=2, ensure_ascii=False) + "\n")
    assert json.loads(GOLDEN.read_text()) == tools, "run `uv run pytest --regen-goldens` and review the diff"
    assert [t["name"] for t in tools] == [*TIER0, "engine_apply", "engine_set"]
    assert all(t["outputSchema"] for t in tools)
    hints = {t["name"]: t["annotations"] for t in tools}
    assert all(hints[name]["readOnlyHint"] for name in TIER0)
    assert not hints["engine_apply"]["readOnlyHint"] and hints["engine_set"]["destructiveHint"]
    assert [hints[name]["openWorldHint"] for name in TIER0] == [False] * 5 + [True] * 2
    assert all(t["inputSchema"]["examples"] for t in tools)


async def test_tier_zero_has_no_write_and_both_wire_modes_list_the_same() -> None:
    lists = []
    for mode in ("auto", "legacy"):
        async with Client(build(0), mode=mode) as c:
            lists.append(wire((await c.list_tools()).tools))
    assert lists[0] == lists[1]
    assert [t["name"] for t in lists[0]] == TIER0


async def test_a_new_op_changes_no_tool(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    before = wire((await client.list_tools()).tools)

    class Glow(fx_op.Op):
        """A test op: it shimmers."""

        sig, out = Sig.SOURCE, Ty.SCALAR

    Glow.op = "glow"
    monkeypatch.setitem(fx_op.REGISTRY, "glow", Glow)
    async with Client(build(1, argv=ARGV)) as fresh:
        assert wire((await fresh.list_tools()).tools) == before
        found = payload(await fresh.call_tool("catalog_search", {"query": "shimmers"}))
    assert [item["name"] for item in found["items"]] == ["glow"]


async def test_each_example_call_in_a_schema_is_valid(client: Client) -> None:
    for tool in (await client.list_tools()).tools:
        for args in tool.input_schema["examples"]:
            for value in (v for k, v in args.items() if k in ("look", "b") and isinstance(v, dict)):
                assert lab.check_look(value).ok, (tool.name, value)


# ---- each tool's answer ---------------------------------------------------------------


async def test_catalog_search_pages_concise_and_detailed_items(client: Client) -> None:
    first = payload(await client.call_tool("catalog_search", {}))
    assert first == lab.catalog().to_json() and first["next_cursor"] == "50"
    rest = payload(await client.call_tool("catalog_search", {"cursor": first["next_cursor"]}))
    found = [(i["kind"], i["name"]) for page in (first, rest) for i in page["items"]]
    assert rest["next_cursor"] is None and len(found) == first["total"] == len(set(found))
    coord = payload(await client.call_tool("catalog_search", {"query": "fold", "kind": "coord"}))
    assert [(i["name"], i["sig"], i["record"]) for i in coord["items"]] == [("kaleid", "coord", None),
                                                                           ("mirror", "coord", None)]
    whole = payload(await client.call_tool("catalog_search", {"query": "kaleidoscope",
                                                               "response_format": "detailed"}))
    assert whole["items"][0]["record"] == lab.describe("op", "kaleid")


async def test_look_check_gives_the_look_normalized_and_in_words(client: Client) -> None:
    result = await client.call_tool("look_check", {"look": COMET, "explain": True})
    assert not result.is_error and payload(result) == lab.check_look(COMET).to_json()
    assert text(result.content[1]) == lab.explain(COMET).text()


async def test_look_check_explains_each_look_of_a_looks_file_with_no_current(client: Client) -> None:
    doc = {"version": 4, "looks": {"a": COMET, "b": layered("comet", {"speed": 1.0})}}
    result = await client.call_tool("look_check", {"look": doc, "explain": True})
    assert not result.is_error and payload(result) == lab.check_look(doc).to_json()
    assert [text(block) for block in result.content[1:]] == [
        f"look {name!r}: {lab.explain(doc, name=name).text()}" for name in ("a", "b")
    ]


async def test_look_render_gives_the_render_a_sheet_and_the_same_json(client: Client) -> None:
    result = await client.call_tool("look_render", {"look": COMET, **FAST})
    rendered = lab.render(COMET, "line:64", 1, 10)
    assert payload(result) == rendered.brief().to_json()
    assert [b.type for b in result.content] == ["text", "image"]
    sheet = await client.read_resource(f"pewpew://render/{rendered.handle}/sheet.png")
    assert png(result.content[1]) == base64.b64decode(blob(sheet.contents[0]))
    detailed = await client.call_tool("look_render", {"look": COMET, **FAST, "sheet": False,
                                                      "response_format": "detailed"})
    assert payload(detailed) == rendered.to_json() and len(detailed.content) == 1


async def test_look_render_moves_a_knob_by_its_route(client: Client) -> None:
    still = {"layers": [{"id": "base", "out": "tint", "nodes": {
        "swell": {"op": "osc", "args": {"freq": 3.0, "sync": 0.0, "axis": "u"}},
        "tint": {"op": "palette", "in": ["swell"], "args": {"palette": "ocean"}}}}]}
    swept = {**still, "signals": {"breath": {"op": "lfo", "args": {"rate": 0.5}}},
             "routes": [{"source": "breath", "path": "layers.base.swell.freq", "depth": 1.0}]}
    plain, moved = [payload(await client.call_tool("look_render", {"look": look, **FAST, "sheet": False}))["metrics"]
                    for look in (still, swept)]
    assert moved != plain
    assert plain["motion_energy"] == 0 < moved["motion_energy"], "only the route moves the stripes"


async def test_look_compare_takes_a_handle_and_a_look(client: Client) -> None:
    a = payload(await client.call_tool("look_render", {"look": COMET, **FAST, "sheet": False}))["handle"]
    faster = layered("comet", {"speed": 1.0})
    result = await client.call_tool("look_compare", {"a": a, "b": faster})
    assert payload(result) == lab.compare(a, faster).to_json()
    assert result.structured_content["look_diff"] == [{"path": "layers.base.comet.speed", "a": 0.4, "b": 1.0}]
    png(result.content[1])


async def test_look_vary_gives_n_candidates_and_their_numbered_sheet(
    client: Client, monkeypatch: pytest.MonkeyPatch,
) -> None:
    instant_looks(monkeypatch)
    result = await client.call_tool("look_vary", {"seed": 4, "n": 2, "map": "line:64"})
    made = lab.vary(None, 4, 2, map_spec="line:64", catalog=Catalog())
    assert payload(result) == made.to_json() and len(made.candidates) == 2
    assert [b.type for b in result.content] == ["text", "image"]
    rows = await client.read_resource(f"pewpew://render/{made.candidates[1].handle}/sheet.png")
    assert png(result.content[1]) != base64.b64decode(blob(rows.contents[0]))  # both rows, not one render
    like = payload(await client.call_tool("look_vary", {"look": COMET, "n": 1, "map": "line:64", "sheet": False,
                                                        "keep": ["layers.base.comet"]}))
    assert like["strength"] == 0.3 and like["keep"] == ["layers.base.comet"]
    refused = await client.call_tool("look_vary", {"keep": ["layers.base"]})
    assert refused.is_error and "give the look to vary" in text(refused.content[0])


async def test_engine_observe_reduces_a_capture_and_draws_it(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    hello = {"type": "hello", "n": 4, "total": 4, "positions": [[i / 3, 0.0, 0.0] for i in range(4)],
             "display_gamma": 2.2, "build": None}
    frames = tuple(Frame(k / 4, k, np.full((4, 3), 40 * k, np.uint8)) for k in range(5))
    seen = Capture(LOCAL, {"hello": hello}, frames)
    asked = []
    monkeypatch.setattr("pewpew.mcp_server.capture", lambda url, seconds: asked.append((url, seconds)) or seen)
    result = await client.call_tool("engine_observe", {"url": LOCAL, "seconds": 1})
    assert asked == [(LOCAL, 1.0)] and payload(result) == seen.observation().to_json()
    png(result.content[1])
    off = await client.call_tool("engine_observe", {"url": LOCAL, "sheet": False})
    assert len(off.content) == 1


async def test_fleet_status_lists_each_board_with_its_health(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    replies = {"10.0.0.2": {"ver": "16.0.1", "mac": "020000000001", "name": "pewpew-1", "live": False,
                            "leds": {"count": 60, "fps": 0}, "wifi": {"rssi": -82, "channel": 6},
                            "uptime": 40, "freeheap": 90000}}

    def fetch(host: str, timeout: float) -> dict:
        if host not in replies:
            raise OSError("no answer")
        return replies[host]

    monkeypatch.setattr(wled, "fetch_info", fetch)
    fleet = payload(await client.call_tool("fleet_status", {"subnet": "10.0.0.0/30"}))
    assert fleet == boards.survey(boards.parse_subnet("10.0.0.0/30")).to_json()
    (board,) = fleet["boards"]
    assert (board["address"], board["name"], board["rssi"], board["level"]) == ("10.0.0.2", "pewpew-1", -82, "bad")
    assert board["reasons"] == ["weak signal -82 dBm"] and board["fix"].startswith("Move the board")
    unknown_net = await client.call_tool("fleet_status", {})
    assert unknown_net.is_error and "give a subnet to scan" in text(unknown_net.content[0])


@contextlib.contextmanager
def engine():
    """An aura on a 4-pixel line that takes looks, behind a started preview."""
    rig = aura_rig(Solid, mapping=line(4), catalog=Catalog(), accept_looks=True)
    with preview_sink(line(4), control=rig.control) as sink, LoopThread(rig.calls):
        yield rig, f"ws://127.0.0.1:{sink.port}/"


async def test_engine_apply_and_set_dry_run_by_default_then_send_and_audit(client: Client, audit_log: Path) -> None:
    with engine() as (rig, url):
        dry = payload(await client.call_tool("engine_apply", {"url": url, "look": COMET}))
        assert dry["dry_run"] and dry["ok"] and dry["answers"] == [] and rig.deck.current == "solid"
        assert not audit_log.exists()
        sent = payload(await client.call_tool("engine_apply", {"url": url, "look": COMET, "dry_run": False}))
        assert sent["answers"] == [{"id": "1", "control": "look", "ok": True, "reason": None, "name": None}]
        assert rig.deck.current == "comet"
        knob = await client.call_tool("engine_set", {"url": url, "path": "layers.base.comet.speed", "value": 9,
                                                     "dry_run": False})
    assert "refused at layers.base.comet.speed" in text(knob.content[0])
    assert refusal(knob)["answers"][0]["ok"] is False
    records = [json.loads(line) for line in audit_log.read_text().splitlines()]
    assert [r["argv"][-1] for r in records] == ["engine_apply", "engine_set"]
    assert all(r["argv"][:-1] == ARGV for r in records)


# ---- failures that teach -------------------------------------------------------------


async def test_a_wrong_argument_gets_its_did_you_mean_and_the_corrected_call(client: Client) -> None:
    result = await client.call_tool("catalog_search", {"query": "fold", "kind": "cord"})
    assert result.is_error
    assert text(result.content[0]).splitlines() == [
        ("out-of-range at kind: unknown kind 'cord' (did you mean 'coord'?); kinds: op, pattern, blend, palette, "
        "kind, source, coord, color, combine, modulate, state, signal"),
        "  fix: set kind to 'coord'",
        'corrected call: catalog_search(query="fold", kind="coord")',
    ]
    refused = refusal(result)
    assert refused["ok"] is False and refused["problems"][0]["did_you_mean"] == "coord"
    stale = await client.call_tool("catalog_search", {"cursor": "999"})
    assert stale.is_error and "pass the next_cursor of the page before" in text(stale.content[0])


@pytest.mark.parametrize(("tool", "look", "says"), [
    ("look_check", SPED, [("unknown-key at layers.base.comet.sped: layers.base.comet: unknown param 'sped' "
                          "(did you mean 'speed'?); params: speed, tail"), "  fix: rename 'sped' to 'speed'"]),
    ("look_render", {"layers": [{"id": "base", "nodes": {"x": {"op": "kaleidd", "args": {}}}}]},
     ["  fix: set layers.base.x.op to 'kaleid'"]),
    ("look_render", layered("/tmp/x.py", node="x"),
     [("bad-ref at layers.base.x.pattern: layers.base.x: pattern '…' does not load: a look sent to an engine names "
      "its pattern by name, never by file")]),
    ("engine_apply", {"layers": [{"id": "base", "blend": "scren", "nodes": {}}]},
     ["  fix: set layers.base.blend to 'screen'"]),
])
async def test_a_look_with_problems_is_an_error_that_teaches_each_fix(
    client: Client, tool: str, look: dict, says: list[str],
) -> None:
    args = {"look": look, "url": LOCAL} if tool == "engine_apply" else {"look": look}
    result = await client.call_tool(tool, args)
    lines = text(result.content[0]).splitlines()
    assert set(says) <= set(lines) and lines[-1] == f"apply each fix and call {tool} again"
    assert refusal(result) == lab.Check(False, None, lab.check_look(look, catalog=Catalog()).problems).to_json()


@pytest.mark.parametrize(("tool", "args", "says"), [
    ("look_compare", {"a": "r1-00000000000000000000", "b": COMET}, "render again with the same look, map"),
    ("look_render", {"look": COMET, "map": "grid16"}, "expected auto, line:64, grid:16x16"),
    ("engine_observe", {"url": LOCAL, "seconds": 0.5}, "nothing answered at ws://127.0.0.1:9/"),
    ("engine_set", {"url": "ws://10.1.2.3:7447/", "path": "layers.base.comet.speed", "value": 0.4},
     "10.1.2.3 is not this machine"),
    ("look_render", {"look": COMET, "seconds": 0}, "greater than 0"),
    ("look_render", {"look": COMET, "maps": "line:64"}, "unknown argument 'maps' (did you mean 'map'?)"),
])
async def test_any_other_failure_is_an_error_that_says_what_to_do(
    client: Client, tool: str, args: dict, says: str,
) -> None:
    result = await client.call_tool(tool, args)
    assert result.is_error and says in text(result.content[0])


# ---- resources and prompts -----------------------------------------------------------


async def test_the_resources_list_and_read(client: Client) -> None:
    listed = {str(r.uri) for r in (await client.list_resources()).resources}
    looks = {f"pewpew://looks/{p.name.removesuffix('.look.json')}" for p in EXAMPLES.glob("*.look.json")}
    assert listed == {"pewpew://catalog", "pewpew://docs/authoring", "pewpew://docs/catalog", *looks}
    assert len(looks) >= 2
    templates = [t.uri_template for t in (await client.list_resource_templates()).resource_templates]
    assert templates == ["pewpew://catalog/{kind}/{id}", "pewpew://looks/{name}", "pewpew://docs/{topic}",
                         "pewpew://docs/authoring/{section}", "pewpew://render/{handle}/sheet.png"]

    async def read(uri: str) -> str:
        return text((await client.read_resource(uri)).contents[0])

    assert json.loads(await read("pewpew://catalog")) == search.index().to_json()
    assert json.loads(await read("pewpew://catalog/op/kaleid")) == lab.describe("op", "kaleid")
    assert await read("pewpew://docs/catalog") == (ROOT / "docs" / "reference" / "catalog.md").read_text()
    guide = (ROOT / "docs" / "authoring.md").read_text()
    assert await read("pewpew://docs/authoring") == guide
    layers = await read("pewpew://docs/authoring/9")
    assert layers.startswith("## 9. Layers\n") and "\n## 10." not in layers and layers in guide
    assert len(layers) < len(guide) / 4  # a section is what an agent reads, not the whole guide
    for uri in sorted(looks):
        assert lab.check_look(await read(uri)).ok


async def test_an_example_look_added_after_start_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pewpew.mcp_server.EXAMPLES", tmp_path)
    async with Client(build(0)) as fresh:
        (tmp_path / "dusk.look.json").write_text(json.dumps(COMET))
        assert json.loads(text((await fresh.read_resource("pewpew://looks/dusk")).contents[0])) == COMET


@pytest.mark.parametrize(("uri", "says"), [
    ("pewpew://catalog/op/kaleidd", "did you mean 'kaleid'?"),
    ("pewpew://catalog/ops/kaleid", "did you mean 'op'?"),
    ("pewpew://looks/mcp-tid", "did you mean 'mcp-tide'?"),
    ("pewpew://docs/autoring", "did you mean 'authoring'?"),
    ("pewpew://docs/authoring/99", "unknown section '99'; sections: 1, 2, 3"),
    ("pewpew://render/r1-00000000000000000000/sheet.png", "render again"),
])
async def test_a_resource_that_is_not_there_says_what_is(client: Client, uri: str, says: str) -> None:
    with pytest.raises(MCPError, match=f".*{says.replace('?', '[?]')}"):
        await client.read_resource(uri)


async def test_the_prompts_carry_their_arguments(client: Client) -> None:
    prompts = (await client.list_prompts()).prompts
    assert [(p.name, [a.name for a in p.arguments or []]) for p in prompts] == [
        ("design-look", ["brief"]), ("critique-pair", ["a", "b"]),
    ]
    design = await client.get_prompt("design-look", {"brief": "slow tide at dusk"})
    assert "slow tide at dusk" in text(design.messages[0].content)
    pair = await client.get_prompt("critique-pair", {"a": "r1-a", "b": "r1-b"})
    assert 'look_compare(a="r1-a", b="r1-b")' in text(pair.messages[0].content)


# ---- the extra and stdout ----------------------------------------------------------------


# What a new process loads with `import pewpew`, and what `mcp` says there
# without the extra.
NO_MCP_CODE = (
    "import sys\n"
    "import pewpew, pewpew.lab, pewpew.__main__\n"
    "print(sorted(m for m in sys.modules if m.partition('.')[0] in {'mcp', 'mcp_types', 'pydantic'}))\n"
    "sys.modules['mcp'] = None\n"
    "print(pewpew.__main__.main(['mcp']))\n"
)
# What a client sends the stdio server, in turn.
STDIO_REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "look_render", "arguments": {
        "look": COMET, **FAST, "sheet": False}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "look_check", "arguments": {
        "look": SPED}}},
]


def _read_to(stream: IO[str], answer_id: int, lines: list[str]) -> bool:
    """Read the lines of `stream` into `lines` up to the answer to
    `answer_id`; False when the stream ends first."""
    while line := stream.readline():
        lines.append(line)
        if json.loads(line).get("id") == answer_id:
            return True
    return False


def _stdio() -> tuple[list[str], int, str]:
    """`python -m pewpew mcp` sent `STDIO_REQUESTS`, each request's answer
    read before the next request goes: each line it wrote to stdout, its
    exit code and its stderr."""
    lines: list[str] = []
    with tempfile.TemporaryFile("w+") as log, subprocess.Popen(
        [sys.executable, "-m", "pewpew", "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True,
    ) as server:
        assert server.stdin is not None and server.stdout is not None
        killer = threading.Timer(20.0, server.kill)
        killer.start()
        try:
            for request in STDIO_REQUESTS:
                server.stdin.write(json.dumps(request) + "\n")
                server.stdin.flush()
                if "id" in request and not _read_to(server.stdout, request["id"], lines):
                    break  # stdout closed: the test shows stderr
            server.stdin.close()
            lines += server.stdout.read().splitlines()
            code = server.wait()
        finally:
            killer.cancel()
        log.seek(0)
        return lines, code, log.read()


# The new processes these tests read, run on the suite's process pool
# (conftest.py).
JOBS = {"no mcp": partial(run_python, NO_MCP_CODE), "stdio": _stdio}


def test_import_pewpew_loads_no_mcp_and_the_command_says_how_to_install_it(pooled: Pooled) -> None:
    done = pooled["no mcp"]
    assert done.stdout.splitlines() == ["[]", "2"]
    assert "install pewpew[agent]" in done.stderr


def test_the_stdio_server_writes_only_protocol_to_stdout(pooled: Pooled) -> None:
    lines, code, stderr = pooled["stdio"]
    messages = [json.loads(line) for line in lines]  # every line is one JSON-RPC message
    assert all(message["jsonrpc"] == "2.0" for message in messages) and code == 0, stderr
    answers = {message.get("id"): message for message in messages}
    assert {1, 2, 3, 4} <= answers.keys(), f"the server closed stdout: {stderr}"
    assert [t["name"] for t in answers[2]["result"]["tools"]] == TIER0
    assert answers[3]["result"]["structuredContent"]["handle"].startswith("r1-")
    assert answers[4]["result"]["isError"] is True and "structuredContent" not in answers[4]["result"]
