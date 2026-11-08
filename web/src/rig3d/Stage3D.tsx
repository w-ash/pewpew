import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, use, useEffect, useMemo, useState } from "react";
import { Button, ToggleButton } from "../design/Button";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { Segments } from "../design/Segments";
import { useMedia, WIDE } from "../design/useMedia";
import { useWire, useWireContext, type WireStore } from "../wire/store";
import { asArrangement, entityOf, fixturesOf, poseOf, setPose } from "../arrange/arrangement";
import { useDoc } from "../arrange/doc";
import { GizmoToolbar, useGizmoTools } from "../arrange/gizmoTools";
import { useRigIsCurrent } from "../arrange/sync";
import type { Selection } from "../arrange/arrangement";
import { dragPreview, heldPose, presentOffsets } from "./dragPreview";
import { Gizmo, gizmoActivity } from "./Gizmo";
import { CameraRig, REDUCED_MOTION, SPIN_SPEED, useAccent, useCameraView, VIEW_ITEMS } from "./CameraRig";
import type { ViewRig } from "./instances";
import { loadParts } from "../rig/loadParts";
import { useModels } from "./models";
import { Rig } from "./Rig";
import { FOV, rigBounds, type ViewName } from "./views";

const NO_SELECTION: ReadonlySet<number> = new Set();

/** Commit the pose a drag of `selection` ended at. The view draws the editor's arrangement
 * (`useEditorPoses`), so the drag's own preview ends as it commits. */
export function commitDrag(selection: Selection, pose: Parameters<typeof setPose>[2]): void {
  const doc = useDoc.getState();
  doc.commit(setPose(doc.history.present, selection, pose));
  dragPreview.clear();
}

/** While `on`, draw each fixture at its pose in the editor's arrangement, not the engine's compile of
 * the last one it took: an edit, an undo or a redo shows at once, and the engine's echo changes nothing
 * on screen. Kept in step synchronously, so a drag's commit and the end of its preview land in one frame. */
function useEditorPoses(store: WireStore, on: boolean): void {
  useEffect(() => {
    if (!on) return;
    let seen: unknown[] = [];
    const update = () => {
      const state = store.getState();
      const present = useDoc.getState().history.present;
      const fixtures = state.map?.rig?.fixtures ?? null;
      const now = [fixtures, present, state.arrangement];
      if (now.every((v, i) => v === seen[i])) return;
      seen = now;
      dragPreview.offset(fixtures ? presentOffsets(fixtures, present, asArrangement(state.arrangement)) : null);
    };
    update();
    const offWire = store.subscribe(update);
    const offDoc = useDoc.subscribe(update);
    return () => {
      offWire();
      offDoc();
      dragPreview.offset(null);
    };
  }, [store, on]);
}

const noPick = () => {};

/** The rig in 3D, drawn from the engine's `rig` (`hello`, `layout`) and its frames, each fixture from its
 * type's assembly. Loaded only when the stage shows 3D (app/App.tsx), with three.js in its own files.
 * While `editing` (the layout panel's arrangement editor is open), each fixture is drawn at its pose in
 * the editor's arrangement, a press picks a fixture or group, and a gizmo moves or turns it: the dragged
 * fixtures follow the gizmo, and the pose commits on release. */
export default function Stage3D({ editing }: { editing: boolean }) {
  const { store } = useWireContext();
  const map = useWire((s) => s.map);
  const arrangement = useDoc((s) => s.history.present);
  const selection = useDoc((s) => (editing ? s.selection : null));
  const mode = useGizmoTools((s) => s.mode);
  const space = useGizmoTools((s) => s.space);
  const wide = useMedia(WIDE);
  useEditorPoses(store, editing);
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
  // An aimed fixture's pose made here when the engine has not compiled the editor's arrangement yet (an undo
  // in flight), so the gizmo stays on it.
  const pose = selection
    ? (poseOf(arrangement, selection, current ? (fixtures ?? []) : []) ?? heldPose(arrangement, selection))
    : null;
  const shown = editing && selection !== null && pose !== null;
  useEffect(() => {
    useGizmoTools.setState({ shown });
    return () => useGizmoTools.setState({ shown: false });
  }, [shown]);
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
        {shown && selection && pose && (
          <Gizmo
            pose={pose}
            fixtures={[...selected]}
            mode={mode}
            space={space}
            onCommit={(next) => commitDrag(selection, next)}
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
        {/* On a phone the layout panel holds the gizmo's tools, so they cover none of the small canvas. */}
        {shown && wide && <GizmoToolbar className="stage-veil" />}
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
