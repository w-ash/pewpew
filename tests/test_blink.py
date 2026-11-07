"""Blink-to-identify: the override, its place in the loop, and its request."""

from __future__ import annotations

import json

import numpy as np
import pytest

from fakes import FakeTime, aura_rig, bar, next_text, room, serving
from pewpew.aura.control import REQUESTS
from pewpew.aura.master import Master
from pewpew.pace import PacedLoop
from pewpew.pattern import Pattern
from pewpew.render import Renderer
from pewpew.room.blink import DURATION, RATE, Blink
from pewpew.room.map import compile_room

pytestmark = pytest.mark.usefixtures("fake_ops")

# Three 8-pixel bars a, b, c, chained on one output.
ROOM = compile_room(room(*(
    bar(fid, pixels=8, chain=i + 1, start=[0.0, float(i)], end=[1.0, float(i)]) for i, fid in enumerate("abc")
)))
FPS = 60.0


def lit(blink: Blink) -> list[str]:
    """The fixtures the next frame lights white. Starts the blink's clock,
    as a frame does."""
    frame = blink.apply(0.0, np.zeros((ROOM.n, 3), dtype=np.float32))
    return [f.id for f in ROOM.fixtures if np.all(frame[f.first : f.first + f.pixels] == 1.0)]


def frames(blink: Blink, seconds: float, start: float = 0.0):
    """Apply the blink to a mid-grey frame at each 60 fps slot; returns the
    outputs and the input frame."""
    grey = np.full((ROOM.n, 3), 0.25, dtype=np.float32)
    grey.setflags(write=False)  # a write into the renderer's frame would raise
    out = [blink.apply(start + k / FPS, grey) for k in range(int(seconds * FPS))]
    return out, grey


def test_only_the_named_fixtures_pixels_flash_white_and_off():
    blink = Blink(ROOM)
    blink.start("b")
    out, grey = frames(blink, 1.0)
    b = slice(8, 16)
    assert np.all(out[0][b] == 1.0)  # on from the first frame
    assert np.all(out[int(0.3 * FPS)][b] == 0.0)  # off in the second half-period
    for frame in out:
        assert np.array_equal(frame[:8], grey[:8]) and np.array_equal(frame[16:], grey[16:])
    assert np.all(grey == 0.25)  # never written


def test_the_rate_stays_under_three_hertz():
    blink = Blink(ROOM)
    blink.start("a")
    out, _ = frames(blink, DURATION)
    on = np.array([f[0, 0] == 1.0 for f in out])
    onsets = int(on[0]) + int(np.count_nonzero(on[1:] & ~on[:-1]))
    assert onsets / DURATION == pytest.approx(RATE) and RATE <= 3.0


def test_it_is_keyed_on_engine_time_and_deterministic():
    one, two = Blink(ROOM), Blink(ROOM)
    one.start("c")
    two.start("c")
    a, _ = frames(one, 2.0, start=10.0)
    b, _ = frames(two, 2.0, start=10.0)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    # The same blink started at another engine time is the same sequence.
    three = Blink(ROOM)
    three.start("c")
    c, _ = frames(three, 2.0, start=3.5)
    assert all(np.array_equal(x, y) for x, y in zip(a, c))


def test_it_ends_after_its_duration_and_hands_back_the_frame_itself():
    blink = Blink(ROOM)
    blink.start("a")
    out, grey = frames(blink, DURATION + 0.5)
    last_blinking = int(DURATION * FPS) - 1
    assert out[last_blinking] is not grey
    assert all(f is grey for f in out[last_blinking + 1 :])


def test_an_unknown_fixture_is_refused_by_name_and_never_starts():
    blink = Blink(ROOM)
    assert blink.check("zz") == "unknown fixture 'zz'; fixtures: a, b, c"
    assert blink.check(3) == "blink takes a fixture id, got 3"
    assert blink.check("a") is None
    rig = aura_rig(blink=blink)
    assert rig.control.request({"type": "blink", "fixture": "zz"}) is not None
    rig.calls.drain()
    assert lit(blink) == []  # nothing refused reached the loop
    assert rig.control.request({"type": "blink", "fixture": "b"}) is None and lit(blink) == []
    rig.calls.drain()  # the loop thread starts it
    assert lit(blink) == ["b"]


class Grey(Pattern):
    def render(self, x, y, z, index):
        return np.full((len(x), 3), 0.25, np.float32)


def test_the_loop_applies_it_before_the_master_and_leaves_the_render_alone():
    renderer = Renderer(Grey(), ROOM.mapping)
    master = Master()
    master.set(0.5)
    blink = Blink(ROOM)
    blink.start("a")
    seen = []
    ft = FakeTime()
    loop = PacedLoop(
        renderer, fps=FPS, after=[blink.apply, master.apply], on_frame=[lambda t, f: seen.append(f)],
        now=ft.now, sleep=ft.sleep,
    )
    loop.run(frames=2)
    assert np.allclose(seen[0][:8], 0.5)  # white, then the master's half
    assert np.allclose(seen[0][8:], 0.125)
    assert np.allclose(renderer.advance_to(renderer.t + 1 / FPS), 0.25)  # the pattern's own frames are grey


def test_a_blink_names_its_fixture_so_an_id_is_only_ever_a_request_id():
    """Any message may carry an `id`, which its answer carries back
    (ADR-020 amendment "capabilities"): the page's blink sends none and
    gets no answer, and a client's `id` never names a fixture."""
    assert [control for control, fields in REQUESTS.items() if "id" in dict(fields)] == []
    blink = Blink(ROOM)
    rig = aura_rig(blink=blink)
    with serving(rig.control, rig.calls) as (_, ws, _):
        ws.send(json.dumps({"type": "blink", "fixture": "b", "id": "req-1"}))
        ws.send(json.dumps({"type": "blink", "fixture": "a"}))
        ws.send(json.dumps({"type": "blink", "fixture": "zz"}))
        answers = []
        while len(answers) < 2:
            if (reply := next_text(ws))["type"] in ("ack", "refused"):
                answers.append(reply)
    assert answers == [
        {"type": "ack", "id": "req-1", "control": "blink"},
        {"type": "refused", "control": "blink", "name": None, "id": None,
         "reason": "unknown fixture 'zz'; fixtures: a, b, c"},
    ]
