import { useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { type Camera, Matrix4, Vector3 } from "three";
import { dragPreview } from "./dragPreview";
import type { ViewRig } from "./instances";

/** How far from a fixture, in CSS px, a click still picks it. */
export const NEAR_PX = 8;
/** Two fixtures this close to a click, in px, are equally near it: the one nearer the camera wins. */
const TIE_PX = 0.5;

const along = new Vector3();
const a = new Vector3();
const b = new Vector3();

/** The length of a fixture's strip: its pixels' span, else its `length`; 0 for a point. */
function lengthOf(rig: ViewRig, f: ViewRig["fixtures"][number]): number {
  return rig.types?.[f.type_id]?.span_m ?? f.dims?.length ?? 0;
}

/** The distance from (px, py) to the segment a–b, all in px. */
function distance(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax, dy = by - ay;
  const len2 = dx * dx + dy * dy;
  const t = len2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2)) : 0;
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/**
 * The index of the fixture whose strip is nearest (px, py) on a `width` × `height` px view through `camera`, within
 * `within` px, or -1. A tie goes to the fixture nearer the camera. Each fixture is where it is drawn: its matrix
 * moved by the editor's offset (`dragPreview.offsets`).
 */
export function nearestFixture(rig: ViewRig, camera: Camera, width: number, height: number, px: number, py: number, within = NEAR_PX): number {
  const view = new Matrix4();
  let best = -1, bestDistance = 0, bestDepth = 0;
  rig.fixtures.forEach((f, i) => {
    view.fromArray(f.matrix);
    const offset = dragPreview.offsets?.get(i);
    if (offset) view.premultiply(offset);
    const half = lengthOf(rig, f) / 2;
    along.set(0, 1, 0).transformDirection(view);
    a.setFromMatrixPosition(view).addScaledVector(along, -half).project(camera);
    b.setFromMatrixPosition(view).addScaledVector(along, half).project(camera);

    if (Math.abs(a.z) > 1 || Math.abs(b.z) > 1) return; // behind the camera or past its far plane
    const d = distance(px, py, (a.x + 1) * width / 2, (1 - a.y) * height / 2, (b.x + 1) * width / 2, (1 - b.y) * height / 2);
    if (d > within + 1e-6) return; // the slack keeps a click exactly `within` px away in
    const depth = Math.min(a.z, b.z);
    if (best < 0 || d < bestDistance - TIE_PX || (d <= bestDistance + TIE_PX && depth < bestDepth)) {
      best = i;
      bestDistance = d;
      bestDepth = depth;
    }
  });
  return best;
}

/** What a click that hit no fixture's body does: picks the nearest strip within `NEAR_PX`; tells whether there was one. */
export type Near = (e: MouseEvent) => boolean;

/** Registers, with `near`, what the canvas's `onPointerMissed` runs for a click: it picks the fixture whose
 * strip is within `NEAR_PX` of the click (`onPick`) and tells whether there was one. Renders nothing. */
export function NearPick({ rig, onPick, near }: { rig: ViewRig; onPick: (fixtureIndex: number) => void; near: (pick: Near | null) => void }) {
  const { camera, gl } = useThree();
  useEffect(() => {
    near((e) => {
      const box = gl.domElement.getBoundingClientRect();
      const i = nearestFixture(rig, camera, box.width, box.height, e.clientX - box.left, e.clientY - box.top);
      if (i >= 0) onPick(i);
      return i >= 0;
    });
    return () => near(null);
  }, [rig, onPick, camera, gl, near]);
  return null;
}
