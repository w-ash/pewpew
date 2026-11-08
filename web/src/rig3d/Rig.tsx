import { useGLTF } from "@react-three/drei";
import { type ThreeEvent, useFrame } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  type BufferAttribute,
  type Color,
  type DataTexture,
  InstancedBufferAttribute,
  InstancedMesh,
  Matrix4,
  type Object3D,
  Points,
} from "three";
import type { Frame } from "../wire/protocol";
import type { WireStore } from "../wire/store";
import type { PartsCatalog } from "../rig/parts";
import { type Assembly, type AssemblyPart, readAssembly, variantAssembly } from "./assembly";
import { dragPreview } from "./dragPreview";
import { type AssemblyRef, assembliesFor, baseType, buildBatches, type InstanceBatch, type ViewRig } from "./instances";
import { createGlowMaterial, glowGeometry, glowPoints, placePoints, setGlowViewport } from "./ledGlow";
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

type Gltf = { scene: Object3D; userData?: Record<string, unknown> };

function assemblyOf(gltf: Gltf): Assembly {
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

/** What `drawnAssemblies` reads of a rig: each type placed, with its base type, dims, pixels and span.
 * Rigs with the same key, such as a `layout` that only moves fixtures, draw with the same assemblies. */
export function assembliesKey(rig: ViewRig): string {
  const types = new Set<string>();
  for (const f of rig.fixtures) {
    const dims = f.dims ? Object.entries(f.dims).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)) : null;
    types.add(JSON.stringify([f.type_id, baseType(f), dims, f.pixel_count, rig.types?.[f.type_id]?.span_m ?? null]));
  }
  return [...types].sort().join("\n");
}

interface Drawn {
  readonly key: string;
  readonly assemblies: Map<string, Assembly>;
  /** The ids of the assemblies made here (the variants'), whose geometry is freed here. */
  readonly made: readonly string[];
}

function drawnFor(key: string, rig: ViewRig, catalog: PartsCatalog, refs: AssemblyRef[], gltfs: Gltf[]): Drawn {
  const loaded = new Map<string, Assembly>();
  refs.forEach((r, i) => {
    if (gltfs[i]) loaded.set(r.id, assemblyOf(gltfs[i]));
  });
  const assemblies = drawnAssemblies(rig, catalog, loaded);
  return { key, assemblies, made: [...assemblies.keys()].filter((id) => !loaded.has(id)) };
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
  ) as unknown as Gltf[];
  // The assemblies follow the types placed, not the rig's identity: a `layout` that only moves fixtures
  // keeps every variant's geometry, so nothing is made or uploaded again.
  const drawnKey = `${catalog.digest ?? ""}|${refs.map((r) => r.url).join(",")}|${assembliesKey(rig)}`;
  const [drawn, setDrawn] = useState(() => drawnFor(drawnKey, rig, catalog, refs, gltfs));
  if (drawn.key !== drawnKey) setDrawn(drawnFor(drawnKey, rig, catalog, refs, gltfs));
  const assemblies = drawn.assemblies;
  // A variant's geometry is made here, so it is freed here; a GLB's stays in the loader's cache.
  useEffect(
    () => () => {
      for (const id of drawn.made) for (const p of drawn.assemblies.get(id)?.parts ?? []) p.geometry.dispose();
    },
    [drawn],
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
      <LedGlow batches={batches} assemblies={assemblies} texture={texture} selected={selected} />
    </>
  );
}

interface GlowProps {
  batches: readonly InstanceBatch[];
  assemblies: ReadonlyMap<string, Assembly>;
  texture: DataTexture;
  selected: ReadonlySet<number>;
}

/** Every pixel's glow sprite, over the meshes (ledGlow.ts). */
function LedGlow({ batches, assemblies, texture, selected }: GlowProps) {
  const points = useMemo(() => glowPoints(batches, assemblies), [batches, assemblies]);
  const material = useMemo(() => createGlowMaterial(texture), [texture]);
  useEffect(() => () => material.dispose(), [material]);
  const sprites = useMemo(() => {
    const object = new Points(glowGeometry(points), material);
    // Drawn after the meshes, which it reads the depth of; a drag moves it past its bounds.
    object.renderOrder = 1;
    object.frustumCulled = false;
    return object;
  }, [points, material]);
  useEffect(() => () => sprites.geometry.dispose(), [sprites]);

  useLayoutEffect(() => {
    const attr = sprites.geometry.getAttribute("aSelected") as BufferAttribute;
    for (let p = 0; p < points.count; p++) attr.array[p] = selected.has(points.fixture[p]!) ? 1 : 0;
    attr.needsUpdate = true;
    setOthersLevel(material, selected.size > 0 ? DIM_UNSELECTED : 1);
  }, [sprites, points, selected, material]);

  const seen = useRef(-1);
  useFrame(({ gl }) => {
    setGlowViewport(material, gl.domElement.height, gl.getPixelRatio());
    if (dragPreview.version === seen.current) return;
    seen.current = dragPreview.version;
    placePoints(points, batches, dragPreview.delta, dragPreview.fixtures);
    sprites.geometry.getAttribute("position").needsUpdate = true;
  });

  return <primitive object={sprites} />;
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

  // The mesh follows the part and the instance count: a new batch of the same size (a `layout` that
  // moves fixtures) only refills the instance data below, and the part's vertices are not uploaded again.
  const count = batch.count;
  const mesh = useMemo(() => {
    const geometry = part.geometry.clone();
    geometry.setAttribute("aRow", new InstancedBufferAttribute(new Float32Array(count), 1));
    geometry.setAttribute("aAxisY", new InstancedBufferAttribute(new Float32Array(count * 4), 4));
    geometry.setAttribute("aAxis", new InstancedBufferAttribute(new Float32Array(count * 3), 3));
    geometry.setAttribute("aSelected", new InstancedBufferAttribute(new Float32Array(count), 1));
    return new InstancedMesh(geometry, material, count);
  }, [part, material, count]);
  // R3F never disposes a <primitive>; the mesh's own dispose frees its instance buffer.
  useEffect(
    () => () => {
      mesh.geometry.dispose();
      mesh.dispose();
    },
    [mesh],
  );

  const scratch = useMemo(() => ({ base: new Matrix4(), out: new Matrix4() }), []);
  useLayoutEffect(() => {
    const g = mesh.geometry;
    for (const [name, data] of [["aRow", batch.rows], ["aAxisY", batch.axisY], ["aAxis", batch.axis]] as const) {
      const attr = g.getAttribute(name) as InstancedBufferAttribute;
      attr.array.set(data);
      attr.needsUpdate = true;
    }
    followDrag(mesh, batch, scratch);
    mesh.computeBoundingSphere();
    mesh.computeBoundingBox();
  }, [mesh, batch, scratch]);

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
