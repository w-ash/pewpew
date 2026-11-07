import { parseFrame } from "../../../src/wire/protocol";
import { describe, expect, it } from "vitest";
import {
  encodeFrame,
  parseStudioMessage,
  STUDIO_TYPES,
  sessionUrl,
} from "../../../src/studio/session/protocol";

describe("parseStudioMessage", () => {
  it("reads bound and power; a power with one reading is uncapped", () => {
    expect(
      parseStudioMessage({
        type: "bound",
        n: 3072,
        catalog_digest: "d",
        issues: [],
      }),
    ).toEqual({ type: "bound", n: 3072 });
    expect(
      parseStudioMessage({ type: "power", watts: 12, uncapped_watts: 40 }),
    ).toEqual({ type: "power", watts: 12, uncapped_watts: 40 });
    expect(parseStudioMessage({ type: "power", watts: 12 })).toEqual({
      type: "power",
      watts: 12,
      uncapped_watts: 12,
    });
  });

  it("reads nothing from the studio's hello, and drops a malformed message", () => {
    expect(STUDIO_TYPES).toContain("hello");
    expect(
      parseStudioMessage({
        type: "hello",
        n: 256,
        fps: 30,
        capabilities: ["ack", "look"],
      }),
    ).toBeNull();
    expect(parseStudioMessage({ type: "bound", n: "many" })).toBeNull();
    expect(parseStudioMessage({ type: "power" })).toBeNull();
  });
});

describe("encodeFrame", () => {
  it("writes the <fI header little-endian, as the wire reads it", () => {
    const frame = parseFrame(
      encodeFrame(2.25, 0x01020304, new Uint8Array([1, 2, 3, 4, 5, 6])),
    );
    expect(frame.t).toBe(2.25);
    expect(frame.seq).toBe(0x01020304);
    expect([...frame.rgb]).toEqual([1, 2, 3, 4, 5, 6]);
  });
});

describe("sessionUrl", () => {
  it("uses wss over https and ws otherwise", () => {
    expect(sessionUrl({ protocol: "https:", host: "studio.example" })).toBe(
      "wss://studio.example/ws/session",
    );
    expect(sessionUrl({ protocol: "http:", host: "127.0.0.1:5173" })).toBe(
      "ws://127.0.0.1:5173/ws/session",
    );
  });
});
