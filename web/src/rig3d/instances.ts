/**
 * Per-instance data for drawing a compiled rig: one batch per fixture or
 * attachment type, each instanced across every part of that type's GLB.
 *
 * Matrices come from the server (`rig.fixtures[].matrix` and
 * `attachment_matrices`). An attachment samples its host's texture row at
 * the end pixel it sits on: pixel 0 at end_a and pixel n−1 at end_b
 * (docs/studio/domain-model.md §5, "Attachments"). Its GLB has no pixel axis
 * of its own, because one file serves both ends.
 */
import { Matrix4 } from "three";
import type { PartsCatalog } from "../rig/parts";
import type { Assembly, AssemblyAnchor, PixelAxis } from "./assembly";

/** A fixture as the 3D view draws it: the fields of both the engine's `rig` (`hello`, `layout`) and a
 * studio compile. */
export interface ViewFixture {
  readonly id: string;
  /** A variant id when the placement gave `dims`; else the catalog type. */
  readonly type_id: string;
  /** The catalog type the fixture is made from. */
  readonly base_type_id?: string | null;
  /** 16 numbers, column-major, three.js `Matrix4.elements` order, in the file's y-up meters. */
  readonly matrix: readonly number[];
  readonly pixel_start: number;
  readonly pixel_count: number;
  readonly dims?: Readonly<Record<string, number>> | null;
  /** Anchor name to attachment type, or null for a bare end. */
  readonly attachments?: Readonly<Record<string, string | null>> | null;
  /** Each attachment's frame in world space: origin on the anchor, +y along its direction. */
  readonly attachment_matrices?: Readonly<Record<string, readonly number[] | null>> | null;
}

/** A type's pixels: `count` over `span_m`, centred on its local y. */
export interface ViewType {
  readonly count: number;
  readonly span_m: number;
}

/** A rig as the 3D view draws it. */
export interface ViewRig {
  /** The pixels a frame carries: fewer than `total` when the engine decimates the map. */
  readonly n: number;
  /** The rig's own pixel count, which `pixel_start` counts in; `n` when absent. */
  readonly total?: number;
  readonly fixtures: readonly ViewFixture[];
  /** The pixels of each type placed, variants included (`rig_view`); absent from a studio compile. */
  readonly types?: Readonly<Record<string, ViewType>>;
}

export type End = "end_a" | "end_b";

export interface AssemblyRef {
  id: string;
  url: string;
  kind: "fixture" | "attachment";
}

export interface InstanceBatch {
  id: string;
  kind: "fixture" | "attachment";
  count: number;
  /** Index into `rig.fixtures` for each instance. */
  fixtureIndex: Int32Array;
  matrices: Float32Array;
  /** Texture row of the fixture each instance samples. */
  rows: Float32Array;
  /** Maps a part-local position to the host-local y it samples: `y = dot(axisY, vec4(p, 1))`. Constant for an attachment. */
  axisY: Float32Array;
  /** Host pixel axis per instance: y0, span, pixel count. */
  axis: Float32Array;
}

/** The catalog type a fixture is made from. */
export const baseType = (f: ViewFixture) => f.base_type_id ?? f.type_id;

/** The catalog types a rig uses, fixture types first, in first-use order. */
function typesFor(
  rig: ViewRig,
  catalog: PartsCatalog,
): Array<Omit<AssemblyRef, "url"> & { url: string | null }> {
  const out = new Map<
    string,
    Omit<AssemblyRef, "url"> & { url: string | null }
  >();
  for (const f of rig.fixtures) {
    // A variant draws from its base type's GLB (`variantAssembly`): no GLB is keyed by a variant.
    const t = catalog.fixture_types.find((x) => x.id === baseType(f));
    if (t && !out.has(t.id))
      out.set(t.id, { id: t.id, url: t.assembly_url, kind: "fixture" });
  }
  for (const f of rig.fixtures) {
    for (const id of Object.values(f.attachments ?? {})) {
      if (!id || out.has(id)) continue;
      const a = catalog.attachment_types.find((x) => x.id === id);
      if (a)
        out.set(a.id, { id: a.id, url: a.assembly_url, kind: "attachment" });
    }
  }
  return [...out.values()];
}

/** The GLBs a rig needs, fixture types first, in first-use order. */
export function assembliesFor(
  rig: ViewRig,
  catalog: PartsCatalog,
): AssemblyRef[] {
  return typesFor(rig, catalog).filter((r): r is AssemblyRef => r.url !== null);
}

/** The types a rig uses that the server sent no `assembly_url` for, so they are not drawn. */
export function missingAssemblies(
  rig: ViewRig,
  catalog: PartsCatalog,
): string[] {
  return typesFor(rig, catalog)
    .filter((r) => r.url === null)
    .map((r) => r.id);
}

/** The host-local y of the pixel an attachment at `end` takes its color from. */
function endPixelY(axis: PixelAxis, end: string): number {
  const j = end === "end_b" ? axis.count - 1 : 0;
  return axis.y0 + ((j + 0.5) * axis.span) / Math.max(axis.count, 1);
}

/** The host's pixel axis: from the GLB, else the y extent of its glowing parts. */
export function hostAxis(
  assembly: Assembly | undefined,
  pixelCount: number,
): PixelAxis {
  if (assembly?.pixelAxis) return { ...assembly.pixelAxis, count: pixelCount };
  let lo = Infinity;
  let hi = -Infinity;
  for (const part of assembly?.parts ?? []) {
    if (part.glow === "none") continue;
    part.geometry.computeBoundingBox();
    const box = part.geometry.boundingBox;
    if (box) {
      lo = Math.min(lo, box.min.y);
      hi = Math.max(hi, box.max.y);
    }
  }
  return hi > lo
    ? { y0: lo, span: hi - lo, count: pixelCount }
    : { y0: -0.5, span: 1, count: pixelCount };
}

/**
 * Where an end's attachment sits in host coordinates, for a rig that sends
 * no `attachment_matrices`. The anchor comes from the GLB, else the ends of
 * the pixel axis. One whose direction points down -Y gets a half turn about
 * Z, as `pose.anchor_frame` gives end_a (src/pewpew/rig/pose.py:161-175 on
 * branch studio-ws1-rig).
 */
export function anchorMatrix(
  end: string,
  anchor: AssemblyAnchor | undefined,
  axis: PixelAxis,
): Matrix4 {
  const at = anchor?.at ?? [
    0,
    end === "end_a" ? axis.y0 : axis.y0 + axis.span,
    0,
  ];
  const down = anchor?.dir ? anchor.dir[1] < 0 : end === "end_a";
  const k = down ? -1 : 1;
  // Written out so the half turn is exact; makeRotationZ(π) leaves 1e-16 in the off-diagonal.
  return new Matrix4().set(
    k,
    0,
    0,
    at[0],
    0,
    k,
    0,
    at[1],
    0,
    0,
    1,
    at[2],
    0,
    0,
    0,
    1,
  );
}

/** One instance batch per type drawn, then per attachment type. `assemblies` is keyed by each
 * fixture's `type_id` (a variant's own, from `variantAssembly`) and by attachment type. */
export function buildBatches(
  rig: ViewRig,
  assemblies: ReadonlyMap<string, Assembly>,
): InstanceBatch[] {
  const hosts = new Map<string, number[]>();
  const attached = new Map<string, Array<{ f: number; end: string }>>();
  rig.fixtures.forEach((fx, i) => {
    const drawn = fx.type_id;
    if (!assemblies.has(drawn)) return;
    if (!hosts.has(drawn)) hosts.set(drawn, []);
    hosts.get(drawn)?.push(i);
    for (const [end, id] of Object.entries(fx.attachments ?? {})) {
      if (!id || !assemblies.has(id)) continue;
      if (!attached.has(id)) attached.set(id, []);
      attached.get(id)?.push({ f: i, end });
    }
  });

  const batch = (
    id: string,
    kind: InstanceBatch["kind"],
    count: number,
  ): InstanceBatch => ({
    id,
    kind,
    count,
    fixtureIndex: new Int32Array(count),
    matrices: new Float32Array(count * 16),
    rows: new Float32Array(count),
    axisY: new Float32Array(count * 4),
    axis: new Float32Array(count * 3),
  });
  const axisFor = (fx: ViewFixture) =>
    hostAxis(assemblies.get(fx.type_id), fx.pixel_count);
  const out: InstanceBatch[] = [];
  const m = new Matrix4();
  const a = new Matrix4();

  for (const [id, list] of hosts) {
    const b = batch(id, "fixture", list.length);
    list.forEach((f, k) => {
      const fx = rig.fixtures[f]!;
      const axis = axisFor(fx);
      b.fixtureIndex[k] = f;
      b.matrices.set(fx.matrix, k * 16);
      b.rows[k] = f;
      b.axisY.set([0, 1, 0, 0], k * 4);
      b.axis.set([axis.y0, axis.span, axis.count], k * 3);
    });
    out.push(b);
  }

  for (const [id, list] of attached) {
    const b = batch(id, "attachment", list.length);
    list.forEach(({ f, end }, k) => {
      const fx = rig.fixtures[f]!;
      const axis = axisFor(fx);
      const world = fx.attachment_matrices?.[end];
      if (world) {
        // The server's frame; its host-local form is the fixture's inverse times it.
        m.fromArray(world);
        a.fromArray(fx.matrix).invert().multiply(m);
      } else {
        a.copy(
          anchorMatrix(
            end,
            assemblies.get(fx.type_id)?.anchors[end as End],
            axis,
          ),
        );
        m.fromArray(fx.matrix).multiply(a);
      }
      b.fixtureIndex[k] = f;
      b.matrices.set(m.elements, k * 16);
      b.rows[k] = f;
      b.axisY.set([0, 0, 0, endPixelY(axis, end)], k * 4);
      b.axis.set([axis.y0, axis.span, axis.count], k * 3);
    });
    out.push(b);
  }
  return out;
}
