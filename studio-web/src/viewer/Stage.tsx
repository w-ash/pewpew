import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Color, type PerspectiveCamera, Vector3 } from "three";
import type { Catalog, CompiledRig } from "@/api/types";
import { entityOf, fixturesOf, poseOf, setPose } from "@/editor/arrangement";
import {
  Gizmo,
  type GizmoMode,
  type GizmoSpace,
  gizmoActivity,
} from "@/editor/Gizmo";
import { cn } from "@/lib/cn";
import { useDoc } from "@/store/doc";
import { useSession } from "@/store/session";
import { assembliesFor, missingAssemblies } from "./instances";
import { Rig } from "./Rig";
import { RigBoundary } from "./RigBoundary";
import {
  type Bounds,
  FOV,
  fitDistance,
  rigBounds,
  VIEWS,
  type ViewName,
} from "./views";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

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
  const tmp = useMemo(() => new Vector3(), []);

  // biome-ignore lint/correctness/useExhaustiveDependencies: a view button press re-runs this through `generation`.
  useEffect(() => {
    if (!view || !controls) return;
    const to = VIEWS[view]
      .clone()
      .multiplyScalar(
        fitDistance(bounds.radius, size.width / Math.max(1, size.height)),
      )
      .add(bounds.center);
    if (prefersReducedMotion()) {
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

export interface StageProps {
  rig: CompiledRig | null;
  catalog: Catalog | null;
}

export function Stage({ rig, catalog }: StageProps) {
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
  // three converts the sRGB hex to its linear working space.
  const accent = useMemo(() => new Color("#6aa6ea"), []);

  const bounds = useMemo(() => rigBounds(rig?.fixtures ?? []), [rig]);
  const [modelError, setModelError] = useState<string | null>(null);
  // A new set of fixture types gets a fresh try at loading their GLBs.
  const modelKey = useMemo(
    () =>
      [
        ...new Set(
          rig?.fixtures.flatMap((f) => [
            f.type_id,
            ...Object.values(f.attachments ?? {}),
          ]) ?? [],
        ),
      ]
        .sort()
        .join(","),
    [rig],
  );
  // biome-ignore lint/correctness/useExhaustiveDependencies: the error belongs to the models it was raised for.
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
    <div className="relative h-full min-h-0 overflow-hidden rounded-md border border-line bg-surface">
      <Canvas
        className="!absolute inset-0"
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
          autoRotate={spin && !prefersReducedMotion()}
          autoRotateSpeed={SPIN_SPEED}
        />
        <CameraRig
          view={view}
          bounds={bounds}
          generation={generation}
          onUserMove={() => setView(null)}
        />
        <RigBoundary key={`${modelKey}#${attempt}`} onError={onModelError}>
          <Suspense fallback={null}>
            {rig && catalog && (
              <Rig
                rig={rig}
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
        </RigBoundary>
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

      <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap items-start justify-between gap-2">
        <fieldset
          className="pointer-events-auto flex overflow-hidden rounded-md border border-line bg-surface"
          aria-label="Camera view"
        >
          {(["angle", "top", "side"] as const).map((name) => (
            <ToggleButton
              key={name}
              pressed={view === name}
              onClick={() => pickView(name)}
            >
              {name}
            </ToggleButton>
          ))}
        </fieldset>
        <div className="pointer-events-auto flex flex-wrap gap-2">
          {selection && (
            <fieldset
              className="flex overflow-hidden rounded-md border border-line bg-surface"
              aria-label="Gizmo"
            >
              <ToggleButton
                pressed={mode === "translate"}
                onClick={() => setMode("translate")}
              >
                Move
              </ToggleButton>
              <ToggleButton
                pressed={mode === "rotate"}
                onClick={() => setMode("rotate")}
              >
                Rotate
              </ToggleButton>
              <ToggleButton
                pressed={space === "local"}
                onClick={() => setSpace(space === "world" ? "local" : "world")}
                label="Gizmo axes"
              >
                {space === "world" ? "World" : "Local"}
              </ToggleButton>
            </fieldset>
          )}
          <div className="flex overflow-hidden rounded-md border border-line bg-surface">
            <ToggleButton
              pressed={spin}
              onClick={() => setSpin(!spin)}
              label="Spin slowly"
            >
              Spin
            </ToggleButton>
          </div>
        </div>
      </div>
      <StageStatus
        rig={rig}
        modelError={modelError}
        onRetry={retryModels}
        missing={missing}
      />
    </div>
  );
}

function ToggleButton({
  pressed,
  onClick,
  children,
  label,
}: {
  pressed: boolean;
  onClick: () => void;
  children: React.ReactNode;
  label?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "min-h-11 min-w-11 px-3 text-xs font-medium uppercase tracking-wider text-muted hover:text-ink",
        "not-first:border-l not-first:border-line",
        pressed && "bg-ink text-surface hover:text-surface",
      )}
    >
      {children}
    </button>
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
  const connection = useSession((s) => s.connection);
  const boundN = useSession((s) => s.boundN);
  const t = useSession((s) => s.t);
  const engineError = useSession((s) => s.engineError);
  const stalled = useSession((s) => s.stalled);
  const live = connection === "open" && boundN !== null;
  return (
    <div className="pointer-events-none absolute inset-x-3 bottom-2 flex flex-wrap items-end justify-between gap-x-4 gap-y-1 text-xs text-muted">
      <span data-testid="stage-status">
        {connection === "open"
          ? live
            ? stalled
              ? "paused while idle · tap to resume"
              : `live · ${boundN} px${t !== null ? ` · t=${t.toFixed(1)} s` : ""}`
            : "binding…"
          : connection === "connecting"
            ? "connecting…"
            : "disconnected, retrying…"}
        {rig ? ` · ${rig.fixtures.length} fixtures` : ""}
      </span>
      {engineError && (
        <span
          className="pointer-events-auto max-w-full truncate rounded bg-error px-2 py-1 text-white"
          role="alert"
        >
          {engineError}
        </span>
      )}
      {modelError && (
        <span
          className="pointer-events-auto flex max-w-full items-center gap-1 rounded bg-error pl-2 text-white"
          role="alert"
        >
          <span className="truncate">
            Fixture models did not load: {modelError}
          </span>
          <button
            type="button"
            onClick={onRetry}
            className="min-h-11 shrink-0 px-3 font-medium underline"
          >
            Retry
          </button>
        </span>
      )}
      {missing.length > 0 && (
        <span
          className="pointer-events-auto max-w-full truncate rounded bg-warning px-2 py-1 text-white"
          role="alert"
        >
          This server has no 3D model for {missing.join(", ")}, so{" "}
          {missing.length > 1 ? "they are" : "it is"} not drawn
        </span>
      )}
      <span className="hidden sm:inline">
        Drag to orbit · pinch or scroll to zoom · two-finger drag to pan
      </span>
    </div>
  );
}
