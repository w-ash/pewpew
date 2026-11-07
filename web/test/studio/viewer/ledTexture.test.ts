import {
  LinearFilter,
  RGBAFormat,
  SRGBColorSpace,
  UnsignedByteType,
} from "three";
import { describe, expect, it } from "vitest";
import { threeBarRig } from "../../../src/studio/mocks/rig";
import {
  createLedData,
  createLedTexture,
  fillLedData,
  ledLayout,
} from "../../../src/studio/viewer/ledTexture";

describe("ledLayout", () => {
  it("is max pixel_count wide with one row per fixture", () => {
    const layout = ledLayout(
      [
        { ...threeBarRig.fixtures[0]!, pixel_start: 0, pixel_count: 64 },
        { ...threeBarRig.fixtures[1]!, pixel_start: 64, pixel_count: 36 },
      ],
      100,
    );
    expect(layout).toMatchObject({ width: 64, height: 2, n: 100 });
    expect(layout.rows).toEqual([
      { start: 0, count: 64 },
      { start: 64, count: 36 },
    ]);
  });
});

describe("fillLedData", () => {
  it("copies each fixture's pixels into its row, padded to RGBA", () => {
    // Two fixtures, the second shorter and listed first in pixel order.
    const layout = {
      width: 3,
      height: 2,
      n: 5,
      rows: [
        { start: 2, count: 3 },
        { start: 0, count: 2 },
      ],
    };
    const data = createLedData(layout);
    const rgb = new Uint8Array([
      10, 11, 12, 20, 21, 22, 30, 31, 32, 40, 41, 42, 50, 51, 52,
    ]);
    fillLedData(data, layout, rgb);
    expect([...data]).toEqual([
      // row 0 = pixels 2, 3, 4
      30, 31, 32, 255, 40, 41, 42, 255, 50, 51, 52, 255,
      // row 1 = pixels 0, 1, then the untouched pad texel
      10, 11, 12, 255, 20, 21, 22, 255, 0, 0, 0, 255,
    ]);
  });

  it("passes bytes through unchanged, with no gamma of its own", () => {
    const layout = ledLayout(threeBarRig.fixtures, threeBarRig.n);
    const data = createLedData(layout);
    const rgb = new Uint8Array(threeBarRig.n * 3).map((_, i) => (i * 7) % 256);
    fillLedData(data, layout, rgb);
    for (let p = 0; p < threeBarRig.n; p++) {
      const f = Math.floor(p / 64);
      const j = p % 64;
      const at = (f * layout.width + j) * 4;
      expect([data[at], data[at + 1], data[at + 2], data[at + 3]]).toEqual([
        rgb[p * 3],
        rgb[p * 3 + 1],
        rgb[p * 3 + 2],
        255,
      ]);
    }
  });

  it("leaves a row alone when its pixels fall outside a short frame", () => {
    const layout = {
      width: 2,
      height: 2,
      n: 4,
      rows: [
        { start: 0, count: 2 },
        { start: 2, count: 2 },
      ],
    };
    const data = createLedData(layout);
    fillLedData(data, layout, new Uint8Array([1, 1, 1, 2, 2, 2]));
    expect([...data.slice(8)]).toEqual([0, 0, 0, 255, 0, 0, 0, 255]);
    expect([...data.slice(0, 8)]).toEqual([1, 1, 1, 255, 2, 2, 2, 255]);
  });
});

describe("createLedTexture", () => {
  it("is RGBA u8, sRGB, linear-filtered and clamped", () => {
    const t = createLedTexture(ledLayout(threeBarRig.fixtures, threeBarRig.n));
    expect(t.format).toBe(RGBAFormat);
    expect(t.type).toBe(UnsignedByteType);
    expect(t.colorSpace).toBe(SRGBColorSpace);
    expect(t.magFilter).toBe(LinearFilter);
    expect(t.minFilter).toBe(LinearFilter);
    expect(t.generateMipmaps).toBe(false);
    expect(t.image.width).toBe(64);
    expect(t.image.height).toBe(3);
  });
});
