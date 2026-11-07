import type { Catalog } from "../api/types";

/** A stand-in catalog: the bar and its two end pieces, with mock GLB URLs. */
export const mockCatalog: Catalog = {
  digest: "mock-catalog",
  fixture_types: [
    {
      id: "clen-rgbw-bar-1m",
      name: "1M LED Pixel Bar",
      digest: "mock-bar",
      assembly_url: "/api/assembly/mock-bar.glb",
      anchors: {
        end_a: { accepts: "diffuser_outer", connector: null },
        end_b: { accepts: "diffuser_outer", connector: null },
        in: { accepts: null, connector: "clen-4pin" },
        out: { accepts: null, connector: "clen-4pin" },
      },
    },
  ],
  attachment_types: [
    {
      id: "point-v0",
      name: "Point",
      digest: "mock-point",
      assembly_url: "/api/assembly/mock-point.glb",
      fits: "diffuser_outer",
    },
    {
      id: "eye-v0",
      name: "Eye",
      digest: "mock-eye",
      assembly_url: "/api/assembly/mock-eye.glb",
      fits: "diffuser_outer",
    },
  ],
  controllers: [
    { id: "esp32s3-devkitc1-ahct125", name: "ESP32-S3 + 74AHCT125" },
  ],
  psus: [{ id: "meanwell-lrs-350-24", name: "Mean Well LRS-350-24" }],
  cables: [{ id: "wire-16awg-pair", name: "16 AWG pair" }],
  presets: [
    { name: "ring", params: [{ name: "count", required: true }] },
    { name: "array", params: [{ name: "counts", required: true }] },
  ],
};

export const MOCK_PIXELS_PER_BAR = 64;
