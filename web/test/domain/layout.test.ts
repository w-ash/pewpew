import { describe, expect, test } from "vitest";
import {
  DOT, DOT_MIN, GLOW_GAP, GLOW_MAX, inputMarker, makeLayout, nearestFixture, padOf, type Layout, type MapShape, type RoomShape, type Viewport,
} from "../../src/domain/room/layout";
const line: MapShape = { n: 8, total: 8, positions: Array.from({ length: 8 }, (_, i) => [i / 7, 0, 0]), is3d: false, room: null };
const grid: MapShape = {
  n: 12, total: 12, is3d: false, room: null,
  positions: Array.from({ length: 12 }, (_, i) => [(i % 4) / 3, Math.floor(i / 4) / 2, 0]),
};
const cube: MapShape = {
  n: 27, total: 27, is3d: true, room: null,
  positions: Array.from({ length: 27 }, (_, i) => [(i % 3) / 2, (Math.floor(i / 3) % 3) / 2, Math.floor(i / 9) / 2]),
};
const room: RoomShape = {
  scale: 0.125,
  fixtures: [
    { id: "A1", pitch: 1 / 64, start: [0.1, 0.2], end: [0.3, 0.2], input: "start" },
    { id: "B1", pitch: 1 / 32, start: [0.5, 0.6], end: [0.5, 0.4], input: "end" },
  ],
  fixture_of: [0, 0, 0, 0, 1, 1, 1, 1],
  plan: { corner: [0, 0.75], unit: 0.001, url: "/plan?v=0" },
};
const roomMap: MapShape = {
  n: 8, total: 8, is3d: false, room,
  positions: [[0.1, 0.2], [0.17, 0.2], [0.23, 0.2], [0.3, 0.2], [0.5, 0.6], [0.5, 0.53], [0.5, 0.47], [0.5, 0.4]],
};

const views = [
  { width: 780, height: 500, dpr: 2 },
  { width: 1200, height: 300, dpr: 1 },
];

test("the room's margin is 30 px, or a tenth of a small stage's shorter side", () => {
  expect(padOf({ width: 1800, height: 1600, dpr: 2 })).toBe(60);
  expect(padOf({ width: 780, height: 292, dpr: 2 })).toBeCloseTo(29.2, 6);
});

/** Every dot's centre lies inside the viewport less its padding. */
function inside(layout: Layout, view: Viewport) {
  const pad = padOf(view);
  for (let i = 0; i < layout.n; i++) {
    expect(layout.px[i]).toBeGreaterThanOrEqual(pad - 1e-3);
    expect(layout.px[i]).toBeLessThanOrEqual(view.width - pad + 1e-3);
    expect(layout.py[i]).toBeGreaterThanOrEqual(pad - 1e-3);
    expect(layout.py[i]).toBeLessThanOrEqual(view.height - pad + 1e-3);
  }
}

describe.each(views)("on %o", (view) => {
  test("a strip spans the width, centred", () => {
    const l = makeLayout(line, view, null);
    inside(l, view);
    expect(l.px[0]).toBeCloseTo(padOf(view), 3);
    expect(l.px[7]).toBeCloseTo(view.width - padOf(view), 3);
    expect(new Set(l.py)).toEqual(new Set([view.height / 2]));
  });

  test("a 2D map keeps one scale for both axes, y=0 at the bottom", () => {
    const l = makeLayout(grid, view, null);
    inside(l, view);
    const sx = (l.px[1]! - l.px[0]!) / (1 / 3), sy = (l.py[0]! - l.py[4]!) / (1 / 2);
    expect(sx).toBeCloseTo(sy, 3);
    expect(l.py[0]).toBeGreaterThan(l.py[8]!);
  });

  test("a 3D map draws its z-slices left to right", () => {
    const l = makeLayout(cube, view, null);
    inside(l, view);
    const slice = (z: number) => Array.from(l.px).filter((_, i) => Math.floor(i / 9) === z);
    expect(Math.max(...slice(0))).toBeLessThan(Math.min(...slice(1)));
    expect(Math.max(...slice(1))).toBeLessThan(Math.min(...slice(2)));
  });

  test("a room draws true to life: dots from their fixture's pitch, the plan from its corner and unit", () => {
    const size = { width: 800, height: 600 };
    for (const plan of [null, size]) {
      const l = makeLayout(roomMap, view, plan);
      inside(l, view);
      const [a, b] = l.fixtures;
      const scale = (a!.bx - a!.ax) / 0.2; // device px per map unit
      expect(b!.by - b!.ay).toBeCloseTo(0.2 * scale, 3);
      const radius = (pitch: number) => Math.max(DOT_MIN * view.dpr, 0.5 * DOT * pitch * scale * room.scale);
      expect(l.radii[0]).toBeCloseTo(radius(1 / 64), 3);
      expect(l.radii[4]).toBeCloseTo(radius(1 / 32), 3);
      if (!plan) {
        expect(l.plan).toBeNull();
        continue;
      }
      expect(l.plan!.w).toBeCloseTo(800 * 0.001 * scale, 3);
      expect(l.plan!.h).toBeCloseTo(600 * 0.001 * scale, 3);
      expect(l.plan!.x).toBeCloseTo(a!.ax - 0.1 * scale, 3);
      expect(l.plan!.y).toBeCloseTo(a!.ay - (0.75 - 0.2) * scale, 3);
    }
  });
});

test("a room's glow reaches a quarter of the way to a fixture's nearest neighbour, at most 8 css px", () => {
  for (const view of views) {
    const l = makeLayout(roomMap, view, null);
    const [a, b] = l.fixtures;
    // A1 runs along y = 0.2 to x = 0.3; B1's nearest end is (0.5, 0.4).
    const gap = Math.hypot(b!.bx - a!.bx, b!.by - a!.by);
    expect(l.glow).toBeCloseTo(Math.min(GLOW_GAP * gap, GLOW_MAX * view.dpr), 3);
  }
});

test("a tap picks the nearest fixture within 16 px", () => {
  const view = { width: 780, height: 500, dpr: 2 };
  const layout = makeLayout(roomMap, view, null);
  const [a] = layout.fixtures;
  expect(nearestFixture(layout, (a!.ax + a!.bx) / 2, a!.ay + 10, 2)?.id).toBe("A1");
  expect(nearestFixture(layout, (a!.ax + a!.bx) / 2, a!.ay + 40, 2)).toBeNull();
});

test("the input marker points from the input end into the strip", () => {
  expect(inputMarker({ id: "x", ax: 0, ay: 0, bx: 10, by: 0, input: "start" }, 5)).toEqual([[8, 0], [0, 5], [0, -5]]);
  const [endTip] = inputMarker({ id: "x", ax: 0, ay: 0, bx: 10, by: 0, input: "end" }, 5);
  expect(endTip).toEqual([2, 0]);
});

test("the room fits under a banner over the stage's top, so every dot shows", () => {
  const view = { width: 780, height: 500, dpr: 2 };
  const under = { ...view, height: 400 };
  const l = makeLayout(grid, view, null, 100);
  expect(Math.min(...l.py)).toBeGreaterThanOrEqual(100 + padOf(under) - 1e-3);
  expect(Math.max(...l.py)).toBeLessThanOrEqual(view.height - padOf(under) + 1e-3);
  const r = makeLayout(roomMap, view, { width: 200, height: 100 }, 100);
  expect(Math.min(r.plan!.y, ...r.fixtures.flatMap((f) => [f.ay, f.by]))).toBeGreaterThanOrEqual(100);
});
