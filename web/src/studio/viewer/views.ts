import { MathUtils, Vector3 } from "three";
import type { CompiledFixture } from "../api/types";

export type ViewName = "angle" | "top" | "side";

/** Camera directions from the prototype (docs/studio/prototype/golden-tubes-3d.html:464-468). */
export const VIEWS: Record<ViewName, Vector3> = {
  angle: new Vector3(0.62, 0.5, 0.6).normalize(),
  top: new Vector3(0, 1, 0.0001).normalize(),
  side: new Vector3(0, 0, 1),
};

export const FOV = 30;

/** Half a bar plus a 10 cm attachment, so the frame holds whole fixtures. */
const FIXTURE_REACH_M = 0.6;

export interface Bounds {
  center: Vector3;
  radius: number;
}

/** A sphere around every fixture origin, padded by one fixture's reach. */
export function rigBounds(fixtures: readonly CompiledFixture[]): Bounds {
  if (fixtures.length === 0) return { center: new Vector3(), radius: 1 };
  const lo = new Vector3(Infinity, Infinity, Infinity);
  const hi = new Vector3(-Infinity, -Infinity, -Infinity);
  const p = new Vector3();
  for (const f of fixtures) {
    p.fromArray(f.matrix, 12);
    lo.min(p);
    hi.max(p);
  }
  const center = lo.clone().add(hi).multiplyScalar(0.5);
  let r = 0;
  for (const f of fixtures) {
    p.fromArray(f.matrix, 12);
    r = Math.max(r, p.distanceTo(center));
  }
  return { center, radius: r + FIXTURE_REACH_M };
}

/** Camera distance that fits `radius` at this aspect (docs/studio/prototype/golden-tubes-3d.html:460-463). */
export function fitDistance(radius: number, aspect: number): number {
  const half = Math.tan(MathUtils.degToRad(FOV / 2));
  return (radius * 1.12) / (half * Math.min(1, aspect));
}
