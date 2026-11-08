/**
 * Draws one quad with the studio's LED material over a known texture row and
 * reads the canvas back, for e2e/color.spec.ts. Served by Vite dev only; it
 * is not a build input.
 */
import {
  Color,
  InstancedBufferAttribute,
  InstancedMesh,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  WebGLRenderer,
} from "three";
import type { Glow } from "../../src/rig3d/assembly";
import { createLedMaterial } from "../../src/rig3d/ledMaterial";
import { createLedTexture, fillLedData, ledLayout } from "../../src/rig3d/ledTexture";

export const BYTES = [
  [10, 20, 30],
  [128, 64, 200],
  [250, 5, 128],
  [77, 177, 233],
];

// 4 × 101 puts each texel center on a pixel center (50.5, 151.5, …).
const SIZE = 404;

function draw(glow: Glow): number[][] {
  const renderer = new WebGLRenderer({
    preserveDrawingBuffer: true,
    antialias: false,
  });
  renderer.setPixelRatio(1);
  renderer.setSize(SIZE, SIZE);
  document.body.appendChild(renderer.domElement);

  const n = BYTES.length;
  const layout = ledLayout(
    [{ pixel_start: 0, pixel_count: n }],
    n,
  );
  const texture = createLedTexture(layout);
  fillLedData(
    texture.image.data as Uint8Array,
    layout,
    Uint8Array.from(BYTES.flat()),
  );
  texture.needsUpdate = true;

  const geometry = new PlaneGeometry(1, 1);
  geometry.setAttribute(
    "aRow",
    new InstancedBufferAttribute(new Float32Array([0]), 1),
  );
  geometry.setAttribute(
    "aAxisY",
    new InstancedBufferAttribute(new Float32Array([0, 1, 0, 0]), 4),
  );
  geometry.setAttribute(
    "aAxis",
    new InstancedBufferAttribute(new Float32Array([-0.5, 1, n]), 3),
  );
  geometry.setAttribute(
    "aSelected",
    new InstancedBufferAttribute(new Float32Array([0]), 1),
  );
  const material = createLedMaterial(glow, 1, texture, new Color(1, 1, 1));
  const mesh = new InstancedMesh(geometry, material, 1);

  // Far and narrow, so |n·v| stays within 1e-5 of 1 across the quad.
  const camera = new PerspectiveCamera(0.5, 1, 1, 1000);
  camera.position.set(0, 0, 1 / (2 * Math.tan((0.25 * Math.PI) / 180)));
  const scene = new Scene();
  scene.add(mesh);
  renderer.render(scene, camera);

  const gl = renderer.getContext();
  const out: number[][] = [];
  for (let i = 0; i < n; i++) {
    // Texel i's center is at y = -0.5 + (i + 0.5)/n; the quad fills the canvas.
    const y = Math.floor(((i + 0.5) / n) * SIZE);
    const px = new Uint8Array(4);
    gl.readPixels(SIZE / 2, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    out.push([...px.subarray(0, 3)]);
  }
  return out;
}

(window as unknown as { colorCheck: unknown }).colorCheck = {
  expected: BYTES,
  pixels: draw("pixels"),
  nearest: draw("pixel_nearest"),
};
