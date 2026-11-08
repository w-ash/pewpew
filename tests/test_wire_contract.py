"""The wire contract: `tests/goldens/wire.json` is what a real preview
sends, captured from a `PreviewSink` over an `AuraControl` on fakes, in a
run that takes looks and has a Gallery to publish to. The run starts in a
look with two signals, routes into a param and a color's part, and front
knobs, so the greeting carries them (`aura.stack`, the signals' knobs, and
the `mod` readout). Its rig file is an arrangement the page may edit, so
the greeting carries the `arrangement` and the rig's `report`, a fixed
`power` reading, and the capabilities `look`, `arrange`, `export` and
`publish`. It holds a new client's greeting, its `catalog` cut to two
cards (`CARDS`) and its report's `basis` to one fact,
then one example of each message whose fields the greeting leaves empty
(a held trigger, a refusal, a look and a layer refused with their ids, an
arrangement refused with its issues and one built on a stale file with the
current one, an ack, the `exported` share an `export` asks for, a render
error, a scan, the layout of a rig with a floor plan), and the controls a
client may send.
The page builds its test messages from it and checks every key against
its types (web/test/wire/wire.test.ts), so a renamed key fails both
suites.
`--regen-goldens` rewrites it; review the diff before committing."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from fakes import (
    FakeTime,
    LoopThread,
    arrangement,
    aura_rig,
    bar,
    ddp_sink,
    greet,
    layered,
    look,
    next_text,
    no_watch,
    preview_sink,
    restore,
    wait_until,
)
from params_zoo import ZOO
from pewpew.aura.book import Trigger
from pewpew.aura.control import REQUESTS
from pewpew.compose import Route
from pewpew.fx.graph import Graph, Node
from pewpew.health import HealthMonitor
from pewpew.mapping import line
from pewpew.pace import PaceStats
from pewpew.rig import load_catalog
from pewpew.rig.models import RigView
from pewpew.rig.runtime import compile_doc, plan_view, rig_view
from pewpew.room.live import RigLive
from pewpew.run import status_line
from pewpew.sinks.ddp import Board

GOLDEN = Path(__file__).parent / "goldens" / "wire.json"
PAGE_SOURCE = Path(__file__).resolve().parents[1] / "web" / "src"
# The hello's build stamp follows the page source; the golden holds this one.
BUILD = "0123456789abcdef"
# The layout's catalog digest follows every catalog entry; the golden holds this one.
DIGEST = "0" * 64
HOST, US = "192.168.1.50", "192.168.1.2"
GALLERY = "https://pewpew.fly.dev"
pytestmark = pytest.mark.usefixtures("fake_ops")
# A look whose one knob is out of its range, which the aura refuses.
REFUSED = layered("osc", {"freq": 99.0})
# The catalog cards the golden keeps: a source's and a coord op's, so an op
# added to the catalog does not change it.
CARDS = ("osc", "kaleid")
# The power reading the golden holds: the run's own follows the frame.
POWER = {"watts": 12.5, "uncapped_watts": 25.0}
REPLY = {
    "mac": "aabbccddeeff", "ver": "16.0.1", "live": True, "lip": US, "uptime": 3700, "freeheap": 120000,
    "leds": {"count": 320, "fps": 40}, "wifi": {"rssi": -55, "channel": 6},
}


def capture(folder: Path) -> dict:
    """Run the aura and record what one client is sent, as the golden holds it."""
    ddp, _, _ = ddp_sink([Board(HOST, 0, 320)], 320)
    stats, ft = PaceStats(), FakeTime()
    replies = {HOST: REPLY, "192.168.1.77": {**REPLY, "mac": "001122334455", "name": "WLED", "live": False}}
    monitor = HealthMonitor(
        ddp, stats=stats, target=60.0, fetch=lambda host, timeout: replies[host], sender=lambda host, port: US,
        now=ft.now, names=lambda: ["A"],
    )
    monitor.step()
    ddp.frames_sent, stats.ticks, ft.t = 40, 60, 1.0
    monitor.step()
    warm = replace(
        look(ZOO, node="zoo", fade=0.0, cycle=True),
        signals=Graph((Node("breath", "lfo", {"rate": 0.5}), Node("macro", "knob", {"value": 0.5}))),
        routes=(Route("breath", "layers.base.zoo.level", 0.2), Route("macro", "layers.base.zoo.color.h", 60.0)),
        front=("signals.macro.value", "layers.base.zoo.level"),
    )
    looks = {"warm": warm, "cool": look(ZOO, {"level": 0.2}, node="zoo", fade=0.0)}
    triggers = {"door": Trigger(look="cool", hold=8.0, debounce=0.0), "bell": Trigger()}
    rig = aura_rig(look(ZOO, node="zoo"), mapping=line(2), looks=looks, current="warm", triggers=triggers,
                   path=folder / "looks.json", boards=monitor, health=monitor.state, accept_looks=True,
                   gallery=GALLERY)
    assert restore(rig) is None
    rig.master.set(0.8)
    rig.frame(rig.clock.advance())
    status = status_line(("render", rig.fader), ("looks", rig.looks))
    lit = arrangement(bar("a", pixels=2), boards={"A": HOST})
    data = (json.dumps(lit, indent=2) + "\n").encode()
    (folder / "rig.arrangement.json").write_bytes(data)
    rig.control.layout = RigLive(
        folder / "rig.arrangement.json", compile_doc(lit, load_catalog()), data, rig.fader, rig.calls,
        ddp=None, argv=["run"], watch=no_watch, edits=True,
    )
    with preview_sink(line(2), control=rig.control, status=status, power=lambda: POWER) as sink:
        ws, by_type = greet(sink)
        greeting = list(by_type.values())
        with ws:
            def later(kind: str) -> dict:
                sink.send(rig.clock.t, rig.frame(rig.clock.advance()))
                while (message := next_text(ws))["type"] != kind:
                    pass
                return message

            rig.triggers.arm(True, "page")
            rig.triggers.submit("page", "door")
            held = later("aura")
            ws.send(json.dumps({"type": "set", "name": "layers.base.zoo.level", "value": 3}))
            refused = next_text(ws)
            with LoopThread(rig.calls):  # a look and a layer are checked on the loop thread
                ws.send(json.dumps({"type": "look", "id": 7, "look": REFUSED}))
                refused_look = next_text(ws)
                ws.send(json.dumps({"type": "add_layer", "id": 8, "layer": {"nodes": REFUSED["layers"][0]["nodes"]},
                                    "below": None}))
                layer = next_text(ws)
            broken = arrangement(bar("a", pixels=2), boards={"A": HOST})
            broken["wiring"]["chains"][0]["fixtures"].append("ghost")
            ws.send(json.dumps({"type": "arrange", "id": 9, "arrangement": broken,
                                "base": by_type["arrangement"]["base"]}))
            arranged = next_text(ws)
            ws.send(json.dumps({"type": "arrange", "id": 10, "arrangement": lit, "base": "0" * 64}))
            stale = next_text(ws)
            ws.send(json.dumps({"type": "blackout", "id": "b1", "on": False}))
            ack = next_text(ws)
            ws.send(json.dumps({"type": "export", "id": 11, "looks": ["cool"], "share": True}))
            exported = next_text(ws)
            rig.renderer().bound.render = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
            error = later("status")
            assert monitor.scan() is None
            wait_until(lambda: not monitor.state()["scan"]["running"])
            scan = later("health")
            plan = folder / "plan.png"
            plan.write_bytes(b"\x89PNG\r\n\x1a\n")
            doc = arrangement(
                bar("a", pixels=2), bar("b", pixels=2, start=[0.0, 1.0], end=[1.0, 1.0], input="end", chain=2),
                boards={"A": HOST},
            )
            doc["plan"] = {"image": "plan.png", "points": [[0, 0], [100, 0]], "meters": 1.0}
            bars = compile_doc(doc, load_catalog())
            sink.remap(bars.mapping, plan_view(bars), plan, rig_view(bars))
            sink.send(rig.clock.t, np.zeros((bars.n, 3), dtype=np.float32))
            layout = next_text(ws)
    greeting[0]["build"] = BUILD
    layout["rig"]["catalog_digest"] = DIGEST
    catalog = by_type["catalog"]
    catalog["cards"] = [card for card in catalog["cards"] if card["name"] in CARDS]
    report = by_type["report"]["report"]
    report["basis"] = report["basis"][:1]  # its sources' wording follows the catalog
    return {
        "greeting": greeting,
        "later": [held, refused, refused_look, layer, arranged, stale, ack, exported, error, scan, layout],
        "controls": {name: [field for field, _ in fields] for name, fields in REQUESTS.items()},
    }


def test_the_golden_is_the_live_wire(tmp_path: Path, regen_goldens: bool) -> None:
    live = capture(tmp_path)
    if regen_goldens:
        GOLDEN.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n")
    assert json.loads(GOLDEN.read_text()) == live, "run `uv run pytest --regen-goldens` and review the diff"


def test_the_golden_holds_every_server_message_and_the_greeting_in_order() -> None:
    golden = json.loads(GOLDEN.read_text())
    assert [m["type"] for m in golden["greeting"]] == [
        "hello", "status", "declare", "params", "mod", "aura", "health", "catalog", "power", "arrangement",
        "report",
    ]
    assert [m["type"] for m in golden["later"]] == [
        "aura", "refused", "refused", "refused", "refused", "refused", "ack", "exported", "status", "health", "layout",
    ]
    assert golden["later"][4]["control"] == "arrange" and golden["later"][4]["issues"]
    stale = golden["later"][5]
    assert stale["control"] == "arrange" and stale["base"] == golden["greeting"][-2]["base"]
    assert stale["arrangement"] == golden["greeting"][-2]["arrangement"]
    assert golden["greeting"][0]["capabilities"] == ["ack", "look", "arrange", "export", "publish"]
    exported = golden["later"][7]
    assert exported["id"] == 11 and exported["gallery"] == GALLERY and exported["file"]["format"] == "pewpew.share"
    assert all("host" not in c for c in exported["file"]["arrangement"]["controllers"])  # a share names no board


def test_the_golden_rig_is_a_rig_view():
    """The layout's rig, its plan served, is what web/src/rig/types.gen.ts describes."""
    rig = json.loads(GOLDEN.read_text())["later"][-1]["rig"]
    assert "url" in rig["plan"] and rig["fixtures"]
    assert RigView.model_validate(rig).model_dump(mode="json") == rig


def test_the_page_reads_the_capabilities_only_in_the_wire():
    """`hello.capabilities` says what this run or Gallery session allows
    (`arrange`, `export`, `publish`, `pause`, `gallery`): the store keeps
    them from the hello and answers what the page may show, so no other
    module reads them (ADR-020 amendment "capabilities")."""
    sources = PAGE_SOURCE.rglob("*.ts*")
    files = sorted(f for f in sources if f.suffix in {".ts", ".tsx"})
    assert len(files) > 10
    readers = [f.relative_to(PAGE_SOURCE).as_posix() for f in files if "capabilities" in f.read_text()]
    assert readers == ["wire/protocol.ts", "wire/store.ts"]
