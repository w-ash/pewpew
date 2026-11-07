import { useGLTF } from "@react-three/drei";
import { type ThreeEvent, useFrame } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import {
  type Color,
  type DataTexture,
  InstancedBufferAttribute,
  InstancedMesh,
  Matrix4,
  type Object3D,
} from "three";
import type { Catalog, CompiledRig } from "@/api/types";
import { type Assembly, type AssemblyPart, readAssembly } from "./assembly";
import { dragPreview } from "./dragPreview";
import { frameBus } from "./frameBus";
import { assembliesFor, buildBatches, type InstanceBatch } from "./instances";
import { createLedMaterial } from "./ledMaterial";
import {
  createLedTexture,
  type LedLayout,
  ledLayout,
  uploadFrame,
} from "./ledTexture";

const assemblyCache = new WeakMap<object, Assembly>();

/** Glow scale for fixtures outside the selection, while one exists. */
const DIM_UNSELECTED = 0.3;

function assemblyOf(gltf: {
  scene: Object3D;
  userData?: Record<string, unknown>;
}): Assembly {
  let a = assemblyCache.get(gltf);
  if (!a) {
    a = readAssembly(gltf);
    assemblyCache.set(gltf, a);
  }
  return a;
}

function layoutKey(layout: LedLayout): string {
  return `${layout.width}x${layout.height}:${layout.rows.map((r) => `${r.start}+${r.count}`).join(",")}`;
}

export interface RigProps {
  rig: CompiledRig;
  catalog: Catalog;
  selected: ReadonlySet<number>;
  accent: Color;
  onPick: (fixtureIndex: number) => void;
}

export function Rig({ rig, catalog, selected, accent, onPick }: RigProps) {
  const refs = useMemo(() => assembliesFor(rig, catalog), [rig, catalog]);
  const gltfs = useGLTF(
    refs.map((r) => r.url),
    false,
    false,
  ) as unknown as Array<{
    scene: Object3D;
    userData?: Record<string, unknown>;
  }>;
  const assemblies = useMemo(() => {
    const map = new Map<string, Assembly>();
    refs.forEach((r, i) => {
      if (gltfs[i]) map.set(r.id, assemblyOf(gltfs[i]));
    });
    return map;
  }, [refs, gltfs]);

  const layout = useMemo(() => ledLayout(rig.fixtures, rig.n), [rig]);
  const key = layoutKey(layout);
  // biome-ignore lint/correctness/useExhaustiveDependencies: the texture follows the layout's shape, not its identity.
  const texture = useMemo(() => {
    const t = createLedTexture(layout);
    const f = frameBus.frame;
    if (f) uploadFrame(t, layout, f.rgb);
    return t;
  }, [key]);
  useEffect(() => () => texture.dispose(), [texture]);

  const batches = useMemo(
    () => buildBatches(rig, assemblies),
    [rig, assemblies],
  );
  // A new compile carries the dragged pose, so the preview has done its job.
  // biome-ignore lint/correctness/useExhaustiveDependencies: runs on each new rig.
  useEffect(() => {
    dragPreview.clear();
  }, [rig]);

  const seen = useRef(-1);
  useFrame(() => {
    if (frameBus.version === seen.current) return;
    seen.current = frameBus.version;
    const f = frameBus.frame;
    if (f) uploadFrame(texture, layout, f.rgb);
  });

  return (
    <>
      {batches.flatMap((batch) =>
        (assemblies.get(batch.id)?.parts ?? []).map((part, i) => (
          <PartInstances
            // biome-ignore lint/suspicious/noArrayIndexKey: parts are fixed per assembly.
            key={`${batch.id}:${i}`}
            batch={batch}
            part={part}
            texture={texture}
            selected={selected}
            accent={accent}
            onPick={onPick}
          />
        )),
      )}
    </>
  );
}

interface PartProps {
  batch: InstanceBatch;
  part: AssemblyPart;
  texture: DataTexture;
  selected: ReadonlySet<number>;
  accent: Color;
  onPick: (fixtureIndex: number) => void;
}

function PartInstances({
  batch,
  part,
  texture,
  selected,
  accent,
  onPick,
}: PartProps) {
  const material = useMemo(
    () => createLedMaterial(part.glow, part.gain, texture, accent),
    [part, texture, accent],
  );
  useEffect(() => () => material.dispose(), [material]);

  const mesh = useMemo(() => {
    const geometry = part.geometry.clone();
    geometry.setAttribute("aRow", new InstancedBufferAttribute(batch.rows, 1));
    geometry.setAttribute(
      "aAxisY",
      new InstancedBufferAttribute(batch.axisY, 4),
    );
    geometry.setAttribute("aAxis", new InstancedBufferAttribute(batch.axis, 3));
    geometry.setAttribute(
      "aSelected",
      new InstancedBufferAttribute(new Float32Array(batch.count), 1),
    );
    const m = new InstancedMesh(geometry, material, batch.count);
    m.instanceMatrix.array.set(batch.matrices);
    m.instanceMatrix.needsUpdate = true;
    m.computeBoundingSphere();
    m.computeBoundingBox();
    return m;
  }, [batch, part, material]);
  // R3F never disposes a <primitive>; the mesh's own dispose frees its instance buffer.
  useEffect(
    () => () => {
      mesh.geometry.dispose();
      mesh.dispose();
    },
    [mesh],
  );

  useLayoutEffect(() => {
    const attr = mesh.geometry.getAttribute(
      "aSelected",
    ) as InstancedBufferAttribute;
    for (let k = 0; k < batch.count; k++) {
      attr.array[k] = selected.has(batch.fixtureIndex[k]) ? 1 : 0;
    }
    attr.needsUpdate = true;
    material.uniforms.uOthers.value = selected.size > 0 ? DIM_UNSELECTED : 1;
  }, [mesh, batch, selected, material]);

  const seen = useRef(-1);
  const scratch = useMemo(
    () => ({ base: new Matrix4(), out: new Matrix4() }),
    [],
  );
  useFrame(() => {
    if (dragPreview.version === seen.current) return;
    seen.current = dragPreview.version;
    const { delta, fixtures } = dragPreview;
    const array = mesh.instanceMatrix.array as Float32Array;
    for (let k = 0; k < batch.count; k++) {
      if (delta && fixtures.has(batch.fixtureIndex[k])) {
        scratch.base.fromArray(batch.matrices, k * 16);
        scratch.out
          .multiplyMatrices(delta, scratch.base)
          .toArray(array, k * 16);
      } else {
        array.set(batch.matrices.subarray(k * 16, k * 16 + 16), k * 16);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
  });

  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 4 || e.instanceId === undefined) return;
    e.stopPropagation();
    onPick(batch.fixtureIndex[e.instanceId]);
  };

  // biome-ignore lint/a11y/noStaticElementInteractions: a three.js object, not a DOM element.
  return <primitive object={mesh} onClick={onClick} />;
}
