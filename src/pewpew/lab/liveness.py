"""Liveness: does every knob of a look change what it shows?

The method of tests/test_param_liveness.py, applied to a whole look: for
each knob of each node of each enabled layer's program (an op's args),
and of each of the look's signals, render the look
twice with the knob at each end of a probe pair (pewpew.params.probes),
every other knob as the look sets it (a color part's other parts too),
and call the knob live when the two sequences, as a sink shows them,
differ by more than `LIVENESS_RMS`.

Each render runs `LIVENESS_WARMUP` frames, then the `LIVENESS_FRAMES`
frames it compares, at `LIVENESS_FPS`: 1 s, of which the last 0.5 s
counts. The first half second lets what builds up fill (a trail, a
feedback field, a simulation) and a slow signal move off where it starts,
so a knob that shows only once the look has run is live, and a knob that
never shows is dead. At the 30 fps `verify looks` renders at, that is 30
frames a render, as many as the cold half second at 60 fps it was before.

A probe that reads dead in that second is looked at again, longer
(`patient`): both ends rendered for `PATIENT_SECONDS` (8 s), the last
half compared. A slow knob, such as a `walk` at 0.02 Hz, a long `decay`,
a `diffuse` bleed or a slow shell, shows there and is live; a knob that
changes nothing changes nothing in 8 s either, so it is still dead. Only
a would-be failure costs the longer look, and a probe says how long it
was looked at (`seconds`). `fx vary` looks only once: it wants each knob
to show at once, with room to spare.

A probe that cannot run is not live and says why: a palette with no
preset to move to, or a look that does not run with the knob at one end
of its range. A probe the map's shape cannot show is not run, whatever
the look (`Op.shows`, as each op declares): an arg that acts in a plane,
on a strip; an arg that acts along an axis the map does not spread along
(`lissajous`'s `b` on a strip along x, `mirror`'s `centre` when it folds
z on a panel), at either end; and a choice of axis or plane whose two
values read the map alike (`plane` from `auto` to the plane `auto` takes,
`axis` from `u` to the one axis a strip spreads along).

A choice is one knob, live when any one of its options changes the
picture; an option that shows as the first does is then not a failure,
but `alike`, as a float is probed at its two ends and never asked to
change the picture at every value between. Options coincide for reasons
an op cannot see: `osc(6).spherical()` reads only the distance, which
`plane` xy and xz both put on x; `blend`'s `stencil` is `normal` where
the second input is never 0, as a noise never is; `min` is the first
input where it is always the darker. A choice none of whose options
changes anything is still dead.

A layer's mix (opacity, blend, enabled) is not probed: what it does
depends on the layers below, and the bottom layer's blend over nothing
shows the same in every mode. A disabled layer's knobs are not probed:
the layer does not run.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, replace
from functools import partial
from typing import Any

import numpy as np

from pewpew.compose import layer_address
from pewpew.compose.controls import signal_address
from pewpew.fx.graph import Graph, Node
from pewpew.fx.ops import OPS
from pewpew.lab.check import Ready
from pewpew.lab.geometry import Geometry
from pewpew.lab.rendering import play
from pewpew.metrics import LIVENESS_RMS, rms
from pewpew.params import ParamSet
from pewpew.params.probes import probes
from pewpew.problems import Refused
from pewpew.result import Result
from pewpew.sinks.sink import sanitize

LIVENESS_FPS = 30.0
LIVENESS_WARMUP = 15  # frames rendered before the ones compared
LIVENESS_FRAMES = 15  # frames compared
# The second, longer look at a probe that reads dead in the first (`patient`).
PATIENT_SECONDS = 8.0
PATIENT_FRAMES = int(PATIENT_SECONDS * LIVENESS_FPS) // 2  # the last half, compared


@dataclass(frozen=True, slots=True)
class KnobProbe(Result):
    """One knob moved from `a` to `b` (JSON values): its path, with the
    part or option moved (`layers.base.tint.palette`), the RMS between
    the two renders, and whether that passes `LIVENESS_RMS`. A probe that
    cannot run is not live: `error` says why, and `rms` is None.
    `seconds` is how long each end rendered: 1, or PATIENT_SECONDS for a
    probe looked at again (module docstring)."""

    path: str
    a: Any
    b: Any
    rms: float | None
    live: bool
    error: str | None = None
    # Shows as the first option does, where another option of the same
    # choice changes the picture: live, by the knob (module docstring).
    alike: bool = False
    seconds: float = (LIVENESS_WARMUP + LIVENESS_FRAMES) / LIVENESS_FPS


def dead(probes: Iterable[KnobProbe]) -> tuple[str, ...]:
    """The paths of `probes` that ran and did not change the picture."""
    return tuple(probe.path for probe in probes if not probe.live and probe.error is None)


def unprobed(probes: Iterable[KnobProbe]) -> tuple[str, ...]:
    """Each probe of `probes` that could not run, as "<path>: <why>"."""
    return tuple(f"{probe.path}: {probe.error}" for probe in probes if probe.error is not None)


def probe_knobs(staged: Ready, geometry: Geometry, seed: int) -> tuple[KnobProbe, ...]:
    """Each probe of each knob of `staged` on `geometry`, the features
    seeded `seed` (module docstring), each that reads dead looked at
    again for PATIENT_SECONDS. A probe that cannot run says why; none
    raises."""
    return tuple(each_probe(staged, geometry, seed, patient=True))


def each_probe(staged: Ready, geometry: Geometry, seed: int, *, patient: bool = False) -> Iterator[KnobProbe]:
    """The probes `probe_knobs` gives, each rendered only when it is asked
    for, so a caller can stop at the first that fails; with `patient`,
    each that reads dead looked at again for PATIENT_SECONDS."""
    spans = np.ptp(geometry.mapping, axis=0).tolist()
    knobs: list[tuple[Node, str, Callable[[str, Any], Ready]]] = []
    for i, layer in enumerate(staged.look.layers):
        if layer.enabled:
            knobs += ((node, layer_address(layer.id, node.id), partial(_moved, staged, i, node.id))
                      for node in layer.program.graph)
    knobs += ((node, signal_address(node.id), partial(_signal_moved, staged, node.id))
              for node in staged.look.signals or ())
    for node, owner, moved in knobs:
        op = OPS[node.op]
        values = ParamSet(op, node.args).snapshot_json()
        for record in ParamSet(op).describe():
            name = record["name"]
            try:
                pairs = probes(record, values[name])
            except ValueError as exc:  # a palette with no preset to move to
                yield KnobProbe(f"{owner}.{name}", values[name], None, None, False, str(exc))
                continue
            shown = _renders(partial(moved, name), geometry, seed, LIVENESS_WARMUP, LIVENESS_FRAMES)
            ran = (_probe(shown, f"{owner}.{probe}", a, b)
                   for probe, a, b in pairs if op.shows(name, a, b, values, spans))
            frames = int(PATIENT_SECONDS * LIVENESS_FPS)
            longer = _renders(partial(moved, name), geometry, seed, frames - PATIENT_FRAMES, PATIENT_FRAMES)
            if record["kind"] == "choice":
                # One live option makes the knob live, so the longer look
                # is for a choice none of whose options shows at once.
                options = tuple(ran)
                if patient and not any(probe.live for probe in options):
                    options = tuple(_again(longer, probe) for probe in options)
                yield from _alike(options)
            elif patient:
                yield from (_again(longer, probe) for probe in ran)
            else:
                yield from ran


def _alike(ran: tuple[KnobProbe, ...]) -> tuple[KnobProbe, ...]:
    """The probes of one choice knob: when any is live, each that ran and
    did not change the picture is live and `alike`."""
    if not any(probe.live for probe in ran):
        return ran
    return tuple(replace(probe, live=True, alike=True) if not probe.live and probe.error is None else probe
                 for probe in ran)


def _again(longer: Callable[[Any], np.ndarray], probe: KnobProbe) -> KnobProbe:
    """`probe`, looked at again on `longer`'s renders when it ran and read
    dead (module docstring)."""
    if probe.live or probe.error is not None:
        return probe
    return replace(_probe(longer, probe.path, probe.a, probe.b), seconds=PATIENT_SECONDS)


def _renders(moved: Callable[[Any], Ready], geometry: Geometry, seed: int, warmup: int,
             compared: int) -> Callable[[Any], np.ndarray]:
    """The frames, as a sink shows them, of `moved(value)`, the look with
    one knob at `value`: `warmup` frames, then the `compared` frames
    given. Each value rendered once, so the probes of one knob that share
    an end (a palette's default, a choice's first option) share its
    render. Raises Refused."""
    seen: dict[str, np.ndarray] = {}

    def shown(value: Any) -> np.ndarray:
        key = json.dumps(value, sort_keys=True)
        if key not in seen:
            frames, _ = play(moved(value), geometry, warmup + compared, LIVENESS_FPS, seed)
            seen[key] = sanitize(frames[warmup:])
        return seen[key]

    return shown


def _probe(shown: Callable[[Any], np.ndarray], path: str, a: Any, b: Any) -> KnobProbe:
    """The knob `shown` renders moved from `a` to `b`: the probe at `path`."""
    ends = []
    for end in (a, b):
        try:
            ends.append(shown(end))
        except Refused as exc:
            return KnobProbe(path, a, b, None, False, f"the look does not run with it at {json.dumps(end)}: {exc}")
    low, high = ends
    change = rms(low, high)
    return KnobProbe(path, a, b, round(change, 6), change > LIVENESS_RMS)


def _moved(staged: Ready, i: int, nid: str, name: str, value: Any) -> Ready:
    """`staged` with knob `name` of node `nid` of layer `i` at `value`."""
    look = staged.look
    layer = look.layers[i]
    graph = Graph(tuple(_set(node, name, value) if node.id == nid else node for node in layer.program.graph))
    moved = replace(layer, program=replace(layer.program, graph=graph))
    return replace(staged, look=replace(look, layers=(*look.layers[:i], moved, *look.layers[i + 1 :])))


def _signal_moved(staged: Ready, sid: str, name: str, value: Any) -> Ready:
    """`staged` with knob `name` of signal `sid` at `value`."""
    look = staged.look
    assert look.signals is not None  # `sid` is one of them
    signals = Graph(tuple(_set(node, name, value) if node.id == sid else node for node in look.signals))
    return replace(staged, look=replace(look, signals=signals))


def _set(node: Node, name: str, value: Any) -> Node:
    """`node` with arg `name` at `value`."""
    return Node(node.id, node.op, {**node.args, name: value}, node.inputs)
