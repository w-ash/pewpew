import { TransformControls } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef } from "react";
import { Group, Matrix4 } from "three";
import { dragPreview } from "../viewer/dragPreview";
import { canonicalQuat, type PoseQ, roundVec } from "./pose";

const TRANSLATION_SNAP_M = 0.01;
const ROTATION_SNAP_RAD = Math.PI / 180;

export type GizmoMode = "translate" | "rotate";
export type GizmoSpace = "world" | "local";

/** When the gizmo last let go, so the click that ends a drag does not also deselect. */
export const gizmoActivity = { releasedAt: 0, hovering: false };

interface GizmoProps {
  pose: PoseQ;
  fixtures: readonly number[];
  mode: GizmoMode;
  space: GizmoSpace;
  onCommit: (pose: PoseQ) => void;
}

function samePose(a: PoseQ, b: PoseQ): boolean {
  return [...a.position_m, ...a.quat_xyzw].every(
    (v, i) => Math.abs(v - [...b.position_m, ...b.quat_xyzw][i]!) < 1e-6,
  );
}

/**
 * A transform gizmo on a proxy at the selection's pose. While dragging, the
 * selection's instances follow the proxy's motion; the pose commits on
 * release and the next compile redraws from server matrices.
 */
export function Gizmo({ pose, fixtures, mode, space, onCommit }: GizmoProps) {
  const proxy = useMemo(() => new Group(), []);
  const start = useRef(new Matrix4());
  const startInverse = useRef(new Matrix4());
  const dragging = useRef(false);

  useLayoutEffect(() => {
    if (dragging.current) return;
    proxy.position.set(...pose.position_m);
    proxy.quaternion.set(...pose.quat_xyzw);
    proxy.updateMatrix();
  }, [pose, proxy]);

  const onMouseDown = () => {
    dragging.current = true;
    proxy.updateMatrix();
    start.current.copy(proxy.matrix);
    startInverse.current.copy(proxy.matrix).invert();
    dragPreview.begin(fixtures);
  };

  const onObjectChange = () => {
    if (!dragging.current) return;
    proxy.updateMatrix();
    dragPreview.move(
      new Matrix4().multiplyMatrices(proxy.matrix, startInverse.current),
    );
  };

  const onMouseUp = () => {
    dragging.current = false;
    gizmoActivity.releasedAt = performance.now();
    const q = proxy.quaternion;
    const next: PoseQ = {
      position_m: roundVec([
        proxy.position.x,
        proxy.position.y,
        proxy.position.z,
      ]),
      quat_xyzw: canonicalQuat([q.x, q.y, q.z, q.w]),
    };
    if (samePose(next, pose)) {
      dragPreview.clear();
      return;
    }
    onCommit(next);
  };

  return (
    <>
      <primitive object={proxy} />
      <TransformControls
        object={proxy}
        mode={mode}
        space={space}
        translationSnap={TRANSLATION_SNAP_M}
        rotationSnap={ROTATION_SNAP_RAD}
        size={0.9}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onObjectChange={onObjectChange}
        onChange={(e) => {
          const target = (
            e as { target?: { axis?: string | null } } | undefined
          )?.target;
          gizmoActivity.hovering = Boolean(target?.axis);
        }}
      />
    </>
  );
}
