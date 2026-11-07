"""Power, wiring and controller arithmetic, the compile report, and effect power.

Workstream 2 owns this module (docs/studio/contracts.md:13). Everything here
is pure: no I/O, no clock, no RNG.

- **Arithmetic.** Pixels per output, frame time, cable resistance, feed drop
  and fuse windows (docs/studio/domain-model.md:38-41, 217-243).
- **Ports.** Where a fixture takes data and power in, and where it passes
  them on.
- **Report.** `build_report` gives the `RigReport` of a wired rig, with the
  timing, hop, lead, feed, fuse and PSU issues of
  docs/studio/domain-model.md:302-321.
- **Effect power.** `effect_power_model` builds the `pewpew.power.EffectPower`
  current model, whose `watts` estimates what one frame draws.
- **Power cap.** The arrangement's `power` block caps every frame
  (`pewpew.power.PowerLimiter`). PSUs are sized for the most the RGB stream
  draws through each board's auto-white, under the cap. Without a cap, feeds,
  connectors and fuses are checked with every channel full; with one, they
  are checked at the capped current and every feed needs a fuse.
- **Boards.** A PSU that powers boards (`PsuPlacement.powers`) also carries
  each board's `power_w` through a buck converter (`BUCK_EFFICIENCY`). That
  draw is flat: the totals, the PSU loads and effect power count it, and the
  power cap never scales it.

Each feed's links, the cable runs from one fixture's `out` to the next one's
`in`, follow the data hop path and have the feed cable's conductors. That is
an assumption: the gauge of the pigtails and of Clen's extension cables is
not found (RES-018, the maintainer's private notes). On a
`tee` chain a link is the trunk run between two fixtures' inputs, with the
same assumed conductors; the gauge of Clen's T trunks is not found either.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike
from pydantic import BaseModel, ConfigDict

from pewpew.power import EffectPower, PowerCap
from pewpew.rig import expr
from pewpew.rig.catalog import Catalog
from pewpew.rig.models import (
    Arrangement,
    AutoWiring,
    Chain,
    ControllerPlacement,
    Feed,
    FixtureInstance,
    Instance,
    Issue,
    OutputSlice,
    PsuPlacement,
    Sourced,
    SourcedNum,
    Status,
    WiringPlan,
    value,
)

#: Copper resistivity, 1/(58 MS/m): IACS copper at 20 °C
#: (https://en.wikipedia.org/wiki/International_Annealed_Copper_Standard).
RHO_CU_OHM_M = 1.0 / 58e6

#: Class 2's power limit. The report gives it as a note and does not check
#: it, because the figure is not checked for DC
#: (https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html,
#: https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c).
CLASS2_VA = 100.0

#: Regular (ATO) blade fuse ratings, in amperes
#: (https://en.wikipedia.org/w/index.php?title=Automotive_fuse&oldid=1356410187#Blade_type).
FUSE_SERIES_A = (0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0)

ORIGIN = (0.0, 0.0, 0.0)

#: Comparisons of sums of floats against limits are inclusive to this much.
EPS = 1e-9

#: The efficiency of the buck converter through which a PSU powers a board.
BUCK_EFFICIENCY = SourcedNum(
    v=0.7,
    status="assumed",
    src=(
        "assumed for a lightly loaded buck: Mean Well gives the DDR-15G-5 84% at 24 V in and its rated 3 A "
        "(https://www.meanwell.com/Upload/PDF/DDR-15/DDR-15-SPEC.PDF); a board draws about 0.12 A of it, where "
        "the datasheet gives no figure"
    ),
)


# ---- arithmetic ------------------------------------------------------------------


def max_px(t_px_s: float, reset_s: float, fps: float) -> int:
    """The most pixels one output can send at `fps`: ⌊(1/fps − reset)/t_px⌋."""
    return max(0, math.floor((1.0 / fps - reset_s) / t_px_s + EPS))


def frame_s(pixels: int, t_px_s: float, reset_s: float) -> float:
    """The wire time of one frame: pixels × t_px + reset."""
    return pixels * t_px_s + reset_s


def loop_ohm_per_m(vplus_mm2: float, gnd_mm2: float) -> float:
    """The resistance of one metre of a V+ and GND pair: ρ/A_vplus + ρ/A_gnd."""
    return RHO_CU_OHM_M / (vplus_mm2 * 1e-6) + RHO_CU_OHM_M / (gnd_mm2 * 1e-6)


def has_conductors(catalog: Catalog, cable_id: str) -> bool:
    """True if the catalog cable has a V+ or a GND conductor."""
    c = catalog.get(cable_id, "cable").conductors_mm2
    return c.vplus is not None or c.gnd is not None


def cable_ohm_per_m(catalog: Catalog, cable_id: str) -> float:
    """A catalog cable's V+ and GND resistance per metre. A missing conductor
    takes the other one's area."""
    c = catalog.get(cable_id, "cable").conductors_mm2
    vplus, gnd = catalog.num(cable_id, c.vplus), catalog.num(cable_id, c.gnd)
    out, back = vplus or gnd, gnd or vplus
    if out is None or back is None:
        raise ValueError(f"{cable_id}: a cable needs a conductor area")
    return loop_ohm_per_m(out, back)


def feed_drop_v(currents: Sequence[float], r_feed_ohm: float, r_link_ohms: Sequence[float]) -> float:
    """The voltage drop at the input of a feed's last fixture.

    `I_seg·R_feed + Σ I_down·R_link` (docs/studio/domain-model.md:232). The
    feed cable carries every fixture's current. Link k, into fixture k,
    carries the current of fixture k and of every fixture after it. A link's
    resistance includes the pass-through of the fixture before it.
    """
    downstream = np.cumsum(np.asarray(currents, dtype=np.float64)[::-1])[::-1]
    return float(downstream[0] * r_feed_ohm + np.dot(downstream[1:], np.asarray(r_link_ohms, dtype=np.float64)))


def board_w(psu: PsuPlacement, profiles: Mapping[str, str], catalog: Catalog) -> tuple[float, list[str]]:
    """The watts that the boards `psu` powers draw from it, their `power_w`
    over `BUCK_EFFICIENCY`, and the ids of the boards whose profile gives no
    `power_w`.

    `profiles` maps a controller id to its profile. A board that is not in
    it adds nothing.
    """
    watts, unknown = 0.0, []
    for cid in psu.powers:
        profile = profiles.get(cid)
        if profile is None:
            continue
        controller = catalog.get(profile, "controller")
        if controller.power_w is None:
            unknown.append(cid)
        else:
            watts += catalog.need(controller.id, controller.power_w)
    return watts / value(BUCK_EFFICIENCY), unknown


def boards_w(
    psus: Sequence[PsuPlacement], controllers: Sequence[ControllerPlacement], catalog: Catalog
) -> dict[str, float]:
    """`board_w` of each PSU that powers a board with a `power_w`, by PSU id."""
    profiles = {c.id: c.profile for c in controllers}
    out = {p.id: board_w(p, profiles, catalog)[0] for p in psus}
    return {k: w for k, w in out.items() if w > 0.0}


def board_load_a(psu: PsuPlacement, profiles: Mapping[str, str], catalog: Catalog) -> float:
    """`board_w` as a current at the PSU's `v_out`."""
    watts = board_w(psu, profiles, catalog)[0]
    return watts / catalog.need(psu.type, catalog.get(psu.type, "psu").v_out) if watts else 0.0


def fuse_window(current_a: float, rated_a: float | None, load_fraction: float) -> tuple[float, float | None]:
    """`[I/load_fraction, rated_a]`: the fuse loads to at most `load_fraction`
    and protects the connector (docs/studio/domain-model.md:232)."""
    return current_a / load_fraction, rated_a


def pick_fuse(current_a: float, rated_a: float | None, load_fraction: float) -> float | None:
    """The smallest blade fuse in the fuse window, or None if none fits."""
    lo, hi = fuse_window(current_a, rated_a, load_fraction)
    for rating in FUSE_SERIES_A:
        if rating >= lo - EPS and (hi is None or rating <= hi + EPS):
            return rating
    return None


#: The RGBW channel sum of an RGB colour is R + G + B + a·min(R, G, B) +
#: b·max(R, G, B), with these (a, b) for each of WLED's auto-white modes
#: (https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125).
#: `manual` derives no W. `brighter` adds W = min. `accurate` adds W = min
#: and takes min from each of R, G and B. `dual` acts as `brighter` on a
#: frame with no W, which is every RGB frame. `max` adds W = max.
AUTO_WHITE_TERMS: dict[str | None, tuple[float, float]] = {
    None: (0.0, 0.0),
    "manual": (0.0, 0.0),
    "brighter": (1.0, 0.0),
    "accurate": (-2.0, 0.0),
    "dual": (1.0, 0.0),
    "max": (0.0, 1.0),
}

#: The auto-white mode of an RGBW fixture that is on no controller.
UNWIRED_AUTO_WHITE = "accurate"


def rgb_reach(channels: str, mode: str | None) -> float:
    """The largest channel sum, in full channels, that an RGB frame gives a
    pixel with `channels` through the auto-white `mode`.

    Where the order of R, G and B is fixed the sum is linear in them, so its
    largest value is at a corner of the RGB cube, with k of them full. A
    pixel without W reaches 3. An RGBW pixel reaches 3 under `manual`, 4
    under `brighter`, `dual` and `max`, and 2 under `accurate`: yellow, two
    channels full and one off, has W = 0.
    """
    a, b = AUTO_WHITE_TERMS[mode] if "W" in channels else (0.0, 0.0)
    return max(k + (a if k == 3 else 0.0) + (b if k else 0.0) for k in range(4))


def rgb_share(catalog: Catalog, type_id: str, mode: str | None) -> float:
    """The share of `max_w` that an RGB frame draws at most from the fixture:
    its reach over its channel count, as `max_w` splits evenly across the
    channels. A `flat` fixture draws all of it."""
    if is_flat(catalog, type_id):
        return 1.0
    channels = catalog.spec(type_id).channels
    return rgb_reach(channels, mode) / len(channels)


# ---- ports -----------------------------------------------------------------------


@dataclass(frozen=True)
class Port:
    """A fixture's data and power connection: world position, pigtail, connector."""

    at: np.ndarray
    pigtail_m: float
    connector: str | None
    anchor: str | None


# Each port is the first of these anchors the fixture type has.
_PORT_ANCHORS = {"in": ("in", "end_a"), "out": ("out", "end_b")}


def ports(inst: Instance, catalog: Catalog) -> tuple[Port, Port]:
    """The fixture's data-in and data-out ports.

    Each is the `in` or `out` anchor, else `end_a` or `end_b`, else the
    fixture's origin with no pigtail and no connector.
    """
    ft = catalog.get(inst.type_id, "fixture_type")
    out = []
    for role in ("in", "out"):
        name = next((n for n in _PORT_ANCHORS[role] if n in ft.anchors), None)
        if name is None:
            out.append(Port(inst.matrix[:3, 3].copy(), 0.0, None, None))
            continue
        anchor = ft.anchors[name]
        at = inst.matrix @ np.append(catalog.vec(ft.id, anchor.at), 1.0)
        pigtail = catalog.need(ft.id, anchor.pigtail_m) if anchor.pigtail_m is not None else 0.0
        out.append(Port(at[:3], pigtail, anchor.connector, name))
    return out[0], out[1]


def run_m(a: ArrayLike, b: ArrayLike, slack: float) -> float:
    """A cable run between two points: the straight distance × slack."""
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))) * slack


def link_m(out: Port, nxt: Port, slack: float) -> float:
    """A data hop: `|out − in| × slack + pigtails` (docs/studio/domain-model.md:221)."""
    return run_m(out.at, nxt.at, slack) + out.pigtail_m + nxt.pigtail_m


def tee_link_m(ports_a: tuple[Port, Port], nxt: Port, slack: float) -> float:
    """A data hop between two fixtures on T drops: `|in_a − in_b| × slack`,
    both pigtails, and fixture a's return from its last pixel to its input,
    taken as `|out_a − in_a|`."""
    a_in, a_out = ports_a
    return link_m(a_in, nxt, slack) + run_m(a_in.at, a_out.at, 1.0)


def lead_m(controller_at: ArrayLike, first: Port, slack: float) -> float:
    """The controller's data lead to its first fixture: `|in − controller| × slack + pigtail`."""
    return run_m(controller_at, first.at, slack) + first.pigtail_m


@dataclass(frozen=True)
class FeedLoad:
    """What one feed carries and loses: `current_a` with every channel full,
    `capped_a` the RGB worst case under the power cap (`Site`)."""

    current_a: float
    capped_a: float
    connector_a: float | None
    v_nominal: float
    loop_ohm: float
    link_ohms: tuple[float, ...]
    drop_v: float

    @property
    def drop_fraction(self) -> float:
        return self.drop_v / self.v_nominal


NO_CAP = PowerCap()


class Site:
    """The electrical numbers of a rig's instances, cached by instance id.

    A fixture has three currents:

    - `current_a`, every channel full: the drop, and the feed checks
      without a cap.
    - `rgb_worst_a`, the most an RGB frame draws through the auto-white of
      the firmware that drives it. `modes` maps a fixture id to that mode;
      a fixture not in it is unwired.
    - `capped_a`, that under `cap`, × `scale`: the PSU loads, and the feed
      checks when `capping`.

    `board_w` is what the boards the PSUs power draw (`boards_w`). It is a
    flat load in every total, and the cap never scales it.
    """

    def __init__(
        self,
        instances: Sequence[Instance],
        catalog: Catalog,
        cap: PowerCap = NO_CAP,
        modes: Mapping[str, str | None] | None = None,
        board_w: float = 0.0,
    ) -> None:
        self.catalog = catalog
        self.by_id = {i.id: i for i in instances}
        self._ports: dict[str, tuple[Port, Port]] = {}
        modes = modes or {}
        self.share = {i.id: rgb_share(catalog, i.type_id, modes.get(i.id, UNWIRED_AUTO_WHITE)) for i in instances}
        draws = [(is_flat(catalog, i.type_id), catalog.spec(i.type_id).max_w, self.share[i.id]) for i in instances]
        flat = math.fsum(w for fixed, w, _ in draws if fixed) + board_w
        variable = math.fsum(w * share for fixed, w, share in draws if not fixed)
        self.cap = cap
        self.capping = cap.caps
        self.board_w = board_w
        self.scale = cap.scale(variable, flat)
        self.worst_w = math.fsum(w for _, w, _ in draws) + board_w
        self.rgb_worst_w = flat + variable
        self.capped_w = cap.watts(variable, flat)

    def ports(self, fid: str) -> tuple[Port, Port]:
        if fid not in self._ports:
            self._ports[fid] = ports(self.by_id[fid], self.catalog)
        return self._ports[fid]

    def current_a(self, fid: str) -> float:
        """The fixture's current with every channel full."""
        return self.catalog.spec(self.by_id[fid].type_id).current_a

    def rgb_worst_a(self, fid: str) -> float:
        """The most current an RGB frame draws from the fixture."""
        return self.current_a(fid) * self.share[fid]

    def capped_a(self, fid: str) -> float:
        """`rgb_worst_a` under the cap. A `flat` fixture draws its full current."""
        current = self.rgb_worst_a(fid)
        return current if is_flat(self.catalog, self.by_id[fid].type_id) else current * self.scale

    def check_a(self, load: FeedLoad) -> float:
        """The current the feed checks take: capped under a cap, else every channel full."""
        return load.capped_a if self.capping else load.current_a

    def connector_a(self, fid: str) -> float | None:
        """The rating of the connector at the fixture's data-in port."""
        connector = self.ports(fid)[0].connector
        if connector is None:
            return None
        return self.catalog.num(connector, self.catalog.get(connector, "connector").rated_a)

    def passthrough_ohm(self, fid: str) -> float:
        """The fixture's resistance from its power in to its power out, or 0 if not given."""
        type_id = self.by_id[fid].type_id
        through = self.catalog.get(type_id, "fixture_type").power.passthrough_ohm
        return 0.0 if through is None else self.catalog.need(type_id, through)

    def link_ohm(self, a: str, b: str, per_m: float, slack: float, tee: bool = False) -> float:
        """The resistance from `a`'s power in to `b`'s: `a`'s pass-through and
        the link cable, or on T drops (`tee`) the trunk run between their inputs."""
        if tee:
            return run_m(self.ports(a)[0].at, self.ports(b)[0].at, slack) * per_m
        return self.passthrough_ohm(a) + link_m(self.ports(a)[1], self.ports(b)[0], slack) * per_m

    def feed(self, fids: Sequence[str], cable_id: str, length_m: float, slack: float, tee: bool = False) -> FeedLoad:
        """The load of a feed into `fids`, in data order, over `length_m` of
        `cable_id`. `tee` puts the fixtures on T drops (`Chain.tee`)."""
        per_m = cable_ohm_per_m(self.catalog, cable_id)
        currents = [self.current_a(f) for f in fids]
        links = tuple(self.link_ohm(a, b, per_m, slack, tee) for a, b in pairwise(fids))
        ratings = [r for r in (self.connector_a(f) for f in fids) if r is not None]
        r_feed = length_m * per_m
        return FeedLoad(
            current_a=sum(currents),
            capped_a=sum(self.capped_a(f) for f in fids),
            connector_a=min(ratings) if ratings else None,
            v_nominal=self.catalog.spec(self.by_id[fids[0]].type_id).v_nominal,
            loop_ohm=r_feed,
            link_ohms=links,
            drop_v=feed_drop_v(currents, r_feed, links),
        )


# ---- effect power ----------------------------------------------------------------


def is_flat(catalog: Catalog, type_id: str) -> bool:
    """True if the fixture type draws its `max_w` whatever it shows."""
    return value(catalog.get(type_id, "fixture_type").power.model_fact) == "flat"


def auto_white_modes(
    chains: Sequence[Chain], controllers: Sequence[ControllerPlacement], catalog: Catalog
) -> dict[str, str | None]:
    """The auto-white mode of the firmware that drives each chained fixture."""
    profiles = {c.id: c.profile for c in controllers}
    return {fid: _auto_white(chain.controller, profiles, catalog) for chain in chains for fid in chain.fixtures}


def supplies_of(plan: WiringPlan) -> dict[str, str]:
    """The PSU id that feeds each fed fixture. A fixture in two feeds takes the first."""
    chains = {c.id: c for c in plan.chains}
    out: dict[str, str] = {}
    for feed in plan.feeds:
        for fid in chains[feed.chain].fixtures[feed.first : feed.first + feed.count]:
            out.setdefault(fid, feed.psu)
    return out


def effect_power_model(
    fixtures: Sequence[FixtureInstance],
    controllers: Sequence[ControllerPlacement],
    catalog: Catalog,
    supplies: Mapping[str, str] | None = None,
    boards: Mapping[str, float] | None = None,
) -> EffectPower:
    """The `EffectPower` of compiled fixtures, from each type's `max_w` and
    `power.model`, the auto-white of each fixture's controller, and the PSU
    in `supplies` that feeds it.

    `channel_w` is the fixture's `max_w` over its pixel and channel count.
    `min_term_w` and `max_term_w` are `channel_w` × the `AUTO_WHITE_TERMS`
    of the pixel's firmware, or 0 on a pixel with no W. A group's `worst_w`
    is `max_w` × `rgb_share` over its fixtures. `boards` maps a PSU id to
    the watts of the boards it powers (`boards_w`), which go into its
    `flat_w`. The supply groups are the PSU ids in sorted order, then the
    fixtures on no feed.
    """
    supplies = supplies or {}
    boards = boards or {}
    profiles = {c.id: c.profile for c in controllers}
    groups = {psu: k for k, psu in enumerate(sorted(set(supplies.values()) | set(boards)))}
    unfed = len(groups)
    n = sum(f.pixel_count for f in fixtures)
    channel_w, min_term_w, max_term_w = np.zeros(n), np.zeros(n), np.zeros(n)
    supply_of = np.full(n, unfed, dtype=np.intp)
    flat_w, worst_w = np.zeros(unfed + 1), np.zeros(unfed + 1)
    for psu, watts in boards.items():
        flat_w[groups[psu]] += watts
    for f in fixtures:
        spec = catalog.spec(f.type_id)
        rows = slice(f.pixel_start, f.pixel_start + f.pixel_count)
        fed_by = supplies.get(f.id)
        g = unfed if fed_by is None else groups.get(fed_by, unfed)
        supply_of[rows] = g
        if is_flat(catalog, f.type_id):
            flat_w[g] += spec.max_w
            continue
        mode = _auto_white(f.controller, profiles, catalog)
        worst_w[g] += spec.max_w * rgb_share(catalog, f.type_id, mode)
        w = spec.max_w / (spec.count * len(spec.channels))
        channel_w[rows] = w
        if "W" in spec.channels:
            a, b = AUTO_WHITE_TERMS[mode]
            min_term_w[rows], max_term_w[rows] = a * w, b * w
    for array in (channel_w, min_term_w, max_term_w, supply_of, flat_w, worst_w):
        array.setflags(write=False)
    return EffectPower(
        channel_w=channel_w,
        min_term_w=min_term_w,
        max_term_w=max_term_w,
        supply_of=supply_of,
        flat_w=flat_w,
        worst_w=worst_w,
    )


def _auto_white(controller: str | None, profiles: dict[str, str], catalog: Catalog) -> str | None:
    if controller is None:
        return UNWIRED_AUTO_WHITE
    firmware = catalog.get(profiles[controller], "controller").firmware
    return catalog.get(firmware, "firmware").ingest.auto_white


# ---- report shapes ---------------------------------------------------------------


class _Report(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Totals(_Report):
    """The rig's draw at the nominal voltage.

    `worst_w` and `worst_a` have every channel of every fixture full.
    `rgb_worst_w` and `rgb_worst_a` are the most the RGB stream draws
    through each board's auto-white. `capped_w` and `capped_a` are that
    under the power cap: what the PSUs are sized for. Each includes the
    boards the PSUs power (`PsuReport.board_a`), whatever the frame.
    """

    fixtures: int
    pixels: int
    worst_w: float
    worst_a: float
    rgb_worst_w: float
    rgb_worst_a: float
    capped_w: float
    capped_a: float
    controllers: int
    psus: int
    feeds: int


class ControllerReport(_Report):
    id: str
    profile: str
    derived: bool
    outputs: int
    outputs_used: int
    pixels: int


class OutputReport(_Report):
    """One output: its pixels and frame time, the frame rate the wire allows,
    and `fps`, the rate it shows: at most the firmware's `min_frame_interval_s`."""

    controller: str
    output: str
    chain: str
    pixels: int
    led_type: int | None
    led_label: str | None
    frame_s: float
    wire_fps: float
    fps: float


class HopReport(_Report):
    """One data cable: a controller's `lead` to a chain, or a `link` between fixtures.

    `run_m` is the straight distance × slack; `path_m` adds the pigtails. On a
    `tee` chain a link runs from input to input along the trunk, and `path_m`
    also adds the source fixture's return to its input (`tee_link_m`).
    """

    chain: str
    kind: Literal["lead", "link"]
    source: str
    target: str
    run_m: float
    path_m: float


class FeedReport(_Report):
    """One feed. `loop_ohm` is its cable's V+ and GND; `drop_v` is at its last fixture.

    `current_a` has every channel full; the drop uses it. `capped_a` is the
    RGB worst case under the power cap; the PSU loads use it. The connector
    check and `fuse_window_a` take `capped_a` under a cap, else `current_a`.
    `connector_a` is the least rating of the fixtures' input connectors and
    the PSU's output connector.
    """

    id: str
    psu: str
    chain: str
    fixtures: list[str]
    cable: str
    length_m: float
    current_a: float
    capped_a: float
    connector_a: float | None
    fuse_a: float | None
    fuse_window_a: tuple[float, float | None]
    loop_ohm: float
    drop_v: float
    drop_fraction: float
    va: float
    note: str | None = None


class PsuReport(_Report):
    """One PSU. `current_a`, `load_fraction` and `watts` are its load from the
    RGB stream under the power cap; `worst_a` is its load with every channel full.
    Both include `board_a`, what the boards it `powers` draw through their buck."""

    id: str
    type: str
    derived: bool
    v_out: float
    i_max_a: float
    current_a: float
    worst_a: float
    load_fraction: float
    watts: float
    feeds: list[str]
    powers: list[str] = []
    board_a: float = 0.0


class BomLine(_Report):
    """One line of the bill of materials. Cables give the total `length_m`."""

    kind: Literal["fixture", "attachment", "controller", "component", "psu", "fuse", "cable"]
    item: str
    name: str
    count: int
    length_m: float | None = None


class Basis(_Report):
    """One unmeasured value that results rest on, with its source."""

    fact: str
    v: Any
    status: Status
    src: str | None
    used_for: list[str]


class RigReport(_Report):
    """The power, wiring and controller report (docs/studio/domain-model.md:228-243)."""

    target_fps: float | None
    limits: AutoWiring
    totals: Totals
    controllers: list[ControllerReport]
    outputs: list[OutputReport]
    hops: list[HopReport]
    feeds: list[FeedReport]
    psus: list[PsuReport]
    bom: list[BomLine]
    basis: list[Basis]
    notes: list[str]


# ---- the report ------------------------------------------------------------------


class _Bases:
    """Collects the unmeasured values results rest on, by fact path."""

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self.found: dict[str, tuple[Any, Status, str | None, set[str]]] = {}
        self._seen: set[tuple[str, str, str, str]] = set()

    def add(self, fact: str, v: Any, status: Status, src: str | None, use: str) -> None:
        self.found.setdefault(fact, (v, status, src, set()))[3].add(use)

    def number(self, kind: str, entity_id: str, field: str, fact: Any, use: str) -> None:
        """`fact` of the entity if it is unmeasured, and every dim its expression names."""
        key = (kind, entity_id, field, use)
        if fact is None or key in self._seen:
            return
        self._seen.add(key)
        if isinstance(fact, Sourced) and fact.status != "measured":
            self.add(f"{kind}/{entity_id}.{field}", self.catalog.num(entity_id, fact), fact.status, fact.src, use)
        raw = value(fact)
        if isinstance(raw, str):
            dims = getattr(self.catalog.get(entity_id), "dims", {})
            for name in sorted(expr.names(raw)):
                self.number(kind, entity_id, f"dims.{name}", dims.get(name), use)

    def text(self, kind: str, entity_id: str, field: str, fact: Any, use: str) -> None:
        if isinstance(fact, Sourced) and fact.status != "measured":
            self.add(f"{kind}/{entity_id}.{field}", value(fact), fact.status, fact.src, use)

    def fixture_power(self, type_id: str, use: str) -> None:
        power = self.catalog.get(type_id, "fixture_type").power
        self.number("fixture_type", type_id, "power.max_w", power.max_w, use)
        self.number("fixture_type", type_id, "power.v_nominal", power.v_nominal, use)

    def port(self, type_id: str, port: Port, use: str) -> None:
        if port.anchor is not None:
            anchor = self.catalog.get(type_id, "fixture_type").anchors[port.anchor]
            self.number("fixture_type", type_id, f"anchors.{port.anchor}.pigtail_m", anchor.pigtail_m, use)

    def records(self) -> list[Basis]:
        return [
            Basis(fact=fact, v=v, status=status, src=src, used_for=sorted(uses))
            for fact, (v, status, src, uses) in sorted(self.found.items())
        ]


def build_report(
    plan: WiringPlan,
    arrangement: Arrangement,
    instances: Sequence[Instance],
    slices: Sequence[OutputSlice],
    catalog: Catalog,
) -> tuple[RigReport, list[Issue]]:
    """The report of a wired rig, and its electrical violations and warnings.

    `slices` gives the chains in data order. The limits are `wiring.auto`'s,
    or `AutoWiring`'s defaults for explicit wiring.
    """
    wiring = arrangement.wiring
    limits = wiring.auto or AutoWiring()
    target_fps = wiring.auto.target_fps if wiring.auto is not None else wiring.target_fps
    controllers = [*arrangement.controllers, *plan.controllers]
    psus = [*arrangement.psus, *plan.psus]
    modes = auto_white_modes(plan.chains, controllers, catalog)
    board_watts = math.fsum(boards_w(psus, controllers, catalog).values())
    site = Site(instances, catalog, arrangement.power.cap, modes, board_watts)
    bases = _Bases(catalog)
    issues: list[Issue] = []
    copies = _copies(arrangement, plan)
    added = {c.id for c in plan.controllers}
    chains = {c.id: c for c in plan.chains}
    types = list(dict.fromkeys(i.type_id for i in instances))

    for type_id in types:
        bases.fixture_power(type_id, "totals")
        bases.fixture_power(type_id, "effect power")
        model = catalog.get(type_id).power.model_fact
        bases.text("fixture_type", type_id, "power.model", model, "effect power")
        # PSU sizing lowers the draw below every channel full only as far as it follows the frame.
        bases.text("fixture_type", type_id, "power.model", model, "PSU sizing")
        if any(site.share[i.id] < 1.0 for i in instances if i.type_id == type_id):
            bases.add(
                f"fixture_type/{type_id}.power.channel_split",
                "even",
                "assumed",
                "max_w is every channel full and splits evenly across the channels; one bar's per-channel watts "
                "are not measured (Q-004, the maintainer's private notes)",
                "PSU sizing",
            )
    profiles = {c.id: c.profile for c in controllers}
    for chain in plan.chains:
        if any(site.share[fid] < 1.0 for fid in chain.fixtures):
            firmware = catalog.get(catalog.get(profiles[chain.controller], "controller").firmware, "firmware")
            bases.add(
                f"firmware/{firmware.id}.ingest.auto_white",
                firmware.ingest.auto_white,
                "assumed",
                "a board setting: set WLED's auto-white mode to it on every board, since PSU sizing takes it; under "
                "None an RGB frame reaches 3 of 4 channels, and under Brighter or Max all 4 "
                "(https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125)",
                "PSU sizing",
            )
    if any("W" in catalog.spec(site.by_id[fid].type_id).channels for fid in plan.unassigned):
        bases.add(
            "wiring.unwired_auto_white",
            UNWIRED_AUTO_WHITE,
            "assumed",
            "an unwired fixture has no firmware, so effect power takes WLED's Accurate auto-white for it",
            "effect power",
        )

    outputs = [_output(s, chains[s.chain], controllers, site, bases, target_fps, issues) for s in slices]
    hops = []
    for s in slices:
        hops.extend(_hops(chains[s.chain], controllers, copies["controller"], limits, site, bases, issues))
    feeds = [_feed(f, chains[f.chain], psus, limits, site, bases, issues) for f in plan.feeds]
    linked = sorted({f.cable for f in feeds if len(f.fixtures) > 1})
    if linked:
        parts = (
            "pigtail, extension and T-trunk"
            if any(chains[f.chain].tee for f in feeds if len(f.fixtures) > 1)
            else "pigtail and extension"
        )
        bases.add(
            "wiring.link_conductors",
            linked,
            "assumed",
            f"each feed's own cable; the {parts} gauge is not found "
            "(RES-018, the maintainer's private notes)",
            "drop",
        )
    _coverage(plan, arrangement, issues)
    psu_reports = _psus(psus, plan, controllers, feeds, limits, site, bases, issues)
    if wiring.auto is not None:
        for p in psus:
            if p.position_m is None and any(f.psu == p.id for f in plan.feeds):
                source = copies["psu"][p.id]
                bases.add(
                    f"psu {source}.position_m",
                    list(ORIGIN),
                    "assumed",
                    "not given; feeds run from the world origin",
                    "feeds",
                )

    for b in bases.records():
        if b.status == "assumed":
            issues.append(
                Issue.of(
                    "warning",
                    "rests_on_assumed",
                    f"{b.fact} = {b.v!r} is assumed, and these results rest on it: {', '.join(b.used_for)}",
                    b.fact,
                )
            )

    board_a = math.fsum(p.board_a for p in psu_reports)
    report = RigReport(
        target_fps=target_fps,
        limits=limits,
        totals=Totals(
            fixtures=len(instances),
            pixels=sum(catalog.spec(i.type_id).count for i in instances),
            worst_w=site.worst_w,
            worst_a=math.fsum(site.current_a(i.id) for i in instances) + board_a,
            rgb_worst_w=site.rgb_worst_w,
            rgb_worst_a=math.fsum(site.rgb_worst_a(i.id) for i in instances) + board_a,
            capped_w=site.capped_w,
            capped_a=math.fsum(site.capped_a(i.id) for i in instances) + board_a,
            controllers=len(controllers),
            psus=len(psus),
            feeds=len(feeds),
        ),
        controllers=[_controller(c, slices, catalog, c.id in added) for c in controllers],
        outputs=outputs,
        hops=hops,
        feeds=feeds,
        psus=psu_reports,
        bom=_bom(instances, controllers, psus, feeds, hops, catalog, frozenset(c.id for c in plan.chains if c.tee)),
        basis=bases.records(),
        notes=_notes(plan, copies, feeds, site, psu_reports),
    )
    return report, issues


def _copies(arrangement: Arrangement, plan: WiringPlan) -> dict[str, dict[str, str]]:
    """For each controller and PSU id, the declared one whose position it has.

    A declared one has its own. Auto-wiring gives an added controller the
    first declared one of its profile, and an added PSU the first declared
    one of its type.
    """
    controllers = {c.id: c.id for c in arrangement.controllers}
    for c in plan.controllers:
        controllers[c.id] = next(d.id for d in arrangement.controllers if d.profile == c.profile)
    psus = {p.id: p.id for p in arrangement.psus}
    for p in plan.psus:
        psus[p.id] = next(d.id for d in arrangement.psus if d.type == p.type)
    return {"controller": controllers, "psu": psus}


def _controller_at(cid: str, controllers: Sequence[ControllerPlacement]) -> ControllerPlacement:
    return next(c for c in controllers if c.id == cid)


def _output(
    s: OutputSlice,
    chain: Chain,
    controllers: Sequence[ControllerPlacement],
    site: Site,
    bases: _Bases,
    target_fps: float | None,
    issues: list[Issue],
) -> OutputReport:
    catalog = site.catalog
    type_id = site.by_id[chain.fixtures[0]].type_id
    spec = catalog.spec(type_id)
    ft = catalog.get(type_id, "fixture_type")
    chip = catalog.get(spec.chipset, "chipset")
    for name in ("bit_s", "reset_s"):
        bases.number("chipset", chip.id, name, getattr(chip, name), "timing")
    bases.text("chipset", chip.id, "bits_per_channel", chip.bits_per_channel, "timing")
    bases.text("fixture_type", type_id, "pixels.chipset", ft.pixels.chipset, "timing")
    profile = catalog.get(_controller_at(s.controller, controllers).profile, "controller")
    firmware = catalog.get(profile.firmware, "firmware")
    bases.number("firmware", firmware.id, "min_frame_interval_s", firmware.min_frame_interval_s, "timing")
    led = catalog.led_type(profile.firmware, spec.chipset, spec.channels)
    t = frame_s(s.count, spec.t_px_s, spec.reset_s)
    shown = 1.0 / catalog.need(firmware.id, firmware.min_frame_interval_s)
    report = OutputReport(
        controller=s.controller,
        output=s.output,
        chain=s.chain,
        pixels=s.count,
        led_type=s.led_type,
        led_label=None if led is None else led.label,
        frame_s=t,
        wire_fps=1.0 / t,
        fps=min(1.0 / t, shown),
    )
    if target_fps is not None and report.fps < target_fps - EPS:
        issues.append(
            Issue.of(
                "warning",
                "fps_below_target",
                f"{s.count} px take {t * 1e3:.2f} ms a frame, so the wire allows {report.wire_fps:.1f} fps and "
                f"{firmware.id} shows at most {shown:.1f}, against a target of {target_fps:g}",
                f"{s.controller}/{s.output}",
            )
        )
    return report


def _hops(
    chain: Chain,
    controllers: Sequence[ControllerPlacement],
    copies: dict[str, str],
    limits: AutoWiring,
    site: Site,
    bases: _Bases,
    issues: list[Issue],
) -> list[HopReport]:
    catalog = site.catalog
    slack = limits.hop_slack
    ctrl = _controller_at(chain.controller, controllers)
    profile = catalog.get(ctrl.profile, "controller")
    first = chain.fixtures[0]
    first_in = site.ports(first)[0]
    at = ctrl.position_m or ORIGIN
    if ctrl.position_m is None:
        bases.add(
            f"controller {copies[ctrl.id]}.position_m",
            list(ORIGIN),
            "assumed",
            "not given; leads run from the world origin",
            "leads",
        )
    bases.port(site.by_id[first].type_id, first_in, "leads")
    lead = HopReport(
        chain=chain.id,
        kind="lead",
        source=ctrl.id,
        target=first,
        run_m=run_m(at, first_in.at, slack),
        path_m=lead_m(at, first_in, slack),
    )
    out = [lead]
    lead_max = catalog.num(profile.id, profile.lead_max_m)
    if lead_max is not None:
        bases.number("controller", profile.id, "lead_max_m", profile.lead_max_m, "leads")
        if lead.path_m > lead_max + EPS:
            issues.append(
                Issue.of(
                    "warning",
                    "lead_over_limit",
                    f"the data lead to {first} is {lead.path_m:.2f} m; {profile.id} is good for {lead_max:g} m",
                    f"chain {chain.id}",
                )
            )
    for a, b in zip(chain.fixtures, chain.fixtures[1:]):
        a_in, a_out = site.ports(a)
        b_in = site.ports(b)[0]
        a_from = a_in if chain.tee else a_out
        bases.port(site.by_id[a].type_id, a_from, "hops")
        bases.port(site.by_id[b].type_id, b_in, "hops")
        hop = HopReport(
            chain=chain.id,
            kind="link",
            source=a,
            target=b,
            run_m=run_m(a_from.at, b_in.at, slack),
            path_m=tee_link_m((a_in, a_out), b_in, slack) if chain.tee else link_m(a_out, b_in, slack),
        )
        out.append(hop)
        if hop.path_m > limits.max_hop_m + EPS:
            issues.append(
                Issue.of(
                    "warning",
                    "hop_over_limit",
                    f"the data hop {a} -> {b} is {hop.path_m:.2f} m, over {limits.max_hop_m:g} m",
                    f"chain {chain.id}",
                )
            )
    return out


def _feed(
    feed: Feed,
    chain: Chain,
    psus: Sequence[PsuPlacement],
    limits: AutoWiring,
    site: Site,
    bases: _Bases,
    issues: list[Issue],
) -> FeedReport:
    catalog = site.catalog
    fids = chain.fixtures[feed.first : feed.first + feed.count]
    load = site.feed(fids, feed.cable, feed.length_m, limits.hop_slack, chain.tee)
    psu = next((p for p in psus if p.id == feed.psu), None)
    v_out = load.v_nominal if psu is None else catalog.need(psu.type, catalog.get(psu.type, "psu").v_out)
    plug = None if psu is None else catalog.get(psu.type, "psu").connector
    connector_a = least(
        load.connector_a, None if plug is None else catalog.num(plug, catalog.get(plug, "connector").rated_a)
    )
    check = site.check_a(load)
    lo, hi = fuse_window(check, connector_a, limits.connector_load_fraction)
    va = v_out * load.current_a
    ref = f"feed {feed.id}"
    if plug is not None:
        for use in ("feed limits", "fuse windows"):
            bases.number("connector", plug, "rated_a", catalog.get(plug, "connector").rated_a, use)

    for fid in fids:
        type_id = site.by_id[fid].type_id
        bases.fixture_power(type_id, "feeds")
        connector = site.ports(fid)[0].connector
        if connector is not None:
            rated = catalog.get(connector, "connector").rated_a
            for use in ("feed limits", "fuse windows"):
                bases.number("connector", connector, "rated_a", rated, use)
    if chain.tee:
        for use in ("feed limits", "fuse windows"):
            bases.add(
                "wiring.tee_connectors",
                "rated as the fixtures' input connector",
                "assumed",
                "the head, trunk and Ts carry the whole feed, and the feed limit takes the fixtures' input connector "
                "for them; the rating of Clen's T parts is not found",
                use,
            )
    conductors = catalog.get(feed.cable, "cable").conductors_mm2
    for role in ("vplus", "gnd"):
        bases.number("cable", feed.cable, f"conductors_mm2.{role}", getattr(conductors, role), "drop")
    # On T drops the trunk carries the current on, so the drop has no pass-through; it also leaves
    # out each fixture's own input pigtail, which carries only that fixture's current.
    if not chain.tee:
        for a, b in pairwise(fids):
            bases.port(site.by_id[a].type_id, site.ports(a)[1], "drop")
            bases.port(site.by_id[b].type_id, site.ports(b)[0], "drop")
        for fid in fids[:-1]:
            type_id = site.by_id[fid].type_id
            through = catalog.get(type_id, "fixture_type").power.passthrough_ohm
            if through is None:
                bases.add(
                    f"fixture_type/{type_id}.power.passthrough_ohm",
                    0.0,
                    "assumed",
                    "not measured (Q-010, the maintainer's private notes); "
                    "the drop leaves it out (docs/studio/domain-model.md:241)",
                    "drop",
                )
            else:
                bases.number("fixture_type", type_id, "power.passthrough_ohm", through, "drop")

    under = " under the cap" if site.capping else ""
    if connector_a is not None and check > limits.connector_load_fraction * connector_a + EPS:
        issues.append(
            Issue.of(
                "violation",
                "feed_over_rating",
                f"{check:.3f} A{under} is over {limits.connector_load_fraction:g} x the connector's {connector_a:g} A",
                ref,
            )
        )
    if feed.fuse_a is None:
        if site.capping:
            issues.append(
                Issue.of(
                    "violation",
                    "cap_without_fuse",
                    f"a capped feed needs a fuse at its head: with every channel full it asks {load.current_a:.2f} A, "
                    f"and only a fuse stops that if the cap fails; the window is {_window_text(lo, hi)}",
                    ref,
                )
            )
        else:
            issues.append(Issue.of("warning", "feed_unfused", f"no fuse; the window is {_window_text(lo, hi)}", ref))
    elif feed.fuse_a < lo - EPS or (hi is not None and feed.fuse_a > hi + EPS):
        issues.append(
            Issue.of(
                "violation", "fuse_outside_window", f"a {feed.fuse_a:g} A fuse is outside {_window_text(lo, hi)}", ref
            )
        )
    elif site.capping and connector_a is not None and load.current_a > connector_a + EPS:
        issues.append(
            Issue.of(
                "warning",
                "relies_on_cap_and_fuse",
                f"with every channel full this feed asks {load.current_a:.2f} A, "
                f"over the connector's {connector_a:g} A; "
                f"the RGB stream draws at most {load.capped_a:.2f} A under the cap, and the {feed.fuse_a:g} A fuse "
                "protects the connector if the cap fails",
                ref,
            )
        )
    if load.drop_fraction > limits.max_drop_fraction + EPS:
        issues.append(
            Issue.of(
                "warning",
                "drop_over_limit",
                f"{load.drop_v:.3f} V drop ({load.drop_fraction:.1%}) is over {limits.max_drop_fraction:.0%}",
                ref,
            )
        )
    return FeedReport(
        id=feed.id,
        psu=feed.psu,
        chain=feed.chain,
        fixtures=list(fids),
        cable=feed.cable,
        length_m=feed.length_m,
        current_a=load.current_a,
        capped_a=load.capped_a,
        connector_a=connector_a,
        fuse_a=feed.fuse_a,
        fuse_window_a=(lo, hi),
        loop_ohm=load.loop_ohm,
        drop_v=load.drop_v,
        drop_fraction=load.drop_fraction,
        va=va,
        note=f"{va:.0f} VA is over Class 2's {CLASS2_VA:g} VA" if va > CLASS2_VA else None,
    )


def _copied(added: Sequence[Any], copies: dict[str, str], what: str, kind_of: Any) -> str:
    """Which declared placement each added one copies, as a sentence."""
    by_source: dict[str, list[str]] = {}
    for a in added:
        by_source.setdefault(copies[a.id], []).append(a.id)
    kinds = {copies[a.id]: kind_of(a) for a in added}
    if len(by_source) == 1:
        (source,) = by_source
        return f"Each has {source}'s {what} ({kinds[source]}) and position."
    parts = [
        f"{', '.join(ids)} copy {source}'s {what} ({kinds[source]}) and position" for source, ids in by_source.items()
    ]
    return "; ".join(parts) + "."


def least(*ratings: float | None) -> float | None:
    """The least of the ratings given, or None if none is."""
    return min((r for r in ratings if r is not None), default=None)


def _window_text(lo: float, hi: float | None) -> str:
    return f"[{lo:.2f}, {hi:g}] A" if hi is not None else f"[{lo:.2f} A, no connector rating]"


def _coverage(plan: WiringPlan, arrangement: Arrangement, issues: list[Issue]) -> None:
    """Fixtures in two feeds are violations; chained fixtures in none are a warning."""
    chains = {c.id: c for c in plan.chains}
    fed: dict[str, str] = {}
    for feed in plan.feeds:
        shared: dict[str, list[str]] = {}
        for fid in chains[feed.chain].fixtures[feed.first : feed.first + feed.count]:
            if fid in fed:
                shared.setdefault(fed[fid], []).append(fid)
            fed.setdefault(fid, feed.id)
        if shared:
            n = sum(len(f) for f in shared.values())
            first = next(iter(shared.values()))[0]
            what = f"{first} is" if n == 1 else f"{first} and {n - 1} more {'fixture' if n == 2 else 'fixtures'} are"
            issues.append(
                Issue.of("violation", "feed_overlap", f"{what} also in feed {', '.join(shared)}", f"feed {feed.id}")
            )
    for chain in plan.chains:
        supplies = list(dict.fromkeys(f.psu for f in plan.feeds if f.chain == chain.id))
        if chain.tee and len(supplies) > 1:
            issues.append(
                Issue.of(
                    "violation",
                    "tee_supplies_join",
                    f"PSUs {', '.join(supplies)} feed one T trunk, whose V+ runs along every T, so their V+ would "
                    "join; feed a trunk from one PSU (RES-032, the maintainer's private notes)",
                    f"chain {chain.id}",
                )
            )
    unfed = [f for c in plan.chains for f in c.fixtures if f not in fed]
    if unfed:
        how = (
            "declare a PSU and auto-wiring feeds every chain"
            if arrangement.wiring.auto is not None
            else "add feeds to check them"
        )
        issues.append(
            Issue.of(
                "warning",
                "unfed",
                f"{len(unfed)} chained fixtures are on no feed, so their power is not checked; {how}",
            )
        )


def _psus(
    psus: Sequence[PsuPlacement],
    plan: WiringPlan,
    controllers: Sequence[ControllerPlacement],
    feeds: Sequence[FeedReport],
    limits: AutoWiring,
    site: Site,
    bases: _Bases,
    issues: list[Issue],
) -> list[PsuReport]:
    catalog = site.catalog
    derived = {p.id for p in plan.psus}
    profiles = {c.id: c.profile for c in controllers}
    out = []
    for p in psus:
        psu = catalog.get(p.type, "psu")
        v_out = catalog.need(psu.id, psu.v_out)
        i_max = catalog.need(psu.id, psu.i_max_a)
        mine = [f for f in feeds if f.psu == p.id]
        boards = board_load_a(p, profiles, catalog)
        current = sum(f.capped_a for f in mine) + boards
        worst = sum(f.current_a for f in mine) + boards
        if mine or boards:
            bases.number("psu", psu.id, "v_out", psu.v_out, "PSU loads")
            bases.number("psu", psu.id, "i_max_a", psu.i_max_a, "PSU loads")
        _board_bases(p, profiles, catalog, bases, issues)
        out.append(
            PsuReport(
                id=p.id,
                type=p.type,
                derived=p.id in derived,
                v_out=v_out,
                i_max_a=i_max,
                current_a=current,
                worst_a=worst,
                load_fraction=current / i_max,
                watts=current * v_out,
                feeds=[f.id for f in mine],
                powers=list(p.powers),
                board_a=boards,
            )
        )
        ref = f"psu {p.id}"
        if worst > i_max + EPS >= current:
            issues.append(
                Issue.of(
                    "warning",
                    "psu_full_white_overload",
                    f"with every channel full its {'feeds and boards' if boards else 'feeds'} ask {worst:.1f} A of its "
                    f"{i_max:g} A; it is sized for the "
                    f"{current:.2f} A the RGB stream draws{' under the cap' if site.capping else ''}, so a fallback "
                    "preset that drives every channel overloads it",
                    ref,
                )
            )
        if current > i_max + EPS:
            issues.append(Issue.of("violation", "psu_overload", f"{current:.2f} A is over its {i_max:g} A", ref))
        elif current > limits.psu_load_fraction * i_max + EPS:
            issues.append(
                Issue.of(
                    "warning",
                    "psu_over_derating",
                    f"{current:.2f} A is {current / i_max:.0%} of its {i_max:g} A, over {limits.psu_load_fraction:.0%}",
                    ref,
                )
            )
        volts = sorted({catalog.spec(site.by_id[fid].type_id).v_nominal for f in mine for fid in f.fixtures})
        if any(abs(v - v_out) > 1e-6 for v in volts):
            issues.append(
                Issue.of(
                    "violation",
                    "psu_voltage",
                    f"a {v_out:g} V supply feeds {', '.join(f'{v:g}' for v in volts)} V fixtures",
                    ref,
                )
            )
    return out


def _board_bases(
    p: PsuPlacement, profiles: Mapping[str, str], catalog: Catalog, bases: _Bases, issues: list[Issue]
) -> None:
    """The bases of the board load of `p`, and a warning for each board it powers without a `power_w`."""
    watts, unknown = board_w(p, profiles, catalog)
    for cid in unknown:
        issues.append(
            Issue.of(
                "warning",
                "board_power_unknown",
                f"it powers {cid}, but {profiles[cid]} gives no power_w, so its load leaves that board out",
                f"psu {p.id}",
            )
        )
    if not watts:
        return
    bases.add(
        "wiring.buck_efficiency", value(BUCK_EFFICIENCY), BUCK_EFFICIENCY.status, BUCK_EFFICIENCY.src, "PSU loads"
    )
    for cid in p.powers:
        controller = catalog.get(profiles[cid], "controller") if cid in profiles else None
        if controller is not None and controller.power_w is not None:
            bases.number("controller", controller.id, "power_w", controller.power_w, "PSU loads")


def _controller(
    placement: ControllerPlacement, slices: Sequence[OutputSlice], catalog: Catalog, derived: bool
) -> ControllerReport:
    mine = [s for s in slices if s.controller == placement.id]
    return ControllerReport(
        id=placement.id,
        profile=placement.profile,
        derived=derived,
        outputs=len(catalog.get(placement.profile, "controller").outputs),
        outputs_used=len(mine),
        pixels=sum(s.count for s in mine),
    )


def _bom(
    instances: Sequence[Instance],
    controllers: Sequence[ControllerPlacement],
    psus: Sequence[PsuPlacement],
    feeds: Sequence[FeedReport],
    hops: Sequence[HopReport],
    catalog: Catalog,
    tees: frozenset[str],
) -> list[BomLine]:
    """The bill of materials. `tees` names the `tee` chains, whose links are trunk runs."""
    lines: list[BomLine] = []

    def counted(kind: Any, ids: Counter) -> None:
        for item, count in sorted(ids.items()):
            lines.append(BomLine(kind=kind, item=item, name=catalog.get(item).name, count=count))

    counted("fixture", Counter(i.type_id for i in instances))
    counted("attachment", Counter(a for i in instances for a in i.attachments.values() if a is not None))
    counted("controller", Counter(c.profile for c in controllers))
    components: Counter = Counter()
    for c in controllers:
        for name, n in catalog.get(c.profile, "controller").components.items():
            components[name] += int(value(n))
    for name, count in sorted(components.items()):
        lines.append(BomLine(kind="component", item=name, name=name, count=count))
    bucks = sum(len(p.powers) for p in psus)
    if bucks:
        lines.append(BomLine(kind="component", item="buck converter", name="buck converter, PSU to board", count=bucks))
    counted("psu", Counter(p.type for p in psus))
    for rating, count in sorted(Counter(f.fuse_a for f in feeds if f.fuse_a is not None).items()):
        lines.append(BomLine(kind="fuse", item=f"{rating:g} A", name=f"{rating:g} A blade fuse", count=count))
    for cable in sorted({f.cable for f in feeds}):
        mine = [f for f in feeds if f.cable == cable]
        lines.append(
            BomLine(
                kind="cable",
                item=cable,
                name=catalog.get(cable).name,
                count=len(mine),
                length_m=sum(f.length_m for f in mine),
            )
        )
    groups = (
        ("lead", "data lead, controller to chain", lambda h: h.kind == "lead"),
        ("link", "fixture link, out to in", lambda h: h.kind == "link" and h.chain not in tees),
        ("trunk", "T trunk run, input to input", lambda h: h.kind == "link" and h.chain in tees),
    )
    for item, name, keep in groups:
        mine = [h for h in hops if keep(h)]
        if mine:
            lines.append(
                BomLine(kind="cable", item=item, name=name, count=len(mine), length_m=sum(h.run_m for h in mine))
            )
    return lines


def _notes(
    plan: WiringPlan,
    copies: dict[str, dict[str, str]],
    feeds: Sequence[FeedReport],
    site: Site,
    psus: Sequence[PsuReport],
) -> list[str]:
    notes = []
    if plan.controllers:
        ids = ", ".join(c.id for c in plan.controllers)
        notes.append(
            f"Auto-wiring added controllers {ids}, because the declared ones have too few outputs. "
            + _copied(plan.controllers, copies["controller"], "profile", lambda c: c.profile)
        )
    if plan.psus:
        ids = ", ".join(p.id for p in plan.psus)
        notes.append(
            f"Auto-wiring added PSUs {ids}, because the declared ones cannot carry every feed. "
            + _copied(plan.psus, copies["psu"], "type", lambda p: p.type)
        )
    tees = {c.id for c in plan.chains if c.tee}
    split = [
        c
        for c in dict.fromkeys(f.chain for f in feeds)
        if c not in tees and len({f.psu for f in feeds if f.chain == c}) > 1
    ]
    if split:
        notes.append(
            f"Chains {', '.join(split)} take feeds from more than one PSU. Keep V+ open at every feed "
            "boundary, as each feed assumes (docs/studio/domain-model.md:50), so that the V+ of two "
            "supplies never join, and join every supply's negative (RES-032, the maintainer's private "
            "notes)."
        )
    powering = [p for p in psus if p.board_a > 0.0]
    if powering:
        boards = [c for p in powering for c in p.powers]
        ids = ", ".join(p.id for p in powering)
        who = f"PSU {ids} also powers board" if len(powering) == 1 else f"PSUs {ids} also power board"
        notes.append(
            f"{who}{'s' if len(boards) > 1 else ''} {', '.join(boards)} through a buck converter: "
            f"{site.board_w:.2f} W at an assumed {value(BUCK_EFFICIENCY):.0%} buck efficiency, "
            "in the PSU loads and the "
            "totals. The power cap does not scale it."
        )
    if feeds:
        notes.append(
            f"A feed's VA is set against Class 2's {CLASS2_VA:g} VA as a note only; the figure is not "
            "checked for DC "
            "(https://www.superbrightleds.com/blog/"
            "is-there-a-difference-between-class-2-and-class-ii-power-supplies.html, "
            "https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c)."
        )
    if site.capped_w < site.worst_w - EPS:
        cap = site.cap
        limits = [f"{cap.max_brightness:.1%} brightness"] if cap.max_brightness < 1.0 else []
        if cap.max_watts is not None:
            limits.append(f"{cap.max_watts:g} W")
        under = (
            f", and the power cap ({' and '.join(limits)}) holds that to {site.capped_w:.1f} W; the engine keeps "
            "each PSU within its share of the cap"
            if site.scale < 1.0
            else ""
        )
        notes.append(
            f"PSUs are sized for {site.capped_w:.1f} W, not the {site.worst_w:.1f} W of every channel full. An RGB "
            f"stream makes the rig draw at most {site.rgb_worst_w:.1f} W, "
            "because each board's WLED derives W from RGB, and in "
            "Accurate mode an RGB frame reaches at most 2 of 4 channels "
            f"(https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L102-L125){under}. A fallback preset "
            "that drives every channel can overload them. The sizing holds only as far as each fixture's draw "
            "follows the frame; measure a fixture with every channel full and at the cap before buying supplies "
            "for it (Q-004, the maintainer's private notes)."
        )
    if site.capping:
        notes.append(
            "Under the power cap, feeds, connectors and fuse windows are checked at the capped current, and every "
            "feed needs a fuse at its head. The cap is software: a fallback preset or a bug can exceed it, and "
            'WLED\'s own limiter is "NOT guaranteed" to hold its margin '
            "(https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L182-L187), so the fuse is what "
            "protects the connector. Drops are still computed with every channel full."
        )
    return notes
