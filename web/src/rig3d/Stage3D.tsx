import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, use, useEffect, useMemo, useState } from "react";
import { Button, ToggleButton } from "../design/Button";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { Segments } from "../design/Segments";
import { useMedia } from "../design/useMedia";
import { useRefusal, useWire, useWireContext } from "../wire/store";
import { entityOf, fixturesOf, poseOf, setPose } from "../arrange/arrangement";
import { useDoc } from "../arrange/doc";
import { useRigIsCurrent } from "../arrange/sync";
import { dragPreview } from "./dragPreview";
import { Gizmo, type GizmoMode, type GizmoSpace, gizmoActivity } from "./Gizmo";
import type { SelectItem } from "../design/Select";
import { CameraRig, REDUCED_MOTION, SPIN_SPEED, useAccent, useCameraView, VIEW_ITEMS } from "./CameraRig";
import type { ViewRig } from "./instances";
import { loadParts } from "../rig/loadParts";
import { useModels } from "./models";
import { Rig } from "./Rig";
import { FOV, rigBounds, type ViewName } from "./views";

const NO_SELECTION: ReadonlySet<number> = new Set();
const noPick = () => {};
const GIZMO_ITEMS: readonly SelectItem[] = [
  { value: "translate", label: "Move" },
  { value: "rotate", label: "Rotate" },
];

/** The rig in 3D, drawn from the engine's `rig` (`hello`, `layout`) and its frames, each fixture from its
 * type's assembly. Loaded only when the stage shows 3D (app/App.tsx), with three.js in its own files.
 * While `editing` (the layout panel's arrangement editor is open), a press picks a fixture or group, and a
 * gizmo moves or turns it: the pose commits on release, and the dragged fixtures follow the gizmo until
 * the engine's next layout, or its refusal, draws them again. */
export default function Stage3D({ editing }: { editing: boolean }) {
  const { store } = useWireContext();
  const map = useWire((s) => s.map);
  const refusal = useRefusal("arrange");
  const arrangement = useDoc((s) => s.history.present);
  const selection = useDoc((s) => (editing ? s.selection : null));
  const [mode, setMode] = useState<GizmoMode>("translate");
  const [space, setSpace] = useState<GizmoSpace>("world");
  useEffect(() => dragPreview.clear(), [map, refusal]);
  const rig: ViewRig | null = useMemo(
    () => (map?.rig ? { n: map.n, total: map.total, fixtures: map.rig.fixtures, types: map.rig.types } : null),
    [map],
  );
  // A retry after a GLB failed fetches the catalog again: an engine upgraded under the page serves new
  // assemblies, maybe for the same catalog digest.
  const [partsTry, setPartsTry] = useState(0);
  const catalog = use(loadParts(`${map?.rig?.catalog_digest ?? ""}#${partsTry}`));
  const camera = useCameraView(rig);
  const [spin, setSpin] = useState(false);
  const still = useMedia(REDUCED_MOTION);
  const accent = useAccent();
  const bounds = useMemo(() => rigBounds(rig?.fixtures ?? []), [rig]);
  const models = useModels(rig, catalog, () => setPartsTry((n) => n + 1));
  const fixtures = map?.rig?.fixtures ?? null;
  const selected = useMemo(() => new Set(fixturesOf(fixtures ?? [], selection)), [fixtures, selection]);
  // A pose read from the engine's compile only while that is the compile of the editor's arrangement.
  const current = useRigIsCurrent();
  const pose = selection ? poseOf(arrangement, selection, current ? (fixtures ?? []) : []) : null;
  return (
    <div className="stage stage-3d">
      <Canvas
        dpr={[1, 2]}
        flat
        gl={{ antialias: true, alpha: true }}
        camera={{ fov: FOV, near: 0.01, far: 500, position: [6, 5, 6] }}
        role="img"
        aria-label="3D preview of the LEDs"
        onPointerMissed={() => {
          if (!editing || gizmoActivity.hovering || performance.now() - gizmoActivity.releasedAt < 300) return;
          useDoc.getState().select(null);
        }}
      >
        <OrbitControls makeDefault enableDamping dampingFactor={0.08} autoRotate={spin && !still} autoRotateSpeed={SPIN_SPEED} />
        <CameraRig view={camera.view} bounds={bounds} generation={camera.generation} onUserMove={camera.release} />
        {/* A GLB that fails to load or parse takes only the rig down, not the canvas. */}
        <ErrorBoundary key={models.key} fallback={null} onError={models.onError}>
          <Suspense fallback={null}>
            {rig && (
              <Rig
                rig={rig}
                frames={store}
                catalog={catalog}
                selected={editing ? selected : NO_SELECTION}
                accent={accent}
                onPick={
                  editing
                    ? (i) => {
                        const f = fixtures?.[i];
                        if (f) useDoc.getState().select(entityOf(useDoc.getState().history.present, f));
                      }
                    : noPick
                }
              />
            )}
          </Suspense>
        </ErrorBoundary>
        {editing && selection && pose && (
          <Gizmo
            pose={pose}
            fixtures={[...selected]}
            mode={mode}
            space={space}
            onCommit={(next) => {
              const doc = useDoc.getState();
              doc.commit(setPose(doc.history.present, selection, next));
            }}
          />
        )}
      </Canvas>
      {(models.error || models.missing.length > 0) && (
        <p className="stage-3d-note t-caption" role="alert">
          {models.error ? (
            <>
              Fixture models did not load: {models.error}{" "}
              <Button variant="tertiary" onPress={models.retry}>
                Retry
              </Button>
            </>
          ) : (
            `No 3D model for ${models.missing.join(", ")}, so ${models.missing.length > 1 ? "they are" : "it is"} not drawn`
          )}
        </p>
      )}
      <div className="stage-3d-controls">
        {editing && selection && (
          <>
            <Segments className="stage-veil" label="Gizmo" items={GIZMO_ITEMS} value={mode} onChange={(m) => setMode(m as GizmoMode)} />
            <ToggleButton
              className="stage-veil"
              variant="tertiary"
              pressed={space === "local"}
              onPressedChange={(local) => setSpace(local ? "local" : "world")}
              title="Gizmo axes"
            >
              {space === "world" ? "World" : "Local"}
            </ToggleButton>
          </>
        )}
        <Segments
          className="stage-veil"
          label="Camera view"
          items={VIEW_ITEMS}
          value={camera.view ?? ""}
          onChange={(name) => camera.pick(name as ViewName)}
        />
        <ToggleButton className="stage-veil" variant="tertiary" pressed={spin} onPressedChange={setSpin} title="Spin slowly">
          Spin
        </ToggleButton>
      </div>
    </div>
  );
}
