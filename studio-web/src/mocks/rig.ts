import type { CompiledRig } from "@/api/types";

/**
 * A hand-written compiled rig: three bars of 64 pixels in a row along x,
 * the middle one turned a quarter turn about z and wearing a point on its
 * data-in end and an eye on its data-out end. Matrices are column-major.
 * The point's world frame is given; the eye's is left out, as a rig from
 * before `attachment_matrices` would.
 */
export const threeBarRig: CompiledRig = {
  n: 192,
  catalog_digest: "mock-catalog",
  fixtures: [
    {
      id: "bar-1",
      type_id: "clen-rgbw-bar-1m",
      group: null,
      matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -0.5, 0.5, 0, 1],
      attachments: { end_a: null, end_b: null },
      pixel_start: 0,
      pixel_count: 64,
    },
    {
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
    },
    {
      id: "bar-3",
      type_id: "clen-rgbw-bar-1m",
      group: null,
      matrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0.5, 0.5, 0, 1],
      attachments: { end_a: null, end_b: null },
      pixel_start: 128,
      pixel_count: 64,
    },
  ],
  slices: [
    {
      controller: "c1",
      output: "rmt0",
      start: 0,
      count: 192,
      led_type: 30,
      color_order: "GRBW",
    },
  ],
  report: {
    totals: {
      pixels: 192,
      max_w: { v: 76.8, status: "stated", src: "RES-038" },
    },
    feeds: { connector_rated_a: { v: 4, status: "assumed", src: "RES-017" } },
  },
  issues: [
    {
      level: "warning",
      code: "assumed",
      message: "Rests on an assumed connector rating.",
      ref: null,
    },
  ],
};
