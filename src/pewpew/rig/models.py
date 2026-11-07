"""The rig file formats and the shapes `compile_rig` returns.

Three layers (docs/studio/domain-model.md:16-54):

- **Catalog.** One JSON file per entity, discriminated by `kind`. A fact is a
  literal or a `Sourced` record `{"v", "status", "src"}`. A numeric field can
  also be an expression over the entity's `dims` (see `pewpew.rig.expr`).
- **Arrangement.** What the user or the studio writes: fixtures with poses,
  preset groups, controllers, PSUs and wiring.
- **Derived.** Never stored: `Instance`, `FixtureInstance`, `OutputSlice`,
  `CompiledRig` and `Issue`.

Every file model forbids unknown fields. Units are SI with a suffix on the
field name (`_m`, `_s`, `_a`, `_v`, `_w`, `_deg`, `_mm2`).
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, TypeVar, cast

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from pydantic_core import PydanticCustomError

from pewpew.mapping import Grouping
from pewpew.power import MAX_CAP_W, EffectPower, PowerCap, PowerLimiter

# ---- shared ------------------------------------------------------------------

Status = Literal["measured", "stated", "inferred", "derived", "assumed"]

#: The largest arrangement `load_arrangement` accepts: free fixtures plus every
#: group's member count. Checked before any group expands. It also caps the
#: length of every list in an arrangement.
MAX_FIXTURES = 200

#: The largest |coordinate| of a position, in meters.
MAX_POSITION_M = 1e4
#: The largest ring `start_radius_m` and array step component, in meters.
MAX_SPAN_M = 1e3

#: A RigError and a compiled rig keep this many issues and replace the rest
#: with one count.
MAX_ISSUES = 100

#: The least frame rate a wiring option takes. Below about 5.6e-309 fps,
#: 1/fps is inf and the pixel arithmetic overflows.
MIN_FPS = 0.1
#: The largest cable slack. It keeps every run finite.
MAX_SLACK = 10.0
#: The least load and drop fraction. It keeps the fuse window finite.
MIN_FRACTION = 0.01
#: The longest feed cable, in meters. It keeps cable sums and drops finite,
#: and it is far over the longest run auto-wiring makes: two array members
#: 199 steps of MAX_SPAN_M·√3 from poses MAX_POSITION_M·√3 out, × MAX_SLACK,
#: is under 1e7 m.
MAX_CABLE_M = 1e9

#: |q| may differ from 1 by this much before a quaternion is refused.
QUAT_TOLERANCE = 1e-6
#: A |q| this close to 1 is already unit length, so canonical_quat keeps q.
_UNIT_ULPS = 4 * sys.float_info.epsilon

CatalogId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")]
# "/" is reserved for group members (`<group>/<k>`).
RigId = Annotated[str, Field(pattern=r"^[^/\s]+$")]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


# ---- provenance --------------------------------------------------------------


class Sourced(_Model):
    """A catalog fact with its provenance.

    `status` says how the value is known; anything other than `measured` is
    unmeasured. `src` names the source. Only a `derived` value may omit it.
    """

    status: Status
    src: str | None = None

    @model_validator(mode="after")
    def _src_unless_derived(self) -> Sourced:
        if self.src is None and self.status != "derived":
            raise PydanticCustomError("missing_src", "a {status} value needs a src", {"status": self.status})
        return self


Expr = Annotated[str, Field(description="an expression over the entity's dims: + - * / ( )")]
Num = float | Expr


class SourcedNum(Sourced):
    v: Num


class SourcedInt(Sourced):
    v: int


class SourcedText(Sourced):
    v: str


Vec3f = tuple[float, float, float]


class SourcedVec(Sourced):
    v: Vec3f | None


class SourcedPinmap(Sourced):
    v: dict[str, str] | None


#: A dimension: a number, an expression, or either one with provenance.
Dim = float | Expr | SourcedNum
IntFact = int | SourcedInt
TextFact = str | SourcedText
Vec3 = tuple[Num, Num, Num]


def value(fact: Any) -> Any:
    """The bare value of a literal or a `Sourced` record."""
    return cast(Any, fact).v if isinstance(fact, Sourced) else fact


def status(fact: Any) -> Status | None:
    """The status of a `Sourced` record, or None for a literal."""
    return fact.status if isinstance(fact, Sourced) else None


# ---- catalog: geometry ---------------------------------------------------------


class Profile(_Model):
    """A 2D CSG shape: one primitive at `at`, minus the shapes in `minus`.

    A part extruded along y reads the profile's 2D coordinates as (x, z). A
    part extruded along z reads them as (x, y). `circle` is a diameter.
    `ref` names another profile of the same entity, or `host:<name>` in an
    attachment.
    """

    rect: tuple[Num, Num] | None = None
    circle: Num | None = None
    polygon: list[tuple[Num, Num]] | None = None
    ref: str | None = None
    at: tuple[Num, Num] = (0.0, 0.0)
    minus: list[Profile] = []

    @model_validator(mode="after")
    def _one_primitive(self) -> Profile:
        given = [k for k in ("rect", "circle", "polygon", "ref") if getattr(self, k) is not None]
        if len(given) != 1:
            raise PydanticCustomError(
                "profile_primitive",
                "a profile needs exactly one of rect, circle, polygon or ref, got {given}",
                {"given": given or "none"},
            )
        return self


Glow = Literal["pixels", "pixel_nearest", "none"]


class Part(_Model):
    """One solid of an assembly.

    A `profile` part is the profile extruded over `range_m` along `axis`; with
    `taper_to` the far end scales to that factor (0 gives a cone). A `box` part
    is a cuboid of sizes (x, y, z) centred at `at`, or at every pixel when
    `at_pixels` is true. `glow` says how the part takes pixel colour
    (docs/studio/domain-model.md:245-252).
    """

    id: str
    profile: str | None = None
    box: Vec3 | None = None
    axis: Literal["y", "z"] = "y"
    range_m: tuple[Num, Num] | None = None
    taper_to: float | None = None
    at: Vec3 | None = None
    at_pixels: bool = False
    glow: Glow
    gain: Dim = 1.0
    finish: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> Part:
        if (self.profile is None) == (self.box is None):
            raise PydanticCustomError("part_shape", "a part needs exactly one of profile or box", {})
        if self.profile is not None and self.range_m is None:
            raise PydanticCustomError("part_range", "a profile part needs range_m", {})
        return self


Gender = Literal["male", "female"]


class SourcedGender(Sourced):
    v: Gender


class Anchor(_Model):
    """A named point on an entity: an end, a connector, a mount.

    An anchor with `accepts` takes an attachment whose `fits` names the same
    profile. Its `dir` points out of the fixture.
    """

    at: Vec3
    dir: Vec3f | None = None
    connector: str | None = None
    gender: Gender | SourcedGender | None = None
    pigtail_m: Num | None = None
    accepts: str | None = None
    src: str | None = None


Channels = Annotated[str, Field(pattern=r"^[RGBWC]{1,6}$")]


class SourcedChannels(Sourced):
    v: Channels


class Pixels(_Model):
    """The emitters along the fixture's +y axis, in data order.

    Pixel j sits at local (0, -span/2 + (j+0.5)*span/count, z_m). A null
    `facing` marks an omnidirectional fixture.
    """

    count: IntFact
    span_m: Dim
    z_m: Dim
    leds_per_pixel: IntFact = 1
    facing: Vec3f | SourcedVec | None = None
    beam_deg: Dim | None = None
    chipset: TextFact
    channels: Channels | SourcedChannels
    color_order: TextFact


PowerModel = Literal["linear", "flat"]


class SourcedPowerModel(Sourced):
    v: PowerModel


#: The power model of a fixture type that names none.
DEFAULT_POWER_MODEL = SourcedPowerModel(
    v="linear",
    status="assumed",
    src=(
        "default, not measured: draw in proportion to the channel sum, as WLED estimates it "
        "(https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp#L196-L206); QuinLED "
        "measured a 24 V SK6812 strip with one IC per LED at 52.70 W whatever it showed "
        "(https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png); "
        "Q-004, the maintainer's private notes"
    ),
)


class Power(_Model):
    """How a fixture draws power at `v_nominal`.

    `max_w` is the draw with every channel of every pixel full. `model` says
    how the draw follows the frame: `linear` scales `max_w` by the channel
    sum, `flat` draws `max_w` whatever the frame shows. Omitted, it is
    `DEFAULT_POWER_MODEL`.
    """

    v_nominal: Dim
    max_w: Dim
    measured_w: Dim | None = None
    passthrough_ohm: Dim | None = None
    model: PowerModel | SourcedPowerModel | None = None

    @property
    def model_fact(self) -> SourcedPowerModel | PowerModel:
        return DEFAULT_POWER_MODEL if self.model is None else self.model


# ---- catalog: entities ---------------------------------------------------------


class _Entity(_Model):
    id: CatalogId
    name: str
    notes: str | None = None


class FixtureType(_Entity):
    kind: Literal["fixture_type"]
    rev: int = 1
    inventory: str | None = None
    dims: dict[str, Dim] = {}
    profiles: dict[str, Profile] = {}
    parts: list[Part] = []
    anchors: dict[str, Anchor] = {}
    pixels: Pixels
    power: Power


class AttachmentType(_Entity):
    """A part that fits on a fixture anchor whose `accepts` equals `fits`.

    Its frame has the origin at the anchor, +y along the anchor's `dir` and +z
    along the host's +z. `host:<profile>` names a profile of the host.
    """

    kind: Literal["attachment_type"]
    rev: int = 1
    fits: str
    dims: dict[str, Dim] = {}
    profiles: dict[str, Profile] = {}
    parts: list[Part] = []
    anchors: dict[str, Anchor] = {}


class Chipset(_Entity):
    kind: Literal["chipset"]
    bit_s: Dim
    bits_per_channel: IntFact
    reset_s: Dim


class Connector(_Entity):
    kind: Literal["connector"]
    pins: IntFact
    rated_a: Dim
    pinmap: dict[str, str] | SourcedPinmap | None = None


class Conductors(_Model):
    vplus: Dim | None = None
    gnd: Dim | None = None
    data: Dim | None = None
    spare: Dim | None = None


class Cable(_Entity):
    """A cable. A null `length_m` means it is cut to the length a feed gives."""

    kind: Literal["cable"]
    length_m: Dim | None = None
    ends: tuple[str | None, str | None] = (None, None)
    conductors_mm2: Conductors


class Psu(_Entity):
    """A power supply. `connector` names its output connector, which limits
    every feed it powers as a fixture's input connector does."""

    kind: Literal["psu"]
    v_out: Dim
    i_max_a: Dim
    connector: str | None = None


#: WLED's auto-white modes (https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L266-L270).
AutoWhite = Literal["manual", "brighter", "accurate", "dual", "max"]


class Ingest(_Model):
    """How the firmware takes frames. `auto_white` is how it derives W from
    RGB on an RGBW output; None is `manual`, which derives no W."""

    protocol: str
    udp_port: int
    send: str
    auto_white: AutoWhite | None = None
    src: str | None = None


class LedType(_Model):
    """One firmware LED type and the pixel format it drives."""

    chipset: str
    channels: Channels
    type: int
    label: str
    src: str | None = None


class Firmware(_Entity):
    kind: Literal["firmware"]
    max_px_per_output: IntFact
    max_px_total: IntFact
    warn_px_per_output: IntFact
    min_frame_interval_s: Dim
    ingest: Ingest
    led_types: list[LedType]


class Output(_Model):
    id: str
    group: str


class OutputGroup(_Model):
    same_led_type: bool = False


class Controller(_Entity):
    """A controller board. `components` names the parts each board needs
    beyond itself, such as a level shifter, with the count per board.
    `power_w` is what the board draws at its own supply input, without its
    LEDs. A PSU that powers the board (`PsuPlacement.powers`) carries it
    through a buck converter."""

    kind: Literal["controller"]
    firmware: str
    outputs: list[Output]
    groups: dict[str, OutputGroup]
    data_out_v: Dim
    lead_max_m: Dim | None = None
    max_px_advised: IntFact | None = None
    network: list[str] = []
    components: dict[str, IntFact] = {}
    power_w: Dim | None = None


CatalogEntity = Annotated[
    FixtureType | AttachmentType | Chipset | Connector | Cable | Psu | Firmware | Controller,
    Field(discriminator="kind"),
]
CATALOG_ENTITY = TypeAdapter(CatalogEntity)
KINDS: tuple[str, ...] = (
    "fixture_type",
    "attachment_type",
    "chipset",
    "connector",
    "cable",
    "psu",
    "firmware",
    "controller",
)

# ---- arrangement ---------------------------------------------------------------

Quat = tuple[float, float, float, float]


def canonical_quat(q: Any) -> Quat:
    """`q` renormalized with w >= 0; raises ValueError if |q| is not near 1.

    When w is 0 the first nonzero of x, y, z is made positive, so each
    rotation has one stored form. A q within a few ulp of unit length is not
    divided again, so canonical_quat(canonical_quat(q)) == canonical_quat(q).
    """
    x, y, z, w = (float(c) for c in q)
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if not math.isfinite(norm) or abs(norm - 1.0) > QUAT_TOLERANCE:
        raise ValueError(f"quaternion |q| = {norm!r} is not within {QUAT_TOLERANCE} of 1")
    if abs(norm - 1.0) > _UNIT_ULPS:
        x, y, z, w = x / norm, y / norm, z / norm, w / norm
    lead = w if w != 0.0 else next((c for c in (x, y, z) if c != 0.0), 1.0)
    if lead < 0.0:
        x, y, z, w = -x, -y, -z, -w
    return (x + 0.0, y + 0.0, z + 0.0, w + 0.0)  # + 0.0 turns -0.0 into 0.0


#: One position coordinate, in meters.
Coord = Annotated[float, Field(ge=-MAX_POSITION_M, le=MAX_POSITION_M)]
Position = tuple[Coord, Coord, Coord]
Step = Annotated[float, Field(ge=-MAX_SPAN_M, le=MAX_SPAN_M)]

_T = TypeVar("_T")
#: A list of at most MAX_FIXTURES items.
Capped = Annotated[list[_T], Field(max_length=MAX_FIXTURES)]


class Aim(_Model):
    """A rotation given by the fixture's +y direction and a roll about it.

    Only the direction of `axis` counts; any nonzero length works.
    """

    axis: Vec3f
    roll_deg: float = 0.0

    @field_validator("axis")
    @classmethod
    def _nonzero(cls, axis: Vec3f) -> Vec3f:
        if not any(axis):
            raise PydanticCustomError("bad_aim", "aim.axis must not be zero", {})
        return axis


class Pose(_Model):
    """A placement: `T(position_m) · R`, with R from `quat_xyzw` or `aim`.

    The quaternion is stored canonical (unit length, w >= 0). With neither
    rotation given, R is the identity.
    """

    position_m: Position = (0.0, 0.0, 0.0)
    quat_xyzw: Quat | None = None
    aim: Aim | None = None

    @field_validator("quat_xyzw")
    @classmethod
    def _canonical(cls, q: Quat | None) -> Quat | None:
        if q is None:
            return None
        try:
            return canonical_quat(q)
        except ValueError as exc:
            raise PydanticCustomError("bad_quaternion", "{reason}", {"reason": str(exc)}) from None

    @model_validator(mode="after")
    def _one_rotation(self) -> Pose:
        if self.quat_xyzw is not None and self.aim is not None:
            raise PydanticCustomError("quat_and_aim", "give quat_xyzw or aim, not both", {})
        return self


class FixturePlacement(_Model):
    """One free fixture. `attach` maps an anchor name to an attachment type."""

    id: RigId
    type: str
    pose: Pose = Pose()
    attach: dict[str, str | None] = {}


def _cap(count: int, where: str) -> None:
    if count > MAX_FIXTURES:
        raise PydanticCustomError(
            "too_many_fixtures",
            "{where} has {count} fixtures; the limit is {limit}",
            {"where": where, "count": count, "limit": MAX_FIXTURES},
        )


class RingAttach(_Model):
    inner: str | None = None
    outer: str | None = None


class RingGroup(_Model):
    """`count` fixtures on a ring, each one's midpoint at radius `start_radius_m + L/2`.

    L is the fixture's length, end anchor to end anchor, so `start_radius_m`
    is the inner-end radius of an untilted member. Member k sits at angle
    `angle_offset_deg + 360k/count`, tilts up by `tilt_deg` about its
    midpoint and rolls by `roll_deg` (docs/studio/domain-model.md:193-200).
    With tilt a, the inner end is at plan radius
    `start_radius_m + L/2 · (1 - cos a)`. `data_in` says which end takes
    data; `"outer"` turns each member end for end and keeps its facing.
    """

    id: RigId
    preset: Literal["ring"]
    type: str
    count: Annotated[int, Field(ge=1)]
    start_radius_m: Annotated[float, Field(ge=0, le=MAX_SPAN_M)]
    angle_offset_deg: float = 0.0
    tilt_deg: float = 0.0
    roll_deg: float = 0.0
    data_in: Literal["inner", "outer"] = "inner"
    attach: RingAttach = RingAttach()
    pose: Pose = Pose()

    @model_validator(mode="after")
    def _size(self) -> RingGroup:
        _cap(self.count, f"group {self.id!r}")
        return self

    @property
    def size(self) -> int:
        return self.count


class ArrayGroup(_Model):
    """A line or grid: member (i, j) sits at `i*steps_m[0] + j*steps_m[1]`.

    Members are numbered row-major, `k = i*counts[1] + j`. Each one takes the
    `member` pose relative to its grid point. `attach` maps an anchor name to
    an attachment type for every member.
    """

    id: RigId
    preset: Literal["array"]
    type: str
    counts: Annotated[list[Annotated[int, Field(ge=1)]], Field(min_length=1, max_length=2)]
    steps_m: Annotated[list[tuple[Step, Step, Step]], Field(min_length=1, max_length=2)]
    member: Pose = Pose()
    attach: dict[str, str | None] = {}
    pose: Pose = Pose()

    @model_validator(mode="after")
    def _shape(self) -> ArrayGroup:
        if len(self.steps_m) != len(self.counts):
            raise PydanticCustomError("array_steps", "steps_m needs one vector per entry of counts", {})
        for n in self.counts:
            _cap(n, f"group {self.id!r}")
        _cap(self.size, f"group {self.id!r}")
        return self

    @property
    def size(self) -> int:
        return math.prod(self.counts)


Group = Annotated[RingGroup | ArrayGroup, Field(discriminator="preset")]


class ControllerPlacement(_Model):
    id: RigId
    profile: str
    position_m: Position | None = None


class PsuPlacement(_Model):
    """A PSU. `powers` names the controllers it also powers through a buck
    converter; the report adds their draw to its load."""

    id: RigId
    type: str
    position_m: Position | None = None
    powers: Capped[str] = []


class Chain(_Model):
    """Fixtures in data order on one controller output.

    `tee` hangs each fixture on a drop of a T trunk. The fixture takes data
    and power at its `in` port and sends its data back up the same drop, so
    each data hop runs from one fixture's `in` to the next one's, and the
    trunk, not the fixture, carries the current on.
    """

    id: RigId
    controller: str
    output: str
    fixtures: Annotated[list[str], Field(min_length=1, max_length=MAX_FIXTURES)]
    color_order: str | None = None
    tee: bool = False


class Feed(_Model):
    """A PSU feed into `count` fixtures of a chain, from index `first`.

    It injects at the input of fixture `first`, with V+ open toward the
    upstream run (docs/studio/domain-model.md:50).
    """

    id: RigId
    psu: str
    chain: str
    first: Annotated[int, Field(ge=0)]
    count: Annotated[int, Field(ge=1)]
    cable: str
    length_m: Annotated[float, Field(gt=0, le=MAX_CABLE_M)]
    fuse_a: float | None = None


class AutoWiring(_Model):
    """Options for the deterministic auto-wiring (docs/studio/domain-model.md:217-226).

    The defaults are the design's: 3 m hop
    (https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607),
    75% loading of a fuse sized to the connector, Littelfuse's guidance as
    RES-033 records it (the maintainer's private notes;
    https://info.littelfuse.com/hubfs/Fuseology%20Design%20Guide.pdf),
    10% drop (https://quinled.info/the-ultimate-led-strip-power-injection-guide/)
    and 80% PSU loading (https://flexfireleds.com/blog/LED-power-supply-derating).
    The 1.2 slack is the design's example figure (docs/studio/domain-model.md:239);
    it lengthens every straight cable run: data hops, leads and feeds.
    `feed_cable` names the cable of every feed; None takes the catalog cable
    with the lowest loop resistance per metre.
    """

    target_fps: Annotated[float, Field(ge=MIN_FPS)] = 40.0
    fixtures_per_output: Annotated[int, Field(ge=1)] | None = None
    max_hop_m: Annotated[float, Field(gt=0)] = 3.0
    hop_slack: Annotated[float, Field(ge=1, le=MAX_SLACK)] = 1.2
    connector_load_fraction: Annotated[float, Field(ge=MIN_FRACTION, le=1)] = 0.75
    max_drop_fraction: Annotated[float, Field(ge=MIN_FRACTION, le=1)] = 0.10
    psu_load_fraction: Annotated[float, Field(ge=MIN_FRACTION, le=1)] = 0.8
    feed_cable: str | None = None


class Wiring(_Model):
    """Explicit `chains` and `feeds`, or `auto`. Both empty leaves all unwired."""

    # compile_rig does not read this; ws2's electrical report (`rig.report`)
    # does, for the "wire fps below target" warning (docs/studio/domain-model.md:317).
    target_fps: Annotated[float, Field(ge=MIN_FPS)] | None = None
    chains: Capped[Chain] = []
    feeds: Capped[Feed] = []
    auto: AutoWiring | None = None

    @model_validator(mode="after")
    def _one_form(self) -> Wiring:
        if self.auto is not None and (self.chains or self.feeds or self.target_fps is not None):
            raise PydanticCustomError("wiring_form", "give wiring.auto or explicit chains and feeds, not both", {})
        return self


class PowerLimit(_Model):
    """A software cap on the rig's light and power (`pewpew.power.PowerCap`).

    `max_brightness` scales every frame. `max_watts`, when set, then holds
    the estimated draw at or under it. The default caps nothing. The report
    sizes PSUs for the capped worst case, and sizes fuses and connectors for
    full white, because a fallback preset or a bug can exceed a software cap.
    """

    max_watts: Annotated[float, Field(gt=0, le=MAX_CAP_W)] | None = None
    max_brightness: Annotated[float, Field(ge=0, le=1)] = 1.0

    @property
    def cap(self) -> PowerCap:
        return PowerCap(self.max_watts, self.max_brightness)


ARRANGEMENT_FORMAT = "pewpew.arrangement"
ARRANGEMENT_VERSION = 1


class Arrangement(_Model):
    """A rig as the user or the studio writes it (format v1).

    `power` is optional, so a file without it caps nothing. A reader older
    than the block refuses a file that has it, as an unknown field.
    """

    format: Literal["pewpew.arrangement"]
    version: Literal[1]
    name: str = ""
    groups: Capped[Group] = []
    fixtures: Capped[FixturePlacement] = []
    controllers: Capped[ControllerPlacement] = []
    psus: Capped[PsuPlacement] = []
    wiring: Wiring = Wiring()
    power: PowerLimit = PowerLimit()

    @model_validator(mode="after")
    def _size(self) -> Arrangement:
        _cap(len(self.fixtures) + sum(g.size for g in self.groups), "the arrangement")
        return self


# ---- derived -------------------------------------------------------------------

Level = Literal["error", "violation", "warning"]


class Issue(_Model):
    """One finding. Errors stop a compile; violations and warnings do not."""

    level: Level
    code: str
    message: str
    ref: str | None = None

    @classmethod
    def of(cls, level: Level, code: str, message: str, ref: str | None = None) -> Issue:
        return cls(level=level, code=code, message=message, ref=ref)

    @classmethod
    def error(cls, code: str, message: str, ref: str | None = None) -> Issue:
        return cls.of("error", code, message, ref)


class RigError(ValueError):
    """A load or compile that found error-level issues; they are in `.issues`.

    Over MAX_ISSUES issues, `.issues` keeps the first MAX_ISSUES, errors
    first, and one `too_many_issues` error that counts the rest.
    """

    def __init__(self, issues: Any) -> None:
        self.issues: tuple[Issue, ...] = capped(issues, "error")
        errors = [i for i in self.issues if i.level == "error"] or list(self.issues)
        head = "; ".join(f"{i.ref}: {i.message}" if i.ref else i.message for i in errors[:3])
        more = f" (and {len(errors) - 3} more)" if len(errors) > 3 else ""
        super().__init__(head + more)


_RANK = {"error": 0, "violation": 1, "warning": 2}


def capped(issues: Any, level: Level | None = None) -> tuple[Issue, ...]:
    """`issues`, or over MAX_ISSUES of them, the MAX_ISSUES most severe and
    one `too_many_issues` issue that counts the rest.

    The count issue has `level`, or None gives the level of the most severe
    issue it counts.
    """
    issues = tuple(issues)
    if len(issues) <= MAX_ISSUES:
        return issues
    ranked = sorted(issues, key=lambda i: _RANK[i.level])
    kept, rest = ranked[:MAX_ISSUES], ranked[MAX_ISSUES:]
    count = Issue.of(level or rest[0].level, "too_many_issues", f"{len(rest)} more issues are not listed")
    return (*kept, count)


@dataclass(frozen=True)
class Instance:
    """One placed fixture before pixel indexing, in authoring order.

    `matrix` is the 4x4 world matrix, read-only. `attachments` maps each
    anchor that accepts an attachment to its attachment type id, or None.
    """

    id: str
    type_id: str
    group: str | None
    matrix: np.ndarray
    attachments: Mapping[str, str | None]


@dataclass(frozen=True)
class WiringPlan:
    """What wiring produced: chains in data order, feeds, and what is left over.

    `unassigned` holds instance ids in authoring order; their pixels come
    after every chain. `controllers` and `psus` are the ones auto-wiring
    added to the declared ones; they follow them in data order.
    """

    chains: tuple[Chain, ...] = ()
    feeds: tuple[Feed, ...] = ()
    unassigned: tuple[str, ...] = ()
    issues: tuple[Issue, ...] = ()
    controllers: tuple[ControllerPlacement, ...] = ()
    psus: tuple[PsuPlacement, ...] = ()


Matrix16 = tuple[float, ...]


class FixtureInstance(_Model):
    """One fixture of a compiled rig.

    `matrix` is the world matrix as 16 floats in column-major order, the order
    of three.js `Matrix4.elements` (https://threejs.org/docs/pages/Matrix4.html).
    The fixture's pixels are `pixel_start .. pixel_start + pixel_count - 1`.
    `attachment_matrices` gives each attachment's frame in world space.
    """

    id: str
    type_id: str
    group: str | None
    matrix: Matrix16
    attachments: dict[str, str | None]
    attachment_matrices: dict[str, Matrix16 | None]
    pixel_start: int
    pixel_count: int
    controller: str | None = None
    output: str | None = None
    chain: str | None = None


class OutputSlice(_Model):
    """The contiguous pixels one controller output drives."""

    controller: str
    output: str
    chain: str
    start: int
    count: int
    led_type: int | None
    color_order: str


class ControllerSlice(_Model):
    """The contiguous pixels one controller receives, for DDP."""

    controller: str
    start: int
    count: int


def fixture_grouping(mapping: np.ndarray, fixtures: Sequence[FixtureInstance]) -> Grouping | None:
    """Each fixture's pixel range as one unit, centred on the mean of its
    pixels in `mapping`; None for a rig with no fixtures. A per-fixture
    pattern (`units = "fixture"`) then lights each bar as one unit."""
    if not fixtures:
        return None
    of = np.zeros(len(mapping), dtype=np.int32)
    centres = np.zeros((len(fixtures), 3), dtype=np.float32)
    for f, fixture in enumerate(fixtures):
        pixels = slice(fixture.pixel_start, fixture.pixel_start + fixture.pixel_count)
        of[pixels] = f
        if fixture.pixel_count:
            centres[f] = np.asarray(mapping[pixels], dtype=np.float64).mean(axis=0)
    for array in (of, centres):
        array.setflags(write=False)
    return Grouping(centres, of)


@dataclass(frozen=True, eq=False)
class CompiledRig:
    """A compiled arrangement. Arrays are read-only; pixels are in data order.

    `mapping` is the Contain-normalized float32 table `Renderer` takes.
    `report` is the `pewpew.rig.electrical.RigReport`, and `power` the
    `pewpew.power.EffectPower` behind `estimate_effect_power`. `power_cap`
    is the arrangement's cap. `issues` holds at most MAX_ISSUES issues and
    one count of the rest.
    """

    mapping: np.ndarray
    positions_m: np.ndarray
    normals: np.ndarray
    fixture_of: np.ndarray
    pixel_in_fixture: np.ndarray
    fixtures: tuple[FixtureInstance, ...]
    slices: tuple[OutputSlice, ...]
    controller_slices: tuple[ControllerSlice, ...]
    issues: tuple[Issue, ...]
    catalog_digest: str
    report: Any = None
    feeds: tuple[Feed, ...] = field(default=())
    power: EffectPower | None = None
    power_cap: PowerCap = field(default_factory=PowerCap)

    @property
    def n(self) -> int:
        return int(self.mapping.shape[0])

    def estimate_effect_power(self, frame_linear: np.ndarray) -> float:
        """The watts the rig draws to show `frame_linear`, with the boards its PSUs power.

        `frame_linear` is the renderer's (N, 3) linear-light RGB frame in rig
        pixel order (docs/studio/contracts.md:64-67).
        """
        if self.power is None:
            raise ValueError("this rig has no power model to estimate with")
        return self.power.watts(frame_linear)

    @property
    def grouping(self) -> Grouping | None:
        """The fixtures as the units of a per-fixture pattern (`fixture_grouping`)."""
        return fixture_grouping(self.mapping, self.fixtures)

    def limiter(self, cap: PowerCap | None = None) -> PowerLimiter:
        """A `PowerLimiter` for this rig under `cap`, or under `power_cap`."""
        return PowerLimiter(self.power_cap if cap is None else cap, self.power)

    def to_json(self) -> dict[str, Any]:
        """The compiled rig as plain JSON types: the body of `POST /api/compile`."""
        report = self.report
        if report is not None and hasattr(report, "model_dump"):
            report = report.model_dump(mode="json")
        return {
            "n": self.n,
            "catalog_digest": self.catalog_digest,
            "fixtures": [f.model_dump(mode="json") for f in self.fixtures],
            "slices": [s.model_dump(mode="json") for s in self.slices],
            "controller_slices": [s.model_dump(mode="json") for s in self.controller_slices],
            "feeds": [f.model_dump(mode="json") for f in self.feeds],
            "issues": [i.model_dump(mode="json") for i in self.issues],
            "report": report,
            "positions_m": self.positions_m.tolist(),
            "normals": self.normals.tolist(),
        }


# ---- schemas -------------------------------------------------------------------

_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def json_schemas() -> dict[str, str]:
    """The committed JSON Schemas, by file name, as the text written to disk."""
    arrangement = Arrangement.model_json_schema()
    catalog = CATALOG_ENTITY.json_schema()
    catalog["title"] = "pewpew catalog entity"
    out = {}
    for name, schema in (("arrangement.v1.json", arrangement), ("catalog.v1.json", catalog)):
        out[name] = json.dumps({"$schema": _DRAFT, **schema}, indent=2, ensure_ascii=False) + "\n"
    return out
