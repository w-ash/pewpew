"""The wire contract: `tests/goldens/wire.json` is what a real preview
sends, captured from a `PreviewSink` over an `AuraControl` on fakes, in a
run that takes looks. The run starts in a look with two signals, routes
into a param and a color's part, and front knobs, so the greeting carries
them (`aura.stack`, the signals' knobs, and the `mod` readout). It holds a
new client's greeting, its `catalog` cut to two cards (`CARDS`), then one
example of each message whose fields the greeting leaves empty (a held
trigger, a refusal, a look and a layer refused with their ids, an ack, a
render error, a scan, a room layout), and the controls a client may send.
The page builds its test messages from it and checks every key against
its types (web/test/infra/wire.test.ts), so a renamed key fails both
suites.
`--regen-goldens` rewrites it; review the diff before committing."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from fakes import (
    FakeTime,
    LoopThread,
    aura_rig,
    bar,
    ddp_sink,
    greet,
    layered,
    look,
    next_text,
    preview_sink,
    restore,
    room,
    wait_until,
)
from params_zoo import Zoo
from pewpew import line
from pewpew.aura.book import Trigger
from pewpew.aura.control import REQUESTS
from pewpew.compose import Route
from pewpew.fx.graph import Graph, Node
from pewpew.health import HealthMonitor
from pewpew.load import Catalog
from pewpew.pace import PaceStats
from pewpew.patterns import ColorPlasma, Wave
from pewpew.room.map import compile_room
from pewpew.run import status_line
from pewpew.sinks.ddp import Board

GOLDEN = Path(__file__).parent / "goldens" / "wire.json"
PAGE_SOURCE = Path(__file__).resolve().parents[1] / "web" / "src"
# The hello's build stamp follows the page source; the golden holds this one.
BUILD = "0123456789abcdef"
HOST, US = "192.168.1.50", "192.168.1.2"
# A look that names its pattern by a file, which no message may do.
PATHED = layered("/tmp/x.py", node="x")
# The catalog cards the golden keeps: a pattern's and an op's, so an op added
# to the catalog does not change it.
CARDS = ("wave", "kaleid")
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
    catalog = Catalog({"colorplasma": ColorPlasma, "wave": Wave, "zoo": Zoo})
    warm = replace(
        look("zoo", fade=0.0, cycle=True),
        signals=Graph((Node("breath", "lfo", {"rate": 0.5}), Node("macro", "knob", {"value": 0.5}))),
        routes=(Route("breath", "layers.base.zoo.level", 0.2), Route("macro", "layers.base.zoo.color.h", 60.0)),
        front=("signals.macro.value", "layers.base.zoo.level"),
    )
    looks = {"warm": warm, "cool": look("zoo", {"level": 0.2}, fade=0.0)}
    triggers = {"door": Trigger(look="cool", hold=8.0, debounce=0.0), "bell": Trigger()}
    rig = aura_rig(Zoo, mapping=line(2), catalog=catalog, looks=looks, current="warm", triggers=triggers,
                   path=folder / "looks.json", boards=monitor, health=monitor.state, accept_looks=True)
    assert restore(rig) is None
    rig.master.set(0.8)
    rig.frame(rig.clock.advance())
    status = status_line(("render", rig.fader), ("looks", rig.looks))
    with preview_sink(line(2), control=rig.control, status=status) as sink:
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
                ws.send(json.dumps({"type": "look", "id": 7, "look": PATHED}))
                pathed = next_text(ws)
                ws.send(json.dumps({"type": "add_layer", "id": 8, "layer": {"nodes": PATHED["layers"][0]["nodes"]},
                                    "below": None}))
                layer = next_text(ws)
            ws.send(json.dumps({"type": "blackout", "id": "b1", "on": False}))
            ack = next_text(ws)
            rig.renderer().pattern.render = lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))
            error = later("status")
            assert monitor.scan() is None
            wait_until(lambda: not monitor.state()["scan"]["running"])
            scan = later("health")
            plan = folder / "plan.png"
            plan.write_bytes(b"\x89PNG\r\n\x1a\n")
            doc = room(bar("a", pixels=2), bar("b", pixels=2, start=[0.0, 1.0], end=[1.0, 1.0], input="end", chain=2),
                       boards={"A": HOST})
            doc["plan"] = {"image": "plan.png", "points": [[0, 0], [100, 0]], "meters": 1.0}
            layout_room = compile_room(doc)
            sink.remap(layout_room.mapping, layout_room.describe(), plan)
            sink.send(rig.clock.t, np.zeros((layout_room.n, 3), dtype=np.float32))
            layout = next_text(ws)
    greeting[0]["build"] = BUILD
    catalog = by_type["catalog"]
    catalog["cards"] = [card for card in catalog["cards"] if card["name"] in CARDS]
    return {
        "greeting": greeting,
        "later": [held, refused, pathed, layer, ack, error, scan, layout],
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
        "hello", "status", "declare", "params", "mod", "aura", "health", "catalog",
    ]
    assert [m["type"] for m in golden["later"]] == [
        "aura", "refused", "refused", "refused", "ack", "status", "health", "layout",
    ]


def test_the_page_never_reads_the_capabilities():
    """`hello.capabilities` is for clients outside the package: the page
    ships with its engine and never branches on it (ADR-020 amendment
    "capabilities"). Only the protocol's description names it."""
    studio = PAGE_SOURCE / "studio"  # the hosted studio's source, beside the page's
    sources = PAGE_SOURCE.rglob("*.ts*")
    files = sorted(f for f in sources if f.suffix in {".ts", ".tsx"} and not f.is_relative_to(studio))
    assert len(files) > 10
    readers = [f.relative_to(PAGE_SOURCE).as_posix() for f in files if "capabilities" in f.read_text()]
    assert readers == ["wire/protocol.ts"]
