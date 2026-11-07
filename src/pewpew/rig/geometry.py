"""3D assemblies of catalog fixture and attachment types, as GLB bytes.

`build_glb(type_id, catalog)` meshes each part of a `fixture_type` or an
`attachment_type` and writes one binary glTF 2.0 file
(docs/studio/domain-model.md:245-273, docs/studio/contracts.md:78-82).
`assembly_digest(type_id, catalog)` is a short hash of those bytes, for the
URL of the file. The same inputs give the same bytes on macOS and Linux:
positions and normals are rounded to a fixed grid before the float32 cast,
because the last bits of `np.arccos` differ between the two.

**Frames.** A fixture is meshed in its local frame: the origin is on the
diffuser axis at mid-length, +y runs from the data-in end to the data-out end
and +z is the LED facing (docs/studio/domain-model.md:177-183). An attachment
is meshed in its own frame: the origin is at the anchor, +y points along the
anchor's `dir` and +z is the host's +z (docs/studio/contracts.md:68-71). The
file uses these frames without conversion. glTF is right-handed, +y up, in
meters (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units).

**Hosts.** An attachment's `host:<profile>` names a profile of each fixture
type with an anchor that accepts what the attachment fits. One GLB serves all
those hosts, so they must give the same meshes.

**Parts.** A profile part extrudes a 2D CSG profile over `range_m`. Along y
(the default) the profile's 2D coordinates are (x, z); along z they are
(x, y). `taper_to` scales the far end of the range toward the profile origin,
so 0 gives a cone apex. A box part is a cuboid centred at `at`, or one cuboid
per pixel when `at_pixels` is true; there `at` is an offset from each pixel.

manifold3d (`pip install pewpew[studio]`) evaluates the profiles, triangulates
them and extrudes them. This module computes the normals itself.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any

import numpy as np

from pewpew.rig.catalog import HOST_PREFIX, Catalog
from pewpew.rig.models import AttachmentType, FixtureType, Part, Profile

#: Segments in every circle. At the bar diffuser's 15.1 mm radius the facets
#: are 3.75° apart and the vertices are at most r(1 - cos(π/96)) ≈ 8 µm from
#: the true circle. A multiple of 4 puts a vertex on each of the circle's
#: four axis extremes.
CIRCLE_SEGMENTS = 96

#: Faces that meet at less than this angle share smooth normals. It is above
#: the 3.75° between circle facets and below the smallest crease in the
#: bundled types: 28.1° in the mesh (acos(11.9/13.6) = 29.0° on the true
#: circle) between the plug's wall and its flat foot, so that edge stays sharp.
SMOOTH_ANGLE_DEG = 15.0

#: Corner pairs per step of the normal sum: about 10 MB of working arrays.
PAIR_CHUNK = 1 << 16

#: Decimals kept before the float32 cast: positions to 1 nm, normal
#: components to 1e-6, so normals stay unit to within 1e-6.
POSITION_DECIMALS = 9
NORMAL_DECIMALS = 6

#: Linear base colour, metallic and roughness per `finish`. glTF base colour
#: factors are linear (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#_material_pbrmetallicroughness_basecolorfactor).
#: The aluminum colour is physicallybased.info's "Aluminum" and the 0.05 grey
#: of both blacks is its "Toner (Black)" (https://api.physicallybased.info/materials).
#: The other values, including metallic 1 for black-anodized, are chosen by
#: eye, not measured.
FINISHES: Mapping[str, tuple[tuple[float, float, float], float, float]] = {
    "aluminum": ((0.916, 0.923, 0.924), 1.0, 0.35),
    "black": ((0.05, 0.05, 0.05), 0.0, 0.5),
    "black-anodized": ((0.05, 0.05, 0.05), 1.0, 0.45),
    "opal": ((0.8, 0.8, 0.8), 0.0, 0.6),
}
UNSPECIFIED_FINISH = "unspecified"
_FALLBACK = ((0.5, 0.5, 0.5), 0.0, 0.5)

# GLB container constants (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-header,
# https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#chunks-overview).
GLB_MAGIC = 0x46546C67
GLB_VERSION = 2
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
FLOAT = 5126
UNSIGNED_INT = 5125
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963
TRIANGLES = 4


class GeometryError(ValueError):
    """Catalog data that cannot be meshed."""


@dataclass(frozen=True)
class _Scope:
    """The entity whose dims and profiles a profile reads, and its host."""

    entity_id: str
    profiles: Mapping[str, Profile]
    host: _Scope | None = None


@dataclass(frozen=True)
class PartMesh:
    """One part as triangles: float32 positions and normals, uint32 indices."""

    part: Part
    gain: float
    positions: np.ndarray
    normals: np.ndarray
    indices: np.ndarray


# ---- public API ---------------------------------------------------------------


def build_glb(type_id: str, catalog: Catalog) -> bytes:
    """The GLB of a fixture or attachment type: one node and one mesh per part.

    Each part node has `extras` `{"glow", "gain", "part"}`. The root node has
    `extras.pixel_axis` `{"y0", "span", "count"}` for a fixture type, with
    pixel j at y = y0 + (j + 0.5) * span / count, and None for an attachment
    type. Raises KeyError for an unknown type and GeometryError for data that
    cannot be meshed.
    """
    meshes = part_meshes(type_id, catalog)
    return _write_glb(type_id, meshes, _pixel_axis(type_id, catalog))


def assembly_digest(type_id: str, catalog: Catalog) -> str:
    """The first 16 hex digits of the SHA-256 of `build_glb(type_id, catalog)`."""
    return hashlib.sha256(build_glb(type_id, catalog)).hexdigest()[:16]


def part_meshes(type_id: str, catalog: Catalog) -> list[PartMesh]:
    """The meshes of a type's parts, in the order the data lists them.

    An attachment type is meshed on each of its hosts. Raises GeometryError
    when two hosts give different meshes.
    """
    m = _manifold3d()
    entity = _entity(type_id, catalog)
    if not entity.parts:
        raise GeometryError(f"{type_id} has no parts")
    hosts = _hosts(entity, catalog)
    built = [_meshes(m, _Scope(type_id, entity.profiles, h), entity.parts, catalog) for h in hosts or [None]]
    keys = [[(p.positions.tobytes(), p.normals.tobytes(), p.indices.tobytes()) for p in mesh] for mesh in built]
    for host, key in zip(hosts[1:], keys[1:]):
        if key != keys[0]:
            raise GeometryError(
                f"{type_id} meshes differently on {hosts[0].entity_id} and {host.entity_id},"
                " so one GLB cannot serve both"
            )
    return built[0]


def _meshes(m: Any, scope: _Scope, parts: list[Part], catalog: Catalog) -> list[PartMesh]:
    out = []
    for part in parts:
        try:
            positions, triangles = _part_solid(m, scope, part, catalog)
            out.append(_finish_mesh(part, catalog.need(scope.entity_id, part.gain), positions, triangles))
        except GeometryError as exc:
            raise GeometryError(f"{scope.entity_id}.{part.id}: {exc}") from None
    return out


# ---- catalog lookups ------------------------------------------------------------


def _manifold3d() -> Any:
    try:
        import manifold3d
    except ImportError as exc:
        raise ImportError("pewpew.rig.geometry needs manifold3d: pip install 'pewpew[studio]'") from exc
    return manifold3d


def _entity(type_id: str, catalog: Catalog) -> FixtureType | AttachmentType:
    entity = catalog.get(type_id)
    if not isinstance(entity, (FixtureType, AttachmentType)):
        raise KeyError(f"no fixture or attachment type {type_id!r}")
    return entity


def _hosts(entity: FixtureType | AttachmentType, catalog: Catalog) -> list[_Scope]:
    """The fixture types whose anchors accept the attachment, in id order."""
    if not isinstance(entity, AttachmentType):
        return []
    return [
        _Scope(ft.id, ft.profiles)
        for ft in catalog.fixture_types.values()
        if any(a.accepts == entity.fits for a in ft.anchors.values())
    ]


# ---- profiles and parts ---------------------------------------------------------


def _section(m: Any, scope: _Scope, p: Profile, catalog: Catalog) -> Any:
    """A profile as a manifold3d CrossSection.

    The primitive is centred at `at`. The `minus` shapes are in the same
    coordinates as the primitive, not offset by `at`.
    """

    num = partial(catalog.need, scope.entity_id)
    if p.rect is not None:
        size = (num(p.rect[0]), num(p.rect[1]))
        if min(size) <= 0:
            raise GeometryError(f"rect sizes must be above 0, got {list(size)}")
        shape = m.CrossSection.square(size, center=True)
    elif p.circle is not None:
        diameter = num(p.circle)
        if diameter <= 0:
            raise GeometryError(f"a circle diameter must be above 0, got {diameter}")
        shape = m.CrossSection.circle(diameter / 2, CIRCLE_SEGMENTS)
    elif p.polygon is not None:
        shape = m.CrossSection([[(num(x), num(y)) for x, y in p.polygon]], m.FillRule.NonZero)
    else:
        if p.ref is None:
            raise GeometryError("a profile needs a rect, circle, polygon or ref")
        shape = _named(m, scope, p.ref, catalog)
    shape = shape.translate((num(p.at[0]), num(p.at[1])))
    for sub in p.minus:
        shape = shape - _section(m, scope, sub, catalog)
    return shape


def _named(m: Any, scope: _Scope, name: str, catalog: Catalog) -> Any:
    if name.startswith(HOST_PREFIX):
        if scope.host is None:
            raise GeometryError(f"names {name!r} but no fixture type accepts this attachment")
        host, key = scope.host, name[len(HOST_PREFIX) :]
        if key not in host.profiles:
            raise GeometryError(f"names {name!r} but {host.entity_id} has no profile {key!r}")
        return _section(m, host, host.profiles[key], catalog)
    return _section(m, scope, scope.profiles[name], catalog)


def _part_solid(m: Any, scope: _Scope, part: Part, catalog: Catalog) -> tuple[np.ndarray, np.ndarray]:
    """A part's float64 positions and its triangles, wound counter-clockwise outward."""

    num = partial(catalog.need, scope.entity_id)
    if part.profile is not None:
        if part.at is not None or part.at_pixels:
            raise GeometryError("a profile part takes no at or at_pixels")
        if part.range_m is None:
            raise GeometryError("a profile part needs range_m")
        lo, hi = (num(v) for v in part.range_m)
        if not hi > lo:
            raise GeometryError(f"range_m must increase, got [{lo}, {hi}]")
        if part.taper_to is not None and part.taper_to < 0:
            raise GeometryError(f"taper_to must be at least 0, got {part.taper_to}")
        scale = 1.0 if part.taper_to is None else float(part.taper_to)
        section = _named(m, scope, part.profile, catalog)
        solid = section.extrude(hi - lo, scale_top=(scale, scale)).translate((0.0, 0.0, lo))
        positions, triangles = _arrays(solid)
        if part.axis == "y":
            # Extrusion runs along manifold z: (u, v, h) becomes (x, y, z) = (u, h, v).
            # The swap is a reflection, so the winding is reversed to keep it outward.
            positions = positions[:, [0, 2, 1]]
            triangles = triangles[:, [0, 2, 1]]
        return positions, triangles

    if part.range_m is not None or part.taper_to is not None or "axis" in part.model_fields_set:
        raise GeometryError("a box part takes no range_m, taper_to or axis")
    if part.box is None:
        raise GeometryError("a part needs a profile or a box")
    size = tuple(num(v) for v in part.box)
    if min(size) <= 0:
        raise GeometryError(f"box sizes must be above 0, got {list(size)}")
    positions, triangles = _arrays(m.Manifold.cube(size, center=True))
    offset = np.zeros(3) if part.at is None else np.array([num(v) for v in part.at])
    if part.at_pixels:
        centres = _pixel_centres(scope.entity_id, catalog) + offset
    else:
        centres = offset[None, :]
    n = len(positions)
    positions = (positions[None, :, :] + centres[:, None, :]).reshape(-1, 3)
    triangles = (triangles[None, :, :] + (np.arange(len(centres)) * n)[:, None, None]).reshape(-1, 3)
    return positions, triangles


def _pixel_axis(type_id: str, catalog: Catalog) -> dict[str, Any] | None:
    """`{"y0", "span", "count"}` of a fixture type, or None for an attachment type."""
    if not catalog.has(type_id, "fixture_type"):
        return None
    spec = catalog.spec(type_id)
    return {"y0": -spec.span_m / 2, "span": spec.span_m, "count": spec.count}


def _pixel_centres(type_id: str, catalog: Catalog) -> np.ndarray:
    """Pixel j at (0, y0 + (j+0.5)*span/count, z_m), as `compile_rig` places it."""
    axis = _pixel_axis(type_id, catalog)
    if axis is None:
        raise GeometryError("at_pixels needs the pixels of a fixture type")
    count = axis["count"]
    y = axis["y0"] + (np.arange(count) + 0.5) * axis["span"] / count
    return np.column_stack([np.zeros(count), y, np.full(count, catalog.spec(type_id).z_m)])


def _arrays(solid: Any) -> tuple[np.ndarray, np.ndarray]:
    mesh = solid.to_mesh64()
    positions = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    triangles = np.asarray(mesh.tri_verts, dtype=np.int64)
    return positions, triangles


# ---- normals and vertices -------------------------------------------------------


def _finish_mesh(part: Part, gain: float, positions: np.ndarray, triangles: np.ndarray) -> PartMesh:
    """Round the positions, drop zero-area triangles, add rounded normals and merge equal vertices."""
    if not (np.abs(positions) <= np.finfo(np.float32).max).all():
        raise GeometryError("a position is outside the float32 range")
    positions = np.round(positions, POSITION_DECIMALS)
    p = positions[triangles]
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area2 = np.linalg.norm(cross, axis=1, keepdims=True)
    keep = area2[:, 0] > 1e-15
    triangles = triangles[keep]
    if len(triangles) == 0:
        raise GeometryError("the part has no area")
    normals = np.round(_corner_normals(positions, triangles, cross[keep] / area2[keep]), NORMAL_DECIMALS)
    corners = np.hstack([positions[triangles.reshape(-1)], normals]).astype(np.float32)
    corners += np.float32(0.0)  # -0.0 becomes 0.0, so equal vertices have equal bytes
    vertices, inverse = np.unique(corners, axis=0, return_inverse=True)
    return PartMesh(
        part=part,
        gain=gain,
        positions=np.ascontiguousarray(vertices[:, :3]),
        normals=np.ascontiguousarray(vertices[:, 3:]),
        indices=inverse.reshape(-1).astype(np.uint32),
    )


def _corner_normals(positions: np.ndarray, triangles: np.ndarray, face_normal: np.ndarray) -> np.ndarray:
    """One unit normal per triangle corner, shape (3T, 3).

    A corner's normal is the angle-weighted mean of the face normals at its
    vertex that are within SMOOTH_ANGLE_DEG of its own face's normal. The
    sum takes about PAIR_CHUNK pairs of corners at a time, so the memory
    stays bounded at a vertex where many faces meet, such as a cone apex.
    """
    p = positions[triangles]
    to_next = np.roll(p, -1, axis=1) - p
    to_prev = np.roll(p, 1, axis=1) - p
    cos_angle = np.einsum("tij,tij->ti", to_next, to_prev) / (
        np.linalg.norm(to_next, axis=2) * np.linalg.norm(to_prev, axis=2)
    )
    angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)).reshape(-1)

    vertex = triangles.reshape(-1)
    face = np.repeat(np.arange(len(triangles)), 3)
    order = np.argsort(vertex, kind="stable")
    sorted_vertex = vertex[order]
    starts = np.flatnonzero(np.r_[True, sorted_vertex[1:] != sorted_vertex[:-1]])
    sizes = np.diff(np.r_[starts, len(vertex)])
    group = np.repeat(np.arange(len(starts)), sizes)
    k, first, ends = sizes[group], starts[group], np.cumsum(sizes[group])
    limit = math.cos(math.radians(SMOOTH_ANGLE_DEG))
    total = np.zeros((len(vertex), 3))
    lo = 0
    while lo < len(vertex):
        # Every ordered pair (a, b) of corners that share a vertex, for the sorted corners a in [lo, hi).
        # All the pairs of one corner a are in one step, in b order, so the step size does not change the sums.
        hi = max(lo + 1, int(np.searchsorted(ends, ends[lo] - k[lo] + PAIR_CHUNK, side="right")))
        kk = k[lo:hi]
        a = np.repeat(np.arange(lo, hi), kk)
        b = np.repeat(first[lo:hi], kk) + np.arange(kk.sum()) - np.repeat(np.cumsum(kk) - kk, kk)
        a, b = order[a], order[b]
        nb = face_normal[face[b]]
        near = np.einsum("ij,ij->i", face_normal[face[a]], nb) >= limit
        np.add.at(total, a[near], angle[b[near], None] * nb[near])
        lo = hi
    return total / np.linalg.norm(total, axis=1, keepdims=True)


# ---- GLB writer -----------------------------------------------------------------


def _write_glb(name: str, meshes: list[PartMesh], pixel_axis: dict[str, Any] | None) -> bytes:
    """A glTF 2.0 binary file: a JSON chunk, then one BIN chunk.

    It follows https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-gltf-layout
    (little-endian header and chunks, each chunk 4-byte aligned, JSON padded
    with spaces and BIN with zeros) and
    https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-stored-buffer
    (buffer 0 has no uri). Each attribute and index array has its own buffer
    view, so no view needs a byteStride
    (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#data-alignment).
    POSITION has min and max, written as the exact float32 values
    (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#accessors-bounds).
    Triangles are counter-clockwise seen from outside, which glTF reads as
    front faces under a transform with a positive determinant
    (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#instantiation).
    The JSON has sorted keys and no generator or timestamp.
    """
    finishes = sorted({_finish(mesh.part) for mesh in meshes})
    material_index = {f: i for i, f in enumerate(finishes)}
    blob = bytearray()
    views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []

    def add(array: np.ndarray, target: int, accessor: dict[str, Any]) -> int:
        data = array.astype(array.dtype.newbyteorder("<"), copy=False).tobytes()
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        accessors.append({"bufferView": len(views) - 1, **accessor})
        return len(accessors) - 1

    nodes: list[dict[str, Any]] = [
        {"name": name, "children": list(range(1, len(meshes) + 1)), "extras": {"pixel_axis": pixel_axis}}
    ]
    gltf_meshes = []
    for i, mesh in enumerate(meshes):
        count = len(mesh.positions)
        position = add(
            mesh.positions,
            ARRAY_BUFFER,
            {
                "componentType": FLOAT,
                "count": count,
                "type": "VEC3",
                "min": [float(v) for v in mesh.positions.min(axis=0)],
                "max": [float(v) for v in mesh.positions.max(axis=0)],
            },
        )
        normal = add(mesh.normals, ARRAY_BUFFER, {"componentType": FLOAT, "count": count, "type": "VEC3"})
        indices = add(
            mesh.indices,
            ELEMENT_ARRAY_BUFFER,
            {"componentType": UNSIGNED_INT, "count": len(mesh.indices), "type": "SCALAR"},
        )
        gltf_meshes.append(
            {
                "name": mesh.part.id,
                "primitives": [
                    {
                        "attributes": {"NORMAL": normal, "POSITION": position},
                        "indices": indices,
                        "material": material_index[_finish(mesh.part)],
                        "mode": TRIANGLES,
                    }
                ],
            }
        )
        nodes.append(
            {
                "name": mesh.part.id,
                "mesh": i,
                "extras": {"glow": mesh.part.glow, "gain": mesh.gain, "part": mesh.part.id},
            }
        )

    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": [_material(f) for f in finishes],
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    text = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    text += b" " * (-len(text) % 4)
    blob.extend(b"\0" * (-len(blob) % 4))
    length = 12 + 8 + len(text) + 8 + len(blob)
    return b"".join(
        [
            struct.pack("<III", GLB_MAGIC, GLB_VERSION, length),
            struct.pack("<II", len(text), CHUNK_JSON),
            text,
            struct.pack("<II", len(blob), CHUNK_BIN),
            bytes(blob),
        ]
    )


def _finish(part: Part) -> str:
    return part.finish or UNSPECIFIED_FINISH


def _material(finish: str) -> dict[str, Any]:
    (r, g, b), metallic, roughness = FINISHES.get(finish, _FALLBACK)
    return {
        "name": finish,
        "pbrMetallicRoughness": {
            "baseColorFactor": [r, g, b, 1.0],
            "metallicFactor": metallic,
            "roughnessFactor": roughness,
        },
    }
