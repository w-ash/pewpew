/**
 * The LED color texture: one row per fixture, `max pixel_count` texels wide,
 * RGBA u8 tagged sRGB.
 *
 * Frames arrive display-ready (gamma and quantization happen on the server,
 * `to_display_u8` in src/pewpew/sinks/base.py:82-91). Tagging the texture
 * sRGB makes the GPU decode on sampling, so the diffuser blends neighbors in
 * linear light, and the material's `colorspace_fragment` encodes once on
 * output: the bytes come back unchanged at texel centers. three.js only
 * accepts sRGB on RGBA u8 textures
 * (https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLTextures.js#L2433-L2451),
 * hence the padding to RGBA.
 */
import {
  ClampToEdgeWrapping,
  DataTexture,
  LinearFilter,
  RGBAFormat,
  SRGBColorSpace,
  UnsignedByteType,
} from "three";
import type { CompiledFixture } from "@/api/types";

export interface LedLayout {
  width: number;
  height: number;
  /** Per texture row: the fixture's first pixel and its pixel count, in rig order. */
  rows: ReadonlyArray<{ start: number; count: number }>;
  /** The rig's total pixel count. */
  n: number;
}

export function ledLayout(
  fixtures: readonly CompiledFixture[],
  n: number,
): LedLayout {
  const rows = fixtures.map((f) => ({
    start: f.pixel_start,
    count: f.pixel_count,
  }));
  const width = Math.max(1, ...rows.map((r) => r.count));
  return { width, height: Math.max(1, rows.length), rows, n };
}

/** Black, opaque texels for a layout. */
export function createLedData(layout: LedLayout): Uint8Array<ArrayBuffer> {
  const data = new Uint8Array(layout.width * layout.height * 4);
  for (let i = 3; i < data.length; i += 4) data[i] = 255;
  return data;
}

/**
 * Copy one frame's RGB (n×3, rig pixel order) into the texels, row by
 * fixture. Rows whose pixels fall outside `rgb` keep their last colors.
 */
export function fillLedData(
  data: Uint8Array,
  layout: LedLayout,
  rgb: Uint8Array,
): void {
  const { width, rows } = layout;
  for (let f = 0; f < rows.length; f++) {
    const { start, count } = rows[f];
    if (start < 0 || (start + count) * 3 > rgb.length) continue;
    let src = start * 3;
    let dst = f * width * 4;
    for (let j = 0; j < count; j++) {
      data[dst] = rgb[src];
      data[dst + 1] = rgb[src + 1];
      data[dst + 2] = rgb[src + 2];
      src += 3;
      dst += 4;
    }
  }
}

/** Fill the texture from a frame when its length matches the layout. */
export function uploadFrame(
  texture: DataTexture,
  layout: LedLayout,
  rgb: Uint8Array,
): void {
  if (rgb.length !== layout.n * 3) return;
  fillLedData(texture.image.data as Uint8Array, layout, rgb);
  texture.needsUpdate = true;
}

export function createLedTexture(layout: LedLayout): DataTexture {
  const texture = new DataTexture(
    createLedData(layout),
    layout.width,
    layout.height,
    RGBAFormat,
    UnsignedByteType,
  );
  texture.colorSpace = SRGBColorSpace;
  texture.magFilter = LinearFilter;
  texture.minFilter = LinearFilter;
  texture.wrapS = ClampToEdgeWrapping;
  texture.wrapT = ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}
