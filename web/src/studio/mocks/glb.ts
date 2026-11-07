/**
 * Stand-in assembly GLBs for the mock server, built from three.js
 * primitives and written with GLTFExporter. Each part carries the `extras`
 * the real GLBs carry (docs/studio/contracts.md, "Geometry"); sizes follow
 * the bar dimensions in docs/studio/domain-model.md §2 loosely.
 */
import {
  BoxGeometry,
  type BufferGeometry,
  ConeGeometry,
  CylinderGeometry,
  ExtrudeGeometry,
  Mesh,
  MeshBasicMaterial,
  Path,
  Scene,
  Shape,
} from "three";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";

const DIFFUSER_R = 0.0151;
const AXIS_Z = 0.0304;
const FLAT_Z = 0.0119;
const ATTACH_LEN = 0.1;
const material = new MeshBasicMaterial();

function part(
  name: string,
  geometry: BufferGeometry,
  glow: string,
  gain = 1,
): Mesh {
  const mesh = new Mesh(geometry, material);
  mesh.name = name;
  mesh.userData = { glow, gain };
  return mesh;
}

function bar(): Scene {
  const scene = new Scene();
  scene.userData = { pixel_axis: { y0: -0.5, span: 1, count: 64 } };
  const housingH = AXIS_Z - FLAT_Z;
  const housing = new BoxGeometry(0.018, 0.992, housingH);
  housing.translate(0, 0, -(AXIS_Z + FLAT_Z) / 2);
  const capA = new BoxGeometry(0.018, 0.004, housingH);
  capA.translate(0, -0.498, -(AXIS_Z + FLAT_Z) / 2);
  const capB = capA.clone().translate(0, 0.996, 0);
  scene.add(
    part("housing", housing, "none"),
    part("cap_a", capA, "none"),
    part("cap_b", capB, "none"),
    part(
      "diffuser",
      new CylinderGeometry(DIFFUSER_R, DIFFUSER_R, 1, 32),
      "pixels",
      1,
    ),
  );
  return scene;
}

function point(): Scene {
  const scene = new Scene();
  const cone = new ConeGeometry(DIFFUSER_R, ATTACH_LEN, 32);
  cone.translate(0, ATTACH_LEN / 2, 0);
  scene.add(part("cone", cone, "pixels", 0.25));
  return scene;
}

/** The prototype's flattened eye with a slot (docs/studio/prototype/golden-tubes-3d.html:354-378), in meters. */
function eye(): Scene {
  const scene = new Scene();
  const bevel = 0.003;
  const thick = 0.014;
  const w = DIFFUSER_R - bevel;
  const tip = ATTACH_LEN - bevel - w;
  const outline = new Shape();
  outline.moveTo(-w, 0);
  outline.lineTo(w, 0);
  outline.lineTo(w, tip);
  outline.absarc(0, tip, w, 0, Math.PI, false);
  outline.lineTo(-w, 0);
  const sw = 0.004;
  const s0 = 0.035;
  const s1 = tip - 0.01;
  const slot = new Path();
  slot.moveTo(sw, s0);
  slot.lineTo(sw, s1);
  slot.absarc(0, s1, sw, 0, Math.PI, false);
  slot.lineTo(-sw, s0);
  slot.absarc(0, s0, sw, Math.PI, Math.PI * 2, false);
  outline.holes.push(slot);
  const blade = new ExtrudeGeometry(outline, {
    depth: thick,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 2,
    curveSegments: 16,
  });
  blade.translate(0, 0, -thick / 2);
  const collar = new CylinderGeometry(DIFFUSER_R, DIFFUSER_R, 0.02, 32);
  collar.translate(0, 0.01, 0);
  scene.add(
    part("collar", collar, "pixels", 0.25),
    part("blade", blade, "pixels", 0.25),
  );
  return scene;
}

const BUILDERS: Record<string, () => Scene> = {
  "mock-bar": bar,
  "mock-point": point,
  "mock-eye": eye,
};

const cache = new Map<string, Promise<ArrayBuffer>>();

export function mockGlb(digest: string): Promise<ArrayBuffer> | null {
  const build = BUILDERS[digest];
  if (!build) return null;
  let glb = cache.get(digest);
  if (!glb) {
    glb = new GLTFExporter().parseAsync(build(), {
      binary: true,
    }) as Promise<ArrayBuffer>;
    cache.set(digest, glb);
  }
  return glb;
}
