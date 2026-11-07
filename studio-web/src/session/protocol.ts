/**
 * The `/ws/session` wire protocol (docs/studio/contracts.md, "WebSocket").
 *
 * Text messages follow the preview's shapes (src/pewpew/sinks/preview.py:8-29).
 * A binary frame is a `<fI` header (engine `t` as float32, uint32 sequence,
 * little-endian) and then n×3 display-ready RGB bytes in rig pixel order.
 */
import type { Arrangement, Issue, ParamSpec, ParamValue } from "@/api/types";
import { decodeParams, decodeValues, isNum, isObj, isStr } from "./params";

export const FRAME_HEADER_BYTES = 8;

export interface HelloMessage {
  type: "hello";
  n: number;
  fps: number;
  patterns: string[];
  pattern: string;
  /** Each param's `spec()`, in display order. */
  params: ParamSpec[];
  /** The current values in their JSON form, by name. */
  values: Record<string, ParamValue>;
}

export type ServerMessage =
  | HelloMessage
  | {
      type: "status";
      error: string | null;
      source: string | null;
      /** The address of the part that raised a render error. */
      path: string | null;
    }
  | { type: "params"; values: Record<string, ParamValue> }
  | { type: "declare"; params: ParamSpec[] }
  | {
      type: "refused";
      /** The refused request: `set`, `pattern`, `bind`, `session` or `message`. */
      control: string;
      /** The param a refused `set` named. */
      name?: string;
      reason: string;
      issues: Issue[];
    }
  | { type: "bound"; n: number; catalog_digest: string; issues: Issue[] }
  | { type: "power"; watts: number; uncapped_watts: number };

export type ClientMessage =
  | { type: "bind"; arrangement: Arrangement }
  | { type: "pattern"; name: string }
  | { type: "set"; name: string; value: ParamValue }
  | { type: "pause" }
  | { type: "resume" };

function issues(v: unknown): Issue[] {
  return Array.isArray(v) ? (v.filter(isObj) as unknown as Issue[]) : [];
}

/** Parse one text message; null for anything malformed or unknown. */
export function parseServerMessage(text: string): ServerMessage | null {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return null;
  }
  if (!isObj(raw)) return null;
  switch (raw.type) {
    case "hello": {
      const ps = decodeParams(raw.params ?? []);
      if (!isNum(raw.n) || !ps) return null;
      return {
        type: "hello",
        n: raw.n,
        fps: isNum(raw.fps) ? raw.fps : 30,
        patterns: Array.isArray(raw.patterns) ? raw.patterns.filter(isStr) : [],
        pattern: isStr(raw.pattern) ? raw.pattern : "",
        params: ps,
        values: decodeValues(raw.values),
      };
    }
    case "status":
      return {
        type: "status",
        error: isStr(raw.error) ? raw.error : null,
        source: isStr(raw.source) ? raw.source : null,
        path: isStr(raw.path) ? raw.path : null,
      };
    case "params":
      if (!isObj(raw.values)) return null;
      return { type: "params", values: decodeValues(raw.values) };
    case "declare": {
      const ps = decodeParams(raw.params);
      return ps ? { type: "declare", params: ps } : null;
    }
    case "refused":
      return {
        type: "refused",
        control: isStr(raw.control) ? raw.control : "",
        ...(isStr(raw.name) ? { name: raw.name } : {}),
        reason: isStr(raw.reason) ? raw.reason : "refused",
        issues: issues(raw.issues),
      };
    case "bound":
      if (!isNum(raw.n)) return null;
      return {
        type: "bound",
        n: raw.n,
        catalog_digest: isStr(raw.catalog_digest) ? raw.catalog_digest : "",
        issues: issues(raw.issues),
      };
    case "power":
      if (!isNum(raw.watts)) return null;
      return {
        type: "power",
        watts: raw.watts,
        // A server without the power cap sends one reading, uncapped.
        uncapped_watts: isNum(raw.uncapped_watts)
          ? raw.uncapped_watts
          : raw.watts,
      };
    default:
      return null;
  }
}

export interface Frame {
  t: number;
  seq: number;
  /** n×3 RGB, a view into the received buffer. */
  rgb: Uint8Array;
}

/** Parse a binary frame for a rig of `n` pixels; null unless its length is exactly 8 + 3n. */
export function parseFrame(buffer: ArrayBuffer, n: number): Frame | null {
  if (n < 0 || buffer.byteLength !== FRAME_HEADER_BYTES + 3 * n) return null;
  const view = new DataView(buffer, 0, FRAME_HEADER_BYTES);
  return {
    t: view.getFloat32(0, true),
    seq: view.getUint32(4, true),
    rgb: new Uint8Array(buffer, FRAME_HEADER_BYTES, 3 * n),
  };
}

/** Build a frame; the inverse of `parseFrame`, for the mock and tests. */
export function encodeFrame(
  t: number,
  seq: number,
  rgb: Uint8Array,
): ArrayBuffer {
  const buffer = new ArrayBuffer(FRAME_HEADER_BYTES + rgb.length);
  const view = new DataView(buffer);
  view.setFloat32(0, t, true);
  view.setUint32(4, seq >>> 0, true);
  new Uint8Array(buffer, FRAME_HEADER_BYTES).set(rgb);
  return buffer;
}

export function encodeClientMessage(msg: ClientMessage): string {
  return JSON.stringify(msg);
}

/** The session URL for a page location: `wss://` over https, `ws://` otherwise. */
export function sessionUrl(loc: Pick<Location, "protocol" | "host">): string {
  const scheme = loc.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${loc.host}/ws/session`;
}
