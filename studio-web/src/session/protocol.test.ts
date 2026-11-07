import { describe, expect, it } from "vitest";
import {
  encodeFrame,
  parseFrame,
  parseServerMessage,
  sessionUrl,
} from "./protocol";

const SPEED = {
  name: "speed",
  kind: "float",
  label: "Speed",
  help: "Cycles per second",
  group: "",
  widget: "",
  default: 1,
  unit: "/s",
  lo: 0,
  hi: 2,
  step: 0.01,
  decimals: 2,
  periodic: false,
  text: [],
};

describe("parseServerMessage", () => {
  it("reads a hello with its records and values", () => {
    const msg = parseServerMessage(
      JSON.stringify({
        type: "hello",
        n: 64,
        fps: 30,
        patterns: ["plasma", "rainbow"],
        pattern: "plasma",
        params: [SPEED],
        values: { speed: 1.5, gone: null },
      }),
    );
    expect(msg).toEqual({
      type: "hello",
      n: 64,
      fps: 30,
      patterns: ["plasma", "rainbow"],
      pattern: "plasma",
      params: [
        {
          name: "speed",
          kind: "float",
          label: "Speed",
          help: "Cycles per second",
          group: "",
          widget: "",
          default: 1,
          unit: "/s",
          lo: 0,
          hi: 2,
          step: 0.01,
          decimals: 2,
          periodic: false,
        },
      ],
      values: { speed: 1.5 },
    });
  });

  it("reads status, params, declare, bound and power", () => {
    expect(
      parseServerMessage(
        '{"type":"status","error":null,"source":null,"path":null}',
      ),
    ).toEqual({ type: "status", error: null, source: null, path: null });
    expect(
      parseServerMessage(
        '{"type":"status","error":"boom","source":"render","path":"plasma"}',
      ),
    ).toEqual({
      type: "status",
      error: "boom",
      source: "render",
      path: "plasma",
    });
    expect(
      parseServerMessage(
        '{"type":"params","values":{"speed":0.5,"on":true,"shape":"ramp","color":{"h":30,"s":1,"v":1},"bad":null}}',
      ),
    ).toEqual({
      type: "params",
      values: {
        speed: 0.5,
        on: true,
        shape: "ramp",
        color: { h: 30, s: 1, v: 1 },
      },
    });
    expect(
      parseServerMessage(JSON.stringify({ type: "declare", params: [SPEED] })),
    ).toMatchObject({
      type: "declare",
      params: [{ name: "speed", kind: "float", decimals: 2 }],
    });
    expect(
      parseServerMessage(
        '{"type":"bound","n":3072,"catalog_digest":"abc","issues":[{"level":"warning","code":"x","message":"m"}]}',
      ),
    ).toEqual({
      type: "bound",
      n: 3072,
      catalog_digest: "abc",
      issues: [{ level: "warning", code: "x", message: "m" }],
    });
    expect(
      parseServerMessage('{"type":"power","watts":12.5,"uncapped_watts":50}'),
    ).toEqual({ type: "power", watts: 12.5, uncapped_watts: 50 });
    expect(parseServerMessage('{"type":"power","watts":12.5}')).toEqual({
      type: "power",
      watts: 12.5,
      uncapped_watts: 12.5,
    });
  });

  it("reads a bind refusal with its issues, and a set refusal with its param", () => {
    expect(
      parseServerMessage(
        '{"type":"refused","control":"bind","reason":"bad","issues":[{"level":"error","code":"c","message":"bad"}]}',
      ),
    ).toEqual({
      type: "refused",
      control: "bind",
      reason: "bad",
      issues: [{ level: "error", code: "c", message: "bad" }],
    });
    expect(
      parseServerMessage(
        '{"type":"refused","control":"set","name":"speed","reason":"out of range"}',
      ),
    ).toEqual({
      type: "refused",
      control: "set",
      name: "speed",
      reason: "out of range",
      issues: [],
    });
    // The preview's shape: `name` and `id` are always there, null when unset.
    expect(
      parseServerMessage(
        '{"type":"refused","control":"pattern","name":null,"id":null,"reason":"no"}',
      ),
    ).toEqual({
      type: "refused",
      control: "pattern",
      reason: "no",
      issues: [],
    });
  });

  it("returns null for malformed or unknown messages", () => {
    expect(parseServerMessage("not json")).toBeNull();
    expect(parseServerMessage("[1,2]")).toBeNull();
    expect(parseServerMessage('{"type":"mystery"}')).toBeNull();
    expect(
      parseServerMessage('{"type":"hello","n":"64","params":[]}'),
    ).toBeNull();
    expect(
      parseServerMessage(
        '{"type":"hello","n":64,"params":[{"name":"x","kind":"float"}]}',
      ),
    ).toBeNull();
    expect(parseServerMessage('{"type":"power","watts":"lots"}')).toBeNull();
    expect(parseServerMessage('{"type":"bound"}')).toBeNull();
  });
});

describe("parseFrame", () => {
  it("reads the <fI header and the RGB body", () => {
    const rgb = new Uint8Array([1, 2, 3, 4, 5, 6]);
    const frame = parseFrame(encodeFrame(1.5, 42, rgb), 2);
    expect(frame?.t).toBeCloseTo(1.5);
    expect(frame?.seq).toBe(42);
    expect([...(frame?.rgb ?? [])]).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("is little-endian, as struct.pack('<fI') writes it", () => {
    const buffer = new ArrayBuffer(8 + 3);
    const view = new DataView(buffer);
    view.setFloat32(0, 2.25, true);
    view.setUint32(4, 0x01020304, true);
    const frame = parseFrame(buffer, 1);
    expect(frame?.t).toBe(2.25);
    expect(frame?.seq).toBe(0x01020304);
  });

  it("drops a frame whose length is not 8 + 3n", () => {
    const buffer = encodeFrame(0, 1, new Uint8Array(3 * 64));
    expect(parseFrame(buffer, 64)).not.toBeNull();
    expect(parseFrame(buffer, 63)).toBeNull();
    expect(parseFrame(buffer, 65)).toBeNull();
    expect(parseFrame(new ArrayBuffer(4), 0)).toBeNull();
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
