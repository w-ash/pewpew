import { useGLTF } from "@react-three/drei";
import { type ThreeEvent, useFrame } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  type Color,
  type DataTexture,
  InstancedBufferAttribute,
  InstancedMesh,
  Matrix4,
  type Object3D,
} from "three";
import type { Frame } from "../wire/protocol";
import type { WireStore } from "../wire/store";
import type { PartsCatalog } from "../rig/parts";
import { type Assembly, type AssemblyPart, readAssembly, variantAssembly } from "./assembly";
import { dragPreview } from "./dragPreview";
import { assembliesFor, baseType, buildBatches, type InstanceBatch, type ViewRig } from "./instances";
import { createLedMaterial, setOthersLevel } from "./ledMaterial";
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

/** Moves the batch's dragged fixtures by the drag preview's delta, and puts the rest at their compiled poses. */
function followDrag(mesh: InstancedMesh, batch: InstanceBatch, scratch: { base: Matrix4; out: Matrix4 }) {
  const { delta, fixtures } = dragPreview;
  const array = mesh.instanceMatrix.array as Float32Array;
  for (let k = 0; k < batch.count; k++) {
    if (delta && fixtures.has(batch.fixtureIndex[k]!)) {
      scratch.base.fromArray(batch.matrices, k * 16);
      scratch.out.multiplyMatrices(delta, scratch.base).toArray(array, k * 16);
    } else {
      array.set(batch.matrices.subarray(k * 16, k * 16 + 16), k * 16);
    }
  }
  mesh.instanceMatrix.needsUpdate = true;
}

/** A texture for `layout`, holding the latest frame. */
function textureFor(layout: LedLayout, frames: WireStore) {
  const texture = createLedTexture(layout);
  const f = frames.getFrame();
  if (f) uploadFrame(texture, layout, f.rgb);
  return texture;
}

function layoutKey(layout: LedLayout): string {
  return `${layout.width}x${layout.height}:${layout.rows.map((r) => `${r.start}+${r.count}`).join(",")}`;
}

/** A dim of a catalog type, from its `{"v"}` fact; null when it has none. */
function catalogDim(catalog: PartsCatalog, typeId: string, name: string): number | null {
  const dims = catalog.fixture_types.find((t) => t.id === typeId)?.dims;
  const fact = dims && typeof dims === "object" ? (dims as Record<string, unknown>)[name] : undefined;
  const v = fact && typeof fact === "object" && "v" in fact ? fact.v : undefined;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/**
 * The assembly each fixture type of `rig` is drawn with, keyed by `type_id`, with each attachment type's:
 * a base type's own, and a dims variant's made from its base type's (`variantAssembly`). The variant's
 * pixel span is the rig's (`types`), else its pitch times its pixels; it stretches by its `length` over
 * the base type's, else by its span over the base type's.
 */
export function drawnAssemblies(
  rig: ViewRig,
  catalog: PartsCatalog,
  loaded: ReadonlyMap<string, Assembly>,
): Map<string, Assembly> {
  const out = new Map(loaded);
  for (const f of rig.fixtures) {
    const base = baseType(f);
    const from = loaded.get(base);
    if (f.type_id === base || out.has(f.type_id) || !from?.pixelAxis) continue;
    const pitch = f.dims?.pitch;
    const span = rig.types?.[f.type_id]?.span_m ?? (pitch ? pitch * f.pixel_count : from.pixelAxis.span);
    const length = f.dims?.length;
    const baseLength = catalogDim(catalog, base, "length");
    const stretch = length && baseLength ? length / baseLength : span / from.pixelAxis.span;
    out.set(f.type_id, variantAssembly(from, f.pixel_count, span, stretch));
  }
  return out;
}

interface RigProps {
  rig: ViewRig;
  /** Where the newest frame is read, each animation frame. */
  frames: WireStore;
  catalog: PartsCatalog;
  selected: ReadonlySet<number>;
  accent: Color;
  onPick: (fixtureIndex: number) => void;
}

export function Rig({ rig, frames, catalog, selected, accent, onPick }: RigProps) {
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
    return drawnAssemblies(rig, catalog, map);
  }, [rig, catalog, refs, gltfs]);
  // A variant's geometry is made here, so it is freed here; a GLB's stays in the loader's cache.
  useEffect(
    () => () => {
      for (const [id, a] of assemblies) if (!refs.some((r) => r.id === id)) for (const p of a.parts) p.geometry.dispose();
    },
    [assemblies, refs],
  );

  const layout = useMemo(() => ledLayout(rig.fixtures, rig.n, rig.total ?? rig.n), [rig]);
  // The texture follows the layout's shape, not its identity: a new compile of the same shape keeps it.
  const key = layoutKey(layout);
  const [shaped, setShaped] = useState(() => ({ key, texture: textureFor(layout, frames) }));
  if (shaped.key !== key) setShaped({ key, texture: textureFor(layout, frames) });
  const texture = shaped.texture;
  useEffect(() => () => texture.dispose(), [texture]);

  const batches = useMemo(
    () => buildBatches(rig, assemblies),
    [rig, assemblies],
  );
  const seen = useRef<Frame | null>(null);
  // A new texture starts empty: the frame it would show has not been seen by it.
  const seenKey = useRef(key);
  useFrame(() => {
    const f = frames.getFrame();
    if (seenKey.current !== key) {
      seenKey.current = key;
      seen.current = null;
    }
    if (f === seen.current) return;
    seen.current = f;
    if (f) uploadFrame(texture, layout, f.rgb);
  });

  return (
    <>
      {batches.flatMap((batch) =>
        (assemblies.get(batch.id)?.parts ?? []).map((part, i) => (
          <PartInstances
            // The index is the key: parts are fixed per assembly.
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
      attr.array[k] = selected.has(batch.fixtureIndex[k]!) ? 1 : 0;
    }
    attr.needsUpdate = true;
    setOthersLevel(material, selected.size > 0 ? DIM_UNSELECTED : 1);
  }, [mesh, batch, selected, material]);

  const seen = useRef(-1);
  const scratch = useMemo(
    () => ({ base: new Matrix4(), out: new Matrix4() }),
    [],
  );
  useFrame(() => {
    if (dragPreview.version === seen.current) return;
    seen.current = dragPreview.version;
    followDrag(mesh, batch, scratch);
  });

  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 4 || e.instanceId === undefined) return;
    e.stopPropagation();
    onPick(batch.fixtureIndex[e.instanceId]!);
  };

  return <primitive object={mesh} onClick={onClick} />;
}
