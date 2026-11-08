import { Button, ToggleButton } from "../design/Button";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { Segments } from "../design/Segments";
import type { SelectItem } from "../design/Select";
import { useMedia } from "../design/useMedia";
import { StatusBar } from "../status/StatusBar";
import { useConnectionText } from "../status/connection";
import { useFrameGap, useFrameValue, useWire, useWireContext } from "../wire/store";
import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useMemo, useState } from "react";
import type { PartsCatalog } from "../rig/parts";
import type { CompiledRig } from "../studio/api/types";
import { entityOf, fixturesOf, poseOf, setPose } from "../arrange/arrangement";
import { useDoc } from "../arrange/doc";
import { CameraRig, REDUCED_MOTION, SPIN_SPEED, useAccent, useCameraView, VIEW_ITEMS } from "./CameraRig";
import { Gizmo, type GizmoMode, type GizmoSpace, gizmoActivity } from "./Gizmo";
import { useModels } from "./models";
import { Rig } from "./Rig";
import { FOV, rigBounds, type ViewName } from "./views";

const GIZMO_ITEMS: readonly SelectItem[] = [
  { value: "translate", label: "Move" },
  { value: "rotate", label: "Rotate" },
];

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
  const readOnly = useDoc((s) => s.readOnly);
  const camera = useCameraView(rig);
  const [spin, setSpin] = useState(false);
  const [mode, setMode] = useState<GizmoMode>("translate");
  const [space, setSpace] = useState<GizmoSpace>("world");
  const still = useMedia(REDUCED_MOTION);
  const accent = useAccent();
  const bounds = useMemo(() => rigBounds(rig?.fixtures ?? []), [rig]);
  const models = useModels(rig, catalog);

  const selected = useMemo(
    () => new Set(fixturesOf(rig?.fixtures ?? [], selection)),
    [rig, selection],
  );
  const pose = selection ? poseOf(arrangement, selection, rig?.fixtures) : null;

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
          view={camera.view}
          bounds={bounds}
          generation={camera.generation}
          onUserMove={camera.release}
        />
        {/* A GLB that fails to load or parse takes only the rig down, not the canvas. */}
        <ErrorBoundary key={models.key} fallback={null} onError={models.onError}>
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
          value={camera.view ?? ""}
          onChange={(name) => camera.pick(name as ViewName)}
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
      <div className="studio-foot">
        <StatusBar planNote={null} />
        <StageStatus
          rig={rig}
          modelError={models.error}
          onRetry={models.retry}
          missing={models.missing}
        />
      </div>
    </div>
  );
}

export function StageStatus({
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
  const bound = useWire((s) => s.bound);
  const t = useFrameValue((f) => f?.t.toFixed(1) ?? null);
  const stalled = useFrameGap(true) > 0;
  return (
    <div className="studio-status t-caption">
      <span data-testid="stage-status">
        {down ??
          (!bound
            ? "binding…"
            : stalled
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
