/**
 * The material for every GLB part, by the part's `glow`.
 *
 * - `pixels`: the fixture's texture row sampled with linear filtering at
 *   u = (y − y0)/span along the host axis, clamped to the end texel centers.
 * - `pixel_nearest`: the one texel the fragment's pixel falls in.
 * - `none`: a dark housing lit by a fixed hemisphere term.
 *
 * While something is selected, the other fixtures' glow scales by
 * `uOthers` so the selection stands out.
 *
 * Lit parts are self-lit and dim toward their silhouette by
 * mix(0.6, 1.0, |n·v|), as the prototype does
 * (docs/studio/prototype/golden-tubes-3d.html:338). `toneMapped: false` and
 * the `colorspace_fragment` chunk make the sRGB encode on output the only
 * transfer applied, so a texel center at gain 1 facing the camera shows its
 * byte unchanged. ShaderMaterial must do its own output conversion
 * (https://threejs.org/manual/pages/color-management.html); e2e/color.spec.ts
 * reads the bytes back.
 */
import { Color, type DataTexture, ShaderMaterial } from "three";
import type { Glow } from "./assembly";

const vertexShader = /* glsl */ `
attribute float aRow;
attribute vec4 aAxisY;
attribute vec3 aAxis;
attribute float aSelected;

varying float vHostY;
varying float vRow;
varying vec3 vAxis;
varying float vSelected;
varying vec3 vNormalView;
varying vec3 vViewDir;
varying float vUp;

void main() {
  vec4 local = vec4(position, 1.0);
  vHostY = dot(aAxisY, local);
  vRow = aRow;
  vAxis = aAxis;
  vSelected = aSelected;
  mat3 rot = mat3(instanceMatrix);
  vec4 mv = modelViewMatrix * instanceMatrix * local;
  vNormalView = normalize(normalMatrix * rot * normal);
  vUp = normalize(mat3(modelMatrix) * rot * normal).y;
  vViewDir = -mv.xyz;
  gl_Position = projectionMatrix * mv;
}
`;

const fragmentShader = /* glsl */ `
uniform sampler2D uLeds;
uniform vec2 uLedSize;
uniform float uGain;
uniform vec3 uHousing;
uniform vec3 uSky;
uniform vec3 uGround;
uniform vec3 uAccent;
uniform float uOthers;

varying float vHostY;
varying float vRow;
varying vec3 vAxis;
varying float vSelected;
varying vec3 vNormalView;
varying vec3 vViewDir;
varying float vUp;

void main() {
  float facing = abs(dot(normalize(vNormalView), normalize(vViewDir)));
#if defined(GLOW_NONE)
  vec3 color = uHousing * mix(uGround, uSky, 0.5 * vUp + 0.5) * mix(0.75, 1.0, facing);
  color = mix(color, uAccent, 0.5 * vSelected);
#else
  float count = max(vAxis.z, 1.0);
  float u = (vHostY - vAxis.x) / max(vAxis.y, 1e-6);
  #if defined(GLOW_NEAREST)
    int i = int(clamp(floor(u * count), 0.0, count - 1.0));
    vec3 led = texelFetch(uLeds, ivec2(i, int(vRow + 0.5)), 0).rgb;
  #else
    float x = clamp(u * count, 0.5, count - 0.5);
    vec3 led = texture2D(uLeds, vec2(x / uLedSize.x, (vRow + 0.5) / uLedSize.y)).rgb;
  #endif
  vec3 color = led * uGain * mix(0.6, 1.0, facing) * mix(uOthers, 1.0, vSelected);
#endif
  gl_FragColor = vec4(color, 1.0);
  #include <colorspace_fragment>
}
`;

/** Linear-light values for the unlit look; picked by eye against the stage surface. */
const HOUSING = new Color(0.05, 0.055, 0.065);
const SKY = new Color(1, 1, 1);
const GROUND = new Color(0.25, 0.25, 0.28);

export function createLedMaterial(
  glow: Glow,
  gain: number,
  texture: DataTexture,
  accent: Color,
): ShaderMaterial {
  const define =
    glow === "none"
      ? "GLOW_NONE"
      : glow === "pixel_nearest"
        ? "GLOW_NEAREST"
        : "GLOW_PIXELS";
  return new ShaderMaterial({
    vertexShader,
    fragmentShader,
    defines: { [define]: "" },
    uniforms: {
      uLeds: { value: texture },
      uLedSize: { value: [texture.image.width, texture.image.height] },
      uGain: { value: gain },
      uHousing: { value: HOUSING },
      uSky: { value: SKY },
      uGround: { value: GROUND },
      uAccent: { value: accent },
      uOthers: { value: 1 },
    },
    toneMapped: false,
  });
}
