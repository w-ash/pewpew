import { Button, ToggleButton } from "../../design/Button";
import { ErrorBoundary } from "../../design/ErrorBoundary";
import { Segments } from "../../design/Segments";
import type { SelectItem } from "../../design/Select";
import { useMedia } from "../../design/useMedia";
import { StatusBar } from "../../status/StatusBar";
import { useConnectionText } from "../../status/connection";
import { useFrameGap, useFrameValue, useWire, useWireContext } from "../../wire/store";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Color, type PerspectiveCamera, Vector3 } from "three";
import type { PartsCatalog, CompiledRig } from "../api/types";
import { entityOf, fixturesOf, poseOf, setPose } from "../editor/arrangement";
import {
  Gizmo,
  type GizmoMode,
  type GizmoSpace,
  gizmoActivity,
} from "../editor/Gizmo";
import { useDoc } from "../store/doc";
import { assembliesFor, missingAssemblies } from "./instances";
import { Rig } from "./Rig";
import {
  type Bounds,
  FOV,
  fitDistance,
  rigBounds,
  VIEWS,
  type ViewName,
} from "./views";

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

const VIEW_ITEMS: readonly SelectItem[] = [
  { value: "angle", label: "Angle" },
  { value: "top", label: "Top" },
  { value: "side", label: "Side" },
];
const GIZMO_ITEMS: readonly SelectItem[] = [
  { value: "translate", label: "Move" },
  { value: "rotate", label: "Rotate" },
];

/** Seconds per orbit at 60 fps: three-stdlib's OrbitControls turns 2π/3600·speed per frame. */
const SPIN_SPEED = 1;

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

function CameraRig({
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

interface StageProps {
  rig: CompiledRig | null;
  catalog: PartsCatalog | null;
}

export function Stage({ rig, catalog }: StageProps) {
  const { store } = useWireContext();
  const arrangement = useDoc((s) => s.history.present);
  const selection = useDoc((s) => s.selection);
  const select = useDoc((s) => s.select);
  const commit = useDoc((s) => s.commit);
  const readOnly = useDoc((s) => s.share.mode === "loading");
  const [view, setView] = useState<ViewName | null>("angle");
  const [generation, setGeneration] = useState(0);
  const [spin, setSpin] = useState(false);
  const [mode, setMode] = useState<GizmoMode>("translate");
  const [space, setSpace] = useState<GizmoSpace>("world");
  const still = useMedia(REDUCED_MOTION);
  // The page marks what is selected in its text colour (--text-1), as its
  // plan does; three converts the sRGB colour to its linear working space.
  const accent = useMemo(() => {
    const c = new Color(1, 1, 1);
    const token = getComputedStyle(document.documentElement)
      .getPropertyValue("--text-1")
      .trim();
    if (token) c.setStyle(token);
    return c;
  }, []);

  const bounds = useMemo(() => rigBounds(rig?.fixtures ?? []), [rig]);
  const [modelError, setModelError] = useState<string | null>(null);
  // A new set of fixture types gets a fresh try at loading their GLBs.
  const modelKey = useMemo(
    () =>
      [
        ...new Set(
          rig?.fixtures.flatMap((f) => [
            f.base_type_id ?? f.type_id,
            ...Object.values(f.attachments ?? {}).filter((a) => a !== null),
          ]) ?? [],
        ),
      ]
        .sort()
        .join(","),
    [rig],
  );
  // The error belongs to the models it was raised for.
  // oxlint-disable-next-line react/set-state-in-effect -- drops the error of the models a new key replaces; render-time reset would need a key prop on the loader
  useEffect(() => setModelError(null), [modelKey]);
  const missing = useMemo(
    () => (rig && catalog ? missingAssemblies(rig, catalog) : []),
    [rig, catalog],
  );
  // A failed load stays in the loader's cache, so it is cleared before a retry.
  const [attempt, setAttempt] = useState(0);
  const urls = useMemo(
    () => (rig && catalog ? assembliesFor(rig, catalog).map((r) => r.url) : []),
    [rig, catalog],
  );
  const onModelError = (message: string) => {
    useGLTF.clear(urls);
    setModelError(message);
  };
  const retryModels = () => {
    setModelError(null);
    setAttempt((a) => a + 1);
  };
  const framed = useRef(false);
  useEffect(() => {
    if (!framed.current && rig && rig.fixtures.length > 0) {
      framed.current = true;
      setGeneration((g) => g + 1);
    }
  }, [rig]);

  const selected = useMemo(
    () => new Set(fixturesOf(rig?.fixtures ?? [], selection)),
    [rig, selection],
  );
  const pose = selection ? poseOf(arrangement, selection, rig?.fixtures) : null;

  const pickView = (name: ViewName) => {
    setView(name);
    setGeneration((g) => g + 1);
  };

  return (
    <div className="studio-stage">
      <Canvas
        style={{ position: "absolute", inset: 0 }}
        dpr={[1, 2]}
        flat
        gl={{ antialias: true, alpha: true }}
        camera={{ fov: FOV, near: 0.01, far: 500, position: [6, 5, 6] }}
        onPointerMissed={() => {
          if (
            gizmoActivity.hovering ||
            performance.now() - gizmoActivity.releasedAt < 300
          )
            return;
          select(null);
        }}
        data-testid="stage-canvas"
      >
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          autoRotate={spin && !still}
          autoRotateSpeed={SPIN_SPEED}
        />
        <CameraRig
          view={view}
          bounds={bounds}
          generation={generation}
          onUserMove={() => setView(null)}
        />
        {/* A GLB that fails to load or parse takes only the rig down, not the canvas. */}
        <ErrorBoundary key={`${modelKey}#${attempt}`} fallback={null} onError={onModelError}>
          <Suspense fallback={null}>
            {rig && catalog && (
              <Rig
                rig={rig}
                frames={store}
                catalog={catalog}
                selected={selected}
                accent={accent}
                onPick={(i) => {
                  const f = rig.fixtures[i];
                  if (f) select(entityOf(arrangement, f));
                }}
              />
            )}
          </Suspense>
        </ErrorBoundary>
        {selection && pose && !readOnly && (
          <Gizmo
            pose={pose}
            fixtures={[...selected]}
            mode={mode}
            space={space}
            onCommit={(next) =>
              commit(
                setPose(useDoc.getState().history.present, selection, next),
              )
            }
          />
        )}
      </Canvas>

      <div className="studio-overlay">
        <Segments
          className="studio-veil"
          label="Camera view"
          items={VIEW_ITEMS}
          value={view ?? ""}
          onChange={(name) => pickView(name as ViewName)}
        />
        <div className="studio-overlay-end">
          {selection && (
            <>
              <Segments
                className="studio-veil"
                label="Gizmo"
                items={GIZMO_ITEMS}
                value={mode}
                onChange={(m) => setMode(m as GizmoMode)}
              />
              <ToggleButton
                className="studio-veil"
                variant="tertiary"
                pressed={space === "local"}
                onPressedChange={(local) => setSpace(local ? "local" : "world")}
                title="Gizmo axes"
              >
                {space === "world" ? "World" : "Local"}
              </ToggleButton>
            </>
          )}
          <ToggleButton
            className="studio-veil"
            variant="tertiary"
            pressed={spin}
            onPressedChange={setSpin}
            title="Spin slowly"
          >
            Spin
          </ToggleButton>
        </div>
      </div>
      <StatusBar planNote={null} />
      <StageStatus
        rig={rig}
        modelError={modelError}
        onRetry={retryModels}
        missing={missing}
      />
    </div>
  );
}

function StageStatus({
  rig,
  modelError,
  onRetry,
  missing,
}: {
  rig: CompiledRig | null;
  modelError: string | null;
  onRetry: () => void;
  missing: readonly string[];
}) {
  const down = useConnectionText("status");
  const n = useWire((s) => s.map?.n);
  const t = useFrameValue((f) => f?.t.toFixed(1) ?? null);
  const stalled = useFrameGap() > 0;
  return (
    <div className="studio-status t-caption">
      <span data-testid="stage-status">
        {down ??
          (stalled
            ? "paused while idle · tap to resume"
            : `live · ${n} px${t !== null ? ` · t=${t} s` : ""}`)}
        {rig ? ` · ${rig.fixtures.length} fixtures` : ""}
      </span>
      {modelError && (
        <span data-tone="error" role="alert">
          <span>Fixture models did not load: {modelError}</span>
          <Button variant="tertiary" onPress={onRetry}>
            Retry
          </Button>
        </span>
      )}
      {missing.length > 0 && (
        <span role="alert">
          This server has no 3D model for {missing.join(", ")}, so{" "}
          {missing.length > 1 ? "they are" : "it is"} not drawn
        </span>
      )}
      <span className="studio-hint">
        Drag to orbit · pinch or scroll to zoom · two-finger drag to pan
      </span>
    </div>
  );
}
