/** The 3D view's camera: the view buttons' framings, a tween between them, and a slow spin. Shared by
 * the Console's 3D stage (Stage3D) and the studio's. */
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import { Color, type PerspectiveCamera, Vector3 } from "three";
import type { SelectItem } from "../design/Select";
import { useMedia } from "../design/useMedia";
import { type Bounds, fitDistance, VIEWS, type ViewName } from "./views";

export const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

export const VIEW_ITEMS: readonly SelectItem[] = [
  { value: "angle", label: "Angle" },
  { value: "top", label: "Top" },
  { value: "side", label: "Side" },
];

/** Seconds per orbit at 60 fps: three-stdlib's OrbitControls turns 2π/3600·speed per frame. */
export const SPIN_SPEED = 1;

/** The parts of drei's OrbitControls the camera rig drives. */
interface OrbitControlsImpl {
  target: Vector3;
  update: () => void;
  addEventListener: (type: "start", listener: () => void) => void;
  removeEventListener: (type: "start", listener: () => void) => void;
}

interface Tween {
  from: Vector3;
  to: Vector3;
  fromTarget: Vector3;
  toTarget: Vector3;
  start: number;
  ms: number;
}

export function CameraRig({
  view,
  bounds,
  generation,
  onUserMove,
}: {
  view: ViewName | null;
  bounds: Bounds;
  generation: number;
  onUserMove: () => void;
}) {
  const camera = useThree((s) => s.camera) as PerspectiveCamera;
  const controls = useThree(
    (s) => s.controls,
  ) as unknown as OrbitControlsImpl | null;
  const size = useThree((s) => s.size);
  const tween = useRef<Tween | null>(null);
  const still = useMedia(REDUCED_MOTION);
  const tmp = useMemo(() => new Vector3(), []);

  // A view button press re-runs this through `generation`.
  useEffect(() => {
    if (!view || !controls) return;
    const to = VIEWS[view]
      .clone()
      .multiplyScalar(
        fitDistance(bounds.radius, size.width / Math.max(1, size.height)),
      )
      .add(bounds.center);
    if (still) {
      camera.position.copy(to);
      controls.target.copy(bounds.center);
      controls.update();
      tween.current = null;
      return;
    }
    tween.current = {
      from: camera.position.clone(),
      to,
      fromTarget: controls.target.clone(),
      toTarget: bounds.center.clone(),
      start: performance.now(),
      ms: 650,
    };
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- a view press (`generation`) or a new controller re-aims the camera; a rig or size change must not
  }, [view, generation, controls]);

  useEffect(() => {
    if (!controls) return;
    const onStart = () => {
      tween.current = null;
      onUserMove();
    };
    controls.addEventListener("start", onStart);
    return () => controls.removeEventListener("start", onStart);
  }, [controls, onUserMove]);

  useFrame(() => {
    const t = tween.current;
    if (!t || !controls) return;
    const k = Math.min(1, (performance.now() - t.start) / t.ms);
    const e = 1 - (1 - k) ** 3;
    // Direction and distance interpolate apart so the camera swings around the rig.
    const fromDir = t.from.clone().sub(t.fromTarget);
    const toDir = t.to.clone().sub(t.toTarget);
    const len = fromDir.length() + (toDir.length() - fromDir.length()) * e;
    controls.target.lerpVectors(t.fromTarget, t.toTarget, e);
    tmp
      .copy(fromDir)
      .normalize()
      .lerp(toDir.normalize(), e)
      .normalize()
      .multiplyScalar(len);
    camera.position.copy(controls.target).add(tmp);
    controls.update();
    if (k === 1) tween.current = null;
  });
  return null;
}

/** The page's text colour (--text-1) in three's linear working space: what is selected is marked in
 * it, as on the plan. */
export function useAccent(): Color {
  return useMemo(() => {
    const c = new Color(1, 1, 1);
    const token = getComputedStyle(document.documentElement).getPropertyValue("--text-1").trim();
    if (token) c.setStyle(token);
    return c;
  }, []);
}

/** The camera view picked (null once the user moves the camera) and the count of picks, which re-aims
 * the camera; the first rig with fixtures counts as a pick, so it is framed. */
export function useCameraView(rig: { readonly fixtures: readonly unknown[] } | null) {
  const [view, setView] = useState<ViewName | null>("angle");
  const [generation, setGeneration] = useState(0);
  const framed = useRef(false);
  useEffect(() => {
    if (!framed.current && rig && rig.fixtures.length > 0) {
      framed.current = true;
      setGeneration((g) => g + 1);
    }
  }, [rig]);
  const pick = (name: ViewName) => {
    setView(name);
    setGeneration((g) => g + 1);
  };
  return { view, generation, pick, release: () => setView(null) };
}
