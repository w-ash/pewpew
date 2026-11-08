import { Matrix4 } from "three";
import type { Arrangement, CompiledFixture, CompiledRig, PartsCatalog, RigReport } from "../../../src/studio/api/types";
import { poseMatrix } from "../../../src/rig3d/pose";

/** A compiled fixture, each field a test leaves out at what a fixture with no group, wiring, tags or
 * dims compiles to. */
export function compiledFixture(
  f: Pick<CompiledFixture, "id" | "type_id" | "matrix" | "pixel_start" | "pixel_count"> & Partial<CompiledFixture>,
): CompiledFixture {
  return {
    base_type_id: f.type_id, group: null, attachments: {}, attachment_matrices: {}, controller: null, output: null,
    chain: null, tags: [], dims: {}, ...f,
  };
}

/** The fields of a compiled rig that no test here reads, empty. */
const EMPTY_RIG = {
  controller_slices: [], feeds: [], positions_m: [], normals: [], controllers: [], scale: 1, shift: [0, 0, 0],
  plan: null, variants: [],
} satisfies Partial<CompiledRig>;

/**
 * A hand-written compiled rig: three bars of 64 pixels in a row along x,
 * the middle one turned a quarter turn about z and wearing a point on its
 * data-in end and an eye on its data-out end. Matrices are column-major.
 * The point's world frame is given; the eye's is left out, as a rig from
 * before `attachment_matrices` would.
 */
export const threeBarRig: CompiledRig = {
  ...EMPTY_RIG,
  n: 192,
  catalog_digest: "mock-catalog",
  fixtures: [
    compiledFixture({
      id: "bar-1",
      type_id: "clen-rgbw-bar-1m",
      group: null,
      matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -0.5, 0.5, 0, 1],
      attachments: { end_a: null, end_b: null },
      pixel_start: 0,
      pixel_count: 64,
    }),
    compiledFixture({
      id: "bar-2",
      type_id: "clen-rgbw-bar-1m",
      // Rz(90°): local +y points along world -x.
      matrix: [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 1.2, 0, 1],
      attachments: { end_a: "point-v0", end_b: "eye-v0" },
      attachment_matrices: {
        end_a: [0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0.5, 1.2, 0, 1],
        end_b: null,
      },
      pixel_start: 64,
      pixel_count: 64,
    }),
    compiledFixture({
      id: "bar-3",
      type_id: "clen-rgbw-bar-1m",
      group: null,
      matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0.5, 0.5, 0, 1],
      attachments: { end_a: null, end_b: null },
      pixel_start: 128,
      pixel_count: 64,
    }),
  ],
  slices: [
    {
      controller: "c1",
      output: "rmt0",
      start: 0,
      count: 192,
      led_type: 30,
      color_order: "GRBW",
      chain: "c1",
    },
  ],
  // A partial report: the studio's report panel shows any JSON it is given.
  report: {
    totals: {
      pixels: 192,
      max_w: { v: 76.8, status: "stated", src: "RES-038" },
    },
    feeds: { connector_rated_a: { v: 4, status: "assumed", src: "RES-017" } },
  } as unknown as RigReport,
  issues: [
    {
      level: "warning",
      code: "assumed",
      message: "Rests on an assumed connector rating.",
      ref: null,
    },
  ],
};

/** A parts catalog of the bar and its two end pieces, enough for the golden rings. */
export const partsCatalog: PartsCatalog = {
  digest: "test-catalog",
  fixture_types: [
    {
      id: "clen-rgbw-bar-1m",
      name: "1M LED Pixel Bar",
      digest: "test-bar",
      assembly_url: "/api/assembly/test-bar.glb",
      anchors: {
        end_a: { accepts: "diffuser_outer", connector: null },
        end_b: { accepts: "diffuser_outer", connector: null },
        in: { accepts: null, connector: "clen-4pin" },
        out: { accepts: null, connector: "clen-4pin" },
      },
    },
  ],
  attachment_types: [
    { id: "point-v0", name: "Point", digest: "test-point", assembly_url: "/api/assembly/test-point.glb", fits: "diffuser_outer" },
    { id: "eye-v0", name: "Eye", digest: "test-eye", assembly_url: "/api/assembly/test-eye.glb", fits: "diffuser_outer" },
  ],
  controllers: [{ id: "esp32s3-devkitc1-ahct125", name: "ESP32-S3 + 74AHCT125" }],
  psus: [{ id: "meanwell-lrs-350-24", name: "Mean Well LRS-350-24" }],
  cables: [{ id: "wire-16awg-pair", name: "16 AWG pair" }],
  presets: [
    { name: "ring", params: [{ name: "count", required: true }] },
    { name: "array", params: [{ name: "counts", required: true }] },
  ],
};

/** A stand-in for the server's compile: each member of a ring group at its angle, each free fixture at its
 * pose, groups first. The ids, order and group fields are the compiler's; the geometry is not. */
export function stubCompile(arrangement: Arrangement): CompiledRig {
  const fixtures: CompiledFixture[] = [];
  const add = (id: string, type_id: string, group: string | null, matrix: Matrix4, attachments: CompiledFixture["attachments"] = {}) =>
    fixtures.push(
      compiledFixture({
        id,
        type_id,
        group,
        matrix: matrix.elements.slice(),
        attachments: { end_a: null, end_b: null, ...attachments },
        pixel_start: fixtures.length * 64,
        pixel_count: 64,
      }),
    );
  for (const g of arrangement.groups) {
    if (g.preset !== "ring") continue;
    for (let k = 0; k < g.count; k++) {
      const t = (2 * Math.PI * k) / g.count;
      const turn = new Matrix4().makeRotationY(-t);
      add(`${g.id}/${k}`, g.type, g.id, turn.setPosition(g.start_radius_m * Math.cos(t), 0, g.start_radius_m * Math.sin(t)), {
        end_a: g.attach?.inner ?? null,
        end_b: g.attach?.outer ?? null,
      });
    }
  }
  for (const f of arrangement.fixtures) {
    add(f.id, f.type, null, poseMatrix({ position_m: f.pose?.position_m ?? [0, 0, 0], quat_xyzw: f.pose?.quat_xyzw ?? [0, 0, 0, 1] }));
  }
  return { ...threeBarRig, n: fixtures.length * 64, fixtures, issues: [] };
}
