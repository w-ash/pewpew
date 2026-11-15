import { expect, test } from "vitest";
import { OrthographicCamera } from "three";
import { nearestFixture } from "../../src/rig3d/NearPick";
import type { ViewRig } from "../../src/rig3d/instances";

/** Two bars 1 m long, along x at z = 0 and z = 0.1, seen from above by a camera 4 m wide in 800 px (200 px a metre). */
const bar = (id: string, z: number) => ({ id, type_id: "strip", pixel_start: 0, pixel_count: 8, matrix: [0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, z, 1] });
const rig: ViewRig = { n: 16, fixtures: [bar("a", 0), bar("b", 0.1)], types: { strip: { count: 8, span_m: 1 } } };
const camera = new OrthographicCamera(-2, 2, 2, -2, 0.1, 10);
camera.position.set(0, 5, 0);
camera.up.set(0, 0, -1);
camera.lookAt(0, 0, 0);
camera.updateMatrixWorld();
camera.updateProjectionMatrix();
// Metres to px: x 400 + 200 x, y 400 + 200 z.
const pick = (x: number, y: number) => nearestFixture(rig, camera, 800, 800, x, y);

test("a click within 8 px of a strip picks it, however thin it is drawn, and one past that picks nothing", () => {
  for (const off of [0, 4, 8]) expect(pick(400, 400 - off)).toBe(0);
  expect(pick(400, 400 - 20)).toBe(-1);
  expect(pick(400 + 100, 400)).toBe(0); // the strip ends at 0.5 m
  expect(pick(400 + 100 + 12, 400)).toBe(-1);
});

test("with two strips near the click, the nearer one wins", () => {
  // The strips are 20 px apart: 12 px from "a" is 8 px from "b".
  expect(pick(400, 400 + 12)).toBe(1);
  expect(pick(400, 400 + 6)).toBe(0);
});
