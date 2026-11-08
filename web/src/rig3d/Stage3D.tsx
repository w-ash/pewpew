import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, use, useMemo, useState } from "react";
import { Button, ToggleButton } from "../design/Button";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { Segments } from "../design/Segments";
import { useMedia } from "../design/useMedia";
import type { PartsCatalog } from "../rig/parts";
import { useWire, useWireContext } from "../wire/store";
import { CameraRig, REDUCED_MOTION, SPIN_SPEED, useAccent, useCameraView, VIEW_ITEMS } from "./CameraRig";
import type { ViewRig } from "./instances";
import { useModels } from "./models";
import { Rig } from "./Rig";
import { FOV, rigBounds, type ViewName } from "./views";

/** Where the engine serves the parts catalog, with each type's assembly URL (src/pewpew/sinks/preview.py). */
const PARTS_URL = "/parts.json";

let parts: Promise<PartsCatalog> | null = null;

/** The engine's parts catalog, fetched once a page; a failed fetch is tried again on the next read. */
function loadParts(): Promise<PartsCatalog> {
  parts ??= fetch(PARTS_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`the parts catalog answered ${r.status}`);
      return r.json() as Promise<PartsCatalog>;
    })
    .catch((e: unknown) => {
      parts = null;
      throw e;
    });
  return parts;
}

const NO_SELECTION: ReadonlySet<number> = new Set();
const noPick = () => {};

/** The rig in 3D, drawn from the engine's `rig` (`hello`, `layout`) and its frames, each fixture from its
 * type's assembly. Loaded only when the stage shows 3D (app/App.tsx), with three.js in its own files. */
export default function Stage3D() {
  const { store } = useWireContext();
  const map = useWire((s) => s.map);
  const rig: ViewRig | null = useMemo(
    () => (map?.rig ? { n: map.n, total: map.total, fixtures: map.rig.fixtures, types: map.rig.types } : null),
    [map],
  );
  const catalog = use(loadParts());
  const camera = useCameraView(rig);
  const [spin, setSpin] = useState(false);
  const still = useMedia(REDUCED_MOTION);
  const accent = useAccent();
  const bounds = useMemo(() => rigBounds(rig?.fixtures ?? []), [rig]);
  const models = useModels(rig, catalog);
  return (
    <div className="stage stage-3d">
      <Canvas
        dpr={[1, 2]}
        flat
        gl={{ antialias: true, alpha: true }}
        camera={{ fov: FOV, near: 0.01, far: 500, position: [6, 5, 6] }}
        role="img"
        aria-label="3D preview of the LEDs"
      >
        <OrbitControls makeDefault enableDamping dampingFactor={0.08} autoRotate={spin && !still} autoRotateSpeed={SPIN_SPEED} />
        <CameraRig view={camera.view} bounds={bounds} generation={camera.generation} onUserMove={camera.release} />
        {/* A GLB that fails to load or parse takes only the rig down, not the canvas. */}
        <ErrorBoundary key={models.key} fallback={null} onError={models.onError}>
          <Suspense fallback={null}>
            {rig && <Rig rig={rig} frames={store} catalog={catalog} selected={NO_SELECTION} accent={accent} onPick={noPick} />}
          </Suspense>
        </ErrorBoundary>
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
