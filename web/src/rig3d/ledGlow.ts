/**
 * The LEDs' glow: one point sprite per pixel of every fixture, over the meshes, so a lit LED reads at
 * any distance.
 *
 * A pixel's mesh is drawn at its true size, so a 5 mm LED seen across a room covers less than a screen
 * pixel. Its sprite has a core of at least `CORE_MIN` css px across, the 2D view's smallest dot
 * (`DOT_MIN` in room/layout.ts), and a Gaussian halo of `GLOW` css px around it, as the 2D view blurs
 * its dots (stage/draw.ts). three's PointsMaterial gives a point a size in pixels, or one shrunk by
 * camera depth (`sizeAttenuation`, https://threejs.org/docs/pages/PointsMaterial.html), but not the
 * larger of the two, so this shader sizes them: the core is the LED's projected width or the minimum,
 * whichever is larger, and the sprite fades out as the projected width grows from one to two
 * minimums. Close up only the meshes draw, at their true size.
 *
 * The falloff applies after the sRGB encode, in display space, as the 2D canvas's blur does, so a texel
 * shows its byte at the core, as the meshes do (ledMaterial.ts). Sprites blend by `max`, as the 2D
 * view's dots `lighten`: overlapping halos of a dense strip never sum past the brightest LED's color,
 * and a black LED leaves what is under it. One draw call of a few thousand small points, with no
 * full-screen pass: three's bloom draws the bright parts into a half-float target and blurs a chain
 * of mip targets every frame (https://threejs.org/docs/pages/UnrealBloomPass.html, and its source,
 * examples/jsm/postprocessing/UnrealBloomPass.js), which a phone pays for at screen resolution.
 */
import {
  BufferAttribute,
  BufferGeometry,
  CustomBlending,
  type DataTexture,
  Matrix4,
  MaxEquation,
  ShaderMaterial,
  Vector3,
} from "three";
import type { Assembly } from "./assembly";
import type { InstanceBatch } from "./instances";

/** The smallest core, in css px: the 2D view's smallest dot diameter (2 × `DOT_MIN`). */
export const CORE_MIN = 3;
/** The halo's Gaussian sigma, in css px. */
export const GLOW = 1.5;
/** The halo's peak, as a fraction of the LED's display value. */
export const HALO = 0.5;

/** Every fixture pixel as a point: where it is in its fixture's frame and in the world, the texel it takes
 * its color from, and how wide its light is. */
export interface GlowPoints {
  readonly count: number;
  /** Local (fixture-frame) position of each point, xyz. */
  readonly local: Float32Array;
  /** World position of each point, xyz: `local` under its fixture's matrix. */
  readonly world: Float32Array;
  /** Texture column and row of each point. */
  readonly texel: Float32Array;
  /** Width of each point's light, meters: its type's glowing parts across. */
  readonly width: Float32Array;
  /** Index into `rig.fixtures` of each point. */
  readonly fixture: Int32Array;
  /** The batch and the instance in it of each point, whose matrix places it. */
  readonly batchOf: Int32Array;
  readonly instanceOf: Int32Array;
}

/** The width of a type's light: the widest x extent of its glowing parts, 0 when none glows. */
export function lightWidth(assembly: Assembly | undefined): number {
  let w = 0;
  for (const part of assembly?.parts ?? []) {
    if (part.glow === "none") continue;
    part.geometry.computeBoundingBox();
    const box = part.geometry.boundingBox;
    if (box) w = Math.max(w, box.max.x - box.min.x);
  }
  return w;
}

/** One point per pixel of each fixture batch, at its pixel's centre on the fixture's axis (local x = z = 0,
 * the diffuser axis: docs/studio/domain-model.md §3). Attachment batches have no points of their own. */
export function glowPoints(batches: readonly InstanceBatch[], assemblies: ReadonlyMap<string, Assembly>): GlowPoints {
  const fixtures = batches.map((b, i) => [b, i] as const).filter(([b]) => b.kind === "fixture");
  let count = 0;
  for (const [b] of fixtures) for (let k = 0; k < b.count; k++) count += Math.max(0, Math.round(b.axis[k * 3 + 2]!));
  const out: GlowPoints = {
    count,
    local: new Float32Array(count * 3),
    world: new Float32Array(count * 3),
    texel: new Float32Array(count * 2),
    width: new Float32Array(count),
    fixture: new Int32Array(count),
    instanceOf: new Int32Array(count),
    batchOf: new Int32Array(count),
  };
  let p = 0;
  for (const [b, bi] of fixtures) {
    const width = lightWidth(assemblies.get(b.id));
    for (let k = 0; k < b.count; k++) {
      const y0 = b.axis[k * 3]!, span = b.axis[k * 3 + 1]!, n = Math.max(0, Math.round(b.axis[k * 3 + 2]!));
      for (let j = 0; j < n; j++, p++) {
        out.local[p * 3 + 1] = y0 + ((j + 0.5) * span) / n;
        out.texel[p * 2] = j;
        out.texel[p * 2 + 1] = b.rows[k]!;
        out.width[p] = width;
        out.fixture[p] = b.fixtureIndex[k]!;
        out.instanceOf[p] = k;
        out.batchOf[p] = bi;
      }
    }
  }
  placePoints(out, batches, null, new Set());
  return out;
}

const m = new Matrix4();
const v = new Vector3();

/** Writes each point's world position from its batch's matrices, each fixture moved by its entry in
 * `offsets`, then by `delta` for `moved` fixtures (a drag in progress, dragPreview.ts). */
export function placePoints(
  points: GlowPoints,
  batches: readonly InstanceBatch[],
  delta: Matrix4 | null,
  moved: ReadonlySet<number>,
  offsets: ReadonlyMap<number, Matrix4> | null = null,
): void {
  for (let p = 0; p < points.count; p++) {
    const b = batches[points.batchOf[p]!]!;
    m.fromArray(b.matrices, points.instanceOf[p]! * 16);
    const offset = offsets?.get(points.fixture[p]!);
    if (offset) m.premultiply(offset);
    if (delta && moved.has(points.fixture[p]!)) m.premultiply(delta);
    v.fromArray(points.local, p * 3).applyMatrix4(m).toArray(points.world, p * 3);
  }
}

/** The points' geometry; `aSelected` is 1 for a point of a selected fixture. */
export function glowGeometry(points: GlowPoints): BufferGeometry {
  const g = new BufferGeometry();
  g.setAttribute("position", new BufferAttribute(points.world, 3));
  g.setAttribute("aTexel", new BufferAttribute(points.texel, 2));
  g.setAttribute("aWidth", new BufferAttribute(points.width, 1));
  g.setAttribute("aSelected", new BufferAttribute(new Float32Array(points.count), 1));
  g.computeBoundingSphere();
  return g;
}

const vertexShader = /* glsl */ `
uniform sampler2D uLeds;
uniform float uHeight;
uniform float uCore;
uniform float uGlow;
attribute vec2 aTexel;
attribute float aWidth;
attribute float aSelected;

varying vec3 vLed;
varying float vCore;
varying float vSize;
varying float vFade;
varying float vSelected;

void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  float dist = max(-mv.z, 1e-4);
  // The light's width in drawing-buffer pixels.
  float s = aWidth * projectionMatrix[1][1] * 0.5 * uHeight / dist;
  vFade = 1.0 - smoothstep(uCore, 2.0 * uCore, s);
  vCore = max(uCore, s);
  vSize = vCore + 6.0 * uGlow;
  vSelected = aSelected;
  vLed = texelFetch(uLeds, ivec2(aTexel), 0).rgb;
  // In front of its own fixture's surface, so the fixture's mesh does not hide it.
  mv.xyz += normalize(-mv.xyz) * aWidth;
  gl_Position = projectionMatrix * mv;
  gl_PointSize = vFade > 0.0 && max(vLed.r, max(vLed.g, vLed.b)) > 0.0 ? vSize : 0.0;
}
`;

const fragmentShader = /* glsl */ `
uniform float uGlow;
uniform float uHalo;
uniform float uOthers;

varying vec3 vLed;
varying float vCore;
varying float vSize;
varying float vFade;
varying float vSelected;

void main() {
  float d = length(gl_PointCoord - 0.5) * vSize;
  float rc = 0.5 * vCore;
  float core = 1.0 - smoothstep(rc - 0.5, rc + 0.5, d);
  float x = max(d - rc, 0.0) / uGlow;
  float halo = uHalo * exp(-0.5 * x * x);
  float level = max(core, halo) * vFade * mix(uOthers, 1.0, vSelected);
  if (level < 0.002) discard;
  gl_FragColor = vec4(vLed, 1.0);
  #include <colorspace_fragment>
  gl_FragColor.rgb *= level;
  gl_FragColor.a = max(gl_FragColor.r, max(gl_FragColor.g, gl_FragColor.b));
}
`;

/** The sprites' material. `setGlowViewport` gives it the drawing buffer's height and pixel ratio. */
export function createGlowMaterial(texture: DataTexture): ShaderMaterial {
  return new ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uLeds: { value: texture },
      uHeight: { value: 1 },
      uCore: { value: CORE_MIN },
      uGlow: { value: GLOW },
      uHalo: { value: HALO },
      uOthers: { value: 1 },
    },
    transparent: true,
    depthWrite: false,
    blending: CustomBlending,
    blendEquation: MaxEquation,
    blendEquationAlpha: MaxEquation,
    toneMapped: false,
  });
}

/** Sizes the sprites for a drawing buffer `height` device px tall at `dpr` device px per css px. */
export function setGlowViewport(material: ShaderMaterial, height: number, dpr: number): void {
  material.uniforms.uHeight!.value = height;
  material.uniforms.uCore!.value = CORE_MIN * dpr;
  material.uniforms.uGlow!.value = GLOW * dpr;
}
