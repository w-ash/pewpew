/**
 * Read a fixture or attachment GLB into parts the viewer can instance.
 *
 * Each part node carries `extras` `{"glow", "gain"}` and the root carries
 * `extras.pixel_axis` `{"y0", "span", "count"}` (docs/studio/contracts.md,
 * "Geometry"). three's GLTFLoader copies `extras` to `userData` on the
 * loaded scene, nodes, meshes and the result itself.
 */
import { BoxGeometry, type BufferGeometry, Matrix4, Mesh, type Object3D } from "three";
import type { Vec3 } from "../rig/parts";

export type Glow = "pixels" | "pixel_nearest" | "none";

export interface PixelAxis {
  y0: number;
  span: number;
  count: number;
}

export interface AssemblyAnchor {
  at: Vec3;
  dir?: Vec3;
}

export interface AssemblyPart {
  name: string;
  /** Baked into the assembly's root frame. */
  geometry: BufferGeometry;
  glow: Glow;
  gain: number;
}

export interface Assembly {
  parts: AssemblyPart[];
  pixelAxis: PixelAxis | null;
  anchors: Partial<Record<"end_a" | "end_b", AssemblyAnchor>>;
}

type Extras = Record<string, unknown>;

/** A number, or the `v` of a sourced `{"v","status","src"}` value. */
function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (value && typeof value === "object" && "v" in value)
    return num((value as { v: unknown }).v);
  return null;
}

function glowOf(value: unknown): Glow {
  return value === "pixels" || value === "pixel_nearest" ? value : "none";
}

function findUp(obj: Object3D | null, key: string): unknown {
  for (let o = obj; o; o = o.parent) {
    if ((o.userData as Extras)?.[key] !== undefined)
      return (o.userData as Extras)[key];
  }
  return undefined;
}

function pixelAxisOf(value: unknown): PixelAxis | null {
  if (!value || typeof value !== "object") return null;
  const v = value as Extras;
  const y0 = num(v.y0);
  const span = num(v.span);
  const count = num(v.count);
  return y0 !== null && span !== null && span > 0
    ? { y0, span, count: count ?? 0 }
    : null;
}

function vec3(value: unknown): Vec3 | null {
  if (Array.isArray(value) && value.length === 3) {
    const v = value.map(num);
    if (v.every((x) => x !== null)) return v as Vec3;
  }
  return null;
}

function anchorsOf(value: unknown): Assembly["anchors"] {
  const out: Assembly["anchors"] = {};
  if (!value || typeof value !== "object") return out;
  for (const end of ["end_a", "end_b"] as const) {
    const a = (value as Extras)[end] as Extras | undefined;
    const at = vec3(a?.at);
    if (at) out[end] = { at, dir: vec3(a?.dir) ?? undefined };
  }
  return out;
}

export function readAssembly(gltf: {
  scene: Object3D;
  userData?: Extras;
}): Assembly {
  const { scene } = gltf;
  scene.updateWorldMatrix(true, true);
  const toRoot = new Matrix4().copy(scene.matrixWorld).invert();
  const parts: AssemblyPart[] = [];
  let axisSource: unknown =
    gltf.userData?.pixel_axis ?? scene.userData?.pixel_axis;
  let anchorSource: unknown = gltf.userData?.anchors ?? scene.userData?.anchors;
  scene.traverse((obj) => {
    axisSource ??= (obj.userData as Extras)?.pixel_axis;
    anchorSource ??= (obj.userData as Extras)?.anchors;
    if (!(obj instanceof Mesh)) return;
    const geometry = (obj.geometry as BufferGeometry).clone();
    geometry.applyMatrix4(
      new Matrix4().multiplyMatrices(toRoot, obj.matrixWorld),
    );
    if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();
    parts.push({
      name: obj.name || `part-${parts.length}`,
      geometry,
      glow: glowOf(findUp(obj, "glow")),
      gain: num(findUp(obj, "gain")) ?? 1,
    });
  });
  return {
    parts,
    pixelAxis: pixelAxisOf(axisSource),
    anchors: anchorsOf(anchorSource),
  };
}

/** A part's glowing geometry as one bar over `span` along y, centred, with the part's x and z extent. */
function barOver(geometry: BufferGeometry, span: number): BufferGeometry {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return geometry.clone();
  const bar = new BoxGeometry(box.max.x - box.min.x, span, box.max.z - box.min.z);
  bar.translate((box.max.x + box.min.x) / 2, 0, (box.max.z + box.min.z) / 2);
  return bar;
}

/** An unlit part of a variant: one that spans the middle (y = 0) stretches along y by `stretch`; one on
 * one side of it, such as an end cap, keeps its size and moves with its outer end. */
function stretched(geometry: BufferGeometry, stretch: number): BufferGeometry {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  const out = geometry.clone();
  if (!box || (box.min.y < 0 && box.max.y > 0)) return out.scale(1, stretch, 1);
  const outer = box.min.y >= 0 ? box.max.y : box.min.y;
  return out.translate(0, outer * (stretch - 1), 0);
}

/**
 * The assembly of a dims variant of `count` pixels over `span`, from its base type's: no GLB is built
 * for a variant, so only its length is drawn. A `pixels` part (a diffuser, a tube) scales along y by the
 * variant's span over the base type's; the discrete LEDs of a `pixel_nearest` part become one bar over
 * the span, colored pixel by pixel as on the base type. An unlit part stretches along y by `stretch`, the
 * variant's length over the base type's, except an end part, which keeps its size and moves to the new
 * end (`stretched`). Anchors move with the stretch. A dim of the cross-section (`tube_d`, `housing_w`…)
 * is not drawn: every part keeps the base type's x and z. The base assembly is not changed.
 */
export function variantAssembly(base: Assembly, count: number, span: number, stretch: number): Assembly {
  const scale = base.pixelAxis ? span / base.pixelAxis.span : stretch;
  const parts = base.parts.map((part) => ({
    ...part,
    geometry:
      part.glow === "pixels"
        ? part.geometry.clone().scale(1, scale, 1)
        : part.glow === "pixel_nearest"
          ? barOver(part.geometry, span)
          : stretched(part.geometry, stretch),
  }));
  const anchors: Assembly["anchors"] = {};
  for (const [end, a] of Object.entries(base.anchors) as Array<[keyof Assembly["anchors"], AssemblyAnchor]>) {
    anchors[end] = { ...a, at: [a.at[0], a.at[1] * stretch, a.at[2]] };
  }
  return { parts, pixelAxis: base.pixelAxis && { y0: -span / 2, span, count }, anchors };
}
